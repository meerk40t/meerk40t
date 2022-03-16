import wx
from wx import aui

from meerk40t.gui.icons import icons8_lock_50, icons8_padlock_50
from meerk40t.svgelements import Length

_ = wx.GetTranslation

MILS_IN_MM = 39.3701
UNITS = (_("mm"), _("cm"), _("inch"), _("mil"), "%")
CONVERSION = (39.37, 393.7, 1000.0, 1.0)
PRECISION = ("%.3f", "%.4f", "%.4f", "%.1f", "%.2f")


def register_panel_position(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Left()
        .MinSize(225, 110)
        .FloatingSize(225, 110)
        .Caption(_("Position"))
        .CaptionVisible(not context.pane_lock)
        .Name("position")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = PositionPanel(window, wx.ID_ANY, context=context)

    window.on_pane_add(pane)
    context.register("pane/position", pane)


class PositionPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.channel = self.context.kernel._console_channel
        self.text_x = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_y = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_w = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_h = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_x.SetMinSize((70, 23))
        self.text_y.SetMinSize((70, 23))
        self.text_w.SetMinSize((70, 23))
        self.text_h.SetMinSize((70, 23))
        self.button_aspect_ratio = wx.BitmapButton(
            self, wx.ID_ANY, icons8_lock_50.GetBitmap()
        )
        self.combo_box_units = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=UNITS,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_units.SetSelection(0)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_x_enter, self.text_x)
        self.text_x.Bind(wx.EVT_KILL_FOCUS, self.on_text_x_enter)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_y_enter, self.text_y)
        self.text_y.Bind(wx.EVT_KILL_FOCUS, self.on_text_y_enter)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_w_enter, self.text_w)
        self.text_w.Bind(wx.EVT_KILL_FOCUS, self.on_text_w_enter)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_h_enter, self.text_h)
        self.text_h.Bind(wx.EVT_KILL_FOCUS, self.on_text_h_enter)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_box_units, self.combo_box_units)
        self.Bind(wx.EVT_BUTTON, self.on_button_aspect_ratio, self.button_aspect_ratio)
        # end wxGlade
        self.bed_dim = self.context.root

        self.position_aspect_ratio = True
        self.position_x = 0.0
        self.position_y = 0.0
        self.position_h = 0.0
        self.position_w = 0.0
        self.position_name = None
        self.context.setting(int, "units_index", 0)
        self.position_units = self.context.units_index
        self._update_position()

    def initialize(self, *args):
        self.context.listen("units", self.space_changed)
        self.context.listen("emphasized", self._update_position)
        self.context.listen("modified", self._update_position)
        self.context.listen("altered", self._update_position)
        self.context.kernel.listen("lifecycle;shutdown", "", self.finalize)

    def finalize(self, *args):
        self.context.unlisten("units", self.space_changed)
        self.context.unlisten("emphasized", self._update_position)
        self.context.unlisten("modified", self._update_position)
        self.context.unlisten("altered", self._update_position)
        self.context.kernel.unlisten("lifecycle;shutdown", "", self.finalize)

    def __set_properties(self):
        # begin wxGlade: PositionPanel.__set_properties
        self.button_aspect_ratio.SetSize(self.button_aspect_ratio.GetBestSize())
        self.combo_box_units.SetSelection(0)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: PositionPanel.__do_layout
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6 = wx.BoxSizer(wx.VERTICAL)
        sizer_7 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Units")), wx.HORIZONTAL
        )
        sizer_panel = wx.BoxSizer(wx.VERTICAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_h = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Height:")), wx.HORIZONTAL
        )
        sizer_w = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Width:")), wx.HORIZONTAL
        )
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_y = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Y:"), wx.HORIZONTAL)
        sizer_x = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "X:"), wx.HORIZONTAL)
        sizer_x.Add(self.text_x, 1, 0, 0)
        sizer_3.Add(sizer_x, 0, 0, 0)
        sizer_y.Add(self.text_y, 1, 0, 0)
        sizer_3.Add(sizer_y, 0, 0, 0)
        sizer_panel.Add(sizer_3, 0, wx.EXPAND, 0)
        label_1 = wx.StaticText(self, wx.ID_ANY, "")
        sizer_panel.Add(label_1, 0, 0, 0)
        sizer_w.Add(self.text_w, 1, 0, 0)
        sizer_4.Add(sizer_w, 0, 0, 0)
        sizer_h.Add(self.text_h, 1, wx.ALL, 0)
        sizer_4.Add(sizer_h, 0, 0, 0)
        sizer_panel.Add(sizer_4, 0, wx.EXPAND, 0)
        sizer_5.Add(sizer_panel, 0, 0, 0)
        sizer_7.Add(self.combo_box_units, 0, 0, 0)
        sizer_6.Add(sizer_7, 0, wx.EXPAND, 0)
        sizer_6.Add(self.button_aspect_ratio, 0, 0, 0)
        sizer_5.Add(sizer_6, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_5)
        sizer_5.Fit(self)
        self.Layout()
        # end wxGlade

    def _update_position(self, *args, **kwargs):
        p = self.context
        elements = p.elements
        bounds = elements.selected_area()
        if bounds is None:
            if self.text_x.IsEnabled():
                self.text_w.Enable(False)
                self.text_h.Enable(False)
                self.text_x.Enable(False)
                self.text_y.Enable(False)
                self.button_aspect_ratio.Enable(False)
            self.combo_box_units.SetSelection(self.position_units)
            return
        if not self.text_x.IsEnabled():
            self.text_w.Enable(True)
            self.text_h.Enable(True)
            self.text_x.Enable(True)
            self.text_y.Enable(True)
            self.button_aspect_ratio.Enable(True)

        self.combo_box_units.SetSelection(self.position_units)

        x0, y0, x1, y1 = bounds
        units = UNITS[self.position_units]
        self.position_name = UNITS[self.position_units % 4]  # % treated as mm
        conversion = CONVERSION[self.position_units % 4]
        precision = PRECISION[self.position_units]

        self.position_x = x0 / conversion
        self.position_y = y0 / conversion
        self.position_w = (x1 - x0) / conversion
        self.position_h = (y1 - y0) / conversion

        if units == "%":
            self.text_x.SetValue(precision % 100)
            self.text_y.SetValue(precision % 100)
            self.text_w.SetValue(precision % 100)
            self.text_h.SetValue(precision % 100)
        else:
            self.text_x.SetValue(precision % self.position_x)
            self.text_y.SetValue(precision % self.position_y)
            self.text_w.SetValue(precision % self.position_w)
            self.text_h.SetValue(precision % self.position_h)

    def space_changed(self, origin, *args):
        self.position_units = self.context.units_index
        self._update_position()

    def on_button_aspect_ratio(self, event):  # wxGlade: MyFrame.<event_handler>
        if self.position_aspect_ratio:
            self.button_aspect_ratio.SetBitmap(icons8_padlock_50.GetBitmap())
        else:
            self.button_aspect_ratio.SetBitmap(icons8_lock_50.GetBitmap())
        self.position_aspect_ratio = not self.position_aspect_ratio

    def text_to_measurement(self, value, oldvalue=None):
        if UNITS[self.position_units] == "%":
            try:
                ratio_w = float(value) / 100.0
            except ValueError:
                return None
            return oldvalue * ratio_w
        units = self.position_name
        try:
            return float(value)
        except ValueError:
            if units == "mm":
                return round(
                    Length(value)
                    .to_mm(
                        ppi=1000,
                        relative_length=self.bed_dim.bed_width * MILS_IN_MM,
                    )
                    .amount,
                    3
                )
            if units == "cm":
                return round(
                    Length(value)
                    .to_cm(
                        ppi=1000,
                        relative_length=self.bed_dim.bed_width * MILS_IN_MM,
                    )
                    .amount,
                    4
                )
            if units == "inch":
                return round(
                    Length(value)
                    .to_inch(
                        ppi=1000,
                        relative_length=self.bed_dim.bed_width * MILS_IN_MM,
                    )
                    .amount,
                    5
                )
            if units == "mil":
                return round(
                    Length(value)
                    .to_mil(
                        ppi=1000,
                        relative_length=self.bed_dim.bed_width * MILS_IN_MM,
                    )
                    .amount,
                    1
                )
            return None

    def _position_resize(self):
        resize = "resize {p}%s {p}%s {p}%s {p}%s\n".format(
            p=PRECISION[self.position_units]
        )
        self.context(
            resize
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

    def on_text_w_enter(self, event):
        event.Skip()
        value = self.text_w.GetValue()
        w = self.text_to_measurement(value, self.position_w)
        if w is None:
            self.channel(_("[red]Position panel: invalid {f} value: {v}").format(
                f=_("width"),
                v=value
            ))
            self._update_position()
            return
        if abs(self.position_w - w) < 1e-4:
            self._update_position()
            return
        if abs(self.position_w) < 1e-5:
            self.channel(
                _("[red]Position panel: cannot resize zero {f}: {v}").format(
                    f=_("width"),
                    v=value
                )
            )
            self._update_position()
            return
        if self.position_aspect_ratio:
            self.position_h *= w / self.position_w
        self.position_w = w
        self._position_resize()

    def on_text_h_enter(self, event):
        event.Skip()
        value = self.text_h.GetValue()
        h = self.text_to_measurement(value, self.position_h)
        if h is None:
            self.channel(_("[red]Position panel: invalid {f} value: {v}").format(
                f=_("height"),
                v=value
            ))
            self._update_position()
            return
        if abs(self.position_h - h) < 1e-4:
            self._update_position()
            return
        if abs(self.position_h) < 1e-5:
            self.channel(
                _("[red]Position panel: cannot resize zero {f}: {v}").format(
                    f=_("height"),
                    v=value
                )
            )
            self._update_position()
            return
        if self.position_aspect_ratio:
            self.position_w *= h / self.position_h
        self.position_h = h
        self._position_resize()

    def on_text_x_enter(self, event=None):
        event.Skip()
        x = self.text_to_measurement(self.text_x.GetValue(), self.position_x)
        if x is None:
            return
        if abs(self.position_x - x) < 1e-4:
            self._update_position()
            return
        self.position_x = x
        self._position_resize()

    def on_text_y_enter(self, event=None):
        event.Skip()
        y = self.text_to_measurement(self.text_y.GetValue(), self.position_y)
        if y is None:
            return
        if abs(self.position_y - y) < 1e-4:
            self._update_position()
            return
        self.position_y = y
        self._position_resize()

    def on_combo_box_units(self, event):  # wxGlade: MyFrame.<event_handler>
        self.position_units = self.combo_box_units.GetSelection()
        self._update_position()
