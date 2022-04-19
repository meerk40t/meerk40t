import threading

import wx
from wx import aui, richtext

from meerk40t.gui.icons import icons8_console_50
from meerk40t.gui.mwindow import MWindow

_ = wx.GetTranslation


def background_color(colour):
    def style_color(style):
        style.SetBackgroundColour(wx.Colour(colour))
        return style

    return style_color


def foreground_color(colour):
    def style_color(style):
        style.SetTextColour(wx.Colour(colour))
        return style

    return style_color


def style_bold(style):
    style.SetFontWeight(wx.FONTWEIGHT_BOLD)
    return style


def style_unbold(style):
    style.SetFontWeight(wx.FONTWEIGHT_NORMAL)
    return style


def style_italic(style):
    style.SetFontStyle(wx.FONTSTYLE_ITALIC)
    return style


def style_unitalic(style):
    style.SetFontStyle(wx.FONTSTYLE_NORMAL)
    return style


def style_underline(style):
    style.SetFontUnderlined(True)
    return style


def style_ununderline(style):
    style.SetFontUnderlined(False)
    return style


def style_negate(style):
    bg_colour = style.BackgroundColour
    fg_colour = style.TextColour
    style.SetBackgroundColour(fg_colour)
    style.SetTextColour(bg_colour)
    return style


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
        if "window/Console" in context.opened:
            w = context.opened["window/Console"]
            w.panel.clear()
        if "pane/console" in context.opened:
            w = context.opened["pane/console"]
            w.control.clear()


class ConsolePanel(wx.ScrolledWindow):
    def __init__(self, *args, context=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.ScrolledWindow.__init__(self, *args, **kwargs)
        self.context = context

        font = wx.Font(
            10,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        self.text_entry = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB
        )

        try:
            self.text_main = richtext.RichTextCtrl(
                self,
                wx.ID_ANY,
                "",
                style=wx.richtext.RE_MULTILINE
                | wx.richtext.RE_READONLY
                | wx.BG_STYLE_SYSTEM
                | wx.VSCROLL
                | wx.ALWAYS_SHOW_SB,
            )
            self.text_main.SetEditable(False)
            self.text_main.BeginSuppressUndo()
            style = wx.TextAttr()

            style.SetFont(font)
            style.SetLineSpacing(0)
            style.SetParagraphSpacingBefore(0)
            style.SetParagraphSpacingAfter(0)
            bg = self.background_color()
            if self.is_dark:
                fg = wx.Colour("white")
            else:
                fg = wx.Colour("black")
            style.SetTextColour(fg)
            style.SetBackgroundColour(bg)

            self.text_main.SetForegroundColour(fg)
            self.text_main.SetBackgroundColour(bg)
            self.text_entry.SetForegroundColour(fg)
            self.text_entry.SetBackgroundColour(bg)
            self.text_entry.SetDefaultStyle(style)

            style = richtext.RichTextAttr(style)
            style.SetLeftIndent(0, 320)
            self.text_main.SetBasicStyle(style)
            self.text_main.SetDefaultStyle(style)
            self.style = style
            self.text_main.Update()  # Apply style to just opened window
            self._update_text = self.update_text_rich

        except NameError:
            self.text_main = wx.TextCtrl(
                self, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY
            )
            self.text_main.SetFont(font)
            self._update_text = self.update_text_text

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down, self.text_entry)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_enter, self.text_entry)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down_main, self.text_main)
        self.Bind(wx.EVT_TEXT_URL, self.on_text_uri)
        # end wxGlade
        self.command_log = []
        self.command_position = 0

        self.ansi_styles = {
            "\033[30m": foreground_color("black"),  # "black"
            "\033[31m": foreground_color("red"),  # "red"
            "\033[32m": foreground_color("green"),  # "green"
            "\033[33m": foreground_color("yellow"),  # "yellow"
            "\033[34m": foreground_color("blue"),  # "blue"
            "\033[35m": foreground_color("magenta"),  # "magenta"
            "\033[36m": foreground_color("cyan"),  # "cyan"
            "\033[37m": foreground_color("white"),  # "white"
            "\033[40m": background_color("black"),  # "bg-black"
            "\033[41m": background_color("red"),  # "bg-red"
            "\033[42m": background_color("green"),  # "bg-green"
            "\033[43m": background_color("yellow"),  # "bg-yellow"
            "\033[44m": background_color("blue"),  # "bg-blue"
            "\033[45m": background_color("magenta"),  # "bg-magenta"
            "\033[46m": background_color("cyan"),  # "bg-cyan"
            "\033[47m": background_color("white"),  # "bg-white"
            "\033[1m": style_bold,  # "bold"
            "\033[22m": style_unbold,  # "/bold"
            "\033[3m": style_italic,  # "italic"
            # "\033[3m": style_unitalic, # "/italic"
            "\033[4m": style_underline,  # "underline"
            "\033[24m": style_ununderline,  # "/underline"
            "\033[7m": None,  # "negative"
            "\033[27m": None,  # "positive"
            "\033[0m": self.style_normal,  # "normal"
        }

    def style_normal(self, style):
        return self.style

    def background_color(self):
        return wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)

    @property
    def is_dark(self):
        return wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127

    def __set_properties(self):
        # begin wxGlade: ConsolePanel.__set_properties
        self.text_entry.SetFocus()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ConsolePanel.__do_layout
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.text_main, 1, wx.EXPAND, 0)
        sizer_2.Add(self.text_entry, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_2)
        sizer_2.FitInside(self)
        self.Layout()
        # end wxGlade

    def pane_show(self, *args):
        self.context.channel("console").watch(self.update_text)

    def pane_hide(self, *args):
        self.context.channel("console").unwatch(self.update_text)

    def clear(self):
        self.text_main.Clear()

    def update_text(self, text):
        if not wx.IsMainThread():
            wx.CallAfter(self._update_text, text)
        else:
            self._update_text(text)

    def update_text_text(self, text):
        self.process_text_text_line(str(text))

    def update_text_rich(self, text):
        self.process_text_rich_line(str(text))

    def process_text_text_line(self, lines):
        text = ""
        ansi_text = ""
        ansi = False
        if not self.text_main.IsEmpty():
            self.text_main.AppendText("\n")
        for c in lines:
            b = ord(c)
            if c == "\n":
                if text:
                    self.text_main.AppendText(text)
                    text = ""
            if b == 27:
                ansi = True
            if ansi:
                ansi_text += c
                if c == "m":
                    if text:
                        self.text_main.AppendText(text)
                        text = ""
                    ansi = False
                    ansi_text = ""
                continue
            text += c
        if text:
            self.text_main.AppendText(text)
        # self.text_main.AppendText(lines)

    def process_text_rich_line(self, lines):
        """
        Update rich text code line. This only works if text_main is a RichText box.

        @param lines:
        @return:
        """
        self.text_main.SetInsertionPointEnd()
        ansi = False
        ansi_text = ""
        text = ""
        if not self.text_main.IsEmpty():
            self.text_main.Newline()
            self.text_main.BeginStyle(self.style)

        for c in lines:
            b = ord(c)
            if c == "\n":
                if text:
                    self.text_main.WriteText(text)
                    text = ""
                self.text_main.Newline()
                self.text_main.BeginStyle(self.style)
            if b == 27:
                ansi = True
            if ansi:
                ansi_text += c
                if c == "m":
                    if text:
                        self.text_main.WriteText(text)
                        text = ""
                    style_function = self.ansi_styles.get(ansi_text)
                    if style_function is not None:
                        new_style = style_function(self.text_main.GetDefaultStyleEx())
                        self.text_main.EndStyle()
                        if new_style is not None:
                            self.text_main.BeginStyle(new_style)
                    ansi = False
                    ansi_text = ""
                continue
            text += c
        if text:
            self.text_main.WriteText(text)
        self.text_main.EndStyle()
        self.text_main.ScrollIntoView(self.text_main.GetLastPosition(), wx.WXK_END)
        self.text_main.Update()

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

    def on_enter(self, event):  # wxGlade: Terminal.<event_handler>
        command = self.text_entry.GetValue()
        self.context(command + "\n")
        self.text_entry.SetValue("")
        self.command_log.append(command)
        self.command_position = 0
        event.Skip(False)


class Console(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(581, 410, *args, **kwds)
        self.panel = ConsolePanel(self, wx.ID_ANY, context=self.context)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_console_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Console"))
        self.Layout()

    @staticmethod
    def sub_register(kernel):
        kernel.register("wxpane/Console", register_panel_console)
        kernel.register(
            "button/project/Console",
            {
                "label": _("Console"),
                "icon": icons8_console_50,
                "tip": _("Open Console Window"),
                "action": lambda v: kernel.console("window toggle Console\n"),
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()
