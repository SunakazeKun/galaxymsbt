import os
import sys
from PyQt5.QtCore import QSettings, QThread

__all__ = ["SettingsHolder", "WorkerThread", "resolve_asset", "PROGRAM_VERSION", "PROGRAM_TITLE"]

PROGRAM_VERSION = "v0.1.0"
PROGRAM_TITLE = f"galaxymsbt -- Super Mario Galaxy 2 MSBT Editor -- {PROGRAM_VERSION}"


def resolve_asset(relative_path: str):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# ----------------------------------------------------------------------------------------------------------------------
# Application settings
# ----------------------------------------------------------------------------------------------------------------------
class SettingsHolder:
    _settings_ = QSettings("galaxymsbt.ini", QSettings.IniFormat)

    @classmethod
    def get_last_arc_path(cls) -> str:
        return cls._settings_.value("last_arc_path", defaultValue="", type=str)

    @classmethod
    def set_last_arc_path(cls, last_arc_path: str):
        cls._settings_.setValue("last_arc_path", last_arc_path)

    @classmethod
    def is_compress_arc(cls) -> bool:
        return cls._settings_.value("compress_arc", defaultValue=False, type=bool)

    @classmethod
    def set_compress_arc(cls, compress_arc: bool):
        cls._settings_.setValue("compress_arc", compress_arc)


# ----------------------------------------------------------------------------------------------------------------------
# Basic service thread that may catch an exception
# ----------------------------------------------------------------------------------------------------------------------
class WorkerThread(QThread):
    _exception_: Exception = None

    def __init__(self, parent):
        super().__init__(parent)

    @property
    def has_exception(self) -> bool:
        return self._exception_ is not None

    @property
    def exception(self) -> Exception:
        return self._exception_
