import platform
import random

import wx
from wx import aui

from meerk40t.core.element_types import elem_nodes
from meerk40t.core.units import UNITS_PER_PIXEL, Length
from meerk40t.gui.icons import (
    STD_ICON_SIZE,
    icon_meerk40t,
    icons8_bed_50,
    icons8_menu_50,
    icons8_r_black,
    icons8_r_white,
    icons8_reference,
    icons8_ungroup_objects_50,
)
from meerk40t.gui.laserrender import DRAW_MODE_BACKGROUND, DRAW_MODE_GUIDES, LaserRender
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.scene.scenepanel import ScenePanel
from meerk40t.gui.scenewidgets.attractionwidget import AttractionWidget
from meerk40t.gui.scenewidgets.bedwidget import BedWidget
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
from meerk40t.gui.utilitywidgets.checkboxwidget import CheckboxWidget
from meerk40t.gui.utilitywidgets.cyclocycloidwidget import CyclocycloidWidget
from meerk40t.gui.utilitywidgets.seekbarwidget import SeekbarWidget
from meerk40t.gui.utilitywidgets.togglewidget import ToggleWidget
from meerk40t.gui.wxutils import get_key_name, is_navigation_key
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
    pane = aui.AuiPaneInfo().CenterPane().MinSize(200, 200).Name("scene")
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

    window.on_pane_create(pane)
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
            scene_name="Scene" if index is None else f"Scene{index}",
            style=wx.EXPAND | wx.WANTS_CHARS,
        )
        self.widget_scene = self.scene.scene
        context = self.context
        self.widget_scene.add_scenewidget(AttractionWidget(self.widget_scene))
        self.widget_scene.add_scenewidget(SelectionWidget(self.widget_scene))
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
        self._keybind_channel = self.context.channel("keybinds")

        if platform.system() == "Windows":

            def charhook(event):
                keyvalue = get_key_name(event)
                if is_navigation_key(keyvalue):
                    if self._keybind_channel:
                        self._keybind_channel(
                            f"Scene, char_hook used for key_down: {keyvalue}"
                        )
                    self.on_key_down(event)
                    event.Skip()
                else:
                    event.DoAllowNextEvent()

            self.scene.Bind(wx.EVT_CHAR_HOOK, charhook)
        self.scene.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.scene.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.scene.scene_panel.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.scene.scene_panel.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.Bind(wx.EVT_SIZE, self.on_size)

        self._tool_widget = None

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

        buttonsize = int(STD_ICON_SIZE / 2)
        context.kernel.register(
            "button/align/refob",
            {
                "label": _("Ref. Obj."),
                "icon": icons8_r_white,
                "tip": _("Toggle Reference Object Status"),
                "action": lambda v: self.toggle_ref_obj(),
                "size": buttonsize,
                "identifier": "refobj",
                "rule_enabled": lambda cond: len(
                    list(context.kernel.elements.elems(emphasized=True))
                )
                == 1,
            },
        )

        # Provide a reference to current scene in root context
        setattr(self.context.root, "mainscene", self.widget_scene)

        @context.console_command("dialog_fps", hidden=True)
        def dialog_fps(**kwgs):
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
        def tool_menu(channel, _, **kwgs):
            orgx = 5
            orgy = 5
            # Are guides drawn?
            if self.context.draw_mode & DRAW_MODE_GUIDES == 0:
                orgx += 25
                orgy += 25
            if self._tool_widget is not None:
                visible = self._tool_widget.visible
                self._tool_widget.show(not visible)
                self.widget_scene.request_refresh()

            if self._tool_widget is None:
                self._tool_widget = ToggleWidget(
                    self.widget_scene,
                    orgx,
                    orgy,
                    orgx + 25,
                    orgy + 25,
                    icons8_menu_50.GetBitmap(use_theme=False),
                    "button/tool",
                )
                self.widget_scene.widget_root.interface_widget.add_widget(
                    -1,
                    self._tool_widget,
                )
            channel(_("Added tool widget to interface"))

        @context.console_command("seek_bar", hidden=True)
        def seek_bar(channel, _, **kwgs):
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

        @context.console_command("checkbox", hidden=True)
        def checkbox(channel, _, **kwgs):
            def checked(value):
                print(value)

            widget = CheckboxWidget(
                self.widget_scene,
                25,
                25,
                text="Example",
                tool_tip="Example's tool tip",
                checked=checked,
            )
            self.widget_scene.widget_root.interface_widget.add_widget(-1, widget)
            channel(_("Added example_checkbox to interface"))
            self.widget_scene.request_refresh()

        @context.console_command("cyclocycloid", hidden=True)
        def cyclocycloid(channel, _, **kwgs):
            self.widget_scene.widget_root.scene_widget.add_widget(
                0, CyclocycloidWidget(self.widget_scene)
            )
            channel(_("Added cyclocycloid widget to scene."))

        @context.console_command("toast", hidden=True)
        def toast_scene(remainder, **kwgs):
            self.widget_scene.toast(remainder)

        @context.console_argument("tool", help=_("tool to use."))
        @context.console_command("tool", help=_("sets a particular tool for the scene"))
        def tool_base(command, channel, _, tool=None, **kwgs):
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
        def clear_laser_path(**kwgs):
            self.laserpath_widget.clear_laserpath()
            self.request_refresh()

        @self.context.console_command("scene", output_type="scene")
        def scene(command, _, channel, **kwgs):
            channel(f"scene: {str(self.widget_scene)}")
            return "scene", self.widget_scene

        @self.context.console_argument(
            "aspect", type=str, help="aspect of the scene to color"
        )
        @self.context.console_argument(
            "color", type=str, help="color to apply to scene"
        )
        @self.context.console_command("color", input_type="scene")
        def scene_color(command, _, channel, data, aspect=None, color=None, **kwgs):
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
                    random_color = (
                        f"#"
                        f"{random.randint(0, 255):02X}"
                        f"{random.randint(0, 255):02X}"
                        f"{random.randint(0, 255):02X}"
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
                    channel(
                        _("{name} is not a known scene color command").format(
                            name=aspect
                        )
                    )

            return "scene", data

        @self.context.console_argument(
            "zoom_x", type=float, help="zoom amount from current"
        )
        @self.context.console_argument(
            "zoom_y", type=float, help="zoom amount from current"
        )
        @self.context.console_command("aspect", input_type="scene")
        def scene_aspect(command, _, channel, data, zoom_x=1.0, zoom_y=1.0, **kwgs):
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
        def scene_zoomfactor(command, _, channel, data, zoomfactor=1.0, **kwgs):
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
        def scene_pan(command, _, channel, data, pan_x, pan_y, **kwgs):
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
        def scene_rotate(command, _, channel, data, angle, **kwgs):
            matrix = data.widget_root.scene_widget.matrix
            if angle is not None:
                matrix.post_rotate(angle)
                data.request_refresh()
            channel(str(matrix))
            return "scene", data

        @self.context.console_command("reset", input_type="scene")
        def scene_reset(command, _, channel, data, **kwgs):
            matrix = data.widget_root.scene_widget.matrix
            matrix.reset()
            data.request_refresh()
            channel(str(matrix))
            return "scene", data

        @self.context.console_argument("x", type=str, help="x position")
        @self.context.console_argument("y", type=str, help="y position")
        @self.context.console_argument("width", type=str, help="width of view")
        @self.context.console_argument("height", type=str, help="height of view")
        @self.context.console_option(
            "animate",
            "a",
            type=bool,
            action="store_true",
            help="perform focus with animation",
        )
        @self.context.console_command("focus", input_type="scene")
        def scene_focus(
            command, _, channel, data, x, y, width, height, animate=False, **kwgs
        ):
            if height is None:
                raise CommandSyntaxError("x, y, width, height not specified")
            try:
                x = self.context.device.length(x, 0, unitless=UNITS_PER_PIXEL)
                y = self.context.device.length(y, 1, unitless=UNITS_PER_PIXEL)
                width = self.context.device.length(width, 0, unitless=UNITS_PER_PIXEL)
                height = self.context.device.length(height, 1, unitless=UNITS_PER_PIXEL)
            except ValueError:
                raise CommandSyntaxError("Not a valid length.")
            bbox = (x, y, width, height)
            matrix = data.widget_root.scene_widget.matrix
            data.widget_root.focus_viewport_scene(bbox, self.Size, animate=animate)
            data.request_refresh()
            channel(str(matrix))
            return "scene", data

        @context.console_command("reference")
        def make_reference(**kwgs):
            # Take first emphasized element
            for e in self.context.elements.flat(types=elem_nodes, emphasized=True):
                self.widget_scene.reference_object = e
                break
            self.context.signal("reference")

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
            **kwgs,
        ):
            if target is None:
                channel(_("Grid-Parameters:"))
                p_state = _("On") if self.widget_scene.draw_grid_primary else _("Off")
                channel(f"Primary: {p_state}")
                if self.widget_scene.draw_grid_secondary:
                    channel(f"Secondary: {_('On')}")
                    if self.widget_scene.grid_secondary_cx is not None:
                        channel(
                            f"   cx: {Length(amount=self.widget_scene.grid_secondary_cx).length_mm}"
                        )
                    if self.widget_scene.grid_secondary_cy is not None:
                        channel(
                            f"   cy: {Length(amount=self.widget_scene.grid_secondary_cy).length_mm}"
                        )
                    if self.widget_scene.grid_secondary_scale_x is not None:
                        channel(
                            f"   scale-x: {self.widget_scene.grid_secondary_scale_x:.2f}"
                        )
                    if self.widget_scene.grid_secondary_scale_y is not None:
                        channel(
                            f"   scale-y: {self.widget_scene.grid_secondary_scale_y:.2f}"
                        )
                else:
                    channel(f"Secondary: {_('Off')}")
                if self.widget_scene.draw_grid_circular:
                    channel(f"Circular: {_('On')}")
                    if self.widget_scene.grid_circular_cx is not None:
                        channel(
                            f"   cx: {Length(amount=self.widget_scene.grid_circular_cx).length_mm}"
                        )
                    if self.widget_scene.grid_circular_cy is not None:
                        channel(
                            f"   cy: {Length(amount=self.widget_scene.grid_circular_cy).length_mm}"
                        )
                else:
                    channel(f"Circular: {_('Off')}")
                return
            else:
                target = target.lower()
                if target[0] == "p":
                    self.widget_scene.draw_grid_primary = (
                        not self.widget_scene.draw_grid_primary
                    )
                    channel(
                        _("Turned primary grid on")
                        if self.widget_scene.draw_grid_primary
                        else _("Turned primary grid off")
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

    def toggle_ref_obj(self):
        for e in self.scene.context.elements.flat(types=elem_nodes, emphasized=True):
            if self.widget_scene.reference_object == e:
                self.widget_scene.reference_object = None
            else:
                self.widget_scene.reference_object = e
            break
        self.context.signal("reference")
        self.request_refresh()

    @signal_listener("draw_mode")
    def on_draw_mode(self, origin, *args):
        if self._tool_widget is not None:
            orgx = 5
            orgy = 5
            # Are guides drawn?
            if self.context.draw_mode & DRAW_MODE_GUIDES == 0:
                orgx += 25
                orgy += 25
            self._tool_widget.set_position(orgx, orgy)

    @signal_listener("scene_right_click")
    def on_scene_right(self, origin, *args):
        def zoom_to_bed(event=None):
            zoom = self.context.zoom_margin
            self.context(f"scene focus -a {-zoom}% {-zoom}% {zoom+100}% {zoom+100}%\n")

        def zoom_to_selected(event=None):
            bbox = self.context.elements.selected_area()
            if bbox is None:
                zoom_to_bed(event=event)
            else:
                zfact = self.context.zoom_margin / 100.0

                x_delta = (bbox[2] - bbox[0]) * zfact
                y_delta = (bbox[3] - bbox[1]) * zfact
                x0 = Length(
                    amount=bbox[0] - x_delta, relative_length=self.context.device.width
                ).length_mm
                y0 = Length(
                    amount=bbox[1] - y_delta, relative_length=self.context.device.height
                ).length_mm
                x1 = Length(
                    amount=bbox[2] + x_delta, relative_length=self.context.device.width
                ).length_mm
                y1 = Length(
                    amount=bbox[3] + y_delta, relative_length=self.context.device.height
                ).length_mm
                self.context(f"scene focus -a {x0} {y0} {x1} {y1}\n")

        def toggle_background(event=None):
            """
            Toggle the draw mode for the background
            """
            self.widget_scene.context.draw_mode ^= DRAW_MODE_BACKGROUND
            self.widget_scene.request_refresh()

        def toggle_grid(gridtype):
            if gridtype == "primary":
                self.widget_scene.draw_grid_primary = (
                    not self.widget_scene.draw_grid_primary
                )
            elif gridtype == "secondary":
                self.widget_scene.draw_grid_secondary = (
                    not self.widget_scene.draw_grid_secondary
                )
            elif gridtype == "circular":
                self.widget_scene.draw_grid_circular = (
                    not self.widget_scene.draw_grid_circular
                )
            self.widget_scene.request_refresh()

        def toggle_grid_p(event=None):
            toggle_grid("primary")

        def toggle_grid_s(event=None):
            toggle_grid("secondary")

        def toggle_grid_c(event=None):
            toggle_grid("circular")

        def remove_background(event=None):
            self.widget_scene._signal_widget(
                self.widget_scene.widget_root, "background", None
            )
            self.widget_scene.request_refresh()

        def stop_auto_update(event=None):
            self.context("timer.updatebg --off\n")

        gui = self
        menu = wx.Menu()
        id1 = menu.Append(
            wx.ID_ANY,
            _("Show Background"),
            _("Display the background picture in the scene"),
            wx.ITEM_CHECK,
        )
        self.Bind(wx.EVT_MENU, toggle_background, id=id1.GetId())
        menu.Check(
            id1.GetId(),
            (self.widget_scene.context.draw_mode & DRAW_MODE_BACKGROUND == 0),
        )
        id2 = menu.Append(
            wx.ID_ANY,
            _("Show Primary Grid"),
            _("Display the primary grid in the scene"),
            wx.ITEM_CHECK,
        )
        self.Bind(wx.EVT_MENU, toggle_grid_p, id=id2.GetId())
        menu.Check(id2.GetId(), self.widget_scene.draw_grid_primary)
        id3 = menu.Append(
            wx.ID_ANY,
            _("Show Secondary Grid"),
            _("Display the secondary grid in the scene"),
            wx.ITEM_CHECK,
        )
        self.Bind(wx.EVT_MENU, toggle_grid_s, id=id3.GetId())
        menu.Check(id3.GetId(), self.widget_scene.draw_grid_secondary)
        id4 = menu.Append(
            wx.ID_ANY,
            _("Show Circular Grid"),
            _("Display the circular grid in the scene"),
            wx.ITEM_CHECK,
        )
        self.Bind(wx.EVT_MENU, toggle_grid_c, id=id4.GetId())
        menu.Check(id4.GetId(), self.widget_scene.draw_grid_circular)
        if self.widget_scene.has_background:
            menu.AppendSeparator()
            id5 = menu.Append(wx.ID_ANY, _("Remove Background"), "")
            self.Bind(wx.EVT_MENU, remove_background, id=id5.GetId())
        # Do we have a timer called .updatebg?
        we_have_a_job = False
        try:
            obj = self.context.kernel.jobs["timer.updatebg"]
            if obj is not None:
                we_have_a_job = True
        except KeyError:
            pass
        if we_have_a_job:
            self.Bind(
                wx.EVT_MENU,
                lambda e: stop_auto_update(),
                menu.Append(
                    wx.ID_ANY,
                    _("Stop autoupdate"),
                    _("Stop automatic refresh of background image"),
                ),
            )
        menu.AppendSeparator()
        self.Bind(
            wx.EVT_MENU,
            lambda e: zoom_to_bed(),
            menu.Append(
                wx.ID_ANY,
                _("&Zoom to Bed"),
                _("View the whole laser bed"),
            ),
        )
        if self.context.elements.has_emphasis():
            self.Bind(
                wx.EVT_MENU,
                lambda e: zoom_to_selected(),
                menu.Append(
                    wx.ID_ANY,
                    _("Zoom to &Selected"),
                    _("Fill the scene area with the selected elements"),
                ),
            )

        if menu.MenuItemCount != 0:
            gui.PopupMenu(menu)
            menu.Destroy()

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

    @signal_listener("bedsize")
    def on_bedsize_simple(self, origin, nocmd = None, *args):
        # The next two are more or less the same, so we remove the direct invocation...
        # self.context.device.realize()
        issue_command = True
        if nocmd is not None and nocmd:
            issue_command = False
        if issue_command:
            self.context("viewport_update\n")
        self.scene.signal("guide")
        self.scene.signal("grid")
        self.request_refresh(origin)

    @signal_listener("magnet-attraction")
    def on_magnet(self, origin, strength, *args):
        strength = int(strength)
        if strength < 0:
            strength = 0
        self.scene.scene.magnet_attraction = strength

    def pane_show(self, *args):
        zl = self.context.zoom_margin
        self.context(f"scene focus -{zl}% -{zl}% {100 + zl}% {100 + zl}%\n")

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
            self.widget_scene.overrule_background = None
        else:
            self.widget_scene.overrule_background = wx.RED
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
        self.widget_scene.context.elements.default_stroke = color

    @signal_listener("selfill")
    def on_selfill(self, origin, rgb, *args):
        # print (origin, rgb, args)
        if rgb[0] == 255 and rgb[1] == 255 and rgb[2] == 255:
            color = None
        else:
            color = Color(rgb[0], rgb[1], rgb[2])
        self.widget_scene.context.elements.default_fill = color

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
        if self._keybind_channel:
            self._keybind_channel(f"Scene key_down: {keyvalue}.")
        if self.context.bind.trigger(keyvalue):
            if self._keybind_channel:
                self._keybind_channel(f"Scene key_down: {keyvalue} executed.")
        else:
            if self._keybind_channel:
                self._keybind_channel(f"Scene key_down: {keyvalue} unfound.")
        event.Skip()

    def on_key_up(self, event, log=True):
        keyvalue = get_key_name(event)
        if self._keybind_channel:
            self._keybind_channel(f"Scene key_up: {keyvalue}.")
        if self.context.bind.untrigger(keyvalue):
            if self._keybind_channel:
                self._keybind_channel(f"Scene key_up: {keyvalue} executed.")
        else:
            if self._keybind_channel:
                self._keybind_channel(f"Scene key_up: {keyvalue} unfound.")
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
