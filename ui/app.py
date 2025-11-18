import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QFile, QTextStream
from PyQt6.QtGui import QIcon
import base64
import os
import sys as _sys

try:
    # Preferred when `ui` is imported as a package (e.g. `from ui import app`).
    from .windows.main_window import MainWindow
except Exception:
    # Fallback for running `python ui/app.py` directly during development.
    # Use absolute package import which works when the parent package is on sys.path.
    from ui.windows.main_window import MainWindow


def load_stylesheet(app: QApplication, path: str):
    """Load a stylesheet file. If `path` is relative, resolve it relative to this module (ui/).
    This function preprocesses CSS-like custom properties declared as
    `--name: value;` and replaces `var(--name)` occurrences because Qt's
    QSS doesn't support CSS custom properties.
    Print a simple warning if loading fails so issues are visible during development.
    """
    try:
        # Resolve relative paths relative to this file (ui/)
        if not os.path.isabs(path):
            base = os.path.dirname(__file__)  # ui/
            path = os.path.normpath(os.path.join(base, path))

        if not os.path.exists(path):
            print(f"Warning: stylesheet not found: {path}", file=_sys.stderr)
            return

        # Read raw stylesheet text
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()

        # Extract simple --name: value; declarations and substitute var(--name)
        import re
        vars_map = {}
        for m in re.finditer(r'--([\w-]+)\s*:\s*([^;]+);', raw):
            vars_map[m.group(1).strip()] = m.group(2).strip()

        def _replace_var(match):
            key = match.group(1)
            return vars_map.get(key, match.group(0))

        processed = re.sub(r'var\(--([\w-]+)\)', _replace_var, raw)

        # Remove the original custom-property declarations since QSS doesn't support them
        processed = re.sub(r'--[\w-]+\s*:\s*[^;]+;\s*', '', processed)

        # Remove any `transition:` properties (not supported by QSS)
        processed = re.sub(r'transition\s*:\s*[^;]+;\s*', '', processed)

        # Remove properties unsupported by Qt QSS that appear in the stylesheet
        # e.g., transform and box-shadow are common CSS properties not supported by QSS.
        processed = re.sub(r'box-shadow\s*:\s*[^;]+;\s*', '', processed, flags=re.IGNORECASE)
        processed = re.sub(r'transform\s*:\s*[^;]+;\s*', '', processed, flags=re.IGNORECASE)
        # Also remove vendor-prefixed variants and any remaining common unsupported props
        processed = re.sub(r'-webkit-box-shadow\s*:\s*[^;]+;\s*', '', processed, flags=re.IGNORECASE)
        processed = re.sub(r'-webkit-transform\s*:\s*[^;]+;\s*', '', processed, flags=re.IGNORECASE)
        app.setStyleSheet(processed)
    except Exception as e:
        print(f"Error loading stylesheet {path}: {e}", file=_sys.stderr)


def main():
    app = QApplication(sys.argv)
    # Load the stylesheet relative to this file (ui/resources/style.qss)
    load_stylesheet(app, os.path.join("resources", "style.qss"))

    # Ensure an app icon exists. We ship a small base64 placeholder in `assets/app_icon.b64`.
    # Compute assets path relative to ui/ (one level up -> assets)
    assets_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets"))
    b64_path = os.path.join(assets_dir, "app_icon.b64")
    png_path = os.path.join(assets_dir, "app_icon.png")
    ico_path = os.path.join(assets_dir, "OBD-Port.ico")
    try:
        # Prefer existing ICO on Windows (if present)
        if os.path.exists(ico_path):
            app.setWindowIcon(QIcon(ico_path))
        else:
            # If we have a base64 placeholder, decode it to png and use it
            if os.path.exists(b64_path) and not os.path.exists(png_path):
                with open(b64_path, "r", encoding="utf-8") as f:
                    b64 = f.read().strip()
                with open(png_path, "wb") as out:
                    out.write(base64.b64decode(b64))
            if os.path.exists(png_path):
                app.setWindowIcon(QIcon(png_path))
            else:
                print(f"Warning: no app icon found in {assets_dir}", file=_sys.stderr)
    except Exception as e:
        print(f"Error setting application icon: {e}", file=_sys.stderr)

    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
