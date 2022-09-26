import ast
import gzip
import os
from base64 import b64encode
from io import BytesIO
from xml.etree.ElementTree import Element, ElementTree, ParseError, SubElement

from meerk40t.core.exceptions import BadFileError
from meerk40t.core.node.node import Fillrule, Linecap, Linejoin

from ..svgelements import (
    SVG,
    SVG_ATTR_DATA,
    SVG_ATTR_FILL,
    SVG_ATTR_FILL_OPACITY,
    SVG_ATTR_FONT_FAMILY,
    SVG_ATTR_FONT_SIZE,
    SVG_ATTR_FONT_STRETCH,
    SVG_ATTR_FONT_STYLE,
    SVG_ATTR_FONT_VARIANT,
    SVG_ATTR_FONT_WEIGHT,
    SVG_ATTR_HEIGHT,
    SVG_ATTR_ID,
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
    SVG_ATTR_XMLNS,
    SVG_ATTR_XMLNS_EV,
    SVG_ATTR_XMLNS_LINK,
    SVG_ATTR_Y,
    SVG_NAME_TAG,
    SVG_RULE_EVENODD,
    SVG_RULE_NONZERO,
    SVG_TAG_GROUP,
    SVG_TAG_IMAGE,
    SVG_TAG_PATH,
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
from .units import DEFAULT_PPI, NATIVE_UNIT_PER_INCH, UNITS_PER_PIXEL

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
        yield "SVG-Compressed", "svgz", "image/svg+xml", "compressed"

    @staticmethod
    def save(context, f, version="default"):
        root = Element(SVG_NAME_TAG)
        root.set(SVG_ATTR_VERSION, SVG_VALUE_VERSION)
        root.set(SVG_ATTR_XMLNS, SVG_VALUE_XMLNS)
        root.set(SVG_ATTR_XMLNS_LINK, SVG_VALUE_XLINK)
        root.set(SVG_ATTR_XMLNS_EV, SVG_VALUE_XMLNS_EV)
        root.set(
            "xmlns:" + MEERK40T_XMLS_ID,
            MEERK40T_NAMESPACE,
        )
        scene_width = context.device.length_width
        scene_height = context.device.length_height
        root.set(SVG_ATTR_WIDTH, scene_width.length_mm)
        root.set(SVG_ATTR_HEIGHT, scene_height.length_mm)
        px_width = scene_width.pixels
        px_height = scene_height.pixels

        viewbox = f"{0} {0} {round(px_width)} {round(px_height)}"
        root.set(SVG_ATTR_VIEWBOX, viewbox)
        elements = context.elements
        elements.validate_ids()
        # If we want to write labels then we need to establish the inkscape namespace
        has_labels = False
        for n in elements.elems_nodes():
            if hasattr(n, "label") and n.label is not None and n.label != "":
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

        # If there is a note set then we save the note with the project.
        if elements.note is not None:
            subelement = SubElement(root, "note")
            subelement.set(SVG_TAG_TEXT, elements.note)

        SVGWriter._write_tree(root, elements._tree)

        SVGWriter._pretty_print(root)
        tree = ElementTree(root)
        if f.lower().endswith("svgz"):
            f = gzip.open(f, "wb")
        tree.write(f)

    @staticmethod
    def _write_tree(xml_tree, node_tree):
        for node in node_tree.children:
            if node.type == "branch ops":
                SVGWriter._write_operations(xml_tree, node)
            elif node.type == "branch elems":
                SVGWriter._write_elements(xml_tree, node)
            elif node.type == "branch reg":
                SVGWriter._write_regmarks(xml_tree, node)

    @staticmethod
    def _write_elements(xml_tree, elem_tree):
        """
        Write the elements branch part of the tree to disk.

        @param xml_tree:
        @param elem_tree:
        @return:
        """

        scale = Matrix.scale(1.0 / UNITS_PER_PIXEL)
        for c in elem_tree.children:
            if c.type == "elem ellipse":
                element = abs(Path(c.shape) * scale)
                copy_attributes(c, element)
                subelement = SubElement(xml_tree, SVG_TAG_PATH)
                subelement.set(SVG_ATTR_DATA, element.d(transformed=False))
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
                t = Matrix(c.matrix) * scale
                subelement.set(
                    "transform",
                    f"matrix({t.a}, {t.b}, {t.c}, {t.d}, {t.e}, {t.f})",
                )
            elif c.type == "elem line":
                element = abs(Path(c.shape) * scale)
                copy_attributes(c, element)
                subelement = SubElement(xml_tree, SVG_TAG_PATH)
                subelement.set(SVG_ATTR_DATA, element.d(transformed=False))
            elif c.type == "elem path":
                element = abs(c.path * scale)
                copy_attributes(c, element)
                subelement = SubElement(xml_tree, SVG_TAG_PATH)
                subelement.set(SVG_ATTR_DATA, element.d(transformed=False))
            elif c.type == "elem point":
                element = Point(c.point) * scale
                c.settings["x"] = element.x
                c.settings["y"] = element.y
                subelement = SubElement(xml_tree, "element")
                SVGWriter._write_custom(subelement, c)
            elif c.type == "elem polyline":
                element = abs(Path(c.shape) * scale)
                copy_attributes(c, element)
                subelement = SubElement(xml_tree, SVG_TAG_PATH)
                subelement.set(SVG_ATTR_DATA, element.d(transformed=False))
            elif c.type == "elem rect":
                element = abs(Path(c.shape) * scale)
                copy_attributes(c, element)
                subelement = SubElement(xml_tree, SVG_TAG_PATH)
                subelement.set(SVG_ATTR_DATA, element.d(transformed=False))
            elif c.type == "elem text":
                subelement = SubElement(xml_tree, SVG_TAG_TEXT)
                subelement.text = c.text
                t = Matrix(c.matrix) * scale
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
                SVGWriter._write_elements(group_element, c)
                continue
            elif c.type == "file":
                # This is a structural group node of elements. Recurse call to write values.
                SVGWriter._write_elements(xml_tree, c)
                continue
            else:
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
                    and key not in ("settings", "attributes")
                    and value is not None
                    and isinstance(value, (str, int, float, complex, list, dict))
                ):
                    subelement.set(key, str(value))
            ###############
            # SAVE CAP/JOIN/FILL-RULE
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
                    stroke_width = SVG_VALUE_NONE
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
    def _write_operations(xml_tree, op_tree):
        """
        Write the operations branch part of the tree to disk.

        @param xml_tree:
        @param elem_tree:
        @return:
        """
        for c in op_tree.children:
            SVGWriter._write_operation(xml_tree, c)

    @staticmethod
    def _write_regmarks(xml_tree, reg_tree):
        if len(reg_tree.children):
            regmark = SubElement(xml_tree, SVG_TAG_GROUP)
            regmark.set("id", "regmarks")
            regmark.set("visibility", "hidden")
            SVGWriter._write_elements(regmark, reg_tree)

    @staticmethod
    def _write_operation(xml_tree, node):
        """
        Write an individual operation. This is any node directly under `branch ops`

        @param xml_tree:
        @param node:
        @return:
        """
        subelement = SubElement(xml_tree, MEERK40T_XMLS_ID + ":operation")
        SVGWriter._write_custom(subelement, node)

    @staticmethod
    def _write_custom(subelement, node):
        subelement.set("type", node.type)
        try:
            settings = node.settings
            for key in settings:
                if not key:
                    # If key is None, do not save.
                    continue
                if key == "references":
                    # References key is obsolete
                    continue
                value = settings[key]
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

        if self.requires_classification:
            self.elements.classify(self.element_list)

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

    def parse(self, element, context_node, e_list):
        if element.values.get("visibility") == "hidden":
            context_node = self.regmark
            e_list = self.regmark_list
        ident = element.id
        # Let's see whether we can get the label from an inkscape save
        _label = None
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
        if isinstance(element, SVGText):
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
        elif isinstance(element, (Polygon, Polyline)) or (
            isinstance(element, Path) and element.values.get("type") == "elem polyline"
        ):
            if not element.is_degenerate():
                if not element.transform.is_identity():
                    # Shape did not reify, convert to path.
                    element = Path(element)
                    element.reify()
                    element.approximate_arcs_with_cubics()
                node = context_node.add(
                    shape=element,
                    type="elem polyline",
                    id=ident,
                    label=_label,
                    lock=_lock,
                )
                self.check_for_line_attributes(node, element)
                self.check_for_fill_attributes(node, element)
                e_list.append(node)
        elif isinstance(element, Circle) or (
            isinstance(element, Path) and element.values.get("type") == "elem circle"
        ):
            if not element.is_degenerate():
                if not element.transform.is_identity():
                    # Shape did not reify, convert to path.
                    element = Path(element)
                    element.reify()
                    element.approximate_arcs_with_cubics()
                node = context_node.add(
                    shape=element,
                    type="elem ellipse",
                    id=ident,
                    label=_label,
                    lock=_lock,
                )
                e_list.append(node)
        elif isinstance(element, Ellipse) or (
            isinstance(element, Path) and element.values.get("type") == "elem ellipse"
        ):
            if not element.is_degenerate():
                if not element.transform.is_identity():
                    # Shape did not reify, convert to path.
                    element = Path(element)
                    element.reify()
                    element.approximate_arcs_with_cubics()
                node = context_node.add(
                    shape=element,
                    type="elem ellipse",
                    id=ident,
                    label=_label,
                    lock=_lock,
                )
                e_list.append(node)
        elif isinstance(element, Rect) or (
            isinstance(element, Path) and element.values.get("type") == "elem rect"
        ):
            if not element.is_degenerate():
                if not element.transform.is_identity():
                    # Shape did not reify, convert to path.
                    element = Path(element)
                    element.reify()
                    element.approximate_arcs_with_cubics()
                node = context_node.add(
                    shape=element, type="elem rect", id=ident, label=_label, lock=_lock
                )
                self.check_for_line_attributes(node, element)
                e_list.append(node)
        elif isinstance(element, SimpleLine) or (
            isinstance(element, Path) and element.values.get("type") == "elem line"
        ):
            if not element.is_degenerate():
                if not element.transform.is_identity():
                    # Shape did not reify, convert to path.
                    element = Path(element)
                    element.reify()
                    element.approximate_arcs_with_cubics()
                node = context_node.add(
                    shape=element, type="elem line", id=ident, label=_label, lock=_lock
                )
                self.check_for_line_attributes(node, element)
                e_list.append(node)
        elif isinstance(element, Path):
            if len(element) >= 0:
                element.approximate_arcs_with_cubics()
                node = context_node.add(
                    path=element, type="elem path", id=ident, label=_label, lock=_lock
                )
                self.check_for_line_attributes(node, element)
                self.check_for_fill_attributes(node, element)
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
        elif isinstance(element, (Group, Use)):
            context_node = context_node.add(type="group", id=ident, label=_label)
            # recurse to children
            if self.reverse:
                for child in reversed(element):
                    self.parse(child, context_node, e_list)
            else:
                for child in element:
                    self.parse(child, context_node, e_list)
        else:
            # SVGElement is type. Generic or unknown node type.
            tag = element.values.get(SVG_ATTR_TAG)
            # We need to reverse the meerk40t:... replacement that the routine had already applied:
            if tag is not None:
                tag = tag.lower()
                torepl = "{" + MEERK40T_NAMESPACE.lower() + "}"
                if torepl in tag:
                    oldval = element.values.get(tag)
                    replacer = MEERK40T_XMLS_ID.lower() + ":"
                    tag = tag.replace(
                        torepl,
                        replacer,
                    )
                    element.values[tag] = oldval
                    element.values[SVG_ATTR_TAG] = tag
            # Check if note-type
            if tag in (MEERK40T_XMLS_ID + ":note", "note"):
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
            if tag in (f"{MEERK40T_XMLS_ID}:operation", "operation"):
                # Check if SVGElement: operation
                if not self.operations_cleared:
                    self.elements.clear_operations()
                    self.operations_cleared = True
                try:
                    attrs = element.values["attributes"]
                except KeyError:
                    attrs = element.values
                try:
                    try:
                        del attrs["type"]
                    except KeyError:
                        pass
                    op = self.elements.op_branch.add(type=node_type, **attrs)
                    op.validate()
                    op.id = node_id
                except AttributeError:
                    # This operation is invalid.
                    pass
            elif tag in (f"{MEERK40T_XMLS_ID}:element", "element"):
                # Check if SVGElement: element
                if "type" in element.values:
                    del element.values["type"]
                if "fill" in element.values:
                    element.values["fill"] = Color(element.values["fill"])
                if "stroke" in element.values:
                    element.values["stroke"] = Color(element.values["stroke"])
                if "transform" in element.values:
                    element.values["matrix"] = Matrix(element.values["transform"])
                if "settings" in element.values:
                    del element.values["settings"]  # If settings was set, delete it or it will mess things up
                if "lock" in element.values:
                    element.values["lock"] = _lock
                elem = context_node.add(type=node_type, **element.values)
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
            svg = SVG.parse(
                source=source,
                reify=True,
                width=width,
                height=height,
                ppi=ppi,
                color="none",
                transform=f"scale({scale_factor})",
            )
        except ParseError as e:
            raise BadFileError(str(e)) from e
        svg_processor = SVGProcessor(elements_service)
        svg_processor.process(svg, pathname)
        return True
