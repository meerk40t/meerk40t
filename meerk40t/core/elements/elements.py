"""
The elements module governs all interactions with various nodes and manages
the tree structure that stores all information about any active project.
It includes functionalities for handling operations, elements, and related
data structures such as Penbox and Wordlists.

This module provides a comprehensive set of classes and functions to manage
elements within the kernel, including operations for cutting, engraving,
rasterizing, and handling user-defined settings. It also supports undo
functionality, element classification, and the management of persistent
operations and preferences.
"""

import contextlib
import os.path
from copy import copy
from time import time

from meerk40t.core.exceptions import BadFileError
from meerk40t.core.node.node import Node
from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_dots import DotsOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_image import ImageOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.core.node.rootnode import RootNode
from meerk40t.core.undos import Undo
from meerk40t.core.units import Length
from meerk40t.core.wordlist import Wordlist
from meerk40t.kernel import ConsoleFunction, Service, Settings
from meerk40t.svgelements import Color, Path, Point, SVGElement

from . import offset_clpr, offset_mk
from .element_types import *


def plugin(kernel, lifecycle=None):
    """
    Plugin function for managing the lifecycle of the kernel in the application.

    This function handles different lifecycle events such as plugin registration,
    pre-registration of commands, and post-boot configurations. It allows for the
    dynamic loading of various plugins and the registration of commands and preferences
    based on the specified lifecycle phase.

    Args:
        kernel: The kernel instance to which the plugins and commands are registered.
        lifecycle (str, optional): The current lifecycle phase. It can be one of
            "plugins", "preregister", "register", "postboot", "prestart", or "poststart".

    Returns:
        list: A list of plugin functions if the lifecycle is "plugins", otherwise None.

    Raises:
        BadFileError: If there is an issue loading a file during the "prestart" phase.
    """
    _ = kernel.translation
    # The order of offset_mk before offset_clpr is relevant,
    # as offset_clpr could and should redefine something later
    if lifecycle == "plugins":
        from . import (
            align,
            branches,
            clipboard,
            element_treeops,
            files,
            geometry,
            grid,
            materials,
            notes,
            placements,
            render,
            shapes,
            trace,
            tree_commands,
            undo_redo,
            wordlist,
            testcases,
        )

        return [
            element_treeops.plugin,
            branches.plugin,
            trace.plugin,
            align.plugin,
            wordlist.plugin,
            materials.plugin,
            shapes.plugin,
            geometry.plugin,
            tree_commands.plugin,
            undo_redo.plugin,
            clipboard.plugin,
            grid.plugin,
            render.plugin,
            notes.plugin,
            files.plugin,
            placements.plugin,
            offset_mk.plugin,
            offset_clpr.plugin,
            testcases.plugin,
        ]
    elif lifecycle == "preregister":
        kernel.register(
            "format/op cut",
            "{danger}{defop}{enabled}{pass}{element_type} {speed}mm/s @{power} {colcode} {opstop}",
        )
        kernel.register(
            "format/op engrave",
            "{danger}{defop}{enabled}{pass}{element_type} {speed}mm/s @{power} {colcode} {opstop}",
        )
        kernel.register(
            "format/op hatch",
            "{danger}{defop}{enabled}{penpass}{pass}{element_type} {speed}mm/s @{power} {colcode} {opstop}",
        )
        kernel.register(
            "format/op raster",
            "{danger}{defop}{enabled}{pass}{element_type} {direction}{speed}mm/s @{power} {colcode} {opstop}",
        )
        kernel.register(
            "format/op image",
            "{danger}{defop}{enabled}{pass}{element_type} {direction}{speed}mm/s @{power}",
        )
        kernel.register(
            "format/op dots",
            "{danger}{defop}{enabled}{pass}{element_type} {dwell_time}ms dwell {opstop}",
        )

        kernel.register("format/util console", "{enabled}{command}")
        kernel.register("format/util wait", "{enabled}{element_type} {wait}")
        kernel.register("format/util home", "{enabled}{element_type}")
        kernel.register(
            "format/util goto", "{enabled}{element_type} {absolute}{adjust}"
        )
        kernel.register("format/util output", "{enabled}{element_type} {bits}")
        kernel.register("format/util input", "{enabled}{element_type} {bits}")
        kernel.register("format/layer", "{element_type} {name}")
        kernel.register("format/elem ellipse", "{element_type} {desc} {stroke}")
        kernel.register(
            "format/elem image", "{element_type} {desc} {width}x{height} @{dpi}"
        )
        kernel.register("format/elem line", "{element_type} {desc} {stroke}")
        kernel.register("format/elem path", "{element_type} {desc} {stroke}")
        kernel.register("format/elem point", "{element_type} {desc} {stroke}")
        kernel.register("format/elem polyline", "{element_type} {desc} {stroke}")
        kernel.register("format/elem rect", "{element_type} {desc} {stroke}")
        kernel.register("format/elem text", "{element_type} {desc} {text}")
        kernel.register(
            "format/effect hatch",
            "{element_type} - {distance} {angle} ({children})",
        )
        kernel.register(
            "format/effect wobble",
            "{element_type} - {type} {radius} ({children})",
        )
        kernel.register(
            "format/effect warp",
            "{element_type} - ({children})",
        )
        kernel.register("format/reference", "*{reference}")
        kernel.register(
            "format/group", "{element_type} {desc} ({children} children, {total} total)"
        )
        kernel.register("format/blob", "{element_type} {data_type}:{label} @{length}")
        kernel.register("format/file", "{element_type} {filename}")
        kernel.register("format/cutcode", "{element_type}")
        kernel.register("format/branch ops", "{element_type} {loops}")
        kernel.register("format/branch elems", "{element_type}")
        kernel.register("format/branch reg", "{element_type}")
        kernel.register("format/place current", "{enabled}{element_type}")
        kernel.register(
            "format/place point",
            "{enabled}{loops}{element_type}{grid} {corner} {x} {y} {rotation}",
        )
    elif lifecycle == "register":
        kernel.add_service("elements", Elemental(kernel))
        # kernel.add_service("elements", Elemental(kernel,1))
    elif lifecycle == "postboot":
        elements = kernel.elements
        choices = [
            {
                "attr": "operation_default_empty",
                "object": elements,
                "default": True,
                "type": bool,
                "label": _("Don't autoload operations on empty set"),
                "tip": _("Leave empty operations, don't load a default set"),
                "page": "Classification",
                "section": "_90_Auto-Generation",
            },
            {
                "attr": "classify_reverse",
                "object": elements,
                "default": False,
                "type": bool,
                "label": _("Classify Reversed"),
                "tip": _(
                    "Classify elements into operations in reverse order e.g. to match Inkscape's Object List"
                ),
                "page": "Classification",
                "section": "_10_Assignment-Logic",
            },
            # No longer used...
            # {
            #     "attr": "legacy_classification",
            #     "object": elements,
            #     "default": False,
            #     "type": bool,
            #     "label": _("Legacy Classify"),
            #     "tip": _(
            #         "Use the legacy classification algorithm rather than the modern classification algorithm."
            #     ),
            #     "page": "Classification",
            #     "section": "",
            # },
            {
                "attr": "use_undo",
                "object": elements,
                "default": True,
                "type": bool,
                "label": _("Track changes and allow undo"),
                "tip": _(
                    "MK will save intermediate states to undo/redo changes") + "\n" +
                    _("This may consume a significant amount of memory"),
                "page": "Start",
                "section": "_60_Undo",
                "signals": "restart",
            },
            {
                "attr": "undo_levels",
                "object": elements,
                "default": 20,
                "type": int,
                "lower": 3,
                "upper": 250,
                "label": _("Levels of Undo-States"),
                "tip": _("How many undo-levels shall MeerK40t hold in memory"),
                "page": "Start",
                "section": "_60_Undo",
                "conditional": (elements, "use_undo"),
                "signals": "restart",
            },
            {
                "attr": "classify_new",
                "object": elements,
                "default": True,
                "type": bool,
                "label": _("Classify elements after creation"),
                "tip": _(
                    "MK will immediately try to classify (automatically assign) an element as soon as it is created,"
                )
                + "\n"
                + _(
                    "if you want to defer this to apply manual assignment, then untick this option."
                ),
                "page": "Classification",
                "section": "_30_GUI-Behaviour",
            },
            {
                "attr": "classify_fuzzy",
                "object": elements,
                "default": False,
                "type": bool,
                "label": _("Fuzzy color-logic"),
                "tip": _(
                    "Unticked: Classify elements into operations with an *exact* color match"
                )
                + "\n"
                + _("Ticked: Allow a certain color-distance for classification"),
                "page": "Classification",
                "section": "_10_Assignment-Logic",
            },
            {
                "attr": "classify_fuzzydistance",
                "object": elements,
                "default": 100,
                "type": float,
                "label": _("Color distance"),
                "style": "combosmall",
                "choices": [
                    0,
                    100,
                    200,
                    400,
                ],
                "conditional": (elements, "classify_fuzzy"),
                "tip": _(
                    "The color distance of an element to an operations that will still allow classifiation"
                )
                + "\n"
                + _(
                    "Values: 0 Identical, 100 very close, 200 tolerant, 400 colorblind"
                ),
                "page": "Classification",
                "section": "_10_Assignment-Logic",
            },
            {
                "attr": "classify_black_as_raster",
                "object": elements,
                "default": True,
                "type": bool,
                "label": _(
                    "Treat 'Black' as raster even for basic elements (like Whisperer does)"
                ),
                "tip": _(
                    "Ticked: Classify will assign black elements to a raster operation"
                )
                + "\n"
                + _(
                    "Unticked: Classify will assign black elements to an engrave operation"
                ),
                "page": "Classification",
                "section": "_10_Assignment-Logic",
            },
            {
                "attr": "classify_fill",
                "object": elements,
                "default": False,
                "type": bool,
                "label": _("Classify elements on fill"),
                "tip": _(
                    "Usually MK will use the fill attribute as an indicator for a raster and will not distinguish between individual colors."
                )
                + "\n"
                + _(
                    "If you want to distinguish between different raster types then activate this option."
                ),
                "page": "Classification",
                "section": "_10_Assignment-Logic",
            },
            {
                "attr": "classify_default",
                "object": elements,
                "default": True,
                "type": bool,
                "hidden": True,
                "label": _("Assign to default operations"),
                "tip": _("If classification did not find a match,")
                + "\n"
                + _("either with color matching (exact or fuzzy, see above)")
                + "\n"
                + _("then it will try to assign it to matching 'default' operation"),
                "page": "Classification",
                "section": "_10_Assignment-Logic",
            },
            {
                "attr": "classify_autogenerate",
                "object": elements,
                "default": True,
                "type": bool,
                "label": _("Autogenerate Operations"),
                "tip": _("If classification did not find a match,")
                + "\n"
                + _("either with color matching (exact or fuzzy, see above)")
                + "\n"
                + _("or by assigning to a default operation (see above),")
                + "\n"
                + _("then MeerK40t can create a matching operation for you."),
                "page": "Classification",
                "section": "_90_Auto-Generation",
            },
            # {
            #     "attr": "classify_auto_inherit",
            #     "object": elements,
            #     "default": True,
            #     "type": bool,
            #     "label": _("Autoinherit for empty operation"),
            #     "tip": _(
            #         "If you drag and drop an element into an operation to assign it there,"
            #     )
            #     + "\n"
            #     + _(
            #         "then the op can (if this option is ticked) inherit the color from the element"
            #     )
            #     + "\n"
            #     + _(
            #         "and adopt not only the dragged element but all elements with the same color"
            #     )
            #     + "\n"
            #     + _(
            #         "- provided no elements are assigned to it yet (i.e. works only for an empty op)!"
            #     ),
            #     "page": "Classification",
            #     "section": "_30_GUI-Behaviour",
            # },
            {
                "attr": "classify_on_color",
                "object": elements,
                "default": True,
                "type": bool,
                "label": _("Classify after color-change"),
                "tip": _("Whenever you change an elements color (stroke or fill),")
                + "\n"
                + _(
                    "MK will then reclassify this element. You can turn this feature off"
                )
                + "\n"
                + _("by disabling this option."),
                "page": "Classification",
                "section": "_30_GUI-Behaviour",
            },
            {
                "attr": "remove_non_used_default_ops",
                "object": elements,
                "default": False,
                "type": bool,
                "label": _("Remove unused default operations"),
                "tip": _(
                    "If a default operation is no longer used it will be removed from the list of active operations"
                ),
                "page": "Classification",
                "section": "_30_GUI-Behaviour",
                "hidden": True,
            },
            {
                "attr": "lock_allows_move",
                "object": elements,
                "default": True,
                "type": bool,
                "label": _("Locked element may move"),
                "tip": _(
                    "Locked elements cannot be modified, but can still be moved if this option is checked."
                ),
                "page": "Scene",
                "section": "General",
            },
        ]
        for c in choices:
            c["help"] = "classification"
        kernel.register_choices("preferences", choices)
        choices = [
            {
                "attr": "op_show_default",
                "object": elements,
                "default": False,
                "type": bool,
                "label": _("Display 'default' for unchanged values"),
                "tip": _(
                    "Ticked: For power and speed display a 'default' string if default values in place."
                )
                + "\n"
                + _("Unticked: Show their current value."),
                "page": "Operations",
                "section": "Display",
            },
            {
                "attr": "allow_reg_to_op_dragging",
                "object": elements,
                "default": True,
                "type": bool,
                "label": _("Allow dragging of regmarks to operations"),
                "tip": _(
                    "Ticked: A drag operation of regmark nodes to an operation will move back these nodes to the element branch."
                )
                + "\n"
                + _(
                    "Unticked: A drag operation of regmark nodes to an operation will be ignored."
                ),
                "page": "Operations",
                "section": "Behaviour",
            },
            {
                "attr": "reuse_operations_on_load",
                "object": elements,
                "default": True,
                "type": bool,
                "label": _("Reuse existing"),
                "tip": _(
                    "Ticked: When loading a file we will reuse an existing operation with the same principal properties."
                )
                + "\n"
                + _(
                    "Unticked: We will add another operation alongside existing ones (always the case if properties differ)."
                ),
                "page": "Operations",
                "section": "Loading",
            },
            {
                "attr": "default_ops_display_mode",
                "object": elements,
                "default": 0,
                "type": int,
                "label": _("Statusbar display"),
                "style": "option",
                "display": (
                    _("As in operations tree"),
                    _("Group types together (CC EE RR II)"),
                    _("Matching (CERI CERI)"),
                ),
                "choices": (0, 1, 2),
                "tip": _(
                    "Choose if and how you want to group together / display the default operations at the bottom of the screen"
                ),
                "page": "Operations",
                "section": "_95_Default Operations",
                "signals": "default_operations",
            },
        ]
        for c in choices:
            c["help"] = "operations"
        kernel.register_choices("preferences", choices)
        choices = [
            {
                "attr": "classify_autogenerate_both",
                "object": elements,
                "default": True,
                "type": bool,
                "conditional": (elements, "classify_autogenerate"),
                "label": _("Autogenerate both for fill and stroke"),
                "tip": _(
                    "Active: for both stroke and fill we look for a corresponding hit, if none was found we generate a matching operation"
                )
                + "\n"
                + _(
                    "Inactive: one hit of either stroke or fill is enough to prevent autogeneration"
                ),
                "page": "Classification",
                "section": "_90_Auto-Generation",
            },
        ]
        kernel.register_choices("preferences", choices)
        choices = [
            {
                "attr": "copy_increases_wordlist_references",
                "object": elements,
                "default": True,
                "type": bool,
                "label": _("Copy will increase {variable} references"),
                "tip": _(
                    "Active: if you copy a text-element containing a wordlist-reference, this will be increased (effectively referencing the next entry in the wordlist)"
                ),
                "page": "Scene",
                "section": "_90_Wordlist",
            },
        ]
        kernel.register_choices("preferences", choices)

        choices = [
            {
                "attr": "auto_startup",
                "object": elements,
                "default": 1,
                "type": int,
                "label": _("File startup commands"),
                "style": "option",
                "display": (
                    _("Ignore"),
                    _("Ask"),
                    _("Allow"),
                ),
                "choices": (0, 1, 2),
                "tip": (
                    _(
                        "Choose if file startup commands are allowed in principle or will all be ignored."
                    )
                    + "\n"
                    + _("Note: They still need to be activated on a per file basis.")
                ),
                "page": "Start",
            },
        ]
        kernel.register_choices("preferences", choices)
    elif lifecycle == "prestart":
        if hasattr(kernel.args, "input") and kernel.args.input is not None:
            # Load any input file
            elements = kernel.elements

            try:
                elements.load(os.path.realpath(kernel.args.input.name))
            except BadFileError as e:
                kernel._console_channel(_("File is Malformed") + ": " + str(e))
    elif lifecycle == "poststart":
        if hasattr(kernel.args, "output") and kernel.args.output is not None:
            # output the file you have at this point.
            elements = kernel.elements

            elements.save(os.path.realpath(kernel.args.output.name))


def reversed_enumerate(collection: list):
    for i in range(len(collection) - 1, -1, -1):
        yield i, collection[i]


OP_PRIORITIES = ["op dots", "op image", "op raster", "op engrave", "op cut"]


# def is_dot(element):
#     if not isinstance(element, Shape):
#         return False
#     if isinstance(element, Path):
#         path = element
#     else:
#         path = element.segments()
#
#     if len(path) == 2 and isinstance(path[0], Move):
#         if isinstance(path[1], Close):
#             return True
#         if isinstance(path[1], Line) and path[1].length() == 0:
#             return True
#     return False


# def is_straight_line(element):
#     if not isinstance(element, Shape):
#         return False
#     if isinstance(element, Path):
#         path = element
#     else:
#         path = element.segments()
#
#     if len(path) == 2 and isinstance(path[0], Move):
#         if isinstance(path[1], Line) and path[1].length() > 0:
#             return True
#     return False


class Elemental(Service):
    def __init__(self, kernel, index=None, *args, **kwargs):
        Service.__init__(
            self, kernel, "elements" if index is None else f"elements{index}"
        )
        self._clipboard = {}
        self._clipboard_default = "0"

        self.note = None
        self.last_file_autoexec = None
        self.last_file_autoexec_active = False
        self._filename = None
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None
        self._emphasized_bounds_dirty = True
        self._tree = RootNode(self)
        self._save_restore_job = ConsoleFunction(self, ".save_restore_point\n", times=1)

        # Point / Segments selected.
        # points in format: points.append((g, idx, 0, node, geom))
        self.points = []
        self.segments = []

        # Will be filled with a list of newly added nodes after a load operation
        self.added_elements = []

        # keyhole-logic
        self.registered_keyholes = {}
        self.remembered_keyhole_nodes = []
        self.setting(bool, "use_undo", True)
        self.setting(int, "undo_levels", 20)
        undo_active = self.use_undo
        undo_levels = self.undo_levels
        self.undo = Undo(self, self._tree, active=undo_active, levels=undo_levels)
        self.do_undo = True
        self.suppress_updates = False
        self.suppress_signalling = False
        # We need to set up these as the settings stuff will only be done
        # on postboot after Elemental has already been created
        self.setting(bool, "classify_new", True)
        self.setting(bool, "classify_reverse", False)
        self.setting(bool, "legacy_classification", False)
        self.setting(bool, "classify_fuzzy", False)
        self.setting(float, "classify_fuzzydistance", 100.0)
        self.setting(bool, "classify_autogenerate", True)
        self.setting(bool, "classify_autogenerate_both", True)
        self.setting(bool, "classify_inherit_stroke", False)
        self.setting(bool, "classify_inherit_fill", False)
        self.setting(bool, "classify_inherit_exclusive", True)
        self.setting(bool, "update_statusbar_on_material_load", True)
        self.setting(bool, "classify_fill", False)
        # self.setting(bool, "classify_auto_inherit", False)
        self.setting(bool, "classify_default", True)
        self.setting(bool, "op_show_default", False)
        self.setting(bool, "reuse_operations_on_load", True)
        self.setting(bool, "lock_allows_move", True)
        self.setting(bool, "auto_note", True)
        self.setting(int, "auto_startup", 1)
        self.setting(bool, "uniform_svg", False)
        self.setting(float, "svg_ppi", 96.0)
        self.setting(bool, "operation_default_empty", True)
        self.setting(bool, "classify_black_as_raster", True)
        self.setting(bool, "classify_on_color", True)

        self.op_data = Settings(
            self.kernel.name, "operations.cfg", create_backup=True
        )  # keep backup

        self.wordlists = {"version": [1, self.kernel.version]}

        direct = os.path.dirname(self.op_data._config_file)
        self.mywordlist = Wordlist(self.kernel.version, direct)
        with self.undofree():
            self.load_persistent_operations("previous")

            ops = list(self.ops())
            if len(ops) == 0 and not self.operation_default_empty:
                self.load_default(performclassify=False)
            if list(self.ops()):
                # Something was loaded for default ops. Mark that.
                # Hint for translate check: _("Operations restored")
                self.undo.mark("Operations restored")  # Mark defaulted

        self._default_stroke = None
        self._default_strokewidth = None
        self._default_fill = None
        self._first_emphasized = None
        self._align_mode = "default"
        self._align_boundaries = None
        self._align_group = False
        self._align_stack = []

        self._timing_stack = {}

        self.default_operations = []
        self.init_default_operations_nodes()

    def set_start_time(self, key):
        if key in self._timing_stack:
            self._timing_stack[key][0] = time()
        else:
            self._timing_stack[key] = [time(), 0, 0]

    def set_end_time(self, key, display=True, delete=False, message=None):
        if key in self._timing_stack:
            stime = self._timing_stack[key]
            etime = time()
            duration = etime - stime[0]
            stime[0] = etime
            stime[1] += duration
            stime[2] += 1
            if display:
                if message is None:
                    msg = ""
                else:
                    msg = " (" + message + ")"
                output = self.kernel.channel("profiler", timestamp=True)
                # print (f"Duration for {key}: {duration:.2f} sec - calls: {stime[2]}, average={stime[1] / stime[2]:.2f} sec")
                output(
                    f"Duration for {key}: {duration:.2f} sec - calls: {stime[2]}, avg={stime[1] / stime[2]:.2f} sec{msg}"
                )
            if delete:
                del self._timing_stack[key]

    @contextlib.contextmanager
    def signalfree(self, source):
        try:
            last = self.suppress_signalling
            self.suppress_signalling = True
            self.stop_visual_updates()
            yield self
        finally:
            self.resume_visual_updates()
            self.suppress_signalling = False
            self.signal(source)

    @contextlib.contextmanager
    def static(self, source:str):
        try:
            self.stop_updates(source, False)
            yield self
        finally:
            self.resume_updates(source)

    @contextlib.contextmanager
    def undofree(self):
        try:
            self.do_undo = False
            yield self
        finally:
            self.do_undo = True

    @contextlib.contextmanager
    def undoscope(self, message:str, static:bool = True):
        busy = self.kernel.busyinfo
        busy.start(msg=self.kernel.translation(message))
        undo_active = self.do_undo
        # No need to mark the state if we are already in a scope...
        if undo_active:
            self.undo.mark(message)
        source = message.replace(" ", "_")
        try:
            if static:
                self.stop_updates(message, False)
            self.do_undo = False
            yield self
        finally:
            if static:
                self.resume_updates(source)
            if undo_active:
                self.do_undo = True
            busy.end()

    def stop_visual_updates(self):
        self._tree.notify_frozen(True)

    def resume_visual_updates(self):
        self._tree.notify_frozen(False)

    def stop_updates(self, source, stop_notify=False):
        # print (f"Stop update called from {source}")
        self._tree.pause_notify = stop_notify
        self.suppress_updates = True
        self.stop_visual_updates()

    def resume_updates(self, source, force_an_update=True):
        # print (f"Resume update called from {source}")
        self.suppress_updates = False
        self._tree.pause_notify = False
        self.resume_visual_updates()
        if force_an_update:
            self.signal("tree_changed")

    @property
    def filename(self):
        result = None
        if self._filename is not None:
            result = self._filename
        return result

    @property
    def basename(self):
        return os.path.basename(self._filename) if self._filename is not None else None

    @property
    def default_strokewidth(self):
        if self._default_strokewidth is not None:
            return self._default_strokewidth
        return 1000.0

    @default_strokewidth.setter
    def default_strokewidth(self, width):
        if isinstance(width, str):
            width = float(Length(width))
        self._default_strokewidth = width

    @property
    def default_stroke(self):
        # We don't allow an empty stroke color as default (why not?!) -- Empty stroke colors are hard to see.
        return Color("blue") if self._default_stroke is None else self._default_stroke

    @default_stroke.setter
    def default_stroke(self, color):
        if isinstance(color, str):
            color = Color(color)
        self._default_stroke = color

    @property
    def default_fill(self):
        return self._default_fill

    @default_fill.setter
    def default_fill(self, color):
        if isinstance(color, str):
            color = Color(color)
        self._default_fill = color

    @property
    def first_emphasized(self):
        if not self.has_emphasis():
            self._first_emphasized = None
        return self._first_emphasized

    @first_emphasized.setter
    def first_emphasized(self, node):
        self._first_emphasized = node

    def set_node_emphasis(self, node, flag):
        if not node.can_emphasize:
            return
        node.emphasized = flag
        if flag:
            if self._first_emphasized is None:
                self._first_emphasized = node
        else:
            if self._first_emphasized is node:
                self._first_emphasized = None
        # We target the parent, unless these are one of the root branches
        # pnode = node.parent
        # while pnode is not None:
        #     if pnode.type in ("root", "branch elems", "branch reg", "branch ops"):
        #         break
        #     pnode.targeted = True
        #     pnode = pnode.parent

    def unassigned_elements(self):
        for e in self.elems():
            if (e._references is None or len(e._references) == 0) and e.type not in (
                "file",
                "group",
            ):
                yield e

    def have_unassigned_elements(self):
        for _ in self.unassigned_elements():
            return True
        return False

    def have_burnable_elements(self):
        canburn = False
        # We might still have an effect to look for
        for node in self.ops():
            if not node.output:
                continue
            for child in node.children:
                if hasattr(child, "node"):
                    child = child.node
                if getattr(child, "hidden", False):
                    continue
                if hasattr(child, "affected_children")  and len(child.affected_children()) == 0:
                    continue
                canburn = True
                break
        return canburn

    def have_unburnable_elements(self):
        unassigned = False
        nonburnt = False
        for node in self.elems():
            if len(node._references) == 0 and node.type not in ("file", "group"):
                unassigned = True
            else:
                will_be_burnt = False
                for refnode in node._references:
                    op = refnode.parent
                    if op is not None:
                        try:
                            if op.output:
                                will_be_burnt = True
                                break
                        except AttributeError as e:
                            # print(f"Encountered error {e} for node {node.type}.{node.id}.{node.display_label()}")
                            pass
                if not will_be_burnt:
                    # print (f"Node {node.type}.{node.id}.{node.display_label()} has {len(node._references)} references but none is active...")
                    nonburnt = True
            if nonburnt and unassigned:
                break

        return unassigned, nonburnt

    def length(self, v):
        return float(Length(v))

    def length_x(self, v):
        try:
            return float(Length(v, relative_length=self.device.view.width))
        except AttributeError:
            return 0.0

    def length_y(self, v):
        try:
            return float(Length(v, relative_length=self.device.view.height))
        except AttributeError:
            return 0.0

    def bounds(self, x0, y0, x1, y1):
        return (
            self.length_x(x0),
            self.length_y(y0),
            self.length_x(x1),
            self.length_y(y1),
        )

    def area(self, v):
        llx = Length(v, relative_length=self.device.view.width)
        lx = float(llx)
        if "%" in v:
            lly = Length(v, relative_length=self.device.view.height)
        else:
            lly = Length(f"1{llx._preferred_units}")
        ly = float(lly)
        return lx * ly

    # ---- Operation tools

    def assign_operation(
        self,
        op_assign,
        data,
        impose="none",
        attrib=None,
        similar=False,
        exclusive=False,
    ):
        # op_assign:    operation to assign to
        # data:         nodes to assign to as minimum (will be extended is similar=True, see below)
        # impose:       - if "to_op" will use attrib-color (see below),
        #                 to impose the first evidence of color in data on the targetop
        #               - if "to_elem" will impose the color of the operation and make it the color of the
        #                 element attrib (i.e. stroke or fill)
        #               - anything else: leave all colors unchanged
        # attrib:       one of 'stroke', 'fill' to establish the source color
        #               ('auto' is an option too, that will pick the color from the
        #               operation settings) - if we talk about an engrave or cut operation
        #               and if 'stroke' or 'auto' have been set, 'fill' will be set None
        # similar:      will use attrib (see above) to establish similar elements (having (nearly) the same
        #               color) and assign those as well
        # exclusive:    will delete all other assignments of the source elements in other operations if True
        if len(data) == 0:
            return
        # some validation...
        if impose is not None:
            impose = impose.lower()
            if impose in ("to_op", "to_elem"):
                if attrib is None:
                    impose = None
            else:
                impose = None
                # No need to check, if no one needs it...

        first_color = None
        target_color = None
        has_a_color = False

        if impose == "to_elem":
            target_color = op_assign.color
            if attrib == "auto":
                if "stroke" in op_assign.allowed_attributes:
                    attrib = "stroke"
                elif "fill" in op_assign.allowed_attributes:
                    attrib = "fill"
                else:
                    attrib = "stroke"

        if attrib is None:
            similar = False
        # print ("parameters:")
        # print ("Impose=%s, operation=%s" % (impose, op_assign) )
        # print ("similar=%s, attrib=%s" % (similar, attrib) )
        # print ("exclusive=%s" % exclusive )

        if impose == "to_op" or similar:
            # Let's establish the color first
            # Look for the first element that has stroke/fill
            for n in data:
                if hasattr(n, attrib):
                    c = getattr(n, attrib)
                    # We accept stroke none or fill none as well!
                    has_a_color = True
                    try:
                        if c is not None and c.argb is not None:
                            first_color = c
                    except (AttributeError, ValueError):
                        first_color = None
                        # Strange....
                        has_a_color = False
                    if has_a_color:
                        break
            if impose == "to_op":
                target_color = first_color

        if impose == "to_op" and target_color is not None:
            op_assign.color = target_color
            if hasattr(op_assign, "add_color_attribute"):  # not true for image
                op_assign.remove_color_attribute("stroke")
                op_assign.remove_color_attribute("fill")
                op_assign.add_color_attribute(attrib)
        # If we haven't identified a color, then similar makes no sense
        if not has_a_color:
            similar = False
        # print ("We have now established the following:")
        # print ("Impose=%s, operation=%s" % (impose, op_assign) )
        # print ("Firstcolor=%s, targetcolor=%s" % (first_color, target_color) )
        # print ("Similar=%s, # data=%d" % (similar, len(data)) )
        if similar:
            # Now that we have the colors let's iterate through all elements
            fuzzy = self.classify_fuzzy
            fuzzydistance = self.classify_fuzzydistance
            for n in self.flat(types=elem_nodes):
                addit = False
                if hasattr(n, attrib):
                    c = getattr(n, attrib)
                    try:
                        if c.argb is None:
                            c = None
                    except AttributeError:
                        c = None
                    if c is not None and first_color is not None:
                        if fuzzy:
                            if Color.distance(first_color, c) <= fuzzydistance:
                                addit = True
                        else:
                            if c == first_color:
                                addit = True
                    elif c is None and first_color is None:
                        addit = True
                if addit and n not in data:
                    data.append(n)

        needs_refresh = False
        set_fill_to_none = (
            op_assign.type in ("op engrave", "op cut") and attrib == "stroke"
        )
        for n in data:
            if op_assign.can_drop(n):
                if exclusive:
                    for ref in list(n._references):
                        ref.remove_node()
                op_assign.drop(n, modify=True)
                if impose == "to_elem" and target_color is not None and hasattr(n, attrib):
                    setattr(n, attrib, target_color)
                    if set_fill_to_none and hasattr(n, "fill"):
                        n.fill = None
                    needs_refresh = True
        # Refresh the operation so any changes like color materialize...
        self.signal("element_property_reload", op_assign)
        if needs_refresh:
            # We changed elems, so update the tree and the scene
            self.signal("element_property_update", data)
            self.signal("refresh_scene", "Scene")

    def condense_elements(self, data, expand_at_end=True):
        """
        This routine looks at a given dataset and will condense
        it in the sense that if all elements of a given hierarchy
        (i.e. group or file) are in this set, then they will be
        replaced and represented by this parent element
        NB: we will set the emphasized_time of the parent element
        to the minimum time of all children
        """

        def remove_children_from_list(list_to_deal, parent_node):
            for idx, node in enumerate(list_to_deal):
                if node is None:
                    continue
                if node.parent is parent_node:
                    list_to_deal[idx] = None
                    if len(node.children) > 0:
                        remove_children_from_list(list_to_deal, node)
                    t1 = parent_node._emphasized_time
                    t2 = node._emphasized_time
                    if t2 is None:
                        continue
                    if t1 is None or t2 < t1:
                        parent_node._emphasized_time = t2

        align_data = list(data)
        needs_repetition = True
        while needs_repetition:
            # Will be set only if we add a parent, as the process needs then to be repeated
            needs_repetition = False

            data_to_align = []
            # We need to iterate through all the elements
            # to establish if they belong to a group,
            # if all the elements in this group are in
            # the dataset too, then we just take the group
            # as a representative.
            data_len = len(align_data)

            for idx1, node_1 in enumerate(align_data):
                if node_1 is None:
                    # Has been dealt with already
                    # print ("Eliminated node")
                    continue
                # Is this a group? Then we just take this node
                # and remove all children nodes
                if node_1.type in ("file", "group"):
                    # print (f"Group node ({node_1.display_label()}), eliminate children")
                    remove_children_from_list(align_data, node_1)
                    # No continue, as we still need to
                    # assess the parent case

                parent = node_1.parent
                if parent is None:
                    data_to_align.append(node_1)
                    align_data[idx1] = None
                    # print (f"Adding {node_1.type}, no parent")
                    continue
                if parent.type not in ("file", "group"):
                    # That should not happen per se,
                    # only for root objects which parent
                    # is elem_branch
                    # print (f"Adding {node_1.type}, parent was: {parent.type}")
                    data_to_align.append(node_1)
                    align_data[idx1] = None
                    continue
                # How many children are contained?
                candidates = len(parent.children)
                identified = 0
                if candidates > 0:
                    # We only need to look to elements not yet dealt with,
                    # but we start with the current index to include
                    # node_1 in the count
                    for idx2 in range(idx1, data_len, 1):
                        node_2 = align_data[idx2]
                        if node_2 is not None and node_2.parent is parent:
                            identified += 1
                if identified == candidates:
                    # All children of the parent object are contained
                    # So we add the parent instead...
                    data_to_align.append(parent)
                    remove_children_from_list(align_data, parent)
                    # print (f"Adding parent for {node_1.type}, all children inside")
                    needs_repetition = True

                else:
                    data_to_align.append(node_1)
                    align_data[idx1] = None
                    # print (f"Adding {node_1.type}, not all children of parent {identified} vs {candidates}")
            if needs_repetition:
                # We copy the data and do it again....
                # print ("Repetition required")
                align_data = list(data_to_align)
        # One special case though: if we have selected all
        # elements within a single group then we still deal
        # with all children
        if expand_at_end:
            while len(data_to_align) == 1:
                node = data_to_align[0]
                if node is not None and node.type in ("file", "group"):
                    data_to_align = list(node.children)
                else:
                    break
        return data_to_align

    def translate_node(self, node, dx, dy):
        if not node.can_move(self.lock_allows_move):
            return
        if node.type in ("group", "file"):
            for c in node.children:
                self.translate_node(c, dx, dy)
            node.translated(dx, dy)
        else:
            try:
                node.matrix.post_translate(dx, dy)
                node.translated(dx, dy)
            except AttributeError:
                pass

    def align_elements(
        self, data_to_align, alignbounds, positionx, positiony, as_group
    ):
        """

        @param data_to_align: elements to align
        @param alignbounds: boundary tuple (left, top, right, bottom)
                            to which data needs to be aligned to
        @param positionx:   one of "min", "max", "center"
        @param positiony:   one of "min", "max", "center"
        @param as_group:    0, align every element of data to the edge
                            1, align the group in total
        @return:
        """

        def calc_dx_dy():
            dx = 0
            dy = 0
            if positionx == "min":
                dx = alignbounds[0] - left_edge
            elif positionx == "max":
                dx = alignbounds[2] - right_edge
            elif positionx == "center":
                dx = (alignbounds[2] + alignbounds[0]) / 2 - (
                    right_edge + left_edge
                ) / 2

            if positiony == "min":
                dy = alignbounds[1] - top_edge
            elif positiony == "max":
                dy = alignbounds[3] - bottom_edge
            elif positiony == "center":
                dy = (alignbounds[3] + alignbounds[1]) / 2 - (
                    bottom_edge + top_edge
                ) / 2
            return dx, dy

        # Selection boundaries
        boundary_points = []
        for node in data_to_align:
            if node.bounds is not None:
                boundary_points.append(node.bounds)
        if not boundary_points:
            return
        left_edge = min(e[0] for e in boundary_points)
        top_edge = min(e[1] for e in boundary_points)
        right_edge = max(e[2] for e in boundary_points)
        bottom_edge = max(e[3] for e in boundary_points)
        if alignbounds is None:
            # print ("Alignbounds were not set...")
            alignbounds = (left_edge, top_edge, right_edge, bottom_edge)
        # print(f"Alignbounds: {alignbounds[0]:.1f},{alignbounds[1]:.1f},{alignbounds[2]:.1f},{alignbounds[3]:.1f}")

        if as_group == 0:
            groupdx = 0
            groupdy = 0
        else:
            groupdx, groupdy = calc_dx_dy()
            # print (f"Group move: {groupdx:.2f}, {groupdy:.2f}")
        with self.undoscope("Align"):
            for q in data_to_align:
                # print(f"Node to be treated: {q.type}")
                if q.bounds is None:
                    continue
                if as_group == 0:
                    if q.bounds is None:
                        continue
                    left_edge = q.bounds[0]
                    top_edge = q.bounds[1]
                    right_edge = q.bounds[2]
                    bottom_edge = q.bounds[3]
                    dx, dy = calc_dx_dy()
                else:
                    dx = groupdx
                    dy = groupdy
                # print (f"Translating {q.type} by {dx:.0f}, {dy:.0f}")
                self.translate_node(q, dx, dy)
        self.signal("refresh_scene", "Scene")
        self.signal("warn_state_update")

    def wordlist_delta(self, orgtext, increase):
        newtext = self.mywordlist.wordlist_delta(orgtext, increase)
        return newtext

    def wordlist_fetch(self, key):
        try:
            wordlist = self.wordlists[key]
        except KeyError:
            return None

        try:
            wordlist[0] += 1
            return wordlist[wordlist[0]]
        except IndexError:
            wordlist[0] = 1
            return wordlist[wordlist[0]]

    def wordlist_advance(self, delta):
        self.mywordlist.move_all_indices(delta)
        self.signal("refresh_scene", "Scene")
        self.signal("wordlist")

    def wordlist_translate(self, pattern, elemnode=None, increment=True):
        # This allows to add / set values for a given wordlist
        node = None
        if elemnode is not None:
            # Does it belong to an op?
            node = elemnode.parent
            # That only seems to be true during burn...
            if node is not None and not node.type.startswith("op"):
                node = None
                # print (f"Does not have an op node as parent ({elemnode.text})")
                for op in list(self.ops()):
                    for refnode in op.children:
                        if refnode.type == "reference" and refnode.node == elemnode:
                            # print (f"Found an associated op for {elemnode.text}")
                            node = op
                            break
                        if node is not None:
                            break

        for opatt in ("speed", "power", "dpi", "passes"):
            skey = f"op_{opatt}"
            found = False
            value = None
            if node is not None:
                if hasattr(node, opatt):
                    value = getattr(node, opatt, None)
                    found = True
                    if opatt == "passes" and (not node.passes_custom or value < 1):
                        # We need to look at one more info
                        value = 1
                else:  # Try setting
                    if hasattr(node, "settings"):
                        try:
                            value = node.settings[opatt]
                            found = True
                        except (AttributeError, KeyError, IndexError):
                            pass
            if found:
                if value is None:
                    value = ""
                self.mywordlist.set_value(skey, value)
            else:
                value = f"<{opatt}>"
                self.mywordlist.set_value(skey, value)
        skey = "op_device"
        value = self.device.label
        self.mywordlist.set_value(skey, value)

        result = self.mywordlist.translate(pattern, increment=increment)
        return result

    def service_detach(self, *args, **kwargs):
        self.unlisten_tree(self)

    def service_attach(self, *args, **kwargs):
        self.listen_tree(self)

    def shutdown(self, *args, **kwargs):
        # No need for an opinfo dict
        self.save_persistent_operations("previous")
        self.op_data.write_configuration()
        for e in self.flat():
            e.unregister()

    def safe_section_name(self, name):
        res = name
        for forbidden in " []":
            res = res.replace(forbidden, "_")
        return res

    def save_persistent_operations_list(
        self,
        name,
        oplist=None,
        opinfo=None,
        inform=True,
        use_settings=None,
        flush=True,
    ):
        """
        Saves a given list of operations to the op_data:Settings

        @param name:
        @param oplist:
        @param opinfo:
        @param inform:
        @param use_settings:
        @param flush:
        @return:
        """
        name = self.safe_section_name(name)
        if oplist is None:
            oplist = self.op_branch.children
        if opinfo is None:
            opinfo = {}
        settings = self.op_data if use_settings is None else use_settings
        self.clear_persistent_operations(name, flush=False, use_settings=settings)
        if len(opinfo) > 0:
            section = f"{name} info"
            for key, value in opinfo.items():
                settings.write_persistent(section, key, value)

        self._save_persistent_operation_tree(name, oplist, flush=flush, inform=True)

    # Operations uniform
    save_persistent_operations = save_persistent_operations_list

    def _save_persistent_operation_tree(
        self, name, oplist, flush=True, inform=True, use_settings=None
    ):
        """
        Recursive save of the tree. Sections append additional values for deeper tree values.
        References are not saved.

        @param name:
        @param oplist:
        @param: inform - if the name is an indicator for a default operation list,
                then we will let everyone know
        @return:
        """
        name = self.safe_section_name(name)
        settings = self.op_data if use_settings is None else use_settings
        for i, op in enumerate(oplist):
            if hasattr(op, "allow_save") and not op.allow_save():
                continue
            if op.type == "reference":
                # We do not save references.
                continue

            section = f"{name} {i:06d}"
            settings.write_persistent(section, "type", op.type)
            op.save(settings, section)
            try:
                self._save_persistent_operation_tree(
                    section, op.children, use_settings=settings
                )
            except AttributeError:
                pass
        if not flush:
            return
        settings.write_configuration()
        if inform and name.startswith("_default"):
            self.signal("default_operations")

    def clear_persistent_operations(self, name, flush=True, use_settings=None):
        """
        Clear operations for the derivables of the given name.

        @param name: name of operation.
        @param flush: Optionally permit non-flushed to disk
        @param use_settings:
        @return:
        """
        name = self.safe_section_name(name)
        settings = self.op_data if use_settings is None else use_settings
        for section in list(settings.derivable(name)):
            settings.clear_persistent(section)
        if not flush:
            return
        settings.write_configuration()

    def load_persistent_op_info(self, name, use_settings=None):
        name = self.safe_section_name(name)
        settings = self.op_data if use_settings is None else use_settings
        op_info = {}
        for section in list(settings.derivable(name)):
            if section.endswith("info"):
                for key in settings.keylist(section):
                    content = settings.read_persistent(str, section, key)
                    op_info[key] = content

                break
        return op_info

    def opnode_label(self, node):
        if isinstance(node, CutOpNode):
            # _("Cut ({percent}, {speed}mm/s)")
            lbl = "Cut ({percent}, {speed}mm/s)"
        elif isinstance(node, EngraveOpNode):
            # _("Engrave ({percent}, {speed}mm/s)")
            lbl = "Engrave ({percent}, {speed}mm/s)"
        elif isinstance(node, RasterOpNode):
            # _("Raster ({percent}, {speed}mm/s)")
            lbl = "Raster ({percent}, {speed}mm/s)"
        elif isinstance(node, ImageOpNode):
            # _("Image ({percent}, {speed}mm/s)")
            lbl = "Image ({percent}, {speed}mm/s)"
        else:
            lbl = ""
        _ = self.kernel.translation
        slabel = _(lbl)  # .format(power=node.power / 10, speed=node.speed)
        return slabel

    def load_persistent_op_list(self, name, use_settings=None):
        name = self.safe_section_name(name)
        settings = self.op_data if use_settings is None else use_settings
        op_tree = {}
        op_info = {}
        for section in list(settings.derivable(name)):
            if section.endswith("info"):
                for key in settings.keylist(section):
                    content = settings.read_persistent(str, section, key)
                    op_info[key] = content

                continue

            op_type = settings.read_persistent(str, section, "type")
            op_attr = {}
            for key in settings.keylist(section):
                if key == "type":
                    # We need to ignore it to avoid double attribute issues.
                    continue
                content = settings.read_persistent(str, section, key)
                op_attr[key] = content
            try:
                op = Node().create(type=op_type, **op_attr)
            except ValueError:
                # Attempted to create a non-bootstrapped node type.
                continue
            # op.load(settings, section)
            op_tree[section] = op
        op_list = []
        for section in op_tree:
            parent = " ".join(section.split(" ")[:-1])
            if parent == name:
                op_list.append(op_tree[section])
            else:
                op_tree[parent].add_node(op_tree[section])
        return op_list, op_info

    def load_persistent_operations(self, name, classify=None, clear=True):
        """
        Load oplist section to replace current op_branch data.

        Performs an optional classification.

        @param name:
        @param classify:
        @param clear:
        @return:
        """
        # _("Load operations")
        with self.undoscope("Load operations"):
            settings = self.op_data
            if clear:
                self.clear_operations()
            operation_branch = self.op_branch
            oplist, opinfo = self.load_persistent_op_list(name, use_settings=settings)
            for op in oplist:
                operation_branch.add_node(op)
            if classify is None:
                classify = self.classify_new
            if not classify:
                return
            if len(list(self.elems())) > 0:
                self.classify(list(self.elems()))
        self.signal("updateop_tree")

    # --------------- Default Operations logic
    def init_default_operations_nodes(self):
        def next_color(primary, secondary, tertiary, delta=32):
            secondary += delta
            if secondary > 255:
                secondary = 0
                primary -= delta
            if primary < 0:
                primary = 255
                tertiary += delta
            if tertiary > 255:
                tertiary = 0
            return primary, secondary, tertiary

        def create_cut(oplist):
            # Cut op
            idx = 0
            blue = 0
            green = 0
            red = 255
            for speed in (1, 2, 5):
                for power in (1000,):
                    idx += 1
                    op_id = f"C{idx:01d}"
                    op = CutOpNode(id=op_id, speed=speed, power=power)
                    op.label = self.opnode_label(op)
                    op.color = Color(red=red, blue=blue, green=green)
                    red, blue, green = next_color(red, blue, green, delta=64)
                    # print(f"Next for cut: {red} {blue} {green}")
                    op.allowed_attributes = ["stroke"]
                    oplist.append(op)

        def create_engrave(oplist):
            # Engrave op
            idx = 0
            blue = 255
            green = 0
            red = 0
            for speed in (20, 35, 50):
                for power in (1000, 750, 500):
                    idx += 1
                    op_id = f"E{idx:01d}"
                    op = EngraveOpNode(id=op_id, speed=speed, power=power)
                    op.label = self.opnode_label(op)
                    op.color = Color(red=red, blue=blue, green=green)
                    blue, green, red = next_color(blue, green, red, delta=24)
                    # print(f"Next for engrave: {red} {blue} {green}")
                    op.allowed_attributes = ["stroke"]
                    oplist.append(op)

        def create_raster(oplist):
            # Raster op
            idx = 0
            blue = 0
            green = 255
            red = 0
            for speed in (250, 200, 150, 100, 75):
                for power in (1000,):
                    idx += 1
                    op_id = f"R{idx:01d}"
                    op = RasterOpNode(id=op_id, speed=speed, power=power)
                    op.label = self.opnode_label(op)
                    op.color = Color(red=red, blue=blue, green=green, delta=60)
                    green, red, blue = next_color(green, red, blue)
                    # print(f"Next for raster: {red} {blue} {green}")
                    op.allowed_attributes = ["fill"]
                    oplist.append(op)

        def create_image(oplist):
            # Image op
            idx = 0
            blue = 0
            green = 0
            red = 0
            for speed in (250, 200, 150, 100, 75):
                for power in (1000,):
                    idx += 1
                    op_id = f"I{idx:01d}"
                    op = ImageOpNode(id=op_id, speed=speed, power=power)
                    op.label = self.opnode_label(op)
                    op.color = Color(red=red, blue=blue, green=green, delta=48)
                    green, blue, red = next_color(green, red, blue)
                    # print(f"Next for Image: {red} {blue} {green}")

                    oplist.append(op)

        # We first have a try at a device specific default_set
        needs_save = False
        std_list = "_default"
        needs_signal = len(self.default_operations) != 0
        oplist = []
        opinfo = {}
        if hasattr(self, "device"):
            std_list = f"_default_{self.device.label}"
            # We need to replace all ' ' by an underscore
            for forbidden in (" ",):
                std_list = std_list.replace(forbidden, "_")
            # print(f"Try to load '{std_list}'")
            oplist, opinfo = self.load_persistent_op_list(std_list)
        if len(oplist) == 0:
            std_list = "_default"
            # print(f"Try to load '{std_list}'")
            oplist, opinfo = self.load_persistent_op_list(std_list)

        if len(oplist) == 0:
            # Then let's create something useful
            create_cut(oplist)
            create_engrave(oplist)
            create_raster(oplist)
            create_image(oplist)
            opinfo.clear()
            opinfo["material"] = "Default"
            opinfo["author"] = "MeerK40t"
            needs_save = True
        # Ensure we have an id for everything
        if self.validate_ids(nodelist=oplist, generic=False):
            needs_save = True
        if needs_save:
            self.save_persistent_operations_list(
                std_list, oplist=oplist, opinfo=opinfo, inform=False
            )

        self.default_operations = oplist
        if needs_signal:
            self.signal("default_operations")

    def create_usable_copy(self, sourceop):
        op_to_use = copy(sourceop)
        for attr in ("id", "label", "color", "lock", "allowed_attributes"):
            setattr(op_to_use, attr, getattr(sourceop, attr))
        return op_to_use

    def assign_default_operation(self, data, targetop):
        emphasize_mode = False
        if data is None:
            emphasize_mode = True
            data = list(self.flat(emphasized=True))
        if len(data) == 0:
            return
        emph_data = [e for e in data]
        op_id = targetop.id
        if op_id is None:
            # WTF, that should not be the case
            op_list = [targetop]
            self.validate_ids(nodelist=op_list, generic=False)
        newone = True
        op_to_use = None
        for op in list(self.ops()):
            if op is targetop:
                # Already existing?
                newone = False
                op_to_use = op
                break
            elif op.id == op_id:
                newone = False
                op_to_use = op
                break
        if newone:
            op_to_use = self.create_usable_copy(targetop)
            try:
                self.op_branch.add_node(op_to_use)
            except ValueError:
                # This happens when we have somehow lost sync with the node,
                # and we try to add a node that is already added...
                # In principle this should be covered by the check
                # above, but you never know
                pass
        impose = "to_elem"
        similar = False
        exclusive = True
        self.assign_operation(
            op_assign=op_to_use,
            data=data,
            impose=impose,
            attrib="auto",
            similar=similar,
            exclusive=exclusive,
        )
        self.remove_unused_default_copies()
        if emphasize_mode:
            # Restore emphasized flags
            for e in emph_data:
                e.emphasized = True
        self.signal("element_property_reload", data)
        self.signal("warn_state_update")

    def remove_unused_default_copies(self):
        # Let's clean non-used operations that come from defaults...
        if self.remove_non_used_default_ops:
            # print("Remove unused called")
            deleted = 0
            to_be_deleted = []

            for op in list(self.ops()):
                # print(f"look at {op.type} - {op.id}: {len(op.children)}")
                if op.id is None:
                    continue
                if len(op.children) != 0:
                    continue
                # is this one of the default operations?
                for def_op in self.default_operations:
                    if def_op.id == op.id:
                        to_be_deleted.append(op)
                        break
            for op in to_be_deleted:
                deleted += 1
                # print(f"will remove {op.type}- {op.id}")
                op.remove_node()

            if deleted:
                self.signal("operation_removed")

    # ------------------------------------------------------------------------

    def prepare_undo(self, message=None):
        if self.do_undo:
            self.undo.message = message
            self.schedule(self._save_restore_job)

    def emphasized(self, *args):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None

    def altered(self, node=None, *args, **kwargs):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None
        # Hint for translate check: _("Element altered")
        self.prepare_undo("Element altered")
        self.test_for_keyholes(node, "altered")

    def modified(self, node=None, *args):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None
        # Hint for translate check: _("Element modified")
        self.prepare_undo("Element modified")
        self.test_for_keyholes(node, "modified")

    def translated(self, node=None, dx=0, dy=0, interim=False, *args):
        # It's safer to just recompute the selection area
        # as these listener routines will be called for every
        # element that faces a .translated(dx, dy)
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None
        # Hint for translate check: _("Element shifted")
        self.prepare_undo("Element shifted")
        self.test_for_keyholes(node, "translated")

    def scaled(self, node=None, sx=1, sy=1, ox=0, oy=0, interim=False, *args):
        # It's safer to just recompute the selection area
        # as these listener routines will be called for every
        # element that faces a .translated(dx, dy)
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None
        # Hint for translate check: _("Element scaled")
        self.prepare_undo("Element scaled")
        self.test_for_keyholes(node, "scaled")

    def node_attached(self, node, **kwargs):
        # Hint for translate check: _("Element added")
        self.prepare_undo("Element added")

    def node_detached(self, node, **kwargs):
        # Hint for translate check: _("Element deleted")
        self.prepare_undo("Element deleted")
        self.remove_keyhole(node)

    def listen_tree(self, listener):
        self._tree.listen(listener)

    def unlisten_tree(self, listener):
        self._tree.unlisten(listener)

    def create_minimal_op_list(self):
        oplist = []
        pwr = 1000
        spd = 140
        node = Node().create(
            type="op image",
            color="black",
            id="I1",
            power=pwr,
            speed=spd,
            raster_step=3,
        )
        node.label = self.opnode_label(node)
        oplist.append(node)
        pwr = 1000
        spd = 150
        node = Node().create(
            type="op raster",
            id="R1",
            power=pwr,
            speed=spd,
        )
        node.label = self.opnode_label(node)
        node.allowed_attributes = ["fill"]
        oplist.append(node)
        pwr = 1000
        spd = 35
        node = Node().create(
            type="op engrave",
            id="E1",
            power=pwr,
            speed=spd,
        )
        node.label = self.opnode_label(node)
        node.allowed_attributes = ["stroke"]
        oplist.append(node)
        pwr = 1000
        spd = 5
        node = Node().create(
            type="op cut",
            id="C1",
            power=pwr,
            speed=spd,
        )
        node.label = self.opnode_label(node)
        node.allowed_attributes = ["stroke"]
        oplist.append(node)
        return oplist

    def create_basic_op_list(self):
        oplist = []
        pwr = 1000
        spd = 140
        node = Node().create(
            type="op image",
            color="black",
            id="I1",
            power=pwr,
            speed=spd,
            raster_step=3,
        )
        node.label = self.opnode_label(node)
        oplist.append(node)
        pwr = 1000
        spd = 150
        node = Node().create(
            type="op raster",
            id="R1",
            power=pwr,
            speed=spd,
        )
        node.label = self.opnode_label(node)
        node.allowed_attributes = ["fill"]
        oplist.append(node)
        pwr = 1000
        spd = 35
        node = Node().create(
            type="op engrave",
            color="blue",
            id="E1",
            power=pwr,
            speed=spd,
        )
        node.label = self.opnode_label(node)
        node.allowed_attributes = ["stroke"]
        oplist.append(node)
        pwr = 1000
        spd = 30
        node = Node().create(
            type="op engrave",
            color="green",
            id="E2",
            power=pwr,
            speed=spd,
        )
        node.label = self.opnode_label(node)
        node.allowed_attributes = ["stroke"]
        oplist.append(node)
        pwr = 1000
        spd = 25
        node = Node().create(
            type="op engrave",
            color="magenta",
            id="E3",
            power=pwr,
            speed=spd,
        )
        node.label = self.opnode_label(node)
        node.allowed_attributes = ["stroke"]
        oplist.append(node)
        pwr = 1000
        spd = 20
        node = Node().create(
            type="op engrave",
            color="cyan",
            id="E4",
            power=pwr,
            speed=spd,
        )
        node.label = self.opnode_label(node)
        node.allowed_attributes = ["stroke"]
        oplist.append(node)
        pwr = 1000
        spd = 15
        node = Node().create(
            type="op engrave",
            color="yellow",
            id="E5",
            power=pwr,
            speed=spd,
        )
        node.label = self.opnode_label(node)
        node.allowed_attributes = ["stroke"]
        oplist.append(node)
        pwr = 1000
        spd = 5
        node = Node().create(
            type="op cut",
            color="red",
            id="C1",
            power=pwr,
            speed=spd,
        )
        node.label = self.opnode_label(node)
        node.allowed_attributes = ["stroke"]
        oplist.append(node)
        pwr = 1000
        spd = 2
        node = Node().create(
            type="op cut",
            color="darkred",
            id="C2",
            power=pwr,
            speed=spd,
        )
        node.label = self.opnode_label(node)
        node.allowed_attributes = ["stroke"]
        oplist.append(node)
        return oplist

    def load_default(self, performclassify=True):
        # _("Load default operations")
        with self.undoscope("Load default operations"):
            self.clear_operations()
            nodes = self.create_minimal_op_list()
            for node in nodes:
                self.op_branch.add_node(node)
            if performclassify:
                self.classify(list(self.elems()))

    def load_default2(self, performclassify=True):
        # _("Load default operations")
        with self.undoscope("Load default operations"):
            self.clear_operations()
            nodes = self.create_basic_op_list()
            for node in nodes:
                self.op_branch.add_node(node)
            if performclassify:
                self.classify(list(self.elems()))

    def flat(self, **kwargs):
        yield from self._tree.flat(**kwargs)

    def validate_ids(self, nodelist=None, generic=True):
        changes = False
        idx = 1
        uid = {}
        missing = []
        if nodelist is None:
            nodelist = list(self.flat())
        for node in nodelist:
            if node.id in uid:
                # ID already used. Clear.
                node.id = None
            if not node.id:
                # Unused IDs need new IDs
                missing.append(node)
            else:
                # Set this ID as used.
                uid[node.id] = node
        for m in missing:
            changes = True
            pattern = "meerk40t:"
            if not generic and m.type.startswith("op "):
                pattern = m.type[3].upper()
            while f"{pattern}{idx}" in uid:
                idx += 1
            m.id = f"{pattern}{idx}"
            uid[m.id] = m
        return changes

    @property
    def reg_branch(self):
        return self._tree.get(type="branch reg")

    @property
    def op_branch(self):
        return self._tree.get(type="branch ops")

    @property
    def elem_branch(self):
        return self._tree.get(type="branch elems")

    def ops(self, **kwargs):
        operations = self.op_branch
        for item in operations.flat(depth=1, **kwargs):
            if item.type.startswith("branch") or item.type.startswith("ref"):
                continue
            yield item

    def op_groups(self, **kwargs):
        operations = self.op_branch
        for item in operations.flat(**kwargs):
            if item.type.startswith("branch") or item.type.startswith("ref"):
                continue
            yield item

    def elems(self, **kwargs):
        elements = self.elem_branch
        yield from elements.flat(types=elem_nodes, **kwargs)

    def elems_nodes(self, depth=None, **kwargs):
        elements = self.elem_branch
        yield from elements.flat(types=elem_group_nodes, depth=depth, **kwargs)

    def regmarks(self, **kwargs):
        elements = self.reg_branch
        yield from elements.flat(types=elem_nodes, **kwargs)

    def regmarks_nodes(self, depth=None, **kwargs):
        elements = self.reg_branch
        yield from elements.flat(types=elem_group_nodes, depth=depth, **kwargs)

    def placement_nodes(self, depth=None, **kwargs):
        elements = self.op_branch
        yield from elements.flat(types=place_nodes, depth=depth, **kwargs)

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
            if hasattr(e, "hidden") and e.hidden:
                continue
            return True
        return False

    def count_elems(self, **kwargs):
        return len(list(self.elems(**kwargs)))

    def count_op(self, **kwargs):
        return len(list(self.ops(**kwargs)))

    def get(self, type=None):
        return self._tree.get(type=type)

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
        @return:
        """
        operation_branch = self.op_branch
        operation_branch.add_node(op, pos=pos)
        self.signal("add_operation", op)

    def add_ops(self, adding_ops):
        operation_branch = self.op_branch
        items = []
        for op in adding_ops:
            operation_branch.add_node(op)
            items.append(op)
        self.signal("add_operation", items)
        return items

    def clear_operations(self, fast=False):
        operations = self.op_branch
        operations.remove_all_children(fast=fast)
        if hasattr(operations, "loop_continuous"):
            operations.loop_continuous = False
            operations.loop_enabled = False
            operations.loop_n = 1
            self.signal("element_property_update", operations)
        self.signal("operation_removed")

    def clear_elements(self, fast=False):
        elements = self.elem_branch
        elements.remove_all_children(fast=fast)
        self.remembered_keyhole_nodes.clear()
        self.registered_keyholes.clear()

    def clear_regmarks(self, fast=False):
        elements = self.reg_branch
        elements.remove_all_children(fast=fast)

    def clear_files(self):
        pass

    def clear_elements_and_operations(self):
        fast = True
        self.clear_elements(fast=fast)
        self.clear_operations(fast=fast)
        if fast:
            self.signal("rebuild_tree", "all")

    def clear_all(self, ops_too=True):
        fast = True
        self.set_start_time("clear_all")
        with self.static("Clear all"):
            self.clear_elements(fast=fast)
            if ops_too:
                self.clear_operations(fast=fast)
            self.clear_files()
            self.clear_note()
            self.clear_autoexec()
            self.clear_regmarks(fast=fast)
            # Do we have any other routine that wants
            # to be called when we start from scratch?
            for routine in self.kernel.lookup_all("reset_routines/.*"):
                routine()
            self.validate_selected_area()
        if fast:
            self.signal("rebuild_tree", "all")
        self.set_end_time("clear_all", display=True)
        self._filename = None
        self.signal("file;cleared")

    def clear_note(self):
        self.note = None
        self.signal("note", self.note)

    def clear_autoexec(self):
        self.last_file_autoexec = None
        self.last_file_autoexec_active = False
        self.signal("autoexec")

    def drag_and_drop(self, dragging_nodes, drop_node, flag=False):
        data = dragging_nodes
        success = False
        to_classify = []
        # if drop_node.type.startswith("op"):
        #     if len(drop_node.children) == 0 and self.classify_auto_inherit:
        #         # only for empty operations!
        #         # Let's establish the colors first
        #         first_color_stroke = None
        #         first_color_fill = None
        #         inh_stroke = False
        #         inh_fill = False
        #         # Look for the first element that has stroke/fill
        #         for n in data:
        #             if first_color_stroke is None and hasattr(n, "stroke") and n.stroke is not None and n.stroke.argb is not None:
        #                 first_color_stroke = n.stroke
        #                 inh_stroke = True
        #             if first_color_fill is None and hasattr(n, "fill") and n.fill is not None and n.fill.argb is not None:
        #                 first_color_fill = n.fill
        #                 inh_fill = True
        #             canbreak = inh_fill or inh_stroke
        #             if canbreak:
        #                 break
        #         if hasattr(drop_node, "color") and (inh_fill or inh_stroke):
        #             # Well if you have both options, then you get that
        #             # color that is present, precedence for fill
        #             if inh_fill:
        #                 col = first_color_fill
        #                 if hasattr(drop_node, "add_color_attribute"): # not true for image
        #                     drop_node.add_color_attribute("fill")
        #                     drop_node.remove_color_attribute("stroke")
        #             else:
        #                 col = first_color_stroke
        #                 if hasattr(drop_node, "add_color_attribute"): # not true for image
        #                     drop_node.add_color_attribute("stroke")
        #                     drop_node.remove_color_attribute("fill")
        #             drop_node.color = col

        #         # Now that we have the colors let's iterate through all elements
        #         fuzzy = self.classify_fuzzy
        #         fuzzydistance = self.classify_fuzzydistance
        #         for n in self.flat(types=elem_nodes):
        #             addit = False
        #             if inh_stroke and first_color_stroke is not None and hasattr(n, "stroke") and n.stroke is not None and n.stroke.argb is not None:
        #                 if fuzzy:
        #                     if Color.distance(first_color_stroke, n.stroke) <= fuzzydistance:
        #                         addit = True
        #                 else:
        #                     if n.stroke == first_color_stroke:
        #                         addit = True
        #             if inh_fill and first_color_fill is not None and hasattr(n, "fill") and n.fill is not None and n.fill.argb is not None:
        #                 if fuzzy:
        #                     if Color.distance(first_color_fill, n.fill) <= fuzzydistance:
        #                         addit = True
        #                 else:
        #                     if n.fill == first_color_fill:
        #                         addit = True
        #             # print ("Checked %s and will addit=%s" % (n.type, addit))
        #             if addit and n not in data:
        #                 data.append(n)
        to_be_refreshed = list(drop_node.flat())
        # _("Drag and drop")
        with self.undoscope("Drag and drop"):
            for drag_node in data:
                to_be_refreshed.extend(drag_node.flat())
                op_treatment = (
                    drop_node.type in op_parent_nodes and (
                        not drag_node.has_ancestor("branch reg") or
                        (drag_node.has_ancestor("branch reg") and self.allow_reg_to_op_dragging)
                    )
                )
                if drop_node is drag_node:
                    # print(f"Drag {drag_node.type} to {drop_node.type} - Drop node was drag node")
                    continue
                if op_treatment and drag_node.has_ancestor("branch reg"):
                    # We need to first relocate the drag_node to the elem branch
                    # print(f"Relocate {drag_node.type} to elem branch")
                    self.elem_branch.drop(drag_node, flag=flag)
                if drop_node.can_drop(drag_node):
                    # Is the drag node coming from the regmarks branch?
                    # If yes then we might need to classify.
                    if drag_node.has_ancestor("branch reg"):
                        if drag_node.type in ("file", "group"):
                            to_classify.extend(iter(drag_node.flat(elem_nodes)))
                        else:
                            to_classify.append(drag_node)
                    drop_node.drop(drag_node, modify=True, flag=flag)
                    success = True
                # else:
                #     print(f"Drag {drag_node.type} to {drop_node.type} - Drop node vetoed")
            if self.classify_new and to_classify:
                self.classify(to_classify)
        # Refresh the target node so any changes like color materialize...
        # print (f"Success: {success}\n{','.join(e.type for e in to_be_refreshed)}")
        self.signal("element_property_reload", to_be_refreshed)
        return success

    def remove_nodes(self, node_list):
        self.set_start_time("remove_nodes")
        to_be_deleted = 0
        fastmode = False
        for node in node_list:
            for n in node.flat():
                n._mark_delete = True
                to_be_deleted += 1
                for ref in list(n._references):
                    ref._mark_delete = True
                    to_be_deleted += 1
        fastmode = to_be_deleted >= 100
        for n in reversed(list(self.flat())):
            if not hasattr(n, "_mark_delete"):
                continue
            if n.type in ("root", "branch elems", "branch reg", "branch ops"):
                continue
            n.remove_node(children=False, references=False, fast=fastmode)
        self.set_end_time("remove_nodes")
        if fastmode:
            self.signal("rebuild_tree", "all")

    def remove_elements(self, element_node_list):
        for elem in element_node_list:
            if hasattr(elem, "can_remove") and not elem.can_remove:
                continue
            elem.remove_node(references=True)
        self.validate_selected_area()

    def remove_operations(self, operations_list):
        for op in operations_list:
            for i, o in enumerate(list(self.ops())):
                if o is op:
                    o.remove_node()
            self.signal("operation_removed")

    def remove_elements_from_operations(self, elements_list):
        for node in elements_list:
            for ref in list(node._references):
                ref.remove_node()

    def selected_area(self, painted=False):
        if self._emphasized_bounds_dirty:
            self.validate_selected_area()
        if painted:
            return self._emphasized_bounds_painted
        else:
            return self._emphasized_bounds

    def validate_selected_area(self):
        boundary_points = []
        boundary_points_painted = []
        for e in self.elem_branch.flat(
            types=elem_nodes,
            emphasized=True,
        ):
            if e.bounds is None:
                continue
            if hasattr(e, "hidden") and e.hidden:
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
            box = e.paint_bounds
            top_left = [box[0], box[1]]
            top_right = [box[2], box[1]]
            bottom_left = [box[0], box[3]]
            bottom_right = [box[2], box[3]]
            boundary_points_painted.append(top_left)
            boundary_points_painted.append(top_right)
            boundary_points_painted.append(bottom_left)
            boundary_points_painted.append(bottom_right)

        if len(boundary_points) == 0:
            new_bounds = None
            new_bounds_painted = None
        else:
            xmin = min([e[0] for e in boundary_points])
            ymin = min([e[1] for e in boundary_points])
            xmax = max([e[0] for e in boundary_points])
            ymax = max([e[1] for e in boundary_points])
            new_bounds = [xmin, ymin, xmax, ymax]
            xmin = min([e[0] for e in boundary_points_painted])
            ymin = min([e[1] for e in boundary_points_painted])
            xmax = max([e[0] for e in boundary_points_painted])
            ymax = max([e[1] for e in boundary_points_painted])
            new_bounds_painted = [xmin, ymin, xmax, ymax]
        self._emphasized_bounds_dirty = False
        if self._emphasized_bounds != new_bounds:
            self._emphasized_bounds = new_bounds
            self._emphasized_bounds_painted = new_bounds_painted
            self.signal("selected_bounds", self._emphasized_bounds)

    def highlight_children(self, node_context):
        """
        Recursively highlight the children.
        @param node_context:
        @return:
        """
        for child in node_context.children:
            child.highlighted = True
            self.highlight_children(child)

    # def target_clones(self, node_context, node_exclude, object_search):
    #     """
    #     Recursively highlight the children.
    #
    #     @param node_context: context node to search from
    #     @param node_exclude: excluded nodes
    #     @param object_search: Specific searched for object.
    #     @return:
    #     """
    #     for child in node_context.children:
    #         self.target_clones(child, node_exclude, object_search)
    #         if child is node_exclude:
    #             continue
    #         if child.object is None:
    #             continue
    #         if object_search is child.object:
    #             child.targeted = True

    def set_selected(self, selected):
        """
        Selected is the sublist of specifically selected nodes.
        """
        for s in self._tree.flat():
            in_list = selected is not None and s in selected
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
        If any element is emphasized, all references are highlighted.
        If any element is emphasized, all operations a references to that element are 'targeted'.
        """
        self.set_start_time("set_emphasis")
        with self.signalfree("emphasized"):
            for s in self._tree.flat():
                if s.highlighted:
                    s.highlighted = False
                if s.targeted:
                    s.targeted = False
                if s.selected:
                    s.selected = False
                if not s.can_emphasize:
                    continue
                in_list = emphasize is not None and s in emphasize
                if s.emphasized:
                    if not in_list:
                        s.emphasized = False
                else:
                    if in_list:
                        s.emphasized = True
                        s.selected = True
            if emphasize is not None:
                # Validate emphasize
                old_first = self.first_emphasized
                if old_first is not None and not old_first.emphasized:
                    self.first_emphasized = None
                    old_first = None
                count = 0
                for e in emphasize:
                    count += 1
                    if e.type == "reference":
                        self.set_node_emphasis(e.node, True)
                        e.highlighted = True
                    else:
                        self.set_node_emphasis(e, True)
                        e.selected = True
                    # if hasattr(e, "object"):
                    #     self.target_clones(self._tree, e, e.object)
                    self.highlight_children(e)
                if count > 1 and old_first is None:
                    # It makes no sense to define a 'first' here, as all are equal
                    self.first_emphasized = None
        self.set_end_time("set_emphasis")

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
        b = self._emphasized_bounds_painted
        if b is None:
            return
        self._emphasized_bounds_painted = [
            min(b[0], b[2]),
            min(b[1], b[3]),
            max(b[0], b[2]),
            max(b[1], b[3]),
        ]
        self.signal("selected_bounds", self._emphasized_bounds)

    def update_bounds(self, b):
        self._emphasized_bounds = [b[0], b[1], b[2], b[3]]
        # We don't know it better...
        self._emphasized_bounds_painted = [b[0], b[1], b[2], b[3]]
        self._emphasized_bounds_dirty = False
        self.signal("selected_bounds", self._emphasized_bounds)

    def move_emphasized(self, dx, dy):
        for node in self.elems(emphasized=True):
            if not node.can_move(self.lock_allows_move):
                continue
            node.matrix.post_translate(dx, dy)
            # node.modified()
            node.translated(dx, dy)

    def set_emphasized_by_position(
        self,
        position,
        keep_old_selection=False,
        use_smallest=False,
        exit_over_selection=False,
    ):
        def contains(box, x, y=None):
            if y is None:
                y = x[1]
                x = x[0]
            return box[0] <= x <= box[2] and box[1] <= y <= box[3]

        if self.has_emphasis():
            if (
                self._emphasized_bounds is not None
                and contains(self._emphasized_bounds, position)
                # and contains(self._emphasized_bounds_painted, position)
                and exit_over_selection
            ):
                return  # Select by position aborted since selection position within current select bounds.
        # Remember previous selection, in case we need to append...
        e_list = []
        f_list = []  # found elements...
        if keep_old_selection:
            for node in self.elems(emphasized=True):
                e_list.append(node)
        for node in self.elems_nodes(emphasized=False):
            try:
                bounds = node.bounds
            except AttributeError:
                continue  # No bounds.
            if hasattr(node, "hidden") and node.hidden:
                continue
            # Empty group / files may cause problems
            if node.type in ("file", "group"):
                if not node._children:
                    bounds = None
            if bounds is None:
                continue
            if contains(bounds, position):
                f_list.append(node)
        bounds = None
        bounds_painted = None
        if len(f_list) > 0:
            # We checked that before, f_list contains only elements with valid bounds...
            e = None
            if use_smallest:
                e_area = float("inf")
            else:
                e_area = -float("inf")
            for node in f_list:
                cc = node.bounds
                f_area = (cc[2] - cc[0]) * (cc[3] - cc[1])
                if use_smallest:
                    if f_area <= e_area:  # Tie goes to child or later sibling
                        e_area = f_area
                        e = node
                else:
                    if f_area > e_area:
                        e_area = f_area
                        e = node
            if e is not None:
                bounds = e.bounds
                bounds_painted = e.paint_bounds
                if bounds_painted is None or bounds is None:
                    e.set_dirty_bounds()
                    bounds = e.bounds
                    bounds_painted = e.paint_bounds
                e_list.append(e)
                if self._emphasized_bounds is not None:
                    cc = self._emphasized_bounds
                    bounds = (
                        min(bounds[0], cc[0]),
                        min(bounds[1], cc[1]),
                        max(bounds[2], cc[2]),
                        max(bounds[3], cc[3]),
                    )
                if self._emphasized_bounds_painted is not None:
                    cc = self._emphasized_bounds_painted
                    bounds = (
                        min(bounds_painted[0], cc[0]),
                        min(bounds_painted[1], cc[1]),
                        max(bounds_painted[2], cc[2]),
                        max(bounds_painted[3], cc[3]),
                    )
        if len(e_list) > 0:
            self._emphasized_bounds = bounds
            self._emphasized_bounds_painted = bounds_painted
            self.set_emphasis(e_list)
            self.signal("element_clicked")
        else:
            self._emphasized_bounds = None
            self._emphasized_bounds_painted = None
            self.set_emphasis(None)

    def post_classify(self, data):
        """
        Provides a post_classification algorithm.

        Why are we doing it here? An immediate classification
        at the end of the element creation might not provide
        the right assignment as additional commands might be
        chained to it:

        e.g. "circle 1cm 1cm 1cm" will classify differently than
        "circle 1cm 1cm 1cm stroke red"

        So we apply the classify_new to the post commands.

        @return: post classification function.
        """

        def post_classify_function(**kwargs):
            if self.classify_new and len(data) > 0:
                with self.undoscope("Classify elements"):
                    self.classify(data)
                self.signal("tree_changed")

        return post_classify_function

    def classify(self, elements, operations=None, add_op_function=None):
        """
        @param elements: list of elements to classify.
        @param operations: operations list to classify into.
        @param add_op_function: function to add a new operation,
                because of a lack of classification options.
        @return:
        """

        def emptydebug(value):
            return

        def _get_next_auto_raster_count(operations):
            auto_raster_count = 0
            for op in operations:
                if op.type == "op raster" and op.id is not None and op.id.startswith("AR#"):
                    try:
                        used_id = int(op.id[3:])
                        auto_raster_count = max(auto_raster_count, used_id)
                    except (IndexError, ValueError):
                        pass
            return auto_raster_count + 1

        def _select_raster_candidate(operations, node, fuzzydistance):
            candidate = None
            candidate_dist = float("inf")
            for cand_op in operations:
                if cand_op.type != "op raster":
                    continue
                col_d = Color.distance(cand_op.color, abs(node.fill))
                if col_d > fuzzydistance:
                    continue
                if candidate is None or col_d < candidate_dist:
                    candidate = cand_op
                    candidate_dist = col_d
            return candidate

        # I am tired of changing the code all the time, so let's do it properly
        debug = self.kernel.channel("classify", timestamp=True)

        if elements is None:
            return
        new_operations_added = False
        debug_set = {}

        def update_debug_set(debug_set, opnode):
            if opnode.type not in debug_set:
                debug_set[opnode.type] = 0
            debug_set[opnode.type] = debug_set[opnode.type] + 1


        if len(list(self.ops())) == 0 and not self.operation_default_empty:
            has_cut = False
            has_engrave = False
            has_raster = False
            has_image = False
            # Do we need to load a default set or do the default_operations
            # contain already relevant archetypes?
            for test in self.default_operations:
                if isinstance(test, CutOpNode):
                    has_cut = True
                elif isinstance(test, EngraveOpNode):
                    has_engrave = True
                elif isinstance(test, RasterOpNode):
                    has_raster = True
                elif isinstance(test, ImageOpNode):
                    has_image = True
            if not (has_cut and has_engrave and has_raster and has_image):
                self.load_default(performclassify=False)
        reverse = self.classify_reverse
        fuzzy = self.classify_fuzzy
        fuzzydistance = self.classify_fuzzydistance
        usedefault = self.classify_default
        autogen = self.classify_autogenerate
        if reverse:
            elements = reversed(elements)
        if operations is None:
            operations = list(self.ops())
        if add_op_function is None:
            # add_op_function = self.add_op
            add_op_function = self.add_classify_op
        for node in elements:
            node_desc = f"[{node.type}]{'' if node.id is None else node.id + '-'}{'<none>' if node.label is None else node.display_label()}"
            if hasattr(node, "stroke") or hasattr(node, "fill"):
                info = ""
                if hasattr(node, "stroke") and node.stroke is not None:
                    info += f"S:{node.stroke},"
                if hasattr(node, "fill") and node.fill is not None:
                    info += f"F:{node.fill},"
                node_desc += f"({info})"
            # Following lines added to handle 0.7 special ops added to ops list
            if hasattr(node, "operation"):
                add_op_function(node)
                continue
            classif_info = [False, False]
            # Even for fuzzy we check first a direct hit
            fuzzy_param = (False, True) if fuzzy else (False, )
            do_stroke = True
            do_fill = True
            for tempfuzzy in fuzzy_param:
                if debug:
                    debug(
                        f"Pass 1 (fuzzy={tempfuzzy}): checks, s:{do_stroke}, f:{do_fill}, node:{node_desc}"
                    )
                was_classified = False
                should_break = False

                for op in operations:
                    # One special case: is this a rasterop and the stroke
                    # color is black and the option 'classify_black_as_raster'
                    # is not set? Then skip...
                    if not do_stroke and op.type in ("op engrave", "op cut", "op dots"):
                        continue
                    if not do_fill and op.type in ("op raster", "op image"):
                        continue
                    is_black = False
                    perform_classification = True
                    if (
                        hasattr(node, "stroke")
                        and node.stroke is not None
                        and node.stroke.argb is not None
                        and node.type != "elem text"
                    ):
                        if fuzzy:  # No need to distinguish tempfuzzy here
                            is_black = (
                                Color.distance("black", node.stroke) <= fuzzydistance
                                or Color.distance("white", node.stroke) <= fuzzydistance
                            )
                        else:
                            is_black = (
                                Color("black") == node.stroke
                                or Color("white") == node.stroke
                            )
                    if (
                        not self.classify_black_as_raster
                        and is_black
                        and isinstance(op, RasterOpNode)
                    ):
                        perform_classification = False
                    elif (
                        self.classify_black_as_raster
                        and is_black
                        and isinstance(op, EngraveOpNode)
                    ):
                        perform_classification = False
                    if debug:
                        debug(
                            f"For {op.type}.{op.id}: black={is_black}, perform={perform_classification}, flag={self.classify_black_as_raster}"
                        )
                    if not (hasattr(op, "classify") and perform_classification):
                        continue
                    classified = False
                    classifying_op = None
                    if (
                        self.classify_fill and
                        op.type=="op raster" and
                        hasattr(node, "fill") and node.fill is not None
                    ):
                        # This is a special use case:
                        # Usually we don't distinguish a fill color - all non-transparent objects
                        # are assigned to a single raster operation.
                        # If the classify_fill flag is set, then we will use the fill attribute
                        # to look for / create a matching raster operation
                        raster_candidate = _select_raster_candidate(operations, node, fuzzydistance)
                        if raster_candidate is None and self.classify_autogenerate:
                            # We need to create one...
                            auto_raster_count = _get_next_auto_raster_count(operations)
                            raster_candidate = RasterOpNode(
                                id = f"AR#{auto_raster_count}",
                                label = f"Auto-Raster #{auto_raster_count}",
                                color = abs(node.fill),
                                output = True,
                            )
                            add_op_function(raster_candidate)
                            new_operations_added = True

                        classified, should_break, feedback = raster_candidate.classify(
                            node,
                            fuzzy=tempfuzzy,
                            fuzzydistance=fuzzydistance,
                            usedefault=False,
                        )
                        if classified:
                            classifying_op = raster_candidate
                            should_break = True
                            if debug:
                                debug(
                                    f"{node_desc} was color-raster-classified: {sstroke} {sfill} matching operation: {type(classifying_op).__name__}, break={should_break}"
                                )

                    if not classified:
                        classified, should_break, feedback = op.classify(
                            node,
                            fuzzy=tempfuzzy,
                            fuzzydistance=fuzzydistance,
                            usedefault=False,
                        )
                        if classified:
                            classifying_op = op
                    if classified:
                        update_debug_set(debug_set, classifying_op)
                        if feedback is not None and "stroke" in feedback:
                            classif_info[0] = True
                        if feedback is not None and "fill" in feedback:
                            classif_info[1] = True
                        was_classified = True
                        if hasattr(node, "stroke"):
                            sstroke = f"s={getattr(node, 'stroke')},"
                        else:
                            sstroke = ""
                        if hasattr(node, "fill"):
                            sfill = f"s={getattr(node, 'fill')},"
                        else:
                            sfill = ""
                        if debug:
                            debug(
                                f"{node_desc} was classified: {sstroke} {sfill} matching operation: {type(classifying_op).__name__}, break={should_break}"
                            )
                    if should_break:
                        break
                # end of operation loop, let's make sure we don't do stuff again if we were successful
                if classif_info[0]:
                    do_stroke = False
                if classif_info[1]:
                    do_fill = False

                # So we are the end of the first pass, if there was already a classification
                # then we call it a day and don't call the fuzzy part
                if was_classified or should_break:
                    break
            # - End of fuzzy loop

            ######################
            # NON-CLASSIFIED ELEMENTS
            ######################
            if not do_stroke:
                classif_info[0] = True
            if not do_fill:
                classif_info[1] = True
            if was_classified and debug:
                debug(f"Classified, stroke={classif_info[0]}, fill={classif_info[1]}")
            # Let's make sure we only consider relevant, i.e. existing attributes...
            if hasattr(node, "stroke"):
                if node.stroke is None or node.stroke.argb is None:
                    classif_info[0] = True
                if node.type == "elem text":
                    # even if it has, we are not going to do something with it
                    classif_info[0] = True
            else:
                classif_info[0] = True
            if hasattr(node, "fill"):
                if node.fill is None or node.fill.argb is None:
                    classif_info[1] = True
            else:
                classif_info[1] = True

            if self.classify_autogenerate_both and not (
                classif_info[0] and classif_info[1]
            ):
                # Not fully classified on both stroke and fill
                was_classified = False
                if debug:
                    debug(
                        f"{node_desc} was not fully classified on stroke and fill (s:{classif_info[0]}, f:{classif_info[1]})"
                    )
            if not was_classified and usedefault:
                # let's iterate through the default ops and add them
                if debug:
                    debug("Pass 2 (wasn't classified), looking for default ops")
                default_candidates = []
                for op in operations:
                    if (
                        hasattr(op, "classify") and
                        getattr(op, "default", False) and
                        hasattr(op, "valid_node_for_reference") and
                        op.valid_node_for_reference(node)
                    ):
                        default_candidates.append(op)
                if len(default_candidates) > 1 and debug:
                    debug(f"For node {node_desc} there were {len(default_candidates)} default operations available, nb the very first will be taken!")
                for op in default_candidates:
                    classified, should_break, feedback = op.classify(
                        node,
                        fuzzy=fuzzy,
                        fuzzydistance=fuzzydistance,
                        usedefault=True,
                    )
                    if classified:
                        update_debug_set(debug_set, op)
                        # Default ops fulfill stuff by definition
                        classif_info[0] = True
                        classif_info[1] = True
                        was_classified = True
                        if debug:
                            debug(
                                f"Was classified to default operation: {type(op).__name__}"
                            )
                        break
            # Let's make sure we only consider relevant, i.e. existing attributes...
            if hasattr(node, "stroke"):
                if node.stroke is None or node.stroke.argb is None:
                    classif_info[0] = True
                if node.type == "elem text":
                    # even if it has, we are not going to do something with it
                    classif_info[0] = True
            else:
                classif_info[0] = True
            if hasattr(node, "fill"):
                if node.fill is None or node.fill.argb is None:
                    classif_info[1] = True
            else:
                classif_info[1] = True

            if self.classify_autogenerate_both and not (
                classif_info[0] and classif_info[1]
            ):
                # Not fully classified on both stroke and fill
                was_classified = False
            if not was_classified and autogen:
                # Despite all efforts we couldn't classify the element, so let's add an op
                if debug:
                    debug("Pass 3, not classified by ops or def ops")
                stdops = []
                if node.type == "elem image":
                    found_default = False
                    for op_candidate in self.default_operations:
                        if isinstance(op_candidate, ImageOpNode):
                            op_to_use = self.create_usable_copy(op_candidate)
                            stdops.append(op_to_use)
                            found_default = True
                            break
                    if found_default:
                        if debug:
                            debug(
                                f"add an op image from default ops with id {op_to_use.id}"
                            )
                    else:
                        stdops.append(ImageOpNode())
                        if debug:
                            debug("add an op image")
                    classif_info[0] = True
                    classif_info[1] = True
                elif node.type == "elem point":
                    found_default = False
                    for op_candidate in self.default_operations:
                        if isinstance(op_candidate, DotsOpNode):
                            op_to_use = self.create_usable_copy(op_candidate)
                            stdops.append(op_to_use)
                            found_default = True
                            break
                    if found_default:
                        if debug:
                            debug(
                                f"add an op dots from default ops with id {op_to_use.id}"
                            )
                    else:
                        stdops.append(DotsOpNode())
                        if debug:
                            debug("add an op dots")
                    classif_info[0] = True
                    classif_info[1] = True
                # That should leave us with fulfilled criteria or stroke / fill stuff
                if (
                    not classif_info[0]
                    and hasattr(node, "stroke")
                    and node.stroke is not None
                    and node.stroke.argb is not None
                ):
                    # Let's loop through the default operations
                    # First the whisperer case
                    if self.classify_black_as_raster:
                        if fuzzy:
                            is_raster = (
                                Color.distance("black", abs(node.stroke))
                                <= fuzzydistance
                                or Color.distance("white", abs(node.stroke))
                                <= fuzzydistance
                            )
                        else:
                            is_raster = Color("black") == abs(node.stroke) or Color(
                                "white"
                            ) == abs(node.stroke)
                    else:
                        is_raster = False
                    if is_raster:
                        stdops.append(RasterOpNode(color="black", output=True))
                        if debug:
                            debug("add an op raster based on black color")
                        classif_info[0] = True
                        classif_info[1] = True
                # Still not something? Check default operations...
                if (
                    not classif_info[0]
                    and hasattr(node, "stroke")
                    and node.stroke is not None
                    and node.stroke.argb is not None
                ):
                    fuzzy_param = (False, True) if fuzzy else (False, )
                    was_classified = False
                    for tempfuzzy in fuzzy_param:
                        if debug:
                            debug(
                                f"Pass 3-stroke, fuzzy={tempfuzzy}): check {node.type}"
                            )
                        for op_candidate in self.default_operations:
                            if isinstance(op_candidate, (CutOpNode, EngraveOpNode)):
                                if tempfuzzy:
                                    classified = (
                                        Color.distance(
                                            abs(node.stroke), abs(op_candidate.color)
                                        )
                                        <= fuzzydistance
                                    )
                                else:
                                    classified = abs(node.stroke) == abs(
                                        op_candidate.color
                                    )

                                if classified:
                                    classif_info[0] = True
                                    was_classified = True
                                    op_to_use = self.create_usable_copy(op_candidate)
                                    stdops.append(op_to_use)
                                    if debug:
                                        debug(
                                            f"Found a default op with fitting stroke, id={op_to_use.id}"
                                        )
                                    break
                        if was_classified:
                            break
                # Sigh, not even a default operation was found...
                if (
                    not classif_info[0]
                    and hasattr(node, "stroke")
                    and node.stroke is not None
                    and node.stroke.argb is not None
                ):
                    if fuzzy:
                        is_cut = (
                            Color.distance(abs(node.stroke), "red") <= fuzzydistance
                        )
                    else:
                        is_cut = abs(node.stroke) == Color("red")
                    if is_cut:
                        op = CutOpNode(color=Color("red"), speed=5.0)
                        op.add_color_attribute("stroke")
                        stdops.append(op)
                        if debug:
                            debug("add an op cut due to stroke")
                    else:
                        op = EngraveOpNode(color=node.stroke, speed=35.0)
                        op.add_color_attribute("stroke")
                        stdops.append(op)
                        if debug:
                            debug(
                                f"add an op engrave with color={node.stroke} due to stroke"
                            )

                # -------------------------------------
                # Do we need to add a fill operation?

                if (
                    not classif_info[1]
                    and hasattr(node, "fill")
                    and node.fill is not None
                    and node.fill.argb is not None
                ):
                    if node.fill.red == node.fill.green == node.fill.blue:
                        is_black = True
                    elif fuzzy:
                        is_black = (
                            Color.distance("black", abs(node.fill)) <= fuzzydistance
                            or Color.distance("white", abs(node.fill)) <= fuzzydistance
                        )
                    else:
                        is_black = Color("black") == abs(node.fill) or Color(
                            "white"
                        ) == abs(node.fill)
                    node_fill = Color("black") if is_black else abs(node.fill)
                    fuzzy_param = (False, True) if fuzzy else (False, )
                    was_classified = False
                    for tempfuzzy in fuzzy_param:
                        if debug:
                            debug(f"Pass 3-fill (fuzzy={tempfuzzy}): check {node.type}")
                        for op_candidate in self.default_operations:
                            classified = False
                            if isinstance(op_candidate, RasterOpNode):
                                if tempfuzzy:
                                    classified = (
                                        Color.distance(
                                            node_fill, abs(op_candidate.color)
                                        )
                                        <= fuzzydistance
                                    )
                                else:
                                    classified = node_fill == abs(op_candidate.color)
                            if classified:
                                classif_info[1] = True
                                was_classified = True
                                op_to_use = self.create_usable_copy(op_candidate)
                                stdops.append(op_to_use)
                                if debug:
                                    debug(
                                        f"Found a default op with fitting fill, id={op_to_use.id}"
                                    )
                                break
                        if was_classified:
                            break
                # Sigh, not even a default operation was found...
                if (
                    not classif_info[1]
                    and hasattr(node, "fill")
                    and node.fill is not None
                    and node.fill.argb is not None
                ):
                    default_color = abs(node.fill) if self.classify_fill else Color("black")
                    default_id = "AR#1" if self.classify_fill else "R1"
                    default_label = "Auto-Raster #1" if self.classify_fill else "Standard-Raster"
                    op = RasterOpNode(
                        id=default_id,
                        label=default_label,
                        color=default_color,
                        output = True,
                    )
                    stdops.append(op)
                    if debug:
                        debug("add an op raster due to fill")

                # ---------------------------------------
                for op in stdops:
                    # Let's make sure we don't have something like that already
                    if debug:
                        debug(f"Check for existence of {op.type}")
                    already_found = False
                    testlist = list(self.ops())
                    for testop in testlist:
                        if type(op) == type(testop):
                            sameop = True
                        else:
                            sameop = False
                        samecolor = False
                        if hasattr(op, "color") and hasattr(testop, "color"):
                            # print ("Comparing color %s to %s" % ( op.color, testop.color ))
                            if fuzzy:
                                if (
                                    Color.distance(op.color, testop.color)
                                    <= fuzzydistance
                                ):
                                    samecolor = True
                            else:
                                if op.color == testop.color:
                                    samecolor = True
                        elif hasattr(op, "color") != hasattr(testop, "color"):
                            samecolor = False
                        else:
                            samecolor = True
                        if op.type == "elem raster":
                            samecolor = True
                        samespeed = False
                        if hasattr(op, "speed") and hasattr(testop, "speed"):
                            if op.speed == testop.speed:
                                samespeed = True
                        elif hasattr(op, "speed") != hasattr(testop, "speed"):
                            samespeed = False
                        else:
                            samespeed = True
                        # print ("Compare: %s to %s - op=%s, col=%s, speed=%s" % (type(op).__name__, type(testop).__name__, sameop, samecolor, samespeed))
                        if sameop and samecolor and samespeed:
                            if debug:
                                debug("A similar operation existed")
                            already_found = True
                            op = testop
                            break
                    if not already_found:
                        if debug:
                            debug(f"Add a new operation {op.type}")
                        if hasattr(op, "output"):
                            op.output = True
                        add_op_function(op)
                        operations.append(op)
                        new_operations_added = True
                        already_found = True
                    # Don't add a node more than once!
                    existing = False
                    if hasattr(op, "is_referenced"):
                        existing = op.is_referenced(node)

                    if not existing:
                        op.add_reference(node)
                        update_debug_set(debug_set, op)


        self.remove_unused_default_copies()
        if debug:
            debug("Summary:")
            for key, count in debug_set.items():
                debug(f"{count} items assigned to {key}")
        if new_operations_added:
            self.signal("tree_changed")

    def add_classify_op(self, op):
        """
        Ops are added as part of classify as elements are iterated that need a new op.
        Rather than add them at the end, creating a random sequence of Engrave and Cut operations
        perhaps with an Image or Raster or Dots operation in there as well, instead  we need to try
        to group operations together, adding the new operation:
        1. After the last operation of the same type if one exists; or if not
        2. After the last operation of the highest priority existing operation, where `Dots` is the lowest priority and
            Cut is the highest.
        """
        operations = self.op_branch.children
        for pos, old_op in reversed_enumerate(operations):
            if op.type == old_op.type:
                return self.add_op(op, pos=pos + 1)

        # No operation of same type found. So we will look for last operation of a lower priority and add after it.
        try:
            priority = OP_PRIORITIES.index(op.type)
        except ValueError:
            return self.add_op(op)

        for pos, old_op in reversed_enumerate(operations):
            try:
                if OP_PRIORITIES.index(old_op.type) < priority:
                    return self.add_op(op, pos=pos + 1)
            except ValueError:
                pass
        return self.add_op(op, pos=0)

    # def classify_advanced(self, elements, operations=None, add_op_function=None):
    #     """
    #     Classify does the placement of elements within operations.
    #     In the future, we expect to be able to save and reload the mapping of
    #     elements to operations, but at present classification is the only means
    #     of assigning elements to operations.
    #
    #     This classification routine ensures that every element is assigned
    #     to at least one operation - the user does NOT have to check whether
    #     some elements have not been assigned (which was an issue with 0.6.x).
    #
    #     Because of how overlaying raster elements can have white areas masking
    #     underlying non-white areas, the classification of raster elements is complex,
    #     and indeed deciding whether elements should be classified as vector or raster
    #     has edge case complexities.
    #
    #     SVGImage is classified as Image.
    #     Dots are a special type of Path
    #     All other SVGElement types are Shapes / Text
    #
    #     Paths consisting of a move followed by a single stright line segment
    #     are never Raster (since no width) - testing for more complex stright line
    #     path-segments and that multiple-such-segments are also straight-line is complex,
    #
    #     Shapes/Text with grey (R=G=B) strokes are raster by default regardless of fill
    #
    #     Shapes/Text with non-transparent Fill are raster by default - except for one
    #     edge case: Elements with white fill, non-grey stroke and no raster elements behind
    #     them are considered vector elements.
    #
    #     Shapes/Text with no fill and non-grey strokes are vector by default - except
    #     for one edge case: Elements with strokes that have other raster elements
    #     overlaying the stroke should in some cases be considered raster elements,
    #     but there are several use cases and counter examples are likely easy to create.
    #     The algorithm below tries to be conservative in deciding whether to switch a default
    #     vector to a raster due to believing it is part of raster combined with elements on top.
    #     In essence, if there are raster elements on top (later in the list of elements) that
    #     have the given vector element's stroke colour as either a stroke or fill colour, then the
    #     probability is that this vector element should be considered a raster instead.
    #
    #     RASTER ELEMENTS
    #     Because rastering of overlapping elements depends on the sequence of the elements
    #     (think of the difference between a white fill above or below a black fill)
    #     it is essential that raster elements are added to operations in the same order
    #     that they exist in the file/elements branch.
    #
    #     Raster elements are handled differently depending on whether existing
    #     Raster operations are simple or complex:
    #         1.  Simple - all existing raster ops have the same color
    #             (default being a different colour to any other); or
    #         2.  Complex - there are existing raster ops of two different colors
    #             (default being a different colour to any other)
    #
    #     Simple - Raster elements are matched immediately to all Raster operations.
    #     Complex - Raster elements are processed in a more complex second pass (see below)
    #
    #     VECTOR ELEMENTS
    #     Vector Shapes/Text are attempted to match to Cut/Engrave/Raster operations of
    #     exact same color (regardless of default raster or vector)
    #
    #     If not matched to exact colour, vector elements are classified based on colour:
    #         1. Redish strokes are considered cuts
    #         2. Other colours are considered engraves
    #     If a default Cut/Engrave operation exists then the element is classified to it.
    #     Otherwise, a new operation of matching color and type is created.
    #     New White Engrave operations are created disabled by default.
    #
    #     SIMPLE RASTER CLASSIFICATION
    #     All existing raster ops are of the same color (or there are no existing raster ops)
    #
    #     In this case all raster operations will be assigned either to:
    #         A. all existing raster ops (if there are any); or
    #         B. to a new Default Raster operation we create in a similar way as vector elements
    #
    #     Because raster elements are all added to the same operations in pass 1 and without being
    #     grouped, the sequence of elements is retained by default, and no special handling is needed.
    #
    #     COMPLEX RASTER CLASSIFICATION
    #     There are existing raster ops of at least 2 different colours.
    #
    #     In this case we are going to try to match raster elements to raster operations by colour.
    #     But this is complicated as we need to keep overlapping raster elements together in the
    #     sae operations because raster images are generated within each operation.
    #
    #     So in this case we classify vector and special elements in a first pass,
    #     and then analyse and classify raster operations in a special second pass.
    #
    #     Because we have to analyse all raster elements together, when you load a new file
    #     Classify has to be called once with all elements in the file
    #     rather than on an element-by-element basis.
    #
    #     In the second pass, we do the following:
    #
    #     1.  Group rasters by whether they have overlapping bounding boxes.
    #         After this, if rasters are in separate groups then they are in entirely separate
    #         areas of the burn which do not overlap. Consequently, they can be allocated
    #         to different operations without causing incorrect results.
    #
    #         Note 1: It is difficult to ensure that elements are retained in sequence when doing
    #         grouping. Before adding to the raster operations, we sort back into the
    #         original element sequence.
    #
    #         Note 2: The current algorithm uses bounding-boxes. One edge case is to have two
    #         separate raster patterns of different colours that do NOT overlap but whose
    #         bounding-boxes DO overlap. In these cases they will both be allocated to the same
    #         raster Operations whereas they potentially could be allocated to different Operations.
    #
    #     2.  For each group of raster objects, determine whether there are existing Raster operations
    #         of the same colour as at least one element in the group.
    #         If any element in a group matches the color of an operation, then
    #         all the raster elements of the group will be added to that operation.
    #
    #     3.  If there are any raster elements that are not classified in this way, then:
    #         A)  If there are Default Raster Operation(s), then the remaining raster elements are
    #             allocated to those.
    #         B)  Otherwise, if there are any non-default raster operations that are empty and those
    #             raster operations are all the same colour, then the remaining raster operations
    #             will be allocated to those Raster operations.
    #         C)  Otherwise, a new Default Raster operation will be created and remaining
    #             Raster elements will be added to that.
    #
    #     LIMITATIONS: The current code does NOT do the following:
    #
    #     a.  Handle rasters in second or later files which overlap elements from earlier files which
    #         have already been classified into operations. It is assumed that if they happen to
    #         overlap that is coincidence. After all the files could have been added in a different
    #         order and then would have a different result.
    #     b.  Handle the reclassifications of single elements which have e.g. had their colour
    #         changed. (The multitude of potential use cases are many and varied, and difficult or
    #         impossible comprehensively to predict.)
    #
    #     It may be that we will need to:
    #
    #     1.  Use the total list of Shape / Text elements loaded in the `Elements Branch` sequence
    #         to keep elements in the correct sequence in an operation.
    #     2.  Handle cases where the user resequences elements by ensuring that a drag and drop
    #         of elements in the Elements branch of the tree is reflected in the sequence in Operations
    #         and vice versa. This could, however, get messy.
    #
    #
    #     @param elements: list of elements to classify.
    #     @param operations: operations list to classify into.
    #     @param add_op_function: function to add a new operation, because of a lack of classification options.
    #     @return:
    #     """
    #     debug = self.kernel.channel("classify", timestamp=True)
    #
    #     if self.legacy_classification:
    #         debug("classify: legacy")
    #         self.classify_legacy(elements, operations, add_op_function)
    #         return
    #
    #     if elements is None:
    #         return
    #
    #     if operations is None:
    #         operations = list(self.ops())
    #     if add_op_function is None:
    #         add_op_function = self.add_classify_op
    #
    #     reverse = self.classify_reverse
    #     # If reverse then we insert all elements into operations at the beginning rather than appending at the end
    #     # EXCEPT for Rasters which have to be in the correct sequence.
    #     element_pos = 0 if reverse else None
    #
    #     vector_ops = []
    #     raster_ops = []
    #     special_ops = []
    #     new_ops = []
    #     default_cut_ops = []
    #     default_engrave_ops = []
    #     default_raster_ops = []
    #     rasters_one_pass = None
    #
    #     for op in operations:
    #         if not op.type.startswith("op"):
    #             continue
    #         if op.type == "op console":
    #             continue
    #         if op.default:
    #             if op.type == "op cut":
    #                 default_cut_ops.append(op)
    #             if op.type == "op engrave":
    #                 default_engrave_ops.append(op)
    #             if op.type == "op raster":
    #                 default_raster_ops.append(op)
    #         if op.type in ("op cut", "op engrave"):
    #             vector_ops.append(op)
    #         elif op.type == "op raster":
    #             raster_ops.append(op)
    #             op_color = op.color.rgb if not op.default else "default"
    #             if rasters_one_pass is not False:
    #                 if rasters_one_pass is not None:
    #                     if str(rasters_one_pass) != str(op_color):
    #                         rasters_one_pass = False
    #                 else:
    #                     rasters_one_pass = op_color
    #         else:
    #             special_ops.append(op)
    #     if rasters_one_pass is not False:
    #         rasters_one_pass = True
    #     if debug:
    #         debug(
    #             "classify: ops: {passes}, {v} vectors, {r} rasters, {s} specials".format(
    #                 passes="one pass" if rasters_one_pass else "two passes",
    #                 v=len(vector_ops),
    #                 r=len(raster_ops),
    #                 s=len(special_ops),
    #             )
    #         )
    #
    #     elements_to_classify = []
    #     for element in elements:
    #         if element is None:
    #             debug("classify: not classifying -  element is None")
    #             continue
    #         if hasattr(element, "operation"):
    #             add_op_function(element)
    #             if debug:
    #                 debug(
    #                     "classify: added element as op: {op}".format(
    #                         op=str(op),
    #                     )
    #                 )
    #             continue
    #
    #         dot = is_dot(element)
    #         straight_line = is_straight_line(element)
    #         # print(element.stroke, element.fill, element.fill.alpha, is_straight_line, is_dot)
    #
    #         # Check for default vector operations
    #         element_vector = False
    #         if isinstance(element, (Shape, SVGText)) and not dot:
    #             # Vector if not filled
    #             if (
    #                 element.fill is None
    #                 or element.fill.rgb is None
    #                 or (element.fill.alpha is not None and element.fill.alpha == 0)
    #                 or straight_line
    #             ):
    #                 element_vector = True
    #
    #             # Not vector if grey stroke
    #             if (
    #                 element_vector
    #                 and element.stroke is not None
    #                 and element.stroke.rgb is not None
    #                 and element.stroke.red == element.stroke.green
    #                 and element.stroke.red == element.stroke.blue
    #             ):
    #                 element_vector = False
    #
    #         elements_to_classify.append(
    #             (
    #                 element,
    #                 element_vector,
    #                 dot,
    #                 straight_line,
    #             )
    #         )
    #     if debug:
    #         debug(
    #             "classify: elements: {e} elements to classify".format(
    #                 e=len(elements_to_classify),
    #             )
    #         )
    #
    #     # Handle edge cases
    #     # Convert raster elements with white fill and no raster elements behind to vector
    #     # Because the white fill is not hiding anything.
    #     for i, (
    #         element,
    #         element_vector,
    #         dot,
    #         straight_line,
    #     ) in enumerate(elements_to_classify):
    #         if (
    #             # Raster?
    #             not element_vector
    #             and isinstance(element, (Shape, SVGText))
    #             and not dot
    #             # White non-transparent fill?
    #             and element.fill is not None
    #             and element.fill.rgb is not None
    #             and element.fill.rgb == 0xFFFFFF
    #             and element.fill.alpha is not None
    #             and element.fill.alpha != 0
    #             # But not grey stroke?
    #             and (
    #                 element.stroke is None
    #                 or element.stroke.rgb is None
    #                 or element.stroke.red != element.stroke.green
    #                 or element.stroke.red != element.stroke.blue
    #             )
    #         ):
    #             bbox = element.bbox()
    #             # Now check for raster elements behind
    #             for e2 in elements_to_classify[:i]:
    #                 # Ignore vectors
    #                 if e2[1]:
    #                     continue
    #                 # If underneath then stick with raster?
    #                 if self.bbox_overlap(bbox, e2[0].bbox()):
    #                     break
    #             else:
    #                 # No rasters underneath - convert to vector
    #                 if debug:
    #                     debug(
    #                         "classify: edge-case: treating raster as vector: {label}".format(
    #                             label=self.element_label_id(element),
    #                         )
    #                     )
    #
    #                 element_vector = True
    #                 elements_to_classify[i] = (
    #                     element,
    #                     element_vector,
    #                     dot,
    #                     straight_line,
    #                 )
    #
    #     # Convert vector elements with element in front crossing the stroke to raster
    #     for i, (
    #         element,
    #         element_vector,
    #         dot,
    #         straight_line,
    #     ) in reversed_enumerate(elements_to_classify):
    #         if (
    #             element_vector
    #             and element.stroke is not None
    #             and element.stroke.rgb is not None
    #             and element.stroke.rgb != 0xFFFFFF
    #         ):
    #             bbox = element.bbox()
    #             color = element.stroke.rgb
    #             # Now check for raster elements in front whose path crosses over this path
    #             for e in elements_to_classify[i + 1 :]:
    #                 # Raster?
    #                 if e[1]:
    #                     continue
    #                 # Stroke or fill same colour?
    #                 if (
    #                     e[0].stroke is None
    #                     or e[0].stroke.rgb is None
    #                     or e[0].stroke.rgb != color
    #                 ) and (
    #                     e[0].fill is None
    #                     or e[0].fill.alpha is None
    #                     or e[0].fill.alpha == 0
    #                     or e[0].fill.rgb is None
    #                     or e[0].fill.rgb != color
    #                 ):
    #                     continue
    #                 # We have an element with a matching color
    #                 if self.bbox_overlap(bbox, e[0].bbox()):
    #                     # Rasters on top - convert to raster
    #                     if debug:
    #                         debug(
    #                             "classify: edge-case: treating vector as raster: {label}".format(
    #                                 label=self.element_label_id(element),
    #                             )
    #                         )
    #
    #                     element_vector = False
    #                     elements_to_classify[i] = (
    #                         element,
    #                         element_vector,
    #                         dot,
    #                         straight_line,
    #                     )
    #                     break
    #
    #     raster_elements = []
    #     for (
    #         element,
    #         element_vector,
    #         dot,
    #         straight_line,
    #     ) in elements_to_classify:
    #
    #         element_color = self.element_classify_color(element)
    #         if isinstance(element, (Shape, SVGText)) and (
    #             element_color is None or element_color.rgb is None
    #         ):
    #             if debug:
    #                 debug(
    #                     "classify: not classifying -  no stroke or fill color: {e}".format(
    #                         e=self.element_label_id(element, short=False),
    #                     )
    #                 )
    #             continue
    #
    #         element_added = False
    #         if dot or isinstance(element, SVGImage):
    #             for op in special_ops:
    #                 if (dot and op.type == "op dots") or (
    #                     isinstance(element, SVGImage) and op.type == "op image"
    #                 ):
    #                     op.add_reference(element.node, pos=element_pos)
    #                     element_added = True
    #                     break  # May only classify in one Dots or Image operation and indeed in one operation
    #         elif element_vector:
    #             # Vector op (i.e. no fill) with exact colour match to Raster Op will be rastered
    #             for op in raster_ops:
    #                 if (
    #                     op.color is not None
    #                     and op.color.rgb == element_color.rgb
    #                     and op not in default_raster_ops
    #                 ):
    #                     if not rasters_one_pass:
    #                         op.add_reference(element.node, pos=element_pos)
    #                     elif not element_added:
    #                         raster_elements.append((element, element.bbox()))
    #                     element_added = True
    #
    #             for op in vector_ops:
    #                 if (
    #                     op.color is not None
    #                     and op.color.rgb == element_color.rgb
    #                     and op not in default_cut_ops
    #                     and op not in default_engrave_ops
    #                 ):
    #                     op.add_reference(element.node, pos=element_pos)
    #                     element_added = True
    #             if (
    #                 element.stroke is None
    #                 or element.stroke.rgb is None
    #                 or element.stroke.rgb == 0xFFFFFF
    #             ):
    #                 if debug:
    #                     debug(
    #                         "classify: not classifying - white element at back: {e}".format(
    #                             e=self.element_label_id(element, short=False),
    #                         )
    #                     )
    #                 continue
    #
    #         elif rasters_one_pass:
    #             for op in raster_ops:
    #                 if op.color is not None and op.color.rgb == element_color.rgb:
    #                     op.add_reference(element.node, pos=element_pos)
    #                     element_added = True
    #         else:
    #             raster_elements.append((element, element.bbox()))
    #             continue
    #
    #         if element_added:
    #             continue
    #
    #         if element_vector:
    #             is_cut = Color.distance_sq("red", element_color) <= 18825
    #             if is_cut:
    #                 for op in default_cut_ops:
    #                     op.add_reference(element.node, pos=element_pos)
    #                     element_added = True
    #             else:
    #                 for op in default_engrave_ops:
    #                     op.add_reference(element.node, pos=element_pos)
    #                     element_added = True
    #         elif (
    #             rasters_one_pass
    #             and isinstance(element, (Shape, SVGText))
    #             and not dot
    #             and raster_ops
    #         ):
    #             for op in raster_ops:
    #                 op.add_reference(element.node, pos=element_pos)
    #             element_added = True
    #
    #         if element_added:
    #             continue
    #
    #         # Need to add a new operation to classify into
    #         op = None
    #         if dot:
    #             op = DotsOpNode(default=True)
    #             special_ops.append(op)
    #         elif isinstance(element, SVGImage):
    #             op = ImageOpNode(default=True)
    #             special_ops.append(op)
    #         elif isinstance(element, (Shape, SVGText)):
    #             if element_vector:
    #                 if (
    #                     is_cut
    #                 ):  # This will be initialised because criteria are same as above
    #                     op = CutOpNode(color=abs(element_color))
    #                 else:
    #                     op = EngraveOpNode(
    #                         operation="Engrave", color=abs(element_color)
    #                     )
    #                     if element_color == Color("white"):
    #                         op.output = False
    #                 vector_ops.append(op)
    #             elif rasters_one_pass:
    #                 op = RasterOpNode(color="Transparent", default=True)
    #                 default_raster_ops.append(op)
    #                 raster_ops.append(op)
    #         if op is not None:
    #             new_ops.append(op)
    #             add_op_function(op)
    #             # element cannot be added to op before op is added to operations - otherwise refelem is not created.
    #             op.add_reference(element.node, pos=element_pos)
    #             if debug:
    #                 debug(
    #                     "classify: added op: {op}".format(
    #                         op=str(op),
    #                     )
    #                 )
    #
    #     # End loop "for element in elements"
    #
    #     if rasters_one_pass:
    #         return
    #
    #     # Now deal with two-pass raster elements
    #     # It is ESSENTIAL that elements are added to operations in the same order as original.
    #     # The easiest way to ensure this is to create groups using a copy of raster_elements and
    #     # then ensure that groups have elements in the same order as in raster_elements.
    #     if debug:
    #         debug(
    #             "classify: raster pass two: {n} elements".format(
    #                 n=len(raster_elements),
    #             )
    #         )
    #
    #     # Debugging print statements have been left in as comments as this code can
    #     # be complex to debug and even print statements can be difficult to craft
    #
    #     # This is a list of groups, where each group is a list of tuples, each an element and its bbox.
    #     # Initial list has a separate group for each element.
    #     raster_groups = [[e] for e in raster_elements]
    #     raster_elements = [e[0] for e in raster_elements]
    #     # print("initial", list(map(lambda g: list(map(lambda e: e[0].id,g)), raster_groups)))
    #
    #     # We are using old-fashioned iterators because Python cannot cope with consolidating a list whilst iterating over it.
    #     for i in range(len(raster_groups) - 2, -1, -1):
    #         g1 = raster_groups[i]
    #         for j in range(len(raster_groups) - 1, i, -1):
    #             g2 = raster_groups[j]
    #             if self.group_elements_overlap(g1, g2):
    #                 # print("g1", list(map(lambda e: e[0].id,g1)))
    #                 # print("g2", list(map(lambda e: e[0].id,g2)))
    #
    #                 # if elements in the group overlap
    #                 # add the element tuples from group 2 to group 1
    #                 g1.extend(g2)
    #                 # and remove group 2
    #                 del raster_groups[j]
    #
    #                 # print("g1+g2", list(map(lambda e: e[0].id,g1)))
    #                 # print("reduced", list(map(lambda g: list(map(lambda e: e[0].id,g)), raster_groups)))
    #     if debug:
    #         debug(
    #             "classify: condensed to {n} raster groups".format(
    #                 n=len(raster_groups),
    #             )
    #         )
    #
    #     # Remove bbox and add element colour from groups
    #     # Change `list` to `groups` which are a list of tuples, each tuple being element and its classification color
    #     raster_groups = list(
    #         map(
    #             lambda g: tuple(((e[0], self.element_classify_color(e[0])) for e in g)),
    #             raster_groups,
    #         )
    #     )
    #
    #     # print("grouped", list(map(lambda g: list(map(lambda e: e[0].id,g)), raster_groups)))
    #
    #     # Add groups to operations of matching colour (and remove from list)
    #     # groups added to at least one existing raster op will not be added to default raster ops.
    #     groups_added = []
    #     for op in raster_ops:
    #         if (
    #             op not in default_raster_ops
    #             and op.color is not None
    #             and op.color.rgb is not None
    #         ):
    #             # Make a list of elements to add (same tupes)
    #             elements_to_add = []
    #             groups_count = 0
    #             for group in raster_groups:
    #                 for e in group:
    #                     if e[1].rgb == op.color.rgb:
    #                         # An element in this group matches op color
    #                         # So add elements to list
    #                         elements_to_add.extend(group)
    #                         if group not in groups_added:
    #                             groups_added.append(group)
    #                         groups_count += 1
    #                         break  # to next group
    #             if elements_to_add:
    #                 if debug:
    #                     debug(
    #                         "classify: adding {e} elements in {g} groups to {label}".format(
    #                             e=len(elements_to_add),
    #                             g=groups_count,
    #                             label=str(op),
    #                         )
    #                     )
    #                 # Create simple list of elements sorted by original element order
    #                 elements_to_add = sorted(
    #                     [e[0] for e in elements_to_add], key=raster_elements.index
    #                 )
    #                 for element in elements_to_add:
    #                     op.add_reference(element.node, pos=element_pos)
    #
    #     # Now remove groups added to at least one op
    #     for group in groups_added:
    #         raster_groups.remove(group)
    #
    #     if not raster_groups:  # added all groups
    #         return
    #
    #     #  Because groups don't matter further simplify back to a simple element_list
    #     elements_to_add = []
    #     for g in raster_groups:
    #         elements_to_add.extend(g)
    #     elements_to_add = sorted(
    #         [e[0] for e in elements_to_add], key=raster_elements.index
    #     )
    #     if debug:
    #         debug(
    #             "classify: {e} elements in {g} raster groups to add to default raster op(s)".format(
    #                 e=len(elements_to_add),
    #                 g=len(raster_groups),
    #             )
    #         )
    #
    #     # Remaining elements are added to one of the following groups of operations:
    #     # 1. to default raster ops if they exist; otherwise
    #     # 2. to empty raster ops if they exist and are all the same color; otherwise to
    #     # 3. a new default Raster operation.
    #     if not default_raster_ops:
    #         # Because this is a check for an empty operation, this functionality relies on all elements being classified at the same time.
    #         # If you add elements individually, after the first raster operation the empty ops will no longer be empty and a default Raster op will be created instead.
    #         default_raster_ops = [op for op in raster_ops if len(op.children) == 0]
    #         color = False
    #         for op in default_raster_ops:
    #             if op.color is None or op.color.rgb is None:
    #                 op_color = "None"
    #             else:
    #                 op_color = op.color.rgb
    #             if color is False:
    #                 color = op_color
    #             elif color != op_color:
    #                 default_raster_ops = []
    #                 break
    #     if not default_raster_ops:
    #         op = RasterOpNode(color="Transparent", default=True)
    #         default_raster_ops.append(op)
    #         add_op_function(op)
    #         if debug:
    #             debug(
    #                 "classify: default raster op added: {op}".format(
    #                     op=str(op),
    #                 )
    #             )
    #     else:
    #         if debug:
    #             for op in default_raster_ops:
    #                 debug(
    #                     "classify: default raster op selected: {op}".format(op=str(op))
    #                 )
    #
    #     for element in elements_to_add:
    #         for op in default_raster_ops:
    #             op.add_reference(element.node, pos=element_pos)

    # No longer used and still uses old element.node syntax
    # @staticmethod
    # def element_label_id(element, short=True):
    #     if element.node is None:
    #         if short:
    #             return element.id
    #         return f"{element.id}: {str(element)}"
    #     elif ":" in element.node.label and short:
    #         return element.node.label.split(":", 1)[0]
    #     else:
    #         return element.node.label

    @staticmethod
    def bbox_overlap(b1, b2):
        if b1[0] <= b2[2] and b1[2] >= b2[0] and b1[1] <= b2[3] and b1[3] >= b2[1]:
            return True
        return False

    def group_elements_overlap(self, g1, g2):
        for e1 in g1:
            for e2 in g2:
                if self.bbox_overlap(e1[1], e2[1]):
                    return True
        return False

    def remove_invalid_references(self):
        # If you load a file to an existing set of elements/operations,
        # references may become invalid as those link to non-existing operation nodes
        # print ("Will check for invalid references")
        for node in self.elems():
            to_be_deleted = []
            for idx, ref in enumerate(node._references):
                if ref is None:
                    # print (f"Empty reference for {node.type}.{node.id}.{node.display_label()}")
                    to_be_deleted.insert(0, idx)  # Last In First Out
                else:
                    try:
                        id = ref.parent  # This needs to exist
                        if id is None:
                            to_be_deleted.insert(0, idx)  # Last In First Out
                            # print (f"Empty parent reference for {node.type}.{node.id}.{node.display_label()}")
                    except AttributeError:
                        to_be_deleted.insert(0, idx)  # Last In First Out
                        # print (f"Invalid reference for {node.type}.{node.id}.{node.display_label()}")
            if to_be_deleted:
                # print (f"Will delete {len(to_be_deleted)} invalid references")
                for idx in to_be_deleted:
                    node._references.pop(idx)

    def remove_empty_groups(self):
        def descend_group(gnode):
            gres = 0
            gdel = 0
            to_be_deleted = []
            for cnode in gnode.children:
                if cnode.type in ("file", "group"):
                    cres, cdel = descend_group(cnode)
                    if cres == 0:
                        # Empty, so remove it
                        to_be_deleted.append(cnode)
                        gdel += cdel + 1
                    else:
                        gres += cres
                        gdel += cdel
                else:
                    gres += 1
            for cnode in to_be_deleted:
                cnode.remove_node(fast=True)
            return gres, gdel

        self.set_start_time("empty_groups")
        l1, d1 = descend_group(self.elem_branch)
        l2, d2 = descend_group(self.reg_branch)
        self.set_end_time("empty_groups", display=True, message=f"{l1} / {l2}")
        if d1:
            self.signal("rebuild_tree", "elements")
        if d2:
            self.signal("rebuild_tree", "regmarks")

    @staticmethod
    def element_classify_color(element: SVGElement):
        element_color = element.stroke
        if element_color is None or element_color.rgb is None:
            element_color = element.fill
        return element_color

    def load(self, pathname, **kwargs):
        kernel = self.kernel
        _ = kernel.translation

        _stored_elements = list(e for e in self.elems_nodes())
        self.clear_loaded_information()

        filename_to_process = pathname
        # Let's check first if we have a preprocessor
        # Use-case: if we identify functionalities in the file
        # which aren't supported by mk yet, we could ask a program
        # to convert these elements into supported artifacts
        # This may change the fileformat (and filename)
        preferred_loader = None
        if "preferred_loader" in kwargs:
            preferred_loader = kwargs["preferred_loader"]
        fn_name, fn_extension = os.path.splitext(filename_to_process)
        if fn_extension:
            preproc = self.lookup(f"preprocessor/{fn_extension}")
            # print (f"Preprocessor routine for preprocessor/{fn_extension}: {preproc}")
            if preproc is not None:
                filename_to_process = preproc(pathname)
                # print (f"Gave: {pathname}, received: {filename_to_process}")
        for loader, loader_name, sname in kernel.find("load"):
            for description, extensions, mimetype in loader.load_types():
                valid = False
                if str(filename_to_process).lower().endswith(extensions):
                    if preferred_loader is None or (preferred_loader == loader_name):
                        valid = True
                if valid:
                    self.set_start_time("load")
                    self.set_start_time("full_load")
                    # _("Load elements")
                    with self.undoscope("Load elements"):
                        try:
                            # We could stop the attachment to shadowtree for the duration
                            # of the load to avoid unnecessary actions, this will provide
                            # about 8% speed increase, but probably not worth the risk
                            # with attachment: 77.2 sec
                            # without attachm: 72.1 sec
                            # self.unlisten_tree(self)
                            elemcount_then = self.count_elems()
                            opcount_then = self.count_op()
                            self._loading_cleared = False
                            results = loader.load(
                                self, self, filename_to_process, **kwargs
                            )
                            elemcount_now = self.count_elems()
                            opcount_now = self.count_op()
                            self.remove_invalid_references()
                            self.remove_empty_groups()
                            for e in self.elems_nodes():
                                if e not in _stored_elements:
                                    self.added_elements.append(e)
                            # self.listen_tree(self)
                            self._filename = pathname
                            self.set_end_time("load", display=True)
                            self.signal("file;loaded")
                            if (
                                elemcount_now != elemcount_then
                                or opcount_then != opcount_now
                            ):
                                return True
                            elif results:
                                if not self._loading_cleared:
                                    self.signal(
                                        "warning",
                                        _("File is Empty"),
                                        _("File is Malformed"),
                                    )
                                return True

                        except (FileNotFoundError, PermissionError, OSError):
                            return False
                        except BadFileError as e:
                            kernel._console_channel(
                                _("File is Malformed") + ": " + str(e)
                            )
                            self.signal("warning", str(e), _("File is Malformed"))
                        except OSError:
                            return False

        return False

    def clear_loaded_information(self):
        self.added_elements.clear()

    def load_types(self, all=True):
        kernel = self.kernel
        _ = kernel.translation
        filetypes = []
        typedescriptors = []
        if all:
            filetypes.append(_("All valid types"))
            exts = []
            for loader, loader_name, sname in kernel.find("load"):
                for description, extensions, mimetype in loader.load_types():
                    for ext in extensions:
                        exts.append(f"*.{ext}")
            filetypes.append(";".join(exts))
            typedescriptors.append(None)
        for loader, loader_name, sname in kernel.find("load"):
            for description, extensions, mimetype in loader.load_types():
                exts = []
                for ext in extensions:
                    exts.append(f"*.{ext}")
                filetypes.append(f"{description} ({extensions[0]})")
                filetypes.append(";".join(exts))
                typedescriptors.append(loader_name)
        return "|".join(filetypes), typedescriptors

    def save(self, pathname, version="default", temporary=False):
        kernel = self.kernel
        for saver, save_name, sname in kernel.find("save"):
            for description, extension, mimetype, _version in saver.save_types():
                if pathname.lower().endswith(extension) and _version == version:
                    saver.save(self, pathname, version)
                    if not temporary:
                        self._filename = pathname
                        self.signal("file;saved")
                    return True
        return False

    def save_types(self):
        kernel = self.kernel
        filetypes = []
        for saver, save_name, sname in kernel.find("save"):
            for description, extension, mimetype, _version in saver.save_types():
                filetypes.append(f"{description} ({extension})")
                filetypes.append(f"*.{extension}")
        return "|".join(filetypes)

    def find_node(self, identifier):
        for node in self.flat():
            if node.id == identifier:
                return node
        return None

    def has_keyhole_subscribers(self, node):
        if node is None or node.id is None:
            return False
        rid = node.id
        if rid in self.registered_keyholes:
            return True
        return False

    def test_for_keyholes(self, node, method):
        if node is None or node.id is None:
            return
        relevant = getattr(node, "_acts_as_keyhole", False) or getattr(
            node, "keyhole_reference", None
        )
        if not relevant:
            return
        update_required = True
        if method == "translated":
            update_required = False
        elif node.type != "elem image":
            update_required = False
        if node.type == "elem image":
            if node.keyhole_reference is not None and update_required:
                self.remember_keyhole_nodes(node)
            return
        if not hasattr(node, "as_geometry"):
            return
        rid = node.id
        geom = node.as_geometry()
        if rid in self.registered_keyholes:
            nodelist = list(self.registered_keyholes[rid])
            # print (f"Update for node {node.type} [{rid}]: {len(nodelist)} images")
            if update_required:
                self.remember_keyhole_nodes(nodelist)
            for node in nodelist:
                node.set_keyhole(rid, geom=geom)

    def remove_keyhole(self, node):
        if node is None or node.id is None:
            return
        rid = node.id
        if rid in self.registered_keyholes:
            nodelist = list(self.registered_keyholes[rid])
            for node in nodelist:
                self.deregister_keyhole(rid, node, False)
            # That should lead to a full removal
        # We need a redraw/recalculation!
        self.signal("modified_by_tool")

    def deregister_keyhole(self, rid, node, reset_on_empty=True):
        if hasattr(node, "keyhole_reference"):
            node.keyhole_reference = None
            self.remember_keyhole_nodes(node)
        if rid in self.registered_keyholes:
            nodelist = list(self.registered_keyholes[rid])
            if node in nodelist:
                nodelist.remove(node)
            if len(nodelist):
                self.registered_keyholes[rid] = nodelist
            else:
                # No longer needed
                del self.registered_keyholes[rid]
                if reset_on_empty:
                    # Lets make it visible again
                    refnode = self.find_node(rid)
                    if refnode is not None:
                        refnode._acts_as_keyhole = False
                        if hasattr(refnode, "stroke") and refnode.stroke is None:
                            refnode.stroke = Color("blue")
                            if self.classify_on_color:
                                self.classify([refnode])

    def register_keyhole(self, refnode, node):
        rid = refnode.id
        if rid is None:
            raise ValueError(
                "You can't register a keyhole element that does not have an ID"
            )
        if not hasattr(refnode, "as_geometry"):
            raise ValueError("You can't register a keyhole that has not a geometry")
        if node.type != "elem image":
            raise ValueError("You can't link a keyhole to a non-image")
        refnode._acts_as_keyhole = True
        if rid in self.registered_keyholes:
            nodelist = list(self.registered_keyholes[rid])
            if not node in nodelist:
                nodelist.append(node)
        else:
            nodelist = (node,)
            if hasattr(refnode, "stroke"):
                refnode.stroke = None
            if hasattr(refnode, "fill"):
                refnode.fill = None
            # Remove it from all classifications
            for ref in list(refnode._references):
                ref.remove_node()

        self.registered_keyholes[rid] = nodelist
        node.set_keyhole(refnode.id, geom=refnode.as_geometry())
        self.remember_keyhole_nodes(node)

    def remember_keyhole_nodes(self, to_add):
        if isinstance(to_add, (list, tuple)):
            for node in to_add:
                if node not in self.remembered_keyhole_nodes:
                    self.remembered_keyhole_nodes.append(node)
        else:
            if to_add not in self.remembered_keyhole_nodes:
                self.remembered_keyhole_nodes.append(to_add)

    def forget_keyhole_nodes(self, to_add):
        if isinstance(to_add, (list, tuple)):
            for node in to_add:
                try:
                    self.remembered_keyhole_nodes.remove(node)
                except ValueError:
                    # Not in list
                    pass
        else:
            try:
                self.remembered_keyhole_nodes.remove(to_add)
            except ValueError:
                # Not in list
                pass

    def process_keyhole_updates(self, context=None):
        # print (f"Need to deal with {len(self.remembered_keyhole_nodes)} images")
        for node in self.remembered_keyhole_nodes:
            node.update(context)
        self.remembered_keyhole_nodes.clear()

    def do_image_update(self, node, context=None, delayed=False):
        if delayed:
            self.remember_keyhole_nodes(node)
        else:
            node.update(context)
            self.forget_keyhole_nodes(node)

    def simplify_node(self, node):
        """
        Delegate for older simplify node. This calls geomstr.simplify()

        @param node:
        @return:
        """
        if node.type not in ("elem path", "elem polyline"):
            # We can only simplify static geometries.
            return False, 0, 0
        try:
            g = node.as_geometry()
        except AttributeError:
            return
        before = g.index
        node.geometry = g.simplify()
        after = node.geometry.index
        changed = True

        return changed, before, after


def linearize_path(path, interp=50, point=False):
    import numpy as np

    current_polygon = []
    for subpath in path.as_subpaths():
        p = Path(subpath)
        s = []
        for segment in p:
            t = type(segment).__name__
            if t == "Move":
                s.append((segment.end[0], segment.end[1]))
            elif t in ("Line", "Close"):
                s.append((segment.end[0], segment.end[1]))
            else:
                s.extend(
                    (s[0], s[1]) for s in segment.npoint(np.linspace(0, 1, interp))
                )
        if point:
            s = list(map(Point, s))
        current_polygon.append(s)
    return current_polygon
