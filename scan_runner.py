"""Runs the news scan and the NPI Registry check side by side and combines them
into the dataset the pages are built from."""
import datetime as dt
import logging
from concurrent.futures import ThreadPoolExecutor

import config
import store
from scanners import news, npi

log = logging.getLogger("hlsascout.scan")


def _npi(conn, progress_cb, force: bool) -> dict:
    cached, saved_at = store.cache_get(conn, "npi")
    if cached and not force and saved_at and dt.datetime.now() - saved_at < dt.timedelta(hours=config.NPI_CACHE_HOURS):
        progress_cb(f"NPI Registry: using today's results from {saved_at:%I:%M %p} "
                    f"({len(cached['orgs'])} organizations; the registry only changes daily).")
        return cached
    result = npi.scan(progress_cb)
    if result["stats"]["failed"] < result["stats"]["searches"] // 2:   # don't cache a mostly-failed run
        store.cache_put(conn, "npi", result)
    elif cached:
        progress_cb("  NPI Registry mostly unreachable - showing the last good results instead.")
        return cached
    return result


def run_full_scan(conn, progress_cb=None, force_npi: bool = False) -> dict:
    def say(msg):
        if progress_cb:
            progress_cb(msg)

    started = dt.datetime.now()
    say("Starting scan...")
    with ThreadPoolExecutor(2) as ex:
        news_f = ex.submit(news.scan, say)
        npi_f = ex.submit(_npi, conn, say, force_npi)
        news_result = news_f.result()
        npi_result = npi_f.result()

    orgs = npi_result["orgs"]
    seen = store.mark_npis_seen(conn, [o["npi"] for o in orgs])
    last_scan = store.get_setting(conn, "last_scan_at")
    for o in orgs:
        first = seen.get(o["npi"], "")
        o["first_seen"] = first
        o["new_since_last"] = bool(last_scan and first > last_scan)
    store.set_setting(conn, "last_scan_at", started.isoformat(timespec="seconds"))

    secs = (dt.datetime.now() - started).total_seconds()
    say(f"Done in {secs:.0f} seconds: {len(news_result['stories'])} stories, {len(orgs)} new organizations.")
    return {
        "stories": news_result["stories"],
        "news_stats": news_result["stats"],
        "orgs": orgs,
        "npi_stats": npi_result["stats"],
        "generated_at": dt.datetime.now(),
        "seconds": round(secs),
        "previous_scan": last_scan,
    }
