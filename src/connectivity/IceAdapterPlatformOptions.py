import sys
from typing import NamedTuple
from typing import Protocol


class IceAdapterPlatformOptions(Protocol):
    def name(self) -> str: ...
    def extension(self) -> str: ...


class GoIceAdapterPlatformOptions(NamedTuple):
    windows: str = "windows-amd64"
    linux: str = "linux-amd64"

    def name(self) -> str:
        if sys.platform == "win32":
            return self.windows
        return self.linux

    def extension(self) -> str:
        return ".exe" if sys.platform == "win32" else ""


class JavaIceAdapterPlatformOptions(NamedTuple):
    windows: str = "win"
    linux: str = "linux"

    def name(self) -> str:
        if sys.platform == "win32":
            return self.windows
        return self.linux

    def extension(self) -> str:
        return ".jar"
