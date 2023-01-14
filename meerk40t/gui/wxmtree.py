import wx
from wx import aui

from ..kernel import signal_listener
from ..svgelements import Color
from .icons import (
    get_default_scale_factor,
    icon_meerk40t,
    icons8_bell_20,
    icons8_close_window_20,
    icons8_diagonal_20,
    icons8_direction_20,
    icons8_file_20,
    icons8_group_objects_20,
    icons8_home_20,
    icons8_image_20,
    icons8_input_20,
    icons8_laser_beam_20,
    icons8_lock_50,
    icons8_output_20,
    icons8_r_white,
    icons8_return_20,
    icons8_scatter_plot_20,
    icons8_small_beam_20,
    icons8_smartphone_ram_50,
    icons8_stop_gesture_20,
    icons8_system_task_20,
    icons8_timer_20,
    icons8_vector_20,
    icons8_visit_20,
    icons8_canvas_20,
    icons8_prototype_20,
    icons8_rectangular_20,
    icons8_oval_20,
    icons8_polyline_50,
    icons8_type_50,
    icons8_line_20,
    icons8_journey_20,
)
from .laserrender import DRAW_MODE_ICONS, LaserRender, swizzlecolor
from .mwindow import MWindow
from .wxutils import create_menu, get_key_name, is_navigation_key

_ = wx.GetTranslation


def register_panel_tree(window, context):
    wxtree = TreePanel(window, wx.ID_ANY, context=context)
    minwd = 75
    pane = (
        aui.AuiPaneInfo()
        .Name("tree")
        .Left()
        .MinSize(minwd, -1)
        .LeftDockable()
        .RightDockable()
        .BottomDockable(False)
        .Caption(_("Tree"))
        .CaptionVisible(not context.pane_lock)
        .TopDockable(False)
    )
    pane.dock_proportion = minwd
    pane.control = wxtree
    window.on_pane_create(pane)
    context.register("pane/tree", pane)


class TreePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        # Define Tree
        self.wxtree = wx.TreeCtrl(
            self,
            wx.ID_ANY,
            style=wx.TR_MULTIPLE
            | wx.TR_HAS_BUTTONS
            | wx.TR_HIDE_ROOT
            | wx.TR_LINES_AT_ROOT,
        )
        if wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127:
            self.wxtree.SetBackgroundColour(wx.Colour(50, 50, 50))

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.wxtree, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.__set_tree()
        self.wxtree.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.wxtree.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self._keybind_channel = self.context.channel("keybinds")

        self.context.signal("rebuild_tree")

    def __set_tree(self):
        self.shadow_tree = ShadowTree(
            self.context.elements, self.GetParent(), self.wxtree, self.context
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
        """
        Keydown for the tree does not execute navigation keys. These are only executed by the scene since they do
        useful work for the tree.

        Make sure the treectl can work on standard keys...

        @param event:
        @return:
        """
        event.Skip()
        keyvalue = get_key_name(event)
        if is_navigation_key(keyvalue):
            if self._keybind_channel:
                self._keybind_channel(
                    f"Tree key_down: {keyvalue} is a navigation key. Not processed."
                )
            return
        if self.context.bind.trigger(keyvalue):
            if self._keybind_channel:
                self._keybind_channel(f"Tree key_down: {keyvalue} is executed.")
        else:
            if self._keybind_channel:
                self._keybind_channel(f"Tree key_down: {keyvalue} was unbound.")

    def on_key_up(self, event):
        """
        Keyup for the tree does not execute navigation keys. These are only executed by the scene.

        Make sure the treectl can work on standard keys...

        @param event:
        @return:
        """
        event.Skip()
        keyvalue = get_key_name(event)
        if is_navigation_key(keyvalue):
            if self._keybind_channel:
                self._keybind_channel(
                    f"Tree key_up: {keyvalue} is a navigation key. Not processed."
                )
            return
        if self.context.bind.untrigger(keyvalue):
            if self._keybind_channel:
                self._keybind_channel(f"Tree key_up: {keyvalue} is executed.")
        else:
            if self._keybind_channel:
                self._keybind_channel(f"Tree key_up: {keyvalue} was unbound.")

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

    @signal_listener("activate_single_node")
    def on_shadow_select_activate_single_tree(self, origin, node=None, *args):
        if node is not None:
            node.selected = True
        # self.shadow_tree.activate_selected_node(origin, *args)

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

    @signal_listener("activate;device")
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
        self.shadow_tree.cache_hits = 0
        self.shadow_tree.cache_requests = 0
        self.shadow_tree.refresh_tree(source=f"signal_{origin}")
        if nodes is not None:
            if isinstance(nodes, (tuple, list)):
                # All Standard nodes first
                for node in nodes:
                    if node is None or node._item is None:
                        pass
                    else:
                        if node.type.startswith("elem "):
                            self.shadow_tree.set_icon(node, force=True)
                # Then all others
                for node in nodes:
                    if node is None or node._item is None:
                        pass
                    else:
                        if not node.type.startswith("elem "):
                            self.shadow_tree.set_icon(node, force=True)
                # Show the first node, but if that's the root node then ignore stuff
                if len(nodes) > 0:
                    node = nodes[0]
                else:
                    node = None
            else:
                node = nodes
                self.shadow_tree.set_icon(node, force=True)
            rootitem = self.shadow_tree.wxtree.GetRootItem()
            if not node is None and not node._item is None and node._item != rootitem:
                self.shadow_tree.wxtree.EnsureVisible(node._item)

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

    @signal_listener("updateop_tree")
    def on_update_op_labels_tree(self, origin, *args):
        self.shadow_tree.update_op_labels()


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

    def __init__(self, service, gui, wxtree, context):
        self.elements = service
        self.context = context
        self.gui = gui
        self.wxtree = wxtree
        self.renderer = LaserRender(service.root)
        self.dragging_nodes = None
        self.tree_images = None
        self.name = "Project"
        self._freeze = False
        self.iconsize = 20
        fact = get_default_scale_factor()
        if fact > 1.0:
            self.iconsize = int(self.iconsize * fact)

        self.do_not_select = False
        self.was_already_expanded = []
        service.add_service_delegate(self)
        self.setup_state_images()
        self.default_images = {
            "console home -f": icons8_home_20,
            "console move_abs": icons8_return_20,
            "console beep": icons8_bell_20,
            "console interrupt": icons8_stop_gesture_20,
            "console quit": icons8_close_window_20,
            "util wait": icons8_timer_20,
            "util home": icons8_home_20,
            "util goto": icons8_return_20,
            "util origin": icons8_visit_20,
            "util output": icons8_output_20,
            "util input": icons8_input_20,
            "util console": icons8_system_task_20,
            "op engrave": icons8_small_beam_20,
            "op cut": icons8_laser_beam_20,
            "op image": icons8_image_20,
            "op raster": icons8_direction_20,
            "op hatch": icons8_diagonal_20,
            "op dots": icons8_scatter_plot_20,
            "elem point": icons8_scatter_plot_20,
            "file": icons8_file_20,
            "group": icons8_group_objects_20,
            "elem rect": icons8_rectangular_20,
            "elem ellipse": icons8_oval_20,
            "elem image": icons8_image_20,
            "elem path": icons8_journey_20,
            "elem line": icons8_line_20,
            "elem polyline": icons8_polyline_50,
            "elem text": icons8_type_50,
        }
        self.image_cache = []
        self.cache_hits = 0
        self.cache_requests = 0
        self._too_big = False
        self.refresh_tree_counter = 0

    def service_attach(self, *args):
        self.elements.listen_tree(self)

    def service_detach(self, *args):
        self.elements.unlisten_tree(self)

    def setup_state_images(self):
        self.state_images = wx.ImageList()
        image = icons8_lock_50.GetBitmap(
            resize=(self.iconsize, self.iconsize), noadjustment=True
        )
        self.state_images.Create(width=self.iconsize, height=self.iconsize)
        image_id = self.state_images.Add(bitmap=image)
        image = icons8_r_white.GetBitmap(
            resize=(self.iconsize, self.iconsize), noadjustment=True
        )
        image_id = self.state_images.Add(bitmap=image)
        self.wxtree.SetStateImageList(self.state_images)

    def node_created(self, node, **kwargs):
        """
        Notified that this node has been created.
        @param node: Node that was created.
        @param kwargs:
        @return:
        """
        if self._freeze or self.context.elements.suppress_updates:
            return
        self.elements.signal("modified")

    def node_destroyed(self, node, **kwargs):
        """
        Notified that this node has been destroyed.
        @param node: Node that was destroyed.
        @param kwargs:
        @return:
        """
        if self._freeze or self.context.elements.suppress_updates:
            return
        self.elements.signal("modified")

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
        if self._freeze or self.context.elements.suppress_updates:
            return
        item = node._item
        if not item.IsOk():
            raise ValueError("Bad Item")
        try:
            self.update_decorations(node, force=True)
        except RuntimeError:
            # A timer can update after the tree closes.
            return

    def selected(self, node):
        """
        Notified that this node was selected.

        Directly selected within the tree, specifically selected within the treectrl
        @param node:
        @return:
        """
        if self._freeze or self.context.elements.suppress_updates:
            return
        item = node._item
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
        if self._freeze or self.context.elements.suppress_updates:
            return
        item = node._item
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
        if self._freeze or self.context.elements.suppress_updates:
            return
        item = node._item
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
        if self._freeze or self.context.elements.suppress_updates:
            return
        item = node._item
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
        if self._freeze or self.context.elements.suppress_updates:
            return
        okay = False
        item = None
        if node is not None and hasattr(node, "_item"):
            item = node._item
            if item is not None and item.IsOk():
                okay = True
        # print (f"Modified: {node}\nItem: {item}, Status={okay}")
        if not okay:
            return
        try:
            self.update_decorations(node, force=True)
        except RuntimeError:
            # A timer can update after the tree closes.
            return
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
        if self._freeze or self.context.elements.suppress_updates:
            return
        item = node._item
        if not item.IsOk():
            raise ValueError("Bad Item")
        try:
            self.update_decorations(node, force=True)
        except RuntimeError:
            # A timer can update after the tree closes.
            return
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
        if self._freeze or self.context.elements.suppress_updates:
            return
        item = node._item
        if not item.IsOk():
            raise ValueError("Bad Item")
        self.wxtree.ExpandAllChildren(item)
        self.set_expanded(item, 1)

    def collapse_within(self, node):
        # Tries to collapse children first, if there were any open,
        # return TRUE, if all were already collapsed, return FALSE
        result = False
        startnode = node._item
        try:
            pnode, cookie = self.wxtree.GetFirstChild(startnode)
        except:
            return
        were_expanded = []
        while pnode.IsOk():
            state = self.wxtree.IsExpanded(pnode)
            if state:
                result = True
                were_expanded.append(pnode)
            pnode, cookie = self.wxtree.GetNextChild(startnode, cookie)
        for pnode in were_expanded:
            cnode = self.wxtree.GetItemData(pnode)
            cnode.notify_collapse()
        return result

    def collapse(self, node):
        """
        Notified that this node was collapsed.

        @param node:
        @return:
        """
        item = node._item
        if not item.IsOk():
            raise ValueError("Bad Item")
        # Special treatment for branches, they only collapse fully,
        # if all their childrens were collapsed already
        if node.type.startswith("branch"):
            if self.collapse_within(node):
                return
        self.wxtree.CollapseAllChildren(item)
        if (
            item is self.wxtree.GetRootItem()
            or self.wxtree.GetItemParent(item) is self.wxtree.GetRootItem()
        ):
            self.wxtree.Expand(self.elements.get(type="branch ops")._item)
            self.wxtree.Expand(self.elements.get(type="branch elems")._item)
            self.wxtree.Expand(self.elements.get(type="branch reg")._item)

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
        if self._freeze or self.context.elements.suppress_updates:
            return
        item = node._item
        if item is None:
            # Could be a faulty refresh during an undo.
            return
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
        if self._freeze or self.context.elements.suppress_updates:
            return
        item = node._item
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
        if isinstance(element, (tuple, list)):
            for node in element:
                if hasattr(node, "node"):
                    node = node.node
                try:
                    self.update_decorations(node, force=True)
                except RuntimeError:
                    # A timer can update after the tree closes.
                    return
        else:
            try:
                self.update_decorations(element, force=True)
            except RuntimeError:
                # A timer can update after the tree closes.
                return

    def on_element_update(self, *args):
        """
        Called by signal "element_property_update"
        @param args:
        @return:
        """
        element = args[0]
        if isinstance(element, (tuple, list)):
            for node in element:
                if hasattr(node, "node"):
                    node = node.node
                try:
                    self.update_decorations(node, force=True)
                except RuntimeError:
                    # A timer can update after the tree closes.
                    return
        else:
            try:
                self.update_decorations(element, force=True)
            except RuntimeError:
                # A timer can update after the tree closes.
                return

    def refresh_tree(self, node=None, level=0, source=""):
        """
        This no longer has any relevance, as the updates are properly done outside...
        """
        # if node is None:
        #     self.context.elements.set_start_time("refresh_tree")
        #     self.refresh_tree_counter = 0
        #     elemtree = self.elements._tree
        #     node = elemtree._item
        #     level = 0
        # else:
        #     self.refresh_tree_counter += 1

        # if node is None:
        #     return
        # tree = self.wxtree
        # child, cookie = tree.GetFirstChild(node)
        # while child.IsOk():
        #     child_node = self.wxtree.GetItemData(child)
        #     if child_node.type in ("group", "file"):
        #         self.update_decorations(child_node, force=True)
        #     ct = self.wxtree.GetChildrenCount(child, recursively=False)
        #     if ct > 0:
        #         self.refresh_tree(child, level + 1)
        #     child, cookie = tree.GetNextChild(node, cookie)

        self.wxtree._freeze = False
        self.wxtree.Expand(self.elements.get(type="branch ops")._item)
        self.wxtree.Expand(self.elements.get(type="branch elems")._item)
        self.wxtree.Expand(self.elements.get(type="branch reg")._item)
        self.context.elements.set_end_time("full_load", True)

    def freeze_tree(self, status=None):
        if status is None:
            status = not self._freeze
        self._freeze = status
        self.wxtree.Enable(not self._freeze)

    def was_expanded(self, node, level):
        txt = self.wxtree.GetItemText(node)
        chk = f"{level}-{txt}"
        for elem in self.was_already_expanded:
            if chk == elem:
                return True
        return False

    def set_expanded(self, node, level):
        txt = self.wxtree.GetItemText(node)
        chk = f"{level}-{txt}"
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
            # That is not working as advertised...
            state = self.wxtree.IsExpanded(pnode)
            state = False  # otherwise every thing gets expanded...
            if state:
                self.was_already_expanded.append(f"{level}-{txt}")
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
            chk = f"{level}-{txt}"
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
        self._freeze = True
        self.reset_expanded()
        # Safety net - if we have too many elements it will take too log to create all preview icons...
        count = self.elements.count_elems() + self.elements.count_op()
        self._too_big = bool(count > 1000)
        # print(f"Was too big?! {count} -> {self._too_big}")

        self.parse_tree(self.wxtree.GetRootItem(), 0)
        # Rebuild tree destroys the emphasis, so let's store it...
        emphasized_list = list(self.elements.elems(emphasized=True))
        elemtree = self.elements._tree
        self.dragging_nodes = None
        self.wxtree.DeleteAllItems()
        if self.tree_images is not None:
            self.tree_images.Destroy()
            self.image_cache = []

        self.tree_images = wx.ImageList()
        self.tree_images.Create(width=self.iconsize, height=self.iconsize)

        self.wxtree.SetImageList(self.tree_images)
        elemtree._item = self.wxtree.AddRoot(self.name)

        self.wxtree.SetItemData(elemtree._item, elemtree)

        self.set_icon(
            elemtree,
            icon_meerk40t.GetBitmap(
                False, resize=(self.iconsize, self.iconsize), noadjustment=True
            ),
        )
        self.register_children(elemtree)

        node_operations = elemtree.get(type="branch ops")
        self.set_icon(
            node_operations,
            icons8_laser_beam_20.GetBitmap(
                resize=(self.iconsize, self.iconsize), noadjustment=True
            ),
        )

        for n in node_operations.children:
            self.set_icon(n, force=True)

        node_elements = elemtree.get(type="branch elems")
        self.set_icon(
            node_elements,
            icons8_canvas_20.GetBitmap(
                resize=(self.iconsize, self.iconsize), noadjustment=True
            ),
        )

        node_registration = elemtree.get(type="branch reg")
        self.set_icon(
            node_registration,
            icons8_prototype_20.GetBitmap(
                resize=(self.iconsize, self.iconsize), noadjustment=True
            ),
        )
        self.update_op_labels()
        # Expand Ops, Element, and Regmarks nodes only
        self.wxtree.CollapseAll()
        self.wxtree.Expand(node_operations._item)
        self.wxtree.Expand(node_elements._item)
        self.wxtree.Expand(node_registration._item)
        # Restore emphasis
        for e in emphasized_list:
            e.emphasized = True
        self.restore_tree(self.wxtree.GetRootItem(), 0)
        self._freeze = False

    def register_children(self, node):
        """
        All children of this node are registered.

        @param node:
        @return:
        """
        for child in node.children:
            self.node_register(child)
            self.register_children(child)
        if node.type in ("group", "file"):
            self.update_decorations(node, force=True)

    def unregister_children(self, node):
        """
        All children of this node are unregistered.
l
        @param node:l
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
        item = node._item
        if item is None:
            raise ValueError("Item was None for node " + repr(node))
        if not item.IsOk():
            raise ValueError("Bad Item")
        # We might need to update the decorations for all parent objects
        e = node.parent
        while e is not None:
            if e.type in ("group", "file"):
                self.update_decorations(e, force=True)
            else:
                break
            e = e.parent

        node.unregister_object()
        self.wxtree.Delete(node._item)
        for i in self.wxtree.GetSelections():
            self.wxtree.SelectItem(i, False)

    def safe_color(self, color_to_set):
        back_color = self.wxtree.GetBackgroundColour()
        rgb = back_color.Get()
        default_color = wx.Colour(
            red=255 - rgb[0], green=255 - rgb[1], blue=255 - rgb[2], alpha=128
        )
        if color_to_set is not None and color_to_set.argb is not None:
            mycolor = wx.Colour(swizzlecolor(color_to_set.argb))
            if mycolor.Get() == rgb:
                mycolor = default_color
        else:
            mycolor = default_color
        return mycolor

    def node_register(self, node, pos=None, **kwargs):
        """
        Node.item is added/inserted. Label is updated and values are set. Icon is set.

        @param node:
        @param pos:
        @param kwargs:
        @return:
        """
        parent = node.parent
        parent_item = parent._item
        tree = self.wxtree
        if pos is None:
            node._item = tree.AppendItem(parent_item, self.name)
        else:
            node._item = tree.InsertItem(parent_item, pos, self.name)
        tree.SetItemData(node._item, node)
        self.update_decorations(node, False)
        wxcolor = self.wxtree.GetForegroundColour()
        if node.type == "elem text":
            attribute_to_try = "fill"
        else:
            attribute_to_try = "stroke"
        if hasattr(node, attribute_to_try):
            wxcolor = self.safe_color(getattr(node, attribute_to_try))
        elif hasattr(node, "color"):
            wxcolor = self.safe_color(node.color)
        else:
            back_color = self.wxtree.GetBackgroundColour()
            rgb = back_color.Get()
            background = Color(rgb[0], rgb[1], rgb[2])
            if background is not None:
                c1 = Color("Black")
                c2 = Color("White")
                if Color.distance(background, c1) > Color.distance(background, c2):
                    textcolor = c1
                else:
                    textcolor = c2
                wxcolor = wx.Colour(swizzlecolor(textcolor))
        try:
            tree.SetItemTextColour(node._item, wxcolor)
        except (AttributeError, KeyError, TypeError):
            pass
        # We might need to update the decorations for all parent objects
        e = node.parent
        while e is not None:
            if e.type in ("group", "file"):
                self.update_decorations(e, force=True)
            else:
                break
            e = e.parent

    def set_enhancements(self, node):
        """
        Node in the tree is drawn special based on nodes current setting.
        @param node:
        @return:
        """
        tree = self.wxtree
        node_item = node._item
        if node_item is None:
            return
        if self._freeze or self.context.elements.suppress_updates:
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
        item = node._item
        if item is None:
            return
        if self._freeze or self.context.elements.suppress_updates:
            return
        tree = self.wxtree
        wxcolor = self.safe_color(color)
        tree.SetItemTextColour(item, wxcolor)

    def create_image_from_node(self, node):
        image = None
        mini_icon = self.context.root.mini_icon and not self._too_big
        c = None
        self.cache_requests += 1
        cached_id = -1
        # Do we have a standard representation?
        defaultcolor = Color("black")
        if mini_icon:
            if node.type == "elem image":
                image = self.renderer.make_thumbnail(
                    node.active_image, width=self.iconsize, height=self.iconsize
                )
            else:
                # Establish colors (and some images)
                if node.type.startswith("op ") or node.type.startswith("util "):
                    if (
                        hasattr(node, "color")
                        and node.color is not None
                        and node.color.argb is not None
                    ):
                        c = node.color
                elif node.type == "reference":
                    c, image, cached_id = self.create_image_from_node(node.node)
                elif node.type.startswith("elem "):
                    if (
                        hasattr(node, "stroke")
                        and node.stroke is not None
                        and node.stroke.argb is not None
                    ):
                        c = node.stroke
                if node.type.startswith("elem ") and node.type != "elem point":
                    image = self.renderer.make_raster(
                        node,
                        node.paint_bounds,
                        width=self.iconsize,
                        height=self.iconsize,
                        bitmap=True,
                        keep_ratio=True,
                    )
        else:
            # Establish at least colors (and an image for a reference)
            if node.type.startswith("op ") or node.type.startswith("util "):
                if (
                    hasattr(node, "color")
                    and node.color is not None
                    and node.color.argb is not None
                ):
                    c = node.color
            elif node.type == "reference":
                c, image, cached_id = self.create_image_from_node(node.node)
            elif node.type == "elem text":
                if (
                    hasattr(node, "fill")
                    and node.fill is not None
                    and node.fill.argb is not None
                ):
                    c = node.fill
            elif node.type.startswith("elem "):
                if (
                    hasattr(node, "stroke")
                    and node.stroke is not None
                    and node.stroke.argb is not None
                ):
                    c = node.stroke

        # Have we already established an image, if no let's use the default
        if image is None:
            img_obj = None
            found = ""
            tofind = node.type
            if tofind == "util console":
                # Let's see whether we find the keyword...
                for key in self.default_images:
                    if key.startswith("console "):
                        skey = key[8:]
                        if node.command is not None and skey in node.command:
                            found = key
                            break

            if not found and tofind in self.default_images:
                found = tofind

            if found:
                for stored_key, stored_color, img_obj, c_id in self.image_cache:
                    if stored_key == found and stored_color == c:
                        image = img_obj
                        cached_id = c_id
                        self.cache_hits += 1
                        # print (f"Restore id {cached_id} for {c} - {found}")
                        break
                if image is None:
                    # has not been found yet...
                    img_obj = self.default_images[found]
                    image = img_obj.GetBitmap(
                        color=c,
                        resize=(self.iconsize, self.iconsize),
                        noadjustment=True,
                    )
                    cached_id = self.tree_images.Add(bitmap=image)
                    # print(f"Store id {cached_id} for {c} - {found}")
                    self.image_cache.append((found, c, image, cached_id))

        if c is None:
            c = defaultcolor
        return c, image, cached_id

    def set_icon(self, node, icon=None, force=False):
        """
        Node icon to be created and applied

        @param node: Node to have the icon set.
        @param icon: overriding icon to be forcibly set, rather than a default.
        @return: item_id if newly created / update
        """
        root = self
        drawmode = self.elements.root.draw_mode
        if drawmode & DRAW_MODE_ICONS != 0:
            return
        # if self._freeze or self.context.elements.suppress_updates:
        #     return
        if node is None:
            return
        try:
            item = node._item
        except AttributeError:
            return  # Node.item can be none if launched from ExecuteJob where the nodes are not part of the tree.
        if node._item is None:
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
                return image_id

            # print ("Default size for iconsize, tree_images", self.iconsize, self.tree_images.GetSize())
            c, image, cached_id = self.create_image_from_node(node)

            if image is not None:
                if cached_id >= 0:
                    image_id = cached_id
                elif image_id < 0:
                    image_id = self.tree_images.Add(bitmap=image)
                else:
                    self.tree_images.Replace(index=image_id, bitmap=image)
                tree.SetItemImage(item, image=image_id)
                # Let's have a look at all references....
                for subnode in node._references:
                    try:
                        subitem = subnode._item
                    except AttributeError:
                        subitem = None
                    if subitem is None:
                        continue
                    tree.SetItemImage(subitem, image=image_id)

            if c is not None:
                self.set_color(node, c)

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
        return image_id

    def update_op_labels(self):
        startnode = self.elements.get(type="branch ops")._item
        child, cookie = self.wxtree.GetFirstChild(startnode)
        while child.IsOk():
            node = self.wxtree.GetItemData(child)  # Make sure the map is updated...
            self.update_decorations(node=node, force=True)
            child, cookie = self.wxtree.GetNextChild(startnode, cookie)

    def update_decorations(self, node, force=False):
        """
        Updates the decorations for a particular node/tree item

        @param node:
        @return:
        """

        def my_create_label(node, text=None):
            if text is None:
                text = "{element_type}:{id}"
            # Just for the optical impression (who understands what a "Rect: None" means),
            # lets replace some of the more obvious ones...
            mymap = node.default_map()
            for key in mymap:
                if hasattr(node, key) and key in mymap and mymap[key] == "None":
                    if getattr(node, key) is None:
                        mymap[key] = "-"
            # There are a couple of translatable entries,
            # to make sure we don't get an unwanted translation we add
            # a special pattern to it
            translatable = (
                "element_type",
                "enabled",
            )
            pattern = "_TREE_"
            for key in mymap:
                if key in translatable:
                    # Original value
                    std = mymap[key]
                    value = _(pattern + std)
                    if not value.startswith(pattern):
                        mymap[key] = value
            try:
                res = text.format_map(mymap)
            except KeyError:
                res = text
            return res

        def get_formatter(nodetype):
            default = self.context.elements.lookup(f"format/{nodetype}")
            lbl = nodetype.replace(" ", "_")
            check_string = f"formatter_{lbl}_active"
            pattern_string = f"formatter_{lbl}"
            self.context.device.setting(bool, check_string, False)
            self.context.device.setting(str, pattern_string, default)
            bespoke = getattr(self.context.device, check_string, False)
            pattern = getattr(self.context.device, pattern_string, "")
            if bespoke and pattern is not None and pattern != "":
                default = pattern
            return default

        if force is None:
            force = False
        if node._item is None:
            # This node is not registered the tree has desynced.
            self.rebuild_tree()
            return

        self.set_icon(node, force=force)
        if hasattr(node, "node") and node.node is not None:
            formatter = get_formatter(node.node.type)
            if node.node.type.startswith("op "):
                if not self.context.elements.op_show_default:
                    if hasattr(node.node, "speed"):
                        node.node.speed = node.node.speed
                    if hasattr(node.node, "power"):
                        node.node.power = node.node.power
                    if hasattr(node.node, "dwell_time"):
                        node.node.dwell_time = node.node.dwell_time

                checker = f"dangerlevel_{node.type.replace(' ', '_')}"
                if hasattr(self.context.device, checker):
                    maxspeed_minpower = getattr(self.context.device, checker)
                    if (
                        isinstance(maxspeed_minpower, (tuple, list))
                        and len(maxspeed_minpower) == 8
                    ):
                        # minpower, maxposer, minspeed, maxspeed
                        # print ("Yes: ", checker, maxspeed_minpower)
                        danger = False
                        if hasattr(node.node, "power"):
                            value = node.node.power
                            if maxspeed_minpower[0] and value < maxspeed_minpower[1]:
                                danger = True
                            if maxspeed_minpower[2] and value > maxspeed_minpower[3]:
                                danger = True
                        if hasattr(node.node, "speed"):
                            value = node.node.speed
                            if maxspeed_minpower[4] and value < maxspeed_minpower[5]:
                                danger = True
                            if maxspeed_minpower[6] and value > maxspeed_minpower[7]:
                                danger = True
                        if hasattr(node.node, "dangerous"):
                            node.node.dangerous = danger
                    else:
                        setattr(self.context.device, checker, [False, 0] * 4)
                        print(
                            f"That's strange {checker}: {type(maxspeed_minpower).__name__}"
                        )
                # node.node.is_dangerous(maxspeed, minpower)
            # label = "*" + node.node.create_label(formatter)
            label = "*" + my_create_label(node.node, formatter)
        else:
            formatter = get_formatter(node.type)
            if node.type.startswith("op "):
                # Not too elegant... op nodes should have a property default_speed, default_power
                if not self.context.elements.op_show_default:
                    if hasattr(node, "speed"):
                        node.speed = node.speed
                    if hasattr(node, "power"):
                        node.power = node.power
                    if hasattr(node, "dwell_time"):
                        node.dwell_time = node.dwell_time
                checker = f"dangerlevel_{node.type.replace(' ', '_')}"
                if hasattr(self.context.device, checker):
                    maxspeed_minpower = getattr(self.context.device, checker)
                    if (
                        isinstance(maxspeed_minpower, (tuple, list))
                        and len(maxspeed_minpower) == 8
                    ):
                        # minpower, maxposer, minspeed, maxspeed
                        # print ("Yes: ", checker, maxspeed_minpower)
                        danger = False
                        if hasattr(node, "power"):
                            value = float(node.power)
                            if maxspeed_minpower[0] and value < maxspeed_minpower[1]:
                                danger = True
                            if maxspeed_minpower[2] and value > maxspeed_minpower[3]:
                                danger = True
                        if hasattr(node, "speed"):
                            value = float(node.speed)
                            if maxspeed_minpower[4] and value < maxspeed_minpower[5]:
                                danger = True
                            if maxspeed_minpower[6] and value > maxspeed_minpower[7]:
                                danger = True
                        if hasattr(node, "dangerous"):
                            node.dangerous = danger
                    else:
                        setattr(self.context.device, checker, [False, 0] * 4)
                        print(
                            f"That's strange {checker}: {type(maxspeed_minpower).__name__}"
                        )
            # label = node.create_label(formatter)
            label = my_create_label(node, formatter)

        self.wxtree.SetItemText(node._item, label)
        if node.type == "elem text":
            attribute_to_try = "fill"
        else:
            attribute_to_try = "stroke"
        wxcolor = None
        if hasattr(node, attribute_to_try):
            wxcolor = self.safe_color(getattr(node, attribute_to_try))
        elif hasattr(node, "color"):
            wxcolor = self.safe_color(node.color)
        else:
            back_color = self.wxtree.GetBackgroundColour()
            rgb = back_color.Get()
            background = Color(rgb[0], rgb[1], rgb[2])
            if background is not None:
                c1 = Color("Black")
                c2 = Color("White")
                if Color.distance(background, c1) > Color.distance(background, c2):
                    textcolor = c1
                else:
                    textcolor = c2
                wxcolor = wx.Colour(swizzlecolor(textcolor))
        try:
            self.wxtree.SetItemTextColour(node._item, wxcolor)
        except (AttributeError, KeyError, TypeError):
            pass

        state_num = -1
        # Has the node a lock attribute?
        if hasattr(node, "lock"):
            lockit = node.lock
        else:
            lockit = False
        if lockit:
            state_num = 0

        scene = getattr(self.context.root, "mainscene", None)
        if scene is not None:
            if node == scene.reference_object:
                state_num = 1
        if state_num >= 0:
            self.wxtree.SetItemState(node._item, state_num)
        else:
            self.wxtree.SetItemState(node._item, wx.TREE_ITEMSTATE_NONE)

    def on_drag_begin_handler(self, event):
        """
        Drag handler begin for the tree.

        @param event:
        @return:
        """

        def typefamily(typename):
            # Combine similar nodetypes
            if typename.startswith("op "):
                result = "op"
            elif typename.startswith("elem "):
                result = "elem"
            else:
                result = typename
            return result

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

        t = typefamily(self.dragging_nodes[0].type)
        for n in self.dragging_nodes:
            tt = typefamily(n.type)
            if t != tt:
                # Different typefamilies
                event.Skip()
                return
            if not n.is_draggable():
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
        # We extend the logic by calling the appropriate elems routine
        skip = not self.elements.drag_and_drop(self.dragging_nodes, drop_node)
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

        # Just out of curiosity, is there no image set? Then just do it again.
        item = event.GetItem()
        if item:
            image_id = self.wxtree.GetItemImage(item)
            if image_id >= self.tree_images.ImageCount:
                image_id = -1
            if image_id < 0:
                node = self.wxtree.GetItemData(item)
                if node is not None:
                    self.set_icon(node, force=True)

        selected = [
            self.wxtree.GetItemData(item) for item in self.wxtree.GetSelections()
        ]

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
        self.elements.set_selected(selected)
        # self.refresh_tree(source="on_item_selection")
        event.Allow()

    def select_in_tree_by_emphasis(self, origin, *args):
        """
        Selected the actual `wx.tree` control those items which are currently emphasized.

        @return:
        """
        self.do_not_select = True
        self.wxtree.UnselectAll()

        for e in self.elements.elems_nodes(emphasized=True):
            self.wxtree.SelectItem(e._item, True)
        self.do_not_select = False
