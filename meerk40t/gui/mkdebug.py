import time

import wx
from wx import aui

from meerk40t.gui.wxutils import StaticBoxSizer

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

def register_panel_color(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Left()
        .MinSize(225, 110)
        .FloatingSize(225, 110)
        .Caption(_("System-Colors"))
        .CaptionVisible(not context.pane_lock)
        .Name("debug_color")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = DebugColorPanel(window, wx.ID_ANY, context=context)
    pane.submenu = "_ZZ_" + _("Debug")
    window.on_pane_create(pane)
    context.register("pane/debug_color", pane)


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
        sizer_1 = StaticBoxSizer(self, wx.ID_ANY, _("Selected:"), wx.VERTICAL)
        sizer_2 = StaticBoxSizer(self, wx.ID_ANY, _("Emphasized:"), wx.VERTICAL)
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

class DebugColorPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        from copy import copy

        self.context = context

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_line = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_line, 0, wx.EXPAND, 0)
        count = 0
        font = wx.Font(6, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        pattern = "SYS_COLOUR_"
        for prop in dir(wx):
            if prop.startswith(pattern):
                # print (prop)
                count += 1
                if count >= 5:
                    sizer_line = wx.BoxSizer(wx.HORIZONTAL)
                    sizer_main.Add(sizer_line, 0, wx.EXPAND, 0)
                    count = 0

                col = wx.SystemSettings().GetColour(getattr(wx, prop))
                infosizer = wx.BoxSizer(wx.VERTICAL)
                box = wx.StaticBitmap(
                    self, wx.ID_ANY,
                    size = wx.Size(32, 32),
                    style=wx.SB_RAISED
                )
                box.SetBackgroundColour(col)
                lbl = wx.StaticText(self, wx.ID_ANY, prop[len(pattern):])
                lbl.SetFont(font)
                lbl.SetMinSize(wx.Size(75, -1))
                infosizer.Add(box, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
                infosizer.Add(lbl, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

                sizer_line.Add(infosizer, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()


    def pane_show(self, *args):
        return

    def pane_hide(self, *args):
        return
