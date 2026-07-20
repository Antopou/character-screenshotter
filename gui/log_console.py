from PySide6.QtGui import QFont
from PySide6.QtWidgets import QPlainTextEdit
from datetime import datetime


class LogConsole(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        f = QFont("Menlo, Monaco, monospace")
        f.setStyleHint(QFont.StyleHint.Monospace)
        f.setPointSize(11)
        self.setFont(f)
        self.setMaximumBlockCount(2000)

    def append_line(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        for line in msg.rstrip("\n").split("\n"):
            self.appendPlainText(f"{ts}  {line}")
