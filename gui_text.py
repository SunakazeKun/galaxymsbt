from __future__ import annotations

import os
import sys

from adapter_smg2 import SuperMarioGalaxy2Adapter
from guihelpers import resolve_asset, PROGRAM_TITLE
from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

__all__ = ["GalaxyTextEditor"]


class GalaxyTextEditor(QDialog):
    def __init__(self, parent: QMainWindow, adapter_maker: type[SuperMarioGalaxy2Adapter]):
        super().__init__(parent)

        # --------------------------------------------------------------------------------------------------------------
        # Variable declarations

        self._adapter_maker_: type[SuperMarioGalaxy2Adapter] = None

        self.textMessageText: QPlainTextEdit = None
        self.buttonTagPageBreak: QToolButton = None
        self.buttonTagTextSize: QToolButton = None
        self.buttonTagTextColor: QToolButton = None
        self.buttonTagResetColor: QToolButton = None
        self.buttonTagNumberFont: QToolButton = None
        self.buttonTagYCenter: QToolButton = None
        self.buttonTagXCenter: QToolButton = None
        self.buttonTagRuby: QToolButton = None
        self.buttonTagPicture: QToolButton = None
        self.buttonTagSound: QToolButton = None
        self.buttonTagPlayer: QToolButton = None
        self.buttonTagRaceTime: QToolButton = None
        self.buttonTagDelay: QToolButton = None
        self.buttonTagFormatNumber: QToolButton = None
        self.buttonTagFormatString: QToolButton = None
        self.buttonBox: QDialogButtonBox = None

        # --------------------------------------------------------------------------------------------------------------

        self._ui_ = uic.loadUi(resolve_asset("assets/dialog_text.ui"), self)
        self.setWindowTitle(PROGRAM_TITLE)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._adapter_maker_ = adapter_maker

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonTagPageBreak.clicked.connect(self._insert_tag_page_break_)
        self.buttonTagTextSize.clicked.connect(self._insert_tag_text_size_)
        self.buttonTagTextColor.clicked.connect(self._insert_tag_text_color_)
        self.buttonTagResetColor.clicked.connect(self._insert_tag_reset_color_)
        self.buttonTagNumberFont.clicked.connect(self._insert_tag_number_font_)
        self.buttonTagYCenter.clicked.connect(self._insert_tag_y_center_)
        self.buttonTagXCenter.clicked.connect(self._insert_tag_x_center_)
        self.buttonTagRuby.clicked.connect(self._insert_tag_ruby_)
        self.buttonTagPicture.clicked.connect(self._insert_tag_picture_)
        self.buttonTagSound.clicked.connect(self._insert_tag_sound_)
        self.buttonTagPlayer.clicked.connect(self._insert_tag_player_)
        self.buttonTagRaceTime.clicked.connect(self._insert_tag_race_time_)
        self.buttonTagDelay.clicked.connect(self._insert_tag_delay_)
        self.buttonTagFormatNumber.clicked.connect(self._insert_tag_format_number_)
        self.buttonTagFormatString.clicked.connect(self._insert_tag_format_string_)

    def request(self, label: str, message: str) -> tuple[str, bool]:
        self.setWindowTitle(f"Editing {label}")
        self.textMessageText.setPlainText(message)
        self.exec()

        edited_text = self.textMessageText.toPlainText()
        valid = self.result() == QDialog.Accepted
        return edited_text, valid

    # ------------------------------------------------------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------------------------------------------------------
    def _insert_tag_page_break_(self):
        self.textMessageText.insertPlainText("[pagebreak]")

    def _insert_tag_text_size_(self):
        text_size, valid = QInputDialog.getItem(self, "Insert size change", "Select text size:",
                                                self._adapter_maker_.FONT_SIZES, editable=False,
                                                flags=self.windowFlags())

        if valid:
            full_tag = f"[size:{text_size}]"
            self.textMessageText.insertPlainText(full_tag)

    def _insert_tag_text_color_(self):
        text_color, valid = QInputDialog.getItem(self, "Insert color change", "Select text color:",
                                                 self._adapter_maker_.FONT_COLORS, editable=False,
                                                 flags=self.windowFlags())

        if valid:
            full_tag = f"[color:{text_color}]"
            self.textMessageText.insertPlainText(full_tag)

    def _insert_tag_number_font_(self):
        description = "Enter the text to be displayed with NumberFont.brfnt. Keep in mind that\n" \
                      "this font is specifically designed for displaying numbers, so the vast\n" \
                      "majority of characters may not be visible ingame."
        number_text, valid = QInputDialog.getText(self, "Insert number text", description, flags=self.windowFlags())

        if valid:
            full_tag = f"[numberfont:{number_text}]"
            self.textMessageText.insertPlainText(full_tag)

    def _insert_tag_reset_color_(self):
        self.textMessageText.insertPlainText("[defcolor]")

    def _insert_tag_y_center_(self):
        self.textMessageText.insertPlainText("[ycenter]")

    def _insert_tag_x_center_(self):
        self.textMessageText.insertPlainText("[xcenter]")

    def _insert_tag_ruby_(self):
        description = "Specify kanji and furigana texts for ruby. This tag will be rendered\n" \
                      "only if the console's language is set to Japanese."
        kanji, furigana, valid = InsertRubyDialog.specify(self, "Insert ruby", description)

        if valid:
            full_tag = f"[ruby:{kanji};{furigana}]"
            self.textMessageText.insertPlainText(full_tag)

    def _insert_tag_picture_(self):
        description = "Select the icon to be inserted into the text."
        picture_icon, valid = PictureIconDialog.select(self, "Insert icon", description, self._adapter_maker_)

        if valid:
            full_tag = f"[icon:{picture_icon}]"
            self.textMessageText.insertPlainText(full_tag)

    def _insert_tag_sound_(self):
        description = "Enter the sound's name to be played. A complete list of sounds can be\n" \
                      "found on the Luma's Workshop wiki. If the sound does not play, it may\n" \
                      "have to be added to the Galaxy's UseResource file."
        sound_name, valid = QInputDialog.getText(self, "Insert sound effect", description, text="SE_SV_TICOFAT_META",
                                                 flags=self.windowFlags())

        if valid:
            full_tag = f"[sound:{sound_name}]"
            self.textMessageText.insertPlainText(full_tag)

    def _insert_tag_player_(self):
        description = "Specify the player name preset. SMG2 only supports preset 0 by default,\n" \
                      "but more texts can be added by editing 'SystemMessage.arc/~/PlayerName.msbt'."
        preset_id, valid = QInputDialog.getInt(self, "Insert player name", description, 0, 0, 255,
                                               flags=self.windowFlags())

        if valid:
            full_tag = f"[player:{preset_id}]"
            self.textMessageText.insertPlainText(full_tag)

    def _insert_tag_race_time_(self):
        description = "Select the race whose time should be displayed."
        race_time, valid = QInputDialog.getItem(self, "Insert race time", description,
                                                self._adapter_maker_.RACE_TIMES, editable=False,
                                                flags=self.windowFlags())

        if valid:
            full_tag = f"[race:{race_time}]"
            self.textMessageText.insertPlainText(full_tag)

    def _insert_tag_delay_(self):
        description = "Specify by how many frames text printing should be delayed.\n" \
                      "60 frames correspond to one 1 second."
        delay, valid = QInputDialog.getInt(self, "Insert printing delay", description, 60, 0, 65535,
                                           flags=self.windowFlags())

        if valid:
            full_tag = f"[delay:{delay}]"
            self.textMessageText.insertPlainText(full_tag)

    def _insert_tag_format_number_(self):
        description = "Inserts a variable that can be replaced with a proper number during gameplay.\n" \
                      "\n" \
                      "There are only a few situations where this can be used properly. If the game doesn't\n" \
                      "replace this variable with a proper number, the default number will be used instead.\n" \
                      "The default number will ignore the specified format option, though."
        format_id, argument_idx, default_value, valid = IntVarDialog.select(self, "Insert number variable", description)

        if valid:
            full_tag = f"[intvar:{format_id};{argument_idx};{default_value}]"
            self.textMessageText.insertPlainText(full_tag)

    def _insert_tag_format_string_(self):
        description = "Inserts a variable that can be replaced with a proper text string during gameplay.\n" \
                      "\n" \
                      "There are only a few situations where this can be used properly. If the game doesn't\n" \
                      "replace this variable with a proper string, the text at the given default address will\n" \
                      "be used. This feature is highly experimental and will most likely crash your game if\n" \
                      "used wrongly. Therefore, just leave the default pointer at 0.\n" \
                      "\n" \
                      "Tag ID is unused by the game, but it can be specified."
        tag_id, argument_idx, default_pointer, valid = StringVarDialog.select(self, "Insert text variable", description)

        if valid:
            full_tag = f"[stringvar:{tag_id};{argument_idx};0x{default_pointer:08X}]"
            self.textMessageText.insertPlainText(full_tag)


class InsertRubyDialog(QDialog):
    def __init__(self, parent: QWidget):
        super().__init__(parent)

        # --------------------------------------------------------------------------------------------------------------
        # Variable declarations

        self.labelDescription: QLabel = None
        self.lineKanji: QLineEdit = None
        self.lineFurigana: QLineEdit = None
        self.buttonBox: QDialogButtonBox = None

        # --------------------------------------------------------------------------------------------------------------

        self._ui_ = uic.loadUi(resolve_asset("assets/dialog_ruby.ui"), self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    @staticmethod
    def specify(parent: QWidget, title: str, description: str) -> tuple[str, str, bool]:
        dialog = InsertRubyDialog(parent)
        dialog.setWindowTitle(title)
        dialog.labelDescription.setText(description)
        dialog.exec()

        kanji = dialog.lineKanji.text()
        furigana = dialog.lineFurigana.text()
        valid = dialog.result() == QDialog.Accepted
        return kanji, furigana, valid


class PictureIconDialog(QDialog):
    def __init__(self, parent: QWidget, adapter_maker: type[SuperMarioGalaxy2Adapter]):
        super(PictureIconDialog, self).__init__(parent)

        # --------------------------------------------------------------------------------------------------------------
        # Variable declarations

        self.comboIcons: QComboBox = None
        self.labelDescription: QLabel = None
        self.buttonBox: QDialogButtonBox = None

        # --------------------------------------------------------------------------------------------------------------

        self._ui_ = uic.loadUi(resolve_asset("assets/dialog_picture.ui"), self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        for key in sorted(adapter_maker.PICTURE_NAMES):
            icon_path = f"icons/{key}.png"
            icon = None

            if os.path.isfile(icon_path):
                try:
                    icon = QIcon(icon_path)
                except Exception:
                    print(f"Couldn't load picture icon {icon_path}", file=sys.stderr)

            if icon is None:
                self.comboIcons.addItem(key)
            else:
                self.comboIcons.addItem(icon, key)

    @staticmethod
    def select(parent: QWidget, title: str, description: str, adapter_maker: type[SuperMarioGalaxy2Adapter])\
            -> tuple[str, bool]:
        dialog = PictureIconDialog(parent, adapter_maker)
        dialog.setWindowTitle(title)
        dialog.labelDescription.setText(description)
        dialog.exec()

        picture = dialog.comboIcons.currentText()
        valid = dialog.result() == QDialog.Accepted
        return picture, valid


class IntVarDialog(QDialog):
    def __init__(self, parent: QWidget):
        super(IntVarDialog, self).__init__(parent)

        # --------------------------------------------------------------------------------------------------------------
        # Variable declarations

        self.comboFormat: QComboBox = None
        self.spinArgumentIdx: QSpinBox = None
        self.spinDefaultValue: QSpinBox = None
        self.labelDescription: QLabel = None
        self.buttonBox: QDialogButtonBox = None

        # --------------------------------------------------------------------------------------------------------------

        self._ui_ = uic.loadUi(resolve_asset("assets/dialog_intvar.ui"), self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    @staticmethod
    def select(parent: QWidget, title: str, description: str)\
            -> tuple[int, int, int, bool]:
        dialog = IntVarDialog(parent)
        dialog.setWindowTitle(title)
        dialog.labelDescription.setText(description)
        dialog.exec()

        format_id = dialog.comboFormat.currentIndex()
        argument_idx = dialog.spinArgumentIdx.value()
        default_value = dialog.spinDefaultValue.value()
        valid = dialog.result() == QDialog.Accepted
        return format_id, argument_idx, default_value, valid


class StringVarDialog(QDialog):
    def __init__(self, parent: QWidget):
        super(StringVarDialog, self).__init__(parent)

        # --------------------------------------------------------------------------------------------------------------
        # Variable declarations

        self.spinTagID: QSpinBox = None
        self.spinArgumentIdx: QSpinBox = None
        self.lineDefaultPointer: QLineEdit = None
        self.labelDescription: QLabel = None
        self.buttonBox: QDialogButtonBox = None

        # --------------------------------------------------------------------------------------------------------------

        self._ui_ = uic.loadUi(resolve_asset("assets/dialog_stringvar.ui"), self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    @staticmethod
    def select(parent: QWidget, title: str, description: str)\
            -> tuple[int, int, int, bool]:
        dialog = StringVarDialog(parent)
        dialog.setWindowTitle(title)
        dialog.labelDescription.setText(description)
        dialog.exec()

        tag_id = dialog.spinTagID.value()
        argument_idx = dialog.spinArgumentIdx.value()
        default_pointer_string = dialog.lineDefaultPointer.text()
        valid = dialog.result() == QDialog.Accepted

        try:
            default_pointer_string = default_pointer_string.strip()
            default_pointer = int(default_pointer_string, 0)

            if default_pointer < 0 or 0xFFFFFFFF < default_pointer:
                default_pointer = 0
        except Exception:
            default_pointer = 0

        return tag_id, argument_idx, default_pointer, valid
