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

BUFFER = 5

def register_panel_ribbon(window, context):
    iconsize = get_default_icon_size()
    minh = 3 * iconsize
    pane = (
        aui.AuiPaneInfo()
        .Name("ribbon")
        .Top()
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

        self._pages = []
        self.set_default_pages()
        # Define Ribbon.
        self.__set_ribbonbar()

    def set_default_pages(self):
        self._pages = [
            {
                "id": "home",          # identifier
                "label": "Project",    # Label
                "panels": [            # Panels to include
                    {
                        "id": "project",
                        "label": "Project",
                        "seq": 1,
                    },
                    {
                        "id": "basicediting",
                        "label": "Edit",
                        "seq": 2,
                    },
                    {
                        "id": "undo",
                        "label": "Undo",
                        "seq": 3,
                    },
                    {
                        "id": "preparation",
                        "label": "Prepare",
                        "seq": 4,
                    },
                    {
                        "id": "control",
                        "label": "Control",
                        "seq": 5,
                    },
                    {
                        "id": "jobstart",
                        "label": "Execute",
                        "seq": 5,
                    },
                ],
                "seq": 1,              # Sequence
            },
            {
                "id": "modify",
                "label": "Modify",
                "panels": [
                    {
                        "id": "undo",
                        "label": "Undo",
                        "seq": 1,
                    },
                    {
                        "id": "modify",
                        "label": "Modification",
                        "seq": 2,
                    },
                    {
                        "id": "geometry",
                        "label": "Geometry",
                        "seq": 3,
                    },
                    {
                        "id": "align",
                        "label": "Alignment",
                        "seq": 4,
                    },
                ],
                "seq": 2,
            },
            {
                "id": "config",
                "label": "Config",
                "panels": [            # Panels to include
                    {
                        "id": "config",
                        "label": "Configuration",
                        "seq": 1,
                    },
                    {
                        "id": "device",
                        "label": "Devices",
                        "seq": 1,
                    },
                ],
                "seq": 3,
            },
        ]


    def set_panel_buttons(self, key, new_values):
        found = 0
        for page_entry in self._pages:
            if "_object" not in page_entry:
                continue
            if "panels" not in page_entry:
                continue
            pageobj = page_entry["_object"]
            for panel_entry in page_entry["panels"]:
                if "_object" not in panel_entry:
                    continue
                panelobj = panel_entry["_object"]
                if panel_entry["id"].lower() == key.lower():
                    # print (key, page_entry["id"], panel_entry)
                    panelobj.set_buttons(new_values)
                    found += 1
        # if found == 0:
        #     print (f"Did not find a panel for {key}")

    @signal_listener("ribbon_show_labels")
    def on_show_labels_change(self, origin, value, *args):
        self.toggle_show_labels(value)

    @lookup_listener("button/basicediting")
    def set_editing_buttons(self, new_values, old_values):
        self.set_panel_buttons("basicediting", new_values)

    @lookup_listener("button/undo")
    def set_undo_buttons(self, new_values, old_values):
        self.set_panel_buttons("undo", new_values)

    @lookup_listener("button/project")
    def set_project_buttons(self, new_values, old_values):
        self.set_panel_buttons("project", new_values)

    @lookup_listener("button/modify")
    def set_modify_buttons(self, new_values, old_values):
        self.set_panel_buttons("modify", new_values)

    @lookup_listener("button/geometry")
    def set_geometry_buttons(self, new_values, old_values):
        self.set_panel_buttons("geometry", new_values)

    @lookup_listener("button/preparation")
    def set_preparation_buttons(self, new_values, old_values):
        self.set_panel_buttons("preparation", new_values)

    @lookup_listener("button/jobstart")
    def set_jobstart_buttons(self, new_values, old_values):
        self.set_panel_buttons("jobstart", new_values)

    @lookup_listener("button/control")
    def set_control_buttons(self, new_values, old_values):
        self.set_panel_buttons("control", new_values)

    @lookup_listener("button/device")
    def set_device_buttons(self, new_values, old_values):
        self.set_panel_buttons("device", new_values)

    @lookup_listener("button/config")
    def set_config_buttons(self, new_values, old_values):
        self.set_panel_buttons("config", new_values)

    @lookup_listener("button/align")
    def set_align_buttons(self, new_values, old_values):
        self.set_panel_buttons("align", new_values)

    @lookup_listener("button/tool")
    def set_tool_buttons(self, new_values, old_values):
        self.set_panel_buttons("tool", new_values)

    @lookup_listener("button/extended_tools")
    def set_tool_extended_buttons(self, new_values, old_values):
        self.set_panel_buttons("extended_tools", new_values)

    @lookup_listener("button/group")
    def set_group_buttons(self, new_values, old_values):
        self.set_panel_buttons("group", new_values)

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
        for entry in sorted(self._pages, key=lambda d: d["seq"]):
            name_id = entry["id"]
            label =_(entry["label"])
            panel_list = entry["panels"]
            page = self.add_page(
                name_id,
                wx.ID_ANY,
                label,
                icons8_opened_folder_50.GetBitmap(resize=16),
            )
            entry["_object"] = page
            for pentry in sorted(panel_list, key=lambda d: d["seq"]):
                p_name_id = pentry["id"]
                p_label =_(pentry["label"])
                panel = self.add_panel(
                    p_name_id,
                    parent=page,
                    id=wx.ID_ANY,
                    label=p_label,
                    icon=icons8_opened_folder_50.GetBitmap(),
                )
                pentry["_object"] = panel

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
