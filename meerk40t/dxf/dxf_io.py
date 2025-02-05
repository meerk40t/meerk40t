import os.path

import ezdxf
from ezdxf import units

from ..core.exceptions import BadFileError
from ..core.units import UNITS_PER_INCH, UNITS_PER_MM

try:
    # ezdxf <= 0.6.14
    from ezdxf.tools.rgb import DXF_DEFAULT_COLORS, int2rgb
except ImportError:
    # ezdxf > 0.6.14
    from ezdxf import int2rgb
    from ezdxf.colors import DXF_DEFAULT_COLORS

from ezdxf.units import decode

from ..svgelements import (
    SVG_ATTR_VECTOR_EFFECT,
    SVG_VALUE_NON_SCALING_STROKE,
    Angle,
    Arc,
    Circle,
    Color,
    Ellipse,
    Matrix,
    Move,
    Path,
    Point,
    Polygon,
    Polyline,
    Viewbox,
)
from meerk40t.tools.geomstr import Geomstr

class DxfLoader:
    @staticmethod
    def load_types():
        yield "Drawing Exchange Format", ("dxf",), "image/vnd.dxf"

    @staticmethod
    def load(kernel, elements_service, pathname, **kwargs):
        """
        Load dxf content. Requires ezdxf which tends to also require Python 3.6 or greater.

        Dxf data has an origin point located in the lower left corner. +y -> top
        """
        try:
            dxf = ezdxf.readfile(pathname)
        except ezdxf.DXFError:
            try:
                # dxf is low quality. Attempt recovery.
                from ezdxf import recover

                dxf, auditor = recover.readfile(pathname)
            except ezdxf.DXFStructureError as e:
                # Recovery failed, return the BadFileError.
                raise BadFileError(str(e)) from e

        unit = dxf.header.get("$INSUNITS")
        if unit is not None and unit != 0:
            du = units.DrawingUnits(UNITS_PER_INCH, unit="in")
            scale = du.factor(decode(unit))
        else:
            scale = UNITS_PER_MM

        dxf_processor = DXFProcessor(elements_service, dxf=dxf, scale=scale)
        dxf_processor.process(dxf.entities, pathname)
        return True


class DXFProcessor:
    def __init__(self, elements_modifier, dxf, scale=1.0):
        self.elements = elements_modifier
        self.dxf = dxf
        self.scale = scale
        self.elements_list = list()
        self.reverse = False
        self.requires_classification = True
        self.pathname = None
        self.try_unsupported = True
        # Path stroke width
        self.std_stroke = 1000

    def process(self, entities, pathname):
        self.pathname = pathname
        # basename = os.path.basename(pathname)
        context_node = self.elements.get(type="branch elems")
        file_node = context_node.add(type="file", filepath=pathname)
        file_node.focus()
        for entity in entities:
            self.parse(entity, file_node, self.elements_list)
        dxf_center = self.elements.setting(bool, "dxf_center", True)
        self.try_unsupported = self.elements.setting(bool, "dxf_try_unsupported", True)
        if dxf_center:
            bbox = file_node.bounds
            if bbox is not None:
                view = self.elements.device.view
                bw = view.unit_width
                bh = view.unit_height
                bx = 0
                by = 0
                x = bbox[0]
                y = bbox[1]
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                if w == 0:
                    w = 1
                if h == 0:
                    h = 1
                if w > view.unit_width or h > view.unit_height:
                    # Cannot fit to bed. Scale.
                    bb = Viewbox(f"{x} {y} {w} {h}", preserve_aspect_ratio="xMidyMid")
                    matrix = bb.transform(Viewbox(bx, by, bw, bh))
                    for node in self.elements_list:
                        node.matrix *= matrix
                        node.modified()
                elif x < bx or y < by or x + w > bw or y + h > bh:
                    # Is outside the bed but sized correctly, center
                    bcx = bw / 2.0
                    bcy = bh / 2.0
                    cx = (bbox[0] + bbox[2]) / 2.0
                    cy = (bbox[1] + bbox[3]) / 2.0
                    matrix = Matrix.translate(bcx - cx, bcy - cy)
                    for node in self.elements_list:
                        node.matrix *= matrix
                        node.modified()
                # else, is within the bed dimensions correctly, change nothing.
        if self.elements.classify_new:
            self.elements.classify(self.elements_list)
        return True

    def check_for_attributes(self, node, entity):
        dxf = self.dxf
        if entity.rgb is not None:
            if isinstance(entity.rgb, tuple):
                node.stroke = Color(*entity.rgb)
            else:
                node.stroke = Color(entity.rgb)
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
            node.stroke = color

    def parse(self, entity, context_node, e_list):
        def full_ellipse(enti):
            tolerance = 1E-4
            if (
                abs(entity.start_point[0] - entity.end_point[0]) < tolerance and
                abs(entity.start_point[1] - entity.end_point[1]) < tolerance and
                abs(entity.dxf.start_param + entity.dxf.end_param) < tolerance
            ):
                return True
            return False

        if hasattr(entity, "transform_to_wcs"):
            try:
                entity.transform_to_wcs(entity.ocs())
            except AttributeError:
                pass
        print (f"Entity: {entity}")
        if hasattr(entity, "dxf"):
            for key in dir(entity.dxf):
                if key.startswith("_"):
                    continue
                try:
                    prop = getattr(entity.dxf, key)
                    print (f"dxf.{key}={prop}")
                except AttributeError:
                    pass
        if entity.dxftype() == "CIRCLE":
            m = Matrix()
            m.post_scale(self.scale, -self.scale)
            m.post_translate_y(self.elements.device.view.unit_height)
            try:
                cx, cy = entity.dxf.center
            except ValueError:
                # 3d center.
                cx, cy, cz = entity.dxf.center
            node = context_node.add(
                cx=cx,
                cy=cy,
                rx=entity.dxf.radius,
                ry=entity.dxf.radius,
                matrix=m,
                stroke_scale=False,
                stroke_width=self.std_stroke,
                type="elem ellipse",
            )
            self.check_for_attributes(node, entity)
            e_list.append(node)
            return
        elif entity.dxftype() == "ARC":
            # TODO: Ellipse used to make circ.arc_angle path.
            circ = Ellipse(center=entity.dxf.center, r=entity.dxf.radius)
            start_angle = Angle.degrees(entity.dxf.start_angle)
            end_angle = Angle.degrees(entity.dxf.end_angle)
            if end_angle < start_angle:
                end_angle += Angle.turns(1)
            element = Path(circ.arc_angle(start_angle, end_angle))
            element.values[SVG_ATTR_VECTOR_EFFECT] = SVG_VALUE_NON_SCALING_STROKE
            element.transform.post_scale(self.scale, -self.scale)
            element.transform.post_translate_y(self.elements.device.view.unit_height)
            path = abs(Path(element))
            if len(path) != 0:
                if not isinstance(path[0], Move):
                    path = Move(path.first_point) + path
                path.approximate_arcs_with_cubics()
            node = context_node.add(
                path=path,
                type="elem path",
                stroke_scale=False,
                stroke_width=self.std_stroke,
            )
            self.check_for_attributes(node, entity)
            e_list.append(node)
            return
        elif entity.dxftype() == "ELLIPSE":
            # TODO: needs more math, axis is vector, ratio is to minor.
            # major axis is vector
            # ratio is the ratio of major to minor.
            if full_ellipse(entity):
                element = Ellipse(
                    cx = entity.dxf.center[0],
                    cy = entity.dxf.center[1],
                    rx = entity.minor_axis[0],
                    ry = entity.dxf.major_axis[1],
                )
            else:
                element = Ellipse(
                    center=entity.dxf.center,
                    start_point=entity.start_point,
                    end_point=entity.end_point,
                    start_angle=entity.dxf.start_param,
                    end_angle=entity.dxf.end_param,
                )
            element.values[SVG_ATTR_VECTOR_EFFECT] = SVG_VALUE_NON_SCALING_STROKE
            element.transform.post_scale(self.scale, -self.scale)
            element.transform.post_translate_y(self.elements.device.view.unit_height)
            node = context_node.add(
                shape=element,
                type="elem ellipse",
                stroke_scale=False,
                stroke_width=self.std_stroke,
            )
            self.check_for_attributes(node, entity)
            e_list.append(node)
            return
        elif entity.dxftype() == "LINE":
            #  https://ezdxf.readthedocs.io/en/stable/dxfentities/line.html
            m = Matrix()
            m.post_scale(self.scale, -self.scale)
            m.post_translate_y(self.elements.device.view.unit_height)
            node = context_node.add(
                x1=entity.dxf.start[0],
                y1=entity.dxf.start[1],
                x2=entity.dxf.end[0],
                y2=entity.dxf.end[1],
                stroke_scale=False,
                stroke_width=self.std_stroke,
                matrix=m,
                type="elem line",
            )
            self.check_for_attributes(node, entity)
            e_list.append(node)
            return
        elif entity.dxftype() == "POINT":
            pos = entity.dxf.location
            if len(pos) == 2:
                x, y = pos
            else:
                x, y, z = pos
            node = context_node.add(x=x, y=y, matrix=Matrix(), type="elem point")
            self.check_for_attributes(node, entity)
            e_list.append(node)
            return
        elif entity.dxftype() == "POLYLINE":
            # https://ezdxf.readthedocs.io/en/stable/dxfentities/polyline.html
            supported = entity.is_2d_polyline
            if not supported:
                # for _att in dir(entity):
                #     if hasattr(entity, _att):
                #         print (f"{_att}: {getattr(entity, _att, '')}")
                if self.try_unsupported:
                    supported = True
            if supported:
                if not entity.has_arc:
                    if entity.is_closed:
                        element = Polygon([(p[0], p[1]) for p in entity.points()])
                    else:
                        element = Polyline([(p[0], p[1]) for p in entity.points()])
                    element.values[
                        SVG_ATTR_VECTOR_EFFECT
                    ] = SVG_VALUE_NON_SCALING_STROKE
                    element.transform.post_scale(self.scale, -self.scale)
                    element.transform.post_translate_y(
                        self.elements.device.view.unit_height
                    )
                    node = context_node.add(
                        shape=element,
                        type="elem polyline",
                        stroke_scale=False,
                        stroke_width=self.std_stroke,
                    )
                    self.check_for_attributes(node, entity)
                    e_list.append(node)
                    return
                else:
                    element = Path()
                    bulge = 0
                    for idx, e in enumerate(entity):
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
                    element.values[
                        SVG_ATTR_VECTOR_EFFECT
                    ] = SVG_VALUE_NON_SCALING_STROKE
                    element.transform.post_scale(self.scale, -self.scale)
                    element.transform.post_translate_y(
                        self.elements.device.view.unit_height
                    )
                    path = abs(Path(element))
                    if len(path) != 0:
                        if not isinstance(path[0], Move):
                            path = Move(path.first_point) + path
                        path.approximate_arcs_with_cubics()
                    node = context_node.add(
                        path=path,
                        type="elem path",
                        stroke_scale=False,
                        stroke_width=self.std_stroke,
                    )
                    self.check_for_attributes(node, entity)
                    e_list.append(node)
                    return
        elif entity.dxftype() == "LWPOLYLINE":
            # https://ezdxf.readthedocs.io/en/stable/dxfentities/lwpolyline.html
            if not entity.has_arc:
                if entity.closed:
                    element = Polygon(*[(p[0], p[1]) for p in entity])
                else:
                    element = Polyline(*[(p[0], p[1]) for p in entity])
                element.values[SVG_ATTR_VECTOR_EFFECT] = SVG_VALUE_NON_SCALING_STROKE
                element.transform.post_scale(self.scale, -self.scale)
                element.transform.post_translate_y(
                    self.elements.device.view.unit_height
                )
                node = context_node.add(
                    shape=element,
                    type="elem polyline",
                    stroke_scale=False,
                    stroke_width=self.std_stroke,
                )
                self.check_for_attributes(node, entity)
                e_list.append(node)
                return
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
                element.values[SVG_ATTR_VECTOR_EFFECT] = SVG_VALUE_NON_SCALING_STROKE
                element.transform.post_scale(self.scale, -self.scale)
                element.transform.post_translate_y(
                    self.elements.device.view.unit_height
                )
                path = abs(Path(element))
                if len(path) != 0:
                    if not isinstance(path[0], Move):
                        path = Move(path.first_point) + path
                    path.approximate_arcs_with_cubics()
                node = context_node.add(
                    path=path,
                    type="elem path",
                    stroke_scale=False,
                    stroke_width=self.std_stroke,
                )
                self.check_for_attributes(node, entity)
                e_list.append(node)
                return
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
            element.values[SVG_ATTR_VECTOR_EFFECT] = SVG_VALUE_NON_SCALING_STROKE
            element.transform.post_scale(self.scale, -self.scale)
            element.transform.post_translate_y(self.elements.device.view.unit_height)
            path = abs(Path(element))
            if len(path) != 0:
                if not isinstance(path[0], Move):
                    path = Move(path.first_point) + path
                path.approximate_arcs_with_cubics()
            node = context_node.add(
                path=path,
                type="elem path",
                stroke_scale=False,
                stroke_width=self.std_stroke,
            )
            self.check_for_attributes(node, entity)
            e_list.append(node)
            return
        elif entity.dxftype() == "IMAGE":
            bottom_left_position = entity.dxf.insert
            targetmatrix = Matrix()
            targetmatrix.post_scale(self.scale, -self.scale)
            targetmatrix.post_translate_y(self.elements.device.view.unit_height)
            # So what's our targetposition then?
            targetpos = targetmatrix.point_in_matrix_space(
                Point(bottom_left_position[0], bottom_left_position[1])
            )

            size_img = entity.dxf.image_size
            w_scale = entity.dxf.u_pixel[0]
            h_scale = entity.dxf.v_pixel[1]
            size = (size_img[0] * w_scale, size_img[1] * h_scale)
            imagedef = entity.image_def
            fname1 = imagedef.dxf.filename
            fname2 = os.path.normpath(
                os.path.join(os.path.dirname(self.pathname), fname1)
            )
            candidates = [
                fname1,
                fname2,
            ]
            # LibreCad 2.2 has a bug - it stores the relative path with a '../' too few
            # So let's add another option
            if fname1.startswith("../"):
                fname1 = "../" + fname1
                fname2 = os.path.normpath(
                    os.path.join(os.path.dirname(self.pathname), fname1)
                )
                candidates.append(fname1)
                candidates.append(fname2)

            was_found = False
            for filename in candidates:
                if not os.path.exists(filename) or os.path.isdir(filename):
                    continue
                was_found = True
                break
            if not was_found:
                return

            x_pos = bottom_left_position[0]
            y_pos = bottom_left_position[1]
            dxf_units_per_inch = self.scale / UNITS_PER_INCH
            width_in_inches = size[0] * dxf_units_per_inch
            height_in_inches = size[1] * dxf_units_per_inch
            dpix = size_img[0] / width_in_inches
            dpiy = size_img[1] / height_in_inches

            # Node.matrix is primary transformation.
            matrix = Matrix()
            matrix.post_scale(1, -1)
            matrix.post_translate_x(x_pos)
            matrix.post_translate_y(y_pos)
            matrix.post_scale(self.scale, -self.scale)
            matrix.post_translate_y(self.elements.device.view.unit_height)
            try:
                node = context_node.add(
                    href=filename,
                    width=size[0],
                    height=size[1],
                    dpi=dpix,
                    matrix=matrix,
                    type="elem image",
                )
            except FileNotFoundError:
                return
            try:
                from PIL import ImageOps

                node.image = ImageOps.exif_transpose(node.image)
            except ImportError:
                pass
            self.check_for_attributes(node, entity)
            # We don't seem to get the position right, so let's look
            # at our bottom_left position again and fix the gap
            bb = node.bounds
            dx = targetpos.x - bb[0]
            dy = targetpos.y - bb[3]
            if dx != 0:
                node.matrix.post_translate_x(dx)
            if dy != 0:
                node.matrix.post_translate_y(dy)
            e_list.append(node)
            return
        elif entity.dxftype() == "MTEXT":
            insert = entity.dxf.insert
            node = context_node.add(
                text=entity.text,
                x=insert[0],
                y=insert[1],
                stroke_scaled=False,
                type="elem text",
            )
            node.matrix.post_scale(1, -1, insert[0], insert[1])
            node.matrix.post_scale(self.scale, -self.scale)
            node.matrix.post_translate_y(self.elements.device.view.unit_height)

            self.check_for_attributes(node, entity)
            e_list.append(node)
            return
        elif entity.dxftype() == "TEXT":
            insert = entity.dxf.insert
            node = context_node.add(
                text=entity.dxf.text,
                x=insert[0],
                y=insert[1],
                stroke_scaled=False,
                type="elem text",
            )
            node.matrix.post_scale(1, -1, insert[0], insert[1])
            node.matrix.post_scale(self.scale, -self.scale)
            node.matrix.post_translate_y(self.elements.device.view.unit_height)
            self.check_for_attributes(node, entity)
            e_list.append(node)
            return
        elif entity.dxftype() == "SOLID" or entity.dxftype() == "TRACE":
            # https://ezdxf.readthedocs.io/en/stable/dxfentities/solid.html
            element = Path()
            element.move((entity[0][0], entity[0][1]))
            element.line((entity[1][0], entity[1][1]))
            element.line((entity[2][0], entity[2][1]))
            element.line((entity[3][0], entity[3][1]))
            element.closed()
            element.fill = Color("black")
            element.values[SVG_ATTR_VECTOR_EFFECT] = SVG_VALUE_NON_SCALING_STROKE
            element.transform.post_scale(self.scale, -self.scale)
            element.transform.post_translate_y(self.elements.device.view.unit_height)

            path = abs(Path(element))
            node = context_node.add(
                path=path,
                type="elem path",
                stroke_scale=False,
                stroke_width=self.std_stroke,
            )
            self.check_for_attributes(node, entity)
            e_list.append(node)
            return
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
                    # Flattening version 0.15
                    for q in entity.flattening(1, 15):
                        element.line((q[0], q[1]))
                except AttributeError:
                    # Version before 0.15
                    try:
                        for (
                            bezier
                        ) in entity.construction_tool().cubic_bezier_approximation(4):
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
            element.values[SVG_ATTR_VECTOR_EFFECT] = SVG_VALUE_NON_SCALING_STROKE
            element.transform.post_scale(self.scale, -self.scale)
            element.transform.post_translate_y(self.elements.device.view.unit_height)
            path = abs(element)
            if len(path) != 0:
                if not isinstance(path[0], Move):
                    path = Move(path.first_point) + path
            node = context_node.add(
                path=path,
                type="elem path",
                stroke_scale=False,
                stroke_width=self.std_stroke,
            )
            self.check_for_attributes(node, entity)
            e_list.append(node)
            return
        elif entity.dxftype() == "INSERT":
            # Insert creates virtual grouping.
            context_node = context_node.add(type="group")
            for e in entity.virtual_entities():
                if e is None:
                    continue
                self.parse(e, context_node, e_list)
            return
        else:
            # We need a channel comment here so that this is not silently ignored.
            return  # Might be something unsupported.
