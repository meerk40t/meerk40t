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
            wx_button.SetToolTip(_("Set stroke-color (right click set fill color)"))
            wx_button.Bind(wx.EVT_LEFT_DOWN, self.on_button_color_left)
            wx_button.Bind(wx.EVT_RIGHT_DOWN, self.on_button_color_right)
            self.button_color.append(wx_button)
        for idx in range(len(colors)):
            self.Add(self.button_color[idx], 1, wx.EXPAND, 0)

    def on_button_color_left(self, event):
        # Okay my backgroundcolor is...
        if not self.startup:
            button = event.EventObject
            color = button.GetBackgroundColour()
            rgb = [color.Red(), color.Green(), color.Blue()]
            if rgb[0] == 255 and rgb[1] == 255 and rgb[2] == 255:
                color_str = "none"
            else:
                color_str = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            self.context(f"stroke {color_str} --classify\n")
            self.context.signal("selstroke", rgb)

    def on_button_color_right(self, event):
        # Okay my backgroundcolor is...
        if not self.startup:
            button = event.EventObject
            color = button.GetBackgroundColour()
            rgb = [color.Red(), color.Green(), color.Blue()]
            if rgb[0] == 255 and rgb[1] == 255 and rgb[2] == 255:
                color_str = "none"
            else:
                color_str = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            self.context(f"fill {color_str} --classify\n")
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

        self.choices = ["px", "pt", "mm", "cm", "inch", "mil"]
        self.combo_units = wx.ComboBox(
            self.parent,
            wx.ID_ANY,
            choices=self.choices,
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
        self.parent.Bind(wx.EVT_COMBOBOX, self.on_stroke_width, self.combo_units)
        # self.parent.Bind(wx.EVT_TEXT_ENTER, self.on_stroke_width, self.spin_width)
        self.parent.Bind(wx.EVT_TEXT_ENTER, self.on_stroke_width, self.spin_width)
        self.Add(self.strokewidth_label, 0, 0, 0)
        self.Add(self.spin_width, 1, wx.EXPAND, 0)
        self.Add(self.combo_units, 1, wx.EXPAND, 0)

    def on_stroke_width(self, event):
        if self.startup or self.combo_units.GetSelection() < 0:
            return
        try:
            self.context.signal(
                "selstrokewidth",
                f"{float(self.spin_width.GetValue()):.2f}"
                f"{self.choices[self.combo_units.GetSelection()]}",
            )
        except ValueError:
            pass

    def Signal(self, signal, *args):
        if signal == "emphasized":
            value = self.context.elements.has_emphasis()
            sw_default = None
            for e in self.context.elements.flat(types=elem_nodes, emphasized=True):
                if hasattr(e, "stroke_width"):
                    if sw_default is None:
                        sw_default = e.stroke_width
                        break
            if sw_default is not None:
                # Set Values
                self.startup = True
                stdlen = float(Length("1mm"))
                value = f"{sw_default / stdlen:.2f}"
                self.spin_width.SetValue(value)
                self.combo_units.SetSelection(self.choices.index("mm"))
                self.startup = False
