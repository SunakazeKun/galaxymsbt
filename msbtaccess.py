from typing import Generator

from natsort import natsort_keygen
from pyjkernel import JKRArchive, JKRArchiveFile
from pymsb import LMSDocument, LMSMessage, LMSFlows, LMSEntryNode, LMSMessageNode, LMSBranchNode
from adapter_smg2 import SuperMarioGalaxy2Adapter
import pymsb

__all__ = ["LMSAccessor"]


class LMSAccessor:
    __LABEL_SORT_KEY__ = natsort_keygen(key=lambda e: e.label)

    def __init__(self, name: str, archive: JKRArchive, adapter: type[SuperMarioGalaxy2Adapter]):
        """
        Creates a new ``LMSAccessor`` with the specified name and adapter. The given archive will be used to retrieve
        contents from and save files to. If there are no MSBT or MSBF files, blank new holders will be constructed.
        Otherwise, the messages and flowcharts will be constructed from the files.

        :param name: the name of MSBT and MSBF files.
        :param archive: the RARC archive.
        :param adapter: the adapter maker used to construct the game-specific adapter.
        """
        self._name_: str = name
        self._archive_: JKRArchive = archive
        self._document_: LMSDocument
        self._flows_: LMSFlows

        msbt_path = create_msbt_file_path(self._archive_, self._name_)
        msbf_path = create_msbf_file_path(self._archive_, self._name_)

        if self._archive_.directory_exists(msbt_path):
            self._document_ = pymsb.msbt_from_buffer(adapter, self._archive_.get_file(msbt_path).data)
        else:
            self._document_ = LMSDocument(adapter)

        if self._archive_.directory_exists(msbf_path):
            self._flows_ = pymsb.msbf_from_buffer(adapter, self._archive_.get_file(msbf_path).data)
            self._link_flowcharts_with_message_labels_()
        else:
            self._flows_ = LMSFlows(adapter)

    @property
    def name(self) -> str:
        """Returns the accessor's name."""
        return self._name_

    @property
    def archive(self) -> JKRArchive:
        """Returns the parent archive."""
        return self._archive_

    @property
    def messages(self) -> list[LMSMessage]:
        """Returns the list of messages."""
        return self._document_.messages

    @property
    def flowcharts(self) -> list[LMSEntryNode]:
        """Returns the list of flowcharts."""
        return self._flows_.flowcharts

    # ------------------------------------------------------------------------------------------------------------------

    def new_message(self, label: str) -> LMSMessage:
        """
        Creates and returns a new message entry using the given label and adds it to the list of messages. If an entry
        with the same label already exists, an LMSException will be thrown.

        :param label: the new message's label.
        :return: the new message entry.
        """
        return self._document_.new_message(label)

    def delete_message(self, label: str) -> bool:
        """
        Tries to delete the message entry with the specified label. If there's at least one flow node that references
        this label, the entry won't be removed. If there's no entry with such label, a KeyError will be thrown.

        :param label: the message's label that should be deleted.
        :return: True if the message was deleted, otherwise False.
        """
        # Don't delete message if referenced by a flow node
        for flowchart in self.flowcharts:
            for node in filter(lambda n: type(n) == LMSMessageNode, flattened_nodes(flowchart)):
                if node.message_label == label:
                    return False

        # Find index of message associated with label
        index = -1

        for i, message in enumerate(self.messages):
            if message.label == label:
                index = i
                break

        if index == -1:
            raise KeyError(f"No message labeled {label} found!")

        # If allowed, remove the actual entry
        self.messages.pop(index)
        return True

    def rename_message(self, old_label: str, new_label: str) -> bool:
        """
        Tries to rename the message entry with the specified labels. If the two labels are the same, nothing is done,
        but True is returned. If there's at least one other message entry whose name is the same as the new label, False
        will be returned and no renaming occurs. Otherwise, the old label will be renamed to the new label. This also
        affects all flow nodes. If there's no entry with such label, a KeyError will be thrown.

        :param old_label: the label of the message whose name should be renamed.
        :param new_label: the new name.
        :return: True if the labels are the same or if renaming was successful, otherwise False.
        """
        if old_label == new_label:
            return True

        # Find message entry associated with label
        associated_message: LMSMessage | None = None

        for message in self.messages:
            if message.label == old_label:
                associated_message = message
            elif message.label == new_label:
                return False

        if associated_message is None:
            raise KeyError(f"No message labeled {old_label} found!")

        # Update message entry's label and flow node references
        associated_message.label = new_label

        for flowchart in self.flowcharts:
            for node in filter(lambda n: type(n) == LMSMessageNode, flattened_nodes(flowchart)):
                if node.message_label == old_label:
                    node.message_label = new_label

        return True

    def sort_messages(self):
        """Sorts all messages by their labels in natural ascending order."""
        self._document_.messages.sort(key=self.__LABEL_SORT_KEY__)

    # ------------------------------------------------------------------------------------------------------------------

    def new_flowchart(self, label: str) -> LMSEntryNode:
        """
        Creates and returns a new flowchart using the given label and adds it to the list of flowcharts. If a flowchart
        with the same label already exists, an LMSException will be thrown.

        :param label: the new message's label.
        :return: the new flowchart.
        """
        return self._flows_.new_flowchart(label)

    def delete_flowchart(self, label: str) -> bool:
        return False

    def rename_flowchart(self, old_label: str, new_label: str) -> bool:
        return False

    def sort_flowcharts(self):
        """Sorts all flowcharts by their labels in natural ascending order."""
        self._flows_.flowcharts.sort(key=self.__LABEL_SORT_KEY__)

    # ------------------------------------------------------------------------------------------------------------------

    def save(self):
        msbt_file: JKRArchiveFile
        msbf_file: JKRArchiveFile
        msbt_path = create_msbt_file_path(self._archive_, self._name_)
        msbf_path = create_msbf_file_path(self._archive_, self._name_)

        # Always pack and keep MSBT
        if not self._archive_.directory_exists(msbt_path):
            msbt_file = self._archive_.create_file(msbt_path)
        else:
            msbt_file = self._archive_.get_file(msbt_path)

        msbt_file.data = self._document_.makebin()

        # Pack and keep MSBF if and only if there is at least one flowchart
        if len(self._flows_.flowcharts) > 0:
            if not self._archive_.directory_exists(msbf_path):
                msbf_file = self._archive_.create_file(msbf_path)
            else:
                msbf_file = self._archive_.get_file(msbf_path)

            self._link_flowcharts_with_message_indexes_()
            msbf_file.data = self._flows_.makebin()

        elif self._archive_.directory_exists(msbf_path):
            self._archive_.remove_file(msbf_path)

    def delete(self):
        """
        Clears all message entries, flowcharts, and removes associated MSBT and MSBF files in the archive.
        """
        msbt_path = create_msbt_file_path(self._archive_, self._name_)
        msbf_path = create_msbf_file_path(self._archive_, self._name_)

        self.messages.clear()
        self.flowcharts.clear()

        if self._archive_.directory_exists(msbt_path):
            self._archive_.remove_file(msbt_path)

        if self._archive_.directory_exists(msbf_path):
            self._archive_.remove_file(msbf_path)

    def _link_flowcharts_with_message_labels_(self):
        for flowchart in self.flowcharts:
            for node in filter(lambda n: type(n) == LMSMessageNode, flattened_nodes(flowchart)):
                node.message_label = self.messages[node.msbt_entry_idx].label

    def _link_flowcharts_with_message_indexes_(self):
        message_labels = [m.label for m in self.messages]

        for flowchart in self.flowcharts:
            for node in filter(lambda n: type(n) == LMSMessageNode, flattened_nodes(flowchart)):
                node.msbt_entry_idx = message_labels.index(node.message_label)


# ----------------------------------------------------------------------------------------------------------------------
# Helper functions for MSBT/MSBF files

def flattened_nodes(flowchart: LMSEntryNode) -> Generator:
    """
    Generator that yields the flow nodes in the given flowchart. This is done using breadth-first search. Every flow
    node will be yielded exactly once, even if they are referenced more than once. This always starts at the root node.

    :param flowchart: the flowchart.
    :return: the next flow node.
    """
    remaining = [flowchart]
    marked = set()

    while len(remaining) > 0:
        current_node = remaining.pop(0)
        next_node = current_node.next_node
        marked.add(current_node)

        if next_node is not None and next_node not in marked:
            remaining.append(next_node)

        if type(current_node) == LMSBranchNode:
            next_node = current_node.next_node_else

            if next_node is not None and next_node not in marked:
                remaining.append(next_node)

        yield current_node


def create_msbt_file_path(archive: JKRArchive, lms_name: str) -> str:
    return f"{archive.root_name}/{lms_name}.msbt"


def create_msbf_file_path(archive: JKRArchive, lms_name: str) -> str:
    return f"{archive.root_name}/{lms_name}.msbf"
