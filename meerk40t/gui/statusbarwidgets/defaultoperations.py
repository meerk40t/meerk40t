import wx

from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_image import ImageOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.gui.icons import EmptyIcon
from meerk40t.gui.laserrender import swizzlecolor

from .statusbarwidget import StatusBarWidget

_ = wx.GetTranslation


class DefaultOperationWidget(StatusBarWidget):
    """
    Panel to quickly assign a laser operation to any emphasized element
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iconsize = 32

        self.assign_buttons = []
        self.positions = []
        self.page_size = 0
        self.first_to_show = 0

    def node_label(self, node):
        if isinstance(node, CutOpNode):
            slabel = f"Cut ({node.power/10:.0f}%, {node.speed}mm/s)"
        elif isinstance(node, EngraveOpNode):
            slabel = f"Engrave ({node.power/10:.0f}%, {node.speed}mm/s)"
        elif isinstance(node, RasterOpNode):
            slabel = f"Raster ({node.power/10:.0f}%, {node.speed}mm/s)"
        elif isinstance(node, ImageOpNode):
            slabel = f"Image ({node.power/10:.0f}%, {node.speed}mm/s)"
        else:
            slabel = ""
        return slabel

    def GenerateControls(self, parent, panelidx, identifier, context):
        def size_it(ctrl, dimen_x, dimen_y):
            ctrl.SetMinSize(wx.Size(dimen_x, dimen_y))
            ctrl.SetMaxSize(wx.Size(dimen_x, dimen_y))

        super().GenerateControls(parent, panelidx, identifier, context)
        self.buttonsize_x = self.iconsize
        self.buttonsize_y = min(self.iconsize, self.height)
        self.ClearItems()
        self.btn_prev = wx.StaticBitmap(
            self.parent,
            id=wx.ID_ANY,
            size=(self.buttonsize_x, self.buttonsize_y),
            # style=wx.BORDER_RAISED,
        )
        icon = EmptyIcon(
            size=(self.iconsize, min(self.iconsize, self.height)),
            color=wx.LIGHT_GREY,
            msg="<",
            ptsize=12,
        ).GetBitmap()
        self.btn_prev.SetBitmap(icon)
        self.btn_prev.SetToolTip(_("Previous entries"))
        self.Add(self.btn_prev, 0, wx.EXPAND, 0)
        self.btn_prev.Bind(wx.EVT_LEFT_DOWN, self.on_prev)
        size_it(self.btn_prev, self.buttonsize_x, self.buttonsize_y)
        self.SetActive(self.btn_prev, False)
        self.first_to_show = 0
        self.page_size = int((self.width - 2 * self.buttonsize_x) / self.buttonsize_x)

        self.context.elements.init_default_operations_nodes()
        self.assign_buttons.clear()
        for idx, op in enumerate(self.context.elements.default_operations):
            btn = wx.StaticBitmap(
                self.parent,
                id=wx.ID_ANY,
                size=(self.buttonsize_x, self.buttonsize_y),
                # style=wx.BORDER_RAISED,
            )
            opid = op.id
            if opid is None:
                opid = ""
            fontsize = 12
            if len(opid) > 2:
                fontsize = 10
            elif len(opid) > 3:
                fontsize = 8
            elif len(opid) > 4:
                fontsize = 6

            icon = EmptyIcon(
                size=(self.iconsize, min(self.iconsize, self.height)),
                color=wx.Colour(swizzlecolor(op.color)),
                msg=opid,
                ptsize=fontsize,
            ).GetBitmap()
            btn.SetBitmap(icon)
            op_label = op.label
            if op_label is None:
                op_label = str(op)
            btn.SetToolTip(op_label)
            size_it(btn, self.buttonsize_x, self.buttonsize_y)
            self.assign_buttons.append(btn)
            btn.Bind(wx.EVT_LEFT_DOWN, self.on_button_left)
            self.Add(btn, 0, wx.EXPAND, 0)
            self.SetActive(btn, False)
        self.btn_next = wx.StaticBitmap(
            parent,
            id=wx.ID_ANY,
            size=(self.buttonsize_x, self.buttonsize_y),
            # style=wx.BORDER_RAISED,
        )
        icon = EmptyIcon(
            size=(self.iconsize, min(self.iconsize, self.height)),
            color=wx.LIGHT_GREY,
            msg=">",
            ptsize=12,
        ).GetBitmap()
        self.btn_next.SetBitmap(icon)
        self.btn_next.SetToolTip(_("Next entries"))
        size_it(self.btn_next, self.buttonsize_x, self.buttonsize_y)

        self.Add(self.btn_next, 0, wx.EXPAND, 0)
        self.SetActive(self.btn_next, False)
        self.btn_next.Bind(wx.EVT_LEFT_DOWN, self.on_next)

    def on_button_left(self, event):
        button = event.GetEventObject()
        idx = 0
        while idx < len(self.assign_buttons):
            if button is self.assign_buttons[idx]:
                node = self.context.elements.default_operations[idx]
                self.execute_on(node)
                break
            idx += 1

    def Show(self, showit=True):
        # Callback function that decides whether to show an element or not
        if showit:
            self.page_size = int(
                (self.width - 2 * self.buttonsize_x) / self.buttonsize_x
            )
            # print(f"Page-Size: {self.page_size}, width={self.width}")
            x = 0
            gap = 0
            if self.first_to_show > 0:
                self.SetActive(self.btn_prev, True)
                x = self.buttonsize_x + gap
            else:
                self.SetActive(self.btn_prev, False)

            residual = False
            for idx, btn in enumerate(self.assign_buttons):
                w = self.buttonsize_x
                # dbg = f"Check btn {idx} ({self.context.elements.default_operations[idx].id}): x={x}, w={w}"
                btnflag = False
                if not residual:
                    if self.context.elements.default_operations[idx] is None:
                        self.SetActive(btn, False)
                    else:
                        if idx < self.first_to_show:
                            btnflag = False
                        elif idx == len(self.assign_buttons) - 1:
                            # The last
                            if x + w > self.width:
                                residual = True
                                btnflag = False
                            else:
                                btnflag = True
                                x += gap + w
                        else:
                            if x + w + gap + self.buttonsize_x > self.width:
                                residual = True
                                btnflag = False
                            else:
                                btnflag = True
                                x += gap + w
                self.SetActive(btn, btnflag)
                # print(f"{dbg} -> {btnflag}")
            # print(f"Next button: {residual}")
            self.SetActive(self.btn_next, residual)

        else:
            self.SetActive(self.btn_prev, False)
            for btn in self.assign_buttons:
                self.SetActive(btn, False)
            self.SetActive(self.btn_next, False)
        self.Layout()
        self.RefreshItems(showit)

    def on_prev(self, event):
        self.first_to_show -= self.page_size
        if self.first_to_show < 0:
            self.first_to_show = 0
        self.Show(True)

    def on_next(self, event):
        self.first_to_show += self.page_size
        if self.first_to_show + self.page_size >= len(self.assign_buttons):
            self.first_to_show = len(self.assign_buttons) - self.page_size
        if self.first_to_show < 0:
            self.first_to_show = 0
        self.Show(True)

    def execute_on(self, targetop):
        data = None  # == selected elements
        self.context.elements.assign_default_operation(data, targetop)

        self.reset_tooltips()

    def show_stuff(self, flag):
        for idx in range(len(self.assign_buttons)):
            myflag = flag and self.context.elements.default_operations[idx] is not None
            self.assign_buttons[idx].Enable(myflag)

        self.parent.Reposition(self.panelidx)

    def reset_tooltips(self):
        # First reset all
        for idx, node in enumerate(self.context.elements.default_operations):
            slabel = self.node_label(node)
            if slabel:
                self.assign_buttons[idx].SetToolTip(slabel)
        oplist = list(self.context.elements.ops())
        for node in oplist:
            if node is None:
                continue
            if not hasattr(node, "id"):
                continue
            opid = node.id
            if opid:
                for idx, op in enumerate(self.context.elements.default_operations):
                    if opid == op.id:
                        slabel = self.node_label(node)
                        if slabel:
                            self.assign_buttons[idx].SetToolTip(slabel)
                        break

    def Signal(self, signal, *args):
        if signal in ("rebuild_tree",):
            self.reset_tooltips()
        elif signal == "element_property_update":
            if len(args):
                self.reset_tooltips()
        elif signal == "default_operations":
            # New default operations!
            self.GenerateControls(
                self.parent, self.panelidx, self.identifier, self.context
            )
            # Repaint
            self.show_stuff(True)
        elif signal == "emphasized":
            self.Enable(self.context.elements.has_emphasis())
