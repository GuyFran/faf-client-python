from enum import Enum
from enum import auto
from typing import Iterable

from PyQt6.QtCore import QPointF
from PyQt6.QtCore import QRectF
from PyQt6.QtCore import QSize
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QFontMetricsF
from PyQt6.QtGui import QPainter
from PyQt6.QtGui import QPixmap
from PyQt6.QtGui import QTextOption

from src import util
from src.fa.maps_.map_utils import get_save_file
from src.fa.maps_.mapdata import MapData


def parse_positions(savefile: str) -> dict[str, dict[str, QPointF]]:
    """When luaparser is fast enough, we can use it to parse positions:

    parser = luaparser.luaParser(savefile)
    positions = parser.parse({
     "markers>hydro*>position": "hydro:__parent__",
     "markers>mass*>position": "mass:__parent__",
     "markers>mex*>position": "mex:__parent__",
     "markers>army*>position": "army:__parent__",
    })
    """
    class State(Enum):
        NONE = auto()
        ARMY = auto()
        HYDRO = auto()
        MASS = auto()

    res = {"army": {}, "hydro": {}, "mass": {}}
    state = State.NONE
    army = ""
    mass_cnt = 0
    hydro_cnt = 0
    with open(savefile, "rt") as file:
        for line in file:
            if line.find("ARMY_") > -1:
                state = State.ARMY
                army = line.strip().split("'")
            elif line.find("STRING( 'Mass' )") > -1:
                state = State.MASS
            elif line.find("STRING( 'Hydrocarbon' )") > -1:
                state = State.HYDRO

            if line.find("position") > -1:
                # ['position'] = VECTOR3( x, z, y )
                x, _, y = map(float, line.strip()[24:-2].split(", ", 3))
                match state:
                    case State.ARMY:
                        res["army"][army[1]] = QPointF(x, y)
                        state = State.NONE
                    case State.HYDRO:
                        hydro_cnt += 1
                        res["hydro"][hydro_cnt] = QPointF(x, y)
                        state = State.NONE
                    case State.MASS:
                        mass_cnt += 1
                        res["mass"][mass_cnt] = QPointF(x, y)
                        state = State.NONE
    return res


def add_markers(
        mapdir: str,
        mapdata: MapData,
        armies: dict | None = None,
        *,
        scale: int = 1,
) -> None:
    if (savefile := get_save_file(mapdir)) is None:
        return
    scale_factor = (1 + scale) / 2

    # icons should be drawn in certain order: first layer is hydros,
    # second - mass, and army on top. made so that previews not
    # look messed up.
    positions = parse_positions(savefile)
    painter = QPainter()
    painter.begin(mapdata.image)
    draw_resource_markers(
        painter,
        util.THEME.pixmap("vaults/map_icons/hydro.png"),
        QSize(10, 10),
        positions["hydro"].values(),
        mapdata,
        scale_factor=scale_factor,
    )
    draw_resource_markers(
        painter,
        util.THEME.pixmap("vaults/map_icons/mass.png"),
        QSize(8, 8),
        positions["mass"].values(),
        mapdata,
        scale_factor=scale_factor,
    )
    armyicon = util.THEME.pixmap("vaults/map_icons/army.png")
    if armies is not None:
        color_ = QColor(115, 115, 115)
        mask = armyicon.createMaskFromColor(color_, Qt.MaskMode.MaskOutColor)
        army_positions = positions["army"]
        for army_name, pos in army_positions.items():
            if (army := armies.get(army_name.upper())) is None:
                continue
            army_pos = normalize_pos(pos, mapdata)
            color = QColor(army["hexcolor"])
            painter.setPen(color)
            target = draw_army_icon(painter, armyicon, scale, army_pos, QPixmap(mask))
            if target is None:
                continue
            player_name = army["PlayerName"]
            draw_army_name(painter, player_name, army_pos, target.bottom())
    else:
        for pos in positions["army"].values():
            army_pos = normalize_pos(pos, mapdata)
            draw_army_icon(painter, armyicon, scale, army_pos)
    painter.end()


def normalize_pos(
        pos: QPointF,
        mapdata: MapData,
) -> QPointF:
    return QPointF(
        pos.x() * mapdata.image_size().width() / mapdata.size().width(),
        pos.y() * mapdata.image_size().height() / mapdata.size().height(),
    )


def draw_army_name(
        painter: QPainter,
        name: str,
        army_pos: QPointF,
        target_top: float,
) -> None:
    font = painter.font()
    font_metrics = QFontMetricsF(font)
    text_option = QTextOption(Qt.AlignmentFlag.AlignCenter)
    contour = QRectF(
        0.0,
        0.0,
        font_metrics.horizontalAdvance(name, text_option),
        font_metrics.height(),
    )
    contour.moveCenter(QPointF(army_pos.x() - 1, army_pos.y() + 1))
    contour.moveTop(target_top + 1)
    painter.setPen(Qt.GlobalColor.black)
    painter.drawText(contour, name, text_option)

    name_rect = QRectF(contour)
    name_rect.moveCenter(army_pos)
    name_rect.moveTop(target_top)
    painter.setPen(Qt.GlobalColor.white)
    painter.drawText(name_rect, name, text_option)


def draw_army_icon(
        painter: QPainter,
        pix: QPixmap,
        scale: int,
        pos: QPointF,
        mask: QPixmap | None = None,
) -> QRectF | None:
    if pos.isNull():
        return
    transform = Qt.TransformationMode.SmoothTransformation
    scaled_pix = pix.scaledToHeight(pix.height() + (scale - 1) * 3, transform)
    source = QRectF(0.0, 0.0, pix.width(), pix.height())
    target = QRectF(0.0, 0.0, scaled_pix.width(), scaled_pix.height())
    target.moveCenter(pos)
    painter.drawPixmap(target, pix, source)
    if mask is not None:
        painter.drawPixmap(target, mask, source)
    return target


def draw_resource_markers(
        painter: QPainter,
        pix: QPixmap,
        default_size: QSize,
        positions: Iterable[QPointF],
        mapdata: MapData,
        *,
        scale_factor: float = 1.0,
) -> None:
    trans_mode = Qt.TransformationMode.SmoothTransformation
    icon = pix.scaledToWidth(int(default_size.width() * scale_factor), trans_mode)
    for pos in positions:
        pos_on_img = normalize_pos(pos, mapdata)
        if pos_on_img.isNull():
            continue
        source = QRectF(0.0, 0.0, icon.width(), icon.height())
        target = QRectF(source)
        target.moveCenter(pos_on_img)
        painter.drawPixmap(target, icon, source)
