from copy import copy

from numpy import linspace

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
from meerk40t.tools.geomstr import Geomstr
from meerk40t.tools.pathtools import VectorMontonizer


_FACTOR = 1000


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
        self.cell_height_percentage = 200
        self.cell_width_percentage = 200
        self.cell_height = height * self.cell_height_percentage / _FACTOR
        self.cell_width = width * self.cell_width_percentage / _FACTOR
        self.cell_padding_v_percentage = 0
        self.cell_padding_h_percentage = 0
        self.cell_padding_h = self.cell_width * self.cell_padding_h_percentage / _FACTOR
        self.cell_padding_v = (
            self.cell_height * self.cell_padding_v_percentage / _FACTOR
        )
        # Requires recalculation
        self.path = None
        self.preview_path = None
        self.outershape = None
        # Specifically for the shape pattern we hold a list of precalculated polygons
        self.pattern = []
        self._extend_patterns = True
        self.set_cell_values(100, 100)
        self.set_padding_values(50, 50)
        self.set_predefined_pattern(entry=(
                set_line,
                False,
                "",
                "",
                (-200, -350, 0, 0),
                True,
            )
        )
        self.cutpattern = None

    def set_hinge_shape(self, shapenode):
        # reset cache
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
        self.preview_path = None

    def set_cell_values(self, percentage_x, percentage_y):
        self.cell_width_percentage = percentage_x
        self.cell_height_percentage = percentage_y
        self.cell_height = self.height * self.cell_height_percentage / _FACTOR
        self.cell_width = self.width * self.cell_width_percentage / _FACTOR
        # Requires recalculation
        self.path = None
        self.preview_path = None

    def set_padding_values(self, padding_x, padding_y):
        self.cell_padding_h_percentage = padding_x
        self.cell_padding_v_percentage = padding_y

        self.cell_padding_h = self.cell_width * self.cell_padding_h_percentage / _FACTOR
        self.cell_padding_v = (
            self.cell_height * self.cell_padding_v_percentage / _FACTOR
        )
        # Requires recalculation
        self.path = None
        self.preview_path = None

    def set_predefined_pattern(self, entry):
        # The pattern needs to be defined within a 0,0  - 1,1 rectangle
        #
        self.cutpattern = entry

        self._extend_patterns = entry[5]
        additional_parameter = entry[1]
        info1 = entry[2]
        info2 = entry[3]
        self.pattern = list(entry[0](self.param_a, self.param_b, outershape=self.outershape))
        return additional_parameter, info1, info2

    def set_additional_parameters(self, param_a, param_b):
        self.param_a = param_a
        self.param_b = param_b
        # Reset cache for shape pattern
        # Make sure pattern is updated with additional parameter
        self.set_predefined_pattern(self.cutpattern)

    @staticmethod
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

    def generate(self, show_outline=False, force=False, final=False, clip_bounds=True):
        if final and self.path is not None and not force:
            # No need to recalculate...
            return
        elif not final and self.preview_path is not None and not force:
            # No need to recalculate...
            return
        from meerk40t.tools.geomstr import Pattern
        from meerk40t.tools.geomstr import Clip
        from meerk40t.tools.geomstr import Polygon as Gpoly

        p = Pattern()
        p.create_from_pattern(self.cutpattern[0], self.param_a, self.param_b, outershape=self.outershape)
        p.set_cell_padding(self.cell_padding_h, self.cell_padding_v)
        p.set_cell_dims(self.cell_width, self.cell_height)

        if self.outershape is None:
            return
        outer_path = self.outershape.as_path()
        pts = [outer_path.point(i / 100.0, error=1e4) for i in range(101)]
        poly = Gpoly(*[complex(pt.x, pt.y) for pt in pts])

        q = Clip(poly)
        clip = Geomstr()
        for s in list(p.generate(*q.bounds)):
            clip.append(s)

        if clip_bounds:
            self.path = q.clip(clip)
        else:
            self.path = clip

        # self.path.geometry.translate(self.start_x, self.start_y)
        self.preview_path = copy(self.path)


# class LivingHingesOld:
#     """
#     This class generates a predefined pattern in a *rectangular* area
#     """
#
#     def __init__(self, xpos, ypos, width, height):
#         self.pattern = None
#         self.start_x = xpos
#         self.start_y = ypos
#         self.width = width
#         self.height = height
#         # We set it off somewhat...
#         self.gap = 0
#         self.x0 = width * self.gap
#         self.y0 = height * self.gap
#         self.x1 = width * (1 - self.gap)
#         self.y1 = height * (1 - self.gap)
#         # Declare all used variables to satisfy codacy
#         self.param_a = 0
#         self.param_b = 0
#         self.cell_height_percentage = 200
#         self.cell_width_percentage = 200
#         self.cell_height = height * self.cell_height_percentage / _FACTOR
#         self.cell_width = width * self.cell_width_percentage / _FACTOR
#         self.cell_padding_v_percentage = 0
#         self.cell_padding_h_percentage = 0
#         self.cell_padding_h = self.cell_width * self.cell_padding_h_percentage / _FACTOR
#         self.cell_padding_v = (
#             self.cell_height * self.cell_padding_v_percentage / _FACTOR
#         )
#         # Requires recalculation
#         self.path = None
#         self.previewpath = None
#         self.outershape = None
#         # Specifically for the shape pattern we hold a list of precalculated polygons
#         self.pattern = []
#         self._extend_patterns = True
#         self.set_cell_values(100, 100)
#         self.set_padding_values(50, 50)
#         self.set_predefined_pattern(entry=(
#                 set_line,
#                 False,
#                 "",
#                 "",
#                 (-200, -350, 0, 0),
#                 True,
#             )
#         )
#         self.cutpattern = None
#
#     def set_predefined_pattern(self, entry):
#         # The pattern needs to be defined within a 0,0  - 1,1 rectangle
#         #
#         self.cutpattern = entry
#
#         self._extend_patterns = entry[5]
#         additional_parameter = entry[1]
#         info1 = entry[2]
#         info2 = entry[3]
#         self.pattern = list(entry[0](self.param_a, self.param_b, outershape=self.outershape))
#         self.path = None
#         self.previewpath = None
#         return additional_parameter, info1, info2
#
#     def make_outline(self, x0, y0, x1, y1):
#         # Draw a rectangle
#         pt0 = Point(x0, y0)
#         pt1 = Point(x1, y0)
#         pt2 = Point(x1, y1)
#         pt3 = Point(x0, y1)
#
#         self.path.move(pt0)
#         self.path.line(pt1)
#         self.path.line(pt2)
#         self.path.line(pt3)
#         self.path.line(pt0)
#
#     def draw_trace(self, offset_x, offset_y, width, height):
#         # Draw the pattern
#         # The extents of the cell will be at (offset_x, offset_y)
#         # in the upper-left corner and (width, height) in the bottom-right corner
#
#         def create_point(x, y):
#             return Point(x * width + offset_x, y * height + offset_y)
#
#         # self.path.move(offset_x, offset_y)
#         # print (f"After initial move: {str(self.path)}")
#         current_x = 0
#         current_y = 0
#         s_left = self.start_x
#         s_right = s_left + self.width
#         s_top = self.start_y
#         s_bottom = s_top + self.height
#         for entry in self.pattern:
#             old_x = current_x
#             old_y = current_y
#             key = entry[0].lower()
#             if key == "m":
#                 endpoint = create_point(entry[1], entry[2])
#                 self.path.move(endpoint)
#                 current_x = entry[1]
#                 current_y = entry[2]
#             elif key == "h":
#                 current_x += entry[1]
#                 dx = entry[1]
#                 self.path.horizontal(dx, relative=True)
#             elif key == "v":
#                 current_y += entry[1]
#                 dy = entry[1]
#                 self.path.vertical(dy, relative=True)
#             elif key == "l":
#                 # Line to...
#                 current_x = entry[1]
#                 current_y = entry[2]
#                 endpoint = create_point(entry[1], entry[2])
#                 self.path.line(endpoint)
#             elif key == "a":
#                 current_x = entry[6]
#                 current_y = entry[7]
#                 rx = entry[1]
#                 ry = entry[2]
#                 rotation = entry[3]
#                 arc = entry[4]
#                 sweep = entry[5]
#                 endpoint = create_point(current_x, current_y)
#                 self.path.arc(rx, ry, rotation, arc, sweep, endpoint)
#             elif key == "c":
#                 current_x = entry[5]
#                 current_y = entry[6]
#                 control1 = create_point(entry[1], entry[2])
#                 control2 = create_point(entry[3], entry[4])
#                 endpoint = create_point(entry[5], entry[6])
#                 self.path.cubic(control1, control2, endpoint)
#             elif key == "q":
#                 current_x = entry[3]
#                 current_y = entry[4]
#                 control1 = create_point(entry[1], entry[2])
#                 endpoint = create_point(entry[3], entry[4])
#                 self.path.quad(control1, endpoint)
#
#     def set_hinge_shape(self, shapenode):
#         # reset cache
#         self.outershape = shapenode
#
#     def set_hinge_area(self, hinge_left, hinge_top, hinge_width, hinge_height):
#         self.start_x = hinge_left
#         self.start_y = hinge_top
#         self.width = hinge_width
#         self.height = hinge_height
#         self.x0 = hinge_width * self.gap
#         self.y0 = hinge_height * self.gap
#         self.x1 = hinge_width * (1 - self.gap)
#         self.y1 = hinge_height * (1 - self.gap)
#         # Requires recalculation
#         self.path = None
#         self.previewpath = None
#
#     def set_cell_values(self, percentage_x, percentage_y):
#         self.cell_width_percentage = percentage_x
#         self.cell_height_percentage = percentage_y
#         # Requires recalculation
#         self.path = None
#         self.previewpath = None
#
#     def set_padding_values(self, padding_x, padding_y):
#         self.cell_padding_h_percentage = padding_x
#         self.cell_padding_v_percentage = padding_y
#         # Requires recalculation
#         self.path = None
#         self.preview_path = None
#
#     def set_additional_parameters(self, param_a, param_b):
#         self.param_a = param_a
#         self.param_b = param_b
#         # Reset cache for shape pattern
#         # Make sure pattern is updated with additional parameter
#         self.set_predefined_pattern(self.cutpattern)
#
#     def generate(self, show_outline=False, force=False, final=False):
#         if final and self.path is not None and not force:
#             # No need to recalculate...
#             return
#         elif not final and self.preview_path is not None and not force:
#             # No need to recalculate...
#             return
#         self.path = Path(stroke=Color("red"), stroke_width=500)
#         self._generate_pattern(show_outline)
#         rectangular = (
#             self.outershape is not None
#             and hasattr(self.outershape, "as_path")
#             and self.outershape.type != "elem rect"
#         )
#         if final and not rectangular:
#             self.path.transform *= Matrix.translate(self.start_x, self.start_y)
#             self.path = self._clip_path_monotonizer()
#         else:
#             # Former method....
#             # ...is limited to rectangular area but maintains inner cubics,
#             # quads and arcs while the vectormontonizer is more versatile
#             # when it comes to the surrounding shape but transforms all
#             # path elements to lines
#             self.path = self._clip_path_rect(self.path, 0, 0, self.width, self.height)
#             self.path.transform *= Matrix.translate(self.start_x, self.start_y)
#             self.previewpath = copy(self.path)
#
#     def _generate_pattern(self, show_outline=False):
#         if show_outline:
#             self.make_outline(self.x0, self.y0, self.x1, self.y1)
#
#         self.cell_width = self.width * self.cell_width_percentage / _FACTOR
#         self.cell_height = self.height * self.cell_height_percentage / _FACTOR
#         self.cell_padding_h = self.cell_width * self.cell_padding_h_percentage / _FACTOR
#         self.cell_padding_v = (
#                 self.cell_height * self.cell_padding_v_percentage / _FACTOR
#         )
#
#         #  Determine rows and columns of cuts to create
#         #  will round down so add 1 and trim later
#         #  Determine rows and columns of cuts to create
#         #  will round down so add 1 and trim later
#         if self.cell_width + 2 * self.cell_padding_h == 0:
#             cols = 1
#         else:
#             cols = (
#                     int(
#                         ((self.x1 - self.x0) + self.cell_width)
#                         / (self.cell_width + (2 * self.cell_padding_h))
#                     )
#                     + 1
#             )
#         if self.cell_height + 2 * self.cell_padding_v == 0:
#             rows = 1
#         else:
#             rows = (
#                     int(
#                         ((self.y1 - self.y0) + self.cell_height)
#                         / (self.cell_height + (2 * self.cell_padding_v))
#                     )
#                     + 1
#             )
#
#         if self._extend_patterns:
#             start_value = -2
#             end_value = 1
#             off_x = -1 * (self.cell_width / 2)
#         else:
#             cols = max(1, cols - 2)
#             rows = max(1, rows - 2)
#             start_value = 0
#             end_value = 0
#             off_x = 0
#         # print (f"Area: {self.width:.1f}, {self.height:.1f}, Cell: {self.cell_width:.1f}, {self.cell_height:.1f}")
#         # print (f"Rows: {rows}, Cols={cols}")
#         # print (f"Ratios: {self.cell_width_percentage}, {self.cell_height_percentage}")
#         # print (f"Padding: {self.cell_padding_h_percentage}, {self.cell_padding_v_percentage}")
#
#         for col in range(start_value, cols + end_value, 1):
#             top_left_x = self.x0 + off_x
#             x_offset = col * (self.cell_width + (2 * self.cell_padding_h))
#             x_current = top_left_x + x_offset
#             for row in range(start_value, rows + end_value, 1):
#                 top_left_y = self.y0
#                 y_offset = row * (self.cell_height + (2 * self.cell_padding_v)) + (
#                         (self.cell_height + (2 * self.cell_padding_v)) / 2
#                 ) * (col % 2)
#                 y_current = top_left_y + y_offset
#
#                 if x_current < self.x1 and y_current < self.y1:
#                     # Don't call draw if outside of hinge area
#                     self.draw_trace(
#                         x_current,
#                         y_current,
#                         self.cell_width,
#                         self.cell_height,
#                     )
#                     if show_outline:
#                         self.make_outline(
#                             x_current,
#                             y_current,
#                             x_current + self.cell_width,
#                             y_current + self.cell_height,
#                         )
#
#     def _clip_path_monotonizer(self):
#         from time import time
#
#         t0 = time()
#         vm = VectorMontonizer()
#         if self.outershape is None:
#             outer_poly = Polygon(
#                 (
#                     Point(self.x0, self.y0),
#                     Point(self.x1, self.y0),
#                     Point(self.x1, self.y1),
#                     Point(self.x0, self.y1),
#                     Point(self.x0, self.y0),
#                 )
#             )
#         else:
#             outer_path = self.outershape.as_path()
#             outer_poly = Polygon(
#                 [outer_path.point(i / 1000.0, error=1e4) for i in range(1001)]
#             )
#         vm.add_polyline(outer_poly)
#         path = Path(stroke=Color("red"), stroke_width=500)
#         deleted = 0
#         total = 0
#         # pt_min_x = 1E+30
#         # pt_min_y = 1E+30
#         # pt_max_x = -1 * pt_min_x
#         # pt_max_y = -1 * pt_min_y
#         # Numpy does not work
#         # vm.add_polyline(outer_poly)
#         # path = Path(stroke=Color("red"), stroke_width=500)
#         # for sub_inner in self.path.as_subpaths():
#         #     sub_inner = Path(sub_inner)
#         #     pts_sub = sub_inner.npoint(linspace(0, 1, 1000))
#         #     good_pts = [p for p in pts_sub if vm.is_point_inside(p[0] + self.start_x, p[1] + self.start_y)]
#         #     path += Path(Polyline(good_pts), stroke=Color("red"), stroke_width=500)
#         for sub_inner in self.path.as_subpaths():
#             sub_inner = Path(sub_inner)
#             pts_sub = [sub_inner.point(i / 1000.0, error=1e4) for i in range(1001)]
#
#             for i in range(len(pts_sub) - 1, -1, -1):
#                 total += 1
#                 pt = pts_sub[i]
#                 pt[0] += self.start_x
#                 pt[1] += self.start_y
#                 # pt_min_x = min(pt_min_x, pt[0])
#                 # pt_min_y = min(pt_min_y, pt[1])
#                 # pt_max_x = max(pt_max_x, pt[0])
#                 # pt_max_y = max(pt_max_y, pt[1])
#                 if not vm.is_point_inside(pt[0], pt[1]):
#                     # if we do have points beyond, then we create a seperate path
#                     if i < len(pts_sub) - 1:
#                         goodpts = pts_sub[i + 1:]
#                         path += Path(
#                             Polyline(goodpts), stroke=Color("red"), stroke_width=500
#                         )
#                     del pts_sub[i:]
#                     deleted += 1
#             path += Path(Polyline(pts_sub), stroke=Color("red"), stroke_width=500)
#         return path
#
#     def _clip_path_rect(self, path, xmin, ymin, xmax, ymax):
#         """
#         Clip a path at a rectangular area, will return the clipped path
#
#         Args:
#             path : The path to clip
#             xmin : Left side of the rectangular area
#             ymin : Upper side of the rectangular area
#             xmax : Right side of the rectangular area
#             ymax : Lower side of the rectangular area
#         """
#
#         def outside(bb_to_check, master_bb):
#             out_x = "inside"
#             out_y = "inside"
#             if bb_to_check[0] > master_bb[2] or bb_to_check[2] < master_bb[0]:
#                 # fully out on x
#                 out_x = "outside"
#             elif bb_to_check[0] < master_bb[0] or bb_to_check[2] > master_bb[2]:
#                 out_x = "cross"
#             if bb_to_check[1] > master_bb[3] or bb_to_check[3] < master_bb[1]:
#                 out_y = "outside"
#             elif bb_to_check[1] < master_bb[1] or bb_to_check[3] > master_bb[3]:
#                 out_x = "cross"
#             return out_x, out_y
#
#         def approximate_line(part_of_path, current_x, current_y):
#             # print(f"Check: {type(part_of_path).__name__} {part_of_path.bbox()} {clipbb}")
#             added = 0
#             partial = 0
#             ignored = 0
#             subj = part_of_path.npoint(linspace(0, 1, interpolation))
#             subj.reshape((2, interpolation))
#             iterated_points = list(map(Point, subj))
#             for p in iterated_points:
#                 segbb = (
#                     min(current_x, p[0]),
#                     min(current_y, p[1]),
#                     max(current_x, p[0]),
#                     max(current_y, p[1]),
#                 )
#                 sx, sy = outside(segbb, clipbb)
#                 # print(f"{segbb} - {clipbb} {sx} - {sy}")
#                 if sx == "outside" or sy == "outside":
#                     # Fully outside, so drop
#                     add_move(newpath, e.end)
#                     ignored += 1
#                 elif statex == "inside" and statey == "inside":
#                     # Fully inside, so append
#                     if current_x != new_cx or current_y != new_cy:
#                         add_move(newpath, Point(current_x, current_y))
#                     newpath.line(p)
#                     added += 1
#                 else:
#                     dx = p[0] - current_x
#                     dy = p[1] - current_y
#                     new_cx = current_x
#                     new_cy = current_y
#                     new_ex = p[0]
#                     new_ey = p[1]
#                     if dx == 0:
#                         # Vertical line needs special treatment
#                         if new_cx >= xmin and new_cx <= xmax:
#                             new_cy = min(max(new_cy, ymin), ymax)
#                             new_ey = min(max(new_ey, ymin), ymax)
#                             if new_cx != current_x or new_cy != current_y:
#                                 # Needs a move
#                                 add_move(newpath, Point(new_cx, new_cy))
#                             newpath.line(Point(new_ex, new_ey))
#                             partial += 1
#                         else:
#                             ignored += 1
#                     else:
#                         # regular line, so lets establish x0 x1
#                         # could still be an outward pointing line....
#                         new_cx = min(max(new_cx, xmin), xmax)
#                         new_ex = min(max(new_ex, xmin), xmax)
#                         # corresponding y values...
#                         edx = p[0] - current_x
#                         edy = p[1] - current_y
#                         new_cy = current_y + (new_cx - current_x) / edx * edy
#                         new_ey = current_y + (new_ex - current_x) / edx * edy
#                         # Y can still cross...
#                         new_cx_clipped = new_cx
#                         new_ex_clipped = new_ex
#                         new_cy_clipped = min(max(new_cy, ymin), ymax)
#                         new_ey_clipped = min(max(new_ey, ymin), ymax)
#                         # Adjust x - value
#                         if dy != 0:
#                             new_cx_clipped = new_cx + dx / dy * (
#                                 new_cy_clipped - new_cy
#                             )
#                             new_ex_clipped = new_ex + dx / dy * (
#                                 new_ey_clipped - new_ey
#                             )
#
#                         new_cx = new_cx_clipped
#                         new_cy = new_cy_clipped
#                         new_ex = new_ex_clipped
#                         new_ey = new_ey_clipped
#                         if min(new_cy, new_ey) == ymax and dy != 0:
#                             # Outward...
#                             ignored += 1
#                         elif max(new_cy, new_ey) == ymin and dy != 0:
#                             # Outward...
#                             ignored += 1
#                         else:
#                             if new_cx != current_x or new_cy != current_y:
#                                 # Needs a move
#                                 add_move(newpath, Point(new_cx, new_cy))
#                             newpath.line(Point(new_ex, new_ey))
#                             partial += 1
#                 current_x = p[0]
#                 current_y = p[1]
#             if current_x != part_of_path.end[0] or current_y != part_of_path.end[1]:
#                 add_move(newpath, part_of_path.end)
#             # print (f"From iterated line: added={added}, partial={partial}, ignored={ignored}")
#
#         def add_move(addpath, destination):
#             # Was the last segment as well a move? Then just update the coords...
#             if len(addpath) > 0:
#                 if isinstance(addpath[-1], Move):
#                     addpath[-1].end = destination
#                     return
#             addpath.move(destination)
#
#         interpolation = 50
#         fully_deleted = 0
#         partial_deleted = 0
#         not_deleted = 0
#         clipbb = (xmin, ymin, xmax, ymax)
#         current_x = 0
#         current_y = 0
#         first_point = path.first_point
#         if first_point is not None:
#             current_x = first_point[0]
#             current_y = first_point[1]
#         newpath = Path(
#             stroke=path.stroke, stroke_width=path.stroke_width, transform=path.transform
#         )
#         for e in path:
#             if hasattr(e, "bbox"):
#                 segbb = e.bbox()
#             elif hasattr(e, "end"):
#                 segbb = (
#                     min(current_x, e.end[0]),
#                     min(current_y, e.end[1]),
#                     max(current_x, e.end[0]),
#                     max(current_y, e.end[1]),
#                 )
#             else:
#                 segbb = (xmin, ymin, 0, 0)
#             if isinstance(e, Move):
#                 add_move(newpath, e.end)
#                 current_x = e.end[0]
#                 current_y = e.end[1]
#                 not_deleted += 1
#             elif isinstance(e, Line):
#                 statex, statey = outside(segbb, clipbb)
#                 dx = e.end[0] - current_x
#                 dy = e.end[1] - current_y
#                 if statex == "outside" or statey == "outside":
#                     # Fully outside, so drop
#                     add_move(newpath, e.end)
#                     fully_deleted += 1
#                 elif statex == "inside" and statey == "inside":
#                     # Fully inside, so append
#                     newpath.line(e.end)
#                     not_deleted += 1
#                 else:
#                     # needs dealing, its either for the time being, just ignored...
#                     new_cx = current_x
#                     new_cy = current_y
#                     new_ex = e.end[0]
#                     new_ey = e.end[1]
#                     if dx == 0:
#                         # Vertical line needs special treatment
#                         if new_cx >= xmin and new_cx <= xmax:
#                             new_cy = min(max(new_cy, ymin), ymax)
#                             new_ey = min(max(new_ey, ymin), ymax)
#                             if new_cx != current_x or new_cy != current_y:
#                                 # Needs a move
#                                 add_move(newpath, Point(new_cx, new_cy))
#                             newpath.line(Point(new_ex, new_ey))
#                     else:
#                         # regular line, so lets establish x0 x1
#                         # could still be an outward pointing line....
#                         new_cx = min(max(new_cx, xmin), xmax)
#                         new_ex = min(max(new_ex, xmin), xmax)
#                         # corresponding y values...
#                         edx = e.end[0] - current_x
#                         edy = e.end[1] - current_y
#                         new_cy = current_y + (new_cx - current_x) / edx * edy
#                         new_ey = current_y + (new_ex - current_x) / edx * edy
#                         # Y can still cross...
#                         new_cx_clipped = new_cx
#                         new_ex_clipped = new_ex
#                         new_cy_clipped = min(max(new_cy, ymin), ymax)
#                         new_ey_clipped = min(max(new_ey, ymin), ymax)
#                         # Adjust x - value
#                         if dy != 0:
#                             new_cx_clipped = new_cx + dx / dy * (
#                                 new_cy_clipped - new_cy
#                             )
#                             new_ex_clipped = new_ex + dx / dy * (
#                                 new_ey_clipped - new_ey
#                             )
#
#                         new_cx = new_cx_clipped
#                         new_cy = new_cy_clipped
#                         new_ex = new_ex_clipped
#                         new_ey = new_ey_clipped
#                         if min(new_cy, new_ey) == ymax and dy != 0:
#                             # Outward...
#                             pass
#                         elif max(new_cy, new_ey) == ymin and dy != 0:
#                             # Outward...
#                             pass
#                         else:
#                             if new_cx != current_x or new_cy != current_y:
#                                 # Needs a move
#                                 add_move(newpath, Point(new_cx, new_cy))
#                             newpath.line(Point(new_ex, new_ey))
#                     if current_x != e.end[0] or current_y != e.end[1]:
#                         add_move(newpath, e.end)
#                     partial_deleted += 1
#                 current_x = e.end[0]
#                 current_y = e.end[1]
#             elif isinstance(e, Close):
#                 newpath.closed()
#                 not_deleted += 1
#             elif isinstance(e, QuadraticBezier):
#                 statex, statey = outside(segbb, clipbb)
#                 if statex == "outside" and statey == "outside":
#                     # Fully outside, so drop
#                     add_move(newpath, e.end)
#                     fully_deleted += 1
#                 elif statex == "inside" and statey == "inside":
#                     # Fully inside, so append
#                     newpath.quad(e.control, e.end)
#                     not_deleted += 1
#                 else:
#                     approximate_line(e, current_x, current_y)
#                 current_x = e.end[0]
#                 current_y = e.end[1]
#             elif isinstance(e, CubicBezier):
#                 statex, statey = outside(segbb, clipbb)
#                 if statex == "outside" and statey == "outside":
#                     # Fully outside, so drop
#                     add_move(newpath, e.end)
#                     fully_deleted += 1
#                 elif statex == "inside" and statey == "inside":
#                     # Fully inside, so append
#                     newpath.cubic(e.control1, e.control2, e.end)
#                     not_deleted += 1
#                 else:
#                     approximate_line(e, current_x, current_y)
#                     partial_deleted += 1
#                 current_x = e.end[0]
#                 current_y = e.end[1]
#             elif isinstance(e, Arc):
#                 for e_cubic in e.as_cubic_curves():
#                     segbb = e_cubic.bbox()
#                     statex, statey = outside(segbb, clipbb)
#                     if statex == "outside" and statey == "outside":
#                         # Fully outside, so drop
#                         add_move(newpath, e.end)
#                         fully_deleted += 1
#                     elif statex == "inside" and statey == "inside":
#                         # Fully inside, so append
#                         newpath.cubic(e_cubic.control1, e_cubic.control2, e_cubic.end)
#                         not_deleted += 1
#                     else:
#                         approximate_line(e_cubic, current_x, current_y)
#                         partial_deleted += 1
#                     current_x = e_cubic.end[0]
#                     current_y = e_cubic.end[1]
#                 current_x = e.end[0]
#                 current_y = e.end[1]
#
#         flag = True
#         while flag:
#             flag = False
#             if len(newpath) > 0 and isinstance(newpath[-1], Move):
#                 # We dont need a move at the end of the path...
#                 newpath._segments.pop(-1)
#                 flag = True
#
#         # print(
#         #     f"Ready: left untouched: {not_deleted}, fully deleted={fully_deleted}, partial deletion:{partial_deleted}"
#         # )
#         return newpath
#

def set_line(*args, **kwargs):
    yield "M", 0, 0.5
    yield "L", 1, 0.5


def set_fishbone(a, b, *args, **kwargs):
    dx = a / 5.0 * 0.5
    dy = b / 5.0 * 0.5
    yield "M", 0 + dx, 1 - dy
    yield "L", 0.5, 0
    # self.pattern.append(("M", 0.5, 0))
    yield "L", 1 - dx, 1 - dy


def set_diagonal(a, b, *args, **kwargs):
    dx = a / 5.0 * 1.0
    dy = b / 5.0 * 1.0
    yield "M", 0 + dx, 1 - dy
    yield "L", 1 - dx, 0 + dy


def set_diamond1(a, b, *args, **kwargs):
    yield "M", 0, 0.5
    yield "L", 0.5, 0
    yield "L", 1, 0.5
    yield "L", 0.5, 1
    yield "L", 0, 0.5


def set_diamond2(a, b, *args, **kwargs):
    yield "M", 0, 0
    yield "L", 0.5, 0.4
    yield "L", 1, 0
    yield "M", 0, 1
    yield "L", 0.5, 0.6
    yield "L", 1, 1


def set_cross(a, b, *args, **kwargs):
    # Pattern: cross
    dx = a / 5.0 * 0.5
    dy = b / 5.0 * 0.5
    yield "M", 0.0, 0.25 + dy
    yield "L", 0.25 + dx, 0.50
    yield "L", 0.0, 0.75 - dy
    yield "M", 0.25 + dx, 0.50
    yield "L", 0.75 - dx, 0.50
    yield "M", 1, 0.25 + dy
    yield "L", 0.75 - dx, 0.50
    yield "L", 1, 0.75 - dy


def set_fabric(a, b, *args, **kwargs):
    yield "M", 0.25, 0.25
    yield "L", 0, 0.25
    yield "L", 0, 0
    yield "L", 0.5, 0
    yield "L", 0.5, 1
    yield "L", 1, 1
    yield "L", 1, 0.75
    yield "L", 0.75, 0.75

    yield "M", 0.75, 0.25
    yield "L", 0.75, 0
    yield "L", 1, 0
    yield "L", 1, 0.5
    yield "L", 0, 0.5
    yield "L", 0, 1
    yield "L", 0.25, 1
    yield "L", 0.25, 0.75


def set_beehive(a, b, *args, **kwargs):
    dx = a / 5.0 * 0.5
    dy = b / 5.0 * 0.5
    # top
    yield "M", 0, 0.5 - dy
    yield "L", dx, dy
    yield "L", 1 - dx, dy
    yield "L", 1, 0.5 - dy
    # inner
    yield "M", 0, 0.5
    yield "L", dx, 2 * dy
    yield "L", 1 - dx, 2 * dy
    yield "L", 1, 0.5
    yield "L", 1 - dx, 1 - 2 * dy
    yield "L", dx, 1 - 2 * dy
    yield "L", 0, 0.5
    # bottom
    yield "M", 0, 0.5 + dy
    yield "L", dx, 1 - dy
    yield "L", 1 - dx, 1 - dy
    yield "L", 1, 0.5 + dy


def set_bowlingpin(a, b, *args, **kwargs):
    yield "M", 0.2, 0.6
    ctrl_x = 0.1 + a
    ctrl_y = 0.5
    yield "Q", ctrl_x, ctrl_y, 0.2, 0.4

    ctrl_x = 0.5
    ctrl_y = 0.1 - b
    yield "Q", ctrl_x, ctrl_y, 0.8, 0.4

    ctrl_x = 0.9 - a
    ctrl_y = 0.5
    yield "Q", ctrl_x, ctrl_y, 0.8, 0.6

    ctrl_x = 0.5
    ctrl_y = 0.9 + b
    yield "Q", ctrl_x, ctrl_y, 0.2, 0.6


def set_wave(a, b, *args, **kwargs):
    # Pattern: wavy
    yield "M", 0.0, 0.25
    yield "L", 0.25, 0.25
    ctrl_x = 0.5 + a
    ctrl_y = 0.25 + b
    yield "Q", ctrl_x, ctrl_y, 0.5, 0.5
    ctrl_x = 0.5 - a
    ctrl_y = 0.75 - b
    yield "Q", ctrl_x, ctrl_y, 0.75, 0.75
    yield "L", 1, 0.75


def set_bezier(a, b, *args, **kwargs):
    anchor_tip = a  # distance factor from anchor to place control point
    anchor_center = b
    yield "M", 0, 0
    yield "C", 1 * anchor_tip, 0, 1 / 2 - (1 * anchor_center), 1, 1 / 2, 1
    yield "C", 1 / 2 + (1 * anchor_center), 1, 1 * (1 - anchor_tip), 0, 1, 0


def set_brackets(a, b, *args, **kwargs):
    p_a = a
    p_b = b
    yield "M", 0.0, 0.5
    yield "C", 0.0, p_a, 1.0, p_b, 1.0, 0.5
    yield "C", 1.0, 1 - p_a, 0.0, 1 - p_b, 0.0, 0.5


def set_shape(a, b, *args, outershape=None, **kwargs):
    # concentric shapes
    polycache = list()

    if len(polycache) != 0:
        # We've done our bit already
        return
    resolution = 200.0
    if outershape is None:
        shape = Path(Polyline((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)))
    else:
        shape = outershape.as_path()
    bb = shape.bbox()
    wd = bb[2] - bb[0]
    if wd == 0:
        wd = 1
    ht = bb[3] - bb[1]
    if ht == 0:
        ht = 1
    tx = 0
    ty = 0
    tc = int(resolution)
    # minx = miny = 1e18
    # maxx = maxy = -1e18
    # Convert to polygon and bring it to 0 / 1
    if wd == 0:
        ratiox = 1
    else:
        ratiox = 1 / wd

    if ht == 0:
        ratioy = 1
    else:
        ratioy = 1 / ht
    amount = int(abs(10 * a))  # (1 to 50)
    segments = int(abs(10 * b))
    seg_break = int(resolution) / (segments + 1)
    seg_len = resolution / 40.0
    for i in range(int(resolution) + 1):
        pt = shape.point(i / resolution, error=1e4)
        pt[0] = (pt[0] - bb[0]) * ratiox
        pt[1] = (pt[1] - bb[1]) * ratioy
        xx = pt[0]
        yy = pt[1]
        tx += xx
        ty += yy
        # minx = min(minx, xx)
        # miny = min(miny, yy)
        # maxx = max(maxx, xx)
        # maxy = max(maxy, yy)
        polycache.append(pt)
    geometric_center_x = tx / tc
    geometric_center_y = ty / tc
    # print(
    #     f"geometric center master: {geometric_center_x:.1f}, {geometric_center_y:.1f}"
    # )
    # print(f"boundaries: {minx:.1f}, {miny:.1f} - {maxx:.1f}, {maxy:.1f}")
    dx = 0
    dy = 0
    regular = False
    ratio = 1.0
    dx = 1.0 / (amount + 1)

    ratio = 1
    for num in range(amount):
        ratio -= dx
        regular = not regular
        current_x = None
        current_y = None
        if regular:
            segcount = int(seg_break * 0.25)
        else:
            segcount = int(seg_break * 0.5)
        # tx = 0
        # ty = 0
        # minx = miny = 1e18
        # maxx = maxy = -1e18
        for i in range(int(resolution) + 1):
            xx = (polycache[i][0] - geometric_center_x) * ratio + geometric_center_x
            yy = (polycache[i][1] - geometric_center_y) * ratio + geometric_center_y
            # tx += xx
            # ty += yy
            # minx = min(minx, xx)
            # miny = min(miny, yy)
            # maxx = max(maxx, xx)
            # maxy = max(maxy, yy)
            segcount += 1
            if segcount < seg_break:
                if current_x is None:
                    yield "M", xx, yy
                else:
                    yield "L", xx, yy
                current_x = xx
                current_y = yy
            elif segcount >= seg_break + seg_len:
                segcount = 0
                current_x = None
                current_y = None
        # geo_x = tx / tc
        # geo_y = ty / tc
        # print(f"geometric center copy: {geo_x:.1f}, {geo_y:.1f}")
        # print(f"boundaries: {minx:.1f}, {miny:.1f} - {maxx:.1f}, {maxy:.1f}")


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root
        context.register(
            "pattern/line",
            (
                set_line,
                False,
                "",
                "",
                (-200, -350, 0, 0),
                True,
            ),
        )
        context.register(
            "pattern/fishbone",
            (
                set_fishbone,
                True,
                "Left/Right Indentation",
                "Top/Bottom Indentation",
                (100, 100, 0, 0),
                True,
            ),
        )
        context.register(
            "pattern/diagonal",
            (
                set_diagonal,
                True,
                "Left/Right Indentation",
                "Top/Bottom Indentation",
                (-100, -100, 0, 0),
                True,
            ),
        )
        context.register(
            "pattern/diamond1",
            (
                set_diamond1,
                False,
                "",
                "",
                (-150, 100, 0, 0),
                True,
            ),
        )
        context.register(
            "pattern/diamond2",
            (
                set_diamond2,
                False,
                "",
                "",
                (-120, 60, 0, 0),
                True,
            ),
        )
        context.register(
            "pattern/cross",
            (
                set_cross,
                True,
                "Left/Right Indentation",
                "Top/Bottom Indentation",
                (-150, -40, 0, 0),
                True,
            ),
        )
        context.register(
            "pattern/bezier",
            (
                set_bezier,
                True,
                "",
                "",
                (-20, -160, 0.4, 0.3),
                True,
            ),
        )
        context.register(
            "pattern/wave",
            (
                set_wave,
                True,
                "",
                "",
                (-130, -260, 0, 0),
                True,
            ),
        )
        context.register(
            "pattern/bowlingpin",
            (
                set_bowlingpin,
                True,
                "Left/Right Bowl",
                "Top/Bottom Bowl",
                (-210, -50, -0.3, 0),
                True,
            ),
        )
        context.register(
            "pattern/beehive",
            (
                set_beehive,
                True,
                "Position of left side",
                "Distance of second line",
                (-10, 60, 1.4, 0),
                True,
            ),
        )
        context.register(
            "pattern/fabric",
            (
                set_fabric,
                False,
                "",
                "",
                (-180, 130, 0, 0),
                True,
            ),
        )
        context.register(
            "pattern/brackets",
            (
                set_brackets,
                True,
                "",
                "",
                (-140, -110, 0.7, 0.7),
                True,
            ),
        )
        context.register(
            "pattern/shape",
            (
                set_shape,
                True,
                "Number of copies",
                "Number of segments",
                (0, 0, 1, 0.4),
                False,
            ),
        )
