import wx
from wx import aui

from meerk40t.gui.wxutils import wxButton, wxCheckBox, wxComboBox, wxStaticText, StaticBoxSizer
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


def register_panel_magnetoptions(window, context):
    panel = MagnetOptionPanel(window, wx.ID_ANY, context=context)
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

        # Main Sizer
        sizer_magnet = wx.BoxSizer(wx.VERTICAL)
        sizer_affection = StaticBoxSizer(self, wx.ID_ANY, _("Attraction areas..."), wx.HORIZONTAL)
        self.check_x = wxCheckBox(self, wx.ID_ANY, _("Left/Right Side"))
        self.check_y = wxCheckBox(self, wx.ID_ANY, _("Top/Bottom Side"))
        self.check_c = wxCheckBox(self, wx.ID_ANY, _("Center"))
        sizer_affection.Add(self.check_x, 1, wx.EXPAND, 0)
        sizer_affection.Add(self.check_y, 1, wx.EXPAND, 0)
        sizer_affection.Add(self.check_c, 1, wx.EXPAND, 0)
        
        sizer_strength = StaticBoxSizer(self, wx.ID_ANY, _("Attraction strength..."), wx.HORIZONTAL)
        choices = [
            _("Off"), 
            _("Weak"), 
            _("Normal"), 
            _("Strong"), 
            _("Very Strong"), 
            _("Enormous"), 
        ]
        self.cbo_strength = wxComboBox(self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        sizer_strength.Add(self.cbo_strength, 1, wx.EXPAND, 0)        

        sizer_template = StaticBoxSizer(self, wx.ID_ANY, _("Save/Load settings"), wx.HORIZONTAL)
        choices = list(self.context.kernel.keylist("magnet_config"))
        self.cbo_template = wxComboBox(self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN)
        self.btn_load = wx.Button(self, wx.ID_ANY, _("Load"))
        self.btn_save = wx.Button(self, wx.ID_ANY, _("Save"))
        sizer_template.Add(self.cbo_template, 1, wx.EXPAND, 0)
        sizer_template.Add(self.btn_save, 0, wx.EXPAND, 0)
        sizer_template.Add(self.btn_load, 0, wx.EXPAND, 0)

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

        sizer_magnet.Add(sizer_affection, 0, wx.EXPAND, 0)
        sizer_strength_template = wx.BoxSizer(wx.HORIZONTAL)
        sizer_strength_template.Add(sizer_strength, 0, wx.EXPAND, 0)
        sizer_strength_template.Add(sizer_template, 1, wx.EXPAND, 0)

        sizer_magnet.Add(sizer_strength_template, 0, wx.EXPAND, 0)
        sizer_magnet.Add(sizer_actions, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_magnet)
        self.Layout()
        self.scene = getattr(self.context.root, "mainscene", None)
        self.Bind(wx.EVT_COMBOBOX, self.on_cbo_strength, self.cbo_strength)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_x, self.check_x)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_y, self.check_y)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_c, self.check_c)
        self.Bind(wx.EVT_BUTTON, self.on_clear_x, self.btn_clear_x)
        self.Bind(wx.EVT_BUTTON, self.on_clear_y, self.btn_clear_y)
        self.Bind(wx.EVT_BUTTON, self.on_clear_all, self.btn_clear_all)

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
            value = self.context.kernel.read_persistent(t=str, section="magnet_config", key=key, default="")
            if value == current:
                self.cbo_template.SetValue(key)
                break
        
        self.on_set_buttons(None)

    def on_save_options(self, event):
        o_name = self.cbo_template.GetValue()
        if o_name is None or o_name == "":
            return
        options = self.get_option_string()
        self.context.kernel.write_persistent(section="magnet_config", key=o_name, value=options)
        self.update_values()

    def on_set_options(self, event):
        o_name = self.cbo_template.GetValue()
        if o_name is None or o_name == "":
            return
        options = self.context.kernel.read_persistent(t=str, section="magnet_config", key=o_name, default="")
        if len(options) != 4:
            return
        p = self.scene.pane
        p.magnet_attract_x = options[0] == "1"
        p.magnet_attract_y = options[1] == "1"
        p.magnet_attract_c = options[2] == "1"
        try:
            idx = int(options[3])
            idx = min(5, idx) # Not higher than enormous
            idx = max(0, idx) # Not lower than off
        except ValueError:
            idx = 2
        p.magnet_attraction = idx
        self.update_values()

    @signal_listener("magnet_options")
    def value_update(self, origin, *args):
        self.update_values()

    def pane_show(self, *args):
        self.update_values()

    def pane_hide(self, *args):
        pass
