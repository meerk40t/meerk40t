import os
import platform
import sys
from functools import partial

import wx
from PIL import Image
from wx import aui

from meerk40t.core.exceptions import BadFileError
from meerk40t.gui.statusbarwidgets.infowidget import (
    BurnProgressPanel,
    InformationWidget,
    StatusPanelWidget,
)
from meerk40t.gui.statusbarwidgets.opassignwidget import (
    OperationAssignOptionWidget,
    OperationAssignWidget,
)
from meerk40t.gui.statusbarwidgets.selectionwidget import SelectionWidget
from meerk40t.gui.statusbarwidgets.shapepropwidget import (
    FillruleWidget,
    LinecapWidget,
    LinejoinWidget,
)
from meerk40t.gui.statusbarwidgets.statusbar import CustomStatusBar
from meerk40t.gui.statusbarwidgets.strokewidget import ColorWidget, StrokeWidget
from meerk40t.kernel import lookup_listener, signal_listener

from ..core.units import UNITS_PER_INCH, Length
from ..svgelements import Color, Matrix, Path
from .icons import (
    STD_ICON_SIZE,
    icon_cag_common_50,
    icon_cag_subtract_50,
    icon_cag_union_50,
    icon_cag_xor_50,
    icon_meerk40t,
    icons8_align_bottom_50,
    icons8_align_left_50,
    icons8_align_right_50,
    icons8_align_top_50,
    icons8_circle_50,
    icons8_cursor_50,
    icons8_flip_vertical,
    icons8_group_objects_50,
    icons8_measure_50,
    icons8_mirror_horizontal,
    icons8_opened_folder_50,
    icons8_oval_50,
    icons8_pencil_drawing_50,
    icons8_place_marker_50,
    icons8_point_50,
    icons8_polygon_50,
    icons8_polyline_50,
    icons8_rectangular_50,
    icons8_rotate_left_50,
    icons8_rotate_right_50,
    icons8_save_50,
    icons8_type_50,
    icons8_ungroup_objects_50,
    icons8_vector_50,
    icons_centerize,
    icons_evenspace_horiz,
    icons_evenspace_vert,
    set_icon_appearance,
)
from .laserrender import (
    DRAW_MODE_ALPHABLACK,
    DRAW_MODE_ANIMATE,
    DRAW_MODE_BACKGROUND,
    DRAW_MODE_CACHE,
    DRAW_MODE_FILLS,
    DRAW_MODE_FLIPXY,
    DRAW_MODE_GRID,
    DRAW_MODE_GUIDES,
    DRAW_MODE_ICONS,
    DRAW_MODE_IMAGE,
    DRAW_MODE_INVERT,
    DRAW_MODE_LASERPATH,
    DRAW_MODE_LINEWIDTH,
    DRAW_MODE_PATH,
    DRAW_MODE_REFRESH,
    DRAW_MODE_REGMARKS,
    DRAW_MODE_RETICLE,
    DRAW_MODE_SELECTION,
    DRAW_MODE_STROKES,
    DRAW_MODE_TEXT,
    DRAW_MODE_VARIABLES,
    swizzlecolor,
)
from .mwindow import MWindow

_ = wx.GetTranslation


class MeerK40t(MWindow):
    """MeerK40t main window"""

    def __init__(self, *args, **kwds):
        width, height = wx.DisplaySize()

        super().__init__(int(width * 0.9), int(height * 0.9), *args, **kwds)
        try:
            self.EnableTouchEvents(wx.TOUCH_ZOOM_GESTURE | wx.TOUCH_PAN_GESTURES)
        except AttributeError:
            # Not WX 4.1
            pass

        self.context.gui = self
        self.usb_running = False
        context = self.context
        self.register_options_and_choices(context)

        if self.context.disable_tool_tips:
            wx.ToolTip.Enable(False)

        self.root_context = context.root
        self.DragAcceptFiles(True)

        self.needs_saving = False
        self.working_file = None

        self.pipe_state = None
        self.previous_position = None
        self.is_paused = False

        self._mgr = aui.AuiManager()
        self._mgr.SetFlags(self._mgr.GetFlags() | aui.AUI_MGR_LIVE_RESIZE)
        self._mgr.Bind(aui.EVT_AUI_PANE_CLOSE, self.on_pane_closed)
        self._mgr.Bind(aui.EVT_AUI_PANE_ACTIVATED, self.on_pane_active)

        self.ui_visible = True
        self.hidden_panes = []

        # notify AUI which frame to use
        self._mgr.SetManagedWindow(self)

        self.__set_panes()
        self.__set_commands()

        # Menu Bar
        self.main_menubar = wx.MenuBar()
        self.__set_menubars()
        # Status Bar
        self.startup = True
        self.main_statusbar = CustomStatusBar(self, 4)
        self.widgets_created = False
        self.setup_statusbar_panels()
        self.SetStatusBar(self.main_statusbar)
        self.main_statusbar.SetStatusStyles(
            [wx.SB_SUNKEN] * self.main_statusbar.GetFieldsCount()
        )
        # Set the panel sizes
        sizes = [-3] * self.main_statusbar.GetFieldsCount()
        # Make the first Panel large
        sizes[0] = -4
        # And the last one smaller
        sizes[self.main_statusbar.GetFieldsCount() - 1] = -2
        self.SetStatusWidths(sizes)

        # self.main_statusbar.SetStatusWidths([-1] * self.main_statusbar.GetFieldsCount())
        self.SetStatusBarPane(0)
        self.main_statusbar.SetStatusText("", 0)
        self.startup = False
        # Make sure its showing up properly
        self.main_statusbar.Reposition()

        self.Bind(wx.EVT_MENU_OPEN, self.on_menu_open)
        self.Bind(wx.EVT_MENU_CLOSE, self.on_menu_close)
        self.Bind(wx.EVT_MENU_HIGHLIGHT, self.on_menu_highlight)
        self.DoGiveHelp_called = False
        self.menus_open = 0
        self.top_menu = None  # Needed because event.GetMenu is None for submenu titles

        self.Bind(wx.EVT_DROP_FILES, self.on_drop_file)

        self.__set_properties()
        self.Layout()

        self.__set_titlebar()
        self.__kernel_initialize()

        self.Bind(wx.EVT_SIZE, self.on_size)

        self.CenterOnScreen()

    def setup_statusbar_panels(self):
        if not self.context.show_colorbar:
            return
        self.widgets_created = True
        self.idx_selection = self.main_statusbar.panelct - 1
        self.idx_colors = self.main_statusbar.panelct - 2
        self.idx_assign = self.main_statusbar.panelct - 3

        self.status_panel = StatusPanelWidget(self.main_statusbar.panelct)
        self.main_statusbar.add_panel_widget(self.status_panel, 0, "status", True)

        self.select_panel = SelectionWidget()
        self.info_panel = InformationWidget()
        self.main_statusbar.add_panel_widget(
            self.select_panel, self.idx_selection, "selection", False
        )
        self.main_statusbar.add_panel_widget(
            self.info_panel, self.idx_selection, "infos", False
        )

        self.assign_button_panel = OperationAssignWidget()
        self.assign_option_panel = OperationAssignOptionWidget()
        self.main_statusbar.add_panel_widget(
            self.assign_button_panel, self.idx_assign, "assign", True
        )
        self.main_statusbar.add_panel_widget(
            self.assign_option_panel, self.idx_assign, "assign-options", True
        )

        self.color_panel = ColorWidget()
        self.stroke_panel = StrokeWidget()
        self.linecap_panel = LinecapWidget()
        self.linejoin_panel = LinejoinWidget()
        self.fillrule_panel = FillruleWidget()
        self.main_statusbar.add_panel_widget(
            self.color_panel, self.idx_colors, "color", False
        )
        self.main_statusbar.add_panel_widget(
            self.stroke_panel, self.idx_colors, "stroke", False
        )
        self.main_statusbar.add_panel_widget(
            self.linecap_panel, self.idx_colors, "linecap", False
        )
        self.main_statusbar.add_panel_widget(
            self.linejoin_panel, self.idx_colors, "linejoin", False
        )
        self.main_statusbar.add_panel_widget(
            self.fillrule_panel, self.idx_colors, "fillrule", False
        )
        self.burn_panel = BurnProgressPanel()
        self.main_statusbar.add_panel_widget(
            self.burn_panel, self.idx_selection, "burninfo", False
        )

        self.assign_button_panel.show_stuff(False)

    def destroy_statusbar_panels(self):
        self.main_statusbar.Clear()
        self.widgets_created = False

    # --- Listen to external events to toggle regmark visibility
    @signal_listener("toggle_regmarks")
    def on_regmark_toggle(self, origin, *args):
        bits = DRAW_MODE_REGMARKS
        self.context.draw_mode ^= bits
        self.context.signal("draw_mode", self.context.draw_mode)
        self.context.signal("refresh_scene", "Scene")

    # --- Listen to external events to update the bar
    @signal_listener("show_colorbar")
    def on_colobar_signal(self, origin, *args):
        if len(args) > 0:
            showem = args[0]
        else:
            showem = True
        if showem:
            if not self.widgets_created:
                self.setup_statusbar_panels()
        else:
            if self.widgets_created:
                self.destroy_statusbar_panels()

    @signal_listener("element_property_reload")
    @signal_listener("element_property_update")
    def on_element_update(self, origin, *args):
        if self.widgets_created:
            self.main_statusbar.Signal("element_property_update", *args)

    @signal_listener("rebuild_tree")
    @signal_listener("refresh_tree")
    @signal_listener("tree_changed")
    @signal_listener("operation_removed")
    @signal_listener("add_operation")
    def on_rebuild(self, origin, *args):
        if self.widgets_created:
            self.main_statusbar.Signal("rebuild_tree")

    # --------- Events for status bar

    @signal_listener("emphasized")
    def on_update_statusbar(self, origin, *args):
        if not self.context.show_colorbar or not self.widgets_created:
            return
        value = self.context.elements.has_emphasis()
        self.main_statusbar.Signal("emphasized")
        # First enable/disable the controls in the statusbar

        self.assign_button_panel.show_stuff(value)
        self.main_statusbar.activate_panel("selection", value)
        self.main_statusbar.activate_panel("infos", value)
        self.main_statusbar.activate_panel("color", value)
        self.main_statusbar.activate_panel("stroke", value)
        self.main_statusbar.activate_panel("fillrule", value)
        self.main_statusbar.activate_panel("linejoin", value)
        self.main_statusbar.activate_panel("linecap", value)
        self.main_statusbar.Reposition()

    # ------------ Setup
    def register_options_and_choices(self, context):
        _ = context._
        context.setting(bool, "disable_tool_tips", False)
        context.setting(bool, "disable_auto_zoom", False)
        context.setting(bool, "enable_sel_move", True)
        context.setting(bool, "enable_sel_size", True)
        context.setting(bool, "enable_sel_rotate", True)
        context.setting(bool, "enable_sel_skew", False)
        context.setting(int, "zoom_level", 4)  # 4%
        # Standard-Icon-Sizes
        # default, factor 1 - leave as is
        # small = factor 2/3, min_size = 32
        # tiny  = factor 1/2, min_size = 25
        context.setting(str, "icon_size", "default")
        # Ribbon-Size (NOT YET ACTIVE)
        # default - std icon size + panel-labels,
        # small - std icon size / no labels
        # tiny - reduced icon size / no labels
        context.setting(str, "ribbon_appearance", "default")
        choices = [
            {
                "attr": "ribbon_appearance",
                "object": self.context.root,
                "default": "default",
                "type": str,
                "style": "combosmall",
                "choices": ["default", "small", "tiny"],
                "label": _("Ribbon-Size:"),
                "tip": _(
                    "Appearance of ribbon at the top (requires a restart to take effect))"
                ),
                "page": "Gui",
                "section": "Appearance",
            },
        ]
        # context.kernel.register_choices("preferences", choices)
        choices = [
            {
                "attr": "icon_size",
                "object": self.context.root,
                "default": "default",
                "type": str,
                "style": "combosmall",
                "choices": ["large", "big", "default", "small", "tiny"],
                "label": _("Icon size:"),
                "tip": _(
                    "Appearance of all icons in the GUI (requires a restart to take effect))"
                ),
                "page": "Gui",
                "section": "Appearance",
            },
        ]
        context.kernel.register_choices("preferences", choices)

        choices = [
            {
                "attr": "zoom_level",
                "object": self.context.root,
                "default": 4,
                "trailer": "%",
                "type": int,
                "style": "combosmall",
                "choices": [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    9,
                    10,
                    15,
                    20,
                    25,
                ],
                "label": _("Default zoom level:"),
                "tip": _(
                    "Default zoom level when changing zoom (automatically or via Ctrl-B)"
                ),
                "page": "Gui",
                "section": "Zoom",
            },
        ]
        context.kernel.register_choices("preferences", choices)
        choices = [
            {
                "attr": "disable_auto_zoom",
                "object": self.context.root,
                "default": False,
                "type": bool,
                "label": _("Don't autoadjust zoom level"),
                "tip": _("Don't autoadjust zoom level when resizing the main window"),
                "page": "Gui",
                "section": "Zoom",
            },
        ]
        context.kernel.register_choices("preferences", choices)

        choices = [
            {
                "attr": "select_smallest",
                "object": context.root,
                "default": True,
                "type": bool,
                "label": _("Select smallest element on scene"),
                "tip": _(
                    "Active: Single click selects the smallest element under cursor (ctrl+click selects the largest) / Inactive: Single click selects the largest element  (ctrl+click the smallest)."
                ),
                "page": "Scene",
                "section": "General",
            },
        ]
        context.kernel.register_choices("preferences", choices)

        choices = [
            {
                "attr": "show_colorbar",
                "object": self.context.root,
                "default": True,
                "type": bool,
                "label": _("Display colorbar in statusbar"),
                "tip": _(
                    "Enable the display of a colorbar at the bottom of the screen."
                ),
                "page": "Gui",
                "section": "General",
            },
        ]
        context.kernel.register_choices("preferences", choices)

        choices = [
            {
                "attr": "outer_handles",
                "object": context.root,
                "default": False,
                "type": bool,
                "label": _("Draw selection handle outside of bounding box"),
                "tip": _(
                    "Active: draw handles outside of / Inactive: Draw them on the bounding box of the selection."
                ),
                "page": "Scene",
                "section": "General",
            },
        ]
        context.kernel.register_choices("preferences", choices)

        choices = [
            {
                "attr": "show_attract_len",
                "object": context.root,
                "default": 45,
                "type": int,
                "style": "slider",
                "min": 1,
                "max": 75,
                "label": _("Distance"),
                "tip": _(
                    "Defines until which distance snap points will be highlighted"
                ),
                "page": "Scene",
                "section": "Snap-Options",
            },
            {
                "attr": "snap_points",
                "object": context.root,
                "default": True,
                "type": bool,
                "label": _("Snap to element"),
                "tip": _("Shall the cursor snap to the next element point?"),
                "page": "Scene",
                "section": "Snap-Options",
            },
            {
                "attr": "action_attract_len",
                "object": context.root,
                "conditional": (context.root, "snap_points"),
                "default": 20,
                "type": int,
                "style": "slider",
                "min": 1,
                "max": 75,
                "label": _("Distance"),
                "tip": _(
                    "Set the distance inside which the cursor will snap to the next element point"
                ),
                "page": "Scene",
                "section": "Snap-Options",
            },
            {
                "attr": "snap_grid",
                "object": context.root,
                "default": True,
                "type": bool,
                "label": _("Snap to Grid"),
                "tip": _("Shall the cursor snap to the next grid intersection?"),
                "page": "Scene",
                "section": "Snap-Options",
            },
            {
                "attr": "grid_attract_len",
                "object": context.root,
                "default": 15,
                "conditional": (context.root, "snap_grid"),
                "type": int,
                "style": "slider",
                "min": 1,
                "max": 75,
                "label": _("Distance"),
                "tip": _(
                    "Set the distance inside which the cursor will snap to the next grid intersection"
                ),
                "page": "Scene",
                "section": "Snap-Options",
            },
        ]
        context.kernel.register_choices("preferences", choices)
        choices = [
            {
                "attr": "use_toolmenu",
                "object": context.root,
                "default": True,
                "type": bool,
                "label": _("Use in-scene tool-menu"),
                "tip": _(
                    "The scene-menu will appear if you right-click on the scene-background"
                ),
                "page": "Gui",
                "section": "Scene",
            },
        ]
        context.kernel.register_choices("preferences", choices)

        context.register(
            "function/open_property_window_for_node", self.open_property_window_for_node
        )
        if context.icon_size == "tiny":
            set_icon_appearance(0.5, int(0.5 * STD_ICON_SIZE))
        elif context.icon_size == "small":
            set_icon_appearance(2 / 3, int(2 / 3 * STD_ICON_SIZE))
        elif context.icon_size == "big":
            set_icon_appearance(1.5, 0)
        elif context.icon_size == "large":
            set_icon_appearance(2.0, 0)
        else:
            set_icon_appearance(1.0, 0)

    def open_property_window_for_node(self, node):
        """
        Activate the node in question.

        @param node:
        @return:
        """
        gui = self
        root = self.context.root
        root.open("window/Properties", gui)

    @staticmethod
    def sub_register(kernel):
        buttonsize = STD_ICON_SIZE
        kernel.register(
            "button/project/Open",
            {
                "label": _("Open"),
                "icon": icons8_opened_folder_50,
                "tip": _("Opens new project"),
                "action": lambda e: kernel.console(".dialog_load\n"),
                "priority": -200,
                "size": buttonsize,
            },
        )
        kernel.register(
            "button/project/Save",
            {
                "label": _("Save"),
                "icon": icons8_save_50,
                "tip": _("Saves a project to disk"),
                "action": lambda e: kernel.console(".dialog_save\n"),
                "priority": -100,
                "size": buttonsize,
            },
        )

        # Default Size for tool buttons - none: use icon size
        buttonsize = STD_ICON_SIZE

        kernel.register(
            "button/tools/Scene",
            {
                "label": _("Select"),
                "icon": icons8_cursor_50,
                "tip": _("Regular selection tool"),
                "action": lambda v: kernel.elements("tool none\n"),
                "group": "tool",
                "size": buttonsize,
                "identifier": "none",
            },
        )

        kernel.register(
            "button/tools/Relocate",
            {
                "label": _("Set Position"),
                "icon": icons8_place_marker_50,
                "tip": _("Set position to given location"),
                "action": lambda v: kernel.elements("tool relocate\n"),
                "group": "tool",
                "size": buttonsize,
                "identifier": "relocate",
            },
        )

        kernel.register(
            "button/tools/Draw",
            {
                "label": _("Draw"),
                "icon": icons8_pencil_drawing_50,
                "tip": _("Add a free-drawing element"),
                "action": lambda v: kernel.elements("tool draw\n"),
                "group": "tool",
                "size": buttonsize,
                "identifier": "draw",
            },
        )

        kernel.register(
            "button/tools/ellipse",
            {
                "label": _("Ellipse"),
                "icon": icons8_oval_50,
                "tip": _("Add an ellipse element"),
                "action": lambda v: kernel.elements("tool ellipse\n"),
                "group": "tool",
                "size": buttonsize,
                "identifier": "ellipse",
            },
        )

        kernel.register(
            "button/tools/circle",
            {
                "label": _("Circle"),
                "icon": icons8_circle_50,
                "tip": _("Add a circle element"),
                "action": lambda v: kernel.elements("tool circle\n"),
                "group": "tool",
                "size": buttonsize,
                "identifier": "circle",
            },
        )

        kernel.register(
            "button/tools/Polygon",
            {
                "label": _("Polygon"),
                "icon": icons8_polygon_50,
                "tip": _(
                    "Add a polygon element\nLeft click: point/line\nDouble click: complete\nRight click: cancel"
                ),
                "action": lambda v: kernel.elements("tool polygon\n"),
                "group": "tool",
                "size": buttonsize,
                "identifier": "polygon",
            },
        )

        kernel.register(
            "button/tools/Polyline",
            {
                "label": _("Polyline"),
                "icon": icons8_polyline_50,
                "tip": _(
                    "Add a polyline element\nLeft click: point/line\nDouble click: complete\nRight click: cancel"
                ),
                "action": lambda v: kernel.elements("tool polyline\n"),
                "group": "tool",
                "size": buttonsize,
                "identifier": "polyline",
            },
        )

        kernel.register(
            "button/tools/Rectangle",
            {
                "label": _("Rectangle"),
                "icon": icons8_rectangular_50,
                "tip": _("Add a rectangular element"),
                "action": lambda v: kernel.elements("tool rect\n"),
                "group": "tool",
                "size": buttonsize,
                "identifier": "rect",
            },
        )

        kernel.register(
            "button/tools/Point",
            {
                "label": _("Point"),
                "icon": icons8_point_50,
                "tip": _("Add point to the scene"),
                "action": lambda v: kernel.elements("tool point\n"),
                "group": "tool",
                "size": buttonsize,
                "identifier": "point",
            },
        )

        kernel.register(
            "button/tools/Vector",
            {
                "label": _("Vector"),
                "icon": icons8_vector_50,
                "tip": _(
                    "Add a shape\nLeft click: point/line\nClick and hold: curve\nDouble click: complete\nRight click: cancel"
                ),
                "action": lambda v: kernel.elements("tool vector\n"),
                "group": "tool",
                "size": buttonsize,
                "identifier": "vector",
            },
        )

        kernel.register(
            "button/tools/Text",
            {
                "label": _("Text"),
                "icon": icons8_type_50,
                "tip": _("Add a text element"),
                "action": lambda v: kernel.elements("tool text\n"),
                "group": "tool",
                "size": buttonsize,
                "identifier": "text",
            },
        )

        kernel.register(
            "button/tools/Measure",
            {
                "label": _("Measure"),
                "icon": icons8_measure_50,
                "tip": _(
                    "Measure distance / perimeter / area\nLeft click: point/line\nDouble click: complete\nRight click: cancel"
                ),
                "action": lambda v: kernel.elements("tool measure\n"),
                "group": "tool",
                "size": buttonsize,
                "identifier": "measure",
            },
        )
        # Default Size for smaller buttons
        buttonsize = STD_ICON_SIZE / 2

        kernel.register(
            "button/modify/Flip",
            {
                "label": _("Flip Vertical"),
                "icon": icons8_flip_vertical,
                "tip": _("Flip the selected element vertically"),
                "action": lambda v: kernel.elements("scale 1 -1\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/modify/Mirror",
            {
                "label": _("Mirror Horizontal"),
                "icon": icons8_mirror_horizontal,
                "tip": _("Mirror the selected element horizontally"),
                "action": lambda v: kernel.elements("scale -1 1\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/modify/Rotate90CW",
            {
                "label": _("Rotate CW"),
                "icon": icons8_rotate_right_50,
                "tip": _("Rotate the selected element clockwise by 90 deg"),
                "action": lambda v: kernel.elements("rotate 90deg\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/modify/Rotate90CCW",
            {
                "label": _("Rotate CCW"),
                "icon": icons8_rotate_left_50,
                "tip": _("Rotate the selected element counterclockwise by 90 deg"),
                "action": lambda v: kernel.elements("rotate -90deg\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/geometry/Union",
            {
                "label": _("Union"),
                "icon": icon_cag_union_50,
                "tip": _("Create a union of the selected elements"),
                "action": lambda v: kernel.elements("element union\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 1,
            },
        )
        kernel.register(
            "button/geometry/Difference",
            {
                "label": _("Difference"),
                "icon": icon_cag_subtract_50,
                "tip": _("Create a difference of the selected elements"),
                "action": lambda v: kernel.elements("element difference\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 1,
            },
        )
        kernel.register(
            "button/geometry/Xor",
            {
                "label": _("Xor"),
                "icon": icon_cag_xor_50,
                "tip": _("Create a xor of the selected elements"),
                "action": lambda v: kernel.elements("element xor\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 1,
            },
        )
        kernel.register(
            "button/geometry/Intersection",
            {
                "label": _("Intersection"),
                "icon": icon_cag_common_50,
                "tip": _("Create a intersection of the selected elements"),
                "action": lambda v: kernel.elements("element intersection\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 1,
            },
        )

        def group_selection():
            group_node = None
            lets_do_it = False
            data = list(kernel.elements.elems(emphasized=True))
            sel_count = len(data)
            my_parent = None
            for node in data:
                this_parent = None
                if hasattr(node, "parent"):
                    if hasattr(node.parent, "type"):
                        if node.parent.type in ("group", "file"):
                            this_parent = node.parent
                if my_parent is None:
                    if this_parent is not None:
                        my_parent = this_parent
                else:
                    if my_parent != this_parent:
                        # different parents, so definitely a do it
                        lets_do_it = True
                        break
            if not lets_do_it:
                if my_parent is None:
                    # All base elements
                    lets_do_it = True
                else:
                    parent_ct = len(my_parent.children)
                    if parent_ct != sel_count:
                        # Not the full group...
                        lets_do_it = True

            if lets_do_it:
                for node in data:
                    if group_node is None:
                        group_node = node.parent.add(type="group", label="Group")
                    group_node.append_child(node)
                kernel.signal("element_property_reload", "Scene", group_node)

        kernel.register(
            "button/geometry/Group",
            {
                "label": _("Group"),
                "icon": icons8_group_objects_50,
                "tip": _("Group elements together"),
                "action": lambda v: group_selection(),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 1,
            },
        )

        def ungroup_selection():
            def release_em(node):
                for n in list(node.children):
                    node.insert_sibling(n)
                node.remove_node()  # Removing group/file node.

            found_some = False
            for node in list(kernel.elements.elems(emphasized=True)):
                if node is not None:
                    if node.type in ("group", "file"):
                        found_some = True
                        release_em(node)
            if not found_some:
                # So let's see that we address the parents...
                for node in list(kernel.elements.elems(emphasized=True)):
                    if node is not None:
                        if hasattr(node, "parent"):
                            if hasattr(node.parent, "type"):
                                if node.parent.type in ("group", "file"):
                                    release_em(node.parent)

        def part_of_group():
            result = False
            for node in list(kernel.elements.elems(emphasized=True)):
                if hasattr(node, "parent"):
                    if node.parent.type in ("group", "file"):
                        result = True
                        break
            return result

        kernel.register(
            "button/geometry/Ungroup",
            {
                "label": _("Ungroup"),
                "icon": icons8_ungroup_objects_50,
                "tip": _("Ungroup elements"),
                "action": lambda v: ungroup_selection(),
                "size": buttonsize,
                "rule_enabled": lambda cond: part_of_group(),
            },
        )
        kernel.register(
            "button/align/AlignLeft",
            {
                "label": _("Align Left"),
                "icon": icons8_align_left_50,
                "tip": _(
                    "Align selected elements at the leftmost position (right click: of the bed)"
                ),
                "action": lambda v: kernel.elements("align left\n"),
                "right": lambda v: kernel.elements("align bedleft\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/align/AlignRight",
            {
                "label": _("Align Right"),
                "icon": icons8_align_right_50,
                "tip": _(
                    "Align selected elements at the rightmost position (right click: of the bed)"
                ),
                "action": lambda v: kernel.elements("align right\n"),
                "right": lambda v: kernel.elements("align bedright\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/align/AlignTop",
            {
                "label": _("Align Top"),
                "icon": icons8_align_top_50,
                "tip": _(
                    "Align selected elements at the topmost position (right click: of the bed)"
                ),
                "action": lambda v: kernel.elements("align top\n"),
                "right": lambda v: kernel.elements("align bedtop\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/align/AlignBottom",
            {
                "label": _("Align Bottom"),
                "icon": icons8_align_bottom_50,
                "tip": _(
                    "Align selected elements at the lowest position (right click: of the bed)"
                ),
                "action": lambda v: kernel.elements("align bottom\n"),
                "right": lambda v: kernel.elements("align bedbottom\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/align/AlignCenter",
            {
                "label": _("Align Center"),
                "icon": icons_centerize,
                "tip": _(
                    "Align selected elements at their center (right click: of the bed)"
                ),
                "action": lambda v: kernel.elements("align center\n"),
                "right": lambda v: kernel.elements("align bedcenter\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/align/AlignHorizontally",
            {
                "label": _("Distr. Hor."),
                "icon": icons_evenspace_horiz,
                "tip": _("Distribute Space Horizontally"),
                "action": lambda v: kernel.elements("align spaceh\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 2,
            },
        )
        kernel.register(
            "button/align/AlignVertically",
            {
                "label": _("Distr. Vert."),
                "icon": icons_evenspace_vert,
                "tip": _("Distribute Space Vertically"),
                "action": lambda v: kernel.elements("align spacev\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 2,
            },
        )

    def window_menu(self):
        return False

    def __set_commands(self):
        context = self.context
        gui = self

        @context.console_command("dialog_transform", hidden=True)
        def transform(**kwargs):
            dlg = wx.TextEntryDialog(
                gui,
                _(
                    "Enter SVG Transform Instruction e.g. 'scale(1.49, 1, $x, $y)', rotate, translate, etc..."
                ),
                _("Transform Entry"),
                "",
            )
            dlg.SetValue("")

            if dlg.ShowModal() == wx.ID_OK:
                elements = context.elements

                m = str(dlg.GetValue())
                x, y = self.context.device.current
                m = m.replace("$x", str(x))
                m = m.replace("$y", str(y))
                matrix = Matrix(m)
                unit_width = context.device.unit_width
                unit_height = context.device.unit_height
                matrix.render(ppi=UNITS_PER_INCH, width=unit_width, height=unit_height)
                if matrix.is_identity():
                    dlg.Destroy()
                    dlg = wx.MessageDialog(
                        None,
                        _("The entered command does nothing."),
                        _("Non-Useful Matrix."),
                        wx.OK | wx.ICON_WARNING,
                    )
                    dlg.ShowModal()
                    dlg.Destroy()
                else:
                    for element in elements.elems():
                        try:
                            element.matrix *= matrix
                            element.modified()
                        except AttributeError:
                            pass

        @context.console_command("dialog_flip", hidden=True)
        def flip(**kwargs):
            dlg = wx.TextEntryDialog(
                gui,
                _(
                    "Material must be jigged at 0,0 either home or home offset.\nHow wide is your material (give units: in, mm, cm, px, etc)?"
                ),
                _("Double Side Flip"),
                "",
            )
            dlg.SetValue("")
            if dlg.ShowModal() == wx.ID_OK:
                unit_width = context.device.unit_width
                length = float(Length(dlg.GetValue(), relative_length=unit_width))
                matrix = Matrix()
                matrix.post_scale(-1.0, 1, length / 2.0, 0)
                for element in context.elements.elems(emphasized=True):
                    try:
                        element.matrix *= matrix
                        element.modified()
                    except AttributeError:
                        pass
            dlg.Destroy()

        @context.console_command("dialog_path", hidden=True)
        def dialog_path(**kwargs):
            dlg = wx.TextEntryDialog(gui, _("Enter SVG Path Data"), _("Path Entry"), "")
            dlg.SetValue("")

            if dlg.ShowModal() == wx.ID_OK:
                path = Path(dlg.GetValue())
                path.stroke = "blue"
                p = abs(path)
                node = context.elements.elem_branch.add(path=p, type="elem path")
                context.elements.classify([node])
            dlg.Destroy()

        @context.console_command("dialog_fill", hidden=True)
        def fill(**kwargs):
            elements = context.elements
            first_selected = elements.first_element(emphasized=True)
            if first_selected is None:
                return
            data = wx.ColourData()
            if first_selected.fill is not None and first_selected.fill != "none":
                data.SetColour(wx.Colour(swizzlecolor(first_selected.fill)))
            dlg = wx.ColourDialog(gui, data)
            if dlg.ShowModal() == wx.ID_OK:
                data = dlg.GetColourData()
                color = data.GetColour()
                rgb = color.GetRGB()
                color = swizzlecolor(rgb)
                color = Color(color, 1.0)
                for elem in elements.elems(emphasized=True):
                    elem.fill = color
                    elem.altered()

        @context.console_command("dialog_stroke", hidden=True)
        def stroke(**kwargs):
            elements = context.elements
            first_selected = elements.first_element(emphasized=True)
            if first_selected is None:
                return
            data = wx.ColourData()
            if first_selected.stroke is not None and first_selected.stroke != "none":
                data.SetColour(wx.Colour(swizzlecolor(first_selected.stroke)))
            dlg = wx.ColourDialog(gui, data)
            if dlg.ShowModal() == wx.ID_OK:
                data = dlg.GetColourData()
                color = data.GetColour()
                rgb = color.GetRGB()
                color = swizzlecolor(rgb)
                color = Color(color, 1.0)
                for elem in elements.elems(emphasized=True):
                    elem.stroke = color
                    elem.altered()

        @context.console_command("dialog_gear", hidden=True)
        def gear(**kwargs):
            dlg = wx.TextEntryDialog(gui, _("Enter Forced Gear"), _("Gear Entry"), "")
            dlg.SetValue("")

            if dlg.ShowModal() == wx.ID_OK:
                value = dlg.GetValue()
                if value in ("0", "1", "2", "3", "4"):
                    context._stepping_force = int(value)
                else:
                    context._stepping_force = None
            dlg.Destroy()

        @context.console_argument(
            "message", help=_("Message to display, optional"), default=""
        )
        @context.console_command("interrupt", hidden=True)
        def interrupt(message="", **kwargs):
            if not message:
                message = _("Spooling Interrupted.")

            dlg = wx.MessageDialog(
                None,
                message + "\n\n" + _("Press OK to Continue."),
                _("Interrupt"),
                wx.OK,
            )
            dlg.ShowModal()
            dlg.Destroy()

        @context.console_command("dialog_load", hidden=True)
        def load_dialog(**kwargs):
            # This code should load just specific project files rather than all importable formats.
            files = context.elements.load_types()
            with wx.FileDialog(
                gui, _("Open"), wildcard=files, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                pathname = fileDialog.GetPath()
                gui.clear_and_open(pathname)

        @context.console_command("dialog_import", hidden=True)
        def import_dialog(**kwargs):
            files = context.elements.load_types()
            with wx.FileDialog(
                gui,
                _("Import"),
                wildcard=files,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                pathname = fileDialog.GetPath()
                gui.load(pathname)

        @context.console_command("dialog_save_as", hidden=True)
        def save_dialog(**kwargs):
            filetypes = []
            types = []
            for saver, save_name, sname in context.find("save"):
                for save_type in saver.save_types():
                    types.append(save_type)
                    description, extension, mimetype, version = save_type
                    filetypes.append(f"{description} ({extension})")
                    filetypes.append(f"*.{extension}")
            files = "|".join(filetypes)

            with wx.FileDialog(
                gui,
                _("Save Project"),
                wildcard=files,
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return
                description, extension, mimetype, version = types[fileDialog.GetFilterIndex()]
                pathname = fileDialog.GetPath()
                if not pathname.lower().endswith(f".{extension}"):
                    pathname += f".{extension}"
                context.elements.save(pathname, version=version)
                gui.validate_save()
                gui.working_file = pathname
                gui.set_file_as_recently_used(gui.working_file)

        @context.console_command("dialog_save", hidden=True)
        def save_or_save_as(**kwargs):
            if gui.working_file is None:
                context(".dialog_save_as\n")
            else:
                gui.set_file_as_recently_used(gui.working_file)
                gui.validate_save()
                context.elements.save(gui.working_file)

        @context.console_command("dialog_import_egv", hidden=True)
        def egv_in_dialog(**kwargs):
            files = "*.egv"
            with wx.FileDialog(
                gui,
                _("Import EGV"),
                wildcard=files,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                pathname = fileDialog.GetPath()
            if pathname is None:
                return
            with wx.BusyInfo(_("Loading File...")):
                context(f"egv_import {pathname}\n")
                return

        @context.console_command("dialog_export_egv", hidden=True)
        def egv_out_dialog(**kwargs):
            files = "*.egv"
            with wx.FileDialog(
                gui, _("Export EGV"), wildcard=files, style=wx.FD_SAVE
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                pathname = fileDialog.GetPath()
            if pathname is None:
                return
            with wx.BusyInfo(_("Saving File...")):
                context(f"egv_export {pathname}\n")
                return

    def __set_panes(self):
        self.context.setting(bool, "pane_lock", False)

        for register_panel in list(self.context.lookup_all("wxpane")):
            register_panel(self, self.context)

        # AUI Manager Update.
        self._mgr.Update()

        self.default_perspective = self._mgr.SavePerspective()
        self.context.setting(str, "perspective")
        if self.context.perspective is not None:
            self._mgr.LoadPerspective(self.context.perspective)

        self.on_config_panes()
        self.__console_commands()

    def __console_commands(self):
        context = self.context

        @context.console_command(
            "pane",
            help=_("control various panes for main window"),
            output_type="panes",
        )
        def panes(**kwargs):
            return "panes", self

        @context.console_argument("pane", help=_("pane to be shown"))
        @context.console_command(
            "show",
            input_type="panes",
            help=_("show the pane"),
            all_arguments_required=True,
        )
        def show_pane(command, _, channel, pane=None, **kwargs):
            _pane = context.lookup("pane", pane)
            if _pane is None:
                channel(_("Pane not found."))
                return
            _pane.Show()
            self._mgr.Update()

        @context.console_command(
            "toggleui",
            input_type="panes",
            help=_("Hides/Restores all the visible panes (except scen)"),
        )
        def toggle_ui(command, _, channel, pane=None, **kwargs):
            # Toggle visibility of all UI-elements
            self.ui_visible = not self.ui_visible

            if self.ui_visible:
                for pane_name in self.hidden_panes:
                    pane = self._mgr.GetPane(pane_name)
                    pane.Show()
                self._mgr.Update()
                channel(_("Panes restored."))
            else:
                self.hidden_panes = []
                for pane in self._mgr.GetAllPanes():
                    if pane.IsShown():
                        if pane.name == "scene":
                            # Scene remains
                            pass
                        else:
                            self.hidden_panes.append(pane.name)
                            pane.Hide()
                self._mgr.Update()
                channel(_("Panes hidden."))

        @context.console_argument("pane", help=_("pane to be hidden"))
        @context.console_command(
            "hide",
            input_type="panes",
            help=_("show the pane"),
            all_arguments_required=True,
        )
        def hide_pane(command, _, channel, pane=None, **kwargs):
            _pane = context.lookup("pane", pane)
            if _pane is None:
                channel(_("Pane not found."))
                return
            _pane.Hide()
            self._mgr.Update()

        @context.console_option("always", "a", type=bool, action="store_true")
        @context.console_argument("pane", help=_("pane to be shown"))
        @context.console_command(
            "float",
            input_type="panes",
            help=_("show the pane"),
            all_arguments_required=True,
        )
        def float_pane(command, _, channel, always=False, pane=None, **kwargs):
            _pane = context.lookup("pane", pane)
            if _pane is None:
                channel(_("Pane not found."))
                return
            _pane.Float()
            _pane.Show()
            _pane.Dockable(not always)
            self._mgr.Update()

        @context.console_command(
            "reset",
            input_type="panes",
            help=_("reset all panes restoring the default perspective"),
        )
        def reset_pane(command, _, channel, **kwargs):
            self.on_pane_reset(None)

        @context.console_command(
            "lock",
            input_type="panes",
            help=_("lock the panes"),
        )
        def lock_pane(command, _, channel, **kwargs):
            self.on_pane_lock(None, lock=True)

        @context.console_command(
            "unlock",
            input_type="panes",
            help=_("unlock the panes"),
        )
        def unlock_pane(command, _, channel, **kwargs):
            self.on_pane_lock(None, lock=False)

        @context.console_argument("pane", help=_("pane to create"))
        @context.console_command(
            "create",
            input_type="panes",
            help=_("create a floating about pane"),
        )
        def create_pane(command, _, channel, pane=None, **kwargs):
            if pane == "about":
                from .about import AboutPanel as CreatePanel

                caption = _("About")
                width = 646
                height = 519
            elif pane == "preferences":
                from .preferences import PreferencesPanel as CreatePanel

                caption = _("Preferences")
                width = 565
                height = 327
            else:
                channel(_("Pane not found."))
                return
            panel = CreatePanel(self, context=context)
            _pane = (
                aui.AuiPaneInfo()
                .Dockable(False)
                .Float()
                .Caption(caption)
                .FloatingSize(width, height)
                .Name(pane)
                .CaptionVisible(True)
            )
            _pane.control = panel
            self.on_pane_add(_pane)
            if hasattr(panel, "pane_show"):
                panel.pane_show()
            self.context.register("pane/about", _pane)
            self._mgr.Update()

    def on_pane_reset(self, event=None):
        self.on_panes_closed()
        self._mgr.LoadPerspective(self.default_perspective, update=True)
        self.on_config_panes()

    def on_panes_closed(self):
        for pane in self._mgr.GetAllPanes():
            if pane.IsShown():
                window = pane.window
                if hasattr(window, "pane_hide"):
                    window.pane_hide()
                if isinstance(window, wx.aui.AuiNotebook):
                    for i in range(window.GetPageCount()):
                        page = window.GetPage(i)
                        if hasattr(page, "pane_hide"):
                            page.pane_hide()

    def on_panes_opened(self):
        for pane in self._mgr.GetAllPanes():
            window = pane.window
            if pane.IsShown():
                if hasattr(window, "pane_show"):
                    window.pane_show()
                if isinstance(window, wx.aui.AuiNotebook):
                    for i in range(window.GetPageCount()):
                        page = window.GetPage(i)
                        if hasattr(page, "pane_show"):
                            page.pane_show()
            else:
                if hasattr(window, "pane_noshow"):
                    window.pane_noshow()
                if isinstance(window, wx.aui.AuiNotebook):
                    for i in range(window.GetPageCount()):
                        page = window.GetPage(i)
                        if hasattr(page, "pane_noshow"):
                            page.pane_noshow()

    def on_config_panes(self):
        self.on_panes_opened()
        self.on_pane_lock(lock=self.context.pane_lock)
        wx.CallAfter(self.on_pane_changed, None)

    def on_pane_lock(self, event=None, lock=None):
        if lock is None:
            self.context.pane_lock = not self.context.pane_lock
        else:
            self.context.pane_lock = lock
        for pane in self._mgr.GetAllPanes():
            if pane.IsShown():
                pane.CaptionVisible(not self.context.pane_lock)
                if hasattr(pane.window, "lock"):
                    pane.window.lock()
        self._mgr.Update()

    def on_pane_add(self, paneinfo: aui.AuiPaneInfo):
        pane = self._mgr.GetPane(paneinfo.name)
        control = paneinfo.control
        if isinstance(control, wx.aui.AuiNotebook):
            for i in range(control.GetPageCount()):
                page = control.GetPage(i)
                self.add_module_delegate(page)
        else:
            self.add_module_delegate(control)
        if len(pane.name):
            if not pane.IsShown():
                pane.Show()
                pane.CaptionVisible(not self.context.pane_lock)
                if hasattr(pane.window, "pane_show"):
                    pane.window.pane_show()
                    wx.CallAfter(self.on_pane_changed, None)
                self._mgr.Update()
            return
        self._mgr.AddPane(
            control,
            paneinfo,
        )

    def on_pane_active(self, event):
        pane = event.GetPane()
        if hasattr(pane.window, "active"):
            pane.window.active()

    def on_pane_closed(self, event):
        pane = event.GetPane()
        if pane.IsShown():
            if hasattr(pane.window, "pane_hide"):
                pane.window.pane_hide()
        wx.CallAfter(self.on_pane_changed, None)

    def on_pane_changed(self, *args):
        for pane in self._mgr.GetAllPanes():
            try:
                shown = pane.IsShown()
                check = pane.window.check
                check(shown)
            except AttributeError:
                pass

    @property
    def is_dark(self):
        return wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127

    def __kernel_initialize(self):
        context = self.context
        context.setting(int, "draw_mode", 0)
        context.setting(bool, "print_shutdown", False)

        @context.console_command(
            "theme", help=_("Theming information and assignments"), hidden=True
        )
        def theme(command, channel, _, **kwargs):
            channel(str(wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)))

        context.setting(str, "file0", None)
        context.setting(str, "file1", None)
        context.setting(str, "file2", None)
        context.setting(str, "file3", None)
        context.setting(str, "file4", None)
        context.setting(str, "file5", None)
        context.setting(str, "file6", None)
        context.setting(str, "file7", None)
        context.setting(str, "file8", None)
        context.setting(str, "file9", None)
        context.setting(str, "file10", None)
        context.setting(str, "file11", None)
        context.setting(str, "file12", None)
        context.setting(str, "file13", None)
        context.setting(str, "file14", None)
        context.setting(str, "file15", None)
        context.setting(str, "file16", None)
        context.setting(str, "file17", None)
        context.setting(str, "file18", None)
        context.setting(str, "file19", None)
        self.populate_recent_menu()

    @lookup_listener("pane")
    def dynamic_fill_pane_menu(self, new=None, old=None):
        def toggle_pane(pane_toggle):
            def toggle(event=None):
                pane_obj = self._mgr.GetPane(pane_toggle)
                if pane_obj.IsShown():
                    if hasattr(pane_obj.window, "pane_hide"):
                        pane_obj.window.pane_hide()
                    pane_obj.Hide()
                    self._mgr.Update()
                    return
                pane_init = self.context.lookup("pane", pane_toggle)
                self.on_pane_add(pane_init)

            return toggle

        self.panes_menu = wx.Menu()
        label = _("Panes")
        index = self.main_menubar.FindMenu(label)
        if index != -1:
            self.main_menubar.Replace(index, self.panes_menu, label)
        else:
            self.main_menubar.Append(self.panes_menu, label)
        submenus = {}
        for pane, _path, suffix_path in self.context.find("pane/.*"):
            try:
                suppress = pane.hide_menu
                if suppress:
                    continue
            except AttributeError:
                pass
            submenu = None
            try:
                submenu_name = pane.submenu
                if submenu_name in submenus:
                    submenu = submenus[submenu_name]
                elif submenu_name is not None:
                    submenu = wx.Menu()
                    self.panes_menu.AppendSubMenu(submenu, submenu_name)
                    submenus[submenu_name] = submenu
            except AttributeError:
                pass
            menu_context = submenu if submenu is not None else self.panes_menu
            try:
                pane_name = pane.name
            except AttributeError:
                pane_name = suffix_path

            pane_caption = pane_name[0].upper() + pane_name[1:] + "."
            try:
                pane_caption = pane.caption
            except AttributeError:
                pass
            if not pane_caption:
                pane_caption = pane_name[0].upper() + pane_name[1:] + "."

            menu_item = menu_context.Append(wx.ID_ANY, pane_caption, "", wx.ITEM_CHECK)
            self.Bind(
                wx.EVT_MENU,
                toggle_pane(pane_name),
                id=menu_item.GetId(),
            )
            pane = self._mgr.GetPane(pane_name)
            try:
                menu_item.Check(pane.IsShown())
                pane.window.check = menu_item.Check
            except AttributeError:
                pass

        self.panes_menu.AppendSeparator()
        item = self.main_menubar.lockpane = self.panes_menu.Append(
            wx.ID_ANY, _("Lock Panes"), "", wx.ITEM_CHECK
        )
        item.Check(self.context.pane_lock)
        self.Bind(
            wx.EVT_MENU,
            self.on_pane_lock,
            id=item.GetId(),
        )

        self.panes_menu.AppendSeparator()
        self.main_menubar.panereset = self.panes_menu.Append(
            wx.ID_ANY, _("Reset Panes"), ""
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_pane_reset,
            id=self.main_menubar.panereset.GetId(),
        )

    @lookup_listener("window")
    def dynamic_fill_window_menu(self, new=None, old=None):
        def toggle_window(_window):
            def toggle(event=None):
                self.context(f"window toggle {_window}\n")

            return toggle

        label = _("Tools")
        self.window_menu = wx.Menu()
        index = self.main_menubar.FindMenu(label)
        if index != -1:
            self.main_menubar.Replace(index, self.window_menu, label)
        else:
            self.main_menubar.Append(self.window_menu, label)

        submenus = {}
        for window, _path, suffix_path in self.context.find("window/.*"):
            if not window.window_menu(None):
                continue
            submenu = None
            try:
                submenu_name = window.submenu
                if submenu_name in submenus:
                    submenu = submenus[submenu_name]
                elif submenu_name is not None:
                    submenu = wx.Menu()
                    self.window_menu.AppendSubMenu(submenu, submenu_name)
                    submenus[submenu_name] = submenu
            except AttributeError:
                pass
            menu_context = submenu if submenu is not None else self.window_menu
            try:
                name = window.name
            except AttributeError:
                name = suffix_path

            try:
                caption = window.caption
            except AttributeError:
                caption = name[0].upper() + name[1:]
            if name in ("Scene", "About"):  # make no sense, so we omit these...
                continue
            # print ("Menu - Name: %s, Caption=%s" % (name, caption))
            menuitem = menu_context.Append(wx.ID_ANY, caption, "", wx.ITEM_NORMAL)
            self.Bind(
                wx.EVT_MENU,
                toggle_window(suffix_path),
                id=menuitem.GetId(),
            )

        self.window_menu.AppendSeparator()
        # If the Main-window has disappeared out of sight (i.e. on a multi-monitor environment)
        # then resetting windows becomes difficult, so a shortcut is in order...
        # REVISED: CTRL-W is needed for mac close-window
        self.window_menu.windowreset = self.window_menu.Append(
            wx.ID_ANY, _("Reset Windows"), ""
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window reset *\n"),
            id=self.window_menu.windowreset.GetId(),
        )

    def __set_menubars(self):
        self.__set_file_menu()
        self.__set_view_menu()
        self.__set_pane_menu()
        self.__set_tool_menu()
        self.__set_window_menu()
        self.__set_help_menu()
        self.add_language_menu()

    def __set_file_menu(self):

        self.file_menu = wx.Menu()
        # ==========
        # FILE MENU
        # ==========

        menu_item = self.file_menu.Append(
            wx.ID_NEW, _("&New\tCtrl-N"), _("Clear Operations, Elements and Notes")
        )
        self.Bind(wx.EVT_MENU, self.on_click_new, id=wx.ID_NEW)

        self.file_menu.Append(
            wx.ID_OPEN,
            _("&Open Project\tCtrl-O"),
            _("Clear existing elements and notes and open a new file"),
        )
        self.Bind(wx.EVT_MENU, self.on_click_open, id=wx.ID_OPEN)

        self.recent_file_menu = wx.Menu()
        if not getattr(sys, "frozen", False) or platform.system() != "Darwin":
            self.file_menu.AppendSubMenu(self.recent_file_menu, _("&Recent"))
        menu_item = self.file_menu.Append(
            wx.ID_ANY,
            _("&Import File"),
            _("Import another file into the same project"),
        )
        self.Bind(wx.EVT_MENU, self.on_click_import, id=menu_item.GetId())
        self.file_menu.AppendSeparator()
        menu_item = self.file_menu.Append(
            wx.ID_SAVE,
            _("&Save\tCtrl-S"),
            _("Save the project as an SVG file (overwriting any existing file)"),
        )
        self.Bind(wx.EVT_MENU, self.on_click_save, id=wx.ID_SAVE)
        menu_item = self.file_menu.Append(
            wx.ID_SAVEAS,
            _("Save &As\tCtrl-Shift-S"),
            _("Save the project in a new SVG file"),
        )
        self.Bind(wx.EVT_MENU, self.on_click_save_as, id=wx.ID_SAVEAS)
        self.file_menu.AppendSeparator()
        if platform.system() == "Darwin":
            menu_item = self.file_menu.Append(
                wx.ID_CLOSE, _("&Close Window\tCtrl-W"), _("Close Meerk40t")
            )
            self.Bind(wx.EVT_MENU, self.on_click_close, id=menu_item.GetId())

        menu_item = self.file_menu.Append(wx.ID_EXIT, _("E&xit"), _("Close Meerk40t"))
        self.Bind(wx.EVT_MENU, self.on_click_exit, id=menu_item.GetId())
        self.main_menubar.Append(self.file_menu, _("File"))

    def __set_view_menu(self):
        def create_draw_mode_item(label, tooltip, FLAG):
            menu_item = self.view_menu.Append(
                wx.ID_ANY,
                label,
                tooltip,
                wx.ITEM_CHECK,
            )
            self.Bind(wx.EVT_MENU, self.toggle_draw_mode(FLAG), id=menu_item.GetId())
            menu_item.Check(self.context.draw_mode & FLAG != 0)

        # ==========
        # VIEW MENU
        # ==========
        self.context.setting(int, "draw_mode", 0)
        self.view_menu = wx.Menu()

        menu_item = self.view_menu.Append(
            wx.ID_ANY, _("Zoom &Out\tCtrl--"), _("Make the scene smaller")
        )
        self.Bind(wx.EVT_MENU, self.on_click_zoom_out, id=menu_item.GetId())

        menu_item = self.view_menu.Append(
            wx.ID_ANY, _("Zoom &In\tCtrl-+"), _("Make the scene larger")
        )
        self.Bind(wx.EVT_MENU, self.on_click_zoom_in, id=menu_item.GetId())
        menu_item = self.view_menu.Append(
            wx.ID_ANY,
            _("Zoom to &Selected\tCtrl-Shift-B"),
            _("Fill the scene area with the selected elements"),
        )
        self.Bind(wx.EVT_MENU, self.on_click_zoom_selected, id=menu_item.GetId())
        menu_item = self.view_menu.Append(
            wx.ID_ANY, _("Zoom to &Bed\tCtrl-B"), _("View the whole laser bed")
        )
        self.Bind(wx.EVT_MENU, self.on_click_zoom_bed, id=menu_item.GetId())
        menu_item = self.view_menu.Append(
            wx.ID_ANY,
            _("Show/Hide UI-Panels\tCtrl-U"),
            _("Show/Hide all panels/ribbon bar"),
        )
        self.Bind(wx.EVT_MENU, self.on_click_toggle_ui, id=menu_item.GetId())

        self.view_menu.AppendSeparator()

        create_draw_mode_item(
            _("Hide Grid"), _("Don't show the sizing grid"), DRAW_MODE_GRID
        )
        create_draw_mode_item(
            _("Hide Background"),
            _("Don't show any background image"),
            DRAW_MODE_BACKGROUND,
        )
        create_draw_mode_item(
            _("Hide Guides"), _("Don't show the measurement guides"), DRAW_MODE_GUIDES
        )
        create_draw_mode_item(
            _("Hide Shapes"),
            _("Don't show shapes (i.e. Rectangles, Paths etc.)"),
            DRAW_MODE_PATH,
        )
        create_draw_mode_item(
            _("Hide Strokes"),
            _("Don't show the strokes (i.e. the edges of SVG shapes)"),
            DRAW_MODE_STROKES,
        )
        # TODO - this function doesn't work.
        create_draw_mode_item(
            _("No Stroke-Width Render"),
            _("Ignore the stroke width when drawing the stroke"),
            DRAW_MODE_LINEWIDTH,
        )
        create_draw_mode_item(
            _("Hide Fills"),
            _("Don't show fills (i.e. the fill inside strokes)"),
            DRAW_MODE_FILLS,
        )
        create_draw_mode_item(_("Hide Images"), _("Don't show images"), DRAW_MODE_IMAGE)
        create_draw_mode_item(
            _("Hide Text"), _("Don't show text elements"), DRAW_MODE_TEXT
        )
        create_draw_mode_item(
            _("Hide Laserpath"),
            _("Don't show the path that the laserhead has followed (blue line)"),
            DRAW_MODE_LASERPATH,
        )
        create_draw_mode_item(
            _("Hide Reticle"),
            _(
                "Don't show the small read circle showing the current laserhead position"
            ),
            DRAW_MODE_RETICLE,
        )
        create_draw_mode_item(
            _("Hide Selection"),
            _("Don't show the selection boundaries and dimensions"),
            DRAW_MODE_SELECTION,
        )
        create_draw_mode_item(
            _("Hide Regmarks"), _("Don't show elements under the regmark branch"), DRAW_MODE_REGMARKS
        )

        # TODO This menu does not clear existing icons or create icons when it is changed
        create_draw_mode_item(_("Hide Icons"), "", DRAW_MODE_ICONS)
        create_draw_mode_item(_("Do Not Cache Image"), "", DRAW_MODE_CACHE)
        create_draw_mode_item(_("Do Not Alpha/Black Images"), "", DRAW_MODE_ALPHABLACK)
        create_draw_mode_item(_("Do Not Refresh"), _(""), DRAW_MODE_REFRESH)
        create_draw_mode_item(_("Do Not Animate"), _(""), DRAW_MODE_ANIMATE)
        create_draw_mode_item(
            _("Invert"),
            _("Show a negative image of the scene by inverting colours"),
            DRAW_MODE_INVERT,
        )
        create_draw_mode_item(
            _("Flip XY"),
            _("Effectively rotate the scene display by 180 degrees"),
            DRAW_MODE_FLIPXY,
        )

        self.view_menu.AppendSeparator()
        create_draw_mode_item(
            _("Show Variables"),
            _("Replace variables in textboxes by their 'real' content"),
            DRAW_MODE_VARIABLES,
        )

        self.main_menubar.Append(self.view_menu, _("View"))

    def __set_pane_menu(self):
        # ==========
        # PANE MENU
        # ==========
        self.dynamic_fill_pane_menu()

    def __set_tool_menu(self):
        # ==========
        # TOOL MENU
        # ==========

        self.dynamic_fill_window_menu()

    def __set_window_menu(self):
        # ==========
        # OSX-ONLY WINDOW MENU
        # ==========
        if platform.system() == "Darwin":
            wt_menu = wx.Menu()
            self.main_menubar.Append(wt_menu, _("Window"))

    def __set_help_menu(self):
        # ==========
        # HELP MENU
        # ==========
        self.help_menu = wx.Menu()

        def launch_help_osx(event=None):
            _resource_path = "help/meerk40t.help"
            if not os.path.exists(_resource_path):
                try:  # pyinstaller internal location
                    # pylint: disable=no-member
                    _resource_path = os.path.join(sys._MEIPASS, "help/meerk40t.help")
                except AttributeError:
                    pass
            if not os.path.exists(_resource_path):
                try:  # Mac py2app resource
                    _resource_path = os.path.join(
                        os.environ["RESOURCEPATH"], "help/meerk40t.help"
                    )
                except KeyError:
                    pass
            if os.path.exists(_resource_path):
                os.system(f"open {_resource_path}")
            else:
                dlg = wx.MessageDialog(
                    None,
                    _('Offline help file ("{help}") was not found.').format(
                        help=_resource_path
                    ),
                    _("File Not Found"),
                    wx.OK | wx.ICON_WARNING,
                )
                dlg.ShowModal()
                dlg.Destroy()

        if platform.system() == "Darwin":
            menuitem = self.help_menu.Append(
                wx.ID_HELP, _("&MeerK40t Help"), _("Open the MeerK40t Mac help file")
            )
            self.Bind(wx.EVT_MENU, launch_help_osx, id=menuitem.GetId())
            menuitem = self.help_menu.Append(
                wx.ID_ANY, _("&Online Help"), _("Open the Meerk40t online wiki")
            )
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.context("webhelp help\n"),
                id=menuitem.GetId(),
            )
        else:
            menuitem = self.help_menu.Append(
                wx.ID_HELP,
                _("&Help"),
                _("Open the Meerk40t online wiki Beginners page"),
            )
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.context("webhelp help\n"),
                id=menuitem.GetId(),
            )

        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("&Beginners' Help"),
            _("Open the Meerk40t online wiki Beginners page"),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp beginners\n"),
            id=menuitem.GetId(),
        )
        menuitem = self.help_menu.Append(
            wx.ID_ANY, _("&Github"), _("Visit Meerk40t's Github home page")
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp main\n"),
            id=menuitem.GetId(),
        )
        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("&Releases"),
            _("Check for a new release on Meerk40t's Github releases page"),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp releases\n"),
            id=menuitem.GetId(),
        )
        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("&Facebook"),
            _("Get help from the K40 Meerk40t Facebook group"),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp facebook\n"),
            id=menuitem.GetId(),
        )
        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("&Discord"),
            _("Chat with developers to get help on the Meerk40t Discord server"),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp discord\n"),
            id=menuitem.GetId(),
        )
        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("&Makers Forum"),
            _("Get help from the Meerk40t page on the Makers Forum"),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp makers\n"),
            id=menuitem.GetId(),
        )
        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("&IRC"),
            _("Chat with developers to get help on the Meerk40t IRC channel"),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp irc\n"),
            id=menuitem.GetId(),
        )
        self.help_menu.AppendSeparator()
        menuitem = self.help_menu.Append(
            wx.ID_ABOUT,
            _("&About MeerK40t"),
            _(
                "Toggle the About window acknowledging those who contributed to creating Meerk40t"
            ),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle About\n"),
            id=menuitem.GetId(),
        )

        self.main_menubar.Append(self.help_menu, _("Help"))

        self.SetMenuBar(self.main_menubar)

    def add_language_menu(self):
        tl = wx.FileTranslationsLoader()
        trans = tl.GetAvailableTranslations("meerk40t")

        if trans:
            wxglade_tmp_menu = wx.Menu()
            i = 0
            for lang in self.context.app.supported_languages:
                language_code, language_name, language_index = lang
                m = wxglade_tmp_menu.Append(
                    wx.ID_ANY, language_name, language_name, wx.ITEM_RADIO
                )
                if i == self.context.language:
                    m.Check(True)

                def language_update(q):
                    return lambda e: self.context.app.update_language(q)

                self.Bind(wx.EVT_MENU, language_update(i), id=m.GetId())
                if language_code not in trans and i != 0:
                    m.Enable(False)
                i += 1
            self.main_menubar.Append(wxglade_tmp_menu, _("Languages"))

    @signal_listener("device;renamed")
    @lookup_listener("service/device/active")
    def on_active_change(self, *args):
        self.__set_titlebar()

    def window_close_veto(self):
        if self.usb_running:
            message = _("The device is actively sending data. Really quit?")
            answer = wx.MessageBox(
                message, _("Currently Sending Data..."), wx.YES_NO | wx.CANCEL, None
            )
            if answer != wx.YES:
                return True  # VETO
        if self.needs_saving:
            message = _(
                "Save changes to project before closing?\n\n"
                "Your changes will be lost if you do not save them."
            )
            answer = wx.MessageBox(
                message, _("Save Project..."), wx.YES_NO | wx.CANCEL, None
            )
            if answer == wx.YES:
                self.context("dialog_save\n")
            if answer == wx.CANCEL:
                return True  # VETO
        return False

    def window_close(self):
        context = self.context

        context.perspective = self._mgr.SavePerspective()
        self.on_panes_closed()
        self._mgr.UnInit()

        if context.print_shutdown:
            context.channel("shutdown").watch(print)
        self.context(".timer 0 1 quit\n")

    @signal_listener("altered")
    @signal_listener("modified")
    def on_invalidate_save(self, origin, *args):
        self.needs_saving = True
        app = self.context.app.GetTopWindow()
        if isinstance(app, wx.TopLevelWindow):
            app.OSXSetModified(self.needs_saving)

    def validate_save(self):
        self.needs_saving = False
        app = self.context.app.GetTopWindow()
        if isinstance(app, wx.TopLevelWindow):
            app.OSXSetModified(self.needs_saving)

    @signal_listener("warning")
    def on_warning_signal(self, origin, message, caption, style):
        if style is None:
            style = wx.OK | wx.ICON_WARNING
        dlg = wx.MessageDialog(
            None,
            message,
            caption,
            style,
        )
        dlg.ShowModal()
        dlg.Destroy()

    @signal_listener("device;noactive")
    def on_device_noactive(self, origin, value):
        dlg = wx.MessageDialog(
            None,
            _("No active device existed. Add a primary device."),
            _("Active Device"),
            wx.OK | wx.ICON_WARNING,
        )
        dlg.ShowModal()
        dlg.Destroy()

    @signal_listener("pipe;failing")
    def on_usb_error(self, origin, value):
        if value == 5:
            self.context.signal("controller", origin)
            dlg = wx.MessageDialog(
                None,
                _("All attempts to connect to USB have failed."),
                _("Usb Connection Problem."),
                wx.OK | wx.ICON_WARNING,
            )
            dlg.ShowModal()
            dlg.Destroy()

    @signal_listener("cutplanning;failed")
    def on_usb_error(self, origin, error):
        dlg = wx.MessageDialog(
            None,
            _("Cut planning failed because: {error}".format(error=error)),
            _("Cut Planning Failed"),
            wx.OK | wx.ICON_WARNING,
        )
        dlg.ShowModal()
        dlg.Destroy()

    @signal_listener("pipe;running")
    def on_usb_running(self, origin, value):
        self.usb_running = value

    @signal_listener("pipe;usb_status")
    def on_usb_state_text(self, origin, value):
        self.main_statusbar.SetStatusText(
            _("Usb: {index}").format(index=value),
            1,
        )

    @signal_listener("pipe;thread")
    def on_pipe_state(self, origin, state):
        if state == self.pipe_state:
            return
        self.pipe_state = state

        self.main_statusbar.SetStatusText(
            _("Controller: {state}").format(
                state=self.context.kernel.get_text_thread_state(state)
            ),
            2,
        )

    @signal_listener("spooler;thread")
    def on_spooler_state(self, origin, value):
        self.main_statusbar.SetStatusText(
            _("Spooler: {state}").format(
                state=self.context.get_text_thread_state(value)
            ),
            3,
        )
        self.main_statusbar.Signal("spooler;thread", value)

    @signal_listener("spooler;queue")
    def on_spooler_queue_signal(self, origin, *args):
        self.main_statusbar.Signal("spooler;queue", args)

        if not self.context.show_colorbar or not self.widgets_created:
            return
        # Queue Len
        if len(args) > 0:
            value = args[0]
        else:
            value = 0
        flag = value > 0
        self.main_statusbar.activate_panel("burninfo", flag)

    @signal_listener("driver;position")
    @signal_listener("emulator;position")
    def on_device_update(self, origin, pos):
        self.main_statusbar.Signal("spooler;update")

    @signal_listener("spooler;completed")
    def on_spool_finished(self, origin, pos):
        self.main_statusbar.Signal("spooler;completed")

    @signal_listener("export-image")
    def on_export_signal(self, origin, frame):
        image_width, image_height, frame = frame
        if frame is not None:
            elements = self.context.elements
            img = Image.fromarray(frame)
            node = elements.elem_branch.add(
                image=img, width=image_width, height=image_height, type="elem image"
            )
            elements.classify([node])

    @signal_listener("statusmsg")
    def on_update_statusmsg(self, origin, value):
        self.main_statusbar.SetStatusText(value, 0)

    @signal_listener("statusupdate")
    def on_update_statuspanel(self, origin, value=None):
        self.main_statusbar.Reposition(value)

    def __set_titlebar(self):
        device_name = ""
        device_version = ""
        title = (
            f"{str(self.context.kernel.name)} v{self.context.kernel.version}      "
            f"{self.context.device.label}"
        )
        self.SetTitle(title)

    def __set_properties(self):
        # begin wxGlade: MeerK40t.__set_properties
        self.__set_titlebar()
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_meerk40t.GetBitmap())
        self.SetIcon(_icon)

    def load_or_open(self, filename):
        """
        Loads recent file name given. If the filename cannot be opened attempts open dialog at last known location.
        """
        if os.path.exists(filename):
            try:
                self.load(filename)
            except PermissionError:
                self.tryopen(filename)
        else:
            self.tryopen(filename)

    def tryopen(self, filename):
        """
        Loads an open dialog at given filename to load data.
        """
        files = self.context.elements.load_types()
        default_file = os.path.basename(filename)
        default_dir = os.path.dirname(filename)

        with wx.FileDialog(
            self,
            _("Open"),
            defaultDir=default_dir,
            defaultFile=default_file,
            wildcard=files,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fileDialog:
            fileDialog.SetFilename(default_file)
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind
            pathname = fileDialog.GetPath()
            self.load(pathname)

    def populate_recent_menu(self):
        if not hasattr(self, "recent_file_menu"):
            return  # No menu, cannot populate.

        context = self.context
        recents = [
            (context.file0, "&1 "),
            (context.file1, "&2 "),
            (context.file2, "&3 "),
            (context.file3, "&4 "),
            (context.file4, "&5 "),
            (context.file5, "&6 "),
            (context.file6, "&7 "),
            (context.file7, "&8 "),
            (context.file8, "&9 "),
            (context.file9, "1&0"),
            (context.file10, "11"),
            (context.file11, "12"),
            (context.file12, "13"),
            (context.file13, "14"),
            (context.file14, "15"),
            (context.file15, "16"),
            (context.file16, "17"),
            (context.file17, "18"),
            (context.file18, "19"),
            (context.file19, "20"),
        ]

        # for i in range(self.recent_file_menu.MenuItemCount):
        # self.recent_file_menu.Remove(self.recent_file_menu.FindItemByPosition(0))

        for item in self.recent_file_menu.GetMenuItems():
            self.recent_file_menu.Remove(item)

        for file, shortcode in recents:
            if file is not None and file:
                shortfile = _("Load {file}...").format(file=os.path.basename(file))
                menuitem = self.recent_file_menu.Append(
                    wx.ID_ANY, shortcode + "  " + file.replace("&", "&&"), shortfile
                )
                self.Bind(
                    wx.EVT_MENU,
                    partial(lambda f, event: self.load_or_open(f), file),
                    id=menuitem.GetId(),
                )

        if self.recent_file_menu.MenuItemCount != 0:
            self.recent_file_menu.AppendSeparator()
            menuitem = self.recent_file_menu.Append(
                wx.ID_ANY,
                _("Clear Recent"),
                _("Delete the list of recent projects"),
            )
            self.Bind(wx.EVT_MENU, lambda e: self.clear_recent(), id=menuitem.GetId())

    def clear_recent(self):
        for i in range(20):
            try:
                setattr(self.context, "file" + str(i), "")
            except IndexError:
                break
        self.populate_recent_menu()

    def set_file_as_recently_used(self, pathname):
        recent = list()
        for i in range(20):
            recent.append(getattr(self.context, "file" + str(i)))
        recent = [r for r in recent if r is not None and r != pathname and len(r) > 0]
        recent.insert(0, pathname)
        for i in range(20):
            try:
                setattr(self.context, "file" + str(i), recent[i])
            except IndexError:
                break
        self.populate_recent_menu()

    def clear_project(self):
        context = self.context
        self.working_file = None
        self.validate_save()
        context.elements.clear_all()
        self.context(".laserpath_clear\n")

    def clear_and_open(self, pathname):
        self.clear_project()
        if self.load(pathname):
            try:
                if self.context.uniform_svg and pathname.lower().endswith("svg"):
                    # or (len(elements) > 0 and "meerK40t" in elements[0].values):
                    # TODO: Disabled uniform_svg, no longer detecting namespace.
                    self.working_file = pathname
                    self.validate_save()
            except AttributeError:
                pass

    def load(self, pathname):
        try:
            try:
                # Reset to standard tool
                self.context("tool none\n")
                self.context.signal("freeze_tree", True)
                # wxPython 4.1.+
                with wx.BusyInfo(
                    wx.BusyInfoFlags().Title(_("Loading File...")).Label(pathname)
                ):
                    n = self.context.elements.note
                    results = self.context.elements.load(
                        pathname,
                        channel=self.context.channel("load"),
                        svg_ppi=self.context.elements.svg_ppi,
                    )
                self.context.signal("freeze_tree", False)
            except AttributeError:
                # wxPython 4.0
                self.context.signal("freeze_tree", True)
                with wx.BusyInfo(_("Loading File...")):
                    n = self.context.elements.note
                    results = self.context.elements.load(
                        pathname,
                        channel=self.context.channel("load"),
                        svg_ppi=self.context.elements.svg_ppi,
                    )
                self.context.signal("freeze_tree", False)
        except BadFileError as e:
            dlg = wx.MessageDialog(
                None,
                str(e),
                _("File is Malformed"),
                wx.OK | wx.ICON_WARNING,
            )
            dlg.ShowModal()
            dlg.Destroy()
            return False
        else:
            if results:
                zl = self.context.zoom_level
                self.context(f"scene focus -{zl}% -{zl}% {100 + zl}% {100 + zl}%\n")

                self.set_file_as_recently_used(pathname)
                if n != self.context.elements.note and self.context.elements.auto_note:
                    self.context("window open Notes\n")  # open/not toggle.
                return True
            return False

    def on_drop_file(self, event):
        """
        Drop file handler

        Accepts multiple files drops.
        """
        accepted = 0
        rejected = 0
        rejected_files = []
        for pathname in event.GetFiles():
            if self.load(pathname):
                accepted += 1
            else:
                rejected += 1
                rejected_files.append(pathname)
        if rejected != 0:
            reject = "\n".join(rejected_files)
            err_msg = _("Some files were unrecognized:\n{rejected_files}").format(
                rejected_files=reject
            )
            dlg = wx.MessageDialog(
                None, err_msg, _("Error encountered"), wx.OK | wx.ICON_ERROR
            )
            dlg.ShowModal()
            dlg.Destroy()

    def on_size(self, event):
        if self.context is None:
            return
        self.Layout()
        if not self.context.disable_auto_zoom:
            zl = self.context.zoom_level
            self.context(f"scene focus -{zl}% -{zl}% {100 + zl}% {100 + zl}%\n")

    def on_focus_lost(self, event):
        self.context("-laser\nend\n")
        # event.Skip()

    def on_click_new(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        self.clear_project()

    def on_click_open(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        self.context(".dialog_load\n")

    def on_click_import(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        self.context(".dialog_import\n")

    def on_click_stop(self, event=None):
        self.context("estop\n")

    def on_click_pause(self, event=None):
        self.context("pause\n")

    def on_click_save(self, event):
        self.context(".dialog_save\n")

    def on_click_save_as(self, event=None):
        self.context(".dialog_save_as\n")

    def on_click_close(self, event=None):
        try:
            window = self.context.app.GetTopWindow().FindFocus().GetTopLevelParent()
            if window is self:
                return
            window.Close(False)
        except RuntimeError:
            pass

    def on_click_exit(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        try:
            self.Close()
        except RuntimeError:
            pass

    def on_click_zoom_out(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoomout button press
        """
        self.context(f"scene zoom {1.0 / 1.5}\n")

    def on_click_zoom_in(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoomin button press
        """
        self.context(f"scene zoom {1.5}\n")

    def on_click_zoom_selected(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoom scene to selected items.
        """
        bbox = self.context.elements.selected_area()
        if bbox is None:
            self.on_click_zoom_bed(event=event)
        else:
            zfact = self.context.zoom_level / 100.0

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

    def on_click_toggle_ui(self, event=None):
        self.context("pane toggleui\n")
        zl = self.context.zoom_level
        self.context(f"scene focus -{zl}% -{zl}% {100 + zl}% {100 + zl}%\n")

    def on_click_zoom_bed(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoom scene to bed size.
        """
        zoom = self.context.zoom_level
        self.context(f"scene focus -a {-zoom}% {-zoom}% {zoom+100}% {zoom+100}%\n")

    def toggle_draw_mode(self, bits):
        """
        Toggle the draw mode.
        @param bits: Bit to toggle.
        @return: Toggle function.
        """

        def toggle(event=None):
            self.context.draw_mode ^= bits
            self.context.signal("draw_mode", self.context.draw_mode)
            self.context.signal("refresh_scene", "Scene")

        return toggle

    def update_statusbar(self, text):
        self.main_statusbar.SetStatusText(text, 0)

    def status_update(self):
        self.update_statusbar("")

    # The standard wx.Frame version of DoGiveHelp is not passed the help text in Windows
    # (no idea about other platforms - wxWidgets code for each platform is different)
    # and has no way of knowing the menuitem and getting the text itself.

    # So we override the standard wx.Frame version and make it do nothing
    # and capture the EVT_MENU_HIGHLIGHT ourselves to process it.
    def DoGiveHelp(self, text, show):
        """Override wx default DoGiveHelp method

        Because we do not call event.Skip() on EVT_MENU_HIGHLIGHT, this should not be called.
        """
        if self.DoGiveHelp_called:
            return
        if text:
            print("DoGiveHelp called with help text:", text)
        else:
            print("DoGiveHelp called but still no help text")
        self.DoGiveHelp_called = True

    def on_menu_open(self, event):
        self.menus_open += 1
        menu = event.GetMenu()
        if menu:
            title = menu.GetTitle()
            if title:
                self.update_statusbar(title + "...")

    def on_menu_close(self, event):
        self.menus_open -= 1
        if self.menus_open <= 0:
            self.top_menu = None
        self.status_update()

    def on_menu_highlight(self, event):
        menuid = event.GetId()
        menu = event.GetMenu()
        if menuid == wx.ID_SEPARATOR:
            self.update_statusbar("...")
            return
        if not self.top_menu and not menu:
            self.status_update()
            return
        if menu and not self.top_menu:
            self.top_menu = menu
        if self.top_menu and not menu:
            menu = self.top_menu
        menuitem, submenu = menu.FindItem(menuid)
        if not menuitem:
            self.update_statusbar("...")
            return
        helptext = menuitem.GetHelp()
        if not helptext:
            helptext = f'{menuitem.GetItemLabelText()} ({_("No help text")})'
        self.update_statusbar(helptext)
