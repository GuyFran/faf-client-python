import logging
import shutil

from PyQt6.QtCore import QThread
from PyQt6.QtCore import pyqtSignal

logger = logging.getLogger(__name__)


class ZipThread(QThread):
    zip_ready = pyqtSignal(str)
    zip_error = pyqtSignal()

    def __init__(self, target_path: str, root_dir: str, base_dir: str) -> None:
        super().__init__()
        self.target_path = target_path
        self.root_dir = root_dir
        self.base_dir = base_dir

    def run(self) -> None:
        try:
            zipped = shutil.make_archive(self.target_path, "zip", self.root_dir, self.base_dir)
        except Exception:
            logger.exception(
                "Could not zip files from '%s' to '%s'",
                self.root_dir,
                self.target_path,
            )
            self.zip_error.emit()
        else:
            self.zip_ready.emit(zipped)
