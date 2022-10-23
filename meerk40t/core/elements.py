import functools
import os.path
import re
from copy import copy
from math import cos, gcd, isinf, pi, sin, sqrt, tau
from os.path import realpath
from random import randint, shuffle

from meerk40t.core.exceptions import BadFileError
from meerk40t.kernel import CommandSyntaxError, ConsoleFunction, Service, Settings

from ..svgelements import (
    SVG_RULE_EVENODD,
    SVG_RULE_NONZERO,
    Angle,
    Close,
    Color,
    CubicBezier,
    Line,
    Matrix,
    QuadraticBezier,
    SVGElement,
    Viewbox,
)
from .cutcode import CutCode
from .element_types import *
from .node.elem_image import ImageNode
from .node.elem_path import PathNode
from .node.node import Fillrule, Linecap, Linejoin, Node
from .node.op_cut import CutOpNode
from .node.op_dots import DotsOpNode
from .node.op_engrave import EngraveOpNode
from .node.op_hatch import HatchOpNode
from .node.op_image import ImageOpNode
from .node.op_raster import RasterOpNode
from .node.rootnode import RootNode
from .node.util_console import ConsoleOperation
from .node.util_input import InputOperation
from .node.util_output import OutputOperation
from .node.util_wait import WaitOperation
from .units import UNITS_PER_INCH, UNITS_PER_PIXEL, Length
from .wordlist import Wordlist


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "plugins":
        from meerk40t.core import element_commands

        return [element_commands.plugin]
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
        kernel.register("format/util goto", "{enabled}{element_type} {adjust}")
        kernel.register("format/util origin", "{enabled}{element_type} {adjust}")
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
        kernel.register("format/reference", "*{reference}")
        kernel.register("format/group", "{element_type} {desc}({children} elems)")
        kernel.register("format/blob", "{element_type} {data_type}:{label} @{length}")
        kernel.register("format/file", "{element_type} {filename}")
        kernel.register("format/lasercode", "{element_type} {command_count}")
        kernel.register("format/cutcode", "{element_type}")
        kernel.register("format/branch ops", "{element_type} {loops}")
        kernel.register("format/branch elems", "{element_type}")
        kernel.register("format/branch reg", "{element_type}")
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
            {
                "attr": "classify_auto_inherit",
                "object": elements,
                "default": True,
                "type": bool,
                "label": _("Autoinherit for empty operation"),
                "tip": _(
                    "If you drag and drop an element into an operation to assign it there,"
                )
                + "\n"
                + _(
                    "then the op can (if this option is ticked) inherit the color from the element"
                )
                + "\n"
                + _(
                    "and adopt not only the dragged element but all elements with the same color"
                )
                + "\n"
                + _(
                    "- provided no elements are assigned to it yet (ie works only for an empty op)!"
                ),
                "page": "Classification",
                "section": "_30_GUI-Behaviour",
            },
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
                "page": "Scene",
                "section": "Operation",
            },
        ]
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
    elif lifecycle == "prestart":
        if hasattr(kernel.args, "input") and kernel.args.input is not None:
            # Load any input file
            elements = kernel.elements

            try:
                elements.load(realpath(kernel.args.input.name))
            except BadFileError as e:
                kernel._console_channel(_("File is Malformed") + ": " + str(e))
    elif lifecycle == "poststart":
        if hasattr(kernel.args, "output") and kernel.args.output is not None:
            # output the file you have at this point.
            elements = kernel.elements

            elements.save(realpath(kernel.args.output.name))


def reversed_enumerate(collection: list):
    for i in range(len(collection) - 1, -1, -1):
        yield i, collection[i]


OP_PRIORITIES = ["op dots", "op image", "op raster", "op engrave", "op cut", "op hatch"]


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
    """
    The elemental service is governs all the interactions with the various elements,
    operations, and filenodes. Handling structure change and selection, emphasis, and
    highlighting changes. The goal of this module is to make sure that the life cycle
    of the elements is strictly enforced. For example, every element that is removed
    must have had the .cache deleted. And anything selecting an element must propagate
    that information out to inform other interested modules.
    """

    def __init__(self, kernel, index=None, *args, **kwargs):
        Service.__init__(
            self, kernel, "elements" if index is None else f"elements{index}"
        )
        self._undo_stack = []
        self._undo_index = -1
        self._clipboard = {}
        self._clipboard_default = "0"

        self.note = None
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None
        self._emphasized_bounds_dirty = True
        self._tree = RootNode(self)
        self._save_restore_job = ConsoleFunction(self, "save_restore_point\n", times=1)

        self.setting(bool, "classify_reverse", False)
        self.setting(bool, "legacy_classification", False)
        self.setting(bool, "classify_fuzzy", False)
        self.setting(float, "classify_fuzzydistance", 100.0)
        self.setting(bool, "classify_autogenerate", True)
        self.setting(bool, "classify_autogenerate_both", True)
        self.setting(bool, "classify_inherit_stroke", False)
        self.setting(bool, "classify_inherit_fill", False)
        self.setting(bool, "classify_inherit_exclusive", True)
        self.setting(bool, "classify_auto_inherit", False)
        self.setting(bool, "classify_default", True)
        self.setting(bool, "op_show_default", False)
        self.setting(bool, "lock_allows_move", True)
        self.setting(bool, "auto_note", True)
        self.setting(bool, "uniform_svg", False)
        self.setting(float, "svg_ppi", 96.0)
        self.setting(bool, "operation_default_empty", True)

        self.op_data = Settings(self.kernel.name, "operations.cfg")
        self.pen_data = Settings(self.kernel.name, "penbox.cfg")

        self.penbox = {}
        self.load_persistent_penbox()

        self.wordlists = {"version": [1, self.kernel.version]}

        self._init_tree(kernel)
        direct = os.path.dirname(self.op_data._config_file)
        self.mywordlist = Wordlist(self.kernel.version, direct)
        self.load_persistent_operations("previous")

        ops = list(self.ops())
        if not len(ops) and not self.operation_default_empty:
            self.load_default(performclassify=False)

        self._default_stroke = None
        self._default_fill = None
        self._first_emphasized = None
        self._align_mode = "default"
        self._align_boundaries = None
        self._align_group = False
        self._align_stack = []

    @property
    def default_stroke(self):
        # We dont allow an empty stroke color as default (why not?!) -- Empty stroke colors are hard to see.
        if self._default_stroke is not None:
            return self._default_stroke
        return Color("blue")

    @default_stroke.setter
    def default_stroke(self, color):
        if isinstance(color, str):
            color = Color(str)
        self._default_stroke = color

    @property
    def default_fill(self):
        return self._default_fill

    @default_fill.setter
    def default_fill(self, color):
        if isinstance(color, str):
            color = Color(str)
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

    def load_persistent_penbox(self):
        settings = self.pen_data
        pens = settings.read_persistent_string_dict("pens", suffix=True)
        for pen in pens:
            length = int(pens[pen])
            box = list()
            for i in range(length):
                penbox = dict()
                settings.read_persistent_string_dict(f"{pen} {i}", penbox, suffix=True)
                box.append(penbox)
            self.penbox[pen] = box

    def save_persistent_penbox(self):
        sections = {}
        for section in self.penbox:
            sections[section] = len(self.penbox[section])
        self.pen_data.write_persistent_dict("pens", sections)
        for section in self.penbox:
            for i, p in enumerate(self.penbox[section]):
                self.pen_data.write_persistent_dict(f"{section} {i}", p)

    def index_range(self, index_string):
        """
        Parses index ranges in the form <idx>,<idx>-<idx>,<idx>
        @param index_string:
        @return:
        """
        indexes = list()
        for s in index_string.split(","):
            q = list(s.split("-"))
            if len(q) == 1:
                indexes.append(int(q[0]))
            else:
                start = int(q[0])
                end = int(q[1])
                if start > end:
                    for q in range(end, start + 1):
                        indexes.append(q)
                else:
                    for q in range(start, end + 1):
                        indexes.append(q)
        return indexes

    def length(self, v):
        return float(Length(v))

    def length_x(self, v):
        return float(Length(v, relative_length=self.device.width))

    def length_y(self, v):
        return float(Length(v, relative_length=self.device.height))

    def bounds(self, x0, y0, x1, y1):
        return (
            float(Length(x0, relative_length=self.device.width)),
            float(Length(y0, relative_length=self.device.height)),
            float(Length(x1, relative_length=self.device.width)),
            float(Length(y1, relative_length=self.device.height)),
        )

    def area(self, v):
        llx = Length(v, relative_length=self.device.width)
        lx = float(llx)
        if "%" in v:
            lly = Length(v, relative_length=self.device.height)
        else:
            lly = Length(f"1{llx._preferred_units}")
        ly = float(lly)
        return lx * ly

    def has_clipboard(self):
        """
        Returns the amount of elements in the clipboard
        """
        # TODO: this counts the clipboard not returns whether it exists
        destination = self._clipboard_default
        try:
            num = len(self._clipboard[destination])
        except (TypeError, KeyError):
            num = 0
        return num

    ### Operation tools

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
        #                 element attrib (ie stroke or fill)
        #               - anything else: leave all colors unchanged
        # attrib:       one of 'stroke', 'fill' to establish the source color
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
        if attrib is None:
            similar = False
        # print ("parameters:")
        # print ("Impose=%s, operation=%s" % (impose, op_assign) )
        # print ("similar=%s, attrib=%s" % (similar, attrib) )
        # print ("exclusive=%s" % exclusive )
        first_color = None
        target_color = None
        has_a_color = False
        # No need to check, if no one needs it...
        if impose == "to_elem":
            target_color = op_assign.color

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
            # Now that we have the colors lets iterate through all elements
            fuzzy = self.classify_fuzzy
            fuzzydistance = self.classify_fuzzydistance
            for n in self.flat(types=elem_nodes):
                addit = False
                if hasattr(n, attrib):
                    c = getattr(n, attrib)
                    try:
                        if c is not None and c.argb is not None:
                            pass
                        else:
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
        for n in data:
            if op_assign.drop(n, modify=False):
                if exclusive:
                    for ref in list(n._references):
                        ref.remove_node()
                op_assign.drop(n, modify=True)
                if impose == "to_elem" and target_color is not None:
                    if hasattr(n, attrib):
                        setattr(n, attrib, target_color)
                        needs_refresh = True
        # Refresh the operation so any changes like color materialize...
        self.signal("element_property_reload", op_assign)
        if needs_refresh:
            # We changed elems, so update the tree and the scene
            self.signal("element_property_update", data)
            self.signal("refresh_scene", "Scene")

    def get_information(self, elem, density=None):
        this_area = 0
        this_length = 0
        if elem is None:
            return this_area, this_length
        try:
            path = elem.as_path()
        except AttributeError:
            path = None
        if density is None:
            interpolation = 100
        else:
            interpolation = density

        subject_polygons = []
        if path is not None:
            this_length = path.length()

            from numpy import linspace

            for subpath in path.as_subpaths():
                subj = Path(subpath).npoint(linspace(0, 1, interpolation))

                subj.reshape((2, interpolation))
                s = list(map(Point, subj))
                subject_polygons.append(s)
        else:
            try:
                bb = elem.bounds
            except:
                # Even bounds failed, next element please
                return this_area, this_length
            s = [
                Point(bb[0], bb[1]),
                Point(bb[2], bb[1]),
                Point(bb[2], bb[3]),
                Point(bb[1], bb[3]),
            ]
            this_length = 2 * (bb[3] - bb[1]) + 2 * (bb[2] - bb[0])
            subject_polygons.append(s)

        if len(subject_polygons) > 0:
            idx = len(subject_polygons[0]) - 1
            if (
                subject_polygons[0][0].x != subject_polygons[0][idx].x
                or subject_polygons[0][0].y != subject_polygons[0][idx].y
            ):
                # not identical, so close the loop
                subject_polygons.append(
                    Point(subject_polygons[0][0].x, subject_polygons[0][0].y)
                )

        if len(subject_polygons) > 0:
            # idx = 0
            # for pt in subject_polygons[0]:
            #     if pt.x > 1.0E8 or pt.y > 1.0E8:
            #         print ("Rather high [%d]: x=%.1f, y=%.1f" % (idx, pt.x, pt.y))
            #     idx += 1
            idx = -1
            area_x_y = 0
            area_y_x = 0
            for pt in subject_polygons[0]:
                if pt is None or pt.x is None or pt.y is None:
                    continue
                if abs(pt.x) > 1.0e8 or abs(pt.y) > 1.0e8:
                    # this does not seem to be a valid coord...
                    continue
                idx += 1
                if idx > 0:
                    dx = pt.x - last_x
                    dy = pt.y - last_y
                    area_x_y += last_x * pt.y
                    area_y_x += last_y * pt.x
                last_x = pt.x
                last_y = pt.y
            this_area = 0.5 * abs(area_x_y - area_y_x)

        return this_area, this_length

    def align_elements(self, data, alignbounds, positionx, positiony, as_group):
        """

        @param data: elements to align
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

        if as_group != 0:
            individually = 2  # all elements as a total
        else:
            individually = 0
            for n in data:
                if n.type == "group":
                    individually = 1
                    break
        # Selection boundaries
        boundary_points = []
        for node in data:
            boundary_points.append(node.bounds)
        if not len(boundary_points):
            return
        left_edge = min([e[0] for e in boundary_points])
        top_edge = min([e[1] for e in boundary_points])
        right_edge = max([e[2] for e in boundary_points])
        bottom_edge = max([e[3] for e in boundary_points])
        if alignbounds is None:
            alignbounds = (left_edge, top_edge, right_edge, bottom_edge)
        # print(f"Alignbounds: {alignbounds[0]:.1f},{alignbounds[1]:.1f},{alignbounds[2]:.1f},{alignbounds[3]:.1f}")

        if individually in (0, 1):
            groupmatrix = ""
            groupdx = 0
            groupdy = 0
        else:
            groupdx, groupdy = calc_dx_dy()
            # print (f"Group move: {groupdx:.2f}, {groupdy:.2f}")
            groupmatrix = f"translate({groupdx}, {groupdy})"

        # Looping through all nodes with node.flat can provide
        # multiple times a single node, as you may loop through
        # files and groups nested into each other.
        # To avoid this we create a temporary set which by definition
        # can only contain unique members
        if individually == 0:
            s = set()
            for n in data:
                # print(f"Node to be resolved: {node.type}")
                s = s.union(n.flat(emphasized=True, types=elem_nodes))
        else:
            s = set()
            for n in data:
                # print(f"Node to be resolved: {node.type}")
                s = s.union(list([n]))
        for q in s:
            # print(f"Node to be treated: {q.type}")
            if individually in (0, 1):
                left_edge = q.bounds[0]
                top_edge = q.bounds[1]
                right_edge = q.bounds[2]
                bottom_edge = q.bounds[3]
                dx, dy = calc_dx_dy()
                matrix = f"translate({dx}, {dy})"
                # print (f"{individually} - {dx:.2f}, {dy:.2f}")
            else:
                dx = groupdx
                dy = groupdy
                matrix = groupmatrix
            if hasattr(q, "lock") and q.lock and not self.lock_allows_move:
                continue
            else:
                if q.type in ("group", "file"):
                    for c in q.flat(emphasized=True, types=elem_nodes):
                        if hasattr(c, "lock") and c.lock and not self.lock_allows_move:
                            continue
                        try:
                            c.matrix.post_translate(dx, dy)
                            c.modified()
                        except AttributeError:
                            pass
                            # print(f"Attribute Error for node {c.type} trying to assign {dx:.2f}, {dy:.2f}")
                else:
                    try:
                        # q.matrix *= matrix
                        q.matrix.post_translate(dx, dy)
                        q.modified()
                    except AttributeError:
                        pass
                        # print(f"Attribute Error for node {q.type} trying to assign {dx:.2f}, {dy:.2f}")
        self.signal("tree_changed")

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
                    if opatt == "passes":  # We need to look at one more info
                        if not node.passes_custom or value < 1:
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

    def _init_tree(self, kernel):

        _ = kernel.translation

        # --------------------------- TREE OPERATIONS ---------------------------

        def is_regmark(node):
            result = False
            try:
                if node._parent.type == "branch reg":
                    result = True
            except AttributeError:
                pass
            return result

        def has_changes(node):
            result = False
            try:
                if not node.matrix.is_identity():
                    result = True
            except AttributeError:
                # There was an error during check for matrix.is_identity
                pass
            return result

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: len(list(self.ops(emphasized=True))) == 1)
        @self.tree_operation(_("Operation properties"), node_type=op_nodes, help="")
        def operation_property(node, **kwargs):
            activate = self.kernel.lookup("function/open_property_window_for_node")
            if activate is not None:
                activate(node)

        @self.tree_separator_after()
        @self.tree_operation(_("Edit"), node_type="util console", help="")
        def edit_console_command(node, **kwargs):
            activate = self.kernel.lookup("function/open_property_window_for_node")
            if activate is not None:
                activate(node)

        @self.tree_separator_after()
        @self.tree_operation(
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

        @self.tree_separator_after()
        @self.tree_operation(_("Group properties"), node_type="group", help="")
        def group_property(node, **kwargs):
            activate = self.kernel.lookup("function/open_property_window_for_node")
            if activate is not None:
                activate(node)

        @self.tree_separator_after()
        @self.tree_operation(_("Text properties"), node_type="elem text", help="")
        def text_property(node, **kwargs):
            activate = self.kernel.lookup("function/open_property_window_for_node")
            if activate is not None:
                activate(node)

        @self.tree_separator_after()
        @self.tree_operation(_("Image properties"), node_type="elem image", help="")
        def image_property(node, **kwargs):
            activate = self.kernel.lookup("function/open_property_window_for_node")
            if activate is not None:
                activate(node)

        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_operation(
            _("Ungroup elements"), node_type=("group", "file"), help=""
        )
        def ungroup_elements(node, **kwargs):
            for n in list(node.children):
                node.insert_sibling(n)
            node.remove_node()  # Removing group/file node.

        @self.tree_conditional(lambda node: len(list(self.elems(emphasized=True))) > 0)
        @self.tree_operation(
            _("Elements in scene..."), node_type=elem_nodes, help="", enable=False
        )
        def element_label(node, **kwargs):
            return

        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_conditional(lambda node: len(list(self.elems(emphasized=True))) > 1)
        @self.tree_operation(_("Group elements"), node_type=elem_nodes, help="")
        def group_elements(node, **kwargs):
            group_node = node.parent.add(type="group", label="Group")
            for e in list(self.elems(emphasized=True)):
                group_node.append_child(e)

        @self.tree_conditional(
            lambda cond: len(
                list(self.flat(selected=True, cascade=False, types=op_nodes))
            )
            >= 1
        )
        @self.tree_operation(
            _("Remove all items from operation"), node_type=op_parent_nodes, help=""
        )
        def clear_all_op_entries(node, **kwargs):
            data = list()
            removed = False
            for item in list(self.flat(selected=True, cascade=False, types=op_nodes)):
                data.append(item)
            for item in data:
                removed = True
                item.remove_all_children()
            if removed:
                self.signal("tree_changed")

        @self.tree_conditional(lambda node: hasattr(node, "output"))
        @self.tree_operation(_("Enable/Disable ops"), node_type=op_nodes, help="")
        def toggle_n_operations(node, **kwargs):
            for n in self.ops(emphasized=True):
                if hasattr(n, "output"):
                    try:
                        n.output = not n.output
                        n.notify_update()
                    except AttributeError:
                        pass

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(_("Convert to Image"), node_type=op_parent_nodes, help="")
        def convert_operation_image(node, **kwargs):
            for n in list(self.ops(emphasized=True)):
                new_settings = dict(n.settings)
                new_settings["type"] = "op image"
                n.replace_node(keep_children=True, **new_settings)
            self.signal("rebuild_tree")

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(_("Convert to Raster"), node_type=op_parent_nodes, help="")
        def convert_operation_raster(node, **kwargs):
            for n in list(self.ops(emphasized=True)):
                new_settings = dict(n.settings)
                new_settings["type"] = "op raster"
                n.replace_node(keep_children=True, **new_settings)
            self.signal("rebuild_tree")

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(
            _("Convert to Engrave"), node_type=op_parent_nodes, help=""
        )
        def convert_operation_engrave(node, **kwargs):
            for n in list(self.ops(emphasized=True)):
                new_settings = dict(n.settings)
                new_settings["type"] = "op engrave"
                n.replace_node(keep_children=True, **new_settings)
            self.signal("rebuild_tree")

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(_("Convert to Cut"), node_type=op_parent_nodes, help="")
        def convert_operation_cut(node, **kwargs):
            for n in list(self.ops(emphasized=True)):
                new_settings = dict(n.settings)
                new_settings["type"] = "op cut"
                n.replace_node(keep_children=True, **new_settings)
            self.signal("rebuild_tree")

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(_("Convert to Hatch"), node_type=op_parent_nodes, help="")
        def convert_operation_hatch(node, **kwargs):
            for n in list(self.ops(emphasized=True)):
                new_settings = dict(n.settings)
                new_settings["type"] = "op hatch"
                n.replace_node(keep_children=True, **new_settings)
            self.signal("rebuild_tree")

        @self.tree_submenu(_("Convert operation"))
        @self.tree_operation(_("Convert to Dots"), node_type=op_parent_nodes, help="")
        def convert_operation_dots(node, **kwargs):
            for n in list(self.ops(emphasized=True)):
                new_settings = dict(n.settings)
                new_settings["type"] = "op dots"
                n.replace_node(keep_children=True, **new_settings)
            self.signal("rebuild_tree")

        @self.tree_submenu(_("RasterWizard"))
        @self.tree_operation(_("Set to None"), node_type="elem image", help="")
        def image_rasterwizard_apply_none(node, **kwargs):
            node.operations = []
            node.update(self)
            activate = self.kernel.lookup("function/open_property_window_for_node")
            if activate is not None:
                activate(node)
                self.signal("propupdate", node)

        @self.tree_submenu(_("RasterWizard"))
        @self.tree_values(
            "script", values=list(self.match("raster_script", suffix=True))
        )
        @self.tree_operation(_("Apply: {script}"), node_type="elem image", help="")
        def image_rasterwizard_apply(node, script=None, **kwargs):
            raster_script = self.lookup(f"raster_script/{script}")
            node.operations = raster_script
            node.update(self)
            activate = self.kernel.lookup("function/open_property_window_for_node")
            if activate is not None:
                activate(node)
                self.signal("propupdate", node)

        def radio_match(node, speed=0, **kwargs):
            return node.speed == float(speed)

        @self.tree_submenu(_("Speed"))
        @self.tree_radio(radio_match)
        @self.tree_values("speed", (50, 75, 100, 150, 200, 250, 300, 350))
        @self.tree_operation(
            _("{speed}mm/s"), node_type=("op raster", "op image"), help=""
        )
        def set_speed_raster(node, speed=150, **kwargs):
            node.speed = float(speed)
            self.signal("element_property_reload", node)

        @self.tree_submenu(_("Speed"))
        @self.tree_radio(radio_match)
        @self.tree_values("speed", (5, 10, 15, 20, 25, 30, 35, 40))
        @self.tree_operation(
            _("{speed}mm/s"),
            node_type=("op cut", "op engrave", "op hatch"),
            help="",
        )
        def set_speed_vector(node, speed=35, **kwargs):
            node.speed = float(speed)
            self.signal("element_property_reload", node)

        def radio_match(node, power=0, **kwargs):
            return node.power == float(power)

        @self.tree_submenu(_("Power"))
        @self.tree_radio(radio_match)
        @self.tree_values("power", (100, 250, 333, 500, 667, 750, 1000))
        @self.tree_operation(
            _("{power}ppi"),
            node_type=("op cut", "op raster", "op image", "op engrave", "op hatch"),
            help="",
        )
        def set_power(node, power=1000, **kwargs):
            node.power = float(power)
            self.signal("element_property_reload", node)

        def radio_match(node, dpi=100, **kwargs):
            return node.dpi == dpi

        @self.tree_submenu(_("DPI"))
        @self.tree_radio(radio_match)
        @self.tree_values("dpi", (100, 250, 333, 500, 667, 750, 1000))
        @self.tree_operation(
            _("DPI {dpi}"),
            node_type=("op raster", "elem image"),
            help=_("Change dpi values"),
        )
        def set_step_n(node, dpi=1, **kwargs):
            node.dpi = dpi
            self.signal("element_property_reload", node)

        def radio_match(node, passvalue=1, **kwargs):
            return (node.passes_custom and passvalue == node.passes) or (
                not node.passes_custom and passvalue == 1
            )

        @self.tree_submenu(_("Set operation passes"))
        @self.tree_radio(radio_match)
        @self.tree_iterate("passvalue", 1, 10)
        @self.tree_operation(
            _("Passes {passvalue}"), node_type=op_parent_nodes, help=""
        )
        def set_n_passes(node, passvalue=1, **kwargs):
            node.passes = passvalue
            node.passes_custom = passvalue != 1
            self.signal("element_property_reload", node)

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

        @self.tree_submenu(_("Burn Direction"))
        @self.tree_radio(radio_match_direction)
        @self.tree_values("raster_direction", values=get_direction_values())
        @self.tree_operation(
            "{raster_direction}",
            node_type=("op raster", "op image"),
            help="",
        )
        def set_direction(node, raster_direction="", **kwargs):
            values = get_direction_values()
            for idx, key in enumerate(values):
                if key == raster_direction:
                    node.raster_direction = idx
                    self.signal("element_property_reload", node)
                    break

        def get_swing_values():
            return (
                _("Bidirectional"),
                _("Unidirectional"),
            )

        def radio_match_swing(node, raster_swing="", **kwargs):
            values = get_swing_values()
            for idx, key in enumerate(values):
                if key == raster_swing:
                    return node.raster_swing == idx
            return False

        @self.tree_submenu(_("Directional Raster"))
        @self.tree_radio(radio_match_swing)
        @self.tree_values("raster_swing", values=get_swing_values())
        @self.tree_operation(
            "{raster_swing}",
            node_type=("op raster", "op image"),
            help="",
        )
        def set_swing(node, raster_swing="", **kwargs):
            values = get_swing_values()
            for idx, key in enumerate(values):
                if key == raster_swing:
                    node.raster_swing = idx
                    self.signal("element_property_reload", node)
                    break

        @self.tree_separator_before()
        @self.tree_operation(
            _("Execute operation(s)"),
            node_type=op_nodes,
            help=_("Execute Job for the selected operation(s)."),
        )
        def execute_job(node, **kwargs):
            self.set_node_emphasis(node, True)
            self("plan0 clear copy-selected\n")
            self("window open ExecuteJob 0\n")

        @self.tree_separator_after()
        @self.tree_operation(
            _("Simulate operation(s)"),
            node_type=op_nodes,
            help=_("Run simulation for the selected operation(s)"),
        )
        def compile_and_simulate(node, **kwargs):
            self.set_node_emphasis(node, True)
            self("plan0 copy-selected preprocess validate blob preopt optimize\n")
            self("window open Simulation 0\n")

        @self.tree_operation(_("Clear all"), node_type="branch ops", help="")
        def clear_all(node, **kwargs):
            self("operation* delete\n")

        @self.tree_operation(
            _("Clear unused"),
            node_type="branch ops",
            help=_("Clear operations without children"),
        )
        def clear_unused(node, **kwargs):
            to_delete = []
            for op in self.ops():
                # print (f"{op.type}, refs={len(op._references)}, children={len(op._children)}")
                if len(op._children) == 0:
                    to_delete.append(op)
            if len(to_delete) > 0:
                self.remove_operations(to_delete)
                self.signal("tree_changed")

        @self.tree_operation(_("Clear all"), node_type="branch elems", help="")
        def clear_all_ops(node, **kwargs):
            self("element* delete\n")
            self.elem_branch.remove_all_children()

        @self.tree_operation(_("Clear all"), node_type="branch reg", help="")
        def clear_all_regmarks(node, **kwargs):
            self.reg_branch.remove_all_children()

        # ==========
        # REMOVE MULTI (Tree Selected)
        # ==========
        # Calculate the amount of selected nodes in the tree:
        # If there are ops selected then they take precedence
        # and will only be counted

        @self.tree_conditional(
            lambda cond: len(
                list(self.flat(selected=True, cascade=False, types="reference"))
            )
            >= 1
        )
        @self.tree_calc(
            "ecount",
            lambda i: len(
                list(self.flat(selected=True, cascade=False, types="reference"))
            ),
        )
        @self.tree_operation(
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

        # @self.tree_conditional(
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
        # @self.tree_calc(
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
        # @self.tree_calc(
        #     "rcount",
        #     lambda i: len(
        #         list(self.flat(selected=True, cascade=False, types=("reference")))
        #     ),
        # )
        # @self.tree_calc(
        #     "eloc",
        #     lambda s: "operations"
        #     if len(list(self.flat(selected=True, cascade=False, types=operate_nodes)))
        #     > 0
        #     else "element-list",
        # )
        # @self.tree_operation(
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
        @self.tree_conditional(lambda node: not node.lock)
        @self.tree_conditional(
            lambda cond: len(
                list(self.flat(selected=True, cascade=False, types=elem_nodes))
            )
            == 1
        )
        @self.tree_operation(
            _("Delete element '{name}' fully"),
            node_type=elem_nodes,
            help="",
        )
        def remove_type_elem(node, **kwargs):
            if hasattr(node, "lock") and node.lock:
                pass
            else:
                node.remove_node()
                self.set_emphasis(None)

        @self.tree_conditional(
            lambda cond: len(
                list(self.flat(selected=True, cascade=False, types=op_nodes))
            )
            == 1
        )
        @self.tree_operation(
            _("Delete operation '{name}' fully"),
            node_type=op_nodes,
            help="",
        )
        def remove_type_op(node, **kwargs):

            node.remove_node()
            self.set_emphasis(None)
            self.signal("operation_removed")

        def contains_no_locked_items():
            nolock = True
            for e in list(self.flat(selected=True, cascade=True)):
                if hasattr(e, "lock") and e.lock:
                    nolock = False
                    break
            return nolock

        @self.tree_conditional(lambda cond: contains_no_locked_items())
        @self.tree_conditional(
            lambda cond: len(
                list(self.flat(selected=True, cascade=False, types=("file", "group")))
            )
            == 1
        )
        @self.tree_operation(
            _("Delete group '{name}' and all its child-elements fully"),
            node_type="group",
            help="",
        )
        def remove_type_grp(node, **kwargs):
            node.remove_node()
            self.set_emphasis(None)

        @self.tree_conditional(lambda cond: contains_no_locked_items())
        @self.tree_conditional(
            lambda cond: len(
                list(self.flat(selected=True, cascade=False, types=("file", "group")))
            )
            == 1
        )
        @self.tree_operation(
            _("Remove loaded file '{name}' and all its child-elements fully"),
            node_type="file",
            help="",
        )
        def remove_type_file(node, **kwargs):
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
            _("Delete {ecount} operations"),
            node_type=(
                "op cut",
                "op raster",
                "op image",
                "op engrave",
                "op dots",
                "op hatch",
                "util console",
                "util wait",
                "util home",
                "util goto",
                "util origin",
                "util output",
                "util input",
                "lasercode",
                "cutcode",
                "blob",
            ),
            help="",
        )
        def remove_n_ops(node, **kwargs):
            self("operation delete\n")

        # ==========
        # REMOVE ELEMENTS
        # ==========
        # More than one, special case == 1 already dealt with
        @self.tree_conditional(lambda node: len(list(self.elems(emphasized=True))) > 1)
        @self.tree_calc("ecount", lambda i: len(list(self.elems(emphasized=True))))
        @self.tree_operation(
            _("Delete {ecount} elements, as selected in scene"),
            node_type=elem_group_nodes,
            help="",
        )
        def remove_n_elements(node, **kwargs):
            self("element delete\n")

        # ==========
        # CONVERT TREE OPERATIONS
        # ==========
        @self.tree_operation(
            _("Convert to Cutcode"),
            node_type="lasercode",
            help="",
        )
        def lasercode2cut(node, **kwargs):
            node.replace_node(CutCode.from_lasercode(node.commands), type="cutcode")

        @self.tree_conditional_try(
            lambda node: kernel.lookup(f"parser/{node.data_type}") is not None
        )
        @self.tree_operation(
            _("Convert to Elements"),
            node_type="blob",
            help="Convert blob to elements ",
        )
        def blob2path(node, **kwargs):
            parser_class = kernel.lookup(f"parser/{node.data_type}")
            parser = parser_class()
            parser.parse(node.data, self)
            return True

        @self.tree_conditional_try(lambda node: hasattr(node, "as_cutobjects"))
        @self.tree_operation(
            _("Convert to Cutcode"),
            node_type="blob",
            help="",
        )
        def blob2cut(node, **kwargs):
            node.replace_node(node.as_cutobjects(), type="cutcode")

        @self.tree_operation(
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

        @self.tree_submenu(_("Clone reference"))
        @self.tree_operation(_("Make 1 copy"), node_type=("reference",), help="")
        def clone_single_element_op(node, **kwargs):
            clone_element_op(node, copies=1, **kwargs)

        @self.tree_submenu(_("Clone reference"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(
            _("Make {copies} copies"), node_type=("reference",), help=""
        )
        def clone_element_op(node, copies=1, **kwargs):
            nodes = list(self.flat(selected=True, cascade=False, types="reference"))
            for snode in nodes:
                index = snode.parent.children.index(snode)
                for i in range(copies):
                    snode.parent.add_reference(snode.node, pos=index)
                snode.modified()
            self.signal("tree_changed")

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_operation(
            _("Reverse subitems order"),
            node_type=(
                "op cut",
                "op raster",
                "op image",
                "op engrave",
                "op dots",
                "op hatch",
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

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: self.classify_autogenerate)
        @self.tree_operation(
            _("Refresh classification"),
            node_type="branch ops",
            help=_("Reclassify elements and create operations if necessary"),
        )
        def refresh_clasifications_1(node, **kwargs):
            self.remove_elements_from_operations(list(self.elems()))
            self.classify(list(self.elems()))
            self.signal("refresh_tree", list(self.flat(types="reference")))

        @self.tree_conditional(lambda node: not self.classify_autogenerate)
        @self.tree_operation(
            _("Refresh classification"),
            node_type="branch ops",
            help=_("Reclassify elements and use only existing operations"),
        )
        def refresh_clasifications_2(node, **kwargs):
            self.remove_elements_from_operations(list(self.elems()))
            self.classify(list(self.elems()))
            self.signal("refresh_tree", list(self.flat(types="reference")))

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: not self.classify_autogenerate)
        @self.tree_operation(
            _("Refresh ... (incl autogeneration)"),
            node_type="branch ops",
            help=_("Reclassify elements and create operations if necessary"),
        )
        def refresh_clasifications_3(node, **kwargs):
            previous = self.classify_autogenerate
            self.classify_autogenerate = True
            self.remove_elements_from_operations(list(self.elems()))
            self.classify(list(self.elems()))
            self.classify_autogenerate = previous
            self.signal("refresh_tree", list(self.flat(types="reference")))

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
                for d in self.op_data.section_set()
                if d not in materials and d != "previous"
            ]
            union.extend(materials)
            return union

        def difference_materials_saved():
            secs = self.op_data.section_set()
            difference = [m for m in materials if m not in secs]
            return difference

        @self.tree_submenu(_("Load"))
        @self.tree_values("opname", values=self.op_data.section_set)
        @self.tree_operation("{opname}", node_type="branch ops", help="")
        def load_ops(node, opname, **kwargs):
            self(f"material load {opname}\n")

        @self.tree_separator_before()
        @self.tree_submenu(_("Load"))
        @self.tree_operation(_("Other/Blue/Red"), node_type="branch ops", help="")
        def default_classifications(node, **kwargs):
            self.load_default(performclassify=True)

        @self.tree_submenu(_("Load"))
        @self.tree_separator_after()
        @self.tree_operation(_("Basic"), node_type="branch ops", help="")
        def basic_classifications(node, **kwargs):
            self.load_default2(performclassify=True)

        @self.tree_submenu(_("Save"))
        @self.tree_values("opname", values=self.op_data.section_set)
        @self.tree_operation("{opname}", node_type="branch ops", help="")
        def save_materials(node, opname="saved", **kwargs):
            self(f"material save {opname}\n")

        @self.tree_separator_before()
        @self.tree_submenu(_("Save"))
        @self.tree_prompt("opname", _("Name to store current operations under?"))
        @self.tree_operation("New", node_type="branch ops", help="")
        def save_material_custom(node, opname, **kwargs):
            self(f"material save {opname.replace(' ', '_')}\n")

        @self.tree_submenu(_("Delete"))
        @self.tree_values("opname", values=self.op_data.section_set)
        @self.tree_operation("{opname}", node_type="branch ops", help="")
        def remove_ops(node, opname="saved", **kwargs):
            self(f"material delete {opname}\n")

        @self.tree_separator_before()
        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Image"), node_type="branch ops", help="")
        def append_operation_image(node, pos=None, **kwargs):
            self.add_op(ImageOpNode(), pos=pos)

        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Raster"), node_type="branch ops", help="")
        def append_operation_raster(node, pos=None, **kwargs):
            self.add_op(RasterOpNode(), pos=pos)

        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Engrave"), node_type="branch ops", help="")
        def append_operation_engrave(node, pos=None, **kwargs):
            self.add_op(EngraveOpNode(), pos=pos)

        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Cut"), node_type="branch ops", help="")
        def append_operation_cut(node, pos=None, **kwargs):
            self.add_op(CutOpNode(), pos=pos)

        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Hatch"), node_type="branch ops", help="")
        def append_operation_hatch(node, pos=None, **kwargs):
            self.add_op(HatchOpNode(), pos=pos)

        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Dots"), node_type="branch ops", help="")
        def append_operation_dots(node, pos=None, **kwargs):
            self.add_op(DotsOpNode(), pos=pos)

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Home"), node_type="branch ops", help="")
        def append_operation_home(node, pos=None, **kwargs):
            self.op_branch.add(
                type="util home",
                pos=pos,
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(
            _("Append Return to Origin"), node_type="branch ops", help=""
        )
        def append_operation_goto(node, pos=None, **kwargs):
            self.op_branch.add(
                type="util goto",
                pos=pos,
                x=0,
                y=0,
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(
            _("Append Set Origin"),
            node_type="branch ops",
            help="",
        )
        def append_operation_setorigin(node, pos=None, **kwargs):
            self.op_branch.add(
                type="util origin",
                pos=pos,
                x=None,
                y=None,
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Beep"), node_type="branch ops", help="")
        def append_operation_beep(node, pos=None, **kwargs):
            self.op_branch.add(
                type="util console",
                pos=pos,
                command="beep",
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Interrupt"), node_type="branch ops", help="")
        def append_operation_interrupt(node, pos=None, **kwargs):
            self.op_branch.add(
                type="util console",
                pos=pos,
                command='interrupt "Spooling was interrupted"',
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_prompt(
            "wait_time", _("Wait for how long (in seconds)?"), data_type=float
        )
        @self.tree_operation(_("Append Wait"), node_type="branch ops", help="")
        def append_operation_wait(node, wait_time, pos=None, **kwargs):
            self.op_branch.add(
                type="util wait",
                pos=pos,
                wait=wait_time,
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Output"), node_type="branch ops", help="")
        def append_operation_output(node, pos=None, **kwargs):
            self.op_branch.add(
                type="util output",
                pos=pos,
                output_mask=0,
                output_value=0,
                output_message=None,
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Input"), node_type="branch ops", help="")
        def append_operation_input(node, pos=None, **kwargs):
            self.op_branch.add(
                type="util input",
                pos=pos,
                input_mask=0,
                input_value=0,
                input_message=None,
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(
            _("Append Home/Beep/Interrupt"), node_type="branch ops", help=""
        )
        def append_operation_home_beep_interrupt(node, **kwargs):
            append_operation_home(node, **kwargs)
            append_operation_beep(node, **kwargs)
            append_operation_interrupt(node, **kwargs)

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(
            _("Append Origin/Beep/Interrupt"), node_type="branch ops", help=""
        )
        def append_operation_origin_beep_interrupt(node, **kwargs):
            append_operation_goto(node, **kwargs)
            append_operation_beep(node, **kwargs)
            append_operation_interrupt(node, **kwargs)

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Shutdown"), node_type="branch ops", help="")
        def append_operation_shutdown(node, pos=None, **kwargs):
            self.op_branch.add(
                type="util console",
                pos=pos,
                command="quit",
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_prompt("opname", _("Console command to append to operations?"))
        @self.tree_operation(_("Append Console"), node_type="branch ops", help="")
        def append_operation_custom(node, opname, pos=None, **kwargs):
            self.op_branch.add(
                type="util console",
                pos=pos,
                command=opname,
            )

        @self.tree_operation(
            _("Reclassify operations"), node_type="branch elems", help=""
        )
        def reclassify_operations(node, **kwargs):
            elems = list(self.elems())
            self.remove_elements_from_operations(elems)
            self.classify(list(self.elems()))
            self.signal("refresh_tree")

        @self.tree_operation(
            _("Remove all assignments from operations"),
            node_type="branch elems",
            help=_("Any existing assignment of elements to operations will be removed"),
        )
        def remove_all_assignments(node, **kwargs):
            for node in self.elems():
                for ref in list(node._references):
                    ref.remove_node()
            self.signal("tree_changed")

        @self.tree_operation(
            _("Duplicate operation(s)"),
            node_type=op_nodes,
            help=_("duplicate operation nodes"),
        )
        def duplicate_operation(node, **kwargs):
            operations = self._tree.get(type="branch ops").children
            for op in self.ops(emphasized=True):
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
            self.signal("tree_changed")

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_submenu(_("Passes"))
        @self.tree_operation(
            _("Add 1 pass"),
            node_type=("op image", "op engrave", "op cut", "op hatch"),
            help="",
        )
        def add_1_pass(node, **kwargs):
            add_n_passes(node, copies=1, **kwargs)

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_submenu(_("Passes"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(
            _("Add {copies} passes"),
            node_type=("op image", "op engrave", "op cut", "op hatch"),
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

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_operation(
            _("Duplicate elements 1 time"),
            node_type=("op image", "op engrave", "op cut"),
            help="",
        )
        def dup_1_copy(node, **kwargs):
            dup_n_copies(node, copies=1, **kwargs)

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(
            _("Duplicate elements {copies} times"),
            node_type=("op image", "op engrave", "op cut"),
            help="",
        )
        def dup_n_copies(node, copies=1, **kwargs):
            add_nodes = list(node.children)
            add_nodes *= copies
            for n in add_nodes:
                node.add_reference(n.node)
            self.signal("refresh_tree")

        @self.tree_operation(
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
                    node = list(self.ops(emphasized=True))[-1]
                operations = self._tree.get(type="branch ops").children
                return operations.index(node) + 1
            except (ValueError, IndexError):
                return None

        @self.tree_separator_before()
        @self.tree_submenu(_("Insert operation"))
        @self.tree_operation(_("Add Image"), node_type=op_nodes, help="")
        def add_operation_image(node, **kwargs):
            append_operation_image(node, pos=add_after_index(node), **kwargs)

        @self.tree_submenu(_("Insert operation"))
        @self.tree_operation(_("Add Raster"), node_type=op_nodes, help="")
        def add_operation_raster(node, **kwargs):
            append_operation_raster(node, pos=add_after_index(node), **kwargs)

        @self.tree_submenu(_("Insert operation"))
        @self.tree_operation(_("Add Engrave"), node_type=op_nodes, help="")
        def add_operation_engrave(node, **kwargs):
            append_operation_engrave(node, pos=add_after_index(node), **kwargs)

        @self.tree_submenu(_("Insert operation"))
        @self.tree_operation(_("Add Cut"), node_type=op_nodes, help="")
        def add_operation_cut(node, **kwargs):
            append_operation_cut(node, pos=add_after_index(node), **kwargs)

        @self.tree_submenu(_("Insert operation"))
        @self.tree_operation(_("Add Hatch"), node_type=op_nodes, help="")
        def add_operation_hatch(node, **kwargs):
            append_operation_hatch(node, pos=add_after_index(node), **kwargs)

        @self.tree_submenu(_("Insert operation"))
        @self.tree_operation(_("Add Dots"), node_type=op_nodes, help="")
        def add_operation_dots(node, **kwargs):
            append_operation_dots(node, pos=add_after_index(node), **kwargs)

        @self.tree_submenu(_("Insert special operation(s)"))
        @self.tree_operation(_("Add Home"), node_type=op_nodes, help="")
        def add_operation_home(node, **kwargs):
            append_operation_home(node, pos=add_after_index(node), **kwargs)

        @self.tree_submenu(_("Insert special operation(s)"))
        @self.tree_operation(_("Add Return to Origin"), node_type=op_nodes, help="")
        def add_operation_origin(node, **kwargs):
            append_operation_goto(node, pos=add_after_index(node), **kwargs)

        @self.tree_submenu(_("Insert special operation(s)"))
        @self.tree_operation(_("Add Beep"), node_type=op_nodes, help="")
        def add_operation_beep(node, **kwargs):
            append_operation_beep(node, pos=add_after_index(node), **kwargs)

        @self.tree_submenu(_("Insert special operation(s)"))
        @self.tree_operation(_("Add Interrupt"), node_type=op_nodes, help="")
        def add_operation_interrupt(node, **kwargs):
            append_operation_interrupt(node, pos=add_after_index(node), **kwargs)

        @self.tree_submenu(_("Insert special operation(s)"))
        @self.tree_prompt(
            "wait_time", _("Wait for how long (in seconds)?"), data_type=float
        )
        @self.tree_operation(_("Add Wait"), node_type=op_nodes, help="")
        def add_operation_wait(node, wait_time, **kwargs):
            append_operation_wait(
                node, wait_time=wait_time, pos=add_after_index(node), **kwargs
            )

        @self.tree_submenu(_("Insert special operation(s)"))
        @self.tree_operation(_("Add Output"), node_type=op_nodes, help="")
        def add_operation_output(node, **kwargs):
            append_operation_output(node, pos=add_after_index(node), **kwargs)

        @self.tree_submenu(_("Insert special operation(s)"))
        @self.tree_operation(_("Add Input"), node_type=op_nodes, help="")
        def add_operation_input(node, **kwargs):
            append_operation_input(node, pos=add_after_index(node), **kwargs)

        @self.tree_submenu(_("Insert special operation(s)"))
        @self.tree_operation(_("Add Home/Beep/Interrupt"), node_type=op_nodes, help="")
        def add_operation_home_beep_interrupt(node, **kwargs):
            pos = add_after_index(node)
            append_operation_home(node, pos=pos, **kwargs)
            if pos:
                pos += 1
            append_operation_beep(node, pos=pos, **kwargs)
            if pos:
                pos += 1
            append_operation_interrupt(node, pos=pos, **kwargs)

        @self.tree_submenu(_("Insert special operation(s)"))
        @self.tree_operation(
            _("Add Origin/Beep/Interrupt"), node_type=op_nodes, help=""
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

        @self.tree_operation(_("Reload '{name}'"), node_type="file", help="")
        def reload_file(node, **kwargs):
            filepath = node.filepath
            node.remove_node()
            self.load(filepath)

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

                open_in_shell(f"open '{normalized}'")
            elif system == "Windows":
                from os import startfile as open_in_shell

                open_in_shell(f'"{normalized}"')
            else:
                from os import system as open_in_shell

                open_in_shell(f"xdg-open '{normalized}'")

        def get_values():
            return [o for o in self.ops() if o.type.startswith("op")]

        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_submenu(_("Assign Operation"))
        @self.tree_values("op_assign", values=get_values)
        @self.tree_operation("{op_assign}", node_type=elem_nodes, help="")
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

        @self.tree_separator_before()
        @self.tree_submenu(_("Assign Operation"))
        @self.tree_operation(
            _("Remove all assignments from operations"),
            node_type=elem_group_nodes,
            help=_(
                "Any existing assignment of this element to operations will be removed"
            ),
        )
        def remove_assignments(node, **kwargs):
            def rem_node(rnode):
                # recursively remove assignments...
                if rnode.type in ("file", "group"):
                    for cnode in list(rnode._children):
                        rem_node(cnode)
                else:
                    for ref in list(rnode._references):
                        ref.remove_node()

            rem_node(node)
            self.signal("tree_changed")

        @self.tree_separator_before()
        @self.tree_submenu(_("Assign Operation"))
        @self.tree_check(exclusive_match)
        @self.tree_operation(
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

        @self.tree_separator_before()
        @self.tree_submenu(_("Assign Operation"))
        @self.tree_check(stroke_match)
        @self.tree_operation(
            _("Inherit stroke and classify similar"),
            node_type=elem_nodes,
            help=_("Operation will inherit element stroke color"),
        )
        def set_assign_option_stroke(node, **kwargs):
            self.classify_inherit_stroke = not self.classify_inherit_stroke
            # Poor mans radio
            if self.classify_inherit_stroke:
                self.classify_inherit_fill = False

        def fill_match(node, **kwargs):
            return self.classify_inherit_fill

        @self.tree_submenu(_("Assign Operation"))
        @self.tree_check(fill_match)
        @self.tree_operation(
            _("Inherit fill and classify similar"),
            node_type=elem_nodes,
            help=_("Operation will inherit element fill color"),
        )
        def set_assign_option_fill(node, **kwargs):
            self.classify_inherit_fill = not self.classify_inherit_fill
            # Poor mans radio
            if self.classify_inherit_fill:
                self.classify_inherit_stroke = False

        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_operation(_("Make 1 copy"), node_type=elem_nodes, help="")
        def duplicate_element_1(node, **kwargs):
            duplicate_element_n(node, copies=1, **kwargs)

        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(_("Make {copies} copies"), node_type=elem_nodes, help="")
        def duplicate_element_n(node, copies, **kwargs):
            copy_nodes = list()
            dx = self.length_x("3mm")
            dy = self.length_y("3mm")
            delta_wordlist = 1
            for e in list(self.elems(emphasized=True)):
                delta_wordlist = 0
                for n in range(copies):
                    delta_wordlist += 1
                    copy_node = copy(e)
                    copy_node.matrix *= Matrix.translate((n + 1) * dx, (n + 1) * dy)
                    had_optional = False
                    for optional in ("wxfont", "mktext", "mkfont", "mkfontsize"):
                        if hasattr(e, optional):
                            had_optional = True
                            setattr(copy_node, optional, getattr(e, optional))
                    if self.copy_increases_wordlist_references and hasattr(e, "text"):
                        copy_node.text = self.wordlist_delta(e.text, delta_wordlist)
                    elif self.copy_increases_wordlist_references and hasattr(
                        e, "mktext"
                    ):
                        copy_node.mktext = self.wordlist_delta(e.mktext, delta_wordlist)
                    node.parent.add_node(copy_node)
                    if had_optional:
                        for property_op in self.kernel.lookup_all("path_updater/.*"):
                            property_op(self.kernel.root, copy_node)

                    copy_nodes.append(copy_node)

            if self.classify_new:
                self.classify(copy_nodes)

            self.set_emphasis(None)

        def has_wordlist(node):
            result = False
            txt = ""
            if hasattr(node, "text") and node.text is not None:
                txt = node.text
            if hasattr(node, "mktext") and node.mktext is not None:
                txt = node.mktext
            # Very stupid, but good enough
            if "{" in txt and "}" in txt:
                result = True
            return result

        @self.tree_conditional(lambda node: has_wordlist(node))
        @self.tree_operation(
            _("Increase Wordlist-Reference"),
            node_type=(
                "elem text",
                "elem path",
            ),
            help="Adjusts the reference value for a wordlist, ie {name} to {name#+1}",
        )
        def wlist_plus(node, **kwargs):
            delta_wordlist = 1
            if hasattr(node, "text"):
                node.text = self.wordlist_delta(node.text, delta_wordlist)
                node.altered()
                self.signal("element_property_update", [node])
            elif hasattr(node, "mktext"):
                node.mktext = self.wordlist_delta(node.mktext, delta_wordlist)
                for property_op in self.kernel.lookup_all("path_updater/.*"):
                    property_op(self.kernel.root, node)
                self.signal("element_property_update", [node])

        @self.tree_conditional(lambda node: has_wordlist(node))
        @self.tree_operation(
            _("Decrease Wordlist-Reference"),
            node_type=(
                "elem text",
                "elem path",
            ),
            help="Adjusts the reference value for a wordlist, ie {name#+3} to {name#+2}",
        )
        def wlist_minus(node, **kwargs):
            delta_wordlist = -1
            if hasattr(node, "text"):
                node.text = self.wordlist_delta(node.text, delta_wordlist)
                node.altered()
                self.signal("element_property_update", [node])
            elif hasattr(node, "mktext"):
                node.mktext = self.wordlist_delta(node.mktext, delta_wordlist)
                for property_op in self.kernel.lookup_all("path_updater/.*"):
                    property_op(self.kernel.root, node)
                self.signal("element_property_update", [node])

        @self.tree_submenu(_("Outline element(s)..."))
        @self.tree_iterate("offset", 1, 10)
        @self.tree_operation(
            _("...with {offset}mm distance"),
            node_type=elem_nodes,
            help="",
        )
        def make_outlines(node, offset=1, **kwargs):
            self(f"outline {offset}mm\n")
            self.signal("refresh_tree")

        def has_vectorize(node):
            result = False
            make_vector = self.lookup("render-op/make_vector")
            if make_vector:
                result = True
            return result

        @self.tree_conditional(lambda node: has_vectorize(node))
        @self.tree_operation(
            _("Trace bitmap"),
            node_type=(
                "elem text",
                "elem image",
            ),
            help="Vectorize the given element",
        )
        def trace_bitmap(node, **kwargs):
            self("vectorize\n")

        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_operation(
            _("Convert to path"),
            node_type=(
                "elem ellipse",
                "elem path",
                "elem polyline",
                "elem rect",
                "elem line",
            ),
            help="",
        )
        def convert_to_path(node, **kwargs):
            oldstuff = []
            for attrib in ("stroke", "fill", "stroke_width", "stroke_scaled"):
                if hasattr(node, attrib):
                    oldval = getattr(node, attrib, None)
                    oldstuff.append([attrib, oldval])
            try:
                path = node.as_path()
            except AttributeError:
                return
            newnode = node.replace_node(path=path, type="elem path")
            for item in oldstuff:
                setattr(newnode, item[0], item[1])
            newnode.altered()

        @self.tree_submenu(_("Flip"))
        @self.tree_separator_before()
        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_conditional_try(lambda node: not node.lock)
        @self.tree_operation(
            _("Horizontally"),
            node_type=elem_group_nodes,
            help=_("Mirror Horizontally"),
        )
        def mirror_elem(node, **kwargs):
            bounds = node.bounds
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self(f"scale -1 1 {center_x} {center_y}\n")

        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_submenu(_("Flip"))
        @self.tree_conditional_try(lambda node: not node.lock)
        @self.tree_operation(
            _("Vertically"),
            node_type=elem_group_nodes,
            help=_("Flip Vertically"),
        )
        def flip_elem(node, **kwargs):
            bounds = node.bounds
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self(f"scale 1 -1 {center_x} {center_y}\n")

        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_conditional_try(lambda node: not node.lock)
        @self.tree_submenu(_("Scale"))
        @self.tree_iterate("scale", 25, 1, -1)
        @self.tree_calc("scale_percent", lambda i: f"{(600.0 / float(i)):.2f}")
        @self.tree_operation(
            _("Scale {scale_percent}%"),
            node_type=elem_group_nodes,
            help=_("Scale Element"),
        )
        def scale_elem_amount(node, scale, **kwargs):
            scale = 6.0 / float(scale)
            bounds = node.bounds
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self(f"scale {scale} {scale} {center_x} {center_y}\n")

        # @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_conditional_try(lambda node: not node.lock)
        @self.tree_submenu(_("Rotate"))
        @self.tree_values(
            "angle",
            (
                180,
                135,
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
        @self.tree_operation(_("Rotate {angle}°"), node_type=elem_group_nodes, help="")
        def rotate_elem_amount(node, angle, **kwargs):
            turns = float(angle) / 360.0
            bounds = node.bounds
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self(f"rotate {turns}turn {center_x} {center_y}\n")
            self.signal("ext-modified")

        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_conditional(lambda node: has_changes(node))
        @self.tree_conditional_try(lambda node: not node.lock)
        @self.tree_operation(
            _("Reify User Changes"), node_type=elem_group_nodes, help=""
        )
        def reify_elem_changes(node, **kwargs):
            self("reify\n")
            self.signal("ext-modified")

        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_conditional_try(lambda node: not node.lock)
        @self.tree_operation(_("Break Subpaths"), node_type="elem path", help="")
        def break_subpath_elem(node, **kwargs):
            self("element subpath\n")

        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_conditional(lambda node: has_changes(node))
        @self.tree_conditional_try(lambda node: not node.lock)
        @self.tree_operation(
            _("Reset user changes"), node_type=elem_group_nodes, help=""
        )
        def reset_user_changes(node, copies=1, **kwargs):
            self("reset\n")
            self.signal("ext-modified")

        @self.tree_operation(
            _("Merge items"),
            node_type="group",
            help=_("Merge this node's children into 1 path."),
        )
        def merge_elements(node, **kwargs):
            self("element merge\n")
            # Is the group now empty? --> delete
            if len(node.children) == 0:
                node.remove_node()

        @self.tree_conditional(lambda node: node.lock)
        @self.tree_separator_before()
        @self.tree_operation(
            _("Unlock element, allows manipulation"), node_type=elem_nodes, help=""
        )
        def element_unlock_manipulations(node, **kwargs):
            self("element unlock\n")

        @self.tree_conditional(lambda node: not node.lock)
        @self.tree_separator_before()
        @self.tree_operation(
            _("Lock elements, prevents manipulations"), node_type=elem_nodes, help=""
        )
        def element_lock_manipulations(node, **kwargs):
            self("element lock\n")

        @self.tree_conditional(lambda node: node.type == "branch reg")
        @self.tree_separator_before()
        @self.tree_operation(
            _("Toggle visibility of regmarks"), node_type="branch reg", help=""
        )
        def toggle_visibility(node, **kwargs):
            self.signal("toggle_regmarks")

        @self.tree_conditional(lambda node: is_regmark(node))
        @self.tree_separator_before()
        @self.tree_operation(
            _("Move back to elements"), node_type=elem_group_nodes, help=""
        )
        def move_back(node, **kwargs):
            # Drag and Drop
            signal_needed = False
            drop_node = self.elem_branch
            data = list()
            for item in list(self.regmarks()):
                if item.selected:
                    data.append(item)
            for item in data:
                drop_node.drop(item)
                signal_needed = True
            if signal_needed:
                self.signal("tree_changed")

        @self.tree_conditional(lambda node: not is_regmark(node))
        @self.tree_separator_before()
        @self.tree_operation(_("Move to regmarks"), node_type=elem_group_nodes, help="")
        def move_to_regmark(node, **kwargs):
            # Drag and Drop
            signal_needed = False
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
                signal_needed = True
            if signal_needed:
                self.signal("tree_changed")
            drop_node.drop(node)
            self.signal("tree_changed")

        @self.tree_conditional(lambda node: not node.lock)
        @self.tree_conditional_try(lambda node: not node.lock)
        @self.tree_operation(_("Actualize pixels"), node_type="elem image", help="")
        def image_actualize_pixels(node, **kwargs):
            self("image resample\n")

        @self.tree_conditional(lambda node: not node.lock)
        @self.tree_submenu(_("Z-depth divide"))
        @self.tree_iterate("divide", 2, 10)
        @self.tree_operation(
            _("Divide into {divide} images"), node_type="elem image", help=""
        )
        def image_zdepth(node, divide=1, **kwargs):
            if node.image.mode != "RGBA":
                node.image = node.image.convert("RGBA")
            band = 255 / divide
            for i in range(0, divide):
                threshold_min = i * band
                threshold_max = threshold_min + band
                self(f"image threshold {threshold_min} {threshold_max}\n")

        @self.tree_conditional(lambda node: node.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Unlock manipulations"), node_type="elem image", help="")
        def image_unlock_manipulations(node, **kwargs):
            self("image unlock\n")

        @self.tree_conditional(lambda node: not node.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Lock manipulations"), node_type="elem image", help="")
        def image_lock_manipulations(node, **kwargs):
            self("image lock\n")

        @self.tree_conditional(lambda node: not node.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Dither to 1 bit"), node_type="elem image", help="")
        def image_dither(node, **kwargs):
            self("image dither\n")

        @self.tree_conditional(lambda node: not node.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Invert image"), node_type="elem image", help="")
        def image_invert(node, **kwargs):
            self("image invert\n")

        @self.tree_conditional(lambda node: not node.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Mirror horizontal"), node_type="elem image", help="")
        def image_mirror(node, **kwargs):
            self("image mirror\n")

        @self.tree_conditional(lambda node: not node.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Flip vertical"), node_type="elem image", help="")
        def image_flip(node, **kwargs):
            self("image flip\n")

        @self.tree_conditional(lambda node: not node.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Rotate 90° CW"), node_type="elem image", help="")
        def image_cw(node, **kwargs):
            self("image cw\n")

        @self.tree_conditional(lambda node: not node.lock)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Rotate 90° CCW"), node_type="elem image", help="")
        def image_ccw(node, **kwargs):
            self("image ccw\n")

        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Save output.png"), node_type="elem image", help="")
        def image_save(node, **kwargs):
            self("image save output.png\n")

        @self.tree_conditional(lambda node: len(node.children) > 0)
        @self.tree_separator_before()
        @self.tree_operation(
            _("Expand all children"),
            node_type=(
                "op cut",
                "op raster",
                "op image",
                "op engrave",
                "op dots",
                "op hatch",
                "branch elems",
                "branch ops",
                "branch reg",
                "group",
                "file",
                "root",
            ),
            help="Expand all children of this given node.",
        )
        def expand_all_children(node, **kwargs):
            node.notify_expand()

        @self.tree_conditional(lambda node: len(node.children) > 0)
        @self.tree_operation(
            _("Collapse all children"),
            node_type=(
                "op cut",
                "op raster",
                "op image",
                "op engrave",
                "op dots",
                "op hatch",
                "branch elems",
                "branch ops",
                "branch reg",
                "group",
                "file",
                "root",
            ),
            help="Collapse all children of this given node.",
        )
        def collapse_all_children(node, **kwargs):
            node.notify_collapse()

    def service_detach(self, *args, **kwargs):
        self.unlisten_tree(self)

    def service_attach(self, *args, **kwargs):
        self.listen_tree(self)

    def shutdown(self, *args, **kwargs):
        self.save_persistent_operations("previous")
        self.save_persistent_penbox()
        self.pen_data.write_configuration()
        self.op_data.write_configuration()
        for e in self.flat():
            e.unregister()

    def save_persistent_operations(self, name):
        settings = self.op_data
        settings.clear_persistent(name)
        for i, op in enumerate(self.ops()):
            if hasattr(op, "allow_save"):
                if not op.allow_save():
                    continue
            section = f"{name} {i:06d}"
            settings.write_persistent(section, "type", op.type)
            op.save(settings, section)

        settings.write_configuration()

    def clear_persistent_operations(self, name):
        settings = self.op_data
        subitems = list(settings.derivable(name))
        for section in subitems:
            settings.clear_persistent(section)
        settings.write_configuration()

    def load_persistent_operations(self, name):
        self.clear_operations()
        settings = self.op_data
        operation_branch = self._tree.get(type="branch ops")
        for section in list(settings.derivable(name)):
            op_type = settings.read_persistent(str, section, "type")
            # That should not happen, but it happens nonetheless...
            # So recover gracefully
            try:
                op = operation_branch.add(type=op_type)
            except (AttributeError, RuntimeError):
                print(f"That should not happen, but ops contained: '{op_type}'")
                continue

            op.load(settings, section)
        if len(list(self.elems())) > 0:
            self.classify(list(self.elems()))

    def emphasized(self, *args):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None

    def altered(self, *args):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None
        # TODO: Reenable when Undo Completed
        if self.setting(bool, "developer_mode", False):
            self.schedule(self._save_restore_job)

    def modified(self, *args):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None
        # TODO: Reenable when Undo Completed
        if self.setting(bool, "developer_mode", False):
            self.schedule(self._save_restore_job)

    def listen_tree(self, listener):
        self._tree.listen(listener)

    def unlisten_tree(self, listener):
        self._tree.unlisten(listener)

    def load_default(self, performclassify=True):
        self.clear_operations()
        self.add_op(
            ImageOpNode(
                color="black",
                speed=140.0,
                power=1000.0,
                raster_step=3,
            )
        )
        self.add_op(RasterOpNode())
        self.add_op(EngraveOpNode())
        self.add_op(CutOpNode())
        if performclassify:
            self.classify(list(self.elems()))
        self.signal("tree_changed")

    def load_default2(self, performclassify=True):
        self.clear_operations()
        self.add_op(
            ImageOpNode(
                color="black",
                speed=140.0,
                power=1000.0,
                raster_step=3,
            )
        )
        self.add_op(RasterOpNode())
        self.add_op(EngraveOpNode(color="blue"))
        self.add_op(EngraveOpNode(color="green"))
        self.add_op(EngraveOpNode(color="magenta"))
        self.add_op(EngraveOpNode(color="cyan"))
        self.add_op(EngraveOpNode(color="yellow"))
        self.add_op(CutOpNode())
        if performclassify:
            self.classify(list(self.elems()))
        self.signal("tree_changed")

    def tree_operations_for_node(self, node):
        for func, m, sname in self.find("tree", node.type, ".*"):
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
                "name": str(node.name)
                if (hasattr(node, "name") and node.name is not None)
                else str(node.label),
                "label": str(node.name)
                if (hasattr(node, "name") and node.name is not None)
                else str(node.label),
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
                if hasattr(func, "check") and func.check is not None:
                    try:
                        func.check_state = func.check(node, **func_dict)
                    except:
                        func.check_state = False
                else:
                    func.check_state = None
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
    def tree_check(check_function):
        def decor(func):
            func.check = check_function
            return func

        return decor

    @staticmethod
    def tree_submenu(submenu):
        def decor(func):
            func.submenu = submenu
            return func

        return decor

    @staticmethod
    def tree_prompt(attr, prompt, data_type=str):
        def decor(func):
            func.user_prompt.append(
                {
                    "attr": attr,
                    "prompt": prompt,
                    "type": data_type,
                }
            )
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

    def tree_operation(self, name, node_type=None, help=None, enable=True, **kwargs):
        def decorator(func):
            @functools.wraps(func)
            def inner(node, **ik):
                returned = func(node, **ik, **kwargs)
                return returned

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
            inner.user_prompt = list()
            inner.calcs = list()
            inner.values = [0]
            inner.enabled = enable
            registered_name = inner.__name__

            for _in in ins:
                p = f"tree/{_in}/{registered_name}"
                if p in self._registered:
                    raise NameError(
                        f"A function of this name was already registered: {p}"
                    )
                self.register(p, inner)
            return inner

        return decorator

    def validate_ids(self):
        idx = 1
        uid = {}
        missing = list()
        for node in self.flat():
            if node.id in uid:
                # ID already used. Clear.
                node.id = None
            if node.id is None:
                # Unused IDs need new IDs
                missing.append(node)
            else:
                # Set this ID as used.
                uid[node.id] = node
        for m in missing:
            while f"meerk40t:{idx}" in uid:
                idx += 1
            m.id = f"meerk40t:{idx}"
            uid[m.id] = m

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
        operations = self._tree.get(type="branch ops")
        for item in operations.flat(depth=1, **kwargs):
            if item.type.startswith("branch") or item.type.startswith("ref"):
                continue
            yield item

    def elems(self, **kwargs):
        elements = self._tree.get(type="branch elems")
        for item in elements.flat(types=elem_nodes, **kwargs):
            yield item

    def elems_nodes(self, depth=None, **kwargs):
        elements = self._tree.get(type="branch elems")
        for item in elements.flat(types=elem_group_nodes, depth=depth, **kwargs):
            yield item

    def regmarks(self, **kwargs):
        elements = self._tree.get(type="branch reg")
        for item in elements.flat(types=elem_nodes, **kwargs):
            yield item

    def regmarks_nodes(self, depth=None, **kwargs):
        elements = self._tree.get(type="branch reg")
        for item in elements.flat(types=elem_group_nodes, depth=depth, **kwargs):
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
        operation_branch = self._tree.get(type="branch ops")
        operation_branch.add_node(op, pos=pos)
        self.signal("add_operation", op)

    def add_ops(self, adding_ops):
        operation_branch = self._tree.get(type="branch ops")
        items = []
        for op in adding_ops:
            operation_branch.add_node(op)
            items.append(op)
        self.signal("add_operation", items)
        return items

    def add_elems(self, adding_elements, classify=False, branch_type="branch elems"):
        """
        Add multiple svg elements to the tree.

        @param adding_elements:
        @param classify:
        @param branch_type:
        @return:
        """
        branch = self._tree.get(type=branch_type)
        items = []
        ct = 0
        for element in adding_elements:
            ct += 1
            node_type = get_type_from_element(element)
            if node_type:
                items.append(branch.add(element, type=node_type))
        if branch_type == "branch elems":
            self.signal("element_added", adding_elements)
        elif branch_type == "branch reg":
            self.signal("regmark_added", adding_elements)
        if classify:
            self.classify(adding_elements)
        return items

    def clear_operations(self):
        operations = self._tree.get(type="branch ops")
        operations.remove_all_children()
        if hasattr(operations, "loop_continuous"):
            operations.loop_continuous = False
            operations.loop_enabled = False
            operations.loop_n = 1
            self.signal("element_property_update", operations)
        self.signal("operation_removed")

    def clear_elements(self):
        elements = self._tree.get(type="branch elems")
        elements.remove_all_children()

    def clear_regmarks(self):
        elements = self._tree.get(type="branch reg")
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

    # def drag_and_drop(self, dragging_nodes, drop_node, inheritance_mode="auto", inherit_stroke = True, inherit_fill = True):

    #     print ("elements d+d called")
    #     if inheritance_mode.lower() == "auto":
    #     elif inheritance_mode.lower() =
    #     if inherit_stroke is None:
    #         inh_stroke = False
    #     else:
    #         inh_stroke = inherit_stroke
    #     if inherit_fill is None:
    #         inh_fill = False
    #     else:
    #         inh_fill = inherit_fill

    #     data = dragging_nodes
    #     success = False
    #     special_occasion = False
    #     if drop_node.type.startswith("op"):
    #         if len(drop_node.children) == 0 and self.classify_auto_inherit:
    #             # only for empty operations!
    #             # Let's establish the colors first
    #             first_color_stroke = None
    #             first_color_fill = None
    #             # Look for the first element that has stroke/fill
    #             for n in data:
    #                 if first_color_stroke is None and hasattr(n, "stroke") and n.stroke is not None and n.stroke.argb is not None:
    #                     first_color_stroke = n.stroke
    #                 if first_color_fill is None and hasattr(n, "fill") and n.fill is not None and n.fill.argb is not None:
    #                     first_color_fill = n.fill
    #                 canbreak = first_color_fill is not None or first_color_stroke is not None
    #                 if canbreak:
    #                     break
    #             if hasattr(drop_node, "color") and (first_color_fill is not None or first_color_stroke is not None):
    #                 # Well if you have both options, then you get that
    #                 # color that is present, precedence for fill
    #                 if first_color_fill is not None:
    #                     col = first_color_fill
    #                     if hasattr(drop_node, "add_color_attribute"): # not true for image
    #                         drop_node.add_color_attribute("fill")
    #                         drop_node.remove_color_attribute("stroke")
    #                 else:
    #                     col = first_color_stroke
    #                     if hasattr(drop_node, "add_color_attribute"): # not true for image
    #                         drop_node.add_color_attribute("stroke")
    #                         drop_node.remove_color_attribute("fill")
    #                 drop_node.color = col

    #             # Now that we have the colors lets iterate through all elements
    #             fuzzy = self.classify_fuzzy
    #             fuzzydistance = self.classify_fuzzydistance
    #             for n in self.flat(types=elem_nodes):
    #                 addit = False
    #                 if inh_stroke and first_color_stroke is not None and hasattr(n, "stroke") and n.stroke is not None and n.stroke.argb is not None:
    #                     if fuzzy:
    #                         if Color.distance(first_color_stroke, n.stroke) <= fuzzydistance:
    #                             addit = True
    #                     else:
    #                         if n.stroke == first_color_stroke:
    #                             addit = True
    #                 if inh_fill and first_color_fill is not None and hasattr(n, "fill") and n.fill is not None and n.fill.argb is not None:
    #                     if fuzzy:
    #                         if Color.distance(first_color_fill, n.fill) <= fuzzydistance:
    #                             addit = True
    #                     else:
    #                         if n.fill == first_color_fill:
    #                             addit = True
    #                 # print ("Checked %s and will addit=%s" % (n.type, addit))
    #                 if addit and n not in data:
    #                     data.append(n)
    #     for drag_node in data:
    #         if drop_node is drag_node:
    #             continue
    #         if drop_node.drop(drag_node, modify=False):
    #             if special_occasion:
    #                 for ref in list(drag_node._references):
    #                     ref.remove_node()
    #             drop_node.drop(drag_node, modify=True)
    #             success = True

    #     # Refresh the target node so any changes like color materialize...
    #     self.signal("element_property_reload", drop_node)
    #     return success

    def drag_and_drop(self, dragging_nodes, drop_node):
        data = dragging_nodes
        success = False
        special_occasion = False
        for drag_node in data:
            if drop_node is drag_node:
                continue
            if drop_node.drop(drag_node, modify=False):
                if special_occasion:
                    for ref in list(drag_node._references):
                        ref.remove_node()
                drop_node.drop(drag_node, modify=True)
                success = True

        # Refresh the target node so any changes like color materialize...
        self.signal("element_property_reload", drop_node)
        return success

    def remove_nodes(self, node_list):
        for node in node_list:
            for n in node.flat():
                n._mark_delete = True
                for ref in list(n._references):
                    ref._mark_delete = True
        for n in reversed(list(self.flat())):
            if not hasattr(n, "_mark_delete"):
                continue
            if n.type in ("root", "branch elems", "branch reg", "branch ops"):
                continue
            n.remove_node(children=False, references=False)

    def remove_elements(self, element_node_list):
        for elem in element_node_list:
            try:
                if hasattr(elem, "lock") and elem.lock:
                    continue
            except AttributeError:
                pass
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
        If any element is emphasized, all operations a references to that element are targeted.
        """
        for s in self._tree.flat():
            if s.highlighted:
                s.highlighted = False
            if s.targeted:
                s.targeted = False
            if s.selected:
                s.selected = False

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
        # We dont know it better...
        self._emphasized_bounds_painted = [b[0], b[1], b[2], b[3]]
        self.signal("selected_bounds", self._emphasized_bounds)

    def move_emphasized(self, dx, dy):
        for node in self.elems(emphasized=True):
            if hasattr(node, "lock") and node.lock and not self.lock_allows_move:
                continue
            node.matrix.post_translate(dx, dy)
            node.modified()

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
        else:
            self._emphasized_bounds = None
            self._emphasized_bounds_painted = None
            self.set_emphasis(None)

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

        # I am tired of changing the code all the time, so let's do it properly
        debug = self.kernel.channel("classify", timestamp=True)

        if elements is None:
            return

        if not len(list(self.ops())) and not self.operation_default_empty:
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
            # Following lines added to handle 0.7 special ops added to ops list
            if hasattr(node, "operation"):
                add_op_function(node)
                continue
            classif_info = [False, False]
            # Even for fuzzy we check first a direct hit
            if fuzzy:
                fuzzy_param = (False, True)
            else:
                fuzzy_param = (False,)
            for tempfuzzy in fuzzy_param:
                if debug:
                    debug(f"Pass 1 (fuzzy={tempfuzzy}): check {node.type}")
                was_classified = False
                should_break = False

                for op in operations:
                    # One special case: is this a rasterop and the stroke
                    # color is black and the option 'classify_black_as_raster'
                    # is not set? Then skip...
                    is_black = False
                    whisperer = True
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
                        whisperer = False
                    elif (
                        self.classify_black_as_raster
                        and is_black
                        and isinstance(op, EngraveOpNode)
                    ):
                        whisperer = False
                    if debug:
                        debug(
                            f"For {op.type}: black={is_black}, perform={whisperer}, flag={self.classify_black_as_raster}"
                        )
                    if hasattr(op, "classify") and whisperer:

                        classified, should_break, feedback = op.classify(
                            node,
                            fuzzy=tempfuzzy,
                            fuzzydistance=fuzzydistance,
                            usedefault=False,
                        )
                    else:
                        continue
                    if classified:
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
                                f"Was classified: {sstroke} {sfill} matching operation: {type(op).__name__}, break={should_break}"
                            )
                    if should_break:
                        break
                # So we are the end of the first pass, if there was already a classification
                # then we call it a day and dont call the fuzzy part
                if was_classified or should_break:
                    break

            ######################
            # NON-CLASSIFIED ELEMENTS
            ######################
            if was_classified and debug:
                debug(f"Classified, stroke={classif_info[0]}, fill={classif_info[1]}")
            # Lets make sure we only consider relevant, ie existing attributes...
            if hasattr(node, "stroke"):
                if node.stroke is None or node.stroke.argb is None:
                    classif_info[0] = True
                if node.type == "elem text":
                    # even if it has, we are not going to something with it
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
            if not was_classified and usedefault:
                # let's iterate through the default ops and add them
                if debug:
                    debug("Pass 2 (wasn't classified), looking for default ops")
                for op in operations:
                    is_black = False
                    whisperer = True
                    if (
                        hasattr(node, "stroke")
                        and node.stroke is not None
                        and node.stroke.argb is not None
                        and node.type != "elem text"
                    ):
                        if fuzzy:
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
                        # print ("Default Skip Raster")
                        whisperer = False
                    elif (
                        self.classify_black_as_raster
                        and is_black
                        and isinstance(op, EngraveOpNode)
                    ):
                        whisperer = False
                    if debug:
                        debug(
                            f"For {op.type}: black={is_black}, perform={whisperer}, flag={self.classify_black_as_raster}"
                        )
                    if hasattr(op, "classifys") and whisperer:
                        classified, should_break, feedback = op.classify(
                            node,
                            fuzzy=fuzzy,
                            fuzzydistance=fuzzydistance,
                            usedefault=True,
                        )
                    else:
                        continue
                    if classified:
                        if feedback is not None and "stroke" in feedback:
                            classif_info[0] = True
                        if feedback is not None and "fill" in feedback:
                            classif_info[1] = True
                        was_classified = True
                        if debug:
                            debug(
                                f"Was classified to default operation: {type(op).__name__}, break={should_break}"
                            )
                    if should_break:
                        break
            # Lets make sure we only consider relevant, ie existing attributes...
            if hasattr(node, "stroke"):
                if node.stroke is None or node.stroke.argb is None:
                    classif_info[0] = True
                if node.type == "elem text":
                    # even if it has, we are not going to something with it
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
                has_raster = False
                if node.type == "elem image":
                    stdops.append(ImageOpNode(output=False))
                    if debug:
                        debug("add an op image")
                    classif_info[0] = True
                    classif_info[1] = True
                elif node.type == "elem point":
                    stdops.append(DotsOpNode(output=False))
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
                    if fuzzy:
                        is_cut = Color.distance("red", node.stroke) <= fuzzydistance
                    else:
                        is_cut = Color("red") == node.stroke
                    if self.classify_black_as_raster:
                        if fuzzy:
                            is_raster = (
                                Color.distance("black", node.stroke) <= fuzzydistance
                                or Color.distance("white", node.stroke) <= fuzzydistance
                            )
                        else:
                            is_raster = (
                                Color("black") == node.stroke
                                or Color("white") == node.stroke
                            )
                    else:
                        is_raster = False
                    # print (f"Need a new op: cut={is_cut},raster={is_raster}, color={node.stroke}")
                    if is_cut:
                        stdops.append(CutOpNode(color=Color("red"), speed=5.0))
                        if debug:
                            debug("add an op cut due to stroke")
                    elif is_raster:
                        stdops.append(RasterOpNode(color="black", output=True))
                        if debug:
                            debug("add an op raster due to stroke")
                        has_raster = True
                    else:
                        stdops.append(EngraveOpNode(color=node.stroke, speed=35.0))
                        if debug:
                            debug(
                                f"add an op engrave with color={node.stroke} due to stroke"
                            )
                # Do we need to add a fill operation?
                if (
                    not classif_info[1]
                    and hasattr(node, "fill")
                    and node.fill is not None
                    and node.fill.argb is not None
                    and not has_raster
                ):
                    stdops.append(RasterOpNode(color="black", output=True))
                    if debug:
                        debug("add an op raster due to fill")
                for op in stdops:
                    # Lets make sure we don't have something like that already
                    if debug:
                        debug(f"Check for existence of {op.type}")
                    already_found = False
                    for testop in self.ops():
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
                        already_found = True
                    op.add_reference(node)

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
        operations = self._tree.get(type="branch ops").children
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

    def remove_empty_groups(self):
        something_was_deleted = True
        while something_was_deleted:
            something_was_deleted = False
            for node in self.elems_nodes():
                if node.type in ("file", "group"):
                    if len(node.children) == 0:
                        node.remove_node()
                        something_was_deleted = True

    @staticmethod
    def element_classify_color(element: SVGElement):
        element_color = element.stroke
        if element_color is None or element_color.rgb is None:
            element_color = element.fill
        return element_color

    def load(self, pathname, **kwargs):
        kernel = self.kernel
        _ = kernel.translation
        for loader, loader_name, sname in kernel.find("load"):
            for description, extensions, mimetype in loader.load_types():
                if str(pathname).lower().endswith(extensions):
                    try:
                        self.signal("freeze_tree", True)
                        results = loader.load(self, self, pathname, **kwargs)
                        self.remove_empty_groups()
                        self.signal("freeze_tree", False)
                    except FileNotFoundError:
                        return False
                    except BadFileError as e:
                        kernel._console_channel(_("File is Malformed") + ": " + str(e))
                    except OSError:
                        return False
                    else:
                        if results:
                            self.signal("tree_changed")
                            return True
        return False

    def load_types(self, all=True):
        kernel = self.kernel
        _ = kernel.translation
        filetypes = []
        if all:
            filetypes.append(_("All valid types"))
            exts = []
            for loader, loader_name, sname in kernel.find("load"):
                for description, extensions, mimetype in loader.load_types():
                    for ext in extensions:
                        exts.append(f"*.{ext}")
            filetypes.append(";".join(exts))
        for loader, loader_name, sname in kernel.find("load"):
            for description, extensions, mimetype in loader.load_types():
                exts = []
                for ext in extensions:
                    exts.append(f"*.{ext}")
                filetypes.append(f"{description} ({extensions[0]})")
                filetypes.append(";".join(exts))
        return "|".join(filetypes)

    def save(self, pathname, version="default"):
        kernel = self.kernel
        for saver, save_name, sname in kernel.find("save"):
            for description, extension, mimetype, _version in saver.save_types():
                if pathname.lower().endswith(extension) and _version == version:
                    saver.save(self, pathname, version)
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
