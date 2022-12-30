import wx
from wx import aui

from ..core.bindalias import keymap_execute
from ..svgelements import Angle, Color, Length
from .icons import icon_meerk40t
from .laserrender import LaserRender
from .mwindow import MWindow
from .scene.scene import ScenePanel
from .scene.scenewidgets import (
    MILS_IN_MM,
    ElementsWidget,
    GridWidget,
    GuideWidget,
    LaserPathWidget,
    RectSelectWidget,
    ReticleWidget,
    SelectionWidget,
)
from .scene.toolwidgets import DrawTool, RectTool, ToolContainer
from .wxutils import get_key_name

_ = wx.GetTranslation


def register_panel_scene(window, context):
    # self.notebook = wx.aui.AuiNotebook(self, -1, size=(200, 150))
    # self._mgr.AddPane(self.notebook, aui.AuiPaneInfo().CenterPane().Name("scene"))
    # self.notebook.AddPage(self.scene, "scene")

    panel = MeerK40tScenePanel(window, wx.ID_ANY, context=context)
    pane = aui.AuiPaneInfo().CenterPane().Name("scene")
    pane.dock_proportion = 600
    pane.control = panel

    window.on_pane_add(pane)
    context.register("pane/scene", pane)


class MeerK40tScenePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.scene = ScenePanel(
            self.context, self, scene_name="Scene", style=wx.EXPAND | wx.WANTS_CHARS
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

        self.triggered_keys = dict()
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
            "aspect", type=str, help="aspect of the scene to color"
        )
        @self.context.console_argument(
            "color", type=Color, help="color to apply to scene"
        )
        @self.context.console_command("color", input_type="scene")
        def scene_color(command, _, channel, data, aspect=None, color=None, **kwargs):
            if aspect is None:
                for key in dir(self.context):
                    if key.startswith("color_"):
                        channel(key[6:])
            else:
                if aspect == "unset":
                    self.context.signal("theme", True)
                    return "scene", data
                if color is None:
                    raise SyntaxError(_("No color given."))
                color_key = f"color_{aspect}"
                if hasattr(self.context, color_key):
                    setattr(self.context, color_key, color.hexa)
                    channel(_("Scene aspect color is set."))
                    self.context.signal("theme", False)
                else:
                    channel(_("%s is not a known scene color command") % aspect)

            return "scene", data

        @self.context.console_argument(
            "zoom_x", type=float, help="zoom amount from current"
        )
        @self.context.console_argument(
            "zoom_y", type=float, help="zoom amount from current"
        )
        @self.context.console_command("aspect", input_type="scene")
        def scene_aspect(command, _, channel, data, zoom_x=1.0, zoom_y=1.0, **kwargs):
            matrix = data.widget_root.scene_widget.matrix
            matrix.post_scale(zoom_x, zoom_y)
            data.request_refresh()
            channel(str(matrix))
            return "scene", data

        @self.context.console_argument(
            "zoomfactor", type=float, help="zoom amount from current"
        )
        @self.context.console_command("zoom", input_type="scene")
        def scene_zoomfactor(command, _, channel, data, zoomfactor=1.0, **kwargs):
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
        def scene_pan(command, _, channel, data, pan_x, pan_y, **kwargs):
            matrix = data.widget_root.scene_widget.matrix
            matrix.post_translate(pan_x, pan_y)
            data.request_refresh()
            channel(str(matrix))
            return "scene", data

        @self.context.console_argument(
            "angle", type=Angle.parse, default=0, help="Rotate scene"
        )
        @self.context.console_command("rotate", input_type="scene")
        def scene_rotate(command, _, channel, data, angle, **kwargs):
            matrix = data.widget_root.scene_widget.matrix
            matrix.post_rotate(angle)
            data.request_refresh()
            channel(str(matrix))
            return "scene", data

        @self.context.console_command("reset", input_type="scene")
        def scene_reset(command, _, channel, data, **kwargs):
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
        def scene_focus(command, _, channel, data, x, y, width, height, **kwargs):
            bed_dim = self.context.root
            x = x.value(ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM)
            y = y.value(ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM)
            width = width.value(
                ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
            )
            height = height.value(
                ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
            )
            bbox = (x, y, width, height)
            data.widget_root.focus_viewport_scene(bbox, self.ClientSize)
            data.request_refresh()
            channel(str(data.matrix))
            return "scene", data

    def on_refresh_scene(self, origin, *args):
        """
        Called by 'refresh_scene' change. To refresh tree.

        :param origin: the path of the originating signal
        :param args:
        :return:
        """
        self.request_refresh()

    def initialize(self, *args):
        context = self.context
        context.listen("driver;mode", self.on_driver_mode)
        context.listen("refresh_scene", self.on_refresh_scene)
        context.listen("background", self.on_background_signal)
        context.listen("theme", self.on_theme_change)
        context.listen("bed_size", self.bed_changed)
        context.listen("emphasized", self.on_emphasized_elements_changed)
        context.listen("modified", self.on_element_modified)
        context.listen("altered", self.on_element_modified)
        context.listen("units", self.space_changed)
        context("scene focus -4% -4% 104% 104%\n")

    def finalize(self, *args):
        context = self.context
        context.unlisten("driver;mode", self.on_driver_mode)
        context.unlisten("refresh_scene", self.on_refresh_scene)
        context.unlisten("background", self.on_background_signal)
        context.unlisten("theme", self.on_theme_change)
        context.unlisten("bed_size", self.bed_changed)
        context.unlisten("emphasized", self.on_emphasized_elements_changed)
        context.unlisten("modified", self.on_element_modified)
        context.unlisten("altered", self.on_element_modified)
        context.unlisten("units", self.space_changed)

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

    def on_theme_change(self, origin, theme=None):
        self.scene.signal("theme", theme)
        self.request_refresh(origin)

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
        if not keyvalue:
            event.Skip()
            return
        if keyvalue == "menu":
            self.scene.on_right_mouse_down(event)
            return
        if keyvalue not in self.triggered_keys:
            if keymap_execute(self.context, keyvalue, keydown=True):
                self.triggered_keys[keyvalue] = 1
                return
        event.Skip()

    def on_key_up(self, event):
        keyvalue = get_key_name(event)
        if not keyvalue:
            event.Skip()
            return
        if keyvalue == "menu":
            self.scene.on_right_mouse_up(event)
            return
        if keyvalue in self.triggered_keys:
            del self.triggered_keys[keyvalue]
        if keymap_execute(self.context, keyvalue, keydown=False):
            return
        event.Skip()


class SceneWindow(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(1280, 800, *args, **kwds)
        self.panel = MeerK40tScenePanel(self, wx.ID_ANY, context=self.context)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_meerk40t.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Scene"))
        self.Layout()

    def window_open(self):
        self.panel.initialize()

    def window_close(self):
        self.panel.finalize()
