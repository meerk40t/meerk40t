import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class OutputPropertyPanel(wx.Panel):
    name = "Output"

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.operation = node

        self.choices = [
            {
                "attr": "output_value",
                "mask": "output_mask",
                "object": self.operation,
                "default": 0,
                "type": int,
                "style": "binary",
                "bits": 16,
                "label": _("Value Bits"),
                "tip": _("Input bits for given value"),
            },
        ]
        self.panel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=self.choices
        )
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)
        self.Layout()

    @signal_listener("output_mask")
    @signal_listener("output_value")
    def wait_changed(self, *args):
        self.context.elements.signal("element_property_update", self.operation)

    def pane_hide(self):
        self.panel.pane_hide()

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
