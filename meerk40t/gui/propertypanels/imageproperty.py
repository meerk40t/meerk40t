import wx

from ..icons import icons8_image_50
from ..mwindow import MWindow

_ = wx.GetTranslation


class ImagePropertyPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.node = node
        self.text_dpi = wx.TextCtrl(self, wx.ID_ANY, "500")
        self.text_x = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_y = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_width = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_height = wx.TextCtrl(self, wx.ID_ANY, "")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TEXT, self.on_text_dpi, self.text_dpi)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_dpi, self.text_dpi)
        self.Bind(wx.EVT_TEXT, self.on_text_x, self.text_x)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_x, self.text_x)
        self.Bind(wx.EVT_TEXT, self.on_text_y, self.text_y)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_y, self.text_y)
        self.Bind(wx.EVT_TEXT, self.on_text_width, self.text_width)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_width, self.text_width)
        self.Bind(wx.EVT_TEXT, self.on_text_height, self.text_height)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_height, self.text_height)

        self.set_widgets()

    @staticmethod
    def accepts(node):
        if node.type == "elem image":
            return True
        return False

    def set_widgets(self, node=None):
        if node is None:
            node = self.node
        if node is None:
            return
        self.text_dpi.SetValue(str(node.dpi))
        try:
            bounds = node.bounds
            self.text_x.SetValue(str(bounds[0]))
            self.text_y.SetValue(str(bounds[1]))
            self.text_width.SetValue(str((bounds[2] - bounds[0])))
            self.text_height.SetValue(str((bounds[3] - bounds[1])))
        except AttributeError:
            pass

    def __set_properties(self):
        self.text_x.SetToolTip(_("X property of image"))
        self.text_x.Enable(False)
        self.text_y.SetToolTip(_("Y property of image"))
        self.text_y.Enable(False)
        self.text_width.SetToolTip(_("Width property of image"))
        self.text_width.Enable(False)
        self.text_height.SetToolTip(_("Height property of image"))
        self.text_height.Enable(False)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ImageProperty.__do_layout
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        label_8 = wx.StaticText(self, wx.ID_ANY, _("DPI:"))
        label_8.SetToolTip(_("Dots Per Inch"))
        sizer_6.Add(label_8, 1, 0, 0)
        sizer_6.Add(self.text_dpi, 5, 0, 0)
        sizer_8.Add(sizer_6, 1, wx.EXPAND, 0)
        label_1 = wx.StaticText(self, wx.ID_ANY, _("X:"))
        sizer_2.Add(label_1, 1, 0, 0)
        sizer_2.Add(self.text_x, 5, 0, 0)
        sizer_8.Add(sizer_2, 1, wx.EXPAND, 0)
        label_2 = wx.StaticText(self, wx.ID_ANY, _("Y:"))
        sizer_3.Add(label_2, 1, 0, 0)
        sizer_3.Add(self.text_y, 5, 0, 0)
        sizer_8.Add(sizer_3, 1, wx.EXPAND, 0)
        label_3 = wx.StaticText(self, wx.ID_ANY, _("Width:"))
        sizer_4.Add(label_3, 1, 0, 0)
        sizer_4.Add(self.text_width, 5, 0, 0)
        sizer_8.Add(sizer_4, 1, wx.EXPAND, 0)
        label_5 = wx.StaticText(self, wx.ID_ANY, _("Height:"))
        sizer_5.Add(label_5, 1, 0, 0)
        sizer_5.Add(self.text_height, 5, 0, 0)
        sizer_8.Add(sizer_5, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_8)
        self.Layout()
        self.Centre()
        # end wxGlade

    def on_text_dpi(self, event=None):  # wxGlade: ImageProperty.<event_handler>
        new_step = float(self.text_dpi.GetValue())
        self.node.dpi = new_step

    def on_text_x(self, event):  # wxGlade: ImageProperty.<event_handler>
        event.Skip()

    def on_text_y(self, event):  # wxGlade: ImageProperty.<event_handler>
        event.Skip()

    def on_text_width(self, event):  # wxGlade: ImageProperty.<event_handler>
        event.Skip()

    def on_text_height(self, event):  # wxGlade: ImageProperty.<event_handler>
        event.Skip()


class ImageProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(276, 218, *args, **kwds)

        self.panel = ImagePropertyPanel(
            self, wx.ID_ANY, context=self.context, node=node
        )
        self.add_module_delegate(self.panel)
        # begin wxGlade: ImageProperty.__set_properties
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_image_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Image Properties"))

    def restore(self, *args, node=None, **kwds):
        self.panel.set_widgets(node)

    def window_preserve(self):
        return False

    def window_menu(self):
        return False
