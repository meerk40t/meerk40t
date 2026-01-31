"""
This module contains panels that display internal developer information.
They will become visible if you type 'set debug_mode True' in the
console and restart the program.

The module provides a set of wxPython panels for debugging, including device view, color, icon, window, and raster plotter panels.
These panels are intended for developers to inspect internal state, test shutdown scenarios, and visualize system resources.
"""

import time

import wx
from wx import aui

import meerk40t.gui.icons as mkicons
from meerk40t.constants import (
    RASTER_B2T,
    RASTER_CROSSOVER,
    RASTER_GREEDY_H,
    RASTER_GREEDY_V,
    RASTER_HATCH,
    RASTER_L2R,
    RASTER_R2L,
    RASTER_SPIRAL,
    RASTER_T2B,
)
from meerk40t.core.units import Angle, Length
from meerk40t.gui.wxutils import (
    ScrolledPanel,
    StaticBoxSizer,
    TextCtrl,
    wxButton,
    wxCheckBox,
    wxComboBox,
    wxRadioBox,
    wxStaticBitmap,
    wxStaticText,
    wxToggleButton,
    dispatch_to_main_thread,
)
from meerk40t.kernel.kernel import signal_listener
from meerk40t.svgelements import Color

_ = wx.GetTranslation


def register_panel_debugger(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Float()
        .MinSize(225, 110)
        .FloatingSize(400, 400)
        .Caption(_("Position"))
        .CaptionVisible(not context.pane_lock)
        .Name("debug_tree")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = DebugTreePanel(window, wx.ID_ANY, context=context)
    pane.submenu = "_ZZ_" + _("Debug")
    pane.helptext = _("Some internal debugging routines")
    window.on_pane_create(pane)
    context.register("pane/debug_tree", pane)


def register_panel_color(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Float()
        .MinSize(225, 110)
        .FloatingSize(400, 400)
        .Caption(_("System-Colors"))
        .CaptionVisible(not context.pane_lock)
        .Name("debug_color")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = DebugColorPanel(window, wx.ID_ANY, context=context)
    pane.submenu = "_ZZ_" + _("Debug")
    pane.helptext = _("Display available color information")
    window.on_pane_create(pane)
    context.register("pane/debug_color", pane)


def register_panel_view(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Float()
        .MinSize(225, 110)
        .FloatingSize(400, 400)
        .Caption(_("Device-View"))
        .CaptionVisible(not context.pane_lock)
        .Name("debug_view")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = DebugViewPanel(window, wx.ID_ANY, context=context)
    pane.submenu = "_ZZ_" + _("Debug")
    pane.helptext = _("Display information about device view")
    window.on_pane_create(pane)
    context.register("pane/debug_view", pane)


def register_panel_icon(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Float()
        .MinSize(225, 110)
        .FloatingSize(400, 400)
        .Caption(_("Icons"))
        .CaptionVisible(not context.pane_lock)
        .Name("debug_icons")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = DebugIconPanel(window, wx.ID_ANY, context=context)
    pane.submenu = "_ZZ_" + _("Debug")
    pane.helptext = _("Display available icons")
    window.on_pane_create(pane)
    context.register("pane/debug_icons", pane)


def register_panel_crash(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Float()
        .MinSize(225, 110)
        .FloatingSize(400, 400)
        .Caption(_("Shutdown Test"))
        .CaptionVisible(not context.pane_lock)
        .Name("debug_shutdown")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = ShutdownPanel(window, wx.ID_ANY, context=context)
    pane.submenu = "_ZZ_" + _("Debug")
    pane.helptext = _("Try some shutdown routines to figure out exit crashes")
    window.on_pane_create(pane)
    context.register("pane/debug_shutdown", pane)


def register_panel_window(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Float()
        .MinSize(225, 110)
        .FloatingSize(400, 400)
        .Caption(_("Window Test"))
        .CaptionVisible(not context.pane_lock)
        .Name("debug_window")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = DebugWindowPanel(window, wx.ID_ANY, context=context)
    pane.submenu = "_ZZ_" + _("Debug")
    pane.helptext = _("Show available windows")
    window.on_pane_create(pane)
    context.register("pane/debug_window", pane)


def register_panel_plotter(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Float()
        .MinSize(225, 110)
        .FloatingSize(400, 400)
        .Caption(_("Plotter Test"))
        .CaptionVisible(not context.pane_lock)
        .Name("debug_plotter")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = DebugRasterPlotterPanel(window, wx.ID_ANY, context=context)
    pane.submenu = "_ZZ_" + _("Debug")
    pane.helptext = _("Raster plotter test")
    window.on_pane_create(pane)
    context.register("pane/debug_plotter", pane)

    pane = (
        aui.AuiPaneInfo()
        .Float()
        .MinSize(225, 110)
        .FloatingSize(400, 400)
        .Caption(_("Op Settings"))
        .CaptionVisible(not context.pane_lock)
        .Name("debug_settings")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = DebugSettingsPanel(window, wx.ID_ANY, context=context)
    pane.submenu = "_ZZ_" + _("Debug")
    pane.helptext = _("OP Settings test")
    window.on_pane_create(pane)
    context.register("pane/debug_settings", pane)


class ShutdownPanel(wx.Panel):
    """
    Tries to create a scenario that has led to multiple runtime errors durign shutdown
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        info = wxStaticText(
            self,
            wx.ID_ANY,
            (
                "Please be careful, if you click on one of the buttons below, "
                + "we will try to create a scenario that hopefully will help us "
                + "identify an edge case crash.\n"
                + "So please save your work first, as it will be compromised!"
            ),
        )
        self.btn_scenario_kernel_first = wxButton(self, wx.ID_ANY, "Kill kernel first")
        self.btn_scenario_gui_first = wxButton(self, wx.ID_ANY, "Kill GUI first")
        self.btn_scenario_only = wxButton(self, wx.ID_ANY, "Just create the scenario")
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(info, 0, wx.EXPAND, 0)
        main_sizer.Add(self.btn_scenario_kernel_first, 0, wx.EXPAND, 0)
        main_sizer.Add(self.btn_scenario_gui_first, 0, wx.EXPAND, 0)
        main_sizer.Add(self.btn_scenario_only, 0, wx.EXPAND, 0)
        self.Bind(wx.EVT_BUTTON, self.die_kernel_die, self.btn_scenario_kernel_first)
        self.Bind(wx.EVT_BUTTON, self.die_gui_die, self.btn_scenario_gui_first)
        self.Bind(wx.EVT_BUTTON, self.create_scenario, self.btn_scenario_only)
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()

    def prepare_scenario(self):
        self.context.elements.clear_all()
        cm = float(Length("1cm"))
        hatchangle = Angle("45deg")
        rootnode = self.context.elements.elem_branch
        x = cm
        y = cm
        nodes = []
        elem_nodes = []
        for idx in range(150):
            cnode = rootnode.add(
                type="elem ellipse",
                cx=x,
                cy=y,
                rx=cm,
                ry=cm,
                stroke=Color("blue"),
                stroke_width=100,
                fill=None,
            )
            enode = rootnode.add(
                type="effect hatch",
                label="Hatch Effect",
                hatch_type="scanline",
                hatch_angle=hatchangle.radians,
                hatch_angle_delta=0,
                hatch_distance="0.2mm",  # cm / 50,
                stroke=Color("green"),
                stroke_width=100,
            )
            enode.append_child(cnode)
            elem_nodes.append(cnode)
            nodes.append(cnode)
            nodes.append(enode)

            if idx % 15 == 0:
                x = cm
                y += cm
            else:
                x += cm
        self.context.elements.classify(nodes)
        self.context.elements.set_emphasis(elem_nodes)
        self.context.signal("refresh_scene")
        self.context.signal("refresh_tree")
        self.context.signal("emphasized")
        self.context.signal("element_property_reload", nodes)

    def die_kernel_die(self, event):
        self.prepare_scenario()
        self.context("quit\n")

    def die_gui_die(self, event):
        self.prepare_scenario()
        self.context.gui.Close()

    def create_scenario(self, event):
        self.prepare_scenario()

    def pane_show(self, *args):
        return

    def pane_hide(self, *args):
        return


class DebugTreePanel(wx.Panel):
    """
    Displays information about selected elements
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.lb_selected = TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE)
        self.lb_emphasized = TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE)
        self.txt_first = TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)

        self.__set_properties()
        self.__do_layout()

        # end wxGlade

        self._update_position()

    def pane_show(self, *args):
        self.context.listen("emphasized", self._update_position)
        self.context.listen("selected", self._update_position)

    def pane_hide(self, *args):
        self.context.unlisten("emphasized", self._update_position)
        self.context.unlisten("selected", self._update_position)

    def __set_properties(self):
        # begin wxGlade: PositionPanel.__set_properties
        self.lb_emphasized.SetToolTip(_("Emphasized nodes"))
        self.lb_selected.SetToolTip(_("Selected nodes"))
        self.txt_first.SetToolTip(_("Primus inter pares"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: PositionPanel.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_1 = StaticBoxSizer(self, wx.ID_ANY, _("Selected:"), wx.VERTICAL)
        sizer_2 = StaticBoxSizer(self, wx.ID_ANY, _("Emphasized:"), wx.VERTICAL)
        sizer_1.Add(self.lb_selected, 1, wx.EXPAND, 0)
        sizer_2.Add(self.lb_emphasized, 1, wx.EXPAND, 0)
        sizer_2.Add(self.txt_first, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_1, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_2, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()
        # end wxGlade

    @dispatch_to_main_thread
    def _update_position(self, *args, **kwargs):
        self.context.elements.set_start_time("Emphasis mkdebug")
        self.update_position(True)
        self.context.elements.set_end_time("Emphasis mkdebug")

    def update_position(self, reset):
        def timestr(ts):
            if ts is None:
                return "---"
            else:
                return time.strftime("%H:%M:%S", time.localtime(ts))

        txt1 = ""
        txt2 = ""
        for node in self.context.elements.elems(selected=True):
            txt1 += str(node) + "\n"
        data = self.context.elements.elems(emphasized=True)
        for node in data:
            txt2 += (
                f"{node.id} - {node.type} {node.display_label()} - {timestr(node._emphasized_time)}"
                + "\n"
            )
        node = self.context.elements.first_emphasized  # (data)
        if node is None:
            txt3 = ""
        else:
            txt3 = f"{node.id} - {node.type} {node.display_label()} - {timestr(node._emphasized_time)}"

        self.lb_selected.SetValue(txt1)
        self.lb_emphasized.SetValue(txt2)

        self.txt_first.SetValue(txt3)


class DebugViewPanel(ScrolledPanel):
    """
    Displays information about the device view and provides coordinate conversion tools.

    This panel shows device-specific information and allows users to convert between
    workspace and device coordinates.
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)

        self.context = context
        self.context.themes.set_window_colors(self)

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.info_device = wx.TextCtrl(
            self, wx.ID_ANY, style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        # Set teletype (monospace) font
        mono_font = wx.Font(
            10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )
        self.info_device.SetFont(mono_font)

        sizer_main.Add(self.info_device, 1, wx.EXPAND, 0)
        pos_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Coordinates to Device"), wx.HORIZONTAL
        )
        self.text_x = wx.TextCtrl(self, wx.ID_ANY)
        self.text_y = wx.TextCtrl(self, wx.ID_ANY)
        self.check_vector = wxCheckBox(self, wx.ID_ANY, "V")
        self.check_vector.SetToolTip(_("Vector-mode: only transition"))
        self.button_test = wxButton(self, wx.ID_ANY, _("Convert"))
        self.info_position = wxStaticText(self, wx.ID_ANY)
        pos_sizer.Add(self.text_x, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        pos_sizer.Add(self.text_y, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        pos_sizer.Add(self.check_vector, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        pos_sizer.Add(self.button_test, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        pos_sizer.Add(self.info_position, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_main.Add(pos_sizer, 0, wx.EXPAND, 0)
        ipos_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Device to Coordinates"), wx.HORIZONTAL
        )
        self.text_ix = wx.TextCtrl(self, wx.ID_ANY)
        self.text_iy = wx.TextCtrl(self, wx.ID_ANY)
        self.check_ivector = wxCheckBox(self, wx.ID_ANY, "V")
        self.check_ivector.SetToolTip(_("Vector-mode: only transition"))
        self.button_itest = wxButton(self, wx.ID_ANY, _("Convert"))
        self.info_iposition = wxStaticText(self, wx.ID_ANY)
        ipos_sizer.Add(self.text_ix, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        ipos_sizer.Add(self.text_iy, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        ipos_sizer.Add(self.check_ivector, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        ipos_sizer.Add(self.button_itest, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        ipos_sizer.Add(self.info_iposition, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_main.Add(ipos_sizer, 0, wx.EXPAND, 0)
        self.Bind(wx.EVT_BUTTON, self.on_test_position, self.button_test)
        self.Bind(wx.EVT_BUTTON, self.on_test_iposition, self.button_itest)
        self.SetupScrolling()
        self.SetSizer(sizer_main)
        self.Layout()

    def on_test_position(self, event):
        try:
            x = float(Length(self.text_x.GetValue()))
            y = float(Length(self.text_y.GetValue()))
        except ValueError:
            self.info_position.SetLabel(_("Invalid length value"))
            return
        from meerk40t.core.view import View

        dview: View = self.context.device.view
        vector = bool(self.check_vector.GetValue())
        mx, my = dview.position(x, y, vector=vector)
        self.info_position.SetLabel(f"x={mx:.2f}, y={my:.2f}")
        if event is not None:
            self.text_ix.SetValue(f"{mx:.2f}")
            self.text_iy.SetValue(f"{my:.2f}")

    def on_test_iposition(self, event):
        try:
            x = float(self.text_ix.GetValue())
            y = float(self.text_iy.GetValue())
        except ValueError:
            self.info_iposition.SetLabel(_("Invalid length value"))
            return
        from meerk40t.core.view import View

        dview: View = self.context.device.view
        vector = bool(self.check_ivector.GetValue())
        mx, my = dview.iposition(x, y, vector=vector)
        self.info_iposition.SetLabel(
            f"x={Length(mx, digits=2).length_mm}, y={Length(my, digits=2).length_mm}"
        )
        if event is not None:
            self.text_x.SetValue(Length(mx).length_mm)
            self.text_y.SetValue(Length(my).length_mm)

    def refresh_info(self):
        def sc(coord):
            return f"({coord[0]:.1f}, {coord[1]:.1f})"

        def disp(source):
            top_left, top_right, bottom_right, bottom_left = source
            return f"TL: {sc(top_left)}, TR: {sc(top_right)}, BL: {sc(bottom_left)}, BR: {sc(bottom_right)}"

        from meerk40t.core.view import View

        infomsg = ""
        dev = self.context.device
        dview: View = dev.view
        infomsg = f"{infomsg}Device     : {dev.label}\n"
        infomsg = f"{infomsg}Offset-X   : {Length(dview.margin_x).length_mm}\n"
        infomsg = f"{infomsg}Offset-Y   : {Length(dview.margin_y).length_mm}\n"

        infomsg = f"{infomsg}Width      : {Length(dview.width).length_mm}\n"
        infomsg = f"{infomsg}Height     : {Length(dview.height).length_mm}\n"
        if dview._source is not None:
            infomsg = f"{infomsg}Source     : {disp(dview._source)}\n"
        if dview._destination is not None:
            infomsg = f"{infomsg}Destination: {disp(dview._destination)}\n"
            tl, tr, br, bl = dview._destination
            if tl[0] > bl[0]:
                infomsg = f"{infomsg}Flip-X : X-Axis appears flipped.\n"
            if tl[1] > bl[1]:
                infomsg = f"{infomsg}Flip-Y : Y-Axis appears flipped.\n"

        def devinfo(attrib):
            if hasattr(dev, attrib):
                info = "yes" if getattr(dev, attrib) else "no"
            else:
                info = "undef"
            return info

        xflip = devinfo("flip_x")
        yflip = devinfo("flip_y")
        xyswap = devinfo("swap_xy")
        infomsg = f"{infomsg}Device-Flip : X:{xflip}, Y:{yflip}, swap xy: {xyswap}\n"
        self.info_device.SetValue(infomsg)

    @signal_listener("view;realized")
    @signal_listener("device;modified")
    @dispatch_to_main_thread
    def on_view_change(self, origin, *args, **kwargs):
        self.refresh_info()
        self.on_test_position(None)

    def pane_show(self, *args):
        self.refresh_info()

    def pane_hide(self, *args):
        return


class DebugColorPanel(ScrolledPanel):
    """
    Displays system defined (OS and wxpython) colors to simplify identifying / choosing them
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)

        self.context = context
        self.context.themes.set_window_colors(self)

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        count = 1000
        font = wx.Font(
            6, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )
        pattern = "SYS_COLOUR_"
        for prop in dir(wx):
            if prop.startswith(pattern):
                # print (prop)
                count += 1
                if count >= 5:
                    sizer_line = wx.BoxSizer(wx.HORIZONTAL)
                    sizer_main.Add(sizer_line, 0, wx.EXPAND, 0)
                    count = 0

                col: wx.Colour = wx.SystemSettings().GetColour(getattr(wx, prop))
                infosizer = wx.BoxSizer(wx.VERTICAL)
                box = wxStaticBitmap(
                    self, wx.ID_ANY, size=wx.Size(32, 32), style=wx.SB_RAISED
                )
                box.SetBackgroundColour(col)
                box.SetToolTip(f"{prop}: {col.GetAsString()}")
                lbl = wxStaticText(self, wx.ID_ANY, prop[len(pattern) :])
                lbl.SetFont(font)
                lbl.SetMinSize(wx.Size(75, -1))
                infosizer.Add(box, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
                infosizer.Add(lbl, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

                sizer_line.Add(infosizer, 1, wx.EXPAND, 0)
        count = 1000  # New line
        coldb = (
            "AQUAMARINE",
            "FIREBRICK",
            "MEDIUM FOREST GREEN",
            "RED",
            "BLACK",
            "FOREST GREEN",
            "MEDIUM GOLDENROD",
            "SALMON",
            "BLUE",
            "GOLD",
            "MEDIUM ORCHID",
            "SEA GREEN",
            "BLUE VIOLET",
            "GOLDENROD",
            "MEDIUM SEA GREEN",
            "SIENNA",
            "BROWN",
            "GREY",
            "MEDIUM SLATE BLUE",
            "SKY BLUE",
            "CADET BLUE",
            "GREEN",
            "MEDIUM SPRING GREEN",
            "SLATE BLUE",
            "CORAL",
            "GREEN YELLOW",
            "MEDIUM TURQUOISE",
            "SPRING GREEN",
            "CORNFLOWER BLUE",
            "INDIAN RED",
            "MEDIUM VIOLET RED",
            "STEEL BLUE",
            "CYAN",
            "KHAKI",
            "MIDNIGHT BLUE",
            "TAN",
            "DARK GREY",
            "LIGHT BLUE",
            "NAVY",
            "THISTLE",
            "DARK GREEN",
            "LIGHT GREY",
            "ORANGE",
            "TURQUOISE",
            "DARK OLIVE GREEN",
            "LIGHT STEEL BLUE",
            "ORANGE RED",
            "VIOLET",
            "DARK ORCHID",
            "LIME GREEN",
            "ORCHID",
            "VIOLET RED",
            "DARK SLATE BLUE",
            "MAGENTA",
            "PALE GREEN",
            "WHEAT",
            "DARK SLATE GREY",
            "MAROON",
            "PINK",
            "WHITE",
            "DARK TURQUOISE",
            "MEDIUM AQUAMARINE",
            "PLUM",
            "YELLOW",
            "DIM GREY",
            "MEDIUM BLUE",
            "PURPLE",
            "YELLOW GREEN",
        )
        for entry in coldb:
            count += 1
            if count >= 5:
                sizer_line = wx.BoxSizer(wx.HORIZONTAL)
                sizer_main.Add(sizer_line, 0, wx.EXPAND, 0)
                count = 0

            col = wx.Colour(entry)
            infosizer = wx.BoxSizer(wx.VERTICAL)
            box = wxStaticBitmap(
                self, wx.ID_ANY, size=wx.Size(32, 32), style=wx.SB_RAISED
            )
            box.SetBackgroundColour(col)
            box.SetToolTip(entry)
            lbl = wxStaticText(self, wx.ID_ANY, entry)
            lbl.SetFont(font)
            lbl.SetMinSize(wx.Size(75, -1))
            infosizer.Add(box, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
            infosizer.Add(lbl, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

            sizer_line.Add(infosizer, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()
        self.SetupScrolling()

    def pane_show(self, *args):
        return

    def pane_hide(self, *args):
        return


class DebugIconPanel(wx.Panel):
    """
    Displays defined icons in a bigger size to facilitate debugging / changing them
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)

        self.context = context
        self.context.themes.set_window_colors(self)

        self.icon = None

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        choose_sizer = wx.BoxSizer(wx.HORIZONTAL)

        lbl = wxStaticText(self, wx.ID_ANY, "Pick icon")

        self.icon_list = list()
        for entry in dir(mkicons):
            # print (entry)
            if entry.startswith("icon"):
                s = getattr(mkicons, entry)
                if isinstance(s, (mkicons.VectorIcon, mkicons.PyEmbeddedImage)):
                    self.icon_list.append(entry)
        self.combo_icons = wxComboBox(
            self,
            wx.ID_ANY,
            choices=self.icon_list,
            style=wx.CB_SORT | wx.CB_READONLY | wx.CB_DROPDOWN,
        )
        choose_sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        choose_sizer.Add(self.combo_icons, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_main.Add(choose_sizer, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.icon_show = wxStaticBitmap(self, wx.ID_ANY)
        self.context.themes.set_window_colors(self.icon_show)
        sizer_main.Add(self.icon_show, 1, wx.EXPAND, 0)
        sizer_main.Fit(self)
        self.combo_icons.Bind(wx.EVT_COMBOBOX, self.on_combo)
        self.Layout()
        if self.icon_list:
            wx.CallAfter(self.show_first)

    def show_first(self):
        self.combo_icons.SetSelection(0)
        self.on_combo(None)

    def on_combo(self, event):
        idx = self.combo_icons.GetSelection()
        if idx < 0:
            return
        s = self.combo_icons.GetString(idx)
        if s:
            obj = getattr(mkicons, s, None)
            if obj is not None:
                if isinstance(obj, (mkicons.VectorIcon, mkicons.PyEmbeddedImage)):
                    imgs = self.icon_show.Size
                    ms = (
                        min(imgs[0], imgs[1])
                        * self.context.root.bitmap_correction_scale
                    )
                    bmp = obj.GetBitmap(
                        resize=ms, force_darkmode=self.context.themes.dark
                    )
                    self.icon_show.SetBitmap(bmp)

    def pane_show(self, *args):
        return

    def pane_hide(self, *args):
        return


class DebugWindowPanel(wx.Panel):
    """
    Displays and loads registered windows
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)

        self.context = context
        self.context.themes.set_window_colors(self)
        self.icon = None

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        choose_sizer = wx.BoxSizer(wx.HORIZONTAL)

        lbl = wxStaticText(self, wx.ID_ANY, "Pick Window")

        self.window_list = []
        for find in self.context.kernel.find("window/"):
            value, name, suffix = find
            self.window_list.append(suffix)

        self.combo_windows = wxComboBox(
            self,
            wx.ID_ANY,
            choices=self.window_list,
            style=wx.CB_SORT | wx.CB_READONLY | wx.CB_DROPDOWN,
        )
        choose_sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        choose_sizer.Add(self.combo_windows, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.btn_show_all = wxButton(self, wx.ID_ANY, "Open all windows")
        choose_sizer.Add(self.btn_show_all, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_main.Add(choose_sizer, 0, wx.EXPAND, 0)
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        left_side = StaticBoxSizer(self, wx.ID_ANY, "Default Controls", wx.VERTICAL)
        cb_left = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=("Option 1", "Option 2", "Option 3"),
            style=wx.CB_READONLY | wx.CB_DROPDOWN,
        )
        text_left = wx.TextCtrl(self, wx.ID_ANY, "")
        check_left = wx.CheckBox(self, wx.ID_ANY, label="Checkbox")
        btn_left = wx.Button(self, wx.ID_ANY, "A button")
        toggle_left = wx.ToggleButton(self, wx.ID_ANY, "Toggle")
        radio_left = wx.RadioBox(self, wx.ID_ANY, choices=("Yes", "No", "Maybe"))
        btn_bmap_left = wx.BitmapButton(
            self,
            wx.ID_ANY,
            mkicons.icon_bell.GetBitmap(
                resize=mkicons.get_default_icon_size(self.context) / 2
            ),
        )
        slider_left = wx.Slider(self, wx.ID_ANY, value=0, minValue=0, maxValue=100)
        static_left = wx.StaticBitmap(
            self,
            wx.ID_ANY,
            mkicons.icon_closed_door.GetBitmap(
                resize=mkicons.get_default_icon_size(self.context)
            ),
        )
        left_side.Add(cb_left, 0, 0, 0)
        left_side.Add(text_left, 0, 0, 0)
        left_side.Add(check_left, 0, 0, 0)
        left_side.Add(btn_left, 0, 0, 0)
        left_side.Add(toggle_left, 0, 0, 0)
        left_side.Add(radio_left, 0, 0, 0)
        left_side.Add(btn_bmap_left, 0, 0, 0)
        left_side.Add(slider_left, 0, 0, 0)
        left_side.Add(static_left, 0, 0, 0)
        for c in left_side.GetChildren():
            if c.IsWindow():
                w = c.GetWindow()
                w.SetToolTip(f"a tooltip for a default {type(w).__name__}")
        # cb_right = wxComboBox(self, wx.ID_ANY, choices=("Option 1", "Option 2", "Option 3"), style=wx.CB_READONLY|wx.CB_DROPDOWN)
        right_side = StaticBoxSizer(self, wx.ID_ANY, "Custom Controls", wx.VERTICAL)
        text_right = TextCtrl(self, wx.ID_ANY, "")
        check_right = wxCheckBox(self, wx.ID_ANY, label="Checkbox")
        btn_right = wxButton(self, wx.ID_ANY, "A button")
        toggle_right = wxToggleButton(self, wx.ID_ANY, "Toggle")
        radio_right = wxRadioBox(self, wx.ID_ANY, choices=("Yes", "No", "Maybe"))
        static_right = wxStaticBitmap(
            self,
            wx.ID_ANY,
            mkicons.icon_closed_door.GetBitmap(
                resize=mkicons.get_default_icon_size(self.context)
            ),
        )
        # right_side.Add(cb_right, 0, 0, 0)
        right_side.Add(text_right, 0, 0, 0)
        right_side.Add(check_right, 0, 0, 0)
        right_side.Add(btn_right, 0, 0, 0)
        right_side.Add(toggle_right, 0, 0, 0)
        right_side.Add(radio_right, 0, 0, 0)
        right_side.Add(static_right, 0, 0, 0)
        for c in right_side.GetChildren():
            if c.IsWindow():
                w = c.GetWindow()
                w.SetToolTip(f"a tooltip for a custom {type(w).__name__}")
        dummy_sizer.Add(left_side, 1, wx.EXPAND, 0)
        dummy_sizer.Add(right_side, 1, wx.EXPAND, 0)
        sizer_main.Add(dummy_sizer, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.combo_windows.Bind(wx.EVT_COMBOBOX, self.on_combo)
        self.btn_show_all.Bind(wx.EVT_BUTTON, self.on_button)
        self.Layout()

    def on_combo(self, event):
        idx = self.combo_windows.GetSelection()
        if idx < 0:
            return
        s = self.combo_windows.GetString(idx)
        if s:
            self.context(f"window open {s}\n")

    def on_button(self, event):
        for s in self.window_list:
            self.context(f"window open {s}\n")

    def pane_show(self, *args):
        return

    def pane_hide(self, *args):
        return


class DebugRasterPlotterPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)

        self.context = context
        self.context.themes.set_window_colors(self)

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        info = StaticBoxSizer(
            self, wx.ID_ANY, _("Raster Plotter Test Info"), wx.HORIZONTAL
        )
        info.Add(
            wxStaticText(self, wx.ID_ANY, "Dimensions:"), 0, wx.ALIGN_CENTER_VERTICAL, 0
        )
        self.text_x = TextCtrl(self, wx.ID_ANY, "1", check="int")
        self.text_y = TextCtrl(self, wx.ID_ANY, "1", check="int")
        info.Add(self.text_x, 1, wx.EXPAND, 0)
        info.Add(wxStaticText(self, wx.ID_ANY, "x"), 0, wx.ALIGN_CENTER_VERTICAL, 0)
        info.Add(self.text_y, 1, wx.EXPAND, 0)
        info.Add(wxStaticText(self, wx.ID_ANY, "pixel"), 0, wx.ALIGN_CENTER_VERTICAL, 0)
        # raster properties
        raster_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Raster Properties"), wx.VERTICAL
        )
        raster_type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        raster_sizer.Add(raster_type_sizer, 0, wx.EXPAND, 0)
        self.raster_terms = [
            (RASTER_T2B, "Top To Bottom"),
            (RASTER_B2T, "Bottom To Top"),
            (RASTER_R2L, "Right To Left"),
            (RASTER_L2R, "Left To Right"),
            (RASTER_HATCH, "Crosshatch"),
            (RASTER_GREEDY_H, "Greedy horizontal"),
            (RASTER_GREEDY_V, "Greedy vertical"),
            (RASTER_CROSSOVER, "Crossover"),
            (RASTER_SPIRAL, "Spiral"),
        ]
        # Look for registered raster (image) preprocessors,
        # these are routines that take one image as parameter
        # and deliver a set of (result image, method (aka raster_direction) )
        # that will be dealt with independently
        # The registered datastructure is (rasterid, description, method)
        self.raster_terms.extend(
            (key, description)
            for key, description, method in self.context.kernel.lookup_all(
                "raster_preprocessor/.*"
            )
        )
        # Add a couple of testcases
        # test_methods = (
        #     (-1, "Test: Horizontal Rectangle"),
        #     (-2, "Test: Vertical Rectangle"),
        #     (-3, "Test: Horizontal Snake"),
        #     (-4, "Test: Vertical Snake"),
        #     (-5,  "Test: Spiral"),
        # )
        # self.raster_terms.extend(test_methods)

        self.raster_methods = [key for key, info in self.raster_terms]

        self.combo_raster_direction = wxComboBox(
            self,
            wx.ID_ANY,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        raster_type_sizer.Add(
            wxStaticText(self, wx.ID_ANY, "Raster Direction:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
            0,
        )
        self.combo_raster_direction.AppendItems(
            [info for key, info in self.raster_terms]
        )
        raster_type_sizer.Add(
            self.combo_raster_direction, 1, wx.ALIGN_CENTER_VERTICAL, 0
        )
        self.check_raster_bidirectional = wxCheckBox(self, wx.ID_ANY, "Bidirectional")

        raster_type_sizer.Add(
            self.check_raster_bidirectional, 0, wx.ALIGN_CENTER_VERTICAL, 0
        )
        self.combo_raster_direction.SetSelection(0)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_test_onepixel_black = wxButton(self, wx.ID_ANY, "Fully Black")
        self.btn_test_onepixel_white = wxButton(self, wx.ID_ANY, "Fully White")
        buttons.Add(self.btn_test_onepixel_black, 1, wx.EXPAND, 0)
        buttons.Add(self.btn_test_onepixel_white, 1, wx.EXPAND, 0)
        self.text_result = TextCtrl(
            self, wx.ID_ANY, style=wx.TE_MULTILINE | wx.TE_READONLY
        )

        sizer_main.Add(info, 0, wx.EXPAND, 0)
        sizer_main.Add(raster_sizer, 0, wx.EXPAND, 0)
        sizer_main.Add(buttons, 0, wx.EXPAND, 0)
        sizer_main.Add(self.text_result, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()

        self.btn_test_onepixel_black.Bind(wx.EVT_BUTTON, self.test_empty_image)
        self.btn_test_onepixel_white.Bind(wx.EVT_BUTTON, self.test_fully_covered_image)

    def test_empty_image(self, event):
        """
        Tests the speed of rasterplotter for a fully black image.
        """
        import numpy as np
        from PIL import Image, ImageDraw

        from meerk40t.tools.rasterplotter import RasterPlotter

        try:
            x = int(self.text_x.GetValue())
            y = int(self.text_y.GetValue())
        except ValueError:
            self.text_result.SetValue("Invalid dimensions. Please enter integers.")
            return
        raster_string = self.combo_raster_direction.GetStringSelection()
        raster_direction = -1
        for key, info in self.raster_terms:
            if raster_string == info:
                raster_direction = key
                break
        if raster_direction < 0:
            self.text_result.SetValue("Invalid raster direction selected.")
            return
        bidir = self.check_raster_bidirectional.GetValue()

        # Notabene: a black pixel is a non-burnt one, so we invert the logic here
        image = Image.new("RGBA", (x, y), "white")
        image = image.convert("L")
        plotter = RasterPlotter(
            image.load(), x, y, direction=raster_direction, bidirectional=bidir
        )
        t = time.time()
        i = 0
        res = []
        pixels = 0
        last_x, last_y = plotter.initial_position_in_scene()
        for x, y, on in plotter.plot():
            i += 1
            if on:
                pixels += (abs(x - last_x) + 1) * (abs(y - last_y) + 1)
            res.append(f"{i}: ({x}, {y}) {'on' if on else 'off'}")
            last_x, last_y = x, y
        ipos = plotter.initial_position_in_scene()
        lpos = plotter.final_position_in_scene()
        res.insert(
            0,
            f"Black found: {pixels} pixels: ranging from ({ipos[0]}, {ipos[1]}) to ({lpos[0]}, {lpos[1]})",
        )
        res.append(f"Time taken to finish process {time.time() - t:.3f}s\n")
        self.text_result.SetValue("\n".join(res))

    def test_fully_covered_image(self, event):
        """
        Tests the speed of rasterplotter for a fully black image.
        """
        import numpy as np
        from PIL import Image, ImageDraw

        from meerk40t.tools.rasterplotter import RasterPlotter

        try:
            x = int(self.text_x.GetValue())
            y = int(self.text_y.GetValue())
        except ValueError:
            self.text_result.SetValue("Invalid dimensions. Please enter integers.")
            return
        if self.combo_raster_direction.GetSelection() < 0:
            self.text_result.SetValue("Please select a raster direction.")
            return
        raster_string = self.combo_raster_direction.GetStringSelection()
        raster_direction = -1
        for key, info in self.raster_terms:
            if raster_string == info:
                raster_direction = key
                break
        if raster_direction < 0:
            self.text_result.SetValue("Invalid raster direction selected.")
            return
        bidir = self.check_raster_bidirectional.GetValue()

        # Notabene: a black pixel is a non-burnt one, so we invert the logic here
        image = Image.new("RGBA", (x, y), "black")
        image = image.convert("L")

        plotter = RasterPlotter(
            image.load(), x, y, direction=raster_direction, bidirectional=bidir
        )
        t = time.time()
        i = 0
        res = []
        pixels = 0
        ipos = plotter.initial_position_in_scene()
        lpos = plotter.final_position_in_scene()
        last_x, last_y = ipos
        for x, y, on in plotter.plot():
            i += 1
            if on:
                pixels += (abs(x - last_x) + 1) * (abs(y - last_y) + 1)
            res.append(f"{i}: ({x}, {y}) {'on' if on else 'off'}")
            last_x, last_y = x, y
        res.insert(
            0,
            f"White found: {pixels} pixels: ranging from ({ipos[0]}, {ipos[1]}) to ({lpos[0]}, {lpos[1]})",
        )
        res.append(f"Time taken to finish process {time.time() - t:.3f}s\n")
        self.text_result.SetValue("\n".join(res))


class DebugSettingsPanel(wx.Panel):
    """
    Displays information about operation settings
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.info = wx.TreeCtrl(
            self, wx.ID_ANY, style=wx.TR_DEFAULT_STYLE | wx.SUNKEN_BORDER
        )

        self.__set_properties()
        self.__do_layout()

        # end wxGlade

        self._update_position()

    def pane_show(self, *args):
        self.context.listen("emphasized", self._update_position)
        self.context.listen("selected", self._update_position)
        self.context.listen("element_property_update", self._update_position)

    def pane_hide(self, *args):
        self.context.unlisten("emphasized", self._update_position)
        self.context.unlisten("selected", self._update_position)
        self.context.listen("element_property_update", self._update_position)

    def __set_properties(self):
        # begin wxGlade: PositionPanel.__set_properties
        self.info.SetToolTip(_("Operation settings"))
        self.info.SetMinSize((300, 200))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: PositionPanel.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_1 = StaticBoxSizer(self, wx.ID_ANY, _("Operations:"), wx.VERTICAL)
        sizer_1.Add(self.info, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_1, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()
        # end wxGlade

    @dispatch_to_main_thread
    def _update_position(self, *args, **kwargs):
        self.update_position(True)

    def update_position(self, reset):
        def timestr(ts):
            return (
                "---" if ts is None else time.strftime("%H:%M:%S", time.localtime(ts))
            )

        try:
            self.info.DeleteAllItems()
        except RuntimeError:
            return  # Already deleted...
        root = self.info.AddRoot(_("Operation settings"))
        for node in self.context.elements.ops():
            nodeitem = self.info.AppendItem(root, str(node))
            if hasattr(node, "settings"):
                settings = node.settings
                if isinstance(settings, dict):
                    for key, value in settings.items():
                        if isinstance(value, (list, tuple)):
                            value = ", ".join(str(v) for v in value)
                        self.info.AppendItem(nodeitem, f"{key}: {value}", data=value)
                else:
                    self.info.AppendItem(nodeitem, str(settings), data=settings)
        self.info.ExpandAllChildren(root)
