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
        self.max_h_val = 0

        self.data: list[list[int]] = [[]]
        self.colors: list[str] = []

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(600, 200)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent | None) -> None:
        if e is None:
            return

        if self.data:
            index = e.pos().x()
            if self.l_margin <= index < self.geometry().width() - self.r_margin:
                self.mouse_pos = index - self.l_margin
                self.update()
                if self.selected_tick < self.ticks:
                    self.selected_tick_signal.emit(self.selected_tick)

    def reset(self) -> None:
        self.max_h_val = 0
        self.data = [[]]
        self.colors = []

    def graph(self, data: list[list[int]], max_h_val: int, colors: list[str], ticks: int) -> None:
        self.max_h_val = max_h_val
        self.data = data
        self.colors = colors
        self.ticks = ticks
        self.update()

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        if self.data:
            max_h, max_w = self.geometry().height(), self.geometry().width()
            content_height = max_h - self.t_margin - self.b_margin
            content_width = max_w - self.l_margin - self.r_margin

            num_of_sources = len(self.data)
            num_of_data = len(self.data[0])
            if num_of_data == 0:
                return

            space_between_x_axis_text = 60
            space_between_y_axis_text = 30

            small = [[] for _ in range(num_of_sources)]
            num_of_sample = max(1, num_of_data // content_width)

            self.selected_tick = self.mouse_pos * num_of_sample

            for i in range(content_width):
                for j in range(num_of_sources):
                    actions = sum(self.data[j][i*num_of_sample:(i+1)*num_of_sample]) / num_of_sample
                    small[j].append(actions)

            p = QtGui.QPainter()
            p.begin(self)

            if self.mouse_pos != self.prev_mouse_pos and self.mouse_pos < max_w - self.r_margin:
                p.drawLine(
                    self.l_margin + self.mouse_pos,
                    self.t_margin,
                    self.l_margin + self.mouse_pos,
                    max_h - self.b_margin,
                )
            else:
                self.mouse_pos = 0

            for i in range(num_of_sources):
                path = QtGui.QPainterPath()
                path.moveTo(self.l_margin, max_h - self.b_margin)
                for j in range(content_width):
                    y_norm = small[i][j] / self.max_h_val * content_height
                    y = max_h - self.b_margin - y_norm
                    path.lineTo(self.l_margin + j, y)
                p.setPen(QtGui.QPen(QtGui.QColor(self.colors[i])))
                p.drawPath(path)

            p.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.gray, 1, QtCore.Qt.PenStyle.SolidLine))
            p.drawRect(self.l_margin, self.t_margin, content_width, content_height)

            for i in range(content_width // space_between_x_axis_text + 1):
                rect = QtCore.QRectF(
                    self.l_margin - 50 + (i * space_between_x_axis_text),
                    max_h - self.b_margin + 5,
                    100,
                    10,
                )
                seconds = round(i * space_between_x_axis_text * num_of_sample / 10)
                text = seconds_to_human(seconds, sep="", full=False)
                p.drawText(rect, text, QtGui.QTextOption(QtCore.Qt.AlignmentFlag.AlignCenter))
                p.drawLine(
                    self.l_margin + (i * space_between_x_axis_text),
                    max_h - self.b_margin + 2,
                    self.l_margin + (i * space_between_x_axis_text),
                    max_h - self.b_margin - 2,
                )

            for i in range(content_height // space_between_y_axis_text + 1):
                rect = QtCore.QRectF(
                    self.l_margin - 40,
                    max_h - self.b_margin - 5 - (i * space_between_y_axis_text),
                    35,
                    10,
                )
                label = (self.max_h_val * i * space_between_y_axis_text * 1.0 / content_height)
                option = QtGui.QTextOption(
                    QtCore.Qt.AlignmentFlag.AlignRight
                    | QtCore.Qt.AlignmentFlag.AlignVCenter,
                )
                p.drawText(rect, f"{label:.2f}", option)
                p.drawLine(
                    self.l_margin - 2,
                    max_h - self.b_margin - i * space_between_y_axis_text,
                    self.l_margin + 2,
                    max_h - self.b_margin - i * space_between_y_axis_text,
                )

            p.end()
