import wx

from .icons import icons8_comments_50
from .mwindow import MWindow
from .panes.notespanel import NotePanel

_ = wx.GetTranslation


class Notes(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(730, 621, *args, **kwds)

        self.panel = NotePanel(self, wx.ID_ANY, context=self.context)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_comments_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Notes"))

    def window_open(self):
        self.context.close(self.name)
        self.panel.initialize()

    def window_close(self):
        self.panel.finalize()
