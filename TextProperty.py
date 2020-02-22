import wx

from LaserRender import swizzlecolor
from icons import icons8_bold_50, icons8_underline_50, icons8_italic_50
from svgelements import *

_ = wx.GetTranslation


class TextProperty(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: TextProperty.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((317, 426))
        self.text_text = wx.TextCtrl(self, wx.ID_ANY, "")
        self.combo_font_size = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.combo_font = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.button_bold = wx.ToggleButton(self, wx.ID_ANY, "")
        self.button_italic = wx.ToggleButton(self, wx.ID_ANY, "")
        self.button_underline = wx.ToggleButton(self, wx.ID_ANY, "")
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
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_font_size, self.combo_font_size)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_font, self.combo_font)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_bold, self.button_bold)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_italic, self.button_italic)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_underline, self.button_underline)
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
        # end wxGlade
        self.kernel = None
        self.text_element = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        self.kernel.mark_window_closed("PathProperty")
        event.Skip()  # Call destroy.

    def set_element(self, element):
        self.text_element = element
        try:
            if element.stroke is not None and element.stroke != "none":
                color = wx.Colour(swizzlecolor(element.stroke))
                self.text_text.SetBackgroundColour(color)
        except AttributeError:
            pass

    def set_kernel(self, kernel):
        self.kernel = kernel

    def __set_properties(self):
        # begin wxGlade: TextProperty.__set_properties
        self.SetTitle(_("Text Properties"))
        self.button_bold.SetMinSize((52, 52))
        self.button_bold.SetBitmap(icons8_bold_50.GetBitmap())
        self.button_italic.SetMinSize((52, 52))
        self.button_italic.SetBitmap(icons8_italic_50.GetBitmap())
        self.button_underline.SetMinSize((52, 52))
        self.button_underline.SetBitmap(icons8_underline_50.GetBitmap())
        self.button_stroke_none.SetToolTip(_("\"none\" defined value"))
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
        self.button_fill_none.SetToolTip(_("\"none\" defined value"))
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
        sizer_9 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Fill Color")), wx.VERTICAL)
        sizer_7 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Stroke Color")), wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_8.Add(self.text_text, 0, wx.EXPAND, 0)
        label_1 = wx.StaticText(self, wx.ID_ANY, _("Font Size:"))
        sizer_1.Add(label_1, 1, 0, 0)
        sizer_1.Add(self.combo_font_size, 2, 0, 0)
        sizer_8.Add(sizer_1, 1, wx.EXPAND, 0)
        label_2 = wx.StaticText(self, wx.ID_ANY, _("Font:"))
        sizer_2.Add(label_2, 1, 0, 0)
        sizer_2.Add(self.combo_font, 2, 0, 0)
        sizer_8.Add(sizer_2, 1, wx.EXPAND, 0)
        sizer_3.Add(self.button_bold, 0, 0, 0)
        sizer_3.Add(self.button_italic, 0, 0, 0)
        sizer_3.Add(self.button_underline, 0, 0, 0)
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

    def on_combo_font_size(self, event):  # wxGlade: TextProperty.<event_handler>
        event.Skip()

    def on_combo_font(self, event):  # wxGlade: TextProperty.<event_handler>
        event.Skip()

    def on_button_bold(self, event):  # wxGlade: TextProperty.<event_handler>
        event.Skip()

    def on_button_italic(self, event):  # wxGlade: TextProperty.<event_handler>
        event.Skip()

    def on_button_underline(self, event):  # wxGlade: TextProperty.<event_handler>
        event.Skip()

    def on_text_name_change(self, event):  # wxGlade: ElementProperty.<event_handler>
        try:
            self.text_element.text = self.text_text.GetValue()
            if self.kernel is not None:
                self.kernel.signal("element_property_update", self.text_element)
        except AttributeError:
            pass

    def on_button_color(self, event):  # wxGlade: ElementProperty.<event_handler>
        button = event.EventObject
        color = None
        if 'none' not in button.name:
            color = button.GetBackgroundColour()
            rgb = color.GetRGB()
            color = swizzlecolor(rgb)
            color = Color(color, 1.0)
        if 'stroke' in button.name:
            if color is not None:
                self.text_element.stroke = color
                self.text_element.values[SVG_ATTR_STROKE] = color.hex
            else:
                self.text_element.stroke = Color('none')
                self.text_element.values[SVG_ATTR_STROKE] = 'none'
        elif 'fill' in button.name:
            if color is not None:
                self.text_element.fill = color
                self.text_element.values[SVG_ATTR_FILL] = color.hex
            else:
                self.text_element.fill = Color('none')
                self.text_element.values[SVG_ATTR_FILL] = 'none'
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.text_element)
            self.kernel.signal("refresh_scene", 0)
