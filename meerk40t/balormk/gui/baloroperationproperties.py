import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.wxutils import ScrolledPanel

from ..balor_params import Parameters

_ = wx.GetTranslation


class BalorOperationPanel(ScrolledPanel):
    name = "Balor"

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("baloroperation")
        self.parent = args[0]
        self.operation = node
        params = Parameters(self.operation.settings)
        params.validate()

        choices = [
            {
                "attr": "rapid_enabled",
                "object": params,
                "default": False,
                "type": bool,
                "label": _("Enable Custom Rapid-Speed"),
                "tip": _("Enable custom jump speed for this operation"),
            },
            {
                "attr": "rapid_speed",
                "object": params,
                "default": 2000.0,
                "type": float,
                "conditional": (params, "rapid_enabled"),
                "label": _("Travel Speed"),
                "tip": _("How fast do we travel when not cutting?"),
            },
            {
                "attr": "pulse_width_enabled",
                "object": params,
                "default": False,
                "type": bool,
                "conditional": (self.context.device, "pulse_width_enabled"),
                "label": _("Enable Custom Pulse Width"),
                "tip": _("Override the global pulse width setting (MOPA)"),
            },
            {
                "attr": "pulse_width",
                "object": params,
                "default": self.context.device.default_pulse_width,
                "type": int,
                "conditional": (params, "pulse_width_enabled"),
                "label": _("Set Pulse Width (ns)"),
                "tip": _("Set the MOPA pulse width setting"),
            },
            {
                "attr": "timing_enabled",
                "object": params,
                "default": False,
                "type": bool,
                "label": _("Enable Custom Timings"),
                "tip": _("Enable custom timings for this operation"),
            },
            {
                "attr": "delay_laser_on",
                "object": params,
                "default": 100.0,
                "type": float,
                "conditional": (params, "timing_enabled"),
                "label": _("Laser On Delay"),
                "tip": _("Delay for the start of the laser"),
            },
            {
                "attr": "delay_laser_off",
                "object": params,
                "default": 100.0,
                "type": float,
                "conditional": (params, "timing_enabled"),
                "label": _("Laser Off Delay"),
                "tip": _("Delay amount for the end of the laser"),
            },
            {
                "attr": "delay_polygon",
                "object": params,
                "default": 100.0,
                "type": float,
                "conditional": (params, "timing_enabled"),
                "label": _("Polygon Delay"),
                "tip": _("Delay amount between different points in the path travel."),
            },
        ]

        self.panel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=choices, scrolling=False
        )

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.panel, 1, wx.EXPAND, 0)

        self.SetSizer(main_sizer)
        # self.parent.add_module_delegate(self.panel)
        self.Layout()

    def pane_hide(self):
        self.panel.pane_hide()

    def pane_show(self):
        self.panel.pane_show()

    def set_widgets(self, node):
        self.operation = node
