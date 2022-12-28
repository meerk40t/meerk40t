import functools
import os.path
import re
import time
from copy import copy
from math import cos, gcd, pi, sin, tau

from .exceptions import BadFileError
from ..device.lasercommandconstants import (
    COMMAND_BEEP,
    COMMAND_CONSOLE,
    COMMAND_FUNCTION,
    COMMAND_HOME,
    COMMAND_LASER_OFF,
    COMMAND_LASER_ON,
    COMMAND_MODE_RAPID,
    COMMAND_MOVE,
    COMMAND_SET_ABSOLUTE,
    COMMAND_WAIT,
    COMMAND_WAIT_FINISH,
)
from ..image.actualize import actualize
from ..kernel import Modifier
from ..svgelements import (
    PATTERN_FLOAT,
    PATTERN_LENGTH_UNITS,
    PATTERN_PERCENT,
    REGEX_LENGTH,
    SVG_STRUCT_ATTRIB,
    Angle,
    Circle,
    Close,
    Color,
    CubicBezier,
    Ellipse,
    Group,
)
from ..svgelements import Length as SVGLength
from ..svgelements import (
    Line,
    Matrix,
    Move,
    Path,
    Point,
    Polygon,
    Polyline,
    QuadraticBezier,
    Rect,
    Shape,
    SimpleLine,
    SVGElement,
    SVGImage,
    SVGText,
    Viewbox,
)
from ..tools.rastergrouping import group_overlapped_rasters
from .cutcode import (
    CubicCut,
    CutCode,
    CutGroup,
    LaserSettings,
    LineCut,
    QuadCut,
    RasterCut,
)


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Elemental", Elemental)
    elif lifecycle == "boot":
        kernel_root = kernel.root
        kernel_root.activate("modifier/Elemental")
    elif lifecycle == "ready":
        context = kernel.root
        context.signal("rebuild_tree")
        context.signal("refresh_tree")


MILS_IN_MM = 39.3701

# Regex expressions
label_truncate_re = re.compile("(:.*)|(\([^ )]*\s.*)")
group_simplify_re = re.compile(
    "(\([^()]+?\))|(SVG(?=Image|Text))|(Simple(?=Line))", re.IGNORECASE
)
subgroup_simplify_re = re.compile("\[[^][]*\]", re.IGNORECASE)
# I deally we would show the positions in the same UoM as set in Settings (with variable precision depending on UoM,
# but until then element descriptions are shown in mils and 2 decimal places (for opacity) should be sufficient for user to see
element_simplify_re = re.compile("(^Simple(?=Line))|((?<=\.\d{2})(\d+))", re.IGNORECASE)
# image_simplify_re = re.compile("(^SVG(?=Image))|((,\s*)?href=('|\")data:.*?('|\")(,\s?|\s|(?=\))))|((?<=\.\d{2})(\d+))", re.IGNORECASE)
image_simplify_re = re.compile(
    "(^SVG(?=Image))|((,\s*)?href=('|\")data:.*?('|\")(,\s?|\s|(?=\))))|((?<=\d)(\.\d*))",
    re.IGNORECASE,
)

OP_PRIORITIES = ["Dots", "Image", "Raster", "Engrave", "Cut"]

# Overload svgelement Length class by adding a validity check
class Length(SVGLength):
    is_valid_length = False

    def __init__(self, *args, **kwargs):
        # Call super_init...
        super().__init__(*args, **kwargs)
        self.is_valid_length = False
        if len(args) == 1:
            value = args[0]
            if value is None:
                return
            s = str(value)
            for m in REGEX_LENGTH.findall(s):
                if len(m[1]) == 0 or m[1] in (
                    PATTERN_LENGTH_UNITS + "|" + PATTERN_PERCENT
                ):
                    self.is_valid_length = True
                return
        elif len(args) == 2:
            try:
                x = float(args[0])
                if len(args[1]) == 0 or args[1] in (
                    PATTERN_LENGTH_UNITS + "|" + PATTERN_PERCENT
                ):
                    self.is_valid_length = True
            except ValueError:
                pass
            return


def reversed_enumerate(collection: list):
    for i in range(len(collection) - 1, -1, -1):
        yield i, collection[i]


def isDot(element):
    if not isinstance(element, Shape):
        return False
    if isinstance(element, Path):
        path = element
    else:
        path = element.segments()

    if len(path) == 2 and isinstance(path[0], Move):
        if isinstance(path[1], Close):
            return True
        if isinstance(path[1], Line) and path[1].length() == 0:
            return True
    return False


def isStraightLine(element):
    if not isinstance(element, Shape):
        return False
    if isinstance(element, Path):
        path = element
    else:
        path = element.segments()

    if len(path) == 2 and isinstance(path[0], Move):
        if isinstance(path[1], Line) and path[1].length() > 0:
            return True
    return False


"""
The elements modifier stores all the element types in a bootstrapped tree. Specific node types added to the tree become
particular class types and the interactions between these types and functions applied are registered in the kernel.

Types:
root: Root Tree element
branch ops: Operation Branch
branch elems: Elements Branch
opnode: Element below op branch which stores specific data.
op: LayerOperation within Operation Branch.
opcmd: CommandOperation within Operation Branch.
elem: Element with Element Branch or subgroup.
file: File Group within Elements Branch
group: Group type within Branch Elems or opnode.
cutcode: CutCode type within Operation Branch and Element Branch.

rasternode: theoretical: would store all the opnodes to be rastered. Such that we could store rasters in images.

Tree Functions are to be stored: tree/command/type. These store many functions like the commands.
"""


class Node:
    """
    Nodes are elements within the tree which stores most of the objects in Elements.
    """

    def __init__(self, data_object=None, type=None, *args, **kwargs):
        super().__init__()
        self._children = list()
        self._root = None
        self._parent = None
        self._references = list()

        self.object = data_object
        self.type = type

        self._selected = False
        self._emphasized = False
        self._highlighted = False
        self._target = False

        self._opened = False

        self._bounds = None
        self._bounds_dirty = True
        self.label = None

        self.item = None
        self.icon = None
        self.cache = None
        self.last_transform = None

    def __repr__(self):
        return "Node('%s', %s, %s)" % (self.type, str(self.object), str(self._parent))

    def __eq__(self, other):
        return other is self

    def is_movable(self):
        return self.type not in ("branch elems", "branch ops", "root")

    def drop(self, drag_node):
        drop_node = self
        if drag_node.type == "elem":
            if drop_node.type == "op":
                # Disallow drop of non-image elems onto an Image op.
                # Disallow drop of image elems onto a Dot op.
                if (
                    not isinstance(drag_node.object, SVGImage)
                    and drop_node.operation == "Image"
                ) or (
                    isinstance(drag_node.object, SVGImage)
                    and drop_node.operation == "Dots"
                ):
                    return False
                # Dragging element onto operation adds that element to the op.
                drop_node.add(drag_node.object, type="opnode", pos=0)
                return True
            elif drop_node.type == "opnode":
                op = drop_node.parent
                # Disallow drop of non-image elems onto an opnode inside an Image op.
                # Disallow drop of image elems onto an opnode inside a Dot op.
                if (
                    not isinstance(drag_node.object, SVGImage)
                    and op.operation == "Image"
                ) or (
                    isinstance(drag_node.object, SVGImage) and op.operation == "Dots"
                ):
                    return False
                # Dragging element onto existing opnode in operation adds that element to the op after the opnode.
                drop_index = op.children.index(drop_node)
                op.add(drag_node.object, type="opnode", pos=drop_index)
                return True
            elif drop_node.type == "group":
                # Dragging element onto a group moves it to the group node.
                drop_node.append_child(drag_node)
                return True
        elif drag_node.type == "opnode":
            if drop_node.type == "op":
                # Disallow drop of non-image opnodes onto an Image op.
                # Disallow drop of image opnodes onto a Dot op.
                if (
                    not isinstance(drag_node.object, SVGImage)
                    and drop_node.operation == "Image"
                ) or (
                    isinstance(drag_node.object, SVGImage)
                    and drop_node.operation == "Dots"
                ):
                    return False
                # Move an opnode to end of op.
                drop_node.append_child(drag_node)
                return True
            if drop_node.type == "opnode":
                op = drop_node.parent
                # Disallow drop of non-image opnodes onto an opnode inside an Image op.
                # Disallow drop of image opnodes onto an opnode inside a Dot op.
                if (
                    not isinstance(drag_node.object, SVGImage)
                    and op.operation == "Image"
                ) or (
                    isinstance(drag_node.object, SVGImage) and op.operation == "Dots"
                ):
                    return False
                # Move an opnode to after another opnode.
                drop_node.insert_sibling(drag_node)
                return True
        elif drag_node.type in ("op", "cmdop", "consoleop"):
            if drop_node.type in ("op", "cmdop", "consoleop"):
                # Move operation to a different position.
                drop_node.insert_sibling(drag_node)
                return True
            elif drop_node.type == "branch ops":
                # Dragging operation to op branch to effectively move to bottom.
                drop_node.append_child(drag_node)
                return True
        elif drag_node.type in "file":
            if drop_node.type == "op":
                some_nodes = False
                for e in drag_node.flat("elem"):
                    # Disallow drop of non-image elems onto an Image op.
                    # Disallow drop of image elems onto a Dot op.
                    if (
                        not isinstance(e.object, SVGImage)
                        and drop_node.operation == "Image"
                    ) or (
                        isinstance(e.object, SVGImage) and drop_node.operation == "Dots"
                    ):
                        continue
                    # Add element to operation
                    drop_node.add(e.object, type="opnode")
                    some_nodes = True
                return some_nodes
        elif drag_node.type == "group":
            if drop_node.type == "elem":
                # Move a group
                drop_node.insert_sibling(drag_node)
                return True
            elif drop_node.type in ("group", "file"):
                # Move a group
                drop_node.append_child(drag_node)
                return True
            elif drop_node.type == "op":
                some_nodes = False
                for e in drag_node.flat("elem"):
                    # Disallow drop of non-image elems onto an Image op.
                    # Disallow drop of image elems onto a Dot op.
                    if (
                        not isinstance(e.object, SVGImage)
                        and drop_node.operation == "Image"
                    ) or (
                        isinstance(e.object, SVGImage) and drop_node.operation == "Dots"
                    ):
                        continue
                    # Add element to operation
                    drop_node.add(e.object, type="opnode")
                    some_nodes = True
                return some_nodes
        return False

    def reverse(self):
        self._children.reverse()
        self.notify_reorder()

    @property
    def children(self):
        return self._children

    @property
    def targeted(self):
        return self._target

    @targeted.setter
    def targeted(self, value):
        if self._target == value:
            return
        self._target = value
        self.notify_targeted(self)

    @property
    def highlighted(self):
        return self._highlighted

    @highlighted.setter
    def highlighted(self, value):
        if self._highlighted == value:
            return
        self._highlighted = value
        self.notify_highlighted(self)

    @property
    def emphasized(self):
        return self._emphasized

    @emphasized.setter
    def emphasized(self, value):
        if self._emphasized == value:
            return
        self._emphasized = value
        self.notify_emphasized(self)

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        if self._selected == value:
            return
        self._selected = value
        self.notify_selected(self)

    @property
    def parent(self):
        return self._parent

    @property
    def root(self):
        return self._root

    @staticmethod
    def node_bbox(node):
        for n in node._children:
            Node.node_bbox(n)
        # Recurse depth first. All children have been processed.
        node._bounds_dirty = False
        node._bounds = None
        if node.type in ("file", "group"):
            for c in node._children:
                # Every child in n is already solved.
                assert not c._bounds_dirty
                if c._bounds is None:
                    continue
                if node._bounds is None:
                    node._bounds = c._bounds
                    continue
                node._bounds = (
                    min(node._bounds[0], c._bounds[0]),
                    min(node._bounds[1], c._bounds[1]),
                    max(node._bounds[2], c._bounds[2]),
                    max(node._bounds[3], c._bounds[3]),
                )
        else:
            e = node.object
            if node.type == "elem" and hasattr(e, "bbox"):
                node._bounds = e.bbox()

    @property
    def bounds(self):
        if self._bounds_dirty:
            self.node_bbox(self)
        return self._bounds

    def notify_created(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_created(node=node, **kwargs)

    def notify_destroyed(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_destroyed(node=node, **kwargs)

    def notify_attached(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_attached(node=node, **kwargs)

    def notify_detached(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_detached(node=node, **kwargs)

    def notify_changed(self, node, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_changed(node=node, **kwargs)

    def notify_selected(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_selected(node=node, **kwargs)

    def notify_emphasized(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_emphasized(node=node, **kwargs)

    def notify_targeted(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_targeted(node=node, **kwargs)

    def notify_highlighted(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_highlighted(node=node, **kwargs)

    def notify_modified(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_modified(node=node, **kwargs)

    def notify_altered(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_altered(node=node, **kwargs)

    def notify_expand(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_expand(node=node, **kwargs)

    def notify_collapse(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_collapse(node=node, **kwargs)

    def notify_reorder(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_reorder(node=node, **kwargs)

    def notify_update(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_update(node=node, **kwargs)

    def notify_focus(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_focus(node=node, **kwargs)

    def focus(self):
        self.notify_focus(self)

    def invalidated_node(self):
        """
        Invalidation of the individual node.
        """
        self._bounds_dirty = True
        self._bounds = None

    def invalidated(self):
        """
        Invalidation occurs when the underlying data is altered or modified. This propagates up from children to
        invalidate the entire parental line.
        """
        self.invalidated_node()
        if self._parent is not None:
            self._parent.invalidated()

    def modified(self):
        """
        The matrix transformation was changed. The object is shaped differently but fundamentally the same structure of
        data.
        """
        self.invalidated()
        self.notify_modified(self)

    def altered(self):
        """
        The data structure was changed. Any assumptions about what this object is/was are void.
        """
        try:
            self.cache.UnGetNativePath(self.object.cache.NativePath)
        except AttributeError:
            pass
        try:
            del self.cache
            del self.icon
        except AttributeError:
            pass
        self.cache = None
        self.icon = None
        self.invalidated()
        self.notify_altered(self)

    def unregister_object(self):
        try:
            self.cache.UngetNativePath(self.cache.NativePath)
        except AttributeError:
            pass
        try:
            del self.cache
        except AttributeError:
            pass
        try:
            del self.icon
        except AttributeError:
            pass

    def unregister(self):
        self.unregister_object()
        try:
            self.targeted = False
            self.emphasized = False
            self.highlighted = False
        except AttributeError:
            pass

    def add_all(self, objects, type=None, name=None, pos=None):
        for obj in objects:
            self.add(obj, type=type, label=name, pos=pos)
            if pos is not None:
                pos += 1

    def add(self, data_object=None, type=None, label=None, pos=None):
        """
        Add a new node bound to the data_object of the type to the current node.
        If the data_object itself is a node already it is merely attached.

        :param data_object:
        :param type:
        :param label: display name for this node
        :param pos:
        :return:
        """
        if isinstance(data_object, Node):
            node = data_object
            if node._parent is not None:
                raise ValueError("Cannot reparent node on add.")
        else:
            node_class = Node
            if type is not None:
                try:
                    node_class = self._root.bootstrap[type]
                except (KeyError, AttributeError):
                    # AttributeError indicates that we are adding a node with a type to an object which is NOT part of the tree.
                    # This should be treated as an exception, however when we run Execute Job (and possibly other tasks)
                    # it adds nodes even though the object isn't part of the tree.
                    pass
                # except AttributeError:
                #    raise AttributeError('%s needs to be added to tree before adding "%s" for %s' % (self.__class__.__name__, type, data_object.__class__.__name__))
            node = node_class(data_object)
            node.set_label(label)
            if self._root is not None:
                self._root.notify_created(node)
        node.type = type

        node._parent = self
        node._root = self._root
        if pos is None:
            self._children.append(node)
        else:
            self._children.insert(pos, node)
        node.notify_attached(node, pos=pos)
        return node

    def label_from_source_cascade(self, element) -> str:
        """
        Creates a cascade of different values that could give the node name. Label, inkscape:label, id, node-object str,
        node str. If something else provides a superior name it should be added in here.
        """
        element_type = element.__class__.__name__
        if element_type == "SVGImage":
            element_type = "Image"
        elif element_type == "SVGText":
            element_type = "Text"
        elif element_type == "SimpleLine":
            element_type = "Line"
        elif isDot(element):
            element_type = "Dot"

        if element is not None:
            desc = str(element)
            if isinstance(element, Path):
                desc = element_simplify_re.sub("", desc)
                if len(desc) > 100:
                    desc = desc[:100] + "…"
                values = []
                if element.stroke is not None:
                    values.append("%s='%s'" % ("stroke", element.stroke))
                if element.fill is not None:
                    values.append("%s='%s'" % ("fill", element.fill))
                if element.stroke_width is not None and element.stroke_width != 1.0:
                    values.append(
                        "%s=%s" % ("stroke-width", str(round(element.stroke_width, 2)))
                    )
                if not element.transform.is_identity():
                    values.append("%s=%s" % ("transform", repr(element.transform)))
                if element.id is not None:
                    values.append("%s='%s'" % ("id", element.id))
                if values:
                    desc = "d='%s', %s" % (desc, ", ".join(values))
                desc = element_type + "(" + desc + ")"
            elif element_type == "Group":  # Group
                desc = desc[1:-1]  # strip leading and trailing []
                n = 1
                while n:
                    desc, n = group_simplify_re.subn("", desc)
                n = 1
                while n:
                    desc, n = subgroup_simplify_re.subn("Group", desc)
                desc = "%s(%s)" % (element_type, desc)
            elif element_type == "Image":  # Image
                desc = image_simplify_re.sub("", desc)
            else:
                desc = element_simplify_re.sub("", desc)
        else:
            desc = None

        try:
            attribs = element.values[SVG_STRUCT_ATTRIB]
            return attribs["label"] + (": " + desc if desc else "")
        except (AttributeError, KeyError):
            pass

        try:
            attribs = element.values[SVG_STRUCT_ATTRIB]
            return attribs["{http://www.inkscape.org/namespaces/inkscape}label"] + (
                ": " + desc if desc else ""
            )
        except (AttributeError, KeyError):
            pass

        try:
            if element.id is not None:
                return str(element.id) + (": " + desc if desc else "")
        except AttributeError:
            pass

        return desc if desc else str(element)

    def set_label(self, name=None):
        self.label = self.create_label(name)

    def create_label(self, name=None):
        """
        Create a label for this node.
        If a name is not specified either use a cascade (primarily for elements) or
        use the string representation
        :param name: Name to be set for this node.
        :return: label
        """
        if name is not None:
            return name
        if self.object is not None:
            return self.label_from_source_cascade(self.object)
        return str(self)

    def _flatten(self, node):
        """
        Yield this node and all descendants in a flat generation.

        :param node: starting node
        :return:
        """
        yield node
        for c in self._flatten_children(node):
            yield c

    def _flatten_children(self, node):
        """
        Yield all descendants in a flat generation.

        :param node: starting node
        :return:
        """
        for child in node.children:
            yield child
            for c in self._flatten_children(child):
                yield c

    def flat(
        self,
        types=None,
        cascade=True,
        depth=None,
        selected=None,
        emphasized=None,
        targeted=None,
        highlighted=None,
    ):
        """
        Returned flat list of matching nodes. If cascade is set then any matching group will give all the descendants
        of the given type, even if those descendants are beyond the depth limit. The sub-elements do not need to match
        the criteria with respect to either the depth or the emphases.

        :param types: types of nodes permitted to be returned
        :param cascade: cascade all subitems if a group matches the criteria.
        :param depth: depth to search within the tree.
        :param selected: match only selected nodes
        :param emphasized: match only emphasized nodes.
        :param targeted: match only targeted nodes
        :param highlighted: match only highlighted nodes
        :return:
        """
        node = self
        if (
            (targeted is None or targeted == node.targeted)
            and (emphasized is None or emphasized == node.emphasized)
            and (selected is None or selected == node.selected)
            and (highlighted is None or highlighted != node.highlighted)
        ):
            # Matches the emphases.
            if cascade:
                # Give every type-matched descendant.
                for c in self._flatten(node):
                    if types is None or c.type in types:
                        yield c
                # Do not recurse further. This node is end node.
                return
            else:
                if types is None or node.type in types:
                    yield node
        if depth is not None:
            if depth <= 0:
                # Depth limit reached. Do not evaluate children.
                return
            depth -= 1
        # Check all children.
        for c in node.children:
            yield from c.flat(
                types, cascade, depth, selected, emphasized, targeted, highlighted
            )

    def count_children(self):
        return len(self._children)

    def objects_of_children(self, types):
        if isinstance(self.object, types):
            yield self.object
        for q in self._children:
            for o in q.objects_of_children(types):
                yield o

    def append_child(self, new_child):
        """
        Add the new_child node as the last child of the current node.
        """
        new_parent = self
        source_siblings = new_child.parent.children
        destination_siblings = new_parent.children

        source_siblings.remove(new_child)  # Remove child
        new_child.notify_detached(new_child)

        destination_siblings.append(new_child)  # Add child.
        new_child._parent = new_parent
        new_child.notify_attached(new_child)

    def insert_sibling(self, new_sibling):
        """
        Add the new_sibling node next to the current node.
        """
        reference_sibling = self
        source_siblings = new_sibling.parent.children
        destination_siblings = reference_sibling.parent.children

        reference_position = destination_siblings.index(reference_sibling)

        source_siblings.remove(new_sibling)

        new_sibling.notify_detached(new_sibling)
        destination_siblings.insert(reference_position, new_sibling)
        new_sibling._parent = reference_sibling._parent
        new_sibling.notify_attached(new_sibling, pos=reference_position)

    def replace_object(self, new_object):
        """
        Replace this node's object with a new object.
        """
        if hasattr(self.object, "node"):
            del self.object.node
        for ref in list(self._references):
            ref.object = new_object
            ref.altered()
        new_object.node = self
        self.unregister_object()
        self.object = new_object

    def replace_node(self, *args, **kwargs):
        """
        Replace this current node with a bootstrapped replacement node.
        """
        parent = self._parent
        index = parent._children.index(self)
        parent._children.remove(self)
        self.notify_detached(self)
        node = parent.add(*args, **kwargs, pos=index)
        self.notify_destroyed()
        for ref in list(self._references):
            ref.remove_node()
        self.item = None
        self._parent = None
        self._root = None
        self.type = None
        self.unregister()
        return node

    def remove_node(self, children=True, references=True):
        """
        Remove the current node from the tree.

        This function must iterate down and first remove all children from the bottom.
        """
        if children:
            self.remove_all_children()
        self._parent._children.remove(self)
        self.notify_detached(self)
        self.notify_destroyed(self)
        if references:
            for ref in list(self._references):
                ref.remove_node()
        self.item = None
        self._parent = None
        self._root = None
        self.type = None
        self.unregister()

    def remove_all_children(self):
        """
        Removes all children of the current node.
        """
        for child in list(self.children):
            child.remove_all_children()
            child.remove_node()

    def get(self, obj=None, type=None):
        if (obj is None or obj == self.object) and (type is None or type == self.type):
            return self
        for n in self._children:
            node = n.get(obj, type)
            if node is not None:
                return node

    def move(self, dest, pos=None):
        self._parent.remove(self)
        dest.insert_node(self, pos=pos)


class OpNode(Node):
    """
    OpNode is the bootstrapped node type for the opnode type.

    OpNodes track referenced copies of vector element data.
    """

    def __init__(self, data_object):
        super(OpNode, self).__init__(data_object)
        data_object.node._references.append(self)

    def __repr__(self):
        return "OpNode('%s', %s, %s)" % (
            self.type,
            str(self.object),
            str(self._parent),
        )

    def notify_destroyed(self, node=None, **kwargs):
        self.object.node._references.remove(self)
        super(OpNode, self).notify_destroyed()


class ElemNode(Node):
    """
    ElemNode is the bootstrapped node type for the elem type. All elem types are bootstrapped into this node object.
    """

    def __init__(self, data_object):
        super(ElemNode, self).__init__(data_object)
        self.last_transform = None
        data_object.node = self

    def __repr__(self):
        return "ElemNode('%s', %s, %s)" % (
            self.type,
            str(self.object),
            str(self._parent),
        )

    def drop(self, drag_node):
        drop_node = self
        # Dragging element into element.
        if drag_node.type == "elem":
            drop_node.insert_sibling(drag_node)
            return True
        return False


class GroupNode(Node):
    """
    GroupNode is the bootstrapped node type for the group type.
    All group types are bootstrapped into this node object.
    """

    def __init__(self, data_object=None):
        if data_object is None:
            data_object = Group()
        super(GroupNode, self).__init__(data_object)
        self.last_transform = None
        data_object.node = self

    def __repr__(self):
        return "GroupNode('%s', %s, %s)" % (
            self.type,
            str(self.object),
            str(self._parent),
        )

    def drop(self, drag_node):
        drop_node = self
        # Dragging element into element.
        if drag_node.type == "elem":
            drop_node.insert_sibling(drag_node)
            return True
        return False


class LaserOperation(Node):
    """
    Default object defining any operation done on the laser.

    This is an Node type "op".
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._operation = None
        try:
            self._operation = kwargs["operation"]
        except KeyError:
            self._operation = "Unknown"
        self.color = None
        self.output = True
        self.show = True
        self.default = False

        self._status_value = "Queued"
        self.settings = LaserSettings(*args, **kwargs)

        try:
            self.color = Color(kwargs["color"])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.output = bool(kwargs["output"])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.show = bool(kwargs["show"])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.default = bool(kwargs["default"])
        except (ValueError, TypeError, KeyError):
            pass

        if len(args) == 1:
            obj = args[0]
            if isinstance(obj, SVGElement):
                self.add(obj, type="opnode")
            elif isinstance(obj, LaserOperation):
                self._operation = obj.operation
                self.color = Color(obj.color)
                self.output = obj.output
                self.show = obj.show
                self.default = obj.default
                self.settings = LaserSettings(obj.settings)

        if self.operation == "Cut":
            if self.settings.speed is None:
                self.settings.speed = 10.0
            if self.settings.power is None:
                self.settings.power = 1000.0
            if self.color is None:
                self.color = Color("red")
        elif self.operation == "Engrave":
            if self.settings.speed is None:
                self.settings.speed = 35.0
            if self.settings.power is None:
                self.settings.power = 1000.0
            if self.color is None:
                self.color = Color("blue")
        elif self.operation == "Raster":
            if self.settings.raster_step == 0:
                self.settings.raster_step = 2
            if self.settings.speed is None:
                self.settings.speed = 150.0
            if self.settings.power is None:
                self.settings.power = 1000.0
            if self.color is None:
                self.color = Color("black")
        elif self.operation == "Image":
            if self.settings.speed is None:
                self.settings.speed = 150.0
            if self.settings.power is None:
                self.settings.power = 1000.0
            if self.color is None:
                self.color = Color("transparent")
        elif self.operation == "Dots":
            if self.settings.speed is None:
                self.settings.speed = 35.0
            if self.settings.power is None:
                self.settings.power = 1000.0
            if self.color is None:
                self.color = Color("transparent")
        else:
            if self.settings.speed is None:
                self.settings.speed = 10.0
            if self.settings.power is None:
                self.settings.power = 1000.0
            if self.color is None:
                self.color = Color("white")

    def __repr__(self):
        return "LaserOperation('%s', %s)" % (self.type, str(self._operation))

    def __str__(self):
        op = self._operation
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        if (
            (self._operation in ("Raster", "Image") and self.settings.speed > 500)
            or (self._operation in ("Cut", "Engrave") and self.settings.speed > 50)
            or self.settings.power <= 100
        ):
            parts.append("❌")
        if self.default:
            parts.append("✓")
        if self.settings.passes_custom and self.settings.passes != 1:
            parts.append("%dX" % self.settings.passes)
        if op is None:
            op = "Unknown"
        if self._operation == "Raster":
            op += str(self.settings.raster_step)
        parts.append(op)
        if op == "Dots":
            parts.append("%gms dwell" % self.settings.speed)
            return " ".join(parts)
        parts.append("%gmm/s" % self.settings.speed)
        if self._operation in ("Raster", "Image"):
            if self.settings.raster_swing:
                raster_dir = "-"
            else:
                raster_dir = "="
            if self.settings.raster_direction == 0:
                raster_dir += "T2B"
            elif self.settings.raster_direction == 1:
                raster_dir += "B2T"
            elif self.settings.raster_direction == 2:
                raster_dir += "R2L"
            elif self.settings.raster_direction == 3:
                raster_dir += "L2R"
            elif self.settings.raster_direction == 4:
                raster_dir += "X"
            else:
                raster_dir += "%d" % self.settings.raster_direction
            parts.append(raster_dir)
        parts.append("%gppi" % self.settings.power)
        if self._operation in ("Raster", "Image"):
            if isinstance(self.settings.overscan, str):
                parts.append("±%s" % self.settings.overscan)
            else:
                parts.append("±%d" % self.settings.overscan)
        if (
            self.operation in ("Cut", "Engrave", "Raster")
            and not self.default
            and self.color is not None
        ):
            parts.append("%s" % self.color.hex)
        if self.settings.dratio_custom:
            parts.append("d:%g" % self.settings.dratio)
        if self.settings.acceleration_custom:
            parts.append("a:%d" % self.settings.acceleration)
        if self.settings.dot_length_custom:
            parts.append("dot: %d" % self.settings.dot_length)
        return " ".join(parts)

    def __copy__(self):
        return LaserOperation(self)

    def copy_children(self, obj):
        for element in obj.children:
            self.add(element.object, type="opnode")

    def deep_copy_children(self, obj):
        for element in obj.children:
            self.add(copy(element.object), type="elem")

    @property
    def operation(self):
        return self._operation

    @operation.setter
    def operation(self, v):
        if self._operation != v:
            self._operation = v
            self.notify_update()

    def time_estimate(self):
        if self._operation in ("Cut", "Engrave"):
            estimate = 0
            for e in self.children:
                e = e.object
                if isinstance(e, Shape):
                    try:
                        length = e.length(error=1e-2, min_depth=2)
                    except AttributeError:
                        length = 0
                    try:
                        estimate += length / (MILS_IN_MM * self.settings.speed)
                    except ZeroDivisionError:
                        estimate = float("inf")
            hours, remainder = divmod(estimate, 3600)
            minutes, seconds = divmod(remainder, 60)
            return "%s:%s:%s" % (
                int(hours),
                str(int(minutes)).zfill(2),
                str(int(seconds)).zfill(2),
            )
        elif self._operation in ("Raster", "Image"):
            estimate = 0
            for e in self.children:
                e = e.object
                if isinstance(e, SVGImage):
                    try:
                        step = e.raster_step
                    except AttributeError:
                        try:
                            step = int(e.values["raster_step"])
                        except (KeyError, ValueError):
                            step = 1
                    estimate += (e.image_width * e.image_height * step) / (
                        MILS_IN_MM * self.settings.speed
                    )
            hours, remainder = divmod(estimate, 3600)
            minutes, seconds = divmod(remainder, 60)
            return "%s:%s:%s" % (
                int(hours),
                str(int(minutes)).zfill(2),
                str(int(seconds)).zfill(2),
            )
        return "Unknown"

    def generate(self):
        if self.operation == "Dots":
            yield COMMAND_MODE_RAPID
            yield COMMAND_SET_ABSOLUTE
            for path_node in self.children:
                try:
                    obj = abs(path_node.object)
                    first = obj.point(0)
                except (IndexError, AttributeError):
                    continue
                if first is None:
                    continue
                yield COMMAND_MOVE, first[0], first[1]
                yield COMMAND_WAIT, 4.000  # I don't know how long the move will take to finish.
                yield COMMAND_WAIT_FINISH
                yield COMMAND_LASER_ON  # This can't be sent early since these are timed operations.
                yield COMMAND_WAIT, (self.settings.speed / 1000.0)
                yield COMMAND_LASER_OFF

    def as_cutobjects(self, closed_distance=15, passes=1):
        """
        Generator of cutobjects for a particular operation.
        """
        settings = self.settings

        if self._operation in ("Cut", "Engrave"):
            for element in self.children:
                object_path = element.object
                if isinstance(object_path, SVGImage):
                    box = object_path.bbox()
                    path = Path(
                        Polygon(
                            (box[0], box[1]),
                            (box[0], box[3]),
                            (box[2], box[3]),
                            (box[2], box[1]),
                        )
                    )
                else:
                    # Is a shape or path.
                    if not isinstance(object_path, Path):
                        path = abs(Path(object_path))
                    else:
                        path = abs(object_path)
                    path.approximate_arcs_with_cubics()
                settings.line_color = path.stroke
                for subpath in path.as_subpaths():
                    sp = Path(subpath)
                    if len(sp) == 0:
                        continue
                    closed = (
                        isinstance(sp[-1], Close)
                        or abs(sp.z_point - sp.current_point) <= closed_distance
                    )
                    group = CutGroup(
                        None,
                        closed=closed,
                        settings=settings,
                        passes=passes,
                    )
                    group.path = sp
                    group.original_op = self._operation
                    for seg in subpath:
                        if isinstance(seg, Move):
                            pass  # Move operations are ignored.
                        elif isinstance(seg, Close):
                            if seg.start != seg.end:
                                group.append(
                                    LineCut(
                                        seg.start,
                                        seg.end,
                                        settings=settings,
                                    )
                                )
                        elif isinstance(seg, Line):
                            if seg.start != seg.end:
                                group.append(
                                    LineCut(
                                        seg.start,
                                        seg.end,
                                        settings=settings,
                                    )
                                )
                        elif isinstance(seg, QuadraticBezier):
                            group.append(
                                QuadCut(
                                    seg.start,
                                    seg.control,
                                    seg.end,
                                    settings=settings,
                                )
                            )
                        elif isinstance(seg, CubicBezier):
                            group.append(
                                CubicCut(
                                    seg.start,
                                    seg.control1,
                                    seg.control2,
                                    seg.end,
                                    settings=settings,
                                )
                            )
                    if len(group) > 0:
                        group[0].first = True
                    for i, cut_obj in enumerate(group):
                        cut_obj.closed = closed
                        cut_obj.passes = passes
                        cut_obj.parent = group
                        try:
                            cut_obj.next = group[i + 1]
                        except IndexError:
                            cut_obj.last = True
                            cut_obj.next = group[0]
                        cut_obj.previous = group[i - 1]
                    yield group
        elif self._operation == "Raster":
            # By the time as_cutobject has been called, the elements in raster operations
            # have already been converted to images.
            step = settings.raster_step
            assert step > 0
            direction = settings.raster_direction
            for element in self.children:
                svg_image = element.object
                if not isinstance(svg_image, SVGImage):
                    continue

                matrix = svg_image.transform
                pil_image = svg_image.image
                pil_image, matrix = actualize(pil_image, matrix, step)
                box = (
                    matrix.value_trans_x(),
                    matrix.value_trans_y(),
                    matrix.value_trans_x() + pil_image.width * step,
                    matrix.value_trans_y() + pil_image.height * step,
                )
                path = Path(
                    Polygon(
                        (box[0], box[1]),
                        (box[0], box[3]),
                        (box[2], box[3]),
                        (box[2], box[1]),
                    )
                )
                cut = RasterCut(
                    pil_image,
                    matrix.value_trans_x(),
                    matrix.value_trans_y(),
                    settings=settings,
                    passes=passes,
                )
                cut.path = path
                cut.original_op = self._operation
                yield cut
                if direction == 4:
                    cut = RasterCut(
                        pil_image,
                        matrix.value_trans_x(),
                        matrix.value_trans_y(),
                        crosshatch=True,
                        settings=settings,
                        passes=passes,
                    )
                    cut.path = path
                    cut.original_op = self._operation
                    yield cut
        elif self._operation == "Image":
            for svg_image in self.children:
                svg_image = svg_image.object
                if not isinstance(svg_image, SVGImage):
                    continue
                settings = LaserSettings(self.settings)
                try:
                    settings.raster_step = int(svg_image.values["raster_step"])
                except KeyError:
                    # This overwrites any step that may have been defined in settings.
                    settings.raster_step = (
                        1  # If raster_step is not set image defaults to 1.
                    )
                if settings.raster_step <= 0:
                    settings.raster_step = 1
                try:
                    settings.raster_direction = int(
                        svg_image.values["raster_direction"]
                    )
                except KeyError:
                    pass
                step = settings.raster_step
                matrix = svg_image.transform
                pil_image = svg_image.image
                pil_image, matrix = actualize(pil_image, matrix, step)
                box = (
                    matrix.value_trans_x(),
                    matrix.value_trans_y(),
                    matrix.value_trans_x() + pil_image.width * step,
                    matrix.value_trans_y() + pil_image.height * step,
                )
                path = Path(
                    Polygon(
                        (box[0], box[1]),
                        (box[0], box[3]),
                        (box[2], box[3]),
                        (box[2], box[1]),
                    )
                )
                cut = RasterCut(
                    pil_image,
                    matrix.value_trans_x(),
                    matrix.value_trans_y(),
                    settings=settings,
                    passes=passes,
                )
                cut.path = path
                cut.original_op = self._operation
                yield cut

                if settings.raster_direction == 4:
                    cut = RasterCut(
                        pil_image,
                        matrix.value_trans_x(),
                        matrix.value_trans_y(),
                        crosshatch=True,
                        settings=settings,
                        passes=passes,
                    )
                    cut.path = path
                    cut.original_op = self._operation
                    yield cut


class CutNode(Node):
    """
    Node type "cutcode"
    Cutcode nodes store cutcode within the tree. When processing in a plan this should be converted to a normal cutcode
    object.
    """

    def __init__(self, data_object, **kwargs):
        super().__init__(data_object, type="cutcode", **kwargs)
        self.output = True
        self.operation = "Cutcode"

    def __repr__(self):
        return "CutNode('%s', %s, %s)" % (
            self.type,
            str(self.object),
            str(self._parent),
        )

    def __copy__(self):
        return CutNode(self.object)

    def __len__(self):
        return 1

    def as_cutobjects(self, closed_distance=15):
        yield from self.object


class ConsoleOperation(Node):
    """
    ConsoleOperation contains a console command (as a string) to be run.

    NOTE: This will eventually replace ConsoleOperation.

    Node type "consoleop"
    """

    def __init__(self, command, **kwargs):
        super().__init__(type="consoleop")
        self.command = command
        self.output = True
        self.operation = "Console"

    def set_command(self, command):
        self.command = command
        self.label = command

    def __repr__(self):
        return "ConsoleOperation('%s', '%s')" % (self.command)

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        parts.append(self.command)
        return " ".join(parts)

    def __copy__(self):
        return ConsoleOperation(self.command)

    def __len__(self):
        return 1

    def generate(self):
        command = self.command
        if not command.endswith("\n"):
            command += "\n"
        yield (COMMAND_CONSOLE, command)


class CommandOperation(Node):
    """
    CommandOperation is a basic command operation. It contains nothing except a single command to be executed.

    Node type "cmdop"
    """

    def __init__(self, name, command, *args, **kwargs):
        super().__init__(type="cmdop")
        self.label = self.name = name
        self.command = command
        self.args = args
        self.output = True
        self.operation = "Command"

    def __repr__(self):
        return "CommandOperation('%s', '%s')" % (self.label, str(self.command))

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        parts.append(self.name)
        return " ".join(parts)

    def __copy__(self):
        return CommandOperation(self.label, self.command, *self.args)

    def __len__(self):
        return 1

    def generate(self):
        yield (self.command,) + self.args


class LaserCodeNode(Node):
    """
    LaserCode is basic command operations. It contains nothing except a list of commands to be executed.

    Node type "lasercode"
    """

    def __init__(self, commands, **kwargs):
        super().__init__(commands, type="lasercode")
        if "name" in kwargs:
            self.name = kwargs["name"]
        else:
            self.name = "LaserCode"
        self.commands = commands
        self.output = True
        self.operation = "LaserCode"

    def __repr__(self):
        return "LaserCode('%s', '%s')" % (self.name, str(self.commands))

    def __str__(self):
        return "LaserCode: %s, %s commands" % (self.name, str(len(self.commands)))

    def __copy__(self):
        return LaserCodeNode(self.commands, name=self.name)

    def __len__(self):
        return len(self.commands)

    def generate(self):
        for cmd in self.commands:
            yield cmd


class RootNode(Node):
    """
    RootNode is one of the few directly declarable node-types and serves as the base type for all Node classes.

    The notifications are shallow. They refer *only* to the node in question, not to any children or parents.
    """

    def __init__(self, context):
        _ = context._
        super().__init__(None)
        self._root = self
        self.set_label("Project")
        self.type = "root"
        self.context = context
        self.listeners = []

        self.elements = context.elements
        self.bootstrap = {
            "op": LaserOperation,
            "cmdop": CommandOperation,
            "consoleop": ConsoleOperation,
            "lasercode": LaserCodeNode,
            "group": GroupNode,
            "elem": ElemNode,
            "opnode": OpNode,
            "cutcode": CutNode,
        }
        self.add(type="branch ops", label=_("Operations"))
        self.add(type="branch elems", label=_("Elements"))

    def __repr__(self):
        return "RootNode(%s)" % (str(self.context))

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
        Notifies any listeners that a value in the tree has had it's underlying data fundamentally changed and while
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


class Elemental(Modifier):
    """
    The elemental module is governs all the interactions with the various elements,
    operations, and filenodes. Handling structure change and selection, emphasis, and
    highlighting changes. The goal of this module is to make sure that the life cycle
    of the elements is strictly enforced. For example, every element that is removed
    must have had the .cache deleted. And anything selecting an element must propagate
    that information out to inform other interested modules.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)

        self._clipboard = {}
        self._clipboard_default = "0"

        self.note = None
        self._emphasized_bounds = None
        self._emphasized_bounds_dirty = True
        self._tree = None

    def tree_operations_for_node(self, node):
        for m in self.context.match("tree/%s/.*" % node.type):
            func = self.context.registered[m]
            reject = False
            for cond in func.conditionals:
                if not cond(node):
                    reject = True
                    break
            if reject:
                continue
            for cond in func.try_conditionals:
                try:
                    if not cond(node):
                        reject = True
                        break
                except Exception:
                    continue
            if reject:
                continue
            func_dict = {
                "name": label_truncate_re.sub("", str(node.label)),
                "label": str(node.label),
            }

            iterator = func.values
            if iterator is None:
                iterator = [0]
            else:
                try:
                    iterator = list(iterator())
                except TypeError:
                    pass
            for i, value in enumerate(iterator):
                func_dict["iterator"] = i
                func_dict["value"] = value
                try:
                    func_dict[func.value_name] = value
                except AttributeError:
                    pass

                for calc in func.calcs:
                    key, c = calc
                    value = c(value)
                    func_dict[key] = value
                if func.radio is not None:
                    try:
                        func.radio_state = func.radio(node, **func_dict)
                    except:
                        func.radio_state = False
                else:
                    func.radio_state = None
                name = func.name.format_map(func_dict)
                func.func_dict = func_dict
                func.real_name = name

                yield func

    def flat(self, **kwargs):
        yield from self._tree.flat(**kwargs)

    @staticmethod
    def tree_calc(value_name, calc_func):
        def decor(func):
            func.calcs.append((value_name, calc_func))
            return func

        return decor

    @staticmethod
    def tree_values(value_name, values):
        def decor(func):
            func.value_name = value_name
            func.values = values
            return func

        return decor

    @staticmethod
    def tree_iterate(value_name, start, stop, step=1):
        def decor(func):
            func.value_name = value_name
            func.values = range(start, stop, step)
            return func

        return decor

    @staticmethod
    def tree_radio(radio_function):
        def decor(func):
            func.radio = radio_function
            return func

        return decor

    @staticmethod
    def tree_submenu(submenu):
        def decor(func):
            func.submenu = submenu
            return func

        return decor

    @staticmethod
    def tree_conditional(conditional):
        def decor(func):
            func.conditionals.append(conditional)
            return func

        return decor

    @staticmethod
    def tree_conditional_try(conditional):
        def decor(func):
            func.try_conditionals.append(conditional)
            return func

        return decor

    @staticmethod
    def tree_reference(node):
        def decor(func):
            func.reference = node
            return func

        return decor

    @staticmethod
    def tree_separator_after():
        def decor(func):
            func.separate_after = True
            return func

        return decor

    @staticmethod
    def tree_separator_before():
        def decor(func):
            func.separate_before = True
            return func

        return decor

    def tree_operation(self, name, node_type=None, help="", **kwargs):
        def decorator(func):
            @functools.wraps(func)
            def inner(node, **ik):
                returned = func(node, **ik, **kwargs)
                return returned

            kernel = self.context.kernel
            if isinstance(node_type, tuple):
                ins = node_type
            else:
                ins = (node_type,)

            # inner.long_help = func.__doc__
            inner.help = help
            inner.node_type = ins
            inner.name = name
            inner.radio = None
            inner.submenu = None
            inner.reference = None
            inner.separate_after = False
            inner.separate_before = False
            inner.conditionals = list()
            inner.try_conditionals = list()
            inner.calcs = list()
            inner.values = [0]
            registered_name = inner.__name__

            for _in in ins:
                p = "tree/%s/%s" % (_in, registered_name)
                if p in kernel.registered:
                    raise NameError(
                        "A function of this name was already registered: %s" % p
                    )
                kernel.register(p, inner)
            return inner

        return decorator

    def attach(self, *a, **kwargs):
        context = self.context
        _ = context._
        context.elements = self
        context.classify = self.classify
        context.save = self.save
        context.save_types = self.save_types
        context.load = self.load
        context.load_types = self.load_types
        context = self.context
        self._tree = RootNode(context)
        bed_dim = context.root
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)
        context.root.setting(bool, "classify_reverse", False)
        context.root.setting(bool, "legacy_classification", False)

        # ==========
        # OPERATION BASE
        # ==========
        @context.console_command(
            "operations", help=_("Show information about operations")
        )
        def element(**kwargs):
            context(".operation* list\n")

        @context.console_command(
            "operation.*", help=_("operation.*: selected operations"), output_type="ops"
        )
        def operation(**kwargs):
            return "ops", list(self.ops(emphasized=True))

        @context.console_command(
            "operation*", help=_("operation*: all operations"), output_type="ops"
        )
        def operation(**kwargs):
            return "ops", list(self.ops())

        @context.console_command(
            "operation~",
            help=_("operation~: non selected operations."),
            output_type="ops",
        )
        def operation(**kwargs):
            return "ops", list(self.ops(emphasized=False))

        @context.console_command(
            "operation", help=_("operation: selected operations."), output_type="ops"
        )
        def operation(**kwargs):
            return "ops", list(self.ops(emphasized=True))

        @context.console_command(
            r"operation([0-9]+,?)+",
            help=_("operation0,2: operation #0 and #2"),
            regex=True,
            output_type="ops",
        )
        def operation(command, channel, _, **kwargs):
            arg = command[9:]
            op_values = []
            for value in arg.split(","):
                try:
                    value = int(value)
                except ValueError:
                    continue
                try:
                    op = self.get_op(value)
                    op_values.append(op)
                except IndexError:
                    channel(_("index %d out of range") % value)
            return "ops", op_values

        # ==========
        # OPERATION SUBCOMMANDS
        # ==========

        @context.console_argument("name", help=_("Name to save the operation under"))
        @context.console_command(
            "save",
            help=_("Save current operations to persistent settings"),
            input_type="ops",
            output_type="ops",
        )
        def save_operations(command, channel, _, data=None, name=None, **kwargs):
            if name is None:
                raise SyntaxError
            if "/" in name:
                raise SyntaxError
            self.save_persistent_operations(name)
            return "ops", list(self.ops())

        @context.console_argument("name", help=_("Name to load the operation from"))
        @context.console_command(
            "load",
            help=_("Load operations from persistent settings"),
            input_type="ops",
            output_type="ops",
        )
        def load_operations(name=None, **kwargs):
            if name is None:
                raise SyntaxError
            if "/" in name:
                raise SyntaxError
            self.load_persistent_operations(name)
            return "ops", list(self.ops())

        @context.console_command(
            "select",
            help=_("Set these values as the selection."),
            input_type="ops",
            output_type="ops",
        )
        def operation_select(data=None, **kwargs):
            self.set_emphasis(data)
            return "ops", data

        @context.console_command(
            "select+",
            help=_("Add the input to the selection"),
            input_type="ops",
            output_type="ops",
        )
        def operation_select_plus(data=None, **kwargs):
            ops = list(self.ops(emphasized=True))
            ops.extend(data)
            self.set_emphasis(ops)
            return "ops", ops

        @context.console_command(
            "select-",
            help=_("Remove the input data from the selection"),
            input_type="ops",
            output_type="ops",
        )
        def operation_select_minus(data=None, **kwargs):
            ops = list(self.ops(emphasized=True))
            for e in data:
                try:
                    ops.remove(e)
                except ValueError:
                    pass
            self.set_emphasis(ops)
            return "ops", ops

        @context.console_command(
            "select^",
            help=_("Toggle the input data in the selection"),
            input_type="ops",
            output_type="ops",
        )
        def operation_select_xor(data=None, **kwargs):
            ops = list(self.ops(emphasized=True))
            for e in data:
                try:
                    ops.remove(e)
                except ValueError:
                    ops.append(e)
            self.set_emphasis(ops)
            return "ops", ops

        @context.console_argument("start", type=int, help=_("operation start"))
        @context.console_argument("end", type=int, help=_("operation end"))
        @context.console_argument("step", type=int, help=_("operation step"))
        @context.console_command(
            "range",
            help=_("Subset existing selection by begin and end indices and step"),
            input_type="ops",
            output_type="ops",
        )
        def operation_select_range(data=None, start=None, end=None, step=1, **kwargs):
            subops = list()
            for e in range(start, end, step):
                try:
                    subops.append(data[e])
                except IndexError:
                    pass
            self.set_emphasis(subops)
            return "ops", subops

        @context.console_argument("filter", type=str, help=_("Filter to apply"))
        @context.console_command(
            "filter",
            help=_("Filter data by given value"),
            input_type="ops",
            output_type="ops",
        )
        def operation_filter(channel=None, data=None, filter=None, **kwargs):
            """
            Apply a filter string to a filter particular operations from the current data.
            Operations are evaluated in an infix prioritized stack format without spaces.
            Qualified values are speed, power, step, acceleration, passes, color, op, overscan, len
            Valid operators are >, >=, <, <=, =, ==, +, -, *, /, &, &&, |, and ||
            eg. filter speed>=10, filter speed=5+5, filter speed>power/10, filter speed==2*4+2
            eg. filter engrave=op&speed=35|cut=op&speed=10
            eg. filter len=0
            """
            subops = list()
            _filter_parse = [
                ("SKIP", r"[ ,\t\n\x09\x0A\x0C\x0D]+"),
                ("OP20", r"(\*|/)"),
                ("OP15", r"(\+|-)"),
                ("OP11", r"(<=|>=|==|!=)"),
                ("OP10", r"(<|>|=)"),
                ("OP5", r"(&&)"),
                ("OP4", r"(&)"),
                ("OP3", r"(\|\|)"),
                ("OP2", r"(\|)"),
                ("NUM", r"([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)"),
                (
                    "COLOR",
                    r"(#[0123456789abcdefABCDEF]{6}|#[0123456789abcdefABCDEF]{3})",
                ),
                (
                    "TYPE",
                    r"(raster|image|cut|engrave|dots|unknown|command|cutcode|lasercode)",
                ),
                (
                    "VAL",
                    r"(speed|power|step|acceleration|passes|color|op|overscan|len)",
                ),
            ]
            filter_re = re.compile(
                "|".join("(?P<%s>%s)" % pair for pair in _filter_parse)
            )
            operator = list()
            operand = list()

            def filter_parser(text: str):
                pos = 0
                limit = len(text)
                while pos < limit:
                    match = filter_re.match(text, pos)
                    if match is None:
                        break  # No more matches.
                    kind = match.lastgroup
                    start = pos
                    pos = match.end()
                    if kind == "SKIP":
                        continue
                    value = match.group()
                    yield kind, value, start, pos

            def solve_to(order: int):
                try:
                    while len(operator) and operator[0][0] >= order:
                        _p, op = operator.pop()
                        v2 = operand.pop()
                        v1 = operand.pop()
                        try:
                            if op == "==" or op == "=":
                                operand.append(v1 == v2)
                            elif op == "!=":
                                operand.append(v1 != v2)
                            elif op == ">":
                                operand.append(v1 > v2)
                            elif op == "<":
                                operand.append(v1 < v2)
                            elif op == "<=":
                                operand.append(v1 <= v2)
                            elif op == ">=":
                                operand.append(v1 >= v2)
                            elif op == "&&" or op == "&":
                                operand.append(v1 and v2)
                            elif op == "||" or op == "|":
                                operand.append(v1 or v2)
                            elif op == "*":
                                operand.append(v1 * v2)
                            elif op == "/":
                                operand.append(v1 / v2)
                            elif op == "+":
                                operand.append(v1 + v2)
                            elif op == "-":
                                operand.append(v1 - v2)
                        except TypeError:
                            raise SyntaxError("Cannot evaluate expression")
                        except ZeroDivisionError:
                            operand.append(float("inf"))
                except IndexError:
                    pass

            for e in data:
                for kind, value, start, pos in filter_parser(filter):
                    if kind == "COLOR":
                        operand.append(Color(value))
                    elif kind == "VAL":
                        if value == "step":
                            operand.append(e.settings.raster_step)
                        elif value == "color":
                            operand.append(e.color)
                        elif value == "op":
                            operand.append(e.operation.lower())
                        elif value == "len":
                            operand.append(len(e.children))
                        else:
                            operand.append(getattr(e.settings, value))

                    elif kind == "NUM":
                        operand.append(float(value))
                    elif kind == "TYPE":
                        operand.append(value)
                    elif kind.startswith("OP"):
                        prec = int(kind[2:])
                        solve_to(prec)
                        operator.append((prec, value))
                solve_to(0)
                if len(operand) == 1:
                    if operand.pop():
                        subops.append(e)
                else:
                    raise SyntaxError(_("Filter parse failed"))

            self.set_emphasis(subops)
            return "ops", subops

        @context.console_command(
            "list",
            help=_("Show information about the chained data"),
            input_type="ops",
            output_type="ops",
        )
        def operation_list(channel, _, data=None, **kwargs):
            channel("----------")
            channel(_("Operations:"))
            index_ops = list(self.ops())
            for op_obj in data:
                i = index_ops.index(op_obj)
                select_piece = "*" if op_obj.emphasized else " "
                name = "%s %d: %s" % (select_piece, i, str(op_obj))
                channel(name)
                if isinstance(op_obj, list):
                    for q, oe in enumerate(op_obj):
                        stroke_piece = (
                            "None"
                            if (not hasattr(oe, "stroke") or oe.stroke) is None
                            else oe.stroke.hex
                        )
                        fill_piece = (
                            "None"
                            if (not hasattr(oe, "stroke") or oe.fill) is None
                            else oe.fill.hex
                        )
                        ident_piece = str(oe.id)
                        name = "%s%d: %s-%s s:%s f:%s" % (
                            "".ljust(5),
                            q,
                            str(type(oe).__name__),
                            ident_piece,
                            stroke_piece,
                            fill_piece,
                        )
                        channel(name)
            channel("----------")

        @context.console_option("color", "c", type=Color)
        @context.console_option("default", "d", type=bool)
        @context.console_option("speed", "s", type=float)
        @context.console_option("power", "p", type=float)
        @context.console_option("step", "S", type=int)
        @context.console_option("overscan", "o", type=Length)
        @context.console_option("passes", "x", type=int)
        @context.console_command(
            ("cut", "engrave", "raster", "imageop", "dots"),
            help=_(
                "<cut/engrave/raster/imageop/dots> - group the elements into this operation"
            ),
            input_type=(None, "elements"),
            output_type="ops",
        )
        def makeop(
            command,
            data=None,
            color=None,
            default=None,
            speed=None,
            power=None,
            step=None,
            overscan=None,
            passes=None,
            **kwargs,
        ):
            op = LaserOperation()
            if color is not None:
                op.color = color
            if default is not None:
                op.default = default
            if speed is not None:
                op.settings.speed = speed
            if power is not None:
                op.settings.power = power
            if passes is not None:
                op.settings.passes_custom = True
                op.settings.passes = passes
            if step is not None:
                op.settings.raster_step = step
            if overscan is not None:
                op.settings.overscan = int(
                    overscan.value(
                        ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                    )
                )
            if command == "cut":
                op.operation = "Cut"
            elif command == "engrave":
                op.operation = "Engrave"
            elif command == "raster":
                op.operation = "Raster"
            elif command == "imageop":
                op.operation = "Image"
            elif command == "dots":
                op.operation = "Dots"
            self.add_op(op)
            if data is not None:
                for item in data:
                    op.add(item, type="opnode")
            return "ops", [op]

        @context.console_argument("step_size", type=int, help=_("raster step size"))
        @context.console_command(
            "step", help=_("step <raster-step-size>"), input_type="ops"
        )
        def op_step(command, channel, _, data, step_size=None, **kwrgs):
            if step_size is None:
                found = False
                for op in data:
                    if op.operation in ("Raster", "Image"):
                        step = op.settings.raster_step
                        channel(_("Step for %s is currently: %d") % (str(op), step))
                        found = True
                if not found:
                    channel(_("No raster operations selected."))
                return
            for op in data:
                if op.operation in ("Raster", "Image"):
                    op.settings.raster_step = step_size
                    op.notify_update()
            return "ops", data

        @context.console_option(
            "difference",
            "d",
            type=bool,
            action="store_true",
            help=_("Change speed by this amount."),
        )
        @context.console_argument("speed", type=str, help=_("operation speed in mm/s"))
        @context.console_command(
            "speed", help=_("speed <speed>"), input_type="ops", output_type="ops"
        )
        def op_speed(
            command, channel, _, speed=None, difference=None, data=None, **kwrgs
        ):
            if speed is None:
                for op in data:
                    old_speed = op.settings.speed
                    channel(_("Speed for '%s' is currently: %f") % (str(op), old_speed))
                return
            if speed.endswith("%"):
                speed = speed[:-1]
                percent = True
            else:
                percent = False

            try:
                new_speed = float(speed)
            except ValueError:
                channel(_("Not a valid speed or percent."))
                return

            for op in data:
                old_speed = op.settings.speed
                if percent and difference:
                    s = old_speed + old_speed * (new_speed / 100.0)
                elif difference:
                    s = old_speed + new_speed
                elif percent:
                    s = old_speed * (new_speed / 100.0)
                else:
                    s = new_speed
                op.settings.speed = s
                channel(
                    _("Speed for '%s' updated %f -> %f")
                    % (str(op), old_speed, new_speed)
                )
                op.notify_update()
            return "ops", data

        @context.console_argument(
            "power", type=int, help=_("power in pulses per inch (ppi, 1000=max)")
        )
        @context.console_command(
            "power", help=_("power <ppi>"), input_type="ops", output_type="ops"
        )
        def op_power(command, channel, _, power=None, data=None, **kwrgs):
            if power is None:
                for op in data:
                    old_ppi = op.settings.power
                    channel(_("Power for '%s' is currently: %d") % (str(op), old_ppi))
                return
            for op in data:
                old_ppi = op.settings.power
                op.settings.power = power
                channel(
                    _("Power for '%s' updated %d -> %d") % (str(op), old_ppi, power)
                )
                op.notify_update()
            return "ops", data

        @context.console_argument("passes", type=int, help=_("Set operation passes"))
        @context.console_command(
            "passes", help=_("passes <passes>"), input_type="ops", output_type="ops"
        )
        def op_passes(command, channel, _, passes=None, data=None, **kwrgs):
            if passes is None:
                for op in data:
                    old_passes = op.settings.passes
                    channel(
                        _("Passes for '%s' is currently: %d") % (str(op), old_passes)
                    )
                return
            for op in data:
                old_passes = op.settings.passes
                op.settings.passes = passes
                if passes >= 1:
                    op.settings.passes_custom = True
                channel(
                    _("Passes for '%s' updated %d -> %d")
                    % (str(op), old_passes, passes)
                )
                op.notify_update()
            return "ops", data

        @context.console_command(
            "disable",
            help=_("Disable the given operations"),
            input_type="ops",
            output_type="ops",
        )
        def op_disable(command, channel, _, data=None, **kwrgs):
            for op in data:
                op.output = False
                channel(_("Operation '%s' disabled.") % str(op))
                op.notify_update()
            return "ops", data

        @context.console_command(
            "enable",
            help=_("Enable the given operations"),
            input_type="ops",
            output_type="ops",
        )
        def op_enable(command, channel, _, data=None, **kwrgs):
            for op in data:
                op.output = True
                channel(_("Operation '%s' enabled.") % str(op))
                op.notify_update()
            return "ops", data

        # ==========
        # ELEMENT/OPERATION SUBCOMMANDS
        # ==========
        @context.console_command(
            "copy",
            help=_("Duplicate elements"),
            input_type=("elements", "ops"),
            output_type=("elements", "ops"),
        )
        def e_copy(data=None, data_type=None, **kwargs):
            add_elem = list(map(copy, data))
            if data_type == "ops":
                self.add_ops(add_elem)
            else:
                self.add_elems(add_elem)
            return data_type, add_elem

        @context.console_command(
            "delete", help=_("Delete elements"), input_type=("elements", "ops")
        )
        def e_delete(command, channel, _, data=None, data_type=None, **kwargs):
            channel(_("Deleting…"))
            if data_type == "elements":
                self.remove_elements(data)
            else:
                self.remove_operations(data)
            self.context.signal("refresh_scene", 0)

        # ==========
        # ELEMENT BASE
        # ==========

        @context.console_command(
            "elements",
            help=_("Show information about elements"),
        )
        def element(**kwargs):
            context(".element* list\n")

        @context.console_command(
            "element*",
            help=_("element*, all elements"),
            output_type="elements",
        )
        def element_star(**kwargs):
            return "elements", list(self.elems())

        @context.console_command(
            "element~",
            help=_("element~, all non-selected elements"),
            output_type="elements",
        )
        def element_not(**kwargs):
            return "elements", list(self.elems(emphasized=False))

        @context.console_command(
            "element",
            help=_("element, selected elements"),
            output_type="elements",
        )
        def element_base(**kwargs):
            return "elements", list(self.elems(emphasized=True))

        @context.console_command(
            r"element([0-9]+,?)+",
            help=_("element0,3,4,5: chain a list of specific elements"),
            regex=True,
            output_type="elements",
        )
        def element_chain(command, channel, _, **kwargs):
            arg = command[7:]
            elements_list = []
            for value in arg.split(","):
                try:
                    value = int(value)
                except ValueError:
                    continue
                try:
                    e = self.get_elem(value)
                    elements_list.append(e)
                except IndexError:
                    channel(_("index %d out of range") % value)
            return "elements", elements_list

        # ==========
        # ELEMENT SUBCOMMANDS
        # ==========

        @context.console_argument("step_size", type=int, help=_("element step size"))
        @context.console_command(
            "step",
            help=_("step <element step-size>"),
            input_type="elements",
            output_type="elements",
        )
        def step_command(command, channel, _, data, step_size=None, **kwrgs):
            if step_size is None:
                found = False
                for element in data:
                    if isinstance(element, SVGImage):
                        try:
                            step = element.values["raster_step"]
                        except KeyError:
                            step = 1
                        channel(
                            _("Image step for %s is currently: %s")
                            % (str(element), step)
                        )
                        found = True
                if not found:
                    channel(_("No image element selected."))
                return
            for element in data:
                element.values["raster_step"] = str(step_size)
                m = element.transform
                tx = m.e
                ty = m.f
                element.transform = Matrix.scale(float(step_size), float(step_size))
                element.transform.post_translate(tx, ty)
                if hasattr(element, "node"):
                    element.node.modified()
                self.context.signal("element_property_reload", element)
                self.context.signal("refresh_scene")
            return ("elements",)

        @context.console_command(
            "select",
            help=_("Set these values as the selection."),
            input_type="elements",
            output_type="elements",
        )
        def element_select_base(data=None, **kwargs):
            self.set_emphasis(data)
            return "elements", data

        @context.console_command(
            "select+",
            help=_("Add the input to the selection"),
            input_type="elements",
            output_type="elements",
        )
        def element_select_plus(data=None, **kwargs):
            elems = list(self.elems(emphasized=True))
            elems.extend(data)
            self.set_emphasis(elems)
            return "elements", elems

        @context.console_command(
            "select-",
            help=_("Remove the input data from the selection"),
            input_type="elements",
            output_type="elements",
        )
        def element_select_minus(data=None, **kwargs):
            elems = list(self.elems(emphasized=True))
            for e in data:
                try:
                    elems.remove(e)
                except ValueError:
                    pass
            self.set_emphasis(elems)
            return "elements", elems

        @context.console_command(
            "select^",
            help=_("Toggle the input data in the selection"),
            input_type="elements",
            output_type="elements",
        )
        def element_select_xor(data=None, **kwargs):
            elems = list(self.elems(emphasized=True))
            for e in data:
                try:
                    elems.remove(e)
                except ValueError:
                    elems.append(e)
            self.set_emphasis(elems)
            return "elements", elems

        @context.console_command(
            "list",
            help=_("Show information about the chained data"),
            input_type="elements",
            output_type="elements",
        )
        def element_list(command, channel, _, data=None, **kwargs):
            channel("----------")
            channel(_("Graphical Elements:"))
            index_list = list(self.elems())
            for e in data:
                i = index_list.index(e)
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                if e.node.emphasized:
                    channel("%d: * %s" % (i, name))
                else:
                    channel("%d: %s" % (i, name))
            channel("----------")
            return "elements", data

        @context.console_argument("start", type=int, help=_("elements start"))
        @context.console_argument("end", type=int, help=_("elements end"))
        @context.console_argument("step", type=int, help=_("elements step"))
        @context.console_command(
            "range",
            help=_("Subset selection by begin & end indices and step"),
            input_type="elements",
            output_type="elements",
        )
        def element_select_range(data=None, start=None, end=None, step=1, **kwargs):
            subelem = list()
            for e in range(start, end, step):
                try:
                    subelem.append(data[e])
                except IndexError:
                    pass
            self.set_emphasis(subelem)
            return "elements", subelem

        @context.console_command(
            "merge",
            help=_("merge elements"),
            input_type="elements",
            output_type="elements",
        )
        def element_merge(data=None, **kwargs):
            super_element = Path()
            for e in data:
                if not isinstance(e, Shape):
                    continue
                if super_element.stroke is None:
                    super_element.stroke = e.stroke
                if super_element.fill is None:
                    super_element.fill = e.fill
                super_element += abs(e)
            self.remove_elements(data)
            self.add_elem(super_element).emphasized = True
            self.classify([super_element])
            return "elements", [super_element]

        @context.console_command(
            "subpath",
            help=_("break elements"),
            input_type="elements",
            output_type="elements",
        )
        def element_subpath(data=None, **kwargs):
            if not isinstance(data, list):
                data = list(data)
            elements_nodes = []
            elements = []
            for e in data:
                node = e.node
                group_node = node.replace_node(type="group", label=node.label)
                if isinstance(e, Shape) and not isinstance(e, Path):
                    e = Path(e)
                elif isinstance(e, SVGText):
                    continue
                p = abs(e)
                for subpath in p.as_subpaths():
                    subelement = Path(subpath)
                    elements.append(subelement)
                    group_node.add(subelement, type="elem")
                elements_nodes.append(group_node)
                self.classify(elements)
            return "elements", elements_nodes

        # ==========
        # ALIGN SUBTYPE
        # Align consist of top level node objects that can be manipulated within the scene.
        # ==========

        @context.console_command(
            "align",
            help=_("align selected elements"),
            input_type=("elements", None),
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, remainder=None, **kwargs):
            if not remainder:
                channel(
                    "top\nbottom\nleft\nright\ncenter\ncenterh\ncenterv\nspaceh\nspacev\n"
                    "<any valid svg:Preserve Aspect Ratio, eg xminymin>"
                )
                return
            if data is None:
                data = list(self.elems(emphasized=True))

            # Element conversion.
            d = list()
            elem_branch = self.elem_branch
            for elem in data:
                node = elem.node
                while node.parent and node.parent is not elem_branch:
                    node = node.parent
                if node not in d:
                    d.append(node)
            data = d
            return "align", data

        @context.console_command(
            "top",
            help=_("align elements at top"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            top_edge = min([e[1] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                top = subbox[1] - top_edge
                matrix = "translate(0, %f)" % -top
                if top != 0:
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
            return "align", data

        @context.console_command(
            "bottom",
            help=_("align elements at bottom"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            bottom_edge = max([e[3] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                bottom = subbox[3] - bottom_edge
                matrix = "translate(0, %f)" % -bottom
                if bottom != 0:
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
            return "align", data

        @context.console_command(
            "left",
            help=_("align elements at left"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            left_edge = min([e[0] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                left = subbox[0] - left_edge
                matrix = "translate(%f, 0)" % -left
                if left != 0:
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
            return "align", data

        @context.console_command(
            "right",
            help=_("align elements at right"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            right_edge = max([e[2] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                right = subbox[2] - right_edge
                matrix = "translate(%f, 0)" % -right
                if right != 0:
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
            return "align", data

        @context.console_command(
            "center",
            help=_("align elements at center"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            left_edge = min([e[0] for e in boundary_points])
            top_edge = min([e[1] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                dx = (subbox[0] + subbox[2] - left_edge - right_edge) / 2.0
                dy = (subbox[1] + subbox[3] - top_edge - bottom_edge) / 2.0
                matrix = "translate(%f, %f)" % (-dx, -dy)
                for q in node.flat(types="elem"):
                    obj = q.object
                    if obj is not None:
                        obj *= matrix
                    q.modified()
            return "align", data

        @context.console_command(
            "centerv",
            help=_("align elements at center vertical"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            left_edge = min([e[0] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                dx = (subbox[0] + subbox[2] - left_edge - right_edge) / 2.0
                matrix = "translate(%f, 0)" % -dx
                for q in node.flat(types="elem"):
                    obj = q.object
                    if obj is not None:
                        obj *= matrix
                    q.modified()
            return "align", data

        @context.console_command(
            "centerh",
            help=_("align elements at center horizontal"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            top_edge = min([e[1] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                dy = (subbox[1] + subbox[3] - top_edge - bottom_edge) / 2.0
                matrix = "translate(0, %f)" % -dy
                for q in node.flat(types="elem"):
                    obj = q.object
                    if obj is not None:
                        obj *= matrix
                    q.modified()
            return "align", data

        @context.console_command(
            "spaceh",
            help=_("align elements across horizontal space"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            if len(data) <= 2:  # Cannot distribute 2 or fewer items.
                return "align", data
            left_edge = min([e[0] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            dim_total = right_edge - left_edge
            dim_available = dim_total
            for node in data:
                bounds = node.bounds
                dim_available -= bounds[2] - bounds[0]
            distributed_distance = dim_available / (len(data) - 1)
            data.sort(key=lambda n: n.bounds[0])  # sort by left edge
            dim_pos = left_edge
            for node in data:
                subbox = node.bounds
                delta = subbox[0] - dim_pos
                matrix = "translate(%f, 0)" % -delta
                if delta != 0:
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
                dim_pos += subbox[2] - subbox[0] + distributed_distance
            return "align", data

        @context.console_command(
            "spacev",
            help=_("align elements down vertical space"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            if len(data) <= 2:  # Cannot distribute 2 or fewer items.
                return "align", data
            top_edge = min([e[1] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])
            dim_total = bottom_edge - top_edge
            dim_available = dim_total
            for node in data:
                bounds = node.bounds
                dim_available -= bounds[3] - bounds[1]
            distributed_distance = dim_available / (len(data) - 1)
            data.sort(key=lambda n: n.bounds[1])  # sort by top edge
            dim_pos = top_edge
            for node in data:
                subbox = node.bounds
                delta = subbox[1] - dim_pos
                matrix = "translate(0, %f)" % -delta
                if delta != 0:
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
                dim_pos += subbox[3] - subbox[1] + distributed_distance
            return "align", data

        @context.console_command(
            "bedcenter",
            help=_("align elements to bedcenter"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            left_edge = min([e[0] for e in boundary_points])
            top_edge = min([e[1] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])
            for node in data:
                bw = bed_dim.bed_width
                bh = bed_dim.bed_height
                dx = (bw * MILS_IN_MM - left_edge - right_edge) / 2.0
                dy = (bh * MILS_IN_MM - top_edge - bottom_edge) / 2.0
                matrix = "translate(%f, %f)" % (dx, dy)
                for q in node.flat(types="elem"):
                    obj = q.object
                    if obj is not None:
                        obj *= matrix
                    q.modified()
            self.context.signal("refresh_scene")
            return "align", data

        @context.console_argument(
            "preserve_aspect_ratio",
            type=str,
            default="none",
            help="preserve aspect ratio value",
        )
        @context.console_command(
            "view",
            help=_("align elements within viewbox"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(
            command, channel, _, data=None, preserve_aspect_ratio="none", **kwargs
        ):
            """
            Align the elements to within the bed according to SVG Viewbox rules. The following aspect ratios
            are valid. These should define all the valid methods of centering data within the laser bed.
            "xminymin",
            "xmidymin",
            "xmaxymin",
            "xminymid",
            "xmidymid",
            "xmaxymid",
            "xminymax",
            "xmidymax",
            "xmaxymax",
            "xminymin meet",
            "xmidymin meet",
            "xmaxymin meet",
            "xminymid meet",
            "xmidymid meet",
            "xmaxymid meet",
            "xminymax meet",
            "xmidymax meet",
            "xmaxymax meet",
            "xminymin slice",
            "xmidymin slice",
            "xmaxymin slice",
            "xminymid slice",
            "xmidymid slice",
            "xmaxymid slice",
            "xminymax slice",
            "xmidymax slice",
            "xmaxymax slice",
            "none"
            """

            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            left_edge = min([e[0] for e in boundary_points])
            top_edge = min([e[1] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])

            if preserve_aspect_ratio in (
                "xminymin",
                "xmidymin",
                "xmaxymin",
                "xminymid",
                "xmidymid",
                "xmaxymid",
                "xminymax",
                "xmidymax",
                "xmaxymax",
                "xminymin meet",
                "xmidymin meet",
                "xmaxymin meet",
                "xminymid meet",
                "xmidymid meet",
                "xmaxymid meet",
                "xminymax meet",
                "xmidymax meet",
                "xmaxymax meet",
                "xminymin slice",
                "xmidymin slice",
                "xmaxymin slice",
                "xminymid slice",
                "xmidymid slice",
                "xmaxymid slice",
                "xminymax slice",
                "xmidymax slice",
                "xmaxymax slice",
                "none",
            ):
                for node in data:
                    bw = bed_dim.bed_width
                    bh = bed_dim.bed_height

                    matrix = Viewbox.viewbox_transform(
                        0,
                        0,
                        bw * MILS_IN_MM,
                        bh * MILS_IN_MM,
                        left_edge,
                        top_edge,
                        right_edge - left_edge,
                        bottom_edge - top_edge,
                        preserve_aspect_ratio,
                    )
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
                    for q in node.flat(types=("file", "group")):
                        q.modified()
                self.context.signal("refresh_scene")
            return "align", data

        @context.console_argument("c", type=int, help=_("Number of columns"))
        @context.console_argument("r", type=int, help=_("Number of rows"))
        @context.console_argument("x", type=Length, help=_("x distance"))
        @context.console_argument("y", type=Length, help=_("y distance"))
        @context.console_option(
            "origin",
            "o",
            type=int,
            nargs=2,
            help=_("Position of original in matrix (e.g '2,2' or '4,3')"),
        )
        @context.console_command(
            "grid",
            help=_("grid <columns> <rows> <x_distance> <y_distance> <origin>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_grid(
            command,
            channel,
            _,
            c: int,
            r: int,
            x: Length,
            y: Length,
            origin=None,
            data=None,
            **kwargs,
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0 and self._emphasized_bounds is None:
                channel(_("No item selected."))
                return
            if r is None:
                raise SyntaxError
            if x is None:
                x = Length("100%")
            else:
                if not x.is_valid_length:
                    raise SyntaxError("x: " + _("This is not a valid length"))
            if y is None:
                y = Length("100%")
            else:
                if not y.is_valid_length:
                    raise SyntaxError("y: " + _("This is not a valid length"))

            try:
                bounds = self._emphasized_bounds
                width = bounds[2] - bounds[0]
                height = bounds[3] - bounds[1]
            except Exception:
                raise SyntaxError
            x = x.value(ppi=1000, relative_length=width)
            y = y.value(ppi=1000, relative_length=height)
            if isinstance(x, Length) or isinstance(y, Length):
                raise SyntaxError
            if origin is None:
                origin = (1, 1)
            cx, cy = origin
            data_out = list(data)
            if cx is None:
                cx = 1
            if cy is None:
                cy = 1
            # Tell whether original is at the left / middle / or right
            start_x = -1 * x * (cx - 1)
            start_y = -1 * y * (cy - 1)
            y_pos = start_y
            for j in range(r):
                x_pos = start_x
                for k in range(c):
                    if j != (cy - 1) or k != (cx - 1):
                        add_elem = list(map(copy, data))
                        for e in add_elem:
                            e *= "translate(%f, %f)" % (x_pos, y_pos)
                        self.add_elems(add_elem)
                        data_out.extend(add_elem)
                    x_pos += x
                y_pos += y

            self.context.signal("refresh_scene")
            return "elements", data_out

        @context.console_argument("repeats", type=int, help=_("Number of repeats"))
        @context.console_argument("radius", type=Length, help=_("Radius"))
        @context.console_argument("startangle", type=Angle.parse, help=_("Start-Angle"))
        @context.console_argument("endangle", type=Angle.parse, help=_("End-Angle"))
        @context.console_option(
            "rotate",
            "r",
            type=bool,
            action="store_true",
            help=_("Rotate copies towards center?"),
        )
        @context.console_option(
            "deltaangle",
            "d",
            type=Angle.parse,
            help=_("Delta-Angle (if omitted will take (end-start)/repeats )"),
        )
        @context.console_command(
            "radial",
            help=_("radial <repeats> <radius> <startangle> <endangle> <rotate>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_radial(
            command,
            channel,
            _,
            repeats: int,
            radius=None,
            startangle=None,
            endangle=None,
            rotate=None,
            deltaangle=None,
            data=None,
            **kwargs,
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0 and self._emphasized_bounds is None:
                channel(_("No item selected."))
                return

            if repeats is None:
                raise SyntaxError
            if repeats <= 1:
                raise SyntaxError(_("repeats should be greater or equal to 2"))
            if radius is None:
                radius = Length(0)
            else:
                if not radius.is_valid_length:
                    raise SyntaxError("radius: " + _("This is not a valid length"))
            if startangle is None:
                startangle = Angle.parse("0deg")
            if endangle is None:
                endangle = Angle.parse("360deg")
            if rotate is None:
                rotate = False

            # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
            bounds = Group.union_bbox(data, with_stroke=True)
            if bounds is None:
                return
            width = bounds[2] - bounds[0]
            radius = radius.value(ppi=1000, relative_length=width)
            if isinstance(radius, Length):
                raise SyntaxError

            data_out = list(data)
            if deltaangle is None:
                segment_len = (endangle.as_radians - startangle.as_radians) / repeats
            else:
                segment_len = deltaangle.as_radians
            # Notabene: we are following the cartesian system here, but as the Y-Axis is top screen to bottom screen,
            # the perceived angle travel is CCW (which is counter-intuitive)
            currentangle = startangle.as_radians
            # bounds = self._emphasized_bounds
            center_x = (bounds[2] + bounds[0]) / 2.0 - radius
            center_y = (bounds[3] + bounds[1]) / 2.0

            # print ("repeats: %d, Radius: %.1f" % (repeats, radius))
            # print ("Center: %.1f, %.1f" % (center_x, center_y))
            # print ("Startangle, Endangle, segment_len: %.1f, %.1f, %.1f" % (180 * startangle.as_radians / pi, 180 * endangle.as_radians / pi, 180 * segment_len / pi))

            currentangle = segment_len
            for cc in range(1, repeats):
                # print ("Angle: %f rad = %f deg" % (currentangle, currentangle/pi * 180))
                add_elem = list(map(copy, data))
                for e in add_elem:
                    if rotate:
                        x_pos = -1 * radius
                        y_pos = 0
                        # e *= "translate(%f, %f)" % (x_pos, y_pos)
                        e *= "rotate(%frad, %f, %f)" % (
                            currentangle,
                            center_x,
                            center_y,
                        )
                    else:
                        x_pos = -1 * radius + radius * cos(currentangle)
                        y_pos = radius * sin(currentangle)
                        e *= "translate(%f, %f)" % (x_pos, y_pos)

                self.add_elems(add_elem)
                data_out.extend(add_elem)

                currentangle += segment_len

            self.context.signal("refresh_scene")
            return "elements", data_out

        @context.console_argument("copies", type=int, help=_("Number of copies"))
        @context.console_argument("radius", type=Length, help=_("Radius"))
        @context.console_argument("startangle", type=Angle.parse, help=_("Start-Angle"))
        @context.console_argument("endangle", type=Angle.parse, help=_("End-Angle"))
        @context.console_option(
            "rotate",
            "r",
            type=bool,
            action="store_true",
            help=_("Rotate copies towards center?"),
        )
        @context.console_option(
            "deltaangle",
            "d",
            type=Angle.parse,
            help=_("Delta-Angle (if omitted will take (end-start)/copies )"),
        )
        @context.console_command(
            "circ_copy",
            help=_("circ_copy <copies> <radius> <startangle> <endangle> <rotate>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_circularcopies(
            command,
            channel,
            _,
            copies: int,
            radius=None,
            startangle=None,
            endangle=None,
            rotate=None,
            deltaangle=None,
            data=None,
            **kwargs,
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0 and self._emphasized_bounds is None:
                channel(_("No item selected."))
                return

            if copies is None:
                raise SyntaxError
            if copies <= 0:
                copies = 1
            if radius is None:
                radius = Length(0)
            else:
                if not radius.is_valid_length:
                    raise SyntaxError("radius: " + _("This is not a valid length"))
            if startangle is None:
                startangle = Angle.parse("0deg")
            if endangle is None:
                endangle = Angle.parse("360deg")
            if rotate is None:
                rotate = False

            # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
            bounds = Group.union_bbox(data, with_stroke=True)
            if bounds is None:
                return
            width = bounds[2] - bounds[0]
            radius = radius.value(ppi=1000, relative_length=width)
            if isinstance(radius, Length):
                raise SyntaxError

            data_out = list(data)
            if deltaangle is None:
                segment_len = (endangle.as_radians - startangle.as_radians) / copies
            else:
                segment_len = deltaangle.as_radians
            # Notabene: we are following the cartesian system here, but as the Y-Axis is top screen to bottom screen,
            # the perceived angle travel is CCW (which is counter-intuitive)
            currentangle = startangle.as_radians
            # bounds = self._emphasized_bounds
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            for cc in range(copies):
                # print ("Angle: %f rad = %f deg" % (currentangle, currentangle/pi * 180))
                add_elem = list(map(copy, data))
                for e in add_elem:
                    if rotate:
                        x_pos = radius
                        y_pos = 0
                        e *= "translate(%f, %f)" % (x_pos, y_pos)
                        e *= "rotate(%frad, %f, %f)" % (
                            currentangle,
                            center_x,
                            center_y,
                        )
                    else:
                        x_pos = radius * cos(currentangle)
                        y_pos = radius * sin(currentangle)
                        e *= "translate(%f, %f)" % (x_pos, y_pos)

                self.add_elems(add_elem)
                data_out.extend(add_elem)
                currentangle += segment_len

            self.context.signal("refresh_scene")
            return "elements", data_out

        @context.console_argument(
            "corners", type=int, help=_("Number of corners/vertices")
        )
        @context.console_argument(
            "cx", type=Length, help=_("X-Value of polygon's center")
        )
        @context.console_argument(
            "cy", type=Length, help=_("Y-Value of polygon's center")
        )
        @context.console_argument(
            "radius",
            type=Length,
            help=_("Radius (length of side if --side_length is used)"),
        )
        @context.console_option(
            "startangle", "s", type=Angle.parse, help=_("Start-Angle")
        )
        @context.console_option(
            "inscribed",
            "i",
            type=bool,
            action="store_true",
            help=_("Shall the polygon touch the inscribing circle?"),
        )
        @context.console_option(
            "side_length",
            "l",
            type=bool,
            action="store_true",
            help=_(
                "Do you want to treat the length value for radius as the length of one edge instead?"
            ),
        )
        @context.console_option(
            "radius_inner",
            "r",
            type=Length,
            help=_("Alternating radius for every other vertex"),
        )
        @context.console_option(
            "alternate_seq",
            "a",
            type=int,
            help=_(
                "Length of alternating sequence (1 for starlike figures, >=2 for more gear-like patterns)"
            ),
        )
        @context.console_option(
            "density", "d", type=int, help=_("Amount of vertices to skip")
        )
        @context.console_command(
            "shape",
            help=_(
                "shape <corners> <x> <y> <r> <startangle> <inscribed> or shape <corners> <r>"
            ),
            input_type=("elements", None),
            output_type="elements",
        )
        def element_shape(
            command,
            channel,
            _,
            corners,
            cx,
            cy,
            radius,
            startangle=None,
            inscribed=None,
            side_length=None,
            radius_inner=None,
            alternate_seq=None,
            density=None,
            data=None,
            **kwargs,
        ):
            if corners is None:
                raise SyntaxError
            if corners <= 2:
                if cx is None:
                    cx = Length(0)
                elif not cx.is_valid_length:
                    raise SyntaxError("cx: " + _("This is not a valid length"))
                if cy is None:
                    cy = Length(0)
                elif not cy.is_valid_length:
                    raise SyntaxError("cy: " + _("This is not a valid length"))
                cx = cx.value(ppi=1000, relative_length=bed_dim.bed_width * MILS_IN_MM)
                cy = cy.value(ppi=1000, relative_length=bed_dim.bed_width * MILS_IN_MM)
                if radius is None:
                    radius = Length(0)
                radius = radius.value(
                    ppi=1000, relative_length=bed_dim.bed_width * MILS_IN_MM
                )
                # No need to look at side_length parameter as we are considering the radius value as an edge anyway...
                if startangle is None:
                    startangle = Angle.parse("0deg")

                starpts = [(cx, cy)]
                if corners == 2:
                    starpts += [
                        (
                            cx + cos(startangle.as_radians) * radius,
                            cy + sin(startangle.as_radians) * radius,
                        )
                    ]

            else:
                if cx is None:
                    raise SyntaxError(
                        _(
                            "Please provide at least one additional value (which will act as radius then)"
                        )
                    )
                else:
                    if not cx.is_valid_length:
                        raise SyntaxError("cx: " + _("This is not a valid length"))

                if cy is None:
                    cy = Length(0)
                else:
                    if not cy.is_valid_length:
                        raise SyntaxError("cy: " + _("This is not a valid length"))
                # do we have something like 'polyshape 3 4cm' ? If yes, reassign the parameters
                if radius is None:
                    radius = cx
                    cx = Length(0)
                    cy = Length(0)
                else:
                    if not radius.is_valid_length:
                        raise SyntaxError("radius: " + _("This is not a valid length"))

                cx = cx.value(ppi=1000, relative_length=bed_dim.bed_width * MILS_IN_MM)
                cy = cy.value(ppi=1000, relative_length=bed_dim.bed_width * MILS_IN_MM)
                radius = radius.value(
                    ppi=1000, relative_length=bed_dim.bed_width * MILS_IN_MM
                )

                if (
                    isinstance(radius, Length)
                    or isinstance(cx, Length)
                    or isinstance(cy, Length)
                ):
                    raise SyntaxError

                if startangle is None:
                    startangle = Angle.parse("0deg")

                if alternate_seq is None:
                    if radius_inner is None:
                        alternate_seq = 0
                    else:
                        alternate_seq = 1

                if density is None:
                    density = 1
                if density < 1 or density > corners:
                    density = 1

                # Do we have to consider the radius value as the length of one corner?
                if not side_length is None:
                    # Let's recalculate the radius then...
                    # d_oc = s * csc( pi / n)
                    radius = 0.5 * radius / sin(pi / corners)

                if radius_inner is None:
                    radius_inner = radius
                else:
                    radius_inner = radius_inner.value(ppi=1000, relative_length=radius)
                    if not radius_inner.is_valid_length:
                        raise SyntaxError(
                            "radius_inner: " + _("This is not a valid length")
                        )
                    if isinstance(radius_inner, Length):
                        radius_inner = radius

                if inscribed:
                    if side_length is None:
                        radius = radius / cos(pi / corners)
                    else:
                        channel(
                            _(
                                "You have as well provided the --side_length parameter, this takes precedence, so --inscribed is ignored"
                            )
                        )

                if alternate_seq < 1:
                    radius_inner = radius

                # print("These are your parameters:")
                # print("Vertices: %d, Center: X=%.2f Y=%.2f" % (corners, cx, cy))
                # print("Radius: Outer=%.2f Inner=%.2f" % (radius, radius_inner))
                # print("Inscribe: %s" % inscribed)
                # print(
                #    "Startangle: %.2f, Alternate-Seq: %d"
                #    % (startangle.as_degrees, alternate_seq)
                # )

                pts = []
                myangle = startangle.as_radians
                deltaangle = tau / corners
                ct = 0
                for j in range(corners):
                    if ct < alternate_seq:
                        # print("Outer: Ct=%d, Radius=%.2f, Angle=%.2f" % (ct, radius, 180 * myangle / pi) )
                        thisx = cx + radius * cos(myangle)
                        thisy = cy + radius * sin(myangle)
                    else:
                        # print("Inner: Ct=%d, Radius=%.2f, Angle=%.2f" % (ct, radius_inner, 180 * myangle / pi) )
                        thisx = cx + radius_inner * cos(myangle)
                        thisy = cy + radius_inner * sin(myangle)
                    ct += 1
                    if ct >= 2 * alternate_seq:
                        ct = 0
                    if j == 0:
                        firstx = thisx
                        firsty = thisy
                    myangle += deltaangle
                    pts += [(thisx, thisy)]
                # Close the path
                pts += [(firstx, firsty)]

                starpts = [(pts[0][0], pts[0][1])]
                idx = density
                while idx != 0:
                    starpts += [(pts[idx][0], pts[idx][1])]
                    idx += density
                    if idx >= corners:
                        idx -= corners
                if len(starpts) < corners:
                    ct = 0
                    possible_combinations = ""
                    for i in range(corners - 1):
                        j = i + 2
                        if gcd(j, corners) == 1:
                            if ct % 3 == 0:
                                possible_combinations += "\n shape %d ... -d %d" % (
                                    corners,
                                    j,
                                )
                            else:
                                possible_combinations += ", shape %d ... -d %d " % (
                                    corners,
                                    j,
                                )
                            ct += 1
                    channel(
                        _("Just for info: we have missed %d vertices...")
                        % (corners - len(starpts))
                    )
                    channel(
                        _("To hit all, the density parameters should be e.g. %s")
                        % possible_combinations
                    )

            poly_path = Polygon(starpts)
            self.add_element(poly_path)
            if data is None:
                return "elements", [poly_path]
            else:
                data.append(poly_path)
                return "elements", data

        @context.console_option("step", "s", default=2.0, type=float)
        @context.console_command(
            "render",
            help=_("Convert given elements to a raster image"),
            input_type=(None, "elements"),
            output_type="image",
        )
        def make_raster_image(command, channel, _, step=2.0, data=None, **kwargs):
            context = self.context
            if data is None:
                data = list(self.elems(emphasized=True))
            reverse = context.classify_reverse
            if reverse:
                data = list(reversed(data))
            elements = context.elements
            make_raster = self.context.registered.get("render-op/make_raster")
            if not make_raster:
                channel(_("No renderer is registered to perform render."))
                return
            bounds = Group.union_bbox(data, with_stroke=True)
            if bounds is None:
                return
            if step <= 0:
                step = 1
            xmin, ymin, xmax, ymax = bounds

            image = make_raster(
                [n.node for n in data],
                bounds,
                step=step,
            )
            image_element = SVGImage(image=image)
            image_element.transform.post_scale(step, step)
            image_element.transform.post_translate(xmin, ymin)
            image_element.values["raster_step"] = step
            elements.add_elem(image_element)
            return "image", [image_element]

        # ==========
        # ELEMENT/SHAPE COMMANDS
        # ==========
        @context.console_argument("x_pos", type=Length)
        @context.console_argument("y_pos", type=Length)
        @context.console_argument("r_pos", type=Length)
        @context.console_command(
            "circle",
            help=_("circle <x> <y> <r> or circle <r>"),
            input_type=("elements", None),
            output_type="elements",
        )
        def element_circle(x_pos, y_pos, r_pos, data=None, **kwargs):
            if x_pos is None:
                raise SyntaxError
            else:
                if r_pos is None:
                    r_pos = x_pos
                    x_pos = 0
                    y_pos = 0
            circ = Circle(cx=x_pos, cy=y_pos, r=r_pos)
            circ.render(
                ppi=1000.0,
                width="%fmm" % bed_dim.bed_width,
                height="%fmm" % bed_dim.bed_height,
            )
            self.add_element(circ)
            if data is None:
                return "elements", [circ]
            else:
                data.append(circ)
                return "elements", data

        @context.console_argument("x_pos", type=Length)
        @context.console_argument("y_pos", type=Length)
        @context.console_argument("rx_pos", type=Length)
        @context.console_argument("ry_pos", type=Length)
        @context.console_command(
            "ellipse",
            help=_("ellipse <cx> <cy> <rx> <ry>"),
            input_type=("elements", None),
            output_type="elements",
        )
        def element_ellipse(x_pos, y_pos, rx_pos, ry_pos, data=None, **kwargs):
            if ry_pos is None:
                raise SyntaxError
            ellip = Ellipse(cx=x_pos, cy=y_pos, rx=rx_pos, ry=ry_pos)
            ellip.render(
                ppi=1000.0,
                width="%fmm" % bed_dim.bed_width,
                height="%fmm" % bed_dim.bed_height,
            )
            self.add_element(ellip)
            if data is None:
                return "elements", [ellip]
            else:
                data.append(ellip)
                return "elements", data

        @context.console_argument(
            "x_pos", type=Length, help=_("x position for top left corner of rectangle.")
        )
        @context.console_argument(
            "y_pos", type=Length, help=_("y position for top left corner of rectangle.")
        )
        @context.console_argument(
            "width", type=Length, help=_("width of the rectangle.")
        )
        @context.console_argument(
            "height", type=Length, help=_("height of the rectangle.")
        )
        @context.console_option(
            "rx", "x", type=Length, help=_("rounded rx corner value.")
        )
        @context.console_option(
            "ry", "y", type=Length, help=_("rounded ry corner value.")
        )
        @context.console_command(
            "rect",
            help=_("adds rectangle to scene"),
            input_type=("elements", None),
            output_type="elements",
        )
        def element_rect(
            x_pos, y_pos, width, height, rx=None, ry=None, data=None, **kwargs
        ):
            """
            Draws an svg rectangle with optional rounded corners.
            """
            if x_pos is None:
                raise SyntaxError
            else:
                if not x_pos.is_valid_length:
                    raise SyntaxError("x_pos: " + _("This is not a valid length"))
            if not y_pos is None:
                if not y_pos.is_valid_length:
                    raise SyntaxError("y-pos: " + _("This is not a valid length"))
            if not rx is None:
                if not rx.is_valid_length:
                    raise SyntaxError("rx: " + _("This is not a valid length"))
            if not ry is None:
                if not ry.is_valid_length:
                    raise SyntaxError("ry: " + _("This is not a valid length"))

            rect = Rect(x=x_pos, y=y_pos, width=width, height=height, rx=rx, ry=ry)
            rect.render(
                ppi=1000.0,
                width="%fmm" % bed_dim.bed_width,
                height="%fmm" % bed_dim.bed_height,
            )
            # rect = Path(rect)
            self.add_element(rect)
            if data is None:
                return "elements", [rect]
            else:
                data.append(rect)
                return "elements", data

        @context.console_argument("x0", type=Length, help=_("start x position"))
        @context.console_argument("y0", type=Length, help=_("start y position"))
        @context.console_argument("x1", type=Length, help=_("end x position"))
        @context.console_argument("y1", type=Length, help=_("end y position"))
        @context.console_command(
            "line",
            help=_("adds line to scene"),
            input_type=("elements", None),
            output_type="elements",
        )
        def element_line(command, x0, y0, x1, y1, data=None, **kwargs):
            """
            Draws an svg line in the scene.
            """
            if y1 is None:
                raise SyntaxError
            if not x0 is None:
                if not x0.is_valid_length:
                    raise SyntaxError("x0: " + _("This is not a valid length"))
            if not y0 is None:
                if not y0.is_valid_length:
                    raise SyntaxError("y0: " + _("This is not a valid length"))
            if not x1 is None:
                if not x1.is_valid_length:
                    raise SyntaxError("x1: " + _("This is not a valid length"))
            if not y1 is None:
                if not y1.is_valid_length:
                    raise SyntaxError("y1: " + _("This is not a valid length"))

            simple_line = SimpleLine(x0, y0, x1, y1)
            simple_line.render(
                ppi=1000.0,
                width="%fmm" % bed_dim.bed_width,
                height="%fmm" % bed_dim.bed_height,
            )
            self.add_element(simple_line)
            if data is None:
                return "elements", [simple_line]
            else:
                data.append(simple_line)
                return "elements", data

        @context.console_option(
            "size", "s", type=float, help=_("font size to for object")
        )
        @context.console_argument("text", type=str, help=_("quoted string of text"))
        @context.console_command(
            "text",
            help=_("text <text>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_text(
            command, channel, _, data=None, text=None, size=None, **kwargs
        ):
            if text is None:
                channel(_("No text specified"))
                return
            svg_text = SVGText(text)
            if size is not None:
                svg_text.font_size = size
            self.add_element(svg_text)
            if data is None:
                return "elements", [svg_text]
            else:
                data.append(svg_text)
                return "elements", data

        @context.console_command(
            "polygon", help=_("polygon (Length Length)*"), input_type=("elements", None)
        )
        def element_polygon(args=tuple(), data=None, **kwargs):
            try:
                mlist = list(map(str, args))
                for ct, e in enumerate(mlist):
                    ll = Length(e)
                    # print("e=%s, ll=%s, valid=%s" % (e, ll, ll.is_valid_length))
                    if ct % 2 == 0:
                        x = ll.value(
                            ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                        )
                    else:
                        x = ll.value(
                            ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
                        )
                    mlist[ct] = x
                    ct += 1
                element = Polygon(mlist)
            except ValueError:
                raise SyntaxError(_("Must be a list of spaced delimited length pairs."))
            self.add_element(element)
            if data is None:
                return "elements", [element]
            else:
                data.append(element)
                return "elements", data

        @context.console_command(
            "polyline",
            help=_("polyline (Length Length)*"),
            input_type=("elements", None),
        )
        def element_polyline(command, channel, _, args=tuple(), data=None, **kwargs):
            pcol = None
            pstroke = Color()
            try:
                mlist = list(map(str, args))
                for ct, e in enumerate(mlist):
                    ll = Length(e)
                    if ct % 2 == 0:
                        x = ll.value(
                            ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                        )
                    else:
                        x = ll.value(
                            ppi=1000.0,
                            relative_length=bed_dim.bed_height * MILS_IN_MM,
                        )
                    mlist[ct] = x

                    ct += 1

                element = Polyline(mlist)
                element.fill = pcol
            except ValueError:
                raise SyntaxError(_("Must be a list of spaced delimited length pairs."))
            self.add_element(element)
            if data is None:
                return "elements", [element]
            else:
                data.append(element)
                return "elements", data

        @context.console_command(
            "path", help=_("Convert any shapes to paths"), input_type="elements"
        )
        def element_path_convert(data, **kwargs):
            for e in data:
                try:
                    node = e.node
                    node.replace_object(abs(Path(node.object)))
                    node.altered()
                except AttributeError:
                    pass

        @context.console_argument(
            "path_d", type=str, help=_("svg path syntax command (quoted).")
        )
        @context.console_command(
            "path",
            help=_("path <svg path>"),
            output_type="elements",
        )
        def element_path(path_d, data, **kwargs):
            try:
                path = Path(path_d)
            except ValueError:
                raise SyntaxError(_("Not a valid path_d string (try quotes)"))

            self.add_element(path)
            if data is None:
                return "elements", [path]
            else:
                data.append(path)
                return "elements", data

        @context.console_argument(
            "stroke_width", type=Length, help=_("Stroke-width for the given stroke")
        )
        @context.console_command(
            "stroke-width",
            help=_("stroke-width <length>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_stroke_width(
            command, channel, _, stroke_width, data=None, **kwargs
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            if stroke_width is None:
                channel("----------")
                channel(_("Stroke-Width Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    if e.stroke is None or e.stroke == "none":
                        channel(_("%d: stroke = none - %s") % (i, name))
                    else:
                        channel(_("%d: stroke = %s - %s") % (i, e.stroke_width, name))
                    i += 1
                channel("----------")
                return
            else:
                if not stroke_width.is_valid_length:
                    raise SyntaxError(
                        "stroke-width: " + _("This is not a valid length")
                    )

            if len(data) == 0:
                channel(_("No selected elements."))
                return
            stroke_width = stroke_width.value(
                ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
            )
            if isinstance(stroke_width, Length):
                raise SyntaxError
            for e in data:
                e.stroke_width = stroke_width
                if hasattr(e, "node"):
                    e.node.altered()
            context.signal("refresh_scene")
            return "elements", data

        @context.console_option("filter", "f", type=str, help="Filter indexes")
        @context.console_argument(
            "color", type=Color, help=_("Color to color the given stroke")
        )
        @context.console_command(
            "stroke",
            help=_("stroke <svg color>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_stroke(
            command, channel, _, color, data=None, filter=None, **kwargs
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            apply = data
            if filter is not None:
                apply = list()
                for value in filter.split(","):
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                    try:
                        apply.append(data[value])
                    except IndexError:
                        channel(_("index %d out of range") % value)
            if color is None:
                channel("----------")
                channel(_("Stroke Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    if e.stroke is None or e.stroke == "none":
                        channel(_("%d: stroke = none - %s") % (i, name))
                    else:
                        channel(_("%d: stroke = %s - %s") % (i, e.stroke.hex, name))
                    i += 1
                channel("----------")
                return
            elif color == "none":
                for e in apply:
                    e.stroke = None
                    if hasattr(e, "node"):
                        e.node.altered()
            else:
                for e in apply:
                    e.stroke = Color(color)
                    if hasattr(e, "node"):
                        e.node.altered()
            context.signal("refresh_scene")
            return "elements", data

        @context.console_option("filter", "f", type=str, help="Filter indexes")
        @context.console_argument(
            "color", type=Color, help=_("Color to set the fill to")
        )
        @context.console_command(
            "fill",
            help=_("fill <svg color>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_fill(command, channel, _, color, data=None, filter=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            apply = data
            if filter is not None:
                apply = list()
                for value in filter.split(","):
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                    try:
                        apply.append(data[value])
                    except IndexError:
                        channel(_("index %d out of range") % value)
            if color is None:
                channel("----------")
                channel(_("Fill Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    if e.fill is None or e.fill == "none":
                        channel(_("%d: fill = none - %s") % (i, name))
                    else:
                        channel(_("%d: fill = %s - %s") % (i, e.fill.hex, name))
                    i += 1
                channel("----------")
                return "elements", data
            elif color == "none":
                for e in apply:
                    e.fill = None
                    if hasattr(e, "node"):
                        e.node.altered()
            else:
                for e in apply:
                    e.fill = Color(color)
                    if hasattr(e, "node"):
                        e.node.altered()
            context.signal("refresh_scene")
            return "elements", data

        @context.console_argument("x_offset", type=Length, help=_("x offset."))
        @context.console_argument("y_offset", type=Length, help=_("y offset"))
        @context.console_command(
            "outline",
            help=_("outline the current selected elements"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_outline(
            command,
            channel,
            _,
            x_offset=None,
            y_offset=None,
            data=None,
            args=tuple(),
            **kwargs,
        ):
            """
            Draws an outline of the current shape.
            """
            if x_offset is None:
                raise SyntaxError
            elif not x_offset.is_valid_length:
                raise SyntaxError("x-offset: " + _("This is not a valid length"))
            if not y_offset is None:
                if not y_offset.is_valid_length:
                    raise SyntaxError("y-offset: " + _("This is not a valid length"))

            bounds = self.selected_area()
            if bounds is None:
                channel(_("Nothing Selected"))
                return
            x_pos = bounds[0]
            y_pos = bounds[1]
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]

            offset_x = x_offset.value(ppi=1000.0, relative_length=width)
            if y_offset is None:
                offset_y = offset_x
            else:
                offset_y = y_offset.value(ppi=1000.0, relative_length=height)

            x_pos -= offset_x
            y_pos -= offset_y
            width += offset_x * 2
            height += offset_y * 2
            element = Path(Rect(x=x_pos, y=y_pos, width=width, height=height))
            self.add_element(element, "red")
            self.classify([element])
            if data is None:
                return "elements", [element]
            else:
                data.append(element)
                return "elements", data

        @context.console_command(
            "hull",
            help=_("creates convex hull of current elements as an object"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_hull(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            pts = []
            for obj in data:
                if isinstance(obj, Path):
                    epath = abs(obj)
                    pts += [q for q in epath.as_points()]
                elif isinstance(obj, SVGImage):
                    bounds = obj.bbox()
                    pts += [
                        (bounds[0], bounds[1]),
                        (bounds[0], bounds[3]),
                        (bounds[2], bounds[1]),
                        (bounds[2], bounds[3]),
                    ]
            hull = [p for p in Point.convex_hull(pts)]
            if len(hull) == 0:
                channel(_("No elements bounds to trace."))
                return
            hull.append(hull[0])  # loop
            poly_path = Polygon(hull)
            self.add_element(poly_path)
            if data is None:
                return "elements", [poly_path]
            else:
                data.append(poly_path)
                return "elements", data

        @context.console_argument(
            "angle", type=Angle.parse, help=_("angle to rotate by")
        )
        @context.console_option("cx", "x", type=Length, help=_("center x"))
        @context.console_option("cy", "y", type=Length, help=_("center y"))
        @context.console_option(
            "absolute",
            "a",
            type=bool,
            action="store_true",
            help=_("angle_to absolute angle"),
        )
        @context.console_command(
            "rotate",
            help=_("rotate <angle>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_rotate(
            command,
            channel,
            _,
            angle,
            cx=None,
            cy=None,
            absolute=False,
            data=None,
            **kwargs,
        ):
            if angle is None:
                channel("----------")
                channel(_("Rotate Values:"))
                i = 0
                for element in self.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    channel(
                        _("%d: rotate(%fturn) - %s")
                        % (i, element.rotation.as_turns, name)
                    )
                    i += 1
                channel("----------")
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            self.validate_selected_area()
            bounds = self.selected_area()
            if bounds is None:
                channel(_("No selected elements."))
                return
            rot = angle.as_degrees

            if cx is not None:
                if cx.is_valid_length:
                    cx = cx.value(
                        ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                    )
                else:
                    raise SyntaxError("cx: " + _("This is not a valid length"))
            else:
                cx = (bounds[2] + bounds[0]) / 2.0
            if cy is not None:
                if cy.is_valid_length:
                    cy = cy.value(
                        ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
                    )
                else:
                    raise SyntaxError("cy: " + _("This is not a valid length"))
            else:
                cy = (bounds[3] + bounds[1]) / 2.0
            matrix = Matrix("rotate(%fdeg,%f,%f)" % (rot, cx, cy))
            try:
                if not absolute:
                    for element in data:
                        try:
                            if element.lock:
                                continue
                        except AttributeError:
                            pass

                        element *= matrix
                        if hasattr(element, "node"):
                            element.node.modified()
                else:
                    for element in data:
                        start_angle = element.rotation
                        amount = rot - start_angle
                        matrix = Matrix(
                            "rotate(%f,%f,%f)" % (Angle(amount).as_degrees, cx, cy)
                        )
                        element *= matrix
                        if hasattr(element, "node"):
                            element.node.modified()
            except ValueError:
                raise SyntaxError
            context.signal("refresh_scene")
            return "elements", data

        @context.console_argument("scale_x", type=float, help=_("scale_x value"))
        @context.console_argument("scale_y", type=float, help=_("scale_y value"))
        @context.console_option("px", "x", type=Length, help=_("scale x origin point"))
        @context.console_option("py", "y", type=Length, help=_("scale y origin point"))
        @context.console_option(
            "absolute",
            "a",
            type=bool,
            action="store_true",
            help=_("scale to absolute size"),
        )
        @context.console_command(
            "scale",
            help=_("scale <scale> [<scale-y>]?"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_scale(
            command,
            channel,
            _,
            scale_x=None,
            scale_y=None,
            px=None,
            py=None,
            absolute=False,
            data=None,
            **kwargs,
        ):
            if scale_x is None:
                channel("----------")
                channel(_("Scale Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    channel(
                        "%d: scale(%f, %f) - %s"
                        % (
                            i,
                            e.transform.value_scale_x(),
                            e.transform.value_scale_x(),
                            name,
                        )
                    )
                    i += 1
                channel("----------")
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            bounds = Group.union_bbox(data)
            if scale_y is None:
                scale_y = scale_x
            if px is not None:
                if px.is_valid_length:
                    center_x = px.value(
                        ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                    )
                else:
                    raise SyntaxError("px: " + _("This is not a valid length"))
            else:
                center_x = (bounds[2] + bounds[0]) / 2.0
            if py is not None:
                if py.is_valid_length:
                    center_y = py.value(
                        ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
                    )
                else:
                    raise SyntaxError("py: " + _("This is not a valid length"))
            else:
                center_y = (bounds[3] + bounds[1]) / 2.0
            if scale_x == 0 or scale_y == 0:
                channel(_("Scaling by Zero Error"))
                return
            m = Matrix("scale(%f,%f,%f,%f)" % (scale_x, scale_y, center_x, center_y))
            try:
                if not absolute:
                    for e in data:
                        try:
                            if e.lock:
                                continue
                        except AttributeError:
                            pass

                        e *= m
                        if hasattr(e, "node"):
                            e.node.modified()
                else:
                    for e in data:
                        try:
                            if e.lock:
                                continue
                        except AttributeError:
                            pass

                        osx = e.transform.value_scale_x()
                        osy = e.transform.value_scale_y()
                        nsx = scale_x / osx
                        nsy = scale_y / osy
                        m = Matrix(
                            "scale(%f,%f,%f,%f)" % (nsx, nsy, center_x, center_y)
                        )
                        e *= m
                        if hasattr(e, "node"):
                            e.node.modified()
            except ValueError:
                raise SyntaxError
            context.signal("refresh_scene")
            return "elements", data

        @context.console_argument("tx", type=Length, help=_("translate x value"))
        @context.console_argument("ty", type=Length, help=_("translate y value"))
        @context.console_option(
            "absolute",
            "a",
            type=bool,
            action="store_true",
            help=_("translate to absolute position"),
        )
        @context.console_command(
            "translate",
            help=_("translate <tx> <ty>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_translate(
            command, channel, _, tx, ty, absolute=False, data=None, **kwargs
        ):
            if tx is None:
                channel("----------")
                channel(_("Translate Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    channel(
                        _("%d: translate(%f, %f) - %s")
                        % (
                            i,
                            e.transform.value_trans_x(),
                            e.transform.value_trans_y(),
                            name,
                        )
                    )
                    i += 1
                channel("----------")
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            if tx is not None:
                if tx.is_valid_length:
                    tx = tx.value(
                        ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                    )
                else:
                    raise SyntaxError("tx: " + _("This is not a valid length"))
            else:
                tx = 0
            if ty is not None:
                if ty.is_valid_length:
                    ty = ty.value(
                        ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
                    )
                else:
                    raise SyntaxError("ty: " + _("This is not a valid length"))
            else:
                ty = 0
            m = Matrix("translate(%f,%f)" % (tx, ty))
            try:
                if not absolute:
                    for e in data:
                        e *= m
                        if hasattr(e, "node"):
                            e.node.modified()
                else:
                    for e in data:
                        otx = e.transform.value_trans_x()
                        oty = e.transform.value_trans_y()
                        ntx = tx - otx
                        nty = ty - oty
                        m = Matrix("translate(%f,%f)" % (ntx, nty))
                        e *= m
                        if hasattr(e, "node"):
                            e.node.modified()
            except ValueError:
                raise SyntaxError
            context.signal("refresh_scene")
            return "elements", data

        @context.console_command(
            "move_to_laser",
            help=_("translates the selected element to the laser head"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_translate(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            spooler, input_driver, output = context.registered[
                "device/%s" % context.root.active
            ]
            try:
                tx = input_driver.current_x
            except AttributeError:
                tx = 0
            try:
                ty = input_driver.current_y
            except AttributeError:
                ty = 0
            try:
                bounds = Group.union_bbox([abs(e) for e in data])
                otx = bounds[0]
                oty = bounds[1]
                ntx = tx - otx
                nty = ty - oty
                for e in data:
                    e.transform.post_translate(ntx, nty)
                    if hasattr(e, "node"):
                        e.node.modified()
            except ValueError:
                raise SyntaxError
            context.signal("refresh_scene")
            return "elements", data

        @context.console_argument(
            "x_pos", type=Length, help=_("x position for top left corner")
        )
        @context.console_argument(
            "y_pos", type=Length, help=_("y position for top left corner")
        )
        @context.console_argument("width", type=Length, help=_("new width of selected"))
        @context.console_argument(
            "height", type=Length, help=_("new height of selected")
        )
        @context.console_command(
            "resize",
            help=_("resize <x-pos> <y-pos> <width> <height>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_resize(
            command, channel, _, x_pos, y_pos, width, height, data=None, **kwargs
        ):
            if height is None:
                raise SyntaxError
            try:
                area = self.selected_area()
                if area is None:
                    channel(_("resize: nothing selected"))
                    return
                if not x_pos is None:
                    if not x_pos.is_valid_length:
                        raise SyntaxError("x_pos: " + _("This is not a valid length"))
                if not y_pos is None:
                    if not y_pos.is_valid_length:
                        raise SyntaxError("y_pos: " + _("This is not a valid length"))
                if not width is None:
                    if not width.is_valid_length:
                        raise SyntaxError("width: " + _("This is not a valid length"))
                if not height is None:
                    if not height.is_valid_length:
                        raise SyntaxError("height: " + _("This is not a valid length"))

                x_pos = x_pos.value(
                    ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                )
                y_pos = y_pos.value(
                    ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
                )
                width = width.value(
                    ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                )
                height = height.value(
                    ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
                )
                x, y, x1, y1 = area
                w, h = x1 - x, y1 - y
                if w == 0 or h == 0:  # dot
                    channel(_("resize: cannot resize a dot"))
                    return
                sx = width / w
                sy = height / h
                # Don't do anything if scale is 1
                if sx == 1.0 and sy == 1.0:
                    channel(_("resize: nothing to do - scale factors 1"))
                    return

                m = Matrix(
                    "translate(%f,%f) scale(%f,%f) translate(%f,%f)"
                    % (x_pos, y_pos, sx, sy, -x, -y)
                )
                if data is None:
                    data = list(self.elems(emphasized=True))
                for e in data:
                    try:
                        if e.lock:
                            channel(_("resize: cannot resize a locked image"))
                            return
                    except AttributeError:
                        pass
                for e in data:
                    e *= m
                    if hasattr(e, "node"):
                        e.node.modified()
                context.signal("refresh_scene")
                return "elements", data
            except (ValueError, ZeroDivisionError, TypeError):
                raise SyntaxError

        @context.console_argument("sx", type=float, help=_("scale_x value"))
        @context.console_argument("kx", type=float, help=_("skew_x value"))
        @context.console_argument("ky", type=float, help=_("skew_y value"))
        @context.console_argument("sy", type=float, help=_("scale_y value"))
        @context.console_argument("tx", type=Length, help=_("translate_x value"))
        @context.console_argument("ty", type=Length, help=_("translate_y value"))
        @context.console_command(
            "matrix",
            help=_("matrix <sx> <kx> <ky> <sy> <tx> <ty>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_matrix(
            command, channel, _, sx, kx, ky, sy, tx, ty, data=None, **kwargs
        ):
            if ty is None:
                channel("----------")
                channel(_("Matrix Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    channel("%d: %s - %s" % (i, str(e.transform), name))
                    i += 1
                channel("----------")
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            try:
                # SVG 7.15.3 defines the matrix form as:
                # [a c  e]
                # [b d  f]
                if not tx is None:
                    if not tx.is_valid_length:
                        raise SyntaxError("tx: " + _("This is not a valid length"))
                if not ty is None:
                    if not ty.is_valid_length:
                        raise SyntaxError("ty: " + _("This is not a valid length"))

                m = Matrix(
                    sx,
                    kx,
                    ky,
                    sy,
                    tx.value(
                        ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                    ),
                    ty.value(
                        ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
                    ),
                )
                for e in data:
                    try:
                        if e.lock:
                            continue
                    except AttributeError:
                        pass

                    e.transform = Matrix(m)
                    if hasattr(e, "node"):
                        e.node.modified()
            except ValueError:
                raise SyntaxError
            context.signal("refresh_scene")
            return

        @context.console_command(
            "reset",
            help=_("reset affine transformations"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def reset(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            for e in data:
                try:
                    if e.lock:
                        continue
                except AttributeError:
                    pass

                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(_("reset - %s") % name)
                e.transform.reset()
                if hasattr(e, "node"):
                    e.node.modified()
            context.signal("refresh_scene")
            return "elements", data

        @context.console_command(
            "reify",
            help=_("reify affine transformations"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_reify(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            for e in data:
                try:
                    if e.lock:
                        continue
                except AttributeError:
                    pass

                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(_("reified - %s") % name)
                e.reify()
                if hasattr(e, "node"):
                    e.node.altered()
            context.signal("refresh_scene")
            return "elements", data

        @context.console_command(
            "classify",
            help=_("classify elements into operations"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_classify(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            self.classify(data)
            return "elements", data

        @context.console_command(
            "declassify",
            help=_("declassify selected elements"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def declassify(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            self.remove_elements_from_operations(data)
            return "elements", data

        # ==========
        # TREE BASE
        # ==========
        @context.console_command(
            "tree", help=_("access and alter tree elements"), output_type="tree"
        )
        def tree(**kwargs):
            return "tree", [self._tree]

        @context.console_command(
            "bounds", help=_("view tree bounds"), input_type="tree", output_type="tree"
        )
        def tree_bounds(command, channel, _, data=None, **kwargs):
            if data is None:
                data = [self._tree]

            def b_list(path, node):
                for i, n in enumerate(node.children):
                    p = list(path)
                    p.append(str(i))
                    channel(
                        "%s: %s - %s %s - %s"
                        % (
                            ".".join(p).ljust(10),
                            str(n._bounds),
                            str(n._bounds_dirty),
                            str(n.type),
                            str(n.label[:16]),
                        )
                    )
                    b_list(p, n)

            for d in data:
                channel("----------")
                if d.type == "root":
                    channel(_("Tree:"))
                else:
                    channel("%s:" % d.label)
                b_list([], d)
                channel("----------")

            return "tree", data

        @context.console_command(
            "list", help=_("view tree"), input_type="tree", output_type="tree"
        )
        def tree_list(command, channel, _, data=None, **kwargs):
            if data is None:
                data = [self._tree]

            def t_list(path, node):
                for i, n in enumerate(node.children):
                    p = list(path)
                    p.append(str(i))
                    if n.targeted:
                        j = "+"
                    elif n.emphasized:
                        j = "~"
                    elif n.highlighted:
                        j = "-"
                    else:
                        j = ":"
                    channel(
                        "%s%s %s - %s"
                        % (".".join(p).ljust(10), j, str(n.type), str(n.label))
                    )
                    t_list(p, n)

            for d in data:
                channel("----------")
                if d.type == "root":
                    channel(_("Tree:"))
                else:
                    channel("%s:" % d.label)
                t_list([], d)
                channel("----------")

            return "tree", data

        @context.console_argument("drag", help="Drag node address")
        @context.console_argument("drop", help="Drop node address")
        @context.console_command(
            "dnd", help=_("Drag and Drop Node"), input_type="tree", output_type="tree"
        )
        def tree_dnd(command, channel, _, data=None, drag=None, drop=None, **kwargs):
            """
            Drag and Drop command performs a console based drag and drop operation
            Eg. "tree dnd 0.1 0.2" will drag node 0.1 into node 0.2
            """
            if data is None:
                data = [self._tree]
            if drop is None:
                raise SyntaxError
            try:
                drag_node = self._tree
                for n in drag.split("."):
                    drag_node = drag_node.children[int(n)]
                drop_node = self._tree
                for n in drop.split("."):
                    drop_node = drop_node.children[int(n)]
                drop_node.drop(drag_node)
            except (IndexError, AttributeError, ValueError):
                raise SyntaxError
            return "tree", data

        @context.console_argument("node", help="Node address for menu")
        @context.console_argument("execute", help="Command to execute")
        @context.console_command(
            "menu",
            help=_("Load menu for given node"),
            input_type="tree",
            output_type="tree",
        )
        def tree_menu(
            command, channel, _, data=None, node=None, execute=None, **kwargs
        ):
            """
            Create menu for a particular node.
            Processes submenus, references, radio_state as needed.
            """
            try:
                menu_node = self._tree
                for n in node.split("."):
                    menu_node = menu_node.children[int(n)]
            except (IndexError, AttributeError, ValueError):
                raise SyntaxError

            menu = []
            submenus = {}

            def menu_functions(f, cmd_node):
                func_dict = dict(f.func_dict)

                def specific(event=None):
                    f(cmd_node, **func_dict)

                return specific

            for func in self.tree_operations_for_node(menu_node):
                submenu_name = func.submenu
                submenu = None
                if submenu_name in submenus:
                    submenu = submenus[submenu_name]
                elif submenu_name is not None:
                    submenu = list()
                    menu.append((submenu_name, submenu))
                    submenus[submenu_name] = submenu

                menu_context = submenu if submenu is not None else menu
                if func.reference is not None:
                    pass
                if func.radio_state is not None:
                    if func.separate_before:
                        menu_context.append(("------", None))
                    n = func.real_name
                    if func.radio_state:
                        n = "✓" + n
                    menu_context.append((n, menu_functions(func, menu_node)))
                else:
                    if func.separate_before:
                        menu_context.append(("------", None))
                    menu_context.append(
                        (func.real_name, menu_functions(func, menu_node))
                    )
                if func.separate_after:
                    menu_context.append(("------", None))
            if execute is not None:
                try:
                    execute_command = ("menu", menu)
                    for n in execute.split("."):
                        name, cmd = execute_command
                        execute_command = cmd[int(n)]
                    name, cmd = execute_command
                    channel("Executing %s: %s" % (name, str(cmd)))
                    cmd()
                except (IndexError, AttributeError, ValueError, TypeError):
                    raise SyntaxError
            else:

                def m_list(path, menu):
                    for i, n in enumerate(menu):
                        p = list(path)
                        p.append(str(i))
                        name, submenu = n
                        channel("%s: %s" % (".".join(p).ljust(10), str(name)))
                        if isinstance(submenu, list):
                            m_list(p, submenu)

                m_list([], menu)

            return "tree", data

        @context.console_command(
            "selected",
            help=_("delegate commands to focused value"),
            input_type="tree",
            output_type="tree",
        )
        def selected(channel, _, **kwargs):
            """
            Set tree list to selected node
            """
            return "tree", list(self.flat(selected=True))

        @context.console_command(
            "emphasized",
            help=_("delegate commands to focused value"),
            input_type="tree",
            output_type="tree",
        )
        def emphasized(channel, _, **kwargs):
            """
            Set tree list to emphasized node
            """
            return "tree", list(self.flat(emphasized=True))

        @context.console_command(
            "highlighted",
            help=_("delegate commands to sub-focused value"),
            input_type="tree",
            output_type="tree",
        )
        def highlighted(channel, _, **kwargs):
            """
            Set tree list to highlighted nodes
            """
            return "tree", list(self.flat(highlighted=True))

        @context.console_command(
            "targeted",
            help=_("delegate commands to sub-focused value"),
            input_type="tree",
            output_type="tree",
        )
        def targeted(channel, _, **kwargs):
            """
            Set tree list to highlighted nodes
            """
            return "tree", list(self.flat(targeted=True))

        @context.console_command(
            "delete",
            help=_("delete the given nodes"),
            input_type="tree",
            output_type="tree",
        )
        def delete(channel, _, data=None, **kwargs):
            """
            Delete nodes.
            Structural nodes such as root, elements branch, and operations branch are not able to be deleted
            """
            self.remove_nodes(data)
            self.context.signal("refresh_scene", 0)
            return "tree", [self._tree]

        @context.console_command(
            "delegate",
            help=_("delegate commands to focused value"),
            input_type="tree",
            output_type=("op", "elements"),
        )
        def delegate(channel, _, **kwargs):
            """
            Delegate to either ops or elements depending on the current node emphasis
            """
            for item in self.flat(
                types=("op", "elem", "group", "file"), emphasized=True
            ):
                if item.type == "op":
                    return "ops", list(self.ops(emphasized=True))
                if item.type in ("elem", "group", "file"):
                    return "elements", list(self.elems(emphasized=True))

        # ==========
        # CLIPBOARD COMMANDS
        # ==========
        @context.console_option("name", "n", type=str)
        @context.console_command(
            "clipboard",
            help=_("clipboard"),
            input_type=(None, "elements"),
            output_type="clipboard",
        )
        def clipboard_base(data=None, name=None, **kwargs):
            """
            Clipboard commands. Applies to current selected elements to
            make a copy of those elements. Paste a copy of those elements
            or cut those elements. Clear clears the clipboard.

            The list command will list them but this is only for debug.
            """
            if name is not None:
                self._clipboard_default = name
            if data is None:
                return "clipboard", list(self.elems(emphasized=True))
            else:
                return "clipboard", data

        @context.console_command(
            "copy",
            help=_("clipboard copy"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_copy(data=None, **kwargs):
            destination = self._clipboard_default
            self._clipboard[destination] = [copy(e) for e in data]
            return "elements", self._clipboard[destination]

        @context.console_option("dx", "x", help=_("paste offset x"), type=Length)
        @context.console_option("dy", "y", help=_("paste offset y"), type=Length)
        @context.console_command(
            "paste",
            help=_("clipboard paste"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_paste(command, channel, _, data=None, dx=None, dy=None, **kwargs):
            destination = self._clipboard_default
            try:
                pasted = [copy(e) for e in self._clipboard[destination]]
            except KeyError:
                channel(_("Error: Clipboard Empty"))
                return
            if dx is not None or dy is not None:
                if dx is None:
                    dx = 0
                else:
                    if dx.is_valid_length:
                        dx = dx.value(
                            ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                        )
                    else:
                        raise SyntaxError("dx: " + _("This is not a valid length"))
                if dy is None:
                    dy = 0
                else:
                    if dy.is_valid_length:
                        dy = dy.value(
                            ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
                        )
                    else:
                        raise SyntaxError("dy: " + _("This is not a valid length"))
                m = Matrix("translate(%s, %s)" % (dx, dy))
                for e in pasted:
                    e *= m
            group = self.elem_branch.add(type="group", label="Group")
            for p in pasted:
                group.add(p, type="elem")
            self.set_emphasis([group])
            return "elements", pasted

        @context.console_command(
            "cut",
            help=_("clipboard cut"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_cut(data=None, **kwargs):
            destination = self._clipboard_default
            self._clipboard[destination] = [copy(e) for e in data]
            self.remove_elements(data)
            return "elements", self._clipboard[destination]

        @context.console_command(
            "clear",
            help=_("clipboard clear"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_clear(data=None, **kwargs):
            destination = self._clipboard_default
            old = self._clipboard[destination]
            self._clipboard[destination] = None
            return "elements", old

        @context.console_command(
            "contents",
            help=_("clipboard contents"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_contents(**kwargs):
            destination = self._clipboard_default
            return "elements", self._clipboard[destination]

        @context.console_command(
            "list",
            help=_("clipboard list"),
            input_type="clipboard",
        )
        def clipboard_list(command, channel, _, **kwargs):
            for v in self._clipboard:
                k = self._clipboard[v]
                channel("%s: %s" % (str(v).ljust(5), str(k)))

        # ==========
        # NOTES COMMANDS
        # ==========
        @context.console_option(
            "append", "a", type=bool, action="store_true", default=False
        )
        @context.console_command("note", help=_("note <note>"))
        def note(command, channel, _, append=False, remainder=None, **kwargs):
            note = remainder
            if note is None:
                if self.note is None:
                    channel(_("No Note."))
                else:
                    channel(str(self.note))
            else:
                if append:
                    self.note += "\n" + note
                else:
                    self.note = note
                channel(_("Note Set."))
                channel(str(self.note))

        # ==========
        # TRACE OPERATIONS
        # ==========
        @context.console_command(
            "trace_hull",
            help=_("trace the convex hull of current elements"),
            input_type=(None, "elements"),
        )
        def trace_trace_hull(command, channel, _, data=None, **kwargs):
            active = self.context.active
            try:
                spooler, input_device, output = self.context.registered[
                    "device/%s" % active
                ]
            except KeyError:
                channel(_("No active device found."))
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            pts = []
            for obj in data:
                if isinstance(obj, Path):
                    epath = abs(obj)
                    pts += [q for q in epath.as_points()]
                elif isinstance(obj, SVGImage):
                    bounds = obj.bbox()
                    pts += [
                        (bounds[0], bounds[1]),
                        (bounds[0], bounds[3]),
                        (bounds[2], bounds[1]),
                        (bounds[2], bounds[3]),
                    ]
            hull = [p for p in Point.convex_hull(pts)]
            if len(hull) == 0:
                channel(_("No elements bounds to trace."))
                return
            hull.append(hull[0])  # loop

            def trace_hull():
                yield COMMAND_WAIT_FINISH
                yield COMMAND_MODE_RAPID
                for p in hull:
                    yield COMMAND_MOVE, p[0], p[1]

            spooler.job(trace_hull)

        @context.console_command(
            "trace_quick", help=_("quick trace the bounding box of current elements")
        )
        def trace_trace_quick(command, channel, _, **kwargs):
            active = self.context.active
            try:
                spooler, input_device, output = self.context.registered[
                    "device/%s" % active
                ]
            except KeyError:
                channel(_("No active device found."))
                return
            bbox = self.selected_area()
            if bbox is None:
                channel(_("No elements bounds to trace."))
                return

            def trace_quick():
                yield COMMAND_MODE_RAPID
                yield COMMAND_MOVE, bbox[0], bbox[1]
                yield COMMAND_MOVE, bbox[2], bbox[1]
                yield COMMAND_MOVE, bbox[2], bbox[3]
                yield COMMAND_MOVE, bbox[0], bbox[3]
                yield COMMAND_MOVE, bbox[0], bbox[1]

            spooler.job(trace_quick)

        # ==========
        # TRACE OPERATIONS
        # ==========
        @context.console_command(
            "trace",
            help=_("trace the given element path"),
            input_type="elements",
        )
        def trace_trace_spooler(command, channel, _, data=None, **kwargs):
            if not data:
                return
            active = self.context.active
            try:
                spooler, input_device, output = self.context.registered[
                    "device/%s" % active
                ]
            except KeyError:
                channel(_("No active device found."))
                return

            pts = []
            for path in data:
                if isinstance(path, Shape):
                    path = abs(Path(path))
                    pts.append(path.first_point)
                    for segment in path:
                        pts.append(segment.end)
            if not pts:
                return

            def trace_command():
                yield COMMAND_WAIT_FINISH
                yield COMMAND_MODE_RAPID
                for p in pts:
                    yield COMMAND_MOVE, p[0], p[1]

            spooler.job(trace_command)

        # --------------------------- END COMMANDS ------------------------------

        # --------------------------- TREE OPERATIONS ---------------------------

        _ = self.context._

        non_structural_nodes = (
            "op",
            "opnode",
            "cmdop",
            "consoleop",
            "lasercode",
            "cutcode",
            "blob",
            "elem",
            "file",
            "group",
        )

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: len(list(self.ops(emphasized=True))) == 1)
        @self.tree_operation(_("Operation properties"), node_type="op", help="")
        def operation_property(node, **kwargs):
            self.context.open("window/OperationProperty", self.context.gui, node=node)

        @self.tree_separator_after()
        @self.tree_operation(_("Edit"), node_type="consoleop", help="")
        def edit_console_command(node, **kwargs):
            self.context.open("window/ConsoleProperty", self.context.gui, node=node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, Shape))
        @self.tree_operation(_("Element properties"), node_type="elem", help="")
        def path_property(node, **kwargs):
            self.context.open("window/PathProperty", self.context.gui, node=node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, Group))
        @self.tree_operation(_("Group properties"), node_type="group", help="")
        def group_property(node, **kwargs):
            self.context.open("window/GroupProperty", self.context.gui, node=node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, SVGText))
        @self.tree_operation(_("Text properties"), node_type="elem", help="")
        def text_property(node, **kwargs):
            self.context.open("window/TextProperty", self.context.gui, node=node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_operation(_("Image properties"), node_type="elem", help="")
        def image_property(node, **kwargs):
            self.context.open("window/ImageProperty", self.context.gui, node=node)

        @self.tree_operation(
            _("Ungroup elements"), node_type=("group", "file"), help=""
        )
        def ungroup_elements(node, **kwargs):
            for n in list(node.children):
                node.insert_sibling(n)
            node.remove_node()  # Removing group/file node.

        @self.tree_operation(_("Group elements"), node_type="elem", help="")
        def group_elements(node, **kwargs):
            # group_node = node.parent.add_sibling(node, type="group", name="Group")
            group_node = node.parent.add(type="group", label="Group")
            for e in list(self.elems(emphasized=True)):
                node = e.node
                group_node.append_child(node)

        @self.tree_operation(
            _("Enable/Disable ops"), node_type=("op", "cmdop", "consoleop"), help=""
        )
        def toggle_n_operations(node, **kwargs):
            for n in self.ops(emphasized=True):
                n.output = not n.output
                n.notify_update()

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(_("Convert to Image"), node_type="op", help="")
        def convert_operation_image(node, **kwargs):
            for n in self.ops(emphasized=True):
                n.operation = "Image"

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(_("Convert to Raster"), node_type="op", help="")
        def convert_operation_raster(node, **kwargs):
            for n in self.ops(emphasized=True):
                n.operation = "Raster"

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(_("Convert to Engrave"), node_type="op", help="")
        def convert_operation_engrave(node, **kwargs):
            for n in self.ops(emphasized=True):
                n.operation = "Engrave"

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(_("Convert to Cut"), node_type="op", help="")
        def convert_operation_cut(node, **kwargs):
            for n in self.ops(emphasized=True):
                n.operation = "Cut"

        def radio_match(node, speed=0, **kwargs):
            return node.settings.speed == float(speed)

        @self.tree_conditional(lambda node: node.operation in ("Raster", "Image"))
        @self.tree_submenu(_("Speed"))
        @self.tree_radio(radio_match)
        @self.tree_values("speed", (50, 75, 100, 150, 200, 250, 300, 350))
        @self.tree_operation(_("%smm/s") % "{speed}", node_type="op", help="")
        def set_speed_raster(node, speed=150, **kwargs):
            node.settings.speed = float(speed)
            self.context.signal("element_property_reload", node)

        @self.tree_conditional(lambda node: node.operation in ("Cut", "Engrave"))
        @self.tree_submenu(_("Speed"))
        @self.tree_radio(radio_match)
        @self.tree_values("speed", (5, 10, 15, 20, 25, 30, 35, 40))
        @self.tree_operation(_("%smm/s") % "{speed}", node_type="op", help="")
        def set_speed_vector(node, speed=35, **kwargs):
            node.settings.speed = float(speed)
            self.context.signal("element_property_reload", node)

        def radio_match(node, power=0, **kwargs):
            return node.settings.power == float(power)

        @self.tree_submenu(_("Power"))
        @self.tree_radio(radio_match)
        @self.tree_values("power", (100, 250, 333, 500, 666, 750, 1000))
        @self.tree_operation(_("%sppi") % "{power}", node_type="op", help="")
        def set_power(node, power=1000, **kwargs):
            node.settings.power = float(power)
            self.context.signal("element_property_reload", node)

        def radio_match(node, i=1, **kwargs):
            return node.settings.raster_step == i

        @self.tree_conditional(lambda node: node.operation == "Raster")
        @self.tree_submenu(_("Step"))
        @self.tree_radio(radio_match)
        @self.tree_iterate("i", 1, 10)
        @self.tree_operation(
            _("Step %s") % "{i}",
            node_type="op",
            help=_("Change raster step values of operation"),
        )
        def set_step_n(node, i=1, **kwargs):
            settings = node.settings
            settings.raster_step = i
            self.context.signal("element_property_reload", node)

        def radio_match(node, passvalue=1, **kwargs):
            return (
                node.settings.passes_custom and passvalue == node.settings.passes
            ) or (not node.settings.passes_custom and passvalue == 1)

        @self.tree_submenu(_("Set operation passes"))
        @self.tree_radio(radio_match)
        @self.tree_iterate("passvalue", 1, 10)
        @self.tree_operation(_("Passes %s") % "{passvalue}", node_type="op", help="")
        def set_n_passes(node, passvalue=1, **kwargs):
            node.settings.passes = passvalue
            node.settings.passes_custom = passvalue != 1
            self.context.signal("element_property_reload", node)

        @self.tree_separator_after()
        @self.tree_operation(
            _("Execute operation(s)"),
            node_type="op",
            help=_("Execute Job for the selected operation(s)."),
        )
        def execute_job(node, **kwargs):
            node.emphasized = True
            self.context("plan0 clear copy-selected\n")
            self.context("window open ExecuteJob 0\n")

        @self.tree_separator_after()
        @self.tree_operation(
            _("Simulate operation(s)"),
            node_type="op",
            help=_("Run simulation for the selected operation(s)"),
        )
        def compile_and_simulate(node, **kwargs):
            node.emphasized = True
            self.context(
                "plan0 copy-selected preprocess validate blob preopt optimize\n"
            )
            self.context("window open Simulation 0\n")

        @self.tree_operation(_("Clear all"), node_type="branch ops", help="")
        def clear_all(node, **kwargs):
            self.context("operation* delete\n")

        @self.tree_operation(_("Clear all"), node_type="branch elems", help="")
        def clear_all_ops(node, **kwargs):
            self.context("element* delete\n")
            self.elem_branch.remove_all_children()

        # ==========
        # REMOVE MULTI (Tree Selected)
        # ==========
        @self.tree_conditional(
            lambda cond: len(
                list(
                    self.flat(selected=True, cascade=False, types=non_structural_nodes)
                )
            )
            > 1
        )
        @self.tree_calc(
            "ecount",
            lambda i: len(
                list(
                    self.flat(selected=True, cascade=False, types=non_structural_nodes)
                )
            ),
        )
        @self.tree_operation(
            _("Remove %s selected items") % "{ecount}",
            node_type=non_structural_nodes,
            help="",
        )
        def remove_multi_nodes(node, **kwargs):
            nodes = list(
                self.flat(selected=True, cascade=False, types=non_structural_nodes)
            )
            for node in nodes:
                if node.parent is not None:  # May have already removed.
                    node.remove_node()
            self.set_emphasis(None)

        # ==========
        # REMOVE SINGLE (Tree Selected)
        # ==========
        @self.tree_conditional(
            lambda cond: len(
                list(
                    self.flat(selected=True, cascade=False, types=non_structural_nodes)
                )
            )
            == 1
        )
        @self.tree_operation(
            _("Remove '%s'") % "{name}",
            node_type=non_structural_nodes,
            help="",
        )
        def remove_type_op(node, **kwargs):
            node.remove_node()
            self.set_emphasis(None)

        # ==========
        # Remove Operations (If No Tree Selected)
        # Note: This code would rarely match anything since the tree selected will almost always be true if we have
        # match this conditional. The tree-selected delete functions are superior.
        # ==========
        @self.tree_conditional(
            lambda cond: len(
                list(
                    self.flat(selected=True, cascade=False, types=non_structural_nodes)
                )
            )
            == 0
        )
        @self.tree_conditional(lambda node: len(list(self.ops(emphasized=True))) > 1)
        @self.tree_calc("ecount", lambda i: len(list(self.ops(emphasized=True))))
        @self.tree_operation(
            _("Remove %s operations") % "{ecount}",
            node_type=("op", "cmdop", "consoleop", "lasercode", "cutcode", "blob"),
            help="",
        )
        def remove_n_ops(node, **kwargs):
            self.context("operation delete\n")

        # ==========
        # REMOVE ELEMENTS
        # ==========
        @self.tree_conditional(lambda node: len(list(self.elems(emphasized=True))) > 1)
        @self.tree_calc("ecount", lambda i: len(list(self.elems(emphasized=True))))
        @self.tree_operation(
            _("Remove %s elements") % "{ecount}",
            node_type=(
                "elem",
                "file",
                "group",
            ),
            help="",
        )
        def remove_n_elements(node, **kwargs):
            self.context("element delete\n")

        # ==========
        # CONVERT TREE OPERATIONS
        # ==========
        @self.tree_operation(
            _("Convert to Cutcode"),
            node_type="lasercode",
            help="",
        )
        def lasercode2cut(node, **kwargs):
            node.replace_node(CutCode.from_lasercode(node.object), type="cutcode")

        @self.tree_conditional_try(lambda node: hasattr(node.object, "as_cutobjects"))
        @self.tree_operation(
            _("Convert to Cutcode"),
            node_type="blob",
            help="",
        )
        def blob2cut(node, **kwargs):
            node.replace_node(node.object.as_cutobjects(), type="cutcode")

        @self.tree_operation(
            _("Convert to Path"),
            node_type="cutcode",
            help="",
        )
        def cutcode2pathcut(node, **kwargs):
            cutcode = node.object
            elements = list(cutcode.as_elements())
            n = None
            for element in elements:
                n = self.elem_branch.add(element, type="elem")
            node.remove_node()
            if n is not None:
                n.focus()

        @self.tree_submenu(_("Clone reference"))
        @self.tree_operation(_("Make 1 copy"), node_type="opnode", help="")
        def clone_single_element_op(node, **kwargs):
            clone_element_op(node, copies=1, **kwargs)

        @self.tree_submenu(_("Clone reference"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(
            _("Make %s copies") % "{copies}", node_type="opnode", help=""
        )
        def clone_element_op(node, copies=1, **kwargs):
            index = node.parent.children.index(node)
            for i in range(copies):
                node.parent.add(node.object, type="opnode", pos=index)
            node.modified()
            self.context.signal("rebuild_tree", 0)

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_operation(
            _("Reverse subitems order"),
            node_type=("op", "group", "branch elems", "file", "branch ops"),
            help=_("Reverse the items within this subitem"),
        )
        def reverse_layer_order(node, **kwargs):
            node.reverse()
            self.context.signal("rebuild_tree", 0)

        @self.tree_separator_after()
        @self.tree_operation(
            _("Refresh classification"), node_type="branch ops", help=""
        )
        def refresh_clasifications(node, **kwargs):
            context = self.context
            elements = context.elements
            elements.remove_elements_from_operations(list(elements.elems()))
            elements.classify(list(elements.elems()))
            self.context.signal("rebuild_tree", 0)

        materials = [
            _("Wood"),
            _("Acrylic"),
            _("Foam"),
            _("Leather"),
            _("Cardboard"),
            _("Cork"),
            _("Textiles"),
            _("Paper"),
            _("Save-1"),
            _("Save-2"),
            _("Save-3"),
        ]

        def union_materials_saved():
            union = [
                d
                for d in self.context.get_context("operations").derivable()
                if d not in materials and d != "previous"
            ]
            union.extend(materials)
            return union

        @self.tree_submenu(_("Use"))
        @self.tree_values(
            "opname", values=self.context.get_context("operations").derivable
        )
        @self.tree_operation(
            _("Load: %s") % "{opname}", node_type="branch ops", help=""
        )
        def load_ops(node, opname, **kwargs):
            self.context("operation load %s\n" % opname)

        @self.tree_submenu(_("Use"))
        @self.tree_operation(_("Other/Blue/Red"), node_type="branch ops", help="")
        def default_classifications(node, **kwargs):
            self.context.elements.load_default()

        @self.tree_submenu(_("Use"))
        @self.tree_operation(_("Basic"), node_type="branch ops", help="")
        def basic_classifications(node, **kwargs):
            self.context.elements.load_default2()

        @self.tree_submenu(_("Save"))
        @self.tree_values("opname", values=union_materials_saved)
        @self.tree_operation("{opname}", node_type="branch ops", help="")
        def save_ops(node, opname="saved", **kwargs):
            self.context("operation save %s\n" % opname)

        @self.tree_separator_before()
        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Image"), node_type="branch ops", help="")
        def append_operation_image(node, pos=None, **kwargs):
            self.context.elements.add_op(LaserOperation(operation="Image"), pos=pos)

        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Raster"), node_type="branch ops", help="")
        def append_operation_raster(node, pos=None, **kwargs):
            self.context.elements.add_op(LaserOperation(operation="Raster"), pos=pos)

        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Engrave"), node_type="branch ops", help="")
        def append_operation_engrave(node, pos=None, **kwargs):
            self.context.elements.add_op(LaserOperation(operation="Engrave"), pos=pos)

        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Cut"), node_type="branch ops", help="")
        def append_operation_cut(node, pos=None, **kwargs):
            self.context.elements.add_op(LaserOperation(operation="Cut"), pos=pos)

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Home"), node_type="branch ops", help="")
        def append_operation_home(node, pos=None, **kwargs):
            self.context.elements.op_branch.add(
                CommandOperation("Home", COMMAND_HOME), type="cmdop", pos=pos
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(
            _("Append Return to Origin"), node_type="branch ops", help=""
        )
        def append_operation_origin(node, pos=None, **kwargs):
            self.context.elements.op_branch.add(
                CommandOperation("Origin", COMMAND_MOVE, 0, 0), type="cmdop", pos=pos
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Beep"), node_type="branch ops", help="")
        def append_operation_beep(node, pos=None, **kwargs):
            self.context.elements.op_branch.add(
                CommandOperation("Beep", COMMAND_BEEP), type="cmdop", pos=pos
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(
            _("Append Interrupt (console)"), node_type="branch ops", help=""
        )
        def append_operation_interrupt_console(node, pos=None, **kwargs):
            self.context.elements.op_branch.add(
                ConsoleOperation('interrupt "Spooling was interrupted"'),
                type="consoleop",
                pos=pos,
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Interrupt"), node_type="branch ops", help="")
        def append_operation_interrupt(node, pos=None, **kwargs):
            self.context.elements.op_branch.add(
                CommandOperation(
                    "Interrupt",
                    COMMAND_FUNCTION,
                    self.context.registered["function/interrupt"],
                ),
                type="cmdop",
                pos=pos,
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(
            _("Append Home/Beep/Interrupt"), node_type="branch ops", help=""
        )
        def append_operation_home_beep_interrupt(node, **kwargs):
            append_operation_home(node, **kwargs)
            append_operation_beep(node, **kwargs)
            append_operation_interrupt(node, **kwargs)
            append_operation_interrupt_console(node, **kwargs)

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Shutdown"), node_type="branch ops", help="")
        def append_operation_shutdown(node, pos=None, **kwargs):
            self.context.elements.op_branch.add(
                CommandOperation(
                    "Shutdown",
                    COMMAND_FUNCTION,
                    self.context.console_function("quit\n"),
                ),
                type="cmdop",
                pos=pos,
            )

        @self.tree_operation(
            _("Reclassify operations"), node_type="branch elems", help=""
        )
        def reclassify_operations(node, **kwargs):
            context = self.context
            elements = context.elements
            elems = list(elements.elems())
            elements.remove_elements_from_operations(elems)
            elements.classify(list(elements.elems()))
            self.context.signal("rebuild_tree", 0)

        @self.tree_operation(
            _("Duplicate operation(s)"),
            node_type="op",
            help=_("duplicate operation element nodes"),
        )
        def duplicate_operation(node, **kwargs):
            operations = self._tree.get(type="branch ops").children
            for op in self.ops(emphasized=True):
                try:
                    pos = operations.index(op) + 1
                except ValueError:
                    pos = None
                copy_op = LaserOperation(op)
                self.add_op(copy_op, pos=pos)
                for child in op.children:
                    try:
                        copy_op.add(child.object, type="opnode")
                    except AttributeError:
                        pass

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_conditional(
            lambda node: node.operation in ("Image", "Engrave", "Cut")
        )
        @self.tree_submenu(_("Passes"))
        @self.tree_operation(_("Add 1 pass"), node_type="op", help="")
        def add_1_pass(node, **kwargs):
            add_n_passes(node, copies=1, **kwargs)

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_conditional(
            lambda node: node.operation in ("Image", "Engrave", "Cut")
        )
        @self.tree_submenu(_("Passes"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(_("Add %s passes") % "{copies}", node_type="op", help="")
        def add_n_passes(node, copies=1, **kwargs):
            add_elements = [
                child.object for child in node.children if child.object is not None
            ]
            removed = False
            for i in range(0, len(add_elements)):
                for q in range(0, i):
                    if add_elements[q] is add_elements[i]:
                        add_elements[i] = None
                        removed = True
            if removed:
                add_elements = [c for c in add_elements if c is not None]
            add_elements *= copies
            node.add_all(add_elements, type="opnode")
            self.context.signal("rebuild_tree", 0)

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_conditional(
            lambda node: node.operation in ("Image", "Engrave", "Cut")
        )
        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_operation(_("Duplicate elements 1 time"), node_type="op", help="")
        def dup_1_copy(node, **kwargs):
            dup_n_copies(node, copies=1, **kwargs)

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_conditional(
            lambda node: node.operation in ("Image", "Engrave", "Cut")
        )
        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(
            _("Duplicate elements %s times") % "{copies}", node_type="op", help=""
        )
        def dup_n_copies(node, copies=1, **kwargs):
            add_elements = [
                child.object for child in node.children if child.object is not None
            ]
            add_elements *= copies
            node.add_all(add_elements, type="opnode")
            self.context.signal("rebuild_tree", 0)

        @self.tree_conditional(lambda node: node.operation in ("Raster", "Image"))
        @self.tree_operation(
            _("Make raster image"),
            node_type="op",
            help=_("Convert a vector element into a raster element."),
        )
        def make_raster_image(node, **kwargs):
            context = self.context
            elements = context.elements
            subitems = list(node.flat(types=("elem", "opnode")))
            reverse = self.context.classify_reverse
            if reverse:
                subitems = list(reversed(subitems))
            make_raster = self.context.registered.get("render-op/make_raster")
            bounds = Group.union_bbox([s.object for s in subitems], with_stroke=True)
            if bounds is None:
                return
            step = float(node.settings.raster_step)
            if step == 0:
                step = 1
            xmin, ymin, xmax, ymax = bounds

            image = make_raster(
                subitems,
                bounds,
                step=step,
            )
            image_element = SVGImage(image=image)
            image_element.transform.post_scale(step, step)
            image_element.transform.post_translate(xmin, ymin)
            image_element.values["raster_step"] = step
            elements.add_elem(image_element)

        def add_after_index(self, node=None):
            try:
                if node is None:
                    node = list(self.ops(emphasized=True))[-1]
                operations = self._tree.get(type="branch ops").children
                return operations.index(node) + 1
            except (ValueError, IndexError):
                return None

        @self.tree_separator_before()
        @self.tree_submenu(_("Add operation"))
        @self.tree_operation(_("Add Image"), node_type="op", help="")
        def add_operation_image(node, **kwargs):
            append_operation_image(node, pos=add_after_index(self, node), **kwargs)

        @self.tree_submenu(_("Add operation"))
        @self.tree_operation(_("Add Raster"), node_type="op", help="")
        def add_operation_raster(node, **kwargs):
            append_operation_raster(node, pos=add_after_index(self, node), **kwargs)

        @self.tree_submenu(_("Add operation"))
        @self.tree_operation(_("Add Engrave"), node_type="op", help="")
        def add_operation_engrave(node, **kwargs):
            append_operation_engrave(node, pos=add_after_index(self, node), **kwargs)

        @self.tree_submenu(_("Add operation"))
        @self.tree_operation(_("Add Cut"), node_type="op", help="")
        def add_operation_cut(node, **kwargs):
            append_operation_cut(node, pos=add_after_index(self, node), **kwargs)

        @self.tree_submenu(_("Add special operation(s)"))
        @self.tree_operation(_("Add Home"), node_type="op", help="")
        def add_operation_home(node, **kwargs):
            append_operation_home(node, pos=add_after_index(self, node), **kwargs)

        @self.tree_submenu(_("Add special operation(s)"))
        @self.tree_operation(_("Add Return to Origin"), node_type="op", help="")
        def add_operation_origin(node, **kwargs):
            append_operation_origin(node, pos=add_after_index(self, node), **kwargs)

        @self.tree_submenu(_("Add special operation(s)"))
        @self.tree_operation(_("Add Beep"), node_type="op", help="")
        def add_operation_beep(node, **kwargs):
            append_operation_beep(node, pos=add_after_index(self, node), **kwargs)

        @self.tree_submenu(_("Add special operation(s)"))
        @self.tree_operation(_("Add Interrupt"), node_type="op", help="")
        def add_operation_interrupt(node, **kwargs):
            append_operation_interrupt(node, pos=add_after_index(self, node), **kwargs)

        @self.tree_submenu(_("Add special operation(s)"))
        @self.tree_operation(_("Add Interrupt (console)"), node_type="op", help="")
        def add_operation_interrupt_console(node, **kwargs):
            append_operation_interrupt_console(
                node, pos=add_after_index(self, node), **kwargs
            )

        @self.tree_submenu(_("Add special operation(s)"))
        @self.tree_operation(_("Add Home/Beep/Interrupt"), node_type="op", help="")
        def add_operation_home_beep_interrupt(node, **kwargs):
            pos = add_after_index(self, node)
            append_operation_home(node, pos=pos, **kwargs)
            if pos:
                pos += 1
            append_operation_beep(node, pos=pos, **kwargs)
            if pos:
                pos += 1
            append_operation_interrupt(node, pos=pos, **kwargs)

        @self.tree_operation(_("Reload '%s'") % "{name}", node_type="file", help="")
        def reload_file(node, **kwargs):
            filepath = node.filepath
            node.remove_node()
            try:
                self.load(filepath)
            except BadFileError as e:
                self.context.signal("warning", str(e), _("File is Malformed"),)

        @self.tree_operation(
            _("Open in System: '{name}'"),
            node_type="file",
            help=_(
                "Open this file in the system application associated with this type of file"
            ),
        )
        def open_system_file(node, **kwargs):
            filepath = node.filepath
            normalized = os.path.realpath(filepath)

            import platform

            system = platform.system()
            if system == "Darwin":
                from os import system as open_in_shell

                open_in_shell("open '{file}'".format(file=normalized))
            elif system == "Windows":
                from os import startfile as open_in_shell

                open_in_shell('"{file}"'.format(file=normalized))
            else:
                from os import system as open_in_shell

                open_in_shell("xdg-open '{file}'".format(file=normalized))

        @self.tree_conditional(
            lambda node: isinstance(node.object, Shape)
            and not isinstance(node.object, Path)
        )
        @self.tree_operation(_("Convert to path"), node_type=("elem",), help="")
        def convert_to_path(node, copies=1, **kwargs):
            node.replace_object(abs(Path(node.object)))
            node.altered()

        @self.tree_submenu(_("Flip"))
        @self.tree_separator_before()
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(
            _("Horizontally"),
            node_type=("elem", "group", "file"),
            help=_("Mirror Horizontally"),
        )
        def mirror_elem(node, **kwargs):
            child_objects = Group()
            child_objects.extend(node.objects_of_children(SVGElement))
            bounds = child_objects.bbox()
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self.context("scale -1 1 %f %f\n" % (center_x, center_y))

        @self.tree_submenu(_("Flip"))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(
            _("Vertically"),
            node_type=("elem", "group", "file"),
            help=_("Flip Vertically"),
        )
        def flip_elem(node, **kwargs):
            child_objects = Group()
            child_objects.extend(node.objects_of_children(SVGElement))
            bounds = child_objects.bbox()
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self.context("scale 1 -1 %f %f\n" % (center_x, center_y))

        # @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Scale"))
        @self.tree_iterate("scale", 25, 1, -1)
        @self.tree_calc("scale_percent", lambda i: "%0.f" % (600.0 / float(i)))
        @self.tree_operation(
            _("Scale %s%%") % "{scale_percent}",
            node_type=("elem", "group", "file"),
            help=_("Scale Element"),
        )
        def scale_elem_amount(node, scale, **kwargs):
            scale = 6.0 / float(scale)
            child_objects = Group()
            child_objects.extend(node.objects_of_children(SVGElement))
            bounds = child_objects.bbox()
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self.context("scale %f %f %f %f\n" % (scale, scale, center_x, center_y))

        # @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Rotate"))
        @self.tree_values(
            "angle",
            (
                180,
                150,
                135,
                120,
                90,
                60,
                45,
                30,
                20,
                15,
                10,
                9,
                8,
                7,
                6,
                5,
                4,
                3,
                2,
                1,
                -1,
                -2,
                -3,
                -4,
                -5,
                -6,
                -7,
                -8,
                -9,
                -10,
                -15,
                -20,
                -30,
                -45,
                -60,
                -90,
                -120,
                -135,
                -150,
            ),
        )
        @self.tree_operation(
            _("Rotate %s°") % ("{angle}"), node_type=("elem", "group", "file"), help=""
        )
        def rotate_elem_amount(node, angle, **kwargs):
            turns = float(angle) / 360.0
            child_objects = Group()
            child_objects.extend(node.objects_of_children(SVGElement))
            bounds = child_objects.bbox()
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self.context("rotate %fturn %f %f\n" % (turns, center_x, center_y))

        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_operation(_("Make 1 copy"), node_type="elem", help="")
        def duplicate_element_1(node, **kwargs):
            duplicate_element_n(node, copies=1, **kwargs)

        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(
            _("Make %s copies") % "{copies}", node_type="elem", help=""
        )
        # TODO Make this duplicate elements in the group hierarchy
        def duplicate_element_n(node, copies, **kwargs):
            context = self.context
            elements = context.elements
            adding_elements = [
                copy(e) for e in list(self.elems(emphasized=True)) * copies
            ]
            elements.add_elems(adding_elements)
            elements.classify(adding_elements)
            elements.set_emphasis(None)

        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(
            _("Reify user changes"), node_type=("elem", "group", "file"), help=""
        )
        def reify_elem_changes(node, **kwargs):
            self.context("reify\n")

        @self.tree_conditional(lambda node: isinstance(node.object, Path))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(_("Break Subpaths"), node_type="elem", help="")
        def break_subpath_elem(node, **kwargs):
            self.context("element subpath\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(
            _("Reset user changes"),
            node_type=("branch elem", "elem", "group", "file"),
            help="",
        )
        def reset_user_changes(node, copies=1, **kwargs):
            self.context("reset\n")

        @self.tree_operation(
            _("Merge items"),
            node_type="group",
            help=_("Merge this node's children into 1 path."),
        )
        def merge_elements(node, **kwargs):
            self.context("element merge\n")

        def radio_match(node, i=0, **kwargs):
            if "raster_step" in node.object.values:
                step = float(node.object.values["raster_step"])
            else:
                step = 1.0
            if i == step:
                m = node.object.transform
                if m.a == step or m.b == 0.0 or m.c == 0.0 or m.d == step:
                    return True
            return False

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_separator_before()
        @self.tree_submenu(_("Step"))
        @self.tree_radio(radio_match)
        @self.tree_iterate("i", 1, 10)
        @self.tree_operation(_("Step %s") % "{i}", node_type="elem", help="")
        def set_step_n_elem(node, i=1, **kwargs):
            step_value = i
            element = node.object
            element.values["raster_step"] = str(step_value)
            m = element.transform
            tx = m.e
            ty = m.f
            element.transform = Matrix.scale(float(step_value), float(step_value))
            element.transform.post_translate(tx, ty)
            if hasattr(element, "node"):
                element.node.modified()
            self.context.signal("element_property_reload", node.object)
            self.context.signal("refresh_scene")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(_("Actualize pixels"), node_type="elem", help="")
        def image_actualize_pixels(node, **kwargs):
            self.context("image resample\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Z-depth divide"))
        @self.tree_iterate("divide", 2, 10)
        @self.tree_operation(
            _("Divide into %s images") % "{divide}", node_type="elem", help=""
        )
        def image_zdepth(node, divide=1, **kwargs):
            element = node.object
            if not isinstance(element, SVGImage):
                return
            if element.image.mode != "RGBA":
                element.image = element.image.convert("RGBA")
            band = 255 / divide
            for i in range(0, divide):
                threshold_min = i * band
                threshold_max = threshold_min + band
                self.context("image threshold %f %f\n" % (threshold_min, threshold_max))

        def is_locked(node):
            try:
                obj = node.object
                return obj.lock
            except AttributeError:
                return False

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_conditional(is_locked)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Unlock manipulations"), node_type="elem", help="")
        def image_unlock_manipulations(node, **kwargs):
            self.context("image unlock\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Dither to 1 bit"), node_type="elem", help="")
        def image_dither(node, **kwargs):
            self.context("image dither\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Invert image"), node_type="elem", help="")
        def image_invert(node, **kwargs):
            self.context("image invert\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Mirror horizontal"), node_type="elem", help="")
        def image_mirror(node, **kwargs):
            context("image mirror\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Flip vertical"), node_type="elem", help="")
        def image_flip(node, **kwargs):
            self.context("image flip\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Rotate 90° CW"), node_type="elem", help="")
        def image_cw(node, **kwargs):
            self.context("image cw\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Rotate 90° CCW"), node_type="elem", help="")
        def image_ccw(node, **kwargs):
            self.context("image ccw\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Save output.png"), node_type="elem", help="")
        def image_save(node, **kwargs):
            self.context("image save output.png\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("RasterWizard"))
        @self.tree_values(
            "script", values=list(self.context.match("raster_script", suffix=True))
        )
        @self.tree_operation(
            _("RasterWizard: %s") % "{script}", node_type="elem", help=""
        )
        def image_rasterwizard_open(node, script=None, **kwargs):
            self.context("window open RasterWizard %s\n" % script)

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Apply raster script"))
        @self.tree_values(
            "script", values=list(self.context.match("raster_script", suffix=True))
        )
        @self.tree_operation(_("Apply: %s") % "{script}", node_type="elem", help="")
        def image_rasterwizard_apply(node, script=None, **kwargs):
            self.context("image wizard %s\n" % script)

        @self.tree_conditional_try(lambda node: hasattr(node.object, "as_elements"))
        @self.tree_operation(_("Convert to SVG"), node_type="elem", help="")
        def cutcode_convert_svg(node, **kwargs):
            self.context.elements.add_elems(list(node.object.as_elements()))

        @self.tree_conditional_try(lambda node: hasattr(node.object, "generate"))
        @self.tree_operation(_("Process as Operation"), node_type="elem", help="")
        def cutcode_operation(node, **kwargs):
            self.context.elements.add_op(node.object)

        @self.tree_conditional(lambda node: len(node.children) > 0)
        @self.tree_separator_before()
        @self.tree_operation(
            _("Expand all children"),
            node_type=("op", "branch elems", "branch ops", "group", "file", "root"),
            help="Expand all children of this given node.",
        )
        def expand_all_children(node, **kwargs):
            node.notify_expand()

        @self.tree_conditional(lambda node: len(node.children) > 0)
        @self.tree_operation(
            _("Collapse all children"),
            node_type=("op", "branch elems", "branch ops", "group", "file", "root"),
            help="Collapse all children of this given node.",
        )
        def collapse_all_children(node, **kwargs):
            node.notify_collapse()

        @self.tree_reference(lambda node: node.object.node)
        @self.tree_operation(_("Element"), node_type="opnode", help="")
        def reference_opnode(node, **kwargs):
            pass

        self.listen(self)

    def detach(self, *a, **kwargs):
        self.save_persistent_operations("previous")
        self.unlisten(self)

    def boot(self, *a, **kwargs):
        self.context.setting(bool, "operation_default_empty", True)
        try:
            self.load_persistent_operations("previous")
        except ValueError:
            print("elements: Previous operation settings invalid: ValueError")
        ops = list(self.ops())
        if not len(ops) and self.context.operation_default_empty:
            self.load_default()
            return

    def save_persistent_operations(self, name):
        context = self.context
        settings = context.derive("operations/" + name)
        settings.clear_persistent()

        for i, op in enumerate(self.ops()):
            op_set = settings.derive("%06i" % i)
            if isinstance(op, LaserOperation):
                sets = op.settings
                for q in (op, sets):
                    for key in dir(q):
                        if key.startswith("_"):
                            continue
                        if key in [
                            "emphasized",
                            "highlighted",
                            "selected",
                            "targeted",
                        ]:
                            continue
                        if key.startswith("implicit"):
                            continue
                        value = getattr(q, key)
                        if value is None:
                            continue
                        if isinstance(value, Color):
                            value = value.argb
                        op_set.write_persistent(key, value)
            elif isinstance(op, CommandOperation) or isinstance(op, ConsoleOperation):
                for key in dir(op):
                    value = getattr(op, key)
                    if key.startswith("_"):
                        continue
                    if key in [
                        "emphasized",
                        "highlighted",
                        "selected",
                        "targeted",
                    ]:
                        continue
                    if value is None:
                        continue
                    op_set.write_persistent(key, value)
        settings.close_subpaths()

    def load_persistent_operations(self, name):
        self.clear_operations()
        settings = self.context.get_context("operations/" + name)
        subitems = list(settings.derivable())
        ops = [None] * len(subitems)
        for i, v in enumerate(subitems):
            op_setting_context = settings.derive(v)
            op_type = op_setting_context.get_persistent_value(str, "type")
            if op_type in ["op", ""]:
                op = LaserOperation()
                op_set = op.settings
                op_setting_context.load_persistent_object(op)
                op_setting_context.load_persistent_object(op_set)
                op.type = "op"
            elif op_type == "cmdop":
                name = op_setting_context.get_persistent_value(str, "label")
                command = op_setting_context.get_persistent_value(int, "command")
                op = CommandOperation(name, command)
                op_setting_context.load_persistent_object(op)
            elif op_type == "consoleop":
                command = op_setting_context.get_persistent_value(str, "command")
                op = ConsoleOperation(command)
                op_setting_context.load_persistent_object(op)
            else:
                continue
            try:
                ops[i] = op
            except (ValueError, IndexError):
                ops.append(op)
        self.add_ops([o for o in ops if o is not None])
        self.classify(list(self.elems()))

    def emphasized(self, *args):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None

    def altered(self, *args):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None

    def modified(self, *args):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None

    def listen(self, listener):
        self._tree.listen(listener)

    def unlisten(self, listener):
        self._tree.unlisten(listener)

    def add_element(self, element, stroke="black"):
        if (
            not isinstance(element, SVGText)
            and hasattr(element, "__len__")
            and len(element) == 0
        ):
            return  # No empty elements.
        context_root = self.context.root
        if hasattr(element, "stroke") and element.stroke is None:
            element.stroke = Color(stroke)
        node = context_root.elements.add_elem(element)
        context_root.elements.set_emphasis([element])
        node.focus()
        return node

    def load_default(self):
        self.clear_operations()
        self.add_op(
            LaserOperation(
                operation="Image",
                color="black",
                speed=140.0,
                power=1000.0,
                raster_step=3,
            )
        )
        self.add_op(LaserOperation(operation="Raster"))
        self.add_op(LaserOperation(operation="Engrave"))
        self.add_op(LaserOperation(operation="Cut"))
        self.classify(list(self.elems()))

    def load_default2(self):
        self.clear_operations()
        self.add_op(
            LaserOperation(
                operation="Image",
                color="black",
                speed=140.0,
                power=1000.0,
                raster_step=3,
            )
        )
        self.add_op(LaserOperation(operation="Raster"))
        self.add_op(LaserOperation(operation="Engrave", color="blue"))
        self.add_op(LaserOperation(operation="Engrave", color="green"))
        self.add_op(LaserOperation(operation="Engrave", color="magenta"))
        self.add_op(LaserOperation(operation="Engrave", color="cyan"))
        self.add_op(LaserOperation(operation="Engrave", color="yellow"))
        self.add_op(LaserOperation(operation="Cut"))
        self.classify(list(self.elems()))

    @property
    def op_branch(self):
        return self._tree.get(type="branch ops")

    @property
    def elem_branch(self):
        return self._tree.get(type="branch elems")

    def ops(self, **kwargs):
        operations = self._tree.get(type="branch ops")
        for item in operations.flat(
            types=("op", "cmdop", "consoleop"), depth=1, **kwargs
        ):
            yield item

    def elems(self, **kwargs):
        elements = self._tree.get(type="branch elems")
        for item in elements.flat(types=("elem",), **kwargs):
            yield item.object

    def elems_nodes(self, depth=None, **kwargs):
        elements = self._tree.get(type="branch elems")
        for item in elements.flat(
            types=("elem", "group", "file"), depth=depth, **kwargs
        ):
            yield item

    def top_element(self, **kwargs):
        """
        Returns the first matching node via a depth first search.
        """
        for e in self.elem_branch.flat(**kwargs):
            return e
        return None

    def first_element(self, **kwargs):
        """
        Returns the first matching element node via a depth first search. Elements must be type elem.
        """
        for e in self.elems(**kwargs):
            return e
        return None

    def has_emphasis(self):
        """
        Returns whether any element is emphasized
        """
        for e in self.elems_nodes(emphasized=True):
            return True
        return False

    def count_elems(self, **kwargs):
        return len(list(self.elems(**kwargs)))

    def count_op(self, **kwargs):
        return len(list(self.ops(**kwargs)))

    def get(self, obj=None, type=None):
        return self._tree.get(obj=obj, type=type)

    def get_op(self, index, **kwargs):
        for i, op in enumerate(self.ops(**kwargs)):
            if i == index:
                return op
        raise IndexError

    def get_elem(self, index, **kwargs):
        for i, elem in enumerate(self.elems(**kwargs)):
            if i == index:
                return elem
        raise IndexError

    def get_elem_node(self, index, **kwargs):
        for i, elem in enumerate(self.elems_nodes(**kwargs)):
            if i == index:
                return elem
        raise IndexError

    def add_op(self, op, pos=None):
        """
        Add an operation. Wraps it within a node, and appends it to the tree.

        :param element:
        :param classify: Should this element be automatically classified.
        :return:
        """
        operation_branch = self._tree.get(type="branch ops")
        op.set_label(str(op))
        operation_branch.add(op, type="op", pos=pos)

    def add_ops(self, adding_ops):
        operation_branch = self._tree.get(type="branch ops")
        items = []
        for op in adding_ops:
            op.set_label(str(op))
            operation_branch.add(op, type=op.type)
            items.append(op)
        return items

    def add_elem(self, element, classify=False):
        """
        Add an element. Wraps it within a node, and appends it to the tree.

        :param element:
        :param classify: Should this element be automatically classified.
        :return:
        """
        element_branch = self._tree.get(type="branch elems")
        node = element_branch.add(element, type="elem")
        self.context.signal("element_added", element)
        if classify:
            self.classify([element])
        return node

    def add_elems(self, adding_elements):
        element_branch = self._tree.get(type="branch elems")
        items = []
        for element in adding_elements:
            items.append(element_branch.add(element, type="elem"))
        self.context.signal("element_added", adding_elements)
        return items

    def clear_operations(self):
        operations = self._tree.get(type="branch ops")
        operations.remove_all_children()

    def clear_elements(self):
        elements = self._tree.get(type="branch elems")
        elements.remove_all_children()

    def clear_files(self):
        pass

    def clear_elements_and_operations(self):
        self.clear_elements()
        self.clear_operations()

    def clear_all(self):
        self.clear_elements()
        self.clear_operations()
        self.clear_files()
        self.clear_note()
        self.validate_selected_area()

    def clear_note(self):
        self.note = None

    def remove_nodes(self, node_list):
        for node in node_list:
            for n in node.flat():
                n._mark_delete = True
                for ref in list(n._references):
                    ref._mark_delete = True
        for n in reversed(list(self.flat())):
            if not hasattr(n, "_mark_delete"):
                continue
            if n.type in ("root", "branch elems", "branch ops"):
                continue
            n.remove_node(children=False, references=False)

    def remove_elements(self, elements_list):
        for elem in elements_list:
            for i, e in enumerate(self.elems()):
                if elem is e:
                    e.node.remove_node()
        self.remove_elements_from_operations(elements_list)
        self.validate_selected_area()

    def remove_operations(self, operations_list):
        for op in operations_list:
            for i, o in enumerate(list(self.ops())):
                if o is op:
                    o.remove_node()
            self.context.signal("operation_removed", op)

    def remove_elements_from_operations(self, elements_list):
        for i, op in enumerate(self.ops()):
            for e in list(op.children):
                for q in elements_list:
                    if q is e.object:
                        e.remove_node()
                        break

    def selected_area(self):
        if self._emphasized_bounds_dirty:
            self.validate_selected_area()
        return self._emphasized_bounds

    def validate_selected_area(self):
        boundary_points = []
        for e in self.elem_branch.flat(
            types="elem",
            emphasized=True,
        ):
            if e.bounds is None:
                continue
            box = e.bounds
            top_left = [box[0], box[1]]
            top_right = [box[2], box[1]]
            bottom_left = [box[0], box[3]]
            bottom_right = [box[2], box[3]]
            boundary_points.append(top_left)
            boundary_points.append(top_right)
            boundary_points.append(bottom_left)
            boundary_points.append(bottom_right)

        if len(boundary_points) == 0:
            new_bounds = None
        else:
            xmin = min([e[0] for e in boundary_points])
            ymin = min([e[1] for e in boundary_points])
            xmax = max([e[0] for e in boundary_points])
            ymax = max([e[1] for e in boundary_points])
            new_bounds = [xmin, ymin, xmax, ymax]
        self._emphasized_bounds_dirty = False
        if self._emphasized_bounds != new_bounds:
            self._emphasized_bounds = new_bounds
            self.context.signal("selected_bounds", self._emphasized_bounds)

    def highlight_children(self, node_context):
        """
        Recursively highlight the children.
        :param node_context:
        :return:
        """
        for child in node_context.children:
            child.highlighted = True
            self.highlight_children(child)

    def target_clones(self, node_context, node_exclude, object_search):
        """
        Recursively highlight the children.

        :param node_context: context node to search from
        :param node_exclude: excluded nodes
        :param object_search: Specific searched for object.
        :return:
        """
        for child in node_context.children:
            self.target_clones(child, node_exclude, object_search)
            if child is node_exclude:
                continue
            if child.object is None:
                continue
            if object_search is child.object:
                child.targeted = True

    def set_selected(self, selected):
        """
        Selected is the sublist of specifically selected nodes.
        """
        for s in self._tree.flat():
            in_list = selected is not None and (
                s in selected or (hasattr(s, "object") and s.object in selected)
            )
            if s.selected:
                if not in_list:
                    s.selected = False
            else:
                if in_list:
                    s.selected = True
        if selected is not None:
            for e in selected:
                e.selected = True

    def set_emphasis(self, emphasize):
        """
        If any operation is selected, all sub-operations are highlighted.
        If any element is emphasized, all copies are highlighted.
        If any element is emphasized, all operations containing that element are targeted.
        """
        for s in self._tree.flat():
            if s.highlighted:
                s.highlighted = False
            if s.targeted:
                s.targeted = False

            in_list = emphasize is not None and (
                s in emphasize or (hasattr(s, "object") and s.object in emphasize)
            )
            if s.emphasized:
                if not in_list:
                    s.emphasized = False
            else:
                if in_list:
                    s.emphasized = True
        if emphasize is not None:
            for e in emphasize:
                e.emphasized = True
                if hasattr(e, "object"):
                    self.target_clones(self._tree, e, e.object)
                if hasattr(e, "node"):
                    e = e.node
                self.highlight_children(e)

    def center(self):
        bounds = self._emphasized_bounds
        return (bounds[2] + bounds[0]) / 2.0, (bounds[3] + bounds[1]) / 2.0

    def ensure_positive_bounds(self):
        b = self._emphasized_bounds
        if b is None:
            return
        self._emphasized_bounds = [
            min(b[0], b[2]),
            min(b[1], b[3]),
            max(b[0], b[2]),
            max(b[1], b[3]),
        ]
        self.context.signal("selected_bounds", self._emphasized_bounds)

    def update_bounds(self, b):
        self._emphasized_bounds = [b[0], b[1], b[2], b[3]]
        self.context.signal("selected_bounds", self._emphasized_bounds)

    def move_emphasized(self, dx, dy):
        for obj in self.elems(emphasized=True):
            obj.transform.post_translate(dx, dy)
            obj.node.modified()

    def set_emphasized_by_position(self, position):
        def contains(box, x, y=None):
            if y is None:
                y = x[1]
                x = x[0]
            return box[0] <= x <= box[2] and box[1] <= y <= box[3]

        if self.has_emphasis():
            if self._emphasized_bounds is not None and contains(
                self._emphasized_bounds, position
            ):
                return  # Select by position aborted since selection position within current select bounds.
        for e in self.elems_nodes(depth=1, cascade=False):
            try:
                bounds = e.bounds
            except AttributeError:
                continue  # No bounds.
            if bounds is None:
                continue
            if contains(bounds, position):
                e_list = [e]
                self._emphasized_bounds = bounds
                self.set_emphasis(e_list)
                return
        self._emphasized_bounds = None
        self.set_emphasis(None)

    def classify_legacy(self, elements, operations=None, add_op_function=None):
        """
        Classify does the placement of elements within operations.
        "Image" is the default for images.
        Typically,
        If element strokes are red they get classed as cut operations
        If they are otherwise they get classed as engrave.
        However, this differs based on the ops in question.
        :param elements: list of elements to classify.
        :param operations: operations list to classify into.
        :param add_op_function: function to add a new operation, because of a lack of classification options.
        :return:
        """
        if elements is None:
            return

        # Use of Classify in reverse is new functionality in 0.7.1
        # So using it is incompatible, but not using it would be inconsistent
        # Perhaps classify_reverse should be cleared and disabled if classify_legacy is set.
        reverse = self.context.classify_reverse
        if reverse:
            elements = reversed(elements)
        if operations is None:
            operations = list(self.ops())
        if add_op_function is None:
            add_op_function = self.add_op
        for element in elements:
            # Following lines added to handle 0.7 special ops added to ops list
            if hasattr(element, "operation"):
                add_op_function(element)
                continue
            # Following lines added that are not in 0.6
            if element is None:
                continue
            was_classified = False
            # image_added code removed because it could never be used
            for op in operations:
                if op.operation == "Raster" and not op.default:
                    if element.stroke is not None and op.color == abs(element.stroke):
                        op.add(element, type="opnode")
                        was_classified = True
                    elif isinstance(element, SVGImage):
                        op.add(element, type="opnode")
                        was_classified = True
                    elif isinstance(element, SVGText):
                        op.add(element)
                        was_classified = True
                    elif element.fill is not None and element.fill.argb is not None:
                        op.add(element, type="opnode")
                        was_classified = True
                elif (
                    op.operation in ("Engrave", "Cut")
                    and element.stroke is not None
                    and op.color == abs(element.stroke)
                    and not op.default
                ):
                    op.add(element, type="opnode")
                    was_classified = True
                elif op.operation == "Image" and isinstance(element, SVGImage):
                    op.add(element, type="opnode")
                    was_classified = True
                    break  # May only classify in one image operation.
                elif op.operation == "Dots" and isDot(element):
                    op.add(element, type="opnode")
                    was_classified = True
                    break  # May only classify in Dots.

            if not was_classified:
                # Additional code over and above 0.6.23 to add new DISABLED operations
                # so that all elements are classified.
                # This code definitely classifies more elements, and should classify all, however
                # it is not guaranteed to classify all elements as this is not explicitly checked.
                op = None
                if isinstance(element, SVGImage):
                    op = LaserOperation(operation="Image", output=False)
                elif isDot(element):
                    op = LaserOperation(operation="Dots", output=False)
                elif (
                    # test for Shape or SVGText instance is probably unnecessary,
                    # but we should probably not test for stroke without ensuring
                    # that the object has a stroke attribute.
                    isinstance(element, (Shape, SVGText))
                    and element.stroke is not None
                    and element.stroke.value is not None
                ):
                    op = LaserOperation(
                        operation="Engrave", color=element.stroke, speed=35.0
                    )
                # This code is separated out to avoid duplication
                if op is not None:
                    add_op_function(op)
                    op.add(element, type="opnode")
                    operations.append(op)

                # Seperate code for Raster ops because we might add a Raster op
                # and a vector op for same element.
                if (
                    isinstance(element, (Shape, SVGText))
                    and element.fill is not None
                    and element.fill.argb is not None
                    and not isDot(element)
                ):
                    op = LaserOperation(operation="Raster", color=0, output=False)
                    add_op_function(op)
                    op.add(element, type="opnode")
                    operations.append(op)

    def add_classify_op(self, op):
        """
        Ops are added as part of classify as elements are iterated that need a new op.
        Rather than add them at the end, creating a random sequence of Engrave and Cut operations
        perhaps with an Image or Raster or Dots operation in there as well, instead  we need to try
        to group operations together, adding the new operation:
        1. After the last operation of the same type if one exists; or if not
        2. After the last operation of the highest priority existing operation (where Dots is the lowest priority and Cut is the highest.
        """
        operations = self._tree.get(type="branch ops").children
        for pos, old_op in reversed_enumerate(operations):
            if op.operation == old_op.operation:
                return self.add_op(op, pos=pos + 1)

        # No operation of same type found. So we will look for last operation of a lower priority and add after it.
        try:
            priority = OP_PRIORITIES.index(op.operation)
        except ValueError:
            return self.add_op(op)

        for pos, old_op in reversed_enumerate(operations):
            try:
                if OP_PRIORITIES.index(old_op.operation) < priority:
                    return self.add_op(op, pos=pos + 1)
            except ValueError:
                pass
        return self.add_op(op, pos=0)

    def classify(self, elements, operations=None, add_op_function=None):
        """
        Classify does the placement of elements within operations.

        SVGImage is classified as Image.
        Dots are a special type of Path
        All other SVGElement types are Shapes / Text

        Paths consisting of a move followed by a single stright line segment are never Raster (since no width) -
            testing for more complex stright line elements is too difficult
        Shapes/Text with Fill are raster by default
        Shapes/Text with Black strokes are raster by default regardless of fill
        All other Shapes/Text with no fill are vector by default

        RASTER ELEMENTS
        Because rastering of overlapping elements depends on the sequence of the elements
        (think of the difference between a white fill above or below a black fill)
        it is essential that raster elements are added to operations in the same order that they exist
        in the file/elements branch.

        Raster elements are handled differently depending on whether existing Raster operations are simple or complex:
            1. Simple - all existing raster ops have the same color (default being a different colour to any other); or
            2. Complex - there are existing raster ops of two different colors (default being a different colour to any other)

        Simple - Raster elements are matched immediately to all Raster operations in the correct sequence.
        Complex - Raster elements are saved for processing in a more complex second pass (see below)

        VECTOR ELEMENTS
        Vector Shapes/Text are attempted to match to Cut/Engrave/Raster operations of exact same color (regardless of default raster or vector)

        If not matched to exact colour, vector elements are classified based on colour:
            1. Redish strokes are considered cuts
            2. Other colours are considered engraves
        If a default Cut/Engrave operation exists then the element is classified to it.
        Otherwise a new operation of matching color and type is created.
        New White Engrave operations are created disabled by default.

        SIMPLE RASTER CLASSIFICATION
        All existing raster ops are of the same color (or there are no existing raster ops)

        In this case all raster operations will be assigned either to:
            A. all existing raster ops (if there are any); or
            B. to a new Default Raster operation we create in a similar way as vector elements

        Because raster elements are all added to the same operations in pass 1 and without being grouped,
        retaining the sequence of elements happens by default, and no special handling is needed.

        (Note: Not true for later classification of single elements due to e.g. colour change. See below.)

        COMPLEX RASTER CLASSIFICATION
        There are existing raster ops of at least 2 different colours.

        In this case we are going to try to match raster elements to raster operations by colour.
        But this is complicated becausewe need to keep overlapping raster elements together.

        So in this case we classify vector and special elements in a first pass,
        and then analyse and classify raster operations in a special second pass.

        Because we have to analyse all raster elements together, when you load a new file
        classify has to be called once with all elements in the file rather than on an element-by-element basis.

        In the second pass, we do the following:

        1.  Group rasters by whether they have overlapping bounding boxes.
            After this, if rasters are in separate groups then they are in entirely separate areas of the burn which do not overlap.

            Note: It is difficult to ensure that elements are retained in the sequence when doing iterative grouping.
            To avoid the complexities, before adding to the raster operations, we sort back into the original element sequence.

        2.  For each group of raster objects, determine whether there are existing Raster operations
            of the same colour as at least one element in the group.
            If any element in a group matches the color of an operation, then
            all the raster elements of the group will be added to that operation.

        3.  If there are any raster elements that are not classified in this way, then:
            A)  If there are Default Raster Operation(s), then the remaining raster elements are allocated to those.
            B)  Otherwise, if there are any non-default raster operations that are empty and those raster operations are all of the same colour,
                then the remaining raster operations will be allocated to those Raster operations.
            C)  Otherwise, a new Default Raster operation will be created and remaining Raster elements will be added to that.

        The current code does NOT do the following:

        a.  Handle rasters in second or later files which overlap elements from earlier files which have already been classified into operations.
            It is assumed that if they happen to overlap that is coincidence. After all the files could have been added in a different order and
            then would have a different result.
        b.  Handle the reclassifications of single elements which have e.g. had their colour changed any differently.
            (The multitude of potential use cases are many and varied, and difficult or impossible comprehensively to predict.)

        It may be that we will need to:

        1.  Use the total list of Shape / Text elements loaded in the Elements Branch sequence to keep elements in the correct sequence in an operation.
        2.  Handle cases where the user resequences elements by ensuring that a drag and drop of elements in the Elements branch of the tree
            are reflected in the sequence in Operations and vice versa. This could, however, get messy.


        :param elements: list of elements to classify.
        :param operations: operations list to classify into.
        :param add_op_function: function to add a new operation, because of a lack of classification options.
        :return:
        """
        if self.context.legacy_classification:
            self.classify_legacy(elements, operations, add_op_function)
            return

        if elements is None:
            return
        if operations is None:
            operations = list(self.ops())
        if add_op_function is None:
            add_op_function = self.add_classify_op

        reverse = self.context.classify_reverse
        # If reverse then we insert all elements into operations at the beginning rather than appending at the end
        # EXCEPT for Rasters which have to be in the correct sequence.
        element_pos = 0 if reverse else None

        vector_ops = []
        raster_ops = []
        special_ops = []
        new_ops = []
        default_cut_ops = []
        default_engrave_ops = []
        default_raster_ops = []
        rasters_one_pass = None

        for op in operations:
            if not isinstance(op, LaserOperation):
                continue
            if op.default:
                if op.operation == "Cut":
                    default_cut_ops.append(op)
                if op.operation == "Engrave":
                    default_engrave_ops.append(op)
                if op.operation == "Raster":
                    default_raster_ops.append(op)
            if op.operation in ("Cut", "Engrave"):
                vector_ops.append(op)
            elif op.operation == "Raster":
                raster_ops.append(op)
                op_color = op.color.rgb if not op.default else "default"
                if rasters_one_pass is not False:
                    if rasters_one_pass is not None:
                        if str(rasters_one_pass) != str(op_color):
                            rasters_one_pass = False
                    else:
                        rasters_one_pass = op_color
            else:
                special_ops.append(op)
        if rasters_one_pass is not False:
            rasters_one_pass = True

        raster_elements = []
        for element in elements:
            if element is None:
                continue
            if hasattr(element, "operation"):
                add_op_function(element)
                continue

            element_color = self.element_classify_color(element)
            if isinstance(element, (Shape, SVGText)) and (
                element_color is None or element_color.rgb is None
            ):
                continue
            is_dot = isDot(element)
            is_straight_line = isStraightLine(element)

            # Check for default vector operations
            element_vector = False
            # print(element.stroke, element.fill, element.fill.alpha, is_straight_line, is_dot)
            if isinstance(element, (Shape, SVGText)) and not is_dot:
                # Vector if not filled
                if (
                    element.fill is None
                    or element.fill.rgb is None
                    or (element.fill.alpha is not None and element.fill.alpha == 0)
                    or is_straight_line
                ):
                    element_vector = True

                # Not vector if black stroke or stroke same color as fill
                if (
                    element_vector
                    and not is_straight_line
                    and element.stroke is not None
                    and element.stroke.rgb is not None
                    and (
                        # Grey
                        (
                            element.stroke.red == element.stroke.green
                            and element.stroke.red == element.stroke.blue
                        )
                        # Same color as fill
                        or (
                            element.fill is not None
                            and element.fill.rgb is not None
                            and element.fill.alpha is not None
                            and element.fill.alpha > 0
                            and element.fill.rgb != element.stroke.rgb
                        )
                    )
                ):
                    element_vector = False

            element_added = False
            if is_dot or isinstance(element, SVGImage):
                for op in special_ops:
                    if (is_dot and op.operation == "Dots") or (
                        isinstance(element, SVGImage) and op.operation == "Image"
                    ):
                        op.add(element, type="opnode", pos=element_pos)
                        element_added = True
                        break  # May only classify in one Dots or Image operation and indeed in one operation
            elif element_vector:
                for op in vector_ops:
                    if (
                        op.color is not None
                        and op.color.rgb == element_color.rgb
                        and op not in default_cut_ops
                        and op not in default_engrave_ops
                    ):
                        op.add(element, type="opnode", pos=element_pos)
                        element_added = True
                # Vector op (i.e. no fill) with exact colour match can be added out of sequence
                for op in raster_ops:
                    if (
                        op.color is not None
                        and op.color.rgb == element_color.rgb
                        and op not in default_raster_ops
                    ):
                        op.add(element, type="opnode", pos=element_pos)
                        element_added = True
            elif rasters_one_pass:
                for op in raster_ops:
                    # New Raster ops are always default so excluded
                    if (
                        op.color is not None
                        and op.color.rgb == element_color.rgb
                        and op not in default_raster_ops
                    ):
                        op.add(element, type="opnode", pos=element_pos)
                        element_added = True

            if element_added:
                continue

            if element_vector:
                is_cut = Color.distance_sq("red", element_color) <= 18825
                if is_cut and default_cut_ops:
                    for op in default_cut_ops:
                        op.add(element, type="opnode", pos=element_pos)
                    element_added = True
                elif not is_cut and default_engrave_ops:
                    for op in default_engrave_ops:
                        op.add(element, type="opnode", pos=element_pos)
                    element_added = True
            elif (
                rasters_one_pass
                and isinstance(element, (Shape, SVGText))
                and not is_dot
                and raster_ops
            ):
                for op in raster_ops:
                    op.add(element, type="opnode", pos=element_pos)
                element_added = True

            if element_added:
                continue

            # Need to add a new operation to classify into
            op = None
            if is_dot:
                op = LaserOperation(operation="Dots", default=True)
                special_ops.append(op)
            elif isinstance(element, SVGImage):
                op = LaserOperation(operation="Image", default=True)
                special_ops.append(op)
            elif isinstance(element, (Shape, SVGText)):
                if element_vector:
                    if (
                        is_cut
                    ):  # This will be initialised because criteria are same as above
                        op = LaserOperation(operation="Cut", color=abs(element_color))
                    else:
                        op = LaserOperation(
                            operation="Engrave", color=abs(element_color)
                        )
                        if element_color == Color("white"):
                            op.output = False
                    vector_ops.append(op)
                elif rasters_one_pass:
                    op = LaserOperation(
                        operation="Raster", color="Transparent", default=True
                    )
                    default_raster_ops.append(op)
                    raster_ops.append(op)
                else:
                    raster_elements.append(element)
            if op:
                new_ops.append(op)
                add_op_function(op)
                # element cannot be added to op before op is added to operations - otherwise opnode is not created.
                op.add(element, type="opnode", pos=element_pos)
                continue

        # End loop "for element in elements"

        if rasters_one_pass:
            return

        # Now deal with two-pass raster elements
        # It is ESSENTIAL that elements are added to operations in the same order as original.
        # The easiest way to ensure this is to create groups using a copy of raster_elements and
        # then ensure that groups have elements in the same order as in raster_elements.

        # Debugging print statements have been left in as comments as this code can
        # be complex to debug and even print statements can be difficult to craft

        # This is a list of groups, where each group is a list of tuples, each an element and its bbox.
        # Initial list has a separate group for each element.
        raster_groups = group_overlapped_rasters(
            [(e, e.bbox()) for e in raster_elements]
        )

        # Remove bbox and add element colour from groups
        # Change list to groups which are a list of tuples, each tuple being element and its classification color
        raster_groups = list(
            map(
                lambda g: tuple(((e[0], self.element_classify_color(e[0])) for e in g)),
                raster_groups,
            )
        )

        # print("grouped", list(map(lambda g: list(map(lambda e: e[0].id,g)), raster_groups)))

        # Add groups to operations of matching colour (and remove from list)
        # groups added to at least one existing raster op will not be added to default raster ops.
        groups_added = []
        for op in raster_ops:
            if (
                op not in default_raster_ops
                and op.color is not None
                and op.color.rgb is not None
            ):
                # Make a list of elements to add (same tupes)
                elements_to_add = []
                for group in raster_groups:
                    for e in group:
                        if e[1].hex == op.color.hex:
                            # An element in this group matches op color
                            # So add elements to list
                            elements_to_add.extend(group)
                            if group not in groups_added:
                                groups_added.append(group)
                            break  # to next group
                if elements_to_add:
                    # Create simple list of elements sorted by original element order
                    elements_to_add = sorted(
                        (e[0] for e in elements_to_add), key=raster_elements.index
                    )
                    for element in elements_to_add:
                        op.add(element, type="opnode", pos=element_pos)

        # Now remove groups added to at least one op
        for group in groups_added:
            raster_groups.remove(group)

        if not raster_groups:  # added all groups
            return

        #  Because groups don't matter further simplify back to a simple element_list
        elements_to_add = []
        for g in raster_groups:
            elements_to_add.extend(g)
        elements_to_add = sorted(
            (e[0] for e in elements_to_add), key=raster_elements.index
        )

        # Remaining elements are added to one of the following groups of operations:
        # 1. to default raster ops if they exist; otherwise
        # 2. to empty raster ops if they exist and are all of same color; otherwise to
        # 3. a new default Raster operation.
        if not default_raster_ops:
            # Because this is a check for an empty operation, this functionality relies on all elements being classified at the same time.
            # If you add elements individually, after the first raster operation the empty ops will no longer be empty and a default Raster op will be created instead.
            default_raster_ops = [op for op in raster_ops if len(op.children) == 0]
            color = False
            for op in default_raster_ops:
                if op.color is None or op.color.rgb is None:
                    op_color = "None"
                else:
                    op_color = op.color.rgb
                if color is False:
                    color = op_color
                elif color != op_color:
                    default_raster_ops = []
                    break
        if not default_raster_ops:
            op = LaserOperation(operation="Raster", color="Transparent", default=True)
            default_raster_ops.append(op)
            add_op_function(op)
        for element in elements_to_add:
            for op in default_raster_ops:
                op.add(element, type="opnode", pos=element_pos)

    def element_classify_color(self, element: SVGElement):
        element_color = element.stroke
        if element_color is None or element_color.rgb is None:
            element_color = element.fill
        return element_color

    def load(self, pathname, **kwargs):
        kernel = self.context.kernel
        for loader_name in kernel.match("load"):
            loader = kernel.registered[loader_name]
            for description, extensions, mimetype in loader.load_types():
                if str(pathname).lower().endswith(extensions):
                    try:
                        results = loader.load(self.context, self, pathname, **kwargs)
                    except FileNotFoundError:
                        return False
                    except OSError:
                        return False
                    if results:
                        self.context("scene focus -4% -4% 104% 104%\n")
                        return True
        return False

    def load_types(self, all=True):
        kernel = self.context.kernel
        _ = kernel.translation
        filetypes = []
        if all:
            filetypes.append(_("All valid types"))
            exts = []
            for loader_name in kernel.match("load"):
                loader = kernel.registered[loader_name]
                for description, extensions, mimetype in loader.load_types():
                    for ext in extensions:
                        exts.append("*.%s" % ext)
            filetypes.append(";".join(exts))
        for loader_name in kernel.match("load"):
            loader = kernel.registered[loader_name]
            for description, extensions, mimetype in loader.load_types():
                exts = []
                for ext in extensions:
                    exts.append("*.%s" % ext)
                filetypes.append("%s (%s)" % (description, extensions[0]))
                filetypes.append(";".join(exts))
        return "|".join(filetypes)

    def save(self, pathname):
        kernel = self.context.kernel
        for save_name in kernel.match("save"):
            saver = kernel.registered[save_name]
            for description, extension, mimetype in saver.save_types():
                if pathname.lower().endswith(extension):
                    saver.save(self.context, pathname, "default")
                    return True
        return False

    def save_types(self):
        kernel = self.context.kernel
        filetypes = []
        for save_name in kernel.match("save"):
            saver = kernel.registered[save_name]
            for description, extension, mimetype in saver.save_types():
                filetypes.append("%s (%s)" % (description, extension))
                filetypes.append("*.%s" % extension)
        return "|".join(filetypes)
