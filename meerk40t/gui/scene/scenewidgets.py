from meerk40t.gui.scene.scene import Widget

try:
    from math import tau
except ImportError:
    from math import pi

    tau = 2 * pi

import wx

from meerk40t.gui.laserrender import (
    DRAW_MODE_BACKGROUND,
    DRAW_MODE_GRID,
    DRAW_MODE_GUIDES,
    DRAW_MODE_LASERPATH,
    DRAW_MODE_RETICLE,
    DRAW_MODE_SELECTION,
    swizzlecolor,
)
from meerk40t.svgelements import Color

MILS_IN_MM = 39.3701

HITCHAIN_HIT = 0
HITCHAIN_DELEGATE = 1
HITCHAIN_HIT_AND_DELEGATE = 2
HITCHAIN_DELEGATE_AND_HIT = 3

RESPONSE_CONSUME = 0
RESPONSE_ABORT = 1
RESPONSE_CHAIN = 2
RESPONSE_DROP = 3

ORIENTATION_MODE_MASK = 0b00001111110000
ORIENTATION_DIM_MASK = 0b00000000001111
ORIENTATION_MASK = ORIENTATION_MODE_MASK | ORIENTATION_DIM_MASK
ORIENTATION_RELATIVE = 0b00000000000000
ORIENTATION_ABSOLUTE = 0b00000000010000
ORIENTATION_CENTERED = 0b00000000100000
ORIENTATION_HORIZONTAL = 0b00000001000000
ORIENTATION_VERTICAL = 0b00000010000000
ORIENTATION_GRID = 0b00000100000000
ORIENTATION_NO_BUFFER = 0b00001000000000
BUFFER = 10.0


class ElementsWidget(Widget):
    def __init__(self, scene, root, renderer):
        Widget.__init__(self, scene, all=True)
        self.renderer = renderer
        self.root = root

    def hit(self):
        return HITCHAIN_HIT

    def process_draw(self, gc):
        context = self.scene.context
        zoom_scale = 1 / self.scene.widget_root.scene_widget.matrix.value_scale_x()
        if zoom_scale < 1:
            zoom_scale = 1
        self.renderer.render(
            context.elements.elems_nodes(),
            gc,
            self.renderer.context.draw_mode,
            zoomscale=zoom_scale,
        )

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "leftclick":
            elements = self.scene.context.elements
            elements.set_emphasized_by_position(space_pos)
            self.root.select_in_tree_by_emphasis()
            return RESPONSE_CONSUME
        return RESPONSE_DROP


class SelectionWidget(Widget):
    def __init__(self, scene, root):
        Widget.__init__(self, scene, all=False)
        self.root = root
        self.elements = scene.context.elements
        self.selection_pen = wx.Pen()
        self.selection_pen.SetColour(wx.Colour(0xA0, 0x7F, 0xA0))
        self.selection_pen.SetStyle(wx.PENSTYLE_DOT)
        self.save_width = None
        self.save_height = None
        self.tool = self.tool_translate
        self.cursor = None
        self.uniform = True

    def hit(self):
        elements = self.elements
        bounds = elements.selected_area()
        if bounds is not None:
            self.left = bounds[0]
            self.top = bounds[1]
            self.right = bounds[2]
            self.bottom = bounds[3]
            self.clear()
            self.scene.context.signal("refresh_scene", 0)
            return HITCHAIN_HIT
        else:
            self.left = float("inf")
            self.top = float("inf")
            self.right = -float("inf")
            self.bottom = -float("inf")
            self.clear()
            self.scene.context.signal("refresh_scene", 0)
            return HITCHAIN_DELEGATE

    def event(self, window_pos=None, space_pos=None, event_type=None):
        elements = self.elements
        if event_type == "hover_start":
            self.cursor = wx.CURSOR_SIZING
            self.scene.context.gui.SetCursor(wx.Cursor(self.cursor))
            return RESPONSE_CHAIN
        if event_type == "hover_end":
            self.cursor = wx.CURSOR_ARROW
            self.scene.context.gui.SetCursor(wx.Cursor(self.cursor))
            return RESPONSE_CHAIN
        if event_type == "hover":
            matrix = self.parent.matrix
            xin = space_pos[0] - self.left
            yin = space_pos[1] - self.top
            xmin = 5 / matrix.value_scale_x()
            ymin = 5 / matrix.value_scale_x()
            xmax = self.width - xmin
            ymax = self.height - ymin
            self.tool = self.tool_translate
            cursor = self.cursor
            self.cursor = wx.CURSOR_SIZING
            first = elements.first_element(emphasized=True)
            try:
                if first.lock:
                    if self.cursor != cursor:
                        self.scene.context.gui.SetCursor(wx.Cursor(self.cursor))
                        self.scene.context.gui.SetCursor(wx.Cursor(self.cursor))
                    return RESPONSE_CHAIN
            except (ValueError, AttributeError):
                pass
            if xin <= xmin:
                self.cursor = wx.CURSOR_SIZEWE
                self.tool = self.tool_scalex_w
            if yin <= ymin:
                self.cursor = wx.CURSOR_SIZENS
                self.tool = self.tool_scaley_n
            if xin >= xmax:
                self.cursor = wx.CURSOR_SIZEWE
                self.tool = self.tool_scalex_e
            if yin >= ymax:
                self.cursor = wx.CURSOR_SIZENS
                self.tool = self.tool_scaley_s
            if xin >= xmax and yin >= ymax:
                self.cursor = wx.CURSOR_SIZENWSE
                self.tool = self.tool_scalexy_se
            if xin <= xmin and yin <= ymin:
                self.cursor = wx.CURSOR_SIZENWSE
                self.tool = self.tool_scalexy_nw
            if xin >= xmax and yin <= ymin:
                self.cursor = wx.CURSOR_SIZENESW
                self.tool = self.tool_scalexy_ne
            if xin <= xmin and yin >= ymax:
                self.cursor = wx.CURSOR_SIZENESW
                self.tool = self.tool_scalexy_sw
            if self.cursor != cursor:
                self.scene.context.gui.SetCursor(wx.Cursor(self.cursor))
            return RESPONSE_CHAIN
        dx = space_pos[4]
        dy = space_pos[5]

        if event_type == "rightdown":
            elements.set_emphasized_by_position(space_pos)
            if not elements.has_emphasis():
                return RESPONSE_CONSUME
            self.root.create_menu(
                self.scene.context.gui, elements.first_element(emphasized=True)
            )
            return RESPONSE_CONSUME
        if event_type == "doubleclick":
            elements.set_emphasized_by_position(space_pos)
            self.root.activate_selected_node()
            return RESPONSE_CONSUME
        if event_type == "leftdown":
            self.save_width = self.width
            self.save_height = self.height
            self.uniform = True
            return RESPONSE_CONSUME
        if event_type == "middledown":
            self.save_width = self.width
            self.save_height = self.height
            self.uniform = False
            return RESPONSE_CONSUME
        if event_type in ("middleup", "leftup"):
            self.elements.ensure_positive_bounds()
            return RESPONSE_CONSUME
        if event_type == "move":
            if not elements.has_emphasis():
                return RESPONSE_CONSUME
            if self.save_width is None or self.save_height is None:
                self.save_width = self.width
                self.save_height = self.height
            self.tool(space_pos, dx, dy)
            return RESPONSE_CONSUME
        return RESPONSE_CHAIN

    def tool_scalexy(self, position, dx, dy):
        elements = self.scene.context.elements
        b = elements.selected_area()
        scalex = (position[0] - self.left) / self.save_width
        scaley = (position[1] - self.top) / self.save_height
        self.save_width *= scalex
        self.save_height *= scaley
        for obj in elements.elems(emphasized=True):
            try:
                if obj.lock:
                    continue
            except AttributeError:
                pass
            obj.transform.post_scale(scalex, scaley, self.left, self.top)
            obj.node.modified()
        elements.update_bounds([b[0], b[1], position[0], position[1]])
        self.scene.context.signal("refresh_scene", 0)

    def tool_scalexy_se(self, position, dx, dy):
        elements = self.scene.context.elements
        b = elements.selected_area()
        scalex = (position[0] - self.left) / self.save_width
        scaley = (position[1] - self.top) / self.save_height
        if self.uniform:
            scale = (scaley + scalex) / 2.0
            scalex = scale
            scaley = scale
        self.save_width *= scalex
        self.save_height *= scaley
        for obj in elements.elems(emphasized=True):
            try:
                if obj.lock:
                    continue
            except AttributeError:
                pass
            obj.transform.post_scale(scalex, scaley, self.left, self.top)
            obj.node.modified()
        elements.update_bounds(
            [b[0], b[1], b[0] + self.save_width, b[1] + self.save_height]
        )
        self.scene.context.signal("refresh_scene", 0)

    def tool_scalexy_nw(self, position, dx, dy):
        elements = self.scene.context.elements
        b = elements.selected_area()
        scalex = (self.right - position[0]) / self.save_width
        scaley = (self.bottom - position[1]) / self.save_height
        if self.uniform:
            scale = (scaley + scalex) / 2.0
            scalex = scale
            scaley = scale
        self.save_width *= scalex
        self.save_height *= scaley
        for obj in elements.elems(emphasized=True):
            try:
                if obj.lock:
                    continue
            except AttributeError:
                pass
            obj.transform.post_scale(scalex, scaley, self.right, self.bottom)
            obj.node.modified()
        elements.update_bounds(
            [b[2] - self.save_width, b[3] - self.save_height, b[2], b[3]]
        )
        self.scene.context.signal("refresh_scene", 0)

    def tool_scalexy_ne(self, position, dx, dy):
        elements = self.scene.context.elements
        b = elements.selected_area()
        scalex = (position[0] - self.left) / self.save_width
        scaley = (self.bottom - position[1]) / self.save_height
        if self.uniform:
            scale = (scaley + scalex) / 2.0
            scalex = scale
            scaley = scale
        self.save_width *= scalex
        self.save_height *= scaley
        for obj in elements.elems(emphasized=True):
            try:
                if obj.lock:
                    continue
            except AttributeError:
                pass
            obj.transform.post_scale(scalex, scaley, self.left, self.bottom)
            obj.node.modified()
        elements.update_bounds(
            [b[0], b[3] - self.save_height, b[0] + self.save_width, b[3]]
        )
        self.scene.context.signal("refresh_scene", 0)

    def tool_scalexy_sw(self, position, dx, dy):
        elements = self.scene.context.elements
        b = elements.selected_area()
        scalex = (self.right - position[0]) / self.save_width
        scaley = (position[1] - self.top) / self.save_height
        if self.uniform:
            scale = (scaley + scalex) / 2.0
            scalex = scale
            scaley = scale
        self.save_width *= scalex
        self.save_height *= scaley
        for obj in elements.elems(emphasized=True):
            try:
                if obj.lock:
                    continue
            except AttributeError:
                pass
            obj.transform.post_scale(scalex, scaley, self.right, self.top)
            obj.node.modified()
        elements.update_bounds(
            [b[2] - self.save_width, b[1], b[2], b[1] + self.save_height]
        )
        self.scene.context.signal("refresh_scene", 0)

    def tool_scalex_e(self, position, dx, dy):
        elements = self.scene.context.elements
        b = elements.selected_area()
        scalex = (position[0] - self.left) / self.save_width
        self.save_width *= scalex
        for obj in elements.elems(emphasized=True):
            try:
                if obj.lock:
                    continue
            except AttributeError:
                pass
            obj.transform.post_scale(scalex, 1, self.left, self.top)
            obj.node.modified()
        elements.update_bounds([b[0], b[1], position[0], b[3]])
        self.scene.context.signal("refresh_scene", 0)

    def tool_scalex_w(self, position, dx, dy):
        elements = self.scene.context.elements
        b = elements.selected_area()
        scalex = (self.right - position[0]) / self.save_width
        self.save_width *= scalex
        for obj in elements.elems(emphasized=True):
            try:
                if obj.lock:
                    continue
            except AttributeError:
                pass
            obj.transform.post_scale(scalex, 1, self.right, self.top)
            obj.node.modified()
        elements.update_bounds([position[0], b[1], b[2], b[3]])
        self.scene.context.signal("refresh_scene", 0)

    def tool_scaley_s(self, position, dx, dy):
        elements = self.scene.context.elements
        b = elements.selected_area()
        scaley = (position[1] - self.top) / self.save_height
        self.save_height *= scaley
        for obj in elements.elems(emphasized=True):
            try:
                if obj.lock:
                    continue
            except AttributeError:
                pass
            obj.transform.post_scale(1, scaley, self.left, self.top)
            obj.node.modified()

        elements.update_bounds([b[0], b[1], b[2], position[1]])
        self.scene.context.signal("refresh_scene", 0)

    def tool_scaley_n(self, position, dx, dy):
        elements = self.scene.context.elements
        b = elements.selected_area()
        scaley = (self.bottom - position[1]) / self.save_height
        self.save_height *= scaley
        for obj in elements.elems(emphasized=True):
            try:
                if obj.lock:
                    continue
            except AttributeError:
                pass
            obj.transform.post_scale(1, scaley, self.left, self.bottom)
            obj.node.modified()
        elements.update_bounds([b[0], position[1], b[2], b[3]])
        self.scene.context.signal("refresh_scene", 0)

    def tool_translate(self, position, dx, dy):
        elements = self.scene.context.elements
        b = elements.selected_area()
        for e in elements.flat(types=("elem",), emphasized=True):
            obj = e.object
            obj.transform.post_translate(dx, dy)
            obj.node.modified()
        for e in elements.flat(types=("group", "file", "op element"), emphasized=True):
            e._bounds_dirty = True
        self.translate(dx, dy)
        elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])
        self.scene.context.signal("refresh_scene", 0)

    def process_draw(self, gc):
        if self.scene.context.draw_mode & DRAW_MODE_SELECTION != 0:
            return
        context = self.scene.context
        draw_mode = context.draw_mode
        elements = self.scene.context.elements
        bounds = elements.selected_area()
        matrix = self.parent.matrix
        if bounds is not None:
            linewidth = 2.0 / matrix.value_scale_x()
            self.selection_pen.SetWidth(linewidth)
            font_size = 14.0 / matrix.value_scale_x()
            if font_size < 1.0:
                font_size = 1.0  # Mac does not allow values lower than 1.
            font = wx.Font(font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
            gc.SetFont(font, wx.Colour(0x7F, 0x7F, 0x7F))
            gc.SetPen(self.selection_pen)
            x0, y0, x1, y1 = bounds
            center_x = (x0 + x1) / 2.0
            center_y = (y0 + y1) / 2.0
            gc.StrokeLine(center_x, 0, center_x, y0)
            gc.StrokeLine(0, center_y, x0, center_y)
            gc.StrokeLine(x0, y0, x1, y0)
            gc.StrokeLine(x1, y0, x1, y1)
            gc.StrokeLine(x1, y1, x0, y1)
            gc.StrokeLine(x0, y1, x0, y0)
            if draw_mode & DRAW_MODE_SELECTION == 0:
                p = self.scene.context
                conversion, name, marks, index = (
                    p.units_convert,
                    p.units_name,
                    p.units_marks,
                    p.units_index,
                )
                gc.DrawText("%.1f%s" % (y0 / conversion, name), center_x, y0 / 2.0)
                gc.DrawText("%.1f%s" % (x0 / conversion, name), x0 / 2.0, center_y)
                gc.DrawText("%.1f%s" % ((y1 - y0) / conversion, name), x1, center_y)
                gc.DrawText("%.1f%s" % ((x1 - x0) / conversion, name), center_x, y1)


class RectSelectWidget(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.selection_pen = wx.Pen()
        self.selection_pen.SetColour(wx.BLUE)
        self.selection_pen.SetWidth(25)
        self.selection_pen.SetStyle(wx.PENSTYLE_SHORT_DASH)
        self.start_location = None
        self.end_location = None

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        elements = self.scene.context.elements
        if event_type == "leftdown":
            self.start_location = space_pos
            self.end_location = space_pos
            return RESPONSE_CONSUME
        elif event_type == "leftclick":
            self.start_location = None
            self.end_location = None
            return RESPONSE_DROP
        elif event_type == "leftup":
            elements.validate_selected_area()
            for obj in elements.elems():
                try:
                    q = obj.bbox(True)
                except AttributeError:
                    continue  # This element has no bounds.
                if q is None:
                    continue
                sx = self.start_location[0]
                sy = self.start_location[1]
                ex = self.end_location[0]
                ey = self.end_location[1]
                right_drag = sx <= ex and sy <= ey
                sx = min(self.start_location[0], self.end_location[0])
                sy = min(self.start_location[1], self.end_location[1])
                ex = max(self.start_location[0], self.end_location[0])
                ey = max(self.start_location[1], self.end_location[1])
                xmin = q[0]
                ymin = q[1]
                xmax = q[2]
                ymax = q[3]
                if right_drag:
                    if (
                        sx <= xmin <= ex
                        and sy <= ymin <= ey
                        and sx <= xmax <= ex
                        and sy <= ymax <= ey
                    ):
                        obj.node.emphasized = True
                    else:
                        obj.node.emphasized = False
                else:
                    if (sx <= xmin <= ex or sx <= xmax <= ex) and (
                        sy <= ymin <= ey or sy <= ymax <= ey
                    ):
                        obj.node.emphasized = True
                    else:
                        obj.node.emphasized = False
            self.scene.context.signal("refresh_scene", 0)
            self.start_location = None
            self.end_location = None
            return RESPONSE_CONSUME
        elif event_type == "move":
            self.scene.context.signal("refresh_scene", 0)
            self.end_location = space_pos
            return RESPONSE_CONSUME
        return RESPONSE_DROP

    def process_draw(self, gc):
        matrix = self.parent.matrix
        if self.start_location is not None and self.end_location is not None:
            x0 = self.start_location[0]
            y0 = self.start_location[1]
            x1 = self.end_location[0]
            y1 = self.end_location[1]
            linewidth = 3.0 / matrix.value_scale_x()
            self.selection_pen.SetWidth(linewidth)
            gc.SetPen(self.selection_pen)
            gc.StrokeLine(x0, y0, x1, y0)
            gc.StrokeLine(x1, y0, x1, y1)
            gc.StrokeLine(x1, y1, x0, y1)
            gc.StrokeLine(x0, y1, x0, y0)


class ReticleWidget(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.reticles = {}
        self.pen = wx.Pen()

    def init(self, context):
        context.listen("driver;position", self.on_update_driver)
        context.listen("emulator;position", self.on_update_emulator)

    def final(self, context):
        context.unlisten("driver;position", self.on_update_driver)
        context.unlisten("emulator;position", self.on_update_emulator)

    def on_update_driver(self, origin, pos):
        self.reticles["d" + origin] = pos[2], pos[3]
        # self.request_refresh_for_animation()

    def on_update_emulator(self, origin, pos):
        self.reticles["e" + origin] = pos[2], pos[3]

    def process_draw(self, gc):
        context = self.scene.context
        try:
            if context.draw_mode & DRAW_MODE_RETICLE == 0:
                # Draw Reticles
                gc.SetBrush(wx.TRANSPARENT_BRUSH)
                for index, ret in enumerate(self.reticles):
                    r = self.reticles[ret]
                    self.pen.SetColour(Color.distinct(index + 2).hex)
                    gc.SetPen(self.pen)
                    x = r[0]
                    y = r[1]
                    if x is None or y is None:
                        x = 0
                        y = 0
                    x, y = self.scene.convert_scene_to_window([x, y])
                    gc.DrawEllipse(x - 5, y - 5, 10, 10)
        except AttributeError:
            pass


class LaserPathWidget(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.laserpath = [[0, 0]] * 1000, [[0, 0]] * 1000
        self.laserpath_index = 0

    def init(self, context):
        context.listen("driver;position", self.on_update)
        context.listen("emulator;position", self.on_update)

    def final(self, context):
        context.unlisten("driver;position", self.on_update)
        context.unlisten("emulator;position", self.on_update)

    def on_update(self, origin, pos):
        laserpath = self.laserpath
        index = self.laserpath_index
        laserpath[0][index][0] = pos[0]
        laserpath[0][index][1] = pos[1]
        laserpath[1][index][0] = pos[2]
        laserpath[1][index][1] = pos[3]
        index += 1
        index %= len(laserpath[0])
        self.laserpath_index = index

    def clear_laserpath(self):
        self.laserpath = [[0, 0]] * 1000, [[0, 0]] * 1000
        self.laserpath_index = 0

    def process_draw(self, gc):
        context = self.scene.context
        if context.draw_mode & DRAW_MODE_LASERPATH == 0:
            gc.SetPen(wx.BLUE_PEN)
            starts, ends = self.laserpath
            try:
                gc.StrokeLineSegments(starts, ends)
            except OverflowError:
                pass  # I don't actually know why this would happen.


class GridWidget(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.grid = None
        self.background = None
        self.grid_line_pen = wx.Pen()
        self.grid_line_pen.SetColour(wx.Colour(0xA0, 0xA0, 0xA0))
        self.grid_line_pen.SetWidth(1)

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "hover":
            return RESPONSE_CHAIN
        elif event_type == "doubleclick":
            menu = wx.Menu()
            _ = self.scene.context._
            if self.background is not None:
                item = menu.Append(wx.ID_ANY, _("Remove Background"), "")
                self.scene.gui.Bind(wx.EVT_MENU, lambda e: self.scene.gui.signal("background", None), id=item.GetId())
                if menu.MenuItemCount != 0:
                    self.scene.gui.PopupMenu(menu)
                    menu.Destroy()
        self.grid = None
        return RESPONSE_CHAIN

    def calculate_grid(self):
        if self.scene.context is not None:
            context = self.scene.context
            bed_dim = context.root
            wmils = bed_dim.bed_width * MILS_IN_MM
            hmils = bed_dim.bed_height * MILS_IN_MM
        else:
            wmils = 310 * MILS_IN_MM
            hmils = 210 * MILS_IN_MM

        kernel_root = self.scene.context.root
        convert = kernel_root.units_convert
        marks = kernel_root.units_marks
        step = convert * marks
        starts = []
        ends = []
        if step == 0:
            self.grid = None
            return starts, ends
        x = 0.0
        while x < wmils:
            starts.append((x, 0))
            ends.append((x, hmils))
            x += step
        y = 0.0
        while y < hmils:
            starts.append((0, y))
            ends.append((wmils, y))
            y += step
        self.grid = starts, ends

    def process_draw(self, gc):
        if self.scene.context.draw_mode & DRAW_MODE_BACKGROUND == 0:
            context = self.scene.context
            if context is not None:
                bed_dim = context.root
                wmils = bed_dim.bed_width * MILS_IN_MM
                hmils = bed_dim.bed_height * MILS_IN_MM
            else:
                wmils = 320 * MILS_IN_MM
                hmils = 210 * MILS_IN_MM
            background = self.background
            if background is None:
                gc.SetBrush(wx.WHITE_BRUSH)
                gc.DrawRectangle(0, 0, wmils, hmils)
            elif isinstance(background, int):
                gc.SetBrush(wx.Brush(wx.Colour(swizzlecolor(background))))
                gc.DrawRectangle(0, 0, wmils, hmils)
            else:
                gc.DrawBitmap(background, 0, 0, wmils, hmils)

        if self.scene.context.draw_mode & DRAW_MODE_GRID == 0:
            if self.grid is None:
                self.calculate_grid()
            starts, ends = self.grid
            try:
                line_width = (
                    1 / self.scene.widget_root.scene_widget.matrix.value_scale_x()
                )
                if line_width < 1:
                    line_width = 1
                self.grid_line_pen.SetWidth(line_width)
                gc.SetPen(self.grid_line_pen)
                gc.StrokeLineSegments(starts, ends)
            except OverflowError:
                self.scene.widget_root.scene_widget.matrix.reset()

    def signal(self, signal, *args, **kwargs):
        if signal == "grid":
            self.grid = None
        elif signal == "background":
            self.background = args[0]


class GuideWidget(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.scene.context.setting(bool, "show_negative_guide", True)

    def process_draw(self, gc):
        if self.scene.context.draw_mode & DRAW_MODE_GUIDES != 0:
            return
        gc.SetPen(wx.BLACK_PEN)
        w, h = gc.Size
        p = self.scene.context
        scaled_conversion = (
            p.units_convert * self.scene.widget_root.scene_widget.matrix.value_scale_x()
        )
        if scaled_conversion == 0:
            return
        edge_gap = 5
        wpoints = w / 15.0
        hpoints = h / 15.0
        points = min(wpoints, hpoints)
        # tweak the scaled points into being useful.
        # points = scaled_conversion * round(points / scaled_conversion * 10.0) / 10.0
        points = scaled_conversion * float("{:.1g}".format(points / scaled_conversion))
        sx, sy = self.scene.convert_scene_to_window([0, 0])
        if points == 0:
            return
        offset_x = sx % points
        offset_y = sy % points

        starts = []
        ends = []
        x = offset_x
        length = 20
        font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        gc.SetFont(font, wx.BLACK)
        gc.DrawText(p.units_name, edge_gap, edge_gap)
        while x < w:
            if x >= 45:
                mark_point = (x - sx) / scaled_conversion
                if round(mark_point * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                if mark_point >= 0 or p.show_negative_guide:
                    starts.append((x, edge_gap))
                    ends.append((x, length + edge_gap))

                    starts.append((x, h - edge_gap))
                    ends.append((x, h - length - edge_gap))

                    # gc.DrawText("%g %s" % (mark_point, p.units_name), x, 0, -tau / 4)
                    gc.DrawText("%g" % mark_point, x, edge_gap, -tau / 4)
            x += points

        y = offset_y
        while y < h:
            if y >= 20:
                mark_point = (y - sy) / scaled_conversion
                if round(mark_point * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                if mark_point >= 0 or p.show_negative_guide:
                    starts.append((edge_gap, y))
                    ends.append((length + edge_gap, y))

                    starts.append((w - edge_gap, y))
                    ends.append((w - length - edge_gap, y))

                    # gc.DrawText("%g %s" % (mark_point + 0, p.units_name), 0, y + 0)
                    gc.DrawText("%g" % (mark_point + 0), edge_gap, y + 0)
            y += points
        if len(starts) > 0:
            gc.StrokeLineSegments(starts, ends)

    def signal(self, signal, *args, **kwargs):
        if signal == "guide":
            pass
