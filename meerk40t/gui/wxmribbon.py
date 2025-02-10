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

import wx
from wx import aui

from meerk40t.gui.icons import (
    get_default_icon_size,
    icon_add_new,
    icon_edit,
    icon_trash,
    icons8_down,
    icons8_opened_folder,
    icons8_up,
)
from meerk40t.gui.ribbon import RibbonBarPanel
from meerk40t.gui.wxutils import (
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxButton,
    wxCheckBox,
    wxComboBox,
    wxListBox,
    wxStaticBitmap,
    wxStaticText,
)
from meerk40t.kernel import Settings, lookup_listener, signal_listener

_ = wx.GetTranslation


def register_panel_ribbon(window, context):
    iconsize = get_default_icon_size(context)
    minh = 3 * iconsize + 25
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
    pane_ribbon.helptext = _("Toolbar with the main commands to control jobs and devices")

    window.on_pane_create(pane_ribbon)
    context.register("pane/ribbon", pane_ribbon)
    context.register("ribbonbar/primary", ribbon)

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
    pane_tool.helptext = _("Icon-bar with the main object creation tools")
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
    context.register("ribbonbar/tools", ribbon)

    pane_edittool = (
        aui.AuiPaneInfo()
        .Name("edittools")
        .Left()
        .BestSize(minh, 300)
        .FloatingSize(minh, 640)
        .Caption(_("Modify"))
        .CaptionVisible(not context.pane_lock)
    )
    pane_edittool.dock_proportion = 640
    pane_edittool.helptext = _("Icon-bar with object modification tools")
    ribbon = MKRibbonBarPanel(
        window,
        wx.ID_ANY,
        context=context,
        pane=pane_edittool,
        identifier="edittools",
        orientation="auto",
        show_labels=False,
    )
    pane_edittool.control = ribbon

    window.on_pane_create(pane_edittool)
    context.register("pane/edittools", pane_edittool)
    context.register("ribbonbar/edittools", ribbon)

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
        RibbonBarPanel.__init__(self, parent, id, context, pane, **kwds)
        self.pane = pane
        self.identifier = identifier
        self.userbuttons = []
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
        if not hasattr(context, "_ribbons"):
            self.context._ribbons = {}
        self.context._ribbons[self.identifier] = self

        self.storage = Settings(
            self.context.kernel.name, f"ribbon_{identifier}.cfg", create_backup=True
        )  # keep backup
        self.storage.read_configuration()

        self.allow_labels = bool(show_labels is None or show_labels)
        # Layout properties.
        if self.allow_labels:
            self.toggle_show_labels(context.setting(bool, "ribbon_show_labels", True))

        self._pages = []
        self.set_default_pages()
        # Define Ribbon.
        self.__set_ribbonbar()

    def get_default_config(self):
        button_config = []
        if self.identifier == "tools":
            ribbon_config = [
                {
                    "id": "tools",  # identifier
                    "label": "Tools",  # Label
                    "panels": [  # Panels to include
                        {
                            "id": "select",
                            "label": "Select + Edit",
                            "seq": 1,
                        },
                        {
                            "id": "lasercontrol",
                            "label": "Laser",
                            "seq": 2,
                        },
                        {
                            "id": "tool",
                            "label": "Create",
                            "seq": 3,
                        },
                        {
                            "id": "extended_tools",
                            "label": "Extended Tools",
                            "seq": 4,
                        },
                        {
                            "id": "group",
                            "label": "Group",
                            "seq": 5,
                        },
                    ],
                    "seq": 1,  # Sequence
                },
            ]
        elif self.identifier == "primary":
            ribbon_config = [
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
                            "seq": 6,
                        },
                        {
                            "id": "user",
                            "label": "User",
                            "seq": 7,
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
        elif self.identifier == "edittools":
            ribbon_config = [
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
                            "id": "group",
                            "label": "Group",
                            "seq": 2,
                        },
                        {
                            "id": "modify",
                            "label": "Modification",
                            "seq": 3,
                        },
                        {
                            "id": "geometry",
                            "label": "Geometry",
                            "seq": 4,
                        },
                        {
                            "id": "align",
                            "label": "Alignment",
                            "seq": 5,
                        },
                    ],
                    "seq": 1,
                },
            ]
        else:
            ribbon_config = []

        return ribbon_config, button_config

    def get_current_config(self):
        import meerk40t.gui.icons as mkicons

        icon_list = []
        for entry in dir(mkicons):
            # print (entry)
            if entry.startswith("icon"):
                s = getattr(mkicons, entry)
                if isinstance(s, (mkicons.VectorIcon, mkicons.PyEmbeddedImage)):
                    icon_list.append(entry)

        # Is the storage empty? Then we use the default config
        ribbon_config, button_config = self.get_default_config()
        testid = self.storage.read_persistent(str, "Ribbon", "identifier", "")
        # print(f"testid='{testid}', should be: {self.identifier}")
        if testid != self.identifier:
            # Thats fishy...
            return ribbon_config, button_config
        flag = self.storage.read_persistent(
            bool, "Ribbon", "show_labels", self.art.show_labels
        )
        self.art.show_labels = flag
        newconfig = []
        newbuttons = []
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
                panel_dict = {}
                panel_dict["id"] = panel_info[0]
                panel_dict["seq"] = int(panel_info[1])
                panel_dict["label"] = panel_info[2]
                panel_list.append(panel_dict)

                panel_idx += 1

            newpage["panels"] = panel_list
            if panel_list:
                newconfig.append(newpage)

            page_idx += 1

        # ------ Read user defined buttons...
        button_idx = 0

        def delayed_command(command):
            def handler(*args):
                cmd = command.replace("\\n", "\n")
                self.context(cmd + "\n")

            return handler

        while True:
            section = f"Button_{button_idx + 1}"
            info = self.storage.read_persistent_string_dict(section)
            if info is None or len(info) == 0:
                break
            # print (info)
            userbutton = {
                "id": f"user_button_{button_idx+1}",
                "label": "Label",
                "action_left": "",
                "action_right": "",
                "enable": "always",
                "visible": "always",
                "tip": _("This could be your tooltip"),
                "icon": "icon_edit",
                "seq": 1,
            }
            for content in ("label", "tip", "action_left", "action_right"):
                k = f"{section}/{content}"
                if k in info:
                    value = self.storage.read_persistent(str, section, content, "")
                    userbutton[content] = value
            for content in ("enable", "visible"):
                k = f"{section}/{content}"
                if k in info:
                    value = self.storage.read_persistent(str, section, content, "")
                    if value in ("always", "selected", "selected2"):
                        userbutton[content] = value

            k = f"{section}/icon"
            if k in info:
                value = self.storage.read_persistent(str, section, "icon", "")
                if value in icon_list:
                    userbutton["icon"] = value
            k = f"{section}/seq"
            if k in info:
                value = self.storage.read_persistent(int, section, "seq", None)
                if value:
                    try:
                        userbutton["seq"] = int(value)
                    except ValueError:
                        pass
            d = {
                "label": userbutton["label"],
                "icon": getattr(mkicons, userbutton["icon"], None),
                "tip": userbutton["tip"],
            }
            if userbutton["action_left"]:
                d["action"] = delayed_command(userbutton["action_left"])
            if userbutton["action_right"]:
                d["action_right"] = delayed_command(userbutton["action_right"])
            if userbutton["enable"] == "selected":
                d["rule_enabled"] = (
                    lambda cond: len(list(self.context.elements.elems(emphasized=True)))
                    > 0
                )
            if userbutton["enable"] == "selected2":
                d["rule_enabled"] = (
                    lambda cond: len(list(self.context.elements.elems(emphasized=True)))
                    > 1
                )
            if userbutton["visible"] == "selected":
                d["rule_visible"] = (
                    lambda cond: len(list(self.context.elements.elems(emphasized=True)))
                    > 0
                )
            if userbutton["visible"] == "selected2":
                d["rule_visible"] = (
                    lambda cond: len(list(self.context.elements.elems(emphasized=True)))
                    > 1
                )

            self.context.kernel.register(f"button/user/{userbutton['id']}", d)
            button_config.append(userbutton)
            button_idx += 1

        if newconfig:
            ribbon_config = newconfig
        return ribbon_config, button_config

    def set_default_pages(self):
        self._pages, self.userbuttons = self.get_current_config()
        paths = []
        for page_entry in self._pages:
            for panel_entry in page_entry["panels"]:
                ppath = f"button/{panel_entry['id']}/*"
                if ppath not in paths:
                    new_values = []
                    new_values.extend(
                        (obj, kname, sname)
                        for obj, kname, sname in self.context.kernel.find(ppath)
                    )
                    self.set_panel_buttons(panel_entry["id"], new_values)
                    paths.append(ppath)

    def set_panel_buttons(self, key, new_values):
        found = 0
        for page_entry in self._pages:
            if "_object" not in page_entry:
                continue
            if "panels" not in page_entry:
                continue
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
        self.art.establish_colors()
        self.pages = []
        self.userbuttons = []
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
                    new_values.extend(
                        (obj, kname, sname)
                        for obj, kname, sname in self.context.kernel.find(ppath)
                    )
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
        if self.allow_labels:
            self.toggle_show_labels(value)

    # Notabene: the lookup listener design will look for partial fits!
    # So a listener to "button/tool" would get changes from
    #  "button/tool", "button/tools" and "button/toolabcdefgh"
    # So to add buttons of your own make sure you are using a distinct name!

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

    @lookup_listener("button/select")
    def set_select_buttons(self, new_values, old_values):
        self.set_panel_buttons("select", new_values)

    @lookup_listener("button/tools")
    def set_tool_buttons(self, new_values, old_values):
        self.set_panel_buttons("tool", new_values)

    @lookup_listener("button/lasercontrol")
    def set_lasercontrol_buttons(self, new_values, old_values):
        self.set_panel_buttons("lasercontrol", new_values)

    @lookup_listener("button/extended_tools")
    def set_tool_extended_buttons(self, new_values, old_values):
        self.set_panel_buttons("extended_tools", new_values)

    @lookup_listener("button/group")
    def set_group_buttons(self, new_values, old_values):
        self.set_panel_buttons("group", new_values)

    @lookup_listener("button/user")
    def set_user_buttons(self, new_values, old_values):
        self.set_panel_buttons("user", new_values)

    @signal_listener("emphasized")
    def on_emphasis_change(self, origin, *args):
        # self.context.elements.set_start_time("Ribbon rule")
        self.apply_enable_rules()
        # self.context.elements.set_end_time("Ribbon rule")

    @signal_listener("undoredo")
    def on_undostate_change(self, origin, *args):
        self.apply_enable_rules()

    @signal_listener("selected")
    @signal_listener("element_property_update")
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
                icons8_opened_folder.GetBitmap(resize=16),
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
                    icon=icons8_opened_folder.GetBitmap(),
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
            pagename = "home"
        for p in self.pages:
            # print (f"compare '{p.reference.lower()}' to '{pagename}'")
            if p.reference.lower() == pagename:
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
        self.context.themes.set_window_colors(self)
        self.SetHelpText("ribboneditor")
        self.ribbon_identifier = "primary"

        self.available_options = []
        self.available_labels = []
        self._config = None
        self._config_buttons = None
        self.current_page = None
        self.current_button = None

        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_ribbons = StaticBoxSizer(self, wx.ID_ANY, _("Ribbons"), wx.VERTICAL)

        sizer_pages = StaticBoxSizer(self, wx.ID_ANY, _("Pages"), wx.VERTICAL)
        sizer_panels = StaticBoxSizer(self, wx.ID_ANY, _("Panels"), wx.VERTICAL)
        sizer_available_panels = StaticBoxSizer(
            self, wx.ID_ANY, _("Available Panels"), wx.VERTICAL
        )

        choices = [v for v in self.context._ribbons]
        self.combo_ribbons = wxComboBox(
            self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.check_labels = wxCheckBox(self, wx.ID_ANY, _("Show the Ribbon Labels"))

        sizer_ribbons.Add(self.combo_ribbons, 0, wx.EXPAND, 0)
        sizer_ribbons.Add(self.check_labels, 0, wx.EXPAND, 0)
        self.list_pages = wxListBox(self, wx.ID_ANY, style=wx.LB_SINGLE)

        self.text_param_page = TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER)

        self.list_panels = wxListBox(self, wx.ID_ANY, style=wx.LB_SINGLE)
        bsize = dip_size(self, 30, 30)
        self.button_add_page = wxStaticBitmap(self, wx.ID_ANY, size=bsize)
        self.button_del_page = wxStaticBitmap(self, wx.ID_ANY, size=bsize)
        self.button_up_page = wxStaticBitmap(self, wx.ID_ANY, size=bsize)
        self.button_down_page = wxStaticBitmap(self, wx.ID_ANY, size=bsize)

        testsize = dip_size(self, 20, 20)
        iconsize = testsize[0]
        # Circumvent a WXPython bug at high resolutions under Windows
        bmp = icon_trash.GetBitmap(resize=iconsize, buffer=1)
        self.button_del_page.SetBitmap(bmp)
        testsize = self.button_del_page.GetBitmap().Size
        if testsize[0] != iconsize:
            iconsize = int(iconsize * iconsize / testsize[0])

        self.button_add_page.SetBitmap(icon_add_new.GetBitmap(resize=iconsize))
        self.button_del_page.SetBitmap(icon_trash.GetBitmap(resize=iconsize, buffer=1))
        self.button_up_page.SetBitmap(icons8_up.GetBitmap(resize=iconsize, buffer=1))
        self.button_down_page.SetBitmap(
            icons8_down.GetBitmap(resize=iconsize, buffer=1)
        )

        self.button_del_panel = wxStaticBitmap(self, wx.ID_ANY, size=bsize)
        self.button_up_panel = wxStaticBitmap(self, wx.ID_ANY, size=bsize)
        self.button_down_panel = wxStaticBitmap(self, wx.ID_ANY, size=bsize)

        self.button_del_panel.SetBitmap(icon_trash.GetBitmap(resize=iconsize, buffer=1))
        self.button_up_panel.SetBitmap(icons8_up.GetBitmap(resize=iconsize, buffer=1))
        self.button_down_panel.SetBitmap(
            icons8_down.GetBitmap(resize=iconsize, buffer=1)
        )

        self.list_options = wxListBox(self, wx.ID_ANY, style=wx.LB_SINGLE)
        self.button_add_panel = wxButton(self, wx.ID_ANY, _("Add to page"))
        self.button_apply = wxButton(self, wx.ID_ANY, _("Apply"))
        self.button_reset = wxButton(self, wx.ID_ANY, _("Reset to Default"))

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

        sizer_buttons = StaticBoxSizer(
            self, wx.ID_ANY, _("User-defined buttons"), wx.VERTICAL
        )
        self.list_buttons = wxListBox(self, wx.ID_ANY, style=wx.LB_SINGLE)
        sizer_button_buttons = wx.BoxSizer(wx.HORIZONTAL)

        self.button_add_button = wxStaticBitmap(self, wx.ID_ANY, size=bsize)
        self.button_del_button = wxStaticBitmap(self, wx.ID_ANY, size=bsize)
        self.button_edit_button = wxStaticBitmap(self, wx.ID_ANY, size=bsize)
        self.button_up_button = wxStaticBitmap(self, wx.ID_ANY, size=bsize)
        self.button_down_button = wxStaticBitmap(self, wx.ID_ANY, size=bsize)

        self.button_add_button.SetBitmap(icon_add_new.GetBitmap(resize=iconsize))
        self.button_del_button.SetBitmap(
            icon_trash.GetBitmap(resize=iconsize, buffer=1)
        )
        self.button_edit_button.SetBitmap(
            icon_edit.GetBitmap(resize=iconsize, buffer=1)
        )
        self.button_up_button.SetBitmap(icons8_up.GetBitmap(resize=iconsize, buffer=1))
        self.button_down_button.SetBitmap(
            icons8_down.GetBitmap(resize=iconsize, buffer=1)
        )

        sizer_button_buttons.Add(self.button_add_button, 0, wx.EXPAND, 0)
        sizer_button_buttons.Add(self.button_del_button, 0, wx.EXPAND, 0)
        sizer_button_buttons.Add(self.button_edit_button, 0, wx.EXPAND, 0)
        sizer_button_buttons.Add(self.button_up_button, 0, wx.EXPAND, 0)
        sizer_button_buttons.Add(self.button_down_button, 0, wx.EXPAND, 0)

        sizer_buttons.Add(self.list_buttons, 1, wx.EXPAND, 0)
        sizer_buttons.Add(sizer_button_buttons, 0, wx.EXPAND, 0)

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(sizer_available_panels, 1, wx.EXPAND, 0)
        sizer_right.Add(sizer_buttons, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_right, 1, wx.EXPAND, 0)

        # Explanatory tooltips
        self.button_add_panel.SetToolTip(
            _("Add the selected panel to the selected page")
        )
        self.button_apply.SetToolTip(_("Apply the configuration"))
        self.button_reset.SetToolTip(
            _("Reset the ribbon appearance to the default configuration")
        )

        self.button_add_page.SetToolTip(_("Add an additional page to the ribbon"))
        self.button_del_page.SetToolTip(_("Remove the selected page from the list"))
        self.button_down_page.SetToolTip(
            _("Decrease the position of the selected page")
        )
        self.button_up_page.SetToolTip(_("Increase the position of the selected page"))
        self.text_param_page.SetToolTip(_("Modify the label of the selected page"))

        self.button_del_panel.SetToolTip(_("Remove the selected panel from the list"))
        self.button_down_panel.SetToolTip(
            _("Decrease the position of the selected panel")
        )
        self.button_up_panel.SetToolTip(
            _("Increase the position of the selected panel")
        )
        self.check_labels.SetToolTip(
            _("Allow/suppress the display of labels beneath the icons in the ribbon")
        )

        self.button_add_button.SetToolTip(_("Add an additional user-defined button"))
        self.button_del_button.SetToolTip(
            _("Remove the selected user-defined button from the list")
        )
        self.button_down_button.SetToolTip(
            _("Decrease the position of the selected button")
        )
        self.button_up_button.SetToolTip(
            _("Increase the position of the selected button")
        )
        self.button_edit_button.SetToolTip(
            _("Modify the content of the selected button")
        )

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

        self.list_buttons.Bind(wx.EVT_LISTBOX, self.on_list_buttons_click)
        self.list_buttons.Bind(wx.EVT_LISTBOX_DCLICK, self.on_button_edit_button)

        self.text_param_page.Bind(wx.EVT_TEXT, self.on_text_label)
        self.text_param_page.Bind(wx.EVT_TEXT_ENTER, self.on_text_label_enter)

        self.button_add_page.Bind(wx.EVT_LEFT_DOWN, self.on_button_add_page_click)
        self.button_del_page.Bind(wx.EVT_LEFT_DOWN, self.on_button_page_delete)
        self.button_up_page.Bind(wx.EVT_LEFT_DOWN, self.on_move_page_up)
        self.button_down_page.Bind(wx.EVT_LEFT_DOWN, self.on_move_page_down)

        self.button_del_panel.Bind(wx.EVT_LEFT_DOWN, self.on_button_panel_delete)
        self.button_up_panel.Bind(wx.EVT_LEFT_DOWN, self.on_move_panel_up)
        self.button_down_panel.Bind(wx.EVT_LEFT_DOWN, self.on_move_panel_down)

        self.button_add_button.Bind(wx.EVT_LEFT_DOWN, self.on_button_add_button)
        self.button_del_button.Bind(wx.EVT_LEFT_DOWN, self.on_button_button_delete)
        self.button_up_button.Bind(wx.EVT_LEFT_DOWN, self.on_move_button_up)
        self.button_down_button.Bind(wx.EVT_LEFT_DOWN, self.on_move_button_down)
        self.button_edit_button.Bind(wx.EVT_LEFT_DOWN, self.on_button_edit_button)

        self.combo_ribbons.SetSelection(0)
        self.on_combo_ribbon(None)
        self.fill_button()

    # ---- Generic routines to access data

    def current_ribbon(self):
        return (
            self.context._ribbons[self.ribbon_identifier]
            if hasattr(self.context, "_ribbons")
            and self.ribbon_identifier in self.context._ribbons
            else None
        )

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
            self._config, self._config_buttons = rib.get_current_config()
        pages = []
        idx = 0
        for p_idx, page_entry in enumerate(
            sorted(self._config, key=lambda d: d["seq"])
        ):
            pages.append(f"{page_entry['id']} ({page_entry['label']})")
            if reposition is not None and page_entry["id"] == reposition:
                idx = p_idx
        self.list_pages.SetItems(pages)
        if pages:
            self.list_pages.SetSelection(idx)
        self.on_list_pages_click(None)

    def fill_button(self, reload=False, reposition=None):
        self.list_buttons.Clear()
        buttons = []
        idx = 0
        for b_idx, button_entry in enumerate(
            sorted(self._config_buttons, key=lambda d: d["seq"])
        ):
            buttons.append(
                f"{button_entry['id']} ({button_entry['label']}): {button_entry['action_left']}"
            )
            if reposition is not None and button_entry["id"] == reposition:
                idx = b_idx
        self.list_buttons.SetItems(buttons)
        if buttons:
            self.list_buttons.SetSelection(idx)
            self.on_list_buttons_click(None)

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
        if panels:
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
            self.check_labels.Enable(rib.allow_labels)
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
            tidx = term.find(" (")
            if tidx >= 0:
                page = term[:tidx]
                self.current_page = page
                self.fill_panels()
                p = self.get_page(page)
                if p is not None:
                    page_label = p["label"]
        self.text_param_page.SetValue(page_label)

    def on_button_page_delete(self, event):
        new_config = []
        new_config.extend(p for p in self._config if p["id"] != self.current_page)
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
            for p_idx, panel_entry in enumerate(
                sorted(panel_list, key=lambda d: d["seq"])
            ):
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
        # Write all user-defined buttons
        for idx, entry in enumerate(
            sorted(self._config_buttons, key=lambda d: d["seq"])
        ):
            section = f"Button_{idx + 1}"
            ob.storage.write_persistent(section, "id", entry["id"])
            ob.storage.write_persistent(section, "label", entry["label"])
            ob.storage.write_persistent(section, "tip", entry["tip"])
            ob.storage.write_persistent(section, "action_left", entry["action_left"])
            ob.storage.write_persistent(section, "action_right", entry["action_right"])
            ob.storage.write_persistent(section, "enable", entry["enable"])
            ob.storage.write_persistent(section, "visible", entry["visible"])
            ob.storage.write_persistent(section, "icon", entry["icon"])
            ob.storage.write_persistent(section, "seq", entry["seq"])

        ob.storage.write_configuration()
        ob.restart()
        # self.context.signal("ribbon_recreate", self.ribbon_identifier)

    def on_button_reset_click(self, event):
        rib = self.current_ribbon()
        if rib is None:
            return
        self._config, self._config_buttons = rib.get_default_config()
        self.fill_pages()
        self.fill_button()

    def on_list_buttons_click(self, event):
        idx = self.list_buttons.GetSelection()
        self.current_button = None if idx < 0 else self._config_buttons[idx]["id"]
        flag1 = idx >= 0
        self.button_del_button.Enable(flag1)
        self.button_down_button.Enable(flag1)
        self.button_up_button.Enable(flag1)
        self.button_edit_button.Enable(flag1)
        if idx < 0:
            return

    def on_move_button_up(self, event):
        newconfig = []
        for idx, entry in enumerate(
            sorted(self._config_buttons, key=lambda d: d["seq"])
        ):
            if entry["id"] == self.current_button and idx > 0:
                newconfig.insert(idx - 1, entry)
            else:
                newconfig.append(entry)
        for idx, entry in enumerate(newconfig):
            entry["seq"] = idx + 1
        self._config_buttons = newconfig
        self.fill_button(reposition=self.current_button)

    def on_move_button_down(self, event):
        newconfig = []
        for idx, entry in enumerate(
            sorted(self._config_buttons, key=lambda d: d["seq"], reverse=True)
        ):
            if entry["id"] == self.current_button and idx > 0:
                newconfig.insert(1, entry)
            else:
                newconfig.insert(0, entry)
        for idx, entry in enumerate(newconfig):
            entry["seq"] = idx + 1
        self._config_buttons = newconfig
        self.fill_button(reposition=self.current_button)

    def on_button_button_delete(self, event):
        new_config = []
        new_config.extend(
            p for p in self._config_buttons if p["id"] != self.current_button
        )
        if len(new_config) != self._config_buttons:
            self._config_buttons = new_config
            self.current_button = None
            self.fill_button()
            self.fill_panels()

    def on_button_add_button(self, event):
        button_idx = len(self._config_buttons) + 1
        newid = f"user_button_{button_idx}"
        newentry = {
            "id": newid,
            "label": f"Button {button_idx}",
            "enable": "always",
            "visible": "always",
            "action_left": "echo Enter your command here",
            "action_right": "",
            "icon": "icon_edit",
            "tip": _("This could be your tooltip"),
            "seq": button_idx,
        }
        self._config_buttons.append(newentry)
        self.current_button = newid
        self.fill_button(reposition=newid)
        self.fill_panels()
        # Edit it immediately...
        self.on_button_edit_button(None)

    def edit_a_button(self, entry):
        # We edit the thing in place if needed...
        dlg = wx.Dialog(
            self,
            wx.ID_ANY,
            _("Edit Button"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.context.themes.set_window_colors(dlg)
        sizer = wx.BoxSizer(wx.VERTICAL)

        line1 = wx.BoxSizer(wx.HORIZONTAL)
        label1 = wxStaticText(dlg, wx.ID_ANY, _("Label"))
        txt_label = TextCtrl(dlg, wx.ID_ANY, value=entry["label"])
        line1.Add(label1, 0, wx.EXPAND, 0)
        line1.Add(txt_label, 1, wx.EXPAND, 0)

        line2 = wx.BoxSizer(wx.HORIZONTAL)
        label2 = wxStaticText(dlg, wx.ID_ANY, _("Tooltip"))
        txt_tip = TextCtrl(dlg, wx.ID_ANY, value=entry["tip"])
        line2.Add(label2, 0, wx.EXPAND, 0)
        line2.Add(txt_tip, 1, wx.EXPAND, 0)

        line3 = wx.BoxSizer(wx.HORIZONTAL)
        label3 = wxStaticText(dlg, wx.ID_ANY, _("Action left click"))
        txt_action_left = TextCtrl(dlg, wx.ID_ANY, value=entry["action_left"])
        line3.Add(label3, 0, wx.EXPAND, 0)
        line3.Add(txt_action_left, 1, wx.EXPAND, 0)

        line4 = wx.BoxSizer(wx.HORIZONTAL)
        label4 = wxStaticText(dlg, wx.ID_ANY, _("Action right click"))
        txt_action_right = TextCtrl(dlg, wx.ID_ANY, value=entry["action_right"])
        line4.Add(label4, 0, wx.EXPAND, 0)
        line4.Add(txt_action_right, 1, wx.EXPAND, 0)

        rule_options = (
            _("Always"),
            _("When at least one element selected"),
            _("When at least two elemente selected"),
        )
        line5 = wx.BoxSizer(wx.HORIZONTAL)
        label5 = wxStaticText(dlg, wx.ID_ANY, _("Rule to enable"))
        combo_enable = wxComboBox(
            dlg, wx.ID_ANY, choices=rule_options, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        if entry["enable"] == "selected2":
            idx = 2
        elif entry["enable"] == "selected":
            idx = 1
        else:
            idx = 0
        combo_enable.SetSelection(idx)
        line5.Add(label5, 0, wx.EXPAND, 0)
        line5.Add(combo_enable, 1, wx.EXPAND, 0)

        line6 = wx.BoxSizer(wx.HORIZONTAL)
        label6 = wxStaticText(dlg, wx.ID_ANY, _("Rule to display"))
        combo_visible = wxComboBox(
            dlg, wx.ID_ANY, choices=rule_options, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        if entry["visible"] == "selected2":
            idx = 2
        elif entry["visible"] == "selected":
            idx = 1
        else:
            idx = 0
        combo_visible.SetSelection(idx)
        line6.Add(label6, 0, wx.EXPAND, 0)
        line6.Add(combo_visible, 1, wx.EXPAND, 0)

        import meerk40t.gui.icons as mkicons

        icon_list = []
        for icon in dir(mkicons):
            # print (entry)
            if icon.startswith("icon"):
                s = getattr(mkicons, icon)
                if isinstance(s, (mkicons.VectorIcon, mkicons.PyEmbeddedImage)):
                    icon_list.append(icon)

        line7 = wx.BoxSizer(wx.HORIZONTAL)
        label7 = wxStaticText(dlg, wx.ID_ANY, _("Icon"))
        combo_icon = wxComboBox(
            dlg, wx.ID_ANY, choices=icon_list, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        preview = wxStaticBitmap(dlg, wx.ID_ANY, size=dip_size(self, 30, 30))
        if entry["icon"] in icon_list:
            combo_icon.SetValue(entry["icon"])
        line7.Add(label7, 0, wx.EXPAND, 0)
        line7.Add(combo_icon, 1, wx.EXPAND, 0)

        line0 = wx.BoxSizer(wx.HORIZONTAL)
        line0.AddStretchSpacer(1)
        line0.Add(preview, 0, wx.EXPAND, 0)

        def on_icon(event):
            icon_name = combo_icon.GetValue()
            ps = preview.GetSize()
            if icon_name:
                icon = getattr(mkicons, icon_name, None)
                if icon:
                    icon_edit.GetBitmap
                    preview.SetBitmap(icon.GetBitmap(resize=ps[0]))

        combo_icon.Bind(wx.EVT_COMBOBOX, on_icon)
        on_icon(None)

        button_sizer = dlg.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(line0, 0, wx.EXPAND, 0)
        sizer.Add(line1, 0, wx.EXPAND, 0)
        sizer.Add(line2, 0, wx.EXPAND, 0)
        sizer.Add(line3, 0, wx.EXPAND, 0)
        sizer.Add(line4, 0, wx.EXPAND, 0)
        sizer.Add(line5, 0, wx.EXPAND, 0)
        sizer.Add(line6, 0, wx.EXPAND, 0)
        sizer.Add(line7, 0, wx.EXPAND, 0)
        sizer.Add(button_sizer, 1, wx.EXPAND, 0)

        xmax = 0
        ymax = 0
        labels = (label1, label2, label3, label4, label5, label6, label7)
        for ctrl in labels:
            ls = ctrl.GetSize()
            if ls[0] > xmax:
                xmax = ls[0]
            if ls[1] > ymax:
                ymax = ls[1]
        for ctrl in labels:
            ctrl.SetMinSize(wx.Size(xmax, ymax))
        for s in (line1, line2, line3, line4, line5, line6, line7):
            s.Layout()

        dlg.SetSizer(sizer)
        dlg.Layout()
        dlg.CenterOnParent()
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            entry["label"] = txt_label.GetValue()
            entry["tip"] = txt_tip.GetValue()
            entry["action_left"] = txt_action_left.GetValue()
            entry["action_right"] = txt_action_right.GetValue()
            ruler = ("always", "selected", "selected2")
            idx = combo_enable.GetSelection()
            idx = min(2, max(0, idx))  # between 0 and 2
            entry["enable"] = ruler[idx]
            idx = combo_visible.GetSelection()
            idx = min(2, max(0, idx))  # between 0 and 2
            entry["visible"] = ruler[idx]
            entry["icon"] = combo_icon.GetValue()

        dlg.Destroy()

    def on_button_edit_button(self, event):
        if self.current_button is None:
            return
        for entry in self._config_buttons:
            if entry["id"] == self.current_button:
                self.edit_a_button(entry)
                break
        self.fill_button(reposition=self.current_button)

    def pane_hide(self):
        pass

    def pane_show(self):
        pass
