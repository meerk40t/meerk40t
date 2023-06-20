"""
The WxmRibbon Bar is a core aspect of MeerK40t's interaction. All the buttons are dynmically generated but the
panels themselves are created in a static fashion. But the contents of those individual ribbon panels are defined
in the kernel lookup.

        service.register(
            "button/control/Redlight",
            {
                "label": _("Red Dot On"),
                "icon": icons8_quick_mode_on_50,
                "tip": _("Turn Redlight On"),
                "action": lambda v: service("red on\n"),
                "toggle": {
                    "label": _("Red Dot Off"),
                    "action": lambda v: service("red off\n"),
                    "icon": icons8_flash_off_50,
                    "signal": "grbl_red_dot",
                },
                "rule_enabled": lambda v: has_red_dot_enabled(),
            },
        )

For example would register a button in the control panel with a discrete name "Redlight" the definitions for label,
icon, tip, action are all pretty standard to set up a button. This can often be registered as part of a service such
that if you switch the service it will change the lookup and that change will be detected here and rebuilt the buttons.

The toggle defines an alternative set of values for the toggle state of the button.
The multi defines a series of alternative states, and creates a hybrid button with a drop-down to select the state
    desired.
Other properties like `rule_enabled` provides a check for whether this button should be enabled or not.

The `toggle_attr` will permit a toggle to set an attribute on the given `object` which would default to the root
context but could need to set a more local object attribute.

If a `signal` is assigned as an aspect of multi it triggers that specfic option in the multi button.
If a `signal` is assigned within the toggle it sets the state of the given toggle. These should be compatible with
the signals issued by choice panels.

The action is a function which is run when the button is pressed.
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
    ribbon = RibbonBarPanel(window, wx.ID_ANY, context=context, pane=pane)
    pane.control = ribbon

    window.on_pane_create(pane)
    context.register("pane/ribbon", pane)

    choices = [
        {
            "attr": "ribbon_art",
            "object": context,
            "default": True,
            "type": bool,
            "label": _("Show Modified Ribbon-Art"),
            "tip": _(
                "Shows the ribbon in gray rather than blue (previously for OSX-DarkMode)"
                "Requires Restart!\n"
            ),
            "page": "Gui",
            "section": "Appearance",
        },
        {
            "attr": "ribbon_show_labels",
            "object": context,
            "default": False,
            "type": bool,
            "label": _("Show the Ribbon Labels"),
            "tip": _(
                "Active: Show the labels for ribbonbar.\n"
                "Inactive: Do not hide the ribbon labels.\n"
                "Requires Restart!\n"
            ),
            "page": "Gui",
            "section": "Appearance",
        },
    ]
    context.kernel.register_choices("preferences", choices)


class DropDown:
    def __init__(self):
        self.position = None

    def contains(self, pos):
        if self.position is None:
            return False
        x, y = pos
        return (
            self.position[0] < x < self.position[2]
            and self.position[1] < y < self.position[3]
        )


class Button:
    def __init__(self, context, parent, button_id, kind, description):
        self.context = context
        self.parent = parent
        self.id = button_id
        self.kind = kind
        self.button_dict = description
        self.enabled = True

        self.label = None
        self.bitmap = None
        self.bitmap_disabled = None
        self.bitmap_small_disabled = None
        self.bitmap_large_disabled = None
        self.bitmap_small = None
        self.bitmap_large = None
        self.tip = None
        self.client_data = None
        self.state = 0
        self.position = None
        self.dropdown = None
        self.overflow = False

        self.toggle = False
        self.state_pressed = None
        self.state_unpressed = None
        self.group = None
        self.toggle_attr = None
        self.identifier = None
        self.action = None
        self.action_right = None
        self.rule_enabled = None
        self.set_aspect(**description)
        self.apply_enable_rules()

    def set_aspect(
        self,
        label=None,
        icon=None,
        tip=None,
        group=None,
        toggle_attr=None,
        identifier=None,
        action=None,
        action_right=None,
        rule_enabled=None,
        object=None,
        **kwargs,
    ):
        self.label = label
        self.icon = icon
        self.bitmap = icon.GetBitmap()
        self.bitmap_disabled = icon.GetBitmap()
        self.bitmap_small_disabled = self.bitmap_disabled
        self.bitmap_large_disabled = self.bitmap_disabled
        self.bitmap_small = self.bitmap
        self.bitmap_large = self.bitmap
        self.tip = tip
        self.group = group
        self.toggle_attr = toggle_attr
        self.identifier = identifier
        self.action = action
        self.action_right = action_right
        self.rule_enabled = rule_enabled
        self.object = object

        self.client_data = None
        self.state = 0
        self.position = None
        self.toggle = False
        self.state_pressed = None
        self.state_unpressed = None
        if self.kind == "hybrid":
            self.dropdown = DropDown()

    def apply_enable_rules(self):
        try:
            v = self.rule_enabled(0)
            if v != self.enabled:
                self.enabled = v
                self.modified()
        except (AttributeError, TypeError):
            pass

    def contains(self, pos):
        if self.position is None:
            return False
        x, y = pos
        return (
            self.position[0] < x < self.position[2]
            and self.position[1] < y < self.position[3]
        )

    def click(self, event=None):
        """
        Process button click of button at provided button_id

        @return:
        """
        if self.group:
            # Toggle radio buttons
            self.toggle = not self.toggle
            if self.toggle:  # got toggled
                button_group = self.parent.group_lookup.get(self.group, [])

                for obutton in button_group:
                    # Untoggle all other buttons in this group.
                    if obutton.group == self.group and obutton.id != self.id:
                        obutton.set_button_toggle(False)
            else:  # got untoggled...
                # so let's activate the first button of the group (implicitly defined as default...)
                button_group = self.parent.group_lookup.get(self.group)
                if button_group:
                    first_button = button_group[0]
                    first_button.set_button_toggle(True)
                    first_button.click()
                    return
        if self.action is not None:
            # We have an action to call.
            self.action(None)

        if self.state_pressed is None:
            # If there's a pressed state we should change the button state
            return

        self.toggle = not self.toggle
        if self.toggle:
            if self.toggle_attr is not None:
                setattr(self.object, self.toggle_attr, True)
                self.context.signal(self.toggle_attr, True, self.object)
            self._restore_button_aspect(self.state_pressed)
        else:
            if self.toggle_attr is not None:
                setattr(self.object, self.toggle_attr, False)
                self.context.signal(self.toggle_attr, False, self.object)
            self._restore_button_aspect(self.state_unpressed)

    def drop_click(self):
        """
        Drop down of a hybrid button was clicked.

        We make a menu popup and fill it with the data about the multi-button

        @param event:
        @return:
        """
        if self.toggle:
            return
        top = self.parent.parent.parent
        menu = wx.Menu()
        for v in self.button_dict["multi"]:
            item = menu.Append(wx.ID_ANY, v.get("label"))
            icon = v.get("icon")
            if icon:
                item.SetBitmap(icon.GetBitmap())
            top.Bind(wx.EVT_MENU, self.drop_menu_click(v), id=self.id)
        top.PopupMenu(menu)

    def drop_menu_click(self, v):
        """
        Creates menu_item_click processors for the various menus created for a drop-click

        @param button:
        @param v:
        @return:
        """

        def menu_item_click(event):
            """
            Process menu item click.

            @param event:
            @return:
            """
            key_id = v.get("identifier")
            setattr(self.object, self.save_id, key_id)
            self.state_unpressed = key_id
            self._restore_button_aspect(key_id)
            # self.ensure_realize()

        return menu_item_click

    def _restore_button_aspect(self, key):
        """
        Restores a saved button aspect for the given key. Given a base_button and the key to the alternative aspect
        we restore the given aspect.

        @param key:
        @return:
        """
        if not hasattr(self, "alternatives"):
            return
        try:
            alt = self.alternatives[key]
        except KeyError:
            return
        self.action = alt.get("action", self.action)
        self.action_right = alt.get("action_right", self.action_right)
        self.label = alt.get("label", self.label)

        helps = alt.get("help_string", "")
        if helps == "":
            helps = alt.get("tip", self.tip)
        self.tip = helps
        self.bitmap_large = alt.get("bitmap_large", self.bitmap_large)
        self.bitmap_large_disabled = alt.get(
            "bitmap_large_disabled", self.bitmap_large_disabled
        )
        self.bitmap_small = alt.get("bitmap_small", self.bitmap_small)
        self.bitmap_small_disabled = alt.get(
            "bitmap_small_disabled", self.bitmap_small_disabled
        )
        self.client_data = alt.get("client_data", self.client_data)
        # base_button.id = alt.get("id", base_button.id)
        # base_button.kind = alt.get("kind", base_button.kind)
        # base_button.state = alt.get("state", base_button.state)
        self.key = key

    def _store_button_aspect(self, key, **kwargs):
        """
        Stores visual aspects of the buttons within the "alternatives" dictionary.

        This stores the various icons, labels, help, and other properties found on the base_button.

        @param key: aspects to store.
        @param kwargs:
        @return:
        """
        if not hasattr(self, "alternatives"):
            self.alternatives = {}
        self.alternatives[key] = {
            "action": self.action,
            "action_right": self.action_right,
            "label": self.label,
            "help_string": self.tip,
            "bitmap_large": self.bitmap_large,
            "bitmap_large_disabled": self.bitmap_large_disabled,
            "bitmap_small": self.bitmap_small,
            "bitmap_small_disabled": self.bitmap_small_disabled,
            "client_data": self.client_data,
            # "id": base_button.id,
            # "kind": base_button.kind,
            # "state": base_button.state,
        }
        key_dict = self.alternatives[key]
        for k in kwargs:
            if kwargs[k] is not None:
                key_dict[k] = kwargs[k]

    def _update_button_aspect(self, key, **kwargs):
        """
        Directly update the button aspects via the kwargs, aspect dictionary *must* exist.

        @param self:
        @param key:
        @param kwargs:
        @return:
        """
        if not hasattr(self, "alternatives"):
            self.alternatives = {}
        key_dict = self.alternatives[key]
        for k in kwargs:
            if kwargs[k] is not None:
                key_dict[k] = kwargs[k]

    def set_button_toggle(self, toggle_state):
        self.toggle = toggle_state
        if toggle_state:
            self._restore_button_aspect(self.state_pressed)
        else:
            self._restore_button_aspect(self.state_unpressed)

    def modified(self):
        self.parent.modified()


class RibbonPanel:
    def __init__(self, context, parent, id, label, icon):
        self.context = context
        self.parent = parent
        self.id = id
        self.label = label
        self.icon = icon

        self._registered_signals = list()
        self.button_lookup = {}
        self.group_lookup = {}

        self.buttons = []
        self.position = None

    def clear_buttons(self):
        self.buttons.clear()
        self.parent.modified()

    def add_button(
        self,
        button_id,
        kind="normal",
        description=None,
    ):
        button = Button(self.context, self, button_id, kind, description=description)
        self.buttons.append(button)
        return button

    def add_hybrid_button(self, **kwargs):
        return self.add_button(**kwargs, kind="hybrid")

    def set_buttons(self, new_values):
        """
        Set buttons is the primary button configuration routine. It is responsible for clearing and recreating buttons.

        * The button definition is a dynamically created and stored dictionary.
        * Buttons are sorted by priority.
        * Multi buttons get a hybrid type.
        * Toggle buttons get a toggle type (Unless they are also multi).
        * Created button objects have attributes assigned to them.
            * toggle, parent, group, identifier, toggle_identifier, action, right, rule_enabled
        * Multi-buttons have an identifier attr which is applied to the root context, or given "object".
        * The identifier is used to set the state of the object, the attr-identifier is set to the value-identifier
        * Toggle buttons have a toggle_identifier, this is used to set the and retrieve the state of the toggle.


        @param new_values: dictionary of button values to use.
        @return:
        """
        self._current_layout = 0
        self._hovered_button = None
        self._active_button = None
        self.clear_buttons()
        button_descriptions = []
        for desc, name, sname in new_values:
            button_descriptions.append(desc)

        # Sort buttons by priority
        def sort_priority(elem):
            return elem.get("priority", 0)

        button_descriptions.sort(key=sort_priority)

        for desc in button_descriptions:
            # Every registered button in the updated lookup gets created.
            group = desc.get("group")
            resize_param = desc.get("size")
            b = self._create_button(desc)

            if "multi" in desc:
                self._setup_multi_button(desc, b)
            if "toggle" in desc:
                self._setup_toggle_button(desc, b)

            # Store newly created button in the various lookups
            new_id = b.id
            self.button_lookup[new_id] = b
            if group is not None:
                c_group = self.group_lookup.get(group)
                if c_group is None:
                    c_group = []
                    self.group_lookup[group] = c_group
                c_group.append(b)

    def _create_button(self, button):
        """
        Creates a button and places it on the button_bar depending on the required definition.

        @param self:
        @param button:
        @return:
        """
        resize_param = button.get("size")
        show_tip = not self.context.disable_tool_tips
        # NewIdRef is only available after 4.1
        try:
            new_id = wx.NewIdRef()
        except AttributeError:
            new_id = wx.NewId()

        # Create kind of button. Multi buttons are hybrid. Else, regular button or toggle-type
        if "multi" in button:
            # Button is a multi-type button
            b = self.add_hybrid_button(
                button_id=new_id,
                description=button,
            )
        else:
            if "group" in button or "toggle" in button:
                bkind = "toggle"
            else:
                bkind = "normal"
            helps = ""
            if show_tip:
                if helps == "" and "help_string" in button:
                    helps = button["help_string"]
                if helps == "" and "tip" in button:
                    helps = button["tip"]
            b = self.add_button(
                button_id=new_id,
                kind=bkind,
                description=button,
            )

        return b

    def _setup_multi_button(self, button, b):
        """
        Store alternative aspects for multi-buttons, load stored previous state.

        @param button:
        @param b:
        @return:
        """
        resize_param = button.get("size")
        multi_aspects = button["multi"]
        # This is the key used for the multi button.
        multi_ident = button.get("identifier")
        b.save_id = multi_ident
        try:
            b.object.setting(str, b.save_id, "default")
        except AttributeError:
            # This is not a context, we tried.
            pass
        initial_value = getattr(b.object, b.save_id, "default")

        for i, v in enumerate(multi_aspects):
            # These are values for the outer identifier
            key = v.get("identifier", i)
            b._store_button_aspect(key)
            b._update_button_aspect(key, **v)
            if "icon" in v:
                v_icon = v.get("icon")
                b._update_button_aspect(
                    key,
                    bitmap_large=v_icon.GetBitmap(resize=resize_param),
                    bitmap_large_disabled=v_icon.GetBitmap(
                        resize=resize_param, color=Color("grey")
                    ),
                )
                if resize_param is None:
                    siz = v_icon.GetBitmap().GetSize()
                    small_resize = 0.5 * siz[0]
                else:
                    small_resize = 0.5 * resize_param
                b._update_button_aspect(
                    key,
                    bitmap_small=v_icon.GetBitmap(resize=small_resize),
                    bitmap_small_disabled=v_icon.GetBitmap(
                        resize=small_resize, color=Color("grey")
                    ),
                )
            if "signal" in v:
                self._create_signal_for_multi(b, key, v["signal"])

            if key == initial_value:
                b._restore_button_aspect(key)

    def _create_signal_for_multi(self, button, key, signal):
        """
        Creates a signal to restore the state of a multi button.

        @param button:
        @param key:
        @param signal:
        @return:
        """

        def make_multi_click(_tb, _key):
            def multi_click(origin, set_value):
                self._restore_button_aspect(_tb, _key)

            return multi_click

        signal_multi_listener = make_multi_click(button, key)
        self.context.listen(signal, signal_multi_listener)
        self._registered_signals.append((signal, signal_multi_listener))

    def _setup_toggle_button(self, button, b):
        """
        Store toggle and original aspects for toggle-buttons

        @param button:
        @param b:
        @return:
        """
        resize_param = button.get("size")

        b.state_pressed = "toggle"
        b.state_unpressed = "original"

        b._store_button_aspect("original")

        toggle_action = button["toggle"]
        key = toggle_action.get("identifier", "toggle")
        if "signal" in toggle_action:
            self._create_signal_for_toggle(b, toggle_action["signal"])

        b._store_button_aspect(key, **toggle_action)
        if "icon" in toggle_action:
            toggle_icon = toggle_action.get("icon")
            b._update_button_aspect(
                key,
                bitmap_large=toggle_icon.GetBitmap(resize=resize_param),
                bitmap_large_disabled=toggle_icon.GetBitmap(
                    resize=resize_param, color=Color("grey")
                ),
            )
            if resize_param is None:
                siz = toggle_icon.GetBitmap().GetSize()
                small_resize = 0.5 * siz[0]
            else:
                small_resize = 0.5 * resize_param
            b._update_button_aspect(
                key,
                bitmap_small=toggle_icon.GetBitmap(resize=small_resize),
                bitmap_small_disabled=toggle_icon.GetBitmap(
                    resize=small_resize, color=Color("grey")
                ),
            )
        # Set initial value by identifer and object
        if b.toggle_attr is not None and getattr(b.object, b.toggle_attr, False):
            b.set_button_toggle(True)
            self.modified()

    def _create_signal_for_toggle(self, button, signal):
        """
        Creates a signal toggle which will listen for the given signal and set the toggle-state to the given set_value

        E.G. If a toggle has a signal called "tracing" and the context.signal("tracing", True) is called this will
        automatically set the toggle state.

        Note: It will not call any of the associated actions, it will simply set the toggle state.

        @param button:
        @param signal:
        @return:
        """

        def make_toggle_click(_tb):
            def toggle_click(origin, set_value, *args):
                _tb.set_button_toggle(set_value)

            return toggle_click

        signal_toggle_listener = make_toggle_click(button)
        self.context.listen(signal, signal_toggle_listener)
        self._registered_signals.append((signal, signal_toggle_listener))

    def contains(self, pos):
        if self.position is None:
            return False
        x, y = pos
        return (
            self.position[0] < x < self.position[2]
            and self.position[1] < y < self.position[3]
        )

    def modified(self):
        self.parent.modified()


class RibbonPage:
    def __init__(self, context, parent, id, label, icon):
        self.context = context
        self.parent = parent
        self.id = id
        self.label = label
        self.icon = icon
        self.panels = []
        self.position = None
        self.tab_position = None

    def add_panel(self, panel, ref):
        self.panels.append(panel)
        setattr(self, ref, panel)

    def contains(self, pos):
        if self.tab_position is None:
            return False
        x, y = pos
        return (
            self.tab_position[0] < x < self.tab_position[2]
            and self.tab_position[1] < y < self.tab_position[3]
        )

    def modified(self):
        self.parent.modified()


class RibbonBarPanel(wx.Control):
    def __init__(self, *args, context=None, pane=None, **kwds):
        super().__init__(*args, **kwds)
        # kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        # wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self._job = Job(
            process=self._perform_realization,
            job_name="realize_ribbon_bar",
            interval=0.1,
            times=1,
            run_main=True,
        )
        self.pane = pane
        self._current_page = None
        self.pages = []

        # Some helper variables for showing / hiding the toolbar
        self.panels_shown = True
        self.minmax = None
        self.context = context
        self.stored_labels = {}
        self.stored_height = 0

        self.text_color = wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNTEXT)

        self.button_face_hover = copy.copy(
            wx.SystemSettings().GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        ).ChangeLightness(50)
        self.inactive_background = copy.copy(
            wx.SystemSettings().GetColour(wx.SYS_COLOUR_INACTIVECAPTION)
        )
        self.inactive_text = copy.copy(
            wx.SystemSettings().GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        self.tooltip_foreground = copy.copy(
            wx.SystemSettings().GetColour(wx.SYS_COLOUR_INFOTEXT)
        )
        self.tooltip_background = copy.copy(
            wx.SystemSettings().GetColour(wx.SYS_COLOUR_INFOBK)
        )
        self.button_face = copy.copy(
            wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNFACE)
        )
        self.highlight = copy.copy(
            wx.SystemSettings().GetColour(wx.SYS_COLOUR_HOTLIGHT)
        )
        self.dark_mode = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        self.font = wx.Font(
            10, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )

        # Define Ribbon.
        self.__set_ribbonbar()

        self._layout_dirty = True
        self.Layout()

        self.pipe_state = None
        self._ribbon_dirty = False
        self.screen_refresh_lock = threading.Lock()
        self.recurse = True
        self._expanded_panel = None
        self._hover_button = None
        self._hover_tab = None
        self._hover_dropdown = None
        self._overflow = list()
        self._overflow_position = None

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_mouse_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)

        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        self.Bind(wx.EVT_RIGHT_UP, self.on_click_right)

    def modified(self):
        self._layout_dirty = True
        self.Refresh()

    def on_erase_background(self, event):
        pass

    def on_mouse_enter(self, event):
        pass

    def on_mouse_leave(self, event):
        self._hover_tab = None
        self._hover_button = None
        self._hover_dropdown = None
        self.Refresh()

    def _check_hover_dropdown(self, drop, pos):
        if drop is not None and not drop.contains(pos):
            drop = None
        if drop is not self._hover_dropdown:
            self._hover_dropdown = drop
            self.Refresh()

    def _check_hover_button(self, pos):
        hover = self._button_at_position(pos)
        if hover is not None:
            self._check_hover_dropdown(hover.dropdown, pos)
        if hover is self._hover_button:
            return
        self._hover_button = hover
        if hover is not None:
            self.SetToolTip(hover.tip)
        self.Refresh()

    def _check_hover_tab(self, pos):
        hover = self._page_at_position(pos)
        if hover is not self._hover_tab:
            self._hover_tab = hover
            self.Refresh()

    def on_mouse_move(self, event):
        pos = event.Position
        self._check_hover_button(pos)
        self._check_hover_tab(pos)

    def on_size(self, event):
        self.Refresh(True)

    def layout(self, dc: wx.DC):
        horizontal = True
        tab_width = 70
        tab_height = 20
        edge_page_buffer = 7
        page_panel_buffer = 7
        panel_button_buffer = 7
        bitmap_text_buffer = 7
        between_button_buffer = 9
        overflow_width = 20
        window_width, window_height = self.Size

        real_width_of_overflow = 0
        self._overflow.clear()
        self._overflow_position = None
        for pn, page in enumerate(self.pages):
            # Set tab positioning.
            page.tab_position = (
                (pn + 0.5) * tab_width,
                0,
                (pn + 1.5) * tab_width,
                tab_height * 2,
            )
            if page is not self._current_page:
                continue

            # Set page position.
            page.position = [
                edge_page_buffer,
                tab_height,
                window_width - edge_page_buffer,
                window_height - edge_page_buffer,
            ]
            # Positioning pane left..
            x = edge_page_buffer + page_panel_buffer

            panel_max_width = 0
            panel_max_height = 0
            for panel in page.panels:
                # Position for button top.
                y = tab_height + edge_page_buffer
                panel_start_x, panel_start_y = x, y

                # Position for button left.
                x += panel_button_buffer

                panel_height = 0
                panel_width = 0
                y += panel_button_buffer
                for button in panel.buttons:
                    if panel_width:
                        x += between_button_buffer
                    bitmap = button.bitmap_large
                    bitmap_width, bitmap_height = bitmap.Size

                    # Calculate text height/width
                    text_width = 0
                    text_height = 0
                    for word in button.label.split(" "):
                        line_width, line_height = dc.GetTextExtent(word)
                        text_width = max(text_width, line_width)
                        text_height += line_height

                    # Calculate dropdown height
                    dropdown_height = 0
                    if button.kind == "hybrid":
                        dropdown_height = 20

                    # Calculate button_width/button_height
                    button_width = max(bitmap_width, text_width)
                    button_height = (
                        bitmap_height + bitmap_text_buffer + text_height + dropdown_height + panel_button_buffer
                    )

                    # Calculate the max value for pane size based on button position
                    panel_width = max(button_width, panel_width)
                    panel_height = max(button_height, panel_height)

                    # layout button_position
                    button.position = (
                        x,
                        y,
                        x + button_width,
                        y + button_height,
                    )

                    # Determine whether button is within overflow.
                    if button.position[2] > window_width - overflow_width:
                        real_width_of_overflow = overflow_width
                        button.overflow = True
                        self._overflow.append(button)
                    else:
                        button.overflow = False

                    if button.kind == "hybrid":
                        # Calculate dropdown
                        button.dropdown.position = (
                            x - button_buffer,
                            y + button_height - dropdown_height,
                            x + button_width + button_buffer,
                            y + button_height,
                        )
                    x += button_width

                # Calculate the max value for panel_width
                panel_max_width = max(panel_max_width, panel_width)
                panel_max_height = max(panel_max_height, panel_height)

                # Calculate end_x for the panel
                panel_end_x = min(x + panel_button_buffer, window_width - page_panel_buffer - panel_button_buffer) - real_width_of_overflow


                if panel_start_x > panel_end_x:
                    # Panel is entirely subsumed.
                    panel.position = None
                else:
                    panel.position = [
                        panel_start_x,
                        panel_start_y,
                        panel_end_x,
                        y + panel_button_buffer,  # Value will be updated when max_y is known.
                    ]
                # Step along x value between panels.
                x += between_button_buffer

            # Solve page max_x and max_y values
            max_x = 0
            max_y = 0
            for panel in page.panels:
                if panel.position:
                    panel.position[3] += panel_max_height
                    max_x = max(max_x, panel.position[2])
                    max_y = max(max_y, panel.position[3])

            # Update panels to give the correct y value, for the solved max_y
            page.position[3] = max_y + edge_page_buffer

            # Set position of the overflow.
            if self._overflow:
                if panel.position:
                    panel.position[2] -= overflow_width
                self._overflow_position = window_width - overflow_width, 0, window_width, max_y
        self._layout_dirty = False
        self.SetMinSize((int(max_x+ edge_page_buffer), int(max_y + edge_page_buffer)))

    def _paint_tab(self, dc: wx.DC, page):
        dc.SetPen(wx.BLACK_PEN)
        if page is not self._current_page:
            dc.SetBrush(wx.Brush(self.button_face))
        else:
            dc.SetBrush(wx.Brush(self.highlight))
        if page is self._hover_tab:
            dc.SetBrush(wx.Brush(self.button_face_hover))
        x, y, x1, y1 = page.tab_position
        dc.DrawRoundedRectangle(int(x), int(y), int(x1 - x), int(y1 - y), 5)
        dc.SetFont(self.font)
        dc.DrawText(page.label, x + BUFFER, y + BUFFER)

    def _paint_background(self, dc: wx.DC):
        w, h = self.Size
        dc.SetBrush(wx.Brush(self.button_face))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(0, 0, w, h)

    def _paint_overflow(self, dc: wx.DC):
        if not self._overflow_position:
            return
        x, y, x1, y1 = self._overflow_position
        dc.SetBrush(wx.Brush(self.highlight))
        dc.SetPen(wx.BLACK_PEN)
        dc.DrawRoundedRectangle(int(x), int(y), int(x1 - x), int(y1 - y), 5)

    def _paint_panel(self, dc: wx.DC, panel):
        if not panel.position:
            return
        x, y, x1, y1 = panel.position
        dc.SetBrush(wx.Brush(self.button_face))
        dc.SetPen(wx.BLACK_PEN)
        dc.DrawRoundedRectangle(int(x), int(y), int(x1 - x), int(y1 - y), 5)

    def _paint_dropdown(self, dc: wx.DC, dropdown):
        x, y, x1, y1 = dropdown.position

        if dropdown is self._hover_dropdown:
            dc.SetBrush(wx.Brush(wx.Colour(self.highlight)))
        else:
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetPen(wx.BLACK_PEN)

        dc.DrawRoundedRectangle(int(x), int(y), int(x1 - x), int(y1 - y), 5)
        r = (y1 - y) / 2
        cx = (x + x1) / 2
        cy = -r / 2 + (y + y1) / 2

        points = [
            (
                int(cx + r * math.cos(math.radians(x))),
                int(cy + r * math.sin(math.radians(x))),
            )
            for x in (0, 90, 180)
        ]
        dc.SetBrush(wx.Brush(self.inactive_background))
        dc.DrawPolygon(points)

    def _paint_button(self, dc: wx.DC, button):
        if button.overflow:
            return
        buffer = 7
        button_buffer = 3

        bitmap = button.bitmap_large
        bitmap_small = button.bitmap_small
        if not button.enabled:
            bitmap = button.bitmap_large_disabled
            bitmap_small = button.bitmap_small_disabled

        dc.SetBrush(wx.Brush(self.button_face))
        dc.SetPen(wx.TRANSPARENT_PEN)
        if not button.enabled:
            dc.SetBrush(wx.Brush(self.inactive_background))
            dc.SetPen(wx.TRANSPARENT_PEN)
        if button.toggle:
            dc.SetBrush(wx.Brush(self.highlight))
            dc.SetPen(wx.BLACK_PEN)
        if self._hover_button is button:
            dc.SetBrush(wx.Brush(self.button_face_hover))
            dc.SetPen(wx.BLACK_PEN)

        x, y, x1, y1 = button.position
        w = x1 - x
        h = y1 - y
        dc.DrawRoundedRectangle(int(x), int(y), int(w), int(h), 5)
        bitmap_width, bitmap_height = bitmap.Size
        y += buffer
        dc.DrawBitmap(bitmap, x + (w - bitmap_width) / 2, y)
        y += bitmap_height
        if button.dropdown is not None:
            self._paint_dropdown(dc, button.dropdown)
        if button.label:
            y += buffer
            dc.SetFont(self.font)
            for n, word in enumerate(button.label.split(" ")):
                text_width, text_height = dc.GetTextExtent(word)
                dc.DrawText(
                    word,
                    x + (w / 2.0) - (text_width / 2),
                    y,
                )
                y += text_height

    def paint(self):
        dc = wx.AutoBufferedPaintDC(self)
        if dc is None:
            return
        self.layout(dc)
        self._paint_background(dc)
        for page in self.pages:
            self._paint_tab(dc, page)

        for page in self.pages:
            if page is not self._current_page:
                continue
            dc.SetBrush(wx.Brush(self.button_face))
            x, y, x1, y1 = page.position
            dc.DrawRoundedRectangle(int(x), int(y), int(x1 - x), int(y1 - y), 5)
            for panel in page.panels:
                self._paint_panel(dc, panel)
                for button in panel.buttons:
                    self._paint_button(dc, button)
        self._paint_overflow(dc)

    def on_paint(self, event):
        """
        Handles the ``wx.EVT_PAINT`` event for :class:`RibbonButtonBar`.

        :param event: a :class:`PaintEvent` event to be processed.
        """
        if self.screen_refresh_lock.acquire(timeout=0.2):
            self.paint()
            self.screen_refresh_lock.release()

    @signal_listener("ribbon_show_labels")
    def on_show_labels(self, origin, v, *args):
        self._show_labels = v
        self.Refresh()

    def _button_at_position(self, pos):
        for page in self.pages:
            if page is not self._current_page:
                continue
            for panel in page.panels:
                for button in panel.buttons:
                    if button.contains(pos) and button.enabled:
                        return button
        return None

    def _page_at_position(self, pos):
        for page in self.pages:
            if page.contains(pos):
                return page
        return None

    def on_click_right(self, event):
        """
        Handles the ``wx.EVT_RIGHT_DOWN`` event
        :param event: a :class:`MouseEvent` event to be processed.
        """
        pos = event.Position
        button = self._button_at_position(pos)
        if button is None:
            return
        if button is not None:
            action = button.action_right
            if action:
                action(event)

    def overflow_click(self):
        """
        Drop down of a hybrid button was clicked.

        We make a menu popup and fill it with the data about the multi-button

        @param event:
        @return:
        """

        menu = wx.Menu()
        for v in self._overflow:
            item = menu.Append(wx.ID_ANY, v.label)
            icon = v.icon
            if icon:
                item.SetBitmap(icon.GetBitmap())
            self.Bind(wx.EVT_MENU, v.click, id=item.Id)
        self.PopupMenu(menu)

    def on_click(self, event):
        pos = event.Position

        if self._overflow_position:
            x, y = pos
            if (
                self._overflow_position[0] < x < self._overflow_position[2]
                and self._overflow_position[1] < y < self._overflow_position[3]
            ):
                self.overflow_click()

        page = self._page_at_position(pos)
        if page is not None:
            self._current_page = page
            self.Refresh()
            return

        button = self._button_at_position(pos)
        if button is None:
            return
        drop = button.dropdown
        if drop is not None and drop.contains(pos):
            button.drop_click()
            self.Refresh()
            return
        button.click()
        self.Refresh()

    @lookup_listener("button/basicediting")
    def set_editing_buttons(self, new_values, old_values):
        self.design.edit.set_buttons(new_values)

    @lookup_listener("button/project")
    def set_project_buttons(self, new_values, old_values):
        self.design.project.set_buttons(new_values)

    @lookup_listener("button/control")
    def set_control_buttons(self, new_values, old_values):
        self.home.control.set_buttons(new_values)

    @lookup_listener("button/config")
    def set_config_buttons(self, new_values, old_values):
        self.config.config.set_buttons(new_values)

    @lookup_listener("button/modify")
    def set_modify_buttons(self, new_values, old_values):
        self.modify.modify.set_buttons(new_values)

    @lookup_listener("button/tool")
    def set_tool_buttons(self, new_values, old_values):
        self.design.tool.set_buttons(new_values)

    @lookup_listener("button/extended_tools")
    def set_tool_extended_buttons(self, new_values, old_values):
        self.design.extended.set_buttons(new_values)

    @lookup_listener("button/geometry")
    def set_geometry_buttons(self, new_values, old_values):
        self.modify.geometry.set_buttons(new_values)

    @lookup_listener("button/preparation")
    def set_preparation_buttons(self, new_values, old_values):
        self.home.prep.set_buttons(new_values)

    @lookup_listener("button/jobstart")
    def set_jobstart_buttons(self, new_values, old_values):
        self.home.job.set_buttons(new_values)

    @lookup_listener("button/group")
    def set_group_buttons(self, new_values, old_values):
        self.design.group.set_buttons(new_values)

    @lookup_listener("button/device")
    def set_device_buttons(self, new_values, old_values):
        self.home.device.set_buttons(new_values)

    @lookup_listener("button/align")
    def set_align_buttons(self, new_values, old_values):
        self.modify.align.set_buttons(new_values)

    @lookup_listener("button/properties")
    def set_property_buttons(self, new_values, old_values):
        self.design.properties.set_buttons(new_values)

    @signal_listener("emphasized")
    def on_emphasis_change(self, origin, *args):
        self.apply_enable_rules()

    @signal_listener("selected")
    def on_selected_change(self, origin, node=None, *args):
        self.apply_enable_rules()

    @signal_listener("icons")
    def on_requested_change(self, origin, node=None, *args):
        self.apply_enable_rules()

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

    def _all_buttons(self):
        for page in self.pages:
            if page is not self._current_page:
                continue
            for panel in page.panels:
                for button in panel.buttons:
                    yield button

    def apply_enable_rules(self):
        for button in self._all_buttons():
            button.apply_enable_rules()

    def ensure_realize(self):
        self._ribbon_dirty = True
        self.context.schedule(self._job)
        self.apply_enable_rules()

    def _perform_realization(self, *args):
        self._ribbon_dirty = False
        # self._ribbon.Realize()

    def add_page(self, ref, id, label, icon):
        page = RibbonPage(
            self.context,
            self,
            id,
            label,
            icon,
        )
        setattr(self, ref, page)
        if self._current_page is None:
            self._current_page = page
        self.pages.append(page)
        return page

    def add_panel(self, ref, parent, id, label, icon):
        panel = RibbonPanel(
            self.context,
            parent=parent,
            id=id,
            label=label,
            icon=icon,
        )
        parent.add_panel(panel, ref)
        return panel

    def __set_ribbonbar(self):
        self.ribbonbar_caption_visible = False

        self.ribbon_position_aspect_ratio = True
        self.ribbon_position_ignore_update = False

        self.add_page(
            "design",
            ID_PAGE_DESIGN,
            _("Design"),
            icons8_opened_folder_50.GetBitmap(resize=16),
        )

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
            _("Settings"),
            icons8_opened_folder_50.GetBitmap(resize=16),
        )

        self.add_panel(
            "job",
            parent=self.home,
            id=wx.ID_ANY,
            label=_("Execute"),
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
            "config",
            parent=self.config,
            id=wx.ID_ANY,
            label=_("Configuration"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "device",
            parent=self.home,
            id=wx.ID_ANY,
            label=_("Devices"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "project",
            parent=self.design,
            id=wx.ID_ANY,
            label=_("Project"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "tool",
            parent=self.design,
            id=wx.ID_ANY,
            label=_("Design"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "edit",
            parent=self.design,
            id=wx.ID_ANY,
            label=_("Edit"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "group",
            parent=self.design,
            id=wx.ID_ANY,
            label=_("Group"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "extended",
            parent=self.design,
            id=wx.ID_ANY,
            label=_("Extended Tools"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "properties",
            parent=self.design,
            id=wx.ID_ANY,
            label=_("Properties"),
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
        self.ensure_realize()

    def pane_show(self):
        pass

    def pane_hide(self):
        for page in self.pages:
            for panel in page.panels:
                for key, listener in panel._registered_signals:
                    self.context.unlisten(key, listener)

    def on_page_changed(self, event):
        page = event.GetPage()
        p_id = page.GetId()
        if p_id != ID_PAGE_DESIGN:
            self.context("tool none\n")
        pagename = ""
        for p in self.ribbon_pages:
            if p[0] is page:
                pagename = p[1]
                break
        setattr(self.context.root, "_active_page", pagename)
        event.Skip()

    @signal_listener("page")
    def on_page_signal(self, origin, pagename=None, *args):
        if pagename is None:
            return
        pagename = pagename.lower()
        if pagename == "":
            pagename = "home"
        for p in self.ribbon_pages:
            if p[1] == pagename:
                self._ribbon.SetActivePage(p[0])
                if getattr(self.context.root, "_active_page", "") != pagename:
                    setattr(self.context.root, "_active_page", pagename)
