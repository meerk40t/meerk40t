import wx

from .mwindow import MWindow
from ..svgelements import SVG_ATTR_FILL, SVG_ATTR_ID, SVG_ATTR_STROKE, Color
from .icons import icons8_vector_50
from .laserrender import swizzlecolor

_ = wx.GetTranslation


class PathProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(288, 303, *args, **kwds)

        self.element = node.object
        self.element_node = node

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

        try:
            if node.object.id is not None:
                self.text_name.SetValue(str(node.object.id))
        except AttributeError:
            pass
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

    def restore(self, *args, node=None, **kwds):
        self.element = node.object
        self.element_node = node
        self.set_widgets()

    def set_widgets(self):
        try:
            if self.element.stroke is not None and self.element.stroke != "none":
                color = wx.Colour(swizzlecolor(self.element.stroke))
                self.text_name.SetBackgroundColour(color)
        except AttributeError:
            pass
        self.Refresh()

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_vector_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: PathProperty.__set_properties
        self.SetTitle(_("Path Properties"))
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
        # begin wxGlade: PathProperty.__do_layout
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_9 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Fill Color")), wx.VERTICAL
        )
        sizer_7 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Stroke Color")), wx.VERTICAL
        )
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
            self.element.id = self.text_name.GetValue()
            self.element.values[SVG_ATTR_ID] = self.element.id
            self.context.signal("element_property_update", self.element)
        except AttributeError:
            pass

    def on_button_color(self, event):  # wxGlade: ElementProperty.<event_handler>
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
                color = wx.Colour(swizzlecolor(self.element.stroke))
                self.text_name.SetBackgroundColour(color)
            else:
                self.element.stroke = Color("none")
                self.element.values[SVG_ATTR_STROKE] = "none"
                self.element.node.altered()
                self.text_name.SetBackgroundColour(wx.WHITE)
        elif "fill" in button.name:
            if color is not None:
                self.element.fill = color
                self.element.values[SVG_ATTR_FILL] = color.hex
                self.element.node.altered()
            else:
                self.element.fill = Color("none")
                self.element.values[SVG_ATTR_FILL] = "none"
                self.element.node.altered()
        self.element.node.emphasized = True
        self.Refresh()
        self.context("declassify\nclassify\n")
        self.context.signal("element_property_update", self.element)
        self.context.signal("refresh_scene", 0)
