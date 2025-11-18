from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox

from ..utils.workers import FunctionWorker


class ClearPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.pool = QThreadPool.globalInstance()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        header = QLabel("Clear Codes")
        header.setObjectName("PageHeader")
        layout.addWidget(header)

        info = QLabel("This will clear active DTCs from the ECU.")
        layout.addWidget(info)

        self.btn_clear = QPushButton("Clear DTCs Now")
        self.btn_clear.setObjectName("DangerButton")
        self.btn_clear.clicked.connect(self.clear_now)
        layout.addWidget(self.btn_clear)

        self.result = QLabel("")
        self.result.setObjectName("ResultText")
        layout.addWidget(self.result)
        self.loading = QLabel("Clearing...")
        self.loading.setObjectName("LoadingText")
        layout.addWidget(self.loading)
        self.loading.hide()
        layout.addStretch(1)

    def on_activated(self):
        # Removed auto-clear to prevent unintended DTC wiping.
        self.result.setText("Ready to clear codes.")

    def on_deactivated(self):
        pass

    def clear_now(self):
        self.btn_clear.setEnabled(False)
        self.loading.show()
        worker = FunctionWorker(self.main.api.clear_codes)
        worker.signals.result.connect(self._show_result)
        worker.signals.error.connect(lambda e: QMessageBox.critical(self, "Clear Error", str(e)))
        def _done():
            self.btn_clear.setEnabled(True)
            self.loading.hide()
        worker.signals.finished.connect(_done)
        self.pool.start(worker)

    def _show_result(self, res: dict):
        # Backend returns {"result": <string>}
        msg = res.get("result") if isinstance(res, dict) else str(res)
        self.result.setText(msg or "Done.")
