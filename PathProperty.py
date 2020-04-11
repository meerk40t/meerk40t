import wx

from Kernel import Module
from LaserRender import swizzlecolor
from svgelements import *

_ = wx.GetTranslation


class PathProperty(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: PathProperty.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((288, 303))
        self.text_name = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_stroke_none = wx.Button(self, wx.ID_ANY, _("None"))
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

        self.button_fill_none = wx.Button(self, wx.ID_ANY, _("None"))
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

        self.Bind(wx.EVT_TEXT, self.on_text_name_change, self.text_name)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_name_change, self.text_name)
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
        self.path_element = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        self.kernel.module_instance_remove(self.name)
        event.Skip()  # Call destroy.

    def set_element(self, element):
        self.path_element = element
        try:
            if element.stroke is not None and element.stroke != "none":
                color = wx.Colour(swizzlecolor(element.stroke))
                self.text_name.SetBackgroundColour(color)
        except AttributeError:
            pass

    def initialize(self, kernel, name=None):
        kernel.module_instance_close(name)
        Module.initialize(kernel, name)
        self.kernel = kernel
        self.name = name
        self.Show()

    def shutdown(self, kernel):
        self.Close()
        Module.shutdown(self, kernel)
        self.kernel = None

    def __set_properties(self):
        # begin wxGlade: PathProperty.__set_properties
        self.SetTitle(_("Path Properties"))
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
        # begin wxGlade: PathProperty.__do_layout
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_9 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Fill Color")), wx.VERTICAL)
        sizer_7 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Stroke Color")), wx.VERTICAL)
        sizer_8.Add(self.text_name, 0, wx.EXPAND, 0)
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

    def on_text_name_change(self, event):  # wxGlade: ElementProperty.<event_handler>
        try:
            self.path_element.name = self.text_name.GetValue()
            if self.kernel is not None:
                self.kernel.signal("element_property_update", self.path_element)
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
                self.path_element.stroke = color
                self.path_element.values[SVG_ATTR_STROKE] = color.hex
            else:
                self.path_element.stroke = Color('none')
                self.path_element.values[SVG_ATTR_STROKE] = 'none'
        elif 'fill' in button.name:
            if color is not None:
                self.path_element.fill = color
                self.path_element.values[SVG_ATTR_FILL] = color.hex
            else:
                self.path_element.fill = Color('none')
                self.path_element.values[SVG_ATTR_FILL] = 'none'
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.path_element)
            self.kernel.signal("refresh_scene", 0)
