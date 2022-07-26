import random

import wx
from wx import aui

from meerk40t.core.element_types import elem_nodes
from meerk40t.core.units import Length
from meerk40t.gui.icons import icon_meerk40t, icons8_menu_50
from meerk40t.gui.laserrender import LaserRender
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.scene.scenepanel import ScenePanel
from meerk40t.gui.scenewidgets.attractionwidget import AttractionWidget
from meerk40t.gui.scenewidgets.bedwidget import BedWidget
from meerk40t.gui.utilitywidgets.cyclocycloidwidget import CyclocycloidWidget
from meerk40t.gui.scenewidgets.elementswidget import ElementsWidget
from meerk40t.gui.scenewidgets.gridwidget import GridWidget
from meerk40t.gui.scenewidgets.guidewidget import GuideWidget
from meerk40t.gui.scenewidgets.laserpathwidget import LaserPathWidget
from meerk40t.gui.scenewidgets.rectselectwidget import RectSelectWidget
from meerk40t.gui.scenewidgets.reticlewidget import ReticleWidget
from meerk40t.gui.scenewidgets.selectionwidget import SelectionWidget
from meerk40t.gui.toolwidgets.toolcircle import CircleTool
from meerk40t.gui.toolwidgets.toolcontainer import ToolContainer
from meerk40t.gui.toolwidgets.tooldraw import DrawTool
from meerk40t.gui.toolwidgets.toolellipse import EllipseTool
from meerk40t.gui.toolwidgets.toolmeasure import MeasureTool
from meerk40t.gui.toolwidgets.toolpoint import PointTool
from meerk40t.gui.toolwidgets.toolpolygon import PolygonTool
from meerk40t.gui.toolwidgets.toolpolyline import PolylineTool
from meerk40t.gui.toolwidgets.toolrect import RectTool
from meerk40t.gui.toolwidgets.toolrelocate import RelocateTool
from meerk40t.gui.toolwidgets.toolribbon import RibbonTool
from meerk40t.gui.toolwidgets.tooltext import TextTool
from meerk40t.gui.toolwidgets.toolvector import VectorTool
from meerk40t.gui.utilitywidgets.seekbarwidget import SeekbarWidget
from meerk40t.gui.utilitywidgets.togglewidget import ToggleWidget
from meerk40t.gui.wxutils import get_key_name
from meerk40t.kernel import CommandSyntaxError, signal_listener
from meerk40t.svgelements import Angle, Color

_ = wx.GetTranslation


def register_panel_scene(window, context):
    # control = wx.aui.AuiNotebook(window, -1, size=(200, 150))
    # panel1 = MeerK40tScenePanel(window, wx.ID_ANY, context=context, index=1)
    # control.AddPage(panel1, "scene1")
    # panel2 = MeerK40tScenePanel(window, wx.ID_ANY, context=context, index=2)
    # control.AddPage(panel2, "scene2")

    control = MeerK40tScenePanel(window, wx.ID_ANY, context=context)
    pane = aui.AuiPaneInfo().CenterPane().Name("scene")
    pane.dock_proportion = 600
    pane.control = control
    pane.hide_menu = True

    # def on_note_page_change(event=None):
    #     if control.GetPageText(control.GetSelection()) == "scene1":
    #         context.kernel.activate_service_path('elements', 'elements')
    #     else:
    #         context.kernel.activate_service_path('elements', "elements1")
    #     context("refresh\n")
    # control.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, on_note_page_change, control)

    window.on_pane_add(pane)
    context.register("pane/scene", pane)


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
        self.widget_scene.add_scenewidget(SelectionWidget(self.widget_scene))
        self.widget_scene.add_scenewidget(AttractionWidget(self.widget_scene))
        self.tool_container = ToolContainer(self.widget_scene)
        self.widget_scene.add_scenewidget(self.tool_container)
        self.widget_scene.add_scenewidget(RectSelectWidget(self.widget_scene))
        self.laserpath_widget = LaserPathWidget(self.widget_scene)
        self.widget_scene.add_scenewidget(self.laserpath_widget)
        self.widget_scene.add_scenewidget(
            ElementsWidget(self.widget_scene, LaserRender(context))
        )
        # Let the grid resize itself
        self.widget_scene.auto_tick = True

        self.widget_scene.add_scenewidget(GridWidget(self.widget_scene))
        self.widget_scene.add_scenewidget(BedWidget(self.widget_scene))
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
        context.register("tool/polyline", PolylineTool)
        context.register("tool/polygon", PolygonTool)
        context.register("tool/point", PointTool)
        context.register("tool/circle", CircleTool)
        context.register("tool/ellipse", EllipseTool)
        context.register("tool/relocate", RelocateTool)
        context.register("tool/text", TextTool)
        context.register("tool/vector", VectorTool)
        context.register("tool/measure", MeasureTool)
        context.register("tool/ribbon", RibbonTool)

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

        @context.console_command("tool_menu", hidden=True)
        def tool_menu(channel, _, **kwargs):
            self.widget_scene.widget_root.interface_widget.add_widget(
                -1,
                ToggleWidget(
                    self.widget_scene,
                    5,
                    5,
                    5 + 25,
                    5 + 25,
                    icons8_menu_50.GetBitmap(),
                    "button/tool",
                ),
            )
            channel(_("Added tool widget to interface"))

        @context.console_command("seek_bar", hidden=True)
        def seek_bar(channel, _, **kwargs):
            def changed(values, seeker):
                print(values)

            widget = SeekbarWidget(
                self.widget_scene, 25, 25, 200, 25, 0, 1000.0, changed
            )

            def clicked(values, seeker):
                self.widget_scene.widget_root.interface_widget.remove_widget(widget)
                self.widget_scene.request_refresh()

            widget.add_value(500.0)
            widget.add_value(250.0)
            widget.clicked = clicked
            self.widget_scene.widget_root.interface_widget.add_widget(-1, widget)

            channel(_("Added example_seekbar to interface"))
            self.widget_scene.request_refresh()

        @context.console_command("cyclocycloid", hidden=True)
        def cyclocycloid(channel, _, **kwargs):
            self.widget_scene.widget_root.scene_widget.add_widget(
                0, CyclocycloidWidget(self.widget_scene)
            )
            channel(_("Added cyclocycloid widget to scene."))

        @context.console_command("toast", hidden=True)
        def toast_scene(remainder, **kwargs):
            self.widget_scene.toast(remainder)

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
                raise CommandSyntaxError

        @context.console_command("laserpath_clear", hidden=True)
        def clear_laser_path(**kwargs):
            self.laserpath_widget.clear_laserpath()
            self.request_refresh()

        @self.context.console_command("scene", output_type="scene")
        def scene(command, _, channel, **kwargs):
            channel("scene: %s" % str(self.widget_scene))
            return "scene", self.widget_scene

        @self.context.console_argument(
            "aspect", type=str, help="aspect of the scene to color"
        )
        @self.context.console_argument(
            "color", type=str, help="color to apply to scene"
        )
        @self.context.console_command("color", input_type="scene")
        def scene_color(command, _, channel, data, aspect=None, color=None, **kwargs):
            """
            Sets the scene colors. This is usually done with `scene color <aspect> <color>` which
            sets the aspect to the color specified. `scene color unset` unsets all colors and returns
            them to the default settings. `scene color random` changes all colors to random.
            """
            if aspect is None:
                for key in dir(self.context):
                    if key.startswith("color_"):
                        channel(key[6:])
            else:
                color_key = f"color_{aspect}"
                if aspect == "unset":  # reset all
                    self.widget_scene.colors.set_default_colors()
                    self.context.signal("theme", True)
                    return "scene", data
                if aspect == "random":  # reset all
                    self.widget_scene.colors.set_random_colors()
                    self.context.signal("theme", True)
                    return "scene", data
                if color == "unset":  # reset one
                    setattr(self.context, color_key, "default")
                    self.context.signal("theme", True)
                    return "scene", data
                if color == "random":  # randomize one
                    random_color = "#%02X%02X%02X" % (
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255),
                    )
                    setattr(self.context, color_key, random_color)
                    self.context.signal("theme", True)
                    return "scene", data

                if color is None:
                    channel(
                        _(
                            "No color given! Please provide one like 'green', '#RRBBGGAA' (i.e. #FF000080 for semitransparent red)"
                        )
                    )
                    return "scene", data
                color = Color(color)
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
            if zoom_x is None or zoom_y is None:
                raise CommandSyntaxError
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
            if zoomfactor is None:
                zoomfactor = 1.0
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
            if pan_x is None or pan_y is None:
                return
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

        @self.context.console_argument("x", type=str, help="x position")
        @self.context.console_argument("y", type=str, help="y position")
        @self.context.console_argument("width", type=str, help="width of view")
        @self.context.console_argument("height", type=str, help="height of view")
        @self.context.console_command("focus", input_type="scene")
        def scene_focus(command, _, channel, data, x, y, width, height, **kwargs):
            if height is None:
                raise CommandSyntaxError("x, y, width, height not specified")
            try:
                x = self.context.device.length(x, 0)
                y = self.context.device.length(y, 1)
                width = self.context.device.length(width, 0)
                height = self.context.device.length(height, 1)
            except ValueError:
                raise CommandSyntaxError("Not a valid length.")
            bbox = (x, y, width, height)
            data.widget_root.focus_viewport_scene(bbox, self.ClientSize)
            data.request_refresh()
            channel(str(data.matrix))
            return "scene", data

        @context.console_command("reference")
        def make_reference(**kwargs):
            # Take first emphasized element
            for e in self.context.elements.flat(types=elem_nodes, emphasized=True):
                self.widget_scene.reference_object = e
                break

        # Establishes commands
        @context.console_argument(
            "target", type=str, help=_("Target (one of primary, secondary, circular")
        )
        @context.console_argument("ox", type=str, help=_("X-Position of origin"))
        @context.console_argument("oy", type=str, help=_("Y-Position of origin"))
        @context.console_argument(
            "scalex", type=str, help=_("Scaling of X-Axis for secondary")
        )
        @context.console_argument(
            "scaley", type=str, help=_("Scaling of Y-Axis for secondary")
        )
        @context.console_command(
            "grid",
            help=_("grid <target> <rows> <x_distance> <y_distance> <origin>"),
            input_type="scene",
        )
        def show_grid(
            command,
            channel,
            _,
            target=None,
            ox=None,
            oy=None,
            scalex=None,
            scaley=None,
            **kwargs,
        ):
            if target is None:
                channel(_("Grid-Parameters:"))
                channel(
                    "Primary: %s" % _("On")
                    if self.widget_scene.draw_grid_primary
                    else _("Off")
                )
                if self.widget_scene.draw_grid_secondary:
                    channel("Secondary: %s" % _("On"))
                    if not self.widget_scene.grid_secondary_cx is None:
                        channel(
                            "   cx: %s"
                            % Length(
                                amount=self.widget_scene.grid_secondary_cx
                            ).length_mm
                        )
                    if not self.widget_scene.grid_secondary_cy is None:
                        channel(
                            "   cy: %s"
                            % Length(
                                amount=self.widget_scene.grid_secondary_cy
                            ).length_mm
                        )
                    if not self.widget_scene.grid_secondary_scale_x is None:
                        channel(
                            "   scale-x: %.2f"
                            % self.widget_scene.grid_secondary_scale_x
                        )
                    if not self.widget_scene.grid_secondary_scale_y is None:
                        channel(
                            "   scale-y: %.2f"
                            % self.widget_scene.grid_secondary_scale_y
                        )
                else:
                    channel("Secondary: %s" % _("Off"))
                if self.widget_scene.draw_grid_circular:
                    channel("Circular: %s" % _("On"))
                    if not self.widget_scene.grid_circular_cx is None:
                        channel(
                            "   cx: %s"
                            % Length(
                                amount=self.widget_scene.grid_circular_cx
                            ).length_mm
                        )
                    if not self.widget_scene.grid_circular_cy is None:
                        channel(
                            "   cy: %s"
                            % Length(
                                amount=self.widget_scene.grid_circular_cy
                            ).length_mm
                        )
                else:
                    channel("Circular: %s" % _("Off"))
                return
            else:
                target = target.lower()
                if target[0] == "p":
                    self.widget_scene.draw_grid_primary = (
                        not self.widget_scene.draw_grid_primary
                    )
                    channel(
                        _(
                            "Turned primary grid on"
                            if self.widget_scene.draw_grid_primary
                            else "Turned primary grid off"
                        )
                    )
                    self.scene.signal("guide")
                    self.scene.signal("grid")
                    self.request_refresh()
                elif target[0] == "s":
                    self.widget_scene.draw_grid_secondary = (
                        not self.widget_scene.draw_grid_secondary
                    )
                    if self.widget_scene.draw_grid_secondary:

                        if ox is None:
                            self.widget_scene.grid_secondary_cx = None
                            self.widget_scene.grid_secondary_cy = None
                            scalex = None
                            scaley = None
                        else:
                            if oy is None:
                                oy = ox
                            self.widget_scene.grid_secondary_cx = float(
                                Length(ox, relative_length=self.context.device.width)
                            )
                            self.widget_scene.grid_secondary_cy = float(
                                Length(oy, relative_length=self.context.device.height)
                            )
                        if scalex is None:
                            rot = self.scene.context.rotary
                            if rot.rotary_enabled:
                                scalex = rot.scale_x
                                scaley = rot.scale_y
                            else:
                                scalex = 1.0
                                scaley = 1.0
                        else:
                            scalex = float(scalex)
                        if scaley is None:
                            scaley = scalex
                        else:
                            scaley = float(scaley)
                        self.widget_scene.grid_secondary_scale_x = scalex
                        self.widget_scene.grid_secondary_scale_y = scaley
                    channel(
                        _(
                            "Turned secondary grid on"
                            if self.widget_scene.draw_grid_secondary
                            else "Turned secondary grid off"
                        )
                    )
                    self.scene.signal("guide")
                    self.scene.signal("grid")
                    self.request_refresh()
                elif target[0] == "c":
                    self.widget_scene.draw_grid_circular = (
                        not self.widget_scene.draw_grid_circular
                    )
                    if self.widget_scene.draw_grid_circular:
                        if ox is None:
                            self.widget_scene.grid_circular_cx = None
                            self.widget_scene.grid_circular_cy = None
                        else:
                            if oy is None:
                                oy = ox
                            self.widget_scene.grid_circular_cx = float(
                                Length(ox, relative_length=self.context.device.width)
                            )
                            self.widget_scene.grid_circular_cy = float(
                                Length(oy, relative_length=self.context.device.height)
                            )
                    channel(
                        _(
                            "Turned circular grid on"
                            if self.widget_scene.draw_grid_circular
                            else "Turned circular grid off"
                        )
                    )
                    self.scene.signal("guide")
                    self.scene.signal("grid")
                    self.request_refresh()
                else:
                    channel(_("Target needs to be one of primary, secondary, circular"))

    @signal_listener("refresh_scene")
    def on_refresh_scene(self, origin, scene_name=None, *args):
        """
        Called by 'refresh_scene' change. To refresh tree.

        @param origin: the path of the originating signal
        @param scene_name: Scene to refresh on if matching
        @param args:
        @return:
        """
        if scene_name == "Scene":
            self.request_refresh()

    @signal_listener("magnet-attraction")
    def on_magnet(self, origin, strength, *args):
        strength = int(strength)
        if strength < 0:
            strength = 0
        self.scene.scene.magnet_attraction = strength

    def pane_show(self, *args):
        self.context(
            "scene focus -{zoom}% -{zoom}% {zoom100}% {zoom100}%\n".format(
                zoom=self.context.zoom_level, zoom100=100 + self.context.zoom_level
            )
        )

    def pane_hide(self, *args):
        pass

    @signal_listener("activate;device")
    def on_activate_device(self, origin, device):
        self.scene.signal("grid")
        self.request_refresh()

    def on_size(self, event):
        if self.context is None:
            return
        self.Layout()
        self.scene.signal("guide")
        self.request_refresh()

    @signal_listener("driver;mode")
    def on_driver_mode(self, origin, state):
        if state == 0:
            self.widget_scene.background_brush = wx.Brush("Grey")
        else:
            self.widget_scene.background_brush = wx.Brush("Red")
        self.widget_scene.request_refresh_for_animation()

    @signal_listener("background")
    def on_background_signal(self, origin, background):
        background = wx.Bitmap.FromBuffer(*background)
        self.scene.signal("background", background)
        self.request_refresh()

    @signal_listener("units")
    def space_changed(self, origin, *args):
        self.scene.signal("guide")
        self.scene.signal("grid")
        self.request_refresh(origin)

    @signal_listener("bed_size")
    def bed_changed(self, origin, *args):
        self.scene.signal("grid")
        # self.scene.signal('guide')
        self.request_refresh(origin)

    @signal_listener("emphasized")
    def on_emphasized_elements_changed(self, origin, *args):
        self.scene.signal("emphasized")
        self.laserpath_widget.clear_laserpath()
        self.request_refresh(origin)

    def request_refresh(self, *args):
        self.widget_scene.request_refresh(*args)

    @signal_listener("altered")
    @signal_listener("modified")
    def on_element_modified(self, *args):
        self.scene.signal("modified")
        self.widget_scene.request_refresh(*args)

    @signal_listener("element_added")
    @signal_listener("tree_changed")
    def on_elements_added(self, origin, nodes=None, *args):
        self.scene.signal("element_added", nodes)
        # There may be a smarter way to eliminate unnecessary rebuilds, but it's doing the job...
        # self.context.signal("rebuild_tree")
        self.context.signal("refresh_tree", nodes)
        self.widget_scene.request_refresh()

    @signal_listener("theme")
    def on_theme_change(self, origin, theme=None):
        self.scene.signal("theme", theme)
        self.request_refresh(origin)

    @signal_listener("selstroke")
    def on_selstroke(self, origin, rgb, *args):
        # print (origin, rgb, args)
        if rgb[0] == 255 and rgb[1] == 255 and rgb[2] == 255:
            color = None
        else:
            color = Color(rgb[0], rgb[1], rgb[2])
        self.widget_scene.default_stroke = color

    @signal_listener("selfill")
    def on_selfill(self, origin, rgb, *args):
        # print (origin, rgb, args)
        if rgb[0] == 255 and rgb[1] == 255 and rgb[2] == 255:
            color = None
        else:
            color = Color(rgb[0], rgb[1], rgb[2])
        self.widget_scene.default_fill = color

    @signal_listener("selstrokewidth")
    def on_selstrokewidth(self, origin, stroke_width, *args):
        # Stroke_width is a text
        # print("Signal with %s" % stroke_width)
        sw = float(Length(stroke_width))
        for e in self.context.elements.flat(types=elem_nodes, emphasized=True):
            try:
                e.stroke_width = sw
                e.altered()
            except AttributeError:
                # Ignore and carry on...
                continue
        self.request_refresh()

    def on_key_down(self, event):
        keyvalue = get_key_name(event)
        if self.context.bind.trigger(keyvalue):
            pass
        event.Skip()

    def on_key_up(self, event):
        keyvalue = get_key_name(event)
        if self.context.bind.untrigger(keyvalue):
            pass
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
