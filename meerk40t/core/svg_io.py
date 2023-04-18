"""
This modeu
"""

import ast
import gzip
import math
import os
from base64 import b64encode
from io import BytesIO
from xml.etree.ElementTree import Element, ElementTree, ParseError, SubElement

from meerk40t.core.exceptions import BadFileError
from meerk40t.core.node.node import Fillrule, Linecap, Linejoin

from ..svgelements import (
    SVG,
    SVG_ATTR_CENTER_X,
    SVG_ATTR_CENTER_Y,
    SVG_ATTR_DATA,
    SVG_ATTR_FILL,
    SVG_ATTR_FILL_OPACITY,
    SVG_ATTR_FONT_FAMILY,
    SVG_ATTR_FONT_SIZE,
    SVG_ATTR_FONT_STRETCH,
    SVG_ATTR_FONT_STYLE,
    SVG_ATTR_FONT_VARIANT,
    SVG_ATTR_HEIGHT,
    SVG_ATTR_ID,
    SVG_ATTR_POINTS,
    SVG_ATTR_RADIUS_X,
    SVG_ATTR_RADIUS_Y,
    SVG_ATTR_STROKE,
    SVG_ATTR_STROKE_OPACITY,
    SVG_ATTR_STROKE_WIDTH,
    SVG_ATTR_TAG,
    SVG_ATTR_TEXT_ALIGNMENT_BASELINE,
    SVG_ATTR_TEXT_ANCHOR,
    SVG_ATTR_TEXT_DOMINANT_BASELINE,
    SVG_ATTR_TRANSFORM,
    SVG_ATTR_VECTOR_EFFECT,
    SVG_ATTR_VERSION,
    SVG_ATTR_VIEWBOX,
    SVG_ATTR_WIDTH,
    SVG_ATTR_X,
    SVG_ATTR_X1,
    SVG_ATTR_X2,
    SVG_ATTR_XMLNS,
    SVG_ATTR_XMLNS_EV,
    SVG_ATTR_XMLNS_LINK,
    SVG_ATTR_Y,
    SVG_ATTR_Y1,
    SVG_ATTR_Y2,
    SVG_NAME_TAG,
    SVG_RULE_EVENODD,
    SVG_RULE_NONZERO,
    SVG_TAG_ELLIPSE,
    SVG_TAG_GROUP,
    SVG_TAG_IMAGE,
    SVG_TAG_LINE,
    SVG_TAG_PATH,
    SVG_TAG_POLYLINE,
    SVG_TAG_RECT,
    SVG_TAG_TEXT,
    SVG_VALUE_NON_SCALING_STROKE,
    SVG_VALUE_NONE,
    SVG_VALUE_VERSION,
    SVG_VALUE_XLINK,
    SVG_VALUE_XMLNS,
    SVG_VALUE_XMLNS_EV,
    Circle,
    Close,
    Color,
    Ellipse,
    Group,
    Matrix,
    Path,
    Point,
    Polygon,
    Polyline,
    Rect,
    SimpleLine,
    SVGImage,
    SVGText,
    Use,
)
from .units import DEFAULT_PPI, NATIVE_UNIT_PER_INCH

SVG_ATTR_STROKE_JOIN = "stroke-linejoin"
SVG_ATTR_STROKE_CAP = "stroke-linecap"
SVG_ATTR_FILL_RULE = "fill-rule"


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation
        choices = [
            {
                "attr": "svg_viewport_bed",
                "object": kernel.elements,
                "default": True,
                "type": bool,
                "label": _("SVG Viewport is Bed"),
                "tip": _(
                    "SVG files can be saved without real physical units.\n"
                    "This setting uses the SVG viewport dimensions to scale the rest of the elements in the file."
                ),
                "page": "Input/Output",
                "section": "Input",
            },
        ]
        kernel.register_choices("preferences", choices)
        kernel.register("load/SVGLoader", SVGLoader)
        kernel.register("save/SVGWriter", SVGWriter)


MEERK40T_NAMESPACE = "https://github.com/meerk40t/meerk40t/wiki/Namespace"
MEERK40T_XMLS_ID = "meerk40t"


def capstr(linecap):
    if linecap == Linecap.CAP_BUTT:
        return "butt"
    elif linecap == Linecap.CAP_SQUARE:
        return "square"
    else:
        return "round"


def joinstr(linejoin):
    if linejoin == Linejoin.JOIN_ARCS:
        return "arcs"
    elif linejoin == Linejoin.JOIN_BEVEL:
        return "bevel"
    elif linejoin == Linejoin.JOIN_MITER_CLIP:
        return "miter-clip"
    elif linejoin == Linejoin.JOIN_ROUND:
        return "round"
    else:
        return "miter"


def rulestr(fillrule):
    if fillrule == Fillrule.FILLRULE_EVENODD:
        return "evenodd"
    else:
        return "nonzero"


def copy_attributes(source, target):
    if hasattr(source, "stroke"):
        target.stroke = source.stroke
    if hasattr(source, "fill"):
        target.fill = source.fill


class SVGWriter:
    @staticmethod
    def save_types():
        yield "Scalable Vector Graphics", "svg", "image/svg+xml", "default"
        yield "SVG-Plain (no extensions)", "svg", "image/svg+xml", "plain"
        yield "SVG-Compressed", "svgz", "image/svg+xml", "compressed"

    @staticmethod
    def save(context, f, version="default"):
        # print (f"Version was set to '{version}'")
        root = Element(SVG_NAME_TAG)
        root.set(SVG_ATTR_VERSION, SVG_VALUE_VERSION)
        root.set(SVG_ATTR_XMLNS, SVG_VALUE_XMLNS)
        root.set(SVG_ATTR_XMLNS_LINK, SVG_VALUE_XLINK)
        root.set(SVG_ATTR_XMLNS_EV, SVG_VALUE_XMLNS_EV)
        if version != "plain":
            root.set(
                "xmlns:" + MEERK40T_XMLS_ID,
                MEERK40T_NAMESPACE,
            )
        scene_width = context.device.length_width
        scene_height = context.device.length_height
        root.set(SVG_ATTR_WIDTH, scene_width.length_mm)
        root.set(SVG_ATTR_HEIGHT, scene_height.length_mm)
        viewbox = f"{0} {0} {int(float(scene_width))} {int(float(scene_height))}"
        root.set(SVG_ATTR_VIEWBOX, viewbox)
        elements = context.elements
        elements.validate_ids()
        # If we want to write labels then we need to establish the inkscape namespace
        has_labels = False
        for n in elements.elems_nodes():
            if hasattr(n, "label") and n.label is not None and n.label != "":
                has_labels = True
                break
            if n.type == "file":
                has_labels = True
                break
        if not has_labels:
            for n in elements.regmarks_nodes():
                if hasattr(n, "label") and n.label is not None and n.label != "":
                    has_labels = True
                    break
        if has_labels:
            root.set(
                "xmlns:inkscape",
                "http://www.inkscape.org/namespaces/inkscape",
            )
        if version != "plain":
            # If there is a note set then we save the note with the project.
            if elements.note is not None:
                subelement = SubElement(root, "note")
                subelement.set(SVG_TAG_TEXT, elements.note)

        SVGWriter._write_tree(root, elements._tree, version)

        SVGWriter._pretty_print(root)
        tree = ElementTree(root)
        if f.lower().endswith("svgz"):
            f = gzip.open(f, "wb")
        tree.write(f)

    @staticmethod
    def _write_tree(xml_tree, node_tree, version):
        # print (f"Write_tree with {version}")
        for node in node_tree.children:
            if version != "plain" and node.type == "branch ops":
                SVGWriter._write_operations(xml_tree, node, version)
            if node.type == "branch elems":
                SVGWriter._write_elements(xml_tree, node, version)
            elif node.type == "branch reg":
                SVGWriter._write_regmarks(xml_tree, node, version)

    @staticmethod
    def _write_elements(xml_tree, elem_tree, version):
        """
        Write the elements branch part of the tree to disk.

        @param xml_tree:
        @param elem_tree:
        @return:
        """

        def single_file_node():
            # do we have more than one element on the top level hierarchy?
            # If no then return True
            flag = True
            if len(elem_tree.children) > 1:
                flag = False
            return flag

        for c in elem_tree.children:
            if c.type == "elem ellipse":
                element = c.shape
                copy_attributes(c, element)
                subelement = SubElement(xml_tree, SVG_TAG_ELLIPSE)
                subelement.set(SVG_ATTR_CENTER_X, str(element.cx))
                subelement.set(SVG_ATTR_CENTER_Y, str(element.cy))
                subelement.set(SVG_ATTR_RADIUS_X, str(element.rx))
                subelement.set(SVG_ATTR_RADIUS_Y, str(element.ry))
                t = Matrix(c.matrix)
                if not t.is_identity():
                    subelement.set(
                        "transform",
                        f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                    )
            elif c.type == "elem image":
                element = c.image
                subelement = SubElement(xml_tree, SVG_TAG_IMAGE)
                stream = BytesIO()
                try:
                    c.image.save(stream, format="PNG", dpi=(c.dpi, c.dpi))
                except OSError:
                    # Edge condition if the original image was CMYK and never touched it can't encode to PNG
                    c.image.convert("RGBA").save(
                        stream, format="PNG", dpi=(c.dpi, c.dpi)
                    )
                subelement.set(
                    "xlink:href",
                    f"data:image/png;base64,{b64encode(stream.getvalue()).decode('utf8')}",
                )
                subelement.set(SVG_ATTR_X, "0")
                subelement.set(SVG_ATTR_Y, "0")
                subelement.set(SVG_ATTR_WIDTH, str(c.image.width))
                subelement.set(SVG_ATTR_HEIGHT, str(c.image.height))
                t = c.matrix
                if not t.is_identity():
                    subelement.set(
                        "transform",
                        f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                    )
            elif c.type == "elem line":
                element = c.shape
                copy_attributes(c, element)
                subelement = SubElement(xml_tree, SVG_TAG_LINE)
                subelement.set(SVG_ATTR_X1, str(element.x1))
                subelement.set(SVG_ATTR_Y1, str(element.y1))
                subelement.set(SVG_ATTR_X2, str(element.x2))
                subelement.set(SVG_ATTR_Y2, str(element.y2))
                t = c.matrix
                if not t.is_identity():
                    subelement.set(
                        "transform",
                        f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                    )

            elif c.type == "elem path":
                element = c.path
                copy_attributes(c, element)
                subelement = SubElement(xml_tree, SVG_TAG_PATH)
                subelement.set(SVG_ATTR_DATA, element.d(transformed=False))
                t = c.matrix
                if not t.is_identity():
                    subelement.set(
                        "transform",
                        f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                    )
            elif c.type == "elem point":
                element = Point(c.point)
                c.x = element.x
                c.y = element.y
                subelement = SubElement(xml_tree, "element")
                t = c.matrix
                if not t.is_identity():
                    subelement.set(
                        "transform",
                        f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                    )
                SVGWriter._write_custom(subelement, c)
            elif c.type == "elem polyline":
                element = c.shape
                copy_attributes(c, element)
                subelement = SubElement(xml_tree, SVG_TAG_POLYLINE)
                subelement.set(
                    SVG_ATTR_POINTS,
                    " ".join([f"{e[0]} {e[1]}" for e in element.points]),
                )
                t = c.matrix
                if not t.is_identity():
                    subelement.set(
                        "transform",
                        f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                    )
            elif c.type == "elem rect":
                element = c.shape
                copy_attributes(c, element)
                subelement = SubElement(xml_tree, SVG_TAG_RECT)
                subelement.set(SVG_ATTR_X, str(element.x))
                subelement.set(SVG_ATTR_Y, str(element.y))
                subelement.set(SVG_ATTR_RADIUS_X, str(element.rx))
                subelement.set(SVG_ATTR_RADIUS_Y, str(element.ry))
                subelement.set(SVG_ATTR_WIDTH, str(element.width))
                subelement.set(SVG_ATTR_HEIGHT, str(element.height))
                t = c.matrix
                if not t.is_identity():
                    subelement.set(
                        "transform",
                        f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                    )
            elif c.type == "elem text":
                subelement = SubElement(xml_tree, SVG_TAG_TEXT)
                subelement.text = c.text
                t = c.matrix
                if not t.is_identity():
                    subelement.set(
                        SVG_ATTR_TRANSFORM,
                        f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                    )
                # Font features are covered by the `font` value shorthand
                if c.font_family:
                    subelement.set(SVG_ATTR_FONT_FAMILY, c.font_family)
                if c.font_style:
                    subelement.set(SVG_ATTR_FONT_STYLE, c.font_style)
                if c.font_variant:
                    subelement.set(SVG_ATTR_FONT_VARIANT, c.font_variant)
                if c.font_stretch:
                    subelement.set(SVG_ATTR_FONT_STRETCH, c.font_stretch)
                if c.font_size:
                    subelement.set(SVG_ATTR_FONT_SIZE, str(c.font_size))
                if c.line_height:
                    subelement.set("line_height", str(c.line_height))
                if c.anchor:
                    subelement.set(SVG_ATTR_TEXT_ANCHOR, c.anchor)
                if c.baseline:
                    subelement.set(SVG_ATTR_TEXT_DOMINANT_BASELINE, c.baseline)
                decor = ""
                if c.underline:
                    decor += " underline"
                if c.overline:
                    decor += " overline"
                if c.strikethrough:
                    decor += " line-through"
                decor = decor.strip()
                if decor:
                    subelement.set("text-decoration", decor)
                element = c
            elif c.type == "group":
                # This is a structural group node of elements. Recurse call to write values.
                group_element = SubElement(xml_tree, SVG_TAG_GROUP)
                if hasattr(c, "label") and c.label is not None and c.label != "":
                    group_element.set("inkscape:label", c.label)
                SVGWriter._write_elements(group_element, c, version)
                continue
            elif c.type == "file":
                # This is a structural group node of elements. Recurse call to write values.
                # is this the only file node? If yes then no need to generate an additional group
                if single_file_node():
                    SVGWriter._write_elements(xml_tree, c, version)
                else:
                    group_element = SubElement(xml_tree, SVG_TAG_GROUP)
                    if hasattr(c, "name") and c.name is not None and c.name != "":
                        group_element.set("inkscape:label", c.name)
                    SVGWriter._write_elements(group_element, c, version)
                continue
            else:
                if version != "plain":
                    # This is a non-standard element. Save custom.
                    subelement = SubElement(xml_tree, "element")
                    SVGWriter._write_custom(subelement, c)
                    continue

            ###############
            # GENERIC SAVING STANDARD ELEMENT
            ###############
            for key, value in c.__dict__.items():
                if (
                    not key.startswith("_")
                    and key
                    not in (
                        "settings",
                        "attributes",
                        "linecap",
                        "linejoin",
                        "fillrule",
                        "stroke_width",
                    )
                    and value is not None
                    and isinstance(value, (str, int, float, complex, list, dict))
                ):
                    subelement.set(key, str(value))
            ###############
            # SAVE STROKE
            ###############
            if hasattr(c, "stroke_scaled"):
                if not c.stroke_scaled:
                    subelement.set(SVG_ATTR_VECTOR_EFFECT, SVG_VALUE_NON_SCALING_STROKE)

            ###############
            # SAVE CAP/JOIN/FILL-RULE
            ###############
            if hasattr(c, "linecap"):
                subelement.set(SVG_ATTR_STROKE_CAP, capstr(c.linecap))
            if hasattr(c, "linejoin"):
                subelement.set(SVG_ATTR_STROKE_JOIN, joinstr(c.linejoin))
            if hasattr(c, "fillrule"):
                subelement.set(SVG_ATTR_FILL_RULE, rulestr(c.fillrule))

            ###############
            # SAVE LABEL
            ###############
            if hasattr(c, "label") and c.label is not None and c.label != "":
                subelement.set("inkscape:label", c.label)

            ###############
            # SAVE STROKE
            ###############
            if hasattr(c, "stroke"):
                stroke = c.stroke
            else:
                stroke = None
            if stroke is not None:
                stroke_opacity = stroke.opacity
                stroke = (
                    str(abs(stroke))
                    if stroke is not None and stroke.value is not None
                    else SVG_VALUE_NONE
                )
                subelement.set(SVG_ATTR_STROKE, stroke)
                if stroke_opacity != 1.0 and stroke_opacity is not None:
                    subelement.set(SVG_ATTR_STROKE_OPACITY, str(stroke_opacity))
                try:
                    factor = 1.0
                    try:
                        if c.stroke_scaled:
                            factor = c.stroke_factor
                    except AttributeError:
                        pass
                    if c.matrix.determinant == 0:
                        c_m_d = 1
                    else:
                        c_m_d = math.sqrt(abs(c.matrix.determinant))
                    stroke_width = str(factor * c.stroke_width / c_m_d)
                    subelement.set(SVG_ATTR_STROKE_WIDTH, stroke_width)
                except AttributeError:
                    pass

            ###############
            # SAVE FILL
            ###############
            if hasattr(c, "fill"):
                fill = c.fill
            else:
                fill = None
            if fill is not None:
                fill_opacity = fill.opacity
                fill = (
                    str(abs(fill))
                    if fill is not None and fill.value is not None
                    else SVG_VALUE_NONE
                )
                subelement.set(SVG_ATTR_FILL, fill)
                if fill_opacity != 1.0 and fill_opacity is not None:
                    subelement.set(SVG_ATTR_FILL_OPACITY, str(fill_opacity))
            else:
                subelement.set(SVG_ATTR_FILL, SVG_VALUE_NONE)
            subelement.set(SVG_ATTR_ID, str(c.id))

    @staticmethod
    def _write_operations(xml_tree, op_tree, version):
        """
        Write the operations branch part of the tree to disk.

        @param xml_tree:
        @param elem_tree:
        @return:
        """
        for c in op_tree.children:
            if c.type.startswith("util") or c.type.startswith("place"):
                subelement = SubElement(xml_tree, MEERK40T_XMLS_ID + ":operation")
                SVGWriter._write_custom(subelement, c)
            else:
                SVGWriter._write_operation(xml_tree, c)

    @staticmethod
    def _write_regmarks(xml_tree, reg_tree, version):
        if len(reg_tree.children):
            regmark = SubElement(xml_tree, SVG_TAG_GROUP)
            regmark.set("id", "regmarks")
            regmark.set("visibility", "hidden")
            SVGWriter._write_elements(regmark, reg_tree, version)

    @staticmethod
    def _write_operation(xml_tree, node):
        """
        Write an individual operation. This is any node directly under `branch ops`

        @param xml_tree:
        @param node:
        @return:
        """
        subelement = SubElement(xml_tree, MEERK40T_XMLS_ID + ":operation")
        subelement.set("type", str(node.type))
        if node.label is not None:
            subelement.set("label", str(node.label))
        if node.lock is not None:
            subelement.set("lock", str(node.lock))
        try:
            for key, value in node.settings.items():
                if not key:
                    # If key is None, do not save.
                    continue
                if key.startswith("_"):
                    continue
                if value is None:
                    continue
                if key in ("references", "tag", "type"):
                    # References key from previous loaded version (filter out, rebuild)
                    continue
                subelement.set(key, str(value))
        except AttributeError:
            pass
        contains = list()
        for c in node.children:
            if c.type == "reference":
                c = c.node  # Contain direct reference not reference node reference.
            contains.append(c.id)
        if contains:
            subelement.set("references", " ".join(contains))
        subelement.set(SVG_ATTR_ID, str(node.id))

    @staticmethod
    def _write_custom(subelement, node):
        subelement.set("type", node.type)
        for key, value in node.__dict__.items():
            if not key:
                # If key is None, do not save.
                continue
            if key.startswith("_"):
                continue
            if value is None:
                continue
            if key in ("references", "tag", "type", "draw", "stroke_width", "matrix"):
                # References key from previous loaded version (filter out, rebuild)
                continue
            subelement.set(key, str(value))

        contains = list()
        for c in node.children:
            if c.type == "reference":
                c = c.node  # Contain direct reference not reference node reference.
            contains.append(c.id)
        if contains:
            subelement.set("references", " ".join(contains))

        subelement.set(SVG_ATTR_ID, str(node.id))

    @staticmethod
    def _pretty_print(current, parent=None, index=-1, depth=0):
        for i, node in enumerate(current):
            SVGWriter._pretty_print(node, current, i, depth + 1)
        if parent is not None:
            if index == 0:
                parent.text = "\n" + ("\t" * depth)
            else:
                parent[index - 1].tail = "\n" + ("\t" * depth)
            if index == len(parent) - 1:
                current.tail = "\n" + ("\t" * (depth - 1))


class SVGProcessor:
    def __init__(self, elements):
        self.elements = elements
        self.element_list = list()
        self.regmark_list = list()
        self.reverse = False
        self.requires_classification = True
        self.operations_cleared = False
        self.pathname = None
        self.regmark = None

        # Setting this is bringing as much benefit as anticipated
        # Both the time to load the file (unexpectedly) as well as the time
        # for the first emphasis when all the nonpopulated bounding
        # boxes will be calculated are benefitting from this precalculation:
        # (All values as average over three consecutive loads)
        #                    |           Load             |       First Select
        # File               |   Old  | Precalc | Speedup |  Old   | Precalc | Speedup
        # Star Wars Calendar |  10,3  |   4,8   |  115%   |  3,4   |   1,0   | 243%
        # Element Classific  |   1,7  |   1,1   |   59%   |  0,6   |   0,4   |  54%
        # Egyptian Bark      |  72,1  |  43,9   |   64%   | 34,6   |  20,1   |  72%
        self.precalc_bbox = True

    def process(self, svg, pathname):
        self.pathname = pathname
        context_node = self.elements.get(type="branch elems")
        file_node = context_node.add(type="file", filepath=pathname)
        self.regmark = self.elements.reg_branch
        file_node.focus()

        self.parse(svg, file_node, self.element_list)
        if self.operations_cleared:
            for op in self.elements.ops():
                if not hasattr(op, "settings"):
                    # Some special nodes might lack settings these can't have references.
                    continue
                refs = op.settings.get("references")
                if refs is None:
                    continue
                self.requires_classification = False
                for ref in refs.split(" "):
                    for e in self.element_list:
                        if e.id == ref:
                            op.add_reference(e)

        if self.requires_classification and self.elements.classify_new:
            self.elements.classify(self.element_list)

    def check_for_mk_path_attributes(self, node, element):
        for prop in element.values:
            lc = element.values.get(prop)
            # print (f"Property: {prop} = {lc}")
            if prop.startswith("mk"):
                if lc is not None:
                    setattr(node, prop, lc)

    def check_for_fill_attributes(self, node, element):
        lc = element.values.get(SVG_ATTR_FILL_RULE)
        if lc is not None:
            nlc = Fillrule.FILLRULE_NONZERO
            lc = lc.lower()
            if lc == SVG_RULE_EVENODD:
                nlc = Fillrule.FILLRULE_EVENODD
            elif lc == SVG_RULE_NONZERO:
                nlc = Fillrule.FILLRULE_NONZERO
            node.fillrule = nlc

    def check_for_line_attributes(self, node, element):
        lc = element.values.get(SVG_ATTR_STROKE_CAP)
        if lc is not None:
            nlc = Linecap.CAP_ROUND
            if lc == "butt":
                nlc = Linecap.CAP_BUTT
            elif lc == "round":
                nlc = Linecap.CAP_ROUND
            elif lc == "square":
                nlc = Linecap.CAP_SQUARE
            node.linecap = nlc
        lj = element.values.get(SVG_ATTR_STROKE_JOIN)
        if lj is not None:
            nlj = Linejoin.JOIN_MITER
            if lj == "arcs":
                nlj = Linejoin.JOIN_ARCS
            elif lj == "bevel":
                nlj = Linejoin.JOIN_BEVEL
            elif lj == "miter":
                nlj = Linejoin.JOIN_MITER
            elif lj == "miter-clip":
                nlj = Linejoin.JOIN_MITER_CLIP
            elif lj == "round":
                nlj = Linejoin.JOIN_ROUND
            node.linejoin = nlj

    @staticmethod
    def is_dot(element):
        """
        Check for the degenerate shape dots. This could by a Path that consisting of a Move + Close, Move, or Move any
        path-segment that has a distance of 0 units. It could be a simple line to the same spot. It could be a polyline
        which has a single point.

        We avoid doing any calculations without checking the degenerate nature of the would-be dot first.

        @param element:
        @return:
        """
        if isinstance(element, Path):
            if len(element) > 2 or element.length(error=1, min_depth=1) > 0:
                return False, None
            return True, abs(element).first_point
        elif isinstance(element, SimpleLine):
            if element.length() == 0:
                return True, abs(Path(element)).first_point
        elif isinstance(element, (Polyline, Polygon)):
            if len(element) > 1:
                return False, None
            if element.length() == 0:
                return True, abs(Path(element)).first_point
        return False, None

    def parse(self, element, context_node, e_list, uselabel=None):
        def is_child(candidate, parent_node):
            if candidate is None:
                return False
            if candidate is parent_node:
                return True
            if candidate.parent is None:
                return False
            return is_child(candidate.parent, parent_node)

        if element.values.get("visibility") == "hidden":
            # This does not allow substructures...
            # Are we already underneath regmark?
            if not is_child(context_node, self.regmark):
                context_node = self.regmark
            e_list = self.regmark_list
        ident = element.id
        # Let's see whether we can get the label from an inkscape save
        _label = None
        if uselabel is not None and uselabel != "":
            _label = uselabel
        if _label is None:
            ink_tag = "inkscape:label"
            try:
                inkscape = element.values.get("inkscape")
                if inkscape is not None and inkscape != "":
                    ink_tag = "{" + inkscape + "}label"
            except (AttributeError, KeyError):
                pass
            try:
                _label = element.values.get(ink_tag)
                if _label == "":
                    _label = None
                # print ("Found label: %s" % my_label)
            except (AttributeError, KeyError):
                # Label might simply be "label"
                _label = element.values.get("label")
        _lock = None
        try:
            _lock = bool(element.values.get("lock") == "True")
        except (ValueError, TypeError):
            pass
        is_dot, dot_point = SVGProcessor.is_dot(element)
        if is_dot:
            node = context_node.add(
                point=dot_point,
                type="elem point",
                matrix=Matrix(),
                fill=element.fill,
                stroke=element.stroke,
                label=_label,
                lock=_lock,
            )
            e_list.append(node)
        elif isinstance(element, SVGText):
            if element.text is None:
                return

            decor = element.values.get("text-decoration", "").lower()
            node = context_node.add(
                id=ident,
                text=element.text,
                x=element.x,
                y=element.y,
                font=element.values.get("font"),
                anchor=element.values.get(SVG_ATTR_TEXT_ANCHOR),
                baseline=element.values.get(
                    SVG_ATTR_TEXT_ALIGNMENT_BASELINE,
                    element.values.get(SVG_ATTR_TEXT_DOMINANT_BASELINE, "baseline"),
                ),
                matrix=element.transform,
                fill=element.fill,
                stroke=element.stroke,
                stroke_width=element.stroke_width,
                stroke_scale=bool(
                    SVG_VALUE_NON_SCALING_STROKE
                    not in element.values.get(SVG_ATTR_VECTOR_EFFECT, "")
                ),
                underline="underline" in decor,
                strikethrough="line-through" in decor,
                overline="overline" in decor,
                texttransform=element.values.get("text-transform"),
                type="elem text",
                label=_label,
                settings=element.values,
            )
            e_list.append(node)
        elif isinstance(element, Path):
            if len(element) >= 0:
                if element.values.get("type") == "elem polyline":
                    # Type is polyline we should restore the node type if we have sufficient info to do so.
                    pass
                if element.values.get("type") == "elem ellipse":
                    # There is not enough info to reconstruct this.
                    pass
                if element.values.get("type") == "elem rect":
                    # There is not enough info to reconstruct this.
                    pass
                if element.values.get("type") == "elem line":
                    pass
                element.approximate_arcs_with_cubics()
                node = context_node.add(
                    path=element, type="elem path", id=ident, label=_label, lock=_lock
                )
                self.check_for_line_attributes(node, element)
                self.check_for_fill_attributes(node, element)
                self.check_for_mk_path_attributes(node, element)
                e_list.append(node)
        elif isinstance(element, (Polygon, Polyline)):
            if element.is_degenerate():
                return
            node = context_node.add(
                shape=element,
                type="elem polyline",
                id=ident,
                label=_label,
                lock=_lock,
            )
            self.check_for_line_attributes(node, element)
            self.check_for_fill_attributes(node, element)
            if self.precalc_bbox:
                # bounds will be done here, paintbounds wont...
                if element.transform.is_identity():
                    points = element.points
                else:
                    points = list(
                        map(element.transform.point_in_matrix_space, element.points)
                    )
                xmin = min(p.x for p in points if p is not None)
                ymin = min(p.y for p in points if p is not None)
                xmax = max(p.x for p in points if p is not None)
                ymax = max(p.y for p in points if p is not None)
                node._bounds = [
                    xmin,
                    ymin,
                    xmax,
                    ymax,
                ]
                node._bounds_dirty = False
                node.revalidate_points()
                node._points_dirty = False
            e_list.append(node)
        elif isinstance(element, (Circle, Ellipse)):
            if element.is_degenerate():
                return
            node = context_node.add(
                shape=element,
                type="elem ellipse",
                id=ident,
                label=_label,
                lock=_lock,
            )
            e_list.append(node)
        elif isinstance(element, Rect):
            if element.is_degenerate():
                return
            node = context_node.add(
                shape=element, type="elem rect", id=ident, label=_label, lock=_lock
            )
            self.check_for_line_attributes(node, element)
            if self.precalc_bbox:
                # bounds will be done here, paintbounds wont...
                points = (
                    Point(element.x, element.y),
                    Point(element.x + element.width, element.y),
                    Point(element.x + element.width, element.y + element.height),
                    Point(element.x, element.y + element.height),
                )
                if not element.transform.is_identity():
                    points = list(map(element.transform.point_in_matrix_space, points))
                xmin = min(p.x for p in points)
                ymin = min(p.y for p in points)
                xmax = max(p.x for p in points)
                ymax = max(p.y for p in points)
                node._bounds = [
                    xmin,
                    ymin,
                    xmax,
                    ymax,
                ]
                node._bounds_dirty = False
                node.revalidate_points()
                node._points_dirty = False
            e_list.append(node)
        elif isinstance(element, SimpleLine):
            if element.is_degenerate():
                return
            node = context_node.add(
                shape=element, type="elem line", id=ident, label=_label, lock=_lock
            )
            self.check_for_line_attributes(node, element)
            if self.precalc_bbox:
                # bounds will be done here, paintbounds wont...
                points = (
                    Point(element.x1, element.y1),
                    Point(element.x2, element.y2),
                )
                if not element.transform.is_identity():
                    points = list(map(element.transform.point_in_matrix_space, points))
                xmin = min(p.x for p in points)
                ymin = min(p.y for p in points)
                xmax = max(p.x for p in points)
                ymax = max(p.y for p in points)
                node._bounds = [
                    xmin,
                    ymin,
                    xmax,
                    ymax,
                ]
                node._bounds_dirty = False
                node.revalidate_points()
                node._points_dirty = False
            e_list.append(node)
        elif isinstance(element, SVGImage):
            try:
                element.load(os.path.dirname(self.pathname))
                try:
                    operations = ast.literal_eval(element.values["operations"])
                except (ValueError, SyntaxError, KeyError):
                    operations = None

                if element.image is not None:
                    try:
                        dpi = element.image.info["dpi"]
                    except KeyError:
                        dpi = None
                    _dpi = 500
                    if (
                        isinstance(dpi, tuple)
                        and len(dpi) >= 2
                        and dpi[0] != 0
                        and dpi[1] != 0
                    ):
                        _dpi = round((float(dpi[0]) + float(dpi[1])) / 2, 0)
                    _overscan = None
                    try:
                        _overscan = str(element.values.get("overscan"))
                    except (ValueError, TypeError):
                        pass
                    _direction = None
                    try:
                        _direction = int(element.values.get("direction"))
                    except (ValueError, TypeError):
                        pass
                    _invert = None
                    try:
                        _invert = bool(element.values.get("invert") == "True")
                    except (ValueError, TypeError):
                        pass
                    _dither = None
                    try:
                        _dither = bool(element.values.get("dither") == "True")
                    except (ValueError, TypeError):
                        pass
                    _dither_type = None
                    try:
                        _dither_type = element.values.get("dither_type")
                    except (ValueError, TypeError):
                        pass
                    _red = None
                    try:
                        _red = float(element.values.get("red"))
                    except (ValueError, TypeError):
                        pass
                    _green = None
                    try:
                        _green = float(element.values.get("green"))
                    except (ValueError, TypeError):
                        pass
                    _blue = None
                    try:
                        _blue = float(element.values.get("blue"))
                    except (ValueError, TypeError):
                        pass
                    _lightness = None
                    try:
                        _lightness = float(element.values.get("lightness"))
                    except (ValueError, TypeError):
                        pass
                    node = context_node.add(
                        image=element.image,
                        matrix=element.transform,
                        type="elem image",
                        id=ident,
                        overscan=_overscan,
                        direction=_direction,
                        dpi=_dpi,
                        invert=_invert,
                        dither=_dither,
                        dither_type=_dither_type,
                        red=_red,
                        green=_green,
                        blue=_blue,
                        lightness=_lightness,
                        label=_label,
                        operations=operations,
                        lock=_lock,
                    )
                    e_list.append(node)
            except OSError:
                pass
        elif isinstance(element, SVG):
            # SVG is type of group, must go first
            if self.reverse:
                for child in reversed(element):
                    self.parse(child, context_node, e_list)
            else:
                for child in element:
                    self.parse(child, context_node, e_list)
        elif isinstance(element, Group):
            if _label == "regmarks" or ident == "regmarks":
                # We don't need a top-level group here, the regmarks node is a kind of a group...
                context_node = self.regmark
                e_list = self.regmark_list
            else:
                context_node = context_node.add(type="group", id=ident, label=_label)
            # recurse to children
            if self.reverse:
                for child in reversed(element):
                    self.parse(child, context_node, e_list)
            else:
                for child in element:
                    self.parse(child, context_node, e_list)
        elif isinstance(element, Use):
            # recurse to children, but do not subgroup elements.
            # We still use the original label

            if self.reverse:
                for child in reversed(element):
                    self.parse(child, context_node, e_list, uselabel=_label)
            else:
                for child in element:
                    self.parse(child, context_node, e_list, uselabel=_label)
        else:
            # SVGElement is type. Generic or unknown node type.
            # Fix: we have mixed capitalisaton in full_ns and tag --> adjust
            tag = element.values.get(SVG_ATTR_TAG).lower()
            if tag is not None:
                # We remove the name space.
                full_ns = f"{{{MEERK40T_NAMESPACE.lower()}}}"
                if full_ns in tag:
                    tag = tag.replace(full_ns, "")
            # Check if note-type
            if tag == "note":
                self.elements.note = element.values.get(SVG_TAG_TEXT)
                self.elements.signal("note", self.pathname)
                return
            node_type = element.values.get("type")
            if node_type == "op":
                # Meerk40t 0.7.x fallback node types.
                op_type = element.values.get("operation")
                if op_type is None:
                    return
                node_type = f"op {op_type.lower()}"
                element.values["attributes"]["type"] = node_type

            if node_type is None:
                # Type is not given. Abort.
                return

            node_id = element.values.get("id")
            try:
                attrs = element.values["attributes"]
            except KeyError:
                attrs = element.values
            try:
                del attrs["type"]
            except KeyError:
                pass
            if "lock" in attrs:
                attrs["lock"] = _lock
            if "transform" in element.values:
                # Uses chained transforms from primary context.
                attrs["matrix"] = Matrix(element.values["transform"])
            if "fill" in attrs:
                attrs["fill"] = Color(attrs["fill"])
            if "stroke" in attrs:
                attrs["stroke"] = Color(attrs["stroke"])

            if tag == "operation":
                # Check if SVGElement: operation
                if not self.operations_cleared:
                    self.elements.clear_operations()
                    self.operations_cleared = True
                try:
                    node = self.elements.op_branch.create(type=node_type, **attrs)
                    if hasattr(node, "validate"):
                        node.validate()
                    node.id = node_id
                    op = self.elements.op_branch.add_node(node)
                    overlooked_attributes = [
                        "output",
                    ]
                    # Sometimes certain attributes weren't assigned properly / missed
                    # This piece of code tries to reapply them. If things were fine
                    # then this is an unneeded attempt. But better safe than sorry
                    for overlooked in overlooked_attributes:
                        if overlooked in element.values and hasattr(op, overlooked):
                            setattr(op, overlooked, element.values.get(overlooked))
                except AttributeError:
                    # This operation is invalid.
                    print (f"Error happened for {node_type}")
                    return
            elif tag == "element":
                # Check if SVGElement: element
                if "settings" in attrs:
                    del attrs[
                        "settings"
                    ]  # If settings was set, delete it or it will mess things up
                elem = context_node.add(type=node_type, **attrs)
                try:
                    elem.validate()
                except AttributeError:
                    pass
                elem.id = node_id
                e_list.append(elem)


class SVGLoader:
    @staticmethod
    def load_types():
        yield "Scalable Vector Graphics", ("svg", "svgz"), "image/svg+xml"

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):
        if "svg_ppi" in kwargs:
            ppi = float(kwargs["svg_ppi"])
        else:
            ppi = DEFAULT_PPI
        if ppi == 0:
            ppi = DEFAULT_PPI
        scale_factor = NATIVE_UNIT_PER_INCH / ppi
        source = pathname
        if pathname.lower().endswith("svgz"):
            source = gzip.open(pathname, "rb")
        try:
            if context.elements.svg_viewport_bed:
                width = context.device.length_width.length_mm
                height = context.device.length_height.length_mm
            else:
                width = None
                height = None
            # The color attribute of SVG.parse decides which default color
            # a stroke / fill will get if the attribute "currentColor" is
            # set - we opt for "black"
            svg = SVG.parse(
                source=source,
                reify=False,
                width=width,
                height=height,
                ppi=ppi,
                color="black",
                transform=f"scale({scale_factor})",
            )
        except ParseError as e:
            raise BadFileError(str(e)) from e
        svg_processor = SVGProcessor(elements_service)
        svg_processor.process(svg, pathname)
        return True
