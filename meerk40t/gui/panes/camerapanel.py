import wx
from wx import aui

from ...kernel import Job
from ...svgelements import Color
from ..icons import (
    icons8_camera_50,
    icons8_connected_50,
    icons8_detective_50,
    icons8_picture_in_picture_alternative_50,
)
from ..mwindow import MWindow
from ..scene.scene import (
    HITCHAIN_HIT,
    RESPONSE_ABORT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    ScenePanel,
    Widget,
)

_ = wx.GetTranslation

CORNER_SIZE = 25


def register_panel(window, context):
    for index in range(5):
        panel = CameraPanel(
            window, wx.ID_ANY, context=context, gui=window, index=index, pane=True
        )
        pane = (
            aui.AuiPaneInfo()
            .Left()
            .MinSize(200, 150)
            .FloatingSize(640, 480)
            .Caption(_("Camera %d" % index))
            .Name("camera%d" % index)
            .CaptionVisible(not context.pane_lock)
            .Hide()
        )
        pane.dock_proportion = 200
        pane.control = panel
        pane.submenu = _("Camera")
        window.on_pane_add(pane)
        context.register("pane/camera%d" % index, pane)


class CameraPanel(wx.Panel, Job):
    def __init__(
        self, *args, context=None, gui=None, index: int = 0, pane=False, **kwds
    ):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.gui = gui
        self.context = context
        self.index = index
        self.pane = pane

        if pane:
            job_name = "CamPane%d" % self.index
        else:
            job_name = "Camera%d" % self.index
        Job.__init__(self, job_name=job_name)
        self.process = self.update_camera_frame
        self.run_main = True

        self.context("camera%d\n" % self.index)  # command activates Camera service
        self.camera = self.context.get_context(
            "camera/%d" % self.index
        )  # camera service location.

        self.last_frame_index = -1

        if not pane:
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
            self.check_perspective = wx.CheckBox(
                self, wx.ID_ANY, _("Correct Perspective")
            )
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
            scene_name = "Camera%s" % self.index
        else:
            scene_name = "CamPaneScene%s" % self.index

        self.display_camera = ScenePanel(
            self.context,
            self,
            scene_name=scene_name,
            style=wx.EXPAND | wx.WANTS_CHARS,
        )
        self.widget_scene = self.display_camera.scene

        # end wxGlade
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        if not pane:
            self.button_update.SetToolTip(_("Update Image"))
            self.button_update.SetSize(self.button_update.GetBestSize())
            self.button_export.SetToolTip(_("Export Snapshot"))
            self.button_export.SetSize(self.button_export.GetBestSize())
            self.button_reconnect.SetToolTip(_("Reconnect Camera"))
            self.button_reconnect.SetSize(self.button_reconnect.GetBestSize())
            self.button_detect.SetToolTip(_("Detect Distortions/Calibration"))
            self.button_detect.SetSize(self.button_detect.GetBestSize())
            sizer_controls = wx.BoxSizer(wx.HORIZONTAL)
            sizer_checkboxes = wx.BoxSizer(wx.VERTICAL)
            sizer_controls.Add(self.button_update, 0, 0, 0)
            sizer_controls.Add(self.button_export, 0, 0, 0)
            sizer_controls.Add(self.button_reconnect, 0, 0, 0)
            sizer_checkboxes.Add(self.check_fisheye, 0, 0, 0)
            sizer_checkboxes.Add(self.check_perspective, 0, 0, 0)
            sizer_controls.Add(sizer_checkboxes, 1, wx.EXPAND, 0)
            sizer_controls.Add(self.slider_fps, 1, wx.EXPAND, 0)
            sizer_controls.Add(self.button_detect, 0, 0, 0)
            sizer_main.Add(sizer_controls, 1, wx.EXPAND, 0)
            self.Bind(wx.EVT_BUTTON, self.on_button_update, self.button_update)
            self.Bind(wx.EVT_BUTTON, self.on_button_export, self.button_export)
            self.Bind(wx.EVT_BUTTON, self.on_button_reconnect, self.button_reconnect)
            self.Bind(wx.EVT_CHECKBOX, self.on_check_fisheye, self.check_fisheye)
            self.Bind(
                wx.EVT_CHECKBOX, self.on_check_perspective, self.check_perspective
            )
            self.Bind(wx.EVT_SLIDER, self.on_slider_fps, self.slider_fps)
            self.Bind(wx.EVT_BUTTON, self.on_button_detect, self.button_detect)
        sizer_main.Add(self.display_camera, 10, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.Layout()

        self.image_width = -1
        self.image_height = -1
        self.frame_bitmap = None

        self.SetDoubleBuffered(True)
        # end wxGlade

        if not pane:
            self.check_fisheye.SetValue(self.camera.correction_fisheye)
            self.check_perspective.SetValue(self.camera.correction_perspective)
            self.slider_fps.SetValue(self.camera.fps)
            self.on_slider_fps()

        self.widget_scene.widget_root.set_aspect(self.camera.aspect)

        self.widget_scene.background_brush = wx.WHITE_BRUSH
        self.widget_scene.add_scenewidget(CamSceneWidget(self.widget_scene, self))
        self.widget_scene.add_scenewidget(CamImageWidget(self.widget_scene, self))
        self.widget_scene.add_interfacewidget(
            CamInterfaceWidget(self.widget_scene, self)
        )

    def pane_show(self, *args):
        from sys import platform as _platform

        if _platform == "darwin" and not hasattr(self.camera, "_first"):
            self.context("camera%d start -t 1\n" % self.index)
            self.camera._first = False
        else:
            self.context("camera%d start\n" % self.index)
        self.context.schedule(self)
        self.context.listen("refresh_scene", self.on_refresh_scene)
        # self.context.kernel.listen("lifecycle;shutdown", "", self.pane_hide)

    def pane_hide(self, *args):
        self.context("camera%d stop\n" % self.index)
        self.context.unschedule(self)
        self.context.unlisten("refresh_scene", self.on_refresh_scene)
        if not self.pane:
            self.context.close("Camera%s" % str(self.index))
        # self.context.kernel.unlisten("lifecycle;shutdown", "", self.pane_hide)

    def module_close(self, *args):
        self.pane_hide()

    def on_refresh_scene(self, origin, *args):
        self.widget_scene.request_refresh(*args)

    def update_camera_frame(self, event=None):
        if self.camera is None:
            return

        if self.camera.frame_index == self.last_frame_index:
            return
        else:
            self.last_frame_index = self.camera.frame_index

        frame = self.camera.get_frame()
        if frame is None:
            return

        self.image_height, self.image_width = frame.shape[:2]
        if not self.frame_bitmap:
            # Initial set.
            self.widget_scene.widget_root.set_view(
                0, 0, self.image_width, self.image_height, self.camera.preserve_aspect
            )
        self.frame_bitmap = wx.Bitmap.FromBuffer(
            self.image_width, self.image_height, frame
        )
        if self.camera.perspective is None:
            self.camera.perspective = (
                [0, 0],
                [self.camera.width, 0],
                [self.camera.width, self.camera.height],
                [0, self.camera.height],
            )
        if self.camera.correction_perspective:
            if (
                self.camera.width != self.image_width
                or self.camera.height != self.image_height
            ):
                self.image_width = self.camera.width
                self.image_height = self.camera.height

        self.widget_scene.request_refresh()

    def reset_perspective(self, event=None):
        """
        Reset the perspective settings.

        :param event:
        :return:
        """
        self.context("camera%d perspective reset\n" % self.index)

    def reset_fisheye(self, event=None):
        """
        Reset the fisheye settings.

        :param event:
        :return:
        """
        self.context("camera%d fisheye reset\n" % self.index)

    def on_check_perspective(self, event=None):
        """
        Perspective checked. Turns on/off
        :param event:
        :return:
        """
        self.camera.correction_perspective = self.check_perspective.GetValue()

    def on_check_fisheye(self, event=None):
        """
        Fisheye checked. Turns on/off.
        :param event:
        :return:
        """
        self.camera.correction_fisheye = self.check_fisheye.GetValue()

    def on_button_update(self, event=None):  # wxGlade: CameraInterface.<event_handler>
        """
        Button update.

        Sets image background to main scene.

        :param event:
        :return:
        """
        self.context("camera%d background\n" % self.index)

    def on_button_export(self, event=None):  # wxGlade: CameraInterface.<event_handler>
        """
        Button export.

        Sends an image to the scene as an exported object.
        :param event:
        :return:
        """
        self.context.console("camera%d export\n" % self.index)

    def on_button_reconnect(
        self, event=None
    ):  # wxGlade: CameraInterface.<event_handler>
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
        self.camera.fps = fps
        self.interval = tick

    def on_button_detect(self, event=None):  # wxGlade: CameraInterface.<event_handler>
        """
        Attempts to locate 6x9 checkerboard pattern for OpenCV to correct the fisheye pattern.

        :param event:
        :return:
        """
        self.context.console("camera%d fisheye capture\n" % self.index)

    def swap_camera(self, uri):
        def swap(event=None):
            self.context("camera%d --uri %s stop start\n" % (self.index, str(uri)))
            self.frame_bitmap = None

        return swap


class CamInterfaceWidget(Widget):
    def __init__(self, scene, camera):
        Widget.__init__(self, scene, all=True)
        self.cam = camera

    def process_draw(self, gc: wx.GraphicsContext):
        if self.cam.frame_bitmap is None:
            font = wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD)
            gc.SetFont(font, wx.BLACK)
            if self.cam.camera is None:
                gc.DrawText(
                    _("Camera backend failure...\nCannot attempt camera connection."),
                    0,
                    0,
                )
            else:
                gc.DrawText(_("Fetching Frame..."), 0, 0)

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "rightdown":

            def enable_aspect(*args):
                self.cam.camera.aspect = not self.cam.camera.aspect
                self.scene.widget_root.set_aspect(self.cam.camera.aspect)
                self.scene.widget_root.set_view(
                    0,
                    0,
                    self.cam.image_width,
                    self.cam.image_height,
                    self.cam.camera.preserve_aspect,
                )

            def set_aspect(aspect):
                def asp(event=None):
                    self.cam.camera.preserve_aspect = aspect
                    self.scene.widget_root.set_aspect(self.cam.camera.aspect)
                    self.scene.widget_root.set_view(
                        0,
                        0,
                        self.cam.image_width,
                        self.cam.image_height,
                        self.cam.camera.preserve_aspect,
                    )

                return asp

            menu = wx.Menu()

            item = menu.Append(wx.ID_ANY, _("Update Background"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.context("camera%d background\n" % self.cam.index),
                id=item.GetId(),
            )

            item = menu.Append(wx.ID_ANY, _("Export Snapshot"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.context("camera%d export\n" % self.cam.index),
                id=item.GetId(),
            )

            item = menu.Append(wx.ID_ANY, _("Reconnect Camera"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.context("camera%d stop start\n" % self.cam.index),
                id=item.GetId(),
            )

            item = menu.Append(wx.ID_ANY, _("Stop Camera"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.context("camera%d stop\n" % self.cam.index),
                id=item.GetId(),
            )

            item = menu.Append(wx.ID_ANY, _("Open CameraInterface"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.context("camwin %d\n" % self.cam.index),
                id=item.GetId(),
            )

            menu.AppendSeparator()

            sub_menu = wx.Menu()
            center = menu.Append(wx.ID_ANY, _("Aspect"), "", wx.ITEM_CHECK)
            if self.cam.camera.aspect:
                center.Check(True)
            self.cam.Bind(wx.EVT_MENU, enable_aspect, center)
            self.cam.Bind(
                wx.EVT_MENU,
                set_aspect("xMinYMin meet"),
                sub_menu.Append(wx.ID_ANY, "xMinYMin meet", "", wx.ITEM_NORMAL),
            )
            self.cam.Bind(
                wx.EVT_MENU,
                set_aspect("xMidYMid meet"),
                sub_menu.Append(wx.ID_ANY, "xMidYMid meet", "", wx.ITEM_NORMAL),
            )
            self.cam.Bind(
                wx.EVT_MENU,
                set_aspect("xMidYMid slice"),
                sub_menu.Append(wx.ID_ANY, "xMidYMid slice", "", wx.ITEM_NORMAL),
            )
            self.cam.Bind(
                wx.EVT_MENU,
                set_aspect("none"),
                sub_menu.Append(wx.ID_ANY, "none", "", wx.ITEM_NORMAL),
            )

            menu.Append(
                wx.ID_ANY,
                _("Preserve: %s") % self.cam.camera.preserve_aspect,
                sub_menu,
            )
            menu.AppendSeparator()

            fisheye = menu.Append(wx.ID_ANY, _("Correct Fisheye"), "", wx.ITEM_CHECK)
            fisheye.Check(self.cam.camera.correction_fisheye)
            self.cam.camera.correction_fisheye = fisheye.IsChecked()

            def check_fisheye(event=None):
                self.cam.camera.correction_fisheye = fisheye.IsChecked()

            self.cam.Bind(wx.EVT_MENU, check_fisheye, fisheye)

            perspect = menu.Append(
                wx.ID_ANY, _("Correct Perspective"), "", wx.ITEM_CHECK
            )
            perspect.Check(self.cam.camera.correction_perspective)
            self.cam.camera.correction_perspective = perspect.IsChecked()

            def check_perspect(event=None):
                self.cam.camera.correction_perspective = perspect.IsChecked()

            self.cam.Bind(wx.EVT_MENU, check_perspect, perspect)
            menu.AppendSeparator()
            item = menu.Append(wx.ID_ANY, _("Reset Perspective"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.camera(
                    "camera%d perspective reset\n" % self.cam.index
                ),
                id=item.GetId(),
            )
            item = menu.Append(wx.ID_ANY, _("Reset Fisheye"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.camera("camera%d fisheye reset\n" % self.cam.index),
                id=item.GetId(),
            )
            menu.AppendSeparator()

            sub_menu = wx.Menu()
            item = sub_menu.Append(wx.ID_ANY, _("Set URI"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.context.open(
                    "window/CameraURI", self.cam, index=self.cam.index
                ),
                id=item.GetId(),
            )

            camera_context = self.cam.context.get_context("camera")
            keylist = camera_context.kernel.load_persistent_string_dict(
                camera_context.path, suffix=True
            )
            if keylist is not None:
                keys = [q for q in keylist]
                keys.sort()
                uri_list = [keylist[k] for k in keys]
                for uri in uri_list:
                    item = sub_menu.Append(wx.ID_ANY, _("URI: %s") % uri, "")
                    self.cam.Bind(
                        wx.EVT_MENU, self.cam.swap_camera(uri), id=item.GetId()
                    )

            item = sub_menu.Append(wx.ID_ANY, _("USB %d") % 0, "")
            self.cam.Bind(wx.EVT_MENU, self.cam.swap_camera(0), id=item.GetId())
            item = sub_menu.Append(wx.ID_ANY, _("USB %d") % 1, "")
            self.cam.Bind(wx.EVT_MENU, self.cam.swap_camera(1), id=item.GetId())
            item = sub_menu.Append(wx.ID_ANY, _("USB %d") % 2, "")
            self.cam.Bind(wx.EVT_MENU, self.cam.swap_camera(2), id=item.GetId())
            item = sub_menu.Append(wx.ID_ANY, _("USB %d") % 3, "")
            self.cam.Bind(wx.EVT_MENU, self.cam.swap_camera(3), id=item.GetId())
            item = sub_menu.Append(wx.ID_ANY, _("USB %d") % 4, "")
            self.cam.Bind(wx.EVT_MENU, self.cam.swap_camera(4), id=item.GetId())

            menu.Append(
                wx.ID_ANY,
                _("Set URI"),
                sub_menu,
            )
            if menu.MenuItemCount != 0:
                self.cam.PopupMenu(menu)
                menu.Destroy()
            return RESPONSE_ABORT
        if event_type == "doubleclick":
            self.cam.context("camera%d background\n" % self.cam.index)
        return RESPONSE_CHAIN


class CamPerspectiveWidget(Widget):
    def __init__(self, scene, camera, index, mid=False):
        self.cam = camera
        self.mid = mid
        self.index = index
        half = CORNER_SIZE / 2.0
        Widget.__init__(self, scene, -half, -half, half, half)
        self.update()
        c = Color.distinct(self.index + 2)
        self.pen = wx.Pen(wx.Colour(c.red, c.green, c.blue))

    def update(self):
        half = CORNER_SIZE / 2.0
        perspective = self.cam.camera.perspective
        pos = perspective[self.index]
        if not self.mid:
            self.set_position(pos[0] - half, pos[1] - half)
        else:
            center_x = sum([e[0] for e in perspective]) / len(perspective)
            center_y = sum([e[1] for e in perspective]) / len(perspective)
            x = (center_x + pos[0]) / 2.0
            y = (center_y + pos[1]) / 2.0
            self.set_position(x - half, y - half)

    def hit(self):
        return HITCHAIN_HIT

    def process_draw(self, gc):
        if (
            not self.cam.camera.correction_perspective
            and self.cam.camera.perspective
            and not self.cam.camera.aspect
        ):
            gc.SetPen(self.pen)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            gc.StrokeLine(
                self.left,
                self.top + self.height / 2.0,
                self.right,
                self.bottom - self.height / 2.0,
            )
            gc.StrokeLine(
                self.left + self.width / 2.0,
                self.top,
                self.right - self.width / 2.0,
                self.bottom,
            )
            gc.DrawEllipse(self.left, self.top, self.width, self.height)

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "leftdown":
            return RESPONSE_CONSUME
        if event_type == "move":
            # self.translate_self(space_pos[4], space_pos[5])
            perspective = self.cam.camera.perspective
            if perspective:
                perspective[self.index][0] += space_pos[4]
                perspective[self.index][1] += space_pos[5]
                if self.mid:
                    perspective[self.index][0] += space_pos[4]
                    perspective[self.index][1] += space_pos[5]
                for w in self.parent:
                    if isinstance(w, CamPerspectiveWidget):
                        w.update()
                self.cam.camera.perspective = repr(perspective)
                self.cam.context.signal("refresh_scene", self.scene.name)
            return RESPONSE_CONSUME


class CamSceneWidget(Widget):
    def __init__(self, scene, camera):
        Widget.__init__(self, scene, all=True)
        self.cam = camera

    def process_draw(self, gc):
        if not self.cam.camera.correction_perspective and not self.cam.camera.aspect:
            if self.cam.camera.perspective:
                if not len(self):
                    for i in range(4):
                        self.add_widget(
                            -1, CamPerspectiveWidget(self.scene, self.cam, i, False)
                        )
                    # for i in range(4):
                    #     self.add_widget(-1, CamPerspectiveWidget(self.scene, self.cam, i, True))
                gc.SetPen(wx.BLACK_DASHED_PEN)
                gc.StrokeLines(self.cam.camera.perspective)
                gc.StrokeLine(
                    self.cam.camera.perspective[0][0],
                    self.cam.camera.perspective[0][1],
                    self.cam.camera.perspective[3][0],
                    self.cam.camera.perspective[3][1],
                )
        else:
            if len(self):
                self.remove_all_widgets()


class CamImageWidget(Widget):
    def __init__(self, scene, camera):
        Widget.__init__(self, scene, all=False)
        self.cam = camera

    def process_draw(self, gc):
        if self.cam.frame_bitmap is None:
            return
        gc.DrawBitmap(
            self.cam.frame_bitmap, 0, 0, self.cam.image_width, self.cam.image_height
        )


class CameraInterface(MWindow):
    def __init__(self, context, path, parent, index=0, **kwds):
        index = int(index)
        super().__init__(640, 480, context, path, parent, **kwds)
        self.panel = CameraPanel(self, wx.ID_ANY, context=self.context, index=index)

        # ==========
        # MENU BAR
        # ==========
        from sys import platform as _platform

        if _platform != "darwin":
            self.CameraInterface_menubar = wx.MenuBar()
            self.create_menu(self.CameraInterface_menubar.Append)
            self.SetMenuBar(self.CameraInterface_menubar)
        # ==========
        # MENUBAR END
        # ==========

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_camera_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("CameraInterface %d") % index)
        self.Layout()

    def create_menu(self, append):
        wxglade_tmp_menu = wx.Menu()
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Reset Perspective"), "")
        self.Bind(wx.EVT_MENU, self.panel.reset_perspective, id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Reset Fisheye"), "")
        self.Bind(wx.EVT_MENU, self.panel.reset_fisheye, id=item.GetId())
        wxglade_tmp_menu.AppendSeparator()

        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Set URI"), "")
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context.open(
                "window/CameraURI", self, index=self.panel.index
            ),
            id=item.GetId(),
        )

        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("USB %d") % 0, "")
        self.Bind(wx.EVT_MENU, self.panel.swap_camera(0), id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("USB %d") % 1, "")
        self.Bind(wx.EVT_MENU, self.panel.swap_camera(1), id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("USB %d") % 2, "")
        self.Bind(wx.EVT_MENU, self.panel.swap_camera(2), id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("USB %d") % 3, "")
        self.Bind(wx.EVT_MENU, self.panel.swap_camera(3), id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("USB %d") % 4, "")
        self.Bind(wx.EVT_MENU, self.panel.swap_camera(4), id=item.GetId())

        append(wxglade_tmp_menu, _("Camera"))

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def sub_register(kernel):
        def camera_click(index=None):
            def specific(event=None):
                kernel.root.setting(int, "camera_default", 1)
                if index is not None:
                    kernel.root.camera_default = index
                v = kernel.root.camera_default
                kernel.console("window toggle CameraInterface %d\n" % v)

            return specific

        kernel.register(
            "button/control/Camera",
            {
                "label": _("Camera"),
                "icon": icons8_camera_50,
                "tip": _("Opens Camera Window"),
                "action": camera_click(),
                "alt-action": (
                    (_("Camera %d") % 1, camera_click(1)),
                    (_("Camera %d") % 2, camera_click(2)),
                    (_("Camera %d") % 3, camera_click(3)),
                    (_("Camera %d") % 4, camera_click(4)),
                    (_("Camera %d") % 5, camera_click(5)),
                ),
            },
        )
        kernel.register("window/CameraURI", CameraURI)

        @kernel.console_argument("index", type=int)
        @kernel.console_command(
            "camwin", help=_("camwin <index>: Open camera window at index")
        )
        def camera_win(index=None, **kwargs):
            kernel.console("window open CameraInterface %d\n" % index)


class CameraURIPanel(wx.Panel):
    def __init__(self, *args, context=None, index=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        if index is None:
            index = 0
        self.index = index
        assert isinstance(self.index, int)

        self.list_uri = wx.ListCtrl(
            self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES
        )
        self.button_add = wx.Button(self, wx.ID_ANY, _("Add URI"))
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
        self.uri_list = None
        self.changed = False

    def __set_properties(self):
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

    def pane_show(self):
        camera_context = self.context.get_context("camera")
        keylist = camera_context.kernel.load_persistent_string_dict(
            camera_context.path, suffix=True
        )
        if keylist is not None:
            keys = [q for q in keylist if isinstance(q, str) and q.startswith("uri")]
            keys.sort()
            self.uri_list = [keylist[k] for k in keys]
            self.on_list_refresh()

    def pane_hide(self):
        self.commit()

    def commit(self):
        if not self.changed:
            return
        camera_context = self.context.get_context("camera")
        for c in dir(camera_context):
            if not c.startswith("uri"):
                continue
            setattr(camera_context, c, None)
        for c in list(camera_context.kernel.keylist(camera_context.path)):
            camera_context.kernel.delete_persistent(c)

        for i, uri in enumerate(self.uri_list):
            key = "uri%d" % i
            setattr(camera_context, key, uri)
        camera_context.flush()
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
        try:
            self.GetParent().Close()
        except (TypeError, AttributeError):
            pass

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
        def delete(event=None):
            try:
                del self.uri_list[index]
            except KeyError:
                pass
            self.changed = True
            self.on_list_refresh()

        return delete

    def on_tree_popup_duplicate(self, index):
        def duplicate(event=None):
            self.uri_list.insert(index, self.uri_list[index])
            self.changed = True
            self.on_list_refresh()

        return duplicate

    def on_tree_popup_edit(self, index):
        def edit(event=None):
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

    def on_button_add_uri(self, event=None):  # wxGlade: CameraURI.<event_handler>
        uri = self.text_uri.GetValue()
        if uri is None or uri == "":
            return
        self.uri_list.append(uri)
        self.text_uri.SetValue("")
        self.changed = True
        self.on_list_refresh()

    def on_text_uri(self, event):  # wxGlade: CameraURI.<event_handler>
        pass


class CameraURI(MWindow):
    def __init__(self, *args, index=None, **kwds):
        super().__init__(437, 530, *args, **kwds)

        self.panel = CameraURIPanel(self, wx.ID_ANY, context=self.context, index=index)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_camera_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: CameraURI.__set_properties
        self.SetTitle(_("Camera URI"))

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()
