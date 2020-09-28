
import wx

from Kernel import Module
from icons import icons8_console_50

_ = wx.GetTranslation


class Terminal(wx.Frame, Module):
    def __init__(self, context, path, parent, *args, **kwds):
        # begin wxGlade: Terminal.__init__
        wx.Frame.__init__(self, parent, -1, "",
                          style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT | wx.TAB_TRAVERSAL)
        Module.__init__(self, context, path)
        self.SetSize((581, 410))
        self.text_main = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_BESTWRAP | wx.TE_MULTILINE | wx.TE_READONLY)
        self.text_entry = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB)

        self.__set_properties()
        self.__do_layout()
        # self.Bind(wx.EVT_TEXT, self.on_key_down, self.text_entry))
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down, self.text_entry)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_entry, self.text_entry)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down_main, self.text_main)
        # end wxGlade
        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.command_log = []
        self.command_position = 0

    def on_middle_click(self, event):
        self.text_main.SetValue('')

    def on_close(self, event):
        if self.state == 5:
            event.Veto()
        else:
            self.state = 5
            self.context.close(self.name)
            event.Skip()  # Call destroy as regular.

    def initialize(self, channel=None):
        self.context.close(self.name)
        self.Show()
        self.context.channel('console').watch(self.update_text)
        self.text_entry.SetFocus()

    def finalize(self, channel=None):
        self.context.channel('console').unwatch(self.update_text)
        try:
            self.Close()
        except RuntimeError:
            pass

    def shutdown(self,  channel=None):
        try:
            self.Close()
        except RuntimeError:
            pass

    def update_text(self, text):
        if not wx.IsMainThread():
            wx.CallAfter(self.update_text_gui, str(text) + '\n')
        else:
            self.update_text_gui(str(text) + '\n')

    def update_text_gui(self, text):
        try:
            self.text_main.AppendText(text)
        except RuntimeError:
            pass

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_console_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Terminal.__set_properties
        self.SetTitle(_('Terminal'))
        self.text_entry.SetFocus()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Terminal.__do_layout
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.text_main, 20, wx.EXPAND, 0)
        sizer_2.Add(self.text_entry, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_2)
        self.Layout()
        # end wxGlade

    def on_key_down_main(self, event):
        key = event.GetKeyCode()
        if key != wx.WXK_CONTROL and (key != ord('C') or not event.ControlDown()):
            if self.FindFocus() is not self.text_entry:
                self.text_entry.SetFocus()
                self.text_entry.AppendText(str(chr(key)).lower())
        event.Skip()

    def on_key_down(self, event):
        key = event.GetKeyCode()
        try:
            if key == wx.WXK_DOWN:
                self.text_entry.SetValue(self.command_log[self.command_position + 1])
                if not wx.IsMainThread():
                    wx.CallAfter(self.text_entry.SetInsertionPointEnd)
                else:
                    self.text_entry.SetInsertionPointEnd()
                self.command_position += 1
            elif key == wx.WXK_UP:
                self.text_entry.SetValue(self.command_log[self.command_position - 1])
                if not wx.IsMainThread():
                    wx.CallAfter(self.text_entry.SetInsertionPointEnd)
                else:
                    self.text_entry.SetInsertionPointEnd()
                self.command_position -= 1
            else:
                event.Skip()
        except IndexError:
            pass

    def on_entry(self, event):  # wxGlade: Terminal.<event_handler>
        command = self.text_entry.GetValue()
        self.context.console(command + '\n')
        self.text_entry.SetValue('')
        self.command_log.append(command)
        self.command_position = 0
        event.Skip()
