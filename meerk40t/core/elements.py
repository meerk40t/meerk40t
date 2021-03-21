import functools
from copy import copy

from ..device.lasercommandconstants import (
    COMMAND_BEEP,
    COMMAND_FUNCTION,
    COMMAND_HOME,
    COMMAND_MODE_RAPID,
    COMMAND_MOVE,
    COMMAND_WAIT_FINISH,
)
from ..kernel import Modifier
from ..svgelements import (
    Angle,
    Arc,
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
    ArcCut,
    CubicCut,
    CutCode,
    LaserSettings,
    LineCut,
    QuadCut,
    RasterCut,
)


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Elemental", Elemental)
    elif lifecycle == "boot":
        kernel_root = kernel.get_context("/")
        kernel_root.activate("modifier/Elemental")
    elif lifecycle == "ready":
        context = kernel.get_context("/")
        context.signal("rebuild_tree")
        context.signal("refresh_tree")


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

    def notify_added(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_added(node=node, **kwargs)

    def notify_removed(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_removed(node=node, **kwargs)

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

    def modified(self):
        """
        The matrix transformation was changed.
        """
        self.notify_modified(self)
        self._bounds_dirty = True
        self._bounds = None

    def altered(self):
        """
        The data structure was changed.
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

    def unregister(self):
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
        try:
            self.targeted = False
            self.emphasized = False
            self.highlighted = False
            self.modified()
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
        :param single:
        :param pos:
        :return:
        """
        if isinstance(data_object, Node):
            node = data_object
            if node._parent != None:
                raise ValueError("Cannot reparent node on add.")
        else:
            node_class = Node
            try:
                node_class = self._root.bootstrap[type]
            except Exception:
                pass
            node = node_class(data_object)
            node.set_name(name)
        node.type = type

        node._parent = self
        node._root = self.root
        if pos is None:
            self._children.append(node)
        else:
            self._children.insert(pos, node)
        node.notify_added(node, pos=pos)
        return node

    def set_name(self, name):
        """
        Set the name of this node to the name given.
        :param name: Name to be set for this node.
        :return:
        """
        self.name = name
        if name is None:
            if self.name is None:
                try:
                    self.name = self.object.id
                    if self.name is None:
                        self.name = str(self.object)
                except AttributeError:
                    self.name = str(self.object)
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
        new_parent = self
        drag_siblings = new_child.parent.children
        drop_siblings = new_parent.children

        drag_siblings.remove(new_child)
        new_child.notify_removed(new_child)

        drop_siblings.append(new_child)
        new_child._parent = new_parent
        new_child.notify_added(new_child)

    def insert_sibling(self, new_sibling):
        destination_sibling = self
        drag_siblings = new_sibling.parent.children
        drop_siblings = destination_sibling.parent.children

        drop_pos = drop_siblings.index(destination_sibling)

        drag_siblings.remove(new_sibling)
        new_sibling.notify_removed(new_sibling)

        drop_siblings.insert(drop_pos, new_sibling)
        new_sibling._parent = destination_sibling._parent
        new_sibling.notify_added(new_sibling, pos=drop_pos)

    def replace_node(self, *args, **kwargs):
        parent = self._parent
        index = parent._children.index(self)
        parent._children.remove(self)
        self.notify_removed(self)
        node = parent.add(*args, **kwargs, pos=index)
        self._parent = None
        self._root = None
        self.type = None
        return node

    def remove_node(self):
        self._parent._children.remove(self)
        self.notify_removed(self)
        self.item = None
        self._parent = None
        self._root = None
        self.type = None

    def remove_all_children(self):
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


class ElemNode(Node):
    """
    ElemNode is the bootstrapped node type for the elem type. All elem types are bootstrapped into this node object.
    """

    def __init__(self, data_object):
        super(ElemNode, self).__init__(data_object)
        self.last_transform = None
        data_object.node = self

    def __repr__(self):
        return "ElemNode('%s', %s, %s)" % (self.type, str(self.object), str(self._parent))

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

                for element in obj.children:
                    element_copy = copy(element.object)
                    self.add(element_copy, type="opnode")
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

    def as_blob(self):
        c = CutCode()
        settings = self.settings
        if self._operation in ("Cut", "Engrave"):
            for object_path in self.children:
                object_path = object_path.object
                if isinstance(object_path, SVGImage):
                    box = object_path.bbox()
                    plot = Path(
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
                        plot = abs(Path(object_path))
                    else:
                        plot = abs(object_path)

                for seg in plot:
                    if isinstance(seg, Move):
                        pass  # Move operations are ignored.
                    elif isinstance(seg, Close):
                        c.append(LineCut(seg.start, seg.end, settings=settings))
                    elif isinstance(seg, Line):
                        c.append(LineCut(seg.start, seg.end, settings=settings))
                    elif isinstance(seg, QuadraticBezier):
                        c.append(
                            QuadCut(seg.start, seg.control, seg.end, settings=settings)
                        )
                    elif isinstance(seg, CubicBezier):
                        c.append(
                            CubicCut(
                                seg.start,
                                seg.control1,
                                seg.control2,
                                seg.end,
                                settings=settings,
                            )
                        )
                    elif isinstance(seg, Arc):
                        arc = ArcCut(seg, settings=settings)
                        c.append(arc)
        elif self._operation == "Raster":
            direction = settings.raster_direction
            settings.crosshatch = False
            if direction == 4:
                cross_settings = LaserSettings(settings)
                cross_settings.crosshatch = True
                for object_image in self.children:
                    object_image = object_image.object
                    c.append(RasterCut(object_image, settings))
                    c.append(RasterCut(object_image, cross_settings))
            else:
                for object_image in self.children:
                    object_image = object_image.object
                    c.append(RasterCut(object_image, settings))
        elif self._operation == "Image":
                for object_image in self.children:
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
                        c.append(RasterCut(object_image, settings))
                        c.append(RasterCut(object_image, cross_settings))
                    else:
                        c.append(RasterCut(object_image, settings))

        if settings.passes_custom:
            c *= settings.passes
        if len(c) == 0:
            return None
        return c


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


class RootNode(Node):
    """
    RootNode is one of the few directly declarable node-types and serves as the base type for all Node classes.
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
            "elem": ElemNode,
        }
        self.add(type="branch ops", name="Operations")
        self.add(type="branch elems", name="Elements")

    def __repr__(self):
        return "RootNode(%s)" % (str(self.context))

    def listen(self, listener):
        self.listeners.append(listener)

    def unlisten(self, listener):
        self.listeners.remove(listener)

    def notify_added(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "node_added"):
                listen.node_added(node, **kwargs)

    def notify_removed(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "node_removed"):
                listen.node_removed(node, **kwargs)

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
                    func.radio_state = func.radio(node, **func_dict)
                else:
                    func.radio_state = None
                name = func.name.format_map(func_dict)
                func.func_dict = func_dict
                func.real_name = name

                yield func

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

    def tree_operation(self, name, node_type=None, help=None, **kwargs):
        def decorator(func):
            @functools.wraps(func)
            def inner(node, **ik):
                returned = func(node, **ik, **kwargs)
                return returned

            kernel = self.context._kernel
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
            inner.conditionals = list()
            inner.try_conditionals = list()
            inner.calcs = list()
            inner.values = [0]
            registered_name = inner.__name__

            for _in in ins:
                p = "tree/%s/%s" % (_in, registered_name)
                kernel.register(p, inner)
            return inner

        return decorator

    def attach(self, *a, **kwargs):
        context = self.context
        context.elements = self
        context.classify = self.classify
        context.save = self.save
        context.save_types = self.save_types
        context.load = self.load
        context.load_types = self.load_types
        context = self.context
        self._tree = RootNode(context)
        bed_dim = context.get_context('/')
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)

        # Element Select
        @context.console_command(
            "select",
            help="Set these values as the selection.",
            input_type="elements",
            output_type="elements",
        )
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
            self.set_emphasis(data)
            return "elements", list(self.elems(emphasized=True))

        @context.console_command(
            "select+",
            help="Add the input to the selection",
            input_type="elements",
            output_type="elements",
        )
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
            for e in data:
                if not e.emphasized:
                    e.node.emphasized = True
            return "elements", list(self.elems(emphasized=True))

        @context.console_command(
            "select-",
            help="Remove the input data from the selection",
            input_type="elements",
            output_type="elements",
        )
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
            for e in data:
                if e.node.emphasized:
                    e.node.emphasized = False
            return "elements", list(self.elems(emphasized=True))

        @context.console_command(
            "select^",
            help="Toggle the input data in the selection",
            input_type="elements",
            output_type="elements",
        )
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
            for e in data:
                e.node.emphasized = not e.node.emphasized
            return "elements", list(self.elems(emphasized=True))

        # Operation Select
        @context.console_command(
            "select",
            help="Set these values as the selection.",
            input_type="ops",
            output_type="ops",
        )
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
            self.set_emphasis(data)
            return "ops", list(self.ops(emphasized=True))

        @context.console_command(
            "select+",
            help="Add the input to the selection",
            input_type="ops",
            output_type="ops",
        )
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
            for e in data:
                if not e.emphasized:
                    e.emphasized = True
            return "ops", list(self.ops(emphasized=True))

        @context.console_command(
            "select-",
            help="Remove the input data from the selection",
            input_type="ops",
            output_type="ops",
        )
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
            for e in data:
                if e.emphasized:
                    e.emphasize = False
            return "ops", list(self.ops(emphasized=True))

        @context.console_command(
            "select^",
            help="Toggle the input data in the selection",
            input_type="ops",
            output_type="ops",
        )
        def select(command, channel, _, data=None, args=tuple(), **kwargs):
            for e in data:
                e.emphasized = not e.emphasized
            return "ops", list(self.ops(emphasized=True))

        # Element Base
        @context.console_command(
            "element*",
            help="element*, all elements",
            output_type="elements",
        )
        def element(command, channel, _, args=tuple(), **kwargs):
            return "elements", list(self.elems())

        @context.console_command(
            "element~",
            help="element~, all non-selected elements",
            output_type="elements",
        )
        def element(command, channel, _, args=tuple(), **kwargs):
            return "elements", list(self.elems(emphasized=False))

        @context.console_command(
            "element",
            help="element, selected elements",
            output_type="elements",
        )
        def element(command, channel, _, args=tuple(), **kwargs):
            return "elements", list(self.elems(emphasized=True))

        @context.console_command(
            "elements",
            help="list all elements in console",
            output_type="elements",
        )
        def element(command, channel, _, args=tuple(), **kwargs):
            channel(_("----------"))
            channel(_("Graphical Elements:"))
            i = 0
            for e in self.elems():
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "..."
                if e.node.emphasized:
                    channel("%d: * %s" % (i, name))
                else:
                    channel("%d: %s" % (i, name))
                i += 1
            channel("----------")

        @context.console_command(
            r"element([0-9]+,?)+",
            help="element0,3,4,5: elements 0, 3, 4, 5",
            regex=True,
            output_type="elements",
        )
        def element(command, channel, _, args=tuple(), **kwargs):
            arg = command[7:]
            if arg == "":
                return "elements", list(self.elems(emphasized=True))
            elif arg == "*":
                return "elements", list(self.elems())
            elif arg == "~":
                return "elements", list(self.elems(emphasized=False))
            elif arg == "s":
                channel(_("----------"))
                channel(_("Graphical Elements:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "..."
                    if e.node.emphasized:
                        channel("%d: * %s" % (i, name))
                    else:
                        channel("%d: %s" % (i, name))
                    i += 1
                channel("----------")
                return
            else:
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

        @context.console_command(
            "operations", help="operations: list operations", output_type="ops"
        )
        def operation(command, channel, _, args=tuple(), **kwargs):
            channel(_("----------"))
            channel(_("Operations:"))
            for i, operation in enumerate(self.ops()):
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

        @context.console_command(
            "operation.*", help="operation: selected operations", output_type="ops"
        )
        def operation(command, channel, _, args=tuple(), **kwargs):
            return "ops", list(self.ops(emphasized=True))

        @context.console_command(
            "operation*", help="operation*: all operations", output_type="ops"
        )
        def operation(command, channel, _, args=tuple(), **kwargs):
            return "ops", list(self.ops())

        @context.console_command(
            "operation~", help="operation~: non selected operations.", output_type="ops"
        )
        def operation(command, channel, _, args=tuple(), **kwargs):
            return "ops", list(self.ops(emphasized=False))

        @context.console_command(
            "operation", help="operation: selected operations.", output_type="ops"
        )
        def operation(command, channel, _, args=tuple(), **kwargs):
            return "ops", list(self.ops(emphasized=True))

        @context.console_command(
            r"operation(\d+,?)+",
            help="operation0,2: operation #0 and #2",
            regex=True,
            output_type="ops",
        )
        def operation(command, channel, _, args=tuple(), **kwargs):
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

        @context.console_command(
            "tree", help="access and alter tree elements", output_type="tree"
        )
        def tree(
            command, channel, _, data=None, data_type=None, args=tuple(), **kwargs
        ):
            return "tree", self._tree

        @context.console_command(
            "list", help="view tree", input_type="tree", output_type="tree"
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

        @context.console_argument("pos", type=int, help="subtree position")
        @context.console_command(
            "sub", help="sub <#>. Tree Context", input_type="tree", output_type="tree"
        )
        def sub(
            command,
            channel,
            _,
            data=None,
            data_type=None,
            pos=None,
            args=tuple(),
            **kwargs
        ):
            if pos is None:
                raise SyntaxError
            try:
                return "tree", data.children[pos]
            except IndexError:
                raise SyntaxError

        @context.console_command(
            "copy",
            help="duplicate elements",
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
            "delete", help="delete elements", input_type=("elements", "ops")
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

        @context.console_command(
            "merge",
            help="merge elements",
            input_type="elements",
            output_type="elements",
        )
        def merge(command, channel, _, data=None, args=tuple(), **kwargs):
            superelement = Path()
            for e in data:
                if superelement.stroke is None:
                    superelement.stroke = e.stroke
                if superelement.fill is None:
                    superelement.fill = e.fill
                superelement += abs(e)
            self.remove_elements(data)
            self.add_elem(superelement).emphasized = True
            return "elements", [superelement]

        @context.console_command(
            "subpath",
            help="break elements",
            input_type="elements",
            output_type="elements",
        )
        def subpath(command, channel, _, data=None, args=tuple(), **kwargs):
            if not isinstance(data, list):
                data = list(data)
            elems = []
            for e in data:
                node = e.node
                qnode = node.replace_node(type="group", name=node.name)
                p = abs(e)
                for subpath in p.as_subpaths():
                    subelement = Path(subpath)
                    qnode.add(subelement, type="elem")
                elems.append(qnode)
            return "elements", elems

        @context.console_argument("align", type=str, help="Alignment position")
        @context.console_command(
            "align",
            help="align elements",
            input_type=("elements", None),
            output_type="elements",
        )
        def align(command, channel, _, data=None, align=None, args=tuple(), **kwargs):
            if data is None:
                elem_branch = self.get(type="branch elems")
                data = list(elem_branch.flat(types=("elems", "file", "group"), cascade=False, depth=1))
            boundary_points = []
            for d in data:
                # d._bounds_dirty = True
                boundary_points.append(d.bounds)
            if not len(boundary_points):
                return
            left_edge = min([e[0] for e in boundary_points])
            top_edge = min([e[1] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])
            if align == 'top':
                for e in data:
                    subbox = e.bounds
                    top = subbox[1] - top_edge
                    if top != 0:
                        for q in e.flat(types="elem"):
                            q.object *= "translate(0, %f)" % -top
                            q.modified()
            elif align == 'bottom':
                for e in data:
                    subbox = e.bounds
                    bottom = subbox[3] - bottom_edge
                    if bottom != 0:
                        for q in e.flat(types="elem"):
                            q.object *= "translate(0, %f)" % -bottom
                            q.modified()
            elif align == 'left':
                for e in data:
                    subbox = e.bounds
                    left = subbox[0] - left_edge
                    if left != 0:
                        for q in e.flat(types="elem"):
                            q.object *= "translate(%f, 0)" % -left
                            q.modified()
            elif align == 'right':
                for e in data:
                    subbox = e.bounds
                    right = subbox[2] - right_edge
                    if right != 0:
                        for q in e.flat(types="elem"):
                            q.object *= "translate(%f, 0)" % -right
                            q.modified()
            elif align == 'center':
                for e in data:
                    subbox = e.bounds
                    dx = (subbox[0] + subbox[2] - left_edge - right_edge) / 2.0
                    dy = (subbox[1] + subbox[3] - top_edge - bottom_edge) / 2.0
                    for q in e.flat(types="elem"):
                        q.object *= "translate(%f, %f)" % (-dx, -dy)
                        q.modified()
            elif align == 'centerv':
                for e in data:
                    subbox = e.bounds
                    dx = (subbox[0] + subbox[2] - left_edge - right_edge) / 2.0
                    for q in e.flat(types="elem"):
                        q.object *= "translate(%f, 0)" % -dx
                        q.modified()
            elif align == 'centerh':
                for e in data:
                    subbox = e.bounds
                    dy = (subbox[1] + subbox[3] - top_edge - bottom_edge) / 2.0
                    for q in e.flat(types="elem"):
                        q.object *= "translate(0, %f)" % -dy
                        q.modified()
            elif align == 'spaceh':
                distance = right_edge - left_edge
                step = distance / (len(data) - 1)
                for e in data:
                    subbox = e.bounds
                    left = subbox[0] - left_edge
                    left_edge += step
                    if left != 0:
                        for q in e.flat(types="elem"):
                            q.object *= "translate(%f, 0)" % -left
                            q.modified()
            elif align == 'spacev':
                distance = bottom_edge - top_edge
                step = distance / (len(data) - 1)
                for e in data:
                    subbox = e.bounds
                    top = subbox[1] - top_edge
                    top_edge += step
                    if top != 0:
                        for q in e.flat(types="elem"):
                            q.object *= "translate(0, %f)" % -top
                            q.modified()
            return "elements", data

        @context.console_argument("c", type=int, help="number of columns")
        @context.console_argument("r", type=int, help="number of rows")
        @context.console_argument("x", type=Length, help="x distance")
        @context.console_argument("y", type=Length, help="y distance")
        @context.console_command(
            "grid",
            help="grid <columns> <rows> <x_distance> <y_distance>",
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

        @context.console_argument("path_d", help="svg path syntax command.")
        @context.console_command("path", help="path <svg path>")
        def path(command, channel, _, path_d, args=tuple(), **kwargs):
            args = kwargs.get("args", tuple())
            if len(args) == 0:
                raise SyntaxError
            path_d += " ".join(args)
            self.add_element(Path(path_d))

        @context.console_option("name", "n", type=str)
        @context.console_command(
            "clipboard",
            help="clipboard",
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
            help="clipboard copy",
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard(command, channel, _, data=None, args=tuple(), **kwargs):
            destination = self._clipboard_default
            self._clipboard[destination] = [copy(e) for e in data]
            return "elements", self._clipboard[destination]

        @context.console_option("dx", "x", help="paste offset x", type=Length)
        @context.console_option("dy", "y", help="paste offset y", type=Length)
        @context.console_command(
            "paste",
            help="clipboard paste",
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard(
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
            help="clipboard cut",
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard(command, channel, _, data=None, args=tuple(), **kwargs):
            destination = self._clipboard_default
            self._clipboard[destination] = [copy(e) for e in data]
            self.remove_elements(data)
            return "elements", self._clipboard[destination]

        @context.console_command(
            "clear",
            help="clipboard clear",
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard(command, channel, _, data=None, args=tuple(), **kwargs):
            destination = self._clipboard_default
            old = self._clipboard[destination]
            self._clipboard[destination] = None
            return "elements", old

        @context.console_command(
            "contents",
            help="clipboard contents",
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard(command, channel, _, data=None, args=tuple(), **kwargs):
            destination = self._clipboard_default
            return "elements", self._clipboard[destination]

        @context.console_command(
            "list",
            help="clipboard list",
            input_type="clipboard",
        )
        def clipboard(command, channel, _, data=None, args=tuple(), **kwargs):
            for v in self._clipboard:
                k = self._clipboard[v]
                channel("%s: %s" % (str(v).ljust(5), str(k)))

        @context.console_argument("x_pos", type=Length)
        @context.console_argument("y_pos", type=Length)
        @context.console_argument("r_pos", type=Length)
        @context.console_command(
            "circle",
            help="circle <x> <y> <r> or circle <r>",
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
            help="ellipse <cx> <cy> <rx> <ry>",
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
                return "elements", [element]
            else:
                data.append(element)
                return "elements", data

        @context.console_argument(
            "x_pos", type=Length, help="x position for top left corner of rectangle."
        )
        @context.console_argument(
            "y_pos", type=Length, help="y position for top left corner of rectangle."
        )
        @context.console_argument("width", type=Length, help="width of the rectangle.")
        @context.console_argument(
            "height", type=Length, help="height of the rectangle."
        )
        @context.console_option("rx", "x", type=Length, help="rounded rx corner value.")
        @context.console_option("ry", "y", type=Length, help="rounded ry corner value.")
        @context.console_command(
            "rect",
            help="adds rectangle to scene",
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

        @context.console_argument("x0", type=Length, help="start x position")
        @context.console_argument("y0", type=Length, help="start y position")
        @context.console_argument("x1", type=Length, help="end x position")
        @context.console_argument("y1", type=Length, help="end y position")
        @context.console_command(
            "line",
            help="adds line to scene",
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

        @context.console_argument("x0", type=Length, help="start x position")
        @context.console_argument("y0", type=Length, help="start y position")
        @context.console_argument("x1", type=Length, help="end x position")
        @context.console_argument("y1", type=Length, help="end y position")
        @context.console_command(
            "line",
            help="adds line to scene",
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

        @context.console_command(
            "text",
            help="text <text>",
            input_type=(None, "elements"),
            output_type="elements",
        )
        def text(command, channel, _, data=None, remainder=None, **kwargs):
            if remainder is None:
                channel(_("No text specified"))
                return
            text = remainder
            svg_text = SVGText(text)
            self.add_element(svg_text)
            if data is None:
                return "elements", [svg_text]
            else:
                data.append(svg_text)
                return "elements", data

        # @context.console_argument("points", type=float, nargs="*", help='x, y of elements')
        @context.console_command(
            "polygon", help="polygon (<point>, <point>)*", input_type=("elements", None)
        )
        def polygon(command, channel, _, data=None, args=tuple(), **kwargs):
            element = Polygon(list(map(float, args)))
            self.add_element(element)

        # @context.console_argument("points", type=float, nargs="*", help='x, y of elements')
        @context.console_command(
            "polyline",
            help="polyline (<point>, <point>)*",
            input_type=("elements", None),
        )
        def polyline(command, args=tuple(), data=None, **kwargs):
            element = Polyline(list(map(float, args)))
            self.add_element(element)

        @context.console_argument(
            "stroke_width", type=Length, help="Stroke-width for the given stroke"
        )
        @context.console_command(
            "stroke-width",
            help="stroke-width <length>",
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def stroke_width(
            command, channel, _, stroke_width, args=tuple(), data=None, **kwargs
        ):
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
                if hasattr(e, 'node'):
                     e.node.altered()
            context.signal("refresh_scene")
            return "elements", data

        @context.console_argument(
            "color", type=Color, help="Color to color the given stroke"
        )
        @context.console_command(
            "stroke",
            help="stroke <svg color>",
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
                    if hasattr(e, 'node'):
                         e.node.altered()
            else:
                for e in data:
                    e.stroke = Color(color)
                    if hasattr(e, 'node'):
                         e.node.altered()
            context.signal("refresh_scene")
            return "elements", data

        @context.console_argument(
            "color", type=Color, help="color to color the given fill"
        )
        @context.console_command(
            "fill",
            help="fill <svg color>",
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
                    if hasattr(e, 'node'):
                         e.node.altered()
            else:
                for e in data:
                    e.fill = Color(color)
                    if hasattr(e, 'node'):
                         e.node.altered()
            context.signal("refresh_scene")
            return

        @context.console_argument("x_offset", type=Length, help="x offset.")
        @context.console_argument("y_offset", type=Length, help="y offset")
        @context.console_command(
            "outline",
            help="outline the current selected elements",
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

        @context.console_argument("angle", type=Angle.parse, help="angle to rotate by")
        @context.console_option("cx", "x", type=Length, help="center x")
        @context.console_option("cy", "y", type=Length, help="center y")
        @context.console_option(
            "absolute",
            "a",
            type=bool,
            action="store_true",
            help="angle_to absolute angle",
        )
        @context.console_command(
            "rotate",
            help="rotate <angle>",
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
                cx = cx.value(
                    ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
                )
            else:
                cx = (bounds[2] + bounds[0]) / 2.0
            if cy is not None:
                cy = cy.value(
                    ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701
                )
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
                        if hasattr(element, 'node'):
                            element.node.modified()
                else:
                    for element in self.elems(emphasized=True):
                        start_angle = element.rotation
                        amount = rot - start_angle
                        matrix = Matrix(
                            "rotate(%f,%f,%f)" % (Angle(amount).as_degrees, cx, cy)
                        )
                        element *= matrix
                        if hasattr(element, 'node'):
                            element.node.modified()
            except ValueError:
                raise SyntaxError
            context.signal("refresh_scene")
            return "elements", data

        @context.console_argument("scale_x", type=float, help="scale_x value")
        @context.console_argument("scale_y", type=float, help="scale_y value")
        @context.console_option("px", "x", type=Length, help="scale x origin point")
        @context.console_option("py", "y", type=Length, help="scale y origin point")
        @context.console_option(
            "absolute",
            "a",
            type=bool,
            action="store_true",
            help="scale to absolute size",
        )
        @context.console_command(
            "scale",
            help="scale <scale> [<scale-y>]?",
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
                        if hasattr(e, 'node'):
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
                        if hasattr(e, 'node'):
                             e.node.modified()
            except ValueError:
                raise SyntaxError
            context.signal("refresh_scene")
            return "elements", data

        @context.console_argument("tx", type=Length, help="translate x value")
        @context.console_argument("ty", type=Length, help="translate y value")
        @context.console_option(
            "absolute",
            "a",
            type=bool,
            action="store_true",
            help="translate to absolute position",
        )
        @context.console_command(
            "translate",
            help="translate <tx> <ty>",
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
                tx = tx.value(
                    ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
                )
            else:
                tx = 0
            if ty is not None:
                ty = ty.value(
                    ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701
                )
            else:
                ty = 0
            m = Matrix("translate(%f,%f)" % (tx, ty))
            try:
                if not absolute:
                    for e in data:
                        e *= m
                        if hasattr(e, 'node'):
                             e.node.modified()
                else:
                    for e in data:
                        otx = e.transform.value_trans_x()
                        oty = e.transform.value_trans_y()
                        ntx = tx - otx
                        nty = ty - oty
                        m = Matrix("translate(%f,%f)" % (ntx, nty))
                        e *= m
                        if hasattr(e, 'node'):
                             e.node.modified()
            except ValueError:
                raise SyntaxError
            context.signal("refresh_scene")
            return "elements", data

        @context.console_argument(
            "x_pos", type=Length, help="x position for top left corner"
        )
        @context.console_argument(
            "y_pos", type=Length, help="y position for top left corner"
        )
        @context.console_argument("width", type=Length, help="new width of selected")
        @context.console_argument("height", type=Length, help="new height of selected")
        @context.console_command(
            "resize",
            help="resize <x-pos> <y-pos> <width> <height>",
            input_type=(None, "elements"),
            output_type="elements",
        )
        def resize(
            command, x_pos, y_pos, width, height, data=None, args=tuple(), **kwargs
        ):
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
                x, y, x1, y1 = self.selected_area()
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
                    if hasattr(e, 'node'):
                         e.node.modified()
                context.signal("refresh_scene")
                return "elements", data
            except (ValueError, ZeroDivisionError):
                raise SyntaxError

        @context.console_argument("sx", type=float, help="scale_x value")
        @context.console_argument("kx", type=float, help="skew_x value")
        @context.console_argument("sy", type=float, help="scale_y value")
        @context.console_argument("ky", type=float, help="skew_y value")
        @context.console_argument("tx", type=Length, help="translate_x value")
        @context.console_argument("ty", type=Length, help="translate_y value")
        @context.console_command(
            "matrix",
            help="matrix <sx> <kx> <sy> <ky> <tx> <ty>",
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
                    tx.value(
                        ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
                    ),
                    ty.value(
                        ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701
                    ),
                )
                for e in data:
                    try:
                        if e.lock:
                            continue
                    except AttributeError:
                        pass

                    e.transform = Matrix(m)
                    if hasattr(e, 'node'):
                         e.node.modified()
            except ValueError:
                raise SyntaxError
            context.signal("refresh_scene")
            return

        @context.console_command(
            "reset",
            help="reset affine transformations",
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
                if hasattr(e, 'node'):
                     e.node.modified()
            context.signal("refresh_scene")
            return "elements", data

        @context.console_command(
            "reify",
            help="reify affine transformations",
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
                if hasattr(e, 'node'):
                     e.node.altered()
            context.signal("refresh_scene")
            return "elements", data

        @context.console_command(
            "classify",
            help="classify elements into operations",
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
            help="declassify selected elements",
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

        @context.console_option("append", "a", type=bool, action="store_true", default=False)
        @context.console_command("note", help="note <note>")
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

        @context.console_option("speed", "s", type=float)
        @context.console_option("power", "p", type=float)
        @context.console_option("step", "S", type=int)
        @context.console_option("overscan", "o", type=Length)
        @context.console_option("color", "c", type=Color)
        @context.console_command(
            ("cut", "engrave", "raster", "imageop"),
            help="group current elements into operation type",
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
            if data is not None:
                op.children.extend(data)
            self.add_op(op)
            return "ops", [op]

        @context.console_argument("step_size", type=int, help="raster step size")
        @context.console_command(
            "step", help="step <raster-step-size>", input_type=("ops", "elements")
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
                if hasattr(element, 'node'):
                     element.node.modified()
                self.context.signal("element_property_update", element)
                self.context.signal("refresh_scene")
            return

        @context.console_command(
            "trace_hull", help="trace the convex hull of current elements"
        )
        def trace_hull(command, channel, _, args=tuple(), **kwargs):
            if context.active is None:
                return
            spooler = context.active.spooler
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
            "trace_quick", help="quick trace the bounding box of current elements"
        )
        def trace_quick(command, channel, _, args=tuple(), **kwargs):
            if context.active is None:
                return
            spooler = context.active.spooler
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

        _ = self.context._kernel.translation

        @self.tree_operation(
            _("Ungroup Elements"), node_type=("group", "file"), help=""
        )
        def ungroup_elements(node, **kwargs):
            for n in list(node.children):
                node.insert_sibling(n)
            node.remove_node()

        @self.tree_operation(
            _("Group Elements"), node_type="elem", help=""
        )
        def group_elements(node, **kwargs):
            # group_node = node.parent.add_sibling(node, type="group", name="Group")
            group_node = node.parent.add(type="group", name="Group")
            for e in list(self.elems(emphasized=True)):
                node = e.node
                group_node.append_child(node)

        @self.tree_operation(
            _("Execute Job"),
            node_type="op",
            help="Execute Job for the particular element.",
        )
        def execute_job(node, **kwargs):
            # self.context.open("window/JobPreview", self.gui, "0", selected=True)
            node.emphasized = True
            self.context("plan0 copy-selected\n")
            self.context("window -p / open JobPreview 0\n")

        @self.tree_operation(_("Clear All"), node_type="branch ops", help="")
        def clear_all(node, **kwargs):
            self.context("operation* delete\n")

        @self.tree_operation(_("Clear All"), node_type="branch elems", help="")
        def clear_all_ops(node, **kwargs):
            self.context("element* delete\n")

        @self.tree_operation(
            _("Remove: {name}"), node_type="op", help=""
        )
        def remove_types(node, **kwargs):
            # self.context("operation delete\n")
            node.remove_node()
            # self.remove_orphaned_opnodes()
            self.set_emphasis(None)

        @self.tree_operation(
            _("Remove: {name}"), node_type="elem", help=""
        )
        def remove_types(node, **kwargs):
            # self.context("element delete\n")
            node.remove_node()
            self.remove_orphaned_opnodes()
            self.set_emphasis(None)

        @self.tree_operation(
            _("Remove: {name}"), node_type="file", help=""
        )
        def remove_types(node, **kwargs):
            node.remove_all_children()
            node.remove_node()
            self.remove_orphaned_opnodes()
            self.set_emphasis(None)

        @self.tree_operation(
            _("Remove: {name}"), node_type="opnode", help=""
        )
        def remove_types(node, **kwargs):
            node.remove_node()
            self.set_emphasis(None)

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
            _("Reverse Layer Order"),
            node_type=("op", "branch elems", "branch ops"),
            help="reverse the items within this subitem",
        )
        def reverse_layer_order(node, **kwargs):
            node.reverse()
            self.context.signal("rebuild_tree", 0)

        @self.tree_operation(
            _("Refresh Classification"), node_type="branch ops", help=""
        )
        def refresh_clasifications(node, **kwargs):
            context = self.context
            elements = context.elements
            elements.remove_elements_from_operations(list(elements.elems()))
            elements.classify(list(elements.elems()))
            self.context.signal("rebuild_tree", 0)

        @self.tree_operation(
            _("Set Other/Blue/Red Classify"), node_type="branch ops", help=""
        )
        def default_classifications(node, **kwargs):
            self.context.elements.load_default()

        @self.tree_operation(
            _("Set Basic Classification"), node_type="branch ops", help=""
        )
        def basic_classifications(node, **kwargs):
            self.context.elements.load_default2()

        @self.tree_operation(_("Add Operation"), node_type="branch ops", help="")
        def add_operation_operation(node, **kwargs):
            self.context.elements.add_op(LaserOperation())

        @self.tree_submenu(_("Special Operations"))
        @self.tree_operation(_("Add Home"), node_type="branch ops", help="")
        def add_operation_home(node, **kwargs):
            self.context.elements.add_op(CommandOperation("Home", COMMAND_HOME))

        @self.tree_submenu(_("Special Operations"))
        @self.tree_operation(_("Add Beep"), node_type="branch ops", help="")
        def add_operation_beep(node, **kwargs):
            self.context.elements.add_op(CommandOperation("Beep", COMMAND_BEEP))

        @self.tree_submenu(_("Special Operations"))
        @self.tree_operation(_("Add Move Origin"), node_type="branch ops", help="")
        def add_operation_origin(node, **kwargs):
            self.context.elements.add_op(CommandOperation("Origin", COMMAND_MOVE, 0, 0))

        @self.tree_submenu(_("Special Operations"))
        @self.tree_operation(_("Add Interrupt"), node_type="branch ops", help="")
        def add_operation_interrupt(node, **kwargs):
            self.context.elements.add_op(
                CommandOperation(
                    "Interrupt",
                    COMMAND_FUNCTION,
                    self.context.console_function("interrupt\n"),
                )
            )

        @self.tree_submenu(_("Special Operations"))
        @self.tree_operation(_("Add Shutdown"), node_type="branch ops", help="")
        def add_operation_shutdown(node, **kwargs):
            self.context.elements.add_op(
                CommandOperation(
                    "Shutdown",
                    COMMAND_FUNCTION,
                    self.context.console_function("quit\n"),
                )
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

        @self.tree_operation(
            _("Duplicate Operation"),
            node_type="op",
            help="duplicate operation element nodes",
        )
        def duplicate_operation(node, **kwargs):
            op = LaserOperation(node)
            self.context.elements.add_op(op)
            for e in node.children:
                op.add(e.object, type="opnode")

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_conditional(lambda node: node.operation in ("Image", "Engrave", "Cut"))
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
        @self.tree_conditional(lambda node: node.operation in ("Image", "Engrave", "Cut"))
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

        def radio_match(node, passvalue=1, **kwargs):
            return node.settings.passes == passvalue

        @self.tree_submenu(_("Set Operation Passes"))
        @self.tree_radio(radio_match)
        @self.tree_iterate("passvalue", 1, 10)
        @self.tree_operation(_("Passes={passvalue}"), node_type="op", help="")
        def set_n_passes(node, passvalue=1, **kwargs):
            node.settings.passes = passvalue
            node.settings.passes_custom = passvalue != 1
            self.context.signal("element_property_update", node)

        @self.tree_conditional(lambda node: node.operation in ("Raster", "Image"))
        @self.tree_submenu(_("Step"))
        @self.tree_iterate("i", 1, 10)
        @self.tree_operation(
            _("Step {iterator}"),
            node_type="op",
            help="Change raster step values of operation",
        )
        def set_step_n(node, i=1, **kwargs):
            element = node.object
            element.raster_step = i
            self.context.signal("element_property_update", node.object)


        @self.tree_conditional(lambda node: node.operation in ("Raster", "Image"))
        @self.tree_operation(
            _("Make Raster Image"),
            node_type="op",
            help="Convert a vector element into a raster element.",
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
            self.clear_elements_and_operations()
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

        @self.tree_conditional(lambda node: isinstance(node.object, Shape) and not isinstance(node.object, Path))
        @self.tree_operation(
            _("Convert To Path"), node_type=("elem",), help=""
        )
        def reset_user_changes(node, copies=1, **kwargs):
            node.object = abs(Path(node.object))
            node.object.node = node
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
            self.context(
                "scale %f %f %f %f\n" % (scale, scale, center_x, center_y)
            )

        @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Rotate"))
        @self.tree_values(
            "i",
            values=(
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                -2,
                -3,
                -4,
                -5,
                -6,
                -7,
                -8,
                -9,
                -10,
                -11,
                -12,
                -13,
            ),
        )
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
            if hasattr(element, 'node'):
                     element.node.modified()
            self.context.signal("element_property_update", node.object)
            self.context.gui.request_refresh()

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
                self.context(
                    "image threshold %f %f\n" % (threshold_min, threshold_max)
                )

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_conditional_try(lambda node: node.object.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Unlock Manipulations"), node_type="elem", help="")
        def image_unlock_manipulations(node, **kwargs):
            self.context("image unlock\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Dither to 1 bit"), node_type="elem", help="")
        def image_dither(node, **kwargs):
            self.context("image dither\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Invert Image"), node_type="elem", help="")
        def image_invert(node, **kwargs):
            self.context("image invert\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Mirror Horizontal"), node_type="elem", help="")
        def image_mirror(node, **kwargs):
            context("image mirror\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Flip Vertical"), node_type="elem", help="")
        def image_flip(node, **kwargs):
            self.context("image flip\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Rotate CW"), node_type="elem", help="")
        def image_cw(node, **kwargs):
            self.context("image cw\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Rotate CCW"), node_type="elem", help="")
        def image_ccw(node, **kwargs):
            self.context("image ccw\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Save output.png"), node_type="elem", help="")
        def image_save(node, **kwargs):
            self.context("image save output.png\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("RasterWizard"))
        @self.tree_values("script", values=self.context.match("raster_script", suffix=True))
        @self.tree_operation(_("RasterWizard: {script}"), node_type="elem", help="")
        def image_rasterwizard_open(node, script=None, **kwargs):
            self.context("window open -p / RasterWizard %s\n" % script)

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Apply Raster Script"))
        @self.tree_values("script", values=self.context.match("raster_script", suffix=True))
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

        self.listen(self)

    def detach(self, *a, **kwargs):
        context = self.context
        settings = context.derive("operations")
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
                        value = value.value
                    op_set.write_persistent(key, value)
        settings.close_subpaths()
        self.unlisten(self)

    def boot(self, *a, **kwargs):
        self.context.setting(bool, "operation_default_empty", True)
        settings = self.context.derive("operations")
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
        if not len(ops) and self.context.operation_default_empty:
            self.load_default()
            return
        self.add_ops([o for o in ops if o is not None])

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
        context_root = self.context.get_context("/")
        if hasattr(element, "stroke") and element.stroke is None:
            element.stroke = Color(stroke)
        node = context_root.elements.add_elem(element)
        context_root.elements.set_emphasis([element])
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
        for item in elements.flat(types=("elem", "file", "group"), depth=depth, **kwargs):
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

    def add_elem(self, element):
        """
        Add an element. Wraps it within a node, and appends it to the tree.

        :param element:
        :return:
        """
        element_branch = self._tree.get(type="branch elems")
        node = element_branch.add(element, type="elem")
        self.context.signal("element_added", element)
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
        for op in reversed(list(operations.flat(types=("op", "opnode")))):
            if op is not None:
                op.remove_node()

    def clear_elements(self):
        for e in reversed(list(self.elems_nodes())):
            if e is not None:
                e.remove_node()

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

    def remove_orphaned_opnodes(self):
        """
        Remove any opnodes whose objects do not appear in the elem list.

        :return:
        """
        elements_list = list(self.elems())
        for i, op in enumerate(self.ops()):
            for e in list(op.children):
                if e.object not in elements_list:
                    e.remove_node()

    def selected_area(self):
        if self._emphasized_bounds_dirty:
            self.validate_selected_area()
        return self._emphasized_bounds

    def validate_selected_area(self):
        boundary_points = []
        for e in self.elems_nodes(emphasized=True):
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
        :param node_context:
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

            if s.emphasized:
                if emphasize is None or s not in emphasize:
                    s.emphasized = False
            else:
                if emphasize is not None and (
                    s in emphasize or (hasattr(s, "object") and s.object in emphasize)
                ):
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
            image_added = False
            if hasattr(element, "operation"):
                add_op_function(element)
                continue
            if element is None:
                continue
            for op in operations:
                if op.operation == "Raster":
                    if image_added:
                        continue  # already added to an image operation, is not added here.
                    if element.stroke is not None and op.color == abs(element.stroke):
                        op.add(element, type="opnode")
                        was_classified = True
                    elif isinstance(element, SVGImage):
                        op.add(element, type="opnode")
                        was_classified = True
                    elif element.fill is not None and element.fill.value is not None:
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
                    image_added = True
                elif isinstance(element, SVGText):
                    op.add(element)
                    was_classified = True
            if not was_classified:
                if element.stroke is not None and element.stroke.value is not None:
                    op = LaserOperation(
                        operation="Engrave", color=element.stroke, speed=35.0
                    )
                    add_op_function(op)
                    op.add(element, type="opnode")
                    operations.append(op)

    def load(self, pathname, **kwargs):
        kernel = self.context._kernel
        for loader_name in kernel.match("load"):
            loader = kernel.registered[loader_name]
            for description, extensions, mimetype in loader.load_types():
                if str(pathname).lower().endswith(extensions):
                    try:
                        results = loader.load(self.context, self, pathname, **kwargs)
                    except FileNotFoundError:
                        return False
                    if not results:
                        continue
                    return True

    def load_types(self, all=True):
        kernel = self.context._kernel
        filetypes = []
        if all:
            filetypes.append("All valid types")
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
        kernel = self.context._kernel
        for save_name in kernel.match("save"):
            saver = kernel.registered[save_name]
            for description, extension, mimetype in saver.save_types():
                if pathname.lower().endswith(extension):
                    saver.save(self.context, pathname, "default")
                    return True
        return False

    def save_types(self):
        kernel = self.context._kernel
        filetypes = []
        for save_name in kernel.match("save"):
            saver = kernel.registered[save_name]
            for description, extension, mimetype in saver.save_types():
                filetypes.append("%s (%s)" % (description, extension))
                filetypes.append("*.%s" % (extension))
        return "|".join(filetypes)
