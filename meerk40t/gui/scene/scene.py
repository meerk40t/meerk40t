from distutils.log import debug
import platform
import threading
import time
from math import isinf, isnan, tau

# from weakref import ref

import wx

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
    ORIENTATION_RELATIVE,
    RESPONSE_ABORT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
    RESPONSE_CHGPOS,
)
from meerk40t.gui.scene.scenespacewidget import SceneSpaceWidget
from meerk40t.gui.zmatrix import ZMatrix
from meerk40t.kernel import Job, Module
from meerk40t.svgelements import Matrix, Point, Viewbox, Polygon, Circle, Ellipse, Arc
from meerk40t.core.units import Length

# TODO: _buffer can be updated partially rather than fully rewritten, especially with some layering.


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
        self.log_events = context.channel("scene-events")
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
        self._reference = None  # Reference Object
        self.attraction_points = []  # Clear all
        self.compute = True

        self.screen_refresh_is_requested = True
        self.background_brush = wx.Brush("Grey")
        self.magnet_x = []
        self.magnet_y = []
        self.magnet_attraction = (
            2  # 0 off, 1..x increasing strength (quadratic behaviour)
        )
        self.magnet_attract_x = True  # Shall the X-Axis be affected
        self.magnet_attract_y = True  # Shall the Y-Axis be affected
        self.magnet_attract_c = True  # Shall the center be affected

        self.tick_distance = 0
        self.auto_tick = False  # by definition do not auto_tick
        # Variables for an amended position
        self.new_x_space = None
        self.new_y_space = None

    def clear_magnets(self):
        self.magnet_x = []
        self.magnet_y = []
        self.context.signal("magnets", False)

    def toggle_x_magnet(self, x_value):
        prev = self.has_magnets()
        if x_value in self.magnet_x:
            self.magnet_x.remove(x_value)
            # print("Remove x magnet for %.1f" % x_value)
            now = self.has_magnets()
        else:
            self.magnet_x += [x_value]
            # print("Add x magnet for %.1f" % x_value)
            now = True
        if prev != now:
            self.context.signal("magnets", now)

    def toggle_y_magnet(self, y_value):
        prev = self.has_magnets()
        if y_value in self.magnet_y:
            self.magnet_y.remove(y_value)
            # print("Remove y magnet for %.1f" % y_value)
            now = self.has_magnets()
        else:
            self.magnet_y += [y_value]
            now = True
            # print("Add y magnet for %.1f" % y_value)
        if prev != now:
            self.context.signal("magnets", now)

    def magnet_attracted_x(self, x_value, useit):
        delta = float("inf")
        x_val = None
        if useit:
            for mag_x in self.magnet_x:
                if abs(x_value - mag_x) < delta:
                    delta = abs(x_value - mag_x)
                    x_val = mag_x
        return delta, x_val

    def magnet_attracted_y(self, y_value, useit):
        delta = float("inf")
        y_val = None
        if useit:
            for mag_y in self.magnet_y:
                if abs(y_value - mag_y) < delta:
                    delta = abs(y_value - mag_y)
                    y_val = mag_y
        return delta, y_val

    def revised_magnet_bound(self, bounds=None):

        dx = 0
        dy = 0
        if self.has_magnets() and self.magnet_attraction > 0:
            if self.tick_distance > 0:
                s = "{amount}{units}".format(
                    amount=self.tick_distance, units=self.context.units_name
                )
                len_tick = float(Length(s))
                # Attraction length is 1/3, 4/3, 9/3 of a grid-unit
                # fmt: off
                attraction_len = 1 / 3 * self.magnet_attraction * self.magnet_attraction * len_tick

                # print("Attraction len=%s, attract=%d, alen=%.1f, tlen=%.1f, factor=%.1f" % (s, self.magnet_attraction, attraction_len, len_tick, attraction_len / len_tick ))
                # fmt: on
            else:
                attraction_len = float(Length("1mm"))

            delta_x1, x1 = self.magnet_attracted_x(bounds[0], self.magnet_attract_x)
            delta_x2, x2 = self.magnet_attracted_x(bounds[2], self.magnet_attract_x)
            delta_x3, x3 = self.magnet_attracted_x(
                (bounds[0] + bounds[2]) / 2, self.magnet_attract_c
            )
            delta_y1, y1 = self.magnet_attracted_y(bounds[1], self.magnet_attract_y)
            delta_y2, y2 = self.magnet_attracted_y(bounds[3], self.magnet_attract_y)
            delta_y3, y3 = self.magnet_attracted_y(
                (bounds[1] + bounds[3]) / 2, self.magnet_attract_c
            )
            if delta_x3 < delta_x1 and delta_x3 < delta_x2:
                if delta_x3 < attraction_len:
                    if not x3 is None:
                        dx = x3 - (bounds[0] + bounds[2]) / 2
                        # print("X Take center , x=%.1f, dx=%.1f" % ((bounds[0] + bounds[2]) / 2, dx)
            elif delta_x1 < delta_x2 and delta_x1 < delta_x3:
                if delta_x1 < attraction_len:
                    if not x1 is None:
                        dx = x1 - bounds[0]
                        # print("X Take left side, x=%.1f, dx=%.1f" % (bounds[0], dx))
            elif delta_x2 < delta_x1 and delta_x2 < delta_x3:
                if delta_x2 < attraction_len:
                    if not x2 is None:
                        dx = x2 - bounds[2]
                        # print("X Take right side, x=%.1f, dx=%.1f" % (bounds[2], dx))
            if delta_y3 < delta_y1 and delta_y3 < delta_y2:
                if delta_y3 < attraction_len:
                    if not y3 is None:
                        dy = y3 - (bounds[1] + bounds[3]) / 2
                        # print("Y Take center , x=%.1f, dx=%.1f" % ((bounds[1] + bounds[3]) / 2, dy))
            elif delta_y1 < delta_y2 and delta_y1 < delta_y3:
                if delta_y1 < attraction_len:
                    if not y1 is None:
                        dy = y1 - bounds[1]
                        # print("Y Take top side, y=%.1f, dy=%.1f" % (bounds[1], dy))
            elif delta_y2 < delta_y1 and delta_y2 < delta_y3:
                if delta_y2 < attraction_len:
                    if not y2 is None:
                        dy = y2 - bounds[3]
                        # print("Y Take bottom side, y=%.1f, dy=%.1f" % (bounds[3], dy))

        return dx, dy

    def calculate_attraction_points(self):
        """
        Looks at all elements (all_points=True) or at non-selected elements (all_points=False) and identifies all
        attraction points (center, corners, sides)
        """
        from time import time

        start_time = time()
        type_point = 1
        type_middle = 2
        type_center = 3
        self.attraction_points = []  # Clear all

        for e in self.context.elements.flat(types=("elem",)):
            obj = e.object
            bb = e.bounds
            emph = e.emphasized
            self.attraction_points.append(
                [(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, type_center, emph]
            )
            has_segments = False
            try:
                segm = obj.segments(True)
                has_segments = True
            except AttributeError:
                # print("Segments exited with Attribute-error")
                pass
            if has_segments:
                ex = None
                ey = None
                sx = float("inf")
                sy = float("inf")
                ct = 0
                for s in segm:
                    ct += 1
                    xs = [p.x for p in s if p is not None]
                    ys = [p.y for p in s if p is not None]
                    for i in range(len(xs)):
                        # print("Segment #%d-%d: %.1f, %.1f" % (ct, i, xs[i], ys[i]))
                        sx = xs[i]
                        sy = ys[i]
                        add_it = True
                        if not ex is None:
                            if sx == ex and sy == ey:
                                add_it = False
                        if add_it:
                            # print("Added pt")
                            self.attraction_points.append([sx, sy, type_point, emph])
                            if not ex is None:
                                # print("Added middle")
                                self.attraction_points.append(
                                    [(sx + ex) / 2, (sy + ey) / 2, type_middle, emph]
                                )
                        ex = sx
                        ey = sy

        end_time = time()
        print(
            "Ready, time needed: %.6f, points added=%d"
            % (end_time - start_time, len(self.attraction_points))
        )

    def has_magnets(self):
        return len(self.magnet_x) + len(self.magnet_y) > 0

    def module_open(self, *args, **kwargs):
        context = self.context
        context.schedule(self)
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
        self.screen_refresh_lock.acquire()  # calling shutdown live locks here since it's already shutting down.
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
                self.calculate_attraction_points()
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
        dc.SelectObject(wx.NullBitmap)
        del dc

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
            if self.log:
                self.log("Redraw Canvas")

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
        RESPONSE_CHGPOS: like CONSUME but a new position needs to be passed to the next widgets (used for attraction)
        consider the dropped element within the hitchain.
        """
        need_refresh = False
        if self.log_events:
            self.log_events("%s: %s" % (event_type, str(window_pos)))

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
            "kb_shift_release",
            "kb_shift_press",
            "kb_ctrl_release",
            "kb_ctrl_press",
            "kb_alt_release",
            "kb_alt_press",
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
                try:
                    # We ignore the consume etc. for the time being...
                    response = current_widget.event(window_pos, space_pos, event_type)
                except AttributeError:
                    pass
            return

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
        # old_debug = ""
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
            # debug_str = "%.1f, %.1f" % (space_pos[0], space_pos[1])
            # if debug_str != old_debug:
            #    old_debug = debug_str
            #    print("Space-Pos changed for widget %d: %s" % (i, debug_str))

            if (
                i == 0
                and event_type == "hover"
                and previous_top_element is not current_widget
            ):
                if previous_top_element is not None:
                    if self.log_events:
                        self.log_events(
                            "Converted %s: %s" % ("hover_end", str(window_pos))
                        )
                    previous_top_element.event(window_pos, window_pos, "hover_end")
                current_widget.event(window_pos, space_pos, "hover_start")
                if self.log_events:
                    self.log_events(
                        "Converted %s: %s" % ("hover_start", str(window_pos))
                    )
                previous_top_element = current_widget
            if event_type == "leftup" and time.time() - self.time <= 0.15:
                response = current_widget.event(window_pos, space_pos, "leftclick")
                if self.log_events:
                    self.log_events("Converted %s: %s" % ("leftclick", str(window_pos)))
            else:
                response = current_widget.event(window_pos, space_pos, event_type)

            # if current_widget is None:
            #    widgetname = "undefined"
            # else:
            #    widgetname = type(current_widget).__name__

            if response == RESPONSE_ABORT:
                # f event_type == "leftdown":
                #    print("Event was aborted by %s" % widgetname)
                self.hit_chain.clear()
                return
            elif response == RESPONSE_CONSUME:
                # if event_type == "leftdown":
                #    print("Event was consumed by %s" % widgetname)
                return
            elif response == RESPONSE_CHAIN:
                continue
            elif response == RESPONSE_CHGPOS:
                # New position has been given:
                print(
                    "New position for %s: %s, %s"
                    % (event_type, self.new_x_space, self.new_y_space)
                )
                new_x = window_pos[0]
                new_y = window_pos[1]
                if not self.new_x_space is None:
                    sdx = self.new_x_space - space_pos[0]
                    odx = sdx
                    if current_matrix is not None and not current_matrix.is_identity():
                        sdx *= current_matrix.value_scale_x()
                    # print("Shift x by %.1f pixel (%.1f)" % (sdx, odx))
                    new_x = window_pos[0] + sdx

                if not self.new_y_space is None:
                    sdy = self.new_y_space - space_pos[1]
                    ody = sdy
                    if current_matrix is not None and not current_matrix.is_identity():
                        sdy *= current_matrix.value_scale_y()
                    # print("Shift y by %.1f pixel (%.1f)" % (sdy, ody))
                    new_y = window_pos[1] + sdy

                dx = new_x - self.last_position[0]
                dy = new_y - self.last_position[1]
                window_pos = (
                    new_x,
                    new_y,
                    self.last_position[0],
                    self.last_position[1],
                    dx,
                    dy,
                )
                self.last_position = window_pos
                self.new_x_space = None
                self.new_y_space = None
                need_refresh = True
                # Hack to update the position of the elements: We run one call through all widgets and ask them to update...
                """
                if event_type != "leftdown":
                    for i2, hit2 in enumerate(self.hit_chain):
                        if hit2 is None or i == i2:
                            continue  # Element was dropped, or identical to the current_widget
                        current_widget2, current_matrix2 = hit
                        space_pos2 = window_pos
                        if (
                            current_matrix2 is not None
                            and not current_matrix2.is_identity()
                        ):
                            space_cur = current_matrix.point_in_inverse_space(
                                window_pos[0:2]
                            )
                            space_last = current_matrix.point_in_inverse_space(
                                window_pos[2:4]
                            )
                            sdx = space_cur[0] - space_last[0]
                            sdy = space_cur[1] - space_last[1]
                            space_pos2 = (
                                space_cur[0],
                                space_cur[1],
                                space_last[0],
                                space_last[1],
                                sdx,
                                sdy,
                            )
                        print("Tell widget #%d to move:" % i2)
                        response2 = current_widget2.event(
                            window_pos, space_pos2, "move"
                        )
                """
                continue
            elif response == RESPONSE_DROP:
                self.hit_chain[i] = None
            else:
                break
        if need_refresh:
            print("Refresh...")
            self.screen_refresh_is_requested = True
            self.refresh_scene()

    def cursor(self, cursor, always=False):
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

    def validate_reference(self):
        """
        Check whether the reference is still valid
        """
        found = False
        if not self._reference is None:
            for e in self.context.elements.flat(types=("elem",)):
                # Here we ignore the lock-status of an element
                obj = e.object
                if obj is self._reference:
                    found = True
                    break
        if not found:
            self._reference = None

    @property
    def reference_object(self):
        return self._reference

    @reference_object.setter
    def reference_object(self, ref_object):
        self._reference = ref_object
