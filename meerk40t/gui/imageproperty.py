import wx

from ..svgelements import Matrix
from .mwindow import MWindow

_ = wx.GetTranslation


class ImageProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(276, 218, *args, **kwds)
        self.element_node = node
        self.element = node.object
        self.spin_step_size = wx.SpinCtrl(self, wx.ID_ANY, "1", min=1, max=63)
        self.combo_dpi = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=[
                "1000",
                "500",
                "333",
                "250",
                "200",
                "166",
                "142",
                "125",
                "111",
                "100",
            ],
            style=wx.CB_DROPDOWN,
        )
        self.text_x = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_y = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_width = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_height = wx.TextCtrl(self, wx.ID_ANY, "")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_SPINCTRL, self.on_spin_step, self.spin_step_size)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_step, self.spin_step_size)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_dpi, self.combo_dpi)
        self.Bind(wx.EVT_TEXT, self.on_text_x, self.text_x)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_x, self.text_x)
        self.Bind(wx.EVT_TEXT, self.on_text_y, self.text_y)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_y, self.text_y)
        self.Bind(wx.EVT_TEXT, self.on_text_width, self.text_width)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_width, self.text_width)
        self.Bind(wx.EVT_TEXT, self.on_text_height, self.text_height)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_height, self.text_height)

    def restore(self, *args, node=None, **kwds):
        self.element_node = node
        self.element = node.object
        self.set_widgets()

    def window_open(self):
        self.set_widgets()

    def set_widgets(self):
        try:
            self.spin_step_size.SetValue(self.element.values["raster_step"])
            self.combo_dpi.SetSelection(self.spin_step_size.GetValue() - 1)
        except KeyError:
            self.spin_step_size.SetValue(1)  # Default value
            self.combo_dpi.SetSelection(self.spin_step_size.GetValue() - 1)
        except AttributeError:
            self.combo_dpi.Enable(False)
            self.spin_step_size.Enable(False)

        try:
            bounds = self.element.bbox()
            self.text_x.SetValue("%f" % bounds[0])
            self.text_y.SetValue("%f" % bounds[1])
            self.text_width.SetValue("%f" % (bounds[2] - bounds[0]))
            self.text_height.SetValue("%f" % (bounds[3] - bounds[1]))
        except AttributeError:
            pass

    def __set_properties(self):
        # begin wxGlade: ImageProperty.__set_properties
        self.SetTitle(_("Image Properties"))
        self.spin_step_size.SetMinSize((100, 23))
        self.spin_step_size.SetToolTip(_("Scan gap / step size image native value."))
        self.combo_dpi.SetSelection(0)
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
        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        label_7 = wx.StaticText(self, wx.ID_ANY, _("DPP"))
        label_7.SetToolTip(_("Dots Per Pixel"))
        sizer_1.Add(label_7, 1, 0, 0)
        sizer_1.Add(self.spin_step_size, 5, 0, 0)
        sizer_8.Add(sizer_1, 1, wx.EXPAND, 0)
        label_8 = wx.StaticText(self, wx.ID_ANY, _("DPI:"))
        label_8.SetToolTip(_("Dots Per Inch"))
        sizer_6.Add(label_8, 1, 0, 0)
        sizer_6.Add(self.combo_dpi, 5, 0, 0)
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

    def on_spin_step(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.element.values["raster_step"] = self.spin_step_size.GetValue()
        self.combo_dpi.SetSelection(self.spin_step_size.GetValue() - 1)
        self.update_step_image()

    def on_combo_dpi(self, event):  # wxGlade: ImageProperty.<event_handler>
        self.spin_step_size.SetValue(self.combo_dpi.GetSelection() + 1)
        self.element.values["raster_step"] = self.spin_step_size.GetValue()
        self.update_step_image()

    def update_step_image(self):
        element = self.element
        step_value = self.spin_step_size.GetValue()
        m = element.transform
        tx = m.e
        ty = m.f
        element.transform = Matrix.scale(float(step_value), float(step_value))
        element.transform.post_translate(tx, ty)
        element.node.modified()
        if self.context is not None:
            self.context.signal("element_property_update", element)
            self.context.signal("refresh_scene")

    def on_text_x(self, event):  # wxGlade: ImageProperty.<event_handler>
        event.Skip()

    def on_text_y(self, event):  # wxGlade: ImageProperty.<event_handler>
        event.Skip()

    def on_text_width(self, event):  # wxGlade: ImageProperty.<event_handler>
        event.Skip()

    def on_text_height(self, event):  # wxGlade: ImageProperty.<event_handler>
        event.Skip()
