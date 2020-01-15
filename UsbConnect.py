import wx

_ = wx.GetTranslation


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
        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.project = None
        self.dirty = False
        self.append_text = ""

    def set_project(self, project):
        self.project = project
        self.project.setting(str, "_device_log", '')
        self.usblog_text.SetValue(self.project._device_log)

        self.project.listen("usb_log", self.update_log)

    def on_close(self, event):
        self.project.unlisten("usb_log", self.update_log)
        try:
            del self.project.windows["usbconnect"]
        except KeyError:
            pass
        self.project = None
        event.Skip()  # Call destroy as regular.

    def update_log(self, text):
        self.append_text += text
        self.post_update()

    def post_update_on_gui_thread(self):
        if self.project is None:
            return
        try:
            self.usblog_text.AppendText(self.append_text)
            self.append_text = ""
        except RuntimeError:
            self.project.unlisten("usb_log", self.update_log)
        self.dirty = False

    def post_update(self):
        if not self.dirty:
            self.dirty = True
            wx.CallAfter(self.post_update_on_gui_thread)

    def __set_properties(self):
        # begin wxGlade: UsbConnect.__set_properties
        self.SetTitle(_("UsbConnect"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: UsbConnect.__do_layout
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.usblog_text, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_2)
        self.Layout()
        # end wxGlade
