import platform

import wx
from wx import aui

from meerk40t.gui.icons import (
    icons8_camera_50,
    icons8_connected_50,
    icons8_detective_50,
    icons8_picture_in_picture_alternative_50,
)
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_HIT,
    RESPONSE_ABORT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
)
from meerk40t.gui.scene.scenepanel import ScenePanel
from meerk40t.gui.scene.widget import Widget
from meerk40t.kernel import Job, signal_listener
from meerk40t.svgelements import Color

_ = wx.GetTranslation

CORNER_SIZE = 25


def register_panel_camera(window, context):
    for index in range(5):
        panel = CameraPanel(
            window, wx.ID_ANY, context=context, gui=window, index=index, pane=True
        )
        pane = (
            aui.AuiPaneInfo()
            .Left()
            .MinSize(200, 150)
            .FloatingSize(640, 480)
            .Caption(_("Camera {index}").format(index=index))
            .Name(f"camera{index}")
            .CaptionVisible(not context.pane_lock)
            .Hide()
        )
        pane.dock_proportion = 200
        pane.control = panel
        pane.submenu = "_60_" + _("Camera")
        window.on_pane_create(pane)
        context.register(f"pane/camera{index}", pane)


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
            job_name = f"CamPane{self.index}"
        else:
            job_name = f"Camera{self.index}"
        Job.__init__(self, job_name=job_name)
        self.process = self.update_camera_frame
        self.run_main = True

        self.context(f"camera{self.index}\n")  # command activates Camera service
        self.camera = self.context.get_context(f"camera/{self.index}")
        self.camera.setting(int, "frames_per_second", 30)
        # camera service location.
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
                30,
                0,
                120,
                style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS,
            )
            self.button_detect = wx.BitmapButton(
                self, wx.ID_ANY, icons8_detective_50.GetBitmap()
            )
            scene_name = f"Camera{self.index}"
        else:
            scene_name = f"CamPaneScene{self.index}"

        self.display_camera = ScenePanel(
            self.camera,
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
            self.button_detect.SetToolTip(
                _(
                    "Detect Distortions/Calibration\n"
                    "You need to print a 9x6 checkerboard pattern from OpenCV\n"
                    "It should be flat and visible in the camera."
                )
            )
            self.button_detect.SetSize(self.button_detect.GetBestSize())
            self.slider_fps.SetToolTip(
                _(
                    "Set the camera frames per second. A value of 0 means a frame every 5 seconds."
                )
            )
            self.check_fisheye.SetToolTip(
                _("Corrects Fisheye lensing, must be trained with checkerboard image.")
            )
            self.check_perspective.SetToolTip(
                _(
                    "The four marker locations (in scene when unchecked) are transformed into corners of a regular square shape."
                )
            )

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
            self.slider_fps.SetValue(self.camera.frames_per_second)

        self.on_fps_change(self.camera.path)

        self.widget_scene.widget_root.set_aspect(self.camera.aspect)

        self.widget_scene.background_brush = wx.Brush(wx.WHITE)
        self.widget_scene.add_scenewidget(CamSceneWidget(self.widget_scene, self))
        self.widget_scene.add_scenewidget(CamImageWidget(self.widget_scene, self))
        self.widget_scene.add_interfacewidget(
            CamInterfaceWidget(self.widget_scene, self)
        )

    def pane_show(self, *args):
        if platform.system() == "Darwin" and not hasattr(self.camera, "_first"):
            self.camera(f"camera{self.index} start -t 1\n")
            self.camera._first = False
        else:
            self.camera(f"camera{self.index} start\n")
        self.camera.schedule(self)
        # This listener is because you can have frames and windows and both need to care about the slider.
        self.camera.listen("camera;fps", self.on_fps_change)
        self.camera.listen("camera;stopped", self.on_camera_stop)
        self.camera.gui = self
        self.camera("camera focus -5% -5% 105% 105%\n")

    def pane_hide(self, *args):
        self.camera(f"camera{self.index} stop\n")
        self.camera.unschedule(self)
        if not self.pane:
            self.camera.close(f"Camera{str(self.index)}")
        self.camera.unlisten("camera;fps", self.on_fps_change)
        self.camera.unlisten("camera;stopped", self.on_camera_stop)
        self.camera.signal("camera;stopped", self.index)
        self.camera.gui = None

    def on_camera_stop(self, origin, index):
        if index == self.index:
            self.camera(f"camera{self.index} start\n")

    def on_fps_change(self, origin, *args):
        # Set the camera fps.
        if origin != self.camera.path:
            # Not this window.
            return
        camera_fps = self.camera.frames_per_second
        if camera_fps == 0:
            tick = 5
        else:
            tick = 1.0 / camera_fps
        self.interval = tick
        # Set the scene fps if it's needed to support the camera.
        scene_fps = self.camera.frames_per_second
        if scene_fps < 30:
            scene_fps = 30
        if self.camera.fps != scene_fps:
            self.display_camera.scene.set_fps(scene_fps)

    @signal_listener("refresh_scene")
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

        @param event:
        @return:
        """
        self.camera(f"camera{self.index} perspective reset\n")

    def reset_fisheye(self, event=None):
        """
        Reset the fisheye settings.

        @param event:
        @return:
        """
        self.camera(f"camera{self.index} fisheye reset\n")

    def on_check_perspective(self, event=None):
        """
        Perspective checked. Turns on/off
        @param event:
        @return:
        """
        self.camera.correction_perspective = self.check_perspective.GetValue()

    def on_check_fisheye(self, event=None):
        """
        Fisheye checked. Turns on/off.
        @param event:
        @return:
        """
        self.camera.correction_fisheye = self.check_fisheye.GetValue()

    def on_button_update(self, event=None):  # wxGlade: CameraInterface.<event_handler>
        """
        Button update.

        Sets image background to main scene.

        @param event:
        @return:
        """
        self.camera(f"camera{self.index} background\n")

    def on_button_export(self, event=None):  # wxGlade: CameraInterface.<event_handler>
        """
        Button export.

        Sends an image to the scene as an exported object.
        @param event:
        @return:
        """
        self.camera.console(f"camera{self.index} export\n")

    def on_button_reconnect(
        self, event=None
    ):  # wxGlade: CameraInterface.<event_handler>
        self.camera.console(f"camera{self.index} stop start\n")

    def on_slider_fps(self, event=None):  # wxGlade: CameraInterface.<event_handler>
        """
        Adjusts the camera FPS.

        If set to 0, this will be a frame each 5 seconds.

        @param event:
        @return:
        """
        self.camera.frames_per_second = self.slider_fps.GetValue()
        self.camera.signal("camera;fps", self.camera.frames_per_second)

    def on_button_detect(self, event=None):  # wxGlade: CameraInterface.<event_handler>
        """
        Attempts to locate 6x9 checkerboard pattern for OpenCV to correct the fisheye pattern.

        @param event:
        @return:
        """
        self.camera.console(f"camera{self.index} fisheye capture\n")

    def swap_camera(self, uri):
        def swap(event=None):
            self.camera(f"camera{self.index} --uri {str(uri)} stop start\n")
            self.frame_bitmap = None

        return swap


class CamInterfaceWidget(Widget):
    def __init__(self, scene, camera):
        Widget.__init__(self, scene, all=True)
        self.cam = camera

    def process_draw(self, gc: wx.GraphicsContext):
        if self.cam.frame_bitmap is None:
            font = wx.Font(
                14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
            )
            gc.SetFont(font, wx.BLACK)
            if self.cam.camera is None:
                gc.DrawText(
                    _("Camera backend failure...\nCannot attempt camera connection."),
                    0,
                    0,
                )
            else:
                gc.DrawText(
                    _("Fetching URI:{uri} Frame...").format(uri=self.cam.camera.uri),
                    0,
                    0,
                )

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
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
                lambda e: self.cam.context(f"camera{self.cam.index} background\n"),
                id=item.GetId(),
            )

            def live_view(c_frames, c_sec):
                def runcam(event=None):
                    ratio = c_sec / c_frames
                    self.cam.context(
                        f"timer.updatebg 0 {ratio} camera{self.cam.index} background\n"
                    )
                    return

                return runcam

            def live_stop():
                self.cam.context("timer.updatebg --off\n")

            submenu = wx.Menu()
            menu.AppendSubMenu(submenu, _("...refresh"))
            rates = ((2, 1), (1, 1), (1, 2), (1, 5), (1, 10))
            for myrate in rates:
                rate_frame = myrate[0]
                rate_sec = myrate[1]
                item = submenu.Append(wx.ID_ANY, f"{rate_frame}x / {rate_sec}sec")
                self.cam.Bind(
                    wx.EVT_MENU,
                    live_view(rate_frame, rate_sec),
                    id=item.GetId(),
                )
            submenu.AppendSeparator()
            item = submenu.Append(wx.ID_ANY, "Disable")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: live_stop(),
                id=item.GetId(),
            )
            menu.AppendSeparator()
            item = menu.Append(wx.ID_ANY, _("Export Snapshot"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.context(f"camera{self.cam.index} export\n"),
                id=item.GetId(),
            )

            item = menu.Append(wx.ID_ANY, _("Reconnect Camera"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.context(f"camera{self.cam.index} stop start\n"),
                id=item.GetId(),
            )

            item = menu.Append(wx.ID_ANY, _("Stop Camera"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.context(f"camera{self.cam.index} stop\n"),
                id=item.GetId(),
            )

            item = menu.Append(wx.ID_ANY, _("Open CameraInterface"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.context(f"camwin {self.cam.index}\n"),
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
                _("Preserve: {aspect}").format(aspect=self.cam.camera.preserve_aspect),
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
                    f"camera{self.cam.index} perspective reset\n"
                ),
                id=item.GetId(),
            )
            item = menu.Append(wx.ID_ANY, _("Reset Fisheye"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.camera(f"camera{self.cam.index} fisheye reset\n"),
                id=item.GetId(),
            )
            menu.AppendSeparator()

            sub_menu = wx.Menu()
            item = sub_menu.Append(wx.ID_ANY, _("URI Manager"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.context.open(
                    "window/CameraURI", self.cam, index=self.cam.index
                ),
                id=item.GetId(),
            )

            camera_context = self.cam.context.get_context("camera")
            uris = camera_context.setting(list, "uris", [])
            for uri in uris:
                item = sub_menu.Append(wx.ID_ANY, _("URI: {uri}").format(uri=uri), "")
                self.cam.Bind(wx.EVT_MENU, self.cam.swap_camera(uri), id=item.GetId())
            if sub_menu.MenuItemCount:
                sub_menu.AppendSeparator()

            item = sub_menu.Append(
                wx.ID_ANY, _("USB {usb_index}").format(usb_index=0), ""
            )
            self.cam.Bind(wx.EVT_MENU, self.cam.swap_camera(0), id=item.GetId())
            item = sub_menu.Append(
                wx.ID_ANY, _("USB {usb_index}").format(usb_index=1), ""
            )
            self.cam.Bind(wx.EVT_MENU, self.cam.swap_camera(1), id=item.GetId())
            item = sub_menu.Append(
                wx.ID_ANY, _("USB {usb_index}").format(usb_index=2), ""
            )
            self.cam.Bind(wx.EVT_MENU, self.cam.swap_camera(2), id=item.GetId())
            item = sub_menu.Append(
                wx.ID_ANY, _("USB {usb_index}").format(usb_index=3), ""
            )
            self.cam.Bind(wx.EVT_MENU, self.cam.swap_camera(3), id=item.GetId())
            item = sub_menu.Append(
                wx.ID_ANY, _("USB {usb_index}").format(usb_index=4), ""
            )
            self.cam.Bind(wx.EVT_MENU, self.cam.swap_camera(4), id=item.GetId())

            menu.Append(
                wx.ID_ANY,
                _("Manage URIs"),
                sub_menu,
            )
            if menu.MenuItemCount != 0:
                self.cam.PopupMenu(menu)
                menu.Destroy()
            return RESPONSE_ABORT
        if event_type == "doubleclick":
            self.cam.context(f"camera{self.cam.index} background\n")
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
        pos_x, pos_y = self.cam.camera.perspective[self.index]
        self.set_position(pos_x - half, pos_y - half)

    def hit(self):
        return HITCHAIN_HIT

    def process_draw(self, gc):
        if not self.cam.camera.correction_perspective and not self.cam.camera.aspect:
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

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        if event_type == "leftdown":
            return RESPONSE_CONSUME
        if event_type == "move":
            self.cam.camera.perspective[self.index][0] += space_pos[4]
            self.cam.camera.perspective[self.index][1] += space_pos[5]
            if self.parent is not None:
                for w in self.parent:
                    if isinstance(w, CamPerspectiveWidget):
                        w.update()
            self.cam.context.signal("refresh_scene", self.scene.name)
            return RESPONSE_CONSUME


class CamSceneWidget(Widget):
    def __init__(self, scene, camera):
        Widget.__init__(self, scene, all=True)
        self.cam = camera

    def process_draw(self, gc):
        if not self.cam.camera.correction_perspective and not self.cam.camera.aspect:
            if self.cam.camera.perspective is not None:
                if not len(self):
                    for i in range(len(self.cam.camera.perspective)):
                        self.add_widget(
                            -1, CamPerspectiveWidget(self.scene, self.cam, i, False)
                        )
                gc.SetPen(wx.BLACK_DASHED_PEN)
                lines = list(self.cam.camera.perspective)
                lines.append(lines[0])
                gc.StrokeLines(lines)
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
        if isinstance(index, str):
            try:
                index = int(index)
            except ValueError:
                pass
        if index is None:
            index = 0
        super().__init__(640, 480, context, path, parent, **kwds)
        self.camera = self.context.get_context(f"camera/{index}")
        self.panel = CameraPanel(self, wx.ID_ANY, context=self.camera, index=index)
        self.add_module_delegate(self.panel)

        # ==========
        # MENU BAR
        # ==========
        if platform.system() != "Darwin":
            self.CameraInterface_menubar = wx.MenuBar()
            self.create_menu(self.CameraInterface_menubar.Append)
            self.SetMenuBar(self.CameraInterface_menubar)
        # ==========
        # MENUBAR END
        # ==========

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_camera_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("CameraInterface {index}").format(index=index))
        self.Layout()

    def create_menu(self, append):
        def identify_cameras(event=None):
            self.context("camdetect\n")

        wxglade_tmp_menu = wx.Menu()
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Reset Fisheye"), "")
        self.Bind(wx.EVT_MENU, self.panel.reset_fisheye, id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Reset Perspective"), "")
        self.Bind(wx.EVT_MENU, self.panel.reset_perspective, id=item.GetId())
        wxglade_tmp_menu.AppendSeparator()

        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("URI Manager"), "")
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.camera.open(
                "window/CameraURI", self, index=self.panel.index
            ),
            id=item.GetId(),
        )
        camera_root = self.context.get_context("camera")
        uris = camera_root.setting(list, "uris", [])
        camera_root.setting(int, "search_range", 5)
        for uri in uris:
            menu_text = _("URI: {usb_index}").format(usb_index=uri)
            if isinstance(uri, int):
                menu_text = _("Detected USB {usb_index}").format(usb_index=uri)
            item = wxglade_tmp_menu.Append(wx.ID_ANY, menu_text, "")
            self.Bind(wx.EVT_MENU, self.panel.swap_camera(uri), id=item.GetId())

        for i in range(camera_root.search_range):
            if i in uris:
                continue
            item = wxglade_tmp_menu.Append(
                wx.ID_ANY, _("USB {usb_index}").format(usb_index=i), ""
            )
            self.Bind(wx.EVT_MENU, self.panel.swap_camera(i), id=item.GetId())
        wxglade_tmp_menu.AppendSeparator()
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Identify cameras"), "")
        self.Bind(wx.EVT_MENU, identify_cameras, id=item.GetId())

        append(wxglade_tmp_menu, _("Camera"))

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def sub_register(kernel):
        camera = kernel.get_context("camera")

        def camera_click(index=None):
            s = index

            def specific(event=None):
                index = s
                camera.default = index
                v = camera.default
                camera(f"window toggle -m {v} CameraInterface {v}\n")

            return specific

        def detect_usb_cameras(event=None):
            camera("camdetect\n")

        kernel.register(
            "button/preparation/Camera",
            {
                "label": _("Camera"),
                "icon": icons8_camera_50,
                "tip": _("Opens Camera Window"),
                "identifier": "camera_id",
                "action": camera_click(),
                "priority": 3,
                "multi": [
                    {
                        "identifier": "cam0",
                        "label": _("Camera {index}").format(index=0),
                        "action": camera_click(0),
                        "signal": "camset0",
                    },
                    {
                        "identifier": "cam1",
                        "label": _("Camera {index}").format(index=1),
                        "action": camera_click(1),
                        "signal": "camset1",
                    },
                    {
                        "identifier": "cam2",
                        "label": _("Camera {index}").format(index=2),
                        "action": camera_click(2),
                        "signal": "camset2",
                    },
                    {
                        "identifier": "cam3",
                        "label": _("Camera {index}").format(index=3),
                        "action": camera_click(3),
                        "signal": "camset3",
                    },
                    {
                        "identifier": "cam4",
                        "label": _("Camera {index}").format(index=4),
                        "action": camera_click(4),
                        "signal": "camset4",
                    },
                    {
                        "identifier": "id_cam",
                        "label": _("Identify cameras"),
                        "action": detect_usb_cameras,
                    },
                ],
            },
        )
        kernel.register("window/CameraURI", CameraURI)

        @kernel.console_argument("index", type=int)
        @kernel.console_command(
            "camwin", help=_("camwin <index>: Open camera window at index")
        )
        def camera_win(index=None, **kwargs):
            kernel.console(f"window open -m {index} CameraInterface {index}\n")

        @kernel.console_command(
            "camdetect", help=_("camdetect: Tries to detect cameras on the system")
        )
        def cam_detect(**kwargs):
            try:
                import cv2
            except ImportError:
                return

            # Max range to look at
            camera = kernel.get_context("camera")
            camera.setting(int, "search_range", 5)
            camera.setting(list, "uris", [])
            # Reset stuff...
            for _index in range(5):
                if _index in camera.uris:
                    camera.uris.remove(_index)

            max_range = camera.search_range
            if max_range is None or max_range < 1:
                max_range = 5
            found = 0
            found_camera_string = _("Cameras found: {count}")
            progress = wx.ProgressDialog(
                _("Looking for Cameras (Range={max_range})").format(
                    max_range=max_range
                ),
                found_camera_string.format(count=found),
                maximum=max_range,
                parent=None,
                style=wx.PD_APP_MODAL | wx.PD_CAN_ABORT,
            )
            # checks for cameras in the first x USB ports
            first_found = -1
            index = 0
            keepgoing = True
            while index < max_range and keepgoing:
                try:
                    cap = cv2.VideoCapture(index)
                    if cap.read()[0]:
                        if first_found < 0:
                            first_found = index
                        camera.uris.append(index)
                        cap.release()
                        found += 1
                except:
                    pass
                keepgoing = progress.Update(
                    index + 1, found_camera_string.format(count=found)
                )
                index += 1
            progress.Destroy()
            if first_found >= 0:
                kernel.signal(f"camset{first_found}", "camera", (first_found, found))

    @staticmethod
    def submenu():
        return ("Camera", "Camera")


class CameraURIPanel(wx.Panel):
    def __init__(self, *args, context=None, index=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context.get_context("camera")
        if index is None:
            index = 0
        self.index = index
        assert isinstance(self.index, int)
        self.context.setting(list, "uris", [])
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
        self.on_list_refresh()

    def pane_hide(self):
        self.commit()

    def commit(self):
        if not self.changed:
            return
        self.context.signal("camera_uri_changed", True)

    def on_list_refresh(self):
        self.list_uri.DeleteAllItems()
        for i, uri in enumerate(self.context.uris):
            m = self.list_uri.InsertItem(i, str(i))
            if m != -1:
                self.list_uri.SetItem(m, 1, str(uri))

    def on_list_activated(self, event):  # wxGlade: CameraURI.<event_handler>
        index = event.GetIndex()
        new_uri = self.context.uris[index]
        self.context.console(f"camera{self.index} --uri {new_uri} stop start\n")
        try:
            self.GetParent().Close()
        except (TypeError, AttributeError):
            pass

    def on_list_right_clicked(self, event):  # wxGlade: CameraURI.<event_handler>
        index = event.GetIndex()
        element = event.Text
        menu = wx.Menu()
        convert = menu.Append(
            wx.ID_ANY,
            _("Remove {name}").format(name=str(element)[:16]),
            "",
            wx.ITEM_NORMAL,
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
                del self.context.uris[index]
            except KeyError:
                pass
            self.changed = True
            self.on_list_refresh()

        return delete

    def on_tree_popup_duplicate(self, index):
        def duplicate(event=None):
            self.context.uris.insert(index, self.context.uris[index])
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
            dlg.SetValue(self.context.uris[index])
            if dlg.ShowModal() == wx.ID_OK:
                self.context.uris[index] = dlg.GetValue()
                self.changed = True
                self.on_list_refresh()

        return edit

    def on_tree_popup_clear(self, index):
        def delete(event):
            self.context.uris.clear()
            self.changed = True
            self.on_list_refresh()

        return delete

    def on_button_add_uri(self, event=None):  # wxGlade: CameraURI.<event_handler>
        uri = self.text_uri.GetValue()
        if uri is None or uri == "":
            return
        self.context.uris.append(uri)
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
        self.SetTitle(_("URI Manager"))

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def submenu():
        return ("Camera", "Sources")
