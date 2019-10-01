import wx

# TODO: Move the draw requirements of the elements outside this class so the writer can be tested without wx.
import path
import svg_parser
from K40Controller import K40Controller
from LaserCommandConstants import *
from LhymicroWriter import LhymicroWriter
from RasterPlotter import RasterPlotter, X_AXIS, TOP, BOTTOM
from ZMatrix import ZMatrix

VARIABLE_NAME_NAME = 'name'
VARIABLE_NAME_COLOR = 'color'
VARIABLE_NAME_SPEED = 'speed'
VARIABLE_NAME_POWER = 'power'
VARIABLE_NAME_PASSES = 'passes'
VARIABLE_NAME_DRATIO = 'd_ratio'
VARIABLE_NAME_RASTER_STEP = "raster_step"
VARIABLE_NAME_RASTER_DIRECTION = 'raster_direction'


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
        elif command == COMMAND_SET_POWER:
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
            y = self.y
            x += self.x
            self.graphic_path.MoveToPoint(x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_VSTEP:
            x = self.x
            y = values
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
                elif isinstance(e, path.Close):
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


class LaserNode(list):
    def __init__(self):
        list.__init__(self)
        self.cut = {}
        self.parent = None
        self.box = None
        self.bounds = None

    def __eq__(self, other):
        return other is self

    def set_color(self, color):
        self.cut[VARIABLE_NAME_COLOR] = color

    def draw(self, dc):
        pass

    def generate(self, dc):
        pass

    def append(self, obj):
        if obj.parent is not None:
            raise ValueError("Still has a parent.")
        if obj in self:
            raise ValueError("Already part of list.")
        list.append(self, obj)
        obj.parent = self
        self.notify_change()

    def remove(self, obj):
        list.remove(self, obj)
        obj.parent = None
        self.notify_change()

    def detach(self):
        if self.parent is not None:
            self.parent.remove(self)

    def notify_change(self):
        if self.parent == self:
            raise ValueError
        if self.parent is not None:
            self.parent.notify_change()

    def contains(self, x, y=None):
        if y is None:
            x, y = x
        if self.bounds is None:
            return False
        return self.bounds[0] <= x <= self.bounds[2] and self.bounds[1] <= y <= self.bounds[3]

    @property
    def center(self):
        return (self.bounds[2] - self.bounds[0]) / 2.0, (self.bounds[3] - self.bounds[1]) / 2.0


class LaserGroup(LaserNode):
    def __init__(self):
        LaserNode.__init__(self)

    def __str__(self):
        if VARIABLE_NAME_PASSES in self.cut:
            return "%d Group" % (self.cut[VARIABLE_NAME_PASSES])
        else:
            return "Group"


class LaserElement(LaserNode):
    def __init__(self):
        LaserNode.__init__(self)
        self.matrix = path.Matrix()
        self.cut = {VARIABLE_NAME_COLOR: 0, VARIABLE_NAME_SPEED: 60, VARIABLE_NAME_PASSES: 1,
                    VARIABLE_NAME_POWER: 1000.0}
        self.cache = None
        self.pen = wx.Pen()
        self.color = wx.Colour()
        self.color.SetRGB(self.cut['color'])

    def set_color(self, color):
        self.cut[VARIABLE_NAME_COLOR] = color

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
            for event in self.generate(path.Matrix()):
                parse.command(event)
            self.cache = p
        gc.StrokePath(self.cache)

    def convert_absolute_to_affinespace(self, position):
        return self.matrix.point_in_matrix_space(position)

    def convert_affinespace_to_absolute(self, position):
        return self.matrix.point_in_inverse_space(position)

    def generate(self, m=None):
        yield COMMAND_MODE_DEFAULT, 0

    def move(self, dx, dy):
        self.matrix.post_translate(dx, dy)  # Apply translate after all the other events.

    def svg_transform(self, transform_str):
        svg_parser.parse_svg_transform(transform_str, self.matrix)


class ImageElement(LaserElement):
    def __init__(self, image):
        LaserElement.__init__(self)
        self.box = [0, 0, image.width, image.height]
        self.image = image
        self.cache = None
        self.cut.update({VARIABLE_NAME_RASTER_STEP: 1,
                         VARIABLE_NAME_SPEED: 100,
                         VARIABLE_NAME_POWER: 1000.0})

    def __str__(self):
        return "%d Image %dX s@%3f" % (self.cut[VARIABLE_NAME_PASSES],
                                       self.cut[VARIABLE_NAME_RASTER_STEP],
                                       self.cut[VARIABLE_NAME_SPEED])

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

    def modulate_filter_1_bit(self, pixel):
        return (255 - pixel) / 255.0

    def modulate_filter_8_bit(self, pixel):
        return (255 - pixel) / 255.0

    def modulate_filter_palette(self, pixel):
        p = self.image.getpalette()
        v = p[pixel * 3] + p[pixel * 3 + 1] + p[pixel * 3 + 2]
        return 1.0 - v / 765.0

    def modulate_filter_rgb(self, pixel):
        return 1.0 - (pixel[0] + pixel[1] + pixel[2]) / 765.0

    def generate(self, m=None):
        if m is None:
            m = self.matrix
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
        if VARIABLE_NAME_POWER in self.cut:
            power = self.cut.get(VARIABLE_NAME_POWER)
            yield COMMAND_SET_POWER, power
        traverse = 0
        if direction == 0:
            yield COMMAND_SET_STEP, step
            traverse |= X_AXIS
            traverse |= TOP
        elif direction == 1:
            yield COMMAND_SET_STEP, step
            traverse |= X_AXIS
            traverse |= BOTTOM
        width, height = self.image.size

        mode = self.image.mode
        if mode == "1":
            image_filter = self.modulate_filter_1_bit
        elif mode == "P":
            image_filter = self.modulate_filter_palette
        elif mode == "L":
            image_filter = self.modulate_filter_8_bit
        elif mode == "RGB" or mode == "RGBA":
            image_filter = self.modulate_filter_rgb
        else:
            # Other modes we force it to become an RGB.
            self.image = self.image.convert("RGBA")
            image_filter = self.modulate_filter_rgb

        data = self.image.load()

        raster = RasterPlotter(data, width, height, traverse, 0, 0,
                               m.value_trans_x(),
                               m.value_trans_y(),
                               step, image_filter)

        yield COMMAND_RAPID_MOVE, raster.initial_position_in_scene()
        yield COMMAND_SET_DIRECTION, raster.initial_direction()
        yield COMMAND_MODE_COMPACT, 0
        yield COMMAND_RASTER, raster
        yield COMMAND_MODE_DEFAULT, 0


class TextElement(LaserElement):
    def __init__(self, text):
        LaserElement.__init__(self)
        self.text = text
        self.cut.update({VARIABLE_NAME_COLOR: 0x000000, VARIABLE_NAME_SPEED: 20, VARIABLE_NAME_POWER: 1000.0})

    def __str__(self):
        string = "NOT IMPLEMENTED: \"%s\"" % (self.text)
        if len(string) < 100:
            return string
        return string[:97] + '...'

    def draw(self, dc):
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(self.matrix)))
        if self.text is not None:
            dc.DrawText(self.text, self.matrix.value_trans_x(), self.matrix.value_trans_y())

    # def generate(self, m=None):
    #     if m is None:
    #         m = self.matrix
    #     if VARIABLE_NAME_SPEED in self.cut:
    #         speed = self.cut.get(VARIABLE_NAME_SPEED)
    #         yield COMMAND_SET_SPEED, speed
    #     if VARIABLE_NAME_POWER in self.cut:
    #         power = self.cut.get(VARIABLE_NAME_POWER)
    #         yield COMMAND_SET_POWER, power
    #     if VARIABLE_NAME_DRATIO in self.cut:
    #         d_ratio = self.cut.get(VARIABLE_NAME_DRATIO)
    #         yield COMMAND_SET_D_RATIO, d_ratio
    #     yield COMMAND_SET_STEP, 0
    #     yield COMMAND_MODE_COMPACT, 0
    #     yield COMMAND_MODE_DEFAULT, 0
    #     yield COMMAND_SET_SPEED, None
    #     yield COMMAND_SET_D_RATIO, None


class PathElement(LaserElement):
    def __init__(self, path_d):
        LaserElement.__init__(self)
        self.path = path_d
        self.cut.update({VARIABLE_NAME_COLOR: 0x00FF00, VARIABLE_NAME_SPEED: 20, VARIABLE_NAME_POWER: 1000.0})

    def __str__(self):
        string = "%d Path @%.1f mm/s %.1fx path=%s" % \
                 (self.cut[VARIABLE_NAME_PASSES], self.cut[VARIABLE_NAME_SPEED], self.matrix.value_scale_x(),
                  str(hash(self.path)))
        if len(string) < 100:
            return string
        return string[:97] + '...'

    def reify_matrix(self):
        """Apply the matrix to the path and reset matrix."""
        object_path = path.Path()
        svg_parser.parse_svg_path(object_path, self.path)
        object_path *= self.matrix
        self.path = object_path.d()
        self.matrix.reset()
        self.cache = None

    def generate(self, m=None):
        if m is None:
            m = self.matrix
        object_path = path.Path()
        svg_parser.parse_svg_path(object_path, self.path)
        self.box = object_path.bbox()
        if VARIABLE_NAME_SPEED in self.cut:
            speed = self.cut.get(VARIABLE_NAME_SPEED)
            yield COMMAND_SET_SPEED, speed
        if VARIABLE_NAME_POWER in self.cut:
            power = self.cut.get(VARIABLE_NAME_POWER)
            yield COMMAND_SET_POWER, power
        if VARIABLE_NAME_DRATIO in self.cut:
            d_ratio = self.cut.get(VARIABLE_NAME_DRATIO)
            yield COMMAND_SET_D_RATIO, d_ratio
        plot = object_path * m
        first_point = plot.first_point
        yield COMMAND_RAPID_MOVE, first_point
        yield COMMAND_SET_STEP, 0
        yield COMMAND_MODE_COMPACT, 0
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

    def generate(self, m=None):
        if m is None:
            m = self.matrix
            # Raw cannot have matrix.
        for command in self.command_list:
            yield command

    def __str__(self):
        string = "Raw #%d cmd=%s" % \
                 (len(self.command_list), str(self.command_list))
        if len(string) < 100:
            return string
        return string[:97] + '...'


class LaserProject(LaserNode):
    def __init__(self):
        LaserNode.__init__(self)
        self.listeners = {}
        self.last_message = {}
        self.elements = self
        self.size = 320, 220
        self.units = (39.37, "mm", 10, 0)
        self.config = None
        self.windows = {}

        self.selected = None
        self.thread = None
        self.autohome = False
        self.autobeep = True
        self.autostart = True
        self.mouse_zoom_invert = False
        self.controller = K40Controller(self)
        self.writer = LhymicroWriter(self, controller=self.controller)

    def __str__(self):
        return "Project"

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
        self.autohome = self[bool, "autohome"]
        self.autobeep = self[bool, "autobeep"]
        self.autostart = self[bool, "autostart"]
        self.mouse_zoom_invert = self[bool, "mouse_zoom_invert"]
        convert = self[float, "units-convert", self.units[0]]
        name = self[str, "units-name", self.units[1]]
        marks = self[int, "units-marks", self.units[2]]
        unitindex = self[int, "units-index", self.units[3]]
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
        self["autohome"] = bool(self.autohome)
        self["autobeep"] = bool(self.autobeep)
        self["autostart"] = bool(self.autostart)
        self["mouse_zoom_invert"] = bool(self.mouse_zoom_invert)
        self["units-convert"] = float(self.units[0])
        self["units-name"] = str(self.units[1])
        self["units-marks"] = int(self.units[2])
        self["units-index"] = int(self.units[3])
        self["bed_width"] = int(self.size[0])
        self["bed_height"] = int(self.size[1])
        self["board"] = str(self.writer.board)
        self["autolock"] = bool(self.writer.autolock)
        self["rotary"] = bool(self.writer.rotary)
        self["scale_x"] = float(self.writer.scale_x)
        self["scale_y"] = float(self.writer.scale_y)
        self["mock"] = bool(self.controller.mock)
        self["usb_index"] = int(self.controller.usb_index)
        self["usb_bus"] = int(self.controller.usb_bus)
        self["usb_address"] = int(self.controller.usb_address)

    def close_old_window(self, name):
        if name in self.windows:
            old_window = self.windows[name]
            try:
                old_window.Close()
            except RuntimeError:
                pass  # already closed.

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

    def validate_matrix(self, node):
        if isinstance(node, ImageElement):
            tx = node.matrix.value_trans_x()
            ty = node.matrix.value_trans_y()
            node.matrix.reset()
            node.matrix.post_translate(tx, ty)
            if VARIABLE_NAME_RASTER_STEP in node.cut:
                step = float(node.cut[VARIABLE_NAME_RASTER_STEP])
                node.matrix.pre_scale(step, step)

    def validate(self, node=None):
        if node is None:
            # Default call.
            node = self

        node.bounds = None  # delete bounds
        for element in node:
            self.validate(element)  # validate all subelements.
        self.validate_matrix(node)
        if len(node) == 0:  # Leaf Node.
            node.bounds = node.box
            if isinstance(node, LaserElement):
                # Perform matrix conversion of box into bounds.
                boundary_points = []
                box = node.box
                if box is None:
                    return
                left_top = node.convert_absolute_to_affinespace([box[0], box[1]])
                right_top = node.convert_absolute_to_affinespace([box[2], box[1]])
                left_bottom = node.convert_absolute_to_affinespace([box[0], box[3]])
                right_bottom = node.convert_absolute_to_affinespace([box[2], box[3]])
                boundary_points.append(left_top)
                boundary_points.append(right_top)
                boundary_points.append(left_bottom)
                boundary_points.append(right_bottom)
                xmin = min([e[0] for e in boundary_points])
                ymin = min([e[1] for e in boundary_points])
                xmax = max([e[0] for e in boundary_points])
                ymax = max([e[1] for e in boundary_points])
                node.bounds = [xmin, ymin, xmax, ymax]
            return

        # Group node.
        xvals = []
        yvals = []
        for e in node:
            bounds = e.bounds
            if bounds is None:
                continue
            xvals.append(bounds[0])
            xvals.append(bounds[2])
            yvals.append(bounds[1])
            yvals.append(bounds[3])
        if len(xvals) == 0:
            return
        node.bounds = [min(xvals), min(yvals), max(xvals), max(yvals)]

    def flat_elements_with_passes(self, elements=None, types=LaserElement):
        if elements is None:
            elements = self.elements
        passes = 1
        if VARIABLE_NAME_PASSES in elements.cut:
            passes = elements.cut[VARIABLE_NAME_PASSES]
        if isinstance(elements, types):
            for q in range(0, passes):
                yield elements
        for element in elements:
            for q in range(0, passes):
                for flat_element in self.flat_elements_with_passes(element, types=types):
                    yield flat_element

    @staticmethod
    def flatten(elements, types=LaserElement):
        if isinstance(elements, types):
            yield elements
        for element in elements:
            for flat_element in LaserProject.flatten(element, types=types):
                yield flat_element

    def flat_elements(self, elements=None, types=(LaserElement)):
        if elements is None:
            elements = self.elements
        for element in elements:
            element.parent = elements
            if isinstance(element, types):
                yield element
            for flat_element in self.flat_elements(element, types=types):
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

    def set_selected(self, selected):
        self.selected = selected
        self("selection", self.selected)

    def set_selected_by_position(self, position):
        self.selected = None
        self.validate()
        for e in self.flat_elements(types=LaserGroup):
            bounds = e.bounds
            if bounds is None:
                continue
            if e.contains(position):
                self.set_selected(e)
                break

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

    def notify_change(self):
        self("elements", 0)

    def menu_convert_raw(self, position):
        self.validate()
        self.set_selected_by_position(position)
        if self.selected is not None:
            for e in self.selected:
                e.detach()
                self.append(RawElement(e))

    def menu_remove(self, position):
        self.validate()
        self.set_selected_by_position(position)
        if self.selected is not None:
            self.selected.detach()

    def menu_scale(self, scale, scale_y=None, position=None):
        if scale_y is None:
            scale_y = scale
        self.validate()
        if position is not None:
            self.set_selected_by_position(position)
        if self.selected is not None:
            for e in self.selected:
                if isinstance(e, PathElement):
                    if position is not None:
                        e.matrix.post_scale(scale, scale_y, position[0], position[1])
                    else:
                        e.matrix.post_scale(scale, scale_y)
        self("elements", 0)

    def menu_rotate(self, radians, position=None):
        self.validate()
        if position is not None:
            self.set_selected_by_position(position)
        else:
            position = self.center
        if self.selected is not None:
            self.validate()
            for e in self.selected:
                if isinstance(e, PathElement):
                    p = position
                    e.matrix.post_rotate(radians, position[0], position[1])
        self("elements", 0)

    def move_selected(self, dx, dy):
        if self.selected is None:
            return
        for e in self.selected:
            if isinstance(e, LaserElement):
                e.move(dx, dy)
        if self.selected is not None and self.selected.bounds is not None:
            self.selected.bounds[0] += dx
            self.selected.bounds[2] += dx
            self.selected.bounds[1] += dy
            self.selected.bounds[3] += dy
