import os
from base64 import b64encode
from io import BytesIO
from xml.etree.cElementTree import Element, ElementTree, SubElement

from LaserOperation import LaserOperation
from svgelements import *

MILS_PER_MM = 39.3701


class SVGWriter:
    @staticmethod
    def save_types():
        yield "Scalable Vector Graphics", "svg", "image/svg+xml"

    @staticmethod
    def versions():
        yield 'default'

    @staticmethod
    def save(device, f, version='default'):
        root = Element(SVG_NAME_TAG)
        root.set(SVG_ATTR_VERSION, SVG_VALUE_VERSION)
        root.set(SVG_ATTR_XMLNS, SVG_VALUE_XMLNS)
        root.set(SVG_ATTR_XMLNS_LINK, SVG_VALUE_XLINK)
        root.set(SVG_ATTR_XMLNS_EV, SVG_VALUE_XMLNS_EV)
        root.set("xmlns:meerK40t", "https://htmlpreview.github.io/?https://github.com/meerk40t/meerk40t/blob/patch-2/svg-namespace.html")
        # Native unit is mils, these must convert to mm and to px
        mils_per_mm = 39.3701
        mils_per_px = 1000.0 / 96.0
        px_per_mils = 96.0 / 1000.0
        device.setting(int, "bed_width", 310)
        device.setting(int, "bed_height", 210)
        mm_width = device.bed_width
        mm_height = device.bed_height
        root.set(SVG_ATTR_WIDTH, '%fmm' % mm_width)
        root.set(SVG_ATTR_HEIGHT, '%fmm' % mm_height)
        px_width = mm_width * mils_per_mm * px_per_mils
        px_height = mm_height * mils_per_mm * px_per_mils

        viewbox = '%d %d %d %d' % (0, 0, round(px_width), round(px_height))
        scale = 'scale(%f)' % px_per_mils
        root.set(SVG_ATTR_VIEWBOX, viewbox)
        elements = device.elements
        for operation in elements.ops():
            subelement = SubElement(root, "operation")
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
                element = abs(element)
                subelement = SubElement(root, SVG_TAG_PATH)
                subelement.set(SVG_ATTR_DATA, element.d(transformed=False))
                subelement.set(SVG_ATTR_TRANSFORM, scale)
                if element.values is not None:
                    for key, val in element.values.items():
                        if key in ('speed', 'overscan', 'power', 'passes',
                                   'raster_direction', 'raster_step', 'd_ratio'):
                            subelement.set(key, str(val))
            elif isinstance(element, SVGText):
                subelement = SubElement(root, SVG_TAG_TEXT)
                subelement.text = element.text
                t = Matrix(element.transform)
                t *= scale
                subelement.set('transform', 'matrix(%f, %f, %f, %f, %f, %f)' % (t.a, t.b, t.c, t.d, t.e, t.f))
                if element.values is not None:
                    for key, val in element.values.items():
                        if key in ('speed', 'overscan', 'power', 'passes',
                                   'raster_direction', 'raster_step', 'd_ratio',
                                   'font-family', 'font_face', 'font-size', 'font-weight',
                                   'anchor', 'x', 'y'):
                            subelement.set(key, str(val))
            else:  # Image.
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
                if element.values is not None:
                    for key, val in element.values.items():
                        if key in ('speed', 'overscan', 'power', 'passes',
                                   'raster_direction', 'raster_step', 'd_ratio'):
                            subelement.set(key, str(val))
            stroke = element.stroke
            if stroke is not None:
                stroke_opacity = stroke.opacity
                stroke = str(abs(stroke)) if stroke is not None and stroke.value is not None else SVG_VALUE_NONE
                subelement.set(SVG_ATTR_STROKE, stroke)
                if stroke_opacity != 1.0 and stroke_opacity is not None:
                    subelement.set(SVG_ATTR_STROKE_OPACITY, str(stroke_opacity))
                try:
                    stroke_width = str(element.stroke_width) if element.stroke_width is not None else SVG_VALUE_NONE
                    subelement.set(SVG_ATTR_STROKE_WIDTH, stroke_width)
                except AttributeError:
                    pass
            fill = element.fill
            if fill is not None:
                fill_opacity = fill.opacity
                fill = str(abs(fill)) if fill is not None and fill.value is not None else SVG_VALUE_NONE
                subelement.set(SVG_ATTR_FILL, fill)
                if fill_opacity != 1.0 and fill_opacity is not None:
                    subelement.set(SVG_ATTR_FILL_OPACITY, str(fill_opacity))
                if element.id is not None:
                    subelement.set(SVG_ATTR_ID, str(element.id))
        tree = ElementTree(root)
        tree.write(f)


class SVGLoader:

    @staticmethod
    def load_types():
        yield "Scalable Vector Graphics", ("svg",), "image/svg+xml"

    @staticmethod
    def load(kernel, pathname, **kwargs):
        kernel.setting(int, "bed_width", 310)
        kernel.setting(int, "bed_height", 210)
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
                        width='%fmm' % (kernel.bed_width),
                        height='%fmm' % (kernel.bed_height),
                        reify=False,
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
                if element.text is not None:
                    elements.append(element)
            elif isinstance(element, Path):
                if len(element) != 0:
                    element.reify()
                    elements.append(element)
            elif isinstance(element, Shape):
                e = Path(element)
                e.reify()  # In some cases the shape could not have reified, the path must.
                if len(e) != 0:
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
    def load(kernel, pathname, **kwargs):
        basename = os.path.basename(pathname)

        image = SVGImage({'href': pathname, 'width': "100%", 'height': "100%", 'id': basename})
        image.load()
        try:
            kernel.setting(bool, 'image_dpi', True)
            if kernel.image_dpi:
                dpi = image.image.info['dpi']
                if isinstance(dpi, tuple):
                    image *= 'scale(%f,%f)' % (1000.0 / dpi[0], 1000.0 / dpi[1])
        except (KeyError, IndexError, AttributeError):
            pass
        return [image], None, None, pathname, basename


class DxfLoader:

    @staticmethod
    def load_types():
        yield "Drawing Exchange Format", ("dxf",), "image/vnd.dxf"

    @staticmethod
    def load(kernel, pathname, **kwargs):
        """"
        Load dxf content. Requires ezdxf which tends to also require Python 3.6 or greater.

        Dxf data has an origin point located in the lower left corner. +y -> top
        """
        kernel.setting(int, "bed_width", 310)
        kernel.setting(int, "bed_height", 210)

        import ezdxf
        from ezdxf import units
        from ezdxf.units import decode

        basename = os.path.basename(pathname)
        dxf = ezdxf.readfile(pathname)
        elements = []
        unit = dxf.header.get('$INSUNITS')

        if unit is not None and unit != 0:
            du = units.DrawingUnits(1000.0, unit='in')
            scale = du.factor(decode(unit))
        else:
            scale = MILS_PER_MM

        for entity in dxf.entities:
            DxfLoader.entity_to_svg(elements, dxf, entity, scale, kernel.bed_height * MILS_PER_MM)

        kernel.setting(bool, "dxf_center", True)
        if kernel.dxf_center:
            g = Group()
            g.extend(elements)
            bbox = g.bbox()
            if bbox is not None:
                bw = kernel.bed_width * MILS_PER_MM
                bh = kernel.bed_height * MILS_PER_MM
                bx = 0
                by = 0
                x = bbox[0]
                y = bbox[1]
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                if w > bw or h > bh:
                    # Cannot fit to bed. Scale.
                    vb = Viewbox("%f %f %f %f" % (bx, by, bw, bh))
                    bb = Viewbox("%f %f %f %f" % (x, y, w, h),
                                preserve_aspect_ratio="xMidyMid")
                    matrix = bb.transform(vb)
                    for e in elements:
                        e *= matrix
                elif x < bx or y < by or x + w > bw or y + h > bh:
                    # Is outside the bed but sized correctly, center
                    bcx = bw / 2.0
                    bcy = bh / 2.0
                    cx = (bbox[0] + bbox[2]) / 2.0
                    cy = (bbox[1] + bbox[3]) / 2.0
                    matrix = Matrix.translate(bcx - cx, bcy - cy)
                    for e in elements:
                        e *= matrix
                # else, is within the bed dimensions correctly, change nothing.
        for e in elements:
            try:
                e.reify()
            except AttributeError:
                pass
        return elements, None, None, pathname, basename

    @staticmethod
    def entity_to_svg(elements, dxf, entity, scale, translate_y):
        element = None
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
                # Fallback for rational b-splines.
                try:
                    for bezier in entity.construction_tool().cubic_bezier_approximation(4):
                        b = bezier.control_points
                        element.cubic(
                            (b[1][0], b[1][1]),
                            (b[2][0], b[2][1]),
                            (b[3][0], b[3][1]))
                except (AttributeError, TypeError):
                    # Fallback for versions of EZDXF prior to 0.13
                    element.move(entity.control_points[0])
                    for i in range(1, entity.dxf.n_control_points):
                        element.line(entity.control_points[i])
            if entity.closed:
                element.closed()
        elif entity.dxftype() == 'INSERT':
            for e in entity.virtual_entities():
                if e is None:
                    continue
                DxfLoader.entity_to_svg(elements, dxf, e, scale, translate_y)
            return
        else:
            return  # Might be something unsupported.

        from ezdxf.tools.rgb import DXF_DEFAULT_COLORS, int2rgb
        if entity.rgb is not None:
            if isinstance(entity.rgb, tuple):
                element.stroke = Color(*entity.rgb)
            else:
                element.stroke = Color(entity.rgb)
        else:
            c = entity.dxf.color
            if c == 256:  # Bylayer.
                if entity.dxf.layer in dxf.layers:
                    layer = dxf.layers.get(entity.dxf.layer)
                    c = layer.color
            try:
                if c == 7:
                    color = Color("black")  # Color 7 is black on light backgrounds, light on black.
                else:
                    color = Color(*int2rgb(DXF_DEFAULT_COLORS[c]))
            except:
                color = Color('black')
            element.stroke = color
        element.transform.post_scale(scale, -scale)
        element.transform.post_translate_y(translate_y)

        if isinstance(element, SVGText):
            elements.append(element)
        else:
            element.values[SVG_ATTR_VECTOR_EFFECT] = SVG_VALUE_NON_SCALING_STROKE
            path = abs(Path(element))
            if len(path) != 0:
                if not isinstance(path[0], Move):
                    path = Move(path.first_point) + path
            elements.append(path)
