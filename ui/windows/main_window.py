from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget,
    QLabel, QFrame, QMessageBox
)

from ..api_client import ApiClient
from ..pages.landing_page import LandingPage
from ..pages.dtc_page import DtcPage
from ..pages.live_page import LivePage
from ..pages.freeze_page import FreezePage
from ..pages.clear_page import ClearPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OBD++ Desktop")
        self.resize(1100, 720)

        self.api = ApiClient()
        self.connected = False

        # Central layout: side menu + stacked pages
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.menu = self._build_menu()
        root.addWidget(self.menu, 0)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        # Pages
        self.page_landing = LandingPage(self)
        self.page_dtc = DtcPage(self)
        self.page_live = LivePage(self)
        self.page_freeze = FreezePage(self)
        self.page_clear = ClearPage(self)

        self.stack.addWidget(self.page_landing)  # 0
        self.stack.addWidget(self.page_dtc)      # 1
        self.stack.addWidget(self.page_live)     # 2
        self.stack.addWidget(self.page_freeze)   # 3
        self.stack.addWidget(self.page_clear)    # 4

        self.setCentralWidget(central)

        # Start on landing
        self.goto_page(0)
        self._update_nav_state()

        # Menu actions
        self.btn_home.clicked.connect(lambda: self.goto_page(0))
        self.btn_dtc.clicked.connect(lambda: self.goto_page(1))
        self.btn_live.clicked.connect(lambda: self.goto_page(2))
        self.btn_freeze.clicked.connect(lambda: self.goto_page(3))
        self.btn_clear.clicked.connect(lambda: self.goto_page(4))

        # File -> Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        self.menuBar().addMenu("File").addAction(exit_action)

    def _build_menu(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("SideMenu")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(12)

        title = QLabel("OBD++")
        title.setObjectName("MenuTitle")
        layout.addWidget(title)

        self.btn_home = QPushButton("Home")
        self.btn_dtc = QPushButton("Read Codes")
        self.btn_live = QPushButton("Live Sensor Data")
        self.btn_freeze = QPushButton("Freeze Frame Data")
        self.btn_clear = QPushButton("Clear Codes")

        # Keep nav buttons in a list in the same order as stack pages
        self.nav_buttons = [self.btn_home, self.btn_dtc, self.btn_live, self.btn_freeze, self.btn_clear]

        for b in self.nav_buttons:
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setObjectName("NavButton")
            b.setCheckable(True)
            layout.addWidget(b)

        layout.addStretch(1)
        footer = QLabel("v1.0")
        footer.setObjectName("MenuFooter")
        layout.addWidget(footer)
        return frame

    def _update_nav_state(self):
        enabled = self.connected
        # Landing/Home always enabled
        self.btn_dtc.setEnabled(enabled)
        self.btn_live.setEnabled(enabled)
        self.btn_freeze.setEnabled(enabled)
        self.btn_clear.setEnabled(enabled)

    def set_connected(self, ok: bool):
        self.connected = ok
        self._update_nav_state()
        # Keep LandingPage controls in sync (connect/disconnect buttons & status)
        try:
            if hasattr(self, "page_landing") and self.page_landing:
                page = self.page_landing
                page.status.setText("Status: Connected" if ok else "Status: Disconnected")
                # Ensure buttons reflect connection state
                try:
                    page.btn_connect.setEnabled(not ok)
                except Exception:
                    pass
                try:
                    page.btn_disconnect.setEnabled(ok)
                except Exception:
                    pass
        except Exception:
            pass

    def goto_page(self, index: int):
        # Notify old page of deactivation if it supports it
        old_widget = self.stack.currentWidget()
        if hasattr(old_widget, "on_deactivated"):
            try:
                old_widget.on_deactivated()
            except Exception:
                pass

        self.stack.setCurrentIndex(index)
        w = self.stack.currentWidget()
        # update nav button checked state (nav_buttons list mirrors page indices)
        try:
            for i, b in enumerate(getattr(self, "nav_buttons", [])):
                b.setChecked(i == index)
        except Exception:
            pass
        if hasattr(w, "on_activated"):
            try:
                w.on_activated()
            except Exception as e:
                QMessageBox.warning(self, "Page Error", str(e))

    def closeEvent(self, event):
        # Best-effort: stop live and disconnect
        try:
            self.api.stop_live()
        except Exception:
            pass
        try:
            self.api.disconnect()
        except Exception:
            pass
        return super().closeEvent(event)
