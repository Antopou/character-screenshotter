#!/usr/bin/env python3
"""Screenshotter — Desktop GUI (PySide6)."""

import sys
from pathlib import Path

try:
    from PySide6.QtCore import Qt, QSize, QSettings
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QStackedWidget, QProgressBar, QFrame, QToolButton,
        QSizePolicy, QToolBar,
    )
except ImportError:
    print("Missing dependency: PySide6", file=sys.stderr)
    print("Install with:  uv sync", file=sys.stderr)
    sys.exit(1)

import frame_extractor
import character_detector
from gui.extract_page import ExtractPage
from gui.detect_page import DetectPage
from gui.worker import GuiWorker
from gui.log_console import LogConsole


QSS = """
* { font-family: "Menlo", "JetBrains Mono", "Consolas", monospace; font-size: 12px; }
QMainWindow, QWidget { background: #17181c; color: #e6e7ea; }

/* Native unified toolbar — force our own bg so titlebar tint doesn't stand out */
QToolBar#maintoolbar {
    background: #17181c; border: none; border-bottom: 1px solid #22242a;
    padding: 4px 8px; spacing: 4px;
}
QToolBar#maintoolbar::separator { width: 0; }

QToolButton[seg="true"] {
    background: transparent; color: #8a8f98; border: none;
    padding: 4px 12px; border-radius: 5px; font-weight: 600;
}
QToolButton[seg="true"]:hover { color: #e6e7ea; background: rgba(255,255,255,0.05); }
QToolButton[seg="true"]:checked { color: #ffffff; background: rgba(255,255,255,0.10); }

/* Inputs */
QGroupBox {
    border: 1px solid #22242a; border-radius: 8px;
    margin-top: 14px; padding: 10px 12px;
    font-weight: 600; color: #b8bcc4;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #1c1e23; border: 1px solid #2a2d34; border-radius: 5px;
    padding: 4px 8px; color: #e6e7ea; min-height: 20px;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0; height: 0; border: none; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #4b8bf5;
}
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView { background: #1c1e23; border: 1px solid #2a2d34; selection-background-color: #2f3239; }

QPushButton {
    background: #24262c; border: 1px solid #2c2f36; border-radius: 5px;
    padding: 5px 12px; color: #e6e7ea;
}
QPushButton:hover { background: #2c2f36; }
QPushButton:disabled { color: #55585f; }

QPushButton#primary {
    background: #4b8bf5; border: none; color: white; font-weight: 600;
    padding: 7px 20px; border-radius: 6px;
}
QPushButton#primary:hover  { background: #5b96f6; }
QPushButton#primary:pressed{ background: #3f7ce0; }
QPushButton#primary:disabled { background: #3a3d44; color: #7a7d84; }

QListWidget {
    background: #1a1c21; border: 1px solid #22242a; border-radius: 6px;
    padding: 4px;
}
QListWidget::item { padding: 3px 6px; border-radius: 3px; }
QListWidget::item:hover { background: #22252b; }
QListWidget::item:selected { background: #2f3441; color: #ffffff; }
QListWidget::item:selected:!active { background: #262a34; }

QProgressBar {
    background: #1c1e23; border: 1px solid #22242a; border-radius: 4px;
    text-align: center; height: 6px; color: transparent;
}
QProgressBar::chunk { background: #4b8bf5; border-radius: 3px; }

QRadioButton, QCheckBox { color: #c5c8cf; }
QSlider::groove:horizontal { background: #2a2d34; height: 4px; border-radius: 2px; }
QSlider::handle:horizontal { background: #4b8bf5; width: 14px; margin: -6px 0; border-radius: 7px; }

QLabel[muted="true"] { color: #7a7f88; }
QLabel[title="true"] { font-size: 14px; font-weight: 700; color: #f2f3f5; }

/* Log */
#logframe { background: #101114; border-top: 1px solid #22242a; }
QPlainTextEdit { background: transparent; border: none; color: #b8bcc4; }

/* Flat overlay scrollbars — no arrows */
QScrollBar:vertical {
    background: transparent; width: 8px; margin: 2px 2px 2px 0;
}
QScrollBar::handle:vertical {
    background: #3a3d44; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #4b4f57; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0; width: 0; border: none; background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

QScrollBar:horizontal {
    background: transparent; height: 8px; margin: 0 2px 2px 2px;
}
QScrollBar::handle:horizontal {
    background: #3a3d44; border-radius: 4px; min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #4b4f57; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    height: 0; width: 0; border: none; background: none;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
"""


class SegButton(QToolButton):
    def __init__(self, text):
        super().__init__()
        self.setText(text)
        self.setProperty("seg", True)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("screenshotter")
        self.resize(880, 620)
        self.setMinimumSize(QSize(760, 540))
        self.setUnifiedTitleAndToolBarOnMac(True)
        self.worker: GuiWorker | None = None
        self.settings = QSettings("screenshotter", "main")

        # ── Native unified toolbar ──
        tb = QToolBar()
        tb.setObjectName("maintoolbar")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        self.tab_extract = SegButton("Extract")
        self.tab_detect  = SegButton("Detect")
        self.tab_extract.setChecked(True)
        self.tab_extract.clicked.connect(lambda: self._switch(0))
        self.tab_detect.clicked.connect(lambda: self._switch(1))
        tb.addWidget(self.tab_extract)
        tb.addWidget(self.tab_detect)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        self.log_toggle = QToolButton()
        self.log_toggle.setText("Log ▾")
        self.log_toggle.setProperty("seg", True)
        self.log_toggle.setCheckable(True)
        self.log_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.log_toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.log_toggle.clicked.connect(self._toggle_log)
        tb.addWidget(self.log_toggle)

        # ── Pages ──
        self.pages = QStackedWidget()
        self.extract_page = ExtractPage()
        self.detect_page = DetectPage()
        self.pages.addWidget(self.extract_page)
        self.pages.addWidget(self.detect_page)
        self.extract_page.btn_start.clicked.connect(self._start_extract)
        self.detect_page.btn_start.clicked.connect(self._start_detect)

        # ── Status bar (thin) ──
        status = QFrame()
        status.setObjectName("logframe")
        status.setFixedHeight(38)
        s_lay = QHBoxLayout(status)
        s_lay.setContentsMargins(14, 8, 14, 8)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label = QLabel("Idle")
        self.status_label.setProperty("muted", True)
        self.status_label.setMinimumWidth(220)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_cancel.clicked.connect(self._cancel)
        s_lay.addWidget(self.progress_bar, 1)
        s_lay.addWidget(self.status_label)
        s_lay.addWidget(self.btn_cancel)

        # ── Log panel (hidden by default) ──
        self.log_frame = QFrame()
        self.log_frame.setObjectName("logframe")
        lf_lay = QVBoxLayout(self.log_frame)
        lf_lay.setContentsMargins(0, 0, 0, 0)
        self.log = LogConsole()
        self.log.setFixedHeight(160)
        lf_lay.addWidget(self.log)
        self.log_frame.setVisible(False)

        # ── Assemble ──
        root = QWidget()
        vlay = QVBoxLayout(root)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)
        vlay.addWidget(self.pages, 1)
        vlay.addWidget(status)
        vlay.addWidget(self.log_frame)
        self.setCentralWidget(root)
        self.setStyleSheet(QSS)
        # Don't auto-focus any field on launch; wait for user Tab
        root.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        root.setFocus()

        # Restore geometry + last tab
        geo = self.settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        try:
            self._switch(int(self.settings.value("tab", 0)))
        except (TypeError, ValueError):
            pass

    def closeEvent(self, e):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("tab", self.pages.currentIndex())
        self.settings.sync()
        super().closeEvent(e)

    # ── slots ──
    def _switch(self, idx):
        self.tab_extract.setChecked(idx == 0)
        self.tab_detect.setChecked(idx == 1)
        self.pages.setCurrentIndex(idx)

    def _toggle_log(self):
        show = self.log_toggle.isChecked()
        self.log_frame.setVisible(show)
        self.log_toggle.setText("Log ▴" if show else "Log ▾")

    def _start_extract(self):
        cfg = self.extract_page.build_config()
        if cfg is None:
            return
        self._start_worker(frame_extractor.run, cfg)

    def _start_detect(self):
        cfg = self.detect_page.build_config()
        if cfg is None:
            return
        self.log.append_line("Loading models (first run downloads ~700 MB)…")
        self._start_worker(character_detector.run, cfg)

    def _start_worker(self, target, config):
        if self.worker and self.worker.isRunning():
            return
        self.extract_page.btn_start.setEnabled(False)
        self.detect_page.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting…")
        self.log.append_line(f"Started with {len(config.get('videos', []))} video(s).")

        self.worker = GuiWorker(target, config)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self.log.append_line)
        self.worker.finished_ok.connect(self._on_done)
        self.worker.start()

    def _on_progress(self, pct: float, saved: int, name: str):
        self.progress_bar.setValue(int(pct))
        self.status_label.setText(f"{name} · {saved} saved")

    def _on_done(self, total: int):
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Done · {total} saved")
        self.log.append_line(f"Finished. Total: {total}")
        self.extract_page.btn_start.setEnabled(True)
        self.detect_page.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.worker = None

    def _cancel(self):
        if self.worker and self.worker.isRunning():
            self.log.append_line("Cancelling…")
            self.worker.cancel()


def _apply_dark_appearance():
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApp, NSAppearance
        NSApp.setAppearance_(NSAppearance.appearanceNamed_("NSAppearanceNameDarkAqua"))
    except Exception as e:
        print(f"[appearance] {e}", file=sys.stderr)


def _make_titlebar_transparent(win):
    if sys.platform != "darwin":
        return
    try:
        import ctypes
        import objc
        view_ptr = int(win.winId())
        nsview = objc.objc_object(c_void_p=ctypes.c_void_p(view_ptr))
        nswin = nsview.window()
        nswin.setTitlebarAppearsTransparent_(True)
        nswin.setTitleVisibility_(1)  # NSWindowTitleHidden
        nswin.setStyleMask_(nswin.styleMask() | (1 << 15))  # FullSizeContentView
    except Exception as e:
        print(f"[titlebar] pyobjc unavailable: {e}", file=sys.stderr)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Screenshotter")
    icon_path = Path(__file__).parent / "assets" / "icon.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    win = MainWindow()
    if icon_path.exists():
        win.setWindowIcon(QIcon(str(icon_path)))
    win.show()
    _apply_dark_appearance()
    _make_titlebar_transparent(win)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
