import datetime
import os
import platform
import sys
from copy import copy
from functools import partial

import wx
from PIL import Image
from wx import aui

from meerk40t.core.exceptions import BadFileError
from meerk40t.gui.gui_mixins import FormatPainter, Warnings
from meerk40t.gui.statusbarwidgets.defaultoperations import DefaultOperationWidget
from meerk40t.gui.statusbarwidgets.infowidget import (
    BurnProgressPanel,
    InformationWidget,
    StatusPanelWidget,
)
from meerk40t.gui.statusbarwidgets.selectionwidget import (
    SelectionOptionWidget,
    SnapOptionsWidget,
)
from meerk40t.gui.statusbarwidgets.shapepropwidget import (
    FillruleWidget,
    LinecapWidget,
    LinejoinWidget,
)
from meerk40t.gui.statusbarwidgets.statusbar import CustomStatusBar
from meerk40t.gui.statusbarwidgets.strokewidget import ColorWidget, StrokeWidget
from meerk40t.kernel import lookup_listener, signal_listener

from ..core.units import (
    DEFAULT_PPI,
    UNITS_PER_INCH,
    UNITS_PER_MM,
    UNITS_PER_PIXEL,
    Length,
)
from ..svgelements import Color, Matrix, Path
from .icons import (  # icon_duplicate,; icon_nohatch,
    STD_ICON_SIZE,
    PyEmbeddedImage,
    icon_bmap_text,
    icon_cag_common,
    icon_cag_subtract,
    icon_cag_union,
    icon_cag_xor,
    icon_hatch,
    icon_hatch_bidir,
    icon_hatch_diag,
    icon_hatch_diag_bidir,
    icon_line,
    icon_meerk40t,
    icon_mk_align_bottom,
    icon_mk_align_left,
    icon_mk_align_right,
    icon_mk_align_top,
    icon_mk_circle,
    icon_mk_ellipse,
    icon_mk_point,
    icon_mk_polygon,
    icon_mk_polyline,
    icon_mk_rectangular,
    icon_mk_redo,
    icon_mk_undo,
    icon_paint_brush,
    icon_paint_brush_green,
    icon_power_button,
    icon_warning,
    icons8_centerh,
    icons8_centerv,
    icons8_circled_left,
    icons8_circled_right,
    icons8_copy,
    icons8_curly_brackets,
    icons8_cursor,
    icons8_delete,
    icons8_finger,
    icons8_flip_horizontal,
    icons8_flip_vertical,
    icons8_group_objects,
    icons8_measure,
    icons8_node_edit,
    icons8_opened_folder,
    icons8_paste,
    icons8_pencil_drawing,
    icons8_place_marker,
    icons8_rotate_left,
    icons8_rotate_right,
    icons8_save,
    icons8_scissors,
    icons8_ungroup_objects,
    icons8_user_location,
    icons8_vector,
    icons_evenspace_horiz,
    icons_evenspace_vert,
    set_default_icon_size,
    set_icon_appearance,
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
    DRAW_MODE_ORIGIN,
    DRAW_MODE_PATH,
    DRAW_MODE_REGMARKS,
    DRAW_MODE_RETICLE,
    DRAW_MODE_STROKES,
    DRAW_MODE_TEXT,
    DRAW_MODE_VARIABLES,
    swizzlecolor,
)
from .mwindow import MWindow

_ = wx.GetTranslation


class MeerK40t(MWindow):
    """MeerK40t main window"""

    def __init__(self, *args, **kwds):
        width, height = wx.DisplaySize()

        super().__init__(int(width * 0.9), int(height * 0.9), *args, **kwds)
        # We do this very early to allow resizing events to do their thing...
        self.restore_aspect(honor_initial_values=True)
        try:
            self.EnableTouchEvents(wx.TOUCH_ZOOM_GESTURE | wx.TOUCH_PAN_GESTURES)
        except AttributeError:
            # Not WX 4.1
            pass
        # print(self.GetDPIScaleFactor())
        # What is the standardsize of a textbox?
        testbox = wx.TextCtrl(self, wx.ID_ANY)
        tb_size = testbox.Size
        testbox.Destroy()
        factor = 4 * tb_size[1] / 100.0
        # Round to nearest 5...
        def_size = int(round(factor * 50 / 5, 0) * 5)
        set_default_icon_size(def_size)

        self.context.gui = self
        self._usb_running = dict()
        context = self.context
        self.register_options_and_choices(context)

        if self.context.disable_tool_tips:
            wx.ToolTip.Enable(False)

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

        self.ui_visible = True
        self.hidden_panes = []

        # notify AUI which frame to use
        self._mgr.SetManagedWindow(self)

        self.__set_panes()
        self.__set_commands()

        self.edit_menu_choice = None
        self._setup_edit_menu_choice()
        self.view_menu_choice = None

        # Menu Bar
        self.main_menubar = wx.MenuBar()
        self.__set_menubars()
        # Status Bar
        self.startup = True
        # Combine the panels to have more space
        combine = True
        pcount = 3 if combine else 4
        self.main_statusbar = CustomStatusBar(self, pcount)
        self.widgets_created = False
        self.setup_statusbar_panels(combine)
        self.SetStatusBar(self.main_statusbar)
        self.main_statusbar.SetStatusStyles(
            [wx.SB_SUNKEN] * self.main_statusbar.GetFieldsCount()
        )
        # Set the panel sizes
        sizes = [-3] * self.main_statusbar.GetFieldsCount()
        # Make the first Panel large
        sizes[0] = -4
        # And the last one smaller
        sizes[self.main_statusbar.GetFieldsCount() - 1] = -2
        self.SetStatusWidths(sizes)

        # self.main_statusbar.SetStatusWidths([-1] * self.main_statusbar.GetFieldsCount())
        self.SetStatusBarPane(0)
        self.main_statusbar.SetStatusText("", 0)
        self.startup = False
        # Make sure its showing up properly
        self.main_statusbar.Reposition()

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
        self.context.signal("view;realized")
        self.CenterOnScreen()
        self.update_check_at_startup()
        self.tips_at_startup()
        self.parametric_info = None

    def tips_at_startup(self):
        self.context.setting(bool, "show_tips", True)
        if self.context.show_tips:
            self.context("window open Tips\n")
        else:
            self.context("window close Tips\n")

    def update_check_at_startup(self):
        if self.context.update_check == 0:
            return
        if self.context.update_check == 1:
            command = "check_for_updates --verbosity 2\n"
        elif self.context.update_check == 2:
            command = "check_for_updates --beta --verbosity 2\n"
        doit = True
        lastdate = None
        lastcall = self.context.setting(int, "last_update_check", None)
        if lastcall is not None:
            try:
                lastdate = datetime.date.fromordinal(lastcall)
            except ValueError:
                pass
        now = datetime.date.today()
        if lastdate is not None:
            delta = now - lastdate
            # print (f"Delta: {delta.days}, lastdate={lastdate}, interval={self.context.update_frequency}")
            if self.context.update_frequency == 2 and delta.days <= 6:
                # Weekly
                doit = False
            elif self.context.update_frequency == 1 and delta.days <= 0:
                # Daily
                doit = False
        if doit:
            self.context.last_update_check = now.toordinal()
            self.context(command)

    def setup_statusbar_panels(self, combine):
        # if not self.context.show_colorbar:
        #     return
        self.widgets_created = True
        if combine:
            self.idx_colors = self.main_statusbar.panelct - 2
            self.idx_assign = self.main_statusbar.panelct - 2
        else:
            self.idx_colors = self.main_statusbar.panelct - 2
            self.idx_assign = self.main_statusbar.panelct - 3

        self.status_panel = StatusPanelWidget(self.main_statusbar.panelct)
        self.idx_selection = self.main_statusbar.panelct - 1

        self.main_statusbar.add_panel_widget(self.status_panel, 0, "status", True)

        self.select_panel = SelectionOptionWidget()
        self.snap_panel = SnapOptionsWidget()
        self.info_panel = InformationWidget()
        self.main_statusbar.add_panel_widget(
            self.select_panel, self.idx_selection, "selection", False
        )
        self.main_statusbar.add_panel_widget(
            self.snap_panel, self.idx_selection, "snap", False
        )
        self.main_statusbar.add_panel_widget(
            self.info_panel, self.idx_selection, "infos", False
        )

        self.assign_button_panel = DefaultOperationWidget()
        # self.assign_option_panel = OperationAssignOptionWidget()
        self.main_statusbar.add_panel_widget(
            self.assign_button_panel, self.idx_assign, "assign", True
        )
        # self.main_statusbar.add_panel_widget(
        #     self.assign_option_panel, self.idx_assign, "assign-options", True
        # )

        self.color_panel = ColorWidget()
        self.stroke_panel = StrokeWidget()
        self.linecap_panel = LinecapWidget()
        self.linejoin_panel = LinejoinWidget()
        self.fillrule_panel = FillruleWidget()
        self.main_statusbar.add_panel_widget(
            self.color_panel, self.idx_colors, "color", False
        )
        self.main_statusbar.add_panel_widget(
            self.stroke_panel, self.idx_colors, "stroke", False
        )
        self.main_statusbar.add_panel_widget(
            self.linecap_panel, self.idx_colors, "linecap", False
        )
        self.main_statusbar.add_panel_widget(
            self.linejoin_panel, self.idx_colors, "linejoin", False
        )
        self.main_statusbar.add_panel_widget(
            self.fillrule_panel, self.idx_colors, "fillrule", False
        )
        self.burn_panel = BurnProgressPanel()
        self.main_statusbar.add_panel_widget(
            self.burn_panel, self.idx_selection, "burninfo", False
        )
        self.main_statusbar.activate_panel("snap", True)
        self.assign_button_panel.show_stuff(False)

    def _setup_edit_menu_choice(self):
        def on_click_undo():
            self.context("undo\n")

        def on_click_redo():
            self.context("redo\n")

        def on_click_cut():
            self.context("clipboard cut\n")

        def on_click_copy():
            self.context("clipboard copy\n")

        def on_click_paste():
            self.context("clipboard paste\n")

        def on_click_paste_external():
            def paste_image(bmp):
                # Create an image element from the data in the *system* clipboard
                def WxBitmapToWxImage(myBitmap):
                    return wx.ImageFromBitmap(myBitmap)

                def imageToPil(myWxImage):
                    myPilImage = Image.new(
                        "RGB", (myWxImage.GetWidth(), myWxImage.GetHeight())
                    )
                    myPilImage.frombytes(myWxImage.GetData())
                    return myPilImage

                image = imageToPil(WxBitmapToWxImage(bmp))
                dpi = DEFAULT_PPI
                matrix = Matrix(f"scale({UNITS_PER_PIXEL})")
                node = self.context.elements.elem_branch.add(
                    image=image,
                    matrix=matrix,
                    type="elem image",
                    dpi=dpi,
                )
                if self.context.elements.classify_new:
                    self.context.elements.classify([node])
                self.context.elements.set_emphasis([node])

            def paste_files(filelist):
                accepted = 0
                rejected = 0
                rejected_files = []
                for pathname in files:
                    if self.load(pathname):
                        accepted += 1
                    else:
                        rejected += 1
                        rejected_files.append(pathname)
                if rejected != 0:
                    reject = "\n".join(rejected_files)
                    err_msg = _(
                        "Some files were unrecognized:\n{rejected_files}"
                    ).format(rejected_files=reject)
                    dlg = wx.MessageDialog(
                        None, err_msg, _("Error encountered"), wx.OK | wx.ICON_ERROR
                    )
                    dlg.ShowModal()
                    dlg.Destroy()

            def paste_text(content):
                size = 16.0
                node = self.context.elements.elem_branch.add(
                    text=content,
                    matrix=Matrix(f"scale({UNITS_PER_PIXEL})"),
                    type="elem text",
                )
                node.font_size = size
                node.stroke = self.context.elements.default_stroke
                node.stroke_width = self.context.elements.default_strokewidth
                node.fill = self.context.elements.default_fill
                node.altered()
                if self.context.elements.classify_new:
                    self.context.elements.classify([node])
                self.context.elements.set_emphasis([node])

            # Read the image
            success = False
            if wx.TheClipboard.Open():
                # Let's see what we have:
                if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
                    bmap_data = wx.BitmapDataObject()
                    success = wx.TheClipboard.GetData(bmap_data)
                    if success:
                        bmp = bmap_data.GetBitmap()
                        paste_image(bmp)

                elif wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
                    fname_data = wx.FileDataObject()
                    success = wx.TheClipboard.GetData(fname_data)
                    if success:
                        files = fname_data.GetFilenames()
                        paste_files(files)

                elif wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                    text_data = wx.TextDataObject()
                    success = wx.TheClipboard.GetData(text_data)
                    if success:
                        txt = text_data.GetText()
                        paste_text(txt)

                elif wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT)):
                    text_data = wx.TextDataObject()
                    success = wx.TheClipboard.GetData(text_data)
                    if success:
                        txt = text_data.GetText().decode("utf-8")
                        paste_text(txt)

                wx.TheClipboard.Close()

        def on_click_sel_all():
            self.context("element* select\n")

        def on_click_sel_none():
            self.context("element* select-\n")

        def on_click_sel_invert():
            self.context("element* select^\n")

        def on_click_sel_unassigned():
            elements = self.context.elements
            for node in elements.elems():
                flag = False
                if hasattr(node, "references"):
                    flag = True
                    if len(node.references) > 0:
                        flag = False
                if node.can_emphasize:
                    node.emphasized = flag
            elements.validate_selected_area()
            self.context.signal("refresh_scene", "Scene")

        def on_click_properties():
            self.context("window open Properties\n")

        def on_click_device_manager():
            self.context("window open DeviceManager\n")

        def on_click_device_settings():
            self.context("window open Configuration\n")

        def on_click_pref_wordlist():
            self.context("window open Wordlist\n")

        def on_click_pref_fonts():
            self.context("window open HersheyFontManager\n")

        def on_click_pref_keys():
            self.context("window open Keymap\n")

        def on_click_preferences():
            self.context("window open Preferences\n")

        def on_click_delete():
            self.context("tree selected delete\n")

        def external_filled():
            # Does the OS clipboard contain something?
            not_empty = bool(
                wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP))
                or wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT))
                or wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT))
                or wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME))
            )
            return not_empty

        def clipboard_filled():
            res = False
            try:
                destination = self.context.elements._clipboard_default
                if len(self.context.elements._clipboard[destination]) > 0:
                    res = True
            except (TypeError, KeyError):
                pass
            return res

        self.edit_menu_choice = [
            {
                "label": _("&Undo\tCtrl-Z"),
                "help": _("Undo last action"),
                "action": on_click_undo,
                "id": wx.ID_UNDO,
                "enabled": self.context.elements.undo.has_undo,
                "level": 1,
                "segment": "",
            },
            {
                "label": _("&Redo\tCtrl-Shift-Z"),
                "help": _("Revert last undo"),
                "action": on_click_redo,
                "id": wx.ID_REDO,
                "enabled": self.context.elements.undo.has_redo,
                "level": 1,
                "segment": "",
            },
            {
                "label": "",
                "level": 1,
                "segment": "",
            },
            {
                "label": _("C&ut\tCtrl-X"),
                "help": _("Cut selected elements"),
                "action": on_click_cut,
                "enabled": self.context.elements.has_emphasis,
                "id": wx.ID_CUT,
                "level": 1,
                "segment": "",
            },
            {
                "label": _("&Copy\tCtrl-C"),
                "help": _("Copy selected elements to clipboard"),
                "action": on_click_copy,
                "enabled": self.context.elements.has_emphasis,
                "id": wx.ID_COPY,
                "level": 1,
                "segment": "",
            },
            {
                "label": _("&Paste\tCtrl-V"),
                "help": _("Paste elements from clipboard"),
                "action": on_click_paste,
                "enabled": clipboard_filled,
                "id": wx.ID_PASTE,
                "level": 1,
                "segment": "",
            },
            {
                "label": _("Paste from system\tShift-Ctrl-V"),
                "help": _("Paste data coming from other applications"),
                "action": on_click_paste_external,
                "enabled": external_filled,
                "id": wx.ID_ANY,
                "level": 1,
                "segment": "",
            },
            {
                "label": "",
                "level": 1,
                "segment": "",
            },
            {
                "label": _("&Select all\tCtrl-A"),
                "help": _("Select all elements on scene"),
                "action": on_click_sel_all,
                "id": wx.ID_SELECTALL,
                "level": 1,
                "segment": "",
            },
            {
                "label": _("&Select None"),
                "help": _("Deselect all elements on scene"),
                "action": on_click_sel_none,
                "enabled": self.context.elements.has_emphasis,
                "level": 1,
                "segment": "",
            },
            {
                "label": _("&Invert selection\tCtrl-I"),
                "help": _("Invert the selection status of all elements"),
                "action": on_click_sel_invert,
                "level": 1,
                "segment": "",
            },
            {
                "label": _("Select all non-assigned"),
                "help": _("Select all elements that are not assigned to an operation"),
                "action": on_click_sel_unassigned,
                "level": 1,
                "segment": "",
            },
            {
                "label": "",
                "level": 1,
                "segment": "",
            },
            {
                "label": _("Delete"),
                "help": _("Delete the selected elements"),
                "action": on_click_delete,
                "enabled": self.context.elements.has_emphasis,
                "level": 1,
                "segment": "",
            },
            {
                "label": "",
                "level": 1,
                "segment": "",
            },
            {
                "label": _("Properties"),
                "help": _("Edit the elements properties"),
                "action": on_click_properties,
                "enabled": self.context.elements.has_emphasis,
                "level": 1,
                "segment": "",
            },
            {
                "label": "",
                "level": 1,
                "segment": "",
            },
            {
                "label": _("Device-Manager"),
                "help": _("Manage the Laser devices"),
                "action": on_click_device_manager,
                "level": 1,
                "segment": "",
            },
            {
                "label": _("Device-Configuration"),
                "help": _("Manage the device settings"),
                "action": on_click_device_settings,
                "level": 1,
                "segment": "",
            },
            {
                "label": "",
                "level": 1,
                "segment": "",
            },
            {
                "label": _("Wordlist-Editor"),
                "help": _("Manages Wordlist-Entries"),
                "action": on_click_pref_wordlist,
                "level": 2,
                "segment": "Settings",
            },
            {
                "label": _("Font-Manager"),
                "help": _("Open the vector-font management window."),
                "action": on_click_pref_fonts,
                "level": 2,
                "segment": "Settings",
            },
            {
                "label": _("Key-Bindings"),
                "help": _("Opens Keymap Window"),
                "action": on_click_pref_keys,
                "level": 2,
                "segment": "Settings",
            },
            {
                "label": "",
                "level": 2,
                "segment": "Settings",
            },
            {
                "label": _("Preferences\tCtrl-,"),
                "help": _("Edit the general preferences"),
                "action": on_click_preferences,
                "level": 2,
                "id": wx.ID_PREFERENCES,
                "segment": "Settings",
            },
        ]

    def destroy_statusbar_panels(self):
        self.main_statusbar.Clear()
        self.widgets_created = False

    # --- Listen to external events to toggle regmark visibility
    @signal_listener("toggle_regmarks")
    def on_regmark_toggle(self, origin, *args):
        bits = DRAW_MODE_REGMARKS
        self.context.draw_mode ^= bits
        self.context.signal("draw_mode", self.context.draw_mode)
        self.context.signal("refresh_scene", "Scene")

    # --- Listen to external events to update the bar
    # @signal_listener("show_colorbar")
    # def on_colobar_signal(self, origin, *args):
    #     if len(args) > 0:
    #         showem = args[0]
    #     else:
    #         showem = True
    #     if showem:
    #         if not self.widgets_created:
    #             self.setup_statusbar_panels()
    #     else:
    #         if self.widgets_created:
    #             self.destroy_statusbar_panels()

    @signal_listener("element_property_reload")
    @signal_listener("element_property_update")
    def on_element_update(self, origin, *args):
        if self.widgets_created:
            self.main_statusbar.Signal("element_property_update", *args)

    @signal_listener("modified")
    def on_element_modified(self, origin, *args):
        if self.widgets_created:
            self.main_statusbar.Signal("modified", *args)

    @signal_listener("rebuild_tree")
    @signal_listener("refresh_tree")
    @signal_listener("tree_changed")
    @signal_listener("operation_removed")
    @signal_listener("add_operation")
    def on_rebuild(self, origin, *args):
        if self.widgets_created:
            self.main_statusbar.Signal("rebuild_tree")

    # --------- Events for status bar
    @signal_listener("element_clicked")
    def on_element_clicked(self, origin, *args):
        self.format_painter.on_emphasis(args)

    @signal_listener("emphasized")
    def on_update_statusbar(self, origin, *args):
        value = self.context.elements.has_emphasis()
        self._update_status_menu(self.edit_menu, self.edit_menu_choice)
        self._update_status_menu(self.view_menu, self.view_menu_choice)
        if not self.widgets_created:
            return

        self.main_statusbar.Signal("emphasized")
        # First enable/disable the controls in the statusbar

        self.assign_button_panel.show_stuff(value)
        self.main_statusbar.activate_panel("selection", value, force=True)
        self.main_statusbar.activate_panel("infos", value)
        self.main_statusbar.activate_panel("color", value)
        self.main_statusbar.activate_panel("stroke", value)
        self.main_statusbar.activate_panel("fillrule", value)
        self.main_statusbar.activate_panel("linejoin", value)
        self.main_statusbar.activate_panel("linecap", value)
        self.main_statusbar.Reposition()

    # ------------ Setup
    def register_options_and_choices(self, context):
        _ = context._
        context.setting(bool, "disable_tool_tips", False)
        context.setting(bool, "enable_sel_move", True)
        context.setting(bool, "enable_sel_size", True)
        context.setting(bool, "enable_sel_rotate", True)
        context.setting(bool, "enable_sel_skew", False)
        context.setting(int, "zoom_margin", 4)  # 4%
        # Standard-Icon-Sizes
        # default, factor 1 - leave as is
        # small = factor 2/3, min_size = 32
        # tiny  = factor 1/2, min_size = 25
        # context.setting(str, "icon_size", "default")
        # Ribbon-Size (NOT YET ACTIVE)
        # default - std icon size + panel-labels,
        # small - std icon size / no labels
        # tiny - reduced icon size / no labels
        context.setting(str, "ribbon_appearance", "default")
        # choices = [
        #     {
        #         "attr": "ribbon_appearance",
        #         "object": self.context.root,
        #         "default": "default",
        #         "type": str,
        #         "style": "combosmall",
        #         "choices": ["default", "small", "tiny"],
        #         "label": _("Ribbon-Size:"),
        #         "tip": _(
        #             "Appearance of ribbon at the top (requires a restart to take effect))"
        #         ),
        #         "page": "Gui",
        #         "section": "Appearance",
        #     },
        # ]
        # context.kernel.register_choices("preferences", choices)
        choices = [
            {
                "attr": "icon_size",
                "object": self.context.root,
                "default": "small",
                "type": str,
                "style": "combosmall",
                "choices": ["large", "big", "default", "small", "tiny"],
                "label": _("Icon size:"),
                "tip": _(
                    "Appearance of all icons in the GUI (requires a restart to take effect)"
                ),
                "page": "Gui",
                "section": "Appearance",
                "signals": "restart",
            },
            {
                "attr": "mini_icon",
                "object": self.context.root,
                "default": False,
                "type": bool,
                "label": _("Mini icon in tree"),
                "tip": _(
                    "Active: Display a miniature representation of the element in the tree\n"
                    + "Inactive: Use a standard icon for the element type instead"
                ),
                "page": "Gui",
                "section": "Appearance",
                "signals": "rebuild_tree",
            },
            {
                "attr": "tree_colored",
                "object": self.context.root,
                "default": True,
                "type": bool,
                "label": _("Color entries in tree"),
                "tip": _(
                    "Active: The tree entry will be displayed in the objects color\n"
                    + "Inactive: Standard Colors are used"
                ),
                "page": "Gui",
                "section": "Appearance",
                "signals": "rebuild_tree",
            },
        ]
        context.kernel.register_choices("preferences", choices)

        choices = [
            {
                "attr": "zoom_margin",
                "object": self.context.root,
                "default": 4,
                "trailer": "%",
                "type": int,
                "style": "combosmall",
                "choices": [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    9,
                    10,
                    15,
                    20,
                    25,
                ],
                "label": _("Default zoom margin:"),
                "tip": _(
                    "Default zoom margin when zoom focused on a location (automatically or via Ctrl-B)"
                ),
                "page": "Gui",
                "section": "Zoom",
            },
            {
                "attr": "zoom_factor",
                "object": self.context.root,
                "default": 0.1,
                "trailer": "x",
                "type": float,
                "label": _("Default zoom factor:"),
                "tip": _(
                    "Default zoom factor controls how quick or fast zooming happens."
                ),
                "page": "Gui",
                "section": "Zoom",
            },
            {
                "attr": "pan_factor",
                "object": self.context.root,
                "default": 25.0,
                "trailer": "px",
                "type": float,
                "label": _("Default pan factor:"),
                "tip": _("Default pan factor controls how quick panning happens."),
                "page": "Gui",
                "section": "Zoom",
            },
        ]
        context.kernel.register_choices("preferences", choices)
        choices = [
            {
                "attr": "autofocus_resize",
                "object": self.context.root,
                "default": False,
                "type": bool,
                "label": _("Autofocus bed on resize"),
                "tip": _("Autofocus bed when resizing the main window"),
                "page": "Gui",
                "section": "Zoom",
            },
        ]
        context.kernel.register_choices("preferences", choices)

        choices = [
            {
                "attr": "select_smallest",
                "object": context.root,
                "default": True,
                "type": bool,
                "label": _("Select smallest element on scene"),
                "tip": _(
                    "Active: Single click selects the smallest element under cursor (ctrl+click selects the largest) / Inactive: Single click selects the largest element  (ctrl+click the smallest)."
                ),
                "page": "Scene",
                "section": "General",
            },
            {
                "attr": "auto_select",
                "object": context.root,
                "default": True,
                "type": bool,
                "label": _("Auto-select element after creation"),
                "tip": _(
                    "Active: selects a newly created element (via one of the tools in the toolbar)"
                ),
                "page": "Scene",
                "section": "General",
            },
        ]
        context.kernel.register_choices("preferences", choices)

        # choices = [
        #     {
        #         "attr": "show_colorbar",
        #         "object": self.context.root,
        #         "default": True,
        #         "type": bool,
        #         "label": _("Display colorbar in statusbar"),
        #         "tip": _(
        #             "Enable the display of a colorbar at the bottom of the screen."
        #         ),
        #         "page": "Gui",
        #         "section": "General",
        #     },
        # ]
        # context.kernel.register_choices("preferences", choices)

        choices = [
            {
                "attr": "outer_handles",
                "object": context.root,
                "default": False,
                "type": bool,
                "label": _("Draw selection handle outside of bounding box"),
                "tip": _(
                    "Active: draw handles outside of / Inactive: Draw them on the bounding box of the selection."
                ),
                "page": "Scene",
                "section": "General",
            },
        ]
        context.kernel.register_choices("preferences", choices)

        choices = [
            {
                "attr": "show_attract_len",
                "object": context.root,
                "default": 45,
                "type": int,
                "style": "slider",
                "min": 1,
                "max": 75,
                "label": _("Display-Distance"),
                "tip": _(
                    "The screen distance in pixels inside which snap points will be highlighted"
                ),
                "page": "Scene",
                "section": "Snap-Options",
            },
            {
                "attr": "snap_points",
                "object": context.root,
                "default": False,
                "type": bool,
                "label": _("Snap to Element"),
                "tip": _(
                    "If checked, the cursor will snap to the closest element point within the specified threshold"
                ),
                "page": "Scene",
                "section": "Snap-Options",
                "subsection": "Element-Points",
            },
            {
                "attr": "action_attract_len",
                "object": context.root,
                "conditional": (context.root, "snap_points"),
                "default": 20,
                "type": int,
                "style": "slider",
                "min": 1,
                "max": 75,
                "label": _("Element-Point-Snap-Threshold"),
                "tip": _(
                    "Set the screen distance in pixels inside which the cursor will snap to the nearest element point"
                ),
                "page": "Scene",
                "section": "Snap-Options",
                "subsection": "Element-Points",
            },
            {
                "attr": "snap_grid",
                "object": context.root,
                "default": True,
                "type": bool,
                "label": _("Snap to Grid"),
                "tip": _(
                    "If checked, the cursor will snap to the closest grid intersection"
                ),
                "page": "Scene",
                "section": "Snap-Options",
                "subsection": "Grid",
            },
            {
                "attr": "grid_attract_len",
                "object": context.root,
                "default": 15,
                "conditional": (context.root, "snap_grid"),
                "type": int,
                "style": "slider",
                "min": 1,
                "max": 75,
                "label": _("Grid-Point-Snap-Threshold"),
                "tip": _(
                    "Set the screen distance in pixels inside which the cursor will snap to the nearest grid intersection"
                ),
                "page": "Scene",
                "section": "Snap-Options",
                "subsection": "Grid",
            },
            {
                "attr": "clear_magnets",
                "object": context.root,
                "default": True,
                "type": bool,
                "label": _("Clear magnets on File/New"),
                "tip": _(
                    "File/New can remove all defined magnetlines (active)\nor leave them in place (inactive)"
                ),
                "page": "Scene",
                "section": "Snap-Options",
                "subsection": "Magnetlines",
            },
        ]
        for c in choices:
            c["help"] = "snap"
        context.kernel.register_choices("preferences", choices)
        choices = [
            # {
            #     "attr": "use_toolmenu",
            #     "object": context.root,
            #     "default": True,
            #     "type": bool,
            #     "label": _("Use in-scene tool-menu"),
            #     "tip": _(
            #         "The scene-menu will appear if you right-click on the scene-background"
            #     ),
            #     "page": "Gui",
            #     "hidden": True,
            #     "section": "Scene",
            # },
            {
                "attr": "button_repeat",
                "object": self.context.root,
                "default": 0.5,
                "type": float,
                "label": _("Button repeat-interval"),
                "tip": _(
                    "If you click and hold the mouse-button on the Jog/Drag-Panels\n"
                    + "the movement action will be repeated. This value establishes\n"
                    + "the interval between individual executions.\n"
                    + "A value of 0 will disable this feature."
                ),
                "page": "Gui",
                "section": "Misc.",
                "subsection": "Button-Behaviour",
                "signals": "button-repeat",
            },
            {
                "attr": "button_accelerate",
                "object": self.context.root,
                "default": True,
                "type": bool,
                "label": _("Accelerate repeats"),
                "tip": _(
                    "If you hold the button for some time, then after some repetitions\n"
                    + "the action will increase in speed if you activate this option."
                ),
                "page": "Gui",
                "section": "Misc.",
                "subsection": "Button-Behaviour",
                "signals": "button-repeat",
            },
            {
                "attr": "process_while_typing",
                "object": context.root,
                "default": False,
                "type": bool,
                "label": _("Process input while typing"),
                "tip": _(
                    "Try to immediately use values you enter in dialog-textfields - "
                )
                + "\n"
                + _(
                    "otherwise they will get applied only after a deliberate confirmation"
                )
                + "\n"
                + _("by enter or stepping out of the field)"),
                "page": "Gui",
                # "hidden": True,
                "section": "Misc.",
            },
        ]
        context.kernel.register_choices("preferences", choices)

        context.register(
            "function/open_property_window_for_node", self.open_property_window_for_node
        )
        if context.icon_size == "tiny":
            set_icon_appearance(0.5, int(0.5 * STD_ICON_SIZE))
        elif context.icon_size == "small":
            set_icon_appearance(2 / 3, int(2 / 3 * STD_ICON_SIZE))
        elif context.icon_size == "big":
            set_icon_appearance(1.5, 0)
        elif context.icon_size == "large":
            set_icon_appearance(2.0, 0)
        else:
            set_icon_appearance(1.0, 0)

        self.format_painter = FormatPainter(
            self.context, "button/extended_tools/Paint", "editpaint"
        )
        self.warning_routine = Warnings(self.context, "button/jobstart/Warning")

    def open_property_window_for_node(self, node):
        """
        Activate the node in question.

        @param node:
        @return:
        """
        gui = self
        root = self.context.root
        root.open("window/Properties", gui)

    @staticmethod
    def sub_register(kernel):
        def register_effects():
            # Cmd, tip, icon, label, category
            # Hatches
            eff = (
                "effect-hatch -e scanline",
                "Wrap the current node in a hatch",
                icon_hatch,
                "Simple line hatch",
                "Fill (unidirectional)",
            )
            kernel.register("registered_effects/SimpleLine", eff)
            eff = (
                "effect-hatch -e scanline -a 45deg",
                "Wrap the current node in a hatch",
                icon_hatch_diag,
                "Diagonal line hatch",
                "Fill (unidirectional)",
            )
            kernel.register("registered_effects/DiagonalLine", eff)

            eff = (
                "effect-hatch -e eulerian",
                "Wrap the current node in a hatch (bidirectional)",
                icon_hatch_bidir,
                "Simple line hatch (bidirectional)",
                "Fill bidirectional",
            )
            kernel.register("registered_effects/SimpleLineBD", eff)
            eff = (
                "effect-hatch -e eulerian -a 45deg",
                "Wrap the current node in a diagonal hatch (bidirectional)",
                icon_hatch_diag_bidir,
                "Diagonal line hatch (bidirectional)",
                "Fill bidirectional",
            )
            kernel.register("registered_effects/DiagonalLineBD", eff)

            # Wobbles
            eff = (
                "effect-wobble -w circle",
                "Apply a wobble movement along the path (circular on top of the line)",
                icon_hatch_diag_bidir,
                "Wobble circular (centered)",
                "Path",
            )
            kernel.register("registered_effects/WobbleCircle", eff)

            eff = (
                "effect-wobble -w circle-right",
                "Apply a wobble movement along the path (circular, at the right side of the line)",
                icon_hatch_diag_bidir,
                "Wobble circular (right)",
                "Path",
            )

            kernel.register("registered_effects/WobbleCircleL", eff)
            eff = (
                "effect-wobble -w circle-left",
                "Apply a wobble movement along the path (circular, at the left side of the line)",
                icon_hatch_diag_bidir,
                "Wobble circular (left)",
                "Path",
            )
            kernel.register("registered_effects/WobbleCircleR", eff)

        bsize_normal = STD_ICON_SIZE
        # bsize_small = STD_ICON_SIZE / 2
        bsize_small = STD_ICON_SIZE
        register_effects()

        def contains_a_param():
            result = False
            for e in kernel.elements.elems(emphasized=True):
                if (
                    hasattr(e, "functional_parameter")
                    and e.functional_parameter is not None
                ):
                    result = True
                    break
            return result

        def contains_moveable_nodes():
            result = False
            for e in kernel.elements.elems(emphasized=True):
                if hasattr(e, "as_geometry"):
                    result = True
                    break
            return result

        def contains_a_path():
            result = False
            for e in kernel.elements.elems(emphasized=True):
                if e.type in ("elem polyline", "elem path"):
                    result = True
                    break
            return result

        def contains_an_element():
            from meerk40t.core.elements.element_types import elem_nodes

            for e in kernel.elements.elems(emphasized=True):
                if e.type in elem_nodes:
                    return True
            return False

        kernel.register(
            "button/project/Open",
            {
                "label": _("Open"),
                "icon": icons8_opened_folder,
                "tip": _("Opens new project"),
                "help": "loadsave",
                "action": lambda e: kernel.console(".dialog_load\n"),
                "priority": -200,
                "size": bsize_normal,
            },
        )
        kernel.register(
            "button/project/Save",
            {
                "label": _("Save"),
                "icon": icons8_save,
                "tip": _("Saves a project to disk"),
                "help": "loadsave",
                "action": lambda e: kernel.console(".dialog_save\n"),
                "priority": -100,
                "size": bsize_normal,
            },
        )

        # Default Size for tool buttons - none: use icon size
        buttonsize = STD_ICON_SIZE

        kernel.register(
            "button/select/Scene",
            {
                "label": _("Select"),
                "icon": icons8_cursor,
                "tip": _("Regular selection tool"),
                "help": "select",
                "action": lambda v: kernel.elements("tool none\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "none",
            },
        )

        # kernel.register(
        #     "button/tools/Nodeeditor",
        #     {
        #         "label": _("Node Edit"),
        #         "icon": icons8_node_edit,
        #         "tip": _("Edit nodes of a polyline/path-object"),
        #         "action": lambda v: kernel.elements("tool nodemove\n"),
        #         "group": "tool",
        #         "size": bsize_normal,
        #         "identifier": "nodemove",
        #     },
        # )
        def finger_tool():
            if contains_a_param():
                kernel.elements("tool parameter\n")
            elif contains_moveable_nodes():
                kernel.elements("tool pointmove\n")

        kernel.register(
            "button/select/Parameter",
            {
                "label": _("Parametric Edit"),
                "icon": icons8_finger,
                "tip": _("Parametric edit of a shape"),
                "help": "parametric",
                "action": lambda v: finger_tool(),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "parameter",
                "rule_enabled": lambda cond: contains_a_param()
                or contains_moveable_nodes(),
            },
        )
        kernel.register(
            "button/select/Nodeeditor",
            {
                "label": _("Node Edit"),
                "icon": icons8_node_edit,
                "tip": _("Edit nodes of a polyline/path-object"),
                "help": "nodeedit",
                "action": lambda v: kernel.elements("tool edit\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "edit",
                "rule_enabled": lambda cond: contains_a_path(),
            },
        )
        rightmsg = "\n" + _("(Right click removes the hatch)")
        effects = list(kernel.lookup_all("registered_effects"))
        # Sort according to categories....
        effects.sort(key=lambda v: v[4])
        sub_effects = list()
        first_hatch = None

        def action(command):
            local_command = command

            def routine(*args):
                kernel.elements(f"{local_command}\n")

            return routine

        for idx, hatch in enumerate(effects):
            if len(hatch) < 4:
                continue
            if not hatch[4].lower().startswith("fill"):
                continue

            cmd = hatch[0]
            if first_hatch is None:
                first_hatch = cmd
            tip = _(hatch[1]) + rightmsg
            icon = hatch[2]
            if icon is None:
                icon = icon_hatch
            label = hatch[3]

            hdict = {
                "identifier": f"hatch_{idx}",
                "label": _(label),
                "icon": icon,
                "tip": tip,
                "help": "hatches",
                "action": action(cmd),
                "action_right": lambda v: kernel.elements("effect-remove\n"),
                "rule_enabled": lambda cond: contains_an_element(),
            }
            sub_effects.append(hdict)

        # hdict = {
        #     "identifier": "hatch_none",
        #     "label": _("Remove hatch"),
        #     "icon": icon_nohatch,
        #     "tip": _("Remove the effect"),
        #     "action": lambda v: kernel.elements("effect-remove\n"),
        #     "rule_enabled": lambda cond: contains_an_element(),
        # }
        # sub_effects.append(hdict)

        hatch_button = {
            "identifier": "hatchbutton",
            "label": _("Hatch"),
            "icon": sub_effects[0]["icon"],
            "tip": sub_effects[0]["tip"],
            "help": "hatches",
            "action": action(first_hatch),
            "action_right": lambda v: kernel.elements("effect-remove\n"),
            "size": bsize_normal,
            "rule_enabled": lambda cond: contains_an_element(),
        }

        if len(sub_effects) > 1:
            hatch_button["multi"] = sub_effects

        kernel.register(
            "button/select/Hatch",
            hatch_button,
        )
        kernel.register(
            "button/lasercontrol/Relocate",
            {
                "label": _("Set Position"),
                "icon": icons8_place_marker,
                "tip": _("Set position to given location"),
                "action": lambda v: kernel.elements("tool relocate\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "relocate",
            },
        )

        kernel.register(
            "button/lasercontrol/Placement",
            {
                "label": _("Job Start"),
                "icon": icons8_user_location,
                "tip": _("Add a job starting point to the scene"),
                "help": "placement",
                "action": lambda v: kernel.elements("tool placement\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "placement",
            },
        )

        kernel.register(
            "button/tools/line",
            {
                "label": _("Line"),
                "icon": icon_line,
                "tip": _("Add a simple line element"),
                "help": "basicshapes",
                "action": lambda v: kernel.elements("tool line\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "line",
            },
        )

        kernel.register(
            "button/tools/circle",
            {
                "label": _("Circle"),
                "icon": icon_mk_circle,
                "tip": _("Add a circle element"),
                "help": "basicshapes",
                "action": lambda v: kernel.elements("tool circle\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "circle",
            },
        )

        kernel.register(
            "button/tools/ellipse",
            {
                "label": _("Ellipse"),
                "icon": icon_mk_ellipse,
                "tip": _("Add an ellipse element"),
                "help": "basicshapes",
                "action": lambda v: kernel.elements("tool ellipse\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "ellipse",
            },
        )

        kernel.register(
            "button/tools/Rectangle",
            {
                "label": _("Rectangle"),
                "icon": icon_mk_rectangular,
                "tip": _("Add a rectangular element"),
                "help": "basicshapes",
                "action": lambda v: kernel.elements("tool rect\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "rect",
            },
        )

        kernel.register(
            "button/tools/Polygon",
            {
                "label": _("Polygon"),
                "icon": icon_mk_polygon,
                "tip": _(
                    "Add a polygon element\nLeft click: point/line\nDouble click: complete\nRight click: cancel"
                ),
                "help": "basicshapes",
                "action": lambda v: kernel.elements("tool polygon\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "polygon",
            },
        )

        kernel.register(
            "button/tools/Polyline",
            {
                "label": _("Polyline"),
                "icon": icon_mk_polyline,
                "tip": _(
                    "Add a polyline element\nLeft click: point/line\nDouble click: complete\nRight click: cancel"
                ),
                "help": "basicshapes",
                "action": lambda v: kernel.elements("tool polyline\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "polyline",
            },
        )

        kernel.register(
            "button/tools/Point",
            {
                "label": _("Point"),
                "icon": icon_mk_point,
                "tip": _("Add point to the scene"),
                "help": "basicshapes",
                "action": lambda v: kernel.elements("tool point\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "point",
            },
        )

        kernel.register(
            "button/tools/Vector",
            {
                "label": _("Vector"),
                "icon": icons8_vector,
                "tip": _(
                    "Add a shape\nLeft click: point/line\nClick and hold: curve\nDouble click: complete\nRight click: end"
                ),
                "help": "basicshapes",
                "action": lambda v: kernel.elements("tool vector\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "vector",
            },
        )

        kernel.register(
            "button/tools/Draw",
            {
                "label": _("Draw"),
                "icon": icons8_pencil_drawing,
                "tip": _("Add a free-drawing element"),
                "help": "basicshapes",
                "action": lambda v: kernel.elements("tool draw\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "draw",
            },
        )

        kernel.register(
            "button/tools/Text",
            {
                "label": _("Text"),
                "icon": icon_bmap_text,
                "tip": _("Add a text element"),
                "help": "basicshapes",
                "action": lambda v: kernel.elements("tool text\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "text",
            },
        )

        kernel.register(
            "button/basicediting/Delete",
            {
                "label": _("Delete"),
                "icon": icons8_delete,
                "tip": _("Delete selected items"),
                "help": "basicediting",
                "action": lambda v: kernel.elements("tree selected delete\n"),
                "size": bsize_normal,
                "rule_enabled": lambda cond: bool(kernel.elements.has_emphasis()),
            },
        )
        kernel.register(
            "button/basicediting/Cut",
            {
                "label": _("Cut"),
                "icon": icons8_scissors,
                "tip": _("Cut selected elements"),
                "help": "basicediting",
                "action": lambda v: kernel.elements("clipboard cut\n"),
                "size": bsize_small,
                "identifier": "editcut",
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/basicediting/Copy",
            {
                "label": _("Copy"),
                "icon": icons8_copy,
                "tip": _("Copy selected elements to clipboard"),
                "help": "basicediting",
                "action": lambda v: kernel.elements("clipboard copy\n"),
                "size": bsize_small,
                "identifier": "editcopy",
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )

        def clipboard_filled():
            res = False
            try:
                destination = kernel.elements._clipboard_default
                if len(kernel.elements._clipboard[destination]) > 0:
                    res = True
            except (TypeError, KeyError):
                pass
            return res

        kernel.register(
            "button/basicediting/Paste",
            {
                "label": _("Paste"),
                "icon": icons8_paste,
                "tip": _("Paste elements from clipboard"),
                "help": "basicediting",
                "action": lambda v: kernel.elements(
                    "clipboard paste -dx 3mm -dy 3mm\n"
                ),
                "size": bsize_small,
                "identifier": "editpaste",
                "rule_enabled": lambda cond: clipboard_filled(),
            },
        )

        # kernel.register(
        #     "button/basicediting/Duplicate",
        #     {
        #         "label": _("Duplicate"),
        #         "icon": icon_duplicate,
        #         "tip": _("Duplicate selected elements"),
        #         "action": lambda v: kernel.elements("element copy --dx=3mm --dy=3mm\n"),
        #         "size": bsize_small,
        #         "identifier": "editduplicate",
        #         "rule_enabled": lambda cond: len(
        #             list(kernel.elements.elems(emphasized=True))
        #         )
        #         > 0,
        #     },
        # )
        kernel.register(
            "button/undo/Undo",
            {
                "label": _("Undo"),
                "icon": icon_mk_undo,
                "tip": _("Undo last operation"),
                "help": "basicediting",
                "action": lambda v: kernel.elements("undo\n"),
                "size": bsize_small,
                "identifier": "editundo",
                "rule_enabled": lambda cond: kernel.elements.undo.has_undo(),
            },
        )
        kernel.register(
            "button/undo/Redo",
            {
                "label": _("Redo"),
                "icon": icon_mk_redo,
                "tip": _("Redo last operation"),
                "help": "basicediting",
                "action": lambda v: kernel.elements("redo\n"),
                "size": bsize_small,
                "identifier": "editredo",
                "rule_enabled": lambda cond: kernel.elements.undo.has_redo(),
            },
        )

        kernel.register(
            "button/extended_tools/Measure",
            {
                "label": _("Measure"),
                "icon": icons8_measure,
                "tip": _(
                    "Measure distance / perimeter / area\nLeft click: point/line\nDouble click: complete\nRight click: cancel"
                ),
                "help": "measure",
                "action": lambda v: kernel.elements("tool measure\n"),
                "group": "tool",
                "size": bsize_normal,
                "identifier": "measure",
            },
        )

        # Default Size for smaller buttons
        buttonsize = STD_ICON_SIZE / 2

        kernel.register(
            "button/modify/Flip",
            {
                "label": _("Flip Vertical"),
                "icon": icons8_flip_vertical,
                "tip": _("Flip the selected element vertically"),
                "help": "flip",
                "action": lambda v: kernel.elements("scale 1 -1\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/modify/Mirror",
            {
                "label": _("Mirror Horizontal"),
                "icon": icons8_flip_horizontal,
                "tip": _("Mirror the selected element horizontally"),
                "help": "flip",
                "action": lambda v: kernel.elements("scale -1 1\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/modify/Rotate90CW",
            {
                "label": _("Rotate CW"),
                "icon": icons8_rotate_right,
                "tip": _("Rotate the selected element clockwise by 90 deg"),
                "help": "flip",
                "action": lambda v: kernel.elements("rotate 90deg\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/modify/Rotate90CCW",
            {
                "label": _("Rotate CCW"),
                "icon": icons8_rotate_left,
                "tip": _("Rotate the selected element counterclockwise by 90 deg"),
                "help": "flip",
                "action": lambda v: kernel.elements("rotate -90deg\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/geometry/Union",
            {
                "label": _("Union"),
                "icon": icon_cag_union,
                "tip": _("Create a union of the selected elements"),
                "help": "cag",
                "action": lambda v: kernel.elements("element union\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 1,
            },
        )
        kernel.register(
            "button/geometry/Difference",
            {
                "label": _("Difference"),
                "icon": icon_cag_subtract,
                "tip": _("Create a difference of the selected elements"),
                "help": "cag",
                "action": lambda v: kernel.elements("element difference\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 1,
            },
        )
        kernel.register(
            "button/geometry/Xor",
            {
                "label": _("Xor"),
                "icon": icon_cag_xor,
                "tip": _("Create a xor of the selected elements"),
                "help": "cag",
                "action": lambda v: kernel.elements("element xor\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 1,
            },
        )
        kernel.register(
            "button/geometry/Intersection",
            {
                "label": _("Intersection"),
                "icon": icon_cag_common,
                "tip": _("Create a intersection of the selected elements"),
                "help": "cag",
                "action": lambda v: kernel.elements("element intersection\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 1,
            },
        )

        def group_selection():
            group_node = None
            lets_do_it = False
            data = list(kernel.elements.elems(emphasized=True))
            sel_count = len(data)
            my_parent = None
            for node in data:
                this_parent = None
                if hasattr(node, "parent"):
                    if hasattr(node.parent, "type"):
                        if node.parent.type in ("group", "file"):
                            this_parent = node.parent
                if my_parent is None:
                    if this_parent is not None:
                        my_parent = this_parent
                else:
                    if my_parent != this_parent:
                        # different parents, so definitely a do it
                        lets_do_it = True
                        break
            if not lets_do_it:
                if my_parent is None:
                    # All base elements
                    lets_do_it = True
                else:
                    parent_ct = len(my_parent.children)
                    if parent_ct != sel_count:
                        # Not the full group...
                        lets_do_it = True

            if lets_do_it:
                for node in data:
                    if group_node is None:
                        group_node = node.parent.add(type="group", label="Group")
                    group_node.append_child(node)
                    node.emphasized = True
                if group_node is not None:
                    group_node.emphasized = True
                    kernel.signal("element_property_reload", "Scene", group_node)

        # Default Size for normal buttons
        buttonsize = STD_ICON_SIZE
        kernel.register(
            "button/group/Group",
            {
                "label": _("Group"),
                "icon": icons8_group_objects,
                "tip": _("Group elements together"),
                "help": "group",
                "action": lambda v: group_selection(),
                "size": bsize_normal,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 1,
            },
        )

        def ungroup_selection():
            def release_em(node):
                for n in list(node.children):
                    node.insert_sibling(n)
                node.remove_node()  # Removing group/file node.

            found_some = False
            for node in list(kernel.elements.elems(emphasized=True)):
                if node is not None:
                    if node.type in ("group", "file"):
                        found_some = True
                        release_em(node)
            if not found_some:
                # So let's see that we address the parents...
                for node in list(kernel.elements.elems(emphasized=True)):
                    if node is not None:
                        if hasattr(node, "parent"):
                            if hasattr(node.parent, "type"):
                                if node.parent.type in ("group", "file"):
                                    release_em(node.parent)

        def part_of_group():
            result = False
            for node in list(kernel.elements.elems(emphasized=True)):
                if hasattr(node, "parent"):
                    if node.parent.type in ("group", "file"):
                        result = True
                        break
            return result

        kernel.register(
            "button/group/Ungroup",
            {
                "label": _("Ungroup"),
                "icon": icons8_ungroup_objects,
                "tip": _("Ungroup elements"),
                "help": "group",
                "action": lambda v: ungroup_selection(),
                "size": bsize_normal,
                "rule_enabled": lambda cond: part_of_group(),
            },
        )

        kernel.register(
            "button/align/AlignLeft",
            {
                "label": _("Left"),
                "icon": icon_mk_align_left,
                "tip": _(
                    "Align selected elements at the leftmost position (right click: of the bed)"
                ),
                "help": "alignment",
                "action": lambda v: kernel.elements(
                    "align push first individual left pop\n"
                ),
                "action_right": lambda v: kernel.elements(
                    "align push bed group left pop\n"
                ),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )

        kernel.register(
            "button/preparation/Wordlist",
            {
                "label": _("Wordlist"),
                "icon": icons8_curly_brackets,
                "tip": _("Manages Wordlist-Entries")
                + "\n"
                + _(" (right go to next entry)"),
                "help": "wordlist",
                "action": lambda v: kernel.console("window toggle Wordlist\n"),
                "identifier": "prep_wordlist",
                "priority": 99,
                "default": "prep_wordlist_edit",
                "multi": [
                    {
                        "identifier": "prep_wordlist_edit",
                        "icon": icons8_curly_brackets,
                        "tip": _("Manages Wordlist-Entries")
                        + _(" (right go to next entry)"),
                        "label": _("Wordlist Editor"),
                        "help": "wordlist",
                        "action": lambda v: kernel.console("window toggle Wordlist\n"),
                        "action_right": lambda v: kernel.elements.wordlist_advance(1),
                    },
                    {
                        "identifier": "prep_wordlist_plus_1",
                        "icon": icons8_circled_right,
                        "tip": _("Wordlist: go to next entry")
                        + _(" (right go to prev entry)"),
                        "help": "wordlist",
                        "label": _("Next"),
                        "action": lambda v: kernel.elements.wordlist_advance(1),
                        "action_right": lambda v: kernel.elements.wordlist_advance(-1),
                    },
                    {
                        "identifier": "prep_wordlist_minus_1",
                        "label": _("Prev"),
                        "icon": icons8_circled_left,
                        "tip": _("Wordlist: go to prev entry")
                        + _(" (right go to next entry)"),
                        "help": "wordlist",
                        "action": lambda v: kernel.elements.wordlist_advance(-1),
                        "action_right": lambda v: kernel.elements.wordlist_advance(1),
                    },
                ],
            },
        )

        # Default Size for small buttons
        buttonsize = STD_ICON_SIZE / 2

        kernel.register(
            "button/align/AlignRight",
            {
                "label": _("Right"),
                "icon": icon_mk_align_right,
                "tip": _(
                    "Align selected elements at the rightmost position (right click: of the bed)"
                ),
                "help": "alignment",
                "action": lambda v: kernel.elements("align first right\n"),
                "action_right": lambda v: kernel.elements("align bed group right\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/align/AlignTop",
            {
                "label": _("Top"),
                "icon": icon_mk_align_top,
                "tip": _(
                    "Align selected elements at the topmost position (right click: of the bed)"
                ),
                "help": "alignment",
                "action": lambda v: kernel.elements("align first top\n"),
                "action_right": lambda v: kernel.elements("align bed group top\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/align/AlignBottom",
            {
                "label": _("Bottom"),
                "icon": icon_mk_align_bottom,
                "tip": _(
                    "Align selected elements at the lowest position (right click: of the bed)"
                ),
                "help": "alignment",
                "action": lambda v: kernel.elements("align first bottom\n"),
                "action_right": lambda v: kernel.elements("align bed group bottom\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/align/AlignCenterH",
            {
                "label": _("Center X"),
                "icon": icons8_centerh,
                "tip": _(
                    "Align selected elements at their center horizontally (right click: of the bed)"
                ),
                "help": "alignment",
                "action": lambda v: kernel.elements("align first centerh\n"),
                "action_right": lambda v: kernel.elements("align bed group centerh\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/align/AlignCenterV",
            {
                "label": _("Center Y"),
                "icon": icons8_centerv,
                "tip": _(
                    "Align selected elements at their center vertically (right click: of the bed)"
                ),
                "help": "alignment",
                "action": lambda v: kernel.elements("align first centerv\n"),
                "action_right": lambda v: kernel.elements("align bed group centerv\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
        kernel.register(
            "button/align/AlignHorizontally",
            {
                "label": _("Distr. Hor."),
                "icon": icons_evenspace_horiz,
                "tip": _("Distribute Space Horizontally")
                + "\n"
                + _("Left click: Equal distances")
                + "\n"
                + _("Right click: Equal centers"),
                "help": "alignment",
                "action": lambda v: kernel.elements("align spaceh\n"),
                "action_right": lambda v: kernel.elements("align spaceh2\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 2,
            },
        )
        kernel.register(
            "button/align/AlignVertically",
            {
                "label": _("Distr. Vert."),
                "icon": icons_evenspace_vert,
                "tip": _("Distribute Space Vertically")
                + "\n"
                + _("Left click: Equal distances")
                + "\n"
                + _("Right click: Equal centers"),
                "help": "alignment",
                "action": lambda v: kernel.elements("align spacev\n"),
                "action_right": lambda v: kernel.elements("align spacev2\n"),
                "size": bsize_small,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 2,
            },
        )

    def window_menu(self):
        return False

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
                matrix = Matrix(m)
                unit_width = context.device.view.unit_width
                unit_height = context.device.view.unit_height
                matrix.render(ppi=UNITS_PER_INCH, width=unit_width, height=unit_height)
                if matrix.is_identity():
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
                            element.matrix *= matrix
                            element.modified()
                        except AttributeError:
                            pass

        @context.console_command("dialog_flip", hidden=True)
        def flip(**kwargs):
            dlg = wx.TextEntryDialog(
                gui,
                _(
                    "Material must be jigged at 0,0.\nHow wide is your material (give units: in, mm, cm, px, etc)?"
                ),
                _("Double Side Flip"),
                "",
            )
            dlg.SetValue("")
            if dlg.ShowModal() == wx.ID_OK:
                unit_width = context.device.view.unit_width
                length = float(Length(dlg.GetValue(), relative_length=unit_width))
                matrix = Matrix()
                matrix.post_scale(-1.0, 1, length / 2.0, 0)
                for element in context.elements.elems(emphasized=True):
                    try:
                        element.matrix *= matrix
                        element.modified()
                    except AttributeError:
                        pass
            dlg.Destroy()

        @context.console_command("dialog_path", hidden=True)
        def dialog_path(**kwargs):
            dlg = wx.TextEntryDialog(gui, _("Enter SVG Path Data"), _("Path Entry"), "")
            dlg.SetValue("")

            if dlg.ShowModal() == wx.ID_OK:
                path = Path(dlg.GetValue())
                path.stroke = "blue"
                p = abs(path)
                node = context.elements.elem_branch.add(path=p, type="elem path")
                context.elements.classify([node])
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
                    elem.altered()

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
                    elem.altered()

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
                idx = fileDialog.GetFilterIndex()
                preferred_loader = None
                if idx > 0:
                    lidx = 0
                    for loader, loader_name, sname in context.kernel.find("load"):
                        lidx += 1
                        if lidx == idx:
                            preferred_loader = loader_name
                            break
                pathname = fileDialog.GetPath()
                gui.clear_and_open(pathname, preferred_loader=preferred_loader)

        @context.console_command("dialog_import", hidden=True)
        def import_dialog(**kwargs):
            files = context.elements.load_types()
            with wx.FileDialog(
                gui,
                _("Import"),
                wildcard=files,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                idx = fileDialog.GetFilterIndex()
                preferred_loader = None
                if idx > 0:
                    lidx = 0
                    for loader, loader_name, sname in context.kernel.find("load"):
                        lidx += 1
                        if lidx == idx:
                            preferred_loader = loader_name
                            break
                pathname = fileDialog.GetPath()
                gui.load(pathname, preferred_loader)

        @context.console_option("quit", "q", action="store_true", type=bool)
        @context.console_command("dialog_save_as", hidden=True)
        def save_dialog(quit=False, **kwargs):
            filetypes = []
            types = []
            for saver, save_name, sname in context.find("save"):
                for save_type in saver.save_types():
                    types.append(save_type)
                    description, extension, mimetype, version = save_type
                    filetypes.append(f"{description} ({extension})")
                    filetypes.append(f"*.{extension}")
            files = "|".join(filetypes)

            with wx.FileDialog(
                gui,
                _("Save Project"),
                wildcard=files,
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return
                description, extension, mimetype, version = types[
                    fileDialog.GetFilterIndex()
                ]
                pathname = fileDialog.GetPath()
                if not pathname.lower().endswith(f".{extension}"):
                    pathname += f".{extension}"
                try:
                    context.elements.save(pathname, version=version)
                    gui.validate_save()
                    gui.working_file = pathname
                    gui.set_file_as_recently_used(gui.working_file)
                except OSError as e:
                    dlg = wx.MessageDialog(
                        None,
                        str(e),
                        _("Saving Failed"),
                        wx.OK | wx.ICON_WARNING,
                    )
                    dlg.ShowModal()
                    dlg.Destroy()
                else:
                    if quit:
                        context("quit\n")

        @context.console_option("quit", "q", action="store_true", type=bool)
        @context.console_command("dialog_save", hidden=True)
        def save_or_save_as(quit=False, **kwargs):
            if gui.working_file is None:
                if quit:
                    context(".dialog_save_as -q\n")
                else:
                    context(".dialog_save_as\n")
            else:
                try:
                    gui.set_file_as_recently_used(gui.working_file)
                    gui.validate_save()
                    context.elements.save(gui.working_file)
                except OSError as e:
                    dlg = wx.MessageDialog(
                        None,
                        str(e),
                        _("Saving Failed"),
                        wx.OK | wx.ICON_WARNING,
                    )
                    dlg.ShowModal()
                    dlg.Destroy()

    def __set_panes(self):
        self.context.setting(bool, "pane_lock", False)

        for register_panel in list(self.context.lookup_all("wxpane")):
            register_panel(self, self.context)

        # AUI Manager Update.
        self._mgr.Update()

        self.default_aui = self._mgr.SavePerspective()
        self.context.setting(str, "aui")
        self.context.setting(str, "aui_version", self.context.kernel.version)
        if self.context.aui is not None:
            # The aui_version will be set on init or reset. This can be used to set resets after specific versions.
            # if self.context.kernel.version == self.context.aui_version:
            self._mgr.LoadPerspective(self.context.aui)

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

        @context.console_argument("configuration", help=_("configuration to load"))
        @context.console_command(
            "load",
            input_type="panes",
            help=_("load pane configuration"),
            all_arguments_required=True,
        )
        def load_pane(command, _, channel, configuration=None, **kwargs):
            aui = context.setting(str, f"aui_{configuration}", None)
            if not aui:
                channel(_("Perspective not found"))
                return
            self.on_panes_closed()
            self._mgr.LoadPerspective(aui, update=True)
            self.on_config_panes()

        @context.console_argument("configuration", help=_("configuration to load"))
        @context.console_command(
            "save",
            input_type="panes",
            help=_("load pane configuration"),
            all_arguments_required=True,
        )
        def save_pane(command, _, channel, configuration=None, **kwargs):
            setattr(context, f"aui_{configuration}", self._mgr.SavePerspective())

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
            pane = self._mgr.GetPane(_pane.name)
            if len(pane.name):
                if not pane.IsShown():
                    pane.Show()
                    pane.CaptionVisible(not self.context.pane_lock)
                    if hasattr(pane.window, "pane_show"):
                        pane.window.pane_show()
                        wx.CallAfter(self.on_pane_changed, None)
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
            pane = self._mgr.GetPane(_pane.name)
            if len(pane.name):
                if pane.IsShown():
                    pane.Hide()
                    if hasattr(pane.window, "pane_hide"):
                        pane.window.pane_hide()
                        wx.CallAfter(self.on_pane_changed, None)
                    self._mgr.Update()

        @context.console_option("always", "a", type=bool, action="store_true")
        @context.console_argument("pane", help=_("pane to be float"))
        @context.console_command(
            "float",
            input_type="panes",
            help=_("Float the pane"),
            all_arguments_required=True,
        )
        def float_pane(command, _, channel, always=False, pane=None, **kwargs):
            _pane = context.lookup("pane", pane)
            if _pane is None:
                channel(_("Pane not found."))
                return
            pane = self._mgr.GetPane(_pane.name)
            if len(pane.name):
                if pane.IsShown():
                    pane.Float()
                    pane.Dockable(not always)
                    pane.CaptionVisible(not self.context.pane_lock)
                    self._mgr.Update()

        @context.console_argument("pane", help=_("pane to be dock"))
        @context.console_command(
            "dock",
            input_type="panes",
            help=_("Dock the pane"),
            all_arguments_required=True,
        )
        def dock_pane(command, _, channel, pane=None, **kwargs):
            _pane = context.lookup("pane", pane)
            if _pane is None:
                channel(_("Pane not found."))
                return
            pane = self._mgr.GetPane(_pane.name)
            if len(pane.name):
                if pane.IsShown():
                    pane.Dockable(True)
                    pane.Dock()
                    pane.CaptionVisible(not self.context.pane_lock)
                    self._mgr.Update()

        @context.console_command(
            "toggleui",
            input_type="panes",
            help=_("Hides/Restores all the visible panes (except scene)"),
        )
        def toggle_ui(command, _, channel, pane=None, **kwargs):
            # Toggle visibility of all UI-elements
            self.ui_visible = not self.ui_visible

            if self.ui_visible:
                for pane_name in self.hidden_panes:
                    pane = self._mgr.GetPane(pane_name)
                    pane.Show()
                self._mgr.Update()
                channel(_("Panes restored."))
            else:
                self.hidden_panes = []
                for pane in self._mgr.GetAllPanes():
                    if pane.IsShown():
                        if pane.name == "scene":
                            # Scene remains
                            pass
                        else:
                            self.hidden_panes.append(pane.name)
                            pane.Hide()
                self._mgr.Update()
                channel(_("Panes hidden."))

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
                from .preferences import PreferencesMain as CreatePanel

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
            self.on_pane_create(_pane)
            if hasattr(panel, "pane_show"):
                panel.pane_show()
            self.context.register("pane/about", _pane)
            self._mgr.Update()

    def on_pane_reset(self, event=None):
        self.on_panes_closed()
        self._mgr.LoadPerspective(self.default_aui, update=True)
        self.context.aui_version = self.context.kernel.version
        self.on_config_panes()

    def on_panes_closed(self):
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

    def on_panes_opened(self):
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

    def on_config_panes(self):
        self.on_panes_opened()
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

    def on_pane_create(self, paneinfo: aui.AuiPaneInfo):
        control = paneinfo.control
        if isinstance(control, wx.aui.AuiNotebook):
            for i in range(control.GetPageCount()):
                page = control.GetPage(i)
                self.add_module_delegate(page)
        else:
            self.add_module_delegate(control)
        paneinfo.manager = self._mgr
        self.on_pane_show(paneinfo)

    def on_pane_show(self, paneinfo: aui.AuiPaneInfo):
        pane = self._mgr.GetPane(paneinfo.name)
        if len(pane.name):
            if not pane.IsShown():
                pane.Show()
                pane.CaptionVisible(not self.context.pane_lock)
                if hasattr(pane.window, "pane_show"):
                    pane.window.pane_show()
                    wx.CallAfter(self.on_pane_changed, None)
                self._mgr.Update()
            return
        control = paneinfo.control
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
        # try:
        #     res = wx.SystemSettings().GetAppearance().IsDark()
        # except AttributeError:
        #     res = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        res = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        return res

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
        if hasattr(context.kernel.busyinfo, "reparent"):
            context.kernel.busyinfo.reparent(self)

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
                self.on_pane_show(pane_init)

            return toggle

        def unsorted_label(original):
            # Special sort key just to sort stuff - we fix the preceeding "_sortcriteria_Correct label"
            result = original
            if result.startswith("_"):
                idx = result.find("_", 1)
                if idx >= 0:
                    result = result[idx + 1 :]
            elif result.startswith("~"):
                result = result[1:]
            return result

        self.panes_menu = wx.Menu()
        label = _("Panes")
        index = self.main_menubar.FindMenu(label)
        if index != -1:
            self.main_menubar.Replace(index, self.panes_menu, label)
        else:
            self.main_menubar.Append(self.panes_menu, label)
        submenus = {}
        panedata = []
        for pane, _path, suffix_path in self.context.find("pane/.*"):
            try:
                suppress = pane.hide_menu
                if suppress:
                    continue
            except AttributeError:
                pass
            try:
                submenu = pane.submenu
            except AttributeError:
                submenu = ""
            if submenu == "":
                submenu = "_ZZZZZZZZZZZZZZZZ_"
            panedata.append([pane, _path, suffix_path, submenu])
        panedata.sort(key=lambda row: row[3])
        for pane, _path, suffix_path, dummy in panedata:
            submenu = None
            try:
                submenu_name = pane.submenu
                submenu_name = unsorted_label(submenu_name)
                if submenu_name == "":
                    submenu_name = None
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

            menu_item = menu_context.Append(wx.ID_ANY, pane_caption, "", wx.ITEM_CHECK)
            self.Bind(
                wx.EVT_MENU,
                toggle_pane(pane_name),
                id=menu_item.GetId(),
            )
            pane = self._mgr.GetPane(pane_name)
            try:
                menu_item.Check(pane.IsShown())
                pane.window.check = menu_item.Check
            except AttributeError:
                pass

        self.panes_menu.AppendSeparator()
        item = self.main_menubar.lockpane = self.panes_menu.Append(
            wx.ID_ANY, _("Lock Panes"), "", wx.ITEM_CHECK
        )
        item.Check(self.context.pane_lock)
        self.Bind(
            wx.EVT_MENU,
            self.on_pane_lock,
            id=item.GetId(),
        )

        self.panes_menu.AppendSeparator()
        self.main_menubar.panereset = self.panes_menu.Append(
            wx.ID_ANY, _("Reset Panes"), ""
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_pane_reset,
            id=self.main_menubar.panereset.GetId(),
        )

    @lookup_listener("window")
    def dynamic_fill_window_menu(self, new=None, old=None):
        def toggle_window(_window):
            def toggle(event=None):
                self.context(f"window toggle {_window}\n")

            return toggle

        def unsorted_label(original):
            # Special sort key just to sort stuff - we fix the preceeding "_sortcriteria_Correct label"
            result = original
            if result.startswith("_"):
                idx = result.find("_", 1)
                if idx >= 0:
                    result = result[idx + 1 :]
            return result

        label = _("Tools")
        self.window_menu = wx.Menu()
        index = self.main_menubar.FindMenu(label)
        if index != -1:
            self.main_menubar.Replace(index, self.window_menu, label)
        else:
            self.main_menubar.Append(self.window_menu, label)

        submenus = {}
        menudata = []
        for window, _path, suffix_path in self.context.find("window/.*"):
            suppress = False
            try:
                name = window.name
            except AttributeError:
                name = suffix_path
            if not window.window_menu(None):
                continue
            win_caption = ""
            try:
                returnvalue = window.submenu()
                if isinstance(returnvalue, str):
                    submenu_name = returnvalue
                elif isinstance(returnvalue, (tuple, list)):
                    if len(returnvalue) > 0:
                        submenu_name = returnvalue[0]
                    if len(returnvalue) > 1:
                        win_caption = returnvalue[1]
                    if len(returnvalue) > 2:
                        suppress = returnvalue[2]
                if submenu_name is None:
                    submenu_name = ""
                if win_caption is None:
                    win_caption = ""
            except AttributeError:
                submenu_name = ""
            if submenu_name == "":
                submenu_name = "_ZZZZZZZZZZZZZZZZ_"
            if win_caption != "":
                caption = win_caption
            else:
                try:
                    caption = window.caption
                except AttributeError:
                    caption = name[0].upper() + name[1:]
            if name in ("Scene", "About"):  # make no sense, so we omit these...
                suppress = True
            if suppress:
                continue
            menudata.append([submenu_name, caption, name, window, suffix_path])
        # Now that we have everything lets sort...
        menudata.sort(key=lambda row: row[0])

        for submenu_name, caption, name, window, suffix_path in menudata:
            submenu = None
            submenu_name = unsorted_label(submenu_name)
            if submenu_name != "":
                if submenu_name in submenus:
                    submenu = submenus[submenu_name]
                elif submenu_name is not None:
                    submenu = wx.Menu()
                    self.window_menu.AppendSubMenu(submenu, _(submenu_name))
                    submenus[submenu_name] = submenu
            menu_context = submenu if submenu is not None else self.window_menu
            # print ("Menu - Name: %s, Caption=%s" % (name, caption))
            caption = _(caption)
            menu_label = caption
            if hasattr(window, "menu_label"):
                menu_label = window.menu_label()

            menu_id = wx.ID_ANY
            if hasattr(window, "menu_id"):
                menu_id = window.menu_id()

            menu_tip = ""
            if hasattr(window, "menu_tip"):
                menu_tip = window.menu_tip()

            menuitem = menu_context.Append(
                menu_id, menu_label, menu_tip, wx.ITEM_NORMAL
            )
            self.Bind(
                wx.EVT_MENU,
                toggle_window(suffix_path),
                id=menuitem.GetId(),
            )

        self.window_menu.AppendSeparator()
        # If the Main-window has disappeared out of sight (i.e. on a multi-monitor environment)
        # then resetting windows becomes difficult, so a shortcut is in order...
        # REVISED: CTRL-W is needed for mac close-window
        self.window_menu.windowreset = self.window_menu.Append(
            wx.ID_ANY, _("Reset Windows"), ""
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window reset *\n"),
            id=self.window_menu.windowreset.GetId(),
        )

    def __set_menubars(self):
        self.__set_file_menu()
        self.__set_edit_menu()
        self.__set_view_menu()
        self.__set_pane_menu()
        self.__set_tool_menu()
        self.__set_window_menu()
        self.__set_help_menu()
        self.add_language_menu()

    def _create_menu_from_choices(self, startmenu, choices):
        current_menu = startmenu
        prev_menu = startmenu
        current_segment = ""
        current_subsegment = ""
        current_level = 1
        for choice in choices:
            try:
                c_level = choice["level"]
                if c_level < 1:
                    c_level = 1
            except KeyError:
                c_level = 1

            c_segment = choice.get("segment", "")
            c_subsegment = choice.get("subsegment", "")
            c_label = choice.get("label", "")
            c_help = choice.get("help", "")
            c_action = choice.get("action")
            c_criteria = choice.get("criteria")
            c_enabled = choice.get("enabled")
            c_segment = choice.get("segment", "")
            c_param = choice.get("parameter")
            c_text_color = choice.get("text_color")
            c_id = choice.get("id", wx.ID_ANY)
            if c_segment != current_segment:
                current_segment = c_segment
                current_subsegment = ""
                # Go back to start
                if c_level != current_level and current_level > 1:
                    current_level = 1
                    current_menu = startmenu
                    prev_menu = startmenu

                if c_level > current_level:
                    prev_menu = current_menu
                    current_menu = wx.Menu()
                    prev_menu.AppendSubMenu(current_menu, _(c_segment))
                else:
                    current_menu.AppendSeparator()

            if c_subsegment != current_subsegment:
                current_subsegment = c_subsegment
                if current_level != c_level:
                    # New submenu
                    if c_subsegment == "":
                        current_menu.AppendSeparator()
                        c_level = current_level
                    else:
                        prev_menu = current_menu
                        current_menu = wx.Menu()
                        prev_menu.AppendSubMenu(current_menu, _(c_subsegment))
                else:
                    if c_subsegment == "":
                        current_menu.AppendSeparator()

            current_level = c_level
            if c_label == "":
                current_menu.AppendSeparator()
            else:
                if c_criteria is None:
                    menu_item = current_menu.Append(
                        c_id,
                        c_label,
                        c_help,
                        wx.ITEM_NORMAL,
                    )
                else:
                    menu_item = current_menu.Append(
                        c_id,
                        c_label,
                        c_help,
                        wx.ITEM_CHECK,
                    )
                    menu_item.Check(c_criteria)
                choice["menu_item"] = menu_item
                if c_text_color:
                    menu_item.SetTextColour(c_text_color)
                # flag = True
                # if c_enabled is not None:
                #     try:
                #         flag = bool(c_enabled())
                #     except (AttributeError, TypeError):
                #         pass
                # if not flag:
                #     menu_item.Enable(flag)

                def deal_with(routine, parameter=None):
                    def done(event):
                        if parameter is None:
                            routine()
                        else:
                            routine(parameter)
                        return

                    return done

                if c_action is None:
                    menu_item.Enable(False)
                else:
                    self.Bind(
                        wx.EVT_MENU, deal_with(c_action, c_param), id=menu_item.GetId()
                    )

    def __set_file_menu(self):
        self.file_menu = wx.Menu()
        # ==========
        # FILE MENU
        # ==========

        menu_item = self.file_menu.Append(
            wx.ID_NEW, _("&New\tCtrl-N"), _("Clear Operations, Elements and Notes")
        )
        self.Bind(wx.EVT_MENU, self.on_click_new, id=wx.ID_NEW)

        self.file_menu.Append(
            wx.ID_OPEN,
            _("&Open Project\tCtrl-O"),
            _("Clear existing elements and notes and open a new file"),
        )
        self.Bind(wx.EVT_MENU, self.on_click_open, id=wx.ID_OPEN)

        self.recent_file_menu = wx.Menu()
        if not getattr(sys, "frozen", False) or platform.system() != "Darwin":
            self.file_menu.AppendSubMenu(self.recent_file_menu, _("&Recent"))
        menu_item = self.file_menu.Append(
            wx.ID_ANY,
            _("&Import File"),
            _("Import another file into the same project"),
        )
        self.Bind(wx.EVT_MENU, self.on_click_import, id=menu_item.GetId())
        self.file_menu.AppendSeparator()
        menu_item = self.file_menu.Append(
            wx.ID_SAVE,
            _("&Save\tCtrl-S"),
            _("Save the project as an SVG file (overwriting any existing file)"),
        )
        self.Bind(wx.EVT_MENU, self.on_click_save, id=wx.ID_SAVE)
        menu_item = self.file_menu.Append(
            wx.ID_SAVEAS,
            _("Save &As\tCtrl-Shift-S"),
            _("Save the project in a new SVG file"),
        )
        self.Bind(wx.EVT_MENU, self.on_click_save_as, id=wx.ID_SAVEAS)
        self.file_menu.AppendSeparator()
        if platform.system() == "Darwin":
            menu_item = self.file_menu.Append(
                wx.ID_CLOSE, _("&Close Window\tCtrl-W"), _("Close Meerk40t")
            )
            self.Bind(wx.EVT_MENU, self.on_click_close, id=menu_item.GetId())

        menu_item = self.file_menu.Append(wx.ID_EXIT, _("E&xit"), _("Close Meerk40t"))
        self.Bind(wx.EVT_MENU, self.on_click_exit, id=menu_item.GetId())
        self.main_menubar.Append(self.file_menu, _("File"))

    def _update_status_menu(self, menu, choices, *args):
        def handler(event):
            for entry in local_choices:
                if "label" in entry and "enabled" in entry:
                    flag = True
                    label = entry["label"]
                    try:
                        flag = bool(entry["enabled"]())
                    except AttributeError:
                        flag = True
                    if label:
                        menu_id = local_menu.FindItem(label)
                        if menu_id != wx.NOT_FOUND:
                            menu_item = local_menu.FindItemById(menu_id)
                            menu_item.Enable(flag)
            if event:
                event.Skip()

        local_menu = menu
        local_choices = choices
        return handler

    def __set_edit_menu(self):
        """
        Edit MENU
        """
        self.edit_menu = wx.Menu()
        self._create_menu_from_choices(self.edit_menu, self.edit_menu_choice)
        label = _("Edit")
        index = self.main_menubar.FindMenu(label)
        if index != -1:
            self.main_menubar.Replace(index, self.edit_menu, label)
        else:
            self.main_menubar.Append(self.edit_menu, label)

        self.edit_menu.Bind(
            wx.EVT_MENU_OPEN,
            self._update_status_menu(self.edit_menu, self.edit_menu_choice),
        )

    def __set_view_menu(self):
        def toggle_draw_mode(bits):
            """
            Toggle the draw mode.
            @param bits: Bit to toggle.
            """
            self.context.draw_mode ^= bits
            self.context.signal("draw_mode", self.context.draw_mode)
            self.context.elements.modified()
            self.context.signal("refresh_scene", "Scene")
            self.context.signal("theme")

        # ==========
        # VIEW MENU
        # ==========
        self.context.setting(int, "draw_mode", 0)
        choices = [
            {
                "label": _("Zoom &Out\tCtrl--"),
                "help": _("Make the scene smaller"),
                "action": self.on_click_zoom_out,
                "id": wx.ID_ZOOM_OUT,
                "level": 1,
                "segment": "",
            },
            {
                "label": _("Zoom &In\tCtrl-+"),
                "help": _("Make the scene larger"),
                "action": self.on_click_zoom_in,
                "id": wx.ID_ZOOM_IN,
                "level": 1,
                "segment": "",
            },
            {
                "label": _("Zoom to &Selected\tCtrl-Shift-B"),
                "help": _("Fill the scene area with the selected elements"),
                "action": self.on_click_zoom_selected,
                "id": wx.ID_ZOOM_100,
                "level": 1,
                "enabled": self.context.elements.has_emphasis,
                "segment": "",
            },
            {
                "label": _("Zoom to &Bed\tCtrl-B"),
                "help": _("View the whole laser bed"),
                "action": self.on_click_zoom_bed,
                "id": wx.ID_ZOOM_FIT,
                "level": 1,
                "segment": "",
            },
            {
                "label": "",
                "level": 1,
                "segment": "",
            },
            {
                "label": _("GUI-Elements"),
                "level": 2,
                "segment": "GUI Appearance",
            },
            {
                "label": _("Show/Hide UI-Panels\tCtrl-U"),
                "help": _("Show/Hide all panels/ribbon bar"),
                "action": self.on_click_toggle_ui,
                "level": 2,
                "segment": "GUI Appearance",
                "subsegment": "GUI",
            },
            {
                "label": _("Hide Icons"),
                "help": _("Don't use icons in the tree"),
                "criteria": self.context.draw_mode & DRAW_MODE_ICONS != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_ICONS,
                "level": 2,
                "segment": "GUI Appearance",
                "subsegment": "Tree",
            },
            ### Scene-Appearance
            {
                "label": _("Hide Origin-Indicator"),
                "help": _("Don't show the origin indicator"),
                "criteria": self.context.draw_mode & DRAW_MODE_ORIGIN != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_ORIGIN,
                "level": 2,
                "segment": "Scene Appearance",
                "subsegment": "Scene",
            },
            {
                "label": _("Hide Grid"),
                "help": _("Don't show the sizing grid"),
                "criteria": self.context.draw_mode & DRAW_MODE_GRID != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_GRID,
                "level": 2,
                "segment": "Scene Appearance",
                "subsegment": "Scene",
            },
            {
                "label": _("Hide Background"),
                "help": _("Don't show any background image"),
                "criteria": self.context.draw_mode & DRAW_MODE_BACKGROUND != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_BACKGROUND,
                "level": 2,
                "segment": "Scene Appearance",
                "subsegment": "Scene",
            },
            {
                "label": _("Hide Guides"),
                "help": _("Don't show the measurement guides"),
                "criteria": self.context.draw_mode & DRAW_MODE_GUIDES != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_GUIDES,
                "level": 2,
                "segment": "Scene Appearance",
                "subsegment": "Scene",
            },
            {
                "label": _("Hide Regmarks"),
                "help": _("Don't show elements under the regmark branch"),
                "criteria": self.context.draw_mode & DRAW_MODE_REGMARKS != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_REGMARKS,
                "level": 2,
                "segment": "Scene Appearance",
            },
            {
                "label": _("Hide Laserpath"),
                "help": _(
                    "Don't show the path that the laserhead has followed (blue line)"
                ),
                "criteria": self.context.draw_mode & DRAW_MODE_LASERPATH != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_LASERPATH,
                "level": 2,
                "segment": "Scene Appearance",
            },
            {
                "label": _("Hide Reticle"),
                "help": _(
                    "Don't show the small read circle showing the current laserhead position"
                ),
                "criteria": self.context.draw_mode & DRAW_MODE_RETICLE != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_RETICLE,
                "level": 2,
                "segment": "Scene Appearance",
            },
            {
                "label": _("Do Not Alpha/Black Images"),
                "help": _("Don't preprocess images for display, i.e. keep color"),
                "criteria": self.context.draw_mode & DRAW_MODE_ALPHABLACK != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_ALPHABLACK,
                "level": 3,
                "segment": "Scene Appearance",
                "subsegment": "Display Options",
            },
            {
                "label": _("Do Not Cache Image"),
                "help": _("Forces a recalculation of nodes when drawing"),
                "criteria": self.context.draw_mode & DRAW_MODE_CACHE != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_CACHE,
                "level": 3,
                "segment": "Scene Appearance",
                "subsegment": "Display Options",
            },
            {
                "label": _("Do Not Animate"),
                "help": _("Don't use animations when zooming"),
                "criteria": self.context.draw_mode & DRAW_MODE_ANIMATE != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_ANIMATE,
                "level": 3,
                "segment": "Scene Appearance",
                "subsegment": "Display Options",
            },
            {
                "label": _("Invert"),
                "help": _("Show a negative image of the scene by inverting colours"),
                "criteria": self.context.draw_mode & DRAW_MODE_INVERT != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_INVERT,
                "level": 3,
                "segment": "Scene Appearance",
                "subsegment": "Display Options",
            },
            {
                "label": _("Flip XY"),
                "help": _("Effectively rotate the scene display by 180 degrees"),
                "criteria": self.context.draw_mode & DRAW_MODE_FLIPXY != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_FLIPXY,
                "level": 3,
                "segment": "Scene Appearance",
                "subsegment": "Display Options",
            },
            ## This will confuse the hell out of people, so omitted...
            # {
            #     "label": _("Do Not Refresh"),
            #     "help": _("Don't refresh the scene when requested"),
            #     "criteria": self.context.draw_mode & DRAW_MODE_REFRESH != 0,
            #     "action": toggle_draw_mode,
            #     "parameter": DRAW_MODE_REFRESH,
            #     "level": 3,
            #     "segment": "Scene Appearance",
            #     "subsegment": "Display Options",
            # },
            ### Render-Options
            ###    Element Display
            {
                "label": _("Affect treatment of elements during render"),
                "help": _(
                    "Advanced options! Tampering with these might break your burn!"
                ),
                "segment": "Render-Options",
                "level": 2,
            },
            {
                "label": _("(both on screen and at the burn-phase)"),
                "help": _(
                    "Advanced options! Tampering with these might break your burn!"
                ),
                "segment": "Render-Options",
                "level": 2,
            },
            {
                "label": _("Hide Shapes"),
                "help": _("Don't show shapes (i.e. Rectangles, Paths etc.)"),
                "criteria": self.context.draw_mode & DRAW_MODE_PATH != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_PATH,
                "segment": "Render-Options",
                "level": 2,
            },
            {
                "label": _("Hide Text"),
                "help": _("Don't show text elements"),
                "criteria": self.context.draw_mode & DRAW_MODE_TEXT != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_TEXT,
                "segment": "Render-Options",
                "level": 2,
            },
            {
                "label": _("Hide Images"),
                "help": _("Don't show images"),
                "criteria": self.context.draw_mode & DRAW_MODE_IMAGE != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_IMAGE,
                "segment": "Render-Options",
                "level": 2,
            },
            ### Render-Options
            ###    Shape attributes
            {
                "label": _("Hide Strokes"),
                "help": _("Don't show the strokes (i.e. the edges of SVG shapes)"),
                "criteria": self.context.draw_mode & DRAW_MODE_STROKES != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_STROKES,
                "level": 3,
                "segment": "Render-Options",
                "subsegment": "Shape-Attributes",
            },
            {
                "label": _("Hide Fills"),
                "help": _("Don't show fills (i.e. the fill inside strokes)"),
                "criteria": self.context.draw_mode & DRAW_MODE_FILLS != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_FILLS,
                "level": 3,
                "segment": "Render-Options",
                "subsegment": "Shape-Attributes",
            },
            {
                "level": 3,
                "segment": "Render-Options",
                "subsegment": "Shape-Attributes",
            },
            {
                "label": _("No Stroke-Width Render"),
                "help": _("Ignore the stroke width when drawing the stroke"),
                "criteria": self.context.draw_mode & DRAW_MODE_LINEWIDTH != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_LINEWIDTH,
                "level": 3,
                "segment": "Render-Options",
                "subsegment": "Shape-Attributes",
            },
            {
                "label": _("Show Variables"),
                "help": _("Replace variables in textboxes by their 'real' content"),
                "criteria": self.context.draw_mode & DRAW_MODE_VARIABLES != 0,
                "action": toggle_draw_mode,
                "parameter": DRAW_MODE_VARIABLES,
                "level": 1,
            },
        ]

        self.view_menu = wx.Menu()
        self.view_menu_choice = choices
        self._create_menu_from_choices(self.view_menu, choices)
        self.main_menubar.Append(self.view_menu, _("View"))
        self.view_menu.Bind(
            wx.EVT_MENU_OPEN,
            self._update_status_menu(self.view_menu, self.view_menu_choice),
        )

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
                except AttributeError:
                    pass
            if not os.path.exists(_resource_path):
                try:  # Mac py2app resource
                    _resource_path = os.path.join(
                        os.environ["RESOURCEPATH"], "help/meerk40t.help"
                    )
                except KeyError:
                    pass
            if os.path.exists(_resource_path):
                os.system(f"open {_resource_path}")
            else:
                dlg = wx.MessageDialog(
                    None,
                    _('Offline help file ("{help}") was not found.').format(
                        help=_resource_path
                    ),
                    _("File Not Found"),
                    wx.OK | wx.ICON_WARNING,
                )
                dlg.ShowModal()
                dlg.Destroy()

        def online_help(event):
            # let's have a look where we are and what the associated HelpText is
            section = ""
            wind, pos = wx.FindWindowAtPointer()
            if wind is not None:
                if hasattr(wind, "GetHelpText"):
                    win = wind
                    while win is not None:
                        section = win.GetHelpText()
                        if section:
                            break
                        win = win.GetParent()
            if section is None or section == "":
                section = "GUI"
            section = section.upper()
            url = f"https://github.com/meerk40t/meerk40t/wiki/Online-Help:-{section}"
            import webbrowser

            webbrowser.open(url, new=0, autoraise=True)

        if platform.system() == "Darwin":
            menuitem = self.help_menu.Append(
                wx.ID_HELP, _("&MeerK40t Help"), _("Open the MeerK40t Mac help file")
            )
            self.Bind(wx.EVT_MENU, launch_help_osx, id=menuitem.GetId())
            menuitem = self.help_menu.Append(
                wx.ID_ANY, _("&Online Help"), _("Open the Meerk40t online wiki")
            )
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.context("webhelp help\n"),
                id=menuitem.GetId(),
            )
        else:
            menuitem = self.help_menu.Append(
                wx.ID_HELP,
                _("&Help\tF1"),
                _("Open the Meerk40t online wiki Beginners page"),
            )
            self.Bind(
                wx.EVT_MENU,
                # lambda e: self.context("webhelp help\n"),
                online_help,
                id=menuitem.GetId(),
            )

        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("Online Reference\tF11"),
            _("Display online reference"),
        )
        self.Bind(
            wx.EVT_MENU,
            online_help,
            id=menuitem.GetId(),
        )

        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("&Beginners' Help"),
            _("Open the Meerk40t online wiki Beginners page"),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp beginners\n"),
            id=menuitem.GetId(),
        )
        menuitem = self.help_menu.Append(
            wx.ID_ANY, _("&Github"), _("Visit Meerk40t's Github homepage")
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp main\n"),
            id=menuitem.GetId(),
        )
        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("&Releases"),
            _("Check for a new release on Meerk40t's Github releases page"),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp releases\n"),
            id=menuitem.GetId(),
        )
        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("&Facebook"),
            _("Get help from the K40 Meerk40t Facebook group"),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp facebook\n"),
            id=menuitem.GetId(),
        )
        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("&Discord"),
            _("Chat with developers to get help on the Meerk40t Discord server"),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp discord\n"),
            id=menuitem.GetId(),
        )
        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("&Makers Forum"),
            _("Get help from the Meerk40t page on the Makers Forum"),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp makers\n"),
            id=menuitem.GetId(),
        )
        self.help_menu.AppendSeparator()
        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("Feature request/feedback"),
            _("You feel something is missing or could be improved? Let us know..."),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context("webhelp featurerequest\n"),
            id=menuitem.GetId(),
        )
        self.help_menu.AppendSeparator()
        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("Check for Updates"),
            _("Check whether a newer version of Meerk40t is available"),
        )

        def update_check_from_menu():
            if self.context.update_check == 1:
                command = "check_for_updates --verbosity 3\n"
            elif self.context.update_check == 2:
                command = "check_for_updates --beta --verbosity 3\n"

            self.context(command)
            self.context.setting(int, "last_update_check", None)
            now = datetime.date.today()
            self.context.last_update_check = now.toordinal()

        self.Bind(
            wx.EVT_MENU,
            lambda v: update_check_from_menu(),
            id=menuitem.GetId(),
        )

        menuitem = self.help_menu.Append(
            wx.ID_ANY,
            _("Tips && Tricks"),
            _("Show some Tips & Tricks"),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window open Tips\n"),
            id=menuitem.GetId(),
        )

        menuitem = self.help_menu.Append(
            wx.ID_ABOUT,
            _("&About MeerK40t"),
            _(
                "Toggle the About window acknowledging those who contributed to creating Meerk40t"
            ),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda v: self.context("window toggle About\n"),
            id=menuitem.GetId(),
        )

        self.main_menubar.Append(self.help_menu, _("Help"))

        self.SetMenuBar(self.main_menubar)

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
                    def check(event):
                        self.context.app.update_language(q)
                        # Intentionally no translation...
                        wx.MessageBox(
                            message="This requires a program restart before the language change will kick in!",
                            caption="Language changed",
                        )
                        self.context.signal("restart")

                    return check

                self.Bind(wx.EVT_MENU, language_update(i), id=m.GetId())
                if language_code not in trans and i != 0:
                    m.Enable(False)
                i += 1
            self.main_menubar.Append(wxglade_tmp_menu, _("Languages"))

    def add_language_menu_kernel(self):
        """
        Unused kernel language menu update see issue #2103

        @return:
        """
        from ..kernel import _gettext_language

        trans = _gettext_language
        if not trans:
            trans = "en"

        wxglade_tmp_menu = wx.Menu()
        for lang in self.context.app.supported_languages:
            language_code, language_name, language_index = lang
            m = wxglade_tmp_menu.Append(
                wx.ID_ANY, language_name, language_name, wx.ITEM_RADIO
            )
            if trans == language_code:
                m.Check(True)

            def language_update(q):
                def check(event):
                    self.context.app.update_language(q)
                    # Intentionally no translation...
                    wx.MessageBox(
                        message="This requires a program restart before the language change will kick in!",
                        caption="Language changed",
                    )

                return check

            self.Bind(wx.EVT_MENU, language_update(language_code), id=m.GetId())
            # if language_code not in trans and i != 0:
            #     m.Enable(False)
        self.main_menubar.Append(wxglade_tmp_menu, _("Languages"))

    @signal_listener("warn_state_update")
    @signal_listener("updateop_tree")
    @signal_listener("tree_changed")
    @signal_listener("modified_by_tool")
    @signal_listener("device;renamed")
    @signal_listener("service/device/active")
    def warning_indicator(self, *args):
        self.warning_routine.warning_indicator()

    @signal_listener("restart")
    def on_restart_required(self, *args):
        self.context.kernel.register(
            "button/project/Restart",
            {
                "label": _("Restart"),
                "icon": icon_power_button,
                "tip": _("Restart needed to apply new parameters"),
                "action": lambda v: self.context("restart\n"),
                "size": STD_ICON_SIZE,
            },
        )

    @signal_listener("file;loaded")
    @signal_listener("file;saved")
    @signal_listener("file;cleared")
    @signal_listener("device;renamed")
    @lookup_listener("service/device/active")
    def on_active_change(self, *args):
        self.__set_titlebar()
        self.context.signal("update_group_labels")

    def window_close_veto(self):
        if self.any_device_running:
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
                self.context("dialog_save -q\n")
                return True
            if answer == wx.CANCEL:
                return True  # VETO
        return False

    def window_close(self):
        context = self.context

        context.aui = self._mgr.SavePerspective()
        self.on_panes_closed()
        self._mgr.UnInit()

        if context.print_shutdown:
            context.channel("shutdown").watch(print)
        self.context(".timer 0 1 quit\n")

    def set_needs_save_status(self, newstatus):
        self.needs_saving = newstatus
        app = self.context.app.GetTopWindow()
        if isinstance(app, wx.TopLevelWindow):
            app.OSXSetModified(self.needs_saving)

    @signal_listener("altered")
    @signal_listener("modified")
    def on_invalidate_save(self, origin, *args):
        status = True
        # Let's check whether the list of elements is empty:
        # if that's the case then we refrain from setting the status
        if len(self.context.elements.elem_branch.children) == 0:
            status = False
        self.set_needs_save_status(status)

    @signal_listener("altered")
    @signal_listener("modified")
    @signal_listener("scaled")
    def check_parametric_updates(self, origin, *args):
        def getit(param, idx, default):
            if idx >= len(param):
                return default
            return param[idx]

        def read_information():
            if self.parametric_info is None:
                self.parametric_info = {}
                for info, m, sname in self.context.kernel.find("element_update"):
                    # function, path, shortname
                    self.parametric_info[sname.lower()] = info

        # Let's check for the need of parametric updates...
        if len(args) == 0:
            return
        read_information()
        data = args[0]
        if not isinstance(data, (list, tuple)):
            data = [args[0]]
        for n in data:
            if n is None:
                continue
            if not hasattr(n, "id"):
                continue
            if n.id is None:
                continue
            nid = n.id
            for e in self.context.elements.elems():
                if not hasattr(e, "functional_parameter"):
                    continue
                param = e.functional_parameter
                if param is None:
                    continue
                ptype = getit(param, 0, None)
                if ptype is None:
                    continue
                pid = getit(param, 2, None)
                if pid != nid:
                    continue
                try:
                    func_tuple = self.parametric_info[ptype.lower()]
                    if not func_tuple[2]:  # No Autoupdate
                        func_tuple = None
                except IndexError:
                    func_tuple = None
                if func_tuple is not None:
                    try:
                        func = func_tuple[0]
                        func(e)
                    except IndexError:
                        pass

    def validate_save(self):
        self.set_needs_save_status(False)

    @signal_listener("warning")
    def on_warning_signal(self, origin, message, caption, style=None):
        if style is None:
            style = wx.OK | wx.ICON_WARNING
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

    @signal_listener("default_operations")
    def on_def_ops(self, origin, *args):
        self.main_statusbar.Signal("default_operations")

    @signal_listener("snap_grid")
    @signal_listener("snap_points")
    def on_sig_snap(self, origin, *args):
        # will be used for both
        self.main_statusbar.Signal("snap_grid")

    @signal_listener("activate;device")
    def on_device_active(self, origin, *args):
        # A new device might have new default operations...
        self.context.elements.init_default_operations_nodes()
        self.main_statusbar.Signal("default_operations")

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
    def on_cutplan_error(self, origin, error):
        dlg = wx.MessageDialog(
            None,
            _("Cut planning failed because: {error}").format(error=error),
            _("Cut Planning Failed"),
            wx.OK | wx.ICON_WARNING,
        )
        dlg.ShowModal()
        dlg.Destroy()

    @property
    def any_device_running(self):
        running = self._usb_running
        for v in running:
            q = running[v]
            if q:
                return True
        return False

    @signal_listener("pipe;running")
    def on_usb_running(self, origin, value):
        self._usb_running[origin] = value

    @signal_listener("pipe;usb_status")
    def on_usb_state_text(self, origin, value):
        self.main_statusbar.SetStatusText(
            _("Usb: {index}").format(index=value),
            1,
        )

    @signal_listener("pipe;thread")
    def on_pipe_state(self, origin, state):
        if state == self.pipe_state:
            return
        self.pipe_state = state

        self.main_statusbar.SetStatusText(
            _("Controller: {state}").format(
                state=self.context.kernel.get_text_thread_state(state)
            ),
            2,
        )

    @signal_listener("spooler;thread")
    def on_spooler_state(self, origin, value):
        self.main_statusbar.SetStatusText(
            _("Spooler: {state}").format(
                state=self.context.get_text_thread_state(value)
            ),
            3,
        )
        self.main_statusbar.Signal("spooler;thread", value)

    @signal_listener("spooler;queue")
    def on_spooler_queue_signal(self, origin, *args):
        self.main_statusbar.Signal("spooler;queue", args)

        if not self.widgets_created:
            return
        # Queue Len
        if len(args) > 0:
            value = args[0]
        else:
            value = 0
        flag = value > 0
        self.main_statusbar.activate_panel("burninfo", flag)

    @signal_listener("driver;position")
    @signal_listener("emulator;position")
    def on_device_update(self, origin, pos):
        self.main_statusbar.Signal("spooler;update")

    @signal_listener("spooler;completed")
    def on_spool_finished(self, origin, pos=None):
        self.main_statusbar.Signal("spooler;completed")

    @signal_listener("export-image")
    def on_export_signal(self, origin, frame):
        image_width, image_height, frame = frame
        if frame is not None:
            elements = self.context.elements
            img = Image.fromarray(frame)
            matrix = Matrix(f"scale({UNITS_PER_PIXEL}, {UNITS_PER_PIXEL})")
            node = elements.elem_branch.add(image=img, matrix=matrix, type="elem image")
            elements.classify([node])
            self.context.signal("refresh_scene", "Scene")

    @signal_listener("statusmsg")
    def on_update_statusmsg(self, origin, value):
        self.main_statusbar.SetStatusText(value, 0)

    @signal_listener("statusupdate")
    def on_update_statuspanel(self, origin, value=None):
        self.main_statusbar.Reposition(value)

    def __set_titlebar(self):
        label = self.context.elements.filename
        if label is None:
            label = ""
        else:
            label = " - " + label

        try:
            dev_label = self.context.device.label
        except AttributeError:
            # Label cannot be found because device does not exist.
            dev_label = ""

        title = (
            f"{str(self.context.kernel.name)} v{self.context.kernel.version} - "
            f"{dev_label}{label}"
        )
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
            idx = fileDialog.GetFilterIndex()
            preferred_loader = None
            if idx > 0:
                lidx = 0
                for loader, loader_name, sname in self.context.kernel.find("load"):
                    lidx += 1
                    if lidx == idx:
                        preferred_loader = loader_name
                        break
            pathname = fileDialog.GetPath()
            self.load(pathname, preferred_loader)

    def populate_recent_menu(self):
        if not hasattr(self, "recent_file_menu"):
            return  # No menu, cannot populate.

        context = self.context
        recents = [
            (context.file0, "&1 "),
            (context.file1, "&2 "),
            (context.file2, "&3 "),
            (context.file3, "&4 "),
            (context.file4, "&5 "),
            (context.file5, "&6 "),
            (context.file6, "&7 "),
            (context.file7, "&8 "),
            (context.file8, "&9 "),
            (context.file9, "1&0"),
            (context.file10, "11"),
            (context.file11, "12"),
            (context.file12, "13"),
            (context.file13, "14"),
            (context.file14, "15"),
            (context.file15, "16"),
            (context.file16, "17"),
            (context.file17, "18"),
            (context.file18, "19"),
            (context.file19, "20"),
        ]

        # for i in range(self.recent_file_menu.MenuItemCount):
        # self.recent_file_menu.Remove(self.recent_file_menu.FindItemByPosition(0))

        for item in self.recent_file_menu.GetMenuItems():
            self.recent_file_menu.Remove(item)

        for file, shortcode in recents:
            if file is not None and file:
                shortfile = _("Load {file}...").format(file=os.path.basename(file))
                menuitem = self.recent_file_menu.Append(
                    wx.ID_ANY, shortcode + "  " + file.replace("&", "&&"), shortfile
                )
                self.Bind(
                    wx.EVT_MENU,
                    partial(lambda f, event: self.load_or_open(f), file),
                    id=menuitem.GetId(),
                )

        if self.recent_file_menu.MenuItemCount != 0:
            self.recent_file_menu.AppendSeparator()
            menuitem = self.recent_file_menu.Append(
                wx.ID_ANY,
                _("Clear Recent"),
                _("Delete the list of recent projects"),
            )
            self.Bind(wx.EVT_MENU, lambda e: self.clear_recent(), id=menuitem.GetId())

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

    def clear_project(self, ops_too=True):
        context = self.context
        kernel = context.kernel
        kernel.busyinfo.start(msg=_("Cleaning up..."))
        self.working_file = None
        context.elements.clear_all(ops_too=ops_too)
        self.context(".laserpath_clear\n")
        self.validate_save()
        kernel.busyinfo.end()
        self.context(".tool none\n")
        context.elements.undo.mark("blank")
        self.context.signal("selected")

    def clear_and_open(self, pathname, preferred_loader=None):
        self.clear_project(ops_too=False)
        if self.load(pathname, preferred_loader):
            try:
                if self.context.uniform_svg and pathname.lower().endswith("svg"):
                    # or (len(elements) > 0 and "meerK40t" in elements[0].values):
                    # TODO: Disabled uniform_svg, no longer detecting namespace.
                    self.working_file = pathname
                    self.validate_save()
            except AttributeError:
                pass

    def load(self, pathname, preferred_loader=None):
        def unescaped(filename):
            OS_NAME = platform.system()
            if OS_NAME == "Windows":
                newstring = filename.replace("&", "&&")
            else:
                newstring = filename.replace("&", "&&")
            return newstring

        kernel = self.context.kernel
        try:
            # Reset to standard tool
            self.context("tool none\n")
            info = _("Loading File...") + "\n" + unescaped(pathname)
            kernel.busyinfo.start(msg=info)
            n = self.context.elements.note
            results = self.context.elements.load(
                pathname,
                channel=self.context.channel("load"),
                svg_ppi=self.context.elements.svg_ppi,
                preferred_loader=preferred_loader,
            )
            kernel.busyinfo.end()
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
                zl = self.context.zoom_margin
                self.context(f"scene focus -{zl}% -{zl}% {100 + zl}% {100 + zl}%\n")

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
            err_msg = _("Some files were unrecognized:\n{rejected_files}").format(
                rejected_files=reject
            )
            dlg = wx.MessageDialog(
                None, err_msg, _("Error encountered"), wx.OK | wx.ICON_ERROR
            )
            dlg.ShowModal()
            dlg.Destroy()

    def on_size(self, event):
        if self.context is None:
            return
        self.Layout()
        if self.context.autofocus_resize:
            zl = self.context.zoom_margin
            self.context(f"scene focus -{zl}% -{zl}% {100 + zl}% {100 + zl}%\n")

    def on_focus_lost(self, event):
        self.context("-laser\nend\n")
        # event.Skip()

    def on_click_new(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        self.clear_project()

    def on_click_open(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        self.context(".dialog_load\n")
        self.context(".tool none\n")

    def on_click_import(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        self.context(".dialog_import\n")
        self.context(".tool none\n")

    def on_click_stop(self, event=None):
        self.context("estop\n")

    def on_click_pause(self, event=None):
        self.context("pause\n")

    def on_click_save(self, event):
        self.context(".dialog_save\n")
        self.context(".tool none\n")

    def on_click_save_as(self, event=None):
        self.context(".dialog_save_as\n")
        self.context(".tool none\n")

    def on_click_close(self, event=None):
        try:
            # We should just rely on the try except, but let's be thorough
            topw = self.context.app.GetTopWindow()
            if topw is None:
                return
            focw = topw.FindFocus()
            if focw is None:
                return
            window = focw.GetTopLevelParent()
            if window is self or window is None:
                return
            window.Close(False)
        except (RuntimeError, AttributeError):
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
        self.context(f"scene zoom {1.0 / 1.5}\n")

    def on_click_zoom_in(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoomin button press
        """
        self.context(f"scene zoom {1.5}\n")

    def on_click_zoom_selected(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoom scene to selected items.
        """
        bbox = self.context.elements.selected_area()
        if bbox is None:
            self.on_click_zoom_bed(event=event)
        else:
            zfact = self.context.zoom_margin / 100.0

            x_delta = (bbox[2] - bbox[0]) * zfact
            y_delta = (bbox[3] - bbox[1]) * zfact
            x0 = Length(
                amount=bbox[0] - x_delta, relative_length=self.context.device.view.width
            ).length_mm
            y0 = Length(
                amount=bbox[1] - y_delta,
                relative_length=self.context.device.view.height,
            ).length_mm
            x1 = Length(
                amount=bbox[2] + x_delta, relative_length=self.context.device.view.width
            ).length_mm
            y1 = Length(
                amount=bbox[3] + y_delta,
                relative_length=self.context.device.view.height,
            ).length_mm
            self.context(f"scene focus -a {x0} {y0} {x1} {y1}\n")

    def on_click_toggle_ui(self, event=None):
        self.context("pane toggleui\n")
        zl = self.context.zoom_margin
        self.context(f"scene focus -{zl}% -{zl}% {100 + zl}% {100 + zl}%\n")

    def on_click_zoom_bed(self, event=None):  # wxGlade: MeerK40t.<event_handler>
        """
        Zoom scene to bed size.
        """
        zoom = self.context.zoom_margin
        self.context(f"scene focus -a {-zoom}% {-zoom}% {zoom+100}% {zoom+100}%\n")

    def update_statusbar(self, text):
        self.main_statusbar.SetStatusText(text, 0)

    def status_update(self):
        self.update_statusbar("")

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
        try:
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
                helptext = f'{menuitem.GetItemLabelText()} ({_("No help text")})'
            self.update_statusbar(helptext)
        except RuntimeError:
            pass
