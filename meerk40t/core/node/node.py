"""
The elements modifier stores all the element types in a bootstrapped tree. Specific node types added to the tree become
particular class types and the interactions between these types and functions applied are registered in the kernel.

Types:
root: Root Tree element
branch ops: Operation Branch
branch elems: Elements Branch
refelem: Element below op branch which stores specific data.
op: LayerOperation within Operation Branch.
opcmd: CommandOperation within Operation Branch.
elem: Element with Element Branch or subgroup.
file: File Group within Elements Branch
group: Group type within Branch Elems or refelem.
cutcode: CutCode type within Operation Branch and Element Branch.

rasternode: theoretical: would store all the refelems to be rastered. Such that we could store rasters in images.

Tree Functions are to be stored: tree/command/type. These store many functions like the commands.
"""

# Regex expressions
import re

label_truncate_re = re.compile("(:.*)|(\([^ )]*\s.*)")
group_simplify_re = re.compile(
    "(\([^()]+?\))|(SVG(?=Image|Text))|(Simple(?=Line))", re.IGNORECASE
)
subgroup_simplify_re = re.compile("\[[^][]*\]", re.IGNORECASE)
# Ideally we would show the positions in the same UoM as set in Settings (with variable precision depending on UoM,
# but until then element descriptions are shown in mils and 2 decimal places (for opacity) should be sufficient for user to see
element_simplify_re = re.compile("(^Simple(?=Line))|((?<=\.\d{2})(\d+))", re.IGNORECASE)
# image_simplify_re = re.compile("(^SVG(?=Image))|((,\s*)?href=('|\")data:.*?('|\")(,\s?|\s|(?=\))))|((?<=\.\d{2})(\d+))", re.IGNORECASE)
image_simplify_re = re.compile(
    "(^SVG(?=Image))|((,\s*)?href=('|\")data:.*?('|\")(,\s?|\s|(?=\))))|((?<=\d)(\.\d*))",
    re.IGNORECASE,
)

OP_PRIORITIES = ["Dots", "Image", "Raster", "Engrave", "Cut"]

from meerk40t.svgelements import Path, SVGImage, SVG_STRUCT_ATTRIB, Shape, Move, Close, Line


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
                drop_node.add(drag_node.object, type="refelem", pos=0)
                return True
            elif drop_node.type == "refelem":
                op = drop_node.parent
                # Disallow drop of non-image elems onto an refelem inside an Image op.
                # Disallow drop of image elems onto an refelem inside a Dot op.
                if (
                    not isinstance(drag_node.object, SVGImage)
                    and op.operation == "Image"
                ) or (
                    isinstance(drag_node.object, SVGImage) and op.operation == "Dots"
                ):
                    return False
                # Dragging element onto existing refelem in operation adds that element to the op after the refelem.
                drop_index = op.children.index(drop_node)
                op.add(drag_node.object, type="refelem", pos=drop_index)
                return True
            elif drop_node.type == "group":
                # Dragging element onto a group moves it to the group node.
                drop_node.append_child(drag_node)
                return True
        elif drag_node.type == "refelem":
            if drop_node.type == "op":
                # Disallow drop of non-image refelems onto an Image op.
                # Disallow drop of image refelems onto a Dot op.
                if (
                    not isinstance(drag_node.object, SVGImage)
                    and drop_node.operation == "Image"
                ) or (
                    isinstance(drag_node.object, SVGImage)
                    and drop_node.operation == "Dots"
                ):
                    return False
                # Move an refelem to end of op.
                drop_node.append_child(drag_node)
                return True
            if drop_node.type == "refelem":
                op = drop_node.parent
                # Disallow drop of non-image refelems onto an refelem inside an Image op.
                # Disallow drop of image refelems onto an refelem inside a Dot op.
                if (
                    not isinstance(drag_node.object, SVGImage)
                    and op.operation == "Image"
                ) or (
                    isinstance(drag_node.object, SVGImage) and op.operation == "Dots"
                ):
                    return False
                # Move an refelem to after another refelem.
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
                    drop_node.add(e.object, type="refelem")
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
                    drop_node.add(e.object, type="refelem")
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
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
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
