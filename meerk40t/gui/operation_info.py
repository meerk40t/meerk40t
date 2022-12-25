import wx

from meerk40t.core.element_types import op_parent_nodes
from meerk40t.gui.icons import (
    icons8_computer_support_50,
    icons8_diagonal_20,
    icons8_direction_20,
    icons8_image_20,
    icons8_laser_beam_20,
    icons8_scatter_plot_20,
    icons8_small_beam_20,
)
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import ScrolledPanel
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class OpInfoPanel(ScrolledPanel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        self.list_operations = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )
        self.list_operations.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=58)

        info = wx.ListItem()
        info.Mask = wx.LIST_MASK_TEXT | wx.LIST_MASK_IMAGE | wx.LIST_MASK_FORMAT
        info.Image = -1
        info.Align = wx.LIST_FORMAT_LEFT
        info.Text = _("Type")
        info.Width = wx.LIST_AUTOSIZE

        self.list_operations.InsertColumn(self.list_operations.GetColumnCount(), info)

        self.list_operations.AppendColumn(
            _("Name"), format=wx.LIST_FORMAT_LEFT, width=wx.LIST_AUTOSIZE
        )
        self.list_operations.AppendColumn(
            _("Items"), format=wx.LIST_FORMAT_CENTER, width=73
        )
        self.list_operations.AppendColumn(
            _("Runtime"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_operations.SetToolTip(
            _("Right-Click for more options for ops and unassigned elements")
        )
        self.cmd_calc = wx.Button(self, wx.ID_ANY, _("Get Time Estimates"))
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.list_operations, 1, wx.EXPAND, 0)
        sizer_main.Add(self.cmd_calc, 0, wx.EXPAND, 0)
        self.cmd_calc.Bind(wx.EVT_BUTTON, self.get_estimates)
        self.Bind(
            wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_rightclick, self.list_operations
        )
        self.SetSizer(sizer_main)
        self.Layout()

        self.opinfo = {
            "op cut": ("Cut", icons8_laser_beam_20, 0),
            "op raster": ("Raster", icons8_direction_20, 0),
            "op image": ("Image", icons8_image_20, 0),
            "op engrave": ("Engrave", icons8_small_beam_20, 0),
            "op dots": ("Dots", icons8_scatter_plot_20, 0),
            "op hatch": ("Hatch", icons8_diagonal_20, 0),
        }
        self.state_images = wx.ImageList()
        self.state_images.Create(width=25, height=25)
        for key in self.opinfo:
            info = self.opinfo[key]
            image_id = self.state_images.Add(
                bitmap=info[1].GetBitmap(resize=(25, 25), noadjustment=True)
            )
            info = (info[0], info[1], image_id)
            self.opinfo[key] = info

        self.list_operations.AssignImageList(self.state_images, wx.IMAGE_LIST_SMALL)
        self.ops = None
        self.refresh_data()

    def get_estimates(self, event):
        lcount = self.list_operations.GetItemCount()
        for index in range(lcount):
            info = "---"
            id = self.list_operations.GetItemData(index)
            if id < 0:
                continue
            myop = self.ops[id]
            if hasattr(myop, "time_estimate"):
                info = myop.time_estimate()
            self.list_operations.SetItem(id, 4, info)

    def refresh_data(self):
        def mklabel(value):
            if value is None:
                return ""
            else:
                return value

        self.list_operations.DeleteAllItems()
        self.ops = list(self.context.elements.ops())
        for idx, node in enumerate(self.ops):
            try:
                info = self.opinfo[node.type]
            except KeyError:
                continue
            # print(f"{node.type} - {node.label} - {info[0]}, {info[2]}")
            list_id = self.list_operations.InsertItem(
                self.list_operations.GetItemCount(), f"#{idx}"
            )
            self.list_operations.SetItem(list_id, 1, info[0])
            self.list_operations.SetItem(list_id, 2, mklabel(node.label))
            self.list_operations.SetItem(list_id, 3, str(len(node.children)))
            self.list_operations.SetItem(list_id, 4, "---")
            self.list_operations.SetItemImage(list_id, info[2])
            self.list_operations.SetItemData(list_id, idx)

        # Check whether we have orphan elements
        elem_count = {
            "elem ellipse": 0,
            "elem image": 0,
            "elem path": 0,
            "elem geomstr": 0,
            "elem point": 0,
            "elem polyline": 0,
            "elem rect": 0,
            "elem line": 0,
            "elem text": 0,
        }
        elems = list(self.context.elements.elems())
        for node in elems:
            try:
                count = elem_count[node.type]
            except KeyError:
                continue

            found = False
            for op in self.ops:
                for ch in op.children:
                    if hasattr(ch, "node"):
                        if node == ch.node:
                            found = True
                            break
                if found:
                    break
            if not found:
                # print (f"Not found: {node.type}")
                count += 1
                elem_count[node.type] = count
        # Iterate over all unfound elem types
        for key in elem_count:
            count = elem_count[key]
            if count == 0:
                continue
            list_id = self.list_operations.InsertItem(
                self.list_operations.GetItemCount(), "!"
            )
            self.list_operations.SetItem(list_id, 1, _("Unassigned"))
            self.list_operations.SetItem(list_id, 2, key)
            self.list_operations.SetItem(list_id, 3, str(count))
            self.list_operations.SetItemImage(list_id, -1)
            self.list_operations.SetItemData(list_id, -1)

    @signal_listener("element_property_update")
    @signal_listener("element_property_reload")
    @signal_listener("rebuild_tree")
    @signal_listener("tree_changed")
    def on_tree_refresh(self, origin, *args):
        self.refresh_data()

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    def on_tree_popup_mark_elem(self, elemtype=""):
        def emphas(event=None):
            data = []
            elems = list(self.context.elements.elems())
            for node in elems:
                if elemtype != "" and elemtype != node.type:
                    continue
                found = False
                for op in self.ops:
                    for ch in op.children:
                        if hasattr(ch, "node"):
                            if node == ch.node:
                                found = True
                                break
                    if found:
                        break
                if not found:
                    data.append(node)

            self.context.elements.set_emphasis(data)

        return emphas

    def on_tree_popup_empty(self, opnode=None):
        def clear(event=None):
            opnode.remove_all_children()
            self.context.signal("tree_changed")

        return clear

    def on_tree_popup_reclassify(self, opnode=None):
        def reclassify(event=None):
            opnode.remove_all_children()
            data = list(self.context.elements.elems())
            reverse = self.context.elements.classify_reverse
            fuzzy = self.context.elements.classify_fuzzy
            fuzzydistance = self.context.elements.classify_fuzzydistance
            if reverse:
                data = reversed(data)
            for node in data:
                # result is a tuple containing classified, should_break, feedback
                result = opnode.classify(
                    node,
                    fuzzy=fuzzy,
                    fuzzydistance=fuzzydistance,
                    usedefault=False,
                )
            self.context.signal("tree_changed")

        return reclassify

    def on_item_rightclick(self, event):
        def mklabel(value):
            if value is None:
                return ""
            else:
                return value

        index = event.Index
        try:
            id = self.list_operations.GetItemData(index)
        except (KeyError, IndexError):
            return
        menu = wx.Menu()
        if id < 0:
            # elem xxx Type:
            listitem = self.list_operations.GetItem(index, 2)
            elemtype = listitem.GetText()
            item = menu.Append(
                wx.ID_ANY,
                _("Emphasize these elements ({name})").format(name=elemtype),
                "",
                wx.ITEM_NORMAL,
            )
            self.Bind(wx.EVT_MENU, self.on_tree_popup_mark_elem(elemtype), item)
            item = menu.Append(
                wx.ID_ANY,
                _("Emphasize all unclassified elements"),
                "",
                wx.ITEM_NORMAL,
            )
            self.Bind(wx.EVT_MENU, self.on_tree_popup_mark_elem(""), item)
        else:
            opnode = self.ops[id]
            s = mklabel(opnode.label)
            if s == "":
                s = opnode.type
            item = menu.Append(
                wx.ID_ANY,
                _("Remove all items from {name}").format(name=s),
                "",
                wx.ITEM_NORMAL,
            )
            self.Bind(wx.EVT_MENU, self.on_tree_popup_empty(opnode), item)
            item = menu.Append(wx.ID_ANY, _("Re-Classify"), "", wx.ITEM_NORMAL)
            self.Bind(wx.EVT_MENU, self.on_tree_popup_reclassify(opnode), item)

        self.PopupMenu(menu)
        menu.Destroy()


class OperationInformation(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(551, 234, submenu="Operations", *args, **kwds)
        self.panel = OpInfoPanel(self, wx.ID_ANY, context=self.context)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_computer_support_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Operation Information"))

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def submenu():
        return ("Operations", "Operation Information")
