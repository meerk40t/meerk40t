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
        self.buttonsize = self.iconsize + 4

        self.assign_buttons = []
        self.op_nodes = []

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
                    op_id = f"C{idx:02d}"
                    op = CutOpNode(label=op_label, id=op_id, speed=speed, power=power)
                    op.color = Color(red=red, blue=blue, green=green)
                    red, blue, green = next_color(red, blue, green, delta=48)
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
                    op_id = f"E{idx:02d}"
                    op = EngraveOpNode(
                        label=op_label, id=op_id, speed=speed, power=power
                    )
                    op.color = Color(red=red, blue=blue, green=green)
                    blue, green, red = next_color(blue, green, red)
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
                    op_id = f"R{idx:02d}"
                    op = RasterOpNode(
                        label=op_label, id=op_id, speed=speed, power=power
                    )
                    op.color = Color(red=red, blue=blue, green=green, delta=48)
                    green, red, blue = next_color(green, red, blue)
                    # print(f"Next for raster: {red} {blue} {green}")
                    op.allowed_attributes = ["fill"]
                    oplist.append(op)

        def create_image():
            # Image op
            idx = 0
            blue = 255
            green = 255
            red = 255
            for speed in (250, 200, 150, 100, 75):
                for power in (1000,):
                    idx += 1
                    op_label = f"Image ({power/10:.0f}%, {speed}mm/s)"
                    op_id = f"I{idx:02d}"
                    op = ImageOpNode(label=op_label, id=op_id, speed=speed, power=power)
                    op.color = Color(red=red, blue=blue, green=green, delta=48)
                    green, red, blue = next_color(green, red, blue)
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
        for idx, op in enumerate(oplist):
            if op.id is None:
                op.id = f"{idx:02d}"
                needs_save = True
        if needs_save:
            self.context.elements.save_persistent_operations_list("_default", oplist)

        self.op_nodes = oplist

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)
        self.init_nodes()
        self.assign_buttons.clear()
        for idx, op in enumerate(self.op_nodes):
            btn = wx.StaticBitmap(
                self.parent,
                id=wx.ID_ANY,
                size=(self.buttonsize, self.buttonsize),
                # style=wx.BORDER_RAISED,
            )
            icon = EmptyIcon(
                size=self.iconsize,
                color=wx.Colour(swizzlecolor(op.color)),
                msg=op.id,
                ptsize=9,
            ).GetBitmap()
            btn.SetBitmap(icon)
            op_label = op.label
            if op_label is None:
                op_label = str(op)
            btn.SetToolTip(op_label)

            self.assign_buttons.append(btn)
            btn.Bind(wx.EVT_LEFT_DOWN, self.on_button_left)
            self.Add(btn, 0, 0, 0)

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
            for idx, btn in enumerate(self.assign_buttons):
                if self.op_nodes[idx] is None:
                    self.SetActive(btn, False)
                else:
                    self.SetActive(btn, True)
        else:
            for btn in self.assign_buttons:
                self.SetActive(btn, False)
        self.RefreshItems(showit)

    def execute_on(self, targetop):
        data = list(self.context.elements.flat(emphasized=True))
        if len(data) == 0:
            return

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

    def show_stuff(self, flag):
        for idx in range(len(self.assign_buttons)):
            myflag = flag and self.op_nodes[idx] is not None
            self.assign_buttons[idx].Enable(myflag)
            self.assign_buttons[idx].Enable(myflag)

        self.parent.Reposition(self.panelidx)

    def Signal(self, signal, *args):
        if signal in ("rebuild_tree",):
            pass
        elif signal == "emphasized":
            self.Enable(self.context.elements.has_emphasis())
