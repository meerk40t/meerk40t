import wx
from wx import aui

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

from ..kernel import signal_listener

_ = wx.GetTranslation


def register_panel_operation_assign(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Left()
        .MinSize(80, 60)
        .FloatingSize(80, 85)
        .Caption(_("Operations"))
        .CaptionVisible(not context.pane_lock)
        .Name("opassign")
        .Hide()
    )
    pane.dock_proportion = 80
    pane.control = OperationAssignPanel(window, wx.ID_ANY, context=context)
    pane.submenu = "_50_" + _("Tools")
    window.on_pane_create(pane)
    context.register("pane/opassign", pane)


class OperationAssignPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: OperationAssignPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.iconsize = 20
        self.buttonsize = self.iconsize + 10
        self.context = context
        self.MAXBUTTONS = 24
        self.hover = 0
        self.buttons = []
        self.op_nodes = []
        for idx in range(self.MAXBUTTONS):
            btn = wx.Button(self, id=wx.ID_ANY, size=(self.buttonsize, self.buttonsize))
            self.buttons.append(btn)
            self.op_nodes.append(None)

        choices = [
            _("Leave"),
            _("-> OP"),
            _("-> Elem"),
        ]
        self.cbo_apply_color = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=choices,
            value=choices[0],
            style=wx.CB_READONLY | wx.CB_DROPDOWN,
        )
        self.chk_all_similar = wx.CheckBox(self, wx.ID_ANY, _("Similar"))
        self.chk_exclusive = wx.CheckBox(self, wx.ID_ANY, _("Exclusive"))
        self.cbo_apply_color.SetToolTip(
            _(
                "Leave - neither the color of the operation nor of the elements will be changed"
            )
            + "\n"
            + _("-> OP - the assigned operation will adopt the color of the element")
            + "\n"
            + _("-> Elem - the elements will adopt the color of the assigned operation")
        )
        self.chk_all_similar.SetToolTip(
            _("Assign as well all other elements with the same stroke-color,")
            + "\n"
            + _("respectively with the same fill-color if you right-click the button")
        )
        self.chk_exclusive.SetToolTip(
            _(
                "When assigning to an operation remove all assignments of the elements to other operations"
            )
        )
        self.lastsize = None
        self.lastcolcount = None
        self._set_layout()
        self.set_buttons()
        self.Bind(wx.EVT_SIZE, self.on_resize)
        for idx in range(self.MAXBUTTONS):
            self.buttons[idx].Bind(wx.EVT_ENTER_WINDOW, self.on_mouse_over)
            self.buttons[idx].Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
            self.buttons[idx].Bind(wx.EVT_BUTTON, self.on_button_left)
            self.buttons[idx].Bind(wx.EVT_RIGHT_DOWN, self.on_button_right)
        self.chk_exclusive.Bind(wx.EVT_CHECKBOX, self.on_chk_exclusive)
        self.show_stuff(False)

    def _set_layout(self):
        self.sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.sizer_options = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_buttons = wx.FlexGridSizer(cols=8)
        self.sizer_options.Add(self.cbo_apply_color, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.sizer_options.Add(self.chk_all_similar, 1, wx.EXPAND, 0)
        self.sizer_options.Add(self.chk_exclusive, 1, wx.EXPAND, 0)

        self.sizer_main.Add(self.sizer_options, 0, wx.EXPAND, 0)
        self.sizer_main.Add(self.sizer_buttons, 1, wx.EXPAND, 0)
        self._set_grid_layout()

        self.SetSizer(self.sizer_main)
        self.Layout()

    def _set_grid_layout(self, width=None):
        # Compute the columns
        if width is None:
            cols = 6
        else:
            cols = int(width / self.buttonsize)
            if cols < 2:
                cols = 2
        if self.lastcolcount is None or self.lastcolcount != cols:
            self.lastcolcount = cols
            self.sizer_buttons.Clear()
            self.sizer_buttons.SetCols(self.lastcolcount)

            for idx in range(self.MAXBUTTONS):
                if self.op_nodes[idx] is not None:
                    self.sizer_buttons.Add(self.buttons[idx], 1, wx.EXPAND, 0)
            self.sizer_buttons.SetCols(self.lastcolcount)

    def _clear_old(self):
        for idx in range(self.MAXBUTTONS):
            self.op_nodes[idx] = None
            self.buttons[idx].SetBitmap(wx.NullBitmap)
            self.buttons[idx].Show(False)
        if self.hover > 0:
            self.context.signal("statusmsg", "")
            self.hover = 0

    def _set_button(self, node):
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
                self.buttons[myidx].SetBackgroundColour(wx.Colour(swizzlecolor(col)))
            else:
                self.buttons[myidx].SetBackgroundColour(wx.LIGHT_GREY)
            if image is None:
                self.buttons[myidx].SetBitmap(wx.NullBitmap)
            else:
                self.buttons[myidx].SetBitmap(image)
                # self.buttons[myidx].SetBitmapDisabled(icons8_padlock_50.GetBitmap(color=Color("Grey"), resize=(self.iconsize, self.iconsize), noadjustment=True, keepalpha=True))
            self.buttons[myidx].SetToolTip(
                str(node)
                + "\n"
                + _("Assign the selected elements to the operation.")
                + "\n"
                + _("Left click: consider stroke as main color, right click: use fill")
            )
            self.buttons[myidx].Show()

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

    def set_buttons(self, skip_layout=False):
        self._clear_old()
        idx = 0
        for node in list(self.context.elements.flat(types=op_nodes)):
            if node.type.startswith("op "):
                self.op_nodes[idx] = node
                self._set_button(node)
                idx += 1
                if idx >= self.MAXBUTTONS:
                    # too many...
                    break
        self._set_grid_layout()
        if not skip_layout:
            self.Layout()

    def show_stuff(self, flag):
        if flag:
            self.set_buttons(skip_layout=True)
        self.chk_all_similar.Enable(flag)
        self.cbo_apply_color.Enable(flag)
        self.chk_exclusive.Enable(flag)

        for idx in range(self.MAXBUTTONS):
            myflag = flag and self.op_nodes[idx] is not None
            self.buttons[idx].Enable(myflag)
            self.buttons[idx].Enable(myflag)
        if not flag:
            if self.hover > 0:
                self.context.signal("statusmsg", "")
                self.hover = 0
        else:
            self.chk_exclusive.SetValue(
                self.context.elements.classify_inherit_exclusive
            )
        siz = self.GetSize()
        self._set_grid_layout(siz[0])
        self.sizer_options.Layout()
        self.sizer_buttons.Layout()
        self.sizer_main.Layout()
        self.Layout()

    @signal_listener("emphasized")
    def on_emphasize_signal(self, origin, *args):
        has_emph = self.context.elements.has_emphasis()
        self.show_stuff(has_emph)

    @signal_listener("element_property_reload")
    @signal_listener("element_property_update")
    def on_element_update(self, origin, *args):
        """
        Called by 'element_property_update' when the properties of an element are changed.

        @param origin: the path of the originating signal
        @param args:
        @return:
        """
        if len(args) > 0:
            # Need to do all?!
            element = args[0]
            if element is None:
                return
            if isinstance(element, (tuple, list)):
                for node in element:
                    if node is None or node.type is None:
                        continue
                    if node.type.startswith("op "):
                        self._set_button(node)
            else:
                if element.type is None:
                    return
                if element.type.startswith("op "):
                    self._set_button(element)

    @signal_listener("rebuild_tree")
    @signal_listener("refresh_tree")
    @signal_listener("tree_changed")
    @signal_listener("operation_removed")
    @signal_listener("add_operation")
    def on_rebuild(self, origin, *args):
        self.set_buttons()

    def pane_show(self, *args):
        # nothing yet
        return

    def pane_hide(self, *args):
        # nothing yet
        return

    def on_resize(self, event):
        if self.lastsize != event.Size:
            self.lastsize = event.Size
            # print ("Size: wd=%d ht=%d" % (self.lastsize[0], self.lastsize[1]))
            self._set_grid_layout(self.lastsize[0])
            self.Layout()
        event.Skip()

    def on_mouse_leave(self, event):
        # Leave events of one tool may come later than the enter events of the next
        self.hover -= 1
        if self.hover < 0:
            self.hover = 0
        if self.hover == 0:
            self.context.signal("statusmsg", "")
        event.Skip()

    def on_mouse_over(self, event):
        button = event.GetEventObject()
        msg = ""
        for idx in range(self.MAXBUTTONS):
            if button == self.buttons[idx]:
                msg = str(self.op_nodes[idx])
        self.hover += 1
        self.context.signal("statusmsg", msg)
        event.Skip()

    def execute_on(self, targetop, attrib):
        data = list(self.context.elements.flat(emphasized=True))
        idx = self.cbo_apply_color.GetCurrentSelection()
        if idx == 1:
            impose = "to_op"
        elif idx == 2:
            impose = "to_elem"
        else:
            impose = None
        similar = self.chk_all_similar.GetValue()
        exclusive = self.chk_exclusive.GetValue()
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

    def on_button_left(self, event):
        button = event.GetEventObject()
        for idx in range(self.MAXBUTTONS):
            if button == self.buttons[idx]:
                node = self.op_nodes[idx]
                self.execute_on(node, "stroke")
                break
        event.Skip()

    def on_button_right(self, event):
        button = event.GetEventObject()
        for idx in range(self.MAXBUTTONS):
            if button == self.buttons[idx]:
                node = self.op_nodes[idx]
                self.execute_on(node, "fill")
                break
        event.Skip()

    def on_chk_exclusive(self, event):
        newval = self.chk_exclusive.GetValue()
        self.context.elements.classify_inherit_exclusive = newval

    # def debug_vis(self, msg):
    #     vis = 0
    #     for idx in range(self.MAXBUTTONS):
    #         if self.buttons[idx].IsShown():
    #             vis += 1
    #     print ("Visible Buttons at stage %s: %d" % (msg, vis))
