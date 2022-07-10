import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel

_ = wx.GetTranslation


class OpBranchPanel(wx.Panel):
    name = "Loop Properties"

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        root = context.root
        self.operation = node

        self.panel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=root, choices="loop_choice"
        )

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(main_sizer)

        self.Layout()

    def pane_hide(self):
        self.panel.pane_hide()

    def pane_show(self):
        self.panel.pane_show()

    def set_widgets(self, node):
        self.operation = node
