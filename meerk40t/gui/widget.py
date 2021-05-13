import time

try:
    from math import tau
except ImportError:
    from math import pi

    tau = 2 * pi

import wx

from ..kernel import Module
from ..svgelements import Color, Matrix, Point
from .laserrender import (
    DRAW_MODE_BACKGROUND,
    DRAW_MODE_GRID,
    DRAW_MODE_GUIDES,
    DRAW_MODE_LASERPATH,
    DRAW_MODE_RETICLE,
    DRAW_MODE_SELECTION,
)
from .zmatrix import ZMatrix

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


def swizzlecolor(c):
    if c is None:
        return None
    if isinstance(c, int):
        c = Color(c)
    return c.blue << 16 | c.green << 8 | c.red


class Scene(Module):
    def __init__(self, context, path):
        Module.__init__(self, context, path)
        self.matrix = Matrix()
        self.hittable_elements = list()
        self.hit_chain = list()
        self.widget_root = SceneSpaceWidget(self)
        self.matrix_root = Matrix()
        self.process = self.animate_tick
        self.interval = 1.0 / 60.0  # 60fps
        self.last_position = None
        self.time = None
        self.distance = None

    @staticmethod
    def sub_register(kernel):
        pass

    def initialize(self, *args, **kwargs):
        self.context.setting(int, "draw_mode", 0)
        self.context.setting(bool, "mouse_zoom_invert", False)
        self.context.setting(bool, "mouse_pan_invert", False)
        self.context.setting(bool, "mouse_wheel_pan", False)

    def finalize(self, *args, **kwargs):
        for e in self.context.elements._tree.flat():
            e.unregister()

    def rotary_stretch(self):
        r = self.context.get_context("rotary/1")
        scale_x = r.scale_x
        scale_y = r.scale_y
        self.widget_root.scene_widget.matrix.post_scale(scale_x, scale_y)
        self.context.signal("refresh_scene", 0)

    def rotary_unstretch(self):
        r = self.context.get_context("rotary/1")
        scale_x = r.scale_x
        scale_y = r.scale_y
        self.widget_root.scene_widget.matrix.post_scale(1.0 / scale_x, 1.0 / scale_y)
        self.context.signal("refresh_scene", 0)

    def signal(self, *args, **kwargs):
        self._signal_widget(self.widget_root, *args, **kwargs)

    def _signal_widget(self, widget, *args, **kwargs):
        try:
            widget.signal(*args)
        except AttributeError:
            pass
        for w in widget:
            if w is None:
                continue
            self._signal_widget(w, *args, **kwargs)

    def animate_tick(self):
        pass

    def draw(self, canvas):
        if self.widget_root is not None:
            self.widget_root.draw(canvas)

    def convert_scene_to_window(self, position):
        point = self.widget_root.scene_widget.matrix.point_in_matrix_space(position)
        return point[0], point[1]

    def convert_window_to_scene(self, position):
        point = self.widget_root.scene_widget.matrix.point_in_inverse_space(position)
        return point[0], point[1]

    def rebuild_hittable_chain(self):
        """
        Iterates through the tree and adds all hittable elements to the hittable_elements list.
        This is dynamically rebuilt on the mouse event.
        """
        self.hittable_elements.clear()
        self.rebuild_hit_chain(self.widget_root, self.matrix_root)

    def rebuild_hit_chain(self, current_widget, current_matrix=None):
        # If there is a matrix for the widget concatenate it.
        if current_widget.matrix is not None:
            matrix_within_scene = Matrix(current_widget.matrix)
            matrix_within_scene.post_cat(current_matrix)
        else:
            matrix_within_scene = Matrix(current_matrix)

        # Add to list and recurse for children based on response.
        response = current_widget.hit()
        if response == HITCHAIN_HIT:
            self.hittable_elements.append((current_widget, matrix_within_scene))
        elif response == HITCHAIN_DELEGATE:
            for w in current_widget:
                self.rebuild_hit_chain(w, matrix_within_scene)
        elif response == HITCHAIN_HIT_AND_DELEGATE:
            self.hittable_elements.append((current_widget, matrix_within_scene))
            for w in current_widget:
                self.rebuild_hit_chain(w, matrix_within_scene)
        elif response == HITCHAIN_DELEGATE_AND_HIT:
            for w in current_widget:
                self.rebuild_hit_chain(w, matrix_within_scene)
            self.hittable_elements.append((current_widget, matrix_within_scene))

    def find_hit_chain(self, position):
        self.hit_chain.clear()
        for current_widget, current_matrix in self.hittable_elements:
            hit_point = Point(current_matrix.point_in_inverse_space(position))
            if current_widget.contains(hit_point.x, hit_point.y):
                self.hit_chain.append((current_widget, current_matrix))

    def event(self, window_pos, event_type=""):
        if self.last_position is None:
            self.last_position = window_pos
        dx = window_pos[0] - self.last_position[0]
        dy = window_pos[1] - self.last_position[1]
        window_pos = (
            window_pos[0],
            window_pos[1],
            self.last_position[0],
            self.last_position[1],
            dx,
            dy,
        )
        self.last_position = window_pos
        try:
            previous_top_element = self.hit_chain[0][0]
        except (IndexError, TypeError):
            previous_top_element = None
        if event_type in (
            "leftdown",
            "middledown",
            "rightdown",
            "wheeldown",
            "wheelup",
            "hover",
        ):
            self.time = time.time()
            self.rebuild_hittable_chain()
            self.find_hit_chain(window_pos)
        for i, hit in enumerate(self.hit_chain):
            if hit is None:
                continue  # Element was dropped.
            current_widget, current_matrix = hit
            if current_widget is None:
                continue
            space_pos = window_pos
            if current_matrix is not None and not current_matrix.is_identity():
                space_cur = current_matrix.point_in_inverse_space(window_pos[0:2])
                space_last = current_matrix.point_in_inverse_space(window_pos[2:4])
                sdx = space_cur[0] - space_last[0]
                sdy = space_cur[1] - space_last[1]
                space_pos = (
                    space_cur[0],
                    space_cur[1],
                    space_last[0],
                    space_last[1],
                    sdx,
                    sdy,
                )
            if (
                i == 0
                and event_type == "hover"
                and previous_top_element is not current_widget
            ):
                if previous_top_element is not None:
                    previous_top_element.event(window_pos, window_pos, "hover_end")
                current_widget.event(window_pos, space_pos, "hover_start")
            if event_type == "leftup" and time.time() - self.time <= 0.15:
                response = current_widget.event(window_pos, space_pos, "leftclick")
            else:
                response = current_widget.event(window_pos, space_pos, event_type)
            if response == RESPONSE_ABORT:
                self.hit_chain.clear()
                return
            elif response == RESPONSE_CONSUME:
                return
            elif response == RESPONSE_CHAIN:
                continue
            elif response == RESPONSE_DROP:
                self.hit_chain[i] = None
            else:
                break

    def add_scenewidget(self, widget, properties=ORIENTATION_RELATIVE):
        self.widget_root.scene_widget.add_widget(-1, widget, properties)

    def add_interfacewidget(self, widget, properties=ORIENTATION_RELATIVE):
        self.widget_root.interface_widget.add_widget(-1, widget, properties)


class Widget(list):
    def __init__(self, scene, left=None, top=None, right=None, bottom=None, all=False):
        list.__init__(self)
        self.matrix = Matrix()
        self.scene = scene
        self.parent = None
        self.properties = ORIENTATION_RELATIVE
        if all:
            # contains all points
            self.left = -float("inf")
            self.top = -float("inf")
            self.right = float("inf")
            self.bottom = float("inf")
        else:
            # contains no points
            self.left = float("inf")
            self.top = float("inf")
            self.right = -float("inf")
            self.bottom = -float("inf")
        if left is not None:
            self.left = left
        if right is not None:
            self.right = right
        if top is not None:
            self.top = top
        if bottom is not None:
            self.bottom = bottom

    def __str__(self):
        return "Widget(%f, %f, %f, %f)" % (self.left, self.top, self.right, self.bottom)

    def __repr__(self):
        return "%s(%f, %f, %f, %f)" % (
            type(self).__name__,
            self.left,
            self.top,
            self.right,
            self.bottom,
        )

    def hit(self):
        return HITCHAIN_DELEGATE

    def draw(self, gc):
        # Concat if this is a thing.
        m = self.matrix
        gc.PushState()
        gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(m)))
        self.process_draw(gc)
        for i in range(len(self) - 1, -1, -1):
            widget = self[i]
            widget.draw(gc)
        gc.PopState()

    def process_draw(self, gc):
        pass

    def contains(self, x, y=None):
        if y is None:
            y = x.y
            x = x.x
        return self.left <= x <= self.right and self.top <= y <= self.bottom

    def event(self, window_pos=None, space_pos=None, event_type=None):
        return RESPONSE_CHAIN

    def notify_added_to_parent(self, parent):
        pass

    def notify_added_child(self, child):
        pass

    def notify_removed_from_parent(self, parent):
        pass

    def notify_removed_child(self, child):
        pass

    def notify_moved_child(self, child):
        pass

    def add_widget(self, index=-1, widget=None, properties=0):
        if len(self) == 0:
            last = None
        else:
            last = self[-1]
        if 0 <= index < len(self):
            self.insert(index, widget)
        else:
            self.append(widget)
        widget.parent = self
        self.layout_by_orientation(widget, last, properties)
        self.notify_added_to_parent(self)
        self.notify_added_child(widget)

    def translate(self, dx, dy):
        if dx == 0 and dy == 0:
            return
        if dx == float("nan"):
            return
        if dy == float("nan"):
            return
        if abs(dx) == float("inf"):
            return
        if abs(dy) == float("inf"):
            return
        self.translate_loop(dx, dy)

    def translate_loop(self, dx, dy):
        if self.properties & ORIENTATION_ABSOLUTE != 0:
            return  # Do not translate absolute oriented widgets.
        self.translate_self(dx, dy)
        for w in self:
            w.translate_loop(dx, dy)

    def translate_self(self, dx, dy):
        self.left += dx
        self.right += dx
        self.top += dy
        self.bottom += dy
        if self.parent is not None:
            self.notify_moved_child(self)

    def union_children_bounds(self, bounds=None):
        if bounds is None:
            bounds = [self.left, self.top, self.right, self.bottom]
        else:
            if bounds[0] > self.left:
                bounds[0] = self.left
            if bounds[1] > self.top:
                bounds[1] = self.top
            if bounds[2] < self.right:
                bounds[2] = self.left
            if bounds[3] < self.bottom:
                bounds[3] = self.bottom
        for w in self:
            w.union_children_bounds(bounds)
        return bounds

    @property
    def height(self):
        return self.bottom - self.top

    @property
    def width(self):
        return self.right - self.left

    def layout_by_orientation(self, widget, last, properties):
        if properties & ORIENTATION_ABSOLUTE != 0:
            return
        if properties & ORIENTATION_NO_BUFFER != 0:
            buffer = 0
        else:
            buffer = BUFFER
        if (properties & ORIENTATION_MODE_MASK) == ORIENTATION_RELATIVE:
            widget.translate(self.left, self.top)
            return
        elif last is None:  # orientation = origin
            widget.translate(self.left - widget.left, self.top - widget.top)
        elif (properties & ORIENTATION_GRID) != 0:
            dim = properties & ORIENTATION_DIM_MASK
            if (properties & ORIENTATION_VERTICAL) != 0:
                if dim == 0:  # Vertical
                    if self.height >= last.bottom - self.top + widget.height:
                        # add to line
                        widget.translate(
                            last.left - widget.left, last.bottom - widget.top
                        )
                    else:
                        # line return
                        widget.translate(
                            last.right - widget.left + buffer, self.top - widget.top
                        )
            else:
                if dim == 0:  # Horizontal
                    if self.width >= last.right - self.left + widget.width:
                        # add to line
                        widget.translate(
                            last.right - widget.left + buffer, last.top - widget.top
                        )
                    else:
                        # line return
                        widget.translate(
                            self.left - widget.left, last.bottom - widget.top + buffer
                        )
        elif (properties & ORIENTATION_HORIZONTAL) != 0:
            widget.translate(last.right - widget.left + buffer, last.top - widget.top)
        elif (properties & ORIENTATION_VERTICAL) != 0:
            widget.translate(last.left - widget.left, last.bottom - widget.top + buffer)
        if properties & ORIENTATION_CENTERED:
            self.center_children()

    def center_children(self):
        child_bounds = self.union_children_bounds()
        dx = self.left - (child_bounds[0] + child_bounds[2]) / 2.0
        dy = self.top - (child_bounds[1] + child_bounds[3]) / 2.0
        if dx != 0 and dy != 0:
            for w in self:
                w.translate_loop(dx, dy)

    def center_widget(self, x, y=None):
        if y is None:
            y = x.y
            x = x.x
        child_bounds = self.union_children_bounds()
        cx = (child_bounds[0] + child_bounds[2]) / 2.0
        cy = (child_bounds[1] + child_bounds[3]) / 2.0
        self.translate(x - cx, y - cy)

    def set_position(self, x, y=None):
        if y is None:
            y = x.y
            x = x.x
        dx = x - self.left
        dy = y - self.top
        self.translate(dx, dy)

    def remove_all_widgets(self):
        for w in self:
            if w is None:
                continue
            w.parent = None
            w.notify_removed_from_parent(self)
            self.notify_removed_child(w)
        self.clear()
        try:
            self.scene.notify_tree_changed()
        except AttributeError:
            pass

    def remove_widget(self, widget=None):
        if widget is None:
            return
        if isinstance(widget, Widget):
            list.remove(widget)
        elif isinstance(widget, int):
            index = widget
            widget = self[index]
            list.remove(index)
        widget.parent = None
        widget.notify_removed_from_parent(self)
        self.notify_removed_child(widget)
        try:
            self.scene.notify_tree_changed()
        except AttributeError:
            pass

    def set_widget(self, index, widget):
        w = self[index]
        self[index] = widget
        widget.parent = self
        widget.notify_added_to_parent(self)
        self.notify_removed_child(w)
        try:
            self.scene.notify_tree_changed()
        except AttributeError:
            pass

    def on_matrix_change(self):
        pass

    def scene_matrix_reset(self):
        self.matrix.reset()
        self.on_matrix_change()

    def scene_post_scale(self, sx, sy=None, ax=0, ay=0):
        self.matrix.post_scale(sx, sy, ax, ay)
        self.on_matrix_change()

    def scene_post_pan(self, px, py):
        self.matrix.post_translate(px, py)
        self.on_matrix_change()

    def scene_post_rotate(self, angle, rx=0, ry=0):
        self.matrix.post_rotate(angle, rx, ry)
        self.on_matrix_change()

    def scene_pre_scale(self, sx, sy=None, ax=0, ay=0):
        self.matrix.pre_scale(sx, sy, ax, ay)
        self.on_matrix_change()

    def scene_pre_pan(self, px, py):
        self.matrix.pre_translate(px, py)
        self.on_matrix_change()

    def scene_pre_rotate(self, angle, rx=0, ry=0):
        self.matrix.pre_rotate(angle, rx, ry)
        self.on_matrix_change()

    def get_scale_x(self):
        return self.matrix.value_scale_x()

    def get_scale_y(self):
        return self.matrix.value_scale_y()

    def get_skew_x(self):
        return self.matrix.value_skew_x()

    def get_skew_y(self):
        return self.matrix.value_skew_y()

    def get_translate_x(self):
        return self.matrix.value_trans_x()

    def get_translate_y(self):
        return self.matrix.value_trans_y()


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
        for e in elements._tree.flat(types=("elem",), emphasized=True):
            obj = e.object
            obj.transform.post_translate(dx, dy)
            obj.node.modified()
        for e in elements._tree.flat(
            types=("group", "file", "op element"), emphasized=True
        ):
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

    def process_draw(self, gc):
        context = self.scene.context
        try:
            if context.draw_mode & DRAW_MODE_RETICLE == 0:
                # Draw Reticle
                gc.SetPen(wx.RED_PEN)
                gc.SetBrush(wx.TRANSPARENT_BRUSH)
                x = context._reticle_x
                y = context._reticle_y
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

    def process_draw(self, gc):
        context = self.scene.context
        if context.draw_mode & DRAW_MODE_LASERPATH == 0:
            gc.SetPen(wx.BLUE_PEN)
            starts, ends = gc.laserpath
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

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "hover":
            return RESPONSE_CHAIN
        self.grid = None
        return RESPONSE_CHAIN

    def calculate_grid(self):
        if self.scene.context is not None:
            context = self.scene.context
            bed_dim = context.get_context("/")
            wmils = bed_dim.bed_width * MILS_IN_MM
            hmils = bed_dim.bed_height * MILS_IN_MM
        else:
            wmils = 310 * MILS_IN_MM
            hmils = 210 * MILS_IN_MM

        kernel_root = self.scene.context.get_context("/")
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
                bed_dim = context.get_context("/")
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


class SceneSpaceWidget(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.interface_widget = Widget(scene)
        self.scene_widget = Widget(scene)
        self.add_widget(-1, self.interface_widget)
        self.add_widget(-1, self.scene_widget)
        self.last_position = None
        self._previous_zoom = None
        self._placement_event = None
        self._placement_event_type = None

    def hit(self):
        return HITCHAIN_DELEGATE_AND_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "hover":
            return RESPONSE_CHAIN
        if event_type == "wheelup" and self.scene.context.mouse_wheel_pan:
            if self.scene.context.mouse_pan_invert:
                self.scene_widget.matrix.post_translate(0, 25)
            else:
                self.scene_widget.matrix.post_translate(0, -25)
        elif event_type == "wheeldown" and self.scene.context.mouse_wheel_pan:
            if self.scene.context.mouse_pan_invert:
                self.scene_widget.matrix.post_translate(0, -25)
            else:
                self.scene_widget.matrix.post_translate(0, 25)
        elif event_type == "wheelup" or event_type == "wheelup_ctrl":
            if self.scene.context.mouse_zoom_invert:
                self.scene_widget.matrix.post_scale(
                    1.0 / 1.1, 1.0 / 1.1, space_pos[0], space_pos[1]
                )
            else:
                self.scene_widget.matrix.post_scale(
                    1.1, 1.1, space_pos[0], space_pos[1]
                )
            self.scene.context.signal("refresh_scene", 0)
            return RESPONSE_CONSUME
        elif event_type == "zoom-in":
            self.scene_widget.matrix.post_scale(1.1, 1.1, space_pos[0], space_pos[1])
            self.scene.context.signal("refresh_scene", 0)
            return RESPONSE_CONSUME
        elif event_type == "rightdown+alt":
            self._previous_zoom = 1.0
            self._placement_event = space_pos
            self._placement_event_type = "zoom"
            return RESPONSE_CONSUME
        elif event_type == "rightdown+control":
            self._previous_zoom = 1.0
            self._placement_event = space_pos
            self._placement_event_type = "pan"
            return RESPONSE_CONSUME
        elif event_type == "rightup":
            self._previous_zoom = None
            self._placement_event = None
            self._placement_event_type = None
        elif event_type == "wheeldown" or event_type == "wheeldown_ctrl":
            if self.scene.context.mouse_zoom_invert:
                self.scene_widget.matrix.post_scale(
                    1.1, 1.1, space_pos[0], space_pos[1]
                )
            else:
                self.scene_widget.matrix.post_scale(
                    1.0 / 1.1, 1.0 / 1.1, space_pos[0], space_pos[1]
                )
            self.scene.context.signal("refresh_scene", 0)
            return RESPONSE_CONSUME
        elif event_type == "zoom-out":
            self.scene_widget.matrix.post_scale(
                1.0 / 1.1, 1.0 / 1.1, space_pos[0], space_pos[1]
            )
            self.scene.context.signal("refresh_scene", 0)
            return RESPONSE_CONSUME
        elif event_type == "wheelleft":
            if self.scene.context.mouse_pan_invert:
                self.scene_widget.matrix.post_translate(25, 0)
            else:
                self.scene_widget.matrix.post_translate(-25, 0)
            self.scene.context.signal("refresh_scene", 0)
            return RESPONSE_CONSUME
        elif event_type == "wheelright":
            if self.scene.context.mouse_pan_invert:
                self.scene_widget.matrix.post_translate(-25, 0)
            else:
                self.scene_widget.matrix.post_translate(25, 0)
            self.scene.context.signal("refresh_scene", 0)
            return RESPONSE_CONSUME
        elif event_type == "middledown":
            return RESPONSE_CONSUME
        elif event_type == "middleup":
            return RESPONSE_CONSUME
        elif event_type == "gesture-start":
            self._previous_zoom = 1.0
            return RESPONSE_CONSUME
        elif event_type == "gesture-end":
            self._previous_zoom = None
            return RESPONSE_CONSUME
        elif str(event_type).startswith("zoom"):
            if self._previous_zoom is None:
                return RESPONSE_CONSUME
            try:
                zoom = float(event_type.split(" ")[1])
            except Exception:
                return RESPONSE_CONSUME

            zoom_change = zoom / self._previous_zoom
            self.scene_widget.matrix.post_scale(
                zoom_change, zoom_change, space_pos[0], space_pos[1]
            )
            self.scene_widget.matrix.post_translate(space_pos[4], space_pos[5])
            self._previous_zoom = zoom
            self.scene.context.signal("refresh_scene", 0)

            return RESPONSE_CONSUME
        # Movement
        if self._placement_event_type is None:
            self.scene_widget.matrix.post_translate(space_pos[4], space_pos[5])
            self.scene.context.signal("refresh_scene", 0)
        elif self._placement_event_type == "zoom":
            from math import e

            p = (
                space_pos[0]
                - self._placement_event[0]
                + space_pos[1]
                - self._placement_event[1]
            )
            p /= 250.0
            zoom_factor = e ** p
            zoom_change = zoom_factor / self._previous_zoom
            self._previous_zoom = zoom_factor
            self.scene_widget.matrix.post_scale(
                zoom_change,
                zoom_change,
                self._placement_event[0],
                self._placement_event[1],
            )
            self.scene.context.signal("refresh_scene", 0)
        elif self._placement_event_type == "pan":
            pan_factor_x = -(space_pos[0] - self._placement_event[0]) / 10
            pan_factor_y = -(space_pos[1] - self._placement_event[1]) / 10
            self.scene_widget.matrix.post_translate(pan_factor_x, pan_factor_y)
            self.scene.context.signal("refresh_scene", 0)
        return RESPONSE_CONSUME

    def focus_position_scene(self, scene_point, scene_size):
        window_width, window_height = self.scene.ClientSize
        scale_x = self.get_scale_x()
        scale_y = self.get_scale_y()
        self.scene_matrix_reset()
        self.scene_post_pan(-scene_point[0], -scene_point[1])
        self.scene_post_scale(scale_x, scale_y)
        self.scene_post_pan(window_width / 2.0, window_height / 2.0)

    def focus_viewport_scene(
        self, new_scene_viewport, scene_size, buffer=0.0, lock=True
    ):
        """
        Focus on the given viewport in the scene.

        :param new_scene_viewport: Viewport to have after this process within the scene.
        :param scene_size: Size of the scene in which this viewport is active.
        :param buffer: Amount of buffer around the edge of the new viewport.
        :param lock: lock the scalex, scaley.
        :return:
        """
        window_width, window_height = scene_size
        left = new_scene_viewport[0]
        top = new_scene_viewport[1]
        right = new_scene_viewport[2]
        bottom = new_scene_viewport[3]
        viewport_width = right - left
        viewport_height = bottom - top

        left -= viewport_width * buffer
        right += viewport_width * buffer
        top -= viewport_height * buffer
        bottom += viewport_height * buffer

        if right == left:
            scale_x = 100
        else:
            scale_x = window_width / float(right - left)
        if bottom == top:
            scale_y = 100
        else:
            scale_y = window_height / float(bottom - top)

        cx = (right + left) / 2
        cy = (top + bottom) / 2
        self.scene_widget.matrix.reset()
        self.scene_widget.matrix.post_translate(-cx, -cy)
        if lock:
            scale = min(scale_x, scale_y)
            if scale != 0:
                self.scene_widget.matrix.post_scale(scale)
        else:
            if scale_x != 0 and scale_y != 0:
                self.scene_widget.matrix.post_scale(scale_x, scale_y)
        self.scene_widget.matrix.post_translate(window_width / 2.0, window_height / 2.0)
