import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.wxutils import ScrolledPanel

from ..newly_params import Parameters

_ = wx.GetTranslation


class NewlyOperationPanel(ScrolledPanel):
    name = "Newly"

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.parent = args[0]
        self.operation = node
        params = Parameters(self.operation.settings)
        params.validate()

        choices = [
            {
                "attr": "acceleration",
                "object": params,
                "default": 15,
                "type": int,
                "label": _("Advanced Acceleration"),
                "tip": _("Set acceleration value for this operation"),
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
