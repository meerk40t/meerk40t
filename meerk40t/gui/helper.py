"""
    This module contains a panel that plugs into the main window
    to listen to mouse enter / mouse leave events.
    It will examine the window if it contains a tooltip text and
    will display this in a textbox in this panel.
    The purpose of this helper window is to allow better
    readability of the otherwise quickly disappearing tooltips
"""

import wx
from wx import aui

from meerk40t.gui.icons import icons8_info, get_default_icon_size
from meerk40t.gui.wxutils import StaticBoxSizer

_ = wx.GetTranslation

def register_panel_helper(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Left()
        .MinSize(225, 110)
        .FloatingSize(225, 110)
        .Caption(_("Help"))
        .CaptionVisible(not context.pane_lock)
        .Name("helper")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = HelperPanel(window, wx.ID_ANY, context=context)
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
        self.text_info = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.button_webhelp = wx.Button(self, wx.ID_ANY, _("Online-Help"))
        self.button_webhelp.SetBitmap(icons8_info.GetBitmap(resize = 0.5 * get_default_icon_size()))
        self.active = False
        self.info = None
        self.section = None
        self.__set_properties()
        self.__do_layout()

        self.timer = wx.Timer(self, id=wx.ID_ANY)
        self.Bind(wx.EVT_TIMER, self.mouse_query, self.timer)
        self.button_webhelp.Bind(wx.EVT_BUTTON, self.on_button_help)

    def pane_show(self, *args):
        self.active = True
        self.timer.Start(500, wx.TIMER_CONTINUOUS)

    def pane_hide(self, *args):
        self.active = False
        self.timer.Stop()

    def __set_properties(self):
        self.text_info.SetToolTip(_("Information about the control the mouse is hovering over"))
        self.button_webhelp.SetToolTip(_("Call online help-page"))

    def __do_layout(self):
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_1 = StaticBoxSizer(self, wx.ID_ANY, _("Information"), wx.VERTICAL)
        sizer_1.Add(self.text_info, 1, wx.EXPAND, 0)
        sizer_1.Add(self.button_webhelp, 0, wx.ALIGN_RIGHT, 0)
        sizer_main.Add(sizer_1, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()

    def update_information(self, control):
        if control is not None and control.Parent is not self:
            if hasattr(control, "GetToolTipText"):
                info = control.GetToolTipText()
                if info and info != self.info:
                    self.info = info
                    self.text_info.SetValue(info)
                    section = "GUI"
                    if hasattr(control, "GetHelpText"):
                        win = control
                        while win is not None:
                            section = win.GetHelpText()
                            if section:
                                break
                            win = win.GetParent()
                        if section is None or section == "":
                            section = "GUI"
                    self.section = section
                    self.button_webhelp.SetToolTip(_("Call online help-page") + f" ({self.section})")
                    # print (f"Info/Help: '{self.info}' / '{self.section}'")

    def mouse_query(self, event):
        wind, pos = wx.FindWindowAtPointer()
        self.update_information(wind)

    def on_button_help(self, event):
        sect = "GUI"
        if self.section:
            sect = self.section.upper()
        url = f"https://github.com/meerk40t/meerk40t/wiki/Online-Help:-{sect}"

        import webbrowser
        webbrowser.open(url, new=0, autoraise=True)
