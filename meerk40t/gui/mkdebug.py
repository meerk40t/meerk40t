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
)
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

    def _update_position(self, *args):
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
        for node in self.context.elements.flat(selected=True):
            txt1 += str(node) + "\n"
        data = self.context.elements.flat(emphasized=True)
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

                col:wx.Colour = wx.SystemSettings().GetColour(getattr(wx, prop))
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
                    ms = min(imgs[0], imgs[1]) * self.context.root.bitmap_correction_scale
                    bmp = obj.GetBitmap(resize=ms, force_darkmode=self.context.themes.dark)
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
            self, wx.ID_ANY, mkicons.icon_bell.GetBitmap(resize=mkicons.get_default_icon_size(self.context)/2)
        )
        slider_left = wx.Slider(self, wx.ID_ANY, value=0, minValue=0, maxValue=100)
        static_left = wx.StaticBitmap(
            self, wx.ID_ANY, mkicons.icon_closed_door.GetBitmap(resize=mkicons.get_default_icon_size(self.context))
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
            self, wx.ID_ANY, mkicons.icon_closed_door.GetBitmap(resize=mkicons.get_default_icon_size(self.context))
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
