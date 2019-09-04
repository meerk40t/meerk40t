import threading

import wx

import EgvParser
import RasterPlotter
import ZinglPlotter
import path
import svg_parser
from K40Controller import K40Controller, MockController
from LaserCommandConstants import *
from LhymicroWriter import LhymicroWriter
from ZMatrix import ZMatrix
from path import Move, Line, QuadraticBezier, CubicBezier, Arc


class LaserElement:
    def __init__(self):
        self.matrix = ZMatrix()
        self.cut = {"color": 0, "speed": 60, "passes": 1}
        self.cache = None

    def draw(self, dc):
        current_scene_matrix = dc.GetTransformMatrix()
        use_matrix = ZMatrix()
        use_matrix.Concat(current_scene_matrix)
        use_matrix.Concat(self.matrix)
        dc.SetTransformMatrix(use_matrix)
        gc = wx.GraphicsContext.Create(dc)
        gc.SetPen(wx.RED_PEN)
        if self.cache is None:
            p = gc.CreatePath()
            parse = PathCommandPlotter(p)
            for event in self.generate():
                # print(event)
                parse.command(event)
            self.cache = p
            self.box = self.cache.GetBox()
        gc.StrokePath(self.cache)
        dc.SetTransformMatrix(current_scene_matrix)

    def generate(self):
        yield COMMAND_MODE_DEFAULT

    def move(self, dx, dy):
        self.matrix.PostTranslate(dx, dy)


class ImageElement(LaserElement):
    def __init__(self, image):
        LaserElement.__init__(self)
        self.box = wx.Rect2D(0, 0, image.width, image.height)
        self.image = image
        self.cut.update({"step": 1})

    def draw(self, dc):
        current_scene_matrix = dc.GetTransformMatrix()
        use_matrix = ZMatrix()
        use_matrix.Concat(current_scene_matrix)
        use_matrix.Concat(self.matrix)
        dc.SetTransformMatrix(use_matrix)
        if self.cache is None:
            width = int(self.box.GetRight())
            height = int(self.box.GetBottom())
            try:
                self.cache = wx.Bitmap.FromBufferRGBA(width, height, self.image.tobytes())
            except ValueError:
                try:
                    self.cache = wx.Bitmap.FromBuffer(width, height, self.image.tobytes())
                except ValueError:
                    return
            # TODO: 1 bit graphics crash
        dc.DrawBitmap(self.cache, 0, 0)
        dc.SetTransformMatrix(current_scene_matrix)

    def generate(self):
        yield COMMAND_SET_SPEED, (self.cut.get("speed"))
        yield COMMAND_SET_STEP, (self.cut.get("step"))
        for event in RasterPlotter.plot_raster(self.image):
            x, y, n = event
            point = self.matrix.TransformPoint(x, y)
            yield point[0], point[1], event[2]
        yield COMMAND_SET_STEP, (0)

    def move(self, dx, dy):
        self.matrix.PostTranslate(dx, dy)


class PathElement(LaserElement):
    def __init__(self, path):
        LaserElement.__init__(self)
        self.path = path
        self.box = wx.Rect2D(0, 0, 200, 200)
        self.cut.update({"color": 0xFF0000, "speed": 20})

    def generate(self):
        parse = path.ObjectParser()
        svg_parser.parse_svg_path(parse, self.path)
        object_path = parse.path
        yield COMMAND_SET_SPEED, (self.cut.get("speed"))
        yield COMMAND_MODE_COMPACT, 0
        for data in object_path:
            if isinstance(data, Move):
                yield COMMAND_MOVE_TO, (int(data.end.real), int(data.end.imag))
            elif isinstance(data, Line):
                yield COMMAND_CUT_LINE_TO, (int(data.end.real), int(data.end.imag))
            elif isinstance(data, QuadraticBezier):
                yield COMMAND_CUT_QUAD_TO, (int(data.control.real), int(data.control.imag),
                                            int(data.end.real), int(data.end.imag))
            elif isinstance(data, CubicBezier):
                yield COMMAND_CUT_CUBIC_TO, (int(data.control1.real), int(data.control1.imag),
                                             int(data.control2.real), int(data.control2.imag),
                                             int(data.end.real), int(data.end.imag))
            elif isinstance(data, Arc):
                yield COMMAND_CUT_ARC_TO, (int(data.center.real), int(data.center.imag),
                                           int(data.end.real), int(data.end.imag))
        yield COMMAND_MODE_DEFAULT, 0

    def move(self, dx, dy):
        self.matrix.PostTranslate(dx, dy)


class EgvElement(LaserElement):
    def __init__(self, file):
        LaserElement.__init__(self)
        self.file = file
        self.box = wx.Rect2D(0, 0, 0, 0)
        self.cut.update({"color": 0xFF0000, "speed": 20})

    def generate(self):
        for event in EgvParser.parse_egv(self.file):
            yield event

    def draw(self, dc):
        current_scene_matrix = dc.GetTransformMatrix()
        use_matrix = ZMatrix()
        use_matrix.Concat(current_scene_matrix)
        use_matrix.Concat(self.matrix)
        dc.SetTransformMatrix(use_matrix)
        gc = wx.GraphicsContext.Create(dc)
        gc.SetPen(wx.RED_PEN)
        if self.cache is None:
            p = gc.CreatePath()
            parse = PathCommandPlotter(p)
            for event in self.generate():
                parse.command(event)
            print(parse.x, parse.y)
            self.cache = p
            self.box = self.cache.GetBox()
        gc.StrokePath(self.cache)
        dc.SetTransformMatrix(current_scene_matrix)

    def move(self, dx, dy):
        self.matrix.PostTranslate(dx, dy)


class PathCommandPlotter:
    def __init__(self, graphic_path):
        self.graphic_path = graphic_path
        self.on = False
        self.x = 0
        self.y = 0

    def command(self, event):
        command, values = event
        if command == COMMAND_SIMPLE_MOVE:
            dx, dy = values
            if self.on:
                self.line_to(self.x + dx, self.y + dy)
            else:
                self.move_to(self.x + dx, self.y + dy)
            self.x += dx
            self.y += dy
        if command == COMMAND_LASER_OFF:
            self.on = False
        if command == COMMAND_LASER_ON:
            self.on = True
        elif command == COMMAND_SIMPLE_CUT:
            self.on = True
            dx, dy = values
            self.line_to(self.x + dx, self.y + dy)
        elif command == COMMAND_SIMPLE_SHIFT:
            self.on = False
            dx, dy = values
            self.move_to(self.x + dx, self.y + dy)
        elif command == COMMAND_RAPID_MOVE:
            x, y = values
            self.move_to(x, y)
        elif command == COMMAND_SET_SPEED:
            pass
        elif command == COMMAND_SET_STEP:
            pass
        elif command == COMMAND_MODE_COMPACT:
            pass
        elif command == COMMAND_MODE_DEFAULT:
            pass
        elif command == COMMAND_MODE_CONCAT:
            pass
        elif command == COMMAND_HSTEP:
            dx = values
            self.move_to(self.x + dx, self.y + 0)
            self.x += dx
        elif command == COMMAND_VSTEP:
            dy = values
            self.move_to(self.x + 0, self.y + dy)
            self.y += dy
        elif command == COMMAND_HOME:
            self.move_to(0, 0)
        elif command == COMMAND_LOCK:
            pass
        elif command == COMMAND_UNLOCK:
            pass
        elif command == COMMAND_MOVE_TO:
            x, y = values
            self.move_to(x, y)
        elif command == COMMAND_CUT_LINE_TO:
            x, y = values
            self.line_to(x, y)
        elif command == COMMAND_CUT_QUAD_TO:
            cx, cy, x, y = values
            self.quad_to(cx, cy, x, y)
        elif command == COMMAND_CUT_CUBIC_TO:
            c1x, c1y, c2x, c2y, x, y = values
            self.cubic_to(c1x, c1y, c2x, c2y, x, y)
        elif command == COMMAND_CUT_ARC_TO:
            cx, cy, x, y = values
            # self.arc_to()
            # Wrong parameterizations
            pass

    def start(self):
        pass

    def end(self):
        pass

    def move_to(self, x, y):
        self.graphic_path.MoveToPoint(x, y)

    def line_to(self, ex, ey):
        self.graphic_path.AddLineToPoint(ex, ey)

    def quad_to(self, cx, cy, ex, ey):
        self.graphic_path.AddQuadCurveToPoint(wx.Point2D(cx, cy),
                                              wx.Point2D(ex, ey))

    def cubic_to(self, c1x, c1y, c2x, c2y, ex, ey):
        self.graphic_path.AddCurveToPoint(c1x, c1y, c2x, c2y, ex, ey)

    def arc_to(self, radius, rotation, arc, sweep, ex, ey):
        sx = self.graphic_path.GetCurrentX()
        sy = self.graphic_path.GetCurrentY()
        element = path.Arc(sx + (sy * 1j), radius, rotation, arc, sweep, ex + (ey * 1j))
        self.graphic_path.AddArc(element.center.real, element.center.imag, element.radius, element.theta,
                                 element.theta + element.sweep)

    def closed(self):
        pass


class LaserThread(threading.Thread):
    def __init__(self, project):
        threading.Thread.__init__(self)
        self.project = project
        self.writer = project.writer
        self.elements = project.elements

    def burn_project(self):
        for element in self.elements:
            self.burn_element(element.generate())

    def burn_element(self, element):
        for command, values in element:
            if command == COMMAND_SIMPLE_MOVE:
                x, y = values
                self.writer.plot(x, y)
            if command == COMMAND_LASER_OFF:
                self.writer.up()
            if command == COMMAND_LASER_ON:
                self.writer.down()
            elif command == COMMAND_SIMPLE_CUT:
                self.writer.down()
                x, y = values
                self.writer.plot(x, y)
            elif command == COMMAND_SIMPLE_SHIFT:
                self.writer.up()
                x, y = values
                self.writer.plot(x, y)
            elif command == COMMAND_RAPID_MOVE:
                self.writer.to_default_mode()
                x, y = values
                self.writer.move(x, y)
            elif command == COMMAND_SET_SPEED:
                speed = values
                self.writer.speed = speed
            elif command == COMMAND_SET_STEP:
                step = values
                self.writer.raster_step = step
            elif command == COMMAND_MODE_COMPACT:
                self.writer.to_compact_mode()
            elif command == COMMAND_MODE_DEFAULT:
                self.writer.to_default_mode()
            elif command == COMMAND_MODE_CONCAT:
                self.writer.to_concat_mode()
            elif command == COMMAND_HSTEP:
                self.writer.v_switch()
            elif command == COMMAND_VSTEP:
                self.writer.h_switch()
            elif command == COMMAND_HOME:
                self.writer.home()
            elif command == COMMAND_LOCK:
                self.writer.lock_rail()
            elif command == COMMAND_UNLOCK:
                self.writer.unlock_rail()
            elif command == COMMAND_MOVE_TO:
                x, y = values
                for x, y, on in ZinglPlotter.plot_line(int(self.writer.current_x), int(self.writer.current_y), x, y):
                    self.writer.move(x - self.writer.current_x, y - self.writer.current_y)
            elif command == COMMAND_CUT_LINE_TO:
                x, y = values
                self.writer.down()
                for x, y, on in ZinglPlotter.plot_line(int(self.writer.current_x), int(self.writer.current_y), x, y):
                    self.writer.move(x - self.writer.current_x, y - self.writer.current_y)
            elif command == COMMAND_CUT_QUAD_TO:
                cx, cy, x, y = values
                self.writer.down()
                for x, y, on in ZinglPlotter.plot_quad_bezier(int(self.writer.current_x), int(self.writer.current_y),
                                                              cx, cy, x, y):
                    self.writer.move(x - self.writer.current_x, y - self.writer.current_y)
            elif command == COMMAND_CUT_CUBIC_TO:
                c1x, c1y, c2x, c2y, x, y = values
                self.writer.down()
                #  --- This currently does not actually work
                # self.execute(ZinglPlotter.plot_cubic_bezier(
                #         int(self.writer.current_x), int(self.writer.current_y),
                #         c1x, c1y,
                #         c2x, c2y,
                #         x, y))
                self.writer.down()
                for x, y, on in ZinglPlotter.plot_line(int(self.writer.current_x), int(self.writer.current_y), x, y):
                    self.writer.move(x - self.writer.current_x, y - self.writer.current_y)
            elif command == COMMAND_CUT_ARC_TO:
                cx, cy, x, y = values
                # I do not actually have an arc plotter.
                self.writer.down()
                for x, y, on in ZinglPlotter.plot_line(int(self.writer.current_x), int(self.writer.current_y), x, y):
                    self.writer.move(x - self.writer.current_x, y - self.writer.current_y)

    def run(self):
        self.burn_project()
        self.project.thread = None


class LaserProject:
    def __init__(self):
        self.elements = []
        self.size = 320, 220
        self.controller = K40Controller()
        #self.controller = MockController()

        self.writer = LhymicroWriter(controller=self.controller)
        self.update_listener = None
        self.selected = []
        self.thread = None

    def select(self, position):
        self.selected = []
        for e in self.elements:
            matrix = e.matrix
            p = matrix.InverseTransformPoint(position)
            if e.box.Contains(p):
                self.selected.append(e)

    def burn_project(self):
        if self.thread is None:
            self.thread = LaserThread(self)
            self.thread.start()

    def move_selected(self, dx, dy):
        for e in self.selected:
            e.move(dx, dy)

    def add_element(self, obj):
        self.elements.append(obj)
        if self.update_listener is not None:
            self.update_listener(None)


def direct_plots(generate):
    cx = 0
    cy = 0
    con = None
    x = 0
    y = 0
    on = None
    for event in generate():
        x, y, on = event
        dx = x - cx
        dy = y - cy

        if con != on or (dx != 0 and dy != 0 and abs(dx) != abs(dy)):
            yield cx, cy, con
            cx = x
            cy = y
            con = on
    if cx != x or cy != y or con != on:
        yield cx, cy, on


def as_lines(generator):
    cx = None
    cy = None
    for event in generator:
        x, y, on = event
        if cx is not None and on != 0:
            yield (cx, cy, x, y)
        cx = x
        cy = y
