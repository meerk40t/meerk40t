import wx
from wx import aui

from ..kernel import signal_listener
from ..svgelements import Color
from .icons import (
    icon_meerk40t,
    icons8_direction_20,
    icons8_file_20,
    icons8_group_objects_20,
    icons8_laser_beam_20,
    icons8_scatter_plot_20,
    icons8_smartphone_ram_50,
    icons8_system_task_20,
    icons8_vector_20,
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

    context.register(
        "format/op cut", "{enabled}{pass}{element_type} {speed}mm/s @{power}"
    )
    context.register(
        "format/op engrave", "{enabled}{pass}{element_type} {speed}mm/s @{power}"
    )
    context.register(
        "format/op hatch", "{enabled}{penpass}{pass}{element_type} {speed}mm/s @{power}"
    )
    context.register(
        "format/op raster",
        "{enabled}{pass}{element_type}{direction}{speed}mm/s @{power}",
    )
    context.register(
        "format/op image",
        "{enabled}{pass}{element_type}{direction}{speed}mm/s @{power}",
    )
    context.register(
        "format/op dots", "{enabled}{pass}{element_type} {dwell_time}ms dwell"
    )
    context.register("format/op console", "{enabled}{command}")
    context.register("format/elem ellipse", "{element_type} {id}")
    context.register("format/elem image", "{element_type} {id}")
    context.register("format/elem line", "{element_type} {id}")
    context.register("format/elem path", "{element_type} {id}")
    context.register("format/elem point", "{element_type} {id}")
    context.register("format/elem polyline", "{element_type} {id}")
    context.register("format/elem rect", "{element_type} {id}")
    context.register("format/elem text", "{element_type} {id}: {text}")
    context.register("format/reference", "*{reference}")
    context.register("format/group", "{element_type} {id}")
    context.register("format/file", "{element_type}: {filename}")
    context.register("format/lasercode", "{element_type}")
    context.register("format/cutcode", "{element_type}")
    context.register("format/branch ops", _("Operations"))
    context.register("format/branch elems", _("Elements"))
    context.register("format/branch reg", _("Regmarks"))


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
    def on_rebuild_tree_signal(self, origin, *args):
        """
        Called by 'rebuild_tree' signal. To refresh tree directly

        @param origin: the path of the originating signal
        @param args:
        @return:
        """
        self.shadow_tree.rebuild_tree()


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
    The shadowTree creates a 'wx.Tree' structure from the 'elements.tree' structure. It listens to updates to the elements
    tree and updates the GUI version accordingly. This tree does not permit alterations to it, rather it sends any
    requested alterations to the 'elements.tree' or the 'elements.elements' or 'elements.'operations' and when those are
    reflected in the tree, the shadow tree is updated accordingly.
    """

    def __init__(self, service, gui, wxtree):
        self.elements = service
        self.gui = gui
        self.wxtree = wxtree
        self.renderer = LaserRender(service.root)
        self.dragging_nodes = None
        self.tree_images = None
        self.name = "Project"

        self.do_not_select = False
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
        Notified that this node has been attached to teh tree.
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
        self.update_decorations(node)

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
        self.update_decorations(node)
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
        self.update_decorations(node)
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
        self.update_decorations(node)
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
        self.update_decorations(node)
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
        self.update_decorations(node)
        try:
            c = node.color
            self.set_color(node, c)
        except AttributeError:
            pass
        self.set_icon(node)
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
        self.set_icon(node)
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
            self.update_decorations(element.node)
        else:
            self.update_decorations(element)

    def on_element_update(self, *args):
        """
        Called by signal "element_property_update"
        @param args:
        @return:
        """
        element = args[0]
        if hasattr(element, "node"):
            self.update_decorations(element.node)
        else:
            self.update_decorations(element)

    def refresh_tree(self, node=None):
        """Any tree elements currently displaying wrong data as per elements should be updated to display
        the proper values and contexts and icons."""
        if node is None:
            elemtree = self.elements._tree
            node = elemtree.item
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
        """
        Tree requires being deleted and completely rebuilt.

        @return:
        """
        # Rebuild tree destroys the emphasis, so let's store it...
        emphasized_list = list(self.elements.elems(emphasized=True))
        elemtree = self.elements._tree
        self.dragging_nodes = None
        self.wxtree.DeleteAllItems()

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
            self.set_icon(n)

        node_elements = elemtree.get(type="branch elems")
        self.set_icon(node_elements, icons8_vector_20.GetBitmap())

        node_registration = elemtree.get(type="branch reg")
        self.set_icon(node_registration, icons8_vector_20.GetBitmap())

        # Expand Ops, Element, and Regmarks nodes only
        self.wxtree.CollapseAll()
        self.wxtree.Expand(node_operations.item)
        self.wxtree.Expand(node_elements.item)
        self.wxtree.Expand(node_registration.item)
        # Restore emphasiss
        for e in emphasized_list:
            e.emphasized = True

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
        self.set_icon(node)

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
        tree = self.wxtree
        if color is None:
            tree.SetItemTextColour(item, None)
        else:
            tree.SetItemTextColour(item, wx.Colour(swizzlecolor(color)))

    def set_icon(self, node, icon=None):
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
        try:
            item = node.item
        except AttributeError:
            return  # Node.item can be none if launched from ExecuteJob where the nodes are not part of the tree.
        if node.item is None:
            return
        tree = root.wxtree
        if icon is None:
            if node.type == "elem image":
                image = self.renderer.make_thumbnail(node.image, width=20, height=20)
                image_id = self.tree_images.Add(bitmap=image)
                tree.SetItemImage(item, image=image_id)
            elif node.type == "elem point":
                if node.stroke is not None and node.stroke.rgb is not None:
                    c = node.stroke
                else:
                    c = Color("black")
                self.set_icon(node, icons8_scatter_plot_20.GetBitmap(color=c))
                return
            elif node.type == "reference":
                image = self.renderer.make_raster(
                    node.node, node.node.bounds, width=20, height=20, bitmap=True
                )
                if image is not None:
                    image_id = self.tree_images.Add(bitmap=image)
                    tree.SetItemImage(item, image=image_id)
            elif node.type.startswith("elem "):
                image = self.renderer.make_raster(
                    node, node.bounds, width=20, height=20, bitmap=True
                )
                if image is not None:
                    image_id = self.tree_images.Add(bitmap=image)
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
            elif node.type == "op console":
                try:
                    c = node.color
                    self.set_color(node, c)
                except AttributeError:
                    c = None
                self.set_icon(node, icons8_system_task_20.GetBitmap(color=c))
            elif node.type == "file":
                self.set_icon(node, icons8_file_20.GetBitmap())
            elif node.type == "group":
                self.set_icon(node, icons8_group_objects_20.GetBitmap())
        else:
            image_id = self.tree_images.Add(bitmap=icon)
            tree.SetItemImage(item, image=image_id)

    def update_decorations(self, node):
        """
        Updates the decorations for a particular node/tree item

        @param node:
        @return:
        """
        self.set_icon(node)
        if node.item is None:
            # This node is not registered the tree has desynced.
            self.rebuild_tree()
            return

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
            self.rebuild_tree()
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
        self.refresh_tree()
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
