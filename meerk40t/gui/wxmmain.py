import os
import sys

import wx
from wx import aui

from ..kernel import ConsoleFunction, lookup_listener, signal_listener
from ..svgelements import Color, Length, Matrix, Path, SVGImage
from .icons import (
    icon_meerk40t,
    icons8_emergency_stop_button_50,
    icons8_gas_industry_50,
    icons8_home_filled_50,
    icons8_opened_folder_50,
    icons8_pause_50,
    icons8_save_50,
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
    DRAW_MODE_TREE,
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

# 1 fill, 2 grids, 4 guides, 8 laserpath, 16 writer_position, 32 selection
ID_MENU_HIDE_FILLS = wx.NewId()
ID_MENU_HIDE_GUIDES = wx.NewId()
ID_MENU_HIDE_GRID = wx.NewId()
ID_MENU_HIDE_BACKGROUND = wx.NewId()
ID_MENU_HIDE_LINEWIDTH = wx.NewId()
ID_MENU_HIDE_STROKES = wx.NewId()
ID_MENU_HIDE_ICONS = wx.NewId()
ID_MENU_HIDE_TREE = wx.NewId()
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
ID_MENU_FILE_CLEAR = wx.NewId()

ID_MENU_KEYMAP = wx.NewId()
ID_MENU_DEVICE_MANAGER = wx.NewId()
ID_MENU_CONFIG = wx.NewId()
ID_MENU_ROTARY = wx.NewId()
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
ID_MAKERS_FORUM = wx.NewId()
ID_IRC = wx.NewId()


class MeerK40t(MWindow):
    """
    MeerK40t main window
    """

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

        self.root_context = context.root
        self.DragAcceptFiles(True)

        self.renderer = LaserRender(context)

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
        self.__set_dialogs()

        # Menu Bar
        self.main_menubar = wx.MenuBar()
        self.__set_menubar()

        self.main_statusbar = self.CreateStatusBar(3)

        self.Bind(wx.EVT_DROP_FILES, self.on_drop_file)

        self.__set_properties()
        self.Layout()

        self.__set_titlebar()
        self.__kernel_initialize()

        self.Bind(wx.EVT_SIZE, self.on_size)

        self.CenterOnScreen()

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

    def __set_dialogs(self):
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
                m = m.replace("$x", str(context.device.current_x))
                m = m.replace("$y", str(context.device.current_y))
                mx = Matrix(m)
                wmils = context.device.bedwidth
                hmils = context.device.bedheight
                mx.render(ppi=1000, width=wmils, height=hmils)
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
                wmils = context.device.bedwidth
                # hmils = context.device.bedheight
                length = Length(dlg.GetValue()).value(ppi=1000.0, relative_length=wmils)
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
                gui.load(pathname)

        @context.console_command("dialog_save", hidden=True)
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

        context.register("control/Transform", lambda: context("dialog_transform\n"))
        context.register("control/Flip", lambda: context("dialog_flip\n"))
        context.register("control/Path", lambda: context("dialog_path\n"))
        context.register("control/Fill", lambda: context("dialog_fill\n"))
        context.register("control/Stroke", lambda: context("dialog_stroke\n"))
        context.register("control/FPS", lambda: context("dialog_fps\n"))
        context.register(
            "control/Speedcode-Gear-Force", lambda: context("dialog_gear\n")
        )
        context.register("control/egv export", lambda: context("dialog_import_egv\n"))
        context.register("control/egv import", lambda: context("dialog_export_egv\n"))

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

        context = self.context

        @context.console_command(
            "pane",
            help=_("control various panes for main window"),
            output_type="panes",
        )
        def pane(**kwargs):
            return "panes", self

        @context.console_argument("pane", help=_("pane to be shown"))
        @context.console_command(
            "show",
            input_type="panes",
            help=_("show the pane"),
        )
        def show_pane(command, _, channel, pane=None, **kwargs):
            if pane is None:
                raise SyntaxError
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
        )
        def hide_pane(command, _, channel, pane=None, **kwargs):
            if pane is None:
                raise SyntaxError
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
        )
        def float_pane(command, _, channel, always=False, pane=None, **kwargs):
            if pane is None:
                raise SyntaxError
            _pane = context.lookup("pane", pane)
            if _pane is None:
                channel(_("Pane not found."))
                return
            _pane.Float()
            _pane.Show()
            _pane.Dockable(not always)
            print(_pane.IsDockable())
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
        def lock_pane(command, _, channel, **kwargs):
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

        @context.console_command(
            "rotaryscale", help=_("Rotary Scale selected elements")
        )
        def apply_rotary_scale(*args, **kwargs):
            self.apply_rotary_scale()

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

        for i in range(self.panes_menu.MenuItemCount):
            self.panes_menu.Remove(self.panes_menu.FindItemByPosition(0))

        submenus = {}
        for pane, _path, suffix_path in self.context.find("pane/.*"):
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

        for i in range(self.window_menu.MenuItemCount):
            self.window_menu.Remove(self.window_menu.FindItemByPosition(0))

        submenus = {}
        for window, _path, suffix_path in self.context.find("window/.*"):
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

        #
        # self.window_menu.executejob = self.window_menu.Append(
        #     ID_MENU_JOB, _("E&xecute Job"), ""
        # )
        # self.window_menu.simulate = self.window_menu.Append(
        #     ID_MENU_SIMULATE, _("&Simulate"), ""
        # )
        # self.window_menu.rasterwizard = self.window_menu.Append(
        #     ID_MENU_RASTER_WIZARD, _("&RasterWizard"), ""
        # )
        # self.window_menu.notes = self.window_menu.Append(ID_MENU_NOTES, _("&Notes"), "")
        # self.window_menu.console = self.window_menu.Append(
        #     ID_MENU_CONSOLE, _("&Console"), ""
        # )
        #
        # self.window_menu.navigation = self.window_menu.Append(
        #     ID_MENU_NAVIGATION, _("N&avigation"), ""
        # )
        # if self.context.has_feature("modifier/Camera"):
        #     self.window_menu.camera = self.window_menu.Append(
        #         ID_MENU_CAMERA, _("C&amera"), ""
        #     )
        # self.window_menu.jobspooler = self.window_menu.Append(
        #     ID_MENU_SPOOLER, _("S&pooler"), ""
        # )
        #
        # self.window_menu.controller = self.window_menu.Append(
        #     ID_MENU_CONTROLLER, _("C&ontroller"), ""
        # )
        # self.window_menu.devices = self.window_menu.Append(
        #     ID_MENU_DEVICE_MANAGER, _("&Devices"), ""
        # )
        # self.window_menu.config = self.window_menu.Append(
        #     ID_MENU_CONFIG, _("Confi&g"), ""
        # )
        # self.window_menu.preferences = self.window_menu.Append(
        #     wx.ID_PREFERENCES, _("Pr&eferences...\tCtrl-,"), ""
        # )
        #
        # self.window_menu.keymap = self.window_menu.Append(
        #     ID_MENU_KEYMAP, _("&Keymap"), ""
        # )
        # self.window_menu.rotary = self.window_menu.Append(
        #     ID_MENU_ROTARY, _("Rotar&y"), ""
        # )
        # self.window_menu.usb = self.window_menu.Append(ID_MENU_USB, _("&USB"), "")

        #

        # self.Bind(
        #     wx.EVT_MENU,
        #     lambda v: self.context("window toggle Console\n"),
        #     id=ID_MENU_CONSOLE,
        # )
        # self.Bind(
        #     wx.EVT_MENU,
        #     lambda v: self.context("window toggle DeviceManager\n"),
        #     id=ID_MENU_DEVICE_MANAGER,
        # )
        # self.Bind(
        #     wx.EVT_MENU,
        #     lambda v: self.context("window toggle Keymap\n"),
        #     id=ID_MENU_KEYMAP,
        # )
        # self.Bind(
        #     wx.EVT_MENU,
        #     lambda v: self.context("window toggle Preferences\n"),
        #     id=wx.ID_PREFERENCES,
        # )
        # self.Bind(
        #     wx.EVT_MENU,
        #     lambda v: self.context("window toggle Notes\n"),
        #     id=ID_MENU_NOTES,
        # )
        # self.Bind(
        #     wx.EVT_MENU,
        #     lambda v: self.context("window toggle Navigation\n"),
        #     id=ID_MENU_NAVIGATION,
        # )
        # self.Bind(
        #     wx.EVT_MENU,
        #     lambda v: self.context("window toggle ExecuteJob 0\n"),
        #     id=ID_MENU_JOB,
        # )
        # if self.context.has_feature("modifier/Camera"):
        #     self.Bind(
        #         wx.EVT_MENU,
        #         lambda v: self.context("window toggle CameraInterface\n"),
        #         id=ID_MENU_CAMERA,
        #     )
        # self.Bind(
        #     wx.EVT_MENU,
        #     lambda v: self.context("window toggle Configuration\n"),
        #     id=ID_MENU_CONFIG,
        # )
        # self.Bind(
        #     wx.EVT_MENU,
        #     lambda v: self.context("window -p rotary/1 open Rotary\n"),
        #     id=ID_MENU_ROTARY,
        # )
        # self.Bind(
        #     wx.EVT_MENU,
        #     lambda v: self.context("window toggle Controller\n"),
        #     id=ID_MENU_CONTROLLER,
        # )
        # self.Bind(
        #     wx.EVT_MENU,
        #     lambda v: self.context("window toggle UsbConnect\n"),
        #     id=ID_MENU_USB,
        # )
        # self.Bind(
        #     wx.EVT_MENU,
        #     lambda v: self.context("window toggle JobSpooler\n"),
        #     id=ID_MENU_SPOOLER,
        # )
        # self.Bind(
        #     wx.EVT_MENU,
        #     lambda v: self.context("window toggle RasterWizard\n"),
        #     id=ID_MENU_RASTER_WIZARD,
        # )
        #
        # def open_simulator(v=None):
        #     with wx.BusyInfo(_("Preparing simulation...")):
        #         self.context(
        #             "plan0 copy preprocess validate blob preopt optimize\nwindow toggle Simulation 0\n"
        #         ),
        #
        # self.Bind(
        #     wx.EVT_MENU,
        #     open_simulator,
        #     id=ID_MENU_SIMULATE,
        # )

    def __set_menubar(self):
        self.file_menu = wx.Menu()
        # ==========
        # FILE MENU
        # ==========

        self.file_menu.Append(wx.ID_NEW, _("&New\tCtrl-N"), "")
        self.file_menu.Append(wx.ID_OPEN, _("&Open Project\tCtrl-O"), "")
        self.recent_file_menu = wx.Menu()
        self.file_menu.AppendSubMenu(self.recent_file_menu, _("&Recent"))
        self.file_menu.Append(ID_MENU_IMPORT, _("&Import File"), "")
        self.file_menu.AppendSeparator()
        self.file_menu.Append(wx.ID_SAVE, _("&Save\tCtrl-S"), "")
        self.file_menu.Append(wx.ID_SAVEAS, _("Save &As\tCtrl-Shift-S"), "")
        self.file_menu.AppendSeparator()
        from sys import platform

        if platform == "darwin":
            self.file_menu.Append(wx.ID_CLOSE, _("&Close Window\tCtrl-W"), "")
        self.file_menu.Append(wx.ID_EXIT, _("E&xit"), "")
        self.main_menubar.Append(self.file_menu, _("File"))

        # ==========
        # VIEW MENU
        # ==========
        self.view_menu = wx.Menu()

        self.view_menu.Append(ID_MENU_ZOOM_OUT, _("Zoom &Out\tCtrl--"), "")
        self.view_menu.Append(ID_MENU_ZOOM_IN, _("Zoom &In\tCtrl-+"), "")
        self.view_menu.Append(ID_MENU_ZOOM_SIZE, _("Zoom To &Size"), "")
        self.view_menu.AppendSeparator()

        self.view_menu.Append(ID_MENU_HIDE_GRID, _("Hide Grid"), "", wx.ITEM_CHECK)
        self.view_menu.Append(
            ID_MENU_HIDE_BACKGROUND, _("Hide Background"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(ID_MENU_HIDE_GUIDES, _("Hide Guides"), "", wx.ITEM_CHECK)
        self.view_menu.Append(ID_MENU_HIDE_PATH, _("Hide Paths"), "", wx.ITEM_CHECK)
        self.view_menu.Append(ID_MENU_HIDE_IMAGE, _("Hide Images"), "", wx.ITEM_CHECK)
        self.view_menu.Append(ID_MENU_HIDE_TEXT, _("Hide Text"), "", wx.ITEM_CHECK)
        self.view_menu.Append(ID_MENU_HIDE_FILLS, _("Hide Fills"), "", wx.ITEM_CHECK)
        self.view_menu.Append(
            ID_MENU_HIDE_STROKES, _("Hide Strokes"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_HIDE_LINEWIDTH, _("No Stroke-Width Render"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_HIDE_LASERPATH, _("Hide Laserpath"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_HIDE_RETICLE, _("Hide Reticle"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_HIDE_SELECTION, _("Hide Selection"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(ID_MENU_HIDE_ICONS, _("Hide Icons"), "", wx.ITEM_CHECK)
        self.view_menu.Append(ID_MENU_HIDE_TREE, _("Hide Tree"), "", wx.ITEM_CHECK)
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
            ID_MENU_SCREEN_REFRESH, _("Do Not Refresh"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(
            ID_MENU_SCREEN_ANIMATE, _("Do Not Animate"), "", wx.ITEM_CHECK
        )
        self.view_menu.Append(ID_MENU_SCREEN_INVERT, _("Invert"), "", wx.ITEM_CHECK)
        self.view_menu.Append(ID_MENU_SCREEN_FLIPXY, _("Flip XY"), "", wx.ITEM_CHECK)

        self.main_menubar.Append(self.view_menu, _("View"))

        # ==========
        # PANE MENU
        # ==========

        self.panes_menu = wx.Menu()
        self.dynamic_fill_pane_menu()
        self.main_menubar.Append(self.panes_menu, _("Panes"))

        # ==========
        # TOOL MENU
        # ==========

        self.window_menu = wx.Menu()
        self.dynamic_fill_window_menu()
        self.main_menubar.Append(self.window_menu, _("Tools"))

        # ==========
        # OSX-ONLY WINDOW MENU
        # ==========
        from sys import platform

        if platform == "darwin":
            wt_menu = wx.Menu()
            self.main_menubar.Append(wt_menu, _("Window"))

        # ==========
        # HELP MENU
        # ==========
        self.help_menu = wx.Menu()

        def launch_help_osx(event=None):
            _resource_path = "help/meerk40t.help"
            if not os.path.exists(_resource_path):
                try:  # pyinstaller internal location
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

        if platform == "darwin":
            self.help_menu.Append(wx.ID_HELP, _("&MeerK40t Help"), "")
            self.Bind(wx.EVT_MENU, launch_help_osx, id=wx.ID_HELP)
            ONLINE_HELP = wx.NewId()
            self.help_menu.Append(ONLINE_HELP, _("&Online Help"), "")
            self.Bind(
                wx.EVT_MENU, lambda e: self.context("webhelp help\n"), id=ONLINE_HELP
            )
        else:
            self.help_menu.Append(wx.ID_HELP, _("&Help"), "")
            self.Bind(
                wx.EVT_MENU, lambda e: self.context("webhelp help\n"), id=wx.ID_HELP
            )

        self.help_menu.Append(ID_BEGINNERS, _("&Beginners' Help"), "")
        self.help_menu.Append(ID_HOMEPAGE, _("&Github"), "")
        self.help_menu.Append(ID_RELEASES, _("&Releases"), "")
        self.help_menu.Append(ID_FACEBOOK, _("&Facebook"), "")
        self.help_menu.Append(ID_MAKERS_FORUM, _("&Makers Forum"), "")
        self.help_menu.Append(ID_IRC, _("&IRC"), "")
        self.help_menu.AppendSeparator()
        self.help_menu.Append(wx.ID_ABOUT, _("&About MeerK40t"), "")
        self.main_menubar.Append(self.help_menu, _("Help"))

        self.SetMenuBar(self.main_menubar)
        # Menu Bar end

        # ==========
        # BINDS
        # ==========
        self.Bind(wx.EVT_MENU, self.on_click_new, id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self.on_click_open, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.on_click_open, id=ID_MENU_IMPORT)
        self.Bind(wx.EVT_MENU, self.on_click_save, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.on_click_save_as, id=wx.ID_SAVEAS)

        self.Bind(wx.EVT_MENU, self.on_click_close, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_MENU, self.on_click_exit, id=wx.ID_EXIT)

        self.Bind(wx.EVT_MENU, self.on_click_zoom_out, id=ID_MENU_ZOOM_OUT)
        self.Bind(wx.EVT_MENU, self.on_click_zoom_in, id=ID_MENU_ZOOM_IN)
        self.Bind(wx.EVT_MENU, self.on_click_zoom_size, id=ID_MENU_ZOOM_SIZE)

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
            wx.EVT_MENU, self.toggle_draw_mode(DRAW_MODE_TREE), id=ID_MENU_HIDE_TREE
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
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle About\n"),
            id=wx.ID_ABOUT,
        )
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
            lambda e: self.context("webhelp irc\n"),
            id=ID_IRC,
        )

        self.add_language_menu()

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
        m = self.GetMenuBar().FindItemById(ID_MENU_HIDE_TREE)
        m.Check(self.context.draw_mode & DRAW_MODE_TREE != 0)
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
                m = wxglade_tmp_menu.Append(wx.ID_ANY, language_name, "", wx.ITEM_RADIO)
                if i == self.context.language:
                    m.Check(True)

                def language_update(q):
                    return lambda e: self.context.app.update_language(q)

                self.Bind(wx.EVT_MENU, language_update(i), id=m.GetId())
                if language_code not in trans and i != 0:
                    m.Enable(False)
                i += 1
            self.main_menubar.Append(wxglade_tmp_menu, _("Languages"))

    @signal_listener("active")
    def on_active_change(self, origin, active):
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

        self.context.close("module/Scene")
        self.context("quit\n")

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

    @signal_listener("pipe;running")
    def on_usb_running(self, origin, value):
        self.usb_running = value

    @signal_listener("pipe;usb_status")
    def on_usb_state_text(self, origin, value):
        self.main_statusbar.SetStatusText(_("Usb: %s") % value, 0)

    @signal_listener("pipe;thread")
    def on_pipe_state(self, origin, state):
        if state == self.pipe_state:
            return
        self.pipe_state = state

        self.main_statusbar.SetStatusText(
            _("Controller: %s") % self.context.kernel.get_text_thread_state(state), 1
        )

    @signal_listener("spooler;thread")
    def on_spooler_state(self, origin, value):
        self.main_statusbar.SetStatusText(
            _("Spooler: %s") % self.context.get_text_thread_state(value), 2
        )

    @signal_listener("export-image")
    def on_export_signal(self, origin, frame):
        image_width, image_height, frame = frame
        if frame is not None:
            elements = self.context.elements
            from PIL import Image

            img = Image.fromarray(frame)
            obj = SVGImage()
            obj.image = img
            obj.image_width = image_width
            obj.image_height = image_height
            elements.add_elem(obj)

    def __set_titlebar(self):
        device_name = ""
        device_version = ""
        title = _("%s v%s") % (
            str(self.context.kernel.name),
            self.context.kernel.version,
        )
        title += "      %s" % self.context.device.name
        self.SetTitle(title)

    def __set_properties(self):
        # begin wxGlade: MeerK40t.__set_properties
        self.__set_titlebar()
        self.main_statusbar.SetStatusWidths([-1] * self.main_statusbar.GetFieldsCount())
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_meerk40t.GetBitmap())
        self.SetIcon(_icon)
        # statusbar fields
        main_statusbar_fields = ["Status"]
        for i in range(len(main_statusbar_fields)):
            self.main_statusbar.SetStatusText(main_statusbar_fields[i], i)

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

        for i in range(self.recent_file_menu.MenuItemCount):
            self.recent_file_menu.Remove(self.recent_file_menu.FindItemByPosition(0))
        context = self.context
        if context.file0 is not None and len(context.file0):
            self.recent_file_menu.Append(ID_MENU_FILE0, "&1   " + context.file0, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file0),
                id=ID_MENU_FILE0,
            )
        if context.file1 is not None and len(context.file1):
            self.recent_file_menu.Append(ID_MENU_FILE1, "&2   " + context.file1, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file1),
                id=ID_MENU_FILE1,
            )
        if context.file2 is not None and len(context.file2):
            self.recent_file_menu.Append(ID_MENU_FILE2, "&3   " + context.file2, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file2),
                id=ID_MENU_FILE2,
            )
        if context.file3 is not None and len(context.file3):
            self.recent_file_menu.Append(ID_MENU_FILE3, "&4   " + context.file3, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file3),
                id=ID_MENU_FILE3,
            )
        if context.file4 is not None and len(context.file4):
            self.recent_file_menu.Append(ID_MENU_FILE4, "&5   " + context.file4, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file4),
                id=ID_MENU_FILE4,
            )
        if context.file5 is not None and len(context.file5):
            self.recent_file_menu.Append(ID_MENU_FILE5, "&6   " + context.file5, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file5),
                id=ID_MENU_FILE5,
            )
        if context.file6 is not None and len(context.file6):
            self.recent_file_menu.Append(ID_MENU_FILE6, "&7   " + context.file6, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file6),
                id=ID_MENU_FILE6,
            )
        if context.file7 is not None and len(context.file7):
            self.recent_file_menu.Append(ID_MENU_FILE7, "&8   " + context.file7, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file7),
                id=ID_MENU_FILE7,
            )
        if context.file8 is not None and len(context.file8):
            self.recent_file_menu.Append(ID_MENU_FILE8, "&9   " + context.file8, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file8),
                id=ID_MENU_FILE8,
            )
        if context.file9 is not None and len(context.file9):
            self.recent_file_menu.Append(ID_MENU_FILE9, "1&0 " + context.file9, "")
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.load_or_open(context.file9),
                id=ID_MENU_FILE9,
            )
        if self.recent_file_menu.MenuItemCount != 0:
            self.recent_file_menu.AppendSeparator()
            self.recent_file_menu.Append(ID_MENU_FILE_CLEAR, _("Clear Recent"), "")
            self.Bind(wx.EVT_MENU, lambda e: self.clear_recent(), id=ID_MENU_FILE_CLEAR)

    def clear_recent(self):
        for i in range(10):
            try:
                setattr(self.context, "file" + str(i), "")
            except IndexError:
                break
        self.populate_recent_menu()

    def set_file_as_recently_used(self, pathname):
        recent = list()
        for i in range(10):
            recent.append(getattr(self.context, "file" + str(i)))
        recent = [r for r in recent if r is not None and r != pathname and len(r) > 0]
        recent.insert(0, pathname)
        for i in range(10):
            try:
                setattr(self.context, "file" + str(i), recent[i])
            except IndexError:
                break
        self.populate_recent_menu()

    def load(self, pathname):
        with wx.BusyInfo(_("Loading File...")):
            n = self.context.elements.note
            try:
                results = self.context.elements.load(
                    pathname,
                    channel=self.context.channel("load"),
                    svg_ppi=self.context.elements.svg_ppi,
                )
            except SyntaxError as e:
                dlg = wx.MessageDialog(
                    None,
                    str(e.msg),
                    _("File is Malformed."),
                    wx.OK | wx.ICON_WARNING,
                )
                dlg.ShowModal()
                dlg.Destroy()
                return False
            if results:
                self.set_file_as_recently_used(pathname)
                if n != self.context.elements.note and self.context.elements.auto_note:
                    self.context("window open Notes\n")  # open/not toggle.
                try:
                    if self.context.elements.uniform_svg and pathname.lower().endswith(
                        "svg"
                    ):
                        # or (len(elements) > 0 and "meerK40t" in elements[0].values):
                        # TODO: Disabled uniform_svg, no longer detecting namespace.
                        self.working_file = pathname
                        self.validate_save()
                except AttributeError:
                    pass
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
        self.working_file = None
        self.validate_save()
        self.context.elements.clear_all()
        self.context(".laserpath_clear\n")

    def on_click_open(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        self.context("dialog_load\n")

    def on_click_stop(self, event=None):
        self.context("estop\n")

    def on_click_pause(self, event=None):
        self.context("pause\n")

    def on_click_save(self, event):
        if self.working_file is None:
            self.on_click_save_as(event)
        else:
            self.set_file_as_recently_used(self.working_file)
            self.validate_save()
            self.context.elements.save(self.working_file)

    def on_click_save_as(self, event=None):
        self.context("dialog_save\n")

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

    def on_click_zoom_size(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoom size button press.
        """
        bbox = self.context.elements.selected_area()
        if bbox is None:
            self.context("scene focus -10% -10% 110% 110%\n")
        else:
            self.context(
                "scene focus %f %f %f %f\n" % (bbox[0], bbox[1], bbox[2], bbox[3])
            )

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

    def apply_rotary_scale(self):
        r = self.context.get_context("rotary/1")
        sx = r.scale_x
        sy = r.scale_y
        spooler, input_driver, output = self.context.root.device()

        mx = Matrix(
            "scale(%f, %f, %f, %f)"
            % (sx, sy, input_driver.current_x, input_driver.current_y)
        )
        for element in self.context.elements.elems():
            try:
                element *= mx
                element.node.modified()
            except AttributeError:
                pass
