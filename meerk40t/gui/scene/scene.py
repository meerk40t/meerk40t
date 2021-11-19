import threading
import time

import wx

from meerk40t.gui.laserrender import (
    DRAW_MODE_ANIMATE,
    DRAW_MODE_FLIPXY,
    DRAW_MODE_INVERT,
    DRAW_MODE_REFRESH,
)
from meerk40t.gui.zmatrix import ZMatrix
from meerk40t.kernel import Job, Module
from meerk40t.svgelements import Matrix, Point, Viewbox

try:
    from math import tau
except ImportError:
    from math import pi

    tau = 2 * pi

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


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        kernel.register("module/Scene", Scene)
    elif lifecycle == "boot":
        kernel_root = kernel.root
        choices = [
            {
                "attr": "units_name",
                "object": kernel_root,
                "default": "mm",
                "type": str,
            },
            {
                "attr": "units_marks",
                "object": kernel_root,
                "default": 10,
                "type": int,
            },
            {
                "attr": "units_index",
                "object": kernel_root,
                "default": 0,
                "type": int,
            },
            {
                "attr": "units_convert",
                "object": kernel_root,
                "default": 39.3701,
                "type": float,
            },
        ]
        kernel.register_choices("units", choices)


class ScenePanel(wx.Panel):
    """
    wxPanel that holds the Scene. This serves as the wx.Control object that holds and draws the scene.
    """

    def __init__(self, context, *args, scene_name="Scene", **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.scene_panel = wx.Panel(self, wx.ID_ANY)
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
        self.scene_panel.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.on_mouse_capture_lost)

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
        """
        Scene signal calls the signal command on the root which is used to pass message and data to deeper objects
        within the scene.
        """
        self.scene._signal_widget(self.scene.widget_root, *args, **kwargs)

    def on_size(self, event=None):
        if self.context is None:
            return
        w, h = self.Size
        self.scene.widget_root.set_frame(0, 0, w, h)
        self.signal("guide")
        self.scene.request_refresh()

    # Mouse Events.

    def on_mousewheel(self, event):
        """
        ScenePanel mousewheel event.

        If modifiers are present it calls the event 'wheelup_ctrl' or 'wheeldown_ctrl' this also triggers scene events
        for up, down, and left and right which exist on some mice and trackpads. If shift is held down while the wheel
        event occurs the up and down rotation is treated as left and right.

        """
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
        """
        The mousewheel zoom is not called.
        """
        if self.scene_panel.HasCapture():
            return
        rotation = event.GetWheelRotation()
        if self.context.mouse_zoom_invert:
            rotation = -rotation
        if rotation > 1:
            self.scene.event(event.GetPosition(), "wheelup")
        elif rotation < -1:
            self.scene.event(event.GetPosition(), "wheeldown")

    def on_mouse_capture_lost(self, event):
        self.scene.event(None, "lost")

    def on_mouse_middle_down(self, event):
        """
        Scene Panel middle click event for down.
        """
        self.SetFocus()
        if not self.scene_panel.HasCapture():
            self.scene_panel.CaptureMouse()
        self.scene.event(event.GetPosition(), "middledown")

    def on_mouse_middle_up(self, event):
        """
        Scene Panel middle click event for up.
        """
        if self.scene_panel.HasCapture():
            self.scene_panel.ReleaseMouse()
        self.scene.event(event.GetPosition(), "middleup")

    def on_left_mouse_down(self, event):
        """
        Scene Panel left click event for down.
        """
        self.SetFocus()
        if not self.scene_panel.HasCapture():
            self.scene_panel.CaptureMouse()
        self.scene.event(event.GetPosition(), "leftdown")

    def on_left_mouse_up(self, event):
        """
        Scene Panel left click event for up.
        """
        if self.scene_panel.HasCapture():
            self.scene_panel.ReleaseMouse()
        self.scene.event(event.GetPosition(), "leftup")

    def on_mouse_double_click(self, event):
        """
        Scene Panel doubleclick event.
        """
        if self.scene_panel.HasCapture():
            return
        self.scene.event(event.GetPosition(), "doubleclick")

    def on_mouse_move(self, event: wx.MouseEvent):
        """
        Scene Panel move event. Calls hover if the mouse has no pressed buttons.
        Calls move if the mouse is currently dragging.
        """
        if event.Moving():
            self.scene.event(event.GetPosition(), "hover")
        else:
            self.scene.event(event.GetPosition(), "move")

    def on_right_mouse_down(self, event):
        """
        Scene Panel right mouse down event.

        Offers alternative events if Alt or control is currently pressed.
        """
        self.SetFocus()
        if event.AltDown():
            self.scene.event(event.GetPosition(), "rightdown+alt")
        elif event.ControlDown():
            self.scene.event(event.GetPosition(), "rightdown+control")
        else:
            self.scene.event(event.GetPosition(), "rightdown")

    def on_right_mouse_up(self, event):
        """
        Scene Panel right mouse up event.
        """
        self.scene.event(event.GetPosition(), "rightup")

    def on_magnify_mouse(self, event):
        """
        Magnify Mouse is a Mac Event called with pinch to zoom on a trackpad.
        """
        magnify = event.GetMagnification()
        if magnify > 0:
            self.scene.event(event.GetPosition(), "zoom-in")
        if magnify < 0:
            self.scene.event(event.GetPosition(), "zoom-out")

    def on_gesture(self, event):
        """
        Scene Panel TouchScreen Gestures events.

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

    def on_paint(self, event=None):
        """
        Scene Panel paint event calls the paints the bitmap self._Buffer. If self._Buffer does not exist initially
        it is created in the self.scene.update_buffer_ui_thread() call.
        """
        try:
            if self._Buffer is None:
                self.scene.update_buffer_ui_thread()
            wx.BufferedPaintDC(self.scene_panel, self._Buffer)
        except (RuntimeError, AssertionError):
            pass

    def on_erase(self, event):
        """
        Scene Panel Screen erase call.
        """
        pass

    def set_buffer(self):
        """
        Set the value for the self._Buffer bitmap equal to the panel's clientSize.
        """
        width, height = self.ClientSize
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        self._Buffer = wx.Bitmap(width, height)


class Scene(Module, Job):
    """
    The Scene Module holds all the needed references to widgets and catches the events from the ScenePanel which
    stores this object primarily.

    Scene overloads both Module being registered in "module/Scene" and the Job to handle the refresh.

    The Scene is the infinite space of the scene as seen through the panel's viewpoint. It serves to zoom, pan, and
    manipulate various elements. This is done through a matrix which translates the scene space to window space. The
    scene space to window space. The widgets are stored in a tree within the scene. The primary widget is the
    SceneSpaceWidget which draws elements in two different forms. It first draws the scene and all scenewidgets added
    to the scene and then the interface widget which contains all the non-scene widget elements.
    """

    def __init__(self, context, path, gui, **kwargs):
        Module.__init__(self, context, path)
        Job.__init__(
            self,
            job_name="Scene-%s" % path,
            process=self.refresh_scene,
            conditional=lambda: self.screen_refresh_is_requested,
            run_main=True,
        )
        self.log = context.channel("scene")
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
        self._cursor = None

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
        """
        Called if the scene is reinitialized with a second open command.
        """
        self.gui = gui

    def finalize(self, *args, **kwargs):
        self._final_widget(self.widget_root, self.context)
        self.context.unlisten("driver;position", self.on_update_position)
        self.screen_refresh_lock.acquire()  # calling shutdown live locks here since it's already shutting down.
        self.context.unschedule(self)
        for e in self.context.elements.flat():
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
        """
        Set the scene frames per second which sets the interval for the Job.
        """
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
        Called in the UI thread.
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
        """
        Rotary Stretch of Scene based on values in "rotary/1"
        """
        r = self.context.get_context("rotary/1")
        scale_x = r.scale_x
        scale_y = r.scale_y
        self.widget_root.scene_widget.matrix.post_scale(scale_x, scale_y)
        self.context.signal("refresh_scene", 0)

    def rotary_unstretch(self):
        """
        Rotary UnStretch of Scene based on values in "rotary/1"
        """
        r = self.context.get_context("rotary/1")
        scale_x = r.scale_x
        scale_y = r.scale_y
        self.widget_root.scene_widget.matrix.post_scale(1.0 / scale_x, 1.0 / scale_y)
        self.context.signal("refresh_scene", 0)

    def _signal_widget(self, widget, *args, **kwargs):
        """
        Calls the signal widget with the given args. Calls signal for the entire widget node tree.
        """
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
        """
        Called when node is added to parent. Notifying the scene as a whole.
        """
        pass

    def notify_added_child(self, child):
        """
        Called when a child is added to the tree. Notifies scene as a whole.
        """
        try:
            child.init(self.context)
        except AttributeError:
            pass

    def notify_removed_from_parent(self, parent):
        """
        Called when a widget is removed from it's parent. Notifies scene as a whole.
        """
        pass

    def notify_removed_child(self, child):
        """
        Called when a widget's child is removed. Notifies scene as a whole.
        """
        try:
            child.final(self.context)
        except AttributeError:
            pass

    def notify_moved_child(self, child):
        """
        Called when a widget is moved from one widget parent to another.
        """
        pass

    def draw(self, canvas):
        """
        Scene Draw routine to be called on paint when the _Buffer bitmap needs to be redrawn.
        """
        if self.widget_root is not None:
            self.widget_root.draw(canvas)

    def convert_scene_to_window(self, position):
        """
        Convert the scene space to the window space for a particular point.
        The position given in the scene, produces the position on the screen.
        """
        point = self.widget_root.scene_widget.matrix.point_in_matrix_space(position)
        return point[0], point[1]

    def convert_window_to_scene(self, position):
        """
        Convert the window space to the scene space for a particular point.
        The position given is the window pixel, produces the position within the scene.
        """
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
        """
        Iterates through the hit chain to find elements which respond to their hit() function that they are HITCHAIN_HIT
        and registers this within the hittable_elements list if they are arble to be hit at the current time. Given the
        dimensions of the widget and the current matrix within the widget tree.

        HITCHAIN_HIT means that this is a hit value and should the termination of this branch of the widget tree.
        HITCHAIN_DELEGATE means that this is not a hittable widget and should not receive mouse events.
        HITCHAIN_HIT_AND_DELEGATE means that this is a hittable widget, but other widgets within it might also matter.
        HITCHAIN_DELEGATE_AND_HIT means that other widgets in the tree should be checked first, but after those this
        widget should be checked.

        The hitchain is the current matrix and current widget in the order of depth.

        """
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
        """
        Processes the hittable_elements list and find which elements are hit at a given position.

        This gives the actual hits with regard to the position of the event.
        """
        self.hit_chain.clear()
        for current_widget, current_matrix in self.hittable_elements:
            try:
                hit_point = Point(current_matrix.point_in_inverse_space(position))
            except ZeroDivisionError:
                current_matrix.reset()
                # Some object is zero matrixed, reset it.
                return
            if current_widget.contains(hit_point.x, hit_point.y):
                self.hit_chain.append((current_widget, current_matrix))

    def event(self, window_pos, event_type=""):
        """
        Scene event code. Processes all the events for a particular mouse event bound in the ScenePanel.

        Many mousedown events trigger the specific start of the hitchain matching, and processes the given hitchain.
        Subsequent delegation of the events will be processed with regard to whether the matching event struck a
        particular widget. This permits a hit widget to get all further events.

        Responses to events are:
        RESPONSE_ABORT: Aborts any future mouse events within the sequence.
        RESPONSE_CONSUME: Consumes the event and prevents any event further in the hitchain from getting the event
        RESPONSE_CHAIN: Permit the event to move to the next event in the hitchain
        RESPONSE_DROP: Remove this item from the hitchain and continue to process the events. Future events will not
        consider the dropped element within the hitchain.
        """
        if window_pos is None:
            # Capture Lost
            for i, hit in enumerate(self.hit_chain):
                if hit is None:
                    continue  # Element was dropped.
                current_widget, current_matrix = hit
                current_widget.event(None, None, event_type)
            return
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
                previous_top_element = current_widget
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

    def cursor(self, cursor):
        """
        Routine to centralize and correct cursor info.
        @param cursor:
        @return:
        """
        if cursor == "sizing":
            new_cursor = wx.CURSOR_SIZING
        elif cursor in ("size_nw", "size_se"):
            new_cursor = wx.CURSOR_SIZENWSE
        elif cursor in ("size_sw", "size_ne"):
            new_cursor = wx.CURSOR_SIZENESW
        elif cursor in ("size_n", "size_s"):
            new_cursor = wx.CURSOR_SIZENS
        elif cursor in ("size_e", "size_w"):
            new_cursor = wx.CURSOR_SIZEWE
        elif cursor == "arrow":
            new_cursor = wx.CURSOR_ARROW
        else:
            new_cursor = wx.CURSOR_ARROW
            self.log("Invalid cursor.")
        if new_cursor != self._cursor:
            self._cursor = new_cursor
            self.gui.SetCursor(wx.Cursor(self._cursor))
            self.log("Cursor changed to %s" % cursor)

    def add_scenewidget(self, widget, properties=ORIENTATION_RELATIVE):
        """
        Delegate to the SceneSpaceWidget scene.
        """
        self.widget_root.scene_widget.add_widget(-1, widget, properties)

    def add_interfacewidget(self, widget, properties=ORIENTATION_RELATIVE):
        """
        Delegate to the SceneSpaceWidget interface.
        """
        self.widget_root.interface_widget.add_widget(-1, widget, properties)


class Widget(list):
    """
    Widgets are drawable, interaction objects within the scene. They have their own space, matrix, orientation, and
    processing of events.
    """

    def __init__(
        self,
        scene: "Scene",
        left: float = None,
        top: float = None,
        right: float = None,
        bottom: float = None,
        all: bool = False,
    ):
        """
        All produces a widget of infinite space rather than finite space.
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
        """
        Default hit state delegates to child-widgets within the current object.
        """
        return HITCHAIN_DELEGATE

    def draw(self, gc):
        """
        Widget.draw() routine which concat's the widgets matrix and call the process_draw() function.
        """
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
        """
        Overloaded function by derived widgets to process the drawing of this widget.
        """
        pass

    def contains(self, x, y=None):
        """
        Query as to whether the current point is contained within the current widget.
        """
        if y is None:
            y = x.y
            x = x.x
        return self.left <= x <= self.right and self.top <= y <= self.bottom

    def event(self, window_pos=None, space_pos=None, event_type=None):
        """
        Default event which simply chains the event to the next hittable object.
        """
        return RESPONSE_CHAIN

    def notify_added_to_parent(self, parent):
        """
        Widget notify that calls scene notify.
        """
        self.scene.notify_added_to_parent(parent)

    def notify_added_child(self, child):
        """
        Widget notify that calls scene notify.
        """
        self.scene.notify_added_child(child)

    def notify_removed_from_parent(self, parent):
        """
        Widget notify that calls scene notify.
        """
        self.scene.notify_removed_from_parent(parent)

    def notify_removed_child(self, child):
        """
        Widget notify that calls scene notify.
        """
        self.scene.notify_removed_child(child)

    def notify_moved_child(self, child):
        """
        Widget notify that calls scene notify.
        """
        self.scene.notify_moved_child(child)

    def add_widget(self, index=-1, widget=None, properties=0):
        """
        Add a widget to the current widget.

        Adds at the particular index according to the properties.

        The properties can be used to trigger particular layouts or properties for the added widget.
        """
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
        """
        Move the current widget and all child widgets.
        """
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
        """
        Loop the translation call to all child objects.
        """
        if self.properties & ORIENTATION_ABSOLUTE != 0:
            return  # Do not translate absolute oriented widgets.
        self.translate_self(dx, dy)
        for w in self:
            w.translate_loop(dx, dy)

    def translate_self(self, dx, dy):
        """
        Perform the local translation of the current widget
        """
        self.left += dx
        self.right += dx
        self.top += dy
        self.bottom += dy
        if self.parent is not None:
            self.notify_moved_child(self)

    def union_children_bounds(self, bounds=None):
        """
        Find the bounds of the current widget and all child widgets.
        """
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
        """
        Height of the current widget.
        """
        return self.bottom - self.top

    @property
    def width(self):
        """
        Width of the current widget.
        """
        return self.right - self.left

    def layout_by_orientation(self, widget, last, properties):
        """
        Perform specific layout based on the properties given.
        ORIENTATION_ABSOLUTE places the widget exactly in the scene.
        ORIENTATION_NO_BUFFER nullifies any buffer between objects being laid out.
        ORIENTATION_RELATIVE lays out the added widget relative to the parent.
        ORIENTATION_GRID lays out the added widget in a DIM_MASK grid.
        ORIENTATION_VERTICAL lays the added widget below the reference widget.
        ORIENTATION_HORIZONTAL lays the added widget to the right of the reference widget.
        ORIENTATION_CENTERED lays out the added widget and within the parent and all child centered.
        """
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
        """
        Centers the children of the current widget within the current widget.
        """
        child_bounds = self.union_children_bounds()
        dx = self.left - (child_bounds[0] + child_bounds[2]) / 2.0
        dy = self.top - (child_bounds[1] + child_bounds[3]) / 2.0
        if dx != 0 and dy != 0:
            for w in self:
                w.translate_loop(dx, dy)

    def center_widget(self, x, y=None):
        """
        Moves the current widget to center within the bounds of the children.
        """
        if y is None:
            y = x.y
            x = x.x
        child_bounds = self.union_children_bounds()
        cx = (child_bounds[0] + child_bounds[2]) / 2.0
        cy = (child_bounds[1] + child_bounds[3]) / 2.0
        self.translate(x - cx, y - cy)

    def set_position(self, x, y=None):
        """
        Sets the absolute position of this widget by moving it from its current position
        to given position.
        """
        if y is None:
            y = x.y
            x = x.x
        dx = x - self.left
        dy = y - self.top
        self.translate(dx, dy)

    def remove_all_widgets(self):
        """
        Remove all widgets from the current widget.
        """
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
        """
        Remove the given widget from being a child of the current widget.
        """
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
        """
        Sets the given widget at the index to replace the child currently at the position of that widget.
        """
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
        """
        Notification of a changed matrix.
        """
        pass

    def scene_matrix_reset(self):
        """
        Resets the scene matrix.
        """
        self.matrix.reset()
        self.on_matrix_change()

    def scene_post_scale(self, sx, sy=None, ax=0, ay=0):
        """
        Adds a post_scale to the matrix.
        """
        self.matrix.post_scale(sx, sy, ax, ay)
        self.on_matrix_change()

    def scene_post_pan(self, px, py):
        """
        Adds a post_pan to the matrix.
        """
        self.matrix.post_translate(px, py)
        self.on_matrix_change()

    def scene_post_rotate(self, angle, rx=0, ry=0):
        """
        Adds a post_rotate to the matrix.
        """
        self.matrix.post_rotate(angle, rx, ry)
        self.on_matrix_change()

    def scene_pre_scale(self, sx, sy=None, ax=0, ay=0):
        """
        Adds a pre_scale to the matrix()
        """
        self.matrix.pre_scale(sx, sy, ax, ay)
        self.on_matrix_change()

    def scene_pre_pan(self, px, py):
        """
        Adds a pre_pan to the matrix()
        """
        self.matrix.pre_translate(px, py)
        self.on_matrix_change()

    def scene_pre_rotate(self, angle, rx=0, ry=0):
        """
        Adds a pre_rotate to the matrix()
        """
        self.matrix.pre_rotate(angle, rx, ry)
        self.on_matrix_change()

    def get_scale_x(self):
        """
        Gets the scale_x of the current matrix
        """
        return self.matrix.value_scale_x()

    def get_scale_y(self):
        """
        Gets the scale_y of the current matrix
        """
        return self.matrix.value_scale_y()

    def get_skew_x(self):
        """
        Gets the skew_x of the current matrix()
        """
        return self.matrix.value_skew_x()

    def get_skew_y(self):
        """
        Gets the skew_y of the current matrix()
        """
        return self.matrix.value_skew_y()

    def get_translate_x(self):
        """
        Gets the translate_x of the current matrix()
        """
        return self.matrix.value_trans_x()

    def get_translate_y(self):
        """
        Gets the translate_y of the current matrix()
        """
        return self.matrix.value_trans_y()


class SceneSpaceWidget(Widget):
    """
    SceneSpaceWidget contains two sections:
    Interface: Drawn on top, uses no matrix.
    Scene: Drawn at a particular scale relative to the zoom-pan scene.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self._view = None
        self._frame = None
        self.aspect = False

        self.interface_widget = Widget(scene)
        self.scene_widget = Widget(scene)
        self.add_widget(-1, self.interface_widget)
        self.add_widget(-1, self.scene_widget)
        self.last_position = None
        self._previous_zoom = None
        self._placement_event = None
        self._placement_event_type = None

    def hit(self):
        """
        If any event captures the events they take priority. But, if nothing is hit, then the events
        should be dealt with here. These are mostly zoom and pan events.
        """
        return HITCHAIN_DELEGATE_AND_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        """
        Process the zooming and panning of otherwise unhit-widget events.

        If nothing was otherwise hit by the event, we process the scene manipulation events
        """
        if event_type == "hover":
            return RESPONSE_CHAIN
        if self.aspect:
            return RESPONSE_CONSUME
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
        elif event_type == "lost":
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
            if self._previous_zoom is not None:
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

    def set_view(self, x, y, w, h, preserve_aspect=None):
        self._view = Viewbox(
            "%d %d %d %d" % (x, y, w, h),
            preserve_aspect,
        )
        self.aspect_matrix()

    def set_frame(self, x, y, w, h):
        self._frame = Viewbox("%d %d %d %d" % (x, y, w, h))
        self.aspect_matrix()

    def set_aspect(self, aspect=True):
        self.aspect = aspect
        self.aspect_matrix()

    def aspect_matrix(self):
        """
        Specifically view the scene with the given Viewbox.
        """
        if self._frame and self._view and self.aspect:
            self.scene_widget.matrix = Matrix(self._view.transform(self._frame))

    def focus_position_scene(self, scene_point, scene_size):
        """
        Focus on the specific point within the scene.
        """
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
