"""MIT License

Copyright (c) 2020 fafafaf

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets

from src.replays.replaydetails.helpers import seconds_to_human


class ChartWidget(QtWidgets.QWidget):
    SPACE_BETWEEN_X_AXIS_TEXT = 60
    SPACE_BETWEEN_Y_AXIS_TEXT = 30

    selected_tick_signal = QtCore.pyqtSignal(int)

    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        self.setMouseTracking(True)

        self.l_margin = 38
        self.t_margin = 10
        self.r_margin = 3
        self.b_margin = 20

        self.mouse_pos = 0
        self.prev_mouse_pos = 0
        self.selected_tick = 0

        self.ticks = 0
        self.max_w = 0
        self.max_h = 0
        self.max_h_val = 0
        self.content_width = 0
        self.content_height = 0
        self.num_of_data = 0

        self.data: dict[int, list[int]] = {}
        self.small: dict[int, list[float]] = {}
        self.colors: dict[int, str] = {}

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(600, 200)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent | None) -> None:
        if e is None or not self.data:
            return

        index = e.pos().x()
        if self.l_margin <= index < self.geometry().width() - self.r_margin:
            self.mouse_pos = index - self.l_margin
            self.selected_tick = self.mouse_pos * self.num_of_sample
            self.update()
            if self.selected_tick < self.ticks:
                self.selected_tick_signal.emit(self.selected_tick)

    def reset(self) -> None:
        self.max_w = 0
        self.max_h = 0
        self.max_h_val = 0
        self.num_of_data = 0
        self.content_width = 0
        self.content_height = 0
        self.data = {}
        self.colors = {}
        self.small = {}

    def graph(
        self,
        data: dict[int, list[int]],
        max_h_val: int,
        colors: dict[int, str],
        ticks: int,
    ) -> None:
        self.max_h_val = max_h_val
        self.data = data
        self.colors = colors
        self.ticks = ticks
        self.num_of_data = len(next(iter(self.data.values())))
        self.recalculate_small()

    def recalculate_small(self) -> None:
        self.max_h, self.max_w = self.geometry().height(), self.geometry().width()
        self.content_height = self.max_h - self.t_margin - self.b_margin
        self.content_width = self.max_w - self.l_margin - self.r_margin

        self.num_of_sample = max(1, self.num_of_data // self.content_width)
        self.small = {
            j: [
                sum(sample_data[i*self.num_of_sample:(i+1)*self.num_of_sample]) / self.num_of_sample
                for i in range(self.content_width)
            ] for j, sample_data in self.data.items()
        }

    def resizeEvent(self, event: QtGui.QResizeEvent | None) -> None:  # type: ignore[override]
        self.recalculate_small()
        super().resizeEvent(event)

    def paintEvent(self, e: QtGui.QPaintEvent | None) -> None:  # type: ignore[override]
        if not self.data or e is None or self.num_of_data == 0:
            return
        p = QtGui.QPainter()
        p.begin(self)

        if self.mouse_pos != self.prev_mouse_pos and self.mouse_pos < self.max_w - self.r_margin:
            p.drawLine(
                self.l_margin + self.mouse_pos,
                self.t_margin,
                self.l_margin + self.mouse_pos,
                self.max_h - self.b_margin,
            )
        else:
            self.mouse_pos = 0

        for i in self.data:
            path = QtGui.QPainterPath()
            path.moveTo(self.l_margin, self.max_h - self.b_margin)
            for j in range(self.content_width):
                y_norm = self.small[i][j] / self.max_h_val * self.content_height
                y = self.max_h - self.b_margin - y_norm
                path.lineTo(self.l_margin + j, y)
            p.setPen(QtGui.QPen(QtGui.QColor(self.colors[i])))
            p.drawPath(path)

        p.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.gray, 1, QtCore.Qt.PenStyle.SolidLine))
        p.drawRect(self.l_margin, self.t_margin, self.content_width, self.content_height)

        for i in range(self.content_width // self.SPACE_BETWEEN_X_AXIS_TEXT + 1):
            rect = QtCore.QRectF(
                self.l_margin - 50 + (i * self.SPACE_BETWEEN_X_AXIS_TEXT),
                self.max_h - self.b_margin + 5,
                100,
                10,
            )
            seconds = round(i * self.SPACE_BETWEEN_X_AXIS_TEXT * self.num_of_sample / 10)
            text = seconds_to_human(seconds, sep="", full=False)
            p.drawText(rect, text, QtGui.QTextOption(QtCore.Qt.AlignmentFlag.AlignCenter))
            p.drawLine(
                self.l_margin + (i * self.SPACE_BETWEEN_X_AXIS_TEXT),
                self.max_h - self.b_margin + 2,
                self.l_margin + (i * self.SPACE_BETWEEN_X_AXIS_TEXT),
                self.max_h - self.b_margin - 2,
            )

        for i in range(self.content_height // self.SPACE_BETWEEN_Y_AXIS_TEXT + 1):
            rect = QtCore.QRectF(
                self.l_margin - 40,
                self.max_h - self.b_margin - 5 - (i * self.SPACE_BETWEEN_Y_AXIS_TEXT),
                35,
                10,
            )
            label = (self.max_h_val * i * self.SPACE_BETWEEN_Y_AXIS_TEXT / self.content_height)
            option = QtGui.QTextOption(
                QtCore.Qt.AlignmentFlag.AlignRight
                | QtCore.Qt.AlignmentFlag.AlignVCenter,
            )
            p.drawText(rect, f"{label:.2f}", option)
            p.drawLine(
                self.l_margin - 2,
                self.max_h - self.b_margin - i * self.SPACE_BETWEEN_Y_AXIS_TEXT,
                self.l_margin + 2,
                self.max_h - self.b_margin - i * self.SPACE_BETWEEN_Y_AXIS_TEXT,
            )

        p.end()
