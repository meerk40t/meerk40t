import os
import platform
from glob import glob
from math import isinf

import wx

from meerk40t.core.units import UNITS_PER_INCH, Length
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import STD_ICON_SIZE, get_default_icon_size, icons8_choose_font
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import StaticBoxSizer, dip_size

_ = wx.GetTranslation


def remove_fontfile(fontfile):
    if os.path.exists(fontfile):
        try:
            os.remove(fontfile)
            base, ext = os.path.splitext(fontfile)
            bmpfile = base + ".png"
            if os.path.exists(bmpfile):
                os.remove(bmpfile)
        except (OSError, RuntimeError, PermissionError, FileNotFoundError):
            pass


class LineTextPropertyPanel(wx.Panel):
    """
    Panel for post-creation text property editing
    """

    def __init__(
        self,
        *args,
        context=None,
        node=None,
        **kwds,
    ):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.node = node
        self.fonts = []

        main_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Vector-Text"), wx.VERTICAL)

        sizer_text = StaticBoxSizer(self, wx.ID_ANY, _("Content"), wx.HORIZONTAL)
        self.text_text = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE
        )
        sizer_text.Add(self.text_text, 1, wx.EXPAND, 0)

        text_all_options = wx.BoxSizer(wx.HORIZONTAL)

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
        self.rb_align.SetToolTip(_("Textalignment for multi-lines"))
        text_all_options.Add(self.rb_align, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        text_options = StaticBoxSizer(self, wx.ID_ANY, "", wx.HORIZONTAL)
        text_all_options.Add(text_options, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_bigger = wx.Button(self, wx.ID_ANY, "++")
        self.btn_bigger.SetToolTip(_("Increase the font-size"))
        text_options.Add(self.btn_bigger, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_smaller = wx.Button(self, wx.ID_ANY, "--")
        self.btn_smaller.SetToolTip(_("Decrease the font-size"))
        text_options.Add(self.btn_smaller, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        text_options.AddSpacer(25)

        msg = (
            "\n"
            + _("- Hold shift/ctrl-Key down for bigger change")
            + "\n"
            + _("- Right click will reset value to default")
        )

        self.btn_bigger_spacing = wx.Button(self, wx.ID_ANY, "+")
        self.btn_bigger_spacing.SetToolTip(_("Increase the character-gap") + msg)
        text_options.Add(self.btn_bigger_spacing, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_smaller_spacing = wx.Button(self, wx.ID_ANY, "-")
        self.btn_smaller_spacing.SetToolTip(_("Decrease the character-gap") + msg)
        text_options.Add(self.btn_smaller_spacing, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        text_options.AddSpacer(25)

        self.btn_attrib_lineplus = wx.Button(self, id=wx.ID_ANY, label="v")
        self.btn_attrib_lineminus = wx.Button(self, id=wx.ID_ANY, label="^")
        text_options.Add(self.btn_attrib_lineplus, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        text_options.Add(self.btn_attrib_lineminus, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_attrib_lineplus.SetToolTip(_("Increase line distance") + msg)
        self.btn_attrib_lineminus.SetToolTip(_("Reduce line distance") + msg)
        self.check_weld = wx.CheckBox(self, wx.ID_ANY, "")
        self.check_weld.SetToolTip(_("Weld overlapping characters together?"))
        text_options.AddSpacer(25)
        text_options.Add(self.check_weld, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        for btn in (
            self.btn_bigger,
            self.btn_smaller,
            self.btn_bigger_spacing,
            self.btn_smaller_spacing,
            self.btn_attrib_lineminus,
            self.btn_attrib_lineplus,
        ):
            btn.SetMinSize(dip_size(self, 35, 35))

        sizer_fonts = StaticBoxSizer(
            self, wx.ID_ANY, _("Fonts (double-click to use)"), wx.VERTICAL
        )

        self.list_fonts = wx.ListBox(self, wx.ID_ANY)
        self.list_fonts.SetMinSize(dip_size(self, -1, 140))
        self.list_fonts.SetToolTip(
            _("Select to preview the font, double-click to apply it")
        )
        sizer_fonts.Add(self.list_fonts, 0, wx.EXPAND, 0)

        self.bmp_preview = wx.StaticBitmap(self, wx.ID_ANY)
        self.bmp_preview.SetMinSize(dip_size(self, -1, 50))
        sizer_fonts.Add(self.bmp_preview, 0, wx.EXPAND, 0)

        main_sizer.Add(sizer_text, 0, wx.EXPAND, 0)
        main_sizer.Add(text_all_options, 0, wx.EXPAND, 0)
        main_sizer.Add(sizer_fonts, 0, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()
        self.btn_bigger.Bind(wx.EVT_BUTTON, self.on_button_bigger)
        self.btn_smaller.Bind(wx.EVT_BUTTON, self.on_button_smaller)

        self.btn_bigger_spacing.Bind(wx.EVT_BUTTON, self.on_button_bigger_spacing)
        self.btn_smaller_spacing.Bind(wx.EVT_BUTTON, self.on_button_smaller_spacing)
        self.btn_bigger_spacing.Bind(wx.EVT_RIGHT_DOWN, self.on_button_reset_spacing)
        self.btn_smaller_spacing.Bind(wx.EVT_RIGHT_DOWN, self.on_button_reset_spacing)
        self.Bind(wx.EVT_BUTTON, self.on_linegap_bigger, self.btn_attrib_lineplus)
        self.Bind(wx.EVT_BUTTON, self.on_linegap_smaller, self.btn_attrib_lineminus)
        self.btn_attrib_lineplus.Bind(wx.EVT_RIGHT_DOWN, self.on_linegap_reset)
        self.btn_attrib_lineminus.Bind(wx.EVT_RIGHT_DOWN, self.on_linegap_reset)
        self.check_weld.Bind(wx.EVT_CHECKBOX, self.on_weld)
        self.rb_align.Bind(wx.EVT_RADIOBOX, self.on_radio_box)

        self.text_text.Bind(wx.EVT_TEXT, self.on_text_change)
        self.list_fonts.Bind(wx.EVT_LISTBOX, self.on_list_font)
        self.list_fonts.Bind(wx.EVT_LISTBOX_DCLICK, self.on_list_font_dclick)
        self.set_widgets(self.node)

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def accepts(self, node):
        if (
            hasattr(node, "mkfont")
            and hasattr(node, "mkfontsize")
            and hasattr(node, "mktext")
        ):
            # Let's take the opportunity to check for incorrect types and fix them...
            self.context.fonts.validate_node(node)
            return True
        else:
            return False

    def set_widgets(self, node):
        self.node = node
        # print(f"set_widget for {self.attribute} to {str(node)}")
        if self.node is None or not self.accepts(node):
            self.Hide()
            return
        if not hasattr(self.node, "mkfontspacing") or self.node.mkfontspacing is None:
            self.node.mkfontspacing = 1.0
        if not hasattr(self.node, "mklinegap") or self.node.mklinegap is None:
            self.node.mklinegap = 1.1
        if not hasattr(self.node, "mkfontweld") or self.node.mkfontweld is None:
            self.node.mkfontweld = False
        self.check_weld.SetValue(self.node.mkfontweld)
        if not hasattr(self.node, "mkalign") or self.node.mkalign is None:
            self.node.mkalign = "start"
        vals = ("start", "middle", "end")
        try:
            idx = vals.index(self.node.mkalign)
        except IndexError:
            idx = 0
        self.rb_align.SetSelection(idx)

        self.load_directory()
        self.text_text.SetValue(str(node.mktext))
        self.Show()

    def load_directory(self):
        self.list_fonts.Clear()
        self.fonts = self.context.fonts.available_fonts()
        font_desc = [e[1] for e in self.fonts]
        self.list_fonts.SetItems(font_desc)
        # index = -1
        # lookfor = getattr(self.context, "sxh_preferred", "")

    def update_node(self):
        vtext = self.text_text.GetValue()
        self.context.fonts.update_linetext(self.node, vtext)
        self.context.signal("element_property_reload", self.node)
        self.context.signal("refresh_scene", "Scene")

    def on_linegap_reset(self, event):
        if self.node is None:
            return
        self.node.mklinegap = 1.1
        self.update_node()

    def on_linegap_bigger(self, event):
        if self.node is None:
            return
        gap = 0.01
        if wx.GetKeyState(wx.WXK_SHIFT):
            gap = 0.1
        if wx.GetKeyState(wx.WXK_CONTROL):
            gap = 0.25
        if self.node.mklinegap is None:
            self.node.mklinegap = 1.1
        else:
            self.node.mklinegap += gap
        self.update_node()

    def on_linegap_smaller(self, event):
        if self.node is None:
            return
        gap = 0.01
        if wx.GetKeyState(wx.WXK_SHIFT):
            gap = 0.1
        if wx.GetKeyState(wx.WXK_CONTROL):
            gap = 0.25
        if self.node.mklinegap is None:
            self.node.mklinegap = 1.1
        else:
            self.node.mklinegap -= gap
        if self.node.mklinegap < 0:
            self.node.mklinegap = 0
        self.update_node()

    def on_radio_box(self, event):
        new_anchor = event.GetInt()
        if new_anchor == 0:
            self.node.mkalign = "start"
        elif new_anchor == 1:
            self.node.mkalign = "middle"
        elif new_anchor == 2:
            self.node.mkalign = "end"
        self.update_node()

    def on_weld(self, event):
        if self.node is None:
            return
        self.node.mkfontweld = self.check_weld.GetValue()
        self.update_node()

    def on_button_bigger(self, event):
        if self.node is None:
            return
        self.node.mkfontsize *= 1.2
        self.update_node()

    def on_button_smaller(self, event):
        if self.node is None:
            return
        self.node.mkfontsize /= 1.2
        self.update_node()

    def on_button_reset_spacing(self, event):
        # print ("Reset")
        self.node.mkfontspacing = 1.0
        self.update_node()

    def on_button_bigger_spacing(self, event):
        if self.node is None:
            return
        gap = 0.01
        if wx.GetKeyState(wx.WXK_SHIFT):
            gap = 0.1
        if wx.GetKeyState(wx.WXK_CONTROL):
            gap = 0.25
        self.node.mkfontspacing += gap
        self.update_node()

    def on_button_smaller_spacing(self, event):
        if self.node is None:
            return
        gap = 0.01
        if wx.GetKeyState(wx.WXK_SHIFT):
            gap = 0.1
        if wx.GetKeyState(wx.WXK_CONTROL):
            gap = 0.25
        self.node.mkfontspacing -= gap
        self.update_node()

    def on_text_change(self, event):
        self.update_node()

    def on_list_font_dclick(self, event):
        if self.node is None:
            return
        index = self.list_fonts.GetSelection()
        if index >= 0:
            fontinfo = self.fonts[index]
            fontname = os.path.basename(fontinfo[0])
            self.node.mkfont = fontname
            self.update_node()

    def on_list_font(self, event):
        if self.list_fonts.GetSelection() >= 0:
            font_info = self.fonts[self.list_fonts.GetSelection()]
            full_font_file = font_info[0]
            bmp = self.context.fonts.preview_file(full_font_file)
            # if bmp is not None:
            #     bmap_bundle = wx.BitmapBundle().FromBitmap(bmp)
            # else:
            #     bmap_bundle = wx.BitmapBundle()
            # self.bmp_preview.SetBitmap(bmap_bundle)
            if bmp is None:
                bmp = wx.NullBitmap
            self.bmp_preview.SetBitmap(bmp)


class PanelFontSelect(wx.Panel):
    """
    Panel to select font during line text creation
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        mainsizer = wx.BoxSizer(wx.VERTICAL)

        self.all_fonts = []
        self.fonts = []
        self.font_checks = {}

        fontinfo = self.context.fonts.fonts_registered
        sizer_checker = wx.BoxSizer(wx.HORIZONTAL)
        for extension in fontinfo:
            info = fontinfo[extension]
            checker = wx.CheckBox(self, wx.ID_ANY, info[0])
            checker.SetValue(True)
            checker.Bind(wx.EVT_CHECKBOX, self.on_checker(extension))
            checker.SetToolTip(
                _("Show/Hide all fonts of type {info[0]}").format(info=info)
            )
            self.font_checks[extension] = [checker, True]
            sizer_checker.Add(checker, 0, 0, wx.ALIGN_CENTER_VERTICAL)

        sizer_fonts = StaticBoxSizer(
            self, wx.ID_ANY, _("Fonts (double-click to use)"), wx.VERTICAL
        )
        mainsizer.Add(sizer_fonts, 1, wx.EXPAND, 0)

        self.list_fonts = wx.ListBox(self, wx.ID_ANY)
        self.list_fonts.SetToolTip(
            _("Select to preview the font, double-click to apply it")
        )
        sizer_fonts.Add(self.list_fonts, 1, wx.EXPAND, 0)
        sizer_fonts.Add(sizer_checker, 0, wx.EXPAND, 0)

        self.bmp_preview = wx.StaticBitmap(self, wx.ID_ANY)
        self.bmp_preview.SetMinSize(dip_size(self, -1, 70))
        sizer_fonts.Add(self.bmp_preview, 0, wx.EXPAND, 0)

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_fonts.Add(sizer_buttons, 0, wx.EXPAND, 0)

        self.btn_bigger = wx.Button(self, wx.ID_ANY, "++")
        self.btn_bigger.SetToolTip(_("Increase the font-size"))
        sizer_buttons.Add(self.btn_bigger, 0, wx.EXPAND, 0)

        self.btn_smaller = wx.Button(self, wx.ID_ANY, "--")
        self.btn_smaller.SetToolTip(_("Decrease the font-size"))
        sizer_buttons.Add(self.btn_smaller, 0, wx.EXPAND, 0)

        lbl_spacer = wx.StaticText(self, wx.ID_ANY, "")
        sizer_buttons.Add(lbl_spacer, 1, 0, 0)

        self.SetSizer(mainsizer)

        self.Layout()

        self.Bind(wx.EVT_LISTBOX, self.on_list_font, self.list_fonts)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_list_font_dclick, self.list_fonts)
        self.Bind(wx.EVT_BUTTON, self.on_btn_bigger, self.btn_bigger)
        self.Bind(wx.EVT_BUTTON, self.on_btn_smaller, self.btn_smaller)

        # end wxGlade
        self.load_directory()

    def load_directory(self):
        self.all_fonts = self.context.fonts.available_fonts()
        self.list_fonts.Clear()
        self.populate_list_box()

    def populate_list_box(self):
        self.fonts.clear()
        font_desc = []
        for entry in self.all_fonts:
            # 0 basename, 1 full_path, 2 facename
            parts = os.path.splitext(entry[0])
            if len(parts) > 1:
                extension = parts[1][1:].lower()
                if extension in self.font_checks:
                    if not self.font_checks[extension][1]:
                        entry = None
            if entry is not None:
                self.fonts.append(entry[0])
                font_desc.append(entry[1])

        self.list_fonts.SetItems(font_desc)

    def on_checker(self, extension):
        def handler(event):
            self.font_checks[extension][1] = not self.font_checks[extension][1]
            # Reload List
            self.populate_list_box()

        return handler

    def on_btn_bigger(self, event):
        self.context.signal("linetext", "bigger")

    def on_btn_smaller(self, event):
        self.context.signal("linetext", "smaller")

    def on_list_font_dclick(self, event):
        index = self.list_fonts.GetSelection()
        if index >= 0:
            fontname = self.fonts[index]
            self.context.signal("linetext", "font", fontname)

    def on_list_font(self, event):
        if self.list_fonts.GetSelection() >= 0:
            full_font_file = self.fonts[self.list_fonts.GetSelection()]
            bmp = self.context.fonts.preview_file(full_font_file)
            # if bmp is not None:
            #     bmap_bundle = wx.BitmapBundle().FromBitmap(bmp)
            # else:
            #     bmap_bundle = wx.BitmapBundle()
            # self.bmp_preview.SetBitmap(bmap_bundle)
            if bmp is None:
                bmp = wx.NullBitmap
            self.bmp_preview.SetBitmap(bmp)


class HersheyFontSelector(MWindow):
    """
    Wrapper Window Class for font selection panel
    """

    def __init__(self, *args, **kwds):
        super().__init__(450, 550, submenu="", *args, **kwds)
        self.panel = PanelFontSelect(self, wx.ID_ANY, context=self.context)
        self.sizer.Add(self.panel, 1, wx.EXPAND, 0)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(
            icons8_choose_font.GetBitmap(resize=0.5 * get_default_icon_size())
        )
        # _icon.CopyFromBitmap(icons8_computer_support.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Font-Selection"))
        self.restore_aspect()

    def window_open(self):
        pass

    def window_close(self):
        pass

    def delegates(self):
        yield self.panel

    @staticmethod
    def submenu():
        # Suppress = True
        return "", "Font-Selector", True


class PanelFontManager(wx.Panel):
    """
    Vector Font Manager
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.SetHelpText("vectortext")

        mainsizer = wx.BoxSizer(wx.VERTICAL)

        self.font_infos = []

        self.text_info = wx.TextCtrl(
            self,
            wx.ID_ANY,
            _(
                "MeerK40t can use True-Type-Fonts, Hershey-Fonts or Autocad-86 shape fonts designed to be rendered purely with vectors.\n"
                + "They can be scaled, burned like any other vector shape and are therefore very versatile.\n"
                + "See more: https://en.wikipedia.org/wiki/Hershey_fonts "
            ),
            style=wx.BORDER_NONE | wx.TE_MULTILINE | wx.TE_READONLY,
        )

        self.text_info.SetMinSize(dip_size(self, -1, 90))
        self.text_info.SetBackgroundColour(self.GetBackgroundColour())
        sizer_info = StaticBoxSizer(self, wx.ID_ANY, _("Information"), wx.HORIZONTAL)
        mainsizer.Add(sizer_info, 0, wx.EXPAND, 0)
        sizer_info.Add(self.text_info, 1, wx.EXPAND, 0)

        sizer_directory = StaticBoxSizer(
            self, wx.ID_ANY, _("Font-Work-Directory"), wx.HORIZONTAL
        )
        mainsizer.Add(sizer_directory, 0, wx.EXPAND, 0)

        self.text_fontdir = wx.TextCtrl(self, wx.ID_ANY, "")
        sizer_directory.Add(self.text_fontdir, 1, wx.EXPAND, 0)
        self.text_fontdir.SetToolTip(_("Additional directory for userdefined fonts (also used to store some cache files)"))

        self.btn_dirselect = wx.Button(self, wx.ID_ANY, "...")
        sizer_directory.Add(self.btn_dirselect, 0, wx.EXPAND, 0)

        choices = []
        prechoices = context.lookup("choices/preferences")
        for info in prechoices:
            if info["attr"] == "system_font_directories":
                cinfo = dict(info)
                cinfo["page"]=""
                choices.append(cinfo)
                break

        self.sysdirs = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=choices, scrolling=False
        )
        mainsizer.Add(self.sysdirs, 0, wx.EXPAND, 0)
        sizer_fonts = StaticBoxSizer(self, wx.ID_ANY, _("Fonts"), wx.VERTICAL)
        mainsizer.Add(sizer_fonts, 1, wx.EXPAND, 0)

        self.list_fonts = wx.ListBox(self, wx.ID_ANY)
        sizer_fonts.Add(self.list_fonts, 1, wx.EXPAND, 0)

        self.bmp_preview = wx.StaticBitmap(self, wx.ID_ANY)
        self.bmp_preview.SetMinSize(dip_size(self, -1, 70))
        sizer_fonts.Add(self.bmp_preview, 0, wx.EXPAND, 0)

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_fonts.Add(sizer_buttons, 0, wx.EXPAND, 0)

        self.btn_add = wx.Button(self, wx.ID_ANY, _("Import"))
        sizer_buttons.Add(self.btn_add, 0, wx.EXPAND, 0)

        self.btn_delete = wx.Button(self, wx.ID_ANY, _("Delete"))
        sizer_buttons.Add(self.btn_delete, 0, wx.EXPAND, 0)

        lbl_spacer = wx.StaticText(self, wx.ID_ANY, "")
        sizer_buttons.Add(lbl_spacer, 1, 0, 0)

        self.btn_refresh = wx.Button(self, wx.ID_ANY, _("Refresh"))
        sizer_buttons.Add(self.btn_refresh, 0, wx.EXPAND, 0)

        self.webresources = [
            "https://github.com/kamalmostafa/hershey-fonts/tree/master/hershey-fonts",
            "http://iki.fi/sol/hershey/index.html",
            "https://www.mepwork.com/2017/11/autocad-shx-fonts.html",
        ]
        choices = [
            _("Goto a font-source..."),
            _("Hershey Fonts - #1"),
            _("Hershey Fonts - #2"),
            _("Autocad-SHX-Fonts"),
        ]
        self.combo_webget = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_webget.SetSelection(0)
        sizer_buttons.Add(self.combo_webget, 0, wx.EXPAND, 0)

        self.SetSizer(mainsizer)
        self.Layout()
        mainsizer.Fit(self)

        self.Bind(wx.EVT_TEXT, self.on_text_directory, self.text_fontdir)
        self.Bind(wx.EVT_BUTTON, self.on_btn_directory, self.btn_dirselect)
        self.Bind(wx.EVT_LISTBOX, self.on_list_font, self.list_fonts)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_list_font_dclick, self.list_fonts)
        self.Bind(wx.EVT_BUTTON, self.on_btn_import, self.btn_add)
        self.Bind(wx.EVT_BUTTON, self.on_btn_delete, self.btn_delete)
        self.Bind(wx.EVT_BUTTON, self.on_btn_refresh, self.btn_refresh)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_webget, self.combo_webget)
        self.list_fonts.Bind(wx.EVT_MOTION, self.on_list_hover)
        # end wxGlade
        fontdir = self.context.fonts.font_directory
        self.text_fontdir.SetValue(fontdir)

    def on_text_directory(self, event):
        fontdir = self.text_fontdir.GetValue()
        self.font_infos.clear()
        font_desc = []
        self.list_fonts.Clear()
        if os.path.exists(fontdir):
            self.context.fonts.font_directory = fontdir
            self.text_fontdir.SetBackgroundColour(wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW))
            self.text_fontdir.SetToolTip(_("Additional directory for userdefined fonts (also used to store some cache files)"))
        else:
            self.text_fontdir.SetBackgroundColour(wx.SystemSettings().GetColour(wx.SYS_COLOUR_HIGHLIGHT))
            self.text_fontdir.SetToolTip(_("Invalid directory! Will not be used, please provide a valid path."))
            return
            # resp = wx.MessageBox(_("This is an invalid directory, do you want to use the default directory?"),_("Invalid directory"), style=wx.YES_NO|wx.ICON_WARNING)
            # if resp==wx.YES:
            #     fontdir = self.context.fonts.font_directory
            #     self.text_fontdir.SetValue(fontdir)
            # else:
            #     return
        self.font_infos = self.context.fonts.available_fonts()

        for info in self.font_infos:
            font_desc.append(info[1])
        self.list_fonts.SetItems(font_desc)
        # Let the world know we have fonts
        self.context.signal("icons")

    def on_btn_directory(self, event):
        fontdir = self.text_fontdir.GetValue()
        dlg = wx.DirDialog(
            None,
            _("Choose font directory"),
            fontdir,
            style=wx.DD_DEFAULT_STYLE
            # | wx.DD_DIR_MUST_EXIST
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.text_fontdir.SetValue(dlg.GetPath())
        # Only destroy a dialog after you're done with it.
        dlg.Destroy()

    def on_list_font_dclick(self, event):
        if self.list_fonts.GetSelection() >= 0:
            font_file = self.font_infos[self.list_fonts.GetSelection()][0]
            self.context.setting(str, "last_font", None)
            self.context.last_font = font_file

    def on_list_font(self, event):
        if self.list_fonts.GetSelection() >= 0:
            info = self.font_infos[self.list_fonts.GetSelection()]
            full_font_file = info[0]
            is_system = info[4]
            self.btn_delete.Enable(not is_system)
            bmp = self.context.fonts.preview_file(full_font_file)
            # if bmp is not None:
            #     bmap_bundle = wx.BitmapBundle().FromBitmap(bmp)
            # else:
            #     bmap_bundle = wx.BitmapBundle()
            # self.bmp_preview.SetBitmap(bmap_bundle)
            if bmp is None:
                bmp = wx.NullBitmap
            self.bmp_preview.SetBitmap(bmp)
    
    def on_list_hover(self, event):
        event.Skip()
        pt = event.GetPosition()
        item = self.list_fonts.HitTest(pt)
        ttip = _("List of available fonts")
        if item >= 0:
            try:
                info = self.font_infos[item]
                ttip = f"{info[1]}\nFamily: {info[2]}\nSubfamily: {info[3]}\n{info[0]}"
            except IndexError:
                pass
        self.list_fonts.SetToolTip(ttip)

    def on_btn_import(self, event, defaultdirectory=None, defaultextension=None):
        fontinfo = self.context.fonts.fonts_registered
        wildcard = "Vector-Fonts"
        idx = 0
        filterindex = 0
        # 1st put all into one wildcard-pattern
        for extension in fontinfo:
            ext = "*." + extension
            if idx == 0:
                wildcard += "|"
            else:
                wildcard += ";"
            wildcard += ext.lower() + ";" + ext.upper()
            idx += 1
        # 2nd add all individual wildcard-patterns
        for idx, extension in enumerate(fontinfo):
            if (
                defaultextension is not None
                and defaultextension.lower() == extension.lower()
            ):
                filterindex = idx + 1
            ext = "*." + extension
            info = fontinfo[extension]
            wildcard += f"|{info[0]}-Fonts|{ext.lower()};{ext.upper()}"
        wildcard += "|" + _("All files") + "|*.*"
        if defaultdirectory is None:
            defdir = ""
        else:
            defdir = defaultdirectory
            # print (os.listdir(os.path.join(os.environ['WINDIR'],'fonts')))
        dlg = wx.FileDialog(
            self,
            message=_(
                "Select a font-file to be imported into the the font-directory {fontdir}"
            ).format(fontdir=self.context.fonts.font_directory),
            defaultDir=defdir,
            defaultFile="",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE | wx.FD_PREVIEW
            #            | wx.FD_SHOW_HIDDEN,
        )
        try:
            # Might not be present in early wxpython versions
            dlg.SetFilterIndex(filterindex)
        except AttributeError:
            pass
        font_files = None
        paths = None
        if dlg.ShowModal() == wx.ID_OK:
            font_files = dlg.GetPaths()
        # Only destroy a dialog after you're done with it.
        dlg.Destroy()
        stats = [0, 0]  # Successful, errors
        if font_files is None:
            return

        maxidx = len(font_files)
        progress_string = _("Fonts imported: {count}")
        progress = wx.ProgressDialog(
            _("Importing fonts..."),
            progress_string.format(count=0),
            maximum=maxidx,
            parent=None,
            style=wx.PD_APP_MODAL | wx.PD_CAN_ABORT,
        )
        for idx, sourcefile in enumerate(font_files):
            basename = os.path.basename(sourcefile)
            destfile = os.path.join(self.context.fonts.font_directory, basename)
            # print (f"Source File: {sourcefile}\nTarget: {destfile}")
            try:
                with open(sourcefile, "rb") as f, open(destfile, "wb") as g:
                    while True:
                        block = f.read(1 * 1024 * 1024)  # work by blocks of 1 MB
                        if not block:  # end of file
                            break
                        g.write(block)
                bmp = self.context.fonts.preview_file(destfile)
                if bmp is not None:
                    stats[0] += 1
                else:
                    # We delete this file again...
                    remove_fontfile(destfile)
                    stats[1] += 1

                keepgoing = progress.Update(
                    idx + 1, progress_string.format(count=idx + 1)
                )
                if progress.WasCancelled():
                    break
            except (OSError, RuntimeError, PermissionError, FileNotFoundError):
                stats[1] += 1
        progress.Destroy()
        wx.MessageBox(
            _(
                "Font-Import completed.\nImported: {ok}\nFailed: {fail}\nTotal: {total}"
            ).format(ok=stats[0], fail=stats[1], total=stats[0] + stats[1]),
            _("Import completed"),
            wx.OK | wx.ICON_INFORMATION,
        )
        # Reload....
        self.on_text_directory(None)

    def on_btn_refresh(self, event):
        self.context.fonts.reset_cache()
        self.on_text_directory(None)

    def on_btn_delete(self, event):
        if self.list_fonts.GetSelection() >= 0:
            info = self.font_infos[self.list_fonts.GetSelection()]
            full_font_file = info[0]
            font_file = os.path.basename(full_font_file)
            if self.context.fonts.is_system_font(full_font_file):
                return
            if (
                wx.MessageBox(
                    _("Do you really want to delete this font: {font}").format(
                        font=font_file
                    ),
                    _("Confirm"),
                    wx.YES_NO | wx.CANCEL | wx.ICON_WARNING,
                )
                == wx.YES
            ):
                remove_fontfile(full_font_file)
                # Reload dir...
                self.on_text_directory(None)

    def on_combo_webget(self, event):
        idx = self.combo_webget.GetSelection() - 1
        if idx >= 0:
            url = self.webresources[idx]
            if url.startswith("http"):
                if (
                    wx.MessageBox(
                        _(
                            "You will be led now to a source in the web, where you can download free fonts.\n"
                            + "Please respect individual property rights!\nDestination: {url}\n"
                        ).format(url=url)
                        + _(
                            "Unpack the downloaded archive after the download and select the extracted files with help of the 'Import'-Button."
                        ),
                        _("Confirm"),
                        wx.YES_NO | wx.CANCEL | wx.ICON_INFORMATION,
                    )
                    == wx.YES
                ):
                    import webbrowser

                    webbrowser.open(url, new=0, autoraise=True)
            else:
                # This is a local directory with existing font-files,
                # e.g. the Windows-Font-Directory
                self.import_files(url, "ttf")

    def import_files(self, import_directory, extension):
        source_files = os.listdir(import_directory)
        font_files = []
        for entry in source_files:
            if entry.lower().endswith(extension):
                font_files.append(os.path.join(import_directory, entry))
        stats = [0, 0]  # Successful, errors
        if len(font_files) == 0:
            return

        maxidx = len(font_files)
        progress_string = _("Fonts imported: {count}")
        progress = wx.ProgressDialog(
            _("Importing fonts..."),
            progress_string.format(count=0),
            maximum=maxidx,
            parent=None,
            style=wx.PD_APP_MODAL | wx.PD_CAN_ABORT,
        )
        for idx, sourcefile in enumerate(font_files):
            basename = os.path.basename(sourcefile)
            destfile = os.path.join(self.context.fonts.font_directory, basename)
            if os.path.exists(destfile):
                continue
            # print (f"Source File: {sourcefile}\nTarget: {destfile}")
            try:
                with open(sourcefile, "rb") as f, open(destfile, "wb") as g:
                    while True:
                        block = f.read(1 * 1024 * 1024)  # work by blocks of 1 MB
                        if not block:  # end of file
                            break
                        g.write(block)
                bmp = self.context.fonts.preview_file(destfile)
                if bmp is not None:
                    stats[0] += 1
                else:
                    # We delete this file again...
                    remove_fontfile(destfile)
                    stats[1] += 1

                keepgoing = progress.Update(
                    idx + 1, progress_string.format(count=idx + 1)
                )
                if progress.WasCancelled():
                    break
            except (OSError, RuntimeError, PermissionError, FileNotFoundError):
                stats[1] += 1
        progress.Destroy()
        wx.MessageBox(
            _(
                "Font-Import completed.\nImported: {ok}\nFailed: {fail}\nTotal: {total}"
            ).format(ok=stats[0], fail=stats[1], total=stats[0] + stats[1]),
            _("Import completed"),
            wx.OK | wx.ICON_INFORMATION,
        )
        # Reload....
        self.on_text_directory(None)


# end of class FontManager


class HersheyFontManager(MWindow):
    """
    Wrapper Window Class for Vector Font Manager
    """

    def __init__(self, *args, **kwds):
        super().__init__(551, 234, submenu="", *args, **kwds)
        self.panel = PanelFontManager(self, wx.ID_ANY, context=self.context)
        self.sizer.Add(self.panel, 1, wx.EXPAND, 0)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_choose_font.GetBitmap())
        # _icon.CopyFromBitmap(icons8_computer_support.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Font-Manager"))
        self.Layout()
        self.restore_aspect()

    def window_open(self):
        pass

    def window_close(self):
        pass

    def delegates(self):
        yield self.panel

    @staticmethod
    def submenu():
        # suppress in tool-menu
        return "", "Font-Manager", True


def register_hershey_stuff(kernel):
    kernel.root.register("path_attributes/linetext", LineTextPropertyPanel)
    buttonsize = int(STD_ICON_SIZE)
    kernel.register(
        "button/config/HersheyFontManager",
        {
            "label": _("Font-Manager"),
            "icon": icons8_choose_font,
            "tip": _("Open the vector-font management window."),
            "help": "vectortext",
            "action": lambda v: kernel.console("window toggle HersheyFontManager\n"),
            "size": buttonsize,
        },
    )
