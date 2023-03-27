"""
This module creates a very basic BusyInfo implementation.
Based on the wxpython wxlib.busy routines.
"""

import wx


class BusyInfo:
    """
    Create a custom BusyInfo class.

    :param string `msg`:     a string to be displayed in the BusyInfo window.
    :param wx.Window `parent`:  an optional window to be used as the parent of
        the `:class:`BusyInfo`.  If given then the ``BusyInfo`` will be centered
        over that window, otherwise it will be centered on the screen.
    :param wx.Colour `bgcolor`: colour to be used for the background
        of the :class:`BusyInfo`
    :param wx.Colour `fgcolor`: colour to be used for the foreground (text)
        of the :class:`BusyInfo`
    """

    def __init__(self, **kwds):
        self.busy_object = None
        self.msg = None
        self.bgcolor = None
        self.fgcolor = None
        self.parent = None
        self.shown = False
        if "parent" in kwds:
            self.parent = kwds["parent"]
        self.frame = None
        self.update_keywords(kwds)

    def update_keywords(self, kwds):
        if "msg" in kwds:
            self.msg = kwds["msg"]
        if "bgcolor" in kwds:
            self.bgcolor = kwds["bgcolor"]
        if "fgcolor" in kwds:
            self.fgcolor = kwds["fgcolor"]

    def start(self, **kwds):
        self.end()
        self.frame = wx.Frame(
            self.parent, style=wx.BORDER_SIMPLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        )
        self.panel = wx.Panel(self.frame)
        self.text = wx.StaticText(self.panel, wx.ID_ANY, "")
        self.update_keywords(kwds)
        self.show()
        self.shown = True

    def end(self):
        self.hide()
        if self.frame:
            self.frame.Close()
            del self.frame
            self.frame = None
        self.shown = False

    def change(self, **kwds):
        self.update_keywords(kwds)
        if self.shown:
            self.show()

    def hide(self):
        if self.frame:
            self.frame.Hide()

    def show(self):
        for win in [self.panel, self.text]:
            win.SetBackgroundColour(self.bgcolor)
        for win in [self.panel, self.text]:
            win.SetForegroundColour(self.fgcolor)
        self.text.SetLabel(self.msg)
        size = self.text.GetBestSize()
        self.frame.SetClientSize((size.width + 60, size.height + 40))
        self.panel.SetSize(self.frame.GetClientSize())
        self.text.Center()
        self.frame.Center()
        self.frame.Show()
        self.frame.Refresh()
        self.frame.Update()
