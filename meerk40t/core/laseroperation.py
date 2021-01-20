from copy import copy

from .cutcode import (
    LaserSettings,
    CutCode,
    LineCut,
    QuadCut,
    CubicCut,
    ArcCut,
    RasterCut,
)
from ..svgelements import (
    Color,
    SVGElement,
    Shape,
    SVGImage,
    Path,
    Polygon,
    Move,
    Close,
    Line,
    QuadraticBezier,
    CubicBezier,
    Arc,
)


class LaserOperation(list):
    """
    Default object defining any operation done on the laser.

    Laser operations are a type of list and should contain SVGElement based objects.
    """

    def __init__(self, *args, **kwargs):
        list.__init__(self)
        self.operation = None
        try:
            self.operation = kwargs["operation"]
        except KeyError:
            self.operation = "Unknown"
        self.output = True
        self.show = True

        self._status_value = "Queued"
        self.color = Color("black")
        self.settings = LaserSettings(*args, **kwargs)

        try:
            self.color = Color(kwargs["color"])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.output = bool(kwargs["output"])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.show = bool(kwargs["show"])
        except (ValueError, TypeError, KeyError):
            pass
        if len(args) == 1:
            obj = args[0]
            if isinstance(obj, SVGElement):
                self.append(obj)
            elif isinstance(obj, LaserOperation):
                self.operation = obj.operation

                self.color = Color(obj.color)
                self.output = obj.output
                self.show = obj.show

                self.settings = LaserSettings(obj.settings)

                for element in obj:
                    element_copy = copy(element)
                    self.append(element_copy)
        if self.operation == "Cut":
            if self.settings.speed is None:
                self.settings.speed = 10.0
            if self.settings.power is None:
                self.settings.power = 1000.0
        if self.operation == "Engrave":
            if self.settings.speed is None:
                self.settings.speed = 35.0
            if self.settings.power is None:
                self.settings.power = 1000.0
        if self.operation == "Raster":
            if self.settings.raster_step == 0:
                self.settings.raster_step = 1
            if self.settings.speed is None:
                self.settings.speed = 150.0
            if self.settings.power is None:
                self.settings.power = 1000.0

    def __str__(self):
        op = self.operation
        if op is None:
            op = "Unknown"
        if self.operation == "Raster":
            op += str(self.settings.raster_step)
        parts = list()
        parts.append("%gmm/s" % self.settings.speed)
        if self.operation in ("Raster", "Image"):
            if self.settings.raster_swing:
                raster_dir = "-"
            else:
                raster_dir = "="
            if self.settings.raster_direction == 0:
                raster_dir += "T2B"
            elif self.settings.raster_direction == 1:
                raster_dir += "B2T"
            elif self.settings.raster_direction == 2:
                raster_dir += "R2L"
            elif self.settings.raster_direction == 3:
                raster_dir += "L2R"
            elif self.settings.raster_direction == 4:
                raster_dir += "X"
            else:
                raster_dir += "%d" % self.settings.raster_direction
            parts.append(raster_dir)
        parts.append("%gppi" % self.settings.power)
        if self.operation in ("Raster", "Image"):
            if isinstance(self.settings.overscan, str):
                parts.append("±%s" % self.settings.overscan)
            else:
                parts.append("±%d" % self.settings.overscan)
        if self.settings.dratio_custom:
            parts.append("d:%g" % self.settings.dratio)
        if self.settings.acceleration_custom:
            parts.append("a:%d" % self.settings.acceleration)
        if self.settings.passes_custom:
            parts.append("passes: %d" % self.settings.passes)
        if self.settings.dot_length_custom:
            parts.append("dot: %d" % self.settings.dot_length)
        if not self.output:
            op = "(Disabled) " + op
        return "%s %s" % (op, " ".join(parts))

    def __copy__(self):
        return LaserOperation(self)

    def time_estimate(self):
        if self.operation in ("Cut", "Engrave"):
            estimate = 0
            for e in self:
                if isinstance(e, Shape):
                    try:
                        length = e.length(error=1e-2, min_depth=2)
                    except AttributeError:
                        length = 0
                    try:
                        estimate += length / (39.3701 * self.settings.speed)
                    except ZeroDivisionError:
                        estimate = float("inf")
            hours, remainder = divmod(estimate, 3600)
            minutes, seconds = divmod(remainder, 60)
            return "%s:%s:%s" % (
                int(hours),
                str(int(minutes)).zfill(2),
                str(int(seconds)).zfill(2),
            )
        elif self.operation in ("Raster", "Image"):
            estimate = 0
            for e in self:
                if isinstance(e, SVGImage):
                    try:
                        step = e.raster_step
                    except AttributeError:
                        try:
                            step = int(e.values["raster_step"])
                        except (KeyError, ValueError):
                            step = 1
                    estimate += (e.image_width * e.image_height * step) / (
                        39.3701 * self.settings.speed
                    )
            hours, remainder = divmod(estimate, 3600)
            minutes, seconds = divmod(remainder, 60)
            return "%s:%s:%s" % (
                int(hours),
                str(int(minutes)).zfill(2),
                str(int(seconds)).zfill(2),
            )
        return "Unknown"

    def as_blob(self):
        c = CutCode()
        settings = self.settings
        if self.operation in ("Cut", "Engrave"):
            for object_path in self:
                if isinstance(object_path, SVGImage):
                    box = object_path.bbox()
                    plot = Path(
                        Polygon(
                            (box[0], box[1]),
                            (box[0], box[3]),
                            (box[2], box[3]),
                            (box[2], box[1]),
                        )
                    )
                else:
                    plot = abs(object_path)
                for seg in plot:
                    if isinstance(seg, Move):
                        pass  # Move operations are ignored.
                    elif isinstance(seg, Close):
                        c.append(LineCut(seg.start, seg.end, settings=settings))
                    elif isinstance(seg, Line):
                        c.append(LineCut(seg.start, seg.end, settings=settings))
                    elif isinstance(seg, QuadraticBezier):
                        c.append(
                            QuadCut(seg.start, seg.control, seg.end, settings=settings)
                        )
                    elif isinstance(seg, CubicBezier):
                        c.append(
                            CubicCut(
                                seg.start,
                                seg.control1,
                                seg.control2,
                                seg.end,
                                settings=settings,
                            )
                        )
                    elif isinstance(seg, Arc):
                        arc = ArcCut(seg, settings=settings)
                        c.append(arc)
        elif self.operation == "Raster":
            direction = settings.raster_direction
            settings.crosshatch = False
            if direction == 4:
                cross_settings = LaserSettings(self.operation.settings)
                cross_settings.crosshatch = True
                for object_image in self:
                    c.append(RasterCut(object_image, settings))
                    c.append(RasterCut(object_image, cross_settings))
            else:
                for object_image in self:
                    c.append(RasterCut(object_image, settings))
        elif self.operation == "Image":
            for object_image in self:
                settings = LaserSettings(self.settings)
                try:
                    settings.raster_step = int(object_image.values["raster_step"])
                except KeyError:
                    settings.raster_step = 1
                direction = settings.raster_direction
                settings.crosshatch = False
                if direction == 4:
                    cross_settings = LaserSettings(settings)
                    cross_settings.crosshatch = True
                    c.append(RasterCut(object_image, settings))
                    c.append(RasterCut(object_image, cross_settings))
                else:
                    c.append(RasterCut(object_image, settings))
        if len(c) == 0:
            return None
        return c


class CommandOperation:
    """CommandOperation is a basic command operation. It contains nothing except a single command to be executed."""

    def __init__(self, name, command, *args):
        self.name = name
        self.command = command
        self.args = args
        self.output = True
        self.operation = "Command"

    def __str__(self):
        return "%s: %s" % (self.name, str(self.args))

    def __copy__(self):
        return CommandOperation(self.name, self.command, *self.args)

    def __len__(self):
        return 1

    def generate(self):
        yield (self.command,) + self.args
