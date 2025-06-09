"""
This module contains a collection of tree operations that define the right-click node menu operations.
These operations are dynamically created based on various context cues and allow for manipulation of
elements within the application.

Functions:
- plugin(kernel, lifecycle=None): Initializes the plugin and sets up the tree operations.
- init_tree(kernel): Initializes the tree operations and defines various helper functions for node manipulation.
- operation_property(node, **kwargs): Opens the property window for the selected operation node.
- edit_console_command(node, **kwargs): Opens the property window for the console command node.
- path_property(node, **kwargs): Opens the property window for the selected path element.
- group_property(node, **kwargs): Opens the property window for the selected group node.
- text_property(node, **kwargs): Opens the property window for the selected text element.
- image_property(node, **kwargs): Opens the property window for the selected image element.
- image_convert_unmodified(node, **kwargs): Replaces the node with its original image without modifications.
- image_convert_unmodified_2(node, **kwargs): Replaces the node with its modified image.
- image_convert_modifier(node, **kwargs): Unlocks modifications on the image node.
- remove_effect(node, **kwargs): Removes the effect from the selected node.
- unhatch_elements(node, **kwargs): Unhatches the selected elements.
- convert_file_to_group(node, **kwargs): Converts a file node to a normal group.
- ungroup_elements(node, **kwargs): Ungroups the selected elements.
- simplify_groups(node, **kwargs): Simplifies nested groups into a single group if applicable.
- element_visibility_toggle(node, **kwargs): Toggles the visibility of the selected elements.
- group_elements(node, **kwargs): Groups the selected elements into a new group.
- clear_all_op_entries(node, **kwargs): Clears all items from the selected operation.
- toggle_n_operations(node, **kwargs): Enables or disables the selected operations.
- toggle_op_elem_visibility(node, **kwargs): Shows or hides the contained elements of the selected operation.
- ops_enable_similar(node, **kwargs): Enables all operations of the same type as the selected operation.
- ops_disable_similar(node, **kwargs): Disables all operations of the same type as the selected operation.
- execute_job(node, **kwargs): Executes the selected operation(s).
- compile_and_simulate(node, **kwargs): Simulates the selected operation(s).
- clear_all(node, **kwargs): Clears all entries from the operations branch.
- clear_unused(node, **kwargs): Clears operations without children.
- set_speed_levels(node, speed=150, **kwargs): Sets the maximum speed for all operations.
- set_power_levels(node, power=1000, **kwargs): Sets the maximum power for all operations.
- ops_enable_all(node, **kwargs): Enables all operations in the operations branch.
- ops_disable_all(node, **kwargs): Disables all operations in the operations branch.
- remove_n_ops(node, **kwargs): Removes selected operations.
- select_similar(node, **kwargs): Selects all elements of the same type as the given node.
- remove_n_elements(node, **kwargs): Deletes the selected elements.
- make_node_reference(node, **kwargs): Converts the selected node into a reference object.
- make_polygon_regular(node, **kwargs): Converts a closed polyline into a regular polygon.
- trace_bitmap(node, **kwargs): Vectorizes the given bitmap element.
- convert_to_vectext(node, **kwargs): Converts bitmap text to vector text.
- convert_to_path(singlenode, **kwargs): Converts the selected node to a path.
- convert_to_path_effect(singlenode, **kwargs): Converts the selected effect node to a path.
- add_a_keyhole(singlenode, **kwargs): Adds a keyhole effect between selected elements.
- remove_all_keyholes(singlenode, **kwargs): Removes all associated keyholes from the selected elements.
- mirror_elem(node, **kwargs): Mirrors the selected elements horizontally.
- flip_elem(node, **kwargs): Flips the selected elements vertically.
- scale_elem_amount(node, scale, **kwargs): Scales the selected elements by a specified percentage.
- rotate_elem_amount(node, angle, **kwargs): Rotates the selected elements by a specified angle.
- reify_elem_changes(node, **kwargs): Reifies user changes made to the selected elements.
- break_subpath_elem(node, **kwargs): Breaks subpaths of the selected path element.
- remove_assignments(singlenode, **kwargs): Removes all assignments from the selected elements.
- set_assign_option_exclusive(node, **kwargs): Toggles exclusive assignment for the selected elements.
- set_assign_option_stroke(node, **kwargs): Toggles stroke inheritance for the selected elements.
- set_assign_option_fill(node, **kwargs): Toggles fill inheritance for the selected elements.
- duplicate_element_1(node, **kwargs): Duplicates the selected elements once.
- duplicate_element_n(node, copies, **kwargs): Duplicates the selected elements a specified number of times.
- make_raster_image(node, **kwargs): Creates a raster image from the assigned elements.
- add_operation_image(node, **kwargs): Appends an image operation to the operations branch.
- add_operation_raster(node, **kwargs): Appends a raster operation to the operations branch.
- add_operation_engrave(node, **kwargs): Appends an engrave operation to the operations branch.
- add_operation_cut(node, **kwargs): Appends a cut operation to the operations branch.
- add_operation_hatch(node, **kwargs): Appends a hatch operation to the operations branch.
- add_operation_dots(node, **kwargs): Appends a dots operation to the operations branch.
- add_operation_home(node, **kwargs): Appends a home operation to the operations branch.
- add_operation_origin(node, **kwargs): Appends a return to origin operation to the operations branch.
- add_operation_beep(node, **kwargs): Appends a beep operation to the operations branch.
- add_operation_interrupt(node, **kwargs): Appends an interrupt operation to the operations branch.
- add_operation_wait(node, wait_time, **kwargs): Appends a wait operation to the operations branch.
- add_operation_output(node, **kwargs): Appends an output operation to the operations branch.
- add_operation_input(node, **kwargs): Appends an input operation to the operations branch.
- add_operation_cool_on(node, **kwargs): Appends a coolant on operation to the operations branch.
- add_operation_cool_off(node, **kwargs): Appends a coolant off operation to the operations branch.
- add_operation_home_beep_interrupt(node, **kwargs): Appends home, beep, and interrupt operations to the operations branch.
- add_operation_origin_beep_interrupt(node, **kwargs): Appends origin, beep, and interrupt operations to the operations branch.
- reload_file(node, **kwargs): Reloads the specified file.
- open_file_in_explorer(node, **kwargs): Opens the containing folder of the specified file in the system's file manager.
- open_system_file(node, **kwargs): Opens the specified file in the system application associated with its type.
- load_ops(node, opname, **kwargs): Loads operations from the specified material.
- set_mat_load_option(node, **kwargs): Toggles the option to update the status bar on material load.
- get_direction_values(): Returns a list of possible burn directions.
- set_direction(node, raster_direction="", **kwargs): Sets the raster direction for the selected operations.
- set_swing(node, raster_swing="", **kwargs): Sets the swing direction for the selected operations.
"""

import math
import os.path
from copy import copy

from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.node.node import Fillrule, Node
from meerk40t.core.treeop import (
    get_tree_operation,
    tree_calc,
    tree_check,
    tree_conditional,
    tree_conditional_try,
    tree_iterate,
    tree_prompt,
    tree_radio,
    tree_separator_after,
    tree_separator_before,
    tree_submenu,
    tree_submenu_list,
    tree_values,
)
from meerk40t.core.units import UNITS_PER_INCH, Length
from meerk40t.kernel import CommandSyntaxError
from meerk40t.svgelements import Matrix, Point
from meerk40t.tools.geomstr import Geomstr

from .element_types import (
    effect_nodes,
    elem_group_nodes,
    elem_nodes,
    elem_ref_nodes,
    non_structural_nodes,
    op_burnable_nodes,
    op_image_nodes,
    op_nodes,
    op_parent_nodes,
    op_vector_nodes,
)


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_tree(kernel)


def init_tree(kernel):
    self = kernel.elements

    tree_operation = get_tree_operation(self)

    _ = kernel.translation

    # --------------------------- TREE OPERATIONS ---------------------------

    def is_regmark(node):
        return node.has_ancestor("branch reg")

    def is_hatched(node):
        e = node
        while e is not None and not e.type.startswith("branch"):
            if e.type.startswith("effect"):
                return True
            e = e.parent
        return False

    def has_changes(node):
        result = False
        try:
            if not node.matrix.is_identity():
                result = True
        except AttributeError:
            # There was an error during check for matrix.is_identity
            pass
        return result

    def is_developer_mode():
        flag = getattr(self.kernel.root, "developer_mode", False)
        return flag

    ## @tree_separator_after()
    @tree_conditional(lambda node: len(list(self.ops(selected=True))) == 1)
    @tree_operation(
        _("Operation properties"),
        node_type=op_nodes,
        help=_("Open property window for operation"),
        grouping="00PROPS",
    )
    def operation_property(node, **kwargs):
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    ## @tree_separator_after()
    @tree_operation(
        _("Edit"),
        node_type="util console",
        help=_("Modify console command"),
        grouping="00PROPS",
    )
    def edit_console_command(node, **kwargs):
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    ## @tree_separator_after()
    @tree_operation(
        _("Element properties"),
        node_type=(
            "elem ellipse",
            "elem path",
            "elem point",
            "elem polyline",
            "elem rect",
            "elem line",
        ),
        help=_("Open property window for shape"),
        grouping="00PROPS",
    )
    def path_property(node, **kwargs):
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    ## @tree_separator_after()
    @tree_operation(
        _("Group properties"),
        node_type="group",
        help=_("Open information window for group"),
        grouping="00PROPS",
    )
    def group_property(node, **kwargs):
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    ## @tree_separator_after()
    @tree_operation(
        _("Text properties"),
        node_type="elem text",
        help=_("Open property window for text"),
        grouping="00PROPS",
    )
    def text_property(node, **kwargs):
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    ## @tree_separator_after()
    @tree_operation(
        _("Image properties"),
        node_type="elem image",
        help=_("Open property window for image"),
        grouping="00PROPS",
    )
    def image_property(node, **kwargs):
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    # @tree_operation(_("Debug group"), node_type=("group", "file"), help="")
    # def debug_group(node, **kwargs):
    #     if node is None:
    #         return
    #     info = ""
    #     for idx, e in enumerate(list(node.children)):
    #         if info:
    #             info += "\n"
    #         info += f"{idx}#: {e.type}, identical to parent: {e is node}"
    #     print (info)

    """
    # Code stub will crash if used
    # ----------------------------

    @tree_conditional(lambda node: not node.lock and is_developer_mode())
    @tree_submenu(_("Passthrough"))
    @tree_operation(
        _("From Original"), node_type="elem image", help=_("Set image to passthrough mode"), grouping="70_ELEM_IMAGES"
    )
    def image_convert_unmodified(node, **kwargs):
        with self.undoscope("From Original"):
            node.replace_node(
                image=node.image,
                matrix=node.matrix,
                type="image raster",
            )

    @tree_conditional(lambda node: not node.lock and is_developer_mode())
    @tree_submenu(_("Passthrough"))
    @tree_operation(
        _("From Modified"), node_type="elem image", help=_("Set image to passthrough mode"), grouping="70_ELEM_IMAGES"
    )
    def image_convert_unmodified_2(node, **kwargs):
        with self.undoscope("From Modified"):
            node.replace_node(
                image=node.active_image,
                matrix=node.active_matrix,
                type="image raster",
            )

    @tree_conditional(lambda node: not node.lock and is_developer_mode())
    @tree_operation(
        _("Unlock modifications"),
        node_type="image raster",
        help=_("Unlock modfications for passthrough image"),
        grouping="70_ELEM_IMAGES",
    )
    def image_convert_modifier(node, **kwargs):
        # Language hint: _("Image modification")
        with self.undoscope("Unlock modifications"):
            node.replace_node(
                image=node.image,
                matrix=node.matrix,
                type="elem image",
            )
    """

    @tree_operation(
        _("Remove effect"),
        node_type=effect_nodes,
        help=_("Remove hatch/wobble"),
        grouping="10_ELEM_DELETION",
    )
    def remove_effect(node, **kwargs):
        with self.undoscope("Remove effect"):
            childs = [e for e in node._children]
            for e in childs:
                e._parent = None  # Otherwise add_node will fail below
                node.parent.add_node(e)
            node._children.clear()
            node.remove_node(fast=True)
        self.signal("rebuild_tree")

    @tree_conditional(lambda node: is_hatched(node))
    @tree_operation(
        _("Remove effect"),
        node_type=elem_nodes,
        help=_("Remove surrounding hatch/wobble"),
        grouping="10_ELEM_DELETION",
    )
    def unhatch_elements(node, **kwargs):
        # Language hint: _("Remove effect")
        data = list(self.elems(emphasized=True))
        if not data:
            return
        with self.undoscope("Remove effect"):
            for e in data:
                # eparent is the nodes immediate parent
                # nparent is the containing hatch
                eparent = e.parent
                nparent = eparent
                while True:
                    if nparent.type.startswith("effect"):
                        break
                    if nparent.parent is None:
                        nparent = None
                        break
                    if nparent.parent is self.elem_branch:
                        nparent = None
                        break
                    nparent = nparent.parent
                if nparent is None:
                    continue
                e._parent = None  # Otherwise add_node will fail below
                try:
                    idx = eparent._children.index(e)
                    if idx >= 0:
                        eparent._children.pop(idx)
                except IndexError:
                    pass
                nparent.parent.add_node(e)
                if len(nparent.children) == 0:
                    nparent.remove_node(fast=True)
                else:
                    nparent.altered()
        self.signal("rebuild_tree")

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_operation(
        _("Convert to normal group"),
        node_type="file",
        help=_("Convert filenode into a regular group"),
        grouping="40_ELEM_FILE",
    )
    def convert_file_to_group(node, **kwargs):
        with self.undoscope("Convert to normal group"):
            node_exp = node.expanded
            n = node.replace_node(
                type="group",
                keep_children=True,
                label=_("Content of {filenode}").format(filenode=node.name),
            )
            n.expanded = node_exp
        # self.signal("rebuild_tree", "elements")

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_operation(
        _("Ungroup elements"),
        node_type=("group", "file"),
        help=_("Ungroup the child elements of this node and remove the node"),
        grouping="40_ELEM_GROUPS",
    )
    def ungroup_elements(node, **kwargs):
        with self.undoscope("Ungroup elements"):
            to_treat = []
            for gnode in self.flat(
                selected=True, cascade=False, types=("group", "file")
            ):
                enode = gnode
                while True:
                    if enode.parent is None or enode.parent is self.elem_branch:
                        if enode not in to_treat:
                            to_treat.append(enode)
                        break
                    if enode.parent.selected:
                        enode = enode.parent
                    else:
                        if enode not in to_treat:
                            to_treat.append(enode)
                        break

            for gnode in to_treat:
                for n in list(gnode.children):
                    gnode.insert_sibling(n, below=False)
                gnode.remove_node()  # Removing group/file node.

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_operation(
        _("Simplify group"),
        node_type=("group", "file"),
        help=_("Unlevel groups if they just contain another group"),
        grouping="40_ELEM_GROUPS",
    )
    def simplify_groups(node, **kwargs):
        def straighten(snode):
            amount = 0
            needs_repetition = True
            while needs_repetition:
                needs_repetition = False
                cl = list(snode.children)
                if len(cl) == 0:
                    # No Children? Remove
                    amount = 1
                    snode.remove_node()
                elif len(cl) == 1:
                    gnode = cl[0]
                    if gnode is not None and gnode.type == "group":
                        for n in list(gnode.children):
                            gnode.insert_sibling(n)
                        gnode.remove_node()  # Removing group/file node.
                        needs_repetition = True
                else:
                    for n in cl:
                        if n is not None and n.type == "group":
                            fnd = straighten(n)
                            amount += fnd
            return amount

        with self.undoscope("Simplify group"):
            res = straighten(node)
        if res > 0:
            self.signal("rebuild_tree", "elements")

    # @tree_conditional(lambda node: len(list(self.elems(emphasized=True))) > 0)
    # @tree_operation(
    #     _("Elements in scene..."),
    #     node_type=elem_nodes,
    #     help="",
    #     enable=False,
    #     grouping="50_ELEM_",
    # )
    # def element_label(node, **kwargs):
    #     return

    def add_node_and_children(node):
        data = []
        data.append(node)
        for e in node.children:
            if e.type in ("file", "group"):
                data.extend(add_node_and_children(e))
            else:
                data.append(e)
        return data

    def set_vis(dataset, mode):
        updated = []
        for e in dataset:
            if not hasattr(e, "hidden"):
                continue
            if mode == 0:
                e.hidden = True
            elif mode == 1:
                e.hidden = False
            else:
                e.hidden = not e.hidden
            if e.hidden:
                e.emphasized = False
            updated.append(e)
        return updated

    @tree_submenu(_("Toggle visibility"))
    @tree_conditional(lambda node: len(list(self.elems(selected=True))) > 0)
    @tree_operation(
        _("Hide elements"),
        node_type=elem_group_nodes,
        help=_("When invisible the element will neither been displayed nor burnt"),
        grouping="30_ELEM_VISIBLE",
    )
    def element_visibility_hide(node, **kwargs):
        data = list(self.flat(selected=True))
        if not data:
            return
        with self.undoscope("Hide elements"):
            updated = set_vis(data, 0)
        self.signal("refresh_scene", "Scene")
        self.signal("element_property_reload", updated)
        self.signal("warn_state_update")

    @tree_submenu(_("Toggle visibility"))
    @tree_conditional(lambda node: len(list(self.elems(selected=True))) > 0)
    @tree_operation(
        _("Show elements"),
        node_type=elem_group_nodes,
        help=_("When invisible the element will neither been displayed nor burnt"),
        grouping="30_ELEM_VISIBLE",
    )
    def element_visibility_show(node, **kwargs):
        data = list(self.flat(selected=True))
        if not data:
            return
        with self.undoscope("Show elements"):
            updated = set_vis(data, 1)
        self.signal("refresh_scene", "Scene")
        self.signal("element_property_reload", updated)
        self.signal("warn_state_update")

    @tree_submenu(_("Toggle visibility"))
    @tree_conditional(lambda node: len(list(self.elems(selected=True))) > 0)
    @tree_operation(
        _("Toggle visibility"),
        node_type=elem_group_nodes,
        help=_("When invisible the element will neither been displayed nor burnt"),
        grouping="30_ELEM_VISIBLE",
    )
    def element_visibility_toggle(node, **kwargs):
        data = list(self.flat(selected=True))
        if not data:
            return
        with self.undoscope("Toggle visibility"):
            updated = set_vis(data, 2)
        self.signal("refresh_scene", "Scene")
        self.signal("element_property_reload", updated)
        self.signal("warn_state_update")

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_conditional(lambda node: len(list(self.elems(emphasized=True))) > 1)
    @tree_operation(
        _("Group elements"),
        node_type=elem_group_nodes,
        help=_("Group selected elements"),
        grouping="40_ELEM_GROUPS",
    )
    def group_elements(node, **kwargs):
        def minimal_parent(data):
            result = None
            root = self.elem_branch
            curr_level = None
            for node in data:
                plevel = 0
                candidate = node.parent
                while candidate is not None and candidate.parent is not root:
                    candidate = candidate.parent
                    plevel += 1
                if curr_level is None or plevel < curr_level:
                    curr_level = plevel
                    result = node.parent
                if plevel == 0:
                    # No need to continue
                    break
            if result is None:
                result = root
            return result

        raw_data = list(self.elems(emphasized=True))
        data = self.condense_elements(raw_data, expand_at_end=False)
        if not data:
            return
        with self.undoscope("Group elements"):
            parent_node = minimal_parent(data)
            group_node = parent_node.add(type="group", label="Group", expanded=True)
            for e in data:
                group_node.append_child(e)

    @tree_conditional(
        lambda cond: len(list(self.flat(selected=True, cascade=False, types=op_nodes)))
        >= 1
    )
    @tree_operation(
        _("Remove all items from operation"),
        node_type=op_parent_nodes,
        help=_("Clear all assignments from this operation"),
        grouping="10_OPS_DELETION",
    )
    def clear_all_op_entries(node, **kwargs):
        data = list()
        for item in list(self.flat(selected=True, cascade=False, types=op_nodes)):
            data.append(item)
        if not data:
            return
        # Language hint: _("Remove all items from operation")
        with self.undoscope("Remove all items from operation"):
            for item in data:
                item.remove_all_children()

    @tree_conditional(lambda node: hasattr(node, "output"))
    @tree_operation(
        _("Enable/Disable ops"),
        node_type=op_nodes,
        help=_("When disabled the operation will be ignored during a burn"),
        grouping="30_OPS_VISIBILITY",
    )
    def toggle_n_operations(node, **kwargs):
        changes = []
        with self.undoscope("Enable/Disable ops"):
            for n in self.ops(selected=True):
                if hasattr(n, "output"):
                    try:
                        n.output = not n.output
                        n.updated()
                        changes.append(n)
                    except AttributeError:
                        pass
        if len(changes) > 0:
            self.validate_selected_area()
            self.signal("element_property_update", changes)
            self.signal("refresh_scene", "Scene")
            self.signal("warn_state_update", "")

    @tree_conditional(
        lambda node: hasattr(node, "output")
        and hasattr(node, "is_visible")
        and not getattr(node, "output", True)
    )
    @tree_operation(
        _("Show/Hide contained elements"),
        node_type=op_nodes,
        help=_("Temporarily suppress all assigned elements of this operation"),
        grouping="30_OPS_VISIBILITY",
    )
    def toggle_op_elem_visibility(node, **kwargs):
        # Language hint: _("Show/Hide elements")
        with self.undoscope("Show/Hide elements"):
            changes = []
            for n in self.ops(selected=True):
                if hasattr(n, "output") and hasattr(n, "is_visible"):
                    newflag = True
                    if n.output is not None:
                        if not n.output:
                            newflag = bool(not n.is_visible)
                    n.is_visible = newflag
                    n.updated()
                    changes.append(n)
        if len(changes) > 0:
            self.validate_selected_area()
            self.signal("element_property_update", changes)
            self.signal("refresh_scene", "Scene")

    @tree_conditional(lambda node: hasattr(node, "output"))
    @tree_operation(
        _("Enable similar"),
        node_type=op_nodes,
        help=_("Enable all operations of this type"),
        grouping="30_OPS_VISIBILITY",
    )
    def ops_enable_similar(node, **kwargs):
        oplist = []
        for n in self.ops():
            if n.type == node.type:
                oplist.append(n)
        if len(oplist):
            with self.undoscope("Enable similar"):
                set_op_output(oplist, True)

    @tree_conditional(lambda node: hasattr(node, "output"))
    ## @tree_separator_after()
    @tree_operation(
        _("Disable similar"),
        node_type=op_nodes,
        help=_("Disable all operations of this type"),
        grouping="30_OPS_VISIBILITY",
    )
    def ops_disable_similar(node, **kwargs):
        oplist = []
        for n in self.ops():
            if n.type == node.type:
                oplist.append(n)
        if len(oplist):
            with self.undoscope("Disable similar"):
                set_op_output(oplist, False)

    def move_op(node, relative: str):
        try:
            idx = self.op_branch._children.index(node)
        except IndexError as e:
            # print (f"threw an error: {e}")
            return
        # Language hint _("Operation order")
        with self.undoscope("Operation order"):
            # print (f"Index was {idx}")
            if relative == "top":
                # to the top
                self.op_branch._children.pop(idx)
                self.op_branch._children.insert(0, node)
            elif relative == "up":
                # one up
                self.op_branch._children.pop(idx)
                self.op_branch._children.insert(idx - 1, node)
            elif relative == "down":
                # one down
                self.op_branch._children.pop(idx)
                self.op_branch._children.insert(idx + 1, node)
            elif relative == "bottom":
                # to the end
                self.op_branch._children.pop(idx)
                self.op_branch._children.append(node)
        # try:
        #     idx = self.op_branch._children.index(node)
        # except IndexError as e:
        #     print (f"threw an error: {e}")
        #     return
        # print (f"Index is now {idx}")
        self.signal("rebuild_tree", "operations")

    @tree_submenu(_("Burning sequence"))
    @tree_operation(
        _("Dragging works as well..."),
        node_type=op_parent_nodes,
        help="You can as well just rearrange the operations by dragging them to a new place",
        enable=False,
        grouping="OPS_40_SEQUENCE",
    )
    def burn_label(node, **kwargs):
        return

    @tree_submenu(_("Burning sequence"))
    @tree_operation(
        _("Burn first"),
        node_type=op_parent_nodes,
        help=_("Establish the sequence of operations during burntime"),
        grouping="OPS_40_SEQUENCE",
    )
    def burn_first(node, **kwargs):
        move_op(node, "top")

    @tree_submenu(_("Burning sequence"))
    @tree_operation(
        _("Burn earlier"),
        node_type=op_parent_nodes,
        help=_("Establish the sequence of operations during burntime"),
        grouping="OPS_40_SEQUENCE",
    )
    def burn_earlier(node, **kwargs):
        move_op(node, "up")

    @tree_submenu(_("Burning sequence"))
    @tree_operation(
        _("Burn later"),
        node_type=op_parent_nodes,
        help=_("Establish the sequence of operations during burntime"),
        grouping="OPS_40_SEQUENCE",
    )
    def burn_later(node, **kwargs):
        move_op(node, "down")

    @tree_submenu(_("Burning sequence"))
    @tree_operation(
        _("Burn last"),
        node_type=op_parent_nodes,
        help=_("Establish the sequence of operations during burntime"),
        grouping="OPS_40_SEQUENCE",
    )
    def burn_last(node, **kwargs):
        move_op(node, "bottom")

    @tree_submenu(_("Convert operation"))
    @tree_operation(
        _("Convert to Image"),
        node_type=op_parent_nodes,
        help=_(
            "Convert an operation to a different type maintaining properties and assigned elements"
        ),
        grouping="OPS_60_CONVERSION",
    )
    def convert_operation_image(node, **kwargs):
        data = list(self.ops(selected=True))
        if not data:
            return
        with self.undoscope("Convert to Image"):
            for n in data:
                if n.type not in op_parent_nodes:
                    continue
                new_settings = dict(n.settings)
                new_settings["type"] = "op image"
                n.replace_node(keep_children=True, **new_settings)
        self.signal("rebuild_tree", "operations")

    @tree_submenu(_("Convert operation"))
    @tree_operation(
        _("Convert to Raster"),
        node_type=op_parent_nodes,
        help=_(
            "Convert an operation to a different type maintaining properties and assigned elements"
        ),
        grouping="OPS_60_CONVERSION",
    )
    def convert_operation_raster(node, **kwargs):
        data = list(self.ops(selected=True))
        if not data:
            return
        with self.undoscope("Convert to Raster"):
            for n in data:
                if n.type not in op_parent_nodes:
                    continue
                new_settings = dict(n.settings)
                new_settings["type"] = "op raster"
                n.replace_node(keep_children=True, **new_settings)
        self.signal("rebuild_tree", "operations")

    @tree_submenu(_("Convert operation"))
    @tree_operation(
        _("Convert to Engrave"),
        node_type=op_parent_nodes,
        help=_(
            "Convert an operation to a different type maintaining properties and assigned elements"
        ),
        grouping="OPS_60_CONVERSION",
    )
    def convert_operation_engrave(node, **kwargs):
        data = list(self.ops(selected=True))
        if not data:
            return
        with self.undoscope("Convert to Engrave"):
            for n in data:
                if n.type not in op_parent_nodes:
                    continue
                new_settings = dict(n.settings)
                new_settings["type"] = "op engrave"
                n.replace_node(keep_children=True, **new_settings)
        self.signal("rebuild_tree", "operations")

    @tree_submenu(_("Convert operation"))
    @tree_operation(
        _("Convert to Cut"),
        node_type=op_parent_nodes,
        help=_(
            "Convert an operation to a different type maintaining properties and assigned elements"
        ),
        grouping="OPS_60_CONVERSION",
    )
    def convert_operation_cut(node, **kwargs):
        data = list(self.ops(selected=True))
        if not data:
            return
        with self.undoscope("Convert to Cut"):
            for n in data:
                if n.type not in op_parent_nodes:
                    continue
                new_settings = dict(n.settings)
                new_settings["type"] = "op cut"
                n.replace_node(keep_children=True, **new_settings)
        self.signal("rebuild_tree", "operations")

    @tree_submenu(_("Convert operation"))
    @tree_operation(
        _("Convert to Dots"),
        node_type=op_parent_nodes,
        help=_(
            "Convert an operation to a different type maintaining properties and assigned elements"
        ),
        grouping="OPS_60_CONVERSION",
    )
    def convert_operation_dots(node, **kwargs):
        data = list(self.ops(selected=True))
        if not data:
            return
        with self.undoscope("Convert to Dots"):
            for n in data:
                if n.type not in op_parent_nodes:
                    continue
                new_settings = dict(n.settings)
                new_settings["type"] = "op dots"
                n.replace_node(keep_children=True, **new_settings)
        self.signal("rebuild_tree", "operations")

    @tree_submenu(_("Raster-Wizard"))
    @tree_operation(
        _("Set to None"),
        node_type="elem image",
        help=_("Remove stored image operations"),
        grouping="70_ELEM_IMAGES",
    )
    def image_rasterwizard_apply_none(node, **kwargs):
        data = []
        for e in list(self.elems(emphasized=True)):
            if e.type != "elem image":
                continue
            data.append(e)
        if not data:
            return
        firstnode = data[0]
        with self.undoscope("Set to None"):
            for e in data:
                e.operations = []
                self.do_image_update(e)
        self.signal("refresh_scene", "Scene")
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None and firstnode is not None:
            activate(firstnode)
            self.signal("propupdate", firstnode)

    @tree_submenu(_("Raster-Wizard"))
    @tree_values("script", values=list(self.match("raster_script", suffix=True)))
    @tree_operation(
        _("Apply: {script}"),
        node_type="elem image",
        help=_("Apply a predefined script to an image"),
        grouping="70_ELEM_IMAGES",
    )
    def image_rasterwizard_apply(node, script=None, **kwargs):
        raster_script = self.lookup(f"raster_script/{script}")
        data = []
        for e in list(self.elems(emphasized=True)):
            if e.type != "elem image":
                continue
            data.append(e)
        if not data:
            return
        firstnode = data[0]
        with self.undoscope(script):
            for e in data:
                e.operations = raster_script
                self.do_image_update(e)
        self.signal("refresh_scene", "Scene")
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(firstnode)
            self.signal("propupdate", firstnode)

    self._image_2_path_bidirectional = True
    self._image_2_path_optimize = True

    def convert_image_to_path(node, mode):
        def feedback(msg):
            busy.change(msg=msg, keep=1)
            busy.show()

        busy = self.kernel.busyinfo
        busy.start(msg="Converting image")
        busy.show()
        with self.undoscope(f"To path: {mode}"):
            image, box = node.as_image()
            vertical = mode.lower() != "horizontal"
            bidirectional = self._image_2_path_bidirectional
            threshold = 0.5 if self._image_2_path_optimize else None  # Half a percent
            geom = Geomstr.image(
                image,
                vertical=vertical,
                bidirectional=bidirectional,
            )
            if threshold:
                geom.two_opt_distance(auto_stop_threshold=threshold, feedback=feedback)
            # self.context
            m = Matrix(node.active_matrix)
            try:
                spot_value = float(Length(getattr(self.device, "laserspot", "0.3mm")))
            except ValueError:
                spot_value = 1000

            n = node.replace_node(
                type="elem path",
                geometry=geom,
                stroke=self.default_stroke,
                stroke_width=spot_value,
                matrix=m,
            )
            if self.classify_new:
                self.classify([n])
        busy.end()

    @tree_submenu(_("Convert to Path"))
    @tree_operation(
        _("Horizontal"),
        node_type="elem image",
        help=_("Create a horizontal linepattern from the image"),
        grouping="70_ELEM_IMAGES_Y",
    )
    def image_convert_to_path_horizontal(node, **kwargs):
        # Language hint _("To path: Horizontal")
        convert_image_to_path(node, "Horizontal")

    @tree_submenu(_("Convert to Path"))
    @tree_operation(
        _("Vertical"),
        node_type="elem image",
        help=_("Create a vertical linepattern from the image"),
        grouping="70_ELEM_IMAGES_Y",
    )
    def image_convert_to_path_vertical(node, **kwargs):
        convert_image_to_path(node, "Vertical")

    def load_for_path_1(node, **kwargs):
        return self._image_2_path_bidirectional

    def load_for_path_2(node, **kwargs):
        return self._image_2_path_optimize

    @tree_submenu(_("Convert to Path"))
    @tree_separator_before()
    @tree_check(load_for_path_1)
    @tree_operation(
        _("Bidirectional"),
        node_type="elem image",
        help=_(
            "Shall the line pattern be able to travel back and forth or will it always start at the same side"
        ),
        grouping="70_ELEM_IMAGES_Y",
    )
    def set_img_2_path_option_1(node, **kwargs):
        self._image_2_path_bidirectional = not self._image_2_path_bidirectional

    @tree_submenu(_("Convert to Path"))
    @tree_check(load_for_path_2)
    @tree_operation(
        _("Optimize travel"),
        node_type="elem image",
        help=_(
            "Shall the line pattern be able to travel back and forth or will it always start at the same side"
        ),
        grouping="70_ELEM_IMAGES_Y",
    )
    def set_img_2_path_option_2(node, **kwargs):
        self._image_2_path_optimize = not self._image_2_path_optimize

    def radio_match_speed(node, speed=0, **kwargs):
        return node.speed == float(speed)

    @tree_submenu(_("Speed for Raster-operation"))
    @tree_radio(radio_match_speed)
    @tree_values("speed", (5, 10, 50, 75, 100, 150, 200, 250, 300, 350, 400, 450, 500))
    @tree_operation(
        _("{speed}mm/s"),
        node_type=op_image_nodes,
        help=_("Set speed for the operation"),
        grouping="OPS_70_MODIFY",
    )
    def set_speed_raster(node, speed=150, **kwargs):
        data = list()
        for n in list(self.ops(selected=True)):
            if n.type not in op_image_nodes:
                continue
            data.append(n)
        if not data:
            return
        with self.undoscope("Speed for Raster-operation"):
            for n in data:
                n.speed = float(speed)
        self.signal("element_property_reload", data)

    @tree_submenu(_("Speed for Vector-operation"))
    @tree_radio(radio_match_speed)
    @tree_values("speed", (2, 3, 4, 5, 6, 7, 10, 15, 20, 25, 30, 35, 40, 50))
    @tree_operation(
        _("{speed}mm/s"),
        node_type=op_vector_nodes,
        help=_("Set speed for the operation"),
        grouping="OPS_70_MODIFY",
    )
    def set_speed_vector_cut(node, speed=20, **kwargs):
        data = list()
        for n in list(self.ops(selected=True)):
            if n.type not in op_vector_nodes:
                continue
            data.append(n)
        if not data:
            return
        with self.undoscope("Speed for Vector-operation"):
            for n in data:
                n.speed = float(speed)
        self.signal("element_property_reload", data)

    def radio_match_power(node, power=0, **kwargs):
        return node.power == float(power)

    @tree_submenu(_("Power"))
    @tree_radio(radio_match_power)
    @tree_values("power", (100, 250, 300, 333, 500, 667, 750, 1000))
    @tree_calc("power_10", lambda i: round(i / 10, 1))
    @tree_operation(
        _("{power}ppi ({power_10}%)"),
        node_type=op_burnable_nodes,
        help=_("Set power for the operation"),
        grouping="OPS_70_MODIFY",
    )
    def set_power(node, power=1000, **kwargs):
        data = list()
        for n in list(self.ops(selected=True)):
            if not hasattr(n, "power"):
                continue
            data.append(n)
        if not data:
            return
        with self.undoscope("Power"):
            for n in data:
                n.power = float(power)
        self.signal("element_property_reload", data)

    def radio_match_dpi(node, dpi=100, **kwargs):
        try:
            flag = bool(round(node.dpi, 0) == round(dpi, 0))
        except ValueError:
            flag = False
        # print (f"Compare {node.dpi} to {dpi}: {flag}")
        return flag

    @tree_submenu(_("DPI"))
    @tree_radio(radio_match_dpi)
    @tree_values("dpi", (100, 200, 250, 300, 333.3, 500, 666.6, 750, 1000))
    @tree_operation(
        _("DPI {dpi}"),
        node_type="elem image",
        help=_("Change dpi values"),
        grouping="70_ELEM_IMAGES",
    )
    def set_step_n_elem(node, dpi=1, **kwargs):
        data = list()
        for n in list(self.elems(emphasized=True)):
            if n.type == "elem image":
                data.append(n)
        if not data:
            return
        with self.undoscope("Set DPI"):
            for n in data:
                n.dpi = dpi
                self.do_image_update(n)
        self.signal("refresh_scene", "Scene")
        self.signal("element_property_reload", data)

    @tree_submenu(_("DPI"))
    @tree_radio(radio_match_dpi)
    @tree_values("dpi", (100, 200, 250, 300, 333.3, 500, 666.6, 750, 1000))
    @tree_operation(
        _("DPI {dpi}"),
        node_type=(
            "op raster",
            "op image",
        ),
        help=_("Change dpi values"),
        grouping="OPS_70_MODIFY",
    )
    def set_step_n_ops(node, dpi=1, **kwargs):
        data = list()
        for n in list(self.ops(selected=True)):
            if not hasattr(n, "dpi"):
                continue
            data.append(n)
        if not data:
            return
        with self.undoscope("Set DPI"):
            for n in data:
                n.dpi = dpi
                if hasattr(n, "override_dpi"):
                    n.override_dpi = True
        self.signal("refresh_scene", "Scene")
        self.signal("element_property_reload", data)

    def radio_match_passes(node, passvalue=1, **kwargs):
        return (node.passes_custom and passvalue == node.passes) or (
            not node.passes_custom and passvalue == 1
        )

    @tree_submenu(_("Set operation passes"))
    @tree_radio(radio_match_passes)
    @tree_iterate("passvalue", 1, 10)
    @tree_operation(
        _("Passes {passvalue}"),
        node_type=op_parent_nodes,
        help=_("Define the amount of executions/passes for the operation"),
        grouping="OPS_70_MODIFY",
    )
    def set_n_passes(node, passvalue=1, **kwargs):
        data = list()
        for n in list(self.ops(selected=True)):
            if not hasattr(n, "passes"):
                continue
            data.append(n)
        if not data:
            return
        with self.undoscope("Set operation passes"):
            for n in data:
                n.passes = passvalue
                n.passes_custom = passvalue != 1
        self.signal("element_property_reload", data)

    def radio_match_loops(node, loopvalue=1, **kwargs):
        return node.loops == loopvalue

    @tree_submenu(_("Set placement loops"))
    @tree_radio(radio_match_loops)
    @tree_iterate("loopvalue", 1, 10)
    @tree_operation(
        _("Loops {loopvalue}"),
        node_type="place point",
        help=_("Set amount of passes/execution at this placement"),
        grouping="OPS_70_MODIFY",
    )
    def set_n_loops(node, loopvalue=1, **kwargs):
        data = list()
        for n in list(self.ops(selected=True)):
            if not hasattr(n, "loops"):
                continue
            data.append(n)
        if not data:
            return
        with self.undoscope("Set placement loops"):
            for n in data:
                n.loops = loopvalue
        self.signal("element_property_update", data)
        self.signal("refresh_scene", "Scene")

    @tree_operation(
        _("Remove all placements"),
        node_type=("place point", "place current"),
        help=_("Remove this and all other placements"),
        grouping="10_OPS_DELETION",
    )
    def remove_all_placements(node, **kwargs):
        data = list()
        for n in list(self.ops()):
            if n.type in ("place point", "place current"):
                data.append(n)
        if not data:
            return
        with self.undoscope("Remove placements"):
            self.remove_operations(data)
        self.signal("rebuild_tree", "operations")
        self.signal("refresh_scene", "Scene")

    @tree_operation(
        _("Move laser to placement"),
        node_type="place point",
        help=_("Move the laserhead to the jobstart position"),
        grouping="OPS_70_MODIFY",
    )
    def move_laser_to_placement(node, **kwargs):
        self(f"move_absolute {node.x}, {node.y}\n")

    # ---- Burn Direction
    def get_direction_values():
        return (
            "Top To Bottom",
            "Bottom To Top",
            "Right To Left",
            "Left To Right",
            "Crosshatch",
        )

    def radio_match_direction(node, raster_direction="", **kwargs):
        values = get_direction_values()
        for idx, key in enumerate(values):
            if key == raster_direction:
                return node.raster_direction == idx
        return False

    @tree_submenu(_("Burn direction"))
    @tree_radio(radio_match_direction)
    @tree_values("raster_direction", values=get_direction_values())
    @tree_operation(
        "{raster_direction}",
        node_type=op_image_nodes,
        help=_("Define the burn-direction for this operation"),
        grouping="OPS_70_MODIFY",
    )
    def set_direction(node, raster_direction="", **kwargs):
        values = get_direction_values()
        for idx, key in enumerate(values):
            if key == raster_direction:
                with self.undoscope("Burn direction"):
                    data = list()
                    for n in list(self.ops(selected=True)):
                        if n.type not in op_image_nodes:
                            continue
                        n.raster_direction = idx
                        data.append(n)
                self.signal("element_property_reload", data)
                break

    def get_swing_values():
        return (
            _("Unidirectional"),
            _("Bidirectional"),
        )

    def radio_match_swing(node, raster_swing="", **kwargs):
        values = get_swing_values()
        for idx, key in enumerate(values):
            if key == raster_swing:
                return node.bidirectional == idx
        return False

    @tree_submenu(_("Directional Raster"))
    @tree_radio(radio_match_swing)
    @tree_values("raster_swing", values=get_swing_values())
    @tree_operation(
        "{raster_swing}",
        node_type=op_image_nodes,
        help=_("Define the behaviour for this operation"),
        grouping="OPS_70_MODIFY",
    )
    def set_swing(node, raster_swing="", **kwargs):
        values = get_swing_values()
        for idx, key in enumerate(values):
            if key == raster_swing:
                with self.undoscope("Directional Raster"):
                    data = list()
                    for n in list(self.ops(selected=True)):
                        if n.type not in op_image_nodes:
                            continue
                        n.bidirectional = bool(idx)
                        data.append(n)
                self.signal("element_property_reload", data)
                break

    def selected_active_ops():
        result = 0
        selected = 0
        contained = 0
        for op in self.ops():
            try:
                if op.selected:
                    selected += 1
                    contained += len(op.children)
                    if op.output:
                        result += 1
            except AttributeError:
                pass
        if contained == 0:
            result = 0
        elif selected == 1:
            result = 1
        return result

    ## @tree_separator_before()
    @tree_conditional(lambda cond: selected_active_ops() > 0)
    @tree_operation(
        _("Execute operation(s)"),
        node_type=op_nodes,
        help=_("Execute Job for the selected operation(s)."),
        grouping="OPS_80_EXECUTION",
    )
    def execute_job(node, **kwargs):
        self.set_node_emphasis(node, True)
        self("plan0 clear copy-selected\n")
        self("window open ExecuteJob 0\n")

    ## @tree_separator_after()
    @tree_conditional(lambda cond: selected_active_ops() > 0)
    @tree_operation(
        _("Simulate operation(s)"),
        node_type=op_nodes,
        help=_("Run simulation for the selected operation(s)"),
        grouping="OPS_80_EXECUTION",
    )
    def compile_and_simulate(node, **kwargs):
        self.set_node_emphasis(node, True)
        self("plan0 copy-selected preprocess validate blob preopt optimize\n")
        self("window open Simulation 0 1 1\n")  # Plan Name, Auto-Clear, Optimise

    # ==========
    # General menu-entries for operation branch
    # ==========

    @tree_operation(
        _("Global operation settings"),
        node_type="branch ops",
        help=_("Define global loops and other properties"),
        grouping="00PROPS",
    )
    def op_prop(node, **kwargs):
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    @tree_operation(
        _("Clear all"),
        node_type="branch ops",
        help=_("Delete all operations"),
        grouping="10_OPS_DELETION",
    )
    def clear_all(node, **kwargs):
        if self.kernel.yesno(
            _("Do you really want to delete all entries?"), caption=_("Operations")
        ):
            with self.undoscope("Clear all"):
                self("operation* delete\n")

    @tree_operation(
        _("Clear unused"),
        node_type="branch ops",
        help=_("Clear operations without children"),
        grouping="10_OPS_DELETION",
    )
    def clear_unused(node, **kwargs):
        to_delete = []
        for op in self.ops():
            # print (f"{op.type}, refs={len(op._references)}, children={len(op._children)}")
            if len(op._children) == 0 and not op.type == "blob":
                to_delete.append(op)
        if len(to_delete) > 0:
            if self.kernel.yesno(
                _("Do you really want to delete {num} entries?").format(
                    num=len(to_delete)
                ),
                caption=_("Operations"),
            ):
                with self.undoscope("Clear unused"):
                    self.remove_operations(to_delete)

    def radio_match_speed_all(node, speed=0, **kwargs):
        maxspeed = 0
        for n in list(self.ops()):
            if not hasattr(n, "speed"):
                continue
            if n.speed is not None:
                maxspeed = max(maxspeed, n.speed)
        return bool(abs(maxspeed - float(speed)) < 0.5)

    @tree_submenu(_("Scale speed settings"))
    @tree_radio(radio_match_speed_all)
    @tree_values("speed", (5, 10, 50, 75, 100, 150, 200, 250, 300, 350, 400, 450, 500))
    @tree_operation(
        _("Max speed = {speed}mm/s"),
        node_type="branch ops",
        help=_("Scale all operation speed values relative to a new maximum"),
        grouping="OPS_70_MODIFY",
    )
    def set_speed_levels(node, speed=150, **kwargs):
        data = list()
        maxspeed = 0
        for n in list(self.ops()):
            if hasattr(node, "speed"):
                if n.speed is not None:
                    maxspeed = max(maxspeed, n.speed)
        if maxspeed == 0:
            return
        with self.undoscope("Scale speed settings"):
            for n in list(self.ops()):
                if not hasattr(node, "speed"):
                    continue
                if n.speed is not None:
                    oldspeed = float(n.speed)
                    newspeed = oldspeed / maxspeed * speed
                    n.speed = float(newspeed)
                    data.append(n)
        self.signal("element_property_reload", data)

    def radio_match_power_all(node, power=0, **kwargs):
        maxpower = 0
        for n in list(self.ops()):
            if not hasattr(n, "power"):
                continue
            if n.power is not None:
                maxpower = max(maxpower, n.power)
        return bool(abs(maxpower - float(power)) < 0.5)

    @tree_submenu(_("Scale power settings"))
    @tree_radio(radio_match_power_all)
    @tree_values("power", (100, 250, 333, 500, 667, 750, 1000))
    @tree_calc("power_10", lambda i: round(i / 10, 1))
    @tree_operation(
        _("Max power = {power}ppi ({power_10}%)"),
        node_type="branch ops",
        help=_("Scale all operation power values relative to a new maximum"),
        grouping="OPS_70_MODIFY",
    )
    def set_power_levels(node, power=1000, **kwargs):
        data = list()
        maxpower = 0
        for n in list(self.ops()):
            if not hasattr(n, "power"):
                continue
            if n.power is not None:
                maxpower = max(maxpower, n.power)
        if maxpower == 0:
            return
        with self.undoscope("Scale power settings"):
            for n in list(self.ops()):
                if not hasattr(n, "power"):
                    continue
                if n.power is not None:
                    oldpower = float(n.power)
                    newpower = oldpower / maxpower * power
                    n.power = float(newpower)
                    data.append(n)
        self.signal("element_property_reload", data)

    def set_op_output(ops, value):
        newvalue = value
        for n in ops:
            if value is None:
                newvalue = not n.output
            try:
                n.output = newvalue
                n.updated()
            except AttributeError:
                pass
        self.signal("element_property_update", ops)
        self.signal("warn_state_update", "")

    ## @tree_separator_before()
    @tree_operation(
        _("Enable all operations"),
        node_type="branch ops",
        help=_("Enable all operations"),
        grouping="30_OPS_VISIBILITY",
    )
    def ops_enable_all(node, **kwargs):
        with self.undoscope("Enable all operations"):
            set_op_output(list(self.ops()), True)

    @tree_operation(
        _("Disable all operations"),
        node_type="branch ops",
        help=_("Disable all operations"),
        grouping="30_OPS_VISIBILITY",
    )
    def ops_disable_all(node, **kwargs):
        with self.undoscope("Disable all operations"):
            set_op_output(list(self.ops()), False)

    ## @tree_separator_after()
    @tree_operation(
        _("Toggle all operations"),
        node_type="branch ops",
        help=_("Toggle enabled-status of all operations"),
        grouping="30_OPS_VISIBILITY",
    )
    def ops_toggle_all(node, **kwargs):
        with self.undoscope("Toggle all operations"):
            set_op_output(list(self.ops()), None)

    # ==========
    # General menu-entries for elem branch
    # ==========

    @tree_operation(
        _("Clear all"),
        node_type="branch elems",
        help=_("Delete all elements"),
        grouping="10_ELEM_DELETION",
    )
    def clear_all_elems(node, **kwargs):
        # self("element* delete\n")
        if self.kernel.yesno(
            _("Do you really want to delete all entries?"), caption=_("Elements")
        ):
            # Language hint _("Clear all elements")
            with self.undoscope("Clear all elements"):
                self.elem_branch.remove_all_children()

    # ==========
    # General menu-entries for regmark branch
    # ==========

    @tree_operation(
        _("Clear all"),
        node_type="branch reg",
        help=_("Delete all registration marks"),
        grouping="REG_05_DELETION",
    )
    def clear_all_regmarks(node, **kwargs):
        if self.kernel.yesno(
            _("Do you really want to delete all entries?"), caption=_("Regmarks")
        ):
            # Language hint _("Clear all regmarks")
            with self.undoscope("Clear all regmarks"):
                self.reg_branch.remove_all_children()

    # ==========
    # REMOVE MULTI (Tree Selected)
    # ==========
    # Calculate the amount of selected nodes in the tree:
    # If there are ops selected then they take precedence
    # and will only be counted

    @tree_conditional(
        lambda cond: len(
            list(self.flat(selected=True, cascade=False, types="reference"))
        )
        >= 1
    )
    @tree_calc(
        "ecount",
        lambda i: len(list(self.flat(selected=True, cascade=False, types="reference"))),
    )
    @tree_operation(
        _("Remove {ecount} selected items from operations"),
        node_type="reference",
        help=_("Delete all selected operations"),
        grouping="10_OPS_DELETION",
    )
    def remove_multi_references(node, **kwargs):
        nodes = list(self.flat(selected=True, cascade=False, types="reference"))
        if not nodes:
            return
        # Language hint _("Remove items from operations")
        with self.undoscope("Remove items from operations"):
            for node in nodes:
                if node.parent is not None:  # May have already removed.
                    node.remove_node()
        self.set_emphasis(None)
        self.signal("refresh_tree")

    @tree_conditional(
        lambda cond: len(list(self.flat(selected=True, cascade=False, types=op_nodes)))
        == 1
    )
    @tree_operation(
        _("Delete operation '{name}' fully"),
        node_type=op_nodes,
        help=_("Delete the selected operation"),
        grouping="10_OPS_DELETION",
    )
    def remove_type_op(node, **kwargs):
        self.set_emphasis(None)
        # Language hint _("Delete operation")
        with self.undoscope("Delete operation"):
            node.remove_node()
        self.signal("operation_removed")

    @tree_conditional(
        lambda cond: len(list(self.flat(selected=True, cascade=False, types="blob")))
        == 1
    )
    @tree_operation(
        _("Delete blob '{name}' fully"),
        node_type="blob",
        help=_("Delete the selected binary object"),
        grouping="10_OPS_DELETION",
    )
    def remove_type_blob(node, **kwargs):
        self.set_emphasis(None)
        # Language hint _("Delete blob")
        with self.undoscope("Delete blob"):
            node.remove_node()
        self.signal("operation_removed")

    @tree_conditional(
        lambda cond: len(list(self.flat(selected=True, cascade=False, types=op_nodes)))
        > 1
    )
    @tree_calc(
        "ecount",
        lambda i: len(list(self.flat(selected=True, cascade=False, types=op_nodes))),
    )
    @tree_operation(
        _("Delete {ecount} operations fully"),
        node_type=op_nodes,
        help=_("Delete the selected operations"),
        grouping="10_OPS_DELETION",
    )
    def remove_type_op_multiple(node, **kwargs):
        data = list(self.flat(selected=True, cascade=False, types=op_nodes))
        if not data:
            return
        # Language hint _("Delete operation")
        with self.undoscope("Delete operation"):
            for op in data:
                op.remove_node()
        self.set_emphasis(None)
        self.signal("operation_removed")

    def contains_no_unremovable_items():
        nolock = True
        for e in list(self.flat(selected=True, cascade=True)):
            if hasattr(e, "can_remove") and not e.can_remove:
                nolock = False
                break
        return nolock

    @tree_conditional(lambda cond: contains_no_unremovable_items())
    @tree_conditional(
        lambda cond: len(
            list(self.flat(selected=True, cascade=False, types=("file", "group")))
        )
        == 1
    )
    @tree_operation(
        _("Delete group '{name}' and all its child-elements fully"),
        node_type="group",
        help=_("Delete the selected group and all its content"),
        grouping="10_ELEM_DELETION",
    )
    def remove_type_grp(node, **kwargs):
        self.set_emphasis(None)
        # Language hint _("Delete group")
        with self.undoscope("Delete group"):
            node.remove_node()

    @tree_conditional(lambda cond: contains_no_unremovable_items())
    @tree_conditional(
        lambda cond: len(
            list(self.flat(selected=True, cascade=False, types=("file", "group")))
        )
        == 1
    )
    @tree_operation(
        _("Remove loaded file '{name}' and all its child-elements fully"),
        node_type="file",
        help=_("Delete the content of the loaded file"),
        grouping="10_ELEM_DELETION",
    )
    def remove_type_file(node, **kwargs):
        to_be_removed = [node]
        for e in self.elem_branch.children:
            if (
                e.type == "file"
                and e.filepath == node.filepath
                and e not in to_be_removed
            ):
                to_be_removed.append(e)
        for e in self.reg_branch.children:
            if (
                e.type == "file"
                and e.filepath == node.filepath
                and e not in to_be_removed
            ):
                to_be_removed.append(e)
        if len(to_be_removed) == 0:
            return
        # Language hint _("Remove file")
        with self.undoscope("Remove file"):
            for e in to_be_removed:
                e.remove_node()
        self.set_emphasis(None)

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_operation(
        _("Remove transparent objects"),
        node_type=("group", "file"),
        help=_("Remove all elements that neither have a border nor a fill color"),
        grouping="40_ELEM_GROUPS",
    )
    def remove_transparent(node, **kwargs):
        res = 0
        data = list()
        for enode in self.flat(
            selected=True,
            cascade=True,
            types=(
                "elem rect",
                "elem ellipse",
                "elem path",
                "elem line",
                "elem polyline",
            ),
        ):
            colored = False
            if (
                hasattr(enode, "fill")
                and enode.fill is not None
                and enode.fill.argb is not None
            ):
                colored = True
            if (
                hasattr(enode, "stroke")
                and enode.stroke is not None
                and enode.stroke.argb is not None
            ):
                colored = True
            if not colored:
                res += 1
                data.append(enode)
        if not data:
            return
        # Language hint _("Remove transparent objects")
        with self.undoscope("Remove transparent objects"):
            for enode in data:
                enode.remove_node()

        self.signal("rebuild_tree", "elements")

    # ==========
    # Remove Operations (If No Tree Selected)
    # Note: This code would rarely match anything since the tree selected will almost always be true if we have
    # match this conditional. The tree-selected delete functions are superior.
    # ==========
    @tree_conditional(
        lambda cond: len(
            list(self.flat(selected=True, cascade=False, types=non_structural_nodes))
        )
        == 0
    )
    @tree_conditional(lambda node: len(list(self.ops(selected=True))) > 1)
    @tree_calc("ecount", lambda i: len(list(self.ops(selected=True))))
    @tree_operation(
        _("Delete {ecount} operations"),
        node_type=(
            "op cut",
            "op raster",
            "op image",
            "op engrave",
            "op dots",
            "util console",
            "util wait",
            "util home",
            "util goto",
            "util output",
            "util input",
            "cutcode",
            "blob",
        ),
        help=_("Delete the selected operations"),
        grouping="10_OPS_DELETION",
    )
    def remove_n_ops(node, **kwargs):
        with self.undoscope("Delete operation"):
            self("operation delete\n")

    @tree_operation(
        _("Select all elements of same type"),
        node_type=elem_nodes,
        help=_("Select all elements in scene, that have the same type as this node"),
        grouping="05_ELEM_SELECTION",
    )
    def select_similar(node, **kwargs):
        ntype = node.type
        changes = False
        with self.static("tree_select"):
            for e in self.elems():
                if e.type == ntype and not e.emphasized and e.can_emphasize:
                    e.emphasized = True
                    e.selected = True
                    changes = True
        if changes:
            self.validate_selected_area()
            self.signal("refresh_scene", "Scene")

    # ==========
    # REMOVE ELEMENTS
    # ==========
    # More than one, special case == 1 already dealt with
    @tree_conditional(lambda node: len(list(self.elems(emphasized=True))) >= 1)
    @tree_calc("ecount", lambda i: len(list(self.elems(emphasized=True))))
    @tree_operation(
        _("Delete {ecount} elements, as selected in scene"),
        node_type=elem_group_nodes,
        help=_("Delete the selected elements"),
        grouping="10_ELEM_DELETION",
    )
    def remove_n_elements(node, **kwargs):
        with self.undoscope("Delete element"):
            self("element delete\n")

    @tree_operation(
        _("Become reference object"),
        node_type=elem_nodes,
        help=_("Make the selected object the reference object for alignment"),
        grouping="30_ELEM_VISIBLE",
    )
    def make_node_reference(node, **kwargs):
        self.signal("make_reference", node)

    @tree_conditional(
        lambda node: node.closed and len(list(node.geometry.as_points())) >= 3
    )
    @tree_operation(
        _("Make Polygon regular"),
        node_type="elem polyline",
        help=_("Change the selected polygon so that all sides have equal length"),
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def make_polygon_regular(node, **kwargs):
        def norm_angle(angle):
            while angle < 0:
                angle += math.tau
            while angle >= math.tau:
                angle -= math.tau
            return angle

        if node is None or node.type != "elem polyline":
            return
        with self.undoscope("Make Polygon regular"):
            pts = list(node.geometry.as_points())
            vertex_count = len(pts) - 1
            baseline = abs(pts[1] - pts[0])
            circumradius = baseline / (2 * math.sin(math.tau / (2 * vertex_count)))
            apothem = baseline / (2 * math.tan(math.tau / (2 * vertex_count)))
            midpoint = (pts[0] + pts[1]) / 2
            angle0 = Geomstr.angle(None, pts[0], pts[1])
            angle1 = norm_angle(angle0 + math.tau / 4)
            angle2 = norm_angle(angle0 - math.tau / 4)
            pt1 = Geomstr.polar(None, midpoint, angle1, apothem)
            pt2 = Geomstr.polar(None, midpoint, angle2, apothem)
            # The arithmetic center (ax, ay) indicates to which
            # 'side' of the baseline the polygon needs to be constructed
            arithmetic_center = sum(pts[:-1]) / vertex_count
            if Geomstr.distance(None, pt1, arithmetic_center) < Geomstr.distance(
                None, pt2, arithmetic_center
            ):
                center_point = pt1
            else:
                center_point = pt2

            start_angle = Geomstr.angle(None, center_point, pts[0])

            node.geometry = Geomstr.regular_polygon(
                vertex_count,
                center_point,
                radius=circumradius,
                radius_inner=circumradius,
                start_angle=start_angle,
            )
            node.altered()
        self.signal("refresh_scene", "Scene")

    # ==========
    # CONVERT TREE OPERATIONS
    # ==========

    @tree_conditional_try(
        lambda node: kernel.lookup(f"spoolerjob/{node.data_type}") is not None
    )
    @tree_operation(
        _("Convert to Elements"),
        node_type="blob",
        help=_("Convert attached binary object to elements"),
        grouping="85_OPS_BLOB",
    )
    def blob2path(node, **kwargs):
        cancelled = False
        from meerk40t.tools.driver_to_path import DriverToPath

        d2p = DriverToPath()
        dialog_class = kernel.lookup("dialog/options")
        if dialog_class and hasattr(d2p, "options"):
            choices = getattr(d2p, "options", None)
            if choices is not None:
                for entry in choices:
                    if "label" in entry:
                        entry["label"] = _(entry["label"])
                    if "tip" in entry:
                        entry["tip"] = _(entry["tip"])
                    if "display" in entry:
                        newdisplay = []
                        for dentry in entry["display"]:
                            newdisplay.append(_(dentry))
                        entry["display"] = newdisplay
                dialog = dialog_class(self.kernel.root, choices=choices)
                res = dialog.dialog_options(
                    title=_("Blob-Conversion"),
                    intro=_(
                        "You can influence the way MK will process the attached binary data:"
                    ),
                )
                if not res:
                    cancelled = True
        if not cancelled:
            with self.undoscope("Convert to Elements"):
                d2p.parse(node.data_type, node.data, self)
                node.remove_node()
        return True

    @tree_conditional_try(lambda node: node.data_type == "egv")
    @tree_operation(
        _("Convert to Elements"),
        node_type="blob",
        help=_("Convert attached binary object to elements"),
        grouping="85_OPS_BLOB",
    )
    def egv2path(node, **kwargs):
        from meerk40t.lihuiyu.parser import LihuiyuParser

        parser = LihuiyuParser()
        parser.fix_speeds = True
        parser.parse(node.data, self)
        node.remove_node()
        self.signal("refresh_scene", "Scene")

    @tree_conditional_try(
        lambda node: kernel.lookup(f"spoolerjob/{node.data_type}") is not None
    )
    @tree_operation(
        _("Execute Blob"),
        node_type="blob",
        help=_("Run the given blob on the current device"),
        grouping="85_OPS_BLOB",
    )
    def blob_execute(node, **kwargs):
        spooler_job = self.lookup(f"spoolerjob/{node.data_type}")
        matrix = self.device.view.matrix
        job_object = spooler_job(self.device.driver, matrix)
        job_object.write_blob(node.data)
        self.device.spooler.send(job_object)

    @tree_conditional_try(lambda node: hasattr(node, "as_cutobjects"))
    @tree_operation(
        _("Convert to Cutcode"),
        node_type="blob",
        help=_("Recreate cutcode from the binary object"),
        grouping="85_OPS_BLOB",
    )
    def blob2cut(node, **kwargs):
        node.replace_node(node.as_cutobjects(), type="cutcode")

    @tree_operation(
        _("Convert to Path"),
        node_type="cutcode",
        help=_("Recreate a path element from the selected cutcode"),
        grouping="85_OPS_BLOB",
    )
    def cutcode2pathcut(node, **kwargs):
        cutcode = node.cutcode
        if cutcode is None:
            return
        elements = list(cutcode.as_elements())
        n = None
        with self.undoscope("Convert to Path"):
            for element in elements:
                n = self.elem_branch.add(type="elem path", path=element)
            node.remove_node()
        if n is not None:
            n.focus()

    @tree_submenu(_("Clone reference"))
    @tree_operation(
        _("Make 1 copy"),
        node_type=("reference",),
        help=_("Add an additional reference of the master element"),
        grouping="20_OPS_DUPLICATION",
    )
    def clone_single_element_op(node, **kwargs):
        clone_element_op(node, copies=1, **kwargs)

    @tree_submenu(_("Clone reference"))
    @tree_iterate("copies", 2, 10)
    @tree_operation(
        _("Make {copies} copies"),
        node_type=("reference",),
        help=_("Add more references of the master element"),
        grouping="20_OPS_DUPLICATION",
    )
    def clone_element_op(node, copies=1, **kwargs):
        nodes = list(self.flat(selected=True, cascade=False, types="reference"))
        if not nodes:
            return
        with self.undoscope("Clone reference"):
            for snode in nodes:
                index = snode.parent.children.index(snode)
                for i in range(copies):
                    snode.parent.add_reference(snode.node, pos=index)
                snode.modified()

    @tree_conditional(lambda node: node.count_children() > 1)
    @tree_operation(
        _("Reverse subitems order"),
        node_type=(
            "op cut",
            "op raster",
            "op image",
            "op engrave",
            "op dots",
            "group",
            "branch elems",
            "file",
            "branch ops",
        ),
        help=_("Reverse the items within this subitem"),
        grouping="ZZZZ_tree",
    )
    def reverse_layer_order(node, **kwargs):
        node.reverse()
        self.signal("refresh_tree", list(self.flat(types="reference")))

    @tree_submenu(_("Classification"))
    @tree_operation(
        _("Generate operations if needed"),
        node_type=("branch ops", "branch elems"),
        help=_("Will create mising operations if required"),
        enable=False,
        grouping="40_ELEM_CLASSIFY",
    )
    def do_classification_comment_1(node, **kwargs):
        return

    @tree_submenu(_("Classification"))
    @tree_operation(
        _("Refresh classification for all"),
        node_type=("branch ops", "branch elems"),
        help=_("Reclassify elements and create operations if necessary"),
        grouping="40_ELEM_CLASSIFY",
    )
    def refresh_classification_for_all_std(node, **kwargs):
        previous = self.classify_autogenerate
        self.classify_autogenerate = True
        # Language hint _("Refresh classification")
        with self.undoscope("Refresh classification"):
            self.remove_elements_from_operations(list(self.elems()))
            self.classify(list(self.elems()))
        self.classify_autogenerate = previous
        self.signal("refresh_tree", list(self.flat(types="reference")))

    @tree_conditional(lambda node: self.have_unassigned_elements())
    @tree_submenu(_("Classification"))
    @tree_operation(
        _("Classification for unassigned"),
        node_type=("branch ops", "branch elems"),
        help=_("Classify unassigned elements and create operations if necessary"),
        grouping="40_ELEM_CLASSIFY",
    )
    def do_classification_for_unassigned_std(node, **kwargs):
        previous = self.classify_autogenerate
        self.classify_autogenerate = True
        target_list = list(self.unassigned_elements())
        if not target_list:
            return
        # Language hint _("Classification")
        with self.undoscope("Classification"):
            self.classify(target_list)
        self.classify_autogenerate = previous
        self.signal("refresh_tree", list(self.flat(types="reference")))

    @tree_submenu(_("Classification"))
    @tree_separator_before()
    @tree_operation(
        _("Use only existing operations"),
        node_type=("branch ops", "branch elems"),
        help=_("Stick with existing operations only"),
        enable=False,
        grouping="40_ELEM_CLASSIFY",
    )
    def do_classification_comment_2(node, **kwargs):
        return

    @tree_submenu(_("Classification"))
    @tree_operation(
        _("Refresh classification for all"),
        node_type=("branch ops", "branch elems"),
        help=_("Reclassify all elements and use only existing operations"),
        grouping="40_ELEM_CLASSIFY",
    )
    def refresh_classification_for_all_existing_only(node, **kwargs):
        previous = self.classify_autogenerate
        self.classify_autogenerate = False
        # Language hint _("Refresh classification")
        with self.undoscope("Refresh classification"):
            self.remove_elements_from_operations(list(self.elems()))
            self.classify(list(self.elems()))
        self.classify_autogenerate = previous
        self.signal("refresh_tree", list(self.flat(types="reference")))

    @tree_submenu(_("Classification"))
    @tree_conditional(lambda node: self.have_unassigned_elements())
    @tree_operation(
        _("Classification for unassigned"),
        node_type=("branch ops", "branch elems"),
        help=_("Classify unassigned elements and use only existing operations"),
        grouping="40_ELEM_CLASSIFY",
    )
    def do_classification_for_unassigned_existing_only(node, **kwargs):
        previous = self.classify_autogenerate
        self.classify_autogenerate = False
        target_list = list(self.unassigned_elements())
        if not target_list:
            return
        # Language hint _("Classification")
        with self.undoscope("Classification"):
            self.classify(target_list)
        self.classify_autogenerate = previous
        self.signal("refresh_tree", list(self.flat(types="reference")))

    @tree_submenu(_("Classification"))
    @tree_separator_before()
    @tree_operation(
        _("Clear all assignments"),
        node_type=("branch ops", "branch elems"),
        help=_("Remove all assignments of elements to operations"),
        grouping="40_ELEM_CLASSIFY",
    )
    def do_classification_clear(node, **kwargs):
        # Language hint _("Clear classification")
        with self.undoscope("Clear classification"):
            self.remove_elements_from_operations(list(self.elems()))
        self.signal("refresh_tree")

    @tree_conditional(lambda cond: self.have_unassigned_elements())
    @tree_operation(
        _("Select unassigned elements"),
        node_type=("branch ops", "branch elems"),
        help=_("Select all elements that won't be burned"),
        grouping="40_ELEM_CLASSIFY",
    )
    def select_unassigned(node, **kwargs):
        changes = False
        for node in self.elems():
            emphasis = bool(len(node.references) == 0)
            if node.emphasized != emphasis and node.can_emphasize:
                changes = True
                node.emphasized = emphasis
        if changes:
            self.validate_selected_area()
            self.signal("refresh_scene", "Scene")

    ## @tree_separator_before()
    @tree_operation(
        _("Material Manager"),
        node_type="branch ops",
        help=_("Open the Material Manager"),
        grouping="OPS_60_MATMAN",
    )
    def load_matman(node, **kwargs):
        self("window open MatManager\n")

    def material_name(material):
        if material == "previous":
            return _("<Previous set>")
        oplist, opinfo = self.load_persistent_op_list(material)
        mat_name = opinfo.get("material", "")
        mat_title = opinfo.get("title", "")
        # material_thickness = opinfo.get("thickness", "")
        if mat_title == "":
            if mat_name:
                mat_title = mat_name
            else:
                if material == "_default":
                    mat_title = "Generic Defaults"
                elif material.startswith("_default_"):
                    mat_title = f"Default for {material[9:]}"
                else:
                    mat_title = material.replace("_", " ")
        name = ""
        # if material_name:
        #     name += f"[{material_name}] "
        name += mat_title
        # if material_thickness:
        #     name += f" {material_thickness}"
        return name

    def material_menus():
        was_previous = False
        entries = list()
        self.op_data.read_configuration()
        for material in self.op_data.section_set():
            if material == "previous":
                was_previous = True
                continue
            opinfo = self.load_persistent_op_info(material)
            material_name = opinfo.get("material", "")
            material_title = opinfo.get("title", "")
            material_thickness = opinfo.get("thickness", "")
            if material_title == "":
                if material_name:
                    material_title = material_name
                else:
                    if material == "_default":
                        material_title = "Generic Defaults"
                    elif material.startswith("_default_"):
                        material_title = f"Default for {material[9:]}"
                    else:
                        material_title = material.replace("_", " ")
            submenu = _("Materials")
            if material_name:
                submenu += f"{'|' if submenu else ''}{material_name}"
            if material_thickness:
                submenu += f"{'|' if submenu else ''}{material_thickness}"
            entries.append((material_name, material_thickness, material_title, submenu))
        # Let's sort them
        entries.sort(
            key=lambda e: (
                e[0],
                e[1],
                e[2],
            )
        )
        submenus = [e[3] for e in entries]
        if was_previous:
            submenus.insert(0, _("Materials"))
        return submenus

    def material_ids():
        was_previous = False
        entries = list()
        for material in self.op_data.section_set():
            if material == "previous":
                was_previous = True
                continue
            opinfo = self.load_persistent_op_info(material)
            material_name = opinfo.get("material", "")
            material_title = opinfo.get("title", "")
            material_thickness = opinfo.get("thickness", "")
            if material_title == "":
                if material_name:
                    material_title = material_name
                else:
                    if material == "_default":
                        material_title = "Generic Defaults"
                    elif material.startswith("_default_"):
                        material_title = f"Default for {material[9:]}"
                    else:
                        material_title = material.replace("_", " ")
            entries.append(
                (material_name, material_thickness, material_title, material)
            )
        # Let's sort them
        entries.sort(
            key=lambda e: (
                e[0],
                e[1],
                e[2],
            )
        )
        res = [e[3] for e in entries]
        if was_previous:
            res.insert(0, "previous")
        return res

    ## @tree_separator_after()
    @tree_submenu(_("Load"))
    @tree_values("opname", values=material_ids)
    @tree_submenu_list(material_menus)
    @tree_calc("material", lambda opname: material_name(opname))
    @tree_operation(
        "{material}",
        node_type="branch ops",
        help=_("Populate the operation template list at the bottom"),
        grouping="OPS_60_MATMAN",
    )
    def load_ops(node, opname, **kwargs):
        self(f"material load {opname}\n")
        if self.update_statusbar_on_material_load:
            op_list, op_info = self.load_persistent_op_list(opname)
            if len(op_list) == 0:
                return
            self.default_operations = list(op_list)
            self.signal("default_operations")

    def load_for_statusbar(node, **kwargs):
        return self.update_statusbar_on_material_load

    ## @tree_separator_before()
    @tree_submenu(_("Materials"))
    @tree_check(load_for_statusbar)
    @tree_operation(
        _("Update Statusbar on load"),
        node_type="branch ops",
        help=_("Loading an entry will update the statusbar icons, too, if checked"),
        grouping="OPS_60_MATMAN",
    )
    def set_mat_load_option(node, **kwargs):
        self.update_statusbar_on_material_load = (
            not self.update_statusbar_on_material_load
        )

    @tree_submenu(_("Add effect"))
    @tree_operation(
        _("Add hatch effect"),
        node_type=("op cut", "op engrave"),
        help=_("Add an hatch effect to the operation"),
        grouping="OPS_40_ADDITION",
    )
    def add_hatch_to_op(node, pos=None, **kwargs):
        with self.undoscope("Add hatch"):
            old_children = list(node.children)
            effect = node.add("effect hatch")
            effect.stroke = node.color
            for e in old_children:
                if e is effect:
                    continue
                if e.type in elem_ref_nodes:
                    effect.append_child(e)
        self.signal("element_property_update", [effect])
        self.signal("updateop_tree")

    @tree_submenu(_("Add effect"))
    @tree_operation(
        _("Add wobble effect"),
        node_type=("op cut", "op engrave"),
        help=_("Add a wobble effect to the operation"),
        grouping="OPS_40_ADDITION",
    )
    def add_wobble_to_op(node, pos=None, **kwargs):
        with self.undoscope("Add wobble"):
            old_children = list(node.children)
            effect = node.add("effect wobble")
            effect.stroke = node.color
            for e in old_children:
                if e is effect:
                    continue
                if e.type in elem_ref_nodes:
                    effect.append_child(e)
        self.signal("element_property_update", [effect])
        self.signal("updateop_tree")

    ## @tree_separator_before()
    @tree_submenu(_("Append operation"))
    @tree_operation(
        _("Append Image"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_image(node, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add("op image", pos=pos)
        self.signal("updateop_tree")

    @tree_submenu(_("Append operation"))
    @tree_operation(
        _("Append Raster"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_raster(node, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add("op raster", pos=pos)
        self.signal("updateop_tree")

    @tree_submenu(_("Append operation"))
    @tree_operation(
        _("Append Engrave"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_engrave(node, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add("op engrave", pos=pos)
        self.signal("updateop_tree")

    @tree_submenu(_("Append operation"))
    @tree_operation(
        _("Append Cut"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_cut(node, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add("op cut", pos=pos)
        self.signal("updateop_tree")

    @tree_submenu(_("Append operation"))
    @tree_operation(
        _("Append new Hatch"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_hatch(node, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            b = self.op_branch.add("op engrave", pos=pos)
            b.add("effect hatch")
        self.signal("updateop_tree")

    @tree_submenu(_("Append operation"))
    @tree_operation(
        _("Append Dots"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_dots(node, pos=None, **kwargs):
        self.op_branch.add("op dots", pos=pos)
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(
        _("Append Home"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_home(node, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add(type="util home", pos=pos)
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(
        _("Append Return to Origin"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_goto(node, pos=None, **kwargs):
        self.op_branch.add(type="util goto", pos=pos, x=0, y=0)
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_prompt("y", _("Y-Coordinate of Goto?"))
    @tree_prompt("x", _("X-Coordinate of Goto?"))
    @tree_operation(
        _("Append Goto Location"),
        node_type="branch ops",
        help=_("Send laser to specific location."),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_goto_location(node, y, x, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add(
                type="util goto",
                pos=pos,
                x=x,
                y=y,
            )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(
        _("Append Beep"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_beep(node, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add(
                type="util console",
                pos=pos,
                command="beep",
            )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(
        _("Append Interrupt"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_interrupt(node, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add(
                type="util console",
                pos=pos,
                command='interrupt "Spooling was interrupted"',
            )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_prompt("wait_time", _("Wait for how long (in seconds)?"), data_type=float)
    @tree_operation(
        _("Append Wait"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_wait(node, wait_time, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add(
                type="util wait",
                pos=pos,
                wait=wait_time,
            )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(
        _("Append Output"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_output(node, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add(
                type="util output",
                pos=pos,
                output_mask=0,
                output_value=0,
                output_message=None,
            )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(
        _("Append Input"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_input(node, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add(
                type="util input",
                pos=pos,
                input_mask=0,
                input_value=0,
                input_message=None,
            )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(
        _("Append Coolant On"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_cool_on(node, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add(
                type="util console",
                pos=pos,
                command="coolant_on",
            )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(
        _("Append Coolant Off"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_cool_off(node, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add(
                type="util console",
                pos=pos,
                command="coolant_off",
            )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(
        _("Append Home/Beep/Interrupt"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_home_beep_interrupt(node, **kwargs):
        append_operation_home(node, **kwargs)
        append_operation_beep(node, **kwargs)
        append_operation_interrupt(node, **kwargs)
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(
        _("Append Origin/Beep/Interrupt"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_origin_beep_interrupt(node, **kwargs):
        # Language hint _("Append operation")
        append_operation_goto(node, **kwargs)
        append_operation_beep(node, **kwargs)
        append_operation_interrupt(node, **kwargs)
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(
        _("Append Shutdown"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_shutdown(node, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add(
                type="util console",
                pos=pos,
                command="quit",
            )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_prompt("opname", _("Console command to append to operations?"))
    @tree_operation(
        _("Append Console"),
        node_type="branch ops",
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def append_operation_custom(node, opname, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add(
                type="util console",
                pos=pos,
                command=opname,
            )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_prompt("y", _("Y-Coordinate for placement to append?"))
    @tree_prompt("x", _("X-Coordinate for placement to append?"))
    @tree_operation(
        _("Append absolute placement"),
        node_type="branch ops",
        help=_("Start job at specicic location"),
        grouping="OPS_40_ADDITION",
    )
    def append_absolute_placement(node, y, x, pos=None, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add(
                type="place point",
                pos=pos,
                x=x,
                y=y,
                rotation=0,
                corner=0,
            )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(
        _("Append relative placement"),
        node_type="branch ops",
        help=_("Start job at current laserposition"),
        grouping="OPS_40_ADDITION",
    )
    def append_relative_placement(node, **kwargs):
        with self.undoscope("Append operation"):
            self.op_branch.add(
                type="place current",
            )
        self.signal("updateop_tree")

    @tree_operation(
        _("Remove all assignments from operations"),
        node_type="branch elems",
        help=_("Any existing assignment of elements to operations will be removed"),
        grouping="40_ELEM_CLASSIFY",
    )
    def remove_all_assignments(node, **kwargs):
        # Language hint _("Clear classification")
        with self.undoscope("Clear classification"):
            for node in self.elems():
                for ref in list(node.references):
                    ref.remove_node()
        self.signal("refresh_tree")

    hatchable_elems = (
        "elem path",
        "elem rect",
        "elem circle",
        "elem ellipse",
        "elem polyline",
    )

    wobbleable_elems = (
        "elem path",
        "elem rect",
        "elem circle",
        "elem ellipse",
        "elem polyline",
        "elem line",
    )

    def hatch_me(node, hatch_type, hatch_distance, hatch_angle, pos):
        # Language hint _("Apply hatch")
        with self.undoscope("Apply hatch"):
            group_node = node.parent.add(
                type="effect hatch",
                hatch_type=hatch_type,
                hatch_distance=hatch_distance,
                hatch_angle=hatch_angle,
                pos=pos,
            )
            for e in list(self.elems(emphasized=True)):
                group_node.append_child(e)
            if self.classify_new:
                self.classify([group_node])

        self.signal("updateelem_tree")

    @tree_submenu(_("Apply special effect"))
    @tree_operation(
        _("Append Line-fill 0.1mm"),
        node_type=hatchable_elems,
        help=_("Apply hatch"),
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def append_element_effect_eulerian(node, pos=None, **kwargs):
        hatch_me(
            node,
            hatch_type="scanline",
            hatch_distance="0.1mm",
            hatch_angle="0deg",
            pos=pos,
        )

    @tree_submenu(_("Apply special effect"))
    @tree_operation(
        _("Append diagonal Line-fill 0.1mm"),
        node_type=hatchable_elems,
        help=_("Apply hatch"),
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def append_element_effect_eulerian_45(node, pos=None, **kwargs):
        hatch_me(
            node,
            hatch_type="scanline",  # scanline / eulerian
            hatch_distance="0.1mm",
            hatch_angle="45deg",
            pos=pos,
        )

    @tree_submenu(_("Apply special effect"))
    @tree_operation(
        _("Append Line-Fill 1mm"),
        node_type=hatchable_elems,
        help=_("Apply hatch"),
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def append_element_effect_line(node, pos=None, **kwargs):
        hatch_me(
            node,
            hatch_type="scanline",
            hatch_distance="1mm",
            hatch_angle="0deg",
            pos=pos,
        )

    @tree_submenu(_("Apply special effect"))
    @tree_operation(
        _("Append diagonal Line-Fill 1mm"),
        node_type=hatchable_elems,
        help=_("Apply hatch"),
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def append_element_effect_line_45(node, pos=None, **kwargs):
        hatch_me(
            node,
            hatch_type="scanline",
            hatch_distance="1mm",
            hatch_angle="45deg",
            pos=pos,
        )

    def wobble_me(node, wobble_type, wobble_radius, wobble_interval, pos):
        # Language hint _("Apply wobble")
        with self.undoscope("Apply wobble"):
            group_node = node.parent.add(
                type="effect wobble",
                wobble_type=wobble_type,
                wobble_radius=wobble_radius,
                wobble_interval=wobble_interval,
                pos=pos,
            )
            for e in list(self.elems(emphasized=True)):
                group_node.append_child(e)
            if self.classify_new:
                self.classify([group_node])

        self.signal("updateelem_tree")

    @tree_submenu(_("Apply special effect"))
    @tree_operation(
        _("Append wobble {type} {radius} @{interval}").format(
            type=_("Circle"), radius="0.5mm", interval="0.05mm"
        ),
        node_type=wobbleable_elems,
        help=_("Apply a wobble (contour follower)"),
        grouping="50_ELEM_MODIFY_ZMISC_WOBBLE",
    )
    def append_element_effect_wobble_c05(node, pos=None, **kwargs):
        wobble_me(
            node=node,
            wobble_type="circle",
            wobble_radius="0.5mm",
            wobble_interval="0.05mm",
            pos=pos,
        )

    @tree_submenu(_("Apply special effect"))
    @tree_operation(
        _("Append wobble {type} {radius} @{interval}").format(
            type=_("Circle"), radius="1mm", interval="0.1mm"
        ),
        node_type=wobbleable_elems,
        help=_("Apply a wobble (contour follower)"),
        grouping="50_ELEM_MODIFY_ZMISC_WOBBLE",
    )
    def append_element_effect_wobble_c1(node, pos=None, **kwargs):
        wobble_me(
            node=node,
            wobble_type="circle",
            wobble_radius="1mm",
            wobble_interval="0.1mm",
            pos=pos,
        )

    @tree_submenu(_("Apply special effect"))
    @tree_operation(
        _("Append wobble {type} {radius} @{interval}").format(
            type=_("Circle"), radius="3mm", interval="0.1mm"
        ),
        node_type=wobbleable_elems,
        help=_("Apply a wobble (contour follower)"),
        grouping="50_ELEM_MODIFY_ZMISC_WOBBLE",
    )
    def append_element_effect_wobble_c3(node, pos=None, **kwargs):
        wobble_me(
            node=node,
            wobble_type="circle_right",
            wobble_radius="3mm",
            wobble_interval="0.1mm",
            pos=pos,
        )

    @tree_submenu(_("Apply special effect"))
    @tree_operation(
        _("Append wobble {type} {radius} @{interval}").format(
            type=_("Meander"), radius="1mm", interval="1.25mm"
        ),
        node_type=wobbleable_elems,
        help=_("Apply a wobble (contour follower)"),
        grouping="50_ELEM_MODIFY_ZMISC_WOBBLE",
    )
    def append_element_effect_wobble_m1(node, pos=None, **kwargs):
        wobble_me(
            node=node,
            wobble_type="meander_1",
            wobble_radius="1mm",
            wobble_interval="1.25mm",
            pos=pos,
        )

    @tree_submenu(_("Apply special effect"))
    @tree_operation(
        _("Append Warp").format(),
        node_type=hatchable_elems,
        help=_("Apply a warp effect"),
        grouping="51_ELEM_MODIFY_ZMISC_WARP",
    )
    def append_element_effect_warp(node, pos=None, **kwargs):
        # Language hint _("Apply warp")
        with self.undoscope("Apply warp"):
            group_node = node.parent.add(
                type="effect warp",
                pos=pos,
            )
            for e in list(self.elems(emphasized=True)):
                group_node.append_child(e)
            if self.classify_new:
                self.classify([group_node])

        self.signal("updateelem_tree")

    @tree_operation(
        _("Duplicate operation(s)"),
        node_type=op_nodes,
        help=_("duplicate operation nodes"),
        grouping="20_OPS_DUPLICATION",
    )
    def duplicate_operation(node, **kwargs):
        data = self.ops(selected=True)
        if not data:
            return
        operations = self._tree.get(type="branch ops").children
        with self.undoscope("Duplicate operation(s)"):
            for op in data:
                try:
                    pos = operations.index(op) + 1
                except ValueError:
                    pos = None
                copy_op = copy(op)
                self.add_op(copy_op, pos=pos)
                for child in op.children:
                    try:
                        copy_op.add_reference(child.node)
                    except AttributeError:
                        pass

    @tree_conditional(lambda node: node.count_children() > 1)
    @tree_submenu(_("Duplicate element(s)"))
    @tree_operation(
        _("Duplicate elements 1 time"),
        node_type=op_burnable_nodes,
        help=_("Create one copy of the selected elements"),
        grouping="20_ELEM_DUPLICATION",
    )
    def dup_1_copy(node, **kwargs):
        dup_n_copies(node, copies=1, **kwargs)

    @tree_conditional(lambda node: node.count_children() > 1)
    @tree_submenu(_("Duplicate element(s)"))
    @tree_iterate("copies", 2, 10)
    @tree_operation(
        _("Duplicate elements {copies} times"),
        node_type=op_burnable_nodes,
        help=_("Create multiple copies of the selected elements"),
        grouping="20_ELEM_DUPLICATION",
    )
    def dup_n_copies(node, copies=1, **kwargs):
        # Code in series.
        # add_nodes = list(node.children)
        # add_nodes *= copies
        # for n in add_nodes:
        #     node.add_reference(n.node)

        # Code in parallel.
        add_nodes = list(node.children)
        if not add_nodes:
            return
        with self.undoscope("Duplicate element(s)"):
            for i in range(len(add_nodes) - 1, -1, -1):
                n = add_nodes[i]
                for k in range(copies):
                    node.add_reference(n.node, pos=i)

        self.signal("refresh_tree")

    def create_image_from_operation(node):
        data = list(node.flat(types=elem_ref_nodes))
        if not data:
            return None, None
        try:
            bounds = Node.union_bounds(data, attr="paint_bounds", ignore_hidden=True)
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
        except TypeError:
            raise CommandSyntaxError
        make_raster = self.lookup("render-op/make_raster")
        if not make_raster:
            raise ValueError("No renderer is registered to perform render.")

        dots_per_units = node.dpi / UNITS_PER_INCH
        new_width = width * dots_per_units
        new_height = height * dots_per_units
        try:
            image = make_raster(
                data,
                bounds=bounds,
                width=new_width,
                height=new_height,
            )
        except Exception:
            return None, None
        matrix = Matrix.scale(width / new_width, height / new_height)
        matrix.post_translate(bounds[0], bounds[1])
        return image, matrix

    @tree_submenu(_("Create image/path"))
    @tree_operation(
        _("Make raster image"),
        node_type=op_burnable_nodes,
        help=_("Create an image from the assigned elements."),
        grouping="OPS_75_CONVERTIMAGE",
    )
    def make_raster_image(node, **kwargs):
        image, matrix = create_image_from_operation(node)
        if image is None:
            return
        with self.undoscope("Make raster image"):
            image_node = ImageNode(image=image, matrix=matrix, dpi=node.dpi)
            self.elem_branch.add_node(image_node)
            node.add_reference(image_node)
        self.signal("refresh_scene", "Scene")

    def convert_raster_to_path(node, mode):
        def feedback(msg):
            busy.change(msg=msg, keep=1)
            busy.show()

        busy = self.kernel.busyinfo
        busy.start(msg="Converting Raster")
        busy.show()
        with self.undoscope(f"To path: {mode}"):
            busy.change(msg=_("Creating image"), keep=1)
            busy.show()
            image, matrix = create_image_from_operation(node)
            if image is None:
                busy.end()
                return
            vertical = mode.lower() != "horizontal"
            bidirectional = self._image_2_path_bidirectional
            threshold = 0.5 if self._image_2_path_optimize else None  # Half a percent
            geom = Geomstr.image(
                image,
                vertical=vertical,
                bidirectional=bidirectional,
            )
            if threshold:
                geom.two_opt_distance(auto_stop_threshold=threshold, feedback=feedback)
            # self.context
            try:
                spot_value = float(Length(getattr(self.device, "laserspot", "0.3mm")))
            except ValueError:
                spot_value = 1000

            n = self.elem_branch.add(
                type="elem path",
                geometry=geom,
                stroke=self.default_stroke,
                stroke_width=spot_value,
                matrix=matrix,
            )
            if self.classify_new:
                self.classify([n])
        busy.end()

    @tree_submenu(_("Create image/path"))
    @tree_separator_before()
    @tree_operation(
        _("Horizontal"),
        node_type="op raster",
        help=_("Create a horizontal linepattern from the raster"),
        grouping="OPS_75_CONVERTIMAGE",
    )
    def raster_convert_to_path_horizontal(node, **kwargs):
        # Language hint _("To path: Horizontal")
        convert_raster_to_path(node, "Horizontal")

    @tree_submenu(_("Create image/path"))
    @tree_operation(
        _("Vertical"),
        node_type="op raster",
        help=_("Create a vertical linepattern from the raster"),
        grouping="OPS_75_CONVERTIMAGE",
    )
    def raster_convert_to_path_vertical(node, **kwargs):
        convert_raster_to_path(node, "Vertical")

    @tree_submenu(_("Create image/path"))
    @tree_separator_before()
    @tree_check(load_for_path_1)
    @tree_operation(
        _("Bidirectional"),
        node_type="op raster",
        help=_(
            "Shall the line pattern be able to travel back and forth or will it always start at the same side"
        ),
        grouping="OPS_75_CONVERTIMAGE",
    )
    def set_raster_2_path_option_1(node, **kwargs):
        self._image_2_path_bidirectional = not self._image_2_path_bidirectional

    @tree_submenu(_("Create image/path"))
    @tree_check(load_for_path_2)
    @tree_operation(
        _("Optimize travel"),
        node_type="op raster",
        help=_(
            "Shall the line pattern be able to travel back and forth or will it always start at the same side"
        ),
        grouping="OPS_75_CONVERTIMAGE",
    )
    def set_raster_2_path_option_2(node, **kwargs):
        self._image_2_path_optimize = not self._image_2_path_optimize

    def add_after_index(node=None):
        try:
            if node is None:
                node = list(self.ops(selected=True))[-1]
            operations = self._tree.get(type="branch ops").children
            return operations.index(node) + 1
        except (ValueError, IndexError):
            return None

    ## @tree_separator_before()
    @tree_submenu(_("Insert operation"))
    @tree_operation(
        _("Add Image"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_image(node, **kwargs):
        append_operation_image(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert operation"))
    @tree_operation(
        _("Add Raster"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_raster(node, **kwargs):
        append_operation_raster(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert operation"))
    @tree_operation(
        _("Add Engrave"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_engrave(node, **kwargs):
        append_operation_engrave(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert operation"))
    @tree_operation(
        _("Add Cut"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_cut(node, **kwargs):
        append_operation_cut(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert operation"))
    @tree_operation(
        _("Add Hatch"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_hatch(node, **kwargs):
        append_operation_hatch(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert operation"))
    @tree_operation(
        _("Add Dots"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_dots(node, **kwargs):
        append_operation_dots(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(
        _("Add Home"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_home(node, **kwargs):
        append_operation_home(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(
        _("Add Return to Origin"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_origin(node, **kwargs):
        append_operation_goto(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(
        _("Add Beep"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_beep(node, **kwargs):
        append_operation_beep(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(
        _("Add Interrupt"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_interrupt(node, **kwargs):
        append_operation_interrupt(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_prompt("wait_time", _("Wait for how long (in seconds)?"), data_type=float)
    @tree_operation(
        _("Add Wait"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_wait(node, wait_time, **kwargs):
        append_operation_wait(
            node, wait_time=wait_time, pos=add_after_index(node), **kwargs
        )

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(
        _("Add Output"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_output(node, **kwargs):
        append_operation_output(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(
        _("Add Input"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_input(node, **kwargs):
        append_operation_input(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(
        _("Add Coolant on"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_cool_on(node, pos=None, **kwargs):
        append_operation_cool_on(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(
        _("Add Coolant Off"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_cool_off(node, pos=None, **kwargs):
        append_operation_cool_off(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(
        _("Add Home/Beep/Interrupt"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_home_beep_interrupt(node, **kwargs):
        pos = add_after_index(node)
        append_operation_home(node, pos=pos, **kwargs)
        if pos:
            pos += 1
        append_operation_beep(node, pos=pos, **kwargs)
        if pos:
            pos += 1
        append_operation_interrupt(node, pos=pos, **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(
        _("Add Origin/Beep/Interrupt"),
        node_type=op_nodes,
        help=_("Add an operation to the tree"),
        grouping="OPS_40_ADDITION",
    )
    def add_operation_origin_beep_interrupt(node, **kwargs):
        pos = add_after_index(node)
        append_operation_goto(node, pos=pos, **kwargs)
        if pos:
            pos += 1
        append_operation_beep(node, pos=pos, **kwargs)
        if pos:
            pos += 1
        append_operation_interrupt(node, pos=pos, **kwargs)

    @tree_operation(
        _("Reload '{name}'"),
        node_type="file",
        help=_("Reload the content of the file"),
        grouping="40_ELEM_FILE",
    )
    def reload_file(node, **kwargs):
        filepath = node.filepath
        if not os.path.exists(filepath):
            self.signal(
                "warning",
                _("The file no longer exists!"),
                _("File does not exist."),
            )
            return
        to_be_removed = [node]
        for e in self.elem_branch.children:
            if (
                e.type == "file"
                and e.filepath == node.filepath
                and e not in to_be_removed
            ):
                to_be_removed.append(e)
        for e in self.reg_branch.children:
            if (
                e.type == "file"
                and e.filepath == node.filepath
                and e not in to_be_removed
            ):
                to_be_removed.append(e)
        for e in to_be_removed:
            e.remove_node()
        self.load(filepath)

    @tree_operation(
        _("Open containing folder: '{name}'"),
        node_type="file",
        help=_("Open this file working directory in the system's file manager"),
        grouping="40_ELEM_FILE",
    )
    def open_file_in_explorer(node, **kwargs):
        file_path = node.filepath

        import platform
        import subprocess

        system_platform = platform.system()

        if system_platform == "Windows":
            # Use the "start" command to open the file explorer in Windows
            # subprocess.run(["start", "explorer", "/select,", os.path.normpath(file_path)], shell=True)
            subprocess.run(["explorer", "/select,", os.path.normpath(file_path)])

        elif system_platform == "Darwin":
            # Use the "open" command to open Finder on macOS
            subprocess.run(["open", "-R", os.path.normpath(file_path)])

        elif system_platform == "Linux":
            # Use the "xdg-open" command to open the file explorer on Linux
            normalized = os.path.normpath(file_path)
            directory = os.path.dirname(normalized)
            subprocess.run(["xdg-open", directory])

    @tree_operation(
        _("Open in System: '{name}'"),
        node_type="file",
        help=_(
            "Open this file in the system application associated with this type of file"
        ),
        grouping="40_ELEM_FILE",
    )
    def open_system_file(node, **kwargs):
        filepath = node.filepath
        if not os.path.exists(filepath):
            self.signal(
                "warning",
                _("The file no longer exists!"),
                _("File does not exist."),
            )
            return

        normalized = os.path.realpath(filepath)

        import platform

        system = platform.system()
        if system == "Darwin":
            from os import system as open_in_shell

            open_in_shell(f"open '{normalized}'")
        elif system == "Windows":
            from os import startfile as open_in_shell

            open_in_shell(f'"{normalized}"')
        else:
            from os import system as open_in_shell

            open_in_shell(f"xdg-open '{normalized}'")

    def get_values():
        return [o for o in self.ops() if o.type.startswith("op")]

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_submenu(_("Assign Operation"))
    @tree_values("op_assign", values=get_values)
    @tree_operation(
        "{op_assign}",
        node_type=elem_nodes,
        help=_("Assign an operation to the selected elements"),
        grouping="40_ELEM_CLASSIFY",
    )
    def menu_assign_operations(node, op_assign, **kwargs):
        if self.classify_inherit_stroke:
            impose = "to_op"
            attrib = "stroke"
            similar = True
        elif self.classify_inherit_fill:
            impose = "to_op"
            attrib = "fill"
            similar = True
        else:
            impose = None
            attrib = None
            similar = False
        exclusive = self.classify_inherit_exclusive
        data = list(self.elems(emphasized=True))
        if not data:
            return
        with self.undoscope("Assign operation"):
            self.assign_operation(
                op_assign=op_assign,
                data=data,
                impose=impose,
                attrib=attrib,
                similar=similar,
                exclusive=exclusive,
            )

    def exclusive_match(node, **kwargs):
        return self.classify_inherit_exclusive

    ## @tree_separator_before()
    @tree_submenu(_("Assign Operation"))
    @tree_operation(
        _("Remove all assignments from operations"),
        node_type=elem_group_nodes,
        help=_("Any existing assignment of this element to operations will be removed"),
        grouping="40_ELEM_CLASSIFY_options",
    )
    def remove_assignments(singlenode, **kwargs):
        def rem_node(rnode):
            # recursively remove assignments...
            if rnode.type in ("file", "group"):
                for cnode in list(rnode._children):
                    rem_node(cnode)
            else:
                for ref in list(rnode.references):
                    ref.remove_node()

        # _("Remove assignments")
        with self.undoscope("Remove assignments"):
            for node in list(self.elems(emphasized=True)):
                rem_node(node)
        self.signal("refresh_tree")

    ## @tree_separator_before()
    @tree_submenu(_("Assign Operation"))
    @tree_check(exclusive_match)
    @tree_operation(
        _("Exclusive assignment"),
        node_type=elem_nodes,
        help=_(
            "An assignment will remove all other classifications of this element if checked"
        ),
        grouping="40_ELEM_CLASSIFY_options",
    )
    def set_assign_option_exclusive(node, **kwargs):
        self.classify_inherit_exclusive = not self.classify_inherit_exclusive

    def stroke_match(node, **kwargs):
        return self.classify_inherit_stroke

    ## @tree_separator_before()
    @tree_submenu(_("Assign Operation"))
    @tree_check(stroke_match)
    @tree_operation(
        _("Inherit stroke and classify similar"),
        node_type=elem_nodes,
        help=_("Operation will inherit element stroke color"),
        grouping="40_ELEM_CLASSIFY_options",
    )
    def set_assign_option_stroke(node, **kwargs):
        self.classify_inherit_stroke = not self.classify_inherit_stroke
        # Poor man's radio
        if self.classify_inherit_stroke:
            self.classify_inherit_fill = False

    def fill_match(node, **kwargs):
        return self.classify_inherit_fill

    @tree_submenu(_("Assign Operation"))
    @tree_check(fill_match)
    @tree_operation(
        _("Inherit fill and classify similar"),
        node_type=elem_nodes,
        help=_("Operation will inherit element fill color"),
        grouping="40_ELEM_CLASSIFY_options",
    )
    def set_assign_option_fill(node, **kwargs):
        self.classify_inherit_fill = not self.classify_inherit_fill
        # Poor man's radio
        if self.classify_inherit_fill:
            self.classify_inherit_stroke = False

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_submenu(_("Duplicate group"))
    @tree_operation(
        _("Make 1 copy"),
        node_type="group",
        help=_("Create one copy of the selected group"),
        grouping="20_ELEM_DUPLICATION",
    )
    def duplicate_groups_1(node, **kwargs):
        duplicate_groups_n(node, copies=1, **kwargs)

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_submenu(_("Duplicate group"))
    @tree_iterate("copies", 2, 10)
    @tree_operation(
        _("Make {copies} copies"),
        node_type="group",
        help=_("Create multiple copies of the selected group"),
        grouping="20_ELEM_DUPLICATION",
    )
    def duplicate_groups_n(node, copies, **kwargs):
        def copy_a_group(groupnode, parent, dx, dy):
            new_group = copy(groupnode)
            for orgnode in groupnode.children:
                if orgnode.type in ("file", "group"):
                    copy_a_group(orgnode, new_group, dx, dy)
                    continue
                copy_node = copy(orgnode)
                if hasattr(copy_node, "matrix"):
                    copy_node.matrix *= Matrix.translate(dx, dy)
                # Need to add stroke and fill, as copy will take the
                # default values for these attributes
                options = ["fill", "stroke", "wxfont"]
                for optional in options:
                    if hasattr(orgnode, optional):
                        setattr(copy_node, optional, getattr(orgnode, optional))
                had_optional = False
                options = []
                for prop in dir(orgnode):
                    if prop.startswith("mk"):
                        options.append(prop)
                for optional in options:
                    if hasattr(orgnode, optional):
                        setattr(copy_node, optional, getattr(orgnode, optional))
                        had_optional = True

                if self.copy_increases_wordlist_references and hasattr(orgnode, "text"):
                    copy_node.text = self.wordlist_delta(orgnode.text, delta_wordlist)
                elif self.copy_increases_wordlist_references and hasattr(
                    orgnode, "mktext"
                ):
                    copy_node.mktext = self.wordlist_delta(
                        orgnode.mktext, delta_wordlist
                    )
                new_group.add_node(copy_node)
                if had_optional:
                    for property_op in self.kernel.lookup_all("path_updater/.*"):
                        property_op(self.kernel.root, copy_node)
                copy_nodes.append(copy_node)
            parent.add_node(new_group)
            dm = new_group.default_map()

        copy_nodes = []
        with self.undoscope("Duplicate element(s)"):
            _dx = self.length_x("3mm")
            _dy = self.length_y("3mm")
            delta_wordlist = 0
            for n in range(copies):
                delta_wordlist += 1
                copy_a_group(node, node.parent, (n + 1) * _dx, (n + 1) * _dy)
        if copy_nodes:
            if self.classify_new:
                self.classify(copy_nodes)
            self.signal("element_property_reload", copy_nodes)
        self.set_emphasis(None)

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_submenu(_("Duplicate element(s)"))
    @tree_operation(
        _("Make 1 copy"),
        node_type=elem_nodes,
        help=_("Create one copy of the selected elements"),
        grouping="20_ELEM_DUPLICATION",
    )
    def duplicate_element_1(node, **kwargs):
        duplicate_element_n(node, copies=1, **kwargs)

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_submenu(_("Duplicate element(s)"))
    @tree_iterate("copies", 2, 10)
    @tree_operation(
        _("Make {copies} copies"),
        node_type=elem_nodes,
        help=_("Create multiple copies of the selected elements"),
        grouping="20_ELEM_DUPLICATION",
    )
    def duplicate_element_n(node, copies, **kwargs):
        def copy_single_node(orgnode, orgparent, times, dx, dy):
            delta_wordlist = 0
            for n in range(times):
                delta_wordlist += 1

                copy_node = copy(orgnode)
                if hasattr(copy_node, "matrix"):
                    copy_node.matrix *= Matrix.translate((n + 1) * dx, (n + 1) * dy)
                # Need to add stroke and fill, as copy will take the
                # default values for these attributes
                options = ["fill", "stroke", "wxfont"]
                for optional in options:
                    if hasattr(orgnode, optional):
                        setattr(copy_node, optional, getattr(orgnode, optional))
                had_optional = False
                options = []
                for prop in dir(orgnode):
                    if prop.startswith("mk"):
                        options.append(prop)
                for optional in options:
                    if hasattr(orgnode, optional):
                        setattr(copy_node, optional, getattr(orgnode, optional))
                        had_optional = True

                if self.copy_increases_wordlist_references and hasattr(orgnode, "text"):
                    copy_node.text = self.wordlist_delta(orgnode.text, delta_wordlist)
                elif self.copy_increases_wordlist_references and hasattr(
                    orgnode, "mktext"
                ):
                    copy_node.mktext = self.wordlist_delta(
                        orgnode.mktext, delta_wordlist
                    )
                orgparent.add_node(copy_node)
                if had_optional:
                    for property_op in self.kernel.lookup_all("path_updater/.*"):
                        property_op(self.kernel.root, copy_node)

                copy_nodes.append(copy_node)

                if orgnode.type in ("file", "group"):
                    newparent = copy_node
                    for cnode in orgnode.children:
                        copy_single_node(
                            cnode, newparent, 1, (n + 1) * dx, (n + 1) * dy
                        )
                    dm = copy_node.default_map()

        copy_nodes = []
        with self.undoscope("Duplicate element(s)"):
            _dx = self.length_x("3mm")
            _dy = self.length_y("3mm")
            alldata = list(self.elems(emphasized=True))
            if len(alldata) == 0:
                alldata = [node]
            if alldata:
                # Special case: did we select all elements inside one group?
                first_parent = alldata[0].parent
                justonegroup = all(node.parent is first_parent for node in alldata)
                if justonegroup:
                    minimaldata = alldata
                else:
                    minimaldata = self.condense_elements(alldata, expand_at_end=False)
                for e in minimaldata:
                    parent = e.parent
                    copy_single_node(e, parent, copies, _dx, _dy)

                if self.classify_new:
                    self.classify(copy_nodes)
        if copy_nodes:
            self.signal("element_property_reload", copy_nodes)
        self.set_emphasis(None)

    def has_wordlist(node):
        result = False
        txt = ""
        if hasattr(node, "text") and node.text is not None:
            txt = str(node.text)
        if hasattr(node, "mktext") and node.mktext is not None:
            txt = str(node.mktext)
        # Very stupid, but good enough
        if "{" in txt and "}" in txt:
            result = True
        return result

    @tree_conditional(lambda node: has_wordlist(node))
    @tree_operation(
        _("Increase Wordlist-Reference"),
        node_type=(
            "elem text",
            "elem path",
        ),
        help=_("Adjusts the reference value for a wordlist, i.e. {name} to {name#+1}"),
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def wlist_plus(singlenode, **kwargs):
        data = list()
        nodes = (node for node in self.elems(emphasized=True) if has_wordlist(node))
        if not nodes:
            return
        with self.undoscope("Increase Wordlist-Reference"):
            for node in nodes:
                delta_wordlist = 1
                if hasattr(node, "text"):
                    node.text = self.wordlist_delta(node.text, delta_wordlist)
                    node.altered()
                    data.append(node)
                elif hasattr(node, "mktext"):
                    node.mktext = self.wordlist_delta(node.mktext, delta_wordlist)
                    for property_op in self.kernel.lookup_all("path_updater/.*"):
                        property_op(self.kernel.root, node)
                    data.append(node)
        if data:
            self.signal("element_property_update", data)

    @tree_conditional(lambda node: has_wordlist(node))
    @tree_operation(
        _("Decrease Wordlist-Reference"),
        node_type=(
            "elem text",
            "elem path",
        ),
        help=_(
            "Adjusts the reference value for a wordlist, i.e. {name#+3} to {name#+2}"
        ),
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def wlist_minus(singlenode, **kwargs):
        data = list()
        nodes = (node for node in self.elems(emphasized=True) if has_wordlist(node))
        if not nodes:
            return
        with self.undoscope("Decrease Wordlist-Reference"):
            for node in nodes:
                delta_wordlist = -1
                if hasattr(node, "text"):
                    node.text = self.wordlist_delta(node.text, delta_wordlist)
                    node.altered()
                    data.append(node)
                elif hasattr(node, "mktext"):
                    node.mktext = self.wordlist_delta(node.mktext, delta_wordlist)
                    for property_op in self.kernel.lookup_all("path_updater/.*"):
                        property_op(self.kernel.root, node)
                    data.append(node)
        if data:
            self.signal("element_property_update", data)

    @tree_conditional(lambda node: has_vectorize(node))
    @tree_submenu(_("Outline element(s)..."))
    @tree_iterate("offset", 1, 10)
    @tree_operation(
        _("...with {offset}mm distance"),
        node_type=elem_nodes,
        help=_("Create an outline around the selected elements"),
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def make_outlines(node, offset=1, **kwargs):
        with self.undoscope("Outline"):
            self(f"outline {offset}mm\n")
        self.signal("refresh_tree")

    @tree_conditional(
        lambda node: not is_regmark(node) and hasattr(node, "as_geometry")
    )
    @tree_submenu(_("Offset shapes..."))
    @tree_iterate("offset", 1, 5)
    @tree_operation(
        _("...to outside with {offset}mm distance"),
        node_type=elem_nodes,
        help=_("Create an outer offset around the selected elements"),
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def make_positive_offsets(node, offset=1, **kwargs):
        with self.undoscope("Offset"):
            self(f"offset {offset}mm\n")
        self.signal("refresh_tree")

    @tree_conditional(
        lambda node: not is_regmark(node) and hasattr(node, "as_geometry")
    )
    @tree_submenu(_("Offset shapes..."))
    @tree_iterate("offset", 1, 5)
    @tree_operation(
        _("...to inside with {offset}mm distance"),
        node_type=elem_nodes,
        help=_("Create an inner offset around the selected elements"),
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def make_negative_offsets(node, offset=1, **kwargs):
        with self.undoscope("Offset"):
            self(f"offset -{offset}mm\n")
        self.signal("refresh_tree")

    def mergeable(node):
        elems = list(self.elems(emphasized=True))
        if len(elems) < 2:
            return False
        result = True
        for e in elems:
            if e.type not in (
                "elem ellipse",
                "elem path",
                "elem polyline",
                "elem rect",
                "elem line",
            ):
                result = False
            break
        return result

    @tree_conditional(lambda node: mergeable(node))
    @tree_operation(
        _("Merge elements"),
        node_type=(
            "elem ellipse",
            "elem path",
            "elem polyline",
            "elem rect",
            "elem line",
        ),
        help=_("Merge two or more elements together into a single path"),
    )
    def elem_merge(singlenode, **kwargs):
        def get_common_parent_node(data):
            def _get_common_parent(node1, node2):
                top = self.elem_branch
                list1 = [node1]
                list2 = [node2]
                n = node1
                while n is not top:
                    n = n.parent
                    list1.append(n)
                n = node2
                while n is not top:
                    n = n.parent
                    list2.append(n)
                # Both lists contain the node itself and the top node
                for n in list1:
                    if n in list2:
                        return n
                # That should not be the case...
                return top

            root = self.elem_branch
            par = None
            for e in data:
                if par is None:
                    par = e
                else:
                    par = _get_common_parent(par, e)
                if par is root:
                    break
            return par

        data = list(self.elems(emphasized=True))
        if not data:
            return
        with self.undoscope("Merge elements"):
            parent = get_common_parent_node(data)
            node = parent.add(type="elem path")
            for e in data:
                try:
                    path = e.as_geometry()
                except AttributeError:
                    continue
                try:
                    if node.stroke is None:
                        node.stroke = e.stroke
                except AttributeError:
                    pass
                try:
                    if node.fill is None:
                        node.fill = e.fill
                except AttributeError:
                    pass
                try:
                    if node.stroke_width is None:
                        node.stroke_width = e.stroke_width
                except AttributeError:
                    pass
                node.geometry.append(path)
            self.remove_elements(data)
            # Newly created! Classification needed?
            data = [node]
            if self.classify_new:
                self.classify(data)
        self.set_node_emphasis(node, True)
        self.signal("refresh_scene", "Scene")
        self.signal("rebuild_tree", "elements")
        node.focus()

    def has_vectorize(node):
        result = False
        make_vector = self.lookup("render-op/make_vector")
        if make_vector:
            result = True
        return result

    def has_vtrace_vectorize(node):
        return self.kernel.has_command("vtracer")

    @tree_submenu(_("Vectorization..."))
    @tree_separator_after()
    @tree_conditional(lambda node: has_vectorize(node))
    @tree_operation(
        _("Trace bitmap"),
        node_type=(
            "elem text",
            "elem image",
        ),
        help=_("Vectorize the given element"),
        grouping="70_ELEM_IMAGES_Z",  # test
    )
    def trace_bitmap(node, **kwargs):
        with self.undoscope("Trace bitmap"):
            self("vectorize\n")

    @tree_submenu(_("Vectorization..."))
    @tree_conditional(lambda node: has_vtrace_vectorize(node))
    @tree_operation(
        _("Trace bitmap via vtracer"),
        node_type=("elem image",),
        help=_("Vectorize the given element"),
        grouping="70_ELEM_IMAGES_Z",  # test
    )
    def trace_bitmap_vtrace(node, **kwargs):
        self("vtracer\n")

    @tree_submenu(_("Vectorization..."))
    @tree_operation(
        _("Contour detection - shapes"),
        node_type=("elem image",),
        help=_("Recognize contours=shapes on the given element"),
        grouping="70_ELEM_IMAGES_Z",  # test
    )
    def contour_bitmap_polyline(node, **kwargs):
        current = self.setting(str, "contour_size", "big")
        if current == "small":
            minval = 0.2
        elif current == "normal":
            minval = 2
        else:
            minval = 10
        inner = self.setting(bool, "contour_inner", True)
        option = f"--minimal {minval:.2f}{' --inner' if inner else ''}"
        with self.undoscope("Contour detection"):
            self(f"identify_contour --simplified {option}\n")

    @tree_submenu(_("Vectorization..."))
    @tree_separator_after()
    @tree_operation(
        _("Contour detection - bounding"),
        node_type=("elem image",),
        help=_("Recognize contours=shapes on the given element"),
        grouping="70_ELEM_IMAGES_Z",  # test
    )
    def contour_bitmap_rectangles(node, **kwargs):
        current = self.setting(str, "contour_size", "big")
        if current == "small":
            minval = 0.2
        elif current == "normal":
            minval = 2
        else:
            minval = 10
        inner = self.setting(bool, "contour_inner", True)
        option = f"--minimal {minval:.2f}{' --inner' if inner else ''}"
        with self.undoscope("Contour detection"):
            self(f"identify_contour --rectangles {option}\n")

    def sizecheck(value):
        def comparison(*args, **kwargs):
            current = self.setting(str, "contour_size", "big")
            return current == value

        return comparison

    def inner_check(*args, **kwargs):
        current = self.setting(bool, "contour_inner", True)
        return current

    @tree_separator_before()
    @tree_submenu(_("Vectorization..."))
    @tree_check(inner_check)
    @tree_operation(
        _("Ignore inner areas"),
        node_type=("elem image",),
        help=_("Inner areas will be ignored"),
        grouping="70_ELEM_IMAGES_Z",
    )
    def set_contour_inner(node, **kwargs):
        current = self.setting(bool, "contour_inner", True)
        self.contour_inner = not self.contour_inner

    @tree_separator_before()
    @tree_submenu(_("Vectorization..."))
    @tree_check(sizecheck("big"))
    @tree_operation(
        _("Big objects"),
        node_type=("elem image",),
        help=_("Only large object will be recognized if checked"),
        grouping="70_ELEM_IMAGES_Z",
    )
    def set_contour_size_big(node, **kwargs):
        self.setting(str, "contour_size", "big")
        self.contour_size = "big"

    @tree_submenu(_("Vectorization..."))
    @tree_check(sizecheck("normal"))
    @tree_operation(
        _("Normal objects"),
        node_type=("elem image",),
        help=_("Also medium sized objects will be recognized if checked"),
        grouping="70_ELEM_IMAGES_Z",
    )
    def set_contour_size_normal(node, **kwargs):
        self.setting(str, "contour_size", "big")
        self.contour_size = "normal"

    @tree_submenu(_("Vectorization..."))
    @tree_check(sizecheck("small"))
    @tree_operation(
        _("Small objects"),
        node_type=("elem image",),
        help=_("Also small objects will be recognized if checked"),
        grouping="70_ELEM_IMAGES_Z",
    )
    def set_contour_size_small(node, **kwargs):
        self.setting(str, "contour_size", "big")
        self.contour_size = "small"

    @tree_operation(
        _("Convert to vector text"),
        node_type="elem text",
        help=_("Convert bitmap text to vector text"),
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def convert_to_vectext(node, **kwargs):
        data = []
        nodelist = list(self.flat(emphasized=True, types=("elem text",)))
        if not nodelist:
            return
        with self.undoscope("Convert to vector text"):
            for e in nodelist:
                if e is None or not hasattr(e, "wxfont"):
                    # print (f"Invalid node: {e.type}")
                    continue
                text = e.text
                facename = e.wxfont.GetFaceName()
                # print (f"Facename: {facename}, svg: {getattr(e, 'font_family', '')}")
                fontfile = self.kernel.root.fonts.face_to_full_name(facename)
                if fontfile is None:
                    # print (f"could not find a font for {facename}")
                    return
                fontname = self.kernel.root.fonts.short_name(fontfile)
                # print (f"{facename} -> {fontname}, {fontfile}")
                node_args = dict()
                node_args["type"] = "elem path"
                node_args["stroke"] = e.stroke
                node_args["fill"] = e.fill
                node_args["stroke_width"] = 500
                node_args["fillrule"] = Fillrule.FILLRULE_NONZERO
                node_args["mktext"] = text
                fsize = e.font_size
                if fsize is None:
                    fsize = 12
                fsize *= 4 / 3
                node_args["mkfontsize"] = fsize
                node_args["mkfont"] = fontname
                anchor = e.anchor
                if anchor is None:
                    anchor = "start"
                node_args["mkalign"] = anchor
                # print (f"{text} aligns in the {anchor}")

                old_matrix = Matrix(e.matrix)
                cc = e.bounds
                p0 = old_matrix.point_in_inverse_space((cc[0], cc[1]))
                p1 = old_matrix.point_in_inverse_space((cc[2], cc[3]))

                # node_args["mkcoordx"] = p0.x
                # node_args["mkcoordy"] = p1.y

                node_args["geometry"] = Geomstr.rect(
                    x=p0.x, y=p1.y, width=p1.x - p0.x, height=p1.y - p0.y
                )
                if e.label is None:
                    x = text.split("\n")
                    node_args["label"] = f"Text: {x[0]}"
                newnode = e.replace_node(**node_args)
                newnode.matrix = old_matrix
                newnode.matrix.pre_translate_y(p1.y - p0.y)

                # Now we need to render it...
                # newnode.set_dirty_bounds()
                # newtext = self.wordlist_translate(text, elemnode=newnode, increment=False)
                # newnode._translated_text = newtext

                kernel = self.kernel
                for property_op in kernel.lookup_all("path_updater/.*"):
                    property_op(kernel.root, newnode)

                if hasattr(newnode, "_cache"):
                    newnode._cache = None

                data.append(newnode)
            if data:
                if self.classify_new:
                    self.classify(data)
        self.signal("rebuild_tree", "elements")
        self.signal("refresh_scene", "Scene")

    @tree_conditional(
        lambda node: not is_regmark(node)
        and hasattr(node, "as_geometry")
        and node.type != "elem path"
    )
    @tree_operation(
        _("Convert to path"),
        node_type=elem_nodes,
        help="Convert node to path",
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def convert_to_path(singlenode, **kwargs):
        nodes = (
            node for node in self.elems(emphasized=True) if hasattr(node, "as_geometry")
        )
        if not nodes:
            return
        with self.undoscope("Convert to path"):
            for node in nodes:
                node_attributes = []
                for attrib in ("stroke", "fill", "stroke_width", "stroke_scaled"):
                    if hasattr(node, attrib):
                        oldval = getattr(node, attrib, None)
                        node_attributes.append([attrib, oldval])
                if hasattr(node, "final_geometry"):
                    geometry = node.final_geometry()
                else:
                    geometry = node.as_geometry()
                newnode = node.replace_node(geometry=geometry, type="elem path")
                for item in node_attributes:
                    setattr(newnode, item[0], item[1])
                newnode.altered()

    # @tree_conditional(
    #     lambda node: hasattr(node, "as_geometry") and node.has_ancestor("branch elems")
    # )
    @tree_operation(
        _("Convert to path"),
        node_type=effect_nodes,
        help="Convert effect to path",
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def convert_to_path_effect(singlenode, **kwargs):
        nodes = (
            node
            for node in self.flat(types=effect_nodes, emphasized=True)
            if hasattr(node, "as_geometry")
        )
        if not nodes:
            return
        with self.undoscope("Convert to path"):
            for node in nodes:
                node_attributes = []
                for attrib in ("stroke", "fill", "stroke_width", "stroke_scaled"):
                    if hasattr(node, attrib):
                        oldval = getattr(node, attrib, None)
                        node_attributes.append([attrib, oldval])
                geometry = node.as_geometry()
                node.remove_all_children()
                if not len(geometry):
                    return
                newnode = node.replace_node(geometry=geometry, type="elem path")
                for item in node_attributes:
                    setattr(newnode, item[0], item[1])
                newnode.altered()

    def valid_keyhole_pair():
        number_of_images: int = 0
        number_of_masks: int = 0
        for node in self.elems(emphasized=True):
            if node.type == "elem image":
                number_of_images += 1
            elif hasattr(node, "as_geometry"):
                number_of_masks += 1

            if number_of_masks > 1:
                # No need to go through all elements any longer
                return False

        return bool(number_of_images > 0 and number_of_masks == 1)

    @tree_conditional(lambda node: valid_keyhole_pair())
    @tree_operation(
        _("Add a keyhole"),
        node_type=elem_nodes,
        help=_("Add a keyhole effect between the selected elements"),
        grouping="70_ELEM_IMAGES",
    )
    def add_a_keyhole(singlenode, **kwargs):
        with self.undoscope("Add a keyhole"):
            self.validate_ids()
            self("keyhole\n")

    @tree_conditional(
        lambda node: hasattr(node, "as_geometry") and self.has_keyhole_subscribers(node)
    )
    @tree_operation(
        _("Remove keyhole"),
        node_type=elem_nodes,
        help="Remove all associated keyholes",
        grouping="70_ELEM_IMAGES",
    )
    def remove_all_keyholes(singlenode, **kwargs):
        with self.undoscope("Remove keyhole"):
            for node in list(self.elems(emphasized=True)):
                if not hasattr(node, "as_geometry"):
                    continue
                self.remove_keyhole(node)
        self.signal("modified_by_tool")

    @tree_submenu(_("Flip"))
    ## @tree_separator_before()
    @tree_conditional(lambda node: not is_regmark(node))
    @tree_conditional_try(lambda node: node.can_scale)
    @tree_operation(
        _("Horizontally"),
        node_type=elem_group_nodes,
        help=_("Mirror Horizontally"),
        grouping="50_ELEM_MODIFY",
    )
    def mirror_elem(node, **kwargs):
        bounds = self._emphasized_bounds
        if bounds is None:
            return
        center_x = (bounds[2] + bounds[0]) / 2.0
        center_y = (bounds[3] + bounds[1]) / 2.0
        with self.undoscope("Flip"):
            self(f"scale -1 1 {center_x} {center_y}\n")

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_submenu(_("Flip"))
    @tree_conditional_try(lambda node: node.can_scale)
    @tree_operation(
        _("Vertically"),
        node_type=elem_group_nodes,
        help=_("Flip Vertically"),
        grouping="50_ELEM_MODIFY",
    )
    def flip_elem(node, **kwargs):
        bounds = self._emphasized_bounds
        if bounds is None:
            return
        center_x = (bounds[2] + bounds[0]) / 2.0
        center_y = (bounds[3] + bounds[1]) / 2.0
        with self.undoscope("Flip"):
            self(f"scale 1 -1 {center_x} {center_y}\n")

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_conditional_try(lambda node: node.can_scale)
    @tree_submenu(_("Scale"))
    @tree_iterate("scale", 25, 1, -1)
    @tree_calc("scale_percent", lambda i: f"{(600.0 / float(i)):.2f}")
    @tree_operation(
        _("Scale {scale_percent}%"),
        node_type=elem_group_nodes,
        help=_("Scale Element"),
        grouping="50_ELEM_MODIFY",
    )
    def scale_elem_amount(node, scale, **kwargs):
        scale = 6.0 / float(scale)
        bounds = self._emphasized_bounds
        if bounds is None:
            return
        center_x = (bounds[2] + bounds[0]) / 2.0
        center_y = (bounds[3] + bounds[1]) / 2.0
        with self.undoscope("Scale"):
            self(f"scale {scale} {scale} {center_x} {center_y}\n")

    # @tree_conditional(lambda node: isinstance(node.object, SVGElement))
    @tree_conditional(lambda node: not is_regmark(node))
    @tree_conditional_try(lambda node: node.can_rotate)
    @tree_submenu(_("Rotate"))
    @tree_values(
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
            -10,
            -15,
            -20,
            -30,
            -45,
            -60,
            -90,
        ),
    )
    @tree_operation(
        _("Rotate {angle}°"),
        node_type=elem_group_nodes,
        help=_("Rotate the selected elements by the given amount"),
        grouping="50_ELEM_MODIFY",
    )
    def rotate_elem_amount(node, angle, **kwargs):
        turns = float(angle) / 360.0
        bounds = self._emphasized_bounds
        if bounds is None:
            return
        center_x = (bounds[2] + bounds[0]) / 2.0
        center_y = (bounds[3] + bounds[1]) / 2.0
        with self.undoscope("Rotate"):
            self(f"rotate {turns}turn {center_x} {center_y}\n")
        self.signal("ext-modified")

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_conditional(lambda node: has_changes(node))
    @tree_conditional_try(lambda node: node.can_modify)
    @tree_operation(
        _("Reify user changes"),
        node_type=elem_group_nodes,
        help=_("Integrate user scale, translate and rotate changes"),
        grouping="80_ELEM_REIFY",
    )
    def reify_elem_changes(node, **kwargs):
        with self.undoscope("Reify User Changes"):
            self("reify\n")
        self.signal("ext-modified")

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_conditional_try(lambda node: node.can_modify)
    @tree_operation(
        _("Break Subpaths"),
        node_type="elem path",
        help=_("Split paths into subelements (if any)"),
        grouping="50_ELEM_MODIFY_ZMISC",
    )
    def break_subpath_elem(node, **kwargs):
        with self.undoscope("Break Subpaths"):
            self("element subpath\n")

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_conditional(lambda node: has_changes(node))
    @tree_conditional_try(lambda node: node.can_modify)
    @tree_operation(
        _("Reset user changes"),
        node_type=elem_group_nodes,
        help=_("Revert user scale, translate and rotate changes"),
        grouping="80_ELEM_REIFY",
    )
    def reset_user_changes(node, copies=1, **kwargs):
        with self.undoscope("Reset user changes"):
            self("reset\n")
        self.signal("ext-modified")

    @tree_operation(
        _("Merge items"),
        node_type="group",
        help=_("Merge this node's children into 1 path."),
        grouping="40_ELEM_GROUPS",
    )
    def merge_elements(node, **kwargs):
        with self.undoscope("Merge items"):
            self("element merge\n")
            # Is the group now empty? --> delete
            if len(node.children) == 0:
                node.remove_node()

    @tree_conditional(lambda node: node.lock)
    ## @tree_separator_before()
    @tree_operation(
        _("Unlock element, allows manipulation"),
        node_type=elem_nodes,
        help=_("Remove manipulation protection flag"),
    )
    def element_unlock_manipulations(node, **kwargs):
        self("element unlock\n")

    @tree_conditional(lambda node: not node.lock)
    ## @tree_separator_before()
    @tree_operation(
        _("Lock elements, prevents manipulations"),
        node_type=elem_nodes,
        help=_("Set manipulation protection flag"),
        grouping="30_ELEM_VISIBLE",
    )
    def element_lock_manipulations(node, **kwargs):
        self("element lock\n")

    @tree_conditional(lambda node: node.type == "branch reg")
    ## @tree_separator_before()
    @tree_operation(
        _("Toggle visibility of regmarks"),
        node_type="branch reg",
        help=_("Show/Hide the content of the regmark branch"),
        grouping="30_REG_VISIBLE",
    )
    def toggle_visibility(node, **kwargs):
        self.signal("toggle_regmarks")

    @tree_conditional(lambda node: is_regmark(node))
    ## @tree_separator_before()
    @tree_operation(
        _("Move back to elements"),
        node_type=elem_group_nodes,
        help=_("Move the selected regmarks back to the element branch"),
        grouping="REG_10_OPTIONS",
    )
    def move_back(node, **kwargs):
        # Drag and Drop
        with self.undoscope("Move back to elements"):
            drop_node = self.elem_branch
            data = list()
            for item in list(self.regmarks_nodes()):
                # print (item.type, item.emphasized, item.selected, item.highlighted)
                if item.emphasized:
                    data.append(item)
            if not data:
                data.append(node)
            self.drag_and_drop(data, drop_node)

    @tree_conditional(lambda node: not is_regmark(node))
    ## @tree_separator_before()
    @tree_operation(
        _("Move to regmarks"),
        node_type=elem_group_nodes,
        help=_("Move the selected elements to the regmark branch"),
        grouping="90_ELEM_REGMARKS",
    )
    def move_to_regmark(node, **kwargs):
        # Drag and Drop
        with self.undoscope("Move to regmarks"):
            drop_node = self.reg_branch
            data = list()
            for item in list(self.elems_nodes()):
                if item.selected:
                    data.append(item)
            for item in data:
                # No usecase for having a locked regmark element
                if hasattr(item, "lock"):
                    item.lock = False
                drop_node.drop(item)

    @tree_conditional(lambda node: is_regmark(node))
    ## @tree_separator_before()
    @tree_operation(
        _("Create placement"),
        node_type=elem_nodes,
        help=_("Define a job starting point aka placement"),
        grouping="REG_20_PLACEMENT",
    )
    def regmark_as_placement(node, **kwargs):
        if hasattr(node, "path"):
            bb = node.path.bbox(transformed=False)
        elif hasattr(node, "shape"):
            bb = node.shape.bbox(transformed=False)
        else:
            return
        if bb is None:
            return
        corner = 0
        try:
            rotation = node.matrix.rotation.as_radians
        except AttributeError:
            rotation = 0
        pt = node.matrix.point_in_matrix_space(Point(bb[0], bb[1]))
        x = pt.x
        y = pt.y
        with self.undoscope("Create placement"):
            self.op_branch.add(
                type="place point", x=x, y=y, corner=corner, rotation=rotation
            )
        self.signal("refresh_scene", "Scene")

    @tree_conditional(lambda node: is_regmark(node))
    @tree_submenu(_("Toggle magnet-lines"))
    @tree_operation(
        _("Around border"),
        node_type=elem_group_nodes,
        help=_("Set/remove magnet lines around the regmark element"),
        grouping="SCENE",
    )
    def regmark_to_magnet_1(node, **kwargs):
        if not hasattr(node, "bounds"):
            return
        self.signal("magnet_gen", ("outer", node))

    @tree_conditional(lambda node: is_regmark(node))
    @tree_submenu(_("Toggle magnet-lines"))
    @tree_operation(
        _("At center"),
        node_type=elem_group_nodes,
        help=_(
            "Set/remove magnet lines right through the middle of the regmark element"
        ),
        grouping="SCENE",
    )
    def regmark_to_magnet_2(node, **kwargs):
        if not hasattr(node, "bounds"):
            return
        self.signal("magnet_gen", ("center", node))

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Z-depth divide"))
    @tree_iterate("divide", 2, 10)
    @tree_operation(
        _("Divide into {divide} images"),
        node_type="elem image",
        help=_("Split image into multiple subimages based on the grayscale level"),
        grouping="70_ELEM_IMAGES",
    )
    def image_zdepth(node, divide=1, **kwargs):
        if node.image.mode != "RGBA":
            node.image = node.image.convert("RGBA")
        band = 255 / divide
        with self.undoscope("Z-depth divide"):
            for i in range(0, divide):
                threshold_min = i * band
                threshold_max = threshold_min + band
                self(f"image threshold {threshold_min} {threshold_max}\n")

    @tree_conditional(lambda node: node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(
        _("Unlock manipulations"),
        node_type="elem image",
        help=_("Allow manipulations of the image"),
        grouping="70_ELEM_IMAGES",
    )
    def image_unlock_manipulations(node, **kwargs):
        self("image unlock\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(
        _("Lock manipulations"),
        node_type="elem image",
        help=_("Prevent manipulations of the image"),
        grouping="70_ELEM_IMAGES",
    )
    def image_lock_manipulations(node, **kwargs):
        self("image lock\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(
        _("Dither to 1 bit"),
        node_type="elem image",
        help=_("Create a pixelated b/w copy of the image"),
        grouping="70_ELEM_IMAGES",
    )
    def image_dither(node, **kwargs):
        with self.undoscope("Dither"):
            self("image dither\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(
        _("Invert image"),
        node_type="elem image",
        help=_("Invert the image"),
        grouping="70_ELEM_IMAGES",
    )
    def image_invert(node, **kwargs):
        with self.undoscope("Invert image"):
            self("image invert\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(
        _("Mirror horizontal"),
        node_type="elem image",
        help=_("Mirror the image along the Y-Axis"),
        grouping="70_ELEM_IMAGES",
    )
    def image_mirror(node, **kwargs):
        with self.undoscope("Mirror horizontal"):
            self("image mirror\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(
        _("Flip vertical"),
        node_type="elem image",
        help=_("Mirror the image along the X-Axis"),
        grouping="70_ELEM_IMAGES",
    )
    def image_flip(node, **kwargs):
        with self.undoscope("Flip vertical"):
            self("image flip\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(
        _("Rotate 90° CW"),
        node_type="elem image",
        help=_("Rotate the image by 90° clockwise"),
        grouping="70_ELEM_IMAGES",
    )
    def image_cw(node, **kwargs):
        with self.undoscope("Rotate 90° CW"):
            self("image cw\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(
        _("Rotate 90° CCW"),
        node_type="elem image",
        help=_("Rotate the image by 90° counterclockwise"),
        grouping="70_ELEM_IMAGES",
    )
    def image_ccw(node, **kwargs):
        with self.undoscope("Rotate 90° CCW"):
            self("image ccw\n")

    @tree_conditional(lambda node: not node.lock)
    ## @tree_separator_before()
    @tree_submenu(_("Image"))
    @tree_operation(
        _("Identify inner white areas"),
        node_type="elem image",
        help=_("Identify and mark bigger white areas inside the image"),
        grouping="70_ELEM_IMAGES",
    )
    def image_white_area(node, **kwargs):
        # Language hint "White areas"
        with self.undoscope("White areas"):
            self("image innerwhite -l -o -m 2\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(
        _("Split image along white areas"),
        node_type="elem image",
        help=_("Split image along white areas to reduce rastering time"),
        grouping="70_ELEM_IMAGES",
    )
    def image_white_area_split(node, **kwargs):
        # Language hint "Split image"
        with self.undoscope("Split image"):
            self("image innerwhite -w -o -m 2\n")

    @tree_submenu(_("Image"))
    ## @tree_separator_before()
    @tree_operation(
        _("Save original image to output.png"),
        node_type="elem image",
        help=_("Save the unmodified image to disk"),
        grouping="70_ELEM_IMAGES_SAVE",
    )
    def image_save(node, **kwargs):
        self("image save output.png\n")

    @tree_submenu(_("Image"))
    @tree_operation(
        _("Save processed image to output.png"),
        node_type="elem image",
        help=_("Save the modified image to disk"),
        grouping="70_ELEM_IMAGES_SAVE",
    )
    def image_save_processed(node, **kwargs):
        self("image save output.png --processed\n")

    ## @tree_separator_before()
    @tree_submenu(_("Image"))
    @tree_conditional(lambda node: node.keyhole_reference is not None)
    @tree_operation(
        _("Remove keyhole"),
        node_type="elem image",
        help=_("Remove the keyhole-link between image and shape"),
        grouping="70_ELEM_IMAGES_KEYHOLE",
    )
    def image_break_keyhole(node, **kwargs):
        with self.undoscope("Remove keyhole"):
            self("remove_keyhole\n")

    @tree_conditional(lambda node: len(node.children) > 0)
    ## @tree_separator_before()
    @tree_operation(
        _("Expand all children"),
        node_type=(
            "op cut",
            "op raster",
            "op image",
            "op engrave",
            "op dots",
            "branch elems",
            "branch ops",
            "branch reg",
            "group",
            "file",
            "root",
            "effect hatch",
            "effect wobble",
        ),
        help=_("Expand all children of this given node."),
        grouping="ZZZZ_tree",
    )
    def expand_all_children(node, **kwargs):
        node.notify_expand()

    @tree_conditional(lambda node: len(node.children) > 0)
    @tree_operation(
        _("Collapse all children"),
        node_type=(
            "op cut",
            "op raster",
            "op image",
            "op engrave",
            "op dots",
            "branch elems",
            "branch ops",
            "branch reg",
            "group",
            "file",
            "root",
            "effect hatch",
            "effect wobble",
        ),
        help=_("Collapse all children of this given node."),
        grouping="ZZZZ_tree",
    )
    def collapse_all_children(node, **kwargs):
        node.notify_collapse()

    @tree_submenu(_("Magnets"))
    @tree_operation(
        _("...around horizontal edges"),
        node_type=elem_group_nodes,
        help=_("Create magnets around horizontal edges"),
        grouping="Magnet",
    )
    def create_horiz_edges(node, **kwargs):
        if not hasattr(node, "bounds") or node.bounds is None:
            return
        bb = node.bounds
        to_create = (("x", bb[0]), ("x", bb[2]))
        self.signal("create_magnets", to_create)

    @tree_submenu(_("Magnets"))
    @tree_operation(
        _("...including center"),
        node_type=elem_group_nodes,
        help=_("Create magnets around horizontal edges + center"),
        grouping="Magnet",
    )
    def create_horiz_edges_plus_center(node, **kwargs):
        if not hasattr(node, "bounds") or node.bounds is None:
            return
        bb = node.bounds
        to_create = (("x", bb[0]), ("x", bb[2]), ("x", (bb[0] + bb[2]) / 2))
        self.signal("create_magnets", to_create)

    @tree_submenu(_("Magnets"))
    @tree_iterate("steps", 3, 6)
    @tree_operation(
        _("...create edges plus every 1/{steps}"),
        node_type=elem_group_nodes,
        help=_("Create magnets equally spaced along horizontal extension"),
        grouping="Magnet",
    )
    def create_x_horiz_edges(node, steps=3, **kwargs):
        if not hasattr(node, "bounds") or node.bounds is None:
            return
        bb = node.bounds
        to_create = []
        x = bb[0]
        delta = (bb[2] - bb[0]) / steps
        if delta == 0:
            return
        while x <= bb[2]:
            to_create.append(("x", x))
            x += delta
        self.signal("create_magnets", to_create)

    @tree_submenu(_("Magnets"))
    @tree_separator_before()
    @tree_operation(
        _("...around vertical edges"),
        node_type=elem_group_nodes,
        help=_("Create magnets around vertical edges"),
        grouping="Magnet",
    )
    def create_vert_edges(node, **kwargs):
        if not hasattr(node, "bounds") or node.bounds is None:
            return
        bb = node.bounds
        to_create = (("y", bb[1]), ("y", bb[3]))
        self.signal("create_magnets", to_create)

    @tree_submenu(_("Magnets"))
    @tree_operation(
        _("...including center"),
        node_type=elem_group_nodes,
        help=_("Create magnets around vertical edges + center"),
        grouping="Magnet",
    )
    def create_vert_edges_plus_center(node, **kwargs):
        if not hasattr(node, "bounds") or node.bounds is None:
            return
        bb = node.bounds
        to_create = (("y", bb[1]), ("y", bb[3]), ("y", (bb[1] + bb[3]) / 2))
        self.signal("create_magnets", to_create)

    @tree_submenu(_("Magnets"))
    @tree_iterate("steps", 3, 6)
    @tree_operation(
        _("...create edges plus every 1/{steps}"),
        node_type=elem_group_nodes,
        help=_("Create magnets equally spaced along vertical extension"),
        grouping="Magnet",
    )
    def create_x_vert_edges(node, steps=3, **kwargs):
        if not hasattr(node, "bounds") or node.bounds is None:
            return
        bb = node.bounds
        to_create = []
        y = bb[1]
        delta = (bb[3] - bb[1]) / steps
        if delta == 0:
            return
        while y <= bb[3]:
            to_create.append(("y", y))
            y += delta
        self.signal("create_magnets", to_create)
