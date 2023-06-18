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
    def __init__(self, button_id, label, bitmap, bitmap_disabled, help_string, kind):
        self.id = button_id
        self.label = label
        self.bitmap = bitmap
        self.bitmap_disabled = bitmap_disabled
        self.bitmap_small_disabled = bitmap_disabled
        self.bitmap_large_disabled = bitmap_disabled
        self.bitmap_small = bitmap
        self.bitmap_large = bitmap
        self.help_string = help_string
        self.kind = kind
        self.client_data = None
        self.state = 0
        self.position = None
        self.toggle = False

    def contains(self, pos):
        if self.position is None:
            return False
        x, y = pos
        return (
            self.position[0] < x < self.position[2]
            and self.position[1] < y < self.position[3]
        )


class RibbonPanel:
    def __init__(self, parent, id, label, icon):
        self.parent = parent
        self.id = id
        self.label = label
        self.icon = icon
        self.buttons = []
        self.position = None

    def clear_buttons(self):
        self.buttons.clear()
        self.parent.modified()


class RibbonPage:
    def __init__(self, parent, id, label, icon):
        self.parent = parent
        self.id = id
        self.label = label
        self.icon = icon
        self.panels = []
        self.map = {}

    def modified(self):
        self.parent.modified()

    def add_panel(self, panel, ref):
        self.panels.append(panel)
        self.map[ref] = panel


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

        self.button_lookup = {}
        self.group_lookup = {}

        self._registered_signals = list()

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

        self.Bind(wx.EVT_LEFT_DOWN, self.button_click)
        self.Bind(wx.EVT_RIGHT_UP, self.button_click_right)
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

    def AddButton(
        self,
        panel,
        button_id,
        label,
        bitmap=None,
        bitmap_disabled=None,
        help_string=None,
        kind="normal",
    ):
        button = Button(button_id, label, bitmap, bitmap_disabled, help_string, kind)
        self.buttons.append(button)
        panel.buttons.append(button)
        return button

    def AddHybridButton(
        self,
        panel,
        button_id,
        label,
        bitmap=None,
        bitmap_disabled=None,
        help_string=None,
    ):
        button = Button(
            button_id, label, bitmap, bitmap_disabled, help_string, "hybrid"
        )
        self.buttons.append(button)
        panel.buttons.append(button)
        return button

    def set_button_toggle(self, button, toggle_state):
        button.toggle = toggle_state
        if toggle_state:
            self._restore_button_aspect(b, b.state_pressed)
        else:
            self._restore_button_aspect(b, b.state_unpressed)


    def layout(self):
        w, h = self.Size
        x = 0
        y = 0
        for pn, page in enumerate(self.pages):
            if pn != self.current_page:
                continue
            for panel in page.panels:
                x += 0
                px, py = x, y
                for button in panel.buttons:
                    bitmap = button.bitmap_large
                    bitmap_small = button.bitmap_small

                    if button.state == "disabled":
                        bitmap = button.bitmap_large_disabled
                        bitmap_small = button.bitmap_small_disabled
                    bw, bh = bitmap.Size
                    button.position = (x, y, x + bw, y + bh)
                    x += bw
                    # if x > w:
                    #     y += bh
                    #     x = 0
                panel.position = (px, py, x, y)
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
            if n != self.current_page:
                continue
            for panel in page.panels:
                dc.SetBrush(wx.GREY_BRUSH)
                for button in panel.buttons:
                    bitmap = button.bitmap_large
                    bitmap_small = button.bitmap_small

                    if button.state == "disabled":
                        bitmap = button.bitmap_large_disabled
                        bitmap_small = button.bitmap_small_disabled

                    # dc.DrawRectangle(button.position)
                    dc.DrawBitmap(bitmap, button.position[0], button.position[1])

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


    def button_click_right(self, event):
        """
        Handles the ``wx.EVT_RIGHT_DOWN`` event
        :param event: a :class:`MouseEvent` event to be processed.
        """
        pos = event.Position
        button = self._button_at_position(pos)
        if button is not None:
            action = button.action_right
            if action:
                action(event)

    def button_click(self, event):
        pos = event.Position
        button = self._button_at_position(pos)
        self._button_click(button)

    def _button_click(self, button, event=None):
        """
        Process button click of button at provided button_id

        @param evt_id:
        @param event:
        @return:
        """
        # button = self.button_lookup.get(evt_id)
        # if button is None:
        #     return

        if button.group:
            # Toggle radio buttons
            button.toggle = not button.toggle
            if button.toggle:  # got toggled
                button_group = self.group_lookup.get(button.group, [])

                for obutton in button_group:
                    # Untoggle all other buttons in this group.
                    if obutton.group == button.group and obutton.id != button.id:
                        self.set_button_toggle(obutton, False)
            else:  # got untoggled...
                # so let's activate the first button of the group (implicitly defined as default...)
                button_group = self.group_lookup.get(button.group)
                if button_group:
                    first_button = button_group[0]
                    self.set_button_toggle(first_button, True)

                    # Clone event and recurse.
                    if event and first_button.id != evt_id:
                        _event = event.Clone()
                        _event.SetId(first_button.id)
                        if first_button.id == evt_id:
                            # Can't recurse.
                            return
                        self.button_click(_event)
                        self._button_click_id(first_button.id, _event)
                        return
        if button.action is not None:
            # We have an action to call.
            button.action(event)

        if button.state_pressed is None:
            # If there's a pressed state we should change the button state
            return

        button.toggle = not button.toggle
        if button.toggle:
            if button.toggle_attr is not None:
                setattr(button.object, button.toggle_attr, True)
                self.context.signal(button.toggle_attr, True, button.object)
            self._restore_button_aspect(button, button.state_pressed)
        else:
            if button.toggle_attr is not None:
                setattr(button.object, button.toggle_attr, False)
                self.context.signal(button.toggle_attr, False, button.object)
            self._restore_button_aspect(button, button.state_unpressed)
        self.ensure_realize()

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

    def _restore_button_aspect(self, base_button, key):
        """
        Restores a saved button aspect for the given key. Given a base_button and the key to the alternative aspect
        we restore the given aspect.

        @param base_button:
        @param key:
        @return:
        """
        if not hasattr(base_button, "alternatives"):
            return
        try:
            alt = base_button.alternatives[key]
        except KeyError:
            return
        base_button.action = alt.get("action", base_button.action)
        base_button.action_right = alt.get("action_right", base_button.action_right)
        base_button.label = alt.get("label", base_button.label)

        helps = alt.get("help_string", "")
        if helps == "":
            helps = alt.get("tip", base_button.help_string)
        base_button.help_string = helps
        base_button.bitmap_large = alt.get("bitmap_large", base_button.bitmap_large)
        base_button.bitmap_large_disabled = alt.get(
            "bitmap_large_disabled", base_button.bitmap_large_disabled
        )
        base_button.bitmap_small = alt.get("bitmap_small", base_button.bitmap_small)
        base_button.bitmap_small_disabled = alt.get(
            "bitmap_small_disabled", base_button.bitmap_small_disabled
        )
        base_button.client_data = alt.get("client_data", base_button.client_data)
        # base_button.id = alt.get("id", base_button.id)
        # base_button.kind = alt.get("kind", base_button.kind)
        # base_button.state = alt.get("state", base_button.state)
        base_button.key = key

    def _store_button_aspect(self, base_button, key, **kwargs):
        """
        Stores visual aspects of the buttons within the "alternatives" dictionary.

        This stores the various icons, labels, help, and other properties found on the base_button.

        @param base_button: button with these askpects
        @param key: aspects to store.
        @param kwargs:
        @return:
        """
        if not hasattr(base_button, "alternatives"):
            base_button.alternatives = {}
        base_button.alternatives[key] = {
            "action": base_button.action,
            "action_right": base_button.action_right,
            "label": base_button.label,
            "help_string": base_button.help_string,
            "bitmap_large": base_button.bitmap_large,
            "bitmap_large_disabled": base_button.bitmap_large_disabled,
            "bitmap_small": base_button.bitmap_small,
            "bitmap_small_disabled": base_button.bitmap_small_disabled,
            "client_data": base_button.client_data,
            # "id": base_button.id,
            # "kind": base_button.kind,
            # "state": base_button.state,
        }
        key_dict = base_button.alternatives[key]
        for k in kwargs:
            if kwargs[k] is not None:
                key_dict[k] = kwargs[k]

    def _update_button_aspect(self, base_button, key, **kwargs):
        """
        Directly update the button aspects via the kwargs, aspect dictionary *must* exist.

        @param base_button:
        @param key:
        @param kwargs:
        @return:
        """
        if not hasattr(base_button, "alternatives"):
            base_button.alternatives = {}
        key_dict = base_button.alternatives[key]
        for k in kwargs:
            if kwargs[k] is not None:
                key_dict[k] = kwargs[k]

    def _create_button(self, button_bar, button):
        """
        Creates a button and places it on the button_bar depending on the required definition.

        @param button_bar:
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
            b = self.AddHybridButton(
                panel=button_bar,
                button_id=new_id,
                label=button["label"],
                bitmap=button["icon"].GetBitmap(resize=resize_param),
                help_string=button["tip"] if show_tip else "",
            )
            # button_bar.Bind(
            #     RB.EVT_RIBBONBUTTONBAR_DROPDOWN_CLICKED,
            #     self.drop_click,
            #     id=new_id,
            # )
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
            b = self.AddButton(
                panel=button_bar,
                button_id=new_id,
                label=button["label"],
                bitmap=button["icon"].GetBitmap(resize=resize_param),
                bitmap_disabled=button["icon"].GetBitmap(
                    resize=resize_param, color=Color("grey")
                ),
                help_string=helps,
                kind=bkind,
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
            self._store_button_aspect(b, key)
            self._update_button_aspect(b, key, **v)
            if "icon" in v:
                v_icon = v.get("icon")
                self._update_button_aspect(
                    b,
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
                self._update_button_aspect(
                    b,
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
            self.set_button_toggle(b, True)
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
                self.set_button_toggle(_tb, set_value)

            return toggle_click

        signal_toggle_listener = make_toggle_click(button)
        self.context.listen(signal, signal_toggle_listener)
        self._registered_signals.append((signal, signal_toggle_listener))

    def set_buttons(self, new_values, button_panel):
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
        @param button_panel: specific button bar these buttons are applied to.
        @return:
        """
        button_panel._current_layout = 0
        button_panel._hovered_button = None
        button_panel._active_button = None
        button_panel.clear_buttons()
        buttons = []
        for button, name, sname in new_values:
            buttons.append(button)

        # Sort buttons by priority
        def sort_priority(elem):
            return elem.get("priority", 0)

        buttons.sort(key=sort_priority)

        for button in buttons:
            # Every registered button in the updated lookup gets created.
            group = button.get("group")
            resize_param = button.get("size")
            b = self._create_button(button_panel, button)

            # Store all relevant aspects for newly registered button.
            b.button_dict = button
            b.state_pressed = None
            b.state_unpressed = None
            b.toggle = False
            b.parent = button_panel
            b.group = group
            b.toggle_attr = button.get("toggle_attr")
            b.identifier = button.get("identifier")
            b.action = button.get("action")
            b.action_right = button.get("right")
            b.enable_rule = button.get("rule_enabled", lambda cond: True)
            b.object = button.get("object", self.context)
            if "multi" in button:
                self._setup_multi_button(button, b)
            if "toggle" in button:
                self._setup_toggle_button(button, b)

            # Store newly created button in the various lookups
            new_id = b.id
            self.button_lookup[new_id] = b
            if group is not None:
                c_group = self.group_lookup.get(group)
                if c_group is None:
                    c_group = []
                    self.group_lookup[group] = c_group
                c_group.append(b)

        self.ensure_realize()

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

    @lookup_listener("button/basicediting")
    def set_editing_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["design"].map["edit"])

    @lookup_listener("button/project")
    def set_project_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["design"].map["project"])

    @lookup_listener("button/control")
    def set_control_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["home"].map["control"])

    @lookup_listener("button/config")
    def set_config_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["config"].map["config"])

    @lookup_listener("button/modify")
    def set_modify_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["modify"].map["modify"])

    @lookup_listener("button/tool")
    def set_tool_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["design"].map["tool"])

    @lookup_listener("button/extended_tools")
    def set_tool_extended_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["design"].map["extended"])

    @lookup_listener("button/geometry")
    def set_geometry_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["modify"].map["geometry"])

    @lookup_listener("button/preparation")
    def set_preparation_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["home"].map["prep"])

    @lookup_listener("button/jobstart")
    def set_jobstart_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["home"].map["job"])

    @lookup_listener("button/group")
    def set_group_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["design"].map["group"])

    @lookup_listener("button/device")
    def set_device_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["home"].map["device"])
        # self.set_buttons(new_values, self.device_copy_panel)

    @lookup_listener("button/align")
    def set_align_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["modify"].map["align"])

    @lookup_listener("button/properties")
    def set_property_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.map["design"].map["properties"])

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

        button_group = self.group_lookup.get(group, [])
        for button in button_group:
            self.set_button_toggle(button, button.identifier == identifier)
        self.apply_enable_rules()

    @property
    def is_dark(self):
        # wxPython's SysAppearance does not always deliver a reliable response from
        # wx.SystemSettings().GetAppearance().IsDark()
        # so lets tick with 'old way', although this one is fishy...
        result = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        return result

    def ensure_realize(self):
        self._ribbon_dirty = True
        self.context.schedule(self._job)
        self.apply_enable_rules()

    def _perform_realization(self, *args):
        self._ribbon_dirty = False
        # self._ribbon.Realize()

    def add_page(self, ref, id, label, icon):
        page = RibbonPage(
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

        # self.add_panel("device_copy",
        #     parent=self.map["config"],
        #     id=wx.ID_ANY,
        #     label="" if self.is_dark else _("Device"),
        #     icon=icons8_opened_folder_50.GetBitmap(),
        # )

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
