import functools
import re
from copy import copy

from ..device.lasercommandconstants import (
    COMMAND_BEEP,
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
from ..kernel import Modifier
from ..svgelements import (
    SVG_STRUCT_ATTRIB,
    Angle,
    Circle,
    Close,
    Color,
    CubicBezier,
    Ellipse,
    Group,
    Length,
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
label_truncate_re = re.compile("((:|\().*)")
group_simplify_re = re.compile("(\([^()]+?\))|(SVG(?=Image|Text))|(Simple(?=Line))", re.IGNORECASE)
subgroup_simplify_re = re.compile("\[[^][]*\]", re.IGNORECASE)
# I deally we would show the positions in the same UoM as set in Settings (with variable precision depending on UoM,
# but until then element descriptions are shown in mils and integer values should be sufficient for user to see
# element_simplify_re = re.compile("(^Simple(?=Line))|((?<=\.\d{2})(\d+))", re.IGNORECASE)
element_simplify_re = re.compile("(^Simple(?=Line))|((?<=\d)(\.\d*))", re.IGNORECASE)
# image_simplify_re = re.compile("(^SVG(?=Image))|((,\s*)?href=('|\")data:.*?('|\")(,\s?|\s|(?=\))))|((?<=\.\d{2})(\d+))", re.IGNORECASE)
image_simplify_re = re.compile("(^SVG(?=Image))|((,\s*)?href=('|\")data:.*?('|\")(,\s?|\s|(?=\))))|((?<=\d)(\.\d*))", re.IGNORECASE)

OP_PRIORITIES = ["Dots","Image","Raster","Engrave","Cut"]

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

        self._emphasized = False
        self._highlighted = False
        self._target = False

        self._opened = False

        self._bounds = None
        self._bounds_dirty = True
        self.label = None

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
                # Dragging element into operation adds that element to the op.
                drop_node.add(drag_node.object, type="opnode", pos=0)
                return True
            elif drop_node.type == "opnode":
                drop_index = drop_node.parent.children.index(drop_node)
                drop_node.parent.add(drag_node.object, type="opnode", pos=drop_index)
                return True
            elif drop_node.type == "group":
                drop_node.append_child(drag_node)
                return True
        elif drag_node.type == "opnode":
            if drop_node.type == "op":
                drop_node.append_child(drag_node)
                return True
            if drop_node.type == "opnode":
                drop_node.insert_sibling(drag_node)
                return True
        elif drag_node.type == "cmdop":
            if drop_node.type == "op" or drop_node.type == "cmdop":
                drop_node.insert_sibling(drag_node)
        elif drag_node.type == "op":
            if drop_node.type == "op":
                # Dragging operation to different operation.
                drop_node.insert_sibling(drag_node)
                return True
            elif drop_node.type == "branch ops":
                # Dragging operation to op branch.
                drop_node.append_child(drag_node)
        elif drag_node.type in "file":
            if drop_node.type == "op":
                for e in drag_node.flat("elem"):
                    drop_node.add(e.object, type="opnode")
                return True
        elif drag_node.type == "group":
            if drop_node.type == "elem":
                drop_node.insert_sibling(drag_node)
                return True
            elif drop_node.type in ("group", "file"):
                drop_node.append_child(drag_node)
                return True
            elif drop_node.type == "op":
                for e in drag_node.flat("elem"):
                    drop_node.add(e.object, type="opnode")
                return True

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
        self._target = value
        self.notify_targeted(self)

    @property
    def highlighted(self):
        return self._highlighted

    @highlighted.setter
    def highlighted(self, value):
        self._highlighted = value
        self.notify_highlighted(self)

    @property
    def emphasized(self):
        return self._emphasized

    @emphasized.setter
    def emphasized(self, value):
        self._emphasized = value
        self.notify_emphasized(self)

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
                assert(not c._bounds_dirty)
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

    def modified(self):
        """
        The matrix transformation was changed. The object is shaped differently but fundamentally the same structure of
        data.
        """
        self._bounds_dirty = True
        self._bounds = None
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
        self._bounds = None
        self._bounds_dirty = True
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
            if isinstance(element,Path):
                desc = element_simplify_re.sub("", desc)
                if len(desc) > 100:
                    desc = desc[:100] + "…"
                values = []
                if element.stroke is not None:
                    values.append("%s='%s'" % ("stroke", element.stroke))
                if element.fill is not None:
                    values.append("%s='%s'" % ("fill", element.fill))
                if element.stroke_width is not None and element.stroke_width != 1.0:
                    values.append("%s=%s" % ("stroke-width", str(element.stroke_width)))
                if not element.transform.is_identity():
                    values.append("%s=%s" % ("transform", repr(element.transform)))
                if element.id is not None:
                    values.append("%s='%s'" % ("id", element.id))
                if values:
                    desc = "d='%s', %s" % (desc, ", ".join(values))
                desc = element_type + "(" + desc + ")"
            elif element_type == "Group": # Group
                desc = desc[1:-1] # strip leading and trailing []
                n = 1
                while n:
                    desc, n = group_simplify_re.subn("", desc)
                n = 1
                while n:
                    desc, n = subgroup_simplify_re.subn("Group", desc)
                desc = "%s(%s)" % (element_type, desc)
            elif element_type == "Image": # Image
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
            return attribs["{http://www.inkscape.org/namespaces/inkscape}label"] + (": " + desc if desc else "")
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
        :param emphasized: match only emphasized nodes.
        :param targeted: match only targeted nodes
        :param highlighted: match only highlighted nodes
        :return:
        """
        node = self
        if (
            (targeted is None or targeted == node.targeted)
            and (emphasized is None or emphasized == node.emphasized)
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
            for q in c.flat(types, cascade, depth, emphasized, targeted, highlighted):
                yield q

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

    def remove_node(self):
        """
        Remove the current node from the tree.

        This function must iterate down and first remove all children from the bottom.
        """
        self.remove_all_children()
        self._parent._children.remove(self)
        self.notify_detached(self)
        self.notify_destroyed(self)
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
                    first = obj.first_point
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

    def as_cutobjects(self, closed_distance=15):
        """
        Generator of cutobjects for a particular operation.
        """
        settings = self.settings

        if self._operation in ("Cut", "Engrave"):
            for object_path in self.children:
                object_path = object_path.object
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
                    closed = isinstance(sp, Close) or abs(sp.z_point - sp.current_point) <= closed_distance
                    group = CutGroup(None, closed=closed)
                    group.path = Path(subpath)
                    group.original_op = self._operation
                    for seg in subpath:
                        if isinstance(seg, Move):
                            pass  # Move operations are ignored.
                        elif isinstance(seg, Close):
                            if seg.start != seg.end:
                                group.append(
                                    LineCut(seg.start, seg.end, settings=settings)
                                )
                        elif isinstance(seg, Line):
                            if seg.start != seg.end:
                                group.append(
                                    LineCut(seg.start, seg.end, settings=settings)
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
                    yield group
        elif self._operation == "Raster":
            direction = settings.raster_direction
            settings.crosshatch = False
            if direction == 4:
                cross_settings = LaserSettings(settings)
                cross_settings.crosshatch = True
                for object_image in self.children:
                    object_image = object_image.object
                    box = object_image.bbox()
                    path = Path(
                        Polygon(
                            (box[0], box[1]),
                            (box[0], box[3]),
                            (box[2], box[3]),
                            (box[2], box[1]),
                        )
                    )
                    cut = RasterCut(object_image, settings)
                    cut.path = path
                    cut.original_op = self._operation
                    yield cut
                    cut = RasterCut(object_image, cross_settings)
                    cut.path = path
                    cut.original_op = self._operation
                    yield cut
            else:
                for object_image in self.children:
                    object_image = object_image.object
                    box = object_image.bbox()
                    path = Path(
                        Polygon(
                            (box[0], box[1]),
                            (box[0], box[3]),
                            (box[2], box[3]),
                            (box[2], box[1]),
                        )
                    )
                    cut = RasterCut(object_image, settings)
                    cut.path = path
                    cut.original_op = self._operation
                    yield cut
        elif self._operation == "Image":
            for object_image in self.children:
                object_image = object_image.object
                box = object_image.bbox()
                path = Path(
                    Polygon(
                        (box[0], box[1]),
                        (box[0], box[3]),
                        (box[2], box[3]),
                        (box[2], box[1]),
                    )
                )
                settings = LaserSettings(self.settings)
                try:
                    settings.raster_step = int(object_image.values["raster_step"])
                except KeyError:
                    settings.raster_step = 1

                cut = RasterCut(object_image, settings)
                cut.path = path
                cut.original_op = self._operation
                yield cut

                if settings.raster_direction == 4:
                    cross_settings = LaserSettings(settings)
                    cross_settings.crosshatch = True

                    cut = RasterCut(object_image, cross_settings)
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


class CommandOperation(Node):
    """
    CommandOperation is a basic command operation. It contains nothing except a single command to be executed.

    Node type "cmdop"
    """

    def __init__(self, name, command, *args, **kwargs):
        super().__init__(command, type="cmdop")
        self.label = name
        self.command = command
        self.args = args
        self.output = True
        self.operation = "Command"

    def __repr__(self):
        return "CommandOperation('%s', '%s')" % (self.label, str(self.command))

    def __str__(self):
        return "%s: %s" % (self.label, str(self.args))

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
            "lasercode": LaserCodeNode,
            "group": GroupNode,
            "elem": ElemNode,
            "opnode": OpNode,
            "cutcode": CutNode,
        }
        self.add(type="branch ops", label="Operations")
        self.add(type="branch elems", label="Elements")

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
        if node is None:
            node = self
        self._bounds = None
        for listen in self.listeners:
            if hasattr(listen, "modified"):
                listen.modified(node, **kwargs)

    def notify_altered(self, node=None, **kwargs):
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
        for e in self._tree.flat(**kwargs):
            yield e

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

    def tree_operation(self, name, node_type=None, help=None, **kwargs):
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
                    raise NameError("A function of this name was already registered: %s" % p)
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

        # ==========
        # OPERATION BASE
        # ==========
        @context.console_command(
            "operations", help=_("Show information about operations")
        )
        def element(**kwgs):
            context(".operation* list\n")

        @context.console_command(
            "operation.*", help=_("operation.*: selected operations"), output_type="ops"
        )
        def operation(**kwgs):
            return "ops", list(self.ops(emphasized=True))

        @context.console_command(
            "operation*", help=_("operation*: all operations"), output_type="ops"
        )
        def operation(**kwgs):
            return "ops", list(self.ops())

        @context.console_command(
            "operation~",
            help=_("operation~: non selected operations."),
            output_type="ops",
        )
        def operation(**kwgs):
            return "ops", list(self.ops(emphasized=False))

        @context.console_command(
            "operation", help=_("operation: selected operations."), output_type="ops"
        )
        def operation(**kwgs):
            return "ops", list(self.ops(emphasized=True))

        @context.console_command(
            r"operation([0-9]+,?)+",
            help=_("operation0,2: operation #0 and #2"),
            regex=True,
            output_type="ops",
        )
        def operation(command, channel, _, **kwgs):
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
        def save_operations(command, channel, _, data=None, name=None, **kwgs):
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
        def load_operations(name=None, **kwgs):
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
        def operation_select(data=None, **kwgs):
            self.set_emphasis(data)
            return "ops", data

        @context.console_command(
            "select+",
            help=_("Add the input to the selection"),
            input_type="ops",
            output_type="ops",
        )
        def operation_select_plus(data=None, **kwgs):
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
        def operation_select_minus(data=None, **kwgs):
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
        def operation_select_xor(data=None, **kwgs):
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
        def operation_select_range(data=None, start=None, end=None, step=1, **kwgs):
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
        def operation_filter(channel=None, data=None, filter=None, **kwgs):
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
                ("COLOR", r"(#[0123456789abcdefABCDEF]{6}|#[0123456789abcdefABCDEF]{3})"),
                ("TYPE", r"(raster|image|cut|engrave|dots|unknown|command|cutcode|lasercode)"),
                ("VAL", r"(speed|power|step|acceleration|passes|color|op|overscan|len)"),
            ]
            filter_re = re.compile("|".join("(?P<%s>%s)" % pair for pair in _filter_parse))
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
                            if op == "==" or op == '=':
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
                            operand.append(float('inf'))
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
        def operation_list(channel, _, data=None, **kwgs):
            channel("----------")
            channel(_("Operations:"))
            index_ops = list(self.ops())
            for op_obj in data:
                i = index_ops.index(op_obj)
                selected = op_obj.emphasized
                select_piece = " *" if selected else "  "
                color = (
                    Color(op_obj.color).hex
                    if hasattr(op_obj, "color") and op_obj.color is not None
                    else "None"
                )
                name = "%d: %s %s - %s" % (i, str(op_obj), select_piece, color)
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
            **kwgs
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

        @context.console_argument("speed", type=float, help=_("operation speed in mm/s"))
        @context.console_command(
            "speed", help=_("speed <speed>"), input_type="ops", output_type="ops"
        )
        def op_speed(command, channel, _, speed=None, data=None, **kwrgs):
            if speed is None:
                for op in data:
                    old_speed = op.settings.speed
                    channel(_("Speed for '%s' is currently: %f") % (str(op), old_speed))
                return
            for op in data:
                old_speed = op.settings.speed
                op.settings.speed = speed
                channel(_("Speed for '%s' updated %f -> %f") % (str(op), old_speed, speed))
                op.notify_update()
            return "ops", data

        @context.console_argument("power", type=int, help=_("power in pulses per inch (ppi, 1000=max)"))
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
                channel(_("Power for '%s' updated %d -> %d") % (str(op), old_ppi, power))
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
                    channel(_("Passes for '%s' is currently: %d") % (str(op), old_passes))
                return
            for op in data:
                old_passes = op.settings.passes
                op.settings.passes = passes
                if passes >= 1:
                    op.settings.passes_custom = True
                channel(_("Passes for '%s' updated %d -> %d") % (str(op), old_passes, passes))
                op.notify_update()
            return "ops", data

        @context.console_command(
            "disable", help=_("Disable the given operations"), input_type="ops", output_type="ops"
        )
        def op_disable(command, channel, _, data=None, **kwrgs):
            for op in data:
                op.output = False
                channel(_("Operation '%s' disabled.") % str(op))
                op.notify_update()
            return "ops", data

        @context.console_command(
            "enable", help=_("Enable the given operations"), input_type="ops", output_type="ops"
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
        def e_copy(data=None, data_type=None, **kwgs):
            add_elem = list(map(copy, data))
            if data_type == "ops":
                self.add_ops(add_elem)
            else:
                self.add_elems(add_elem)
            return data_type, add_elem

        @context.console_command(
            "delete", help=_("Delete elements"), input_type=("elements", "ops")
        )
        def e_delete(command, channel, _, data=None, data_type=None, **kwgs):
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
        def element(**kwgs):
            context(".element* list\n")

        @context.console_command(
            "element*",
            help=_("element*, all elements"),
            output_type="elements",
        )
        def element_star(**kwgs):
            return "elements", list(self.elems())

        @context.console_command(
            "element~",
            help=_("element~, all non-selected elements"),
            output_type="elements",
        )
        def element_not(**kwgs):
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
        def element_chain(command, channel, _, **kwgs):
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
            "step", help=_("step <element step-size>"), input_type="elements", output_type="elements"
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
            return "elements",

        @context.console_command(
            "select",
            help=_("Set these values as the selection."),
            input_type="elements",
            output_type="elements",
        )
        def element_select_base(data=None, **kwgs):
            self.set_emphasis(data)
            return "elements", data

        @context.console_command(
            "select+",
            help=_("Add the input to the selection"),
            input_type="elements",
            output_type="elements",
        )
        def element_select_plus(data=None, **kwgs):
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
        def element_select_minus(data=None, **kwgs):
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
        def element_select_xor(data=None, **kwgs):
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
        def element_list(command, channel, _, data=None, **kwgs):
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
        def element_select_range(data=None, start=None, end=None, step=1, **kwgs):
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
        def element_merge(data=None, **kwgs):
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
        def element_subpath(data=None, **kwgs):
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

        @context.console_argument("align", type=str, help=_("Alignment position"))
        @context.console_command(
            "align",
            help=_("align elements"),
            input_type=("elements", None),
        )
        def element_align(command, channel, _, data=None, align=None, **kwgs):
            if align is None:
                channel(
                    "top\nbottom\nleft\nright\ncenter\ncenterh\ncenterv\nspaceh\nspacev\n"
                    "<any valid svg:Preserve Aspect Ratio, eg xminymin>"
                )
                return
            if data is None:
                elem_branch = self.get(type="branch elems")
                data = list(
                    elem_branch.flat(
                        types=("elems", "file", "group"), cascade=False, depth=1
                    )
                )
                if len(data) == 0:
                    channel(_("Nothing to align."))
                    return
                for d in data:
                    channel(_("Aligning: %s") % str(d))
            boundary_points = []
            for e in data:
                node = e.node
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            left_edge = min([e[0] for e in boundary_points])
            top_edge = min([e[1] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])
            if align == "top":
                for e in data:
                    node = e.node
                    subbox = node.bounds
                    top = subbox[1] - top_edge
                    matrix = "translate(0, %f)" % -top
                    if top != 0:
                        for q in node.flat(types=("elem", "group", "file")):
                            obj = q.object
                            if obj is not None:
                                obj *= matrix
                            q.modified()
            elif align == "bottom":
                for e in data:
                    node = e.node
                    subbox = node.bounds
                    bottom = subbox[3] - bottom_edge
                    matrix = "translate(0, %f)" % -bottom
                    if bottom != 0:
                        for q in node.flat(types=("elem", "group", "file")):
                            obj = q.object
                            if obj is not None:
                                obj *= matrix
                            q.modified()
            elif align == "left":
                for e in data:
                    node = e.node
                    subbox = node.bounds
                    left = subbox[0] - left_edge
                    matrix = "translate(%f, 0)" % -left
                    if left != 0:
                        for q in node.flat(types=("elem", "group", "file")):
                            obj = q.object
                            if obj is not None:
                                obj *= matrix
                            q.modified()
            elif align == "right":
                for e in data:
                    node = e.node
                    subbox = node.bounds
                    right = subbox[2] - right_edge
                    matrix = "translate(%f, 0)" % -right
                    if right != 0:
                        for q in node.flat(types=("elem", "group", "file")):
                            obj = q.object
                            if obj is not None:
                                obj *= matrix
                            q.modified()
            elif align == "center":
                for e in data:
                    node = e.node
                    subbox = node.bounds
                    dx = (subbox[0] + subbox[2] - left_edge - right_edge) / 2.0
                    dy = (subbox[1] + subbox[3] - top_edge - bottom_edge) / 2.0
                    matrix = "translate(%f, %f)" % (-dx, -dy)
                    for q in node.flat(types=("elem", "group", "file")):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
            elif align == "centerv":
                for e in data:
                    node = e.node
                    subbox = node.bounds
                    dx = (subbox[0] + subbox[2] - left_edge - right_edge) / 2.0
                    matrix = "translate(%f, 0)" % -dx
                    for q in node.flat(types=("elem", "group", "file")):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
            elif align == "centerh":
                for e in data:
                    node = e.node
                    subbox = node.bounds
                    dy = (subbox[1] + subbox[3] - top_edge - bottom_edge) / 2.0
                    matrix = "translate(0, %f)" % -dy
                    for q in node.flat(types=("elem", "group", "file")):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
            elif align == "spaceh":
                if len(data) <= 1:
                    channel(_("Cannot spacial align fewer than 2 elements."))
                    return
                distance = right_edge - left_edge
                step = distance / (len(data) - 1)
                for e in data:
                    node = e.node
                    subbox = node.bounds
                    left = subbox[0] - left_edge
                    left_edge += step
                    matrix = "translate(%f, 0)" % -left
                    if left != 0:
                        for q in node.flat(types=("elem", "group", "file")):
                            obj = q.object
                            if obj is not None:
                                obj *= matrix
                            q.modified()
            elif align == "spacev":
                distance = bottom_edge - top_edge
                step = distance / (len(data) - 1)
                for e in data:
                    node = e.node
                    subbox = node.bounds
                    top = subbox[1] - top_edge
                    top_edge += step
                    matrix = "translate(0, %f)" % -top
                    if top != 0:
                        for q in node.flat(types=("elem", "group", "file")):
                            obj = q.object
                            if obj is not None:
                                obj *= matrix
                            q.modified()
            elif align == "topleft":
                for e in data:
                    node = e.node
                    dx = -left_edge
                    dy = -top_edge
                    matrix = "translate(%f, %f)" % (dx, dy)
                    for q in node.flat(types=("elem", "group", "file")):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
                self.context.signal("refresh_scene")
            elif align == "bedcenter":
                for e in data:
                    node = e.node
                    bw = bed_dim.bed_width
                    bh = bed_dim.bed_height
                    dx = (bw * MILS_IN_MM - left_edge - right_edge) / 2.0
                    dy = (bh * MILS_IN_MM - top_edge - bottom_edge) / 2.0
                    matrix = "translate(%f, %f)" % (dx, dy)
                    for q in node.flat(types=("elem", "group", "file")):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
                self.context.signal("refresh_scene")
            elif align in (
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
                for e in data:
                    node = e.node
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
                        align,
                    )
                    for q in node.flat(types=("elem", "group", "file")):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
                self.context.signal("refresh_scene")
            return "elements", data

        @context.console_argument("c", type=int, help=_("Number of columns"))
        @context.console_argument("r", type=int, help=_("Number of rows"))
        @context.console_argument("x", type=Length, help=_("x distance"))
        @context.console_argument("y", type=Length, help=_("y distance"))
        @context.console_command(
            "grid",
            help=_("grid <columns> <rows> <x_distance> <y_distance>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_grid(
            command, channel, _, c: int, r: int, x: Length, y: Length, data=None, **kwgs
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
            if y is None:
                y = Length("100%")
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
            y_pos = 0
            data_out = list(data)
            for j in range(r):
                x_pos = 0
                for k in range(c):
                    if j != 0 or k != 0:
                        add_elem = list(map(copy, data))
                        for e in add_elem:
                            e *= "translate(%f, %f)" % (x_pos, y_pos)
                        self.add_elems(add_elem)
                        data_out.extend(add_elem)
                    x_pos += x
                y_pos += y
            return "elements", data_out

        @context.console_option("step", "s", default=2.0, type=float)
        @context.console_command(
            "render",
            help=_("Convert given elements to a raster image"),
            input_type=(None, "elements"),
            output_type="image",
        )
        def make_raster_image(command, channel, _, step=2.0, data=None, **kwgs):
            context = self.context
            if data is None:
                data = list(self.elems(emphasized=True))
            elements = context.elements
            make_raster = self.context.registered.get("render-op/make_raster")

            bounds = Group.union_bbox(data)
            if bounds is None:
                return
            if step <= 0:
                step = 1.0
            xmin, ymin, xmax, ymax = bounds

            image = make_raster(
                [n.node for n in data],
                bounds,
                width=(xmax - xmin),
                height=(ymax - ymin),
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
        def element_circle(x_pos, y_pos, r_pos, data=None, **kwgs):
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
        def element_ellipse(x_pos, y_pos, rx_pos, ry_pos, data=None, **kwgs):
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
            x_pos, y_pos, width, height, rx=None, ry=None, data=None, **kwgs
        ):
            """
            Draws an svg rectangle with optional rounded corners.
            """
            if x_pos is None:
                raise SyntaxError
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
        def element_line(command, x0, y0, x1, y1, data=None, **kwgs):
            """
            Draws an svg line in the scene.
            """
            if y1 is None:
                raise SyntaxError
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

        @context.console_argument("text", type=str, help=_("quoted string of text"))
        @context.console_command(
            "text",
            help=_("text <text>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_text(command, channel, _, data=None, text=None, **kwgs):
            if text is None:
                channel(_("No text specified"))
                return
            svg_text = SVGText(text)
            self.add_element(svg_text)
            if data is None:
                return "elements", [svg_text]
            else:
                data.append(svg_text)
                return "elements", data

        @context.console_command(
            "polygon", help=_("polygon (float float)*"), input_type=("elements", None)
        )
        def element_polygon(args=tuple(), **kwgs):
            try:
                element = Polygon(list(map(float, args)))
            except ValueError:
                raise SyntaxError(
                    _(
                        "Must be a list of spaced delimited floating point numbers values."
                    )
                )
            self.add_element(element)

        @context.console_command(
            "polyline",
            help=_("polyline (float float)*"),
            input_type=("elements", None),
        )
        def element_polyline(command, channel, _, args=tuple(), **kwgs):
            try:
                element = Polyline(list(map(float, args)))
            except ValueError:
                raise SyntaxError(
                    _(
                        "Must be a list of spaced delimited floating point numbers values."
                    )
                )
            self.add_element(element)

        @context.console_command(
            "path", help=_("Convert any shapes to paths"), input_type="elements"
        )
        def element_path_convert(data, **kwgs):
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
        @context.console_command("path", help=_("path <svg path>"), input_type="elements", output_type="elements")
        def element_path(path_d, data, **kwgs):
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
        def element_stroke_width(command, channel, _, stroke_width, data=None, **kwgs):
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
        def element_stroke(command, channel, _, color, data=None, filter=None, **kwargs):
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
        def element_fill(command, channel, _, color, data=None, filter=None, **kwgs):
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
            **kwgs
        ):
            """
            Draws an outline of the current shape.
            """
            if x_offset is None:
                raise SyntaxError
            bounds = self.selected_area()
            if bounds is None:
                channel(_("Nothing Selected"))
                return
            x_pos = bounds[0]
            y_pos = bounds[1]
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
            offset_x = (
                y_offset.value(ppi=1000.0, relative_length=width)
                if len(args) >= 1
                else 0
            )
            offset_y = (
                x_offset.value(ppi=1000.0, relative_length=height)
                if len(args) >= 2
                else offset_x
            )

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
            **kwgs
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
            rot = angle.as_degrees

            if cx is not None:
                cx = cx.value(
                    ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                )
            else:
                cx = (bounds[2] + bounds[0]) / 2.0
            if cy is not None:
                cy = cy.value(
                    ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
                )
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
            **kwgs
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
                center_x = px.value(
                    ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                )
            else:
                center_x = (bounds[2] + bounds[0]) / 2.0
            if py is not None:
                center_y = py.value(
                    ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
                )
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
            command, channel, _, tx, ty, absolute=False, data=None, **kwgs
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
                tx = tx.value(
                    ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                )
            else:
                tx = 0
            if ty is not None:
                ty = ty.value(
                    ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
                )
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
        def element_resize(command, x_pos, y_pos, width, height, data=None, **kwgs):
            if height is None:
                raise SyntaxError
            try:
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
                area = self.selected_area()
                if area is None:
                    return
                x, y, x1, y1 = area
                w, h = x1 - x, y1 - y
                sx = width / w
                sy = height / h
                if abs(sx - 1.0) < 1e-1:
                    sx = 1.0
                if abs(sy - 1.0) < 1e-1:
                    sy = 1.0

                m = Matrix(
                    "translate(%f,%f) scale(%f,%f) translate(%f,%f)"
                    % (x_pos, y_pos, sx, sy, -x, -y)
                )
                if data is None:
                    data = list(self.elems(emphasized=True))
                for e in data:
                    try:
                        if e.lock and (not sx == 1.0 or not sy == 1.0):
                            continue
                    except AttributeError:
                        pass
                    e *= m
                    if hasattr(e, "node"):
                        e.node.modified()
                context.signal("refresh_scene")
                return "elements", data
            except (ValueError, ZeroDivisionError, TypeError):
                raise SyntaxError

        @context.console_argument("sx", type=float, help=_("scale_x value"))
        @context.console_argument("kx", type=float, help=_("skew_x value"))
        @context.console_argument("sy", type=float, help=_("scale_y value"))
        @context.console_argument("ky", type=float, help=_("skew_y value"))
        @context.console_argument("tx", type=Length, help=_("translate_x value"))
        @context.console_argument("ty", type=Length, help=_("translate_y value"))
        @context.console_command(
            "matrix",
            help=_("matrix <sx> <kx> <sy> <ky> <tx> <ty>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_matrix(
            command, channel, _, sx, kx, sy, ky, tx, ty, data=None, **kwgs
        ):
            if tx is None:
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
            if ty:
                raise SyntaxError
            try:
                m = Matrix(
                    sx,
                    kx,
                    sy,
                    ky,
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
        def reset(command, channel, _, data=None, **kwgs):
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
        def element_reify(command, channel, _, data=None, **kwgs):
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
        def element_classify(command, channel, _, data=None, **kwgs):
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
        def declassify(command, channel, _, data=None, **kwgs):
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
        def tree(**kwgs):
            return "tree", [self._tree]

        @context.console_command(
            "bounds", help=_("view tree bounds"), input_type="tree", output_type="tree"
        )
        def tree_bounds(command, channel, _, data=None, **kwgs):
            if data is None:
                data = [self._tree]

            def b_list(path, node):
                for i, n in enumerate(node.children):
                    p = list(path)
                    p.append(str(i))
                    channel("%s: %s - %s %s - %s" % ('.'.join(p).ljust(10), str(n._bounds), str(n._bounds_dirty), str(n.type), str(n.label[:16])))
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
        def tree_list(command, channel, _, data=None, **kwgs):
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
                    channel("%s%s %s - %s" % ('.'.join(p).ljust(10), j, str(n.type), str(n.label)))
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
        def tree_dnd(command, channel, _, data=None, drag=None, drop=None, **kwgs):
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
            "menu", help=_("Load menu for given node"), input_type="tree", output_type="tree"
        )
        def tree_menu(command, channel, _, data=None, node=None, execute=None, **kwgs):
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
                    menu_context.append((func.real_name,menu_functions(func, menu_node)))
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
                        channel("%s: %s" % ('.'.join(p).ljust(10), str(name)))
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
        def emphasized(channel, _, **kwargs):
            """
            Set tree list to selected node
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
            Delete node. Due to nodes within nodes, only the first node is deleted.
            Structural nodes such as root, elements, and operations are not able to be deleted
            """
            for n in data:
                if n.type not in ("root", "branch elems", "branch ops"):
                    # Cannot delete structure nodes.
                    n.remove_node()
                    break
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
                    types=("op", "elem", "file", "group"), emphasized=True
            ):
                if item.type == "op":
                    return "ops", list(self.ops(emphasized=True))
                if item.type in ("elem", "file", "group"):
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
        def clipboard_base(data=None, name=None, **kwgs):
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
        def clipboard_copy(data=None, **kwgs):
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
        def clipboard_paste(command, channel, _, data=None, dx=None, dy=None, **kwgs):
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
                    dx = dx.value(
                        ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                    )
                if dy is None:
                    dy = 0
                else:
                    dy = dy.value(
                        ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
                    )
                m = Matrix("translate(%s, %s)" % (dx, dy))
                for e in pasted:
                    e *= m
            self.add_elems(pasted)
            return "elements", pasted

        @context.console_command(
            "cut",
            help=_("clipboard cut"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_cut(data=None, **kwgs):
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
        def clipboard_clear(data=None, **kwgs):
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
        def clipboard_contents(**kwgs):
            destination = self._clipboard_default
            return "elements", self._clipboard[destination]

        @context.console_command(
            "list",
            help=_("clipboard list"),
            input_type="clipboard",
        )
        def clipboard_list(command, channel, _, **kwgs):
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
        def note(command, channel, _, append=False, remainder=None, **kwgs):
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
            "trace_hull", help=_("trace the convex hull of current elements")
        )
        def trace_trace_hull(command, channel, _, **kwgs):
            active = self.context.active
            spooler, input_device, output = self.context.registered[
                "device/%s" % active
            ]
            pts = []
            for obj in self.elems(emphasized=True):
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
        def trace_trace_quick(command, channel, _, **kwgs):
            active = self.context.active
            spooler, input_device, output = self.context.registered[
                "device/%s" % active
            ]
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

        # --------------------------- END COMMANDS ------------------------------

        # --------------------------- TREE OPERATIONS ---------------------------

        _ = self.context._

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: len(list(self.ops(emphasized=True))) == 1)
        @self.tree_operation(_("Operation properties"), node_type="op", help="")
        def operation_property(node, **kwgs):
            self.context.open("window/OperationProperty", self.context.gui, node=node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, Shape))
        @self.tree_operation(_("Element properties"), node_type="elem", help="")
        def path_property(node, **kwgs):
            self.context.open("window/PathProperty", self.context.gui, node=node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, Group))
        @self.tree_operation(_("Group properties"), node_type="group", help="")
        def group_property(node, **kwgs):
            self.context.open("window/GroupProperty", self.context.gui, node=node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, SVGText))
        @self.tree_operation(_("Text properties"), node_type="elem", help="")
        def text_property(node, **kwgs):
            self.context.open("window/TextProperty", self.context.gui, node=node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_operation(_("Image properties"), node_type="elem", help="")
        def image_property(node, **kwgs):
            self.context.open("window/ImageProperty", self.context.gui, node=node)

        @self.tree_operation(
            _("Ungroup elements"), node_type=("group", "file"), help=""
        )
        def ungroup_elements(node, **kwgs):
            for n in list(node.children):
                node.insert_sibling(n)
            node.remove_node()  # Removing group/file node.

        @self.tree_operation(_("Group elements"), node_type="elem", help="")
        def group_elements(node, **kwgs):
            # group_node = node.parent.add_sibling(node, type="group", name="Group")
            group_node = node.parent.add(type="group", label="Group")
            for e in list(self.elems(emphasized=True)):
                node = e.node
                group_node.append_child(node)

        @self.tree_operation(_("Enable/Disable ops"), node_type="op", help="")
        def toggle_n_operations(node, **kwgs):
            for n in self.ops(emphasized=True):
                n.output = not n.output
                n.notify_update()

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(_("Convert to Image"), node_type="op", help="")
        def convert_operation_image(node, **kwgs):
            for n in self.ops(emphasized=True):
                n.operation = "Image"

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(_("Convert to Raster"), node_type="op", help="")
        def convert_operation_raster(node, **kwgs):
            for n in self.ops(emphasized=True):
                n.operation = "Raster"

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(_("Convert to Engrave"), node_type="op", help="")
        def convert_operation_engrave(node, **kwgs):
            for n in self.ops(emphasized=True):
                n.operation = "Engrave"

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(_("Convert to Cut"), node_type="op", help="")
        def convert_operation_cut(node, **kwgs):
            for n in self.ops(emphasized=True):
                n.operation = "Cut"

        def radio_match(node, speed=0, **kwgs):
            return node.settings.speed == float(speed)

        @self.tree_conditional(lambda node: node.operation in ("Raster", "Image"))
        @self.tree_submenu(_("Speed"))
        @self.tree_radio(radio_match)
        @self.tree_values("speed", (50, 75, 100, 150, 200, 250, 300, 350))
        @self.tree_operation(
            _("Speed %smm/s") % "{speed}",
            node_type="op",
            help=""
        )
        def set_speed_raster(node, speed=150, **kwgs):
            node.settings.speed = float(speed)
            self.context.signal("element_property_reload", node)

        @self.tree_conditional(lambda node: node.operation in ("Cut", "Engrave"))
        @self.tree_submenu(_("Speed"))
        @self.tree_radio(radio_match)
        @self.tree_values("speed", (5, 10, 15, 20, 25, 30, 35, 40))
        @self.tree_operation(
            _("Speed %smm/s") % "{speed}",
            node_type="op",
            help=""
        )
        def set_speed_vector(node, speed=35, **kwgs):
            node.settings.speed = float(speed)
            self.context.signal("element_property_reload", node)

        def radio_match(node, i=1, **kwgs):
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
        def set_step_n(node, i=1, **kwgs):
            settings = node.settings
            settings.raster_step = i
            self.context.signal("element_property_reload", node)

        def radio_match(node, passvalue=1, **kwgs):
            return (
                (node.settings.passes_custom and passvalue == node.settings.passes)
                or
                (not node.settings.passes_custom and passvalue == 1)
            )

        @self.tree_submenu(_("Set operation passes"))
        @self.tree_radio(radio_match)
        @self.tree_iterate("passvalue", 1, 10)
        @self.tree_operation(_("Passes %s") % "{passvalue}", node_type="op", help="")
        def set_n_passes(node, passvalue=1, **kwgs):
            node.settings.passes = passvalue
            node.settings.passes_custom = passvalue != 1
            self.context.signal("element_property_reload", node)

        @self.tree_separator_after()
        @self.tree_operation(
            _("Execute operation(s)"),
            node_type="op",
            help=_("Execute Job for the selected operation(s)."),
        )
        def execute_job(node, **kwgs):
            node.emphasized = True
            self.context("plan0 clear copy-selected\n")
            self.context("window open ExecuteJob 0\n")

        @self.tree_separator_after()
        @self.tree_operation(
            _("Simulate operation(s)"),
            node_type="op",
            help=_("Run simulation for the selected operation(s)"),
        )
        def compile_and_simulate(node, **kwgs):
            node.emphasized = True
            self.context(
                "plan0 copy-selected preprocess validate blob preopt optimize\n"
            )
            self.context("window open Simulation 0\n")

        @self.tree_operation(_("Clear all"), node_type="branch ops", help="")
        def clear_all(node, **kwgs):
            self.context("operation* delete\n")

        @self.tree_operation(_("Clear all"), node_type="branch elems", help="")
        def clear_all_ops(node, **kwgs):
            self.context("element* delete\n")
            self.elem_branch.remove_all_children()

        @self.tree_conditional(lambda node: len(list(self.ops(emphasized=True))) == 1)
        @self.tree_operation(
            _("Remove '%s'") % "{name}",
            node_type=(
                "op",
                "cmdop",
                "elem",
                "lasercode",
                "cutcode",
                "blob"
            ),
            help="",
        )
        def remove_type_op(node, **kwgs):
            node.remove_node()
            self.set_emphasis(None)

        @self.tree_conditional(lambda node: len(list(self.elems(emphasized=True))) == 1)
        @self.tree_operation(
            _("Remove '%s'") % "{name}",
            node_type=(
                "opnode",
                "cmdop",
                "file",
                "group",
                "lasercode",
                "cutcode",
                "blob"
            ),
            help="",
        )
        def remove_type_elem(node, **kwgs):
            node.remove_node()
            self.set_emphasis(None)

        @self.tree_conditional(lambda node: len(list(self.ops(emphasized=True))) > 1)
        @self.tree_calc("ecount", lambda i: len(list(self.ops(emphasized=True))))
        @self.tree_operation(
            _("Remove %s operations") % "{ecount}",
            node_type="op",
            help=""
        )
        def remove_n_ops(node, **kwgs):
            self.context("element delete\n")

        @self.tree_conditional(lambda node: len(list(self.elems(emphasized=True))) > 1)
        @self.tree_calc("ecount", lambda i: len(list(self.elems(emphasized=True))))
        @self.tree_operation(
            _("Remove %s elements") % "{ecount}",
            node_type=("elem", "opnode"),
            help=""
        )
        def remove_n_elements(node, **kwgs):
            self.context("element delete\n")

        @self.tree_operation(
            _("Convert to Cutcode"),
            node_type="lasercode",
            help="",
        )
        def lasercode2cut(node, **kwgs):
            node.replace_node(CutCode.from_lasercode(node.object), type="cutcode")

        @self.tree_conditional_try(lambda node: hasattr(node.object, "as_cutobjects"))
        @self.tree_operation(
            _("Convert to Cutcode"),
            node_type="blob",
            help="",
        )
        def blob2cut(node, **kwgs):
            node.replace_node(node.object.as_cutobjects(), type="cutcode")

        @self.tree_operation(
            _("Convert to Path"),
            node_type="cutcode",
            help="",
        )
        def cutcode2pathcut(node, **kwgs):
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
        def clone_single_element_op(node, **kwgs):
            clone_element_op(node, 1, **kwgs)

        @self.tree_submenu(_("Clone reference"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(_("Make %s copies") % "{copies}", node_type="opnode", help="")
        def clone_element_op(node, copies=1, **kwgs):
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
        def reverse_layer_order(node, **kwgs):
            node.reverse()
            self.context.signal("rebuild_tree", 0)

        @self.tree_separator_after()
        @self.tree_operation(
            _("Refresh classification"), node_type="branch ops", help=""
        )
        def refresh_clasifications(node, **kwgs):
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
        @self.tree_operation(_("Load: %s") % "{opname}", node_type="branch ops", help="")
        def load_ops(node, opname, **kwgs):
            self.context("operation load %s\n" % opname)

        @self.tree_submenu(_("Use"))
        @self.tree_operation(_("Other/Blue/Red"), node_type="branch ops", help="")
        def default_classifications(node, **kwgs):
            self.context.elements.load_default()

        @self.tree_submenu(_("Use"))
        @self.tree_operation(_("Basic"), node_type="branch ops", help="")
        def basic_classifications(node, **kwgs):
            self.context.elements.load_default2()

        @self.tree_submenu(_("Save"))
        @self.tree_values("opname", values=union_materials_saved)
        @self.tree_operation("{opname}", node_type="branch ops", help="")
        def save_ops(node, opname="saved", **kwgs):
            self.context("operation save %s\n" % opname)

        @self.tree_separator_before()
        @self.tree_submenu(_("Add operation"))
        @self.tree_operation(_("Add Image"), node_type="branch ops", help="")
        def add_operation_image(node, **kwgs):
            self.context.elements.add_op(LaserOperation(operation="Image"))

        @self.tree_submenu(_("Add operation"))
        @self.tree_operation(_("Add Raster"), node_type="branch ops", help="")
        def add_operation_raster(node, **kwgs):
            self.context.elements.add_op(LaserOperation(operation="Raster"))

        @self.tree_submenu(_("Add operation"))
        @self.tree_operation(_("Add Engrave"), node_type="branch ops", help="")
        def add_operation_engrave(node, **kwgs):
            self.context.elements.add_op(LaserOperation(operation="Engrave"))

        @self.tree_submenu(_("Add operation"))
        @self.tree_operation(_("Add Cut"), node_type="branch ops", help="")
        def add_operation_cut(node, **kwgs):
            self.context.elements.add_op(LaserOperation(operation="Cut"))

        @self.tree_submenu(_("Special operations"))
        @self.tree_operation(_("Add Home"), node_type="branch ops", help="")
        def add_operation_home(node, **kwgs):
            self.context.elements.op_branch.add(
                CommandOperation("Home", COMMAND_HOME), type="cmdop"
            )

        @self.tree_submenu(_("Special operations"))
        @self.tree_operation(_("Add Beep"), node_type="branch ops", help="")
        def add_operation_beep(node, **kwgs):
            self.context.elements.op_branch.add(
                CommandOperation("Beep", COMMAND_BEEP), type="cmdop"
            )

        @self.tree_submenu(_("Special operations"))
        @self.tree_operation(_("Add Move Origin"), node_type="branch ops", help="")
        def add_operation_origin(node, **kwgs):
            self.context.elements.op_branch.add(
                CommandOperation("Origin", COMMAND_MOVE, 0, 0), type="cmdop"
            )

        @self.tree_submenu(_("Special operations"))
        @self.tree_operation(_("Add Interrupt"), node_type="branch ops", help="")
        def add_operation_interrupt(node, **kwgs):
            self.context.elements.op_branch.add(
                CommandOperation(
                    "Interrupt",
                    COMMAND_FUNCTION,
                    self.context.registered["function/interrupt"],
                ),
                type="cmdop",
            )

        @self.tree_submenu(_("Special operations"))
        @self.tree_operation(_("Add Shutdown"), node_type="branch ops", help="")
        def add_operation_shutdown(node, **kwgs):
            self.context.elements.op_branch.add(
                CommandOperation(
                    "Shutdown",
                    COMMAND_FUNCTION,
                    self.context.console_function("quit\n"),
                ),
                type="cmdop",
            )

        @self.tree_operation(
            _("Reclassify operations"), node_type="branch elems", help=""
        )
        def reclassify_operations(node, **kwgs):
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
        def duplicate_operation(node, **kwgs):
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
        def add_1_pass(node, **kwgs):
            add_n_passes(node, 1, **kwgs)

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_conditional(
            lambda node: node.operation in ("Image", "Engrave", "Cut")
        )
        @self.tree_submenu(_("Passes"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(_("Add %s passes") % "{copies}", node_type="op", help="")
        def add_n_passes(node, copies=1, **kwgs):
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
        @self.tree_operation(
            _("Duplicate elements 1 time"), node_type="op", help=""
        )
        def dup_1_copy(node, **kwgs):
            dup_n_copies(node, 1, **kwgs)

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_conditional(
            lambda node: node.operation in ("Image", "Engrave", "Cut")
        )
        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(
            _("Duplicate elements %s times") % "{copies}", node_type="op", help=""
        )
        def dup_n_copies(node, copies=1, **kwgs):
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
        def make_raster_image(node, **kwgs):
            context = self.context
            elements = context.elements
            subitems = list(node.flat(types=("elem", "opnode")))
            make_raster = self.context.registered.get("render-op/make_raster")
            bounds = Group.union_bbox([s.object for s in subitems])
            if bounds is None:
                return
            step = float(node.settings.raster_step)
            if step == 0:
                step = 1.0
            xmin, ymin, xmax, ymax = bounds

            image = make_raster(
                subitems,
                bounds,
                width=(xmax - xmin),
                height=(ymax - ymin),
                step=step,
            )
            image_element = SVGImage(image=image)
            image_element.transform.post_scale(step, step)
            image_element.transform.post_translate(xmin, ymin)
            image_element.values["raster_step"] = step
            elements.add_elem(image_element)

        @self.tree_operation(_("Reload '%s'") % "{name}", node_type="file", help="")
        def reload_file(node, **kwgs):
            filepath = node.filepath
            node.remove_node()
            self.load(filepath)

        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_operation(_("Make 1 copy"), node_type="elem", help="")
        def duplicate_element_1(node, **kwgs):
            duplicate_element_n(node, 1, **kwgs)

        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(_("Make %s copies") % "{copies}", node_type="elem", help="")
        def duplicate_element_n(node, copies, **kwgs):
            context = self.context
            elements = context.elements
            adding_elements = [
                copy(e) for e in list(self.elems(emphasized=True)) * copies
            ]
            elements.add_elems(adding_elements)
            elements.classify(adding_elements)
            elements.set_emphasis(None)

        @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(
            _("Reset user changes"), node_type=("branch elem", "elem"), help=""
        )
        def reset_user_changes(node, copies=1, **kwgs):
            self.context("reset\n")

        @self.tree_conditional(
            lambda node: isinstance(node.object, Shape)
            and not isinstance(node.object, Path)
        )
        @self.tree_operation(_("Convert to path"), node_type=("elem",), help="")
        def convert_to_path(node, copies=1, **kwgs):
            node.replace_object(abs(Path(node.object)))
            node.altered()

        @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Scale"))
        @self.tree_iterate("scale", 25, 1, -1)
        @self.tree_calc("scale_percent", lambda i: "%0.f" % (600.0 / float(i)))
        @self.tree_operation(
            _("Scale %s%%") % "{scale_percent}", node_type="elem", help="Scale Element"
        )
        def scale_elem_amount(node, scale, **kwgs):
            scale = 6.0 / float(scale)
            child_objects = Group()
            child_objects.extend(node.objects_of_children(SVGElement))
            bounds = child_objects.bbox()
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self.context("scale %f %f %f %f\n" % (scale, scale, center_x, center_y))

        @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Rotate"))
        @self.tree_values("angle",
            (
                180,150,135,120,90,60,45,30,20,15,10,9,8,7,6,5,4,3,2,1,
                -1,-2,-3,-4,-5,-6,-7,-8,-9,-10,-15,-20,-30,-45,-60,-90,-120,-135,-150
            )
        )
        @self.tree_operation(_(u"Rotate %s°") % ("{angle}"), node_type="elem", help="")
        def rotate_elem_amount(node, angle, **kwgs):
            turns = float(angle) / 360.0
            child_objects = Group()
            child_objects.extend(node.objects_of_children(SVGElement))
            bounds = child_objects.bbox()
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self.context("rotate %fturn %f %f\n" % (turns, center_x, center_y))

        @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(_("Reify User Changes"), node_type="elem", help="")
        def reify_elem_changes(node, **kwgs):
            self.context("reify\n")

        @self.tree_conditional(lambda node: isinstance(node.object, Path))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(_("Break Subpaths"), node_type="elem", help="")
        def break_subpath_elem(node, **kwgs):
            self.context("element subpath\n")

        @self.tree_operation(
            _("Merge items"),
            node_type="group",
            help=_("Merge this node's children into 1 path."),
        )
        def merge_elements(node, **kwgs):
            self.context("element merge\n")

        def radio_match(node, i=0, **kwgs):
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
        @self.tree_submenu(_("Step"))
        @self.tree_radio(radio_match)
        @self.tree_iterate("i", 1, 10)
        @self.tree_operation(_("Step %s") % "{i}", node_type="elem", help="")
        def set_step_n_elem(node, i=1, **kwgs):
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
        def image_actualize_pixels(node, **kwgs):
            self.context("image resample\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Z-depth divide"))
        @self.tree_iterate("divide", 2, 10)
        @self.tree_operation(
            _("Divide into %s images") % "{divide}", node_type="elem", help=""
        )
        def image_zdepth(node, divide=1, **kwgs):
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
        def image_unlock_manipulations(node, **kwgs):
            self.context("image unlock\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Dither to 1 bit"), node_type="elem", help="")
        def image_dither(node, **kwgs):
            self.context("image dither\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Invert image"), node_type="elem", help="")
        def image_invert(node, **kwgs):
            self.context("image invert\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Mirror horizontal"), node_type="elem", help="")
        def image_mirror(node, **kwgs):
            context("image mirror\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Flip vertical"), node_type="elem", help="")
        def image_flip(node, **kwgs):
            self.context("image flip\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Rotate 90° CW"), node_type="elem", help="")
        def image_cw(node, **kwgs):
            self.context("image cw\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Rotate 90° CCW"), node_type="elem", help="")
        def image_ccw(node, **kwgs):
            self.context("image ccw\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Save output.png"), node_type="elem", help="")
        def image_save(node, **kwgs):
            self.context("image save output.png\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("RasterWizard"))
        @self.tree_values(
            "script", values=list(self.context.match("raster_script", suffix=True))
        )
        @self.tree_operation(_("RasterWizard: %s") % "{script}", node_type="elem", help="")
        def image_rasterwizard_open(node, script=None, **kwgs):
            self.context("window open RasterWizard %s\n" % script)

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Apply raster script"))
        @self.tree_values(
            "script", values=list(self.context.match("raster_script", suffix=True))
        )
        @self.tree_operation(_("Apply: %s") % "{script}", node_type="elem", help="")
        def image_rasterwizard_apply(node, script=None, **kwgs):
            self.context("image wizard %s\n" % script)

        @self.tree_conditional_try(lambda node: hasattr(node.object, "as_elements"))
        @self.tree_operation(_("Convert to SVG"), node_type="elem", help="")
        def cutcode_convert_svg(node, **kwgs):
            self.context.elements.add_elems(list(node.object.as_elements()))

        @self.tree_conditional_try(lambda node: hasattr(node.object, "generate"))
        @self.tree_operation(_("Process as Operation"), node_type="elem", help="")
        def cutcode_operation(node, **kwgs):
            self.context.elements.add_op(node.object)

        @self.tree_conditional(lambda node: len(node.children) > 0)
        @self.tree_separator_before()
        @self.tree_operation(
            _("Expand all children"),
            node_type=("op", "branch elems", "branch ops", "group", "file", "root"),
            help="Expand all children of this given node.",
        )
        def expand_all_children(node, **kwgs):
            node.notify_expand()

        @self.tree_conditional(lambda node: len(node.children) > 0)
        @self.tree_operation(
            _("Collapse all children"),
            node_type=("op", "branch elems", "branch ops", "group", "file", "root"),
            help="Collapse all children of this given node.",
        )
        def collapse_all_children(node, **kwgs):
            node.notify_collapse()

        @self.tree_reference(lambda node: node.object.node)
        @self.tree_operation(_("Element"), node_type="opnode", help="")
        def reference_opnode(node, **kwgs):
            pass

        self.listen(self)

    def detach(self, *a, **kwargs):
        self.save_persistent_operations("previous")
        self.unlisten(self)

    def boot(self, *a, **kwargs):
        self.context.setting(bool, "operation_default_empty", True)
        self.load_persistent_operations("previous")
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
            if not hasattr(op, "settings"):
                continue  # Might be a function.
            sets = op.settings
            for q in (op, sets):
                for key in dir(q):
                    if key.startswith("_"):
                        continue
                    if key.startswith("implicit"):
                        continue
                    value = getattr(q, key)
                    if value is None:
                        continue
                    if isinstance(value, Color):
                        value = value.argb
                    op_set.write_persistent(key, value)
        settings.close_subpaths()

    def load_persistent_operations(self, name):
        self.clear_operations()
        settings = self.context.get_context("operations/" + name)
        subitems = list(settings.derivable())
        ops = [None] * len(subitems)
        for i, v in enumerate(subitems):
            op_setting_context = settings.derive(v)
            op = LaserOperation()
            op_set = op.settings
            op_setting_context.load_persistent_object(op)
            op_setting_context.load_persistent_object(op_set)
            try:
                ops[i] = op
            except (ValueError, IndexError):
                ops.append(op)
        self.add_ops([o for o in ops if o is not None])
        self.classify(list(self.elems()))

    def emphasized(self, *args):
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
        for item in operations.flat(types=("op",), depth=1, **kwargs):
            yield item

    def elems(self, **kwargs):
        elements = self._tree.get(type="branch elems")
        for item in elements.flat(types=("elem",), **kwargs):
            yield item.object

    def elems_nodes(self, depth=None, **kwargs):
        elements = self._tree.get(type="branch elems")
        for item in elements.flat(
            types=("elem", "file", "group"), depth=depth, **kwargs
        ):
            yield item

    def first_element(self, **kwargs):
        for e in self.elems(**kwargs):
            return e
        return None

    def has_emphasis(self):
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
            operation_branch.add(op, type="op")
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
                if e.object in elements_list:
                    e.remove_node()

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
        Text is classified as Raster
        All other SVGElement types are Shapes

        Paths consisting of a move followed by a single stright line segment are never Raster (since no width) -
            testing for more complex stright line elements is too difficult
        Stroke/Fill of same colour is a Raster
        Stroke/Fill of different colors are both Cut/Engrave and Raster
        No Stroke/Fill is a Raster
        Reddish Stroke is a Cut.
        Black Stroke is a Raster.
        All other stroke colors are Engrave
        White Engrave operations created by classify will be created disabled.
        Cut/Engraves elements are attenpted to match to a matching Operation of same absolute color, creating it if necessary.

        Rasters are classified to Raster Operations differently based on whether
            1. all existing rasters have the same color (default being a different colour to any other); or
            2. there are existing raster ops of different colors

         1. All existing raster ops are of the same color (or there are no existing raster ops):
            In this case all raster operations will be assigned either to all existing raster ops or to a new Default Raster operation we create
            in exactly the same wasy as vector Cut/Engrave operations.

         2. There are at least 2 raster ops of different colours:
            In this case we are going to try to match raster elements to raster operations by colour. But this is complicated because
            we need to keep overlapping raster elements together.
            So in this case we classify vector and special elements in a first pass, and then analyse and classify raster operations in a special second pass.
            Because we have to analyse all raster elements together, we cannot add elements one by one.

            In the second pass, we do the following:
             1. Group rasters by whether they have overlapping bounding boxes. The order of rasters MUST be maintained within these groups.
                After this, if rasters are in separate groups then they are in entirely separate areas of the burn which do not overlap.
             2. For each group of raster objects, determine which operations are of the same colour as at least one element in the group.
                All the raster elements of the group will be added to those operations.
             3. If there are any raster elements that are not classified in this way then:
                 A) If there are Default Raster Operation(s), then the remaining raster elements are allocated to those.
                 B) Otherwise, if there are any non-default raster operations that are empty and those raster operations are of the same colour,
                    then the remaining raster operations will be allocated to those Raster Operations.
                 C) Otherwise, a new Default Raster operation will be created and remaining Raster elements will be added to that.

        The current code does not do the following:
        a)  Handle rasters in second or later files which overlap elements from earlier files which have already been classified into operations.
            It is assumed that if they happen to overlap that is coincidence. After all the files could have been added in a different order and
            then would have a different result.
        b)  Handle any differently the reclassifications of single elements which have e.g. had their colour changed. (This needs to be checked.)

        :param elements: list of elements to classify.
        :param operations: operations list to classify into.
        :param add_op_function: function to add a new operation, because of a lack of classification options.
        :return:
        """

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
        default_cut_ops = []
        default_engrave_ops = []
        default_raster_ops = []
        rasters_one_pass = None

        for op in operations:
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
            if isinstance(element, (Shape, SVGText)) and (element_color is None or element_color.rgb is None):
                continue
            is_dot = isDot(element)
            is_straight_line = isStraightLine(element)


            add_vector = False    # For everything except shapes
            add_non_vector = True # Text, Images and Dots
            if isinstance(element, (Shape, SVGText)) and not is_dot:
                if element_color.rgb == 0x000000: # Black treated as a raster for user convenience
                    add_vector = False
                    add_non_vector = True
                else:
                    add_vector = element.stroke is not None and element.stroke.rgb is not None
                    add_non_vector = (
                        element.fill is not None
                        and element.fill.rgb is not None  # Filled
                        and not is_straight_line          # Cannot raster a straight line segment
                        and element.fill.alpha !=0        # Not Transparent
                    )
                    if add_vector and add_non_vector and element.stroke.rgb == element.fill.rgb: # Stroke same as fill - raster-only
                        add_vector = False

            if not (add_vector or add_non_vector): # No stroke and (straight line or transparent fill)
                continue

            # First classify to operations of exact color
            if add_vector:
                for op in vector_ops:
                    if (
                        op.color.rgb == element_color.rgb
                        and op not in default_cut_ops
                        and op not in default_engrave_ops
                    ):
                        op.add(element, type="opnode", pos=element_pos)
                        add_vector = False
            if add_non_vector:
                if is_dot or isinstance(element, SVGImage):
                    for op in special_ops:
                        if (
                            (is_dot and op.operation == "Dots")
                            or (isinstance(element, SVGImage) and op.operation == "Image")
                        ):
                            op.add(element, type="opnode", pos=element_pos)
                            add_non_vector = False
                            break # May only classify in one Dots or Image operation and indeed in one operation
                elif raster_ops and rasters_one_pass:
                    for op in raster_ops:
                        op.add(element, type="opnode", pos=element_pos)
                        add_non_vector = False

            # Check for default vector operations
            if add_vector:
                is_cut = Color.distance_sq("red", element_color) <= 18825
                if is_cut and default_cut_ops:
                    for op in default_cut_ops:
                        op.add(element, type="opnode", pos=element_pos)
                    add_vector = False
                elif not is_cut and default_engrave_ops:
                    for op in default_engrave_ops:
                        op.add(element, type="opnode", pos=element_pos)
                    add_vector = False

            # Need to add a vector operation to classify into
            if add_vector:
                if is_cut: # This will be initialised because criteria are same as above
                    op = LaserOperation(operation="Cut", color=abs(element_color))
                else:
                    op = LaserOperation(operation="Engrave", color=abs(element_color))
                    if element_color == Color("white"):
                        op.settings.laser_enabled = False
                vector_ops.append(op)
                add_op_function(op)
                # element cannot be added to op before op is added to operations - otherwise opnode is not created.
                op.add(element, type="opnode", pos=element_pos)

            # Need to add a special or raster operation to classify into
            if add_non_vector:
                if is_dot:
                    op = LaserOperation(operation="Dots", default=True)
                    special_ops.append(op)
                elif isinstance(element, SVGImage):
                    op = LaserOperation(operation="Image", default=True)
                    special_ops.append(op)
                elif rasters_one_pass:
                    op = LaserOperation(operation="Raster", color="Transparent", default=True)
                    default_raster_ops.append(op)
                    raster_ops.append(op)
                else:
                    raster_elements.append(element)
                    continue
                add_op_function(op)
                # element cannot be added to op before op is added to operations - otherwise opnode is not created.
                op.add(element, type="opnode", pos=element_pos)

        # End loop "for element in elements"

        if not raster_elements:
            return

        # Now deal with two-pass raster elements
        # It is ESSENTIAL that elements are added to operations in the same order as original.
        # The easiest way to ensure this is to create groups using a copy of raster_elements and
        # then ensure that groups have elements in the same order as in raster_elements.
        raster_groups = [[(e, e.bbox())] for e in raster_elements]
        for i, g1 in reversed_enumerate(raster_groups[:-1]):
            for g2 in reversed(raster_groups[i + 1:]):
                if self.group_elements_overlap(g1, g2):
                    g1.extend(g2)
                    raster_groups.remove(g2)

        # Remove bbox and add element colour from groups
        raster_groups = list(map(lambda g: tuple(((e[0], self.element_classify_color(e[0])) for e in g)), raster_groups))

        # Add groups to operations of matching colour (and remove from list)
        groups_added =[]
        for op in raster_ops:
            if op not in default_raster_ops:
                elements_to_add = []
                for group in raster_groups:
                    for e in group:
                        if e[1].rgb == op.color.rgb:
                            elements_to_add.extend(group)
                            if group not in groups_added:
                                groups_added.append(group)
                            break
                if elements_to_add:
                    elements_to_add = sorted((e[0] for e in elements_to_add), key=raster_elements.index)
                    for element in elements_to_add:
                        op.add(element, type="opnode", pos=element_pos)

        # Now remove groups added to at least one op
        for group in groups_added:
            raster_groups.remove(group)

        if not raster_groups: # added all groups
            return

        #  Because groups don't matter further simplify back to an element_list
        elements_to_add = []
        for g in raster_groups:
            elements_to_add.extend(g)
        elements_to_add = sorted((e[0] for e in elements_to_add), key=raster_elements.index)

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
                if color is False:
                    color = op.color.rgb
                elif color != op.color.rgb:
                    default_raster_ops = []
                    break
        if not default_raster_ops:
            op = LaserOperation(operation="Raster", color="Transparent", default=True)
            default_raster_ops.append(op)
            add_op_function(op)
        for element in elements_to_add:
            for op in default_raster_ops:
                op.add(element, type="opnode", pos=element_pos)


    def group_elements_overlap(self, g1, g2):
        for e1 in g1:
            e1xmin, e1ymin, e1xmax, e1ymax = e1[1]
            for e2 in g2:
                e2xmin, e2ymin, e2xmax, e2ymax = e2[1]
                if e1xmin <= e2xmax and e1xmax >= e2xmin and e1ymin <= e2ymax and e1ymax >= e2ymin:
                    return True
        return False


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
