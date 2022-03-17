import wx
from meerk40t.gui.propertiespanel import PropertiesPanel
from ..balor_params import Parameters

_ = wx.GetTranslation


class BalorOperationPanel(wx.Panel):
    name = "Balor"

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node
        params = Parameters(self.operation.settings)

        choices = [
            {
                "attr": "travel_speed",
                "object": params,
                "default": 2000.0,
                "type": float,
                "label": _("Travel Speed"),
                "tip": _("How fast do we travel when not cutting?"),
            },
            {
                "attr": "laser_power",
                "object": params,
                "default": 50.0,
                "type": float,
                "label": _("Laser Power"),
                "tip": _("How what power level do we cut at?"),
            },
            {
                "attr": "cut_speed",
                "object": params,
                "default": 100.0,
                "type": float,
                "label": _("Cut Speed"),
                "tip": _("How fast do we cut?"),
            },
            {
                "attr": "q_switch_frequency",
                "object": params,
                "default": 30.0,
                "type": float,
                "label": _("Q Switch Frequency"),
                "tip": _("QSwitch Frequency value"),
            },
            {
                "attr": "delay_laser_on",
                "object": params,
                "default": 100.0,
                "type": float,
                "label": _("Laser On Delay"),
                "tip": _("Delay for the start of the laser"),
            },
            {
                "attr": "delay_laser_off",
                "object": params,
                "default": 100.0,
                "type": float,
                "label": _("Laser Off Delay"),
                "tip": _("Delay amount for the end of the laser"),
            },
            {
                "attr": "delay_polygon",
                "object": params,
                "default": 100.0,
                "type": float,
                "label": _("Polygon Delay"),
                "tip": _("Delay amount between different points in the path travel."),
            },
        ]

        self.panel = PropertiesPanel(
            self, wx.ID_ANY, context=self.context, choices=choices
        )

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(main_sizer)

        self.Layout()

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def set_widgets(self, node):
        self.operation = node
