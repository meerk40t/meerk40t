import gzip
import os
from base64 import b64encode
from io import BytesIO
from xml.etree.ElementTree import Element, ElementTree, ParseError, SubElement

from meerk40t.core.exceptions import BadFileError

from ..svgelements import (
    SVG,
    SVG_ATTR_DATA,
    SVG_ATTR_FILL,
    SVG_ATTR_FILL_OPACITY,
    SVG_ATTR_HEIGHT,
    SVG_ATTR_ID,
    SVG_ATTR_STROKE,
    SVG_ATTR_STROKE_OPACITY,
    SVG_ATTR_STROKE_WIDTH,
    SVG_ATTR_TAG,
    SVG_ATTR_TRANSFORM,
    SVG_ATTR_VERSION,
    SVG_ATTR_VIEWBOX,
    SVG_ATTR_WIDTH,
    SVG_ATTR_X,
    SVG_ATTR_XMLNS,
    SVG_ATTR_XMLNS_EV,
    SVG_ATTR_XMLNS_LINK,
    SVG_ATTR_Y,
    SVG_NAME_TAG,
    SVG_TAG_GROUP,
    SVG_TAG_IMAGE,
    SVG_TAG_PATH,
    SVG_TAG_TEXT,
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
    Polygon,
    Polyline,
    Rect,
    SimpleLine,
    SVGImage,
    SVGText,
)
from .units import DEFAULT_PPI, UNITS_PER_INCH, UNITS_PER_PIXEL


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation
        choices = [
            {
                "attr": "uniform_svg",
                "object": kernel.elements,
                "default": False,
                "type": bool,
                "label": _("SVG Uniform Save"),
                "tip": _(
                    "Do not treat overwriting SVG differently if they are MeerK40t files"
                ),
            },
        ]
        kernel.register_choices("preferences", choices)
        kernel.register("load/SVGLoader", SVGLoader)
        kernel.register("save/SVGWriter", SVGWriter)


MEERK40T_NAMESPACE = "https://github.com/meerk40t/meerk40t/wiki/Namespace"


class SVGWriter:
    @staticmethod
    def save_types():
        yield "Scalable Vector Graphics", "svg", "image/svg+xml"

    @staticmethod
    def versions():
        yield "default"

    @staticmethod
    def save(context, f, version="default"):
        root = Element(SVG_NAME_TAG)
        root.set(SVG_ATTR_VERSION, SVG_VALUE_VERSION)
        root.set(SVG_ATTR_XMLNS, SVG_VALUE_XMLNS)
        root.set(SVG_ATTR_XMLNS_LINK, SVG_VALUE_XLINK)
        root.set(SVG_ATTR_XMLNS_EV, SVG_VALUE_XMLNS_EV)
        root.set(
            "xmlns:meerK40t",
            MEERK40T_NAMESPACE,
        )
        scene_width = context.device.length_width
        scene_height = context.device.length_height
        root.set(SVG_ATTR_WIDTH, scene_width.length_mm)
        root.set(SVG_ATTR_HEIGHT, scene_height.length_mm)
        px_width = scene_width.pixels
        px_height = scene_height.pixels

        viewbox = "%d %d %d %d" % (0, 0, round(px_width), round(px_height))
        root.set(SVG_ATTR_VIEWBOX, viewbox)
        elements = context.elements
        elements.validate_ids()

        # If there is a note set then we save the note with the project.
        if elements.note is not None:
            subelement = SubElement(root, "note")
            subelement.set(SVG_TAG_TEXT, elements.note)

        SVGWriter._write_tree(root, elements._tree)

        SVGWriter._pretty_print(root)
        tree = ElementTree(root)
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
        def copy_attributes(source, target):
            #
            if hasattr(source, "stroke"):
                target.stroke = source.stroke
            if hasattr(source, "fill"):
                target.fill = source.fill

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
                c.image.save(stream, format="PNG")
                png = b64encode(stream.getvalue()).decode("utf8")
                subelement.set("xlink:href", "data:image/png;base64,%s" % png)
                subelement.set(SVG_ATTR_X, "0")
                subelement.set(SVG_ATTR_Y, "0")
                subelement.set(SVG_ATTR_WIDTH, str(c.image.width))
                subelement.set(SVG_ATTR_HEIGHT, str(c.image.height))
                t = Matrix(c.matrix)
                t *= scale
                subelement.set(
                    "transform",
                    "matrix(%f, %f, %f, %f, %f, %f)" % (t.a, t.b, t.c, t.d, t.e, t.f),
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
                subelement = SubElement(xml_tree, "element")
                SVGWriter._write_custom(subelement, c)
                return
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
                element = c.text
                copy_attributes(c, element)
                subelement = SubElement(xml_tree, SVG_TAG_TEXT)
                subelement.text = element.text
                t = Matrix(element.transform)
                t *= scale
                subelement.set(
                    "transform",
                    "matrix(%f, %f, %f, %f, %f, %f)" % (t.a, t.b, t.c, t.d, t.e, t.f),
                )
                for key, val in element.values.items():
                    if key in (
                        "font-family",
                        "font_face",
                        "font-size",
                        "font-weight",
                        "anchor",
                        "x",
                        "y",
                    ):
                        subelement.set(key, str(val))
            elif c.type == "group":
                # This is a structural group node of elements. Recurse call to write flat values.
                SVGWriter._write_elements(xml_tree, c)
                return
            elif c.type == "file":
                # This is a structural group node of elements. Recurse call to write flat values.
                SVGWriter._write_elements(xml_tree, c)
                return
            else:
                subelement = SubElement(xml_tree, "element")
                SVGWriter._write_custom(subelement, c)
                return
            if hasattr(element, "stroke"):
                stroke = element.stroke
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
                    stroke_width = (
                        str(element.stroke_width)
                        if element.stroke_width is not None
                        else SVG_VALUE_NONE
                    )
                    subelement.set(SVG_ATTR_STROKE_WIDTH, stroke_width)
                except AttributeError:
                    pass

            if hasattr(element, "fill"):
                fill = element.fill
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
            for c in reg_tree.children:
                SVGWriter._write_elements(regmark, c)

    @staticmethod
    def _write_operation(xml_tree, node):
        """
        Write an individual operation. This is any node directly under `branch ops`

        @param xml_tree:
        @param node:
        @return:
        """
        subelement = SubElement(xml_tree, "operation")
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
                value = settings[key]
                subelement.set(key, str(value))
        except AttributeError:
            pass
        contains = list()
        for c in node.children:
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

    def parse(self, element, context_node, e_list):
        if element.values.get("visibility") == "hidden":
            context_node = self.regmark
            e_list = self.regmark_list
        ident = element.id
        if isinstance(element, SVGText):
            if element.text is not None:
                node = context_node.add(text=element, type="elem text", id=ident)
                e_list.append(node)
        elif isinstance(element, Path):
            if len(element) >= 0:
                element.approximate_arcs_with_cubics()
                node = context_node.add(path=element, type="elem path", id=ident)
                e_list.append(node)
        elif isinstance(element, (Polygon, Polyline)):
            if not element.is_degenerate():
                if not element.transform.is_identity():
                    # Shape did not reify, convert to path.
                    element = Path(element)
                    element.reify()
                    element.approximate_arcs_with_cubics()
                node = context_node.add(shape=element, type="elem polyline", id=ident)
                e_list.append(node)
        elif isinstance(element, Circle):
            if not element.is_degenerate():
                if not element.transform.is_identity():
                    # Shape did not reify, convert to path.
                    element = Path(element)
                    element.reify()
                    element.approximate_arcs_with_cubics()
                node = context_node.add(shape=element, type="elem ellipse", id=ident)
                e_list.append(node)
        elif isinstance(element, Ellipse):
            if not element.is_degenerate():
                if not element.transform.is_identity():
                    # Shape did not reify, convert to path.
                    element = Path(element)
                    element.reify()
                    element.approximate_arcs_with_cubics()
                node = context_node.add(shape=element, type="elem ellipse", id=ident)
                e_list.append(node)
        elif isinstance(element, Rect):
            if not element.is_degenerate():
                if not element.transform.is_identity():
                    # Shape did not reify, convert to path.
                    element = Path(element)
                    element.reify()
                    element.approximate_arcs_with_cubics()
                node = context_node.add(shape=element, type="elem rect", id=ident)
                e_list.append(node)
        elif isinstance(element, SimpleLine):
            if not element.is_degenerate():
                if not element.transform.is_identity():
                    # Shape did not reify, convert to path.
                    element = Path(element)
                    element.reify()
                    element.approximate_arcs_with_cubics()
                node = context_node.add(shape=element, type="elem line", id=ident)
                e_list.append(node)
        elif isinstance(element, SVGImage):
            try:
                element.load(os.path.dirname(self.pathname))
                if element.image is not None:
                    node = context_node.add(
                        image=element.image,
                        matrix=element.transform,
                        type="elem image",
                        id=ident,
                    )
                    e_list.append(node)
            except OSError:
                pass
        elif isinstance(element, (Group, SVG)):
            context_node = context_node.add(type="group", id=ident)
            # recurse to children
            if self.reverse:
                for child in reversed(element):
                    self.parse(child, context_node, e_list)
            else:
                for child in element:
                    self.parse(child, context_node, e_list)
        else:
            # Check if SVGElement:  Note.
            tag = element.values.get(SVG_ATTR_TAG)
            if tag is not None:
                tag = tag.lower()
            if tag == "note":
                self.elements.note = element.values.get(SVG_TAG_TEXT)
                self.elements.signal("note", self.pathname)
                return
            node_type = element.values.get("type")
            if node_type is not None:
                node_id = element.values.get("id")
                # Check if SVGElement: operation
                if tag == "operation":
                    if node_type == "op":
                        # Meerk40t 0.7.x fallback node types.
                        op_type = element.values.get("operation")
                        if op_type is None:
                            return
                        node_type = "op %s" % op_type.lower()
                    if not self.operations_cleared:
                        self.elements.clear_operations()
                        self.operations_cleared = True

                    op = self.elements.op_branch.add(type=node_type)

                    try:
                        op.settings.update(element.values["attributes"])
                    except AttributeError:
                        # This operation is invalid.
                        op.remove_node()
                    except KeyError:
                        try:
                            op.settings.update(element.values)
                        except AttributeError:
                            # This operation is invalid.
                            op.remove_node()
                    try:
                        op.validate()
                    except AttributeError:
                        pass
                    op.id = node_id
                # Check if SVGElement: element
                if tag == "element":
                    elem = context_node.add(type=node_type)
                    elem.settings.update(element.values)
                    try:
                        elem.validate()
                    except AttributeError:
                        pass
                    elem.id = node_id


class SVGLoader:
    @staticmethod
    def load_types():
        yield "Scalable Vector Graphics", ("svg", "svgz"), "image/svg+xml"

    @staticmethod
    def load(context, elements_modifier, pathname, **kwargs):
        if "svg_ppi" in kwargs:
            ppi = float(kwargs["svg_ppi"])
        else:
            ppi = DEFAULT_PPI
        if ppi == 0:
            ppi = DEFAULT_PPI
        scale_factor = UNITS_PER_PIXEL
        source = pathname
        if pathname.lower().endswith("svgz"):
            source = gzip.open(pathname, "rb")
        try:
            svg = SVG.parse(
                source=source,
                reify=True,
                width=context.device.length_width.length_mm,
                height=context.device.length_height.length_mm,
                ppi=ppi,
                color="none",
                transform=f"scale({scale_factor})",
            )
        except ParseError as e:
            raise BadFileError(str(e)) from e
        svg_processor = SVGProcessor(elements_modifier)
        svg_processor.process(svg, pathname)
        return True
