import copy

import wx
import wx.lib.agw.ribbon as RB
# import wx.ribbon as RB
from wx import aui

from meerk40t.kernel import Job, lookup_listener, signal_listener
from meerk40t.svgelements import Color

from .icons import icons8_connected_50, icons8_opened_folder_50
from .mwindow import MWindow

_ = wx.GetTranslation

ID_PAGE_MAIN = 10
ID_PAGE_TOOL = 20
ID_PAGE_TOGGLE = 30

def debug_system_colors():
    reslist = list()
    slist = (
        (wx.SYS_COLOUR_SCROLLBAR, "The scrollbar grey area."),
        (wx.SYS_COLOUR_DESKTOP, "The desktop colour."),
        (wx.SYS_COLOUR_ACTIVECAPTION, "Active window caption colour."),
        (wx.SYS_COLOUR_INACTIVECAPTION, "Inactive window caption colour."),
        (wx.SYS_COLOUR_MENU, "Menu background colour."),
        (wx.SYS_COLOUR_WINDOW, "Window background colour."),
        (wx.SYS_COLOUR_WINDOWFRAME, "Window frame colour."),
        (wx.SYS_COLOUR_MENUTEXT, "Colour of the text used in the menus."),
        (wx.SYS_COLOUR_WINDOWTEXT, "Colour of the text used in generic windows."),
        (wx.SYS_COLOUR_CAPTIONTEXT, "Colour of the text used in captions, size boxes and scrollbar arrow boxes."),
        (wx.SYS_COLOUR_ACTIVEBORDER, "Active window border colour."),
        (wx.SYS_COLOUR_INACTIVEBORDER, "Inactive window border colour."),
        (wx.SYS_COLOUR_APPWORKSPACE, "Background colour for MDI applications."),
        (wx.SYS_COLOUR_HIGHLIGHT, "Colour of item(s) selected in a control."),
        (wx.SYS_COLOUR_HIGHLIGHTTEXT, "Colour of the text of item(s) selected in a control."),
        (wx.SYS_COLOUR_BTNFACE, "Face shading colour on push buttons."),
        (wx.SYS_COLOUR_BTNSHADOW, "Edge shading colour on push buttons."),
        (wx.SYS_COLOUR_GRAYTEXT, "Colour of greyed (disabled) text."),
        (wx.SYS_COLOUR_BTNTEXT, "Colour of the text on push buttons."),
        (wx.SYS_COLOUR_INACTIVECAPTIONTEXT, "Colour of the text in inactive captions."),
        (wx.SYS_COLOUR_BTNHIGHLIGHT, "Highlight colour for buttons."),
        (wx.SYS_COLOUR_3DDKSHADOW, "Dark shadow colour for three-dimensional display elements."),
        (wx.SYS_COLOUR_3DLIGHT, "Light colour for three-dimensional display elements."),
        (wx.SYS_COLOUR_INFOTEXT, "Text colour for tooltip controls."),
        (wx.SYS_COLOUR_INFOBK, "Background colour for tooltip controls."),
        (wx.SYS_COLOUR_LISTBOX, "Background colour for list-like controls."),
        (wx.SYS_COLOUR_HOTLIGHT, "Colour for a hyperlink or hot-tracked item."),
        (wx.SYS_COLOUR_GRADIENTACTIVECAPTION, "Right side colour in the colour gradient of an active window’s title bar."),
        (wx.SYS_COLOUR_GRADIENTINACTIVECAPTION, "Right side colour in the colour gradient of an inactive window’s title bar."),
        (wx.SYS_COLOUR_MENUHILIGHT, "The colour used to highlight menu items when the menu appears as a flat menu."),
        (wx.SYS_COLOUR_MENUBAR, "The background colour for the menu bar when menus appear as flat menus."),
        (wx.SYS_COLOUR_LISTBOXTEXT, "Text colour for list-like controls."),
        (wx.SYS_COLOUR_LISTBOXHIGHLIGHTTEXT, "Text colour for the unfocused selection of list-like controls."),
        # (wx.SYS_COLOUR_BACKGROUND, "Synonym for SYS_COLOUR_DESKTOP ."),
        # (wx.SYS_COLOUR_3DFACE, "Synonym for SYS_COLOUR_BTNFACE ."),
        # (wx.SYS_COLOUR_3DSHADOW, "Synonym for SYS_COLOUR_BTNSHADOW ."),
        # (wx.SYS_COLOUR_BTNHILIGHT, "Synonym for SYS_COLOUR_BTNHIGHLIGHT ."),
        # (wx.SYS_COLOUR_3DHIGHLIGHT, "Synonym for SYS_COLOUR_BTNHIGHLIGHT ."),
        # (wx.SYS_COLOUR_3DHILIGHT, "Synonym for SYS_COLOUR_BTNHIGHLIGHT ."),
        # (wx.SYS_COLOUR_FRAMEBK, "Synonym for SYS_COLOUR_BTNFACE "),
    )
    is_dark = False
    dark_bg = False
    try:
        sysappearance = wx.SystemSettings().GetAppearance()
        source = "Sysappearance"
        is_dark = sysappearance.IsDark()
        dark_bg = sysappearance.IsUsingDarkBackground()
    except:
        source = "Default"
        is_dark = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        dark_bg = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
    reslist.append("%s delivered: is_dark=%s, dark_bg=%s" % ( source, is_dark, dark_bg))
    for colpair in slist:
        syscol = wx.SystemSettings().GetColour(colpair[0])
        if syscol is None:
            s = "Null"
        else:
            try:
                s = syscol.GetAsString(wx.C2S_NAME)
            except AssertionError:
                s = syscol.GetAsString(wx.C2S_CSS_SYNTAX)
        reslist.append( "{col} for {desc}".format(col=s, desc=colpair[1]) )
    return reslist

def register_panel_ribbon(window, context):
    minh = 75 # 150
    pane = (
        aui.AuiPaneInfo()
        .Name("ribbon")
        .Top()
        .RightDockable(False)
        .LeftDockable(False)
        .MinSize(300, minh)
        .FloatingSize(640, minh)
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
        self.ribbon_bars = []
        self.ribbon_panels = []
        self.ribbon_pages = []

        # Some helper variables for showing / hiding the toolbar
        self.panels_shown = True
        self.minmax = None
        self.context = context
        self.stored_labels = {}
        self.stored_height = 0
        self.art_provider_count = 0

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
        evt_id = event.GetId()
        # cursor = event.GetPosition()
        # print("Id%d, cursor=%s" % (evt_id, cursor))
        bar = None
        active_button = 0
        for item in self.ribbon_bars:
            item_id = item.GetId()
            if item_id == evt_id:
                bar = item
                # Now look for the corresponding buttons...
                if not bar._hovered_button is None:
                    # print ("Hovered button: %d" % bar._hovered_button.base.id)
                    active_button = bar._hovered_button.base.id
                break
        if bar is None or active_button == 0:
            # Nothing found
            return

        for button in self.button_actions:
            my_id = button[1]
            my_code = button[5]
            if my_code is not None and my_id == active_button:
                # Found one...
                my_code(0)  # Needs a parameter....
                break

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

        show_tip = not self.context.disable_tool_tips
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
                    button_id = new_id,
                    label = button["label"],
                    bitmap = button["icon"].GetBitmap(resize=resize_param),
                    help_string = button["tip"] if show_tip else "",
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
                    bitmap_disabled = button["icon"].GetBitmap(resize=resize_param, color=Color("grey")),
                    help_string = button["tip"] if show_tip else "",
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
            button_bar.Bind(wx.EVT_RIGHT_UP, self.button_click_right)

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

    # @signal_listener("ribbonbar")
    # def on_rb_toggle(self, origin, showit, *args):
    #     self._ribbon.ShowPanels(True)


    @property
    def is_dark(self):
        try:
            sysappearance = wx.SystemSettings().GetAppearance()
            result = sysappearance.IsDark()
            dark_bg = sysappearance.IsUsingDarkBackground()
        except:
            result = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
            dark_bg = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        return result

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

        home = RB.RibbonPage(self._ribbon, ID_PAGE_MAIN, _("Home"), icons8_opened_folder_50.GetBitmap(resize=16),)
        self.ribbon_pages.append(home)
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
        self.ribbon_panels.append(self.project_panel)

        button_bar = RB.RibbonButtonBar(self.project_panel)
        self.project_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.control_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            "" if self.is_dark else _("Control"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )
        self.ribbon_panels.append(self.control_panel)

        button_bar = RB.RibbonButtonBar(self.control_panel)
        self.control_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.config_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            "" if self.is_dark else _("Configuration"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )
        self.ribbon_panels.append(self.config_panel)

        button_bar = RB.RibbonButtonBar(self.config_panel)
        self.config_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        tool = RB.RibbonPage(
            self._ribbon,
            ID_PAGE_TOOL,
            _("Tools"),
            icons8_opened_folder_50.GetBitmap(resize=16),
        )
        self.ribbon_pages.append(tool)

        self.tool_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.is_dark else _("Tools"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )
        self.ribbon_panels.append(self.tool_panel)

        button_bar = RB.RibbonButtonBar(self.tool_panel)
        self.tool_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.modify_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.is_dark else _("Modification"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )
        self.ribbon_panels.append(self.modify_panel)

        button_bar = RB.RibbonButtonBar(self.modify_panel)
        self.modify_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.geometry_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.is_dark else _("Geometry"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )
        self.ribbon_panels.append(self.geometry_panel)
        button_bar = RB.RibbonButtonBar(self.geometry_panel)
        self.geometry_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.align_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.is_dark else _("Alignment"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )
        self.ribbon_panels.append(self.align_panel)
        button_bar = RB.RibbonButtonBar(self.align_panel)
        self.align_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self._ribbon.Bind(RB.EVT_RIBBONBAR_PAGE_CHANGING, self.on_page_change)
        minmaxpage = RB.RibbonPage(self._ribbon, ID_PAGE_TOGGLE, "Click me")
        self.ribbon_pages.append(minmaxpage)

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
            slist = debug_system_colors()
            msg = ""
            for s in slist:
                msg += s + "\n"
            wx.MessageBox(msg, "Info", wx.OK | wx.ICON_INFORMATION)
            event.Veto()

# RIBBON_ART_BUTTON_BAR_LABEL_COLOUR = 16
# RIBBON_ART_BUTTON_BAR_HOVER_BORDER_COLOUR = 17
# RIBBON_ART_BUTTON_BAR_ACTIVE_BORDER_COLOUR = 22
# RIBBON_ART_GALLERY_BORDER_COLOUR = 27
# RIBBON_ART_GALLERY_BUTTON_ACTIVE_FACE_COLOUR = 40
# RIBBON_ART_GALLERY_ITEM_BORDER_COLOUR = 45
# RIBBON_ART_TAB_LABEL_COLOUR = 46
# RIBBON_ART_TAB_SEPARATOR_COLOUR = 47
# RIBBON_ART_TAB_SEPARATOR_GRADIENT_COLOUR = 48
# RIBBON_ART_TAB_BORDER_COLOUR = 59
# RIBBON_ART_PANEL_BORDER_COLOUR = 60
# RIBBON_ART_PANEL_BORDER_GRADIENT_COLOUR = 61
# RIBBON_ART_PANEL_MINIMISED_BORDER_COLOUR = 62
# RIBBON_ART_PANEL_MINIMISED_BORDER_GRADIENT_COLOUR = 63
# RIBBON_ART_PANEL_LABEL_COLOUR = 66
# RIBBON_ART_PANEL_HOVER_LABEL_BACKGROUND_COLOUR = 67
# RIBBON_ART_PANEL_HOVER_LABEL_BACKGROUND_GRADIENT_COLOUR = 68
# RIBBON_ART_PANEL_HOVER_LABEL_COLOUR = 69
# RIBBON_ART_PANEL_MINIMISED_LABEL_COLOUR = 70
# RIBBON_ART_PANEL_BUTTON_FACE_COLOUR = 75
# RIBBON_ART_PANEL_BUTTON_HOVER_FACE_COLOUR = 76
# RIBBON_ART_PAGE_BORDER_COLOUR = 77

# RIBBON_ART_TOOLBAR_BORDER_COLOUR = 86
# RIBBON_ART_TOOLBAR_HOVER_BORDER_COLOUR = 87
# RIBBON_ART_TOOLBAR_FACE_COLOUR = 88



def _update_ribbon_artprovider_for_dark_mode(provider):
    def _set_ribbon_colour(provider, art_id_list, colour):
        for id_ in art_id_list:
            try:
                provider.SetColour(id_, colour)
            except:
                # Not all colorcodes are supported by all providers.
                # So lets ignore it
                pass

    TEXTCOLOUR = wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNTEXT)

    BTNFACE_HOVER = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_HIGHLIGHT))
    INACTIVE_BG = copy.copy(
        wx.SystemSettings().GetColour(wx.SYS_COLOUR_INACTIVECAPTION)
    )
    INACTIVE_TEXT = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_GRAYTEXT))
    TOOLTIP_FG = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_INFOTEXT))
    TOOLTIP_BG = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_INFOBK))
    BTNFACE = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNFACE))
    BTNFACE_HOVER = BTNFACE_HOVER.ChangeLightness(50)
    HIGHLIGHT = copy.copy(wx.SystemSettings().GetColour(wx.SYS_COLOUR_HOTLIGHT))

    texts = [
        RB.RIBBON_ART_BUTTON_BAR_LABEL_COLOUR,
        RB.RIBBON_ART_PANEL_LABEL_COLOUR,
    ]
    _set_ribbon_colour(provider, texts, TEXTCOLOUR)
    disabled = [
       RB.RIBBON_ART_GALLERY_BUTTON_DISABLED_FACE_COLOUR,
       RB.RIBBON_ART_TAB_LABEL_COLOUR,
    ]
    _set_ribbon_colour(provider, disabled, INACTIVE_TEXT)

    backgrounds = [
        # Toolbar element backgrounds
        RB.RIBBON_ART_TOOL_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_TOOL_BACKGROUND_TOP_GRADIENT_COLOUR,
        RB.RIBBON_ART_TOOL_BACKGROUND_COLOUR,
        RB.RIBBON_ART_TOOL_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_TOOL_HOVER_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_TOOL_HOVER_BACKGROUND_TOP_GRADIENT_COLOUR,
        RB.RIBBON_ART_TOOL_HOVER_BACKGROUND_COLOUR,
        RB.RIBBON_ART_TOOL_HOVER_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_TOOL_ACTIVE_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_TOOL_ACTIVE_BACKGROUND_TOP_GRADIENT_COLOUR,
        RB.RIBBON_ART_TOOL_ACTIVE_BACKGROUND_COLOUR,
        RB.RIBBON_ART_TOOL_ACTIVE_BACKGROUND_GRADIENT_COLOUR,
        # Page Background
        RB.RIBBON_ART_PAGE_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_PAGE_BACKGROUND_TOP_GRADIENT_COLOUR,
        RB.RIBBON_ART_PAGE_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PAGE_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_PAGE_HOVER_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_PAGE_HOVER_BACKGROUND_TOP_GRADIENT_COLOUR,
        RB.RIBBON_ART_PAGE_HOVER_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PAGE_HOVER_BACKGROUND_GRADIENT_COLOUR,
        # Art Gallery
        RB.RIBBON_ART_GALLERY_HOVER_BACKGROUND_COLOUR,
        RB.RIBBON_ART_GALLERY_BUTTON_BACKGROUND_COLOUR,
        RB.RIBBON_ART_GALLERY_BUTTON_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_GALLERY_BUTTON_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_GALLERY_BUTTON_FACE_COLOUR,
        RB.RIBBON_ART_GALLERY_BUTTON_HOVER_BACKGROUND_COLOUR,
        RB.RIBBON_ART_GALLERY_BUTTON_HOVER_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_GALLERY_BUTTON_HOVER_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_GALLERY_BUTTON_HOVER_FACE_COLOUR,
        RB.RIBBON_ART_GALLERY_BUTTON_ACTIVE_BACKGROUND_COLOUR,
        RB.RIBBON_ART_GALLERY_BUTTON_ACTIVE_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_GALLERY_BUTTON_ACTIVE_BACKGROUND_TOP_COLOUR,

        # Panel backgrounds
        RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_PANEL_ACTIVE_BACKGROUND_TOP_GRADIENT_COLOUR,
        RB.RIBBON_ART_PANEL_LABEL_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PANEL_LABEL_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_PANEL_HOVER_LABEL_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PANEL_HOVER_LABEL_BACKGROUND_GRADIENT_COLOUR,
        # Tab Background
        RB.RIBBON_ART_TAB_CTRL_BACKGROUND_COLOUR,
        RB.RIBBON_ART_TAB_CTRL_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_TAB_HOVER_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_TAB_HOVER_BACKGROUND_TOP_GRADIENT_COLOUR,
        RB.RIBBON_ART_TAB_HOVER_BACKGROUND_COLOUR,
        RB.RIBBON_ART_TAB_HOVER_BACKGROUND_GRADIENT_COLOUR,
        RB.RIBBON_ART_TAB_ACTIVE_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_TAB_ACTIVE_BACKGROUND_TOP_GRADIENT_COLOUR,
        RB.RIBBON_ART_TAB_ACTIVE_BACKGROUND_COLOUR,
        RB.RIBBON_ART_TAB_ACTIVE_BACKGROUND_GRADIENT_COLOUR,
    ]
    _set_ribbon_colour(provider, backgrounds, BTNFACE)
    highlights  = [
        RB.RIBBON_ART_PANEL_HOVER_LABEL_BACKGROUND_COLOUR,
        RB.RIBBON_ART_PANEL_HOVER_LABEL_BACKGROUND_GRADIENT_COLOUR,
    ]
    _set_ribbon_colour(provider, highlights, HIGHLIGHT)
    borders = [
        RB.RIBBON_ART_PANEL_BUTTON_HOVER_FACE_COLOUR,
    ]
    _set_ribbon_colour(provider, borders, wx.RED)

    lowlights = [
        RB.RIBBON_ART_TAB_HOVER_BACKGROUND_TOP_COLOUR,
        RB.RIBBON_ART_TAB_HOVER_BACKGROUND_TOP_GRADIENT_COLOUR,
    ]
    _set_ribbon_colour(provider, lowlights, INACTIVE_BG)
