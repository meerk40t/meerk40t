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

import ast
from copy import copy
from enum import IntEnum
from time import time


# LINEJOIN
# Value	arcs | bevel |miter | miter-clip | round
# Default value	miter
class Linejoin(IntEnum):
    JOIN_ARCS = 0
    JOIN_BEVEL = 1
    JOIN_MITER = 2
    JOIN_MITER_CLIP = 3
    JOIN_ROUND = 4


# LINECAP
# Value	butt | round | square
# Default value	butt
class Linecap(IntEnum):
    CAP_BUTT = 0
    CAP_ROUND = 1
    CAP_SQUARE = 2


# FILL-RULE
# Value	nonzero | evenodd
# Default value	nonzero
class Fillrule(IntEnum):
    FILLRULE_NONZERO = 0
    FILLRULE_EVENODD = 1


class Node:
    """
    Nodes are elements within the tree which stores most of the objects in Elements.

    All nodes have children, root, parent, and reference links. The children are subnodes,
    the root points to the tree root, the parent points to the immediate parent, and references
    refers to nodes that point to this node type.

    All nodes have type, id, label, and lock values.

    Type is a string value of the given node type and is used to delineate nodes.
    Label is a string value that will often describe the node.
    `Id` is a string value, during saving, we make sure this is a unique id.


    Node bounds exist, but not all nodes are have geometric bounds.
    Node paint_bounds exists, not all nodes have painted area bounds.

    Nodes can be emphasized. This is selecting the given node.
    Nodes can be highlighted.
    Nodes can be targeted.
    """

    def __init__(self, *args, **kwargs):
        self.type = None
        self.id = None
        self.label = None
        self.lock = False
        self._can_emphasize = True
        self._can_highlight = True
        self._can_target = True
        self._can_move = True
        self._can_scale = True
        self._can_rotate = True
        self._can_skew = True
        self._can_modify = True
        self._can_alter = True
        self._can_update = True
        self._can_remove = True
        self._is_visible = True
        self._expanded = False
        self._children = list()
        self._root = None
        self._parent = None
        self._references = list()
        self._formatter = "{element_type}:{id}"

        self._points = list()
        self._points_dirty = True

        self._selected = False
        self._emphasized = False
        self._emphasized_time = None
        self._highlighted = False
        self._target = False

        self._opened = False

        self._bounds = None
        self._bounds_dirty = True

        self._paint_bounds = None
        self._paint_bounds_dirty = True

        self._item = None
        self._cache = None
        self._default_map = dict()
        if "expanded" in kwargs:
            # print (f"Require expanded: {kwargs}")
            exp_value = kwargs["expanded"]
            self._expanded = exp_value
            del kwargs["expanded"]

        for k, v in kwargs.items():
            if k.startswith("_"):
                continue
            if isinstance(v, str) and k not in ("text", "id", "label"):
                try:
                    v = ast.literal_eval(v)
                except (ValueError, SyntaxError):
                    pass
            try:
                setattr(self, k, v)
            except AttributeError:
                # If this is already an attribute, just add it to the node dict.
                self.__dict__[k] = v

        super().__init__()

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self._parent)})"

    def __copy__(self):
        return self.__class__(**self.node_dict)

    def __str__(self):
        text = self._formatter
        if text is None:
            text = "{element_type}"
        default_map = self.default_map()
        try:
            return text.format_map(default_map)
        except KeyError as e:
            raise KeyError(
                f"mapping '{text}' did not contain a required key in {default_map} for {self.__class__}"
            ) from e

    def __eq__(self, other):
        return other is self

    def __hash__(self):
        return id(self)

    @property
    def node_dict(self):
        nd = dict()
        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue
            if k == "type":
                continue
            nd[k] = v
        return nd

    @property
    def children(self):
        return self._children

    @property
    def references(self):
        return self._references

    @property
    def targeted(self):
        return self._target

    @targeted.setter
    def targeted(self, value):
        self._target = value
        self.notify_targeted(self)

    @property
    def expanded(self):
        return self._expanded

    @expanded.setter
    def expanded(self, value):
        self._expanded = value
        # No use case for notify expand
        # self.notify_expand(self)

    @property
    def highlighted(self):
        return self._highlighted

    @highlighted.setter
    def highlighted(self, value):
        self._highlighted = value
        self.notify_highlighted(self)

    @property
    def is_visible(self):
        result = True
        # is it an operation?
        if hasattr(self, "output"):
            if self.output:
                return True
            else:
                return self._is_visible
        if hasattr(self, "references"):
            valid = False
            flag = False
            for n in self.references:
                if hasattr(n.parent, "output"):
                    valid = True
                    if n.parent.output is None or n.parent.output:
                        flag = True
                        break
                    if n.parent.is_visible:
                        flag = True
                        break
            # If there aren't any references then it is visible by default
            if valid:
                result = flag
        return result

    @is_visible.setter
    def is_visible(self, value):
        # is it an operation?
        if hasattr(self, "output"):
            if self.output:
                value = True
        else:
            value = True
        self._is_visible = value

    @property
    def emphasized(self):
        if self.is_visible:
            result = self._emphasized
        else:
            result = False
        return result

    @emphasized.setter
    def emphasized(self, value):
        if not self.is_visible:
            value = False
        if value != self._emphasized:
            self._emphasized = value
            if value:
                # Any value that is emphasiezd is automatically selected True
                # This is not true for the inverse case, a node can be selected
                # but not necessarily emphasized
                self._selected = True
            self._emphasized_time = time() if value else None
        self.notify_emphasized(self)

    @property
    def emphasized_time(self):
        # we intentionally reduce the resolution to 1/100 sec.
        # to allow simultaneous assignments to return the same delta
        factor = 100
        if self._emphasized_time is None:
            # Insanely high
            result = float("inf")
        else:
            result = self._emphasized_time
            result = round(result * factor) / factor
        return result

    def emphasized_since(self, reftime=None, fullres=False):
        # we intentionally reduce the resolution to 1/100 sec.
        # to allow simultaneous assignments to return the same delta
        factor = 100
        if reftime is None:
            reftime = time()
        if self._emphasized_time is None:
            delta = 0
        else:
            delta = reftime - self._emphasized_time
            if not fullres:
                delta = round(delta * factor) / factor
        return delta

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
    def can_emphasize(self):
        return self._can_emphasize

    @property
    def can_highlight(self):
        return self._can_highlight

    @property
    def can_target(self):
        return self._can_target

    def can_move(self, optional_permission=False):
        if not self._can_move:
            return False
        if optional_permission:
            return True
        return not self.lock

    @property
    def can_scale(self):
        return self._can_scale and not self.lock

    @property
    def can_rotate(self):
        return self._can_rotate and not self.lock

    @property
    def can_skew(self):
        return self._can_skew and not self.lock

    @property
    def can_modify(self):
        return self._can_modify and not self.lock

    @property
    def can_alter(self):
        return self._can_alter and not self.lock

    @property
    def can_update(self):
        return self._can_update and not self.lock

    @property
    def can_remove(self):
        return self._can_remove and not self.lock

    @property
    def bounds(self):
        if not self._bounds_dirty:
            return self._bounds

        try:
            self._bounds = self.bbox(with_stroke=False)
        except AttributeError:
            self._bounds = None

        if self._children:
            self._bounds = Node.union_bounds(self._children, bounds=self._bounds)
        self._bounds_dirty = False
        return self._bounds

    @property
    def paint_bounds(self):
        # Make sure that bounds is valid
        if not self._paint_bounds_dirty:
            return self._paint_bounds

        flag = True
        if hasattr(self, "stroke"):
            if self.stroke is None or self.stroke.argb is None:
                flag = False
        try:
            self._paint_bounds = self.bbox(with_stroke=flag)
        except AttributeError:
            self._paint_bounds = None

        if self._children:
            self._paint_bounds = Node.union_bounds(
                self._children, bounds=self._paint_bounds, attr="paint_bounds"
            )
        self._paint_bounds_dirty = False
        return self._paint_bounds

    def set_dirty_bounds(self):
        self._paint_bounds_dirty = True
        self._bounds_dirty = True
        self._points_dirty = True

    def set_dirty(self):
        self.points_dirty = True
        self.empty_cache()

    @property
    def formatter(self):
        return self._formatter

    @formatter.setter
    def formatter(self, formatter):
        self._formatter = formatter

    def display_label(self):
        x = self.label
        if x is None:
            return None
        start = 0
        default_map = self._default_map
        while True:
            i1 = x.find("{", start)
            if i1 < 0:
                break
            i2 = x.find("}", i1)
            if i2 < 0:
                break
            nd = x[i1 + 1 : i2]
            nd_val = ""
            if nd in default_map:
                n_val = default_map[nd]
                if n_val is not None:
                    nd_val = str(n_val)
            elif hasattr(self, nd):
                n_val = getattr(self, nd, "")
                if n_val is not None:
                    nd_val = str(n_val)
            x = x[:i1] + nd_val + x[i2 + 1 :]
            start = i1 + len(nd_val)
        return x

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

    def restore_tree(self, tree_data):
        # Takes a backup and reapplies it again to the tree
        # Caveat: we can't just simply take the backup and load it into the tree,
        # although it is already a perfectly independent copy.
        #           self._children.extend(tree_data)
        # If loaded directly as above then this stored state will be used
        # as the basis for further modifications consequently changing the
        # original data (as it is still the original structure) used in the undostack.
        # tree_data contains the copied branch nodes

        self._children.clear()
        links = {id(self): (self, None)}
        attrib_list = (
            "_selected",
            "_emphasized",
            "_emphasized_time",
            "_highlighted",
            "_expanded",
        )
        for c in tree_data:
            c._build_copy_nodes(links=links)
            node_copy = copy(c)
            for att in attrib_list:
                if getattr(node_copy, att) != getattr(c, att):
                    # print (f"Strange {att} not identical, fixing")
                    setattr(node_copy, att, getattr(c, att))
            node_copy._root = self._root
            links[id(c)] = (c, node_copy)

        # Rebuild structure.
        self._validate_links(links)
        branches = [links[id(c)][1] for c in tree_data]
        self._children.extend(branches)
        self._validate_tree()

    def _validate_links(self, links):
        for uid, n in links.items():
            node, node_copy = n
            if node._parent is None:
                # Root.
                continue
            # Find copy-parent of copy-node and link.
            original_parent, copied_parent = links[id(node._parent)]
            if copied_parent is None:
                # copy_parent should have been copied root, but roots don't copy
                node_copy._parent = self._root
                continue
            node_copy._parent = copied_parent
            copied_parent._children.append(node_copy)
            if node.type == "reference":
                try:
                    original_referenced, copied_referenced = links[id(node.node)]
                    node_copy.node = copied_referenced
                    copied_referenced._references.append(node_copy)
                except KeyError:
                    pass

    def _validate_tree(self):
        for c in self._children:
            assert c._parent is self
            assert c._root is self._root
            assert c in c._parent._children
            for q in c._references:
                assert q.node is c
            if c.type == "reference":
                assert c in c.node._references
            c._validate_tree()

    def _build_copy_nodes(self, links=None):
        """
        Creates a copy of each node, linked to the ID of the original node. This will create
        a map between id of original node and copy node. Without any structure. The original
        root will link to `None` since root copies are in-effective.

        @param links:
        @return:
        """
        if links is None:
            links = {id(self): (self, None)}
        attrib_list = (
            "_selected",
            "_emphasized",
            "_emphasized_time",
            "_highlighted",
            "_expanded",
            "_translated_text",
        )
        for c in self._children:
            c._build_copy_nodes(links=links)
            node_copy = copy(c)
            for att in attrib_list:
                if not hasattr(c, att):
                    continue
                if not hasattr(node_copy, att) or getattr(node_copy, att) != getattr(
                    c, att
                ):
                    # print (f"Strange {att} not identical, fixing")
                    setattr(node_copy, att, getattr(c, att))
            node_copy._root = self._root
            links[id(c)] = (c, node_copy)
        return links

    def backup_tree(self):
        """
        Creates structured copy of the branches of the tree at the current node.

        This creates copied nodes, relinks the structure and returns branches of
        the current node.
        @return:
        """
        links = self._build_copy_nodes()

        # Rebuild structure.
        self._validate_links(links)
        branches = [links[id(c)][1] for c in self._children]
        return branches

    def create_label(self, text=None):
        if text is None:
            text = "{element_type}:{id}"
        # Just for the optical impression (who understands what a "Rect: None" means),
        # let's replace some of the more obvious ones...
        mymap = self.default_map()
        for key in mymap:
            if hasattr(self, key) and mymap[key] == "None":
                if getattr(self, key) is None:
                    mymap[key] = "-"
        # slist = text.split("{")
        # for item in slist:
        #     idx = item.find("}")
        #     if idx>0:
        #         sitem = item[0:idx]
        #     else:
        #         sitem = item
        #     try:
        #         dummy = mymap[sitem]
        #     except KeyError:
        #         # Addit
        #         mymap[sitem] = "??ERR??"
        try:
            result = text.format_map(mymap)
        except ValueError:
            result = "<invalid pattern>"
        return result

    def default_map(self, default_map=None):  # , skip_label=False
        if default_map is None:
            default_map = self._default_map
        default_map["id"] = str(self.id) if self.id is not None else "-"
        lbl = self.display_label()
        default_map["label"] = lbl if lbl is not None else ""
        default_map["desc"] = (
            lbl if lbl is not None else str(self.id) if self.id is not None else "-"
        )
        default_map["element_type"] = "Node"
        default_map["node_type"] = self.type
        return default_map

    def valid_node_for_reference(self, node):
        return True

    def copy_children_as_references(self, obj):
        """
        Copy the children of the given object as direct references to those children.
        @param obj:
        @return:
        """
        for element in obj.children:
            self.add_reference(element)

    def copy_with_reified_tree(self):
        """
        Make a copy of the current node, and a copy of the sub-nodes dereferencing any reference nodes
        @return:
        """
        copy_c = copy(self)
        copy_c.copy_children_as_real(self)
        return copy_c

    def copy_children_as_real(self, copy_node):
        """
        Copy the children of copy_node to the current node, dereferencing any reference nodes.
        @param copy_node:
        @return:
        """
        for child in copy_node.children:
            child = child
            if child.type == "reference":
                child = child.node
            copy_child = copy(child)
            self.add_node(copy_child)
            copy_child.copy_children_as_real(child)

    def is_draggable(self):
        return True

    def can_drop(self, drag_node):
        return False

    def would_accept_drop(self, drag_nodes):
        # drag_nodes can be a single node or a list of nodes
        # drag_nodes can be a single node or a list of nodes
        if isinstance(drag_nodes, (list, tuple)):
            data = drag_nodes
        else:
            data = list(drag_nodes)
        return any(self.can_drop(node) for node in data)

    def drop(self, drag_node, modify=True, flag=False):
        """
        Process drag and drop node values for tree reordering.

        @param drag_node:
        @param modify:
        @return:
        """
        return False

    def reverse(self):
        self._children.reverse()
        self.notify_reorder()

    def load(self, settings, section):
        """
        Default loading will read the persistence object, such that any values found in the given section of the
        settings file. Will load parse the file to the correct type and set the attributes on this node.

        @param settings:
        @param section:
        @return:
        """
        settings.read_persistent_object(section, self)

    def save(self, settings, section):
        """
        The default node saving to a settings will write the persistence dictionary of the instance dictionary. This
        will save to that section any non `_` attributes.

        @param settings:
        @param section:
        @return:
        """
        settings.write_persistent_dict(section, self.__dict__)

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

        @param index: updating point index
        @param point: Point to be updated
        @return: Whether update was successful
        """
        return False

    def add_point(self, point, index=None):
        """
        Attempts to add a point into node.points.

        Should be overloaded by subclasses.

        @param point: point to be added
        @param index: index for point insertion
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
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_created(node=node, **kwargs)

    def notify_destroyed(self, node=None, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_destroyed(node=node, **kwargs)

    def notify_attached(self, node=None, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_attached(node=node, **kwargs)

    def notify_detached(self, node=None, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_detached(node=node, **kwargs)

    def notify_changed(self, node, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_changed(node=node, **kwargs)

    def notify_selected(self, node=None, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_selected(node=node, **kwargs)

    def notify_emphasized(self, node=None, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_emphasized(node=node, **kwargs)

    def notify_targeted(self, node=None, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_targeted(node=node, **kwargs)

    def notify_highlighted(self, node=None, **kwargs):
        if self._root is not None:
            if node is None:
                node = self
            self._root.notify_highlighted(node=node, **kwargs)

    def notify_modified(self, node=None, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_modified(node=node, **kwargs)

    def notify_translated(
        self, node=None, dx=0, dy=0, invalidate=False, interim=False, **kwargs
    ):
        if invalidate:
            self.set_dirty_bounds()
        if self._parent is not None:
            if node is None:
                node = self
            # Any change to position / size needs a recalculation of the bounds
            self._parent.notify_translated(
                node=node, dx=dx, dy=dy, invalidate=True, interim=interim, **kwargs
            )

    def notify_scaled(
        self,
        node=None,
        sx=1,
        sy=1,
        ox=0,
        oy=0,
        invalidate=False,
        interim=False,
        **kwargs,
    ):
        if invalidate:
            self.set_dirty_bounds()
        if self._parent is not None:
            if node is None:
                node = self
            # Any change to position / size needs a recalculation of the bounds
            self._parent.notify_scaled(
                node=node,
                sx=sx,
                sy=sy,
                ox=ox,
                oy=oy,
                invalidate=True,
                interim=interim,
                **kwargs,
            )

    def notify_altered(self, node=None, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_altered(node=node, **kwargs)

    def notify_expand(self, node=None, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_expand(node=node, **kwargs)

    def notify_collapse(self, node=None, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_collapse(node=node, **kwargs)

    def notify_reorder(self, node=None, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_reorder(node=node, **kwargs)

    def notify_update(self, node=None, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_update(node=node, **kwargs)

    def notify_focus(self, node=None, **kwargs):
        if self._parent is not None:
            if node is None:
                node = self
            self._parent.notify_focus(node=node, **kwargs)

    def focus(self):
        self.notify_focus(self)

    def invalidated_node(self):
        """
        Invalidation of the individual node.
        """
        self.set_dirty_bounds()
        self._bounds = None
        self._paint_bounds = None

    def invalidated(self):
        """
        Invalidation occurs when the underlying data is altered or modified. This propagates up from children to
        invalidate the entire parental line.
        """
        self.invalidated_node()
        if self._parent is not None:
            self._parent.invalidated()

    def updated(self):
        """
        The nodes display information may have changed but nothing about the matrix or the internal data is altered.
        """
        self.notify_update(self)

    def modified(self):
        """
        The matrix transformation was changed. The object is shaped
        differently but fundamentally the same structure of data.
        """
        self.invalidated()
        self.notify_modified(self)

    def translated(self, dx, dy, interim=False):
        """
        This is a special case of the modified call, we are translating
        the node without fundamentally altering its properties
        """
        if self._bounds_dirty or self._bounds is None:
            # A pity but we need proper data
            self.modified()
            return
        self._bounds = [
            self._bounds[0] + dx,
            self._bounds[1] + dy,
            self._bounds[2] + dx,
            self._bounds[3] + dy,
        ]
        if self._paint_bounds_dirty or self._paint_bounds is None:
            # Nothing we can do...
            pass
        else:
            self._paint_bounds = [
                self._paint_bounds[0] + dx,
                self._paint_bounds[1] + dy,
                self._paint_bounds[2] + dx,
                self._paint_bounds[3] + dy,
            ]
        # self.set_dirty()
        # No need to translate it as we will apply the matrix later
        # self.translate_functional_parameter(dx, dy)

        # if self._points_dirty:
        #     self.revalidate_points()
        # else:
        #     for pt in self._points:
        #         pt[0] += dx
        #         pt[1] += dy
        self.notify_translated(self, dx=dx, dy=dy, interim=interim)

    def scaled(self, sx, sy, ox, oy, interim=False):
        """
        This is a special case of the modified call, we are scaling
        the node without fundamentally altering its properties
        """

        def apply_it(box):
            x0, y0, x1, y1 = box
            if sx != 1.0:
                d1 = x0 - ox
                d2 = x1 - ox
                x0 = ox + sx * d1
                x1 = ox + sx * d2
            if sy != 1.0:
                d1 = y0 - oy
                d2 = y1 - oy
                y0 = oy + sy * d1
                y1 = oy + sy * d2
            return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

        if self._bounds_dirty or self._bounds is None:
            # A pity but we need proper data
            self.modified()
            return
        self._bounds = apply_it(self._bounds)
        # self.scale_functional_parameter(sx, sy, ox, oy)
        # This may not really correct, we need the
        # implied stroke_width to add, so the inherited
        # element classes will need to overload it
        if self._paint_bounds is not None:
            self._paint_bounds = apply_it(self._paint_bounds)
        self.set_dirty()
        self.notify_scaled(self, sx=sx, sy=sy, ox=ox, oy=oy, interim=interim)

    def empty_cache(self):
        # Remove cached artifacts
        try:
            self._cache.UnGetNativePath(self._cache.NativePath)
        except AttributeError:
            pass
        try:
            del self._cache
            del self._cache_matrix
        except AttributeError:
            pass
        self._cache = None

    def altered(self, *args, **kwargs):
        """
        The data structure was changed. Any assumptions about what this object is/was are void.
        """
        self.empty_cache()
        self.invalidated()
        self.notify_altered(self)

    def unregister_object(self):
        self.empty_cache()

    def unregister(self):
        self.unregister_object()
        try:
            self.targeted = False
            self.emphasized = False
            self.highlighted = False
        except AttributeError:
            pass

    def add_reference(self, node=None, pos=None, **kwargs):
        """
        Add a new node bound to the data_object of the type to the current node.
        If the data_object itself is a node already it is merely attached.

        @param node:
        @param pos:
        @return:
        """
        if node is None:
            return
        if not self.valid_node_for_reference(node):
            # We could raise a ValueError but that will break things...
            return
        ref = self.add(node=node, type="reference", pos=pos, **kwargs)
        node._references.append(ref)

    def add_node(self, node, pos=None):
        """
        Attach an already created node to the tree.

        Requires that this node be validated to avoid loops.

        @param node:
        @param pos:
        @return:
        """
        if node is None:
            # This should not happen and is a sign that something is amiss,
            # so we inform at least abount it
            print("Tried to add an invalid node...")
            return
        if node._parent is not None:
            raise ValueError("Cannot reparent node on add.")
        node._parent = self
        node.set_root(self._root)
        if pos is None:
            self._children.append(node)
        else:
            self._children.insert(pos, node)
        node.notify_attached(node, parent=self, pos=pos)
        return node

    def create(self, type, **kwargs):
        """
        Create node of type with attributes via node bootstrapping. Apply node defaults to values with defaults.

        @param type:
        @param kwargs:
        @return:
        """
        from .bootstrap import bootstrap, defaults

        node_class = bootstrap.get(type, None)
        if node_class is None:
            raise ValueError("Attempted to create unbootstrapped node")
        node_defaults = defaults.get(type, {})
        nd = dict(node_defaults)
        nd.update(kwargs)
        node = node_class(**nd)
        if self._root is not None:
            self._root.notify_created(node)
        return node

    def add(self, type=None, pos=None, **kwargs):
        """
        Add a new node bound to the data_object of the type to the current node.
        If the data_object itself is a node already it is merely attached.

        @param type: Node type to be bootstrapped
        @param pos: Position within current node to add this node
        @return:
        """
        node = self.create(type=type, **kwargs)
        if node is not None:
            self.add_node(node, pos=pos)
        else:
            print(f"Did not produce a valid node for type '{type}'")
        return node

    def set_root(self, root):
        """
        Set the root for this and all descendant to the provided root

        @param root:
        @return:
        """
        self._root = root
        for c in self._children:
            c.set_root(root)

    def _flatten(self, node):
        """
        Yield this node and all descendants in a flat generation.

        @param node: starting node
        @return:
        """
        yield node
        yield from self._flatten_children(node)

    def _flatten_children(self, node):
        """
        Yield all descendants in a flat generation.

        @param node: starting node
        @return:
        """
        for child in node.children:
            yield child
            yield from self._flatten_children(child)

    def flat(
        self,
        types=None,
        cascade=True,
        depth=None,
        selected=None,
        emphasized=None,
        targeted=None,
        highlighted=None,
        lock=None,
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
        @param lock: match locked nodes
        @return:
        """
        node = self
        if (
            (targeted is None or targeted == node.targeted)
            and (emphasized is None or emphasized == node.emphasized)
            and (selected is None or selected == node.selected)
            and (highlighted is None or highlighted == node.highlighted)
            and (lock is None or lock == node.lock)
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
                types, cascade, depth, selected, emphasized, targeted, highlighted, lock
            )

    def count_children(self):
        return len(self._children)

    def append_child(self, new_child):
        """
        Moves the new_child node as the last child of the current node.
        If the node exists elsewhere in the tree it will be removed from that location.

        """
        if new_child is None:
            return
        new_parent = self
        belonged_to_me = bool(new_child.parent is self)
        if new_child.parent is not None:
            source_siblings = new_child.parent.children
            if belonged_to_me and source_siblings.index(new_child) == 0:
                # The very first will be moved to the end
                belonged_to_me = False
            source_siblings.remove(new_child)  # Remove child
        destination_siblings = new_parent.children

        new_child.notify_detached(new_child)

        if belonged_to_me:
            destination_siblings.insert(0, new_child)
            new_child._parent = new_parent
            new_child.notify_attached(new_child, pos=0)
        else:
            destination_siblings.append(new_child)  # Add child.
            new_child._parent = new_parent
            new_child.notify_attached(new_child)

    def insert_sibling(self, new_sibling, below=True):
        """
        Add the new_sibling node next to the current node.
        If the node exists elsewhere in the tree it will be removed from that location.
        """
        reference_sibling = self
        source_siblings = (
            None if new_sibling.parent is None else new_sibling.parent.children
        )
        destination_siblings = reference_sibling.parent.children

        if source_siblings:
            source_siblings.remove(new_sibling)
        try:
            reference_position = destination_siblings.index(reference_sibling)
            if below:
                reference_position += 1
        except ValueError:
            # Not in list, we could have just removed it...
            reference_position = 0

        new_sibling.notify_detached(new_sibling)
        destination_siblings.insert(reference_position, new_sibling)
        new_sibling._parent = reference_sibling._parent
        new_sibling.notify_attached(new_sibling, pos=reference_position)

    def replace_node(self, keep_children=None, *args, **kwargs):
        """
        Replace this current node with a bootstrapped replacement node.
        """
        if keep_children is None:
            keep_children = False
        parent = self._parent
        index = parent._children.index(self)
        parent._children.remove(self)
        self.notify_detached(self)
        node = parent.add(*args, **kwargs, pos=index)
        self.notify_destroyed()
        for ref in list(self._references):
            ref.remove_node()
        if keep_children:
            for ref in list(self._children):
                node._children.append(ref)
                ref._parent = node
                # Don't call attach / detach, as the tree
                # doesn't know about the new node yet...
        self._item = None
        self._parent = None
        self._root = None
        self.unregister()
        return node

    def swap_node(self, node):
        """
        Swap nodes swaps the current node with the provided node in the other position in the same tree. All children
        during a swap are kept in place structurally. This permits swapping nodes between two positions that may be
        nested, without creating a loop.

        Special care is taken for both swaps being children of the same parent.

        @param node: Node already in the tree that should be swapped with the current node.
        @return:
        """
        # Remove self from tree.
        parent = self._parent
        n_parent = node._parent

        index = parent._children.index(self)
        n_index = n_parent._children.index(node)

        if index < n_index:
            # N_index is greater.
            del n_parent._children[n_index]
            del parent._children[index]

            parent._children.insert(index, node)
            n_parent._children.insert(n_index, self)
        else:
            # N_index is lesser, equal
            del parent._children[index]
            del n_parent._children[n_index]

            n_parent._children.insert(n_index, self)
            parent._children.insert(index, node)

        node._parent = parent
        self._parent = n_parent

        # Make a copy of children
        n_children = list(node._children)
        children = list(self._children)

        # Delete children.
        node._children.clear()
        self._children.clear()

        # Move children without call attach / detach.
        node._children.extend(children)
        self._children.extend(n_children)

        # Correct parent for all children.
        for n in list(n_children):
            n._parent = self
        for n in list(children):
            n._parent = node

        # self._root._validate_tree()
        self._root.notify_reorder()

    def remove_node(self, children=True, references=True, fast=False, destroy=True):
        """
        Remove the current node from the tree.

        @param children: removes all the children of this node.
        @param references: remove the references to this node.
        @param fast: Do not send notifications of the detatches and destroys
        @param destroy: Do not destroy the node.
        @return:
        """
        if children:
            self.remove_all_children(fast=fast)
        if self._parent:
            if self in self._parent._children:
                self._parent._children.remove(self)
            self._parent.set_dirty_bounds()
        if not fast:
            self.notify_detached(self)
            if destroy:
                self.notify_destroyed(self)
        if references:
            for ref in list(self._references):
                ref.remove_node(fast=fast)
        self._item = None
        self._parent = None
        self._root = None
        self.unregister()

    def remove_all_children(self, fast=False, destroy=True):
        """
        Recursively removes all children of the current node.
        """
        for child in list(self.children):
            child.remove_all_children(fast=fast, destroy=destroy)
            child.remove_node(fast=fast, destroy=destroy)

    def is_a_child_of(self, node):
        candidate = self
        while candidate is not None:
            if candidate is node:
                return True
            candidate = candidate.parent
        return False

    def has_ancestor(self, type):
        """
        Return whether this node has an ancestor node that matches the given type, or matches the major type.

        @param type:
        @return:
        """
        if self.parent is None:
            return False

        if self.parent.type == type:
            return True

        if " " not in type:
            if self.parent.type.startswith(type):
                return True

        return self.parent.has_ancestor(type=type)

    def get(self, type=None):
        """
        Recursive call for get to find first sub-nodes with the given type.
        @param type:
        @return:
        """
        if type is None or type == self.type:
            return self
        for n in self._children:
            node = n.get(type)
            if node is not None:
                return node
        return None

    def move(self, dest, pos=None):
        self._parent.remove(self)
        dest.insert_node(self, pos=pos)

    @staticmethod
    def union_bounds(
        nodes, bounds=None, attr="bounds", ignore_locked=True, ignore_hidden=False
    ):
        """
        Returns the union of the node list given, optionally unioned the given bounds value

        @return: union of all bounds within the iterable.
        """
        if bounds is None:
            xmin = float("inf")
            ymin = float("inf")
            xmax = -xmin
            ymax = -ymin
        else:
            xmin, ymin, xmax, ymax = bounds
        for e in nodes:
            if ignore_locked and e.lock:
                continue
            if ignore_hidden and getattr(e, "hidden", False):
                continue
            box = getattr(e, attr, None)
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

    @property
    def name(self):
        return self.__str__()
