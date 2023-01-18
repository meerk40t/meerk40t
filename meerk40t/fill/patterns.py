from copy import copy

from meerk40t.svgelements import Path, Polyline
from meerk40t.tools.geomstr import Geomstr

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
        self.set_predefined_pattern(
            entry=(
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
        self.pattern = list(
            entry[0](self.param_a, self.param_b, outershape=self.outershape)
        )
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
        from meerk40t.tools.geomstr import Clip, Pattern

        p = Pattern()
        p.create_from_pattern(
            self.cutpattern[0], self.param_a, self.param_b, outershape=self.outershape
        )
        p.set_cell_padding(self.cell_padding_h, self.cell_padding_v)
        p.set_cell_dims(self.cell_width, self.cell_height)
        p.extend_pattern = self._extend_patterns  # Grid type

        if self.outershape is None:
            return
        outer_path = self.outershape.as_path()
        if outer_path is None:
            return
        self.path = Geomstr()
        clip = Geomstr()
        for sp in outer_path.as_subpaths():
            pts = [Path(sp).point(i / 100.0, error=1e4) for i in range(101)]
            clip.polyline([complex(pt.x, pt.y) for pt in pts])
            # clip.end()

        q = Clip(clip)
        subject = Geomstr()
        for s in list(p.generate(*q.bounds)):
            subject.append(s)

        if clip_bounds:
            self.path.append(q.clip(subject))
        else:
            self.path.append(subject)

        # self.path.geometry.translate(self.start_x, self.start_y)
        self.preview_path = copy(self.path)


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
