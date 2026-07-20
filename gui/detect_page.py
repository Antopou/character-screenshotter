from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QListWidget, QListWidgetItem,
    QFileDialog, QGroupBox, QFormLayout, QSlider, QMessageBox,
)

import frame_extractor


class DetectPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_videos: list[Path] = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("Detect Character")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        root.addWidget(title)

        sub = QLabel("AI: DeepDanbooru tag match + optional reference image similarity.")
        sub.setStyleSheet("color: gray;")
        root.addWidget(sub)

        # Videos
        vid_box = QGroupBox("Videos")
        vl = QVBoxLayout(vid_box)
        row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Video folder…")
        btn_folder = QPushButton("Browse folder…")
        btn_folder.clicked.connect(self._pick_folder)
        btn_files = QPushButton("Pick files…")
        btn_files.clicked.connect(self._pick_files)
        row.addWidget(self.folder_edit, 1)
        row.addWidget(btn_folder)
        row.addWidget(btn_files)
        vl.addLayout(row)
        self.vid_list = QListWidget()
        self.vid_list.setMinimumHeight(120)
        vl.addWidget(self.vid_list)
        root.addWidget(vid_box)

        # Detection
        det_box = QGroupBox("Detection")
        form = QFormLayout(det_box)

        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("e.g. rem_(re:zero)   (blank = skip DeepDanbooru)")
        form.addRow("Character tag:", self.tag_edit)

        ref_row = QHBoxLayout()
        self.ref_edit = QLineEdit("references")
        btn_ref = QPushButton("Browse…")
        btn_ref.clicked.connect(self._pick_ref)
        ref_row.addWidget(self.ref_edit, 1)
        ref_row.addWidget(btn_ref)
        form.addRow("Reference folder:", ref_row)

        self.slider_tag = self._make_slider(30, 80, 45)
        form.addRow("Tag threshold:", self._slider_row(self.slider_tag, scale=100))

        self.slider_match = self._make_slider(60, 90, 72)
        form.addRow("Match threshold:", self._slider_row(self.slider_match, scale=100))

        self.combo_combine = QComboBox()
        self.combo_combine.addItems(["either", "both"])
        form.addRow("Combine mode:", self.combo_combine)

        self.spin_cps = QSpinBox()
        self.spin_cps.setRange(1, 30)
        self.spin_cps.setValue(1)
        form.addRow("Checks/sec:", self.spin_cps)

        self.spin_gap = QSpinBox()
        self.spin_gap.setRange(0, 120)
        self.spin_gap.setValue(4)
        form.addRow("Min gap (sec):", self.spin_gap)

        out_row = QHBoxLayout()
        self.out_edit = QLineEdit("screenshots")
        btn_out = QPushButton("Browse…")
        btn_out.clicked.connect(self._pick_output)
        out_row.addWidget(self.out_edit, 1)
        out_row.addWidget(btn_out)
        form.addRow("Output folder:", out_row)

        root.addWidget(det_box)

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

    def _make_slider(self, lo, hi, val):
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    def _slider_row(self, slider, scale):
        row = QHBoxLayout()
        lbl = QLabel(f"{slider.value() / scale:.2f}")
        lbl.setMinimumWidth(40)
        slider.valueChanged.connect(lambda v: lbl.setText(f"{v/scale:.2f}"))
        row.addWidget(slider, 1)
        row.addWidget(lbl)
        return row

    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Video folder", str(Path.home()))
        if folder:
            self.folder_edit.setText(folder)
            p = Path(folder)
            self.selected_videos = sorted(
                f for f in p.iterdir()
                if f.suffix.lower() in frame_extractor.VIDEO_EXTS
            )
            self._refresh_list()

    def _pick_files(self):
        exts = " ".join(f"*{e}" for e in frame_extractor.VIDEO_EXTS)
        files, _ = QFileDialog.getOpenFileNames(
            self, "Pick videos", str(Path.home()), f"Videos ({exts})",
        )
        if files:
            self.selected_videos = [Path(f) for f in files]
            self._refresh_list()

    def _refresh_list(self):
        self.vid_list.clear()
        for v in self.selected_videos:
            it = QListWidgetItem(v.name)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked)
            it.setData(Qt.ItemDataRole.UserRole, str(v))
            self.vid_list.addItem(it)

    def _pick_ref(self):
        folder = QFileDialog.getExistingDirectory(self, "Reference folder", str(Path.cwd()))
        if folder:
            self.ref_edit.setText(folder)

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
        tag = self.tag_edit.text().strip()
        ref = self.ref_edit.text().strip()
        if not tag and (not ref or not Path(ref).exists()):
            QMessageBox.warning(self, "Nothing to detect",
                                "Provide a character tag OR a reference folder with images.")
            return None
        cfg = {
            "videos": videos,
            "CHARACTER_TAG": tag,
            "REFERENCE_FOLDER": ref or "references",
            "TAG_THRESHOLD": self.slider_tag.value() / 100.0,
            "MATCH_THRESHOLD": self.slider_match.value() / 100.0,
            "COMBINE_MODE": self.combo_combine.currentText(),
            "CHECKS_PER_SECOND": self.spin_cps.value(),
            "MIN_SECONDS_GAP": self.spin_gap.value(),
            "OUTPUT_FOLDER": self.out_edit.text().strip() or "screenshots",
        }
        return cfg
