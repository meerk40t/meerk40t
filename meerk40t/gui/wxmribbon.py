import copy

import wx
import wx.ribbon as RB
from wx import aui

from meerk40t.kernel import Job, lookup_listener, signal_listener

from .icons import icons8_connected_50, icons8_opened_folder_50
from .mwindow import MWindow

_ = wx.GetTranslation


def register_panel_ribbon(window, context):
    ribbon = RibbonPanel(window, wx.ID_ANY, context=context)

    pane = (
        aui.AuiPaneInfo()
        .Name("ribbon")
        .Top()
        .RightDockable(False)
        .LeftDockable(False)
        .MinSize(300, 150)
        .FloatingSize(640, 150)
        .Caption(_("Ribbon"))
        .CaptionVisible(not context.pane_lock)
    )
    pane.dock_proportion = 640
    pane.control = ribbon

    window.on_pane_add(pane)
    context.register("pane/ribbon", pane)


class RibbonPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self._job = Job(
            process=self._perform_realization,
            job_name="realize_ribbon_bar",
            interval=0.1,
            times=1,
            run_main=True,
        )

        # Define Ribbon.
        self._ribbon = RB.RibbonBar(
            self,
            style=RB.RIBBON_BAR_FLOW_HORIZONTAL
            | RB.RIBBON_BAR_SHOW_PAGE_LABELS
            | RB.RIBBON_BAR_SHOW_PANEL_EXT_BUTTONS
            | RB.RIBBON_BAR_SHOW_TOGGLE_BUTTON
            | RB.RIBBON_BAR_SHOW_HELP_BUTTON,
        )
        self.__set_ribbonbar()

        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(self._ribbon, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # self._ribbon
        self.pipe_state = None
        self._ribbon_dirty = False
        self.button_actions = []

    def button_click(self, event):
        # Let's figure out what kind of action we need to perform
        # button["action"]
        evt_id = event.GetId()
        # print("button_click called for %d" % evt_id)
        for button in self.button_actions:
            parent_obj = button[0]
            my_id = button[1]
            my_grp = button[2]
            my_code = button[3]
            if my_id == evt_id:
                button[4] = not button[4]
                if my_grp != "":
                    if button[4]:  # got toggled
                        for obutton in self.button_actions:
                            if obutton[2] == my_grp and obutton[1] != my_id:
                                obutton[0].ToggleButton(obutton[1], False)
                    else:  # got untoggled...
                        # so let' activate the first button of the group (implicitly defined as default...)
                        for obutton in self.button_actions:
                            if obutton[2] == my_grp:
                                obutton[0].ToggleButton(obutton[1], True)
                                mevent = event.Clone()
                                mevent.SetId(obutton[1])
                                # print("Calling master...")
                                self.button_click(mevent)
                                # exit
                                return
                my_code(0)  # Needs a parameter....
                break

    def set_buttons(self, new_values, button_bar):
        button_bar.ClearButtons()
        buttons = []
        for button, name, sname in new_values:
            buttons.append(button)

        def sort_priority(elem):
            return elem["priority"] if "priority" in elem else 0

        buttons.sort(key=sort_priority)

        for button in buttons:
            new_id = wx.NewId()
            toggle_grp = ""
            if "size" in button:
                resize_param = button["size"]
            else:
                resize_param = None
            if "alt-action" in button:
                button_bar.AddHybridButton(
                    new_id,
                    button["label"],
                    button["icon"].GetBitmap(resize=resize_param),
                    button["tip"],
                )

                def drop_bind(alt_action):
                    def on_dropdown(event):
                        menu = wx.Menu()
                        for act_label, act_func in alt_action:
                            hybrid_id = wx.NewId()
                            menu.Append(hybrid_id, act_label)
                            button_bar.Bind(wx.EVT_MENU, act_func, id=hybrid_id)
                        event.PopupMenu(menu)

                    return on_dropdown

                button_bar.Bind(
                    RB.EVT_RIBBONBUTTONBAR_DROPDOWN_CLICKED,
                    drop_bind(button["alt-action"]),
                    id=new_id,
                )
            else:
                if "toggle" in button:
                    toggle_grp = button["toggle"]
                    bkind = RB.RIBBON_BUTTON_TOGGLE
                else:
                    bkind = RB.RIBBON_BUTTON_NORMAL

                button_bar.AddButton(
                    new_id,
                    button["label"],
                    button["icon"].GetBitmap(resize=resize_param),
                    button["tip"],
                    kind=bkind,
                )
            self.button_actions.append(
                [
                    button_bar,
                    new_id,
                    toggle_grp,
                    button["action"],
                    False,
                ]  # Parent, ID, Toggle, Action, State
            )
            # button_bar.Bind(RB.EVT_RIBBONBUTTONBAR_CLICKED, button_clickbutton["action"], id=new_id)
            button_bar.Bind(
                RB.EVT_RIBBONBUTTONBAR_CLICKED, self.button_click, id=new_id
            )
        self.ensure_realize()
        # Disable buttons by default
        self.on_emphasis_change(None)

    @lookup_listener("button/project")
    def set_project_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.project_button_bar)

    @lookup_listener("button/control")
    def set_control_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.control_button_bar)

    @lookup_listener("button/config")
    def set_config_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.config_button_bar)

    @lookup_listener("button/modify")
    def set_modify_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.modify_button_bar)

    @lookup_listener("button/tool")
    def set_tool_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.tool_button_bar)

    @lookup_listener("button/geometry")
    def set_geometry_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.geometry_button_bar)

    @lookup_listener("button/align")
    def set_align_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.align_button_bar)

    def enable_all_buttons_on_bar(self, button_bar, active):
        for i in range(button_bar.GetButtonCount()):
            btn = button_bar.GetItem(i)
            b_id = button_bar.GetItemId(btn)
            button_bar.EnableButton(b_id, active)

    @signal_listener("emphasized")
    def on_emphasis_change(self, origin, *args):
        active = self.context.elements.has_emphasis()
        self.enable_all_buttons_on_bar(self.geometry_button_bar, active)
        self.enable_all_buttons_on_bar(self.align_button_bar, active)
        self.enable_all_buttons_on_bar(self.modify_button_bar, active)

    @property
    def is_dark(self):
        return wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127

    def ensure_realize(self):
        self._ribbon_dirty = True
        self.context.schedule(self._job)

    def _perform_realization(self, *args):
        self._ribbon_dirty = False
        self._ribbon.Realize()

    def __set_ribbonbar(self):
        self.ribbonbar_caption_visible = False

        if self.is_dark:
            provider = self._ribbon.GetArtProvider()
            _update_ribbon_artprovider_for_dark_mode(provider)
        self.ribbon_position_aspect_ratio = True
        self.ribbon_position_ignore_update = False

        home = RB.RibbonPage(
            self._ribbon,
            wx.ID_ANY,
            _("Home"),
            icons8_opened_folder_50.GetBitmap(),
        )
        self.Bind(
            RB.EVT_RIBBONBAR_HELP_CLICK,
            lambda e: self.context("webhelp help\n"),
        )

        self.project_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            "" if self.is_dark else _("Project"),
            style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        )

        button_bar = RB.RibbonButtonBar(self.project_panel)
        self.project_button_bar = button_bar

        self.control_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            "" if self.is_dark else _("Control"),
            icons8_opened_folder_50.GetBitmap(),
            style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        )
        button_bar = RB.RibbonButtonBar(self.control_panel)
        self.control_button_bar = button_bar

        self.config_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            "" if self.is_dark else _("Configuration"),
            icons8_opened_folder_50.GetBitmap(),
            style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        )
        button_bar = RB.RibbonButtonBar(self.config_panel)
        self.config_button_bar = button_bar

        tool = RB.RibbonPage(
            self._ribbon,
            wx.ID_ANY,
            _("Tools"),
            icons8_opened_folder_50.GetBitmap(),
        )

        self.tool_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.is_dark else _("Tools"),
            icons8_opened_folder_50.GetBitmap(),
            style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        )
        button_bar = RB.RibbonButtonBar(self.tool_panel)
        self.tool_button_bar = button_bar

        self.modify_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.is_dark else _("Modification"),
            icons8_opened_folder_50.GetBitmap(),
            # style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        )
        button_bar = RB.RibbonButtonBar(self.modify_panel)
        self.modify_button_bar = button_bar

        self.geometry_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.is_dark else _("Geometry"),
            icons8_opened_folder_50.GetBitmap(),
            style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        )
        button_bar = RB.RibbonButtonBar(self.geometry_panel)
        self.geometry_button_bar = button_bar

        self.align_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.is_dark else _("Alignment"),
            icons8_opened_folder_50.GetBitmap(),
            # style=RB.RIBBON_PANEL_NO_AUTO_MINIMISE,
        )
        button_bar = RB.RibbonButtonBar(self.align_panel)
        self.align_button_bar = button_bar

        self.ensure_realize()

    def pane_show(self):
        pass

    def pane_hide(self):
        pass


class Ribbon(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(423, 121, *args, **kwds)

        self.panel = RibbonPanel(self, wx.ID_ANY, context=self.context)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_connected_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Ribbon"))

    def window_open(self):
        try:
            self.panel.pane_show()
        except AttributeError:
            pass

    def window_close(self):
        try:
            self.panel.pane_hide()
        except AttributeError:
            pass


def _update_ribbon_artprovider_for_dark_mode(provider: RB.RibbonArtProvider) -> None:
    def _set_ribbon_colour(
        provider: RB.RibbonArtProvider, art_id_list: list, colour: wx.Colour
    ) -> None:
        for id_ in art_id_list:
            provider.SetColour(id_, colour)

    TEXTCOLOUR = wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNTEXT)

    BTNFACE_HOVER = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_HIGHLIGHT))
    INACTIVE_BG = copy.copy(
        wx.SystemSettings().GetColour(wx.SYS_COLOUR_INACTIVECAPTION)
    )
    INACTIVE_TEXT = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_GRAYTEXT))
    BTNFACE = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNFACE))
    BTNFACE_HOVER = BTNFACE_HOVER.ChangeLightness(50)

    texts = [
        RB.RIBBON_ART_BUTTON_BAR_LABEL_COLOUR,
        RB.RIBBON_ART_PANEL_LABEL_COLOUR,
    ]
    try:  # wx 4.0 compat, not supported on that
        texts.extend(
            [
                RB.RIBBON_ART_TAB_ACTIVE_LABEL_COLOUR,
                RB.RIBBON_ART_TAB_HOVER_LABEL_COLOUR,
            ]
        )
        _set_ribbon_colour(provider, [RB.RIBBON_ART_TAB_LABEL_COLOUR], INACTIVE_TEXT)
    except AttributeError:
        _set_ribbon_colour(provider, [RB.RIBBON_ART_TAB_LABEL_COLOUR], TEXTCOLOUR)
        pass
    _set_ribbon_colour(provider, texts, TEXTCOLOUR)

    backgrounds = [
        RB.RIBBON_ART_BUTTON_BAR_HOVER_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_BUTTON_BAR_HOVER_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_TOP_GRADIENT_COLOUR,
        RB.RIBBON_ART_PANEL_LABEL_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PANEL_LABEL_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_PANEL_HOVER_LABEL_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PANEL_HOVER_LABEL_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_TAB_HOVER_BACKGROUND_COLOUR,
        RB.RIBBON_ART_TAB_ACTIVE_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_TAB_ACTIVE_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PAGE_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_PAGE_BACKGROUND_TOP_GRADIENT_COLOUR,
        RB.RIBBON_ART_PAGE_HOVER_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PAGE_HOVER_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_TAB_CTRL_BACKGROUND_COLOUR,
        RB.RIBBON_ART_TAB_CTRL_BACKGROUND_GRADIENT_COLOUR,
    ]
    _set_ribbon_colour(provider, backgrounds, BTNFACE)
    _set_ribbon_colour(
        provider,
        [
            RB.RIBBON_ART_TAB_HOVER_BACKGROUND_COLOUR,
            RB.RIBBON_ART_TAB_HOVER_BACKGROUND_GRADIENT_COLOUR,
            RB.RIBBON_ART_TAB_HOVER_BACKGROUND_TOP_COLOUR,
            RB.RIBBON_ART_TAB_HOVER_BACKGROUND_TOP_GRADIENT_COLOUR,
        ],
        INACTIVE_BG,
    )
