import os.path
from os.path import realpath

from meerk40t.core.exceptions import BadFileError
from meerk40t.kernel import ConsoleFunction, Service, Settings, signal_listener

from ..svgelements import Close, Color, Line, Move, SVGElement
from .element_types import *
from .node.op_cut import CutOpNode
from .node.op_dots import DotsOpNode
from .node.op_engrave import EngraveOpNode
from .node.op_image import ImageOpNode
from .node.op_raster import RasterOpNode
from .node.rootnode import RootNode
from .undos import Undo
from .units import UNITS_PER_MIL, Length
from .wordlist import Wordlist


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "plugins":
        from meerk40t.core import element_commands, element_treeops

        return [element_commands.plugin, element_treeops.plugin]
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
        kernel.register(
            "format/group", "{element_type} {desc} ({children} children, {total} total)"
        )
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
        self._clipboard = {}
        self._clipboard_default = "0"

        self.note = None
        self._filename = None
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None
        self._emphasized_bounds_dirty = True
        self._tree = RootNode(self)
        self._save_restore_job = ConsoleFunction(self, ".save_restore_point\n", times=1)

        self.undo = Undo(self._tree)

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

        direct = os.path.dirname(self.op_data._config_file)
        self.mywordlist = Wordlist(self.kernel.version, direct)
        self.load_persistent_operations("previous")

        ops = list(self.ops())
        if not len(ops) and not self.operation_default_empty:
            self.load_default(performclassify=False)
        if list(self.ops()):
            # Something was loaded for default ops. Mark that.
            self.undo.mark("op-loaded")  # Mark defaulted
        self._default_stroke = None
        self._default_strokewidth = None
        self._default_fill = None
        self._first_emphasized = None
        self._align_mode = "default"
        self._align_boundaries = None
        self._align_group = False
        self._align_stack = []

    @property
    def filename(self):
        result = None
        if self._filename is not None:
            result = self._filename
        return result

    @property
    def basename(self):
        result = None
        if self._filename is not None:
            result = os.path.basename(self._filename)
        return result

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
        # We dont allow an empty stroke color as default (why not?!) -- Empty stroke colors are hard to see.
        if self._default_stroke is not None:
            return self._default_stroke
        return Color("blue")

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
            if node.bounds is not None:
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
        self.schedule(self._save_restore_job)

    def modified(self, *args):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None
        self._emphasized_bounds_painted = None
        self.schedule(self._save_restore_job)

    def node_attached(self, node, **kwargs):
        self.schedule(self._save_restore_job)

    def node_detached(self, node, **kwargs):
        self.schedule(self._save_restore_job)

    def listen_tree(self, listener):
        self._tree.listen(listener)

    def unlisten_tree(self, listener):
        self._tree.unlisten(listener)

    def load_default(self, performclassify=True):
        self.clear_operations()
        self.op_branch.add(
            type="op image",
            color="black",
            speed=140.0,
            power=1000.0,
            raster_step=3,
        )
        self.op_branch.add(type="op raster")
        self.op_branch.add(type="op engrave")
        self.op_branch.add(type="op cut")
        if performclassify:
            self.classify(list(self.elems()))
        self.signal("tree_changed")

    def load_default2(self, performclassify=True):
        self.clear_operations()
        self.op_branch.add(
            type="op image",
            color="black",
            speed=140.0,
            power=1000.0,
            raster_step=3,
        )
        self.op_branch.add(type="op raster")
        self.op_branch.add(type="op engrave")
        self.op_branch.add(type="op engrave", color="blue")
        self.op_branch.add(type="op engrave", color="green")
        self.op_branch.add(type="op engrave", color="magenta")
        self.op_branch.add(type="op engrave", color="cyan")
        self.op_branch.add(type="op engrave", color="yellow")
        self.op_branch.add(type="op cut")
        if performclassify:
            self.classify(list(self.elems()))
        self.signal("tree_changed")

    def flat(self, **kwargs):
        yield from self._tree.flat(**kwargs)

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
        yield from elements.flat(types=elem_nodes, **kwargs)

    def elems_nodes(self, depth=None, **kwargs):
        elements = self._tree.get(type="branch elems")
        yield from elements.flat(types=elem_group_nodes, depth=depth, **kwargs)

    def regmarks(self, **kwargs):
        elements = self._tree.get(type="branch reg")
        yield from elements.flat(types=elem_nodes, **kwargs)

    def regmarks_nodes(self, depth=None, **kwargs):
        elements = self._tree.get(type="branch reg")
        yield from elements.flat(types=elem_group_nodes, depth=depth, **kwargs)

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
        self.clear_regmarks()
        self.validate_selected_area()

    def clear_note(self):
        self.note = None
        self.signal("note", self.note)

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
        to_classify = []
        for drag_node in data:
            if drop_node is drag_node:
                continue
            if drop_node.drop(drag_node, modify=False):
                # Is the drag node coming from the regmarks branch?
                # If yes then we might need to classify.
                if drag_node._parent.type == "branch reg":
                    to_classify.append(drag_node)
                if special_occasion:
                    for ref in list(drag_node._references):
                        ref.remove_node()
                drop_node.drop(drag_node, modify=True)
                success = True
        if self.classify_new and len(to_classify) > 0:
            self.classify(to_classify)
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
                        self._filename = pathname
                        self.signal("tree_changed")
                        return True
                    except FileNotFoundError:
                        return False
                    except BadFileError as e:
                        kernel._console_channel(_("File is Malformed") + ": " + str(e))
                        self.signal("warning", str(e), _("File is Malformed"))
                    except OSError:
                        return False
                    finally:
                        self.signal("freeze_tree", False)
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
                    self._filename = pathname
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

    def simplify_node(self, node):
        basically_zero = 1.0e-6
        tolerance = UNITS_PER_MIL * 1

        def my_sign(x):
            # Returns +1 for positive figures, -1 for negative and 0 for Zero
            return bool(x > 0) - bool(x < 0)

        def remove_zero_length_lines(obj):
            # We remove degenerate line segments ie those of zero length
            # could be intentional in some cases, but that should be dealt
            # with in dwell cuts...
            removed = 0
            for idx in range(len(obj._segments) - 1, -1, -1):
                seg = obj._segments[idx]
                if (
                    isinstance(seg, Line)
                    and seg.start.x == seg.end.x
                    and seg.start.y == seg.end.y
                ):
                    obj._segments.pop(idx)
                    removed += 1
            return removed

        def remove_superfluous_moves(obj):
            # Two or more consecutive moves are processed
            # as well as a move at the very end
            lastseg = None
            removed = 0
            for idx in range(len(obj._segments) - 1, -1, -1):
                seg = obj._segments[idx]
                if isinstance(seg, Move):
                    if lastseg is None:
                        # Move as the very last segment -> Delete
                        obj._segments.pop(idx)
                        removed += 1
                    else:
                        if isinstance(lastseg, Move):
                            # Two consecutive moves? Delete
                            obj._segments.pop(idx)
                            removed += 1
                        else:
                            lastseg = seg
                else:
                    lastseg = seg
            return removed

        def remove_interim_points_on_line(obj):
            removed = 0
            last = None
            for idx in range(len(obj._segments) - 1, -1, -1):
                seg = obj._segments[idx]
                if isinstance(seg, Line):
                    if last is not None:
                        # Two consecutive line segments (x1,y1)-(x2,y2) and (x3,y3)-(x4,y4)
                        # denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
                        # denom = (
                        #     (seg.start.x - seg.end.x) * (last.start.y - last.end.y) -
                        #     (seg.start.y - seg.end.y) * (last.start.x - last.end.x)
                        # )
                        lastdx = last.start.x - last.end.x
                        lastdy = last.start.y - last.end.y
                        thisdx = seg.start.x - seg.end.x
                        thisdy = seg.start.y - seg.end.y
                        denom = thisdx * lastdy - thisdy * lastdx

                        same = (
                            abs(denom) < basically_zero
                            and my_sign(lastdx) == my_sign(thisdx)
                            and my_sign(lastdy) == my_sign(thisdy)
                        )
                        # if thisdx == 0 or lastdx == 0:
                        #     channel(f"One Vertical line, {thisdx:.1f}, {thisdy:1f} vs {lastdx:1f},{lastdy:.1f}")
                        # else:
                        #     channel(f"Compare {idx}, {thisdy / thisdx:.3f} vs {lastdy / lastdx:.3f}")

                        if thisdx == 0 or lastdx == 0:
                            # Vertical line - same direction?
                            if thisdx == lastdx and my_sign(thisdy) == my_sign(lastdy):
                                same = True
                        elif abs(thisdy / thisdx - lastdy / lastdx) < basically_zero:
                            same = True

                        if same:
                            # We can just merge the two segments
                            seg.end = last.end
                            obj._segments.pop(idx + 1)
                            removed += 1
                    last = seg
                else:
                    last = None
            return removed

        def combine_overlapping_chains(obj):
            def list_subpath_bounds(obj):
                # Return a sorted list of subpaths in the given path (from left to right):
                # tuples with first index, last index, x-coordinate of first segment
                result = []
                start = -1
                for current, seg in enumerate(obj._segments):
                    if isinstance(seg, Move):
                        if start >= 0:
                            result.append(
                                (start, current - 1, obj._segments[start].start.x)
                            )
                            start = -1
                    elif isinstance(seg, Close):
                        if start >= 0:
                            result.append(
                                (start, current - 1, obj._segments[start].start.x)
                            )
                            start = -1
                    else:
                        if start < 0:
                            start = current
                if start >= 0:
                    result.append((start, len(obj) - 1, obj._segments[start].start.x))
                # Now let's sort the list according to the X-start position
                result.sort(key=lambda a: a[2])
                return result

            joined = 0
            redo = True
            while redo:
                # Dont do it again unless indicated...
                redo = False
                reason = ""
                results = list_subpath_bounds(obj)
                if len(results) <= 1:
                    # only one chain, exit
                    break

                for idx, entry in enumerate(results):
                    this_start = entry[0]
                    this_end = entry[1]
                    this_endseg = obj._segments[this_end]
                    this_endline = bool(isinstance(this_endseg, Line))

                    # Look at all subsequent chains, as they are sorted we know we can just look at
                    # a) the last point and the first point or the two chains, if they are identical
                    #    the two chains can be joined (regardless of the type of the two path
                    #    segments at the end / start)
                    # b) if the last segment of the first chain and the first segment of the second chain
                    #    are lines the we establish whether they overlap
                    for idx2 in range(idx + 1, len(results)):
                        other_entry = results[idx2]
                        other_start = other_entry[0]
                        other_end = other_entry[1]
                        other_startseg = obj._segments[other_start]
                        other_startline = bool(isinstance(other_startseg, Line))
                        # Do the lines overlap or have a common end / startpoint together?
                        if (
                            abs(this_endseg.end.x - other_startseg.start.x) < tolerance
                            and abs(this_endseg.end.y - other_startseg.start.y)
                            < tolerance
                        ):
                            for idx3 in range(other_end - other_start + 1):
                                obj._segments.insert(
                                    this_end + 1, obj._segments.pop(other_end)
                                )
                            joined += 1
                            redo = True
                            reason = f"Join segments at endpoints {idx} - {idx2}"
                            break
                        else:
                            if not other_startline or not this_endline:
                                # incompatible types, need two lines
                                continue
                            thisdx = this_endseg.start.x - this_endseg.end.x
                            thisdy = this_endseg.start.y - this_endseg.end.y
                            lastdx = other_startseg.start.x - other_startseg.end.x
                            lastdy = other_startseg.start.y - other_startseg.end.y
                            denom = thisdx * lastdy - thisdy * lastdx

                            # We have a couple of base cases
                            # a) end point of first line identical to start point of second line
                            # -> already covered elsewhere

                            # b) Lines are not parallel -> ignore
                            if abs(denom) > basically_zero:
                                continue

                            if abs(thisdx) > basically_zero:
                                # Non-vertical lines
                                # c) second segment starts left of the first -> ignore
                                if other_startseg.start.x < this_endseg.start.x:
                                    continue

                                # d) second segment fully to the right of the first -> ignore
                                if other_startseg.start.x > this_endseg.end.x:
                                    continue

                                # e) They could still be just parallel, so let's establish this...
                                if (
                                    abs(lastdx) < basically_zero
                                    or abs(thisdx) < basically_zero
                                ):
                                    # Was coming from zero length lines, now removed earlier
                                    continue
                                b1 = (
                                    this_endseg.start.y
                                    - thisdy / thisdx * this_endseg.start.x
                                )
                                b2 = (
                                    other_startseg.start.y
                                    - lastdy / lastdx * other_startseg.start.x
                                )
                                if abs(b1 - b2) > tolerance:
                                    continue

                                # f) Lying completely inside, only if the second chain is a single line we can remove it...
                                if other_startseg.end.x <= this_endseg.end.x:
                                    if other_start == other_end:
                                        # Can be eliminated....
                                        obj._segments.pop(other_start)
                                        joined += 1
                                        redo = True
                                        reason = (
                                            f"Removed segment {idx2} fully inside {idx}"
                                        )
                                        break
                                    else:
                                        continue
                                # g) the remaining case is an overlap on x, so we can adjust the start to the end and join
                                other_startseg.start.x = this_endseg.end.x
                                other_startseg.start.y = this_endseg.end.y
                                # Now copy the segments together:
                                # We know that the to be copied segments, ie the source segments, lie behind the target segments
                                # print (f"We copy [{other_start}:{other_end}] to the end after {this_end}")
                                for idx3 in range(other_end - other_start + 1):
                                    # print(f"copy #{idx3}: {obj._segments[this_end + 1]} <- {obj._segments[other_end]}")
                                    obj._segments.insert(
                                        this_end + 1, obj._segments.pop(other_end)
                                    )
                                joined += 1
                                redo = True
                                reason = f"Added overlapping segment {idx2} to {idx}"
                                break
                            else:
                                # vertical lines but still the same logic applies...
                                # c) second segment starts on top of the first -> ignore
                                if other_startseg.start.y < this_endseg.start.y:
                                    continue

                                # d) second segment fully below the first -> ignore
                                if other_startseg.start.y > this_endseg.end.y:
                                    continue

                                # e) They could still be just parallel, so let's establish this...
                                if (
                                    abs(other_startseg.start.x - this_endseg.start.x)
                                    > tolerance
                                ):
                                    continue

                                # f) Lying completely inside, only if the second chain is a single line we can remove it...
                                if other_startseg.end.y <= this_endseg.end.y:
                                    if other_start == other_end:
                                        # Can be eliminated....
                                        obj._segments.pop(other_start)
                                        joined += 1
                                        redo = True
                                        reason = f"Removed vertical segment {idx2} fully inside {idx}"
                                        break
                                    else:
                                        continue
                                # g) the remaining case is an overlap on y, so we can adjust the start to the end and join
                                other_startseg.start.x = this_endseg.end.x
                                other_startseg.start.y = this_endseg.end.y
                                # Now copy the segments together:
                                # We know that the to be copied segments, ie the source segments,
                                # lie behind the target segments
                                for idx3 in range(other_end - other_start + 1):
                                    obj._segments.insert(
                                        this_end + 1, obj._segments.pop(other_end)
                                    )
                                joined += 1
                                reason = f"Added overlapping vertical segment {idx2} to {idx}"
                                redo = True
                                break
                    # end of inner loop

                    if redo:
                        # print(f"Redo required inner loop: {reason}")
                        changed = True
                        break
                # end of outer loop
            return joined

        def simplify_polyline(obj):
            removed = 0
            pt_older = None
            pt_old = None
            for idx in range(len(obj.points) - 1, -1, -1):
                pt = obj.points[idx]
                if pt_older is not None and pt_old is not None:
                    # Two consecutive line segments (x1,y1)-(x2,y2) and (x3,y3)-(x4,y4)
                    # denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
                    # denom = (
                    #     (pt[0] - pt_old[0]) * (pt_old[1] - pt_older[1]) -
                    #     (pt[1] - pt_old[1]) * (pt_old[0] - pt_older[0])
                    # )
                    lastdx = pt_old[0] - pt_older[0]
                    lastdy = pt_old[1] - pt_older[1]
                    thisdx = pt[0] - pt_old[0]
                    thisdy = pt[1] - pt_old[1]
                    denom = thisdx * lastdy - thisdy * lastdx
                    same = (
                        abs(denom) < basically_zero
                        and my_sign(lastdx) == my_sign(thisdx)
                        and my_sign(lastdy) == my_sign(thisdy)
                    )
                    # Opposing directions may not happen

                    if same:
                        # We can just merge the two segments by
                        # elminating the middle point
                        obj.points.pop(idx + 1)
                        removed += 1
                        # just set the middle point to the last point,
                        # so that the last point remains
                        pt_old = pt_older

                pt_older = pt_old
                pt_old = pt
            return removed

        changed = False
        before = 0
        after = 0

        if node.type == "elem path" and len(node.path._segments) > 1:
            obj = node.path
            before = len(obj._segments)

            # Pass 1: Dropping zero length line segments
            eliminated = remove_zero_length_lines(obj)
            if eliminated > 0:
                changed = True

            # Pass 2: look inside the nodes and bring small line segments back together...
            eliminated = remove_interim_points_on_line(obj)
            if eliminated > 0:
                changed = True

            # Pass 3: look at the subpaths....
            eliminated = combine_overlapping_chains(obj)
            if eliminated > 0:
                changed = True

            # pass 4: remove superfluous moves
            eliminated = remove_superfluous_moves(obj)
            if eliminated > 0:
                changed = True

            after = len(obj._segments)
        elif node.type == "elem polyline" and len(node.shape.points) > 2:
            obj = node.shape
            before = len(obj.points)
            eliminated = simplify_polyline(obj)
            if eliminated > 0:
                changed = True
            after = len(obj.points)

        # print (f"Before: {before}, After: {after}")
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
