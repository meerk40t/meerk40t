from K40Controller import K40Controller
from LhymicroWriter import LhymicroWriter
from ProjectNodes import *
import wx


class LaserProject:
    def __init__(self):
        self.listeners = {}
        self.last_message = {}
        self.elements = ProjectRoot()
        self.elements.parent = self
        self.size = 320, 220
        self.units = (39.37, "mm", 10, 0)
        self.config = None
        self.windows = {}
        self.draw_mode = 0
        self.window_width = 600
        self.window_height = 600

        self.selected = None
        self.autohome = False
        self.autobeep = True
        self.autostart = True
        self.mouse_zoom_invert = False
        self.keymap = {}
        self.properties = {
            0xFF0000: {
                VARIABLE_NAME_COLOR: 0xFF0000,
                VARIABLE_NAME_FILL_COLOR: 0xFF0000,
                VARIABLE_NAME_SPEED: 10,
                VARIABLE_NAME_PASSES: 1,
                VARIABLE_NAME_POWER: 1000.0},
            0x00FF00: {
                VARIABLE_NAME_COLOR: 0x00FF00,
                VARIABLE_NAME_FILL_COLOR: 0x00FF00,
                VARIABLE_NAME_SPEED: 30,
                VARIABLE_NAME_PASSES: 1,
                VARIABLE_NAME_POWER: 1000.0},
            0x0000FF: {
                VARIABLE_NAME_COLOR: 0x0000FF,
                VARIABLE_NAME_FILL_COLOR: 0x0000FF,
                VARIABLE_NAME_SPEED: 40,
                VARIABLE_NAME_PASSES: 1,
                VARIABLE_NAME_POWER: 1000.0},
            0xFFFF00: {
                VARIABLE_NAME_COLOR: 0xFFFF00,
                VARIABLE_NAME_FILL_COLOR: 0xFFFF00,
                VARIABLE_NAME_SPEED: 15,
                VARIABLE_NAME_PASSES: 2,
                VARIABLE_NAME_POWER: 500.0},
            0xFF00FF: {
                VARIABLE_NAME_COLOR: 0xFF00FF,
                VARIABLE_NAME_FILL_COLOR: 0xFF00FF,
                VARIABLE_NAME_SPEED: 35,
                VARIABLE_NAME_PASSES: 1,
                VARIABLE_NAME_POWER: 800.0},
            0x00FFFF: {
                VARIABLE_NAME_COLOR: 0x00FFFF,
                VARIABLE_NAME_FILL_COLOR: 0x00FFFF,
                VARIABLE_NAME_SPEED: 6,
                VARIABLE_NAME_PASSES: 4,
                VARIABLE_NAME_POWER: 1000.0},
            "Raster": {
                VARIABLE_NAME_COLOR: 0x000000,
                VARIABLE_NAME_FILL_COLOR: 0x000000,
                VARIABLE_NAME_SPEED: 80,
                VARIABLE_NAME_PASSES: 1,
                VARIABLE_NAME_POWER: 1000.0
            },
            "Vector": {
                VARIABLE_NAME_COLOR: 0x000000,
                VARIABLE_NAME_FILL_COLOR: 0x000000,
                VARIABLE_NAME_SPEED: 20,
                VARIABLE_NAME_PASSES: 1,
                VARIABLE_NAME_POWER: 1000.0
            },
            None: {
                VARIABLE_NAME_COLOR: 0x000000,
                VARIABLE_NAME_FILL_COLOR: 0x000000,
                VARIABLE_NAME_SPEED: 20,
                VARIABLE_NAME_PASSES: 1,
                VARIABLE_NAME_POWER: 1000.0,
                VARIABLE_NAME_NAME: '',
                VARIABLE_NAME_DRATIO: 0.271,
                VARIABLE_NAME_RASTER_STEP: 1,
                VARIABLE_NAME_RASTER_DIRECTION: 0
            }
        }
        self.controller = K40Controller(self)
        self.writer = LhymicroWriter(self, controller=self.controller)

    def __str__(self):
        return "Project"

    def __call__(self, code, message):
        if code in self.listeners:
            listeners = self.listeners[code]
            for listener in listeners:
                wx.CallAfter(listener,message)
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
        self.properties = eval(self[str, "properties", repr(self.properties)])
        self.window_width = self[int, "window_width", self.window_width]  # TODO: hookup, so window size stays.
        self.window_height = self[int, "window_height", self.window_height]
        self.draw_mode = self[int, "mode", self.draw_mode]
        self.autohome = self[bool, "autohome", self.autobeep]
        self.autobeep = self[bool, "autobeep", self.autobeep]
        self.autostart = self[bool, "autostart", self.autostart]
        self.mouse_zoom_invert = self[bool, "mouse_zoom_invert", self.mouse_zoom_invert]
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
        self["properties"] = repr(self.properties)
        self["window_width"] = int(self.window_width)
        self["window_height"] = int(self.window_height)
        self["mode"] = int(self.draw_mode)
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
            if VARIABLE_NAME_RASTER_STEP in node.properties:
                step = float(node.properties[VARIABLE_NAME_RASTER_STEP])
                node.matrix.pre_scale(step, step)

    def validate(self, node=None):
        if node is None:
            # Default call.
            node = self.elements

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
        for e in self.elements.flat_elements(types=LaserGroup):
            bounds = e.bounds
            if bounds is None:
                continue
            if e.contains(position):
                self.set_selected(e)
                break

    def bbox(self):
        boundary_points = []
        for e in self.elements.flat_elements(LaserNode):
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
