import wx

from meerk40t.gui.icons import icons8_usb_connector_50
from meerk40t.gui.mwindow import MWindow

_ = wx.GetTranslation


class UsbConnectPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        self.text_main = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_BESTWRAP | wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.text_entry = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TEXT_ENTER, self.on_entry, self.text_entry)
        # end wxGlade
        self.pipe = None
        self._active_when_loaded = None

    def pane_show(self):
        active = self.context.device.active
        self._active_when_loaded = active
        self.context.channel(f"{active}/usb", buffer_size=500).watch(self.update_text)

    def pane_hide(self):
        active = self._active_when_loaded
        self.context.channel(f"{active}/usb").unwatch(self.update_text)

    def update_text(self, text):
        if not wx.IsMainThread():
            wx.CallAfter(self.update_text_gui, text + "\n")
        else:
            self.update_text_gui(text + "\n")

    def update_text_gui(self, text):
        try:
            self.text_main.AppendText(text)
        except RuntimeError:
            pass

    def __set_properties(self):
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

    def on_entry(self, event):
        if self.pipe is not None:
            self.pipe.write(self.text_entry.GetValue() + "\n")
            self.text_entry.SetValue("")
        event.Skip()


class UsbConnect(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(915, 424, *args, **kwds)

        self.panel = UsbConnectPanel(self, wx.ID_ANY, context=self.context)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_usb_connector_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Terminal.__set_properties
        self.SetTitle(_("UsbConnect"))

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def submenu():
        return "Device-Control", "USB-Connection"
