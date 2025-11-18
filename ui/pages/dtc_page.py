from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QHBoxLayout,
    QMessageBox, QDialog, QDialogButtonBox, QGridLayout, QTextBrowser
)

from ..utils.workers import FunctionWorker


class DtcPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.pool = QThreadPool.globalInstance()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 24, 32, 24)
        outer.setSpacing(16)

        header = QLabel("Read Codes")
        header.setObjectName("PageHeader")
        outer.addWidget(header)

        # Controls
        controls = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh Codes")
        self.btn_refresh.setObjectName("PrimaryButton")
        self.btn_refresh.clicked.connect(self.load_codes)
        controls.addWidget(self.btn_refresh)
        controls.addStretch(1)
        outer.addLayout(controls)

        # Scroll list
        # Page-level loading indicator
        self.loading = QLabel("Loading...")
        self.loading.setObjectName("LoadingText")
        outer.addWidget(self.loading)
        self.loading.hide()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.list_container)
        outer.addWidget(self.scroll)

    # Page lifecycle
    def on_activated(self):
        self.load_codes()

    def on_deactivated(self):
        pass

    def load_codes(self):
        self.btn_refresh.setEnabled(False)
        # show page-level loading indicator
        try:
            self.loading.show()
        except Exception:
            pass
        # Clear existing items (except stretch)
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        worker = FunctionWorker(self.main.api.get_dtc)
        worker.signals.result.connect(self._populate_codes)
        worker.signals.error.connect(lambda e: QMessageBox.critical(self, "DTC Error", str(e)))

        def _finished():
            self.btn_refresh.setEnabled(True)
            try:
                self.loading.hide()
            except Exception:
                pass

        worker.signals.finished.connect(_finished)
        self.pool.start(worker)

    def _populate_codes(self, codes):
        # Normalize backend response and handle "no codes" case with a simple message.
        # Expected payload is a list of [code, description] pairs, but be defensive.

        # Clear any existing widgets except the trailing stretch.
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # If backend returned a string like "No codes found", treat as empty.
        if isinstance(codes, str):
            codes = []

        # If backend returned None or empty list, show centered message only.
        if not codes:
            label = QLabel("No DTC codes found.")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setObjectName("EmptyStateText")
            self.list_layout.insertWidget(0, label)
            return

        # Otherwise, render each real code/description pair as a card.
        for pair in codes:
            card = self._code_card(pair)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

    def _code_card(self, pair):
        code = pair[0] if len(pair) > 0 else ""
        desc = pair[1] if len(pair) > 1 else ""

        frame = QFrame()
        frame.setObjectName("Card")
        grid = QGridLayout(frame)
        grid.setContentsMargins(16, 12, 16, 12)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)

        lbl_code = QLabel(code)
        lbl_code.setObjectName("CodeLabel")
        lbl_desc = QLabel(desc)
        lbl_desc.setObjectName("DescLabel")

        btn = QPushButton("Explain with AI")
        btn.setObjectName("SecondaryButton")
        btn.clicked.connect(lambda: self._explain(code))

        grid.addWidget(QLabel("Code:"), 0, 0)
        grid.addWidget(lbl_code, 0, 1)
        grid.addWidget(QLabel("Description:"), 1, 0)
        grid.addWidget(lbl_desc, 1, 1)
        grid.addWidget(btn, 0, 2, 2, 1)

        return frame

    def _explain(self, code: str):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Explain {code}")
        dlg.resize(900, 700)

        layout = QVBoxLayout(dlg)
        # Dialog title inside content (larger, styled via QSS)
        dlg_title = QLabel(code)
        dlg_title.setObjectName("DialogTitle")
        layout.addWidget(dlg_title)

        text = QTextBrowser()
        text.setObjectName("ExplainText")
        text.setOpenExternalLinks(True)
        # Show loading text and a short note about expected duration
        text.setHtml("<i>Loading...</i>")
        # larger default text for readability
        try:
            text.setStyleSheet("font-size:13pt;")
        except Exception:
            pass
        spinner = QLabel("Loading... ")
        spinner.setObjectName("LoadingText")
        note = QLabel("Note: AI explanation can take up to 70 seconds.")
        note.setObjectName("SubHeader")
        layout.addWidget(spinner)
        layout.addWidget(note)
        layout.addWidget(text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)

        def _clean_html_candidate(html_candidate: str, res: dict) -> str:
            """
            If html_candidate contains the unwanted generic message,
            replace it with a clearer message using backend error info.
            """
            if not html_candidate:
                return ""
            lowered = html_candidate.lower()
            generic_phrases = [
                "sorry this feature is not available currently",
                "this feature is not available",
                "feature is not available"
            ]
            if any(phrase in lowered for phrase in generic_phrases):
                # Prefer backend-provided error message if available
                exp = res.get("explanation") if isinstance(res, dict) else None
                if isinstance(exp, dict) and exp.get("error"):
                    return f"<b>Explain service returned an error:</b><br><pre>{exp.get('error')}</pre>"
                # Fallback: show a clear short message plus raw response for debugging
                return "<b>Explanation currently unavailable.</b><br><pre>{}</pre>".format(
                    res if isinstance(res, dict) else str(res)
                )
            return html_candidate

        def on_result(res: dict):
            # If the dialog has been closed by the user, ignore late results
            if not dlg.isVisible():
                return
            # stop spinner
            try:
                timer.stop()
            except Exception:
                pass
            spinner.hide()
            # main.py returns { code, freeze_frame, explanation }
            # explanation may itself be a dict with 'explanation' or HTML string
            html = None
            exp = res.get("explanation")
            if isinstance(exp, dict):
                html = exp.get("explanation") or exp.get("html") or exp.get("error") or str(exp)
            elif isinstance(exp, str):
                html = exp
            if not html:
                html = f"<pre>{res}</pre>"

            # Clean or replace generic message if present
            safe_html = _clean_html_candidate(html, res)
            text.setHtml(safe_html)

        def on_error(exc):
            # Ignore errors if dialog closed
            if not dlg.isVisible():
                return
            try:
                timer.stop()
            except Exception:
                pass
            spinner.hide()
            # Show a concise friendly message plus the low-level error details as preformatted text
            text.setHtml(f"<b>Explain failed.</b><br><pre>{exc}</pre>")

        worker = FunctionWorker(self.main.api.explain_code, code)
        worker.signals.result.connect(on_result)
        worker.signals.error.connect(on_error)
        self.pool.start(worker)

        # simple animated dots for spinner
        timer = QTimer(dlg)
        dots = {"n": 0}

        def _tick():
            dots["n"] = (dots["n"] + 1) % 4
            spinner.setText("Loading" + "." * dots["n"])

        timer.timeout.connect(_tick)
        timer.start(350)

        # stop timer when dialog closes
        dlg.finished.connect(lambda: timer.stop())

        dlg.exec()
