import wx

from icons import icons8_stop_sign_50, icon_meerk40t
from Kernel import *

_ = wx.GetTranslation


class Shutdown(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: Shutdown.__init__
        kwds["style"] = kwds.get("style", 0) | wx.CAPTION | wx.CLIP_CHILDREN | wx.FRAME_TOOL_WINDOW | wx.RESIZE_BORDER
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((413, 573))
        self.text_shutdown = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.button_stop = wx.BitmapButton(self, wx.ID_ANY, icons8_stop_sign_50.GetBitmap())
        self.button_reload = wx.BitmapButton(self, wx.ID_ANY, icon_meerk40t.GetBitmap())

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_stop, self.button_stop)
        self.Bind(wx.EVT_BUTTON, self.on_button_reload, self.button_reload)
        # end wxGlade

        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.is_closed = False

    def initialize(self):
        self.device.close('window', self.name)
        self.Show()
        self.device.setting(bool, "autoclose_shutdown", True)
        self.device.device_root.add_watcher('shutdown', self.update_text)

    def on_close(self, event):
        self.is_closed = True
        self.device.remove('window', self.name)
        self.device.remove_watcher('shutdown', self.update_text)
        event.Skip()  # Call destroy as regular.

    def detach(self, device, channel=None):
        """
        Override detach to prevent detaching if autoclose shutdown is False.
        :param device:
        :return:
        """
        if self.device.autoclose_shutdown:
            Module.detach(self, device, channel)

    def shutdown(self,  channel):
        self.is_closed = True
        self.Close()

    def update_text(self, text):
        if not self.is_closed:
            wx.CallAfter(self.update_text_gui, text + '\n')

    def update_text_gui(self, text):
        if not self.is_closed:
            self.text_shutdown.AppendText(text)

    def __set_properties(self):
        # begin wxGlade: Shutdown.__set_properties
        self.SetTitle(_("Shutdown"))
        self.button_stop.SetMinSize((108, 108))
        self.button_reload.SetSize(self.button_reload.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Shutdown.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(self.text_shutdown, 5, wx.EXPAND, 0)
        sizer_2.Add(self.button_stop, 0, 0, 0)
        sizer_2.Add(self.button_reload, 0, 0, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def on_button_stop(self, event):  # wxGlade: Shutdown.<event_handler>
        wx.CallAfter(self.Close, True)

    def on_button_reload(self, event):  # wxGlade: Shutdown.<event_handler>
        # self.device.module_instance_open('MeerK40t', None, -1, "")
        self.Close()
