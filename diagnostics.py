"""The copy-and-paste diagnostics report: versions, where the data lives,
counts, the last scan and the recent log."""
import datetime as dt
import os
import platform
import sys

import applog
import config
import paths
import store


def build_report(conn=None, max_log_lines: int = 150) -> str:
    rt = applog.runtime
    db, _ = paths.db_path()
    size = f"{os.path.getsize(db):,} bytes" if os.path.exists(db) else "not present"
    counts = ""
    if conn is not None:
        try:
            counts = f"watchlist items: {store.watchlist_count(conn)}"
        except Exception as e:
            counts = f"(could not query: {e})"
    last = rt.get("last_scan")
    scan_txt = (f"{last['finished']} - {'OK' if last['ok'] else 'FAILED'} in {last.get('seconds', '?')}s. {last.get('summary', '')}"
                if last else "none since this window was opened")
    return "\n".join([
        f"=== {config.APP_NAME} diagnostics ===",
        f"Generated:     {dt.datetime.now():%Y-%m-%d %H:%M:%S}",
        f"App version:   {config.APP_VERSION} ({config.APP_VERSION_DATE})",
        f"Windows:       {platform.platform()}",
        f"Python:        {platform.python_version()} (packaged exe: {bool(getattr(sys, 'frozen', False))})",
        f"Program file:  {sys.executable}",
        f"Data folder:   {paths.data_dir()}",
        f"Database:      {db} ({size}; opened: {rt.get('db_how', '?')}; {counts})",
        f"Local server:  http://127.0.0.1:{rt.get('port', '?')}/",
        f"Last scan:     {scan_txt}",
        "",
        f"--- Last {max_log_lines} log lines ---",
        applog.tail(paths.log_dir(), max_log_lines) or "(log is empty)",
        "=== end of diagnostics ===",
    ])
