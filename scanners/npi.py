"""Newly registered healthcare organizations, from the free federal NPI Registry
(npiregistry.cms.hhs.gov - no key, no account).

Every clinic, practice, agency or facility that bills insurance must get an
organizational NPI, usually weeks before it opens. So a brand-new NPI in the
territory is often the earliest public sign of a new Mom-and-Pop practice or
home health agency - long before (or instead of) any news story.

The registry API returns at most 1,200 results per search and sorts them
alphabetically, so each 3-digit ZIP area is searched once per type of provider
(taxonomy) - small enough slices that the newest registrations aren't cut off."""
import datetime as dt
import logging
import re
from concurrent.futures import ThreadPoolExecutor

import requests

import config
import geo

log = logging.getLogger("hlsascout.npi")

API = "https://npiregistry.cms.hhs.gov/api/"

# (registry taxonomy text to search, our group label). The registry matches
# taxonomy text loosely, so each search is re-checked against the group's words.
TAXONOMY_SEARCHES = [
    ("Home Health", "Home health & home care"), ("Personal Care", "Home health & home care"),
    ("Hospice", "Hospice"), ("Assisted Living", "Senior living & nursing"),
    ("Nursing Facility", "Senior living & nursing"), ("Skilled Nursing", "Senior living & nursing"),
    ("Family Medicine", "Primary care & clinics"), ("Internal Medicine", "Primary care & clinics"),
    ("General Practice", "Primary care & clinics"), ("Pediatrics", "Primary care & clinics"),
    ("Clinic/Center", "Primary care & clinics"), ("Nurse Practitioner", "Primary care & clinics"),
    ("Physician Assistant", "Primary care & clinics"), ("Multi-Specialty", "Physician groups"),
    ("Single Specialty", "Physician groups"), ("Obstetrics", "Physician groups"),
    ("Orthopaedic", "Physician groups"), ("Cardiovascular", "Physician groups"),
    ("Dermatology", "Physician groups"), ("Pain Medicine", "Physician groups"),
    ("Surgery", "Physician groups"), ("Ambulatory Surgical", "Surgery & hospitals"),
    ("Hospital", "Surgery & hospitals"), ("Emergency Medicine", "Surgery & hospitals"),
    ("Counselor", "Behavioral health"), ("Psychologist", "Behavioral health"),
    ("Social Worker", "Behavioral health"), ("Psychiatry", "Behavioral health"),
    ("Behavior Analyst", "Behavioral health"), ("Physical Therapist", "Therapy & rehab"),
    ("Occupational Therapist", "Therapy & rehab"), ("Speech", "Therapy & rehab"),
    ("Chiropractor", "Therapy & rehab"), ("Podiatrist", "Specialty practices"),
    ("Optometrist", "Specialty practices"), ("Dentist", "Dental"),
    ("Durable Medical Equipment", "Equipment, pharmacy & labs"), ("Pharmacy", "Equipment, pharmacy & labs"),
    ("Laboratory", "Equipment, pharmacy & labs"), ("Radiology", "Equipment, pharmacy & labs"),
    ("Ambulance", "Equipment, pharmacy & labs"),
]
GROUP_ORDER = ["Home health & home care", "Hospice", "Senior living & nursing", "Primary care & clinics",
               "Physician groups", "Surgery & hospitals", "Behavioral health", "Therapy & rehab",
               "Specialty practices", "Dental", "Equipment, pharmacy & labs", "Other"]

# Which partners a new organization of each group could use.
GROUP_PARTNERS = {
    "Home health & home care": ["nt_staff", "nt_cred", "wave", "mr3", "guiding", "macro"],
    "Hospice": ["nt_staff", "wave", "guiding", "macro"],
    "Senior living & nursing": ["nt_staff", "nurses_etc", "guiding", "mr3", "macro"],
    "Primary care & clinics": ["nt_cred", "nt_staff", "wave", "mr3", "macro", "ascent"],
    "Physician groups": ["nt_cred", "wave", "orchestra", "mr3", "macro", "ascent"],
    "Surgery & hospitals": ["nt_cred", "nurses_etc", "orchestra", "wave", "arista"],
    "Behavioral health": ["nt_cred", "wave", "macro"],
    "Therapy & rehab": ["nt_cred", "wave", "puckett", "macro"],
    "Specialty practices": ["nt_cred", "wave", "mr3", "macro"],
    "Dental": ["macro", "ascent"],
    "Equipment, pharmacy & labs": ["wave", "mr3"],
    "Other": ["nt_cred", "wave"],
}

# Registrations by big systems / chains / government are labelled, not hidden.
_BIG_RE = re.compile("|".join(config.BIG_SYSTEMS) + r"|HOSPITAL DISTRICT|COUNTY OF|CITY OF|STATE OF|UNIVERSITY",
                     re.I)


def _query(params: dict) -> list:
    params = dict(params, version="2.1", enumeration_type="NPI-2", state="TX", limit=200)
    out = []
    for skip in range(0, 1200, 200):
        params["skip"] = skip
        r = requests.get(API, params=params, timeout=40, headers=config.REQUEST_HEADERS)
        r.raise_for_status()
        data = r.json()
        if data.get("Errors"):
            raise RuntimeError(str(data["Errors"])[:200])
        res = data.get("results", [])
        out += res
        if len(res) < 200:
            break
    return out


def _location(rec: dict) -> dict | None:
    addrs = rec.get("addresses", [])
    loc = next((a for a in addrs if a.get("address_purpose") == "LOCATION"), addrs[0] if addrs else None)
    return loc


def _phone(raw) -> str:
    digits = re.sub(r"\D", "", raw or "")
    return f"{digits[:3]}-{digits[3:6]}-{digits[6:10]}" if len(digits) == 10 else (raw or "")


def _org(rec: dict, group_hint: str) -> dict | None:
    b = rec.get("basic", {})
    addr = _location(rec)
    if not addr:
        return None
    city = (addr.get("city") or "").upper().strip()
    where = geo.NPI_CITIES.get(city)
    if not where:
        return None
    taxes = rec.get("taxonomies", [])
    primary = next((t for t in taxes if t.get("primary")), taxes[0] if taxes else {})
    desc = primary.get("desc", "") or ""
    group = _group_for(desc) or "Other"
    name = b.get("organization_name", "") or ""
    other = [o.get("organization_name") for o in rec.get("other_names", []) if o.get("organization_name")]
    official = " ".join(x for x in [b.get("authorized_official_first_name", ""), b.get("authorized_official_last_name", "")] if x)
    zip5 = (addr.get("postal_code") or "")[:5]
    official = official.title()
    cred = (b.get("authorized_official_credential") or "").replace(".", "").upper()
    if official and cred:
        official = f"{official}, {cred}"
    return {
        "npi": rec.get("number", ""), "name": name.title() if name.isupper() else name,
        "dba": ", ".join(o.title() if o.isupper() else o for o in other[:2]),
        "enumerated": b.get("enumeration_date", ""), "updated": b.get("last_updated", ""),
        "taxonomy": desc, "group": group, "city": where[0], "county": where[1], "region": where[2],
        "address": " ".join(x for x in [addr.get("address_1", ""), addr.get("address_2", "")] if x).title(),
        "zip": zip5, "phone": _phone(addr.get("telephone_number")), "fax": _phone(addr.get("fax_number")),
        "official": official,
        "official_title": (b.get("authorized_official_title_or_position") or "").title(),
        "official_phone": _phone(b.get("authorized_official_telephone_number")),
        "big_system": bool(_BIG_RE.search(name + " " + " ".join(other))),
        "partners": GROUP_PARTNERS.get(group, GROUP_PARTNERS["Other"]),
        "registry_link": f"https://npiregistry.cms.hhs.gov/provider-view/{rec.get('number', '')}",
    }


# Group from the organization's primary taxonomy text, most specific first.
_GROUP_RULES = [
    ("home health|personal care|home care|private duty", "Home health & home care"),
    ("hospice", "Hospice"),
    ("assisted living|nursing facility|skilled nursing|custodial care|intermediate care", "Senior living & nursing"),
    ("counsel|psych|social worker|behavior|mental|addiction|substance", "Behavioral health"),
    ("physical therap|occupational therap|speech|chiropract|rehabilitation", "Therapy & rehab"),
    ("dentist|dental|orthodont", "Dental"),
    ("equipment|pharmacy|laborator|radiolog|ambulance|supplier|prosthet|orthotic", "Equipment, pharmacy & labs"),
    ("hospital|surg|anesthes|emergency", "Surgery & hospitals"),
    ("family|internal medicine|general practice|pediatric|nurse practitioner|physician assistant|clinic|primary care|"
     "federally qualified|rural health", "Primary care & clinics"),
    ("podiatr|optomet|ophthalm|audiolog|wound", "Specialty practices"),
    ("specialty|orthopaed|cardio|obstet|gynec|dermat|pain|neurolog|oncolog|urolog|gastro|allerg", "Physician groups"),
]
_GROUP_RES = [(re.compile(rx, re.I), g) for rx, g in _GROUP_RULES]


def _group_for(desc: str) -> str | None:
    for rx, g in _GROUP_RES:
        if rx.search(desc or ""):
            return g
    return None


def _collapse(orgs: list) -> list:
    """One row per organization name + city (systems often register many NPIs at once)."""
    rows = {}
    for o in orgs:
        key = (o["name"].lower(), o["city"])
        if key in rows:
            rows[key]["count"] += 1
            rows[key]["npis"].append(o["npi"])
        else:
            rows[key] = dict(o, count=1, npis=[o["npi"]])
    return list(rows.values())


def scan(progress_cb=None) -> dict:
    """{'orgs': [...newest first], 'stats': {...}}. Network failures in single
    searches are logged and skipped, never fatal."""
    def say(msg):
        if progress_cb:
            progress_cb(msg)
        log.info(msg)

    cutoff = (dt.date.today() - dt.timedelta(days=config.NPI_WINDOW_DAYS)).isoformat()
    jobs = [({"postal_code": f"{p}*"}, None) for p in geo.NPI_ZIP_PREFIXES]
    jobs += [({"postal_code": f"{p}*", "taxonomy_description": t}, g)
             for p in geo.NPI_ZIP_PREFIXES for t, g in TAXONOMY_SEARCHES]
    say(f"Checking the NPI Registry for new healthcare organizations ({len(jobs)} searches)...")

    def run(job):
        params, group = job
        try:
            return group, _query(params), None
        except Exception as e:
            return group, [], f"{params}: {e}"

    found, errors, capped = {}, [], 0
    with ThreadPoolExecutor(6) as ex:
        for group, recs, err in ex.map(run, jobs):
            if err:
                errors.append(err)
                continue
            if len(recs) >= 1200:
                capped += 1
            for rec in recs:
                if (rec.get("basic", {}).get("enumeration_date") or "") < cutoff:
                    continue
                org = _org(rec, group)
                if org and org["npi"] not in found:
                    found[org["npi"]] = org
    for e in errors[:5]:
        log.warning("NPI search failed: %s", e)
    orgs = sorted(_collapse(found.values()), key=lambda o: (o["enumerated"], o["name"]), reverse=True)
    say(f"  {len(orgs)} organizations registered in the last {config.NPI_WINDOW_DAYS} days in the territory"
        + (f" ({len(errors)} searches failed)" if errors else ""))
    return {"orgs": orgs, "stats": {"searches": len(jobs), "failed": len(errors), "capped": capped,
                                    "window_days": config.NPI_WINDOW_DAYS,
                                    "fetched_at": dt.datetime.now().isoformat(timespec="seconds")}}
