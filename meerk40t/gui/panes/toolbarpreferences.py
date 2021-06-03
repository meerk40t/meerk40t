import wx

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

from ..icons import (
    icons8_administrative_tools_50,
    icons8_computer_support_50,
    icons8_keyboard_50,
    icons8_manager_50,
    icons8_roll_50,
)

_ = wx.GetTranslation


class PreferencesTools(wx.ScrolledWindow):
    def __init__(self, *args, gui=None, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.ScrolledWindow.__init__(self, *args, **kwds)
        self.context = context
        self.gui = gui
        self.SetScrollRate(10, 10)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        toolbar = PreferencesToolBar(
            self, wx.ID_ANY, gui=self.gui, context=self.context
        )
        sizer.Add(toolbar, 0, 0, 0)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()


class PreferencesToolBar(wx.ToolBar):
    def __init__(self, *args, context, gui, **kwds):
        # begin wxGlade: wxToolBar.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.ToolBar.__init__(self, *args, **kwds)
        self.context = context
        self.gui = gui

        self.AddTool(
            ID_DEVICES,
            _("Devices"),
            icons8_manager_50.GetBitmap(),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            "Opens Device Manager",
            "",
        )
        self.Bind(
            wx.EVT_TOOL,
            lambda v: self.context("window toggle DeviceManager\n"),
            id=ID_DEVICES,
        )

        self.AddTool(
            ID_CONFIGURATION,
            _("Config"),
            icons8_computer_support_50.GetBitmap(),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            "Opens Configuration Window",
            "",
        )
        self.Bind(
            wx.EVT_TOOL,
            lambda v: self.context("window toggle -d Preferences\n"),
            id=ID_CONFIGURATION,
        )

        self.AddTool(
            ID_SETTING,
            _("Settings"),
            icons8_administrative_tools_50.GetBitmap(),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            "Opens Settings Window",
            "",
        )
        self.Bind(
            wx.EVT_TOOL,
            lambda v: self.context("window toggle Settings\n"),
            id=ID_SETTING,
        )

        self.AddTool(
            ID_KEYMAP,
            _("Keymap"),
            icons8_keyboard_50.GetBitmap(),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            "Opens Keymap Window",
            "",
        )
        self.Bind(
            wx.EVT_TOOL,
            lambda v: self.context("window toggle Keymap\n"),
            id=ID_KEYMAP,
        )
        self.AddTool(
            ID_ROTARY,
            _("Rotary"),
            icons8_roll_50.GetBitmap(),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            "Opens Rotary Window",
            "",
        )
        self.Bind(
            wx.EVT_TOOL,
            lambda v: self.context("window -p rotary/1 toggle Rotary\n"),
            id=ID_ROTARY,
        )

        # self.SetBackgroundColour((200, 225, 250, 255))
        self.__set_properties()
        self.__do_layout()
        # Tool Bar end

    def __set_properties(self):
        # begin wxGlade: wxToolBar.__set_properties
        self.Realize()
        self.SetLabel("Preferences")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: wxToolBar.__do_layout
        pass
        # end wxGlade
