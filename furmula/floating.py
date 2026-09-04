"""The desktop floating window (bottom-right pet) and its chrome.

Clicking the main body toggles sleeping/waiting (the controller decides when
that is legal); the bottom-right badge shows the current formula target
(LaTeX / Word). A right-click menu offers Settings / Quit.
"""
from PyQt5.QtCore import QEvent, QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from .animation import FrameStage
from .logging_setup import log_exc
from .theme import ERR, TEXT

BASE_WINDOW = 268      # 100% scale
MIN_WINDOW = 150
MAX_WINDOW = 480
MARGIN = 12            # gap from the work-area edge
DRAG_THRESHOLD = 6     # px of movement before a press becomes a drag


class ToastBalloon(QWidget):
    """Small auto-hiding message bubble that floats above the pet."""

    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        from PyQt5.QtCore import QTimer

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._label = QLabel(self)
        self._label.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.addWidget(self._label)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self._parent_anchor = None

    def show_message(self, anchor_widget, text, kind="info", ms=3500):
        try:
            if kind == "error":
                bg = QColor(ERR)
            else:
                bg = QColor(22, 46, 118, 240)   # deep-blue info bubble
            self._label.setStyleSheet(
                f"color: {TEXT}; background: transparent; font-size: 11px;"
            )
            self._label.setText(text)
            self.setStyleSheet(f"background: {bg.name()}; border-radius: 10px;")
            self.adjustSize()
            self._move_near(anchor_widget)
            self.show()
            self.raise_()
            self._timer.start(max(500, int(ms)))
        except Exception:
            log_exc("floating.toast")

    def _move_near(self, anchor_widget):
        if anchor_widget is None or not anchor_widget.isVisible():
            return
        pos = anchor_widget.mapToGlobal(QPoint(0, 0))
        w = self.width()
        x = pos.x() + (anchor_widget.width() - w) // 2
        y = pos.y() - self.height() - 8
        scr = QApplication.screenAt(anchor_widget.mapToGlobal(QPoint(0, 0)))
        if scr is None:
            scr = QApplication.primaryScreen()
        ag = scr.availableGeometry() if scr else None
        if ag is not None:
            x = max(ag.left() + 4, min(x, ag.right() - w - 4))
            y = max(ag.top() + 4, y)
        self.move(x, y)


class FloatingWindow(QWidget):
    toggle_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, library, parent=None):
        super().__init__(
            parent,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._library = library
        self._press_gpos: QPoint | None = None
        self._dragging = False
        self.setFixedSize(BASE_WINDOW, BASE_WINDOW)

        self.stage = FrameStage(library, self)
        self.stage.installEventFilter(self)

        # --- status pill (top-left) ----------------------------------- #
        self.pill = QLabel(self)
        self.pill.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.pill.setStyleSheet(
            "color: white; background: rgba(8,18,58,190); border-radius: 10px;"
            "padding: 2px 9px; font-size: 10.5px;"
        )
        self.pill.adjustSize()

        # --- bottom-right badge: current target ------------------------ #
        # a plain QLabel carries its own rounded background (same as the pill)
        self.badge = QLabel("LaTeX", self)
        self.badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.badge.setStyleSheet(
            "color: white; background: rgba(10,20,62,205); border-radius: 10px;"
            "padding: 2px 10px; font-size: 10.5px; font-weight: 600;"
        )
        self.badge.adjustSize()

        # right-click menu
        self._menu = QMenu(self)
        act_settings = self._menu.addAction("设置…")
        act_settings.triggered.connect(self.settings_requested)
        act_quit = self._menu.addAction("退出 Furmula")
        act_quit.triggered.connect(self.quit_requested)
        self._menu.setStyleSheet(
            "QMenu { background:#0C1A4D; color:white; border:1px solid #27429F;}"
            "QMenu::item:selected { background:#2E5BFF; }"
        )

        self.toast = ToastBalloon()
        self._set_pill("sleeping")
        self.stage.show_static("sleeping")  # initial picture before any toggle
        self.move_to_corner()

    # ---------------------------------------------------------------- #
    def eventFilter(self, obj, event):
        try:
            if obj is self.stage:
                t = event.type()
                if t == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                    self._press_gpos = event.globalPos()
                    self._dragging = False
                    return True
                if t == QEvent.MouseMove and event.buttons() & Qt.LeftButton:
                    if self._press_gpos is not None:
                        delta = event.globalPos() - self._press_gpos
                        if not self._dragging and delta.manhattanLength() >= DRAG_THRESHOLD:
                            self._dragging = True
                        if self._dragging:
                            self.move(self.pos() + delta)
                            self._press_gpos = event.globalPos()
                            return True
                if t == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                    if self._dragging:
                        self._dragging = False
                        self._press_gpos = None
                        return True          # dragged, not clicked
                    self._press_gpos = None
                    self.toggle_requested.emit()
                    return True
                if t == QEvent.ContextMenu:
                    self._menu.exec_(event.globalPos())
                    return True
        except Exception:
            log_exc("floating.eventFilter")
        return super().eventFilter(obj, event)

    def apply_visual(self, scale_pct: int, opacity_pct: int):
        """Apply the settings-driven window size (%) and opacity (%)."""
        scale_pct = max(50, min(200, int(scale_pct or 100)))
        size = round(BASE_WINDOW * scale_pct / 100)
        size = max(MIN_WINDOW, min(MAX_WINDOW, size))
        self.setFixedSize(size, size)
        op = max(15, min(100, int(opacity_pct or 100)))
        self.setWindowOpacity(op / 100.0)

    def _set_pill(self, state):
        text = {"sleeping": "闲 置 中", "waiting": "监 听 中", "working": "工 作 中"}.get(
            state, state
        )
        self.pill.setText(f"●  {text}")
        self.pill.adjustSize()
        self._place_pill()
        tip = {
            "sleeping": "闲置：不监听剪贴板\n单击切换为监听 · 按住拖动可移动 · 右键：设置/退出",
            "waiting": "监听：截图后自动识别为公式\n单击切换为闲置 · 按住拖动可移动 · 右键：设置/退出",
            "working": "工作中：正在识别公式…",
        }.get(state, "")
        self.setToolTip(tip)

    def set_status(self, state: str):
        """Update only the small status pill (working keeps the stage video)."""
        self._set_pill(state)

    def set_state(self, state: str):
        """Switch to an idle scene + matching status pill."""
        self._set_pill(state)
        if state == "sleeping":
            self.stage.show_static("sleeping")
        elif state == "waiting":
            self.stage.show_static("waiting")

    def set_target_text(self, target: str):
        label = {"latex": "LaTeX", "word": "Word"}.get(target, target)
        self.badge.setText(label)
        self.badge.adjustSize()
        self._place_badge()

    def play_once(self, clip_name: str):
        self.stage.play(clip_name, loop=False)

    def play_loop(self, clip_name: str):
        self.stage.play(clip_name, loop=True)

    def stage_stop_at_boundary(self):
        self.stage.stop_at_boundary()

    # ---------------------------------------------------------------- #
    def _place_pill(self):
        self.pill.move(10, 8)

    def _place_badge(self):
        self.badge.adjustSize()
        bw, bh = self.badge.width(), self.badge.height()
        self.badge.move(self.width() - bw - 10, self.height() - bh - 10)
        self.badge.raise_()

    def showEvent(self, event):
        super().showEvent(event)
        self.stage.setGeometry(0, 0, self.width(), self.height())
        self._place_pill()
        self._place_badge()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.stage.setGeometry(0, 0, self.width(), self.height())
        self._place_pill()
        self._place_badge()

    # ---------------------------------------------------------------- #
    def move_to_corner(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        ag = screen.availableGeometry()
        self.move(ag.right() - self.width() - MARGIN, ag.bottom() - self.height() - MARGIN)

    def show_toast(self, text: str, kind="info", ms=3500):
        self.toast.show_message(self, text, kind, ms)

    def closeEvent(self, event):
        self.toast.close()
        super().closeEvent(event)
