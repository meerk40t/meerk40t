
import wx

from Kernel import Module
from icons import icons8_comments_50

_ = wx.GetTranslation


class Notes(wx.Frame, Module):
    def __init__(self, context, path, parent, *args, **kwds):
        # begin wxGlade: Notes.__init__
        wx.Frame.__init__(self, parent, -1, "",
                          style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT | wx.TAB_TRAVERSAL)
        Module.__init__(self, context, path)
        self.SetSize((730, 621))
        self.check_auto_open_notes = wx.CheckBox(self, wx.ID_ANY, _("Automatically Open Notes"))
        self.text_notes = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_BESTWRAP | wx.TE_MULTILINE | wx.TE_WORDWRAP)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_auto_note_open, self.check_auto_open_notes)
        self.Bind(wx.EVT_TEXT, self.on_text_notes, self.text_notes)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_notes, self.text_notes)
        # end wxGlade

        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        if self.state == 5:
            event.Veto()
        else:
            self.state = 5
            self.context.close(self.name)
            event.Skip()  # Call destroy as regular.

    def initialize(self, channel=None):
        self.context.setting(bool, 'auto_note', True)
        self.context.close(self.name)
        self.check_auto_open_notes.SetValue(self.context.auto_note)
        if self.context.elements.note is not None:
            self.text_notes.SetValue(self.context.elements.note)
        self.Show()

    def finalize(self, channel=None):
        try:
            self.Close()
        except RuntimeError:
            pass

    def shutdown(self,  channel=None):
        try:
            self.Close()
        except RuntimeError:
            pass

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_comments_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle("Notes")
        self.check_auto_open_notes.SetToolTip(_("Automatically open notes if they exist when file is opened."))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Notes.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.check_auto_open_notes, 0, 0, 0)
        sizer_1.Add(self.text_notes, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def on_check_auto_note_open(self, event):  # wxGlade: Notes.<event_handler>
        self.context.auto_note = self.check_auto_open_notes.GetValue()

    def on_text_notes(self, event):  # wxGlade: Notes.<event_handler>
        if len(self.text_notes.GetValue()) == 0:
            self.context.elements.note = None
        else:
            self.context.elements.note = self.text_notes.GetValue()
