import wx

from meerk40t.gui.functionwrapper import ConsoleCommandUI
from meerk40t.gui.icons import STD_ICON_SIZE, icon_copies
from meerk40t.gui.mwindow import MWindow
from meerk40t.kernel.kernel import signal_listener

_ = wx.GetTranslation


class GridUI(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(
            350,
            350,
            *args,
            style=wx.CAPTION
            | wx.CLOSE_BOX
            | wx.FRAME_FLOAT_ON_PARENT
            | wx.TAB_TRAVERSAL
            | wx.RESIZE_BORDER,
            **kwds,
        )
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.panels = []
        self.window_context.themes.set_window_colors(self.notebook_main)
        bg_std = self.window_context.themes.get("win_bg")
        bg_active = self.window_context.themes.get("highlight")
        self.notebook_main.GetArtProvider().SetColour(bg_std)
        self.notebook_main.GetArtProvider().SetActiveColour(bg_active)

        self.sizer.Add(self.notebook_main, 1, wx.EXPAND, 0)
        self.scene = getattr(self.context.root, "mainscene", None)
        panel_grid = ConsoleCommandUI(self, wx.ID_ANY, context=self.context, command_string="grid", preview_routine=self.preview_grid)
        self.panels.append(panel_grid)
        self.notebook_main.AddPage(panel_grid, _("Grid"))
        panel_circular = ConsoleCommandUI(self, wx.ID_ANY, context=self.context, command_string="circ_copy", preview_routine=self.preview_circular)
        self.panels.append(panel_circular)
        self.notebook_main.AddPage(panel_circular, _("Circular grid"))
        panel_radial = ConsoleCommandUI(self, wx.ID_ANY, context=self.context, command_string="radial", preview_routine=self.preview_radial)
        self.panels.append(panel_radial)
        self.notebook_main.AddPage(panel_radial, _("Radial"))

        self.Layout()
        self.restore_aspect()

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_copies.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Copy selection"))

    def delegates(self):
        yield from self.panels

    def preview_grid(self, variables):
        return None

    def preview_circular(self, variables):
        return None

    def preview_radial(self, variables):
        return None

    @staticmethod
    def sub_register(kernel):
        bsize_normal = STD_ICON_SIZE
        # bsize_small = int(STD_ICON_SIZE / 2)

        kernel.register(
            "button/basicediting/Duplicate",
            {
                "label": _("Duplicate"),
                "icon": icon_copies,
                "tip": _("Create copies of the current selection"),
                "help": "duplicate",
                "action": lambda v: kernel.console("window toggle GridUI\n"),
                "size": bsize_normal,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )

    def window_open(self):
        self.on_update("internal")

    def window_close(self):
        pass
    
    def done(self):
        self.Close()

    @signal_listener("emphasized")
    def on_update(self, origin, *args):
        value = self.context.elements.has_emphasis()
        for panel in self.panels:
            if hasattr(panel, "show_stuff"):
                panel.show_stuff(value)

    @staticmethod
    def submenu():
        return "Editing", "Duplicate"

    @staticmethod
    def helptext():
        return _("Duplicate elements in multiple fashions")
