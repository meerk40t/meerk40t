"""
Placements are representations of a laserjob origin.
A project may contain multiple such placements, for every placement
a copy of the plan will be executed with the placement indicating
the relative position
"""
import ast
from math import tau

from meerk40t.core.node.node import Node
from meerk40t.core.units import Angle, Length
from meerk40t.svgelements import Matrix


class PlacePointNode(Node):
    """
    PlacePointNode is the bootstrapped node type for the 'place point' type.
    """

    def __init__(
        self,
        x=0,
        y=0,
        rotation=0,
        corner=0,
        loops=1,
        dx=0,
        dy=0,
        nx=1,
        ny=1,
        alternating_dx=0,
        alternating_dy=0,
        alternate_rot_x=False,
        alternate_rot_y=False,
        orientation=0,
        start_index=0,
        repetitions=0,
        **kwargs,
    ):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.nx = nx
        self.ny = ny
        self.start_index = start_index
        self.repetitions = repetitions
        """
        Orientation defines the sequence of placement points
        0 = standard
        1 = Boustrodephon - horizontal (snake movement along the rows)
        2 = Boustrodephon - vertical (snake movement along the columns)
        Example for 3 x 3 grid
        Standard       Horizontal      Vertical
        1 2 3          1 2 3           1 6 7
        4 5 6          6 5 4           2 5 8
        7 8 9          7 8 9           3 4 9

        """
        self.orientation = orientation
        if self.orientation is None or self.orientation not in (0, 1, 2):
            self.orientation = 0
        # Alternating are factors that decide if and by what amount
        # every other line will be displaced (alternating dy)
        # and/or every column will be displaced (alternating dx)
        # These are factors between -1 and +1
        self.alternating_dx = alternating_dx
        self.alternating_dy = alternating_dy
        self.alternate_rot_x = alternate_rot_x
        self.alternate_rot_y = alternate_rot_y
        self.rotation = rotation
        self.corner = corner
        self.loops = loops
        self.output = True
        super().__init__(type="place point", **kwargs)
        self._formatter = (
            "{enabled}{loops}{element_type}{grid} {corner} {x} {y} {rotation}"
        )
        self.validate()

    def validate(self):
        def _valid_bool(field):
            if isinstance(field, str):
                try:
                    value = bool(ast.literal_eval(field))
                except (ValueError, SyntaxError):
                    value = False
            else:
                try:
                    value = bool(field)
                except ValueError:
                    value = False
            return value

        def _valid_length(field):
            try:
                if isinstance(field, str):
                    value = float(Length(field))
                elif isinstance(field, Length):
                    value = float(field)
                else:
                    value = field
            except ValueError:
                value = 0
            return value

        def _valid_angle(field):
            try:
                if isinstance(field, str):
                    value = Angle(field).radians
                elif isinstance(field, Angle):
                    value = field.radians
                else:
                    value = field
            except ValueError:
                value = 0
            return value

        def _valid_int(field, minim=None, maxim=None):
            # if field is None:
            #     if minim is None:
            #         value = 0
            #     else:
            #         value = minim
            try:
                value = int(field)
                if minim is not None and value < minim:
                    value = minim
                if maxim is not None and value > maxim:
                    value = maxim
            except ValueError:
                value = minim
            return value

        def _valid_float(field, minim=None, maxim=None):
            # if field is None:
            #     if minim is None:
            #         value = 0
            #     else:
            #         value = minim
            try:
                value = float(field)
                if minim is not None and value < minim:
                    value = minim
                if maxim is not None and value > maxim:
                    value = maxim
            except ValueError:
                value = minim
            return value

        self.output = _valid_bool(self.output)
        self.alternate_rot_x = _valid_bool(self.alternate_rot_x)
        self.alternate_rot_y = _valid_bool(self.alternate_rot_y)
        self.x = _valid_length(self.x)
        self.y = _valid_length(self.y)
        self.dx = _valid_length(self.dx)
        self.dy = _valid_length(self.dy)
        self.alternating_dx = _valid_float(self.alternating_dx)
        self.alternating_dy = _valid_float(self.alternating_dy)
        self.rotation = _valid_angle(self.rotation)
        self.loops = _valid_int(self.loops, 1, None)
        self.corner = _valid_int(self.corner, 0, 4)
        self.nx = _valid_int(self.nx, 0, None)
        self.ny = _valid_int(self.ny, 0, None)
        self.start_index = _valid_int(self.start_index, 0, None)
        self.repetitions = _valid_int(self.repetitions, 0, None)

    def placements(self, context, outline, matrix, plan):
        if outline is None:
            # This job can't be placed.
            return
        scene_width = context.device.view.unit_width
        scene_height = context.device.view.unit_height
        unit_x = Length(self.x, relative_length=scene_width).units
        unit_y = Length(self.y, relative_length=scene_height).units
        org_x, org_y = matrix.point_in_matrix_space((unit_x, unit_y))
        unit_x2 = Length(self.x + self.dx, relative_length=scene_width).units
        unit_y2 = Length(self.y + self.dy, relative_length=scene_height).units
        odx, ody = matrix.point_in_matrix_space((unit_x2, unit_y2))
        dx = odx - org_x
        dy = ody - org_y

        ccx = sum([c[0] for c in outline]) / len(outline)
        ccy = sum([c[1] for c in outline]) / len(outline)
        if 0 <= self.corner <= 3:
            cx, cy = outline[self.corner]
        else:
            cx = ccx
            cy = ccy
        # Create grid...
        xloop = self.nx
        if xloop == 0:  # as much as we can fit
            if abs(self.dx) < 1e-6:
                xloop = 1
            else:
                x = self.x
                while x + self.dx < scene_width:
                    x += self.dx
                    xloop += 1
        yloop = self.ny
        if yloop == 0:  # as much as we can fit
            if abs(self.dy) < 1e-6:
                yloop = 1
            else:
                y = self.y
                while y + self.dy < scene_height:
                    y += self.dy
                    yloop += 1
        result = []
        sorted_result = []
        y = org_y - cy
        # print (f"Generating {xloop}x{yloop}")
        for ycount in range(yloop):
            roty = 0
            x = org_x - cx
            xx = x
            if ycount % 2 == 1:
                if self.alternating_dx != 0:
                    xx += self.alternating_dx * abs(dx)
                if self.alternate_rot_y:
                    roty = tau / 2
            for xcount in range(xloop):
                rotx = 0
                yy = y
                if xcount % 2 == 1:
                    if self.alternating_dy != 0:
                        yy += self.alternating_dy * abs(dy)
                    if self.alternate_rot_x:
                        rotx = tau / 2
                shift_matrix = Matrix()
                rotangle = rotx + roty
                if self.rotation != 0:
                    shift_matrix.post_rotate(self.rotation, cx, cy)
                if rotangle != 0:
                    shift_matrix.post_rotate(rotangle, ccx, ccy)
                shift_matrix.post_translate(xx, yy)
                result.append(matrix * shift_matrix)
                xx += dx
            y += dy

        def idx_horizontal(row, col):
            return row * xloop + col

        def idx_vertical(col, row):
            return row * xloop + col

        if self.orientation == 2:
            max_outer = xloop
            max_inner = yloop
            func = idx_vertical
            hither = True
        elif self.orientation == 1:
            max_outer = yloop
            max_inner = xloop
            func = idx_horizontal
            hither = True
        else:
            max_outer = yloop
            max_inner = xloop
            func = idx_horizontal
            hither = False

        p_idx = 0
        p_count = 0
        s_index = self.start_index
        if s_index is None:
            s_index = 0
        if s_index > max_outer * max_inner - 1:
            s_index = max_outer * max_inner - 1
        s_count = self.repetitions
        if s_count is None or s_count < 0:
            s_count = 0
        if s_count == 0:
            s_count = max_inner * max_outer

        for idx_outer in range(max_outer):
            for idx_inner in range(max_inner):
                if hither and idx_outer % 2 == 1:
                    sorted_idx = func(idx_outer, max_inner - 1 - idx_inner)
                else:
                    sorted_idx = func(idx_outer, idx_inner)
                # print (f"p_idx={p_idx}, p_count={p_count}, s_index={s_index}, s_count={s_count}")
                if p_idx >= s_index and p_count < s_count:
                    sorted_result.append(result[sorted_idx])
                    p_count += 1

                p_idx += 1

        for mat in sorted_result:
            yield mat

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Placement"
        default_map.update(self.__dict__)
        try:
            xlen = Length(self.x, digits=2)
            # print (f"{float(xlen):.2f} = {xlen.length_cm}")
        except ValueError:
            xlen = Length(0, digits=2)
        try:
            ylen = Length(self.y, digits=2)
        except ValueError:
            ylen = Length(0, digits=2)
        # print (self.x, self.y, type(self.x).__name__, type(self.y).__name__,)
        default_map["position"] = f"{xlen.length_cm}, {ylen.length_cm}"
        default_map["x"] = f"{xlen.length_cm}"
        default_map["y"] = f"{ylen.length_cm}"
        default_map["rotation"] = f"{Angle(self.rotation, digits=1).degrees}°"
        default_map["loops"] = f"{str(self.loops) + 'X ' if self.loops > 1 else ''}"
        if self.nx != 1 or self.ny != 1:
            default_map["grid"] = f"{self.nx}x{self.ny}"
        else:
            default_map["grid"] = ""

        if self.corner == 0:
            default_map["corner"] = "`+ "
        elif self.corner == 1:
            default_map["corner"] = " +'"
        elif self.corner == 2:
            default_map["corner"] = " +."
        elif self.corner == 3:
            default_map["corner"] = ".+ "
        else:
            default_map["corner"] = " + "
        default_map["enabled"] = "(Disabled) " if not self.output else ""

        return default_map

