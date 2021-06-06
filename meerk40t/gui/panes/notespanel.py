import wx

_ = wx.GetTranslation


class NotePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: NotePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
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

        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_auto_note_open, self.check_auto_open_notes
        )
        self.Bind(wx.EVT_TEXT, self.on_text_notes, self.text_notes)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_notes, self.text_notes)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: NotePanel.__set_properties
        self.check_auto_open_notes.SetToolTip(
            _("Automatically open notes if they exist when file is opened.")
        )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: NotePanel.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.check_auto_open_notes, 0, 0, 0)
        sizer_1.Add(self.text_notes, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()
        # end wxGlade

    def initialize(self, *args):
        self.context.setting(bool, "auto_note", True)
        self.check_auto_open_notes.SetValue(self.context.auto_note)
        if self.context.elements.note is not None:
            self.text_notes.SetValue(self.context.elements.note)

    def on_check_auto_note_open(self, event=None):  # wxGlade: Notes.<event_handler>
        self.context.auto_note = self.check_auto_open_notes.GetValue()

    def on_text_notes(self, event=None):  # wxGlade: Notes.<event_handler>
        if len(self.text_notes.GetValue()) == 0:
            self.context.elements.note = None
        else:
            self.context.elements.note = self.text_notes.GetValue()
