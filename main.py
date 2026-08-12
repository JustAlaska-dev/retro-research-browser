"""
Retro Research Browser - Stage 1
A Chromium-based browser with a 1960s TV/electronics aesthetic.

Stage 1 scope:
- Multi-tab browsing on real Chromium (QWebEngineView)
- Retro cream/walnut/brass chrome
- Toggleable CRT scanline overlay on the web view
- WEB / BOARD mode dial (BOARD is a placeholder in this stage)

Run with:  python main.py
"""

import sys
from PySide6.QtCore import Qt, QUrl, QRect
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QFont, QIcon, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLineEdit, QToolButton, QLabel, QPushButton,
    QStackedWidget, QFrame, QSizePolicy
)
from PySide6.QtWebEngineWidgets import QWebEngineView

# ---------------------------------------------------------------------------
# Palette - warm 1960s electronics: cream, walnut brown, brass/gold accents
# ---------------------------------------------------------------------------
COLOR_CREAM = "#f3e9d8"
COLOR_CREAM_DARK = "#e8dcc4"
COLOR_WALNUT = "#5b3a29"
COLOR_WALNUT_DARK = "#3f2a1d"
COLOR_BRASS = "#c9a24b"
COLOR_BRASS_LIGHT = "#e0c07a"
COLOR_TEXT_DARK = "#3a2b1e"
COLOR_SCREEN_BG = "#1c1c1c"

DEFAULT_HOME = "https://www.google.com"


class CRTOverlay(QWidget):
    """A transparent overlay widget that paints faint scanlines + a subtle
    vignette glow over whatever sits underneath it (the web view)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._enabled = False
        self.hide()

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if enabled:
            self.show()
            self.raise_()
        else:
            self.hide()
        self.update()

    def paintEvent(self, event):
        if not self._enabled:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # Scanlines
        line_color = QColor(0, 0, 0, 28)
        painter.setPen(line_color)
        y = 0
        while y < self.height():
            painter.drawLine(0, y, self.width(), y)
            y += 3

        # Vignette glow at edges
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(0, 0, 0, 40))
        gradient.setColorAt(0.08, QColor(0, 0, 0, 0))
        gradient.setColorAt(0.92, QColor(0, 0, 0, 0))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 40))
        painter.fillRect(self.rect(), gradient)

        painter.end()


class BrowserTab(QWidget):
    """A single browser tab: web view + CRT overlay stacked on top."""

    def __init__(self, url=DEFAULT_HOME, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView(self)
        self.web_view.setUrl(QUrl(url))

        self.crt_overlay = CRTOverlay(self.web_view)

        layout.addWidget(self.web_view)

        self.web_view.resizeEvent = self._wrap_resize(self.web_view.resizeEvent)

    def _wrap_resize(self, original_resize):
        def resize_event(event):
            original_resize(event)
            self.crt_overlay.setGeometry(0, 0, self.web_view.width(), self.web_view.height())
        return resize_event

    def set_crt_enabled(self, enabled: bool):
        self.crt_overlay.set_enabled(enabled)
        self.crt_overlay.setGeometry(0, 0, self.web_view.width(), self.web_view.height())


class ModeDial(QWidget):
    """A physical-feeling toggle between WEB and BOARD modes."""

    def __init__(self, on_change, parent=None):
        super().__init__(parent)
        self.on_change = on_change
        self.current_mode = "WEB"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        self.web_btn = QPushButton("WEB")
        self.board_btn = QPushButton("BOARD")

        for btn in (self.web_btn, self.board_btn):
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setMinimumWidth(70)

        self.web_btn.setChecked(True)
        self.web_btn.clicked.connect(lambda: self._select("WEB"))
        self.board_btn.clicked.connect(lambda: self._select("BOARD"))

        layout.addWidget(self.web_btn)
        layout.addWidget(self.board_btn)

        self._apply_style()

    def _select(self, mode):
        self.current_mode = mode
        self.web_btn.setChecked(mode == "WEB")
        self.board_btn.setChecked(mode == "BOARD")
        self._apply_style()
        self.on_change(mode)

    def _apply_style(self):
        base = f"""
            QPushButton {{
                background-color: {COLOR_CREAM_DARK};
                color: {COLOR_TEXT_DARK};
                border: 2px solid {COLOR_WALNUT};
                font-family: 'Georgia', serif;
                font-weight: bold;
                letter-spacing: 1px;
                font-size: 11px;
            }}
            QPushButton:checked {{
                background-color: {COLOR_BRASS};
                color: {COLOR_WALNUT_DARK};
                border: 2px solid {COLOR_BRASS_LIGHT};
            }}
            QPushButton:hover {{
                background-color: {COLOR_BRASS_LIGHT};
            }}
        """
        self.web_btn.setStyleSheet(base + "QPushButton { border-top-left-radius: 6px; border-bottom-left-radius: 6px; border-right: none; }")
        self.board_btn.setStyleSheet(base + "QPushButton { border-top-right-radius: 6px; border-bottom-right-radius: 6px; }")


class BoardPlaceholder(QWidget):
    """Placeholder for the Research Board, built in Stage 2."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("RESEARCH BOARD")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"""
            color: {COLOR_BRASS};
            font-family: 'Georgia', serif;
            font-size: 28px;
            font-weight: bold;
            letter-spacing: 4px;
        """)

        sub = QLabel("Coming in Stage 2 — the card canvas lives here")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"""
            color: {COLOR_CREAM_DARK};
            font-family: 'Georgia', serif;
            font-size: 13px;
        """)

        layout.addWidget(label)
        layout.addWidget(sub)
        self.setStyleSheet(f"background-color: {COLOR_WALNUT_DARK};")


class RetroBrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Retro Research Browser")
        self.resize(1280, 820)

        self.crt_enabled = False

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Top chrome bar ---
        chrome = QFrame()
        chrome.setFixedHeight(56)
        chrome.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_WALNUT};
                border-bottom: 3px solid {COLOR_BRASS};
            }}
        """)
        chrome_layout = QHBoxLayout(chrome)
        chrome_layout.setContentsMargins(10, 8, 10, 8)
        chrome_layout.setSpacing(8)

        nav_btn_style = f"""
            QToolButton {{
                background-color: {COLOR_CREAM_DARK};
                color: {COLOR_WALNUT_DARK};
                border: 2px solid {COLOR_BRASS};
                border-radius: 15px;
                font-weight: bold;
                font-size: 14px;
                min-width: 32px;
                min-height: 32px;
            }}
            QToolButton:hover {{
                background-color: {COLOR_BRASS_LIGHT};
            }}
            QToolButton:pressed {{
                background-color: {COLOR_BRASS};
            }}
        """

        self.back_btn = QToolButton()
        self.back_btn.setText("\u2190")
        self.back_btn.setStyleSheet(nav_btn_style)
        self.back_btn.clicked.connect(self.navigate_back)

        self.forward_btn = QToolButton()
        self.forward_btn.setText("\u2192")
        self.forward_btn.setStyleSheet(nav_btn_style)
        self.forward_btn.clicked.connect(self.navigate_forward)

        self.reload_btn = QToolButton()
        self.reload_btn.setText("\u27f3")
        self.reload_btn.setStyleSheet(nav_btn_style)
        self.reload_btn.clicked.connect(self.reload_page)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter a URL and press Enter\u2026")
        self.url_bar.returnPressed.connect(self.navigate_to_url_bar)
        self.url_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_CREAM};
                color: {COLOR_TEXT_DARK};
                border: 2px solid {COLOR_BRASS};
                border-radius: 14px;
                padding: 6px 14px;
                font-family: 'Georgia', serif;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLOR_BRASS_LIGHT};
                background-color: #fffdf7;
            }}
        """)

        self.new_tab_btn = QToolButton()
        self.new_tab_btn.setText("+")
        self.new_tab_btn.setStyleSheet(nav_btn_style)
        self.new_tab_btn.clicked.connect(lambda: self.add_new_tab())

        self.crt_toggle_btn = QToolButton()
        self.crt_toggle_btn.setText("CRT")
        self.crt_toggle_btn.setCheckable(True)
        self.crt_toggle_btn.setToolTip("Toggle CRT scanline overlay")
        self.crt_toggle_btn.clicked.connect(self.toggle_crt)
        self.crt_toggle_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: {COLOR_CREAM_DARK};
                color: {COLOR_WALNUT_DARK};
                border: 2px solid {COLOR_BRASS};
                border-radius: 8px;
                font-weight: bold;
                font-size: 11px;
                padding: 6px 10px;
            }}
            QToolButton:checked {{
                background-color: {COLOR_BRASS};
                color: {COLOR_WALNUT_DARK};
            }}
            QToolButton:hover {{
                background-color: {COLOR_BRASS_LIGHT};
            }}
        """)

        self.mode_dial = ModeDial(self.on_mode_change)

        chrome_layout.addWidget(self.back_btn)
        chrome_layout.addWidget(self.forward_btn)
        chrome_layout.addWidget(self.reload_btn)
        chrome_layout.addWidget(self.url_bar, stretch=1)
        chrome_layout.addWidget(self.new_tab_btn)
        chrome_layout.addWidget(self.crt_toggle_btn)
        chrome_layout.addSpacing(12)
        chrome_layout.addWidget(self.mode_dial)

        root_layout.addWidget(chrome)

        # --- Tab bar ---
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {COLOR_SCREEN_BG};
            }}
            QTabBar::tab {{
                background-color: {COLOR_CREAM_DARK};
                color: {COLOR_TEXT_DARK};
                font-family: 'Georgia', serif;
                font-size: 12px;
                padding: 8px 16px;
                border: 1px solid {COLOR_BRASS};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLOR_BRASS_LIGHT};
                color: {COLOR_WALNUT_DARK};
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background-color: {COLOR_BRASS};
            }}
        """)

        # --- Stacked view: WEB (tabs) vs BOARD (placeholder) ---
        self.stack = QStackedWidget()
        self.board_view = BoardPlaceholder()
        self.stack.addWidget(self.tabs)         # index 0 = WEB
        self.stack.addWidget(self.board_view)   # index 1 = BOARD

        root_layout.addWidget(self.stack, stretch=1)

        # Status-ish footer strip for a bit of retro flavor
        footer = QFrame()
        footer.setFixedHeight(22)
        footer.setStyleSheet(f"background-color: {COLOR_WALNUT}; border-top: 2px solid {COLOR_BRASS};")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 0, 10, 0)
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"color: {COLOR_CREAM_DARK}; font-family: 'Georgia', serif; font-size: 10px;")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()
        root_layout.addWidget(footer)

        # Overall window background
        central.setStyleSheet(f"background-color: {COLOR_SCREEN_BG};")

        # First tab
        self.add_new_tab(DEFAULT_HOME)

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------
    def add_new_tab(self, url=DEFAULT_HOME):
        tab = BrowserTab(url)
        tab.set_crt_enabled(self.crt_enabled)

        index = self.tabs.addTab(tab, "New Tab")
        self.tabs.setCurrentIndex(index)

        tab.web_view.urlChanged.connect(lambda qurl, t=tab: self.on_url_changed(t, qurl))
        tab.web_view.titleChanged.connect(lambda title, t=tab: self.on_title_changed(t, title))
        tab.web_view.loadStarted.connect(lambda: self.status_label.setText("Loading\u2026"))
        tab.web_view.loadFinished.connect(lambda ok: self.status_label.setText("Ready" if ok else "Failed to load"))

        return tab

    def close_tab(self, index):
        if self.tabs.count() <= 1:
            # keep at least one tab open; just reset it
            self.tabs.widget(0).web_view.setUrl(QUrl(DEFAULT_HOME))
            return
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        widget.deleteLater()

    def current_tab(self):
        return self.tabs.currentWidget()

    def on_tab_changed(self, index):
        tab = self.current_tab()
        if tab:
            self.url_bar.setText(tab.web_view.url().toString())

    def on_url_changed(self, tab, qurl):
        if tab is self.current_tab():
            self.url_bar.setText(qurl.toString())

    def on_title_changed(self, tab, title):
        index = self.tabs.indexOf(tab)
        if index != -1:
            display = title if title else "New Tab"
            if len(display) > 22:
                display = display[:22] + "\u2026"
            self.tabs.setTabText(index, display)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def navigate_to_url_bar(self):
        text = self.url_bar.text().strip()
        if not text:
            return
        if not text.startswith(("http://", "https://")):
            if "." in text and " " not in text:
                text = "https://" + text
            else:
                text = "https://www.google.com/search?q=" + text.replace(" ", "+")
        tab = self.current_tab()
        if tab:
            tab.web_view.setUrl(QUrl(text))

    def navigate_back(self):
        tab = self.current_tab()
        if tab:
            tab.web_view.back()

    def navigate_forward(self):
        tab = self.current_tab()
        if tab:
            tab.web_view.forward()

    def reload_page(self):
        tab = self.current_tab()
        if tab:
            tab.web_view.reload()

    # ------------------------------------------------------------------
    # CRT + Mode
    # ------------------------------------------------------------------
    def toggle_crt(self):
        self.crt_enabled = self.crt_toggle_btn.isChecked()
        for i in range(self.tabs.count()):
            self.tabs.widget(i).set_crt_enabled(self.crt_enabled)

    def on_mode_change(self, mode):
        if mode == "WEB":
            self.stack.setCurrentIndex(0)
        else:
            self.stack.setCurrentIndex(1)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Retro Research Browser")
    window = RetroBrowserWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
