"""
Placements are representations of a laserjob origin.
A project may contain multiple such placements, for every placement
a copy of the plan will be executed with the placement indicating
the relative position
"""

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
        **kwargs,
    ):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.nx = nx
        self.ny = ny
        self.alternating_dx = dx
        self.alternating_dy = dy
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

        def _valid_int(field, minim, maxim):
            if field is None:
                value = minim
            try:
                value = min(maxim, max(minim, int(field)))
            except ValueError:
                value = minim
            return value

        if isinstance(self.output, str):
            try:
                self.output = bool(self.output)
            except ValueError:
                self.output = True
        self.x = _valid_length(self.x)
        self.y = _valid_length(self.y)
        self.dx = _valid_length(self.dx)
        self.dy = _valid_length(self.dy)
        try:
            if isinstance(self.rotation, str):
                self.rotation = Angle(self.rotation).radians
            elif isinstance(self.rotation, Angle):
                self.rotation = self.rotation.radians
        except ValueError:
            self.rotation = 0

    def placements(self, context, outline, matrix, plan):
        if outline is None:
            # This job can't be placed.
            return
        scene_width = context.device.view.unit_width
        scene_height = context.device.view.unit_height
        unit_x = Length(self.x, relative_length=scene_width).units
        unit_y = Length(self.y, relative_length=scene_height).units
        org_x, org_y = matrix.point_in_matrix_space((unit_x, unit_y))
        dx, dy = matrix.point_in_matrix_space((self.dx, self.dy))
        if 0 <= self.corner <= 3:
            cx, cy = outline[self.corner]
        else:
            cx = sum([c[0] for c in outline]) / len(outline)
            cy = sum([c[1] for c in outline]) / len(outline)
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

        x = org_x - cx
        # print (f"Generating {xloop}x{yloop}")
        for xcount in range(xloop):
            y = org_y - cy
            for ycount in range(yloop):
                shift_matrix = Matrix()
                if self.rotation != 0:
                    shift_matrix.post_rotate(self.rotation, cx, cy)
                shift_matrix.post_translate(x, y)

                yield matrix * shift_matrix
                y += dy
            x += dx

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

    def drop(self, drag_node, modify=True):
        return False
