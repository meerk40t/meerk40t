import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.wxutils import ScrolledPanel

_ = wx.GetTranslation


class RuidaOperationPanel(ScrolledPanel):
    name = "Ruida"

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.parent = args[0]
        self.operation = node

        choices = [
            {
                "attr": "air_assist",
                "object": node,
                "default": True,
                "type": bool,
                "label": _("Air Assist"),
                "tip": _("Trigger the per element air assist"),
            },
        ]

        self.panel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=choices, scrolling=False
        )

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.panel, 1, wx.EXPAND, 0)

        self.SetSizer(main_sizer)
        self.Layout()

    def pane_hide(self):
        self.panel.pane_hide()

    def pane_show(self):
        self.panel.pane_show()

    def set_widgets(self, node):
        self.operation = node
