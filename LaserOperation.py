from LaserCommandConstants import *
from RasterPlotter import RasterPlotter, X_AXIS, TOP, BOTTOM
from svgelements import Length

VARIABLE_NAME_NAME = 'name'
VARIABLE_NAME_SPEED = 'speed'
VARIABLE_NAME_POWER = 'power'
VARIABLE_NAME_DRATIO = 'd_ratio'
VARIABLE_NAME_RASTER_STEP = 'raster_step'
VARIABLE_NAME_RASTER_DIRECTION = 'raster_direction'


class LaserOperation(list):
    """
    Default object defining any operation done on the laser.
    Laser operations are a type of list and should contain SVGElement based objects
    """

    def __init__(self):
        list.__init__(self)
        self.speed = 20.0
        self.power = 1000.0
        self.dratio = None

    def __str__(self):
        parts = []
        parts.append("speed=%f" % self.speed)
        parts.append("power=%f" % self.power)
        if self.dratio is not None:
            parts.append("dratio=%f" % self.dratio)
        return "Unknown Operation: (%s)" % ", ".join(parts)


class RasterOperation(LaserOperation):
    """
    Defines the default raster operation to be done and the properties needed.
    """

    def __init__(self, image=None):
        LaserOperation.__init__(self)
        self.speed = 150.0
        self.raster_step = 1
        self.raster_direction = 0
        self.unidirectional = False
        self.overscan = 20
        if image is not None:
            self.append(image)

    def __str__(self):
        parts = []
        parts.append("speed=%s" % Length.str(self.speed))
        parts.append("step=%d" % self.raster_step)
        parts.append("direction=%d" % self.raster_direction)
        parts.append("overscan=%d" % self.overscan)
        return "Raster: (%s)" % ", ".join(parts)

    def generate(self):
        yield COMMAND_SET_SPEED, self.speed

        direction = self.raster_direction
        step = self.raster_step
        yield COMMAND_SET_POWER, self.power

        traverse = 0
        if direction == 0:
            yield COMMAND_SET_STEP, step
            traverse |= X_AXIS
            traverse |= TOP
        elif direction == 1:
            yield COMMAND_SET_STEP, step
            traverse |= X_AXIS
            traverse |= BOTTOM

        for image in self:
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
            m = image.transform
            data = image.load()

            overscan = self.overscan
            if overscan is None:
                overscan = 20
            else:
                try:
                    overscan = int(overscan)
                except ValueError:
                    overscan = 20
            raster = RasterPlotter(data, width, height, traverse, 0, overscan,
                                   m.value_trans_x(),
                                   m.value_trans_y(),
                                   step, image_filter)
            yield COMMAND_RAPID_MOVE, raster.initial_position_in_scene()
            yield COMMAND_SET_DIRECTION, raster.initial_direction()
            yield COMMAND_MODE_COMPACT, 0
            yield COMMAND_RASTER, raster
            yield COMMAND_MODE_DEFAULT, 0


class EngraveOperation(LaserOperation):
    """
    Defines the default vector engraving operation. This is intended to mark the
    object being engraved on.
    """

    def __init__(self, path=None):
        LaserOperation.__init__(self)
        self.speed = 35.0
        if path is not None:
            self.append(path)

    def __str__(self):
        parts = []
        parts.append("speed=%f" % self.speed)
        parts.append("power=%f" % self.power)
        return "Engrave: (%s)" % ", ".join(parts)

    def generate(self):
        yield COMMAND_SET_SPEED, self.speed
        yield COMMAND_SET_POWER, self.power
        if self.dratio is not None:
            yield COMMAND_SET_D_RATIO, self.dratio
        for object_path in self:
            plot = abs(object_path)
            first_point = plot.first_point
            if first_point is None:
                continue
            yield COMMAND_RAPID_MOVE, first_point
            yield COMMAND_SET_STEP, 0
            yield COMMAND_MODE_COMPACT, 0
            yield COMMAND_PLOT, plot
            yield COMMAND_MODE_DEFAULT, 0
        yield COMMAND_SET_SPEED, None
        yield COMMAND_SET_D_RATIO, None


class CutOperation(EngraveOperation):
    def __init__(self, path=None):
        EngraveOperation.__init__(self, path=path)
        self.speed = 10.0

    def __str__(self):
        parts = []
        parts.append("speed=%f" % self.speed)
        parts.append("power=%f" % self.power)
        return "Cut: (%s)" % ", ".join(parts)