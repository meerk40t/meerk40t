import wx
from wx import aui
from wx import richtext

from ..icons import icons8_console_50
from ..mwindow import MWindow

_ = wx.GetTranslation

RICHTEXT_TRANSLATE = {
    "[Red]":    "",
}


def register_panel_console(window, context):
    panel = ConsolePanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Bottom()
        .Layer(2)
        .MinSize(600, 100)
        .FloatingSize(600, 230)
        .Caption(_("Console"))
        .Name("console")
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = 600
    pane.control = panel

    window.on_pane_add(pane)
    context.register("pane/console", pane)

    @context.console_command(
        "cls",
        help=_("Clear console screen"),
    )
    def clear_console(channel, _, *args, **kwargs):
        panels = [
            context.opened[x]
            for x in ("window/Console", "window/Terminal")
            if x in context.opened
        ]

        panels.append(
            context.registered["pane/console"]
        )
        for panel in panels:
            panel.control.clear()

class ConsolePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.text_main = richtext.RichTextCtrl(
            self,
            wx.ID_ANY,
            "",
            style=wx.richtext.RE_MULTILINE
            | wx.richtext.RE_READONLY
        )
        self.text_main.BeginSuppressUndo()
        font = wx.Font(
            10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,
        )
        textattr = wx.TextAttr(wx.Colour(0), font=font)
        textattr.SetLineSpacing(0)
        textattr = richtext.RichTextAttr(textattr)
        self.text_main.SetBasicStyle(textattr)
        self.text_main.SetFont(font)
        self.text_main.BeginLineSpacing(0)
        self.text_main.BeginParagraphSpacing(0, 0)
        self.text_main.BeginLeftIndent(0, 320)

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

    def clear(self):
        self.text_main.Clear()

    def update_text(self, text):
        if not wx.IsMainThread():
            wx.CallAfter(self.update_text_gui, str(text) + "\n")
        else:
            self.update_text_gui(str(text) + "\n")

    def update_text_gui(self, text):
        try:
            self.text_main.WriteText(text)
            self.text_main.ScrollIntoView(self.text_main.GetLastPosition(), wx.WXK_END)
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


class Console(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(581, 410, *args, **kwds)
        self.control = ConsolePanel(self, wx.ID_ANY, context=self.context)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_console_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Console"))
        self.Layout()

    def window_open(self):
        self.control.initialize()

    def window_close(self):
        self.control.finalize()
