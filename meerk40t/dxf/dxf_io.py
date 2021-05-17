import os

import ezdxf
from ezdxf import units
from ezdxf.tools.rgb import DXF_DEFAULT_COLORS, int2rgb
from ezdxf.units import decode

from ..svgelements import (
    SVG_ATTR_VECTOR_EFFECT,
    SVG_VALUE_NON_SCALING_STROKE,
    Angle,
    Arc,
    Circle,
    Color,
    Ellipse,
    Group,
    Matrix,
    Move,
    Path,
    Polygon,
    Polyline,
    SimpleLine,
    SVGImage,
    SVGText,
    Viewbox,
)

MILS_PER_MM = 39.3701


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("load/DxfLoader", DxfLoader)


class DxfLoader:
    @staticmethod
    def load_types():
        yield "Drawing Exchange Format", ("dxf",), "image/vnd.dxf"

    @staticmethod
    def load(kernel, elements_modifier, pathname, **kwargs):
        """ "
        Load dxf content. Requires ezdxf which tends to also require Python 3.6 or greater.

        Dxf data has an origin point located in the lower left corner. +y -> top
        """
        bed_dim = kernel.get_context("/")
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)

        dxf = ezdxf.readfile(pathname)
        elements = []
        unit = dxf.header.get("$INSUNITS")

        if unit is not None and unit != 0:
            du = units.DrawingUnits(1000.0, unit="in")
            scale = du.factor(decode(unit))
        else:
            scale = MILS_PER_MM

        for entity in dxf.entities:
            DxfLoader.entity_to_svg(
                elements, dxf, entity, scale, bed_dim.bed_height * MILS_PER_MM
            )

        kernel.setting(bool, "dxf_center", True)
        if kernel.dxf_center:
            g = Group()
            g.extend(elements)
            bbox = g.bbox()
            if bbox is not None:
                bw = bed_dim.bed_width * MILS_PER_MM
                bh = bed_dim.bed_height * MILS_PER_MM
                bx = 0
                by = 0
                x = bbox[0]
                y = bbox[1]
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                if w > bw or h > bh:
                    # Cannot fit to bed. Scale.
                    vb = Viewbox("%f %f %f %f" % (bx, by, bw, bh))
                    bb = Viewbox(
                        "%f %f %f %f" % (x, y, w, h), preserve_aspect_ratio="xMidyMid"
                    )
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
        element_branch = elements_modifier.get(type="branch elems")
        basename = os.path.basename(pathname)

        file_node = element_branch.add(type="file", name=basename)
        file_node.filepath = pathname
        file_node.add_all(elements, type="elem")

        elements_modifier.classify(elements)
        return True

    @staticmethod
    def entity_to_svg(elements, dxf, entity, scale, translate_y):
        element = None
        try:
            entity.transform_to_wcs(entity.ocs())
        except AttributeError:
            pass
        if entity.dxftype() == "CIRCLE":
            element = Circle(center=entity.dxf.center, r=entity.dxf.radius)
        elif entity.dxftype() == "ARC":
            circ = Circle(center=entity.dxf.center, r=entity.dxf.radius)
            start_angle = Angle.degrees(entity.dxf.start_angle)
            end_angle = Angle.degrees(entity.dxf.end_angle)
            if end_angle < start_angle:
                end_angle += Angle.turns(1)
            element = Path(circ.arc_angle(start_angle, end_angle))
        elif entity.dxftype() == "ELLIPSE":

            # TODO: needs more math, axis is vector, ratio is to minor.
            element = Ellipse(
                center=entity.dxf.center,
                # major axis is vector
                # ratio is the ratio of major to minor.
                start_point=entity.start_point,
                end_point=entity.end_point,
                start_angle=entity.dxf.start_param,
                end_angle=entity.dxf.end_param,
            )
        elif entity.dxftype() == "LINE":
            #  https://ezdxf.readthedocs.io/en/stable/dxfentities/line.html
            element = SimpleLine(
                x1=entity.dxf.start[0],
                y1=entity.dxf.start[1],
                x2=entity.dxf.end[0],
                y2=entity.dxf.end[1],
            )
        elif entity.dxftype() == "POINT":
            element = Path(Move(entity.dxf.location)) + "z"
        elif entity.dxftype() == "POLYLINE":
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
                            element += Arc(
                                start=element.current_point,
                                end=(point[0], point[1]),
                                bulge=bulge,
                            )
                        bulge = e.dxf.bulge
                    if entity.is_closed:
                        if bulge == 0:
                            element.closed()
                        else:
                            element += Arc(
                                start=element.current_point,
                                end=element.z_point,
                                bulge=bulge,
                            )
                            element.closed()
        elif entity.dxftype() == "LWPOLYLINE":
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
                        element += Arc(
                            start=element.current_point, end=(e[0], e[1]), bulge=bulge
                        )
                    bulge = e[4]
                if entity.closed:
                    if bulge == 0:
                        element.closed()
                    else:
                        element += Arc(
                            start=element.current_point,
                            end=element.z_point,
                            bulge=bulge,
                        )
                        element.closed()
        elif entity.dxftype() == "HATCH":
            # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html
            element = Path()
            if entity.bgcolor is not None:
                Path.fill = Color(*entity.bgcolor)
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
                            circ = Circle(
                                center=e.center,
                                radius=e.radius,
                            )
                            element += circ.arc_angle(
                                Angle.degrees(e.start_angle), Angle.degrees(e.end_angle)
                            )
                        elif type(e) == "EllipseEdge":
                            # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html#ezdxf.entities.EllipseEdge
                            element += Arc(
                                radius=e.radius,
                                start_angle=Angle.degrees(e.start_angle),
                                end_angle=Angle.degrees(e.end_angle),
                                ccw=e.is_counter_clockwise,
                            )
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
        elif entity.dxftype() == "IMAGE":
            bottom_left_position = entity.dxf.insert
            size = entity.dxf.image_size
            imagedef = entity.dxf.image_def_handle
            if not isinstance(imagedef, str):
                imagedef = imagedef.filename
            element = SVGImage(
                href=imagedef,
                x=bottom_left_position[0],
                y=bottom_left_position[1] - size[1],
                width=size[0],
                height=size[1],
            )
        elif entity.dxftype() == "MTEXT":
            insert = entity.dxf.insert
            element = SVGText(x=insert[0], y=insert[1], text=entity.text)
        elif entity.dxftype() == "TEXT":
            insert = entity.dxf.insert
            element = SVGText(x=insert[0], y=insert[1], text=entity.dxf.text)
        elif entity.dxftype() == "SOLID" or entity.dxftype() == "TRACE":
            # https://ezdxf.readthedocs.io/en/stable/dxfentities/solid.html
            element = Path()
            element.move((entity[0][0], entity[0][1]))
            element.line((entity[1][0], entity[1][1]))
            element.line((entity[2][0], entity[2][1]))
            element.line((entity[3][0], entity[3][1]))
            element.closed()
            element.fill = Color("black")
        elif entity.dxftype() == "SPLINE":
            element = Path()
            try:
                for b in entity.construction_tool().bezier_decomposition():
                    if len(element) == 0:
                        element.move((b[0][0], b[0][1]))
                    if len(b) == 4:
                        element.cubic(
                            (b[1][0], b[1][1]), (b[2][0], b[2][1]), (b[3][0], b[3][1])
                        )
                    elif len(b) == 3:
                        element.quad((b[1][0], b[1][1]), (b[2][0], b[2][1]))
            except (AttributeError, TypeError):
                # Fallback for rational b-splines.
                try:
                    for bezier in entity.construction_tool().cubic_bezier_approximation(
                        4
                    ):
                        b = bezier.control_points
                        if len(b) == 4:
                            element.cubic(
                                (b[1][0], b[1][1]),
                                (b[2][0], b[2][1]),
                                (b[3][0], b[3][1]),
                            )
                        elif len(b) == 3:
                            element.quad((b[1][0], b[1][1]), (b[2][0], b[2][1]))
                except (AttributeError, TypeError):
                    # Fallback for versions of EZDXF prior to 0.13
                    element.move(entity.control_points[0])
                    for i in range(1, entity.dxf.n_control_points):
                        element.line(entity.control_points[i])
            if entity.closed:
                element.closed()
        elif entity.dxftype() == "INSERT":
            for e in entity.virtual_entities():
                if e is None:
                    continue
                DxfLoader.entity_to_svg(elements, dxf, e, scale, translate_y)
            return
        else:
            return  # Might be something unsupported.

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
                    color = Color(
                        "black"
                    )  # Color 7 is black on light backgrounds, light on black.
                else:
                    color = Color(*int2rgb(DXF_DEFAULT_COLORS[c]))
            except Exception:
                color = Color("black")
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
