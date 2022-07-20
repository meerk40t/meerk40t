import wx
from wx import aui

from ..kernel import signal_listener

from meerk40t.core.element_types import elem_nodes, op_nodes
from meerk40t.core.elements import Elemental
from meerk40t.gui.icons import icons8_direction_20, icons8_laser_beam_20, icons8_scatter_plot_20, icons8_padlock_50
from meerk40t.svgelements import Color
from meerk40t.gui.laserrender import swizzlecolor

_ = wx.GetTranslation


def register_panel_operation_assign(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Left()
        .MinSize(80, 110)
        .FloatingSize(120, 110)
        .Caption(_("Operations"))
        .CaptionVisible(not context.pane_lock)
        .Name("opassign")
        .Hide()
    )
    pane.dock_proportion = 80
    pane.control = OperationAssignPanel(window, wx.ID_ANY, context=context)
    pane.submenu = _("Editing")
    window.on_pane_add(pane)
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
        self.buttons = []
        self.op_nodes= []
        for idx in range(self.MAXBUTTONS):
            btn = wx.Button(self, id=wx.ID_ANY, size=(self.buttonsize, self.buttonsize))
            self.buttons.append(btn)
            self.op_nodes.append(None)
        self.chk_apply_color = wx.CheckBox(self, wx.ID_ANY, _("Assign color"))
        self.chk_all_similar = wx.CheckBox(self, wx.ID_ANY, _("Similar"))
        self.lastsize = None
        self.lastcolcount = None
        self._set_layout()
        self.set_buttons()
        self.Bind(wx.EVT_SIZE, self.on_resize)


    def on_resize (self, event):
        if self.lastsize != event.Size:
            self.lastsize = event.Size
            print ("Size: wd=%d ht=%d" % (self.lastsize[0], self.lastsize[1]))
            self._set_grid_layout(self.lastsize[0])
            self.Layout()

    def _set_layout(self):
        self.sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.sizer_options = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_buttons = wx.FlexGridSizer(cols=8)
        self.sizer_options.Add(self.chk_apply_color, 1, wx.EXPAND, 0)
        self.sizer_options.Add(self.chk_all_similar, 1, wx.EXPAND, 0)

        self.sizer_main.Add(self.sizer_options, 0, wx.EXPAND, 0)
        self.sizer_main.Add(self.sizer_buttons, 1, wx.EXPAND, 0)
        self._set_grid_layout()

        self.SetSizer(self.sizer_main)
        self.Layout()

    def _set_grid_layout(self, width = None):
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

    def _clear_old(self):
        self.chk_all_similar.Enable(False)
        self.chk_apply_color.Enable(False)
        for idx in range(self.MAXBUTTONS):
            self.buttons[idx].Show(False)
            self.buttons[idx].Enable(False)
            self.op_nodes[idx] = None

    def _set_button(self, node):
        def get_bitmap():
            def get_color():
                iconcolor = None
                background = node.color
                if background is not None:
                    c1 = Color("Black")
                    c2 = Color("White")
                    if Color.distance(background, c1)> Color.distance(background, c2):
                        iconcolor = c1
                    else:
                        iconcolor = c2
                return iconcolor, background

            iconsize = 20
            result = None,
            c = None
            if node.type in ("op raster", "op image"):
                c, d = get_color()
                result = icons8_direction_20.GetBitmap(color=c, resize=(iconsize, iconsize), noadjustment=True, keepalpha=True)
            elif node.type in ("op engrave", "op cut", "op hatch"):
                c, d = get_color()
                result = icons8_laser_beam_20.GetBitmap(color=c, resize=(iconsize, iconsize), noadjustment=True, keepalpha=True)
            elif node.type == "op dots":
                c, d = get_color()
                result = icons8_scatter_plot_20.GetBitmap(color=c, resize=(iconsize, iconsize), noadjustment=True, keepalpha=True)
            return d, result

        for idx in range(self.MAXBUTTONS):
            if node is self.op_nodes[idx]:
                col, image = get_bitmap()
                if col is not None:
                    self.buttons[idx].SetBackgroundColour(wx.Colour(swizzlecolor(col)))
                else:
                    self.buttons[idx].SetBackgroundColour(wx.LIGHT_GREY)
                if image is None:
                    self.buttons[idx].SetBitmap(wx.NullBitmap)
                else:
                    self.buttons[idx].SetBitmap(image)
                    self.buttons[idx].SetBitmapDisabled(icons8_padlock_50.GetBitmap(color=Color("Grey"), resize=(self.iconsize, self.iconsize), noadjustment=True, keepalpha=True))
                self.buttons[idx].Show(True)
                break

    def set_buttons(self):
        self._clear_old()
        for idx, node in enumerate(list(self.context.elements.flat(types=op_nodes))):
            self.op_nodes[idx] = node
            self._set_button(node)
        self._set_grid_layout()
        self.Layout()

    @signal_listener("emphasized")
    def on_emphasize_signal(self, origin, *args):
        has_emph = self.context.elements.has_emphasis()
        self.chk_all_similar.Enable(has_emph)
        self.chk_apply_color.Enable(has_emph)
        for b in self.buttons:
            b.Enable(has_emph)

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
            if isinstance(element, (tuple, list)):
                for node in element:
                    if node.type.startswith("op "):
                        self._set_button(node)
            else:
                if element.type.startswith("op "):
                    self._set_button(element)

    @signal_listener("rebuild_tree")
    @signal_listener("refresh_tree")
    def on_rebuild(self, origin, *args):
        self.set_buttons()

    @signal_listener("node_created")
    def on_create(self, origin, *args):
        were_ops = False
        if len(args) > 0:
            # Need to do all?!
            element = args[0]
            if isinstance(element, (tuple, list)):
                for node in element:
                    if node.type.startswith("op "):
                        were_ops = True
                        break
            else:
                if element.type.startswith("op "):
                    were_ops = True
        if were_ops:
            set.set_buttons()

    @signal_listener("node_destroyed")
    def on_destroy(self, origin, *args):
        self.set_buttons()
