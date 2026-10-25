"""Builds the phone edition of HLSA Scout: a static website made from one
finished scan, published on GitHub Pages by .github/workflows/scan.yml.

The pages are the desktop app's own pages (render.py) in STATIC mode, so any
change to the desktop version shows up on the phone the next time this runs.
The phone can't call Google News itself, so the 🔓 free-version searches are
run here in advance (free.json). Nothing personal is published: each phone
keeps its own watchlist in its own storage."""
import concurrent.futures
import datetime as dt
import json
import os
import shutil

import requests

import config
import render
import site_assets
from scanners import news

NEW_DAYS = 7          # an organization is "NEW" for a week after it first shows up
SEEN_KEEP_DAYS = 150  # forget registrations not seen for this long


def check_quality(result: dict) -> list:
    """Reasons a scan is too incomplete to publish (empty = fine). A bad scan must
    never replace the last good one."""
    problems = []
    ns = result["news_stats"]
    if ns["empty_searches"] > 0.7 * ns["searches"]:
        problems.append(f"{ns['empty_searches']} of {ns['searches']} news searches came back empty (Google News may be blocking)")
    if len(result["stories"]) < 5:
        problems.append(f"only {len(result['stories'])} stories")
    if len(result["orgs"]) < 50:
        problems.append(f"only {len(result['orgs'])} new organizations (NPI Registry trouble?)")
    return problems


def _previous_seen(site_url: str) -> dict | None:
    """When each NPI first appeared, from the currently published site (None on the very first run)."""
    try:
        r = requests.get(site_url.rstrip("/") + "/npi_seen.json", timeout=20, headers=config.REQUEST_HEADERS)
        return r.json() if r.ok else None
    except Exception:
        return None


def _mark_new(orgs: list, previous: dict | None, now: dt.datetime) -> dict:
    today = now.date().isoformat()
    seen = dict(previous or {})
    cutoff_new = (now - dt.timedelta(days=NEW_DAYS)).date().isoformat()
    for o in orgs:
        first = seen.setdefault(o["npi"], today)
        o["first_seen"] = first
        # On the very first run everything is "first seen today" - don't badge all of it.
        o["new_since_last"] = previous is not None and first >= cutoff_new
    keep_after = (now - dt.timedelta(days=SEEN_KEEP_DAYS)).date().isoformat()
    current = {o["npi"] for o in orgs}
    return {k: v for k, v in seen.items() if k in current or v >= keep_after}


def _free_lookup(titles: list, progress) -> dict:
    out = {}

    def one(t):
        r = news.find_free_versions(t)
        return t, {"keywords": r["keywords"], "search_url": r["search_url"],
                   "matches": [{"source": m["source"], "title": m["title"], "link": m["link"]} for m in r["matches"]]}

    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        for t, info in ex.map(one, titles):
            out[t] = info
    progress(f"  free versions found for {sum(1 for v in out.values() if v['matches'])} of {len(titles)} paywalled stories")
    return out


def _watchlist_page() -> str:
    return render._shell("watch", f"""
      <p class="section-sub" style="margin-top:18px">Your watchlist is saved on <b>this device only</b> - it doesn't sync with the
      laptop app or other phones. Tick the box on any story or organization to save it; status and notes save as you type.</p>
      <div id="wl-bar" class="page-actions">
        <button class="btn red" type="button" onclick="exportReport()">\U0001F4E4 Share Watchlist as Report</button>
        <button class="btn" type="button" onclick="exportCsv()">⬇ Excel (CSV)</button></div>
      <div class="filters" id="wl-chips"></div>
      <div class="filters"><input type="search" id="q" placeholder="Search watchlist..." oninput="applyFilters()"></div>
      <div class="list" id="wl-root"></div>""", "Watchlist")


def _diagnostics_page() -> str:
    return render._shell("", """<h2 class="section">Diagnostics</h2>
      <p class="section-sub">If something looks wrong, tap Copy and paste it into an email or chat. It shows the app version,
      when this scan ran, this device's browser, how many watchlist items are saved here and any recent errors.</p>
      <p><button class="btn" onclick="navigator.clipboard.writeText(document.getElementById('diag').textContent).then(()=>this.textContent='Copied!')">Copy</button></p>
      <pre id="diag" style="background:#fff;border:1px solid var(--border);border-radius:8px;padding:12px;font-size:11.5px;white-space:pre-wrap">Gathering...</pre>""",
                         "Diagnostics")


def build_site(result: dict, out_dir: str, site_url: str = config.PHONE_URL, progress=print,
               look_up_free: bool = True, tz_label: str = "CT") -> dict:
    now = dt.datetime.now()
    generated = result["generated_at"]
    scan_label = generated.strftime("%b %d, %Y %I:%M %p").replace(" 0", " ") + f" {tz_label}"
    build_id = now.strftime("%Y%m%d-%H%M%S")

    previous = _previous_seen(site_url)
    progress("NPI first-seen history: " + ("loaded from the live site" if previous is not None else "none yet (first run)"))
    seen = _mark_new(result["orgs"], previous, now)

    free = {}
    if look_up_free:
        titles = sorted({s["title"] for s in result["stories"] if s.get("paywalled")})
        progress(f"Looking up free versions for {len(titles)} paywalled stories...")
        free = _free_lookup(titles, progress)

    with open(config.README_PATH, encoding="utf-8") as f:
        readme = f.read()
    render.configure_static(version_label=f"Phone edition · scanned {scan_label}", scan_label=scan_label,
                            scan_epoch=generated.timestamp(), build_id=build_id, repo_url=config.REPO_URL)
    try:
        pages = {
            "index.html": render.scan_page(result, set()),
            "wire.html": render.wire_page(result, set()),
            "orgs.html": render.orgs_page(result, set()),
            "watchlist.html": _watchlist_page(),
            "about.html": render.about_page(readme),
            "diagnostics.html": _diagnostics_page(),
        }
    finally:
        render.STATIC["on"] = False

    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    for name, html in pages.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(html)

    def dump(name, obj):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, separators=(",", ":"))

    dump("free.json", free)
    dump("npi_seen.json", seen)
    dump("version.json", {"build": build_id, "app_version": config.APP_VERSION, "scan_epoch": generated.timestamp(),
                          "scan_label": scan_label, "stories": len(result["stories"]), "orgs": len(result["orgs"])})
    with open(os.path.join(out_dir, "manifest.webmanifest"), "w", encoding="utf-8") as f:
        f.write(site_assets.manifest_json())
    with open(os.path.join(out_dir, "sw.js"), "w", encoding="utf-8") as f:
        f.write(site_assets.sw_js(build_id))
    with open(os.path.join(out_dir, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nDisallow: /\n")
    open(os.path.join(out_dir, ".nojekyll"), "w").close()
    site_assets.copy_static_files(out_dir)

    sizes = {n: os.path.getsize(os.path.join(out_dir, n)) for n in pages}
    return {"build_id": build_id, "scan_label": scan_label, "sizes": sizes,
            "new_orgs": sum(1 for o in result["orgs"] if o.get("new_since_last"))}
