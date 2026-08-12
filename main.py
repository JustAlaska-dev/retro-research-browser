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
import math
import json
import os
import uuid
from datetime import datetime
from PySide6.QtCore import Qt, QUrl, QRect, QEvent, QTimer, QPointF, QMimeData
from PySide6.QtGui import (
    QPainter, QColor, QLinearGradient, QFont, QIcon, QAction, QPainterPath, QDrag
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLineEdit, QToolButton, QLabel, QPushButton,
    QStackedWidget, QFrame, QSizePolicy, QScrollArea, QTextEdit,
    QMenu, QInputDialog, QMessageBox, QGraphicsDropShadowEffect
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

CARD_MIME = "application/x-retro-board-card"
BOARD_DATA_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "research_board_data.json"
)


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

        # Scanlines - tighter spacing, darker + a faint bright sibling line
        # underneath each dark one, which is what sells the "phosphor row"
        # look on a real CRT instead of a plain stripe pattern.
        dark_line = QColor(0, 0, 0, 70)
        bright_line = QColor(255, 255, 255, 8)
        y = 0
        while y < self.height():
            painter.setPen(dark_line)
            painter.drawLine(0, y, self.width(), y)
            painter.setPen(bright_line)
            painter.drawLine(0, y + 1, self.width(), y + 1)
            y += 2

        # Deeper vignette glow at edges, top/bottom
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(0, 0, 0, 95))
        gradient.setColorAt(0.14, QColor(0, 0, 0, 0))
        gradient.setColorAt(0.86, QColor(0, 0, 0, 0))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 95))
        painter.fillRect(self.rect(), gradient)

        # Matching vignette left/right so the darkening reads like a curved
        # tube rather than just top/bottom bars
        h_gradient = QLinearGradient(0, 0, self.width(), 0)
        h_gradient.setColorAt(0.0, QColor(0, 0, 0, 70))
        h_gradient.setColorAt(0.10, QColor(0, 0, 0, 0))
        h_gradient.setColorAt(0.90, QColor(0, 0, 0, 0))
        h_gradient.setColorAt(1.0, QColor(0, 0, 0, 70))
        painter.fillRect(self.rect(), h_gradient)

        painter.end()


class RedPandaMascot(QWidget):
    """A small illustrated red panda that pops into the bottom corner on
    first load, waves for a bit, and fades away on the user's first click
    anywhere in the app."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(150, 150)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._phase = 0.0
        self._opacity = 1.0
        self._scale = 0.0          # pop-in scale
        self._exiting = False

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start(30)

    # -- animation ----------------------------------------------------
    def _on_tick(self):
        self._phase += 0.12

        if self._scale < 1.0:
            self._scale = min(1.0, self._scale + 0.08)

        if self._exiting:
            self._opacity -= 0.07
            if self._opacity <= 0:
                self._opacity = 0.0
                self._tick_timer.stop()
                self.hide()

        self.update()

    def start_exit(self):
        if not self._exiting:
            self._exiting = True

    # -- drawing --------------------------------------------------------
    def paintEvent(self, event):
        if self._opacity <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setOpacity(self._opacity)

        w, h = self.width(), self.height()
        bob = math.sin(self._phase) * 3

        painter.translate(w / 2, h - 12 + bob)
        painter.scale(self._scale, self._scale)

        rust = QColor("#b5502e")
        rust_dark = QColor("#8e3d22")
        cream = QColor(COLOR_CREAM)
        dark = QColor("#2e2118")

        # Tail, curled behind the body with a few rings
        tail_path = QPainterPath()
        tail_path.moveTo(18, -20)
        tail_path.cubicTo(55, -20, 60, -70, 30, -78)
        tail_path.cubicTo(10, -83, -2, -65, 18, -55)
        tail_path.cubicTo(30, -48, 25, -30, 10, -30)
        tail_path.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(rust)
        painter.drawPath(tail_path)
        painter.setBrush(cream)
        painter.drawEllipse(QPointF(38, -60), 6, 6)
        painter.drawEllipse(QPointF(20, -40), 5, 5)

        # Feet
        painter.setBrush(rust_dark)
        painter.drawEllipse(QPointF(-16, -8), 11, 8)
        painter.drawEllipse(QPointF(14, -8), 11, 8)

        # Body
        painter.setBrush(rust)
        painter.drawRoundedRect(QRect(-26, -58, 52, 52), 24, 24)
        painter.setBrush(cream)
        painter.drawEllipse(QPointF(0, -28), 14, 16)

        # Non-waving arm, resting on the body
        painter.setBrush(rust)
        painter.drawEllipse(QPointF(-22, -32), 8, 12)

        # Waving arm (rotates about the shoulder)
        wave_angle = 25 + math.sin(self._phase * 2.6) * 30
        painter.save()
        painter.translate(22, -50)
        painter.rotate(-wave_angle)
        painter.setBrush(rust)
        painter.drawRoundedRect(QRect(-7, 0, 14, 30), 7, 7)
        painter.setBrush(cream)
        painter.drawEllipse(QPointF(0, 30), 8, 8)
        painter.restore()

        # Head
        head_center = QPointF(0, -78)
        painter.setBrush(rust)
        painter.drawEllipse(head_center, 30, 27)

        # Ears
        painter.setBrush(rust_dark)
        painter.drawEllipse(QPointF(-22, -98), 10, 10)
        painter.drawEllipse(QPointF(22, -98), 10, 10)
        painter.setBrush(cream)
        painter.drawEllipse(QPointF(-22, -96), 5, 5)
        painter.drawEllipse(QPointF(22, -96), 5, 5)

        # Face mask
        painter.setBrush(cream)
        painter.drawEllipse(QPointF(0, -70), 22, 18)

        # Eye patches + eyes
        painter.setBrush(rust_dark)
        painter.drawEllipse(QPointF(-11, -76), 7, 9)
        painter.drawEllipse(QPointF(11, -76), 7, 9)
        painter.setBrush(dark)
        painter.drawEllipse(QPointF(-10, -74), 3, 3.5)
        painter.drawEllipse(QPointF(10, -74), 3, 3.5)

        # Nose + mouth
        painter.setBrush(dark)
        painter.drawEllipse(QPointF(0, -64), 3.5, 2.5)
        pen = painter.pen()
        painter.setPen(QColor(dark))
        painter.drawArc(QRect(-6, -63, 12, 10), 200 * 16, 140 * 16)
        painter.setPen(pen)

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


class BoardCardWidget(QFrame):
    """A single card on the board - a saved page or a typed note.

    Cards are dragged by pressing anywhere on their body except the
    delete button (and, for notes, the text editor itself). We roll our
    own mouse-based drag/drop rather than QListWidget's built-in item
    dragging, since that mechanism is unreliable once custom item
    widgets are involved.
    """

    def __init__(self, card, board, parent=None):
        super().__init__(parent)
        self.card = card          # dict: id, type, title/url or text, created
        self.board = board        # back-reference to ResearchBoard
        self._drag_start = None
        self.setFrameShape(QFrame.NoFrame)
        self.setCursor(Qt.OpenHandCursor)
        self.setMinimumWidth(190)

        is_page = card["type"] == "page"
        accent = COLOR_BRASS if is_page else "#8fae7d"

        self.setStyleSheet(f"""
            BoardCardWidget {{
                background-color: {'#fffdf7' if is_page else '#fbf3d9'};
                border: 1px solid {COLOR_BRASS};
                border-left: 5px solid {accent};
                border-radius: 4px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 110))
        self.setGraphicsEffect(shadow)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 8, 10)
        outer.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(4)
        kind_label = QLabel("PAGE" if is_page else "NOTE")
        kind_label.setStyleSheet(
            f"color: {COLOR_WALNUT}; font-family: 'Georgia', serif; "
            "font-size: 9px; font-weight: bold; letter-spacing: 1px; "
            "border: none; background: transparent;"
        )
        header.addWidget(kind_label)
        header.addStretch()

        del_btn = QPushButton("\u00d7")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setFixedSize(18, 18)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLOR_WALNUT};
                border: none;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ color: #a33; }}
        """)
        del_btn.clicked.connect(self._delete_self)
        header.addWidget(del_btn)
        outer.addLayout(header)

        if is_page:
            title = QLabel(card.get("title") or "(untitled page)")
            title.setWordWrap(True)
            title.setStyleSheet(
                f"color: {COLOR_TEXT_DARK}; font-family: 'Georgia', serif; "
                "font-size: 12px; font-weight: bold; border: none; background: transparent;"
            )
            outer.addWidget(title)

            url_label = QLabel(card.get("url", ""))
            url_label.setWordWrap(True)
            url_label.setStyleSheet(
                f"color: {COLOR_WALNUT}; font-family: 'Georgia', serif; "
                "font-size: 10px; border: none; background: transparent;"
            )
            outer.addWidget(url_label)

            open_hint = QLabel("click to open \u2197")
            open_hint.setStyleSheet(
                f"color: {COLOR_BRASS}; font-family: 'Georgia', serif; "
                "font-size: 9px; font-style: italic; border: none; background: transparent;"
            )
            outer.addWidget(open_hint)
        else:
            self.editor = QTextEdit()
            self.editor.setPlainText(card.get("text", ""))
            self.editor.setPlaceholderText("Type a note\u2026")
            self.editor.setFrameShape(QFrame.NoFrame)
            self.editor.setStyleSheet(f"""
                QTextEdit {{
                    background: transparent;
                    color: {COLOR_TEXT_DARK};
                    font-family: 'Georgia', serif;
                    font-size: 12px;
                    border: none;
                }}
            """)
            self.editor.document().documentLayout().documentSizeChanged.connect(
                self._adjust_note_height
            )
            self.editor.textChanged.connect(self._on_note_changed)
            outer.addWidget(self.editor)
            self._adjust_note_height()

    # -- sizing for notes ------------------------------------------------
    def _adjust_note_height(self, *args):
        doc_h = self.editor.document().size().height()
        h = max(70, min(int(doc_h) + 16, 240))
        self.editor.setFixedHeight(h)

    def _on_note_changed(self):
        self.card["text"] = self.editor.toPlainText()
        self.board.save()

    # -- deletion ----------------------------------------------------------
    def _delete_self(self):
        self.board.delete_card(self.card["id"])

    # -- drag handling -----------------------------------------------------
    def mousePressEvent(self, event):
        child = self.childAt(event.pos())
        if isinstance(child, (QPushButton, QTextEdit)):
            super().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is None or not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(CARD_MIME, self.card["id"].encode("utf-8"))
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(event.position().toPoint())
        self._drag_start = None
        self.hide()
        drag.exec(Qt.MoveAction)
        self.show()

    def mouseReleaseEvent(self, event):
        was_plain_click = self._drag_start is not None
        self._drag_start = None
        if was_plain_click and self.card["type"] == "page" and event.button() == Qt.LeftButton:
            child = self.childAt(event.pos())
            if not isinstance(child, QPushButton):
                self.board.open_card(self.card["id"])
        super().mouseReleaseEvent(event)


class CardStack(QWidget):
    """Vertical stack of cards inside one column. Accepts drops to
    reorder cards within the column, or to receive a card dragged in
    from another column."""

    def __init__(self, column_id, board, parent=None):
        super().__init__(parent)
        self.column_id = column_id
        self.board = board
        self.setAcceptDrops(True)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(8, 8, 8, 8)
        self.layout_.setSpacing(10)
        self.layout_.addStretch()

    def card_widgets(self):
        widgets = []
        for i in range(self.layout_.count() - 1):  # last item is the stretch
            item = self.layout_.itemAt(i)
            if item and item.widget():
                widgets.append(item.widget())
        return widgets

    def rebuild(self, cards):
        while self.layout_.count():
            item = self.layout_.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for card in cards:
            self.layout_.addWidget(BoardCardWidget(card, self.board))
        self.layout_.addStretch()

    def _index_for_y(self, y):
        for i, w in enumerate(self.card_widgets()):
            mid = w.y() + w.height() / 2
            if y < mid:
                return i
        return len(self.card_widgets())

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(CARD_MIME):
            return
        card_id = bytes(event.mimeData().data(CARD_MIME)).decode("utf-8")
        index = self._index_for_y(event.position().toPoint().y())
        self.board.move_card(card_id, self.column_id, index)
        event.acceptProposedAction()


class BoardColumnWidget(QFrame):
    """One column/group on the corkboard: a renamable title, a
    scrollable stack of cards, and a button to drop a fresh note in."""

    def __init__(self, column, board, parent=None):
        super().__init__(parent)
        self.column = column
        self.board = board
        self.setFixedWidth(260)
        self.setStyleSheet(f"""
            BoardColumnWidget {{
                background-color: {COLOR_WALNUT};
                border: 2px solid {COLOR_BRASS};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QHBoxLayout()
        self.name_edit = QLineEdit(column["name"])
        self.name_edit.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                color: {COLOR_CREAM};
                font-family: 'Georgia', serif;
                font-size: 13px;
                font-weight: bold;
                border: none;
                padding: 2px;
            }}
            QLineEdit:focus {{
                background-color: {COLOR_WALNUT_DARK};
                border-radius: 4px;
            }}
        """)
        self.name_edit.editingFinished.connect(self._rename)
        header.addWidget(self.name_edit, stretch=1)

        del_col_btn = QPushButton("\u00d7")
        del_col_btn.setFixedSize(20, 20)
        del_col_btn.setCursor(Qt.PointingHandCursor)
        del_col_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {COLOR_CREAM_DARK};
                border: none; font-weight: bold; font-size: 14px;
            }}
            QPushButton:hover {{ color: #e07a5f; }}
        """)
        del_col_btn.clicked.connect(self._delete_column)
        header.addWidget(del_col_btn)
        layout.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(f"background-color: {COLOR_WALNUT_DARK}; border-radius: 6px;")
        self.stack = CardStack(column["id"], board)
        self.stack.setStyleSheet(f"background-color: {COLOR_WALNUT_DARK};")
        self.scroll.setWidget(self.stack)
        layout.addWidget(self.scroll, stretch=1)

        add_note_btn = QPushButton("+ Note")
        add_note_btn.setCursor(Qt.PointingHandCursor)
        add_note_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_CREAM_DARK};
                color: {COLOR_WALNUT_DARK};
                border: 2px solid {COLOR_BRASS};
                border-radius: 6px;
                font-family: 'Georgia', serif;
                font-weight: bold;
                padding: 5px;
            }}
            QPushButton:hover {{ background-color: {COLOR_BRASS_LIGHT}; }}
        """)
        add_note_btn.clicked.connect(lambda: self.board.add_note_card(column["id"]))
        layout.addWidget(add_note_btn)

        self.refresh()

    def refresh(self):
        self.stack.rebuild(self.column["cards"])

    def _rename(self):
        self.column["name"] = self.name_edit.text().strip() or "Untitled"
        self.board.save()

    def _delete_column(self):
        if self.board.column_count() <= 1:
            return
        confirm = QMessageBox.question(
            self, "Delete column",
            f"Delete \u201c{self.column['name']}\u201d and its {len(self.column['cards'])} card(s)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self.board.delete_column(self.column["id"])


class ResearchBoard(QWidget):
    """Stage 2 research board: columns/groups of cards (saved pages +
    typed notes), corkboard-style, persisted to a small JSON file
    beside the app so the board survives restarts."""

    def __init__(self, open_url_callback, parent=None):
        super().__init__(parent)
        self.open_url_callback = open_url_callback
        self.setStyleSheet(f"background-color: {COLOR_WALNUT_DARK};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(12, 10, 12, 4)
        title = QLabel("RESEARCH BOARD")
        title.setStyleSheet(
            f"color: {COLOR_BRASS}; font-family: 'Georgia', serif; "
            "font-size: 16px; font-weight: bold; letter-spacing: 3px;"
        )
        toolbar.addWidget(title)
        toolbar.addStretch()
        add_col_btn = QPushButton("+ Column")
        add_col_btn.setCursor(Qt.PointingHandCursor)
        add_col_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_BRASS};
                color: {COLOR_WALNUT_DARK};
                border-radius: 6px;
                font-family: 'Georgia', serif;
                font-weight: bold;
                padding: 6px 12px;
            }}
            QPushButton:hover {{ background-color: {COLOR_BRASS_LIGHT}; }}
        """)
        add_col_btn.clicked.connect(self.add_column)
        toolbar.addWidget(add_col_btn)
        outer.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(f"background-color: {COLOR_WALNUT_DARK};")
        self.columns_container = QWidget()
        self.columns_layout = QHBoxLayout(self.columns_container)
        self.columns_layout.setContentsMargins(12, 6, 12, 12)
        self.columns_layout.setSpacing(12)
        self.columns_layout.addStretch()
        self.scroll.setWidget(self.columns_container)
        outer.addWidget(self.scroll, stretch=1)

        self.data = self._load()
        self._render_all()

    # -- persistence ---------------------------------------------------
    def _load(self):
        if os.path.exists(BOARD_DATA_FILE):
            try:
                with open(BOARD_DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("columns"):
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return {"columns": [{"id": str(uuid.uuid4()), "name": "Inbox", "cards": []}]}

    def save(self):
        try:
            with open(BOARD_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except OSError:
            pass

    # -- rendering -------------------------------------------------------
    def _render_all(self):
        while self.columns_layout.count():
            item = self.columns_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for column in self.data["columns"]:
            self.columns_layout.addWidget(BoardColumnWidget(column, self))
        self.columns_layout.addStretch()
        self.save()

    # -- column ops --------------------------------------------------------
    def column_count(self):
        return len(self.data["columns"])

    def column_names(self):
        return [(c["id"], c["name"]) for c in self.data["columns"]]

    def add_column(self):
        name, ok = QInputDialog.getText(self, "New column", "Column name:", text="New Group")
        if not ok:
            return
        self.data["columns"].append({
            "id": str(uuid.uuid4()),
            "name": name.strip() or "Untitled",
            "cards": [],
        })
        self._render_all()

    def delete_column(self, column_id):
        self.data["columns"] = [c for c in self.data["columns"] if c["id"] != column_id]
        self._render_all()

    def _find_column(self, column_id):
        for c in self.data["columns"]:
            if c["id"] == column_id:
                return c
        return None

    # -- card ops ------------------------------------------------------
    def add_page_card(self, column_id, title, url):
        column = self._find_column(column_id)
        if not column:
            return
        column["cards"].insert(0, {
            "id": str(uuid.uuid4()),
            "type": "page",
            "title": title or url,
            "url": url,
            "created": datetime.now().isoformat(timespec="seconds"),
        })
        self._render_all()

    def add_note_card(self, column_id):
        column = self._find_column(column_id)
        if not column:
            return
        column["cards"].insert(0, {
            "id": str(uuid.uuid4()),
            "type": "note",
            "text": "",
            "created": datetime.now().isoformat(timespec="seconds"),
        })
        self._render_all()

    def delete_card(self, card_id):
        for column in self.data["columns"]:
            column["cards"] = [c for c in column["cards"] if c["id"] != card_id]
        self._render_all()

    def move_card(self, card_id, target_column_id, index):
        source_card = None
        for column in self.data["columns"]:
            for c in list(column["cards"]):
                if c["id"] == card_id:
                    source_card = c
                    column["cards"].remove(c)
                    break
            if source_card:
                break
        if not source_card:
            return
        target = self._find_column(target_column_id)
        if not target:
            return
        index = max(0, min(index, len(target["cards"])))
        target["cards"].insert(index, source_card)
        self._render_all()

    def open_card(self, card_id):
        for column in self.data["columns"]:
            for c in column["cards"]:
                if c["id"] == card_id and c["type"] == "page":
                    self.open_url_callback(c["url"])
                    return


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

        self.save_page_btn = QToolButton()
        self.save_page_btn.setText("SAVE")
        self.save_page_btn.setToolTip("Save the current page to the Research Board")
        self.save_page_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: {COLOR_CREAM_DARK};
                color: {COLOR_WALNUT_DARK};
                border: 2px solid {COLOR_BRASS};
                border-radius: 8px;
                font-weight: bold;
                font-size: 11px;
                padding: 6px 10px;
            }}
            QToolButton:hover {{
                background-color: {COLOR_BRASS_LIGHT};
            }}
            QToolButton:pressed {{
                background-color: {COLOR_BRASS};
            }}
        """)
        self.save_page_btn.clicked.connect(self.save_current_page_to_board)

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
        chrome_layout.addWidget(self.save_page_btn)
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

        # --- Stacked view: WEB (tabs) vs BOARD ---
        self.stack = QStackedWidget()
        self.board_view = ResearchBoard(self.open_url_from_board)
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

        # --- Red panda mascot: pops in on first load, waves, then fades
        # out the moment the user clicks anywhere in the app ---
        self.panda_mascot = RedPandaMascot(central)
        self._position_panda_mascot()
        self.panda_mascot.show()
        self.panda_mascot.raise_()
        QApplication.instance().installEventFilter(self)

    def _position_panda_mascot(self):
        central = self.centralWidget()
        margin = 18
        x = central.width() - self.panda_mascot.width() - margin
        y = central.height() - self.panda_mascot.height() - margin
        self.panda_mascot.move(max(0, x), max(0, y))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "panda_mascot"):
            self._position_panda_mascot()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and hasattr(self, "panda_mascot"):
            if self.panda_mascot.isVisible():
                self.panda_mascot.start_exit()
            QApplication.instance().removeEventFilter(self)
        return super().eventFilter(obj, event)

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
    # Research board integration
    # ------------------------------------------------------------------
    def open_url_from_board(self, url):
        """Open a saved research page in a new browser tab."""
        if not url:
            return
        self.add_new_tab(url)
        self.mode_dial._select("WEB")

    def save_current_page_to_board(self):
        """Save the active web page into a selected research-board column."""
        tab = self.current_tab()
        if not tab:
            return

        url = tab.web_view.url().toString().strip()
        title = tab.web_view.title().strip() or url

        if not url or url in ("about:blank", ""):
            QMessageBox.information(
                self, "Nothing to save",
                "Open a web page before saving it to the Research Board."
            )
            return

        columns = self.board_view.column_names()
        if not columns:
            return

        names = [name for _, name in columns]
        selected, ok = QInputDialog.getItem(
            self, "Save to Research Board",
            "Choose a column:", names, 0, False
        )
        if not ok:
            return

        column_id = columns[names.index(selected)][0]

        # Avoid accidentally creating a pile of identical cards.
        for column in self.board_view.data["columns"]:
            for card in column.get("cards", []):
                if card.get("type") == "page" and card.get("url") == url:
                    QMessageBox.information(
                        self, "Already saved",
                        f"This page is already on the Research Board in “{column.get('name', 'Untitled')}”."
                    )
                    self.mode_dial._select("BOARD")
                    return

        self.board_view.add_page_card(column_id, title, url)
        self.status_label.setText("Saved to Research Board")
        self.mode_dial._select("BOARD")

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
