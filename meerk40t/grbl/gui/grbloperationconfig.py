import wx

from meerk40t.core.units import Length
from meerk40t.gui.wxutils import StaticBoxSizer, TextCtrl, wxCheckBox

_ = wx.GetTranslation


class GRBLAdvancedPanel(wx.Panel):
    name = "Advanced"

    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LhyAdvancedPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("grbloperation")
        self.operation = node

        extras_sizer = wx.BoxSizer(wx.VERTICAL)

        advanced_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Advanced Features:"), wx.VERTICAL
        )
        extras_sizer.Add(advanced_sizer, 0, wx.EXPAND, 0)

        sizer_z_axis = wx.BoxSizer(wx.HORIZONTAL)
        advanced_sizer.Add(sizer_z_axis, 0, wx.EXPAND, 0)

        self.check_zaxis = wxCheckBox(self, wx.ID_ANY, _("Set Z-Axis value"))
        self.check_zaxis.SetToolTip(_("Enables the ability to set a specific z-Value."))
        sizer_z_axis.Add(self.check_zaxis, 1, 0, 0)

        self.text_zaxis = TextCtrl(
            self,
            wx.ID_ANY,
            "0",
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        OPERATION_ZAXIS_TOOLTIP = _(
            "If enabled this will allow to set a defined z-Axis value for all elements assigned to this operation"
        )

        self.text_zaxis.SetToolTip(OPERATION_ZAXIS_TOOLTIP)
        sizer_z_axis.Add(self.text_zaxis, 1, 0, 0)

        sizer_commands = StaticBoxSizer(self, wx.ID_ANY, _("Custom Code:"))
        advanced_sizer.Add(sizer_commands, 1, wx.EXPAND, 0)
        self.text_commands = TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE)
        self.text_commands.SetToolTip(_("Any custom GRBL code that will be executed at the start of the operation"))
        sizer_commands.Add(self.text_commands, 1, wx.EXPAND, 0)
        self.SetSizer(extras_sizer)

        self.Layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_zaxis, self.check_zaxis)
        self.text_zaxis.SetActionRoutine(self.on_text_zaxis)
        self.text_commands.Bind(wx.EVT_TEXT, self.on_text_commands)

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def set_widgets(self, node):
        self.operation = node
        value = ""
        flag = False
        z_val = getattr(self.operation, "zaxis", None)
        if z_val is not None:
            try:
                value = Length(z_val).preferred_length
                flag = True
            except ValueError:
                pass

        self.check_zaxis.SetValue(flag)
        self.text_zaxis.SetValue(value)
        self.text_zaxis.Enable(flag)
        value = getattr(self.operation, "custom_commands", "")
        if value is None:
            value = ""
        self.text_commands.SetValue(value)

    def on_check_zaxis(self, event=None):
        on = self.check_zaxis.GetValue()
        self.text_zaxis.Enable(on)

    def on_text_zaxis(self):
        try:
            self.operation.zaxis = Length(self.text_zaxis.GetValue())
        except ValueError:
            return
        self.context.elements.signal("element_property_reload", self.operation)

    def on_text_commands(self, event):
        value = self.text_commands.GetValue()
        if value == "":
            value = None
        self.operation.custom_commands = value
        # self.context.elements.signal("element_property_update", self.operation)
