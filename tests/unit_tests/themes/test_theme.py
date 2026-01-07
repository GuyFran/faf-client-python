from semantic_version import Version

from src.util import Theme

THEME_FILE_FUNS = [
    "pixmap",
    "loadUi",
    "loadUiType",
    "readlines",
    "readstylesheet",
    "themeurl",
    "readfile",
    "sound",
]


def test_theme_with_empty_dir_keeps_filename(tmpdir):
    vfile = tmpdir.join("file")
    vfile.write("content")
    theme = Theme(None, "")
    assert theme.readfile(str(tmpdir.join("file"))) == "content"


def test_theme_with_dir_prepends_dir(tmpdir):
    themedir = tmpdir.mkdir("theme")
    vfile = themedir.join("file")
    vfile.write("content")
    theme = Theme(str(themedir), "")
    assert theme.readfile("file") == "content"


def test_missing_files_return_none(tmpdir):
    themedir = tmpdir.mkdir("theme")

    theme = Theme(str(themedir), "")
    for fun in THEME_FILE_FUNS:
        assert getattr(theme, fun)("file") is None

    theme = Theme(None, "")
    for fun in THEME_FILE_FUNS:
        assert getattr(theme, fun)(str(themedir.join("file"))) is None


def test_missing_version_returns_none(tmpdir):
    themedir = tmpdir.mkdir("theme")
    theme = Theme(str(themedir), "")
    assert theme.version() is None


def test_empty_dir_theme_version_returns_none(tmpdir):
    tmpdir.mkdir("theme")
    theme = Theme(None, "")
    assert theme.version() is None


def test_malformed_version_returns_none(tmpdir):
    themedir = tmpdir.mkdir("theme")
    themedir.join("version").write("1.0blergh")
    theme = Theme(str(themedir), "")
    assert theme.version() is None


def test_version_correctly_read(tmpdir):
    themedir = tmpdir.mkdir("theme")
    themedir.join("version").write("0.12.4")
    theme = Theme(str(themedir), "")
    version = theme.version()
    assert isinstance(version, Version)
    assert str(theme.version()) == "0.12.4"


def test_pixmap_cache_caches(tmpdir, mocker):
    mocker.patch('PyQt6.QtGui.QPixmap', side_effect=[1, 2])
    themedir = tmpdir.mkdir("theme")
    themedir.join("file").write("content")
    themedir.join("second_file").write("content")
    theme = Theme(str(themedir), "")

    first = theme.pixmap("file")
    still_first = theme.pixmap("file")
    second = theme.pixmap("second_file")

    assert first is not None and second is not None
    assert first is still_first
    assert first is not second


def test_stylesheet(tmpdir):
    themedir = tmpdir.mkdir("theme")
    styledir = themedir.mkdir("client")
    styledir.join("client.css").write("content")
    theme = Theme(str(themedir), "cool_theme")
    assert theme.stylesheet == "content"


def test_finding_stylesheet_attributes(tmpdir):
    themedir = tmpdir.mkdir("theme")
    styledir = themedir.mkdir("client")
    sheet = """\
    QListWidget {
        color: blue;
        background: yellow;
    }
    QListWidget::item
    {
        font-weight: bold;
        color: #000000;
    }
    QListWidget#tourneyList
    {
        border-style:solid;
        border-width:1px;
        border-color:#353535;
        color:silver;
        padding:5px;
        background-color:#0F0F0F;
        border-top-right-radius : 5px;
        border-top-left-radius : 5px;
        border-bottom-left-radius : 5px;
        border-bottom-right-radius : 5px;
    }
    """
    styledir.join("client.css").write(sheet)
    theme = Theme(str(themedir), "cool_theme")
    assert theme.find_stylesheet_attribute("QListWidget", "background") == "yellow"
    assert theme.find_stylesheet_attribute("QListWidget", "color") == "blue"
    assert theme.find_stylesheet_attribute("QListWidget::item", "font-weight") == "bold"
    assert theme.find_stylesheet_attribute("QListWidget::item", "color") == "#000000"
    assert theme.find_stylesheet_attribute("QListWidget#tourneyList", "border-color") == "#353535"
    assert theme.find_stylesheet_attribute(
        "QListWidget#tourneyList",
        "border-bottom-left-radius",
    ) == "5px"


def test_finding_stylesheet_style(tmpdir):
    themedir = tmpdir.mkdir("theme")
    styledir = themedir.mkdir("client")
    sheet = """\
    QLabel[bordered="true"] {
        border-radius: 8px;
        background-color: #252525;
        color: #a0a0a0;
        padding: 2px;
    }
    """
    styledir.join("client.css").write(sheet)
    theme = Theme(str(themedir), "cool_theme")
    assert theme.find_stylesheet_style("QLabel[bordered=\"true\"]") == """\
        border-radius: 8px;
        background-color: #252525;
        color: #a0a0a0;
        padding: 2px;\n"""

# TODO - tests for specific results of functions
