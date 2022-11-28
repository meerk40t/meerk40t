import wx
from wx import aui

from ...kernel import signal_listener
from ..icons import icons8_computer_support_50
from ..mwindow import MWindow

_ = wx.GetTranslation


class PropertyWindow(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(598, 429, *args, **kwds)

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_computer_support_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Navigation.__set_properties
        self.SetTitle(_("Properties"))
        self.panel_instances = list()

        self.notebook_main = aui.AuiNotebook(
            self,
            -1,
            style=aui.AUI_NB_TAB_EXTERNAL_MOVE
            | aui.AUI_NB_SCROLL_BUTTONS
            | aui.AUI_NB_TAB_SPLIT
            | aui.AUI_NB_TAB_MOVE,
        )
        self.notebook_main.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_page_changed)
        self.Layout()

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

    @signal_listener("selected")
    def on_selected(self, origin, *args):
        self.Freeze()
        for p in self.panel_instances:
            try:
                p.pane_hide()
            except AttributeError:
                pass
            self.remove_module_delegate(p)

        def sort_priority(prop):
            prop_sheet, node = prop
            return (
                getattr(prop_sheet, "priority")
                if hasattr(prop_sheet, "priority")
                else 0
            )

        nodes = list(self.context.elements.flat(selected=True, cascade=False))
        if nodes is None:
            return
        pages_to_instance = []
        for node in nodes:
            pages_in_node = []
            found = False
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

        self.window_close()
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
            try:
                page_panel.set_widgets(instance)
            except AttributeError:
                pass
            self.add_module_delegate(page_panel)
            self.panel_instances.append(page_panel)
            try:
                page_panel.pane_show()
            except AttributeError:
                pass
            page_panel.Layout()
            try:
                page_panel.SetupScrolling()
            except AttributeError:
                pass

        self.Layout()
        self.Thaw()
        # self.Refresh()

    @staticmethod
    def sub_register(kernel):
        # kernel.register("wxpane/Properties", register_panel_property)
        kernel.register(
            "button/preparation/Properties",
            {
                "label": _("Property Window"),
                "icon": icons8_computer_support_50,
                "tip": _("Opens Properties Window"),
                "action": lambda v: kernel.console("window toggle Properties\n"),
                "priority": 2,
            },
        )
        kernel.register(
            "button/properties/Properties",
            {
                "label": _("Property Window"),
                "icon": icons8_computer_support_50,
                "tip": _("Opens Properties Window"),
                "action": lambda v: kernel.console("window toggle Properties\n"),
            },
        )

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
        return ("Editing", "Operation/Element Properties")
