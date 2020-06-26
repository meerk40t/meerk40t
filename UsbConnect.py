import wx

from Kernel import Module

_ = wx.GetTranslation


class UsbConnect(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: Terminal.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.FRAME_FLOAT_ON_PARENT
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((915, 424))
        self.text_main = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_BESTWRAP | wx.TE_MULTILINE | wx.TE_READONLY)
        self.text_entry = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TEXT_ENTER, self.on_entry, self.text_entry)
        # end wxGlade
        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.pipe = None

    def on_close(self, event):
        self.device.close('window', 'UsbConnect')
        event.Skip()

    def initialize(self, channel=None):
        self.device.close('window', 'UsbConnect')
        self.Show()
        self.device.add_watcher('usb', self.update_text)

    def finalize(self, channel=None):
        self.device.remove_watcher('usb', self.update_text)
        try:
            self.Close()
        except RuntimeError:
            pass

    def shutdown(self, channel=None):
        try:
            self.Close()
        except RuntimeError:
            pass

    def update_text(self, text):
        wx.CallAfter(self.update_text_gui, text + '\n')

    def update_text_gui(self, text):
        try:
            self.text_main.AppendText(text)
        except RuntimeError:
            pass

    def __set_properties(self):
        # begin wxGlade: Terminal.__set_properties
        self.SetTitle(_('UsbConnect'))
        self.text_entry.SetFocus()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Terminal.__do_layout
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.text_main, 20, wx.EXPAND, 0)
        sizer_2.Add(self.text_entry, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_2)
        self.Layout()
        # end wxGlade

    def on_entry(self, event):  # wxGlade: Terminal.<event_handler>
        if self.pipe is not None:
            self.pipe.write(self.text_entry.GetValue() + "\n")
            self.text_entry.SetValue('')
        event.Skip()
