import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class OpBranchPanel(wx.Panel):
    name = "Loop Properties"

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        self.operation = node
        choices = [
            {
                "attr": "loop_continuous",
                "object": self.operation,
                "default": False,
                "type": bool,
                "label": _("Loop Continuously"),
                "tip": _("Operation job will run forever in a loop"),
            },
            {
                "attr": "loop_enabled",
                "object": self.operation,
                "default": False,
                "type": bool,
                "label": _("Loop Parameter"),
                "tip": _("Operation job should run set number of times"),
            },
            {
                "attr": "loop_n",
                "object": self.operation,
                "default": 1,
                "type": int,
                "conditional": (self.operation, "loop_enabled"),
                "label": _("Loop"),
                "trailing": _("times"),
                "tip": _("How many times should the operation job loop"),
            },
        ]
        self.panel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=context, choices=choices
        )

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(main_sizer)

        self.Layout()

    @signal_listener("loop_continuous")
    @signal_listener("loop_n")
    @signal_listener("loop_enabled")
    def wait_changed(self, *args):
        self.context.elements.signal("element_property_update", self.operation)

    def pane_hide(self):
        self.panel.pane_hide()

    def pane_show(self):
        self.panel.pane_show()

    def set_widgets(self, node):
        self.operation = node
