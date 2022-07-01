import wx
from wx import aui

from ..kernel import signal_listener
from ..svgelements import Color
from .icons import (
    icon_meerk40t,
    icons8_direction_20,
    icons8_file_20,
    icons8_group_objects_20,
    icons8_input_20,
    icons8_laser_beam_20,
    icons8_scatter_plot_20,
    icons8_smartphone_ram_50,
    icons8_system_task_20,
    icons8_timer_20,
    icons8_vector_20,
    icons8_vga_20,
)
from .laserrender import DRAW_MODE_ICONS, LaserRender, swizzlecolor
from .mwindow import MWindow
from .wxutils import create_menu, get_key_name

_ = wx.GetTranslation


def register_panel_tree(window, context):
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

        self.context.signal("rebuild_tree")

    def __set_tree(self):
        self.shadow_tree = ShadowTree(
            self.context.elements, self.GetParent(), self.wxtree
        )

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
        if self.context.bind.trigger(keyvalue):
            event.Skip()
        else:
            # Make sure the treectl can work on standard keys...
            event.Skip()

    def on_key_up(self, event):
        keyvalue = get_key_name(event)
        if self.context.bind.untrigger(keyvalue):
            event.Skip()
        else:
            # Make sure the treectl can work on standard keys...
            event.Skip()

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    @signal_listener("select_emphasized_tree")
    def on_shadow_select_emphasized_tree(self, origin, *args):
        self.shadow_tree.select_in_tree_by_emphasis(origin, *args)

    @signal_listener("activate_selected_nodes")
    def on_shadow_select_activate_tree(self, origin, *args):
        self.shadow_tree.activate_selected_node(origin, *args)

    @signal_listener("element_property_update")
    def on_element_update(self, origin, *args):
        """
        Called by 'element_property_update' when the properties of an element are changed.

        @param origin: the path of the originating signal
        @param args:
        @return:
        """
        if self.shadow_tree is not None:
            self.shadow_tree.on_element_update(*args)

    @signal_listener("element_property_reload")
    def on_force_element_update(self, origin, *args):
        """
        Called by 'element_property_reload' when the properties of an element are changed.

        @param origin: the path of the originating signal
        @param args:
        @return:
        """
        if self.shadow_tree is not None:
            self.shadow_tree.on_force_element_update(*args)

    @signal_listener("rebuild_tree")
    def on_rebuild_tree_signal(self, origin, target=None, *args):
        """
        Called by 'rebuild_tree' signal. To rebuild the tree directly

        @param origin: the path of the originating signal
        @param args:
        @return:
        """
        # if target is not None:
        #     if target == "elements":
        #         startnode = self.shadow_tree.elements.get(type="branch elems").item
        #     elif target == "operations":
        #         startnode = self.shadow_tree.elements.get(type="branch ops").item
        #     elif target == "regmarks":
        #         startnode = self.shadow_tree.elements.get(type="branch reg").item
        #     print ("Current content of branch %s" % target)
        #     idx = 0
        #     child, cookie = self.shadow_tree.wxtree.GetFirstChild(startnode)
        #     while child.IsOk():
        #         # child_node = self.wxtree.GetItemData(child)
        #         lbl = self.shadow_tree.wxtree.GetItemText(child)
        #         print ("Node #%d - content: %s" % (idx, lbl))
        #         child, cookie = self.shadow_tree.wxtree.GetNextChild(startnode, cookie)
        #         idx += 1
        #     self.shadow_tree.wxtree.Expand(startnode)
        # else:
        #     self.shadow_tree.rebuild_tree()
        self.shadow_tree.rebuild_tree()

    @signal_listener("refresh_tree")
    def on_refresh_tree_signal(self, origin, nodes=None, *args):
        """
        Called by 'refresh_tree' signal. To refresh tree directly

        @param origin: the path of the originating signal
        @param nodes: which nodes were added.
        @param args:
        @return:
        """
        self.shadow_tree.refresh_tree(source="signal_{org}".format(org=origin))
        if nodes is not None:
            if isinstance(nodes, (tuple, list)):
                for node in nodes:
                    self.shadow_tree.set_icon(node, force=True)
                node = nodes[0]
            else:
                node = nodes
                self.shadow_tree.set_icon(node, force=True)

            self.shadow_tree.wxtree.EnsureVisible(node.item)

    @signal_listener("freeze_tree")
    def on_freeze_tree_signal(self, origin, status=None, *args):
        """
        Called by 'rebuild_tree' signal. Halts any updates like set_decorations and others

        @param origin: the path of the originating signal
        @param: status: true, false (evident what they do), None: to toggle
        @param args:
        @return:
        """
        self.shadow_tree.freeze_tree(status)


class ElementsTree(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(423, 131, *args, **kwds)

        self.panel = TreePanel(self, wx.ID_ANY, context=self.context)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_smartphone_ram_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Tree"))

    def window_open(self):
        try:
            self.panel.pane_show()
        except AttributeError:
            pass

    def window_close(self):
        try:
            self.panel.pane_hide()
        except AttributeError:
            pass


class ShadowTree:
    """
    The shadowTree creates a 'wx.Tree' structure from the 'elements.tree' structure. It listens to updates to the
    elements tree and updates the GUI version accordingly. This tree does not permit alterations to it, rather it sends
    any requested alterations to the 'elements.tree' or the 'elements.elements' or 'elements.operations' and when those
    are reflected in the tree, the shadow tree is updated accordingly.
    """

    def __init__(self, service, gui, wxtree):
        self.elements = service
        self.gui = gui
        self.wxtree = wxtree
        self.renderer = LaserRender(service.root)
        self.dragging_nodes = None
        self.tree_images = None
        self.name = "Project"
        self._freeze = False

        self.do_not_select = False
        self.was_already_expanded = []
        service.add_service_delegate(self)

    def service_attach(self, *args):
        self.elements.listen_tree(self)

    def service_detach(self, *args):
        self.elements.unlisten_tree(self)

    def node_created(self, node, **kwargs):
        """
        Notified that this node has been created.
        @param node: Node that was created.
        @param kwargs:
        @return:
        """
        pass

    def node_destroyed(self, node, **kwargs):
        """
        Notified that this node has been destroyed.
        @param node: Node that was destroyed.
        @param kwargs:
        @return:
        """
        pass

    def node_detached(self, node, **kwargs):
        """
        Notified that this node has been detached from the tree.
        @param node: Node that was detached.
        @param kwargs:
        @return:
        """
        self.unregister_children(node)
        self.node_unregister(node, **kwargs)

    def node_attached(self, node, **kwargs):
        """
        Notified that this node has been attached to the tree.
        @param node: Node that was attached.
        @param kwargs:
        @return:
        """
        self.node_register(node, **kwargs)
        self.register_children(node)

    def node_changed(self, node):
        """
        Notified that this node has been changed.
        @param node: Node that was changed.
        @return:
        """
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_decorations(node, force=True)

    def selected(self, node):
        """
        Notified that this node was selected.

        Directly selected within the tree, specifically selected within the treectrl
        @param node:
        @return:
        """
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        # self.update_decorations(node)
        self.set_enhancements(node)
        self.elements.signal("selected", node)

    def emphasized(self, node):
        """
        Notified that this node was emphasized.

        Item is selected by being emphasized this is treated like a soft selection throughout
        @param node:
        @return:
        """
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        # self.update_decorations(node)
        self.set_enhancements(node)
        self.elements.signal("emphasized", node)

    def targeted(self, node):
        """
        Notified that this node was targeted.

        If any element is emphasized, all operations containing that element are targeted.
        @param node:
        @return:
        """
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_decorations(node)
        self.set_enhancements(node)
        self.elements.signal("targeted", node)

    def highlighted(self, node):
        """
        Notified that this node was highlighted.

        If any operation is selected, all sub-operations are highlighted.
        If any element is emphasized, all copies are highlighted.
        @param node:
        @return:
        """
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        # self.update_decorations(node)
        self.set_enhancements(node)
        self.elements.signal("highlighted", node)

    def modified(self, node):
        """
        Notified that this node was modified.
        This node position values were changed, but nothing about the core data was altered.
        @param node:
        @return:
        """
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_decorations(node, force=True)
        try:
            c = node.color
            self.set_color(node, c)
        except AttributeError:
            pass
        self.elements.signal("modified", node)

    def altered(self, node):
        """
        Notified that this node was altered.
        This node was changed in fundamental ways and nothing about this node remains trusted.
        @param node:
        @return:
        """
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.update_decorations(node, force=True)
        try:
            c = node.color
            self.set_color(node, c)
        except AttributeError:
            pass
        self.elements.signal("altered", node)

    def expand(self, node):
        """
        Notified that this node was expanded.

        @param node:
        @return:
        """
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.wxtree.ExpandAllChildren(item)
        self.set_expanded(item, 1)

    def collapse(self, node):
        """
        Notified that this node was collapsed.

        @param node:
        @return:
        """
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.wxtree.CollapseAllChildren(item)
        if (
            item is self.wxtree.GetRootItem()
            or self.wxtree.GetItemParent(item) is self.wxtree.GetRootItem()
        ):
            self.wxtree.Expand(self.elements.get(type="branch ops").item)
            self.wxtree.Expand(self.elements.get(type="branch elems").item)
            self.wxtree.Expand(self.elements.get(type="branch reg").item)

    def reorder(self, node):
        """
        Notified that this node was reordered.

        Tree is rebuilt.

        @param node:
        @return:
        """
        self.rebuild_tree()

    def update(self, node):
        """
        Notified that this node has been updated.
        @param node:
        @return:
        """
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.set_icon(node, force=False)
        self.on_force_element_update(node)

    def focus(self, node):
        """
        Notified that this node has been focused.

        It must be seen in the tree.
        @param node:
        @return:
        """
        item = node.item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.wxtree.EnsureVisible(item)
        for s in self.wxtree.GetSelections():
            self.wxtree.SelectItem(s, False)
        self.wxtree.SelectItem(item)
        self.wxtree.ScrollTo(item)

    def on_force_element_update(self, *args):
        """
        Called by signal "element_property_reload"
        @param args:
        @return:
        """
        element = args[0]
        if hasattr(element, "node"):
            self.update_decorations(element.node, force=True)
        else:
            self.update_decorations(element, force=True)

    def on_element_update(self, *args):
        """
        Called by signal "element_property_update"
        @param args:
        @return:
        """
        element = args[0]
        if hasattr(element, "node"):
            self.update_decorations(element.node, force=True)
        else:
            self.update_decorations(element, force=True)

    def refresh_tree(self, node=None, level=0, source=""):
        """Any tree elements currently displaying wrong data as per elements should be updated to display
        the proper values and contexts and icons."""
        if node is None:
            # print ("refresh tree called: %s" % source)
            elemtree = self.elements._tree
            node = elemtree.item
            level = 0
        if node is None:
            return
        tree = self.wxtree

        child, cookie = tree.GetFirstChild(node)
        while child.IsOk():
            child_node = self.wxtree.GetItemData(child)
            self.refresh_tree(child, level + 1)
            # An empty node needs to be expanded at least once is it has children...
            # ct = self.wxtree.GetChildrenCount(child, recursively=False)
            # if ct > 0:
            #     former_state = self.was_expanded(child, level)
            #     if not former_state:
            #         self.wxtree.Expand(child)
            #         self.set_expanded(child, level)
            child, cookie = tree.GetNextChild(node, cookie)
        if level == 0:
            self.update_op_labels()
        self.wxtree.Expand(self.elements.get(type="branch ops").item)
        self.wxtree.Expand(self.elements.get(type="branch elems").item)
        self.wxtree.Expand(self.elements.get(type="branch reg").item)

    def freeze_tree(self, status=None):
        if status is None:
            status = not self._freeze
        self._freeze = status
        self.wxtree.Enable(not self._freeze)

    def was_expanded(self, node, level):
        txt = self.wxtree.GetItemText(node)
        chk = "%d-%s" % (level, txt)
        result = False
        for elem in self.was_already_expanded:
            if chk == elem:
                result = True
                break
        return result

    def set_expanded(self, node, level):
        txt = self.wxtree.GetItemText(node)
        chk = "%d-%s" % (level, txt)
        result = self.was_expanded(node, level)
        if not result:
            self.was_already_expanded.append(chk)

    def parse_tree(self, startnode, level):
        if startnode is None:
            return
        cookie = 0
        try:
            pnode, cookie = self.wxtree.GetFirstChild(startnode)
        except:
            return
        while pnode.IsOk():
            txt = self.wxtree.GetItemText(pnode)
            state = self.wxtree.IsExpanded(pnode)
            if state:
                self.was_already_expanded.append("%d-%s" % (level, txt))
            self.parse_tree(pnode, level + 1)
            pnode, cookie = self.wxtree.GetNextChild(startnode, cookie)

    def restore_tree(self, startnode, level):
        if startnode is None:
            return
        cookie = 0
        try:
            pnode, cookie = self.wxtree.GetFirstChild(startnode)
        except:
            return
        while pnode.IsOk():
            txt = self.wxtree.GetItemText(pnode)
            chk = "%d-%s" % (level, txt)
            for elem in self.was_already_expanded:
                if chk == elem:
                    self.wxtree.ExpandAllChildren(pnode)
                    break
            self.parse_tree(pnode, level + 1)
            pnode, cookie = self.wxtree.GetNextChild(startnode, cookie)

    def reset_expanded(self):
        self.was_already_expanded = []

    def rebuild_tree(self):
        """
        Tree requires being deleted and completely rebuilt.

        @return:
        """

        # let's try to remember which branches were expanded:
        self.reset_expanded()

        self.parse_tree(self.wxtree.GetRootItem(), 0)
        # Rebuild tree destroys the emphasis, so let's store it...
        emphasized_list = list(self.elements.elems(emphasized=True))
        elemtree = self.elements._tree
        self.dragging_nodes = None
        self.wxtree.DeleteAllItems()
        if self.tree_images is not None:
            self.tree_images.Destroy()

        self.tree_images = wx.ImageList()
        self.tree_images.Create(width=20, height=20)

        self.wxtree.SetImageList(self.tree_images)
        elemtree.item = self.wxtree.AddRoot(self.name)

        self.wxtree.SetItemData(elemtree.item, elemtree)

        self.set_icon(elemtree, icon_meerk40t.GetBitmap(False, resize=(20, 20)))
        self.register_children(elemtree)

        node_operations = elemtree.get(type="branch ops")
        self.set_icon(node_operations, icons8_laser_beam_20.GetBitmap())

        for n in node_operations.children:
            self.set_icon(n, force=True)

        node_elements = elemtree.get(type="branch elems")
        self.set_icon(node_elements, icons8_vector_20.GetBitmap())

        node_registration = elemtree.get(type="branch reg")
        self.set_icon(node_registration, icons8_vector_20.GetBitmap())
        self.update_op_labels()
        # Expand Ops, Element, and Regmarks nodes only
        self.wxtree.CollapseAll()
        self.wxtree.Expand(node_operations.item)
        self.wxtree.Expand(node_elements.item)
        self.wxtree.Expand(node_registration.item)
        # Restore emphasis
        for e in emphasized_list:
            e.emphasized = True
        self.restore_tree(self.wxtree.GetRootItem(), 0)

    def register_children(self, node):
        """
        All children of this node are registered.

        @param node:
        @return:
        """
        for child in node.children:
            self.node_register(child)
            self.register_children(child)

    def unregister_children(self, node):
        """
        All children of this node are unregistered.

        @param node:
        @return:
        """
        for child in node.children:
            self.unregister_children(child)
            self.node_unregister(child)

    def node_unregister(self, node, **kwargs):
        """
        Node object is unregistered and item is deleted.

        @param node:
        @param kwargs:
        @return:
        """
        item = node.item
        if item is None:
            raise ValueError("Item was None for node " + repr(node))
        if not item.IsOk():
            raise ValueError("Bad Item")
        node.unregister_object()
        self.wxtree.Delete(node.item)
        for i in self.wxtree.GetSelections():
            self.wxtree.SelectItem(i, False)

    def node_register(self, node, pos=None, **kwargs):
        """
        Node.item is added/inserted. Label is updated and values are set. Icon is set.

        @param node:
        @param pos:
        @param kwargs:
        @return:
        """
        parent = node.parent
        parent_item = parent.item
        tree = self.wxtree
        if pos is None:
            node.item = tree.AppendItem(parent_item, self.name)
        else:
            node.item = tree.InsertItem(parent_item, pos, self.name)
        tree.SetItemData(node.item, node)
        self.update_decorations(node)
        try:
            stroke = node.stroke
            color = wx.Colour(swizzlecolor(Color(stroke).argb))
            tree.SetItemTextColour(node.item, color)
        except AttributeError:
            pass
        except KeyError:
            pass
        except TypeError:
            pass

    def set_enhancements(self, node):
        """
        Node in the tree is drawn special based on nodes current setting.
        @param node:
        @return:
        """
        tree = self.wxtree
        node_item = node.item
        if node_item is None:
            return
        if self._freeze:
            return
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
        """
        Node color is set.

        @param node: Not to be colored
        @param color: Color to be set.
        @return:
        """
        item = node.item
        if item is None:
            return
        if self._freeze:
            return
        tree = self.wxtree
        if color is None:
            tree.SetItemTextColour(item, None)
        else:
            tree.SetItemTextColour(item, wx.Colour(swizzlecolor(color)))

    def set_icon(self, node, icon=None, force=False):
        """
        Node icon to be created and applied

        @param node: Node to have the icon set.
        @param icon: overriding icon to be forcably set, rather than a default.
        @return:
        """
        root = self
        drawmode = self.elements.root.draw_mode
        if drawmode & DRAW_MODE_ICONS != 0:
            return
        if self._freeze:
            return
        try:
            item = node.item
        except AttributeError:
            return  # Node.item can be none if launched from ExecuteJob where the nodes are not part of the tree.
        if node.item is None:
            return
        tree = root.wxtree
        if icon is None:
            if force is None:
                force = False
            image_id = tree.GetItemImage(item)
            if image_id >= self.tree_images.ImageCount:
                image_id = -1
            if image_id >= 0 and not force:
                # Don't do it twice
                return

            if node.type == "elem image":
                image = self.renderer.make_thumbnail(node.image, width=20, height=20)
                if image_id < 0:
                    image_id = self.tree_images.Add(bitmap=image)
                else:
                    self.tree_images.Replace(index=image_id, bitmap=image)
                tree.SetItemImage(item, image=image_id)
            elif node.type == "elem point":
                if node.stroke is not None and node.stroke.rgb is not None:
                    c = node.stroke
                else:
                    c = Color("black")
                self.set_icon(node, icons8_scatter_plot_20.GetBitmap(color=c))
                return
            elif node.type == "reference":
                image_id = tree.GetItemImage(node.node.item)
                if image_id >= self.tree_images.ImageCount:
                    image_id = -1
                    # Reset Image Node in List
                if image_id < 0:
                    image = self.renderer.make_raster(
                        node.node,
                        node.node.bounds,
                        width=20,
                        height=20,
                        bitmap=True,
                        keep_ratio=True,
                    )
                    if image is not None:
                        image_id = self.tree_images.Add(bitmap=image)
                        tree.SetItemImage(node.node.item, image=image_id)
                tree.SetItemImage(item, image=image_id)

            elif node.type.startswith("elem "):
                image = self.renderer.make_raster(
                    node, node.bounds, width=20, height=20, bitmap=True, keep_ratio=True
                )
                if image is not None:
                    if image_id < 0:
                        image_id = self.tree_images.Add(bitmap=image)
                    else:
                        self.tree_images.Replace(index=image_id, bitmap=image)
                    tree.SetItemImage(item, image=image_id)
            elif node.type in ("op raster", "op image"):
                try:
                    c = node.color
                    self.set_color(node, c)
                except AttributeError:
                    c = None
                self.set_icon(node, icons8_direction_20.GetBitmap(color=c))
            elif node.type in ("op engrave", "op cut", "op hatch"):
                try:
                    c = node.color
                    self.set_color(node, c)
                except AttributeError:
                    c = None
                self.set_icon(node, icons8_laser_beam_20.GetBitmap(color=c))
            elif node.type == "op dots":
                try:
                    c = node.color
                    self.set_color(node, c)
                except AttributeError:
                    c = None
                self.set_icon(node, icons8_scatter_plot_20.GetBitmap(color=c))
            elif node.type == "util console":
                try:
                    c = node.color
                    self.set_color(node, c)
                except AttributeError:
                    c = None
                self.set_icon(node, icons8_system_task_20.GetBitmap(color=c))
            elif node.type == "util wait":
                self.set_icon(node, icons8_timer_20.GetBitmap())
            elif node.type == "util output":
                self.set_icon(node, icons8_vga_20.GetBitmap())
            elif node.type == "util input":
                self.set_icon(node, icons8_input_20.GetBitmap())
            elif node.type == "file":
                self.set_icon(node, icons8_file_20.GetBitmap())
            elif node.type == "group":
                self.set_icon(node, icons8_group_objects_20.GetBitmap())
        else:
            image_id = tree.GetItemImage(item)
            if image_id >= self.tree_images.ImageCount:
                image_id = -1
                # Reset Image Node in List
            if image_id < 0:
                image_id = self.tree_images.Add(bitmap=icon)
            else:
                self.tree_images.Replace(index=image_id, bitmap=icon)

            tree.SetItemImage(item, image=image_id)

    def update_op_labels(self):
        startnode = self.elements.get(type="branch ops").item
        child, cookie = self.wxtree.GetFirstChild(startnode)
        while child.IsOk():
            node = self.wxtree.GetItemData(child)  # Make sure the map is updated...
            formatter = self.elements.lookup(f"format/{node.type}")
            label = node.create_label(formatter)
            self.wxtree.SetItemText(child, label)
            child, cookie = self.wxtree.GetNextChild(startnode, cookie)

    def update_decorations(self, node, force=False):
        """
        Updates the decorations for a particular node/tree item

        @param node:
        @return:
        """
        if force is None:
            force = False
        if node.item is None:
            # This node is not registered the tree has desynced.
            self.rebuild_tree()
            return

        self.set_icon(node, force=force)
        formatter = self.elements.lookup(f"format/{node.type}")
        label = node.create_label(formatter)
        self.wxtree.SetItemText(node.item, label)
        try:
            stroke = node.stroke
            wxcolor = Color(stroke).bgr
            if wxcolor is not None:
                color = wx.Colour(wxcolor)
                self.wxtree.SetItemTextColour(node.item, color)
        except AttributeError:
            pass
        try:
            color = node.color
            wxcolor = Color(color).bgr
            if wxcolor is not None:
                c = wx.Colour(wxcolor)
                self.wxtree.SetItemTextColour(node.item, c)
        except AttributeError:
            pass

    def on_drag_begin_handler(self, event):
        """
        Drag handler begin for the tree.

        @param event:
        @return:
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

        @param event:
        @return:
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
            # Make sure that the drop node is visible
            self.wxtree.Expand(drop_item)
            self.wxtree.EnsureVisible(drop_item)
            self.refresh_tree(source="drag end")
            # self.rebuild_tree()
        self.dragging_nodes = None

    def on_item_right_click(self, event):
        """
        Right click of element in tree.

        @param event:
        @return:
        """
        item = event.GetItem()
        if item is None:
            return
        node = self.wxtree.GetItemData(item)

        create_menu(self.gui, node, self.elements)

    def on_item_activated(self, event):
        """
        Tree item is double-clicked. Launches PropertyWindow associated with that object.

        @param event:
        @return:
        """
        item = event.GetItem()
        node = self.wxtree.GetItemData(item)
        activate = self.elements.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(node)

    def activate_selected_node(self, *args):
        """
        Call activated on the first emphasized node.

        @param args:
        @return:
        """
        first_element = self.elements.first_element(emphasized=True)
        if hasattr(first_element, "node"):
            # Reference
            first_element = first_element.node
        activate = self.elements.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(first_element)

    def on_item_selection_changed(self, event):
        """
        Tree menu item is changed. Modify the selection.

        @param event:
        @return:
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
            if node.type == "reference":
                emphasized[i] = node.node
            elif node.type.startswith("op"):
                for n in node.flat(types=("reference",), cascade=False):
                    try:
                        emphasized.append(n.node)
                    except Exception:
                        pass
        self.elements.set_emphasis(emphasized)
        # self.refresh_tree(source="on_item_selection")
        event.Allow()

    def select_in_tree_by_emphasis(self, origin, *args):
        """
        Selected the actual `wx.tree` control those items which are currently emphasized.

        @return:
        """
        self.do_not_select = True
        for e in self.elements.elems_nodes(emphasized=True):
            self.wxtree.SelectItem(e.item, True)
        self.do_not_select = False
