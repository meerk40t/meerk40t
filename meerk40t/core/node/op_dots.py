from copy import copy

from meerk40t.core.cutcode import (
    CubicCut,
    CutGroup,
    DwellCut,
    LineCut,
    QuadCut,
    RasterCut,
    PlotCut,
)
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.core.units import Length
from meerk40t.image.actualize import actualize
from meerk40t.svgelements import (
    Close,
    Color,
    CubicBezier,
    Line,
    Move,
    Path,
    Polygon,
    QuadraticBezier,
    Shape,
    SVGElement,
    SVGImage, Matrix, Angle,
)
from meerk40t.tools.pathtools import VectorMontonizer, EulerianFill

MILS_IN_MM = 39.3701


class DotsOpNode(Node, Parameters):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "op dots".
    """

    def __init__(self, *args, **kwargs):
        if "setting" in kwargs:
            kwargs = kwargs["settings"]
            if "type" in kwargs:
                del kwargs["type"]
        Node.__init__(self, *args, type="op dots", **kwargs)
        Parameters.__init__(self, None, **kwargs)
        self.settings.update(kwargs)
        self._status_value = "Queued"

        if len(args) == 1:
            obj = args[0]
            if isinstance(obj, SVGElement):
                self.add(obj, type="ref elem")
            elif hasattr(obj, "settings"):
                self.settings = dict(obj.settings)
            elif isinstance(obj, dict):
                self.settings.update(obj)

    def __repr__(self):
        return "DotsOpNode()"

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        if self.default:
            parts.append("✓")
        if self.passes_custom and self.passes != 1:
            parts.append("%dX" % self.passes)
        if self.frequency is not None:
            parts.append("%gkHz" % float(self.frequency))
        parts.append("Dots")
        parts.append("%gms dwell" % self.dwell_time)
        return " ".join(parts)

    def __copy__(self):
        return DotsOpNode(self)

    def load(self, settings, section):
        settings.read_persistent_attributes(section, self)
        update_dict = settings.read_persistent_string_dict(section, suffix=True)
        self.settings.update(update_dict)
        self.validate()
        hexa = self.settings.get("hex_color")
        if hexa is not None:
            self.color = Color(hexa)
        self.notify_update()

    def save(self, settings, section):
        settings.write_persistent_attributes(section, self)
        settings.write_persistent(section, "hex_color", self.color.hexa)
        settings.write_persistent_dict(section, self.settings)

    def copy_children(self, obj):
        for element in obj.children:
            self.add(element.object, type="ref elem")

    def deep_copy_children(self, obj):
        for element in obj.children:
            self.add(copy(element.object), type=element.type)

    def time_estimate(self):
        estimate = 0
        for e in self.children:
            e = e.object
            if isinstance(e, Shape):
                estimate += self.dwell_time
        hours, remainder = divmod(estimate, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "%s:%s:%s" % (
            int(hours),
            str(int(minutes)).zfill(2),
            str(int(seconds)).zfill(2),
        )

    def as_cutobjects(self, closed_distance=15, passes=1):
        """Generator of cutobjects for a particular operation."""
        settings = self.derive()
        for path_node in self.children:
            try:
                obj = abs(path_node.object)
                first = obj.point(0)
            except (IndexError, AttributeError):
                continue
            if first is None:
                continue
            yield DwellCut(
                (first[0], first[1]),
                settings=settings,
                passes=passes,
            )
