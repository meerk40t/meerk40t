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

        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.page_panel = None
        self.Layout()

    @signal_listener("selected")
    def on_selected(self, origin, *args):
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
            for property_sheet in self.context.lookup_all(
                f"property/{node.__class__.__name__}/.*"
            ):
                if not hasattr(property_sheet, "accepts") or property_sheet.accepts(
                    node
                ):
                    pages_in_node.append((property_sheet, node))
            pages_in_node.sort(key=sort_priority)
            pages_to_instance.extend(pages_in_node)

        self.window_close()
        # self.panel_instances.clear()
        self.notebook_main.DeleteAllPages()
        self.page_panel = None
        for prop_sheet, instance in pages_to_instance:
            self.page_panel = prop_sheet(
                self.notebook_main, wx.ID_ANY, context=self.context, node=instance
            )
            try:
                name = prop_sheet.name
            except AttributeError:
                name = instance.__class__.__name__

            self.notebook_main.AddPage(self.page_panel, name)
            try:
                self.page_panel.set_widgets(instance)
            except AttributeError:
                pass
            self.panel_instances.append(self.page_panel)
            try:
                self.page_panel.pane_show()
            except AttributeError:
                pass
            self.page_panel.Layout()
            try:
                self.page_panel.SetupScrolling()
            except AttributeError:
                pass

        self.Layout()

    def delegate(self):
        yield self.page_panel

    @staticmethod
    def sub_register(kernel):
        # kernel.register("wxpane/Properties", register_panel_property)
        kernel.register(
            "button/control/Properties",
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
            self.remove_module_delegate(p)
        self.panel_instances.clear()
