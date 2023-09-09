import wx

from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.core.node.op_image import ImageOpNode

from meerk40t.gui.icons import EmptyIcon
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.svgelements import Color

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
        self.op_nodes = []
        self.positions = []
        self.page_size = 0
        self.first_to_show = 0

    def init_nodes(self):
        def next_color(primary, secondary, tertiary, delta=32):
            secondary += delta
            if secondary > 255:
                secondary = 0
                primary -= delta
            if primary < 0:
                primary = 255
                tertiary += delta
            if tertiary > 255:
                tertiary = 0
            return primary, secondary, tertiary

        def create_cut():
            # Cut op
            idx = 0
            blue = 0
            green = 0
            red = 255
            for speed in (1, 2, 5):
                for power in (1000,):
                    idx += 1
                    op_label = f"Cut ({power/10:.0f}%, {speed}mm/s)"
                    op_id = f"C{idx:01d}"
                    op = CutOpNode(label=op_label, id=op_id, speed=speed, power=power)
                    op.color = Color(red=red, blue=blue, green=green)
                    red, blue, green = next_color(red, blue, green, delta=64)
                    # print(f"Next for cut: {red} {blue} {green}")
                    op.allowed_attributes = ["stroke"]
                    oplist.append(op)

        def create_engrave():
            # Engrave op
            idx = 0
            blue = 255
            green = 0
            red = 0
            for speed in (20, 35, 50):
                for power in (1000, 750, 500):
                    idx += 1
                    op_label = f"Engrave ({power/10:.0f}%, {speed}mm/s)"
                    op_id = f"E{idx:01d}"
                    op = EngraveOpNode(
                        label=op_label, id=op_id, speed=speed, power=power
                    )
                    op.color = Color(red=red, blue=blue, green=green)
                    blue, green, red = next_color(blue, green, red, delta=24)
                    # print(f"Next for engrave: {red} {blue} {green}")
                    op.allowed_attributes = ["stroke"]
                    oplist.append(op)

        def create_raster():
            # Raster op
            idx = 0
            blue = 0
            green = 255
            red = 0
            for speed in (250, 200, 150, 100, 75):
                for power in (1000,):
                    idx += 1
                    op_label = f"Raster ({power/10:.0f}%, {speed}mm/s)"
                    op_id = f"R{idx:01d}"
                    op = RasterOpNode(
                        label=op_label, id=op_id, speed=speed, power=power
                    )
                    op.color = Color(red=red, blue=blue, green=green, delta=60)
                    green, red, blue = next_color(green, red, blue)
                    # print(f"Next for raster: {red} {blue} {green}")
                    op.allowed_attributes = ["fill"]
                    oplist.append(op)

        def create_image():
            # Image op
            idx = 0
            blue = 0
            green = 0
            red = 0
            for speed in (250, 200, 150, 100, 75):
                for power in (1000,):
                    idx += 1
                    op_label = f"Image ({power/10:.0f}%, {speed}mm/s)"
                    op_id = f"I{idx:01d}"
                    op = ImageOpNode(label=op_label, id=op_id, speed=speed, power=power)
                    op.color = Color(red=red, blue=blue, green=green, delta=48)
                    green, blue, red = next_color(green, red, blue)
                    # print(f"Next for Image: {red} {blue} {green}")

                    oplist.append(op)

        oplist = self.context.elements.load_persistent_op_list("_default")
        needs_save = False
        if len(oplist) == 0:
            # Then let's create something useful
            create_cut()
            create_engrave()
            create_raster()
            create_image()
            needs_save = True
        # Ensure we have an id for everything
        for opidx, opnode in enumerate(oplist):
            if opnode.id is None:
                opnode.id = f"{opidx:01d}"
                needs_save = True
        if needs_save:
            self.context.elements.save_persistent_operations_list("_default", oplist)

        self.op_nodes = oplist

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

        self.init_nodes()
        self.assign_buttons.clear()
        for idx, op in enumerate(self.op_nodes):
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
                node = self.op_nodes[idx]
                self.execute_on(node)
                break
            idx += 1

    def Show(self, showit=True):
        # Callback function that decides whether to show an element or not
        if showit:
            self.page_size = int((self.width - 2 * self.buttonsize_x) / self.buttonsize_y)
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
                # dbg = f"Check btn {idx} ({self.op_nodes[idx].id}): x={x}, w={w}"
                btnflag = False
                if not residual:
                    if self.op_nodes[idx] is None:
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
        data = list(self.context.elements.flat(emphasized=True))
        if len(data) == 0:
            return
        emph_data = [e for e in data]
        op_id = targetop.id
        newone = True
        for op in self.context.elements.ops():
            if op.id == op_id:
                newone = False
                targetop = op
                break
        if newone:
            self.context.elements.op_branch.add_node(targetop)
        impose = "to_elem"
        similar = False
        exclusive = True
        self.context.elements.assign_operation(
            op_assign=targetop,
            data=data,
            impose=impose,
            attrib="auto",
            similar=similar,
            exclusive=exclusive,
        )
        # Let's clean non-used operations that come from defaults...
        deleted = 0
        for op in self.context.elements.ops():
            if len(op.children) == 0:
                # is this one of the default operations?
                is_default = False
                for def_op in self.op_nodes:
                    if def_op.id is not None and def_op.id == op.id:
                        # Lets check at least power and speed if they are identical
                        if def_op.speed == op.speed and def_op.power == op.power:
                            is_default = True
                            break
                if is_default:
                    deleted += 1
                    op.remove_node()
        if deleted:
            self.context.elements.signal("operation_removed")

        for e in emph_data:
            e.emphasized = True

    def show_stuff(self, flag):
        for idx in range(len(self.assign_buttons)):
            myflag = flag and self.op_nodes[idx] is not None
            self.assign_buttons[idx].Enable(myflag)

        self.parent.Reposition(self.panelidx)

    def Signal(self, signal, *args):
        if signal in ("rebuild_tree",):
            # if hasattr(self, "context") and self.context is not None:
            #     self.GenerateControls(
            #         self.parent, self.panelidx, self.identifier, self.context
            #     )
            #     self.Show(True)
            pass
        elif signal == "emphasized":
            self.Enable(self.context.elements.has_emphasis())
