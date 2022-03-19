import wx
from wx import aui

from ..icons import icons8_computer_support_50
from ..mwindow import MWindow
from ...kernel import lookup_listener

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

    @lookup_listener("active/instances")
    def on_lookup_change(self, instance_values, old_panels):
        for p in self.panel_instances:
            p.pane_hide()
            self.remove_module_delegate(p)
        self.panel_instances.clear()
        if instance_values is None:
            return
        properties = []
        for instance_value in instance_values:
            instances, _, _ = instance_value
            for instance in instances:
                for q in self.context.lookup_all("property/{class_name}/.*".format(class_name=instance.__class__.__name__)):
                    properties.append((q, instance))

        def sort_priority(prop):
            elem, inst = prop
            return getattr(elem, "priority") if hasattr(elem, "priority") else 0

        properties.sort(key=sort_priority)

        for panel, instance in properties:
            page_panel = panel(
                self.notebook_main, wx.ID_ANY, context=self.context, node=instance
            )
            self.notebook_main.AddPage(page_panel, panel.name)
            self.add_module_delegate(page_panel)
            self.panel_instances.append(page_panel)
        for p in self.panel_instances:
            p.pane_show()
            p.Layout()
        self.Layout()

    @staticmethod
    def sub_register(kernel):
        pass
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
