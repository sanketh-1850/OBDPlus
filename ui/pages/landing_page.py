from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox

from utils.workers import FunctionWorker


class LandingPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.pool = QThreadPool.globalInstance()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        header = QLabel("Home")
        header.setObjectName("PageHeader")
        layout.addWidget(header)

        sub = QLabel("Connect to your OBD-II adapter to begin.")
        sub.setObjectName("SubHeader")
        layout.addWidget(sub)

        self.status = QLabel("Status: Disconnected")
        self.status.setObjectName("StatusText")
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("PrimaryButton")
        self.btn_connect.clicked.connect(self._on_connect)
        buttons.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setObjectName("DangerButton")
        self.btn_disconnect.clicked.connect(self._on_disconnect)
        self.btn_disconnect.setEnabled(False)
        buttons.addWidget(self.btn_disconnect)

        layout.addLayout(buttons)
        layout.addStretch(1)

        # Small status / loading label for connect/disconnect operations
        self.loading = QLabel("")
        self.loading.setObjectName("LoadingText")
        layout.addWidget(self.loading)

    def _on_connect(self):
        self.btn_connect.setEnabled(False)
        self.loading.setText("Connecting...")
        self.loading.show()
        worker = FunctionWorker(self.main.api.connect)
        worker.signals.result.connect(self._connected)
        worker.signals.error.connect(self._connect_error)
        def _finished():
            # finished: hide loading; enable connect only if still disconnected
            self.loading.hide()
            if not self.main.connected:
                self.btn_connect.setEnabled(True)

        worker.signals.finished.connect(_finished)
        self.pool.start(worker)

    def _on_disconnect(self):
        self.btn_disconnect.setEnabled(False)
        self.loading.setText("Disconnecting...")
        self.loading.show()
        worker = FunctionWorker(self.main.api.disconnect)
        worker.signals.result.connect(self._disconnected)
        worker.signals.error.connect(lambda e: QMessageBox.critical(self, "Disconnect Error", str(e)))
        def _finished_disconnect():
            self.loading.hide()
            # if still connected, re-enable disconnect button
            if self.main.connected:
                self.btn_disconnect.setEnabled(True)

        worker.signals.finished.connect(_finished_disconnect)
        self.pool.start(worker)

    def _connected(self, res: dict):
        status = res.get("status")
        ok = status == "connected" or status == "already_connected"
        self.main.set_connected(ok)
        if ok:
            self.status.setText("Status: Connected")
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self.loading.hide()
        else:
            self.status.setText(f"Status: {status or 'Failed'}")
            QMessageBox.warning(self, "Connect", "Failed to connect to OBD adapter. Ensure server is running and adapter is available.")
            self.loading.hide()

    def _connect_error(self, e: Exception):
        self.status.setText("Status: Error")
        QMessageBox.critical(self, "Connect Error", str(e))
        try:
            self.loading.hide()
        except Exception:
            pass

    def _disconnected(self, res: dict):
        status = res.get("status")
        ok = status == "disconnected"
        self.main.set_connected(False)
        self.status.setText("Status: Disconnected" if ok else f"Status: {status}")
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        try:
            self.loading.hide()
        except Exception:
            pass
