"""SQLite persistence (in the per-user data folder, see paths.py):
- watchlist: saved stories / new organizations, each with a lead status + notes
- npi_seen: when each new organization was first shown, for the "NEW" badge
- cache: the last NPI Registry result, reused between scans for a few hours
- settings: small key/value preferences"""
import datetime
import json
import sqlite3
import threading

_lock = threading.Lock()

STATUSES = ["New", "Researching", "Contacted", "Meeting set", "Pursuing", "Won", "Not a fit"]


def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS watchlist (
            item_type TEXT NOT NULL, item_id TEXT NOT NULL, label TEXT, snapshot TEXT,
            added_at TEXT, status TEXT DEFAULT 'New', notes TEXT DEFAULT '', updated_at TEXT,
            PRIMARY KEY (item_type, item_id));
        CREATE TABLE IF NOT EXISTS npi_seen (npi TEXT PRIMARY KEY, first_seen TEXT);
        CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, saved_at TEXT);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
    """)
    conn.commit()
    return conn


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def add_item(conn, item_type: str, item_id: str, label: str, snapshot: dict):
    with _lock:
        conn.execute(
            "INSERT INTO watchlist (item_type, item_id, label, snapshot, added_at, status, notes, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 'New', '', ?) "
            "ON CONFLICT(item_type, item_id) DO UPDATE SET label=excluded.label, snapshot=excluded.snapshot",
            (item_type, item_id, label, json.dumps(snapshot), _now(), _now()))
        conn.commit()


def remove_item(conn, item_type: str, item_id: str):
    with _lock:
        conn.execute("DELETE FROM watchlist WHERE item_type=? AND item_id=?", (item_type, item_id))
        conn.commit()


def update_item(conn, item_type: str, item_id: str, status: str = None, notes: str = None) -> bool:
    sets, args = [], []
    if status is not None:
        sets.append("status=?")
        args.append(status if status in STATUSES else "New")
    if notes is not None:
        sets.append("notes=?")
        args.append(notes[:4000])
    if not sets:
        return False
    with _lock:
        cur = conn.execute(f"UPDATE watchlist SET {', '.join(sets)}, updated_at=? WHERE item_type=? AND item_id=?",
                           (*args, _now(), item_type, item_id))
        conn.commit()
    return cur.rowcount > 0


def list_items(conn) -> list:
    with _lock:
        rows = conn.execute("SELECT item_type, item_id, label, snapshot, added_at, status, notes, updated_at "
                            "FROM watchlist ORDER BY added_at DESC").fetchall()
    return [{"type": r[0], "id": r[1], "label": r[2], "snapshot": json.loads(r[3] or "{}"), "added_at": r[4],
             "status": r[5] or "New", "notes": r[6] or "", "updated_at": r[7]} for r in rows]


def watchlisted_keys(conn) -> set:
    with _lock:
        rows = conn.execute("SELECT item_type, item_id FROM watchlist").fetchall()
    return {(r[0], r[1]) for r in rows}


def watchlist_count(conn) -> int:
    with _lock:
        return conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]


def mark_npis_seen(conn, npis: list) -> dict:
    """Records first-seen time for any new NPIs; returns {npi: first_seen} for all given."""
    now = _now()
    with _lock:
        conn.executemany("INSERT OR IGNORE INTO npi_seen (npi, first_seen) VALUES (?, ?)", [(n, now) for n in npis])
        conn.commit()
        seen = {}
        for i in range(0, len(npis), 500):
            chunk = npis[i:i + 500]
            q = "SELECT npi, first_seen FROM npi_seen WHERE npi IN (%s)" % ",".join("?" * len(chunk))
            seen.update(dict(conn.execute(q, chunk).fetchall()))
    return seen


def cache_get(conn, key: str):
    with _lock:
        row = conn.execute("SELECT value, saved_at FROM cache WHERE key=?", (key,)).fetchone()
    if not row:
        return None, None
    return json.loads(row[0]), datetime.datetime.fromisoformat(row[1])


def cache_put(conn, key: str, value):
    with _lock:
        conn.execute("INSERT OR REPLACE INTO cache (key, value, saved_at) VALUES (?, ?, ?)",
                     (key, json.dumps(value), _now()))
        conn.commit()


def get_setting(conn, key: str, default=None):
    with _lock:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_setting(conn, key: str, value: str):
    with _lock:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
