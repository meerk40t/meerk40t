import wx
from wx import aui

from meerk40t.gui.icons import *
from meerk40t.gui.propertiespanel import PropertiesPanel
from meerk40t.gui.wxmeerk40t import MeerK40t

MILS_IN_MM = 39.3701

_ = wx.GetTranslation


def register_panel(window: MeerK40t, context):
    control = OptimizePanel(window, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .Layer(1)
        .MinSize(350, 350)
        .FloatingSize(400, 400)
        .MaxSize(500, 500)
        .Caption(_("Optimize"))
        .CaptionVisible(not context.pane_lock)
        .Name("opt")
    )
    pane.control = control
    pane.dock_proportion = 400

    window.on_pane_add(pane)
    window.context.register("pane/optimize", pane)


class OptimizePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        self.properties_panel = PropertiesPanel(self, wx.ID_ANY, context=self.context, choices="optimize")
        sizer_1.Add(self.properties_panel, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_1)
        self.Layout()