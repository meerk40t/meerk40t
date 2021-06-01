
try:
    from math import tau
except ImportError:
    from math import pi

    tau = 2 * pi

import wx

from meerk40t.svgelements import Matrix

from meerk40t.gui.zmatrix import ZMatrix

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


# TODO: _buffer can be updated partially rather than fully rewritten, especially with some layering.


class Widget(list):
    def __init__(
        self,
        scene: 'Scene',
        left: float = None,
        top: float = None,
        right: float = None,
        bottom: float = None,
        all: bool = False,
    ):
        """
        All is whether this sends all points.
        """
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
        matrix = self.matrix
        gc.PushState()
        if matrix is not None and not matrix.is_identity():
            gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
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
        self.scene.notify_added_to_parent(parent)

    def notify_added_child(self, child):
        self.scene.notify_added_child(child)

    def notify_removed_from_parent(self, parent):
        self.scene.notify_removed_from_parent(parent)

    def notify_removed_child(self, child):
        self.scene.notify_removed_child(child)

    def notify_moved_child(self, child):
        self.scene.notify_moved_child(child)

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


class ButtonWidget(Widget):
    def __init__(self, scene, left, top, right, bottom, bitmap):
        Widget.__init__(self, scene, left, top, right, bottom)
        self.bitmap = bitmap
        self.background_brush = None
        self.enabled = True

    def hit(self):
        if self.enabled:
            return HITCHAIN_HIT
        else:
            return HITCHAIN_DELEGATE

    def process_draw(self, gc: wx.GraphicsContext):
        gc.PushState()
        gc.SetTransform(ZMatrix(self.matrix))
        if self.background_brush is not None:
            gc.SetBrush(self.background_brush)
            gc.DrawRectangle(0, 0, self.width, self.height)
        gc.DrawBitmap(self.bitmap)
        gc.PopState()

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "leftdown":
            self.clicked(window_pos=None, space_pos=None)
        return RESPONSE_ABORT

    def clicked(self, window_pos=None, space_pos=None):
        pass
