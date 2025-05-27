"""
This extension governs SVG loading and saving, registering both the load and the save values for SVG.
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
from .units import DEFAULT_PPI, NATIVE_UNIT_PER_INCH, Length

SVG_ATTR_STROKE_JOIN = "stroke-linejoin"
SVG_ATTR_STROKE_CAP = "stroke-linecap"
SVG_ATTR_FILL_RULE = "fill-rule"
SVG_ATTR_STROKE_DASH = "stroke-dasharray"


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
            {
                "attr": "load_hidden_to_regmarks",
                "object": kernel.elements,
                "default": True,
                "type": bool,
                "label": _("Load hidden objects to regmarks"),
                "tip": _(
                    "Ticked: When loading a file invisible elements will be loaded to the regmarks branch."
                )
                + "\n"
                + _(
                    "Unticked: Invisible elements will be loaded as regular elements and will be hidden."
                ),
                "page": "Input/Output",
                "section": "Input",
            },
        ]
        kernel.register_choices("preferences", choices)
        # The order is relevant as both loaders support SVG
        # By definition the very first matching loader is used as a default
        # so that needs to be the full loader
        kernel.register("load/SVGLoader", SVGLoader)
        kernel.register("load/SVGPlainLoader", SVGLoaderPlain)
        kernel.register("save/SVGWriter", SVGWriter)


MEERK40T_NAMESPACE = "https://github.com/meerk40t/meerk40t/wiki/Namespace"
MEERK40T_XMLS_ID = "meerk40t"


def capstr(linecap):
    """
    Given the mk enum values for linecap, returns the svg string.
    @param linecap:
    @return:
    """
    if linecap == Linecap.CAP_BUTT:
        return "butt"
    elif linecap == Linecap.CAP_SQUARE:
        return "square"
    else:
        return "round"


def joinstr(linejoin):
    """
    Given the mk enum value for linejoin, returns the svg string.

    @param linejoin:
    @return:
    """
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
    """
    Given the mk enum value for fillrule, returns the svg string.

    @param fillrule:
    @return:
    """
    return "evenodd" if fillrule == Fillrule.FILLRULE_EVENODD else "nonzero"


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
        scene_width = Length(context.device.view.width)
        scene_height = Length(context.device.view.height)
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
                subelement.set(SVG_TAG_TEXT, str(elements.note))
            if elements.last_file_autoexec is not None:
                subelement = SubElement(root, "autoexec")
                subelement.set("autoexec", str(elements.last_file_autoexec))
                subelement.set(
                    "autoexec-active", str(elements.last_file_autoexec_active)
                )

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
        for c in elem_tree.children:
            SVGWriter._write_element(xml_tree, c, version)

    @staticmethod
    def _write_element(xml_tree, c, version):
        def single_file_node():
            # do we have more than one element on the top level hierarchy?
            # If no then return True
            flag = True
            if len(c.children) > 1:
                flag = False
            return flag

        if c.type == "elem ellipse":
            subelement = SubElement(xml_tree, SVG_TAG_ELLIPSE)
            subelement.set(SVG_ATTR_CENTER_X, str(c.cx))
            subelement.set(SVG_ATTR_CENTER_Y, str(c.cy))
            subelement.set(SVG_ATTR_RADIUS_X, str(c.rx))
            subelement.set(SVG_ATTR_RADIUS_Y, str(c.ry))
            t = Matrix(c.matrix)
            if not t.is_identity():
                subelement.set(
                    "transform",
                    f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                )
        elif c.type in ("elem image", "image raster"):
            subelement = SubElement(xml_tree, SVG_TAG_IMAGE)
            stream = BytesIO()
            try:
                c.image.save(stream, format="PNG", dpi=(c.dpi, c.dpi))
            except OSError:
                # Edge condition if the original image was CMYK and never touched it can't encode to PNG
                c.image.convert("RGBA").save(stream, format="PNG", dpi=(c.dpi, c.dpi))
            subelement.set(
                "xlink:href",
                f"data:image/png;base64,{b64encode(stream.getvalue()).decode('utf8')}",
            )
            ref = c.keyhole_reference
            if ref is not None:
                subelement.set("keyhole_reference", ref)
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
            subelement = SubElement(xml_tree, SVG_TAG_LINE)
            subelement.set(SVG_ATTR_X1, str(c.x1))
            subelement.set(SVG_ATTR_Y1, str(c.y1))
            subelement.set(SVG_ATTR_X2, str(c.x2))
            subelement.set(SVG_ATTR_Y2, str(c.y2))
            t = c.matrix
            if not t.is_identity():
                subelement.set(
                    "transform",
                    f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                )
        elif c.type == "elem path":
            element = c.geometry.as_path()
            subelement = SubElement(xml_tree, SVG_TAG_PATH)
            subelement.set(SVG_ATTR_DATA, element.d(transformed=False))
            t = c.matrix
            if not t.is_identity():
                subelement.set(
                    "transform",
                    f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                )
        elif c.type == "elem point":
            subelement = SubElement(xml_tree, "element")
            t = c.matrix
            if not t.is_identity():
                subelement.set(
                    "transform",
                    f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                )
            subelement.set("x", str(c.x))
            subelement.set("y", str(c.y))
        elif c.type == "elem polyline":
            subelement = SubElement(xml_tree, SVG_TAG_POLYLINE)
            points = list(c.geometry.as_points())
            subelement.set(
                SVG_ATTR_POINTS,
                " ".join([f"{e.real} {e.imag}" for e in points]),
            )
            t = c.matrix
            if not t.is_identity():
                subelement.set(
                    "transform",
                    f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                )
        elif c.type == "elem rect":
            subelement = SubElement(xml_tree, SVG_TAG_RECT)
            subelement.set(SVG_ATTR_X, str(c.x))
            subelement.set(SVG_ATTR_Y, str(c.y))
            subelement.set(SVG_ATTR_RADIUS_X, str(c.rx))
            subelement.set(SVG_ATTR_RADIUS_Y, str(c.ry))
            subelement.set(SVG_ATTR_WIDTH, str(c.width))
            subelement.set(SVG_ATTR_HEIGHT, str(c.height))
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
                subelement.set(SVG_ATTR_FONT_FAMILY, str(c.font_family))
            if c.font_style:
                subelement.set(SVG_ATTR_FONT_STYLE, str(c.font_style))
            if c.font_variant:
                subelement.set(SVG_ATTR_FONT_VARIANT, str(c.font_variant))
            if c.font_stretch:
                subelement.set(SVG_ATTR_FONT_STRETCH, str(c.font_stretch))
            if c.font_size:
                subelement.set(SVG_ATTR_FONT_SIZE, str(c.font_size))
            if c.line_height:
                subelement.set("line_height", str(c.line_height))
            if c.anchor:
                subelement.set(SVG_ATTR_TEXT_ANCHOR, str(c.anchor))
            if c.baseline:
                subelement.set(SVG_ATTR_TEXT_DOMINANT_BASELINE, str(c.baseline))
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
        elif c.type == "group":
            # This is a structural group node of elements. Recurse call to write values.
            group_element = SubElement(xml_tree, SVG_TAG_GROUP)
            if hasattr(c, "label") and c.label is not None and c.label != "":
                group_element.set("inkscape:label", str(c.label))
            if hasattr(c, "label_display") and c.label_display is not None:
                group_element.set("label_display", str(c.label_display))
            SVGWriter._write_elements(group_element, c, version)
            return
        elif c.type.startswith("effect"):
            # This is a structural group node of elements. Recurse call to write values.
            group_element = SubElement(xml_tree, SVG_TAG_GROUP)
            SVGWriter._write_custom(group_element, c)
            SVGWriter._write_elements(group_element, c, version)
            return
        elif c.type == "file":
            # This is a structural group node of elements. Recurse call to write values.
            # is this the only file node? If yes then no need to generate an additional group
            if single_file_node():
                SVGWriter._write_elements(xml_tree, c, version)
            else:
                group_element = SubElement(xml_tree, SVG_TAG_GROUP)
                if hasattr(c, "name") and c.name is not None and c.name != "":
                    group_element.set("inkscape:label", str(c.name))
                SVGWriter._write_elements(group_element, c, version)
            return
        else:
            if version == "plain":
                # Plain does not save custom.
                return
            # This is a non-standard element. Save custom.
            subelement = SubElement(xml_tree, "element")
            SVGWriter._write_custom(subelement, c)
            return

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
                    "stroke_dash",
                )
                and value is not None
                and isinstance(value, (str, int, float, complex, list, tuple, dict))
            ):
                subelement.set(key, str(value))

        # ###########################
        # # SAVE SVG STROKE-SCALING
        # ###########################
        # if hasattr(c, "stroke_scaled"):
        #     if not c.stroke_scaled:
        #         subelement.set(SVG_ATTR_VECTOR_EFFECT, SVG_VALUE_NON_SCALING_STROKE)

        ###############
        # SAVE CAP/JOIN/FILL-RULE
        ###############
        if hasattr(c, "linecap"):
            subelement.set(SVG_ATTR_STROKE_CAP, capstr(c.linecap))
        if hasattr(c, "linejoin"):
            subelement.set(SVG_ATTR_STROKE_JOIN, joinstr(c.linejoin))
        if hasattr(c, "fillrule"):
            subelement.set(SVG_ATTR_FILL_RULE, rulestr(c.fillrule))
        if hasattr(c, "stroke_dash") and c.stroke_dash:
            subelement.set(SVG_ATTR_STROKE_DASH, c.stroke_dash)

        ###############
        # SAVE LABEL
        ###############
        if hasattr(c, "label") and c.label is not None and c.label != "":
            subelement.set("inkscape:label", c.label)

        ###############
        # SAVE STROKE
        ###############
        stroke = c.stroke if hasattr(c, "stroke") else None
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
                if c.stroke_width is not None:
                    stroke_width = str(factor * c.stroke_width / c_m_d)
                    subelement.set(SVG_ATTR_STROKE_WIDTH, stroke_width)
            except AttributeError:
                pass

        ###############
        # SAVE FILL
        ###############
        fill = c.fill if hasattr(c, "fill") else None
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

        if hasattr(c, "hidden") and c.hidden:
            subelement.set("visibility", "hidden")

        subelement.set(SVG_ATTR_ID, str(c.id))
        if hasattr(c, "bounds"):
            bb = c.bounds
            bbstr = f"{bb[0]}, {bb[1]}, {bb[2]}, {bb[3]}"
            subelement.set("bounds", bbstr)
        if hasattr(c, "paint_bounds"):
            bb = c.paint_bounds
            bbstr = f"{bb[0]}, {bb[1]}, {bb[2]}, {bb[3]}"
            subelement.set("paint_bounds", bbstr)

    @staticmethod
    def _write_operations(xml_tree, op_tree, version):
        """
        Write the operations branch part of the tree to disk.

        @param xml_tree:
        @param op_tree:
        @return:
        """
        for c in op_tree.children:
            SVGWriter._write_operation(xml_tree, c, version)

    @staticmethod
    def _write_regmarks(xml_tree, reg_tree, version):
        if len(reg_tree.children):
            regmark = SubElement(xml_tree, SVG_TAG_GROUP)
            regmark.set("id", "regmarks")
            regmark.set("visibility", "hidden")
            SVGWriter._write_elements(regmark, reg_tree, version)

    @staticmethod
    def _write_operation(xml_tree, node, version):
        """
        Write an individual operation. This is any node directly under `branch ops`

        @param xml_tree:
        @param node:
        @return:
        """
        # All operations are groups.
        subelement = SubElement(xml_tree, SVG_TAG_GROUP)
        subelement.set("type", str(node.type))

        if node.label is not None:
            subelement.set("label", str(node.label))

        # We might end up with items in settings that have an unwanted equivalent in the node.dict
        # as the settings instance is read and initiated on svg load...
        for key, value in node.__dict__.items():
            if not key or key.startswith("_"):
                continue
            if key in (
                "references",
                "tag",
                "type",
                "draw",
                "stroke_width",
                "matrix",
                "settings",
            ):
                continue
            if hasattr(node, "settings"):
                if key in node.settings:
                    settings_value = node.settings[key]
                    if settings_value != value:
                        # print (f"Needed to fix {key}: node-value: {value}, settings-value: {settings_value}")
                        node.settings[key] = value

        saved_attributes = []
        if hasattr(node, "settings"):
            try:
                for key, value in node.settings.items():
                    saved_attributes.append(key)
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
        # Node does not have settings, write object dict
        for key, value in node.__dict__.items():
            if (
                not key
                or key.startswith("_")
                or key in saved_attributes
                or value is None
            ):
                continue
            if key in (
                "references",
                "tag",
                "type",
                "draw",
                "stroke_width",
                "matrix",
                "settings",
            ):
                # References key from previous loaded version (filter out, rebuild)
                continue
            subelement.set(key, str(value))

        # Store current node reference values.
        SVGWriter._write_references(subelement, node)
        subelement.set(SVG_ATTR_ID, str(node.id))

        for c in node.children:
            # Recurse all non-ref nodes
            if c.type == "reference":
                continue
            SVGWriter._write_operation(subelement, c, version)

    @staticmethod
    def _write_references(subelement, node):
        contains = list()
        for c in node.children:
            if c.type == "reference":
                c = c.node  # Contain direct reference not reference node reference.
                if c.id is not None:  # Something strange happened here...
                    contains.append(c.id)
        if contains:
            subelement.set("references", " ".join(contains))

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
        SVGWriter._write_references(subelement, node)
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
    """
    SVGProcessor is the parser for svg objects. We employ svgelements to do the actual parsing of the file and convert
    the parsed objects into mk nodes, operations, elements, and regmarks.

    Special care is taken to load MK specific objects like `note` and `operations`
    """

    def __init__(
        self,
        elements,
        load_operations,
        load_hidden_to_regmarks=True,
        reuse_operations=True,
    ):
        self.elements = elements

        self.operation_list = list()
        self.element_list = list()
        self.regmark_list = list()
        self.load_hidden_to_regmarks = load_hidden_to_regmarks

        self.reverse = False
        self.requires_classification = True
        self.operations_generated = False
        self.pathname = None
        self.load_operations = load_operations
        self.reuse_operations = reuse_operations
        self.mk_params = list(
            self.elements.kernel.lookup_all("registered_mk_svg_parameters")
        )
        # Append barcode from external plugin
        self.mk_params.append("mkbcparam")

        # Setting this is bringing as much benefit as anticipated
        # Both the time to load the file (unexpectedly) and the time
        # for the first emphasis when all the nonpopulated bounding
        # boxes will be calculated are benefiting from this precalculation:
        # (All values as average over three consecutive loads)
        #                    |           Load             |       First Select
        # File               |   Old  | Precalc | Speedup |  Old   | Precalc | Speedup
        # Star Wars Calendar |  10,3  |   4,8   |  115%   |  3,4   |   1,0   | 243%
        # Element Classific  |   1,7  |   1,1   |   59%   |  0,6   |   0,4   |  54%
        # Egyptian Bark      |  72,1  |  43,9   |   64%   | 34,6   |  20,1   |  72%
        self.precalc_bbox = True

    def process(self, svg, pathname):
        """
        Process sends the data to parse and deals with creating the file_node, setting the operations, classifying
        either directly from the data within the file or automatically.

        @param svg:
        @param pathname:
        @return:
        """
        retain_op_list = [
            child
            for child in list(self.elements.ops())
            if child._children is not None and len(child._children) > 0
        ]
        self.pathname = pathname

        context_node = self.elements.elem_branch
        file_node = context_node.add(type="file", filepath=pathname)
        file_node.focus()

        self.parse(svg, file_node, self.element_list, branch="elements")

        if self.load_operations and self.operations_generated:
            # print ("Will replace all operations...")
            self.requires_classification = False
            for child in list(self.elements.op_branch.children):
                if child in retain_op_list:
                    continue
                if not hasattr(child, "_ref_load"):
                    child.remove_all_children(fast=True, destroy=True)
                    child.remove_node(fast=True, destroy=True)
            # Hint for translate check: _("File loaded")
            self.elements.undo.mark("File loaded")
            for op in self.elements.op_branch.flat():
                try:
                    refs = op._ref_load
                    del op._ref_load
                except AttributeError:
                    continue
                if refs is None:
                    continue

                for ref in refs.split(" "):
                    for e in self.element_list:
                        if e.id == ref:
                            op.add_reference(e)

        if self.requires_classification and self.elements.classify_new:
            self.elements.classify(self.element_list)

    def check_for_bound_information(self, node, element):
        # Do we have existing boundary information?
        if "bounds" not in element.values:
            return False
        bbstr = element.values["bounds"]
        if not bbstr:
            return False
        bb_info = bbstr.split(",")
        if len(bb_info) == 4:
            bbox = [0, 0, 0, 0]
            try:
                for idx in range(4):
                    val = float(bb_info[idx])
                    bbox[idx] = val
            except ValueError:
                return False
            node._bounds = list(bbox)
            node._bounds_dirty = False
            if "paint_bounds" in element.values:
                try:
                    bbstr = element.values["paint_bounds"]
                    bb_info = bbstr.split(",")
                    if len(bb_info) == 4:
                        for idx in range(4):
                            val = float(bb_info[idx])
                            bbox[idx] = val
                except Exception:
                    # Whatever it was, we don't continue...
                    pass
            node._paint_bounds = list(bbox)
            node._paint_bounds_dirty = False
            return True

    def check_for_mk_path_attributes(self, node, element, skip=None):
        """
        Checks for some mk special parameters starting with mk. Especially mkparam, and uses this property to fill in
        the functional_parameter attribute for the node. This can be skipped if needed (eg. for basic shapes) as this
        is not needed for them.

        @param node:
        @param element:
        @return:
        """
        for prop in element.values:
            lc = element.values.get(prop)
            if prop.startswith("mk"):
                if skip and prop in skip:
                    continue
                if lc is not None:
                    setattr(node, prop, lc)
                    # This needs to be done as some node types are not based on Parameters
                    # and hence would not convert the stringified tuple
                    if prop == "mkparam" and hasattr(node, "functional_parameter"):
                        try:
                            value = ast.literal_eval(lc)
                            node.functional_parameter = value
                        except (ValueError, SyntaxError):
                            pass
                    elif prop in self.mk_params:
                        try:
                            value = ast.literal_eval(lc)
                            setattr(node, prop, value)
                        except (ValueError, SyntaxError):
                            pass

    def check_for_label_display(self, node, element):
        """
        Called for all nodes to check whether the label_display needs to be set
        @param node:
        @param element:
        @return:
        """
        lc = element.values.get("label_display")
        if lc is not None and hasattr(node, "label_display"):
            d_val = bool(ast.literal_eval(lc))
            node.label_display = d_val

    def check_for_fill_attributes(self, node, element):
        """
        Called for paths and poly lines. This checks for an attribute of `fill-rule` in the SVG and sets the MK equal.

        @param node:
        @param element:
        @return:
        """
        lc = element.values.get(SVG_ATTR_FILL_RULE)
        # SVG default is nonzero
        nlc = Fillrule.FILLRULE_NONZERO
        if lc is not None:
            lc = lc.lower()
            if lc == SVG_RULE_EVENODD:
                nlc = Fillrule.FILLRULE_EVENODD
            elif lc == SVG_RULE_NONZERO:
                nlc = Fillrule.FILLRULE_NONZERO
        node.fillrule = nlc

    def check_for_line_attributes(self, node, element):
        """
        Called for many element types. This checks for the stroke-cap and line-join attributes in the svgelements
        primitive and sets the node with the mk equal

        @param node:
        @param element:
        @return:
        """
        lc = element.values.get(SVG_ATTR_STROKE_CAP)
        # SVG default is butt
        nlc = Linecap.CAP_BUTT
        if lc is not None:
            if lc == "butt":
                nlc = Linecap.CAP_BUTT
            elif lc == "round":
                nlc = Linecap.CAP_ROUND
            elif lc == "square":
                nlc = Linecap.CAP_SQUARE
        node.linecap = nlc
        lj = element.values.get(SVG_ATTR_STROKE_JOIN)
        # SVG default is miter
        nlj = Linejoin.JOIN_MITER
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
        lj = element.values.get(SVG_ATTR_STROKE_DASH)
        if lj not in (None, "", "none"):
            node.stroke_dash = lj

    @staticmethod
    def is_dot(element):
        """
        Check for the degenerate shape dots. This could be a Path that consisting of a Move + Close, Move, or Move any
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

    def get_tag_label(self, element):
        """
        Gets the tag label from the element. This is usually an inkscape label.

        Let's see whether we can get the label from an inkscape save
        We only want the 'label' attribute from the current tag, so
        we look at element.values["attributes"]

        @param element:
        @return:
        """

        if "attributes" in element.values:
            local_dict = element.values["attributes"]
        else:
            local_dict = element.values
        if local_dict is None:
            return None
        ink_tag = "inkscape:label"
        inkscape = element.values.get("inkscape")
        if inkscape:
            ink_tag = "{" + inkscape + "}label"
        tag_label = local_dict.get(ink_tag)
        if tag_label:
            return tag_label
        return local_dict.get("label")

    def _parse_text(
        self, element, ident, label, lock, context_node, e_list, set_hidden
    ):
        """
        Parses an SVGText object, into an `elem text` node.

        @param element:
        @param ident:
        @param label:
        @param lock:
        @param context_node:
        @param e_list:
        @return:
        """

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
            label=label,
            settings=element.values,
            hidden=set_hidden,
        )
        self.check_for_label_display(node, element)
        self.check_for_bound_information(node, element)
        e_list.append(node)

    def _parse_path(
        self, element, ident, label, lock, context_node, e_list, set_hidden
    ):
        """
        Parses an SVG Path object.

        There were a few versions of meerk40t where Path was used to store other save nodes. But, there is not
        enough information to reconstruct those elements.

        @param element:
        @param ident:
        @param label:
        @param lock:
        @param context_node:
        @param e_list:
        @return:
        """
        if len(element) < 0:
            return

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
            path=element,
            type="elem path",
            id=ident,
            label=label,
            lock=lock,
            hidden=set_hidden,
        )
        self.check_for_label_display(node, element)
        self.check_for_line_attributes(node, element)
        self.check_for_fill_attributes(node, element)
        self.check_for_mk_path_attributes(node, element)
        self.check_for_bound_information(node, element)
        e_list.append(node)

    def _parse_polyline(
        self, element, ident, label, lock, context_node, e_list, set_hidden
    ):
        """
        Parses svg Polyline and Polygon objects into `elem polyline` nodes.

        @param element:
        @param ident:
        @param label:
        @param lock:
        @param context_node:
        @param e_list:
        @return:
        """
        if element.is_degenerate():
            return
        node = context_node.add(
            shape=element,
            type="elem polyline",
            id=ident,
            label=label,
            lock=lock,
            hidden=set_hidden,
        )
        self.check_for_label_display(node, element)
        self.check_for_line_attributes(node, element)
        self.check_for_fill_attributes(node, element)
        self.check_for_mk_path_attributes(node, element, skip=("mkparam",))
        if not self.check_for_bound_information(node, element) and self.precalc_bbox:
            # bounds will be done here, paintbounds won't...
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

    def _parse_ellipse(
        self, element, ident, label, lock, context_node, e_list, set_hidden
    ):
        """
        Parses the SVG Circle, and Ellipse nodes into `elem ellipse` nodes.

        @param element:
        @param ident:
        @param label:
        @param lock:
        @param context_node:
        @param e_list:
        @return:
        """
        if element.is_degenerate():
            return
        node = context_node.add(
            shape=element,
            type="elem ellipse",
            id=ident,
            label=label,
            lock=lock,
            hidden=set_hidden,
        )
        self.check_for_label_display(node, element)
        self.check_for_line_attributes(node, element)
        self.check_for_mk_path_attributes(node, element, skip=("mkparam",))
        self.check_for_bound_information(node, element)
        e_list.append(node)

    def _parse_rect(
        self, element, ident, label, lock, context_node, e_list, set_hidden
    ):
        """
        Parse SVG Rect objects into `elem rect` objects.

        @param element:
        @param ident:
        @param label:
        @param lock:
        @param context_node:
        @param e_list:
        @return:
        """
        if element.is_degenerate():
            return
        node = context_node.add(
            shape=element,
            type="elem rect",
            id=ident,
            label=label,
            lock=lock,
            hidden=set_hidden,
        )
        self.check_for_label_display(node, element)
        self.check_for_line_attributes(node, element)
        self.check_for_mk_path_attributes(node, element, skip=("mkparam",))
        if not self.check_for_bound_information(node, element) and self.precalc_bbox:
            # bounds will be done here, paintbounds won't...
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

    def _parse_line(
        self, element, ident, label, lock, context_node, e_list, set_hidden
    ):
        """
        Parse SVG Line objects into `elem line`

        @param element:
        @param ident:
        @param label:
        @param lock:
        @param context_node:
        @param e_list:
        @return:
        """
        if element.is_degenerate():
            return
        node = context_node.add(
            shape=element,
            type="elem line",
            id=ident,
            label=label,
            lock=lock,
            hidden=set_hidden,
        )
        self.check_for_label_display(node, element)
        self.check_for_line_attributes(node, element)
        self.check_for_mk_path_attributes(node, element, skip=("mkparam",))
        if not self.check_for_bound_information(node, element) and self.precalc_bbox:
            # bounds will be done here, paintbounds won't...
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

    def _parse_image(
        self, element, ident, label, lock, context_node, e_list, set_hidden
    ):
        """
        Parse SVG Image objects into either `image raster` or `elem image` objects, potentially other classes.

        @param element:
        @param ident:
        @param label:
        @param lock:
        @param context_node:
        @param e_list:
        @return:
        """
        try:
            element.load(os.path.dirname(self.pathname))
            if element.image is not None:
                try:
                    from PIL import ImageOps

                    element.image = ImageOps.exif_transpose(element.image)
                except ImportError:
                    pass
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
                _keyhole = None
                try:
                    _keyhole = element.values.get("keyhole_reference")
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
                _is_depthmap = False
                try:
                    _is_depthmap = bool(element.values.get("is_depthmap") == "True")
                except (ValueError, TypeError):
                    pass
                _depth_resolution = 256
                try:
                    _depth_resolution = int(element.values.get("depth_resolution"))
                    if _depth_resolution <= 1 or _depth_resolution > 256:
                        _depth_resolution = 256
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
                    label=label,
                    operations=operations,
                    lock=lock,
                    is_depthmap=_is_depthmap,
                    depth_resolution=_depth_resolution,
                    keyhole_reference=_keyhole,
                    hidden=set_hidden,
                )
                self.check_for_label_display(node, element)
                self.check_for_bound_information(node, element)
                e_list.append(node)
        except OSError:
            pass

    def _parse_element(self, element, ident, label, lock, context_node, e_list):
        """
        SVGElement is type. Generic or unknown node type. These nodes do not have children, these are used in
        meerk40t contain notes and operations. Element type="elem point", and other points will also load with
        this code.

        @param element:
        @param ident:
        @param label:
        @param lock:
        @param context_node:
        @param e_list:
        @return:
        """

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

        # Check if note-type
        if tag == "autoexec":
            self.elements.last_file_autoexec = element.values.get("autoexec")
            s = element.values.get("autoexec-active")
            self.elements.last_file_autoexec_active = bool(s in ("1", "True"))
            self.elements.signal("autoexec", self.pathname)
            return

        node_type = element.values.get("type")
        if node_type is None:
            # Type is not given. Abort.
            return

        if node_type == "op":
            # Meerk40t 0.7.x fallback node types.
            op_type = element.values.get("operation")
            if op_type is None:
                return
            node_type = f"op {op_type.lower()}"
            element.values["attributes"]["type"] = node_type

        node_id = element.values.get("id")

        # Get node dictionary.
        try:
            attrs = element.values["attributes"]
        except KeyError:
            attrs = element.values

        # If type exists in the dictionary, delete it to avoid double attribute issues.
        try:
            del attrs["type"]
        except KeyError:
            pass

        # Set dictionary types with proper classes.
        if "lock" in attrs:
            attrs["lock"] = lock
        if "transform" in element.values:
            # Uses chained transforms from primary context.
            attrs["matrix"] = Matrix(element.values["transform"])
        if "fill" in attrs:
            attrs["fill"] = Color(attrs["fill"])
        if "stroke" in attrs:
            attrs["stroke"] = Color(attrs["stroke"])

        if tag == "operation":
            # Operation type node.
            if not self.load_operations:
                # We don't do that.
                return

            self.operations_generated = True

            try:
                if node_type == "op hatch":
                    # Special fallback operation, op hatch is an op engrave with an effect hatch within it.
                    node_type = "op engrave"
                    op = self.elements.op_branch.add(type=node_type, **attrs)
                    effect = op.add(type="effect hatch", **attrs)
                else:
                    op = self.elements.op_branch.add(type=node_type, **attrs)
                op._ref_load = element.values.get("references")

                if op is None or not hasattr(op, "type") or op.type is None:
                    return
                if hasattr(op, "validate"):
                    op.validate()

                op.id = node_id
                self.operation_list.append(op)
            except AttributeError:
                # This operation is invalid.
                return
            except ValueError:
                # This operation type failed to bootstrap.
                return

        elif tag == "element":
            # Check if SVGElement: element
            if "settings" in attrs:
                del attrs[
                    "settings"
                ]  # If settings was set, delete it, or it will mess things up
            elem = context_node.add(type=node_type, **attrs)
            # This could be an elem point
            self.check_for_label_display(elem, element)
            self.check_for_bound_information(elem, element)
            try:
                elem.validate()
            except AttributeError:
                pass
            elem.id = node_id
            e_list.append(elem)

    def parse(self, element, context_node, e_list, branch=None, uselabel=None):
        """
        Parse does the bulk of the work. Given an element, here the base case is an SVG itself, we parse such that
        any groups will call and check all children recursively, updating the context_node, and passing each element
        to this same function.


        @param element: Element to parse.
        @param context_node: Current context parent we're writing to.
        @param e_list: elements list of all the nodes added by this function.
        @param branch: Branch we are currently adding elements to.
        @param uselabel:
        @return:
        """
        set_hidden = False
        display = ""
        if "display" in element.values:
            display = element.values.get("display").lower()
            if display == "none":
                if branch not in ("elements", "regmarks"):
                    return
        if element.values.get("visibility") == "hidden" or display == "none":
            if self.load_hidden_to_regmarks:
                if branch != "regmarks":
                    self.parse(
                        element,
                        self.elements.reg_branch,
                        self.regmark_list,
                        branch="regmarks",
                    )
                    return
            else:
                set_hidden = True

        ident = element.id

        _label = uselabel if uselabel else self.get_tag_label(element)
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
                hidden=set_hidden,
            )
            self.check_for_label_display(node, element)
            self.check_for_bound_information(node, element)
            e_list.append(node)
        elif isinstance(element, SVGText):
            self._parse_text(
                element, ident, _label, _lock, context_node, e_list, set_hidden
            )
        elif isinstance(element, Path):
            self._parse_path(
                element, ident, _label, _lock, context_node, e_list, set_hidden
            )
        elif isinstance(element, (Polygon, Polyline)):
            self._parse_polyline(
                element, ident, _label, _lock, context_node, e_list, set_hidden
            )
        elif isinstance(element, (Circle, Ellipse)):
            self._parse_ellipse(
                element, ident, _label, _lock, context_node, e_list, set_hidden
            )
        elif isinstance(element, Rect):
            self._parse_rect(
                element, ident, _label, _lock, context_node, e_list, set_hidden
            )
        elif isinstance(element, SimpleLine):
            self._parse_line(
                element, ident, _label, _lock, context_node, e_list, set_hidden
            )
        elif isinstance(element, SVGImage):
            self._parse_image(
                element, ident, _label, _lock, context_node, e_list, set_hidden
            )
        elif isinstance(element, SVG):
            # SVG is type of group, it must be processed before Group. Nothing special is done with the type.
            if self.reverse:
                for child in reversed(element):
                    self.parse(child, context_node, e_list, branch=branch)
            else:
                for child in element:
                    self.parse(child, context_node, e_list, branch=branch)
        elif isinstance(element, Group):
            if branch != "regmarks" and (_label == "regmarks" or ident == "regmarks"):
                # Recurse at same level within regmarks.
                self.parse(
                    element,
                    self.elements.reg_branch,
                    self.regmark_list,
                    branch="regmarks",
                )
                return

            # Load group with specific group attributes (if needed)
            e_dict = dict(element.values["attributes"])
            e_type = e_dict.get("type", "group")
            if branch != "operations" and (
                e_type.startswith("op ")
                or e_type.startswith("place ")
                or e_type.startswith("util ")
            ):
                # This is an operations, but we are not in operations context.
                if not self.load_operations:
                    # We don't do that.
                    return
                self.operations_generated = True
                self.parse(
                    element,
                    self.elements.op_branch,
                    self.operation_list,
                    branch="operations",
                )
                return
            if "stroke" in e_dict:
                e_dict["stroke"] = Color(e_dict.get("stroke"))
            if "fill" in e_dict:
                e_dict["fill"] = Color(e_dict.get("fill"))
            for attr in ("type", "id", "label"):
                if attr in e_dict:
                    del e_dict[attr]

            #
            already = False
            if self.reuse_operations:
                # No need to create another operation, if we do
                # have an identical operation in place
                if e_type.startswith("op "):
                    # It needs to be non-empty to be used!
                    for testop in self.elements.ops():
                        if len(testop.children) == 0:
                            continue
                        if e_type != testop.type:
                            continue
                        differs = False
                        for check_attr, check_default in (
                            ("id", None),
                            ("power", "1000"),
                            ("speed", None),
                            ("passes", "0"),
                            ("color", None),
                        ):
                            if not hasattr(testop, check_attr):
                                if check_attr in e_dict:
                                    differs = True
                                    break
                                continue
                            test_val = getattr(testop, check_attr, check_default)
                            if test_val is None:
                                test_val = ""
                            else:
                                test_val = str(test_val)
                            if check_attr == "id":
                                eop_val = ident
                            else:
                                if check_attr not in e_dict:
                                    eop_val = check_default
                                else:
                                    eop_val = e_dict[check_attr]
                            if eop_val is None:
                                eop_val = ""
                            if test_val != eop_val:
                                differs = True
                                # print (f"{testop.type}.{check_attr}: {eop_val} != {test_val}")
                                break
                        if differs:
                            continue
                        context_node = testop
                        already = True
                        break

            if not already:
                context_node = context_node.add(
                    type=e_type, id=ident, label=_label, **e_dict
                )
                self.check_for_label_display(context_node, element)
                self.check_for_bound_information(context_node, element)
            context_node._ref_load = element.values.get("references")
            e_list.append(context_node)
            if hasattr(context_node, "validate"):
                context_node.validate()

            # recurse to children
            if self.reverse:
                for child in reversed(element):
                    self.parse(child, context_node, e_list, branch=branch)
            else:
                for child in element:
                    self.parse(child, context_node, e_list, branch=branch)
        elif isinstance(element, Use):
            # recurse to children, but do not subgroup elements.
            # We still use the original label
            if self.reverse:
                for child in reversed(element):
                    self.parse(
                        child, context_node, e_list, branch=branch, uselabel=_label
                    )
            else:
                for child in element:
                    self.parse(
                        child, context_node, e_list, branch=branch, uselabel=_label
                    )
        else:
            self._parse_element(element, ident, _label, _lock, context_node, e_list)

    def cleanup(self):
        # Make a couple of structural fixes that would be to cumbersome to integrate at parse level
        # 1) Fix regmark grouping.
        # Regmarks nodes are saved under a group with visibility=False set
        # So let's flatten this top group
        if len(self.regmark_list) > 0:
            # We need to add another filenode under regmarks and move all elements to it
            context_node = self.elements.reg_branch
            file_node = context_node.add(type="file", filepath=self.pathname)
            for node in self.regmark_list:
                if node._parent is context_node:
                    if node.type == "group" and (
                        node.id == "regmarks" or node.label == "regmarks"
                    ):
                        for n in list(node.children):
                            file_node.append_child(n)
                        node.remove_node()  # Removing group/file node.
                    else:
                        file_node.append_child(node)

        regmark = self.elements.reg_branch
        for c in regmark.children:
            if c.type == "group" and (c.id == "regmarks" or c.label == "regmarks"):
                for n in list(c.children):
                    c.insert_sibling(n)
                c.remove_node()  # Removing group/file node.

        needs_update = False
        for c in self.elements.flat():
            # All nodes including regmarks and elements
            if c.type == "elem image" and c.keyhole_reference is not None:
                refnode = self.elements.find_node(c.keyhole_reference)
                if refnode is None or not hasattr(refnode, "as_geometry"):
                    # Invalid -> remove
                    c.keyhole_reference = None
                else:
                    try:
                        self.elements.register_keyhole(refnode, c)
                        needs_update = True
                    except ValueError as e:
                        c.keyhole_reference = None

        if needs_update:
            self.elements.process_keyhole_updates(None)


class SVGLoader:
    """
    SVG loader - loading elements, regmarks and operations
    """

    @staticmethod
    def load_types():
        yield "Scalable Vector Graphics", ("svg", "svgz"), "image/svg+xml"

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):
        ppi = float(kwargs["svg_ppi"]) if "svg_ppi" in kwargs else DEFAULT_PPI
        if ppi == 0:
            ppi = DEFAULT_PPI
        scale_factor = NATIVE_UNIT_PER_INCH / ppi
        source = pathname
        if pathname.lower().endswith("svgz"):
            source = gzip.open(pathname, "rb")
        try:
            if context.elements.svg_viewport_bed:
                width = Length(amount=context.device.view.unit_width).length_mm
                height = Length(amount=context.device.view.unit_height).length_mm
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
                parse_display_none=True,
                transform=f"scale({scale_factor})",
            )
        except ParseError as e:
            raise BadFileError(str(e)) from e
        reuse = elements_service.reuse_operations_on_load
        to_regmarks = elements_service.load_hidden_to_regmarks
        elements_service._loading_cleared = True
        svg_processor = SVGProcessor(
            elements_service,
            load_operations=True,
            reuse_operations=reuse,
            load_hidden_to_regmarks=to_regmarks,
        )
        svg_processor.process(svg, pathname)
        svg_processor.cleanup()
        return True


class SVGLoaderPlain:
    """
    SVG loader but without loading the operations branch
    """

    @staticmethod
    def load_types():
        yield "SVG (elements only)", ("svg", "svgz"), "image/svg+xml"

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):
        ppi = float(kwargs["svg_ppi"]) if "svg_ppi" in kwargs else DEFAULT_PPI
        if ppi == 0:
            ppi = DEFAULT_PPI
        scale_factor = NATIVE_UNIT_PER_INCH / ppi
        source = pathname
        if pathname.lower().endswith("svgz"):
            source = gzip.open(pathname, "rb")
        try:
            if context.elements.svg_viewport_bed:
                width = Length(amount=context.device.view.unit_width).length_mm
                height = Length(amount=context.device.view.unit_height).length_mm
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
        elements_service._loading_cleared = True
        to_regmarks = elements_service.load_hidden_to_regmarks
        svg_processor = SVGProcessor(
            elements_service, load_operations=False, load_hidden_to_regmarks=to_regmarks
        )
        svg_processor.process(svg, pathname)
        svg_processor.cleanup()
        return True
