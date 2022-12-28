import gzip
import os
from base64 import b64encode
from io import BytesIO
from xml.etree.ElementTree import ParseError
from xml.etree.cElementTree import Element, ElementTree, SubElement

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
    SVG_TAG_IMAGE,
    SVG_TAG_PATH,
    SVG_TAG_TEXT,
    SVG_VALUE_NONE,
    SVG_VALUE_VERSION,
    SVG_VALUE_XLINK,
    SVG_VALUE_XMLNS,
    SVG_VALUE_XMLNS_EV,
    Color,
    Group,
    Matrix,
    Path,
    Shape,
    SVGElement,
    SVGImage,
    SVGText,
    Use,
)
from .elements import LaserOperation

MILS_IN_MM = 39.3701


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("load/SVGLoader", SVGLoader)
        kernel.register("save/SVGWriter", SVGWriter)


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
            "https://htmlpreview.github.io/?https://github.com/meerk40t/meerk40t/blob/master/svg-namespace.html",
        )
        # Native unit is mils, these must convert to mm and to px
        # mils_per_px = 1000.0 / 96.0
        px_per_mils = 96.0 / 1000.0
        bed_dim = context.root
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)
        mm_width = bed_dim.bed_width
        mm_height = bed_dim.bed_height
        root.set(SVG_ATTR_WIDTH, "%fmm" % mm_width)
        root.set(SVG_ATTR_HEIGHT, "%fmm" % mm_height)
        px_width = mm_width * MILS_IN_MM * px_per_mils
        px_height = mm_height * MILS_IN_MM * px_per_mils

        viewbox = "%d %d %d %d" % (0, 0, round(px_width), round(px_height))
        scale = "scale(%f)" % px_per_mils
        root.set(SVG_ATTR_VIEWBOX, viewbox)
        elements = context.elements
        for operation in elements.ops():
            subelement = SubElement(root, "operation")

            if hasattr(operation, "color"):
                c = getattr(operation, "color")
                if c is not None:
                    if isinstance(c, int):
                        c = Color(c)
                subelement.set("color", str(c).lower())
            for key in dir(operation):
                if key.startswith("_") or key.startswith("implicit"):
                    continue
                value = getattr(operation, key)
                if type(value) not in (int, float, str, bool):
                    continue
                subelement.set(key, str(value))
            if hasattr(operation, "settings"):
                for key in dir(operation.settings):
                    if key.startswith("_") or key.startswith("implicit"):
                        continue
                    value = getattr(operation.settings, key)
                    if type(value) not in (int, float, str, bool):
                        continue
                    subelement.set(key, str(value))

        if elements.note is not None:
            subelement = SubElement(root, "note")
            subelement.set(SVG_TAG_TEXT, elements.note)
        for element in elements.elems():

            if isinstance(element, Shape) and not isinstance(element, Path):
                element = Path(element)

            if isinstance(element, Path):
                element = abs(element)
                subelement = SubElement(root, SVG_TAG_PATH)
                subelement.set(SVG_ATTR_DATA, element.d(transformed=False))
                subelement.set(SVG_ATTR_TRANSFORM, scale)

                for key, val in element.values.items():
                    if key in (
                        "speed",
                        "overscan",
                        "power",
                        "passes",
                        "raster_direction",
                        "raster_step",
                        "d_ratio",
                    ):
                        subelement.set(key, str(val))
            elif isinstance(element, SVGText):
                subelement = SubElement(root, SVG_TAG_TEXT)
                subelement.text = element.text
                t = Matrix(element.transform)
                t *= scale
                subelement.set(
                    "transform",
                    "matrix(%f, %f, %f, %f, %f, %f)" % (t.a, t.b, t.c, t.d, t.e, t.f),
                )
                for key, val in element.values.items():
                    if key in (
                        "speed",
                        "overscan",
                        "power",
                        "passes",
                        "raster_direction",
                        "raster_step",
                        "d_ratio",
                        "font-family",
                        "font_face",
                        "font-size",
                        "font-weight",
                        "anchor",
                        "x",
                        "y",
                    ):
                        subelement.set(key, str(val))
            elif isinstance(element, SVGImage):
                subelement = SubElement(root, SVG_TAG_IMAGE)
                stream = BytesIO()
                try:
                    element.image.save(stream, format="PNG")
                except OSError:
                    # Edge condition if the original image was CMYK and never touched it can't encode to PNG
                    element.image.convert("RGBA").save(stream, format="PNG")
                png = b64encode(stream.getvalue()).decode("utf8")
                subelement.set("xlink:href", "data:image/png;base64,%s" % png)
                subelement.set(SVG_ATTR_X, "0")
                subelement.set(SVG_ATTR_Y, "0")
                subelement.set(SVG_ATTR_WIDTH, str(element.image.width))
                subelement.set(SVG_ATTR_HEIGHT, str(element.image.height))
                subelement.set(SVG_ATTR_TRANSFORM, scale)
                t = Matrix(element.transform)
                t *= scale
                subelement.set(
                    "transform",
                    "matrix(%f, %f, %f, %f, %f, %f)" % (t.a, t.b, t.c, t.d, t.e, t.f),
                )
                if element.values is not None:
                    for key, val in element.values.items():
                        if key in (
                            "speed",
                            "overscan",
                            "power",
                            "passes",
                            "raster_direction",
                            "raster_step",
                            "d_ratio",
                        ):
                            subelement.set(key, str(val))
            else:
                raise ValueError("Attempting to save unknown element.")
            stroke = element.stroke
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

            fill = element.fill
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

            if element.id is not None:
                subelement.set(SVG_ATTR_ID, str(element.id))
        SVGWriter._pretty_print(root)
        tree = ElementTree(root)
        tree.write(f)

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


class SVGLoader:
    @staticmethod
    def load_types():
        yield "Scalable Vector Graphics", ("svg", "svgz"), "image/svg+xml"

    @staticmethod
    def load(context, elements_modifier, pathname, **kwargs):
        # context.root.setting(bool, "classify_reverse", False)
        reverse = False
        bed_dim = context.root
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)
        if "svg_ppi" in kwargs:
            ppi = float(kwargs["svg_ppi"])
        else:
            ppi = 96.0
        if ppi == 0:
            ppi = 96.0
        scale_factor = 1000.0 / ppi
        source = pathname
        if pathname.lower().endswith("svgz"):
            source = gzip.open(pathname, "rb")
        try:
            svg = SVG.parse(
                source=source,
                reify=True,
                width="%fmm" % bed_dim.bed_width,
                height="%fmm" % bed_dim.bed_height,
                ppi=ppi,
                color="none",
                transform="scale(%f)" % scale_factor,
            )
        except ParseError as e:
            raise BadFileError(str(e)) from e
        context_node = elements_modifier.get(type="branch elems")
        basename = os.path.basename(pathname)
        file_node = context_node.add(type="file", label=basename)
        file_node.filepath = pathname
        file_node.focus()
        elements = []
        result = SVGLoader.parse(
            svg, elements_modifier, file_node, pathname, scale_factor, reverse, elements
        )
        elements_modifier.classify(elements)
        return result

    @staticmethod
    def parse(
        svg, elements_modifier, context_node, pathname, scale_factor, reverse, elements
    ):
        operations_cleared = False
        if reverse:
            svg = reversed(svg)
        for element in svg:
            try:
                if element.values["visibility"] == "hidden":
                    continue
            except KeyError:
                pass
            except AttributeError:
                pass
            if isinstance(element, SVGText):
                if element.text is None:
                    continue
                context_node.add(element, type="elem")
                elements.append(element)
            elif isinstance(element, Path):
                if len(element) == 0:
                    continue
                element.approximate_arcs_with_cubics()
                context_node.add(element, type="elem")
                elements.append(element)
            elif isinstance(element, Shape):
                if not element.transform.is_identity():
                    # 1 Shape Reification failed.
                    element = Path(element)
                    element.reify()
                    element.approximate_arcs_with_cubics()
                    if len(element) == 0:
                        continue  # Degenerate.
                else:
                    e = Path(element)
                    if len(e) == 0:
                        continue  # Degenerate.
                context_node.add(element, type="elem")
                elements.append(element)
            elif isinstance(element, SVGImage):
                try:
                    element.load(os.path.dirname(pathname))
                    if element.image is not None:
                        context_node.add(element, type="elem")
                        elements.append(element)
                except OSError:
                    pass
            elif isinstance(element, SVG):
                continue
            elif isinstance(element, Use):
                new_context = context_node.add(Group(), type="group")
                SVGLoader.parse(
                    element,
                    elements_modifier,
                    new_context,
                    pathname,
                    scale_factor,
                    reverse,
                    elements,
                )
                continue
            elif isinstance(element, Group):
                new_context = context_node.add(element, type="group")
                SVGLoader.parse(
                    element,
                    elements_modifier,
                    new_context,
                    pathname,
                    scale_factor,
                    reverse,
                    elements,
                )
                continue
            elif isinstance(element, SVGElement):
                try:
                    if str(element.values[SVG_ATTR_TAG]).lower() == "note":
                        try:
                            elements_modifier.note = element.values[SVG_TAG_TEXT]
                            elements_modifier.context.signal("note", pathname)
                        except (KeyError, AttributeError):
                            pass
                except KeyError:
                    pass
                try:
                    if str(element.values[SVG_ATTR_TAG]).lower() == "operation":
                        if not operations_cleared:
                            elements_modifier.clear_operations()
                            operations_cleared = True
                        op = LaserOperation()
                        for key in dir(op):
                            if key.startswith("_") or key.startswith("implicit"):
                                continue
                            v = getattr(op, key)
                            if key in element.values:
                                type_v = type(v)
                                if type_v in (str, int, float, Color):
                                    try:
                                        setattr(op, key, type_v(element.values[key]))
                                    except (ValueError, KeyError):
                                        pass
                                elif type_v == bool:
                                    setattr(
                                        op,
                                        key,
                                        str(element.values[key]).lower()
                                        in ("true", "1"),
                                    )
                        for key in dir(op.settings):
                            if key.startswith("_") or key.startswith("implicit"):
                                continue
                            v = getattr(op.settings, key)
                            if key in element.values:
                                type_v = type(v)
                                if type_v in (str, int, float, Color):
                                    try:
                                        setattr(
                                            op.settings,
                                            key,
                                            type_v(element.values[key]),
                                        )
                                    except (ValueError, KeyError, AttributeError):
                                        pass
                                elif type_v == bool:
                                    try:
                                        setattr(
                                            op.settings,
                                            key,
                                            str(element.values[key]).lower()
                                            in ("true", "1"),
                                        )
                                    except (ValueError, KeyError, AttributeError):
                                        pass
                        elements_modifier.add_op(op)
                except KeyError:
                    pass

        return True
