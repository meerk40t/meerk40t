# -*- coding: utf-8 -*-

import os
import sys
import traceback

from .wxutils import get_key_name

try:
    import wx
except ImportError as e:
    from ..core.exceptions import Mk40tImportAbort

    raise Mk40tImportAbort("wxpython")

import wx.aui as aui

from ..main import MEERK40T_VERSION
from .file.fileoutput import FileOutput
from .groupproperties import GroupProperty
from .mwindow import MWindow
from .panes.consolepanel import Console
from .panes.devicespanel import DeviceManager
from .panes.spoolerpanel import JobSpooler
from .panes.navigationpanels import Navigation
from .panes.camerapanel import CameraInterface
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
from ..kernel import ConsoleFunction, Module
from ..svgelements import (
    Color,
    Length,
    Matrix,
    Path,
    SVGImage,
)
from .about import About
from .bufferview import BufferView
from .controller import Controller
from .executejob import ExecuteJob
from .icons import (
    icon_meerk40t,
    icons8_emergency_stop_button_50,
    icons8_gas_industry_50,
    icons8_home_filled_50,
    icons8_pause_50,
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
from .notes import Notes
from .operationproperty import OperationProperty
from .pathproperty import PathProperty
from .configuration import Configuration
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
        def run_later(command, *args):
            if wx.IsMainThread():
                command(*args)
            else:
                wx.CallAfter(command, *args)
        kernel.run_later = run_later
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
        self.DragAcceptFiles(True)

        self.renderer = LaserRender(context)
        self.working_file = None
        self._rotary_view = False
        self.pipe_state = None
        self.previous_position = None
        self.is_paused = False

        # Define Scene
        self.scene = ScenePanel(
            self.context, self, scene_name="Scene", style=wx.EXPAND | wx.WANTS_CHARS
        )
        self.widget_scene = self.scene.scene

        self._mgr = aui.AuiManager()
        self._mgr.SetFlags(self._mgr.GetFlags() | aui.AUI_MGR_LIVE_RESIZE)
        self._mgr.Bind(aui.EVT_AUI_PANE_CLOSE, self.on_pane_closed)
        self._mgr.Bind(aui.EVT_AUI_PANE_ACTIVATED, self.on_pane_active)

        # notify AUI which frame to use
        self._mgr.SetManagedWindow(self)

        self.__set_panes()
        self.__set_dialogs()

        # Menu Bar
        self.main_menubar = wx.MenuBar()
        self.__set_menubar()

        self.main_statusbar = self.CreateStatusBar(3)

        self.Bind(wx.EVT_DROP_FILES, self.on_drop_file)

        self.__set_properties()
        self.Layout()

        self.scene.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.scene.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.scene.scene_panel.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.scene.scene_panel.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.__set_titlebar()
        self.__kernel_initialize(context)

        self.Bind(wx.EVT_SIZE, self.on_size)

        self.CenterOnScreen()

    def __set_dialogs(self):
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
                spooler, input_driver, output = context.registered[
                    "device/%s" % context.root.active
                ]
                root_context = context.root
                bed_dim = context.root
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
                root_context = context.root
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

        @context.console_command("dialog_path", hidden=True)
        def path(**kwargs):
            dlg = wx.TextEntryDialog(gui, _("Enter SVG Path Data"), _("Path Entry"), "")
            dlg.SetValue("")

            if dlg.ShowModal() == wx.ID_OK:
                path = Path(dlg.GetValue())
                path.stroke = "blue"
                p = abs(path)
                context.elements.add_elem(p)
                context.classify([p])
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
                    elem.node.altered()

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
                    elem.node.altered()

        @context.console_command("dialog_fps", hidden=True)
        def fps(**kwargs):
            dlg = wx.TextEntryDialog(
                gui, _("Enter FPS Limit"), _("FPS Limit Entry"), ""
            )
            dlg.SetValue("")

            if dlg.ShowModal() == wx.ID_OK:
                fps = dlg.GetValue()
                try:
                    gui.widget_scene.set_fps(int(fps))
                except ValueError:
                    pass
            dlg.Destroy()

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

        @context.console_command("dialog_load", hidden=True)
        def load_dialog(**kwargs):
            # This code should load just specific project files rather than all importable formats.
            files = context.load_types()
            with wx.FileDialog(
                gui, _("Open"), wildcard=files, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                pathname = fileDialog.GetPath()
                gui.load(pathname)

        @context.console_command("dialog_save", hidden=True)
        def save_dialog(**kwargs):
            files = context.save_types()
            with wx.FileDialog(
                gui,
                _("Save Project"),
                wildcard=files,
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                pathname = fileDialog.GetPath()
                if not pathname.lower().endswith(".svg"):
                    pathname += ".svg"
                context.save(pathname)
                gui.working_file = pathname
                gui.save_recent(gui.working_file)

        @context.console_command("dialog_import_egv", hidden=True)
        def evg_in_dialog(**kwargs):
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
                context("egv_import %s\n" % pathname)
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
                context("egv_export %s\n" % pathname)
                return

        context.register("control/Transform", lambda: context("dialog_transform\n"))
        context.register("control/Flip", lambda: context("dialog_flip\n"))
        context.register("control/Path", lambda: context("dialog_path\n"))
        context.register("control/Fill", lambda: context("dialog_fill\n"))
        context.register("control/Stroke", lambda: context("dialog_stroke\n"))
        context.register("control/FPS", lambda: context("dialog_fps\n"))
        context.register(
            "control/Speedcode-Gear-Force", lambda: context("dialog_gear\n")
        )
        context.register("control/egv export", lambda: context("dialog_import_egv\n"))
        context.register("control/egv import", lambda: context("dialog_export_egv\n"))

    def __set_panes(self):
        self.context.setting(bool, "pane_lock", True)
        # self.notebook = wx.aui.AuiNotebook(self, -1, size=(200, 150))
        # self._mgr.AddPane(self.notebook, aui.AuiPaneInfo().CenterPane().Name("scene"))
        # self.notebook.AddPage(self.scene, "scene")
        self._mgr.AddPane(self.scene, aui.AuiPaneInfo().CenterPane().Name("scene"))

        from .panes.navigationpanels import register_panel

        register_panel(self, self.context)

        # Define Tree
        from .wxmtree import register_panel

        register_panel(self, self.context)

        # Define Laser.
        from .panes.laserpanel import register_panel

        register_panel(self, self.context)

        # Define Position
        from .panes.position import register_panel

        register_panel(self, self.context)

        # Define Ribbon
        from .wxmribbon import register_panel

        register_panel(self, self.context)

        # Define Toolbars

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
        context.listen("refresh_scene", self.on_refresh_scene)
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

        self.widget_scene.add_scenewidget(SelectionWidget(self.widget_scene))
        self.tool_container = ToolContainer(self.widget_scene)
        self.widget_scene.add_scenewidget(self.tool_container)
        self.widget_scene.add_scenewidget(RectSelectWidget(self.widget_scene))
        self.laserpath_widget = LaserPathWidget(self.widget_scene)
        self.widget_scene.add_scenewidget(self.laserpath_widget)
        self.widget_scene.add_scenewidget(
            ElementsWidget(self.widget_scene, self.renderer)
        )
        self.widget_scene.add_scenewidget(GridWidget(self.widget_scene))
        self.widget_scene.add_interfacewidget(GuideWidget(self.widget_scene))
        self.widget_scene.add_interfacewidget(ReticleWidget(self.widget_scene))

        @context.console_command("laserpath_clear", hidden=True)
        def clear_laser_path(**kwargs):
            self.laserpath_widget.clear_laserpath()

        @context.console_command(
            "theme", help=_("Theming information and assignments"), hidden=True
        )
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
        context.unlisten("refresh_scene", self.on_refresh_scene)
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

    def on_click_new(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        context = self.context
        self.working_file = None
        context.elements.clear_all()
        self.laserpath_widget.clear_laserpath()
        self.request_refresh()

    def on_click_open(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        self.context("dialog_load\n")

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
        self.context("dialog_save\n")

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
        kernel.register("window/default/Preferences", Configuration)
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

        @kernel.console_command("tooltips_enable", hidden=True)
        def tooltip_enable(command, channel, _, **kwargs):
            context.setting(bool, "disable_tool_tips", False)
            context.disable_tool_tips = False
            wx.ToolTip.Enable(not context.disable_tool_tips)

        @kernel.console_command("tooltips_disable", hidden=True)
        def tooltip_disable(command, channel, _, **kwargs):
            context.setting(bool, "disable_tool_tips", False)
            context.disable_tool_tips = True
            wx.ToolTip.Enable(not context.disable_tool_tips)

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


sys.excepthook = handleGUIException
