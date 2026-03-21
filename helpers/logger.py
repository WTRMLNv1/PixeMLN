# helpers/logger.py
# Central logging setup for PixeMLN.
# Usage anywhere in the project:
#     from helpers.logger import get_logger
#     log = get_logger(__name__)
#     log.info("something happened")
#     log.warning("uh oh")
#     log.error("something broke", exc_info=True)   # exc_info=True attaches the traceback
# -----------------------------------------------------------------------------------------
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── resolve Data/ dir the same way json_manager does ──────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
_LOG_DIR  = BASE_DIR / "Data"
_LOG_FILE = _LOG_DIR / "pixemln.log"

_LOG_FORMAT  = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ── single flag so we only configure the root logger once ─────────────────────
_configured = False


def _configure():
    global _configured
    if _configured:
        return
    _configured = True

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("pixemln")
    root.setLevel(logging.DEBUG)

    # rotating file handler — 1 MB per file, keep 3 backups
    fh = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(fh)

    # console handler — INFO and above only so the terminal stays quiet
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(ch)

    root.info("Logger initialised — log file: %s", _LOG_FILE)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'pixemln' root.

    Pass __name__ so log lines show which module they came from.

    Example
    -------
        log = get_logger(__name__)
        log.info("user created: %s", username)
    """
    _configure()
    # Strip the project-root prefix so names stay short in the log file
    # e.g.  "helpers.json_manager"  instead of  "pixemln.helpers.json_manager"
    short = name.removeprefix("pixemln.")
    return logging.getLogger(f"pixemln.{short}")
