from natsort import natsort_keygen
from pyjkernel import JKRArchiveFile
from pymsb import LMSDocument, LMSMessage
from adapter_smg2 import SuperMarioGalaxy2Adapter
import pymsb

__all__ = ["MsbtAccessor"]


class MsbtAccessor:
    __LABEL_SORT_KEY__ = natsort_keygen(key=lambda e: e.label)

    def __init__(self, adapter: type[SuperMarioGalaxy2Adapter], file: JKRArchiveFile):
        """
        Creates a new ``MsbtAccessor`` from the given JKRArchiveFile and adapter. If the file's content is empty, a
        blank new LMS document will be constructed. Otherwise, the document will be constructed from the file's content.

        :param adapter: the adapter maker used to construct the game-specific adapter.
        :param file: the file inside the RARC archive.
        """
        self._file_ = file
        self._document_ = LMSDocument(adapter) if len(file.data) == 0 else pymsb.msbt_from_buffer(adapter, file.data)

    @property
    def messages(self) -> list[LMSMessage]:
        """Returns the LMS document's list of messages."""
        return self._document_.messages

    @property
    def document(self) -> LMSDocument:
        """Returns the MSBT's LMS document."""
        return self._document_

    @property
    def name(self) -> str:
        """Returns the MSBT's file name."""
        return self._file_.name

    def save(self):
        """Packs the LMS document and writes the data to the file in the RARC archive."""
        self._file_.data = self._document_.makebin()

    def sort_messages(self):
        """Sorts all message by their labels in natural ascending order."""
        self._document_.messages.sort(key=self.__LABEL_SORT_KEY__)
