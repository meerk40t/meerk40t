import wx

from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_image import ImageOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.gui.icons import EmptyIcon, icon_library
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
        self.assign_operations = []
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
        slabel = _("Assign the selection to:") + "\n" + slabel + "\n" + _("Right click for options")
        return slabel

    def GenerateControls(self, parent, panelidx, identifier, context):
        def size_it(ctrl, dimen_x, dimen_y):
            ctrl.SetMinSize(wx.Size(dimen_x, dimen_y))
            ctrl.SetMaxSize(wx.Size(dimen_x, dimen_y))

        super().GenerateControls(parent, panelidx, identifier, context)
        # How should be display the data?
        display_mode = self.context.elements.setting(int, "default_ops_display_mode", 0)

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
        ).GetBitmap(noadjustment=True)
        self.btn_prev.SetBitmap(icon)
        self.btn_prev.SetToolTip(_("Previous entries"))
        self.Add(self.btn_prev, 0, wx.EXPAND, 0)
        self.btn_prev.Bind(wx.EVT_LEFT_DOWN, self.on_prev)
        size_it(self.btn_prev, self.buttonsize_x, self.buttonsize_y)
        self.SetActive(self.btn_prev, False)
        self.first_to_show = 0
        self.page_size = int((self.width - 2 * self.buttonsize_x) / self.buttonsize_x)

        self.assign_buttons.clear()
        self.assign_operations.clear()
        op_order = ("op cut", "op engrave", "op raster", "op image", "op dots")
        oplist = []
        for op in self.context.elements.default_operations:
            if hasattr(op, "type") and op.type in op_order:
                oplist.append(op)
        if display_mode == 0:
            # As in tree, so nothing to do...
            pass
        elif display_mode == 1:
            # Group according to type CC EE RR
            oplist = []
            for ntype in op_order:
                for op in self.context.elements.default_operations:
                    if op.type == ntype:
                        oplist.append(op)
        elif display_mode == 2:
            oplist = []
            mylist = []
            for ntype in op_order:
                for op in self.context.elements.default_operations:
                    if op.type == ntype:
                        mylist.append(op)
            for idx, op in enumerate(mylist):
                if op is None:
                    # Already dealt with
                    continue
                oplist.append(op)
                type_index_1 = op_order.index(op.type)
                for idx2 in range(idx + 1, len(mylist)):
                    op2 = mylist[idx2]
                    if op2 is None:
                        continue
                    type_index_2 = op_order.index(op2.type)
                    if type_index_2 <= type_index_1:
                        continue
                    oplist.append(op2)
                    mylist[idx2] = None
                    # Next one
                    type_index_1 = type_index_2

                mylist[idx] = None

        for op in oplist:
            btn = wx.StaticBitmap(
                self.parent,
                id=wx.ID_ANY,
                size=(self.buttonsize_x, self.buttonsize_y),
                # style=wx.BORDER_RAISED,
            )
            opid = op.id
            if opid is None:
                opid = ""
            fontsize = 10
            if len(opid) > 2:
                fontsize = 8
            elif len(opid) > 3:
                fontsize = 7
            elif len(opid) > 4:
                fontsize = 6
            # use_theme=False is needed as otherwise colors will get reversed
            icon = EmptyIcon(
                size=(self.iconsize, min(self.iconsize, self.height)),
                color=wx.Colour(swizzlecolor(op.color)),
                msg=opid,
                ptsize=fontsize,
            ).GetBitmap(noadjustment=True, use_theme=False)
            btn.SetBitmap(icon)
            btn.SetToolTip(self.node_label(op))
            size_it(btn, self.buttonsize_x, self.buttonsize_y)
            self.assign_buttons.append(btn)
            self.assign_operations.append(op)
            btn.Bind(wx.EVT_LEFT_DOWN, self.on_button_left)
            btn.Bind(wx.EVT_RIGHT_DOWN, self.on_button_right)
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
        ).GetBitmap(noadjustment=True)
        self.btn_next.SetBitmap(icon)
        self.btn_next.SetToolTip(_("Next entries"))
        size_it(self.btn_next, self.buttonsize_x, self.buttonsize_y)

        self.Add(self.btn_next, 0, wx.EXPAND, 0)
        self.SetActive(self.btn_next, False)
        self.btn_next.Bind(wx.EVT_LEFT_DOWN, self.on_next)

        self.btn_matman = wx.StaticBitmap(
            parent,
            id=wx.ID_ANY,
            size=(self.buttonsize_x, self.buttonsize_y),
            # style=wx.BORDER_RAISED,
        )
        icon = icon_library.GetBitmap(resize=self.iconsize)
        self.btn_matman.SetBitmap(icon)
        self.btn_matman.SetToolTip(_("Open material manager"))
        size_it(self.btn_matman, self.buttonsize_x, self.buttonsize_y)

        self.Add(self.btn_matman, 0, wx.EXPAND, 0)
        self.btn_matman.Bind(wx.EVT_LEFT_DOWN, self.on_matman)

    def on_matman(self, event):
        self.context("window open MatManager\n")

    def on_button_left(self, event):
        button = event.GetEventObject()
        shift_pressed = event.ShiftDown()
        # print (f"Shift: {event.ShiftDown()}, ctrl={event.ControlDown()}, alt={event.AltDown()}, bitmask={event.GetModifiers()}")
        idx = 0
        while idx < len(self.assign_buttons):
            if button is self.assign_buttons[idx]:
                node = self.assign_operations[idx]
                self.execute_on(node, shift_pressed)
                break
            idx += 1

    def on_button_right(self, event):
        # Allow loading of a different set of operations...
        # See function for all buttons...
        # button = event.GetEventObject()
        menu = wx.Menu()
        matcount = 0

        def on_menu_material(matname):
            def handler(*args):
                oplist, opinfo = self.context.elements.load_persistent_op_list(
                    stored_mat
                )
                if oplist is not None and len(oplist) > 0:
                    self.context.elements.default_operations = oplist
                    self.Signal("default_operations")

            stored_mat = matname
            return handler

        # def on_update_button_from_tree(idx, operation):
        #     def handler(*args):
        #         self.assign_operations[stored_idx] = self.context.elements.create_usable_copy(stored_op)
        #
        #     stored_idx = idx
        #     stored_op = operation
        #     return handler
        #
        # # Check if the id of this entry is already existing (and the types match too)
        # button = event.GetEventObject()
        # node_index = -1
        # node = None
        # idx = 0
        # while idx < len(self.assign_buttons):
        #     if button is self.assign_buttons[idx]:
        #         node_index = idx
        #         node = self.assign_operations[idx]
        #         break
        #     idx += 1
        # foundop = None
        # if node_index >= 0 and node.id is not None:
        #     for op in self.context.elements.ops():
        #         if op.type == node.type and op.id == node.id:
        #             foundop = op
        #             break
        # if node is not None and foundop is not None:
        #     self.parent.Bind(
        #         wx.EVT_MENU,
        #         on_update_button_from_tree(node_index, foundop),
        #         menu.Append(wx.ID_ANY, _("Use settings from tree for this button"), ""),
        #     )
        #     menu.AppendSeparator()

        for material in self.context.elements.op_data.section_set():
            if material == "previous":
                continue
            if matcount == 0:
                item = menu.Append(wx.ID_ANY, _("Load materials/operations"), "")
                item.Enable(False)
            opinfo = self.context.elements.load_persistent_op_info(material)
            material_name = opinfo.get("material", "")
            material_title = opinfo.get("title", "")
            label = material_name
            if material_title:
                label += " - " + material_title
            if not material_name:
                if material == "_default":
                    label = "Generic Defaults"
                elif material.startswith("_default_"):
                    label = f"Default for {material[9:]}"
                else:
                    label = material.replace("_", " ")
            if "thickness" in opinfo:
                if opinfo["thickness"]:
                    label += ", " + opinfo["thickness"]
            matcount += 1

            self.parent.Bind(
                wx.EVT_MENU,
                on_menu_material(material),
                menu.Append(wx.ID_ANY, label, ""),
            )

        if matcount > 0:
            menu.AppendSeparator()

        self.parent.Bind(
            wx.EVT_MENU,
            lambda e: self.context("window open MatManager\n"),
            menu.Append(wx.ID_ANY, _("Material Library"), ""),
        )

        self.parent.PopupMenu(menu)

        menu.Destroy()

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
                btnflag = False
                if not residual:
                    if self.assign_operations[idx] is None:
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
            self.SetActive(self.btn_next, residual)
            self.SetActive(self.btn_matman, not residual)

        else:
            self.SetActive(self.btn_prev, False)
            for btn in self.assign_buttons:
                self.SetActive(btn, False)
            self.SetActive(self.btn_next, False)
            self.SetActive(self.btn_matman, True)
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

    def execute_on(self, targetop, use_parent):
        targetdata = []
        data = list(self.context.elements.elems(emphasized=True))
        for node in data:
            add_node = node
            if use_parent:
                if node.parent is not None and node.parent.type.startswith("effect"):
                    add_node = node.parent
            if add_node not in targetdata:
                targetdata.append(add_node)

        self.context.elements.assign_default_operation(targetdata, targetop)
        self.context.elements.set_emphasis(data)

        self.reset_tooltips()

    def show_stuff(self, flag):
        # for idx in range(len(self.assign_buttons)):
        #     myflag = flag and self.assign_operations[idx] is not None
        #     self.assign_buttons[idx].Enable(myflag)

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
            pass
            # self.Enable(self.context.elements.has_emphasis())
