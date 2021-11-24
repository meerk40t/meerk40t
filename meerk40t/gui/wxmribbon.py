import copy

import wx
import wx.ribbon as RB
from wx import aui

from ..kernel import lookup_listener
from .icons import icons8_connected_50, icons8_opened_folder_50
from .mwindow import MWindow

_ = wx.GetTranslation


def register_panel(window, context):
    ribbon = RibbonPanel(window, wx.ID_ANY, context=context)

    pane = (
        aui.AuiPaneInfo()
        .Name("ribbon")
        .Top()
        .RightDockable(False)
        .LeftDockable(False)
        .MinSize(300, 120)
        .FloatingSize(640, 120)
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
        self.ribbon_position_units = self.context.units_index

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
            if "alt-action" in button:
                button_bar.AddHybridButton(
                    new_id,
                    button["label"],
                    button["icon"].GetBitmap(),
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
                button_bar.AddButton(
                    new_id,
                    button["label"],
                    button["icon"].GetBitmap(),
                    button["tip"],
                )
            button_bar.Bind(RB.EVT_RIBBONBUTTONBAR_CLICKED, button["action"], id=new_id)
        self._ribbon.Realize()

    @lookup_listener("button/project")
    def set_project_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.project_button_bar)

    @lookup_listener("button/control")
    def set_control_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.control_button_bar)

    @lookup_listener("button/config")
    def set_config_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.config_button_bar)

    @property
    def is_dark(self):
        return wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127

    def __set_ribbonbar(self):
        self.ribbonbar_caption_visible = False

        if self.is_dark:
            provider = self._ribbon.GetArtProvider()
            _update_ribbon_artprovider_for_dark_mode(provider)
        self.ribbon_position_aspect_ratio = True
        self.ribbon_position_ignore_update = False
        self.ribbon_position_x = 0.0
        self.ribbon_position_y = 0.0
        self.ribbon_position_h = 0.0
        self.ribbon_position_w = 0.0
        self.ribbon_position_units = 0
        self.ribbon_position_name = None

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

        self._ribbon.Realize()

    def pane_show(self):
        pass

    def pane_hide(self):
        pass


class Ribbon(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(423, 131, *args, **kwds)

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
