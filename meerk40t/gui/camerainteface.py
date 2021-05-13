import wx

from ..kernel import Job, Module
from ..svgelements import Matrix, Point, Viewbox
from .icons import (
    icons8_camera_50,
    icons8_connected_50,
    icons8_detective_50,
    icons8_picture_in_picture_alternative_50,
)
from .laserrender import DRAW_MODE_FLIPXY, DRAW_MODE_INVERT
from .mwindow import MWindow
from .zmatrix import ZMatrix

_ = wx.GetTranslation

CORNER_SIZE = 25


class CameraInterface(MWindow, Job):
    def __init__(self, *args, index=None, **kwds):
        super().__init__(640, 480, *args, **kwds)
        if index is None:
            index = 0
        self.index = index
        Job.__init__(self, job_name="Camera%d" % self.index)
        self.camera = None
        self.last_frame_index = -1

        self.camera_setting = self.context.get_context("camera")
        self.setting = self.camera_setting.derive(str(self.index))

        self.root_context = self.context.get_context("/")

        self.button_update = wx.BitmapButton(
            self, wx.ID_ANY, icons8_camera_50.GetBitmap()
        )
        self.button_export = wx.BitmapButton(
            self, wx.ID_ANY, icons8_picture_in_picture_alternative_50.GetBitmap()
        )
        self.button_reconnect = wx.BitmapButton(
            self, wx.ID_ANY, icons8_connected_50.GetBitmap()
        )
        self.check_fisheye = wx.CheckBox(self, wx.ID_ANY, _("Correct Fisheye"))
        self.check_perspective = wx.CheckBox(self, wx.ID_ANY, _("Correct Perspective"))
        self.slider_fps = wx.Slider(
            self,
            wx.ID_ANY,
            24,
            0,
            60,
            style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS,
        )
        self.button_detect = wx.BitmapButton(
            self, wx.ID_ANY, icons8_detective_50.GetBitmap()
        )
        self.display_camera = wx.Panel(self, wx.ID_ANY)

        self.CameraInterface_menubar = wx.MenuBar()
        wxglade_tmp_menu = wx.Menu()
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Reset Perspective"), "")
        self.Bind(wx.EVT_MENU, self.reset_perspective, id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Reset Fisheye"), "")
        self.Bind(wx.EVT_MENU, self.reset_fisheye, id=item.GetId())
        wxglade_tmp_menu.AppendSeparator()

        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Set URI"), "")
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context.open("window/CameraURI", self, index=self.index),
            id=item.GetId(),
        )

        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("USB %d") % 0, "")
        self.Bind(wx.EVT_MENU, self.swap_camera(0), id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("USB %d") % 1, "")
        self.Bind(wx.EVT_MENU, self.swap_camera(1), id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("USB %d") % 2, "")
        self.Bind(wx.EVT_MENU, self.swap_camera(2), id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("USB %d") % 3, "")
        self.Bind(wx.EVT_MENU, self.swap_camera(3), id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("USB %d") % 4, "")
        self.Bind(wx.EVT_MENU, self.swap_camera(4), id=item.GetId())

        self.CameraInterface_menubar.Append(wxglade_tmp_menu, _("Camera"))
        self.SetMenuBar(self.CameraInterface_menubar)
        # Menu Bar

        self.__set_properties()
        self.__do_layout()

        self.image_width = -1
        self.image_height = -1
        self._Buffer = None

        self.frame_bitmap = None

        self.previous_window_position = None
        self.previous_scene_position = None

        self.corner_drag = None

        self.matrix = Matrix()

        self.Bind(wx.EVT_BUTTON, self.on_button_update, self.button_update)
        self.Bind(wx.EVT_BUTTON, self.on_button_export, self.button_export)
        self.Bind(wx.EVT_BUTTON, self.on_button_reconnect, self.button_reconnect)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_fisheye, self.check_fisheye)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_perspective, self.check_perspective)
        self.Bind(wx.EVT_SLIDER, self.on_slider_fps, self.slider_fps)
        self.Bind(wx.EVT_BUTTON, self.on_button_detect, self.button_detect)
        self.SetDoubleBuffered(True)
        # end wxGlade

        self.display_camera.Bind(wx.EVT_PAINT, self.on_paint)
        self.display_camera.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase)
        self.display_camera.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.display_camera.Bind(wx.EVT_MOUSEWHEEL, self.on_mousewheel)
        self.display_camera.Bind(wx.EVT_MIDDLE_UP, self.on_mouse_middle_up)
        self.display_camera.Bind(wx.EVT_MIDDLE_DOWN, self.on_mouse_middle_down)

        self.display_camera.Bind(wx.EVT_RIGHT_DOWN, self.on_mouse_right_down)
        self.display_camera.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_left_down)
        self.display_camera.Bind(wx.EVT_LEFT_UP, self.on_mouse_left_up)
        self.display_camera.Bind(
            wx.EVT_ENTER_WINDOW, lambda event: self.display_camera.SetFocus()
        )  # Focus follows mouse.

        self.setting.setting(bool, "aspect", False)
        self.setting.setting(str, "preserve_aspect", "xMinYMin meet")

        self.Bind(wx.EVT_SIZE, self.on_size, self)
        self.on_size()

        self.on_update_buffer()

        self.context.setting(bool, "mouse_zoom_invert", False)
        self.context.setting(int, "draw_mode", 0)

        self.bed_dim = self.context.get_context("/")
        self.bed_dim.setting(int, "bed_width", 310)
        self.bed_dim.setting(int, "bed_height", 210)

        try:
            self.camera = self.setting.activate("modifier/Camera")
        except ValueError:
            pass

        self.setting.setting(int, "index", 0)
        self.setting.setting(int, "fps", 1)
        self.setting.setting(bool, "correction_fisheye", False)
        self.setting.setting(bool, "correction_perspective", False)
        self.setting.setting(str, "fisheye", "")
        self.setting.setting(str, "perspective", "")
        self.setting.setting(str, "uri", "0")

        self.check_fisheye.SetValue(self.setting.correction_fisheye)
        self.check_perspective.SetValue(self.setting.correction_perspective)
        if self.setting.fisheye is not None and len(self.setting.fisheye) != 0:
            self.fisheye_k, self.fisheye_d = eval(self.setting.fisheye)
        if self.setting.perspective is not None and len(self.setting.perspective) != 0:
            self.perspective = eval(self.setting.perspective)
        self.slider_fps.SetValue(self.setting.fps)
        self.on_slider_fps()
        self.process = self.update_view

    def swap_camera(self, uri):
        def swap(event=None):
            self.context("camera%d --uri %s stop start\n" % (self.index, str(uri)))
            self.frame_bitmap = None

        return swap

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.button_update, 0, 0, 0)
        sizer_2.Add(self.button_export, 0, 0, 0)
        sizer_2.Add(self.button_reconnect, 0, 0, 0)
        sizer_3.Add(self.check_fisheye, 0, 0, 0)
        sizer_3.Add(self.check_perspective, 0, 0, 0)
        sizer_2.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_2.Add(self.slider_fps, 1, wx.EXPAND, 0)
        sizer_2.Add(self.button_detect, 0, 0, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        sizer_1.Add(self.display_camera, 10, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_camera_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: CameraInterface.__set_properties
        self.SetTitle(_("CameraInterface %d") % self.index)
        self.button_update.SetToolTip(_("Update Image"))
        self.button_update.SetSize(self.button_update.GetBestSize())
        self.button_export.SetToolTip(_("Export Snapsnot"))
        self.button_export.SetSize(self.button_export.GetBestSize())
        self.button_reconnect.SetToolTip(_("Reconnect Camera"))
        self.button_reconnect.SetSize(self.button_reconnect.GetBestSize())
        self.button_detect.SetToolTip(_("Detect Distortions/Calibration"))
        self.button_detect.SetSize(self.button_detect.GetBestSize())
        # end wxGlade

    @staticmethod
    def sub_register(kernel):
        kernel.register("window/CameraURI", CameraURI)

        @kernel.console_argument("index", type=int)
        @kernel.console_command(
            "camwin", help="camwin <index>: Open camera window at index"
        )
        def camera_win(command, channel, _, index=None, args=tuple(), **kwargs):
            if index is None:
                raise SyntaxError
            context = kernel.get_context("/")
            try:
                parent = context.gui
            except AttributeError:
                parent = None
            try:
                context.open_as(
                    "window/CameraInterface", "camera%d" % index, parent, index=index
                )
            except KeyError:
                pass

    def on_close(self, event):
        if self.state == 5:
            event.Veto()
        else:
            self.state = 5
            self.context.close(self.name)
            event.Skip()  # Call destroy as regular.

    def window_open(self):
        self.context("camera%d start\n" % self.index)
        self.context.schedule(self)

    def window_close(self):
        self.context("camera%d stop\n" % self.index)
        self.context.unschedule(self)

    def on_size(self, event=None):
        self.Layout()
        width, height = self.ClientSize
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        self._Buffer = wx.Bitmap(width, height)
        self.aspect_matrix()
        self.on_update_buffer()
        try:
            self.Refresh(True)
            self.Update()
        except RuntimeError:
            pass

    def update_view(self):
        if self.camera is None:
            return

        if self.camera.frame_index == self.last_frame_index:
            return
        else:
            self.last_frame_index = self.camera.frame_index

        if not wx.IsMainThread():
            wx.CallAfter(self._guithread_update_view)
        else:
            self._guithread_update_view()

    def _guithread_update_view(self):
        frame = self.camera.get_frame()
        if frame is None:
            return
        else:
            if self.frame_bitmap is None:
                wx.CallAfter(self.on_size, None)
        bed_width = self.bed_dim.bed_width * 2
        bed_height = self.bed_dim.bed_height * 2

        self.image_height, self.image_width = frame.shape[:2]
        self.frame_bitmap = wx.Bitmap.FromBuffer(
            self.image_width, self.image_height, frame
        )

        if self.setting.correction_perspective:
            if bed_width != self.image_width or bed_height != self.image_height:
                self.image_width = bed_width
                self.image_height = bed_height
                self.display_camera.SetSize((self.image_width, self.image_height))
        self.on_update_buffer()
        try:
            self.Refresh(True)
            self.Update()
        except RuntimeError:
            pass

    def reset_perspective(self, event):
        """
        Reset the perspective settings.

        :param event:
        :return:
        """
        self.perspective = None
        self.setting.perspective = ""

    def reset_fisheye(self, event):
        """
        Reset the fisheye settings.

        :param event:
        :return:
        """
        self.fisheye_k = None
        self.fisheye_d = None
        self.setting.fisheye = ""

    def on_erase(self, event):
        """
        Erase camera view.
        :param event:
        :return:
        """
        pass

    def on_paint(self, event):
        """
        Paint camera view.
        :param event:
        :return:
        """
        try:
            wx.BufferedPaintDC(self.display_camera, self._Buffer)
        except (RuntimeError, TypeError):
            pass

    def on_update_buffer(self, event=None):
        """
        Draw Camera view.

        :param event:
        :return:
        """
        dm = self.context.draw_mode
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        w, h = self._Buffer.GetSize()
        # dc.SetBackground(wx.WHITE_BRUSH)
        gc.SetBrush(wx.WHITE_BRUSH)
        gc.DrawRectangle(0, 0, w, h)
        if self.frame_bitmap is None:
            font = wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD)
            gc.SetFont(font, wx.BLACK)
            if self.camera is None:
                gc.DrawText(
                    _("Camera backend failure...\nCannot attempt camera connection."),
                    0,
                    0,
                )
            else:
                gc.DrawText(_("Fetching Frame..."), 0, 0)
            gc.Destroy()
            self.matrix.reset()
            return
        if dm & DRAW_MODE_FLIPXY != 0:
            dc.SetUserScale(-1, -1)
            dc.SetLogicalOrigin(w, h)

        gc.PushState()
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(self.matrix)))
        gc.DrawBitmap(self.frame_bitmap, 0, 0, self.image_width, self.image_height)
        if not self.setting.correction_perspective and not self.setting.aspect:
            if self.camera.perspective is None:
                self.camera.perspective = (
                    [0, 0],
                    [self.image_width, 0],
                    [self.image_width, self.image_height],
                    [0, self.image_height],
                )
            gc.SetPen(wx.BLACK_DASHED_PEN)
            gc.StrokeLines(self.camera.perspective)
            gc.StrokeLine(
                self.camera.perspective[0][0],
                self.camera.perspective[0][1],
                self.camera.perspective[3][0],
                self.camera.perspective[3][1],
            )
            gc.SetPen(wx.BLUE_PEN)
            for p in self.camera.perspective:
                half = CORNER_SIZE / 2
                gc.StrokeLine(p[0] - half, p[1], p[0] + half, p[1])
                gc.StrokeLine(p[0], p[1] - half, p[0], p[1] + half)
                gc.DrawEllipse(p[0] - half, p[1] - half, CORNER_SIZE, CORNER_SIZE)
        gc.PopState()
        if dm & DRAW_MODE_INVERT != 0:
            dc.Blit(0, 0, w, h, dc, 0, 0, wx.SRC_INVERT)
        gc.Destroy()
        del dc

    def aspect_matrix(self):
        if self.setting.aspect:
            v = Viewbox(
                "0 0 %d %d" % (self.image_width, self.image_height),
                self.setting.preserve_aspect,
            )
            w, h = self.display_camera.GetSize()
            v2 = Viewbox("0 0 %d %d" % (w, h))
            self.matrix = Matrix(v.transform(v2))

    def convert_scene_to_window(self, position):
        """
        Scene Matrix convert scene to window.
        :param position:
        :return:
        """
        point = self.matrix.point_in_matrix_space(position)
        return point[0], point[1]

    def convert_window_to_scene(self, position):
        """
        Scene Matrix convert window to scene.
        :param position:
        :return:
        """
        point = self.matrix.point_in_inverse_space(position)
        return point[0], point[1]

    def on_mouse_move(self, event):
        """
        Handle mouse movement.

        :param event:
        :return:
        """
        if not event.Dragging():
            return
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        if self.previous_window_position is None:
            return
        pos = event.GetPosition()
        window_position = pos.x, pos.y
        scene_position = self.convert_window_to_scene(
            [window_position[0], window_position[1]]
        )
        sdx = scene_position[0] - self.previous_scene_position[0]
        sdy = scene_position[1] - self.previous_scene_position[1]
        wdx = window_position[0] - self.previous_window_position[0]
        wdy = window_position[1] - self.previous_window_position[1]
        if self.corner_drag is None:
            self.scene_post_pan(wdx, wdy)
        else:
            self.camera.perspective[self.corner_drag][0] += sdx
            self.camera.perspective[self.corner_drag][1] += sdy
            self.setting.perspective = repr(self.camera.perspective)
        self.previous_window_position = window_position
        self.previous_scene_position = scene_position

    def on_mousewheel(self, event):
        """
        Handle mouse wheel.

        Used for zooming.

        :param event:
        :return:
        """
        rotation = event.GetWheelRotation()
        mouse = event.GetPosition()
        if self.context.get_context("/").mouse_zoom_invert:
            rotation = -rotation
        if rotation > 1:
            self.scene_post_scale(1.1, 1.1, mouse[0], mouse[1])
        elif rotation < -1:
            self.scene_post_scale(0.9, 0.9, mouse[0], mouse[1])

    def on_mouse_right_down(self, event):
        def enable_aspect(*args):
            self.setting.aspect = not self.setting.aspect
            self.aspect_matrix()
            self.on_update_buffer()

        def set_aspect(aspect):
            def asp(e):
                self.setting.preserve_aspect = aspect
                self.aspect_matrix()
                self.on_update_buffer()

            return asp

        menu = wx.Menu()
        sub_menu = wx.Menu()
        center = menu.Append(wx.ID_ANY, "Aspect", "", wx.ITEM_CHECK)
        if self.setting.aspect:
            center.Check(True)
        self.Bind(wx.EVT_MENU, enable_aspect, center)
        self.Bind(
            wx.EVT_MENU,
            set_aspect("xMinYMin meet"),
            sub_menu.Append(wx.ID_ANY, "xMinYMin meet", "", wx.ITEM_NORMAL),
        )
        self.Bind(
            wx.EVT_MENU,
            set_aspect("xMidYMid meet"),
            sub_menu.Append(wx.ID_ANY, "xMidYMid meet", "", wx.ITEM_NORMAL),
        )
        self.Bind(
            wx.EVT_MENU,
            set_aspect("xMidYMid slice"),
            sub_menu.Append(wx.ID_ANY, "xMidYMid slice", "", wx.ITEM_NORMAL),
        )
        self.Bind(
            wx.EVT_MENU,
            set_aspect("none"),
            sub_menu.Append(wx.ID_ANY, "none", "", wx.ITEM_NORMAL),
        )

        menu.Append(
            wx.ID_ANY, _("Preserve: %s") % self.setting.preserve_aspect, sub_menu
        )
        if menu.MenuItemCount != 0:
            self.PopupMenu(menu)
            menu.Destroy()

    def on_mouse_left_down(self, event):
        """
        Handle mouse left down event.

        Used for adjusting perspective items.

        :param event:
        :return:
        """
        self.previous_window_position = event.GetPosition()
        self.previous_scene_position = self.convert_window_to_scene(
            self.previous_window_position
        )
        self.corner_drag = None
        if self.camera.perspective is not None:
            for i, p in enumerate(self.camera.perspective):
                half = CORNER_SIZE / 2
                if Point.distance(self.previous_scene_position, p) < half:
                    self.corner_drag = i
                    break

    def on_mouse_left_up(self, event):
        """
        Handle Mouse Left Up.

        Drag Ends.

        :param event:
        :return:
        """
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        self.previous_window_position = None
        self.previous_scene_position = None
        self.corner_drag = None

    def on_mouse_middle_down(self, event):
        """
        Handle mouse middle down

        Panning.

        :param event:
        :return:
        """
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.previous_window_position = event.GetPosition()
        self.previous_scene_position = self.convert_window_to_scene(
            self.previous_window_position
        )

    def on_mouse_middle_up(self, event):
        """
        Handle mouse middle up.

        Pan ends.

        :param event:
        :return:
        """
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        self.previous_window_position = None
        self.previous_scene_position = None

    def scene_post_pan(self, px, py):
        """
        Scene Pan.
        :param px:
        :param py:
        :return:
        """
        self.matrix.post_translate(px, py)
        self.on_update_buffer()

    def scene_post_scale(self, sx, sy=None, ax=0, ay=0):
        """
        Scene Zoom.
        :param sx:
        :param sy:
        :param ax:
        :param ay:
        :return:
        """
        self.matrix.post_scale(sx, sy, ax, ay)
        self.on_update_buffer()

    def on_check_perspective(self, event):
        """
        Perspective checked. Turns on/off
        :param event:
        :return:
        """
        self.setting.correction_perspective = self.check_perspective.GetValue()

    def on_check_fisheye(self, event):
        """
        Fisheye checked. Turns on/off.
        :param event:
        :return:
        """
        self.setting.correction_fisheye = self.check_fisheye.GetValue()

    def on_button_update(self, event):  # wxGlade: CameraInterface.<event_handler>
        """
        Button update.

        Sets image background to main scene.

        :param event:
        :return:
        """
        self.context("camera%d background\n" % self.index)

    def on_button_export(self, event):  # wxGlade: CameraInterface.<event_handler>
        """
        Button export.

        Sends an image to the scene as an exported object.
        :param event:
        :return:
        """
        self.context.console("camera%d export\n" % self.index)

    def on_button_reconnect(self, event):  # wxGlade: CameraInterface.<event_handler>
        self.context.console("camera%d stop start\n" % self.index)

    def on_slider_fps(self, event=None):  # wxGlade: CameraInterface.<event_handler>
        """
        Adjusts the camera FPS.

        If set to 0, this will be a frame each 5 seconds.

        :param event:
        :return:
        """
        fps = self.slider_fps.GetValue()
        if fps == 0:
            tick = 5
        else:
            tick = 1.0 / fps
        self.setting.fps = fps
        self.interval = tick

    def on_button_detect(self, event):  # wxGlade: CameraInterface.<event_handler>
        """
        Attempts to locate 6x9 checkerboard pattern for OpenCV to correct the fisheye pattern.

        :param event:
        :return:
        """
        self.context.console("camera%d fisheye detect\n" % self.index)


class CameraURI(MWindow):
    def __init__(self, *args, index=None, **kwds):
        super().__init__(437, 530, *args, **kwds)
        if index is None:
            index = 0
        self.index = index

        self.list_uri = wx.ListCtrl(
            self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES
        )
        self.button_add = wx.Button(self, wx.ID_ANY, "Add URI")
        self.text_uri = wx.TextCtrl(self, wx.ID_ANY, "")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_list_activated, self.list_uri)
        self.Bind(
            wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_list_right_clicked, self.list_uri
        )
        self.Bind(wx.EVT_BUTTON, self.on_button_add_uri, self.button_add)
        self.Bind(wx.EVT_TEXT, self.on_text_uri, self.text_uri)
        # end wxGlade
        self.camera_setting = None
        self.uri_list = dict()
        self.changed = False

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_camera_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: CameraURI.__set_properties
        self.SetTitle(_("Camera URI"))
        self.list_uri.SetToolTip(_("Displays a list of registered camera URIs"))
        self.list_uri.AppendColumn(_("Index"), format=wx.LIST_FORMAT_LEFT, width=69)
        self.list_uri.AppendColumn(_("URI"), format=wx.LIST_FORMAT_LEFT, width=348)
        self.button_add.SetToolTip(_("Add a new URL"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: CameraURI.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(self.list_uri, 1, wx.EXPAND, 0)
        sizer_2.Add(self.button_add, 0, 0, 0)
        sizer_2.Add(self.text_uri, 2, 0, 0)
        sizer_1.Add(sizer_2, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def window_open(self):
        self.camera_setting = self.context.get_context("camera")
        keylist = self.camera_setting._kernel.load_persistent_string_dict(
            self.camera_setting._path, suffix=True
        )
        if keylist is not None:
            keys = [q for q in keylist]
            keys.sort()
            self.uri_list = [keylist[k] for k in keys]
            self.on_list_refresh()

    def window_close(self):
        self.commit()

    def commit(self):
        if not self.changed:
            return
        for c in dir(self.camera_setting):
            if not c.startswith("uri"):
                continue
            setattr(self.camera_setting, c, None)
        for c in list(self.camera_setting._kernel.keylist(self.camera_setting._path)):
            self.camera_setting._kernel.delete_persistent(c)

        for i, uri in enumerate(self.uri_list):
            key = "uri%d" % i
            setattr(self.camera_setting, key, uri)
        self.camera_setting.flush()
        self.context.signal("camera_uri_changed", True)

    def on_list_refresh(self):
        self.list_uri.DeleteAllItems()
        for i, uri in enumerate(self.uri_list):
            m = self.list_uri.InsertItem(i, str(i))
            if m != -1:
                self.list_uri.SetItem(m, 1, str(uri))

    def on_list_activated(self, event):  # wxGlade: CameraURI.<event_handler>
        index = event.GetIndex()
        new_uri = self.uri_list[index]
        self.context.console("camera%d --uri %s stop start\n" % (self.index, new_uri))
        self.Close()

    def on_list_right_clicked(self, event):  # wxGlade: CameraURI.<event_handler>
        index = event.GetIndex()
        element = event.Text
        menu = wx.Menu()
        convert = menu.Append(
            wx.ID_ANY, _("Remove %s") % str(element)[:16], "", wx.ITEM_NORMAL
        )
        self.Bind(wx.EVT_MENU, self.on_tree_popup_delete(index), convert)
        convert = menu.Append(wx.ID_ANY, _("Duplicate"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_duplicate(index), convert)
        convert = menu.Append(wx.ID_ANY, _("Edit"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_edit(index), convert)
        convert = menu.Append(wx.ID_ANY, _("Clear All"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_clear(index), convert)
        self.PopupMenu(menu)
        menu.Destroy()

    def on_tree_popup_delete(self, index):
        def delete(event):
            try:
                del self.uri_list[index]
            except KeyError:
                pass
            self.changed = True
            self.on_list_refresh()

        return delete

    def on_tree_popup_duplicate(self, index):
        def duplicate(event):
            self.uri_list.insert(index, self.uri_list[index])
            self.changed = True
            self.on_list_refresh()

        return duplicate

    def on_tree_popup_edit(self, index):
        def edit(event):
            dlg = wx.TextEntryDialog(
                self,
                _("Edit"),
                _("Camera URI"),
                "",
            )
            dlg.SetValue(self.uri_list[index])
            if dlg.ShowModal() == wx.ID_OK:
                self.uri_list[index] = dlg.GetValue()
                self.changed = True
                self.on_list_refresh()

        return edit

    def on_tree_popup_clear(self, index):
        def delete(event):
            self.uri_list = list()
            self.changed = True
            self.on_list_refresh()

        return delete

    def on_button_add_uri(self, event):  # wxGlade: CameraURI.<event_handler>
        uri = self.text_uri.GetValue()
        if uri is None or uri == "":
            return
        self.uri_list.append(uri)
        self.text_uri.SetValue("")
        self.changed = True
        self.on_list_refresh()

    def on_text_uri(self, event):  # wxGlade: CameraURI.<event_handler>
        pass
