from copy import copy

import wx
from numpy import linspace

from meerk40t.core.units import Length
from meerk40t.gui.icons import EmptyIcon, icons8_hinges_50
from meerk40t.gui.laserrender import LaserRender
from meerk40t.gui.mwindow import MWindow
from meerk40t.kernel import signal_listener
from meerk40t.svgelements import (
    Arc,
    Close,
    Color,
    CubicBezier,
    Line,
    Matrix,
    Move,
    Path,
    Point,
    Polygon,
    Polyline,
    QuadraticBezier,
)
from meerk40t.tools.pathtools import VectorMontonizer

_ = wx.GetTranslation

"""
TODO:
a) get rid of row / col range limitation and iterate until boundary exceeds frame
b) Fix circle arc invocation

"""


class LivingHinges:
    """
    This class generates a predefined pattern in a *rectangular* area
    """

    def __init__(self, xpos, ypos, width, height):
        self.pattern = None
        self.start_x = xpos
        self.start_y = ypos
        self.width = width
        self.height = height
        # We set it off somewhat...
        self.gap = 0
        self.x0 = width * self.gap
        self.y0 = height * self.gap
        self.x1 = width * (1 - self.gap)
        self.y1 = height * (1 - self.gap)
        # Declare all used variables to satisfy codacy
        self.param_a = 0
        self.param_b = 0
        self.cell_height_percentage = 20
        self.cell_width_percentage = 20
        self.cell_height = height * self.cell_height_percentage / 100
        self.cell_width = width * self.cell_width_percentage / 100
        self.cell_padding_v_percentage = 0
        self.cell_padding_h_percentage = 0
        self.cell_padding_h = self.cell_width * self.cell_padding_h_percentage / 100
        self.cell_padding_v = self.cell_height * self.cell_padding_v_percentage / 100
        # Requires recalculation
        self.path = None
        self.previewpath = None
        self.outershape = None
        self.pattern = []
        self.cutshape = ""
        self._defined_patterns = {}
        self._defined_patterns["line"] = (
            self.set_line,
            False,
            "",
            "",
            (-20, -35, 0, 0),
        )
        self._defined_patterns["fishbone"] = (
            self.set_fishbone,
            True,
            "Left/Right Indentation",
            "Bottom Indentation",
            (10, 10, 0, 0),
        )
        self._defined_patterns["diagonal"] = (
            self.set_diagonal,
            True,
            "Left/Right Indentation",
            "Top/Bottom Indentation",
            (-10, -10, 0, 0),
        )
        self._defined_patterns["diamond1"] = (
            self.set_diamond1,
            False,
            "",
            "",
            (-15, 10, 0, 0),
        )
        self._defined_patterns["diamond2"] = (
            self.set_diamond2,
            False,
            "",
            "",
            (-12, 6, 0, 0),
        )
        self._defined_patterns["cross"] = (
            self.set_cross,
            True,
            "Left/Right Indentation",
            "Top/Bottom Indentation",
            (-15, -4, 0, 0),
        )
        self._defined_patterns["bezier"] = (
            self.set_bezier,
            True,
            "",
            "",
            (-2, -16, 0.4, 0.3),
        )
        self._defined_patterns["wave"] = (self.set_wave, True, "", "", (-13, -26, 0, 0))
        self._defined_patterns["bowlingpin"] = (
            self.set_bowlingpin,
            True,
            "Left/right bowl",
            "Top/bottom bowl",
            (-21, -5, -0.3, 0),
        )
        self._defined_patterns["beehive"] = (
            self.set_beehive,
            True,
            "Position of left side",
            "Distance of second line",
            (-1, 6, 1.4, 0),
        )
        self._defined_patterns["fabric"] = (
            self.set_fabric,
            False,
            "",
            "",
            (-18, 13, 0, 0),
        )
        self._defined_patterns["brackets"] = (
            self.set_brackets,
            True,
            "",
            "",
            (-14, -11, 0.7, 0.7),
        )
        # self._defined_patterns["circle"] = (self.set_circle, True, "", "", (10, 10, 0.7, 0.7))

        self.set_cell_values(10, 10)
        self.set_padding_values(5, 5)
        self.set_predefined_pattern("line")

    def get_patterns(self):
        for entry in self._defined_patterns:
            yield entry, self._defined_patterns[entry][4]
        # yield "circle"

    def get_default(self, pattern):
        if pattern in self._defined_patterns:
            return self._defined_patterns[pattern][4]
        else:
            return (0, 0, 0, 0)

    def set_predefined_pattern(self, cutshape):
        # The pattern needs to be defined within a 0,0  - 1,1 rectangle
        #
        if cutshape in self._defined_patterns:
            entry = self._defined_patterns[cutshape]
        else:
            entry = self._defined_patterns[0]
        additional_parameter = entry[1]
        info1 = entry[2]
        info2 = entry[3]
        self.cutshape = cutshape
        self.pattern = []
        entry[0]()
        self.path = None
        self.previewpath = None
        return additional_parameter, info1, info2

    def set_line(self):
        self.pattern.append(("M", 0, 0.5))
        self.pattern.append(("L", 1, 0.5))

    def set_fishbone(self):
        dx = self.param_a / 5.0 * 0.5
        dy = self.param_b / 5.0 * 0.5
        self.pattern.append(("M", 0 + dx, 1 - dy))
        self.pattern.append(("L", 0.5, 0))
        # self.pattern.append(("M", 0.5, 0))
        self.pattern.append(("L", 1 - dx, 1 - dy))

    def set_diagonal(self):
        dx = self.param_a / 5.0 * 1.0
        dy = self.param_b / 5.0 * 1.0
        self.pattern.append(("M", 0 + dx, 1 - dy))
        self.pattern.append(("L", 1 - dx, 0 + dy))

    def set_diamond1(self):
        self.pattern.append(("M", 0, 0.5))
        self.pattern.append(("L", 0.5, 0))
        self.pattern.append(("L", 1, 0.5))
        self.pattern.append(("L", 0.5, 1))
        self.pattern.append(("L", 0, 0.5))

    def set_diamond2(self):
        self.pattern.append(("M", 0, 0))
        self.pattern.append(("L", 0.5, 0.4))
        self.pattern.append(("L", 1, 0))
        self.pattern.append(("M", 0, 1))
        self.pattern.append(("L", 0.5, 0.6))
        self.pattern.append(("L", 1, 1))

    def set_cross(self):
        # Pattern: cross
        dx = self.param_a / 5.0 * 0.5
        dy = self.param_b / 5.0 * 0.5
        self.pattern.append(("M", 0.0, 0.25 + dy))
        self.pattern.append(("L", 0.25 + dx, 0.50))
        self.pattern.append(("L", 0.0, 0.75 - dy))
        self.pattern.append(("M", 0.25 + dx, 0.50))
        self.pattern.append(("L", 0.75 - dx, 0.50))
        self.pattern.append(("M", 1, 0.25 + dy))
        self.pattern.append(("L", 0.75 - dx, 0.50))
        self.pattern.append(("L", 1, 0.75 - dy))

    def set_fabric(self):
        self.pattern.append(("M", 0.25, 0.25))
        self.pattern.append(("L", 0, 0.25))
        self.pattern.append(("L", 0, 0))
        self.pattern.append(("L", 0.5, 0))
        self.pattern.append(("L", 0.5, 1))
        self.pattern.append(("L", 1, 1))
        self.pattern.append(("L", 1, 0.75))
        self.pattern.append(("L", 0.75, 0.75))

        self.pattern.append(("M", 0.75, 0.25))
        self.pattern.append(("L", 0.75, 0))
        self.pattern.append(("L", 1, 0))
        self.pattern.append(("L", 1, 0.5))
        self.pattern.append(("L", 0, 0.5))
        self.pattern.append(("L", 0, 1))
        self.pattern.append(("L", 0.25, 1))
        self.pattern.append(("L", 0.25, 0.75))

    def set_beehive(self):
        dx = self.param_a / 5.0 * 0.5
        dy = self.param_b / 5.0 * 0.5
        # top
        self.pattern.append(("M", 0, 0.5 - dy))
        self.pattern.append(("L", dx, dy))
        self.pattern.append(("L", 1 - dx, dy))
        self.pattern.append(("L", 1, 0.5 - dy))
        # inner
        self.pattern.append(("M", 0, 0.5))
        self.pattern.append(("L", dx, 2 * dy))
        self.pattern.append(("L", 1 - dx, 2 * dy))
        self.pattern.append(("L", 1, 0.5))
        self.pattern.append(("L", 1 - dx, 1 - 2 * dy))
        self.pattern.append(("L", dx, 1 - 2 * dy))
        self.pattern.append(("L", 0, 0.5))
        # bottom
        self.pattern.append(("M", 0, 0.5 + dy))
        self.pattern.append(("L", dx, 1 - dy))
        self.pattern.append(("L", 1 - dx, 1 - dy))
        self.pattern.append(("L", 1, 0.5 + dy))

    def set_bowlingpin(self):
        self.pattern.append(("M", 0.2, 0.6))
        ctrl_x = 0.1 + self.param_a
        ctrl_y = 0.5
        self.pattern.append(("Q", ctrl_x, ctrl_y, 0.2, 0.4))

        ctrl_x = 0.5
        ctrl_y = 0.1 - self.param_b
        self.pattern.append(("Q", ctrl_x, ctrl_y, 0.8, 0.4))

        ctrl_x = 0.9 - self.param_a
        ctrl_y = 0.5
        self.pattern.append(("Q", ctrl_x, ctrl_y, 0.8, 0.6))

        ctrl_x = 0.5
        ctrl_y = 0.9 + self.param_b
        self.pattern.append(("Q", ctrl_x, ctrl_y, 0.2, 0.6))

    def set_wave(self):
        # Pattern: wavy
        self.pattern.append(("M", 0.0, 0.25))
        self.pattern.append(("L", 0.25, 0.25))
        ctrl_x = 0.5 + self.param_a
        ctrl_y = 0.25 + self.param_b
        self.pattern.append(("Q", ctrl_x, ctrl_y, 0.5, 0.5))
        ctrl_x = 0.5 - self.param_a
        ctrl_y = 0.75 - self.param_b
        self.pattern.append(("Q", ctrl_x, ctrl_y, 0.75, 0.75))
        self.pattern.append(("L", 1, 0.75))

    def set_bezier(self):
        anchor_tip = self.param_a  # distance factor from anchor to place control point
        anchor_center = self.param_b
        self.pattern.append(("M", 0, 0))
        self.pattern.append(
            ("C", 1 * anchor_tip, 0, 1 / 2 - (1 * anchor_center), 1, 1 / 2, 1)
        )
        self.pattern.append(
            ("C", 1 / 2 + (1 * anchor_center), 1, 1 * (1 - anchor_tip), 0, 1, 0)
        )

    def set_brackets(self):
        p_a = self.param_a
        p_b = self.param_b
        self.pattern.append(("M", 0.0, 0.5))
        self.pattern.append(("C", 0.0, p_a, 1.0, p_b, 1.0, 0.5))
        self.pattern.append(("C", 1.0, 1 - p_a, 0.0, 1 - p_b, 0.0, 0.5))

    def set_circle(self):
        # concentric circles
        amount = int(abs(10 * self.param_a)) + 1  # (1 to 50)
        gap = abs(self.param_b)
        dx = 0.5 / amount
        cx = 0.5
        cy = 0.5
        rotation = 0
        sweep = 0
        arc = 0
        for i in range(amount):
            # A move-to command to the point cx+rx,cy;
            # arc to cx,cy+ry;
            # arc to cx-rx,cy;
            # arc to cx,cy-ry;
            # arc with a segment-completing close path operation.
            radius = i * dx

            self.pattern.append(("M", cx + radius, cy))
            self.pattern.append(("A", cx, cy, rotation, arc, sweep, cx, cy + radius))
            self.pattern.append(("A", cx, cy, rotation, arc, sweep, cx - radius, cy))
            self.pattern.append(("A", cx, cy, rotation, arc, sweep, cx, cy - radius))
            self.pattern.append(("A", cx, cy, rotation, arc, sweep, cx + radius, cy))

    def make_outline(self, x0, y0, x1, y1):
        # Draw a rectangle
        pt0 = Point(x0, y0)
        pt1 = Point(x1, y0)
        pt2 = Point(x1, y1)
        pt3 = Point(x0, y1)

        self.path.move(pt0)
        self.path.line(pt1)
        self.path.line(pt2)
        self.path.line(pt3)
        self.path.line(pt0)

    def draw_trace(self, offset_x, offset_y, width, height):
        # Draw the pattern
        # The extents of the cell will be at (offset_x, offset_y)
        # in the upper-left corner and (width, height) in the bottom-right corner

        def create_point(x, y):
            return Point(x * width + offset_x, y * height + offset_y)

        # self.path.move(offset_x, offset_y)
        # print (f"After initial move: {str(self.path)}")
        current_x = 0
        current_y = 0
        s_left = self.start_x
        s_right = s_left + self.width
        s_top = self.start_y
        s_bottom = s_top + self.height
        for entry in self.pattern:
            old_x = current_x
            old_y = current_y
            key = entry[0].lower()
            if key == "m":
                endpoint = create_point(entry[1], entry[2])
                self.path.move(endpoint)
                current_x = entry[1]
                current_y = entry[2]
            elif key == "h":
                current_x += entry[1]
                dx = entry[1]
                self.path.horizontal(dx, relative=True)
            elif key == "v":
                current_y += entry[1]
                dy = entry[1]
                self.path.vertical(dy, relative=True)
            elif key == "l":
                # Line to...
                current_x = entry[1]
                current_y = entry[2]
                endpoint = create_point(entry[1], entry[2])
                self.path.line(endpoint)
            elif key == "a":
                current_x = entry[6]
                current_y = entry[7]
                rx = entry[1]
                ry = entry[2]
                rotation = entry[3]
                arc = entry[4]
                sweep = entry[5]
                endpoint = create_point(current_x, current_y)
                self.path.arc(rx, ry, rotation, arc, sweep, endpoint)
            elif key == "c":
                current_x = entry[5]
                current_y = entry[6]
                control1 = create_point(entry[1], entry[2])
                control2 = create_point(entry[3], entry[4])
                endpoint = create_point(entry[5], entry[6])
                self.path.cubic(control1, control2, endpoint)
            elif key == "q":
                current_x = entry[3]
                current_y = entry[4]
                control1 = create_point(entry[1], entry[2])
                endpoint = create_point(entry[3], entry[4])
                self.path.quad(control1, endpoint)

    def set_hinge_shape(self, shapenode):
        self.outershape = shapenode

    def set_hinge_area(self, hinge_left, hinge_top, hinge_width, hinge_height):
        self.start_x = hinge_left
        self.start_y = hinge_top
        self.width = hinge_width
        self.height = hinge_height
        self.x0 = hinge_width * self.gap
        self.y0 = hinge_height * self.gap
        self.x1 = hinge_width * (1 - self.gap)
        self.y1 = hinge_height * (1 - self.gap)
        # Requires recalculation
        self.path = None
        self.previewpath = None

    def set_cell_values(self, percentage_x, percentage_y):
        self.cell_width_percentage = percentage_x
        self.cell_height_percentage = percentage_y
        # Requires recalculation
        self.path = None
        self.previewpath = None

    def set_padding_values(self, padding_x, padding_y):
        self.cell_padding_h_percentage = padding_x
        self.cell_padding_v_percentage = padding_y
        # Requires recalculation
        self.path = None
        self.preview_path = None

    def set_additional_parameters(self, param_a, param_b):
        self.param_a = param_a
        self.param_b = param_b
        # Make sure pattern is updated with additional parameter
        self.set_predefined_pattern(self.cutshape)

    def generate(self, show_outline=False, force=False, final=False):
        if final and self.path is not None and not force:
            # No need to recalculate...
            return
        elif not final and self.preview_path is not None and not force:
            # No need to recalculate...
            return

        self.cell_width = self.width * self.cell_width_percentage / 100
        self.cell_height = self.height * self.cell_height_percentage / 100
        self.cell_padding_h = self.cell_width * self.cell_padding_h_percentage / 100
        self.cell_padding_v = self.cell_height * self.cell_padding_v_percentage / 100
        self.path = Path(stroke=Color("red"), stroke_width=500)

        if show_outline:
            self.make_outline(self.x0, self.y0, self.x1, self.y1)

        #  Determine rows and columns of cuts to create
        #  will round down so add 1 and trim later
        cols = (
            int(
                ((self.x1 - self.x0) + self.cell_width)
                / (self.cell_width + (2 * self.cell_padding_h))
            )
            + 1
        )
        rows = (
            int(
                ((self.y1 - self.y0) + self.cell_height)
                / (self.cell_height + (2 * self.cell_padding_v))
            )
            + 1
        )

        # print (f"Area: {self.width:.1f}, {self.height:.1f}, Cell: {self.cell_width:.1f}, {self.cell_height:.1f}")
        # print (f"Rows: {rows}, Cols={cols}")
        # print (f"Ratios: {self.cell_width_percentage}, {self.cell_height_percentage}")
        # print (f"Padding: {self.cell_padding_h_percentage}, {self.cell_padding_v_percentage}")
        for col in range(-2, cols + 1, 1):
            top_left_x = self.x0 - (self.cell_width / 2)
            x_offset = col * (self.cell_width + (2 * self.cell_padding_h))
            x_current = top_left_x + x_offset
            for row in range(-2, rows + 1, 1):
                top_left_y = self.y0
                y_offset = row * (self.cell_height + (2 * self.cell_padding_v)) + (
                    (self.cell_height + (2 * self.cell_padding_v)) / 2
                ) * (col % 2)
                y_current = top_left_y + y_offset

                if x_current < self.x1 and y_current < self.y1:
                    # Don't call draw if outside of hinge area
                    self.draw_trace(
                        x_current,
                        y_current,
                        self.cell_width,
                        self.cell_height,
                    )
                    if show_outline:
                        self.make_outline(
                            x_current,
                            y_current,
                            x_current + self.cell_width,
                            y_current + self.cell_height,
                        )
        rectangular = True
        if (
            self.outershape is not None
            and hasattr(self.outershape, "as_path")
            and self.outershape.type != "elem rect"
        ):
            rectangular = False
        if final and not rectangular:
            self.path.transform *= Matrix.translate(self.start_x, self.start_y)
            from time import time

            t0 = time()
            vm = VectorMontonizer()
            if self.outershape is None:
                outer_poly = Polygon(
                    (
                        Point(self.x0, self.y0),
                        Point(self.x1, self.y0),
                        Point(self.x1, self.y1),
                        Point(self.x0, self.y1),
                        Point(self.x0, self.y0),
                    )
                )
            else:
                outer_path = self.outershape.as_path()
                outer_poly = Polygon(
                    [outer_path.point(i / 1000.0, error=1e4) for i in range(1001)]
                )
            vm.add_polyline(outer_poly)
            path = Path(stroke=Color("red"), stroke_width=500)
            deleted = 0
            total = 0
            # pt_min_x = 1E+30
            # pt_min_y = 1E+30
            # pt_max_x = -1 * pt_min_x
            # pt_max_y = -1 * pt_min_y
            # Numpy does not work
            # vm.add_polyline(outer_poly)
            # path = Path(stroke=Color("red"), stroke_width=500)
            # for sub_inner in self.path.as_subpaths():
            #     sub_inner = Path(sub_inner)
            #     pts_sub = sub_inner.npoint(linspace(0, 1, 1000))
            #     good_pts = [p for p in pts_sub if vm.is_point_inside(p[0] + self.start_x, p[1] + self.start_y)]
            #     path += Path(Polyline(good_pts), stroke=Color("red"), stroke_width=500)
            for sub_inner in self.path.as_subpaths():
                sub_inner = Path(sub_inner)
                pts_sub = [sub_inner.point(i / 1000.0, error=1e4) for i in range(1001)]

                for i in range(len(pts_sub) - 1, -1, -1):
                    total += 1
                    pt = pts_sub[i]
                    pt[0] += self.start_x
                    pt[1] += self.start_y
                    # pt_min_x = min(pt_min_x, pt[0])
                    # pt_min_y = min(pt_min_y, pt[1])
                    # pt_max_x = max(pt_max_x, pt[0])
                    # pt_max_y = max(pt_max_y, pt[1])
                    if not vm.is_point_inside(pt[0], pt[1]):
                        # if we do have points beyond, then we create a seperate path
                        if i < len(pts_sub) - 1:
                            goodpts = pts_sub[i + 1 :]
                            path += Path(
                                Polyline(goodpts), stroke=Color("red"), stroke_width=500
                            )
                        del pts_sub[i:]
                        deleted += 1
                path += Path(Polyline(pts_sub), stroke=Color("red"), stroke_width=500)
            self.path = path
        else:
            # Former method....
            # ...is limited to rectangular area but maintains inner cubics,
            # quads and arcs while the vectormontonizer is more versatile
            # when it comes to the surrounding shape but transforms all
            # path elements to lines
            self.path = self.clip_path(self.path, 0, 0, self.width, self.height)
            self.path.transform *= Matrix.translate(self.start_x, self.start_y)
            self.previewpath = copy(self.path)

    def clip_path(self, path, xmin, ymin, xmax, ymax):
        """
        Clip a path at a rectangular area, will return the clipped path

        Args:
            path : The path to clip
            xmin : Left side of the rectangular area
            ymin : Upper side of the rectangular area
            xmax : Right side of the rectangular area
            ymax : Lower side of the rectangular area
        """

        def outside(bb_to_check, master_bb):
            out_x = "inside"
            out_y = "inside"
            if bb_to_check[0] > master_bb[2] or bb_to_check[2] < master_bb[0]:
                # fully out on x
                out_x = "outside"
            elif bb_to_check[0] < master_bb[0] or bb_to_check[2] > master_bb[2]:
                out_x = "cross"
            if bb_to_check[1] > master_bb[3] or bb_to_check[3] < master_bb[1]:
                out_y = "outside"
            elif bb_to_check[1] < master_bb[1] or bb_to_check[3] > master_bb[3]:
                out_x = "cross"
            return out_x, out_y

        def approximate_line(part_of_path, current_x, current_y):
            # print(f"Check: {type(part_of_path).__name__} {part_of_path.bbox()} {clipbb}")
            added = 0
            partial = 0
            ignored = 0
            subj = part_of_path.npoint(linspace(0, 1, interpolation))
            subj.reshape((2, interpolation))
            iterated_points = list(map(Point, subj))
            for p in iterated_points:
                segbb = (
                    min(current_x, p[0]),
                    min(current_y, p[1]),
                    max(current_x, p[0]),
                    max(current_y, p[1]),
                )
                sx, sy = outside(segbb, clipbb)
                # print(f"{segbb} - {clipbb} {sx} - {sy}")
                if sx == "outside" or sy == "outside":
                    # Fully outside, so drop
                    add_move(newpath, e.end)
                    ignored += 1
                elif statex == "inside" and statey == "inside":
                    # Fully inside, so append
                    if current_x != new_cx or current_y != new_cy:
                        add_move(newpath, Point(current_x, current_y))
                    newpath.line(p)
                    added += 1
                else:
                    dx = p[0] - current_x
                    dy = p[1] - current_y
                    new_cx = current_x
                    new_cy = current_y
                    new_ex = p[0]
                    new_ey = p[1]
                    if dx == 0:
                        # Vertical line needs special treatment
                        if new_cx >= xmin and new_cx <= xmax:
                            new_cy = min(max(new_cy, ymin), ymax)
                            new_ey = min(max(new_ey, ymin), ymax)
                            if new_cx != current_x or new_cy != current_y:
                                # Needs a move
                                add_move(newpath, Point(new_cx, new_cy))
                            newpath.line(Point(new_ex, new_ey))
                            partial += 1
                        else:
                            ignored += 1
                    else:
                        # regular line, so lets establish x0 x1
                        # could still be an outward pointing line....
                        new_cx = min(max(new_cx, xmin), xmax)
                        new_ex = min(max(new_ex, xmin), xmax)
                        # corresponding y values...
                        edx = p[0] - current_x
                        edy = p[1] - current_y
                        new_cy = current_y + (new_cx - current_x) / edx * edy
                        new_ey = current_y + (new_ex - current_x) / edx * edy
                        # Y can still cross...
                        new_cx_clipped = new_cx
                        new_ex_clipped = new_ex
                        new_cy_clipped = min(max(new_cy, ymin), ymax)
                        new_ey_clipped = min(max(new_ey, ymin), ymax)
                        # Adjust x - value
                        if dy != 0:
                            new_cx_clipped = new_cx + dx / dy * (
                                new_cy_clipped - new_cy
                            )
                            new_ex_clipped = new_ex + dx / dy * (
                                new_ey_clipped - new_ey
                            )

                        new_cx = new_cx_clipped
                        new_cy = new_cy_clipped
                        new_ex = new_ex_clipped
                        new_ey = new_ey_clipped
                        if min(new_cy, new_ey) == ymax and dy != 0:
                            # Outward...
                            ignored += 1
                        elif max(new_cy, new_ey) == ymin and dy != 0:
                            # Outward...
                            ignored += 1
                        else:
                            if new_cx != current_x or new_cy != current_y:
                                # Needs a move
                                add_move(newpath, Point(new_cx, new_cy))
                            newpath.line(Point(new_ex, new_ey))
                            partial += 1
                current_x = p[0]
                current_y = p[1]
            if current_x != part_of_path.end[0] or current_y != part_of_path.end[1]:
                add_move(newpath, part_of_path.end)
            # print (f"From iterated line: added={added}, partial={partial}, ignored={ignored}")

        def add_move(addpath, destination):
            # Was the last segment as well a move? Then just update the coords...
            if len(addpath) > 0:
                if isinstance(addpath[-1], Move):
                    addpath[-1].end = destination
                    return
            addpath.move(destination)

        interpolation = 50
        fully_deleted = 0
        partial_deleted = 0
        not_deleted = 0
        clipbb = (xmin, ymin, xmax, ymax)
        current_x = 0
        current_y = 0
        first_point = path.first_point
        if first_point is not None:
            current_x = first_point[0]
            current_y = first_point[1]
        newpath = Path(
            stroke=path.stroke, stroke_width=path.stroke_width, transform=path.transform
        )
        for e in path:
            if hasattr(e, "bbox"):
                segbb = e.bbox()
            elif hasattr(e, "end"):
                segbb = (
                    min(current_x, e.end[0]),
                    min(current_y, e.end[1]),
                    max(current_x, e.end[0]),
                    max(current_y, e.end[1]),
                )
            else:
                segbb = (xmin, ymin, 0, 0)
            if isinstance(e, Move):
                add_move(newpath, e.end)
                current_x = e.end[0]
                current_y = e.end[1]
                not_deleted += 1
            elif isinstance(e, Line):
                statex, statey = outside(segbb, clipbb)
                dx = e.end[0] - current_x
                dy = e.end[1] - current_y
                if statex == "outside" or statey == "outside":
                    # Fully outside, so drop
                    add_move(newpath, e.end)
                    fully_deleted += 1
                elif statex == "inside" and statey == "inside":
                    # Fully inside, so append
                    newpath.line(e.end)
                    not_deleted += 1
                else:
                    # needs dealing, its either for the time being, just ignored...
                    new_cx = current_x
                    new_cy = current_y
                    new_ex = e.end[0]
                    new_ey = e.end[1]
                    if dx == 0:
                        # Vertical line needs special treatment
                        if new_cx >= xmin and new_cx <= xmax:
                            new_cy = min(max(new_cy, ymin), ymax)
                            new_ey = min(max(new_ey, ymin), ymax)
                            if new_cx != current_x or new_cy != current_y:
                                # Needs a move
                                add_move(newpath, Point(new_cx, new_cy))
                            newpath.line(Point(new_ex, new_ey))
                    else:
                        # regular line, so lets establish x0 x1
                        # could still be an outward pointing line....
                        new_cx = min(max(new_cx, xmin), xmax)
                        new_ex = min(max(new_ex, xmin), xmax)
                        # corresponding y values...
                        edx = e.end[0] - current_x
                        edy = e.end[1] - current_y
                        new_cy = current_y + (new_cx - current_x) / edx * edy
                        new_ey = current_y + (new_ex - current_x) / edx * edy
                        # Y can still cross...
                        new_cx_clipped = new_cx
                        new_ex_clipped = new_ex
                        new_cy_clipped = min(max(new_cy, ymin), ymax)
                        new_ey_clipped = min(max(new_ey, ymin), ymax)
                        # Adjust x - value
                        if dy != 0:
                            new_cx_clipped = new_cx + dx / dy * (
                                new_cy_clipped - new_cy
                            )
                            new_ex_clipped = new_ex + dx / dy * (
                                new_ey_clipped - new_ey
                            )

                        new_cx = new_cx_clipped
                        new_cy = new_cy_clipped
                        new_ex = new_ex_clipped
                        new_ey = new_ey_clipped
                        if min(new_cy, new_ey) == ymax and dy != 0:
                            # Outward...
                            pass
                        elif max(new_cy, new_ey) == ymin and dy != 0:
                            # Outward...
                            pass
                        else:
                            if new_cx != current_x or new_cy != current_y:
                                # Needs a move
                                add_move(newpath, Point(new_cx, new_cy))
                            newpath.line(Point(new_ex, new_ey))
                    if current_x != e.end[0] or current_y != e.end[1]:
                        add_move(newpath, e.end)
                    partial_deleted += 1
                current_x = e.end[0]
                current_y = e.end[1]
            elif isinstance(e, Close):
                newpath.closed()
                not_deleted += 1
            elif isinstance(e, QuadraticBezier):
                statex, statey = outside(segbb, clipbb)
                if statex == "outside" and statey == "outside":
                    # Fully outside, so drop
                    add_move(newpath, e.end)
                    fully_deleted += 1
                elif statex == "inside" and statey == "inside":
                    # Fully inside, so append
                    newpath.quad(e.control, e.end)
                    not_deleted += 1
                else:
                    approximate_line(e, current_x, current_y)
                current_x = e.end[0]
                current_y = e.end[1]
            elif isinstance(e, CubicBezier):
                statex, statey = outside(segbb, clipbb)
                if statex == "outside" and statey == "outside":
                    # Fully outside, so drop
                    add_move(newpath, e.end)
                    fully_deleted += 1
                elif statex == "inside" and statey == "inside":
                    # Fully inside, so append
                    newpath.cubic(e.control1, e.control2, e.end)
                    not_deleted += 1
                else:
                    approximate_line(e, current_x, current_y)
                    partial_deleted += 1
                current_x = e.end[0]
                current_y = e.end[1]
            elif isinstance(e, Arc):
                for e_cubic in e.as_cubic_curves():
                    segbb = e_cubic.bbox()
                    statex, statey = outside(segbb, clipbb)
                    if statex == "outside" and statey == "outside":
                        # Fully outside, so drop
                        add_move(newpath, e.end)
                        fully_deleted += 1
                    elif statex == "inside" and statey == "inside":
                        # Fully inside, so append
                        newpath.cubic(e_cubic.control1, e_cubic.control2, e_cubic.end)
                        not_deleted += 1
                    else:
                        approximate_line(e_cubic, current_x, current_y)
                        partial_deleted += 1
                    current_x = e_cubic.end[0]
                    current_y = e_cubic.end[1]
                current_x = e.end[0]
                current_y = e.end[1]

        flag = True
        while flag:
            flag = False
            if len(newpath) > 0 and isinstance(newpath[-1], Move):
                # We dont need a move at the end of the path...
                newpath._segments.pop(-1)
                flag = True

        # print(
        #     f"Ready: left untouched: {not_deleted}, fully deleted={fully_deleted}, partial deletion:{partial_deleted}"
        # )
        return newpath


class HingePanel(wx.Panel):
    """
    UI for LivingHinges, allows setting of parameters including preview of the expected result
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.hinge_origin_x = "0cm"
        self.hinge_origin_y = "0cm"
        self.hinge_width = "5cm"
        self.hinge_height = "5cm"
        self.hinge_cells_x = 20
        self.hinge_cells_y = 20
        self.hinge_padding_x = 10
        self.hinge_padding_y = 10
        self.hinge_param_a = 0.7
        self.hinge_param_b = 0.7

        self.renderer = LaserRender(context)
        self.in_draw_event = False
        self.in_change_event = False
        self.require_refresh = True
        self._Buffer = None

        self.text_origin_x = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_origin_y = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_width = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_height = wx.TextCtrl(self, wx.ID_ANY, "")
        self.combo_style = wx.ComboBox(
            self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN
        )
        self.button_default = wx.Button(self, wx.ID_ANY, "D")
        self.slider_width = wx.Slider(
            self,
            wx.ID_ANY,
            20,
            1,
            100,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.text_cell_width = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )
        self.slider_height = wx.Slider(
            self,
            wx.ID_ANY,
            20,
            1,
            100,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.text_cell_height = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )
        self.slider_offset_x = wx.Slider(
            self,
            wx.ID_ANY,
            0,
            -49,
            50,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.text_cell_offset_x = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )
        self.slider_offset_y = wx.Slider(
            self,
            wx.ID_ANY,
            0,
            -49,
            50,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.text_cell_offset_y = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )
        # Slider times ten
        self.slider_param_a = wx.Slider(
            self,
            wx.ID_ANY,
            7,
            -50,
            50,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.slider_param_b = wx.Slider(
            self,
            wx.ID_ANY,
            7,
            -50,
            +50,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.button_generate = wx.Button(self, wx.ID_ANY, _("Generate"))
        self.button_close = wx.Button(self, wx.ID_ANY, _("Close"))
        self.context.setting(bool, "hinge_preview_pattern", True)
        self.context.setting(bool, "hinge_preview_shape", True)
        self.check_preview_show_pattern = wx.CheckBox(
            self, wx.ID_ANY, _("Preview Pattern")
        )
        self.check_preview_show_pattern.SetValue(
            bool(self.context.hinge_preview_pattern)
        )
        self.check_preview_show_shape = wx.CheckBox(self, wx.ID_ANY, _("Preview Shape"))
        self.check_preview_show_shape.SetValue(bool(self.context.hinge_preview_shape))

        self.hinge_generator = LivingHinges(
            0, 0, float(Length("5cm")), float(Length("5cm"))
        )

        #  self.check_debug_outline = wx.CheckBox(self, wx.ID_ANY, "Show outline")

        self.patterns = list()
        self.defaults = list()
        for pattern, default in self.hinge_generator.get_patterns():
            self.patterns.append(pattern)
            self.defaults.append(default)
        self.combo_style.Set(self.patterns)
        self.combo_style.SetSelection(0)
        # self.check_debug_outline.SetValue(True)
        self._set_layout()
        self._set_logic()

        self._setup_settings()
        self._restore_settings()

        self.Layout()

    def _set_logic(self):
        self.panel_preview.Bind(wx.EVT_PAINT, self.on_paint)
        self.button_close.Bind(wx.EVT_BUTTON, self.on_button_close)
        self.button_generate.Bind(wx.EVT_BUTTON, self.on_button_generate)
        self.text_height.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_width.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_origin_x.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_origin_y.Bind(wx.EVT_TEXT, self.on_option_update)
        self.slider_width.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_height.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_offset_x.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_offset_y.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_param_a.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_param_b.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.combo_style.Bind(wx.EVT_COMBOBOX, self.on_pattern_update)
        self.button_default.Bind(wx.EVT_BUTTON, self.on_default_button)
        self.check_preview_show_pattern.Bind(wx.EVT_CHECKBOX, self.on_preview_options)
        self.check_preview_show_shape.Bind(wx.EVT_CHECKBOX, self.on_preview_options)
        self.panel_preview.Bind(wx.EVT_PAINT, self.on_display_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.text_cell_height.Bind(wx.EVT_TEXT_ENTER, self.on_option_update)
        self.text_cell_width.Bind(wx.EVT_TEXT_ENTER, self.on_option_update)
        self.text_cell_offset_x.Bind(wx.EVT_TEXT_ENTER, self.on_option_update)
        self.text_cell_offset_y.Bind(wx.EVT_TEXT_ENTER, self.on_option_update)

    def _set_layout(self):
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        main_left = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(main_left, 1, wx.EXPAND, 0)

        vsizer_dimension = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Dimension")), wx.VERTICAL
        )
        main_left.Add(vsizer_dimension, 0, wx.EXPAND, 0)

        hsizer_origin = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_dimension.Add(hsizer_origin, 0, wx.EXPAND, 0)

        hsizer_originx = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("X:")), wx.VERTICAL
        )
        self.text_origin_x.SetToolTip(_("X-Coordinate of the hinge area"))
        hsizer_originx.Add(self.text_origin_x, 1, wx.EXPAND, 0)

        hsizer_originy = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Y:")), wx.VERTICAL
        )
        self.text_origin_y.SetToolTip(_("Y-Coordinate of the hinge area"))
        hsizer_originy.Add(self.text_origin_y, 1, wx.EXPAND, 0)

        hsizer_origin.Add(hsizer_originx, 1, wx.EXPAND, 0)
        hsizer_origin.Add(hsizer_originy, 1, wx.EXPAND, 0)

        hsizer_wh = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_dimension.Add(hsizer_wh, 0, wx.EXPAND, 0)

        hsizer_width = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Width:")), wx.VERTICAL
        )
        self.text_width.SetToolTip(_("Width of the hinge area"))
        hsizer_width.Add(self.text_width, 1, wx.EXPAND, 0)

        hsizer_height = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Height:")), wx.VERTICAL
        )

        self.text_height.SetToolTip(_("Height of the hinge area"))
        hsizer_height.Add(self.text_height, 1, wx.EXPAND, 0)

        hsizer_wh.Add(hsizer_width, 1, wx.EXPAND, 0)
        hsizer_wh.Add(hsizer_height, 1, wx.EXPAND, 0)

        vsizer_options = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Options")), wx.VERTICAL
        )
        main_left.Add(vsizer_options, 0, wx.EXPAND, 0)

        hsizer_pattern = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_pattern, 0, wx.EXPAND, 0)

        label_pattern = wx.StaticText(self, wx.ID_ANY, _("Pattern:"))
        label_pattern.SetMinSize((90, -1))
        hsizer_pattern.Add(label_pattern, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.combo_style.SetToolTip(_("Choose the hinge pattern"))
        hsizer_pattern.Add(self.combo_style, 1, wx.EXPAND, 0)

        self.button_default.SetToolTip(_("Default Values"))
        self.button_default.SetMinSize((30, -1))
        hsizer_pattern.Add(self.button_default, 0, wx.EXPAND, 0)

        hsizer_cellwidth = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_cellwidth, 1, wx.EXPAND, 0)

        label_cell_width = wx.StaticText(self, wx.ID_ANY, _("Cell-Width:"))
        label_cell_width.SetMinSize((90, -1))
        hsizer_cellwidth.Add(label_cell_width, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_width.SetToolTip(
            _("Select the ratio of the cell width compared to the overall width")
        )
        self.text_cell_width.SetToolTip(
            _("Select the ratio of the cell width compared to the overall width")
            + "\n"
            + _("(Press return to apply values)")
        )
        hsizer_cellwidth.Add(self.slider_width, 2, wx.EXPAND, 0)
        hsizer_cellwidth.Add(self.text_cell_width, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        hsizer_cellheight = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_cellheight, 1, wx.EXPAND, 0)

        label_cell_height = wx.StaticText(self, wx.ID_ANY, _("Cell-Height:"))
        label_cell_height.SetMinSize((90, -1))
        hsizer_cellheight.Add(label_cell_height, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_height.SetToolTip(
            _("Select the ratio of the cell height compared to the overall height")
        )
        self.text_cell_height.SetToolTip(
            _("Select the ratio of the cell height compared to the overall height")
            + "\n"
            + _("(Press return to apply values)")
        )
        hsizer_cellheight.Add(self.slider_height, 2, wx.EXPAND, 0)
        hsizer_cellheight.Add(self.text_cell_height, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        hsizer_offsetx = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_offsetx, 1, wx.EXPAND, 0)

        label_offset_x = wx.StaticText(self, wx.ID_ANY, _("Offset X:"))
        label_offset_x.SetMinSize((90, -1))
        hsizer_offsetx.Add(label_offset_x, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_offset_x.SetToolTip(_("Select the pattern-offset in X-direction"))
        self.text_cell_offset_x.SetToolTip(
            _("Select the pattern-offset in X-direction")
            + "\n"
            + _("(Press return to apply values)")
        )
        hsizer_offsetx.Add(self.slider_offset_x, 2, wx.EXPAND, 0)
        hsizer_offsetx.Add(self.text_cell_offset_x, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        hsizer_offsety = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_offsety, 0, wx.EXPAND, 0)

        label_offset_y = wx.StaticText(self, wx.ID_ANY, _("Offset Y:"))
        label_offset_y.SetMinSize((90, -1))
        hsizer_offsety.Add(label_offset_y, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_offset_y.SetToolTip(_("Select the pattern-offset in Y-direction"))
        self.text_cell_offset_y.SetToolTip(
            _("Select the pattern-offset in Y-direction")
            + "\n"
            + _("(Press return to apply values)")
        )
        hsizer_offsety.Add(self.slider_offset_y, 2, wx.EXPAND, 0)
        hsizer_offsety.Add(self.text_cell_offset_y, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_param_a.SetToolTip(_("Change the shape appearance"))
        self.slider_param_b.SetToolTip(_("Change the shape appearance"))
        hsizer_param_a = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_param_a.Add(self.slider_param_a, 1, wx.EXPAND, 0)
        hsizer_param_a.Add(self.slider_param_b, 1, wx.EXPAND, 0)
        vsizer_options.Add(hsizer_param_a, 0, wx.EXPAND, 0)
        # main_left.Add(self.check_debug_outline, 0, wx.EXPAND, 0)

        hsizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        main_left.Add(hsizer_buttons, 0, wx.EXPAND, 0)

        self.button_generate.SetToolTip(_("Generates the hinge"))
        hsizer_buttons.Add(self.button_generate, 2, 0, 0)

        hsizer_buttons.Add(self.button_close, 1, 0, 0)

        main_right = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Preview"), wx.VERTICAL
        )
        main_sizer.Add(main_right, 2, wx.EXPAND, 0)

        hsizer_preview = wx.BoxSizer(wx.HORIZONTAL)
        main_right.Add(hsizer_preview, 0, wx.EXPAND, 0)
        self.check_preview_show_pattern.SetMinSize(wx.Size(-1, 23))
        self.check_preview_show_shape.SetMinSize(wx.Size(-1, 23))
        hsizer_preview.Add(self.check_preview_show_pattern, 1, wx.EXPAND, 0)
        hsizer_preview.Add(self.check_preview_show_shape, 1, wx.EXPAND, 0)

        self.panel_preview = wx.Panel(self, wx.ID_ANY)
        main_right.Add(self.panel_preview, 1, wx.EXPAND, 0)

        self.SetSizer(main_sizer)

    def on_preview_options(self, event):
        self.context.hinge_preview_pattern = self.check_preview_show_pattern.GetValue()
        self.context.hinge_preview_shape = self.check_preview_show_shape.GetValue()
        self.refresh_display()

    def on_display_paint(self, event=None):
        try:
            wx.BufferedPaintDC(self.panel_preview, self._Buffer)
        except RuntimeError:
            pass

    def set_buffer(self):
        width, height = self.panel_preview.Size
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        self._Buffer = wx.Bitmap(width, height)

    def refresh_display(self):
        if not wx.IsMainThread():
            wx.CallAfter(self.refresh_in_ui)
        else:
            self.refresh_in_ui()

    def on_paint(self, event):
        self.Layout()
        self.set_buffer()
        wx.CallAfter(self.refresh_in_ui)

    def on_size(self, event=None):
        self.Layout()
        self.set_buffer()
        wx.CallAfter(self.refresh_in_ui)

    def refresh_in_ui(self):
        if self.in_draw_event:
            return
        # Create paint DC
        self.in_draw_event = True
        if self._Buffer is None:
            self.set_buffer()
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        # Create graphics context from it
        gc = wx.GraphicsContext.Create(dc)

        if gc:
            wd, ht = self.panel_preview.GetSize()
            ratio = min(
                wd / self.hinge_generator.width, ht / self.hinge_generator.height
            )
            ratio *= 0.9
            matrix = gc.CreateMatrix(
                a=ratio,
                b=0,
                c=0,
                d=ratio,
                tx=0.05 * ratio * self.hinge_generator.width,
                ty=0.05 * ratio * self.hinge_generator.height,
            )
            gc.SetTransform(matrix)
            linewidth = max(int(1 / ratio), 1)
            if self.check_preview_show_shape.GetValue():
                mypen_border = wx.Pen(wx.BLUE, linewidth, wx.PENSTYLE_SOLID)
                gc.SetPen(mypen_border)
                if self.hinge_generator.outershape is None:
                    # Draw the hinge area:
                    gc.DrawRectangle(
                        0, 0, self.hinge_generator.width, self.hinge_generator.height
                    )
                else:
                    node = copy(self.hinge_generator.outershape)
                    bb = node.bbox()
                    node.matrix *= Matrix.translate(-bb[0], -bb[1])
                    path = node.as_path()
                    gcpath = self.renderer.make_path(gc, path)
                    gc.StrokePath(gcpath)
            if self.check_preview_show_pattern.GetValue():
                mypen_path = wx.Pen(wx.RED, linewidth, wx.PENSTYLE_SOLID)
                # flag = self.check_debug_outline.GetValue()
                self.hinge_generator.generate(
                    show_outline=False, force=False, final=False
                )
                gc.SetPen(mypen_path)
                gcpath = self.renderer.make_path(gc, self.hinge_generator.previewpath)
                gc.StrokePath(gcpath)
        self.panel_preview.Refresh()
        self.panel_preview.Update()
        self.in_draw_event = False

    def on_button_close(self, event):
        self.context("window toggle Hingetool\n")

    def on_default_button(self, event):
        idx = self.combo_style.GetSelection()
        if idx < 0:
            return
        pattern = self.patterns[idx]
        default = self.hinge_generator.get_default(pattern)
        self.slider_width.SetValue(20)
        self.slider_height.SetValue(20)
        self.slider_offset_x.SetValue(default[0])
        self.slider_offset_y.SetValue(default[1])
        self.slider_param_a.SetValue(int(10 * default[2]))
        self.slider_param_b.SetValue(int(10 * default[3]))
        self.on_option_update(None)

    def on_button_generate(self, event):
        oldlabel = self.button_generate.Label
        self.button_generate.Enable(False)
        self.button_generate.SetLabel(_("Processing..."))
        if self.hinge_generator.outershape is not None:
            # As we have a reference shape, we make sure
            # we update the information...
            units = self.context.units_name
            bounds = self.hinge_generator.outershape.bbox()
            start_x = bounds[0]
            start_y = bounds[1]
            wd = bounds[2] - bounds[0]
            ht = bounds[3] - bounds[1]
            self.hinge_origin_x = Length(
                amount=start_x, digits=3, preferred_units=units
            ).preferred_length
            self.hinge_origin_y = Length(
                amount=start_y, digits=3, preferred_units=units
            ).preferred_length
            self.hinge_width = Length(
                amount=wd, digits=2, preferred_units=units
            ).preferred_length
            self.hinge_height = Length(
                amount=ht, digits=2, preferred_units=units
            ).preferred_length
            self.text_origin_x.ChangeValue(self.hinge_origin_x)
            self.text_origin_y.ChangeValue(self.hinge_origin_y)
            self.text_width.ChangeValue(self.hinge_width)
            self.text_height.ChangeValue(self.hinge_height)
            self.hinge_generator.set_hinge_area(start_x, start_y, wd, ht)

        # Polycut algorithm does not work for me (yet), final=False still
        self.hinge_generator.generate(show_outline=False, force=True, final=True)
        node = self.context.elements.elem_branch.add(
            path=self.hinge_generator.path,
            stroke_width=500,
            color=Color("red"),
            type="elem path",
        )
        if self.hinge_generator.outershape is not None:
            group_node = self.hinge_generator.outershape.parent.add(
                type="group", label="Hinge"
            )
            group_node.append_child(self.hinge_generator.outershape)
            group_node.append_child(node)
        self.context.signal("classify_new", node)
        self.context.signal("refresh_scene")
        self.button_generate.Enable(True)
        self.button_generate.SetLabel(oldlabel)

    def on_pattern_update(self, event):
        # Save the old values...
        # self._save_settings()
        idx = self.combo_style.GetSelection()
        if idx < 0:
            idx = 0
        style = self.patterns[idx]
        self.context.hinge_type = style
        # Load new set of values...
        self._restore_settings(reload=True)
        self.sync_controls(True)
        self.apply()

    def sync_controls(self, to_text=True):
        # print(f"Sync-Control called: {to_text}")
        try:
            wd = float(Length(self.text_width.GetValue()))
        except ValueError:
            wd = 0
        try:
            ht = float(Length(self.text_height.GetValue()))
        except ValueError:
            ht = 0
        if to_text:
            cell_x = self.slider_width.GetValue()
            cell_y = self.slider_height.GetValue()
            offset_x = self.slider_offset_x.GetValue()
            offset_y = self.slider_offset_y.GetValue()
            units = self.context.units_name
            cx = cell_x / 100 * wd
            cy = cell_y / 100 * ht
            self.text_cell_width.SetValue(
                Length(amount=cx, preferred_units=units).preferred_length
            )
            self.text_cell_height.SetValue(
                Length(amount=cy, preferred_units=units).preferred_length
            )

            self.text_cell_offset_x.SetValue(
                Length(
                    amount=cx * offset_x / 100, preferred_units=units
                ).preferred_length
            )
            self.text_cell_offset_y.SetValue(
                Length(
                    amount=cy * offset_y / 100, preferred_units=units
                ).preferred_length
            )
        else:
            try:
                cx = float(Length(self.text_cell_width.GetValue()))
            except ValueError:
                cx = 0
            try:
                cy = float(Length(self.text_cell_height.GetValue()))
            except ValueError:
                cy = 0
            try:
                offset_x = float(Length(self.text_cell_offset_x.GetValue()))
            except ValueError:
                offset_x = 0
            try:
                offset_y = float(Length(self.text_cell_offset_y.GetValue()))
            except ValueError:
                offset_y = 0
            if wd != 0:
                px = int(100 * cx / wd)
            else:
                px = 100
            if ht != 0:
                py = int(100 * cy / ht)
            else:
                py = 100
            if self.slider_width.GetValue() != px:
                self.hinge_cells_x = px
                self.slider_width.SetValue(px)
            if self.slider_height.GetValue() != py:
                self.hinge_cells_y = py
                self.slider_height.SetValue(py)
            if cx != 0:
                px = int(100 * offset_x / cx)
            else:
                px = 0
            if cy != 0:
                py = int(100 * offset_y / cy)
            else:
                py = 0
            if self.slider_offset_x.GetValue() != px:
                self.hinge_padding_x = px
                self.slider_offset_x.SetValue(px)
            if self.slider_offset_y.GetValue() != py:
                self.hinge_padding_y = py
                self.slider_offset_y.SetValue(py)

    def on_option_update(self, event):
        # Generic update within a pattern
        if self.in_change_event:
            return
        self.in_change_event = True
        origin = event.GetEventObject()
        etype = event.GetEventType()
        sync_direction = True
        if (
            origin is self.text_cell_height
            or origin is self.text_cell_width
            or origin is self.text_cell_offset_x
            or origin is self.text_cell_offset_y
        ):
            sync_direction = False
        flag = True
        try:
            wd = float(Length(self.text_width.GetValue()))
            if wd > 0:
                self.hinge_width = self.text_width.GetValue()
        except ValueError:
            wd = 0
            flag = False
        try:
            ht = float(Length(self.text_height.GetValue()))
            if ht > 0:
                self.hinge_height = self.text_height.GetValue()
        except ValueError:
            ht = 0
            flag = False
        try:
            x = float(Length(self.text_origin_x.GetValue()))
            self.hinge_origin_x = self.text_origin_x.GetValue()
        except ValueError:
            x = 0
            flag = False
        try:
            y = float(Length(self.text_origin_y.GetValue()))
            self.hinge_origin_y = self.text_origin_y.GetValue()
        except ValueError:
            y = 0
            flag = False
        cell_x = self.slider_width.GetValue()
        cell_y = self.slider_height.GetValue()
        self.hinge_cells_x = cell_x
        self.hinge_cells_y = cell_y
        offset_x = self.slider_offset_x.GetValue()
        offset_y = self.slider_offset_y.GetValue()
        self.hinge_padding_x = offset_x
        self.hinge_padding_y = offset_y

        self.sync_controls(to_text=sync_direction)

        p_a = self.slider_param_a.GetValue() / 10.0
        p_b = self.slider_param_b.GetValue() / 10.0
        self.hinge_param_a = p_a
        self.hinge_param_b = p_b
        self._save_settings()
        self.apply()
        self.in_change_event = False

    def _setup_settings(self):
        firstpattern = self.patterns[0]
        for (pattern, recommended) in zip(self.patterns, self.defaults):
            default = (
                pattern,
                20,
                20,
                recommended[0],
                recommended[1],
                recommended[2],
                recommended[3],
            )
            self.context.setting(list, f"hinge_{pattern}", default)
        self.context.setting(str, "hinge_type", firstpattern)

    def apply(self):
        # Restore settings will call the LivingHinge class
        self._restore_settings(reload=False)
        self.refresh_display()

    def _save_settings(self):
        pattern = self.context.hinge_type
        default = (
            pattern,
            self.hinge_cells_x,
            self.hinge_cells_y,
            self.hinge_padding_x,
            self.hinge_padding_y,
            self.hinge_param_a,
            self.hinge_param_b,
        )
        setattr(self.context, f"hinge_{pattern}", default)
        # print (f"Stored defaults for {pattern}: {default}")

    def _restore_settings(self, reload=False):
        pattern = self.context.hinge_type
        if pattern not in self.patterns:
            pattern = self.patterns[0]
            self.context.hinge_type = pattern

        if reload:
            default = getattr(self.context, f"hinge_{pattern}", None)
            # print (f"Got defaults for {pattern}: {default}")
            if default is None or len(default) < 7:
                # strange
                # print(f"Could not get a setting for {pattern}: {default}")
                return
            self.hinge_cells_x = default[1]
            self.hinge_cells_y = default[2]
            self.hinge_padding_x = default[3]
            self.hinge_padding_y = default[4]
            self.hinge_param_a = default[5]
            self.hinge_param_b = default[6]

        flag, info1, info2 = self.hinge_generator.set_predefined_pattern(pattern)
        x = float(Length(self.hinge_origin_x))
        y = float(Length(self.hinge_origin_y))
        wd = float(Length(self.hinge_width))
        ht = float(Length(self.hinge_height))
        self.hinge_generator.set_hinge_area(x, y, wd, ht)
        self.hinge_generator.set_cell_values(self.hinge_cells_x, self.hinge_cells_y)
        self.hinge_generator.set_padding_values(
            self.hinge_padding_x, self.hinge_padding_y
        )
        self.hinge_generator.set_additional_parameters(
            self.hinge_param_a, self.hinge_param_b
        )
        self.slider_param_a.Enable(flag)
        self.slider_param_b.Enable(flag)
        self.slider_param_a.Show(flag)
        self.slider_param_b.Show(flag)
        if not info1:
            info1 = "Change the shape appearance"
        if not info2:
            info2 = "Change the shape appearance"
        self.slider_param_a.SetToolTip(_(info1))
        self.slider_param_b.SetToolTip(_(info2))
        if self.combo_style.GetSelection() != self.patterns.index(
            self.context.hinge_type
        ):
            self.combo_style.SetSelection(self.patterns.index(self.context.hinge_type))
        # if self.text_origin_x.GetValue() != self.hinge_origin_x:
        #     self.text_origin_x.ChangeValue(self.hinge_origin_x)
        # if self.text_origin_y.GetValue() != self.hinge_origin_y:
        #     self.text_origin_y.ChangeValue(self.hinge_origin_y)
        # if self.text_width.GetValue() != self.hinge_width:
        #     self.text_width.ChangeValue(self.hinge_width)
        # if self.text_height.GetValue() != self.hinge_height:
        #     self.text_height.ChangeValue(self.hinge_height)
        require_sync = False
        if self.slider_width.GetValue() != self.hinge_cells_x:
            self.slider_width.SetValue(self.hinge_cells_x)
            require_sync = True
        if self.slider_height.GetValue() != self.hinge_cells_y:
            self.slider_height.SetValue(self.hinge_cells_y)
            require_sync = True
        if self.slider_offset_x.GetValue() != self.hinge_padding_x:
            self.slider_offset_x.SetValue(self.hinge_padding_x)
            require_sync = True
        if self.slider_offset_y.GetValue() != self.hinge_padding_y:
            self.slider_offset_y.SetValue(self.hinge_padding_y)
            require_sync = True
        if self.slider_param_a.GetValue() != int(10 * self.hinge_param_a):
            self.slider_param_a.SetValue(int(10 * self.hinge_param_a))
        if self.slider_param_b.GetValue() != int(10 * self.hinge_param_b):
            self.slider_param_b.SetValue(int(10 * self.hinge_param_b))
        if require_sync:
            self.sync_controls(True)
        flag = wd > 0 and ht > 0
        self.button_generate.Enable(flag)
        self.Layout()

    def pane_show(self):
        first_selected = None
        units = self.context.units_name
        flag = True
        for node in self.context.elements.elems(emphasized=True):
            first_selected = node
            bounds = node.bbox()
            self.hinge_generator.set_hinge_shape(first_selected)
            flag = False
            break
        if flag:
            self.hinge_generator.set_hinge_shape(None)
            if units in ("in", "inch"):
                s = "2in"
            else:
                s = "5cm"
            bounds = (0, 0, float(Length(s)), float(Length(s)))
        self.combo_style.SetSelection(self.patterns.index(self.context.hinge_type))
        start_x = bounds[0]
        start_y = bounds[1]
        wd = bounds[2] - bounds[0]
        ht = bounds[3] - bounds[1]
        self.hinge_origin_x = Length(
            amount=start_x, digits=3, preferred_units=units
        ).preferred_length
        self.hinge_origin_y = Length(
            amount=start_y, digits=3, preferred_units=units
        ).preferred_length
        self.hinge_width = Length(
            amount=wd, digits=2, preferred_units=units
        ).preferred_length
        self.hinge_height = Length(
            amount=ht, digits=2, preferred_units=units
        ).preferred_length
        self.text_origin_x.ChangeValue(self.hinge_origin_x)
        self.text_origin_y.ChangeValue(self.hinge_origin_y)
        self.text_width.ChangeValue(self.hinge_width)
        self.text_height.ChangeValue(self.hinge_height)
        self.text_origin_x.Enable(flag)
        self.text_origin_y.Enable(flag)
        self.text_width.Enable(flag)
        self.text_height.Enable(flag)
        self.hinge_generator.set_hinge_area(start_x, start_y, wd, ht)
        self.on_pattern_update(None)


class LivingHingeTool(MWindow):
    """
    LivingHingeTool is the wrapper class to setup the
    required calls to open the HingePanel window
    In addition it listens to element selection and passes this
    information to HingePanel
    """

    def __init__(self, *args, **kwds):
        super().__init__(570, 420, submenu="Laser-Tools", *args, **kwds)
        self.panel_template = HingePanel(
            self,
            wx.ID_ANY,
            context=self.context,
        )
        self.add_module_delegate(self.panel_template)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_hinges_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Living Hinges"))
        self.Layout()
        self.Bind(wx.EVT_ACTIVATE, self.window_active, self)

    def window_open(self):
        self.panel_template.pane_show()

    def window_close(self):
        pass

    def window_active(self, event):
        self.panel_template.pane_show()

    @signal_listener("emphasized")
    def on_emphasized_elements_changed(self, origin, *args):
        self.panel_template.pane_show()

    @staticmethod
    def submenu():
        return ("Laser-Tools", "Living-Hinges")
