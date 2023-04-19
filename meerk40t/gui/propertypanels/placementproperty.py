"""
Display and Editing of the properties of 'place current', 'place point'
"""

import wx

from meerk40t.core.units import Angle, Length
from meerk40t.gui.propertypanels.attributes import IdPanel
from meerk40t.gui.wxutils import ScrolledPanel, StaticBoxSizer, TextCtrl, set_ctrl_value
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class PlacementPanel(wx.Panel):
    """
    Display and Editing of the properties of 'place current', 'place point'
    """

    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        prop_sizer = wx.BoxSizer(wx.HORIZONTAL)
        first_sizer = StaticBoxSizer(self, wx.ID_ANY, "", wx.HORIZONTAL)
        self.checkbox_output = wx.CheckBox(self, wx.ID_ANY, _("Enable"))
        self.checkbox_output.SetToolTip(
            _("Enable this operation for inclusion in Execute Job.")
        )
        self.checkbox_output.SetValue(1)
        first_sizer.Add(self.checkbox_output, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        info_loops = wx.StaticText(self, wx.ID_ANY, _("Loops:"))
        self.text_loops = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="int",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_loops.lower_limit = 1
        self.loop_sizer = StaticBoxSizer(self, wx.ID_ANY, "", wx.HORIZONTAL)
        self.loop_sizer.Add(info_loops, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.loop_sizer.Add(self.text_loops, 1, wx.EXPAND, 0)
        self.text_loops.SetToolTip(_("Define how often this placement will be used"))

        prop_sizer.Add(first_sizer, 1, wx.EXPAND, 0)
        prop_sizer.Add(self.loop_sizer, 1, wx.EXPAND, 0)
        main_sizer.Add(prop_sizer, 1, 0, 0)

        # X and Y
        self.pos_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Placement:"), wx.HORIZONTAL)
        info_x = wx.StaticText(self, wx.ID_ANY, _("X:"))
        self.text_x = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_x.SetToolTip(_("X-Coordinate of placement"))
        info_y = wx.StaticText(self, wx.ID_ANY, _("Y:"))
        self.text_y = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_y.SetToolTip(_("Y-Coordinate of placement"))
        self.pos_sizer.Add(info_x, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.pos_sizer.Add(self.text_x, 1, wx.EXPAND, 0)
        self.pos_sizer.Add(info_y, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.pos_sizer.Add(self.text_y, 1, wx.EXPAND, 0)
        main_sizer.Add(self.pos_sizer, 0, wx.EXPAND, 0)

        # Rotation
        self.rot_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Rotation:"), wx.HORIZONTAL)
        self.text_rot = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="angle",
            style=wx.TE_PROCESS_ENTER,
        )
        self.rot_sizer.Add(self.text_rot, 1, wx.EXPAND, 0)
        self.slider_angle = wx.Slider(self, wx.ID_ANY, 0, 0, 360)
        self.rot_sizer.Add(self.slider_angle, 3, wx.EXPAND, 0)
        main_sizer.Add(self.rot_sizer, 0, wx.EXPAND, 0)
        ttip = _(
            "The to be plotted elements can be rotated around the defined coordinate"
        )
        self.text_rot.SetToolTip(ttip)
        self.slider_angle.SetToolTip(ttip)

        # Corner

        self.corner_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Orientation:"), wx.HORIZONTAL
        )
        info_corner = wx.StaticText(self, wx.ID_ANY, _("Corner:"))
        self.combo_corner = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=[
                _("Top-Left"),
                _("Top-Right"),
                _("Bottom-Right"),
                _("Bottom-Left"),
                _("Center"),
            ],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_corner.SetToolTip(
            _(
                "The corner type establishes the placement of the bounding box\n"
                + "of to be plotted elements against the defined coordinate"
            )
        )
        self.corner_sizer.Add(info_corner, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.corner_sizer.Add(self.combo_corner, 1, wx.EXPAND, 0)
        main_sizer.Add(self.corner_sizer, 0, wx.EXPAND, 0)

        self.SetSizer(main_sizer)

        self.Layout()

        self.Bind(wx.EVT_COMBOBOX, self.on_combo_corner, self.combo_corner)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_output, self.checkbox_output)
        self.text_rot.SetActionRoutine(self.on_text_rot)
        self.text_x.SetActionRoutine(self.on_text_x)
        self.text_y.SetActionRoutine(self.on_text_y)
        self.text_loops.SetActionRoutine(self.on_text_loops)
        self.Bind(wx.EVT_COMMAND_SCROLL, self.on_slider_angle, self.slider_angle)

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def accepts(self, node):
        return node.type in (
            "place current",
            "place point",
        )

    def set_widgets(self, node):
        self.operation = node
        if self.operation is None or not self.accepts(node):
            self.Hide()
            return
        if hasattr(self.operation, "validate"):
            self.operation.validate()
        op = self.operation.type
        is_current = bool(op == "place current")
        if self.operation.output is not None:
            self.checkbox_output.SetValue(self.operation.output)
        if self.operation.output:
            flag_enabled = True
        else:
            flag_enabled = False
        self.text_rot.Enable(flag_enabled)
        self.text_x.Enable(flag_enabled)
        self.text_y.Enable(flag_enabled)
        self.text_loops.Enable(flag_enabled)
        self.slider_angle.Enable(flag_enabled)
        if is_current:
            self.pos_sizer.Show(False)
            self.rot_sizer.Show(False)
            self.corner_sizer.Show(False)
            self.loop_sizer.Show(False)
        else:
            self.loop_sizer.Show(True)
            self.pos_sizer.Show(True)
            self.rot_sizer.Show(True)
            self.corner_sizer.Show(True)
            units = self.context.units_name
            if units in ("inch", "inches"):
                units = "in"

            x = self.operation.x
            if isinstance(x, str):
                x = float(Length(x))
            if x is None:
                x = 0
            y = self.operation.y
            if isinstance(y, str):
                y = float(Length(y))
            if y is None:
                y = 0
            ang = self.operation.rotation
            myang = Angle(ang, digits=2)
            if ang is None:
                ang = 0
            loops = self.operation.loops
            if loops is None:
                loops = 1
            set_ctrl_value(self.text_loops, str(loops))
            set_ctrl_value(
                self.text_x,
                f"{Length(amount=x, preferred_units=units, digits=4).preferred_length}",
            )
            set_ctrl_value(
                self.text_y,
                f"{Length(amount=y, preferred_units=units, digits=4).preferred_length}",
            )
            set_ctrl_value(self.text_rot, f"{myang.angle_degrees}")
            try:
                h_angle = myang.degrees
                while h_angle > self.slider_angle.GetMax():
                    h_angle -= 360
                while h_angle < self.slider_angle.GetMin():
                    h_angle += 360
                self.slider_angle.SetValue(int(h_angle))
            except ValueError:
                pass
            corner = max(min(self.operation.corner, 4), 0)  # between 0 and 4
            self.combo_corner.SetSelection(corner)

        self.Layout()
        self.Show()

    def on_text_rot(self):
        if self.operation is None or not hasattr(self.operation, "rotation"):
            return
        try:
            self.operation.rotation = Angle(self.text_rot.GetValue()).angle
            self.updated()
        except ValueError:
            return
        myang = Angle(self.operation.rotation)
        try:
            h_angle = myang.degrees
            while h_angle > self.slider_angle.GetMax():
                h_angle -= 360
            while h_angle < self.slider_angle.GetMin():
                h_angle += 360
            self.slider_angle.SetValue(int(h_angle))
        except ValueError:
            pass

    def on_slider_angle(self, event):  # wxGlade: HatchSettingsPanel.<event_handler>
        if self.operation is None or not hasattr(self.operation, "rotation"):
            return
        value = self.slider_angle.GetValue()
        self.text_rot.SetValue(f"{value}deg")
        self.on_text_rot()

    def on_check_output(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        if self.operation.output != bool(self.checkbox_output.GetValue()):
            self.operation.output = bool(self.checkbox_output.GetValue())
            self.context.elements.signal("element_property_update", self.operation)
        flag = self.operation.output
        self.text_x.Enable(flag)
        self.text_y.Enable(flag)
        self.text_rot.Enable(flag)
        self.slider_angle.Enable(flag)
        self.combo_corner.Enable(flag)

    def on_combo_corner(self, event):
        if self.operation is None or not hasattr(self.operation, "corner"):
            return
        corner = self.combo_corner.GetSelection()
        if corner < 0:
            return
        if self.operation.corner != corner:
            self.operation.corner = corner
            self.updated()

    def on_text_x(self):
        if self.operation is None or not hasattr(self.operation, "x"):
            return
        try:
            x = float(Length(self.text_x.GetValue()))
        except ValueError:
            return
        if self.operation.x != x:
            self.operation.x = x
            self.updated()

    def on_text_y(self):
        if self.operation is None or not hasattr(self.operation, "y"):
            return
        try:
            y = float(Length(self.text_y.GetValue()))
        except ValueError:
            return
        if self.operation.y != y:
            self.operation.y = y
            self.updated()

    def on_text_loops(self):
        if self.operation is None or not hasattr(self.operation, "loops"):
            return
        try:
            loops = int(self.text_loops.GetValue())
            if loops < 1:
                loops = 1
        except ValueError:
            return
        if self.operation.loops != loops:
            self.operation.loops = loops
            self.updated()

    def updated(self):
        self.context.elements.signal("element_property_update", self.operation)
        self.context.elements.signal("refresh_scene", "Scene")


class PlacementParameterPanel(ScrolledPanel):
    name = _("Properties")
    priority = -1

    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: ParameterPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node
        self.panels = []

        param_sizer = wx.BoxSizer(wx.VERTICAL)

        self.id_panel = IdPanel(
            self,
            wx.ID_ANY,
            context=context,
            node=node,
            showid=False,
        )
        param_sizer.Add(self.id_panel, 0, wx.EXPAND, 0)
        self.panels.append(self.id_panel)

        self.place_panel = PlacementPanel(self, wx.ID_ANY, context=context, node=node)
        param_sizer.Add(self.place_panel, 0, wx.EXPAND, 0)
        self.panels.append(self.place_panel)

        self.SetSizer(param_sizer)

        self.Layout()
        # end wxGlade

    @signal_listener("element_property_reload")
    def on_element_property_reload(self, origin=None, *args):
        # Is this something I should care about?
        # element_property_reload provides a list of nodes that are affected
        # if self.operation isn't one of them, then we just let it slip
        for_me = False
        if len(args) > 0:
            element = args[0]
            if isinstance(element, (tuple, list)):
                for node in element:
                    if node == self.operation:
                        for_me = True
                        break
            elif self.operation == element:
                for_me = True
        if not for_me:
            return

        self.set_widgets(self.operation)
        self.Layout()

    def set_widgets(self, node):
        self.operation = node
        for panel in self.panels:
            panel.set_widgets(node)

    def pane_hide(self):
        for panel in self.panels:
            panel.pane_hide()

    def pane_show(self):
        for panel in self.panels:
            panel.pane_show()
