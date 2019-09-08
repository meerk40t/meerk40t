import wx


class UsbConnect(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: UsbConnect.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((915, 424))
        self.usblog_text = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_WORDWRAP)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade
        self.project = None

    def set_project(self, project):
        self.project = project
        self.usblog_text.SetValue(self.project.controller.device_log)
        self.project.controller.usblog_listener = self.update_log

    def update_log(self, text):
        try:
            self.usblog_text.AppendText(text)
        except RuntimeError:
            self.project.controller.usblog_listener = None

    def __set_properties(self):
        # begin wxGlade: UsbConnect.__set_properties
        self.SetTitle("UsbConnect")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: UsbConnect.__do_layout
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.usblog_text, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_2)
        self.Layout()
        # end wxGlade
