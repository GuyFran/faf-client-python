from typing import Any

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.qt.graphics.labeledbargraphitem import LabeledBarGraphItem

UNIT_TYPES = {
    "land": "Land",
    "air": "Air",
    "naval": "Naval",
    "tech1": "Tech 1",
    "tech2": "Tech 2",
    "tech3": "Tech 3",
    "experimental": "Experimental",
    "transportation": "Transportation",
    "engineer": "Engineer",
    "structures": "Structures",
    "cdr": "ACUs",
    "sacu": "SACUs",
}

BAR_GROUP_WIDTH = 0.8


class StatsVisualizer(QWidget):
    def __init__(self) -> None:
        QWidget.__init__(self)
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.stats = {}

    def _remove_old_widgets(self) -> None:
        while (item := self.main_layout.takeAt(0)) is not None:
            if (widget := item.widget()) is not None:
                widget.deleteLater()

    def _draw_no_data(self) -> None:
        label = QLabel("No game stats found")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = label.font()
        font.setBold(True)
        font.setPointSize(20)
        label.setFont(font)
        self.main_layout.addWidget(label)

    def draw_stats(self, data: dict[str, Any]) -> None:
        self._remove_old_widgets()

        if not data:
            self._draw_no_data()
            return

        self.stats = data["stats"]

        tabs = QTabWidget()
        self.main_layout.addWidget(tabs)

        score_tab = QWidget()
        score_layout = QVBoxLayout(score_tab)
        score_layout.setContentsMargins(0, 0, 0, 0)
        tabs.addTab(score_tab, "Scores")

        resource_tab = QWidget()
        resource_layout = QGridLayout(resource_tab)
        resource_layout.setContentsMargins(0, 0, 0, 0)
        tabs.addTab(resource_tab, "Resources")

        unit_tabs = QTabWidget()

        general_units_tab = QWidget()
        units_layout = QGridLayout(general_units_tab)
        units_layout.setContentsMargins(0, 0, 0, 0)
        unit_tabs.addTab(general_units_tab, "General")

        units_breakdown_tab = QWidget()
        units_scroll_layout = QVBoxLayout(units_breakdown_tab)
        units_scroll_layout.setContentsMargins(0, 0, 0, 0)

        units_scroll = QScrollArea()
        units_scroll.setContentsMargins(0, 0, 0, 0)
        units_scroll.setWidgetResizable(True)
        units_scroll_layout.addWidget(units_scroll)

        units_breakdown_widget = QWidget()
        units_breakdown_widget.setContentsMargins(0, 0, 0, 0)
        units_breakdown_layout = QGridLayout(units_breakdown_widget)
        units_breakdown_layout.setContentsMargins(0, 0, 0, 0)
        units_breakdown_widget.setObjectName("statisticsChartsScrollArea")
        units_scroll.setWidget(units_breakdown_widget)
        unit_tabs.addTab(units_breakdown_tab, "Breakdown")
        tabs.addTab(unit_tabs, "Units")

        balance_tab = QWidget()
        balance_layout = QGridLayout(balance_tab)
        balance_layout.setContentsMargins(0, 0, 0, 0)
        tabs.addTab(balance_tab, "Build vs Loss")

        self.add_resource_plots(resource_layout)
        self.add_unit_plots(units_layout)
        self.add_balance_plots(balance_layout)
        self.add_score_plot(score_layout)
        self.add_units_breakdown_plot(units_breakdown_layout)

    def add_units_breakdown_plot(self, layout: QGridLayout) -> None:
        bar_width = BAR_GROUP_WIDTH / 3
        player_names = [player["name"] for player in self.stats]
        x_pos = np.arange(len(self.stats))

        for index, (unit_type, title) in enumerate(UNIT_TYPES.items()):
            if unit_type not in self.stats[0]["units"]:
                continue

            plot = pg.PlotWidget(title=title)
            plot.setLabel("left", "Count")
            plot.addLegend()
            plot.setMinimumHeight(300)

            for i, (color, stat) in enumerate(zip(("b", "r", "g"), ("built", "lost", "kills"))):
                values = [player["units"][unit_type][stat] for player in self.stats]
                bar = LabeledBarGraphItem(
                    categories=player_names,
                    x=x_pos + (i - 1) * bar_width,
                    height=values,
                    width=bar_width,
                    brush=color,
                    name=stat.title(),
                )
                plot.addItem(bar)
            plot.getAxis("bottom").setTicks(
                [[(i, name) for i, name in enumerate(player_names)]],
            )
            layout.addWidget(plot, index // 2, index % 2)

    def _create_income_plots(self) -> list[pg.PlotWidget]:
        plots = []

        player_names = [player["name"] for player in self.stats]
        x_pos = np.arange(len(player_names))
        bar_width = BAR_GROUP_WIDTH / 3
        colors = {
            "mass": ("b", "r", "g"),
            "energy": ("y", "m", "c"),
        }
        for resource in ("mass", "energy"):
            plot = pg.PlotWidget(title=f"{resource.capitalize()}")
            plot.setLabel("left", resource)
            plot.addLegend()

            metrics = (
                (f"{resource}in", "total", "Collected"),
                (f"{resource}out", "total", "Spent"),
                (f"{resource}out", "excess", "Wasted"),
            )
            for i, (category, metric, name) in enumerate(metrics):
                values = [player["resources"][category][metric] for player in self.stats]
                bar = LabeledBarGraphItem(
                    categories=player_names,
                    x=x_pos + (i - len(metrics)/2 + 0.5) * bar_width,
                    height=values,
                    width=bar_width,
                    brush=colors[resource][i],
                    name=name,
                )
                plot.addItem(bar)
            plot.getAxis("bottom").setTicks([[(i, name) for i, name in enumerate(player_names)]])
            plots.append(plot)
        return plots

    def _create_income_breakdown_plots(self) -> list[pg.PlotWidget]:
        plots = []

        player_names = [player["name"] for player in self.stats]
        x_pos = np.arange(len(player_names))
        bar_width = 0.4

        colors = {
            "mass": ("b", "c"),
            "energy": ("y", "m"),
        }
        for resource in ("mass", "energy"):
            plot = pg.PlotWidget(title=f"{resource.title()} Income Breakdown")
            plot.setLabel("left", resource)
            plot.addLegend()

            total = np.array(
                [player["resources"][f"{resource}in"]["total"] for player in self.stats],
            )
            reclaimed = np.array(
                [player["resources"][f"{resource}in"]["reclaimed"] for player in self.stats],
            )
            produced = total - reclaimed
            for i, (name, val) in enumerate(zip(("Produced", "Reclaimed"), (produced, reclaimed))):
                bar = LabeledBarGraphItem(
                    categories=player_names,
                    x=x_pos + (i - 0.5) * bar_width,
                    height=val,
                    width=bar_width,
                    brush=colors[resource][i],
                    name=name,
                )
                plot.addItem(bar)
            plot.getAxis("bottom").setTicks(
                [[(i, name) for i, name in enumerate(player_names)]],
            )
            plots.append(plot)
        return plots

    def add_resource_plots(self, layout: QGridLayout) -> None:
        income_plots = self._create_income_plots()
        breakdown_plots = self._create_income_breakdown_plots()
        for index, plot in enumerate(income_plots + breakdown_plots):
            layout.addWidget(plot, index // 2, index % 2)

    def add_unit_plots(self, layout: QGridLayout) -> None:
        unit_types = [
            "land",
            "air",
            "naval",
            "tech1",
            "tech2",
            "tech3",
            "experimental",
        ]
        colors = {
            "land": (0, 255, 0),            # Green
            "air": (100, 100, 255),         # Light Blue
            "naval": (0, 0, 255),           # Dark Blue
            "tech1": (255, 255, 0),         # Yellow
            "tech2": (255, 128, 0),         # Orange
            "tech3": (255, 0, 0),           # Red
            "experimental": (255, 0, 255),  # Magenta
        }

        player_names = [player["name"] for player in self.stats]
        plot_types = ["built", "lost", "kills"]
        x_pos = np.arange(len(player_names))
        bar_width = BAR_GROUP_WIDTH / len(unit_types)

        for index, plot_type in enumerate(plot_types):
            plot = pg.PlotWidget(title=f"Units {plot_type.capitalize()}")
            plot.addLegend()
            plot.setLabel("left", "Units")

            for i, unit_type in enumerate(unit_types):
                values = [player["units"][unit_type][plot_type] for player in self.stats]
                bar = LabeledBarGraphItem(
                    categories=player_names,
                    x=x_pos + (i - len(unit_types)/2 + 0.5) * bar_width,
                    height=values,
                    width=bar_width,
                    brush=colors[unit_type],
                    name=unit_type,
                )
                plot.addItem(bar)
            plot.getAxis("bottom").setTicks([[(i, name) for i, name in enumerate(player_names)]])
            layout.addWidget(plot, index // 2, index % 2)

    def _create_kd_plot(self) -> pg.PlotWidget:
        player_names = [player["name"] for player in self.stats]
        x_pos = np.arange(len(player_names))

        kd_plot = pg.PlotWidget(title="Kill/Death Ratio (Unit Count)")
        kd_plot.addLegend()
        kd_plot.setLabel("left", "Ratio")

        kd_values = [
            player["general"]["kills"]["count"] / (player["general"]["lost"]["count"] or 1)
            for player in self.stats
        ]

        kd_bar = LabeledBarGraphItem(
            categories=player_names,
            x=x_pos,
            height=kd_values,
            width=BAR_GROUP_WIDTH,
            brush="b",
            name="KD ratio",
        )
        kd_plot.addItem(kd_bar)
        kd_plot.getAxis("bottom").setTicks([[(i, name) for i, name in enumerate(player_names)]])

        line = pg.InfiniteLine(
            pos=1,
            angle=0,
            pen=pg.mkPen("r", style=pg.QtCore.Qt.PenStyle.DashLine),
        )
        kd_plot.addItem(line)
        return kd_plot

    def add_balance_plots(self, layout: QGridLayout) -> None:
        player_names = [player["name"] for player in self.stats]
        x_pos = np.arange(len(player_names))

        categories = ["mass", "energy", "count"]
        width = BAR_GROUP_WIDTH / len(categories)
        for index, category in enumerate(categories):
            plot = pg.PlotWidget(title=f"Build vs Loss ({category})")
            plot.addLegend()
            plot.setLabel("left", category)
            plot.setMinimumHeight(300)

            for i, (color, stat) in enumerate(zip(("b", "r", "g"), ("built", "lost", "kills"))):
                values = [player["general"][stat][category] for player in self.stats]
                bar = LabeledBarGraphItem(
                    categories=player_names,
                    x=x_pos + (i - len(categories)/2 + 0.5) * width,
                    height=values,
                    width=width,
                    brush=color,
                    name=stat.title(),
                )
                plot.addItem(bar)
            plot.getAxis("bottom").setTicks(
                [[(i, name) for i, name in enumerate(player_names)]],
            )
            layout.addWidget(plot, index // 2, index % 2)
        layout.addWidget(self._create_kd_plot(), 1, 1)

    def add_score_plot(self, layout: QVBoxLayout) -> None:
        score_plot = pg.PlotWidget(title="Player Scores")
        score_plot.setLabel("left", "Score")

        player_names = [player["name"] for player in self.stats]
        player_scores = [player["general"]["score"] for player in self.stats]

        x_pos = np.arange(len(player_names))
        score_bar = LabeledBarGraphItem(
            categories=player_names,
            x=x_pos,
            height=player_scores,
            width=BAR_GROUP_WIDTH,
            brush=(0, 150, 255),
            name="Score",
        )
        score_plot.addItem(score_bar)
        score_plot.getAxis("bottom").setTicks([[(i, name) for i, name in enumerate(player_names)]])
        layout.addWidget(score_plot)
