import wx

import RasterPlotter
import path
import svg_parser
from K40Controller import K40Controller
from LaserCommandConstants import *
from LhymicroWriter import LhymicroWriter
from ZMatrix import ZMatrix

VARIABLE_NAME_NAME = 'name'
VARIABLE_NAME_COLOR = 'color'
VARIABLE_NAME_SPEED = 'speed'
VARIABLE_NAME_PASSES = 'passes'
VARIABLE_NAME_DRATIO = 'd_ratio'
VARIABLE_NAME_RASTER_STEP = "raster_step"
VARIABLE_NAME_RASTER_DIRECTION = 'raster_direction'


class LaserElement:
    def __init__(self):
        self.matrix = path.Matrix()
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
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(self.matrix)))
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
        return self.matrix.point_in_matrix_space(position)

    def convert_affinespace_to_absolute(self, position):
        return self.matrix.point_in_inverse_space(position)

    def generate(self):
        yield COMMAND_MODE_DEFAULT

    def move(self, dx, dy):
        self.matrix.pre_translate(dx, dy)

    def contains(self, x, y=None):
        if y is None:
            x, y = x
        return self.box[0] <= x <= self.box[2] and self.box[1] <= y <= self.box[3]


class ImageElement(LaserElement):
    def __init__(self, image):
        LaserElement.__init__(self)
        self.box = [0, 0, image.width, image.height]
        self.image = image
        self.cache = None
        self.cut.update({VARIABLE_NAME_RASTER_STEP: 1,
                         VARIABLE_NAME_SPEED: 100})

    def draw(self, dc):
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(self.matrix)))
        if self.cache is None:
            myPilImage = self.image
            myWxImage = wx.Image(*myPilImage.size)
            myPilImageCopy = myPilImage.copy()
            myPilImageCopyRGB = myPilImageCopy.convert('RGB')  # Discard any alpha from the PIL image.
            myPilImageRgbData = myPilImageCopyRGB.tobytes()
            myWxImage.SetData(myPilImageRgbData)
            self.cache = myWxImage.ConvertToBitmap()
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

        direction = 0
        if VARIABLE_NAME_RASTER_DIRECTION in self.cut:
            direction = self.cut[VARIABLE_NAME_RASTER_DIRECTION]
        step = 1
        if VARIABLE_NAME_RASTER_STEP in self.cut:
            step = self.cut[VARIABLE_NAME_RASTER_STEP]
        transverse = 0
        if direction == 0:
            yield COMMAND_SET_STEP, step
            transverse |= RasterPlotter.X_AXIS
            transverse |= RasterPlotter.TOP
        elif direction == 1:
            yield COMMAND_SET_STEP, step
            transverse |= RasterPlotter.X_AXIS
            transverse |= RasterPlotter.BOTTOM
        for command in RasterPlotter.plot_raster(self.image, filter=self.filter,
                                                 offset_x=self.matrix.value_trans_x(),
                                                 offset_y=self.matrix.value_trans_y(),
                                                 transversal=transverse,
                                                 step=step):
            yield command


class PathElement(LaserElement):
    def __init__(self, path_d):
        LaserElement.__init__(self)
        self.path = path_d
        self.cut.update({VARIABLE_NAME_COLOR: 0x00FF00, VARIABLE_NAME_SPEED: 20})

    def generate(self):
        object_path = path.Path()
        svg_parser.parse_svg_path(object_path, self.path)
        self.box = object_path.bbox()
        if VARIABLE_NAME_SPEED in self.cut:
            speed = self.cut.get(VARIABLE_NAME_SPEED)
            yield COMMAND_SET_SPEED, speed
        if VARIABLE_NAME_DRATIO in self.cut:
            d_ratio = self.cut.get(VARIABLE_NAME_DRATIO)
            yield COMMAND_SET_D_RATIO, d_ratio
        yield COMMAND_SET_STEP, 0
        yield COMMAND_MODE_COMPACT, 0
        plot = object_path * self.matrix
        yield COMMAND_PLOT, plot
        yield COMMAND_MODE_DEFAULT, 0
        yield COMMAND_SET_SPEED, None
        yield COMMAND_SET_D_RATIO, None


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
        self.relative = False
        self.x = 0
        self.y = 0

    def command(self, event):
        command, values = event
        if command == COMMAND_LASER_OFF:
            self.on = False
        elif command == COMMAND_LASER_ON:
            self.on = True
        elif command == COMMAND_RAPID_MOVE:
            x, y = values
            if self.relative:
                x += self.x
                y += self.y
            self.graphic_path.MoveToPoint(x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_SET_SPEED:
            pass
        elif command == COMMAND_SET_STEP:
            pass
        elif command == COMMAND_SET_DIRECTION:
            pass
        elif command == COMMAND_MODE_COMPACT:
            pass
        elif command == COMMAND_MODE_DEFAULT:
            pass
        elif command == COMMAND_MODE_CONCAT:
            pass
        elif command == COMMAND_SET_ABSOLUTE:
            self.relative = False
        elif command == COMMAND_SET_INCREMENTAL:
            self.relative = True
        elif command == COMMAND_HSTEP:
            x = values
            y = 0
            if self.relative:
                x += self.x
                y += self.y
            self.graphic_path.MoveToPoint(x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_VSTEP:
            x = 0
            y = values
            if self.relative:
                x += self.x
                y += self.y
            self.graphic_path.MoveToPoint(x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_HOME:
            self.graphic_path.MoveToPoint(0, 0)
            self.x = 0
            self.y = 0
        elif command == COMMAND_LOCK:
            pass
        elif command == COMMAND_UNLOCK:
            pass
        elif command == COMMAND_PLOT:
            plot = values
            for e in plot:
                if isinstance(e, path.Move):
                    self.graphic_path.MoveToPoint(e.end[0], e.end[1])
                elif isinstance(e, path.Line):
                    self.graphic_path.AddLineToPoint(e.end[0], e.end[1])
                elif isinstance(e, path.QuadraticBezier):
                    self.graphic_path.AddQuadCurveToPoint(e.control[0], e.control[1],
                                                          e.end[0], e.end[1])
                elif isinstance(e, path.CubicBezier):
                    self.graphic_path.AddCurveToPoint(e.control1[0], e.control1[1],
                                                      e.control2[0], e.control2[1],
                                                      e.end[0], e.end[1])
                elif isinstance(e, path.Arc):
                    for curve in e.as_cubic_curves():
                        self.graphic_path.AddCurveToPoint(curve.control1[0], curve.control1[1],
                                                          curve.control2[0], curve.control2[1],
                                                          curve.end[0], curve.end[1])

        elif command == COMMAND_SHIFT:
            x, y = values
            if self.relative:
                x += self.x
                y += self.y
            self.graphic_path.MoveToPoint(x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_MOVE:
            x, y = values
            if self.relative:
                x += self.x
                y += self.y
            if self.on:
                self.graphic_path.MoveToPoint(x, y)
            else:
                self.graphic_path.AddLineToPoint(x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_CUT:
            x, y = values
            if self.relative:
                x += self.x
                y += self.y
            self.graphic_path.AddLineToPoint(x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_CUT_QUAD:
            cx, cy, x, y = values
            if self.relative:
                x += self.x
                y += self.y
                cx += self.x
                cy += self.y

            self.graphic_path.AddQuadCurveToPoint(cx, cy, x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_CUT_CUBIC:
            c1x, c1y, c2x, c2y, x, y = values
            if self.relative:
                x += self.x
                y += self.y
                c1x += self.x
                c1y += self.y
                c2x += self.x
                c2y += self.y
            self.graphic_path.AddCurveToPoint(c1x, c1y, c2x, c2y, x, y)
            self.x = x
            self.y = y


class LaserProject:
    def __init__(self):
        self.listeners = {}
        self.last_message = {}
        self.elements = []
        self.size = 320, 220
        self.units = (39.37, "mm", 10, 0)
        self.config = None

        self.selected = []
        self.selected_bbox = None
        self.thread = None
        self.autohome = False
        self.autobeep = True
        self.autostart = True
        self.controller = K40Controller(self)
        self.writer = LhymicroWriter(self, controller=self.controller)

    def __call__(self, code, message):
        if code in self.listeners:
            listeners = self.listeners[code]
            for listener in listeners:
                listener(message)
        self.last_message[code] = message

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            if value is None:
                key, value = key
                self.remove_listener(value, key)
            else:
                key, value = key
                self.add_listener(value, key)
        elif isinstance(key, str):
            if isinstance(value, str):
                self.config.Write(key, value)
            elif isinstance(value, int):
                self.config.WriteInt(key, value)
            elif isinstance(value, float):
                self.config.WriteFloat(key, value)
            elif isinstance(value, bool):
                self.config.WriteBool(key, value)

    def __getitem__(self, item):
        if isinstance(item, tuple):
            if len(item) == 2:
                t, key = item
                if t == str:
                    return self.config.Read(key)
                elif t == int:
                    return self.config.ReadInt(key)
                elif t == float:
                    return self.config.ReadFloat(key)
                elif t == bool:
                    return self.config.ReadBool(key)
            else:
                t, key, default = item
                if t == str:
                    return self.config.Read(key, default)
                elif t == int:
                    return self.config.ReadInt(key, default)
                elif t == float:
                    return self.config.ReadFloat(key, default)
                elif t == bool:
                    return self.config.ReadBool(key, default)
        return self.config.Read(item)

    def load_config(self):
        # self.spin_scalex.SetValue(self.project.writer.scale_x)
        # self.spin_scaley.SetValue(self.project.writer.scale_y)
        # self.checkbox_rotary.SetValue(self.project.writer.rotary)

        self.autohome = self[bool, "autohome"]
        self.autobeep = self[bool, "autobeep"]
        self.autostart = self[bool, "autostart"]
        convert = self[float, "units-convert", self.units[0]]
        name = self[str, "units-name", self.units[1]]
        marks = self[int, "units-marks", self.units[2]]
        unitindex = self[int, "unit-index", self.units[3]]
        self.units = (convert, name, marks, unitindex)
        width = self[int, "bed_width", self.size[0]]
        height = self[int, "bed_height", self.size[1]]
        self.size = width, height
        self.writer.board = self[str, "board", self.writer.board]
        self.writer.autolock = self[bool, "autolock", self.writer.autolock]
        self.writer.rotary = self[bool, "rotary", self.writer.rotary]
        self.writer.scale_x = self[float, "scale_x", self.writer.scale_x]
        self.writer.scale_y = self[float, "scale_y", self.writer.scale_y]
        self.controller.mock = self[bool, "mock", self.controller.mock]
        self.controller.usb_index = self[int, "usb_index", self.controller.usb_index]
        self.controller.usb_bus = self[int, "usb_bus", self.controller.usb_bus]
        self.controller.usb_address = self[int, "usb_address", self.controller.usb_address]
        self("units", self.units)
        self("bed_size", self.size)

    def save_config(self):
        self["autohome"] = self.autohome
        self["autobeep"] = self.autobeep
        self["autostart"] = self.autostart
        self["units-convert"] = self.units[0]
        self["units-name"] = self.units[1]
        self["units-marks"] = self.units[2]
        self["units-index"] = self.units[3]
        self["bed_width"] = self.size[0]
        self["bed_height"] = self.size[1]
        self["board"] = self.writer.board
        self["autolock"] = self.writer.autolock
        self["rotary"] = self.writer.rotary
        self["scale_x"] = self.writer.scale_x
        self["scale_y"] = self.writer.scale_y
        self["mock"] = self.controller.mock
        self["usb_index"] = self.controller.usb_index
        self["usb_bus"] = self.controller.usb_bus
        self["usb_address"] = self.controller.usb_address

    def shutdown(self):
        pass

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
        self.units = (1000, "inch", 1, 2)
        self("units", self.units)

    def set_mil(self):
        self.units = (1, "mil", 1000, 3)
        self("units", self.units)

    def set_cm(self):
        self.units = (393.7, "cm", 1, 1)
        self("units", self.units)

    def set_mm(self):
        self.units = (39.37, "mm", 10, 0)
        self("units", self.units)

    def set_selected(self, select_elements):
        if isinstance(select_elements, list):
            self.selected = select_elements
        else:
            self.selected = [select_elements]
        self.set_selected_bbox_by_selected()
        self("selection", self.selected)

    def set_selected_bbox_by_selected(self):
        boundary_points = []
        for e in self.selected:
            if isinstance(e, list):
                continue
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
            p = matrix.point_in_inverse_space(position)
            if e.contains(p):
                if e.parent is None:
                    self.set_selected(e)
                else:
                    self.set_selected(e.parent)
                break
        self("selection", self.selected)

    def bbox(self):
        boundary_points = []
        for e in self.flat_elements():
            box = e.box
            if box is None:
                continue
            top_left = e.matrix.point_in_matrix_space([box[0], box[1]])
            top_right = e.matrix.point_in_matrix_space([box[2], box[1]])
            bottom_left = e.matrix.point_in_matrix_space([box[0], box[3]])
            bottom_right = e.matrix.point_in_matrix_space([box[2], box[3]])
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
            p = matrix.point_in_inverse_space(position)
            if e.contains(p):
                self.remove_element(e)
                self.append(RawElement(e))
                break
        self("elements", 0)

    def menu_remove(self, position):
        for e in self.flat_elements():
            matrix = e.matrix
            p = matrix.point_in_inverse_space(position)
            if e.contains(p):
                self.remove_element(e)
                break
        self("elements", 0)

    def menu_scale(self, scale, scale_y=None, position=None):
        if scale_y is None:
            scale_y = scale
        if position is None:
            for s in self.selected:
                s.matrix.post_scale(scale, scale_y)
        else:
            for e in self.flat_elements():
                matrix = e.matrix
                p = matrix.point_in_inverse_space(position)
                if e.contains(p):
                    e.matrix.post_scale(scale, scale_y, p[0], p[1])
        self("elements", 0)

    def menu_rotate(self, radians, position=None):
        if position is None:
            for s in self.selected:
                s.matrix.post_rotate(radians)
        else:
            for e in self.flat_elements():
                matrix = e.matrix
                p = matrix.point_in_inverse_space(position)
                if e.contains(p):
                    e.matrix.post_rotate(radians, p[0], p[1])
        self("elements", 0)

    def move_selected(self, dx, dy):
        for e in self.selected:
            if isinstance(e, LaserElement):
                e.move(dx, dy)
        if self.selected_bbox is not None:
            self.selected_bbox[0] += dx
            self.selected_bbox[2] += dx
            self.selected_bbox[1] += dy
            self.selected_bbox[3] += dy

    def remove_element(self, obj):
        if obj in obj.parent:
            obj.parent.remove(obj)
        self("elements", 0)

    def append(self, obj):
        self.elements.append(obj)
        self("elements", 0)
