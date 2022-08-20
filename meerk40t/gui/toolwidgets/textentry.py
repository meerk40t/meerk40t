import platform

import wx

from meerk40t.core.units import UNITS_PER_PIXEL
from meerk40t.gui.fonts import wxfont_to_svg
from meerk40t.gui.icons import icons8_type_50
from meerk40t.gui.laserrender import swizzlecolor, LaserRender
from meerk40t.gui.mwindow import MWindow
from meerk40t.svgelements import Color, Matrix

_ = wx.GetTranslation


class TextEntryPanel(wx.Panel):
    def __init__(self, *args, context=None, x=0, y=0, default_string="", **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.parent = args[0]
        self.context = context
        self.x = x
        self.y = y
        self.FONTHISTORY = 4
        # begin wxGlade: TextEntry.__init__
        self.context = context

        self.default_font = wx.Font(
            14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
        )
        self.result_text = ""
        self.result_font = self.default_font
        self.result_colour = wx.BLACK
        self.result_anchor = 0  # 0 = left, 1=center, 2=right

        self.txt_Text = wx.TextCtrl(self, wx.ID_ANY, default_string)

        self.btn_choose_font = wx.Button(self, wx.ID_ANY, _("Select Font"))

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
            _("Define where to place the origin (i.e. current mouse position")
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
        self.button_attrib_smaller.SetToolTip(_("Decrease fontsize"))
        self.button_attrib_larger.SetToolTip(_("Increase fontsize"))
        self.button_attrib_bold.SetToolTip(_("Toggle bold"))
        self.button_attrib_italic.SetToolTip(_("Toggle italic"))
        self.button_attrib_underline.SetToolTip(_("Toggle underline"))
        self.button_attrib_strikethrough.SetToolTip(_("Toggle strikethrough"))
        # populate listbox
        choices = self.context.elements.mywordlist.get_variable_list()
        self.lb_variables = wx.ListBox(self, wx.ID_ANY, choices=choices)
        self.lb_variables.SetToolTip(_("Double click a variable to add it to the text"))

        self.preview = wx.StaticText(
            self,
            wx.ID_ANY,
            _("<Preview>"),
            style=wx.ST_ELLIPSIZE_END | wx.ST_NO_AUTORESIZE,
        )
        self.preview.SetFont(self.default_font)
        self.preview.SetMinSize((-1, 90))
        self.btn_color = []
        bgcolors = (
            0xFFFFFF,
            0x000000,
            0xFF0000,
            0x00FF00,
            0x0000FF,
            0xFFFF00,
            0xFF00FF,
            0x00FFFF,
        )
        for i in range(8):
            self.btn_color.append(wx.Button(self, wx.ID_ANY, ""))
            self.btn_color[i].SetMinSize((10, 23))
            self.btn_color[i].SetBackgroundColour(wx.Colour(bgcolors[i]))

        self.last_font = []
        for i in range(self.FONTHISTORY):
            self.last_font.append(
                wx.StaticText(
                    self,
                    wx.ID_ANY,
                    _("<empty>"),
                    style=wx.ALIGN_CENTER_HORIZONTAL
                    | wx.ST_ELLIPSIZE_END
                    | wx.ST_NO_AUTORESIZE,
                )
            )
            self.last_font[i].SetMinSize((120, 90))
            self.last_font[i].SetFont(self.default_font)
            self.last_font[i].SetToolTip(_("Choose last used font-settings"))

        self.button_OK = wx.Button(self, wx.ID_OK, "")
        self.button_OK.SetDefault()

        self.button_CANCEL = wx.Button(self, wx.ID_CANCEL, "")

        self.load_font_history()

        self.setLayout()

        self.setLogic()
        self.result = 0

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    def setLayout(self):
        sizer_v_main = wx.BoxSizer(wx.VERTICAL)

        sizer_h_text = wx.BoxSizer(wx.HORIZONTAL)
        sizer_v_main.Add(sizer_h_text, 0, wx.EXPAND, 0)
        label_1 = wx.StaticText(self, wx.ID_ANY, _("Text"))
        sizer_h_text.Add(label_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_h_text.Add(self.txt_Text, 1, 0, 0)
        sizer_h_text.Add(self.btn_choose_font, 0, 0, 0)

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

        sizer_h_align = wx.BoxSizer(wx.HORIZONTAL)
        sizer_v_main.Add(sizer_h_align, 0, wx.EXPAND, 0)
        label_2 = wx.StaticText(self, wx.ID_ANY, _("Alignment"))
        sizer_h_align.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_h_align.Add(self.rb_align, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_h_align.Add(self.button_attrib_larger, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_h_align.Add(self.button_attrib_smaller, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_h_align.Add(self.button_attrib_bold, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_h_align.Add(self.button_attrib_italic, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_h_align.Add(self.button_attrib_underline, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_h_align.Add(
            self.button_attrib_strikethrough, 0, wx.ALIGN_CENTER_VERTICAL, 0
        )
        sizer_h_color = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Color")), wx.HORIZONTAL
        )
        sizer_v_main.Add(sizer_h_color, 0, wx.EXPAND, 0)
        for i in range(8):
            sizer_h_color.Add(self.btn_color[i], 1, 0, 0)

        sizer_h_variables = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Available Variables")), wx.HORIZONTAL
        )
        sizer_v_main.Add(sizer_h_variables, 0, wx.EXPAND, 0)
        sizer_h_variables.Add(self.lb_variables, 1, wx.EXPAND, 0)

        sizer_v_main.Add(self.preview, 1, wx.EXPAND, 1)

        sizer_h_fonthistory = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Last Font-Entries")), wx.HORIZONTAL
        )
        sizer_v_main.Add(sizer_h_fonthistory, 0, wx.EXPAND, 0)
        for i in range(self.FONTHISTORY):
            sizer_h_fonthistory.Add(
                self.last_font[i], 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 1
            )

        sizer_h_okcancel = wx.StdDialogButtonSizer()
        sizer_v_main.Add(sizer_h_okcancel, 0, wx.ALIGN_RIGHT | wx.ALL, 4)

        self.button_OK.Enable(len(self.txt_Text.GetValue()) > 0)
        sizer_h_okcancel.AddButton(self.button_OK)
        sizer_h_okcancel.AddButton(self.button_CANCEL)
        sizer_h_okcancel.Realize()

        self.SetSizer(sizer_v_main)

        # self.SetAffirmativeId(self.button_OK.GetId())
        # self.SetEscapeId(self.button_CANCEL.GetId())

        self.Layout()
        self.Centre()

    def setLogic(self):
        self.btn_choose_font.Bind(wx.EVT_BUTTON, self.on_choose_font)
        self.lb_variables.Bind(wx.EVT_LISTBOX_DCLICK, self.on_variable_dclick)
        for i in range(self.FONTHISTORY):
            self.last_font[i].Bind(wx.EVT_LEFT_DOWN, self.on_last_font)
        for i in range(8):
            self.btn_color[i].Bind(wx.EVT_BUTTON, self.on_btn_color)
        self.txt_Text.Bind(wx.EVT_TEXT, self.on_text_change)
        self.rb_align.Bind(wx.EVT_RADIOBOX, self.on_radio_box)

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
        self.Bind(wx.EVT_BUTTON, self.on_button_ok, self.button_OK)
        self.Bind(wx.EVT_BUTTON, self.on_button_cancel, self.button_CANCEL)

    def set_preview_alignment(self):
        mystyle = self.preview.GetWindowStyle()
        if self.result_anchor == 0:
            # Align the text to the left.
            mystyle1 = wx.ALIGN_LEFT
            mystyle2 = wx.ST_ELLIPSIZE_END
        elif self.result_anchor == 1:
            mystyle1 = wx.ALIGN_CENTER
            mystyle2 = wx.ST_ELLIPSIZE_MIDDLE
        else:
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
        self.preview.SetWindowStyle(mystyle)
        self.preview.Refresh()

    def on_radio_box(self, event):
        self.result_anchor = event.GetInt()
        self.set_preview_alignment()

    def on_text_change(self, event):
        svalue = self.context.elements.mywordlist.translate(self.txt_Text.GetValue())
        self.preview.Label = svalue
        for i in range(self.FONTHISTORY):
            self.last_font[i].Label = svalue
        self.result_text = self.txt_Text.GetValue()
        self.button_OK.Enable(len(self.result_text) > 0)
        event.Skip()

    def on_choose_font(self, event):  # wxGlade: TextEntry.<event_handler>
        data = wx.FontData()
        data.EnableEffects(True)
        data.SetColour(self.result_colour)  # set colour
        data.SetInitialFont(self.result_font)

        dlg = wx.FontDialog(self, data)

        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetFontData()
            self.result_font = data.GetChosenFont()
            self.result_colour = data.GetColour()

            self.preview.SetFont(self.result_font)
            self.preview.ForegroundColour = self.result_colour
            self.preview.Refresh()

        dlg.Destroy()
        event.Skip()

    def on_variable_dclick(self, event):
        svalue = event.GetString()
        svalue = svalue[0 : svalue.find(" (")]
        svalue = self.txt_Text.GetValue() + " {" + svalue + "}"
        self.txt_Text.SetValue(svalue.strip(" "))
        event.Skip()

    def on_last_font(self, event):
        obj = event.EventObject
        self.result_colour = obj.GetForegroundColour()
        self.result_font = obj.GetFont()
        self.preview.ForegroundColour = self.result_colour
        self.preview.Font = self.result_font
        self.preview.Refresh()
        event.Skip()

    def on_btn_color(self, event):
        obj = event.EventObject
        self.result_colour = obj.GetBackgroundColour()
        self.preview.ForegroundColour = self.result_colour
        self.preview.Refresh()
        event.Skip()

    def store_font_history(self):
        fontdesc = self.result_font.GetNativeFontInfoDesc()
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

    def on_button_smaller(self, event):
        try:
            size = self.result_font.GetFractionalPointSize()
        except AttributeError:
            size = self.result_font.GetPointSize()

        size = size / 1.2
        if size < 4:
            size = 4
        try:
            self.result_font.SetFractionalPointSize(size)
        except AttributeError:
            self.result_font.SetPointSize(int(size))

        self.preview.Font = self.result_font
        self.preview.Refresh()
        event.Skip()

    def on_button_larger(self, event):
        try:
            size = self.result_font.GetFractionalPointSize()
        except AttributeError:
            size = self.result_font.GetPointSize()
        size *= 1.2

        try:
            self.result_font.SetFractionalPointSize(size)
        except AttributeError:
            self.result_font.SetPointSize(int(size))

        self.preview.Font = self.result_font
        self.preview.Refresh()
        event.Skip()

    # def on_font_choice(self, event):
    #     lastfont = self.result_font.GetFaceName()
    #     fface = self.combo_font.GetValue()
    #     self.result_font.SetFaceName(fface)
    #     if not self.result_font.IsOk():
    #         self.result_font.SetFaceName(lastfont)

    #     self.preview.Font = self.result_font
    #     self.preview.Refresh()
    #     event.Skip()

    def on_button_bold(self, event):
        button = event.EventObject
        state = button.GetValue()
        if state:
            try:
                self.result_font.SetNumericWeight(700)
            except AttributeError:
                self.result_font.SetWeight(wx.FONTWEIGHT_BOLD)
        else:
            try:
                self.result_font.SetNumericWeight(400)
            except AttributeError:
                self.result_font.SetWeight(wx.FONTWEIGHT_NORMAL)
        self.preview.Font = self.result_font
        self.preview.Refresh()
        event.Skip()

    def on_button_italic(self, event):
        button = event.EventObject
        state = button.GetValue()
        if state:
            self.result_font.SetStyle(wx.FONTSTYLE_ITALIC)
        else:
            self.result_font.SetStyle(wx.FONTSTYLE_NORMAL)
        self.preview.Font = self.result_font
        self.preview.Refresh()
        event.Skip()

    def on_button_underline(self, event):
        button = event.EventObject
        state = button.GetValue()
        self.result_font.SetUnderlined(state)
        self.preview.Font = self.result_font
        self.preview.Refresh()
        event.Skip()

    def on_button_strikethrough(self, event):
        button = event.EventObject
        state = button.GetValue()
        self.result_font.SetStrikethrough(state)
        self.preview.Font = self.result_font
        self.preview.Refresh()
        event.Skip()

    def on_button_ok(self, event):
        self.result = 1
        self.parent.Close()
        event.Skip()

    def on_button_cancel(self, event):
        self.result = -1
        self.parent.Close()
        event.Skip()


class TextEntry(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(518, 580, *args, **kwds)
        x = 0 if len(args) <= 3 else float(args[3])
        y = 0 if len(args) <= 4 else float(args[4])
        default_string = "" if len(args) <= 5 else " ".join(args[5:])
        self.panel = TextEntryPanel(self, wx.ID_ANY, context=self.context, x=x, y=y, default_string=default_string)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_type_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Add a Text-element"))

    @staticmethod
    def sub_register(kernel):
        # kernel.register(
        #     "button/config/Keymap",
        #     {
        #         "label": _("Keymap"),
        #         "icon": icons8_keyboard_50,
        #         "tip": _("Opens Keymap Window"),
        #         "action": lambda v: kernel.console("window toggle Keymap\n"),
        #     },
        # )
        pass

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()
        if self.panel.result == 1:
            text = self.panel.result_text
            elements = self.context.elements
            if self.panel.result_anchor == 1:
                anchor = "middle"
            elif self.panel.result_anchor == 2:
                anchor = "end"
            else:
                anchor = "start"

            color = self.panel.result_colour
            rgb = color.GetRGB()
            color = swizzlecolor(rgb)
            color = Color(color, 1.0)
            node = elements.elem_branch.add(
                text=text,
                matrix=Matrix(f"translate({self.panel.x}, {self.panel.y}) scale({UNITS_PER_PIXEL})"),
                anchor=anchor,
                fill=color,
                type="elem text",
            )

            # Translate wxFont to SVG font....
            node.wxfont = self.panel.result_font
            wxfont_to_svg(node)
            renderer = LaserRender(self.context)
            renderer.measure_text(node)
            self.panel.store_font_history()
            if elements.classify_new:
                elements.classify([node])
            node.notify_created(node)
