"""Leads in the format HLSA Pipeline (the CRM) reads.

Used two ways:
  - the phone edition publishes site/leads.json on every scan (public registry/news data only)
  - the desktop app's "Send to HLSA Pipeline" downloads the user's watchlist, with status and notes
"""
import datetime as dt

import config

FORMAT = "hlsa-scout-leads"


def _partner_names(keys):
    return [config.PARTNERS[k][0] for k in (keys or []) if k in config.PARTNERS]


def org_lead(o: dict, status: str = "", notes: str = "") -> dict:
    return {"key": f"npi:{o.get('npi', '')}", "kind": "org", "name": o.get("name", ""), "dba": o.get("dba", ""),
            "taxonomy": o.get("taxonomy", ""), "registered": o.get("enumerated", ""),
            "address": " ".join(x for x in [o.get("address", ""), o.get("city", ""), "TX", o.get("zip", "")] if x),
            "city": o.get("city", ""), "county": o.get("county", ""), "phone": o.get("phone", ""),
            "official": o.get("official", ""), "official_title": o.get("official_title", ""),
            "official_phone": o.get("official_phone", ""), "big_system": bool(o.get("big_system")),
            "new": bool(o.get("new_since_last") or o.get("is_new")), "partners": _partner_names(o.get("partners")),
            "link": o.get("registry_link", ""), "status": status, "notes": notes}


def story_lead(s: dict, status: str = "", notes: str = "") -> dict:
    when = dt.datetime.fromtimestamp(s["ts"]).strftime("%Y-%m-%d") if s.get("ts") else ""
    return {"key": f"story:{s.get('id', '')}", "kind": "story", "title": s.get("title", ""), "summary": s.get("summary", ""),
            "place": s.get("place", ""), "source": s.get("source", ""), "date": when, "category": s.get("category", ""),
            "partners": _partner_names(s.get("partners")), "link": s.get("link", ""), "status": status, "notes": notes}


def from_scan(result: dict) -> dict:
    return {"format": FORMAT, "origin": "scan", "app_version": config.APP_VERSION,
            "generated": dt.datetime.now().isoformat(timespec="seconds"),
            "leads": [org_lead(o) for o in result.get("orgs", [])] + [story_lead(s) for s in result.get("stories", [])]}


def from_watchlist(items: list) -> dict:
    leads = []
    for it in items:
        snap = it["snapshot"]
        leads.append(org_lead(snap, it["status"], it["notes"]) if it["type"] == "org"
                     else story_lead(snap, it["status"], it["notes"]))
    return {"format": FORMAT, "origin": "watchlist", "app_version": config.APP_VERSION,
            "generated": dt.datetime.now().isoformat(timespec="seconds"), "leads": leads}
