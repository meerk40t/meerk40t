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


class CutOpNode(Node, Parameters):
    """
    Default object defining a cut operation done on the laser.

    This is a Node of type "op cut".
    """

    def __init__(self, *args, **kwargs):
        Node.__init__(self, *args, type="op cut", **kwargs)
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
        return "CutOpNode()"

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        if self.default:
            parts.append("✓")
        if self.passes_custom and self.passes != 1:
            parts.append("%dX" % self.passes)
        parts.append("Cut")
        if self.speed is not None:
            parts.append("%gmm/s" % self.speed)
        if self.power is not None:
            parts.append("%gppi" % self.power)
        if self.frequency is not None:
            parts.append("%gkHz" % self.frequency)
        parts.append("%s" % self.color.hex)
        if self.dratio_custom:
            parts.append("d:%g" % self.dratio)
        if self.acceleration_custom:
            parts.append("a:%d" % self.acceleration)
        if self.dot_length_custom:
            parts.append("dot: %d" % self.dot_length)
        return " ".join(parts)

    def __copy__(self):
        return CutOpNode(self)

    def load(self, settings, section):
        settings.read_persistent_attributes(section, self)
        update_dict = settings.read_persistent_string_dict(section, suffix=True)
        self.settings.update(update_dict)
        self.validate()
        hexa = self.settings.get("hex_color")
        if hexa is not None:
            self.color = Color(hexa)

    def save(self, settings, section):
        settings.write_persistent_attributes(section, self)
        settings.write_persistent(section, "hex_color", self.color.hexa)
        settings.write_persistent_dict(section, self.settings)

    def copy_children(self, obj):
        for element in obj.children:
            self.add(element.object, type="ref elem")

    def deep_copy_children(self, obj):
        for element in obj.children:
            self.add(copy(element.object), type="elem")

    def time_estimate(self):
        estimate = 0
        for e in self.children:
            e = e.object
            if isinstance(e, Shape):
                try:
                    length = e.length(error=1e-2, min_depth=2)
                except AttributeError:
                    length = 0
                try:
                    estimate += length / (MILS_IN_MM * self.speed)
                except ZeroDivisionError:
                    estimate = float("inf")
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
        for element in self.children:
            object_path = element.object
            if isinstance(object_path, SVGImage):
                box = object_path.bbox()
                path = Path(
                    Polygon(
                        (box[0], box[1]),
                        (box[0], box[3]),
                        (box[2], box[3]),
                        (box[2], box[1]),
                    )
                )
            else:
                # Is a shape or path.
                if not isinstance(object_path, Path):
                    path = abs(Path(object_path))
                else:
                    path = abs(object_path)
                path.approximate_arcs_with_cubics()
            settings["line_color"] = path.stroke
            for subpath in path.as_subpaths():
                sp = Path(subpath)
                if len(sp) == 0:
                    continue
                closed = (
                    isinstance(sp[-1], Close)
                    or abs(sp.z_point - sp.current_point) <= closed_distance
                )
                group = CutGroup(
                    None,
                    closed=closed,
                    settings=settings,
                    passes=passes,
                )
                group.path = Path(subpath)
                group.original_op = self.type
                for seg in subpath:
                    if isinstance(seg, Move):
                        pass  # Move operations are ignored.
                    elif isinstance(seg, Close):
                        if seg.start != seg.end:
                            group.append(
                                LineCut(
                                    seg.start,
                                    seg.end,
                                    settings=settings,
                                    passes=passes,
                                    parent=group,
                                )
                            )
                    elif isinstance(seg, Line):
                        if seg.start != seg.end:
                            group.append(
                                LineCut(
                                    seg.start,
                                    seg.end,
                                    settings=settings,
                                    passes=passes,
                                    parent=group,
                                )
                            )
                    elif isinstance(seg, QuadraticBezier):
                        group.append(
                            QuadCut(
                                seg.start,
                                seg.control,
                                seg.end,
                                settings=settings,
                                passes=passes,
                                parent=group,
                            )
                        )
                    elif isinstance(seg, CubicBezier):
                        group.append(
                            CubicCut(
                                seg.start,
                                seg.control1,
                                seg.control2,
                                seg.end,
                                settings=settings,
                                passes=passes,
                                parent=group,
                            )
                        )
                if len(group) > 0:
                    group[0].first = True
                for i, cut_obj in enumerate(group):
                    cut_obj.closed = closed
                    try:
                        cut_obj.next = group[i + 1]
                    except IndexError:
                        cut_obj.last = True
                        cut_obj.next = group[0]
                    cut_obj.previous = group[i - 1]
                yield group


class EngraveOpNode(Node, Parameters):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "op engrave".
    """

    def __init__(self, *args, **kwargs):
        if "setting" in kwargs:
            kwargs = kwargs["settings"]
            if "type" in kwargs:
                del kwargs["type"]
        Node.__init__(self, *args, type="op engrave", **kwargs)
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
        return "EngraveOpNode()"

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        if self.default:
            parts.append("✓")
        if self.passes_custom and self.passes != 1:
            parts.append("%dX" % self.passes)
        parts.append("Engrave")
        if self.speed is not None:
            parts.append("%gmm/s" % self.speed)
        if self.power is not None:
            parts.append("%gppi" % self.power)
        if self.frequency is not None:
            parts.append("%gkHz" % self.frequency)
        parts.append("%s" % self.color.hex)
        if self.dratio_custom:
            parts.append("d:%g" % self.dratio)
        if self.acceleration_custom:
            parts.append("a:%d" % self.acceleration)
        if self.dot_length_custom:
            parts.append("dot: %d" % self.dot_length)
        return " ".join(parts)

    def __copy__(self):
        return EngraveOpNode(self)

    def load(self, settings, section):
        settings.read_persistent_attributes(section, self)
        update_dict = settings.read_persistent_string_dict(section, suffix=True)
        self.settings.update(update_dict)
        self.validate()
        hexa = self.settings.get("hex_color")
        if hexa is not None:
            self.color = Color(hexa)

    def save(self, settings, section):
        settings.write_persistent_attributes(section, self)
        settings.write_persistent(section, "hex_color", self.color.hexa)
        settings.write_persistent_dict(section, self.settings)

    def copy_children(self, obj):
        for element in obj.children:
            self.add(element.object, type="ref elem")

    def deep_copy_children(self, obj):
        for element in obj.children:
            self.add(copy(element.object), type="elem")

    def time_estimate(self):
        estimate = 0
        for e in self.children:
            e = e.object
            if isinstance(e, Shape):
                try:
                    length = e.length(error=1e-2, min_depth=2)
                except AttributeError:
                    length = 0
                try:
                    estimate += length / (MILS_IN_MM * self.speed)
                except ZeroDivisionError:
                    estimate = float("inf")
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
        for element in self.children:
            object_path = element.object
            if isinstance(object_path, SVGImage):
                box = object_path.bbox()
                path = Path(
                    Polygon(
                        (box[0], box[1]),
                        (box[0], box[3]),
                        (box[2], box[3]),
                        (box[2], box[1]),
                    )
                )
            else:
                # Is a shape or path.
                if not isinstance(object_path, Path):
                    path = abs(Path(object_path))
                else:
                    path = abs(object_path)
                path.approximate_arcs_with_cubics()
            settings["line_color"] = path.stroke
            for subpath in path.as_subpaths():
                sp = Path(subpath)
                if len(sp) == 0:
                    continue
                closed = (
                    isinstance(sp[-1], Close)
                    or abs(sp.z_point - sp.current_point) <= closed_distance
                )
                group = CutGroup(
                    None,
                    closed=closed,
                    settings=settings,
                    passes=passes,
                )
                group.path = Path(subpath)
                group.original_op = self.type
                for seg in subpath:
                    if isinstance(seg, Move):
                        pass  # Move operations are ignored.
                    elif isinstance(seg, Close):
                        if seg.start != seg.end:
                            group.append(
                                LineCut(
                                    seg.start,
                                    seg.end,
                                    settings=settings,
                                    passes=passes,
                                    parent=group,
                                )
                            )
                    elif isinstance(seg, Line):
                        if seg.start != seg.end:
                            group.append(
                                LineCut(
                                    seg.start,
                                    seg.end,
                                    settings=settings,
                                    passes=passes,
                                    parent=group,
                                )
                            )
                    elif isinstance(seg, QuadraticBezier):
                        group.append(
                            QuadCut(
                                seg.start,
                                seg.control,
                                seg.end,
                                settings=settings,
                                passes=passes,
                                parent=group,
                            )
                        )
                    elif isinstance(seg, CubicBezier):
                        group.append(
                            CubicCut(
                                seg.start,
                                seg.control1,
                                seg.control2,
                                seg.end,
                                settings=settings,
                                passes=passes,
                                parent=group,
                            )
                        )
                if len(group) > 0:
                    group[0].first = True
                for i, cut_obj in enumerate(group):
                    cut_obj.closed = closed
                    try:
                        cut_obj.next = group[i + 1]
                    except IndexError:
                        cut_obj.last = True
                        cut_obj.next = group[0]
                    cut_obj.previous = group[i - 1]
                yield group


class RasterOpNode(Node, Parameters):
    """
    Default object defining any raster operation done on the laser.

    This is a Node of type "op raster".
    """

    def __init__(self, *args, **kwargs):
        if "setting" in kwargs:
            kwargs = kwargs["settings"]
            if "type" in kwargs:
                del kwargs["type"]
        Node.__init__(self, *args, type="op raster", **kwargs)
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
        return "RasterOp()"

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        if self.default:
            parts.append("✓")
        if self.passes_custom and self.passes != 1:
            parts.append("%dX" % self.passes)
        parts.append("Raster{step}".format(step=self.raster_step))
        if self.speed is not None:
            parts.append("%gmm/s" % self.speed)
        if self.frequency is not None:
            parts.append("%gkHz" % self.frequency)
        if self.raster_swing:
            raster_dir = "-"
        else:
            raster_dir = "="
        if self.raster_direction == 0:
            raster_dir += "T2B"
        elif self.raster_direction == 1:
            raster_dir += "B2T"
        elif self.raster_direction == 2:
            raster_dir += "R2L"
        elif self.raster_direction == 3:
            raster_dir += "L2R"
        elif self.raster_direction == 4:
            raster_dir += "X"
        else:
            raster_dir += "%d" % self.raster_direction
        parts.append(raster_dir)
        if self.power is not None:
            parts.append("%gppi" % self.power)
        parts.append("±{overscan}".format(overscan=self.overscan))
        if self.acceleration_custom:
            parts.append("a:%d" % self.acceleration)
        return " ".join(parts)

    def __copy__(self):
        return RasterOpNode(self)

    def load(self, settings, section):
        settings.read_persistent_attributes(section, self)
        update_dict = settings.read_persistent_string_dict(section, suffix=True)
        self.settings.update(update_dict)
        self.validate()
        hexa = self.settings.get("hex_color")
        if hexa is not None:
            self.color = Color(hexa)

    def save(self, settings, section):
        settings.write_persistent_attributes(section, self)
        settings.write_persistent(section, "hex_color", self.color.hexa)
        settings.write_persistent_dict(section, self.settings)

    def copy_children(self, obj):
        for element in obj.children:
            self.add(element.object, type="ref elem")

    def deep_copy_children(self, obj):
        for element in obj.children:
            self.add(copy(element.object), type="elem")

    def time_estimate(self):
        # TODO: Strictly speaking this is wrong. The time estimate is raster of non-svgimage objects.
        estimate = 0
        for e in self.children:
            e = e.object
            if isinstance(e, SVGImage):
                try:
                    step = e.raster_step
                except AttributeError:
                    try:
                        step = int(e.values["raster_step"])
                    except (KeyError, ValueError):
                        step = 1
                estimate += (e.image_width * e.image_height * step) / (
                    MILS_IN_MM * self.speed
                )
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
        step = self.raster_step
        assert step > 0
        direction = self.raster_direction
        for element in self.children:
            svg_image = element.object
            if not isinstance(svg_image, SVGImage):
                continue

            matrix = svg_image.transform
            pil_image = svg_image.image
            pil_image, matrix = actualize(pil_image, matrix, step)
            box = (
                matrix.value_trans_x(),
                matrix.value_trans_y(),
                matrix.value_trans_x() + pil_image.width * step,
                matrix.value_trans_y() + pil_image.height * step,
            )
            path = Path(
                Polygon(
                    (box[0], box[1]),
                    (box[0], box[3]),
                    (box[2], box[3]),
                    (box[2], box[1]),
                )
            )
            cut = RasterCut(
                pil_image,
                matrix.value_trans_x(),
                matrix.value_trans_y(),
                settings=settings,
                passes=passes,
            )
            cut.path = path
            cut.original_op = self.type
            yield cut
            if direction == 4:
                cut = RasterCut(
                    pil_image,
                    matrix.value_trans_x(),
                    matrix.value_trans_y(),
                    crosshatch=True,
                    settings=settings,
                    passes=passes,
                )
                cut.path = path
                cut.original_op = self.type
                yield cut


class ImageOpNode(Node, Parameters):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "op image".
    """

    def __init__(self, *args, **kwargs):
        if "setting" in kwargs:
            kwargs = kwargs["settings"]
            if "type" in kwargs:
                del kwargs["type"]
        Node.__init__(self, *args, type="op image", **kwargs)
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
        return "ImageOpNode()"

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        if self.default:
            parts.append("✓")
        if self.passes_custom and self.passes != 1:
            parts.append("%dX" % self.passes)
        parts.append("Image")
        if self.speed is not None:
            parts.append("%gmm/s" % self.speed)
        if self.frequency is not None:
            parts.append("%gkHz" % self.frequency)
        if self.raster_swing:
            raster_dir = "-"
        else:
            raster_dir = "="
        if self.raster_direction == 0:
            raster_dir += "T2B"
        elif self.raster_direction == 1:
            raster_dir += "B2T"
        elif self.raster_direction == 2:
            raster_dir += "R2L"
        elif self.raster_direction == 3:
            raster_dir += "L2R"
        elif self.raster_direction == 4:
            raster_dir += "X"
        else:
            raster_dir += "%d" % self.raster_direction
        parts.append(raster_dir)
        if self.power is not None:
            parts.append("%gppi" % self.power)
        parts.append("±{overscan}".format(overscan=self.overscan))
        parts.append("%s" % self.color.hex)
        if self.acceleration_custom:
            parts.append("a:%d" % self.acceleration)
        return " ".join(parts)

    def __copy__(self):
        return ImageOpNode(self)

    def load(self, settings, section):
        settings.read_persistent_attributes(section, self)
        update_dict = settings.read_persistent_string_dict(section, suffix=True)
        self.settings.update(update_dict)
        self.validate()
        hexa = self.settings.get("hex_color")
        if hexa is not None:
            self.color = Color(hexa)

    def save(self, settings, section):
        settings.write_persistent_attributes(section, self)
        settings.write_persistent(section, "hex_color", self.color.hexa)
        settings.write_persistent_dict(section, self.settings)

    def copy_children(self, obj):
        for element in obj.children:
            self.add(element.object, type="ref elem")

    def deep_copy_children(self, obj):
        for element in obj.children:
            self.add(copy(element.object), type="elem")

    def time_estimate(self):
        estimate = 0
        for e in self.children:
            e = e.object
            if isinstance(e, SVGImage):
                try:
                    step = e.raster_step
                except AttributeError:
                    try:
                        step = int(e.values["raster_step"])
                    except (KeyError, ValueError):
                        step = 1
                estimate += (e.image_width * e.image_height * step) / (
                    MILS_IN_MM * self.speed
                )
        hours, remainder = divmod(estimate, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "%s:%s:%s" % (
            int(hours),
            str(int(minutes)).zfill(2),
            str(int(seconds)).zfill(2),
        )

    def as_cutobjects(self, closed_distance=15, passes=1):
        """Generator of cutobjects for a particular operation."""
        for svg_image in self.children:
            svg_image = svg_image.object
            if not isinstance(svg_image, SVGImage):
                continue
            settings = self.derive()
            try:
                settings["raster_step"] = int(svg_image.values["raster_step"])
            except KeyError:
                # This overwrites any step that may have been defined in settings.
                settings[
                    "raster_step"
                ] = 1  # If raster_step is not set image defaults to 1.
            if settings["raster_step"] <= 0:
                settings["raster_step"] = 1

            try:
                settings["raster_direction"] = int(svg_image.values["raster_direction"])
            except KeyError:
                pass
            step = settings["raster_step"]
            matrix = svg_image.transform
            pil_image = svg_image.image
            pil_image, matrix = actualize(pil_image, matrix, step)
            box = (
                matrix.value_trans_x(),
                matrix.value_trans_y(),
                matrix.value_trans_x() + pil_image.width * step,
                matrix.value_trans_y() + pil_image.height * step,
            )
            path = Path(
                Polygon(
                    (box[0], box[1]),
                    (box[0], box[3]),
                    (box[2], box[3]),
                    (box[2], box[1]),
                )
            )
            cut = RasterCut(
                pil_image,
                matrix.value_trans_x(),
                matrix.value_trans_y(),
                settings=settings,
                passes=passes,
            )
            cut.path = path
            cut.original_op = self.type
            yield cut
            if settings["raster_direction"] == 4:
                cut = RasterCut(
                    pil_image,
                    matrix.value_trans_x(),
                    matrix.value_trans_y(),
                    crosshatch=True,
                    settings=settings,
                    passes=passes,
                )
                cut.path = path
                cut.original_op = self.type
                yield cut


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
            parts.append("%gkHz" % self.frequency)
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

    def save(self, settings, section):
        settings.write_persistent_attributes(section, self)
        settings.write_persistent(section, "hex_color", self.color.hexa)
        settings.write_persistent_dict(section, self.settings)

    def copy_children(self, obj):
        for element in obj.children:
            self.add(element.object, type="ref elem")

    def deep_copy_children(self, obj):
        for element in obj.children:
            self.add(copy(element.object), type="elem")

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


class HatchOpNode(Node, Parameters):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "hatch op".
    """

    def __init__(self, *args, **kwargs):
        if "setting" in kwargs:
            kwargs = kwargs["settings"]
            if "type" in kwargs:
                del kwargs["type"]
        Node.__init__(self, *args, type="op hatch", **kwargs)
        Parameters.__init__(self, None, **kwargs)
        self.settings.update(kwargs)
        self._status_value = "Queued"
        self._hatch_distance_native = None

        if len(args) == 1:
            obj = args[0]
            if isinstance(obj, SVGElement):
                self.add(obj, type="ref elem")
            elif hasattr(obj, "settings"):
                self.settings = dict(obj.settings)
            elif isinstance(obj, dict):
                self.settings.update(obj)

    def __repr__(self):
        return "HatchOpNode()"

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        if self.default:
            parts.append("✓")
        if self.passes_custom and self.passes != 1:
            parts.append("%dX" % self.passes)
        parts.append("Hatch")
        if self.speed is not None:
            parts.append("%gmm/s" % self.speed)
        if self.frequency is not None:
            parts.append("%gkHz" % self.frequency)
        if self.power is not None:
            parts.append("%gppi" % self.power)
        parts.append("%s" % self.color.hex)
        return " ".join(parts)

    def __copy__(self):
        return HatchOpNode(self)

    def load(self, settings, section):
        settings.read_persistent_attributes(section, self)
        update_dict = settings.read_persistent_string_dict(section, suffix=True)
        self.settings.update(update_dict)
        self.validate()
        hexa = self.settings.get("hex_color")
        if hexa is not None:
            self.color = Color(hexa)

    def save(self, settings, section):
        settings.write_persistent_attributes(section, self)
        settings.write_persistent(section, "hex_color", self.color.hexa)
        settings.write_persistent_dict(section, self.settings)

    def copy_children(self, obj):
        for element in obj.children:
            self.add(element.object, type="ref elem")

    def deep_copy_children(self, obj):
        for element in obj.children:
            self.add(copy(element.object), type="elem")

    def time_estimate(self):
        estimate = 0
        # TODO: Implement time_estimate.
        hours, remainder = divmod(estimate, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "%s:%s:%s" % (
            int(hours),
            str(int(minutes)).zfill(2),
            str(int(seconds)).zfill(2),
        )

    def scale_native(self, matrix):
        distance_y = float(Length(self.settings.get("hatch_distance", "1mm")))
        transformed_vector = matrix.transform_vector([0, distance_y])
        self._hatch_distance_native = abs(complex(transformed_vector[0], transformed_vector[1]))

    def as_cutobjects(self, closed_distance=15, passes=1):
        """Generator of cutobjects for a particular operation."""
        settings = self.derive()
        # TODO: This currently applies Eulerian fill when it could just apply scanline fill.
        distance = self._hatch_distance_native
        angle = Angle.parse(settings.get("hatch_angle", "0deg"))
        angle = 0
        efill = EulerianFill(distance)
        for element in self.children:
            object_path = element.object
            if isinstance(object_path, Shape):
                object_path = abs(Path(object_path))
            if not isinstance(object_path, Path):
                continue
            object_path.approximate_arcs_with_cubics()
            settings["line_color"] = object_path.stroke
            for subpath in object_path.as_subpaths():
                sp = Path(subpath)
                if len(sp) == 0:
                    continue
                if angle is not None:
                    sp *= Matrix.rotate(angle)

                pts = [sp.point(i / 100.0, error=1e-4) for i in range(101)]
                efill += pts
        points = efill.get_fill()
        counter_rotate = Matrix.rotate(-angle)

        def split(points):
            pos = 0
            for i, pts in enumerate(points):
                if pts is None:
                    yield points[pos: i - 1]
                    pos = i + 1
            if pos != len(points):
                yield points[pos: len(points)]

        plot = PlotCut(settings=settings, passes=passes)
        for s in split(points):
            for p in s:
                x, y = counter_rotate.point_in_matrix_space((p.x, p.y))
                if p.value == "RUNG":
                    plot.plot_append(int(round(x)), int(round(y)), 1)
                if p.value == "EDGE":
                    plot.plot_append(int(round(x)), int(round(y)), 0)
        if len(plot):
            yield plot
