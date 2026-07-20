from PySide6.QtCore import QThread, Signal


class GuiWorker(QThread):
    progress = Signal(float, int, str)   # pct 0-100, saved, video_name
    log      = Signal(str)
    finished_ok = Signal(int)

    def __init__(self, target, config, parent=None):
        super().__init__(parent)
        self.target = target
        self.config = dict(config)
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        self.config["progress_cb"] = lambda pct, saved, name: self.progress.emit(pct, saved, name)
        self.config["log_cb"] = self.log.emit
        self.config["cancel_cb"] = lambda: self._cancel
        try:
            total = self.target(self.config)
        except Exception as e:
            self.log.emit(f"ERROR: {e}")
            total = 0
        self.finished_ok.emit(total or 0)
