import re
import wx
from wx import aui
from wx import richtext

from ..icons import icons8_console_50
from ..mwindow import MWindow

_ = wx.GetTranslation

def bg_Colour(colour):
    def styColour(style):
        style.SetBackgroundColour(wx.Colour(colour))
        return style
    return styColour

def fg_Colour(colour):
    def styColour(style):
        style.SetTextColour(wx.Colour(colour))
        return style
    return styColour

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

BBCODE_LIST = {
    "black":        fg_Colour("black"),
    "red":          fg_Colour("red"),
    "green":        fg_Colour("green"),
    "yellow":       fg_Colour("yellow"),
    "blue":         fg_Colour("blue"),
    "magenta":      fg_Colour("magenta"),
    "cyan":         fg_Colour("cyan"),
    "white":        fg_Colour("white"),
    "bg-black":     bg_Colour("black"),
    "bg-red":       bg_Colour("red"),
    "bg-green":     bg_Colour("green"),
    "bg-yellow":    bg_Colour("yellow"),
    "bg-blue":      bg_Colour("blue"),
    "bg-magenta":   bg_Colour("magenta"),
    "bg-cyan":      bg_Colour("cyan"),
    "bg-white":     bg_Colour("white"),
    "bold":         style_bold,
    "/bold":        style_unbold,
    "italic":       style_italic,
    "/italic":      style_unitalic,
    "underline":    style_underline,
    "/underline":   style_ununderline,
    "underscore":   style_underline,
    "/underscore":  style_ununderline,
    "normal":       None,
    "negative":     None,
    "positive":     None,
    "raw":          None,
    "/raw":         None,
}

RE_BBCODE = re.compile(
    r"(%s)" %
        (r"|".join([r"\[%s\]" % x for x in BBCODE_LIST])),
    re.IGNORECASE,
)

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
            | wx.BG_STYLE_SYSTEM
        )
        self.text_main.SetEditable(False)
        self.text_main.BeginSuppressUndo()

        self.text_entry = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB
        )

        # style = richtext.RichTextAttr()
        style = wx.TextAttr()
        font = wx.Font(
            10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,
        )
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
        self.text_main.Update()  # Apply style to just opened window

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down, self.text_entry)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_enter, self.text_entry)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down_main, self.text_main)
        self.Bind(wx.EVT_TEXT_URL, self.on_text_uri)
        # end wxGlade
        self.command_log = []
        self.command_position = 0

    def background_color(self):
        return wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)

    @property
    def is_dark(self):
        return wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW).GetLuminance() < 0.5

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
            wx.CallAfter(self.update_text_gui, str(text))
        else:
            self.update_text_gui(str(text))

    def update_text_gui(self, lines, bbcode=True):
        lines = lines.split("\n") if "\n" in lines else [lines]
        basic_style = self.text_main.BasicStyle
        raw = negative = False
        self.text_main.SetInsertionPointEnd()
        for text in lines:
            self.text_main.BeginStyle(basic_style)
            parts = RE_BBCODE.split(text)
            for part in parts:
                if part == "":
                    continue
                tag = part[1:-1].lower()
                if (
                    bbcode
                    and part.startswith("[")
                    and part.endswith("]")
                    and tag in BBCODE_LIST
                ):
                    if tag[-3:] == "raw":
                        raw = tag == "raw"
                        continue
                    if not raw:
                        style = self.text_main.DefaultStyleEx
                        if negative:
                            style = style_negate(style)
                        if tag in ("negative", "positive", "normal"):
                            negative = tag == "negative"
                        if tag == "normal":
                            style = basic_style
                        else:
                            getstyle = BBCODE_LIST[part[1:-1].lower()]
                            if getstyle:
                                style = getstyle(style)
                        if negative:
                            style = style_negate(style)
                        self.text_main.EndStyle()
                        self.text_main.BeginStyle(style)
                        continue
                self.text_main.WriteText(part)
            self.text_main.EndStyle()
            self.text_main.Newline()
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
