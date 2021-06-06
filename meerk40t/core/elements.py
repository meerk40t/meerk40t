import functools
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
        self.name = None

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
        elif drag_node.type == "group":
            if drop_node.type == "elem":
                drop_node.insert_sibling(drag_node)
                return True
            elif drop_node.type == "group" or drop_node.type == "file":
                drop_node.append_child(drag_node)
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

    @property
    def bounds(self):
        if self._bounds_dirty:
            try:
                self._bounds = self.object.bbox()
            except AttributeError:
                self._bounds = None
            for e in self._children:
                bb = e.bounds
                if bb is None:
                    continue
                elif self._bounds is None:
                    self._bounds = bb
                else:
                    aa = self._bounds
                    self._bounds = (
                        min(aa[0], bb[0]),
                        min(aa[1], bb[1]),
                        max(aa[2], bb[2]),
                        max(aa[3], bb[3]),
                    )
            self._bounds_dirty = False
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
        for object in objects:
            self.add(object, type=type, name=name, pos=pos)
            if pos is not None:
                pos += 1

    def add(self, data_object=None, type=None, name=None, pos=None):
        """
        Add a new node bound to the data_object of the type to the current node.
        If the data_object itself is a node already it is merely attached.

        :param data_object:
        :param type:
        :param name:
        :param pos:
        :return:
        """
        if isinstance(data_object, Node):
            node = data_object
            if node._parent is not None:
                raise ValueError("Cannot reparent node on add.")
        else:
            node_class = Node
            try:
                node_class = self._root.bootstrap[type]
            except Exception:
                pass
            node = node_class(data_object)
            node.set_name(name)
            if self.root is not None:
                self.root.notify_created(node)
        node.type = type

        node._parent = self
        node._root = self.root
        if pos is None:
            self._children.append(node)
        else:
            self._children.insert(pos, node)
        node.notify_attached(node, pos=pos)
        return node

    def _get_node_name(self, node) -> str:
        """
        Creates a cascade of different values that could give the node name. Label, inkscape:label, id, node-object str,
        node str. If something else provides a superior name it should be added in here.
        """
        try:
            attribs = node.object.values[SVG_STRUCT_ATTRIB]
            return attribs["label"]
        except (AttributeError, KeyError):
            pass

        try:
            attribs = node.object.values[SVG_STRUCT_ATTRIB]
            return attribs["{http://www.inkscape.org/namespaces/inkscape}label"]
        except (AttributeError, KeyError):
            pass

        try:
            return node.object.id
        except AttributeError:
            pass

        if node.object is not None:
            return str(node.object)
        return str(node)

    def set_name(self, name):
        """
        Set the name of this node to the name given.
        :param name: Name to be set for this node.
        :return:
        """
        self.name = name
        if name is None:
            if self.name is None:
                self.name = self._get_node_name(self)
        else:
            self.name = name

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
        for ref in self._references:
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
        self.output = True
        self.show = True

        self._status_value = "Queued"
        self.color = Color("black")
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
        if len(args) == 1:
            obj = args[0]
            if isinstance(obj, SVGElement):
                self.add(obj, type="opnode")
            elif isinstance(obj, LaserOperation):
                self._operation = obj.operation

                self.color = Color(obj.color)
                self.output = obj.output
                self.show = obj.show

                self.settings = LaserSettings(obj.settings)
        if self.operation == "Cut":
            if self.settings.speed is None:
                self.settings.speed = 10.0
            if self.settings.power is None:
                self.settings.power = 1000.0
        if self.operation == "Engrave":
            if self.settings.speed is None:
                self.settings.speed = 35.0
            if self.settings.power is None:
                self.settings.power = 1000.0
        if self.operation == "Raster":
            if self.settings.raster_step == 0:
                self.settings.raster_step = 1
            if self.settings.speed is None:
                self.settings.speed = 150.0
            if self.settings.power is None:
                self.settings.power = 1000.0

    def __repr__(self):
        return "LaserOperation('%s', %s)" % (self.type, str(self._operation))

    def __str__(self):
        op = self._operation
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
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
                        estimate += length / (39.3701 * self.settings.speed)
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
                        39.3701 * self.settings.speed
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

    def as_blob(self, cut_inner_first=True):
        requires_constraint = False
        blob = CutCode()
        blob.mode = "grouped"
        context = blob
        settings = self.settings
        for p in range(settings.implicit_passes):
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
                        closed = isinstance(subpath[-1], Close)
                        constrained = self._operation == "Cut" and cut_inner_first
                        if closed and constrained:
                            requires_constraint = True
                        group = CutGroup(
                            context, constrained=constrained, closed=closed
                        )
                        context.append(group)
                        group.path = Path(subpath)

                        context = group
                        for seg in subpath:
                            if isinstance(seg, Move):
                                pass  # Move operations are ignored.
                            elif isinstance(seg, Close):
                                context.append(
                                    LineCut(seg.start, seg.end, settings=settings)
                                )
                            elif isinstance(seg, Line):
                                context.append(
                                    LineCut(seg.start, seg.end, settings=settings)
                                )
                            elif isinstance(seg, QuadraticBezier):
                                context.append(
                                    QuadCut(
                                        seg.start,
                                        seg.control,
                                        seg.end,
                                        settings=settings,
                                    )
                                )
                            elif isinstance(seg, CubicBezier):
                                context.append(
                                    CubicCut(
                                        seg.start,
                                        seg.control1,
                                        seg.control2,
                                        seg.end,
                                        settings=settings,
                                    )
                                )
                        context = context.parent
            elif self._operation == "Raster":
                direction = settings.raster_direction
                settings.crosshatch = False
                group = CutGroup(context)
                context.append(group)
                context = group
                if direction == 4:
                    cross_settings = LaserSettings(settings)
                    cross_settings.crosshatch = True
                    for object_image in self.children:
                        object_image = object_image.object
                        context.append(RasterCut(object_image, settings))
                        context.append(RasterCut(object_image, cross_settings))
                else:
                    for object_image in self.children:
                        object_image = object_image.object
                        context.append(RasterCut(object_image, settings))
                context = context.parent
            elif self._operation == "Image":
                group = CutGroup(context)
                context.append(group)
                context = group
                for object_image in self.children:
                    group = CutGroup(context)
                    context.append(group)
                    context = group
                    object_image = object_image.object
                    settings = LaserSettings(self.settings)
                    try:
                        settings.raster_step = int(object_image.values["raster_step"])
                    except KeyError:
                        settings.raster_step = 1
                    direction = settings.raster_direction
                    settings.crosshatch = False
                    if direction == 4:
                        cross_settings = LaserSettings(settings)
                        cross_settings.crosshatch = True
                        context.append(RasterCut(object_image, settings))
                        context.append(RasterCut(object_image, cross_settings))
                    else:
                        context.append(RasterCut(object_image, settings))

                    context = context.parent
                context = context.parent
        blob.correct_empty()
        if len(blob) == 0:
            return None
        if requires_constraint:
            blob.mode = "constrained"
        return blob


class CutNode(Node):
    """
    Node type "cutcode"
    """

    def __init__(self, data_object, **kwargs):
        super().__init__(data_object, type="cutcode", **kwargs)
        self.output = True
        self.operation = "Cutcode"

    def __repr__(self):
        return "CutNode('%s', '%s')" % (self.name, str(self.command))

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

    def as_blob(self, cut_inner_first=None):
        return self.object


class CommandOperation(Node):
    """
    CommandOperation is a basic command operation. It contains nothing except a single command to be executed.

    Node type "cmdop"
    """

    def __init__(self, name, command, *args, **kwargs):
        super().__init__(command, type="cmdop")
        self.name = name
        self.command = command
        self.args = args
        self.output = True
        self.operation = "Command"

    def __repr__(self):
        return "CommandOperation('%s', '%s')" % (self.name, str(self.command))

    def __str__(self):
        return "%s: %s" % (self.name, str(self.args))

    def __copy__(self):
        return CommandOperation(self.name, self.command, *self.args)

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
        self.set_name("Project")
        self.type = "root"
        self.context = context
        self.listeners = []

        self.elements = context.elements
        self.bootstrap = {
            "op": LaserOperation,
            "cmdop": CommandOperation,
            "lasercode": LaserCodeNode,
            "elem": ElemNode,
            "opnode": OpNode,
            "cutcode": CutNode,
        }
        self.add(type="branch ops", name="Operations")
        self.add(type="branch elems", name="Elements")

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
                "name": str(node.name)[:15],
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
            func.separate = True
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
            inner.separate = False
            inner.separate_before = False
            inner.conditionals = list()
            inner.try_conditionals = list()
            inner.calcs = list()
            inner.values = [0]
            registered_name = inner.__name__

            for _in in ins:
                p = "tree/%s/%s" % (_in, registered_name)
                if p in kernel.registered:
                    raise NameError("A function of this name was already registered.")
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

        # ==========
        # OPERATION BASE
        # ==========
        @context.console_command(
            "operations", help=_("show information about operations")
        )
        def element(**kwargs):
            context(".operation* list\n")

        @context.console_command(
            "operation.*", help=_("operation: selected operations"), output_type="ops"
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

        @context.console_argument("name", help=_("name to save the operation under"))
        @context.console_command(
            "save",
            help=_("Save current operations to persistent settings"),
            input_type="ops",
            output_type="ops",
        )
        def save(command, channel, _, data=None, name=None, **kwargs):
            if name is None:
                raise SyntaxError
            if "/" in name:
                raise SyntaxError
            self.save_persistent_operations(name)
            return "ops", list(self.ops())

        @context.console_argument("name", help=_("name to save the operation under"))
        @context.console_command(
            "load",
            help=_("Load operations from persistent settings"),
            input_type="ops",
            output_type="ops",
        )
        def save(command, channel, _, data=None, name=None, **kwargs):
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
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
            self.set_emphasis(data)
            return "ops", data

        @context.console_command(
            "select+",
            help=_("Add the input to the selection"),
            input_type="ops",
            output_type="ops",
        )
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
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
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
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
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
            ops = list(self.ops(emphasized=True))
            for e in data:
                try:
                    ops.remove(e)
                except ValueError:
                    ops.append(e)
            self.set_emphasis(ops)
            return "ops", ops

        @context.console_command(
            "list",
            help=_("Show information about the chained data"),
            input_type="ops",
            output_type="ops",
        )
        def operation(command, channel, _, data=None, **kwargs):
            channel(_("----------"))
            channel(_("Operations:"))
            index_ops = list(self.ops())
            for operation in data:
                i = index_ops.index(operation)
                selected = operation.emphasized
                select = " *" if selected else "  "
                color = (
                    "None"
                    if not hasattr(operation, "color") or operation.color is None
                    else Color(operation.color).hex
                )
                name = "%d: %s %s - %s" % (i, str(operation), select, color)
                channel(name)
                if isinstance(operation, list):
                    for q, oe in enumerate(operation):
                        stroke = (
                            "None"
                            if not hasattr(oe, "stroke") or oe.stroke is None
                            else oe.stroke.hex
                        )
                        fill = (
                            "None"
                            if not hasattr(oe, "stroke") or oe.fill is None
                            else oe.fill.hex
                        )
                        ident = str(oe.id)
                        name = "%s%d: %s-%s s:%s f:%s" % (
                            "".ljust(5),
                            q,
                            str(type(oe).__name__),
                            ident,
                            stroke,
                            fill,
                        )
                        channel(name)
            channel(_("----------"))

        @context.console_option("speed", "s", type=float)
        @context.console_option("power", "p", type=float)
        @context.console_option("step", "S", type=int)
        @context.console_option("overscan", "o", type=Length)
        @context.console_option("color", "c", type=Color)
        @context.console_option("passes", "x", type=int)
        @context.console_command(
            ("cut", "engrave", "raster", "imageop", "dots"),
            help=_(
                "<cut/engrave/raster/imageop> - group the elements into this operation"
            ),
            input_type=(None, "elements"),
            output_type="ops",
        )
        def makeop(
            command,
            channel,
            _,
            data,
            color=None,
            speed=None,
            power=None,
            step=None,
            overscan=None,
            passes=None,
            args=tuple(),
            **kwargs
        ):
            op = LaserOperation()
            if color is not None:
                op.color = color
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
                        ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
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
            "step", help=_("step <raster-step-size>"), input_type=("ops", "elements")
        )
        def step(command, channel, _, step_size=None, args=tuple(), **kwargs):
            if step_size is None:
                found = False
                for op in self.ops(emphasized=True):
                    if op.operation in ("Raster", "Image"):
                        step = op.settings.raster_step
                        channel(_("Step for %s is currently: %d") % (str(op), step))
                        found = True
                for element in self.elems(emphasized=True):
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
                    channel(_("No raster operations selected."))
                return
            for op in self.ops(emphasized=True):
                if op.operation in ("Raster", "Image"):
                    op.settings.raster_step = step_size
                    self.context.signal("element_property_update", op)
            for element in self.elems(emphasized=True):
                element.values["raster_step"] = str(step_size)
                m = element.transform
                tx = m.e
                ty = m.f
                element.transform = Matrix.scale(float(step_size), float(step_size))
                element.transform.post_translate(tx, ty)
                if hasattr(element, "node"):
                    element.node.modified()
                self.context.signal("element_property_update", element)
                self.context.signal("refresh_scene")
            return

        # ==========
        # ELEMENT/OPERATION SUBCOMMANDS
        # ==========
        @context.console_command(
            "copy",
            help=_("duplicate elements"),
            input_type=("elements", "ops"),
            output_type=("elements", "ops"),
        )
        def e_copy(
            command, channel, _, data=None, data_type=None, args=tuple(), **kwargs
        ):
            add_elem = list(map(copy, data))
            if data_type == "ops":
                self.add_ops(add_elem)
            else:
                self.add_elems(add_elem)
            return data_type, add_elem

        @context.console_command(
            "delete", help=_("delete elements"), input_type=("elements", "ops")
        )
        def e_delete(
            command, channel, _, data=None, data_type=None, args=tuple(), **kwargs
        ):
            channel(_("deleting."))
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
            help=_("show information about elements"),
        )
        def element(**kwargs):
            context(".element* list\n")

        @context.console_command(
            "element*",
            help=_("element*, all elements"),
            output_type="elements",
        )
        def element(**kwargs):
            return "elements", list(self.elems())

        @context.console_command(
            "element~",
            help=_("element~, all non-selected elements"),
            output_type="elements",
        )
        def element(**kwargs):
            return "elements", list(self.elems(emphasized=False))

        @context.console_command(
            "element",
            help=_("element, selected elements"),
            output_type="elements",
        )
        def element(**kwargs):
            return "elements", list(self.elems(emphasized=True))

        @context.console_command(
            r"element([0-9]+,?)+",
            help=_("element0,3,4,5: chain a list of specific elements"),
            regex=True,
            output_type="elements",
        )
        def element(command, channel, _, **kwargs):
            arg = command[7:]
            element_list = []
            for value in arg.split(","):
                try:
                    value = int(value)
                except ValueError:
                    continue
                try:
                    e = self.get_elem(value)
                    element_list.append(e)
                except IndexError:
                    channel(_("index %d out of range") % value)
            return "elements", element_list

        # ==========
        # ELEMENT SUBCOMMANDS
        # ==========
        @context.console_command(
            "select",
            help=_("Set these values as the selection."),
            input_type="elements",
            output_type="elements",
        )
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
            self.set_emphasis(data)
            return "elements", data

        @context.console_command(
            "select+",
            help=_("Add the input to the selection"),
            input_type="elements",
            output_type="elements",
        )
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
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
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
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
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
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
            channel(_("----------"))
            channel(_("Graphical Elements:"))
            index_list = list(self.elems())
            for e in data:
                i = index_list.index(e)
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "..."
                if e.node.emphasized:
                    channel("%d: * %s" % (i, name))
                else:
                    channel("%d: %s" % (i, name))
            channel("----------")
            return "elements", data

        @context.console_command(
            "merge",
            help=_("merge elements"),
            input_type="elements",
            output_type="elements",
        )
        def merge(command, channel, _, data=None, args=tuple(), **kwargs):
            superelement = Path()
            for e in data:
                if not isinstance(e, Shape):
                    continue
                if superelement.stroke is None:
                    superelement.stroke = e.stroke
                if superelement.fill is None:
                    superelement.fill = e.fill
                superelement += abs(e)
            self.remove_elements(data)
            self.add_elem(superelement).emphasized = True
            self.classify([superelement])
            return "elements", [superelement]

        @context.console_command(
            "subpath",
            help=_("break elements"),
            input_type="elements",
            output_type="elements",
        )
        def subpath(command, channel, _, data=None, args=tuple(), **kwargs):
            if not isinstance(data, list):
                data = list(data)
            elements_nodes = []
            elements = []
            for e in data:
                node = e.node
                group_node = node.replace_node(type="group", name=node.name)
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
        def align(command, channel, _, data=None, align=None, remainder=None, **kwargs):
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
            for d in data:
                boundary_points.append(d.bounds)
            if not len(boundary_points):
                return
            left_edge = min([e[0] for e in boundary_points])
            top_edge = min([e[1] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])
            if align == "top":
                for e in data:
                    subbox = e.bounds
                    top = subbox[1] - top_edge
                    matrix = "translate(0, %f)" % -top
                    if top != 0:
                        for q in e.flat(types=("elem", "group", "file")):
                            obj = q.object
                            if obj is not None:
                                obj *= matrix
                            q.modified()
            elif align == "bottom":
                for e in data:
                    subbox = e.bounds
                    bottom = subbox[3] - bottom_edge
                    matrix = "translate(0, %f)" % -bottom
                    if bottom != 0:
                        for q in e.flat(types=("elem", "group", "file")):
                            obj = q.object
                            if obj is not None:
                                obj *= matrix
                            q.modified()
            elif align == "left":
                for e in data:
                    subbox = e.bounds
                    left = subbox[0] - left_edge
                    matrix = "translate(%f, 0)" % -left
                    if left != 0:
                        for q in e.flat(types=("elem", "group", "file")):
                            obj = q.object
                            if obj is not None:
                                obj *= matrix
                            q.modified()
            elif align == "right":
                for e in data:
                    subbox = e.bounds
                    right = subbox[2] - right_edge
                    matrix = "translate(%f, 0)" % -right
                    if right != 0:
                        for q in e.flat(types=("elem", "group", "file")):
                            obj = q.object
                            if obj is not None:
                                obj *= matrix
                            q.modified()
            elif align == "center":
                for e in data:
                    subbox = e.bounds
                    dx = (subbox[0] + subbox[2] - left_edge - right_edge) / 2.0
                    dy = (subbox[1] + subbox[3] - top_edge - bottom_edge) / 2.0
                    matrix = "translate(%f, %f)" % (-dx, -dy)
                    for q in e.flat(types=("elem", "group", "file")):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
            elif align == "centerv":
                for e in data:
                    subbox = e.bounds
                    dx = (subbox[0] + subbox[2] - left_edge - right_edge) / 2.0
                    matrix = "translate(%f, 0)" % -dx
                    for q in e.flat(types=("elem", "group", "file")):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
            elif align == "centerh":
                for e in data:
                    subbox = e.bounds
                    dy = (subbox[1] + subbox[3] - top_edge - bottom_edge) / 2.0
                    matrix = "translate(0, %f)" % -dy
                    for q in e.flat(types=("elem", "group", "file")):
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
                    subbox = e.bounds
                    left = subbox[0] - left_edge
                    left_edge += step
                    matrix = "translate(%f, 0)" % -left
                    if left != 0:
                        for q in e.flat(types=("elem", "group", "file")):
                            obj = q.object
                            if obj is not None:
                                obj *= matrix
                            q.modified()
            elif align == "spacev":
                distance = bottom_edge - top_edge
                step = distance / (len(data) - 1)
                for e in data:
                    subbox = e.bounds
                    top = subbox[1] - top_edge
                    top_edge += step
                    matrix = "translate(0, %f)" % -top
                    if top != 0:
                        for q in e.flat(types=("elem", "group", "file")):
                            obj = q.object
                            if obj is not None:
                                obj *= matrix
                            q.modified()
            elif align == "topleft":
                for e in data:
                    dx = -left_edge
                    dy = -top_edge
                    matrix = "translate(%f, %f)" % (dx, dy)
                    for q in e.flat(types=("elem", "group", "file")):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
                self.context.signal("refresh_scene")
            elif align == "bedcenter":
                for e in data:
                    bw = bed_dim.bed_width
                    bh = bed_dim.bed_height
                    dx = (bw * MILS_IN_MM - left_edge - right_edge) / 2.0
                    dy = (bh * MILS_IN_MM - top_edge - bottom_edge) / 2.0
                    matrix = "translate(%f, %f)" % (dx, dy)
                    for q in e.flat(types=("elem", "group", "file")):
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
                    bw = bed_dim.bed_width
                    bh = bed_dim.bed_height
                    from ..svgelements import Viewbox

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
                    for q in e.flat(types=("elem", "group", "file")):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
                self.context.signal("refresh_scene")
            return "elements", data

        @context.console_argument("c", type=int, help=_("number of columns"))
        @context.console_argument("r", type=int, help=_("number of rows"))
        @context.console_argument("x", type=Length, help=_("x distance"))
        @context.console_argument("y", type=Length, help=_("y distance"))
        @context.console_command(
            "grid",
            help=_("grid <columns> <rows> <x_distance> <y_distance>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def grid(
            command,
            channel,
            _,
            c: int,
            r: int,
            x: Length,
            y: Length,
            data=None,
            args=tuple(),
            **kwargs
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0 or self._emphasized_bounds is None:
                channel(_("No item selected."))
                return
            if r is None:
                raise SyntaxError
            if x is not None and y is not None:
                x = x.value(ppi=1000)
                y = y.value(ppi=1000)
            else:
                try:
                    bounds = self._emphasized_bounds
                    x = bounds[2] - bounds[0]
                    y = bounds[3] - bounds[1]
                except Exception:
                    raise SyntaxError
            if isinstance(x, Length) or isinstance(y, Length):
                raise SyntaxError
            y_pos = 0
            for j in range(r):
                x_pos = 0
                for k in range(c):
                    if j != 0 or k != 0:
                        add_elem = list(map(copy, data))
                        for e in add_elem:
                            e *= "translate(%f, %f)" % (x_pos, y_pos)
                        self.add_elems(add_elem)
                    x_pos += x
                y_pos += y

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
        def circle(command, x_pos, y_pos, r_pos, data=None, args=tuple(), **kwargs):
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
        def ellipse(
            command, x_pos, y_pos, rx_pos, ry_pos, data=None, args=tuple(), **kwargs
        ):
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
        def rect(
            command,
            x_pos,
            y_pos,
            width,
            height,
            rx=None,
            ry=None,
            data=None,
            args=tuple(),
            **kwargs
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
        def line(command, x0, y0, x1, y1, data=None, args=tuple(), **kwargs):
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
        def line_command(command, x0, y0, x1, y1, data=None, args=tuple(), **kwargs):
            """
            Draws an svg line in the scene.
            """
            if y1 is None:
                raise SyntaxError
            line = SimpleLine(x0, y0, x1, y1)
            line.render(
                ppi=1000.0,
                width="%fmm" % bed_dim.bed_width,
                height="%fmm" % bed_dim.bed_height,
            )
            self.add_element(line)
            if data is None:
                return "elements", [line]
            else:
                data.append(line)
                return "elements", data

        @context.console_argument("text", type=str, help=_("quoted string of text"))
        @context.console_command(
            "text",
            help=_("text <text>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def text(command, channel, _, data=None, text=None, **kwargs):
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
        def polygon(command, channel, _, data=None, args=tuple(), **kwargs):
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
        def polyline(command, args=tuple(), data=None, **kwargs):
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
            "path", help=_("convert any shapes to paths"), input_type="elements"
        )
        def path(data, **kwargs):
            for e in data:
                try:
                    node = e.node
                    node.replace_object(abs(Path(node.object)))
                    node.altered()
                except AttributeError:
                    pass

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
        def stroke_width(command, channel, _, stroke_width, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            if stroke_width is None:
                channel(_("----------"))
                channel(_("Stroke-Width Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "..."
                    if e.stroke is None or e.stroke == "none":
                        channel(_("%d: stroke = none - %s") % (i, name))
                    else:
                        channel(_("%d: stroke = %s - %s") % (i, e.stroke_width, name))
                    i += 1
                channel(_("----------"))
                return

            if len(data) == 0:
                channel(_("No selected elements."))
                return
            stroke_width = stroke_width.value(
                ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
            )
            if isinstance(stroke_width, Length):
                raise SyntaxError
            for e in data:
                e.stroke_width = stroke_width
                if hasattr(e, "node"):
                    e.node.altered()
            context.signal("refresh_scene")
            return "elements", data

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
        def stroke(command, channel, _, color, args=tuple(), data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            if color is None:
                channel(_("----------"))
                channel(_("Stroke Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "..."
                    if e.stroke is None or e.stroke == "none":
                        channel(_("%d: stroke = none - %s") % (i, name))
                    else:
                        channel(_("%d: stroke = %s - %s") % (i, e.stroke.hex, name))
                    i += 1
                channel(_("----------"))
                return
            if len(data) == 0:
                channel(_("No selected elements."))
                return

            if color == "none":
                for e in data:
                    e.stroke = None
                    if hasattr(e, "node"):
                        e.node.altered()
            else:
                for e in data:
                    e.stroke = Color(color)
                    if hasattr(e, "node"):
                        e.node.altered()
            context.signal("refresh_scene")
            return "elements", data

        @context.console_argument(
            "color", type=Color, help=_("color to color the given fill")
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
        def fill(command, channel, _, color, data=None, args=tuple(), **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            if color is None:
                channel(_("----------"))
                channel(_("Fill Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "..."
                    if e.fill is None or e.fill == "none":
                        channel(_("%d: fill = none - %s") % (i, name))
                    else:
                        channel(_("%d: fill = %s - %s") % (i, e.fill.hex, name))
                    i += 1
                channel(_("----------"))
                return
            if color == "none":
                for e in data:
                    e.fill = None
                    if hasattr(e, "node"):
                        e.node.altered()
            else:
                for e in data:
                    e.fill = Color(color)
                    if hasattr(e, "node"):
                        e.node.altered()
            context.signal("refresh_scene")
            return

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
        def outline(
            command,
            channel,
            _,
            x_offset=None,
            y_offset=None,
            data=None,
            args=tuple(),
            **kwargs
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
        def rotate(
            command,
            channel,
            _,
            angle,
            cx=None,
            cy=None,
            absolute=False,
            data=None,
            args=tuple(),
            **kwargs
        ):
            if angle is None:
                channel(_("----------"))
                channel(_("Rotate Values:"))
                i = 0
                for element in self.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + "..."
                    channel(
                        _("%d: rotate(%fturn) - %s")
                        % (i, element.rotation.as_turns, name)
                    )
                    i += 1
                channel(_("----------"))
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
                cx = cx.value(ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701)
            else:
                cx = (bounds[2] + bounds[0]) / 2.0
            if cy is not None:
                cy = cy.value(ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701)
            else:
                cy = (bounds[3] + bounds[1]) / 2.0
            matrix = Matrix("rotate(%fdeg,%f,%f)" % (rot, cx, cy))
            try:
                if not absolute:
                    for element in self.elems(emphasized=True):
                        try:
                            if element.lock:
                                continue
                        except AttributeError:
                            pass

                        element *= matrix
                        if hasattr(element, "node"):
                            element.node.modified()
                else:
                    for element in self.elems(emphasized=True):
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
        def scale(
            command,
            channel,
            _,
            scale_x=None,
            scale_y=None,
            px=None,
            py=None,
            absolute=False,
            data=None,
            args=tuple(),
            **kwargs
        ):
            if scale_x is None:
                channel(_("----------"))
                channel(_("Scale Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "..."
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
                channel(_("----------"))
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
                    ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
                )
            else:
                center_x = (bounds[2] + bounds[0]) / 2.0
            if py is not None:
                center_y = py.value(
                    ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701
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
        def translate(
            command,
            channel,
            _,
            tx,
            ty,
            absolute=False,
            data=None,
            args=tuple(),
            **kwargs
        ):
            if tx is None:
                channel(_("----------"))
                channel(_("Translate Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "..."
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
                channel(_("----------"))
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            if tx is not None:
                tx = tx.value(ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701)
            else:
                tx = 0
            if ty is not None:
                ty = ty.value(ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701)
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
        def resize(command, x_pos, y_pos, width, height, data=None, **kwargs):
            if height is None:
                raise SyntaxError
            try:
                x_pos = x_pos.value(
                    ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
                )
                y_pos = y_pos.value(
                    ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701
                )
                width = width.value(
                    ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
                )
                height = height.value(
                    ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701
                )
                area = self.selected_area()
                if area is None:
                    return
                x, y, x1, y1 = area
                w, h = x1 - x, y1 - y
                sx = width / w
                sy = height / h
                m = Matrix(
                    "translate(%f,%f) scale(%f,%f) translate(%f,%f)"
                    % (x_pos, y_pos, sx, sy, -x, -y)
                )
                if data is None:
                    data = list(self.elems(emphasized=True))
                for e in data:
                    try:
                        if e.lock:
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
        def matrix(
            command,
            channel,
            _,
            sx,
            kx,
            sy,
            ky,
            tx,
            ty,
            data=None,
            args=tuple(),
            **kwargs
        ):
            if tx is None:
                channel(_("----------"))
                channel(_("Matrix Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "..."
                    channel("%d: %s - %s" % (i, str(e.transform), name))
                    i += 1
                channel(_("----------"))
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
                    tx.value(ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701),
                    ty.value(ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701),
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
        def reset(command, channel, _, data=None, args=tuple(), **kwargs):
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
                    name = name[:50] + "..."
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
        def reify(command, channel, _, data=None, args=tuple(), **kwargs):
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
                    name = name[:50] + "..."
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
        def classify(command, channel, _, data=None, args=tuple(), **kwargs):
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
        def declassify(command, channel, _, data=None, args=tuple(), **kwargs):
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
        def tree(
            command, channel, _, data=None, data_type=None, args=tuple(), **kwargs
        ):
            return "tree", self._tree

        @context.console_command(
            "list", help=_("view tree"), input_type="tree", output_type="tree"
        )
        def tree_list(
            command, channel, _, data=None, data_type=None, args=tuple(), **kwargs
        ):
            if data is None:
                data = self._tree
            channel(_("----------"))
            channel(_("Tree:"))
            path = ""
            for i, node in enumerate(data.children):
                channel("%s:%d %s" % (path, i, str(node.name)))
            channel(_("----------"))
            return "tree", data

        @context.console_argument(
            "path_d", type=str, help=_("svg path syntax command (quoted).")
        )
        @context.console_command("path", help=_("path <svg path>"))
        def path(path_d, **kwargs):
            try:
                self.add_element(Path(path_d))
            except ValueError:
                raise SyntaxError(_("Not a valid path_d string (try quotes)"))

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
        def clipboard(
            command, channel, _, data=None, name=None, args=tuple(), **kwargs
        ):
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
        def clipboard_copy(command, channel, _, data=None, args=tuple(), **kwargs):
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
        def clipboard_paste(
            command, channel, _, data=None, dx=None, dy=None, args=tuple(), **kwargs
        ):
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
                        ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
                    )
                if dy is None:
                    dy = 0
                else:
                    dy = dy.value(
                        ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701
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
        def clipboard_cut(command, channel, _, data=None, args=tuple(), **kwargs):
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
        def clipboard_clear(command, channel, _, data=None, args=tuple(), **kwargs):
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
        def clipboard_contents(command, channel, _, data=None, args=tuple(), **kwargs):
            destination = self._clipboard_default
            return "elements", self._clipboard[destination]

        @context.console_command(
            "list",
            help=_("clipboard list"),
            input_type="clipboard",
        )
        def clipboard_list(command, channel, _, data=None, args=tuple(), **kwargs):
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
            "trace_hull", help=_("trace the convex hull of current elements")
        )
        def trace_hull(command, channel, _, args=tuple(), **kwargs):
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
        def trace_quick(command, channel, _, args=tuple(), **kwargs):
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
        @self.tree_operation(_("Operation Properties"), node_type="op", help="")
        def operation_property(node, **kwargs):
            self.context.open("window/OperationProperty", self.context.gui, node=node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, Path))
        @self.tree_operation(_("Path Properties"), node_type="elem", help="")
        def path_property(node, **kwargs):
            self.context.open("window/PathProperty", self.context.gui, node=node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, SVGText))
        @self.tree_operation(_("Text Properties"), node_type="elem", help="")
        def text_property(node, **kwargs):
            self.context.open("window/TextProperty", self.context.gui, node=node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_operation(_("Image Properties"), node_type="elem", help="")
        def image_property(node, **kwargs):
            self.context.open("window/ImageProperty", self.context.gui, node=node)

        @self.tree_operation(
            _("Ungroup Elements"), node_type=("group", "file"), help=""
        )
        def ungroup_elements(node, **kwargs):
            for n in list(node.children):
                node.insert_sibling(n)
            node.remove_node()  # Removing group/file node.

        @self.tree_operation(_("Group Elements"), node_type="elem", help="")
        def group_elements(node, **kwargs):
            # group_node = node.parent.add_sibling(node, type="group", name="Group")
            group_node = node.parent.add(type="group", name="Group")
            for e in list(self.elems(emphasized=True)):
                node = e.node
                group_node.append_child(node)

        @self.tree_operation(_("Enable/Disable Ops"), node_type="op", help="")
        def toggle_n_operations(node, **kwargs):
            for n in self.ops(emphasized=True):
                n.output = not n.output
                n.notify_update()

        @self.tree_submenu(_("Convert Operation"))
        @self.tree_operation(_("Convert Raster"), node_type="op", help="")
        def convert_operation_raster(node, **kwargs):
            node.operation = "Raster"

        @self.tree_submenu(_("Convert Operation"))
        @self.tree_operation(_("Convert Engrave"), node_type="op", help="")
        def convert_operation_engrave(node, **kwargs):
            node.operation = "Engrave"

        @self.tree_submenu(_("Convert Operation"))
        @self.tree_operation(_("Convert Cut"), node_type="op", help="")
        def convert_operation_cut(node, **kwargs):
            node.operation = "Cut"

        @self.tree_submenu(_("Convert Operation"))
        @self.tree_operation(_("Convert Image"), node_type="op", help="")
        def convert_operation_image(node, **kwargs):
            node.operation = "Image"

        def radio_match(node, i=1, **kwargs):
            return node.settings.raster_step == i

        @self.tree_conditional(lambda node: node.operation == "Raster")
        @self.tree_submenu(_("Step"))
        @self.tree_radio(radio_match)
        @self.tree_iterate("i", 1, 10)
        @self.tree_operation(
            _("Step {i}"),
            node_type="op",
            help=_("Change raster step values of operation"),
        )
        def set_step_n(node, i=1, **kwargs):
            settings = node.settings
            settings.raster_step = i
            self.context.signal("element_property_update", node)

        def radio_match(node, passvalue=1, **kwargs):
            return node.settings.passes == passvalue and node.settings.passes_custom

        @self.tree_submenu(_("Set Operation Passes"))
        @self.tree_radio(radio_match)
        @self.tree_iterate("passvalue", 1, 10)
        @self.tree_operation(_("Passes={passvalue}"), node_type="op", help="")
        def set_n_passes(node, passvalue=1, **kwargs):
            node.settings.passes = passvalue
            node.settings.passes_custom = passvalue != 1
            self.context.signal("element_property_update", node)

        @self.tree_separator_after()
        @self.tree_operation(
            _("Execute Job"),
            node_type="op",
            help=_("Execute Job for the particular element."),
        )
        def execute_job(node, **kwargs):
            # self.context.open("window/ExecuteJob", self.gui, "0", selected=True)
            node.emphasized = True
            self.context("plan0 copy-selected\n")
            self.context("window open ExecuteJob 0\n")

        @self.tree_separator_after()
        @self.tree_operation(
            _("Compile and Simulate"),
            node_type="op",
            help=_("Compile Job and run simulation"),
        )
        def compile_and_simulate(node, **kwargs):
            node.emphasized = True
            self.context(
                "plan0 copy-selected preprocess validate blob preopt optimize\n"
            )
            self.context("window open Simulation 0\n")

        @self.tree_operation(_("Clear All"), node_type="branch ops", help="")
        def clear_all(node, **kwargs):
            self.context("operation* delete\n")

        @self.tree_operation(_("Clear All"), node_type="branch elems", help="")
        def clear_all_ops(node, **kwargs):
            self.context("element* delete\n")
            self.elem_branch.remove_all_children()

        @self.tree_operation(
            _("Remove: {name}"),
            node_type=(
                "op",
                "elem",
                "cmdop",
                "file",
                "group",
                "opnode",
                "lasercode",
                "cutcode",
            ),
            help="",
        )
        def remove_type_op(node, **kwargs):
            node.remove_node()
            self.set_emphasis(None)

        @self.tree_operation(
            _("Convert to Cutcode"),
            node_type="lasercode",
            help="",
        )
        def lasercode2cut(node, **kwargs):
            node.replace_node(CutCode.from_lasercode(node.object), type="cutcode")

        @self.tree_operation(
            _("Convert to Path"),
            node_type="cutcode",
            help="",
        )
        def cutcode2pathcut(node, **kwargs):
            cutcode = node.object
            elements = cutcode.as_elements()
            n = None
            for element in elements:
                n = self.elem_branch.add(element, type="elem")
            node.remove_node()
            if n is not None:
                n.focus()

        @self.tree_conditional(lambda node: len(list(self.elems(emphasized=True))) > 1)
        @self.tree_calc("ecount", lambda i: len(list(self.elems(emphasized=True))))
        @self.tree_operation(
            _("Remove: {ecount} objects"), node_type=("elem", "opnode"), help=""
        )
        def remove_n_objects(node, **kwargs):
            self.context("element delete\n")

        @self.tree_submenu(_("Clone Reference"))
        @self.tree_iterate("copies", 1, 10)
        @self.tree_operation(_("Make {copies} copies."), node_type="opnode", help="")
        def clone_element_op(node, copies=1, **kwargs):
            index = node.parent.children.index(node)
            for i in range(copies):
                node.parent.add(node.object, type="opnode", pos=index)
            node.modified()
            self.context.signal("rebuild_tree", 0)

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_operation(
            _("Reverse Order"),
            node_type=("op", "group", "branch elems", "file", "branch ops"),
            help=_("reverse the items within this subitem"),
        )
        def reverse_layer_order(node, **kwargs):
            node.reverse()
            self.context.signal("rebuild_tree", 0)

        @self.tree_separator_after()
        @self.tree_operation(
            _("Refresh Classification"), node_type="branch ops", help=""
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
        @self.tree_operation(_("Load: {opname}"), node_type="branch ops", help="")
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
        @self.tree_operation(_("{opname}"), node_type="branch ops", help="")
        def save_ops(node, opname="saved", **kwargs):
            self.context("operation save %s\n" % opname)

        @self.tree_separator_before()
        @self.tree_operation(_("Add Operation"), node_type="branch ops", help="")
        def add_operation_operation(node, **kwargs):
            self.context.elements.add_op(LaserOperation())

        @self.tree_submenu(_("Special Operations"))
        @self.tree_operation(_("Add Home"), node_type="branch ops", help="")
        def add_operation_home(node, **kwargs):
            self.context.elements.op_branch.add(
                CommandOperation("Home", COMMAND_HOME), type="cmdop"
            )

        @self.tree_submenu(_("Special Operations"))
        @self.tree_operation(_("Add Beep"), node_type="branch ops", help="")
        def add_operation_beep(node, **kwargs):
            self.context.elements.op_branch.add(
                CommandOperation("Beep", COMMAND_BEEP), type="cmdop"
            )

        @self.tree_submenu(_("Special Operations"))
        @self.tree_operation(_("Add Move Origin"), node_type="branch ops", help="")
        def add_operation_origin(node, **kwargs):
            self.context.elements.op_branch.add(
                CommandOperation("Origin", COMMAND_MOVE, 0, 0), type="cmdop"
            )

        @self.tree_submenu(_("Special Operations"))
        @self.tree_operation(_("Add Interrupt"), node_type="branch ops", help="")
        def add_operation_interrupt(node, **kwargs):
            self.context.elements.op_branch.add(
                CommandOperation(
                    "Interrupt",
                    COMMAND_FUNCTION,
                    self.context.console_function("interrupt\n"),
                ),
                type="cmdop",
            )

        @self.tree_submenu(_("Special Operations"))
        @self.tree_operation(_("Add Shutdown"), node_type="branch ops", help="")
        def add_operation_shutdown(node, **kwargs):
            self.context.elements.op_branch.add(
                CommandOperation(
                    "Shutdown",
                    COMMAND_FUNCTION,
                    self.context.console_function("quit\n"),
                ),
                type="cmdop",
            )

        @self.tree_operation(
            _("Reclassify Operations"), node_type="branch elems", help=""
        )
        def reclassify_operations(node, **kwargs):
            context = self.context
            elements = context.elements
            elems = list(elements.elems())
            elements.remove_elements_from_operations(elems)
            elements.classify(list(elements.elems()))
            self.context.signal("rebuild_tree", 0)

        @self.tree_operation(
            _("Duplicate Operation"),
            node_type="op",
            help=_("duplicate operation element nodes"),
        )
        def duplicate_operation(node, **kwargs):
            copy_op = LaserOperation(node)
            self.add_op(copy_op)
            for n in node.children:
                try:
                    obj = n.object
                    copy_op.add(obj, type="opnode")
                except AttributeError:
                    pass

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_conditional(
            lambda node: node.operation in ("Image", "Engrave", "Cut")
        )
        @self.tree_submenu(_("Passes"))
        @self.tree_iterate("copies", 1, 10)
        @self.tree_operation(_("Add {copies} pass(es)."), node_type="op", help="")
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
        @self.tree_submenu(_("Duplicate"))
        @self.tree_iterate("copies", 1, 10)
        @self.tree_operation(
            _("Duplicate elements {copies} time(s)."), node_type="op", help=""
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
            _("Make Raster Image"),
            node_type="op",
            help=_("Convert a vector element into a raster element."),
        )
        def make_raster_image(node, **kwargs):
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

        @self.tree_operation(_("Reload {name}"), node_type="file", help="")
        def reload_file(node, **kwargs):
            filepath = node.filepath
            node.remove_node()
            self.load(filepath)

        @self.tree_submenu(_("Duplicate"))
        @self.tree_iterate("copies", 1, 10)
        @self.tree_operation(_("Make {copies} copies."), node_type="elem", help="")
        def duplicate_n_element(node, copies, **kwargs):
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
            _("Reset User Changes"), node_type=("branch elem", "elem"), help=""
        )
        def reset_user_changes(node, copies=1, **kwargs):
            self.context("reset\n")

        @self.tree_conditional(
            lambda node: isinstance(node.object, Shape)
            and not isinstance(node.object, Path)
        )
        @self.tree_operation(_("Convert To Path"), node_type=("elem",), help="")
        def convert_to_path(node, copies=1, **kwargs):
            node.replace_object(abs(Path(node.object)))
            node.altered()

        @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Scale"))
        @self.tree_iterate("scale", 1, 25)
        @self.tree_calc("scale_percent", lambda i: "%0.f" % (600.0 / float(i)))
        @self.tree_operation(
            _("Scale {scale_percent}%"), node_type="elem", help="Scale Element"
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

        @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Rotate"))
        @self.tree_values("i", values=tuple([i for i in range(2, -14, -1) if i != 0]))
        @self.tree_calc(
            "angle", lambda i: "%0.f" % Angle.turns(1.0 / float(i)).as_degrees
        )
        @self.tree_operation(_(u"Rotate turn/{i}, {angle}°"), node_type="elem", help="")
        def rotate_elem_amount(node, i, **kwargs):
            value = 1.0 / float(i)
            child_objects = Group()
            child_objects.extend(node.objects_of_children(SVGElement))
            bounds = child_objects.bbox()
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self.context("rotate %fturn %f %f\n" % (value, center_x, center_y))

        @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(_("Reify User Changes"), node_type="elem", help="")
        def reify_elem_changes(node, **kwargs):
            self.context("reify\n")

        @self.tree_conditional(lambda node: isinstance(node.object, Path))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(_("Break Subpaths"), node_type="elem", help="")
        def break_subpath_elem(node, **kwargs):
            self.context("element subpath\n")

        @self.tree_operation(
            _("Merge Items"),
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
        @self.tree_submenu(_("Step"))
        @self.tree_radio(radio_match)
        @self.tree_iterate("i", 1, 10)
        @self.tree_operation(_("Step {i}"), node_type="elem", help="")
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
            self.context.signal("element_property_update", node.object)
            self.context.signal("refresh_scene")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(_("Actualize Pixels"), node_type="elem", help="")
        def image_actualize_pixels(node, **kwargs):
            self.context("image resample\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("ZDepth Divide"))
        @self.tree_iterate("divide", 2, 10)
        @self.tree_operation(
            _("Divide Into {divide} Images"), node_type="elem", help=""
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
        @self.tree_operation(_("Unlock Manipulations"), node_type="elem", help="")
        def image_unlock_manipulations(node, **kwargs):
            self.context("image unlock\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Dither to 1 bit"), node_type="elem", help="")
        def image_dither(node, **kwargs):
            self.context("image dither\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Invert Image"), node_type="elem", help="")
        def image_invert(node, **kwargs):
            self.context("image invert\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Mirror Horizontal"), node_type="elem", help="")
        def image_mirror(node, **kwargs):
            context("image mirror\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Flip Vertical"), node_type="elem", help="")
        def image_flip(node, **kwargs):
            self.context("image flip\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Rotate CW"), node_type="elem", help="")
        def image_cw(node, **kwargs):
            self.context("image cw\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Rotate CCW"), node_type="elem", help="")
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
        @self.tree_operation(_("RasterWizard: {script}"), node_type="elem", help="")
        def image_rasterwizard_open(node, script=None, **kwargs):
            self.context("window open RasterWizard %s\n" % script)

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Apply Raster Script"))
        @self.tree_values(
            "script", values=list(self.context.match("raster_script", suffix=True))
        )
        @self.tree_operation(_("Apply: {script}"), node_type="elem", help="")
        def image_rasterwizard_apply(node, script=None, **kwargs):
            self.context("image wizard %s\n" % script)

        @self.tree_conditional_try(lambda node: hasattr(node.object, "as_elements"))
        @self.tree_operation(_("Convert to SVG"), node_type="elem", help="")
        def cutcode_convert_svg(node, **kwargs):
            self.context.elements.add_elems(node.object.as_elements())

        @self.tree_conditional_try(lambda node: hasattr(node.object, "generate"))
        @self.tree_operation(_("Process as Operation"), node_type="elem", help="")
        def cutcode_operation(node, **kwargs):
            self.context.elements.add_op(node.object)

        @self.tree_operation(
            _("Expand All Children"),
            node_type=("op", "branch elems", "branch ops", "group", "file", "root"),
            help="Expand all children of this given node.",
        )
        def expand_all_children(node, **kwargs):
            node.notify_expand()

        @self.tree_reference(lambda node: node.object.node)
        @self.tree_operation(_("Reference"), node_type="opnode", help="")
        def reference_opnode(node, **kwargs):
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
            op_set = settings.derive(str(i))
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
        self.add_op(LaserOperation(operation="Raster", color="black", speed=140.0))
        self.add_op(LaserOperation(operation="Engrave", color="blue", speed=35.0))
        self.add_op(LaserOperation(operation="Cut", color="red", speed=10.0))
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
        self.add_op(LaserOperation(operation="Raster", color="black", speed=140.0))
        self.add_op(LaserOperation(operation="Engrave", color="green", speed=35.0))
        self.add_op(LaserOperation(operation="Engrave", color="blue", speed=35.0))
        self.add_op(LaserOperation(operation="Engrave", color="magenta", speed=35.0))
        self.add_op(LaserOperation(operation="Engrave", color="cyan", speed=35.0))
        self.add_op(LaserOperation(operation="Engrave", color="yellow", speed=35.0))
        self.add_op(LaserOperation(operation="Cut", color="red", speed=10.0))
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
        for i, elem in enumerate(self.elems(**kwargs)):
            if i == index:
                return elem
        raise IndexError

    def add_op(self, op):
        operation_branch = self._tree.get(type="branch ops")
        op.set_name(str(op))
        operation_branch.add(op, type="op")

    def add_ops(self, adding_ops):
        operation_branch = self._tree.get(type="branch ops")
        items = []
        for op in adding_ops:
            op.set_name(str(op))
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
            emphasized=True  # "file", "group"
            # Reverted from https://github.com/meerk40t/meerk40t/commit/ac613d9f5a8eb24fa98f6de6ce7eb0570bd5e348
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

    def classify(self, elements, operations=None, add_op_function=None):
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
        if operations is None:
            operations = list(self.ops())
        if add_op_function is None:
            add_op_function = self.add_op
        for element in elements:
            was_classified = False
            if hasattr(element, "operation"):
                add_op_function(element)
                continue
            if element is None:
                continue
            for op in operations:
                if op.operation == "Raster":
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
                ):
                    op.add(element, type="opnode")
                    was_classified = True
                elif op.operation == "Image" and isinstance(element, SVGImage):
                    op.add(element, type="opnode")
                    was_classified = True
                    break  # May only classify in one image operation.
                elif (
                    op.operation == "Dots"
                    and isinstance(element, Path)
                    and len(element) == 2
                    and isinstance(element[0], Move)
                    and isinstance(element[1], Close)
                ):
                    op.add(element, type="opnode")
                    was_classified = True
                    break  # May only classify in Dots.
            if not was_classified:
                if element.stroke is not None and element.stroke.value is not None:
                    if element.stroke == Color("red"):
                        op = LaserOperation(operation="Cut", color=element.stroke)
                    else:
                        op = LaserOperation(operation="Engrave", color=element.stroke)
                    add_op_function(op)
                    op.add(element, type="opnode")
                    operations.append(op)

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
                    if not results:
                        continue
                    return True

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
                filetypes.append("*.%s" % (extension))
        return "|".join(filetypes)
