from time import perf_counter

import wx
from wx import aui

from ...kernel import signal_listener
from ..icons import icons8_computer_support
from ..mwindow import MWindow

_ = wx.GetTranslation


class PropertyWindow(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(600, 650, *args, **kwds)

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_computer_support.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Navigation.__set_properties
        self.SetTitle(_("Properties"))
        self.panel_instances = list()
        self.nodes_displayed = list()

        self.notebook_main = aui.AuiNotebook(
            self,
            -1,
            style=aui.AUI_NB_TAB_EXTERNAL_MOVE
            | aui.AUI_NB_SCROLL_BUTTONS
            | aui.AUI_NB_TAB_SPLIT
            | aui.AUI_NB_TAB_MOVE,
        )
        self.sizer.Add(self.notebook_main, 1, wx.EXPAND, 0)
        self.notebook_main.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_page_changed)
        self.Layout()
        self.restore_aspect(honor_initial_values=True)
        self.channel = self.context.channel("propertypanel", timestamp=True)

    def on_page_changed(self, event):
        event.Skip()
        page = self.notebook_main.GetCurrentPage()
        if page is None:
            return
        for panel in self.panel_instances:
            try:
                if panel is page:
                    page.pane_active()
                else:
                    panel.pane_deactive()
            except AttributeError:
                pass

    def unload_property_panes(self):
        if self.channel:
            self.channel("Unload property panes")
        for p in self.panel_instances:
            try:
                p.pane_hide()
            except AttributeError:
                pass
            self.remove_module_delegate(p)
        self.panel_instances.clear()

    def load_property_panes(self, pages_to_instance):
        nodes = self.nodes_displayed

        # This will clear the old list
        self.window_close()
        if self.channel:
            self.channel(
                f"Loading new property panes for {len(nodes)} nodes - pages found: {len(pages_to_instance)}"
            )
        # self.panel_instances.clear()
        self.notebook_main.DeleteAllPages()
        for prop_sheet, instance in pages_to_instance:
            page_panel = prop_sheet(
                self.notebook_main, wx.ID_ANY, context=self.context, node=instance
            )
            try:
                name = prop_sheet.name
            except AttributeError:
                name = instance.__class__.__name__

            self.notebook_main.AddPage(page_panel, _(name))
            if hasattr(page_panel, "set_widgets"):
                page_panel.set_widgets(instance)
            self.add_module_delegate(page_panel)
            self.panel_instances.append(page_panel)
            if hasattr(page_panel, "pane_show"):
                page_panel.pane_show()
            page_panel.Layout()
            if hasattr(page_panel, "SetupScrolling"):
                page_panel.SetupScrolling()
        # print(f"Panels created: {len(self.panel_instances)}")
        # self.Refresh()

    def validate_display(self, nodes, source):
        def sort_priority(prop):
            prop_sheet, node = prop
            return (
                getattr(prop_sheet, "priority")
                if hasattr(prop_sheet, "priority")
                else 0
            )

        # Are the new nodes identical to the displayed ones?
        different = False
        if nodes is None:
            nodes = list()
        else:
            nodes = list(nodes)
        to_be_deleted = []
        for idx, e in enumerate(nodes):
            # We remove reference nodes and insert the 'real' thing instead.
            if e.type == "reference":
                node = e.node
                if node not in nodes:
                    nodes.append(node)
                # Reverse order
                to_be_deleted.insert(0, idx)
        # print (f"Need to delete {len(to_be_deleted)} references")
        for idx in to_be_deleted:
            nodes.pop(idx)

        nlen = len(nodes)
        plen = len(self.nodes_displayed)

        if nlen != plen:
            different = True
        else:
            for e in nodes:
                if e not in self.nodes_displayed:
                    different = True
                    break
        pages_to_instance = []
        if different:
            for node in nodes:
                pages_in_node = []
                found = False
                # print(f"Looking for 'property/{node.__class__.__name__}/.*'")
                for property_sheet in self.context.lookup_all(
                    f"property/{node.__class__.__name__}/.*"
                ):
                    if not hasattr(property_sheet, "accepts") or property_sheet.accepts(
                        node
                    ):
                        pages_in_node.append((property_sheet, node))
                        found = True
                # If we did not have any hits and the node is a reference
                # then we fall back to the master. So if in the future we
                # would have a property panel dealing with reference-nodes
                # then this would no longer apply.
                if node.type == "reference" and not found:
                    snode = node.node
                    found = False
                    for property_sheet in self.context.lookup_all(
                        f"property/{snode.__class__.__name__}/.*"
                    ):
                        if not hasattr(property_sheet, "accepts") or property_sheet.accepts(
                            snode
                        ):
                            pages_in_node.append((property_sheet, snode))
                            found = True

                pages_in_node.sort(key=sort_priority)
                pages_to_instance.extend(pages_in_node)

        if self.channel:
            msg = f"Check done for {source}, displayed={len(self.nodes_displayed)}, nodes={len(nodes)}"
            if different and len(pages_to_instance) > 0:
                msg += " - different, so new panels will load"
            elif different:
                msg += " - different but nothing defined, so panels remain"
                if len(nodes) > 0:
                    msg += f"(first node was: {nodes[0].type})"
            else:
                msg += " - identical, so panels remain"
            self.channel(msg)
        if different and len(pages_to_instance) > 0:
            t1 = perf_counter()
            busy = wx.BusyCursor()
            self.Freeze()
            self.unload_property_panes()
            self.nodes_displayed.clear()
            if len(nodes) > 0:
                for e in nodes:
                    if e not in self.nodes_displayed:
                        self.nodes_displayed.append(e)
                # self.nodes_displayed.extend(nodes)
            self.load_property_panes(pages_to_instance)
            self.Layout()
            self.Thaw()
            del busy
            t2 = perf_counter()
            if self.channel:
                self.channel(f"Took {t2-t1:.2f} seconds to load")

    @signal_listener("refresh_scene")
    def on_refresh_scene(self, origin, *args):
        myargs = [i for i in args]
        if len(args) > 0 and args[0] == "Scene":
            for p in self.panel_instances:
                if hasattr(p, "signal"):
                    p.signal("refresh_scene", myargs)

    @signal_listener("modified_by_tool")
    def on_tool_modified(self, origin, *args):
        myargs = [i for i in args]
        for p in self.panel_instances:
            if hasattr(p, "signal"):
                p.signal("modified_by_tool", myargs)

    @signal_listener("nodetype")
    def on_nodetype(self, origin, *args):
        myargs = [i for i in args]
        for p in self.panel_instances:
            if hasattr(p, "signal"):
                p.signal("nodetype", myargs)

    @signal_listener("imageprop;nodither")
    def on_no_dither(self, origin, *args):
        myargs = [i for i in args]
        for p in self.panel_instances:
            if hasattr(p, "signal"):
                p.signal("imageprop;nodither", myargs)

    @signal_listener("imageprop;nodepth")
    def on_no_depth(self, origin, *args):
        myargs = [i for i in args]
        for p in self.panel_instances:
            if hasattr(p, "signal"):
                p.signal("imageprop;nodepth", myargs)

    @signal_listener("textselect")
    def on_textselect(self, origin, *args):
        myargs = [i for i in args]
        for p in self.panel_instances:
            if hasattr(p, "signal"):
                p.signal("textselect", myargs)

    @signal_listener("selected")
    def on_selected(self, origin, *args):
        nodes = list(self.context.elements.flat(selected=True, cascade=False))
        self.validate_display(nodes, "selected")

    @signal_listener("emphasized")
    def on_emphasized(self, origin, *args):
        nodes = list(self.context.elements.flat(emphasized=True, cascade=False))
        self.validate_display(nodes, "emphasized")

    @staticmethod
    def sub_register(kernel):
        # kernel.register("wxpane/Properties", register_panel_property)
        kernel.register(
            "button/preparation/Properties",
            {
                "label": _("Property Window"),
                "icon": icons8_computer_support,
                "tip": _("Opens Properties Window"),
                "action": lambda v: kernel.console("window toggle Properties\n"),
                "priority": 2,
            },
        )
        kernel.register(
            "button/properties/Properties",
            {
                "label": _("Property Window"),
                "icon": icons8_computer_support,
                "tip": _("Opens Properties Window"),
                "action": lambda v: kernel.console("window toggle Properties\n"),
            },
        )

    def window_open(self):
        nodes = list(self.context.elements.flat(selected=True, cascade=False))
        self.validate_display(nodes, "window_open")

    def window_close(self):
        for p in self.panel_instances:
            try:
                p.pane_hide()
            except AttributeError:
                pass
        # We do not remove the delegates, they will detach with the closing of the module.
        self.panel_instances.clear()

    @staticmethod
    def submenu():
        return "Editing", "Operation/Element Properties"
