import os
from base64 import b64encode
from io import BytesIO
from xml.etree.cElementTree import Element, ElementTree, SubElement

from .elements import LaserOperation
from ..svgelements import (
    SVG_NAME_TAG,
    SVG_ATTR_VERSION,
    SVG_VALUE_VERSION,
    SVG_ATTR_XMLNS,
    SVG_VALUE_XMLNS,
    SVG_ATTR_XMLNS_LINK,
    SVG_VALUE_XLINK,
    SVG_ATTR_XMLNS_EV,
    SVG_VALUE_XMLNS_EV,
    SVG_ATTR_WIDTH,
    SVG_ATTR_HEIGHT,
    SVG_ATTR_VIEWBOX,
    SVG_TAG_TEXT,
    Path,
    SVG_TAG_PATH,
    SVG_ATTR_DATA,
    SVG_ATTR_TRANSFORM,
    SVG_ATTR_STROKE_WIDTH,
    Shape,
    Rect,
    SVG_TAG_RECT,
    Circle,
    SVG_TAG_CIRCLE,
    Ellipse,
    SVG_TAG_ELLIPSE,
    Polygon,
    SVG_TAG_POLYGON,
    Polyline,
    SVG_TAG_POLYLINE,
    Matrix,
    SVG_ATTR_RADIUS_X,
    SVG_ATTR_RADIUS_Y,
    SVG_ATTR_POINTS,
    SVG_ATTR_RADIUS,
    SVG_ATTR_X,
    SVG_ATTR_Y,
    SVGText,
    SVGImage,
    SVG_TAG_IMAGE,
    SVG_VALUE_NONE,
    SVG_ATTR_STROKE,
    SVG_ATTR_FILL,
    SVG,
    Group,
    SVGElement,
    SVG_ATTR_TAG,
    Color,
    SVG_ATTR_ID,
    SVG_ATTR_FILL_OPACITY,
    SVG_ATTR_STROKE_OPACITY,
)

MILS_PER_MM = 39.3701


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
            "xmlns:meerK40t", "https://github.com/meerk40t/meerk40t/wiki/Namespace"
        )
        # Native unit is mils, these must convert to mm and to px
        mils_per_mm = 39.3701
        mils_per_px = 1000.0 / 96.0
        px_per_mils = 96.0 / 1000.0
        context.setting(int, "bed_width", 310)
        context.setting(int, "bed_height", 210)
        mm_width = context.bed_width
        mm_height = context.bed_height
        root.set(SVG_ATTR_WIDTH, "%fmm" % mm_width)
        root.set(SVG_ATTR_HEIGHT, "%fmm" % mm_height)
        px_width = mm_width * mils_per_mm * px_per_mils
        px_height = mm_height * mils_per_mm * px_per_mils

        viewbox = "%d %d %d %d" % (0, 0, round(px_width), round(px_height))
        scale = "scale(%f)" % px_per_mils
        root.set(SVG_ATTR_VIEWBOX, viewbox)
        elements = context.elements
        for operation in elements.ops():
            subelement = SubElement(root, "operation")
            c = getattr(operation, "color")
            if c is not None:
                subelement.set("color", str(c))
            for key in dir(operation):
                if key.startswith("_"):
                    continue
                value = getattr(operation, key)
                if type(value) not in (int, float, str, bool):
                    continue
                subelement.set(key, str(value))

        if elements.note is not None:
            subelement = SubElement(root, "note")
            subelement.set(SVG_TAG_TEXT, elements.note)
        for element in elements.elems():

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
                        "font-size",
                        "font-weight",
                    ):
                        subelement.set(key, str(val))
            else:  # Image.
                subelement = SubElement(root, SVG_TAG_IMAGE)
                stream = BytesIO()
                element.image.save(stream, format="PNG")
                png = b64encode(stream.getvalue()).decode("utf8")
                subelement.set("xlink:href", "data:image/png;base64,%s" % (png))
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
        yield "Scalable Vector Graphics", ("svg",), "image/svg+xml"

    @staticmethod
    def load(context, elements_modifier, pathname, **kwargs):
        context.setting(int, "bed_width", 310)
        context.setting(int, "bed_height", 210)
        if "svg_ppi" in kwargs:
            ppi = float(kwargs["svg_ppi"])
        else:
            ppi = 96.0
        if ppi == 0:
            ppi = 96.0
        scale_factor = 1000.0 / ppi
        svg = SVG.parse(
            source=pathname,
            reify=False,
            width="%fmm" % (context.bed_width),
            height="%fmm" % (context.bed_height),
            ppi=ppi,
            color="none",
            transform="scale(%f)" % scale_factor,
        )
        for element in svg:
            try:
                if element.values["visibility"] == "hidden":
                    continue
            except KeyError:
                pass
            except AttributeError:
                pass
            if isinstance(element, SVGText):
                elements_modifier.add_elem(element)
                elements_modifier.classify(element)
            elif isinstance(element, Path):
                if len(element) != 0:
                    element.approximate_arcs_with_cubics()
                    elements_modifier.add_elem(element)
                    elements_modifier.classify(element)
            elif isinstance(element, Shape):
                e = Path(element)
                e.reify()  # In some cases the shape could not have reified, the path must.
                if len(e) != 0:
                    e.approximate_arcs_with_cubics()
                    elements_modifier.add_elem(e)
                    elements_modifier.classify(element)
            elif isinstance(element, SVGImage):
                try:
                    element.load(os.path.dirname(pathname))
                    if element.image is not None:
                        elements_modifier.add_elem(element)
                        elements_modifier.classify(element)
                except OSError:
                    pass
            elif isinstance(element, SVG):
                continue
            elif isinstance(element, Group):
                continue
            elif isinstance(element, SVGElement):
                try:
                    if str(element.values[SVG_ATTR_TAG]).lower() == "note":
                        try:
                            elements_modifier.note = element.values[SVG_TAG_TEXT]
                        except KeyError:
                            pass
                except KeyError:
                    pass
                try:
                    if str(element.values[SVG_ATTR_TAG]).lower() == "operation":
                        op = LaserOperation()
                        for key in dir(op):
                            if key.startswith("_"):
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
                            if key.startswith("_"):
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
                                    except (ValueError, KeyError):
                                        pass
                                elif type_v == bool:
                                    setattr(
                                        op.settings,
                                        key,
                                        str(element.values[key]).lower()
                                        in ("true", "1"),
                                    )
                        elements_modifier.add_op(op)
                except KeyError:
                    pass
        return True
