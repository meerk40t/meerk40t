
import wx

from Kernel import Module

_ = wx.GetTranslation


class Terminal(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: Terminal.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.FRAME_FLOAT_ON_PARENT
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((581, 410))
        self.text_main = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_BESTWRAP | wx.TE_MULTILINE | wx.TE_READONLY)
        self.text_entry = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB)

        self.__set_properties()
        self.__do_layout()
        # self.Bind(wx.EVT_TEXT, self.on_key_down, self.text_entry)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down, self.text_entry)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_entry, self.text_entry)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down, self.text_main)
        # end wxGlade
        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.pipe = None
        self.command_log = []
        self.command_position = 0

    def on_middle_click(self, event):
        self.text_main.SetValue('')

    def initialize(self):
        self.device.close('window', 'Terminal')
        self.Show()
        self.pipe = self.device.using('module', 'Console')
        self.device.add_watcher('console', self.update_text)
        self.SetCanFocus(True)
        self.SetFocus()
        self.text_entry.SetFocus()

    def on_close(self, event):
        self.device.remove_watcher('console', self.update_text)
        self.device.remove('window', 'Terminal')
        event.Skip()

    def shutdown(self,  channel):
        try:
            self.Close()
        except RuntimeError:
            pass

    def update_text(self, text):
        wx.CallAfter(self.update_text_gui, text + '\n')

    def update_text_gui(self, text):
        try:
            self.text_main.AppendText(text)
        except RuntimeError:
            pass

    def __set_properties(self):
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

    def on_key_down(self, event):
        key = event.GetKeyCode()
        if self.FindFocus() is not self.text_entry:
            self.text_entry.SetFocus()
            self.text_entry.AppendText(str(chr(key)).lower())
        try:
            if key == wx.WXK_DOWN:
                self.text_entry.SetValue(self.command_log[self.command_position + 1])
                wx.CallAfter(self.text_entry.SetInsertionPointEnd)
                self.command_position += 1
            elif key == wx.WXK_UP:
                self.text_entry.SetValue(self.command_log[self.command_position - 1])
                wx.CallAfter(self.text_entry.SetInsertionPointEnd)
                self.command_position -= 1
        except IndexError:
            pass
        event.Skip()

    def on_entry(self, event):  # wxGlade: Terminal.<event_handler>
        if self.pipe is not None:
            command = self.text_entry.GetValue()
            self.pipe.write(command + '\n')
            self.text_entry.SetValue('')
            self.command_log.append(command)
            self.command_position = 0
        event.Skip()
