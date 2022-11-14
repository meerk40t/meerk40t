from meerk40t.core.node.blobnode import BlobNode
from meerk40t.core.node.branch_elems import BranchElementsNode
from meerk40t.core.node.branch_ops import BranchOperationsNode
from meerk40t.core.node.branch_regmark import BranchRegmarkNode
from meerk40t.core.node.cutnode import CutNode
from meerk40t.core.node.elem_ellipse import EllipseNode
from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.node.elem_line import LineNode
from meerk40t.core.node.elem_numpath import NumpathNode
from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.node.elem_point import PointNode
from meerk40t.core.node.elem_polyline import PolylineNode
from meerk40t.core.node.elem_rect import RectNode
from meerk40t.core.node.elem_text import TextNode
from meerk40t.core.node.filenode import FileNode
from meerk40t.core.node.groupnode import GroupNode
from meerk40t.core.node.lasercodenode import LaserCodeNode
from meerk40t.core.node.layernode import LayerNode
from meerk40t.core.node.node import Node
from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_dots import DotsOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_hatch import HatchOpNode
from meerk40t.core.node.op_image import ImageOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.core.node.refnode import ReferenceNode
from meerk40t.core.node.util_console import ConsoleOperation
from meerk40t.core.node.util_goto import GotoOperation
from meerk40t.core.node.util_home import HomeOperation
from meerk40t.core.node.util_input import InputOperation
from meerk40t.core.node.util_origin import SetOriginOperation
from meerk40t.core.node.util_output import OutputOperation
from meerk40t.core.node.util_wait import WaitOperation


class RootNode(Node):
    """
    RootNode is one of the few directly declarable node-types and serves as the base type for all Node classes.

    The notifications are shallow. They refer *only* to the node in question, not to any children or parents.
    """

    def __init__(self, context, id=None, label=None, lock=False, **kwargs):
        _ = context._
        super(RootNode, self).__init__(
            type="root", id=id, label=label, lock=lock, **kwargs
        )
        self._root = self
        self.context = context
        self.listeners = []
        self.bootstrap = bootstrap
        self.add(type="branch ops", label=_("Operations"))
        self.add(type="branch elems", label=_("Elements"))
        self.add(type="branch reg", label=_("Regmarks"))

    def __repr__(self):
        return f"RootNode({str(self.context)})"

    def __copy__(self):
        return RootNode(self.context, id=self.id, label=self.label, lock=self.lock)

    def is_draggable(self):
        return False

    def listen(self, listener):
        self.listeners.append(listener)

    def unlisten(self, listener):
        self.listeners.remove(listener)

    def notify_created(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "node_created"):
                listen.node_created(node, **kwargs)

    def notify_destroyed(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "node_destroyed"):
                listen.node_destroyed(node, **kwargs)

    def notify_attached(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "node_attached"):
                listen.node_attached(node, **kwargs)

    def notify_detached(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "node_detached"):
                listen.node_detached(node, **kwargs)

    def notify_changed(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "node_changed"):
                listen.node_changed(node, **kwargs)

    def notify_selected(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "selected"):
                listen.selected(node, **kwargs)

    def notify_emphasized(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "emphasized"):
                listen.emphasized(node, **kwargs)

    def notify_targeted(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "targeted"):
                listen.targeted(node, **kwargs)

    def notify_highlighted(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "highlighted"):
                listen.highlighted(node, **kwargs)

    def notify_modified(self, node=None, **kwargs):
        """
        Notifies any listeners that a value in the tree has been changed such that the matrix or other property
        values have changed. But that the underlying data object itself remains intact.
        @param node: node that was modified.
        @param kwargs:
        @return:
        """
        if node is None:
            node = self
        self._bounds = None
        for listen in self.listeners:
            if hasattr(listen, "modified"):
                listen.modified(node, **kwargs)

    def notify_altered(self, node=None, **kwargs):
        """
        Notifies any listeners that a value in the tree has had its underlying data fundamentally changed and while
        this may not be reflected by the properties any assumptions about the content of this node are no longer
        valid.

        @param node:
        @param kwargs:
        @return:
        """
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "altered"):
                listen.altered(node, **kwargs)

    def notify_expand(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "expand"):
                listen.expand(node, **kwargs)

    def notify_collapse(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "collapse"):
                listen.collapse(node, **kwargs)

    def notify_reorder(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "reorder"):
                listen.reorder(node, **kwargs)

    def notify_update(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "update"):
                listen.update(node, **kwargs)

    def notify_focus(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "focus"):
                listen.focus(node, **kwargs)


bootstrap = {
    "root": RootNode,
    "op cut": CutOpNode,
    "op engrave": EngraveOpNode,
    "op raster": RasterOpNode,
    "op image": ImageOpNode,
    "op dots": DotsOpNode,
    "op hatch": HatchOpNode,
    "util console": ConsoleOperation,
    "util wait": WaitOperation,
    "util origin": SetOriginOperation,
    "util home": HomeOperation,
    "util goto": GotoOperation,
    "util input": InputOperation,
    "util output": OutputOperation,
    "lasercode": LaserCodeNode,
    "blob": BlobNode,
    "group": GroupNode,
    "layer": LayerNode,
    "elem ellipse": EllipseNode,
    "elem line": LineNode,
    "elem rect": RectNode,
    "elem path": PathNode,
    "elem point": PointNode,
    "elem polyline": PolylineNode,
    "elem image": ImageNode,
    "elem text": TextNode,
    "elem numpath": NumpathNode,
    "reference": ReferenceNode,
    "cutcode": CutNode,
    "branch ops": BranchOperationsNode,
    "branch elems": BranchElementsNode,
    "branch reg": BranchRegmarkNode,
    "file": FileNode,
}
