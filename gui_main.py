from __future__ import annotations

import gc

from pyjkernel import JKRArchive, JKRCompression
from pymsb import LMSMessage, LMSEntryNode, LMSException
from msbtaccess import LMSAccessor
from gui_text import GalaxyTextEditor
from guihelpers import SettingsHolder, WorkerThread, resolve_asset, PROGRAM_TITLE
from adapter_smg2 import SuperMarioGalaxy2Adapter
from adapter_config import initialize_custom_smg2_adapter_maker

import pyjkernel

from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

__all__ = ["GalaxyMsbtEditor"]

CONFIG_PATH = "adapter_config.json"


class GalaxyMsbtEditor(QMainWindow):
    def __init__(self):
        super().__init__(None)

        # --------------------------------------------------------------------------------------------------------------
        # Variable declarations

        # Data storage
        self.current_arc_path: str = ""                 # Path to the current archive file
        self.archive: JKRArchive = None                 # Current RARC archive
        self.lms_accessors: list[LMSAccessor] = None    # List of text files in archive
        self.current_accessor: LMSAccessor = None       # Currently edited text file
        self.current_message: LMSMessage = None         # Currently edited LMS message
        self.current_flowchart: LMSEntryNode = None     # Currently edited LMS flowchart

        # Data helpers
        self.adapter: type[SuperMarioGalaxy2Adapter] = None     # Active adapter for parsing text files
        self.rarc_reader_thread: RarcReaderThread = None        # Reads RARC file and parses text files
        self.rarc_writer_thread: RarcWriterThread = None        # Packs text files and writes RARC file
        self.model_lms_accessor_names: QStringListModel = None  # Model reflecting text file names
        self.model_message_names: QStringListModel = None       # Model reflecting message names
        self.model_flowchart_names: QStringListModel = None     # Model reflecting flowchart names
        self.unsaved_changes: bool = False                      # True if there are some edits

        # Helper forms
        self._gui_text_editor_: GalaxyTextEditor = None

        # UI elements (initialized by UI loader)
        self.statusBar: QStatusBar = None
        self.actionNew: QAction = None
        self.actionOpen: QAction = None
        self.actionSave: QAction = None
        self.actionOptionCompression: QAction = None
        self.actionAbout: QAction = None

        self.lineArchivePath: QLineEdit = None
        self.lineArchiveRoot: QLineEdit = None
        self.buttonChangeRoot: QPushButton = None

        self.buttonLmsAccessorNew: QPushButton = None
        self.buttonLmsAccessorDelete: QPushButton = None
        self.listLmsAccessors: QListView = None

        self.buttonMessagesAdd: QPushButton = None
        self.buttonMessagesRemove: QPushButton = None
        self.buttonMessagesDuplicate: QPushButton = None
        self.buttonMessagesSort: QPushButton = None
        self.listMessageEntries: QListView = None

        self.buttonFlowchartsAdd: QPushButton = None
        self.buttonFlowchartsRemove: QPushButton = None
        self.buttonFlowchartsDuplicate: QPushButton = None
        self.buttonFlowchartsSort: QPushButton = None
        self.listFlowcharts: QListView = None

        self.buttonChangeLabel: QPushButton = None
        self.buttonShowEditor: QPushButton = None
        self.lineLabel: QLineEdit = None
        self.comboTalkType: QComboBox = None
        self.comboBalloonType: QComboBox = None
        self.comboSoundName: QComboBox = None
        self.comboCameraType: QComboBox = None
        self.spinCameraId: QSpinBox = None
        self.spinMsgLinkId: QSpinBox = None
        self.spinUnk7: QSpinBox = None
        self.textMessageText: QPlainTextEdit = None
        self.textComment: QPlainTextEdit = None

        # --------------------------------------------------------------------------------------------------------------

        self._ui_ = uic.loadUi(resolve_asset("assets/editor.ui"), self)
        self.setWindowTitle(PROGRAM_TITLE)

        self.model_lms_accessor_names = QStringListModel()
        self.model_message_names = QStringListModel()
        self.model_flowchart_names = QStringListModel()
        self.listLmsAccessors.setModel(self.model_lms_accessor_names)
        self.listMessageEntries.setModel(self.model_message_names)
        self.listFlowcharts.setModel(self.model_flowchart_names)

        self.actionOptionCompression.blockSignals(True)
        self.actionOptionCompression.setChecked(SettingsHolder.is_compress_arc())
        self.actionOptionCompression.blockSignals(False)

        self.set_lms_file_components_enabled(False)
        self.set_archive_components_enabled(False)
        self.set_message_components_enabled(False)
        self.set_flowcharts_components_enabled(False)
        self.set_message_entry_components_enabled(False)

        self.reset_message_entry_values()

        self.init_adapter()
        self.init_subforms()
        self.init_events()

    def init_adapter(self):
        try:
            self.adapter = initialize_custom_smg2_adapter_maker()
        except Exception as ex:
            self.adapter = SuperMarioGalaxy2Adapter
            self.show_error_dialog(f"An error occurred while trying to load adapter config data:\n\n{repr(ex)}")

        for talk_type in self.adapter.TALK_TYPES:
            self.comboTalkType.addItem(talk_type)

        for talk_type in self.adapter.BALLOON_TYPES:
            self.comboBalloonType.addItem(talk_type)

        for sound_name in self.adapter.MESSAGE_SOUNDS:
            self.comboSoundName.addItem(sound_name)

        for talk_type in self.adapter.CAMERA_TYPES:
            self.comboCameraType.addItem(talk_type)

    def init_subforms(self):
        self._gui_text_editor_ = GalaxyTextEditor(self, self.adapter)

    def init_events(self):
        # File menu events
        self.actionNew.triggered.connect(self.new_arc)
        self.actionOpen.triggered.connect(self.open_arc)
        self.actionSave.triggered.connect(lambda: self.save_arc(False))
        self.actionSaveAs.triggered.connect(lambda: self.save_arc(True))

        # Options menu events
        self.actionOptionCompression.triggered.connect(SettingsHolder.set_compress_arc)

        # About menu events
        self.actionAbout.triggered.connect(self.show_about)

        # Archive events
        self.buttonChangeRoot.clicked.connect(self.change_archive_root)

        # LMS accessor events
        self.buttonLmsAccessorNew.clicked.connect(self.new_accessor)
        self.buttonLmsAccessorDelete.clicked.connect(self.delete_accessor)
        self.listLmsAccessors.selectionModel().selectionChanged.connect(self.on_accessor_selected)

        # Message events
        self.buttonMessagesAdd.clicked.connect(self.create_message)
        self.buttonMessagesRemove.clicked.connect(self.remove_message)
        self.buttonMessagesDuplicate.clicked.connect(self.duplicate_message)
        self.buttonMessagesSort.clicked.connect(self.sort_messages)
        self.listMessageEntries.selectionModel().selectionChanged.connect(self.on_message_selected)

        # Flowchart events
        self.buttonFlowchartsAdd.clicked.connect(self.create_flowchart)
        self.buttonFlowchartsRemove.clicked.connect(self.remove_flowchart)
        self.buttonFlowchartsDuplicate.clicked.connect(self.duplicate_flowchart)
        self.buttonFlowchartsSort.clicked.connect(self.sort_flowcharts)
        self.listFlowcharts.selectionModel().selectionChanged.connect(self.on_flowchart_selected)

        # Message component events
        self.buttonChangeLabel.clicked.connect(self.set_message_entry_label)
        self.buttonShowEditor.clicked.connect(self.open_message_entry_text_editor)
        self.comboTalkType.currentIndexChanged.connect(self.set_message_entry_talk_type)
        self.comboBalloonType.currentIndexChanged.connect(self.set_message_entry_balloon_type)
        self.comboSoundName.currentIndexChanged.connect(self.set_message_entry_sound_id)
        self.comboCameraType.currentIndexChanged.connect(self.set_message_entry_camera_type)
        self.spinCameraId.valueChanged.connect(self.set_message_entry_camera_id)
        self.spinMsgLinkId.valueChanged.connect(self.set_message_entry_msg_link_id)
        self.spinUnk7.valueChanged.connect(self.set_message_entry_unk_7)
        self.textMessageText.textChanged.connect(self.set_message_entry_text)
        self.textComment.textChanged.connect(self.set_message_entry_comment)

    def show_about(self):
        description = f"{PROGRAM_TITLE} by Aurum\n\n" \
                      f"- Special thanks to SY24 who created the UI icons.\n" \
                      f"- Text icons ripped from the original game."
        QMessageBox.information(self, "About", description)

    def show_wip(self):
        QMessageBox.information(self, PROGRAM_TITLE, "This action is not supported yet!")

    # ------------------------------------------------------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------------------------------------------------------
    def reset_editor(self):
        self.unsaved_changes = False

        self.set_archive_components_enabled(False)
        self.set_lms_file_components_enabled(False)
        self.set_message_components_enabled(False)
        self.set_flowcharts_components_enabled(False)
        self.set_message_entry_components_enabled(False)

        self.lineArchivePath.setText("")
        self.lineArchiveRoot.setText("")

        self.reset_lms_accessors_model()
        self.reset_messages_model()
        self.reset_flowcharts_model()
        self.reset_message_entry_values()

    def set_file_menu_components_enabled(self, state: bool):
        self.actionNew.blockSignals(not state)
        self.actionOpen.blockSignals(not state)
        self.actionSave.blockSignals(not state)

    def set_archive_components_enabled(self, state: bool):
        # pyjkernel does not support renaming yet...
        self.buttonChangeRoot.blockSignals(True)

        self.lineArchivePath.setEnabled(state)
        self.lineArchiveRoot.setEnabled(state)
        self.buttonChangeRoot.setEnabled(False)  # This should be adjusted in the future!

    def set_lms_file_components_enabled(self, state: bool):
        self.buttonLmsAccessorNew.blockSignals(not state)
        self.buttonLmsAccessorDelete.blockSignals(not state)
        self.listLmsAccessors.selectionModel().blockSignals(not state)

        self.buttonLmsAccessorNew.setEnabled(state)
        self.buttonLmsAccessorDelete.setEnabled(state)
        self.listLmsAccessors.setEnabled(state)

    def set_message_components_enabled(self, state: bool):
        self.buttonMessagesAdd.blockSignals(not state)
        self.buttonMessagesRemove.blockSignals(not state)
        self.buttonMessagesDuplicate.blockSignals(not state)
        self.buttonMessagesSort.blockSignals(not state)
        self.listMessageEntries.selectionModel().blockSignals(not state)

        self.buttonMessagesAdd.setEnabled(state)
        self.buttonMessagesRemove.setEnabled(state)
        self.buttonMessagesDuplicate.setEnabled(state)
        self.buttonMessagesSort.setEnabled(state)
        self.listMessageEntries.setEnabled(state)

    def set_flowcharts_components_enabled(self, state: bool):
        self.buttonFlowchartsAdd.blockSignals(not state)
        self.buttonFlowchartsRemove.blockSignals(not state)
        self.buttonFlowchartsDuplicate.blockSignals(not state)
        self.buttonFlowchartsSort.blockSignals(not state)
        self.listFlowcharts.selectionModel().blockSignals(not state)

        self.buttonFlowchartsAdd.setEnabled(state)
        self.buttonFlowchartsRemove.setEnabled(state)
        self.buttonFlowchartsDuplicate.setEnabled(state)
        self.buttonFlowchartsSort.setEnabled(state)
        self.listFlowcharts.setEnabled(state)

    def set_message_entry_components_enabled(self, state: bool):
        self.buttonChangeLabel.blockSignals(not state)
        self.buttonShowEditor.blockSignals(not state)
        self.comboSoundName.blockSignals(not state)
        self.comboTalkType.blockSignals(not state)
        self.comboBalloonType.blockSignals(not state)
        self.comboCameraType.blockSignals(not state)
        self.spinCameraId.blockSignals(not state)
        self.spinMsgLinkId.blockSignals(not state)
        self.spinUnk7.blockSignals(not state)
        self.textMessageText.blockSignals(not state)
        self.textComment.blockSignals(not state)

        self.buttonChangeLabel.setEnabled(state)
        self.buttonShowEditor.setEnabled(state)
        self.lineLabel.setEnabled(state)
        self.comboSoundName.setEnabled(state)
        self.comboTalkType.setEnabled(state)
        self.comboBalloonType.setEnabled(state)
        self.comboCameraType.setEnabled(state)
        self.spinCameraId.setEnabled(state)
        self.spinMsgLinkId.setEnabled(state)
        self.spinUnk7.setEnabled(state)
        self.textMessageText.setEnabled(state)
        self.textComment.setEnabled(state)

    def populate_lms_files_model(self):
        start_row = self.model_lms_accessor_names.rowCount()
        self.model_lms_accessor_names.insertRows(start_row, len(self.lms_accessors))

        for lms_accessor in self.lms_accessors:
            self.model_lms_accessor_names.setData(self.model_lms_accessor_names.index(start_row), lms_accessor.name)
            start_row += 1

        self.model_lms_accessor_names.sort(0)

    def reset_lms_accessors_model(self):
        self.model_lms_accessor_names.removeRows(0, self.model_lms_accessor_names.rowCount())

    def populate_messages_model(self):
        start_row = self.model_message_names.rowCount()
        self.model_message_names.insertRows(start_row, len(self.current_accessor.messages))

        for message in self.current_accessor.messages:
            self.model_message_names.setData(self.model_message_names.index(start_row), message.label)
            start_row += 1

    def reset_messages_model(self):
        self.model_message_names.removeRows(0, self.model_message_names.rowCount())

    def populate_flowcharts_model(self):
        start_row = self.model_flowchart_names.rowCount()
        self.model_flowchart_names.insertRows(start_row, len(self.current_accessor.flowcharts))

        for flowchart in self.current_accessor.flowcharts:
            self.model_flowchart_names.setData(self.model_flowchart_names.index(start_row), flowchart.label)
            start_row += 1

    def reset_flowcharts_model(self):
        self.model_flowchart_names.removeRows(0, self.model_flowchart_names.rowCount())

    def reset_message_entry_values(self):
        self.lineLabel.setText("null")
        self.comboSoundName.setCurrentIndex(1)
        self.comboTalkType.setCurrentIndex(0)
        self.comboBalloonType.setCurrentIndex(0)
        self.comboCameraType.setCurrentIndex(0)
        self.spinCameraId.setValue(0)
        self.spinMsgLinkId.setValue(255)
        self.spinUnk7.setValue(255)
        self.textMessageText.setPlainText("")
        self.textComment.setPlainText("")

    # ------------------------------------------------------------------------------------------------------------------
    # ARC creation, opening & saving
    # ------------------------------------------------------------------------------------------------------------------
    def new_arc(self):
        # Ignore changes?
        if not self.try_prompt_ignore_unsaved_changes():
            return

        # Specify archive root name, abort if not valid
        root_name, valid = self.prompt_root_name()

        if not valid:
            return

        if root_name == "":
            self.show_error_dialog("No valid name specified!")
            return

        # (Re-)initialize editor and create archive
        self.reset_editor()

        self.current_arc_path = ""

        self.archive = pyjkernel.create_new_archive(root_name, sync_file_ids=True)
        self.lms_accessors = []
        self.current_accessor = None
        self.current_message = None

        self.lineArchivePath.setText(self.current_arc_path)
        self.lineArchiveRoot.setText(self.archive.root_name)
        self.set_archive_components_enabled(True)
        self.set_lms_file_components_enabled(True)

    def open_arc(self):
        if not self.try_prompt_ignore_unsaved_changes():
            return

        # Try select ARC file
        arc_file_path, valid = self.select_open_arc_file()

        if not valid:
            return

        self.current_arc_path = arc_file_path
        self.lineArchivePath.setText(self.current_arc_path)
        SettingsHolder.set_last_arc_path(arc_file_path)

        # Reset editor & storage
        self.reset_editor()
        self.lineArchivePath.setText(self.current_arc_path)

        self.archive = None
        self.lms_accessors = None
        self.current_accessor = None
        self.current_message = None

        # Read RARC file
        self.set_file_menu_components_enabled(False)
        self.rarc_reader_thread = RarcReaderThread(self, self.current_arc_path, self.adapter)
        self.rarc_reader_thread.finished.connect(self.on_arc_opened)
        self.rarc_reader_thread.start()

    def on_arc_opened(self):
        if not self.rarc_reader_thread.has_exception:
            self.archive = self.rarc_reader_thread.archive
            self.lms_accessors = self.rarc_reader_thread.lms_accessors

            self.populate_lms_files_model()
            self.lineArchiveRoot.setText(self.archive.root_name)
            self.set_archive_components_enabled(True)
            self.set_lms_file_components_enabled(True)
        else:
            self.set_archive_components_enabled(False)
            self.set_lms_file_components_enabled(False)

            exception = self.rarc_reader_thread.exception
            description = f"Archive couldn't be loaded because an error occurred:\n\n{repr(exception)}"
            self.show_error_dialog(description)

        del self.rarc_reader_thread
        self.set_file_menu_components_enabled(True)

    def save_arc(self, force_new_path: bool):
        if self.archive is None or self.lms_accessors is None:
            return

        # Select file to save to if no path has been specified yet
        if force_new_path or self.current_arc_path == "":
            arc_file_path, valid = self.select_save_arc_file()

            if not valid:
                return

            self.current_arc_path = arc_file_path
            self.lineArchivePath.setText(self.current_arc_path)
            SettingsHolder.set_last_arc_path(arc_file_path)

        self.set_file_menu_components_enabled(False)
        self.rarc_writer_thread\
            = RarcWriterThread(self, self.current_arc_path, self.archive, self.lms_accessors)
        self.rarc_writer_thread.finished.connect(self.on_arc_saved)
        self.rarc_writer_thread.start()

    def on_arc_saved(self):
        if not self.rarc_writer_thread.has_exception:
            self.unsaved_changes = False
            self.show_info_dialog("Successfully saved all text files and the archive!")
        else:
            exception = self.rarc_writer_thread.exception
            description = f"Archive couldn't be saved because an error occurred:\n\n{repr(exception)}"
            self.show_error_dialog(description)

        del self.rarc_writer_thread
        self.set_file_menu_components_enabled(True)

    def change_archive_root(self):
        # pyjkernel does not support this yet...
        pass

    # ------------------------------------------------------------------------------------------------------------------
    # Text file creation & deletion
    # ------------------------------------------------------------------------------------------------------------------
    def new_accessor(self):
        # Try enter a name
        accessor_name, valid = self.prompt_lms_name()
        accessor_name = accessor_name.removesuffix(".msbt").removesuffix(".msbf")

        if not valid:
            return

        if accessor_name == "":
            self.show_error_dialog(f"No valid name specified!")
            return

        # Check if accessor with same name already exists
        for lms_accessor in self.lms_accessors:
            if accessor_name.lower() == lms_accessor.name.lower():
                self.show_error_dialog("A file with the same name already exists!")
                return

        # Create accessor
        lms_accessor = LMSAccessor(accessor_name, self.archive, self.adapter)
        self.lms_accessors.append(lms_accessor)

        self.unsaved_changes = True

        # Insert accessor name in list model
        start_row = self.model_lms_accessor_names.rowCount()
        self.model_lms_accessor_names.insertRow(start_row)
        self.model_lms_accessor_names.setData(self.model_lms_accessor_names.index(start_row), lms_accessor.name, 0)
        self.model_lms_accessor_names.sort(0)

    def delete_accessor(self):
        selected_indices = self.listLmsAccessors.selectionModel().selectedIndexes()

        if len(selected_indices) < 1:
            return
        if not self.show_yes_no_prompt("Do you really want to remove the selected file(s)?"):
            return

        remove_file_names = []
        remove_accessors = set()

        # Remove file names from model
        for selected_index in reversed(selected_indices):
            remove_file_names.append(self.model_lms_accessor_names.data(selected_index, 0))
            self.model_lms_accessor_names.removeRow(selected_index.row())

        # Remove accessors and files inside RARC
        if len(remove_file_names) > 0:
            for lms_accessor in self.lms_accessors:
                if lms_accessor.name in remove_file_names:
                    remove_accessors.add(lms_accessor)
                    lms_accessor.delete()

                    # If currently selected accessor is removed, respective components need to be cleared
                    if self.current_accessor == lms_accessor:
                        self.set_message_components_enabled(False)
                        self.set_flowcharts_components_enabled(False)
                        self.set_message_entry_components_enabled(False)
                        self.reset_messages_model()
                        self.reset_flowcharts_model()
                        self.reset_message_entry_values()
                        self.current_accessor = None
                        self.current_message = None

            for remove_accessor in remove_accessors:
                self.lms_accessors.remove(remove_accessor)

            self.unsaved_changes = True

    # ------------------------------------------------------------------------------------------------------------------
    # Message creation, deletion, etc.
    # ------------------------------------------------------------------------------------------------------------------
    def create_message(self):
        # Try enter a label for the message
        message_label, valid = self.prompt_message_label()

        if not valid:
            return

        if message_label == "":
            self.show_error_dialog(f"No valid name specified!")
            return

        # Try to create new entry
        try:
            self.current_accessor.new_message(message_label)
        except LMSException:
            self.show_error_dialog(f"A message with the label {message_label} already exists!")
            return

        self.unsaved_changes = True

        # Insert message label in list model
        start_row = self.model_message_names.rowCount()
        self.model_message_names.insertRow(start_row)
        self.model_message_names.setData(self.model_message_names.index(start_row), message_label, 0)

    def remove_message(self):
        selected_indices = self.listMessageEntries.selectionModel().selectedIndexes()

        if len(selected_indices) == 0:
            return
        if not self.show_yes_no_prompt("Do you really want to remove the selected message(s)?"):
            return

        # Collect labels and indices to be removed
        remove_label_rows = {}

        for selected_index in reversed(selected_indices):
            label = self.model_message_names.data(selected_index, 0)
            remove_label_rows[label] = selected_index.row()

        # Remove messages
        failed_labels = []

        for label in remove_label_rows.keys():
            if self.current_accessor.delete_message(label):
                if self.current_message is not None and self.current_message.label == label:
                    self.set_message_entry_components_enabled(False)
                    self.reset_message_entry_values()
                    self.current_message = None

                self.unsaved_changes = True

            else:
                failed_labels.append(label)
                remove_label_rows[label] = -2  # Invalid row to prevent it from deletion

        # Remove labels from model
        were_blocked = self.model_message_names.signalsBlocked()
        self.model_message_names.blockSignals(True)

        for row in filter(lambda i: i >= 0, remove_label_rows.values()):
            self.model_message_names.removeRow(row)

        self.model_message_names.blockSignals(were_blocked)

        # Notify about failed labels
        if len(failed_labels) > 0:
            print_count = min([len(failed_labels), 5])
            error_msg = "The following messages weren't removed because they are referenced in flowcharts:\n\n"
            error_msg += "\n".join(failed_labels[:print_count])

            if print_count < len(failed_labels):
                unprinted_count = len(failed_labels) - print_count
                error_msg += f"\n... and {unprinted_count} more!"

            self.show_error_dialog(error_msg)

    def duplicate_message(self):
        self.show_wip()
        selected_indices = self.listMessageEntries.selectionModel().selectedIndexes()

        if len(selected_indices) < 1:
            return

        self.model_message_names.blockSignals(True)

        # Implement remaining logic, duh

        self.model_message_names.blockSignals(False)
        # self.unsaved_changes = True

    def sort_messages(self):
        self.current_accessor.sort_messages()
        self.model_message_names.blockSignals(True)

        # Repopulate model without sort function to retain exact natural order of elements
        self.listMessageEntries.selectionModel().clearSelection()
        self.reset_messages_model()
        self.model_message_names.blockSignals(False)
        self.populate_messages_model()
        self.unsaved_changes = True

    # ------------------------------------------------------------------------------------------------------------------
    # Flowchart creation, deletion, etc.
    # ------------------------------------------------------------------------------------------------------------------
    def create_flowchart(self):
        self.show_wip()

    def remove_flowchart(self):
        selected_indices = self.listFlowcharts.selectionModel().selectedIndexes()

        if len(selected_indices) == 0:
            return
        if not self.show_yes_no_prompt("Do you really want to remove the selected flowchart(s)?"):
            return

        # Collect labels and indices to be removed
        remove_label_rows = {}

        for selected_index in reversed(selected_indices):
            label = self.model_flowchart_names.data(selected_index, 0)
            remove_label_rows[label] = selected_index.row()

        # Remove flowcharts
        for label in remove_label_rows.keys():
            if self.current_accessor.delete_flowchart(label):
                if self.current_flowchart is not None and self.current_flowchart.label == label:
                    self.current_flowchart = None

                self.unsaved_changes = True

            else:
                remove_label_rows[label] = -2  # Invalid row to prevent it from deletion

        # Remove labels from model
        were_blocked = self.model_flowchart_names.signalsBlocked()
        self.model_flowchart_names.blockSignals(True)

        for row in filter(lambda i: i >= 0, remove_label_rows.values()):
            self.model_flowchart_names.removeRow(row)

        self.model_flowchart_names.blockSignals(were_blocked)

    def duplicate_flowchart(self):
        self.show_wip()

    def sort_flowcharts(self):
        self.current_accessor.sort_flowcharts()
        self.model_flowchart_names.blockSignals(True)

        # Repopulate model without sort function to retain exact natural order of elements
        self.listFlowcharts.selectionModel().clearSelection()
        self.reset_flowcharts_model()
        self.model_flowchart_names.blockSignals(False)
        self.populate_flowcharts_model()
        self.unsaved_changes = True

    # ------------------------------------------------------------------------------------------------------------------
    # List change events
    # ------------------------------------------------------------------------------------------------------------------
    def on_accessor_selected(self):
        selection = self.listLmsAccessors.selectionModel().selection()
        self.set_message_components_enabled(False)
        self.set_flowcharts_components_enabled(False)
        self.set_message_entry_components_enabled(False)
        self.reset_messages_model()
        self.reset_flowcharts_model()
        self.reset_message_entry_values()
        self.current_accessor = None
        self.current_message = None

        if len(selection.indexes()) != 1:
            return

        lms_name: str = self.model_lms_accessor_names.data(selection.indexes()[0], 0)

        for lms_accessor in self.lms_accessors:
            if lms_accessor.name == lms_name:
                self.current_accessor = lms_accessor
                break

        if self.current_accessor is not None:
            self.populate_messages_model()
            self.populate_flowcharts_model()
            self.set_message_components_enabled(True)
            self.set_flowcharts_components_enabled(True)

    def on_message_selected(self):
        selection = self.listMessageEntries.selectionModel().selection()
        self.set_message_entry_components_enabled(False)
        self.reset_message_entry_values()
        self.current_message = None

        if len(selection.indexes()) != 1:
            return

        label: str = self.model_message_names.data(selection.indexes()[0], 0)
        self.current_message = self.current_accessor.get_message(label)

        self.populate_from_current_message()
        self.set_message_entry_components_enabled(True)

    def on_flowchart_selected(self):
        selection = self.listMessageEntries.selectionModel().selection()
        self.current_flowchart = None

        if len(selection.indexes()) != 1:
            return

        label: str = self.model_flowchart_names.data(selection.indexes()[0], 0)
        self.current_flowchart = self.current_accessor.get_flowchart(label)

    # ------------------------------------------------------------------------------------------------------------------
    # Message entry events
    # ------------------------------------------------------------------------------------------------------------------
    def populate_from_current_message(self):
        self.lineLabel.setText(self.current_message.label)

        attributes = self.current_message.attributes
        talk_type = attributes["talk_type"]
        balloon_type = attributes["balloon_type"]
        sound_id = attributes["sound_id"]
        camera_type = attributes["camera_type"]

        if talk_type >= len(self.adapter.TALK_TYPES):
            talk_type = 0
            attributes["talk_type"] = 0
        if balloon_type >= len(self.adapter.BALLOON_TYPES):
            balloon_type = 0
            attributes["balloon_type"] = 0
        if sound_id >= len(self.adapter.MESSAGE_SOUNDS):
            sound_id = 1
            attributes["sound_id"] = 1
        if camera_type >= len(self.adapter.CAMERA_TYPES):
            camera_type = 0
            attributes["camera_type"] = 0

        self.comboTalkType.setCurrentIndex(talk_type)
        self.comboBalloonType.setCurrentIndex(balloon_type)
        self.comboSoundName.setCurrentIndex(sound_id)
        self.comboCameraType.setCurrentIndex(camera_type)
        self.spinCameraId.setValue(attributes["camera_id"])
        self.spinMsgLinkId.setValue(attributes["msg_link_id"])
        self.spinUnk7.setValue(attributes["unk7"])

        self.textMessageText.setPlainText(self.current_message.text)
        self.textComment.setPlainText(attributes["comment"])

    def set_message_entry_label(self):
        # Try enter a label for the message
        new_label, valid = self.prompt_message_label()
        old_label = self.current_message.label

        if not valid or new_label == old_label:
            return

        if new_label == "":
            self.show_error_dialog(f"No valid name specified!")
            return

        # Check if label is already used
        if not self.current_accessor.rename_message(old_label, new_label):
            self.show_error_dialog(f"A message with the label {new_label} already exists!")
            return

        # Update entry and model
        self.current_message.label = new_label
        self.unsaved_changes = True

        row = self.model_message_names.stringList().index(old_label)
        self.model_message_names.setData(self.model_message_names.index(row), new_label)
        self.lineLabel.setText(new_label)

    def open_message_entry_text_editor(self):
        result, valid = self._gui_text_editor_.request(self.current_message.label, self.current_message.text)

        if valid and result != self.current_message.text:
            self.current_message.text = result
            self.unsaved_changes = True

            self.textMessageText.blockSignals(True)
            self.textMessageText.setPlainText(self.current_message.text)
            self.textMessageText.blockSignals(False)

    def set_message_entry_talk_type(self, talk_type: int):
        self.current_message.attributes["talk_type"] = talk_type
        self.unsaved_changes = True

    def set_message_entry_balloon_type(self, balloon_type: int):
        self.current_message.attributes["balloon_type"] = balloon_type
        self.unsaved_changes = True

    def set_message_entry_sound_id(self, sound_id: int):
        self.current_message.attributes["sound_id"] = sound_id
        self.unsaved_changes = True

    def set_message_entry_camera_type(self, camera_type: int):
        self.current_message.attributes["camera_type"] = camera_type
        self.unsaved_changes = True

    def set_message_entry_camera_id(self, camera_id: int):
        self.current_message.attributes["camera_id"] = camera_id
        self.unsaved_changes = True

    def set_message_entry_msg_link_id(self, msg_link_id: int):
        self.current_message.attributes["msg_link_id"] = msg_link_id
        self.unsaved_changes = True

    def set_message_entry_unk_7(self, unk7: int):
        self.current_message.attributes["unk7"] = unk7
        self.unsaved_changes = True

    def set_message_entry_text(self):
        self.current_message.text = self.textMessageText.toPlainText()
        self.unsaved_changes = True

    def set_message_entry_comment(self):
        self.current_message.attributes["comment"] = self.textComment.toPlainText()
        self.unsaved_changes = True

    # ------------------------------------------------------------------------------------------------------------------
    # Dialogs & prompts
    # ------------------------------------------------------------------------------------------------------------------
    def show_info_dialog(self, info: str | Exception):
        if type(info) == Exception:
            QMessageBox.information(self, "Information", info.message if hasattr(info, "message") else repr(info))
        else:
            QMessageBox.information(self, "Information", info)

    def show_error_dialog(self, cause: str | Exception):
        if isinstance(cause, Exception):
            QMessageBox.critical(self, "Error", cause.message if hasattr(cause, "message") else repr(cause))
        else:
            QMessageBox.critical(self, "Error", cause)

    def show_yes_no_prompt(self, description: str) -> bool:
        result = QMessageBox.question(self, "Question", description, QMessageBox.Yes, QMessageBox.No)
        return result == QMessageBox.Yes

    def try_prompt_ignore_unsaved_changes(self) -> bool:
        if self.unsaved_changes:
            description = "There are unsaved changes. Are you sure you want to discard the changes?"
            return self.show_yes_no_prompt(description)
        return True

    # ------------------------------------------------------------------------------------------------------------------

    def prompt_root_name(self) -> tuple[str, bool]:
        root_name, valid = QInputDialog.getText(self, self.windowTitle(), "Specify archive root folder name:",
                                                flags=self.windowFlags())
        root_name = root_name.strip()
        return root_name, valid

    def prompt_lms_name(self) -> tuple[str, bool]:
        lms_name, valid = QInputDialog.getText(self, self.windowTitle(), "Specify text file name without extension:",
                                               flags=self.windowFlags())
        lms_name = lms_name.strip()
        return lms_name, valid

    def prompt_message_label(self) -> tuple[str, bool]:
        message_label, valid = QInputDialog.getText(self, self.windowTitle(), "Specify label (max. 255 characters):",
                                                    flags=self.windowFlags())
        message_label = message_label.strip()
        return message_label, valid and len(message_label) <= 255

    # ------------------------------------------------------------------------------------------------------------------

    def select_open_arc_file(self) -> tuple[str, bool]:
        filters = "ARC file (*.arc);;RARC file (*.rarc)"
        last_arc_path = SettingsHolder.get_last_arc_path()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open texts from ...", directory=last_arc_path, filter=filters)
        return (file_path, True) if len(file_path) != 0 else ("", False)

    def select_save_arc_file(self) -> tuple[str, bool]:
        filters = "ARC file (*.arc);;RARC file (*.rarc)"
        last_arc_path = SettingsHolder.get_last_arc_path()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save texts to ...", directory=last_arc_path, filter=filters)
        return (file_path, True) if len(file_path) != 0 else ("", False)


# ----------------------------------------------------------------------------------------------------------------------
# Service threads for reading & saving
# ----------------------------------------------------------------------------------------------------------------------
class RarcReaderThread(WorkerThread):
    def __init__(self, parent: QMainWindow, arc_path: str, adapter: type[SuperMarioGalaxy2Adapter]):
        super().__init__(parent)
        self.adapter: type[SuperMarioGalaxy2Adapter] = adapter
        self.arc_path: str = arc_path
        self.archive: JKRArchive | None = None
        self.lms_accessors: list[LMSAccessor] = []

    def run(self):
        try:
            self.archive = pyjkernel.from_archive_file(self.arc_path)

            for file in filter(lambda f: f.name.endswith(".msbt"), self.archive.list_files(self.archive.root_name)):
                self.lms_accessors.append(LMSAccessor(file.name.removesuffix(".msbt"), self.archive, self.adapter))
        except Exception as e:
            self._exception_ = e


class RarcWriterThread(WorkerThread):
    def __init__(self, parent: QMainWindow, arc_path: str, archive: JKRArchive, lms_accessors: list[LMSAccessor]):
        super().__init__(parent)
        self.arc_path: str = arc_path
        self.archive: JKRArchive = archive
        self.lms_accessors: list[LMSAccessor] = lms_accessors
        self.compress_rarc: bool = SettingsHolder.is_compress_arc()

    def run(self):
        try:
            for lms_accessor in self.lms_accessors:
                lms_accessor.save()

            compression = JKRCompression.SZS if self.compress_rarc else JKRCompression.NONE
            pyjkernel.write_archive_file(self.archive, self.arc_path, compression=compression)
        except Exception as e:
            self._exception_ = e
