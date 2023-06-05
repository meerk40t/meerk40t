import wx
from wx import aui

from .icons import icons8_computer_support_50
from .mwindow import MWindow

_ = wx.GetTranslation


class SimpleUI(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(598, 429, *args, **kwds)

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_computer_support_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Navigation.__set_properties
        self.SetTitle(_("MeerK40t"))
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
        self.on_build()

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

    def on_build(self, *args):
        self.Freeze()

        def sort_priority(prop):
            return (
                getattr(prop, "priority")
                if hasattr(prop, "priority")
                else 0
            )
        pages_to_instance = list()
        for property_sheet in self.context.lookup_all(
            f"simpleui/.*"
        ):
            pages_to_instance.append(property_sheet)

        pages_to_instance.sort(key=sort_priority)

        for page in pages_to_instance:
            page_panel = page(
                self.notebook_main, wx.ID_ANY, context=self.context
            )
            try:
                name = page.name
            except AttributeError:
                name = page_panel.__class__.__name__

            self.notebook_main.AddPage(page_panel, _(name))
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

    @staticmethod
    def sub_register(kernel):
        from meerk40t.gui.laserpanel import LaserPanel
        kernel.register("simpleui/laserpanel", LaserPanel)
        from meerk40t.gui.navigationpanels import Jog
        kernel.register("simpleui/navigation", Jog)
        from meerk40t.gui.consolepanel import ConsolePanel
        kernel.register("simpleui/console", ConsolePanel)

    def window_close(self):
        context = self.context
        for p in self.panel_instances:
            try:
                p.pane_hide()
            except AttributeError:
                pass
        # We do not remove the delegates, they will detach with the closing of the module.
        self.panel_instances.clear()

        context.channel("shutdown").watch(print)
        self.context(".timer 0 1 quit\n")

    def window_menu(self):
        return False

    @staticmethod
    def submenu():
        return "Interface", "SimpleUI"
