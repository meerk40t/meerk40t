"""
This module provides a basic operation panel that allows to access
fundamental properties of operations. This is supposed to provide
a simpler interface to operations
"""

import wx

from meerk40t.core.elements.element_types import op_nodes
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.core.elements.element_types import elem_nodes

from ..kernel import lookup_listener, signal_listener
from ..svgelements import Color
from .icons import (
    icons8_diagonal_20,
    icons8_direction_20,
    icons8_image_20,
    icons8_laser_beam_20,
    icons8_scatter_plot_20,
    icons8_small_beam_20,
)
from .wxutils import ScrolledPanel, StaticBoxSizer, TextCtrl, create_menu
from .propertypanels.attributes import (
    PositionSizePanel,
    ColorPanel,
    PreventChangePanel,
    StrokeWidthPanel,
    LinePropPanel,
)
from .propertypanels.textproperty import TextPropertyPanel

_ = wx.GetTranslation

BUTTONSIZE = 20


class LabelPanel(wx.Panel):
    def __init__(
        self, *args, context=None, node=None, showid=True, showlabel=True, **kwds
    ):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.node = node

        self.text_label = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_id_label = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_label = StaticBoxSizer(self, wx.ID_ANY, _("Label"), wx.HORIZONTAL)
        self.sizer_label.Add(self.text_label, 1, wx.EXPAND, 0)
        self.btn_props = wx.Button(self, wx.ID_ANY, "...")
        self.btn_props.SetMaxSize(wx.Size(25, -1))
        self.btn_props.SetMinSize(wx.Size(25, -1))
        self.sizer_label.Add(self.btn_props, 0, wx.EXPAND, 0)
        sizer_id_label.Add(self.sizer_label, 1, wx.EXPAND, 0)

        self.btn_props.Bind(wx.EVT_BUTTON, self.on_button)
        main_sizer.Add(sizer_id_label, 0, wx.EXPAND, 0)

        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()
        self.text_label.SetActionRoutine(self.on_text_label_change)
        self.set_widgets(self.node)

    def on_button(self, event):
        if self.node is not None:
            self.node.selected = True
            create_menu(self, self.node, self.context.elements)

    def on_text_label_change(self):
        try:
            self.node.label = self.text_label.GetValue()
            self.context.elements.signal("element_property_reload", self.node)
        except AttributeError:
            pass

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
        vis = False
        if node is not None:

            try:
                if hasattr(self.node, "label"):
                    vis = True
                    self.text_label.SetValue(mklabel(node.label))
                    self.sizer_label.SetLabel(_("Label") + f" ({node.type})")
                self.text_label.Show(vis)
                self.sizer_label.Show(vis)
            except RuntimeWarning:
                # Could happen if the propertypanel has been destroyed
                pass

        if vis:
            self.Show()
        else:
            self.Hide()


class OperationAssignment(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.node = node
        self.ops = []
        self._ignore_event = False
        # Shall we display id / label?

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.combo_ops = wx.ComboBox(
            self, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.pic_op = wx.StaticBitmap(self, wx.ID_ANY)
        self.pic_op.SetSize(wx.Size(25, 25))

        sizer_id = StaticBoxSizer(self, wx.ID_ANY, _("Operation"), wx.HORIZONTAL)

        sizer_id.Add(self.combo_ops, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_id.Add(self.pic_op, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        main_sizer.Add(sizer_id, 0, wx.EXPAND, 0)

        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()
        self.set_widgets(self.node)
        self.combo_ops.Bind(wx.EVT_COMBOBOX, self.on_combo)

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def set_widgets(self, node):

        self.node = node
        # print(f"set_widget for {str(node)}")
        vis = False
        if node is not None:
            vis = True
            choices = [_("-Unassigned-")]
            self.ops = [None]
            realop = None
            realidx = 0
            idx = 0
            for op in self.context.elements.ops():
                if op.type.startswith("op "):
                    idx += 1
                    self.ops.append(op)
                    choices.append(str(op))
                    if realop is None:
                        for ref in op.children:
                            if node is ref.node:
                                realop = op
                                realidx = idx
                                self.pic_op.SetBackgroundColour(
                                    wx.Colour(swizzlecolor(op.color))
                                )
                                break
            self._ignore_event = True
            self.combo_ops.Clear()
            self.combo_ops.Set(choices)
            self.combo_ops.SetSelection(realidx)
            self._ignore_event = False
        if vis:
            self.Show()
        else:
            self.Hide()

    def on_combo(self, event):
        if self._ignore_event:
            return
        idx = self.combo_ops.GetSelection()
        if idx >= 0:
            targetop = self.ops[idx]
            # print(f"Target: {str(targetop)}")
            data = [self.node]

            self.context.elements.assign_operation(
                op_assign=targetop,
                data=data,
                impose="to_elem",
                attrib="stroke",
                similar=False,
                exclusive=True,
            )
        self.set_widgets(self.node)

    def accepts(self, node):
        return True


class BasicElemPanel(ScrolledPanel):
    """
    Basic interface to show elements and change basic properties.
    Very much like the layer concept in other laser software products
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ParameterPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.node = None
        self.panels = []
        self._ignore_event = False
        self.context.setting(
            bool, "_auto_classify", self.context.elements.classify_on_color
        )

        self.id_panel = LabelPanel(
            self,
            wx.ID_ANY,
            context=context,
            node=self.node,
            showid=False,
        )
        self.panels.append(self.id_panel)
        self.op_panel = OperationAssignment(
            self,
            wx.ID_ANY,
            context=context,
            node=self.node,
        )
        self.panels.append(self.op_panel)
        for property_class in self.context.lookup_all("path_attributes/.*"):
            panel = property_class(
                self, id=wx.ID_ANY, context=self.context, node=self.node
            )
            self.panels.append(panel)
        panel_text = TextPropertyPanel(
            self, wx.ID_ANY, context=self.context, node=self.node
        )
        self.panels.append(panel_text)
        panel_stroke = ColorPanel(
            self,
            id=wx.ID_ANY,
            context=self.context,
            label="Stroke:",
            attribute="stroke",
            callback=self.callback_color,
            node=self.node,
        )
        self.panels.append(panel_stroke)
        panel_fill = ColorPanel(
            self,
            id=wx.ID_ANY,
            context=self.context,
            label="Fill:",
            attribute="fill",
            callback=self.callback_color,
            node=self.node,
        )
        self.panels.append(panel_fill)

        # Next one is a placeholder...
        self.panels.append(None)
        self.check_classify = wx.CheckBox(
            self, wx.ID_ANY, _("Immediately classify after colour change")
        )
        self.check_classify.SetValue(self.context._auto_classify)

        panel_width = StrokeWidthPanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.panels.append(panel_width)
        panel_line = LinePropPanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.panels.append(panel_line)
        panel_lock = PreventChangePanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.panels.append(panel_lock)
        panel_xy = PositionSizePanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.panels.append(panel_xy)

        self.__do_layout()

    def __do_layout(self):
        # begin wxGlade: PathProperty.__do_layout
        sizer_v_main = wx.BoxSizer(wx.VERTICAL)

        for panel in self.panels:
            if panel is None:
                sizer_v_main.Add(self.check_classify, 0, wx.EXPAND, 0)
            else:
                sizer_v_main.Add(panel, 0, wx.EXPAND, 0)

        self.Bind(wx.EVT_CHECKBOX, self.on_check_classify, self.check_classify)
        self.SetSizer(sizer_v_main)
        sizer_v_main.Layout()
        self.Layout()
        self.Centre()

    def on_check_classify(self, event):
        self.context.elements._auto_classify = self.check_classify.GetValue()

    def update_label(self):
        return

    def set_widgets(self, node):
        self._ignore_event = True
        flag = False
        if node is not None:
            if hasattr(node, "stroke"):
                flag = True
            if hasattr(node, "fill"):
                flag = True
        if flag:
            self.check_classify.Show()
        else:
            self.check_classify.Hide()
        for panel in self.panels:
            if panel is not None:
                panel.set_widgets(node)
                flag = False
                if node is not None:
                    if hasattr(panel, "accepts"):
                        if panel.accepts(node):
                            flag = True
                    else:
                        flag = True
                if flag:
                    panel.Show()
                else:
                    panel.Hide()
        if node is not None:
            self.node = node
        self._ignore_event = False
        self.Layout()
        self.SetupScrolling()
        self.Refresh()

    def callback_color(self):
        self.update_label()
        self.Refresh()
        if self._ignore_event:
            return
        self.node.altered()
        if self.check_classify.GetValue():
            mynode = self.node
            wasemph = self.node.emphasized
            self.context("declassify\nclassify\n")
            self.context.elements.signal("tree_changed")
            self.context.elements.signal("element_property_update", self.node)
            mynode.emphasized = wasemph
            self.set_widgets(mynode)

    def update_node(self, message):
        # print(f"Update_node called by {message}")
        self.node = None
        ct = 0
        more_than_one = False
        for e in self.context.elements.flat(types=elem_nodes, emphasized=True):
            self.node = e
            ct += 1
            if ct > 1:
                self.node = None
                more_than_one = True
                break

        self.set_widgets(self.node)

    # @signal_listener("refresh_scene")
    # def on_refresh_scene(self, origin, scene_name=None, *args):
    #     if scene_name == "Scene":
    #         self.update_node("refresh_scene")

    @signal_listener("tool_modified")
    @signal_listener("emphasized")
    def on_modified(self, *args):
        self.update_node("tool_modified/emphasized")

    @signal_listener("element_property_reload")
    @signal_listener("element_property_update")
    def on_element_update(self, origin, *args):
        """
        Called by 'element_property_update' when the properties of an element are changed.

        @param origin: the path of the originating signal
        @param args:
        @return:
        """
        flag = False
        if len(args) > 0:
            if isinstance(args[0], (tuple, list)):
                for p in args[0]:
                    if p is self.node:
                        flag = True
                        break
            elif self.node is args[0]:
                flag = True

        if flag:
            self.update_node("property update/reload")


class BasicOpPanel(wx.Panel):
    """
    Basic interface to show operations and assign elements to them.
    Very much like the layer concept in other laser software products
    """

    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        choices = [
            _("Leave color"),
            _("Op inherits color"),
            _("Elem inherits color"),
        ]
        self.combo_apply_color = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=choices,
            value=choices[0],
            style=wx.CB_READONLY | wx.CB_DROPDOWN,
        )
        self.check_exclusive = wx.CheckBox(self, wx.ID_ANY, _("Exclusive"))
        self.check_all_similar = wx.CheckBox(self, wx.ID_ANY, _("Similar"))
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

        self.btn_config = wx.Button(self, wx.ID_ANY, "...")
        self.btn_config.SetMinSize(wx.Size(25, -1))
        self.btn_config.SetMaxSize(wx.Size(25, -1))
        self.btn_config.Bind(wx.EVT_BUTTON, self.on_config)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.op_panel = ScrolledPanel(self, wx.ID_ANY)
        self.op_panel.SetupScrolling()
        self.operation_sizer = None

        option_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Options"), wx.HORIZONTAL)
        option_sizer.Add(self.combo_apply_color, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        option_sizer.Add(self.check_exclusive, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        option_sizer.Add(self.check_all_similar, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        option_sizer.Add(self.btn_config, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.main_sizer.Add(self.op_panel, 1, wx.EXPAND, 0)
        self.main_sizer.Add(option_sizer, 0, wx.EXPAND, 0)
        self.SetSizer(self.main_sizer)
        self.Layout()
        self.use_percent = False
        self.use_mm_min = False
        self.set_display()
        # self.fill_operations()

    def set_display(self):
        self.context.device.setting(bool, "use_percent_for_power_display", False)
        self.use_percent = self.context.device.use_percent_for_power_display
        self.context.device.setting(bool, "use_mm_min_for_speed_display", False)
        self.use_mm_min = self.context.device.use_mm_min_for_speed_display

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
                self.execute_single(mynode, "stroke")

            mynode = node
            return handler

        def on_button_right(node):
            def handler(event):
                # print(f"Right for {mynode.type}")

                mynode.selected = True
                create_menu(self, mynode, self.context.elements)
                # self.execute_single(mynode, "fill")

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
                    self.context.elements.signal("element_property_update", ops)
                    self.context.elements.signal("refresh_scene", "Scene")
                cb.SetValue(newflag)

            mynode = node
            return handler

        def on_check_output(node):
            def handler(event):
                # print(f"Output for {mynode.type}")
                cb = event.GetEventObject()
                flag = False
                if hasattr(mynode, "output"):
                    flag = not mynode.output
                    try:
                        mynode.output = flag
                        mynode.updated()
                    except AttributeError:
                        pass
                    ops = [mynode]
                    self.context.elements.signal("element_property_update", ops)
                    self.context.elements.signal("warn_state_update", "")
                    cb.SetValue(flag)

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
                    if node.power != value:
                        node.power = value
                        self.context.elements.signal(
                            "element_property_reload", [node], "text_power"
                        )
                except ValueError:
                    pass

            mynode = node
            mytext = tbox
            return handler

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
                result = icons8_direction_20.GetBitmap(
                    color=c,
                    resize=(iconsize, iconsize),
                    noadjustment=True,
                    keepalpha=True,
                )
            elif node.type == "op image":
                c, d = get_color()
                result = icons8_image_20.GetBitmap(
                    color=c,
                    resize=(iconsize, iconsize),
                    noadjustment=True,
                    keepalpha=True,
                )
            elif node.type == "op engrave":
                c, d = get_color()
                result = icons8_small_beam_20.GetBitmap(
                    color=c,
                    resize=(iconsize, iconsize),
                    noadjustment=True,
                    keepalpha=True,
                )
            elif node.type == "op cut":
                c, d = get_color()
                result = icons8_laser_beam_20.GetBitmap(
                    color=c,
                    resize=(iconsize, iconsize),
                    noadjustment=True,
                    keepalpha=True,
                )
            elif node.type == "op hatch":
                c, d = get_color()
                result = icons8_diagonal_20.GetBitmap(
                    color=c,
                    resize=(iconsize, iconsize),
                    noadjustment=True,
                    keepalpha=True,
                )
            elif node.type == "op dots":
                c, d = get_color()
                result = icons8_scatter_plot_20.GetBitmap(
                    color=c,
                    resize=(iconsize, iconsize),
                    noadjustment=True,
                    keepalpha=True,
                )
            return d, result

        if self.operation_sizer:
            self.operation_sizer.Clear()
            self.op_panel.DestroyChildren()
        self.op_panel.Freeze()
        self.operation_sizer = StaticBoxSizer(
            self.op_panel, wx.ID_ANY, _("Operations"), wx.VERTICAL
        )
        self.op_panel.SetSizer(self.operation_sizer)
        elements = self.context.elements

        info_sizer = wx.BoxSizer(wx.HORIZONTAL)
        header = wx.StaticText(self.op_panel, wx.ID_ANY, label=_("Operation"))
        header.SetMinSize(wx.Size(50, -1))
        header.SetMaxSize(wx.Size(90, -1))
        info_sizer.Add(header, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        header = wx.StaticText(self.op_panel, wx.ID_ANY, label=_("Active"))
        header.SetMinSize(wx.Size(30, -1))
        header.SetMaxSize(wx.Size(50, -1))
        info_sizer.Add(header, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        header = wx.StaticText(self.op_panel, wx.ID_ANY, label=_("Show"))
        header.SetMinSize(wx.Size(30, -1))
        header.SetMaxSize(wx.Size(50, -1))
        info_sizer.Add(header, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        header = wx.StaticText(self.op_panel, wx.ID_ANY, label=_("Power"))
        header.SetMaxSize(wx.Size(30, -1))
        header.SetMaxSize(wx.Size(70, -1))
        info_sizer.Add(header, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        header = wx.StaticText(self.op_panel, wx.ID_ANY, label=_("Speed"))
        header.SetMaxSize(wx.Size(30, -1))
        header.SetMaxSize(wx.Size(70, -1))
        info_sizer.Add(header, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.operation_sizer.Add(info_sizer, 0, wx.EXPAND, 0)

        for op in elements.flat(types=op_nodes):
            if op is None:
                continue
            if op.type.startswith("op "):
                op_sizer = wx.BoxSizer(wx.HORIZONTAL)
                self.operation_sizer.Add(op_sizer, 0, wx.EXPAND, 0)
                btn = wx.StaticBitmap(
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
                    # self.assign_buttons[myidx].SetBitmapDisabled(icons8_padlock_50.GetBitmap(color=Color("Grey"), resize=(self.iconsize, self.iconsize), noadjustment=True, keepalpha=True))
                btn.SetToolTip(
                    str(op)
                    + "\n"
                    + _("Assign the selected elements to the operation.")
                    + "\n"
                    + _("Right click: Extended options for operation")
                )
                btn.SetMinSize(wx.Size(20, -1))
                btn.SetMaxSize(wx.Size(20, -1))

                # btn.Bind(wx.EVT_ENTER_WINDOW, self.on_mouse_over)
                # btn.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
                btn.Bind(wx.EVT_LEFT_DOWN, on_button_left(op))
                btn.Bind(wx.EVT_RIGHT_DOWN, on_button_right(op))
                # btn.Bind(wx.EVT_LEFT_DCLICK, on_button_doubleclick(op))
                op_sizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL, 0)
                info = op.type[3:].capitalize()
                if op.label is not None:
                    info = info[0] + ": " + op.label
                header = wx.StaticText(
                    self.op_panel, wx.ID_ANY, label=info, style=wx.ST_ELLIPSIZE_END
                )
                header.SetMinSize(wx.Size(30, -1))
                header.SetMaxSize(wx.Size(70, -1))
                op_sizer.Add(header, 1, wx.ALIGN_CENTER_VERTICAL, 0)

                c_out = wx.CheckBox(self.op_panel, id=wx.ID_ANY)
                c_out.SetMinSize(wx.Size(30, -1))
                c_out.SetMaxSize(wx.Size(50, -1))
                self.op_panel.Bind(wx.EVT_CHECKBOX, on_check_output(op), c_out)
                if hasattr(op, "output"):
                    flag = bool(op.output)
                    c_out.SetValue(flag)
                    showflag = not flag
                else:
                    c_out.Enable(False)
                    showflag = False
                c_out.SetToolTip(
                    _("Enable this operation for inclusion in Execute Job.")
                )
                op_sizer.Add(c_out, 1, wx.ALIGN_CENTER_VERTICAL, 0)

                c_show = wx.CheckBox(self.op_panel, id=wx.ID_ANY)
                c_show.SetMinSize(wx.Size(30, -1))
                c_show.SetMaxSize(wx.Size(50, -1))
                c_show.SetToolTip(_("Hide all contained elements on scene if not set."))
                self.op_panel.Bind(wx.EVT_CHECKBOX, on_check_show(op), c_show)
                if hasattr(op, "is_visible"):
                    flag = bool(op.is_visible)
                    c_show.SetValue(flag)
                else:
                    showflag = False
                c_show.Enable(showflag)
                op_sizer.Add(c_show, 1, wx.ALIGN_CENTER_VERTICAL, 0)

                t_power = TextCtrl(
                    self.op_panel,
                    wx.ID_ANY,
                    "",
                    limited=True,
                    check="float",
                    style=wx.TE_PROCESS_ENTER,
                    nonzero=True,
                )

                t_power.SetMinSize(wx.Size(30, -1))
                t_power.SetMaxSize(wx.Size(70, -1))
                op_sizer.Add(t_power, 1, wx.ALIGN_CENTER_VERTICAL, 0)
                if hasattr(op, "power"):
                    if op.power is not None:
                        sval = op.power
                    else:
                        sval = 0
                    if self.use_percent:
                        t_power.SetValue(f"{sval / 10:.0f}%")
                        unit = "%"
                    else:
                        t_power.SetValue(f"{sval:.0f}")
                        unit = "ppi"
                    t_power.SetToolTip(_("Power ({unit})").format(unit=unit))
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
                t_speed.SetMinSize(wx.Size(30, -1))
                t_speed.SetMaxSize(wx.Size(70, -1))
                op_sizer.Add(t_speed, 1, wx.ALIGN_CENTER_VERTICAL, 0)
                if hasattr(op, "speed"):
                    if op.speed is not None:
                        sval = op.speed
                    else:
                        sval = 0
                    if self.use_mm_min:
                        t_speed.SetValue(f"{sval * 60:.0f}")
                        unit = "mm/min"
                    else:
                        t_speed.SetValue(f"{sval:.1f}")
                        unit = "mm/s"
                    t_speed.SetToolTip(_("Speed ({unit})").format(unit=unit))
                else:
                    t_speed.Enable(False)
                t_speed.SetActionRoutine(on_speed(op, t_speed))

        self.op_panel.SetupScrolling()
        self.operation_sizer.Layout()
        self.op_panel.Layout()
        self.op_panel.Thaw()
        self.op_panel.Refresh()
        # print (f"Fill operations called: {len(self.op_panel.GetChildren())}")

    def pane_show(self, *args):
        # self.fill_operations()
        pass

    def pane_hide(self, *args):
        pass

    @signal_listener("element_property_update")
    def signal_handler_update(self, origin, *args, **kwargs):
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
            self.fill_operations()

    @signal_listener("element_property_reload")
    def signal_handler_reload(self, origin, *args, **kwargs):
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
        # print (f"Signal elem reload called {args} / {kwargs} / {len(list(self.context.elements.ops()))}")
        if hadops:
            self.fill_operations()

    @signal_listener("rebuild_tree")
    def signal_handler_rebuild(self, origin, *args, **kwargs):
        # print (f"Signal rebuild called {args} / {kwargs} / {len(list(self.context.elements.ops()))}")
        self.fill_operations()

    @signal_listener("tree_changed")
    def signal_handler_tree(self, origin, *args, **kwargs):
        # print (f"Signal tree changed called {args} / {kwargs} / {len(list(self.context.elements.ops()))}")
        self.fill_operations()

    @signal_listener("power_percent")
    @signal_listener("speed_min")
    @lookup_listener("service/device/active")
    def on_device_update(self, *args):
        self.set_display()
        self.fill_operations()
