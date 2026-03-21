# main.py
# Run this file

from helpers.logger import get_logger

log = get_logger(__name__)

if __name__ == "__main__":
    try:
        from ui.UI import UI
        ui = UI()
        ui.run()
    except Exception:
        log.critical("Unhandled exception — PixeMLN crashed", exc_info=True)
        raise
