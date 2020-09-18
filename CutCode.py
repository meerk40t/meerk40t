from RasterPlotter import RasterPlotter, X_AXIS, TOP, BOTTOM, Y_AXIS, RIGHT, LEFT, UNIDIRECTIONAL
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


class CutCode(list):
    def __init__(self):
        list.__init__(self)

    def as_svg(self):
        svg = []
        for e in self:
            svg.append(e.as_svg())
        return svg


class LaserSettings:
    def __init__(self):
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


class CutObject:
    def __init__(self, settings=None):
        if settings is None:
            settings = LaserSettings()
        self.settings = settings

    def start(self):
        return None

    def end(self):
        return None

    def generator(self):
        raise NotImplemented


class LineCut(CutObject):
    def __init__(self, start_point, end_point):
        CutObject.__init__(self)
        self.start_point = start_point
        self.end_point = end_point

    def start(self):
        return self.start_point

    def end(self):
        return self.end_point

    def generator(self):
        return ZinglPlotter.plot_line(self.start_point[0], self.start_point[1], self.end_point[0], self.end_point[1])


class QuadCut(CutObject):
    def __init__(self, start_point, control_point, end_point):
        CutObject.__init__(self)
        self.start_point = start_point
        self.control_point = control_point
        self.end_point = end_point

    def start(self):
        return self.start_point

    def end(self):
        return self.end_point

    def generator(self):
        return ZinglPlotter.plot_quad_bezier(self.start_point[0], self.start_point[1],
                                             self.control_point[0], self.control_point[1],
                                             self.end_point[0], self.end_point[1])


class CubicCut(CutObject):
    def __init__(self, start_point, control1, control2, end_point):
        CutObject.__init__(self)
        self.start_point = start_point
        self.control1 = control1
        self.control2 = control2
        self.end_point = end_point

    def start(self):
        return self.start_point

    def end(self):
        return self.end_point

    def generator(self):
        return ZinglPlotter.plot_cubic_bezier(self.start_point[0], self.start_point[1],
                                             self.control1[0], self.control1[1],
                                             self.control2[0], self.control2[1],
                                             self.end_point[0], self.end_point[1])


class ArcCut(CutObject):
    def __init__(self, arc):
        CutObject.__init__(self)
        self.arc = arc

    def start(self):
        return self.arc.start

    def end(self):
        return self.arc.end

    def generator(self):
        return ZinglPlotter.plot_arc(self.arc)


class RasterCut(CutObject):
    def __init__(self, image):
        CutObject.__init__(self)
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
