"""
    This module contains panels that display internal developer information.
    They will become visible if you type 'set debug_mode True' in the
    console and restart the program.
"""
import time

import wx
from wx import aui

import meerk40t.gui.icons as mkicons
from meerk40t.core.units import Angle, Length
from meerk40t.gui.wxutils import ScrolledPanel, StaticBoxSizer
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
    window.on_pane_create(pane)
    context.register("pane/debug_color", pane)


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
    window.on_pane_create(pane)
    context.register("pane/debug_shutdown", pane)


class ShutdownPanel(wx.Panel):
    """
    Tries to create a scenario that has led to multipl runtime errors durign shutdown
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        info = wx.StaticText(
            self,
            wx.ID_ANY,
            (
                "Please be careful, if you click on one of the buttons below, "
                + "we will try to create a scenario that hopefully will help us "
                + "identify an edge case crash.\n"
                + "So please save your work first, as it will be compromised!"
            ),
        )
        self.btn_scenario_kernel_first = wx.Button(self, wx.ID_ANY, "Kill kernel first")
        self.btn_scenario_gui_first = wx.Button(self, wx.ID_ANY, "Kill GUI first")
        self.btn_scenario_only = wx.Button(self, wx.ID_ANY, "Just create the scenario")
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
        self.lb_selected = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE)
        self.lb_emphasized = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE)
        self.txt_first = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)

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

    def _update_position(self, *args):
        self.update_position(True)

    def update_position(self, reset):
        def timestr(ts):
            if ts is None:
                return "---"
            else:
                return time.strftime("%H:%M:%S", time.localtime(ts))

        txt1 = ""
        txt2 = ""
        for node in self.context.elements.flat(selected=True):
            txt1 += str(node) + "\n"
        data = self.context.elements.flat(emphasized=True)
        for node in data:
            txt2 += (
                f"{node.id} - {node.type} {node.label} - {timestr(node._emphasized_time)}"
                + "\n"
            )
        node = self.context.elements.first_emphasized  # (data)
        if node is None:
            txt3 = ""
        else:
            txt3 = f"{node.id} - {node.type} {node.label} - {timestr(node._emphasized_time)}"

        self.lb_selected.SetValue(txt1)
        self.lb_emphasized.SetValue(txt2)

        self.txt_first.SetValue(txt3)


class DebugColorPanel(ScrolledPanel):
    """
    Displays system defined (OS and wxpython) colors to simplify identifying / choosing them
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)
        from copy import copy

        self.context = context

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

                col = wx.SystemSettings().GetColour(getattr(wx, prop))
                infosizer = wx.BoxSizer(wx.VERTICAL)
                box = wx.StaticBitmap(
                    self, wx.ID_ANY, size=wx.Size(32, 32), style=wx.SB_RAISED
                )
                box.SetBackgroundColour(col)
                box.SetToolTip(prop)
                lbl = wx.StaticText(self, wx.ID_ANY, prop[len(pattern) :])
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
            box = wx.StaticBitmap(
                self, wx.ID_ANY, size=wx.Size(32, 32), style=wx.SB_RAISED
            )
            box.SetBackgroundColour(col)
            box.SetToolTip(entry)
            lbl = wx.StaticText(self, wx.ID_ANY, entry)
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
        self.icon = None

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        choose_sizer = wx.BoxSizer(wx.HORIZONTAL)

        lbl = wx.StaticText(self, wx.ID_ANY, "Pick icon")

        self.icon_list = list()
        for entry in dir(mkicons):
            # print (entry)
            if entry.startswith("icon"):
                self.icon_list.append(entry)
        self.combo_icons = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=self.icon_list,
            style=wx.CB_SORT | wx.CB_READONLY | wx.CB_DROPDOWN,
        )
        choose_sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        choose_sizer.Add(self.combo_icons, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_main.Add(choose_sizer, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.icon_show = wx.StaticBitmap(self, wx.ID_ANY)
        sizer_main.Add(self.icon_show, 1, wx.EXPAND, 0)
        sizer_main.Fit(self)
        self.combo_icons.Bind(wx.EVT_COMBOBOX, self.on_combo)
        self.Layout()

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
                    ms = min(imgs[0], imgs[1])
                    bmp = obj.GetBitmap(resize=ms)
                    self.icon_show.SetBitmap(bmp)

    def pane_show(self, *args):
        return

    def pane_hide(self, *args):
        return
