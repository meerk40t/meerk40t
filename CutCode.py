from LaserCommandConstants import *
from RasterPlotter import RasterPlotter, X_AXIS, TOP, BOTTOM, Y_AXIS, RIGHT, LEFT, UNIDIRECTIONAL
from svgelements import *
from zinglplotter import ZinglPlotter

"""
Cutcode is a list of cut objects. These are line, quad, cubic, arc, and raster. And anything else that should be
considered a laser primitive. These are disjointed objects. If the distance between one and the next exist the laser 
should be toggled and move by anything executing these in the planning process. Various other laser-file types should
be converted into cut code. This should be the parsed form of file-blobs. Cutcode can convert easily to both SVG and
to LaserCode.

All CutObjects have a .start() .end() and .generator() functions. They also have a settings object that contains all 
properties for that cuts may need or use. Or which may be used by the CutPlanner, PlotPlanner, or local objects. These
are references to settings which may be shared by all CutObjects created by a LaserOperation.  
"""


class LaserSettings:
    def __init__(self, *args, **kwargs):
        self.speed = 20.0
        self.power = 1000.0
        self.dratio_custom = False
        self.dratio = 0.261
        self.acceleration_custom = False
        self.acceleration = 1

        self.raster_step = 0
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

        if args == 1:
            obj = args[0]
            if isinstance(obj, LaserSettings):
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


class CutCode(list):
    def __init__(self):
        list.__init__(self)

    def as_svg(self):
        svg = []
        for e in self:
            svg.append(e.as_svg())
        return svg

    def cross(self, j, k):
        """
        Reverses subpaths flipping the individual elements from position j inclusive to
        k exclusive.

        :param subpaths:
        :param j:
        :param k:
        :return:
        """
        for q in range(j, k):
            self[q].direct_close()
            self[q].reverse()
        self[j:k] = self[j:k][::-1]

    def generate(self, rapid=True, jog=0):
        speed = None
        power = None
        dratio = None
        accel = None
        step = None
        settings = None
        for cutobject in self:
            if cutobject.settings is not settings:
                new_step = cutobject.settings.raster_step
                new_speed = cutobject.settings.speed
                new_power = cutobject.settings.power
                if cutobject.settings.dratio_custom:
                    new_dratio = cutobject.settings.dratio
                else:
                    new_dratio = None
                if cutobject.settings.acceleration_custom:
                    new_accel = cutobject.settings.acceleration_custom
                else:
                    new_accel = None
                # direction = cutobject.settings.raster_direction
                # top, left, x_dir, y_dir = cutobject.settings.initial_direction()
                # yield COMMAND_SET_DIRECTION, top, left, x_dir, y_dir
                # TODO: Should only return to rapid if a primary setting changes.
                if speed != new_speed or step != new_step or power != new_power or dratio != new_dratio or accel != new_accel:
                    yield COMMAND_MODE_RAPID
                    yield COMMAND_SET_ABSOLUTE
                    if speed != new_speed:
                        yield COMMAND_SET_SPEED, new_speed
                    if step != new_step:
                        yield COMMAND_SET_STEP, new_step
                    if power != new_power:
                        yield COMMAND_SET_POWER, new_power
                    if dratio != new_dratio:
                        yield COMMAND_SET_D_RATIO, new_dratio
                    if accel != new_accel:
                        yield COMMAND_SET_ACCELERATION, new_accel
            settings = cutobject.settings
            speed = new_speed
            power = new_power
            dratio = new_dratio
            accel = new_accel
            step = new_step
            yield COMMAND_MODE_PROGRAM
            try:
                first = cutobject.start()
                x = first[0]
                y = first[1]
                #TODO: Restore jogging for rapid between objects.

                # if rapid:
                #     if jog == 0:
                #         yield COMMAND_JOG, x, y
                #     elif jog == 1:
                #         yield COMMAND_JOG_SWITCH, x, y
                #     else:
                #         yield COMMAND_JOG_FINISH, x, y
                # else:
                #     yield COMMAND_MODE_RAPID
                yield COMMAND_MOVE, x, y
                #     yield COMMAND_MODE_PROGRAM
            except (IndexError, AttributeError):
                pass
            yield COMMAND_PLOT, cutobject.generator()
        yield COMMAND_MODE_RAPID


class CutObject:
    def __init__(self, settings=None):
        if settings is None:
            settings = LaserSettings()
        self.settings = settings
        self._start = None
        self._end = None
        self._bounds = None

    def start(self):
        return self._start

    def end(self):
        return self._end

    def bounds(self):
        return self._bounds

    def reverse(self):
        self._start, self._end = self._end, self._start

    def generator(self):
        raise NotImplemented


class LineCut(CutObject):
    def __init__(self, start_point, end_point, settings=None):
        CutObject.__init__(self, settings=settings)
        self.start_point = start_point
        self.end_point = end_point

    def start(self):
        return self.start_point

    def end(self):
        return self.end_point

    def reverse(self):
        self.start_point, self.end_point = self.end_point, self.start_point

    def generator(self):
        return ZinglPlotter.plot_line(self.start_point[0], self.start_point[1], self.end_point[0], self.end_point[1])


class QuadCut(CutObject):
    def __init__(self, start_point, control_point, end_point, settings=None):
        CutObject.__init__(self, settings=settings)
        self.start_point = start_point
        self.control_point = control_point
        self.end_point = end_point

    def start(self):
        return self.start_point

    def end(self):
        return self.end_point

    def reverse(self):
        self.start_point, self.end_point = self.end_point, self.start_point

    def generator(self):
        return ZinglPlotter.plot_quad_bezier(self.start_point[0], self.start_point[1],
                                             self.control_point[0], self.control_point[1],
                                             self.end_point[0], self.end_point[1])


class CubicCut(CutObject):
    def __init__(self, start_point, control1, control2, end_point, settings=None):
        CutObject.__init__(self, settings=settings)
        self.start_point = start_point
        self.control1 = control1
        self.control2 = control2
        self.end_point = end_point

    def start(self):
        return self.start_point

    def end(self):
        return self.end_point

    def reverse(self):
        self.control1, self.control2 = self.control2, self.control1
        self.start_point, self.end_point = self.end_point, self.start_point

    def generator(self):
        return ZinglPlotter.plot_cubic_bezier(self.start_point[0], self.start_point[1],
                                              self.control1[0], self.control1[1],
                                              self.control2[0], self.control2[1],
                                              self.end_point[0], self.end_point[1])


class ArcCut(CutObject):
    def __init__(self, arc, settings=None):
        CutObject.__init__(self, settings=settings)
        self.arc = arc

    def start(self):
        return self.arc.start

    def end(self):
        return self.arc.end

    def reverse(self):
        self.arc = copy(self.arc).reversed()

    def generator(self):
        return ZinglPlotter.plot_arc(self.arc)


class RasterCut(CutObject):
    def __init__(self, image, settings=None):
        CutObject.__init__(self, settings=settings)
        self.image = image

    def start(self):
        return None

    def end(self):
        return None

    def generator(self):
        step = self.settings.raster_step
        direction = self.settings.raster_direction
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
        if self.settings.raster_swing:
            traverse |= UNIDIRECTIONAL

        svgimage = self.image
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
        return RasterPlotter(data, width, height, traverse, 0, overscan,
                             tx,
                             ty,
                             step, image_filter)
