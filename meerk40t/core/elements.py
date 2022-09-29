import functools
import os.path
import re
from copy import copy
from math import cos, gcd, isinf, pi, sin, sqrt, tau
from os.path import realpath
from random import randint, shuffle

from numpy import linspace

from meerk40t.core.exceptions import BadFileError
from meerk40t.kernel import CommandSyntaxError, Service, Settings

from ..numpath import Numpath
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
    if lifecycle == "preregister":
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
                "label": _("Classify newly created elements"),
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
                "label": _("Autogenerate both for fill and stroke"),
                "tip": _("Active: for both stroke and fill we look for a corresponding hit, if none was found we generate a matching operation")
                + "\n"
                + _("Inactive: one hit of either stroke or fill is enough to prevent autogeneration"),
                "page": "Classification",
                "section": "_90_Auto-Generation",
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
        self._clipboard = {}
        self._clipboard_default = "0"

        self.note = None
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None
        self._emphasized_bounds_dirty = True
        self._tree = RootNode(self)

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

        self._init_commands(kernel)
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
        # data:         nodes to assign to as minimum (will be extened is similar=True, see below)
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
        # If we havent identified a color, then similar makes no sense
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
                    this_length += sqrt(dx * dx + dy * dy)
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

    def wordlist_translate(self, pattern, elemnode=None):
        # This allows to add / set values for a given wordlist
        node = None
        if elemnode is not None:
            # Does it belong to an op?
            node = elemnode.parent
            # That only seems to be true during burn...
            if not node.type.startswith("op"):
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

        result = self.mywordlist.translate(pattern)
        return result

    def _init_commands(self, kernel):

        _ = kernel.translation

        @self.console_argument("filename")
        @self.console_command(
            "load",
            help=_("loads file from working directory"),
            input_type=None,
            output_type="file",
        )
        def load(channel, _, filename=None, **kwargs):
            import os

            if filename is None:
                channel(_("No file specified."))
                return
            new_file = os.path.join(self.kernel.current_directory, filename)
            if not os.path.exists(new_file):
                channel(_("No such file."))
                return
            try:
                channel(_("loading..."))
                result = self.load(new_file)
                if result:
                    channel(_("Done."))
            except AttributeError:
                raise CommandSyntaxError(_("Loading files was not defined"))
            return "file", new_file

        # ==========
        # WORDLISTS COMMANDS
        # ==========

        @self.console_command(
            "wordlist",
            help=_("Wordlist base operation"),
            output_type="wordlist",
        )
        def wordlist_base(command, channel, _, remainder=None, **kwargs):
            return "wordlist", ""

        @self.console_argument("key", help=_("Wordlist value"))
        @self.console_argument("value", help=_("Content"))
        @self.console_command(
            "add",
            help=_("add value to wordlist"),
            input_type="wordlist",
            output_type="wordlist",
        )
        def wordlist_add(command, channel, _, key=None, value=None, **kwargs):
            if key is not None:
                if value is None:
                    value = ""
                self.mywordlist.add(key, value)
            return "wordlist", key

        @self.console_argument("key", help=_("Wordlist value"))
        @self.console_argument("value", help=_("Content"))
        @self.console_command(
            "addcounter",
            help=_("add numeric counter to wordlist"),
            input_type="wordlist",
            output_type="wordlist",
        )
        def wordlist_addcounter(command, channel, _, key=None, value=None, **kwargs):
            if key is not None:
                if value is None:
                    value = 1
                else:
                    try:
                        value = int(value)
                    except ValueError:
                        value = 1
                self.mywordlist.add(key, value, 2)
            return "wordlist", key

        @self.console_argument("key", help=_("Wordlist value"))
        @self.console_argument("index", help=_("index to use"))
        @self.console_command(
            "get",
            help=_("get current value from wordlist"),
            input_type="wordlist",
            output_type="wordlist",
        )
        def wordlist_get(command, channel, _, key=None, index=None, **kwargs):
            if key is not None:
                result = self.mywordlist.fetch_value(skey=key, idx=index)
                channel(str(result))
            else:
                channel(_("Missing key"))
                result = ""
            return "wordlist", result

        @self.console_argument("key", help=_("Wordlist value"))
        @self.console_argument("value", help=_("Wordlist value"))
        @self.console_argument("index", help=_("index to use"))
        @self.console_command(
            "set",
            help=_("set value to wordlist"),
            input_type="wordlist",
            output_type="wordlist",
        )
        def wordlist_set(
            command, channel, _, key=None, value=None, index=None, **kwargs
        ):
            if key is not None and value is not None:
                self.mywordlist.set_value(skey=key, value=value, idx=index)
            else:
                channel(_("Not enough parameters given"))
            return "wordlist", key

        @self.console_argument(
            "key", help=_("Individual wordlist value (use @ALL for all)")
        )
        @self.console_argument("index", help=_("index to use, or +2 to increment by 2"))
        @self.console_command(
            "index",
            help=_("sets index in wordlist"),
            input_type="wordlist",
            output_type="wordlist",
            all_arguments_required=True,
        )
        def wordlist_index(command, channel, _, key=None, index=None, **kwargs):
            self.mywordlist.set_index(skey=key, idx=index)
            return "wordlist", key

        @self.console_argument(
            "filename", help=_("Wordlist file (if empty use mk40-default)")
        )
        @self.console_command(
            "restore",
            help=_("Loads a previously saved wordlist"),
            input_type="wordlist",
            output_type="wordlist",
        )
        def wordlist_restore(
            command, channel, _, filename=None, remainder=None, **kwargs
        ):
            new_file = filename
            if filename is not None:
                new_file = os.path.join(self.kernel.current_directory, filename)
                if not os.path.exists(new_file):
                    channel(_("No such file."))
                    return
            self.mywordlist.load_data(new_file)
            return "wordlist", ""

        @self.console_argument(
            "filename", help=_("Wordlist file (if empty use mk40-default)")
        )
        @self.console_command(
            "backup",
            help=_("Saves the current wordlist"),
            input_type="wordlist",
            output_type="wordlist",
        )
        def wordlist_backup(
            command, channel, _, filename=None, remainder=None, **kwargs
        ):
            new_file = filename
            if filename is not None:
                new_file = os.path.join(self.kernel.current_directory, filename)

            self.mywordlist.save_data(new_file)
            return "wordlist", ""

        @self.console_argument("key", help=_("Wordlist value"))
        @self.console_command(
            "list",
            help=_("list wordlist values"),
            input_type="wordlist",
            output_type="wordlist",
        )
        def wordlist_list(command, channel, _, key=None, **kwargs):
            channel("----------")
            if key is None:
                for skey in self.mywordlist.content:
                    channel(str(skey))
            else:
                if key in self.mywordlist.content:
                    wordlist = self.mywordlist.content[key]
                    channel(
                        _("Wordlist {name} (Type={type}, Index={index})):").format(
                            name=key, type=wordlist[0], index=wordlist[1] - 2
                        )
                    )
                    for idx, value in enumerate(wordlist[2:]):
                        channel(f"#{idx}: {str(value)}")
                else:
                    channel(_("There is no such pattern {name}").format(name=key))
            channel("----------")
            return "wordlist", key

        @self.console_argument("filename", help=_("CSV file"))
        @self.console_command(
            "load",
            help=_("Attach a csv-file to the wordlist"),
            input_type="wordlist",
            output_type="wordlist",
        )
        def wordlist_load(command, channel, _, filename=None, **kwargs):
            if filename is None:
                channel(_("No file specified."))
                return
            new_file = os.path.join(self.kernel.current_directory, filename)
            if not os.path.exists(new_file):
                channel(_("No such file."))
                return

            rows, columns, names = self.mywordlist.load_csv_file(new_file)
            channel(_("Rows added: {rows}").format(rows=rows))
            channel(_("Values added: {values}").format(columns=columns))
            for name in names:
                channel("  " + name)
            return "wordlist", names

        # ==========
        # PENBOX COMMANDS
        # ==========

        @self.console_argument("key", help=_("Penbox key"))
        @self.console_command(
            "penbox",
            help=_("Penbox base operation"),
            input_type=None,
            output_type="penbox",
        )
        def penbox(command, channel, _, key=None, remainder=None, **kwargs):
            if remainder is None or key is None:
                channel("----------")
                if key is None:
                    for key in self.penbox:
                        channel(str(key))
                else:
                    try:
                        for i, value in enumerate(self.penbox[key]):
                            channel(f"{i}: {str(value)}")
                    except KeyError:
                        channel(_("penbox does not exist"))
                channel("----------")
            return "penbox", key

        @self.console_argument("count", help=_("Penbox count"), type=int)
        @self.console_command(
            "add",
            help=_("add pens to the chosen penbox"),
            input_type="penbox",
            output_type="penbox",
        )
        def penbox_add(
            command, channel, _, count=None, data=None, remainder=None, **kwargs
        ):
            if count is None:
                raise CommandSyntaxError
            current = self.penbox.get(data)
            if current is None:
                current = list()
                self.penbox[data] = current
            current.extend([dict() for _ in range(count)])
            return "penbox", data

        @self.console_argument("count", help=_("Penbox count"), type=int)
        @self.console_command(
            "del",
            help=_("delete pens to the chosen penbox"),
            input_type="penbox",
            output_type="penbox",
        )
        def penbox_del(
            command, channel, _, count=None, data=None, remainder=None, **kwargs
        ):
            if count is None:
                raise CommandSyntaxError
            current = self.penbox.get(data)
            if current is None:
                current = list()
                self.penbox[data] = current
            for _ in range(count):
                try:
                    del current[-1]
                except IndexError:
                    break
            return "penbox", data

        @self.console_argument("index", help=_("Penbox index"), type=self.index_range)
        @self.console_argument("key", help=_("Penbox key"), type=str)
        @self.console_argument("value", help=_("Penbox key"), type=str)
        @self.console_command(
            "set",
            help=_("set value in penbox"),
            input_type="penbox",
            output_type="penbox",
        )
        def penbox_set(
            command,
            channel,
            _,
            index=None,
            key=None,
            value=None,
            data=None,
            remainder=None,
            **kwargs,
        ):
            if not value:
                raise CommandSyntaxError
            current = self.penbox.get(data)
            if current is None:
                current = list()
                self.penbox[data] = current
            rex = re.compile(r"([+-]?[0-9]+)(?:[,-]([+-]?[0-9]+))?")
            m = rex.match(value)
            if not m:
                raise CommandSyntaxError
            value = float(m.group(1))
            end = m.group(2)
            if end:
                end = float(end)

            if not end:
                for i in index:
                    try:
                        current[i][key] = value
                    except IndexError:
                        pass
            else:
                r = len(index)
                try:
                    s = (end - value) / (r - 1)
                except ZeroDivisionError:
                    s = 0
                d = 0
                for i in index:
                    try:
                        current[i][key] = value + d
                    except IndexError:
                        pass
                    d += s
            return "penbox", data

        # ==========
        # MATERIALS COMMANDS
        # ==========
        @self.console_command(
            "material",
            help=_("material base operation"),
            input_type=(None, "ops"),
            output_type="materials",
        )
        def materials(command, channel, _, data=None, remainder=None, **kwargs):
            if data is None:
                data = list(self.ops(emphasized=True))
            if remainder is None:
                channel("----------")
                channel(_("Materials:"))
                for section in self.op_data.section_set():
                    channel(section)
                channel("----------")
            return "materials", data

        @self.console_argument("name", help=_("Name to save the materials under"))
        @self.console_command(
            "save",
            help=_("Save current materials to persistent settings"),
            input_type="materials",
            output_type="materials",
        )
        def save_materials(command, channel, _, data=None, name=None, **kwargs):
            if name is None:
                raise CommandSyntaxError
            self.save_persistent_operations(name)
            return "materials", data

        @self.console_argument("name", help=_("Name to load the materials from"))
        @self.console_command(
            "load",
            help=_("Load materials from persistent settings"),
            input_type="materials",
            output_type="ops",
        )
        def load_materials(name=None, **kwargs):
            if name is None:
                raise CommandSyntaxError
            self.load_persistent_operations(name)
            return "ops", list(self.ops())

        @self.console_argument("name", help=_("Name to delete the materials from"))
        @self.console_command(
            "delete",
            help=_("Delete materials from persistent settings"),
            input_type="materials",
            output_type="materials",
        )
        def load_materials(name=None, **kwargs):
            if name is None:
                raise CommandSyntaxError
            self.clear_persistent_operations(name)
            return "materials", list(self.ops())

        @self.console_argument("name", help=_("Name to display the materials from"))
        @self.console_command(
            "list",
            help=_("Show information about materials"),
            input_type="materials",
            output_type="materials",
        )
        def materials_list(channel, _, data=None, name=None, **kwargs):
            channel("----------")
            channel(_("Materials Current:"))
            for section in self.op_data.section_set():
                for subsect in self.op_data.derivable(section):
                    label = self.op_data.read_persistent(str, subsect, "label", "-")
                    channel(f"{subsect}: {label}")
            channel("----------")

        # ==========
        # PENBOX OPERATION COMMANDS
        # ==========

        @self.console_argument("key", help=_("Penbox key"))
        @self.console_command(
            "penbox_pass",
            help=_("Set the penbox_pass for the given operation"),
            input_type="ops",
            output_type="ops",
        )
        def penbox_pass(
            command, channel, _, key=None, remainder=None, data=None, **kwargs
        ):
            if data is not None:
                if key is not None:
                    for op in data:
                        try:
                            op.settings["penbox_pass"] = key
                            channel(f"{str(op)} penbox_pass changed to {key}.")
                        except AttributeError:
                            pass
                else:
                    if key is None:
                        channel("----------")
                        for op in data:
                            try:
                                key = op.settings.get("penbox_pass")
                                if key is None:
                                    channel(f"{str(op)} penbox_pass is not set.")
                                else:
                                    channel(f"{str(op)} penbox_pass is set to {key}.")
                            except AttributeError:
                                pass  # No op.settings.
                        channel("----------")
            return "ops", data

        @self.console_argument("key", help=_("Penbox key"))
        @self.console_command(
            "penbox_value",
            help=_("Set the penbox_value for the given operation"),
            input_type="ops",
            output_type="ops",
        )
        def penbox_value(
            command, channel, _, key=None, remainder=None, data=None, **kwargs
        ):
            if data is not None:
                if key is not None:
                    for op in data:
                        try:
                            op.settings["penbox_value"] = key
                            channel(f"{str(op)} penbox_value changed to {key}.")
                        except AttributeError:
                            pass
                else:
                    if key is None:
                        channel("----------")
                        for op in data:
                            try:
                                key = op.settings.get("penbox_value")
                                if key is None:
                                    channel(f"{str(op)} penbox_value is not set.")
                                else:
                                    channel(f"{str(op)} penbox_value is set to {key}.")
                            except AttributeError:
                                pass  # No op.settings.
                        channel("----------")
            return "ops", data

        # ==========
        # OPERATION BASE
        # ==========

        @self.console_command("operations", help=_("Show information about operations"))
        def element(**kwargs):
            self(".operation* list\n")

        @self.console_command(
            "operation.*", help=_("operation.*: selected operations"), output_type="ops"
        )
        def operation(**kwargs):
            return "ops", list(self.ops(emphasized=True))

        @self.console_command(
            "operation*", help=_("operation*: all operations"), output_type="ops"
        )
        def operation(**kwargs):
            return "ops", list(self.ops())

        @self.console_command(
            "operation~",
            help=_("operation~: non selected operations."),
            output_type="ops",
        )
        def operation(**kwargs):
            return "ops", list(self.ops(emphasized=False))

        @self.console_command(
            "operation", help=_("operation: selected operations."), output_type="ops"
        )
        def operation(**kwargs):
            return "ops", list(self.ops(emphasized=True))

        @self.console_command(
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
                    channel(_("index {index} out of range").format(index=value))
            return "ops", op_values

        @self.console_command(
            "select",
            help=_("Set these values as the selection."),
            input_type="ops",
            output_type="ops",
        )
        def operation_select(data=None, **kwargs):
            self.set_emphasis(data)
            return "ops", data

        @self.console_command(
            "select+",
            help=_("Add the input to the selection"),
            input_type="ops",
            output_type="ops",
        )
        def operation_select_plus(data=None, **kwargs):
            ops = list(self.ops(emphasized=True))
            ops.extend(data)
            self.set_emphasis(ops)
            return "ops", ops

        @self.console_command(
            "select-",
            help=_("Remove the input data from the selection"),
            input_type="ops",
            output_type="ops",
        )
        def operation_select_minus(data=None, **kwargs):
            ops = list(self.ops(emphasized=True))
            for e in data:
                try:
                    ops.remove(e)
                except ValueError:
                    pass
            self.set_emphasis(ops)
            return "ops", ops

        @self.console_command(
            "select^",
            help=_("Toggle the input data in the selection"),
            input_type="ops",
            output_type="ops",
        )
        def operation_select_xor(data=None, **kwargs):
            ops = list(self.ops(emphasized=True))
            for e in data:
                try:
                    ops.remove(e)
                except ValueError:
                    ops.append(e)
            self.set_emphasis(ops)
            return "ops", ops

        @self.console_argument("start", type=int, help=_("operation start"))
        @self.console_argument("end", type=int, help=_("operation end"))
        @self.console_argument("step", type=int, help=_("operation step"))
        @self.console_command(
            "range",
            help=_("Subset existing selection by begin and end indices and step"),
            input_type="ops",
            output_type="ops",
        )
        def operation_select_range(data=None, start=None, end=None, step=1, **kwargs):
            subops = list()
            for e in range(start, end, step):
                try:
                    subops.append(data[e])
                except IndexError:
                    pass
            self.set_emphasis(subops)
            return "ops", subops

        @self.console_argument("filter", type=str, help=_("Filter to apply"))
        @self.console_command(
            "filter",
            help=_("Filter data by given value"),
            input_type="ops",
            output_type="ops",
        )
        def operation_filter(channel=None, data=None, filter=None, **kwargs):
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
                (
                    "COLOR",
                    r"(#[0123456789abcdefABCDEF]{6}|#[0123456789abcdefABCDEF]{3})",
                ),
                (
                    "TYPE",
                    r"(raster|image|cut|engrave|dots|unknown|command|cutcode|lasercode)",
                ),
                (
                    "VAL",
                    r"(speed|power|step|acceleration|passes|color|op|overscan|len)",
                ),
            ]
            filter_re = re.compile(
                "|".join("(?P<%s>%s)" % pair for pair in _filter_parse)
            )
            operator = list()
            operand = list()

            def filter_parser(text: str):
                p = 0
                limit = len(text)
                while p < limit:
                    match = filter_re.match(text, p)
                    if match is None:
                        break  # No more matches.
                    _kind = match.lastgroup
                    _start = p
                    p = match.end()
                    if _kind == "SKIP":
                        continue
                    _value = match.group()
                    yield _kind, _value, _start, p

            def solve_to(order: int):
                try:
                    while len(operator) and operator[0][0] >= order:
                        _p, op = operator.pop()
                        v2 = operand.pop()
                        v1 = operand.pop()
                        try:
                            if op == "==" or op == "=":
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
                            raise CommandSyntaxError("Cannot evaluate expression")
                        except ZeroDivisionError:
                            operand.append(float("inf"))
                except IndexError:
                    pass

            for e in data:
                for kind, value, start, pos in filter_parser(filter):
                    if kind == "COLOR":
                        operand.append(Color(value))
                    elif kind == "VAL":
                        if value == "dpi":
                            operand.append(e.dpi)
                        elif value == "color":
                            operand.append(e.color)
                        elif value == "op":
                            operand.append(e.type.remove("op").strip())
                        elif value == "len":
                            operand.append(len(e.children))
                        else:
                            operand.append(e.settings.get(value))

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
                    raise CommandSyntaxError(_("Filter parse failed"))

            self.set_emphasis(subops)
            return "ops", subops

        @self.console_command(
            "list",
            help=_("Show information about the chained data"),
            input_type="ops",
            output_type="ops",
        )
        def operation_list(channel, _, data=None, **kwargs):
            channel("----------")
            channel(_("Operations:"))
            index_ops = list(self.ops())
            for op_obj in data:
                i = index_ops.index(op_obj)
                select_piece = "*" if op_obj.emphasized else " "
                name = f"{select_piece} {i}: {str(op_obj)}"
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
                        name = f"{''.ljust(5)}{q}: {str(type(oe).__name__)}-{ident_piece} s:{stroke_piece} f:{fill_piece}"
                        channel(name)
            channel("----------")

        @self.console_option("color", "c", type=Color)
        @self.console_option("default", "D", type=bool)
        @self.console_option("speed", "s", type=float)
        @self.console_option("power", "p", type=float)
        @self.console_option("dpi", "d", type=int)
        @self.console_option("overscan", "o", type=self.length)
        @self.console_option("passes", "x", type=int)
        @self.console_option(
            "parallel",
            "P",
            type=bool,
            help=_("Creates a new operation for each element given"),
            action="store_true",
        )
        @self.console_option(
            "stroke",
            "K",
            type=bool,
            action="store_true",
            help=_(
                "Set the operation color based on the stroke if the first stroked item added to this operation"
            ),
        )
        @self.console_option(
            "fill",
            "F",
            type=bool,
            action="store_true",
            help=_(
                "Set the operation color based on the fill if the first filled item added to this operation"
            ),
        )
        @self.console_command(
            ("cut", "engrave", "raster", "imageop", "dots", "hatch"),
            help=_(
                "<cut/engrave/raster/imageop/dots/hatch> - group the elements into this operation"
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
            dpi=None,
            overscan=None,
            passes=None,
            parallel=False,
            stroke=False,
            fill=False,
            **kwargs,
        ):
            op_list = []

            def make_op():
                if command == "cut":
                    return CutOpNode()
                elif command == "engrave":
                    return EngraveOpNode()
                elif command == "raster":
                    return RasterOpNode()
                elif command == "imageop":
                    return ImageOpNode()
                elif command == "dots":
                    return DotsOpNode()
                elif command == "hatch":
                    return HatchOpNode()
                elif command == "waitop":
                    return WaitOperation()
                elif command == "outputop":
                    return OutputOperation()
                elif command == "inputop":
                    return InputOperation()
                else:
                    raise ValueError

            if parallel:
                if data is None:
                    return "op", []
                for item in data:
                    op = make_op()
                    if color is not None:
                        op.color = color
                    elif fill:
                        try:
                            op.color = item.fill
                        except AttributeError:
                            continue
                    elif stroke:
                        try:
                            op.color = item.stroke
                        except AttributeError:
                            continue
                    if default is not None:
                        op.default = default
                    if speed is not None:
                        op.speed = speed
                    if power is not None:
                        op.power = power
                    if passes is not None:
                        op.passes_custom = True
                        op.passes = passes
                    if dpi is not None:
                        op.dpi = dpi
                    if overscan is not None:
                        op.overscan = overscan
                    self.add_op(op)
                    op.add_reference(item)
                    op_list.append(op)
            else:
                op = make_op()
                if color is not None:
                    op.color = color
                elif fill:
                    try:
                        op.color = data[0].fill
                    except (AttributeError, IndexError):
                        pass
                elif stroke:
                    try:
                        op.color = data[0].stroke
                    except (AttributeError, IndexError):
                        pass
                if default is not None:
                    op.default = default
                if speed is not None:
                    op.speed = speed
                if power is not None:
                    op.power = power
                if passes is not None:
                    op.passes_custom = True
                    op.passes = passes
                if dpi is not None:
                    op.dpi = dpi
                if overscan is not None:
                    op.overscan = overscan
                self.add_op(op)
                if data is not None:
                    for item in data:
                        op.add_reference(item)
                op_list.append(op)
            return "ops", op_list

        @self.console_argument(
            "time",
            type=float,
            default=5,
            help=_("Time for the given wait operation."),
        )
        @self.console_command(
            "waitop",
            help=_("<waitop> - Create new utility operation"),
            input_type=None,
            output_type="ops",
        )
        def makeop(
            command,
            time=None,
            **kwargs,
        ):
            op = WaitOperation(wait=time)
            self.add_op(op)
            return "ops", [op]

        @self.console_argument(
            "mask",
            type=int,
            default=0,
            help=_("binary input/output mask"),
        )
        @self.console_argument(
            "value",
            type=int,
            default=0,
            help=_("binary input/output value"),
        )
        @self.console_command(
            ("outputop", "inputop"),
            help=_("<outputop, inputop> - Create new utility operation"),
            input_type=None,
            output_type="ops",
        )
        def makeop(
            command,
            mask=None,
            value=None,
            **kwargs,
        ):
            if command == "inputop":
                op = InputOperation(mask=mask, value=value)
            else:
                op = OutputOperation(mask=mask, value=value)

            self.add_op(op)
            return "ops", [op]

        @self.console_command(
            "consoleop",
            help=_("<consoleop> - Create new utility operation"),
        )
        def makeop(
            command,
            remainder=None,
            **kwargs,
        ):
            if remainder is not None:
                op = ConsoleOperation(command=remainder)
                self.add_op(op)
                return "ops", [op]

        @self.console_argument("dpi", type=int, help=_("raster dpi"))
        @self.console_command("dpi", help=_("dpi <raster-dpi>"), input_type="ops")
        def op_dpi(command, channel, _, data, dpi=None, **kwrgs):
            if dpi is None:
                found = False
                for op in data:
                    if op.type in ("op raster", "op image"):
                        dpi = op.dpi
                        channel(
                            _("Step for {name} is currently: {dpi}").format(
                                name=str(op), dpi=dpi
                            )
                        )
                        found = True
                if not found:
                    channel(_("No raster operations selected."))
                return
            for op in data:
                if op.type in ("op raster", "op image"):
                    op.dpi = dpi
                    op.notify_update()
            return "ops", data

        @self.console_option(
            "difference",
            "d",
            type=bool,
            action="store_true",
            help=_("Change speed by this amount."),
        )
        @self.console_option(
            "progress",
            "p",
            type=bool,
            action="store_true",
            help=_("Change speed for each item in order"),
        )
        @self.console_argument("speed", type=str, help=_("operation speed in mm/s"))
        @self.console_command(
            "speed", help=_("speed <speed>"), input_type="ops", output_type="ops"
        )
        def op_speed(
            command,
            channel,
            _,
            speed=None,
            difference=False,
            progress=False,
            data=None,
            **kwrgs,
        ):
            if speed is None:
                for op in data:
                    old = op.speed
                    channel(
                        _("Speed for '{name}' is currently: {speed}").format(
                            name=str(op), speed=old
                        )
                    )
                return
            if speed.endswith("%"):
                speed = speed[:-1]
                percent = True
            else:
                percent = False

            try:
                new_speed = float(speed)
            except ValueError:
                channel(_("Not a valid speed or percent."))
                return
            delta = 0
            for op in data:
                old = op.speed
                if percent and difference:
                    s = old + old * (new_speed / 100.0)
                elif difference:
                    s = old + new_speed
                elif percent:
                    s = old * (new_speed / 100.0)
                elif progress:
                    s = old + delta
                    delta += new_speed
                else:
                    s = new_speed
                if s < 0:
                    s = 0
                op.speed = s
                channel(
                    _("Speed for '{name}' updated {old_speed} -> {speed}").format(
                        name=str(op), old_speed=old, speed=s
                    )
                )
                op.notify_update()
            return "ops", data

        @self.console_argument(
            "power", type=int, help=_("power in pulses per inch (ppi, 1000=max)")
        )
        @self.console_option(
            "difference",
            "d",
            type=bool,
            action="store_true",
            help=_("Change power by this amount."),
        )
        @self.console_option(
            "progress",
            "p",
            type=bool,
            action="store_true",
            help=_("Change power for each item in order"),
        )
        @self.console_command(
            "power", help=_("power <ppi>"), input_type="ops", output_type="ops"
        )
        def op_power(
            command,
            channel,
            _,
            power=None,
            difference=False,
            progress=False,
            data=None,
            **kwrgs,
        ):
            if power is None:
                for op in data:
                    old = op.power
                    channel(
                        _("Power for '{name}' is currently: {power}").format(
                            name=str(op), power=old
                        )
                    )
                return
            delta = 0
            for op in data:
                old = op.power
                if progress:
                    s = old + delta
                    delta += power
                elif difference:
                    s = old + power
                else:
                    s = power
                if s > 1000:
                    s = 1000
                if s < 0:
                    s = 0
                op.power = s
                channel(
                    _("Power for '{name}' updated {old_power} -> {power}").format(
                        name=str(op), old_power=old, power=s
                    )
                )
                op.notify_update()
            return "ops", data

        @self.console_argument(
            "frequency", type=float, help=_("frequency set for operation")
        )
        @self.console_option(
            "difference",
            "d",
            type=bool,
            action="store_true",
            help=_("Change speed by this amount."),
        )
        @self.console_option(
            "progress",
            "p",
            type=bool,
            action="store_true",
            help=_("Change speed for each item in order"),
        )
        @self.console_command(
            "frequency", help=_("frequency <kHz>"), input_type="ops", output_type="ops"
        )
        def op_frequency(
            command,
            channel,
            _,
            frequency=None,
            difference=False,
            progress=False,
            data=None,
            **kwrgs,
        ):
            if frequency is None:
                for op in data:
                    old = op.frequency
                    channel(
                        _("Frequency for '{name}' is currently: {frequency}").format(
                            name=str(op), frequency=old
                        )
                    )
                return
            delta = 0
            for op in data:
                old = op.frequency
                if progress:
                    s = old + delta
                    delta += frequency
                elif difference:
                    s = old + frequency
                else:
                    s = frequency
                if s < 0:
                    s = 0
                op.frequency = s
                channel(
                    _(
                        "Frequency for '{name}' updated {old_frequency} -> {frequency}"
                    ).format(name=str(op), old_frequency=old, frequency=s)
                )
                op.notify_update()
            return "ops", data

        @self.console_argument("passes", type=int, help=_("Set operation passes"))
        @self.console_command(
            "passes", help=_("passes <passes>"), input_type="ops", output_type="ops"
        )
        def op_passes(command, channel, _, passes=None, data=None, **kwrgs):
            if passes is None:
                for op in data:
                    old_passes = op.passes
                    channel(
                        _("Passes for '{name}' is currently: {passes}").format(
                            name=str(op), passes=old_passes
                        )
                    )
                return
            for op in data:
                old_passes = op.passes
                op.passes = passes
                if passes >= 1:
                    op.passes_custom = True
                channel(
                    _("Passes for '{name}' updated {old_passes} -> {passes}").format(
                        name=str(op), old_passes=old_passes, passes=passes
                    )
                )
                op.notify_update()
            return "ops", data

        @self.console_argument(
            "distance", type=Length, help=_("Set hatch-distance of operations")
        )
        @self.console_option(
            "difference",
            "d",
            type=bool,
            action="store_true",
            help=_("Change hatch-distance by this amount."),
        )
        @self.console_option(
            "progress",
            "p",
            type=bool,
            action="store_true",
            help=_("Change hatch-distance for each item in order"),
        )
        @self.console_command(
            "hatch-distance",
            help=_("hatch-distance <distance>"),
            input_type="ops",
            output_type="ops",
        )
        def op_hatch_distance(
            command,
            channel,
            _,
            distance=None,
            difference=False,
            progress=False,
            data=None,
            **kwrgs,
        ):
            if distance is None:
                for op in data:
                    old = op.hatch_distance
                    channel(
                        _(
                            "Hatch Distance for '{name}' is currently: {distance}"
                        ).format(name=str(op), distance=old)
                    )
                return
            delta = 0
            for op in data:
                old = Length(op.hatch_distance)
                if progress:
                    s = float(old) + delta
                    delta += float(distance)
                elif difference:
                    s = float(old) + float(distance)
                else:
                    s = float(distance)
                if s < 0:
                    s = 0
                op.hatch_distance = Length(amount=s).length_mm
                channel(
                    _(
                        "Hatch Distance for '{name}' updated {old_distance} -> {distance}"
                    ).format(name=str(op), old_distance=old, distance=op.hatch_distance)
                )
                op.notify_update()
            return "ops", data

        @self.console_argument(
            "angle", type=Angle.parse, help=_("Set hatch-angle of operations")
        )
        @self.console_option(
            "difference",
            "d",
            type=bool,
            action="store_true",
            help=_("Change hatch-distance by this amount."),
        )
        @self.console_option(
            "progress",
            "p",
            type=bool,
            action="store_true",
            help=_("Change hatch-distance for each item in order"),
        )
        @self.console_command(
            "hatch-angle",
            help=_("hatch-angle <angle>"),
            input_type="ops",
            output_type="ops",
        )
        def op_hatch_distance(
            command,
            channel,
            _,
            angle=None,
            difference=False,
            progress=False,
            data=None,
            **kwrgs,
        ):
            if angle is None:
                for op in data:
                    old = f"{Angle.parse(op.hatch_angle).as_turns:.4f}turn"
                    old_hatch_angle_deg = (
                        f"{Angle.parse(op.hatch_angle).as_degrees:.4f}deg"
                    )
                    channel(
                        _(
                            "Hatch Angle for '{name}' is currently: {angle} ({angle_degree})"
                        ).format(
                            name=str(op), angle=old, angle_degree=old_hatch_angle_deg
                        )
                    )
                return
            delta = 0
            for op in data:
                old = Angle.parse(op.hatch_angle)
                if progress:
                    s = old + delta
                    delta += angle
                elif difference:
                    s = old + angle
                else:
                    s = angle
                s = Angle.radians(float(s))
                op.hatch_angle = f"{s.as_turns}turn"
                new_hatch_angle_turn = f"{s.as_turns:.4f}turn"
                new_hatch_angle_deg = f"{s.as_degrees:.4f}deg"

                channel(
                    _(
                        "Hatch Angle for '{name}' updated {old_angle} -> {angle} ({angle_degree})"
                    ).format(
                        name=str(op),
                        old_angle=f"{old.as_turns:.4f}turn",
                        angle=new_hatch_angle_turn,
                        angle_degree=new_hatch_angle_deg,
                    )
                )
                op.notify_update()
            return "ops", data

        @self.console_command(
            "disable",
            help=_("Disable the given operations"),
            input_type="ops",
            output_type="ops",
        )
        def op_disable(command, channel, _, data=None, **kwrgs):
            for op in data:
                no_op = True
                if hasattr(op, "output"):
                    try:
                        op.output = False
                        channel(_("Operation '{name}' disabled.").format(name=str(op)))
                        op.notify_update()
                        no_op = False
                    except AttributeError:
                        pass
                if no_op:
                    channel(
                        _("Operation '{name}' can't be disabled.").format(name=str(op))
                    )
            return "ops", data

        @self.console_command(
            "enable",
            help=_("Enable the given operations"),
            input_type="ops",
            output_type="ops",
        )
        def op_enable(command, channel, _, data=None, **kwrgs):
            for op in data:
                no_op = True
                if hasattr(op, "output"):
                    try:
                        op.output = True
                        channel(_("Operation '{name}' enabled.").format(name=str(op)))
                        op.notify_update()
                        no_op = False
                    except AttributeError:
                        pass
                if no_op:
                    channel(
                        _("Operation '{name}' can't be enabled.").format(name=str(op))
                    )
            return "ops", data

        # ==========
        # ELEMENT/OPERATION SUBCOMMANDS
        # ==========
        @self.console_command(
            "lock",
            help=_("Lock element (protect from manipulation)"),
            input_type="elements",
            output_type="elements",
        )
        def e_lock(data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            for e in data:
                e.lock = True
            self.signal("element_property_update", data)
            self.signal("refresh_scene", "Scene")
            return "elements", data

        @self.console_command(
            "unlock",
            help=_("Unlock element (allow manipulation)"),
            input_type="elements",
            output_type="elements",
        )
        def e_unlock(data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            for e in data:
                if hasattr(e, "lock"):
                    e.lock = False
            self.signal("element_property_update", data)
            self.signal("refresh_scene", "Scene")
            return "elements", data

        @self.console_option(
            "dx", "x", help=_("copy offset x (for elems)"), type=Length, default=0
        )
        @self.console_option(
            "dy", "y", help=_("copy offset y (for elems)"), type=Length, default=0
        )
        @self.console_command(
            "copy",
            help=_("Duplicate elements"),
            input_type=("elements", "ops"),
            output_type=("elements", "ops"),
        )
        def e_copy(data=None, data_type=None, dx=None, dy=None, **kwargs):
            if data is None:
                # Take tree selection for ops, scene selection for elements
                if data_type == "ops":
                    data = list(self.ops(selected=True))
                else:
                    data = list(self.elems(emphasized=True))

            if data_type == "ops":
                add_elem = list(map(copy, data))
                self.add_ops(add_elem)
                return "ops", add_elem
            else:
                if dx is None:
                    x_pos = 0
                else:
                    x_pos = dx
                if dy is None:
                    y_pos = 0
                else:
                    y_pos = dy
                add_elem = list(map(copy, data))
                matrix = None
                if x_pos != 0 or y_pos != 0:
                    matrix = Matrix.translate(dx, dy)
                for e in add_elem:
                    if matrix:
                        e.matrix *= matrix
                    self.elem_branch.add_node(e)
                self.signal("refresh_scene", "Scene")
                return "elements", add_elem

        @self.console_command(
            "delete", help=_("Delete elements"), input_type=("elements", "ops")
        )
        def e_delete(command, channel, _, data=None, data_type=None, **kwargs):
            channel(_("Deleting…"))
            if data_type == "elements":
                self.remove_elements(data)
            else:
                self.remove_operations(data)
            self.signal("tree_changed")

        # ==========
        # ELEMENT BASE
        # ==========

        @self.console_command(
            "elements",
            help=_("Show information about elements"),
        )
        def element(**kwargs):
            self(".element* list\n")

        @self.console_command(
            "element*",
            help=_("element*, all elements"),
            output_type="elements",
        )
        def element_star(**kwargs):
            return "elements", list(self.elems())

        @self.console_command(
            "element~",
            help=_("element~, all non-selected elements"),
            output_type="elements",
        )
        def element_not(**kwargs):
            return "elements", list(self.elems(emphasized=False))

        @self.console_command(
            "element",
            help=_("element, selected elements"),
            output_type="elements",
        )
        def element_base(**kwargs):
            return "elements", list(self.elems(emphasized=True))

        @self.console_command(
            r"element([0-9]+,?)+",
            help=_("element0,3,4,5: chain a list of specific elements"),
            regex=True,
            output_type="elements",
        )
        def element_chain(command, channel, _, **kwargs):
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
                    channel(_("index {index} out of range").format(index=value))
            return "elements", elements_list

        # ==========
        # REGMARK COMMANDS
        # ==========
        def move_nodes_to(target, nodes):
            for elem in nodes:
                target.drop(elem)

        @self.console_argument("cmd", type=str, help=_("free, clear, add"))
        @self.console_command(
            "regmark",
            help=_("regmark cmd"),
            input_type=(None, "elements"),
            output_type="elements",
            all_arguments_required=True,
        )
        def regmark(command, channel, _, data, cmd=None, **kwargs):
            # Move regmarks into the regular element tree and vice versa
            if cmd == "free":
                target = self.elem_branch
            else:
                target = self.reg_branch

            if data is None:
                data = list()
                if cmd == "free":
                    for item in list(self.regmarks()):
                        data.append(item)
                else:
                    for item in list(self.elems(emphasized=True)):
                        data.append(item)
            if cmd in ("free", "add"):
                if len(data) == 0:
                    channel(_("No elements to transfer"))
                else:
                    move_nodes_to(target, data)
            elif cmd == "clear":
                self.clear_regmarks()
                data = None
            else:
                # Unknown command
                channel(_("Invalid command, use one of add, free, clear"))
                data = None
            self.signal("tree_changed")
            return "elements", data

        # ==========
        # ELEMENT SUBCOMMANDS
        # ==========

        # @self.console_argument("step_size", type=int, help=_("element step size"))
        # @self.console_command(
        #     "step",
        #     help=_("step <element step-size>"),
        #     input_type="elements",
        #     output_type="elements",
        # )
        # def step_command(command, channel, _, data, step_size=None, **kwrgs):
        #     if step_size is None:
        #         found = False
        #         for element in data:
        #             if isinstance(element, SVGImage):
        #                 try:
        #                     step = element.values["raster_step"]
        #                 except KeyError:
        #                     step = 1
        #                 channel(
        #                     _("Image step for %s is currently: %s")
        #                     % (str(element), step)
        #                 )
        #                 found = True
        #         if not found:
        #             channel(_("No image element selected."))
        #         return
        #     for element in data:
        #         element.values["raster_step"] = str(step_size)
        #         m = element.transform
        #         tx = m.e
        #         ty = m.f
        #         element.transform = Matrix.scale(float(step_size), float(step_size))
        #         element.transform.post_translate(tx, ty)
        #         if hasattr(element, "node"):
        #             element.node.modified()
        #         self.signal("element_property_reload", element)
        #     return ("elements",)

        @self.console_command(
            "select",
            help=_("Set these values as the selection."),
            input_type="elements",
            output_type="elements",
        )
        def element_select_base(data=None, **kwargs):
            self.set_emphasis(data)
            return "elements", data

        @self.console_command(
            "select+",
            help=_("Add the input to the selection"),
            input_type="elements",
            output_type="elements",
        )
        def element_select_plus(data=None, **kwargs):
            elems = list(self.elems(emphasized=True))
            elems.extend(data)
            self.set_emphasis(elems)
            return "elements", elems

        @self.console_command(
            "select-",
            help=_("Remove the input data from the selection"),
            input_type="elements",
            output_type="elements",
        )
        def element_select_minus(data=None, **kwargs):
            elems = list(self.elems(emphasized=True))
            for e in data:
                try:
                    elems.remove(e)
                except ValueError:
                    pass
            self.set_emphasis(elems)
            return "elements", elems

        @self.console_command(
            "select^",
            help=_("Toggle the input data in the selection"),
            input_type="elements",
            output_type="elements",
        )
        def element_select_xor(data=None, **kwargs):
            elems = list(self.elems(emphasized=True))
            for e in data:
                try:
                    elems.remove(e)
                except ValueError:
                    elems.append(e)
            self.set_emphasis(elems)
            return "elements", elems

        @self.console_command(
            "list",
            help=_("Show information about the chained data"),
            input_type="elements",
            output_type="elements",
        )
        def element_list(command, channel, _, data=None, **kwargs):
            channel("----------")
            channel(_("Graphical Elements:"))
            index_list = list(self.elems())
            for e in data:
                i = index_list.index(e)
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                if e.emphasized:
                    channel(f"{i}: * {name}")
                else:
                    channel(f"{i}: {name}")
            channel("----------")
            return "elements", data

        @self.console_argument("start", type=int, help=_("elements start"))
        @self.console_argument("end", type=int, help=_("elements end"))
        @self.console_argument("step", type=int, help=_("elements step"))
        @self.console_command(
            "range",
            help=_("Subset selection by begin & end indices and step"),
            input_type="elements",
            output_type="elements",
        )
        def element_select_range(data=None, start=None, end=None, step=1, **kwargs):
            subelem = list()
            for e in range(start, end, step):
                try:
                    subelem.append(data[e])
                except IndexError:
                    pass
            self.set_emphasis(subelem)
            return "elements", subelem

        @self.console_command(
            "merge",
            help=_("merge elements"),
            input_type="elements",
            output_type="elements",
        )
        def element_merge(data=None, **kwargs):
            super_element = Path()
            for e in data:
                try:
                    path = e.as_path()
                except AttributeError:
                    continue
                try:
                    if super_element.stroke is None:
                        super_element.stroke = e.stroke
                except AttributeError:
                    pass
                try:
                    if super_element.fill is None:
                        super_element.fill = e.fill
                except AttributeError:
                    pass
                super_element += path
            self.remove_elements(data)
            node = self.elem_branch.add(path=super_element, type="elem path")
            self.set_node_emphasis(node, True)
            if self.classify_new:
                self.classify([node])
            return "elements", [node]

        @self.console_command(
            "subpath",
            help=_("break elements"),
            input_type="elements",
            output_type="elements",
        )
        def element_subpath(data=None, **kwargs):
            if not isinstance(data, list):
                data = list(data)
            elements_nodes = []
            elements = []
            for node in data:
                group_node = node.replace_node(type="group", label=node.label)
                try:
                    p = node.as_path()
                except AttributeError:
                    continue
                for subpath in p.as_subpaths():
                    subelement = Path(subpath)
                    elements.append(subelement)
                    group_node.add(path=subelement, type="elem path")
                elements_nodes.append(group_node)
                if self.classify_new:
                    self.classify(elements)
            return "elements", elements_nodes

        # ==========
        # ALIGN SUBTYPE
        # Align consist of top level node objects that can be manipulated within the scene.
        # ==========

        def _align_xy(
            channel,
            _,
            mode,
            bounds,
            elements,
            align_x=None,
            align_y=None,
            asgroup=None,
            **kwargs,
        ):
            """
            This routine prepares the data according to some validation.

            The complete validation stuff...
            """
            if elements is None:
                return
            if align_x is None or align_y is None:
                channel(_("You need to provide parameters for both x and y"))
                return
            align_bounds = None
            align_x = align_x.lower()
            align_y = align_y.lower()

            if align_x not in ("min", "max", "center", "none"):
                channel(_("Invalid alignment parameter for x"))
                return
            if align_y not in ("min", "max", "center", "none"):
                channel(_("Invalid alignment parameter for y"))
                return
            if mode == "default":
                if len(elements) < 2:
                    channel(_("No sense in aligning an element to itself"))
                    return
                # boundaries are the selection boundaries,
                # will be calculated later
            elif mode == "first":
                if len(elements) < 2:
                    channel(_("No sense in aligning an element to itself"))
                    return
                elements.sort(key=lambda n: n.emphasized_time)
                # Is there a noticeable difference?!
                # If not then we fall back to default
                if elements[0].emphasized_time != elements[1].emphasized_time:
                    align_bounds = elements[0].bounds
                    elements.pop(0)
            elif mode == "last":
                if len(elements) < 2:
                    channel(_("No sense in aligning an element to itself"))
                    return
                elements.sort(reverse=True, key=lambda n: n.emphasized_time)
                # Is there a noticeable difference?!
                # If not then we fall back to default
                if elements[0].emphasized_time != elements[1].emphasized_time:
                    align_bounds = elements[0].bounds
                    elements.pop(0)
            elif mode == "bed":
                align_bounds = bounds
            elif mode == "ref":
                align_bounds = bounds
            self.align_elements(
                data=elements,
                alignbounds=align_bounds,
                positionx=align_x,
                positiony=align_y,
                as_group=asgroup,
            )

        @self.console_command(
            "push",
            help=_("pushes the current align mode to the stack"),
            input_type="align",
            output_type="align",
        )
        def alignmode_push(channel, _, data, **kwargs):
            """
            Special command to push the current values on the stack
            """
            mode, group, bound, elements = data
            self._align_stack.append((mode, group, bound))
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "pop",
            help=_("pushes the current align mode to the stack"),
            input_type="align",
            output_type="align",
        )
        def alignmode_pop(channel, _, data, **kwargs):
            """
            Special command to push the current values on the stack
            """
            mode, group, bound, elements = data
            if len(self._align_stack) > 0:
                (
                    self._align_mode,
                    self._align_group,
                    self._align_boundaries,
                ) = self._align_stack.pop()
                mode = self._align_mode
                group = self._align_group
                bound = self._align_boundaries
            channel(_("New alignmode = {mode}").format(mode=self._align_mode))
            if self._align_boundaries is not None:
                channel(
                    _("Align boundaries = {bound}").format(
                        bound=str(self._align_boundaries)
                    )
                )
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "group",
            help=_("Set the requested alignment to treat selection as group"),
            input_type="align",
            output_type="align",
        )
        def alignmode_first(command, channel, _, data, **kwargs):
            mode, group, bound, elements = data
            group = True
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "individual",
            help=_("Set the requested alignment to treat selection as individuals"),
            input_type="align",
            output_type="align",
        )
        def alignmode_first(command, channel, _, data, **kwargs):
            mode, group, bound, elements = data
            group = False
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "default",
            help=_("align within selection - all equal"),
            input_type="align",
            output_type="align",
        )
        def alignmode_default(channel, _, data, **kwargs):
            """
            Set the alignment mode to default
            """
            mode, group, bound, elements = data
            mode = "default"
            bound = None
            self._align_mode = mode
            self._align_boundaries = bound
            channel(_("New alignmode = {mode}").format(mode=self._align_mode))
            if self._align_boundaries is not None:
                channel(
                    _("Align boundaries = {bound}").format(
                        bound=str(self._align_boundaries)
                    )
                )
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "first",
            help=_("Set the requested alignment to first element selected"),
            input_type="align",
            output_type="align",
        )
        def alignmode_first(command, channel, _, data, **kwargs):
            mode, group, bound, elements = data
            mode = "first"
            bound = None
            self._align_mode = mode
            self._align_boundaries = bound
            channel(_("New alignmode = {mode}").format(mode=self._align_mode))
            if self._align_boundaries is not None:
                channel(
                    _("Align boundaries = {bound}").format(
                        bound=str(self._align_boundaries)
                    )
                )
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "last",
            help=_("Set the requested alignment to last element selected"),
            input_type="align",
            output_type="align",
        )
        def alignmode_last(command, channel, _, data, **kwargs):
            mode, group, bound, elements = data
            mode = "last"
            bound = None
            self._align_mode = mode
            self._align_boundaries = bound
            channel(_("New alignmode = {mode}").format(mode=self._align_mode))
            if self._align_boundaries is not None:
                channel(
                    _("Align boundaries = {bound}").format(
                        bound=str(self._align_boundaries)
                    )
                )
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "bed",
            help=_("Set the requested alignment to within the bed"),
            input_type="align",
            output_type="align",
        )
        def alignmode_bed(channel, _, data, **kwargs):
            mode, group, bound, elements = data
            mode = "bed"
            device_width = self.length_x("100%")
            device_height = self.length_y("100%")
            bound = (0, 0, device_width, device_height)
            self._align_mode = mode
            self._align_boundaries = bound
            channel(_("New alignmode = {mode}").format(mode=self._align_mode))
            if self._align_boundaries is not None:
                channel(
                    _("Align boundaries = {bound}").format(
                        bound=str(self._align_boundaries)
                    )
                )
            return "align", (mode, group, bound, elements)

        @self.console_option(
            "boundaries", "b", type=self.bounds, parallel_cast=True, nargs=4
        )
        @self.console_command(
            "ref",
            help=_("Set the requested alignment to the reference object"),
            input_type="align",
            output_type="align",
        )
        def alignmode_ref(channel, _, data, boundaries, **kwargs):
            mode, group, bound, elements = data
            if boundaries is None:
                channel(
                    _(
                        "You need to provide the boundaries for align-mode {mode}"
                    ).format(mode="ref")
                )
                return
            mode = "ref"
            bound = boundaries
            self._align_mode = mode
            self._align_boundaries = bound
            channel(_("New alignmode = {mode}").format(mode=self._align_mode))
            if self._align_boundaries is not None:
                channel(
                    _("Align boundaries = {bound}").format(
                        bound=str(self._align_boundaries)
                    )
                )
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "align",
            help=_("align selected elements"),
            input_type=("elements", None),
            output_type="align",
        )
        def align_elements_base(
            command, channel, _, data=None, remainder=None, **kwargs
        ):
            """
            Base align commands. Triggers other base commands within the command context
            'align'.
            """
            if not remainder:
                channel(
                    "top\nbottom\nleft\nright\ncenter\ncenterh\ncenterv\nspaceh\nspacev\n"
                    "<any valid svg:Preserve Aspect Ratio, eg xminymin>"
                )
                # Bunch of other things.
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            # Element conversion.
            # We need to establish, if for a given node within a group
            # all it's siblings are selected as well, if that's the case
            # then use the parent instead - unless there are no other elements
            # selected ie all selected belong to the same group...
            d = list()
            elem_branch = self.elem_branch
            for node in data:
                snode = node
                if snode.parent and snode.parent is not elem_branch:
                    # I need all other siblings
                    singular = False
                    for n in list(node.parent.children):
                        if n not in data:
                            singular = True
                            break
                    if not singular:
                        while (
                            snode.parent
                            and snode.parent is not elem_branch
                            and snode.parent.type != "file"
                        ):
                            snode = snode.parent
                if snode is not None and snode not in d:
                    d.append(snode)
            if len(d) == 1 and d[0].type == "group":
                # This is just on single group - expand...
                data = list(d[0].flat(emphasized=True, types=elem_nodes))
                for n in data:
                    n._emphasized_time = d[0]._emphasized_time
            else:
                data = d
            return "align", (
                self._align_mode,
                self._align_group,
                self._align_boundaries,
                data,
            )

        @self.console_argument(
            "alignx", type=str, help=_("One of 'min', 'center', 'max', 'none'")
        )
        @self.console_argument(
            "aligny", type=str, help=_("One of 'min', 'center', 'max', 'none'")
        )
        @self.console_command(
            "xy",
            help=_("align elements in x and y"),
            input_type="align",
            output_type="align",
        )
        def subtype_align_xy(
            command,
            channel,
            _,
            data=None,
            alignx=None,
            aligny=None,
            **kwargs,
        ):
            mode, group, bound, elements = data
            _align_xy(channel, _, mode, bound, elements, alignx, aligny, group)
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "top",
            help=_("align elements at top"),
            input_type="align",
            output_type="align",
        )
        def subtype_align_top(command, channel, _, data=None, **kwargs):
            mode, group, bound, elements = data
            _align_xy(channel, _, mode, bound, elements, "none", "min", group)
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "bottom",
            help=_("align elements at bottom"),
            input_type="align",
            output_type="align",
        )
        def subtype_align_bottom(command, channel, _, data=None, **kwargs):
            mode, group, bound, elements = data
            _align_xy(channel, _, mode, bound, elements, "none", "max", group)
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "left",
            help=_("align elements at left"),
            input_type="align",
            output_type="align",
        )
        def subtype_align_left(command, channel, _, data=None, **kwargs):
            mode, group, bound, elements = data
            _align_xy(channel, _, mode, bound, elements, "min", "none", group)
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "right",
            help=_("align elements at right"),
            input_type="align",
            output_type="align",
        )
        def subtype_align_right(command, channel, _, data=None, **kwargs):
            mode, group, bound, elements = data
            _align_xy(channel, _, mode, bound, elements, "max", "none", group)
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "center",
            help=_("align elements at center"),
            input_type="align",
            output_type="align",
        )
        def subtype_align_center(command, channel, _, data=None, **kwargs):
            mode, group, bound, elements = data
            _align_xy(
                command, channel, _, mode, bound, elements, "center", "center", group
            )
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "centerh",
            help=_("align elements at center horizontally"),
            input_type="align",
            output_type="align",
        )
        def subtype_align_centerh(command, channel, _, data=None, **kwargs):
            mode, group, bound, elements = data
            _align_xy(channel, _, mode, bound, elements, "center", "none", group)
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "centerv",
            help=_("align elements at center vertically"),
            input_type="align",
            output_type="align",
        )
        def subtype_align_centerv(command, channel, _, data=None, **kwargs):
            mode, group, bound, elements = data
            _align_xy(channel, _, mode, bound, elements, "none", "center", group)
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "spaceh",
            help=_("align elements across horizontal space"),
            input_type="align",
            output_type="align",
        )
        def subtype_align_spaceh(command, channel, _, data=None, **kwargs):
            mode, group, bound, elements = data
            boundary_points = []
            for node in elements:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            if len(elements) <= 2:  # Cannot distribute 2 or fewer items.
                return "align", (mode, group, bound, elements)
            left_edge = min([e[0] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            dim_total = right_edge - left_edge
            dim_available = dim_total
            for node in elements:
                bounds = node.bounds
                dim_available -= bounds[2] - bounds[0]
            distributed_distance = dim_available / (len(elements) - 1)
            elements.sort(key=lambda n: n.bounds[0])  # sort by left edge
            dim_pos = left_edge

            haslock = False
            for node in elements:
                if hasattr(node, "lock") and node.lock and not self.lock_allows_move:
                    haslock = True
                    break
            if haslock:
                channel(
                    _("Your selection contains a locked element, that cannot be moved")
                )
                return
            for node in elements:
                subbox = node.bounds
                delta = subbox[0] - dim_pos
                matrix = f"translate({-delta}, 0)"
                if delta != 0:
                    for q in node.flat(types=elem_nodes):
                        try:
                            q.matrix *= matrix
                            q.modified()
                        except AttributeError:
                            continue
                dim_pos += subbox[2] - subbox[0] + distributed_distance
            return "align", (mode, group, bound, elements)

        @self.console_command(
            "spacev",
            help=_("align elements down vertical space"),
            input_type="align",
            output_type="align",
        )
        def subtype_align_spacev(command, channel, _, data=None, **kwargs):
            mode, group, bound, elements = data
            boundary_points = []
            for node in elements:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            if len(elements) <= 2:  # Cannot distribute 2 or fewer items.
                return "align", (mode, group, bound, elements)
            top_edge = min([e[1] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])
            dim_total = bottom_edge - top_edge
            dim_available = dim_total
            for node in elements:
                bounds = node.bounds
                dim_available -= bounds[3] - bounds[1]
            distributed_distance = dim_available / (len(elements) - 1)
            elements.sort(key=lambda n: n.bounds[1])  # sort by top edge
            dim_pos = top_edge

            haslock = False
            for node in elements:
                if hasattr(node, "lock") and node.lock and not self.lock_allows_move:
                    haslock = True
                    break
            if haslock:
                channel(
                    _("Your selection contains a locked element, that cannot be moved")
                )
                return
            for node in elements:
                subbox = node.bounds
                delta = subbox[1] - dim_pos
                matrix = f"translate(0, {-delta})"
                if delta != 0:
                    for q in node.flat(types=elem_nodes):
                        try:
                            q.matrix *= matrix
                            q.modified()
                        except AttributeError:
                            continue
                dim_pos += subbox[3] - subbox[1] + distributed_distance
            return "align", (mode, group, bound, elements)

        @self.console_argument(
            "preserve_aspect_ratio",
            type=str,
            default="none",
            help="preserve aspect ratio value",
        )
        @self.console_command(
            "view",
            help=_("align elements within viewbox"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(
            command, channel, _, data=None, preserve_aspect_ratio="none", **kwargs
        ):
            """
            Align the elements to within the bed according to SVG Viewbox rules. The following aspect ratios
            are valid. These should define all the valid methods of centering data within the laser bed.
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
            "none"
            """
            mode, group, bound, elements = data
            boundary_points = []
            for node in elements:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return

            haslock = False
            for node in elements:
                if hasattr(node, "lock") and node.lock and not self.lock_allows_move:
                    haslock = True
                    break
            if haslock:
                channel(
                    _("Your selection contains a locked element, that cannot be moved")
                )
                return
            left_edge = min([e[0] for e in boundary_points])
            top_edge = min([e[1] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])

            if preserve_aspect_ratio in (
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
                for node in elements:
                    device_width = self.length_x("100%")
                    device_height = self.length_y("100%")

                    matrix = Viewbox.viewbox_transform(
                        0,
                        0,
                        device_width,
                        device_height,
                        left_edge,
                        top_edge,
                        right_edge - left_edge,
                        bottom_edge - top_edge,
                        preserve_aspect_ratio,
                    )
                    for q in node.flat(types=elem_nodes):
                        try:
                            q.matrix *= matrix
                            q.modified()
                        except AttributeError:
                            continue
                    for q in node.flat(types=("file", "group")):
                        q.modified()
            return "align", (mode, group, bound, elements)

        # ==========
        # GRID SUBTYPE
        # ==========

        @self.console_argument("c", type=int, help=_("Number of columns"))
        @self.console_argument("r", type=int, help=_("Number of rows"))
        @self.console_argument("x", type=str, help=_("x distance"))
        @self.console_argument("y", type=str, help=_("y distance"))
        @self.console_option(
            "origin",
            "o",
            type=int,
            nargs=2,
            help=_("Position of original in matrix (e.g '2,2' or '4,3')"),
        )
        @self.console_command(
            "grid",
            help=_("grid <columns> <rows> <x_distance> <y_distance> <origin>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_grid(
            command,
            channel,
            _,
            c: int,
            r: int,
            x: str,
            y: str,
            origin=None,
            data=None,
            **kwargs,
        ):
            if r is None:
                raise CommandSyntaxError
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No item selected."))
                return
            try:
                bounds = Node.union_bounds(data)
                width = bounds[2] - bounds[0]
                height = bounds[3] - bounds[1]
            except TypeError:
                raise CommandSyntaxError
            if x is None:
                x = "100%"
            if y is None:
                y = "100%"
            x = float(Length(x, relative_length=Length(amount=width).length_mm))
            y = float(Length(y, relative_length=Length(amount=height).length_mm))
            if origin is None:
                origin = (1, 1)
            cx, cy = origin
            data_out = list(data)
            if cx is None:
                cx = 1
            if cy is None:
                cy = 1
            start_x = -1 * x * (cx - 1)
            start_y = -1 * y * (cy - 1)
            y_pos = start_y
            for j in range(r):
                x_pos = start_x
                for k in range(c):
                    if j != (cy - 1) or k != (cx - 1):
                        add_elem = list(map(copy, data))
                        for e in add_elem:
                            e.matrix *= Matrix.translate(x_pos, y_pos)
                            self.elem_branch.add_node(e)
                        data_out.extend(add_elem)
                    x_pos += x
                y_pos += y
            self.signal("refresh_scene", "Scene")
            return "elements", data_out

        @self.console_argument("repeats", type=int, help=_("Number of repeats"))
        @self.console_argument("radius", type=self.length, help=_("Radius"))
        @self.console_argument("startangle", type=Angle.parse, help=_("Start-Angle"))
        @self.console_argument("endangle", type=Angle.parse, help=_("End-Angle"))
        @self.console_option(
            "rotate",
            "r",
            type=bool,
            action="store_true",
            help=_("Rotate copies towards center?"),
        )
        @self.console_option(
            "deltaangle",
            "d",
            type=Angle.parse,
            help=_("Delta-Angle (if omitted will take (end-start)/repeats )"),
        )
        @self.console_command(
            "radial",
            help=_("radial <repeats> <radius> <startangle> <endangle> <rotate>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_radial(
            command,
            channel,
            _,
            repeats: int,
            radius=None,
            startangle=None,
            endangle=None,
            rotate=None,
            deltaangle=None,
            data=None,
            **kwargs,
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0 and self._emphasized_bounds is None:
                channel(_("No item selected."))
                return

            if repeats is None:
                raise CommandSyntaxError
            if repeats <= 1:
                raise CommandSyntaxError(_("repeats should be greater or equal to 2"))
            if radius is None:
                radius = 0

            if startangle is None:
                startangle = Angle.parse("0deg")
            if endangle is None:
                endangle = Angle.parse("360deg")
            if rotate is None:
                rotate = False

            # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
            bounds = Node.union_bounds(data)
            if bounds is None:
                return
            width = bounds[2] - bounds[0]

            data_out = list(data)
            if deltaangle is None:
                segment_len = (endangle.as_radians - startangle.as_radians) / repeats
            else:
                segment_len = deltaangle.as_radians
            # Notabene: we are following the cartesian system here, but as the Y-Axis is top screen to bottom screen,
            # the perceived angle travel is CCW (which is counter-intuitive)
            currentangle = startangle.as_radians
            # bounds = self._emphasized_bounds
            center_x = (bounds[2] + bounds[0]) / 2.0 - radius
            center_y = (bounds[3] + bounds[1]) / 2.0

            # print ("repeats: %d, Radius: %.1f" % (repeats, radius))
            # print ("Center: %.1f, %.1f" % (center_x, center_y))
            # print ("Startangle, Endangle, segment_len: %.1f, %.1f, %.1f" % (180 * startangle.as_radians / pi, 180 * endangle.as_radians / pi, 180 * segment_len / pi))

            currentangle = segment_len
            for cc in range(1, repeats):
                # print ("Angle: %f rad = %f deg" % (currentangle, currentangle/pi * 180))
                add_elem = list(map(copy, data))
                for e in add_elem:
                    if rotate:
                        x_pos = -1 * radius
                        y_pos = 0
                        # e *= "translate(%f, %f)" % (x_pos, y_pos)
                        e *= f"rotate({currentangle}rad, {center_x}, {center_y})"
                    else:
                        x_pos = -1 * radius + radius * cos(currentangle)
                        y_pos = radius * sin(currentangle)
                        e *= f"translate({x_pos}, {y_pos})"

                self.add_elems(add_elem)
                data_out.extend(add_elem)

                currentangle += segment_len

            self.signal("refresh_scene", "Scene")
            return "elements", data_out

        @self.console_argument("copies", type=int, help=_("Number of copies"))
        @self.console_argument("radius", type=self.length, help=_("Radius"))
        @self.console_argument("startangle", type=Angle.parse, help=_("Start-Angle"))
        @self.console_argument("endangle", type=Angle.parse, help=_("End-Angle"))
        @self.console_option(
            "rotate",
            "r",
            type=bool,
            action="store_true",
            help=_("Rotate copies towards center?"),
        )
        @self.console_option(
            "deltaangle",
            "d",
            type=Angle.parse,
            help=_("Delta-Angle (if omitted will take (end-start)/copies )"),
        )
        @self.console_command(
            "circ_copy",
            help=_("circ_copy <copies> <radius> <startangle> <endangle> <rotate>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_circularcopies(
            command,
            channel,
            _,
            copies: int,
            radius=None,
            startangle=None,
            endangle=None,
            rotate=None,
            deltaangle=None,
            data=None,
            **kwargs,
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0 and self._emphasized_bounds is None:
                channel(_("No item selected."))
                return

            if copies is None:
                raise CommandSyntaxError
            if copies <= 0:
                copies = 1
            if radius is None:
                radius = 0

            if startangle is None:
                startangle = Angle.parse("0deg")
            if endangle is None:
                endangle = Angle.parse("360deg")
            if rotate is None:
                rotate = False

            # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
            bounds = Node.union_bounds(data)
            if bounds is None:
                return
            width = bounds[2] - bounds[0]

            data_out = list(data)
            if deltaangle is None:
                segment_len = (endangle.as_radians - startangle.as_radians) / copies
            else:
                segment_len = deltaangle.as_radians
            # Notabene: we are following the cartesian system here, but as the Y-Axis is top screen to bottom screen,
            # the perceived angle travel is CCW (which is counter-intuitive)
            currentangle = startangle.as_radians
            # bounds = self._emphasized_bounds
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            for cc in range(copies):
                # print ("Angle: %f rad = %f deg" % (currentangle, currentangle/pi * 180))
                add_elem = list(map(copy, data))
                for e in add_elem:
                    if rotate:
                        x_pos = radius
                        y_pos = 0
                        e *= f"translate({x_pos}, {y_pos})"
                        e *= f"rotate({currentangle}rad, {center_x}, {center_y})"
                    else:
                        x_pos = radius * cos(currentangle)
                        y_pos = radius * sin(currentangle)
                        e *= f"translate({x_pos}, {y_pos})"

                self.add_elems(add_elem)
                data_out.extend(add_elem)
                currentangle += segment_len

            self.signal("refresh_scene", "Scene")
            return "elements", data_out

        @self.console_argument(
            "corners", type=int, help=_("Number of corners/vertices")
        )
        @self.console_argument(
            "cx", type=self.length_x, help=_("X-Value of polygon's center")
        )
        @self.console_argument(
            "cy", type=self.length_y, help=_("Y-Value of polygon's center")
        )
        @self.console_argument(
            "radius",
            type=self.length_x,
            help=_("Radius (length of side if --side_length is used)"),
        )
        @self.console_option("startangle", "s", type=Angle.parse, help=_("Start-Angle"))
        @self.console_option(
            "inscribed",
            "i",
            type=bool,
            action="store_true",
            help=_("Shall the polygon touch the inscribing circle?"),
        )
        @self.console_option(
            "side_length",
            "l",
            type=bool,
            action="store_true",
            help=_(
                "Do you want to treat the length value for radius as the length of one edge instead?"
            ),
        )
        @self.console_option(
            "radius_inner",
            "r",
            type=str,
            help=_("Alternating radius for every other vertex"),
        )
        @self.console_option(
            "alternate_seq",
            "a",
            type=int,
            help=_(
                "Length of alternating sequence (1 for starlike figures, >=2 for more gear-like patterns)"
            ),
        )
        @self.console_option(
            "density", "d", type=int, help=_("Amount of vertices to skip")
        )
        @self.console_command(
            "shape",
            help=_(
                "shape <corners> <x> <y> <r> <startangle> <inscribed> or shape <corners> <r>"
            ),
            input_type=("elements", None),
            output_type="elements",
        )
        def element_shape(
            command,
            channel,
            _,
            corners,
            cx,
            cy,
            radius,
            startangle=None,
            inscribed=None,
            side_length=None,
            radius_inner=None,
            alternate_seq=None,
            density=None,
            data=None,
            **kwargs,
        ):
            if corners is None:
                raise CommandSyntaxError

            if cx is None:
                if corners <= 2:
                    raise CommandSyntaxError(
                        _(
                            "Please provide at least one additional value (which will act as radius then)"
                        )
                    )
                cx = 0
            if cy is None:
                cy = 0
            if radius is None:
                radius = 0
            if corners <= 2:
                # No need to look at side_length parameter as we are considering the radius value as an edge anyway...
                if startangle is None:
                    startangle = Angle.parse("0deg")

                star_points = [(cx, cy)]
                if corners == 2:
                    star_points += [
                        (
                            cx + cos(startangle.as_radians) * radius,
                            cy + sin(startangle.as_radians) * radius,
                        )
                    ]
            else:
                # do we have something like 'polyshape 3 4cm' ? If yes, reassign the parameters
                if radius is None:
                    radius = cx
                    cx = 0
                    cy = 0
                if startangle is None:
                    startangle = Angle.parse("0deg")

                if alternate_seq is None:
                    if radius_inner is None:
                        alternate_seq = 0
                    else:
                        alternate_seq = 1

                if density is None:
                    density = 1
                if density < 1 or density > corners:
                    density = 1

                # Do we have to consider the radius value as the length of one corner?
                if side_length is not None:
                    # Let's recalculate the radius then...
                    # d_oc = s * csc( pi / n)
                    radius = 0.5 * radius / sin(pi / corners)

                if radius_inner is None:
                    radius_inner = radius
                else:
                    try:
                        radius_inner = float(
                            Length(radius_inner, relative_length=radius)
                        )
                    except ValueError:
                        raise CommandSyntaxError

                if inscribed:
                    if side_length is None:
                        radius = radius / cos(pi / corners)
                    else:
                        channel(
                            _(
                                "You have as well provided the --side_length parameter, this takes precedence, so --inscribed is ignored"
                            )
                        )

                if alternate_seq < 1:
                    radius_inner = radius

                # print(
                #   "Your parameters are:\n cx=%.1f, cy=%.1f\n radius=%.1f, inner=%.1f\n corners=%d, density=%d\n seq=%d, angle=%.1f"
                #   % (cx, cy, radius, radius_inner, corners, density, alternate_seq, startangle)
                # )
                pts = []
                i_angle = startangle.as_radians
                delta_angle = tau / corners
                ct = 0
                for j in range(corners):
                    if ct < alternate_seq:
                        r = radius
                    #    dbg = "outer"
                    else:
                        r = radius_inner
                    #    dbg = "inner"
                    thisx = cx + r * cos(i_angle)
                    thisy = cy + r * sin(i_angle)
                    # print(
                    #    "pt %d, Angle=%.1f: %s radius=%.1f: (%.1f, %.1f)"
                    #    % (j, i_angle / pi * 180, dbg, r, thisx, thisy)
                    # )
                    ct += 1
                    if ct >= 2 * alternate_seq:
                        ct = 0
                    if j == 0:
                        firstx = thisx
                        firsty = thisy
                    i_angle += delta_angle
                    pts += [(thisx, thisy)]
                # Close the path
                pts += [(firstx, firsty)]

                star_points = [(pts[0][0], pts[0][1])]
                idx = density
                while idx != 0:
                    star_points += [(pts[idx][0], pts[idx][1])]
                    idx += density
                    if idx >= corners:
                        idx -= corners
                if len(star_points) < corners:
                    ct = 0
                    possible_combinations = ""
                    for i in range(corners - 1):
                        j = i + 2
                        if gcd(j, corners) == 1:
                            if ct % 3 == 0:
                                possible_combinations += (
                                    f"\n shape {corners} ... -d {j}"
                                )
                            else:
                                possible_combinations += (
                                    f", shape {corners} ... -d {j} "
                                )
                            ct += 1
                    channel(
                        _("Just for info: we have missed {count} vertices...").format(
                            count=(corners - len(star_points))
                        )
                    )
                    channel(
                        _(
                            "To hit all, the density parameters should be e.g. {combinations}"
                        ).format(combinations=possible_combinations)
                    )

            poly_path = Polygon(star_points)
            node = self.elem_branch.add(shape=poly_path, type="elem polyline")
            node.stroke = self.default_stroke
            node.fill = self.default_fill
            self.set_emphasis([node])
            node.focus()
            if data is None:
                data = list()
            data.append(poly_path)
            return "elements", data

        @self.console_option("dpi", "d", default=500, type=float)
        @self.console_command(
            "render",
            help=_("Convert given elements to a raster image"),
            input_type=(None, "elements"),
            output_type="image",
        )
        def render_elements(command, channel, _, dpi=500.0, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            reverse = self.classify_reverse
            if reverse:
                data = list(reversed(data))
            make_raster = self.lookup("render-op/make_raster")
            if not make_raster:
                channel(_("No renderer is registered to perform render."))
                return

            bounds = Node.union_bounds(data, attr="paint_bounds")
            if bounds is None:
                return
            xmin, ymin, xmax, ymax = bounds
            if isinf(xmin):
                channel(_("No bounds for selected elements."))
                return
            width = xmax - xmin
            height = ymax - ymin

            dots_per_units = dpi / UNITS_PER_INCH
            new_width = width * dots_per_units
            new_height = height * dots_per_units
            new_height = max(new_height, 1)
            new_width = max(new_width, 1)

            image = make_raster(
                data,
                bounds=bounds,
                width=new_width,
                height=new_height,
            )
            matrix = Matrix.scale(width / new_width, height / new_height)
            matrix.post_translate(bounds[0], bounds[1])

            image_node = ImageNode(image=image, matrix=matrix, dpi=dpi)
            self.elem_branch.add_node(image_node)
            self.signal("refresh_scene", "Scene")

            return "image", [image_node]

        # ==========
        # ELEMENT/SHAPE COMMANDS
        # ==========
        @self.console_argument("x_pos", type=Length)
        @self.console_argument("y_pos", type=Length)
        @self.console_argument("r_pos", type=Length)
        @self.console_command(
            "circle",
            help=_("circle <x> <y> <r>"),
            input_type=("elements", None),
            output_type="elements",
            all_arguments_required=True,
        )
        def element_circle(channel, _, x_pos, y_pos, r_pos, data=None, **kwargs):
            circ = Circle(cx=float(x_pos), cy=float(y_pos), r=float(r_pos))
            if circ.is_degenerate():
                channel(_("Shape is degenerate."))
                return "elements", data
            node = self.elem_branch.add(
                shape=circ,
                type="elem ellipse",
                stroke=self.default_stroke,
                fill=self.default_fill,
            )
            self.set_emphasis([node])
            node.focus()
            if data is None:
                data = list()
            data.append(node)
            return "elements", data

        @self.console_argument("r_pos", type=Length)
        @self.console_command(
            "circle_r",
            help=_("circle_r <r>"),
            input_type=("elements", None),
            output_type="elements",
            all_arguments_required=True,
        )
        def element_circle_r(channel, _, r_pos, data=None, **kwargs):
            circ = Circle(r=float(r_pos))
            if circ.is_degenerate():
                channel(_("Shape is degenerate."))
                return "elements", data
            node = self.elem_branch.add(shape=circ, type="elem ellipse")
            node.stroke = self.default_stroke
            node.fill = self.default_fill
            self.set_emphasis([node])
            node.focus()
            if data is None:
                data = list()
            data.append(node)
            return "elements", data

        @self.console_argument("x_pos", type=Length)
        @self.console_argument("y_pos", type=Length)
        @self.console_argument("rx_pos", type=Length)
        @self.console_argument("ry_pos", type=Length)
        @self.console_command(
            "ellipse",
            help=_("ellipse <cx> <cy> <rx> <ry>"),
            input_type=("elements", None),
            output_type="elements",
            all_arguments_required=True,
        )
        def element_ellipse(
            channel, _, x_pos, y_pos, rx_pos, ry_pos, data=None, **kwargs
        ):
            ellip = Ellipse(
                cx=float(x_pos), cy=float(y_pos), rx=float(rx_pos), ry=float(ry_pos)
            )
            if ellip.is_degenerate():
                channel(_("Shape is degenerate."))
                return "elements", data
            node = self.elem_branch.add(shape=ellip, type="elem ellipse")
            node.stroke = self.default_stroke
            node.fill = self.default_fill
            self.set_emphasis([node])
            node.focus()
            if data is None:
                data = list()
            data.append(node)
            return "elements", data

        @self.console_argument(
            "x_pos",
            type=self.length_x,
            help=_("x position for top left corner of rectangle."),
        )
        @self.console_argument(
            "y_pos",
            type=self.length_y,
            help=_("y position for top left corner of rectangle."),
        )
        @self.console_argument(
            "width", type=self.length_x, help=_("width of the rectangle.")
        )
        @self.console_argument(
            "height", type=self.length_y, help=_("height of the rectangle.")
        )
        @self.console_option(
            "rx", "x", type=self.length_x, help=_("rounded rx corner value.")
        )
        @self.console_option(
            "ry", "y", type=self.length_y, help=_("rounded ry corner value.")
        )
        @self.console_command(
            "rect",
            help=_("adds rectangle to scene"),
            input_type=("elements", None),
            output_type="elements",
            all_arguments_required=True,
        )
        def element_rect(
            channel,
            _,
            x_pos,
            y_pos,
            width,
            height,
            rx=None,
            ry=None,
            data=None,
            **kwargs,
        ):
            """
            Draws a svg rectangle with optional rounded corners.
            """
            rect = Rect(x=x_pos, y=y_pos, width=width, height=height, rx=rx, ry=ry)
            if rect.is_degenerate():
                channel(_("Shape is degenerate."))
                return "elements", data
            node = self.elem_branch.add(shape=rect, type="elem rect")
            node.stroke = self.default_stroke
            node.fill = self.default_fill
            self.set_emphasis([node])
            node.focus()
            if data is None:
                data = list()
            data.append(node)
            return "elements", data

        @self.console_argument("x0", type=self.length_x, help=_("start x position"))
        @self.console_argument("y0", type=self.length_y, help=_("start y position"))
        @self.console_argument("x1", type=self.length_x, help=_("end x position"))
        @self.console_argument("y1", type=self.length_y, help=_("end y position"))
        @self.console_command(
            "line",
            help=_("adds line to scene"),
            input_type=("elements", None),
            output_type="elements",
            all_arguments_required=True,
        )
        def element_line(command, x0, y0, x1, y1, data=None, **kwargs):
            """
            Draws a svg line in the scene.
            """
            simple_line = SimpleLine(x0, y0, x1, y1)
            node = self.elem_branch.add(shape=simple_line, type="elem line")
            node.stroke = self.default_stroke
            self.set_emphasis([node])
            node.focus()
            if data is None:
                data = list()
            data.append(node)
            return "elements", data

        @self.console_option(
            "size", "s", type=float, default=16, help=_("font size to for object")
        )
        @self.console_argument("text", type=str, help=_("quoted string of text"))
        @self.console_command(
            "text",
            help=_("text <text>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_text(
            command, channel, _, data=None, text=None, size=None, **kwargs
        ):
            if text is None:
                channel(_("No text specified"))
                return
            node = self.elem_branch.add(
                text=text, matrix=Matrix(f"scale({UNITS_PER_PIXEL})"), type="elem text"
            )
            node.font_size = size
            node.stroke = self.default_stroke
            node.fill = self.default_fill
            self.set_emphasis([node])
            node.focus()
            if data is None:
                data = list()
            data.append(node)
            return "elements", data

        @self.console_argument(
            "anchor", type=str, default="start", help=_("set text anchor")
        )
        @self.console_command(
            "text-anchor",
            help=_("set text object text-anchor; start, middle, end"),
            input_type=(
                None,
                "elements",
            ),
            hidden=True,
            output_type="elements",
        )
        def element_text_anchor(command, channel, _, data, anchor=None, **kwargs):
            if anchor not in ("start", "middle", "end"):
                raise CommandSyntaxError(
                    _("Only 'start', 'middle', and 'end' are valid anchors.")
                )
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            for e in data:
                if hasattr(e, "lock") and e.lock:
                    channel(
                        _("Can't modify a locked element: {name}").format(name=str(e))
                    )
                    continue
                if e.type == "elem text":
                    old_anchor = e.anchor
                    e.anchor = anchor
                    channel(f"Node {e} anchor changed from {old_anchor} to {anchor}")

                e.altered()
            return "elements", data

        @self.console_argument(
            "mlist", type=Length, help=_("list of positions"), nargs="*"
        )
        @self.console_command(
            ("polygon", "polyline"),
            help=_("poly(gon|line) (Length Length)*"),
            input_type=("elements", None),
            output_type="elements",
            all_arguments_required=True,
        )
        def element_poly(command, channel, _, mlist, data=None, **kwargs):
            try:
                pts = [float(Length(p)) for p in mlist]
                if command == "polygon":
                    shape = Polygon(pts)
                else:
                    shape = Polyline(pts)
            except ValueError:
                raise CommandSyntaxError(
                    _("Must be a list of spaced delimited length pairs.")
                )
            if shape.is_degenerate():
                channel(_("Shape is degenerate."))
                return "elements", data
            node = self.elem_branch.add(shape=shape, type="elem polyline")
            node.stroke = self.default_stroke
            node.fill = self.default_fill
            self.set_emphasis([node])
            node.focus()
            if data is None:
                data = list()
            data.append(node)
            return "elements", data

        @self.console_command(
            "path",
            help=_("Convert any shapes to paths"),
            input_type="shapes",
            output_type="shapes",
        )
        def element_path_convert(data, **kwargs):
            paths = []
            for e in data:
                paths.append(abs(Path(e)))
            return "shapes", paths

        @self.console_command(
            "numpath",
            help=_("Convert any element nodes to numpath nodes"),
            input_type="elements",
            output_type="elements",
        )
        def element_path_convert(data, **kwargs):
            if data is None:
                return "elements", data
            if len(data) == 0:
                return "elements", data
            numpath = Numpath()
            for node in data:
                try:
                    e = node.as_path()
                except AttributeError:
                    continue
                for seg in e:
                    if isinstance(seg, Line):
                        numpath.line(complex(seg.start), complex(seg.end))
                    elif isinstance(seg, QuadraticBezier):
                        numpath.quad(
                            complex(seg.start), complex(seg.control), complex(seg.end)
                        )
                    elif isinstance(seg, CubicBezier):
                        numpath.cubic(
                            complex(seg.start),
                            complex(seg.control1),
                            complex(seg.control2),
                            complex(seg.end),
                        )
                    elif isinstance(seg, Close):
                        numpath.close()
                        numpath.end()
                numpath.end()
            if len(numpath) == 0:
                return "elements", data
            try:
                fillrule = data[0].fillrule
            except AttributeError:
                fillrule = None
            try:
                cap = data[0].linecap
            except AttributeError:
                cap = None
            try:
                join = data[0].linejoin
            except AttributeError:
                join = None
            node = self.elem_branch.add(
                path=numpath,
                type="elem numpath",
                stroke=data[0].stroke,
                fill=data[0].fill,
                fillrule=fillrule,
                linecap=cap,
                linejoin=join,
            )
            self.set_emphasis([node])
            node.focus()
            data.append(node)
            return "elements", data

        @self.console_command(
            "path",
            help=_("Convert any element nodes to paths"),
            input_type="elements",
            output_type="shapes",
        )
        def element_path_convert(data, **kwargs):
            paths = []
            for node in data:
                try:
                    e = node.as_path()
                except AttributeError:
                    continue
                paths.append(e)
            return "shapes", paths

        @self.console_argument(
            "path_d", type=str, help=_("svg path syntax command (quoted).")
        )
        @self.console_command(
            "path",
            help=_("path <svg path>"),
            output_type="elements",
        )
        def element_path(path_d, data, **kwargs):
            if path_d is None:
                raise CommandSyntaxError(_("Not a valid path_d string"))
            try:
                path = Path(path_d)
                path *= f"Scale({UNITS_PER_PIXEL})"
            except ValueError:
                raise CommandSyntaxError(_("Not a valid path_d string (try quotes)"))

            node = self.elem_branch.add(path=path, type="elem path")
            node.stroke = self.default_stroke
            node.fill = self.default_fill
            self.set_emphasis([node])
            node.focus()
            if data is None:
                data = list()
            data.append(node)
            return "elements", data

        @self.console_argument(
            "stroke_width",
            type=self.length,
            help=_("Stroke-width for the given stroke"),
        )
        @self.console_command(
            "stroke-width",
            help=_("stroke-width <length>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_stroke_width(
            command, channel, _, stroke_width, data=None, **kwargs
        ):
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
                    if not hasattr(e, "stroke_width"):
                        pass
                    elif not hasattr(e, "stroke_scaled"):
                        channel(
                            _(
                                "{index}: stroke-width = {stroke_width}/{implied_stroke_width} - {name} - scaled-stroke"
                            ).format(
                                index=i,
                                stroke_width="None",
                                implied_stroke_width="None",
                                name=name,
                            )
                        )
                    else:
                        if e.stroke_scaled:
                            channel(
                                _(
                                    "{index}: stroke-width = {stroke_width}/{implied_stroke_width} - {name} - scaled-stroke"
                                ).format(
                                    index=i,
                                    stroke_width=e.stroke_width,
                                    implied_stroke_width=e.implied_stroke_width(),
                                    name=name,
                                )
                            )
                        else:
                            channel(
                                _(
                                    "{index}: stroke-width = {stroke_width}/{implied_stroke_width} - {name} - non-scaling-stroke"
                                ).format(
                                    index=i,
                                    stroke_width=e.stroke_width,
                                    implied_stroke_width=e.implied_stroke_width(),
                                    name=name,
                                )
                            )
                    i += 1
                channel("----------")
                return

            if len(data) == 0:
                channel(_("No selected elements."))
                return
            for e in data:
                if hasattr(e, "lock") and e.lock:
                    channel(
                        _("Can't modify a locked element: {name}").format(name=str(e))
                    )
                    continue
                e.stroke_width = stroke_width
                e.altered()
            return "elements", data

        @self.console_command(
            ("enable_stroke_scale", "disable_stroke_scale"),
            help=_("stroke-width <length>"),
            input_type=(
                None,
                "elements",
            ),
            hidden=True,
            output_type="elements",
        )
        def element_stroke_scale_enable(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            for e in data:
                if hasattr(e, "lock") and e.lock:
                    channel(
                        _("Can't modify a locked element: {name}").format(name=str(e))
                    )
                    continue
                e.stroke_scaled = command == "enable_stroke_scale"
                e.altered()
            return "elements", data

        @self.console_option("filter", "f", type=str, help="Filter indexes")
        @self.console_argument(
            "cap",
            type=str,
            help=_("Linecap to apply to the path (one of butt, round, square)"),
        )
        @self.console_command(
            "linecap",
            help=_("linecap <cap>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_cap(
            command, channel, _, cap=None, data=None, filter=None, **kwargs
        ):
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
                        channel(_("index {index} out of range").format(index=value))
            if cap is None:
                channel("----------")
                channel(_("Linecaps:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    if hasattr(e, "linecap"):
                        if e.linecap == Linecap.CAP_SQUARE:
                            capname = "square"
                        elif e.linecap == Linecap.CAP_BUTT:
                            capname = "butt"
                        else:
                            capname = "round"
                        channel(
                            _("{index}: linecap = {linecap} - {name}").format(
                                index=i, linecap=capname, name=name
                            )
                        )
                    i += 1
                channel("----------")
                return
            else:
                capvalue = None
                if cap.lower() == "butt":
                    capvalue = Linecap.CAP_BUTT
                elif cap.lower() == "round":
                    capvalue = Linecap.CAP_ROUND
                elif cap.lower() == "square":
                    capvalue = Linecap.CAP_SQUARE
                if capvalue is not None:
                    for e in apply:
                        if hasattr(e, "linecap"):
                            if hasattr(e, "lock") and e.lock:
                                channel(
                                    _("Can't modify a locked element: {name}").format(
                                        name=str(e)
                                    )
                                )
                                continue
                            e.linecap = capvalue
                            e.altered()
                return "elements", data

        @self.console_option("filter", "f", type=str, help="Filter indexes")
        @self.console_argument(
            "join",
            type=str,
            help=_(
                "jointype to apply to the path (one of arcs, bevel, miter, miter-clip, round)"
            ),
        )
        @self.console_command(
            "linejoin",
            help=_("linejoin <join>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_join(
            command, channel, _, join=None, data=None, filter=None, **kwargs
        ):
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
                        channel(_("index {index} out of range").format(index=value))
            if join is None:
                channel("----------")
                channel(_("Linejoins:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    if hasattr(e, "linejoin"):
                        if e.linejoin == Linejoin.JOIN_ARCS:
                            joinname = "arcs"
                        elif e.linejoin == Linejoin.JOIN_BEVEL:
                            joinname = "bevel"
                        elif e.linejoin == Linejoin.JOIN_MITER_CLIP:
                            joinname = "miter-clip"
                        elif e.linejoin == Linejoin.JOIN_MITER:
                            joinname = "miter"
                        elif e.linejoin == Linejoin.JOIN_ROUND:
                            joinname = "round"
                        channel(
                            _("{index}: linejoin = {linejoin} - {name}").format(
                                index=i, linejoin=joinname, name=name
                            )
                        )
                    i += 1
                channel("----------")
                return
            else:
                joinvalue = None
                if join.lower() == "arcs":
                    joinvalue = Linejoin.JOIN_ARCS
                elif join.lower() == "bevel":
                    joinvalue = Linejoin.JOIN_BEVEL
                elif join.lower() == "miter":
                    joinvalue = Linejoin.JOIN_MITER
                elif join.lower() == "miter-clip":
                    joinvalue = Linejoin.JOIN_MITER_CLIP
                elif join.lower() == "round":
                    joinvalue = Linejoin.JOIN_ROUND
                if joinvalue is not None:
                    for e in apply:
                        if hasattr(e, "linejoin"):
                            if hasattr(e, "lock") and e.lock:
                                channel(
                                    _("Can't modify a locked element: {name}").format(
                                        name=str(e)
                                    )
                                )
                                continue
                            e.linejoin = joinvalue
                            e.altered()
                return "elements", data

        @self.console_option("filter", "f", type=str, help="Filter indexes")
        @self.console_argument(
            "rule",
            type=str,
            help=_(
                "rule to apply to fill the path (one of {nonzero}, {evenodd})"
            ).format(nonzero=SVG_RULE_NONZERO, evenodd=SVG_RULE_EVENODD),
        )
        @self.console_command(
            "fillrule",
            help=_("fillrule <rule>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_rule(
            command, channel, _, rule=None, data=None, filter=None, **kwargs
        ):
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
                        channel(_("index {index} out of range").format(index=value))
            if rule is None:
                channel("----------")
                channel(_("fillrules:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    if hasattr(e, "fillrule"):
                        if e.fillrule == Fillrule.FILLRULE_EVENODD:
                            rulename = SVG_RULE_EVENODD
                        elif e.fillrule == Fillrule.FILLRULE_NONZERO:
                            rulename = SVG_RULE_NONZERO
                        channel(
                            _("{index}: fillrule = {fillrule} - {name}").format(
                                index=i, fillrule=rulename, name=name
                            )
                        )
                    i += 1
                channel("----------")
                return
            else:
                rulevalue = None
                if rule.lower() == SVG_RULE_EVENODD:
                    rulevalue = Fillrule.FILLRULE_EVENODD
                elif rule.lower() == SVG_RULE_NONZERO:
                    rulevalue = Fillrule.FILLRULE_NONZERO
                if rulevalue is not None:
                    for e in apply:
                        if hasattr(e, "fillrule"):
                            if hasattr(e, "lock") and e.lock:
                                channel(
                                    _("Can't modify a locked element: {name}").format(
                                        name=str(e)
                                    )
                                )
                                continue
                            e.fillrule = rulevalue
                            e.altered()
                return "elements", data

        @self.console_option(
            "classify", "c", type=bool, action="store_true", help="Reclassify element"
        )
        @self.console_option("filter", "f", type=str, help="Filter indexes")
        @self.console_argument(
            "color", type=Color, help=_("Color to color the given stroke")
        )
        @self.console_command(
            "stroke",
            help=_("stroke <svg color>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_stroke(
            command, channel, _, color, data=None, classify=None, filter=None, **kwargs
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
                was_emphasized = True
                old_first = self.first_emphasized
            else:
                was_emphasized = False
                old_first = None
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
                        channel(_("index {index} out of range").format(index=value))
            if color is None:
                channel("----------")
                channel(_("Stroke Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    if not hasattr(e, "stroke"):
                        pass
                    elif (
                        hasattr(e, "stroke") and e.stroke is None or e.stroke == "none"
                    ):
                        channel(f"{i}: stroke = none - {name}")
                    else:
                        channel(f"{i}: stroke = {e.stroke.hex} - {name}")
                    i += 1
                channel("----------")
                return
            elif color == "none":
                for e in apply:
                    if hasattr(e, "lock") and e.lock:
                        channel(
                            _("Can't modify a locked element: {name}").format(
                                name=str(e)
                            )
                        )
                        continue
                    e.stroke = None
                    e.altered()
            else:
                for e in apply:
                    if hasattr(e, "lock") and e.lock:
                        channel(
                            _("Can't modify a locked element: {name}").format(
                                name=str(e)
                            )
                        )
                        continue
                    e.stroke = Color(color)
                    e.altered()
            if classify is None:
                classify = False
            if classify:
                self.remove_elements_from_operations(apply)
                self.classify(apply)
                if was_emphasized:
                    for e in apply:
                        e.emphasized = True
                    if len(apply) == 1:
                        apply[0].focus()
                if old_first is not None and old_first in apply:
                    self.first_emphasized = old_first
                else:
                    self.first_emphasized = None
                # self.signal("rebuild_tree")
                self.signal("refresh_tree", apply)
            return "elements", data

        @self.console_option(
            "classify", "c", type=bool, action="store_true", help="Reclassify element"
        )
        @self.console_option("filter", "f", type=str, help="Filter indexes")
        @self.console_argument("color", type=Color, help=_("Color to set the fill to"))
        @self.console_command(
            "fill",
            help=_("fill <svg color>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_fill(
            command, channel, _, color, data=None, classify=None, filter=None, **kwargs
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
                was_emphasized = True
                old_first = self.first_emphasized
            else:
                was_emphasized = False
                old_first = None
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
                        channel(_("index {index} out of range").format(index=value))
            if color is None:
                channel("----------")
                channel(_("Fill Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    if not hasattr(e, "fill"):
                        pass
                    elif e.fill is None or e.fill == "none":
                        channel(
                            _("{index}: fill = none - {name}").format(
                                index=i, name=name
                            )
                        )
                    else:
                        channel(
                            _("{index}: fill = {fill} - {name}").format(
                                index=i, fill=e.fill.hex, name=name
                            )
                        )
                    i += 1
                channel("----------")
                return "elements", data
            elif color == "none":
                for e in apply:
                    if hasattr(e, "lock") and e.lock:
                        channel(
                            _("Can't modify a locked element: {name}").format(
                                name=str(e)
                            )
                        )
                        continue
                    e.fill = None
                    e.altered()
            else:
                for e in apply:
                    if hasattr(e, "lock") and e.lock:
                        channel(
                            _("Can't modify a locked element: {name}").format(
                                name=str(e)
                            )
                        )
                        continue
                    e.fill = Color(color)
                    e.altered()
            if classify is None:
                classify = False
            if classify:
                self.remove_elements_from_operations(apply)
                self.classify(apply)
                if was_emphasized:
                    for e in apply:
                        e.emphasized = True
                    if len(apply) == 1:
                        apply[0].focus()
                if old_first is not None and old_first in apply:
                    self.first_emphasized = old_first
                else:
                    self.first_emphasized = None
                self.signal("refresh_tree", apply)
            #                self.signal("rebuild_tree")
            return "elements", data

        @self.console_argument(
            "x_offset", type=self.length_x, help=_("x offset."), default="0"
        )
        @self.console_argument(
            "y_offset", type=self.length_y, help=_("y offset"), default="0"
        )
        @self.console_command(
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
            **kwargs,
        ):
            """
            Draws an outline of the current shape.
            """
            bounds = self.selected_area()
            if bounds is None:
                channel(_("Nothing Selected"))
                return
            x_pos = bounds[0]
            y_pos = bounds[1]
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
            x_pos -= x_offset
            y_pos -= y_offset
            width += x_offset * 2
            height += y_offset * 2

            _element = Path(Rect(x=x_pos, y=y_pos, width=width, height=height))
            node = self.elem_branch.add(shape=_element, type="elem ellipse")
            node.stroke = Color("red")
            self.set_emphasis([node])
            node.focus()
            if self.classify_new:
                self.classify([node])

            if data is None:
                data = list()
            data.append(_element)
            return "elements", data

        @self.console_argument("angle", type=Angle.parse, help=_("angle to rotate by"))
        @self.console_option("cx", "x", type=self.length_x, help=_("center x"))
        @self.console_option("cy", "y", type=self.length_y, help=_("center y"))
        @self.console_option(
            "absolute",
            "a",
            type=bool,
            action="store_true",
            help=_("angle_to absolute angle"),
        )
        @self.console_command(
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
            **kwargs,
        ):
            if angle is None:
                channel("----------")
                channel(_("Rotate Values:"))
                i = 0
                for node in self.elems():
                    name = str(node)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    channel(
                        _("{index}: rotate({angle}turn) - {name}").format(
                            index=i, angle=node.matrix.rotation.as_turns, name=name
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
            self.validate_selected_area()
            bounds = self.selected_area()
            if bounds is None:
                channel(_("No selected elements."))
                return
            rot = angle.as_degrees

            if cx is None:
                cx = (bounds[2] + bounds[0]) / 2.0
            if cy is None:
                cy = (bounds[3] + bounds[1]) / 2.0
            matrix = Matrix(f"rotate({rot}deg,{cx},{cy})")
            try:
                if not absolute:
                    for node in data:
                        if hasattr(node, "lock") and node.lock:
                            continue

                        node.matrix *= matrix
                        node.modified()
                else:
                    for node in data:
                        start_angle = node.matrix.rotation
                        amount = rot - start_angle
                        matrix = Matrix(f"rotate({Angle(amount).as_degrees},{cx},{cy})")
                        node.matrix *= matrix
                        node.modified()
            except ValueError:
                raise CommandSyntaxError
            return "elements", data

        @self.console_argument("scale_x", type=str, help=_("scale_x value"))
        @self.console_argument("scale_y", type=str, help=_("scale_y value"))
        @self.console_option(
            "px", "x", type=self.length_x, help=_("scale x origin point")
        )
        @self.console_option(
            "py", "y", type=self.length_y, help=_("scale y origin point")
        )
        @self.console_option(
            "absolute",
            "a",
            type=bool,
            action="store_true",
            help=_("scale to absolute size"),
        )
        @self.console_command(
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
            **kwargs,
        ):
            if scale_x is None:
                channel("----------")
                channel(_("Scale Values:"))
                i = 0
                for node in self.elems():
                    name = str(node)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    channel(
                        f"{i}: scale({node.matrix.value_scale_x()}, {node.matrix.value_scale_y()}) - {name}"
                    )
                    i += 1
                channel("----------")
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            # print (f"Start: {scale_x} ({type(scale_x).__name__}), {scale_y} ({type(scale_y).__name__})")
            factor = 1
            if scale_x.endswith("%"):
                factor = 0.01
                scale_x = scale_x[:-1]
            try:
                scale_x = factor * float(scale_x)
            except ValueError:
                scale_x = 1
            if scale_y is None:
                scale_y = scale_x
            else:
                factor = 1
                if scale_y.endswith("%"):
                    factor = 0.01
                    scale_y = scale_y[:-1]
                try:
                    scale_y = factor * float(scale_y)
                except ValueError:
                    scale_y = 1
            # print (f"End: {scale_x} ({type(scale_x).__name__}), {scale_y} ({type(scale_y).__name__})")

            bounds = Node.union_bounds(data)
            if px is None:
                px = (bounds[2] + bounds[0]) / 2.0
            if py is None:
                py = (bounds[3] + bounds[1]) / 2.0
            if scale_x == 0 or scale_y == 0:
                channel(_("Scaling by Zero Error"))
                return
            matrix = Matrix(f"scale({scale_x},{scale_y},{px},{py})")
            try:
                if not absolute:
                    for node in data:
                        if hasattr(node, "lock") and node.lock:
                            continue
                        node.matrix *= matrix
                        node.modified()
                else:
                    for node in data:
                        if hasattr(node, "lock") and node.lock:
                            continue
                        osx = node.matrix.value_scale_x()
                        osy = node.matrix.value_scale_y()
                        nsx = scale_x / osx
                        nsy = scale_y / osy
                        matrix = Matrix(f"scale({nsx},{nsy},{px},{px})")
                        node.matrix *= matrix
                        node.modified()
            except ValueError:
                raise CommandSyntaxError
            return "elements", data

        @self.console_option(
            "new_area", "n", type=self.area, help=_("provide a new area to cover")
        )
        @self.console_option(
            "density", "d", type=int, help=_("Defines the interpolation density")
        )
        @self.console_command(
            "area",
            help=_("provides information about/changes the area of a selected element"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_area(
            command,
            channel,
            _,
            new_area=None,
            density=None,
            data=None,
            **kwargs,
        ):
            if density is None:
                density = 200
            if new_area is None:
                display_only = True
            else:
                if new_area == 0:
                    channel(_("You shouldn't collapse a shape to a zero-sized thing"))
                    return
                display_only = False
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            total_area = 0
            if display_only:
                channel("----------")
                channel(_("Area values (Density={density})").format(density=density))

            units = ("mm", "cm", "in")
            square_unit = [0] * len(units)
            for idx, u in enumerate(units):
                value = float(Length(f"1{u}"))
                square_unit[idx] = value * value

            i = 0
            for elem in data:
                this_area, this_length = self.get_information(elem, density=density)

                if display_only:
                    name = str(elem)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    channel(f"{i}: {name}")
                    for idx, u in enumerate(units):
                        this_area_local = this_area / square_unit[idx]
                        channel(
                            _(" Area= {area:.3f} {unit}²").format(
                                area=this_area_local, unit=u
                            )
                        )
                i += 1
                total_area += this_area
            if display_only:
                channel("----------")
            else:
                if total_area == 0:
                    channel(_("You can't reshape a zero-sized shape"))
                    return

                ratio = sqrt(new_area / total_area)
                self(f"scale {ratio}\n")

            return "elements", data
            # Do we have a new value to set? If yes scale by sqrt(of the fraction)

        @self.console_argument("tx", type=self.length_x, help=_("translate x value"))
        @self.console_argument("ty", type=self.length_y, help=_("translate y value"))
        @self.console_option(
            "absolute",
            "a",
            type=bool,
            action="store_true",
            help=_("translate to absolute position"),
        )
        @self.console_command(
            "translate",
            help=_("translate <tx> <ty>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_translate(
            command, channel, _, tx, ty, absolute=False, data=None, **kwargs
        ):
            if tx is None:
                channel("----------")
                channel(_("Translate Values:"))
                i = 0
                for node in self.elems():
                    name = str(node)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    channel(
                        f"{i}: translate({node.matrix.value_trans_x():.1f}, {node.matrix.value_trans_y():.1f}) - {name}"
                    )
                    i += 1
                channel("----------")
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            if tx is None:
                tx = 0
            if ty is None:
                ty = 0
            matrix = Matrix.translate(tx, ty)
            try:
                if not absolute:
                    for node in data:
                        if (
                            hasattr(node, "lock")
                            and node.lock
                            and not self.lock_allows_move
                        ):
                            continue

                        node.matrix *= matrix
                        node.modified()
                else:
                    for node in data:
                        if (
                            hasattr(node, "lock")
                            and node.lock
                            and not self.lock_allows_move
                        ):
                            continue
                        otx = node.matrix.value_trans_x()
                        oty = node.matrix.value_trans_y()
                        ntx = tx - otx
                        nty = ty - oty
                        matrix = Matrix.translate(ntx, nty)
                        node.matrix *= matrix
                        node.modified()
            except ValueError:
                raise CommandSyntaxError
            return "elements", data

        @self.console_argument("tx", type=self.length_x, help=_("New x value"))
        @self.console_argument("ty", type=self.length_y, help=_("New y value"))
        @self.console_command(
            "position",
            help=_("position <tx> <ty>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_position(
            command, channel, _, tx, ty, absolute=False, data=None, **kwargs
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            if tx is None or ty is None:
                channel(_("You need to provide a new position."))
                return

            dbounds = Node.union_bounds(data)
            for node in data:
                if hasattr(node, "lock") and node.lock and not self.lock_allows_move:
                    continue
                nbounds = node.bounds
                dx = tx - dbounds[0]
                dy = ty - dbounds[1]
                if dx != 0 or dy != 0:
                    node.matrix.post_translate(dx, dy)
                node.modified()
            return "elements", data

        @self.console_command(
            "move_to_laser",
            help=_("translates the selected element to the laser head"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_move_to_laser(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            tx, ty = self.device.current
            try:
                bounds = Node.union_bounds(data)
                otx = bounds[0]
                oty = bounds[1]
                ntx = tx - otx
                nty = ty - oty
                for node in data:
                    if (
                        hasattr(node, "lock")
                        and node.lock
                        and not self.lock_allows_move
                    ):
                        continue
                    node.matrix.post_translate(ntx, nty)
                    node.modified()
            except ValueError:
                raise CommandSyntaxError
            return "elements", data

        @self.console_argument(
            "x_pos", type=self.length_x, help=_("x position for top left corner")
        )
        @self.console_argument(
            "y_pos", type=self.length_y, help=_("y position for top left corner")
        )
        @self.console_argument(
            "width", type=self.length_x, help=_("new width of selected")
        )
        @self.console_argument(
            "height", type=self.length_y, help=_("new height of selected")
        )
        @self.console_command(
            "resize",
            help=_("resize <x-pos> <y-pos> <width> <height>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_resize(
            command, channel, _, x_pos, y_pos, width, height, data=None, **kwargs
        ):
            if height is None:
                raise CommandSyntaxError
            try:
                area = self.selected_area()
                if area is None:
                    channel(_("resize: nothing selected"))
                    return
                x, y, x1, y1 = area
                w, h = x1 - x, y1 - y
                if w == 0 or h == 0:  # dot
                    channel(_("resize: cannot resize a dot"))
                    return
                sx = width / w
                sy = height / h
                # Don't do anything if scale is 1
                if sx == 1.0 and sy == 1.0:
                    scale_str = ""
                else:
                    scale_str = f"scale({sx},{sy})"
                if x_pos == x and y_pos == y and scale_str == "":
                    return
                #     trans1_str = ""
                #     trans2_str = ""
                # else:
                trans1_str = f"translate({round(x_pos, 7)},{round(y_pos, 7)})"
                trans2_str = f"translate({round(-x, 7)},{round(-y, 7)})"
                matrixstr = f"{trans1_str} {scale_str} {trans2_str}".strip()
                # channel(f"{matrixstr}")
                matrix = Matrix(matrixstr)
                if data is None:
                    data = list(self.elems(emphasized=True))
                for node in data:
                    if hasattr(node, "lock") and node.lock:
                        channel(_("resize: cannot resize a locked element"))
                        continue
                    node.matrix *= matrix
                    node.modified()
                return "elements", data
            except (ValueError, ZeroDivisionError, TypeError):
                raise CommandSyntaxError

        @self.console_argument("sx", type=float, help=_("scale_x value"))
        @self.console_argument("kx", type=float, help=_("skew_x value"))
        @self.console_argument("ky", type=float, help=_("skew_y value"))
        @self.console_argument("sy", type=float, help=_("scale_y value"))
        @self.console_argument("tx", type=self.length_x, help=_("translate_x value"))
        @self.console_argument("ty", type=self.length_y, help=_("translate_y value"))
        @self.console_command(
            "matrix",
            help=_("matrix <sx> <kx> <ky> <sy> <tx> <ty>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_matrix(
            command, channel, _, sx, kx, ky, sy, tx, ty, data=None, **kwargs
        ):
            if ty is None:
                channel("----------")
                channel(_("Matrix Values:"))
                i = 0
                for node in self.elems():
                    name = str(node)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    channel(f"{i}: {str(node.matrix)} - {name}")
                    i += 1
                channel("----------")
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            try:
                # SVG 7.15.3 defines the matrix form as:
                # [a c  e]
                # [b d  f]
                m = Matrix(
                    sx,
                    kx,
                    ky,
                    sy,
                    tx,
                    ty,
                )
                for node in data:
                    if hasattr(node, "lock") and node.lock:
                        continue
                    node.matrix = Matrix(m)
                    node.modified()
            except ValueError:
                raise CommandSyntaxError
            return

        @self.console_command(
            "reset",
            help=_("reset affine transformations"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def reset(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            for e in data:
                if hasattr(e, "lock") and e.lock:
                    continue
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(_("reset - {name}").format(name=name))
                e.matrix.reset()
                e.modified()
            return "elements", data

        @self.console_command(
            "reify",
            help=_("reify affine transformations"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_reify(command, channel, _, data=None, **kwargs):
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
                try:
                    e.shape.reify()
                    e.altered()
                    channel(_("reified - %s") % name)
                except AttributeError as err:
                    channel(_("Couldn't reify - %s - %s") % (name, err))

            return "elements", data

        @self.console_command(
            "classify",
            help=_("classify elements into operations"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_classify(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
                was_emphasized = True
                old_first = self.first_emphasized
            else:
                was_emphasized = False
                old_first = None
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            self.classify(data)
            if was_emphasized:
                for e in data:
                    e.emphasized = True
                if len(data) == 1:
                    data[0].focus()
                if old_first is not None and old_first in data:
                    self.first_emphasized = old_first
                else:
                    self.first_emphasized = None

            return "elements", data

        @self.console_command(
            "declassify",
            help=_("declassify selected elements"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def declassify(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
                was_emphasized = True
                old_first = self.first_emphasized
            else:
                was_emphasized = False
                old_first = None
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            self.remove_elements_from_operations(data)
            # restore emphasized flag as it is relevant for subsequent operations
            if was_emphasized:
                for e in data:
                    e.emphasized = True
                if len(data) == 1:
                    data[0].focus()
                if old_first is not None and old_first in data:
                    self.first_emphasized = old_first
                else:
                    self.first_emphasized = None
            return "elements", data

        # ==========
        # TREE BASE
        # ==========
        @self.console_command(
            "tree", help=_("access and alter tree elements"), output_type="tree"
        )
        def tree(**kwargs):
            return "tree", [self._tree]

        @self.console_command(
            "bounds", help=_("view tree bounds"), input_type="tree", output_type="tree"
        )
        def tree_bounds(command, channel, _, data=None, **kwargs):
            if data is None:
                data = [self._tree]

            def b_list(path, node):
                for i, n in enumerate(node.children):
                    p = list(path)
                    p.append(str(i))
                    channel(
                        f"{'.'.join(p).ljust(10)}: {str(n._bounds)} - {str(n._bounds_dirty)} {str(n.type)} - {str(str(n)[:16])}"
                    )
                    b_list(p, n)

            for d in data:
                channel("----------")
                if d.type == "root":
                    channel(_("Tree:"))
                else:
                    channel(f"{str(d)}:")
                b_list([], d)
                channel("----------")

            return "tree", data

        @self.console_command(
            "list", help=_("view tree"), input_type="tree", output_type="tree"
        )
        def tree_list(command, channel, _, data=None, **kwargs):
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
                    channel(
                        f"{'.'.join(p).ljust(10)}{j} {str(n.type)} - {str(n.label)}"
                    )
                    t_list(p, n)

            for d in data:
                channel("----------")
                if d.type == "root":
                    channel(_("Tree:"))
                else:
                    channel(f"{d.label}:")
                t_list([], d)
                channel("----------")

            return "tree", data

        @self.console_argument("drag", help="Drag node address")
        @self.console_argument("drop", help="Drop node address")
        @self.console_command(
            "dnd", help=_("Drag and Drop Node"), input_type="tree", output_type="tree"
        )
        def tree_dnd(command, channel, _, data=None, drag=None, drop=None, **kwargs):
            """
            Drag and Drop command performs a console based drag and drop operation
            E.g. "tree dnd 0.1 0.2" will drag node 0.1 into node 0.2
            """
            if data is None:
                data = [self._tree]
            if drop is None:
                raise CommandSyntaxError
            try:
                drag_node = self._tree
                for n in drag.split("."):
                    drag_node = drag_node.children[int(n)]
                drop_node = self._tree
                for n in drop.split("."):
                    drop_node = drop_node.children[int(n)]
                drop_node.drop(drag_node)
            except (IndexError, AttributeError, ValueError):
                raise CommandSyntaxError
            self.signal("tree_changed")
            return "tree", data

        @self.console_argument("node", help="Node address for menu")
        @self.console_argument("execute", help="Command to execute")
        @self.console_command(
            "menu",
            help=_("Load menu for given node"),
            input_type="tree",
            output_type="tree",
        )
        def tree_menu(
            command, channel, _, data=None, node=None, execute=None, **kwargs
        ):
            """
            Create menu for a particular node.
            Processes submenus, references, radio_state and check_state as needed.
            """
            try:
                menu_node = self._tree
                for n in node.split("."):
                    menu_node = menu_node.children[int(n)]
            except (IndexError, AttributeError, ValueError):
                raise CommandSyntaxError

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
                    n = func.real_name
                    if hasattr(func, "check_state") and func.check_state:
                        n = "✓" + n
                    menu_context.append((n, menu_functions(func, menu_node)))
                if func.separate_after:
                    menu_context.append(("------", None))
            if execute is not None:
                try:
                    execute_command = ("menu", menu)
                    for n in execute.split("."):
                        name, cmd = execute_command
                        execute_command = cmd[int(n)]
                    name, cmd = execute_command
                    channel(f"Executing {name}: {str(cmd)}")
                    cmd()
                except (IndexError, AttributeError, ValueError, TypeError):
                    raise CommandSyntaxError
            else:

                def m_list(path, _menu):
                    for i, _n in enumerate(_menu):
                        p = list(path)
                        p.append(str(i))
                        _name, _submenu = _n
                        channel(f"{'.'.join(p).ljust(10)}: {str(_name)}")
                        if isinstance(_submenu, list):
                            m_list(p, _submenu)

                m_list([], menu)

            return "tree", data

        @self.console_command(
            "selected",
            help=_("delegate commands to focused value"),
            input_type="tree",
            output_type="tree",
        )
        def selected(channel, _, **kwargs):
            """
            Set tree list to selected node
            """
            # print ("selected")
            # for n in self.flat():
            #     print ("Node: %s, selected=%s, emphasized=%s" % (n.type, n.selected, n.emphasized))
            return "tree", list(self.flat(selected=True))

        @self.console_command(
            "emphasized",
            help=_("delegate commands to focused value"),
            input_type="tree",
            output_type="tree",
        )
        def emphasized(channel, _, **kwargs):
            """
            Set tree list to emphasized node
            """
            return "tree", list(self.flat(emphasized=True))

        @self.console_command(
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

        @self.console_command(
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

        @self.console_command(
            "delete",
            help=_("delete the given nodes"),
            input_type="tree",
            output_type="tree",
        )
        def delete(channel, _, data=None, **kwargs):
            """
            Delete nodes.
            Structural nodes such as root, elements branch, and operations branch are not able to be deleted
            """
            # This is an unusually dangerous operation, so if we have multiple node types, like ops + elements
            # then we would 'only' delete those where we have the least danger, so that regmarks < operations < elements
            if len(data) == 0:
                channel(_("Nothing to delete"))
                return
            # print ("Delete called with data:")
            # for n in data:
            #     print ("Node: %s, sel=%s, emp=%s" % (n.type, n.selected, n.emphasized))
            typecount = [0, 0, 0, 0, 0]
            todelete = [[], [], [], [], []]
            nodetypes = ("Operations", "References", "Elements", "Regmarks", "Branches")
            regmk = list(self.regmarks())
            for node in data:
                if node.type in op_nodes:
                    typecount[0] += 1
                    todelete[0].append(node)
                elif node.type == "reference":
                    typecount[1] += 1
                    todelete[1].append(node)
                elif node.type in elem_group_nodes:
                    if node in regmk:
                        typecount[3] += 1
                        todelete[3].append(node)
                    else:
                        if hasattr(node, "lock") and node.lock:
                            # Don't delete locked nodes
                            continue
                        typecount[2] += 1
                        todelete[2].append(node)
                else:  # branches etc...
                    typecount[4] += 1
            # print ("Types: ops=%d, refs=%d, elems=%d, regmarks=%d, branches=%d" %
            #     (typecount[0], typecount[1], typecount[2], typecount[3], typecount[4]))
            single = False
            if (
                typecount[0] > 0
                and typecount[1] == 0
                and typecount[2] == 0
                and typecount[3] == 0
            ):
                single = True
                entry = 0
            elif (
                typecount[1] > 0
                and typecount[0] == 0
                and typecount[2] == 0
                and typecount[3] == 0
            ):
                single = True
                entry = 1
            elif (
                typecount[2] > 0
                and typecount[0] == 0
                and typecount[1] == 0
                and typecount[3] == 0
            ):
                single = True
                entry = 2
            elif (
                typecount[3] > 0
                and typecount[0] == 0
                and typecount[1] == 0
                and typecount[2] == 0
            ):
                single = True
                entry = 3
            if not single:
                if typecount[3] > 0:
                    # regmarks take precedence, the least dangereous delete
                    entry = 3
                elif typecount[1] > 0:
                    # refs next
                    entry = 1
                elif typecount[0] > 0:
                    # ops next
                    entry = 0
                else:
                    # Not sure why and when this suposed to happen?
                    entry = 2
                channel(
                    _(
                        "There were nodes across operations ({c1}), assignments ({c2}), elements ({c3}) and regmarks ({c4})."
                    ).format(
                        c1=typecount[0],
                        c2=typecount[1],
                        c3=typecount[2],
                        c4=typecount[3],
                    )
                    + "\n"
                    + _("Only nodes of type {nodetype} were deleted.").format(
                        nodetype=nodetypes[entry]
                    )
                    + "\n"
                    + _(
                        "If you want to remove all nodes regardless of their type, consider: 'tree selected remove'"
                    )
                )
            # print ("Want to delete %d" % entry)
            # for n in todelete[entry]:
            #     print ("Node to delete: %s" % n.type)
            self.remove_nodes(todelete[entry])
            self.validate_selected_area()
            self.signal("tree_changed")
            self.signal("refresh_scene", "Scene")
            return "tree", [self._tree]

        @self.console_command(
            "remove",
            help=_("forcefully deletes all given nodes"),
            input_type="tree",
            output_type="tree",
        )
        def remove(channel, _, data=None, **kwargs):
            """
            Delete nodes.
            Structural nodes such as root, elements branch, and operations branch are not able to be deleted
            """
            # This is an unusually dangerous operation, so if we have multiple node types, like ops + elements
            # then we would 'only' delete those where we have the least danger, so that regmarks < operations < elements
            self.remove_nodes(data)
            self.signal("tree_changed")
            self.signal("refresh_scene", "Scene")
            return "tree", [self._tree]

        @self.console_command(
            "delegate",
            help=_("delegate commands to focused value"),
            input_type="tree",
            output_type=("op", "elements"),
        )
        def delegate(channel, _, **kwargs):
            """
            Delegate to either ops or elements depending on the current node emphasis
            """
            for item in self.flat(emphasized=True):
                if item.type.startswith("op"):
                    return "ops", list(self.ops(emphasized=True))
                if item.type in elem_nodes or item.type in ("group", "file"):
                    return "elements", list(self.elems(emphasized=True))

        # ==========
        # CLIPBOARD COMMANDS
        # ==========
        @self.console_option("name", "n", type=str)
        @self.console_command(
            "clipboard",
            help=_("clipboard"),
            input_type=(None, "elements"),
            output_type="clipboard",
        )
        def clipboard_base(data=None, name=None, **kwargs):
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

        @self.console_command(
            "copy",
            help=_("clipboard copy"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_copy(data=None, **kwargs):
            destination = self._clipboard_default
            self._clipboard[destination] = [copy(e) for e in data]
            return "elements", self._clipboard[destination]

        @self.console_option(
            "dx", "x", help=_("paste offset x"), type=Length, default=0
        )
        @self.console_option(
            "dy", "y", help=_("paste offset y"), type=Length, default=0
        )
        @self.console_command(
            "paste",
            help=_("clipboard paste"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_paste(command, channel, _, data=None, dx=None, dy=None, **kwargs):
            destination = self._clipboard_default
            try:
                pasted = [copy(e) for e in self._clipboard[destination]]
            except (TypeError, KeyError):
                channel(_("Error: Clipboard Empty"))
                return
            if dx != 0 or dy != 0:
                matrix = Matrix.translate(float(dx), float(dy))
                for node in pasted:
                    node.matrix *= matrix
            group = self.elem_branch.add(type="group", label="Group", id="Copy")
            for p in pasted:
                group.add_node(copy(p))
            self.set_emphasis([group])
            self.signal("refresh_tree", group)
            return "elements", pasted

        @self.console_command(
            "cut",
            help=_("clipboard cut"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_cut(data=None, **kwargs):
            destination = self._clipboard_default
            self._clipboard[destination] = [copy(e) for e in data]
            self.remove_elements(data)
            return "elements", self._clipboard[destination]

        @self.console_command(
            "clear",
            help=_("clipboard clear"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_clear(data=None, **kwargs):
            destination = self._clipboard_default
            try:
                old = self._clipboard[destination]
            except KeyError:
                old = None
            self._clipboard[destination] = None
            return "elements", old

        @self.console_command(
            "contents",
            help=_("clipboard contents"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_contents(**kwargs):
            destination = self._clipboard_default
            return "elements", self._clipboard[destination]

        @self.console_command(
            "list",
            help=_("clipboard list"),
            input_type="clipboard",
        )
        def clipboard_list(command, channel, _, **kwargs):
            for v in self._clipboard:
                k = self._clipboard[v]
                channel(f"{str(v).ljust(5)}: {str(k)}")
            num = self.has_clipboard()
            channel(_("Clipboard-Entries: {index}").format(index=num))

        # ==========
        # NOTES COMMANDS
        # ==========
        @self.console_option(
            "append", "a", type=bool, action="store_true", default=False
        )
        @self.console_command("note", help=_("note <note>"))
        def note(command, channel, _, append=False, remainder=None, **kwargs):
            _note = remainder
            if _note is None:
                if self.note is None:
                    channel(_("No Note."))
                else:
                    channel(str(self.note))
            else:
                if append:
                    self.note += "\n" + _note
                else:
                    self.note = _note
                channel(_("Note Set."))
                channel(str(self.note))

        # ==========
        # TRACE OPERATIONS
        # ==========

        # Function to return the euclidean distance
        # between two points
        def dist(a, b):
            return sqrt(pow(a[0] - b[0], 2) + pow(a[1] - b[1], 2))

        # Function to check whether a point lies inside
        # or on the boundaries of the circle
        def is_inside(center, radius, p):
            return dist(center, p) <= radius

        # The following two functions are used
        # To find the equation of the circle when
        # three points are given.

        # Helper method to get a circle defined by 3 points
        def get_circle_center(bx, by, cx, cy):
            B = bx * bx + by * by
            C = cx * cx + cy * cy
            D = bx * cy - by * cx
            return [(cy * B - by * C) / (2 * D), (bx * C - cx * B) / (2 * D)]

        # Function to return the smallest circle
        # that intersects 2 points
        def circle_from1(A, B):
            # Set the center to be the midpoint of A and B
            C = [(A[0] + B[0]) / 2.0, (A[1] + B[1]) / 2.0]

            # Set the radius to be half the distance AB
            return C, dist(A, B) / 2.0

        # Function to return a unique circle that
        # intersects three points
        def circle_from2(A, B, C):
            if A == B:
                I, radius = circle_from1(A, C)
                return I, radius
            elif A == C:
                I, radius = circle_from1(A, B)
                return I, radius
            elif B == C:
                I, radius = circle_from1(A, B)
                return I, radius
            else:
                I = get_circle_center(
                    B[0] - A[0], B[1] - A[1], C[0] - A[0], C[1] - A[1]
                )
                I[0] += A[0]
                I[1] += A[1]
                radius = dist(I, A)
                return I, radius

        # Function to check whether a circle
        # encloses the given points
        def is_valid_circle(center, radius, P):

            # Iterating through all the points
            # to check  whether the points
            # lie inside the circle or not
            for p in P:
                if not is_inside(center, radius, p):
                    return False
            return True

        # Function to return the minimum enclosing
        # circle for N <= 3
        def min_circle_trivial(P):
            assert len(P) <= 3

            if not P:
                return [0, 0], 0

            elif len(P) == 1:
                return P[0], 0

            elif len(P) == 2:
                center, radius = circle_from1(P[0], P[1])
                return center, radius

            # To check if MEC can be determined
            # by 2 points only
            for i in range(3):
                for j in range(i + 1, 3):

                    center, radius = circle_from1(P[i], P[j])
                    if is_valid_circle(center, radius, P):
                        return center, radius

            center, radius = circle_from2(P[0], P[1], P[2])
            return center, radius

        # Returns the MEC using Welzl's algorithm
        # Takes a set of input points P and a set R
        # points on the circle boundary.
        # n represents the number of points in P
        # that are not yet processed.
        def welzl_helper(P, R, n):
            # Base case when all points processed or |R| = 3
            if n == 0 or len(R) == 3:
                center, radius = min_circle_trivial(R)
                return center, radius

            # Pick a random point randomly
            idx = randint(0, n - 1)
            p = P[idx]

            # Put the picked point at the end of P
            # since it's more efficient than
            # deleting from the middle of the vector
            P[idx], P[n - 1] = P[n - 1], P[idx]

            # Get the MEC circle d from the
            # set of points P - :p
            dcenter, dradius = welzl_helper(P, R.copy(), n - 1)

            # If d contains p, return d
            if is_inside(dcenter, dradius, p):
                return dcenter, dradius

            # Otherwise, must be on the boundary of the MEC
            R.append(p)

            # Return the MEC for P - :p and R U :p
            dcenter, dradius = welzl_helper(P, R.copy(), n - 1)
            return dcenter, dradius

        def welzl(P):
            P_copy = P.copy()
            shuffle(P_copy)
            center, radius = welzl_helper(P_copy, [], len(P_copy))
            return center, radius

        def generate_hull_shape(method, data, resolution=None):
            if resolution is None:
                DETAIL = 500  # How coarse / fine shall a subpath be split
            else:
                DETAIL = int(resolution)
            pts = []
            min_val = [float("inf"), float("inf")]
            max_val = [-float("inf"), -float("inf")]
            for node in data:
                if method in ("hull", "segment", "circle"):
                    try:
                        path = node.as_path()
                    except AttributeError:
                        path = None
                    if path is not None:
                        p = path.first_point
                        pts += [(p.x, p.y)]
                        for segment in path:
                            p = segment.end
                            pts += [(p.x, p.y)]
                    else:
                        bounds = node.bounds
                        pts += [
                            (bounds[0], bounds[1]),
                            (bounds[0], bounds[3]),
                            (bounds[2], bounds[1]),
                            (bounds[2], bounds[3]),
                        ]
                elif method == "complex":
                    try:
                        path = node.as_path()
                    except AttributeError:
                        path = None

                    if path is not None:
                        for subpath in path.as_subpaths():
                            psp = Path(subpath)
                            p = psp.first_point
                            pts += [(p.x, p.y)]
                            positions = linspace(0, 1, num=DETAIL, endpoint=True)
                            subj = psp.npoint(positions)
                            # Not sure why we need to do that, its already rows x 2
                            # subj.reshape((2, DETAIL))
                            s = list(map(Point, subj))
                            for p in s:
                                pts += [(p.x, p.y)]
                    else:
                        bounds = node.bounds
                        pts += [
                            (bounds[0], bounds[1]),
                            (bounds[0], bounds[3]),
                            (bounds[2], bounds[1]),
                            (bounds[2], bounds[3]),
                        ]
                elif method == "quick":
                    bounds = node.bounds
                    min_val[0] = min(min_val[0], bounds[0])
                    min_val[1] = min(min_val[1], bounds[1])
                    max_val[0] = max(max_val[0], bounds[2])
                    max_val[1] = max(max_val[1], bounds[3])
            if method == "quick":
                if (
                    not isinf(min_val[0])
                    and not isinf(min_val[1])
                    and not isinf(max_val[0])
                    and not isinf(max_val[0])
                ):
                    pts += [
                        (min_val[0], min_val[1]),
                        (min_val[0], max_val[1]),
                        (max_val[0], min_val[1]),
                        (max_val[0], max_val[1]),
                    ]
            if method == "segment":
                hull = [p for p in pts]
            elif method == "circle":
                mec_center, mec_radius = welzl(pts)
                # So now we have a circle with (mec[0], mec[1]), and mec_radius
                hull = []
                RES = 100
                for i in range(RES):
                    hull += [
                        (
                            mec_center[0] + mec_radius * cos(i / RES * tau),
                            mec_center[1] + mec_radius * sin(i / RES * tau),
                        )
                    ]
            else:
                hull = [p for p in Point.convex_hull(pts)]
            if len(hull) != 0:
                hull.append(hull[0])  # loop
            return hull

        @self.console_argument(
            "method",
            help=_("Method to use (one of quick, hull, complex, segment, circle)"),
        )
        @self.console_argument("resolution")
        @self.console_command(
            "trace",
            help=_("trace the given elements"),
            input_type=("elements", "shapes", None),
        )
        def trace_trace_spooler(
            command, channel, _, method=None, resolution=None, data=None, **kwargs
        ):
            if method is None:
                method = "quick"
            method = method.lower()
            if method not in ("segment", "quick", "hull", "complex", "circle"):
                channel(
                    _(
                        "Invalid method, please use one of quick, hull, complex, segment, circle."
                    )
                )
                return

            spooler = self.device.spooler
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No elements bounds to trace"))
                return
            hull = generate_hull_shape(method, data, resolution)
            if len(hull) == 0:
                channel(_("No elements bounds to trace."))
                return

            def run_shape(_spooler, _hull):
                def trace_hull():
                    yield "wait_finish"
                    yield "rapid_mode"
                    idx = 0
                    for p in _hull:
                        idx += 1
                        yield (
                            "move_abs",
                            Length(amount=p[0]).length_mm,
                            Length(amount=p[1]).length_mm,
                        )

                _spooler.laserjob(list(trace_hull()), label=f"Trace Job: {method}")

            run_shape(spooler, hull)

        @self.console_argument(
            "method",
            help=_("Method to use (one of quick, hull, complex, segment, circle)"),
        )
        @self.console_argument(
            "resolution", help=_("Resolution for complex slicing, default=500")
        )
        @self.console_command(
            "tracegen",
            help=_("create the trace around the given elements"),
            input_type=("elements", "shapes", None),
            output_type="elements",
        )
        def trace_trace_generator(
            command, channel, _, method=None, resolution=None, data=None, **kwargs
        ):
            if method is None:
                method = "quick"
            method = method.lower()
            if not method in ("segment", "quick", "hull", "complex", "circle"):
                channel(
                    _(
                        "Invalid method, please use one of quick, hull, complex, segment, circle."
                    )
                )
                return

            if data is None:
                data = list(self.elems(emphasized=True))
            hull = generate_hull_shape(method, data, resolution=resolution)
            if len(hull) == 0:
                channel(_("No elements bounds to trace."))
                return
            shape = Polyline(hull)
            if shape.is_degenerate():
                channel(_("Shape is degenerate."))
                return "elements", data
            node = self.elem_branch.add(shape=shape, type="elem polyline")
            node.stroke = self.default_stroke
            node.fill = self.default_fill
            self.set_emphasis([node])
            node.focus()
            data.append(node)
            return "elements", data

        # --------------------------- END COMMANDS ------------------------------

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

        @self.tree_operation(_("Clear unused"), node_type="branch ops", help=_("Clear operations without children"))
        def clear_unused(node, **kwargs):
            to_delete = []
            for op in self.ops():
                # print (f"{op.type}, refs={len(op._references)}, children={len(op._children)}")
                if len(op._children) == 0:
                    to_delete.append(op)
            if len(to_delete)>0:
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
            _("Remove all assignments from operations"), node_type="branch elems",
            help=_(
                "Any existing assignment of elements to operations will be removed"
            ),
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
            help=_("Convert a vector element into a raster element."),
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

            rem_node (node)
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
            for e in list(self.elems(emphasized=True)):
                for n in range(copies):
                    copy_node = copy(e)
                    if hasattr(e, "wxfont"):
                        copy_node.wxfont = e.wxfont
                    node.parent.add_node(copy_node)
                    copy_nodes.append(copy_node)

            if self.classify_new:
                self.classify(copy_nodes)

            self.set_emphasis(None)

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
            try:
                path = node.as_path()
            except AttributeError:
                return
            node.replace_node(path=path, type="elem path")

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

    def modified(self, *args):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None

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
                    debug (f"Pass 1 (fuzzy={tempfuzzy}): check {node.type}")
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
                        debug (f"For {op.type}: black={is_black}, perform={whisperer}, flag={self.classify_black_as_raster}")
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
                            debug(f"Was classified: {sstroke} {sfill} matching operation: {type(op).__name__}, break={should_break}")
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
                    #even if it has, we are not going to something with it
                    classif_info[0] = True
            else:
                classif_info[0] = True
            if hasattr(node, "fill"):
                if node.fill is None or node.fill.argb is None:
                    classif_info[1] = True
            else:
                classif_info[1] = True

            if self.classify_autogenerate_both and not (classif_info[0] and classif_info[1]):
                # Not fully classified on both stroke and fill
                was_classified = False
            if not was_classified and usedefault:
                # let's iterate through the default ops and add them
                if debug:
                    debug ("Pass 2 (wasn't classified), looking for default ops")
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
                        debug(f"For {op.type}: black={is_black}, perform={whisperer}, flag={self.classify_black_as_raster}")
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
                            debug(f"Was classified to default operation: {type(op).__name__}, break={should_break}")
                    if should_break:
                        break
            # Lets make sure we only consider relevant, ie existing attributes...
            if hasattr(node, "stroke"):
                if node.stroke is None or node.stroke.argb is None:
                    classif_info[0] = True
                if node.type == "elem text":
                    #even if it has, we are not going to something with it
                    classif_info[0] = True
            else:
                classif_info[0] = True
            if hasattr(node, "fill"):
                if node.fill is None or node.fill.argb is None:
                    classif_info[1] = True
            else:
                classif_info[1] = True

            if self.classify_autogenerate_both and not (classif_info[0] and classif_info[1]):
                # Not fully classified on both stroke and fill
                was_classified = False
            if not was_classified and autogen:
                # Despite all efforts we couldn't classify the element, so let's add an op
                if debug:
                    debug ("Pass 3, not classified by ops or def ops")
                stdops = []
                has_raster = False
                if node.type == "elem image":
                    stdops.append(ImageOpNode(output=False))
                    if debug:
                        debug ("add an op image")
                    classif_info[0] = True
                    classif_info[1] = True
                elif node.type == "elem point":
                    stdops.append(DotsOpNode(output=False))
                    if debug:
                        debug ("add an op dots")
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
                            debug ("add an op cut due to stroke")
                    elif is_raster:
                        stdops.append(RasterOpNode(color="black", output=True))
                        if debug:
                            debug ("add an op raster due to stroke")
                        has_raster = True
                    else:
                        stdops.append(EngraveOpNode(color=node.stroke, speed=35.0))
                        if debug:
                            debug (f"add an op engrave with color={node.stroke} due to stroke")
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
                        debug ("add an op raster due to fill")
                for op in stdops:
                    # Lets make sure we don't have something like that already
                    if debug:
                        debug (f"Check for existence of {op.type}")
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
                                if Color.distance(op.color, testop.color) <= fuzzydistance:
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
    #     but there are serveral use cases and counter examples are likely easy to create.
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
