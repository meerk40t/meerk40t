"""
This module provides a basic operation panel that allows to access
fundamental properties of operations. This is supposed to provide
a simpler interface to operations
"""

import wx

from meerk40t.core.elements.element_types import elem_nodes
from meerk40t.gui.laserrender import swizzlecolor

from ..kernel import Job, lookup_listener, signal_listener
from ..svgelements import Color
from .icons import (
    icon_air_off,
    icon_air_on,
    icon_ignore,
    icon_points,
    icons8_direction,
    icons8_image,
    icons8_laser_beam,
    icons8_laserbeam_weak,
)
from .wxutils import (
    ScrolledPanel,
    StaticBoxSizer,
    TextCtrl,
    create_menu,
    dip_size,
    wxButton,
    wxCheckBox,
    wxComboBox,
    wxStaticBitmap,
    wxStaticText,
)

_ = wx.GetTranslation

BUTTONSIZE = 20


class BasicOpPanel(wx.Panel):
    """
    Basic interface to show operations and assign elements to them.
    Very much like the layer concept in other laser software products
    """

    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)

        # icons for coolant-indicator
        isize = 20 * self.context.root.bitmap_correction_scale
        self.cool_icons = {
            0: icon_ignore.GetBitmap(resize=isize),
            1: icon_air_on.GetBitmap(resize=isize, color="green"),
            2: icon_air_off.GetBitmap(resize=isize, color="red"),
        }

        # Refresh logic
        self.visible = False
        self.pending_ops = dict()
        self.ignore_refill = False
        self.filtered = True
        self._refill_job = Job(
            process=self.fill_operations,
            job_name="basicops_fillop",
            interval=0.5,
            times=1,
            run_main=True,
        )
        choices = [
            _("Leave color"),
            _("Op inherits color"),
            _("Elem inherits color"),
        ]
        self.combo_apply_color = wxComboBox(
            self,
            wx.ID_ANY,
            choices=choices,
            value=choices[0],
            style=wx.CB_READONLY | wx.CB_DROPDOWN,
        )
        self.check_exclusive = wxCheckBox(self, wx.ID_ANY, _("Exclusive"))
        self.check_all_similar = wxCheckBox(self, wx.ID_ANY, _("Similar"))
        self.combo_apply_color.SetToolTip(
            _(
                "Leave - neither the color of the operation nor of the elements will be changed"
            )
            + "\n"
            + _("-> OP - the assigned operation will adopt the color of the element")
            + "\n"
            + _("-> Elem - the elements will adopt the color of the assigned operation")
        )
        self.check_all_similar.SetToolTip(
            _("Assign as well all other elements with the same stroke-color")
        )
        self.check_exclusive.SetToolTip(
            _(
                "When assigning to an operation remove all assignments of the elements to other operations"
            )
        )
        self.context.elements.setting(bool, "classify_inherit_exclusive", True)
        self.context.elements.setting(bool, "classify_all_similar", True)
        self.context.elements.setting(int, "classify_impose_default", 0)
        self.check_exclusive.SetValue(self.context.elements.classify_inherit_exclusive)
        self.check_all_similar.SetValue(self.context.elements.classify_all_similar)
        value = self.context.elements.classify_impose_default
        self.combo_apply_color.SetSelection(value)
        self.check_exclusive.Bind(wx.EVT_CHECKBOX, self.on_check_exclusive)
        self.check_all_similar.Bind(wx.EVT_CHECKBOX, self.on_check_allsimilar)
        self.combo_apply_color.Bind(wx.EVT_COMBOBOX, self.on_combo_color)

        self.btn_config = wxButton(self, wx.ID_ANY, "...")
        self.btn_config.SetMinSize(dip_size(self, 25, -1))
        self.btn_config.SetMaxSize(dip_size(self, 25, -1))
        self.btn_config.Bind(wx.EVT_BUTTON, self.on_config)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.op_panel = ScrolledPanel(self, wx.ID_ANY)
        self.context.themes.set_window_colors(self.op_panel)
        self.op_panel.SetupScrolling()
        self.operation_sizer = None
        classif_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Classification"), wx.VERTICAL
        )
        upper_sizer = wx.BoxSizer(wx.HORIZONTAL)
        upper_sizer.Add(self.combo_apply_color, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        upper_sizer.Add(self.btn_config, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        classif_sizer.Add(upper_sizer, 0, wx.EXPAND, 0)

        lower_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lower_sizer.Add(self.check_exclusive, 1, wx.EXPAND, 0)
        lower_sizer.Add(self.check_all_similar, 1, wx.EXPAND, 0)
        classif_sizer.Add(lower_sizer, 0, wx.EXPAND, 0)

        self.main_sizer.Add(self.op_panel, 1, wx.EXPAND, 0)
        self.main_sizer.Add(classif_sizer, 0, wx.EXPAND, 0)
        self.SetSizer(self.main_sizer)
        self.Layout()
        self.use_percent = False
        self.use_mm_min = False
        self.set_display()
        self.op_ctrl_list = []
        self.std_color_back = None
        self.std_color_fore = None

    def set_display(self):
        dev = self.context.device
        if dev is None:
            dev = self.context.root
        dev.setting(bool, "use_percent_for_power_display", False)
        self.use_percent = dev.use_percent_for_power_display
        dev.setting(bool, "use_mm_min_for_speed_display", False)
        self.use_mm_min = dev.use_mm_min_for_speed_display

    def on_combo_color(self, event):
        value = self.combo_apply_color.GetCurrentSelection()
        self.context.elements.classify_impose_default = value

    def on_check_exclusive(self, event):
        newval = self.check_exclusive.GetValue()
        self.context.elements.classify_inherit_exclusive = newval

    def on_check_allsimilar(self, event):
        newval = self.check_all_similar.GetValue()
        self.context.elements.classify_all_similar = newval

    def execute_single(self, targetop, attrib):
        data = list(self.context.elements.flat(emphasized=True))
        idx = self.context.elements.classify_impose_default
        if idx == 1:
            impose = "to_op"
        elif idx == 2:
            impose = "to_elem"
        else:
            impose = None
        similar = self.context.elements.classify_all_similar
        exclusive = self.context.elements.classify_inherit_exclusive
        if len(data) == 0:
            return
        self.context.elements.assign_operation(
            op_assign=targetop,
            data=data,
            impose=impose,
            attrib=attrib,
            similar=similar,
            exclusive=exclusive,
        )

    def on_config(self, event):
        mynode = self.context.elements.op_branch
        mynode.selected = True
        create_menu(self, mynode, self.context.elements)

    def fill_operations(self):
        def on_button_left(node):
            def handler(event):
                # print(f"Left for {mynode.type}")
                self.execute_single(mynode, "auto")

            mynode = node
            return handler

        def on_button_right(node):
            def handler(event):
                # print(f"Right for {mynode.type}")

                mynode.selected = True
                create_menu(self, mynode, self.context.elements)

            mynode = node
            return handler

        # def on_button_doubleclick(node):
        #     def handler(event):
        #         print(f"Double for {mynode.type}")
        #         activate = self.context.kernel.lookup(
        #             "function/open_property_window_for_node"
        #         )
        #         if activate is not None:
        #             mynode.selected = True
        #             activate(mynode)

        #     mynode = node
        #     return handler

        def on_check_show(node):
            def handler(event):
                # print(f"Show for {mynode.type}")
                cb = event.GetEventObject()
                newflag = True
                if hasattr(mynode, "output") and hasattr(mynode, "is_visible"):
                    if mynode.output is not None:
                        if not mynode.output:
                            newflag = bool(not mynode.is_visible)

                    mynode.is_visible = newflag
                    mynode.updated()
                    self.context.elements.validate_selected_area()
                    ops = [mynode]
                    self.ignore_refill = True
                    self.context.elements.signal("element_property_update", ops)
                    self.context.elements.signal("refresh_scene", "Scene")
                cb.SetValue(newflag)

            mynode = node
            return handler

        def on_check_output(node, showctrl):
            def handler(event):
                # print(f"Output for {mynode.type}")
                cb = event.GetEventObject()
                if hasattr(mynode, "output"):
                    flag_out = not mynode.output
                    try:
                        mynode.output = flag_out
                        mynode.updated()
                    except AttributeError:
                        pass
                    if flag_out:
                        myshow.SetValue(True)
                        myshow.Enable(False)
                    else:
                        myshow.Enable(True)
                    self.ignore_refill = True
                    ops = [mynode]
                    self.context.elements.signal("element_property_update", ops)
                    self.context.elements.signal("warn_state_update", "")
                    self.context.elements.signal("refresh_scene", "Scene")
                    cb.SetValue(flag_out)

            mynode = node
            myshow = showctrl
            return handler

        def on_check_cool(node):
            def handler(event):
                cb = event.GetEventObject()
                if hasattr(mynode, "coolant"):
                    value = mynode.coolant
                    if value is None:
                        value = 0
                    value += 1
                    if value > 2:
                        value = 0
                    mynode.coolant = value
                    mynode.updated()
                    ops = [mynode]
                    self.ignore_refill = True
                    self.context.elements.signal("element_property_update", ops)
                    cb.SetBitmap(self.cool_icons[mynode.coolant])

            mynode = node
            return handler

        def on_speed(node, tbox):
            def handler():
                # print(f"Speed for {mynode.type}")
                try:
                    value = float(mytext.GetValue())
                    if self.use_mm_min:
                        value /= 60
                    if mynode.speed != value:
                        mynode.speed = value
                        self.ignore_refill = True
                        self.context.elements.signal(
                            "element_property_reload", [mynode], "text_speed"
                        )
                except ValueError:
                    pass

            mynode = node
            mytext = tbox
            return handler

        def on_power(node, tbox):
            def handler():
                # print(f"Power for {mynode.type}")
                try:
                    value = float(mytext.GetValue())
                    if self.use_percent:
                        value *= 10
                    if mynode.power != value:
                        mynode.power = value
                        self.ignore_refill = True
                        self.context.elements.signal(
                            "element_property_reload", [mynode], "text_power"
                        )
                except ValueError:
                    pass

            mynode = node
            mytext = tbox
            return handler

        def on_label_single(node):
            def handler(event):
                self.context.elements.set_emphasis(None)
                for elem in mynode.children:
                    elem.selected = True
                    try:
                        if elem.node is not None:
                            elem.node.emphasized = True
                    except AttributeError:
                        # Is a structured node like hatch-effect
                        pass
                mynode.highlighted = True
                self.context.elements.signal("refresh_scene", "Scene")

            mynode = node
            return handler

        def on_label_double(node):
            def handler(event):
                activate = self.context.kernel.lookup(
                    "function/open_property_window_for_node"
                )
                if activate is not None:
                    mynode.selected = True
                    activate(mynode)

            mynode = node
            return handler

        def on_check_filtered(event):
            obj = event.GetEventObject()
            self.filtered = obj.GetValue()
            self.context.schedule(self._refill_job)

        def get_bitmap(node):
            def get_color():
                iconcolor = None
                background = node.color
                if background is not None and background.argb is not None:
                    c1 = Color("Black")
                    c2 = Color("White")
                    if Color.distance(background, c1) > Color.distance(background, c2):
                        iconcolor = c1
                    else:
                        iconcolor = c2
                return iconcolor, background

            iconsize = BUTTONSIZE
            result = None
            d = None
            if node.type == "op raster":
                c, d = get_color()
                result = icons8_direction.GetBitmap(
                    color=c,
                    resize=iconsize * self.context.root.bitmap_correction_scale,
                    noadjustment=True,
                    keepalpha=True,
                )
            elif node.type == "op image":
                c, d = get_color()
                result = icons8_image.GetBitmap(
                    color=c,
                    resize=iconsize * self.context.root.bitmap_correction_scale,
                    noadjustment=True,
                    keepalpha=True,
                )
            elif node.type == "op engrave":
                c, d = get_color()
                result = icons8_laserbeam_weak.GetBitmap(
                    color=c,
                    resize=iconsize * self.context.root.bitmap_correction_scale,
                    noadjustment=True,
                    keepalpha=True,
                )
            elif node.type == "op cut":
                c, d = get_color()
                result = icons8_laser_beam.GetBitmap(
                    color=c,
                    resize=iconsize * self.context.root.bitmap_correction_scale,
                    noadjustment=True,
                    keepalpha=True,
                )
            elif node.type == "op dots":
                c, d = get_color()
                result = icon_points.GetBitmap(
                    color=c,
                    resize=iconsize * self.context.root.bitmap_correction_scale,
                    noadjustment=True,
                    keepalpha=True,
                )
            return d, result

        if self.context.kernel.is_shutdown:
            return
        if self.operation_sizer:
            self.operation_sizer.Clear()
            self.op_panel.DestroyChildren()
        try:
            self.op_panel.Freeze()
        except RuntimeError:
            return
        self.operation_sizer = StaticBoxSizer(
            self.op_panel, wx.ID_ANY, _("Operations"), wx.VERTICAL, context=self.context,
        )
        self.op_panel.SetSizer(self.operation_sizer)
        elements = self.context.elements
        self.op_ctrl_list.clear()

        info_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.check_filtered = wxCheckBox(self.op_panel, wx.ID_ANY)
        self.check_filtered.SetToolTip(_("Suppress non-used operations"))
        self.check_filtered.SetValue(self.filtered)
        self.check_filtered.SetMinSize(
            dip_size(self, 25, -1)
        )  # 20 from button + 5 from spacer
        self.check_filtered.SetMaxSize(dip_size(self, 25, -1))
        info_sizer.Add(self.check_filtered, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.check_filtered.Bind(wx.EVT_CHECKBOX, on_check_filtered)

        header = wxStaticText(self.op_panel, wx.ID_ANY, label="A")
        self.context.themes.set_window_colors(header)
        header.SetMinSize(dip_size(self, 20, -1))
        header.SetMaxSize(dip_size(self, 20, -1))
        header.SetToolTip(_("A: Active = toggle whether the elements assigned to this operation will be burned or not"))
        info_sizer.Add(header, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        header = wxStaticText(self.op_panel, wx.ID_ANY, label="S")
        self.context.themes.set_window_colors(header)
        header.SetMinSize(dip_size(self, 20, -1))
        header.SetMaxSize(dip_size(self, 20, -1))
        header.SetToolTip(_("S: Show = if inactive then you can suppress the drawing of the assigned elements"))
        info_sizer.Add(header, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        header = wxStaticText(self.op_panel, wx.ID_ANY, label="C")
        self.context.themes.set_window_colors(header)
        header.SetMinSize(dip_size(self, 20, -1))
        header.SetMaxSize(dip_size(self, 20, -1))
        header.SetToolTip(_("C: Coolant = determines whether coolant remains / will be turned on / turned off at start of this operation"))
        info_sizer.Add(header, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        unit = " [%]" if self.use_percent else ""
        header = wxStaticText(
            self.op_panel, wx.ID_ANY, label=_("Power {unit}").format(unit=unit)
        )
        self.context.themes.set_window_colors(header)
        header.SetMaxSize(dip_size(self, 30, -1))
        header.SetMaxSize(dip_size(self, 70, -1))
        info_sizer.Add(header, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        header = wxStaticText(self.op_panel, wx.ID_ANY, label=_("Speed"))
        self.context.themes.set_window_colors(header)
        header.SetMaxSize(dip_size(self, 30, -1))
        header.SetMaxSize(dip_size(self, 70, -1))
        info_sizer.Add(header, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.operation_sizer.Add(info_sizer, 0, wx.EXPAND, 0)
        self.op_ctrl_list.clear()
        for op in list(elements.ops()):
            if op is None:
                continue
            if self.filtered and len(op.children) == 0:
                continue
            if op.type.startswith("op "):
                info = _(op.type[3:].capitalize())
                if op.label is not None:
                    info = info[0] + ": " + op.display_label()
                op_sizer = wx.BoxSizer(wx.HORIZONTAL)
                self.operation_sizer.Add(op_sizer, 0, wx.EXPAND, 0)
                btn = wxStaticBitmap(
                    self.op_panel,
                    id=wx.ID_ANY,
                    size=(BUTTONSIZE, BUTTONSIZE),
                    # style=wx.BORDER_RAISED,
                )
                col, image = get_bitmap(op)
                if image is not None:
                    pass
                if col is not None:
                    btn.SetBackgroundColour(wx.Colour(swizzlecolor(col)))
                else:
                    btn.SetBackgroundColour(wx.LIGHT_GREY)
                if image is None:
                    btn.SetBitmap(wx.NullBitmap)
                else:
                    btn.SetBitmap(image)

                btn.SetToolTip(
                    info
                    + "\n"
                    + _("Assign the selected elements to the operation.")
                    + "\n"
                    + _("Right click: Extended options for operation")
                )
                btn.SetMinSize(dip_size(self, 20, -1))
                btn.SetMaxSize(dip_size(self, 20, -1))
                # btn.Bind(wx.EVT_ENTER_WINDOW, self.on_mouse_over)
                # btn.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
                btn.Bind(wx.EVT_LEFT_DOWN, on_button_left(op))
                btn.Bind(wx.EVT_RIGHT_DOWN, on_button_right(op))
                # btn.Bind(wx.EVT_LEFT_DCLICK, on_button_doubleclick(op))
                op_sizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL, 0)

                op_sizer.AddSpacer(5)

                c_out = wxCheckBox(self.op_panel, id=wx.ID_ANY)
                c_out.SetMinSize(dip_size(self, 20, -1))
                c_out.SetMaxSize(dip_size(self, 20, -1))

                if hasattr(op, "output"):
                    flag = bool(op.output)
                    c_out.SetValue(flag)
                    showflag = not flag
                else:
                    c_out.Enable(False)
                    showflag = False
                c_out.SetToolTip(
                    info
                    + "\n"
                    + _("Enable this operation for inclusion in Execute Job.")
                )
                op_sizer.Add(c_out, 1, wx.ALIGN_CENTER_VERTICAL, 0)

                c_show = wxCheckBox(self.op_panel, id=wx.ID_ANY)
                c_show.SetMinSize(dip_size(self, 20, -1))
                c_show.SetMaxSize(dip_size(self, 20, -1))
                c_show.SetToolTip(
                    info + "\n" + _("Hide all contained elements on scene if not set.")
                )
                op_sizer.Add(c_show, 1, wx.ALIGN_CENTER_VERTICAL, 0)

                if hasattr(op, "is_visible"):
                    flag = bool(op.is_visible)
                    c_show.SetValue(flag)
                else:
                    showflag = False
                c_show.Enable(showflag)

                c_cool = wxStaticBitmap(self.op_panel, id=wx.ID_ANY)
                c_cool.SetMinSize(dip_size(self, 20, -1))
                c_cool.SetMaxSize(dip_size(self, 20, -1))

                if hasattr(op, "coolant"):
                    value = op.coolant
                    if value is None or value > 2 or value < 0:
                        value = 0
                    c_cool.SetBitmap(self.cool_icons[value])
                    c_cool.Enable(True)
                else:
                    c_cool.Enable(False)
                c_cool.SetToolTip(
                    info
                    + "\n"
                    + _("Set coolant to on/off or leave unchanged (default)")
                )
                op_sizer.Add(c_cool, 1, wx.ALIGN_CENTER_VERTICAL, 0)

                self.op_panel.Bind(wx.EVT_CHECKBOX, on_check_output(op, c_show), c_out)
                self.op_panel.Bind(wx.EVT_CHECKBOX, on_check_show(op), c_show)
                c_cool.Bind(wx.EVT_LEFT_DOWN, on_check_cool(op))

                t_power = TextCtrl(
                    self.op_panel,
                    wx.ID_ANY,
                    "",
                    limited=True,
                    check="float",
                    style=wx.TE_PROCESS_ENTER,
                    nonzero=True,
                )

                t_power.SetMinSize(dip_size(self, 30, -1))
                t_power.SetMaxSize(dip_size(self, 70, -1))
                op_sizer.Add(t_power, 1, wx.ALIGN_CENTER_VERTICAL, 0)
                if hasattr(op, "power"):
                    sval = op.power if op.power is not None else 0
                    if self.use_percent:
                        t_power.SetValue(f"{sval / 10:.0f}")
                        unit = "%"
                    else:
                        t_power.SetValue(f"{sval:.0f}")
                        unit = "ppi"
                    t_power.SetToolTip(
                        info + "\n" + _("Power ({unit})").format(unit=unit)
                    )
                else:
                    t_power.Enable(False)
                t_power.SetActionRoutine(on_power(op, t_power))

                t_speed = TextCtrl(
                    self.op_panel,
                    wx.ID_ANY,
                    "",
                    limited=True,
                    check="float",
                    style=wx.TE_PROCESS_ENTER,
                    nonzero=True,
                )
                t_speed.SetMinSize(dip_size(self, 30, -1))
                t_speed.SetMaxSize(dip_size(self, 70, -1))
                op_sizer.Add(t_speed, 1, wx.ALIGN_CENTER_VERTICAL, 0)
                if hasattr(op, "speed"):
                    sval = op.speed if op.speed is not None else 0
                    if self.use_mm_min:
                        t_speed.SetValue(f"{sval * 60:.0f}")
                        unit = "mm/min"
                    else:
                        t_speed.SetValue(f"{sval:.1f}")
                        unit = "mm/s"
                    t_speed.SetToolTip(
                        info + "\n" + _("Speed ({unit})").format(unit=unit)
                    )
                else:
                    t_speed.Enable(False)
                t_speed.SetActionRoutine(on_speed(op, t_speed))

                header = wxStaticText(
                    self.op_panel, wx.ID_ANY, label=info, style=wx.ST_ELLIPSIZE_END
                )
                header.SetToolTip(
                    info
                    + "\n"
                    + _("Click to select all contained elements on the scene.")
                    + "\n"
                    + _("Double click to open the property dialog for the operation")
                )
                header.SetMinSize(dip_size(self, 30, -1))
                header.SetMaxSize(dip_size(self, 170, -1))
                op_sizer.Add(header, 1, wx.ALIGN_CENTER_VERTICAL, 0)
                if self.std_color_back is None:
                    self.std_color_back = wx.Colour(header.GetBackgroundColour())
                    self.std_color_fore = wx.Colour(header.GetForegroundColour())
                self.op_ctrl_list.append((op, header))
                header.Bind(wx.EVT_LEFT_DOWN, on_label_single(op))
                header.Bind(wx.EVT_LEFT_DCLICK, on_label_double(op))

        self.op_panel.SetupScrolling()
        self.operation_sizer.Layout()
        self.op_panel.Layout()
        self.highlight_operations(source="fill_operations")
        self.op_panel.Thaw()
        self.op_panel.Refresh()
        # print (f"Fill operations called: {len(self.op_panel.GetChildren())}")

    def highlight_operations(self, source=None):
        # print (f"Highlighting [{source}]")
        active_ops = []
        highlight_back = wx.SystemSettings().GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        highlight_fore = wx.SystemSettings().GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        highlight_back.ChangeLightness(32)

        for elem in self.context.elements.flat(types=elem_nodes, emphasized=True):
            for op in self.context.elements.ops():
                for node in op.children:
                    if node.type == "reference":
                        node = node.node
                    if node is elem:
                        if op not in active_ops:
                            active_ops.append(op)
                        break
        # print(f"Active ops: {len(active_ops)}")
        for op, ctrl in self.op_ctrl_list:
            if op in active_ops:
                ctrl.SetBackgroundColour(highlight_back)
                ctrl.SetForegroundColour(highlight_fore)
            else:
                ctrl.SetBackgroundColour(self.std_color_back)
                ctrl.SetForegroundColour(self.std_color_fore)
            ctrl.Refresh()

    def pane_show(self, *args):
        # print ("Showing")
        self.visible = True
        if "set_display" in self.pending_ops:
            self.set_display()
        if "ask_for_refill" in self.pending_ops:
            self.ask_for_refill()
            # Ask for refill will also highlight, so no need to check this
        elif "highlight_operations" in self.pending_ops:
            self.highlight_operations(source="pane_show")

        self.pending_ops = dict()

    def pane_hide(self, *args):
        # print ("Hiding")
        self.visible = False

    @signal_listener("element_property_update")
    @signal_listener("element_property_reload")
    def signal_handler_update(self, origin, *args, **kwargs):
        if not self.visible:
            self.pending_ops["ask_for_refill"] = True
            return

        hadops = False
        if len(args) > 0:
            if isinstance(args[0], (list, tuple)):
                myl = args[0]
            else:
                if args[0] is self.context.elements.op_branch:
                    myl = list(self.context.elements.ops())
                else:
                    myl = [args[0]]
            for n in myl:
                if n.type.startswith("op "):
                    hadops = True
                    break
        # print (f"Signal elem update called {args} / {kwargs} / {len(list(self.context.elements.ops()))}")
        if hadops:
            self.ask_for_refill()

    @signal_listener("rebuild_tree")
    @signal_listener("refresh_tree")
    @signal_listener("tree_changed")
    @signal_listener("operation_removed")
    @signal_listener("add_operation")
    @signal_listener("warn_state_update")
    def signal_handler_rebuild(self, origin, *args, **kwargs):
        # print (f"Signal rebuild called {args} / {kwargs} / {len(list(self.context.elements.ops()))}")
        if not self.visible:
            # print ("Delay ask_for_refill")
            self.pending_ops["ask_for_refill"] = True
            return

        self.ask_for_refill()

    def ask_for_refill(self):
        # Endless cup
        if self.ignore_refill:
            self.ignore_refill = False
            return
        self.context.schedule(self._refill_job)

    @signal_listener("power_percent")
    @signal_listener("speed_min")
    @lookup_listener("service/device/active")
    def on_device_update(self, *args):
        if not self.visible:
            self.pending_ops["set_display"] = True
            self.pending_ops["ask_for_refill"] = True
            return

        self.set_display()
        self.ask_for_refill()

    @signal_listener("emphasized")
    def signal_handler_emphasized(self, origin, *args, **kwargs):
        if not self.IsShown():
            # print ("Delay highlight_operations")
            self.pending_ops["highlight_operations"] = True
            return
        self.context.elements.set_start_time("BasicOpPanel")
        self.highlight_operations(source="emphasized")
        self.context.elements.set_end_time("BasicOpPanel", message=f"vis={self.visible}")
