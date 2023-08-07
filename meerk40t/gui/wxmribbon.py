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

from meerk40t.kernel import Settings, lookup_listener, signal_listener

from meerk40t.gui.icons import (
    get_default_icon_size,
    icons8_opened_folder_50,
    icons8_up_50,
    icons8_down_50,
    icons8_remove_25,
    icons8_add_new_25,
)

from meerk40t.gui.ribbon import RibbonBarPanel
from meerk40t.gui.wxutils import StaticBoxSizer

_ = wx.GetTranslation


def register_panel_ribbon(window, context):
    iconsize = get_default_icon_size()
    minh = 3 * iconsize
    pane_ribbon = (
        aui.AuiPaneInfo()
        .Name("ribbon")
        .Top()
        .BestSize(300, minh)
        .FloatingSize(640, minh)
        .Caption(_("Ribbon"))
        .CaptionVisible(not context.pane_lock)
    )
    pane_ribbon.dock_proportion = 640
    ribbon = MKRibbonBarPanel(
        window, wx.ID_ANY, context=context, pane=pane_ribbon, identifier="primary"
    )
    pane_ribbon.control = ribbon

    window.on_pane_create(pane_ribbon)
    context.register("pane/ribbon", pane_ribbon)

    minh = int(1.5 * iconsize)
    pane_tool = (
        aui.AuiPaneInfo()
        .Name("tools")
        .Left()
        .BestSize(minh, 300)
        .FloatingSize(minh, 640)
        .Caption(_("Tools"))
        .CaptionVisible(not context.pane_lock)
    )
    pane_tool.dock_proportion = 640
    ribbon = MKRibbonBarPanel(
        window,
        wx.ID_ANY,
        context=context,
        pane=pane_tool,
        identifier="tools",
        orientation="auto",
        show_labels=False,
    )
    pane_tool.control = ribbon

    window.on_pane_create(pane_tool)
    context.register("pane/tools", pane_tool)

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
    def __init__(
        self,
        parent,
        id,
        context=None,
        pane=None,
        identifier=None,
        orientation=None,
        show_labels=None,
        **kwds,
    ):
        RibbonBarPanel.__init__(self, parent, id, context, **kwds)
        self.pane = pane
        self.identifier = identifier
        if orientation is not None:
            if orientation.lower().startswith("h"):
                self.art.orientation = self.art.RIBBON_ORIENTATION_HORIZONTAL
            elif orientation.lower().startswith("v"):
                self.art.orientation = self.art.RIBBON_ORIENTATION_VERTICAL
            elif orientation.lower().startswith("a"):
                self.art.orientation = self.art.RIBBON_ORIENTATION_AUTO
        if show_labels is not None:
            self.art.show_labels = show_labels
        # Make myself known in context
        if not hasattr(context, f"_ribbons"):
            self.context._ribbons = dict()
        self.context._ribbons[self.identifier] = self

        self.storage = Settings(self.context.kernel.name, f"ribbon_{identifier}.cfg")
        self.storage.read_configuration()

        # Layout properties.
        self.toggle_show_labels(context.setting(bool, "ribbon_show_labels", True))

        self._pages = []
        self.set_default_pages()
        # Define Ribbon.
        self.__set_ribbonbar()

    def get_default_config(self):
        if self.identifier == "tools":
            config = [
                {
                    "id": "tools",  # identifier
                    "label": "Tools",  # Label
                    "panels": [  # Panels to include
                        {
                            "id": "tool",
                            "label": "Project",
                            "seq": 1,
                        },
                        {
                            "id": "extendedtools",
                            "label": "group",
                            "seq": 2,
                        },
                        {
                            "id": "group",
                            "label": "Group",
                            "seq": 3,
                        },
                    ],
                    "seq": 1,  # Sequence
                },
            ]
        elif self.identifier == "primary":
            config = [
                {
                    "id": "home",  # identifier
                    "label": "Project",  # Label
                    "panels": [  # Panels to include
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
                    "seq": 1,  # Sequence
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
                    "panels": [  # Panels to include
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
        else:
            config = []

        return config

    def get_current_config(self):
        # Is the storage empty? Then we use the default config
        config = self.get_default_config()
        testid = self.storage.read_persistent(str, "Ribbon", "identifier", "")
        # print(f"testid='{testid}', should be: {self.identifier}")
        if testid != self.identifier:
            # Thats fishy...
            return config
        flag = self.storage.read_persistent(
            bool, "Ribbon", "show_labels", self.art.show_labels
        )
        self.art.show_labels = flag
        newconfig = []
        page_idx = 0
        while True:
            section = f"Page_{page_idx + 1}"
            info = self.storage.read_persistent_string_dict(section)
            if info is None or len(info) == 0:
                break
            # print (info)
            newpage = {"id": "id", "label": "Label", "seq": 1}
            k = f"{section}/id"
            if k in info:
                value = self.storage.read_persistent(str, section, "id", "")
                newpage["id"] = value
            k = f"{section}/label"
            if k in info:
                value = self.storage.read_persistent(str, section, "label", "")
                newpage["label"] = value
            k = f"{section}/seq"
            if k in info:
                value = self.storage.read_persistent(int, section, "seq", None)
                if value:
                    try:
                        newpage["seq"] = int(value)
                    except ValueError:
                        pass
            panel_list = []
            panel_idx = 0
            while True:
                k = f"panel_{panel_idx + 1}"
                panel_info = self.storage.read_persistent(tuple, section, k, None)
                # print (f"{k} : {panel_info}")
                if (
                    panel_info is None
                    or not isinstance(panel_info, (list, tuple))
                    or len(panel_info) < 3
                ):
                    break
                panel_dict = dict()
                panel_dict["id"] = panel_info[0]
                panel_dict["seq"] = int(panel_info[1])
                panel_dict["label"] = panel_info[2]
                panel_list.append(panel_dict)

                panel_idx += 1

            newpage["panels"] = panel_list
            if len(panel_list) > 0:
                newconfig.append(newpage)

            page_idx += 1

        if len(newconfig) > 0:
            config = newconfig
        return config

    def set_default_pages(self):
        self._pages = self.get_current_config()
        paths = []
        for page_entry in self._pages:
            for panel_entry in page_entry["panels"]:
                ppath = f"button/{panel_entry['id']}/*"
                if ppath not in paths:
                    new_values = []
                    for obj, kname, sname in self.context.kernel.find(ppath):
                        new_values.append((obj, kname, sname))
                    self.set_panel_buttons(panel_entry["id"], new_values)
                    paths.append(ppath)

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

    def restart(self):
        self.storage.read_configuration()
        self.pages = []
        self.set_default_pages()
        # Define Ribbon.
        self.__set_ribbonbar()
        # And now we query the kernel to recreate the buttons
        paths = []
        for page_entry in self._pages:
            for panel_entry in page_entry["panels"]:
                ppath = f"button/{panel_entry['id']}/*"
                if ppath not in paths:
                    new_values = []
                    for obj, kname, sname in self.context.kernel.find(ppath):
                        new_values.append((obj, kname, sname))
                    self.set_panel_buttons(panel_entry["id"], new_values)
                    paths.append(ppath)
        self.art.current_page = self.first_page()
        self.modified()

    @signal_listener("ribbon_recreate")
    def on_recreate(self, origin, target, *args):
        if target is not None and target != self.identifier:
            return
        self.restart()

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

    @signal_listener("tool_changed")
    def on_tool_changed(self, origin, newtool=None, *args):
        # Signal provides a tuple with (togglegroup, id)
        if newtool is None:
            return
        if isinstance(newtool, (list, tuple)):
            group = newtool[0].lower() if newtool[0] is not None else ""
            identifier = newtool[1].lower() if newtool[1] is not None else ""
        else:
            group = newtool
            identifier = ""

        for page in self.pages:
            for panel in page.panels:
                for button in panel.buttons:
                    if button.group != group:
                        continue
                    button.set_button_toggle(button.identifier == identifier)
        self.apply_enable_rules()
        self.modified()

    def __set_ribbonbar(self):
        """
        GUI Specific creation of ribbonbar.
        @return:
        """
        for entry in sorted(self._pages, key=lambda d: d["seq"]):
            name_id = entry["id"]
            label = _(entry["label"])
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
                p_label = _(pentry["label"])
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


class RibbonEditor(wx.Panel):
    """
    RibbonEditor is a panel that allows you to define the content
    of the ribbonbar on top of Mks main window
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)

        self.context = context
        self.ribbon_identifier = "primary"

        self.available_options = []
        self.available_labels = []
        self._config = None
        self.current_page = None

        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_ribbons = StaticBoxSizer(self, wx.ID_ANY, _("Ribbons"), wx.VERTICAL)

        sizer_pages = StaticBoxSizer(self, wx.ID_ANY, _("Pages"), wx.VERTICAL)
        sizer_panels = StaticBoxSizer(self, wx.ID_ANY, _("Panels"), wx.VERTICAL)
        sizer_available_panels = StaticBoxSizer(
            self, wx.ID_ANY, _("Available Panels"), wx.VERTICAL
        )

        choices = [v for v in self.context._ribbons]
        self.combo_ribbons = wx.ComboBox(
            self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.check_labels = wx.CheckBox(self, wx.ID_ANY, _("Show the Ribbon Labels"))

        sizer_ribbons.Add(self.combo_ribbons, 0, wx.EXPAND, 0)
        sizer_ribbons.Add(self.check_labels, 0, wx.EXPAND, 0)
        self.list_pages = wx.ListBox(self, wx.ID_ANY, style=wx.LB_SINGLE)
        self.text_param_page = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER)

        self.list_panels = wx.ListBox(self, wx.ID_ANY, style=wx.LB_SINGLE)
        self.button_add_page = wx.StaticBitmap(self, wx.ID_ANY, size=wx.Size(30, 30))
        self.button_del_page = wx.StaticBitmap(self, wx.ID_ANY, size=wx.Size(30, 30))
        self.button_up_page = wx.StaticBitmap(self, wx.ID_ANY, size=wx.Size(30, 30))
        self.button_down_page = wx.StaticBitmap(self, wx.ID_ANY, size=wx.Size(30, 20))
        self.button_add_page.SetBitmap(icons8_add_new_25.GetBitmap(resize=25))
        self.button_del_page.SetBitmap(icons8_remove_25.GetBitmap(resize=25))
        self.button_up_page.SetBitmap(icons8_up_50.GetBitmap(resize=25))
        self.button_down_page.SetBitmap(icons8_down_50.GetBitmap(resize=25))

        self.button_del_panel = wx.StaticBitmap(self, wx.ID_ANY, size=wx.Size(30, 30))
        self.button_up_panel = wx.StaticBitmap(self, wx.ID_ANY, size=wx.Size(30, 30))
        self.button_down_panel = wx.StaticBitmap(self, wx.ID_ANY, size=wx.Size(30, 30))
        self.button_del_panel.SetBitmap(icons8_remove_25.GetBitmap(resize=25))
        self.button_up_panel.SetBitmap(icons8_up_50.GetBitmap(resize=25))
        self.button_down_panel.SetBitmap(icons8_down_50.GetBitmap(resize=25))

        self.list_options = wx.ListBox(self, wx.ID_ANY, style=wx.LB_SINGLE)
        self.button_add_panel = wx.Button(self, wx.ID_ANY, _("Add to page"))
        self.button_apply = wx.Button(self, wx.ID_ANY, _("Apply"))
        self.button_reset = wx.Button(self, wx.ID_ANY, _("Reset to Default"))

        sizer_button = wx.BoxSizer(wx.VERTICAL)
        sizer_button.Add(self.button_add_panel, 1, wx.EXPAND, 0)
        sizer_button.Add(self.button_apply, 1, wx.EXPAND, 0)
        sizer_button.Add(self.button_reset, 1, wx.EXPAND, 0)

        sizer_available_panels.Add(self.list_options, 1, wx.EXPAND, 0)
        sizer_available_panels.Add(sizer_button, 0, wx.EXPAND, 0)

        hsizer_page = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_page.Add(self.text_param_page, 1, wx.EXPAND, 0)
        hsizer_page.Add(self.button_add_page, 0, wx.EXPAND, 0)
        hsizer_page.Add(self.button_del_page, 0, wx.EXPAND, 0)
        hsizer_page.Add(self.button_up_page, 0, wx.EXPAND, 0)
        hsizer_page.Add(self.button_down_page, 0, wx.EXPAND, 0)

        sizer_pages.Add(self.list_pages, 1, wx.EXPAND, 0)
        sizer_pages.Add(hsizer_page, 0, wx.EXPAND, 0)

        hsizer_panel = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_panel.Add(self.button_del_panel, 0, wx.EXPAND, 0)
        hsizer_panel.Add(self.button_up_panel, 0, wx.EXPAND, 0)
        hsizer_panel.Add(self.button_down_panel, 0, wx.EXPAND, 0)
        sizer_panels.Add(self.list_panels, 1, wx.EXPAND, 0)
        sizer_panels.Add(hsizer_panel, 0, wx.EXPAND, 0)

        sizer_active_config = wx.BoxSizer(wx.VERTICAL)
        sizer_active_config.Add(sizer_ribbons, 0, wx.EXPAND, 0)
        sizer_active_config.Add(sizer_pages, 1, wx.EXPAND, 0)
        sizer_active_config.Add(sizer_panels, 1, wx.EXPAND, 0)

        sizer_main.Add(sizer_active_config, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_available_panels, 1, wx.EXPAND, 0)

        # Explanatory tooltips
        self.button_add_panel.SetToolTip(
            _("Add the selected panel to the selected page")
        )
        self.button_apply.SetToolTip(_("Apply the configuration"))
        self.button_reset.SetToolTip(
            _("Reset the ribbon appearance to the default configuration")
        )
        self.button_del_page.SetToolTip(_("Remove the selected page from the list"))
        self.button_del_panel.SetToolTip(_("Remove the selected panel from the list"))
        self.button_down_page.SetToolTip(
            _("Decrease the position of the selected page")
        )
        self.button_up_page.SetToolTip(_("Increase the position of the selected page"))
        self.button_down_panel.SetToolTip(
            _("Decrease the position of the selected panel")
        )
        self.button_up_panel.SetToolTip(
            _("Increase the position of the selected panel")
        )
        self.text_param_page.SetToolTip(_("Modify the label of the selected page"))

        self.fill_options()
        self.SetSizer(sizer_main)
        self.Layout()
        self.list_options.Bind(wx.EVT_LISTBOX, self.on_list_options_click)
        self.list_options.Bind(wx.EVT_LISTBOX_DCLICK, self.on_list_options_dclick)

        self.button_add_panel.Bind(wx.EVT_BUTTON, self.on_button_add_panel_click)
        self.button_apply.Bind(wx.EVT_BUTTON, self.on_button_apply_click)
        self.button_reset.Bind(wx.EVT_BUTTON, self.on_button_reset_click)
        self.combo_ribbons.Bind(wx.EVT_COMBOBOX, self.on_combo_ribbon)

        self.list_pages.Bind(wx.EVT_LISTBOX, self.on_list_pages_click)
        self.list_panels.Bind(wx.EVT_LISTBOX, self.on_list_panels_click)

        self.text_param_page.Bind(wx.EVT_TEXT, self.on_text_label)
        self.text_param_page.Bind(wx.EVT_TEXT_ENTER, self.on_text_label_enter)

        self.button_add_page.Bind(wx.EVT_LEFT_DOWN, self.on_button_add_page_click)
        self.button_del_page.Bind(wx.EVT_LEFT_DOWN, self.on_button_page_delete)
        self.button_up_page.Bind(wx.EVT_LEFT_DOWN, self.on_move_page_up)
        self.button_down_page.Bind(wx.EVT_LEFT_DOWN, self.on_move_page_down)

        self.button_del_panel.Bind(wx.EVT_LEFT_DOWN, self.on_button_panel_delete)
        self.button_up_panel.Bind(wx.EVT_LEFT_DOWN, self.on_move_panel_up)
        self.button_down_panel.Bind(wx.EVT_LEFT_DOWN, self.on_move_panel_down)

        self.combo_ribbons.SetSelection(0)
        self.on_combo_ribbon(None)

    # ---- Generic routines to access data

    def current_ribbon(self):
        result = None
        if hasattr(self.context, "_ribbons"):
            if self.ribbon_identifier in self.context._ribbons:
                result = self.context._ribbons[self.ribbon_identifier]
        return result

    def get_page(self, pageid=None):
        if pageid is None:
            pageid = self.current_page
        for p in self._config:
            if p["id"] == pageid:
                return p
        return None

    def update_page(self, pageid, newlabel=None, newseq=None):
        for p in self._config:
            if p["id"] == pageid:
                if newlabel is not None:
                    p["label"] = newlabel
                if newseq is not None:
                    p["seq"] = newseq

    # ---- Routines to fill listboxes

    def fill_pages(self, reload=False, reposition=None):
        self.list_pages.Clear()
        if reload is None:
            reload = False
        if reload:
            rib = self.current_ribbon()
            if rib is None:
                return
            self._config = rib.get_current_config()
        pages = []
        idx = 0
        for p_idx, page_entry in enumerate(
            sorted(self._config, key=lambda d: d["seq"])
        ):
            pages.append(f"{page_entry['id']} ({page_entry['label']})")
            if reposition is not None and page_entry["id"] == reposition:
                idx = p_idx
        self.list_pages.SetItems(pages)
        if len(pages) > 0:
            self.list_pages.SetSelection(idx)
        self.on_list_pages_click(None)

    def fill_panels(self, pageid=None, reposition=None):
        if pageid is None:
            pageid = self.current_page
        self.list_panels.Clear()
        panels = []
        tidx = 0
        cidx = 0
        for page_entry in self._config:
            if pageid == page_entry["id"]:
                panel_list = page_entry["panels"]
                for panel_entry in sorted(panel_list, key=lambda d: d["seq"]):
                    panels.append(f"{panel_entry['id']}")
                    if reposition is not None and reposition == panel_entry["id"]:
                        tidx = cidx
                    cidx += 1

        self.list_panels.SetItems(panels)
        if len(panels) > 0:
            self.list_panels.SetSelection(tidx)

    def fill_options(self):
        # Query all registered button sections
        self.available_options.clear()
        self.available_labels.clear()
        for d_name in self.context.kernel.match("button", suffix=False):
            secs = d_name.split("/")
            #  print(f"{d_name} {secs}")
            if len(secs) > 2:
                section = secs[1]
                button = secs[2]
                try:
                    idx = self.available_options.index(section)
                    self.available_labels[idx] += f", {button}"
                except ValueError:
                    self.available_options.append(section)
                    self.available_labels.append(button)

        self.list_options.Clear()
        self.list_options.SetItems(self.available_options)

    # ---- Event Handler Routines

    def on_combo_ribbon(self, event):
        idx = self.combo_ribbons.GetSelection()
        if idx < 0:
            return
        rlist = list(self.context._ribbons.keys())
        if len(rlist) > 0:
            self.ribbon_identifier = rlist[idx]
            rib = self.current_ribbon()
            self.check_labels.SetValue(rib.art.show_labels)
            self.fill_pages(reload=True)

    def on_move_page_up(self, event):
        newconfig = []
        for p_idx, page_entry in enumerate(
            sorted(self._config, key=lambda d: d["seq"])
        ):
            if page_entry["id"] == self.current_page and p_idx > 0:
                newconfig.insert(p_idx - 1, page_entry)
            else:
                newconfig.append(page_entry)
        for p_idx, page_entry in enumerate(newconfig):
            page_entry["seq"] = p_idx + 1
        self._config = newconfig
        self.fill_pages(reposition=self.current_page)

    def on_move_page_down(self, event):
        newconfig = []
        for p_idx, page_entry in enumerate(
            sorted(self._config, key=lambda d: d["seq"], reverse=True)
        ):
            if page_entry["id"] == self.current_page and p_idx > 0:
                newconfig.insert(1, page_entry)
            else:
                newconfig.insert(0, page_entry)
        for p_idx, page_entry in enumerate(newconfig):
            page_entry["seq"] = p_idx + 1
        self._config = newconfig
        self.fill_pages(reposition=self.current_page)

    def on_list_pages_click(self, event):
        idx = self.list_pages.GetSelection()
        flag1 = idx >= 0
        self.button_del_page.Enable(flag1)
        self.button_down_page.Enable(flag1)
        self.button_up_page.Enable(flag1)
        self.button_add_page.Enable(True)
        page_label = ""
        if idx >= 0:
            term = self.list_pages.GetStringSelection()
            idx = term.find(" (")
            if idx >= 0:
                page = term[0:idx]
                self.current_page = page
                self.fill_panels()
                p = self.get_page(page)
                if p is not None:
                    page_label = p["label"]
        self.text_param_page.SetValue(page_label)

    def on_button_page_delete(self, event):
        new_config = []
        for p in self._config:
            if p["id"] != self.current_page:
                new_config.append(p)
        if len(new_config) != self._config:
            self._config = new_config
            self.current_page = None
            self.fill_pages()

    def on_button_add_page_click(self, event):
        newid = f"page_{len(self._config) + 1}"
        newentry = {
            "id": newid,
            "label": f"Page {len(self._config) + 1}",
            "seq": len(self._config) + 1,
            "panels": [],
        }
        self._config.append(newentry)
        self.fill_pages(reposition=newid)

    def on_move_panel_up(self, event):
        idx = self.list_panels.GetSelection()
        if idx < 0:
            return
        panelid = self.list_panels.GetString(idx)
        for page in self._config:
            if page["id"] != self.current_page:
                continue
            panel_list = page["panels"]
            newconfig = []
            for p_idx, panel_entry in enumerate(sorted(panel_list, key=lambda d: d["seq"])):
                if panel_entry["id"] == panelid and p_idx > 0:
                    newconfig.insert(p_idx - 1, panel_entry)
                else:
                    newconfig.append(panel_entry)
            for p_idx, panel_entry in enumerate(newconfig):
                panel_entry["seq"] = p_idx + 1
            page["panels"] = newconfig
        self.fill_panels(reposition=panelid)

    def on_move_panel_down(self, event):
        idx = self.list_panels.GetSelection()
        if idx < 0:
            return
        panelid = self.list_panels.GetString(idx)
        for page in self._config:
            if page["id"] != self.current_page:
                continue
            panelid = self.list_panels.GetString(idx)
            panel_list = page["panels"]
            newconfig = []
            for p_idx, panel_entry in enumerate(
                sorted(panel_list, key=lambda d: d["seq"], reverse=True)
            ):
                if panel_entry["id"] == panelid and p_idx > 0:
                    newconfig.insert(1, panel_entry)
                else:
                    newconfig.insert(0, panel_entry)
            for p_idx, panel_entry in enumerate(newconfig):
                panel_entry["seq"] = p_idx + 1
            page["panels"] = newconfig
        self.fill_panels(reposition=panelid)

    def on_button_panel_delete(self, event):
        idx = self.list_panels.GetSelection()
        if idx < 0:
            return
        panelid = self.list_panels.GetString(idx)
        for page in self._config:
            if page["id"] != self.current_page:
                continue
            panel_list = page["panels"]
            new_config = []
            seqnum = 1
            for panel in sorted(panel_list, key=lambda d: d["seq"]):
                if panel["id"] != panelid:
                    panel["seq"] = seqnum
                    new_config.append(panel)
                    seqnum += 1
            page["panels"] = new_config
        self.fill_panels()

    def on_list_panels_click(self, event):
        idx = self.list_panels.GetSelection()
        flag1 = idx >= 0
        self.button_del_panel.Enable(flag1)
        self.button_down_panel.Enable(flag1)
        self.button_up_panel.Enable(flag1)
        if idx < 0:
            return

    def on_text_label(self, event):
        label = self.text_param_page.GetValue()
        self.update_page(self.current_page, newlabel=label)

    def on_text_label_enter(self, event):
        self.fill_pages(reposition=self.current_page)

    def on_list_options_click(self, event):
        ttip = ""
        idx = self.list_options.GetSelection()
        if idx >= 0:
            self.button_add_panel.Enable(True)
            ttip = f"{self.available_options[idx]}: {self.available_labels[idx]}"
        else:
            self.button_add_panel.Enable(False)
        self.list_options.SetToolTip(ttip)

    def on_list_options_dclick(self, event):
        self.on_button_add_panel_click(event)

    def on_button_add_panel_click(self, event):
        idx = self.list_options.GetSelection()
        if idx < 0:
            return
        panel = self.available_options[idx]
        for page in self._config:
            if page["id"] != self.current_page:
                continue
            if panel not in page["panels"]:
                newpanel = {
                    "id": panel,
                    "label": panel,
                    "seq": len(page["panels"]) + 2,
                }
                page["panels"].append(newpanel)
        self.fill_pages(reposition=self.current_page)

    def on_button_apply_click(self, event):
        ob = self.current_ribbon()
        if ob is None:
            return
        if len(self._config) == 0:
            return
        ob.storage.delete_all_persistent()
        ob.storage.write_persistent("Ribbon", "identifier", self.ribbon_identifier)
        show_labels = self.check_labels.GetValue()
        ob.storage.write_persistent("Ribbon", "show_labels", show_labels)

        for p_idx, page_entry in enumerate(
            sorted(self._config, key=lambda d: d["seq"])
        ):
            section = f"Page_{p_idx + 1}"
            ob.storage.write_persistent(section, "id", page_entry["id"])
            ob.storage.write_persistent(section, "label", page_entry["label"])
            ob.storage.write_persistent(section, "seq", page_entry["seq"])
            panel_list = page_entry["panels"]
            for panel_idx, pentry in enumerate(
                sorted(panel_list, key=lambda d: d["seq"])
            ):
                key = f"Panel_{panel_idx + 1}"
                result = (
                    pentry["id"],
                    pentry["seq"],
                    pentry["label"],
                )
                ob.storage.write_persistent(section, key, result)
        ob.storage.write_configuration()
        ob.restart()
        # self.context.signal("ribbon_recreate", self.ribbon_identifier)

    def on_button_reset_click(self, event):
        rib = self.current_ribbon()
        if rib is None:
            return
        self._config = rib.get_default_config()
        self.fill_pages()

    def pane_hide(self):
        pass

    def pane_show(self):
        pass
