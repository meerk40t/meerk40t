import platform

import wx

from meerk40t.gui.fonts import wxfont_to_svg
from meerk40t.gui.wxutils import ScrolledPanel

from ...svgelements import Color
from ..icons import icons8_choose_font_50, icons8_text_50
from ..laserrender import swizzlecolor
from ..mwindow import MWindow
from .attributes import ColorPanel, IdPanel

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


class TextPropertyPanel(ScrolledPanel):
    def __init__(self, parent, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        super().__init__(parent, *args, **kwds)
        self.context = context

        self.text_text = wx.TextCtrl(self, wx.ID_ANY, "")
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
            self, wx.ID_ANY, icons8_choose_font_50.GetBitmap()
        )
        self.panel_id = IdPanel(self, id=wx.ID_ANY, context=self.context)
        self.panel_stroke = ColorPanel(self, id=wx.ID_ANY, label="Stroke:", attribute="stroke", callback=self.callback_color)
        self.panel_fill = ColorPanel(self, id=wx.ID_ANY, label="Fill:", attribute="fill", callback=self.callback_color)

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

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TEXT, self.on_text_name_change, self.text_text)

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
        if node is not None:
            self.node = node
        try:
            if self.node.text is not None:
                self.text_text.SetValue(self.node.text)
                self.label_fonttest.SetLabelText(self.node.text)
                try:
                    self.label_fonttest.SetFont(self.node.wxfont)
                except AttributeError:
                    pass
        except AttributeError:
            pass

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
            _("Define where to place the origin (i.e. current mouse position")
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
        sizer_anchor.Add(self.rb_align, 0, 0, 0)
        sizer_main.Add(self.text_text, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_attrib, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_anchor, 0, wx.EXPAND, 0)

        sizer_main.Add(self.panel_stroke, 0, wx.EXPAND, 0)
        sizer_main.Add(self.panel_fill, 0, wx.EXPAND, 0)

        sizer_main.Add(sizer_font, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        self.Layout()
        self.Centre()
        # end wxGlade

    def update_label(self):
        try:
            self.label_fonttest.SetFont(self.node.wxfont)
        except AttributeError:
            pass
        mystyle = self.label_fonttest.GetWindowStyle()
        if self.node.anchor == "start":
            new_anchor = 0
            # Align the text to the left.
            mystyle1 = wx.ALIGN_LEFT
            mystyle2 = wx.ST_ELLIPSIZE_END
        elif self.node.anchor == "middle":
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
        self.label_fonttest.SetLabelText(self.node.text)
        self.label_fonttest.SetForegroundColour(wx.Colour(swizzlecolor(self.node.fill)))
        self.label_fonttest.Refresh()

        self.button_attrib_bold.SetValue(self.node.weight > 600)
        self.button_attrib_italic.SetValue(self.node.font_style != "normal")
        self.button_attrib_underline.SetValue(self.node.underline)
        self.button_attrib_strikethrough.SetValue(self.node.strikethrough)
        self.combo_font.SetValue(self.node.wxfont.GetFaceName())

    def refresh(self):
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
        event.Skip()

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
        event.Skip()

    def on_font_choice(self, event):
        lastfont = self.node.wxfont.GetFaceName()
        fface = self.combo_font.GetValue()
        self.node.wxfont.SetFaceName(fface)
        if not self.node.wxfont.IsOk():
            self.node.wxfont.SetFaceName(lastfont)
        wxfont_to_svg(self.node)
        self.update_label()
        self.refresh()
        event.Skip()

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
        event.Skip()

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
        event.Skip()

    def on_button_underline(self, event):
        button = event.EventObject
        state = button.GetValue()
        self.node.wxfont.SetUnderlined(state)
        wxfont_to_svg(self.node)
        self.update_label()
        self.refresh()
        event.Skip()

    def on_button_strikethrough(self, event):
        button = event.EventObject
        state = button.GetValue()
        self.node.wxfont.SetStrikethrough(state)
        wxfont_to_svg(self.node)
        self.update_label()
        self.refresh()
        event.Skip()

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

    def on_text_name_change(self, event):  # wxGlade: TextProperty.<event_handler>
        try:
            self.node.text = self.text_text.GetValue()
            self.node.modified()
            self.update_label()
            self.refresh()
        except AttributeError:
            pass
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
