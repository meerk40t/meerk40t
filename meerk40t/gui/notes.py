import wx

from .icons import icons8_comments_50
from .mwindow import MWindow
from .panes.notespanel import NotePanel

_ = wx.GetTranslation


class Notes(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(730, 621, *args, **kwds)

        self.panel = NotePanel(self, wx.ID_ANY, context=self.context)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_comments_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Notes"))
        self.Children[0].SetFocus()

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/project/Notes",
            {
                "label": _("Notes"),
                "icon": icons8_comments_50,
                "tip": _("Open Notes Window"),
                "action": lambda v: kernel.console("window toggle Notes\n"),
            },
        )

    def window_open(self):
        self.context.close(self.name)
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()
