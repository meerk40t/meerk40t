import wx


class RasterSpeedChart(wx.Panel):
    def __init__(self, *args, **kwds):
        # begin wxGlade: RasterSpeedChart.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)

        sizer_main = wx.BoxSizer(wx.VERTICAL)

        self.list_chart = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.list_chart.AppendColumn("Speed <=", format=wx.LIST_FORMAT_LEFT, width=133)
        self.list_chart.AppendColumn("Acceleration Length", format=wx.LIST_FORMAT_LEFT, width=244)
        self.list_chart.AppendColumn("Backlash", format=wx.LIST_FORMAT_LEFT, width=142)
        self.list_chart.AppendColumn("Corner Speed", format=wx.LIST_FORMAT_LEFT, width=128)
        sizer_main.Add(self.list_chart, 10, wx.EXPAND, 0)

        self.panel_control = wx.Panel(self, wx.ID_ANY)
        sizer_main.Add(self.panel_control, 1, wx.EXPAND, 0)

        sizer_control = wx.BoxSizer(wx.HORIZONTAL)

        self.button_add = wx.Button(self.panel_control, wx.ID_ANY, "Add")
        sizer_control.Add(self.button_add, 0, 0, 0)

        self.button_remove = wx.Button(self.panel_control, wx.ID_ANY, "Remove")
        sizer_control.Add(self.button_remove, 0, 0, 0)

        self.panel_control.SetSizer(sizer_control)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.Layout()
        # end wxGlade
