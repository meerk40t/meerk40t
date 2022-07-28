import wx
from .statusbarwidget import StatusBarWidget

_ = wx.GetTranslation

class SBW_Color(StatusBarWidget):
    def __init__(self, parent, panelidx, identifier, context, **args):
        super().__init__(parent, panelidx, identifier, context, args)
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
            wx_button = wx.Button(
                self.parent, id=wx.ID_ANY, size=wx.Size(20, -1), label=""
            )
            wx_button.SetBackgroundColour(wx.Colour(colors[idx]))
            wx_button.SetMinSize(wx.Size(10, -1))
            wx_button.SetToolTip(_("Set stroke-color (right click set fill color)"))
            wx_button.Bind(wx.EVT_BUTTON, self.on_button_color_left)
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
                colstr = "none"
            else:
                colstr = "#%02x%02x%02x" % (rgb[0], rgb[1], rgb[2])
            self.context("stroke %s --classify\n" % colstr)
            self.context.signal("selstroke", rgb)

    def on_button_color_right(self, event):
        # Okay my backgroundcolor is...
        if not self.startup:
            button = event.EventObject
            color = button.GetBackgroundColour()
            rgb = [color.Red(), color.Green(), color.Blue()]
            if rgb[0] == 255 and rgb[1] == 255 and rgb[2] == 255:
                colstr = "none"
            else:
                colstr = "#%02x%02x%02x" % (rgb[0], rgb[1], rgb[2])
            self.context("fill %s --classify\n" % colstr)
            self.context.signal("selfill", rgb)

class SBW_Stroke(StatusBarWidget):
    def __init__(self, parent, panelidx, identifier, context, **args):
        super().__init__(parent, panelidx, identifier, context, args)
        FONT_SIZE = 7

        # Plus one combobox + value field for stroke width
        self.strokewidth_label = wx.StaticText(
            self.parent, id=wx.ID_ANY, label=_("Stroke:")
        )
        self.strokewidth_label.SetFont(
            wx.Font(
                FONT_SIZE,
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
                FONT_SIZE,
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
                FONT_SIZE,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        self.combo_units.SetMinSize(wx.Size(30, -1))
        self.combo_units.SetMaxSize(wx.Size(120, -1))
        self.combo_units.SetSelection(0)
        self.Bind(wx.EVT_COMBOBOX, self.on_stroke_width, self.combo_units)
        # self.Bind(wx.EVT_TEXT_ENTER, self.on_stroke_width, self.spin_width)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_stroke_width, self.spin_width)
        self.Add(self.strokewidth_label, 0, wx.EXPAND, 1)
        self.Add(self.spin_width, 1, wx.EXPAND, 1)
        self.Add(self.combo_units, 1, wx.EXPAND, 1)

    def SetValues(self, swidth):
        return

    def on_stroke_width(self, event):
        if not self.startup:
            chg = False
            if self.combo_units.GetSelection() >= 0:
                newunit = self.choices[self.combo_units.GetSelection()]
                try:
                    newval = float(self.spin_width.GetValue())
                    chg = True
                except ValueError:
                    chg = False
            if chg:
                value = "{wd:.2f}{unit}".format(wd=newval, unit=newunit)
                mysignal = "selstrokewidth"
                self.context.signal(mysignal, value)

