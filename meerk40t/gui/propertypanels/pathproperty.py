import wx

from meerk40t.gui.wxutils import ScrolledPanel

from ...svgelements import Color
from ..icons import icons8_vector_50
from ..laserrender import swizzlecolor
from ..mwindow import MWindow
from ...core.units import Length

_ = wx.GetTranslation


class PathPropertyPanel(ScrolledPanel):
    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        self.node = node

        self.text_id = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_label = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
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
        self.color_info_stroke = wx.StaticText(self, wx.ID_ANY, "")
        self.color_info_fill = wx.StaticText(self, wx.ID_ANY, "")
        # Property display
        self.lbl_info_points = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.lbl_info_length = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.lbl_info_area   = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.btn_info_get = wx.Button(self, wx.ID_ANY, _("Retrieve"))

        self.__set_properties()
        self.__do_layout()

        self.text_id.Bind(wx.EVT_KILL_FOCUS, self.on_text_id_change)
        self.text_id.Bind(wx.EVT_TEXT_ENTER, self.on_text_id_change)
        self.text_label.Bind(wx.EVT_KILL_FOCUS, self.on_text_label_change)
        self.text_label.Bind(wx.EVT_TEXT_ENTER, self.on_text_label_change)
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

        self.Bind(wx.EVT_BUTTON, self.on_btn_get_infos, self.btn_info_get)

    @staticmethod
    def accepts(node):
        if node.type == "elem text":
            return False
        elif node.type.startswith("elem"):
            return True
        return False

    def on_btn_get_infos(self, event):
        def closed_path(path):
            p1 = path.first_point
            p2 = path.current_point
            # print (p1, p2)
            # print (type(p1).__name__, type(p2).__name__)
            return p1 == p2

        elements = self.context.elements
        _mm = float(Length("1mm"))
        total_area = 0
        total_length = 0

        this_area, this_length = elements.get_information(self.node, density=50)
        total_area += this_area
        total_length += this_length

        total_area = total_area / (_mm * _mm)
        total_length = total_length / _mm
        try:
            testpath = self.node.as_path()
            points = len(testpath.segments())
            if closed_path(testpath):
                points = max(0, points - 1)
        except AttributeError:
            points = 0

        self.lbl_info_area.SetValue(f"{total_area:.1f} mm²")
        self.lbl_info_length.SetValue(f"{total_length:.1f} mm")
        self.lbl_info_points.SetValue(f"{points:d}")

    def set_widgets(self, node):
        if node is not None:
            self.node = node
        try:
            if self.node.stroke is not None and self.node.stroke != "none":
                color = wx.Colour(swizzlecolor(self.node.stroke))
                self.text_id.SetBackgroundColour(color)
        except AttributeError:
            pass
        try:
            if node.id is not None:
                self.text_id.SetValue(str(node.id))
        except AttributeError:
            pass
        try:
            if node.label is not None:
                self.text_label.SetValue(str(node.label))
        except AttributeError:
            pass
        s_stroke = "None"
        s_fill = "None"
        if self.node is not None:
            if self.node.stroke is not None and self.node.stroke.argb is not None:
                scol = self.node.stroke
                wcol = wx.Colour(swizzlecolor(scol))
                s = ""
                try:
                    s = wcol.GetAsString(wx.C2S_NAME)
                except AssertionError:
                    s = ""
                if s != "":
                    s = s + " (" + scol.hexrgb + ")"
                else:
                    s = scol.hexrgb
                s_stroke = s
            if self.node.fill is not None and self.node.fill.argb is not None:
                scol = self.node.fill
                wcol = wx.Colour(swizzlecolor(scol))
                s = ""
                try:
                    s = wcol.GetAsString(wx.C2S_NAME)
                except AssertionError:
                    s = ""
                if s != "":
                    s = s + " (" + scol.hexrgb + ")"
                else:
                    s = scol.hexrgb
                s_fill = s
        self.color_info_stroke.SetLabel(s_stroke)
        self.color_info_fill.SetLabel(s_fill)
        self.lbl_info_area.SetValue("")
        self.lbl_info_length.SetValue("")
        self.lbl_info_points.SetValue("")

        self.Refresh()

    def __set_properties(self):
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
        sizer_v_main = wx.BoxSizer(wx.VERTICAL)
        sizer_h_colors = wx.BoxSizer(wx.HORIZONTAL)
        sizer_v_col_fill = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Fill Color")), wx.VERTICAL
        )
        sizer_v_col_stroke = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Stroke Color")), wx.VERTICAL
        )
        sizer_id_label = wx.BoxSizer(wx.HORIZONTAL)
        sizer_id = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Id")), wx.VERTICAL
        )
        sizer_id.Add(self.text_id, 1, wx.EXPAND, 0)
        sizer_label = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Label")), wx.VERTICAL
        )
        sizer_label.Add(self.text_label, 1, wx.EXPAND, 0)
        sizer_id_label.Add(sizer_id, 1, wx.EXPAND, 0)
        sizer_id_label.Add(sizer_label, 1, wx.EXPAND, 0)

        sizer_v_col_stroke.Add(self.button_stroke_none, 0, wx.EXPAND, 0)
        sizer_v_col_stroke.Add(self.button_stroke_F00, 0, wx.EXPAND, 0)
        sizer_v_col_stroke.Add(self.button_stroke_0F0, 0, wx.EXPAND, 0)
        sizer_v_col_stroke.Add(self.button_stroke_00F, 0, wx.EXPAND, 0)
        sizer_v_col_stroke.Add(self.button_stroke_F0F, 0, wx.EXPAND, 0)
        sizer_v_col_stroke.Add(self.button_stroke_0FF, 0, wx.EXPAND, 0)
        sizer_v_col_stroke.Add(self.button_stroke_FF0, 0, wx.EXPAND, 0)
        sizer_v_col_stroke.Add(self.button_stroke_000, 0, wx.EXPAND, 0)
        sizer_v_col_stroke.Add(self.color_info_stroke, 0, wx.EXPAND, 0)

        sizer_v_col_fill.Add(self.button_fill_none, 0, wx.EXPAND, 0)
        sizer_v_col_fill.Add(self.button_fill_F00, 0, wx.EXPAND, 0)
        sizer_v_col_fill.Add(self.button_fill_0F0, 0, wx.EXPAND, 0)
        sizer_v_col_fill.Add(self.button_fill_00F, 0, wx.EXPAND, 0)
        sizer_v_col_fill.Add(self.button_fill_F0F, 0, wx.EXPAND, 0)
        sizer_v_col_fill.Add(self.button_fill_0FF, 0, wx.EXPAND, 0)
        sizer_v_col_fill.Add(self.button_fill_FF0, 0, wx.EXPAND, 0)
        sizer_v_col_fill.Add(self.button_fill_000, 0, wx.EXPAND, 0)
        sizer_v_col_fill.Add(self.color_info_fill, 0, wx.EXPAND, 0)

        sizer_h_colors.Add(sizer_v_col_stroke, 1, wx.EXPAND, 0)
        sizer_h_colors.Add(sizer_v_col_fill, 1, wx.EXPAND, 0)

        sizer_h_infos = wx.BoxSizer(wx.HORIZONTAL)
        sizer_info1 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Points")), wx.VERTICAL
        )
        sizer_info1.Add(self.lbl_info_points, 1, wx.EXPAND, 0)

        sizer_info2 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Length")), wx.VERTICAL
        )
        sizer_info2.Add(self.lbl_info_length, 1, wx.EXPAND, 0)

        sizer_info3 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Area")), wx.VERTICAL
        )
        sizer_info3.Add(self.lbl_info_area, 1, wx.EXPAND, 0)

        sizer_h_infos.Add(sizer_info1, 1, wx.EXPAND, 0)
        sizer_h_infos.Add(sizer_info2, 1, wx.EXPAND, 0)
        sizer_h_infos.Add(sizer_info3, 1, wx.EXPAND, 0)
        sizer_h_infos.Add(self.btn_info_get, 0, wx.EXPAND, 0)

        sizer_v_main.Add(sizer_id_label, 0, wx.EXPAND, 0)
        sizer_v_main.Add(sizer_h_colors, 1, wx.EXPAND, 0)
        sizer_v_main.Add(sizer_h_infos, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_v_main)
        self.Layout()
        self.Centre()
        # end wxGlade

    def on_text_id_change(self, event=None):
        try:
            self.node.id = self.text_id.GetValue()
            self.context.elements.signal("element_property_update", self.node)
        except AttributeError:
            pass

    def on_text_label_change(self, event=None):
        try:
            self.node.label = self.text_label.GetValue()
            self.context.elements.signal("element_property_update", self.node)
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
                self.node.stroke = color
                self.node.altered()
                color = wx.Colour(swizzlecolor(self.node.stroke))
                self.text_id.SetBackgroundColour(color)
            else:
                self.node.stroke = Color("none")
                self.node.altered()
                self.text_id.SetBackgroundColour(wx.WHITE)
        elif "fill" in button.name:
            if color is not None:
                self.node.fill = color
                self.node.altered()
            else:
                self.node.fill = Color("none")
                self.node.altered()
        self.node.emphasized = True
        self.Refresh()
        self.context("declassify\nclassify\n")
        self.context.elements.signal("element_property_update", self.node)


class PathProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(288, 303, *args, **kwds)

        self.panel = PathPropertyPanel(self, wx.ID_ANY, context=self.context, node=node)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_vector_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: PathProperty.__set_properties
        self.SetTitle(_("Path Properties"))

    def delegate(self):
        yield self.panel

    def restore(self, *args, node=None, **kwds):
        self.panel.set_widgets(node)

    def window_preserve(self):
        return False

    def window_menu(self):
        return False
