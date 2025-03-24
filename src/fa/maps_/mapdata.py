from typing import NamedTuple
from typing import Self

from PyQt6.QtCore import QSizeF
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage


class MapData(NamedTuple):
    width: float
    height: float
    image: QImage

    def size(self) -> QSizeF:
        return QSizeF(self.width, self.height)

    def image_size(self) -> QSizeF:
        return QSizeF(self.image.size())

    def scale_image_by(self, factor: int) -> Self:
        w = self.image.width()
        h = self.image.height()
        ratio = Qt.AspectRatioMode.KeepAspectRatio
        trans_mode = Qt.TransformationMode.SmoothTransformation
        scaled = self.image.scaled(w * factor, h * factor, ratio, trans_mode)
        return self._replace(image=scaled)
