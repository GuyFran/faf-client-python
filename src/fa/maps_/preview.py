import io
import os
import struct

from PyQt6.QtGui import QImage
from PyQt6.QtGui import QPixmap
from PyQt6.QtGui import QScreen

from src.fa.maps_._preview import add_markers
from src.fa.maps_.map_utils import get_scmap_file
from src.fa.maps_.mapdata import MapData


def extract_dds(scmap: str, dest: str) -> bool:
    """
    magic = struct.unpack('i', scmap.read(4))[0]
    version_major = struct.unpack('i', scmap.read(4))[0]
    unk_edfe = struct.unpack('i', scmap.read(4))[0]
    unk_efbe = struct.unpack('i', scmap.read(4))[0]
    width = struct.unpack('f', scmap.read(4))[0]
    height = struct.unpack('f', scmap.read(4))[0]
    unk_32 = struct.unpack('i', scmap.read(4))[0]
    unk_16 = struct.unpack('h', scmap.read(2))[0]
    """
    with open(scmap, "rb") as mapfile, open(dest, "wb") as outfile:
        mapfile.seek(30)
        dds_size = int.from_bytes(mapfile.read(4), "little")
        outfile.write(mapfile.read(dds_size))
    return os.path.exists(dest)


def map_data_from_scmap(scmap: str) -> MapData:
    with open(scmap, "rb") as mapfile:
        mapfile.seek(16)
        width, = struct.unpack("f", mapfile.read(4))
        height, = struct.unpack("f", mapfile.read(4))
        mapfile.seek(34)
        image = image_from_dds_data(mapfile)
    return MapData(width, height, image)


def image_from_dds(sourcename: str) -> QImage:
    with open(sourcename, "rb") as file:
        return image_from_dds_data(file)


def image_from_dds_data(reader: io.BufferedReader) -> QImage:
    header = reader.read(128)
    height = int.from_bytes(header[12:16], "little")
    width = int.from_bytes(header[16:20], "little")
    body_size = height * width * 4
    img = bytearray(body_size)
    reader.readinto(img)
    return QImage(
        bytes(img),
        width,
        height,
        QImage.Format.Format_RGBA8888,
    ).rgbSwapped()


def create_large_preview(
        mapdir: str,
        armies: dict | None = None,
        *,
        scale: int = 1,
) -> QPixmap:
    scmap = get_scmap_file(mapdir)
    assert scmap is not None
    mapdata = map_data_from_scmap(scmap).scale_image_by(scale)
    add_markers(mapdir, mapdata, armies, scale=scale)
    return QPixmap(mapdata.image)


def create_largest_preview(
        screen: QScreen | None,
        mapdir: str,
        armies: dict | None = None,
) -> QPixmap:
    return create_large_preview(mapdir, armies=armies, scale=largest_preview_scale(screen))


def largest_preview_scale(screen: QScreen | None) -> int:
    if screen is None:
        return 2
    size = screen.availableSize()
    return min(size.height() // 256, 4)
