"""
The 'elements' service stores all the element types in a bootstrapped tree. Specific node types added to the tree become
particular class types and the interactions between these types and functions applied are registered in the kernel.

Types:
* root: Root Tree element
* branch ops: Operation Branch
* branch elems: Elements Branch
* branch reg: Regmark Branch
* reference: Element below op branch which stores specific data.
* op: LayerOperation within Operation Branch.
* elem: Element with Element Branch or subgroup.
* file: File Group within Elements Branch
* group: Group type within Branch Elems or refelem.
* cutcode: CutCode type within Operation Branch and Element Branch.

rasternode: theoretical: would store all the refelems to be rastered. Such that we could store rasters in images.

Tree Functions are to be stored: tree/command/type. These store many functions like the commands.
"""
from enum import Enum


# LINEJOIN
# Value	arcs | bevel |miter | miter-clip | round
# Default value	miter
class Linejoin(Enum):
    JOIN_ARCS = 0
    JOIN_BEVEL = 1
    JOIN_MITER = 2
    JOIN_MITER_CLIP = 3
    JOIN_ROUND = 4


# LINECAP
# Value	butt | round | square
# Default value	butt
class Linecap(Enum):
    CAP_BUTT = 0
    CAP_ROUND = 1
    CAP_SQUARE = 2


# FILL-RULE
# Value	nonzero | evenodd
# Default value	nonzero
class Fillrule(Enum):
    FILLRULE_NONZERO = 0
    FILLRULE_EVENODD = 1


class Node:
    """
    Nodes are elements within the tree which stores most of the objects in Elements.
    """

    def __init__(self, type=None, *args, **kwargs):
        super().__init__()
        self._children = list()
        self._root = None
        self._parent = None
        self._references = list()

        self.type = type

        self._points = list()
        self._points_dirty = True

        self._selected = False
        self._emphasized = False
        self._highlighted = False
        self._target = False

        self._opened = False

        self._bounds = None
        self._bounds_dirty = True

        self.item = None
        self.icon = None
        self.cache = None
        self.id = None

    def __repr__(self):
        return "Node('%s', %s)" % (self.type, str(self._parent))

    def __str__(self):
        return self.create_label()

    def __eq__(self, other):
        return other is self

    @property
    def label(self):
        return str(self)

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

    @property
    def bounds(self):
        return None

    @property
    def points(self):
        """
        Returns the node points values

        @return: validated node point values, this is a list of lists of 3 elements.
        """
        if self._points_dirty:
            self.revalidate_points()
        self._points_dirty = False
        return self._points

    def create_label(self, text=None):
        if text is None:
            text = "{element_type}:{id}"
        return text.format_map(self.default_map())

    def default_map(self, default_map=None):
        if default_map is None:
            default_map = dict()
        default_map["id"] = str(self.id)
        default_map["element_type"] = "Node"
        default_map["node_type"] = self.type
        return default_map

    def is_movable(self):
        return True

    def drop(self, drag_node):
        return False

    def reverse(self):
        self._children.reverse()
        self.notify_reorder()

    def load(self, settings, section):
        pass

    def save(self, settings, section):
        pass

    def revalidate_points(self):
        """
        Ensure the points values for the node are valid with regard to the node's
        current state. By default, this calls bounds but valid nodes can be overloaded
        based on specific node type.

        Should be overloaded by subclasses.

        @return:
        """
        bounds = self.bounds
        if bounds is None:
            return
        if len(self._points) < 5:
            self._points.extend([None] * (5 - len(self._points)))
        self._points[0] = [bounds[0], bounds[1], "bounds top_left"]
        self._points[1] = [bounds[2], bounds[1], "bounds top_right"]
        self._points[2] = [bounds[0], bounds[3], "bounds bottom_left"]
        self._points[3] = [bounds[2], bounds[3], "bounds bottom_right"]
        cx = (bounds[0] + bounds[2]) / 2
        cy = (bounds[1] + bounds[3]) / 2
        self._points[4] = [cx, cy, "bounds center_center"]

    def update_point(self, index, point):
        """
        Attempt to update a node value, located at a specific index with the new
        point provided.

        Should be overloaded by subclasses.

        @param index: index of the updating point
        @param point: Point to be updated
        @return: Whether update was successful
        """
        return False

    def add_point(self, point, index=None):
        """
        Attempts to add a point into node.points.

        Should be overloaded by subclasses.

        @param point: point to be added
        @return: Whether append was successful
        """
        # return self._insert_point(point, index)
        return False

    def _insert_point(self, point, index=None):
        """
        Default implementation of inserting point into points.

        @param point:
        @param index:
        @return:
        """
        x = None
        y = None
        point_type = None
        try:
            x = point[0]
            y = point[1]
            point_type = point[3]
        except IndexError:
            pass
        if index is None:
            self._points.append([x, y, point_type])
        else:
            try:
                self._points.insert(index, [x, y, point_type])
            except IndexError:
                return False
        return True

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
        self._points_dirty = True
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
            self.cache.UnGetNativePath(self.cache.NativePath)
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

    def add_reference(self, node=None, pos=None, **kwargs):
        """
        Add a new node bound to the data_object of the type to the current node.
        If the data_object itself is a node already it is merely attached.

        @param node:
        @param pos:
        @return:
        """

        node_class = self._root.bootstrap["reference"]
        reference_node = node_class(node, **kwargs)
        if self._root is not None:
            self._root.notify_created(reference_node)
        reference_node.type = "reference"
        reference_node.id = node.id
        reference_node._parent = self
        reference_node._root = node._root
        if pos is None:
            self._children.append(reference_node)
        else:
            self._children.insert(pos, reference_node)
        reference_node.notify_attached(reference_node, pos=pos)
        return reference_node

    def add_node(self, node, pos=None):
        if node._parent is not None:
            raise ValueError("Cannot reparent node on add.")
        node._parent = self
        node._root = self._root
        if pos is None:
            self._children.append(node)
        else:
            self._children.insert(pos, node)
        node.notify_attached(node, pos=pos)

    def add(self, type=None, id=None, pos=None, **kwargs):
        """
        Add a new node bound to the data_object of the type to the current node.
        If the data_object itself is a node already it is merely attached.

        @param data_object:
        @param type:
        @param label: display name for this node
        @param pos:
        @return:
        """
        node_class = self._root.bootstrap.get(type, Node)
        node = node_class(**kwargs)
        if self._root is not None:
            self._root.notify_created(node)
        node.type = type
        node.id = id
        node._parent = self
        node._root = self._root
        if pos is None:
            self._children.append(node)
        else:
            self._children.insert(pos, node)
        node.notify_attached(node, pos=pos)
        return node

    def _flatten(self, node):
        """
        Yield this node and all descendants in a flat generation.

        @param node: starting node
        @return:
        """
        yield node
        for c in self._flatten_children(node):
            yield c

    def _flatten_children(self, node):
        """
        Yield all descendants in a flat generation.

        @param node: starting node
        @return:
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

        @param types: types of nodes permitted to be returned
        @param cascade: cascade all subitems if a group matches the criteria.
        @param depth: depth to search within the tree.
        @param selected: match only selected nodes
        @param emphasized: match only emphasized nodes.
        @param targeted: match only targeted nodes
        @param highlighted: match only highlighted nodes
        @return:
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

    @staticmethod
    def union_bounds(nodes):
        """
        Returns the union of the node list given.

        @return: union of all bounds within the iterable.
        """
        xmin = float("inf")
        ymin = float("inf")
        xmax = -xmin
        ymax = -ymin
        for e in nodes:
            box = e.bounds
            if box is None:
                continue
            if box[0] < xmin:
                xmin = box[0]
            if box[2] > xmax:
                xmax = box[2]
            if box[1] < ymin:
                ymin = box[1]
            if box[3] > ymax:
                ymax = box[3]
        return xmin, ymin, xmax, ymax
