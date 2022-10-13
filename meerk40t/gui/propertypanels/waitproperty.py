import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class WaitPropertyPanel(wx.Panel):
    name = "Wait"

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        self.choices = [
            {
                "attr": "wait",
                "object": self.operation,
                "default": 1.0,
                "type": float,
                "label": _("Wait time for pause in execution (in seconds)"),
                "tip": _("Set the wait time for pausing the laser execution."),
            },
        ]
        self.panel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=self.choices
        )
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)
        self.Layout()

    @signal_listener("wait")
    def wait_changed(self, *args):
        self.context.elements.signal("element_property_update", self.operation)

    def pane_hide(self):
        self.panel.pane_hide()
        self.context.elements.signal("element_property_update", self.operation)

    def pane_show(self):
        self.panel.pane_show()

    def set_widgets(self, node):
        self.operation = node
        for item in self.choices:
            try:
                item_att = item["attr"]
            except KeyError:
                continue
            if hasattr(node, item_att):
                item_value = getattr(node, item_att)
                self.context.signal(item_att, item_value, self.operation)
