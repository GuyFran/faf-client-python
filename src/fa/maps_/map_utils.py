import os


def get_scmap_file(folder: str) -> str | None:
    for infile in os.listdir(folder):
        if infile.lower().endswith(".scmap"):
            return os.path.join(folder, infile)
    return None


def get_save_file(folder: str) -> str | None:
    """ Return the save.lua file """
    for infile in os.listdir(folder):
        if infile.lower().endswith("_save.lua"):
            return os.path.join(folder, infile)
    return None
