"""HLSA Scout desktop launcher: starts the local-only web server, and the
Scan Now button runs a scan and opens the report in your browser."""
import datetime as dt
import logging
import os
import sys
import threading
import time
import traceback
import webbrowser
import tkinter as tk
from tkinter import messagebox, scrolledtext

import applog
import paths

applog.setup(paths.log_dir())

import app_server  # noqa: E402  (after logging is set up)
import config  # noqa: E402
import diagnostics  # noqa: E402
import scan_runner  # noqa: E402
import store  # noqa: E402

log = logging.getLogger("hlsascout")

NAVY, NAVY_DARK, RED = config.NAVY, config.NAVY_DARK, config.RED
PANEL, TEXT, MUTED = "#26365A", "#F4F6FA", "#B9C4DA"


class App:
    def __init__(self, root):
        self.root = root
        root.title(f"{config.APP_NAME} v{config.APP_VERSION} — {config.APP_SUBTITLE}")
        root.geometry("780x580")
        root.configure(bg=NAVY)

        tk.Label(root, text=config.APP_NAME, font=("Segoe UI", 21, "bold"), fg=TEXT, bg=NAVY).pack(pady=(16, 0))
        tk.Label(root, text="Local healthcare business opportunities for HLSA's Trusted Referral Partners & NT Partnership\n"
                            "San Antonio · Bexar-adjacent counties · I-35 Corridor · Hill Country & rural ring",
                 font=("Segoe UI", 10), fg=MUTED, bg=NAVY, justify="center").pack(pady=(2, 4))
        tk.Label(root, text=f"Version {config.APP_VERSION} · {config.APP_VERSION_DATE}", font=("Segoe UI", 8),
                 fg=MUTED, bg=NAVY).pack(pady=(0, 10))

        self.scan_btn = tk.Button(root, text="Scan Now", font=("Segoe UI", 13, "bold"), bg=RED, fg="#fff",
                                  activebackground="#A8191F", activeforeground="#fff", relief="flat",
                                  padx=24, pady=9, command=self.start_scan)
        self.scan_btn.pack(pady=(0, 10))

        self.log_box = scrolledtext.ScrolledText(root, height=16, bg=PANEL, fg="#E3E8F2", insertbackground="#E3E8F2",
                                                 font=("Consolas", 9), relief="flat")
        self.log_box.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        self.log_box.configure(state="disabled")

        row = tk.Frame(root, bg=NAVY)
        row.pack(pady=(0, 6))
        for label, path in [("Scan Report", "/"), ("Opportunity Wire", "/wire"), ("New Organizations", "/orgs"),
                            ("Watchlist", "/watchlist"), ("About", "/about")]:
            tk.Button(row, text=label, font=("Segoe UI", 10), bg=PANEL, fg=TEXT, relief="flat", padx=10, pady=5,
                      command=lambda p=path: self.open_url(p)).pack(side="left", padx=3)
        row2 = tk.Frame(root, bg=NAVY)
        row2.pack(pady=(0, 12))
        for label, cmd in [("Copy Diagnostics", self.copy_diagnostics), ("Open Data Folder", self.open_data_folder)]:
            tk.Button(row2, text=label, font=("Segoe UI", 8), bg=NAVY, fg=MUTED, relief="flat", padx=8,
                      command=cmd).pack(side="left", padx=3)

        db, how = paths.db_path()
        self.conn = store.get_conn(db)
        applog.runtime.update(db_path=db, db_how=how)
        log.info("Started %s %s; database %s (%s)", config.APP_NAME, config.APP_VERSION, db, how)
        self.port = None
        self._start_server()
        self.log(f"Your watchlist is saved in: {db}")
        self.log("Click Scan Now to gather the latest opportunities (about a minute).")

    def _start_server(self):
        app = app_server.create_app(self.conn)
        self.port = app_server.find_free_port()
        applog.runtime["port"] = self.port
        threading.Thread(target=app_server.run_server, args=(app, self.port), daemon=True, name="server").start()
        self.log(f"Local server ready at http://127.0.0.1:{self.port}/ (this computer only)")

    def open_url(self, path):
        if self.port:
            webbrowser.open(f"http://127.0.0.1:{self.port}{path}")

    def log(self, msg: str):
        def append():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.root.after(0, append)

    def start_scan(self):
        self.scan_btn.configure(state="disabled", text="Scanning...")
        threading.Thread(target=self._run_scan, daemon=True, name="scan").start()

    def _run_scan(self):
        t0 = time.time()
        try:
            result = scan_runner.run_full_scan(self.conn, progress_cb=self.log, with_market=True)
            app_server.state.set_scan(result)
            applog.runtime["last_scan"] = {"finished": f"{dt.datetime.now():%Y-%m-%d %H:%M}", "ok": True,
                                           "seconds": round(time.time() - t0),
                                           "summary": f"{len(result['stories'])} stories, {len(result['orgs'])} orgs"}
            self.root.after(0, self._on_done)
        except Exception as e:
            log.exception("Scan failed")
            applog.runtime["last_scan"] = {"finished": f"{dt.datetime.now():%Y-%m-%d %H:%M}", "ok": False,
                                           "seconds": round(time.time() - t0), "summary": str(e)}
            self.log(f"ERROR: {e}")
            self.log(traceback.format_exc())
            self.root.after(0, self._on_error, str(e))

    def _on_done(self):
        self.scan_btn.configure(state="normal", text="Scan Now")
        self.open_url("/")

    def _on_error(self, msg):
        self.scan_btn.configure(state="normal", text="Scan Now")
        messagebox.showerror("Scan failed", f"Something went wrong:\n{msg}\n\nClick 'Copy Diagnostics' and send it along.")

    def copy_diagnostics(self):
        report = diagnostics.build_report(self.conn)
        self.root.clipboard_clear()
        self.root.clipboard_append(report)
        self.log("Diagnostics copied to the clipboard - paste it into an email or chat.")

    def open_data_folder(self):
        os.startfile(paths.data_dir())


def self_test():
    """`HLSAScout.exe --self-test`: one full scan with no window; result goes to the log."""
    db, how = paths.db_path()
    conn = store.get_conn(db)
    try:
        r = scan_runner.run_full_scan(conn, progress_cb=log.info, with_market=True)
        log.info("SELF-TEST OK: %d stories, %d organizations", len(r["stories"]), len(r["orgs"]))
    except Exception:
        log.exception("SELF-TEST FAILED")


def main():
    if "--self-test" in sys.argv:
        self_test()
        return
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
