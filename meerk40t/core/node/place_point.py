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

    def __init__(self, x=0, y=0, rotation=0, corner=0, loops=1, **kwargs):
        self.x = x
        self.y = y
        self.rotation = rotation
        self.corner = corner
        self.loops = loops
        self.output = True
        super().__init__(type="place point", **kwargs)
        self._formatter = "{enabled}{loops}{element_type} {corner} {x} {y} {rotation}"
        self.validate()

    def validate(self):
        if isinstance(self.output, str):
            try:
                self.output = bool(self.output)
            except ValueError:
                self.output = True
        try:
            if isinstance(self.x, str):
                self.x = float(Length(self.x))
            elif isinstance(self.x, Length):
                self.x = float(self.x)
        except ValueError:
            self.x = 0
        try:
            if isinstance(self.y, str):
                self.y = float(Length(self.y))
            elif isinstance(self.y, Length):
                self.y = float(self.y)
        except ValueError:
            self.y = 0
        try:
            if isinstance(self.rotation, str):
                self.rotation = Angle(self.rotation).radians
            elif isinstance(self.rotation, Angle):
                self.rotation = self.rotation.radians
        except ValueError:
            self.rotation = 0
        try:
            self.corner = min(4, max(0, int(self.corner)))
        except ValueError:
            self.corner = 0
        # repetitions at the same point
        if self.loops is None:
            self.loops = 1
        else:
            try:
                self.loops = int(self.loops)
            except ValueError:
                self.loops = 1

    def placements(self, context, outline, matrix, plan):
        if outline is None:
            # This job can't be placed.
            return
        scene_width = context.device.view.unit_width
        scene_height = context.device.view.unit_height
        unit_x = Length(self.x, relative_length=scene_width).units
        unit_y = Length(self.y, relative_length=scene_height).units
        x, y = matrix.point_in_matrix_space((unit_x, unit_y))
        if 0 <= self.corner <= 3:
            cx, cy = outline[self.corner]
        else:
            cx = sum([c[0] for c in outline]) / len(outline)
            cy = sum([c[1] for c in outline]) / len(outline)
        x -= cx
        y -= cy
        shift_matrix = Matrix()
        if self.rotation != 0:
            shift_matrix.post_rotate(self.rotation, cx, cy)
        shift_matrix.post_translate(x, y)

        yield matrix * shift_matrix

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
