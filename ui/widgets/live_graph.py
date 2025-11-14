from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QLabel
from PyQt6.QtCore import QTimer, pyqtSignal
import collections
import time
import csv
import os

import pyqtgraph as pg


class LiveGraphWidget(QWidget):
    dataUpdated = pyqtSignal()
    seriesAdded = pyqtSignal(str)
    seriesRemoved = pyqtSignal(str)
    pausedChanged = pyqtSignal(bool)
    exportComplete = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, parent=None, max_history_seconds: int = 60, redraw_interval_ms: int = 500):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        # Controls row
        controls = QHBoxLayout()
        self.btn_pause = QPushButton("Pause")
        self.btn_clear = QPushButton("Clear")
        self.btn_export = QPushButton("Export CSV")
        controls.addWidget(self.btn_pause)
        controls.addWidget(self.btn_clear)
        controls.addWidget(self.btn_export)
        controls.addStretch(1)
        self.layout.addLayout(controls)

        # Plot area
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True)
        self.plot.addLegend(offset=(10, 10))
        self.layout.addWidget(self.plot)

        # Internal state
        self.max_history_seconds = max_history_seconds
        self.buffers = {}  # name -> {'t':deque, 'v':deque, 'curve':PlotDataItem, 'color':QColor}
        self.paused = False

        # Colors: use pyqtgraph default color generator
        self._color_index = 0

        # Redraw timer (controls how often we update the visual)
        self.redraw_timer = QTimer(self)
        self.redraw_timer.setInterval(redraw_interval_ms)
        self.redraw_timer.timeout.connect(self._redraw)
        self.redraw_timer.start()

        # Wire controls
        self.btn_pause.clicked.connect(self._toggle_pause)
        self.btn_clear.clicked.connect(self.clear)
        self.btn_export.clicked.connect(self._export_dialog)

    # ----------------
    # Series management
    # ----------------
    def add_series(self, name: str):
        if name in self.buffers:
            return
        # create ring buffers (deque) for timestamps and values
        dq_t = collections.deque()
        dq_v = collections.deque()
        color = pg.intColor(self._color_index)
        self._color_index += 1
        curve = self.plot.plot([], [], pen=color, name=name)
        self.buffers[name] = {"t": dq_t, "v": dq_v, "curve": curve, "color": color}
        self.seriesAdded.emit(name)

    def remove_series(self, name: str):
        if name not in self.buffers:
            return
        try:
            item = self.buffers[name]["curve"]
            self.plot.removeItem(item)
        except Exception:
            pass
        del self.buffers[name]
        self.seriesRemoved.emit(name)

    # ----------------
    # Data ingestion
    # ----------------
    def update(self, data: dict, timestamp: float = None):
        """Append new samples from `data` (mapping name->floatable)."""
        ts = timestamp if timestamp is not None else time.time()
        for k, raw_v in data.items():
            # convert to float where possible
            try:
                v = float(raw_v)
            except Exception:
                # ignore non-numeric samples
                continue
            if k not in self.buffers:
                self.add_series(k)
            buf = self.buffers[k]
            buf["t"].append(ts)
            buf["v"].append(v)
            # drop old samples beyond history window
            cutoff = ts - self.max_history_seconds
            while buf["t"] and buf["t"][0] < cutoff:
                buf["t"].popleft()
                buf["v"].popleft()

        # fire a lightweight signal (UI redraw controlled by timer)
        self.dataUpdated.emit()

    # ----------------
    # Rendering
    # ----------------
    def _redraw(self):
        if self.paused:
            return
        if not self.buffers:
            return
        # Plot each series; x axis use relative timestamps (seconds from now) for nicer scale
        now = time.time()
        for name, buf in self.buffers.items():
            ts = list(buf["t"]) if buf["t"] else []
            vs = list(buf["v"]) if buf["v"] else []
            if not ts:
                buf["curve"].setData([], [])
                continue
            # convert to relative times (seconds ago) or absolute - keep absolute for CSV but shift for plotting
            # We'll plot relative to now (seconds), newest at the right
            xs = [t - now for t in ts]
            buf["curve"].setData(xs, vs)

    # ----------------
    # Controls
    # ----------------
    def _toggle_pause(self):
        self.paused = not self.paused
        self.btn_pause.setText("Resume" if self.paused else "Pause")
        self.pausedChanged.emit(self.paused)

    def pause(self):
        if not self.paused:
            self._toggle_pause()

    def resume(self):
        if self.paused:
            self._toggle_pause()

    def clear(self, name: str = None):
        if name:
            if name in self.buffers:
                self.buffers[name]["t"].clear()
                self.buffers[name]["v"].clear()
        else:
            for k in list(self.buffers.keys()):
                self.buffers[k]["t"].clear()
                self.buffers[k]["v"].clear()

    # ----------------
    # Export
    # ----------------
    def _export_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", os.path.expanduser("~"), "CSV Files (*.csv)")
        if path:
            try:
                self.export_csv(path)
                self.exportComplete.emit(path)
            except Exception as e:
                self.error.emit(str(e))

    def export_csv(self, path: str):
        # Collect timestamps union, align by nearest timestamp per series
        # Simpler: use each series internal buffers and write columns as timestamp + value per series row-wise by index
        if not self.buffers:
            raise RuntimeError("No data to export")
        # Prepare header
        series_names = list(self.buffers.keys())
        # Find max length
        max_len = max(len(self.buffers[n]["t"]) for n in series_names)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = ["index", "timestamp"] + series_names
            writer.writerow(header)
            # Write rows by index; if a series is shorter, leave blank
            for i in range(max_len):
                # pick timestamp from first available series at index i or empty
                ts = ""
                for n in series_names:
                    if len(self.buffers[n]["t"]) > i:
                        ts = self.buffers[n]["t"][i]
                        break
                row = [i, ts]
                for n in series_names:
                    if len(self.buffers[n]["v"]) > i:
                        row.append(self.buffers[n]["v"][i])
                    else:
                        row.append("")
                writer.writerow(row)
