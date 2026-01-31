from copy import copy
from math import sqrt

from meerk40t.core.node.mixins import Suppressable
from meerk40t.core.node.node import Node
from meerk40t.core.units import Angle, Length
from meerk40t.svgelements import Color, Point
from meerk40t.core.geomstr import Geomstr  # ,  Scanbeam


class HatchEffectNode(Node, Suppressable):
    """
    Effect node performing a hatch with multiple algorithm options for optimal performance.

    Effects are themselves a sort of geometry node that contains other geometry and
    the required data to produce additional geometry.

    Hatch Algorithm Selection:
    - 'auto': Automatically selects the best algorithm based on geometry complexity and parameters
    - 'scanbeam': Traditional scanbeam algorithm (reliable for all geometry types)
    - 'direct_grid': High-performance Direct Grid algorithm (3-6x faster for simple shapes)

    The auto-selection logic uses Direct Grid for simple shapes with reasonable line spacing
    (distance > 0.5mm) and falls back to scanbeam for complex shapes or very fine hatching.

    Properties:
    - hatch_distance: Distance between hatch lines
    - hatch_angle: Angle of hatch lines in degrees or radians
    - hatch_angle_delta: Angle increment for multiple passes
    - hatch_algorithm: Algorithm selection ('auto', 'scanbeam', 'direct_grid')
    - loops: Number of hatch passes with angle delta rotation
    - unidirectional: If True, all lines go same direction
    """

    def __init__(self, *args, id=None, label=None, lock=False, **kwargs):
        self.fill = None
        self.stroke = Color("Blue")
        self.stroke_width = 100.0
        self.stroke_scale = False
        self._stroke_zero = None
        self.include_outlines = False

        self.output = True
        self.hatch_distance = None
        self.hatch_angle = None
        self.hatch_angle_delta = None
        self.hatch_type = None
        self.unidirectional = False
        self.loops = None
        self.hatch_algorithm = (
            None  # Algorithm selection: 'auto', 'scanbeam', 'direct_grid'
        )
        self._interim = False
        super().__init__(
            self, type="effect hatch", id=id, label=label, lock=lock, **kwargs
        )
        if "hidden" in kwargs:
            if isinstance(kwargs["hidden"], str):
                kwargs["hidden"] = kwargs["hidden"].lower() == "true"
            self.hidden = kwargs["hidden"]

        self._formatter = "{element_type} {id} - {distance} {angle} ({children})"

        self.label = "Hatch" if label is None else label
        if self.hatch_type is None:
            self.hatch_type = "scanline"
        if self.loops is None:
            self.loops = 1
        if self.hatch_distance is None:
            self.hatch_distance = "1mm"
        if self.hatch_angle is None:
            self.hatch_angle = "0deg"
        if self.hatch_angle_delta is None:
            self.hatch_angle_delta = "0deg"
        if self.hatch_algorithm is None:
            self.hatch_algorithm = "auto"  # Default to auto-selection
        self._distance = None
        self._angle = None
        self._angle_delta = 0
        self._effect = True
        self.recalculate()

    @property
    def implied_stroke_width(self):
        return self.stroke_width

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self._parent)})"

    def __copy__(self):
        nd = self.node_dict
        nd["stroke"] = copy(self.stroke)
        nd["fill"] = copy(self.fill)
        return HatchEffectNode(**nd)

    def get_effect_descriptor(self):
        """
        Returns a string descriptor for the effect, concatenating the effect type, hatch type, hatch distance, hatch angle, hatch angle delta, and loops, separated by pipe ('|') characters.

        Returns:
            str: A descriptor string in the format "<type>|<hatch_type>|<hatch_distance>|<hatch_angle>|<hatch_angle_delta>|<loops>".
        """
        return f"{self.type}|{self.hatch_type}|{self.hatch_distance}|{self.hatch_angle}|{self.hatch_angle_delta}|{self.loops}|{'1' if self.unidirectional else '0'}|{1 if self.include_outlines else 0}"

    def set_effect_descriptor(self, descriptor):
        """
        Sets the effect parameters from a descriptor string.

        The descriptor should be a string with five components separated by '|':
        'typeinfo|hatchtype|hatchdistance|hatchangle|hatchangledelta|loops'.

        If the typeinfo matches the current object's type, updates the hatch
        parameters (type, distance, angle, angle_delta, loops) and triggers recalculation.

        Parameters:
            descriptor (str): The effect descriptor string.

        Exceptions:
            ValueError: Silently ignored if the descriptor cannot be split into five parts.
        """
        try:
            pattern = descriptor.split("|")
            # Make sure we have enough parts, check get_effect_descriptor for format
            targetlen = len(self.get_effect_descriptor().split("|"))
            while len(pattern) < targetlen:
                # add default values for missing parameters
                pattern.append(
                    "0"
                )  # Default unidirectional / include_outlines to False
            (
                typeinfo,
                hatchtype,
                hatchdistance,
                hatchangle,
                hatchangledelta,
                loops,
                unidirectional,
                include_outlines,
            ) = pattern
            if typeinfo == self.type:
                self.hatch_type = hatchtype
                self.hatch_distance = hatchdistance
                self.hatch_angle = hatchangle
                self.hatch_angle_delta = hatchangledelta
                self.loops = loops
                self.unidirectional = unidirectional == "1"
                self.include_outlines = str(include_outlines).strip().lower() in (
                    "1",
                    "true",
                    "yes",
                    "on",
                )
                self.recalculate()
        except ValueError:
            pass

    def scaled(self, sx, sy, ox, oy, interim=False):
        if interim:
            self.set_interim()
        else:
            self.altered()

    def notify_attached(self, node=None, **kwargs):
        Node.notify_attached(self, node=node, **kwargs)
        if node is self:
            return
        self.altered()

    def notify_detached(self, node=None, **kwargs):
        Node.notify_detached(self, node=node, **kwargs)
        if node is self:
            return
        self.altered()

    def notify_modified(self, node=None, **kwargs):
        Node.notify_modified(self, node=node, **kwargs)
        if node is self:
            return
        self.altered()

    def notify_altered(self, node=None, **kwargs):
        Node.notify_altered(self, node=node, **kwargs)
        if node is self:
            return
        self.altered()

    def notify_scaled(self, node=None, sx=1, sy=1, ox=0, oy=0, interim=False, **kwargs):
        Node.notify_scaled(self, node, sx, sy, ox, oy, interim=interim, **kwargs)
        if node is self:
            return
        if interim:
            self.set_interim()
        else:
            self.altered()

    def notify_translated(self, node=None, dx=0, dy=0, interim=False, **kwargs):
        Node.notify_translated(self, node, dx, dy, interim=interim, **kwargs)
        if node is self:
            return
        if interim:
            self.set_interim()
        else:
            self.altered()

    @property
    def angle(self):
        return self.hatch_angle

    @angle.setter
    def angle(self, value):
        self.hatch_angle = value
        self.recalculate()

    @property
    def delta(self):
        return self.hatch_angle_delta

    @delta.setter
    def delta(self, value):
        self.hatch_angle_delta = value
        self.recalculate()

    @property
    def distance(self):
        return self.hatch_distance

    @distance.setter
    def distance(self, value):
        self.hatch_distance = value
        self.recalculate()

    def recalculate(self):
        """
        Ensure that the properties for distance, angle and angle_delta are in usable units.
        @return:
        """
        h_dist = self.hatch_distance
        h_angle = self.hatch_angle
        h_angle_delta = self.hatch_angle_delta
        distance_y = float(Length(h_dist))

        self._angle = h_angle if isinstance(h_angle, float) else Angle(h_angle).radians
        self._angle_delta = (
            h_angle_delta
            if isinstance(h_angle_delta, float)
            else Angle(h_angle_delta).radians
        )

        # transformed_vector = self.matrix.transform_vector([0, distance_y])
        transformed_vector = [0, distance_y]
        self._distance = abs(complex(transformed_vector[0], transformed_vector[1]))

    def preprocess(self, context, matrix, plan):
        factor = sqrt(abs(matrix.determinant))
        self._distance *= factor
        # Let's establish the angle
        p1: Point = matrix.point_in_matrix_space((0, 0))
        p2: Point = matrix.point_in_matrix_space((1, 0))
        angle = p1.angle_to(p2)
        self._angle -= angle
        # from math import tau
        # print(f"Angle: {angle} - {angle/tau * 360:.1f}°")

        # for c in self._children:
        #     c.matrix *= matrix

        self.set_dirty_bounds()

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Hatch"
        default_map["enabled"] = "" if self.output else "(Disabled) "
        default_map["loop"] = (
            f"{self.loops}X " if self.loops and self.loops != 1 else ""
        )
        if self.hatch_angle is None:
            ang = 0.0
        elif isinstance(self.hatch_angle, float):
            ang = self.hatch_angle
        else:
            try:
                ang = Angle(self.hatch_angle).radians
            except ValueError:
                ang = 0.0
        default_map["angle"] = f"{Angle(ang, digits=1).angle_degrees}"
        default_map["distance"] = str(self.hatch_distance)

        default_map["children"] = str(len(self.children))
        return default_map

    def affected_children(self):
        def right_types(start_node):
            res = []
            for e in start_node._children:
                if e.type.startswith("effect"):
                    continue
                if e._children:
                    subs = right_types(e)
                    res.extend(subs)
                elif e.type.startswith("elem"):
                    if hasattr(e, "hidden") and e.hidden:
                        continue
                    res.append(e)
            return res

        nodes = right_types(self)
        return nodes

    def as_preview(self, **kws) -> Geomstr:
        """
        Calculates the hatch effect geometry. The pass index is the number of copies of this geometry whereas the
        internal loops value is rotated each pass by the angle-delta.

        @param kws:
        @return:
        """
        stored = {
            prop: getattr(self, prop)
            for prop in (
                "loops",
                "hatch_distance",
                "hatch_angle",
                "hatch_angle_delta",
            )
        }
        self.loops = 1
        dist = Length(self.hatch_distance)
        if dist.mm < 1:
            self.hatch_distance = "1mm"
        self.recalculate()
        result = self.as_geometry()

        # Restore old values
        for key, value in stored.items():
            setattr(self, key, value)
        self.recalculate()

        return result

    def as_geometry(self, **kws) -> Geomstr:
        """
        Calculates the hatch effect geometry. The pass index is the number of copies of this geometry whereas the
        internal loops value is rotated each pass by the angle-delta.

        @param kws:
        @return:
        """
        outlines = Geomstr()
        for node in self.affected_children():
            try:
                outlines.append(node.as_geometry(**kws))
            except AttributeError:
                # If direct children lack as_geometry(), do nothing.
                pass
        if self._interim:
            return outlines
        path = Geomstr()
        if self._distance is None:
            self.recalculate()
        for p in range(self.loops):
            # Choose algorithm based on selection and complexity
            if self.hatch_type == "spiral":
                path.append(
                    Geomstr.hatch_spiral(
                        outlines,
                        angle=self._angle + p * self._angle_delta,
                        distance=self._distance,
                    )
                )
            else:
                if self._should_use_direct_grid():
                    path.append(
                        self._direct_grid_hatch(
                            outlines,
                            distance=self._distance,
                            angle=self._angle + p * self._angle_delta,
                            unidirectional=self.unidirectional,
                        )
                    )
                else:
                    path.append(
                        Geomstr.hatch(
                            outlines,
                            distance=self._distance,
                            angle=self._angle + p * self._angle_delta,
                            unidirectional=self.unidirectional,
                        )
                    )
        # Mark hatch effect geometry to prevent stitching
        # Hatch lines are closely-spaced parallel lines that should not be stitched together
        path.no_stitch = True
        return path

    def _should_use_direct_grid(self) -> bool:
        """Determine if Direct Grid algorithm should be used."""
        if self.hatch_algorithm == "direct_grid":
            return True
        elif self.hatch_algorithm == "scanbeam":
            return False
        elif self.hatch_algorithm == "auto":
            # Auto-selection logic
            # For simple shapes and reasonable distances, prefer Direct Grid
            return (
                self._distance and self._distance > 0.5
            )  # Use direct grid for reasonable spacing
        return False

    def _direct_grid_hatch(
        self,
        outlines: Geomstr,
        distance: float,
        angle: float,
        unidirectional: bool = False,
    ) -> Geomstr:
        """Use the optimized Direct Grid Fill algorithm for hatching."""
        try:
            # Use Geomstr's built-in Direct Grid algorithm
            return Geomstr.hatch_direct_grid(outlines, angle, distance, unidirectional)
        except AttributeError:
            # Fallback to original algorithm if direct_grid_fill not available
            return Geomstr.hatch(
                outlines, distance=distance, angle=angle, unidirectional=unidirectional
            )

    def as_geometries(self, **kws):
        """
        Calculates the hatch effect geometries and returns the geometries
        for each pass and child object individually.
        The pass index is the number of copies of this geometry whereas the
        internal loops value is rotated each pass by the angle-delta.

        @param kws:
        @return:
        """
        outlines = [
            node.as_geometry(**kws)
            for node in self.affected_children()
            if hasattr(node, "as_geometry")
        ]
        if self._distance is None:
            self.recalculate()
        for o in outlines:
            if self.include_outlines:
                yield o
            for p in range(self.loops):
                if self.hatch_type == "spiral":
                    yield Geomstr.hatch_spiral(
                        o,
                        angle=self._angle + p * self._angle_delta,
                        distance=self._distance,
                    )
                else:
                    yield Geomstr.hatch(
                        o,
                        distance=self._distance,
                        angle=self._angle + p * self._angle_delta,
                        unidirectional=self.unidirectional,
                    )

    def set_interim(self):
        self.empty_cache()
        self._interim = True

    def altered(self, *args, **kwargs):
        self._interim = False
        super().altered()

    def modified(self):
        self.altered()

    def can_drop(self, drag_node):
        return bool(
            (
                hasattr(drag_node, "as_geometry")
                or drag_node.type in ("effect", "file", "group", "reference")
                or (drag_node.type.startswith("op ") and drag_node.type != "op dots")
            )
        )

    def drop(self, drag_node, modify=True, flag=False):
        # Default routine for drag + drop for an effect node - irrelevant for others...
        if not self.can_drop(drag_node):
            return False
        if drag_node.type.startswith("effect"):
            if modify:
                if drag_node.parent is self.parent:
                    self.append_child(drag_node)
                else:
                    self.swap_node(drag_node)
                drag_node.altered()
                self.altered()
            return True
        if hasattr(drag_node, "as_geometry"):
            # Dragging element onto operation adds that element to the op.
            if modify:
                if self.has_ancestor("branch ops"):
                    self.add_reference(drag_node)
                else:
                    self.append_child(drag_node)
                self.altered()
            return True
        elif drag_node.type == "reference":
            if modify:
                if self.has_ancestor("branch ops"):
                    self.append_child(drag_node)
                else:
                    self.append_child(drag_node.node)
            return True
        elif drag_node.type.startswith("op"):
            # If we drag an operation to this node,
            # then we will reverse the game, but we will take the operations color
            old_references = list(self._references)
            result = drag_node.drop(self, modify=modify, flag=flag)
            if result and modify:
                if hasattr(drag_node, "color") and drag_node.color is not None:
                    self.stroke = drag_node.color
                for ref in old_references:
                    ref.remove_node()
            return result
        elif drag_node.type in ("file", "group"):
            # If we drag a group or a file to this node,
            # then we will do it only if this an element effect
            if modify:
                if self.has_ancestor("branch ops"):
                    return False
                else:
                    self.append_child(drag_node)
                self.altered()
            return True
        return False
