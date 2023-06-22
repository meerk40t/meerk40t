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
            "attr": "ribbon_show_labels",
            "object": context,
            "default": False,
            "type": bool,
            "label": _("Show the Ribbon Labels"),
            "tip": _(
                "Active: Show the labels for ribbonbar.\n"
                "Inactive: Do not hide the ribbon labels.\n"
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
        self._aspects = {}
        self.key = "original"
        self.object = None

        self.position = None
        self.toggle = False

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
        self.dropdown = None
        self.overflow = False

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
        resize_param = kwargs.get("size")
        if resize_param is None:
            siz = icon.GetBitmap().GetSize()
            small_resize = 0.5 * siz[0]
        else:
            small_resize = 0.5 * resize_param

        self.bitmap_large = icon.GetBitmap(resize=resize_param)
        self.bitmap_large_disabled = icon.GetBitmap(
            resize=resize_param, color=Color("grey")
        )
        self.bitmap_small = icon.GetBitmap(resize=small_resize)
        self.bitmap_small_disabled = icon.GetBitmap(
            resize=small_resize, color=Color("grey")
        )
        self.bitmap = self.bitmap_large
        self.bitmap_disabled = self.bitmap_large_disabled

        self.tip = tip
        self.group = group
        self.toggle_attr = toggle_attr
        self.identifier = identifier
        self.action = action
        self.action_right = action_right
        self.rule_enabled = rule_enabled
        if object is not None:
            self.object = object
        if self.kind == "hybrid":
            self.dropdown = DropDown()
        self.modified()

    def _restore_button_aspect(self, key):
        """
        Restores a saved button aspect for the given key. Given a base_button and the key to the alternative aspect
        we restore the given aspect.

        @param key:
        @return:
        """
        try:
            alt = self._aspects[key]
        except KeyError:
            return
        self.set_aspect(**alt)
        self.key = key

    def _store_button_aspect(self, key, **kwargs):
        """
        Stores visual aspects of the buttons within the "alternatives" dictionary.

        This stores the various icons, labels, help, and other properties found on the base_button.

        @param key: aspects to store.
        @param kwargs:
        @return:
        """
        self._aspects[key] = {
            "action": self.action,
            "action_right": self.action_right,
            "label": self.label,
            "tip": self.tip,
            "icon": self.icon,
            "client_data": self.client_data,
        }
        self._update_button_aspect(key, **kwargs)

    def _update_button_aspect(self, key, **kwargs):
        """
        Directly update the button aspects via the kwargs, aspect dictionary *must* exist.

        @param self:
        @param key:
        @param kwargs:
        @return:
        """
        key_dict = self._aspects[key]
        for k in kwargs:
            if kwargs[k] is not None:
                key_dict[k] = kwargs[k]

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

    def click(self, event=None, recurse=True):
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
                if button_group and recurse:
                    first_button = button_group[0]
                    first_button.set_button_toggle(True)
                    first_button.click(recurse=False)
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
            item = menu.AppendCheckItem(wx.ID_ANY, v.get("label"))
            tip = v.get("tip")
            if tip:
                item.SetHelp(tip)
            if v.get("identifier") == self.identifier:
                item.Check(True)
            icon = v.get("icon")
            if icon:
                item.SetBitmap(icon.GetBitmap())
            top.Bind(wx.EVT_MENU, self.drop_menu_click(v), id=item.GetId())
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
            try:
                setattr(self.object, self.save_id, key_id)
            except AttributeError:
                pass
            self.state_unpressed = key_id
            self._restore_button_aspect(key_id)
            # self.ensure_realize()

        return menu_item_click

    def _setup_multi_button(self):
        """
        Store alternative aspects for multi-buttons, load stored previous state.

        @return:
        """
        multi_aspects = self.button_dict["multi"]
        # This is the key used for the multi button.
        multi_ident = self.button_dict.get("identifier")
        self.save_id = multi_ident
        try:
            self.object.setting(str, self.save_id, "default")
        except AttributeError:
            # This is not a context, we tried.
            pass
        initial_value = getattr(self.object, self.save_id, "default")

        for i, v in enumerate(multi_aspects):
            # These are values for the outer identifier
            key = v.get("identifier", i)
            self._store_button_aspect(key, **v)
            if "signal" in v:
                self._create_signal_for_multi(key, v["signal"])

            if key == initial_value:
                self._restore_button_aspect(key)

    def _create_signal_for_multi(self, key, signal):
        """
        Creates a signal to restore the state of a multi button.

        @param key:
        @param signal:
        @return:
        """

        def multi_click(origin, set_value):
            self._restore_button_aspect(key)

        self.context.listen(signal, multi_click)
        self.parent._registered_signals.append((signal, multi_click))

    def _setup_toggle_button(self):
        """
        Store toggle and original aspects for toggle-buttons

        @param self:
        @return:
        """
        resize_param = self.button_dict.get("size")

        self.state_pressed = "toggle"
        self.state_unpressed = "original"
        self._store_button_aspect(self.state_unpressed)

        toggle_button_dict = self.button_dict.get("toggle")
        key = toggle_button_dict.get("identifier", self.state_pressed)
        if "signal" in toggle_button_dict:
            self._create_signal_for_toggle(toggle_button_dict.get("signal"))
        self._store_button_aspect(key, **toggle_button_dict)

        # Set initial value by identifer and object
        if self.toggle_attr is not None and getattr(
            self.object, self.toggle_attr, False
        ):
            self.set_button_toggle(True)
            self.modified()

    def _create_signal_for_toggle(self, signal):
        """
        Creates a signal toggle which will listen for the given signal and set the toggle-state to the given set_value

        E.G. If a toggle has a signal called "tracing" and the context.signal("tracing", True) is called this will
        automatically set the toggle state.

        Note: It will not call any of the associated actions, it will simply set the toggle state.

        @param signal:
        @return:
        """

        def toggle_click(origin, set_value, *args):
            self.set_button_toggle(set_value)

        self.context.listen(signal, toggle_click)
        self.parent._registered_signals.append((signal, toggle_click))

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
            b = self._create_button(desc)

            # Store newly created button in the various lookups
            self.button_lookup[b.id] = b
            group = desc.get("group")
            if group is not None:
                c_group = self.group_lookup.get(group)
                if c_group is None:
                    c_group = []
                    self.group_lookup[group] = c_group
                c_group.append(b)

    def _create_button(self, desc):
        """
        Creates a button and places it on the button_bar depending on the required definition.

        @param desc:
        @return:
        """
        show_tip = not self.context.disable_tool_tips
        # NewIdRef is only available after 4.1
        try:
            new_id = wx.NewIdRef()
        except AttributeError:
            new_id = wx.NewId()

        # Create kind of button. Multi buttons are hybrid. Else, regular button or toggle-type
        if "multi" in desc:
            # Button is a multi-type button
            b = Button(
                self.context, self, button_id=new_id, kind="hybrid", description=desc
            )
            self.buttons.append(b)
            b._setup_multi_button()
        else:
            bkind = "normal"
            if "group" in desc or "toggle" in desc:
                bkind = "toggle"
            b = Button(
                self.context, self, button_id=new_id, kind=bkind, description=desc
            )
            self.buttons.append(b)

        if "toggle" in desc:
            b._setup_toggle_button()
        return b

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

        # Layout properties.
        self.height_factor = 1
        self.horizontal = True
        self.tab_width = 70
        self.tab_height = 20
        self.tab_tab_buffer = 10
        self.tab_initial_buffer = 30
        self.edge_page_buffer = 3 * self.height_factor
        self.page_panel_buffer = 3 * self.height_factor
        self.panel_button_buffer = 3 * self.height_factor
        self.bitmap_text_buffer = 10 * self.height_factor
        self.between_button_buffer = 3
        self.between_panel_buffer = 3
        self.dropdown_height = 20
        self.overflow_width = 20
        self.text_dropdown_buffer = 7
        self._show_labels = context.setting(bool, "ribbon_show_labels", True)

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

    def on_mouse_enter(self, event: wx.MouseEvent):
        pass

    def on_mouse_leave(self, event: wx.MouseEvent):
        self._hover_tab = None
        self._hover_button = None
        self._hover_dropdown = None
        self.modified()

    def _check_hover_dropdown(self, drop, pos):
        if drop is not None and not drop.contains(pos):
            drop = None
        if drop is not self._hover_dropdown:
            self._hover_dropdown = drop
            self.modified()

    def _check_hover_button(self, pos):
        hover = self._button_at_position(pos)
        if hover is not None:
            self._check_hover_dropdown(hover.dropdown, pos)
        if hover is self._hover_button:
            return
        self._hover_button = hover
        if hover is not None:
            self.SetToolTip(hover.tip)
        self.modified()

    def _check_hover_tab(self, pos):
        hover = self._pagetab_at_position(pos)
        if hover is not self._hover_tab:
            self._hover_tab = hover
            self.modified()

    def on_mouse_move(self, event: wx.MouseEvent):
        pos = event.Position
        self._check_hover_button(pos)
        self._check_hover_tab(pos)

    def on_size(self, event: wx.SizeEvent):
        self.modified()

    def layout(self, dc: wx.DC):
        if not self._layout_dirty:
            return
        window_width, window_height = self.Size

        real_width_of_overflow = 0
        self._overflow.clear()
        self._overflow_position = None
        for pn, page in enumerate(self.pages):
            # Set tab positioning.
            page.tab_position = (
                pn * self.tab_tab_buffer
                + pn * self.tab_width
                + self.tab_initial_buffer,
                0,
                pn * self.tab_tab_buffer
                + (pn + 1) * self.tab_width
                + self.tab_initial_buffer,
                self.tab_height * 2,
            )
            if page is not self._current_page:
                continue

            # Set page position.
            page.position = [
                self.edge_page_buffer,
                self.tab_height,
                window_width - self.edge_page_buffer,
                window_height - self.edge_page_buffer,
            ]
            # Positioning pane left..
            x = self.edge_page_buffer + self.page_panel_buffer

            panel_max_width = 0
            panel_max_height = 0
            for panel in page.panels:
                # Position for button top.
                y = self.tab_height + self.page_panel_buffer
                panel_start_x, panel_start_y = x, y

                # Position for button left.
                panel_height = 0
                panel_width = 0
                y += self.panel_button_buffer

                x += self.panel_button_buffer
                button_count = 0
                for button in panel.buttons:
                    if panel_width:
                        x += self.between_button_buffer
                    bitmap = button.bitmap_large
                    bitmap_width, bitmap_height = bitmap.Size

                    # Calculate text height/width
                    text_width = 0
                    text_height = 0
                    if button.label and self._show_labels:
                        for word in button.label.split(" "):
                            line_width, line_height = dc.GetTextExtent(word)
                            text_width = max(text_width, line_width)
                            text_height += line_height

                    # Calculate button_width/button_height
                    button_width = max(bitmap_width, text_width)
                    button_height = (
                        bitmap_height
                        # + dropdown_height
                        + self.panel_button_buffer
                    )
                    if button.label and self._show_labels:
                        button_height += self.bitmap_text_buffer + text_height

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
                    if button.position[2] > window_width - self.overflow_width:
                        real_width_of_overflow = self.overflow_width
                        button.overflow = True
                        self._overflow.append(button)
                    else:
                        button.overflow = False
                        button_count += 1

                    if button.kind == "hybrid" and button.key != "toggle":
                        # Calculate dropdown
                        button.dropdown.position = (
                            x + bitmap_width / 2,
                            y + bitmap_height / 2,
                            x + bitmap_width,
                            y + bitmap_height,
                        )
                    x += button_width
                    panel_end_x = x
                x += self.panel_button_buffer
                y += self.panel_button_buffer

                # Calculate the max value for panel_width
                panel_max_width = max(panel_max_width, panel_width)
                panel_max_height = max(panel_max_height, panel_height)

                # Calculate end_x for the panel
                panel_end_x = min(
                    x, window_width - self.edge_page_buffer - self.page_panel_buffer
                )

                if panel_start_x > panel_end_x or button_count == 0:
                    # Panel is entirely subsumed.
                    panel.position = None
                else:
                    panel.position = [
                        panel_start_x,
                        panel_start_y,
                        panel_end_x,
                        y
                        + self.panel_button_buffer,  # Value will be updated when max_y is known.
                    ]
                # Step along x value between panels.
                x += self.between_panel_buffer

            # Solve page max_x and max_y values
            max_x = 0
            max_y = 0
            for panel in page.panels:
                if panel.position:
                    panel.position[3] += panel_max_height
                    max_x = max(max_x, panel.position[2])
                    max_y = max(max_y, panel.position[3])

            # Update panels to give the correct y value, for the solved max_y
            page.position[3] = max_y + self.page_panel_buffer

            # Set position of the overflow.
            if self._overflow:
                if panel.position:
                    panel.position[2] -= self.overflow_width
                self._overflow_position = (
                    window_width - self.overflow_width,
                    self.edge_page_buffer,
                    window_width,
                    window_height - self.edge_page_buffer,
                )
        self._layout_dirty = False
        bar_size_width = int(max_x + self.edge_page_buffer)
        bar_size_height = int(max_y + self.edge_page_buffer)
        # self.pane.MinSize(bar_size_width, bar_size_height)

    def _paint_tab(self, dc: wx.DC, page: RibbonPage):
        dc.SetPen(wx.BLACK_PEN)
        if page is not self._current_page:
            dc.SetBrush(wx.Brush(self.button_face))
        else:
            dc.SetBrush(wx.Brush(self.highlight))
        if page is self._hover_tab and self._hover_button is None:
            dc.SetBrush(wx.Brush(self.button_face_hover))
        x, y, x1, y1 = page.tab_position
        dc.DrawRoundedRectangle(int(x), int(y), int(x1 - x), int(y1 - y), 5)
        dc.SetFont(self.font)
        dc.DrawText(page.label, int(x + BUFFER), int(y + BUFFER))

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

    def _paint_panel(self, dc: wx.DC, panel: RibbonPanel):
        if not panel.position:
            return
        x, y, x1, y1 = panel.position
        dc.SetBrush(wx.Brush(self.button_face))
        dc.SetPen(wx.BLACK_PEN)
        dc.DrawRoundedRectangle(int(x), int(y), int(x1 - x), int(y1 - y), 5)

    def _paint_dropdown(self, dc: wx.DC, dropdown: DropDown):
        x, y, x1, y1 = dropdown.position

        if dropdown is self._hover_dropdown:
            dc.SetBrush(wx.Brush(wx.Colour(self.highlight)))
        else:
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetPen(wx.TRANSPARENT_PEN)

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
        dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.Brush(self.inactive_background))
        dc.DrawPolygon(points)

    def _paint_button(self, dc: wx.DC, button: Button):
        if button.overflow:
            return

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
        if self._hover_button is button and self._hover_dropdown is None:
            dc.SetBrush(wx.Brush(self.button_face_hover))
            dc.SetPen(wx.BLACK_PEN)

        x, y, x1, y1 = button.position
        w = x1 - x
        h = y1 - y
        dc.DrawRoundedRectangle(int(x), int(y), int(w), int(h), 5)
        bitmap_width, bitmap_height = bitmap.Size

        dc.DrawBitmap(bitmap, x + (w - bitmap_width) / 2, y)
        y += bitmap_height

        if button.label and self._show_labels:
            y += self.bitmap_text_buffer
            dc.SetFont(self.font)
            for word in button.label.split(" "):
                text_width, text_height = dc.GetTextExtent(word)
                dc.DrawText(
                    word,
                    int(x + (w / 2.0) - (text_width / 2)),
                    int(y),
                )
                y += text_height
        if button.dropdown is not None and button.dropdown.position is not None:
            y += self.text_dropdown_buffer
            self._paint_dropdown(dc, button.dropdown)

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

    def on_paint(self, event: wx.PaintEvent):
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
        self.modified()

    def _button_at_position(self, pos):
        for page in self.pages:
            if page is not self._current_page:
                continue
            for panel in page.panels:
                for button in panel.buttons:
                    if button.contains(pos) and button.enabled:
                        return button
        return None

    def _pagetab_at_position(self, pos):
        for page in self.pages:
            if page.contains(pos):
                return page
        return None

    def on_click_right(self, event: wx.MouseEvent):
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
        Click of overflow. Overflow exists if some icons are not able to be shown.

        We make a menu popup and fill it with the overflow commands.

        @param event:
        @return:
        """

        menu = wx.Menu()
        for v in self._overflow:
            item = menu.Append(wx.ID_ANY, v.label)
            item.Enable(v.enabled)
            item.SetHelp(v.tip)
            if v.icon:
                item.SetBitmap(v.icon.GetBitmap())
            self.Bind(wx.EVT_MENU, v.click, id=item.Id)
        self.PopupMenu(menu)

    def on_click(self, event: wx.MouseEvent):
        pos = event.Position

        if self._overflow_position:
            x, y = pos
            if (
                self._overflow_position[0] < x < self._overflow_position[2]
                and self._overflow_position[1] < y < self._overflow_position[3]
            ):
                self.overflow_click()

        page = self._pagetab_at_position(pos)
        button = self._button_at_position(pos)
        if page is not None and button is None:
            self._current_page = page
            self.modified()
            return
        if button is None:
            return
        drop = button.dropdown
        if drop is not None and drop.contains(pos):
            button.drop_click()
            self.modified()
            return
        button.click()
        self.modified()

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
