from math import sqrt

import wx

from ...core.element_types import elem_nodes
from ...core.units import Length
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
            wx_button = wx.StaticBitmap(
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

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)
        font_size = 7

        # Plus one combobox + value field for stroke width
        self.strokewidth_label = wx.StaticText(
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
        self.spin_width = wx.TextCtrl(
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
        self.combo_units = wx.ComboBox(
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
        self.combo_units.SetSelection(0)

        self.chk_scale = wx.CheckBox(self.parent, wx.ID_ANY, _("Scale"))
        self.chk_scale.SetToolTip(
            _("Toggle the behaviour of stroke-growth.")
            + "\n"
            + _("Active: stroke width remains the same, regardless of the element size")
            + "\n"
            + _("Inactive: stroke grows/shrink with scaled element")
        )

        self.parent.Bind(wx.EVT_COMBOBOX, self.on_stroke_width, self.combo_units)
        # self.parent.Bind(wx.EVT_TEXT_ENTER, self.on_stroke_width, self.spin_width)
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

    def on_stroke_width(self, event):
        if self.startup or self.combo_units.GetSelection() < 0:
            return
        try:
            units = self.unit_choices[self.combo_units.GetSelection()]
            self.context(f"stroke-width {float(self.spin_width.GetValue())}{units}")
        except ValueError:
            pass

    def Signal(self, signal, *args):
        if signal == "emphasized":
            value = self.context.elements.has_emphasis()
            sw_default = None
            ck_default = True
            mat_default = None
            for e in self.context.elements.flat(types=elem_nodes, emphasized=True):
                if hasattr(e, "stroke_width") and hasattr(e, "stroke_scaled"):
                    if sw_default is None:
                        sw_default = e.stroke_width
                        mat_default = e.matrix
                        ck_default = e.stroke_scaled
                        break
            if sw_default is not None:
                # Set Values
                self.startup = True
                # Lets establish which unit might be the best to represent the display
                found_something = False
                if sw_default == 0:
                    value = 0
                    idxunit = 0  # px
                    found_something = True
                else:
                    best_post = 99999999
                    delta = 0.99999999
                    best_pre = 0
                    factor = sqrt(abs(mat_default.determinant)) if ck_default else 1.0
                    node_stroke_width = sw_default * factor
                    for idx, unit in enumerate(self.unit_choices):
                        std = float(Length(f"1{unit}"))
                        fraction = abs(node_stroke_width / std)
                        if fraction == 0:
                            continue
                        curr_post = 0
                        curr_pre = int(fraction)
                        while fraction < 1:
                            curr_post += 1
                            fraction *= 10
                        fraction -= curr_pre
                        # print (f"unit={unit}, fraction={fraction}, digits={curr_post}, value={self.node.stroke_width / std}")
                        takespref = False
                        if fraction < delta:
                            takespref = True
                        elif fraction == delta and curr_pre > best_pre:
                            takespref = True
                        elif fraction == delta and curr_post < best_post:
                            takespref = True
                        if takespref:
                            best_pre = curr_pre
                            delta = fraction
                            best_post = curr_post
                            idxunit = idx
                            value = node_stroke_width / std
                            found_something = True

                    if not found_something:
                        std = float(Length(f"1mm"))
                        if node_stroke_width / std < 0.1:
                            idxunit = 0  # px
                        else:
                            idxunit = 2  # mm
                        unit = self.unit_choices[idxunit]
                        std = float(Length(f"1{unit}"))
                        value = node_stroke_width / std

                self.spin_width.SetValue(str(round(value, 4)))
                self.combo_units.SetSelection(idxunit)
                self.chk_scale.SetValue(ck_default)
                self.startup = False
