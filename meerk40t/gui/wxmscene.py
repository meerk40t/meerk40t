import platform
import random
import time

import wx
from PIL import Image
from wx import aui

from meerk40t.core.elements.element_types import elem_nodes
from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.units import UNITS_PER_PIXEL, Angle, Length
from meerk40t.gui.icons import STD_ICON_SIZE, icon_meerk40t, icons8_r_white, icons8_text
from meerk40t.gui.laserrender import DRAW_MODE_BACKGROUND, DRAW_MODE_GUIDES, LaserRender
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.propertypanels.imageproperty import ContourPanel
from meerk40t.gui.scene.scenepanel import ScenePanel

# from meerk40t.gui.scenewidgets.affinemover import AffineMover
from meerk40t.gui.scenewidgets.attractionwidget import AttractionWidget
from meerk40t.gui.scenewidgets.bedwidget import BedWidget
from meerk40t.gui.scenewidgets.elementswidget import ElementsWidget
from meerk40t.gui.scenewidgets.gridwidget import GridWidget
from meerk40t.gui.scenewidgets.guidewidget import GuideWidget
from meerk40t.gui.scenewidgets.laserpathwidget import LaserPathWidget
from meerk40t.gui.scenewidgets.machineoriginwidget import MachineOriginWidget

# from meerk40t.gui.scenewidgets.nodeselector import NodeSelector
from meerk40t.gui.scenewidgets.rectselectwidget import RectSelectWidget
from meerk40t.gui.scenewidgets.reticlewidget import ReticleWidget

# from meerk40t.gui.scenewidgets.selectionwidget import SelectionWidget
from meerk40t.gui.toolwidgets.toolcircle import CircleTool
from meerk40t.gui.toolwidgets.toolcontainer import ToolContainer
from meerk40t.gui.toolwidgets.tooldraw import DrawTool
from meerk40t.gui.toolwidgets.toolellipse import EllipseTool
from meerk40t.gui.toolwidgets.toolimagecut import ImageCutTool
from meerk40t.gui.toolwidgets.toolline import LineTool
from meerk40t.gui.toolwidgets.toollinetext import LineTextTool
from meerk40t.gui.toolwidgets.toolmeasure import MeasureTool
from meerk40t.gui.toolwidgets.toolnodeedit import EditTool
from meerk40t.gui.toolwidgets.toolnodemove import NodeMoveTool
from meerk40t.gui.toolwidgets.toolparameter import ParameterTool
from meerk40t.gui.toolwidgets.toolplacement import PlacementTool
from meerk40t.gui.toolwidgets.toolpoint import PointTool
from meerk40t.gui.toolwidgets.toolpointmove import PointMoveTool
from meerk40t.gui.toolwidgets.toolpolygon import PolygonTool
from meerk40t.gui.toolwidgets.toolpolyline import PolylineTool
from meerk40t.gui.toolwidgets.toolrect import RectTool
from meerk40t.gui.toolwidgets.toolrelocate import RelocateTool
from meerk40t.gui.toolwidgets.toolribbon import RibbonTool
from meerk40t.gui.toolwidgets.tooltabedit import TabEditTool
from meerk40t.gui.toolwidgets.tooltext import TextTool
from meerk40t.gui.toolwidgets.toolvector import VectorTool
from meerk40t.gui.utilitywidgets.checkboxwidget import CheckboxWidget
from meerk40t.gui.utilitywidgets.cyclocycloidwidget import CyclocycloidWidget
from meerk40t.gui.utilitywidgets.harmonograph import HarmonographWidget
from meerk40t.gui.utilitywidgets.seekbarwidget import SeekbarWidget
from meerk40t.gui.wxutils import get_key_name, is_navigation_key
from meerk40t.kernel import CommandSyntaxError, signal_listener
from meerk40t.svgelements import Color, Matrix

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


class ContourDetectionDialog(wx.Dialog):
    def __init__(self, parent, context, node):
        super().__init__(
            parent, wx.ID_ANY, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.context = context
        self._init_ui(node)
        self._start_dialog()

    def _init_ui(self, node):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        panel = ContourPanel(
            self,
            wx.ID_ANY,
            context=self.context,
            node=node,
            simplified=True,
            direct_mode=True,
        )
        main_sizer.Add(panel, 1, wx.EXPAND, 0)
        buttons = self.CreateStdDialogButtonSizer(wx.OK)
        main_sizer.Add(buttons, 0, wx.EXPAND, 0)
        panel.pane_active()
        self.SetSizer(main_sizer)
        self.Layout()

    def _start_dialog(self):
        win_wd = self.context.setting(int, "win_bgcontour_width", 700)
        win_ht = self.context.setting(int, "win_bgcontour_height", 500)
        self.SetSize(win_wd, win_ht)
        self.CenterOnParent()

    def end_dialog(self):
        # Save window size for next time
        win_wd, win_ht = self.GetSize()
        self.context.win_bgcontour_width = win_wd
        self.context.win_bgcontour_height = win_ht
        self.context.signal("refresh_scene", "Scene")


class MeerK40tScenePanel(wx.Panel):
    def __init__(self, *args, context=None, index=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.scene = ScenePanel(
            self.context,
            self,
            scene_name="Scene" if index is None else f"Scene{index}",
            style=wx.EXPAND | wx.WANTS_CHARS,
        )
        self.scene.start_scene()
        self.widget_scene = self.scene.scene

        self.tool_active = False
        self.modif_active = False
        self.ignore_snap = False
        self.suppress_selection = False
        self._reference = None  # Reference Object

        # Stuff for magnet-lines
        self.magnet_x = []
        self.magnet_y = []
        self._magnet_attraction = 2
        # 0 off, `1..x` increasing strength (quadratic behaviour)
        self.magnet_attract_x = True  # Shall the X-Axis be affected
        self.magnet_attract_y = True  # Shall the Y-Axis be affected
        self.magnet_attract_c = True  # Shall the center be affected

        self.context.setting(bool, "clear_magnets", True)

        # Save / Load the content of magnets
        from os.path import join

        self._magnet_file = join(
            self.context.kernel.os_information["WORKDIR"], "magnets.cfg"
        )
        self.load_magnets()
        # Add a plugin routine to be called at the time of a full new start
        context.kernel.register(
            "reset_routines/magnets", self.clear_magnets_conditionally
        )

        self.active_tool = "none"

        self._last_snap_position = None
        self._last_snap_ts = 0

        context = self.context
        # Add in snap-to-grid functionality.
        self.widget_scene.add_scenewidget(AttractionWidget(self.widget_scene))

        # Tool container - Widget to hold tools.
        self.tool_container = ToolContainer(self.widget_scene)
        self.widget_scene.add_scenewidget(self.tool_container)

        # Rectangular selection.
        self.widget_scene.add_scenewidget(RectSelectWidget(self.widget_scene))

        # Laser-Path blue-line drawer.
        self.laserpath_widget = LaserPathWidget(self.widget_scene)
        self.widget_scene.add_scenewidget(self.laserpath_widget)

        # Draw elements in scene.
        self.widget_scene.add_scenewidget(
            ElementsWidget(self.widget_scene, LaserRender(context))
        )

        # Draw Machine Origin widget.
        self.widget_scene.add_scenewidget(MachineOriginWidget(self.widget_scene))

        # Draw Grid.
        self.grid = GridWidget(self.widget_scene)
        self.widget_scene.add_scenewidget(self.grid)

        # Draw Bed
        self.widget_scene.add_scenewidget(BedWidget(self.widget_scene))

        # Draw Interface Guide.
        self.widget_scene.add_interfacewidget(GuideWidget(self.widget_scene))

        # Draw Interface Laser-Position
        self.widget_scene.add_interfacewidget(ReticleWidget(self.widget_scene))

        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.scene, 20, wx.EXPAND, 0)
        self.SetSizer(sizer_2)
        sizer_2.Fit(self)
        self.Layout()

        # Allow Scene update from now on (are suppressed by default during startup phase)
        self.widget_scene.suppress_changes = False
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

        self.Bind(wx.EVT_SIZE, self.on_size)

        self._tool_widget = None

        context.register("tool/draw", DrawTool)
        context.register("tool/rect", RectTool)
        context.register("tool/line", LineTool)
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
        context.register("tool/linetext", LineTextTool)
        context.register("tool/edit", EditTool)
        context.register("tool/placement", PlacementTool)
        context.register("tool/nodemove", NodeMoveTool)
        context.register("tool/pointmove", PointMoveTool)
        context.register("tool/parameter", ParameterTool)
        context.register("tool/imagecut", ImageCutTool)
        context.register("tool/tabedit", TabEditTool)

        bsize_normal = STD_ICON_SIZE

        def proxy_linetext():
            if context.fonts.have_hershey_fonts():
                context.kernel.elements("tool linetext\n")
            else:
                context.kernel.elements("window open HersheyFontManager\n")

        context.kernel.register(
            "button/tools/Linetext",
            {
                "label": _("Vector Text"),
                "icon": icons8_text,
                "tip": _("Add a vector text element"),
                "action": lambda v: proxy_linetext(),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "linetext",
            },
        )

        context.kernel.register(
            "button/align/refob",
            {
                "label": _("Ref. Obj."),
                "icon": icons8_r_white,
                "tip": _("Toggle Reference Object Status"),
                "action": lambda v: self.toggle_ref_obj(),
                "size": bsize_normal,
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

        # @context.console_command("tool_menu", hidden=True)
        # def tool_menu(channel, _, **kwgs):
        #     orgx = 5
        #     orgy = 5
        #     # Are guides drawn?
        #     if self.context.draw_mode & DRAW_MODE_GUIDES == 0:
        #         orgx += 25
        #         orgy += 25
        #     if self._tool_widget is not None:
        #         visible = self._tool_widget.visible
        #         self._tool_widget.show(not visible)
        #         self.widget_scene.request_refresh()

        #     if self._tool_widget is None:
        #         self._tool_widget = ToggleWidget(
        #             self.widget_scene,
        #             orgx,
        #             orgy,
        #             orgx + 25,
        #             orgy + 25,
        #             icons8_menu.GetBitmap(use_theme=False),
        #             "button/tool",
        #         )
        #         self.widget_scene.widget_root.interface_widget.add_widget(
        #             -1,
        #             self._tool_widget,
        #         )
        #     channel(_("Added tool widget to interface"))

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

        @context.console_command("harmonograph", hidden=True)
        def harmonograph(channel, _, **kwgs):
            self.widget_scene.widget_root.scene_widget.add_widget(
                0, HarmonographWidget(self.widget_scene)
            )
            self.widget_scene.request_refresh()
            channel(_("Added harmonograph widget to scene."))

        @context.console_command("toast", hidden=True)
        def toast_scene(remainder, **kwgs):
            self.widget_scene.toast(remainder)

        @context.console_argument("tool", help=_("tool to use."))
        @context.console_command("tool", help=_("sets a particular tool for the scene"))
        def tool_base(command, channel, _, tool=None, remainder=None, **kwgs):
            if tool is None:
                channel(_("Tools:"))
                channel("none")
                for t in context.match("tool/", suffix=True):
                    channel(t)
                channel(_("-------"))
                return
            toolbar = context.lookup("ribbonbar/tools")
            # Reset the edit toolbar
            if toolbar is not None:
                toolbar.remove_page("toolcontainer")
                for pages in toolbar.pages:
                    pages.visible = True
                toolbar.validate_current_page()
                toolbar.apply_enable_rules()
                toolbar.modified()
            try:
                if tool == "none":
                    success, response = self.tool_container.set_tool(None, remainder)
                    channel(response)
                    if not success:
                        return
                else:
                    success, response = self.tool_container.set_tool(
                        tool.lower(), remainder
                    )
                    channel(response)
                    if not success:
                        return
                    # Reset the edit toolbar
                    if toolbar is not None:
                        toolbar.remove_page("toolcontainer")
                        tool_values = list(
                            context.find(f"button/secondarytool_{tool}/.*")
                        )
                        # print(f"button/secondarytool_{tool}/.*\n{tool_values}")
                        if tool_values is not None and len(tool_values) > 0:
                            for pages in toolbar.pages:
                                pages.visible = False
                            newpage = toolbar.add_page(
                                "toolcontainer",
                                "toolcontainer",
                                "Select",
                                None,
                            )

                            select_panel = toolbar.add_panel(
                                "toolback",
                                newpage,
                                "toolback",
                                "Select",
                                None,
                            )
                            select_values = (
                                (
                                    context.lookup("button/select/Scene"),
                                    "button/select/Scene",
                                    "Select",
                                ),
                            )
                            select_panel.set_buttons(select_values)

                            tool_panel = toolbar.add_panel(
                                "toolutil",
                                newpage,
                                "toolutil",
                                "Tools",
                                None,
                            )
                            tool_panel.set_buttons(tool_values)
                            newpage.visible = True
                            toolbar.validate_current_page()
                            toolbar.apply_enable_rules()

                        toolbar.modified()

            except (KeyError, AttributeError):
                raise CommandSyntaxError

        @context.console_argument("page", help=_("page to use."))
        @context.console_command(
            "page", help=_("Switches to a particular page in the ribbonbar")
        )
        def page_base(command, channel, _, page=None, **kwgs):
            # No need to store it beyond
            context = self.context.root
            context.setting(str, "_active_page", "")
            if page is None:
                channel(_("Active Page: {page}").format(page=context._active_page))
                return
            else:
                page = page.lower()
                if page == "none":
                    page = "home"
                context._active_page = page
                self.context.signal("page", page)

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
                if aspect == "unsetbright":  # reset all
                    self.widget_scene.colors.set_default_colors(brighter=True)
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
            "angle", type=Angle, default=0, help="Rotate scene"
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
            if animate:
                overrule = self.context.setting(bool, "suppress_focus_animation", False)
                if overrule:
                    animate = False

            if height is None:
                raise CommandSyntaxError("x, y, width, height not specified")
            try:
                x = Length(
                    x,
                    relative_length=self.context.device.view.width,
                    unitless=UNITS_PER_PIXEL,
                )
                y = Length(
                    y,
                    relative_length=self.context.device.view.height,
                    unitless=UNITS_PER_PIXEL,
                )
                width = Length(
                    width,
                    relative_length=self.context.device.view.width,
                    unitless=UNITS_PER_PIXEL,
                )
                height = Length(
                    height,
                    relative_length=self.context.device.view.height,
                    unitless=UNITS_PER_PIXEL,
                )
            except ValueError:
                raise CommandSyntaxError("Not a valid length.")
            bbox = (x, y, width, height)
            matrix = data.widget_root.scene_widget.matrix
            data.widget_root.focus_viewport_scene(bbox, self.Size, animate=animate)
            data.request_refresh()
            channel(str(matrix))
            return "scene", data

        @context.console_command("feature_request")
        def send_developer_feature(remainder="", **kwgs):
            from .wxmeerk40t import send_data_to_developers

            send_data_to_developers("feature_request.txt", remainder)

        @context.console_command("bug")
        def send_developer_bug(remainder="", **kwgs):
            from .wxmeerk40t import send_data_to_developers

            send_data_to_developers("bug.txt", remainder)

        @context.console_command("reference")
        def make_reference(**kwgs):
            # Take first emphasized element
            for e in self.context.elements.flat(types=elem_nodes, emphasized=True):
                self.reference_object = e
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
                p_state = _("On") if self.grid.draw_grid_primary else _("Off")
                channel(f"Primary: {p_state}")
                if self.grid.draw_grid_secondary:
                    channel(f"Secondary: {_('On')}")
                    if self.grid.grid_secondary_cx is not None:
                        channel(
                            f"   cx: {Length(amount=self.grid.grid_secondary_cx).length_mm}"
                        )
                    if self.grid.grid_secondary_cy is not None:
                        channel(
                            f"   cy: {Length(amount=self.grid.grid_secondary_cy).length_mm}"
                        )
                    if self.grid.grid_secondary_scale_x is not None:
                        channel(f"   scale-x: {self.grid.grid_secondary_scale_x:.2f}")
                    if self.grid.grid_secondary_scale_y is not None:
                        channel(f"   scale-y: {self.grid.grid_secondary_scale_y:.2f}")
                else:
                    channel(f"Secondary: {_('Off')}")
                if self.grid.draw_grid_circular:
                    channel(f"Circular: {_('On')}")
                    if self.grid.grid_circular_cx is not None:
                        channel(
                            f"   cx: {Length(amount=self.grid.grid_circular_cx).length_mm}"
                        )
                    if self.grid.grid_circular_cy is not None:
                        channel(
                            f"   cy: {Length(amount=self.grid.grid_circular_cy).length_mm}"
                        )
                else:
                    channel(f"Circular: {_('Off')}")
                return
            else:
                target = target.lower()
                if target[0] == "p":
                    self.grid.draw_grid_primary = not self.grid.draw_grid_primary
                    channel(
                        _("Turned primary grid on")
                        if self.grid.draw_grid_primary
                        else _("Turned primary grid off")
                    )
                    self.scene.signal("guide")
                    self.scene.signal("grid")
                    self.widget_scene.reset_snap_attraction()
                    self.request_refresh()
                elif target[0] == "s":
                    self.grid.draw_grid_secondary = not self.grid.draw_grid_secondary
                    if self.grid.draw_grid_secondary:
                        if ox is None:
                            self.grid.grid_secondary_cx = None
                            self.grid.grid_secondary_cy = None
                            scalex = None
                            scaley = None
                        else:
                            if oy is None:
                                oy = ox
                            self.grid.grid_secondary_cx = float(
                                Length(
                                    ox, relative_length=self.context.device.view.width
                                )
                            )
                            self.grid.grid_secondary_cy = float(
                                Length(
                                    oy, relative_length=self.context.device.view.height
                                )
                            )
                        if scalex is None:
                            rot = self.scene.context.device.rotary
                            if rot.active:
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
                        self.grid.grid_secondary_scale_x = scalex
                        self.grid.grid_secondary_scale_y = scaley
                    channel(
                        _(
                            "Turned secondary grid on"
                            if self.grid.draw_grid_secondary
                            else "Turned secondary grid off"
                        )
                    )
                    self.scene.signal("guide")
                    self.scene.signal("grid")
                    self.request_refresh()
                elif target[0] == "c":
                    self.grid.draw_grid_circular = not self.grid.draw_grid_circular
                    if self.grid.draw_grid_circular:
                        if ox is None:
                            self.grid.grid_circular_cx = None
                            self.grid.grid_circular_cy = None
                        else:
                            if oy is None:
                                oy = ox
                            self.grid.grid_circular_cx = float(
                                Length(
                                    ox, relative_length=self.context.device.view.width
                                )
                            )
                            self.grid.grid_circular_cy = float(
                                Length(
                                    oy, relative_length=self.context.device.view.height
                                )
                            )
                    channel(
                        _(
                            "Turned circular grid on"
                            if self.grid.draw_grid_circular
                            else "Turned circular grid off"
                        )
                    )
                    self.scene.signal("guide")
                    self.scene.signal("grid")
                    self.request_refresh()
                else:
                    channel(_("Target needs to be one of primary, secondary, circular"))

        # Establishes magnet commands
        @context.console_argument(
            "action", type=str, help=_("Action: clear or set / delete with coordinate")
        )
        @context.console_argument("axis", type=str, help=_("Axis (X or Y)"))
        @context.console_argument("pos", type=str, help=_("Position for magnetline"))
        @context.console_command(
            "magnet",
            help=_("magnet <action> <axis> <position>"),
            input_type=("scene", None),
        )
        def magnet_set(
            command,
            channel,
            _,
            action=None,
            axis=None,
            pos=None,
            **kwarg,
        ):
            def info(opt_msg):
                channel(
                    _("You need to provide the intended action:")
                    + "\n"
                    + _("clear x - clear y : will clear all magnets on the given axis")
                    + "\n"
                    + _(
                        "set x <pos> - set y <pos>: will set a magnet line on the given axis"
                    )
                    + "\n"
                    + _(
                        "delete x <pos> - delete y <pos>: will delete the magnet line on the given axis"
                    )
                    + _(
                        "split x <count> - split y <count>: will generate <count> lines between the selection boundaries on the given axis"
                    )
                )
                if opt_msg:
                    channel(opt_msg)

            if action is None or axis is None or axis.upper() not in ("X", "Y"):
                info("")
                return
            action = action.lower()
            axis = axis.upper()
            value = None
            if action == "split":
                if pos:
                    try:
                        value = int(pos)
                    except ValueError:
                        info(f"Invalid count: {pos}")
                        return

                if value is None or value <= 0:
                    info(_("You need to provide a number of splits"))
                    return
            else:
                if pos:
                    try:
                        rel_len = (
                            self.context.device.view.width
                            if axis == "X"
                            else self.context.device.view.height
                        )
                        value = float(Length(pos, relative_length=rel_len))
                    except ValueError:
                        info(f"Invalid length: {pos}")
                        return

                if action != "clear" and value is None:
                    info(_("You need to provide a position"))
                    return

            if action == "clear":
                if axis == "X":
                    count = len(self.magnet_x)
                    self.magnet_x.clear()
                else:
                    count = len(self.magnet_y)
                    self.magnet_y.clear()
                self.save_magnets()
                self.context.signal("refresh_scene", "Scene")
                channel(
                    _("Deleted {count} magnet lines on axis {axis}").format(
                        axis=axis, count=count
                    )
                )
            elif action == "split":
                bb = self.context.elements.selected_area()
                if bb is None:
                    channel(_("Nothing selected"))
                    return

                min_v = bb[0] if axis == "X" else bb[1]
                max_v = bb[2] if axis == "X" else bb[3]
                count = value + 1
                delta = (max_v - min_v) / count
                mvalue = min_v
                while mvalue + delta < max_v:
                    mvalue += delta
                    if axis == "X":
                        if mvalue not in self.magnet_x:
                            self.magnet_x.append(mvalue)
                    else:
                        if mvalue not in self.magnet_y:
                            self.magnet_y.append(mvalue)
                self.save_magnets()
                channel(
                    _(
                        "Created {count} magnet lines on {axis}-axis between {min_len} and {max_len}"
                    ).format(
                        count=count,
                        axis=axis,
                        min_len=Length(min_v, digits=1).length_mm,
                        max_len=Length(max_v, digits=1).length_mm,
                    )
                )
                self.context.signal("refresh_scene", "Scene")

            elif action == "set":
                done = False
                if axis == "X":
                    if not value in self.magnet_x:
                        done = True
                        self.magnet_x.append(value)
                else:
                    if not value in self.magnet_y:
                        done = True
                        self.magnet_y.append(value)
                self.save_magnets()
                self.context.signal("refresh_scene", "Scene")
                if done:
                    channel(
                        _("Magnetline appended at {pos} on axis {axis}").format(
                            pos=pos, axis=axis
                        )
                    )
                else:
                    channel(_("Magnetline was already present"))
            elif action.startswith("del"):
                done = False
                if axis == "X":
                    if value in self.magnet_x:
                        done = True
                        self.magnet_x.remove(value)
                else:
                    if value in self.magnet_y:
                        done = True
                        self.magnet_y.remove(value)
                self.save_magnets()
                self.context.signal("refresh_scene", "Scene")
                if done:
                    channel(
                        _("Magnetline removed at {pos} on axis {axis}").format(
                            pos=pos, axis=axis
                        )
                    )
                else:
                    channel(_("Magnetline was not existing"))

    def toggle_ref_obj(self):
        for e in self.scene.context.elements.flat(types=elem_nodes, emphasized=True):
            if self.reference_object == e:
                self.reference_object = None
            else:
                self.reference_object = e
            break
        self.context.signal("reference")
        self.request_refresh()

    def validate_reference(self):
        """
        Check whether the reference is still valid
        """
        found = False
        if self._reference:
            for e in self.context.elements.flat(types=elem_nodes):
                # Here we ignore the lock-status of an element
                if e is self._reference:
                    found = True
                    break
        if not found:
            self._reference = None

    @property
    def reference_object(self):
        return self._reference

    @reference_object.setter
    def reference_object(self, ref_object):
        prev = self._reference
        self._reference = ref_object
        self.scene.reference_object = self._reference
        dlist = []
        if prev is not None:
            dlist.append(prev)
        if self._reference is not None:
            dlist.append(self._reference)
        if len(dlist) > 0:
            self.context.signal("element_property_update", dlist)

    ##########
    # MAGNETS
    ##########

    @property
    def magnet_attraction(self):
        return self._magnet_attraction

    @magnet_attraction.setter
    def magnet_attraction(self, value):
        if 0 <= value <= 5:
            self._magnet_attraction = value
            self.save_magnets()

    def save_magnets(self):
        try:
            with open(self._magnet_file, "w") as f:
                f.write(f"a={self.magnet_attraction}\n")
                for x in self.magnet_x:
                    f.write(f"x={Length(x, preferred_units='mm').preferred_length}\n")
                for y in self.magnet_y:
                    f.write(f"y={Length(y, preferred_units='mm').preferred_length}\n")
        except (ValueError, PermissionError, OSError, FileNotFoundError):
            return

    def load_magnets(self):
        self.magnet_x = []
        self.magnet_y = []
        try:
            with open(self._magnet_file, "r") as f:
                for line in f:
                    cline = line.strip()
                    if cline != "":
                        subs = cline.split("=")
                        if len(subs) > 1:
                            try:
                                if subs[0] in ("a", "A"):
                                    # Attraction strength
                                    value = int(subs[1])
                                    if value < 0:
                                        value = 0
                                    if value > 5:
                                        value = 5
                                    self._magnet_attraction = value
                                elif subs[0] in ("x", "X"):
                                    dimens = Length(subs[1])
                                    value = float(dimens)
                                    if value not in self.magnet_x:
                                        self.magnet_x.append(value)
                                elif subs[0] in ("y", "Y"):
                                    dimens = Length(subs[1])
                                    value = float(dimens)
                                    if value not in self.magnet_y:
                                        self.magnet_y.append(value)
                            except ValueError:
                                pass
        except (PermissionError, OSError, FileNotFoundError):
            return

    def clear_magnets(self):
        self.magnet_x = []
        self.magnet_y = []
        self.save_magnets()

    def clear_magnets_conditionally(self):
        # Depending on setting
        if self.context.clear_magnets:
            self.clear_magnets()

    def toggle_x_magnet(self, x_value):
        if x_value in self.magnet_x:
            self.magnet_x.remove(x_value)
        else:
            self.magnet_x += [x_value]

    def toggle_y_magnet(self, y_value):
        if y_value in self.magnet_y:
            self.magnet_y.remove(y_value)
        else:
            self.magnet_y += [y_value]

    def magnet_attracted_x(self, x_value, useit):
        delta = float("inf")
        x_val = None
        if useit:
            for mag_x in self.magnet_x:
                if abs(x_value - mag_x) < delta:
                    delta = abs(x_value - mag_x)
                    x_val = mag_x
        return delta, x_val

    def magnet_attracted_y(self, y_value, useit):
        delta = float("inf")
        y_val = None
        if useit:
            for mag_y in self.magnet_y:
                if abs(y_value - mag_y) < delta:
                    delta = abs(y_value - mag_y)
                    y_val = mag_y
        return delta, y_val

    def revised_magnet_bound(self, bounds=None):
        dx = 0
        dy = 0
        if self.has_magnets() and self._magnet_attraction > 0:
            if self.grid.tick_distance > 0:
                s = f"{self.grid.tick_distance}{self.context.units_name}"
                len_tick = float(Length(s))
                # Attraction length is 1/3, 4/3, 9/3 of a grid-unit
                # fmt: off
                attraction_len = 1 / 3 * self._magnet_attraction * self._magnet_attraction * len_tick

                # print("Attraction len=%s, attract=%d, alen=%.1f, tlen=%.1f, factor=%.1f" % (s, self._magnet_attraction, attraction_len, len_tick, attraction_len / len_tick ))
                # fmt: on
            else:
                attraction_len = float(Length("1mm"))

            delta_x1, x1 = self.magnet_attracted_x(bounds[0], self.magnet_attract_x)
            delta_x2, x2 = self.magnet_attracted_x(bounds[2], self.magnet_attract_x)
            delta_x3, x3 = self.magnet_attracted_x(
                (bounds[0] + bounds[2]) / 2, self.magnet_attract_c
            )
            delta_y1, y1 = self.magnet_attracted_y(bounds[1], self.magnet_attract_y)
            delta_y2, y2 = self.magnet_attracted_y(bounds[3], self.magnet_attract_y)
            delta_y3, y3 = self.magnet_attracted_y(
                (bounds[1] + bounds[3]) / 2, self.magnet_attract_c
            )
            if delta_x3 < delta_x1 and delta_x3 < delta_x2:
                if delta_x3 < attraction_len:
                    if x3 is not None:
                        dx = x3 - (bounds[0] + bounds[2]) / 2
                        # print("X Take center , x=%.1f, dx=%.1f" % ((bounds[0] + bounds[2]) / 2, dx)
            elif delta_x1 < delta_x2 and delta_x1 < delta_x3:
                if delta_x1 < attraction_len:
                    if x1 is not None:
                        dx = x1 - bounds[0]
                        # print("X Take left side, x=%.1f, dx=%.1f" % (bounds[0], dx))
            elif delta_x2 < delta_x1 and delta_x2 < delta_x3:
                if delta_x2 < attraction_len:
                    if x2 is not None:
                        dx = x2 - bounds[2]
                        # print("X Take right side, x=%.1f, dx=%.1f" % (bounds[2], dx))
            if delta_y3 < delta_y1 and delta_y3 < delta_y2:
                if delta_y3 < attraction_len:
                    if y3 is not None:
                        dy = y3 - (bounds[1] + bounds[3]) / 2
                        # print("Y Take center , x=%.1f, dx=%.1f" % ((bounds[1] + bounds[3]) / 2, dy))
            elif delta_y1 < delta_y2 and delta_y1 < delta_y3:
                if delta_y1 < attraction_len:
                    if y1 is not None:
                        dy = y1 - bounds[1]
                        # print("Y Take top side, y=%.1f, dy=%.1f" % (bounds[1], dy))
            elif delta_y2 < delta_y1 and delta_y2 < delta_y3:
                if delta_y2 < attraction_len:
                    if y2 is not None:
                        dy = y2 - bounds[3]
                        # print("Y Take bottom side, y=%.1f, dy=%.1f" % (bounds[3], dy))

        return dx, dy

    def has_magnets(self):
        return len(self.magnet_x) + len(self.magnet_y) > 0

    ##############
    # SNAPS
    ##############

    @property
    def last_snap(self):
        result = self._last_snap_position
        # Too old? Discard
        if (time.time() - self._last_snap_ts) > 0.5:
            result = None
        return result

    @last_snap.setter
    def last_snap(self, value):
        self._last_snap_position = value
        if value is None:
            self._last_snap_ts = 0
        else:
            self._last_snap_ts = time.time()

    @signal_listener("make_reference")
    def listen_make_ref(self, origin, *args):
        node = args[0]
        self.reference_object = node
        self.context.signal("reference")

    @signal_listener("create_magnets")
    def listen_magnet_creation(self, origin, creation_list, *args):
        for info, value in creation_list:
            if info == "x":
                self.toggle_x_magnet(value)
            else:
                self.toggle_y_magnet(value)
        self.save_magnets()
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
        def zoom_in(event=None):
            self.context(f"scene zoom {1.5 / 1.0}\n")

        def zoom_out(event=None):
            self.context(f"scene zoom {1.0 / 1.5}\n")

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
                    amount=bbox[0] - x_delta,
                    relative_length=self.context.device.view.width,
                ).length_mm
                y0 = Length(
                    amount=bbox[1] - y_delta,
                    relative_length=self.context.device.view.height,
                ).length_mm
                x1 = Length(
                    amount=bbox[2] + x_delta,
                    relative_length=self.context.device.view.width,
                ).length_mm
                y1 = Length(
                    amount=bbox[3] + y_delta,
                    relative_length=self.context.device.view.height,
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
                self.grid.draw_grid_primary = not self.grid.draw_grid_primary
            elif gridtype == "secondary":
                self.grid.draw_grid_secondary = not self.grid.draw_grid_secondary
            elif gridtype == "circular":
                self.grid.draw_grid_circular = not self.grid.draw_grid_circular
            elif gridtype == "offset":
                self.grid.draw_offset_lines = not self.grid.draw_offset_lines
            self.scene.signal("guide")
            self.scene.signal("grid")
            self.widget_scene.reset_snap_attraction()
            self.request_refresh()

        def toggle_grid_p(event=None):
            toggle_grid("primary")

        def toggle_grid_s(event=None):
            toggle_grid("secondary")

        def toggle_grid_c(event=None):
            toggle_grid("circular")

        def toggle_grid_o(event=None):
            toggle_grid("offset")

        def remove_background(event=None):
            self.widget_scene._signal_widget(
                self.widget_scene.widget_root, "background", None
            )
            self.widget_scene.request_refresh()

        def recognize_background_contours(event=None):
            def image_from_bitmap(myBitmap):
                img = myBitmap.ConvertToImage()
                buf = img.GetData()
                return Image.frombuffer(
                    "RGB", tuple(myBitmap.GetSize()), bytes(buf), "raw", "RGB", 0, 1
                )
                wx_image = myBitmap.ConvertToImage()
                myPilImage = Image.new(
                    "RGB", (wx_image.GetWidth(), wx_image.GetHeight())
                )
                byte_data = bytes(wx_image.GetData())
                myPilImage.frombytes(byte_data)
                return myPilImage

            if not self.widget_scene.has_background:
                return
            # We build a dummy imageNode, so we fetch the background,
            # calculate the required transformation matrix and pass
            # it on to one of the standard image node property dialogs

            background = self.widget_scene.active_background
            if background is None:
                return
            background_image = image_from_bitmap(background)

            # Calculate scaling matrix
            sx = float(Length(self.context.device.view.width)) / background_image.width
            sy = (
                float(Length(self.context.device.view.height)) / background_image.height
            )
            matrix = Matrix(f"scale({sx},{sy})")
            # print (f"Image dimension: {background_image.width} x {background_image.height} pixel")
            # print (f"View-Size: {float(Length(self.context.device.view.width))} x {float(Length(self.context.device.view.height))}")
            # print (f"Matrix: {matrix}")

            node = ImageNode(
                image=background_image,
                matrix=matrix,
                dither=False,
                prevent_crop=True,
                dpi=500,
            )
            # print (f"Node-Dimensions: {node.bbox()}")
            # self.context.elements.elem_branch.add_node(node)

            dlg = ContourDetectionDialog(self, self.context, node)
            dlg.ShowModal()
            dlg.end_dialog()
            dlg.Destroy()

        def stop_auto_update(event=None):
            devlabel = self.context.device.label
            to_stop = []
            for job, content in self.context.kernel.jobs.items():
                if job is not None and job.startswith("timer.updatebg"):
                    cmd = str(content).strip()
                    if cmd.endswith("background") or cmd.endswith(devlabel):
                        to_stop.append(job)
            for job in to_stop:
                self.context(f"{job} --off\n")

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
        menu.Check(id2.GetId(), self.grid.draw_grid_primary)
        id3 = menu.Append(
            wx.ID_ANY,
            _("Show Secondary Grid"),
            _("Display the secondary grid in the scene"),
            wx.ITEM_CHECK,
        )
        self.Bind(wx.EVT_MENU, toggle_grid_s, id=id3.GetId())
        menu.Check(id3.GetId(), self.grid.draw_grid_secondary)
        id4 = menu.Append(
            wx.ID_ANY,
            _("Show Circular Grid"),
            _("Display the circular grid in the scene"),
            wx.ITEM_CHECK,
        )
        self.Bind(wx.EVT_MENU, toggle_grid_c, id=id4.GetId())
        menu.Check(id4.GetId(), self.grid.draw_grid_circular)
        try:
            mx = float(Length(self.context.device.view.margin_x))
            my = float(Length(self.context.device.view.margin_y))
        except ValueError:
            mx = 0
            my = 0
        # print(self.context.device.view.margin_x, self.context.device.view.margin_y)
        if mx != 0.0 or my != 0.0:
            menu.AppendSeparator()
            id4b = menu.Append(
                wx.ID_ANY,
                _("Show physical dimensions"),
                _("Display the physical dimensions"),
                wx.ITEM_CHECK,
            )
            self.Bind(wx.EVT_MENU, toggle_grid_o, id=id4b.GetId())
            menu.Check(id4b.GetId(), self.grid.draw_offset_lines)

        if self.widget_scene.has_background:
            menu.AppendSeparator()
            id5 = menu.Append(wx.ID_ANY, _("Remove Background"), "")
            self.Bind(wx.EVT_MENU, remove_background, id=id5.GetId())

            id6 = menu.Append(wx.ID_ANY, _("Detect contours on background"), "")
            self.Bind(wx.EVT_MENU, recognize_background_contours, id=id6.GetId())
        # Do we have a timer called .updatebg?
        devlabel = self.context.device.label
        we_have_a_job = False
        for job, content in self.context.kernel.jobs.items():
            if job is not None and job.startswith("timer.updatebg"):
                cmd = str(content).strip()
                if cmd.endswith("background") or cmd.endswith(devlabel):
                    we_have_a_job = True
                    break

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
            lambda e: zoom_out(),
            menu.Append(
                wx.ID_ANY,
                _("Zoom Out"),
                _("Make the scene smaller"),
            ),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: zoom_in(),
            menu.Append(
                wx.ID_ANY,
                _("Zoom In"),
                _("Make the scene larger"),
            ),
        )
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

    @signal_listener("coolant_changed")
    def on_coolant_changed(self, origin, *args):
        if hasattr(self.context.device, "coolant"):
            coolid = self.context.device.device_coolant
            if coolid == "":
                coolid = None
            cool = self.context.kernel.root.coolant
            cool.claim_coolant(self.context.device, coolid)

    @signal_listener("view;realized")
    def on_bedsize_simple(self, origin=None, nocmd=None, *args):
        self.scene.signal("guide")
        self.scene.signal("grid")
        self.request_refresh(origin)

    @signal_listener("magnet-attraction")
    def on_magnet_attract(self, origin, strength, *args):
        strength = int(strength)
        if strength < 0:
            strength = 0
        self.magnet_attraction = strength

    @signal_listener("magnet_gen")
    def on_magnet_generate(self, origin, *args):
        candidate = args[0]
        if candidate is None:
            return
        if not isinstance(candidate, (tuple, list)) or len(candidate) < 2:
            return
        method = candidate[0]
        node = candidate[1]
        bb = node.bounds
        if method == "outer":
            self.toggle_x_magnet(bb[0])
            self.toggle_x_magnet(bb[2])
            self.toggle_y_magnet(bb[1])
            self.toggle_y_magnet(bb[3])
        elif method == "center":
            self.toggle_x_magnet((bb[0] + bb[2]) / 2)
            self.toggle_y_magnet((bb[1] + bb[3]) / 2)
        self.save_magnets()
        self.request_refresh()

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
        # Refresh not needed as scenepanel already does it...
        # self.scene.signal("guide")
        # self.request_refresh()

    def on_close(self, event):
        self.save_magnets()

    @signal_listener("pause")
    @signal_listener("pipe;running")
    def on_driver_mode(self, origin, *args):
        # pipe running has (state) as args
        new_color = None
        try:
            if self.context.device.driver.paused:
                new_color = self.context.themes.get("pause_bg")
            elif self.context.device.laser_status == "active":
                new_color = self.context.themes.get("stop_bg")
        except AttributeError:
            pass
        self.widget_scene.overrule_background = new_color
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

    @signal_listener("modified_by_tool")
    def on_modification_by_tool(self, origin, *args):
        self.context.elements.process_keyhole_updates(self.context)
        self.scene.signal("modified_by_tool")

    @signal_listener("tabs_updated")
    def on_tabs_update(self, origin, *args):
        # Pass on to scene widgets
        self.scene.signal("tabs_updated")

    @signal_listener("emphasized")
    def on_emphasized_elements_changed(self, origin, *args):
        self.scene.context.elements.set_start_time("Emphasis wxmscene")
        self.scene.signal("emphasized")
        self.laserpath_widget.clear_laserpath()
        self.request_refresh(origin)
        self.scene.context.elements.set_end_time("Emphasis wxmscene")

    def request_refresh(self, *args):
        self.widget_scene.request_refresh(*args)

    @signal_listener("altered")
    @signal_listener("modified")
    def on_element_modified(self, *args):
        self.scene.signal("modified")
        self.widget_scene.request_refresh(*args)

    @signal_listener("linetext")
    def on_signal_linetext(self, origin, *args):
        if len(args) == 1:
            self.scene.signal("linetext", args[0])
        elif len(args) > 1:
            self.scene.signal("linetext", args[0], args[1])

    @signal_listener("nodeedit")
    def on_signal_nodeedit(self, origin, *args):
        if len(args) == 1:
            self.scene.signal("nodeedit", args[0])
        elif len(args) > 1:
            self.scene.signal("nodeedit", args[0], args[1])

    @signal_listener("element_added")
    @signal_listener("tree_changed")
    def on_elements_added(self, origin, nodes=None, *args):
        self.scene.signal("element_added", nodes)
        # There may be a smarter way to eliminate unnecessary rebuilds, but it's doing the job...
        # self.context.signal("rebuild_tree")
        self.context.signal("refresh_tree", nodes)
        self.widget_scene.request_refresh()

    @signal_listener("rebuild_tree")
    def on_rebuild_tree(self, origin, *args):
        self.widget_scene._signal_widget(
            self.widget_scene.widget_root, "rebuild_tree", None
        )

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

    @signal_listener("scene_deactivated")
    def on_scene_deactived(self, origin, *args):
        if not self.context.setting(bool, "auto_tool_reset", True):
            return
        if self.active_tool != "none":
            self.context(".tool none\n")

    def on_key_down(self, event):
        keyvalue = get_key_name(event)
        ignore = self.tool_active
        if self._keybind_channel:
            self._keybind_channel(f"Scene key_down: {keyvalue}.")
        if not ignore and self.context.bind.trigger(keyvalue):
            if self._keybind_channel:
                self._keybind_channel(f"Scene key_down: {keyvalue} executed.")
        else:
            if self._keybind_channel:
                if ignore:
                    self._keybind_channel(
                        f"Scene key_down: {keyvalue} was ignored as tool active."
                    )
                else:
                    self._keybind_channel(f"Scene key_down: {keyvalue} unfound.")
        event.Skip()

    def on_key_up(self, event, log=True):
        keyvalue = get_key_name(event)
        ignore = self.tool_active
        if self._keybind_channel:
            self._keybind_channel(f"Scene key_up: {keyvalue}.")
        if not ignore and self.context.bind.untrigger(keyvalue):
            if self._keybind_channel:
                self._keybind_channel(f"Scene key_up: {keyvalue} executed.")
        else:
            if self._keybind_channel:
                if ignore:
                    self._keybind_channel(
                        f"Scene key_up: {keyvalue} was ignored as tool active."
                    )
                else:
                    self._keybind_channel(f"Scene key_up: {keyvalue} unfound.")
        event.Skip()


class SceneWindow(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(1280, 800, *args, **kwds)
        self.panel = MeerK40tScenePanel(self, wx.ID_ANY, context=self.context)
        self.sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_meerk40t.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Scene"))
        self.Layout()
        self.restore_aspect()

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()
