from __future__ import annotations

from NodeGraphQt import NodeGraph, BaseNode
from PyQt5.QtWidgets import QMainWindow
from pymsb import LMSEntryNode, LMSMessageNode, LMSBranchNode, LMSEventNode

from adapter_smg2 import SuperMarioGalaxy2Adapter
from msbtaccess import flattened_nodes


class FlowchartEditor:
    def __init__(self, parent: QMainWindow, adapter_maker: type[SuperMarioGalaxy2Adapter]):
        # --------------------------------------------------------------------------------------------------------------
        # Variable declarations

        self._parent_: QMainWindow = parent
        self._adapter_maker_ = adapter_maker
        self._graph_ = NodeGraph()
        self._widget_ = self._graph_.widget
        self._flowchart_: LMSEntryNode | None = None

        # --------------------------------------------------------------------------------------------------------------

        self._graph_.register_nodes([
            EditorEntryNode,
            EditorMessageNode,
            EditorBranchNode,
            EditorEventNode
        ])

    def show(self, flowchart: LMSEntryNode):
        self._flowchart_ = flowchart
        self._widget_.resize(800, 600)
        self._widget_.show()  # here or at end?

        self._graph_.clear_session()
        self._build_nodes_()

    def _build_nodes_(self):
        mapping = {}

        def create_or_get(node):
            if node not in mapping:
                if type(node) == LMSEntryNode:
                    editor_node = self._graph_.create_node(node_key("EditorEntryNode"), node.label)
                    mapping[node] = editor_node
                elif type(node) == LMSMessageNode:
                    editor_node = self._graph_.create_node(node_key("EditorMessageNode"), node.message_label)
                    mapping[node] = editor_node
                elif type(node) == LMSBranchNode:
                    editor_node = self._graph_.create_node(node_key("EditorBranchNode"))
                    mapping[node] = editor_node
                elif type(node) == LMSEventNode:
                    editor_node = self._graph_.create_node(node_key("EditorEventNode"))
                    mapping[node] = editor_node

            return mapping[node]

        for node in flattened_nodes(self._flowchart_):
            editor_node = create_or_get(node)

            if node.next_node is not None:
                next_editor_node = create_or_get(node.next_node)
                editor_node.set_output(0, next_editor_node.input(0))

            if type(node) == LMSBranchNode and node.next_node_else is not None:
                next_editor_node = create_or_get(node.next_node_else)
                editor_node.set_output(1, next_editor_node.input(0))

        self._graph_.auto_layout_nodes(start_nodes=self._graph_.all_nodes())
        self._graph_.clear_selection()
        self._graph_.fit_to_selection()

# ----------------------------------------------------------------------------------------------------------------------


__NAMESPACE__ = "galaxymsbt.nodes"


def node_key(type: str) -> str:
    return f"{__NAMESPACE__}.{type}"


class EditorEntryNode(BaseNode):
    __identifier__ = __NAMESPACE__

    def __init__(self):
        super(EditorEntryNode, self).__init__()

        self.add_output(name="next", multi_output=False)


class EditorMessageNode(BaseNode):
    __identifier__ = __NAMESPACE__

    def __init__(self):
        super(EditorMessageNode, self).__init__()

        self.add_input(multi_input=True)
        self.add_output(name="Next", multi_output=False)


class EditorBranchNode(BaseNode):
    __identifier__ = __NAMESPACE__

    def __init__(self):
        super(EditorBranchNode, self).__init__()

        self.add_input(multi_input=True)
        self.add_output(name="iftrue", multi_output=False)
        self.add_output(name="otherwise", multi_output=False)


class EditorEventNode(BaseNode):
    __identifier__ = __NAMESPACE__

    def __init__(self):
        super(EditorEventNode, self).__init__()

        self.add_input(multi_input=True)
        self.add_output(multi_output=False)

