#!/usr/bin/env python3
"""
Screenshotter — Desktop GUI (PySide6)

Modern flat-design window with sidebar navigation. Wraps frame_extractor
and character_detector so all video-processing logic stays shared with the CLI/TUI.
"""

import sys

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QStackedWidget, QProgressBar, QFrame, QListWidget,
        QListWidgetItem, QSplitter,
    )
except ImportError:
    print("Missing dependency: PySide6", file=sys.stderr)
    print("Install with:  uv pip install PySide6", file=sys.stderr)
    sys.exit(1)

import frame_extractor
import character_detector
from gui.extract_page import ExtractPage
from gui.detect_page import DetectPage
from gui.worker import GuiWorker
from gui.log_console import LogConsole


DARK_QSS = """
QMainWindow, QWidget { background: #1e1e1e; color: #e8e8e8; }
QGroupBox {
    border: 1px solid #333; border-radius: 8px; margin-top: 12px; padding: 12px;
    font-weight: 600;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #ccc; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {
    background: #2a2a2a; border: 1px solid #3a3a3a; border-radius: 4px;
    padding: 4px 6px; color: #e8e8e8;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #0078d4;
}
QPushButton {
    background: #2f2f2f; border: 1px solid #444; border-radius: 4px;
    padding: 6px 14px; color: #e8e8e8;
}
QPushButton:hover { background: #3a3a3a; }
QPushButton:disabled { color: #777; }
QListWidget {
    background: #262626; border: 1px solid #333; border-radius: 4px;
}
QProgressBar {
    background: #2a2a2a; border: 1px solid #333; border-radius: 4px;
    text-align: center; height: 22px; color: #e8e8e8;
}
QProgressBar::chunk { background: #0078d4; border-radius: 4px; }
QLabel { color: #e8e8e8; }
"""


class Sidebar(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self.setStyleSheet("""
            QListWidget { background: #171717; border: none; padding: 12px 0; }
            QListWidget::item { padding: 12px 20px; color: #b8b8b8; }
            QListWidget::item:selected { background: #0078d4; color: white; border-radius: 4px; margin: 0 8px; }
            QListWidget::item:hover { background: #262626; }
        """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screenshotter")
        self.resize(1100, 780)
        self.worker: GuiWorker | None = None

        # Sidebar
        self.sidebar = Sidebar()
        for label in ("🎬  Extract Frames", "🤖  Detect Character"):
            self.sidebar.addItem(QListWidgetItem(label))
        self.sidebar.currentRowChanged.connect(self._switch_page)

        # Pages
        self.pages = QStackedWidget()
        self.extract_page = ExtractPage()
        self.detect_page = DetectPage()
        self.pages.addWidget(self.extract_page)
        self.pages.addWidget(self.detect_page)

        self.extract_page.btn_start.clicked.connect(self._start_extract)
        self.detect_page.btn_start.clicked.connect(self._start_detect)

        # Progress + log panel
        bottom = self._build_bottom()

        # Layout
        content = QWidget()
        vlay = QVBoxLayout(content)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.pages)
        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        vlay.addWidget(splitter)

        root = QWidget()
        hlay = QHBoxLayout(root)
        hlay.setContentsMargins(0, 0, 0, 0)
        hlay.setSpacing(0)
        hlay.addWidget(self.sidebar)
        hlay.addWidget(content, 1)
        self.setCentralWidget(root)

        self.setStyleSheet(DARK_QSS)
        self.sidebar.setCurrentRow(0)

    def _build_bottom(self):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #171717; border-top: 1px solid #333; }")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(24, 12, 24, 12)

        row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label = QLabel("Idle")
        self.status_label.setStyleSheet("color: #aaa;")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel)
        row.addWidget(self.progress_bar, 1)
        row.addWidget(self.status_label)
        row.addWidget(self.btn_cancel)
        lay.addLayout(row)

        self.log = LogConsole()
        self.log.setFixedHeight(180)
        lay.addWidget(self.log)
        return frame

    def _switch_page(self, idx: int):
        self.pages.setCurrentIndex(idx)

    def _start_extract(self):
        cfg = self.extract_page.build_config()
        if cfg is None:
            return
        self._start_worker(frame_extractor.run, cfg)

    def _start_detect(self):
        cfg = self.detect_page.build_config()
        if cfg is None:
            return
        self.log.append_line("Loading models (may take a while on first run)…")
        self._start_worker(character_detector.run, cfg)

    def _start_worker(self, target, config):
        if self.worker and self.worker.isRunning():
            return
        self.extract_page.btn_start.setEnabled(False)
        self.detect_page.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Running…")
        self.log.append_line(f"Started with {len(config.get('videos', []))} video(s).")

        self.worker = GuiWorker(target, config)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self.log.append_line)
        self.worker.finished_ok.connect(self._on_done)
        self.worker.start()

    def _on_progress(self, pct: float, saved: int, name: str):
        self.progress_bar.setValue(int(pct))
        self.status_label.setText(f"{name}  •  saved {saved}")

    def _on_done(self, total: int):
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Done — total {total}")
        self.log.append_line(f"Finished. Total screenshots: {total}")
        self.extract_page.btn_start.setEnabled(True)
        self.detect_page.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.worker = None

    def _cancel(self):
        if self.worker and self.worker.isRunning():
            self.log.append_line("Cancelling…")
            self.worker.cancel()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Screenshotter")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
