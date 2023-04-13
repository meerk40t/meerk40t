import platform

import wx

from meerk40t.gui.fonts import wxfont_to_svg
from meerk40t.gui.laserrender import LaserRender
from meerk40t.gui.wxutils import ScrolledPanel, StaticBoxSizer

from ...svgelements import Color
from ..icons import icons8_choose_font_50, icons8_text_50
from ..laserrender import swizzlecolor
from ..mwindow import MWindow
from .attributes import ColorPanel, IdPanel, PositionSizePanel, PreventChangePanel

_ = wx.GetTranslation


class PromptingComboBox(wx.ComboBox):
    def __init__(self, parent, choices=None, style=0, **kwargs):
        if choices is None:
            choices = []
        wx.ComboBox.__init__(
            self,
            parent,
            wx.ID_ANY,
            style=style | wx.CB_DROPDOWN,
            choices=choices,
            **kwargs,
        )
        self.choices = choices
        self.Bind(wx.EVT_TEXT, self.OnText)
        self.Bind(wx.EVT_KEY_DOWN, self.OnPress)
        self.ignore_evt_text = False
        self.delete_key = False
        self.pre_found = False

    def OnPress(self, event):
        if event.GetKeyCode() == 8:
            self.delete_key = True
        event.Skip()

    def OnText(self, event):
        current_text = event.GetString()
        if self.ignore_evt_text:
            self.ignore_evt_text = False
            return
        if self.delete_key:
            self.delete_key = False
            if self.pre_found:
                current_text = current_text[:-1]

        self.pre_found = False
        for choice in self.choices:
            if choice.startswith(current_text):
                self.ignore_evt_text = True
                self.SetValue(choice)
                self.SetInsertionPoint(len(current_text))
                self.SetTextSelection(len(current_text), len(choice))
                self.pre_found = True
                break
        event.Skip()


class FontHistory(wx.Panel):
    def __init__(self, *args, context=None, textbox=None, callback=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.FONTHISTORY = 4
        self.context = context
        self.last_font = []
        self.callback = callback
        self.textbox = textbox
        self.default_font = wx.Font(
            14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
        )

        for i in range(self.FONTHISTORY):
            self.last_font.append(
                wx.StaticText(
                    self,
                    wx.ID_ANY,
                    _("<empty>"),
                    style=wx.ALIGN_CENTER_VERTICAL
                    # | wx.ST_ELLIPSIZE_END
                    | wx.ST_NO_AUTORESIZE,
                )
            )
            self.last_font[i].SetMinSize((120, 90))
            self.last_font[i].SetFont(self.default_font)
            self.last_font[i].SetToolTip(_("Choose last used font-settings"))
            self.textbox.Bind(wx.EVT_TEXT, self.on_text_change)

        self.load_font_history()
        sizer_h_fonthistory = StaticBoxSizer(
            self, wx.ID_ANY, _("Last Font-Entries"), wx.HORIZONTAL
        )
        for i in range(self.FONTHISTORY):
            sizer_h_fonthistory.Add(
                self.last_font[i], 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 1
            )
        self.SetSizer(sizer_h_fonthistory)
        self.Layout()
        for i in range(self.FONTHISTORY):
            self.last_font[i].Bind(wx.EVT_LEFT_DOWN, self.on_last_font)

    def on_text_change(self, event):
        txt = self.textbox.GetValue()
        for i in range(self.FONTHISTORY):
            self.last_font[i].SetLabel(txt)
        event.Skip()

    def on_last_font(self, event):
        if self.callback is None:
            return
        obj = event.EventObject
        self.callback(obj.GetForegroundColour(), obj.GetFont())

    def store_font_history(self, font):
        fontdesc = font.GetNativeFontInfoDesc()
        # Is the fontdesc already contained?
        if fontdesc in self.history:
            # print (f"Was already there: {fontdesc}")
            return
        for i in range(self.FONTHISTORY - 1, 0, -1):
            self.history[i] = self.history[i - 1]
        self.history[0] = fontdesc
        for i in range(self.FONTHISTORY):
            setattr(self.context, f"fonthistory_{i}", self.history[i])
        self.context.flush()

    def load_font_history(self):
        self.history = []
        defaultfontdesc = self.default_font.GetNativeFontInfoUserDesc()
        for i in range(self.FONTHISTORY):
            self.context.setting(str, f"fonthistory_{i}", defaultfontdesc)
            fontdesc = getattr(self.context, f"fonthistory_{i}")
            self.history.append(fontdesc)
            font = wx.Font(fontdesc)
            self.last_font[i].SetFont(font)


class TextVariables(wx.Panel):
    def __init__(self, *args, context=None, textbox=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.textbox = textbox
        # populate listbox
        choices = self.context.elements.mywordlist.get_variable_list()
        self.lb_variables = wx.ListBox(self, wx.ID_ANY, choices=choices)
        self.lb_variables.SetToolTip(_("Double click a variable to add it to the text"))
        sizer_h_variables = StaticBoxSizer(
            self,
            wx.ID_ANY,
            _("Available Variables (double click to use)"),
            wx.HORIZONTAL,
        )
        sizer_h_variables.Add(self.lb_variables, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_h_variables)
        self.Layout()
        self.lb_variables.Bind(wx.EVT_LISTBOX_DCLICK, self.on_variable_dclick)

    def on_variable_dclick(self, event):
        svalue = event.GetString()
        svalue = svalue[0 : svalue.find(" (")]
        svalue = self.textbox.GetValue() + " {" + svalue + "}"
        self.textbox.SetValue(svalue.strip(" "))


class TextPropertyPanel(ScrolledPanel):
    def __init__(self, parent, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        super().__init__(parent, *args, **kwds)
        self.context = context
        self.renderer = LaserRender(self.context)

        self.text_text = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.node = node
        self.label_fonttest = wx.StaticText(
            self, wx.ID_ANY, "", style=wx.ST_ELLIPSIZE_END | wx.ST_NO_AUTORESIZE
        )
        self.label_fonttest.SetMinSize((-1, 90))
        self.label_fonttest.SetFont(
            wx.Font(
                16,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        self.button_choose_font = wx.BitmapButton(
            self, wx.ID_ANY, icons8_choose_font_50.GetBitmap(resize=25)
        )
        self.panel_id = IdPanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.panel_stroke = ColorPanel(
            self,
            id=wx.ID_ANY,
            label="Stroke:",
            attribute="stroke",
            callback=self.callback_color,
            context=self.context,
            node=self.node,
        )
        self.panel_fill = ColorPanel(
            self,
            id=wx.ID_ANY,
            label="Fill:",
            attribute="fill",
            callback=self.callback_color,
            context=self.context,
            node=self.node,
        )
        self.panel_lock = PreventChangePanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.panel_xy = PositionSizePanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.panel_variables = TextVariables(
            self, wx.ID_ANY, context=self.context, textbox=self.text_text
        )
        self.panel_history = FontHistory(
            self,
            wx.ID_ANY,
            context=self.context,
            textbox=self.text_text,
            callback=self.font_callback,
        )
        flist = wx.FontEnumerator()
        flist.EnumerateFacenames()
        elist = flist.GetFacenames()
        elist.sort()
        self.combo_font = PromptingComboBox(
            self, choices=elist, style=wx.TE_PROCESS_ENTER
        )
        # Linux requires a minimum  height / width to display a text inside a button
        system = platform.system()
        if system == "Darwin":
            mysize = 40
        elif system == "Windows":
            mysize = 23
        elif system == "Linux":
            mysize = 40
        else:
            mysize = 23
        self.button_attrib_larger = wx.Button(
            self, id=wx.ID_ANY, label="A", size=wx.Size(mysize, mysize)
        )
        self.button_attrib_smaller = wx.Button(
            self, id=wx.ID_ANY, label="a", size=wx.Size(mysize, mysize)
        )
        self.button_attrib_bold = wx.ToggleButton(
            self, id=wx.ID_ANY, label="b", size=wx.Size(mysize, mysize)
        )
        self.button_attrib_italic = wx.ToggleButton(
            self, id=wx.ID_ANY, label="i", size=wx.Size(mysize, mysize)
        )
        self.button_attrib_underline = wx.ToggleButton(
            self, id=wx.ID_ANY, label="u", size=wx.Size(mysize, mysize)
        )
        self.button_attrib_strikethrough = wx.ToggleButton(
            self, id=wx.ID_ANY, label="s", size=wx.Size(mysize, mysize)
        )

        self.check_variable = wx.CheckBox(self, wx.ID_ANY, _(" Translate Variables"))
        self.check_variable.SetToolTip(_("If active, preview will translate variables"))
        self.check_variable.SetValue(True)
        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TEXT, self.on_text_change, self.text_text)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter, self.text_text)
        self.Bind(wx.EVT_BUTTON, self.on_button_choose_font, self.button_choose_font)
        self.Bind(wx.EVT_COMBOBOX, self.on_font_choice, self.combo_font)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_font_choice, self.combo_font)
        self.combo_font.Bind(wx.EVT_KILL_FOCUS, self.on_font_choice)

        self.Bind(wx.EVT_BUTTON, self.on_button_larger, self.button_attrib_larger)
        self.Bind(wx.EVT_BUTTON, self.on_button_smaller, self.button_attrib_smaller)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_bold, self.button_attrib_bold)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_italic, self.button_attrib_italic)
        self.Bind(
            wx.EVT_TOGGLEBUTTON, self.on_button_underline, self.button_attrib_underline
        )
        self.Bind(
            wx.EVT_TOGGLEBUTTON,
            self.on_button_strikethrough,
            self.button_attrib_strikethrough,
        )
        self.rb_align.Bind(wx.EVT_RADIOBOX, self.on_radio_box)
        self.check_variable.Bind(wx.EVT_CHECKBOX, self.on_text_change)

    @staticmethod
    def accepts(node):
        if node.type == "elem text":
            return True
        return False

    def pane_show(self):
        self.set_widgets(self.node)

    def pane_hide(self):
        pass

    def set_widgets(self, node):
        self.panel_id.set_widgets(node)
        self.panel_stroke.set_widgets(node)
        self.panel_fill.set_widgets(node)
        self.panel_lock.set_widgets(node)
        self.panel_xy.set_widgets(node)

        if node is not None:
            self.node = node
        try:
            if self.node.text is not None:
                self.text_text.SetValue(self.node.text)
                display_string = self.node.text
                if self.check_variable.GetValue():
                    display_string = self.context.elements.wordlist_translate(
                        display_string,
                        self.node,
                        increment=False,
                    )
                self.label_fonttest.SetLabelText(display_string)
                try:
                    self.label_fonttest.SetFont(self.node.wxfont)
                except AttributeError:
                    pass
        except AttributeError:
            pass
        self.text_text.SetFocus()
        self.text_text.SelectAll()

    def __set_properties(self):

        self.button_choose_font.SetSize(self.button_choose_font.GetBestSize())

        self.button_attrib_bold.SetFont(
            wx.Font(
                9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, 0, ""
            )
        )
        self.button_attrib_italic.SetFont(
            wx.Font(
                9,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_ITALIC,
                wx.FONTWEIGHT_NORMAL,
                0,
                "",
            )
        )
        special_font = wx.Font(
            9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL, 0, ""
        )
        special_font.SetUnderlined(True)
        self.button_attrib_underline.SetFont(special_font)
        special_font2 = wx.Font(
            9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL, 0, ""
        )
        special_font2.SetStrikethrough(True)
        self.button_attrib_strikethrough.SetFont(special_font2)

        self.button_choose_font.SetToolTip(_("Choose System-font"))
        self.combo_font.SetToolTip(_("Choose System-font"))
        self.button_attrib_smaller.SetToolTip(_("Decrease fontsize"))
        self.button_attrib_larger.SetToolTip(_("Increase fontsize"))
        self.button_attrib_bold.SetToolTip(_("Toggle bold"))
        self.button_attrib_italic.SetToolTip(_("Toggle italic"))
        self.button_attrib_underline.SetToolTip(_("Toggle underline"))
        self.button_attrib_strikethrough.SetToolTip(_("Toggle strikethrough"))

        align_options = [_("Left"), _("Center"), _("Right")]
        self.rb_align = wx.RadioBox(
            self,
            wx.ID_ANY,
            "",
            wx.DefaultPosition,
            wx.DefaultSize,
            align_options,
            len(align_options),
            wx.RA_SPECIFY_COLS | wx.BORDER_NONE,
        )
        self.rb_align.SetToolTip(
            _("Define where to place the origin (i.e. current mouse position)")
        )

        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: TextProperty.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.panel_id, 0, wx.EXPAND, 0)

        sizer_font = wx.BoxSizer(wx.HORIZONTAL)
        sizer_font.Add(self.label_fonttest, 1, wx.EXPAND, 0)

        sizer_attrib = wx.BoxSizer(wx.HORIZONTAL)
        sizer_attrib.Add(self.button_choose_font, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_attrib.Add(self.combo_font, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_attrib.Add(self.button_attrib_larger, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_attrib.Add(self.button_attrib_smaller, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_attrib.Add(self.button_attrib_bold, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_attrib.Add(self.button_attrib_italic, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_attrib.Add(self.button_attrib_underline, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_attrib.Add(
            self.button_attrib_strikethrough, 0, wx.ALIGN_CENTER_VERTICAL, 0
        )

        sizer_anchor = wx.BoxSizer(wx.HORIZONTAL)
        sizer_anchor.Add(self.rb_align, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_anchor.AddSpacer(25)
        sizer_anchor.Add(self.check_variable, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_main.Add(self.text_text, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_attrib, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_anchor, 0, wx.EXPAND, 0)

        self.notebook = wx.Notebook(self, id=wx.ID_ANY)
        page_main = wx.Panel(self.notebook, wx.ID_ANY)
        sizer_page_main = wx.BoxSizer(wx.VERTICAL)
        self.panel_fill.Reparent(page_main)
        self.panel_stroke.Reparent(page_main)
        sizer_page_main.Add(self.panel_stroke, 0, wx.EXPAND, 0)
        sizer_page_main.Add(self.panel_fill, 0, wx.EXPAND, 0)
        page_main.SetSizer(sizer_page_main)

        def on_size_mm(evt):
            siz1 = self.GetSize()
            siz = (siz1[0] - 20, -1)
            page_main.SetSize(siz)
            page_main.Layout()

        page_main.Bind(wx.EVT_SIZE, on_size_mm)

        page_extended = wx.Panel(self.notebook, wx.ID_ANY)
        sizer_page_extended = wx.BoxSizer(wx.VERTICAL)
        self.panel_lock.Reparent(page_extended)
        self.panel_xy.Reparent(page_extended)
        sizer_page_extended.Add(self.panel_lock, 0, wx.EXPAND, 0)
        sizer_page_extended.Add(self.panel_xy, 0, wx.EXPAND, 0)
        page_extended.SetSizer(sizer_page_extended)

        def on_size_ex(evt):
            siz1 = self.GetSize()
            siz = (siz1[0] - 20, -1)
            page_extended.SetSize(siz)
            page_extended.Layout()

        page_extended.Bind(wx.EVT_SIZE, on_size_ex)

        page_variables = wx.Panel(self.notebook, wx.ID_ANY)
        sizer_page_variables = wx.BoxSizer(wx.VERTICAL)
        self.panel_variables.Reparent(page_variables)
        sizer_page_variables.Add(self.panel_variables, 1, wx.EXPAND, 0)
        page_variables.SetSizer(sizer_page_variables)

        def on_size_pv(evt):
            siz1 = self.GetSize()
            siz = (siz1[0] - 20, -1)
            page_variables.SetSize(siz)
            page_variables.Layout()

        page_variables.Bind(wx.EVT_SIZE, on_size_pv)

        page_fonthistory = wx.Panel(self.notebook, wx.ID_ANY)
        sizer_page_history = wx.BoxSizer(wx.VERTICAL)
        self.panel_history.Reparent(page_fonthistory)
        sizer_page_history.Add(self.panel_history, 1, wx.EXPAND, 0)
        page_fonthistory.SetSizer(sizer_page_history)

        def on_size_fh(evt):
            siz1 = self.GetSize()
            siz = (siz1[0] - 20, -1)
            page_fonthistory.SetSize(siz)
            page_fonthistory.Layout()

        page_fonthistory.Bind(wx.EVT_SIZE, on_size_fh)

        self.notebook.AddPage(page_main, _("Colors"))
        self.notebook.AddPage(page_variables, _("Text-Variables"))
        self.notebook.AddPage(page_fonthistory, _("Font-History"))
        self.notebook.AddPage(page_extended, _("Position"))
        sizer_main.Add(sizer_font, 1, wx.EXPAND, 0)
        sizer_main.Add(self.notebook, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        self.Layout()
        self.Centre()

    def update_label(self):
        try:
            self.label_fonttest.SetFont(self.node.wxfont)
        except AttributeError:
            pass
        mystyle = self.label_fonttest.GetWindowStyle()
        mystyle1 = wx.ALIGN_LEFT
        mystyle2 = wx.ST_ELLIPSIZE_END
        if self.node.anchor is None:
            self.node.anchor = "start"
        # try:
        #     size = self.node.wxfont.GetFractionalPointSize()
        # except AttributeError:
        #     size = self.node.wxfont.GetPointSize()
        # print (f"Anchor: {self.node.anchor}, fontsize={size}")
        new_anchor = 0
        # Align the text to the left.
        mystyle1 = wx.ALIGN_LEFT
        mystyle2 = wx.ST_ELLIPSIZE_END
        if self.node.anchor == "middle":
            new_anchor = 1
            mystyle1 = wx.ALIGN_CENTER
            mystyle2 = wx.ST_ELLIPSIZE_MIDDLE
        elif self.node.anchor == "end":
            new_anchor = 2
            mystyle1 = wx.ALIGN_RIGHT
            mystyle2 = wx.ST_ELLIPSIZE_START
        # Clear old alignment...
        mystyle = mystyle & ~wx.ALIGN_LEFT
        mystyle = mystyle & ~wx.ALIGN_RIGHT
        mystyle = mystyle & ~wx.ALIGN_CENTER
        mystyle = mystyle & ~wx.ST_ELLIPSIZE_END
        mystyle = mystyle & ~wx.ST_ELLIPSIZE_MIDDLE
        mystyle = mystyle & ~wx.ST_ELLIPSIZE_START
        # Set new one
        mystyle = mystyle | mystyle1 | mystyle2
        self.label_fonttest.SetWindowStyle(mystyle)

        self.rb_align.SetSelection(new_anchor)
        display_string = self.node.text
        if self.check_variable.GetValue():
            display_string = self.context.elements.wordlist_translate(
                display_string,
                self.node,
                increment=False,
            )
        self.label_fonttest.SetLabelText(display_string)
        self.label_fonttest.SetForegroundColour(wx.Colour(swizzlecolor(self.node.fill)))
        self.label_fonttest.Refresh()

        self.button_attrib_bold.SetValue(self.node.weight > 600)
        self.button_attrib_italic.SetValue(self.node.font_style != "normal")
        self.button_attrib_underline.SetValue(self.node.underline)
        self.button_attrib_strikethrough.SetValue(self.node.strikethrough)
        try:
            self.combo_font.SetValue(self.node.wxfont.GetFaceName())
        except AttributeError:
            pass

    def font_callback(self, forecolor, newfont):
        self.node.wxfont = newfont
        self.node.fill = Color(swizzlecolor(forecolor))
        wxfont_to_svg(self.node)
        self.update_label()
        self.refresh()

    def refresh(self):
        self.renderer.measure_text(self.node)
        bb = self.node.bounds
        self.context.elements.signal("element_property_reload", self.node)
        self.context.signal("refresh_scene", "Scene")

    def on_button_smaller(self, event):
        try:
            size = self.node.wxfont.GetFractionalPointSize()
        except AttributeError:
            size = self.node.wxfont.GetPointSize()

        size = size / 1.2
        if size < 4:
            size = 4
        try:
            self.node.wxfont.SetFractionalPointSize(size)
        except AttributeError:
            self.node.wxfont.SetPointSize(int(size))

        wxfont_to_svg(self.node)
        self.update_label()
        self.refresh()

    def on_button_larger(self, event):
        try:
            size = self.node.wxfont.GetFractionalPointSize()
        except AttributeError:
            size = self.node.wxfont.GetPointSize()
        size *= 1.2

        try:
            self.node.wxfont.SetFractionalPointSize(size)
        except AttributeError:
            self.node.wxfont.SetPointSize(int(size))

        wxfont_to_svg(self.node)
        self.update_label()
        self.refresh()

    def on_font_choice(self, event):
        lastfont = self.node.wxfont.GetFaceName()
        fface = self.combo_font.GetValue()
        self.node.wxfont.SetFaceName(fface)
        if not self.node.wxfont.IsOk():
            self.node.wxfont.SetFaceName(lastfont)
        wxfont_to_svg(self.node)
        self.update_label()
        self.refresh()

    def on_button_bold(self, event):
        button = event.EventObject
        state = button.GetValue()
        if state:
            try:
                self.node.wxfont.SetNumericWeight(700)
            except AttributeError:
                self.node.wxfont.SetWeight(wx.FONTWEIGHT_BOLD)
        else:
            try:
                self.node.wxfont.SetNumericWeight(400)
            except AttributeError:
                self.node.wxfont.SetWeight(wx.FONTWEIGHT_NORMAL)
        wxfont_to_svg(self.node)
        self.update_label()
        self.refresh()

    def on_button_italic(self, event):
        button = event.EventObject
        state = button.GetValue()
        if state:
            self.node.wxfont.SetStyle(wx.FONTSTYLE_ITALIC)
        else:
            self.node.wxfont.SetStyle(wx.FONTSTYLE_NORMAL)
        wxfont_to_svg(self.node)
        self.update_label()
        self.refresh()

    def on_button_underline(self, event):
        button = event.EventObject
        state = button.GetValue()
        self.node.wxfont.SetUnderlined(state)
        wxfont_to_svg(self.node)
        self.update_label()
        self.refresh()

    def on_button_strikethrough(self, event):
        button = event.EventObject
        state = button.GetValue()
        self.node.wxfont.SetStrikethrough(state)
        wxfont_to_svg(self.node)
        self.update_label()
        self.refresh()

    def on_radio_box(self, event):
        new_anchor = event.GetInt()
        if new_anchor == 0:
            self.node.anchor = "start"
        elif new_anchor == 1:
            self.node.anchor = "middle"
        elif new_anchor == 2:
            self.node.anchor = "end"
        self.node.modified()
        self.update_label()
        self.refresh()

    def on_text_change(self, event):  # wxGlade: TextProperty.<event_handler>
        try:
            self.node.text = self.text_text.GetValue()
            self.node.modified()
            self.update_label()
            self.refresh()
        except AttributeError:
            pass
        event.Skip()

    def on_check_variable(self, event):  # wxGlade: TextProperty.<event_handler>
        self.update_label()
        self.refresh()

    def on_text_enter(self, event):  # wxGlade: TextProperty.<event_handler>
        self.panel_history.store_font_history(self.node.wxfont)
        event.Skip()

    def on_button_choose_font(self, event):  # wxGlade: TextProperty.<event_handler>
        font_data = wx.FontData()
        try:
            font_data.SetInitialFont(self.node.wxfont)
            font_data.SetColour(wx.Colour(swizzlecolor(self.node.fill)))
            dialog = wx.FontDialog(None, font_data)
        except AttributeError:
            dialog = wx.FontDialog(None, font_data)
        if dialog.ShowModal() == wx.ID_OK:
            data = dialog.GetFontData()
            font = data.GetChosenFont()
            try:
                color = data.GetColour()
                rgb = color.GetRGB()
                color = swizzlecolor(rgb)
                color = Color(color, 1.0)
                self.node.fill = color
                # Translate wxFont to SVG font....
                self.node.wxfont = font
                wxfont_to_svg(self.node)
                self.node.modified()
            except AttributeError:  # rgb get failed.
                pass

            self.update_label()
            self.refresh()
        dialog.Destroy()
        event.Skip()

    def callback_color(self):
        self.node.altered()
        self.update_label()
        self.refresh()

    # @signal_listener("textselect")
    # def on_signal_select(self, origin, *args):
    #     try:
    #         self.text_text.SelectAll()
    #         self.text_text.SetFocus()
    #     except RuntimeError:
    #         pass


class TextProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(317, 360, *args, **kwds)

        self.panel = TextPropertyPanel(self, wx.ID_ANY, context=self.context, node=node)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_text_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: TextProperty.__set_properties
        self.SetTitle(_("Text Properties"))

    def restore(self, *args, node=None, **kwds):
        self.panel.set_widgets(node)

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    def window_preserve(self):
        return False

    def window_menu(self):
        return False
