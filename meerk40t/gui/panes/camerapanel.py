import wx

from ...kernel import Job
from ...svgelements import Color
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


class CameraPanel(wx.Panel, Job):
    def __init__(self, *args, context=None, gui=None, index: int = 0, **kwds):
        # begin wxGlade: Drag.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.gui = gui
        self.context = context
        self.index = index
        Job.__init__(self, job_name="CamPane%d" % self.index)
        self.process = self.update_camera_frame
        self.run_main = True

        self.camera = None
        self.last_frame_index = -1

        self.camera_setting = self.context.get_context("camera")
        self.setting = self.camera_setting.derive(str(self.index))

        self.root_context = self.context.root

        self.display_camera = ScenePanel(
            self.context,
            self,
            scene_name="CamPaneScene%s" % str(self.index),
            style=wx.EXPAND | wx.WANTS_CHARS,
        )
        self.widget_scene = self.display_camera.scene

        self.__set_properties()
        self.__do_layout()

        self.image_width = -1
        self.image_height = -1
        self.frame_bitmap = None

        self.SetDoubleBuffered(True)
        # end wxGlade

        self.bed_dim = self.context.root
        self.bed_dim.setting(int, "bed_width", 310)
        self.bed_dim.setting(int, "bed_height", 210)

        self.setting.setting(int, "width", 640)
        self.setting.setting(int, "height", 480)
        self.setting.setting(bool, "aspect", False)
        self.setting.setting(str, "preserve_aspect", "xMinYMin meet")
        self.setting.setting(int, "index", 0)
        self.setting.setting(int, "fps", 1)
        self.setting.setting(bool, "correction_fisheye", False)
        self.setting.setting(str, "fisheye", "")
        self.setting.setting(bool, "correction_perspective", False)
        self.setting.setting(str, "perspective", "")
        self.setting.setting(str, "uri", "0")

        try:
            self.camera = self.setting.activate("modifier/Camera")
        except ValueError:

            return

        if self.setting.fisheye is not None and len(self.setting.fisheye) != 0:
            self.fisheye_k, self.fisheye_d = eval(self.setting.fisheye)
        else:
            self.fisheye_k = None
            self.fisheye_d = None

        if self.setting.perspective is not None and len(self.setting.perspective) != 0:
            self.camera.perspective = eval(self.setting.perspective)
        else:
            self.camera.perspective = None
        self.widget_scene.widget_root.set_aspect(self.setting.aspect)

        self.widget_scene.background_brush = wx.WHITE_BRUSH
        self.widget_scene.add_scenewidget(CamSceneWidget(self.widget_scene, self))
        self.widget_scene.add_scenewidget(CamImageWidget(self.widget_scene, self))
        self.widget_scene.add_interfacewidget(
            CamInterfaceWidget(self.widget_scene, self)
        )

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.display_camera, 10, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()

    def __set_properties(self):
        # begin wxGlade: CameraInterface.__set_properties
        pass
        # end wxGlade

    def initialize(self, *args):
        from sys import platform as _platform

        if _platform == "darwin" and not hasattr(self.setting, "_first"):
            self.context("camera%d start -t 1\n" % self.index)
            self.setting._first = False
        else:
            self.context("camera%d start\n" % self.index)
        self.context.schedule(self)
        self.context.listen("refresh_scene", self.on_refresh_scene)
        self.context.kernel.listen("lifecycle;shutdown", "", self.finalize)

    def finalize(self, *args):
        self.context("camera%d stop\n" % self.index)
        self.context.unschedule(self)
        self.context.unlisten("refresh_scene", self.on_refresh_scene)
        self.context.kernel.unlisten("lifecycle;shutdown", "", self.finalize)

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
                0, 0, self.image_width, self.image_height, self.setting.preserve_aspect
            )
        self.frame_bitmap = wx.Bitmap.FromBuffer(
            self.image_width, self.image_height, frame
        )
        if self.camera.perspective is None:
            self.camera.perspective = (
                [0, 0],
                [self.setting.width, 0],
                [self.setting.width, self.setting.height],
                [0, self.setting.height],
            )
        if self.setting.correction_perspective:
            if (
                self.setting.width != self.image_width
                or self.setting.height != self.image_height
            ):
                self.image_width = self.setting.width
                self.image_height = self.setting.height

        self.widget_scene.request_refresh()

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
                self.cam.setting.aspect = not self.cam.setting.aspect
                self.scene.widget_root.set_aspect(self.cam.setting.aspect)
                self.scene.widget_root.set_view(
                    0,
                    0,
                    self.cam.image_width,
                    self.cam.image_height,
                    self.cam.setting.preserve_aspect,
                )

            def set_aspect(aspect):
                def asp(event=None):
                    self.cam.setting.preserve_aspect = aspect
                    self.scene.widget_root.set_aspect(self.cam.setting.aspect)
                    self.scene.widget_root.set_view(
                        0,
                        0,
                        self.cam.image_width,
                        self.cam.image_height,
                        self.cam.setting.preserve_aspect,
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
            if self.cam.setting.aspect:
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
                _("Preserve: %s") % self.cam.setting.preserve_aspect,
                sub_menu,
            )
            menu.AppendSeparator()

            fisheye = menu.Append(wx.ID_ANY, _("Correct Fisheye"), "", wx.ITEM_CHECK)
            fisheye.Check(self.cam.setting.correction_fisheye)
            self.cam.setting.correction_fisheye = fisheye.IsChecked()

            def check_fisheye(event=None):
                self.cam.setting.correction_fisheye = fisheye.IsChecked()

            self.cam.Bind(wx.EVT_MENU, check_fisheye, fisheye)

            perspect = menu.Append(
                wx.ID_ANY, _("Correct Perspective"), "", wx.ITEM_CHECK
            )
            perspect.Check(self.cam.setting.correction_perspective)
            self.cam.setting.correction_perspective = perspect.IsChecked()

            def check_perspect(event=None):
                self.cam.setting.correction_perspective = perspect.IsChecked()

            self.cam.Bind(wx.EVT_MENU, check_perspect, perspect)
            menu.AppendSeparator()
            item = menu.Append(wx.ID_ANY, _("Reset Perspective"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.setting("camera%d perspective reset\n" % self.index),
                id=item.GetId(),
            )
            item = menu.Append(wx.ID_ANY, _("Reset Fisheye"), "")
            self.cam.Bind(
                wx.EVT_MENU,
                lambda e: self.cam.setting("camera%d fisheye reset\n" % self.index),
                id=item.GetId(),
            )
            menu.AppendSeparator()

            sub_menu = wx.Menu()
            camera_setting = self.cam.context.get_context("camera")
            keylist = camera_setting.kernel.load_persistent_string_dict(
                camera_setting.path, suffix=True
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
            not self.cam.setting.correction_perspective
            and self.cam.camera.perspective
            and not self.cam.setting.aspect
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
                self.cam.setting.perspective = repr(perspective)
                self.cam.context.signal("refresh_scene", 1)
            return RESPONSE_CONSUME


class CamSceneWidget(Widget):
    def __init__(self, scene, camera):
        Widget.__init__(self, scene, all=True)
        self.cam = camera

    def process_draw(self, gc):
        if not self.cam.setting.correction_perspective and not self.cam.setting.aspect:
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
