"""
This file contains routines to create some test patterns
to establish the correct kerf size of your laser
"""

import wx

from meerk40t.core.units import ACCEPTED_UNITS, Length
from meerk40t.gui.icons import STD_ICON_SIZE, icons8_hinges_50, icons8_detective_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import StaticBoxSizer, TextCtrl

_ = wx.GetTranslation

class KerfPanel(wx.Panel):
    """
    UI for KerfTest, allows setting of parameters
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        self.spin_count = wx.SpinCtrl(self, wx.ID_ANY, initial=5, min=1, max=100)
        self.text_min = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_max = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_dim = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_dim.set_range(0, 50)
        self.text_delta = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_delta.set_range(0, 50)
        color_choices = [_("Red"), _("Green"), _("Blue")]
        self.combo_color = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=color_choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.check_color_direction = wx.CheckBox(self, wx.ID_ANY, _("Growing"))
        self.radio_pattern = wx.RadioBox(self, wx.ID_ANY, _("Pattern"), choices=(_("Rectangular (box joints)"), _("Circular (inlays)")))

        self.button_create = wx.Button(self, wx.ID_ANY, _("Create Pattern"))
        self.button_create.SetBitmap(icons8_detective_50.GetBitmap(resize=25))

        self._set_layout()
        self._set_logic()
        self.Layout()

    def _set_logic(self):
        return

    def _set_layout(self):
        def size_it(ctrl, value):
            ctrl.SetMaxSize(wx.Size(int(value), -1))
            ctrl.SetMinSize(wx.Size(int(value * 0.75), -1))
            ctrl.SetSize(wx.Size(value, -1))

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_param = StaticBoxSizer(
            self, wx.ID_ANY, _("Parameters"), wx.VERTICAL
        )

        hline_type = wx.BoxSizer(wx.HORIZONTAL)
        hline_type.Add(self.radio_pattern, 0, wx.EXPAND, 0)
        hline_count = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Count:"))
        hline_count.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_count.Add(self.spin_count, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_min = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Minimum:"))
        hline_min.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_min.Add(self.text_min, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_max = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Maximum:"))
        hline_max.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_max.Add(self.text_max, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_dim = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Height:"))
        hline_dim.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_dim.Add(self.text_dim, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wx.StaticText(self, wx.ID_ANY, "mm")
        hline_dim.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_delta = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Delta:"))
        hline_delta.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_delta.Add(self.text_delta, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wx.StaticText(self, wx.ID_ANY, "mm")
        hline_delta.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_color = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Color:"))
        hline_color.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_color.Add(self.combo_color, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_color.Add(self.check_color_direction, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_param.Add(hline_type, 0, wx.EXPAND, 0)
        sizer_param.Add(hline_count, 0, wx.EXPAND, 0)
        sizer_param.Add(hline_min, 0, wx.EXPAND, 0)
        sizer_param.Add(hline_max, 0, wx.EXPAND, 0)
        sizer_param.Add(hline_dim, 0, wx.EXPAND, 0)
        sizer_param.Add(hline_delta, 0, wx.EXPAND, 0)
        sizer_param.Add(hline_color, 0, wx.EXPAND, 0)

        sizer_info = StaticBoxSizer(self, wx.ID_ANY, _("How to use it"), wx.VERTICAL)
        infomsg = _(
            "If you want to produce cut out shapes with *exact* dimensions"
           + " after the burn, then you need to take the width of the"
           + " laserbeam into consideration (aka Kerf).\n"
           + "This routine will create a couple of testshapes for you to establish this value.\n"
           + "After you cut these shapes out you need to try to fit shapes with the same"
           + " label together. Choose the one that have a perfect fit and use the"
           + " label as your kerf-value."
        )
        info_label = wx.TextCtrl(
            self, wx.ID_ANY, value=infomsg, style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        info_label.SetBackgroundColour(self.GetBackgroundColour())
        sizer_info.Add(info_label, 1, wx.EXPAND, 0)

        main_sizer.Add(sizer_param, 0, wx.EXPAND, 1)
        main_sizer.Add(self.button_create, 0, 0, 0)
        main_sizer.Add(sizer_info, 1, wx.EXPAND, 0)
        main_sizer.Layout()

        self.button_create.SetToolTip(_("Create a grid with your values"))

        self.SetSizer(main_sizer)

    def on_button_close(self, event):
        self.context("window close Kerftest\n")

    def on_button_generate(self, event):
        from time import time
        return

    def pane_show(self):
        return

class KerfTool(MWindow):
    """
    LivingHingeTool is the wrapper class to setup the
    required calls to open the HingePanel window
    In addition it listens to element selection and passes this
    information to HingePanel
    """

    def __init__(self, *args, **kwds):
        super().__init__(570, 420, submenu="Laser-Tools", *args, **kwds)
        self.panel_template = KerfPanel(
            self,
            wx.ID_ANY,
            context=self.context,
        )
        self.add_module_delegate(self.panel_template)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_hinges_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Kerf-Test"))
        self.Layout()

    def window_open(self):
        self.panel_template.pane_show()

    def window_close(self):
        pass

    @staticmethod
    def submenu():
        return ("Laser-Tools", "Kerf-Test")
