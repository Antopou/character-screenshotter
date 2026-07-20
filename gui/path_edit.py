from pathlib import Path

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPainter, QColor, QKeyEvent
from PySide6.QtWidgets import QLineEdit, QStyle, QStyleOptionFrame


class PathLineEdit(QLineEdit):
    """QLineEdit with inline ghost-text directory completion. Tab accepts."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ghost = ""
        self.textEdited.connect(self._recompute_ghost)
        self.textChanged.connect(lambda _: self.update())

    def _recompute_ghost(self, text: str):
        self._ghost = self._suggest(text)
        self.update()

    @staticmethod
    def _suggest(text: str) -> str:
        if not text:
            return ""
        try:
            p = Path(text).expanduser()
        except (OSError, ValueError):
            return ""
        if text.endswith("/") or text.endswith("\\"):
            return ""
        parent, stem = p.parent, p.name
        if not stem:
            return ""
        try:
            if not parent.is_dir():
                return ""
            stem_l = stem.lower()
            matches = []
            for child in parent.iterdir():
                if not child.is_dir():
                    continue
                name = child.name
                if name.startswith("."):
                    continue
                if not name.lower().startswith(stem_l):
                    continue
                matches.append(name)
        except (OSError, PermissionError):
            return ""
        if not matches:
            return ""
        matches.sort(key=str.lower)
        pick = matches[0]
        return pick[len(stem):] if stem else pick

    def _accept_ghost(self) -> bool:
        if not self._ghost:
            return False
        new_text = self.text() + self._ghost
        p = Path(new_text).expanduser()
        try:
            if p.is_dir() and not new_text.endswith(("/", "\\")):
                new_text += "/"
        except OSError:
            pass
        self.setText(new_text)
        self._ghost = self._suggest(new_text)
        self.update()
        return True

    def event(self, e):
        if e.type() == QEvent.Type.KeyPress and isinstance(e, QKeyEvent):
            if e.key() == Qt.Key.Key_Tab and self._ghost:
                if self._accept_ghost():
                    e.accept()
                    return True
        return super().event(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Right, Qt.Key.Key_End) and self._ghost:
            if self.cursorPosition() == len(self.text()):
                if self._accept_ghost():
                    e.accept()
                    return
        if e.key() == Qt.Key.Key_Escape and self._ghost:
            self._ghost = ""
            self.update()
            e.accept()
            return
        super().keyPressEvent(e)

    def focusOutEvent(self, e):
        self._ghost = ""
        self.update()
        super().focusOutEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        if not self._ghost or not self.hasFocus():
            return

        opt = QStyleOptionFrame()
        self.initStyleOption(opt)
        content = self.style().subElementRect(
            QStyle.SubElement.SE_LineEditContents, opt, self
        )
        left, top, right = self.textMargins().left(), self.textMargins().top(), self.textMargins().right()
        content.adjust(left + 2, top, -right - 2, 0)

        fm = self.fontMetrics()
        typed = self.text()
        typed_width = fm.horizontalAdvance(typed)

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
        ghost = fm.elidedText(self._ghost, Qt.TextElideMode.ElideRight, available)
        painter.drawText(x, y, ghost)
