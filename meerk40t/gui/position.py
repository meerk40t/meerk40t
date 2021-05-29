import wx

_ = wx.GetTranslation


from .icons import icons8_lock_50, icons8_padlock_50


class PositionPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.text_x = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_y = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_w = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_h = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.button_aspect_ratio = wx.BitmapButton(
            self, wx.ID_ANY, icons8_lock_50.GetBitmap()
        )
        self.combo_box_units = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["mm", "cm", "inch", "mil", "%"],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_units.SetSelection(0)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TEXT, self.on_text_x, self.text_x)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_pos_enter, self.text_x)
        self.Bind(wx.EVT_TEXT, self.on_text_y, self.text_y)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_pos_enter, self.text_y)
        self.Bind(wx.EVT_TEXT, self.on_text_w, self.text_w)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_dim_enter, self.text_w)
        self.Bind(wx.EVT_TEXT, self.on_text_h, self.text_h)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_dim_enter, self.text_h)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_box_units, self.combo_box_units)
        self.Bind(wx.EVT_BUTTON, self.on_button_aspect_ratio, self.button_aspect_ratio)
        # end wxGlade
        self.position_aspect_ratio = True
        self.position_ignore_update = False
        self.position_x = 0.0
        self.position_y = 0.0
        self.position_h = 0.0
        self.position_w = 0.0
        self.position_units = 0
        self.position_name = None
        self.context.setting(int, "units_index", 0)
        self.position_units = self.context.units_index
        self._update_position()

    def initialize(self, *args):
        self.context.listen("units", self.space_changed)
        self.context.listen("emphasized", self._update_position)
        self.context.listen("modified", self._update_position)
        self.context._kernel.listen("lifecycle;shutdown", "", self.finalize)

    def finalize(self, *args):
        self.context.unlisten("units", self.space_changed)
        self.context.unlisten("emphasized", self._update_position)
        self.context.unlisten("modified", self._update_position)
        self.context._kernel.unlisten("lifecycle;shutdown", "", self.finalize)

    def __set_properties(self):
        # begin wxGlade: PositionPanel.__set_properties
        self.button_aspect_ratio.SetSize(self.button_aspect_ratio.GetBestSize())
        self.combo_box_units.SetSelection(0)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: PositionPanel.__do_layout
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_units = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Units:"), wx.HORIZONTAL
        )
        sizer_h = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "H:"), wx.HORIZONTAL)
        sizer_w = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "W:"), wx.HORIZONTAL)
        sizer_y = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Y:"), wx.HORIZONTAL)
        sizer_x = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "X:"), wx.HORIZONTAL)
        sizer_x.Add(self.text_x, 1, 0, 0)
        sizer_panel.Add(sizer_x, 0, 0, 0)
        sizer_y.Add(self.text_y, 1, 0, 0)
        sizer_panel.Add(sizer_y, 0, 0, 0)
        sizer_w.Add(self.text_w, 1, 0, 0)
        sizer_panel.Add(sizer_w, 0, 0, 0)
        sizer_panel.Add(self.button_aspect_ratio, 0, 0, 0)
        sizer_h.Add(self.text_h, 1, 0, 0)
        sizer_panel.Add(sizer_h, 0, 0, 0)
        sizer_units.Add(self.combo_box_units, 0, 0, 0)
        sizer_panel.Add(sizer_units, 0, 0, 0)
        self.SetSizer(sizer_panel)
        sizer_panel.Fit(self)
        self.Layout()
        # end wxGlade

    def _update_position(self, *args, **kwargs):
        p = self.context
        elements = p.elements
        bounds = elements.selected_area()
        self.text_w.Enable(bounds is not None)
        self.text_h.Enable(bounds is not None)
        self.text_x.Enable(bounds is not None)
        self.text_y.Enable(bounds is not None)
        self.button_aspect_ratio.Enable(bounds is not None)
        if bounds is None:
            self.position_ignore_update = True
            self.combo_box_units.SetSelection(self.position_units)
            self.position_ignore_update = False
            return
        x0, y0, x1, y1 = bounds
        conversion, name, index = (39.37, "mm", 0)
        if self.position_units == 2:
            conversion, name, index = (1000.0, "in", 2)
        elif self.position_units == 3:
            conversion, name, index = (1.0, "mil", 3)
        elif self.position_units == 1:
            conversion, name, index = (393.7, "cm", 1)
        elif self.position_units == 0:
            conversion, name, index = (39.37, "mm", 0)
        self.position_name = name
        self.position_x = x0 / conversion
        self.position_y = y0 / conversion
        self.position_w = (x1 - x0) / conversion
        self.position_h = (y1 - y0) / conversion
        self.position_ignore_update = True
        if self.position_units != 4:
            self.text_x.SetValue("%.2f" % self.position_x)
            self.text_y.SetValue("%.2f" % self.position_y)
            self.text_w.SetValue("%.2f" % self.position_w)
            self.text_h.SetValue("%.2f" % self.position_h)
        else:
            self.text_x.SetValue("%.2f" % 100)
            self.text_y.SetValue("%.2f" % 100)
            self.text_w.SetValue("%.2f" % 100)
            self.text_h.SetValue("%.2f" % 100)
        self.combo_box_units.SetSelection(self.position_units)
        self.position_ignore_update = False

    def space_changed(self, origin, *args):
        self.position_units = self.context.units_index
        self._update_position()

    def on_text_x(self, event):  # wxGlade: MyFrame.<event_handler>
        if self.position_ignore_update:
            return
        try:
            if self.position_units != 4:
                self.position_x = float(self.text_x.GetValue())
        except ValueError:
            pass

    def on_text_y(self, event):  # wxGlade: MyFrame.<event_handler>
        if self.position_ignore_update:
            return
        try:
            if self.position_units != 4:
                self.position_y = float(self.text_y.GetValue())
        except ValueError:
            pass

    def on_text_w(self, event):  # wxGlade: MyFrame.<event_handler>
        if self.position_ignore_update:
            return
        try:
            new = float(self.text_w.GetValue())
            old = self.position_w
            if self.position_units == 4:
                ratio = new / 100.0
                if self.position_aspect_ratio:
                    self.position_ignore_update = True
                    self.text_h.SetValue("%.2f" % (ratio * 100))
                    self.position_ignore_update = False
            else:
                ratio = new / old
                if self.position_aspect_ratio:
                    self.position_ignore_update = True
                    self.text_h.SetValue("%.2f" % (self.position_h * ratio))
                    self.position_ignore_update = False
        except (ValueError, ZeroDivisionError):
            pass

    def on_button_aspect_ratio(self, event):  # wxGlade: MyFrame.<event_handler>
        if self.position_ignore_update:
            return
        if self.position_aspect_ratio:
            self.button_aspect_ratio.SetBitmap(icons8_padlock_50.GetBitmap())
        else:
            self.button_aspect_ratio.SetBitmap(icons8_lock_50.GetBitmap())
        self.position_aspect_ratio = not self.position_aspect_ratio

    def on_text_h(self, event):  # wxGlade: MyFrame.<event_handler>
        if self.position_ignore_update:
            return
        try:
            new = float(self.text_h.GetValue())
            old = self.position_h
            if self.position_units == 4:
                if self.position_aspect_ratio:
                    self.position_ignore_update = True
                    self.text_w.SetValue("%.2f" % (new))
                    self.position_ignore_update = False
            else:
                if self.position_aspect_ratio:
                    self.position_ignore_update = True
                    self.text_w.SetValue("%.2f" % (self.position_w * (new / old)))
                    self.position_ignore_update = False
        except (ValueError, ZeroDivisionError):
            pass

    def on_text_dim_enter(self, event):
        if self.position_units == 4:
            ratio_w = float(self.text_w.GetValue()) / 100.0
            ratio_h = float(self.text_h.GetValue()) / 100.0
            self.position_w *= ratio_w
            self.position_h *= ratio_h
        else:
            w = float(self.text_w.GetValue())
            h = float(self.text_h.GetValue())
            self.position_w = w
            self.position_h = h
        self.context(
            "resize %f%s %f%s %f%s %f%s\n"
            % (
                self.position_x,
                self.position_name,
                self.position_y,
                self.position_name,
                self.position_w,
                self.position_name,
                self.position_h,
                self.position_name,
            )
        )
        self._update_position()

    def on_text_pos_enter(self, event):
        if self.position_units == 4:
            ratio_x = float(self.text_x.GetValue()) / 100.0
            ratio_y = float(self.text_y.GetValue()) / 100.0
            self.position_x *= ratio_x
            self.position_y *= ratio_y
        else:
            x = float(self.text_x.GetValue())
            y = float(self.text_y.GetValue())
            self.position_x = x
            self.position_y = y
        self.context(
            "resize %f%s %f%s %f%s %f%s\n"
            % (
                self.position_x,
                self.position_name,
                self.position_y,
                self.position_name,
                self.position_w,
                self.position_name,
                self.position_h,
                self.position_name,
            )
        )
        self._update_position()

    def on_combo_box_units(self, event):  # wxGlade: MyFrame.<event_handler>
        if self.position_ignore_update:
            return
        self.position_units = self.combo_box_units.GetSelection()
        self._update_position()
