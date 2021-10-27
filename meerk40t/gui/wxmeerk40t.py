# -*- coding: utf-8 -*-

import copy
import os
import sys
import traceback

try:
    import wx
except ImportError as e:
    from ..core.exceptions import Mk40tImportAbort

    raise Mk40tImportAbort("wxpython")

import wx.aui as aui
import wx.ribbon as RB

from meerk40t.gui.panes.jog import Jog
from meerk40t.gui.panes.position import PositionPanel

from ..core.cutcode import CutCode
from ..main import MEERK40T_VERSION
from .file.fileoutput import FileOutput
from .groupproperties import GroupProperty
from .mwindow import MWindow
from .panes.camerapanel import CameraPanel
from .panes.consolepanel import ConsolePanel, Console
from .panes.devicespanel import DevicesPanel
from .panes.dragpanel import Drag
from .panes.jogdistancepanel import JogDistancePanel
from .panes.movepanel import MovePanel
from .panes.notespanel import NotePanel
from .panes.pulsepanel import PulsePanel
from .panes.spoolerpanel import SpoolerPanel, JobSpooler
from .panes.transformpanel import Transform
from .scene.scene import ScenePanel
from .scene.scenewidgets import (
    ElementsWidget,
    GridWidget,
    GuideWidget,
    LaserPathWidget,
    RectSelectWidget,
    ReticleWidget,
    SelectionWidget,
)
from .scene.toolwidgets import DrawTool, RectTool, ToolContainer
from .simulation import Simulation

try:
    from math import tau
except ImportError:
    from math import pi

    tau = pi * 2

from ..core.elements import LaserOperation, isDot
from ..device.lasercommandconstants import (
    COMMAND_FUNCTION,
    COMMAND_HOME,
    COMMAND_JOG,
    COMMAND_JOG_FINISH,
    COMMAND_JOG_SWITCH,
    COMMAND_LASER_OFF,
    COMMAND_LASER_ON,
    COMMAND_MODE_PROGRAM,
    COMMAND_MODE_RAPID,
    COMMAND_MOVE,
    COMMAND_SET_ABSOLUTE,
    COMMAND_SET_DIRECTION,
    COMMAND_SET_SPEED,
    COMMAND_WAIT,
    COMMAND_WAIT_FINISH,
)
from ..kernel import STATE_BUSY, ConsoleFunction, Module
from ..svgelements import (
    SVG_ATTR_STROKE,
    Color,
    Group,
    Length,
    Matrix,
    Path,
    Shape,
    SVGElement,
    SVGImage,
    SVGText,
)
from .about import About
from .bufferview import BufferView
from .camerainteface import CameraInterface
from .controller import Controller
from .devicemanager import DeviceManager
from .executejob import ExecuteJob
from .icons import (
    icon_meerk40t,
    icons8_administrative_tools_50,
    icons8_camera_50,
    icons8_comments_50,
    icons8_computer_support_50,
    icons8_connected_50,
    icons8_console_50,
    icons8_direction_20,
    icons8_emergency_stop_button_50,
    icons8_fantasy_50,
    icons8_file_20,
    icons8_gas_industry_50,
    icons8_group_objects_20,
    icons8_home_filled_50,
    icons8_keyboard_50,
    icons8_laser_beam_20,
    icons8_laser_beam_52,
    icons8_laser_beam_hazard2_50,
    icons8_manager_50,
    icons8_move_50,
    icons8_opened_folder_50,
    icons8_pause_50,
    icons8_roll_50,
    icons8_route_50,
    icons8_save_50,
    icons8_scatter_plot_20,
    icons8_system_task_20,
    icons8_vector_20,
)
from .imageproperty import ImageProperty
from .keymap import Keymap
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
    DRAW_MODE_RETICLE,
    DRAW_MODE_SELECTION,
    DRAW_MODE_STROKES,
    DRAW_MODE_TEXT,
    DRAW_MODE_TREE,
    LaserRender,
    swizzlecolor,
)
from .lhystudios.lhystudiosaccel import LhystudiosAccelerationChart
from .lhystudios.lhystudioscontrollergui import LhystudiosControllerGui
from .lhystudios.lhystudiosdrivergui import LhystudiosDriverGui
from .moshi.moshicontrollergui import MoshiControllerGui
from .moshi.moshidrivergui import MoshiDriverGui
from .navigation import Navigation
from .notes import Notes
from .operationproperty import OperationProperty
from .pathproperty import PathProperty
from .preferences import Preferences
from .rasterwizard import RasterWizard
from .rotarysettings import RotarySettings
from .settings import Settings
from .tcp.tcpcontroller import TCPController
from .textproperty import TextProperty
from .usbconnect import UsbConnect

"""
Laser software for the Stock-LIHUIYU laserboard.

MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed
open-source laser cutting software. See https://github.com/meerk40t/meerk40t
for full details.

wxMeerK40t is the primary gui addon for MeerK40t. It requires wxPython for the interface.
The Transformations work in Windows/OSX/Linux for wxPython 4.0+ (and likely before)

"""

MILS_IN_MM = 39.3701

GUI_START = [True]


def plugin(kernel, lifecycle):
    if lifecycle == "console":
        GUI_START[0] = False

        @kernel.console_command("gui", help=_("starts the gui"))
        def gui_start(**kwargs):
            del kernel.registered["command/None/gui"]
            kernel_root = kernel.root
            meerk40tgui = kernel_root.open("module/wxMeerK40t")
            kernel.console("window open MeerK40t\n")
            meerk40tgui.MainLoop()

    elif lifecycle == "preregister":
        kernel.register("module/wxMeerK40t", wxMeerK40t)
        kernel_root = kernel.root
        kernel_root.open("module/wxMeerK40t")

        context = kernel.root
        renderer = LaserRender(context)
        context.register("render-op/make_raster", renderer.make_raster)
    if GUI_START[0]:
        if lifecycle == "mainloop":
            kernel_root = kernel.root
            meerk40tgui = kernel_root.open("module/wxMeerK40t")
            kernel.console("window open MeerK40t\n")
            meerk40tgui.MainLoop()


ID_MAIN_TOOLBAR = wx.NewId()
ID_ADD_FILE = wx.NewId()
ID_OPEN = wx.NewId()

ID_SAVE = wx.NewId()
ID_NAV = wx.NewId()
ID_USB = wx.NewId()
ID_CONTROLLER = wx.NewId()
ID_CONFIGURATION = wx.NewId()
ID_DEVICES = wx.NewId()
ID_CAMERA = wx.NewId()
ID_CAMERA1 = wx.NewId()
ID_CAMERA2 = wx.NewId()
ID_CAMERA3 = wx.NewId()
ID_CAMERA4 = wx.NewId()
ID_CAMERA5 = wx.NewId()
ID_JOB = wx.NewId()
ID_SIM = wx.NewId()
ID_PAUSE = wx.NewId()
ID_STOP = wx.NewId()

ID_SPOOLER = wx.NewId()
ID_KEYMAP = wx.NewId()
ID_SETTING = wx.NewId()
ID_NOTES = wx.NewId()
ID_OPERATIONS = wx.NewId()
ID_CONSOLE = wx.NewId()
ID_ROTARY = wx.NewId()
ID_RASTER = wx.NewId()

ID_BEGINNERS = wx.NewId()
ID_HOMEPAGE = wx.NewId()
ID_RELEASES = wx.NewId()
ID_FACEBOOK = wx.NewId()
ID_MAKERS_FORUM = wx.NewId()
ID_IRC = wx.NewId()

ID_SELECT = wx.NewId()

ID_MENU_IMPORT = wx.NewId()
ID_MENU_RECENT = wx.NewId()
ID_MENU_ZOOM_OUT = wx.NewId()
ID_MENU_ZOOM_IN = wx.NewId()
ID_MENU_ZOOM_SIZE = wx.NewId()

# 1 fill, 2 grids, 4 guides, 8 laserpath, 16 writer_position, 32 selection
ID_MENU_HIDE_FILLS = wx.NewId()
ID_MENU_HIDE_GUIDES = wx.NewId()
ID_MENU_HIDE_GRID = wx.NewId()
ID_MENU_HIDE_BACKGROUND = wx.NewId()
ID_MENU_HIDE_LINEWIDTH = wx.NewId()
ID_MENU_HIDE_STROKES = wx.NewId()
ID_MENU_HIDE_ICONS = wx.NewId()
ID_MENU_HIDE_TREE = wx.NewId()
ID_MENU_HIDE_LASERPATH = wx.NewId()
ID_MENU_HIDE_RETICLE = wx.NewId()
ID_MENU_HIDE_SELECTION = wx.NewId()
ID_MENU_SCREEN_REFRESH = wx.NewId()
ID_MENU_SCREEN_ANIMATE = wx.NewId()
ID_MENU_SCREEN_INVERT = wx.NewId()
ID_MENU_SCREEN_FLIPXY = wx.NewId()
ID_MENU_PREVENT_CACHING = wx.NewId()
ID_MENU_PREVENT_ALPHABLACK = wx.NewId()
ID_MENU_HIDE_IMAGE = wx.NewId()
ID_MENU_HIDE_PATH = wx.NewId()
ID_MENU_HIDE_TEXT = wx.NewId()

ID_MENU_FILE0 = wx.NewId()
ID_MENU_FILE1 = wx.NewId()
ID_MENU_FILE2 = wx.NewId()
ID_MENU_FILE3 = wx.NewId()
ID_MENU_FILE4 = wx.NewId()
ID_MENU_FILE5 = wx.NewId()
ID_MENU_FILE6 = wx.NewId()
ID_MENU_FILE7 = wx.NewId()
ID_MENU_FILE8 = wx.NewId()
ID_MENU_FILE9 = wx.NewId()
ID_MENU_FILE_CLEAR = wx.NewId()

ID_MENU_KEYMAP = wx.NewId()
ID_MENU_DEVICE_MANAGER = wx.NewId()
ID_MENU_SETTINGS = wx.NewId()
ID_MENU_ROTARY = wx.NewId()
ID_MENU_NAVIGATION = wx.NewId()
ID_MENU_NOTES = wx.NewId()
ID_MENU_OPERATIONS = wx.NewId()
ID_MENU_CONTROLLER = wx.NewId()
ID_MENU_CAMERA = wx.NewId()
ID_MENU_CONSOLE = wx.NewId()
ID_MENU_USB = wx.NewId()
ID_MENU_SPOOLER = wx.NewId()
ID_MENU_SIMULATE = wx.NewId()
ID_MENU_RASTER_WIZARD = wx.NewId()
ID_MENU_WINDOW_RESET = wx.NewId()
ID_MENU_PANE_RESET = wx.NewId()
ID_MENU_PANE_LOCK = wx.NewId()
ID_MENU_JOB = wx.NewId()
ID_MENU_TREE = wx.NewId()

ID_ALIGN_LEFT = wx.NewId()
ID_ALIGN_RIGHT = wx.NewId()
ID_ALIGN_TOP = wx.NewId()
ID_ALIGN_BOTTOM = wx.NewId()
ID_ALIGN_CENTER = wx.NewId()

ID_ALIGN_SPACE_V = wx.NewId()
ID_ALIGN_SPACE_H = wx.NewId()

ID_FLIP_HORIZONTAL = wx.NewId()
ID_FLIP_VERTICAL = wx.NewId()
ID_GROUP = wx.NewId()
ID_UNGROUP = wx.NewId()
ID_TOOL_POSITION = wx.NewId()
ID_TOOL_OVAL = wx.NewId()
ID_TOOL_CIRCLE = wx.NewId()
ID_TOOL_POLYGON = wx.NewId()
ID_TOOL_POLYLINE = wx.NewId()
ID_TOOL_RECT = wx.NewId()
ID_TOOL_TEXT = wx.NewId()

_ = wx.GetTranslation
supported_languages = (
    ("en", u"English", wx.LANGUAGE_ENGLISH),
    ("it", u"italiano", wx.LANGUAGE_ITALIAN),
    ("fr", u"français", wx.LANGUAGE_FRENCH),
    ("de", u"Deutsch", wx.LANGUAGE_GERMAN),
    ("es", u"español", wx.LANGUAGE_SPANISH),
    ("zh", u"中文", wx.LANGUAGE_CHINESE),
    ("hu", u"Magyar", wx.LANGUAGE_HUNGARIAN),
)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class MeerK40t(MWindow):
    """
    MeerK40t main window
    """

    def __init__(self, *args, **kwds):
        super().__init__(1200, 600, *args, **kwds)
        try:
            self.EnableTouchEvents(wx.TOUCH_ZOOM_GESTURE | wx.TOUCH_PAN_GESTURES)
        except AttributeError:
            # Not WX 4.1
            pass
        self.usb_running = False
        context = self.context
        self.context.setting(bool, "disable_tool_tips", False)
        if self.context.disable_tool_tips:
            wx.ToolTip.Enable(False)

        self.root_context = context.root
        context._kernel.run_later = self.run_later
        self.DragAcceptFiles(True)

        self.renderer = LaserRender(context)
        self.working_file = None
        self._rotary_view = False
        self.pipe_state = None
        self.previous_position = None
        self.ribbonbar_caption_visible = False
        self.is_paused = False

        # Define Tree
        self.wxtree = wx.TreeCtrl(
            self, wx.ID_ANY, style=wx.TR_MULTIPLE | wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT
        )
        self.__set_tree()

        # Define Scene
        self.scene = ScenePanel(
            self.context, self, scene_name="Scene", style=wx.EXPAND | wx.WANTS_CHARS
        )
        self.widget_scene = self.scene.scene

        # Define Ribbon.
        self._ribbon = RB.RibbonBar(
            self,
            style=RB.RIBBON_BAR_FLOW_HORIZONTAL
            | RB.RIBBON_BAR_SHOW_PAGE_LABELS
            | RB.RIBBON_BAR_SHOW_PANEL_EXT_BUTTONS
            | RB.RIBBON_BAR_SHOW_TOGGLE_BUTTON
            | RB.RIBBON_BAR_SHOW_HELP_BUTTON,
        )
        self.__set_ribbonbar()

        self._mgr = aui.AuiManager()
        self._mgr.SetFlags(self._mgr.GetFlags() | aui.AUI_MGR_LIVE_RESIZE)
        self._mgr.Bind(aui.EVT_AUI_PANE_CLOSE, self.on_pane_closed)
        self._mgr.Bind(aui.EVT_AUI_PANE_ACTIVATED, self.on_pane_active)

        # notify AUI which frame to use
        self._mgr.SetManagedWindow(self)

        self.__set_panes()

        # Menu Bar
        self.main_menubar = wx.MenuBar()
        self.__set_menubar()

        self.main_statusbar = self.CreateStatusBar(3)

        self.Bind(wx.EVT_DROP_FILES, self.on_drop_file)

        self.__set_properties()
        self.__do_layout()

        self.wxtree.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.wxtree.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.scene.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.scene.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.scene.scene_panel.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.scene.scene_panel.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.__set_titlebar()
        self.__kernel_initialize(context)

        self.Bind(wx.EVT_SIZE, self.on_size)

        self.CenterOnScreen()

        self.on_rebuild_tree_request()

    def __set_panes(self):
        self.context.setting(bool, "pane_lock", True)
        # self.notebook = wx.aui.AuiNotebook(self, -1, size=(200, 150))
        # self._mgr.AddPane(self.notebook, aui.AuiPaneInfo().CenterPane().Name("scene"))
        # self.notebook.AddPage(self.scene, "scene")
        self._mgr.AddPane(self.scene, aui.AuiPaneInfo().CenterPane().Name("scene"))

        # Define Jog
        from .panes.jog import register_panel

        register_panel(self, self.context)

        # Define Drag.
        from .panes.dragpanel import register_panel

        register_panel(self, self.context)

        # Define Transform.
        from .panes.transformpanel import register_panel

        register_panel(self, self.context)

        # Define Jog Distance.
        from .panes.jogdistancepanel import register_panel

        register_panel(self, self.context)

        # Define Pulse.
        from .panes.pulsepanel import register_panel

        register_panel(self, self.context)

        # Define Move.
        from .panes.movepanel import register_panel

        register_panel(self, self.context)

        # Define Tree
        pane = (
            aui.AuiPaneInfo()
            .Name("tree")
            .Left()
            .MinSize(200, -1)
            .LeftDockable()
            .RightDockable()
            .BottomDockable(False)
            .Caption(_("Tree"))
            .CaptionVisible(not self.context.pane_lock)
            .TopDockable(False)
        )
        pane.dock_proportion = 275
        pane.control = self.wxtree
        self.on_pane_add(pane)
        self.context.register("pane/tree", pane)

        # Define Laser.
        from .panes.laserpanel import register_panel

        register_panel(self, self.context)

        # Define Position
        from .panes.position import register_panel

        register_panel(self, self.context)

        pane = (
            aui.AuiPaneInfo()
            .Name("ribbon")
            .Top()
            .RightDockable(False)
            .LeftDockable(False)
            .MinSize(300, 120)
            .FloatingSize(640, 120)
            .Caption(_("Ribbon"))
            .CaptionVisible(not self.context.pane_lock)
        )
        pane.dock_proportion = 640
        pane.control = self._ribbon

        self.on_pane_add(pane)
        self.context.register("pane/ribbon", pane)

        from .panes.toolbarproject import register_project_tools

        register_project_tools(context=self.context, gui=self)

        from .panes.toolbarcontrol import register_control_tools

        register_control_tools(context=self.context, gui=self)

        from .panes.toolbarpreferences import register_preferences_tools

        register_preferences_tools(context=self.context, gui=self)

        from .panes.toolbarmodify import register_modify_tools

        register_modify_tools(context=self.context, gui=self)

        from .panes.toolbaralign import register_align_tools

        register_align_tools(context=self.context, gui=self)

        self.context.setting(bool, "developer_mode", False)
        if self.context.developer_mode:

            from .panes.toolbarshapes import register_shapes_tools

            register_shapes_tools(context=self.context, gui=self)

        # Define Go
        go = wx.BitmapButton(self, wx.ID_ANY, icons8_gas_industry_50.GetBitmap())

        def busy_go_plan(*args):
            with wx.BusyInfo(_("Processing and sending...")):
                self.context(
                    "plan clear copy preprocess validate blob preopt optimize spool\nplan clear\n"
                )

        self.Bind(
            wx.EVT_BUTTON,
            busy_go_plan,
            go,
        )
        go.SetBackgroundColour(wx.Colour(0, 127, 0))
        go.SetToolTip(_("One Touch: Send Job To Laser "))
        go.SetSize(go.GetBestSize())
        pane = (
            aui.AuiPaneInfo()
            .Bottom()
            .Caption(_("Go"))
            .MinSize(40, 40)
            .FloatingSize(98, 98)
            .Name("go")
            .CaptionVisible(not self.context.pane_lock)
            .Hide()
        )
        pane.dock_proportion = 98
        pane.control = go

        self.on_pane_add(pane)
        self.context.register("pane/go", pane)

        # Define Stop.
        stop = wx.BitmapButton(
            self, wx.ID_ANY, icons8_emergency_stop_button_50.GetBitmap()
        )
        self.Bind(
            wx.EVT_BUTTON,
            ConsoleFunction(self.context, "dev estop\n"),
            stop,
        )
        stop.SetBackgroundColour(wx.Colour(127, 0, 0))
        stop.SetToolTip(_("Emergency stop/reset the controller."))
        stop.SetSize(stop.GetBestSize())
        pane = (
            aui.AuiPaneInfo()
            .Bottom()
            .Caption(_("Stop"))
            .MinSize(40, 40)
            .FloatingSize(98, 98)
            .Name("stop")
            .CaptionVisible(not self.context.pane_lock)
        )
        pane.dock_proportion = 98
        pane.control = stop

        self.on_pane_add(pane)
        self.context.register("pane/stop", pane)

        # Define Pause.
        pause = wx.BitmapButton(
            self, wx.ID_ANY, icons8_pause_50.GetBitmap(use_theme=False)
        )

        def on_pause_button(event=None):
            try:
                self.context("dev pause\n")
                # if self.pipe_state != 3:
                #     pause.SetBitmap(icons8_play_50.GetBitmap())
                # else:
                # pause.SetBitmap(icons8_pause_50.GetBitmap(use_theme=False))
            except AttributeError:
                pass

        self.Bind(
            wx.EVT_BUTTON,
            on_pause_button,
            pause,
        )
        pause.SetBackgroundColour(wx.Colour(255, 255, 0))
        pause.SetToolTip(_("Pause/Resume the controller"))
        pause.SetSize(pause.GetBestSize())
        pane = (
            aui.AuiPaneInfo()
            .Caption(_("Pause"))
            .Bottom()
            .MinSize(40, 40)
            .FloatingSize(98, 98)
            .Name("pause")
            .CaptionVisible(not self.context.pane_lock)
        )
        pane.dock_proportion = 98
        pane.control = pause

        self.on_pane_add(pane)
        self.context.register("pane/pause", pane)

        # Define Home.
        home = wx.BitmapButton(self, wx.ID_ANY, icons8_home_filled_50.GetBitmap())
        # home.SetBackgroundColour((200, 225, 250))
        self.Bind(wx.EVT_BUTTON, lambda e: self.context("home\n"), home)
        pane = (
            aui.AuiPaneInfo()
            .Bottom()
            .Caption(_("Home"))
            .MinSize(40, 40)
            .FloatingSize(98, 98)
            .Name("home")
            .CaptionVisible(not self.context.pane_lock)
        )
        pane.dock_proportion = 98
        pane.control = home
        self.on_pane_add(pane)
        self.context.register("pane/home", pane)

        # Define Notes.
        from .panes.notespanel import register_panel

        register_panel(self, self.context)

        # Define Spooler.
        from .panes.spoolerpanel import register_panel

        register_panel(self, self.context)

        # Define Console.
        from .panes.consolepanel import register_panel

        register_panel(self, self.context)

        # Define Devices.
        from .panes.devicespanel import register_panel

        register_panel(self, self.context)

        # Define Camera
        if self.context.has_feature("modifier/Camera"):
            from .panes.camerapanel import register_panel

            register_panel(self, self.context)

        # AUI Manager Update.
        self._mgr.Update()

        self.default_perspective = self._mgr.SavePerspective()
        self.context.setting(str, "perspective")
        if self.context.perspective is not None:
            self._mgr.LoadPerspective(self.context.perspective)
        self.on_config_panes()

    def on_pane_reset(self, event=None):
        for pane in self._mgr.GetAllPanes():
            if pane.IsShown():
                if hasattr(pane.window, "finalize"):
                    pane.window.finalize()
        self._mgr.LoadPerspective(self.default_perspective, update=True)
        self.on_config_panes()

    def on_config_panes(self):
        for pane in self._mgr.GetAllPanes():
            if pane.IsShown():
                if hasattr(pane.window, "initialize"):
                    pane.window.initialize()
            else:
                if hasattr(pane.window, "noninitialize"):
                    pane.window.noninitialize()
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
        if len(pane.name):
            if not pane.IsShown():
                pane.Show()
                pane.CaptionVisible(not self.context.pane_lock)
                if hasattr(pane.window, "initialize"):
                    pane.window.initialize()
                    wx.CallAfter(self.on_pane_changed, None)
                self._mgr.Update()
            return
        self._mgr.AddPane(
            paneinfo.control,
            paneinfo,
        )

    def on_pane_active(self, event):
        pane = event.GetPane()
        if hasattr(pane.window, "active"):
            pane.window.active()

    def on_pane_closed(self, event):
        pane = event.GetPane()
        if pane.IsShown():
            if hasattr(pane.window, "finalize"):
                pane.window.finalize()
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

    def __kernel_initialize(self, context):
        context.gui = self
        context.setting(int, "draw_mode", 0)
        context.setting(float, "units_convert", MILS_IN_MM)
        context.setting(str, "units_name", "mm")
        context.setting(int, "units_marks", 10)
        context.setting(int, "units_index", 0)
        context.setting(bool, "mouse_zoom_invert", False)
        context.setting(bool, "print_shutdown", False)

        context.listen("units", self.space_changed)

        context.listen("emphasized", self.on_emphasized_elements_changed)
        context.listen("modified", self.on_element_modified)
        context.listen("altered", self.on_element_modified)
        context.listen("export-image", self.on_export_signal)
        context.listen("background", self.on_background_signal)
        context.listen("rebuild_tree", self.on_rebuild_tree_signal)
        context.listen("refresh_tree", self.request_refresh)
        context.listen("refresh_scene", self.on_refresh_scene)
        context.listen("element_property_update", self.on_element_update)
        context.listen("element_property_reload", self.on_force_element_update)

        context.listen("device;noactive", self.on_device_noactive)
        context.listen("pipe;failing", self.on_usb_error)
        context.listen("pipe;running", self.on_usb_running)
        context.listen("pipe;usb_status", self.on_usb_state_text)
        context.listen("pipe;thread", self.on_pipe_state)
        context.listen("spooler;thread", self.on_spooler_state)
        context.listen("driver;mode", self.on_driver_mode)
        context.listen("bed_size", self.bed_changed)
        context.listen("warning", self.on_warning_signal)
        bed_dim = context.root
        bed_dim.setting(int, "bed_width", 310)  # Default Value
        bed_dim.setting(int, "bed_height", 210)  # Default Value

        context.listen("active", self.on_active_change)

        self.widget_scene.add_scenewidget(
            SelectionWidget(self.widget_scene, self.shadow_tree)
        )
        self.tool_container = ToolContainer(self.widget_scene)
        self.widget_scene.add_scenewidget(self.tool_container)
        self.widget_scene.add_scenewidget(RectSelectWidget(self.widget_scene))
        self.laserpath_widget = LaserPathWidget(self.widget_scene)
        self.widget_scene.add_scenewidget(self.laserpath_widget)
        self.widget_scene.add_scenewidget(
            ElementsWidget(self.widget_scene, self.shadow_tree, self.renderer)
        )
        self.widget_scene.add_scenewidget(GridWidget(self.widget_scene))
        self.widget_scene.add_interfacewidget(GuideWidget(self.widget_scene))
        self.widget_scene.add_interfacewidget(ReticleWidget(self.widget_scene))

        @context.console_command("dialog_transform", hidden=True)
        def transform(**kwargs):
            self.open_transform_dialog()

        @context.console_command("dialog_flip", hidden=True)
        def flip(**kwargs):
            self.open_flip_dialog()

        @context.console_command("dialog_path", hidden=True)
        def path(**kwargs):
            self.open_path_dialog()

        @context.console_command("dialog_fill", hidden=True)
        def fill(**kwargs):
            self.open_fill_dialog()

        @context.console_command("dialog_stroke", hidden=True)
        def stroke(**kwargs):
            self.open_stroke_dialog()

        @context.console_command("dialog_fps", hidden=True)
        def fps(**kwargs):
            self.open_fps_dialog()

        @context.console_command("dialog_gear", hidden=True)
        def gear(**kwargs):
            self.open_speedcode_gear_dialog()

        @context.console_command("laserpath_clear", hidden=True)
        def gear(**kwargs):
            self.laserpath_widget.clear_laserpath()

        context.register("control/Transform", self.open_transform_dialog)
        context.register("control/Flip", self.open_flip_dialog)
        context.register("control/Path", self.open_path_dialog)
        context.register("control/Fill", self.open_fill_dialog)
        context.register("control/Stroke", self.open_stroke_dialog)
        context.register("control/FPS", self.open_fps_dialog)
        context.register(
            "control/Speedcode-Gear-Force", self.open_speedcode_gear_dialog
        )
        context.register("control/Jog Transition Test", self.run_jog_transition_test)
        context.register(
            "control/Jog Transition Switch Test", self.run_jog_transition_switch_test
        )
        context.register(
            "control/Jog Transition Finish Test", self.run_jog_transition_finish_test
        )
        context.register("control/Home and Dot", self.run_home_and_dot_test)

        def test_crash_in_thread():
            def foo():
                a = 1 / 0

            context.threaded(foo)

        context.register("control/Crash Thread", test_crash_in_thread)
        context.register(
            "control/Clear Laserpath", self.laserpath_widget.clear_laserpath
        )
        context.register("control/egv export", self.egv_export)
        context.register("control/egv import", self.egv_import)

        @context.console_command("theme", help=_("Theming information and assignments"))
        def theme(command, channel, _, **kwargs):
            channel(str(wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)))

        @context.console_command("rotaryview", help=_("Rotary View of Scene"))
        def toggle_rotary_view(*args, **kwargs):
            self.toggle_rotary_view()

        @context.console_command(
            "rotaryscale", help=_("Rotary Scale selected elements")
        )
        def apply_rotary_scale(*args, **kwargs):
            self.apply_rotary_scale()

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
        self.populate_recent_menu()

        bed_dim = context.root
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)
        bbox = (0, 0, bed_dim.bed_width * MILS_IN_MM, bed_dim.bed_height * MILS_IN_MM)
        self.widget_scene.widget_root.focus_viewport_scene(
            bbox, self.scene.ClientSize, 0.1
        )

        def interrupt_popup():
            dlg = wx.MessageDialog(
                None,
                _("Spooling Interrupted. Press OK to Continue."),
                _("Interrupt"),
                wx.OK,
            )
            dlg.ShowModal()
            dlg.Destroy()

        context.register("function/interrupt", interrupt_popup)

        def interrupt():
            yield COMMAND_WAIT_FINISH
            yield COMMAND_FUNCTION, context.registered["function/interrupt"]

        context.register("plan/interrupt", interrupt)

        # Registers the render-op make_raster. This is used to do cut planning.
        context.register("render-op/make_raster", self.renderer.make_raster)
        # After main window is launched run_later actually works.

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

    def __set_tree(self):
        self.shadow_tree = ShadowTree(self.context, self, self.context.elements._tree)
        self.Bind(
            wx.EVT_TREE_BEGIN_DRAG, self.shadow_tree.on_drag_begin_handler, self.wxtree
        )
        self.Bind(
            wx.EVT_TREE_END_DRAG, self.shadow_tree.on_drag_end_handler, self.wxtree
        )
        self.Bind(
            wx.EVT_TREE_ITEM_ACTIVATED, self.shadow_tree.on_item_activated, self.wxtree
        )
        self.Bind(
            wx.EVT_TREE_SEL_CHANGED,
            self.shadow_tree.on_item_selection_changed,
            self.wxtree,
        )
        self.Bind(
            wx.EVT_TREE_ITEM_RIGHT_CLICK,
            self.shadow_tree.on_item_right_click,
            self.wxtree,
        )

    def ribbon_bar_toggle(self, event=None):
        pane = self._mgr.GetPane("ribbon")
        if pane.name == "ribbon":
            self.ribbonbar_caption_visible = not self.ribbonbar_caption_visible
            pane.CaptionVisible(self.ribbonbar_caption_visible)
            self._mgr.Update()

    def __set_ribbonbar(self):
        self.ribbonbar_caption_visible = False

        if self.is_dark:
            provider = self._ribbon.GetArtProvider()
            _update_ribbon_artprovider_for_dark_mode(provider)
        self.ribbon_position_aspect_ratio = True
        self.ribbon_position_ignore_update = False
        self.ribbon_position_x = 0.0
        self.ribbon_position_y = 0.0
        self.ribbon_position_h = 0.0
        self.ribbon_position_w = 0.0
        self.ribbon_position_units = 0
        self.ribbon_position_name = None

        home = RB.RibbonPage(
            self._ribbon,
            wx.ID_ANY,
            _("Home"),
            icons8_opened_folder_50.GetBitmap(),
        )
        self.Bind(
            RB.EVT_RIBBONBAR_HELP_CLICK,
            lambda e: self.context("webhelp help\n"),
        )
        self.Bind(RB.EVT_RIBBONBAR_TOGGLED, self.ribbon_bar_toggle)

        # ==========
        # PROJECT PANEL
        # ==========

        self.toolbar_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            _("" if self.is_dark else "Project"),
            style=wx.ribbon.RIBBON_PANEL_NO_AUTO_MINIMISE | RB.RIBBON_PANEL_FLEXIBLE,
        )

        toolbar = RB.RibbonButtonBar(self.toolbar_panel)
        self.toolbar_button_bar = toolbar
        toolbar.AddButton(ID_OPEN, _("Open"), icons8_opened_folder_50.GetBitmap(), "")
        toolbar.AddButton(ID_SAVE, _("Save"), icons8_save_50.GetBitmap(), "")
        toolbar.AddButton(
            ID_JOB, _("Execute Job"), icons8_laser_beam_52.GetBitmap(), ""
        )
        toolbar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda v: self.context("window toggle ExecuteJob 0\n"),
            id=ID_JOB,
        )
        toolbar.AddButton(
            ID_SIM, _("Simulate"), icons8_laser_beam_hazard2_50.GetBitmap(), ""
        )

        toolbar.AddButton(
            ID_RASTER, _("RasterWizard"), icons8_fantasy_50.GetBitmap(), ""
        )
        toolbar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda v: self.context("window toggle RasterWizard\n"),
            id=ID_RASTER,
        )

        toolbar.AddButton(ID_NOTES, _("Notes"), icons8_comments_50.GetBitmap(), "")
        toolbar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda v: self.context("window toggle Notes\n"),
            id=ID_NOTES,
        )
        toolbar.AddButton(ID_CONSOLE, _("Console"), icons8_console_50.GetBitmap(), "")
        toolbar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda v: self.context("window toggle Console\n"),
            id=ID_CONSOLE,
        )

        def open_simulator(v=None):
            with wx.BusyInfo(_("Preparing simulation...")):
                self.context(
                    "plan0 copy preprocess validate blob preopt optimize\nwindow toggle Simulation 0\n"
                ),

        toolbar.Bind(RB.EVT_RIBBONBUTTONBAR_CLICKED, self.on_click_open, id=ID_OPEN)
        toolbar.Bind(RB.EVT_RIBBONBUTTONBAR_CLICKED, self.on_click_save, id=ID_SAVE)
        toolbar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            open_simulator,
            id=ID_SIM,
        )
        # ==========
        # CONTROL PANEL
        # ==========

        self.windows_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            _("" if self.is_dark else "Control"),
            icons8_opened_folder_50.GetBitmap(),
            style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        )
        button_bar = RB.RibbonButtonBar(self.windows_panel)
        self.window_button_bar = button_bar
        # So Navigation, Camera, Spooler, Controller, Terminal in one group,
        # Settings, Keymap, Devices, Preferences, Rotary, USB in another.
        # Raster Wizard and Notes should IMO be in the Main Group.
        button_bar.AddButton(ID_NAV, _("Navigation"), icons8_move_50.GetBitmap(), "")
        button_bar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda v: self.context("window toggle Navigation\n"),
            id=ID_NAV,
        )
        if self.context.has_feature("modifier/Camera"):
            button_bar.AddHybridButton(
                ID_CAMERA, _("Camera"), icons8_camera_50.GetBitmap(), ""
            )
            button_bar.Bind(
                RB.EVT_RIBBONBUTTONBAR_CLICKED, self.on_camera_click, id=ID_CAMERA
            )
            button_bar.Bind(
                RB.EVT_RIBBONBUTTONBAR_DROPDOWN_CLICKED,
                self.on_camera_dropdown,
                id=ID_CAMERA,
            )
            self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA1)
            self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA2)
            self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA3)
            self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA4)
            self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA5)

        button_bar.AddButton(ID_SPOOLER, _("Spooler"), icons8_route_50.GetBitmap(), "")
        button_bar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda v: self.context("window toggle JobSpooler\n"),
            id=ID_SPOOLER,
        )
        button_bar.AddButton(
            ID_CONTROLLER, _("Controller"), icons8_connected_50.GetBitmap(), ""
        )
        button_bar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda v: self.context("window toggle -o Controller\n"),
            id=ID_CONTROLLER,
        )
        button_bar.AddToggleButton(
            ID_PAUSE, _("Pause"), icons8_pause_50.GetBitmap(), ""
        )
        button_bar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED, self.on_click_pause, id=ID_PAUSE
        )
        button_bar.AddButton(
            ID_STOP, _("Stop"), icons8_emergency_stop_button_50.GetBitmap(), ""
        )
        button_bar.Bind(RB.EVT_RIBBONBUTTONBAR_CLICKED, self.on_click_stop, id=ID_STOP)

        # ==========
        # DEVICES PANEL
        # ==========
        # self.devices_panel = RB.RibbonPanel(
        #     home,
        #     wx.ID_ANY,
        #     _("" if self.is_dark else "Devices"),
        #     icons8_opened_folder_50.GetBitmap(),
        #     # style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        # )
        # button_bar = RB.RibbonButtonBar(self.devices_panel)
        # self.devices_button_bar = button_bar

        # ==========
        # SETTINGS PANEL
        # ==========
        self.settings_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            _("" if self.is_dark else "Preferences"),
            icons8_opened_folder_50.GetBitmap(),
            style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        )
        button_bar = RB.RibbonButtonBar(self.settings_panel)
        self.setting_button_bar = button_bar

        button_bar.AddButton(
            ID_DEVICES, _("Devices"), icons8_manager_50.GetBitmap(), ""
        )
        button_bar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda v: self.context("window toggle DeviceManager\n"),
            id=ID_DEVICES,
        )

        button_bar.AddButton(
            ID_CONFIGURATION,
            _("Config"),
            icons8_computer_support_50.GetBitmap(),
            "",
        )
        button_bar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda v: self.context("window toggle -d Preferences\n"),
            id=ID_CONFIGURATION,
        )

        button_bar.AddButton(
            ID_SETTING, _("Settings"), icons8_administrative_tools_50.GetBitmap(), ""
        )
        button_bar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda v: self.context("window toggle Settings\n"),
            id=ID_SETTING,
        )

        button_bar.AddButton(ID_KEYMAP, _("Keymap"), icons8_keyboard_50.GetBitmap(), "")
        button_bar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda v: self.context("window toggle Keymap\n"),
            id=ID_KEYMAP,
        )
        button_bar.AddButton(ID_ROTARY, _("Rotary"), icons8_roll_50.GetBitmap(), "")
        button_bar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda v: self.context("window -p rotary/1 toggle Rotary\n"),
            id=ID_ROTARY,
        )

        # ==========
        # TOOLBOX PAGE
        # ==========
        # home = RB.RibbonPage(
        #     self._ribbon,
        #     wx.ID_ANY,
        #     _("Toolbox"),
        #     icons8_opened_folder_50.GetBitmap(),
        # )
        #
        # align_panel = RB.RibbonPanel(
        #     home,
        #     wx.ID_ANY,
        #     _("Align"),
        #     icons8_opened_folder_50.GetBitmap(),
        #     style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        # )
        # align = RB.RibbonButtonBar(align_panel)
        # align.AddButton(
        #     ID_ALIGN_LEFT, _("Align Left"), icons8_align_left_50.GetBitmap(), ""
        # )
        # align.AddButton(
        #     ID_ALIGN_RIGHT, _("Align Right"), icons8_align_right_50.GetBitmap(), ""
        # )
        # align.AddButton(
        #     ID_ALIGN_TOP, _("Align Top"), icons8_align_top_50.GetBitmap(), ""
        # )
        # align.AddButton(
        #     ID_ALIGN_BOTTOM, _("Align Bottom"), icons8_align_bottom_50.GetBitmap(), ""
        # )
        # align.AddButton(
        #     ID_ALIGN_CENTER, _("Align Center"), icons_centerize.GetBitmap(), ""
        # )
        # align.AddButton(
        #     ID_ALIGN_SPACE_V, _("Space Vertical"), icons_evenspace_vert.GetBitmap(), ""
        # )
        # align.AddButton(
        #     ID_ALIGN_SPACE_H,
        #     _("Space Horizontal"),
        #     icons_evenspace_horiz.GetBitmap(),
        #     "",
        # )
        #
        # # TODO: Fix and reenable.
        # align.EnableButton(ID_ALIGN_LEFT, False)
        # align.EnableButton(ID_ALIGN_RIGHT, False)
        # align.EnableButton(ID_ALIGN_TOP, False)
        # align.EnableButton(ID_ALIGN_BOTTOM, False)
        # align.EnableButton(ID_ALIGN_CENTER, False)
        # align.EnableButton(ID_ALIGN_SPACE_V, False)
        # align.EnableButton(ID_ALIGN_SPACE_H, False)
        #
        # flip_panel = RB.RibbonPanel(
        #     home,
        #     wx.ID_ANY,
        #     _("Flip"),
        #     icons8_opened_folder_50.GetBitmap(),
        #     style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        # )
        # flip = RB.RibbonButtonBar(flip_panel)
        #
        # flip.AddButton(
        #     ID_FLIP_HORIZONTAL,
        #     _("Flip Horizontal"),
        #     icons8_flip_horizontal_50.GetBitmap(),
        #     "",
        # )
        # flip.AddButton(
        #     ID_FLIP_VERTICAL,
        #     _("Flip Vertical"),
        #     icons8_flip_vertical_50.GetBitmap(),
        #     "",
        # )
        #
        # group_panel = RB.RibbonPanel(
        #     home,
        #     wx.ID_ANY,
        #     _("Group"),
        #     icons8_opened_folder_50.GetBitmap(),
        #     style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        # )
        #
        # group = RB.RibbonButtonBar(group_panel)
        # group.AddButton(ID_GROUP, _("Group"), icons8_group_objects_50.GetBitmap(), "")
        # group.AddButton(
        #     ID_UNGROUP, _("Ungroup"), icons8_ungroup_objects_50.GetBitmap(), ""
        # )
        #
        # # TODO: Fix and Reenable.
        # group.EnableButton(ID_GROUP, False)
        # group.EnableButton(ID_UNGROUP, False)
        #
        # tool_panel = RB.RibbonPanel(
        #     home,
        #     wx.ID_ANY,
        #     _("Tools"),
        #     icons8_opened_folder_50.GetBitmap(),
        #     style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        # )
        # tool = RB.RibbonButtonBar(tool_panel)
        # tool.AddButton(
        #     ID_TOOL_POSITION, _("Set Position"), icons8_place_marker_50.GetBitmap(), ""
        # )
        # tool.AddButton(ID_TOOL_OVAL, _("Oval"), icons8_oval_50.GetBitmap(), "")
        # tool.AddButton(ID_TOOL_CIRCLE, _("Circle"), icons8_circle_50.GetBitmap(), "")
        # tool.AddButton(ID_TOOL_POLYGON, _("Polygon"), icons8_polygon_50.GetBitmap(), "")
        # tool.AddButton(
        #     ID_TOOL_POLYLINE, _("Polyline"), icons8_polyline_50.GetBitmap(), ""
        # )
        # tool.AddButton(
        #     ID_TOOL_RECT, _("Rectangle"), icons8_rectangular_50.GetBitmap(), ""
        # )
        # tool.AddButton(ID_TOOL_TEXT, _("Text"), icons8_type_50.GetBitmap(), "")
        #
        # # TODO: Fix and Reenable
        # tool.EnableButton(ID_TOOL_POSITION, False)
        # tool.EnableButton(ID_TOOL_OVAL, False)
        # tool.EnableButton(ID_TOOL_CIRCLE, False)
        # tool.EnableButton(ID_TOOL_POLYLINE, False)
        # tool.EnableButton(ID_TOOL_POLYGON, False)
        # tool.EnableButton(ID_TOOL_RECT, False)
        # tool.EnableButton(ID_TOOL_TEXT, False)
        #
        #
        # align.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("align left\n"),
        #     id=ID_ALIGN_LEFT,
        # )
        # align.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("align right\n"),
        #     id=ID_ALIGN_RIGHT,
        # )
        # align.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("align top\n"),
        #     id=ID_ALIGN_TOP,
        # )
        # align.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("align bottom\n"),
        #     id=ID_ALIGN_BOTTOM,
        # )
        # align.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("align center\n"),
        #     id=ID_ALIGN_CENTER,
        # )
        # align.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("align spacev\n"),
        #     id=ID_ALIGN_SPACE_V,
        # )
        # align.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("align spaceh\n"),
        #     id=ID_ALIGN_SPACE_H,
        # )
        # flip.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("scale 1 -1\n"),
        #     id=ID_FLIP_HORIZONTAL,
        # )
        # flip.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("scale -1 1\n"),
        #     id=ID_FLIP_VERTICAL,
        # )
        # group.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("group\n"),
        #     id=ID_GROUP,
        # )
        # group.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("ungroup\n"),
        #     id=ID_UNGROUP,
        # )
        # tool.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("tool position\n"),
        #     id=ID_TOOL_POSITION,
        # )
        # tool.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("tool oval\n"),
        #     id=ID_TOOL_OVAL,
        # )
        # tool.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("tool circle\n"),
        #     id=ID_TOOL_CIRCLE,
        # )
        # tool.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("tool polygon\n"),
        #     id=ID_TOOL_POLYGON,
        # )
        # tool.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("tool polyline\n"),
        #     id=ID_TOOL_POLYLINE,
        # )
        # tool.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("tool rect\n"),
        #     id=ID_TOOL_RECT,
        # )
        # tool.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_CLICKED,
        #     lambda e: self.context("tool text\n"),
        #     id=ID_TOOL_TEXT,
        # )
        # ==========
        # POSITION PAGE
        # ==========
        # home = RB.RibbonPage(
        #     self._ribbon,
        #     wx.ID_ANY,
        #     _("Position"),
        #     icons8_opened_folder_50.GetBitmap(),
        # )
        # position_panel = RB.RibbonPanel(
        #     home,
        #     wx.ID_ANY,
        #     _("Position"),
        #     icons8_opened_folder_50.GetBitmap(),
        #     style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        # )
        #
        # self.text_x = wx.TextCtrl(
        #     position_panel, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        # )
        # self.text_y = wx.TextCtrl(
        #     position_panel, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        # )
        # self.text_w = wx.TextCtrl(
        #     position_panel, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        # )
        # self.button_aspect_ratio = wx.BitmapButton(
        #     position_panel, wx.ID_ANY, icons8_lock_50.GetBitmap()
        # )
        # self.text_h = wx.TextCtrl(
        #     position_panel, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        # )
        # self.combo_box_units = wx.ComboBox(
        #     position_panel,
        #     wx.ID_ANY,
        #     choices=["mm", "cm", "inch", "mil", "%"],
        #     style=wx.CB_DROPDOWN | wx.CB_READONLY,
        # )
        #
        # self.button_aspect_ratio.SetSize(self.button_aspect_ratio.GetBestSize())
        # self.combo_box_units.SetSelection(0)
        #
        # sizer_panel = wx.BoxSizer(wx.HORIZONTAL)
        # sizer_units = wx.StaticBoxSizer(
        #     wx.StaticBox(position_panel, wx.ID_ANY, "Units:"), wx.HORIZONTAL
        # )
        # sizer_h = wx.StaticBoxSizer(
        #     wx.StaticBox(position_panel, wx.ID_ANY, "H:"), wx.HORIZONTAL
        # )
        # sizer_w = wx.StaticBoxSizer(
        #     wx.StaticBox(position_panel, wx.ID_ANY, "W:"), wx.HORIZONTAL
        # )
        # sizer_y = wx.StaticBoxSizer(
        #     wx.StaticBox(position_panel, wx.ID_ANY, "Y:"), wx.HORIZONTAL
        # )
        # sizer_x = wx.StaticBoxSizer(
        #     wx.StaticBox(position_panel, wx.ID_ANY, "X:"), wx.HORIZONTAL
        # )
        # sizer_x.Add(self.text_x, 1, 0, 0)
        # sizer_panel.Add(sizer_x, 0, 0, 0)
        # sizer_y.Add(self.text_y, 1, 0, 0)
        # sizer_panel.Add(sizer_y, 0, 0, 0)
        # sizer_w.Add(self.text_w, 1, 0, 0)
        # sizer_panel.Add(sizer_w, 0, 0, 0)
        # sizer_panel.Add(self.button_aspect_ratio, 0, 0, 0)
        # sizer_h.Add(self.text_h, 1, 0, 0)
        # sizer_panel.Add(sizer_h, 0, 0, 0)
        # sizer_units.Add(self.combo_box_units, 0, 0, 0)
        # sizer_panel.Add(sizer_units, 0, 0, 0)
        # position_panel.SetSizer(sizer_panel)
        self._ribbon.Realize()
        #
        # self.Bind(wx.EVT_TEXT, self.on_text_x, self.text_x)
        # self.Bind(wx.EVT_TEXT_ENTER, self.on_text_pos_enter, self.text_x)
        # self.Bind(wx.EVT_TEXT, self.on_text_y, self.text_y)
        # self.Bind(wx.EVT_TEXT_ENTER, self.on_text_pos_enter, self.text_y)
        # self.Bind(wx.EVT_TEXT, self.on_text_w, self.text_w)
        # self.Bind(wx.EVT_TEXT_ENTER, self.on_text_dim_enter, self.text_w)
        # self.Bind(wx.EVT_BUTTON, self.on_button_aspect_ratio, self.button_aspect_ratio)
        # self.Bind(wx.EVT_TEXT, self.on_text_h, self.text_h)
        # self.Bind(wx.EVT_TEXT_ENTER, self.on_text_dim_enter, self.text_h)
        # self.Bind(wx.EVT_COMBOBOX, self.on_combo_box_units, self.combo_box_units)
        #
        # self.context.setting(int, "units_index", 0)
        # self.ribbon_position_units = self.context.units_index
        # self.update_ribbon_position()

    def run_later(self, command, *args):
        if wx.IsMainThread():
            command(*args)
        else:
            wx.CallAfter(command, *args)

    def on_camera_dropdown(self, event):
        menu = wx.Menu()
        menu.Append(ID_CAMERA1, _("Camera %d") % 1)
        menu.Append(ID_CAMERA2, _("Camera %d") % 2)
        menu.Append(ID_CAMERA3, _("Camera %d") % 3)
        menu.Append(ID_CAMERA4, _("Camera %d") % 4)
        menu.Append(ID_CAMERA5, _("Camera %d") % 5)
        event.PopupMenu(menu)

    def on_camera_click(self, event):
        eid = event.GetId()
        self.context.setting(int, "camera_default", 1)
        if eid == ID_CAMERA1:
            self.context.camera_default = 1
        elif eid == ID_CAMERA2:
            self.context.camera_default = 2
        elif eid == ID_CAMERA3:
            self.context.camera_default = 3
        elif eid == ID_CAMERA4:
            self.context.camera_default = 4
        elif eid == ID_CAMERA5:
            self.context.camera_default = 5

        v = self.context.camera_default
        self.context("camwin %d\n" % v)

    def __set_menubar(self):
        self.file_menu = wx.Menu()
        # ==========
        # FILE MENU
        # ==========

        self.file_menu.Append(wx.ID_NEW, _("&New\tCtrl-N"), "")
        self.file_menu.Append(wx.ID_OPEN, _("&Open Project\tCtrl-O"), "")
        self.recent_file_menu = wx.Menu()
        self.file_menu.AppendSubMenu(self.recent_file_menu, _("&Recent"))
        self.file_menu.Append(ID_MENU_IMPORT, _("&Import File"), "")
        self.file_menu.AppendSeparator()
        self.file_menu.Append(wx.ID_SAVE, _("&Save\tCtrl-S"), "")
        self.file_menu.Append(wx.ID_SAVEAS, _("Save &As\tCtrl-Shift-S"), "")
        self.file_menu.AppendSeparator()

        self.file_menu.Append(wx.ID_EXIT, _("E&xit"), "")
        self.main_menubar.Append(self.file_menu, _("File"))

        # ==========
        # VIEW MENU
        # ==========
        self.view_menu = wx.Menu()

        self.view_menu.Append(ID_MENU_ZOOM_OUT, _("Zoom &Out\tCtrl--"), "")
        self.view_menu.Append(ID_MENU_ZOOM_IN, _("Zoom &In\tCtrl-+"), "")
        self.view_menu.Append(ID_MENU_ZOOM_SIZE, _("Zoom To &Size"), "")
        self.view_menu.AppendSeparator()

        self.view_menu.Append(ID_MENU_HIDE_GRID, _("Hide Grid"), "", wx.ITEM_CHECK)
        self.view_menu.Append(
            ID_MENU_HIDE_BACKGROUND, _("Hide Background"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(ID_MENU_HIDE_GUIDES, _("Hide Guides"), "", wx.ITEM_CHECK)
        self.view_menu.Append(ID_MENU_HIDE_PATH, _("Hide Paths"), "", wx.ITEM_CHECK)
        self.view_menu.Append(ID_MENU_HIDE_IMAGE, _("Hide Images"), "", wx.ITEM_CHECK)
        self.view_menu.Append(ID_MENU_HIDE_TEXT, _("Hide Text"), "", wx.ITEM_CHECK)
        self.view_menu.Append(ID_MENU_HIDE_FILLS, _("Hide Fills"), "", wx.ITEM_CHECK)
        self.view_menu.Append(
            ID_MENU_HIDE_STROKES, _("Hide Strokes"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_HIDE_LINEWIDTH, _("No Stroke-Width Render"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_HIDE_LASERPATH, _("Hide Laserpath"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_HIDE_RETICLE, _("Hide Reticle"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_HIDE_SELECTION, _("Hide Selection"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(ID_MENU_HIDE_ICONS, _("Hide Icons"), "", wx.ITEM_CHECK)
        self.view_menu.Append(ID_MENU_HIDE_TREE, _("Hide Tree"), "", wx.ITEM_CHECK)
        self.view_menu.Append(
            ID_MENU_PREVENT_CACHING, _("Do Not Cache Image"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_PREVENT_ALPHABLACK,
            _("Do Not Alpha/Black Images"),
            "",
            wx.ITEM_CHECK,
        )
        self.view_menu.Append(
            ID_MENU_SCREEN_REFRESH, _("Do Not Refresh"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_SCREEN_ANIMATE, _("Do Not Animate"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(ID_MENU_SCREEN_INVERT, _("Invert"), "", wx.ITEM_CHECK)
        self.view_menu.Append(ID_MENU_SCREEN_FLIPXY, _("Flip XY"), "", wx.ITEM_CHECK)

        self.main_menubar.Append(self.view_menu, _("View"))

        # ==========
        # PANE MENU
        # ==========

        self.panes_menu = wx.Menu()

        def toggle_pane(pane_toggle):
            def toggle(event=None):
                pane_obj = self._mgr.GetPane(pane_toggle)
                if pane_obj.IsShown():
                    if hasattr(pane_obj.window, "finalize"):
                        pane_obj.window.finalize()
                    pane_obj.Hide()
                    self._mgr.Update()
                    return
                pane_init = self.context.registered["pane/%s" % pane_toggle]
                self.on_pane_add(pane_init)

            return toggle

        submenus = {}
        for p in self.context.match("pane/.*"):
            pane = self.context.registered[p]
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
                pane_name = p.split("/")[-1]

            try:
                pane_caption = pane.caption
            except AttributeError:
                pane_caption = pane_name[0].upper() + pane_name[1:] + "."

            id_new = wx.NewId()
            menu_item = menu_context.Append(id_new, pane_caption, "", wx.ITEM_CHECK)
            self.Bind(
                wx.EVT_MENU,
                toggle_pane(pane_name),
                id=id_new,
            )
            pane = self._mgr.GetPane(pane_name)
            try:
                menu_item.Check(pane.IsShown())
                pane.window.check = menu_item.Check
            except AttributeError:
                pass

        self.panes_menu.AppendSeparator()
        item = self.main_menubar.panereset = self.panes_menu.Append(
            ID_MENU_PANE_LOCK, _("Lock Panes"), "", wx.ITEM_CHECK
        )
        item.Check(self.context.pane_lock)
        self.panes_menu.AppendSeparator()
        self.main_menubar.panereset = self.panes_menu.Append(
            ID_MENU_PANE_RESET, _("Reset Panes"), ""
        )
        self.main_menubar.Append(self.panes_menu, _("Panes"))

        # ==========
        # TOOL MENU
        # ==========

        self.window_menu = wx.Menu()

        self.window_menu.executejob = self.window_menu.Append(
            ID_MENU_JOB, _("E&xecute Job"), ""
        )
        self.window_menu.simulate = self.window_menu.Append(
            ID_MENU_SIMULATE, _("&Simulate"), ""
        )
        self.window_menu.rasterwizard = self.window_menu.Append(
            ID_MENU_RASTER_WIZARD, _("&RasterWizard"), ""
        )
        self.window_menu.notes = self.window_menu.Append(ID_MENU_NOTES, _("&Notes"), "")
        self.window_menu.console = self.window_menu.Append(
            ID_MENU_CONSOLE, _("&Console"), ""
        )

        self.window_menu.navigation = self.window_menu.Append(
            ID_MENU_NAVIGATION, _("N&avigation"), ""
        )
        if self.context.has_feature("modifier/Camera"):
            self.window_menu.camera = self.window_menu.Append(
                ID_MENU_CAMERA, _("C&amera"), ""
            )
        self.window_menu.jobspooler = self.window_menu.Append(
            ID_MENU_SPOOLER, _("S&pooler"), ""
        )

        self.window_menu.controller = self.window_menu.Append(
            ID_MENU_CONTROLLER, _("C&ontroller"), ""
        )
        self.window_menu.devices = self.window_menu.Append(
            ID_MENU_DEVICE_MANAGER, _("&Devices"), ""
        )
        self.window_menu.preferences = self.window_menu.Append(
            wx.ID_PREFERENCES, _("Confi&g"), ""
        )
        self.window_menu.settings = self.window_menu.Append(
            ID_MENU_SETTINGS, _("Se&ttings"), ""
        )

        self.window_menu.keymap = self.window_menu.Append(
            ID_MENU_KEYMAP, _("&Keymap"), ""
        )
        self.window_menu.rotary = self.window_menu.Append(
            ID_MENU_ROTARY, _("Rotar&y"), ""
        )
        self.window_menu.usb = self.window_menu.Append(ID_MENU_USB, _("&USB"), "")

        self.window_menu.AppendSeparator()
        self.window_menu.windowreset = self.window_menu.Append(
            ID_MENU_WINDOW_RESET, _("Reset Windows"), ""
        )

        self.main_menubar.Append(self.window_menu, _("Tools"))

        # ==========
        # OSX-ONLY WINDOW MENU
        # ==========
        from sys import platform

        if platform == "darwin":
            wt_menu = wx.Menu()
            self.main_menubar.Append(wt_menu, _("Window"))

        # ==========
        # HELP MENU
        # ==========
        self.help_menu = wx.Menu()
        self.help_menu.Append(wx.ID_HELP, _("&Help"), "")
        self.help_menu.Append(ID_BEGINNERS, _("&Beginners' Help"), "")
        self.help_menu.Append(ID_HOMEPAGE, _("&Github"), "")
        self.help_menu.Append(ID_RELEASES, _("&Releases"), "")
        self.help_menu.Append(ID_FACEBOOK, _("&Facebook"), "")
        self.help_menu.Append(ID_MAKERS_FORUM, _("&Makers Forum"), "")
        self.help_menu.Append(ID_IRC, _("&IRC"), "")
        self.help_menu.AppendSeparator()
        self.help_menu.Append(wx.ID_ABOUT, _("&About"), "")
        self.main_menubar.Append(self.help_menu, _("Help"))

        self.SetMenuBar(self.main_menubar)
        # Menu Bar end

        # ==========
        # BINDS
        # ==========
        self.Bind(wx.EVT_MENU, self.on_click_new, id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self.on_click_open, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.on_click_open, id=ID_MENU_IMPORT)
        self.Bind(wx.EVT_MENU, self.on_click_save, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.on_click_save_as, id=wx.ID_SAVEAS)

        self.Bind(wx.EVT_MENU, self.on_click_exit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.on_click_zoom_out, id=ID_MENU_ZOOM_OUT)
        self.Bind(wx.EVT_MENU, self.on_click_zoom_in, id=ID_MENU_ZOOM_IN)
        self.Bind(wx.EVT_MENU, self.on_click_zoom_size, id=ID_MENU_ZOOM_SIZE)

        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_GRID), id=ID_MENU_HIDE_GRID
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_BACKGROUND),
            id=ID_MENU_HIDE_BACKGROUND,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_LINEWIDTH),
            id=ID_MENU_HIDE_LINEWIDTH,
        )
        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_GUIDES), id=ID_MENU_HIDE_GUIDES
        )
        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_PATH), id=ID_MENU_HIDE_PATH
        )
        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_IMAGE), id=ID_MENU_HIDE_IMAGE
        )
        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_TEXT), id=ID_MENU_HIDE_TEXT
        )
        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_FILLS), id=ID_MENU_HIDE_FILLS
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_LASERPATH),
            id=ID_MENU_HIDE_LASERPATH,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_RETICLE),
            id=ID_MENU_HIDE_RETICLE,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_SELECTION),
            id=ID_MENU_HIDE_SELECTION,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_STROKES),
            id=ID_MENU_HIDE_STROKES,
        )
        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_ICONS), id=ID_MENU_HIDE_ICONS
        )
        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_TREE), id=ID_MENU_HIDE_TREE
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_CACHE),
            id=ID_MENU_PREVENT_CACHING,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_ALPHABLACK),
            id=ID_MENU_PREVENT_ALPHABLACK,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_REFRESH),
            id=ID_MENU_SCREEN_REFRESH,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_ANIMATE),
            id=ID_MENU_SCREEN_ANIMATE,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_INVERT),
            id=ID_MENU_SCREEN_INVERT,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_FLIPXY),
            id=ID_MENU_SCREEN_FLIPXY,
        )

        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle About\n"),
            id=wx.ID_ABOUT,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle Console\n"),
            id=ID_MENU_CONSOLE,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle DeviceManager\n"),
            id=ID_MENU_DEVICE_MANAGER,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle Keymap\n"),
            id=ID_MENU_KEYMAP,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle Settings\n"),
            id=ID_MENU_SETTINGS,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle Notes\n"),
            id=ID_MENU_NOTES,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle Navigation\n"),
            id=ID_MENU_NAVIGATION,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle ExecuteJob 0\n"),
            id=ID_MENU_JOB,
        )
        if self.context.has_feature("modifier/Camera"):
            self.Bind(
                wx.EVT_MENU,
                lambda v: self.context("window toggle CameraInterface\n"),
                id=ID_MENU_CAMERA,
            )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle -d Preferences\n"),
            id=wx.ID_PREFERENCES,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window -p rotary/1 open Rotary\n"),
            id=ID_MENU_ROTARY,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle -o Controller\n"),
            id=ID_MENU_CONTROLLER,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle UsbConnect\n"),
            id=ID_MENU_USB,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle JobSpooler\n"),
            id=ID_MENU_SPOOLER,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle RasterWizard\n"),
            id=ID_MENU_RASTER_WIZARD,
        )

        def open_simulator(v=None):
            with wx.BusyInfo(_("Preparing simulation...")):
                self.context(
                    "plan0 copy preprocess validate blob preopt optimize\nwindow toggle Simulation 0\n"
                ),

        self.Bind(
            wx.EVT_MENU,
            open_simulator,
            id=ID_MENU_SIMULATE,
        )

        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window reset *\n"),
            id=ID_MENU_WINDOW_RESET,
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_pane_reset,
            id=ID_MENU_PANE_RESET,
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_pane_lock,
            id=ID_MENU_PANE_LOCK,
        )
        self.Bind(wx.EVT_MENU, lambda e: self.context("webhelp help\n"), id=wx.ID_HELP)
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp beginners\n"),
            id=ID_BEGINNERS,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp main\n"),
            id=ID_HOMEPAGE,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp releases\n"),
            id=ID_RELEASES,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp makers\n"),
            id=ID_MAKERS_FORUM,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp facebook\n"),
            id=ID_FACEBOOK,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp irc\n"),
            id=ID_IRC,
        )

        self.add_language_menu()

        self.context.setting(int, "draw_mode", 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_FILLS)
        m.Check(self.context.draw_mode & DRAW_MODE_FILLS != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_GUIDES)
        m.Check(self.context.draw_mode & DRAW_MODE_GUIDES != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_BACKGROUND)
        m.Check(self.context.draw_mode & DRAW_MODE_BACKGROUND != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_LINEWIDTH)
        m.Check(self.context.draw_mode & DRAW_MODE_LINEWIDTH != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_GRID)
        m.Check(self.context.draw_mode & DRAW_MODE_GRID != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_LASERPATH)
        m.Check(self.context.draw_mode & DRAW_MODE_LASERPATH != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_RETICLE)
        m.Check(self.context.draw_mode & DRAW_MODE_RETICLE != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_SELECTION)
        m.Check(self.context.draw_mode & DRAW_MODE_SELECTION != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_STROKES)
        m.Check(self.context.draw_mode & DRAW_MODE_STROKES != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_ICONS)
        m.Check(self.context.draw_mode & DRAW_MODE_ICONS != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_TREE)
        m.Check(self.context.draw_mode & DRAW_MODE_TREE != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_PREVENT_CACHING)
        m.Check(self.context.draw_mode & DRAW_MODE_CACHE != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_PREVENT_ALPHABLACK)
        m.Check(self.context.draw_mode & DRAW_MODE_ALPHABLACK != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_SCREEN_REFRESH)
        m.Check(self.context.draw_mode & DRAW_MODE_REFRESH != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_SCREEN_ANIMATE)
        m.Check(self.context.draw_mode & DRAW_MODE_ANIMATE != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_PATH)
        m.Check(self.context.draw_mode & DRAW_MODE_PATH != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_IMAGE)
        m.Check(self.context.draw_mode & DRAW_MODE_IMAGE != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_TEXT)
        m.Check(self.context.draw_mode & DRAW_MODE_TEXT != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_SCREEN_FLIPXY)
        m.Check(self.context.draw_mode & DRAW_MODE_FLIPXY != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_SCREEN_INVERT)
        m.Check(self.context.draw_mode & DRAW_MODE_INVERT != 0)

    def add_language_menu(self):
        tl = wx.FileTranslationsLoader()
        trans = tl.GetAvailableTranslations("meerk40t")

        if trans:
            wxglade_tmp_menu = wx.Menu()
            i = 0
            for lang in supported_languages:
                language_code, language_name, language_index = lang
                m = wxglade_tmp_menu.Append(wx.ID_ANY, language_name, "", wx.ITEM_RADIO)
                if i == self.context.language:
                    m.Check(True)

                def language_update(q):
                    return lambda e: self.context.app.update_language(q)

                self.Bind(wx.EVT_MENU, language_update(i), id=m.GetId())
                if language_code not in trans and i != 0:
                    m.Enable(False)
                i += 1
            self.main_menubar.Append(wxglade_tmp_menu, _("Languages"))

    def on_active_change(self, origin, active):
        self.__set_titlebar()

    def window_close_veto(self):
        if self.usb_running:
            message = _("The device is actively sending data. Really quit?")
            answer = wx.MessageBox(
                message, _("Currently Sending Data..."), wx.YES_NO | wx.CANCEL, None
            )
            return answer != wx.YES

    def window_close(self):
        context = self.context

        context.perspective = self._mgr.SavePerspective()
        self._mgr.UnInit()

        if context.print_shutdown:
            context.channel("shutdown").watch(print)

        self.context.close("module/Scene")

        context.unlisten("emphasized", self.on_emphasized_elements_changed)
        context.unlisten("modified", self.on_element_modified)
        context.unlisten("altered", self.on_element_modified)

        context.unlisten("units", self.space_changed)

        context.unlisten("export-image", self.on_export_signal)
        context.unlisten("background", self.on_background_signal)
        context.unlisten("rebuild_tree", self.on_rebuild_tree_signal)
        context.unlisten("refresh_scene", self.on_refresh_scene)
        context.unlisten("refresh_tree", self.request_refresh)
        context.unlisten("element_property_update", self.on_element_update)
        context.unlisten("element_property_reload", self.on_force_element_update)

        context.unlisten("device;noactive", self.on_device_noactive)
        context.unlisten("pipe;failing", self.on_usb_error)
        context.unlisten("pipe;running", self.on_usb_running)
        context.unlisten("pipe;usb_status", self.on_usb_state_text)
        context.unlisten("pipe;thread", self.on_pipe_state)
        context.unlisten("spooler;thread", self.on_spooler_state)
        context.unlisten("driver;mode", self.on_driver_mode)
        context.unlisten("bed_size", self.bed_changed)
        context.unlisten("warning", self.on_warning_signal)

        context.unlisten("active", self.on_active_change)

        self.context("quit\n")

    def on_element_update(self, origin, *args):
        """
        Called by 'element_property_update' when the properties of an element are changed.

        :param origin: the path of the originating signal
        :param args:
        :return:
        """
        if self.shadow_tree is not None:
            self.shadow_tree.on_element_update(*args)

    def on_force_element_update(self, origin, *args):
        """
        Called by 'element_property_reload' when the properties of an element are changed.

        :param origin: the path of the originating signal
        :param args:
        :return:
        """
        if self.shadow_tree is not None:
            self.shadow_tree.on_force_element_update(*args)

    def on_rebuild_tree_request(self, *args):
        """
        Called by various functions, sends a rebuild_tree signal.
        This is to prevent multiple events from overtaxing the rebuild.

        :param args:
        :return:
        """
        self.context.signal("rebuild_tree")

    def on_refresh_tree_signal(self, *args):
        self.request_refresh()

    def on_rebuild_tree_signal(self, origin, *args):
        """
        Called by 'rebuild_tree' signal. To refresh tree directly

        :param origin: the path of the originating signal
        :param args:
        :return:
        """
        if self.context.draw_mode & DRAW_MODE_TREE != 0:
            self.wxtree.Hide()
            return
        else:
            self.wxtree.Show()
        self.shadow_tree.rebuild_tree()
        self.request_refresh()

    def on_refresh_scene(self, origin, *args):
        """
        Called by 'refresh_scene' change. To refresh tree.

        :param origin: the path of the originating signal
        :param args:
        :return:
        """
        self.request_refresh()

    def on_warning_signal(self, origin, message, caption, style):
        dlg = wx.MessageDialog(
            None,
            message,
            caption,
            style,
        )
        dlg.ShowModal()
        dlg.Destroy()

    def on_device_noactive(self, origin, value):
        dlg = wx.MessageDialog(
            None,
            _("No active device existed. Add a primary device."),
            _("Active Device"),
            wx.OK | wx.ICON_WARNING,
        )
        dlg.ShowModal()
        dlg.Destroy()

    def on_usb_error(self, origin, value):
        if value == 5:
            device = origin.split("/")[-1]
            self.context("window open -os %s Controller\n" % device)
            dlg = wx.MessageDialog(
                None,
                _("All attempts to connect to USB have failed."),
                _("Usb Connection Problem."),
                wx.OK | wx.ICON_WARNING,
            )
            dlg.ShowModal()
            dlg.Destroy()

    def on_usb_running(self, origin, value):
        self.usb_running = value

    def on_usb_state_text(self, origin, value):
        self.main_statusbar.SetStatusText(_("Usb: %s") % value, 0)

    def on_pipe_state(self, origin, state):
        if state == self.pipe_state:
            return
        self.pipe_state = state

        self.main_statusbar.SetStatusText(
            _("Controller: %s") % self.context.kernel.get_text_thread_state(state), 1
        )
        self.toolbar_button_bar.ToggleButton(ID_PAUSE, state == STATE_BUSY)

    def on_spooler_state(self, origin, value):
        self.main_statusbar.SetStatusText(
            _("Spooler: %s") % self.context.get_text_thread_state(value), 2
        )

    def on_driver_mode(self, origin, state):
        if state == 0:
            self.widget_scene.background_brush = wx.Brush("Grey")
        else:
            self.widget_scene.background_brush = wx.Brush("Red")
        self.widget_scene.request_refresh_for_animation()

    def on_export_signal(self, origin, frame):
        image_width, image_height, frame = frame
        if frame is not None:
            elements = self.context.elements
            from PIL import Image

            img = Image.fromarray(frame)
            obj = SVGImage()
            obj.image = img
            obj.image_width = image_width
            obj.image_height = image_height
            elements.add_elem(obj)

    def on_background_signal(self, origin, background):
        background = wx.Bitmap.FromBuffer(*background)
        self.scene.signal("background", background)
        self.request_refresh()

    def __set_titlebar(self):
        device_name = ""
        device_version = ""
        if self.context is not None:
            device_version = self.context.device_version
            device_name = str(self.context.device_name)
        try:
            active = self.context.active
            _spooler, _input_driver, _output = self.context.registered[
                "device/%s" % active
            ]
            self.SetTitle(
                _("%s v%s      (%s -> %s -> %s)")
                % (
                    device_name,
                    device_version,
                    _spooler.name,
                    _input_driver.type,
                    _output.type,
                )
            )
        except (KeyError, AttributeError):
            self.SetTitle(_("%s v%s") % (device_name, device_version))

    def __set_properties(self):
        # begin wxGlade: MeerK40t.__set_properties
        self.__set_titlebar()
        self.main_statusbar.SetStatusWidths([-1] * self.main_statusbar.GetFieldsCount())
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_meerk40t.GetBitmap())
        self.SetIcon(_icon)
        # statusbar fields
        main_statusbar_fields = ["Status"]
        for i in range(len(main_statusbar_fields)):
            self.main_statusbar.SetStatusText(main_statusbar_fields[i], i)

    def __do_layout(self):
        # main_sizer = wx.BoxSizer(wx.VERTICAL)
        # main_sizer.Add(self._ribbon, 0, wx.EXPAND, 0)
        # widget_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # widget_sizer.Add(self.tree, 1, wx.EXPAND, 0)
        # widget_sizer.Add(self.scene, 5, wx.EXPAND, 0)
        # main_sizer.Add(widget_sizer, 8, wx.EXPAND, 0)
        # self.SetSizer(main_sizer)
        # self._mgr.Update()
        self.Layout()

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
        files = self.context.load_types()
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
        for i in range(self.recent_file_menu.MenuItemCount):
            self.recent_file_menu.Remove(self.recent_file_menu.FindItemByPosition(0))
        context = self.context
        if context.file0 is not None and len(context.file0):
            self.recent_file_menu.Append(ID_MENU_FILE0, "&1   " + context.file0, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file0),
                id=ID_MENU_FILE0,
            )
        if context.file1 is not None and len(context.file1):
            self.recent_file_menu.Append(ID_MENU_FILE1, "&2   " + context.file1, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file1),
                id=ID_MENU_FILE1,
            )
        if context.file2 is not None and len(context.file2):
            self.recent_file_menu.Append(ID_MENU_FILE2, "&3   " + context.file2, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file2),
                id=ID_MENU_FILE2,
            )
        if context.file3 is not None and len(context.file3):
            self.recent_file_menu.Append(ID_MENU_FILE3, "&4   " + context.file3, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file3),
                id=ID_MENU_FILE3,
            )
        if context.file4 is not None and len(context.file4):
            self.recent_file_menu.Append(ID_MENU_FILE4, "&5   " + context.file4, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file4),
                id=ID_MENU_FILE4,
            )
        if context.file5 is not None and len(context.file5):
            self.recent_file_menu.Append(ID_MENU_FILE5, "&6   " + context.file5, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file5),
                id=ID_MENU_FILE5,
            )
        if context.file6 is not None and len(context.file6):
            self.recent_file_menu.Append(ID_MENU_FILE6, "&7   " + context.file6, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file6),
                id=ID_MENU_FILE6,
            )
        if context.file7 is not None and len(context.file7):
            self.recent_file_menu.Append(ID_MENU_FILE7, "&8   " + context.file7, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file7),
                id=ID_MENU_FILE7,
            )
        if context.file8 is not None and len(context.file8):
            self.recent_file_menu.Append(ID_MENU_FILE8, "&9   " + context.file8, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file8),
                id=ID_MENU_FILE8,
            )
        if context.file9 is not None and len(context.file9):
            self.recent_file_menu.Append(ID_MENU_FILE9, "1&0 " + context.file9, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file9),
                id=ID_MENU_FILE9,
            )
        if self.recent_file_menu.MenuItemCount != 0:
            self.recent_file_menu.AppendSeparator()
            self.recent_file_menu.Append(ID_MENU_FILE_CLEAR, _("Clear Recent"), "")
            self.Bind(wx.EVT_MENU, lambda e: self.clear_recent(), id=ID_MENU_FILE_CLEAR)

    def clear_recent(self):
        for i in range(10):
            try:
                setattr(self.context, "file" + str(i), "")
            except IndexError:
                break
        self.populate_recent_menu()

    def save_recent(self, pathname):
        recent = list()
        for i in range(10):
            recent.append(getattr(self.context, "file" + str(i)))
        recent = [r for r in recent if r is not None and r != pathname and len(r) > 0]
        recent.insert(0, pathname)
        for i in range(10):
            try:
                setattr(self.context, "file" + str(i), recent[i])
            except IndexError:
                break
        self.populate_recent_menu()

    def load(self, pathname):
        self.context.setting(bool, "auto_note", True)
        self.context.setting(bool, "uniform_svg", False)
        self.context.setting(float, "svg_ppi", 96.0)
        with wx.BusyInfo(_("Loading File...")):
            n = self.context.elements.note
            try:
                results = self.context.load(
                    pathname,
                    channel=self.context.channel("load"),
                    svg_ppi=self.context.svg_ppi,
                )
            except SyntaxError as e:
                dlg = wx.MessageDialog(
                    None,
                    str(e.msg),
                    _("File is Malformed."),
                    wx.OK | wx.ICON_WARNING,
                )
                dlg.ShowModal()
                dlg.Destroy()
                return False
            if results:
                self.save_recent(pathname)
                if n != self.context.elements.note and self.context.auto_note:
                    self.context("window open Notes\n")  # open/not toggle.
                try:
                    if self.context.uniform_svg and pathname.lower().endswith("svg"):
                        # or (len(elements) > 0 and "meerK40t" in elements[0].values):
                        # TODO: Disabled uniform_svg, no longer detecting namespace.
                        self.working_file = pathname
                except AttributeError:
                    pass
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
            err_msg = _("Some files were unrecognized:\n%s") % reject
            dlg = wx.MessageDialog(
                None, err_msg, _("Error encountered"), wx.OK | wx.ICON_ERROR
            )
            dlg.ShowModal()
            dlg.Destroy()

    def on_size(self, event):
        if self.context is None:
            return
        self.Layout()
        self.scene.signal("guide")
        self.request_refresh()

    def space_changed(self, origin, *args):
        self.ribbon_position_units = self.context.units_index
        self.update_ribbon_position()
        self.scene.signal("grid")
        self.scene.signal("guide")
        self.request_refresh(origin)

    def bed_changed(self, origin, *args):
        self.scene.signal("grid")
        # self.scene.signal('guide')
        self.request_refresh(origin)

    def on_emphasized_elements_changed(self, origin, *args):
        self.update_ribbon_position()
        self.laserpath_widget.clear_laserpath()
        self.request_refresh(origin)

    def request_refresh(self, *args):
        self.widget_scene.request_refresh(*args)

    def on_element_modified(self, *args):
        self.update_ribbon_position()
        self.widget_scene.request_refresh(*args)

    def on_focus_lost(self, event):
        self.context("-laser\nend\n")
        # event.Skip()

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

    def update_ribbon_position(self):
        pass
        # p = self.context
        # elements = p.elements
        # bounds = elements.selected_area()
        # self.text_w.Enable(bounds is not None)
        # self.text_h.Enable(bounds is not None)
        # self.text_x.Enable(bounds is not None)
        # self.text_y.Enable(bounds is not None)
        # self.button_aspect_ratio.Enable(bounds is not None)
        # if bounds is None:
        #     self.ribbon_position_ignore_update = True
        #     self.combo_box_units.SetSelection(self.ribbon_position_units)
        #     self.ribbon_position_ignore_update = False
        #     return
        # x0, y0, x1, y1 = bounds
        # conversion, name, index = (39.37, "mm", 0)
        # if self.ribbon_position_units == 2:
        #     conversion, name, index = (1000.0, "in", 2)
        # elif self.ribbon_position_units == 3:
        #     conversion, name, index = (1.0, "mil", 3)
        # elif self.ribbon_position_units == 1:
        #     conversion, name, index = (393.7, "cm", 1)
        # elif self.ribbon_position_units == 0:
        #     conversion, name, index = (39.37, "mm", 0)
        # self.ribbon_position_name = name
        # self.ribbon_position_x = x0 / conversion
        # self.ribbon_position_y = y0 / conversion
        # self.ribbon_position_w = (x1 - x0) / conversion
        # self.ribbon_position_h = (y1 - y0) / conversion
        # self.ribbon_position_ignore_update = True
        # if self.ribbon_position_units != 4:
        #     self.text_x.SetValue("%.2f" % self.ribbon_position_x)
        #     self.text_y.SetValue("%.2f" % self.ribbon_position_y)
        #     self.text_w.SetValue("%.2f" % self.ribbon_position_w)
        #     self.text_h.SetValue("%.2f" % self.ribbon_position_h)
        # else:
        #     self.text_x.SetValue("%.2f" % 100)
        #     self.text_y.SetValue("%.2f" % 100)
        #     self.text_w.SetValue("%.2f" % 100)
        #     self.text_h.SetValue("%.2f" % 100)
        # self.combo_box_units.SetSelection(self.ribbon_position_units)
        # self.ribbon_position_ignore_update = False

    # def on_text_x(self, event):  # wxGlade: MyFrame.<event_handler>
    #     if self.ribbon_position_ignore_update:
    #         return
    #     try:
    #         if self.ribbon_position_units != 4:
    #             self.ribbon_position_x = float(self.text_x.GetValue())
    #     except ValueError:
    #         pass
    #
    # def on_text_y(self, event):  # wxGlade: MyFrame.<event_handler>
    #     if self.ribbon_position_ignore_update:
    #         return
    #     try:
    #         if self.ribbon_position_units != 4:
    #             self.ribbon_position_y = float(self.text_y.GetValue())
    #     except ValueError:
    #         pass

    # def on_text_w(self, event):  # wxGlade: MyFrame.<event_handler>
    #     if self.ribbon_position_ignore_update:
    #         return
    #     try:
    #         new = float(self.text_w.GetValue())
    #         old = self.ribbon_position_w
    #         if self.ribbon_position_units == 4:
    #             ratio = new / 100.0
    #             if self.ribbon_position_aspect_ratio:
    #                 self.ribbon_position_ignore_update = True
    #                 self.text_h.SetValue("%.2f" % (ratio * 100))
    #                 self.ribbon_position_ignore_update = False
    #         else:
    #             ratio = new / old
    #             if self.ribbon_position_aspect_ratio:
    #                 self.ribbon_position_ignore_update = True
    #                 self.text_h.SetValue("%.2f" % (self.ribbon_position_h * ratio))
    #                 self.ribbon_position_ignore_update = False
    #     except (ValueError, ZeroDivisionError):
    #         pass

    # def on_button_aspect_ratio(self, event):  # wxGlade: MyFrame.<event_handler>
    #     if self.ribbon_position_ignore_update:
    #         return
    #     if self.ribbon_position_aspect_ratio:
    #         self.button_aspect_ratio.SetBitmap(icons8_padlock_50.GetBitmap())
    #     else:
    #         self.button_aspect_ratio.SetBitmap(icons8_lock_50.GetBitmap())
    #     self.ribbon_position_aspect_ratio = not self.ribbon_position_aspect_ratio

    # def on_text_h(self, event):  # wxGlade: MyFrame.<event_handler>
    #     if self.ribbon_position_ignore_update:
    #         return
    #     try:
    #         new = float(self.text_h.GetValue())
    #         old = self.ribbon_position_h
    #         if self.ribbon_position_units == 4:
    #             if self.ribbon_position_aspect_ratio:
    #                 self.ribbon_position_ignore_update = True
    #                 self.text_w.SetValue("%.2f" % new)
    #                 self.ribbon_position_ignore_update = False
    #         else:
    #             if self.ribbon_position_aspect_ratio:
    #                 self.ribbon_position_ignore_update = True
    #                 self.text_w.SetValue(
    #                     "%.2f" % (self.ribbon_position_w * (new / old))
    #                 )
    #                 self.ribbon_position_ignore_update = False
    #     except (ValueError, ZeroDivisionError):
    #         pass
    #
    # def on_text_dim_enter(self, event):
    #     if self.ribbon_position_units == 4:
    #         ratio_w = float(self.text_w.GetValue()) / 100.0
    #         ratio_h = float(self.text_h.GetValue()) / 100.0
    #         self.ribbon_position_w *= ratio_w
    #         self.ribbon_position_h *= ratio_h
    #     else:
    #         w = float(self.text_w.GetValue())
    #         h = float(self.text_h.GetValue())
    #         self.ribbon_position_w = w
    #         self.ribbon_position_h = h
    #     self.context(
    #         "resize %f%s %f%s %f%s %f%s\n"
    #         % (
    #             self.ribbon_position_x,
    #             self.ribbon_position_name,
    #             self.ribbon_position_y,
    #             self.ribbon_position_name,
    #             self.ribbon_position_w,
    #             self.ribbon_position_name,
    #             self.ribbon_position_h,
    #             self.ribbon_position_name,
    #         )
    #     )
    #     self.update_ribbon_position()
    #
    # def on_text_pos_enter(self, event):
    #     if self.ribbon_position_units == 4:
    #         ratio_x = float(self.text_x.GetValue()) / 100.0
    #         ratio_y = float(self.text_y.GetValue()) / 100.0
    #         self.ribbon_position_x *= ratio_x
    #         self.ribbon_position_y *= ratio_y
    #     else:
    #         x = float(self.text_x.GetValue())
    #         y = float(self.text_y.GetValue())
    #         self.ribbon_position_x = x
    #         self.ribbon_position_y = y
    #     self.context(
    #         "resize %f%s %f%s %f%s %f%s\n"
    #         % (
    #             self.ribbon_position_x,
    #             self.ribbon_position_name,
    #             self.ribbon_position_y,
    #             self.ribbon_position_name,
    #             self.ribbon_position_w,
    #             self.ribbon_position_name,
    #             self.ribbon_position_h,
    #             self.ribbon_position_name,
    #         )
    #     )
    #     self.update_ribbon_position()
    #
    # def on_combo_box_units(self, event):  # wxGlade: MyFrame.<event_handler>
    #     if self.ribbon_position_ignore_update:
    #         return
    #     self.ribbon_position_units = self.combo_box_units.GetSelection()
    #     self.update_ribbon_position()

    def on_click_new(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        context = self.context
        self.working_file = None
        context.elements.clear_all()
        self.laserpath_widget.clear_laserpath()
        self.request_refresh()

    def on_click_open(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        # This code should load just specific project files rather than all importable formats.
        files = self.context.load_types()
        with wx.FileDialog(
            self, _("Open"), wildcard=files, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind
            pathname = fileDialog.GetPath()
            self.load(pathname)

    def on_click_stop(self, event=None):
        self.context("estop\n")

    def on_click_pause(self, event=None):
        self.context("pause\n")

    def on_click_save(self, event):
        if self.working_file is None:
            self.on_click_save_as(event)
        else:
            self.save_recent(self.working_file)
            self.context.save(self.working_file)

    def on_click_save_as(self, event=None):
        files = self.context.save_types()
        with wx.FileDialog(
            self,
            _("Save Project"),
            wildcard=files,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind
            pathname = fileDialog.GetPath()
            if not pathname.lower().endswith(".svg"):
                pathname += ".svg"
            self.context.save(pathname)
            self.working_file = pathname
            self.save_recent(self.working_file)

    def on_click_exit(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        try:
            self.Close()
        except RuntimeError:
            pass

    def on_click_zoom_out(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoomout button press
        """
        m = self.scene.ClientSize / 2
        self.widget_scene.widget_root.scene_widget.scene_post_scale(
            1.0 / 1.5, 1.0 / 1.5, m[0], m[1]
        )
        self.request_refresh()

    def on_click_zoom_in(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoomin button press
        """
        m = self.scene.ClientSize / 2
        self.widget_scene.widget_root.scene_widget.scene_post_scale(
            1.5, 1.5, m[0], m[1]
        )
        self.request_refresh()

    def on_click_zoom_size(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoom size button press.
        """
        elements = self.context.elements
        bbox = elements.selected_area()
        if bbox is None:
            bed_dim = self.context.root
            bbox = (
                0,
                0,
                bed_dim.bed_width * MILS_IN_MM,
                bed_dim.bed_height * MILS_IN_MM,
            )
        self.widget_scene.widget_root.focus_viewport_scene(bbox, self.scene.ClientSize)
        self.request_refresh()

    def toggle_draw_mode(self, bits):
        """
        Toggle the draw mode.
        :param bits: Bit to toggle.
        :return: Toggle function.
        """

        def toggle(event=None):
            self.context.draw_mode ^= bits
            self.context.signal("draw_mode", self.context.draw_mode)
            self.request_refresh()

        return toggle

    def open_speedcode_gear_dialog(self):
        dlg = wx.TextEntryDialog(self, _("Enter Forced Gear"), _("Gear Entry"), "")
        dlg.SetValue("")

        if dlg.ShowModal() == wx.ID_OK:
            value = dlg.GetValue()
            if value in ("0", "1", "2", "3", "4"):
                self.context._stepping_force = int(value)
            else:
                self.context._stepping_force = None
        dlg.Destroy()

    def open_fps_dialog(self):
        dlg = wx.TextEntryDialog(self, _("Enter FPS Limit"), _("FPS Limit Entry"), "")
        dlg.SetValue("")

        if dlg.ShowModal() == wx.ID_OK:
            fps = dlg.GetValue()
            try:
                self.widget_scene.set_fps(int(fps))
            except ValueError:
                pass
        dlg.Destroy()

    def open_transform_dialog(self):
        dlg = wx.TextEntryDialog(
            self,
            _(
                "Enter SVG Transform Instruction e.g. 'scale(1.49, 1, $x, $y)', rotate, translate, etc..."
            ),
            _("Transform Entry"),
            "",
        )
        dlg.SetValue("")

        if dlg.ShowModal() == wx.ID_OK:
            spooler, input_driver, output = self.context.registered[
                "device/%s" % self.context.root.active
            ]
            root_context = self.context.root
            bed_dim = self.context.root
            m = str(dlg.GetValue())
            m = m.replace("$x", str(input_driver.current_x))
            m = m.replace("$y", str(input_driver.current_y))
            mx = Matrix(m)
            wmils = bed_dim.bed_width * 39.37
            hmils = bed_dim.bed_height * 39.37
            mx.render(ppi=1000, width=wmils, height=hmils)
            if mx.is_identity():
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
                for element in root_context.elements.elems():
                    try:
                        element *= mx
                        element.node.modified()
                    except AttributeError:
                        pass

    def open_fill_dialog(self):
        context = self.context
        elements = context.elements
        first_selected = elements.first_element(emphasized=True)
        if first_selected is None:
            return
        data = wx.ColourData()
        if first_selected.fill is not None and first_selected.fill != "none":
            data.SetColour(wx.Colour(swizzlecolor(first_selected.fill)))
        dlg = wx.ColourDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetColourData()
            color = data.GetColour()
            rgb = color.GetRGB()
            color = swizzlecolor(rgb)
            color = Color(color, 1.0)
            for elem in elements.elems(emphasized=True):
                elem.fill = color
                elem.node.altered()

    def open_stroke_dialog(self):
        context = self.context
        elements = context.elements
        first_selected = elements.first_element(emphasized=True)
        if first_selected is None:
            return
        data = wx.ColourData()
        if first_selected.stroke is not None and first_selected.stroke != "none":
            data.SetColour(wx.Colour(swizzlecolor(first_selected.stroke)))
        dlg = wx.ColourDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetColourData()
            color = data.GetColour()
            rgb = color.GetRGB()
            color = swizzlecolor(rgb)
            color = Color(color, 1.0)
            for elem in elements.elems(emphasized=True):
                elem.stroke = color
                elem.node.altered()

    def open_flip_dialog(self):
        dlg = wx.TextEntryDialog(
            self,
            _(
                "Material must be jigged at 0,0 either home or home offset.\nHow wide is your material (give units: in, mm, cm, px, etc)?"
            ),
            _("Double Side Flip"),
            "",
        )
        dlg.SetValue("")
        if dlg.ShowModal() == wx.ID_OK:
            p = self.context
            root_context = p.root
            bed_dim = root_context
            wmils = bed_dim.bed_width * MILS_IN_MM
            # hmils = bed_dim.bed_height * MILS_IN_MM
            length = Length(dlg.GetValue()).value(ppi=1000.0, relative_length=wmils)
            mx = Matrix()
            mx.post_scale(-1.0, 1, length / 2.0, 0)
            for element in root_context.elements.elems(emphasized=True):
                try:
                    element *= mx
                    element.node.modified()
                except AttributeError:
                    pass
        dlg.Destroy()

    def open_path_dialog(self):
        dlg = wx.TextEntryDialog(self, _("Enter SVG Path Data"), _("Path Entry"), "")
        dlg.SetValue("")

        if dlg.ShowModal() == wx.ID_OK:
            context = self.context
            path = Path(dlg.GetValue())
            path.stroke = "blue"
            p = abs(path)
            context.elements.add_elem(p)
            self.context.classify([p])
        dlg.Destroy()

    def egv_import(self):
        files = "*.egv"
        with wx.FileDialog(
            self,
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
            self.context("egv_import %s\n" % pathname)
            return

    def egv_export(self):
        files = "*.egv"
        with wx.FileDialog(
            self, _("Export EGV"), wildcard=files, style=wx.FD_SAVE
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind
            pathname = fileDialog.GetPath()
        if pathname is None:
            return
        with wx.BusyInfo(_("Saving File...")):
            self.context("egv_export %s\n" % pathname)
            return

    def apply_rotary_scale(self):
        r = self.context.get_context("rotary/1")
        sx = r.scale_x
        sy = r.scale_y
        spooler, input_driver, output = self.context.root.device()

        mx = Matrix(
            "scale(%f, %f, %f, %f)"
            % (sx, sy, input_driver.current_x, input_driver.current_y)
        )
        for element in self.context.root.elements.elems():
            try:
                element *= mx
                element.node.modified()
            except AttributeError:
                pass

    def toggle_rotary_view(self):
        if self._rotary_view:
            self.widget_scene.rotary_stretch()
        else:
            self.widget_scene.rotary_unstretch()
        self._rotary_view = not self._rotary_view

    def run_jog_transition_finish_test(self):
        return self.run_jog_transition_test(COMMAND_JOG_FINISH)

    def run_jog_transition_switch_test(self):
        return self.run_jog_transition_test(COMMAND_JOG_SWITCH)

    def run_jog_transition_test(self, command=COMMAND_JOG):
        """ "
        The Jog Transition Test is intended to test the jogging
        """

        def jog_transition_test():
            yield COMMAND_SET_ABSOLUTE
            yield COMMAND_MODE_RAPID
            yield COMMAND_HOME
            yield COMMAND_LASER_OFF
            yield COMMAND_WAIT_FINISH
            yield COMMAND_MOVE, 3000, 3000
            yield COMMAND_WAIT_FINISH
            yield COMMAND_LASER_ON
            yield COMMAND_WAIT, 0.05
            yield COMMAND_LASER_OFF
            yield COMMAND_WAIT_FINISH

            yield COMMAND_SET_SPEED, 10.0

            def pos(i):
                if i < 3:
                    x = 200
                elif i < 6:
                    x = -200
                else:
                    x = 0
                if i % 3 == 0:
                    y = 200
                elif i % 3 == 1:
                    y = -200
                else:
                    y = 0
                return x, y

            for q in range(8):
                top = q & 1
                left = q & 2
                x_val = q & 3
                yield COMMAND_SET_DIRECTION, top, left, x_val, not x_val
                yield COMMAND_MODE_PROGRAM
                for j in range(9):
                    jx, jy = pos(j)
                    for k in range(9):
                        kx, ky = pos(k)
                        yield COMMAND_MOVE, 3000, 3000
                        yield COMMAND_MOVE, 3000 + jx, 3000 + jy
                        yield command, 3000 + jx + kx, 3000 + jy + ky
                yield COMMAND_MOVE, 3000, 3000
                yield COMMAND_MODE_RAPID
                yield COMMAND_WAIT_FINISH
                yield COMMAND_LASER_ON
                yield COMMAND_WAIT, 0.05
                yield COMMAND_LASER_OFF
                yield COMMAND_WAIT_FINISH

        self.context.spooler.job(jog_transition_test)

    def run_home_and_dot_test(self):
        def home_dot_test():
            for i in range(25):
                yield COMMAND_SET_ABSOLUTE
                yield COMMAND_MODE_RAPID
                yield COMMAND_HOME
                yield COMMAND_LASER_OFF
                yield COMMAND_WAIT_FINISH
                yield COMMAND_MOVE, 3000, 3000
                yield COMMAND_WAIT_FINISH
                yield COMMAND_LASER_ON
                yield COMMAND_WAIT, 0.05
                yield COMMAND_LASER_OFF
                yield COMMAND_WAIT_FINISH
            yield COMMAND_HOME
            yield COMMAND_WAIT_FINISH

        self.context.spooler.job(home_dot_test)


NODE_ROOT = 0
NODE_OPERATION_BRANCH = 10
NODE_OPERATION = 11
NODE_OPERATION_ELEMENT = 12
NODE_ELEMENTS_BRANCH = 20
NODE_ELEMENT = 21
NODE_FILES_BRANCH = 30
NODE_FILE_FILE = 31
NODE_FILE_ELEMENT = 32


class ShadowTree:
    """
    The shadowTree creates a wx.Tree structure from the elements.tree structure. It listens to updates to the elements
    tree and updates the GUI version accordingly. This tree does not permit alterations to it, rather it sends any
    requested alterations to the elements.tree or the elements.elements or elements.operations and when those are
    reflected in the tree, the shadow tree is updated accordingly.
    """

    def __init__(self, context, gui, root):
        self.context = context
        self.element_root = root
        self.gui = gui
        self.wxtree = gui.wxtree
        self.renderer = gui.renderer
        self.dragging_nodes = None
        self.tree_images = None
        self.object = "Project"
        self.name = "Project"
        self.context = context
        self.elements = context.elements
        self.elements.listen(self)
        self.do_not_select = False

    def node_created(self, node, **kwargs):
        pass

    def node_destroyed(self, node, **kwargs):
        pass

    def node_detached(self, node, **kwargs):
        self.unregister_children(node)
        self.node_unregister(node, **kwargs)

    def node_attached(self, node, **kwargs):
        self.node_register(node, **kwargs)
        self.register_children(node)

    def node_changed(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node)

    def selected(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node)
        self.set_enhancements(node)
        self.context.signal("selected", node)

    def emphasized(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node)
        self.set_enhancements(node)
        self.context.signal("emphasized", node)

    def targeted(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node)
        self.set_enhancements(node)
        self.context.signal("targeted", node)

    def highlighted(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node)
        self.set_enhancements(node)
        self.context.signal("highlighted", node)

    def modified(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node)
        try:
            c = node.color
            self.set_color(node, c)
        except AttributeError:
            pass
        self.context.signal("modified", node)

    def altered(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node, force=True)
        try:
            c = node.color
            self.set_color(node, c)
        except AttributeError:
            pass
        self.set_icon(node)
        self.context.signal("altered", node)

    def expand(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.wxtree.ExpandAllChildren(item)

    def collapse(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.wxtree.CollapseAllChildren(item)
        if self.wxtree.GetItemParent(item) == self.wxtree.GetRootItem():
            self.wxtree.Expand(item)

    def reorder(self, node):
        self.rebuild_tree()

    def update(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.set_icon(node)
        self.on_force_element_update(node)

    def focus(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.wxtree.EnsureVisible(item)
        for s in self.wxtree.GetSelections():
            self.wxtree.SelectItem(s, False)
        self.wxtree.SelectItem(item)
        self.wxtree.ScrollTo(item)

    def on_force_element_update(self, *args):
        element = args[0]
        if hasattr(element, "node"):
            self.update_label(element.node, force=True)
        else:
            self.update_label(element, force=True)

    def on_element_update(self, *args):
        element = args[0]
        if hasattr(element, "node"):
            self.update_label(element.node)
        else:
            self.update_label(element)

    def refresh_tree(self, node=None):
        """Any tree elements currently displaying wrong data as per elements should be updated to display
        the proper values and contexts and icons."""
        if node is None:
            node = self.element_root.item
        if node is None:
            return
        tree = self.wxtree

        child, cookie = tree.GetFirstChild(node)
        while child.IsOk():
            child_node = self.wxtree.GetItemData(child)
            self.set_enhancements(child_node)
            self.refresh_tree(child)
            child, cookie = tree.GetNextChild(node, cookie)

    def rebuild_tree(self):
        self.dragging_nodes = None
        self.wxtree.DeleteAllItems()

        self.tree_images = wx.ImageList()
        self.tree_images.Create(width=20, height=20)

        self.wxtree.SetImageList(self.tree_images)
        self.element_root.item = self.wxtree.AddRoot(self.name)

        self.wxtree.SetItemData(self.element_root.item, self.element_root)

        self.set_icon(
            self.element_root, icon_meerk40t.GetBitmap(False, resize=(20, 20))
        )
        self.register_children(self.element_root)

        node_operations = self.element_root.get(type="branch ops")
        self.set_icon(node_operations, icons8_laser_beam_20.GetBitmap())

        for n in node_operations.children:
            self.set_icon(n)

        node_elements = self.element_root.get(type="branch elems")
        self.set_icon(node_elements, icons8_vector_20.GetBitmap())

        # Expand Ops and Element nodes only
        # We check these two exist but will open any additional siblings just in case
        self.wxtree.CollapseAll()
        item = self.wxtree.GetFirstVisibleItem()
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.wxtree.Expand(item)
        item = self.wxtree.GetNextSibling(item)
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.wxtree.Expand(item)
        item = self.wxtree.GetNextSibling(item)
        while item.IsOk():
            self.wxtree.Expand(item)
            item = self.wxtree.GetNextSibling(item)

    def register_children(self, node):
        for child in node.children:
            self.node_register(child)
            self.register_children(child)

    def unregister_children(self, node):
        for child in node.children:
            self.unregister_children(child)
            self.node_unregister(child)

    def node_unregister(self, node, **kwargs):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        node.unregister_object()
        self.wxtree.Delete(node.item)
        for i in self.wxtree.GetSelections():
            self.wxtree.SelectItem(i, False)

    def node_register(self, node, pos=None, **kwargs):
        parent = node.parent
        parent_item = parent.item
        tree = self.wxtree
        if pos is None:
            node.item = tree.AppendItem(parent_item, self.name)
        else:
            node.item = tree.InsertItem(parent_item, pos, self.name)
        tree.SetItemData(node.item, node)
        self.update_label(node)
        try:
            stroke = node.object.values[SVG_ATTR_STROKE]
            color = wx.Colour(swizzlecolor(Color(stroke).argb))
            tree.SetItemTextColour(node.item, color)
        except AttributeError:
            pass
        except KeyError:
            pass
        except TypeError:
            pass
        self.set_icon(node)
        self.context.signal("refresh_tree")

    def set_enhancements(self, node):
        tree = self.wxtree
        node_item = node.item
        tree.SetItemBackgroundColour(node_item, None)
        try:
            if node.highlighted:
                tree.SetItemBackgroundColour(node_item, wx.LIGHT_GREY)
            elif node.emphasized:
                tree.SetItemBackgroundColour(node_item, wx.Colour(0x80A0A0))
            elif node.targeted:
                tree.SetItemBackgroundColour(node_item, wx.Colour(0xA080A0))
        except AttributeError:
            pass

    def set_color(self, node, color=None):
        item = node.item
        if item is None:
            return
        tree = self.wxtree
        if color is None:
            tree.SetItemTextColour(item, None)
        else:
            tree.SetItemTextColour(item, wx.Colour(swizzlecolor(color)))

    def set_icon(self, node, icon=None):
        root = self
        drawmode = self.context.draw_mode
        if drawmode & DRAW_MODE_ICONS != 0:
            return
        try:
            item = node.item
        except AttributeError:
            return  # Node.item can be none if launched from ExecuteJob where the nodes are not part of the tree.
        data_object = node.object
        tree = root.wxtree
        if icon is None:
            if isinstance(data_object, SVGImage):
                image = self.renderer.make_thumbnail(
                    data_object.image, width=20, height=20
                )
                image_id = self.tree_images.Add(bitmap=image)
                tree.SetItemImage(item, image=image_id)
            elif isinstance(data_object, (Shape, SVGText)):
                if isDot(data_object):
                    if (
                        data_object.stroke is not None
                        and data_object.stroke.rgb is not None
                    ):
                        c = data_object.stroke
                    else:
                        c = Color("black")
                    self.set_icon(node, icons8_scatter_plot_20.GetBitmap(color=c))
                    return
                image = self.renderer.make_raster(
                    node, data_object.bbox(), width=20, height=20, bitmap=True
                )
                if image is not None:
                    image_id = self.tree_images.Add(bitmap=image)
                    tree.SetItemImage(item, image=image_id)
                    self.context.signal("refresh_tree")
            elif isinstance(node, LaserOperation):
                try:
                    op = node.operation
                except AttributeError:
                    op = None
                try:
                    c = node.color
                    self.set_color(node, c)
                except AttributeError:
                    c = None
                if op in ("Raster", "Image"):
                    self.set_icon(node, icons8_direction_20.GetBitmap(color=c))
                elif op in ("Engrave", "Cut"):
                    self.set_icon(node, icons8_laser_beam_20.GetBitmap(color=c))
                elif op == "Dots":
                    self.set_icon(node, icons8_scatter_plot_20.GetBitmap(color=c))
                else:
                    self.set_icon(node, icons8_system_task_20.GetBitmap(color=c))
            elif node.type == "file":
                self.set_icon(node, icons8_file_20.GetBitmap())
            elif node.type == "group":
                self.set_icon(node, icons8_group_objects_20.GetBitmap())
        else:
            image_id = self.tree_images.Add(bitmap=icon)
            tree.SetItemImage(item, image=image_id)

    def update_label(self, node, force=False):
        if node.label is None or force:
            node.label = node.create_label()
            self.set_icon(node)
        if not hasattr(node, "item"):
            # Unregistered node updating name.
            self.rebuild_tree()
            return

        self.wxtree.SetItemText(node.item, node.label)
        try:
            stroke = node.object.stroke
            color = wx.Colour(swizzlecolor(Color(stroke).argb))
            self.wxtree.SetItemTextColour(node.item, color)
        except AttributeError:
            pass
        try:
            color = node.color
            c = wx.Colour(swizzlecolor(Color(color)))
            self.wxtree.SetItemTextColour(node.item, c)
        except AttributeError:
            pass

    def move_node(self, node, new_parent, pos=None):
        tree = self.root.shadow_tree
        item = self.item
        image = tree.GetItemImage(item)
        data = tree.GetItemData(item)
        color = tree.GetItemTextColour(item)
        tree.Delete(item)
        if pos is None:
            self.item = tree.AppendItem(new_parent.item, self.name)
        else:
            self.item = tree.InsertItem(new_parent.item, pos, self.name)
        item = self.item
        tree.SetItemImage(item, image)
        tree.SetItemData(item, data)
        tree.SetItemTextColour(item, color)

    def bbox(self, node):
        return Group.union_bbox([self.object])

    def on_drag_begin_handler(self, event):
        """
        Drag handler begin for the tree.

        :param event:
        :return:
        """
        self.dragging_nodes = None

        pt = event.GetPoint()
        drag_item, _ = self.wxtree.HitTest(pt)

        if drag_item is None or drag_item.ID is None or not drag_item.IsOk():
            event.Skip()
            return

        self.dragging_nodes = [
            self.wxtree.GetItemData(item) for item in self.wxtree.GetSelections()
        ]
        if not len(self.dragging_nodes):
            event.Skip()
            return

        t = self.dragging_nodes[0].type
        for n in self.dragging_nodes:
            if t != n.type:
                event.Skip()
                return
            if not n.is_movable():
                event.Skip()
                return
        event.Allow()

    def on_drag_end_handler(self, event):
        """
        Drag end handler for the tree

        :param event:
        :return:
        """
        if self.dragging_nodes is None:
            event.Skip()
            return

        drop_item = event.GetItem()
        if drop_item is None or drop_item.ID is None:
            event.Skip()
            return
        drop_node = self.wxtree.GetItemData(drop_item)
        if drop_node is None:
            event.Skip()
            return

        skip = True
        for drag_node in self.dragging_nodes:
            if drop_node is drag_node:
                continue
            if drop_node.drop(drag_node):
                skip = False
        if skip:
            event.Skip()
        else:
            event.Allow()
        self.dragging_nodes = None

    def on_item_right_click(self, event):
        """
        Right click of element in tree.

        :param event:
        :return:
        """
        item = event.GetItem()
        if item is None:
            return
        node = self.wxtree.GetItemData(item)

        self.create_menu(self.gui, node)

    def on_item_activated(self, event):
        """
        Tree item is double-clicked. Launches PropertyWindow associated with that object.

        :param event:
        :return:
        """
        item = event.GetItem()
        node = self.wxtree.GetItemData(item)
        self.activated_node(node)

    def activate_selected_node(self):
        first_element = self.elements.first_element(emphasized=True)
        if hasattr(first_element, "node"):
            self.activated_node(first_element.node)

    def activated_node(self, node):
        if isinstance(node, LaserOperation):
            self.context.open("window/OperationProperty", self.gui, node=node)
            return
        if node is None:
            return
        obj = node.object
        if obj is None:
            return
        elif isinstance(obj, Path):
            self.context.open("window/PathProperty", self.gui, node=node)
        elif isinstance(obj, SVGText):
            self.context.open("window/TextProperty", self.gui, node=node)
        elif isinstance(obj, SVGImage):
            self.context.open("window/ImageProperty", self.gui, node=node)
        elif isinstance(obj, Group):
            self.context.open("window/GroupProperty", self.gui, node=node)
        elif isinstance(obj, SVGElement):
            self.context.open("window/PathProperty", self.gui, node=node)
        elif isinstance(obj, CutCode):
            self.context.open("window/Simulation", self.gui, node=node)

    def on_item_selection_changed(self, event):
        """
        Tree menu item is changed. Modify the selection.

        :param event:
        :return:
        """
        if self.do_not_select:
            # Do not select is part of a linux correction where moving nodes around in a drag and drop fashion could
            # cause them to appear to drop invalid nodes.
            return
        selected = [
            self.wxtree.GetItemData(item) for item in self.wxtree.GetSelections()
        ]
        self.elements.set_selected(selected)

        emphasized = list(selected)
        for i in range(len(emphasized)):
            node = emphasized[i]
            if node.type == "opnode":
                emphasized[i] = node.object.node
            elif node.type == "op":
                for n in node.flat(types=("opnode",), cascade=False):
                    try:
                        emphasized.append(n.object.node)
                    except Exception:
                        pass

        self.elements.set_emphasis(emphasized)
        self.refresh_tree()
        self.gui.request_refresh()
        # self.do_not_select = True
        # for s in self.wxtree.GetSelections():
        #     self.wxtree.SelectItem(s, False)
        # self.do_not_select = False
        event.Allow()

    def select_in_tree_by_emphasis(self):
        """
        :return:
        """
        self.do_not_select = True
        for e in self.elements.elems_nodes(emphasized=True):
            self.wxtree.SelectItem(e.item, True)
        self.do_not_select = False

    def contains(self, box, x, y=None):
        if y is None:
            y = x[1]
            x = x[0]
        return box[0] <= x <= box[2] and box[1] <= y <= box[3]

    def create_menu_for_node(self, gui, node) -> wx.Menu:
        """
        Create menu for a particular node. Does not invoke the menu.

        Processes submenus, references, radio_state as needed.
        """
        menu = wx.Menu()
        submenus = {}
        radio_check_not_needed = []

        def menu_functions(f, node):
            func_dict = dict(f.func_dict)

            def specific(event=None):
                f(node, **func_dict)

            return specific

        for func in self.elements.tree_operations_for_node(node):
            submenu_name = func.submenu
            submenu = None
            if submenu_name in submenus:
                submenu = submenus[submenu_name]
            else:
                if func.separate_before:
                    menu.AppendSeparator()
                if submenu_name is not None:
                    submenu = wx.Menu()
                    menu.AppendSubMenu(submenu, submenu_name)
                    submenus[submenu_name] = submenu

            menu_context = submenu if submenu is not None else menu
            if func.reference is not None:
                menu_context.AppendSubMenu(
                    self.create_menu_for_node(gui, func.reference(node)), func.real_name
                )
                continue
            if func.radio_state is not None:
                item = menu_context.Append(wx.ID_ANY, func.real_name, "", wx.ITEM_RADIO)
                gui.Bind(
                    wx.EVT_MENU,
                    menu_functions(func, node),
                    item,
                )
                check = func.radio_state
                item.Check(check)
                if check and menu_context not in radio_check_not_needed:
                    radio_check_not_needed.append(menu_context)
            else:
                gui.Bind(
                    wx.EVT_MENU,
                    menu_functions(func, node),
                    menu_context.Append(wx.ID_ANY, func.real_name, "", wx.ITEM_NORMAL),
                )
                if menu_context not in radio_check_not_needed:
                    radio_check_not_needed.append(menu_context)
            if not submenu and func.separate_after:
                menu.AppendSeparator()

        for submenu in submenus.values():
            if submenu not in radio_check_not_needed:
                item = submenu.Append(wx.ID_ANY, _("Other"), "", wx.ITEM_RADIO)
                item.Check(True)
        return menu

    def create_menu(self, gui, node):
        """
        Create menu items. This is used for both the scene and the tree to create menu items.

        :param gui: Gui used to create menu items.
        :param node: The Node clicked on for the generated menu.
        :return:
        """
        if node is None:
            return
        if hasattr(node, "node"):
            node = node.node
        menu = self.create_menu_for_node(gui, node)
        if menu.MenuItemCount != 0:
            gui.PopupMenu(menu)
            menu.Destroy()


def get_key_name(event):
    keyvalue = ""
    if event.ControlDown():
        keyvalue += "control+"
    if event.AltDown():
        keyvalue += "alt+"
    if event.ShiftDown():
        keyvalue += "shift+"
    if event.MetaDown():
        keyvalue += "meta+"
    key = event.GetKeyCode()
    if key == wx.WXK_CONTROL:
        return
    if key == wx.WXK_ALT:
        return
    if key == wx.WXK_SHIFT:
        return
    if key == wx.WXK_F1:
        keyvalue += "f1"
    elif key == wx.WXK_F2:
        keyvalue += "f2"
    elif key == wx.WXK_F3:
        keyvalue += "f3"
    elif key == wx.WXK_F4:
        keyvalue += "f4"
    elif key == wx.WXK_F5:
        keyvalue += "f5"
    elif key == wx.WXK_F6:
        keyvalue += "f6"
    elif key == wx.WXK_F7:
        keyvalue += "f7"
    elif key == wx.WXK_F8:
        keyvalue += "f8"
    elif key == wx.WXK_F9:
        keyvalue += "f9"
    elif key == wx.WXK_F10:
        keyvalue += "f10"
    elif key == wx.WXK_F11:
        keyvalue += "f11"
    elif key == wx.WXK_F12:
        keyvalue += "f12"
    elif key == wx.WXK_F13:
        keyvalue += "f13"
    elif key == wx.WXK_F14:
        keyvalue += "f14"
    elif key == wx.WXK_F15:
        keyvalue += "f15"
    elif key == wx.WXK_F16:
        keyvalue += "f16"
    elif key == wx.WXK_ADD:
        keyvalue += "+"
    elif key == wx.WXK_END:
        keyvalue += "end"
    elif key == wx.WXK_NUMPAD0:
        keyvalue += "numpad0"
    elif key == wx.WXK_NUMPAD1:
        keyvalue += "numpad1"
    elif key == wx.WXK_NUMPAD2:
        keyvalue += "numpad2"
    elif key == wx.WXK_NUMPAD3:
        keyvalue += "numpad3"
    elif key == wx.WXK_NUMPAD4:
        keyvalue += "numpad4"
    elif key == wx.WXK_NUMPAD5:
        keyvalue += "numpad5"
    elif key == wx.WXK_NUMPAD6:
        keyvalue += "numpad6"
    elif key == wx.WXK_NUMPAD7:
        keyvalue += "numpad7"
    elif key == wx.WXK_NUMPAD8:
        keyvalue += "numpad8"
    elif key == wx.WXK_NUMPAD9:
        keyvalue += "numpad9"
    elif key == wx.WXK_NUMPAD_ADD:
        keyvalue += "numpad_add"
    elif key == wx.WXK_NUMPAD_SUBTRACT:
        keyvalue += "numpad_subtract"
    elif key == wx.WXK_NUMPAD_MULTIPLY:
        keyvalue += "numpad_multiply"
    elif key == wx.WXK_NUMPAD_DIVIDE:
        keyvalue += "numpad_divide"
    elif key == wx.WXK_NUMPAD_DECIMAL:
        keyvalue += "numpad."
    elif key == wx.WXK_NUMPAD_ENTER:
        keyvalue += "numpad_enter"
    elif key == wx.WXK_NUMPAD_RIGHT:
        keyvalue += "numpad_right"
    elif key == wx.WXK_NUMPAD_LEFT:
        keyvalue += "numpad_left"
    elif key == wx.WXK_NUMPAD_UP:
        keyvalue += "numpad_up"
    elif key == wx.WXK_NUMPAD_DOWN:
        keyvalue += "numpad_down"
    elif key == wx.WXK_NUMPAD_DELETE:
        keyvalue += "numpad_delete"
    elif key == wx.WXK_NUMPAD_INSERT:
        keyvalue += "numpad_insert"
    elif key == wx.WXK_NUMPAD_PAGEUP:
        keyvalue += "numpad_pgup"
    elif key == wx.WXK_NUMPAD_PAGEDOWN:
        keyvalue += "numpad_pgdn"
    elif key == wx.WXK_NUMLOCK:
        keyvalue += "numlock"
    elif key == wx.WXK_SCROLL:
        keyvalue += "scroll"
    elif key == wx.WXK_HOME:
        keyvalue += "home"
    elif key == wx.WXK_DOWN:
        keyvalue += "down"
    elif key == wx.WXK_UP:
        keyvalue += "up"
    elif key == wx.WXK_RIGHT:
        keyvalue += "right"
    elif key == wx.WXK_LEFT:
        keyvalue += "left"
    elif key == wx.WXK_ESCAPE:
        keyvalue += "escape"
    elif key == wx.WXK_BACK:
        keyvalue += "back"
    elif key == wx.WXK_PAUSE:
        keyvalue += "pause"
    elif key == wx.WXK_PAGEDOWN:
        keyvalue += "pagedown"
    elif key == wx.WXK_PAGEUP:
        keyvalue += "pageup"
    elif key == wx.WXK_PRINT:
        keyvalue += "print"
    elif key == wx.WXK_RETURN:
        keyvalue += "return"
    elif key == wx.WXK_SPACE:
        keyvalue += "space"
    elif key == wx.WXK_TAB:
        keyvalue += "tab"
    elif key == wx.WXK_DELETE:
        keyvalue += "delete"
    elif key == wx.WXK_INSERT:
        keyvalue += "insert"
    else:
        keyvalue += chr(key)
    return keyvalue.lower()


class wxMeerK40t(wx.App, Module):
    """
    wxMeerK40t is the wx.App main class and a qualified Module for the MeerK40t kernel.
    Running MeerK40t without the wxMeerK40t gui is both possible and reasonable. This should not change the way the
    underlying code runs. It should just be a series of frames held together with the kernel.
    """

    def __init__(self, context, path):
        wx.App.__init__(self, 0)
        import meerk40t.gui.icons as icons

        icons.DARKMODE = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        icons.icon_r = 230
        icons.icon_g = 230
        icons.icon_b = 230
        Module.__init__(self, context, path)
        self.locale = None
        self.Bind(wx.EVT_CLOSE, self.on_app_close)
        self.Bind(wx.EVT_QUERY_END_SESSION, self.on_app_close)  # MAC DOCK QUIT.
        self.Bind(wx.EVT_END_SESSION, self.on_app_close)
        self.Bind(wx.EVT_END_PROCESS, self.on_app_close)
        # This catches events when the app is asked to activate by some other process
        self.Bind(wx.EVT_ACTIVATE_APP, self.OnActivate)

    def on_app_close(self, event=None):
        try:
            if self.context is not None:
                self.context("quit\n")
        except AttributeError:
            pass

    def OnInit(self):
        return True

    def BringWindowToFront(self):
        try:  # it's possible for this event to come when the frame is closed
            self.GetTopWindow().Raise()
        except Exception:
            pass

    def OnActivate(self, event):
        # if this is an activate event, rather than something else, like iconize.
        if event.GetActive():
            self.BringWindowToFront()
        event.Skip()

    def MacReopenApp(self):
        """Called when the doc icon is clicked, and ???"""
        self.BringWindowToFront()

    def MacNewFile(self):
        try:
            if self.context is not None:
                self.context.elements.clear_all()
        except AttributeError:
            pass

    def MacPrintFile(self, file_path):
        pass

    def MacOpenFile(self, filename):
        try:
            if self.context is not None:
                self.context.load(os.path.realpath(filename))
        except AttributeError:
            pass

    def MacOpenFiles(self, filenames):
        try:
            if self.context is not None:
                for filename in filenames:
                    self.context.load(os.path.realpath(filename))
        except AttributeError:
            pass

    @staticmethod
    def sub_register(kernel):
        kernel.register("window/MeerK40t", MeerK40t)
        kernel.register("window/PathProperty", PathProperty)
        kernel.register("window/TextProperty", TextProperty)
        kernel.register("window/ImageProperty", ImageProperty)
        kernel.register("window/OperationProperty", OperationProperty)
        kernel.register("window/GroupProperty", GroupProperty)
        kernel.register("window/CameraInterface", CameraInterface)
        kernel.register("window/Terminal", Console)
        kernel.register("window/Console", Console)
        kernel.register("window/Settings", Settings)
        kernel.register("window/Rotary", RotarySettings)
        kernel.register("window/About", About)
        kernel.register("window/DeviceManager", DeviceManager)
        kernel.register("window/Keymap", Keymap)
        kernel.register("window/UsbConnect", UsbConnect)
        kernel.register("window/Navigation", Navigation)
        kernel.register("window/Notes", Notes)
        kernel.register("window/JobSpooler", JobSpooler)
        kernel.register("window/ExecuteJob", ExecuteJob)
        kernel.register("window/BufferView", BufferView)
        kernel.register("window/RasterWizard", RasterWizard)
        kernel.register("window/Simulation", Simulation)

        kernel.register("window/default/Controller", Controller)
        kernel.register("window/default/Preferences", Preferences)
        kernel.register("window/tcp/Controller", TCPController)
        kernel.register("window/file/Controller", FileOutput)
        kernel.register("window/lhystudios/Preferences", LhystudiosDriverGui)
        kernel.register("window/lhystudios/Controller", LhystudiosControllerGui)
        kernel.register(
            "window/lhystudios/AccelerationChart", LhystudiosAccelerationChart
        )
        kernel.register("window/moshi/Preferences", MoshiDriverGui)
        kernel.register("window/moshi/Controller", MoshiControllerGui)

        context = kernel.root

        @kernel.console_option(
            "path",
            "p",
            type=str,
            default="/",
            help=_("Context Path at which to open the window"),
        )
        @kernel.console_command(
            "window", output_type="window", help=_("Base window command")
        )
        def window_base(channel, _, path=None, remainder=None, **kwargs):
            """
            Opens a MeerK40t window or provides information. This command is restricted to use with the wxMeerK40t gui.
            This also allows use of a -p flag that sets the context path for this window to operate at. This should
            often be restricted to where the windows are typically opened since their function and settings usually
            depend on the context used. The default root path is "/". Eg. "window -p / open Settings"
            """
            context = kernel.root
            if path is None:
                path = context
            else:
                path = kernel.get_context(path)

            if remainder is None:
                channel(_("----------"))
                channel(_("Loaded Windows in Context %s:") % str(context.path))
                for i, name in enumerate(context.opened):
                    if not name.startswith("window"):
                        continue
                    module = context.opened[name]
                    channel(_("%d: %s as type of %s") % (i + 1, name, type(module)))

                channel(_("----------"))
                channel(_("Loaded Windows in Device %s:") % str(path.path))
                for i, name in enumerate(path.opened):
                    if not name.startswith("window"):
                        continue
                    module = path.opened[name]
                    channel(_("%d: %s as type of %s") % (i + 1, name, type(module)))
                channel(_("----------"))
            return "window", path

        @kernel.console_command(
            "list",
            input_type="window",
            output_type="window",
            help=_("List available windows."),
        )
        def window_list(channel, _, data, **kwargs):
            channel(_("----------"))
            channel(_("Windows Registered:"))
            for i, name in enumerate(context.match("window")):
                name = name[7:]
                if "/" in name:
                    channel("%d: Specific Window: %s" % (i + 1, name))
                else:
                    channel("%d: %s" % (i + 1, name))
            return "window", data

        @kernel.console_option(
            "driver",
            "d",
            type=bool,
            action="store_true",
            help=_("Load Driver Specific Window"),
        )
        @kernel.console_option(
            "output",
            "o",
            type=bool,
            action="store_true",
            help=_("Load Output Specific Window"),
        )
        @kernel.console_option(
            "source",
            "s",
            type=str,
            help=_("Specify source window type"),
        )
        @kernel.console_argument("window", type=str, help=_("window to be opened"))
        @kernel.console_command(
            ("open", "toggle"),
            input_type="window",
            help=_("open/toggle the supplied window"),
        )
        def window_open(
            command,
            channel,
            _,
            data,
            window=None,
            driver=False,
            output=False,
            source=None,
            args=(),
            **kwargs
        ):
            path = data
            try:
                parent = context.gui
            except AttributeError:
                parent = None
            window_uri = "window/%s" % window
            context.root.setting(str, "active", "0")
            active = context.root.active
            if source is not None:
                active = source
            if output or driver:
                # Specific class subwindow
                try:
                    _spooler, _input_driver, _output = context.registered[
                        "device/%s" % active
                    ]
                except KeyError:
                    channel(_("Device not found."))
                    return
                if output:
                    q = _output
                elif driver:
                    q = _input_driver
                else:
                    q = _input_driver
                t = "default"
                m = "/"
                if q is not None:
                    obj = q
                    try:
                        t = obj.type
                        m = obj.context.path
                    except AttributeError:
                        pass
                path = context.get_context(m)
                window_uri = "window/%s/%s" % (t, window)
                if window_uri not in context.registered:
                    window_uri = "window/%s/%s" % ("default", window)

            def window_open(*a, **k):
                path.open(window_uri, parent, *args)

            def window_close(*a, **k):
                path.close(window_uri, *args)

            if command == "open":
                if window_uri in context.registered:
                    kernel.run_later(window_open, None)
                    channel(_("Window Opened."))
                else:
                    channel(_("No such window as %s" % window))
                    raise SyntaxError
            else:
                if window_uri in context.registered:
                    try:
                        w = path.opened[window_uri]
                        kernel.run_later(window_close, None)
                        channel(_("Window Closed."))
                    except KeyError:
                        kernel.run_later(window_open, None)
                        channel(_("Window Opened."))
                else:
                    channel(_("No such window as %s" % window))
                    raise SyntaxError

        @kernel.console_argument("window", type=str, help=_("window to be closed"))
        @kernel.console_command(
            "close",
            input_type="window",
            output_type="window",
            help=_("close the supplied window"),
        )
        def window_close(channel, _, data, window=None, args=(), **kwargs):
            path = data
            try:
                parent = context.gui if hasattr(context, "gui") else None
                kernel.run_later(
                    lambda e: path.close("window/%s" % window, parent, *args), None
                )
                channel(_("Window closed."))
            except (KeyError, ValueError):
                channel(_("No such window as %s" % window))
            except IndexError:
                raise SyntaxError

        @kernel.console_argument("window", type=str, help=_("window to be reset"))
        @kernel.console_command(
            "reset",
            input_type="window",
            output_type="window",
            help=_("reset the supplied window, or '*' for all windows"),
        )
        def window_reset(channel, _, data, window=None, **kwargs):
            if kernel._config is not None:
                for context in list(kernel.contexts):
                    if context.startswith("window"):
                        del kernel.contexts[context]
                kernel._config.DeleteGroup("window")

        @kernel.console_command("refresh", help=_("Refresh the main wxMeerK40 window"))
        def scene_refresh(command, channel, _, **kwargs):
            context.signal("refresh_scene")
            context.signal("rebuild_tree")
            channel(_("Refreshed."))

    def initialize(self, *args, **kwargs):
        context = self.context
        kernel = context.kernel

        try:  # pyinstaller internal location
            _resource_path = os.path.join(sys._MEIPASS, "locale")
            wx.Locale.AddCatalogLookupPathPrefix(_resource_path)
        except Exception:
            pass

        try:  # Mac py2app resource
            _resource_path = os.path.join(os.environ["RESOURCEPATH"], "locale")
            wx.Locale.AddCatalogLookupPathPrefix(_resource_path)
        except Exception:
            pass

        wx.Locale.AddCatalogLookupPathPrefix("locale")

        # Default Locale, prepended. Check this first.
        basepath = os.path.abspath(os.path.dirname(sys.argv[0]))
        localedir = os.path.join(basepath, "locale")
        wx.Locale.AddCatalogLookupPathPrefix(localedir)

        kernel.translation = wx.GetTranslation
        kernel.set_config(wx.FileConfig(kernel.profile))
        context.app = self  # Registers self as kernel.app

        context.setting(int, "language", None)
        context.register("control/Delete Settings", self.clear_control)
        language = context.language
        if language is not None and language != 0:
            self.update_language(language)

    def clear_control(self):
        kernel = self.context.kernel
        if kernel._config is not None:
            kernel._config.DeleteAll()
            kernel._config = None
            kernel.shutdown()

    def update_language(self, lang):
        """
        Update language to the requested language.
        """
        context = self.context
        try:
            language_code, language_name, language_index = supported_languages[lang]
        except (IndexError, ValueError):
            return
        context.language = lang

        if self.locale:
            assert sys.getrefcount(self.locale) <= 2
            del self.locale
        self.locale = wx.Locale(language_index)
        # wxWidgets is broken. IsOk()==false and pops up error dialog, but it translates fine!
        if self.locale.IsOk() or "linux" in sys.platform:
            self.locale.AddCatalog("meerk40t")
        else:
            self.locale = None
        context.signal("language", (lang, language_code, language_name, language_index))


# end of class MeerK40tGui
def send_file_to_developers(filename):
    """
    Sends crash log to a server using rfc1341 7.2 The multipart Content-Type
    https://www.w3.org/Protocols/rfc1341/7_2_Multipart.html

    :param filename: filename to send. (must be text/plain)
    :return:
    """
    import socket

    with open(filename, "r") as f:
        data = f.read()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ipaddr = socket.gethostbyname("api.anonfiles.com")
        s.connect((ipaddr, 80))
        boundary = "----------------meerk40t-boundary"
        file_head = list()
        file_head.append("--" + boundary)
        file_head.append(
            'Content-Disposition: form-data; name="file"; filename="%s"' % filename
        )
        file_head.append("Content-Type: text/plain")
        file_head.append("")
        part = "\x0D\x0A".join(file_head)
        terminal = "--" + boundary + "--"
        payload = "\x0D\x0A".join((part, data, terminal, ""))
        http_req = list()
        http_req.append("POST /upload?token=630f908431136ef4 HTTP/1.1")
        http_req.append("Host: api.anonfiles.com")
        http_req.append("User-Agent: meerk40t/0.0.1")
        http_req.append("Accept: */*")
        http_req.append("Content-Length: %d" % (len(payload)))
        http_req.append("Content-Type: multipart/form-data; boundary=%s" % boundary)
        http_req.append("")
        header = "\x0D\x0A".join(http_req)
        request = "\x0D\x0A".join((header, payload))
        s.send(bytes(request, "utf-8"))
        response = s.recv(4096)
        response = response.decode("utf-8")
        print(response)
        s.close()
    if response is None or len(response) == 0:
        http_code = "No Response."
    else:
        http_code = response.split("\n")[0]

    if http_code.startswith("HTTP/1.1 200 OK"):
        http_code = response.split("\n")[0]
        dlg = wx.MessageDialog(
            None,
            _("We got your message. Thank you for helping\n\n") + str(http_code),
            _("Thanks"),
            wx.OK,
        )
        dlg.ShowModal()
        dlg.Destroy()
    else:
        MEERK40T_ISSUES = "https://github.com/meerk40t/meerk40t/issues"
        dlg = wx.MessageDialog(
            None,
            _(
                "We're sorry, that didn't work. Raise an issue on the github please.\n\n The log file will be in your working directory.\n"
            )
            + MEERK40T_ISSUES
            + "\n\n"
            + str(http_code),
            _("Thanks"),
            wx.OK,
        )
        dlg.ShowModal()
        dlg.Destroy()


def handleGUIException(exc_type, exc_value, exc_traceback):
    """
    Handler for errors. Save error to a file, and create dialog.

    :param exc_type:
    :param exc_value:
    :param exc_traceback:
    :return:
    """
    wxversion = "wx"
    try:
        wxversion = wx.version()
    except:
        pass

    error_log = "MeerK40t crash log. Version: %s on %s - %s\n" % (
        MEERK40T_VERSION,
        sys.platform,
        wxversion,
    )
    error_log += "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(error_log)
    try:
        import datetime

        filename = "MeerK40t-{date:%Y-%m-%d_%H_%M_%S}.txt".format(
            date=datetime.datetime.now()
        )
    except Exception:  # I already crashed once, if there's another here just ignore it.
        filename = "MeerK40t-Crash.txt"

    try:
        with open(filename, "w") as file:
            # Crash logs are not translated.
            file.write(error_log)
            print(file)
    except Exception:  # I already crashed once, if there's another here just ignore it.
        pass

    # Ask to send file.
    message = _(
        """
    Good news MeerK40t User! MeerK40t encountered an crash!

    You now have the ability to help meerk40t's development by sending us the log.

    Send the following data to the MeerK40t team?
    ------
    """
    )
    message += error_log
    answer = wx.MessageBox(
        message, _("Crash Detected! Send Log?"), wx.YES_NO | wx.CANCEL, None
    )
    if answer == wx.YES:
        send_file_to_developers(filename)


def _update_ribbon_artprovider_for_dark_mode(provider: RB.RibbonArtProvider) -> None:
    def _set_ribbon_colour(
        provider: RB.RibbonArtProvider, art_id_list: list, colour: wx.Colour
    ) -> None:
        for id_ in art_id_list:
            provider.SetColour(id_, colour)

    TEXTCOLOUR = wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNTEXT)

    BTNFACE_HOVER = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_HIGHLIGHT))
    INACTIVE_BG = copy.copy(
        wx.SystemSettings().GetColour(wx.SYS_COLOUR_INACTIVECAPTION)
    )
    INACTIVE_TEXT = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_GRAYTEXT))
    BTNFACE = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNFACE))
    BTNFACE_HOVER = BTNFACE_HOVER.ChangeLightness(50)

    texts = [
        RB.RIBBON_ART_BUTTON_BAR_LABEL_COLOUR,
        RB.RIBBON_ART_PANEL_LABEL_COLOUR,
    ]
    try:  # wx 4.0 compat, not supported on that
        texts.extend(
            [
                RB.RIBBON_ART_TAB_ACTIVE_LABEL_COLOUR,
                RB.RIBBON_ART_TAB_HOVER_LABEL_COLOUR,
            ]
        )
        _set_ribbon_colour(provider, [RB.RIBBON_ART_TAB_LABEL_COLOUR], INACTIVE_TEXT)
    except AttributeError:
        _set_ribbon_colour(provider, [RB.RIBBON_ART_TAB_LABEL_COLOUR], TEXTCOLOUR)
        pass
    _set_ribbon_colour(provider, texts, TEXTCOLOUR)

    backgrounds = [
        RB.RIBBON_ART_BUTTON_BAR_HOVER_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_BUTTON_BAR_HOVER_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_TOP_GRADIENT_COLOUR,
        RB.RIBBON_ART_PANEL_LABEL_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PANEL_LABEL_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_PANEL_HOVER_LABEL_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PANEL_HOVER_LABEL_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_TAB_HOVER_BACKGROUND_COLOUR,
        RB.RIBBON_ART_TAB_ACTIVE_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_TAB_ACTIVE_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PAGE_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_PAGE_BACKGROUND_TOP_GRADIENT_COLOUR,
        RB.RIBBON_ART_PAGE_HOVER_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PAGE_HOVER_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_TAB_CTRL_BACKGROUND_COLOUR,
        RB.RIBBON_ART_TAB_CTRL_BACKGROUND_GRADIENT_COLOUR,
    ]
    _set_ribbon_colour(provider, backgrounds, BTNFACE)
    _set_ribbon_colour(
        provider,
        [
            RB.RIBBON_ART_TAB_HOVER_BACKGROUND_COLOUR,
            RB.RIBBON_ART_TAB_HOVER_BACKGROUND_GRADIENT_COLOUR,
            RB.RIBBON_ART_TAB_HOVER_BACKGROUND_TOP_COLOUR,
            RB.RIBBON_ART_TAB_HOVER_BACKGROUND_TOP_GRADIENT_COLOUR,
        ],
        INACTIVE_BG,
    )


sys.excepthook = handleGUIException
