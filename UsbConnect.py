import wx

from Kernel import Module

_ = wx.GetTranslation


class UsbConnect(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: UsbConnect.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((915, 424))
        self.usblog_text = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_WORDWRAP)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def initialize(self):
        self.device.module_instance_close(self.name)
        self.Show()
        if self.device.is_root():
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(False)
            dlg = wx.MessageDialog(None, _("You do not have a selected device."),
                                   _("No Device Selected."), wx.OK | wx.ICON_WARNING)
            result = dlg.ShowModal()
            dlg.Destroy()
            return
        self.device.listen('pipe;device_log', self.update_log)
        self.usblog_text.SetValue(self.device._device_log)
        self.usblog_text.AppendText("\n")

    def shutdown(self,  channel):
        self.Close()

    def on_close(self, event):
        if self.device is not None:
            self.device.unlisten('pipe;device_log', self.update_log)
        self.device.module_instance_remove(self.name)
        event.Skip()  # Call destroy as regular.

    def update_log(self, text):
        if self.device is None:
            return
        try:
            device = self.device
            try:
                self.usblog_text.SetValue(device._device_log)
                self.usblog_text.AppendText("\n")
            except RuntimeError:
                pass  # must have closed before signal hit.
        except AttributeError:
            return

    def __set_properties(self):
        self.SetTitle(_("UsbConnect"))

    def __do_layout(self):
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.usblog_text, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_2)
        self.Layout()
