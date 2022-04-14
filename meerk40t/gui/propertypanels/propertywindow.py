import wx
from wx import aui

from ..icons import icons8_computer_support_50
from ..mwindow import MWindow
from ...kernel import signal_listener

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
        self.Layout()

    @signal_listener("selected")
    def on_selected(self, origin, *args):
        for p in self.panel_instances:
            try:
                p.pane_hide()
            except AttributeError:
                pass
            self.remove_module_delegate(p)
        nodes = list(self.context.elements.flat(selected=True, cascade=False))
        if nodes is None:
            return
        pages_to_instance = []
        for node in nodes:
            for property_sheet in self.context.lookup_all(
                "property/{class_name}/.*".format(class_name=node.__class__.__name__)
            ):
                if not hasattr(property_sheet, "accepts") or property_sheet.accepts(
                    node
                ):
                    pages_to_instance.append((property_sheet, node))

        def sort_priority(prop):
            prop_sheet, node = prop
            return (
                getattr(prop_sheet, "priority")
                if hasattr(prop_sheet, "priority")
                else 0
            )

        pages_to_instance.sort(key=sort_priority)

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

            self.notebook_main.AddPage(page_panel, name)
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

        self.Layout()

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
