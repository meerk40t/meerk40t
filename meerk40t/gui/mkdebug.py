import time

import wx
from wx import aui

_ = wx.GetTranslation


def register_panel_debugger(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Left()
        .MinSize(225, 110)
        .FloatingSize(225, 110)
        .Caption(_("Position"))
        .CaptionVisible(not context.pane_lock)
        .Name("debug_tree")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = DebugTreePanel(window, wx.ID_ANY, context=context)
    pane.submenu = "_ZZ_" + _("Debug")
    window.on_pane_create(pane)
    context.register("pane/debug_tree", pane)


class DebugTreePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.lb_selected = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE)
        self.lb_emphasized = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE)
        self.txt_first = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)

        self.__set_properties()
        self.__do_layout()

        # end wxGlade

        self._update_position()

    def pane_show(self, *args):
        self.context.listen("emphasized", self._update_position)
        self.context.listen("selected", self._update_position)

    def pane_hide(self, *args):
        self.context.unlisten("emphasized", self._update_position)
        self.context.unlisten("selected", self._update_position)

    def __set_properties(self):
        # begin wxGlade: PositionPanel.__set_properties
        self.lb_emphasized.SetToolTip(_("Emphasized nodes"))
        self.lb_selected.SetToolTip(_("Selected nodes"))
        self.txt_first.SetToolTip(_("Primus inter pares"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: PositionPanel.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_1 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Selected:")), wx.VERTICAL
        )
        sizer_2 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Emphasized:")), wx.VERTICAL
        )
        sizer_1.Add(self.lb_selected, 1, wx.EXPAND, 0)
        sizer_2.Add(self.lb_emphasized, 1, wx.EXPAND, 0)
        sizer_2.Add(self.txt_first, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_1, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_2, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()
        # end wxGlade

    def _update_position(self, *args):
        self.update_position(True)

    def update_position(self, reset):
        def timestr(ts):
            if ts is None:
                return "---"
            else:
                return time.strftime("%H:%M:%S", time.localtime(ts))

        txt1 = ""
        txt2 = ""
        for node in self.context.elements.flat(selected=True):
            txt1 += str(node) + "\n"
        data = self.context.elements.flat(emphasized=True)
        for node in data:
            txt2 += (
                f"{node.id} - {node.type} {node.label} - {timestr(node._emphasized_time)}"
                + "\n"
            )
        node = self.context.elements.first_emphasized  # (data)
        if node is None:
            txt3 = ""
        else:
            txt3 = f"{node.id} - {node.type} {node.label} - {timestr(node._emphasized_time)}"

        self.lb_selected.SetValue(txt1)
        self.lb_emphasized.SetValue(txt2)

        self.txt_first.SetValue(txt3)
