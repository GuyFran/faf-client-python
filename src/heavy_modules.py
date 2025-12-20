import importlib.util
import sys
from types import ModuleType

from PyQt6.QtCore import QThread


def lazy_import(name: str, backup_name: str = "") -> ModuleType:
    try:
        if (spec := importlib.util.find_spec(name)) is None:
            raise ModuleNotFoundError
    except ModuleNotFoundError:
        spec = importlib.util.find_spec(backup_name)
        name = backup_name
    assert spec is not None
    assert spec.loader is not None
    loader = importlib.util.LazyLoader(spec.loader)
    spec.loader = loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


np = lazy_import("numpy")
pg = lazy_import("pyqtgraph")
scipy_ndimage = lazy_import("scipy_ndimage.ndimage._filters", "scipy")


class _BackgroundImporter(QThread):
    def run(self) -> None:
        dir(pg)
        dir(np)
        dir(scipy_ndimage)
        self.quit()


BackgroundImporter = _BackgroundImporter()
