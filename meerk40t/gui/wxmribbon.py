"""
The WxmRibbon Bar is a core aspect of MeerK40t's interaction. To allow fully dynamic buttons we use the ribbonbar
control widget built into meerk40t.

Panels are created in a static fashion within this class. But the contents of those individual ribbon panels are defined
in the kernel lookup.

    service.register(
        "button/control/Redlight",
        {
            ...<def>...
        },
    )

This setup allows us to define a large series of buttons with a button prefix and the name of a panel it should be
added to as well as a unique name. This defines within the meerk40t ecosystem a methodology of specifically creating
dynamic buttons. When the service changes because of a switch in the device (for example) it will trigger the lookup
listeners which will update their contents, triggering the update within this control.
"""

import copy
import math
import platform
import threading

import wx
from wx import aui

from meerk40t.kernel import Job, lookup_listener, signal_listener
from meerk40t.svgelements import Color

from .icons import get_default_icon_size, icons8_opened_folder_50
from .ribbon import RibbonBarPanel

_ = wx.GetTranslation

ID_PAGE_MAIN = 10
ID_PAGE_DESIGN = 20
ID_PAGE_MODIFY = 30
ID_PAGE_CONFIG = 40
ID_PAGE_TOGGLE = 99

BUFFER = 5


def register_panel_ribbon(window, context):
    iconsize = get_default_icon_size()
    minh = 3 * iconsize
    pane = (
        aui.AuiPaneInfo()
        .Name("ribbon")
        .Top()
        .RightDockable(False)
        .LeftDockable(False)
        .BestSize(300, minh)
        .FloatingSize(640, minh)
        .Caption(_("Ribbon"))
        .CaptionVisible(not context.pane_lock)
    )
    pane.dock_proportion = 640
    ribbon = MKRibbonBarPanel(window, wx.ID_ANY, context=context, pane=pane)
    pane.control = ribbon

    window.on_pane_create(pane)
    context.register("pane/ribbon", pane)

    choices = [
        {
            "attr": "ribbon_show_labels",
            "object": context,
            "default": False,
            "type": bool,
            "label": _("Show the Ribbon Labels"),
            "tip": _(
                "Active: Show the labels for ribbonbar.\n"
                "Inactive: Hide the ribbon labels."
            ),
            "page": "Gui",
            "section": "Appearance",
        },
    ]
    context.kernel.register_choices("preferences", choices)


class MKRibbonBarPanel(RibbonBarPanel):
    def __init__(self, parent, id, context=None, pane=None, **kwds):
        RibbonBarPanel.__init__(self, parent, id, context, **kwds)
        self.pane = pane

        # Layout properties.
        self.toggle_show_labels(context.setting(bool, "ribbon_show_labels", True))

        # Define Ribbon.
        self.__set_ribbonbar()

    @signal_listener("ribbon_show_labels")
    def on_show_labels_change(self, origin, value, *args):
        self.toggle_show_labels(value)

    @lookup_listener("button/basicediting")
    def set_editing_buttons(self, new_values, old_values):
        self.home.edit.set_buttons(new_values)

    @lookup_listener("button/project")
    def set_project_buttons(self, new_values, old_values):
        self.home.project.set_buttons(new_values)

    @lookup_listener("button/modify")
    def set_modify_buttons(self, new_values, old_values):
        self.modify.modify.set_buttons(new_values)

    @lookup_listener("button/geometry")
    def set_geometry_buttons(self, new_values, old_values):
        self.modify.geometry.set_buttons(new_values)

    @lookup_listener("button/preparation")
    def set_preparation_buttons(self, new_values, old_values):
        self.home.prep.set_buttons(new_values)

    @lookup_listener("button/jobstart")
    def set_jobstart_buttons(self, new_values, old_values):
        self.home.job.set_buttons(new_values)

    @lookup_listener("button/control")
    def set_control_buttons(self, new_values, old_values):
        self.home.control.set_buttons(new_values)

    @lookup_listener("button/device")
    def set_device_buttons(self, new_values, old_values):
        self.config.device.set_buttons(new_values)

    @lookup_listener("button/config")
    def set_config_buttons(self, new_values, old_values):
        self.config.config.set_buttons(new_values)

    @lookup_listener("button/align")
    def set_align_buttons(self, new_values, old_values):
        self.modify.align.set_buttons(new_values)

    @signal_listener("emphasized")
    def on_emphasis_change(self, origin, *args):
        self.apply_enable_rules()

    @signal_listener("selected")
    def on_selected_change(self, origin, node=None, *args):
        self.apply_enable_rules()

    @signal_listener("icons")
    def on_requested_change(self, origin, node=None, *args):
        self.apply_enable_rules()
        self.redrawn()

    # @signal_listener("tool_changed")
    # def on_tool_changed(self, origin, newtool=None, *args):
    #     # Signal provides a tuple with (togglegroup, id)
    #     if newtool is None:
    #         return
    #     if isinstance(newtool, (list, tuple)):
    #         group = newtool[0].lower() if newtool[0] is not None else ""
    #         identifier = newtool[1].lower() if newtool[1] is not None else ""
    #     else:
    #         group = newtool
    #         identifier = ""
    #     for page in self.pages:
    #         for panel in page.panels:
    #             for button in panel.buttons:
    #                 if button.group != group:
    #                     continue
    #                 button.set_button_toggle(button.identifier == identifier)
    #                 if self.art.current_page is not page:
    #                     self.art.current_page = page
    #     self.apply_enable_rules()
    #     self.modified()

    def __set_ribbonbar(self):
        """
        GUI Specific creation of ribbonbar.
        @return:
        """

        self.add_page(
            "home",
            ID_PAGE_MAIN,
            _("Project"),
            icons8_opened_folder_50.GetBitmap(resize=16),
        )

        self.add_page(
            "modify",
            ID_PAGE_MODIFY,
            _("Modify"),
            icons8_opened_folder_50.GetBitmap(resize=16),
        )

        self.add_page(
            "config",
            ID_PAGE_CONFIG,
            _("Config"),
            icons8_opened_folder_50.GetBitmap(resize=16),
        )

        self.add_panel(
            "project",
            parent=self.home,
            id=wx.ID_ANY,
            label=_("Project"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "edit",
            parent=self.home,
            id=wx.ID_ANY,
            label=_("Edit"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "prep",
            parent=self.home,
            id=wx.ID_ANY,
            label=_("Prepare"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "control",
            parent=self.home,
            id=wx.ID_ANY,
            label=_("Control"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "job",
            parent=self.home,
            id=wx.ID_ANY,
            label=_("Execute"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "config",
            parent=self.config,
            id=wx.ID_ANY,
            label=_("Configuration"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "device",
            parent=self.config,
            id=wx.ID_ANY,
            label=_("Devices"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "modify",
            parent=self.modify,
            id=wx.ID_ANY,
            label=_("Modification"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "geometry",
            parent=self.modify,
            id=wx.ID_ANY,
            label=_("Geometry"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "align",
            parent=self.modify,
            id=wx.ID_ANY,
            label=_("Alignment"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )
        self.modified()

    def pane_show(self):
        pass

    def pane_hide(self):
        """
        On pane_hide all the listeners are disabled.
        @return:
        """
        for page in self.pages:
            for panel in page.panels:
                for key, listener in panel._registered_signals:
                    self.context.unlisten(key, listener)

    @signal_listener("page")
    def on_page_signal(self, origin, pagename=None, *args):
        """
        Page listener to force the given active page on the triggering of a page signal.
        @param origin:
        @param pagename:
        @param args:
        @return:
        """
        if pagename is None:
            return
        pagename = pagename.lower()
        if pagename == "":
            pagename = "project"
        for p in self.pages:
            if p.label.lower() == pagename:
                self.art.current_page = p
                self.modified()
                if getattr(self.context.root, "_active_page", "") != pagename:
                    setattr(self.context.root, "_active_page", pagename)
