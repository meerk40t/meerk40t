import wx

from meerk40t.core.elements.element_types import op_nodes
from meerk40t.gui.icons import (
    icons8_diagonal_20,
    icons8_direction_20,
    icons8_image_20,
    icons8_laser_beam_20,
    icons8_scatter_plot_20,
    icons8_small_beam_20,
)
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.svgelements import Color

from .statusbarwidget import StatusBarWidget

_ = wx.GetTranslation


class OperationAssignOptionWidget(StatusBarWidget):
    """
    Panel to set some options for manual operation assignment
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)
        choices = [
            _("Leave"),
            _("-> OP"),
            _("-> Elem"),
        ]
        self.combo_apply_color = wx.ComboBox(
            self.parent,
            wx.ID_ANY,
            choices=choices,
            value=choices[0],
            style=wx.CB_READONLY | wx.CB_DROPDOWN,
        )
        self.check_all_similar = wx.CheckBox(self.parent, wx.ID_ANY, _("Similar"))
        self.check_exclusive = wx.CheckBox(self.parent, wx.ID_ANY, _("Exclusive"))
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
            _(
                "Assign as well all other elements with the same stroke-color (fill-color if right-click"
            )
        )
        self.check_exclusive.SetToolTip(
            _(
                "When assigning to an operation remove all assignments of the elements to other operations"
            )
        )
        self.context.elements.setting(bool, "classify_inherit_exclusive", True)
        self.context.elements.setting(bool, "classify_all_similar", True)
        self.context.elements.setting(int, "classify_impose_default", 0)
        self.StartPopulation()
        self.check_exclusive.SetValue(self.context.elements.classify_inherit_exclusive)
        self.check_all_similar.SetValue(self.context.elements.classify_all_similar)
        value = self.context.elements.classify_impose_default
        self.combo_apply_color.SetSelection(value)
        self.EndPopulation()
        self.Add(self.combo_apply_color, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Add(self.check_all_similar, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Add(self.check_exclusive, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.check_exclusive.Bind(wx.EVT_CHECKBOX, self.on_check_exclusive)
        self.check_all_similar.Bind(wx.EVT_CHECKBOX, self.on_check_allsimilar)
        self.combo_apply_color.Bind(wx.EVT_COMBOBOX, self.on_combo_color)

    def on_combo_color(self, event):
        if not self.startup:
            value = self.combo_apply_color.GetCurrentSelection()
            self.context.elements.classify_impose_default = value

    def on_check_exclusive(self, event):
        if not self.startup:
            newval = self.check_exclusive.GetValue()
            self.context.elements.classify_inherit_exclusive = newval

    def on_check_allsimilar(self, event):
        if not self.startup:
            newval = self.check_all_similar.GetValue()
            self.context.elements.classify_all_similar = newval

    def Signal(self, signal, *args):
        if signal == "emphasized":
            self.Enable(self.context.elements.has_emphasis())


class OperationAssignWidget(StatusBarWidget):
    """
    Panel to quickly assign a laser operation to any emphasized element
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iconsize = 20
        self.buttonsize = self.iconsize + 4
        self.MAXBUTTONS = 24
        self.assign_hover = 0
        self.assign_buttons = []
        self.op_nodes = []

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)

        for __ in range(self.MAXBUTTONS):
            btn = wx.StaticBitmap(
                self.parent,
                id=wx.ID_ANY,
                size=(self.buttonsize, self.buttonsize),
                # style=wx.BORDER_RAISED,
            )
            self.assign_buttons.append(btn)
            self.op_nodes.append(None)
            btn.Bind(wx.EVT_ENTER_WINDOW, self.on_mouse_over)
            btn.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
            btn.Bind(wx.EVT_LEFT_DOWN, self.on_button_left)
            btn.Bind(wx.EVT_RIGHT_DOWN, self.on_button_right)
            self.Add(btn, 1, wx.EXPAND, 0)

    def on_button_left(self, event):
        button = event.GetEventObject()
        for idx in range(self.MAXBUTTONS):
            if button == self.assign_buttons[idx]:
                node = self.op_nodes[idx]
                self.execute_on(node, "stroke")
                break
        event.Skip()

    def on_button_right(self, event):
        button = event.GetEventObject()
        for idx in range(self.MAXBUTTONS):
            if button == self.assign_buttons[idx]:
                node = self.op_nodes[idx]
                self.execute_on(node, "fill")
                break
        event.Skip()

    def Show(self, showit=True):
        # Callback function that decides whether to show an element or not
        if showit:
            for idx, btn in enumerate(self.assign_buttons):
                if self.op_nodes[idx] is None:
                    self.SetActive(btn, False)
                else:
                    self.SetActive(btn, True)
        else:
            for btn in self.assign_buttons:
                self.SetActive(btn, False)
        self.RefreshItems(showit)

    def on_mouse_leave(self, event):
        # Leave events of one tool may come later than the enter events of the next
        self.assign_hover -= 1
        if self.assign_hover < 0:
            self.assign_hover = 0
        if self.assign_hover == 0:
            self.parent.SetStatusText("", 0)
        event.Skip()

    def on_mouse_over(self, event):
        button = event.GetEventObject()
        msg = ""
        for idx in range(self.MAXBUTTONS):
            if button == self.assign_buttons[idx]:
                msg = str(self.op_nodes[idx])
        self.assign_hover += 1
        self.parent.SetStatusText(msg, 0)
        event.Skip()

    def execute_on(self, targetop, attrib):
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

    # --------- Logic for operation assignment
    def assign_clear_old(self):
        for idx in range(self.MAXBUTTONS):
            self.op_nodes[idx] = None
            self.assign_buttons[idx].SetBitmap(wx.NullBitmap)
            self.SetActive(self.assign_buttons[idx], False)
            self.assign_buttons[idx].Show(False)
        if self.assign_hover > 0:
            self.parent.SetStatusText("", 0)
            self.assign_hover = 0

    def set_single_button(self, node):
        def get_bitmap():
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

            iconsize = 20
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

        def process_button(myidx):
            col, image = get_bitmap()
            if image is None:
                return
            if col is not None:
                self.assign_buttons[myidx].SetBackgroundColour(
                    wx.Colour(swizzlecolor(col))
                )
            else:
                self.assign_buttons[myidx].SetBackgroundColour(wx.LIGHT_GREY)
            if image is None:
                self.assign_buttons[myidx].SetBitmap(wx.NullBitmap)
            else:
                self.assign_buttons[myidx].SetBitmap(image)
                # self.assign_buttons[myidx].SetBitmapDisabled(icons8_padlock_50.GetBitmap(color=Color("Grey"), resize=(self.iconsize, self.iconsize), noadjustment=True, keepalpha=True))
            self.assign_buttons[myidx].SetToolTip(
                str(node)
                + "\n"
                + _("Assign the selected elements to the operation.")
                + "\n"
                + _("Left click: consider stroke as main color, right click: use fill")
            )
            self.assign_buttons[myidx].Show()

        lastfree = -1
        found = False
        for idx in range(self.MAXBUTTONS):
            if node is self.op_nodes[idx]:
                process_button(idx)
                found = True
                break
            else:
                if lastfree < 0 and self.op_nodes[idx] is None:
                    lastfree = idx
        if not found:
            if lastfree >= 0:
                self.op_nodes[lastfree] = node
                process_button(lastfree)

    def set_buttons(self):
        self.parent.Freeze()
        self.assign_clear_old()
        idx = 0
        for node in list(self.context.elements.flat(types=op_nodes)):
            if node is None:
                continue
            if node.type.startswith("op "):
                self.op_nodes[idx] = node
                self.set_single_button(node)
                idx += 1
                if idx >= self.MAXBUTTONS:
                    # too many...
                    break
        if self.visible:
            self.ShowItems(True)
        self.parent.Thaw()
        # We need to call reposition for the updates to be seen
        self.parent.Reposition(self.panelidx)

    def show_stuff(self, flag):
        if flag:
            self.set_buttons()

        for idx in range(self.MAXBUTTONS):
            myflag = flag and self.op_nodes[idx] is not None
            self.assign_buttons[idx].Enable(myflag)
            self.assign_buttons[idx].Enable(myflag)
        if not flag:
            if self.assign_hover > 0:
                self.parent.SetStatusText("statusmsg", 0)
                self.assign_hover = 0
        self.parent.Reposition(self.panelidx)

    def Signal(self, signal, *args):
        if signal in (
            "element_property_update",
            "element_property_reload",
            "rebuild_tree",
            "tree_changed",
        ):
            self.set_buttons()
        elif signal == "emphasized":
            self.Enable(self.context.elements.has_emphasis())
