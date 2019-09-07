import threading
import time

import wx

import EgvParser
import RasterPlotter
import ZinglPlotter
import path
import svg_parser
from K40Controller import K40Controller
from LaserCommandConstants import *
from LhymicroWriter import LhymicroWriter
from ZMatrix import ZMatrix
from path import Move, Line, QuadraticBezier, CubicBezier, Arc


class LaserElement:
    def __init__(self):
        self.matrix = ZMatrix()
        self.cut = {"color": 0, "speed": 60, "passes": 1}
        self.cache = None
        self.pen = wx.Pen()
        self.color = wx.Colour()
        self.box = None
        self.color.SetRGB(self.cut['color'])

    def draw(self, dc):
        """Default draw routine for the laser element.
        If the generate is defined this will draw the
        element as a series of lines, as defined by generate."""

        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, self.matrix))
        self.color.SetRGB(self.cut['color'])
        self.pen.SetColour(self.color)
        gc.SetPen(self.pen)
        if self.cache is None:
            p = gc.CreatePath()
            parse = LaserCommandPathParser(p)
            for event in self.generate():
                parse.command(event)
            self.cache = p
        gc.StrokePath(self.cache)

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
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, self.matrix))
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
        gc.DrawBitmap(self.cache, 0, 0, self.image.width, self.image.height)

    def filter(self, pixel):
        if pixel[0] + pixel[1] + pixel[2] <= 384:
            return 1
        return 0

    def generate(self):
        yield COMMAND_SET_SPEED, (self.cut.get("speed"))
        yield COMMAND_SET_STEP, (self.cut.get("step"))
        for event in RasterPlotter.plot_raster(self.image, filter=self.filter, overscan=100):
            x, y, pixel_color = event
            point = self.matrix.TransformPoint(x, y)
            if not isinstance(pixel_color, int) and pixel_color[0] + pixel_color[1] + pixel_color[2] <= 384:
                yield COMMAND_SIMPLE_CUT, (point[0], point[1])
            else:
                yield COMMAND_SIMPLE_SHIFT, (point[0], point[1])


class PathElement(LaserElement):
    def __init__(self, path):
        LaserElement.__init__(self)
        self.path = path
        self.box = None
        self.cut.update({"color": 0x00FF00, "speed": 20})

    def generate(self):
        parse = path.ObjectParser()
        svg_parser.parse_svg_path(parse, self.path)
        object_path = parse.path
        self.box = wx.Rect2D(object_path.bbox())
        yield COMMAND_SET_SPEED, self.cut.get("speed")
        yield COMMAND_SET_STEP, 0
        yield COMMAND_MODE_COMPACT, 0
        for data in object_path:
            if isinstance(data, Move):
                s = self.matrix.TransformPoint(data.end.real, data.end.imag)
                yield COMMAND_MOVE_TO, (int(s[0]), int(s[1]))
            elif isinstance(data, Line):
                s = self.matrix.TransformPoint(data.start.real, data.start.imag)
                e = self.matrix.TransformPoint(data.end.real, data.end.imag)
                yield COMMAND_CUT_LINE_TO, (int(s[0]), int(s[1]),
                                            int(e[0]), int(e[1]))
            elif isinstance(data, QuadraticBezier):
                s = self.matrix.TransformPoint(data.start.real, data.start.imag)
                c = self.matrix.TransformPoint(data.control.real, data.control.imag)
                e = self.matrix.TransformPoint(data.end.real, data.end.imag)
                yield COMMAND_CUT_QUAD_TO, (int(s[0]), int(s[1]),
                                            c[0], c[1],
                                            int(e[0]), int(e[1]))
            elif isinstance(data, CubicBezier):
                s = self.matrix.TransformPoint(data.start.real, data.start.imag)
                c1 = self.matrix.TransformPoint(data.control1.real, data.control1.imag)
                c2 = self.matrix.TransformPoint(data.control2.real, data.control2.imag)
                e = self.matrix.TransformPoint(data.end.real, data.end.imag)
                yield COMMAND_CUT_CUBIC_TO, (int(s[0]), int(s[1]),
                                             c1[0], c1[1],
                                             c2[0], c2[1],
                                             int(e[0]), int(e[1]))
            elif isinstance(data, Arc):
                s = self.matrix.TransformPoint(data.start.real, data.start.imag)
                c = self.matrix.TransformPoint(data.center.real, data.center.imag)
                e = self.matrix.TransformPoint(data.end.real, data.end.imag)
                yield COMMAND_CUT_ARC_TO, (int(s[0]), int(s[1]),
                                           int(c[0]), int(c[1]),
                                           int(e[0]), int(e[1]))
        yield COMMAND_MODE_DEFAULT, 0
        yield COMMAND_SET_SPEED, 0


class EgvElement(LaserElement):
    def __init__(self, file):
        LaserElement.__init__(self)
        self.file = file
        self.box = wx.Rect2D(0, 0, 0, 0)
        self.cut.update({"color": 0x0000FF, "speed": 20})

    def generate(self):
        for event in EgvParser.parse_egv(self.file):
            yield event

    def draw(self, dc):
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, self.matrix))
        self.color.SetRGB(self.cut['color'])
        self.pen.SetColour(self.color)
        gc.SetPen(self.pen)
        if self.cache is None:
            p = gc.CreatePath()
            parse = LaserCommandPathParser(p)
            for event in self.generate():
                parse.command(event)
            self.cache = p
            self.box = self.cache.GetBox()
        gc.StrokePath(self.cache)


class RawElement(LaserElement):
    def __init__(self, element):
        LaserElement.__init__(self)
        self.command_list = []
        for command in element.generate():
            self.command_list.append(command)

    def generate(self):
        for command in self.command_list:
            yield command


class LaserCommandPathParser:
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
            sx, sy, ex, ey = values
            self.line_to(ex, ey)
        elif command == COMMAND_CUT_QUAD_TO:
            sx, sy, cx, cy, x, y = values
            self.quad_to(cx, cy, x, y)
        elif command == COMMAND_CUT_CUBIC_TO:
            sx, sy, c1x, c1y, c2x, c2y, x, y = values
            self.cubic_to(c1x, c1y, c2x, c2y, x, y)
        elif command == COMMAND_CUT_ARC_TO:
            sx, sy, cx, cy, x, y = values
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
        self.graphic_path.AddQuadCurveToPoint(cx, cy, ex, ey)

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
        self.controller = project.controller
        self.elements = project.elements

    def burn_project(self):
        for element in self.elements:
            self.burn_element(element.generate())

    def burn_element(self, element):
        for command, values in element:
            while self.controller.count_packet_buffer() > 5:
                # Backend is clogged and not sending stuff. We're waiting.
                time.sleep(0.1)  # if we've given it enough for a while just wait here.

            if command == COMMAND_SIMPLE_MOVE:
                x, y = values
                self.writer.move_abs(x, y)
            if command == COMMAND_LASER_OFF:
                self.writer.up()
            if command == COMMAND_LASER_ON:
                self.writer.down()
            elif command == COMMAND_SIMPLE_CUT:
                self.writer.down()
                x, y = values
                self.writer.move_abs(x, y)
            elif command == COMMAND_SIMPLE_SHIFT:
                self.writer.up()
                x, y = values
                self.writer.move_abs(x, y)
            elif command == COMMAND_RAPID_MOVE:
                self.writer.to_default_mode()
                sx, sy, x, y = values
                self.writer.move_abs(x, y)
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
                ex, ey = values
                self.writer.up()
                for x, y, on in direct_plots(self.writer.current_x, self.writer.current_y,
                                             ZinglPlotter.plot_line(
                                                 int(self.writer.current_x),
                                                 int(self.writer.current_y), ex, ey
                                             )):
                    self.writer.move_abs(x, y)
            elif command == COMMAND_CUT_LINE_TO:
                sx, sy, ex, ey = values
                self.writer.down()
                for x, y, on in direct_plots(sx, sy, ZinglPlotter.plot_line(sx, sy,
                                                                            ex, ey)):
                    self.writer.move_abs(x, y)
            elif command == COMMAND_CUT_QUAD_TO:
                sx, sy, cx, cy, ex, ey = values
                self.writer.down()
                for x, y, on in direct_plots(sx, sy,
                                             ZinglPlotter.plot_quad_bezier(sx, sy,
                                                                           cx, cy,
                                                                           ex, ey)):
                    self.writer.move_abs(x, y)
            elif command == COMMAND_CUT_CUBIC_TO:
                sx, sy, c1x, c1y, c2x, c2y, ex, ey = values
                self.writer.down()
                for x, y, on in direct_plots(sx, sy,
                                             ZinglPlotter.plot_cubic_bezier(sx, sy,
                                                                            c1x, c1y,
                                                                            c2x, c2y,
                                                                            ex, ey)):
                    self.writer.move_abs(x, y)
            elif command == COMMAND_CUT_ARC_TO:
                sx, sy, cx, cy, ex, ey = values
                # I do not actually have an arc plotter.
                self.writer.down()
                for x, y, on in ZinglPlotter.plot_line(sx, sy, ex, ey):
                    self.writer.move_abs(x, y)

    def run(self):
        self.burn_project()
        self.project.thread = None


class LaserProject:
    def __init__(self):
        self.elements = []
        self.size = 320, 220
        self.controller = K40Controller()  #mock=True

        self.writer = LhymicroWriter(controller=self.controller)
        self.update_listener = None
        self.selected = []
        self.thread = None

    def select(self, position):
        self.selected = []
        for e in self.elements:
            matrix = e.matrix
            p = matrix.InverseTransformPoint(position)
            if e.box is None:
                continue
            if e.box.Contains(p):
                self.selected.append(e)

    def burn_project(self):
        if self.thread is None:
            self.thread = LaserThread(self)
            self.thread.start()

    def bbox(self):
        boxes = []
        for e in self.elements:
            box = e.box
            if box is None:
                continue
            top_left = e.matrix.TransformPoint([box.Left, box.Top])
            bottom_right = e.matrix.TransformPoint([box.Bottom, box.Right])
            boxes.append([top_left[0], top_left[1], bottom_right[0], bottom_right[1]])
        xmin = min([box[0] for box in boxes])
        ymin = min([box[1] for box in boxes])
        xmax = max([box[2] for box in boxes])
        ymax = max([box[3] for box in boxes])
        return xmin, ymin, xmax, ymax

    def menu_convert_raw(self, position):
        self.selected = []
        for e in self.elements:
            if isinstance(e, RawElement):
                continue
            matrix = e.matrix
            p = matrix.InverseTransformPoint(position)
            if e.box.Contains(p):
                self.remove_element(e)
                self.add_element(RawElement(e))
                break

    def menu_remove_element(self, position):
        for e in self.elements:
            matrix = e.matrix
            p = matrix.InverseTransformPoint(position)
            if e.box.Contains(p):
                self.remove_element(e)
                break

    def menu_scale(self, position, scale):
        for e in self.elements:
            matrix = e.matrix
            p = matrix.InverseTransformPoint(position)
            if e.box.Contains(p):
                e.matrix.PostScale(scale)

    def move_selected(self, dx, dy):
        for e in self.selected:
            e.move(dx, dy)

    def remove_element(self,obj):
        self.elements.remove(obj)
        if self.update_listener is not None:
            self.update_listener(None)

    def add_element(self, obj):
        self.elements.append(obj)
        if self.update_listener is not None:
            self.update_listener(None)


def direct_plots(start_x, start_y, generate):
    last_x = start_x
    last_y = start_y
    dx = 0
    dy = 0

    for event in generate:
        x, y, on = event
        if x == last_x + dx and y == last_y + dy:
            last_x = x
            last_y = y
            continue

        yield last_x, last_y, 1
        dx = x - last_x
        dy = y - last_y
        if abs(dx) > 1 or abs(dy) > 1:
            raise ValueError
        last_x = x
        last_y = y
    yield last_x, last_y, 1
