import wx
from PIL import Image, ImageDraw
from meerk40t.core.units import Length, Angle
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

    def preview_grid(self, variables, dimension=400):
        def PIL2wx (image):
            width, height = image.size
            return wx.Bitmap.FromBuffer(width, height, image.tobytes())

        example_dimension = Length("1cm")
        origin="0,0"
        col_count = 1
        row_count = 1
        xgap = Length("1cm")
        ygap = Length("1cm")
        mypos_c = 0
        mypos_r = 0
        relative = False
        for vari in variables:
            var_name = vari["name"]
            var_value = vari["value"]
            if var_value is None:
                continue
            try:
                if var_name == "columns":
                    col_count = var_value
                elif var_name == "rows":
                    row_count = var_value
                elif var_name == "x_distance":
                    xgap = Length(var_value)
                elif var_name == "y_distance":
                    ygap = Length(var_value)
                elif var_name == "relative":
                    relative = var_value
                elif var_name == "origin":
                    origin = var_value
            except ValueError:
                continue
        if isinstance(origin, str):
            or_arr = origin.split(",")
            if len(or_arr) > 1:
                try:
                    mypos_c = int(or_arr[0]) - 1
                    mypos_r = int(or_arr[1]) - 1
                except ValueError:
                    pass
        if mypos_c < 0 or mypos_c >= col_count:
            mypos_c = 0
        if mypos_r < 0 or mypos_r >= row_count:
            mypos_r = 0
        xd = example_dimension.cm
        yd = xd
        dx = xgap.cm
        dy = ygap.cm
        if relative:
            dx += xd
            dy += yd
        if self.context.themes.dark:
            backcolor = "black"
            forecolor = "white"
        else:
            backcolor = "white"
            forecolor = "black"
        img = Image.new(mode="RGB", size=(dimension, dimension), color=backcolor)
        draw = ImageDraw.Draw(img)

        if relative:
            maxx = col_count * (xd + dx) + xd
            maxy = row_count * (yd + dy) + yd
        else:
            maxx = col_count * xd + xd
            maxy = row_count * yd + yd
        max_xy = max(maxx, maxy)
        ixd = int(dimension * xd / max_xy)
        iyd = int(dimension * yd / max_xy)
        x = 0
        for colidx in range(col_count):
            y = 0
            for rowidx in range(row_count):
                if colidx == mypos_c and rowidx == mypos_r:
                    color = "red"
                else:
                    color = forecolor
                ix = int(dimension * x / max_xy)
                iy = int(dimension * y / max_xy)
                draw.rectangle([(ix, iy), (ix + ixd - 1, iy + iyd - 1)], outline=color)

                y += dy
            x += dx

        return PIL2wx(img)

    def preview_circular(self, variables, dimension=400):
        return None

    def preview_radial(self, variables, dimension=400):
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
