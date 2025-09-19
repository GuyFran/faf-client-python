import os


def get_scmap_file(folder: str) -> str | None:
    for entry in os.scandir(folder):
        if entry.name.lower().endswith(".scmap"):
            return entry.path
    return None


def get_save_file(folder: str) -> str | None:
    """ Return the save.lua file """
    for entry in os.scandir(folder):
        if entry.name.lower().endswith("_save.lua"):
            return entry.path
    return None
