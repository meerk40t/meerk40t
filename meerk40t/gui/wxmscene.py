import wx
from wx import aui

from meerk40t.gui.icons import icon_meerk40t, icons8_console_50
from meerk40t.gui.laserrender import LaserRender
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.scene.scene import ScenePanel
from meerk40t.gui.scene.scenewidgets import (
    ElementsWidget,
    GridWidget,
    GuideWidget,
    LaserPathWidget,
    RectSelectWidget,
    ReticleWidget,
    SelectionWidget,
)
from meerk40t.gui.scene.toolwidgets import DrawTool, RectTool, ToolContainer
from meerk40t.gui.wxutils import get_key_name
from meerk40t.kernel import signal_listener
from meerk40t.svgelements import Angle, Length

_ = wx.GetTranslation


def register_panel(window, context):
    # control = wx.aui.AuiNotebook(window, -1, size=(200, 150))
    # panel1 = MeerK40tScenePanel(window, wx.ID_ANY, context=context, index=1)
    # control.AddPage(panel1, "scene1")
    # panel2 = MeerK40tScenePanel(window, wx.ID_ANY, context=context, index=2)
    # control.AddPage(panel2, "scene2")

    control = MeerK40tScenePanel(window, wx.ID_ANY, context=context)
    pane = aui.AuiPaneInfo().CenterPane().Name("scene")
    pane.dock_proportion = 600
    pane.control = control

    # def on_note_page_change(event=None):
    #     if control.GetPageText(control.GetSelection()) == "scene1":
    #         context.kernel.activate_service_path('elements', 'elements')
    #     else:
    #         context.kernel.activate_service_path('elements', "elements1")
    #     context("refresh\n")
    # control.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, on_note_page_change, control)

    window.on_pane_add(pane)
    context.register("pane/console", pane)


class MeerK40tScenePanel(wx.Panel):
    def __init__(self, *args, context=None, index=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.scene = ScenePanel(
            self.context,
            self,
            scene_name="Scene" if index is None else "Scene%d" % index,
            style=wx.EXPAND | wx.WANTS_CHARS,
        )
        self.widget_scene = self.scene.scene
        context = self.context
        self._rotary_view = False
        self.widget_scene.add_scenewidget(SelectionWidget(self.widget_scene))
        self.tool_container = ToolContainer(self.widget_scene)
        self.widget_scene.add_scenewidget(self.tool_container)
        self.widget_scene.add_scenewidget(RectSelectWidget(self.widget_scene))
        self.laserpath_widget = LaserPathWidget(self.widget_scene)
        self.widget_scene.add_scenewidget(self.laserpath_widget)
        self.widget_scene.add_scenewidget(
            ElementsWidget(self.widget_scene, LaserRender(context))
        )
        self.widget_scene.add_scenewidget(GridWidget(self.widget_scene))
        self.widget_scene.add_interfacewidget(GuideWidget(self.widget_scene))
        self.widget_scene.add_interfacewidget(ReticleWidget(self.widget_scene))

        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.scene, 20, wx.EXPAND, 0)
        self.SetSizer(sizer_2)
        sizer_2.Fit(self)
        self.Layout()

        self.scene.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.scene.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.scene.scene_panel.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.scene.scene_panel.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.Bind(wx.EVT_SIZE, self.on_size)

        context.register("tool/draw", DrawTool)
        context.register("tool/rect", RectTool)

        @context.console_command("dialog_fps", hidden=True)
        def fps(**kwargs):
            dlg = wx.TextEntryDialog(
                None, _("Enter FPS Limit"), _("FPS Limit Entry"), ""
            )
            dlg.SetValue("")

            if dlg.ShowModal() == wx.ID_OK:
                fps = dlg.GetValue()
                try:
                    self.widget_scene.set_fps(int(fps))
                except ValueError:
                    pass
            dlg.Destroy()

        @context.console_argument("tool", help=_("tool to use."))
        @context.console_command("tool", help=_("sets a particular tool for the scene"))
        def tool_base(command, channel, _, tool=None, **kwargs):
            if tool is None:
                channel(_("Tools:"))
                channel("none")
                for t in context.match("tool/", suffix=True):
                    channel(t)
                channel(_("-------"))
                return
            try:
                if tool == "none":
                    self.tool_container.set_tool(None)
                else:
                    self.tool_container.set_tool(tool.lower())
            except (KeyError, AttributeError):
                raise SyntaxError

        @context.console_command("laserpath_clear", hidden=True)
        def clear_laser_path(**kwargs):
            self.laserpath_widget.clear_laserpath()
            self.request_refresh()

        @context.console_command("rotaryview", help=_("Rotary View of Scene"))
        def toggle_rotary_view(*args, **kwargs):
            self.toggle_rotary_view()

        @self.context.console_command("scene", output_type="scene")
        def scene(command, _, channel, **kwargs):
            channel("scene: %s" % str(self.widget_scene))
            return "scene", self.widget_scene

        @self.context.console_argument(
            "zoom_x", type=float, help="zoom amount from current"
        )
        @self.context.console_argument(
            "zoom_y", type=float, help="zoom amount from current"
        )
        @self.context.console_command("aspect", input_type="scene")
        def scene(command, _, channel, data, zoom_x=1.0, zoom_y=1.0, **kwargs):
            matrix = data.widget_root.scene_widget.matrix
            matrix.post_scale(zoom_x, zoom_y)
            data.request_refresh()
            channel(str(matrix))
            return "scene", data

        @self.context.console_argument(
            "zoomfactor", type=float, help="zoom amount from current"
        )
        @self.context.console_command("zoom", input_type="scene")
        def scene(command, _, channel, data, zoomfactor=1.0, **kwargs):
            matrix = data.widget_root.scene_widget.matrix
            matrix.post_scale(zoomfactor)
            data.request_refresh()
            channel(str(matrix))
            return "scene", data

        @self.context.console_argument(
            "pan_x", type=float, default=0, help="pan from current position x"
        )
        @self.context.console_argument(
            "pan_y", type=float, default=0, help="pan from current position y"
        )
        @self.context.console_command("pan", input_type="scene")
        def scene(command, _, channel, data, pan_x, pan_y, **kwargs):
            matrix = data.widget_root.scene_widget.matrix
            matrix.post_translate(pan_x, pan_y)
            data.request_refresh()
            channel(str(matrix))
            return "scene", data

        @self.context.console_argument(
            "angle", type=Angle.parse, default=0, help="Rotate scene"
        )
        @self.context.console_command("rotate", input_type="scene")
        def scene(command, _, channel, data, angle, **kwargs):
            matrix = data.widget_root.scene_widget.matrix
            matrix.post_rotate(angle)
            data.request_refresh()
            channel(str(matrix))
            return "scene", data

        @self.context.console_command("reset", input_type="scene")
        def scene(command, _, channel, data, **kwargs):
            matrix = data.widget_root.scene_widget.matrix
            matrix.reset()
            data.request_refresh()
            channel(str(matrix))
            return "scene", data

        @self.context.console_argument("x", type=Length, help="x position")
        @self.context.console_argument("y", type=Length, help="y position")
        @self.context.console_argument("width", type=Length, help="width of view")
        @self.context.console_argument("height", type=Length, help="height of view")
        @self.context.console_command("focus", input_type="scene")
        def scene(command, _, channel, data, x, y, width, height, **kwargs):
            x = x.value(ppi=1000.0, relative_length=self.context.device.bedwidth)
            y = y.value(ppi=1000.0, relative_length=self.context.device.bedheight)
            width = width.value(
                ppi=1000.0, relative_length=self.context.device.bedwidth
            )
            height = height.value(
                ppi=1000.0, relative_length=self.context.device.bedheight
            )
            bbox = (x, y, width, height)
            data.widget_root.focus_viewport_scene(bbox, self.ClientSize)
            data.request_refresh()
            channel(str(data.matrix))
            return "scene", data

    def on_refresh_scene(self, origin, scene_name=None, *args):
        """
        Called by 'refresh_scene' change. To refresh tree.

        :param origin: the path of the originating signal
        :param args:
        :return:
        """
        if scene_name == "Scene":
            self.request_refresh()

    def pane_show(self, *args):
        context = self.context
        context.listen("driver;mode", self.on_driver_mode)
        context.listen("refresh_scene", self.on_refresh_scene)
        context.listen("background", self.on_background_signal)
        context.listen("bed_size", self.bed_changed)
        context.listen("emphasized", self.on_emphasized_elements_changed)
        context.listen("modified", self.on_element_modified)
        context.listen("altered", self.on_element_modified)
        context.listen("units", self.space_changed)
        context("scene focus -10% -10% 110% 110%\n")

    def pane_hide(self, *args):
        context = self.context
        context.unlisten("driver;mode", self.on_driver_mode)
        context.unlisten("refresh_scene", self.on_refresh_scene)
        context.unlisten("background", self.on_background_signal)
        context.unlisten("bed_size", self.bed_changed)
        context.unlisten("emphasized", self.on_emphasized_elements_changed)
        context.unlisten("modified", self.on_element_modified)
        context.unlisten("altered", self.on_element_modified)
        context.unlisten("units", self.space_changed)

    @signal_listener("activate;device")
    def on_activate_device(self, origin, device):
        self.request_refresh()
        self.scene.signal("grid")

    def on_size(self, event):
        if self.context is None:
            return
        self.Layout()
        self.scene.signal("guide")
        self.request_refresh()

    def on_driver_mode(self, origin, state):
        if state == 0:
            self.widget_scene.background_brush = wx.Brush("Grey")
        else:
            self.widget_scene.background_brush = wx.Brush("Red")
        self.widget_scene.request_refresh_for_animation()

    def on_background_signal(self, origin, background):
        background = wx.Bitmap.FromBuffer(*background)
        self.scene.signal("background", background)
        self.request_refresh()

    def space_changed(self, origin, *args):
        self.scene.signal("grid")
        self.scene.signal("guide")
        self.request_refresh(origin)

    def bed_changed(self, origin, *args):
        self.scene.signal("grid")
        # self.scene.signal('guide')
        self.request_refresh(origin)

    def on_emphasized_elements_changed(self, origin, *args):
        self.laserpath_widget.clear_laserpath()
        self.request_refresh(origin)

    def request_refresh(self, *args):
        self.widget_scene.request_refresh(*args)

    def on_element_modified(self, *args):
        self.widget_scene.request_refresh(*args)

    def toggle_rotary_view(self):
        if self._rotary_view:
            self.widget_scene.rotary_stretch()
        else:
            self.widget_scene.rotary_unstretch()
        self._rotary_view = not self._rotary_view

    def on_key_down(self, event):
        keyvalue = get_key_name(event)
        if self.context.bind.trigger(keyvalue):
            event.Skip()

    def on_key_up(self, event):
        keyvalue = get_key_name(event)
        if self.context.bind.untrigger(keyvalue):
            event.Skip()


class SceneWindow(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(1280, 800, *args, **kwds)
        self.panel = MeerK40tScenePanel(self, wx.ID_ANY, context=self.context)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_meerk40t.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Scene"))
        self.Layout()

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()
