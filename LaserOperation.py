from copy import copy

from CutCode import LaserSettings, CutCode
from svgelements import SVGImage, SVGElement, Shape, Color, Path, Polygon


class LaserOperation(list):
    """
    Default object defining any operation done on the laser.

    Laser operations are a type of list and should contain SVGElement based objects.
    """

    def __init__(self, *args, **kwargs):
        list.__init__(self)
        self.operation = None
        try:
            self.operation = kwargs['operation']
        except KeyError:
            self.operation = "Unknown"
        self.output = True
        self.show = True

        self._status_value = "Queued"
        self.color = Color('black')
        self.settings = LaserSettings(*args, **kwargs)

        try:
            self.color = Color(kwargs['color'])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.output = bool(kwargs['output'])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.show = bool(kwargs['show'])
        except (ValueError, TypeError, KeyError):
            pass
        
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
            if self.settings.speed is None:
                self.settings.speed = 150.0
            if self.settings.power is None:
                self.settings.power = 1000.0
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
                        estimate = float('inf')
            hours, remainder = divmod(estimate, 3600)
            minutes, seconds = divmod(remainder, 60)
            return "%s:%s:%s" % (int(hours), str(int(minutes)).zfill(2), str(int(seconds)).zfill(2))
        elif self.operation in ("Raster", "Image"):
            estimate = 0
            for e in self:
                if isinstance(e, SVGImage):
                    try:
                        step = e.raster_step
                    except AttributeError:
                        try:
                            step = int(e.values['raster_step'])
                        except (KeyError, ValueError):
                            step = 1
                    estimate += (e.image_width * e.image_height * step) / (39.3701 * self.settings.speed)
            hours, remainder = divmod(estimate, 3600)
            minutes, seconds = divmod(remainder, 60)
            return "%s:%s:%s" % (int(hours), str(int(minutes)).zfill(2), str(int(seconds)).zfill(2))
        return "Unknown"

    def generate(self):
        c = CutCode()
        if self.operation in ("Cut", "Engrave"):
            for object_path in self:
                if isinstance(object_path, SVGImage):
                    box = object_path.bbox()
                    plot = Path(Polygon((box[0], box[1]), (box[0], box[3]), (box[2], box[3]), (box[2], box[1])))
                else:
                    plot = abs(object_path)
                for segment in plot:
                    if isinstance(segment, Line):
                        c.append(LineCut(segment.start, segment.end))

                yield COMMAND_PLOT, plot
        elif self.operation in ("Raster", "Image"):
            yield COMMAND_MODE_RAPID
            yield COMMAND_SET_ABSOLUTE
            yield COMMAND_SET_SPEED, self.settings.speed
            direction = self.settings.raster_direction
            yield COMMAND_SET_POWER, self.settings.power
            yield COMMAND_SET_D_RATIO, None
            if self.settings.acceleration is not None and self.settings.acceleration_custom:
                yield COMMAND_SET_ACCELERATION, self.settings.acceleration
            else:
                yield COMMAND_SET_ACCELERATION, None
            crosshatch = False
            traverse = 0
            if direction == 0:
                traverse |= X_AXIS
                traverse |= TOP
            elif direction == 1:
                traverse |= X_AXIS
                traverse |= BOTTOM
            elif direction == 2:
                traverse |= Y_AXIS
                traverse |= RIGHT
            elif direction == 3:
                traverse |= Y_AXIS
                traverse |= LEFT
            elif direction == 4:
                traverse |= X_AXIS
                traverse |= TOP
                crosshatch = True
            if self.settings.raster_swing:
                traverse |= UNIDIRECTIONAL
            for svgimage in self:
                if not isinstance(svgimage, SVGImage):
                    continue  # We do not raster anything that is not classed properly.
                if self.operation == "Raster":
                    step = self.settings.raster_step
                else:
                    try:
                        step = int(svgimage.values['raster_step'])
                    except (KeyError, ValueError):
                        step = 1
                yield COMMAND_SET_STEP, step
                image = svgimage.image
                width, height = image.size
                mode = image.mode

                if mode != "1" and mode != "P" and mode != "L" and mode != "RGB" and mode != "RGBA":
                    # Any mode without a filter should get converted.
                    image = image.convert("RGBA")
                    mode = image.mode
                if mode == "1":
                    def image_filter(pixel):
                        return (255 - pixel) / 255.0
                elif mode == "P":
                    p = image.getpalette()

                    def image_filter(pixel):
                        v = p[pixel * 3] + p[pixel * 3 + 1] + p[pixel * 3 + 2]
                        return 1.0 - v / 765.0
                elif mode == "L":
                    def image_filter(pixel):
                        return (255 - pixel) / 255.0
                elif mode == "RGB":
                    def image_filter(pixel):
                        return 1.0 - (pixel[0] + pixel[1] + pixel[2]) / 765.0
                elif mode == "RGBA":
                    def image_filter(pixel):
                        return (1.0 - (pixel[0] + pixel[1] + pixel[2]) / 765.0) * pixel[3] / 255.0
                else:
                    raise ValueError  # this shouldn't happen.
                m = svgimage.transform
                data = image.load()

                overscan = self.settings.overscan
                if overscan is None:
                    overscan = 20
                else:
                    try:
                        overscan = int(overscan)
                    except ValueError:
                        overscan = 20
                tx = m.value_trans_x()
                ty = m.value_trans_y()
                raster = RasterPlotter(data, width, height, traverse, 0, overscan,
                                       tx,
                                       ty,
                                       step, image_filter)
                yield COMMAND_MODE_RAPID
                x, y = raster.initial_position_in_scene()
                yield COMMAND_MOVE, x, y
                top, left, x_dir, y_dir = raster.initial_direction()
                yield COMMAND_SET_DIRECTION, top, left, x_dir, y_dir
                yield COMMAND_MODE_PROGRAM
                yield COMMAND_RASTER, raster
                if crosshatch:
                    cross_traverse = traverse
                    cross_traverse ^= Y_AXIS
                    if traverse & Y_AXIS:
                        cross_traverse ^= RIGHT
                        if int(round(width)) & 1 and not traverse & UNIDIRECTIONAL:
                            cross_traverse ^= BOTTOM
                    else:
                        cross_traverse ^= BOTTOM
                        if int(round(height)) & 1 and not traverse & UNIDIRECTIONAL:
                            cross_traverse ^= RIGHT

                    cross_raster = RasterPlotter(data, width, height, cross_traverse, 0, overscan,
                                           tx,
                                           ty,
                                           step, image_filter)
                    yield COMMAND_MODE_RAPID
                    x, y = cross_raster.initial_position_in_scene()
                    yield COMMAND_MOVE, x, y
                    top, left, x_dir, y_dir = cross_raster.initial_direction()
                    yield COMMAND_SET_DIRECTION, top, left, x_dir, y_dir
                    yield COMMAND_MODE_PROGRAM
                    yield COMMAND_RASTER, cross_raster
            yield COMMAND_MODE_RAPID


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