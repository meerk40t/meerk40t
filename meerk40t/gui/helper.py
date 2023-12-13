"""
    This module displays information about an element
    that is gathered by periodically (every 0.5 seconds)
    looking at the window ie control under the mouse cursor.
    It will examine the window if it contains a tooltip text and
    will display this in a textbox in this panel.
    The purpose of this helper window is to allow better
    readability of the otherwise quickly disappearing tooltips.
"""

import wx
from wx import aui

from meerk40t.gui.icons import get_default_icon_size, icons8_info
from meerk40t.gui.wxutils import StaticBoxSizer
from meerk40t.kernel import Job

_ = wx.GetTranslation


def register_panel_helper(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Left()
        .Float()
        .MinSize(225, 110)
        .FloatingSize(225, 110)
        .Caption(_("Help"))
        .CaptionVisible(not context.pane_lock)
        .Name("helper")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = HelperPanel(window, wx.ID_ANY, context=context)
    pane.submenu = "~" + _("Help")

    window.on_pane_create(pane)
    context.register("pane/helper", pane)


class HelperPanel(wx.Panel):
    """
    Displays information about the GUI element the mouse is currently hovering over
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.text_info = wx.TextCtrl(
            self, wx.ID_ANY, style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        # self.button_webhelp = wx.Button(self, wx.ID_ANY, _("Online-Help"))
        # self.button_webhelp.SetBitmap(icons8_info.GetBitmap(resize = 0.5 * get_default_icon_size()))
        self.active = False
        self.__set_properties()
        self.__do_layout()

        self._last_help_info = ""
        self.job = Job(
            process=self.mouse_query,
            job_name="helper-check",
            interval=0.2,
            run_main=True,
        )

    def mouse_query(self, event=None):
        """
        This routine looks periodically (every 0.5 seconds)
        at the window ie control under the mouse cursor.
        It will examine the window if it contains a tooltip text and
        will display this in a textbox in this panel.
        Additionally, it will read the associated HelpText of the control
        (or its parent if the control does not have any) to construct a
        Wiki page on GitHub to open an associated online help page.
        """
        if self.context.kernel.is_shutdown:
            return
        try:
            wind, pos = wx.FindWindowAtPointer()
            if wind is None or wind is self:
                return
            if wind.GetParent() is self:
                return
            if not hasattr(wind, "GetToolTipText"):
                return
            info = wind.GetToolTipText()
            if info != self._last_help_info:
                self.text_info.SetValue(info)
                self._last_help_info = info
        except RuntimeError:
            return

    def pane_show(self, *args):
        self.context.kernel.schedule(self.job)

    def pane_hide(self, *args):
        self.context.kernel.unschedule(self.job)

    def __set_properties(self):
        self.text_info.SetToolTip(
            _("Information about the control the mouse is hovering over")
        )
        # self.button_webhelp.SetToolTip(_("Call online help-page"))

    def __do_layout(self):
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_1 = StaticBoxSizer(self, wx.ID_ANY, _("Information"), wx.VERTICAL)
        sizer_1.Add(self.text_info, 1, wx.EXPAND, 0)
        # sizer_1.Add(self.button_webhelp, 0, wx.ALIGN_RIGHT, 0)
        sizer_main.Add(sizer_1, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()
