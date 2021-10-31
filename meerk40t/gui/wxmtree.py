
import wx
from wx import aui

from .icons import icons8_smartphone_ram_50, icon_meerk40t, icons8_laser_beam_20, icons8_vector_20, \
    icons8_scatter_plot_20, icons8_direction_20, icons8_system_task_20, icons8_file_20, icons8_group_objects_20
from .laserrender import swizzlecolor, DRAW_MODE_ICONS, DRAW_MODE_TREE
from .mwindow import MWindow
from .wxutils import get_key_name, create_menu
from ..core.cutcode import CutCode
from ..core.elements import isDot, LaserOperation
from ..svgelements import SVG_ATTR_STROKE, Color, SVGImage, Shape, SVGText, Group, Path, SVGElement

_ = wx.GetTranslation

NODE_ROOT = 0
NODE_OPERATION_BRANCH = 10
NODE_OPERATION = 11
NODE_OPERATION_ELEMENT = 12
NODE_ELEMENTS_BRANCH = 20
NODE_ELEMENT = 21
NODE_FILES_BRANCH = 30
NODE_FILE_FILE = 31
NODE_FILE_ELEMENT = 32


def register_panel(window, context):
    wxtree = TreePanel(window, wx.ID_ANY, context=context)

    pane = (
        aui.AuiPaneInfo()
            .Name("tree")
            .Left()
            .MinSize(200, -1)
            .LeftDockable()
            .RightDockable()
            .BottomDockable(False)
            .Caption(_("Tree"))
            .CaptionVisible(not context.pane_lock)
            .TopDockable(False)
    )
    pane.dock_proportion = 275
    pane.control = wxtree
    window.on_pane_add(pane)
    context.register("pane/tree", pane)


class TreePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        # Define Tree
        self.wxtree = wx.TreeCtrl(
            self, wx.ID_ANY, style=wx.TR_MULTIPLE | wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT
        )
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.wxtree, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.__set_tree()
        self.wxtree.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.wxtree.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.on_rebuild_tree_request()

    def __set_tree(self):
        self.shadow_tree = ShadowTree(self.context, self.GetParent(), self.context.elements._tree, self.wxtree)
        self.Bind(
            wx.EVT_TREE_BEGIN_DRAG, self.shadow_tree.on_drag_begin_handler, self.wxtree
        )
        self.Bind(
            wx.EVT_TREE_END_DRAG, self.shadow_tree.on_drag_end_handler, self.wxtree
        )
        self.Bind(
            wx.EVT_TREE_ITEM_ACTIVATED, self.shadow_tree.on_item_activated, self.wxtree
        )
        self.Bind(
            wx.EVT_TREE_SEL_CHANGED,
            self.shadow_tree.on_item_selection_changed,
            self.wxtree,
        )
        self.Bind(
            wx.EVT_TREE_ITEM_RIGHT_CLICK,
            self.shadow_tree.on_item_right_click,
            self.wxtree,
        )

    def on_key_down(self, event):
        keyvalue = get_key_name(event)
        keymap = self.context.keymap
        if keyvalue in keymap:
            action = keymap[keyvalue]
            self.context(action + "\n")
        else:
            event.Skip()

    def on_key_up(self, event):
        keyvalue = get_key_name(event)
        keymap = self.context.keymap
        if keyvalue in keymap:
            action = keymap[keyvalue]
            if action.startswith("+"):
                # Keyup commands only trigger if the down command started with +
                action = "-" + action[1:]
                self.context(action + "\n")
        else:
            event.Skip()

    def initialize(self):
        self.context.listen("rebuild_tree", self.on_rebuild_tree_signal)
        self.context.listen("refresh_tree", self.request_refresh)
        self.context.listen("element_property_update", self.on_element_update)
        self.context.listen("element_property_reload", self.on_force_element_update)
        self.context.listen("select_emphasized_tree", self.shadow_tree.select_in_tree_by_emphasis)
        self.context.listen("activate_selected_nodes", self.shadow_tree.activate_selected_node)

    def finalize(self):
        self.context.unlisten("rebuild_tree", self.on_rebuild_tree_signal)
        self.context.unlisten("refresh_tree", self.request_refresh)
        self.context.unlisten("element_property_update", self.on_element_update)
        self.context.unlisten("element_property_reload", self.on_force_element_update)
        self.context.unlisten("select_emphasized_tree", self.shadow_tree.select_in_tree_by_emphasis)
        self.context.unlisten("activate_selected_nodes", self.shadow_tree.activate_selected_node)

    def on_element_update(self, origin, *args):
        """
        Called by 'element_property_update' when the properties of an element are changed.

        :param origin: the path of the originating signal
        :param args:
        :return:
        """
        if self.shadow_tree is not None:
            self.shadow_tree.on_element_update(*args)

    def on_force_element_update(self, origin, *args):
        """
        Called by 'element_property_reload' when the properties of an element are changed.

        :param origin: the path of the originating signal
        :param args:
        :return:
        """
        if self.shadow_tree is not None:
            self.shadow_tree.on_force_element_update(*args)

    def on_rebuild_tree_request(self, *args):
        """
        Called by various functions, sends a rebuild_tree signal.
        This is to prevent multiple events from overtaxing the rebuild.

        :param args:
        :return:
        """
        self.context.signal("rebuild_tree")

    def on_refresh_tree_signal(self, *args):
        self.request_refresh()

    def on_rebuild_tree_signal(self, origin, *args):
        """
        Called by 'rebuild_tree' signal. To refresh tree directly

        :param origin: the path of the originating signal
        :param args:
        :return:
        """
        if self.context.draw_mode & DRAW_MODE_TREE != 0:
            self.wxtree.Hide()
            return
        else:
            self.wxtree.Show()
        self.shadow_tree.rebuild_tree()
        self.request_refresh()

    def request_refresh(self, *args):
        pass


class ElementsTree(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(423, 131, *args, **kwds)

        self.panel = TreePanel(self, wx.ID_ANY, context=self.context)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_smartphone_ram_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Tree"))

    def window_open(self):
        try:
            self.panel.initialize()
        except AttributeError:
            pass

    def window_close(self):
        try:
            self.panel.finalize()
        except AttributeError:
            pass


class ShadowTree:
    """
    The shadowTree creates a wx.Tree structure from the elements.tree structure. It listens to updates to the elements
    tree and updates the GUI version accordingly. This tree does not permit alterations to it, rather it sends any
    requested alterations to the elements.tree or the elements.elements or elements.operations and when those are
    reflected in the tree, the shadow tree is updated accordingly.
    """

    def __init__(self, context, gui, root, wxtree):
        self.context = context
        self.element_root = root
        self.gui = gui
        self.wxtree = wxtree
        self.renderer = gui.renderer
        self.dragging_nodes = None
        self.tree_images = None
        self.object = "Project"
        self.name = "Project"
        self.context = context
        self.elements = context.elements
        self.elements.listen(self)
        self.do_not_select = False

    def node_created(self, node, **kwargs):
        pass

    def node_destroyed(self, node, **kwargs):
        pass

    def node_detached(self, node, **kwargs):
        self.unregister_children(node)
        self.node_unregister(node, **kwargs)

    def node_attached(self, node, **kwargs):
        self.node_register(node, **kwargs)
        self.register_children(node)

    def node_changed(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node)

    def selected(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node)
        self.set_enhancements(node)
        self.context.signal("selected", node)

    def emphasized(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node)
        self.set_enhancements(node)
        self.context.signal("emphasized", node)

    def targeted(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node)
        self.set_enhancements(node)
        self.context.signal("targeted", node)

    def highlighted(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node)
        self.set_enhancements(node)
        self.context.signal("highlighted", node)

    def modified(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node)
        try:
            c = node.color
            self.set_color(node, c)
        except AttributeError:
            pass
        self.context.signal("modified", node)

    def altered(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_label(node, force=True)
        try:
            c = node.color
            self.set_color(node, c)
        except AttributeError:
            pass
        self.set_icon(node)
        self.context.signal("altered", node)

    def expand(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.wxtree.ExpandAllChildren(item)

    def collapse(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.wxtree.CollapseAllChildren(item)
        if self.wxtree.GetItemParent(item) == self.wxtree.GetRootItem():
            self.wxtree.Expand(item)

    def reorder(self, node):
        self.rebuild_tree()

    def update(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.set_icon(node)
        self.on_force_element_update(node)

    def focus(self, node):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.wxtree.EnsureVisible(item)
        for s in self.wxtree.GetSelections():
            self.wxtree.SelectItem(s, False)
        self.wxtree.SelectItem(item)
        self.wxtree.ScrollTo(item)

    def on_force_element_update(self, *args):
        element = args[0]
        if hasattr(element, "node"):
            self.update_label(element.node, force=True)
        else:
            self.update_label(element, force=True)

    def on_element_update(self, *args):
        element = args[0]
        if hasattr(element, "node"):
            self.update_label(element.node)
        else:
            self.update_label(element)

    def refresh_tree(self, node=None):
        """Any tree elements currently displaying wrong data as per elements should be updated to display
        the proper values and contexts and icons."""
        if node is None:
            node = self.element_root.item
        if node is None:
            return
        tree = self.wxtree

        child, cookie = tree.GetFirstChild(node)
        while child.IsOk():
            child_node = self.wxtree.GetItemData(child)
            self.set_enhancements(child_node)
            self.refresh_tree(child)
            child, cookie = tree.GetNextChild(node, cookie)

    def rebuild_tree(self):
        self.dragging_nodes = None
        self.wxtree.DeleteAllItems()

        self.tree_images = wx.ImageList()
        self.tree_images.Create(width=20, height=20)

        self.wxtree.SetImageList(self.tree_images)
        self.element_root.item = self.wxtree.AddRoot(self.name)

        self.wxtree.SetItemData(self.element_root.item, self.element_root)

        self.set_icon(
            self.element_root, icon_meerk40t.GetBitmap(False, resize=(20, 20))
        )
        self.register_children(self.element_root)

        node_operations = self.element_root.get(type="branch ops")
        self.set_icon(node_operations, icons8_laser_beam_20.GetBitmap())

        for n in node_operations.children:
            self.set_icon(n)

        node_elements = self.element_root.get(type="branch elems")
        self.set_icon(node_elements, icons8_vector_20.GetBitmap())

        # Expand Ops and Element nodes only
        # We check these two exist but will open any additional siblings just in case
        self.wxtree.CollapseAll()
        self.wxtree.Expand(node_operations.item)
        self.wxtree.Expand(node_elements.item)


    def register_children(self, node):
        for child in node.children:
            self.node_register(child)
            self.register_children(child)

    def unregister_children(self, node):
        for child in node.children:
            self.unregister_children(child)
            self.node_unregister(child)

    def node_unregister(self, node, **kwargs):
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        node.unregister_object()
        self.wxtree.Delete(node.item)
        for i in self.wxtree.GetSelections():
            self.wxtree.SelectItem(i, False)

    def node_register(self, node, pos=None, **kwargs):
        parent = node.parent
        parent_item = parent.item
        tree = self.wxtree
        if pos is None:
            node.item = tree.AppendItem(parent_item, self.name)
        else:
            node.item = tree.InsertItem(parent_item, pos, self.name)
        tree.SetItemData(node.item, node)
        self.update_label(node)
        try:
            stroke = node.object.values[SVG_ATTR_STROKE]
            color = wx.Colour(swizzlecolor(Color(stroke).argb))
            tree.SetItemTextColour(node.item, color)
        except AttributeError:
            pass
        except KeyError:
            pass
        except TypeError:
            pass
        self.set_icon(node)
        self.context.signal("refresh_tree")

    def set_enhancements(self, node):
        tree = self.wxtree
        node_item = node.item
        tree.SetItemBackgroundColour(node_item, None)
        try:
            if node.highlighted:
                tree.SetItemBackgroundColour(node_item, wx.LIGHT_GREY)
            elif node.emphasized:
                tree.SetItemBackgroundColour(node_item, wx.Colour(0x80A0A0))
            elif node.targeted:
                tree.SetItemBackgroundColour(node_item, wx.Colour(0xA080A0))
        except AttributeError:
            pass

    def set_color(self, node, color=None):
        item = node.item
        if item is None:
            return
        tree = self.wxtree
        if color is None:
            tree.SetItemTextColour(item, None)
        else:
            tree.SetItemTextColour(item, wx.Colour(swizzlecolor(color)))

    def set_icon(self, node, icon=None):
        root = self
        drawmode = self.context.draw_mode
        if drawmode & DRAW_MODE_ICONS != 0:
            return
        try:
            item = node.item
        except AttributeError:
            return  # Node.item can be none if launched from ExecuteJob where the nodes are not part of the tree.
        data_object = node.object
        tree = root.wxtree
        if icon is None:
            if isinstance(data_object, SVGImage):
                image = self.renderer.make_thumbnail(
                    data_object.image, width=20, height=20
                )
                image_id = self.tree_images.Add(bitmap=image)
                tree.SetItemImage(item, image=image_id)
            elif isinstance(data_object, (Shape, SVGText)):
                if isDot(data_object):
                    if (
                        data_object.stroke is not None
                        and data_object.stroke.rgb is not None
                    ):
                        c = data_object.stroke
                    else:
                        c = Color("black")
                    self.set_icon(node, icons8_scatter_plot_20.GetBitmap(color=c))
                    return
                image = self.renderer.make_raster(
                    node, data_object.bbox(), width=20, height=20, bitmap=True
                )
                if image is not None:
                    image_id = self.tree_images.Add(bitmap=image)
                    tree.SetItemImage(item, image=image_id)
                    self.context.signal("refresh_tree")
            elif isinstance(node, LaserOperation):
                try:
                    op = node.operation
                except AttributeError:
                    op = None
                try:
                    c = node.color
                    self.set_color(node, c)
                except AttributeError:
                    c = None
                if op in ("Raster", "Image"):
                    self.set_icon(node, icons8_direction_20.GetBitmap(color=c))
                elif op in ("Engrave", "Cut"):
                    self.set_icon(node, icons8_laser_beam_20.GetBitmap(color=c))
                elif op == "Dots":
                    self.set_icon(node, icons8_scatter_plot_20.GetBitmap(color=c))
                else:
                    self.set_icon(node, icons8_system_task_20.GetBitmap(color=c))
            elif node.type == "file":
                self.set_icon(node, icons8_file_20.GetBitmap())
            elif node.type == "group":
                self.set_icon(node, icons8_group_objects_20.GetBitmap())
        else:
            image_id = self.tree_images.Add(bitmap=icon)
            tree.SetItemImage(item, image=image_id)

    def update_label(self, node, force=False):
        if node.label is None or force:
            node.label = node.create_label()
            self.set_icon(node)
        if not hasattr(node, "item"):
            # Unregistered node updating name.
            self.rebuild_tree()
            return

        self.wxtree.SetItemText(node.item, node.label)
        try:
            stroke = node.object.stroke
            color = wx.Colour(swizzlecolor(Color(stroke).argb))
            self.wxtree.SetItemTextColour(node.item, color)
        except AttributeError:
            pass
        try:
            color = node.color
            c = wx.Colour(swizzlecolor(Color(color)))
            self.wxtree.SetItemTextColour(node.item, c)
        except AttributeError:
            pass

    def move_node(self, node, new_parent, pos=None):
        tree = self.root.shadow_tree
        item = self.item
        image = tree.GetItemImage(item)
        data = tree.GetItemData(item)
        color = tree.GetItemTextColour(item)
        tree.Delete(item)
        if pos is None:
            self.item = tree.AppendItem(new_parent.item, self.name)
        else:
            self.item = tree.InsertItem(new_parent.item, pos, self.name)
        item = self.item
        tree.SetItemImage(item, image)
        tree.SetItemData(item, data)
        tree.SetItemTextColour(item, color)

    def bbox(self, node):
        return Group.union_bbox([self.object])

    def on_drag_begin_handler(self, event):
        """
        Drag handler begin for the tree.

        :param event:
        :return:
        """
        self.dragging_nodes = None

        pt = event.GetPoint()
        drag_item, _ = self.wxtree.HitTest(pt)

        if drag_item is None or drag_item.ID is None or not drag_item.IsOk():
            event.Skip()
            return

        self.dragging_nodes = [
            self.wxtree.GetItemData(item) for item in self.wxtree.GetSelections()
        ]
        if not len(self.dragging_nodes):
            event.Skip()
            return

        t = self.dragging_nodes[0].type
        for n in self.dragging_nodes:
            if t != n.type:
                event.Skip()
                return
            if not n.is_movable():
                event.Skip()
                return
        event.Allow()

    def on_drag_end_handler(self, event):
        """
        Drag end handler for the tree

        :param event:
        :return:
        """
        if self.dragging_nodes is None:
            event.Skip()
            return

        drop_item = event.GetItem()
        if drop_item is None or drop_item.ID is None:
            event.Skip()
            return
        drop_node = self.wxtree.GetItemData(drop_item)
        if drop_node is None:
            event.Skip()
            return

        skip = True
        for drag_node in self.dragging_nodes:
            if drop_node is drag_node:
                continue
            if drop_node.drop(drag_node):
                skip = False
        if skip:
            event.Skip()
        else:
            event.Allow()
        self.dragging_nodes = None

    def on_item_right_click(self, event):
        """
        Right click of element in tree.

        :param event:
        :return:
        """
        item = event.GetItem()
        if item is None:
            return
        node = self.wxtree.GetItemData(item)

        create_menu(self.gui, node, self.elements)

    def on_item_activated(self, event):
        """
        Tree item is double-clicked. Launches PropertyWindow associated with that object.

        :param event:
        :return:
        """
        item = event.GetItem()
        node = self.wxtree.GetItemData(item)
        self.activated_node(node)

    def activate_selected_node(self, *args):
        first_element = self.elements.first_element(emphasized=True)
        if hasattr(first_element, "node"):
            self.activated_node(first_element.node)

    def activated_node(self, node):
        if isinstance(node, LaserOperation):
            self.context.open("window/OperationProperty", self.gui, node=node)
            return
        if node is None:
            return
        obj = node.object
        if obj is None:
            return
        elif isinstance(obj, Path):
            self.context.open("window/PathProperty", self.gui, node=node)
        elif isinstance(obj, SVGText):
            self.context.open("window/TextProperty", self.gui, node=node)
        elif isinstance(obj, SVGImage):
            self.context.open("window/ImageProperty", self.gui, node=node)
        elif isinstance(obj, Group):
            self.context.open("window/GroupProperty", self.gui, node=node)
        elif isinstance(obj, SVGElement):
            self.context.open("window/PathProperty", self.gui, node=node)
        elif isinstance(obj, CutCode):
            self.context.open("window/Simulation", self.gui, node=node)

    def on_item_selection_changed(self, event):
        """
        Tree menu item is changed. Modify the selection.

        :param event:
        :return:
        """
        if self.do_not_select:
            # Do not select is part of a linux correction where moving nodes around in a drag and drop fashion could
            # cause them to appear to drop invalid nodes.
            return
        selected = [
            self.wxtree.GetItemData(item) for item in self.wxtree.GetSelections()
        ]
        self.elements.set_selected(selected)

        emphasized = list(selected)
        for i in range(len(emphasized)):
            node = emphasized[i]
            if node.type == "opnode":
                emphasized[i] = node.object.node
            elif node.type == "op":
                for n in node.flat(types=("opnode",), cascade=False):
                    try:
                        emphasized.append(n.object.node)
                    except Exception:
                        pass

        self.elements.set_emphasis(emphasized)
        self.refresh_tree()
        event.Allow()

    def select_in_tree_by_emphasis(self, origin, *args):
        """
        :return:
        """
        self.do_not_select = True
        for e in self.elements.elems_nodes(emphasized=True):
            self.wxtree.SelectItem(e.item, True)
        self.do_not_select = False

    def contains(self, box, x, y=None):
        if y is None:
            y = x[1]
            x = x[0]
        return box[0] <= x <= box[2] and box[1] <= y <= box[3]
