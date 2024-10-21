import wx

from meerk40t.core.units import Length
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class GotoPropertyPanel(wx.Panel):
    name = "Goto"

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.operation = node

        self.choices = [
            {
                "attr": "x",
                "object": self.operation,
                "default": 0,
                "type": Length,
                "label": _("X-Coordinate of Goto?"),
                "tip": _("Set the X-Coordinate of the goto operation."),
            },
            {
                "attr": "y",
                "object": self.operation,
                "default": 0,
                "type": Length,
                "label": _("Y-Coordinate of Goto?"),
                "tip": _("Set the Y-Coordinate of the goto operation."),
            },
            {
                "attr": "absolute",
                "object": self.operation,
                "default": False,
                "type": bool,
                "label": _("Goto Absolute Position"),
                "tip": _(
                    "This value should give exact goto locations rather than offset from device origin."
                ),
            },
        ]
        self.panel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=self.choices
        )
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)
        self.Layout()

    @signal_listener("x")
    @signal_listener("y")
    @signal_listener("absolute")
    def location_changed(self, *args):
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
