from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QGridLayout, QPushButton, QMessageBox

from ..utils.workers import FunctionWorker


class FreezePage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.pool = QThreadPool.globalInstance()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 24, 32, 24)
        outer.setSpacing(16)

        header = QLabel("Freeze Frame Data")
        header.setObjectName("PageHeader")
        outer.addWidget(header)
        # Removed manual refresh button; page auto-loads on activation

        self.loading = QLabel("Loading...")
        self.loading.setObjectName("LoadingText")
        outer.addWidget(self.loading)
        self.loading.hide()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(8)
        self.scroll.setWidget(self.container)
        outer.addWidget(self.scroll)

    def on_activated(self):
        self.load_once()

    def on_deactivated(self):
        pass

    def load_once(self):
        self.loading.show()
        worker = FunctionWorker(self.main.api.get_freeze)
        worker.signals.result.connect(self._update)
        worker.signals.error.connect(lambda e: QMessageBox.critical(self, "Freeze Frame Error", str(e)))
        worker.signals.finished.connect(lambda: self.loading.hide())
        self.pool.start(worker)

    def _update(self, data: dict):
        # Clear grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        if not data:
            self.grid.addWidget(QLabel("No data"), 0, 0)
            return
        row = 0
        for k, v in sorted(data.items()):
            card = QFrame()
            card.setObjectName("CardRow")
            gl = QGridLayout(card)
            gl.setContentsMargins(12, 8, 12, 8)
            key = QLabel(str(k))
            key.setObjectName("KeyLabel")
            val = QLabel(str(v))
            val.setObjectName("ValueLabel")
            gl.addWidget(key, 0, 0)
            gl.addWidget(val, 0, 1)

            self.grid.addWidget(card, row, 0)
            row += 1
