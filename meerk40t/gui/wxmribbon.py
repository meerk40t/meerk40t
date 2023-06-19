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
    ribbon = RibbonBarPanel(window, wx.ID_ANY, context=context)
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


class Button:
    def __init__(self, context, parent, button_id, kind, description):
        self.context = context
        self.parent = parent
        self.id = button_id
        self.kind = kind
        self.button_dict = description

        self.label = None
        self.bitmap = None
        self.bitmap_disabled = None
        self.bitmap_small_disabled = None
        self.bitmap_large_disabled = None
        self.bitmap_small = None
        self.bitmap_large = None
        self.help_string = None
        self.client_data = None
        self.state = 0
        self.position = None
        self.toggle = False
        self.state_pressed = None
        self.state_unpressed = None
        self.group = None
        self.toggle_attr = None
        self.identifier = None
        self.action = None
        self.action_right = None
        self.enable_rule = None
        self.set_aspect(**description)

    def set_aspect(
        self,
        label=None,
        icon=None,
        help_string=None,
        group=None,
        toggle_attr=None,
        identifier=None,
        action=None,
        action_right=None,
        enable_rule=None,
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
        self.help_string = help_string
        self.group = group
        self.toggle_attr = toggle_attr
        self.identifier = identifier
        self.action = action
        self.action_right = action_right
        self.enable_rule = enable_rule
        self.object = object

        self.client_data = None
        self.state = 0
        self.position = None
        self.toggle = False
        self.state_pressed = None
        self.state_unpressed = None

    def contains(self, pos):
        if self.position is None:
            return False
        x, y = pos
        return (
            self.position[0] < x < self.position[2]
            and self.position[1] < y < self.position[3]
        )

    def click(self):
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
            self._restore_button_aspect(self, self.state_pressed)
        else:
            if self.toggle_attr is not None:
                setattr(self.object, self.toggle_attr, False)
                self.context.signal(self.toggle_attr, False, self.object)
            self._restore_button_aspect(self, self.state_unpressed)

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
            helps = alt.get("tip", self.help_string)
        self.help_string = helps
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
            "help_string": self.help_string,
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
                self._restore_button_aspect(b, key)

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

        self._store_button_aspect(b, "original")

        toggle_action = button["toggle"]
        key = toggle_action.get("identifier", "toggle")
        if "signal" in toggle_action:
            self._create_signal_for_toggle(b, toggle_action["signal"])

        self._store_button_aspect(b, key, **toggle_action)
        if "icon" in toggle_action:
            toggle_icon = toggle_action.get("icon")
            self._update_button_aspect(
                b,
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
            self._update_button_aspect(
                b,
                key,
                bitmap_small=toggle_icon.GetBitmap(resize=small_resize),
                bitmap_small_disabled=toggle_icon.GetBitmap(
                    resize=small_resize, color=Color("grey")
                ),
            )
        # Set initial value by identifer and object
        if b.toggle_attr is not None and getattr(b.object, b.toggle_attr, False):
            b.set_button_toggle(True)
            self.Refresh()

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

    def apply_enable_rules(self):
        for k in self.button_lookup:
            v = self.button_lookup[k]
            try:
                enable_it = v.enable_rule(0)
            except:
                enable_it = True
            # The button might no longer around, so catch the error...
            try:
                v.parent.EnableButton(v.id, enable_it)
            except:
                pass


    def contains(self, pos):
        if self.position is None:
            return False
        x, y = pos
        return (
            self.position[0] < x < self.position[2]
            and self.position[1] < y < self.position[3]
        )


class RibbonPage:
    def __init__(self, context, parent, id, label, icon):
        self.context = context
        self.parent = parent
        self.id = id
        self.label = label
        self.icon = icon
        self.panels = []
        self.map = {}
        self.position = None

    def modified(self):
        self.parent.modified()

    def add_panel(self, panel, ref):
        self.panels.append(panel)
        self.map[ref] = panel

    def contains(self, pos):
        if self.position is None:
            return False
        x, y = pos
        return (
            self.position[0] < x < self.position[2]
            and self.position[1] < y < self.position[3]
        )



class RibbonBarPanel(wx.Panel):
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
        self.pages = []
        self.map = {}

        # Some helper variables for showing / hiding the toolbar
        self.panels_shown = True
        self.minmax = None
        self.context = context
        self.stored_labels = {}
        self.stored_height = 0

        # Define Ribbon.
        self.__set_ribbonbar()

        self.Layout()
        # self._ribbon
        self.pipe_state = None
        self._ribbon_dirty = False
        self.screen_refresh_lock = threading.Lock()
        self.recurse = True
        self._expanded_panel = None

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_mouse_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)

        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        self.Bind(wx.EVT_RIGHT_UP, self.on_click_right)
        self.current_page = 0
        self._layout_dirty = True

    def modified(self):
        self._layout_dirty = True
        self.Refresh()

    def on_erase_background(self, event):
        pass

    def on_mouse_enter(self, event):
        pass

    def on_mouse_leave(self, event):
        pass

    def on_mouse_move(self, event):
        self._hover_button = self._button_at_position(event.Position)
        print(self._hover_button)

    def on_size(self, event):
        self.Refresh(True)

    def layout(self):
        w, h = self.Size
        x = BUFFER * 2
        y = h / 2
        for pn, page in enumerate(self.pages):
            page.position = pn * 70, 0, (pn + 1) * 70, 20
            if pn != self.current_page:
                continue
            for panel in page.panels:
                x += BUFFER * 3
                px, py = x, y
                m_height = 0
                m_width = 0
                for button in panel.buttons:
                    x += BUFFER
                    bitmap = button.bitmap_large
                    bitmap_small = button.bitmap_small

                    if button.state == "disabled":
                        bitmap = button.bitmap_large_disabled
                        bitmap_small = button.bitmap_small_disabled
                    bw, bh = bitmap.Size
                    m_height = max(bh, m_height)
                    m_width = max(bw, m_width)
                    button.position = (x, y, x + bw, y + bh)
                    x += bw
                panel.position = (
                    px - BUFFER,
                    py - BUFFER,
                    x + BUFFER,
                    y + BUFFER + m_height,
                )
        self._layout_dirty = False

    def paint(self):
        dc = wx.AutoBufferedPaintDC(self)
        if dc is None:
            return
        self.layout()
        dc.SetBrush(wx.GREEN_BRUSH)
        w, h = self.Size
        dc.DrawRectangle(0, 0, w, h)


        for n, page in enumerate(self.pages):


            dc.SetBrush(wx.WHITE_BRUSH)
            x, y, x1, y1 = page.position
            dc.DrawRectangle(x, y, x1 - x, y1 - y)

            dc.DrawText(page.label, x + BUFFER, y + BUFFER)
            if n != self.current_page:
                continue

            for panel in page.panels:
                dc.SetBrush(wx.MEDIUM_GREY_BRUSH)
                x, y, x1, y1 = panel.position
                dc.DrawRectangle(x, y, x1 - x, y1 - y)
                for button in panel.buttons:
                    bitmap = button.bitmap_large
                    bitmap_small = button.bitmap_small
                    if button.state == "disabled":
                        bitmap = button.bitmap_large_disabled
                        bitmap_small = button.bitmap_small_disabled

                    if button.toggle:
                        dc.SetBrush(wx.GREY_BRUSH)
                    else:
                        dc.SetBrush(wx.WHITE_BRUSH)
                    x, y, x1, y1 = button.position
                    dc.DrawRectangle(x, y, x1 - x, y1 - y)
                    dc.DrawBitmap(bitmap, x, y)

    def on_paint(self, event):
        """
        Handles the ``wx.EVT_PAINT`` event for :class:`RibbonButtonBar`.

        :param event: a :class:`PaintEvent` event to be processed.
        """
        if self.screen_refresh_lock.acquire(timeout=0.2):
            self.paint()
            self.screen_refresh_lock.release()

    @signal_listener("ribbon_show_labels")
    def on_show_labels(self, origin, *args):
        self.ribbon_bars.clear()
        self.ribbon_panels.clear()
        self.ribbon_pages.clear()
        self._ribbon = RB.RibbonBar(
            self,
            agwStyle=RB.RIBBON_BAR_FLOW_HORIZONTAL
            | RB.RIBBON_BAR_SHOW_PAGE_LABELS
            | RB.RIBBON_BAR_SHOW_PANEL_EXT_BUTTONS
            | RB.RIBBON_BAR_SHOW_PANEL_MINIMISE_BUTTONS,
        )
        self.__set_ribbonbar()
        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(self._ribbon, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        self.Refresh()
        self.Update()

    def _button_at_position(self, pos):
        for n, page in enumerate(self.pages):
            if n != self.current_page:
                continue
            for panel in page.panels:
                for button in panel.buttons:
                    if button.contains(pos):
                        return button
        return None

    def _page_at_position(self, pos):
        for n, page in enumerate(self.pages):
            if page.contains(pos):
                return n
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

    def on_click(self, event):
        page = self._page_at_position(event.Position)
        if page is not None:
            self.current_page = page
            self.Refresh()
            return

        pos = event.Position
        button = self._button_at_position(pos)
        if button is None:
            return
        button.click()
        self.Refresh()

    def drop_click(self, event):
        """
        Drop down of a hybrid button was clicked.

        We make a menu popup and fill it with the data about the multi-button

        @param event:
        @return:
        """
        evt_id = event.GetId()
        button = self.button_lookup.get(evt_id)
        if button is None:
            return
        if button.toggle:
            return
        menu = wx.Menu()
        for v in button.button_dict["multi"]:
            item = menu.Append(wx.ID_ANY, v.get("label"))
            menu_id = item.GetId()
            self.Bind(wx.EVT_MENU, self.drop_menu_click(button, v), id=menu_id)
        event.PopupMenu(menu)

    def drop_menu_click(self, button, v):
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
            setattr(button.object, button.save_id, key_id)
            button.state_unpressed = key_id
            self._restore_button_aspect(button, key_id)
            self.ensure_realize()

        return menu_item_click

    @lookup_listener("button/basicediting")
    def set_editing_buttons(self, new_values, old_values):
        self.map["design"].map["edit"].set_buttons(new_values)

    @lookup_listener("button/project")
    def set_project_buttons(self, new_values, old_values):
        self.map["design"].map["project"].set_buttons(new_values)

    @lookup_listener("button/control")
    def set_control_buttons(self, new_values, old_values):
        self.map["home"].map["control"].set_buttons(new_values)

    @lookup_listener("button/config")
    def set_config_buttons(self, new_values, old_values):
        self.map["config"].map["config"].set_buttons(new_values)

    @lookup_listener("button/modify")
    def set_modify_buttons(self, new_values, old_values):
        self.map["modify"].map["modify"].set_buttons(new_values)

    @lookup_listener("button/tool")
    def set_tool_buttons(self, new_values, old_values):
        self.map["design"].map["tool"].set_buttons(new_values)

    @lookup_listener("button/extended_tools")
    def set_tool_extended_buttons(self, new_values, old_values):
        self.map["design"].map["extended"].set_buttons(new_values)

    @lookup_listener("button/geometry")
    def set_geometry_buttons(self, new_values, old_values):
        self.map["modify"].map["geometry"].set_buttons(new_values)

    @lookup_listener("button/preparation")
    def set_preparation_buttons(self, new_values, old_values):
        self.map["home"].map["prep"].set_buttons(new_values)

    @lookup_listener("button/jobstart")
    def set_jobstart_buttons(self, new_values, old_values):
        self.map["home"].map["job"].set_buttons(new_values)

    @lookup_listener("button/group")
    def set_group_buttons(self, new_values, old_values):
        self.map["design"].map["group"].set_buttons(new_values)

    @lookup_listener("button/device")
    def set_device_buttons(self, new_values, old_values):
        self.map["home"].map["device"].set_buttons(new_values)

    @lookup_listener("button/align")
    def set_align_buttons(self, new_values, old_values):
        self.map["modify"].map["align"].set_buttons(new_values)

    @lookup_listener("button/properties")
    def set_property_buttons(self, new_values, old_values):
        self.map["design"].map["properties"].set_buttons(new_values)

    @signal_listener("emphasized")
    def on_emphasis_change(self, origin, *args):
        self.apply_enable_rules()

    @signal_listener("selected")
    def on_selected_change(self, origin, node=None, *args):
        self.apply_enable_rules()

    @signal_listener("icons")
    def on_requested_change(self, origin, node=None, *args):
        self.apply_enable_rules()

    # @signal_listener("ribbonbar")
    # def on_rb_toggle(self, origin, showit, *args):
    #     self._ribbon.ShowPanels(True)

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

    @property
    def is_dark(self):
        # wxPython's SysAppearance does not always deliver a reliable response from
        # wx.SystemSettings().GetAppearance().IsDark()
        # so lets tick with 'old way', although this one is fishy...
        result = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        return result

    def apply_enable_rules(self):
        for page in self.pages:
            for panel in page.panels:
                panel.apply_enable_rules()

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
        self.pages.append(page)
        self.map[ref] = page
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

        # if self.is_dark or self.context.ribbon_art:
        #     provider = self._ribbon.GetArtProvider()
        #     _update_ribbon_artprovider_for_dark_mode(
        #         provider, show_labels=self.context.ribbon_show_labels
        #     )
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
            parent=self.map["home"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Execute"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "prep",
            parent=self.map["home"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Prepare"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "control",
            parent=self.map["home"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Control"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "config",
            parent=self.map["config"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Configuration"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "device",
            parent=self.map["home"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Devices"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "project",
            parent=self.map["design"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Project"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "tool",
            parent=self.map["design"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Design"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "edit",
            parent=self.map["design"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Edit"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "group",
            parent=self.map["design"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Group"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "extended",
            parent=self.map["design"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Extended Tools"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "properties",
            parent=self.map["design"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Properties"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "modify",
            parent=self.map["modify"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Modification"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "geometry",
            parent=self.map["modify"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Geometry"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "align",
            parent=self.map["modify"],
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Alignment"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )
        self.ensure_realize()

    def pane_show(self):
        pass

    def pane_hide(self):
        for page in self.pages:
            for panel in page.panels:
                for key, listener in self._registered_signals:
                    self.context.unlisten(key, listener)

    # def on_page_changing(self, event):
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


def _update_ribbon_artprovider_for_dark_mode(provider, show_labels=False):
    def _set_ribbon_colour(provider, art_id_list, colour):
        for id_ in art_id_list:
            try:
                provider.SetColour(id_, colour)
            except:
                # Not all colorcodes are supported by all providers.
                # So let's ignore it
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
    highlights = [
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
    if not show_labels:
        font = wx.Font(
            1, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )
        provider.SetFont(RB.RIBBON_ART_BUTTON_BAR_LABEL_FONT, font)
        provider.SetFont(RB.RIBBON_ART_PANEL_LABEL_FONT, font)
        fontcolors = [
            RB.RIBBON_ART_BUTTON_BAR_LABEL_COLOUR,
            RB.RIBBON_ART_PANEL_LABEL_COLOUR,
        ]
        _set_ribbon_colour(provider, fontcolors, BTNFACE)
