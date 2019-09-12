import threading
import time

import wx

import EgvParser
import RasterPlotter
import path
import svg_parser
from K40Controller import K40Controller
from LaserCommandConstants import *
from LhymicroWriter import LhymicroWriter
from ThreadConstants import *
from ZMatrix import ZMatrix
from path import Move, Line, QuadraticBezier, CubicBezier, Arc

VARIABLE_NAME_NAME = 'name'
VARIABLE_NAME_COLOR = 'color'
VARIABLE_NAME_SPEED = 'speed'
VARIABLE_NAME_PASSES = 'passes'
VARIABLE_NAME_DRATIO = 'd_ratio'
VARIABLE_NAME_RASTER_STEP = "raster_step"
VARIABLE_NAME_RASTER_DIRECTION = 'raster_direction'


class LaserElement:
    def __init__(self):
        self.matrix = ZMatrix()
        self.cut = {VARIABLE_NAME_COLOR: 0, VARIABLE_NAME_SPEED: 60, VARIABLE_NAME_PASSES: 1}
        self.cache = None
        self.pen = wx.Pen()
        self.color = wx.Colour()
        self.color.SetRGB(self.cut['color'])
        self.box = [-10, -10, 10, 10]
        self.parent = None

    def draw(self, dc):
        """Default draw routine for the laser element.
        If the generate is defined this will draw the
        element as a series of lines, as defined by generate."""

        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, self.matrix))
        self.color.SetRGB(self.cut[VARIABLE_NAME_COLOR])
        self.pen.SetColour(self.color)
        gc.SetPen(self.pen)
        if self.cache is None:
            p = gc.CreatePath()
            parse = LaserCommandPathParser(p)
            for event in self.generate():
                parse.command(event)
            self.cache = p
        gc.StrokePath(self.cache)

    def convert_absolute_to_affinespace(self, position):
        if isinstance(position, complex):
            return self.matrix.TransformPoint([position.real, position.imag])
        return self.matrix.TransformPoint([position[0], position[1]])

    def convert_affinespace_to_absolute(self, position):
        if isinstance(position, complex):
            return self.matrix.InverseTransformPoint([position.real, position.imag])
        return self.matrix.InverseTransformPoint([position[0], position[1]])

    def generate(self):
        yield COMMAND_MODE_DEFAULT

    def move(self, dx, dy):
        self.matrix.PostTranslate(dx, dy)

    def contains(self, x, y=None):
        if y is None:
            x, y = x
        return self.box[0] <= x <= self.box[2] and self.box[1] <= y <= self.box[3]


class ImageElement(LaserElement):
    def __init__(self, image):
        LaserElement.__init__(self)
        self.box = [0, 0, image.width, image.height]
        self.image = image
        self.cut.update({VARIABLE_NAME_RASTER_STEP: 1,
                         VARIABLE_NAME_SPEED: 100})

    def draw(self, dc):
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, self.matrix))
        if self.cache is None:
            width = self.image.width
            height = self.image.height
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
        speed = 100
        if VARIABLE_NAME_SPEED in self.cut:
            speed = self.cut[VARIABLE_NAME_SPEED]
        if speed is None:
            speed = 100
        yield COMMAND_SET_SPEED, speed
        step = 1
        if VARIABLE_NAME_RASTER_STEP in self.cut:
            step = self.cut[VARIABLE_NAME_RASTER_STEP]
        yield COMMAND_SET_STEP, step

        direction = 0
        if VARIABLE_NAME_RASTER_DIRECTION in self.cut:
            direction = self.cut[VARIABLE_NAME_RASTER_DIRECTION]
            print(direction)
        print(direction)
        transverse = 0
        if direction == 0:
            transverse |= RasterPlotter.X_AXIS
            transverse |= RasterPlotter.TOP
        elif direction == 1:
            transverse |= RasterPlotter.X_AXIS
            transverse |= RasterPlotter.BOTTOM
        elif direction == 2:
            transverse |= RasterPlotter.Y_AXIS
            transverse |= RasterPlotter.LEFT
        elif direction == 3:
            transverse |= RasterPlotter.Y_AXIS
            transverse |= RasterPlotter.RIGHT
        for command in RasterPlotter.plot_raster(self.image, filter=self.filter,
                                                 offset_x=self.matrix.GetTranslateX(),
                                                 offset_y=self.matrix.GetTranslateY(),
                                                 transversal=transverse):
            yield command
        yield COMMAND_MODE_DEFAULT, 0


class PathElement(LaserElement):
    def __init__(self, path_d):
        LaserElement.__init__(self)
        self.path = path_d
        self.cut.update({VARIABLE_NAME_COLOR: 0x00FF00, VARIABLE_NAME_SPEED: 20})

    def generate(self):
        parse = path.ObjectParser()
        svg_parser.parse_svg_path(parse, self.path)
        object_path = parse.path
        self.box = object_path.bbox()
        speed = self.cut.get(VARIABLE_NAME_SPEED)
        if speed is None:
            speed = 100
        yield COMMAND_SET_SPEED, speed
        yield COMMAND_SET_STEP, 0
        yield COMMAND_MODE_COMPACT, 0
        for data in object_path:
            if isinstance(data, Move):
                s = self.convert_absolute_to_affinespace(data.end)
                yield COMMAND_MOVE_TO, (int(s[0]), int(s[1]))
            elif isinstance(data, Line):
                s = self.convert_absolute_to_affinespace(data.start)
                e = self.convert_absolute_to_affinespace(data.end)
                yield COMMAND_CUT_LINE, (int(s[0]), int(s[1]),
                                         int(e[0]), int(e[1]))
            elif isinstance(data, QuadraticBezier):
                s = self.convert_absolute_to_affinespace(data.start)
                c = self.convert_absolute_to_affinespace(data.control)
                e = self.convert_absolute_to_affinespace(data.end)
                yield COMMAND_CUT_QUAD, (int(s[0]), int(s[1]),
                                         c[0], c[1],
                                         int(e[0]), int(e[1]))
            elif isinstance(data, CubicBezier):
                s = self.convert_absolute_to_affinespace(data.start)
                c1 = self.convert_absolute_to_affinespace(data.control1)
                c2 = self.convert_absolute_to_affinespace(data.control2)
                e = self.convert_absolute_to_affinespace(data.end)
                yield COMMAND_CUT_CUBIC, (int(s[0]), int(s[1]),
                                          c1[0], c1[1],
                                          c2[0], c2[1],
                                          int(e[0]), int(e[1]))
            elif isinstance(data, Arc):
                s = self.convert_absolute_to_affinespace(data.start)
                c = self.convert_absolute_to_affinespace(data.center)
                e = self.convert_absolute_to_affinespace(data.end)
                yield COMMAND_CUT_ARC, (int(s[0]), int(s[1]),
                                        int(c[0]), int(c[1]),
                                        int(e[0]), int(e[1]))
        yield COMMAND_MODE_DEFAULT, 0
        yield COMMAND_SET_SPEED, None
        yield COMMAND_SET_D_RATIO, None


class EgvElement(LaserElement):
    def __init__(self, file):
        LaserElement.__init__(self)
        self.file = file
        self.cut.update({VARIABLE_NAME_COLOR: 0x0000FF, VARIABLE_NAME_SPEED: 20})

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
            # print(parse.x, parse.y)
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
    """This class converts a set of laser commands into a
     graphical representation of those commands."""

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
            ex, ey = values
            self.line_to(ex, ey)
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
        elif command == COMMAND_CUT_LINE:
            sx, sy, ex, ey = values
            self.move_to(sx, sy)
            self.line_to(ex, ey)
        elif command == COMMAND_CUT_QUAD:
            sx, sy, cx, cy, x, y = values
            self.move_to(sx, sy)
            self.quad_to(cx, cy, x, y)
        elif command == COMMAND_CUT_CUBIC:
            sx, sy, c1x, c1y, c2x, c2y, x, y = values
            self.move_to(sx, sy)
            self.cubic_to(c1x, c1y, c2x, c2y, x, y)
        elif command == COMMAND_CUT_ARC:
            sx, sy, cx, cy, x, y = values
            self.move_to(x, y)
            # self.arc_to()
            # Wrong parameterizations
            pass

    def start(self):
        pass

    def end(self):
        pass

    def move_to(self, x, y):
        self.graphic_path.MoveToPoint(x, y)
        self.x = x
        self.y = y

    def line_to(self, ex, ey):
        self.graphic_path.AddLineToPoint(ex, ey)
        self.x = ex
        self.y = ey

    def quad_to(self, cx, cy, ex, ey):
        self.graphic_path.AddQuadCurveToPoint(cx, cy, ex, ey)
        self.x = ex
        self.y = ey

    def cubic_to(self, c1x, c1y, c2x, c2y, ex, ey):
        self.graphic_path.AddCurveToPoint(c1x, c1y, c2x, c2y, ex, ey)
        self.x = ex
        self.y = ey

    def arc_to(self, radius, rotation, arc, sweep, ex, ey):
        sx = self.graphic_path.GetCurrentX()
        sy = self.graphic_path.GetCurrentY()
        element = path.Arc(sx + (sy * 1j), radius, rotation, arc, sweep, ex + (ey * 1j))
        self.graphic_path.AddArc(element.center.real, element.center.imag, element.radius, element.theta,
                                 element.theta + element.sweep)
        self.x = ex
        self.y = ey

    def closed(self):
        pass


class LaserThread(threading.Thread):
    def __init__(self, project):
        threading.Thread.__init__(self)
        self.project = project
        self.writer = project.writer
        self.controller = project.controller
        self.element_list = None
        self.element_index = -1
        self.command_index = -1
        self.limit_buffer = True
        self.buffer_max = 50*30
        self.buffer_size = -1
        self.state = THREAD_STATE_UNSTARTED
        self.autohome = self.project.autohome
        self.autobeep = self.project.autobeep
        self.element_index = 0
        self.command_index = 0
        self.element_list = [e for e in self.project.flat_elements()]
        self.project("progress", (self.element_index, len(self.element_list)))

    def start_element_producer(self):
        if self.state != THREAD_STATE_ABORT:
            self.state = THREAD_STATE_STARTED
            self.start()

    def run(self):
        self.element_index = 0
        self.project("progress", (self.element_index, len(self.element_list)))
        self.project["buffer"] = self.update_buffer_size
        while self.state != THREAD_STATE_ABORT and self.state != THREAD_STATE_FINISHED:
            self.process_queue()
            time.sleep(0.1)
            while self.state == THREAD_STATE_PAUSED:
                time.sleep(1)
        # Final listener calls.
        if self.autohome:
            return self.writer.command(COMMAND_HOME, 0)
        self.element_list = None
        self.element_index = -1
        self.project["buffer", self.update_buffer_size] = None
        if self.autobeep:
            print('\a')  # Beep.

    def update_buffer_size(self, size):
        self.buffer_size = size

    def process_queue(self):
        if self.element_list is None:
            self.state = THREAD_STATE_FINISHED
            return
        try:
            element = self.element_list[self.element_index]
        except IndexError:
            self.state = THREAD_STATE_FINISHED
            return
        commands_gen = element.generate()
        while True:
            self.project("progress", (self.element_index + 1, len(self.element_list)))
            self.project("command", self.command_index)
            while self.limit_buffer and self.buffer_size > self.buffer_max:
                # Backend is clogged and not sending stuff. We're waiting.
                time.sleep(0.1)  # if we've given it enough for a while just wait here.
            try:
                e = next(commands_gen)
            except StopIteration:
                self.element_index += 1
                break
            command, values = e
            self.writer.command(command, values)
            self.command_index += 1


class LaserProject:
    def __init__(self):
        self.listeners = {}
        self.last_message = {}
        self.elements = []
        self.size = 320, 220
        self.units = (39.37, "mm", 10)
        self.controller = K40Controller(self)

        self.writer = LhymicroWriter(controller=self.controller)
        self.selection_listener = None
        self.elements_change_listener = None
        self.unit_space_listener = None

        self.selected = []
        self.selected_bbox = None
        self.thread = None
        self.autohome = False
        self.autobeep = True

    def __call__(self, code, message):
        if code in self.listeners:
            listeners = self.listeners[code]
            for listener in listeners:
                listener(message)
        self.last_message[code] = message

    def __setitem__(self, key, value):
        if value is None:
            key, value = key
            self.remove_listener(value, key)
        else:
            self.add_listener(value, key)

    def __getitem__(self, item):
        if item in self.listeners:
            return self.listeners[item]
        else:
            return None

    def add_listener(self, listener, code):
        if code in self.listeners:
            listeners = self.listeners[code]
            listeners.append(listener)
        else:
            self.listeners[code] = [listener]
        if code in self.last_message:
            last_message = self.last_message[code]
            listener(last_message)

    def remove_listener(self, listener, code):
        if code in self.listeners:
            listeners = self.listeners[code]
            listeners.remove(listener)

    def flat_elements(self, elements=None):
        if elements is None:
            elements = self.elements
        for element in elements:
            if isinstance(element, LaserElement):
                element.parent = elements
                yield element
            else:
                for flat_element in self.flat_elements(element):
                    yield flat_element

    def size_in_native_units(self):
        return self.size[0] * 39.37, self.size[1] * 39.37

    def set_inch(self):
        self.units = (1000, "inch", 1)
        if self.unit_space_listener is not None:
            self.unit_space_listener()

    def set_mil(self):
        self.units = (1, "mil", 1000)
        if self.unit_space_listener is not None:
            self.unit_space_listener()

    def set_cm(self):
        self.units = (393.7, "cm", 1)
        if self.unit_space_listener is not None:
            self.unit_space_listener()

    def set_mm(self):
        self.units = (39.37, "mm", 10)
        if self.unit_space_listener is not None:
            self.unit_space_listener()

    def set_selected(self, select_elements):
        if isinstance(select_elements, list):
            self.selected = select_elements
        else:
            self.selected = [select_elements]
        self.set_selected_bbox_by_selected()
        if self.selection_listener is not None:
            self.selection_listener(self.selected)

    def set_selected_bbox_by_selected(self):
        boundary_points = []
        for e in self.selected:
            box = e.box
            if box is None:
                continue
            left_top = e.convert_absolute_to_affinespace([box[0], box[1]])
            right_top = e.convert_absolute_to_affinespace([box[2], box[1]])
            left_bottom = e.convert_absolute_to_affinespace([box[0], box[3]])
            right_bottom = e.convert_absolute_to_affinespace([box[2], box[3]])
            boundary_points.append(left_top)
            boundary_points.append(right_top)
            boundary_points.append(left_bottom)
            boundary_points.append(right_bottom)
        if len(boundary_points) > 0:
            xmin = min([e[0] for e in boundary_points])
            ymin = min([e[1] for e in boundary_points])
            xmax = max([e[0] for e in boundary_points])
            ymax = max([e[1] for e in boundary_points])
            self.selected_bbox = [xmin, ymin, xmax, ymax]
        else:
            self.selected_bbox = None

    def set_selected_by_position(self, position):
        self.selected = []
        for e in self.flat_elements():
            box = e.box
            if box is None:
                continue
            matrix = e.matrix
            p = matrix.InverseTransformPoint(position)
            if e.contains(p):
                if e.parent is None:
                    self.set_selected(e)
                else:
                    self.set_selected(e.parent)
                break
        if self.selection_listener is not None:
            self.selection_listener(self.selected)

    def bbox(self):
        boundary_points = []
        for e in self.flat_elements():
            box = e.box
            if box is None:
                continue
            top_left = e.matrix.TransformPoint([box[0], box[1]])
            top_right = e.matrix.TransformPoint([box[2], box[1]])
            bottom_left = e.matrix.TransformPoint([box[0], box[3]])
            bottom_right = e.matrix.TransformPoint([box[2], box[3]])
            boundary_points.append(top_left)
            boundary_points.append(top_right)
            boundary_points.append(bottom_left)
            boundary_points.append(bottom_right)
        if len(boundary_points) == 0:
            return None
        xmin = min([e[0] for e in boundary_points])
        ymin = min([e[1] for e in boundary_points])
        xmax = max([e[0] for e in boundary_points])
        ymax = max([e[1] for e in boundary_points])
        return xmin, ymin, xmax, ymax

    def menu_convert_raw(self, position):
        for e in self.flat_elements():
            if isinstance(e, RawElement):
                continue
            matrix = e.matrix
            p = matrix.InverseTransformPoint(position)
            if e.contains(p):
                self.remove_element(e)
                self.append(RawElement(e))
                break

    def menu_remove(self, position):
        for e in self.flat_elements():
            matrix = e.matrix
            p = matrix.InverseTransformPoint(position)
            if e.contains(p):
                self.remove_element(e)
                break

    def menu_scale(self, scale, scale_y=None, position=None):
        if scale_y is None:
            scale_y = scale
        for e in self.flat_elements():
            matrix = e.matrix
            if position is not None:
                p = matrix.InverseTransformPoint(position)
                if e.contains(p):
                    e.matrix.PostScale(scale, scale_y, p[0], p[1])
            else:
                for e in self.selected:
                    e.matrix.PostScale(scale, scale_y)

    def menu_rotate(self, radians, position=None):
        for e in self.flat_elements():
            matrix = e.matrix
            if position is not None:
                p = matrix.InverseTransformPoint(position)
                if e.contains(p):
                    e.matrix.PostRotate(radians, p[0], p[1])
            else:
                for e in self.selected:
                    e.matrix.PostRotate(radians)

    def move_selected(self, dx, dy):
        for e in self.selected:
            e.move(dx, dy)
        if self.selected_bbox is not None:
            self.selected_bbox[0] += dx
            self.selected_bbox[2] += dx
            self.selected_bbox[1] += dy
            self.selected_bbox[3] += dy

    def remove_element(self, obj):
        obj.parent.remove(obj)
        if self.elements_change_listener is not None:
            self.elements_change_listener()

    def append(self, obj):
        self.elements.append(obj)
        if self.elements_change_listener is not None:
            self.elements_change_listener()
