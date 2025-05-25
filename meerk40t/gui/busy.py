"""
This module creates a very basic BusyInfo implementation.
Based on the wxpython wxlib.busy routines.
"""
import threading

import wx

DEFAULT_SIZE = 14

class SimpleBusyInfo:
    """
    Create a simplified BusyInfo class that uses the main window title as canvas. 
    Just used for Linux as the wxWidgets implementation sucks big time regarding
    the controlled update of a window. So the full-featured implementation below
    does not only produce nothing visible but seems to have severe side effects
    that may caus segmenation faults.

    :param string `msg`:     a string to be displayed in the BusyInfo window.
    """
    def __init__(self, **kwds):
        self.kernel = kwds.get("kernel", None)
        self.shown = False
        self._old_title = ""
        self._msg = ""

    def start(self, **kwds):
        if self.shown:
            self.end()
        self.update_keywords(kwds)
        self.shown = True
        self._old_title = ""
        try:
            win:wx.Window = self.kernel.root.gui
            win.SetCursor(wx.Cursor(wx.CURSOR_WAIT))
            self._old_title = win.GetTitle()
        except (TypeError, AttributeError) as e:
            return

    def end(self):
        self.shown = False
        self._msg = ""
        try:
            win = self.kernel.root.gui
            win.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        except (TypeError, AttributeError):
            return
        if self._old_title:
            win.SetTitle(self._old_title)

    def change(self, **kwds):
        self.update_keywords(kwds)
        if self.msg:
            try:
                win = self.kernel.root.gui
                win.SetTitle(self.msg)
            except (TypeError, AttributeError):
                return

    def update_keywords(self, kwds):
        keep = 0
        if "keep" in kwds:
            keep = int(kwds["keep"])
        if "msg" in kwds:
            old_lines = self._msg.split("\n") if self._msg else []
            new_lines = old_lines[:keep]
            new_lines.append(kwds["msg"])
            self._msg = "\n".join(new_lines)            

    @property
    def msg(self):
        return self._msg.replace("\n", " - ")

    def hide(self):
        self.shown = False
        return

    def show(self):
        self.shown = True
        return


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
        self.lock = threading.RLock()
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
        self.image = None
        if "startup" in kwds:
            try:
                kwds["startup"](self)
            except AttributeError:
                pass
        self.update_keywords(kwds)

    def update_keywords(self, kwds):
        keep = 0
        if "keep" in kwds:
            keep = int(kwds["keep"])
        if "image" in kwds:
            self.image = kwds["image"]
        else:
            if keep == 0:
                self.image = None
        if "msg" in kwds:
            old_lines = self.msg.split("\n") if self.msg else []
            new_lines = old_lines[:keep]
            new_lines.append(kwds["msg"])
            self.msg = "\n".join(new_lines)            
        if "bgcolor" in kwds:
            self.bgcolor = kwds["bgcolor"]
        if "fgcolor" in kwds:
            self.fgcolor = kwds["fgcolor"]
        if "fontsize" in kwds:
            self.fontsize = kwds["fontsize"]

    def start(self, **kwds):
        self.end()
        with self.lock:
            self.frame = wx.Frame(
                self.parent,
                id=wx.ID_ANY,
                style=wx.BORDER_SIMPLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP,
            )
            self.panel = wx.Panel(self.frame, id=wx.ID_ANY)
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.display = wx.StaticBitmap(self.panel, wx.ID_ANY)
            self.text = wx.StaticText(
                self.panel, id=wx.ID_ANY, label="", style=wx.ALIGN_CENTRE_HORIZONTAL
            )
            sizer.Add(self.display, 0, wx.ALIGN_CENTER_VERTICAL, 0)
            sizer.Add(self.text, 1, wx.ALIGN_CENTER_VERTICAL, 0)
            self.update_keywords(kwds)
            self.panel.SetSizer(sizer)
            self.panel.Layout()
            self.show()
            if self.parent is not None:
                self.parent.SetCursor(wx.Cursor(wx.CURSOR_WAIT))
            self.shown = True

    def end(self):
        with self.lock:
            self.hide()
            if self.parent is not None:
                self.parent.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
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
        with self.lock:
            if self.frame is None or self.panel is None or self.text is None:
                # The busy was ended before this thread could acquire the lock.
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
            bm_w = 0
            bm_h = 0
            if self.image is None:
                self.display.SetBitmap(wx.NullBitmap)
                self.display.Hide()
            else:
                self.display.SetBitmap(self.image)
                bm_w, bm_h = self.display.GetBitmap().Size
                self.display.SetSize(bm_w + 2, bm_h + 2)

            self.text.SetFont(font)
            self.text.SetLabel(self.msg.replace("|", "\n"))

            sizetext = self.text.GetBestSize()

            wd = sizetext.width + 5 + bm_w
            ht = max(sizetext.height, bm_h)

            self.frame.SetClientSize((wd + 60, ht + 40))
            self.panel.SetSize(self.frame.GetClientSize())
            self.panel.Layout()
            # self.text.Center()
            self.frame.Center()
            # That may be a bit over the top, but we really want an update :-)
            self.frame.Show()
            self.frame.Refresh()
            self.frame.Update()
