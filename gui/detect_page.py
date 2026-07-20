from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QComboBox, QListWidget, QListWidgetItem,
    QFileDialog, QGroupBox, QSlider, QMessageBox, QToolButton, QFrame,
    QAbstractSpinBox, QCheckBox,
)

import frame_extractor
from gui.path_edit import PathLineEdit


class DetectPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_videos: list[Path] = []
        self.settings = QSettings("vidframe", "detect")
        self._last_row: int = -1
        self._build()
        self._restore()
        self._wire_shortcuts()
        self._set_tab_order()

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
        self.folder_edit = PathLineEdit()
        self.folder_edit.setPlaceholderText("Type or paste folder path…")
        self.folder_edit.editingFinished.connect(self._on_folder_typed)
        btn_folder = QPushButton("Folder")
        btn_folder.clicked.connect(self._pick_folder)
        btn_folder.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_files = QPushButton("Files")
        btn_files.clicked.connect(self._pick_files)
        btn_files.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_refresh = QPushButton("Reload")
        btn_refresh.setToolTip("Rescan current folder for new files")
        btn_refresh.clicked.connect(self._refresh)
        btn_refresh.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        row.addWidget(self.folder_edit, 1)
        row.addWidget(btn_refresh)
        row.addWidget(btn_folder)
        row.addWidget(btn_files)
        vl.addLayout(row)
        self.chk_all = QCheckBox("Select all")
        self.chk_all.setTristate(True)
        self.chk_all.clicked.connect(self._toggle_all)
        vl.addWidget(self.chk_all)

        self.vid_list = QListWidget()
        self.vid_list.setMinimumHeight(100)
        self.vid_list.setMaximumHeight(160)
        self.vid_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.vid_list.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.vid_list.itemActivated.connect(self._toggle_item)
        self.vid_list.itemChanged.connect(self._update_master)
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
        self.ref_edit = PathLineEdit("references")
        ref_row.addWidget(self.ref_edit, 1)
        btn_ref = QPushButton("Browse")
        btn_ref.clicked.connect(self._pick_ref)
        btn_ref.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ref_row.addWidget(btn_ref)
        ref_row.addSpacing(10)
        ref_row.addWidget(QLabel("Output"))
        self.out_edit = PathLineEdit("screenshots")
        ref_row.addWidget(self.out_edit, 1)
        btn_out = QPushButton("Browse")
        btn_out.clicked.connect(self._pick_output)
        btn_out.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.adv_toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.combo_combine.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        misc.addWidget(self.combo_combine)
        misc.addSpacing(12)
        misc.addWidget(QLabel("Checks/s"))
        self.spin_cps = QSpinBox()
        self.spin_cps.setRange(1, 30)
        self.spin_cps.setValue(1)
        self.spin_cps.setFixedWidth(60)
        self.spin_cps.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_cps.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        misc.addWidget(self.spin_cps)
        misc.addSpacing(12)
        misc.addWidget(QLabel("Min gap (s)"))
        self.spin_gap = QSpinBox()
        self.spin_gap.setRange(0, 120)
        self.spin_gap.setValue(4)
        self.spin_gap.setFixedWidth(60)
        self.spin_gap.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_gap.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.btn_start.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_row.addWidget(self.btn_start)
        root.addLayout(btn_row)

    def _slider(self, label, lo, hi, val, attr):
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel(label))
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        s.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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

    def _wire_shortcuts(self):
        for seq in ("Shift+Return", "Shift+Enter"):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(lambda: self.btn_start.click())
        for seq in ("Return", "Enter"):
            sc = QShortcut(QKeySequence(seq), self.vid_list)
            sc.setContext(Qt.ShortcutContext.WidgetShortcut)
            sc.activated.connect(self._toggle_current)
        sc = QShortcut(QKeySequence("Escape"), self)
        sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc.activated.connect(self._focus_list)

    def _focus_list(self):
        row = self.vid_list.currentRow()
        if row >= 0:
            self._last_row = row
        self.vid_list.setCurrentRow(-1)
        fw = self.focusWidget()
        if fw:
            fw.clearFocus()

    def _set_tab_order(self):
        QWidget.setTabOrder(self.folder_edit, self.chk_all)
        QWidget.setTabOrder(self.chk_all, self.tag_edit)
        QWidget.setTabOrder(self.tag_edit, self.ref_edit)
        QWidget.setTabOrder(self.ref_edit, self.out_edit)
        QWidget.setTabOrder(self.out_edit, self.btn_start)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            if self.vid_list.count() > 0:
                row = self.vid_list.currentRow()
                if row < 0:
                    row = min(self.vid_list.count() - 1, self._last_row + 1) if self._last_row >= 0 else 0
                elif e.key() == Qt.Key.Key_Up:
                    row = max(0, row - 1)
                else:
                    row = min(self.vid_list.count() - 1, row + 1)
                self.vid_list.setCurrentRow(row)
                self._last_row = row
                self.vid_list.setFocus()
                return
        super().keyPressEvent(e)

    def _toggle_current(self):
        item = self.vid_list.currentItem()
        if item is not None:
            self._toggle_item(item)

    def _toggle_item(self, item):
        item.setCheckState(
            Qt.CheckState.Unchecked
            if item.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )

    def _on_folder_typed(self):
        folder = self.folder_edit.text().strip()
        if folder and Path(folder).is_dir():
            self.selected_videos = sorted(
                f for f in Path(folder).iterdir()
                if f.suffix.lower() in frame_extractor.VIDEO_EXTS
            )
            self._refresh_list()

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
        self.vid_list.blockSignals(True)
        self.vid_list.clear()
        for v in self.selected_videos:
            it = QListWidgetItem(v.name)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked)
            it.setData(Qt.ItemDataRole.UserRole, str(v))
            self.vid_list.addItem(it)
        self.vid_list.blockSignals(False)
        self.vid_list.setCurrentRow(-1)
        self._update_master()

    def _toggle_all(self):
        target = (Qt.CheckState.Checked
                  if self.chk_all.checkState() != Qt.CheckState.Unchecked
                  else Qt.CheckState.Unchecked)
        self.vid_list.blockSignals(True)
        for i in range(self.vid_list.count()):
            self.vid_list.item(i).setCheckState(target)
        self.vid_list.blockSignals(False)
        self._update_master()

    def _update_master(self, *_):
        n = self.vid_list.count()
        c = sum(1 for i in range(n)
                if self.vid_list.item(i).checkState() == Qt.CheckState.Checked)
        self.chk_all.blockSignals(True)
        if c == 0:
            self.chk_all.setCheckState(Qt.CheckState.Unchecked)
            self.chk_all.setText(f"Select all  ({n})")
        elif c == n:
            self.chk_all.setCheckState(Qt.CheckState.Checked)
            self.chk_all.setText(f"Select all  ({c}/{n})")
        else:
            self.chk_all.setCheckState(Qt.CheckState.PartiallyChecked)
            self.chk_all.setText(f"Select all  ({c}/{n})")
        self.chk_all.blockSignals(False)

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
