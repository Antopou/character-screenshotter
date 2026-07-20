from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QListWidget, QListWidgetItem,
    QFileDialog, QGroupBox, QMessageBox, QToolButton, QStackedWidget,
    QFrame,
)

import frame_extractor


class ExtractPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_videos: list[Path] = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 14)
        root.setSpacing(10)

        title = QLabel("Extract Frames")
        title.setProperty("title", True)
        root.addWidget(title)

        # ── Videos ──
        vids = QGroupBox("Videos")
        vl = QVBoxLayout(vids)
        vl.setContentsMargins(10, 14, 10, 10)
        vl.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(6)
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("No folder selected")
        self.folder_edit.setReadOnly(True)
        btn_folder = QPushButton("Folder")
        btn_folder.clicked.connect(self._pick_folder)
        btn_files = QPushButton("Files")
        btn_files.clicked.connect(self._pick_files)
        row.addWidget(self.folder_edit, 1)
        row.addWidget(btn_folder)
        row.addWidget(btn_files)
        vl.addLayout(row)

        self.vid_list = QListWidget()
        self.vid_list.setMinimumHeight(120)
        self.vid_list.setMaximumHeight(180)
        vl.addWidget(self.vid_list)
        root.addWidget(vids)

        # ── Main options (compact single-row) ──
        main_row = QHBoxLayout()
        main_row.setSpacing(8)

        main_row.addWidget(QLabel("Every"))
        self.spin_val = QSpinBox()
        self.spin_val.setRange(1, 100000)
        self.spin_val.setValue(50)
        self.spin_val.setFixedWidth(80)
        main_row.addWidget(self.spin_val)

        self.combo_unit = QComboBox()
        self.combo_unit.addItems(["frames", "seconds"])
        self.combo_unit.setFixedWidth(100)
        main_row.addWidget(self.combo_unit)
        self.combo_unit.currentTextChanged.connect(self._on_unit_change)

        main_row.addSpacing(16)
        main_row.addWidget(QLabel("Output"))
        self.out_edit = QLineEdit("screenshots")
        main_row.addWidget(self.out_edit, 1)
        btn_out = QPushButton("…")
        btn_out.setFixedWidth(30)
        btn_out.clicked.connect(self._pick_output)
        main_row.addWidget(btn_out)
        root.addLayout(main_row)

        # ── Advanced (collapsed) ──
        self.adv_toggle = QToolButton()
        self.adv_toggle.setText("▸ Advanced")
        self.adv_toggle.setCheckable(True)
        self.adv_toggle.setStyleSheet(
            "QToolButton { color: #8a8f98; border: none; padding: 4px 2px; }"
            "QToolButton:hover { color: #e6e7ea; }"
        )
        self.adv_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adv_toggle.clicked.connect(self._toggle_adv)
        root.addWidget(self.adv_toggle)

        self.adv_frame = QFrame()
        adv_l = QVBoxLayout(self.adv_frame)
        adv_l.setContentsMargins(4, 0, 4, 0)
        adv_l.setSpacing(6)

        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(8)
        fmt_row.addWidget(QLabel("Format"))
        self.combo_fmt = QComboBox()
        self.combo_fmt.addItems(["jpg", "png"])
        self.combo_fmt.setFixedWidth(80)
        fmt_row.addWidget(self.combo_fmt)
        fmt_row.addSpacing(12)
        fmt_row.addWidget(QLabel("Quality"))
        self.spin_q = QSpinBox()
        self.spin_q.setRange(1, 100)
        self.spin_q.setValue(92)
        self.spin_q.setFixedWidth(70)
        fmt_row.addWidget(self.spin_q)
        self.combo_fmt.currentTextChanged.connect(
            lambda t: self.spin_q.setEnabled(t == "jpg")
        )
        fmt_row.addStretch(1)
        adv_l.addLayout(fmt_row)

        range_row = QHBoxLayout()
        range_row.setSpacing(8)
        range_row.addWidget(QLabel("Start"))
        self.start_edit = QLineEdit()
        self.start_edit.setPlaceholderText("00:00")
        self.start_edit.setFixedWidth(90)
        range_row.addWidget(self.start_edit)
        range_row.addSpacing(12)
        range_row.addWidget(QLabel("End"))
        self.end_edit = QLineEdit()
        self.end_edit.setPlaceholderText("blank = end")
        self.end_edit.setFixedWidth(120)
        range_row.addWidget(self.end_edit)
        range_row.addStretch(1)
        adv_l.addLayout(range_row)

        self.adv_frame.setVisible(False)
        root.addWidget(self.adv_frame)

        root.addStretch(1)

        # ── Action ──
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_start = QPushButton("Start  →")
        self.btn_start.setObjectName("primary")
        btn_row.addWidget(self.btn_start)
        root.addLayout(btn_row)

    # ── helpers ──
    def _toggle_adv(self):
        on = self.adv_toggle.isChecked()
        self.adv_frame.setVisible(on)
        self.adv_toggle.setText("▾ Advanced" if on else "▸ Advanced")

    def _on_unit_change(self, unit):
        if unit == "seconds":
            self.spin_val.setValue(2)
        else:
            self.spin_val.setValue(50)

    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Video folder", str(Path.home()))
        if folder:
            self.folder_edit.setText(folder)
            self._load_folder(folder)

    def _pick_files(self):
        exts = " ".join(f"*{e}" for e in frame_extractor.VIDEO_EXTS)
        files, _ = QFileDialog.getOpenFileNames(
            self, "Pick videos", str(Path.home()), f"Videos ({exts})",
        )
        if files:
            self.folder_edit.setText(str(Path(files[0]).parent))
            self.selected_videos = [Path(f) for f in files]
            self._refresh_list()

    def _load_folder(self, folder):
        p = Path(folder)
        self.selected_videos = sorted(
            f for f in p.iterdir() if f.suffix.lower() in frame_extractor.VIDEO_EXTS
        )
        self._refresh_list()

    def _refresh_list(self):
        self.vid_list.clear()
        for v in self.selected_videos:
            it = QListWidgetItem(v.name)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked)
            it.setData(Qt.ItemDataRole.UserRole, str(v))
            self.vid_list.addItem(it)

    def _pick_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Output folder", str(Path.cwd()))
        if folder:
            self.out_edit.setText(folder)

    def get_checked_videos(self):
        picked = []
        for i in range(self.vid_list.count()):
            it = self.vid_list.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                picked.append(Path(it.data(Qt.ItemDataRole.UserRole)))
        return picked

    def build_config(self):
        videos = self.get_checked_videos()
        if not videos:
            QMessageBox.warning(self, "No videos", "Pick at least one video.")
            return None
        cfg = {
            "videos": videos,
            "output": self.out_edit.text().strip() or "screenshots",
            "format": self.combo_fmt.currentText(),
            "quality": self.spin_q.value(),
            "start_sec": self._parse_ts(self.start_edit.text()),
            "end_sec": self._parse_ts(self.end_edit.text()),
            "prefix": None,
        }
        if self.combo_unit.currentText() == "frames":
            cfg["every_n_frames"] = self.spin_val.value()
        else:
            cfg["every_seconds"] = float(self.spin_val.value())
        return cfg

    @staticmethod
    def _parse_ts(text):
        text = text.strip()
        if not text:
            return None
        try:
            return frame_extractor.parse_ts(text)
        except Exception:
            return None
