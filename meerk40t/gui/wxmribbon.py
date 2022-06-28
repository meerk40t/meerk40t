import copy
import threading
import wx
import wx.lib.agw.ribbon as RB

# import wx.ribbon as RB
from wx.lib.agw import aui

from meerk40t.kernel import Job, lookup_listener, signal_listener
from meerk40t.svgelements import Color
from .icons import icons8_connected_50, icons8_opened_folder_50
from .mwindow import MWindow

_ = wx.GetTranslation

ID_PAGE_MAIN = 10
ID_PAGE_TOOL = 20
ID_PAGE_TOGGLE = 30


class RibbonButtonBar(RB.RibbonButtonBar):
    def __init__(
        self,
        parent,
        id=wx.ID_ANY,
        pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        agwStyle=0,
    ):
        super().__init__(parent, id, pos, size, agwStyle)
        self.screen_refresh_lock = threading.Lock()

    def SetBitmap(self, id,
            bitmap,
            bitmap_small=wx.NullBitmap,
            bitmap_disabled=wx.NullBitmap,
            bitmap_small_disabled=wx.NullBitmap):
        result = False
        for base in self._buttons:
            # base = button.base
            if base.id == id:
                base.bitmap_large = bitmap
                if not base.bitmap_large.IsOk():
                    base.bitmap_large = self.MakeResizedBitmap(base.bitmap_small, self._bitmap_size_large)

                elif base.bitmap_large.GetSize() != self._bitmap_size_large:
                    base.bitmap_large = self.MakeResizedBitmap(base.bitmap_large, self._bitmap_size_large)

                base.bitmap_small = bitmap_small

                if not base.bitmap_small.IsOk():
                    base.bitmap_small = self.MakeResizedBitmap(base.bitmap_large, self._bitmap_size_small)

                elif base.bitmap_small.GetSize() != self._bitmap_size_small:
                    base.bitmap_small = self.MakeResizedBitmap(base.bitmap_small, self._bitmap_size_small)

                base.bitmap_large_disabled = bitmap_disabled

                if not base.bitmap_large_disabled.IsOk():
                    base.bitmap_large_disabled = self.MakeDisabledBitmap(base.bitmap_large)

                base.bitmap_small_disabled = bitmap_small_disabled

                if not base.bitmap_small_disabled.IsOk():
                    base.bitmap_small_disabled = self.MakeDisabledBitmap(base.bitmap_small)
                result = True
                break
        return result

    def OnPaint(self, event):
        """
        Handles the ``wx.EVT_PAINT`` event for :class:`RibbonButtonBar`.

        :param `event`: a :class:`PaintEvent` event to be processed.
        """
        if self.screen_refresh_lock.acquire(timeout=0.2):

            dc = wx.AutoBufferedPaintDC(self)
            if not dc is None:

                self._art.DrawButtonBarBackground(dc, self, wx.Rect(0, 0, *self.GetSize()))

                try:
                    layout = self._layouts[self._current_layout]
                except IndexError:
                    return

                for button in layout.buttons:
                    base = button.base

                    bitmap = base.bitmap_large
                    bitmap_small = base.bitmap_small

                    if base.state & RB.RIBBON_BUTTONBAR_BUTTON_DISABLED:
                        bitmap = base.bitmap_large_disabled
                        bitmap_small = base.bitmap_small_disabled

                    rect = wx.Rect(
                        button.position + self._layout_offset, base.sizes[button.size].size
                    )
                    self._art.DrawButtonBarButton(
                        dc,
                        self,
                        rect,
                        base.kind,
                        base.state | button.size,
                        base.label,
                        bitmap,
                        bitmap_small,
                    )
            # else:
            #     print("DC was faulty")
            self.screen_refresh_lock.release()
        # else:
        #     print ("OnPaint was locked...")



def register_panel_ribbon(window, context):
    # debug_system_colors()
    minh = 150
    pane = (
        aui.AuiPaneInfo()
        .Name("ribbon")
        .Top()
        .RightDockable(False)
        .LeftDockable(False)
        .MinSize(wx.Size(300, minh))
        .FloatingSize(wx.Size(640, minh))
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
        self.ribbon_buttons = []
        self.darkmode = False

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
            agwStyle=RB.RIBBON_BAR_DEFAULT_STYLE
            | RB.RIBBON_BAR_SHOW_PANEL_EXT_BUTTONS
            | RB.RIBBON_BAR_SHOW_PANEL_MINIMISE_BUTTONS,
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
        button_bar._current_layout = 0
        button_bar._hovered_button = None
        button_bar._active_button = None
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
                    button_id=new_id,
                    label=button["label"],
                    bitmap=button["icon"].GetBitmap(resize=resize_param),
                    help_string=button["tip"] if show_tip else "",
                )
                self.ribbon_buttons.append((new_id, button["icon"], resize_param))
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
                    button_id=new_id,
                    label=button["label"],
                    bitmap=button["icon"].GetBitmap(resize=resize_param),
                    bitmap_disabled=button["icon"].GetBitmap(
                        resize=resize_param, color=Color("grey")
                    ),
                    help_string=button["tip"] if show_tip else "",
                    kind=bkind,
                )
                self.ribbon_buttons.append((new_id, button["icon"], resize_param))

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

    @signal_listener("gui_appearance")
    def gui_changed(self, origin, *args):
        self.darkmode = getattr(self.context, "theme_isdark", False)
        self._update_ribbon_artprovider()
        for panel in self.ribbon_panels:
            panel[0].Label = "" if self.darkmode else panel[1]
        for button in self.ribbon_buttons:
            but_id = button[0]
            bitmap = button[1].GetBitmap(resize=button[2])
            bitmap_disabled = button[1].GetBitmap(resize=button[2], color=Color("grey"))
            for bars in self.ribbon_bars:
                found = bars.SetBitmap(
                    but_id,
                    bitmap = bitmap,
                    bitmap_disabled=bitmap_disabled)
                if found:
                    break
        self._ribbon.Refresh()

    @signal_listener("emphasized")
    def on_emphasis_change(self, origin, *args):
        active = self.context.elements.has_emphasis()
        self.enable_all_buttons_on_bar(self.geometry_button_bar, active)
        self.enable_all_buttons_on_bar(self.align_button_bar, active)
        self.enable_all_buttons_on_bar(self.modify_button_bar, active)

    # @signal_listener("ribbonbar")
    # def on_rb_toggle(self, origin, showit, *args):
    #     self._ribbon.ShowPanels(True)

    def ensure_realize(self):
        self._ribbon_dirty = True
        self.context.schedule(self._job)

    def _perform_realization(self, *args):
        self._ribbon_dirty = False
        self._ribbon.Realize()

    def __set_ribbonbar(self):
        self.ribbonbar_caption_visible = False

        self.darkmode = getattr(self.context, "theme_isdark", False)
        self._update_ribbon_artprovider()
        self.ribbon_position_aspect_ratio = True
        self.ribbon_position_ignore_update = False

        home = RB.RibbonPage(
            self._ribbon,
            ID_PAGE_MAIN,
            _("Home"),
            icons8_opened_folder_50.GetBitmap(resize=16),
        )
        self.ribbon_pages.append(home)
        # self.Bind(
        #    RB.EVT_RIBBONBAR_HELP_CLICK,
        #    lambda e: self.context("webhelp help\n"),
        # )

        self.project_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            "" if self.darkmode else _("Project"),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON
        )
        self.ribbon_panels.append((self.project_panel, _("Project")))

        button_bar = RibbonButtonBar(self.project_panel)
        self.project_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.control_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            "" if self.darkmode else _("Control"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON,
        )
        self.ribbon_panels.append((self.control_panel, _("Control")))

        button_bar = RibbonButtonBar(self.control_panel)
        self.control_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.config_panel = RB.RibbonPanel(
            home,
            wx.ID_ANY,
            "" if self.darkmode else _("Configuration"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON,
        )
        self.ribbon_panels.append((self.config_panel, _("Configuration")))

        button_bar = RibbonButtonBar(self.config_panel)
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
            "" if self.darkmode else _("Tools"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON,
        )
        self.ribbon_panels.append((self.tool_panel, _("Tools")))

        button_bar = RibbonButtonBar(self.tool_panel)
        self.tool_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.modify_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.darkmode else _("Modification"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON,
        )
        self.ribbon_panels.append((self.modify_panel, _("Modification")))

        button_bar = RibbonButtonBar(self.modify_panel)
        self.modify_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.geometry_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.darkmode else _("Geometry"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON,
        )
        self.ribbon_panels.append((self.geometry_panel, _("Geometry")))
        button_bar = RibbonButtonBar(self.geometry_panel)
        self.geometry_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.align_panel = RB.RibbonPanel(
            tool,
            wx.ID_ANY,
            "" if self.darkmode else _("Alignment"),
            icons8_opened_folder_50.GetBitmap(),
            agwStyle=RB.RIBBON_PANEL_MINIMISE_BUTTON,
        )
        self.ribbon_panels.append((self.align_panel, _("Alignment")))
        button_bar = RibbonButtonBar(self.align_panel)
        self.align_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        # self._ribbon.Bind(RB.EVT_RIBBONBAR_PAGE_CHANGING, self.on_page_change)
        # minmaxpage = RB.RibbonPage(self._ribbon, ID_PAGE_TOGGLE, "Click me")
        # self.ribbon_pages.append(minmaxpage)

        self.ensure_realize()

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    # def on_page_change(self, event):
    #     page = event.GetPage()
    #     p_id = page.GetId()
    #     # print ("Page Changing to ", p_id)
    #     if p_id  == ID_PAGE_TOGGLE:
    #         slist = debug_system_colors()
    #         msg = ""
    #         for s in slist:
    #             msg += s + "\n"
    #         wx.MessageBox(msg, "Info", wx.OK | wx.ICON_INFORMATION)
    #         event.Veto()


    def _update_ribbon_artprovider(self):
        def _set_ribbon_colour(provider, art_id_list, colour):
            mycolour = wx.Colour()
            mycolour.SetRGBA(colour)
            for id_ in art_id_list:
                try:
                    # ccol = provider.GetColour(id_)
                    # print ("Before for %d: %s, now: %s" % (id_, ccol.GetAsString(wx.C2S_CSS_SYNTAX), mycolour.GetAsString(wx.C2S_CSS_SYNTAX)))
                    provider.SetColour(id_, mycolour)
                except:
                    # Not all colorcodes are supported by all providers.
                    # So lets ignore it
                    pass

        provider = self._ribbon.GetArtProvider()
        theme_colours = getattr(self.context, "theme_colors", None)
        if theme_colours is None:
            # There were no theme-colours
            return
        try:
            TEXTCOLOUR = theme_colours["text"]
            BTNFACE_HOVER = theme_colours["button_hover"]
            INACTIVE_BG = theme_colours["inactive_bg"]
            INACTIVE_TEXT = theme_colours["text_inactive"]
            TOOLTIP_FG = theme_colours["tooltip_fg"]
            TOOLTIP_BG = theme_colours["tooltip_bg"]
            BTNFACE = theme_colours["button_face"]
            HIGHLIGHT = theme_colours["highlight"]
        except KeyError:
            # There's something wrong....
            # print ("Error, dont know that entry!")
            return
        texts = [
            RB.RIBBON_ART_BUTTON_BAR_LABEL_COLOUR,
            RB.RIBBON_ART_PANEL_LABEL_COLOUR,
            RB.RIBBON_ART_TAB_LABEL_COLOUR,
        ]
        _set_ribbon_colour(provider, texts, TEXTCOLOUR)
        disabled = [
            RB.RIBBON_ART_GALLERY_BUTTON_DISABLED_FACE_COLOUR,
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
        # In principle we would like to highlight the hovered panel
        # but there's a bug that it doesnt reset it properly...
        # _set_ribbon_colour(provider, highlights, HIGHLIGHT)
        _set_ribbon_colour(provider, highlights, BTNFACE)
        borders = [
            RB.RIBBON_ART_PANEL_BUTTON_HOVER_FACE_COLOUR,
        ]
        _set_ribbon_colour(provider, borders, HIGHLIGHT)

        lowlights = [
            RB.RIBBON_ART_TAB_HOVER_BACKGROUND_TOP_COLOUR,
            RB.RIBBON_ART_TAB_HOVER_BACKGROUND_TOP_GRADIENT_COLOUR,
        ]
        _set_ribbon_colour(provider, lowlights, INACTIVE_BG)
