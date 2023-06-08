"""
Simple Display. The goal here is not to create a fully fleshed out, has everything dialog but rather a simple dialog
that is small enough that it can fit in a 5in rPi touch screen display. This code is executed with --simpleui
flagged from the commandline.

See Discussion:
https://github.com/meerk40t/meerk40t/discussions/1944
"""

import wx
from wx import aui

from .icons import icons8_computer_support_50, icons8_opened_folder_50
from .mwindow import MWindow
from ..core.exceptions import BadFileError

_ = wx.GetTranslation


class ProjectPanel(wx.Panel):
    """
    Serves to allow the use of Load Project button. This couldn't be provided natively by any readily availible panel.
    """

    name = "Project"

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: Jog.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.SetSize((400, 300))

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)

        self.button_load = wx.Button(self, wx.ID_ANY, _("Load Project"))

        self.button_load.SetBitmap(icons8_opened_folder_50.GetBitmap())
        sizer_buttons.Add(self.button_load, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.SetSizer(sizer_buttons)

        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.on_load, self.button_load)
        self.Bind(wx.EVT_DROP_FILES, self.on_drop_file)
        # end wxGlade

    def on_load(self, event):  # wxGlade: MyFrame.<event_handler>
        # This code should load just specific project files rather than all importable formats.
        files = self.context.elements.load_types()
        with wx.FileDialog(
            self, _("Open"), wildcard=files, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind
            pathname = fileDialog.GetPath()
            self.clear_project()
            self.load(pathname)
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

    def load(self, pathname):
        kernel = self.context.kernel
        try:
            # Reset to standard tool
            self.context("tool none\n")
            info = _("Loading File...") + "\n" + pathname
            kernel.busyinfo.start(msg=info)
            self.context.elements.load(
                pathname,
                channel=self.context.channel("load"),
                svg_ppi=self.context.elements.svg_ppi,
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
        _icon.CopyFromBitmap(icons8_computer_support_50.GetBitmap())
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
        self.notebook_main.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_page_changed)

        self.Layout()
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
        from meerk40t.gui.navigationpanels import Jog

        kernel.register("simpleui/navigation", (Jog, {"icon_size": 20}))
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
