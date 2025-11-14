from PyQt6.QtCore import Qt, QThreadPool, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QGridLayout, QMessageBox

from utils.workers import FunctionWorker


class LivePage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.pool = QThreadPool.globalInstance()
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)
        self._pending = False
        self._started = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 24, 32, 24)
        outer.setSpacing(16)

        header = QLabel("Live Sensor Data")
        header.setObjectName("PageHeader")
        outer.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(8)
        self.scroll.setWidget(self.container)
        outer.addWidget(self.scroll)

        self.empty = QLabel("Waiting for live data...")
        outer.addWidget(self.empty)
        self.empty.hide()

        self.starting_label = QLabel("Starting live stream...")
        self.starting_label.setObjectName("LoadingText")
        outer.addWidget(self.starting_label)
        self.starting_label.hide()

    # Page lifecycle
    def on_activated(self):
        if not self._started:
            # Start live on background worker to avoid blocking the UI
            self._started = None  # starting
            self.starting_label.show()
            worker = FunctionWorker(self.main.api.start_live)

            def _on_started(res: dict):
                status = res.get("status") if isinstance(res, dict) else None
                if status == "started":
                    self._started = True
                    self.timer.start()
                    self.starting_label.hide()
                else:
                    self._started = False
                    self.starting_label.hide()
                    QMessageBox.warning(self, "Live Start", f"Failed to start live: {res}")

            worker.signals.result.connect(_on_started)
            worker.signals.error.connect(lambda e: QMessageBox.critical(self, "Live Start Error", str(e)))
            self.pool.start(worker)
        else:
            # Already started previously; ensure timer is running
            if self._started:
                self.timer.start()

    def on_deactivated(self):
        # Stop polling timer immediately, then request backend to stop in background
        self.timer.stop()
        if self._started:
            worker = FunctionWorker(self.main.api.stop_live)
            worker.signals.result.connect(lambda res: setattr(self, "_started", False))
            worker.signals.error.connect(lambda e: None)
            self.pool.start(worker)

    def _tick(self):
        if self._pending:
            return
        self._pending = True
        worker = FunctionWorker(self.main.api.get_live_data)
        worker.signals.result.connect(self._update)
        worker.signals.error.connect(lambda e: None)
        worker.signals.finished.connect(lambda: setattr(self, "_pending", False))
        self.pool.start(worker)

    def _update(self, data: dict):
        # Clear grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        if not data:
            self.empty.show()
            return
        self.empty.hide()
        row = 0
        for k, v in sorted(data.items()):
            key = QLabel(str(k))
            key.setObjectName("KeyLabel")
            val = QLabel(str(v))
            val.setObjectName("ValueLabel")

            card = QFrame()
            card.setObjectName("CardRow")
            gl = QGridLayout(card)
            gl.setContentsMargins(12, 8, 12, 8)
            gl.addWidget(key, 0, 0)
            gl.addWidget(val, 0, 1)

            self.grid.addWidget(card, row, 0, 1, 1)
            row += 1
