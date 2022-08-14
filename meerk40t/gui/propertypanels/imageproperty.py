import wx
from wx.lib.scrolledpanel import ScrolledPanel

from ...core.units import Length
from ..icons import icons8_image_50
from ..mwindow import MWindow
from ..wxutils import TextCtrl

_ = wx.GetTranslation


class ImagePropertyPanel(ScrolledPanel):
    def __init__(self, *args, context=None, node=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.node = node
        self.text_id = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_label = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)

        self.text_dpi = TextCtrl(
            self, wx.ID_ANY, "500", style=wx.TE_PROCESS_ENTER, check="float"
        )
        self.text_x = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY, limited=True)
        self.text_y = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY, limited=True)
        self.text_width = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY, limited=True
        )
        self.text_height = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY, limited=True
        )

        self.check_enable_dither = wx.CheckBox(self, wx.ID_ANY, _("Dither"))
        self.choices = [
            "Floyd-Steinberg",
            "Atkinson",
            "Jarvis-Judice-Ninke",
            "Stucki",
            "Burkes",
            "Sierra3",
            "Sierra2",
            "Sierra-2-4a",
        ]
        self.combo_dither = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=self.choices,
            style=wx.CB_DROPDOWN,
        )

        self.check_invert_grayscale = wx.CheckBox(self, wx.ID_ANY, _("Invert"))
        self.slider_grayscale_red = wx.Slider(
            self, wx.ID_ANY, 0, -1000, 1000, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_grayscale_red = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.slider_grayscale_green = wx.Slider(
            self, wx.ID_ANY, 0, -1000, 1000, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_grayscale_green = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.slider_grayscale_blue = wx.Slider(
            self, wx.ID_ANY, 0, -1000, 1000, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_grayscale_blue = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.slider_grayscale_lightness = wx.Slider(
            self, wx.ID_ANY, 500, 0, 1000, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_grayscale_lightness = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )

        self.__set_properties()
        self.__do_layout()

        self.text_id.Bind(wx.EVT_KILL_FOCUS, self.on_text_id_change)
        self.text_id.Bind(wx.EVT_TEXT_ENTER, self.on_text_id_change)
        self.text_label.Bind(wx.EVT_KILL_FOCUS, self.on_text_label_change)
        self.text_label.Bind(wx.EVT_TEXT_ENTER, self.on_text_label_change)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_enable_dither, self.check_enable_dither
        )
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_dither_type, self.combo_dither)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_combo_dither_type, self.combo_dither)

        self.text_dpi.Bind(wx.EVT_KILL_FOCUS, self.on_text_dpi)
        self.text_dpi.Bind(wx.EVT_TEXT_ENTER, self.on_text_dpi)

        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_invert_grayscale, self.check_invert_grayscale
        )
        self.Bind(
            wx.EVT_SLIDER,
            self.on_slider_grayscale_component,
            self.slider_grayscale_lightness,
        )
        self.Bind(
            wx.EVT_SLIDER, self.on_slider_grayscale_component, self.slider_grayscale_red
        )
        self.Bind(
            wx.EVT_SLIDER,
            self.on_slider_grayscale_component,
            self.slider_grayscale_green,
        )
        self.Bind(
            wx.EVT_SLIDER,
            self.on_slider_grayscale_component,
            self.slider_grayscale_blue,
        )
        # self.check_enable_grayscale.SetValue(op["enable"])
        self.check_invert_grayscale.SetValue(node.invert)

        self.slider_grayscale_red.SetValue(int(node.red * 500.0))
        self.text_grayscale_red.SetValue(str(node.red))

        self.slider_grayscale_green.SetValue(int(node.green * 500.0))
        self.text_grayscale_green.SetValue(str(node.green))

        self.slider_grayscale_blue.SetValue(int(node.blue * 500.0))
        self.text_grayscale_blue.SetValue(str(node.blue))

        self.slider_grayscale_lightness.SetValue(int(node.lightness * 500.0))
        self.text_grayscale_lightness.SetValue(str(node.lightness))
        self.set_widgets()

    @staticmethod
    def accepts(node):
        if node.type == "elem image":
            return True
        return False

    def set_widgets(self, node=None):
        if node is None:
            node = self.node
        if node is None:
            return
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

        self.text_dpi.SetValue(str(node.dpi))
        try:
            bounds = node.bounds
            self.text_x.SetValue(
                Length(amount=bounds[0], unitless=1, digits=2).length_mm
            )
            self.text_y.SetValue(
                Length(amount=bounds[1], unitless=1, digits=2).length_mm
            )
            self.text_width.SetValue(
                Length(amount=bounds[2] - bounds[0], unitless=1, digits=2).length_mm
            )
            self.text_height.SetValue(
                Length(amount=bounds[3] - bounds[1], unitless=1, digits=2).length_mm
            )
        except AttributeError:
            pass
        self.check_enable_dither.SetValue(node.dither)
        self.combo_dither.SetValue(node.dither_type)

    def __set_properties(self):
        self.text_x.SetToolTip(_("X property of image"))
        self.text_y.SetToolTip(_("Y property of image"))
        self.text_width.SetToolTip(_("Width property of image"))
        self.text_height.SetToolTip(_("Height property of image"))
        self.check_enable_dither.SetToolTip(_("Enable Dither"))
        self.check_enable_dither.SetValue(1)
        self.combo_dither.SetToolTip(_("Select dither algorithm to use"))
        self.combo_dither.SetSelection(0)
        self.check_invert_grayscale.SetToolTip(_("Invert Grayscale"))
        self.slider_grayscale_red.SetToolTip(_("Red component amount"))
        self.text_grayscale_red.SetToolTip(_("Red Factor"))
        self.slider_grayscale_green.SetToolTip(_("Green component control"))
        self.text_grayscale_green.SetToolTip(_("Green Factor"))
        self.slider_grayscale_blue.SetToolTip(_("Blue component control"))
        self.text_grayscale_blue.SetToolTip(_("Blue Factor"))
        self.slider_grayscale_lightness.SetToolTip(_("Lightness control"))
        self.text_grayscale_lightness.SetToolTip(_("Lightness"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ImageProperty.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_dim = wx.BoxSizer(wx.HORIZONTAL)
        sizer_xy = wx.BoxSizer(wx.HORIZONTAL)
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
        sizer_main.Add(sizer_id_label, 0, wx.EXPAND, 0)

        sizer_dpi = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("DPI:")), wx.VERTICAL
        )
        self.text_dpi.SetToolTip(_("Dots Per Inch"))
        sizer_dpi.Add(self.text_dpi, 0, 0, 0)

        sizer_main.Add(sizer_dpi, 0, wx.EXPAND, 0)
        label_x = wx.StaticText(self, wx.ID_ANY, _("X:"))
        label_y = wx.StaticText(self, wx.ID_ANY, _("Y:"))

        sizer_xy.Add(label_x, 1, wx.EXPAND, 0)
        sizer_xy.Add(self.text_x, 3, wx.EXPAND, 0)
        sizer_xy.Add(label_y, 1, wx.EXPAND, 0)
        sizer_xy.Add(self.text_y, 3, wx.EXPAND, 0)
        sizer_main.Add(sizer_xy, 0, wx.EXPAND, 0)

        label_w = wx.StaticText(self, wx.ID_ANY, _("Width:"))
        label_h = wx.StaticText(self, wx.ID_ANY, _("Height:"))
        sizer_dim.Add(label_w, 1, wx.EXPAND, 0)
        sizer_dim.Add(self.text_width, 3, wx.EXPAND, 0)
        sizer_dim.Add(label_h, 1, wx.EXPAND, 0)
        sizer_dim.Add(self.text_height, 3, wx.EXPAND, 0)
        sizer_main.Add(sizer_dim, 0, wx.EXPAND, 0)

        sizer_dither = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Dither")), wx.HORIZONTAL
        )
        sizer_dither.Add(self.check_enable_dither, 0, 0, 0)
        sizer_dither.Add(self.combo_dither, 0, wx.EXPAND, 0)

        sizer_main.Add(sizer_dither, 0, wx.EXPAND, 0)

        # -----

        sizer_rg = wx.BoxSizer(wx.HORIZONTAL)
        sizer_bl = wx.BoxSizer(wx.HORIZONTAL)
        sizer_grayscale = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Grayscale")), wx.VERTICAL
        )
        sizer_grayscale_lightness = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Lightness")), wx.HORIZONTAL
        )
        sizer_grayscale_blue = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Blue")), wx.HORIZONTAL
        )
        sizer_grayscale_green = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Green")), wx.HORIZONTAL
        )
        sizer_grayscale_red = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Red")), wx.HORIZONTAL
        )
        sizer_grayscale.Add(self.check_invert_grayscale, 0, 0, 0)
        sizer_grayscale_red.Add(self.slider_grayscale_red, 1, wx.EXPAND, 0)
        sizer_grayscale_red.Add(self.text_grayscale_red, 1, 0, 0)
        sizer_rg.Add(sizer_grayscale_red, 0, wx.EXPAND, 0)
        sizer_grayscale_green.Add(self.slider_grayscale_green, 1, wx.EXPAND, 0)
        sizer_grayscale_green.Add(self.text_grayscale_green, 1, 0, 0)
        sizer_rg.Add(sizer_grayscale_green, 0, wx.EXPAND, 0)
        sizer_grayscale_blue.Add(self.slider_grayscale_blue, 1, wx.EXPAND, 0)
        sizer_grayscale_blue.Add(self.text_grayscale_blue, 1, 0, 0)
        sizer_bl.Add(sizer_grayscale_blue, 0, wx.EXPAND, 0)
        sizer_grayscale_lightness.Add(self.slider_grayscale_lightness, 1, wx.EXPAND, 0)
        sizer_grayscale_lightness.Add(self.text_grayscale_lightness, 1, 0, 0)
        sizer_bl.Add(sizer_grayscale_lightness, 0, wx.EXPAND, 0)
        sizer_grayscale.Add(sizer_rg, 5, wx.EXPAND, 0)
        sizer_grayscale.Add(sizer_bl, 5, wx.EXPAND, 0)

        self.text_grayscale_red.SetMaxSize(wx.Size(70, -1))
        self.text_grayscale_green.SetMaxSize(wx.Size(70, -1))
        self.text_grayscale_blue.SetMaxSize(wx.Size(70, -1))
        self.text_grayscale_lightness.SetMaxSize(wx.Size(70, -1))

        sizer_main.Add(sizer_grayscale, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
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

    def on_text_dpi(self, event=None):  # wxGlade: ImageProperty.<event_handler>
        new_step = float(self.text_dpi.GetValue())
        self.node.dpi = new_step

    def on_check_enable_dither(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        self.node.dither = self.check_enable_dither.GetValue()
        self.node.update(self.context)

    def on_combo_dither_type(self, event=None):  # wxGlade: RasterWizard.<event_handler>
        self.node.dither_type = self.choices[self.combo_dither.GetSelection()]
        self.node.update(self.context)

    def on_check_invert_grayscale(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        self.node.invert = self.check_invert_grayscale.GetValue()
        self.node.update(self.context)

    def on_slider_grayscale_component(
        self, event=None
    ):  # wxGlade: GrayscalePanel.<event_handler>
        self.node.red = float(int(self.slider_grayscale_red.GetValue()) / 500.0)
        self.text_grayscale_red.SetValue(str(self.node.red))

        self.node.green = float(int(self.slider_grayscale_green.GetValue()) / 500.0)
        self.text_grayscale_green.SetValue(str(self.node.green))

        self.node.blue = float(int(self.slider_grayscale_blue.GetValue()) / 500.0)
        self.text_grayscale_blue.SetValue(str(self.node.blue))

        self.node.lightness = float(
            int(self.slider_grayscale_lightness.GetValue()) / 500.0
        )
        self.text_grayscale_lightness.SetValue(str(self.node.lightness))
        self.node.update(self.context)


class ImageProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(276, 218, *args, **kwds)

        self.panel = ImagePropertyPanel(
            self, wx.ID_ANY, context=self.context, node=node
        )
        self.add_module_delegate(self.panel)
        # begin wxGlade: ImageProperty.__set_properties
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_image_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Image Properties"))

    def restore(self, *args, node=None, **kwds):
        self.panel.set_widgets(node)

    def window_preserve(self):
        return False

    def window_menu(self):
        return False
