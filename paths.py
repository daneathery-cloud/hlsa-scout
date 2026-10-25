"""Where HLSA Scout keeps its data: a fixed per-user folder
(%LOCALAPPDATA%\\HLSAScout), never next to the exe - so copying, zipping or
replacing the program with a newer version can't lose the watchlist."""
import os
import sys

DB_NAME = "hlsascout.db"


def exe_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def data_dir() -> str:
    """HLSASCOUT_DATA_DIR overrides it (for testing). Falls back to the exe's
    folder if the per-user folder can't be written."""
    base = os.environ.get("HLSASCOUT_DATA_DIR")
    if not base:
        local = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        base = os.path.join(local, "HLSAScout")
    try:
        os.makedirs(base, exist_ok=True)
        probe = os.path.join(base, ".write_test")
        with open(probe, "w"):
            pass
        os.remove(probe)
        return base
    except OSError:
        return exe_dir()


def log_dir() -> str:
    path = os.path.join(data_dir(), "logs")
    os.makedirs(path, exist_ok=True)
    return path


def db_path() -> tuple:
    """(path, 'existing' | 'created new (empty)')."""
    db = os.path.join(data_dir(), DB_NAME)
    return db, ("existing" if os.path.exists(db) else "created new (empty)")
