from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QEvent
from PySide6.QtGui import QKeyEvent, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QListWidget, QListWidgetItem,
    QFileDialog, QGroupBox, QMessageBox, QToolButton, QStackedWidget,
    QFrame, QAbstractSpinBox, QCheckBox,
)

import frame_extractor
from gui.path_edit import PathLineEdit


class ExtractPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_videos: list[Path] = []
        self.settings = QSettings("screenshotter", "extract")
        self._last_row: int = -1
        self._build()
        self._restore()
        self._wire_shortcuts()
        self._set_tab_order()

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
        self.vid_list.setMinimumHeight(120)
        self.vid_list.setMaximumHeight(180)
        self.vid_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.vid_list.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.vid_list.itemActivated.connect(self._toggle_item)
        self.vid_list.itemChanged.connect(self._update_master)
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
        self.spin_val.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        main_row.addWidget(self.spin_val)

        self.combo_unit = QComboBox()
        self.combo_unit.addItems(["frames", "seconds"])
        self.combo_unit.setFixedWidth(100)
        self.combo_unit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        main_row.addWidget(self.combo_unit)
        self.combo_unit.currentTextChanged.connect(self._on_unit_change)

        main_row.addSpacing(16)
        main_row.addWidget(QLabel("Output"))
        self.out_edit = PathLineEdit("screenshots")
        main_row.addWidget(self.out_edit, 1)
        btn_out = QPushButton("Browse")
        btn_out.clicked.connect(self._pick_output)
        btn_out.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.adv_toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.combo_fmt.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        fmt_row.addWidget(self.combo_fmt)
        fmt_row.addSpacing(12)
        fmt_row.addWidget(QLabel("Quality"))
        self.spin_q = QSpinBox()
        self.spin_q.setRange(1, 100)
        self.spin_q.setValue(92)
        self.spin_q.setFixedWidth(70)
        self.spin_q.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_q.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.start_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        range_row.addWidget(self.start_edit)
        range_row.addSpacing(12)
        range_row.addWidget(QLabel("End"))
        self.end_edit = QLineEdit()
        self.end_edit.setPlaceholderText("blank = end")
        self.end_edit.setFixedWidth(120)
        self.end_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.btn_start.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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

    def _wire_shortcuts(self):
        for seq in ("Shift+Return", "Shift+Enter"):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(lambda: self.btn_start.click())
        for seq in ("Return", "Enter"):
            sc = QShortcut(QKeySequence(seq), self.vid_list)
            sc.setContext(Qt.ShortcutContext.WidgetShortcut)
            sc.activated.connect(self._toggle_current)
        # ESC = drop focus and jump to video list for arrow-key nav
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
        QWidget.setTabOrder(self.chk_all, self.spin_val)
        QWidget.setTabOrder(self.spin_val, self.out_edit)
        QWidget.setTabOrder(self.out_edit, self.btn_start)

    def keyPressEvent(self, e):
        # Route arrow keys to video list regardless of current focus
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
            self._load_folder(folder)

    def _refresh(self):
        folder = self.folder_edit.text().strip()
        if not folder or not Path(folder).is_dir():
            return
        prev_checked = {v.name for v in self.get_checked_videos()}
        self._load_folder(folder)
        # restore check state
        for i in range(self.vid_list.count()):
            it = self.vid_list.item(i)
            if it.text() not in prev_checked:
                it.setCheckState(Qt.CheckState.Unchecked)

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
        self._persist()
        return cfg

    def _persist(self):
        s = self.settings
        s.setValue("folder", self.folder_edit.text())
        s.setValue("unit", self.combo_unit.currentText())
        s.setValue("val", self.spin_val.value())
        s.setValue("format", self.combo_fmt.currentText())
        s.setValue("quality", self.spin_q.value())
        s.setValue("output", self.out_edit.text())
        s.setValue("start", self.start_edit.text())
        s.setValue("end", self.end_edit.text())
        s.sync()

    def _restore(self):
        s = self.settings
        folder = s.value("folder", "")
        if folder and Path(folder).is_dir():
            self.folder_edit.setText(folder)
            self._load_folder(folder)
        unit = s.value("unit", "frames")
        idx = self.combo_unit.findText(unit)
        if idx >= 0:
            self.combo_unit.setCurrentIndex(idx)
        try:
            self.spin_val.setValue(int(s.value("val", 50)))
        except (TypeError, ValueError):
            pass
        fmt = s.value("format", "jpg")
        idx = self.combo_fmt.findText(fmt)
        if idx >= 0:
            self.combo_fmt.setCurrentIndex(idx)
        try:
            self.spin_q.setValue(int(s.value("quality", 92)))
        except (TypeError, ValueError):
            pass
        out = s.value("output", "screenshots")
        if out:
            self.out_edit.setText(out)
        self.start_edit.setText(s.value("start", "") or "")
        self.end_edit.setText(s.value("end", "") or "")

    @staticmethod
    def _parse_ts(text):
        text = text.strip()
        if not text:
            return None
        try:
            return frame_extractor.parse_ts(text)
        except Exception:
            return None
