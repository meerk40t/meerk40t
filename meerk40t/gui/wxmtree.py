import wx
from wx import aui

from meerk40t.core.elements.element_types import op_nodes, elem_nodes

from ..core.units import Length
from ..kernel import signal_listener
from ..svgelements import Color
from .basicops import BasicOpPanel
from .icons import (
    icon_bell,
    icon_bmap_text,
    icon_canvas,
    icon_close_window,
    icon_console,
    icon_distort,
    icon_effect_hatch,
    icon_effect_wobble,
    icon_external,
    icon_internal,
    icon_line,
    icon_meerk40t,
    icon_mk_ellipse,
    icon_mk_polyline,
    icon_mk_rectangular,
    icon_path,
    icon_points,
    icon_regmarks,
    icon_return,
    icon_round_stop,
    icon_timer,
    icon_tree,
    icon_warning,
    icons8_direction,
    icons8_file,
    icons8_ghost,
    icons8_group_objects,
    icons8_home_filled,
    icons8_image,
    icons8_laser_beam,
    icons8_laserbeam_weak,
    icons8_lock,
    icons8_r_white,
)
from .laserrender import DRAW_MODE_ICONS, LaserRender, swizzlecolor
from .mwindow import MWindow
from .wxutils import (
    StaticBoxSizer,
    create_menu,
    dip_size,
    get_key_name,
    is_navigation_key,
    wxButton,
    wxTreeCtrl,
)

_ = wx.GetTranslation


def register_panel_tree(window, context):
    lastpage = context.root.setting(int, "tree_panel_page", 1)
    if lastpage is None or lastpage < 0 or lastpage > 2:
        lastpage = 0

    basic_op = BasicOpPanel(window, wx.ID_ANY, context=context)
    wxtree = TreePanel(window, wx.ID_ANY, context=context)

    def on_panel_change(context):
        def handler(event):
            mycontext.root.setting(int, "tree_panel_page", 1)
            pagenum = notetab.GetSelection()
            setattr(mycontext.root, "tree_panel_page", pagenum)
            if pagenum == 0:
                basic_op.pane_show()
                wxtree.pane_hide()
            else:
                basic_op.pane_hide()
                wxtree.pane_show()

        mycontext = context
        return handler

    # ARGGH, the color setting via the ArtProvider does only work
    # if you set the tabs to the bottom! wx.aui.AUI_NB_BOTTOM
    notetab = wx.aui.AuiNotebook(
        window,
        wx.ID_ANY,
        style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
        | wx.aui.AUI_NB_SCROLL_BUTTONS
        | wx.aui.AUI_NB_TAB_SPLIT
        | wx.aui.AUI_NB_TAB_MOVE
        | wx.aui.AUI_NB_BOTTOM,
    )
    context.themes.set_window_colors(notetab)
    bg_std = context.themes.get("win_bg")
    bg_active = context.themes.get("highlight")
    notetab.GetArtProvider().SetColour(bg_std)
    notetab.GetArtProvider().SetActiveColour(bg_active)

    pane = (
        aui.AuiPaneInfo()
        .Name("tree")
        .Right()
        .MinSize(200, 180)
        .BestSize(300, 270)
        .FloatingSize(300, 270)
        .LeftDockable()
        .RightDockable()
        .BottomDockable(False)
        .Caption(_("Tree"))
        .CaptionVisible(not context.pane_lock)
        .TopDockable(False)
    )
    pane.helptext = _("Tree containing all objects")
    notetab.AddPage(basic_op, _("Burn-Operation"))
    notetab.AddPage(wxtree, _("Details"))
    notetab.SetSelection(lastpage)
    notetab.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, on_panel_change(context))
    pane.dock_proportion = 500
    pane.control = notetab
    window.on_pane_create(pane)
    context.register("pane/tree", pane)


class TreePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        # Define Tree
        self.wxtree = wxTreeCtrl(
            self,
            wx.ID_ANY,
            style=wx.TR_MULTIPLE
            | wx.TR_HAS_BUTTONS
            | wx.TR_HIDE_ROOT
            | wx.TR_LINES_AT_ROOT,
        )
        # try:
        #     res = wx.SystemSettings().GetAppearance().IsDark()
        # except AttributeError:
        #     res = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        self.SetHelpText(
            "tree"
        )  # That will be used for all controls in this window, unless stated differently

        self.setup_warn_panel()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.wxtree, 1, wx.EXPAND, 0)
        main_sizer.Add(self.warn_panel, 0, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.__set_tree()
        self.wxtree.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.wxtree.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self._keybind_channel = self.context.channel("keybinds")

        self.context.signal("rebuild_tree", "all")

    def setup_warn_panel(self):
        def fix_unassigned_create(event):
            previous = self.context.elements.classify_autogenerate
            self.context.elements.classify_autogenerate = True
            target_list = list(self.context.elements.unassigned_elements())
            self.context.elements.classify(target_list)
            self.context.elements.classify_autogenerate = previous
            self.context.elements.signal("refresh_tree")

        def fix_unassigned_used(event):
            previous = self.context.elements.classify_autogenerate
            self.context.elements.classify_autogenerate = False
            target_list = list(self.context.elements.unassigned_elements())
            self.context.elements.classify(target_list)
            self.context.elements.classify_autogenerate = previous
            self.context.elements.signal("refresh_tree")

        def fix_unburnt(event):
            to_reload = []
            for node in self.context.elements.elems():
                will_be_burnt = False
                first_op = None
                for refnode in node._references:
                    op = refnode.parent
                    if op is not None:
                        try:
                            if op.output:
                                will_be_burnt = True
                                break
                            else:
                                if first_op is None:
                                    first_op = op
                        except AttributeError:
                            pass
                if not will_be_burnt and first_op is not None:
                    try:
                        first_op.output = True
                        to_reload.append(first_op)
                    except AttributeError:
                        pass
            if to_reload:
                self.context.elements.signal(
                    "element_property_reload", to_reload
                )
                self.context.elements.signal("warn_state_update")

        self.warn_panel = wx.BoxSizer(wx.HORIZONTAL)
        unassigned_frame = StaticBoxSizer(self, wx.ID_ANY, "Unassigned", wx.HORIZONTAL)
        unburnt_frame = StaticBoxSizer(self, wx.ID_ANY, "Non-burnt", wx.HORIZONTAL)
        self.btn_fix_assign_create = wxButton(self, wx.ID_ANY, "Assign (+new)")
        self.btn_fix_assign_existing = wxButton(self, wx.ID_ANY, "Assign")
        self.btn_fix_unburnt = wxButton(self, wx.ID_ANY, "Enable")
        self.btn_fix_assign_create.SetToolTip(
            _("Classify unassigned elements and create operations if necessary")
        )
        self.btn_fix_assign_existing.SetToolTip(
            _("Classify unassigned elements and use only existing operations")
        )
        self.btn_fix_unburnt.SetToolTip(
            _("Reactivate disabled operations that prevent elements from being burnt")
        )

        unassigned_frame.Add(self.btn_fix_assign_create, 0, wx.EXPAND, 0)
        unassigned_frame.Add(self.btn_fix_assign_existing, 0, wx.EXPAND, 0)
        unburnt_frame.Add(self.btn_fix_unburnt, 0, wx.EXPAND, 0)
        self.warn_panel.Add(unassigned_frame, 1, wx.EXPAND, 0)
        self.warn_panel.Add(unburnt_frame, 1, wx.EXPAND, 0)
        self._last_issue = None
        self.warn_panel.Show(False)
        self.warn_panel.ShowItems(False)
        self.Bind(wx.EVT_BUTTON, fix_unassigned_create, self.btn_fix_assign_create)
        self.Bind(wx.EVT_BUTTON, fix_unassigned_used, self.btn_fix_assign_existing)
        self.Bind(wx.EVT_BUTTON, fix_unburnt, self.btn_fix_unburnt)
        # self.Show(False)

    def check_for_issues(self):
        needs_showing = False
        non_assigned, non_burn = self.context.elements.have_unburnable_elements()
        warn_level = self.context.setting(int, "concern_level", 1)
        if non_assigned and warn_level <= 2:
            needs_showing = True
        if non_burn and warn_level <= 1:
            needs_showing = True
        self.btn_fix_assign_create.Enable(non_assigned)
        self.btn_fix_assign_existing.Enable(non_assigned)
        self.btn_fix_unburnt.Enable(non_burn)
        new_issue = non_assigned or non_burn
        if (self._last_issue == new_issue) and (needs_showing == self.btn_fix_unburnt.IsShown()):
            # no changes
            return
        self._last_issue = new_issue
        if new_issue and needs_showing:
            self.warn_panel.Show(True)
            self.warn_panel.ShowItems(True)
        else:
            self.warn_panel.Show(False)
            self.warn_panel.ShowItems(False)
        self.Layout()

    def __set_tree(self):
        self.shadow_tree = ShadowTree(
            self.context.elements, self.GetParent(), self.wxtree, self.context
        )

        # self.Bind(
        #     wx.EVT_TREE_BEGIN_DRAG, self.shadow_tree.on_drag_begin_handler, self.wxtree
        # )
        self.shadow_tree.wxtree.Bind(
            wx.EVT_TREE_BEGIN_DRAG, self.shadow_tree.on_drag_begin_handler
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
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.shadow_tree.on_collapse, self.wxtree)
        self.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.shadow_tree.on_expand, self.wxtree)
        self.Bind(wx.EVT_TREE_STATE_IMAGE_CLICK, self.shadow_tree.on_state_icon, self.wxtree)

        self.wxtree.Bind(wx.EVT_MOTION, self.shadow_tree.on_mouse_over)
        self.wxtree.Bind(wx.EVT_LEAVE_WINDOW, self.on_lost_focus, self.wxtree)

    def on_lost_focus(self, event):
        self.wxtree.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

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
        keyvalue = get_key_name(event)
        # There is a menu entry in wxmain that should catch all 'delete' keys
        # but that is not consistently so, every other key seems to slip through
        # probably there is an issue there, but we use the opportunity not
        # only to catch these but to establish a forced delete via ctrl-delete as well

        if keyvalue == "delete":
            self.context("tree selected delete\n")
            return
        if keyvalue == "ctrl+delete":
            self.context("tree selected remove\n")
            return
        event.Skip()
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

    @signal_listener("updateop_tree")
    @signal_listener("warn_state_update")
    def on_warn_state_update(self, origin, *args):
        # Updates the warning state, using signal to avoid unnecessary calls
        self.shadow_tree.update_warn_sign()
        self.check_for_issues()

    @signal_listener("update_group_labels")
    def on_group_update(self, origin, *args):
        self.shadow_tree.update_group_labels("signal")

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
            stop_updates = not self.shadow_tree._freeze
            if stop_updates:
                self.shadow_tree.freeze_tree(True)
            self.shadow_tree.on_element_update(*args)
            if stop_updates:
                self.shadow_tree.freeze_tree(False)

    @signal_listener("element_property_reload")
    def on_force_element_update(self, origin, *args):
        """
        Called by 'element_property_reload' when the properties of an element are changed.

        @param origin: the path of the originating signal
        @param args:
        @return:
        """
        if self.shadow_tree is not None:
            stop_updates = not self.shadow_tree._freeze
            if stop_updates:
                self.shadow_tree.freeze_tree(True)
            self.shadow_tree.on_force_element_update(*args)
            if stop_updates:
                self.shadow_tree.freeze_tree(False)

    @signal_listener("activate;device")
    def on_activate_device(self, origin, target=None, *args):
        self.shadow_tree.reset_formatter_cache()
        self.shadow_tree.refresh_tree(source="device")

    @signal_listener("reset_formatter")
    def on_reset_formatter(self, origin, target=None, *args):
        self.shadow_tree.reset_formatter_cache()

    @signal_listener("sync_expansion")
    def on_sync_expansion(self, origin, target=None, *args):
        self.shadow_tree.sync_expansion()

    @signal_listener("rebuild_tree")
    def on_rebuild_tree_signal(self, origin, target=None, *args):
        """
        Called by 'rebuild_tree' signal. To rebuild the tree directly

        @param origin: the path of the originating signal
        @param target: target device
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
        if target is None:
            target = "all"
        self.shadow_tree.rebuild_tree(source="signal", target=target)

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
                    if node is not None and node._item is not None and node.type.startswith("elem "):
                        self.shadow_tree.set_icon(node, force=True)
                # Then all others
                for node in nodes:
                    if node is not None and node._item is not None and not node.type.startswith("elem "):
                        self.shadow_tree.set_icon(node, force=True)
                # Show the first node, but if that's the root node then ignore stuff
                node = nodes[0] if len(nodes) > 0 else None
            else:
                node = nodes
                self.shadow_tree.set_icon(node, force=True)
            rootitem = self.shadow_tree.wxtree.GetRootItem()
            if (
                node is not None
                and node._item is not None
                and node._item != rootitem
            ):
                self.shadow_tree.wxtree.EnsureVisible(node._item)

    @signal_listener("freeze_tree")
    def on_freeze_tree_signal(self, origin, status=None, *args):
        """
        Called by 'rebuild_tree' signal. Halts any updates like set_decorations and others

        @param origin: the path of the originating signal
        @param status: true, false (evident what they do), None: to toggle
        @param args:
        @return:
        """
        self.shadow_tree.freeze_tree(status)

    @signal_listener("updateop_tree")
    def on_update_op_labels_tree(self, origin, *args):
        stop_updates = not self.shadow_tree._freeze
        if stop_updates:
            self.shadow_tree.freeze_tree(True)
        self.shadow_tree.update_op_labels()
        opitem = self.context.elements.get(type="branch ops")._item
        if opitem is None:
            return
        tree = self.shadow_tree.wxtree
        tree.Expand(opitem)
        if stop_updates:
            self.shadow_tree.freeze_tree(False)

    @signal_listener("updateelem_tree")
    def on_update_elem_tree(self, origin, *args):
        elitem = self.context.elements.get(type="branch elems")._item
        if elitem is None:
            return
        tree = self.shadow_tree.wxtree
        tree.Expand(elitem)


class ElementsTree(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(423, 131, *args, **kwds)

        self.panel = TreePanel(self, wx.ID_ANY, context=self.context)
        self.sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_tree.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Tree"))
        self.restore_aspect()

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
        testsize = dip_size(self.wxtree, 20, 20)
        self.iconsize = testsize[1]
        self.iconstates = {}
        self.last_call = 0
        self._nodes_to_expand = []

        # fact = get_default_scale_factor()
        # if fact > 1.0:
        #    self.iconsize = int(self.iconsize * fact)

        self.do_not_select = False
        self.was_already_expanded = []
        service.add_service_delegate(self)
        self.setup_state_images()
        self.default_images = {
            "console home -f": icons8_home_filled,
            "console move_abs": icon_return,
            "console beep": icon_bell,
            "console interrupt": icon_round_stop,
            "console quit": icon_close_window,
            "util wait": icon_timer,
            "util home": icons8_home_filled,
            "util goto": icon_return,
            "util output": icon_external,
            "util input": icon_internal,
            "util console": icon_console,
            "op engrave": icons8_laserbeam_weak,
            "op cut": icons8_laser_beam,
            "op image": icons8_image,
            "op raster": icons8_direction,
            "op dots": icon_points,
            "effect hatch": icon_effect_hatch,
            "effect wobble": icon_effect_wobble,
            "effect warp": icon_distort,
            "place current": icons8_home_filled,
            "place point": icons8_home_filled,
            "elem point": icon_points,
            "file": icons8_file,
            "group": icons8_group_objects,
            "elem rect": icon_mk_rectangular,
            "elem ellipse": icon_mk_ellipse,
            "elem image": icons8_image,
            "elem path": icon_path,
            "elem line": icon_line,
            "elem polyline": icon_mk_polyline,
            "elem text": icon_bmap_text,
            "image raster": icons8_image,
            "blob": icons8_file,
        }
        self.image_cache = []
        self.cache_hits = 0
        self.cache_requests = 0
        self.color_cache = {}
        self.formatter_cache = {}
        self._too_big = False
        self.refresh_tree_counter = 0
        self._last_hover_item = None

    def service_attach(self, *args):
        self.elements.listen_tree(self)

    def service_detach(self, *args):
        self.elements.unlisten_tree(self)

    def setup_state_images(self):
        self.state_images = wx.ImageList()
        self.iconstates = {}
        self.state_images.Create(width=self.iconsize, height=self.iconsize)
        image = icons8_lock.GetBitmap(
            resize=(self.iconsize, self.iconsize),
            noadjustment=True,
            buffer=1,
        )
        image_id = self.state_images.Add(bitmap=image)
        self.iconstates["lock"] = image_id
        image = icons8_r_white.GetBitmap(
            resize=(self.iconsize, self.iconsize),
            noadjustment=True,
            buffer=1,
        )
        image_id = self.state_images.Add(bitmap=image)
        self.iconstates["refobject"] = image_id
        image = icon_warning.GetBitmap(
            resize=(self.iconsize, self.iconsize),
            noadjustment=True,
            buffer=1,
        )
        image_id = self.state_images.Add(bitmap=image)
        self.iconstates["warning"] = image_id
        image = icons8_ghost.GetBitmap(
            resize=(self.iconsize, self.iconsize),
            noadjustment=True,
            buffer=1,
        )
        image_id = self.state_images.Add(bitmap=image)
        self.iconstates["ghost"] = image_id
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
        self.elements.signal("warn_state_update")

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
        if node.expanded:
            # Needs to be done later...
            self._nodes_to_expand.append(node)
            if not self.context.elements.suppress_signalling:
                self.context.elements.signal("sync_expansion")

    def sync_expansion(self):
        for node in self._nodes_to_expand:
            item = node._item
            if item is None or not item.IsOk():
                continue
            if node.expanded:
                self.wxtree.Expand(item)
            else:
                self.wxtree.Collapse(item)
        self._nodes_to_expand.clear()

    def node_changed(self, node):
        """
        Notified that this node has been changed.
        @param node: Node that was changed.
        @return:
        """
        if self._freeze or self.context.elements.suppress_updates:
            return
        item = node._item
        self.check_validity(item)
        try:
            self.update_decorations(node, force=True)
        except RuntimeError:
            # A timer can update after the tree closes.
            return

    def check_validity(self, item):
        if item is None or not item.IsOk():
            # raise ValueError("Bad Item")
            self.rebuild_tree(source="validity", target="all")
            self.elements.signal("refresh_scene", "Scene")
            return False
        return True

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
        self.check_validity(item)
        # self.update_decorations(node)
        self.set_enhancements(node)
        if not self.context.elements.suppress_signalling:
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
        self.check_validity(item)
        # self.update_decorations(node)
        self.set_enhancements(node)
        if not self.context.elements.suppress_signalling:
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
        self.check_validity(item)
        self.update_decorations(node)
        self.set_enhancements(node)
        if not self.context.elements.suppress_signalling:
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
        self.check_validity(item)
        # self.update_decorations(node)
        self.set_enhancements(node)
        if not self.context.elements.suppress_signalling:
            self.elements.signal("highlighted", node)

    def translated(self, node, dx=0, dy=0, interim=False, *args):
        """
        This node was moved
        """
        return

    def scaled(self, node, sx=1, sy=1, ox=0, oy=0, interim=False, *args):
        """
        This node was scaled
        """
        return

    def modified(self, node):
        """
        Notified that this node was modified.
        This node position values were changed, but nothing about the core data was altered.
        @param node:
        @return:
        """
        if self._freeze or self.context.elements.suppress_updates:
            return

        if node is None or not hasattr(node, "_item"):
            return

        item = node._item
        if item is None or not item.IsOk():
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

    def altered(self, node, *args, **kwargs):
        """
        Notified that this node was altered.
        This node was changed in fundamental ways and nothing about this node remains trusted.
        @param node:
        @return:
        """
        if self._freeze or self.context.elements.suppress_updates:
            return
        item = node._item
        self.check_validity(item)
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
        node.expanded = True
        item = node._item
        self.check_validity(item)
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
            if self.wxtree.IsExpanded(pnode):
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
        if node is None:
            return
        node.expanded = False
        item = node._item
        if item is None:
            return
        self.check_validity(item)
        # Special treatment for branches, they only collapse fully,
        # if all their childrens were collapsed already
        if node.type.startswith("branch") and self.collapse_within(node):
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
        target = "all"
        while node.parent is not None:
            if node.parent.type == "branch reg":
                target = "regmarks"
                break
            if node.parent.type == "branch elem":
                target = "elements"
                break
            if node.parent.type == "branch ops":
                target = "operations"
                break
            node = node.parent
        
        self.rebuild_tree("reorder", target=target)

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
        self.check_validity(item)
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
        self.check_validity(item)
        self.wxtree.EnsureVisible(item)
        self.wxtree.ScrollTo(item)
        # self.wxtree.SetFocusedItem(item)

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
                    for refnode in node.references:
                        self.update_decorations(refnode, force=True)
                except RuntimeError:
                    # A timer can update after the tree closes.
                    return
        else:
            try:
                self.update_decorations(element, force=True)
                for refnode in element.references:
                    self.update_decorations(refnode, force=True)
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
        self.context.elements.set_start_time("refresh_tree")
        self.freeze_tree(True)
        self.update_op_labels()
        if node is not None:
            if isinstance(node, (tuple, list)):
                for enode in node:
                    if hasattr(enode, "node"):
                        enode = enode.node
                    try:
                        self.update_decorations(enode, force=True)
                    except RuntimeError:
                        # A timer can update after the tree closes.
                        return
            else:
                try:
                    self.update_decorations(node, force=True)
                except RuntimeError:
                    # A timer can update after the tree closes.
                    return

        branch_elems_item = self.elements.get(type="branch elems")._item
        if branch_elems_item:
            self.wxtree.Expand(branch_elems_item)
        branch_reg_item = self.elements.get(type="branch reg")._item
        if branch_reg_item:
            self.wxtree.Expand(branch_reg_item)
        self.context.elements.signal("warn_state_update")
        self.freeze_tree(False)
        self.context.elements.set_end_time("full_load", display=True, delete=True)
        self.context.elements.set_end_time("refresh_tree", display=True)

    def update_warn_sign(self):
        # from time import perf_counter
        # this_call =  perf_counter()
        # print (f"Update warn was called, time since last: {this_call-self.last_call:.3f}sec")
        # self.last_call = this_call
        op_node = self.elements.get(type="branch ops")
        if op_node is None:
            return
        op_item = op_node._item

        status = ""
        if op_item is None:
            return

        self.wxtree.Expand(op_item)
        unassigned, unburnt = self.elements.have_unburnable_elements()
        needs_showing = False
        warn_level = self.context.setting(int, "concern_level", 1)
        messages = []
        if unassigned and warn_level <= 2:
            needs_showing = True
            messages.append( _("You have unassigned elements, that won't be burned") )
        if unburnt and warn_level <= 1:
            needs_showing = True
            messages.append( _("You have elements in disabled operations, that won't be burned") )

        if needs_showing:
            self.wxtree.SetItemState(op_item, self.iconstates["warning"])
            status = "\n".join(messages)
        else:
            self.wxtree.SetItemState(op_item, wx.TREE_ITEMSTATE_NONE)
            status = ""
        op_node._tooltip = status
        op_node._tooltip_translated = True

    def freeze_tree(self, status=None):
        if status is None:
            status = not self._freeze
        if self._freeze != status:
            self._freeze = status
            self.wxtree.Enable(not self._freeze)
            if status:
                self.wxtree.Freeze()
            else:
                self.wxtree.Thaw()
                self.wxtree.Refresh()

    def frozen(self, status):
        self.wxtree.Enable(not status)
        if status:
            self.wxtree.Freeze()
        else:
            self.wxtree.Thaw()
            self.wxtree.Refresh()

    def was_expanded(self, node, level):
        txt = self.wxtree.GetItemText(node)
        chk = f"{level}-{txt}"
        return any(chk == elem for elem in self.was_already_expanded)

    def set_expanded(self, node, level):
        txt = self.wxtree.GetItemText(node)
        chk = f"{level}-{txt}"
        result = self.was_expanded(node, level)
        if not result:
            self.was_already_expanded.append(chk)

    # These routines were supposed to save and restore the expanded state of the tree
    # But that did not work out as intended....
    #
    # def parse_tree(self, startnode, level):
    #     if startnode is None:
    #         return
    #     cookie = 0
    #     try:
    #         pnode, cookie = self.wxtree.GetFirstChild(startnode)
    #     except:
    #         return
    #     while pnode.IsOk():
    #         txt = self.wxtree.GetItemText(pnode)
    #         # That is not working as advertised...
    #         state = self.wxtree.IsExpanded(pnode)
    #         if state:
    #             self.was_already_expanded.append(f"{level}-{txt}")
    #         self.parse_tree(pnode, level + 1)
    #         pnode, cookie = self.wxtree.GetNextChild(startnode, cookie)

    # def restore_tree(self, startnode, level):
    #     if startnode is None:
    #         return
    #     cookie = 0
    #     try:
    #         pnode, cookie = self.wxtree.GetFirstChild(startnode)
    #     except:
    #         return
    #     while pnode.IsOk():
    #         txt = self.wxtree.GetItemText(pnode)
    #         chk = f"{level}-{txt}"
    #         for elem in self.was_already_expanded:
    #             if chk == elem:
    #                 self.wxtree.ExpandAllChildren(pnode)
    #                 break
    #         self.parse_tree(pnode, level + 1)
    #         pnode, cookie = self.wxtree.GetNextChild(startnode, cookie)
    #
    # def reset_expanded(self):
    #     self.was_already_expanded = []

    def reset_dragging(self):
        self.dragging_nodes = None
        self.wxtree.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

    def rebuild_tree(self, source:str, target:str="all" ):
        """
        Tree requires being deleted and completely rebuilt.

        @return:
        """
        # print (f"Rebuild called from {source}")
        # let's try to remember which branches were expanded:
        busy = wx.BusyCursor()
        self.context.elements.set_start_time(f"rebuild_tree_{target}")
        self.freeze_tree(True)

        # self.reset_expanded()

        # Safety net - if we have too many elements it will
        # take too long to create all preview icons...
        count = self.elements.count_elems() + self.elements.count_op()
        self._too_big = count > 1000
        # print(f"Was too big?! {count} -> {self._too_big}")

        # self.parse_tree(self.wxtree.GetRootItem(), 0)
        # Rebuild tree destroys the emphasis, so let's store it...
        def delete_items(target):
            if target == "regmarks":
                node = self.elements.reg_branch
                item = node._item
                if item is not None:
                    self.wxtree.DeleteChildren(item)
            elif target == "operations":
                node = self.elements.op_branch
                item = node._item
                if item is not None:
                    self.wxtree.DeleteChildren(item)
            elif target == "elements":
                node = self.elements.elem_branch
                item = node._item
                if item is not None:
                    self.wxtree.DeleteChildren(item)
            else:
                self.wxtree.DeleteAllItems()
        
        def rebuild_items(target):
            if target == "all":
                if self.tree_images is not None:
                    self.tree_images.Destroy()
                    self.image_cache = []
                self.tree_images = wx.ImageList()
                self.tree_images.Create(width=self.iconsize, height=self.iconsize)

                self.wxtree.SetImageList(self.tree_images)
            if target == "regmarks":
                elemtree = self.elements.reg_branch
            elif target == "operations":
                elemtree = self.elements.op_branch
            elif target == "elements":
                elemtree = self.elements.elem_branch
            else:
                elemtree = self.elements._tree
                elemtree._item = self.wxtree.AddRoot(self.name)
                self.wxtree.SetItemData(elemtree._item, elemtree)
                self.set_icon(
                    elemtree,
                    icon_meerk40t.GetBitmap(
                        False,
                        resize=(self.iconsize, self.iconsize),
                        noadjustment=True,
                        buffer=1,
                    ),
                )
            self.register_children(elemtree)
            branch_list = (
                ("branch ops", "operations", icons8_laser_beam),
                ("branch reg", "regmarks", icon_regmarks),
                ("branch elems", "elements", icon_canvas),
            )
            for branch_name, branch_type, icon in branch_list:
                if target not in ("all", branch_type):
                    continue
                node_branch = elemtree.get(type=branch_name)
                self.set_icon(
                    node_branch,
                    icon.GetBitmap(
                        resize=(self.iconsize, self.iconsize),
                        noadjustment=True,
                        buffer=1,
                    ),
                )
                for n in node_branch.children:
                    self.set_icon(n, force=True)
            if target in {"all", "operations"}:
                self.update_op_labels()
            if target in {"all", "elements"}:
                self.update_group_labels("rebuild_tree")

        emphasized_list = list(self.elements.elems(emphasized=True))

        delete_items(target)
        rebuild_items(target)

        # Expand Ops, Element, and Regmarks nodes only
        # self.wxtree.CollapseAll()
        self.wxtree.Expand(self.elements.op_branch._item)
        self.wxtree.Expand(self.elements.elem_branch._item)
        self.wxtree.Expand(self.elements.reg_branch._item)
        startnode = self.elements._tree._item
        
        def expand_leaf(snode):
            child, cookie = self.wxtree.GetFirstChild(snode)
            while child.IsOk():
                node = self.wxtree.GetItemData(child)  
                if node.expanded:
                    self.wxtree.Expand(child)
                expand_leaf(child)
                child, cookie = self.wxtree.GetNextChild(snode, cookie)
        
        expand_leaf(startnode)
        self.elements.signal("warn_state_update")

        # Restore emphasis
        for e in emphasized_list:
            e.emphasized = True
        # self.restore_tree(self.wxtree.GetRootItem(), 0)
        self.freeze_tree(False)
        self.context.elements.set_end_time(f"rebuild_tree_{target}", display=True)
        # print(f"Rebuild done for {source}")
        del busy

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

        item = node._item
        if item is None:
            print(f"Item was None for node {repr(node)}")
            return

        self.do_not_select = True
        self.check_validity(item)
        # We might need to update the decorations for all parent objects
        informed = []
        if not self._freeze:
            parent = node._parent
            while parent is not None and not parent.type.startswith("branch "):
                informed.append(parent)
                parent = parent._parent

        node.unregister_object()
        self.wxtree.Delete(node._item)
        if informed:
            self.context.signal("element_property_update", informed)
        for i in self.wxtree.GetSelections():
            self.wxtree.SelectItem(i, False)

        self.do_not_select = False

    def safe_color(self, color_to_set):
        _hash = str(color_to_set)
        if _hash not in self.color_cache:
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
            self.color_cache[_hash] = mycolor
        else:
            mycolor = self.color_cache[_hash]
        return mycolor

    def node_register(self, node, pos=None, **kwargs):
        """
        Node.item is added/inserted. Label is updated and values are set. Icon is set.

        @param node:
        @param pos:
        @param kwargs:
        @return:
        """
        try:
            parent = node.parent
            parent_item = parent._item
            if parent_item is None:
                # We are appending items in tree before registration.
                return
            tree = self.wxtree
            if pos is None:
                node._item = tree.AppendItem(parent_item, self.name)
            else:
                node._item = tree.InsertItem(parent_item, pos, self.name)
            tree.SetItemData(node._item, node)
        except Exception as e:
            # Invalid tree?
            self.context.signal("rebuild_tree", "all")
            print (f"We encountered an error at node registration: {e}")
            return
        self.update_decorations(node, False)
        wxcolor = self.wxtree.GetForegroundColour()
        attribute_to_try = "fill" if node.type == "elem text" else "stroke"
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
        if self.context.root.tree_colored:
            try:
                tree.SetItemTextColour(node._item, wxcolor)
            except (AttributeError, KeyError, TypeError):
                pass
        # We might need to update the decorations for all parent objects
        if not self._freeze:
            informed = []
            parent = node._parent
            while parent is not None and not parent.type.startswith("branch "):
                informed.append(parent)
                parent = parent._parent
            if informed:
                self.context.signal("element_property_update", informed)

        # self.context.signal("update_group_labels")

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
        if not self.context.root.tree_colored:
            return
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
                try:
                    image = self.renderer.make_thumbnail(
                        node.active_image, width=self.iconsize, height=self.iconsize
                    )
                except (MemoryError, RuntimeError):
                    image = None
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
            elif node.type.startswith("elem ") or node.type.startswith("effect "):
                if (
                    hasattr(node, "stroke")
                    and node.stroke is not None
                    and node.stroke.argb is not None
                ):
                    c = node.stroke

        # Have we already established an image, if no let's use the default
        if image is None:
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
                # print (f"Wasn't found use {tofind}")
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
                        buffer=1,
                    )
                    cached_id = self.tree_images.Add(bitmap=image)
                    # print(f"Store id {cached_id} for {c} - {found}")
                    self.image_cache.append((found, c, image, cached_id))

        if c is None:
            c = defaultcolor
        # print (f"Icon gives color: {c} and cached-id={cached_id}")
        return c, image, cached_id

    def set_icon(self, node, icon=None, force=False):
        """
        Node icon to be created and applied

        @param node: Node to have the icon set.
        @param icon: overriding icon to be forcibly set, rather than a default.
        @param force: force the icon setting
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
                for subnode in node.references:
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
        if startnode is None:
            # Branch op never populated the tree, we cannot update sublayer.
            return
        child, cookie = self.wxtree.GetFirstChild(startnode)
        while child.IsOk():
            node = self.wxtree.GetItemData(child)  # Make sure the map is updated...
            self.update_decorations(node=node, force=True)
            child, cookie = self.wxtree.GetNextChild(startnode, cookie)

    def update_group_labels(self, src):
        # print(f"group_labels: {src}")
        stop_updates = not self._freeze
        if stop_updates:
            self.freeze_tree(True)
        for e in self.context.elements.elems_nodes():
            if e.type == "group":
                self.update_decorations(e)
        for e in self.context.elements.regmarks_nodes():
            if e.type == "group":
                self.update_decorations(e)
        if stop_updates:
            self.freeze_tree(False)

    def reset_formatter_cache(self):
        self.formatter_cache.clear()

    def update_decorations(self, node, force=False):
        """
        Updates the decorations for a particular node/tree item

        @param node:
        @param force: force updating decorations
        @return:
        """

        def my_create_label(node, text=None):
            if text is None:
                try:
                    text = node._formatter
                except AttributeError:
                    text = "{element_type}:{id}"
            # Just for the optical impression (who understands what a "Rect: None" means),
            # let's replace some of the more obvious ones...
            mymap = node.default_map()
            # We change power to either ppi or percent
            if "power" in mymap and "ppi" in mymap and "percent" in mymap:
                self.context.device.setting(
                    bool, "use_percent_for_power_display", False
                )
                if self.context.device.use_percent_for_power_display:
                    mymap["power"] = mymap["percent"]
            if "speed" in mymap and "speed_mm_min" in mymap:
                self.context.device.setting(bool, "use_mm_min_for_speed_display", False)
                if self.context.device.use_mm_min_for_speed_display:
                    text = text.replace("mm/s", "mm/min")
                    mymap["speed"] = mymap["speed_mm_min"]
                    mymap["speed_unit"] = "mm/min"
                else:
                    mymap["speed_unit"] = "mm/s"
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
            except (ValueError, KeyError):
                res = text
            return res

        def get_formatter(nodetype):
            if nodetype not in self.formatter_cache:
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
                self.formatter_cache[nodetype] = default
            return self.formatter_cache[nodetype]

        if force is None:
            force = False
        if node._item is None:
            # This node is not registered the tree has desynced.
            self.rebuild_tree(source="desync", target="all")
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
            label = f"*{my_create_label(node.node, formatter)}"
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
        attribute_to_try = "fill" if node.type == "elem text" else "stroke"
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
        if self.context.root.tree_colored:
            try:
                self.wxtree.SetItemTextColour(node._item, wxcolor)
            except (AttributeError, KeyError, TypeError):
                pass

        state_num = -1
        if node is self.elements.get(type="branch ops"):
            unassigned, unburnt = self.elements.have_unburnable_elements()
            if unassigned or unburnt:
                state_num = self.iconstates["warning"]
        else:
            # Has the node a lock attribute?
            lockit = node.lock if hasattr(node, "lock") else False
            if lockit:
                state_num = self.iconstates["lock"]
            scene = getattr(self.context.root, "mainscene", None)
            if scene is not None and node == scene.pane.reference_object:
                    state_num = self.iconstates["refobject"]
        if state_num < 0:
            state_num = wx.TREE_ITEMSTATE_NONE
            if (
                node.type in op_nodes
                and hasattr(node, "is_visible")
                and not node.is_visible
            ) or (
                node.type in elem_nodes and hasattr(node, "hidden") and node.hidden
            ) or (
                hasattr(node, "node") and hasattr(node.node, "hidden") and node.node.hidden
            ):
                state_num = self.iconstates["ghost"]
        self.wxtree.SetItemState(node._item, state_num)

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
            elif typename.startswith("group"):
                result = "elem"
            elif typename.startswith("file"):
                result = "elem"
            else:
                result = typename
            return result

        self.dragging_nodes = None

        pt = event.GetPoint()
        drag_item, _ = self.wxtree.HitTest(pt)

        if drag_item is None or drag_item.ID is None or not drag_item.IsOk():
            # errmsg = ""
            # if drag_item is None:
            #     errmsg = "item was none"
            # elif drag_item.ID is None:
            #     errmsg = "id was none"
            # elif not drag_item.IsOk():
            #     errmsg = "IsOk was false"
            # print (f"Drag item was wrong: {errmsg}")
            event.Skip()
            return

        self.dragging_nodes = []
        for item in self.wxtree.GetSelections():
            node = self.wxtree.GetItemData(item)
            if node is not None and node.is_draggable():
                self.dragging_nodes.append(node)

        if not self.dragging_nodes:
            # print ("Dragging_nodes was empty")
            event.Skip()
            return

        t = typefamily(self.dragging_nodes[0].type)
        for n in self.dragging_nodes:
            tt = typefamily(n.type)
            if t != tt:
                # Different typefamilies
                # print ("Different typefamilies")
                event.Skip()
                return
            if not n.is_draggable():
                # print ("Element was not draggable")
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
        self.wxtree.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        drop_item = event.GetItem()
        if drop_item is None or drop_item.ID is None:
            event.Skip()
            return
        drop_node = self.wxtree.GetItemData(drop_item)
        if drop_node is None:
            event.Skip()
            return
        # Is the node expanded? If yes regular dnd applies, if not we will add the node to the end...
        closed_leaf = (self.wxtree.ItemHasChildren(drop_item) and not self.wxtree.IsExpanded(drop_item))
        # We extend the logic by calling the appropriate elems routine
        skip = not self.elements.drag_and_drop(self.dragging_nodes, drop_node, flag=closed_leaf)
        if skip:
            event.Skip()
            self.dragging_nodes = None
            return
        event.Allow()
        # Make sure that the drop node is visible
        self.wxtree.Expand(drop_item)
        self.wxtree.EnsureVisible(drop_item)
        self.refresh_tree(source="drag end")
        # Do the dragging_nodes contain an operation?
        # Let's give an indication of that, as this may
        # have led to the creation of a new reference
        # node. For whatever reason this is not recognised
        # otherwise...
        if not self.dragging_nodes:
            # Dragging nodes were cleared (we must have rebuilt the entire tree)
            return
        for node in self.dragging_nodes:
            if node.type.startswith("op"):
                self.context.signal("tree_changed")
                break
        # self.rebuild_tree()
        self.reset_dragging()

    def on_mouse_over(self, event):
        # establish the item we are over...
        event.Skip()
        ttip = ""
        pt = event.GetPosition()
        item, flags = self.wxtree.HitTest(pt)
        if self._last_hover_item is item:
            return
        if item:
            state = self.wxtree.GetItemState(item)
            node = self.wxtree.GetItemData(item)
            if node is not None:
                # Lets check the dragging status
                if self.dragging_nodes:
                    if hasattr(node, "would_accept_drop"):
                        would_drop = node.would_accept_drop(self.dragging_nodes)
                    else:
                        would_drop = False
                    if would_drop:
                        self.wxtree.SetCursor(wx.Cursor(wx.CURSOR_HAND))
                    else:
                        self.wxtree.SetCursor(wx.Cursor(wx.CURSOR_NO_ENTRY))
                else:
                    self.wxtree.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

                if hasattr(node, "_tooltip"):
                    # That has precedence and will be displayed in all cases
                    ttip = node._tooltip
                elif not self.context.disable_tree_tool_tips:
                    if node.type == "blob":
                        ttip = _(
                            "This is binary data imported or generated\n"
                            + "that will be sent directly to the laser.\n"
                            + "Double-click to view."
                        )
                    elif node.type == "op cut":
                        ttip = _(
                            "This will engrave/cut the elements contained,\n"
                            + "following the vector-paths of the data.\n"
                            + "(Usually done last)"
                        )
                    elif node.type == "op engrave":
                        ttip = _(
                            "This will engrave the elements contained,\n"
                            + "following the vector-paths of the data."
                        )
                    elif node.type == "op image":
                        ttip = _(
                            "This engraves already created images pixel by pixel,\n"
                            + "applying the settings to the individual pictures"
                        )
                    elif node.type == "op raster":
                        ttip = _(
                            "This will render all contained elements\n"
                            + "into an intermediary image which then will be\n"
                            + "engraved pixel by pixel."
                        )
                    elif node.type == "op dots":
                        ttip = _(
                            "This will engrave a single point for a given period of time"
                        )
                    elif node.type == "util console":
                        ttip = _(
                            "This allows to execute an arbitrary command during the engrave process"
                        )
                    elif node.type == "util goto":
                        ttip = _(
                            "This will send the laser back to its logical start position"
                        )
                    elif node.type == "util home":
                        ttip = _(
                            "This will send the laser back to its physical start position"
                        )
                    elif node.type == "util input":
                        ttip = _(
                            "This will wait for active IO bits on the laser (mainly fibre laser for now)"
                        )
                    elif node.type == "util output":
                        ttip = _(
                            "This will set some IO bits on the laser (mainly fibre laser for now)"
                        )
                    elif node.type == "util wait":
                        ttip = _(
                            "This will pause the engrave process for a given period"
                        )
                    elif node.type == "branch reg":
                        ttip = _(
                            "The elements under this section will not be engraved,\n"
                            + "they can serve as a template or registration marks."
                        )
                    elif node.type == "elem line":
                        bb = node.bounds
                        if bb is not None:
                            ww = Length(amount=bb[2] - bb[0], digits=1)
                            hh = Length(amount=bb[3] - bb[1], digits=1)
                            ll = Length(amount=node.length(), digits=1)
                            ttip = f"{ww.length_mm} x {hh.length_mm}, L={ll.length_mm}"
                    elif node.type == "elem rect":
                        bb = node.bounds
                        if bb is not None:
                            ww = Length(amount=bb[2] - bb[0], digits=1)
                            hh = Length(amount=bb[3] - bb[1], digits=1)
                            ll = Length(amount=node.length(), digits=1)
                            ttip = f"{ww.length_mm} x {hh.length_mm}, L={ll.length_mm}"
                    elif node.type == "elem polyline":
                        bb = node.bounds
                        if bb is not None:
                            ww = Length(amount=bb[2] - bb[0], digits=1)
                            hh = Length(amount=bb[3] - bb[1], digits=1)
                            ll = Length(amount=node.length(), digits=1)
                            ttip = f"{ww.length_mm} x {hh.length_mm}, L={ll.length_mm}"
                            ttip += f"\n{len(node)} pts"
                    elif node.type == "elem ellipse":
                        bb = node.bounds
                        if bb is not None:
                            ww = Length(amount=bb[2] - bb[0], digits=1)
                            hh = Length(amount=bb[3] - bb[1], digits=1)
                            ttip = f"{ww.length_mm} x {hh.length_mm}"
                    elif node.type == "elem path":
                        bb = node.bounds
                        if bb is not None:
                            ww = Length(amount=bb[2] - bb[0], digits=1)
                            hh = Length(amount=bb[3] - bb[1], digits=1)
                            ttip = f"{ww.length_mm} x {hh.length_mm}"
                            ttip += f"\n{len(node.path)} segments"
                    elif node.type == "elem text":
                        bb = node.bounds
                        if bb is not None:
                            ww = Length(amount=bb[2] - bb[0], digits=1)
                            hh = Length(amount=bb[3] - bb[1], digits=1)
                            ttip = f"{ww.length_mm} x {hh.length_mm}"
                            # ttip += f"\n{node.font}"
                    elif node.type == "place current":
                        ttip = _(
                            "This is a placeholder for the 'place current' operation"
                        )
                    elif node.type == "place point":
                        ttip = _(
                            "This will define an origin from where all the elements in this scene\n"
                            + "will be plotted. You can have multiple such job start points"
                        )
                    elif node.type == "effect hatch":
                        ttip = _(
                            "This is a special node that will consume any other closed path\n"
                            + "you drag onto it and will fill the shape with a line pattern.\n"
                            + "To activate / deactivate this effect please use the context menu."
                        )
                    if node.type in op_nodes:
                        if hasattr(node, "label") and node.label is not None:
                            ttip += f"\n{node.id + ': ' if node.id is not None else ''}{node.display_label()}"
                        ps_info = ""
                        if hasattr(node, "power") and node.power is not None:
                            try:
                                p = float(node.power)
                                if self.context.device.use_percent_for_power_display:
                                    ps_info += f"{', ' if ps_info else ''}{p / 10:.1f}%"
                                else:
                                    ps_info += f"{', ' if ps_info else ''}{p:.0f}ppi"
                            except ValueError:
                                pass

                        if hasattr(node, "speed") and node.speed is not None:
                            try:
                                p = float(node.speed)
                                if self.context.device.use_mm_min_for_speed_display:
                                    ps_info += (
                                        f"{', ' if ps_info else ''}{p * 60.0:.0f}mm/min"
                                    )
                                else:
                                    ps_info += f"{', ' if ps_info else ''}{p:.0f}mm/s"
                            except ValueError:
                                pass

                        if (
                            hasattr(self.context.device, "default_frequency")
                            and hasattr(node, "frequency")
                            and node.frequency is not None
                        ):
                            try:
                                p = float(node.frequency)
                                ps_info += f"{', ' if ps_info else ''}{p:.0f}kHz"
                            except ValueError:
                                pass

                        if ps_info:
                            ttip += f"\n{ps_info}"
            if state == self.iconstates["ghost"]:
                ttip = _("HIDDEN: ") + ttip
        self._last_hover_item = item
        if ttip != self.wxtree.GetToolTipText():
            self.wxtree.SetToolTip(ttip)

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
        if first_element is None:
            first_element = self.elements.first_element(selected=True)
        if first_element is None:
            return
        if hasattr(first_element, "node"):
            # Reference
            first_element = first_element.node
        activate = self.elements.lookup("function/open_property_window_for_node")
        if activate is not None:
            activate(first_element)

    def on_collapse(self, event):
        if self.do_not_select:
            # Do not select is part of a linux correction where moving nodes around in a drag and drop fashion could
            # cause them to appear to drop invalid nodes.
            return
        item = event.GetItem()
        if not item:
            return
        node = self.wxtree.GetItemData(item)
        node.expanded = False

    def on_expand(self, event):
        if self.do_not_select:
            # Do not select is part of a linux correction where moving nodes around in a drag and drop fashion could
            # cause them to appear to drop invalid nodes.
            return
        item = event.GetItem()
        if not item:
            return
        node = self.wxtree.GetItemData(item)
        node.expanded = True

    def on_state_icon(self, event):
        if self.do_not_select:
            # Do not select is part of a linux correction where moving nodes around in a drag and drop fashion could
            # cause them to appear to drop invalid nodes.
            return
        item = event.GetItem()
        if not item:
            return
        node = self.wxtree.GetItemData(item)
        if hasattr(node, "hidden"):
            node.hidden = False
            self.context.elements.set_emphasis([node])
            # self.context.signal("refresh_scene", "Scene")
            self.update_decorations(node)

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
        # print (f"tree claims: {self.wxtree.FindFocus().GetId()},  parent claims: {self.wxtree.GetParent().FindFocus().GetId()}, toplevel claims: {self.wxtree.GetTopLevelParent().FindFocus().GetId()}, tree-id={self.wxtree.GetId()}")
        its_me = self.wxtree.FindFocus() is self.wxtree
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
            if node is None or node.type is None:
                # Rare issue seen building the tree during materials test and the node type didn't exist.
                return
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

        # We seem to lose focus, so lets reclaim it
        if its_me:
            def restore_focus():
                self.wxtree.SetFocus()
            wx.CallAfter(restore_focus)

    def select_in_tree_by_emphasis(self, origin, *args):
        """
        Selected the actual `wx.tree` control those items which are currently emphasized.

        @return:
        """
        self.do_not_select = True
        self.wxtree.UnselectAll()
        require_rebuild = False
        for e in self.elements.elems_nodes(emphasized=True):
            if e._item:
                self.wxtree.SelectItem(e._item, True)
            else:
                # That should not happen, apparently we have a not fully built tree
                require_rebuild = True
                break
        if require_rebuild:
            self.context.signal("rebuild_tree", "all")

        self.do_not_select = False
