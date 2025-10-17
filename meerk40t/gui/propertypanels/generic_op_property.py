import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.core.units import Length
from meerk40t.kernel.kernel import signal_listener

_ = wx.GetTranslation

SUPPORTED = {
    "util wait": [
        {
            "attr": "output",
            "default": True,
            "type": bool,
            "label": _("Active"),
            "tip": _("This operation will only run if active is checked."),
        },
        {
            "attr": "wait",
            "default": 1.0,
            "type": float,
            "label": _("Wait time for pause in execution (in seconds)"),
            "tip": _("Set the wait time for pausing the laser execution."),
        },
    ],
    "util goto": [
        {
            "attr": "output",
            "default": True,
            "type": bool,
            "label": _("Active"),
            "tip": _("This operation will only run if active is checked."),
        },
        {
            "attr": "x",
            "default": 0,
            "type": Length,
            "label": _("X-Coordinate"),
            "tip": _("Set the X-Coordinate of the goto operation."),
            # _("Laser target position"),
            "subsection": "Laser target position"
        },
        {
            "attr": "y",
            "default": 0,
            "type": Length,
            "label": _("Y-Coordinate"),
            "tip": _("Set the Y-Coordinate of the goto operation."),
            # _("Laser target position"),
            "subsection": "Laser target position"
        },
        {
            "attr": "absolute",
            "default": False,
            "type": bool,
            "label": _("Goto Absolute Position"),
            "tip": _(
                "This value should give exact goto locations rather than offset from device origin."
            ),
        },
    ],
    "util home": [
        {
            "attr": "output",
            "default": True,
            "type": bool,
            "label": _("Active"),
            "tip": _("This operation will only run if active is checked."),
        },
        {
            "attr": "physical",
            "default": False,
            "type": bool,
            "label": _("Physical Home"),
            "tip": _("Move the laser to the physical home position (engaging endstops)."),
        },
    ],
    "util output": [
        {
            "attr": "output",
            "default": True,
            "type": bool,
            "label": _("Active"),
            "tip": _("This operation will only run if active is checked."),
        },
        {
            "attr": "output_value",
            "mask": "output_mask",
            "default": 0,
            "type": int,
            "style": "binary",
            "bits": 16,
            "label": _("Value Bits"),
            "tip": _("Input bits for given value"),
        },
    ],
    "util input": [
        {
            "attr": "output",
            "default": True,
            "type": bool,
            "label": _("Active"),
            "tip": _("This operation will only run if active is checked."),
        },
        {
            "attr": "input_value",
            "mask": "input_mask",
            "default": 0,
            "type": int,
            "style": "binary",
            "bits": 16,
            "label": _("Value Bits"),
            "tip": _("Input bits for given value"),
        },
    ],
    "util console": [
        {
            "attr": "output",
            "default": True,
            "type": bool,
            "label": _("Active"),
            "tip": _("This operation will only run if active is checked."),
        },
        {
            "attr": "command",
            "default": "",
            "type": str,
            "style": "combosmall",
            "exclusive": False,
            "choices": [
                "beep",
                'interrupt "Spooling was interrupted"',
                "coolant_on",
                "coolant_off",
                "system_hibernate prevent",
                "system_hibernate allow",
            ],
            "label": _("Console Command"),
            "tip": _("Console command to execute."),
        },
        
    ]
}

class GenericOpPropertyPanel(wx.Panel):
    name = "Generic Operation Properties"

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.operation = node
        self.optype = None if node is None else node.type
        self.choices = self.get_choices()
        self.panel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=self.choices
        )
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.main_sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.SetSizer(self.main_sizer)
        self.Layout()
      

    @staticmethod
    def accepts(node):
        return (  
            node is not None  
            and hasattr(node, "type")  
            and node.type in SUPPORTED  
        )  
        
    def get_choices(self):
        if self.operation is None:
            return []
        
        choices = [choice.copy() for choice in SUPPORTED.get(self.operation.type, [])]  
        for choice in choices:
            choice["object"] = self.operation
            choice["signals"] = "opupdate"
        return choices

    def pane_hide(self):
        self.panel.pane_hide()
        if self.operation is not None:
            self.context.elements.signal("element_property_update", self.operation)

    def pane_show(self):
        # Update choices
        self.panel.pane_show()
        self.panel.reload()

    def set_widgets(self, node):
        self.operation = node
        if self.choices:
            # we need to unload the old panel first
            self.main_sizer.Detach(self.panel)
            # self.panel.Close()
            self.panel.pane_hide() # This will remove signal listeners
            self.panel.Destroy()
        self.choices = self.get_choices()
        self.panel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=self.get_choices()
        )
        self.main_sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.Layout()

    @signal_listener("opupdate")
    def on_operation_update(self, *args, **kwargs):
        if self.operation is not None:
            self.context.elements.signal("element_property_update", self.operation)
        