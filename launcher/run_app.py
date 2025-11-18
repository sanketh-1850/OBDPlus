"""
Launcher that starts the FastAPI backend (uvicorn) in a background thread
then starts the PyQt UI in the main thread. When the UI exits the launcher
stops the backend and exits.

This script is written to be friendly for freezing with PyInstaller
(`--onedir --windowed`). It writes a timestamped log file to `logs/` and
shows simple console output if run from a terminal.
"""
import sys
import threading
import time
import logging
import os
from pathlib import Path

import requests

# Ensure project root is on sys.path and set as working directory so
# `import main` works both when running from source and when frozen by
# PyInstaller (sys._MEIPASS is used by PyInstaller to point to extracted files).
if getattr(sys, "_MEIPASS", None):
    project_root = Path(sys._MEIPASS)
else:
    # project root is the parent of the launcher folder
    project_root = Path(__file__).parent.parent.resolve()

# Insert project root at front of sys.path so module imports find project files
sys.path.insert(0, str(project_root))
# Also change cwd so uvicorn and other code resolve files relative to project root
try:
    os.chdir(project_root)
except Exception:
    pass

LOG_DIR = Path(__file__).parent.joinpath('logs')
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR.joinpath(f"obdplus-{time.strftime('%Y%m%d-%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('launcher')

# Redirect stdout/stderr to the same log file so double-click runs get captured.
try:
    _log_fh = open(log_file, mode="a", encoding="utf-8", buffering=1)  # line-buffered
    # Preserve original streams in case something needs them
    _orig_stdout = sys.stdout
    _orig_stderr = sys.stderr
    sys.stdout = _log_fh
    sys.stderr = _log_fh
except Exception:
    logger.exception("Failed to redirect stdout/stderr to log file")


def _global_excepthook(exc_type, exc_value, exc_tb):
    try:
        logger.exception("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
    except Exception:
        # If logging fails, fallback to original stderr
        try:
            _orig_stderr.write(f"Uncaught exception: {exc_type} {exc_value}\n")
        except Exception:
            pass


sys.excepthook = _global_excepthook


def start_uvicorn_in_thread(host='127.0.0.1', port=8000):
    """Start uvicorn programmatically in a background daemon thread."""
    try:
        import uvicorn
    except Exception as e:
        logger.exception("uvicorn is required to run the backend: %s", e)
        raise

    # Try to import the backend module so PyInstaller includes it in the bundle.
    # Also retrieve the ASGI app object to pass directly to uvicorn (more robust
    # than relying on string imports when frozen).
    try:
        import importlib
        main_mod = None
        try:
            main_mod = importlib.import_module("main")
        except Exception as e:
            logger.debug("importlib.import_module('main') failed: %s", e)
        app_obj = None
        if main_mod is not None:
            app_obj = getattr(main_mod, "app", None)
        if app_obj is None:
            # Try to locate a literal main.py file (useful when PyInstaller bundles it as data)
            try:
                import importlib.util
                main_path = None
                # prefer sys._MEIPASS when frozen
                if getattr(sys, "_MEIPASS", None):
                    candidate = Path(sys._MEIPASS) / "main.py"
                    if candidate.exists():
                        main_path = candidate
                # fallback to project root (project_root was set earlier)
                if main_path is None:
                    candidate = Path(__file__).parent.parent / "main.py"
                    if candidate.exists():
                        main_path = candidate
                if main_path is not None:
                    logger.info("Loading main.py from file: %s", main_path)
                    spec = importlib.util.spec_from_file_location("main", str(main_path))
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    app_obj = getattr(mod, "app", None)
                else:
                    logger.debug("No main.py file found to load directly")
            except Exception as e:
                logger.exception("Failed to load main.py from file: %s", e)
        if app_obj is None:
            logger.warning("Could not load app object from main; will fall back to import string 'main:app'")
            app_target = "main:app"
        else:
            app_target = app_obj
    except Exception:
        # If import fails here, fall back to the string — uvicorn will try to import it.
        app_target = "main:app"

    def _run():
        config = uvicorn.Config(app_target, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        # run() blocks until shutdown; run it here inside the thread
        logger.info("Starting uvicorn server thread")
        server.run()
        logger.info("Uvicorn server thread has exited")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


def wait_for_backend(url="http://127.0.0.1:8000/openapi.json", timeout=15):
    """Poll the backend until it responds or until timeout seconds elapse."""
    start = time.time()
    while True:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                logger.info("Backend is healthy")
                return True
        except Exception:
            pass
        if time.time() - start > timeout:
            logger.error("Backend did not become healthy within %s seconds", timeout)
            return False
        time.sleep(0.5)


def launch_ui():
    """Import and run the UI. The UI is expected to block until the user closes it."""
    logger.info("Launching UI (importing ui.app)")
    try:
        # Importing and calling the UI main function keeps everything in one
        # frozen executable (recommended for --onedir single-exe launcher).
        from ui import app as ui_app
        # ui.app should expose a `main()` function that runs the QApplication
        if hasattr(ui_app, 'main'):
            ui_app.main()
        else:
            # fallback: run as a module
            logger.info("ui.app has no main(); falling back to module run")
            import runpy
            runpy.run_module('ui.app', run_name='__main__')
    except Exception:
        logger.exception("Failed to start the UI")
        raise


def main():
    logger.info("Launcher starting")

    # Start backend
    try:
        server_thread = start_uvicorn_in_thread()
    except Exception:
        logger.error("Unable to start backend; aborting")
        return 2

    # Wait for backend readiness
    healthy = wait_for_backend()
    if not healthy:
        logger.error("Backend failed to start; see log %s", log_file)
        return 3

    # Launch UI in main thread; this will block until UI exits
    try:
        launch_ui()
    except Exception:
        logger.exception("UI crashed or exited with error")
    finally:
        logger.info("UI exited — attempting backend shutdown")
        # uvicorn server will normally stop when process exits; give a moment
        time.sleep(0.5)

    logger.info("Launcher exiting")
    return 0


if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
