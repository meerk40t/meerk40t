import os
import threading

import wx
from wx import aui

from meerk40t.gui.icons import STD_ICON_SIZE, icons8_console
from meerk40t.gui.mwindow import MWindow
from meerk40t.kernel import signal_listener
from meerk40t.gui.wxutils import TextCtrl

try:
    from wx import richtext
except ImportError:
    print("import of wx.richtext for console failed, using default console window")


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
        .MinSize(100, 100)
        .FloatingSize(600, 230)
        .Caption(_("Console"))
        .Name("console")
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = 600
    pane.control = panel
    pane.helptext = _("Open command interface")

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

    @context.console_option("reset", "r", type=bool, action="store_true")
    @context.console_command(
        ("console_font"),
        help=_("Sets the console font"),
    )
    def set_console_font(channel, _, reset=False, *args, **kwargs):
        def getfont(initial):
            result = ""
            data = wx.FontData()
            data.EnableEffects(True)
            cur_font = None
            if initial:
                try:
                    cur_font = wx.Font()
                    success = cur_font.SetNativeFontInfo(initial)
                    if not success:
                        cur_font = None
                except Exception:
                    pass
            if cur_font is None:
                cur_font = wx.Font(
                10,
                wx.FONTFAMILY_TELETYPE,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
            data.SetInitialFont(cur_font)

            dlg = wx.FontDialog(window, data)

            if dlg.ShowModal() == wx.ID_OK:
                data = dlg.GetFontData()
                font = data.GetChosenFont()
                result = font.GetNativeFontInfoDesc()

            # Don't destroy the dialog until you get everything you need from the
            # dialog!
            dlg.Destroy()
            return result

        current = context.setting(str, "console_font", "")
        if reset:
            context.console_font = ""
        else:
            # Show Fontdialog
            result = getfont(current)
            context.console_font = result
        if "window/Console" in context.opened:
            w = context.opened["window/Console"]
            w.panel.reset_font()
        if "pane/console" in context.opened:
            w = context.opened["pane/console"]
            w.control.reset_font()
        channel(_("Font has been changed"))


class ConsolePanel(wx.ScrolledWindow):
    def __init__(self, *args, context=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.ScrolledWindow.__init__(self, *args, **kwargs)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("notes")
        font = self.get_font()
        self.text_entry = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB
        )
        self.richtext = False

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
            self.richtext = True

        except NameError:
            self.text_main = TextCtrl(
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
        self.command_list = list(self.context.kernel.match("command/.*/.*"))
        self.command_list.sort()
        self.command_context = list()
        for command_name in self.command_list:
            parts = command_name.split("/")
            context_item = parts[1]
            if context_item != "None" and context_item not in self.command_context:
                self.command_context.append(context_item)

    def get_font(self):
        font = None
        fontdesc = self.context.setting(str, "console_font", "")
        if fontdesc:
            # print (f"Try fontdesc: {fontdesc}")
            try:
                font = wx.Font(fontdesc)
            except Exception as e:
                # print (e)
                font = None
        if font is None:
            font = wx.Font(
                10,
                wx.FONTFAMILY_TELETYPE,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        return font

    def reset_font(self):
        font = self.get_font()
        if self.richtext:
            self.style.SetFont(font)
            self.text_main.SetBasicStyle(self.style)
            self.text_main.SetDefaultStyle(self.style)
            self.text_main.Update()
        else:
            self.text_main.SetFont(font)
        self.Refresh()

    def style_normal(self, style):
        return self.style

    def background_color(self):
        return self.context.themes.get("win_bg")
        # return wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)

    @property
    def is_dark(self):
        # try:
        #     res = wx.SystemSettings().GetAppearance().IsDark()
        # except AttributeError:
        #     res = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        return self.context.themes.dark

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
        self.text_main.SetValue("")
        self.text_main.Clear()

    def update_text(self, text):
        with self._buffer_lock:
            self._buffer += f"{text}\n"
            if len(self._buffer) > 50000:
                self._buffer = self._buffer[-50000:]
        if getattr(self.context, "process_console_in_realtime", False):
            self.update_console_main("internal")
        else:
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
        try:
            if not self.text_main.IsEmpty():
                self.text_main.AppendText("\n")
        except RuntimeError:
            return
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
            elif key == wx.WXK_TAB:
                # Let's try some autocompletion or at least show possible candidates
                content = self.text_entry.GetValue()
                words = content.split(" ")
                if len(words):
                    short_check = words[0]
                    context_str = ""
                    if len(short_check):
                        if len(words) > 1 and short_check in self.command_context:
                            context_str = short_check + " "
                            short_check = words[1]
                        long_check = context_str + short_check
                        full_match = False
                        found = 0
                        candidate = ""
                        for command_name in self.command_list:
                            parts = command_name.split("/")
                            command_item = parts[2]
                            full_item = command_item
                            if parts[1] != "None":
                                full_item = parts[1] + " " + full_item
                            # print (f"Compare {s} to {command_item}")
                            if context_str == "":
                                if command_item == short_check:
                                    candidate = command_item
                                    full_match = True
                                elif short_check in command_item:
                                    candidate = command_item
                                    found += 1
                            else:
                                if full_item == long_check:
                                    candidate = command_item
                                    full_match = True
                                elif long_check in full_item:
                                    candidate = command_item
                                    found += 1
                        self.context(f"?? {long_check}\n")
                        if full_match or found == 1:
                            self.context(f"help {candidate}\n")
                        if found == 0 and context_str == "":
                            context_candidate = ""
                            for context_name in self.command_context:
                                if context_name.startswith(short_check):
                                    found += 1
                                    context_candidate = context_name
                            # Only set if we did not provide  parameters already
                            if found == 1 and len(words) == 1:
                                self.text_entry.SetValue(f"{context_candidate} ")
                                self.text_entry.SetInsertionPointEnd()
                        elif found == 1:
                            # Only set if we did not provide  parameters already
                            if len(words) == 1 or (
                                len(words) == 2 and context_str != ""
                            ):
                                self.text_entry.SetValue(f"{context_str}{candidate}")
                                self.text_entry.SetInsertionPointEnd()
                # We are consuming the key...
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
        safe_dir = self.context.kernel.os_information["WORKDIR"]
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
        def tail(fs, window=1):
            """
            Returns the last `window` lines of file `f` as a list of bytes.
            """
            if window == 0:
                return b""
            BUFSIZE = 1024
            fs.seek(0, 2)
            end = fs.tell()
            nlines = window + 1
            data = []
            while nlines > 0 and end > 0:
                i = max(0, end - BUFSIZE)
                nread = min(end, BUFSIZE)

                fs.seek(i)
                chunk = fs.read(nread)
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
        if fexists:
            result = []
            try:
                with open(fname, "rb") as f:
                    result = (
                        tail(f, 3 * limit).decode("utf-8", errors="ignore").splitlines()
                    )
            except (PermissionError, OSError):
                # Could not load
                pass
            for entry in result:
                if len(self.command_log) and entry == self.command_log[-1]:
                    # print (f"ignored duplicate {entry}")
                    continue
                self.command_log.append(entry)
            if len(self.command_log) > limit:
                self.command_log = self.command_log[-limit:]


class Console(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(550, 450, *args, **kwds)
        self.panel = ConsolePanel(self, wx.ID_ANY, context=self.context)
        self.sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_console.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Console"))
        self.Layout()
        self.restore_aspect(honor_initial_values=True)

    @staticmethod
    def sub_register(kernel):
        kernel.register("wxpane/Console", register_panel_console)
        kernel.register(
            "button/preparation/Console",
            {
                "label": _("Console"),
                "icon": icons8_console,
                "tip": _("Open Console Window"),
                "help": "console",
                "action": lambda v: kernel.console("window toggle Console\n"),
                "size": STD_ICON_SIZE,
                "priority": 4,
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def helptext():
        return _("Open command interface")
