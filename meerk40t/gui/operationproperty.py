import wx
from .icons import icons8_laser_beam_52
from .mwindow import MWindow

_ = wx.GetTranslation


class OperationProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(350, 582, *args, **kwds)
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.panels = []
        panels = list(self.context.lookup_all("operationproperty"))

        def sort_priority(elem):
            return getattr(elem, "priority") if hasattr(elem, "priority") else 0

        panels.sort(key=sort_priority)

        for panel in panels:
            page_panel = panel(
                self.notebook_main, wx.ID_ANY, context=self.context, node=node
            )
            self.notebook_main.AddPage(page_panel, panel.name)
            page_panel.set_widgets(node)
            self.add_module_delegate(page_panel)
            self.panels.append(page_panel)

        # begin wxGlade: OperationProperty.__set_properties
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_laser_beam_52.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Operation Properties"))

        self.Layout()

    def restore(self, *args, node=None, **kwds):
        for p in self.panels:
            p.set_widgets(node)
            p.on_size()
        self.Refresh()
        self.Update()

    def window_open(self):
        for p in self.panels:
            p.pane_show()

    def window_close(self):
        for p in self.panels:
            p.pane_hide()

    def window_preserve(self):
        return False

    def window_menu(self):
        return False
