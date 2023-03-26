"""
This module creates a very basic BusyInfo implementation.
Based on the wxpython wxlib.busy routines.
"""

import wx

class BusyInfo():
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
        self.bgcolor=None
        self.fgcolor=None
        self.parent = None
        self.shown = False
        if "parent" in kwds:
            self.parent = kwds["parent"]

        self.frame = wx.Frame(self.parent, style=wx.BORDER_SIMPLE|wx.FRAME_TOOL_WINDOW|wx.STAY_ON_TOP)
        self.panel = wx.Panel(self.frame)
        self.text = wx.StaticText(self.panel, wx.ID_ANY, "")
        self.update_keywords(kwds)
        for win in [self.panel, self.text]:
            win.SetCursor(wx.HOURGLASS_CURSOR)

    def update_keywords(self, kwds):
        if "msg" in kwds:
            self.msg = kwds["msg"]
            self.text.SetLabel(self.msg)
        if "bgcolor" in kwds:
            self.bgcolor = kwds["bgcolor"]
            for win in [self.panel, self.text]:
                win.SetBackgroundColour(self.bgcolor)
        if "fgcolor" in kwds:
            self.fgcolor = kwds["fgcolor"]
            for win in [self.panel, self.text]:
                win.SetForegroundColour(self.fgcolor)
        size = self.text.GetBestSize()
        self.frame.SetClientSize((size.width + 60, size.height + 40))
        self.panel.SetSize(self.frame.GetClientSize())
        self.text.Center()
        self.frame.Center()

    def start(self, **kwds):
        self.update_keywords(kwds)
        if "msg" in kwds:
            self.msg = kwds["msg"]
            self.text.SetLabel(self.msg)
        if "bgcolor" in kwds:
            self.bgcolor = kwds["bgcolor"]
            self.frame.SetBackgroundColor(self.msg)
        if "fgcolor" in kwds:
            self.fgcolor = kwds["fgcolor"]
        if "parent" in kwds:
            self.parent = kwds["parent"]
        self.show()

    def end(self):
        self.hide()

    def change(self, **kwds):
        self.update_keywords(kwds)
        if self.shown:
            self.show()

    def hide(self):
        self.frame.Hide()
        self.shown = False

    def show(self):
        self.frame.Show()
        self.frame.Refresh()
        self.frame.Update()
        self.shown = True
