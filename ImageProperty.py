import wx

from Kernel import Module

_ = wx.GetTranslation


class ImageProperty(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: ImageProperty.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.FRAME_FLOAT_ON_PARENT
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((276, 218))
        self.spin_step_size = wx.SpinCtrl(self, wx.ID_ANY, "1", min=1, max=63)
        self.combo_dpi = wx.ComboBox(self, wx.ID_ANY,
                                     choices=["1000", "500", "333", "250", "200", "166", "142", "125", "111", "100"],
                                     style=wx.CB_DROPDOWN)
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
        # end wxGlade
        self.image_element = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        self.device.remove('window', self.name)
        event.Skip()  # Call destroy.

    def set_element(self, element):
        self.image_element = element
        try:
            self.spin_step_size.SetValue(element.values['raster_step'])
            self.combo_dpi.SetSelection(self.spin_step_size.GetValue() - 1)
        except KeyError:
            self.spin_step_size.SetValue(1)  # Default value
            self.combo_dpi.SetSelection(self.spin_step_size.GetValue() - 1)
        except AttributeError:
            self.combo_dpi.Enable(False)
            self.spin_step_size.Enable(False)

        try:
            bounds = self.image_element.bbox()
            self.text_x.SetValue("%f" % bounds[0])
            self.text_y.SetValue("%f" % bounds[1])
            self.text_width.SetValue("%f" % (bounds[2] - bounds[0]))
            self.text_height.SetValue("%f" % (bounds[3] - bounds[1]))
        except AttributeError:
            pass

    def initialize(self):
        self.device.close('window', self.name)
        self.Show()

    def shutdown(self,  channel):
        self.Close()

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
        self.image_element.values['raster_step'] = self.spin_step_size.GetValue()
        self.combo_dpi.SetSelection(self.spin_step_size.GetValue() - 1)
        self.device.signal('element_property_update', self.image_element)

    def on_combo_dpi(self, event):  # wxGlade: ImageProperty.<event_handler>
        self.spin_step_size.SetValue(self.combo_dpi.GetSelection() + 1)
        self.image_element.values['raster_step'] = self.spin_step_size.GetValue()
        self.device.signal('element_property_update', self.image_element)

    def on_text_x(self, event):  # wxGlade: ImageProperty.<event_handler>
        event.Skip()

    def on_text_y(self, event):  # wxGlade: ImageProperty.<event_handler>
        event.Skip()

    def on_text_width(self, event):  # wxGlade: ImageProperty.<event_handler>
        event.Skip()

    def on_text_height(self, event):  # wxGlade: ImageProperty.<event_handler>
        event.Skip()
