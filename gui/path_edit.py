from pathlib import Path

from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtGui import QPainter, QColor, QKeyEvent
from PySide6.QtWidgets import (
    QLineEdit, QStyle, QStyleOptionFrame, QListWidget, QListWidgetItem,
    QFrame,
)


_POPUP_MAX_ROWS = 8

_POPUP_QSS = """
QListWidget#pathPopup {
    background: #1c1e23;
    border: 1px solid #2a2d34;
    border-radius: 6px;
    color: #e6e7ea;
    padding: 4px;
    outline: 0;
    font-family: "Menlo", "Consolas", monospace;
    font-size: 12px;
}
QListWidget#pathPopup::item {
    padding: 5px 8px;
    border-radius: 4px;
    color: #c5c8cf;
}
QListWidget#pathPopup::item:hover {
    background: #22252b;
    color: #e6e7ea;
}
QListWidget#pathPopup::item:selected {
    background: #2f3441;
    color: #ffffff;
}
"""


class PathLineEdit(QLineEdit):
    """QLineEdit with ghost-text + dropdown directory completion.

    Tab / click accepts; Shift+Tab / Down/Up cycles.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._matches: list[str] = []
        self._stem: str = ""
        self._idx: int = 0
        self._in_focus_cycle: bool = False
        self._popup = QListWidget(None)
        self._popup.setObjectName("pathPopup")
        self._popup.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self._popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._popup.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._popup.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._popup.setFrameShape(QFrame.Shape.NoFrame)
        self._popup.setUniformItemSizes(True)
        self._popup.setStyleSheet(_POPUP_QSS)
        self._popup.itemClicked.connect(self._on_popup_clicked)
        self.textEdited.connect(self._recompute)
        self.cursorPositionChanged.connect(lambda _o, _n: self.update())

    def _recompute(self, text: str):
        self._matches, self._stem = self._collect(text)
        self._idx = 0
        self._refresh_popup()
        self.update()

    @staticmethod
    def _collect(text: str) -> tuple[list[str], str]:
        if not text:
            return [], ""
        try:
            p = Path(text).expanduser()
        except (OSError, ValueError):
            return [], ""
        if text.endswith("/") or text.endswith("\\"):
            parent, stem = p, ""
        else:
            parent, stem = p.parent, p.name
        try:
            if not parent.is_dir():
                return [], stem
            stem_l = stem.lower()
            matches = []
            for child in parent.iterdir():
                if not child.is_dir():
                    continue
                name = child.name
                if name.startswith("."):
                    continue
                if stem_l and not name.lower().startswith(stem_l):
                    continue
                matches.append(name)
        except (OSError, PermissionError):
            return [], stem
        matches.sort(key=str.lower)
        return matches, stem

    @property
    def _ghost(self) -> str:
        if not self._matches:
            return ""
        pick = self._matches[self._idx % len(self._matches)]
        return pick[len(self._stem):]

    def _accept(self) -> bool:
        if not self._matches:
            return False
        new_text = self.text() + self._ghost
        try:
            if Path(new_text).expanduser().is_dir() and not new_text.endswith(("/", "\\")):
                new_text += "/"
        except OSError:
            pass
        self.setText(new_text)
        self._matches, self._stem = self._collect(new_text)
        self._idx = 0
        self._refresh_popup()
        self.update()
        return True

    def _cycle(self, step: int) -> bool:
        if len(self._matches) <= 1:
            return False
        self._idx = (self._idx + step) % len(self._matches)
        self._popup.setCurrentRow(self._idx)
        self.update()
        return True

    def _refresh_popup(self):
        self._popup.clear()
        if not self._matches or not self.hasFocus():
            self._popup.hide()
            return
        for name in self._matches:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self._popup.addItem(item)
        self._popup.setCurrentRow(self._idx)
        self._position_popup()
        self._popup.show()
        self._popup.raise_()

    def _position_popup(self):
        gp = self.mapToGlobal(QPoint(0, self.height() + 2))
        rows = min(len(self._matches), _POPUP_MAX_ROWS)
        row_h = self._popup.sizeHintForRow(0) if self._popup.count() else 24
        h = rows * row_h + 10
        self._popup.setGeometry(gp.x(), gp.y(), self.width(), h)

    def _on_popup_clicked(self, item: QListWidgetItem):
        name = item.data(Qt.ItemDataRole.UserRole)
        if name is None:
            return
        try:
            self._idx = self._matches.index(name)
        except ValueError:
            return
        self._accept()
        self.setFocus()

    def event(self, e):
        if e.type() == QEvent.Type.KeyPress and isinstance(e, QKeyEvent):
            k = e.key()
            mod = e.modifiers()
            if k == Qt.Key.Key_Tab and not (mod & Qt.KeyboardModifier.ShiftModifier):
                if self._matches:
                    self._accept()
                e.accept()
                return True
            if k == Qt.Key.Key_Backtab or (k == Qt.Key.Key_Tab and mod & Qt.KeyboardModifier.ShiftModifier):
                if self._matches:
                    self._cycle(1)
                e.accept()
                return True
        return super().event(e)

    def keyPressEvent(self, e):
        if self._matches:
            if e.key() == Qt.Key.Key_Down:
                self._cycle(1)
                e.accept()
                return
            if e.key() == Qt.Key.Key_Up:
                self._cycle(-1)
                e.accept()
                return
            if e.key() in (Qt.Key.Key_Right, Qt.Key.Key_End):
                if self.cursorPosition() == len(self.text()):
                    if self._accept():
                        e.accept()
                        return
            if e.key() == Qt.Key.Key_Escape:
                self._matches = []
                self._popup.hide()
                self.update()
                e.accept()
                return
        super().keyPressEvent(e)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        if self._in_focus_cycle:
            return
        self._in_focus_cycle = True
        try:
            self._matches = []
            self._popup.hide()
            self.update()
        finally:
            self._in_focus_cycle = False

    def focusInEvent(self, e):
        super().focusInEvent(e)
        if self._in_focus_cycle:
            return
        self._in_focus_cycle = True
        try:
            self._matches, self._stem = self._collect(self.text())
            self._idx = 0
            self._refresh_popup()
            self.update()
        finally:
            self._in_focus_cycle = False

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._popup.isVisible():
            self._position_popup()

    def moveEvent(self, e):
        super().moveEvent(e)
        if self._popup.isVisible():
            self._position_popup()

    def paintEvent(self, e):
        super().paintEvent(e)
        ghost = self._ghost
        if not ghost or not self.hasFocus():
            return
        if self.cursorPosition() != len(self.text()):
            return

        opt = QStyleOptionFrame()
        self.initStyleOption(opt)
        content = self.style().subElementRect(
            QStyle.SubElement.SE_LineEditContents, opt, self
        )
        left = self.textMargins().left()
        top = self.textMargins().top()
        right = self.textMargins().right()
        content.adjust(left + 2, top, -right - 2, 0)

        fm = self.fontMetrics()
        typed_width = fm.horizontalAdvance(self.text())

        painter = QPainter(self)
        color = QColor(self.palette().text().color())
        color.setAlpha(110)
        painter.setPen(color)
        painter.setFont(self.font())
        x = content.left() + typed_width
        y = content.top() + (content.height() + fm.ascent() - fm.descent()) // 2
        available = content.right() - x
        if available <= 0:
            return
        drawn = fm.elidedText(ghost, Qt.TextElideMode.ElideRight, available)
        painter.drawText(x, y, drawn)
