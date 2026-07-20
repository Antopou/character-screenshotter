from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QRadioButton, QButtonGroup,
    QListWidget, QListWidgetItem, QFileDialog, QGroupBox, QFormLayout,
    QMessageBox,
)

import frame_extractor


class ExtractPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_videos: list[Path] = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("Extract Frames")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        root.addWidget(title)

        subtitle = QLabel("Dump screenshots from videos at fixed intervals — no AI.")
        subtitle.setStyleSheet("color: gray;")
        root.addWidget(subtitle)

        # Video picker
        vid_box = QGroupBox("Videos")
        vl = QVBoxLayout(vid_box)
        row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Pick a folder containing video files…")
        btn_folder = QPushButton("Browse folder…")
        btn_folder.clicked.connect(self._pick_folder)
        btn_files = QPushButton("Pick files…")
        btn_files.clicked.connect(self._pick_files)
        row.addWidget(self.folder_edit, 1)
        row.addWidget(btn_folder)
        row.addWidget(btn_files)
        vl.addLayout(row)

        self.vid_list = QListWidget()
        self.vid_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.vid_list.setMinimumHeight(140)
        vl.addWidget(self.vid_list)
        root.addWidget(vid_box)

        # Interval
        opt_box = QGroupBox("Options")
        form = QFormLayout(opt_box)

        interval_row = QHBoxLayout()
        self.rb_frames = QRadioButton("Every N frames")
        self.rb_secs = QRadioButton("Every N seconds")
        self.rb_frames.setChecked(True)
        bg = QButtonGroup(self)
        bg.addButton(self.rb_frames)
        bg.addButton(self.rb_secs)
        interval_row.addWidget(self.rb_frames)
        interval_row.addWidget(self.rb_secs)
        interval_row.addStretch(1)
        form.addRow("Interval:", interval_row)

        self.spin_n = QSpinBox()
        self.spin_n.setRange(1, 100000)
        self.spin_n.setValue(50)
        form.addRow("N frames:", self.spin_n)

        self.spin_sec = QDoubleSpinBox()
        self.spin_sec.setRange(0.1, 3600.0)
        self.spin_sec.setValue(2.0)
        self.spin_sec.setSingleStep(0.5)
        form.addRow("N seconds:", self.spin_sec)

        self.combo_fmt = QComboBox()
        self.combo_fmt.addItems(["jpg", "png"])
        form.addRow("Format:", self.combo_fmt)

        self.spin_q = QSpinBox()
        self.spin_q.setRange(1, 100)
        self.spin_q.setValue(92)
        form.addRow("JPEG quality:", self.spin_q)

        self.combo_fmt.currentTextChanged.connect(
            lambda t: self.spin_q.setEnabled(t == "jpg")
        )

        out_row = QHBoxLayout()
        self.out_edit = QLineEdit("screenshots")
        btn_out = QPushButton("Browse…")
        btn_out.clicked.connect(self._pick_output)
        out_row.addWidget(self.out_edit, 1)
        out_row.addWidget(btn_out)
        form.addRow("Output folder:", out_row)

        range_row = QHBoxLayout()
        self.start_edit = QLineEdit()
        self.start_edit.setPlaceholderText("00:00")
        self.end_edit = QLineEdit()
        self.end_edit.setPlaceholderText("blank = end")
        range_row.addWidget(QLabel("Start:"))
        range_row.addWidget(self.start_edit)
        range_row.addSpacing(12)
        range_row.addWidget(QLabel("End:"))
        range_row.addWidget(self.end_edit)
        form.addRow("Range:", range_row)

        root.addWidget(opt_box)

        # Action button
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_start = QPushButton("Start ▶")
        self.btn_start.setMinimumHeight(38)
        self.btn_start.setStyleSheet(
            "QPushButton { background: #0078d4; color: white; border-radius: 6px; padding: 6px 24px; font-weight: 600; }"
            "QPushButton:hover { background: #1084dd; }"
            "QPushButton:disabled { background: #7a7a7a; }"
        )
        btn_row.addWidget(self.btn_start)
        root.addLayout(btn_row)
        root.addStretch(1)

    # ── slots ──
    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Pick video folder", str(Path.home()))
        if folder:
            self.folder_edit.setText(folder)
            self._load_folder(folder)

    def _pick_files(self):
        exts = " ".join(f"*{e}" for e in frame_extractor.VIDEO_EXTS)
        files, _ = QFileDialog.getOpenFileNames(
            self, "Pick videos", str(Path.home()), f"Videos ({exts})",
        )
        if files:
            self.selected_videos = [Path(f) for f in files]
            self._refresh_list()

    def _load_folder(self, folder):
        p = Path(folder)
        vids = sorted(f for f in p.iterdir()
                      if f.suffix.lower() in frame_extractor.VIDEO_EXTS)
        self.selected_videos = vids
        self._refresh_list()

    def _refresh_list(self):
        self.vid_list.clear()
        for v in self.selected_videos:
            item = QListWidgetItem(v.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, str(v))
            self.vid_list.addItem(item)

    def _pick_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Pick output folder", str(Path.cwd()))
        if folder:
            self.out_edit.setText(folder)

    def get_checked_videos(self) -> list[Path]:
        picked = []
        for i in range(self.vid_list.count()):
            item = self.vid_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                picked.append(Path(item.data(Qt.ItemDataRole.UserRole)))
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
        if self.rb_frames.isChecked():
            cfg["every_n_frames"] = self.spin_n.value()
        else:
            cfg["every_seconds"] = self.spin_sec.value()
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
