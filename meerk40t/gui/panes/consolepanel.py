import wx

_ = wx.GetTranslation


class ConsolePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.text_main = wx.TextCtrl(
            self,
            wx.ID_ANY,
            "",
            style=wx.TE_BESTWRAP
            | wx.TE_MULTILINE
            | wx.TE_READONLY
            | wx.TE_RICH2
            | wx.TE_AUTO_URL,
        )
        self.text_main.SetFont(
            wx.Font(
                10, wx.FONTFAMILY_TELETYPE, wx.NORMAL, wx.NORMAL, faceName="Monospace"
            )
        )
        self.text_entry = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down, self.text_entry)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_entry, self.text_entry)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down_main, self.text_main)
        self.Bind(wx.EVT_TEXT_URL, self.on_text_uri)
        # end wxGlade
        self.command_log = []
        self.command_position = 0

    def __set_properties(self):
        # begin wxGlade: ConsolePanel.__set_properties
        self.text_entry.SetFocus()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ConsolePanel.__do_layout
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.text_main, 20, wx.EXPAND, 0)
        sizer_2.Add(self.text_entry, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_2)
        sizer_2.Fit(self)
        self.Layout()
        # end wxGlade

    def initialize(self, *args):
        self.context.channel("console").watch(self.update_text)

    def finalize(self, *args):
        self.context.channel("console").unwatch(self.update_text)

    def update_text(self, text):
        if not wx.IsMainThread():
            wx.CallAfter(self.update_text_gui, str(text) + "\n")
        else:
            self.update_text_gui(str(text) + "\n")

    def update_text_gui(self, text):
        try:
            self.text_main.AppendText(text)
        except RuntimeError:
            pass

    def on_text_uri(self, event):
        mouse_event = event.GetMouseEvent()
        if mouse_event.LeftDClick():
            url_start = event.GetURLStart()
            url_end = event.GetURLEnd()
            url = self.text_main.GetRange(url_start, url_end)
            import webbrowser

            webbrowser.open_new_tab(url)

    def on_key_down_main(self, event):
        key = event.GetKeyCode()
        if key != wx.WXK_CONTROL and (key != ord("C") or not event.ControlDown()):
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
        self.context(command + "\n")
        self.text_entry.SetValue("")
        self.command_log.append(command)
        self.command_position = 0
        event.Skip(False)
