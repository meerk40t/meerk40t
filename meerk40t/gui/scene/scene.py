import platform
import threading
import time

import wx

from meerk40t.core.elements.element_types import elem_nodes
from meerk40t.gui.laserrender import (
    DRAW_MODE_ANIMATE,
    DRAW_MODE_FLIPXY,
    DRAW_MODE_INVERT,
    DRAW_MODE_REFRESH,
)
from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_DELEGATE,
    HITCHAIN_DELEGATE_AND_HIT,
    HITCHAIN_HIT,
    HITCHAIN_HIT_AND_DELEGATE,
    HITCHAIN_PRIORITY_HIT,
    ORIENTATION_RELATIVE,
    RESPONSE_ABORT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.scene.scenespacewidget import SceneSpaceWidget
from meerk40t.gui.wxutils import get_matrix_scale
from meerk40t.kernel import Job, Module
from meerk40t.svgelements import Matrix, Point

_reused_identity_widget = Matrix()
XCELLS = 15
YCELLS = 15

TYPE_BOUND = 0
TYPE_POINT = 1
TYPE_MIDDLE = 2
TYPE_CENTER = 3
TYPE_GRID = 4
TYPE_MIDDLE_SMALL = 5


class SceneToast:
    """
    SceneToast is drawn directly by the Scene. It creates a text message in a box that animates a fade.
    """

    def __init__(self, scene, left, top, right, bottom):
        self.scene = scene
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.countdown = 0
        self.message = None
        self.token = None

        self.brush = wx.Brush()
        self.pen = wx.Pen()
        self.font = wx.Font()
        self.brush_color = wx.Colour()
        self.pen_color = wx.Colour()
        self.font_color = wx.Colour()

        self.pen.SetWidth(10)
        self.text_height = float("inf")
        self.text_width = float("inf")

        self.alpha = None
        self.set_alpha(255)

    def tick(self):
        """
        Each tick reduces countdown by 1. Once countdown is below 20 we call requests for animation.
        @return:
        """
        self.countdown -= 1
        if self.countdown <= 20:
            self.scene.invalidate(
                self.left - 10,
                self.top - 10,
                self.right + 10,
                self.bottom + 10,
                animate=True,
            )
        if self.countdown <= 0:
            self.scene.invalidate(
                self.left - 10,
                self.top - 10,
                self.right + 10,
                self.bottom + 10,
                animate=False,
            )
            # self.scene.request_refresh()
            self.message = None
            self.token = None
        return self.countdown > 0

    def set_alpha(self, alpha):
        """
        We set the alpha for all the colors.

        @param alpha:
        @return:
        """
        if alpha != self.alpha:
            self.alpha = alpha
            self.brush_color.SetRGBA(0xFFFFFF | alpha << 24)
            self.pen_color.SetRGBA(0x70FF70 | alpha << 24)
            self.font_color.SetRGBA(0x000000 | alpha << 24)
            self.brush.SetColour(self.brush_color)
            self.pen.SetColour(self.pen_color)

    def draw(self, gc: wx.GraphicsContext):
        if not self.message:
            return
        alpha = 255
        if self.countdown <= 20:
            alpha = int(self.countdown * 12.5)
        self.set_alpha(alpha)

        width = self.right - self.left
        height = self.bottom - self.top
        text_size = height

        while self.text_height > height or self.text_width > width:
            # If we do not fit in the box, decrease size
            text_size *= 0.9
            try:
                self.font.SetFractionalPointSize(text_size)
            except AttributeError:
                self.font.SetPointSize(int(text_size))
            gc.SetFont(self.font, self.font_color)
            self.text_width, self.text_height = gc.GetTextExtent(self.message)
        if text_size == height:
            gc.SetFont(self.font, self.font_color)
        gc.SetPen(self.pen)
        gc.SetBrush(self.brush)
        gc.DrawRectangle(
            self.left, self.top, self.right - self.left, self.bottom - self.top
        )

        toast_x = self.left + (width - self.text_width) / 2.0
        toast_y = self.top
        gc.DrawText(self.message, toast_x, toast_y)

    def start_threaded(self):
        """
        First start of threaded animate. Refresh to draw.
        @return:
        """
        self.scene.request_refresh()

    def stop_threaded(self):
        """
        Stop of threaded animate. Unset text dims and delete the toast.
        @return:
        """
        self.scene._toast = None
        self.text_height = float("inf")
        self.text_width = float("inf")

    def set_message(self, message, token=-1, duration=100):
        """
        Sets the message. If the token is different, we reset the text position.

        We always reset the duration.

        @param message:
        @param token:
        @param duration:
        @return:
        """
        if token != self.token or token == -1:
            self.text_height = float("inf")
            self.text_width = float("inf")
        self.message = message
        self.token = token
        self.countdown = duration


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

    def __init__(self, context, path, gui, pane=None, **kwargs):
        Module.__init__(self, context, path)
        Job.__init__(
            self,
            job_name=f"Scene-{path}",
            process=self.refresh_scene,
            conditional=lambda: self.screen_refresh_is_requested,
            run_main=True,
        )
        self.stack = []

        # Scene lock is used for widget structure modification and scene drawing.
        self.scene_lock = threading.RLock()

        self.log = context.channel("scene")
        self.log_events = context.channel("scene-events")
        self.gui = gui
        self.pane = pane
        self.hittable_elements = list()
        self.hit_chain = list()
        self.widget_root = None
        self.push_stack(SceneSpaceWidget(self))

        self.interval = 1.0 / 60.0  # 60fps
        self.last_position = None
        self._down_start_time = None
        self._down_start_pos = None
        self._cursor = None
        self.suppress_changes = True

        self.colors = self.context.colors

        self.screen_refresh_is_requested = True
        self.clip = wx.Rect(0, 0, 0, 0)

        self.background_brush = wx.Brush(self.colors.color_background)
        self._hasbackgrounds = {}
        self._backgrounds = {}
        # If set this color will be used for the scene background (used during burn)
        self.overrule_background = None

        self._animating = list()
        self._animate_lock = threading.Lock()
        self._adding_widgets = list()
        self._animate_job = Job(
            self._animate_scene,
            job_name=f"Animate-Scene{path}",
            run_main=True,
            interval=1.0 / 60.0,
        )
        self._toast = None
        # Snap information
        self.snap_display_points = None
        self.snap_attraction_points = None

    @property
    def has_background(self):
        devlabel = self.context.device.label
        if devlabel not in self._hasbackgrounds:
            self._hasbackgrounds[devlabel] = False
        return self._hasbackgrounds[devlabel]

    @has_background.setter
    def has_background(self, value):
        devlabel = self.context.device.label
        self._hasbackgrounds[devlabel] = value
        if not value:
            self.active_background = None

    @property
    def active_background(self):
        devlabel = self.context.device.label
        if devlabel not in self._hasbackgrounds:
            self._backgrounds[devlabel] = None
        return self._backgrounds[devlabel]

    @active_background.setter
    def active_background(self, value):
        devlabel = self.context.device.label
        self._backgrounds[devlabel] = value

    def module_open(self, *args, **kwargs):
        context = self.context
        context.setting(int, "draw_mode", 0)
        context.setting(bool, "mouse_zoom_invert", False)
        context.setting(bool, "mouse_pan_invert", False)
        context.setting(bool, "mouse_wheel_pan", False)
        context.setting(float, "zoom_factor", 0.1)
        context.setting(float, "pan_factor", 25.0)
        context.setting(int, "fps", 40)
        if context.fps <= 0:
            context.fps = 60
        self.interval = 1.0 / float(context.fps)
        self.commit()

    def commit(self):
        context = self.context
        self._init_widget(self.widget_root, context)

    def module_close(self, *args, **kwargs):
        self._final_widget(self.widget_root, self.context)
        self.scene_lock.acquire()  # calling shutdown live locks here since it's already shutting down.
        self.context.unschedule(self)

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

    def push_stack(self, widget):
        if self.widget_root is not None:
            try:
                widget.init(self.context)
            except AttributeError:
                pass
            self.stack.append(self.widget_root)
        self.widget_root = widget

    def pop_stack(self):
        widget = self.stack.pop()
        try:
            self.widget_root.final(self.context)
        except AttributeError:
            pass
        self.widget_root = widget

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

    def invalidate(self, min_x, min_y, max_x, max_y, animate=False):
        self.clip.Union((min_x, min_y, max_x - min_x, max_y - min_y))
        if animate:
            self.request_refresh_for_animation()
        else:
            self.request_refresh()

    def animate(self, widget):
        with self._animate_lock:
            if widget not in self._adding_widgets:
                self._adding_widgets.append(widget)
        if self.log:
            self.log("Start Animation...")
        self.context.schedule(self._animate_job)

    def _animate_scene(self, *args, **kwargs):
        if self.log:
            self.log("Animating Scene...")
        if self._adding_widgets:
            with self._animate_lock:
                animate_add = list(self._adding_widgets)
                self._adding_widgets.clear()
            for widget in animate_add:
                self._animating.append(widget)
                try:
                    widget.start_threaded()
                except AttributeError:
                    pass
        if self._animating:
            for idx in range(len(self._animating) - 1, -1, -1):
                widget = self._animating[idx]
                try:
                    more = widget.tick()
                    if not more:
                        try:
                            widget.stop_threaded()
                        except AttributeError:
                            pass
                        del self._animating[idx]
                except AttributeError:
                    pass
        if not self._animating:
            self._animate_job.cancel()
            if self.log:
                self.log("Removing Animation...")

    def refresh_scene(self, *args, **kwargs):
        """
        Called by the Scheduler at a given the specified framerate.
        Called in the UI thread.
        """
        if not self.screen_refresh_is_requested:
            return
        if self.scene_lock.acquire(timeout=0.2):
            try:
                self._update_buffer_ui_thread()
                self.gui.Refresh()
                self.gui.Update()
            except RuntimeError:
                # May hit runtime error.
                pass
            self.screen_refresh_is_requested = False
            self.scene_lock.release()
        else:
            self.screen_refresh_is_requested = False

    def _update_buffer_ui_thread(self):
        """Performs redrawing of the data in the UI thread."""
        dm = self.context.draw_mode
        buf = self.gui.scene_buffer
        if buf is None or buf.GetSize() != self.gui.ClientSize or not buf.IsOk():
            self.gui.set_buffer()
            buf = self.gui.scene_buffer
        dc = wx.MemoryDC()
        if self.clip.width != 0 and self.clip.height != 0:
            dc.SetClippingRegion(self.clip)
            self.clip.SetX(0)
            self.clip.SetY(0)
            self.clip.SetWidth(0)
            self.clip.SetHeight(0)

        dc.SelectObject(buf)
        if self.overrule_background is None:
            self.background_brush.SetColour(self.colors.color_background)
        else:
            self.background_brush.SetColour(self.overrule_background)
        dc.SetBackground(self.background_brush)
        dc.Clear()
        w, h = dc.Size
        if dm & DRAW_MODE_FLIPXY != 0:
            dc.SetUserScale(-1, -1)
            dc.SetLogicalOrigin(w, h)
        gc = wx.GraphicsContext.Create(dc)
        gc.dc = dc
        gc.Size = dc.Size

        font = wx.Font(14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        gc.SetFont(font, wx.BLACK)
        self.draw(gc)
        if dm & DRAW_MODE_INVERT != 0:
            dc.Blit(0, 0, w, h, dc, 0, 0, wx.SRC_INVERT)
        gc.Destroy()
        dc.SelectObject(wx.NullBitmap)
        del gc.dc
        del dc

    def toast(self, message, token=-1):
        if self._toast is None:
            self._toast = SceneToast(
                self, self.x(0.1), self.y(0.8), self.x(0.9), self.y(0.9)
            )
            self._toast.set_message(message, token)
            self.animate(self._toast)
        else:
            self._toast.set_message(message, token)
            self.animate(self._toast)

    def x(self, v):
        width, height = self.gui.ClientSize
        return width * v

    def y(self, v):
        width, height = self.gui.ClientSize
        return height * v

    def cell(self):
        width, height = self.gui.ClientSize
        return min(width / XCELLS, height / YCELLS)

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
        Called when a widget is removed from its parent. Notifies scene as a whole.
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
        if self.widget_root is not None and not self.suppress_changes:
            self.widget_root.draw(canvas)
            if self.log:
                self.log("Redraw Canvas")
        if self._toast is not None:
            self._toast.draw(canvas)

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
        self.rebuild_hit_chain(self.widget_root, _reused_identity_widget)

    def rebuild_hit_chain(self, current_widget, current_matrix=None):
        """
        Iterates through the hit chain to find elements which respond to their hit() function that they are HITCHAIN_HIT
        and registers this within the hittable_elements list if they are able to hit at the current time. Given the
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
        elif response == HITCHAIN_PRIORITY_HIT:
            self.hittable_elements.insert(0, (current_widget, matrix_within_scene))
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

    def event(
        self, window_pos, event_type="", nearest_snap=None, modifiers=None, keycode=None
    ):
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

        Returns a flag whether the event was consumed by someone
        """
        if self.log_events:
            self.log_events(
                f"{event_type}: {str(window_pos)} {str(nearest_snap)} {str(modifiers)} {str(keycode)}"
            )

        if window_pos is None:
            # Capture Lost
            for i, hit in enumerate(self.hit_chain):
                if hit is None:
                    continue  # Element was dropped.
                current_widget, current_matrix = hit
                current_widget.event(
                    window_pos=None,
                    scene_pos=None,
                    event_type=event_type,
                    nearest_snap=None,
                    modifiers=None,
                )
            return False
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
        previous_top_element = None
        try:
            idx = 0
            while idx < len(self.hit_chain):
                if not self.hit_chain[idx][0].transparent:
                    previous_top_element = self.hit_chain[idx][0]
                    break
                idx += 1

        except (IndexError, TypeError):
            pass

        if event_type in (
            "key_down",
            "key_up",
        ):
            # print("Keyboard-Event raised: %s" % event_type)
            self.rebuild_hittable_chain()
            for current_widget, current_matrix in self.hittable_elements:
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
                response = current_widget.event(
                    window_pos=window_pos,
                    space_pos=space_pos,
                    event_type=event_type,
                    nearest_snap=nearest_snap,
                    modifiers=modifiers,
                    keycode=keycode,
                )

                if response == RESPONSE_ABORT:
                    self.hit_chain.clear()
                    # print (f"Response abort of {event_type}, {keycode}/{modifiers} by {current_widget}")
                    return True
                elif response == RESPONSE_CONSUME:
                    # if event_type in ("leftdown", "middledown", "middleup", "leftup", "move", "leftclick"):
                    #      widgetname = type(current_widget).__name__
                    #      print("Event %s was consumed by %s" % (event_type, widgetname))
                    # print (f"Response consume of {event_type}, {keycode}/{modifiers} by {current_widget}")
                    return True
                elif response == RESPONSE_CHAIN:
                    continue
                elif response == RESPONSE_DROP:
                    # self.hit_chain[i] = None
                    continue
                #
                # if response == RESPONSE_ABORT:
                #     self.hit_chain.clear()
            return False

        if event_type in (
            "leftdown",
            "middledown",
            "rightdown",
            "wheeldown",
            "wheelup",
            "hover",
        ):
            self._down_start_time = time.time()
            self._down_start_pos = window_pos
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
                    if self.log_events:
                        self.log_events(f"Converted hover_end: {str(window_pos)}")
                    previous_top_element.event(
                        window_pos=window_pos,
                        space_pos=space_pos,
                        event_type="hover_end",
                        nearest_snap=None,
                        modifiers=modifiers,
                        keycode=keycode,
                    )
                current_widget.event(
                    window_pos=window_pos,
                    space_pos=space_pos,
                    event_type="hover_start",
                    nearest_snap=None,
                    modifiers=modifiers,
                    keycode=keycode,
                )
                if self.log_events:
                    self.log_events(f"Converted hover_start: {str(window_pos)}")
                previous_top_element = current_widget
            if (
                event_type == "leftup"
                and time.time() - self._down_start_time <= 0.30
                and abs(complex(*window_pos[:2]) - complex(*self._down_start_pos[:2]))
                < 50
            ):  # Anything within 0.3 seconds will be converted to a leftclick
                response = current_widget.event(
                    window_pos=window_pos,
                    space_pos=space_pos,
                    event_type="leftclick",
                    nearest_snap=nearest_snap,
                    modifiers=modifiers,
                    keycode=keycode,
                )
                if self.log_events:
                    self.log_events(f"Converted leftclick: {str(window_pos)}")
            elif event_type == "leftup":
                if self.log_events:
                    self.log_events(
                        f"Did not convert to click, {time.time() - self._down_start_time}"
                    )
                response = current_widget.event(
                    window_pos=window_pos,
                    space_pos=space_pos,
                    event_type=event_type,
                    nearest_snap=nearest_snap,
                    modifiers=modifiers,
                    keycode=keycode,
                )
                # print ("Leftup called for widget #%d" % i )
                # print (response)
            else:
                response = current_widget.event(
                    window_pos=window_pos,
                    space_pos=space_pos,
                    event_type=event_type,
                    nearest_snap=nearest_snap,
                    modifiers=modifiers,
                    keycode=keycode,
                )

            ##################
            # PROCESS RESPONSE
            ##################
            if type(response) is tuple:
                # print (f"Nearest snap provided")
                # We get two additional parameters which are the screen location of the nearest snap point
                params = response[1:]
                response = response[0]
                if len(params) > 1:
                    new_x_space = params[0]
                    new_y_space = params[1]
                    new_x = window_pos[0]
                    new_y = window_pos[1]

                    sdx = new_x_space - space_pos[0]
                    if current_matrix is not None and not current_matrix.is_identity():
                        sdx *= get_matrix_scale(current_matrix)
                    snap_x = window_pos[0] + sdx
                    sdy = new_y_space - space_pos[1]
                    if current_matrix is not None and not current_matrix.is_identity():
                        sdy *= current_matrix.value_scale_y()
                    # print("Shift x by %.1f pixel (%.1f), Shift y by %.1f pixel (%.1f)" % (sdx, odx, sdy, ody))
                    snap_y = window_pos[1] + sdy

                    # dx = new_x - self.last_position[0]
                    # dy = new_y - self.last_position[1]
                    if snap_x is None:
                        nearest_snap = None
                    else:
                        # We are providing the space and screen coordinates
                        snap_space = current_matrix.point_in_inverse_space(
                            (snap_x, snap_y)
                        )
                        nearest_snap = (
                            snap_space[0],
                            snap_space[1],
                            snap_x,
                            snap_y,
                        )
                        self.pane.last_snap = nearest_snap

            if response == RESPONSE_ABORT:
                self.hit_chain.clear()
                return True
            elif response == RESPONSE_CONSUME:
                # if event_type in ("leftdown", "middledown", "middleup", "leftup", "move", "leftclick"):
                #      widgetname = type(current_widget).__name__
                #      print("Event %s was consumed by %s" % (event_type, widgetname))
                return True
            elif response == RESPONSE_CHAIN:
                continue
            elif response == RESPONSE_DROP:
                self.hit_chain[i] = None
                continue
            else:
                break
        return False

    def cursor(self, cursor, always=False):
        """
        Routine to centralize and correct cursor info.
        @param cursor: Changed cursor
        @param always: Force cursor change
        @return:
        """
        if cursor == "sizing":
            new_cursor = wx.CURSOR_SIZING
        elif cursor in ("size_nw", "size_se"):
            new_cursor = wx.CURSOR_SIZENWSE
        elif cursor in ("size_sw", "size_ne"):
            new_cursor = wx.CURSOR_SIZENESW
        elif cursor in ("size_n", "size_s", "skew_y"):
            new_cursor = wx.CURSOR_SIZENS
        elif cursor in ("size_e", "size_w", "skew_x"):
            new_cursor = wx.CURSOR_SIZEWE
        elif cursor == "arrow":
            new_cursor = wx.CURSOR_ARROW
        elif cursor == "cross":
            new_cursor = wx.CROSS_CURSOR
        elif cursor == "rotate1":
            new_cursor = wx.CURSOR_CROSS
        elif cursor == "rotate2":
            new_cursor = wx.CURSOR_CROSS
        elif cursor == "rotmove":
            new_cursor = wx.CURSOR_HAND
        elif cursor == "reference":
            new_cursor = wx.CURSOR_BULLSEYE
        elif cursor == "text":
            new_cursor = wx.CURSOR_IBEAM
        else:
            new_cursor = wx.CURSOR_ARROW
            self.log("Invalid cursor.")
        if platform.system() == "Linux":
            if cursor == "sizing":
                new_cursor = wx.CURSOR_SIZENWSE
            elif cursor in ("size_nw", "size_se"):
                new_cursor = wx.CURSOR_SIZING
            elif cursor in ("size_sw", "size_ne"):
                new_cursor = wx.CURSOR_SIZING
        if new_cursor != self._cursor or always:
            self._cursor = new_cursor
            self.gui.scene_panel.SetCursor(wx.Cursor(self._cursor))
            self.log(f"Cursor changed to {cursor}")

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

    # --- Centralised snap_point calculation
    def _calculate_snap_points(self, my_x, my_y, length):
        """
        Recalculate the snap element attraction points

        @param length:
        @return:
        """
        for pts in self.snap_attraction_points:
            if self.pane.modif_active:
                if pts[3]:
                    # No snap points for emphasized objects.
                    continue
            if abs(pts[0] - my_x) <= length and abs(pts[1] - my_y) <= length:
                self.snap_display_points.append([pts[0], pts[1], pts[2]])

    def _calculate_grid_points(self, my_x, my_y, length):
        """
        Recalculate the local grid points

        @param length:
        @return:
        """
        for pts in self.pane.grid.grid_points:
            if abs(pts[0] - my_x) <= length and abs(pts[1] - my_y) <= length:
                self.snap_display_points.append([pts[0], pts[1], TYPE_GRID])

    def _calculate_attraction_points(self):
        """
        Looks at all elements (all_points=True) or at non-selected elements (all_points=False) and identifies all
        attraction points (center, corners, sides)
        """
        self.context.elements.set_start_time("attr_calc_points")
        self.snap_attraction_points = []  # Clear all
        translation_table = {
            "bounds top_left": TYPE_BOUND,
            "bounds top_right": TYPE_BOUND,
            "bounds bottom_left": TYPE_BOUND,
            "bounds bottom_right": TYPE_BOUND,
            "bounds center_center": TYPE_CENTER,
            "bounds top_center": TYPE_MIDDLE,
            "bounds bottom_center": TYPE_MIDDLE,
            "bounds center_left": TYPE_MIDDLE,
            "bounds center_right": TYPE_MIDDLE,
            "endpoint": TYPE_POINT,
            "point": TYPE_POINT,
            "midpoint": TYPE_MIDDLE_SMALL,
        }

        for e in self.context.elements.flat(types=elem_nodes):
            emph = e.emphasized
            if hasattr(e, "points"):
                for pt in e.points:
                    try:
                        pt_type = translation_table[pt[2]]
                    except:
                        print(f"Unknown type: {pt[2]}")
                        pt_type = TYPE_POINT
                    self.snap_attraction_points.append([pt[0], pt[1], pt_type, emph])

        self.context.elements.set_end_time(
            "attr_calc_points",
            message=f"points added={len(self.snap_attraction_points)}",
        )

    def calculate_display_points(self, my_x, my_y, snap_points, snap_grid):
        """
        Recalculate the points that need to be displayed for the user.

        @return:
        """
        self.snap_display_points = []
        if my_x is None:
            return
        if self.snap_attraction_points is None and snap_points:
            self._calculate_attraction_points()

        matrix = self.widget_root.scene_widget.matrix
        length = self.context.show_attract_len / get_matrix_scale(matrix)

        if snap_points and self.snap_attraction_points:
            self._calculate_snap_points(my_x, my_y, length)

        if snap_grid and self.pane.grid.grid_points:
            self._calculate_grid_points(my_x, my_y, length)

    def calculate_snap(self, my_x, my_y):
        """
        Calculates the nearest_snap
        """
        # Loop through display points, find closest.
        res_x = None
        res_y = None
        if self.snap_display_points and my_x is not None:
            # Has to be lower than the action threshold
            min_delta = float("inf")
            new_x = None
            new_y = None
            for pt in self.snap_display_points:
                dx = pt[0] - my_x
                dy = pt[1] - my_y
                delta = dx * dx + dy * dy
                if delta < min_delta:
                    new_x = pt[0]
                    new_y = pt[1]
                    min_delta = delta
            if new_x is not None:
                matrix = self.widget_root.scene_widget.matrix
                pixel = self.context.action_attract_len / get_matrix_scale(matrix)
                if abs(new_x - my_x) <= pixel and abs(new_y - my_y) <= pixel:
                    # If the distance is small enough: snap.
                    res_x = new_x
                    res_y = new_y
        return res_x, res_y

    def get_snap_point(self, sx, sy, modifiers):
        resx = sx
        resy = sy
        sgrid = self.context.snap_grid
        spoints = self.context.snap_points
        if "shift" in modifiers:
            sgrid = not sgrid
            spoints = False
        if sgrid or spoints:
            if "shift" in modifiers:
                # Need to recalculate
                self.reset_snap_attraction()
            self.calculate_display_points(sx, sy, spoints, sgrid)
            nx, ny = self.calculate_snap(sx, sy)
            if nx is not None:
                resx = nx
                resy = ny
            if "shift" in modifiers:
                # Need to recalculate again
                self.reset_snap_attraction()
        return resx, resy

    def reset_snap_attraction(self):
        self.snap_attraction_points = None
