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

from ..icons import (icons8_camera_50, icons8_connected_50, icons8_move_50,
                     icons8_route_50)

_ = wx.GetTranslation


class ControlTools(wx.ScrolledWindow):
    def __init__(self, *args, gui=None, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.ScrolledWindow.__init__(self, *args, **kwds)
        self.context = context
        self.gui = gui
        self.SetScrollRate(10, 10)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        toolbar = ControlToolBar(self, wx.ID_ANY, gui=self.gui, context=self.context)
        sizer.Add(toolbar, 0, 0, 0)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()


class ControlToolBar(wx.ToolBar):
    def __init__(self, *args, context, gui, **kwds):
        # begin wxGlade: wxToolBar.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.ToolBar.__init__(self, *args, **kwds)
        self.context = context
        self.gui = gui

        self.AddTool(
            ID_NAV,
            _("Navigation"),
            icons8_move_50.GetBitmap(),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            _("Opens new project"),
            "",
        )
        self.Bind(
            wx.EVT_TOOL,
            lambda v: self.context("window toggle Navigation\n"),
            id=ID_NAV,
        )
        if self.context.has_feature("modifier/Camera"):
            self.AddTool(
                ID_CAMERA,
                _("Camera"),
                icons8_camera_50.GetBitmap(),
                wx.NullBitmap,
                wx.ITEM_NORMAL,
                _("Opens Camera Window"),
                "",
            )
            self.Bind(wx.EVT_TOOL, gui.on_camera_click, id=ID_CAMERA)
            # self.Bind(
            #     RB.EVT_RIBBONBUTTONBAR_DROPDOWN_CLICKED,
            #     self.on_camera_dropdown,
            #     id=ID_CAMERA,
            # )
            # self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA1)
            # self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA2)
            # self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA3)
            # self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA4)
            # self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA5)

        self.AddTool(
            ID_SPOOLER,
            _("Spooler"),
            icons8_route_50.GetBitmap(),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            _("Opens Spooler Window"),
            "",
        )
        self.Bind(
            wx.EVT_TOOL,
            lambda v: self.context("window toggle JobSpooler\n"),
            id=ID_SPOOLER,
        )
        self.AddTool(
            ID_CONTROLLER,
            _("Controller"),
            icons8_connected_50.GetBitmap(),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            _("Opens Controller Window"),
            "",
        )
        self.Bind(
            wx.EVT_TOOL,
            lambda v: self.context("window toggle -o Controller\n"),
            id=ID_CONTROLLER,
        )
        self.__set_properties()
        self.__do_layout()
        # Tool Bar end

    def __set_properties(self):
        # begin wxGlade: wxToolBar.__set_properties
        self.Realize()
        self.SetLabel(_("Control"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: wxToolBar.__do_layout
        pass
        # end wxGlade
