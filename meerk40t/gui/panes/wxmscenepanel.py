import wx
from wx import aui

from meerk40t.gui.icons import icons8_console_50, icon_meerk40t
from meerk40t.gui.laserrender import LaserRender
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.scene.scene import ScenePanel
from meerk40t.gui.scene.scenewidgets import SelectionWidget, RectSelectWidget, LaserPathWidget, ElementsWidget, \
    GridWidget, GuideWidget, ReticleWidget, MILS_IN_MM
from meerk40t.gui.scene.toolwidgets import ToolContainer, DrawTool, RectTool
from meerk40t.gui.wxutils import get_key_name

_ = wx.GetTranslation


def register_panel(window, context):
    # self.notebook = wx.aui.AuiNotebook(self, -1, size=(200, 150))
    # self._mgr.AddPane(self.notebook, aui.AuiPaneInfo().CenterPane().Name("scene"))
    # self.notebook.AddPage(self.scene, "scene")

    panel = MeerK40tScenePanel(window, wx.ID_ANY, context=context)
    pane = aui.AuiPaneInfo().CenterPane().Name("scene")
    pane.dock_proportion = 600
    pane.control = panel

    window.on_pane_add(pane)
    context.register("pane/console", pane)


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

        self.scene.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.scene.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.scene.scene_panel.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.scene.scene_panel.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.Bind(wx.EVT_SIZE, self.on_size)

        context.register("tool/draw", DrawTool)
        context.register("tool/rect", RectTool)

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
        context.listen("bed_size", self.bed_changed)
        context.listen("emphasized", self.on_emphasized_elements_changed)
        context.listen("modified", self.on_element_modified)
        context.listen("altered", self.on_element_modified)
        context.listen("units", self.space_changed)

    def finalize(self, *args):
        context = self.context
        context.unlisten("driver;mode", self.on_driver_mode)
        context.unlisten("refresh_scene", self.on_refresh_scene)
        context.unlisten("background", self.on_background_signal)
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
        keymap = self.context.keymap
        if keyvalue in keymap:
            action = keymap[keyvalue]
            self.context(action + "\n")
        else:
            event.Skip()

    def on_key_up(self, event):
        keyvalue = get_key_name(event)
        keymap = self.context.keymap
        if keyvalue in keymap:
            action = keymap[keyvalue]
            if action.startswith("+"):
                # Keyup commands only trigger if the down command started with +
                action = "-" + action[1:]
                self.context(action + "\n")
        else:
            event.Skip()


class SceneWindow(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(581, 410, *args, **kwds)
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
