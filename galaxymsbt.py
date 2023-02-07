import sys
import traceback

from gui_main import GalaxyMsbtEditor
from guihelpers import resolve_asset

import qdarkstyle
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication


if __name__ == "__main__":
    app = QApplication([])
    app.setWindowIcon(QIcon(resolve_asset("assets/icon.ico")))
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    # Setup exception hook
    sys._excepthook = sys.excepthook

    def exception_hook(exctype, value, trace):
        formatted = "".join(traceback.format_exception(exctype, value, trace))
        print(formatted, file=sys.stderr)
        sys.exit(1)

    sys.excepthook = exception_hook

    editor = GalaxyMsbtEditor()
    editor.setVisible(True)
    sys.exit(app.exec_())
