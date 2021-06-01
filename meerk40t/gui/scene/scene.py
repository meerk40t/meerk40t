import threading
import time

from meerk40t.gui.scene.widget import SceneSpaceWidget

try:
    from math import tau
except ImportError:
    from math import pi

    tau = 2 * pi

import wx

from meerk40t.kernel import Job, Module
from meerk40t.svgelements import Matrix, Point
from meerk40t.gui.laserrender import (
    DRAW_MODE_ANIMATE,
    DRAW_MODE_FLIPXY,
    DRAW_MODE_INVERT,
    DRAW_MODE_REFRESH,
)

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


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        kernel.register("module/Scene", Scene)


class ScenePanel(wx.Panel):
    def __init__(self, context, *args, scene_name="Scene", **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL | wx.WANTS_CHARS
        wx.Panel.__init__(self, *args, **kwds)
        self.scene_panel = wx.Panel(self, wx.ID_ANY, style=wx.WANTS_CHARS)
        self.scene = context.open_as("module/Scene", scene_name, self)
        self.context = context
        self.scene_panel.SetDoubleBuffered(True)

        self._Buffer = None

        self.__set_properties()
        self.__do_layout()

        self.scene_panel.Bind(wx.EVT_PAINT, self.on_paint)
        self.scene_panel.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase)

        self.scene_panel.Bind(wx.EVT_MOTION, self.on_mouse_move)

        self.scene_panel.Bind(wx.EVT_MOUSEWHEEL, self.on_mousewheel)

        self.scene_panel.Bind(wx.EVT_MIDDLE_DOWN, self.on_mouse_middle_down)
        self.scene_panel.Bind(wx.EVT_MIDDLE_UP, self.on_mouse_middle_up)

        self.scene_panel.Bind(wx.EVT_LEFT_DCLICK, self.on_mouse_double_click)

        self.scene_panel.Bind(wx.EVT_RIGHT_DOWN, self.on_right_mouse_down)
        self.scene_panel.Bind(wx.EVT_RIGHT_UP, self.on_right_mouse_up)

        self.scene_panel.Bind(wx.EVT_LEFT_DOWN, self.on_left_mouse_down)
        self.scene_panel.Bind(wx.EVT_LEFT_UP, self.on_left_mouse_up)

        self.scene_panel.Bind(wx.EVT_SIZE, self.on_size)

        try:
            self.scene_panel.Bind(wx.EVT_MAGNIFY, self.on_magnify_mouse)
            self.scene_panel.Bind(wx.EVT_GESTURE_PAN, self.on_gesture)
            self.scene_panel.Bind(wx.EVT_GESTURE_ZOOM, self.on_gesture)
            # self.tree.Bind(wx.EVT_GESTURE_PAN, self.on_gesture)
            # self.tree.Bind(wx.EVT_GESTURE_ZOOM, self.on_gesture)
        except AttributeError:
            # Not WX 4.1
            pass

    def __set_properties(self):
        pass

    def __do_layout(self):
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(self.scene_panel, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()

    def signal(self, *args, **kwargs):
        self.scene._signal_widget(self.scene.widget_root, *args, **kwargs)

    def on_size(self, event):
        if self.context is None:
            return
        # self.Layout()
        self.signal("guide")
        self.scene.request_refresh()

    # Mouse Events.

    def on_mousewheel(self, event):
        if self.scene_panel.HasCapture():
            return
        rotation = event.GetWheelRotation()
        if event.GetWheelAxis() == wx.MOUSE_WHEEL_VERTICAL and not event.ShiftDown():
            if event.HasAnyModifiers():
                if rotation > 1:
                    self.scene.event(event.GetPosition(), "wheelup_ctrl")
                elif rotation < -1:
                    self.scene.event(event.GetPosition(), "wheeldown_ctrl")
            else:
                if rotation > 1:
                    self.scene.event(event.GetPosition(), "wheelup")
                elif rotation < -1:
                    self.scene.event(event.GetPosition(), "wheeldown")
        else:
            if rotation > 1:
                self.scene.event(event.GetPosition(), "wheelleft")
            elif rotation < -1:
                self.scene.event(event.GetPosition(), "wheelright")

    def on_mousewheel_zoom(self, event):
        if self.scene_panel.HasCapture():
            return
        rotation = event.GetWheelRotation()
        if self.context.mouse_zoom_invert:
            rotation = -rotation
        if rotation > 1:
            self.scene.event(event.GetPosition(), "wheelup")
        elif rotation < -1:
            self.scene.event(event.GetPosition(), "wheeldown")

    def on_mouse_middle_down(self, event):
        self.SetFocus()
        if not self.scene_panel.HasCapture():
            self.scene_panel.CaptureMouse()
        self.scene.event(event.GetPosition(), "middledown")

    def on_mouse_middle_up(self, event):
        if self.scene_panel.HasCapture():
            self.scene_panel.ReleaseMouse()
        self.scene.event(event.GetPosition(), "middleup")

    def on_left_mouse_down(self, event):
        self.SetFocus()
        if not self.scene_panel.HasCapture():
            self.scene_panel.CaptureMouse()
        self.scene.event(event.GetPosition(), "leftdown")

    def on_left_mouse_up(self, event):
        if self.scene_panel.HasCapture():
            self.scene_panel.ReleaseMouse()
        self.scene.event(event.GetPosition(), "leftup")

    def on_mouse_double_click(self, event):
        if self.scene_panel.HasCapture():
            return
        self.scene.event(event.GetPosition(), "doubleclick")

    def on_mouse_move(self, event: wx.MouseEvent):
        if event.Moving():
            self.scene.event(event.GetPosition(), "hover")
        else:
            self.scene.event(event.GetPosition(), "move")

    def on_right_mouse_down(self, event):
        self.SetFocus()
        if event.AltDown():
            self.scene.event(event.GetPosition(), "rightdown+alt")
        elif event.ControlDown():
            self.scene.event(event.GetPosition(), "rightdown+control")
        else:
            self.scene.event(event.GetPosition(), "rightdown")

    def on_right_mouse_up(self, event):
        self.scene.event(event.GetPosition(), "rightup")

    def on_magnify_mouse(self, event):
        magnify = event.GetMagnification()
        if magnify > 0:
            self.scene.event(event.GetPosition(), "zoom-in")
        if magnify < 0:
            self.scene.event(event.GetPosition(), "zoom-out")

    def on_gesture(self, event):
        """
        This code requires WXPython 4.1 and the bind will fail otherwise.
        """
        if event.IsGestureStart():
            self.scene.event(event.GetPosition(), "gesture-start")
        elif event.IsGestureEnd():
            self.scene.event(event.GetPosition(), "gesture-end")
        else:
            try:
                zoom = event.GetZoomFactor()
            except AttributeError:
                zoom = 1.0
            self.scene.event(event.GetPosition(), "zoom %f" % zoom)

    def on_paint(self, event):
        try:
            if self._Buffer is None:
                self.scene.update_buffer_ui_thread()
            wx.BufferedPaintDC(self.scene_panel, self._Buffer)
        except RuntimeError:
            pass

    def on_erase(self, event):
        pass

    def set_buffer(self):
        width, height = self.ClientSize
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        self._Buffer = wx.Bitmap(width, height)


class Scene(Module, Job):
    def __init__(self, context, path, gui, **kwargs):
        Module.__init__(self, context, path)
        Job.__init__(
            self,
            job_name="Scene-%s" % path,
            process=self.refresh_scene,
            conditional=lambda: self.screen_refresh_is_requested,
            run_main=True,
        )
        self.gui = gui
        self.matrix = Matrix()
        self.hittable_elements = list()
        self.hit_chain = list()
        self.widget_root = SceneSpaceWidget(self)
        self.matrix_root = Matrix()
        self.screen_refresh_lock = threading.Lock()
        self.interval = 1.0 / 60.0  # 60fps
        self.last_position = None
        self.time = None
        self.distance = None

        self.screen_refresh_is_requested = True
        self.background_brush = wx.Brush("Grey")

    def initialize(self, *args, **kwargs):
        context = self.context
        context.schedule(self)
        context.listen("driver;position", self.on_update_position)
        context.setting(int, "draw_mode", 0)
        context.setting(bool, "mouse_zoom_invert", False)
        context.setting(bool, "mouse_pan_invert", False)
        context.setting(bool, "mouse_wheel_pan", False)
        context.setting(int, "fps", 40)
        if context.fps <= 0:
            context.fps = 60
        self.interval = 1.0 / float(context.fps)
        self.commit()

    def on_update_position(self, origin, pos):
        self.request_refresh_for_animation()

    def commit(self):
        context = self.context
        self._init_widget(self.widget_root, context)

    def restore(self, gui, **kwargs):
        self.gui = gui

    def finalize(self, *args, **kwargs):
        self._final_widget(self.widget_root, self.context)
        self.context.unlisten("driver;position", self.on_update_position)
        self.screen_refresh_lock.acquire()  # calling shutdown live locks here since it's already shutting down.
        self.context.unschedule(self)
        for e in self.context.elements._tree.flat():
            e.unregister()

    def _init_widget(self, widget, context):
        try:
            widget.init(context)
        except AttributeError:
            pass
        for w in widget:
            if w is None:
                continue
            self._init_widget(w, context)

    def _final_widget(self, widget, context):
        try:
            widget.final(context)
        except AttributeError:
            pass
        for w in widget:
            if w is None:
                continue
            self._final_widget(w, context)

    def set_fps(self, fps):
        if fps == 0:
            fps = 1
        self.context.fps = fps
        self.interval = 1.0 / float(self.context.fps)

    def request_refresh_for_animation(self):
        """Called on the various signals trying to animate the screen."""
        try:
            if self.context.draw_mode & DRAW_MODE_ANIMATE == 0:
                self.request_refresh()
        except AttributeError:
            pass

    def request_refresh(self, origin=None, *args):
        """Request an update to the scene."""
        try:
            if self.context.draw_mode & DRAW_MODE_REFRESH == 0:
                self.screen_refresh_is_requested = True
        except AttributeError:
            pass

    def refresh_scene(self, *args, **kwargs):
        """
        Called by the Scheduler at a given the specified framerate.
        Called by in the UI thread.
        """
        if self.screen_refresh_is_requested:
            if self.screen_refresh_lock.acquire(timeout=0.2):
                self.update_buffer_ui_thread()
                self.gui.Refresh()
                self.gui.Update()
                self.screen_refresh_is_requested = False
                self.screen_refresh_lock.release()
            else:
                self.screen_refresh_is_requested = False

    def update_buffer_ui_thread(self):
        """Performs the redraw of the data in the UI thread."""
        dm = self.context.draw_mode
        buf = self.gui._Buffer
        if buf is None or buf.GetSize() != self.gui.ClientSize or not buf.IsOk():
            self.gui.set_buffer()
            buf = self.gui._Buffer
        dc = wx.MemoryDC()
        dc.SelectObject(buf)
        dc.SetBackground(self.background_brush)
        dc.Clear()
        w, h = dc.Size
        if dm & DRAW_MODE_FLIPXY != 0:
            dc.SetUserScale(-1, -1)
            dc.SetLogicalOrigin(w, h)
        gc = wx.GraphicsContext.Create(dc)
        gc.Size = dc.Size

        font = wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD)
        gc.SetFont(font, wx.BLACK)
        self.draw(gc)
        if dm & DRAW_MODE_INVERT != 0:
            dc.Blit(0, 0, w, h, dc, 0, 0, wx.SRC_INVERT)
        gc.Destroy()
        del dc

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

    def notify_added_to_parent(self, parent):
        pass

    def notify_added_child(self, child):
        try:
            child.init(self.context)
        except AttributeError:
            pass

    def notify_removed_from_parent(self, parent):
        pass

    def notify_removed_child(self, child):
        try:
            child.final(self.context)
        except AttributeError:
            pass

    def notify_moved_child(self, child):
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

