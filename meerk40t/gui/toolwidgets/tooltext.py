import wx

from meerk40t.gui.fonts import wxfont_to_svg
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Color, SVGText

from ...core.units import UNITS_PER_PIXEL

_ = wx.GetTranslation


class TextEntry(wx.Dialog):
    def __init__(self, context, defaultstring=None, *args, **kwds):
        self.FONTHISTORY = 4
        # begin wxGlade: TextEntry.__init__
        if defaultstring is None:
            defaultstring = ""
        self.context = context
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.SetSize((518, 580))
        self.SetTitle(_("Add a Text-element"))
        self.default_font = wx.Font(
            14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
        )
        self.result_text = ""
        self.result_font = self.default_font
        self.result_colour = wx.BLACK
        self.result_anchor = 0  # 0 = left, 1=center, 2=right

        self.txt_Text = wx.TextCtrl(self, wx.ID_ANY, defaultstring)

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

    def setLayout(self):
        sizer_v_main = wx.BoxSizer(wx.VERTICAL)

        sizer_h_text = wx.BoxSizer(wx.HORIZONTAL)
        sizer_v_main.Add(sizer_h_text, 0, wx.EXPAND, 0)
        label_1 = wx.StaticText(self, wx.ID_ANY, _("Text"))
        sizer_h_text.Add(label_1, 0, 0, 0)
        sizer_h_text.Add(self.txt_Text, 1, 0, 0)
        sizer_h_text.Add(self.btn_choose_font, 0, 0, 0)

        sizer_h_align = wx.BoxSizer(wx.HORIZONTAL)
        sizer_v_main.Add(sizer_h_align, 0, wx.EXPAND, 0)
        label_2 = wx.StaticText(self, wx.ID_ANY, _("Alignment"))
        sizer_h_align.Add(label_2, 0, 0, 0)
        sizer_h_align.Add(self.rb_align, 0, 0, 0)

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

        sizer_h_okcancel.AddButton(self.button_OK)
        sizer_h_okcancel.AddButton(self.button_CANCEL)
        sizer_h_okcancel.Realize()

        self.SetSizer(sizer_v_main)

        self.SetAffirmativeId(self.button_OK.GetId())
        self.SetEscapeId(self.button_CANCEL.GetId())

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


# end of class TextEntry


class TextTool(ToolWidget):
    """
    Text Drawing Tool

    Adds Text at set location.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.x = None
        self.y = None
        self.text = None

    def process_draw(self, gc: wx.GraphicsContext):
        if self.text is not None:
            gc.SetPen(self.pen)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            gc.DrawText(self.text.text, self.x, self.y)

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            self.p1 = complex(space_pos[0], space_pos[1])
            _ = self.scene.context._
            self.text = SVGText("")
            if nearest_snap is None:
                x = space_pos[0]
                y = space_pos[1]
            else:
                x = nearest_snap[0]
                y = nearest_snap[1]
            self.x = x
            self.y = y
            self.text *= f"translate({x}, {y}) scale({UNITS_PER_PIXEL})"
            dlg = TextEntry(self.scene.context, "", None, wx.ID_ANY, "")
            if dlg.ShowModal() == wx.ID_OK:
                self.text.text = dlg.result_text
                if dlg.result_anchor == 1:
                    self.text.anchor = "middle"
                elif dlg.result_anchor == 2:
                    self.text.anchor = "end"
                else:
                    self.text.anchor = "start"
                elements = self.scene.context.elements
                node = elements.elem_branch.add(text=self.text, type="elem text")
                color = dlg.result_colour
                rgb = color.GetRGB()
                color = swizzlecolor(rgb)
                color = Color(color, 1.0)
                node.fill = color
                # Translate wxFont to SVG font....
                node.wxfont = dlg.result_font
                dlg.store_font_history()
                wxfont_to_svg(node)
                if elements.classify_new:
                    elements.classify([node])
                self.notify_created(node)
            dlg.Destroy()
            response = RESPONSE_CONSUME
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.scene.tool_active:
                self.scene.tool_active = False
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
        return response
