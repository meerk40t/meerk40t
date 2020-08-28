from copy import copy

from LaserCommandConstants import *
from RasterPlotter import RasterPlotter, X_AXIS, TOP, BOTTOM, Y_AXIS, RIGHT, LEFT, UNIDIRECTIONAL
from svgelements import SVGImage, SVGElement, Shape, Color, Path, Polygon


class LaserOperation(list):
    """
    Default object defining any operation done on the laser.
    Laser operations are a type of list and should contain SVGElement based objects
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
        self.speed = 20.0
        self.power = 1000.0
        self.dratio_custom = False
        self.dratio = 0.261
        self.acceleration_custom = False
        self.acceleration = 1

        self.raster_step = 1
        self.raster_direction = 0
        self.raster_swing = False  # False = bidirectional, True = Unidirectional
        self.raster_preference_top = 0
        self.raster_preference_right = 0
        self.raster_preference_left = 0
        self.raster_preference_bottom = 0
        self.overscan = 20

        self.advanced = False

        self.dot_length_custom = False
        self.dot_length = 1

        self.group_pulses = False

        self.passes_custom = False
        self.passes = 1
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
        try:
            self.speed = float(kwargs['speed'])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.power = float(kwargs['power'])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.dratio = float(kwargs['dratio'])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.dratio_custom = bool(kwargs['dratio_custom'])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.acceleration = int(kwargs['acceleration'])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.acceleration_custom = bool(kwargs['acceleration_custom'])
        except (ValueError, TypeError, KeyError):
            pass

        try:
            self.raster_step = int(kwargs['raster_step'])
        except (ValueError, TypeError, KeyError):
            pass

        try:
            self.raster_direction = int(kwargs['raster_direction'])
        except (ValueError, TypeError, KeyError):
            pass

        try:
            self.raster_swing = bool(kwargs['raster_swing'])
        except (ValueError, TypeError, KeyError):
            pass

        try:
            self.raster_preference_top = int(kwargs['raster_preference_top'])
        except (ValueError, TypeError, KeyError):
            pass

        try:
            self.raster_preference_right = int(kwargs['raster_preference_right'])
        except (ValueError, TypeError, KeyError):
            pass

        try:
            self.raster_preference_left = int(kwargs['raster_preference_left'])
        except (ValueError, TypeError, KeyError):
            pass

        try:
            self.raster_preference_bottom = int(kwargs['raster_preference_bottom'])
        except (ValueError, TypeError, KeyError):
            pass

        try:
            self.overscan = int(kwargs['overscan'])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.dot_length = int(kwargs['dot_length'])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.dot_length_custom = bool(kwargs['dot_length_custom'])
        except (ValueError, TypeError, KeyError):
            pass

        try:
            self.group_pulses = bool(kwargs['group_pulses'])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.passes = int(kwargs['passes'])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.passes_custom = bool(kwargs['passes_custom'])
        except (ValueError, TypeError, KeyError):
            pass

        if self.operation == "Cut":
            if self.speed is None:
                self.speed = 10.0
            if self.power is None:
                self.power = 1000.0
        if self.operation == "Engrave":
            if self.speed is None:
                self.speed = 35.0
            if self.power is None:
                self.power = 1000.0
        if self.operation == "Raster":
            if self.speed is None:
                self.speed = 150.0
            if self.power is None:
                self.power = 1000.0
        if len(args) == 1:
            obj = args[0]
            if isinstance(obj, SVGElement):
                self.append(obj)
            elif isinstance(obj, LaserOperation):
                self.operation = obj.operation

                self.color = Color(obj.color)
                self.output = obj.output
                self.show = obj.show

                self.speed = obj.speed
                self.power = obj.power
                self.dratio_custom = obj.dratio_custom
                self.dratio = obj.dratio
                self.acceleration_custom = obj.acceleration_custom
                self.acceleration = obj.acceleration
                self.raster_step = obj.raster_step
                self.raster_direction = obj.raster_direction
                self.raster_swing = obj.raster_swing
                self.overscan = obj.overscan

                self.raster_preference_top = obj.raster_preference_top
                self.raster_preference_right = obj.raster_preference_right
                self.raster_preference_left = obj.raster_preference_left
                self.raster_preference_bottom = obj.raster_preference_bottom

                self.advanced = obj.advanced
                self.dot_length_custom = obj.dot_length_custom
                self.dot_length = obj.dot_length

                self.group_pulses = obj.group_pulses

                self.passes_custom = obj.passes_custom
                self.passes = obj.passes

                for element in obj:
                    element_copy = copy(element)
                    self.append(element_copy)

    def __str__(self):
        op = self.operation
        if op is None:
            op = "Unknown"
        if self.operation == "Raster":
            op += str(self.raster_step)
        parts = list()
        parts.append("%gmm/s" % self.speed)
        if self.operation in ("Raster", "Image"):
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
        parts.append("%gppi" % self.power)
        if self.operation in ("Raster", "Image"):
            if isinstance(self.overscan, str):
                parts.append("±%s" % self.overscan)
            else:
                parts.append("±%d" % self.overscan)
        if self.dratio_custom:
            parts.append("d:%g" % self.dratio)
        if self.acceleration_custom:
            parts.append("a:%d" % self.acceleration)
        if self.passes_custom:
            parts.append("passes: %d" % self.passes)
        if self.dot_length_custom:
            parts.append("dot: %d" % self.dot_length)
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
                        estimate += length / (39.3701 * self.speed)
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
                    estimate += (e.image_width * e.image_height * step) / (39.3701 * self.speed)
            hours, remainder = divmod(estimate, 3600)
            minutes, seconds = divmod(remainder, 60)
            return "%s:%s:%s" % (int(hours), str(int(minutes)).zfill(2), str(int(seconds)).zfill(2))
        return "Unknown"

    def generate(self):
        if self.operation in ("Cut", "Engrave"):
            yield COMMAND_MODE_RAPID
            yield COMMAND_SET_ABSOLUTE
            yield COMMAND_SET_SPEED, self.speed
            yield COMMAND_SET_STEP, 0
            yield COMMAND_SET_POWER, self.power
            if self.dratio is not None and self.dratio_custom:
                yield COMMAND_SET_D_RATIO, self.dratio
            else:
                yield COMMAND_SET_D_RATIO, None
            if self.acceleration is not None and self.acceleration_custom:
                yield COMMAND_SET_ACCELERATION, self.acceleration
            else:
                yield COMMAND_SET_ACCELERATION, None
            try:
                first = abs(self[0]).first_point
                yield COMMAND_MOVE, first[0], first[1]
            except (IndexError, AttributeError):
                pass
            yield COMMAND_MODE_PROGRAM
            for object_path in self:
                if isinstance(object_path, SVGImage):
                    box = object_path.bbox()
                    plot = Path(Polygon((box[0], box[1]), (box[0], box[3]), (box[2], box[3]), (box[2], box[1])))
                    yield COMMAND_PLOT, plot
                else:
                    plot = abs(object_path)
                    yield COMMAND_PLOT, plot
            yield COMMAND_MODE_RAPID
        elif self.operation in ("Raster", "Image"):
            yield COMMAND_MODE_RAPID
            yield COMMAND_SET_ABSOLUTE
            yield COMMAND_SET_SPEED, self.speed
            direction = self.raster_direction
            yield COMMAND_SET_POWER, self.power
            yield COMMAND_SET_D_RATIO, None
            if self.acceleration is not None and self.acceleration_custom:
                yield COMMAND_SET_ACCELERATION, self.acceleration
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
            if self.raster_swing:
                traverse |= UNIDIRECTIONAL
            for svgimage in self:
                if not isinstance(svgimage, SVGImage):
                    continue  # We do not raster anything that is not classed properly.
                if self.operation == "Raster":
                    step = self.raster_step
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

                overscan = self.overscan
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
