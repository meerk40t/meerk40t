"""
This module creates a very basic BusyInfo implementation.
Based on the wxpython wxlib.busy routines.
"""

import wx

DEFAULT_SIZE = 14


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

    def __init__(self, parent=None, **kwds):
        self.busy_object = None
        self.msg = None
        self.bgcolor = None
        self.fgcolor = None
        self.parent = parent
        self.shown = False
        self.fontsize = DEFAULT_SIZE
        # if "parent" in kwds:
        #     self.parent = kwds["parent"]
        self.frame = None
        self.panel = None
        self.text = None
        self.update_keywords(kwds)

    def update_keywords(self, kwds):
        keep = 0
        if "keep" in kwds:
            keep = int(kwds["keep"])
        if "msg" in kwds:
            newmsg = ""
            if self.msg:
                old = self.msg.split("\n")
                idx = 0
                while (idx < keep) and (idx < len(old)):
                    if newmsg:
                        newmsg += "\n"
                    newmsg += old[idx]
                    idx += 1
            if newmsg:
                newmsg += "\n"
            newmsg += kwds["msg"]
            self.msg = newmsg
        if "bgcolor" in kwds:
            self.bgcolor = kwds["bgcolor"]
        if "fgcolor" in kwds:
            self.fgcolor = kwds["fgcolor"]
        if "fontsize" in kwds:
            self.fontsize = kwds["fontsize"]

    def start(self, **kwds):
        self.end()
        # self.frame = wx.Frame(
        #     self.parent, style=wx.BORDER_SIMPLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        # )
        self.frame = wx.Frame(
            self.parent,
            id=wx.ID_ANY,
            style=wx.BORDER_SIMPLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP,
        )
        self.panel = wx.Panel(self.frame, id=wx.ID_ANY)
        self.text = wx.StaticText(
            self.panel, id=wx.ID_ANY, label="", style=wx.ALIGN_CENTRE_HORIZONTAL
        )
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

    def reparent(self, newparent):
        self.parent = newparent

    def show(self):
        if self.frame is None or self.panel is None or self.text is None:
            # Shouldn't happen, `show` called before `start`
            # print (f"Strange, show called although frame was none: {self.shown}")
            return
        for win in [self.panel, self.text]:
            win.SetBackgroundColour(self.bgcolor)
        for win in [self.panel, self.text]:
            win.SetForegroundColour(self.fgcolor)
        try:
            self.fontsize = int(self.fontsize)
        except ValueError:
            self.fontsize = DEFAULT_SIZE
        font = wx.Font(
            self.fontsize,
            wx.FONTFAMILY_SWISS,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        self.text.SetFont(font)
        self.text.SetLabel(self.msg)
        size = self.text.GetBestSize()
        self.frame.SetClientSize((size.width + 60, size.height + 40))
        self.panel.SetSize(self.frame.GetClientSize())
        self.text.Center()
        self.frame.Center()
        # That may be a bit over the top, but we really want an update :-)
        self.frame.Show()
        self.frame.Refresh()
        self.frame.Update()
