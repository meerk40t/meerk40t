"""
    This module displays information about an element
    that is gathered by periodically (every 0.5 seconds)
    looking at the window i.e. control under the mouse cursor.
    It will examine the window if it contains a tooltip text and
    will display this in a textbox in this panel.
    The purpose of this helper window is to allow better
    readability of the otherwise quickly disappearing tooltips.
"""

import wx
from wx import aui

from meerk40t.gui.wxutils import wxCheckBox, TextCtrl  # , wxButton
from meerk40t.kernel import Job, signal_listener

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
    pane.helptext = _("Permanently displays tooltip information")

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
        self.context.themes.set_window_colors(self)
        self._lock_updates = None
        self.text_info = TextCtrl(
            self, wx.ID_ANY, style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.check_allow = wxCheckBox(self, wx.ID_ANY, _("Display control-information"))
        # self.button_webhelp = wxButton(self, wx.ID_ANY, _("Online-Help"))
        # self.button_webhelp.SetBitmap(icons8_info.GetBitmap(resize = 0.5 * get_default_icon_size(self.context)))
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
        self.lock_updates = False
        self.Bind(wx.EVT_CHECKBOX, self.on_check_allow, self.check_allow)

    @property
    def lock_updates(self):
        return self._lock_updates

    @lock_updates.setter
    def lock_updates(self, value):
        if self.lock_updates != value:
            self._lock_updates = value
            self.check_allow.SetValue(not value)
            if not value:
                # Make sure we get an update immediately
                self.mouse_query(None)

    def on_check_allow(self, event):
        value = self.check_allow.GetValue()
        self.lock_updates = not value

    def mouse_query(self, event=None):
        """
        This routine looks periodically (every 0.5 seconds)
        at the window i.e. control under the mouse cursor.
        It will examine the window if it contains a tooltip text and
        will display this in a textbox in this panel.
        Additionally, it will read the associated HelpText of the control
        (or its parent if the control does not have any) to construct a
        Wiki page on GitHub to open an associated online help page.
        """
        if self.context.kernel.is_shutdown:
            return
        if self._lock_updates:
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

    @signal_listener("lock_helper")
    def helper_locker(self, origin, *args, **kwargs):
        self.lock_updates = not self.lock_updates

    def pane_show(self, *args):
        self.context.kernel.schedule(self.job)

    def pane_hide(self, *args):
        self.context.kernel.unschedule(self.job)

    def __set_properties(self):
        s = _("Information about the control the mouse is hovering over")
        self.text_info.SetToolTip(s)
        self.check_allow.SetToolTip(
            s
            + "\n"
            + _(
                "If inactive then no more updates will happen until you check this checkbox again"
            )
            # + "\n"
            # + _(
            #     "Tip: Press Ctrl+Shift+L while hovering over a control to lock the content."
            # )
        )
        # self.button_webhelp.SetToolTip(_("Call online help-page"))

    def __do_layout(self):
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.check_allow, 0, 0, 0)
        sizer_1.Add(self.text_info, 1, wx.EXPAND, 0)
        # sizer_1.Add(self.button_webhelp, 0, wx.ALIGN_RIGHT, 0)
        sizer_main.Add(sizer_1, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()
