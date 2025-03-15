from collections import Counter
from operator import itemgetter
from typing import Any
from typing import NamedTuple

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtCore import QTimer
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QSpinBox
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.config import Settings
from src.replays.replaydetails.rangeslider import RangeSlider


class HeatmapProperties(NamedTuple):
    height: int = 1024
    width: int = 1024


class Heatmap(QWidget):
    def __init__(self) -> None:
        QWidget.__init__(self)
        _viewbox = pg.ViewBox()
        self.heatmap = pg.ImageItem()
        _viewbox.addItem(self.heatmap)

        _graphics_layout = QGridLayout()
        _graphics_layout.setSpacing(6)
        _graphics_view = pg.GraphicsView()
        _graphics_view.setCentralItem(_viewbox)

        _graphics_layout.addWidget(_graphics_view, 0, 0, 7, 1)

        self.hist = self.color_bar_hist()
        self.hist.setImageItem(self.heatmap)
        _graphics_layout.addWidget(self.hist, 0, 1)

        self.smooth_check_box = QCheckBox("Smoothing")
        smoothing = Settings.get("replaycard.heatmap/smoothing", True, type=bool)
        self.smooth_check_box.setChecked(smoothing)
        self.smooth_check_box.checkStateChanged.connect(self._generate_new_heatmap)
        self.smooth_check_box.checkStateChanged.connect(
            lambda state: Settings.set(
                "replaycard.heatmap/smoothing",
                state == Qt.CheckState.Checked,
            ),
        )
        _graphics_layout.addWidget(self.smooth_check_box, 1, 1)

        debounce_layout = QHBoxLayout()

        self.debounce_check_box = QCheckBox("Debounce:")
        debounce_tooltip = "Delay between selecting time range and applying smoothing"
        self.debounce_check_box.setToolTip(debounce_tooltip)
        debounce = Settings.get("replaycard.heatmap/debounce", True, type=bool)
        self.debounce_check_box.setChecked(debounce)
        self.debounce_check_box.checkStateChanged.connect(
            lambda state: Settings.set(
                "replaycard.heatmap/smoothing",
                state == Qt.CheckState.Checked,
            ),
        )

        self.debounce_spin_box = QSpinBox()
        self.debounce_spin_box.setMinimum(0)
        self.debounce_spin_box.setMaximum(1000)
        debounce_time_ms = Settings.get("replaycard.heatmap/debounce_time_ms", 100, type=int)
        self.debounce_spin_box.setValue(debounce_time_ms)
        self.debounce_spin_box.setSuffix(" ms")
        self.debounce_spin_box.valueChanged.connect(
            lambda value: Settings.set("replaycard.heatmap/debounce_time_ms", value),
        )

        debounce_layout.addWidget(self.debounce_check_box)
        debounce_layout.addWidget(self.debounce_spin_box)
        _graphics_layout.addItem(debounce_layout, 2, 1)

        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._generate_new_heatmap)

        sigma_layout = QHBoxLayout()
        self.x_sigma = QSpinBox()
        self.x_sigma.setMinimum(0)
        self.x_sigma.setMaximum(100)
        self.x_sigma.setPrefix("x: ")
        self.x_sigma.setValue(2)
        self.y_sigma = QSpinBox()
        self.y_sigma.setMinimum(0)
        self.y_sigma.setMaximum(100)
        self.y_sigma.setPrefix("y: ")
        self.y_sigma.setValue(2)
        sigma_layout.addWidget(self.x_sigma)
        sigma_layout.addWidget(self.y_sigma)

        self.regen_button = QPushButton("Regenerate heatmap")
        self.regen_button.clicked.connect(self._generate_new_heatmap)

        _graphics_layout.addWidget(QLabel("Standard deviation for Gaussian kernel:"), 4, 1)
        _graphics_layout.addItem(sigma_layout, 5, 1)
        _graphics_layout.addWidget(self.regen_button, 6, 1)

        self.heatmapRangeSlider = RangeSlider()
        self.heatmapRangeSlider.setOrientation(Qt.Orientation.Horizontal)
        self.heatmapRangeSlider.sliderMoved.connect(self.debounce)
        self.heatmapSliderText = QLabel()
        self.heatmapSliderText.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.heatmapSliderText.setMaximumHeight(12)

        heatmapTabLayout = QVBoxLayout()

        heatmapTabLayout.addItem(_graphics_layout)
        heatmapTabLayout.addWidget(self.heatmapRangeSlider)
        heatmapTabLayout.addWidget(self.heatmapSliderText)

        self.setLayout(heatmapTabLayout)
        self.heatmap_properties = HeatmapProperties()

        self.pts_norm = []

    def color_bar_hist(self) -> pg.HistogramLUTWidget:
        hist = pg.HistogramLUTWidget()
        cmap_name = Settings.get("replaycard.heatmap/colormap", "preset-gradient:flame")
        if cmap_name.startswith("preset-gradient"):
            hist.item.gradient.loadPreset(cmap_name.split(":")[1])
        else:
            cmap = pg.colormap.get(cmap_name)
            hist.item.gradient.setColorMap(cmap)
            hist.item.gradient.showTicks(False)
        hist.item.gradient.menu.sigColorMapTriggered.connect(
            lambda colormap: Settings.set("replaycard.heatmap/colormap", colormap.name),
        )
        return hist

    def _generate_new_heatmap(self) -> None:
        if len(self.pts_norm) == 0:
            return

        lowtick = self.heatmapRangeSlider.low()
        hightick = self.heatmapRangeSlider.high()
        img = self.return_heatmap(lowtick, hightick)

        if self.smooth_check_box.isChecked() and not self.debounce_timer.isActive():
            img = pg.gaussianFilter(img, (self.x_sigma.value(), self.y_sigma.value(), 0))

        self.heatmap.setImage(img)
        self.heatmapSliderText.setText(
            f"{self.seconds_to_human(lowtick // 10)}"
            f"({lowtick})"
            f"{self.seconds_to_human(hightick // 10)}"
            f"({hightick})",
        )

    def debounce(self) -> None:
        self._generate_new_heatmap()
        if self.debounce_check_box.isChecked():
            self.debounce_timer.start(self.debounce_spin_box.value())

    def redraw_heatmap(self) -> None:
        self.generate_new_heatmap(self.heatmapRangeSlider.low(), self.heatmapRangeSlider.high())

    def seconds_to_human(self, seconds: int) -> str:
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "%d:%02d:%02d" % (h, m, s)

    def set_pts(self, pts: list) -> None:
        self.pts_norm = self.points_normalized(pts)
        max_sigma = (len(pts) + 1) // 6
        self.x_sigma.setMaximum(max_sigma)
        self.y_sigma.setMaximum(max_sigma)

    def points_normalized(self, pts: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
        pts.sort(key=lambda elem: elem[0])

        min_x = min(pts, key=itemgetter(1))[1] if pts else 0
        min_y = min(pts, key=itemgetter(2))[2] if pts else 0
        max_x = max(pts, key=itemgetter(1))[1] if pts else 0
        max_y = max(pts, key=itemgetter(2))[2] if pts else 0

        w = self.heatmap_properties.width - 1
        h = self.heatmap_properties.height - 1

        return [
            (
                tick,
                round(((x - min_x) / (max_x - min_x)) * w),
                round((1 - ((y - min_y) / (max_y - min_y))) * h),
            )
            for tick, x, y in pts
        ]

    def create_(self, ticks: int) -> None:
        self.heatmapRangeSlider.setMinimum(0)
        self.heatmapRangeSlider.setMaximum(ticks)
        self.heatmapRangeSlider.setLow(0)
        self.heatmapRangeSlider.setHigh(ticks)
        self._generate_new_heatmap()

    @pyqtSlot(int, int)
    def generate_new_heatmap(self, lowtick: int, hightick: int) -> None:
        img = self.return_heatmap(lowtick, hightick)
        self.heatmap.setImage(img)
        self.heatmapSliderText.setText(
            self.seconds_to_human(lowtick // 10)
            + " (" + str(lowtick) + ") - "
            + self.seconds_to_human(hightick // 10)
            + " (" + str(hightick) + ")",
        )

    def return_heatmap(self, fromTick: int = 0, toTick: int = -1) -> np.ndarray | None:
        pts = self.return_pts(fromTick, toTick)
        if len(pts) != 0:
            pixels = pg.numpy.zeros((self.heatmap_properties.width, self.heatmap_properties.height))
            for (x, y), count in pts.items():
                pixels[x][y] += count
            return pixels

    def return_pts(self, fromTick: int, toTick: int) -> Any:
        return Counter(
            (x, y)
            for (tick, x, y) in self.pts_norm
            if (fromTick < tick < toTick) or (toTick == -1)
        )
