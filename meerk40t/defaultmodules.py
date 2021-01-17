import os
from base64 import b64encode
from io import BytesIO
from xml.etree.cElementTree import Element, ElementTree, SubElement

from . laseroperation import LaserOperation
from . svgelements import SVG_NAME_TAG, SVG_ATTR_VERSION, SVG_VALUE_VERSION, SVG_ATTR_XMLNS, SVG_VALUE_XMLNS, \
    SVG_ATTR_XMLNS_LINK, SVG_VALUE_XLINK, SVG_ATTR_XMLNS_EV, SVG_VALUE_XMLNS_EV, SVG_ATTR_WIDTH, SVG_ATTR_HEIGHT, \
    SVG_ATTR_VIEWBOX, SVG_TAG_TEXT, Path, SVG_TAG_PATH, SVG_ATTR_DATA, SVG_ATTR_TRANSFORM, SVG_ATTR_STROKE_WIDTH, Shape, \
    Rect, SVG_TAG_RECT, Circle, SVG_TAG_CIRCLE, Ellipse, SVG_TAG_ELLIPSE, Polygon, SVG_TAG_POLYGON, Polyline, \
    SVG_TAG_POLYLINE, Matrix, SVG_ATTR_RADIUS_X, SVG_ATTR_RADIUS_Y, SVG_ATTR_POINTS, SVG_ATTR_RADIUS, SVG_ATTR_X, \
    SVG_ATTR_Y, SVGText, SVGImage, SVG_TAG_IMAGE, SVG_VALUE_NONE, SVG_ATTR_STROKE, SVG_ATTR_FILL, SVG, Group, \
    SVGElement, SVG_ATTR_TAG, Color, Angle, Arc, Move, SimpleLine

MILS_PER_MM = 39.3701


class SVGWriter:
    @staticmethod
    def save_types():
        yield "Scalable Vector Graphics", "svg", "image/svg+xml"

    @staticmethod
    def versions():
        yield 'default'

    @staticmethod
    def save(context, f, version='default'):
        root = Element(SVG_NAME_TAG)
        root.set(SVG_ATTR_VERSION, SVG_VALUE_VERSION)
        root.set(SVG_ATTR_XMLNS, SVG_VALUE_XMLNS)
        root.set(SVG_ATTR_XMLNS_LINK, SVG_VALUE_XLINK)
        root.set(SVG_ATTR_XMLNS_EV, SVG_VALUE_XMLNS_EV)
        root.set("xmlns:meerK40t", "https://github.com/meerk40t/meerk40t/wiki/Namespace")
        # Native unit is mils, these must convert to mm and to px
        mils_per_mm = 39.3701
        mils_per_px = 1000.0 / 96.0
        px_per_mils = 96.0 / 1000.0
        context.setting(int, "bed_width", 310)
        context.setting(int, "bed_height", 210)
        mm_width = context.bed_width
        mm_height = context.bed_height
        root.set(SVG_ATTR_WIDTH, '%fmm' % mm_width)
        root.set(SVG_ATTR_HEIGHT, '%fmm' % mm_height)
        px_width = mm_width * mils_per_mm * px_per_mils
        px_height = mm_height * mils_per_mm * px_per_mils

        viewbox = '%d %d %d %d' % (0, 0, round(px_width), round(px_height))
        scale = 'scale(%f)' % px_per_mils
        root.set(SVG_ATTR_VIEWBOX, viewbox)
        elements = context.elements
        for operation in elements.ops():
            subelement = SubElement(root, "operation")
            if hasattr(operation, 'color'):
                c = getattr(operation, 'color')
                if c is not None:
                    subelement.set('color', str(c))
            for key in dir(operation):
                if key.startswith('_'):
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
                subelement = SubElement(root, SVG_TAG_PATH)
                subelement.set(SVG_ATTR_DATA, element.d())
                subelement.set(SVG_ATTR_TRANSFORM, scale)
                for key, val in element.values.items():
                    if key in (SVG_ATTR_STROKE_WIDTH, 'fill-opacity', 'speed',
                               'overscan', 'power', 'id', 'passes',
                               'raster_direction', 'raster_step', 'd_ratio'):
                        subelement.set(key, str(val))
            elif isinstance(element, Shape):
                if isinstance(element, Rect):
                    subelement = SubElement(root, SVG_TAG_RECT)
                elif isinstance(element, Circle):
                    subelement = SubElement(root, SVG_TAG_CIRCLE)
                elif isinstance(element, Ellipse):
                    subelement = SubElement(root, SVG_TAG_ELLIPSE)
                elif isinstance(element, Polygon):
                    subelement = SubElement(root, SVG_TAG_POLYGON)
                elif isinstance(element, Polyline):
                    subelement = SubElement(root, SVG_TAG_POLYLINE)
                else:
                    subelement = SubElement(root, type(element))
                t = Matrix(element.transform)
                t *= scale
                subelement.set('transform', 'matrix(%f, %f, %f, %f, %f, %f)' % (t.a, t.b, t.c, t.d, t.e, t.f))
                for key, val in element.values.items():
                    if key in (SVG_ATTR_RADIUS_X, SVG_ATTR_RADIUS_Y, SVG_ATTR_POINTS, SVG_ATTR_RADIUS, SVG_ATTR_X,
                               SVG_ATTR_Y, SVG_ATTR_STROKE_WIDTH, 'fill-opacity', 'speed',
                               'overscan', 'power', 'id', 'passes',
                               'raster_direction', 'raster_step', 'd_ratio'):
                        subelement.set(key, str(val))
            elif isinstance(element, SVGText):
                subelement = SubElement(root, SVG_TAG_TEXT)
                subelement.text = element.text
                t = Matrix(element.transform)
                t *= scale
                subelement.set('transform', 'matrix(%f, %f, %f, %f, %f, %f)' % (t.a, t.b, t.c, t.d, t.e, t.f))
                for key, val in element.values.items():
                    if key in (SVG_ATTR_STROKE_WIDTH, 'fill-opacity', 'speed',
                               'overscan', 'power', 'id', 'passes',
                               'raster_direction', 'raster_step', 'd_ratio',
                               'font-family', 'font-size', 'font-weight'):
                        subelement.set(key, str(val))
            elif isinstance(element, SVGImage):
                subelement = SubElement(root, SVG_TAG_IMAGE)
                stream = BytesIO()
                element.image.save(stream, format='PNG')
                png = b64encode(stream.getvalue()).decode('utf8')
                subelement.set('xlink:href', "data:image/png;base64,%s" % (png))
                subelement.set(SVG_ATTR_X, '0')
                subelement.set(SVG_ATTR_Y, '0')
                subelement.set(SVG_ATTR_WIDTH, str(element.image.width))
                subelement.set(SVG_ATTR_HEIGHT, str(element.image.height))
                subelement.set(SVG_ATTR_TRANSFORM, scale)
                t = Matrix(element.transform)
                t *= scale
                subelement.set('transform', 'matrix(%f, %f, %f, %f, %f, %f)' % (t.a, t.b, t.c, t.d, t.e, t.f))
                for key, val in element.values.items():
                    if key in (SVG_ATTR_STROKE_WIDTH, 'fill-opacity', 'speed',
                               'overscan', 'power', 'id', 'passes',
                               'raster_direction', 'raster_step', 'd_ratio'):
                        subelement.set(key, str(val))
            try:
                stroke = str(element.stroke)
                fill = str(element.fill)
                if stroke == 'None':
                    stroke = SVG_VALUE_NONE
                if fill == 'None':
                    fill = SVG_VALUE_NONE
                subelement.set(SVG_ATTR_STROKE, stroke)
                subelement.set(SVG_ATTR_FILL, fill)
            except AttributeError:
                pass  # element lacks a fill or stroke attribute.
        tree = ElementTree(root)
        tree.write(f)


class SVGLoader:

    @staticmethod
    def load_types():
        yield "Scalable Vector Graphics", ("svg",), "image/svg+xml"

    @staticmethod
    def load(context, pathname, **kwargs):
        context.setting(int, "bed_width", 310)
        context.setting(int, "bed_height", 210)
        elements = []
        if 'svg_ppi' in kwargs:
            ppi = float(kwargs['svg_ppi'])
        else:
            ppi = 96.0
        if ppi == 0:
            ppi = 96.0
        basename = os.path.basename(pathname)
        scale_factor = 1000.0 / ppi
        svg = SVG.parse(source=pathname,
                        reify=False,
                        width='%fmm' % (context.bed_width),
                        height='%fmm' % (context.bed_height),
                        ppi=ppi,
                        color='none',
                        transform='scale(%f)' % scale_factor)
        ops = None
        note = None
        for element in svg.elements():
            try:
                if element.values['visibility'] == 'hidden':
                    continue
            except KeyError:
                pass
            except AttributeError:
                pass
            if isinstance(element, SVGText):
                elements.append(element)
            elif isinstance(element, Path):
                if len(element) != 0:
                    element.approximate_arcs_with_cubics()
                    elements.append(element)
            elif isinstance(element, Shape):
                e = Path(element)
                e.reify()  # In some cases the shape could not have reified, the path must.
                if len(e) != 0:
                    e.approximate_arcs_with_cubics()
                    elements.append(e)
            elif isinstance(element, SVGImage):
                try:
                    element.load(os.path.dirname(pathname))
                    if element.image is not None:
                        elements.append(element)
                except OSError:
                    pass
            elif isinstance(element, SVG):
                continue
            elif isinstance(element, Group):
                continue
            elif isinstance(element, SVGElement):
                try:
                    if str(element.values[SVG_ATTR_TAG]).lower() == 'note':
                        try:
                            note = element.values[SVG_TAG_TEXT]
                        except KeyError:
                            pass
                except KeyError:
                    pass
                try:
                    if str(element.values[SVG_ATTR_TAG]).lower() == 'operation':
                        op = LaserOperation()
                        for key in dir(op):
                            if key.startswith('_'):
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
                                    setattr(op, key, str(element.values[key]).lower() in ("true", "1"))
                        for key in dir(op.settings):
                            if key.startswith('_'):
                                continue
                            v = getattr(op.settings, key)
                            if key in element.values:
                                type_v = type(v)
                                if type_v in (str, int, float, Color):
                                    try:
                                        setattr(op.settings, key, type_v(element.values[key]))
                                    except (ValueError, KeyError):
                                        pass
                                elif type_v == bool:
                                    setattr(op.settings, key, str(element.values[key]).lower() in ("true", "1"))
                        if ops is None:
                            ops = list()
                        ops.append(op)
                except KeyError:
                    pass
        return elements, ops, note, pathname, basename


class ImageLoader:

    @staticmethod
    def load_types():
        yield "Portable Network Graphics", ("png",), "image/png"
        yield "Bitmap Graphics", ("bmp",), "image/bmp"
        yield "EPS Format", ("eps",), "image/eps"
        yield "GIF Format", ("gif",), "image/gif"
        yield "Icon Format", ("ico",), "image/ico"
        yield "JPEG Format", ("jpg", "jpeg", "jpe"), "image/jpeg"
        yield "Webp Format", ("webp",), "image/webp"

    @staticmethod
    def load(context, pathname, **kwargs):
        basename = os.path.basename(pathname)

        image = SVGImage({'href': pathname, 'width': "100%", 'height': "100%", 'id': basename})
        image.load()
        try:
            context.setting(bool, 'image_dpi', True)
            if context.image_dpi:
                dpi = image.image.info['dpi']
                if isinstance(dpi, tuple):
                    image *= 'scale(%f,%f)' % (1000.0/dpi[0], 1000.0/dpi[1])
        except (KeyError, IndexError):
            pass
        return [image], None, None, pathname, basename


class DxfLoader:

    @staticmethod
    def load_types():
        yield "Drawing Exchange Format", ("dxf",), "image/vnd.dxf"

    @staticmethod
    def load(context, pathname, **kwargs):
        """"
        Load dxf content. Requires ezdxf which tends to also require Python 3.6 or greater.

        Dxf data has an origin point located in the lower left corner. +y -> top
        """
        context.setting(int, "bed_width", 310)
        context.setting(int, "bed_height", 210)

        import ezdxf

        basename = os.path.basename(pathname)
        dxf = ezdxf.readfile(pathname)
        elements = []
        for entity in dxf.entities:
            try:
                entity.transform_to_wcs(entity.ocs())
            except AttributeError:
                pass
            if entity.dxftype() == 'CIRCLE':
                element = Circle(center=entity.dxf.center, r=entity.dxf.radius)
            elif entity.dxftype() == 'ARC':
                circ = Circle(center=entity.dxf.center,
                              r=entity.dxf.radius)
                start_angle = Angle.degrees(entity.dxf.start_angle)
                end_angle = Angle.degrees(entity.dxf.end_angle)
                if end_angle < start_angle:
                    end_angle += Angle.turns(1)
                element = Path(circ.arc_angle(start_angle,
                                              end_angle))
            elif entity.dxftype() == 'ELLIPSE':

                # TODO: needs more math, axis is vector, ratio is to minor.
                element = Ellipse(center=entity.dxf.center,
                                  # major axis is vector
                                  # ratio is the ratio of major to minor.
                                  start_point=entity.start_point,
                                  end_point=entity.end_point,
                                  start_angle=entity.dxf.start_param,
                                  end_angle=entity.dxf.end_param)
            elif entity.dxftype() == 'LINE':
                #  https://ezdxf.readthedocs.io/en/stable/dxfentities/line.html
                element = SimpleLine(x1=entity.dxf.start[0], y1=entity.dxf.start[1],
                                     x2=entity.dxf.end[0], y2=entity.dxf.end[1])
            elif entity.dxftype() == 'POLYLINE':
                # https://ezdxf.readthedocs.io/en/stable/dxfentities/lwpolyline.html
                if entity.is_2d_polyline:
                    if not entity.has_arc:
                        if entity.is_closed:
                            element = Polygon([(p[0], p[1]) for p in entity.points()])
                        else:
                            element = Polyline([(p[0], p[1]) for p in entity.points()])
                    else:
                        element = Path()
                        bulge = 0
                        for e in entity:
                            point = e.dxf.location
                            if bulge == 0:
                                element.line((point[0], point[1]))
                            else:
                                element += Arc(start=element.current_point,
                                                end=(point[0], point[1]),
                                                bulge=bulge)
                            bulge = e.dxf.bulge
                        if entity.is_closed:
                            if bulge == 0:
                                element.closed()
                            else:
                                element += Arc(start=element.current_point,
                                                end=element.z_point,
                                                bulge=bulge)
                                element.closed()
            elif entity.dxftype() == 'LWPOLYLINE':
                # https://ezdxf.readthedocs.io/en/stable/dxfentities/lwpolyline.html
                if not entity.has_arc:
                    if entity.closed:
                        element = Polygon(*[(p[0], p[1]) for p in entity])
                    else:
                        element = Polyline(*[(p[0], p[1]) for p in entity])
                else:
                    element = Path()
                    bulge = 0
                    for e in entity:
                        if bulge == 0:
                            element.line((e[0], e[1]))
                        else:
                            element += Arc(start=element.current_point,
                                            end=(e[0], e[1]),
                                            bulge=bulge)
                        bulge = e[4]
                    if entity.closed:
                        if bulge == 0:
                            element.closed()
                        else:
                            element += Arc(start=element.current_point,
                                            end=element.z_point,
                                            bulge=bulge)
                            element.closed()
            elif entity.dxftype() == 'HATCH':
                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html
                element = Path()
                if entity.bgcolor is not None:
                    Path.fill = Color(entity.bgcolor)
                for p in entity.paths:
                    if p.path_type_flags & 2:
                        for v in p.vertices:
                            element.line(v[0], v[1])
                        if p.is_closed:
                            element.closed()
                    else:
                        for e in p.edges:
                            if type(e) == "LineEdge":
                                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html#ezdxf.entities.LineEdge
                                element.line(e.start, e.end)
                            elif type(e) == "ArcEdge":
                                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html#ezdxf.entities.ArcEdge
                                circ = Circle(center=e.center,
                                              radius=e.radius, )
                                element += circ.arc_angle(Angle.degrees(e.start_angle), Angle.degrees(e.end_angle))
                            elif type(e) == "EllipseEdge":
                                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html#ezdxf.entities.EllipseEdge
                                element += Arc(radius=e.radius,
                                               start_angle=Angle.degrees(e.start_angle),
                                               end_angle=Angle.degrees(e.end_angle),
                                               ccw=e.is_counter_clockwise)
                            elif type(e) == "SplineEdge":
                                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html#ezdxf.entities.SplineEdge
                                if e.degree == 3:
                                    for i in range(len(e.knot_values)):
                                        control = e.control_values[i]
                                        knot = e.knot_values[i]
                                        element.quad(control, knot)
                                elif e.degree == 4:
                                    for i in range(len(e.knot_values)):
                                        control1 = e.control_values[2 * i]
                                        control2 = e.control_values[2 * i + 1]
                                        knot = e.knot_values[i]
                                        element.cubic(control1, control2, knot)
                                else:
                                    for i in range(len(e.knot_values)):
                                        knot = e.knot_values[i]
                                        element.line(knot)
            elif entity.dxftype() == 'IMAGE':
                bottom_left_position = entity.dxf.insert
                size = entity.dxf.image_size
                imagedef = entity.dxf.image_def_handle
                if not isinstance(imagedef, str):
                    imagedef = imagedef.filename
                element = SVGImage(href=imagedef,
                                   x=bottom_left_position[0],
                                   y=bottom_left_position[1] - size[1],
                                   width=size[0],
                                   height=size[1])
            elif entity.dxftype() == 'MTEXT':
                insert = entity.dxf.insert
                element = SVGText(x=insert[0], y=insert[1], text=entity.text)
            elif entity.dxftype() == 'TEXT':
                insert = entity.dxf.insert
                element = SVGText(x=insert[0], y=insert[1], text=entity.dxf.text)
            elif entity.dxftype() == 'SOLID' or entity.dxftype() == 'TRACE':
                # https://ezdxf.readthedocs.io/en/stable/dxfentities/solid.html
                element = Path()
                element.move((entity[0][0], entity[0][1]))
                element.line((entity[1][0], entity[1][1]))
                element.line((entity[2][0], entity[2][1]))
                element.line((entity[3][0], entity[3][1]))
                element.closed()
                element.fill = Color('Black')
            elif entity.dxftype() == 'SPLINE':
                element = Path()
                try:
                    for b in entity.construction_tool().bezier_decomposition():
                        if len(element) == 0:
                            element.move((b[0][0], b[0][1]))
                        element.cubic(
                            (b[1][0], b[1][1]),
                            (b[2][0], b[2][1]),
                            (b[3][0], b[3][1])
                        )
                except (AttributeError, TypeError):
                    # Fallback for versions of EZDXF prior to 0.13
                    element.move(entity.control_points[0])
                    for i in range(1, entity.dxf.n_control_points):
                        element.line(entity.control_points[i])
                if entity.closed:
                    element.closed()
            else:
                continue
                # Might be something unsupported.
            if entity.rgb is not None:
                element.stroke = Color(entity.rgb)
            else:
                element.stroke = Color('black')
            element.transform.post_scale(MILS_PER_MM, -MILS_PER_MM)
            element.transform.post_translate_y(context.bed_height * MILS_PER_MM)
            if isinstance(element, SVGText):
                elements.append(element)
            else:
                path = abs(Path(element))
                if len(path) != 0:
                    if not isinstance(path[0], Move):
                        path = Move(path.first_point) + path
                elements.append(path)

        return elements, None, None, pathname, basename
