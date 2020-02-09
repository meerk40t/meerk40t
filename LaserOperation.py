from LaserCommandConstants import *
from RasterPlotter import RasterPlotter, X_AXIS, TOP, BOTTOM
from svgelements import Length, SVGImage

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

    def __init__(self, obj=None):
        list.__init__(self)
        self.speed = 20
        self.power = 1000
        self.dratio = None
        if obj is not None:
            if 'speed' in obj.values and obj.values['speed'] is not None:
                self.speed = float(obj.values['speed'])
            if 'power' in obj.values and obj.values['power'] is not None:
                self.power = float(obj.values['power'])
            if 'd_ratio' in obj.values and obj.values['d_ratio'] is not None:
                self.dratio = float(obj.values['d_ratio'])

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
        LaserOperation.__init__(self, image)
        self.speed = 150.0
        self.raster_step = 1
        self.raster_direction = 0
        self.unidirectional = False
        self.overscan = 20

        if image is not None:
            if 'speed' in image.values and image.values['speed'] is not None:
                self.speed = float(image.values['speed'])
            if 'raster_step' in image.values and image.values['raster_step'] is not None:
                self.raster_step = int(image.values['raster_step'])
            if 'raster_direction' in image.values and image.values['raster_direction'] is not None:
                self.raster_direction = int(image.values['raster_direction'])
            if 'unidirectional' in image.values and image.values['unidirectional'] is not None:
                self.unidirectional = bool(image.values['unidirectional'])
            if 'overscan' in image.values and image.values['overscan'] is not None:
                self.overscan = int(image.values['overscan'])
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

        for svgimage in self:
            if not isinstance(svgimage, SVGImage):
                continue  # We do not raster anything that is not classed properly.
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
        LaserOperation.__init__(self, path)

        speed = 35.0
        if path is not None:
            if 'speed' in path.values and path.values['speed'] is not None:
                speed = float(path.values['speed'])
            self.append(path)
        self.speed = speed

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


class CutOperation(LaserOperation):
    """
    Defines the default vector cut operation.
    """

    def __init__(self, path=None):
        LaserOperation.__init__(self, path)

        speed = 10.0
        if path is not None:
            if 'speed' in path.values and path.values['speed'] is not None:
                speed = float(path.values['speed'])
            self.append(path)
        self.speed = speed

    def __str__(self):
        parts = []
        parts.append("speed=%f" % self.speed)
        parts.append("power=%f" % self.power)
        return "Cut: (%s)" % ", ".join(parts)

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