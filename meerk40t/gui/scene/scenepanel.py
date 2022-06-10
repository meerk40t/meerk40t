from copy import copy
import wx

from meerk40t.svgelements import Color, Rect
from meerk40t.core.node.elem_rect import RectNode
from meerk40t.gui.laserrender import LaserRender
from meerk40t.gui.wxutils import get_key_name
from meerk40t.gui.zmatrix import ZMatrix


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
        # Stuff for animated shapes...
        self._DrawBuffer = None
        self.animate = True
        self.counter = 0
        self.maxcounter = 1000

        self.__set_properties()
        self.__do_layout()

        self.scene_panel.Bind(wx.EVT_PAINT, self.on_paint)
        self.scene_panel.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase)

        self.scene_panel.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.scene_panel.Bind(wx.EVT_KEY_UP, self.on_key_up)

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

    # Indicator for Keyboard-Modifier
    isShiftPressed = False
    isCtrlPressed = False
    isAltPressed = False

    def on_key_down(self, evt):
        literal = get_key_name(evt, True)
        # keycode = evt.GetKeyCode()
        # print("Key-Down: %f - literal: %s" % (keycode, literal))
        if "shift+" in literal:
            if not self.isShiftPressed:  # ignore multiple calls
                self.isShiftPressed = True
                self.scene.event(self.scene.last_position, "kb_shift_press", None)
        if "ctrl+" in literal:
            if not self.isCtrlPressed:  # ignore multiple calls
                self.isCtrlPressed = True
                self.scene.event(self.scene.last_position, "kb_ctrl_press", None)
        if "alt+" in literal:
            if not self.isAltPressed:  # ignore multiple calls
                self.isAltPressed = True
                self.scene.event(self.scene.last_position, "kb_alt_press", None)
                # self.scene.event(self.scene.last_position, "kb_alt_press")
        evt.Skip()

    def on_key_up(self, evt):
        literal = ""
        keystates = (evt.ShiftDown(), evt.ControlDown(), evt.AltDown())
        if self.isShiftPressed and not keystates[0]:
            literal += "shift+"
        if self.isCtrlPressed and not keystates[1]:
            literal += "ctrl+"
        if self.isAltPressed and not keystates[2]:
            literal += "alt+"
        # key = evt.GetKeyCode()
        # print("Key-Up: %f - literal: %s" % (key, literal))

        if "shift+" in literal:
            if self.isShiftPressed:  # ignore multiple calls
                self.isShiftPressed = False
                self.scene.event(self.scene.last_position, "kb_shift_release", None)
        if "ctrl+" in literal:
            if self.isCtrlPressed:  # ignore multiple calls
                self.isCtrlPressed = False
                self.scene.event(self.scene.last_position, "kb_ctrl_release", None)
        if "alt+" in literal:
            if self.isAltPressed:  # ignore multiple calls
                self.isAltPressed = False
                self.scene.event(self.scene.last_position, "kb_alt_release", None)
        evt.Skip()

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
                    self.scene.event(event.GetPosition(), "wheelup_ctrl", None)
                elif rotation < -1:
                    self.scene.event(event.GetPosition(), "wheeldown_ctrl", None)
            else:
                if rotation > 1:
                    self.scene.event(event.GetPosition(), "wheelup", None)
                elif rotation < -1:
                    self.scene.event(event.GetPosition(), "wheeldown", None)
        else:
            if rotation > 1:
                self.scene.event(event.GetPosition(), "wheelleft", None)
            elif rotation < -1:
                self.scene.event(event.GetPosition(), "wheelright", None)

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
            self.scene.event(event.GetPosition(), "wheelup", None)
        elif rotation < -1:
            self.scene.event(event.GetPosition(), "wheeldown", None)

    def on_mouse_capture_lost(self, event):
        self.scene.event(None, "lost", None)

    def on_mouse_middle_down(self, event):
        """
        Scene Panel middle click event for down.
        """
        self.SetFocus()
        if not self.scene_panel.HasCapture():
            self.scene_panel.CaptureMouse()
        self.scene.event(event.GetPosition(), "middledown", None)

    def on_mouse_middle_up(self, event):
        """
        Scene Panel middle click event for up.
        """
        if self.scene_panel.HasCapture():
            self.scene_panel.ReleaseMouse()
        self.scene.event(event.GetPosition(), "middleup", None)

    def on_left_mouse_down(self, event):
        """
        Scene Panel left click event for down.
        """
        # Convert mac Control+left click into right click
        if event.RawControlDown() and not event.ControlDown():
            self.on_right_mouse_down(event)
            return
        self.SetFocus()

        if not self.scene_panel.HasCapture():
            self.scene_panel.CaptureMouse()
        self.scene.event(event.GetPosition(), "leftdown", None)

    def on_left_mouse_up(self, event):
        """
        Scene Panel left click event for up.
        """
        # Convert mac Control+left click into right click
        if event.RawControlDown() and not event.ControlDown():
            self.on_right_mouse_up(event)
            return
        if self.scene_panel.HasCapture():
            self.scene_panel.ReleaseMouse()
        self.scene.event(event.GetPosition(), "leftup", None)

    def on_mouse_double_click(self, event):
        """
        Scene Panel doubleclick event.
        """
        if self.scene_panel.HasCapture():
            return
        self.scene.event(event.GetPosition(), "doubleclick", None)

    last_mode = None

    def on_mouse_move(self, event: wx.MouseEvent):
        """
        Scene Panel move event. Calls hover if the mouse has no pressed buttons.
        Calls move if the mouse is currently dragging.
        """
        if event.Moving():
            self.scene.event(event.GetPosition(), "hover", None)
        else:
            self.scene.event(event.GetPosition(), "move", None)

    def on_right_mouse_down(self, event):
        """
        Scene Panel right mouse down event.

        Offers alternative events if Alt or control is currently pressed.
        """
        self.SetFocus()
        if event.AltDown():
            self.scene.event(event.GetPosition(), "rightdown+alt", None)
        elif event.ControlDown():
            self.scene.event(event.GetPosition(), "rightdown+control", None)
        else:
            self.scene.event(event.GetPosition(), "rightdown", None)
        event.Skip()

    def on_right_mouse_up(self, event):
        """
        Scene Panel right mouse up event.
        """
        self.scene.event(event.GetPosition(), "rightup", None)

    def on_magnify_mouse(self, event):
        """
        Magnify Mouse is a Mac-only Event called with pinch to zoom on a trackpad.
        """
        magnification = event.GetMagnification()
        # if event.IsGestureStart():
        #     self.scene.event(event.GetPosition(), "gesture-start")
        # elif event.IsGestureEnd():
        #     self.scene.event(event.GetPosition(), "gesture-end")
        # else:
        self.scene.event(
            event.GetPosition(), "magnify {mag}".format(mag=(1.0 + magnification))
        )

    def on_gesture(self, event):
        """
        Scene Panel TouchScreen Gestures events.

        This code requires WXPython 4.1 and the bind will fail otherwise.
        """
        if event.IsGestureStart():
            self.scene.event(event.GetPosition(), "gesture-start", None)
        elif event.IsGestureEnd():
            self.scene.event(event.GetPosition(), "gesture-end", None)
        else:
            try:
                zoom = event.GetZoomFactor()
            except AttributeError:
                zoom = 1.0
            self.scene.event(event.GetPosition(), "zoom {zoom}".format(zoom=zoom), None)

    def draw_animation(self, canvas, counter):
        canvas.DrawRectangle(0, 0, 5000, 5000)
        nodes = list()
        for e in list(self.scene.context.elements.elems(emphasized=True)):
            if e.type == "elem file" or e.type == "elem group":
                # We only show basic types
                continue
            if e.type == "elem image" or e.type == "elem text":
                bb = e.bounds
                rect = Rect(x=bb[0], y=bb[1], width=(bb[2] - bb[0]), height=(bb[3] - bb[1]))
                copy_node = RectNode(shape=rect, matrix = copy(e.matrix))
                copy_node.stroke = Color(255, 0, 0)
            else:
                copy_node = copy(e)
                if hasattr(e, "fill"):
                    copy_node.fill = None
                if hasattr(e, "stroke"):
                    copy_node.stroke = Color(255, 0, 0)
            nodes.append(copy_node)
        if len(nodes)>0:
            print ("Nodes to display: %d" % len(nodes))
            matrix = self.scene.matrix
            scale_x = matrix.value_scale_x()
            try:
                zoom_scale = 1 / scale_x
            except ZeroDivisionError:
                matrix.reset()
                zoom_scale = 1
            if zoom_scale < 1:
                zoom_scale = 1
            draw_mode = self.scene.context.draw_mode
            animation_render = LaserRender(self.scene.context)
            animation_render.xor_mode = True
            animation_render.pen_style = wx.PENSTYLE_USER_DASH
            if counter % 2 == 0:
                animation_render.pen_dash = [1, 2, 5, 2]
            else:
                animation_render.pen_dash = [5, 2, 1, 2]
            animation_render.render(nodes, canvas, draw_mode, zoomscale=zoom_scale)
        else:
            print("nothing to display")

    def on_paint(self, event=None):
        """
        Scene Panel paint event calls the paints the bitmap self._Buffer. If self._Buffer does not exist initially
        it is created in the self.scene.update_buffer_ui_thread() call.
        """
        #try:
        print ("Paint")
        if self._Buffer is None:
            print("Update was needed")
            self.scene.update_buffer_ui_thread()
            # The buffer contains all the regular stuff
        # Now we add all the animation things...
        w, h = self._Buffer.Size
        self._DrawBuffer = self._Buffer.GetSubBitmap(wx.Rect(0, 0, w, h))
        dc = wx.MemoryDC()
        dc.SelectObject(self._DrawBuffer)
        # Now lets do additional drawing on it...
        gc = None
        if self.animate:
            gc = wx.GraphicsContext.Create(dc)
            gc.Size = dc.Size
            if self.scene.matrix is not None and not self.scene.matrix.is_identity():
                gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(self.scene.matrix)))
            self.draw_animation(gc, self.counter)
            self.counter += 1
            if self.counter >= self.maxcounter:
                self.counter = 0
        wx.BufferedPaintDC(self.scene_panel, self._DrawBuffer)
        # I am done, so lets get rid of it
        if not gc is None:
            gc.Destroy()
        dc.SelectObject(wx.NullBitmap)
        del dc
        #except (RuntimeError, AssertionError, TypeError):
        #    pass

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
