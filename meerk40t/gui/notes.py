import wx
from wx import aui

from .icons import STD_ICON_SIZE, icons8_comments_50
from .mwindow import MWindow

_ = wx.GetTranslation


def register_panel(window, context):
    panel = NotePanel(window, wx.ID_ANY, context=context, pane=True)
    pane = (
        aui.AuiPaneInfo()
        .Float()
        .MinSize(100, 100)
        .FloatingSize(170, 230)
        .MaxSize(500, 500)
        .Caption(_("Notes"))
        .CaptionVisible(not context.pane_lock)
        .Name("notes")
        .Hide()
    )
    pane.dock_proportion = 100
    pane.control = panel
    pane.submenu = "_50_" + _("Tools")

    window.on_pane_create(pane)
    context.register("pane/notes", pane)


class NotePanel(wx.Panel):
    def __init__(self, *args, context=None, pane=False, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.pane = pane
        if not self.pane:
            self.check_auto_open_notes = wx.CheckBox(
                self, wx.ID_ANY, _("Automatically Open Notes")
            )
        self.text_notes = wx.TextCtrl(
            self,
            wx.ID_ANY,
            "",
            style=wx.TE_BESTWRAP | wx.TE_MULTILINE | wx.TE_WORDWRAP | wx.TE_RICH,
        )

        self.__set_properties()
        self.__do_layout()

        if not self.pane:
            self.Bind(
                wx.EVT_CHECKBOX,
                self.on_check_auto_note_open,
                self.check_auto_open_notes,
            )
        self.Bind(wx.EVT_TEXT, self.on_text_notes, self.text_notes)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_notes, self.text_notes)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: NotePanel.__set_properties
        if not self.pane:
            self.check_auto_open_notes.SetToolTip(
                _("Automatically open notes if they exist when file is opened.")
            )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: NotePanel.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        if not self.pane:
            sizer_1.Add(self.check_auto_open_notes, 0, 0, 0)
        sizer_1.Add(self.text_notes, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()
        # end wxGlade

    def pane_show(self, *args):
        if not self.pane:
            self.context.setting(bool, "auto_note", True)
            self.check_auto_open_notes.SetValue(self.context.elements.auto_note)
        if self.context.elements.note is not None:
            self.text_notes.SetValue(self.context.elements.note)
        self.context.listen("note", self.on_note_listen)

    def pane_hide(self):
        self.context.unlisten("note", self.on_note_listen)

    def on_check_auto_note_open(self, event=None):  # wxGlade: Notes.<event_handler>
        self.context.elements.auto_note = self.check_auto_open_notes.GetValue()

    def on_text_notes(self, event=None):  # wxGlade: Notes.<event_handler>
        if len(self.text_notes.GetValue()) == 0:
            self.context.elements.note = None
        else:
            self.context.elements.note = self.text_notes.GetValue()
        self.context.elements.signal("note", self)

    def on_note_listen(self, origin, source):
        if source is self:
            return
        note = self.context.elements.note
        if self.context.elements.note is None:
            note = ""
        if self.text_notes.GetValue() != note:
            self.text_notes.SetValue(note)


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
        kernel.register("wxpane/Notes", register_panel)
        kernel.register(
            "button/project/Notes",
            {
                "label": _("Notes"),
                "icon": icons8_comments_50,
                "tip": _("Open Notes Window"),
                "action": lambda v: kernel.console("window toggle Notes\n"),
                "size": STD_ICON_SIZE,
            },
        )

    def window_open(self):
        self.context.close(self.name)
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()
