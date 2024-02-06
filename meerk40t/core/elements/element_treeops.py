"""
This is a large number of flagged tree operations. The details of how these are registered is available in the treeop.py
file. These define the right-click node menu operations. That menu is dynamically created based on various context
cues.
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
from meerk40t.core.units import UNITS_PER_INCH
from meerk40t.kernel import CommandSyntaxError
from meerk40t.svgelements import Matrix, Point
from meerk40t.tools.geomstr import Geomstr

from .element_types import *


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

    @tree_separator_after()
    @tree_conditional(lambda node: len(list(self.ops(selected=True))) == 1)
    @tree_operation(_("Operation properties"), node_type=op_nodes, help="")
    def operation_property(node, **kwargs):
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    @tree_separator_after()
    @tree_operation(_("Edit"), node_type="util console", help="")
    def edit_console_command(node, **kwargs):
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    @tree_separator_after()
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
        help="",
    )
    def path_property(node, **kwargs):
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    @tree_separator_after()
    @tree_operation(_("Group properties"), node_type="group", help="")
    def group_property(node, **kwargs):
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    @tree_separator_after()
    @tree_operation(_("Text properties"), node_type="elem text", help="")
    def text_property(node, **kwargs):
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    @tree_separator_after()
    @tree_operation(_("Image properties"), node_type="elem image", help="")
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

    @tree_conditional(lambda node: not node.lock and is_developer_mode())
    @tree_submenu(_("Passthrough"))
    @tree_operation(_("From Original"), node_type="elem image", help="")
    def image_convert_unmodified(node, **kwargs):
        node.replace_node(
            image=node.image,
            matrix=node.matrix,
            type="image raster",
        )

    @tree_conditional(lambda node: not node.lock and is_developer_mode())
    @tree_submenu(_("Passthrough"))
    @tree_operation(_("From Modified"), node_type="elem image", help="")
    def image_convert_unmodified_2(node, **kwargs):
        node.replace_node(
            image=node.active_image,
            matrix=node.active_matrix,
            type="image raster",
        )

    @tree_conditional(lambda node: not node.lock and is_developer_mode())
    @tree_operation(_("Unlock Modifications"), node_type="image raster", help="")
    def image_convert_modifier(node, **kwargs):
        node.replace_node(
            image=node.image,
            matrix=node.matrix,
            type="elem image",
        )

    @tree_operation(_("Remove effect"), node_type=effect_nodes, help="")
    def remove_effect(node, **kwargs):
        childs = [e for e in node._children]
        for e in childs:
            e._parent = None  # Otherwise add_node will fail below
            node.parent.add_node(e)
        node._children.clear()
        node.remove_node()
        self.signal("rebuild_tree")

    @tree_conditional(lambda node: is_hatched(node))
    @tree_operation(_("Remove effect"), node_type=elem_nodes, help="")
    def unhatch_elements(node, **kwargs):
        for e in list(self.elems(emphasized=True)):
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
                nparent.remove_node()
            else:
                nparent.altered()
        self.signal("rebuild_tree")

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_operation(_("Ungroup elements"), node_type=("group", "file"), help="")
    def ungroup_elements(node, **kwargs):
        to_treat = []
        for gnode in self.flat(selected=True, cascade=False, types=("group", "file")):
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
                gnode.insert_sibling(n)
            gnode.remove_node()  # Removing group/file node.

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_operation(
        _("Simplify group"),
        node_type=("group", "file"),
        help=_("Unlevel groups if they just contain another group"),
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

        res = straighten(node)
        if res > 0:
            self.signal("rebuild_tree")

    @tree_conditional(lambda node: len(list(self.elems(emphasized=True))) > 0)
    @tree_operation(
        _("Elements in scene..."), node_type=elem_nodes, help="", enable=False
    )
    def element_label(node, **kwargs):
        return

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_conditional(lambda node: len(list(self.elems(emphasized=True))) > 1)
    @tree_operation(_("Group elements"), node_type=elem_nodes, help="")
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
        parent_node = minimal_parent(data)
        group_node = parent_node.add(type="group", label="Group")
        for e in data:
            group_node.append_child(e)

    @tree_conditional(
        lambda cond: len(list(self.flat(selected=True, cascade=False, types=op_nodes)))
        >= 1
    )
    @tree_operation(
        _("Remove all items from operation"), node_type=op_parent_nodes, help=""
    )
    def clear_all_op_entries(node, **kwargs):
        with self.static("clear_all_op"):
            data = list()
            for item in list(self.flat(selected=True, cascade=False, types=op_nodes)):
                data.append(item)
            for item in data:
                item.remove_all_children()

    @tree_conditional(lambda node: hasattr(node, "output"))
    @tree_operation(_("Enable/Disable ops"), node_type=op_nodes, help="")
    def toggle_n_operations(node, **kwargs):
        changes = []
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
    @tree_operation(_("Show/Hide contained elements"), node_type=op_nodes, help="")
    def toggle_op_elem_visibility(node, **kwargs):
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
    )
    def ops_enable_similar(node, **kwargs):
        oplist = []
        for n in self.ops():
            if n.type == node.type:
                oplist.append(n)
        set_op_output(oplist, True)

    @tree_conditional(lambda node: hasattr(node, "output"))
    @tree_separator_after()
    @tree_operation(
        _("Disable similar"),
        node_type=op_nodes,
        help=_("Disable all operations of this type"),
    )
    def ops_disable_similar(node, **kwargs):
        oplist = []
        for n in self.ops():
            if n.type == node.type:
                oplist.append(n)
        set_op_output(oplist, False)

    @tree_submenu(_("Convert operation"))
    @tree_operation(_("Convert to Image"), node_type=op_parent_nodes, help="")
    def convert_operation_image(node, **kwargs):
        for n in list(self.ops(selected=True)):
            new_settings = dict(n.settings)
            new_settings["type"] = "op image"
            n.replace_node(keep_children=True, **new_settings)
        self.signal("rebuild_tree")

    @tree_submenu(_("Convert operation"))
    @tree_operation(_("Convert to Raster"), node_type=op_parent_nodes, help="")
    def convert_operation_raster(node, **kwargs):
        for n in list(self.ops(selected=True)):
            new_settings = dict(n.settings)
            new_settings["type"] = "op raster"
            n.replace_node(keep_children=True, **new_settings)
        self.signal("rebuild_tree")

    @tree_submenu(_("Convert operation"))
    @tree_operation(_("Convert to Engrave"), node_type=op_parent_nodes, help="")
    def convert_operation_engrave(node, **kwargs):
        for n in list(self.ops(selected=True)):
            new_settings = dict(n.settings)
            new_settings["type"] = "op engrave"
            n.replace_node(keep_children=True, **new_settings)
        self.signal("rebuild_tree")

    @tree_submenu(_("Convert operation"))
    @tree_operation(_("Convert to Cut"), node_type=op_parent_nodes, help="")
    def convert_operation_cut(node, **kwargs):
        for n in list(self.ops(selected=True)):
            new_settings = dict(n.settings)
            new_settings["type"] = "op cut"
            n.replace_node(keep_children=True, **new_settings)
        self.signal("rebuild_tree")

    @tree_submenu(_("Convert operation"))
    @tree_operation(_("Convert to Dots"), node_type=op_parent_nodes, help="")
    def convert_operation_dots(node, **kwargs):
        for n in list(self.ops(selected=True)):
            new_settings = dict(n.settings)
            new_settings["type"] = "op dots"
            n.replace_node(keep_children=True, **new_settings)
        self.signal("rebuild_tree")

    @tree_submenu(_("RasterWizard"))
    @tree_operation(_("Set to None"), node_type="elem image", help="")
    def image_rasterwizard_apply_none(node, **kwargs):
        firstnode = None
        for e in list(self.elems(emphasized=True)):
            if e.type != "elem image":
                continue
            e.operations = []
            e.update(None)
            if firstnode is None:
                firstnode = e
        self.signal("refresh_scene", "Scene")
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None and firstnode is not None:
            activate(firstnode)
            self.signal("propupdate", firstnode)

    @tree_submenu(_("RasterWizard"))
    @tree_values("script", values=list(self.match("raster_script", suffix=True)))
    @tree_operation(_("Apply: {script}"), node_type="elem image", help="")
    def image_rasterwizard_apply(node, script=None, **kwargs):
        raster_script = self.lookup(f"raster_script/{script}")
        firstnode = None
        for e in list(self.elems(emphasized=True)):
            if e.type != "elem image":
                continue
            e.operations = raster_script
            e.update(None)
            if firstnode is None:
                firstnode = e
        self.signal("refresh_scene", "Scene")
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)
            self.signal("propupdate", node)

    @tree_submenu(_("Convert to Path"))
    @tree_operation(_("Horizontal"), node_type="elem image", help="")
    def image_convert_to_path_horizontal(node, **kwargs):
        image, box = node.as_image()
        m = Matrix(node.active_matrix)
        n = node.replace_node(
            type="elem path",
            geometry=Geomstr.image(image, vertical=False),
            stroke=self.default_stroke,
            stroke_width=self.default_strokewidth,
            matrix=m,
        )
        if self.classify_new:
            self.classify([n])

    @tree_submenu(_("Convert to Path"))
    @tree_operation(_("Vertical"), node_type="elem image", help="")
    def image_convert_to_path_vertical(node, **kwargs):
        image, box = node.as_image()
        m = Matrix(node.active_matrix)
        n = node.replace_node(
            type="elem path",
            geometry=Geomstr.image(image, vertical=True),
            stroke=self.default_stroke,
            stroke_width=self.default_strokewidth,
            matrix=m,
        )
        if self.classify_new:
            self.classify([n])

    def radio_match_speed(node, speed=0, **kwargs):
        return node.speed == float(speed)

    @tree_submenu(_("Speed for Raster-Operation"))
    @tree_radio(radio_match_speed)
    @tree_values("speed", (5, 10, 50, 75, 100, 150, 200, 250, 300, 350, 400, 450, 500))
    @tree_operation(_("{speed}mm/s"), node_type=("op raster", "op image"), help="")
    def set_speed_raster(node, speed=150, **kwargs):
        data = list()
        for n in list(self.ops(selected=True)):
            if n.type not in ("op raster", "op image"):
                continue
            n.speed = float(speed)
            data.append(n)
        self.signal("element_property_reload", data)

    @tree_submenu(_("Speed for Vector-Operation"))
    @tree_radio(radio_match_speed)
    @tree_values("speed", (2, 3, 4, 5, 6, 7, 10, 15, 20, 25, 30, 35, 40, 50))
    @tree_operation(
        _("{speed}mm/s"),
        node_type=("op cut", "op engrave"),
        help="",
    )
    def set_speed_vector_cut(node, speed=20, **kwargs):
        data = list()
        for n in list(self.ops(selected=True)):
            if n.type not in ("op cut", "op engrave"):
                continue
            n.speed = float(speed)
            data.append(n)
        self.signal("element_property_reload", data)

    def radio_match_power(node, power=0, **kwargs):
        return node.power == float(power)

    @tree_submenu(_("Power"))
    @tree_radio(radio_match_power)
    @tree_values("power", (100, 250, 333, 500, 667, 750, 1000))
    @tree_calc("power_10", lambda i: round(i / 10, 1))
    @tree_operation(
        _("{power}ppi ({power_10}%)"),
        node_type=("op cut", "op raster", "op image", "op engrave"),
        help="",
    )
    def set_power(node, power=1000, **kwargs):
        data = list()
        for n in list(self.ops(selected=True)):
            if not hasattr(n, "power"):
                continue
            n.power = float(power)
            data.append(n)
        if len(data) > 0:
            self.signal("element_property_reload", data)

    def radio_match(node, dpi=100, **kwargs):
        try:
            return round(node.dpi, 0) == round(dpi, 0)
        except ValueError:
            return False

    @tree_submenu(_("DPI"))
    @tree_radio(radio_match)
    @tree_values("dpi", (100, 200, 250, 333.3, 500, 666.6, 750, 1000))
    @tree_operation(
        _("DPI {dpi}"),
        node_type=("op raster", "elem image"),
        help=_("Change dpi values"),
    )
    def set_step_n(node, dpi=1, **kwargs):
        data = list()
        for n in list(self.ops(selected=True)):
            if not hasattr(n, "dpi"):
                continue
            n.dpi = dpi
            data.append(n)
        for n in list(self.elems(emphasized=True)):
            if n.type == "elem image":
                n.dpi = dpi
                n.update(None)
                data.append(n)
        if len(data) > 0:
            self.signal("refresh_scene", "Scene")
            self.signal("element_property_reload", data)

    def radio_match_passes(node, passvalue=1, **kwargs):
        return (node.passes_custom and passvalue == node.passes) or (
            not node.passes_custom and passvalue == 1
        )

    @tree_submenu(_("Set operation passes"))
    @tree_radio(radio_match_passes)
    @tree_iterate("passvalue", 1, 10)
    @tree_operation(_("Passes {passvalue}"), node_type=op_parent_nodes, help="")
    def set_n_passes(node, passvalue=1, **kwargs):
        data = list()
        for n in list(self.ops(selected=True)):
            if not hasattr(n, "passes"):
                continue
            n.passes = passvalue
            n.passes_custom = passvalue != 1
            data.append(n)
        if len(data) > 0:
            self.signal("element_property_reload", data)

    def radio_match_loops(node, loopvalue=1, **kwargs):
        return node.loops == loopvalue

    @tree_submenu(_("Set placement loops"))
    @tree_radio(radio_match_loops)
    @tree_iterate("loopvalue", 1, 10)
    @tree_operation(_("Loops {loopvalue}"), node_type="place point", help="")
    def set_n_loops(node, loopvalue=1, **kwargs):
        data = list()
        for n in list(self.ops(selected=True)):
            if not hasattr(n, "loops"):
                continue
            n.loops = loopvalue
            data.append(n)
        if len(data) > 0:
            self.signal("element_property_update", data)
            self.signal("refresh_scene", "Scene")

    # @tree_submenu(_("Layout"))
    # @tree_prompt("dx", _("Distance between placements?"))
    # @tree_prompt(
    #     "nx",
    #     _(
    #         "How many placements on the X-Axis?\n(0 = as many as fit on the bed)"
    #     ),
    # )
    # @tree_operation(
    #     _("Create placements horizontally"), node_type="place point", help=""
    # )
    # def copies_horizontally(node, dx, nx, pos=None, **kwargs):
    #     self(f"placement_grid {nx} {dx} 1 0\n")

    # @tree_submenu(_("Layout"))
    # @tree_prompt("dy", _("Distance between placements?"))
    # @tree_prompt(
    #     "ny",
    #     _(
    #         "How many placements on the Y-Axis?\n(0 = as many as fit on the bed)"
    #     ),
    # )
    # @tree_operation(_("Create placements vertically"), node_type="place point", help="")
    # def copies_vertically(node, dy, ny, pos=None, **kwargs):
    #     self(f"placement_grid 1 0 {ny} {dy}\n")

    # @tree_submenu(_("Layout"))
    # @tree_prompt("dx", _("Horizontal distance between placements?"))
    # @tree_prompt(
    #     "nx",
    #     _(
    #         "How many placements on the X-Axis?\n(0 = as many as fit on the bed)"
    #     ),
    # )
    # @tree_prompt("dy", _("Vertical distance between placements?"))
    # @tree_prompt(
    #     "ny",
    #     _(
    #         "How many placements on the Y-Axis?\n(0 = as many as fit on the bed)"
    #     ),
    # )
    # @tree_operation(
    #     _("Create grid of placements"), node_type="place point", help=""
    # )
    # def copies_grid(node, dx, nx, dy, ny, pos=None, **kwargs):
    #     self(f"placement_grid {nx} {dx} {ny} {dy}\n")

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

    @tree_submenu(_("Burn Direction"))
    @tree_radio(radio_match_direction)
    @tree_values("raster_direction", values=get_direction_values())
    @tree_operation(
        "{raster_direction}",
        node_type=("op raster", "op image"),
        help="",
    )
    def set_direction(node, raster_direction="", **kwargs):
        values = get_direction_values()
        for idx, key in enumerate(values):
            if key == raster_direction:
                data = list()
                for n in list(self.ops(selected=True)):
                    if n.type not in ("op raster", "op image"):
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
        node_type=("op raster", "op image"),
        help="",
    )
    def set_swing(node, raster_swing="", **kwargs):
        values = get_swing_values()
        for idx, key in enumerate(values):
            if key == raster_swing:
                data = list()
                for n in list(self.ops(selected=True)):
                    if n.type not in ("op raster", "op image"):
                        continue
                    n.bidirectional = bool(idx)
                    data.append(n)
                self.signal("element_property_reload", data)
                break

    # @tree_separator_before()
    # @tree_operation(
    #     _("Execute operation(s)"),
    #     node_type=op_nodes,
    #     help=_("Execute Job for the selected operation(s)."),
    # )
    # def execute_job(node, **kwargs):
    #     self.set_node_emphasis(node, True)
    #     self("plan0 clear copy-selected\n")
    #     self("window open ExecuteJob 0\n")

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

    @tree_separator_after()
    @tree_conditional(lambda cond: selected_active_ops() > 0)
    @tree_operation(
        _("Simulate operation(s)"),
        node_type=op_nodes,
        help=_("Run simulation for the selected operation(s)"),
    )
    def compile_and_simulate(node, **kwargs):
        self.set_node_emphasis(node, True)
        self("plan0 copy-selected preprocess validate blob preopt optimize\n")
        self("window open Simulation 0 1 1\n")  # Plan Name, Auto-Clear, Optimise

    # ==========
    # General menu-entries for operation branch
    # ==========

    @tree_operation(_("Global Settings"), node_type="branch ops", help="")
    def op_prop(node, **kwargs):
        activate = self.kernel.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    @tree_operation(_("Clear all"), node_type="branch ops", help="")
    def clear_all(node, **kwargs):
        self("operation* delete\n")

    @tree_operation(
        _("Clear unused"),
        node_type="branch ops",
        help=_("Clear operations without children"),
    )
    def clear_unused(node, **kwargs):
        to_delete = []
        for op in self.ops():
            # print (f"{op.type}, refs={len(op._references)}, children={len(op._children)}")
            if len(op._children) == 0 and not op.type == "blob":
                to_delete.append(op)
        if len(to_delete) > 0:
            with self.static("clear_unused"):
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
        help="",
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
        help="",
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

    @tree_separator_before()
    @tree_operation(
        _("Enable all operations"),
        node_type="branch ops",
        help=_("Enable all operations"),
    )
    def ops_enable_all(node, **kwargs):
        set_op_output(list(self.ops()), True)

    @tree_operation(
        _("Disable all operations"),
        node_type="branch ops",
        help=_("Disable all operations"),
    )
    def ops_disable_all(node, **kwargs):
        set_op_output(list(self.ops()), False)

    @tree_separator_after()
    @tree_operation(
        _("Toggle all operations"),
        node_type="branch ops",
        help=_("Toggle enabled-status of all operations"),
    )
    def ops_toggle_all(node, **kwargs):
        set_op_output(list(self.ops()), None)

    # ==========
    # General menu-entries for elem branch
    # ==========

    @tree_operation(_("Clear all"), node_type="branch elems", help="")
    def clear_all_elems(node, **kwargs):
        # self("element* delete\n")
        with self.static("clear_elems"):
            self.elem_branch.remove_all_children()

    # ==========
    # General menu-entries for regmark branch
    # ==========

    @tree_operation(_("Clear all"), node_type="branch reg", help="")
    def clear_all_regmarks(node, **kwargs):
        with self.static("clear_regmarks"):
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
        help="",
    )
    def remove_multi_references(node, **kwargs):
        nodes = list(self.flat(selected=True, cascade=False, types="reference"))
        for node in nodes:
            if node.parent is not None:  # May have already removed.
                node.remove_node()
        self.set_emphasis(None)
        self.signal("refresh_tree")

    # @tree_conditional(
    #     lambda cond: len(
    #         list(self.flat(selected=True, cascade=False, types=operate_nodes))
    #     )
    #     if len(list(self.flat(selected=True, cascade=False, types=operate_nodes)))
    #     > 0
    #     else len(
    #         list(self.flat(selected=True, cascade=False, types=elem_group_nodes))
    #     )
    #     > 1
    # )
    # @tree_calc(
    #     "ecount",
    #     lambda i: len(
    #         list(self.flat(selected=True, cascade=False, types=operate_nodes))
    #     )
    #     if len(list(self.flat(selected=True, cascade=False, types=operate_nodes)))
    #     > 0
    #     else len(
    #         list(self.flat(selected=True, cascade=False, types=elem_group_nodes))
    #     ),
    # )
    # @tree_calc(
    #     "rcount",
    #     lambda i: len(
    #         list(self.flat(selected=True, cascade=False, types=("reference")))
    #     ),
    # )
    # @tree_calc(
    #     "eloc",
    #     lambda s: "operations"
    #     if len(list(self.flat(selected=True, cascade=False, types=operate_nodes)))
    #     > 0
    #     else "element-list",
    # )
    # @tree_operation(
    #     _("Delete %s selected items from %s (Ref=%s)") % ("{ecount}", "{eloc}", "{rcount}"),
    #     node_type=non_structural_nodes,
    #     help="",
    # )
    # def remove_multi_nodes(node, **kwargs):
    #     if (
    #         len(list(self.flat(selected=True, cascade=False, types=operate_nodes)))
    #         > 0
    #     ):
    #         types = operate_nodes
    #     else:
    #         types = elem_group_nodes
    #     nodes = list(self.flat(selected=True, cascade=False, types=types))
    #     for node in nodes:
    #         # If we are selecting an operation / an element within an operation, then it
    #         # also selects/emphasizes the contained elements in the elements branch...
    #         # So both will be deleted...
    #         # To circumvent this, we inquire once more the selected status...
    #         if node.selected:
    #             if node.parent is not None:  # May have already removed.
    #                 node.remove_node()
    #     self.set_emphasis(None)

    # ==========
    # REMOVE SINGLE (Tree Selected - ELEMENT)
    # ==========

    # @tree_conditional(lambda node: node.can_remove)
    # @tree_conditional(
    #     lambda cond: len(
    #         list(self.flat(selected=True, cascade=False, types=elem_nodes))
    #     )
    #     == 1
    # )
    # @tree_operation(
    #     _("Delete element '{name}' fully"),
    #     node_type=elem_nodes,
    #     help="",
    # )
    # def remove_type_elem(node, **kwargs):
    #     if hasattr(node, "can_remove") and not node.can_remove:
    #         pass
    #     else:
    #         self.set_emphasis(None)
    #         node.remove_node()

    @tree_conditional(
        lambda cond: len(list(self.flat(selected=True, cascade=False, types=op_nodes)))
        == 1
    )
    @tree_operation(
        _("Delete operation '{name}' fully"),
        node_type=op_nodes,
        help="",
    )
    def remove_type_op(node, **kwargs):
        self.set_emphasis(None)
        node.remove_node()
        self.signal("operation_removed")

    @tree_conditional(
        lambda cond: len(list(self.flat(selected=True, cascade=False, types="blob")))
        == 1
    )
    @tree_operation(
        _("Delete blob '{name}' fully"),
        node_type="blob",
        help="",
    )
    def remove_type_blob(node, **kwargs):
        self.set_emphasis(None)
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
        help="",
    )
    def remove_type_op_multiple(node, **kwargs):
        for op in list(self.flat(selected=True, cascade=False, types=op_nodes)):
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
        help="",
    )
    def remove_type_grp(node, **kwargs):
        self.set_emphasis(None)
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
        help="",
    )
    def remove_type_file(node, **kwargs):
        self.set_emphasis(None)
        node.remove_node()

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_operation(
        _("Remove transparent objects"),
        node_type=("group", "file"),
        help=_("Remove all elements that neither have a border nor a fill color"),
    )
    def remove_transparent(node, **kwargs):
        res = 0
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
                enode.remove_node()

        if res > 0:
            self.signal("rebuild_tree")

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
        help="",
    )
    def remove_n_ops(node, **kwargs):
        self("operation delete\n")

    @tree_operation(
        _("Select all elements of same type"),
        node_type=elem_nodes,
        help=_("Select all elements in scene, that have the same type as this node"),
    )
    def select_similar(node, **kwargs):
        ntype = node.type
        changes = False
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
        help="",
    )
    def remove_n_elements(node, **kwargs):
        self("element delete\n")

    @tree_operation(
        _("Become reference object"),
        node_type=elem_nodes,
        help="",
    )
    def make_node_reference(node, **kwargs):
        self.signal("make_reference", node)

    @tree_conditional(
        lambda node: node.closed and len(list(node.geometry.as_points())) >= 3
    )
    @tree_operation(
        _("Make Polygon regular"),
        node_type="elem polyline",
        help="",
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
            d2p.parse(node.data_type, node.data, self)
        return True

    @tree_conditional_try(
        lambda node: kernel.lookup(f"spoolerjob/{node.data_type}") is not None
    )
    @tree_operation(
        _("Execute Blob"),
        node_type="blob",
        help=_("Run the given blob on the current device"),
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
        help="",
    )
    def blob2cut(node, **kwargs):
        node.replace_node(node.as_cutobjects(), type="cutcode")

    @tree_operation(
        _("Convert to Path"),
        node_type="cutcode",
        help="",
    )
    def cutcode2pathcut(node, **kwargs):
        cutcode = node.cutcode
        if cutcode is None:
            return
        elements = list(cutcode.as_elements())
        n = None
        for element in elements:
            n = self.elem_branch.add(type="elem path", path=element)
        node.remove_node()
        if n is not None:
            n.focus()

    @tree_submenu(_("Clone reference"))
    @tree_operation(_("Make 1 copy"), node_type=("reference",), help="")
    def clone_single_element_op(node, **kwargs):
        clone_element_op(node, copies=1, **kwargs)

    @tree_submenu(_("Clone reference"))
    @tree_iterate("copies", 2, 10)
    @tree_operation(_("Make {copies} copies"), node_type=("reference",), help="")
    def clone_element_op(node, copies=1, **kwargs):
        with self.static("clone_elem_op"):
            nodes = list(self.flat(selected=True, cascade=False, types="reference"))
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
    )
    def reverse_layer_order(node, **kwargs):
        node.reverse()
        self.signal("refresh_tree", list(self.flat(types="reference")))

    @tree_submenu(_("Classification"))
    @tree_operation(
        _("Generate operations if needed"),
        node_type=("branch ops", "branch elems"),
        help="",
        enable=False,
    )
    def do_classification_comment_1(node, **kwargs):
        return

    @tree_submenu(_("Classification"))
    @tree_operation(
        _("Refresh classification for all"),
        node_type=("branch ops", "branch elems"),
        help=_("Reclassify elements and create operations if necessary"),
    )
    def refresh_classification_for_all_std(node, **kwargs):
        previous = self.classify_autogenerate
        self.classify_autogenerate = True
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
    )
    def do_classification_for_unassigned_std(node, **kwargs):
        previous = self.classify_autogenerate
        self.classify_autogenerate = True
        target_list = list(self.unassigned_elements())
        self.classify(target_list)
        self.classify_autogenerate = previous
        self.signal("refresh_tree", list(self.flat(types="reference")))

    @tree_submenu(_("Classification"))
    @tree_separator_before()
    @tree_operation(
        _("Use only existing operations"),
        node_type=("branch ops", "branch elems"),
        help="",
        enable=False,
    )
    def do_classification_comment_2(node, **kwargs):
        return

    @tree_submenu(_("Classification"))
    @tree_operation(
        _("Refresh classification for all"),
        node_type=("branch ops", "branch elems"),
        help=_("Reclassify all elements and use only existing operations"),
    )
    def refresh_classification_for_all_existing_only(node, **kwargs):
        previous = self.classify_autogenerate
        self.classify_autogenerate = False
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
    )
    def do_classification_for_unassigned_existing_only(node, **kwargs):
        previous = self.classify_autogenerate
        self.classify_autogenerate = False
        target_list = list(self.unassigned_elements())
        self.classify(target_list)
        self.classify_autogenerate = previous
        self.signal("refresh_tree", list(self.flat(types="reference")))

    @tree_submenu(_("Classification"))
    @tree_separator_before()
    @tree_operation(
        _("Clear all assignments"),
        node_type=("branch ops", "branch elems"),
        help="",
    )
    def do_classification_clear(node, **kwargs):
        self.remove_elements_from_operations(list(self.elems()))
        self.signal("refresh_tree")

    @tree_conditional(lambda cond: self.have_unassigned_elements())
    @tree_operation(
        _("Select unassigned elements"),
        node_type=("branch ops", "branch elems"),
        help=_("Select all elements that won't be burned"),
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

    # materials = [
    #     _("Wood"),
    #     _("Acrylic"),
    #     _("Foam"),
    #     _("Leather"),
    #     _("Cardboard"),
    #     _("Cork"),
    #     _("Textiles"),
    #     _("Paper"),
    #     _("Save-1"),
    #     _("Save-2"),
    #     _("Save-3"),
    # ]

    # def union_materials_saved():
    #     union = [
    #         d
    #         for d in self.op_data.section_set()
    #         if d not in materials and d != "previous"
    #     ]
    #     union.extend(materials)
    #     return union

    # def difference_materials_saved():
    #     secs = self.op_data.section_set()
    #     difference = [m for m in materials if m not in secs]
    #     return difference

    @tree_separator_before()
    @tree_operation(
        _("Material Manager"),
        node_type="branch ops",
        help=_("Open the Material Manager"),
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

    @tree_separator_after()
    @tree_submenu(_("Load"))
    @tree_values("opname", values=material_ids)
    @tree_submenu_list(material_menus)
    @tree_calc("material", lambda opname: material_name(opname))
    @tree_operation("{material}", node_type="branch ops", help="")
    def load_ops(node, opname, **kwargs):
        self(f"material load {opname}\n")

    # @tree_separator_before()
    # @tree_submenu(_("Load"))
    # @tree_operation(_("Minimal"), node_type="branch ops", help=_("Load a minimal set of operations"))
    # def default_classifications(node, **kwargs):
    #     self.load_default(performclassify=True)

    # @tree_submenu(_("Load"))
    # @tree_operation(_("Basic"), node_type="branch ops", help=_("Load a basic set of operation"))
    # def basic_classifications(node, **kwargs):
    #     self.load_default2(performclassify=True)

    # @tree_submenu(_("Save"))
    # @tree_values("opname", values=self.op_data.section_set)
    # @tree_calc("material", lambda opname: material_name(opname) )
    # @tree_operation("{material}", node_type="branch ops", help="")
    # def save_materials(node, opname="saved", **kwargs):
    #     self(f"material save {opname}\n")

    # @tree_separator_before()
    # @tree_submenu(_("Save"))
    # @tree_prompt("opname", _("Name to store current operations under?"))
    # @tree_operation(_("New"), node_type="branch ops", help="")
    # def save_material_custom(node, opname, **kwargs):
    #     self(f"material save {opname.replace(' ', '_')}\n")

    # @tree_submenu(_("Delete"))
    # @tree_values("opname", values=self.op_data.section_set)
    # @tree_operation("{opname}", node_type="branch ops", help="")
    # def remove_ops(node, opname="saved", **kwargs):
    #     self(f"material delete {opname}\n")

    @tree_separator_before()
    @tree_submenu(_("Append operation"))
    @tree_operation(_("Append Image"), node_type="branch ops", help="")
    def append_operation_image(node, pos=None, **kwargs):
        self.op_branch.add("op image", pos=pos)
        self.signal("updateop_tree")

    @tree_submenu(_("Append operation"))
    @tree_operation(_("Append Raster"), node_type="branch ops", help="")
    def append_operation_raster(node, pos=None, **kwargs):
        self.op_branch.add("op raster", pos=pos)
        self.signal("updateop_tree")

    @tree_submenu(_("Append operation"))
    @tree_operation(_("Append Engrave"), node_type="branch ops", help="")
    def append_operation_engrave(node, pos=None, **kwargs):
        self.op_branch.add("op engrave", pos=pos)
        self.signal("updateop_tree")

    @tree_submenu(_("Append operation"))
    @tree_operation(_("Append Cut"), node_type="branch ops", help="")
    def append_operation_cut(node, pos=None, **kwargs):
        self.op_branch.add("op cut", pos=pos)
        self.signal("updateop_tree")

    @tree_submenu(_("Append operation"))
    @tree_operation(_("Append Hatch"), node_type="branch ops", help="")
    def append_operation_hatch(node, pos=None, **kwargs):
        b = self.op_branch.add("op engrave", pos=pos)
        b.add("effect hatch")
        self.signal("updateop_tree")

    @tree_submenu(_("Append operation"))
    @tree_operation(_("Append Dots"), node_type="branch ops", help="")
    def append_operation_dots(node, pos=None, **kwargs):
        self.op_branch.add("op dots", pos=pos)
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(_("Append Home"), node_type="branch ops", help="")
    def append_operation_home(node, pos=None, **kwargs):
        self.op_branch.add(type="util home", pos=pos)
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(_("Append Return to Origin"), node_type="branch ops", help="")
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
    )
    def append_operation_goto_location(node, y, x, pos=None, **kwargs):
        self.op_branch.add(
            type="util goto",
            pos=pos,
            x=x,
            y=y,
        )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(_("Append Beep"), node_type="branch ops", help="")
    def append_operation_beep(node, pos=None, **kwargs):
        self.op_branch.add(
            type="util console",
            pos=pos,
            command="beep",
        )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(_("Append Interrupt"), node_type="branch ops", help="")
    def append_operation_interrupt(node, pos=None, **kwargs):
        self.op_branch.add(
            type="util console",
            pos=pos,
            command='interrupt "Spooling was interrupted"',
        )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_prompt("wait_time", _("Wait for how long (in seconds)?"), data_type=float)
    @tree_operation(_("Append Wait"), node_type="branch ops", help="")
    def append_operation_wait(node, wait_time, pos=None, **kwargs):
        self.op_branch.add(
            type="util wait",
            pos=pos,
            wait=wait_time,
        )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(_("Append Output"), node_type="branch ops", help="")
    def append_operation_output(node, pos=None, **kwargs):
        self.op_branch.add(
            type="util output",
            pos=pos,
            output_mask=0,
            output_value=0,
            output_message=None,
        )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(_("Append Input"), node_type="branch ops", help="")
    def append_operation_input(node, pos=None, **kwargs):
        self.op_branch.add(
            type="util input",
            pos=pos,
            input_mask=0,
            input_value=0,
            input_message=None,
        )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(_("Append Home/Beep/Interrupt"), node_type="branch ops", help="")
    def append_operation_home_beep_interrupt(node, **kwargs):
        append_operation_home(node, **kwargs)
        append_operation_beep(node, **kwargs)
        append_operation_interrupt(node, **kwargs)
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(_("Append Origin/Beep/Interrupt"), node_type="branch ops", help="")
    def append_operation_origin_beep_interrupt(node, **kwargs):
        append_operation_goto(node, **kwargs)
        append_operation_beep(node, **kwargs)
        append_operation_interrupt(node, **kwargs)
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_operation(_("Append Shutdown"), node_type="branch ops", help="")
    def append_operation_shutdown(node, pos=None, **kwargs):
        self.op_branch.add(
            type="util console",
            pos=pos,
            command="quit",
        )
        self.signal("updateop_tree")

    @tree_submenu(_("Append special operation(s)"))
    @tree_prompt("opname", _("Console command to append to operations?"))
    @tree_operation(_("Append Console"), node_type="branch ops", help="")
    def append_operation_custom(node, opname, pos=None, **kwargs):
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
    )
    def append_absolute_placement(node, y, x, pos=None, **kwargs):
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
    )
    def append_relative_placement(node, **kwargs):
        self.op_branch.add(
            type="place current",
        )
        self.signal("updateop_tree")

    @tree_operation(
        _("Remove all assignments from operations"),
        node_type="branch elems",
        help=_("Any existing assignment of elements to operations will be removed"),
    )
    def remove_all_assignments(node, **kwargs):
        with self.static("remove_all_assign"):
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

    @tree_submenu(_("Apply special effect"))
    @tree_operation(_("Append Line-fill 0.1mm"), node_type=hatchable_elems, help="")
    def append_element_effect_eulerian(node, pos=None, **kwargs):
        group_node = node.parent.add(
            type="effect hatch",
            hatch_type="scanline",
            hatch_distance="0.1mm",
            hatch_angle="0deg",
            pos=pos,
        )
        for e in list(self.elems(emphasized=True)):
            group_node.append_child(e)
        if self.classify_new:
            self.classify([group_node])

        self.signal("updateelem_tree")

    @tree_submenu(_("Apply special effect"))
    @tree_operation(
        _("Append diagonal Line-fill 0.1mm"), node_type=hatchable_elems, help=""
    )
    def append_element_effect_eulerian_45(node, pos=None, **kwargs):
        group_node = node.parent.add(
            type="effect hatch",
            hatch_type="scanline",  # scanline / eulerian
            hatch_distance="0.1mm",
            hatch_angle="45deg",
            pos=pos,
        )
        for e in list(self.elems(emphasized=True)):
            group_node.append_child(e)
        if self.classify_new:
            self.classify([group_node])

        self.signal("updateelem_tree")

    @tree_submenu(_("Apply special effect"))
    @tree_operation(_("Append Line-Fill 1mm"), node_type=hatchable_elems, help="")
    def append_element_effect_line(node, pos=None, **kwargs):
        group_node = node.parent.add(
            type="effect hatch",
            hatch_type="scanline",
            hatch_distance="1mm",
            hatch_angle="0deg",
            pos=pos,
        )
        for e in list(self.elems(emphasized=True)):
            group_node.append_child(e)
        if self.classify_new:
            self.classify([group_node])

        self.signal("updateelem_tree")

    @tree_submenu(_("Apply special effect"))
    @tree_operation(
        _("Append diagonal Line-Fill 1mm"), node_type=hatchable_elems, help=""
    )
    def append_element_effect_line_45(node, pos=None, **kwargs):
        group_node = node.parent.add(
            type="effect hatch",
            hatch_type="scanline",
            hatch_distance="1mm",
            hatch_angle="45deg",
            pos=pos,
        )
        for e in list(self.elems(emphasized=True)):
            group_node.append_child(e)
        if self.classify_new:
            self.classify([group_node])

        self.signal("updateelem_tree")

    @tree_conditional(lambda node: is_developer_mode())
    @tree_submenu(_("Apply special effect"))
    @tree_operation(
        _("Append Warp").format(),
        node_type=hatchable_elems,
        help="",
    )
    def append_element_effect_warp(node, pos=None, **kwargs):
        group_node = node.parent.add(
            type="effect warp",
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
            type="Circle", radius="0.5mm", interval="0.05mm"
        ),
        node_type=wobbleable_elems,
        help="",
    )
    def append_element_effect_wobble_c05(node, pos=None, **kwargs):
        group_node = node.parent.add(
            type="effect wobble",
            wobble_type="circle",
            wobble_radius="0.5mm",
            wobble_interval="0.05mm",
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
            type="Circle", radius="1mm", interval="0.1mm"
        ),
        node_type=wobbleable_elems,
        help="",
    )
    def append_element_effect_wobble_c1(node, pos=None, **kwargs):
        group_node = node.parent.add(
            type="effect wobble",
            wobble_type="circle",
            wobble_radius="1mm",
            wobble_interval="0.1mm",
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
            type="Circle", radius="3mm", interval="0.1mm"
        ),
        node_type=wobbleable_elems,
        help="",
    )
    def append_element_effect_wobble_c3(node, pos=None, **kwargs):
        group_node = node.parent.add(
            type="effect wobble",
            wobble_type="circle_right",
            wobble_radius="3mm",
            wobble_interval="0.1mm",
            pos=pos,
        )
        for e in list(self.elems(emphasized=True)):
            group_node.append_child(e)
        if self.classify_new:
            self.classify([group_node])

        self.signal("updateelem_tree")

    @tree_submenu(_("Apply special effect"))
    @tree_operation(
        _("Append {type} {radius} @{interval}").format(
            type="Meander", radius="1mm", interval="1.25mm"
        ),
        node_type=wobbleable_elems,
        help="",
    )
    def append_element_effect_wobble_m1(node, pos=None, **kwargs):
        group_node = node.parent.add(
            type="effect wobble",
            wobble_type="meander_1",
            wobble_radius="1mm",
            wobble_interval="1.25mm",
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
    )
    def duplicate_operation(node, **kwargs):
        with self.static("duplicate_operation"):
            operations = self._tree.get(type="branch ops").children
            for op in self.ops(selected=True):
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
    @tree_submenu(_("Passes"))
    @tree_operation(
        _("Add 1 pass"),
        node_type=("op image", "op engrave", "op cut"),
        help="",
    )
    def add_1_pass(node, **kwargs):
        add_n_passes(node, copies=1, **kwargs)

    @tree_conditional(lambda node: node.count_children() > 1)
    @tree_submenu(_("Passes"))
    @tree_iterate("copies", 2, 10)
    @tree_operation(
        _("Add {copies} passes"),
        node_type=("op image", "op engrave", "op cut"),
        help="",
    )
    def add_n_passes(node, copies=1, **kwargs):
        add_nodes = list(node.children)

        removed = False
        for i in range(0, len(add_nodes)):
            for q in range(0, i):
                if add_nodes[q] is add_nodes[i]:
                    add_nodes[i] = None
                    removed = True
        if removed:
            add_nodes = [c for c in add_nodes if c is not None]
        add_nodes *= copies
        for n in add_nodes:
            node.add_reference(n.node)
        self.signal("rebuild_tree")

    @tree_conditional(lambda node: node.count_children() > 1)
    @tree_submenu(_("Duplicate element(s)"))
    @tree_operation(
        _("Duplicate elements 1 time"),
        node_type=("op image", "op engrave", "op cut"),
        help="",
    )
    def dup_1_copy(node, **kwargs):
        dup_n_copies(node, copies=1, **kwargs)

    @tree_conditional(lambda node: node.count_children() > 1)
    @tree_submenu(_("Duplicate element(s)"))
    @tree_iterate("copies", 2, 10)
    @tree_operation(
        _("Duplicate elements {copies} times"),
        node_type=("op image", "op engrave", "op cut"),
        help="",
    )
    def dup_n_copies(node, copies=1, **kwargs):
        # Code in series.
        # add_nodes = list(node.children)
        # add_nodes *= copies
        # for n in add_nodes:
        #     node.add_reference(n.node)

        # Code in parallel.
        add_nodes = list(node.children)
        for i in range(len(add_nodes) - 1, -1, -1):
            n = add_nodes[i]
            for k in range(copies):
                node.add_reference(n.node, pos=i)

        self.signal("refresh_tree")

    @tree_operation(
        _("Make raster image"),
        node_type=("op image", "op raster"),
        help=_("Create an image from the assigned elements."),
    )
    def make_raster_image(node, **kwargs):
        data = list(node.flat(types=elem_ref_nodes))
        if len(data) == 0:
            return
        try:
            bounds = Node.union_bounds(data, attr="paint_bounds")
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

        image = make_raster(
            data,
            bounds=bounds,
            width=new_width,
            height=new_height,
        )
        matrix = Matrix.scale(width / new_width, height / new_height)
        matrix.post_translate(bounds[0], bounds[1])

        image_node = ImageNode(image=image, matrix=matrix, dpi=node.dpi)
        self.elem_branch.add_node(image_node)
        node.add_reference(image_node)
        self.signal("refresh_scene", "Scene")

    def add_after_index(node=None):
        try:
            if node is None:
                node = list(self.ops(selected=True))[-1]
            operations = self._tree.get(type="branch ops").children
            return operations.index(node) + 1
        except (ValueError, IndexError):
            return None

    @tree_separator_before()
    @tree_submenu(_("Insert operation"))
    @tree_operation(_("Add Image"), node_type=op_nodes, help="")
    def add_operation_image(node, **kwargs):
        append_operation_image(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert operation"))
    @tree_operation(_("Add Raster"), node_type=op_nodes, help="")
    def add_operation_raster(node, **kwargs):
        append_operation_raster(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert operation"))
    @tree_operation(_("Add Engrave"), node_type=op_nodes, help="")
    def add_operation_engrave(node, **kwargs):
        append_operation_engrave(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert operation"))
    @tree_operation(_("Add Cut"), node_type=op_nodes, help="")
    def add_operation_cut(node, **kwargs):
        append_operation_cut(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert operation"))
    @tree_operation(_("Add Hatch"), node_type=op_nodes, help="")
    def add_operation_hatch(node, **kwargs):
        append_operation_hatch(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert operation"))
    @tree_operation(_("Add Dots"), node_type=op_nodes, help="")
    def add_operation_dots(node, **kwargs):
        append_operation_dots(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(_("Add Home"), node_type=op_nodes, help="")
    def add_operation_home(node, **kwargs):
        append_operation_home(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(_("Add Return to Origin"), node_type=op_nodes, help="")
    def add_operation_origin(node, **kwargs):
        append_operation_goto(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(_("Add Beep"), node_type=op_nodes, help="")
    def add_operation_beep(node, **kwargs):
        append_operation_beep(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(_("Add Interrupt"), node_type=op_nodes, help="")
    def add_operation_interrupt(node, **kwargs):
        append_operation_interrupt(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_prompt("wait_time", _("Wait for how long (in seconds)?"), data_type=float)
    @tree_operation(_("Add Wait"), node_type=op_nodes, help="")
    def add_operation_wait(node, wait_time, **kwargs):
        append_operation_wait(
            node, wait_time=wait_time, pos=add_after_index(node), **kwargs
        )

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(_("Add Output"), node_type=op_nodes, help="")
    def add_operation_output(node, **kwargs):
        append_operation_output(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(_("Add Input"), node_type=op_nodes, help="")
    def add_operation_input(node, **kwargs):
        append_operation_input(node, pos=add_after_index(node), **kwargs)

    @tree_submenu(_("Insert special operation(s)"))
    @tree_operation(_("Add Home/Beep/Interrupt"), node_type=op_nodes, help="")
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
    @tree_operation(_("Add Origin/Beep/Interrupt"), node_type=op_nodes, help="")
    def add_operation_origin_beep_interrupt(node, **kwargs):
        pos = add_after_index(node)
        append_operation_goto(node, pos=pos, **kwargs)
        if pos:
            pos += 1
        append_operation_beep(node, pos=pos, **kwargs)
        if pos:
            pos += 1
        append_operation_interrupt(node, pos=pos, **kwargs)

    @tree_operation(_("Reload '{name}'"), node_type="file", help="")
    def reload_file(node, **kwargs):
        filepath = node.filepath
        if not os.path.exists(filepath):
            self.signal(
                "warning",
                _("The file no longer exists!"),
                _("File does not exist."),
            )
            return
        node.remove_node()
        self.load(filepath)

    @tree_operation(
        _("Open containing folder: '{name}'"),
        node_type="file",
        help=_("Open this file working directory in the system's file manager"),
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
    @tree_operation("{op_assign}", node_type=elem_nodes, help="")
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

    @tree_separator_before()
    @tree_submenu(_("Assign Operation"))
    @tree_operation(
        _("Remove all assignments from operations"),
        node_type=elem_group_nodes,
        help=_("Any existing assignment of this element to operations will be removed"),
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

        with self.static("remove_assign"):
            for node in list(self.elems(emphasized=True)):
                rem_node(node)
        self.signal("refresh_tree")

    @tree_separator_before()
    @tree_submenu(_("Assign Operation"))
    @tree_check(exclusive_match)
    @tree_operation(
        _("Exclusive assignment"),
        node_type=elem_nodes,
        help=_(
            "An assignment will remove all other classifications of this element if checked"
        ),
    )
    def set_assign_option_exclusive(node, **kwargs):
        self.classify_inherit_exclusive = not self.classify_inherit_exclusive

    def stroke_match(node, **kwargs):
        return self.classify_inherit_stroke

    @tree_separator_before()
    @tree_submenu(_("Assign Operation"))
    @tree_check(stroke_match)
    @tree_operation(
        _("Inherit stroke and classify similar"),
        node_type=elem_nodes,
        help=_("Operation will inherit element stroke color"),
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
    )
    def set_assign_option_fill(node, **kwargs):
        self.classify_inherit_fill = not self.classify_inherit_fill
        # Poor man's radio
        if self.classify_inherit_fill:
            self.classify_inherit_stroke = False

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_submenu(_("Duplicate element(s)"))
    @tree_operation(_("Make 1 copy"), node_type=elem_group_nodes, help="")
    def duplicate_element_1(node, **kwargs):
        duplicate_element_n(node, copies=1, **kwargs)

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_submenu(_("Duplicate element(s)"))
    @tree_iterate("copies", 2, 10)
    @tree_operation(_("Make {copies} copies"), node_type=elem_group_nodes, help="")
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
                    if hasattr(e, optional):
                        setattr(copy_node, optional, getattr(orgnode, optional))
                had_optional = False
                options = []
                for prop in dir(e):
                    if prop.startswith("mk"):
                        options.append(prop)
                for optional in options:
                    if hasattr(e, optional):
                        setattr(copy_node, optional, getattr(orgnode, optional))
                        had_optional = True

                if self.copy_increases_wordlist_references and hasattr(orgnode, "text"):
                    copy_node.text = self.wordlist_delta(orgnode.text, delta_wordlist)
                elif self.copy_increases_wordlist_references and hasattr(e, "mktext"):
                    copy_node.mktext = self.wordlist_delta(e.mktext, delta_wordlist)
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

        copy_nodes = list()
        _dx = self.length_x("3mm")
        _dy = self.length_y("3mm")
        alldata = list(self.elems(emphasized=True))
        minimaldata = self.condense_elements(alldata, expand_at_end=False)
        for e in minimaldata:
            parent = e.parent
            copy_single_node(e, parent, copies, _dx, _dy)

        if self.classify_new:
            self.classify(copy_nodes)

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
        help=_("Adjusts the reference value for a wordlist, ie {name} to {name#+1}"),
    )
    def wlist_plus(singlenode, **kwargs):
        data = list()
        for node in list(self.elems(emphasized=True)):
            if not has_wordlist(node):
                continue
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
        self.signal("element_property_update", data)

    @tree_conditional(lambda node: has_wordlist(node))
    @tree_operation(
        _("Decrease Wordlist-Reference"),
        node_type=(
            "elem text",
            "elem path",
        ),
        help=_("Adjusts the reference value for a wordlist, ie {name#+3} to {name#+2}"),
    )
    def wlist_minus(singlenode, **kwargs):
        data = list()
        for node in list(self.elems(emphasized=True)):
            if not has_wordlist(node):
                continue
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
        self.signal("element_property_update", data)

    @tree_conditional(lambda node: has_vectorize(node))
    @tree_submenu(_("Outline element(s)..."))
    @tree_iterate("offset", 1, 10)
    @tree_operation(
        _("...with {offset}mm distance"),
        node_type=elem_nodes,
        help="",
    )
    def make_outlines(node, offset=1, **kwargs):
        self(f"outline {offset}mm\n")
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
        if len(data) == 0:
            return
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
        self.signal("rebuild_tree")
        node.focus()

    def has_vectorize(node):
        result = False
        make_vector = self.lookup("render-op/make_vector")
        if make_vector:
            result = True
        return result

    @tree_conditional(lambda node: has_vectorize(node))
    @tree_operation(
        _("Trace bitmap"),
        node_type=(
            "elem text",
            "elem image",
        ),
        help=_("Vectorize the given element"),
    )
    def trace_bitmap(node, **kwargs):
        self("vectorize\n")

    @tree_operation(
        _("Convert to vector text"),
        node_type="elem text",
        help=_("Convert bitmap text to vector text"),
    )
    def convert_to_vectext(node, **kwargs):
        data = []
        nodelist = list(self.flat(emphasized=True, types=("elem text",)))
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
            if anchor != "start":
                newnode.matrix.pre_translate_x(-1 * (p1.x - p0.x) / 2)

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
        if len(data):
            if self.classify_new:
                self.classify(data)
            self.signal("rebuild_tree")
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
    )
    def convert_to_path(singlenode, **kwargs):
        for node in list(self.elems(emphasized=True)):
            if not hasattr(node, "as_geometry"):
                continue
            node_attributes = []
            for attrib in ("stroke", "fill", "stroke_width", "stroke_scaled"):
                if hasattr(node, attrib):
                    oldval = getattr(node, attrib, None)
                    node_attributes.append([attrib, oldval])
            geometry = node.as_geometry()
            newnode = node.replace_node(geometry=geometry, type="elem path")
            for item in node_attributes:
                setattr(newnode, item[0], item[1])
            newnode.altered()

    @tree_conditional(
        lambda node: hasattr(node, "as_geometry") and node.has_ancestor("branch elems")
    )
    @tree_operation(
        _("Convert to path"),
        node_type=effect_nodes,
        help="Convert effect to path",
    )
    def convert_to_path(singlenode, **kwargs):
        elements = self.elem_branch
        for node in list(elements.flat(types=effect_nodes, emphasized=True)):
            if not hasattr(node, "as_geometry"):
                continue
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

    @tree_submenu(_("Flip"))
    @tree_separator_before()
    @tree_conditional(lambda node: not is_regmark(node))
    @tree_conditional_try(lambda node: node.can_scale)
    @tree_operation(
        _("Horizontally"),
        node_type=elem_group_nodes,
        help=_("Mirror Horizontally"),
    )
    def mirror_elem(node, **kwargs):
        bounds = self._emphasized_bounds
        if bounds is None:
            return
        center_x = (bounds[2] + bounds[0]) / 2.0
        center_y = (bounds[3] + bounds[1]) / 2.0
        self(f"scale -1 1 {center_x} {center_y}\n")

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_submenu(_("Flip"))
    @tree_conditional_try(lambda node: node.can_scale)
    @tree_operation(
        _("Vertically"),
        node_type=elem_group_nodes,
        help=_("Flip Vertically"),
    )
    def flip_elem(node, **kwargs):
        bounds = self._emphasized_bounds
        if bounds is None:
            return
        center_x = (bounds[2] + bounds[0]) / 2.0
        center_y = (bounds[3] + bounds[1]) / 2.0
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
    )
    def scale_elem_amount(node, scale, **kwargs):
        scale = 6.0 / float(scale)
        bounds = self._emphasized_bounds
        if bounds is None:
            return
        center_x = (bounds[2] + bounds[0]) / 2.0
        center_y = (bounds[3] + bounds[1]) / 2.0
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
    @tree_operation(_("Rotate {angle}°"), node_type=elem_group_nodes, help="")
    def rotate_elem_amount(node, angle, **kwargs):
        turns = float(angle) / 360.0
        bounds = self._emphasized_bounds
        if bounds is None:
            return
        center_x = (bounds[2] + bounds[0]) / 2.0
        center_y = (bounds[3] + bounds[1]) / 2.0
        self(f"rotate {turns}turn {center_x} {center_y}\n")
        self.signal("ext-modified")

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_conditional(lambda node: has_changes(node))
    @tree_conditional_try(lambda node: node.can_modify)
    @tree_operation(_("Reify User Changes"), node_type=elem_group_nodes, help="")
    def reify_elem_changes(node, **kwargs):
        self("reify\n")
        self.signal("ext-modified")

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_conditional_try(lambda node: node.can_modify)
    @tree_operation(_("Break Subpaths"), node_type="elem path", help="")
    def break_subpath_elem(node, **kwargs):
        self("element subpath\n")

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_conditional(lambda node: has_changes(node))
    @tree_conditional_try(lambda node: node.can_modify)
    @tree_operation(_("Reset user changes"), node_type=elem_group_nodes, help="")
    def reset_user_changes(node, copies=1, **kwargs):
        self("reset\n")
        self.signal("ext-modified")

    @tree_operation(
        _("Merge items"),
        node_type="group",
        help=_("Merge this node's children into 1 path."),
    )
    def merge_elements(node, **kwargs):
        self("element merge\n")
        # Is the group now empty? --> delete
        if len(node.children) == 0:
            node.remove_node()

    @tree_conditional(lambda node: node.lock)
    @tree_separator_before()
    @tree_operation(
        _("Unlock element, allows manipulation"), node_type=elem_nodes, help=""
    )
    def element_unlock_manipulations(node, **kwargs):
        self("element unlock\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_separator_before()
    @tree_operation(
        _("Lock elements, prevents manipulations"), node_type=elem_nodes, help=""
    )
    def element_lock_manipulations(node, **kwargs):
        self("element lock\n")

    @tree_conditional(lambda node: node.type == "branch reg")
    @tree_separator_before()
    @tree_operation(_("Toggle visibility of regmarks"), node_type="branch reg", help="")
    def toggle_visibility(node, **kwargs):
        self.signal("toggle_regmarks")

    @tree_conditional(lambda node: is_regmark(node))
    @tree_separator_before()
    @tree_operation(_("Move back to elements"), node_type=elem_group_nodes, help="")
    def move_back(node, **kwargs):
        # Drag and Drop
        with self.static("move_back"):
            drop_node = self.elem_branch
            data = list()
            for item in list(self.regmarks_nodes()):
                # print (item.type, item.emphasized, item.selected, item.highlighted)
                if item.emphasized:
                    data.append(item)
            if len(data) == 0:
                data.append(node)
            self.drag_and_drop(data, drop_node)

    @tree_conditional(lambda node: not is_regmark(node))
    @tree_separator_before()
    @tree_operation(_("Move to regmarks"), node_type=elem_group_nodes, help="")
    def move_to_regmark(node, **kwargs):
        # Drag and Drop
        with self.static("move_to_reg"):
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
    @tree_separator_before()
    @tree_operation(_("Create placement"), node_type=elem_nodes, help="")
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
        self.op_branch.add(
            type="place point", x=x, y=y, corner=corner, rotation=rotation
        )
        self.signal("refresh_scene", "Scene")

    @tree_conditional(lambda node: is_regmark(node))
    @tree_submenu(_("Toggle Magnet-Lines"))
    @tree_operation(_("Around border"), node_type=elem_group_nodes, help="")
    def regmark_to_magnet_1(node, **kwargs):
        if not hasattr(node, "bounds"):
            return
        self.signal("magnet_gen", ("outer", node))

    @tree_conditional(lambda node: is_regmark(node))
    @tree_submenu(_("Toggle Magnet-Lines"))
    @tree_operation(_("At center"), node_type=elem_group_nodes, help="")
    def regmark_to_magnet_2(node, **kwargs):
        if not hasattr(node, "bounds"):
            return
        self.signal("magnet_gen", ("center", node))

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Z-depth divide"))
    @tree_iterate("divide", 2, 10)
    @tree_operation(_("Divide into {divide} images"), node_type="elem image", help="")
    def image_zdepth(node, divide=1, **kwargs):
        if node.image.mode != "RGBA":
            node.image = node.image.convert("RGBA")
        band = 255 / divide
        for i in range(0, divide):
            threshold_min = i * band
            threshold_max = threshold_min + band
            self(f"image threshold {threshold_min} {threshold_max}\n")

    @tree_conditional(lambda node: node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(_("Unlock manipulations"), node_type="elem image", help="")
    def image_unlock_manipulations(node, **kwargs):
        self("image unlock\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(_("Lock manipulations"), node_type="elem image", help="")
    def image_lock_manipulations(node, **kwargs):
        self("image lock\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(_("Dither to 1 bit"), node_type="elem image", help="")
    def image_dither(node, **kwargs):
        self("image dither\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(_("Invert image"), node_type="elem image", help="")
    def image_invert(node, **kwargs):
        self("image invert\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(_("Mirror horizontal"), node_type="elem image", help="")
    def image_mirror(node, **kwargs):
        self("image mirror\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(_("Flip vertical"), node_type="elem image", help="")
    def image_flip(node, **kwargs):
        self("image flip\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(_("Rotate 90° CW"), node_type="elem image", help="")
    def image_cw(node, **kwargs):
        self("image cw\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(_("Rotate 90° CCW"), node_type="elem image", help="")
    def image_ccw(node, **kwargs):
        self("image ccw\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_separator_before()
    @tree_submenu(_("Image"))
    @tree_operation(_("Identify inner white areas"), node_type="elem image", help="")
    def image_white_area(node, **kwargs):
        self("image innerwhite -l -o -m 2\n")

    @tree_conditional(lambda node: not node.lock)
    @tree_submenu(_("Image"))
    @tree_operation(_("Split image along white areas"), node_type="elem image", help="")
    def image_white_area_split(node, **kwargs):
        self("image innerwhite -w -o -m 2\n")

    @tree_submenu(_("Image"))
    @tree_separator_before()
    @tree_operation(
        _("Save original image to output.png"), node_type="elem image", help=""
    )
    def image_save(node, **kwargs):
        self("image save output.png\n")

    @tree_submenu(_("Image"))
    @tree_operation(
        _("Save processed image to output.png"), node_type="elem image", help=""
    )
    def image_save_processed(node, **kwargs):
        self("image save output.png --processed\n")

    @tree_conditional(lambda node: len(node.children) > 0)
    @tree_separator_before()
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
        ),
        help=_("Expand all children of this given node."),
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
        ),
        help=_("Collapse all children of this given node."),
    )
    def collapse_all_children(node, **kwargs):
        node.notify_collapse()
