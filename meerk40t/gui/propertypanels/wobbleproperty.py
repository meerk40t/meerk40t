import wx

from meerk40t.gui.wxutils import ScrolledPanel, StaticBoxSizer

from ...core.units import Length
from ..wxutils import TextCtrl, set_ctrl_value, wxCheckBox, wxComboBox
from .attributes import AutoHidePanel, ColorPanel, IdPanel

_ = wx.GetTranslation


class WobblePropertyPanel(ScrolledPanel):
    name = _("Wobble")

    def __init__(self, *args, context=None, node=None, **kwds):
        # super().__init__(parent)
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.context.setting(
            bool, "_auto_classify", self.context.elements.classify_on_color
        )
        self.node = node

        self.operation = node
        self.SetHelpText("wobbles")
        self.choices = [
            {
                "attr": "loop_continuous",
                "object": self.operation,
                "default": False,
                "type": bool,
                "label": _("Loop Continuously"),
                "tip": _("Operation job will run forever in a loop"),
            },
            {
                "attr": "loop_enabled",
                "object": self.operation,
                "default": False,
                "type": bool,
                "label": _("Loop Parameter"),
                "tip": _("Operation job should run set number of times"),
            },
            {
                "attr": "loop_n",
                "object": self.operation,
                "default": 1,
                "type": int,
                "conditional": (self.operation, "loop_enabled"),
                "label": _("Loop"),
                "trailing": _("times"),
                "tip": _("How many times should the operation job loop"),
            },
        ]
        # self.panel = ChoicePropertyPanel(
        #    self, wx.ID_ANY, context=context, choices=self.choices
        # )

        main_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Wobble:"), wx.VERTICAL)
        self.panels = []
        # `Id` at top in all cases...
        panel_id = IdPanel(self, id=wx.ID_ANY, context=self.context, node=self.node)
        main_sizer.Add(panel_id, 1, wx.EXPAND, 0)
        self.panels.append(panel_id)

        panel_hide = AutoHidePanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        main_sizer.Add(panel_hide, 1, wx.EXPAND, 0)
        self.panels.append(panel_hide)

        panel_stroke = ColorPanel(
            self,
            id=wx.ID_ANY,
            context=self.context,
            label="Stroke:",
            attribute="stroke",
            callback=self.callback_color,
            node=self.node,
        )
        main_sizer.Add(panel_stroke, 1, wx.EXPAND, 0)
        self.panels.append(panel_stroke)

        option_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer_radius = StaticBoxSizer(
            self, wx.ID_ANY, _("Wobble Radius:"), wx.HORIZONTAL
        )

        self.text_radius = TextCtrl(
            self,
            wx.ID_ANY,
            str(node.radius),
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        sizer_radius.Add(self.text_radius, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_interval = StaticBoxSizer(
            self, wx.ID_ANY, _("Wobble Interval:"), wx.HORIZONTAL
        )
        self.text_interval = TextCtrl(
            self,
            wx.ID_ANY,
            str(node.interval),
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        sizer_interval.Add(self.text_interval, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_speed = StaticBoxSizer(self, wx.ID_ANY, _("Wobble Speed:"), wx.HORIZONTAL)
        self.text_speed = TextCtrl(
            self,
            wx.ID_ANY,
            str(node.speed),
            limited=True,
            check="int",
            style=wx.TE_PROCESS_ENTER,
        )
        sizer_speed.Add(self.text_speed, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        option_sizer.Add(sizer_radius, 1, wx.EXPAND, 0)
        option_sizer.Add(sizer_interval, 1, wx.EXPAND, 0)
        option_sizer.Add(sizer_speed, 1, wx.EXPAND, 0)

        main_sizer.Add(option_sizer, 0, wx.EXPAND, 0)

        sizer_fill = StaticBoxSizer(self, wx.ID_ANY, _("Fill Style"), wx.VERTICAL)
        main_sizer.Add(sizer_fill, 6, wx.EXPAND, 0)

        self.fills = list(self.context.match("wobble", suffix=True))
        self.combo_fill_style = wxComboBox(
            self, wx.ID_ANY, choices=self.fills, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        sizer_fill.Add(self.combo_fill_style, 0, wx.EXPAND, 0)

        self.check_classify = wxCheckBox(
            self, wx.ID_ANY, _("Immediately classify after colour change")
        )
        self.check_classify.SetValue(self.context._auto_classify)
        main_sizer.Add(self.check_classify, 1, wx.EXPAND, 0)

        self.SetSizer(main_sizer)

        self.text_interval.SetToolTip(
            _("Segmentation size, the wobble pattern will be applied at every segment")
        )
        self.text_radius.SetToolTip(
            _("Wobble size, does influence the size of the wobble pattern")
        )
        self.text_speed.SetToolTip(
            _("How quickly does the wobble pattern revolve around the path")
        )
        self.combo_fill_style.SetToolTip(_("The wobble pattern to be applied"))

        self.text_radius.SetActionRoutine(self.on_text_radius)
        self.text_interval.SetActionRoutine(self.on_text_interval)
        self.text_speed.SetActionRoutine(self.on_text_speed)

        self.check_classify.Bind(wx.EVT_CHECKBOX, self.on_check_classify)

        self.Bind(wx.EVT_COMBOBOX, self.on_combo_fill, self.combo_fill_style)

        self.Layout()

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    @staticmethod
    def accepts(node):
        return node.type in ("effect wobble",)

    def set_widgets(self, node):
        for panel in self.panels:
            panel.set_widgets(node)
        self.node = node
        if self.node is None or not self.accepts(node):
            self.Hide()
            return
        i = 0
        for ht in self.fills:
            if ht == self.node.wobble_type:
                break
            i += 1
        if i == len(self.fills):
            i = 0
        self.combo_fill_style.SetSelection(i)
        set_ctrl_value(self.text_interval, str(self.node.interval))
        set_ctrl_value(self.text_radius, str(self.node.radius))
        set_ctrl_value(self.text_speed, str(self.node.speed))
        # try:
        #     # h_angle = float(self.node.wobble_speed)
        #     # self.slider_angle.SetValue(int(h_angle))
        # except ValueError:
        #     pass
        self.Show()

    def on_check_classify(self, event):
        self.context._auto_classify = self.check_classify.GetValue()

    def update_label(self):
        return

    def callback_color(self):
        self.node.altered()
        self.update_label()
        self.Refresh()
        if self.check_classify.GetValue():
            mynode = self.node
            wasemph = self.node.emphasized
            self.context("declassify\nclassify\n")
            self.context.elements.signal("tree_changed")
            self.context.elements.signal("element_property_reload", self.node)
            mynode.emphasized = wasemph
            self.set_widgets(mynode)

    def update(self):
        self.node.modified()
        self.context.elements.signal("element_property_reload", self.node)

    def on_text_radius(self):
        try:
            dist = Length(self.text_radius.GetValue()).length_mm
            if dist == self.node.radius:
                return
            self.node.radius = dist
        except ValueError:
            pass
        self.update()

    def on_text_interval(self):
        try:
            dist = Length(self.text_interval.GetValue()).length_mm
            if dist == self.node.interval:
                return
            self.node.interval = dist
        except ValueError:
            pass
        self.update()

    def on_text_speed(self):
        try:
            spd = int(self.text_speed.GetValue())
            if spd == self.node.speed:
                return
            self.node.speed = spd
        except ValueError:
            pass
        self.update()

    def on_combo_fill(self, event):  # wxGlade: HatchSettingsPanel.<event_handler>
        wobble_type = self.fills[int(self.combo_fill_style.GetSelection())]
        self.node.wobble_type = wobble_type
        self.update()
