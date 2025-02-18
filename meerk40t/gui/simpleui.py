"""
Simple Display. The goal here is not to create a fully fleshed out, has everything dialog but rather a simple dialog
that is small enough that it can fit in a 5in rPi touch screen display. This code is executed with --simpleui
flagged from the commandline.

See Discussion:
https://github.com/meerk40t/meerk40t/discussions/1944
"""

import wx
from wx import aui

from ..core.exceptions import BadFileError
from .icons import get_default_icon_size, icons8_computer_support, icons8_opened_folder
from .mwindow import MWindow
from .navigationpanels import Drag, Jog, JogDistancePanel
from .wxutils import StaticBoxSizer, TextCtrl, wxButton, wxStaticText

_ = wx.GetTranslation


class JogMovePanel(wx.Panel):
    def __init__(self, *args, context=None, icon_size=None, **kwds):
        # begin wxGlade: Jog.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        distance_panel = JogDistancePanel(self, wx.ID_ANY, context=context)
        jog_panel = Jog(self, wx.ID_ANY, context=context)
        drag_panel = Drag(self, wx.ID_ANY, context=context)
        self.panels = [distance_panel, jog_panel, drag_panel]
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.jog_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.jog_sizer.Add(jog_panel, 1, wx.EXPAND, 0)
        self.jog_sizer.Add(drag_panel, 1, wx.EXPAND, 0)
        self.main_sizer.Add(distance_panel, 0, wx.EXPAND, 0)
        self.main_sizer.Add(self.jog_sizer, 1, wx.EXPAND, 0)
        self.SetSizer(self.main_sizer)
        self.Layout()
        self.Bind(wx.EVT_SIZE, self.on_resize)
        # Force initial resizing
        wx.CallAfter(self.on_resize)

    def on_resize(self, event=None):
        wb_size = self.jog_sizer.GetSize()
        panel_size = (wb_size[0] / 2, wb_size[1])
        for p in self.panels:
            if hasattr(p, "set_icons"):
                p.set_icons(dimension=panel_size)
        self.Layout()


class ProjectPanel(wx.Panel):
    """
    Serves to allow the use of Load Project button. This couldn't be provided natively by any readily available panel.
    """

    name = "Project"

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: Jog.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetSize((400, 300))

        sizer_buttons = wx.BoxSizer(wx.VERTICAL)

        self.button_load = wxButton(self, wx.ID_ANY, _("Load Project"))

        self.button_load.SetBitmap(
            icons8_opened_folder.GetBitmap(resize=get_default_icon_size(self.context))
        )
        info_panel = StaticBoxSizer(self, wx.ID_ANY, "Project-Information", wx.VERTICAL)
        line1 = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wxStaticText(self, wx.ID_ANY, "File:")
        lbl.SetMinSize(wx.Size(70, -1))
        self.info_file = TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        line1.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        line1.Add(self.info_file, 1, wx.EXPAND, 0)

        line2 = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wxStaticText(self, wx.ID_ANY, "Content:")
        lbl.SetMinSize(wx.Size(70, -1))
        self.info_elements = TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        self.info_operations = TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        line2.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        line2.Add(self.info_elements, 1, wx.EXPAND, 0)
        line2.Add(self.info_operations, 1, wx.EXPAND, 0)

        line3 = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wxStaticText(self, wx.ID_ANY, "Status:")
        lbl.SetMinSize(wx.Size(70, -1))
        self.info_status = TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        line3.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        line3.Add(self.info_status, 1, wx.EXPAND, 0)

        info_panel.Add(line1, 0, wx.EXPAND, 0)
        info_panel.Add(line2, 0, wx.EXPAND, 0)
        info_panel.Add(line3, 0, wx.EXPAND, 0)
        # info_panel.Add(line4, 0, wx.EXPAND, 0)
        sizer_buttons.Add(self.button_load, 0, 0, 0)
        sizer_buttons.Add(info_panel, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_buttons)

        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.on_load, self.button_load)
        self.Bind(wx.EVT_DROP_FILES, self.on_drop_file)
        # end wxGlade

    def update_info(self, pathname):
        self.info_file.SetValue(pathname)
        self.info_elements.SetValue(
            f"{len(list(self.context.elements.elems()))} elements"
        )
        self.info_operations.SetValue(
            f"{len(list(self.context.elements.ops()))} burn operations"
        )
        unass, unburn = self.context.elements.have_unburnable_elements()
        status = ""
        if unass:
            status += "Unassigned elements! "
        if unburn:
            status += "Unburnable elements! "
        if status == "":
            status = "Ready to burn."
            self.info_status.SetBackgroundColour(None)
        else:
            self.info_status.SetBackgroundColour(wx.YELLOW)
        self.info_status.SetValue(status)

    def on_load(self, event):  # wxGlade: MyFrame.<event_handler>
        # This code should load just specific project files rather than all importable formats.
        files, descriptors = self.context.elements.load_types()
        with wx.FileDialog(
            self,
            _("Open"),
            wildcard=files,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW,
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind
            idx = fileDialog.GetFilterIndex()
            try:
                preferred_loader = descriptors[idx]
            except IndexError:
                preferred_loader = None
            pathname = fileDialog.GetPath()
            self.clear_project()
            self.load(pathname, preferred_loader)
            self.update_info(pathname)
        event.Skip()

    def clear_project(self):
        context = self.context
        kernel = context.kernel
        kernel.busyinfo.start(msg=_("Cleaning up..."))
        context.elements.clear_all()
        kernel.busyinfo.end()

    def on_drop_file(self, event):
        """
        Drop file handler

        Accepts multiple files drops.
        """
        accepted = 0
        rejected = 0
        rejected_files = []
        validpath = ""
        for pathname in event.GetFiles():
            if self.load(pathname):
                accepted += 1
                if validpath:
                    validpath += ","
                validpath += pathname
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
            self.update_info(validpath)

    def load(self, pathname, preferred_loader=None):
        def unescaped(filename):
            import platform

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
            self.context.elements.load(
                pathname,
                channel=self.context.channel("load"),
                svg_ppi=self.context.elements.svg_ppi,
                preferred_loader=preferred_loader,
            )
            kernel.busyinfo.end()
            return True
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


class SimpleUI(MWindow):
    """
    This version of SimpleUI (we are not attached this, and it can be radically changed in the future) consists of a
    simple notebook of panels taken various sources.
    """

    def __init__(self, *args, **kwds):
        super().__init__(598, 429, *args, **kwds)

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_computer_support.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Navigation.__set_properties
        self.SetTitle(_("MeerK40t"))
        self.panel_instances = list()

        self.notebook_main = aui.AuiNotebook(
            self,
            -1,
            style=aui.AUI_NB_TAB_EXTERNAL_MOVE
            | aui.AUI_NB_SCROLL_BUTTONS
            | aui.AUI_NB_TAB_SPLIT
            | aui.AUI_NB_TAB_MOVE,
        )
        self.window_context.themes.set_window_colors(self.notebook_main)
        bg_std = self.window_context.themes.get("win_bg")
        bg_active = self.window_context.themes.get("highlight")
        self.notebook_main.GetArtProvider().SetColour(bg_std)
        self.notebook_main.GetArtProvider().SetActiveColour(bg_active)

        self.sizer.Add(self.notebook_main, 1, wx.EXPAND, 0)
        self.notebook_main.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_page_changed)

        self.Layout()
        self.restore_aspect(honor_initial_values=True)
        self.on_build()

    def on_page_changed(self, event):
        event.Skip()
        page = self.notebook_main.GetCurrentPage()
        if page is None:
            return
        for panel in self.panel_instances:
            try:
                if panel is page:
                    page.pane_active()
                else:
                    panel.pane_deactive()
            except AttributeError:
                pass

    def on_build(self, *args):
        self.Freeze()

        def sort_priority(ref):
            prop, kwargs = ref
            return getattr(prop, "priority") if hasattr(prop, "priority") else 0

        pages_to_instance = list()
        for prop, kwargs in self.context.lookup_all("simpleui/.*"):
            if kwargs is None:
                kwargs = dict()
            pages_to_instance.append((prop, kwargs))

        pages_to_instance.sort(key=sort_priority)

        for page, kwargs in pages_to_instance:
            page_panel = page(
                self.notebook_main, wx.ID_ANY, context=self.context, **kwargs
            )
            try:
                name = page.name
            except AttributeError:
                name = page_panel.__class__.__name__

            self.notebook_main.AddPage(page_panel, _(name))
            self.add_module_delegate(page_panel)
            self.panel_instances.append(page_panel)
            try:
                page_panel.pane_show()
            except AttributeError:
                pass
            page_panel.Layout()
            try:
                page_panel.SetupScrolling()
            except AttributeError:
                pass

        self.Layout()
        self.Thaw()

    @staticmethod
    def sub_register(kernel):
        kernel.register("simpleui/load", (ProjectPanel, None))

        # from meerk40t.gui.wxmscene import MeerK40tScenePanel
        # kernel.register("simpleui/scene", MeerK40tScenePanel)
        from meerk40t.gui.laserpanel import LaserPanel

        kernel.register("simpleui/laserpanel", (LaserPanel, None))

        kernel.register("simpleui/navigation", (JogMovePanel, None))

        from meerk40t.gui.consolepanel import ConsolePanel

        kernel.register("simpleui/console", (ConsolePanel, None))

    def window_close(self):
        context = self.context
        for p in self.panel_instances:
            try:
                p.pane_hide()
            except AttributeError:
                pass
        # We do not remove the delegates, they will detach with the closing of the module.
        self.panel_instances.clear()

        context.channel("shutdown").watch(print)
        self.context(".timer 0 1 quit\n")

    def window_menu(self):
        return False

    @staticmethod
    def submenu():
        return "Interface", "SimpleUI"

    @staticmethod
    def helptext():
        return _("A very basic user interface")
