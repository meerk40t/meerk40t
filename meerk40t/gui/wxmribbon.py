import copy

import wx
import wx.lib.agw.ribbon as RB
# import wx.ribbon as RB
from wx import aui

from meerk40t.kernel import Job, lookup_listener, signal_listener

from .icons import icons8_connected_50, icons8_opened_folder_50
from .mwindow import MWindow

_ = wx.GetTranslation

ID_PAGE_MAIN = 10
ID_PAGE_TOOL = 20
ID_PAGE_TOGGLE = 30

def register_panel_ribbon(window, context):
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
    ribbon = RibbonPanel(window, wx.ID_ANY, context=context)
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
        self.buttons = []
        self.button_bars = []
        # Some helper variables for showing / hiding the toolbar
        self.panels_shown = True
        self.minmax = None
        self.context = context
        self.stored_labels = {}

        self.button_actions = []

        # Define Ribbon.
        self._ribbon = RB.RibbonBar(
            self,
            agwStyle=RB.RIBBON_BAR_DEFAULT_STYLE|RB.RIBBON_BAR_SHOW_PANEL_EXT_BUTTONS|RB.RIBBON_BAR_SHOW_PANEL_MINIMISE_BUTTONS
        )
        self.__set_ribbonbar()

        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(self._ribbon, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # self._ribbon
        self.pipe_state = None
        self._ribbon_dirty = False

    def button_click_right(self, event):
        """
        Handles the ``wx.EVT_RIGHT_DOWN`` event
        :param `event`: a :class:`MouseEvent` event to be processed.
        """
        print("right button_click called for event:", event, vars(event))
        evt_id = event.GetId()
        cursor = event.GetPosition()
        print("Id%d, cursor=%s" % (evt_id, cursor))
        bar = None
        active_button = 0
        for item in self.button_bars:
            item_id = item.GetId()
            if item_id == evt_id:
                bar = item
                # Now look for the corresponding buttons...
                if bar._hovered_button is None:
                    print ("No hovered button")
                else:
                    print ("Hovered button: %d" % bar._hovered_button.base.id)
                    active_button = bar._hovered_button.base.id
                if bar._active_button is None:
                    print ("No active button")
                else:
                    print ("Active button: %d" % bar._active_button.base.id)


                break
        if bar is None:
            # Nothing found
            event.Skip()
            return
        # Debug
        for button in bar._buttons:
            print (button.id, button.label)


        if active_button:
            for button in self.button_actions:
                parent_obj = button[0]
                my_id = button[1]
                my_grp = button[2]
                my_code = button[5]
                if my_code is not None and my_id == active_button:
                    print ("Found one...")
                    my_code(0)  # Needs a parameter....
                    break
            print ("There was no action")
        else:
            print ("There wasnt an active button, strange")
        event.Skip()

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
                    button_id = new_id,
                    label = button["label"],
                    bitmap = button["icon"].GetBitmap(resize=resize_param),
                    help_string = button["tip"],
                    kind = bkind,
                )
            if "right" in button:
                self.button_actions.append(
                    [
                        button_bar,
                        new_id,
                        toggle_grp,
                        button["action"],
                        False,
                        button["right"],
                    ]  # Parent, ID, Toggle, Action, State, Right-Mouse-Action
                )
            else:
                self.button_actions.append(
                    [
                        button_bar,
                        new_id,
                        toggle_grp,
                        button["action"],
                        False,
                        None,
                    ]  # Parent, ID, Toggle, Action, State, Right-Mouse-Action
                )

            # button_bar.Bind(RB.EVT_RIBBONBUTTONBAR_CLICKED, button_clickbutton["action"], id=new_id)
            button_bar.Bind(
                RB.EVT_RIBBONBUTTONBAR_CLICKED, self.button_click, id=new_id
            )
            button_bar.Bind(wx.EVT_RIGHT_DOWN, self.button_click_right)

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
        for button in self.button_actions:
            if button[0] is button_bar:
                b_id = button[1]
                button_bar.EnableButton(b_id, active)

    @signal_listener("emphasized")
    def on_emphasis_change(self, origin, *args):
        active = self.context.elements.has_emphasis()
        self.enable_all_buttons_on_bar(self.geometry_button_bar, active)
        self.enable_all_buttons_on_bar(self.align_button_bar, active)
        self.enable_all_buttons_on_bar(self.modify_button_bar, active)

    @signal_listener("ribbonbar")
    def on_rb_toggle(self, origin, showit, *args):
        def toggle_label(bar):
            for button in bar._buttons:
                b_id = str(button.id)
                old_label = button.label
                if showit:
                    try:
                        old_label = self.stored_labels[b_id]
                    except KeyError:
                        old_label = "?? %s" % b_id
                    button.label=old_label
                else:
                    self.stored_labels[b_id] = old_label
                    button.label = ""

        if showit:
            if len(self.stored_labels) == 0:
                return
        else:
            self.stored_labels = {}
        toggle_label(self.geometry_button_bar)
        toggle_label(self.align_button_bar)
        toggle_label(self.modify_button_bar)
        toggle_label(self.project_button_bar)
        toggle_label(self.control_button_bar)
        toggle_label(self.config_button_bar)
        # Resize the panels, the pages, the bar, the aui_pane...
        for bar in self.button_bars:
            bar.Realise()
        self._ribbon.Realise()
        self._ribbon.Refresh()

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
            # _update_ribbon_artprovider_for_dark_mode(provider)
        self.ribbon_position_aspect_ratio = True
        self.ribbon_position_ignore_update = False

        home = RB.RibbonPage(self._ribbon, ID_PAGE_MAIN, _("Home"), icons8_opened_folder_50.GetBitmap(resize=16),)
        #self.Bind(
        #    RB.EVT_RIBBONBAR_HELP_CLICK,
        #    lambda e: self.context("webhelp help\n"),
        #)

        self.project_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            "" if self.is_dark else _("Project"),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )

        button_bar = RB.RibbonButtonBar(self.project_panel)
        self.project_button_bar = button_bar
        self.button_bars.append(button_bar)

        self.control_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            "" if self.is_dark else _("Control"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )
        button_bar = RB.RibbonButtonBar(self.control_panel)
        self.control_button_bar = button_bar
        self.button_bars.append(button_bar)

        self.config_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            "" if self.is_dark else _("Configuration"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )
        button_bar = RB.RibbonButtonBar(self.config_panel)
        self.config_button_bar = button_bar
        self.button_bars.append(button_bar)

        tool = RB.RibbonPage(
            self._ribbon,
            ID_PAGE_TOOL,
            _("Tools"),
            icons8_opened_folder_50.GetBitmap(resize=16),
        )

        self.tool_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.is_dark else _("Tools"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )
        button_bar = RB.RibbonButtonBar(self.tool_panel)
        self.tool_button_bar = button_bar
        self.button_bars.append(button_bar)

        self.modify_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.is_dark else _("Modification"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )
        button_bar = RB.RibbonButtonBar(self.modify_panel)
        self.modify_button_bar = button_bar
        self.button_bars.append(button_bar)

        self.geometry_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.is_dark else _("Geometry"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )
        button_bar = RB.RibbonButtonBar(self.geometry_panel)
        self.geometry_button_bar = button_bar
        self.button_bars.append(button_bar)

        self.align_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.is_dark else _("Alignment"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )
        button_bar = RB.RibbonButtonBar(self.align_panel)
        self.align_button_bar = button_bar
        self.button_bars.append(button_bar)

        self._ribbon.Bind(RB.EVT_RIBBONBAR_PAGE_CHANGING, self.on_page_change)

        minmaxpage = RB.RibbonPage(self._ribbon, ID_PAGE_TOGGLE, _("_"))
        self.ensure_realize()

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    def on_page_change(self, event):
        page = event.GetPage()
        p_id = page.GetId()
        # print ("Page Changing to ", p_id)
        if p_id  == ID_PAGE_TOGGLE:
            self.panels_shown = not self.panels_shown
            if self.panels_shown:
                newlabel = "-"
            else:
                newlabel = "+"
            page.SetLabel(newlabel)
            # event.Skip()
            self.context.signal("ribbonbar", self.panels_shown)
            event.Veto()


# class Ribbon(MWindow):
#     def __init__(self, *args, **kwds):
#         print ("Ribbon init start")
#         super().__init__(423, 121, *args, **kwds)

#         print ("Super init done")
#         self.panel = RibbonPanel(self, wx.ID_ANY, context=self.context)
#         print ("RibbonPanel done")
#         self.add_module_delegate(self.panel)
#         print ("Module-delegate done")
#         _icon = wx.NullIcon
#         _icon.CopyFromBitmap(icons8_connected_50.GetBitmap())
#         self.SetIcon(_icon)
#         self.SetTitle(_("Ribbon"))

#     def window_open(self):
#         try:
#             self.panel.pane_show()
#         except AttributeError:
#             pass

#     def window_close(self):
#         try:
#             self.panel.pane_hide()
#         except AttributeError:
#             pass


# def _update_ribbon_artprovider_for_dark_mode(provider: RB.RibbonArtProvider) -> None:
#     def _set_ribbon_colour(
#         provider: RB.RibbonArtProvider, art_id_list: list, colour: wx.Colour
#     ) -> None:
#         for id_ in art_id_list:
#             provider.SetColour(id_, colour)

#     TEXTCOLOUR = wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNTEXT)

#     BTNFACE_HOVER = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_HIGHLIGHT))
#     INACTIVE_BG = copy.copy(
#         wx.SystemSettings().GetColour(wx.SYS_COLOUR_INACTIVECAPTION)
#     )
#     INACTIVE_TEXT = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_GRAYTEXT))
#     BTNFACE = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNFACE))
#     BTNFACE_HOVER = BTNFACE_HOVER.ChangeLightness(50)

#     texts = [
#         RB.RIBBON_ART_BUTTON_BAR_LABEL_COLOUR,
#         RB.RIBBON_ART_PANEL_LABEL_COLOUR,
#     ]
#     try:  # wx 4.0 compat, not supported on that
#         texts.extend(
#             [
#                 RB.RIBBON_ART_TAB_ACTIVE_LABEL_COLOUR,
#                 RB.RIBBON_ART_TAB_HOVER_LABEL_COLOUR,
#             ]
#         )
#         _set_ribbon_colour(provider, [RB.RIBBON_ART_TAB_LABEL_COLOUR], INACTIVE_TEXT)
#     except AttributeError:
#         _set_ribbon_colour(provider, [RB.RIBBON_ART_TAB_LABEL_COLOUR], TEXTCOLOUR)
#         pass
#     _set_ribbon_colour(provider, texts, TEXTCOLOUR)

#     backgrounds = [
#         RB.RIBBON_ART_BUTTON_BAR_HOVER_BACKGROUND_TOP_COLOUR,
#         RB.RIBBON_ART_BUTTON_BAR_HOVER_BACKGROUND_COLOUR,
#         RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_COLOUR,
#         RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_GRADIENT_COLOUR,
#         RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_TOP_COLOUR,
#         RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_TOP_GRADIENT_COLOUR,
#         RB.RIBBON_ART_PANEL_LABEL_BACKGROUND_COLOUR,
#         RB.RIBBON_ART_PANEL_LABEL_BACKGROUND_GRADIENT_COLOUR,
#         RB.RIBBON_ART_PANEL_HOVER_LABEL_BACKGROUND_COLOUR,
#         RB.RIBBON_ART_PANEL_HOVER_LABEL_BACKGROUND_GRADIENT_COLOUR,
#         RB.RIBBON_ART_TAB_HOVER_BACKGROUND_COLOUR,
#         RB.RIBBON_ART_TAB_ACTIVE_BACKGROUND_TOP_COLOUR,
#         RB.RIBBON_ART_TAB_ACTIVE_BACKGROUND_COLOUR,
#         RB.RIBBON_ART_PAGE_BACKGROUND_TOP_COLOUR,
#         RB.RIBBON_ART_PAGE_BACKGROUND_TOP_GRADIENT_COLOUR,
#         RB.RIBBON_ART_PAGE_HOVER_BACKGROUND_COLOUR,
#         RB.RIBBON_ART_PAGE_HOVER_BACKGROUND_GRADIENT_COLOUR,
#         RB.RIBBON_ART_TAB_CTRL_BACKGROUND_COLOUR,
#         RB.RIBBON_ART_TAB_CTRL_BACKGROUND_GRADIENT_COLOUR,
#     ]
#     _set_ribbon_colour(provider, backgrounds, BTNFACE)
#     _set_ribbon_colour(
#         provider,
#         [
#             RB.RIBBON_ART_TAB_HOVER_BACKGROUND_COLOUR,
#             RB.RIBBON_ART_TAB_HOVER_BACKGROUND_GRADIENT_COLOUR,
#             RB.RIBBON_ART_TAB_HOVER_BACKGROUND_TOP_COLOUR,
#             RB.RIBBON_ART_TAB_HOVER_BACKGROUND_TOP_GRADIENT_COLOUR,
#         ],
#         INACTIVE_BG,
#     )
