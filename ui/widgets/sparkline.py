from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from collections import deque
import pyqtgraph as pg


class Sparkline(QWidget):
    """Minimal inline sparkline widget.

    API:
      - append(value: float)
      - clear()
      - setBufferSize(n: int)
    """

    def __init__(self, parent=None, buffer_size: int = 240, pen=None):
        super().__init__(parent)
        self._buffer_size = buffer_size
        self._buf = deque(maxlen=self._buffer_size)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.plot = pg.PlotWidget()
        # compact plot: no padding and small margins
        self.setContentsMargins(0, 0, 0, 0)
        self.plot.setMinimumWidth(120)
        self.plot.setMaximumWidth(220)
        self.plot.setBackground(None)
        self.plot.setMouseEnabled(x=False, y=False)
        # hide axes for a compact sparkline look
        try:
            self.plot.hideAxis('left')
            self.plot.hideAxis('bottom')
        except Exception:
            pass
        self.plot.setMenuEnabled(False)
        self.plot.showGrid(x=False, y=False)
        self._pen = pen or pg.mkPen(color=(120, 200, 255), width=1)
        self._curve = self.plot.plot([], [], pen=self._pen)

        self._layout.addWidget(self.plot)

    def append(self, value: float):
        try:
            self._buf.append(float(value))
        except Exception:
            return
        # Update curve with current buffer values
        try:
            self._curve.setData(list(self._buf))
        except Exception:
            pass

    def clear(self):
        self._buf.clear()
        try:
            self._curve.setData([])
        except Exception:
            pass

    def setBufferSize(self, n: int):
        if n == self._buffer_size:
            return
        # recreate buffer with new size, keep most recent values
        vals = list(self._buf)
        self._buffer_size = n
        self._buf = deque(vals[-n:], maxlen=n)
        try:
            self._curve.setData(list(self._buf))
        except Exception:
            pass
