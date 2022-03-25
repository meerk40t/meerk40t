import os
import platform
import sys
from functools import partial

import wx
from PIL import Image
from wx import aui

from meerk40t.core.exceptions import BadFileError
from meerk40t.kernel import lookup_listener, signal_listener


from ..core.units import UNITS_PER_INCH, Length
from ..svgelements import (
    Color,
    Matrix,
    Path,
    SVGImage,
)
from .icons import (
    icon_meerk40t,
    icons8_circle_50,
    icons8_cursor_50,
    icons8_emergency_stop_button_50,
    icons8_flip_vertical,
    icons8_gas_industry_50,
    icons8_home_filled_50,
    icons8_mirror_horizontal,
    icons8_opened_folder_50,
    icons8_oval_50,
    icons8_pause_50,
    icons8_pencil_drawing_50,
    icons8_place_marker_50,
    icons8_polygon_50,
    icons8_polyline_50,
    icons8_rectangular_50,
    icons8_save_50,
    icons8_type_50,
    icons8_union_50,
    icons8_vector_50,
)
from .laserrender import (
    DRAW_MODE_ALPHABLACK,
    DRAW_MODE_ANIMATE,
    DRAW_MODE_BACKGROUND,
    DRAW_MODE_CACHE,
    DRAW_MODE_FILLS,
    DRAW_MODE_FLIPXY,
    DRAW_MODE_GRID,
    DRAW_MODE_GUIDES,
    DRAW_MODE_ICONS,
    DRAW_MODE_IMAGE,
    DRAW_MODE_INVERT,
    DRAW_MODE_LASERPATH,
    DRAW_MODE_LINEWIDTH,
    DRAW_MODE_PATH,
    DRAW_MODE_REFRESH,
    DRAW_MODE_RETICLE,
    DRAW_MODE_SELECTION,
    DRAW_MODE_STROKES,
    DRAW_MODE_TEXT,
    LaserRender,
    swizzlecolor,
)
from .mwindow import MWindow

_ = wx.GetTranslation

ID_MENU_IMPORT = wx.NewId()
ID_MENU_RECENT = wx.NewId()
ID_MENU_ZOOM_OUT = wx.NewId()
ID_MENU_ZOOM_IN = wx.NewId()
ID_MENU_ZOOM_SIZE = wx.NewId()
ID_MENU_ZOOM_BED = wx.NewId()

# 1 fill, 2 grids, 4 guides, 8 laserpath, 16 writer_position, 32 selection
ID_MENU_HIDE_FILLS = wx.NewId()
ID_MENU_HIDE_GUIDES = wx.NewId()
ID_MENU_HIDE_GRID = wx.NewId()
ID_MENU_HIDE_BACKGROUND = wx.NewId()
ID_MENU_HIDE_LINEWIDTH = wx.NewId()
ID_MENU_HIDE_STROKES = wx.NewId()
ID_MENU_HIDE_ICONS = wx.NewId()
ID_MENU_HIDE_LASERPATH = wx.NewId()
ID_MENU_HIDE_RETICLE = wx.NewId()
ID_MENU_HIDE_SELECTION = wx.NewId()
ID_MENU_SCREEN_REFRESH = wx.NewId()
ID_MENU_SCREEN_ANIMATE = wx.NewId()
ID_MENU_SCREEN_INVERT = wx.NewId()
ID_MENU_SCREEN_FLIPXY = wx.NewId()
ID_MENU_PREVENT_CACHING = wx.NewId()
ID_MENU_PREVENT_ALPHABLACK = wx.NewId()
ID_MENU_HIDE_IMAGE = wx.NewId()
ID_MENU_HIDE_PATH = wx.NewId()
ID_MENU_HIDE_TEXT = wx.NewId()

ID_MENU_FILE0 = wx.NewId()
ID_MENU_FILE1 = wx.NewId()
ID_MENU_FILE2 = wx.NewId()
ID_MENU_FILE3 = wx.NewId()
ID_MENU_FILE4 = wx.NewId()
ID_MENU_FILE5 = wx.NewId()
ID_MENU_FILE6 = wx.NewId()
ID_MENU_FILE7 = wx.NewId()
ID_MENU_FILE8 = wx.NewId()
ID_MENU_FILE9 = wx.NewId()
ID_MENU_FILE10 = wx.NewId()
ID_MENU_FILE11 = wx.NewId()
ID_MENU_FILE12 = wx.NewId()
ID_MENU_FILE13 = wx.NewId()
ID_MENU_FILE14 = wx.NewId()
ID_MENU_FILE15 = wx.NewId()
ID_MENU_FILE16 = wx.NewId()
ID_MENU_FILE17 = wx.NewId()
ID_MENU_FILE18 = wx.NewId()
ID_MENU_FILE19 = wx.NewId()
ID_MENU_FILE_CLEAR = wx.NewId()

ID_MENU_KEYMAP = wx.NewId()
ID_MENU_DEVICE_MANAGER = wx.NewId()
ID_MENU_CONFIG = wx.NewId()
ID_MENU_NAVIGATION = wx.NewId()
ID_MENU_NOTES = wx.NewId()
ID_MENU_OPERATIONS = wx.NewId()
ID_MENU_CONTROLLER = wx.NewId()
ID_MENU_CAMERA = wx.NewId()
ID_MENU_CONSOLE = wx.NewId()
ID_MENU_USB = wx.NewId()
ID_MENU_SPOOLER = wx.NewId()
ID_MENU_SIMULATE = wx.NewId()
ID_MENU_RASTER_WIZARD = wx.NewId()
ID_MENU_WINDOW_RESET = wx.NewId()
ID_MENU_PANE_RESET = wx.NewId()
ID_MENU_PANE_LOCK = wx.NewId()
ID_MENU_JOB = wx.NewId()
ID_MENU_TREE = wx.NewId()

ID_BEGINNERS = wx.NewId()
ID_HOMEPAGE = wx.NewId()
ID_RELEASES = wx.NewId()
ID_FACEBOOK = wx.NewId()
ID_DISCORD = wx.NewId()
ID_MAKERS_FORUM = wx.NewId()
ID_IRC = wx.NewId()


class CustomStatusBar(wx.StatusBar):
    """Overloading of Statusbar to allow some checkboxes on it"""

    panelct = 5
    startup = True

    def __init__(self, parent, panelct):
        self.Startup = True
        self.panelct = panelct
        self.context = parent.context
        wx.StatusBar.__init__(self, parent, -1)
        self.SetFieldsCount(self.panelct)
        self.SetStatusStyles([wx.SB_SUNKEN] * self.panelct)
        sizes = [-2] * self.panelct
        # Make the first Panel large
        sizes[0] = -3
        # Make the last Panel smaller
        sizes[self.panelct - 1] = -1
        self.SetStatusWidths(sizes)
        self.sizeChanged = False
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

        # These will fall into the last field
        self.cb_move = wx.CheckBox(self, id=wx.ID_ANY, label=_("Move"))
        self.cb_handle = wx.CheckBox(self, id=wx.ID_ANY, label=_("Resize"))
        self.cb_rotate = wx.CheckBox(self, id=wx.ID_ANY, label=_("Rotate"))
        self.cb_skew = wx.CheckBox(self, id=wx.ID_ANY, label=_("Skew"))
        self.Bind(wx.EVT_CHECKBOX, self.on_toggle_move, self.cb_move)
        self.Bind(wx.EVT_CHECKBOX, self.on_toggle_handle, self.cb_handle)
        self.Bind(wx.EVT_CHECKBOX, self.on_toggle_rotate, self.cb_rotate)
        self.Bind(wx.EVT_CHECKBOX, self.on_toggle_skew, self.cb_skew)
        self.context.setting(bool, "enable_sel_move", True)
        self.context.setting(bool, "enable_sel_size", True)
        self.context.setting(bool, "enable_sel_rotate", True)
        self.context.setting(bool, "enable_sel_skew", False)
        self.cb_move.SetValue(self.context.enable_sel_move)
        self.cb_handle.SetValue(self.context.enable_sel_size)
        self.cb_rotate.SetValue(self.context.enable_sel_rotate)
        self.cb_skew.SetValue(self.context.enable_sel_skew)
        self.cb_enabled = False

        # set the initial position of the checkboxes
        self.Reposition()
        self.startup = False

    @property
    def cb_enabled(self):
        return self._cb_enabled

    @cb_enabled.setter
    def cb_enabled(self, cb_enabled):
        if cb_enabled:
            self.cb_move.Show()
            self.cb_handle.Show()
            self.cb_rotate.Show()
            self.cb_skew.Show()
        else:
            self.cb_move.Hide()
            self.cb_handle.Hide()
            self.cb_rotate.Hide()
            self.cb_skew.Hide()
        self._cb_enabled = cb_enabled

    # the checkbox was clicked
    def on_toggle_move(self, event):
        if not self.startup:
            valu = self.cb_move.GetValue()
            self.context.enable_sel_move = valu
            self.context.signal("refresh_scene", "Scene")

    def on_toggle_handle(self, event):
        if not self.startup:
            valu = self.cb_handle.GetValue()
            self.context.enable_sel_size = valu
            self.context.signal("refresh_scene", "Scene")

    def on_toggle_rotate(self, event):
        if not self.startup:
            valu = self.cb_rotate.GetValue()
            self.context.enable_sel_rotate = valu
            self.context.signal("refresh_scene", "Scene")

    def on_toggle_skew(self, event):
        if not self.startup:
            valu = self.cb_skew.GetValue()
            self.context.enable_sel_skew = valu
            self.context.signal("refresh_scene", "Scene")

    def OnSize(self, evt):
        evt.Skip()
        self.Reposition()  # for normal size events
        self.sizeChanged = True

    def OnIdle(self, evt):
        if self.sizeChanged:
            self.Reposition()

    # reposition the checkboxes
    def Reposition(self):
        rect = self.GetFieldRect(self.panelct - 1)
        wd = rect.width / 4
        rect.x += 1
        rect.y += 1
        rect.width = wd
        self.cb_move.SetRect(rect)
        rect.x += wd
        self.cb_handle.SetRect(rect)
        rect.x += wd
        self.cb_rotate.SetRect(rect)
        rect.x += wd
        self.cb_skew.SetRect(rect)
        self.sizeChanged = False


class MeerK40t(MWindow):
    """MeerK40t main window"""

    def __init__(self, *args, **kwds):
        width, height = wx.DisplaySize()

        super().__init__(int(width * 0.9), int(height * 0.9), *args, **kwds)
        try:
            self.EnableTouchEvents(wx.TOUCH_ZOOM_GESTURE | wx.TOUCH_PAN_GESTURES)
        except AttributeError:
            # Not WX 4.1
            pass

        self.context.gui = self
        self.usb_running = False
        context = self.context
        self.context.setting(bool, "disable_tool_tips", False)
        if self.context.disable_tool_tips:
            wx.ToolTip.Enable(False)

        self.context.register(
            "function/open_property_window_for_node", self.open_property_window_for_node
        )

        self.root_context = context.root
        self.DragAcceptFiles(True)

        self.needs_saving = False
        self.working_file = None

        self.pipe_state = None
        self.previous_position = None
        self.is_paused = False

        self._mgr = aui.AuiManager()
        self._mgr.SetFlags(self._mgr.GetFlags() | aui.AUI_MGR_LIVE_RESIZE)
        self._mgr.Bind(aui.EVT_AUI_PANE_CLOSE, self.on_pane_closed)
        self._mgr.Bind(aui.EVT_AUI_PANE_ACTIVATED, self.on_pane_active)

        # notify AUI which frame to use
        self._mgr.SetManagedWindow(self)

        self.__set_panes()
        self.__set_commands()

        # Menu Bar
        self.main_menubar = wx.MenuBar()
        self.__set_menubars()

        self.main_statusbar = CustomStatusBar(self, 5)
        self.SetStatusBar(self.main_statusbar)
        self.main_statusbar.SetStatusStyles(
            [wx.SB_SUNKEN] * self.main_statusbar.GetFieldsCount()
        )
        self.main_statusbar.SetStatusWidths([-1] * self.main_statusbar.GetFieldsCount())
        self.SetStatusBarPane(0)
        self.main_statusbar.SetStatusText(_("Status..."), 0)
        self.Bind(wx.EVT_MENU_OPEN, self.on_menu_open)
        self.Bind(wx.EVT_MENU_CLOSE, self.on_menu_close)
        self.Bind(wx.EVT_MENU_HIGHLIGHT, self.on_menu_highlight)
        self.DoGiveHelp_called = False
        self.menus_open = 0
        self.top_menu = None  # Needed because event.GetMenu is None for submenu titles

        self.Bind(wx.EVT_DROP_FILES, self.on_drop_file)

        self.__set_properties()
        self.Layout()

        self.__set_titlebar()
        self.__kernel_initialize()

        self.Bind(wx.EVT_SIZE, self.on_size)

        self.CenterOnScreen()

    def open_property_window_for_node(self, node):
        """
        Activate the node in question.

        @param node:
        @return:
        """
        gui = self
        root = self.context.root
        root.open("window/Properties", gui)
        # self.context.kernel.activate_instance(node)
        #
        # if isinstance(
        #     node, (RasterOpNode, ImageOpNode, CutOpNode, EngraveOpNode, DotsOpNode)
        # ):
        #     pass
        #     return
        # if isinstance(node, ConsoleOperation):
        #     root.open("window/ConsoleProperty", gui, node=node)
        # if node is None:
        #     return
        # obj = node.object
        # if obj is None:
        #     return
        # elif isinstance(obj, Path):
        #     root.open("window/PathProperty", gui, node=node)
        # elif isinstance(obj, SVGText):
        #     root.open("window/TextProperty", gui, node=node)
        # elif isinstance(obj, SVGImage):
        #     root.open("window/ImageProperty", gui, node=node)
        # elif isinstance(obj, Group):
        #     root.open("window/GroupProperty", gui, node=node)
        # elif isinstance(obj, SVGElement):
        #     root.open("window/PathProperty", gui, node=node)
        # elif isinstance(obj, CutCode):
        #     root.open("window/Simulation", gui, node=node)

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/project/Open",
            {
                "label": _("Open"),
                "icon": icons8_opened_folder_50,
                "tip": _("Opens new project"),
                "action": lambda e: kernel.console(".dialog_load\n"),
                "priority": -200,
            },
        )
        kernel.register(
            "button/project/Save",
            {
                "label": _("Save"),
                "icon": icons8_save_50,
                "tip": _("Saves a project to disk"),
                "action": lambda e: kernel.console(".dialog_save\n"),
                "priority": -100,
            },
        )
        kernel.register(
            "button/modify/Flip",
            {
                "label": _("Flip Vertical"),
                "icon": icons8_flip_vertical,
                "tip": _("Flip the selected element vertically"),
                "action": lambda v: kernel.elements("scale 1 -1\n"),
            },
        )
        kernel.register(
            "button/modify/Mirror",
            {
                "label": _("Mirror Horizontal"),
                "icon": icons8_mirror_horizontal,
                "tip": _("Mirror the selected element horizontally"),
                "action": lambda v: kernel.elements("scale -1 1\n"),
            },
        )

        kernel.register(
            "button/tools/Scene",
            {
                "label": _("Regular Scene"),
                "icon": icons8_cursor_50,
                "tip": _("Regular selection tool"),
                "action": lambda v: kernel.elements("tool none\n"),
                "toggle": "tool",
            },
        )

        kernel.register(
            "button/tools/Relocate",
            {
                "label": _("Set Position"),
                "icon": icons8_place_marker_50,
                "tip": _("Set position to given location"),
                "action": lambda v: kernel.elements("tool relocate\n"),
                "toggle": "tool",
            },
        )

        kernel.register(
            "button/tools/Draw",
            {
                "label": _("Draw"),
                "icon": icons8_pencil_drawing_50,
                "tip": _(""),
                "action": lambda v: kernel.elements("tool draw\n"),
                "toggle": "tool",
            },
        )

        kernel.register(
            "button/tools/ellipse",
            {
                "label": _("Ellipse"),
                "icon": icons8_oval_50,
                "tip": _(""),
                "action": lambda v: kernel.elements("tool ellipse\n"),
                "toggle": "tool",
            },
        )

        kernel.register(
            "button/tools/circle",
            {
                "label": _("Circle"),
                "icon": icons8_circle_50,
                "tip": _(""),
                "action": lambda v: kernel.elements("tool circle\n"),
                "toggle": "tool",
            },
        )

        kernel.register(
            "button/tools/Polygon",
            {
                "label": _("Polygon"),
                "icon": icons8_polygon_50,
                "tip": _(""),
                "action": lambda v: kernel.elements("tool polygon\n"),
                "toggle": "tool",
            },
        )

        kernel.register(
            "button/tools/Polyline",
            {
                "label": _("Polyline"),
                "icon": icons8_polyline_50,
                "tip": _(""),
                "action": lambda v: kernel.elements("tool polyline\n"),
                "toggle": "tool",
            },
        )

        kernel.register(
            "button/tools/Rectangle",
            {
                "label": _("Rectangle"),
                "icon": icons8_rectangular_50,
                "tip": _(""),
                "action": lambda v: kernel.elements("tool rect\n"),
                "toggle": "tool",
            },
        )

        kernel.register(
            "button/tools/Vector",
            {
                "label": _("Vector"),
                "icon": icons8_vector_50,
                "tip": _(""),
                "action": lambda v: kernel.elements("tool vector\n"),
                "toggle": "tool",
            },
        )

        kernel.register(
            "button/tools/Text",
            {
                "label": _("Text"),
                "icon": icons8_type_50,
                "tip": _(""),
                "action": lambda v: kernel.elements("tool text\n"),
                "toggle": "tool",
            },
        )
        kernel.register(
            "button/geometry/Union",
            {
                "label": _("Union"),
                "icon": icons8_union_50,
                "tip": _("Create a union of the selected elements"),
                "action": lambda v: kernel.elements("element union\n"),
            },
        )
        kernel.register(
            "button/geometry/Difference",
            {
                "label": _("Difference"),
                "icon": icons8_union_50,
                "tip": _("Create a difference of the selected elements"),
                "action": lambda v: kernel.elements("element difference\n"),
            },
        )
        kernel.register(
            "button/geometry/Xor",
            {
                "label": _("Xor"),
                "icon": icons8_union_50,
                "tip": _("Create a xor of the selected elements"),
                "action": lambda v: kernel.elements("element xor\n"),
            },
        )
        kernel.register(
            "button/geometry/Intersection",
            {
                "label": _("Intersection"),
                "icon": icons8_union_50,
                "tip": _("Create a intersection of the selected elements"),
                "action": lambda v: kernel.elements("element intersection\n"),
            },
        )

    def __set_commands(self):
        context = self.context
        gui = self

        @context.console_command("dialog_transform", hidden=True)
        def transform(**kwargs):
            dlg = wx.TextEntryDialog(
                gui,
                _(
                    "Enter SVG Transform Instruction e.g. 'scale(1.49, 1, $x, $y)', rotate, translate, etc..."
                ),
                _("Transform Entry"),
                "",
            )
            dlg.SetValue("")

            if dlg.ShowModal() == wx.ID_OK:
                elements = context.elements

                m = str(dlg.GetValue())
                x, y = self.context.device.current
                m = m.replace("$x", str(x))
                m = m.replace("$y", str(y))
                mx = Matrix(m)
                unit_width = context.device.unit_width
                unit_height = context.device.unit_height
                mx.render(ppi=UNITS_PER_INCH, width=unit_width, height=unit_height)
                if mx.is_identity():
                    dlg.Destroy()
                    dlg = wx.MessageDialog(
                        None,
                        _("The entered command does nothing."),
                        _("Non-Useful Matrix."),
                        wx.OK | wx.ICON_WARNING,
                    )
                    dlg.ShowModal()
                    dlg.Destroy()
                else:
                    for element in elements.elems():
                        try:
                            element *= mx
                            element.node.modified()
                        except AttributeError:
                            pass

        @context.console_command("dialog_flip", hidden=True)
        def flip(**kwargs):
            dlg = wx.TextEntryDialog(
                gui,
                _(
                    "Material must be jigged at 0,0 either home or home offset.\nHow wide is your material (give units: in, mm, cm, px, etc)?"
                ),
                _("Double Side Flip"),
                "",
            )
            dlg.SetValue("")
            if dlg.ShowModal() == wx.ID_OK:
                unit_width = context.device.unit_width
                length = float(Length(dlg.GetValue(), relative_length=unit_width))
                mx = Matrix()
                mx.post_scale(-1.0, 1, length / 2.0, 0)
                for element in context.elements.elems(emphasized=True):
                    try:
                        element *= mx
                        element.node.modified()
                    except AttributeError:
                        pass
            dlg.Destroy()

        @context.console_command("dialog_path", hidden=True)
        def path(**kwargs):
            dlg = wx.TextEntryDialog(gui, _("Enter SVG Path Data"), _("Path Entry"), "")
            dlg.SetValue("")

            if dlg.ShowModal() == wx.ID_OK:
                path = Path(dlg.GetValue())
                path.stroke = "blue"
                p = abs(path)
                context.elements.add_elem(p)
                context.elements.classify([p])
            dlg.Destroy()

        @context.console_command("dialog_fill", hidden=True)
        def fill(**kwargs):
            elements = context.elements
            first_selected = elements.first_element(emphasized=True)
            if first_selected is None:
                return
            data = wx.ColourData()
            if first_selected.fill is not None and first_selected.fill != "none":
                data.SetColour(wx.Colour(swizzlecolor(first_selected.fill)))
            dlg = wx.ColourDialog(gui, data)
            if dlg.ShowModal() == wx.ID_OK:
                data = dlg.GetColourData()
                color = data.GetColour()
                rgb = color.GetRGB()
                color = swizzlecolor(rgb)
                color = Color(color, 1.0)
                for elem in elements.elems(emphasized=True):
                    elem.fill = color
                    elem.node.altered()

        @context.console_command("dialog_stroke", hidden=True)
        def stroke(**kwargs):
            elements = context.elements
            first_selected = elements.first_element(emphasized=True)
            if first_selected is None:
                return
            data = wx.ColourData()
            if first_selected.stroke is not None and first_selected.stroke != "none":
                data.SetColour(wx.Colour(swizzlecolor(first_selected.stroke)))
            dlg = wx.ColourDialog(gui, data)
            if dlg.ShowModal() == wx.ID_OK:
                data = dlg.GetColourData()
                color = data.GetColour()
                rgb = color.GetRGB()
                color = swizzlecolor(rgb)
                color = Color(color, 1.0)
                for elem in elements.elems(emphasized=True):
                    elem.stroke = color
                    elem.node.altered()

        @context.console_command("dialog_gear", hidden=True)
        def gear(**kwargs):
            dlg = wx.TextEntryDialog(gui, _("Enter Forced Gear"), _("Gear Entry"), "")
            dlg.SetValue("")

            if dlg.ShowModal() == wx.ID_OK:
                value = dlg.GetValue()
                if value in ("0", "1", "2", "3", "4"):
                    context._stepping_force = int(value)
                else:
                    context._stepping_force = None
            dlg.Destroy()

        @context.console_argument(
            "message", help=_("Message to display, optional"), default=""
        )
        @context.console_command("interrupt", hidden=True)
        def interrupt(message="", **kwargs):
            if not message:
                message = _("Spooling Interrupted.")

            dlg = wx.MessageDialog(
                None,
                message + "\n\n" + _("Press OK to Continue."),
                _("Interrupt"),
                wx.OK,
            )
            dlg.ShowModal()
            dlg.Destroy()

        @context.console_command("dialog_load", hidden=True)
        def load_dialog(**kwargs):
            # This code should load just specific project files rather than all importable formats.
            files = context.elements.load_types()
            with wx.FileDialog(
                gui, _("Open"), wildcard=files, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                pathname = fileDialog.GetPath()
                gui.clear_and_open(pathname)

        @context.console_command("dialog_import", hidden=True)
        def import_dialog(**kwargs):
            files = context.load_types()
            with wx.FileDialog(
                gui,
                _("Import"),
                wildcard=files,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                pathname = fileDialog.GetPath()
                gui.load(pathname)

        @context.console_command("dialog_save_as", hidden=True)
        def save_dialog(**kwargs):
            files = context.elements.save_types()
            with wx.FileDialog(
                gui,
                _("Save Project"),
                wildcard=files,
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                pathname = fileDialog.GetPath()
                if not pathname.lower().endswith(".svg"):
                    pathname += ".svg"
                context.elements.save(pathname)
                gui.validate_save()
                gui.working_file = pathname
                gui.set_file_as_recently_used(gui.working_file)

        @context.console_command("dialog_save", hidden=True)
        def save_or_save_as(**kwargs):
            if gui.working_file is None:
                context(".dialog_save_as\n")
            else:
                gui.set_file_as_recently_used(gui.working_file)
                gui.validate_save()
                context.save(gui.working_file)

        @context.console_command("dialog_import_egv", hidden=True)
        def egv_in_dialog(**kwargs):
            files = "*.egv"
            with wx.FileDialog(
                gui,
                _("Import EGV"),
                wildcard=files,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                pathname = fileDialog.GetPath()
            if pathname is None:
                return
            with wx.BusyInfo(_("Loading File...")):
                context("egv_import %s\n" % pathname)
                return

        @context.console_command("dialog_export_egv", hidden=True)
        def egv_out_dialog(**kwargs):
            files = "*.egv"
            with wx.FileDialog(
                gui, _("Export EGV"), wildcard=files, style=wx.FD_SAVE
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                pathname = fileDialog.GetPath()
            if pathname is None:
                return
            with wx.BusyInfo(_("Saving File...")):
                context("egv_export %s\n" % pathname)
                return

    def __set_panes(self):
        self.context.setting(bool, "pane_lock", True)

        for register_panel in list(self.context.lookup_all("wxpane")):
            register_panel(self, self.context)

        # AUI Manager Update.
        self._mgr.Update()

        self.default_perspective = self._mgr.SavePerspective()
        self.context.setting(str, "perspective")
        if self.context.perspective is not None:
            self._mgr.LoadPerspective(self.context.perspective)

        self.on_config_panes()
        self.__console_commands()

    def __console_commands(self):
        context = self.context

        @context.console_command(
            "pane",
            help=_("control various panes for main window"),
            output_type="panes",
        )
        def panes(**kwargs):
            return "panes", self

        @context.console_argument("pane", help=_("pane to be shown"))
        @context.console_command(
            "show",
            input_type="panes",
            help=_("show the pane"),
            all_arguments_required=True,
        )
        def show_pane(command, _, channel, pane=None, **kwargs):
            _pane = context.lookup("pane", pane)
            if _pane is None:
                channel(_("Pane not found."))
                return
            _pane.Show()
            self._mgr.Update()

        @context.console_argument("pane", help=_("pane to be hidden"))
        @context.console_command(
            "hide",
            input_type="panes",
            help=_("show the pane"),
            all_arguments_required=True,
        )
        def hide_pane(command, _, channel, pane=None, **kwargs):
            _pane = context.lookup("pane", pane)
            if _pane is None:
                channel(_("Pane not found."))
                return
            _pane.Hide()
            self._mgr.Update()

        @context.console_option("always", "a", type=bool, action="store_true")
        @context.console_argument("pane", help=_("pane to be shown"))
        @context.console_command(
            "float",
            input_type="panes",
            help=_("show the pane"),
            all_arguments_required=True,
        )
        def float_pane(command, _, channel, always=False, pane=None, **kwargs):
            _pane = context.lookup("pane", pane)
            if _pane is None:
                channel(_("Pane not found."))
                return
            _pane.Float()
            _pane.Show()
            _pane.Dockable(not always)
            self._mgr.Update()

        @context.console_command(
            "reset",
            input_type="panes",
            help=_("reset all panes restoring the default perspective"),
        )
        def reset_pane(command, _, channel, **kwargs):
            self.on_pane_reset(None)

        @context.console_command(
            "lock",
            input_type="panes",
            help=_("lock the panes"),
        )
        def lock_pane(command, _, channel, **kwargs):
            self.on_pane_lock(None, lock=True)

        @context.console_command(
            "unlock",
            input_type="panes",
            help=_("unlock the panes"),
        )
        def unlock_pane(command, _, channel, **kwargs):
            self.on_pane_lock(None, lock=False)

        @context.console_argument("pane", help=_("pane to create"))
        @context.console_command(
            "create",
            input_type="panes",
            help=_("create a floating about pane"),
        )
        def create_pane(command, _, channel, pane=None, **kwargs):
            if pane == "about":
                from .about import AboutPanel as CreatePanel

                caption = _("About")
                width = 646
                height = 519
            elif pane == "preferences":
                from .preferences import PreferencesPanel as CreatePanel

                caption = _("Preferences")
                width = 565
                height = 327
            else:
                channel(_("Pane not found."))
                return
            panel = CreatePanel(self, context=context)
            _pane = (
                aui.AuiPaneInfo()
                .Dockable(False)
                .Float()
                .Caption(caption)
                .FloatingSize(width, height)
                .Name(pane)
                .CaptionVisible(True)
            )
            _pane.control = panel
            self.on_pane_add(_pane)
            if hasattr(panel, "pane_show"):
                panel.pane_show()
            self.context.register("pane/about", _pane)
            self._mgr.Update()

    def on_pane_reset(self, event=None):
        for pane in self._mgr.GetAllPanes():
            if pane.IsShown():
                window = pane.window
                if hasattr(window, "pane_hide"):
                    window.pane_hide()
                if isinstance(window, wx.aui.AuiNotebook):
                    for i in range(window.GetPageCount()):
                        page = window.GetPage(i)
                        if hasattr(page, "pane_hide"):
                            page.pane_hide()
        self._mgr.LoadPerspective(self.default_perspective, update=True)
        self.on_config_panes()

    def on_config_panes(self):
        for pane in self._mgr.GetAllPanes():
            window = pane.window
            if pane.IsShown():
                if hasattr(window, "pane_show"):
                    window.pane_show()
                if isinstance(window, wx.aui.AuiNotebook):
                    for i in range(window.GetPageCount()):
                        page = window.GetPage(i)
                        if hasattr(page, "pane_show"):
                            page.pane_show()
            else:
                if hasattr(window, "pane_noshow"):
                    window.pane_noshow()
                if isinstance(window, wx.aui.AuiNotebook):
                    for i in range(window.GetPageCount()):
                        page = window.GetPage(i)
                        if hasattr(page, "pane_noshow"):
                            page.pane_noshow()
        self.on_pane_lock(lock=self.context.pane_lock)
        wx.CallAfter(self.on_pane_changed, None)

    def on_pane_lock(self, event=None, lock=None):
        if lock is None:
            self.context.pane_lock = not self.context.pane_lock
        else:
            self.context.pane_lock = lock
        for pane in self._mgr.GetAllPanes():
            if pane.IsShown():
                pane.CaptionVisible(not self.context.pane_lock)
                if hasattr(pane.window, "lock"):
                    pane.window.lock()
        self._mgr.Update()

    def on_pane_add(self, paneinfo: aui.AuiPaneInfo):
        pane = self._mgr.GetPane(paneinfo.name)
        control = paneinfo.control
        if isinstance(control, wx.aui.AuiNotebook):
            for i in range(control.GetPageCount()):
                page = control.GetPage(i)
                self.add_module_delegate(page)
        else:
            self.add_module_delegate(control)
        if len(pane.name):
            if not pane.IsShown():
                pane.Show()
                pane.CaptionVisible(not self.context.pane_lock)
                if hasattr(pane.window, "pane_show"):
                    pane.window.pane_show()
                    wx.CallAfter(self.on_pane_changed, None)
                self._mgr.Update()
            return
        self._mgr.AddPane(
            control,
            paneinfo,
        )

    def on_pane_active(self, event):
        pane = event.GetPane()
        if hasattr(pane.window, "active"):
            pane.window.active()

    def on_pane_closed(self, event):
        pane = event.GetPane()
        if pane.IsShown():
            if hasattr(pane.window, "pane_hide"):
                pane.window.pane_hide()
        wx.CallAfter(self.on_pane_changed, None)

    def on_pane_changed(self, *args):
        for pane in self._mgr.GetAllPanes():
            try:
                shown = pane.IsShown()
                check = pane.window.check
                check(shown)
            except AttributeError:
                pass

    @property
    def is_dark(self):
        return wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127

    def __kernel_initialize(self):
        context = self.context
        context.setting(int, "draw_mode", 0)
        context.setting(bool, "print_shutdown", False)

        @context.console_command(
            "theme", help=_("Theming information and assignments"), hidden=True
        )
        def theme(command, channel, _, **kwargs):
            channel(str(wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)))

        context.setting(str, "file0", None)
        context.setting(str, "file1", None)
        context.setting(str, "file2", None)
        context.setting(str, "file3", None)
        context.setting(str, "file4", None)
        context.setting(str, "file5", None)
        context.setting(str, "file6", None)
        context.setting(str, "file7", None)
        context.setting(str, "file8", None)
        context.setting(str, "file9", None)
        context.setting(str, "file10", None)
        context.setting(str, "file11", None)
        context.setting(str, "file12", None)
        context.setting(str, "file13", None)
        context.setting(str, "file14", None)
        context.setting(str, "file15", None)
        context.setting(str, "file16", None)
        context.setting(str, "file17", None)
        context.setting(str, "file18", None)
        context.setting(str, "file19", None)
        self.populate_recent_menu()

    @lookup_listener("pane")
    def dynamic_fill_pane_menu(self, new=None, old=None):
        def toggle_pane(pane_toggle):
            def toggle(event=None):
                pane_obj = self._mgr.GetPane(pane_toggle)
                if pane_obj.IsShown():
                    if hasattr(pane_obj.window, "pane_hide"):
                        pane_obj.window.pane_hide()
                    pane_obj.Hide()
                    self._mgr.Update()
                    return
                pane_init = self.context.lookup("pane", pane_toggle)
                self.on_pane_add(pane_init)

            return toggle

        self.panes_menu = wx.Menu()
        label = _("Panes")
        index = self.main_menubar.FindMenu(label)
        if index != -1:
            self.main_menubar.Replace(index, self.panes_menu, label)
        else:
            self.main_menubar.Append(self.panes_menu, label)
        submenus = {}
        for pane, _path, suffix_path in self.context.find("pane/.*"):
            try:
                suppress = pane.hide_menu
                if suppress:
                    continue
            except AttributeError:
                pass
            submenu = None
            try:
                submenu_name = pane.submenu
                if submenu_name in submenus:
                    submenu = submenus[submenu_name]
                elif submenu_name is not None:
                    submenu = wx.Menu()
                    self.panes_menu.AppendSubMenu(submenu, submenu_name)
                    submenus[submenu_name] = submenu
            except AttributeError:
                pass
            menu_context = submenu if submenu is not None else self.panes_menu
            try:
                pane_name = pane.name
            except AttributeError:
                pane_name = suffix_path

            pane_caption = pane_name[0].upper() + pane_name[1:] + "."
            try:
                pane_caption = pane.caption
            except AttributeError:
                pass
            if not pane_caption:
                pane_caption = pane_name[0].upper() + pane_name[1:] + "."

            id_new = wx.NewId()
            menu_item = menu_context.Append(id_new, pane_caption, "", wx.ITEM_CHECK)
            self.Bind(
                wx.EVT_MENU,
                toggle_pane(pane_name),
                id=id_new,
            )
            pane = self._mgr.GetPane(pane_name)
            try:
                menu_item.Check(pane.IsShown())
                pane.window.check = menu_item.Check
            except AttributeError:
                pass

        self.panes_menu.AppendSeparator()
        item = self.main_menubar.panereset = self.panes_menu.Append(
            ID_MENU_PANE_LOCK, _("Lock Panes"), "", wx.ITEM_CHECK
        )
        item.Check(self.context.pane_lock)
        self.panes_menu.AppendSeparator()
        self.main_menubar.panereset = self.panes_menu.Append(
            ID_MENU_PANE_RESET, _("Reset Panes"), ""
        )

    @lookup_listener("window")
    def dynamic_fill_window_menu(self, new=None, old=None):
        def toggle_window(window):
            def toggle(event=None):
                self.context("window toggle {window}\n".format(window=window))

            return toggle

        label = _("Tools")
        self.window_menu = wx.Menu()
        index = self.main_menubar.FindMenu(label)
        if index != -1:
            self.main_menubar.Replace(index, self.window_menu, label)
        else:
            self.main_menubar.Append(self.window_menu, label)

        submenus = {}
        for window, _path, suffix_path in self.context.find("window/.*"):
            if not window.window_menu(None):
                continue
            submenu = None
            try:
                submenu_name = window.submenu
                if submenu_name in submenus:
                    submenu = submenus[submenu_name]
                elif submenu_name is not None:
                    submenu = wx.Menu()
                    self.window_menu.AppendSubMenu(submenu, submenu_name)
                    submenus[submenu_name] = submenu
            except AttributeError:
                pass
            menu_context = submenu if submenu is not None else self.window_menu
            try:
                name = window.name
            except AttributeError:
                name = suffix_path

            try:
                caption = window.caption
            except AttributeError:
                caption = name[0].upper() + name[1:]

            id_new = wx.NewId()
            menu_context.Append(id_new, caption, "", wx.ITEM_NORMAL)
            self.Bind(
                wx.EVT_MENU,
                toggle_window(suffix_path),
                id=id_new,
            )

        self.window_menu.AppendSeparator()
        self.window_menu.windowreset = self.window_menu.Append(
            ID_MENU_WINDOW_RESET, _("Reset Windows"), ""
        )

        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window reset *\n"),
            id=ID_MENU_WINDOW_RESET,
        )

    def __set_menubars(self):
        self.__set_file_menu()
        self.__set_view_menu()
        self.__set_pane_menu()
        self.__set_tool_menu()
        self.__set_window_menu()
        self.__set_help_menu()
        self.__set_menu_binds()
        self.add_language_menu()
        self.__set_draw_modes()

    def __set_file_menu(self):
        self.file_menu = wx.Menu()
        # ==========
        # FILE MENU
        # ==========

        self.file_menu.Append(
            wx.ID_NEW, _("&New\tCtrl-N"), _("Clear Operations, Elements and Notes")
        )
        self.file_menu.Append(
            wx.ID_OPEN,
            _("&Open Project\tCtrl-O"),
            _("Clear existing elements and notes and open a new file"),
        )
        self.recent_file_menu = wx.Menu()
        self.file_menu.AppendSubMenu(self.recent_file_menu, _("&Recent"))
        self.file_menu.Append(
            ID_MENU_IMPORT,
            _("&Import File"),
            _("Import another file into the same project"),
        )
        self.file_menu.AppendSeparator()
        self.file_menu.Append(
            wx.ID_SAVE,
            _("&Save\tCtrl-S"),
            _("Save the project as an SVG file (overwriting any existing file)"),
        )
        self.file_menu.Append(
            wx.ID_SAVEAS,
            _("Save &As\tCtrl-Shift-S"),
            _("Save the project in a new SVG file"),
        )
        self.file_menu.AppendSeparator()
        if platform.system() == "Darwin":
            self.file_menu.Append(
                wx.ID_CLOSE, _("&Close Window\tCtrl-W"), _("Close Meerk40t")
            )
        self.file_menu.Append(wx.ID_EXIT, _("E&xit"), _("Close Meerk40t"))
        self.main_menubar.Append(self.file_menu, _("File"))

    def __set_view_menu(self):
        # ==========
        # VIEW MENU
        # ==========
        self.view_menu = wx.Menu()

        self.view_menu.Append(
            ID_MENU_ZOOM_OUT, _("Zoom &Out\tCtrl--"), _("Make the scene smaller")
        )
        self.view_menu.Append(
            ID_MENU_ZOOM_IN, _("Zoom &In\tCtrl-+"), _("Make the scene larger")
        )
        self.view_menu.Append(
            ID_MENU_ZOOM_SIZE,
            _("Zoom to &Selected\tCtrl-Shift-B"),
            _("Fill the scene area with the selected elements"),
        )
        self.view_menu.Append(
            ID_MENU_ZOOM_BED, _("Zoom to &Bed\tCtrl-B"), _("View the whole laser bed")
        )
        self.view_menu.AppendSeparator()

        self.view_menu.Append(
            ID_MENU_HIDE_GRID,
            _("Hide Grid"),
            _("Don't show the sizing grid"),
            wx.ITEM_CHECK,
        )
        self.view_menu.Append(
            ID_MENU_HIDE_BACKGROUND,
            _("Hide Background"),
            _("Don't show any background image"),
            wx.ITEM_CHECK,
        )
        self.view_menu.Append(
            ID_MENU_HIDE_GUIDES,
            _("Hide Guides"),
            _("Don't show the measurement guides"),
            wx.ITEM_CHECK,
        )
        self.view_menu.Append(
            ID_MENU_HIDE_PATH,
            _("Hide Shapes"),
            _("Don't show shapes (i.e. Rectangles, Paths etc.)"),
            wx.ITEM_CHECK,
        )
        self.view_menu.Append(
            ID_MENU_HIDE_STROKES,
            _("Hide Strokes"),
            _("Don't show the strokes (i.e. the edges of SVG shapes)"),
            wx.ITEM_CHECK,
        )
        # TODO - this function doesn't work.
        self.view_menu.Append(
            ID_MENU_HIDE_LINEWIDTH,
            _("No Stroke-Width Render"),
            _("Ignore the stroke width when drawing the stroke"),
            wx.ITEM_CHECK,
        )
        self.view_menu.Append(
            ID_MENU_HIDE_FILLS,
            _("Hide Fills"),
            _("Don't show fills (i.e. the fill inside strokes)"),
            wx.ITEM_CHECK,
        )
        self.view_menu.Append(
            ID_MENU_HIDE_IMAGE, _("Hide Images"), _("Don't show images"), wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_HIDE_TEXT,
            _("Hide Text"),
            _("Don't show text elements"),
            wx.ITEM_CHECK,
        )
        self.view_menu.Append(
            ID_MENU_HIDE_LASERPATH,
            _("Hide Laserpath"),
            _("Don't show the path that the laserhead has followed (blue line)"),
            wx.ITEM_CHECK,
        )
        self.view_menu.Append(
            ID_MENU_HIDE_RETICLE,
            _("Hide Reticle"),
            _(
                "Don't show the small read circle showing the current laserhead position"
            ),
            wx.ITEM_CHECK,
        )
        self.view_menu.Append(
            ID_MENU_HIDE_SELECTION,
            _("Hide Selection"),
            _("Don't show the selection boundaries and dimensions"),
            wx.ITEM_CHECK,
        )
        # TODO This menu does not clear existing icons or create icons when it is changed
        self.view_menu.Append(ID_MENU_HIDE_ICONS, _("Hide Icons"), "", wx.ITEM_CHECK)
        self.view_menu.Append(
            ID_MENU_PREVENT_CACHING, _("Do Not Cache Image"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_PREVENT_ALPHABLACK,
            _("Do Not Alpha/Black Images"),
            "",
            wx.ITEM_CHECK,
        )
        self.view_menu.Append(
            ID_MENU_SCREEN_REFRESH, _("Do Not Refresh"), _(""), wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_SCREEN_ANIMATE, _("Do Not Animate"), _(""), wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_SCREEN_INVERT,
            _("Invert"),
            _("Show a negative image of the scene by inverting colours"),
            wx.ITEM_CHECK,
        )
        self.view_menu.Append(
            ID_MENU_SCREEN_FLIPXY,
            _("Flip XY"),
            _("Effectively rotate the scene display by 180 degrees"),
            wx.ITEM_CHECK,
        )

        self.main_menubar.Append(self.view_menu, _("View"))

    def __set_pane_menu(self):
        # ==========
        # PANE MENU
        # ==========
        self.dynamic_fill_pane_menu()

    def __set_tool_menu(self):
        # ==========
        # TOOL MENU
        # ==========

        self.dynamic_fill_window_menu()

    def __set_window_menu(self):
        # ==========
        # OSX-ONLY WINDOW MENU
        # ==========
        if platform.system() == "Darwin":
            wt_menu = wx.Menu()
            self.main_menubar.Append(wt_menu, _("Window"))

    def __set_help_menu(self):
        # ==========
        # HELP MENU
        # ==========
        self.help_menu = wx.Menu()

        def launch_help_osx(event=None):
            _resource_path = "help/meerk40t.help"
            if not os.path.exists(_resource_path):
                try:  # pyinstaller internal location
                    # pylint: disable=no-member
                    _resource_path = os.path.join(sys._MEIPASS, "help/meerk40t.help")
                except Exception:
                    pass
            if not os.path.exists(_resource_path):
                try:  # Mac py2app resource
                    _resource_path = os.path.join(
                        os.environ["RESOURCEPATH"], "help/meerk40t.help"
                    )
                except Exception:
                    pass
            if os.path.exists(_resource_path):
                os.system("open %s" % _resource_path)
            else:
                dlg = wx.MessageDialog(
                    None,
                    _('Offline help file ("%s") was not found.') % _resource_path,
                    _("File Not Found"),
                    wx.OK | wx.ICON_WARNING,
                )
                dlg.ShowModal()
                dlg.Destroy()

        if platform.system() == "Darwin":
            self.help_menu.Append(
                wx.ID_HELP, _("&MeerK40t Help"), _("Open the MeerK40t Mac help file")
            )
            self.Bind(wx.EVT_MENU, launch_help_osx, id=wx.ID_HELP)
            ONLINE_HELP = wx.NewId()
            self.help_menu.Append(
                ONLINE_HELP, _("&Online Help"), _("Open the Meerk40t online wiki")
            )
            self.Bind(
                wx.EVT_MENU, lambda e: self.context("webhelp help\n"), id=ONLINE_HELP
            )
        else:
            self.help_menu.Append(
                wx.ID_HELP,
                _("&Help"),
                _("Open the Meerk40t online wiki Beginners page"),
            )
            self.Bind(
                wx.EVT_MENU, lambda e: self.context("webhelp help\n"), id=wx.ID_HELP
            )

        self.help_menu.Append(
            ID_BEGINNERS,
            _("&Beginners' Help"),
            _("Open the Meerk40t online wiki Beginners page"),
        )
        self.help_menu.Append(
            ID_HOMEPAGE, _("&Github"), _("Visit Meerk40t's Github home page")
        )
        self.help_menu.Append(
            ID_RELEASES,
            _("&Releases"),
            _("Check for a new release on Meerk40t's Github releases page"),
        )
        self.help_menu.Append(
            ID_FACEBOOK,
            _("&Facebook"),
            _("Get help from the K40 Meerk40t Facebook group"),
        )
        self.help_menu.Append(
            ID_DISCORD,
            _("&Discord"),
            _("Chat with developers to get help on the Meerk40t Discord server"),
        )
        self.help_menu.Append(
            ID_MAKERS_FORUM,
            _("&Makers Forum"),
            _("Get help from the Meerk40t page on the Makers Forum"),
        )
        self.help_menu.Append(
            ID_IRC,
            _("&IRC"),
            _("Chat with developers to get help on the Meerk40t IRC channel"),
        )
        self.help_menu.AppendSeparator()
        self.help_menu.Append(
            wx.ID_ABOUT,
            _("&About MeerK40t"),
            _(
                "Toggle the About window acknowledging those who contributed to creating Meerk40t"
            ),
        )

        self.main_menubar.Append(self.help_menu, _("Help"))

        self.SetMenuBar(self.main_menubar)

    def __set_menu_binds(self):
        self.__set_file_menu_binds()
        self.__set_view_menu_binds()
        self.__set_panes_menu_binds()
        self.__set_help_menu_binds()

    def __set_file_menu_binds(self):
        # ==========
        # BINDS
        # ==========
        self.Bind(wx.EVT_MENU, self.on_click_new, id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self.on_click_open, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.on_click_import, id=ID_MENU_IMPORT)
        self.Bind(wx.EVT_MENU, self.on_click_save, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.on_click_save_as, id=wx.ID_SAVEAS)

        self.Bind(wx.EVT_MENU, self.on_click_close, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_MENU, self.on_click_exit, id=wx.ID_EXIT)

    def __set_view_menu_binds(self):
        self.Bind(wx.EVT_MENU, self.on_click_zoom_out, id=ID_MENU_ZOOM_OUT)
        self.Bind(wx.EVT_MENU, self.on_click_zoom_in, id=ID_MENU_ZOOM_IN)
        self.Bind(wx.EVT_MENU, self.on_click_zoom_selected, id=ID_MENU_ZOOM_SIZE)
        self.Bind(wx.EVT_MENU, self.on_click_zoom_bed, id=ID_MENU_ZOOM_BED)

        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_GRID), id=ID_MENU_HIDE_GRID
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_BACKGROUND),
            id=ID_MENU_HIDE_BACKGROUND,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_LINEWIDTH),
            id=ID_MENU_HIDE_LINEWIDTH,
        )
        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_GUIDES), id=ID_MENU_HIDE_GUIDES
        )
        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_PATH), id=ID_MENU_HIDE_PATH
        )
        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_IMAGE), id=ID_MENU_HIDE_IMAGE
        )
        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_TEXT), id=ID_MENU_HIDE_TEXT
        )
        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_FILLS), id=ID_MENU_HIDE_FILLS
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_LASERPATH),
            id=ID_MENU_HIDE_LASERPATH,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_RETICLE),
            id=ID_MENU_HIDE_RETICLE,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_SELECTION),
            id=ID_MENU_HIDE_SELECTION,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_STROKES),
            id=ID_MENU_HIDE_STROKES,
        )
        self.Bind(
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_ICONS), id=ID_MENU_HIDE_ICONS
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_CACHE),
            id=ID_MENU_PREVENT_CACHING,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_ALPHABLACK),
            id=ID_MENU_PREVENT_ALPHABLACK,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_REFRESH),
            id=ID_MENU_SCREEN_REFRESH,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_ANIMATE),
            id=ID_MENU_SCREEN_ANIMATE,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_INVERT),
            id=ID_MENU_SCREEN_INVERT,
        )
        self.Bind(
            wx.EVT_MENU,
            self.toggle_draw_mode(DRAW_MODE_FLIPXY),
            id=ID_MENU_SCREEN_FLIPXY,
        )

    def __set_panes_menu_binds(self):
        self.Bind(
            wx.EVT_MENU,
            self.on_pane_reset,
            id=ID_MENU_PANE_RESET,
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_pane_lock,
            id=ID_MENU_PANE_LOCK,
        )

    def __set_help_menu_binds(self):
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp beginners\n"),
            id=ID_BEGINNERS,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp main\n"),
            id=ID_HOMEPAGE,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp releases\n"),
            id=ID_RELEASES,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp makers\n"),
            id=ID_MAKERS_FORUM,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp facebook\n"),
            id=ID_FACEBOOK,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp discord\n"),
            id=ID_DISCORD,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp irc\n"),
            id=ID_IRC,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle About\n"),
            id=wx.ID_ABOUT,
        )

    def __set_draw_modes(self):
        self.context.setting(int, "draw_mode", 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_FILLS)
        m.Check(self.context.draw_mode & DRAW_MODE_FILLS != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_GUIDES)
        m.Check(self.context.draw_mode & DRAW_MODE_GUIDES != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_BACKGROUND)
        m.Check(self.context.draw_mode & DRAW_MODE_BACKGROUND != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_LINEWIDTH)
        m.Check(self.context.draw_mode & DRAW_MODE_LINEWIDTH != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_GRID)
        m.Check(self.context.draw_mode & DRAW_MODE_GRID != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_LASERPATH)
        m.Check(self.context.draw_mode & DRAW_MODE_LASERPATH != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_RETICLE)
        m.Check(self.context.draw_mode & DRAW_MODE_RETICLE != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_SELECTION)
        m.Check(self.context.draw_mode & DRAW_MODE_SELECTION != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_STROKES)
        m.Check(self.context.draw_mode & DRAW_MODE_STROKES != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_ICONS)
        m.Check(self.context.draw_mode & DRAW_MODE_ICONS != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_PREVENT_CACHING)
        m.Check(self.context.draw_mode & DRAW_MODE_CACHE != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_PREVENT_ALPHABLACK)
        m.Check(self.context.draw_mode & DRAW_MODE_ALPHABLACK != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_SCREEN_REFRESH)
        m.Check(self.context.draw_mode & DRAW_MODE_REFRESH != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_SCREEN_ANIMATE)
        m.Check(self.context.draw_mode & DRAW_MODE_ANIMATE != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_PATH)
        m.Check(self.context.draw_mode & DRAW_MODE_PATH != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_IMAGE)
        m.Check(self.context.draw_mode & DRAW_MODE_IMAGE != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_TEXT)
        m.Check(self.context.draw_mode & DRAW_MODE_TEXT != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_SCREEN_FLIPXY)
        m.Check(self.context.draw_mode & DRAW_MODE_FLIPXY != 0)
        m = self.GetMenuBar().FindItemById(ID_MENU_SCREEN_INVERT)
        m.Check(self.context.draw_mode & DRAW_MODE_INVERT != 0)

    def add_language_menu(self):
        tl = wx.FileTranslationsLoader()
        trans = tl.GetAvailableTranslations("meerk40t")

        if trans:
            wxglade_tmp_menu = wx.Menu()
            i = 0
            for lang in self.context.app.supported_languages:
                language_code, language_name, language_index = lang
                m = wxglade_tmp_menu.Append(
                    wx.ID_ANY, language_name, language_name, wx.ITEM_RADIO
                )
                if i == self.context.language:
                    m.Check(True)

                def language_update(q):
                    return lambda e: self.context.app.update_language(q)

                self.Bind(wx.EVT_MENU, language_update(i), id=m.GetId())
                if language_code not in trans and i != 0:
                    m.Enable(False)
                i += 1
            self.main_menubar.Append(wxglade_tmp_menu, _("Languages"))

    @signal_listener("device;renamed")
    @lookup_listener("service/device/active")
    def on_active_change(self, *args):
        self.__set_titlebar()

    def window_close_veto(self):
        if self.usb_running:
            message = _("The device is actively sending data. Really quit?")
            answer = wx.MessageBox(
                message, _("Currently Sending Data..."), wx.YES_NO | wx.CANCEL, None
            )
            if answer != wx.YES:
                return True  # VETO
        if self.needs_saving:
            message = _(
                "Save changes to project before closing?\n\n"
                "Your changes will be lost if you do not save them."
            )
            answer = wx.MessageBox(
                message, _("Save Project..."), wx.YES_NO | wx.CANCEL, None
            )
            if answer == wx.YES:
                self.context("dialog_save\n")
            if answer == wx.CANCEL:
                return True  # VETO
        return False

    def window_close(self):
        context = self.context

        context.perspective = self._mgr.SavePerspective()
        for pane in self._mgr.GetAllPanes():
            if pane.IsShown():
                if hasattr(pane.window, "pane_hide"):
                    pane.window.pane_hide()
        self._mgr.UnInit()

        if context.print_shutdown:
            context.channel("shutdown").watch(print)
        self.context(".timer 0 1 quit\n")

    @signal_listener("altered")
    @signal_listener("modified")
    def on_invalidate_save(self, origin, *args):
        self.needs_saving = True
        app = self.context.app.GetTopWindow()
        if isinstance(app, wx.TopLevelWindow):
            app.OSXSetModified(self.needs_saving)

    def validate_save(self):
        self.needs_saving = False
        app = self.context.app.GetTopWindow()
        if isinstance(app, wx.TopLevelWindow):
            app.OSXSetModified(self.needs_saving)

    @signal_listener("warning")
    def on_warning_signal(self, origin, message, caption, style):
        dlg = wx.MessageDialog(
            None,
            message,
            caption,
            style,
        )
        dlg.ShowModal()
        dlg.Destroy()

    @signal_listener("device;noactive")
    def on_device_noactive(self, origin, value):
        dlg = wx.MessageDialog(
            None,
            _("No active device existed. Add a primary device."),
            _("Active Device"),
            wx.OK | wx.ICON_WARNING,
        )
        dlg.ShowModal()
        dlg.Destroy()

    @signal_listener("pipe;failing")
    def on_usb_error(self, origin, value):
        if value == 5:
            self.context.signal("controller", origin)
            dlg = wx.MessageDialog(
                None,
                _("All attempts to connect to USB have failed."),
                _("Usb Connection Problem."),
                wx.OK | wx.ICON_WARNING,
            )
            dlg.ShowModal()
            dlg.Destroy()

    @signal_listener("cutplanning;failed")
    def on_usb_error(self, origin, error):
        dlg = wx.MessageDialog(
            None,
            _("Cut planning failed because: {error}".format(error=error)),
            _("Cut Planning Failed"),
            wx.OK | wx.ICON_WARNING,
        )
        dlg.ShowModal()
        dlg.Destroy()

    @signal_listener("pipe;running")
    def on_usb_running(self, origin, value):
        self.usb_running = value

    @signal_listener("pipe;usb_status")
    def on_usb_state_text(self, origin, value):
        self.main_statusbar.SetStatusText(
            _("Usb: %s") % value,
            1,
        )

    @signal_listener("pipe;thread")
    def on_pipe_state(self, origin, state):
        if state == self.pipe_state:
            return
        self.pipe_state = state

        self.main_statusbar.SetStatusText(
            _("Controller: %s") % self.context.kernel.get_text_thread_state(state),
            2,
        )

    @signal_listener("spooler;thread")
    def on_spooler_state(self, origin, value):
        self.main_statusbar.SetStatusText(
            _("Spooler: %s") % self.context.get_text_thread_state(value),
            3,
        )

    @signal_listener("export-image")
    def on_export_signal(self, origin, frame):
        image_width, image_height, frame = frame
        if frame is not None:
            elements = self.context.elements
            img = Image.fromarray(frame)
            obj = SVGImage()
            obj.image = img
            obj.image_width = image_width
            obj.image_height = image_height
            elements.add_elem(obj)

    @signal_listener("statusmsg")
    def on_update_statusmsg(self, origin, value):
        self.main_statusbar.SetStatusText(value, 0)

    @signal_listener("emphasized")
    def on_update_selwidget(self, origin, *args):
        elements = self.context.elements
        valu = elements.has_emphasis()
        self.main_statusbar.cb_enabled = valu

    def __set_titlebar(self):
        device_name = ""
        device_version = ""
        title = _("%s v%s") % (
            str(self.context.kernel.name),
            self.context.kernel.version,
        )
        title += "      %s" % self.context.device.label
        self.SetTitle(title)

    def __set_properties(self):
        # begin wxGlade: MeerK40t.__set_properties
        self.__set_titlebar()
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_meerk40t.GetBitmap())
        self.SetIcon(_icon)

    def load_or_open(self, filename):
        """
        Loads recent file name given. If the filename cannot be opened attempts open dialog at last known location.
        """
        if os.path.exists(filename):
            try:
                self.load(filename)
            except PermissionError:
                self.tryopen(filename)
        else:
            self.tryopen(filename)

    def tryopen(self, filename):
        """
        Loads an open dialog at given filename to load data.
        """
        files = self.context.elements.load_types()
        default_file = os.path.basename(filename)
        default_dir = os.path.dirname(filename)

        with wx.FileDialog(
            self,
            _("Open"),
            defaultDir=default_dir,
            defaultFile=default_file,
            wildcard=files,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fileDialog:
            fileDialog.SetFilename(default_file)
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind
            pathname = fileDialog.GetPath()
            self.load(pathname)

    def populate_recent_menu(self):
        if not hasattr(self, "recent_file_menu"):
            return  # No menu, cannot populate.

        context = self.context
        recents = [
            (context.file0, ID_MENU_FILE0, "&1 "),
            (context.file1, ID_MENU_FILE1, "&2 "),
            (context.file2, ID_MENU_FILE2, "&3 "),
            (context.file3, ID_MENU_FILE3, "&4 "),
            (context.file4, ID_MENU_FILE4, "&5 "),
            (context.file5, ID_MENU_FILE5, "&6 "),
            (context.file6, ID_MENU_FILE6, "&7 "),
            (context.file7, ID_MENU_FILE7, "&8 "),
            (context.file8, ID_MENU_FILE8, "&9 "),
            (context.file9, ID_MENU_FILE9, "1&0"),
            (context.file10, ID_MENU_FILE10, "11"),
            (context.file11, ID_MENU_FILE11, "12"),
            (context.file12, ID_MENU_FILE12, "13"),
            (context.file13, ID_MENU_FILE13, "14"),
            (context.file14, ID_MENU_FILE14, "15"),
            (context.file15, ID_MENU_FILE15, "16"),
            (context.file16, ID_MENU_FILE16, "17"),
            (context.file17, ID_MENU_FILE17, "18"),
            (context.file18, ID_MENU_FILE18, "19"),
            (context.file19, ID_MENU_FILE19, "20"),
        ]

        # for i in range(self.recent_file_menu.MenuItemCount):
        # self.recent_file_menu.Remove(self.recent_file_menu.FindItemByPosition(0))

        for item in self.recent_file_menu.GetMenuItems():
            self.recent_file_menu.Remove(item)

        for file, id, shortcode in recents:
            if file is not None and file:
                shortfile = _("Load {file}...").format(file=os.path.basename(file))
                self.recent_file_menu.Append(id, shortcode + "  " + file, shortfile)
                self.Bind(
                    wx.EVT_MENU,
                    partial(lambda f, event: self.load_or_open(f), file),
                    id=id,
                )

        if self.recent_file_menu.MenuItemCount != 0:
            self.recent_file_menu.AppendSeparator()
            self.recent_file_menu.Append(
                ID_MENU_FILE_CLEAR,
                _("Clear Recent"),
                _("Delete the list of recent projects"),
            )
            self.Bind(wx.EVT_MENU, lambda e: self.clear_recent(), id=ID_MENU_FILE_CLEAR)

    def clear_recent(self):
        for i in range(20):
            try:
                setattr(self.context, "file" + str(i), "")
            except IndexError:
                break
        self.populate_recent_menu()

    def set_file_as_recently_used(self, pathname):
        recent = list()
        for i in range(20):
            recent.append(getattr(self.context, "file" + str(i)))
        recent = [r for r in recent if r is not None and r != pathname and len(r) > 0]
        recent.insert(0, pathname)
        for i in range(20):
            try:
                setattr(self.context, "file" + str(i), recent[i])
            except IndexError:
                break
        self.populate_recent_menu()

    def clear_project(self):
        context = self.context
        self.working_file = None
        self.validate_save()
        context.elements.clear_all()
        self.context(".laserpath_clear\n")

    def clear_and_open(self, pathname):
        self.clear_project()
        if self.load(pathname):
            try:
                if self.context.uniform_svg and pathname.lower().endswith("svg"):
                    # or (len(elements) > 0 and "meerK40t" in elements[0].values):
                    # TODO: Disabled uniform_svg, no longer detecting namespace.
                    self.working_file = pathname
                    self.validate_save()
            except AttributeError:
                pass

    def load(self, pathname):
        try:
            try:
                # wxPython 4.1.+
                with wx.BusyInfo(
                    wx.BusyInfoFlags().Title(_("Loading File...")).Label(pathname)
                ):
                    n = self.context.elements.note
                    results = self.context.elements.load(
                        pathname,
                        channel=self.context.channel("load"),
                        svg_ppi=self.context.elements.svg_ppi,
                    )
            except AttributeError:
                # wxPython 4.0
                with wx.BusyInfo(_("Loading File...")):
                    n = self.context.elements.note
                    results = self.context.elements.load(
                        pathname,
                        channel=self.context.channel("load"),
                        svg_ppi=self.context.elements.svg_ppi,
                    )
        except BadFileError as e:
            dlg = wx.MessageDialog(
                None,
                str(e),
                _("File is Malformed"),
                wx.OK | wx.ICON_WARNING,
            )
            dlg.ShowModal()
            dlg.Destroy()
            return False
        else:
            if results:
                self.context("scene focus -4% -4% 104% 104%\n")
                self.set_file_as_recently_used(pathname)
                if n != self.context.elements.note and self.context.elements.auto_note:
                    self.context("window open Notes\n")  # open/not toggle.
                return True
            return False

    def on_drop_file(self, event):
        """
        Drop file handler

        Accepts multiple files drops.
        """
        accepted = 0
        rejected = 0
        rejected_files = []
        for pathname in event.GetFiles():
            if self.load(pathname):
                accepted += 1
            else:
                rejected += 1
                rejected_files.append(pathname)
        if rejected != 0:
            reject = "\n".join(rejected_files)
            err_msg = _("Some files were unrecognized:\n%s") % reject
            dlg = wx.MessageDialog(
                None, err_msg, _("Error encountered"), wx.OK | wx.ICON_ERROR
            )
            dlg.ShowModal()
            dlg.Destroy()

    def on_size(self, event):
        if self.context is None:
            return
        self.Layout()

    def on_focus_lost(self, event):
        self.context("-laser\nend\n")
        # event.Skip()

    def on_click_new(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        self.clear_project()

    def on_click_open(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        self.context(".dialog_load\n")

    def on_click_import(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        self.context(".dialog_import\n")

    def on_click_stop(self, event=None):
        self.context("estop\n")

    def on_click_pause(self, event=None):
        self.context("pause\n")

    def on_click_save(self, event):
        self.context(".dialog_save\n")

    def on_click_save_as(self, event=None):
        self.context(".dialog_save_as\n")

    def on_click_close(self, event=None):
        try:
            window = self.context.app.GetTopWindow().FindFocus().GetTopLevelParent()
            if window is self:
                return
            window.Close(False)
        except RuntimeError:
            pass

    def on_click_exit(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        try:
            self.Close()
        except RuntimeError:
            pass

    def on_click_zoom_out(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoomout button press
        """
        self.context("scene zoom %f\n" % (1.0 / 1.5))

    def on_click_zoom_in(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoomin button press
        """
        self.context("scene zoom %f\n" % 1.5)

    def on_click_zoom_selected(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoom scene to selected items.
        """
        bbox = self.context.elements.selected_area()
        if bbox is None:
            self.on_click_zoom_bed(event=event)
        else:
            x_delta = (bbox[2] - bbox[0]) * 0.04
            y_delta = (bbox[3] - bbox[1]) * 0.04
            self.context(
                "scene focus %f %f %f %f\n"
                % (
                    bbox[0] - x_delta,
                    bbox[1] - y_delta,
                    bbox[2] + x_delta,
                    bbox[3] + y_delta,
                )
            )

    def on_click_zoom_bed(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoom scene to bed size.
        """
        self.context("scene focus -4% -4% 104% 104%\n")

    def toggle_draw_mode(self, bits):
        """
        Toggle the draw mode.
        :param bits: Bit to toggle.
        :return: Toggle function.
        """

        def toggle(event=None):
            self.context.draw_mode ^= bits
            self.context.signal("draw_mode", self.context.draw_mode)
            self.context.signal("refresh_scene", "Scene")

        return toggle

    def update_statusbar(self, text):
        self.main_statusbar.SetStatusText(text, self.GetStatusBarPane())

    def status_update(self):
        # ToDo Get spool status and make the status dynamic
        self.update_statusbar(_("Idle..."))

    # The standard wx.Frame version of DoGiveHelp is not passed the help text in Windows
    # (no idea about other platforms - wxWidgets code for each platform is different)
    # and has no way of knowing the menuitem and getting the text itself.

    # So we override the standard wx.Frame version and make it do nothing
    # and capture the EVT_MENU_HIGHLIGHT ourselves to process it.
    def DoGiveHelp(self, text, show):
        """Override wx default DoGiveHelp method

        Because we do not call event.Skip() on EVT_MENU_HIGHLIGHT, this should not be called.
        """
        if self.DoGiveHelp_called:
            return
        if text:
            print("DoGiveHelp called with help text:", text)
        else:
            print("DoGiveHelp called but still no help text")
        self.DoGiveHelp_called = True

    def on_menu_open(self, event):
        self.menus_open += 1
        menu = event.GetMenu()
        if menu:
            title = menu.GetTitle()
            if title:
                self.update_statusbar(title + "...")

    def on_menu_close(self, event):
        self.menus_open -= 1
        if self.menus_open <= 0:
            self.top_menu = None
        self.status_update()

    def on_menu_highlight(self, event):
        menuid = event.GetId()
        menu = event.GetMenu()
        if menuid == wx.ID_SEPARATOR:
            self.update_statusbar("...")
            return
        if not self.top_menu and not menu:
            self.status_update()
            return
        if menu and not self.top_menu:
            self.top_menu = menu
        if self.top_menu and not menu:
            menu = self.top_menu
        menuitem, submenu = menu.FindItem(menuid)
        if not menuitem:
            self.update_statusbar("...")
            return
        helptext = menuitem.GetHelp()
        if not helptext:
            helptext = "{m} ({s})".format(
                m=menuitem.GetItemLabelText(),
                s=_("No help text"),
            )
        self.update_statusbar(helptext)
