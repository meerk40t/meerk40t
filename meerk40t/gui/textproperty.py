import wx

from ..svgelements import SVG_ATTR_FILL, SVG_ATTR_STROKE, Color
from .icons import icons8_choose_font_50, icons8_text_50
from .laserrender import swizzlecolor
from .mwindow import MWindow

_ = wx.GetTranslation


class TextProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(317, 360, *args, **kwds)

        self.text_text = wx.TextCtrl(self, wx.ID_ANY, "")
        self.element = node.object
        self.element_node = node
        self.label_fonttest = wx.StaticText(self, wx.ID_ANY, "")
        self.label_fonttest.SetFont(
            wx.Font(
                16,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        self.button_choose_font = wx.BitmapButton(
            self, wx.ID_ANY, icons8_choose_font_50.GetBitmap()
        )
        self.button_stroke_none = wx.Button(self, wx.ID_ANY, "None")
        self.button_stroke_none.name = "stroke none"
        self.button_stroke_F00 = wx.Button(self, wx.ID_ANY, "")
        self.button_stroke_F00.name = "stroke #F00"
        self.button_stroke_0F0 = wx.Button(self, wx.ID_ANY, "")
        self.button_stroke_0F0.name = "stroke #0F0"
        self.button_stroke_00F = wx.Button(self, wx.ID_ANY, "")
        self.button_stroke_00F.name = "stroke #00F"
        self.button_stroke_F0F = wx.Button(self, wx.ID_ANY, "")
        self.button_stroke_F0F.name = "stroke #F0F"
        self.button_stroke_0FF = wx.Button(self, wx.ID_ANY, "")
        self.button_stroke_0FF.name = "stroke #0FF"
        self.button_stroke_FF0 = wx.Button(self, wx.ID_ANY, "")
        self.button_stroke_FF0.name = "stroke #FF0"
        self.button_stroke_000 = wx.Button(self, wx.ID_ANY, "")
        self.button_stroke_000.name = "stroke #000"

        self.button_fill_none = wx.Button(self, wx.ID_ANY, "None")
        self.button_fill_none.name = "fill none"
        self.button_fill_F00 = wx.Button(self, wx.ID_ANY, "")
        self.button_fill_F00.name = "fill #F00"
        self.button_fill_0F0 = wx.Button(self, wx.ID_ANY, "")
        self.button_fill_0F0.name = "fill #0F0"
        self.button_fill_00F = wx.Button(self, wx.ID_ANY, "")
        self.button_fill_00F.name = "fill #00F"
        self.button_fill_F0F = wx.Button(self, wx.ID_ANY, "")
        self.button_fill_F0F.name = "fill #F0F"
        self.button_fill_0FF = wx.Button(self, wx.ID_ANY, "")
        self.button_fill_0FF.name = "fill #0FF"
        self.button_fill_FF0 = wx.Button(self, wx.ID_ANY, "")
        self.button_fill_FF0.name = "fill #FF0"
        self.button_fill_000 = wx.Button(self, wx.ID_ANY, "")
        self.button_fill_000.name = "fill #000"

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TEXT, self.on_text_name_change, self.text_text)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_name_change, self.text_text)
        self.Bind(wx.EVT_BUTTON, self.on_button_choose_font, self.button_choose_font)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_stroke_none)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_stroke_F00)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_stroke_0F0)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_stroke_00F)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_stroke_F0F)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_stroke_0FF)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_stroke_FF0)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_stroke_000)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_fill_none)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_fill_F00)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_fill_0F0)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_fill_00F)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_fill_F0F)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_fill_0FF)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_fill_FF0)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_fill_000)

    def restore(self, *args, node=None, **kwds):
        self.element_node = node
        self.element = node.object
        self.set_widgets()

    def window_open(self):
        self.set_widgets()

    def window_close(self):
        pass

    def set_widgets(self):
        try:
            if self.element.text is not None:
                self.text_text.SetValue(self.element.text)
                self.label_fonttest.SetLabelText(self.element.text)
                try:
                    self.label_fonttest.SetFont(self.element_node.wxfont)
                except AttributeError:
                    pass
                self.context.signal("refresh_scene", 0)
        except AttributeError:
            pass

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_text_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: TextProperty.__set_properties
        self.SetTitle("Text Properties")
        self.button_choose_font.SetSize(self.button_choose_font.GetBestSize())
        self.button_stroke_none.SetToolTip(_('"none" defined value'))
        self.button_stroke_F00.SetBackgroundColour(wx.Colour(255, 0, 0))
        self.button_stroke_F00.SetToolTip(_("#FF0000 defined values."))
        self.button_stroke_0F0.SetBackgroundColour(wx.Colour(0, 255, 0))
        self.button_stroke_0F0.SetToolTip(_("#00FF00 defined values."))
        self.button_stroke_00F.SetBackgroundColour(wx.Colour(0, 0, 255))
        self.button_stroke_00F.SetToolTip(_("#00FF00 defined values."))
        self.button_stroke_F0F.SetBackgroundColour(wx.Colour(255, 0, 255))
        self.button_stroke_F0F.SetToolTip(_("#FF00FF defined values."))
        self.button_stroke_0FF.SetBackgroundColour(wx.Colour(0, 255, 255))
        self.button_stroke_0FF.SetToolTip(_("#00FFFF defined values."))
        self.button_stroke_FF0.SetBackgroundColour(wx.Colour(255, 255, 0))
        self.button_stroke_FF0.SetToolTip(_("#FFFF00 defined values."))
        self.button_stroke_000.SetBackgroundColour(wx.Colour(0, 0, 0))
        self.button_stroke_000.SetToolTip(_("#000000 defined values."))
        self.button_fill_none.SetToolTip(_('"none" defined value'))
        self.button_fill_F00.SetBackgroundColour(wx.Colour(255, 0, 0))
        self.button_fill_F00.SetToolTip(_("#FF0000 defined values."))
        self.button_fill_0F0.SetBackgroundColour(wx.Colour(0, 255, 0))
        self.button_fill_0F0.SetToolTip(_("#00FF00 defined values."))
        self.button_fill_00F.SetBackgroundColour(wx.Colour(0, 0, 255))
        self.button_fill_00F.SetToolTip(_("#00FF00 defined values."))
        self.button_fill_F0F.SetBackgroundColour(wx.Colour(255, 0, 255))
        self.button_fill_F0F.SetToolTip(_("#FF00FF defined values."))
        self.button_fill_0FF.SetBackgroundColour(wx.Colour(0, 255, 255))
        self.button_fill_0FF.SetToolTip(_("#00FFFF defined values."))
        self.button_fill_FF0.SetBackgroundColour(wx.Colour(255, 255, 0))
        self.button_fill_FF0.SetToolTip(_("#FFFF00 defined values."))
        self.button_fill_000.SetBackgroundColour(wx.Colour(0, 0, 0))
        self.button_fill_000.SetToolTip(_("#000000 defined values."))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: TextProperty.__do_layout
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_9 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Fill Color")), wx.VERTICAL
        )
        sizer_7 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Stroke Color")), wx.VERTICAL
        )
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_8.Add(self.text_text, 0, wx.EXPAND, 0)
        sizer_3.Add(self.button_choose_font, 0, 0, 0)
        sizer_3.Add(self.label_fonttest, 1, wx.EXPAND, 0)
        sizer_8.Add(sizer_3, 0, wx.EXPAND, 0)
        sizer_7.Add(self.button_stroke_none, 0, wx.EXPAND, 0)
        sizer_7.Add(self.button_stroke_F00, 0, wx.EXPAND, 0)
        sizer_7.Add(self.button_stroke_0F0, 0, wx.EXPAND, 0)
        sizer_7.Add(self.button_stroke_00F, 0, wx.EXPAND, 0)
        sizer_7.Add(self.button_stroke_F0F, 0, wx.EXPAND, 0)
        sizer_7.Add(self.button_stroke_0FF, 0, wx.EXPAND, 0)
        sizer_7.Add(self.button_stroke_FF0, 0, wx.EXPAND, 0)
        sizer_7.Add(self.button_stroke_000, 0, wx.EXPAND, 0)
        sizer_6.Add(sizer_7, 1, wx.EXPAND, 0)
        sizer_9.Add(self.button_fill_none, 0, wx.EXPAND, 0)
        sizer_9.Add(self.button_fill_F00, 0, wx.EXPAND, 0)
        sizer_9.Add(self.button_fill_0F0, 0, wx.EXPAND, 0)
        sizer_9.Add(self.button_fill_00F, 0, wx.EXPAND, 0)
        sizer_9.Add(self.button_fill_F0F, 0, wx.EXPAND, 0)
        sizer_9.Add(self.button_fill_0FF, 0, wx.EXPAND, 0)
        sizer_9.Add(self.button_fill_FF0, 0, wx.EXPAND, 0)
        sizer_9.Add(self.button_fill_000, 0, wx.EXPAND, 0)
        sizer_6.Add(sizer_9, 1, wx.EXPAND, 0)
        sizer_8.Add(sizer_6, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_8)
        self.Layout()
        self.Centre()
        # end wxGlade

    def update_label(self):
        element = self.element
        element_node = self.element_node
        try:
            self.label_fonttest.SetFont(element_node.wxfont)
        except AttributeError:
            pass
        self.label_fonttest.SetLabelText(element.text)
        self.label_fonttest.SetForegroundColour(wx.Colour(swizzlecolor(element.fill)))

    def refresh(self):
        self.context.signal("element_property_update", self.element)
        self.context.signal("refresh_scene", 0)

    def on_text_name_change(self, event):  # wxGlade: TextProperty.<event_handler>
        try:
            self.element.text = self.text_text.GetValue()
            self.update_label()
            self.refresh()
        except AttributeError:
            pass
        event.Skip()

    def on_button_choose_font(self, event):  # wxGlade: TextProperty.<event_handler>
        font_data = wx.FontData()
        try:
            font_data.SetInitialFont(self.element_node.wxfont)
            font_data.SetColour(wx.Colour(swizzlecolor(self.element.fill)))
            dialog = wx.FontDialog(None, font_data)
        except AttributeError:
            dialog = wx.FontDialog(None, font_data)
        if dialog.ShowModal() == wx.ID_OK:
            data = dialog.GetFontData()
            font = data.GetChosenFont()
            try:
                color = data.GetColour()
                rgb = color.GetRGB()
                color = swizzlecolor(rgb)
                color = Color(color, 1.0)
                self.element.fill = color
            except Exception:  # rgb get failed.
                pass
            self.element_node.wxfont = font
            self.update_label()
            self.refresh()
        dialog.Destroy()
        event.Skip()

    def on_button_color(self, event):  # wxGlade: TextProperty.<event_handler>
        button = event.EventObject
        color = None
        if "none" not in button.name:
            color = button.GetBackgroundColour()
            rgb = color.GetRGB()
            color = swizzlecolor(rgb)
            color = Color(color, 1.0)
        if "stroke" in button.name:
            if color is not None:
                self.element.stroke = color
                self.element.values[SVG_ATTR_STROKE] = color.hex
                self.element.node.altered()
            else:
                self.element.stroke = Color("none")
                self.element.values[SVG_ATTR_STROKE] = "none"
                self.element.node.altered()
        elif "fill" in button.name:
            if color is not None:
                self.element.fill = color
                self.element.values[SVG_ATTR_FILL] = color.hex
                self.element.node.altered()
            else:
                self.element.fill = Color("none")
                self.element.values[SVG_ATTR_FILL] = "none"
                self.element.node.altered()
        self.update_label()
        self.refresh()
        event.Skip()
