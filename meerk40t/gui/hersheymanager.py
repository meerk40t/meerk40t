import os
import platform
import wx

from meerk40t.core.units import Length
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import (
    STD_ICON_SIZE,
    get_default_icon_size,
    icon_kerning_bigger,
    icon_kerning_smaller,
    icon_linegap_bigger,
    icon_linegap_smaller,
    icon_textalign_center,
    icon_textalign_left,
    icon_textalign_right,
    icon_textsize_down,
    icon_textsize_up,
    icons8_choose_font,
)
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import (
    StaticBoxSizer,
    dip_size,
    wxButton,
    wxCheckBox,
    wxComboBox,
    wxListBox,
    wxListCtrl,
    wxStaticBitmap,
    wxStaticText,
    wxToggleButton,
    TextCtrl,
)
from meerk40t.kernel.kernel import signal_listener
from meerk40t.tools.geomstr import TYPE_ARC, TYPE_CUBIC, TYPE_LINE, TYPE_QUAD, Geomstr

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


class FontGlyphPicker(wx.Dialog):
    """
    Dialog to pick a glyph from the existing set of characters in a font
    """

    def __init__(self, *args, context=None, font=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = (
            kwds.get("style", 0) | wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        wx.Dialog.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.font = font
        self.icon_size = 32
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        self.list_glyphs = wxListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
            context=self.context, list_name="list_glyphpicker"
        )
        self.list_glyphs.AppendColumn("UC", format=wx.LIST_FORMAT_LEFT, width=75)
        self.list_glyphs.AppendColumn("ASCII", format=wx.LIST_FORMAT_LEFT, width=75)
        self.list_glyphs.AppendColumn("Char", format=wx.LIST_FORMAT_LEFT, width=75)
        self.list_glyphs.AppendColumn("Debug", format=wx.LIST_FORMAT_LEFT, width=125)
        self.images = wx.ImageList()
        self.images.Create(width=self.icon_size, height=self.icon_size)
        self.list_glyphs.AssignImageList(self.images, wx.IMAGE_LIST_SMALL)
        self.txt_result = TextCtrl(self, wx.ID_ANY)
        mainsizer.Add(self.list_glyphs, 1, wx.EXPAND, 0)
        mainsizer.Add(self.txt_result, 0, wx.EXPAND, 0)

        self.btn_ok = wxButton(self, wx.ID_OK, _("OK"))
        self.btn_cancel = wxButton(self, wx.ID_CANCEL, _("Cancel"))
        box_sizer = wx.BoxSizer(wx.HORIZONTAL)
        box_sizer.Add(self.btn_ok, 0, 0, 0)
        box_sizer.Add(self.btn_cancel, 0, 0, 0)
        mainsizer.Add(box_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

        self.list_glyphs.Bind(wx.EVT_LEFT_DCLICK, self.on_dbl_click)
        self.SetSizer(mainsizer)
        self.list_glyphs.load_column_widths()
        self.Layout()
        # end wxGlade
        self.load_font()

    def load_font(self):
        def geomstr_to_gcpath(gc, path):
            """
            Takes a Geomstr path and converts it to a GraphicsContext.Graphics path

            This also creates a point list of the relevant nodes and creates a ._cache_edit value to be used by node
            editing view.
            """
            p = gc.CreatePath()
            pts = list()
            for subpath in path.as_subpaths():
                if len(subpath) == 0:
                    continue
                end = None
                for e in subpath.segments:
                    seg_type = int(e[2].real)
                    start = e[0]
                    if end != start:
                        # Start point does not equal previous end point.
                        p.MoveToPoint(start.real, start.imag)
                    c0 = e[1]
                    c1 = e[3]
                    end = e[4]

                    if seg_type == TYPE_LINE:
                        p.AddLineToPoint(end.real, end.imag)
                        pts.append(start)
                        pts.append(end)
                    elif seg_type == TYPE_QUAD:
                        p.AddQuadCurveToPoint(c0.real, c0.imag, end.real, end.imag)
                        pts.append(c0)
                        pts.append(start)
                        pts.append(end)
                    elif seg_type == TYPE_ARC:
                        radius = Geomstr.arc_radius(None, line=e)
                        center = Geomstr.arc_center(None, line=e)
                        start_t = Geomstr.angle(None, center, start)
                        end_t = Geomstr.angle(None, center, end)
                        p.AddArc(
                            center.real,
                            center.imag,
                            radius,
                            start_t,
                            end_t,
                            clockwise="ccw"
                            != Geomstr.orientation(None, start, c0, end),
                        )
                        pts.append(c0)
                        pts.append(start)
                        pts.append(end)
                    elif seg_type == TYPE_CUBIC:
                        p.AddCurveToPoint(
                            c0.real, c0.imag, c1.real, c1.imag, end.real, end.imag
                        )
                        pts.append(c0)
                        pts.append(c1)
                        pts.append(start)
                        pts.append(end)
                    else:
                        print(f"Unknown seg_type: {seg_type}")
                if subpath.first_point == end:
                    p.CloseSubpath()
            return p

        def prepare_bitmap(geom, final_icon_width, final_icon_height, as_stroke=False):
            edge = 1
            strokewidth = 1
            wincol = self.context.themes.get("win_bg")
            strcol = self.context.themes.get("win_fg")

            spen = wx.Pen()
            sbrush = wx.Brush()
            spen.SetColour(strcol)
            sbrush.SetColour(strcol)
            spen.SetWidth(strokewidth)
            spen.SetCap(wx.CAP_ROUND)
            spen.SetJoin(wx.JOIN_ROUND)

            bmp = wx.Bitmap.FromRGBA(
                final_icon_width,
                final_icon_height,
                wincol.red,
                wincol.blue,
                wincol.green,
                0,
            )
            dc = wx.MemoryDC()
            dc.SelectObject(bmp)
            # dc.SetBackground(self._background)
            # dc.SetBackground(wx.RED_BRUSH)
            # dc.Clear()
            gc = wx.GraphicsContext.Create(dc)
            gc.dc = dc

            gp = geomstr_to_gcpath(gc, geom)
            m_x, m_y, p_w, p_h = gp.Box
            min_x = m_x
            min_y = m_y
            max_x = m_x + p_w
            max_y = m_y + p_h

            path_width = max_x - min_x
            path_height = max_y - min_y

            path_width += 2 * edge
            path_height += 2 * edge

            stroke_buffer = strokewidth
            path_width += 2 * stroke_buffer
            path_height += 2 * stroke_buffer

            scale_x = final_icon_width / path_width
            scale_y = final_icon_height / path_height

            scale = min(scale_x, scale_y)
            width_scaled = int(round(path_width * scale))
            height_scaled = int(round(path_height * scale))

            # print (f"W: {final_icon_width} vs {width_scaled}, {final_icon_height} vs {height_scaled}")
            keep_ratio = True

            if keep_ratio:
                scale_x = min(scale_x, scale_y)
                scale_y = scale_x

            from meerk40t.gui.zmatrix import ZMatrix
            from meerk40t.svgelements import Matrix

            matrix = Matrix()
            matrix.post_translate(
                -min_x
                + edge
                + stroke_buffer
                + (final_icon_width - width_scaled) / 2 / scale_x,
                -min_y
                + edge
                + stroke_buffer
                + (final_icon_height - height_scaled) / 2 / scale_x,
            )
            matrix.post_scale(scale_x, scale_y)
            if scale_y < 0:
                matrix.pre_translate(0, -height_scaled)
            if scale_x < 0:
                matrix.pre_translate(-width_scaled, 0)

            gc = wx.GraphicsContext.Create(dc)
            gc.dc = dc
            gc.SetInterpolationQuality(wx.INTERPOLATION_BEST)
            gc.PushState()
            if not matrix.is_identity():
                gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
            if as_stroke:
                gc.SetPen(spen)
                gc.StrokePath(gp)
            else:
                gc.SetBrush(sbrush)
                gc.FillPath(gp, fillStyle=wx.WINDING_RULE)
            dc.SelectObject(wx.NullBitmap)
            gc.Destroy()
            del gc.dc
            del dc
            return bmp

        def getbitmap(geom, icon_size, as_stroke=False):
            final_icon_height = int(icon_size)
            final_icon_width = int(icon_size)
            if final_icon_height <= 0:
                final_icon_height = 1
            if final_icon_width <= 0:
                final_icon_width = 1
            bmp = prepare_bitmap(
                geom, final_icon_width, final_icon_height, as_stroke=as_stroke
            )
            return bmp

        self.list_glyphs.DeleteAllItems()
        self.images.RemoveAll()
        from meerk40t.extra.hershey import FontPath

        fontfile = self.context.fonts.full_name(self.font)

        cfont = self.context.fonts.cached_fontclass(fontfile)
        if cfont is None:
            return
        as_stroke = getattr(cfont, "STROKE_BASED", False)
        for c in cfont.glyphs:
            if isinstance(c, str):
                if len(c) > 1:
                    # print (f"Strange: {c}, use {idx} instead")
                    continue
                if ord(c) == 65535:
                    continue
                cstr = str(c)
            elif isinstance(c, int):
                if c == 65535:
                    continue
                cstr = chr(c)
            else:
                continue
            hexa = cstr.encode("utf-8")
            item = self.list_glyphs.InsertItem(self.list_glyphs.ItemCount, hexa)
            self.list_glyphs.SetItem(item, 1, str(ord(cstr)))
            self.list_glyphs.SetItem(item, 2, cstr)
            path = FontPath(False)
            try:
                cfont.render(
                    path,
                    cstr,
                    True,
                    12.0,
                    1.0,
                    1.1,
                    "left",
                )
                # path contains now the geometry...
                okay = True
            except Exception as e:
                self.list_glyphs.SetItem(item, 3, str(e))
                okay = False
            # path contains now the geometry...
            if okay:
                geo = path.geometry
                # print (f"Length {geo.index} after rendering: {ord(c)} / '{hexa}'")
                bmp = getbitmap(geo, self.icon_size, as_stroke=as_stroke)
                if bmp is not None:
                    image_index = self.images.Add(bmp)
                    self.list_glyphs.SetItemImage(item, image_index)
                else:
                    self.list_glyphs.SetItem(item, 3, "Could not create bitmap")
        # for idx in range(self.images.GetImageCount()):
        #     bmp = self.images.GetBitmap(idx)
        #     bmp.SaveFile(f"C:\\temp\\bmp_{idx}.png", type=wx.BITMAP_TYPE_PNG)

    def on_dbl_click(self, event):
        # Get the ascii code
        x, y = event.GetPosition()
        row_id, flags = self.list_glyphs.HitTest((x, y))
        if row_id < 0:
            return
        listitem = self.list_glyphs.GetItem(row_id, 1)
        data = listitem.GetText()
        try:
            code = int(data)
        except ValueError:
            return
        content = self.txt_result.GetValue() + chr(code)
        self.txt_result.ChangeValue(content)

    def result(self):
        return self.txt_result.GetValue()


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
        self.context.themes.set_window_colors(self)
        self.context.setting(float, "last_font_size", float(Length("20px")))
        self.context.setting(str, "last_font", "")

        self.node = node
        self.fonts = []

        # We neeed this to avoid a crash under Linux when textselection is called too quickly
        self._islinux = platform.system() == "Linux"

        main_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Vector-Text"), wx.VERTICAL)

        sizer_text = StaticBoxSizer(self, wx.ID_ANY, _("Content"), wx.HORIZONTAL)
        self.text_text = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE
        )
        sizer_text.Add(self.text_text, 1, wx.EXPAND, 0)

        text_options = StaticBoxSizer(self, wx.ID_ANY, "", wx.HORIZONTAL)

        iconsize = dip_size(self, 25, 25)[0]

        align_options = (_("Left"), _("Center"), _("Right"))
        align_icons = (icon_textalign_left, icon_textalign_center, icon_textalign_right)
        self.rb_align = []
        ttip_main = _("Textalignment for multi-lines")
        for ttip_sub, icon in zip(align_options, align_icons):
            btn = wxToggleButton(self, wx.ID_ANY)
            btn.SetToolTip(f"{ttip_main}: {ttip_sub}")
            btn.SetValue(False)
            btn.SetBitmap(icon.GetBitmap(resize=iconsize))
            self.rb_align.append(btn)
            text_options.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        text_options.AddSpacer(25)

        self.btn_bigger = wxButton(self, wx.ID_ANY)
        self.btn_bigger.SetToolTip(_("Increase the font-size"))
        self.btn_bigger.SetBitmap(icon_textsize_up.GetBitmap(resize=iconsize))
        text_options.Add(self.btn_bigger, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_smaller = wxButton(self, wx.ID_ANY)
        self.btn_smaller.SetToolTip(_("Decrease the font-size"))
        self.btn_smaller.SetBitmap(icon_textsize_down.GetBitmap(resize=iconsize))
        text_options.Add(self.btn_smaller, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        text_options.AddSpacer(25)

        msg = (
            "\n"
            + _("- Hold shift/ctrl-Key down for bigger change")
            + "\n"
            + _("- Right click will reset value to default")
        )

        self.btn_bigger_spacing = wxButton(self, wx.ID_ANY)
        self.btn_bigger_spacing.SetToolTip(_("Increase the character-gap") + msg)
        self.btn_bigger_spacing.SetBitmap(
            icon_kerning_bigger.GetBitmap(resize=iconsize)
        )
        text_options.Add(self.btn_bigger_spacing, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_smaller_spacing = wxButton(self, wx.ID_ANY)
        self.btn_smaller_spacing.SetToolTip(_("Decrease the character-gap") + msg)
        self.btn_smaller_spacing.SetBitmap(
            icon_kerning_smaller.GetBitmap(resize=iconsize)
        )
        text_options.Add(self.btn_smaller_spacing, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        text_options.AddSpacer(25)

        self.btn_attrib_lineplus = wxButton(self, id=wx.ID_ANY)
        self.btn_attrib_lineminus = wxButton(self, id=wx.ID_ANY)
        text_options.Add(self.btn_attrib_lineplus, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        text_options.Add(self.btn_attrib_lineminus, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_attrib_lineplus.SetToolTip(_("Increase line distance") + msg)
        self.btn_attrib_lineminus.SetToolTip(_("Reduce line distance") + msg)
        self.btn_attrib_lineplus.SetBitmap(
            icon_linegap_bigger.GetBitmap(resize=iconsize)
        )
        self.btn_attrib_lineminus.SetBitmap(
            icon_linegap_smaller.GetBitmap(resize=iconsize)
        )
        self.check_weld = wxCheckBox(self, wx.ID_ANY, "")
        self.check_weld.SetToolTip(_("Weld overlapping characters together?"))
        text_options.AddSpacer(25)
        text_options.Add(self.check_weld, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        for btn in (
            self.rb_align[0],
            self.rb_align[1],
            self.rb_align[2],
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

        self.list_fonts = wxListBox(self, wx.ID_ANY)
        self.list_fonts.SetMinSize(dip_size(self, -1, 140))
        self.list_fonts.SetToolTip(
            _("Select to preview the font, double-click to apply it")
        )
        sizer_fonts.Add(self.list_fonts, 0, wx.EXPAND, 0)

        self.bmp_preview = wxStaticBitmap(self, wx.ID_ANY)
        self.bmp_preview.SetMinSize(dip_size(self, -1, 50))
        sizer_fonts.Add(self.bmp_preview, 0, wx.EXPAND, 0)

        main_sizer.Add(sizer_text, 0, wx.EXPAND, 0)
        main_sizer.Add(text_options, 0, wx.EXPAND, 0)
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
        for btn in self.rb_align:
            btn.Bind(wx.EVT_TOGGLEBUTTON, self.on_radio_box)
        self.text_text.Bind(wx.EVT_TEXT, self.on_text_change)
        self.text_text.Bind(wx.EVT_RIGHT_DOWN, self.on_context_menu)
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
        for b_idx, btn in enumerate(self.rb_align):
            btn.SetValue(bool(idx == b_idx))

        self.load_directory()
        self.text_text.ChangeValue(str(node.mktext))
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
        self.context.last_font = self.node.mkfont
        self.context.last_font_size = self.node.mkfontsize

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
        evt_btn = event.GetEventObject()
        for idx, btn in enumerate(self.rb_align):
            if btn is evt_btn:
                new_anchor = idx
                btn.SetValue(True)
            else:
                btn.SetValue(False)
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

    def on_context_menu(self, event):
        def on_paste(event):
            self.text_text.Paste()

        def on_glyph(event):
            mydlg = FontGlyphPicker(
                None, id=wx.ID_ANY, context=self.context, font=self.node.mkfont
            )
            glyphs = None
            if mydlg.ShowModal() == wx.ID_OK:
                # This returns a string of characters that need to be inserted
                glyphs = mydlg.result()
            mydlg.Destroy()
            if glyphs is None or glyphs == "":
                return
            text = self.text_text.GetValue()
            pos = self.text_text.GetInsertionPoint()
            if pos == self.text_text.GetLastPosition():
                before = text
                after = ""
            else:
                before = self.text_text.GetValue()[:pos]
                after = self.text_text.GetValue()[pos:]
            self.text_text.SetValue(before + glyphs + after)

        menu = wx.Menu()
        item = menu.Append(wx.ID_ANY, _("Paste"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, on_paste, item)
        item = menu.Append(wx.ID_ANY, _("Insert symbol"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, on_glyph, item)
        self.PopupMenu(menu)
        menu.Destroy()


    def signal(self, signalstr, myargs):
        if signalstr == "textselect" and self.IsShown():
            # This can crash for completely unknown reasons under Linux!
            # Hypothesis: you can't focus / SelectStuff if the control is not yet shown.
            if self._islinux:
                return
            self.text_text.SelectAll()
            self.text_text.SetFocus()


class PanelFontSelect(wx.Panel):
    """
    Panel to select font during line text creation
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)

        mainsizer = wx.BoxSizer(wx.VERTICAL)

        self.all_fonts = []
        self.fonts = []
        self.font_checks = {}

        fontinfo = self.context.fonts.fonts_registered
        sizer_checker = wx.BoxSizer(wx.HORIZONTAL)
        for extension in fontinfo:
            info = fontinfo[extension]
            checker = wxCheckBox(self, wx.ID_ANY, info[0])
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

        self.list_fonts = wxListBox(self, wx.ID_ANY)
        self.list_fonts.SetToolTip(
            _("Select to preview the font, double-click to apply it")
        )
        sizer_fonts.Add(self.list_fonts, 1, wx.EXPAND, 0)
        sizer_fonts.Add(sizer_checker, 0, wx.EXPAND, 0)

        self.bmp_preview = wxStaticBitmap(self, wx.ID_ANY)
        self.bmp_preview.SetMinSize(dip_size(self, -1, 70))
        sizer_fonts.Add(self.bmp_preview, 0, wx.EXPAND, 0)

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_fonts.Add(sizer_buttons, 0, wx.EXPAND, 0)

        picsize = dip_size(self, 32, 32)
        icon_size = picsize[0]
        bsize = icon_size * self.context.root.bitmap_correction_scale

        self.btn_bigger = wxButton(self, wx.ID_ANY)
        self.btn_bigger.SetBitmap(icon_textsize_up.GetBitmap(resize=bsize))
        self.btn_bigger.SetToolTip(_("Increase the font-size"))
        sizer_buttons.Add(self.btn_bigger, 0, wx.EXPAND, 0)

        self.btn_smaller = wxButton(self, wx.ID_ANY)
        self.btn_smaller.SetBitmap(icon_textsize_down.GetBitmap(resize=bsize))
        self.btn_smaller.SetToolTip(_("Decrease the font-size"))
        sizer_buttons.Add(self.btn_smaller, 0, wx.EXPAND, 0)

        sizer_buttons.AddSpacer(25)

        self.btn_align_left = wxButton(self, wx.ID_ANY)
        self.btn_align_left.SetBitmap(icon_textalign_left.GetBitmap(resize=bsize))
        self.btn_align_left.SetToolTip(_("Align text on the left side"))
        sizer_buttons.Add(self.btn_align_left, 0, wx.EXPAND, 0)

        self.btn_align_center = wxButton(self, wx.ID_ANY)
        self.btn_align_center.SetBitmap(
            icon_textalign_center.GetBitmap(resize=bsize)
        )
        self.btn_align_center.SetToolTip(_("Align text around the center"))
        sizer_buttons.Add(self.btn_align_center, 0, wx.EXPAND, 0)

        self.btn_align_right = wxButton(self, wx.ID_ANY)
        self.btn_align_right.SetBitmap(icon_textalign_right.GetBitmap(resize=bsize))
        self.btn_align_right.SetToolTip(_("Align text on the right side"))
        sizer_buttons.Add(self.btn_align_right, 0, wx.EXPAND, 0)

        for btn in (
            self.btn_align_center,
            self.btn_align_left,
            self.btn_align_right,
            self.btn_bigger,
            self.btn_smaller,
        ):
            btn.SetMaxSize(dip_size(self, icon_size + 4, -1))

        lbl_spacer = wxStaticText(self, wx.ID_ANY, "")
        sizer_buttons.Add(lbl_spacer, 1, 0, 0)

        self.SetSizer(mainsizer)

        self.Layout()

        self.Bind(wx.EVT_LISTBOX, self.on_list_font, self.list_fonts)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_list_font_dclick, self.list_fonts)
        self.Bind(wx.EVT_BUTTON, self.on_btn_bigger, self.btn_bigger)
        self.Bind(wx.EVT_BUTTON, self.on_btn_smaller, self.btn_smaller)

        self.Bind(wx.EVT_BUTTON, self.on_align("start"), self.btn_align_left)
        self.Bind(wx.EVT_BUTTON, self.on_align("middle"), self.btn_align_center)
        self.Bind(wx.EVT_BUTTON, self.on_align("end"), self.btn_align_right)

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

    def on_align(self, alignment):
        def handler(event):
            self.context.signal("linetext", "align", local_alignment)

        local_alignment = alignment
        return handler

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
            icons8_choose_font.GetBitmap(resize=0.5 * get_default_icon_size(self.context))
        )
        # _icon.CopyFromBitmap(icons8_computer_support.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Font-Selection"))
        self.restore_aspect()

    def window_open(self):
        pass

    def window_close(self):
        # We don't need an automatic opening
        self.window_context.open_on_start = False

    def delegates(self):
        yield self.panel

    @staticmethod
    def submenu():
        # Suppress = True
        return "", "Font-Selector", True

    @staticmethod
    def helptext():
        return _("Pick a font to use for vector text")

    @signal_listener("tool_changed")
    def on_tool_changed(self, origin, newtool=None, *args):
        # Signal provides a tuple with (togglegroup, id)
        needs_close = True
        if newtool is not None:
            if isinstance(newtool, (list, tuple)):
                group = newtool[0].lower() if newtool[0] is not None else ""
                identifier = newtool[1].lower() if newtool[1] is not None else ""
            else:
                group = newtool
                identifier = ""
            needs_close = identifier != "linetext"
        if needs_close:
            self.Close()


class PanelFontManager(wx.Panel):
    """
    Vector Font Manager
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("vectortext")

        mainsizer = wx.BoxSizer(wx.VERTICAL)

        self.font_infos = []

        self.text_info = TextCtrl(
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

        self.text_fontdir = TextCtrl(self, wx.ID_ANY, "")
        sizer_directory.Add(self.text_fontdir, 1, wx.EXPAND, 0)
        self.text_fontdir.SetToolTip(
            _(
                "Additional directory for userdefined fonts (also used to store some cache files)"
            )
        )

        self.btn_dirselect = wxButton(self, wx.ID_ANY, "...")
        sizer_directory.Add(self.btn_dirselect, 0, wx.EXPAND, 0)

        choices = []
        prechoices = context.lookup("choices/preferences")
        for info in prechoices:
            if info["attr"] == "system_font_directories":
                cinfo = dict(info)
                cinfo["page"] = ""
                choices.append(cinfo)
                break

        self.sysdirs = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=choices, scrolling=False
        )
        mainsizer.Add(self.sysdirs, 0, wx.EXPAND, 0)
        sizer_fonts = StaticBoxSizer(self, wx.ID_ANY, _("Fonts"), wx.VERTICAL)
        mainsizer.Add(sizer_fonts, 1, wx.EXPAND, 0)

        self.list_fonts = wxListBox(self, wx.ID_ANY)
        sizer_fonts.Add(self.list_fonts, 1, wx.EXPAND, 0)

        self.bmp_preview = wxStaticBitmap(self, wx.ID_ANY)
        self.bmp_preview.SetMinSize(dip_size(self, -1, 70))
        sizer_fonts.Add(self.bmp_preview, 0, wx.EXPAND, 0)

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_fonts.Add(sizer_buttons, 0, wx.EXPAND, 0)

        self.btn_add = wxButton(self, wx.ID_ANY, _("Import"))
        sizer_buttons.Add(self.btn_add, 0, wx.EXPAND, 0)

        self.btn_delete = wxButton(self, wx.ID_ANY, _("Delete"))
        sizer_buttons.Add(self.btn_delete, 0, wx.EXPAND, 0)

        lbl_spacer = wxStaticText(self, wx.ID_ANY, "")
        sizer_buttons.Add(lbl_spacer, 1, 0, 0)

        self.btn_refresh = wxButton(self, wx.ID_ANY, _("Refresh"))
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
        self.combo_webget = wxComboBox(
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
            self.text_fontdir.SetBackgroundColour(
                wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)
            )
            self.text_fontdir.SetToolTip(
                _(
                    "Additional directory for userdefined fonts (also used to store some cache files)"
                )
            )
        else:
            self.text_fontdir.SetBackgroundColour(
                wx.SystemSettings().GetColour(wx.SYS_COLOUR_HIGHLIGHT)
            )
            self.text_fontdir.SetToolTip(
                _("Invalid directory! Will not be used, please provide a valid path.")
            )
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

                progress.Update(idx + 1, progress_string.format(count=idx + 1))
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

                progress.Update(idx + 1, progress_string.format(count=idx + 1))
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

    def pane_hide(self):
        self.sysdirs.pane_hide()

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

    @staticmethod
    def helptext():
        return _("Manage the fonts available to MeerK40t")


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
