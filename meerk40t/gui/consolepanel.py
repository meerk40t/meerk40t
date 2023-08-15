import os
import threading

import wx
from wx import aui

from meerk40t.kernel import get_safe_path, signal_listener
#
# try:
#     from wx import richtext
# except ImportError:
#     print("import of wx.richtext for console failed, using default console window")

from meerk40t.gui.icons import STD_ICON_SIZE, icons8_console_50
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

    window.on_pane_create(pane)
    context.register("pane/console", pane)

    @context.console_command(
        ("cls", "clear"),
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
        self.load_log()

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
        self._buffer = ""
        self._buffer_lock = threading.Lock()

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
        with self._buffer_lock:
            self._buffer += f"{text}\n"
            if len(self._buffer) > 50000:
                self._buffer = self._buffer[-50000:]
        self.context.signal("console_update")

    @signal_listener("console_update")
    def update_console_main(self, origin, *args):
        with self._buffer_lock:
            buffer = self._buffer
            self._buffer = ""
        # Update text depends on rich/normal text_field
        self._update_text(buffer)

    def update_text_text(self, text):
        # If normal called by self._update_text
        self.process_text_text_line(str(text))

    def update_text_rich(self, text):
        # If rich called by self._update_text
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

    def process_text_rich_line(self, lines):
        """
        Update rich text code line. This only works if text_main is a RichText box.

        @param lines:
        @return:
        """
        try:
            self.text_main.SetInsertionPointEnd()
        except RuntimeError:
            # Console is shutdown.
            return
        ansi = False
        ansi_text = ""
        text = ""
        open_style = False
        for c in lines:
            b = ord(c)
            if c == "\n":
                if text:
                    self.text_main.WriteText(text)
                    text = ""
                self.text_main.Newline()
                self.text_main.BeginStyle(self.style)
                open_style = True
                continue  # New Line is already processed.
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
                        if open_style:
                            self.text_main.EndStyle()
                            open_style = False
                        if new_style is not None:
                            self.text_main.BeginStyle(new_style)
                            open_style = True
                    ansi = False
                    ansi_text = ""
                continue
            text += c
        if text:
            self.text_main.WriteText(text)
        if open_style:
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
        def isrealchar(keycode):
            if keycode in (wx.WXK_LEFT, wx.WXK_RIGHT):
                # There are much more, but I am lazy...
                return False
            else:
                return chr(keycode).isprintable

        def refocus():
            self.text_entry.SetInsertionPointEnd()
            self.text_entry.SetFocus()

        key = event.GetKeyCode()
        if key != wx.WXK_CONTROL and (key != ord("C")) and not event.ControlDown():
            if self.FindFocus() is not self.text_entry:
                try:
                    if key == wx.WXK_DOWN:
                        self.text_entry.SetValue(
                            self.command_log[self.command_position + 1]
                        )
                        if not wx.IsMainThread():
                            wx.CallAfter(refocus)
                        else:
                            refocus()
                        self.command_position += 1
                    elif key == wx.WXK_UP:
                        self.text_entry.SetValue(
                            self.command_log[self.command_position - 1]
                        )
                        if not wx.IsMainThread():
                            wx.CallAfter(refocus)
                        else:
                            refocus()
                        self.command_position -= 1
                    elif isrealchar(key):
                        self.text_entry.SetFocus()
                        self.text_entry.AppendText(str(chr(key)).lower())
                    else:
                        self.text_entry.SetFocus()
                        # event.Skip()
                except IndexError:
                    self.command_position = 0
                    self.text_entry.SetValue("")
        else:
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
            self.command_position = 0
            self.text_entry.SetValue("")

    def on_enter(self, event):  # wxGlade: Terminal.<event_handler>
        command = self.text_entry.GetValue()
        self.command_log.append(command)
        self.save_log(command)
        self.command_position = 0
        self.context(command + "\n")
        self.text_entry.SetValue("")
        event.Skip(False)

    def history_filename(self):
        safe_dir = os.path.realpath(get_safe_path(self.context.kernel.name))
        fname = os.path.join(safe_dir, "cmdhistory.log")
        is_there = os.path.exists(fname)
        return fname, is_there

    def save_log(self, last_command):
        fname, fexists = self.history_filename()
        try:
            history_file = open(fname, "a", encoding="utf-8")  # Append mode
            history_file.write(last_command + "\n")
            history_file.close()
        except (PermissionError, OSError):
            # Could not save
            pass

    def load_log(self):
        def tail(f, window=1):
            """
            Returns the last `window` lines of file `f` as a list of bytes.
            """
            if window == 0:
                return b""
            BUFSIZE = 1024
            f.seek(0, 2)
            end = f.tell()
            nlines = window + 1
            data = []
            while nlines > 0 and end > 0:
                i = max(0, end - BUFSIZE)
                nread = min(end, BUFSIZE)

                f.seek(i)
                chunk = f.read(nread)
                data.append(chunk)
                nlines -= chunk.count(b"\n")
                end -= nread
            return b"\n".join(b"".join(reversed(data)).splitlines()[-window:])

        # Restores the last 50 commands from disk

        self.context.setting(int, "history_limit", 50)
        limit = int(self.context.history_limit)
        # print (f"Limit = {limit}")
        self.command_log = [""]
        fname, fexists = self.history_filename()
        if fexists:
            result = []
            try:
                with open(fname, "rb") as f:
                    result = tail(f, limit).decode("utf-8").splitlines()
            except (PermissionError, OSError):
                # Could not load
                pass
            for entry in result:
                self.command_log.append(entry)


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
            "button/preparation/Console",
            {
                "label": _("Console"),
                "icon": icons8_console_50,
                "tip": _("Open Console Window"),
                "action": lambda v: kernel.console("window toggle Console\n"),
                "size": STD_ICON_SIZE,
                "priority": 4,
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()
