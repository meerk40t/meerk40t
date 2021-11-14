import wx
from wx import aui

from meerk40t.gui.icons import icons8_lock_50, icons8_padlock_50
from meerk40t.svgelements import Length

_ = wx.GetTranslation

MILS_IN_MM = 39.3701


def register_panel(window, context):
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
            choices=[_("mm"), _("cm"), _("inch"), _("mil"), "%"],
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

        self.position_aspect_ratio = True
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
        bounds = self.context.elements.selected_area()
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

        if self.position_units == 4:
            self.text_x.SetValue("%.2f" % 100)
            self.text_y.SetValue("%.2f" % 100)
            self.text_w.SetValue("%.2f" % 100)
            self.text_h.SetValue("%.2f" % 100)
        else:
            self.text_x.SetValue("%.2f" % self.position_x)
            self.text_y.SetValue("%.2f" % self.position_y)
            self.text_w.SetValue("%.2f" % self.position_w)
            self.text_h.SetValue("%.2f" % self.position_h)
        self.combo_box_units.SetSelection(self.position_units)

    def space_changed(self, origin, *args):
        self.position_units = self.context.units_index
        self._update_position()

    def on_button_aspect_ratio(self, event):  # wxGlade: MyFrame.<event_handler>
        if self.position_aspect_ratio:
            self.button_aspect_ratio.SetBitmap(icons8_padlock_50.GetBitmap())
        else:
            self.button_aspect_ratio.SetBitmap(icons8_lock_50.GetBitmap())
        self.position_aspect_ratio = not self.position_aspect_ratio

    def on_text_w_enter(self, event):
        event.Skip()
        original = self.position_w

        if self.position_units == 4:
            ratio_w = float(self.text_w.GetValue()) / 100.0
            w = self.position_w * ratio_w
        else:
            try:
                w = float(self.text_w.GetValue())
            except ValueError:
                if self.position_units == 0:
                    w = (
                        Length(self.text_w.GetValue())
                        .to_mm(
                            ppi=1000,
                            relative_length=self.context.device.bed_width * MILS_IN_MM,
                        )
                        .amount
                    )
                elif self.position_units == 1:
                    w = (
                        Length(self.text_w.GetValue())
                        .to_cm(
                            ppi=1000,
                            relative_length=self.context.device.bed_width * MILS_IN_MM,
                        )
                        .amount
                    )
                elif self.position_units == 2:
                    w = (
                        Length(self.text_w.GetValue())
                        .to_inch(
                            ppi=1000,
                            relative_length=self.context.device.bed_width * MILS_IN_MM,
                        )
                        .amount
                    )
                elif self.position_units == 3:
                    w = (
                        Length(self.text_w.GetValue())
                        .value(
                            ppi=1000,
                            relative_length=self.context.device.bed_width * MILS_IN_MM,
                        )
                        .amount
                    )
                else:
                    return
        if abs(w) < 1e-8:
            self.text_w.SetValue(str(self.position_w))
            return
        self.position_w = w
        if self.position_aspect_ratio:
            if abs(original) < 1e-8:
                return
            self.position_h *= self.position_w / original
        if self.position_w == 0:
            return
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

    def on_text_h_enter(self, event):
        event.Skip()
        original = self.position_h
        if self.position_units == 4:
            ratio_w = float(self.text_h.GetValue()) / 100.0
            h = self.position_h * ratio_w
        else:
            try:
                h = float(self.text_h.GetValue())
            except ValueError:
                if self.position_units == 0:
                    h = (
                        Length(self.text_h.GetValue())
                        .to_mm(
                            ppi=1000,
                            relative_length=self.context.device.bed_height * MILS_IN_MM,
                        )
                        .amount
                    )
                elif self.position_units == 1:
                    h = (
                        Length(self.text_h.GetValue())
                        .to_cm(
                            ppi=1000,
                            relative_length=self.context.device.bed_height * MILS_IN_MM,
                        )
                        .amount
                    )
                elif self.position_units == 2:
                    h = (
                        Length(self.text_h.GetValue())
                        .to_inch(
                            ppi=1000,
                            relative_length=self.context.device.bed_height * MILS_IN_MM,
                        )
                        .amount
                    )
                elif self.position_units == 3:
                    h = Length(self.text_h.GetValue()).value(
                        ppi=1000, relative_length=self.context.device.bed_height * MILS_IN_MM
                    )
                else:
                    return
        if abs(h) < 1e-8:
            self.text_h.SetValue(str(self.position_h))
            return
        self.position_h = h
        if self.position_aspect_ratio:
            if abs(original) < 1e-8:
                return
            self.position_w *= self.position_h / original
        if self.position_h == 0:
            return
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

    def on_text_x_enter(self, event=None):
        try:
            x = float(self.text_x.GetValue())
            self.position_x = x
        except ValueError:
            if self.position_units == 0:
                x = Length(self.text_x.GetValue()).to_mm(
                    ppi=1000, relative_length=self.context.device.bed_width * MILS_IN_MM
                )
                self.position_x = x.amount
            elif self.position_units == 1:
                x = Length(self.text_x.GetValue()).to_cm(
                    ppi=1000, relative_length=self.context.device.bed_width * MILS_IN_MM
                )
                self.position_x = x.amount
            elif self.position_units == 2:
                x = Length(self.text_x.GetValue()).to_inch(
                    ppi=1000, relative_length=self.context.device.bed_width * MILS_IN_MM
                )
                self.position_x = x.amount
            elif self.position_units == 3:
                x = Length(self.text_x.GetValue()).value(
                    ppi=1000, relative_length=self.context.device.bed_width * MILS_IN_MM
                )
                self.position_x = x.amount
            elif self.position_units == 4:
                ratio_x = float(self.text_x.GetValue()) / 100.0
                self.position_x *= ratio_x
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
        event.Skip()

    def on_text_y_enter(self, event=None):
        try:
            y = float(self.text_y.GetValue())
            self.position_y = y
        except ValueError:
            if self.position_units == 0:
                y = Length(self.text_y.GetValue()).to_mm(
                    ppi=1000, relative_length=self.context.device.bed_height * MILS_IN_MM
                )
                self.position_y = y.amount
            elif self.position_units == 1:
                y = Length(self.text_y.GetValue()).to_cm(
                    ppi=1000, relative_length=self.context.device.bed_height * MILS_IN_MM
                )
                self.position_y = y.amount
            elif self.position_units == 2:
                y = Length(self.text_y.GetValue()).to_inch(
                    ppi=1000, relative_length=self.context.device.bed_height * MILS_IN_MM
                )
                self.position_y = y.amount
            elif self.position_units == 3:
                y = Length(self.text_y.GetValue()).value(
                    ppi=1000, relative_length=self.context.device.bed_height * MILS_IN_MM
                )
                self.position_y = y.amount
            elif self.position_units == 4:
                ratio_y = float(self.text_y.GetValue()) / 100.0
                self.position_y *= ratio_y
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
        event.Skip()

    def on_combo_box_units(self, event):  # wxGlade: MyFrame.<event_handler>
        self.position_units = self.combo_box_units.GetSelection()
        self._update_position()
