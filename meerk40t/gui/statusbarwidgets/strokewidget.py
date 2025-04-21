import wx

from meerk40t.core.elements.element_types import elem_nodes
from meerk40t.core.units import Length
from meerk40t.gui.wxutils import TextCtrl, wxCheckBox, wxComboBox, wxStaticBitmap, wxStaticText

from .statusbarwidget import StatusBarWidget

_ = wx.GetTranslation


class ColorWidget(StatusBarWidget):
    """
    Displays the 8 'main' colors and allows assignment to stroke and fill
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)
        # And now 8 Buttons for Stroke / Fill:
        colors = (
            0xFFFFFF,
            0x000000,
            0xFF0000,
            0x00FF00,
            0x0000FF,
            0xFFFF00,
            0xFF00FF,
            0x00FFFF,
            0xFFFFFF,
        )
        self.button_color = []
        for idx in range(len(colors)):
            wx_button = wxStaticBitmap(
                self.parent,
                id=wx.ID_ANY,
                size=wx.Size(20, -1),
                style=wx.BORDER_RAISED,
            )
            wx_button.SetBackgroundColour(wx.Colour(colors[idx]))
            wx_button.SetMinSize(wx.Size(10, -1))
            if idx == 0:
                wx_button.SetToolTip(
                    _("Clear stroke-color (right click clear fill color)")
                )
            else:
                wx_button.SetToolTip(_("Set stroke-color (right click set fill color)"))
            wx_button.Bind(wx.EVT_LEFT_DOWN, self.on_button_color_left)
            wx_button.Bind(wx.EVT_RIGHT_DOWN, self.on_button_color_right)
            self.button_color.append(wx_button)

        xsize = 15
        imgBit = wx.Bitmap(xsize, xsize)
        dc = wx.MemoryDC(imgBit)
        dc.SelectObject(imgBit)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        dc.SetPen(wx.Pen(wx.RED, 2))
        dc.DrawLine((0, 0), (xsize, xsize))
        dc.DrawLine((xsize, 0), (0, xsize))
        # Now release dc
        dc.SelectObject(wx.NullBitmap)
        self.button_color[0].SetBitmap(imgBit)

        for idx in range(len(colors)):
            self.Add(self.button_color[idx], 1, wx.EXPAND, 0)

    def on_button_color_left(self, event):
        # Okay my backgroundcolor is...
        if not self.startup:
            button = event.EventObject
            color = button.GetBackgroundColour()
            rgb = [color.Red(), color.Green(), color.Blue()]
            if button == self.button_color[0]:
                color_str = "none"
            else:
                color_str = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            if self.context.elements.classify_on_color:
                option = " --classify"
            else:
                option = ""
            self.context(f"stroke {color_str}{option}\n")
            self.context.signal("selstroke", rgb)

    def on_button_color_right(self, event):
        # Okay my backgroundcolor is...
        if not self.startup:
            button = event.EventObject
            color = button.GetBackgroundColour()
            rgb = [color.Red(), color.Green(), color.Blue()]
            if button == self.button_color[0]:
                color_str = "none"
            else:
                color_str = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            if self.context.elements.classify_on_color:
                option = " --classify"
            else:
                option = ""
            self.context(f"fill {color_str}{option}\n")
            self.context.signal("selfill", rgb)


class StrokeWidget(StatusBarWidget):
    """
    Allows manipulation of the strokewidth properties
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._needs_generation = False

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)
        font_size = 7

        # Plus one combobox + value field for stroke width
        self.strokewidth_label = wxStaticText(
            self.parent, id=wx.ID_ANY, label=_("Stroke:")
        )
        self.strokewidth_label.SetFont(
            wx.Font(
                font_size,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        self.spin_width = TextCtrl(
            self.parent, id=wx.ID_ANY, value="0.10", style=wx.TE_PROCESS_ENTER
        )
        self.spin_width.SetFont(
            wx.Font(
                font_size,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        self.spin_width.SetMinSize(wx.Size(30, -1))
        self.spin_width.SetMaxSize(wx.Size(80, -1))

        self.unit_choices = ["px", "pt", "mm", "cm", "inch", "mil"]
        self.combo_units = wxComboBox(
            self.parent,
            wx.ID_ANY,
            choices=self.unit_choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_units.SetFont(
            wx.Font(
                font_size,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        self.combo_units.SetMinSize(wx.Size(30, -1))
        self.combo_units.SetMaxSize(wx.Size(120, -1))
        self.context.setting(int, "strokewidth_default_units", 0)
        if (
            0 > self.context.strokewidth_default_units
            or self.context.strokewidth_default_units >= len(self.unit_choices)
        ):
            self.context.strokewidth_default_units = 0
        self.combo_units.SetSelection(self.context.strokewidth_default_units)

        self.chk_scale = wxCheckBox(self.parent, wx.ID_ANY, _("Scale"))
        self.chk_scale.SetToolTip(
            _("Toggle the behaviour of stroke-growth.")
            + "\n"
            + _("Active: stroke width remains the same, regardless of the element size")
            + "\n"
            + _("Inactive: stroke grows/shrink with scaled element")
        )

        self.parent.Bind(wx.EVT_COMBOBOX, self.on_stroke_width_combo, self.combo_units)
        self.parent.Bind(wx.EVT_TEXT_ENTER, self.on_stroke_width, self.spin_width)
        self.parent.Bind(wx.EVT_CHECKBOX, self.on_chk_scale, self.chk_scale)
        self.Add(self.strokewidth_label, 0, 0, 0)
        self.Add(self.spin_width, 2, 0, 0)
        self.Add(self.combo_units, 2, 0, 0)
        self.Add(self.chk_scale, 1, 0, 0)

    def on_chk_scale(self, event):
        if self.startup:
            return
        if self.chk_scale.GetValue():
            self.context("enable_stroke_scale")
        else:
            self.context("disable_stroke_scale")
        self.update_stroke_magnitude()

    def on_stroke_width_combo(self, event):
        if self.startup or self.combo_units.GetSelection() < 0:
            return
        if self.context.strokewidth_default_units == self.combo_units.GetSelection():
            # No change.
            return
        original = self.unit_choices[self.context.strokewidth_default_units]
        units = self.unit_choices[self.combo_units.GetSelection()]
        new_text = Length(
            f"{float(self.spin_width.GetValue())}{original}", preferred_units=units
        )
        self.spin_width.SetValue(f"{new_text.preferred:.3f}")
        try:
            self.context(f"stroke-width {float(self.spin_width.GetValue())}{units}")
        except ValueError:
            pass
        self.context.strokewidth_default_units = self.combo_units.GetSelection()

    def on_stroke_width(self, event):
        if self.startup or self.combo_units.GetSelection() < 0:
            return
        try:
            units = self.unit_choices[self.combo_units.GetSelection()]
            self.context(f"stroke-width {float(self.spin_width.GetValue())}{units}")
        except ValueError:
            pass

    def update_stroke_magnitude(self):
        sw_default = None
        for e in self.context.elements.flat(types=elem_nodes, emphasized=True):
            if hasattr(e, "stroke_width"):
                sw_default = e.stroke_width
                try:
                    sw_default = e.implied_stroke_width
                except AttributeError:
                    pass
                break
        if sw_default is None:
            # Nothing
            return
        self.context.setting(int, "strokewidth_default_units", 0)
        unit = self.unit_choices[self.context.strokewidth_default_units]
        std = float(Length(f"1{unit}"))
        value = sw_default / std
        self.spin_width.SetValue(str(round(value, 4)))

    def update_stroke_scale_check(self):
        for e in self.context.elements.flat(types=elem_nodes, emphasized=True):
            if hasattr(e, "stroke_scaled"):
                self.chk_scale.SetValue(e.stroke_scaled)
                return

    def calculate_infos(self):
        self.update_stroke_magnitude()
        self.update_stroke_scale_check()
        self.startup = False

    def GenerateInfos(self):
        if self.visible:
            self.context.elements.set_start_time("strokewidget")
            self.calculate_infos()
            self.context.elements.set_end_time("strokewidget")
        else:
            self._needs_generation = True

    def Show(self, showit=True):
        if self._needs_generation and showit:
            self.calculate_infos()
        super().Show(showit)

    def Signal(self, signal, *args):
        if signal in ("modified", "emphasized"):
            self.GenerateInfos()
