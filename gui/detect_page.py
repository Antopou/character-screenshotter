from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QComboBox, QListWidget, QListWidgetItem,
    QFileDialog, QGroupBox, QSlider, QMessageBox, QToolButton, QFrame,
    QAbstractSpinBox,
)

import frame_extractor


class DetectPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_videos: list[Path] = []
        self.settings = QSettings("screenshotter", "detect")
        self._build()
        self._restore()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 14)
        root.setSpacing(10)

        title = QLabel("Detect Character")
        title.setProperty("title", True)
        root.addWidget(title)

        # Videos
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
        btn_refresh = QPushButton("↻")
        btn_refresh.setFixedWidth(30)
        btn_refresh.setToolTip("Rescan current folder")
        btn_refresh.clicked.connect(self._refresh)
        row.addWidget(self.folder_edit, 1)
        row.addWidget(btn_refresh)
        row.addWidget(btn_folder)
        row.addWidget(btn_files)
        vl.addLayout(row)
        self.vid_list = QListWidget()
        self.vid_list.setMinimumHeight(100)
        self.vid_list.setMaximumHeight(160)
        vl.addWidget(self.vid_list)
        root.addWidget(vids)

        # Main options — tag + reference
        tag_row = QHBoxLayout()
        tag_row.setSpacing(8)
        tag_row.addWidget(QLabel("Tag"))
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("e.g. rem_(re:zero)   — blank to skip DeepDanbooru")
        tag_row.addWidget(self.tag_edit, 1)
        root.addLayout(tag_row)

        ref_row = QHBoxLayout()
        ref_row.setSpacing(8)
        ref_row.addWidget(QLabel("Refs"))
        self.ref_edit = QLineEdit("references")
        ref_row.addWidget(self.ref_edit, 1)
        btn_ref = QPushButton("…")
        btn_ref.setFixedWidth(30)
        btn_ref.clicked.connect(self._pick_ref)
        ref_row.addWidget(btn_ref)
        ref_row.addSpacing(10)
        ref_row.addWidget(QLabel("Output"))
        self.out_edit = QLineEdit("screenshots")
        ref_row.addWidget(self.out_edit, 1)
        btn_out = QPushButton("…")
        btn_out.setFixedWidth(30)
        btn_out.clicked.connect(self._pick_output)
        ref_row.addWidget(btn_out)
        root.addLayout(ref_row)

        # Advanced
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

        self.adv = QFrame()
        av = QVBoxLayout(self.adv)
        av.setContentsMargins(4, 0, 4, 0)
        av.setSpacing(8)

        av.addLayout(self._slider("Tag threshold", 30, 80, 45, "slider_tag"))
        av.addLayout(self._slider("Match threshold", 60, 90, 72, "slider_match"))

        misc = QHBoxLayout()
        misc.setSpacing(8)
        misc.addWidget(QLabel("Combine"))
        self.combo_combine = QComboBox()
        self.combo_combine.addItems(["either", "both"])
        self.combo_combine.setFixedWidth(90)
        misc.addWidget(self.combo_combine)
        misc.addSpacing(12)
        misc.addWidget(QLabel("Checks/s"))
        self.spin_cps = QSpinBox()
        self.spin_cps.setRange(1, 30)
        self.spin_cps.setValue(1)
        self.spin_cps.setFixedWidth(60)
        self.spin_cps.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        misc.addWidget(self.spin_cps)
        misc.addSpacing(12)
        misc.addWidget(QLabel("Min gap (s)"))
        self.spin_gap = QSpinBox()
        self.spin_gap.setRange(0, 120)
        self.spin_gap.setValue(4)
        self.spin_gap.setFixedWidth(60)
        self.spin_gap.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        misc.addWidget(self.spin_gap)
        misc.addStretch(1)
        av.addLayout(misc)

        self.adv.setVisible(False)
        root.addWidget(self.adv)

        root.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_start = QPushButton("Start  →")
        self.btn_start.setObjectName("primary")
        btn_row.addWidget(self.btn_start)
        root.addLayout(btn_row)

    def _slider(self, label, lo, hi, val, attr):
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel(label))
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        setattr(self, attr, s)
        lbl = QLabel(f"{val/100:.2f}")
        lbl.setFixedWidth(40)
        lbl.setProperty("muted", True)
        s.valueChanged.connect(lambda v: lbl.setText(f"{v/100:.2f}"))
        row.addWidget(s, 1)
        row.addWidget(lbl)
        return row

    def _toggle_adv(self):
        on = self.adv_toggle.isChecked()
        self.adv.setVisible(on)
        self.adv_toggle.setText("▾ Advanced" if on else "▸ Advanced")

    def _refresh(self):
        folder = self.folder_edit.text().strip()
        if not folder or not Path(folder).is_dir():
            return
        prev = {v.name for v in self.get_checked_videos()}
        p = Path(folder)
        self.selected_videos = sorted(
            f for f in p.iterdir() if f.suffix.lower() in frame_extractor.VIDEO_EXTS
        )
        self._refresh_list()
        for i in range(self.vid_list.count()):
            it = self.vid_list.item(i)
            if it.text() not in prev:
                it.setCheckState(Qt.CheckState.Unchecked)

    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Video folder", str(Path.home()))
        if folder:
            self.folder_edit.setText(folder)
            p = Path(folder)
            self.selected_videos = sorted(
                f for f in p.iterdir() if f.suffix.lower() in frame_extractor.VIDEO_EXTS
            )
            self._refresh_list()

    def _pick_files(self):
        exts = " ".join(f"*{e}" for e in frame_extractor.VIDEO_EXTS)
        files, _ = QFileDialog.getOpenFileNames(
            self, "Pick videos", str(Path.home()), f"Videos ({exts})",
        )
        if files:
            self.folder_edit.setText(str(Path(files[0]).parent))
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
        self._persist()
        return cfg

    def _persist(self):
        s = self.settings
        s.setValue("folder", self.folder_edit.text())
        s.setValue("tag", self.tag_edit.text())
        s.setValue("ref", self.ref_edit.text())
        s.setValue("output", self.out_edit.text())
        s.setValue("tag_thr", self.slider_tag.value())
        s.setValue("match_thr", self.slider_match.value())
        s.setValue("combine", self.combo_combine.currentText())
        s.setValue("cps", self.spin_cps.value())
        s.setValue("gap", self.spin_gap.value())
        s.sync()

    def _restore(self):
        s = self.settings
        folder = s.value("folder", "")
        if folder and Path(folder).is_dir():
            self.folder_edit.setText(folder)
            p = Path(folder)
            self.selected_videos = sorted(
                f for f in p.iterdir() if f.suffix.lower() in frame_extractor.VIDEO_EXTS
            )
            self._refresh_list()
        self.tag_edit.setText(s.value("tag", "") or "")
        ref = s.value("ref", "references")
        if ref:
            self.ref_edit.setText(ref)
        out = s.value("output", "screenshots")
        if out:
            self.out_edit.setText(out)
        try:
            self.slider_tag.setValue(int(s.value("tag_thr", 45)))
            self.slider_match.setValue(int(s.value("match_thr", 72)))
        except (TypeError, ValueError):
            pass
        idx = self.combo_combine.findText(s.value("combine", "either"))
        if idx >= 0:
            self.combo_combine.setCurrentIndex(idx)
        try:
            self.spin_cps.setValue(int(s.value("cps", 1)))
            self.spin_gap.setValue(int(s.value("gap", 4)))
        except (TypeError, ValueError):
            pass
