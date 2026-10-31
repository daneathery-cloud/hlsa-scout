"""Local-only Flask server. Binds to 127.0.0.1, so it is reachable only from
this computer - never the network or internet."""
import csv
import datetime as dt
import io
import json
import logging
import socket
import threading

from flask import Flask, jsonify, make_response, request, send_file

import config
import diagnostics
import pipeline_export
import render
import render_market
import scan_runner
import store
from scanners import news

logging.getLogger("werkzeug").setLevel(logging.WARNING)
log = logging.getLogger("hlsascout.server")


class AppState:
    def __init__(self):
        self.lock = threading.Lock()
        self.data = None     # latest scan_runner result
        self.conn = None

    def set_scan(self, data):
        with self.lock:
            self.data = data

    def get(self):
        with self.lock:
            return self.data


state = AppState()


def find_free_port(preferred: int = 5335) -> int:
    for port in [preferred, *range(5336, 5370)]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _html(text: str, status: int = 200):
    resp = make_response(text, status)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    resp.headers["Cache-Control"] = "no-store"
    return resp


def create_app(conn) -> Flask:
    app = Flask(__name__)
    state.conn = conn

    @app.get("/")
    def scan_report():
        data = state.get()
        return _html(render.scan_page(data, store.watchlisted_keys(conn)) if data else render.empty_scan_page())

    @app.get("/wire")
    def wire():
        return _html(render.wire_page(state.get(), store.watchlisted_keys(conn), request.args.get("cat", "all")))

    @app.get("/orgs")
    def orgs():
        return _html(render.orgs_page(state.get(), store.watchlisted_keys(conn)))

    @app.get("/watchlist")
    def watchlist():
        return _html(render.watchlist_page(store.list_items(conn)))

    @app.get("/about")
    def about():
        try:
            with open(config.README_PATH, encoding="utf-8") as f:
                readme = f.read()
        except OSError:
            readme = "<p>README not found.</p>"
        return _html(render.about_page(readme))

    # ---- Market & Plan (desktop only)
    def _assumptions() -> dict:
        a = dict(config.PLAN_DEFAULTS)
        try:
            a.update({k: float(v) for k, v in json.loads(store.get_setting(conn, "plan_assumptions", "{}")).items()
                      if k in config.PLAN_DEFAULTS})
        except (ValueError, TypeError):
            pass
        return a

    def _market_cached():
        m, _ = store.cache_get(conn, "market")
        return m

    @app.get("/market")
    def market_page():
        return _html(render_market.market_page(_market_cached(), state.get(), _assumptions()))

    @app.post("/api/market/refresh")
    def market_refresh():
        try:
            scan_runner.market_data(conn, force=True)
            return jsonify({"ok": True})
        except Exception as e:
            log.exception("Market refresh failed")
            return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500

    @app.route("/api/market/assumptions", methods=["POST", "DELETE"])
    def market_assumptions():
        if request.method == "DELETE":
            store.set_setting(conn, "plan_assumptions", "{}")
            return jsonify({"ok": True})
        p = request.get_json(force=True, silent=True) or {}
        clean = {k: float(v) for k, v in p.items() if k in config.PLAN_DEFAULTS and isinstance(v, (int, float))}
        store.set_setting(conn, "plan_assumptions", json.dumps(clean))
        return jsonify({"ok": True})

    @app.get("/export/business_plan")
    def export_plan():
        m = _market_cached()
        if not m:
            return _html("<p>Load the market data on the Market &amp; Plan tab first.</p>", 404)
        resp = _html(render_market.business_plan_export(m, state.get(), _assumptions()))
        resp.headers["Content-Disposition"] = (
            f'attachment; filename="NT_Partnership_Business_Plan_{dt.datetime.now():%Y%m%d}.html"')
        return resp

    @app.get("/diagnostics")
    def diag():
        return _html(render.diagnostics_page(diagnostics.build_report(conn)))

    @app.get("/logo.png")
    def logo():
        return send_file(config.LOGO_PATH, mimetype="image/png")

    @app.get("/export/watchlist")
    def export_watchlist():
        resp = _html(render.watchlist_export_html(store.list_items(conn)))
        resp.headers["Content-Disposition"] = (
            f'attachment; filename="HLSA_Scout_Watchlist_{dt.datetime.now():%Y%m%d_%H%M}.html"')
        return resp

    @app.get("/export/pipeline.json")
    def export_pipeline():
        resp = make_response(json.dumps(pipeline_export.from_watchlist(store.list_items(conn)), indent=1))
        resp.headers["Content-Type"] = "application/json; charset=utf-8"
        resp.headers["Content-Disposition"] = f'attachment; filename="HLSA_Scout_Leads_{dt.datetime.now():%Y%m%d_%H%M}.json"'
        return resp

    @app.get("/export/watchlist.csv")
    def export_csv():
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["Kind", "Title / Organization", "Status", "Notes", "Town", "Source / Type", "Date",
                    "Address", "Phone", "Registered by", "Official's title", "Official's phone", "Could help", "Link", "Saved"])
        for it in store.list_items(conn):
            s = it["snapshot"]
            partners = ", ".join(config.PARTNERS[p][0] for p in (s.get("partners") or []) if p in config.PARTNERS)
            if it["type"] == "org":
                w.writerow(["New organization", s.get("name"), it["status"], it["notes"], s.get("city"),
                            s.get("taxonomy"), s.get("enumerated"), f"{s.get('address', '')} {s.get('zip', '')}".strip(),
                            s.get("phone"), s.get("official"), s.get("official_title"), s.get("official_phone"), partners, s.get("registry_link"), it["added_at"]])
            else:
                when = dt.datetime.fromtimestamp(s["ts"]).strftime("%Y-%m-%d") if s.get("ts") else ""
                w.writerow(["Story", s.get("title"), it["status"], it["notes"], s.get("place"), s.get("source"), when,
                            "", "", "", "", "", partners, s.get("link"), it["added_at"]])
        resp = make_response("﻿" + buf.getvalue())   # BOM so Excel reads accents/dashes correctly
        resp.headers["Content-Type"] = "text/csv; charset=utf-8"
        resp.headers["Content-Disposition"] = f'attachment; filename="HLSA_Scout_Watchlist_{dt.datetime.now():%Y%m%d}.csv"'
        return resp

    @app.post("/api/watchlist/toggle")
    def toggle():
        p = request.get_json(force=True, silent=True) or {}
        t, i, action = p.get("type"), p.get("id"), p.get("action")
        if t not in ("story", "org") or not i or action not in ("add", "remove"):
            return jsonify({"ok": False, "error": "bad request"}), 400
        if action == "add":
            store.add_item(conn, t, i, p.get("label", ""), p.get("snapshot") or {})
        else:
            store.remove_item(conn, t, i)
        log.info("Watchlist %s %s %s (now %d items)", action, t, (p.get("label") or "")[:60], store.watchlist_count(conn))
        return jsonify({"ok": True})

    @app.post("/api/watchlist/update")
    def update():
        p = request.get_json(force=True, silent=True) or {}
        ok = store.update_item(conn, p.get("type", ""), p.get("id", ""), p.get("status"), p.get("notes"))
        return jsonify({"ok": ok}), (200 if ok else 404)

    @app.get("/api/free_versions")
    def free_versions():
        title = (request.args.get("title") or "").strip()
        if not title:
            return jsonify({"error": "no title"}), 400
        return jsonify(news.find_free_versions(title))

    return app


def run_server(app: Flask, port: int):
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)
