from math import sqrt

import wx

import meerk40t.gui.icons as mkicons
from meerk40t.core.units import Length
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.wxutils import (
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxButton,
    wxCheckBox,
    wxComboBox,
    wxStaticBitmap,
    wxStaticText,
    wxToggleButton,
)
from meerk40t.svgelements import Color

_ = wx.GetTranslation


class ColorPanel(wx.Panel):
    def __init__(
        self,
        *args,
        context=None,
        label=None,
        attribute=None,
        callback=None,
        node=None,
        **kwds,
    ):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.callback = callback
        if attribute is None:
            attribute = "stroke"
        self.attribute = attribute
        self.label = label
        self.node = node

        self.main_sizer = StaticBoxSizer(self, wx.ID_ANY, _(self.label), wx.VERTICAL)
        color_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.main_sizer.Add(color_sizer, 0, wx.EXPAND, 0)
        self.btn_color = []
        self.underliner = []
        self.bgcolors = [
            0xFFFFFF,
            0x000000,
            0xFF0000,
            0x00FF00,
            0x0000FF,
            0xFFFF00,
            0xFF00FF,
            0x00FFFF,
            0xFFFFFF,
            None,
        ]
        self.last_col_idx = len(self.bgcolors) - 1
        for i in range(len(self.bgcolors)):
            self.underliner.append(wxStaticBitmap(self, wx.ID_ANY))
            self.underliner[i].SetBackgroundColour(wx.BLUE)
            self.underliner[i].SetMaxSize(dip_size(self, -1, 3))
            # self.lbl_color[i].SetMinSize(dip_size(self, -1, 20))
            self.btn_color.append(wxButton(self, wx.ID_ANY, ""))
            if i == 0:
                self.btn_color[i].SetForegroundColour(wx.RED)
                self.btn_color[i].SetLabel("X")
            elif i == len(self.bgcolors) - 1:
                self.btn_color[i].SetLabel(_("Custom"))
            else:
                self.btn_color[i].SetForegroundColour(wx.Colour(self.bgcolors[i]))
                colinfo = wx.Colour(self.bgcolors[i]).GetAsString(wx.C2S_NAME)
                self.btn_color[i].SetLabel(_(colinfo))
            self.btn_color[i].SetMinSize(dip_size(self, 10, 23))
            self.btn_color[i].SetBackgroundColour(wx.Colour(self.bgcolors[i]))
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(self.btn_color[i], 0, wx.EXPAND, 0)
            sizer.Add(self.underliner[i], 0, wx.EXPAND, 0)
            color_sizer.Add(sizer, 1, wx.EXPAND, 0)
            self.btn_color[i].Bind(wx.EVT_BUTTON, self.on_button)
        font = wx.Font(
            7,
            wx.FONTFAMILY_SWISS,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_BOLD,
        )
        self.btn_color[self.last_col_idx].SetFont(font)
        self.SetSizer(self.main_sizer)
        self.main_sizer.Fit(self)
        self.Layout()
        self.set_widgets(self.node)

    def on_button(self, event):
        value = None
        button = event.GetEventObject()
        bidx = None
        if button == self.btn_color[self.last_col_idx]:
            nodecol = None
            cvalue = getattr(self.node, self.attribute, None)
            if cvalue == "none":
                cvalue = None
            if cvalue is not None:
                nodecol = wx.Colour(swizzlecolor(cvalue))
            color_data = wx.ColourData()
            color_data.SetColour(wx.Colour(nodecol))
            # We try to prepopulate user defined colors from
            # the colors of the existing operations
            idx = 0
            for operation in self.context.elements.ops():
                if hasattr(operation, "color"):
                    if operation.color is not None and operation.color.argb is not None:
                        color_data.SetCustomColour(
                            idx, wx.Colour(swizzlecolor(operation.color))
                        )
                        idx += 1
                        # There are only 16 colors available
                        if idx > 15:
                            break
            dlg = wx.ColourDialog(self, color_data)
            if dlg.ShowModal() == wx.ID_OK:
                color_data = dlg.GetColourData()
                cvalue = color_data.GetColour()
                value = Color(swizzlecolor(cvalue.GetRGB()), 1.0)
                button.SetBackgroundColour(cvalue)
            else:
                return
        else:
            for bidx, sbtn in enumerate(self.btn_color):
                if sbtn == button:
                    value = None
                    if bidx == 0:
                        value = None
                    else:
                        if bidx < 0 or bidx >= len(self.btn_color):
                            bidx = -1
                        else:
                            bcolor = button.GetBackgroundColour()
                            rgb = bcolor.GetRGB()
                            color = swizzlecolor(rgb)
                            value = Color(color, 1.0)
                    break
        setattr(self.node, self.attribute, value)
        self.context.elements.signal("element_property_update", self.node)
        if self.callback is not None:
            self.callback()
        self.mark_color(bidx)
        self.node.focus()

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def accepts(self, node):
        return hasattr(node, self.attribute)

    def set_widgets(self, node):
        self.node = node
        # print(f"set_widget for {self.attribute} to {str(node)}")
        if self.node is None or not self.accepts(node):
            self.Hide()
            return
        self.mark_color(None)
        self.Show()

    def mark_color(self, idx):
        def countercolor(bgcolor):
            background = swizzlecolor(bgcolor)
            c1 = Color("Black")
            c2 = Color("White")
            if Color.distance(background, c1) > Color.distance(background, c2):
                textcolor = c1
            else:
                textcolor = c2
            wxcolor = wx.Colour(swizzlecolor(textcolor))
            return wxcolor

        if self.node is None:
            idx = -1
            self.btn_color[self.last_col_idx].SetBackgroundColour(None)
            self.bgcolors[self.last_col_idx] = None
        else:
            value = getattr(self.node, self.attribute, None)
            nodecol = None
            if value == "none":
                value = None

            colinfo = "None"
            if value is not None:
                nodecol = wx.Colour(swizzlecolor(value))
                self.bgcolors[self.last_col_idx] = nodecol
                self.btn_color[self.last_col_idx].SetBackgroundColour(
                    self.bgcolors[self.last_col_idx]
                )
                self.btn_color[self.last_col_idx].SetForegroundColour(
                    countercolor(self.bgcolors[self.last_col_idx])
                )
                try:
                    s = nodecol.GetAsString(wx.C2S_NAME)
                except AssertionError:
                    s = ""
                if s != "":
                    s = s + " = " + value.hexrgb
                else:
                    s = value.hexrgb
                colinfo = s
            self.main_sizer.SetLabel(_(self.label) + " (" + colinfo + ")")
            self.main_sizer.Refresh()

            if idx is None:  # Okay, we need to determine it ourselves
                idx = -1
                if value is None:
                    idx = 0
                else:
                    for i, btn in enumerate(self.btn_color):
                        if i == 0:  # We skip the none color...
                            continue
                        col = self.btn_color[i].GetBackgroundColour()
                        if nodecol == col:
                            idx = i
                            break

        for i, liner in enumerate(self.underliner):
            if i == idx:
                liner.Show(True)
            else:
                liner.Show(False)
        self.Layout()


class IdPanel(wx.Panel):
    def __init__(
        self, *args, context=None, node=None, showid=True, showlabel=True, **kwds
    ):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node
        # Shall we display id / label?
        self.showid = showid
        self.showlabel = showlabel
        self.text_id = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_label = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.check_label = wxCheckBox(self, wx.ID_ANY)
        self.check_hidden = wxCheckBox(self, wx.ID_ANY)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_id_label = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_id = StaticBoxSizer(self, wx.ID_ANY, _("Id"), wx.HORIZONTAL)
        self.sizer_id.Add(self.text_id, 1, wx.EXPAND, 0)
        self.sizer_id.Add(self.check_hidden, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.sizer_label = StaticBoxSizer(self, wx.ID_ANY, _("Label"), wx.VERTICAL)
        h_label_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_label_sizer.Add(self.text_label, 1, wx.EXPAND, 0)
        h_label_sizer.Add(self.check_label, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.sizer_label.Add(h_label_sizer, 1, wx.EXPAND, 0)
        sizer_id_label.Add(self.sizer_id, 1, wx.EXPAND, 0)
        sizer_id_label.Add(self.sizer_label, 1, wx.EXPAND, 0)
        self.icon_display = wxStaticBitmap(self, wx.ID_ANY)
        self.icon_display.SetSize(wx.Size(mkicons.STD_ICON_SIZE, mkicons.STD_ICON_SIZE))
        self.icon_hidden = wxStaticBitmap(self, wx.ID_ANY)
        self.icon_hidden.SetSize(wx.Size(mkicons.STD_ICON_SIZE, mkicons.STD_ICON_SIZE))
        self.icon_hidden.SetBitmap(
            mkicons.icons8_ghost.GetBitmap(resize=mkicons.STD_ICON_SIZE * self.context.root.bitmap_correction_scale)
        )
        self.icon_hidden.SetToolTip(
            _("Element is hidden, so it will neither be displayed nor burnt")
        )
        sizer_id_label.Add(self.icon_display, 0, wx.EXPAND, 0)
        sizer_id_label.Add(self.icon_hidden, 0, wx.EXPAND, 0)

        main_sizer.Add(sizer_id_label, 0, wx.EXPAND, 0)

        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()
        self.text_id.SetActionRoutine(self.on_text_id_change)
        self.text_label.SetActionRoutine(self.on_text_label_change)
        self.check_label.Bind(wx.EVT_CHECKBOX, self.on_check_label)
        self.check_label.SetToolTip(_("Display label on screen"))
        self.check_hidden.Bind(wx.EVT_CHECKBOX, self.on_check_hidden)
        self.check_hidden.SetToolTip(_("Suppress object for display and burning"))
        self.icon_hidden.Bind(wx.EVT_LEFT_DOWN, self.on_hidden_click)

        self.set_widgets(self.node)

    def on_text_id_change(self):
        try:
            self.node.id = self.text_id.GetValue()
            self.context.elements.signal("element_property_reload", self.node)
        except AttributeError:
            pass

    def on_text_label_change(self):
        try:
            self.node.label = self.text_label.GetValue()
            self.context.elements.signal("element_property_reload", self.node)
            self.text_label.SetToolTip(self.node.display_label())
        except AttributeError:
            pass

    def add_node_and_children(self, node):
        data = []
        data.append(node)
        for e in node.children:
            if e.type in ("file", "group"):
                data.extend(self.add_node_and_children(e))
            else:
                data.append(e)
        return data

    def on_check_label(self, event):
        self.node.label_display = bool(self.check_label.GetValue())
        self.context.signal("element_property_update", self.node)
        self.context.signal("refresh_scene", "Scene")

    def on_check_hidden(self, event):
        self.node.hidden = bool(self.check_hidden.GetValue())
        self.icon_hidden.Show(self.node.hidden)
        self.Layout()
        if self.node.type == "group":
            self.context.signal("refresh_tree")
        data = self.add_node_and_children(self.node)
        self.context.signal("element_property_reload", data)
        self.context.signal("refresh_scene", "Scene")
        self.context.signal("warn_state_update")

    def on_hidden_click(self, event):
        self.node.hidden = False
        self.check_hidden.SetValue(False)
        self.icon_hidden.Show(self.node.hidden)
        self.Layout()
        data = self.add_node_and_children(self.node)
        self.context.signal("element_property_reload", data)
        self.context.signal("refresh_scene", "Scene")
        self.context.signal("warn_state_update")

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def set_widgets(self, node):
        def mklabel(value):
            res = ""
            if value is not None:
                res = str(value)
            return res

        self.node = node
        # print(f"set_widget for {self.attribute} to {str(node)}")
        vis0 = False
        vis1 = False
        vis2 = False
        vis3 = False
        vis_hidden = False
        try:
            if hasattr(self.node, "id") and self.showid:
                vis1 = True
                self.text_id.SetValue(mklabel(node.id))
            self.text_id.Show(vis1)
            self.sizer_id.Show(vis1)
        except RuntimeError:
            # Could happen if the propertypanel has been destroyed
            pass
        try:
            if hasattr(self.node, "hidden") and self.showid:
                vis0 = True
                self.check_hidden.SetValue(node.hidden)
                vis_hidden = self.node.hidden
            self.check_hidden.Show(vis0)
            self.icon_hidden.Show(vis_hidden)
        except RuntimeError:
            # Could happen if the propertypanel has been destroyed
            pass
        try:
            if hasattr(self.node, "label") and self.showlabel:
                vis2 = True
                if hasattr(self.node, "label_display"):
                    vis3 = True
                    self.check_label.SetValue(bool(self.node.label_display))
                self.text_label.SetValue(mklabel(node.label))
                self.text_label.SetToolTip(node.display_label())
            self.text_label.Show(vis2)
            self.sizer_label.Show(vis2)
            self.check_label.Show(vis3)
        except RuntimeError:
            # Could happen if the propertypanel has been destroyed
            pass

        bmp = None
        type_patterns = {
            "util wait": mkicons.icon_timer,
            "util home": mkicons.icons8_home_filled,
            "util goto": mkicons.icon_return,
            "util output": mkicons.icon_external,
            "util input": mkicons.icon_internal,
            "util console": mkicons.icon_console,
            "op engrave": mkicons.icons8_laserbeam_weak,
            "op cut": mkicons.icons8_laser_beam,
            "op image": mkicons.icons8_image,
            "op raster": mkicons.icons8_direction,
            "op dots": mkicons.icon_points,
            "effect hatch": mkicons.icon_effect_hatch,
            "effect wobble": mkicons.icon_effect_wobble,
            "effect warp": mkicons.icon_distort,
            "place current": mkicons.icons8_home_filled,
            "place point": mkicons.icons8_home_filled,
            "elem point": mkicons.icon_points,
            "file": mkicons.icons8_file,
            "group": mkicons.icons8_group_objects,
            "elem rect": mkicons.icon_mk_rectangular,
            "elem ellipse": mkicons.icon_mk_ellipse,
            "elem image": mkicons.icons8_image,
            "elem path": mkicons.icon_path,
            "elem line": mkicons.icon_line,
            "elem polyline": mkicons.icon_mk_polyline,
            "elem text": mkicons.icon_bmap_text,
            "image raster": mkicons.icons8_image,
            "blob": mkicons.icons8_file,
            "_3d_image": mkicons.icon_image3d,
        }
        if hasattr(self.node, "type"):
            n_type = node.type
            if n_type == "elem image" and getattr(node, "is_depthmap", False):
                n_type = "_3d_image"
            if n_type in type_patterns:
                icon = type_patterns[n_type]
                bmp = icon.GetBitmap(resize=mkicons.STD_ICON_SIZE * self.context.root.bitmap_correction_scale, buffer=2)
        if bmp is None:
            self.icon_display.Show(False)
        else:
            try:
                self.icon_display.SetBitmap(bmp)
                self.icon_display.Show(True)
            except RuntimeError:
                pass

        if vis1 or vis2:
            self.Layout()
            self.Show()
        else:
            self.Hide()

    def signal(self, signalstr, myargs):
        if signalstr == "nodetype":
            self.set_widgets(self.node)

class LinePropPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node
        capchoices = (_("Butt"), _("Round"), _("Square"))
        joinchoices = (_("Arcs"), _("Bevel"), _("Miter"), _("Miter-Clip"), _("Round"))
        fillchoices = (_("Non-Zero"), _("Even-Odd"))
        self.dash_patterns = {
            "Solid": "",
            "Dot": "0.5 0.5",
            "Short Dash": "2 1",
            "Long Dash": "4 1",
            "Dash Dot": "4 1 0.5 1",
        }
        linestylechoices = [_(e) for e in self.dash_patterns]
        linestylechoices.append(_("User defined"))
        self.combo_cap = wxComboBox(
            self, wx.ID_ANY, choices=capchoices, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.combo_join = wxComboBox(
            self, wx.ID_ANY, choices=joinchoices, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.combo_fill = wxComboBox(
            self, wx.ID_ANY, choices=fillchoices, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.combo_linestyle = wxComboBox(
            self,
            wx.ID_ANY,
            choices=linestylechoices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.text_linestyle = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.combo_cap.SetMaxSize(dip_size(self, 100, -1))
        self.combo_join.SetMaxSize(dip_size(self, 100, -1))
        self.combo_fill.SetMaxSize(dip_size(self, 100, -1))
        self.combo_linestyle.SetMaxSize(dip_size(self, 150, -1))

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_attributes = wx.BoxSizer(wx.HORIZONTAL)

        self.sizer_cap = StaticBoxSizer(self, wx.ID_ANY, _("Line-End"), wx.VERTICAL)
        self.sizer_cap.Add(self.combo_cap, 1, wx.EXPAND, 0)

        self.sizer_join = StaticBoxSizer(self, wx.ID_ANY, _("Line-Join"), wx.VERTICAL)
        self.sizer_join.Add(self.combo_join, 1, wx.EXPAND, 0)

        self.sizer_fill = StaticBoxSizer(self, wx.ID_ANY, _("Fillrule"), wx.VERTICAL)
        self.sizer_fill.Add(self.combo_fill, 1, wx.EXPAND, 0)

        self.sizer_linestyle = StaticBoxSizer(
            self, wx.ID_ANY, _("Linestyle"), wx.HORIZONTAL
        )
        self.sizer_linestyle.Add(self.combo_linestyle, 1, wx.EXPAND, 0)
        self.sizer_linestyle.Add(self.text_linestyle, 1, wx.EXPAND, 0)

        self.tab_length = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            style=wx.TE_PROCESS_ENTER,
            limited=True,
            check="length",
        )
        self.tab_positions = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            style=wx.TE_PROCESS_ENTER,
        )
        self.tab_length.SetMaxSize(dip_size(self, 100, -1))
        label1 = wxStaticText(self, wx.ID_ANY, _("Tab-Length"))
        label2 = wxStaticText(self, wx.ID_ANY, _("Tabs"))
        self.sizer_tabs = StaticBoxSizer(
            self, wx.ID_ANY, _("Tabs/Bridges"), wx.HORIZONTAL
        )
        self.sizer_tabs.Add(label1, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.sizer_tabs.Add(self.tab_length, 1, wx.EXPAND, 0)
        self.sizer_tabs.Add(label2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.sizer_tabs.Add(self.tab_positions, 1, wx.EXPAND, 0)

        sizer_attributes.Add(self.sizer_cap, 1, wx.EXPAND, 0)
        sizer_attributes.Add(self.sizer_join, 1, wx.EXPAND, 0)
        sizer_attributes.Add(self.sizer_fill, 1, wx.EXPAND, 0)
        main_sizer.Add(sizer_attributes, 0, wx.EXPAND, 0)

        sizer_attributes2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_attributes2.Add(self.sizer_linestyle, 1, wx.EXPAND, 0)
        sizer_attributes2.Add(self.sizer_tabs, 1, wx.EXPAND, 0)
        main_sizer.Add(sizer_attributes2, 0, wx.EXPAND, 0)

        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()
        self.combo_cap.Bind(wx.EVT_COMBOBOX, self.on_cap)
        self.combo_join.Bind(wx.EVT_COMBOBOX, self.on_join)
        self.combo_fill.Bind(wx.EVT_COMBOBOX, self.on_fill)
        self.combo_linestyle.Bind(wx.EVT_COMBOBOX, self.on_linestyle)
        self.text_linestyle.SetActionRoutine(self.on_txt_linestyle)
        self.tab_positions.SetActionRoutine(self.on_tab_count)
        self.tab_length.SetActionRoutine(self.on_tab_length)
        self.combo_linestyle.SetToolTip(_("Choose the linestyle of the shape"))
        self.text_linestyle.SetToolTip(
            _("Define the linestyle of the shape:") + "\n" +
            _("A list of comma and/or white space separated numbers that specify the lengths of alternating dashes and gaps")
        )
        self.tab_positions.SetToolTip(
            _("Where do you want to place tabs:") +  "\n" +
            _("A list of comma and/or white space separated numbers that specify the relative positions, i.e. percentage of total shape perimeter, of the tab centers.") + "\n" +
            _("You may provide a placeholder for x equidistant tabs by stating '*x' e.g. '*4' for four tabs.") + "\n" +
            _("An empty list stands for no tabs.")
        )
        self.tab_length.SetToolTip(_("How wide should the tab be?"))
        self.set_widgets(self.node)

    def on_cap(self, event):
        if self.node is None or self.node.lock:
            return
        _id = self.combo_cap.GetSelection()
        try:
            self.node.linecap = _id
            self.context.signal("element_property_update", self.node)
            self.context.signal("refresh_scene", "Scene")
        except AttributeError:
            pass

    def on_join(self, event):
        if self.node is None or self.node.lock:
            return
        _id = self.combo_join.GetSelection()
        try:
            self.node.linejoin = _id
            self.context.signal("element_property_update", self.node)
            self.context.signal("refresh_scene", "Scene")
        except AttributeError:
            pass

    def on_fill(self, event):
        if self.node is None or self.node.lock:
            return
        _id = self.combo_fill.GetSelection()
        try:
            self.node.fillrule = _id
            self.context.signal("element_property_update", self.node)
            self.context.signal("refresh_scene", "Scene")
        except AttributeError:
            pass

    def on_linestyle(self, event):
        if self.node is None or self.node.lock:
            return
        _id = self.combo_linestyle.GetSelection()
        for idx, (key, entry) in enumerate(self.dash_patterns.items()):
            if idx == _id:
                self.text_linestyle.SetValue(entry)
                self.on_txt_linestyle()
                break

    def sync_linestyle_combo(self, value):
        if value is None:
            value = ""
        index = -1
        for idx, (key, entry) in enumerate(self.dash_patterns.items()):
            if value == entry:
                index = idx
                break
        if index < 0:
            index = len(self.dash_patterns)  # The following "user defined..."
        self.combo_linestyle.SetSelection(index)

    def on_txt_linestyle(self):
        if self.node is None or self.node.lock:
            return
        value = self.text_linestyle.GetValue()
        self.sync_linestyle_combo(value)
        if value == "":
            value = None
        try:
            self.node.stroke_dash = value
            # We need to recalculate the appearance
            self.node.empty_cache()
            self.context.signal("element_property_update", self.node)
            self.context.signal("refresh_scene", "Scene")
        except AttributeError:
            pass

    def on_tab_length(self):
        if self.node is None or self.node.lock:
            return
        try:
            swidth = float(Length(self.tab_length.GetValue()))
            if self.node.mktablength != swidth:
                self.node.mktablength = swidth
                self.node.empty_cache()
                self.context.signal("refresh_scene", "Scene")
                self.context.signal("element_property_update", self.node)
                self.context.signal("tabs_updated")
        except (ValueError, AttributeError):
            pass

    def on_tab_count(self):
        if self.node is None or self.node.lock:
            return
        try:
            positions = self.tab_positions.GetValue()
            if self.node.mktabpositions != positions:
                self.node.mktabpositions = positions
                self.node.empty_cache()
                self.context.signal("refresh_scene", "Scene")
                self.context.signal("element_property_update", self.node)
                self.context.signal("tabs_updated")
        except (ValueError, AttributeError):
            pass

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def set_widgets(self, node):
        self.node = node
        # print(f"set_widget for {self.attribute} to {str(node)}")
        vis1 = False
        vis2 = False
        vis3 = False
        vis4 = False
        vis5 = False
        if hasattr(self.node, "linecap"):
            vis1 = True
            self.combo_cap.SetSelection(int(node.linecap))
        if hasattr(self.node, "linejoin"):
            vis2 = True
            self.combo_join.SetSelection(int(node.linejoin))
        if hasattr(self.node, "fillrule"):
            vis3 = True
            self.combo_fill.SetSelection(int(node.fillrule))
        if hasattr(self.node, "stroke_dash"):
            vis4 = True
            value = self.node.stroke_dash
            if value is None:
                value = ""
            self.text_linestyle.SetValue(value)
            self.sync_linestyle_combo(value)
        if hasattr(self.node, "mktablength"):
            vis5 = True
            x = self.node.mktablength
            units = self.context.units_name
            if units in ("inch", "inches"):
                units = "in"
            self.tab_length.SetValue(
                f"{Length(amount=x, preferred_units=units, digits=4).preferred_length}"
            )
            val = node.mktabpositions
            if val is None:
                val = ""
            self.tab_positions.SetValue(val)

        self.combo_cap.Show(vis1)
        self.sizer_cap.Show(vis1)
        self.combo_join.Show(vis2)
        self.sizer_join.Show(vis2)
        self.combo_fill.Show(vis3)
        self.sizer_fill.Show(vis3)
        self.combo_linestyle.Show(vis4)
        self.sizer_linestyle.Show(vis4)
        self.tab_length.Show(vis5)
        self.tab_positions.Show(vis5)
        self.sizer_tabs.Show(vis5)

        if vis1 or vis2 or vis3 or vis4 or vis5:
            self.Show()
        else:
            self.Hide()


class StrokeWidthPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        s_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Stroke-Width"), wx.HORIZONTAL)
        main_sizer.Add(s_sizer, 1, wx.EXPAND, 0)
        # Plus one combobox + value field for stroke width
        strokewidth_label = wxStaticText(self, wx.ID_ANY, label=_("Width:"))
        self.text_width = TextCtrl(
            self,
            wx.ID_ANY,
            value="0.10",
            style=wx.TE_PROCESS_ENTER,
            check="float",
            limited=True,
        )
        self.text_width.SetMaxSize(dip_size(self, 100, -1))

        self.unit_choices = ["px", "pt", "mm", "cm", "inch", "mil"]
        self.combo_units = wxComboBox(
            self,
            wx.ID_ANY,
            choices=self.unit_choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_units.SetSelection(0)
        self.combo_units.SetMaxSize(dip_size(self, 100, -1))

        self.chk_scale = wxCheckBox(self, wx.ID_ANY, _("Scale"))
        self.chk_scale.SetToolTip(
            _("Toggle the behaviour of stroke-growth.")
            + "\n"
            + _("Active: stroke width remains the same, regardless of the element size")
            + "\n"
            + _("Inactive: stroke grows/shrink with scaled element")
        )
        s_sizer.Add(strokewidth_label, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        s_sizer.Add(self.text_width, 1, wx.EXPAND, 0)
        s_sizer.Add(self.combo_units, 1, wx.EXPAND, 0)
        s_sizer.Add(self.chk_scale, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Bind(wx.EVT_COMBOBOX, self.on_stroke_width_combo, self.combo_units)
        self.Bind(wx.EVT_CHECKBOX, self.on_chk_scale, self.chk_scale)
        self.text_width.SetActionRoutine(self.on_stroke_width)
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()
        self.set_widgets(self.node)

    def on_chk_scale(self, event):
        if self.node is None or self.node.lock:
            return
        flag = self.chk_scale.GetValue()
        try:
            if self.node.stroke_scaled != flag:
                self.node.stroke_scaled = flag
                self.context.signal("refresh_scene", "Scene")
                self.context.signal("element_property_update", self.node)
        except (ValueError, AttributeError):
            pass

    def on_stroke_width_combo(self, event):
        self.on_stroke_width()

    def on_stroke_width(self):
        if self.node is None or self.node.lock:
            return
        try:
            swidth = float(
                Length(
                    f"{self.text_width.GetValue()}{self.unit_choices[self.combo_units.GetSelection()]}"
                )
            )
            stroke_scale = (
                sqrt(abs(self.node.matrix.determinant))
                if self.node.stroke_scaled
                else 1.0
            )
            stroke_width = swidth / stroke_scale
            if self.node.stroke_width != stroke_width:
                self.node.stroke_width = stroke_width
                self.node.altered()
                self.context.signal("refresh_scene", "Scene")
                self.context.signal("element_property_update", self.node)
        except (ValueError, AttributeError):
            pass

    def set_widgets(self, node):
        self.node = node
        enable = False
        if self.node is None:
            self.text_width.SetValue("0")
            self.combo_units.SetSelection(0)
            self.chk_scale.SetValue(True)
        elif hasattr(self.node, "stroke_width") and hasattr(self.node, "stroke_scaled"):
            enable = True
            self.chk_scale.SetValue(self.node.stroke_scaled)
            # Let's establish which unit might be the best to represent the display
            value = 0
            idxunit = 0  # px
            if self.node.stroke_width is not None and self.node.stroke_width != 0:
                found_something = False
                best_post = 99999999
                delta = 0.99999999
                best_pre = 0
                # # We don't need to scale it here...
                # factor = (
                #     sqrt(abs(self.node.matrix.determinant))
                #     if self.node.stroke_scaled
                #     else 1.0
                # )
                factor = 1
                node_stroke_width = self.node.stroke_width * factor
                # print (f"Stroke-width={self.node.stroke_width} ({node_stroke_width}), scaled={self.node.stroke_scaled}")
                for idx, unit in enumerate(self.unit_choices):
                    std = float(Length(f"1{unit}"))
                    fraction = abs(round(node_stroke_width / std, 6))
                    if fraction == 0:
                        continue
                    curr_post = 0
                    curr_pre = int(fraction)
                    while fraction < 1:
                        curr_post += 1
                        fraction *= 10
                    fraction -= curr_pre
                    # print (f"unit={unit}, fraction={fraction}, digits={curr_post}, value={node_stroke_width / std}")
                    takespref = False
                    if fraction < delta:
                        takespref = True
                    elif fraction == delta and curr_pre > best_pre:
                        takespref = True
                    elif fraction == delta and curr_post < best_post:
                        takespref = True
                    if takespref:
                        best_pre = curr_pre
                        delta = fraction
                        best_post = curr_post
                        idxunit = idx
                        value = node_stroke_width / std
                        found_something = True

                if not found_something:
                    std = float(Length("1mm"))
                    if node_stroke_width / std < 0.1:
                        idxunit = 0  # px
                    else:
                        idxunit = 2  # mm
                    unit = self.unit_choices[idxunit]
                    std = float(Length(f"1{unit}"))
                    value = node_stroke_width / std
            self.text_width.SetValue(str(round(value, 6)))
            self.combo_units.SetSelection(idxunit)

        self.text_width.Enable(enable)
        self.combo_units.Enable(enable)
        self.chk_scale.Enable(enable)

    def pane_hide(self):
        pass

    def pane_show(self):
        pass


class PositionSizePanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node
        self.text_x = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            style=wx.TE_PROCESS_ENTER,
            limited=True,
            check="length",
        )
        self.text_y = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER, limited=True, check="length"
        )
        self.text_w = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            style=wx.TE_PROCESS_ENTER,
            limited=True,
            check="length",
            nonzero=True,
        )
        self.text_h = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            style=wx.TE_PROCESS_ENTER,
            limited=True,
            check="length",
            nonzero=True,
        )
        self.context.setting(bool, "lock_active", True)
        self.btn_lock_ratio = wxToggleButton(self, wx.ID_ANY, "")
        self.bitmap_locked = mkicons.icons8_lock.GetBitmap(
            resize=mkicons.STD_ICON_SIZE * self.context.root.bitmap_correction_scale / 2, use_theme=False
        )
        self.bitmap_unlocked = mkicons.icons8_unlock.GetBitmap(
            resize=mkicons.STD_ICON_SIZE * self.context.root.bitmap_correction_scale/ 2, use_theme=False
        )
        self.btn_lock_ratio.bitmap_toggled = self.bitmap_locked
        self.btn_lock_ratio.bitmap_untoggled = self.bitmap_unlocked
        self.btn_lock_ratio.SetValue(self.context.lock_active)

        self.__set_properties()
        self.__do_layout()

        self.text_x.SetActionRoutine(self.on_text_x_enter)
        self.text_y.SetActionRoutine(self.on_text_y_enter)
        self.text_w.SetActionRoutine(self.on_text_w_enter)
        self.text_h.SetActionRoutine(self.on_text_h_enter)
        self.btn_lock_ratio.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle_ratio)

        self.set_widgets(self.node)

    def __do_layout(self):
        # begin wxGlade: PositionPanel.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_h = StaticBoxSizer(self, wx.ID_ANY, _("Height:"), wx.HORIZONTAL)
        sizer_w = StaticBoxSizer(self, wx.ID_ANY, _("Width:"), wx.HORIZONTAL)
        sizer_opt = wx.BoxSizer(wx.VERTICAL)
        sizer_y = StaticBoxSizer(self, wx.ID_ANY, "Y:", wx.HORIZONTAL)
        sizer_x = StaticBoxSizer(self, wx.ID_ANY, "X:", wx.HORIZONTAL)

        sizer_x.Add(self.text_x, 1, wx.EXPAND, 0)
        sizer_y.Add(self.text_y, 1, wx.EXPAND, 0)
        sizer_w.Add(self.text_w, 1, wx.EXPAND, 0)
        sizer_h.Add(self.text_h, 1, wx.EXPAND, 0)

        self.btn_lock_ratio.SetMinSize(dip_size(self, 32, 32))
        self.btn_lock_ratio.SetToolTip(
            _("Lock the ratio of width / height to the original values")
        )

        sizer_opt.Add(self.btn_lock_ratio, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

        sizer_h_xy = wx.BoxSizer(wx.HORIZONTAL)
        sizer_h_xy.Add(sizer_x, 1, wx.EXPAND, 0)
        sizer_h_xy.Add(sizer_y, 1, wx.EXPAND, 0)

        self.sizer_h_wh = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_h_wh.Add(sizer_w, 1, wx.EXPAND, 0)
        self.sizer_h_wh.Add(sizer_h, 1, wx.EXPAND, 0)

        sizer_h_dimensions = wx.BoxSizer(wx.HORIZONTAL)

        self.sizer_v_xywh = wx.BoxSizer(wx.VERTICAL)
        self.sizer_v_xywh.Add(sizer_h_xy, 0, wx.EXPAND, 0)
        self.sizer_v_xywh.Add(self.sizer_h_wh, 0, wx.EXPAND, 0)
        sizer_h_dimensions.Add(self.sizer_v_xywh, 1, wx.EXPAND, 0)
        sizer_h_dimensions.Add(sizer_opt, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_main.Add(sizer_h_dimensions, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()

    def __set_properties(self):
        # begin wxGlade: PositionPanel.__set_properties
        self.text_h.SetToolTip(_("New height (enter to apply)"))
        self.text_w.SetToolTip(_("New width (enter to apply)"))
        self.text_x.SetToolTip(
            _("New X-coordinate of left top corner (enter to apply)")
        )
        self.text_y.SetToolTip(
            _("New Y-coordinate of left top corner (enter to apply)")
        )

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def signal(self, signalstr, myargs):
        # To get updates about translation / scaling of selected elements
        if signalstr == "refresh_scene":
            if myargs[0] == "Scene":
                self.set_widgets(self.node)
        elif signalstr == "modified_by_tool":
            self.set_widgets(self.node)
        elif signalstr == "lock_active":
            if self.btn_lock_ratio.GetValue() != self.context.lock_active:
                self.btn_lock_ratio.SetValue(self.context.lock_active)

    def _set_widgets_hidden(self):
        self.text_x.SetValue("")
        self.text_y.SetValue("")
        self.text_w.SetValue("")
        self.text_h.SetValue("")
        self.Hide()

    def show_hide_wh(self, displaythem):
        self.text_w.Show(show=displaythem)
        self.text_h.Show(show=displaythem)
        self.sizer_h_wh.ShowItems(displaythem)
        self.sizer_v_xywh.Layout()
        self.Layout()

    def set_widgets(self, node):
        self.node = node
        try:
            bb = node.bounds
        except:
            # Node is none or bounds threw an error.
            bb = None

        if bb is None:
            # Bounds was genuinely none, or node threw an error.
            self._set_widgets_hidden()
            return

        en_xy = self.node.can_move(self.context.elements.lock_allows_move)
        en_wh = self.node.can_scale
        x = bb[0]
        y = bb[1]
        w = bb[2] - bb[0]
        h = bb[3] - bb[1]
        units = self.context.units_name
        if units in ("inch", "inches"):
            units = "in"

        self.text_x.SetValue(
            f"{Length(amount=x, preferred_units=units, digits=4).preferred_length}"
        )
        self.text_y.SetValue(
            f"{Length(amount=y, preferred_units=units, digits=4).preferred_length}"
        )
        self.text_w.SetValue(
            f"{Length(amount=w, preferred_units=units, digits=4).preferred_length}"
        )
        self.text_h.SetValue(
            f"{Length(amount=h, preferred_units=units, digits=4).preferred_length}"
        )
        self.text_x.Enable(en_xy)
        self.text_y.Enable(en_xy)
        self.text_w.Enable(en_wh)
        self.text_h.Enable(en_wh)
        self.show_hide_wh(node.type != "elem point")
        self.Refresh()
        self.Show()

    def translate_it(self):
        if not self.node.can_move(self.context.elements.lock_allows_move):
            return
        bb = self.node.bounds
        try:
            newx = float(Length(self.text_x.GetValue()))
            newy = float(Length(self.text_y.GetValue()))
        except (ValueError, AttributeError):
            return
        dx = newx - bb[0]
        dy = newy - bb[1]
        if dx != 0 or dy != 0:
            self.node.matrix.post_translate(dx, dy)
            # self.node.modified()
            self.node.translated(dx, dy)
            self.context.elements.signal("element_property_update", self.node)
            self.context.elements.signal("refresh_scene", "Scene")

    def scale_it(self, was_width):
        if not self.node.can_scale:
            return
        bb = self.node.bounds
        keep_ratio = self.btn_lock_ratio.GetValue()
        try:
            neww = float(Length(self.text_w.GetValue()))
            newh = float(Length(self.text_h.GetValue()))
        except (ValueError, AttributeError):
            return
        if bb[2] != bb[0]:
            sx = neww / (bb[2] - bb[0])
        else:
            sx = 1
        if bb[3] != bb[1]:
            sy = newh / (bb[3] - bb[1])
        else:
            sy = 1
        if keep_ratio:
            if was_width:
                sy = sx
            else:
                sx = sy
        if sx != 1.0 or sy != 1.0:
            self.node.matrix.post_scale(sx, sy, bb[0], bb[1])
            self.node.scaled(sx=sx, sy=sy, ox=bb[0], oy=bb[1])
            # self.node.modified()
            bb = self.node.bounds
            w = bb[2] - bb[0]
            h = bb[3] - bb[1]
            units = self.context.units_name
            if units in ("inch", "inches"):
                units = "in"
            self.text_w.SetValue(
                f"{Length(amount=w, preferred_units=units, digits=4).preferred_length}"
            )
            self.text_h.SetValue(
                f"{Length(amount=h, preferred_units=units, digits=4).preferred_length}"
            )

            self.context.elements.signal("element_property_update", self.node)
            self.context.elements.signal("refresh_scene", "Scene")

    def on_toggle_ratio(self, event):
        self.btn_lock_ratio.update_button(None)
        if self.context.lock_active != self.btn_lock_ratio.GetValue():
            self.context.lock_active = self.btn_lock_ratio.GetValue()
            self.context.signal("lock_active")

    def on_text_x_enter(self):
        self.translate_it()

    def on_text_y_enter(self):
        self.translate_it()

    def on_text_w_enter(self):
        self.scale_it(True)

    def on_text_h_enter(self):
        self.scale_it(False)


class PreventChangePanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node
        self.check_lock = wxCheckBox(self, wx.ID_ANY, _("Lock element"))
        self.__set_properties()
        self.__do_layout()
        self.check_lock.Bind(wx.EVT_CHECKBOX, self.on_check_lock)
        self.set_widgets(self.node)

    def __do_layout(self):
        # begin wxGlade: PositionPanel.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_lock = StaticBoxSizer(
            self, wx.ID_ANY, _("Prevent changes:"), wx.HORIZONTAL
        )
        sizer_lock.Add(self.check_lock, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_main.Add(sizer_lock, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()

    def __set_properties(self):
        self.check_lock.SetToolTip(
            _(
                "If active then this element is effectively prevented from being modified"
            )
        )

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def _set_widgets_hidden(self):
        self.Hide()

    def set_widgets(self, node):
        self.node = node
        if hasattr(self.node, "lock"):
            self.check_lock.Enable(True)
            self.check_lock.SetValue(self.node.lock)
        else:
            self.check_lock.SetValue(False)
            self.check_lock.Enable(False)
        self.Show()

    def on_check_lock(self, event):
        flag = self.check_lock.GetValue()
        if hasattr(self.node, "lock"):
            self.node.lock = flag
            self.context.elements.signal("element_property_update", self.node)
            self.set_widgets(self.node)


class RoundedRectPanel(wx.Panel):
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
        self.node = node
        self.fonts = []

        main_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Rounded Corners"), wx.HORIZONTAL
        )
        sizer_x = StaticBoxSizer(self, wx.ID_ANY, _("X:"), wx.HORIZONTAL)
        sizer_y = StaticBoxSizer(self, wx.ID_ANY, _("Y:"), wx.HORIZONTAL)
        # Wxpython seems to have issues with drawing a roundedrect with values
        # beyond 50%, so let's limit it (makes sense anyway)..
        self.slider_x = wx.Slider(
            self,
            wx.ID_ANY,
            value=0,
            minValue=0,
            maxValue=50,
            style=wx.SL_LABELS | wx.SL_HORIZONTAL,
        )
        self.slider_x.SetToolTip(_("Ratio of X-Radius compared to width (in %)"))

        self.slider_y = wx.Slider(
            self,
            wx.ID_ANY,
            value=0,
            minValue=0,
            maxValue=50,
            style=wx.SL_LABELS | wx.SL_HORIZONTAL,
        )
        self.slider_y.SetToolTip(_("Ratio of Y-Radius compared to height (in %)"))
        self.btn_lock_ratio = wxToggleButton(self, wx.ID_ANY, "")
        self.btn_lock_ratio.SetValue(True)
        self.btn_lock_ratio.SetMinSize(dip_size(self, 32, 32))
        self.btn_lock_ratio.SetToolTip(_("Lock the radii of X- and Y-axis"))
        # Set Bitmap
        self.bitmap_locked = mkicons.icons8_lock.GetBitmap(
            resize=mkicons.STD_ICON_SIZE * self.context.root.bitmap_correction_scale/ 2, use_theme=False
        )
        self.bitmap_unlocked = mkicons.icons8_unlock.GetBitmap(
            resize=mkicons.STD_ICON_SIZE * self.context.root.bitmap_correction_scale/ 2, use_theme=False
        )

        sizer_x.Add(self.slider_x, 1, wx.EXPAND, 0)
        sizer_y.Add(self.slider_y, 1, wx.EXPAND, 0)
        sizer_y.Add(self.btn_lock_ratio, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        main_sizer.Add(sizer_x, 1, wx.EXPAND, 0)
        main_sizer.Add(sizer_y, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()
        self.set_widgets(self.node)
        self.slider_x.Bind(wx.EVT_SLIDER, self.on_slider_x)
        self.slider_y.Bind(wx.EVT_SLIDER, self.on_slider_y)
        self.btn_lock_ratio.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle_ratio)
        self.set_widgets(node)

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def accepts(self, node):
        if node.type == "elem rect":
            return True
        else:
            return False

    def set_widgets(self, node):
        self.node = node
        # print(f"set_widget for {self.attribute} to {str(node)}")
        if self.node is None or not self.accepts(node):
            self.Hide()
            return
        # Set values for rx and ry
        bb = self.node.bbox()
        width = self.node.width
        height = self.node.height
        if self.node.rx is None:
            rx = 0
        else:
            rx = self.node.rx
        if self.node.ry is None:
            ry = 0
        else:
            ry = self.node.ry
        flag = bool(rx == ry)
        self.btn_lock_ratio.SetValue(flag)
        self.on_toggle_ratio(None)
        if width == 0:
            int_rx = 0
        else:
            int_rx = int(100.0 * rx / width)

        if height == 0:
            int_ry = 0
        else:
            int_ry = int(100.0 * ry / height)

        max_val_x = self.slider_x.GetMax()
        max_val_y = self.slider_x.GetMax()
        self.slider_x.SetValue(min(max_val_x, int_rx))
        self.slider_y.SetValue(min(max_val_y, int_ry))
        self.Show()

    def set_values(self, axis, value):
        sync = self.btn_lock_ratio.GetValue()
        width = self.node.width
        height = self.node.height
        rx = self.node.rx
        ry = self.node.ry
        if axis == 0:
            rx = value / 100 * width
            if sync:
                ry = rx
        else:
            ry = value / 100 * height
            if sync:
                rx = ry
        # rx and ry can either both be 0 or both non-zero
        if (rx == 0 or ry == 0) and rx != ry:
            # totally fine
            if rx == 0:
                rx = 1 / 100 * width
            if ry == 0:
                ry = 1 / 100 * height
        self.node.rx = rx
        self.node.ry = ry
        max_val_x = self.slider_x.GetMax()
        max_val_y = self.slider_y.GetMax()
        int_rx = int(100.0 * rx / width)
        int_ry = int(100.0 * ry / height)
        if self.slider_x.GetValue() != int_rx:
            self.slider_x.SetValue(min(max_val_x, int_rx))
        if self.slider_y.GetValue() != int_ry:
            self.slider_y.SetValue(min(max_val_y, int_ry))
        self.node.altered()
        self.context.elements.signal("element_property_update", self.node)
        self.context.signal("refresh_scene", "Scene")

    def on_slider_x(self, event):
        if self.node is None:
            return
        value = self.slider_x.GetValue()
        self.set_values(0, value)

    def on_slider_y(self, event):
        if self.node is None:
            return
        value = self.slider_y.GetValue()
        self.set_values(1, value)

    def on_toggle_ratio(self, event):
        if self.btn_lock_ratio.GetValue():
            self.btn_lock_ratio.SetBitmap(self.bitmap_locked)
            self.slider_y.Enable(False)
        else:
            self.btn_lock_ratio.SetBitmap(self.bitmap_unlocked)
            self.slider_y.Enable(True)

class AutoHidePanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node

        main_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Auto-Hide"), wx.HORIZONTAL)
        self.check_autohide = wxCheckBox(self, wx.ID_ANY, _("Autohide children"))
        main_sizer.Add(self.check_autohide, 1, wx.EXPAND, 0)
        self.check_autohide.SetToolTip(
            _("Toggle the adoption behaviour of the effect.")
            + "\n"
            + _("Active: Added children will be automatically hidden, so only the result of the effect will be seen/burned")
            + "\n"
            + _("Inactive: Added children remain unchanged, so both the child and the result of the effect will be seen/burned")
        )
        self.check_autohide.Bind(wx.EVT_CHECKBOX, self.on_autohide)
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()
        self.set_widgets(self.node)

    def on_autohide(self, event):
        if self.node is None:
            return
        flag = self.check_autohide.GetValue()
        self.node.autohide = flag
        for e in self.node.children:
            if hasattr(e, "hidden"):
                e.hidden = flag
        self.context.signal("refresh_scene", "Scene")
        self.context.signal("element_property_update", self.node.children)

    def accepts(self, node):
        return hasattr(node, "autohide")

    def set_widgets(self, node):
        self.node = node
        if node is None:
            self.check_autohide.SetValue(False)
            self.check_autohide.Enable(False)
        else:
            self.check_autohide.SetValue(self.node.autohide)
            self.check_autohide.Enable(True)

    def pane_hide(self):
        pass

    def pane_show(self):
        pass
