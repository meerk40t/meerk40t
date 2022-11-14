import wx

from meerk40t.gui.icons import STD_ICON_SIZE, icons8_keyhole_50, icons8_split_table_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import TextCtrl
from meerk40t.kernel import signal_listener
from meerk40t.svgelements import Color

_ = wx.GetTranslation


class InfoPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.lbl_info_main = wx.StaticText(self, wx.ID_ANY, "")
        self.lbl_info_default = wx.StaticText(self, wx.ID_ANY, "")
        self.lbl_info_first = wx.StaticText(self, wx.ID_ANY, "")
        self.lbl_info_last = wx.StaticText(self, wx.ID_ANY, "")
        self.preview_size = 25
        self.image_default = wx.StaticBitmap(
            self, wx.ID_ANY, size=wx.Size(self.preview_size, self.preview_size)
        )
        self.image_first = wx.StaticBitmap(
            self, wx.ID_ANY, size=wx.Size(self.preview_size, self.preview_size)
        )
        self.image_last = wx.StaticBitmap(
            self, wx.ID_ANY, size=wx.Size(self.preview_size, self.preview_size)
        )
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        sizer_default = wx.BoxSizer(wx.HORIZONTAL)
        sizer_default.Add(self.image_default, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_default.Add(self.lbl_info_default, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_first = wx.BoxSizer(wx.HORIZONTAL)
        sizer_first.Add(self.image_first, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_first.Add(self.lbl_info_first, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_last = wx.BoxSizer(wx.HORIZONTAL)
        sizer_last.Add(self.image_last, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_last.Add(self.lbl_info_last, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_main.Add(self.lbl_info_main, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_default, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_first, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_last, 0, wx.EXPAND, 0)
        self.make_raster = None
        self.SetSizer(sizer_main)
        self.Layout

    def show_stuff(self, has_emph):
        def create_image_from_node(node, iconsize):
            image = wx.NullBitmap
            c = None
            # Do we have a standard representation?
            defaultcolor = Color("black")
            if node.type.startswith("elem "):
                if (
                    hasattr(node, "stroke")
                    and node.stroke is not None
                    and node.stroke.argb is not None
                ):
                    c = node.stroke
            if node.type.startswith("elem ") and node.type != "elem point":
                image = self.make_raster(
                    node,
                    node.paint_bounds,
                    width=iconsize,
                    height=iconsize,
                    bitmap=True,
                    keep_ratio=True,
                )

            if c is None:
                c = defaultcolor
            return c, image

        if self.make_raster is None:
            self.make_raster = self.context.elements.lookup("render-op/make_raster")

        count = 0
        msg = ""
        if has_emph:
            data = list(self.context.elements.flat(emphasized=True))
            count = len(data)
            self.lbl_info_main.SetLabel(
                _("Selected elements: {count}").format(count=count)
            )
            if count > 0:
                node = data[0]
                c, image = create_image_from_node(node, self.preview_size)
                self.image_default.SetBitmap(image)
                self.lbl_info_default.SetLabel(
                    _("As in Selection: {type} {lbl}").format(
                        type=node.type, lbl=node.label
                    )
                )

                data.sort(key=lambda n: n.emphasized_time)
                node = data[0]
                c, image = create_image_from_node(node, self.preview_size)
                self.image_first.SetBitmap(image)
                self.lbl_info_first.SetLabel(
                    _("First selected: {type} {lbl}").format(
                        type=node.type, lbl=node.label
                    )
                )

                node = data[-1]
                c, image = create_image_from_node(node, self.preview_size)
                self.image_last.SetBitmap(image)
                self.lbl_info_last.SetLabel(
                    _("Last selected: {type} {lbl}").format(
                        type=node.type, lbl=node.label
                    )
                )
        else:
            self.lbl_info_default.SetLabel("")
            self.lbl_info_first.SetLabel("")
            self.lbl_info_last.SetLabel("")
            self.lbl_info_main.SetLabel(_("No elements selected"))
            self.image_default.SetBitmap(wx.NullBitmap)
            self.image_first.SetBitmap(wx.NullBitmap)
            self.image_last.SetBitmap(wx.NullBitmap)
        return count


class SplitterPanel(wx.Panel):
    def __init__(self, *args, context=None, scene=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.scene = scene
        # Amount of currently selected
        self.count = 0
        self.first_node = None
        self.last_node = None

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.selchoices = (
            _("Selection"),
            _("First Selected"),
            _("Last Selected"),
        )
        self.selectparam = ("default", "first", "last")

        self.split_x = wx.SpinCtrl(self, wx.ID_ANY, initial=1, min=1, max=25)
        self.split_y = wx.SpinCtrl(self, wx.ID_ANY, initial=1, min=1, max=25)

        self.rbox_selection = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Order to process:"),
            choices=self.selchoices,
            majorDimension=3,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_selection.SetSelection(0)
        self.text_dpi = TextCtrl(self, wx.ID_ANY, limited=True, check="int")
        self.text_dpi.SetValue("500")
        self.lbl_info = wx.StaticText(self, wx.ID_ANY, "")
        self.btn_align = wx.Button(self, wx.ID_ANY, _("Create split images"))
        self.btn_align.SetBitmap(icons8_split_table_50.GetBitmap(resize=25))

        lbl_dpi = wx.StaticText(self, wx.ID_ANY, "DPI:")
        sizer_dpi = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Image resolution:")), wx.HORIZONTAL
        )
        sizer_dpi.Add(lbl_dpi, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_dpi.Add(self.text_dpi, 1, wx.EXPAND, 0)

        sizer_dimensions = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dim_x = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("X-Axis:")),
            wx.VERTICAL,
        )
        sizer_dim_x.Add(self.split_x, 0, wx.EXPAND, 0)

        sizer_dim_y = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Y-Axis:")),
            wx.VERTICAL,
        )
        sizer_dim_y.Add(self.split_y, 0, wx.EXPAND, 0)

        sizer_dimensions.Add(sizer_dim_x, 1, wx.EXPAND, 0)
        sizer_dimensions.Add(sizer_dim_y, 1, wx.EXPAND, 0)

        sizer_main.Add(sizer_dimensions, 0, wx.EXPAND, 0)

        sizer_main.Add(self.rbox_selection, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_dpi, 0, wx.EXPAND, 0)
        sizer_main.Add(self.btn_align, 0, wx.EXPAND, 0)
        self.info_panel = InfoPanel(self, wx.ID_ANY, context=self.context)

        sizer_main.Add(self.info_panel, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_split, self.btn_align)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_selection)
        self.Bind(wx.EVT_SPINCTRL, self.validate_data, self.split_x)
        self.Bind(wx.EVT_SPINCTRL, self.validate_data, self.split_y)
        self.Bind(wx.EVT_TEXT, self.validate_data, self.text_dpi)
        has_emph = self.context.elements.has_emphasis()
        self.context.setting(int, "split_x", 0)
        self.context.setting(int, "split_y", 0)
        self.context.setting(int, "split_selection", 0)
        self.context.setting(str, "split_dpi", "500")
        self.restore_setting()
        self.show_stuff(has_emph)

    def validate_data(self, event=None):
        if event is not None:
            event.Skip()
        if self.context.elements.has_emphasis():
            active = True
            num_cols = self.split_x.GetValue()
            num_rows = self.split_y.GetValue()
            idx = self.rbox_selection.GetSelection()
            if idx < 0:
                idx = 0
            esort = self.selectparam[idx]
            try:
                dpi = int(self.text_dpi.GetValue())
            except ValueError:
                dpi = 0
            if dpi <= 0:
                active = False
        else:
            active = False
        # active = True
        self.btn_align.Enable(active)

    def on_button_split(self, event):
        num_cols = self.split_x.GetValue()
        num_rows = self.split_y.GetValue()
        idx = self.rbox_selection.GetSelection()
        if idx < 0:
            idx = 0
        esort = self.selectparam[idx]
        try:
            mydpi = int(self.text_dpi.GetValue())
        except ValueError:
            mydpi = 500
        cmdstr = f"render_split {num_cols} {num_rows} {mydpi} --order {esort}\n"
        self.context(cmdstr)
        self.save_setting()

    def save_setting(self):
        self.context.split_selection = self.rbox_selection.GetSelection()
        self.context.split_x = self.split_x.GetValue()
        self.context.split_y = self.split_y.GetValue()
        self.context.split_dpi = self.text_dpi.GetValue()

    def restore_setting(self):
        try:
            self.rbox_selection.SetSelection(self.context.split_selection)
            self.split_x.SetValue(self.context.split_x)
            self.split_y.SetValue(self.context.split_y)
            self.text_dpi.SetValue(self.context.split_dpi)
        except (ValueError, AttributeError, RuntimeError):
            pass

    def show_stuff(self, has_emph):
        self.count = self.info_panel.show_stuff(has_emph)
        self.rbox_selection.Enable(has_emph)
        self.split_x.Enable(has_emph)
        self.split_y.Enable(has_emph)
        self.text_dpi.Enable(has_emph)
        self.validate_data()


class KeyholePanel(wx.Panel):
    def __init__(self, *args, context=None, scene=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.scene = scene
        # Amount of currently selected
        self.count = 0
        self.first_node = None
        self.last_node = None

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.selchoices = (
            _("First Selected"),
            _("Last Selected"),
        )
        self.selectparam = ("first", "last")

        self.rbox_selection = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Keyhole Object:"),
            choices=self.selchoices,
            majorDimension=2,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_selection.SetSelection(0)
        self.text_dpi = TextCtrl(self, wx.ID_ANY, limited=True, check="int")
        self.text_dpi.SetValue("500")
        self.info_panel = InfoPanel(self, wx.ID_ANY, context=self.context)

        self.btn_align = wx.Button(self, wx.ID_ANY, _("Create keyhole image"))
        self.btn_align.SetBitmap(icons8_keyhole_50.GetBitmap(resize=25))

        lbl_dpi = wx.StaticText(self, wx.ID_ANY, "DPI:")
        sizer_dpi = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Image resolution:")), wx.HORIZONTAL
        )
        sizer_dpi.Add(lbl_dpi, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_dpi.Add(self.text_dpi, 1, wx.EXPAND, 0)

        sizer_options = wx.BoxSizer(wx.HORIZONTAL)
        sizer_check_invert = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Invert Mask:")),
            wx.HORIZONTAL,
        )
        sizer_check_outline = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Trace Keyhole:")),
            wx.HORIZONTAL,
        )
        self.check_invert = wx.CheckBox(self, wx.ID_ANY, "Invert")
        self.check_outline = wx.CheckBox(self, wx.ID_ANY, "Trace")

        sizer_check_invert.Add(self.check_invert, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_check_outline.Add(self.check_outline, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_options.Add(sizer_dpi, 1, wx.EXPAND, 0)
        sizer_options.Add(sizer_check_invert, 1, wx.EXPAND, 0)
        sizer_options.Add(sizer_check_outline, 1, wx.EXPAND, 0)

        sizer_main.Add(self.rbox_selection, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_options, 0, wx.EXPAND, 0)
        sizer_main.Add(self.btn_align, 0, wx.EXPAND, 0)
        sizer_main.Add(self.info_panel, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_keyhole, self.btn_align)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_selection)
        self.Bind(wx.EVT_CHECKBOX, self.validate_data, self.check_invert)
        self.Bind(wx.EVT_CHECKBOX, self.validate_data, self.check_outline)
        self.Bind(wx.EVT_TEXT, self.validate_data, self.text_dpi)
        has_emph = self.context.elements.has_emphasis()
        self.context.setting(int, "keyhole_selection", 0)
        self.context.setting(str, "keyhole_dpi", "500")
        self.context.setting(bool, "keyhole_invert", False)
        self.context.setting(bool, "keyhole_outline", True)
        self.restore_setting()
        self.show_stuff(has_emph)

    def validate_data(self, event=None):
        if event is not None:
            event.Skip()
        if self.context.elements.has_emphasis():
            active = True
            invert = self.check_invert.GetValue()
            outline = self.check_outline.GetValue()
            idx = self.rbox_selection.GetSelection()
            if idx < 0:
                idx = 0
            esort = self.selectparam[idx]
            try:
                dpi = int(self.text_dpi.GetValue())
            except ValueError:
                dpi = 0
            if dpi <= 0:
                active = False
            # if self.count < 2:
            #     active = False
        else:
            active = False
        # active = True
        self.btn_align.Enable(active)

    def on_button_keyhole(self, event):
        idx = self.rbox_selection.GetSelection()
        if idx < 0:
            idx = 0
        esort = self.selectparam[idx]
        try:
            mydpi = int(self.text_dpi.GetValue())
        except ValueError:
            mydpi = 500
        if self.check_invert.GetValue():
            invert = " --invert 1"
        else:
            invert = ""
        if self.check_outline.GetValue():
            outline = " --outline 1"
        else:
            outline = ""
        cmdstr = f"render_keyhole {mydpi} --order {esort}{invert}{outline}\n"
        self.context(cmdstr)
        self.save_setting()

    def save_setting(self):
        self.context.keyhole_selection = self.rbox_selection.GetSelection()
        self.context.keyhole_invert = self.check_invert.GetValue()
        self.context.keyhole_outline = self.check_outline.GetValue()
        self.context.keyhole_dpi = self.text_dpi.GetValue()

    def restore_setting(self):
        try:
            self.rbox_selection.SetSelection(self.context.keyhole_selection)
            self.check_invert.SetValue(bool(self.context.keyhole_invert))
            self.check_outline.SetValue(bool(self.context.keyhole_outline))
            self.text_dpi.SetValue(self.context.keyhole_dpi)
        except (ValueError, AttributeError, RuntimeError):
            pass

    def show_stuff(self, has_emph):
        self.count = self.info_panel.show_stuff(has_emph)
        self.rbox_selection.Enable(has_emph)
        self.check_invert.Enable(has_emph)
        self.check_outline.Enable(has_emph)
        self.text_dpi.Enable(has_emph)
        self.validate_data()


class RenderSplit(MWindow):
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
        self.scene = getattr(self.context.root, "mainscene", None)
        # Hide Arrangement until ready...
        self.panel_split = SplitterPanel(
            self, wx.ID_ANY, context=self.context, scene=self.scene
        )
        self.panel_keyhole = KeyholePanel(
            self, wx.ID_ANY, context=self.context, scene=self.scene
        )
        self.notebook_main.AddPage(self.panel_split, _("Render + Split"))
        self.notebook_main.AddPage(self.panel_keyhole, _("Keyhole operation"))

        self.Layout()

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_split_table_50.GetBitmap(resize=25))
        self.SetIcon(_icon)
        self.SetTitle(_("Create split images"))

    def delegates(self):
        yield self.panel_split
        yield self.panel_keyhole

    @signal_listener("reference")
    @signal_listener("emphasized")
    def on_emphasize_signal(self, origin, *args):
        has_emph = self.context.elements.has_emphasis()
        self.panel_split.show_stuff(has_emph)
        self.panel_keyhole.show_stuff(has_emph)

    @staticmethod
    def sub_register(kernel):
        bsize_normal = STD_ICON_SIZE
        bsize_small = int(STD_ICON_SIZE / 2)

        kernel.register(
            "button/align/SplitImage",
            {
                "label": _("Image ops"),
                "icon": icons8_split_table_50,
                "tip": _("Open create split image dialog / keyhole generation"),
                "action": lambda v: kernel.console("window toggle SplitImage\n"),
                "size": bsize_normal,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )

    def window_open(self):
        pass

    def window_close(self):
        pass

    @staticmethod
    def submenu():
        return ("Editing", "Image Splitting")
