import wx

from .icons import icons8_comments_50
from .mwindow import MWindow

_ = wx.GetTranslation


class BufferViewPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.text_buffer_length = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_buffer_info = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_CHARWRAP | wx.TE_MULTILINE
        )

        self.__set_properties()
        self.__do_layout()

    def pane_show(self):
        buffer = self.context.device.viewbuffer
        if buffer is None:
            buffer = _("Could not find buffer.\n")

        self.text_buffer_length = self.text_buffer_length.SetValue(str(len(buffer)))
        self.text_buffer_info = self.text_buffer_info.SetValue(buffer)

    def __set_properties(self):
        self.text_buffer_length.SetMinSize((165, 23))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: BufferView.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        label_8 = wx.StaticText(self, wx.ID_ANY, _("Buffer"))
        sizer_5.Add(label_8, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_5.Add(self.text_buffer_length, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_5, 0, wx.EXPAND, 0)
        sizer_1.Add(self.text_buffer_info, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    # end of class BufferView


class BufferView(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(697, 586, *args, **kwds)
        self.panel = BufferViewPanel(self, wx.ID_ANY, context=self.context)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_comments_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: BufferView.__set_properties
        self.SetTitle(_("BufferView"))

    def window_preserve(self):
        return False

    def window_open(self):
        self.context.close(self.name)
        self.panel.pane_show()

    @staticmethod
    def submenu():
        return "Device-Control", "Buffer"
