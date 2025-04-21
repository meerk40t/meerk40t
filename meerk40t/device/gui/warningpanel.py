import wx

from meerk40t.gui.icons import (
    icon_effect_hatch,
    icon_points,
    icons8_direction,
    icons8_image,
    icons8_laser_beam,
    icons8_laserbeam_weak,
)
from meerk40t.gui.wxutils import (
    TextCtrl,
    dip_size,
    wxCheckBox,
    wxStaticBitmap,
    wxStaticText,
)
from meerk40t.kernel.kernel import signal_listener

_ = wx.GetTranslation


class WarningPanel(wx.Panel):
    """
    WarningPanel is a panel that should work for all devices (hence in its own directory)
    It allows to define Min and Max Values for Speed and Power per operation
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("warning")

        self.op_id = ("cut", "engrave", "raster", "image", "dots", "hatch")
        self.data = {}

        self.images = {
            "cut": icons8_laser_beam,
            "engrave": icons8_laserbeam_weak,
            "raster": icons8_direction,
            "image": icons8_image,
            "dots": icon_points,
            "hatch": icon_effect_hatch,
        }
        self.checkboxes = []
        self.limits = []

        for op in self.op_id:
            for attr in ("power", "speed"):
                opatt_id = op + "_" + attr
                xdata = {
                    "op": op,
                    "image": self.images[op],
                    "attr": attr,
                    "active_min": False,
                    "value_min": 0,
                    "checkbox_min": None,
                    "textcontrol_min": None,
                    "active_max": False,
                    "value_max": 0,
                    "checkbox_max": None,
                    "textcontrol_max": None,
                }
                self.data[opatt_id] = xdata

        hsizer = wx.FlexGridSizer(cols=10, gap=dip_size(self, 2, 0))
        # hsizer.SetCols(9)
        idx = -1
        self.power_as_percent = self.context.setting(
            bool, "use_percent_for_power_display", False
        )
        self.speed_as_mm_min = self.context.setting(
            bool, "use_mm_min_for_speed_display", False
        )
        for key in self.data:
            entry = self.data[key]

            min1 = None
            max1 = None
            if entry["attr"] == "power":
                if self.power_as_percent:
                    unit1 = "%"
                else:
                    unit1 = "ppi"
            else:
                if self.speed_as_mm_min:
                    unit1 = "mm/min"
                else:
                    unit1 = "mm/s"
            idx += 1
            bsize = 20 * self.context.root.bitmap_correction_scale
            image = wxStaticBitmap(self, id=wx.ID_ANY)
            image.SetBitmap(entry["image"].GetBitmap(resize=bsize))

            label1 = wxStaticText(
                self, id=wx.ID_ANY, label=_(entry["op"].capitalize())
            )

            label2 = wxStaticText(
                self, id=wx.ID_ANY, label=_(entry["attr"].capitalize())
            )

            label3 = wxStaticText(self, id=wx.ID_ANY, label="<")
            chk1 = wxCheckBox(self, id=wx.ID_ANY, label="")
            chk1.SetToolTip(_("Enable/Disable the warning level"))
            entry["checkbox_min"] = chk1

            ctrl1 = TextCtrl(
                self,
                id=wx.ID_ANY,
                style=wx.TE_PROCESS_ENTER,
                limited=True,
                check="float",
            )
            ctrl1.SetMinSize(dip_size(self, 60, -1))
            ctrl1.SetToolTip(
                _("Warn level for minimum {unit}").format(unit=_(entry["attr"]))
            )
            ctrl1.Enable(False)
            entry["textcontrol_min"] = ctrl1
            chk1.Bind(wx.EVT_CHECKBOX, self.on_checkbox_check(entry, False))
            ctrl1.SetActionRoutine(self.on_text_limit(ctrl1, entry, False))

            label4 = wxStaticText(self, id=wx.ID_ANY, label=">")
            chk2 = wxCheckBox(self, id=wx.ID_ANY, label="")
            chk2.SetToolTip(_("Enable/Disable the warning level"))
            entry["checkbox_max"] = chk2

            ctrl2 = TextCtrl(
                self,
                id=wx.ID_ANY,
                style=wx.TE_PROCESS_ENTER,
                limited=True,
                check="float",
            )
            ctrl2.SetMinSize(dip_size(self, 60, -1))
            ctrl2.SetToolTip(
                _("Warn level for maximum {unit}").format(unit=_(entry["attr"]))
            )
            ctrl2.Enable(False)
            entry["textcontrol_max"] = ctrl2
            chk2.Bind(wx.EVT_CHECKBOX, self.on_checkbox_check(entry, True))
            ctrl2.SetActionRoutine(self.on_text_limit(ctrl2, entry, True))

            label5 = wxStaticText(self, id=wx.ID_ANY, label=unit1)

            # Store the corresponding attribute for later updates
            label5.attribute = entry["attr"]

            hsizer.Add(image, 0, wx.ALIGN_CENTER_VERTICAL, 0)
            hsizer.Add(label1, 1, wx.ALIGN_CENTER_VERTICAL, 0)
            hsizer.Add(label2, 1, wx.ALIGN_CENTER_VERTICAL, 0)

            hsizer.Add(chk1, 1, wx.EXPAND, 0)
            hsizer.Add(label3, 1, wx.ALIGN_CENTER_VERTICAL, 0)
            hsizer.Add(ctrl1, 1, wx.EXPAND, 0)

            hsizer.Add(chk2, 1, wx.EXPAND, 0)
            hsizer.Add(label4, 1, wx.ALIGN_CENTER_VERTICAL, 0)
            hsizer.Add(ctrl2, 1, wx.EXPAND, 0)
            hsizer.Add(label5, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hsizer.Layout()
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        infolabel = wxStaticText(
            self,
            id=wx.ID_ANY,
            label=_(
                "Meerk40t can warn you if it believes the values for\n"
                + "power and speed are too ambitious for your machine.\n"
                + "It will display a warning indicator: '❌'\n"
                + "in the label of the associated operation-node"
            ),
        )

        sizer_main.Add(infolabel, 0, 0, 0)
        sizer_main.Add(hsizer, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)

        self.Layout()

        self.update_widgets()

    def on_checkbox_check(self, entry, isMax):
        def check(event=None):
            event.Skip()
            checkctrl = event.GetEventObject()
            active = checkctrl.GetValue()
            if isMax:
                flag = "max"
            else:
                flag = "min"
            lbl = "textcontrol_" + flag
            textctrl = entry[lbl]
            textctrl.Enable(active)

            try:
                value = float(textctrl.GetValue())
            except ValueError:
                return  # We don't update it (yet)

            self.update_settings(entry["op"], entry["attr"], flag, active, value)

        return check

    def on_text_limit(self, textctrl, entry, isMax):
        def check():
            if isMax:
                flag = "max"
            else:
                flag = "min"
            lbl = "checkbox_" + flag
            checkctrl = entry[lbl]
            active = checkctrl.GetValue()
            try:
                value = float(textctrl.GetValue())
            except ValueError:
                return  # We don't update it (yet)

            self.update_settings(entry["op"], entry["attr"], flag, active, value)

        return check

    def update_settings(self, operation, attribute, minmax, active, value):
        if minmax == "min":
            if attribute == "power":
                index = 0
            else:
                index = 4
        else:
            if attribute == "power":
                index = 2
            else:
                index = 6
        if attribute == "power" and self.power_as_percent:
            # Change to ppi
            value = value * 10.0
        if attribute == "speed" and self.speed_as_mm_min:
            # Change to mm/s
            value = value / 60.0
        label = "dangerlevel_op_" + operation
        warning = [False, 0, False, 0, False, 0, False, 0]
        if hasattr(self.context, label):
            dummy = getattr(self.context, label)
            if isinstance(dummy, (tuple, list)) and len(dummy) == len(warning):
                warning = list(dummy)
        # print ("old[%s]: %s" % (label, warning))
        anychanges = False
        if warning[index] != active:
            warning[index] = active
            anychanges = True
        if warning[index + 1] != value:
            warning[index + 1] = value
            anychanges = True
        # print ("new[%s]: %s" % (label, warning))
        if anychanges:
            setattr(self.context, label, warning)
            self.context.signal("updateop_tree")

    def update_widgets(self):
        # We intentionally reset the unit labels as a device change or setting change might have happened...
        self.power_as_percent = self.context.setting(
            bool, "use_percent_for_power_display", False
        )
        self.speed_as_mm_min = self.context.setting(
            bool, "use_mm_min_for_speed_display", False
        )
        if self.power_as_percent:
            unit1 = "%"
        else:
            unit1 = "ppi"
        if self.speed_as_mm_min:
            unit2 = "mm/min"
        else:
            unit2 = "mm/s"
        for ctrl in self.GetChildren():
            if hasattr(ctrl, "attribute"):
                if ctrl.attribute == "power":
                    if isinstance(ctrl, wx.StaticText):
                        ctrl.SetLabel(unit1)
                if ctrl.attribute == "speed":
                    if isinstance(ctrl, wx.StaticText):
                        ctrl.SetLabel(unit2)

        if self.speed_as_mm_min:
            s_factor = 60.0
        else:
            s_factor = 1.0
        if self.power_as_percent:
            p_factor = 0.1
        else:
            p_factor = 1.0
        for op in self.op_id:
            label = "dangerlevel_op_" + op
            warning = [False, 0, False, 0, False, 0, False, 0]
            if hasattr(self.context, label):
                dummy = getattr(self.context, label)
                if isinstance(dummy, (tuple, list)) and len(dummy) == len(warning):
                    warning = dummy
            ident = op + "_power"
            try:
                entry = self.data[ident]
                entry["checkbox_min"].SetValue(warning[0])
                entry["textcontrol_min"].SetValue(str(warning[1] * p_factor))
                entry["textcontrol_min"].Enable(warning[0])

                entry["checkbox_max"].SetValue(warning[2])
                entry["textcontrol_max"].SetValue(str(warning[3] * p_factor))
                entry["textcontrol_max"].Enable(warning[2])
            except KeyError:
                pass
            ident = op + "_speed"
            try:
                entry = self.data[ident]
                entry["checkbox_min"].SetValue(warning[4])
                entry["textcontrol_min"].SetValue(str(warning[5] * s_factor))
                entry["textcontrol_min"].Enable(warning[4])

                entry["checkbox_max"].SetValue(warning[6])
                entry["textcontrol_max"].SetValue(str(warning[7] * s_factor))
                entry["textcontrol_max"].Enable(warning[6])
            except KeyError:
                pass

    def pane_hide(self):
        pass

    def pane_show(self):
        self.update_widgets()

    @signal_listener("power_percent")
    @signal_listener("speed_min")
    def signal_units(self, *args):
        self.update_widgets()
