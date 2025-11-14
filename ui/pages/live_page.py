from PyQt6.QtCore import Qt, QThreadPool, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QGridLayout, QMessageBox, QSizePolicy

from utils.workers import FunctionWorker
from widgets.sparkline import Sparkline
import collections
import time


class LivePage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.pool = QThreadPool.globalInstance()
        self.timer = QTimer(self)
        # Lower update latency to 500ms
        self.timer.setInterval(500)
        self.timer.timeout.connect(self._tick)
        self._pending = False
        self._started = False
        # persistent rows storage: key -> {card, key_label, val_label, spark, buf, row}
        self._rows = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 24, 36, 24)
        outer.setSpacing(18)

        header = QLabel("Live Sensor Data")
        header.setObjectName("PageHeader")
        outer.addWidget(header)

        # NOTE: Large shared graph removed. Per-row sparklines are shown inline.

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        # make the grid more spacious
        self.grid.setContentsMargins(12, 10, 12, 10)
        self.grid.setHorizontalSpacing(20)
        self.grid.setVerticalSpacing(12)
        # Make three columns with weights: sensor name | value | sparkline (2:1:3)
        self.grid.setColumnStretch(0, 2)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnStretch(2, 3)
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
                    # timer started; per-row sparklines will be updated by _update
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
        # Update per-row widgets in-place. Create rows only when first seen.
        if not data:
            self.empty.show()
            return
        self.empty.hide()

        keys = sorted(data.keys())
        # Remove rows for keys that no longer exist
        to_remove = [k for k in self._rows.keys() if k not in keys]
        for k in to_remove:
            entry = self._rows.pop(k)
            # remove individual widgets
            for wname in ("key_label", "val_label", "spark"):
                w = entry.get(wname)
                if w:
                    w.deleteLater()

        row = 0
        for k in keys:
            v = data.get(k)
            if k not in self._rows:
                key_lbl = QLabel(str(k))
                key_lbl.setObjectName("KeyLabel")
                key_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                val_lbl = QLabel(str(v))
                val_lbl.setObjectName("ValueLabel")
                val_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
                spark = Sparkline(self)
                spark.setFixedHeight(48)
                spark.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

                # Add widgets directly into the page grid so columns align across rows
                self.grid.addWidget(key_lbl, row, 0)
                self.grid.addWidget(val_lbl, row, 1)
                self.grid.addWidget(spark, row, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                buf = collections.deque(maxlen=240)
                self._rows[k] = {"key_label": key_lbl, "val_label": val_lbl, "spark": spark, "buf": buf, "row": row}
            else:
                entry = self._rows[k]
                # Move widgets to the current row (preserve order)
                try:
                    self.grid.addWidget(entry["key_label"], row, 0)
                    self.grid.addWidget(entry["val_label"], row, 1)
                    self.grid.addWidget(entry["spark"], row, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                except Exception:
                    pass
                entry["val_label"].setText(str(v))

            # Try to parse numeric value for sparkline
            try:
                # strip units if present (e.g., "123.4 kPa")
                num = float(str(v).split()[0])
            except Exception:
                num = None

            if num is not None:
                entry = self._rows[k]
                entry["buf"].append(num)
                try:
                    entry["spark"].append(num)
                except Exception:
                    pass

            row += 1
