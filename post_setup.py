import pathlib
import shutil
import sys


def remove_some_redundant_qt_files() -> None:
    current_dir = pathlib.Path(__file__).parent
    app_dir = current_dir / "build" / "faf_python_client"
    app_qt6 = app_dir / "lib" / "PyQt6" / "Qt6"

    try:
        translations = app_qt6 / "translations"
        print(f"Removing '{translations}'...")
        shutil.rmtree(translations)
    except FileNotFoundError:
        pass

    if sys.platform == "win32":
        return

    # cx_Freeze copies these into lib directory itself
    # and into every plugin directory for some reason
    libfiles = [file.name for file in (app_qt6 / "lib").iterdir()]

    # not all of them, but the most obvious and largest ones
    redundant_plugins_files = [
        "libffmpegmediaplugin.so",
        "libQt6Pdf.so.6",
        "libQt6Qml.so.6",
        "libQt6QmlModels.so.6",
        "libQt6Quick.so.6",
    ]

    plugins_dir = app_qt6 / "plugins"
    for plugin in plugins_dir.iterdir():
        for file in plugin.iterdir():
            if file.name in libfiles + redundant_plugins_files:
                print(f"Removing {file}...")
                file.unlink()


def main() -> None:
    remove_some_redundant_qt_files()


if __name__ == "__main__":
    raise SystemExit(main())
