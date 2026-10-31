"""Market data for the Market & Plan tab (NT Partnership's market analysis and
business plan). All free, public, no-key sources:

- CMS data catalog (data.cms.gov/data-api): Medicare home health and hospice
  agencies (enrollments + owners) and their 2024 Medicare volume, the nursing
  homes' Payroll-Based Journal staffing (employee vs CONTRACT hours), and the
  clinicians who bill Medicare (by specialty and town).
- BLS Occupational Employment & Wage Statistics for the San Antonio and Austin
  metros (workforce size and pay - the basis of placement fees).

Market share here is measured on the CUSTOMER side (which agencies/owners hold
the Medicare home health and hospice volume, which facilities buy contract
labor). Firm-level market shares of staffing or credentialing companies are not
published anywhere; those are covered by the competitor landscape in config.

Everything is cached for a week (the sources update quarterly or yearly)."""
import datetime as dt
import logging
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

import requests

import config
import geo

log = logging.getLogger("hlsascout.market")

API = "https://data.cms.gov/data-api/v1/dataset/{}/data"
DATASETS = {
    "hha_enroll": "15f64ab4-3172-4a27-b589-ebd67a6d28aa",
    "hha_owners": "fc009b2d-7846-44b1-b4a1-692f0c143879",
    "hha_util": "43ef03ce-2b60-40a8-958e-146195b5fec7",
    "hos_enroll": "25704213-e833-4b8b-9dbc-58dd17149209",
    "hos_owners": "e983965e-1603-4cb8-82b5-c40090e380d1",
    "hos_util": "4e73f1b5-82cb-4682-8ad2-28493f0b6840",
    "pbj": "7e0d53ba-8f02-4c66-98a5-14a1c997c50d",
    "clinicians": "8889d81e-2ee7-448f-8713-f071038289b5",
}
BLS_AREAS = {"0041700": "San Antonio-New Braunfels metro", "0012420": "Austin-Round Rock metro"}
BLS_OCCUPATIONS = {
    "291141": "Registered nurses", "292061": "LVNs / LPNs", "311120": "Home health & personal care aides",
    "311131": "Nursing assistants", "319092": "Medical assistants", "291171": "Nurse practitioners",
    "291071": "Physician assistants", "291123": "Physical therapists", "119111": "Medical & health services managers",
    "292072": "Medical records specialists",
}
CACHE_DAYS = 7

TERRITORY_CITIES = set(geo.NPI_CITIES)                       # upper-case city names
CITY_REGION = {k: v[2] for k, v in geo.NPI_CITIES.items()}
CITY_COUNTY = {k: v[1] for k, v in geo.NPI_CITIES.items()}
TERRITORY_COUNTIES = {p[1] for p in geo.PLACES}
COUNTY_REGION = {}
for _p, _c, _r, _a in geo.PLACES:
    COUNTY_REGION.setdefault(_c, _r)


def _get_all(ds_key: str, filters: dict, page: int = 5000, max_rows: int = 60000) -> list:
    rows, offset = [], 0
    while offset < max_rows:
        params = {f"filter[{k}]": v for k, v in filters.items()}
        params.update(size=page, offset=offset)
        r = requests.get(API.format(DATASETS[ds_key]), params=params, timeout=120, headers=config.REQUEST_HEADERS)
        r.raise_for_status()
        batch = r.json()
        rows += batch
        if len(batch) < page:
            break
        offset += page
    return rows


def _num(v) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _clean_name(name: str) -> str:
    name = re.sub(r"\s*\(D\.?B\.?A\.?\)\s*", " ", name or "").strip()
    return name.title() if name.isupper() else name


# ------------------------------------------------------------------ agencies
_CORP_SUFFIX = re.compile(r"\b(LLC|L\.L\.C\.|INC|INC\.|CORP|CORPORATION|LP|L\.P\.|LTD|PLLC|PA|CO|COMPANY|HOLDINGS?)\b\.?,?", re.I)


def _owner_key(name: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", _CORP_SUFFIX.sub("", name or "").lower()).strip()


def _owners_for(kind: str, enroll_ids: set) -> dict:
    """{enrollment id: [owner org names]} - organizational owners with 5%+ interest.
    The owners file has no state column for the agency, so it is read in full
    pages and kept only for our agencies (about 2-4 pages for Texas-sized volumes)."""
    out = defaultdict(list)
    offset, page = 0, 5000
    while offset < 400000:
        r = requests.get(API.format(DATASETS[f"{kind}_owners"]), params={"size": page, "offset": offset},
                         timeout=120, headers=config.REQUEST_HEADERS)
        r.raise_for_status()
        batch = r.json()
        for o in batch:
            if o.get("ENROLLMENT ID") in enroll_ids and o.get("TYPE - OWNER") == "O":
                nm = o.get("ORGANIZATION NAME - OWNER") or o.get("DOING BUSINESS AS NAME - OWNER") or ""
                role = (o.get("ROLE TEXT - OWNER") or "").upper()
                if nm and ("OWNERSHIP" in role):     # 5%+ direct or indirect ownership interest
                    out[o["ENROLLMENT ID"]].append(nm)
        if len(batch) < page:
            break
        offset += page
    return out


def agency_market(kind: str) -> dict:
    enroll = [r for r in _get_all(f"{kind}_enroll", {"STATE": "TX"}) if (r.get("CITY") or "").upper() in TERRITORY_CITIES]
    util = {u["PRVDR_ID"]: u for u in _get_all(f"{kind}_util", {"STATE": "TX", "SMRY_CTGRY": "PROVIDER"})}
    owners = _owners_for(kind, {r["ENROLLMENT ID"] for r in enroll})

    # One row per agency (an agency can have several enrollments / NPIs under one CCN)
    agencies = {}
    for r in enroll:
        ccn = r.get("CCN") or r["ENROLLMENT ID"]
        city = (r.get("CITY") or "").upper()
        a = agencies.setdefault(ccn, {
            "ccn": ccn, "name": _clean_name(r.get("DOING BUSINESS AS NAME") or r.get("ORGANIZATION NAME")),
            "legal": _clean_name(r.get("ORGANIZATION NAME")), "city": geo.NPI_CITIES[city][0],
            "county": CITY_COUNTY[city], "region": CITY_REGION[city],
            "nonprofit": r.get("PROPRIETARY_NONPROFIT") == "N", "incorporated": r.get("INCORPORATION DATE", ""),
            "npi": r.get("NPI", ""), "owners": set(), "benes": 0.0, "episodes": 0.0, "payments": 0.0,
        })
        a["owners"].update(owners.get(r["ENROLLMENT ID"], []))
        u = util.get(ccn)
        if u and not a["benes"]:
            a["benes"] = _num(u.get("BENE_DSTNCT_CNT"))
            a["episodes"] = _num(u.get("TOT_EPSD_STAY_CNT"))
            a["payments"] = _num(u.get("TOT_MDCR_PYMT_AMT"))

    # Parent group: an organizational owner shared by 2+ agencies here (a chain / platform),
    # else the single org owner, else the agency itself (independent).
    owner_counts = Counter(_owner_key(o) for a in agencies.values() for o in a["owners"])
    owner_label = {}
    for a in agencies.values():
        for o in a["owners"]:
            owner_label.setdefault(_owner_key(o), _clean_name(o))
    for a in agencies.values():
        shared = sorted((o for o in a["owners"] if owner_counts[_owner_key(o)] >= 2),
                        key=lambda o: -owner_counts[_owner_key(o)])
        if shared:
            a["group"], a["group_type"] = owner_label[_owner_key(shared[0])], "Multi-agency owner"
        elif a["nonprofit"]:
            a["group"], a["group_type"] = a["name"], "Nonprofit"
        elif a["owners"]:
            a["group"], a["group_type"] = a["name"], "Single-site, company-owned"
        else:
            a["group"], a["group_type"] = a["name"], "Independent (owner-operated)"
        a["owners"] = sorted(a["owners"])

    rows = sorted(agencies.values(), key=lambda a: -a["benes"])
    total = sum(a["benes"] for a in rows) or 1
    groups = defaultdict(lambda: {"benes": 0.0, "payments": 0.0, "agencies": 0, "type": ""})
    for a in rows:
        g = groups[a["group"]]
        g["benes"] += a["benes"]
        g["payments"] += a["payments"]
        g["agencies"] += 1
        g["type"] = a["group_type"]
    group_rows = sorted(({"group": k, **v, "share": v["benes"] / total} for k, v in groups.items()),
                        key=lambda g: -g["benes"])
    hhi = round(sum((g["share"] * 100) ** 2 for g in group_rows))
    by_type = defaultdict(lambda: {"agencies": 0, "benes": 0.0})
    for a in rows:
        by_type[a["group_type"]]["agencies"] += 1
        by_type[a["group_type"]]["benes"] += a["benes"]
    by_region = defaultdict(lambda: {"agencies": 0, "benes": 0.0, "with_volume": 0})
    for a in rows:
        by_region[a["region"]]["agencies"] += 1
        by_region[a["region"]]["benes"] += a["benes"]
        by_region[a["region"]]["with_volume"] += 1 if a["benes"] else 0
    return {
        "agencies": rows, "groups": group_rows, "total_benes": total if rows else 0,
        "total_payments": sum(a["payments"] for a in rows), "hhi": hhi,
        "top5_share": sum(g["share"] for g in group_rows[:5]),
        "by_type": dict(by_type), "by_region": dict(by_region),
        "no_volume": sum(1 for a in rows if not a["benes"]),
    }


# ------------------------------------------------------------------ nursing homes: contract labor
def contract_labor() -> dict:
    """Latest quarter of the Payroll-Based Journal for nursing homes in the
    territory's counties: employee vs contract (agency) nursing hours."""
    facilities = defaultdict(lambda: {"emp": 0.0, "ctr": 0.0, "days": set(), "census": 0.0})
    quarter = ""

    def county_rows(county):
        try:
            return _get_all("pbj", {"STATE": "TX", "COUNTY_NAME": county}, max_rows=20000)
        except Exception as e:
            log.warning("PBJ %s failed: %s", county, e)
            return []

    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(county_rows, sorted(TERRITORY_COUNTIES)))
    for rows in results:
        for r in rows:
            quarter = max(quarter, r.get("CY_Qtr", ""))
    for rows in results:
        for r in rows:
            if r.get("CY_Qtr") != quarter:
                continue
            f = facilities[r["PROVNUM"]]
            f.update(name=_clean_name(r["PROVNAME"]), city=(r.get("CITY") or "").title(), county=r.get("COUNTY_NAME", ""))
            for role in ("RN", "LPN", "CNA", "RNDON", "RNadmin", "LPNadmin", "NAtrn", "MedAide"):
                f["emp"] += _num(r.get(f"Hrs_{role}_emp"))
                f["ctr"] += _num(r.get(f"Hrs_{role}_ctr"))
            f["census"] += _num(r.get("MDScensus"))
            f["days"].add(r.get("WorkDate"))
    rows = []
    for pid, f in facilities.items():
        tot = f["emp"] + f["ctr"]
        if not tot:
            continue
        days = len(f["days"]) or 1
        rows.append({"id": pid, "name": f["name"], "city": f["city"], "county": f["county"],
                     "region": COUNTY_REGION.get(f["county"], ""), "contract_hours": round(f["ctr"]),
                     "total_hours": round(tot), "contract_share": f["ctr"] / tot,
                     "avg_census": round(f["census"] / days)})
    rows.sort(key=lambda r: -r["contract_hours"])
    by_county = defaultdict(lambda: {"facilities": 0, "contract_hours": 0, "total_hours": 0})
    for r in rows:
        c = by_county[r["county"]]
        c["facilities"] += 1
        c["contract_hours"] += r["contract_hours"]
        c["total_hours"] += r["total_hours"]
    return {"quarter": quarter, "facilities": rows, "by_county": dict(by_county),
            "contract_hours": sum(r["contract_hours"] for r in rows),
            "total_hours": sum(r["total_hours"] for r in rows)}


# ------------------------------------------------------------------ clinicians (credentialing market)
def clinicians() -> dict:
    """Clinicians who billed Medicare in 2024 with a practice address in the territory."""
    rows = [r for r in _get_all("clinicians", {"Rndrng_Prvdr_State_Abrvtn": "TX", "Rndrng_Prvdr_Ent_Cd": "I"},
                                max_rows=120000)
            if (r.get("Rndrng_Prvdr_City") or "").upper() in TERRITORY_CITIES]
    spec = Counter(r.get("Rndrng_Prvdr_Type", "Other") for r in rows)
    region = Counter(CITY_REGION[(r.get("Rndrng_Prvdr_City") or "").upper()] for r in rows)
    city = Counter(geo.NPI_CITIES[(r.get("Rndrng_Prvdr_City") or "").upper()][0] for r in rows)
    return {"total": len(rows), "by_specialty": spec.most_common(), "by_region": dict(region),
            "by_city": city.most_common(25)}


# ------------------------------------------------------------------ workforce (BLS)
def workforce() -> dict:
    series = [f"OEUM{a}000000{o}{d}" for a in BLS_AREAS for o in BLS_OCCUPATIONS for d in ("01", "04")]
    out, year = defaultdict(dict), ""
    for i in range(0, len(series), 25):
        r = requests.post("https://api.bls.gov/publicAPI/v1/timeseries/data/", json={"seriesid": series[i:i + 25]},
                          timeout=60, headers=config.REQUEST_HEADERS).json()
        for s in r.get("Results", {}).get("series", []):
            if not s.get("data"):
                continue
            sid, val = s["seriesID"], _num(s["data"][0]["value"])
            year = max(year, s["data"][0].get("year", ""))
            area, occ, kind = sid[4:11], sid[17:23], sid[-2:]
            out[(area, occ)]["employment" if kind == "01" else "annual_wage"] = val
    rows = [{"area": BLS_AREAS[a], "occupation": BLS_OCCUPATIONS[o], "occ": o, **v} for (a, o), v in out.items()]
    return {"year": year, "rows": rows}


# ------------------------------------------------------------------ everything
def build(progress_cb=None) -> dict:
    def say(m):
        if progress_cb:
            progress_cb(m)
        log.info(m)

    say("Market data: CMS home health, hospice, nursing-home staffing, clinicians + BLS workforce...")
    jobs = {"home_health": lambda: agency_market("hha"), "hospice": lambda: agency_market("hos"),
            "contract_labor": contract_labor, "clinicians": clinicians, "workforce": workforce}
    out, errors = {}, {}
    with ThreadPoolExecutor(5) as ex:
        futs = {k: ex.submit(f) for k, f in jobs.items()}
        for k, f in futs.items():
            try:
                out[k] = f.result()
            except Exception as e:
                log.exception("Market source %s failed", k)
                errors[k] = f"{type(e).__name__}: {e}"
                out[k] = None
    out["errors"] = errors
    out["fetched_at"] = dt.datetime.now().isoformat(timespec="seconds")
    hh = out.get("home_health") or {}
    say(f"  Market data ready: {len(hh.get('agencies', []))} home health agencies, "
        f"{len((out.get('hospice') or {}).get('agencies', []))} hospices, "
        f"{len((out.get('contract_labor') or {}).get('facilities', []))} nursing homes, "
        f"{(out.get('clinicians') or {}).get('total', 0)} Medicare clinicians"
        + (f" ({len(errors)} sources failed)" if errors else ""))
    return out
