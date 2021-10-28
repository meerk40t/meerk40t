import copy

import wx
from wx import aui, ID_OPEN, ID_SAVE
import wx.ribbon as RB

from .icons import (
    icons8_connected_50,
    icons8_opened_folder_50,
    icons8_save_50,
    icons8_laser_beam_52,
    icons8_laser_beam_hazard2_50,
    icons8_fantasy_50,
    icons8_comments_50,
    icons8_console_50,
    icons8_move_50,
    icons8_camera_50,
    icons8_roll_50,
    icons8_keyboard_50,
    icons8_administrative_tools_50,
    icons8_computer_support_50,
    icons8_manager_50,
    icons8_emergency_stop_button_50,
    icons8_pause_50,
    icons8_route_50,
)
from .mwindow import MWindow

ID_JOB = wx.NewId()
ID_SIM = wx.NewId()
ID_RASTER = wx.NewId()
ID_NOTES = wx.NewId()
ID_CONSOLE = wx.NewId()
ID_NAV = wx.NewId()
ID_CAMERA = wx.NewId()
ID_CAMERA1 = wx.NewId()
ID_CAMERA2 = wx.NewId()
ID_CAMERA3 = wx.NewId()
ID_CAMERA4 = wx.NewId()
ID_CAMERA5 = wx.NewId()
ID_SPOOLER = wx.NewId()
ID_CONTROLLER = wx.NewId()
ID_PAUSE = wx.NewId()
ID_STOP = wx.NewId()
ID_DEVICES = wx.NewId()
ID_CONFIGURATION = wx.NewId()
ID_SETTING = wx.NewId()
ID_KEYMAP = wx.NewId()
ID_ROTARY = wx.NewId()

from ..kernel import STATE_BUSY


_ = wx.GetTranslation


def register_panel(window, context):
    ribbon = RibbonPanel(window, wx.ID_ANY, context=context)

    pane = (
        aui.AuiPaneInfo()
        .Name("ribbon")
        .Top()
        .RightDockable(False)
        .LeftDockable(False)
        .MinSize(300, 120)
        .FloatingSize(640, 120)
        .Caption(_("Ribbon"))
        .CaptionVisible(not context.pane_lock)
    )
    pane.dock_proportion = 640
    pane.control = ribbon

    window.on_pane_add(pane)
    context.register("pane/ribbon", pane)


class RibbonPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

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

        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(self._ribbon, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # self._ribbon
        self.pipe_state = None
        self.ribbon_position_units = self.context.units_index

    @property
    def is_dark(self):
        return wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127

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
        # self.Bind(RB.EVT_RIBBONBAR_TOGGLED, self.ribbon_bar_toggle)

        # ==========
        # PROJECT PANEL
        # ==========

        self.toolbar_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            "" if self.is_dark else _("Project"),
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

        toolbar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda e: self.context(".dialog_load\n"),
            id=ID_OPEN,
        )
        toolbar.Bind(
            RB.EVT_RIBBONBUTTONBAR_CLICKED,
            lambda e: self.context(".dialog_save\n"),
            id=ID_SAVE,
        )
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
            "" if self.is_dark else _("Control"),
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
        # SETTINGS PANEL
        # ==========
        self.settings_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            "" if self.is_dark else _("Preferences"),
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

        self._ribbon.Realize()

    def on_click_stop(self, event=None):
        self.context("estop\n")

    def on_click_pause(self, event=None):
        self.context("pause\n")

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
        self.context("window toggle CameraInterface %d\n" % v)

    def on_pipe_state(self, origin, state):
        if state == self.pipe_state:
            return
        self.toolbar_button_bar.ToggleButton(ID_PAUSE, state == STATE_BUSY)

    def initialize(self):
        self.context.listen("pipe;thread", self.on_pipe_state)

    def finalize(self):
        self.context.unlisten("pipe;thread", self.on_pipe_state)


class Ribbon(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(423, 131, *args, **kwds)

        self.panel = RibbonPanel(self, wx.ID_ANY, context=self.context)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_connected_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Ribbon"))

    def window_open(self):
        try:
            self.panel.initialize()
        except AttributeError:
            pass

    def window_close(self):
        try:
            self.panel.finalize()
        except AttributeError:
            pass


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
