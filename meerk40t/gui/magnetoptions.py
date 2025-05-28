import wx
from wx import aui

from meerk40t.core.units import Length
from meerk40t.gui.wxutils import (
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxButton,
    wxCheckBox,
    wxComboBox,
    wxStaticText,
)
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


def register_panel_magnetoptions(window, context):
    panel = MagnetPanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(80, 125)
        .FloatingSize(120, 145)
        .Hide()
        .Caption(_("Magnet-Options"))
        .CaptionVisible(not context.pane_lock)
        .Name("magnetoptions")
    )
    pane.dock_proportion = 150
    pane.control = panel
    pane.submenu = "_40_" + _("Editing")
    pane.helptext = _("Edit magnet snapping options")

    window.on_pane_create(pane)
    context.register("pane/magnetoptions", pane)


class MagnetOptionPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("magnet")
        self.scene = getattr(self.context.root, "mainscene", None)

        # Main Sizer
        sizer_magnet = wx.BoxSizer(wx.VERTICAL)
        sizer_affection = StaticBoxSizer(
            self, wx.ID_ANY, _("Attraction areas..."), wx.HORIZONTAL
        )
        self.check_x = wxCheckBox(self, wx.ID_ANY, _("Left/Right Side"))
        self.check_x.SetToolTip(
            _("Will a magnet line attract the left/right edges of an object")
        )
        self.check_y = wxCheckBox(self, wx.ID_ANY, _("Top/Bottom Side"))
        self.check_y.SetToolTip(
            _("Will a magnet line attract the top/bottom edges of an object")
        )
        self.check_c = wxCheckBox(self, wx.ID_ANY, _("Center"))
        self.check_c.SetToolTip(_("Will a magnet line attract the center of an object"))
        sizer_affection.Add(self.check_x, 1, wx.EXPAND, 0)
        sizer_affection.Add(self.check_y, 1, wx.EXPAND, 0)
        sizer_affection.Add(self.check_c, 1, wx.EXPAND, 0)

        sizer_strength = StaticBoxSizer(
            self, wx.ID_ANY, _("Attraction strength..."), wx.HORIZONTAL
        )
        choices = [
            _("Off"),
            _("Weak"),
            _("Normal"),
            _("Strong"),
            _("Very Strong"),
            _("Enormous"),
        ]
        self.cbo_strength = wxComboBox(
            self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.cbo_strength.SetToolTip(
            _(
                "Define the attraction strength from weak (very close) to enormous (from far away)"
            )
        )
        sizer_strength.Add(self.cbo_strength, 1, wx.EXPAND, 0)

        sizer_template = StaticBoxSizer(
            self, wx.ID_ANY, _("Save/Load settings"), wx.HORIZONTAL
        )
        choices = list(self.context.kernel.keylist("magnet_config"))
        self.cbo_template = wxComboBox(
            self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN
        )
        self.cbo_template.SetToolTip(
            _("Name to save to / load from the current settings")
        )
        self.btn_load = wx.Button(self, wx.ID_ANY, _("Load"))
        self.btn_load.SetToolTip(_("Load an existing setting configuration"))
        self.btn_save = wx.Button(self, wx.ID_ANY, _("Save"))
        self.btn_load.SetToolTip(_("Save the current configuration for later reuse"))
        sizer_template.Add(self.cbo_template, 1, wx.EXPAND, 0)
        sizer_template.Add(self.btn_load, 0, wx.EXPAND, 0)
        sizer_template.Add(self.btn_save, 0, wx.EXPAND, 0)

        sizer_magnet.Add(sizer_affection, 0, wx.EXPAND, 0)
        sizer_strength_template = wx.BoxSizer(wx.HORIZONTAL)
        sizer_strength_template.Add(sizer_strength, 0, wx.EXPAND, 0)
        sizer_strength_template.Add(sizer_template, 1, wx.EXPAND, 0)

        sizer_magnet.Add(sizer_strength_template, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_magnet)
        self.Layout()

        self.Bind(wx.EVT_COMBOBOX, self.on_cbo_strength, self.cbo_strength)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_x, self.check_x)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_y, self.check_y)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_c, self.check_c)

        self.Bind(wx.EVT_TEXT, self.on_set_buttons, self.cbo_template)
        self.Bind(wx.EVT_BUTTON, self.on_save_options, self.btn_save)
        self.Bind(wx.EVT_BUTTON, self.on_set_options, self.btn_load)

    def on_set_buttons(self, event):
        flag_load = False
        flag_save = False
        o_name = self.cbo_template.GetValue()
        if o_name:
            flag_save = True
            choices = list(self.context.kernel.keylist("magnet_config"))
            flag_load = o_name in choices

        self.btn_load.Enable(flag_load)
        self.btn_save.Enable(flag_save)

    def on_check_x(self, event):
        flag = self.check_x.GetValue()
        self.scene.pane.magnet_attract_x = flag

    def on_check_y(self, event):
        flag = self.check_y.GetValue()
        self.scene.pane.magnet_attract_y = flag

    def on_check_c(self, event):
        flag = self.check_c.GetValue()
        self.scene.pane.magnet_attract_c = flag

    def on_cbo_strength(self, event):
        idx = self.cbo_strength.GetSelection()
        if idx < 0:
            return
        self.scene.pane.magnet_attraction = idx

    def get_option_string(self):
        p = self.scene.pane
        return f"{'1' if p.magnet_attract_x else '0'}{'1' if p.magnet_attract_y else '0'}{'1' if p.magnet_attract_c else '0'}{p.magnet_attraction}"

    def update_values(self):
        idx = self.scene.pane.magnet_attraction
        if 0 <= idx < len(self.cbo_strength.GetItems()):
            self.cbo_strength.SetSelection(idx)
        self.check_x.SetValue(self.scene.pane.magnet_attract_x)
        self.check_y.SetValue(self.scene.pane.magnet_attract_y)
        self.check_c.SetValue(self.scene.pane.magnet_attract_c)
        choices = list(self.context.kernel.keylist("magnet_config"))
        self.cbo_template.SetItems(choices)
        current = self.get_option_string()
        for key in choices:
            value = self.context.kernel.read_persistent(
                t=str, section="magnet_config", key=key, default=""
            )
            if value == current:
                self.cbo_template.SetValue(key)
                break

        self.on_set_buttons(None)

    def on_save_options(self, event):
        o_name = self.cbo_template.GetValue()
        if o_name is None or o_name == "":
            return
        options = self.get_option_string()
        self.context.kernel.write_persistent(
            section="magnet_config", key=o_name, value=options
        )
        self.update_values()

    def on_set_options(self, event):
        o_name = self.cbo_template.GetValue()
        if o_name is None or o_name == "":
            return
        options = self.context.kernel.read_persistent(
            t=str, section="magnet_config", key=o_name, default=""
        )
        if len(options) != 4:
            return
        p = self.scene.pane
        p.magnet_attract_x = options[0] == "1"
        p.magnet_attract_y = options[1] == "1"
        p.magnet_attract_c = options[2] == "1"
        try:
            idx = int(options[3])
            idx = min(5, idx)  # Not higher than enormous
            idx = max(0, idx)  # Not lower than off
        except ValueError:
            idx = 2
        p.magnet_attraction = idx
        self.update_values()

    def signal(self, signal_name):
        if signal_name == "magnet_options":
            self.update_values()

    def pane_show(self, *args):
        self.update_values()

    def pane_hide(self, *args):
        pass


class MagnetActionPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("magnet")
        self.scene = getattr(self.context.root, "mainscene", None)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        position_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Set single line"), wx.HORIZONTAL
        )
        label = wxStaticText(self, wx.ID_ANY, _("Position:"))
        self.txt_coord = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        self.btn_set_x = wxButton(self, wx.ID_ANY, "X")
        self.btn_set_y = wxButton(self, wx.ID_ANY, "Y")
        self.txt_coord.SetToolTip(_("Define the position of the magnet line"))
        self.btn_set_x.SetToolTip(
            _("Toggle a magnet line at the position on the X-axis")
        )
        self.btn_set_y.SetToolTip(
            _("Toggle a magnet line at the position on the Y-axis")
        )
        position_sizer.Add(label, 0, wx.EXPAND, 0)
        position_sizer.Add(self.txt_coord, 1, wx.EXPAND, 0)
        position_sizer.Add(self.btn_set_x, 0, wx.EXPAND, 0)
        position_sizer.Add(self.btn_set_y, 0, wx.EXPAND, 0)

        main_sizer.Add(position_sizer, 0, wx.EXPAND, 0)

        self.selection_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Set around selection"), wx.VERTICAL
        )
        parent = self.selection_sizer.sbox
        hor_sizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wxStaticText(parent, wx.ID_ANY, _("Horizontal"))
        hor_sizer.Add(label, 1, wx.EXPAND, 0)
        self.btn_h_min = wxButton(parent, wx.ID_ANY, _("Left"))
        self.btn_h_center = wxButton(parent, wx.ID_ANY, _("Center"))
        self.btn_h_max = wxButton(parent, wx.ID_ANY, _("Right"))
        self.btn_h_3 = wxButton(parent, wx.ID_ANY, "3")
        self.btn_h_4 = wxButton(parent, wx.ID_ANY, "4")
        self.btn_h_5 = wxButton(parent, wx.ID_ANY, "5")
        self.btn_h_min.SetToolTip(
            _("Toggle a magnet line at the left edge of the selection")
        )
        self.btn_h_center.SetToolTip(
            _("Toggle a magnet line at the horizontal center of the selection")
        )
        self.btn_h_max.SetToolTip(
            _("Toggle a magnet line at the right edge of the selection")
        )
        self.btn_h_3.SetToolTip(
            _(
                "Toggle magnet lines at 1/3 and 2/3 across the horizontal extent of the selection"
            )
        )
        self.btn_h_4.SetToolTip(
            _(
                "Toggle magnet lines at 1/4, 2/4 and 3/4 across the horizontal extent of the selection"
            )
        )
        self.btn_h_5.SetToolTip(
            _(
                "Toggle magnet lines at 1/5, 2/5, 3/5 and 4/5 across the horizontal extent of the selection"
            )
        )
        hor_sizer.Add(self.btn_h_min, 0, wx.EXPAND, 0)
        hor_sizer.Add(self.btn_h_center, 0, wx.EXPAND, 0)
        hor_sizer.Add(self.btn_h_max, 0, wx.EXPAND, 0)
        hor_sizer.Add(self.btn_h_3, 0, wx.EXPAND, 0)
        hor_sizer.Add(self.btn_h_4, 0, wx.EXPAND, 0)
        hor_sizer.Add(self.btn_h_5, 0, wx.EXPAND, 0)

        vert_sizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wxStaticText(parent, wx.ID_ANY, _("Vertical"))
        vert_sizer.Add(label, 1, wx.EXPAND, 0)
        self.btn_v_min = wxButton(parent, wx.ID_ANY, _("Top"))
        self.btn_v_center = wxButton(parent, wx.ID_ANY, _("Center"))
        self.btn_v_max = wxButton(parent, wx.ID_ANY, _("Bottom"))
        self.btn_v_3 = wxButton(parent, wx.ID_ANY, "3")
        self.btn_v_4 = wxButton(parent, wx.ID_ANY, "4")
        self.btn_v_5 = wxButton(parent, wx.ID_ANY, "5")
        self.btn_v_min.SetToolTip(
            _("Toggle a magnet line at the top edge of the selection")
        )
        self.btn_v_center.SetToolTip(
            _("Toggle a magnet line at the vertical center of the selection")
        )
        self.btn_v_max.SetToolTip(
            _("Toggle a magnet line at the bottom edge of the selection")
        )
        self.btn_v_3.SetToolTip(
            _(
                "Toggle magnet lines at 1/3 and 2/3 across the vertical extent of the selection"
            )
        )
        self.btn_v_4.SetToolTip(
            _(
                "Toggle magnet lines at 1/4, 2/4 and 3/4 across the vertical extent of the selection"
            )
        )
        self.btn_v_5.SetToolTip(
            _(
                "Toggle magnet lines at 1/5, 2/5, 3/5 and 4/5 across the vertical extent of the selection"
            )
        )
        vert_sizer.Add(self.btn_v_min, 0, wx.EXPAND, 0)
        vert_sizer.Add(self.btn_v_center, 0, wx.EXPAND, 0)
        vert_sizer.Add(self.btn_v_max, 0, wx.EXPAND, 0)
        vert_sizer.Add(self.btn_v_3, 0, wx.EXPAND, 0)
        vert_sizer.Add(self.btn_v_4, 0, wx.EXPAND, 0)
        vert_sizer.Add(self.btn_v_5, 0, wx.EXPAND, 0)
        for btn in (
            self.btn_h_3,
            self.btn_h_4,
            self.btn_h_5,
            self.btn_h_min,
            self.btn_h_center,
            self.btn_h_max,
            self.btn_v_3,
            self.btn_v_4,
            self.btn_v_5,
            self.btn_v_min,
            self.btn_v_center,
            self.btn_v_max,
        ):
            btn.SetMinSize(wx.Size(dip_size(self, 50, -1)))

        self.selection_sizer.Add(hor_sizer, 0, wx.EXPAND, 0)
        self.selection_sizer.Add(vert_sizer, 0, wx.EXPAND, 0)

        main_sizer.Add(self.selection_sizer, 0, wx.EXPAND, 0)

        sizer_actions = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_clear_all = wxButton(self, wx.ID_ANY, _("Clear all"))
        self.btn_clear_all.SetToolTip(_("Clears all magnet lines"))
        self.btn_clear_x = wxButton(self, wx.ID_ANY, _("Clear X"))
        self.btn_clear_x.SetToolTip(_("Clears magnet lines on X-axis"))
        self.btn_clear_y = wxButton(self, wx.ID_ANY, _("Clear Y"))
        self.btn_clear_y.SetToolTip(_("Clears magnet lines on Y-axis"))
        sizer_actions.Add(self.btn_clear_all, 0, wx.EXPAND, 0)
        sizer_actions.Add(self.btn_clear_x, 0, wx.EXPAND, 0)
        sizer_actions.Add(self.btn_clear_y, 0, wx.EXPAND, 0)

        main_sizer.Add(sizer_actions, 0, wx.EXPAND, 0)

        self.SetSizer(main_sizer)
        self.Layout()
        self.Bind(wx.EVT_BUTTON, self.on_toggle_x, self.btn_set_x)
        self.Bind(wx.EVT_BUTTON, self.on_toggle_y, self.btn_set_y)

        self.Bind(wx.EVT_BUTTON, self.set_edges("min", "x"), self.btn_h_min)
        self.Bind(wx.EVT_BUTTON, self.set_edges("center", "x"), self.btn_h_center)
        self.Bind(wx.EVT_BUTTON, self.set_edges("max", "x"), self.btn_h_max)
        self.Bind(wx.EVT_BUTTON, self.set_edges("min", "y"), self.btn_v_min)
        self.Bind(wx.EVT_BUTTON, self.set_edges("center", "y"), self.btn_v_center)
        self.Bind(wx.EVT_BUTTON, self.set_edges("max", "y"), self.btn_v_max)
        self.Bind(wx.EVT_BUTTON, self.set_split(3, "x"), self.btn_h_3)
        self.Bind(wx.EVT_BUTTON, self.set_split(4, "x"), self.btn_h_4)
        self.Bind(wx.EVT_BUTTON, self.set_split(5, "x"), self.btn_h_5)
        self.Bind(wx.EVT_BUTTON, self.set_split(3, "y"), self.btn_v_3)
        self.Bind(wx.EVT_BUTTON, self.set_split(4, "y"), self.btn_v_4)
        self.Bind(wx.EVT_BUTTON, self.set_split(5, "y"), self.btn_v_5)
        self.Bind(wx.EVT_BUTTON, self.on_clear_x, self.btn_clear_x)
        self.Bind(wx.EVT_BUTTON, self.on_clear_y, self.btn_clear_y)
        self.Bind(wx.EVT_BUTTON, self.on_clear_all, self.btn_clear_all)

    def toggle(self, value: float, is_x: bool):
        if is_x:
            self.scene.pane.toggle_x_magnet(value)
        else:
            self.scene.pane.toggle_y_magnet(value)
        self.context.signal("refresh_scene", "Scene")

    def toggle_text(self, is_x: bool):
        txt = self.txt_coord.GetValue()
        if not txt:
            return
        try:
            value = float(Length(txt))
        except ValueError:
            return
        self.toggle(value, is_x)

    def on_toggle_x(self, event):
        self.toggle_text(is_x=True)

    def on_toggle_y(self, event):
        self.toggle_text(is_x=False)

    def on_clear_x(self, event):
        self.scene.pane.magnet_x.clear()
        self.scene.pane.save_magnets()
        self.context.signal("refresh_scene", "Scene")

    def on_clear_y(self, event):
        self.scene.pane.magnet_y.clear()
        self.scene.pane.save_magnets()
        self.context.signal("refresh_scene", "Scene")

    def on_clear_all(self, event):
        self.scene.pane.magnet_x.clear()
        self.scene.pane.magnet_y.clear()
        self.scene.pane.save_magnets()
        self.context.signal("refresh_scene", "Scene")

    def set_edges(self, edge, axis):
        def handler(event):
            is_x = axis == "x"
            bb = self.context.elements.selected_area()
            if bb is None:
                return
            if edge == "min":
                value = bb[0] if is_x else bb[1]
            elif edge == "max":
                value = bb[2] if is_x else bb[3]
            else:
                value = (bb[0] + bb[2]) / 2 if is_x else (bb[1] + bb[3]) / 2
            self.toggle(value, is_x)

        return handler

    def set_split(self, count, axis):
        def handler(event):
            self.context(f"magnet split {axis} {count}\n")
            # if count < 1:
            #     return
            # is_x = axis == "x"
            # bb = self.context.elements.selected_area()
            # if bb is None:
            #     return
            # min_v = bb[0] if is_x else bb[1]
            # max_v = bb[2] if is_x else bb[3]
            # delta = (max_v - min_v) / count
            # value = min_v
            # while value + delta < max_v:
            #     value += delta
            #     self.toggle(value, is_x)

        return handler

    def update_values(self):
        flag = self.context.elements.has_emphasis()
        self.selection_sizer.Enable(flag)
        self.Layout()

    def pane_show(self, *args):
        self.update_values()

    def pane_hide(self, *args):
        pass

    def signal(self, signal_name):
        if signal_name == "emphasized":
            self.update_values()


class MagnetPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("magnet")
        self.notebook = wx.Notebook(self, wx.ID_ANY)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.notebook, 1, wx.EXPAND, 0)
        panel_action = MagnetActionPanel(self.notebook, wx.ID_ANY, context=self.context)
        panel_options = MagnetOptionPanel(
            self.notebook, wx.ID_ANY, context=self.context
        )
        self.panels = (panel_action, panel_options)
        self.notebook.AddPage(panel_action, _("Actions"))
        self.notebook.AddPage(panel_options, _("Options"))
        self.SetSizer(sizer_main)
        self.Layout()

    def tab_handler(self, event):
        active = self.notebook.GetCurrentPage()
        for panel in self.panels:
            if panel is active:
                panel.pane_show()
            else:
                panel.pane_hide()

    def pane_show(self, *args):
        for panel in self.panels:
            panel.pane_show(args)

    def pane_hide(self, *args):
        for panel in self.panels:
            panel.pane_hide(args)

    @signal_listener("emphasized")
    def handle_emphasized(self, origin, *args):
        for panel in self.panels:
            panel.signal("emphasized")

    @signal_listener("magnet_options")
    def handle_options(self, origin, *args):
        for panel in self.panels:
            panel.signal("magnet_options")
