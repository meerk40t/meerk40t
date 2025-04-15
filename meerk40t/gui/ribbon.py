"""
The RibbonBar is a scratch control widget. All the buttons are dynamically generated. The contents of those individual
ribbon panels are defined by implementing classes.

The primary method of defining a panel is by calling the `set_buttons()` on the panel.

control_panel.set_buttons(
    {
        "label": _("Red Dot On"),
        "icon": icons8_flash_on,
        "tip": _("Turn Redlight On"),
        "action": lambda v: service("red on\n"),
        "toggle": {
            "label": _("Red Dot Off"),
            "action": lambda v: service("red off\n"),
            "icon": icons8_flash_off,
            "signal": "grbl_red_dot",
        },
        "rule_enabled": lambda v: has_red_dot_enabled(),
    }
)

Would, for example, register a button in the control panel the definitions for label, icon, tip, action are all
standard with regard to buttons.

The toggle defines an alternative set of values for the toggle state of the button.

The multi defines a series of alternative states, and creates a hybrid button with a drop-down to select the state
    desired.

Other properties like `rule_enabled` provides a check for whether this button should be enabled or not.

The `toggle_attr` will permit a toggle to set an attribute on the given `object` which would default to the root
context but could need to set a more local object attribute.

If a `signal` is assigned as an aspect of multi it triggers that option multi-button option.
If a `signal` is assigned within the toggle it sets the state of the given toggle. These should be compatible with
the signals issued by choice panels.

The action is a function which is run when the button is pressed.
"""

import copy
import platform
import threading

import wx

from meerk40t.gui.icons import STD_ICON_SIZE
from meerk40t.kernel import Job
from meerk40t.svgelements import Color

_ = wx.GetTranslation

COLOR_MODE_DEFAULT = 0
COLOR_MODE_COLOR = 1
COLOR_MODE_DARK = 2


class DropDown:
    """
    Dropdowns are the triangle click addons that expand the button list to having other functions.

    This primarily stores the position of the given dropdown.
    """

    def __init__(self):
        self.position = None

    def contains(self, pos):
        """
        Is this drop down hit by this position.

        @param pos:
        @return:
        """
        if self.position is None:
            return False
        x, y = pos
        return (
            self.position[0] < x < self.position[2]
            and self.position[1] < y < self.position[3]
        )


class Button:
    """
    Buttons store most of the relevant data as to how to display the current aspect of the given button. This
    includes things like tool-tip, the drop-down if needed, whether its in the overflow, the pressed and unpressed
    aspects of the buttons and enable/disable rules.
    """

    def __init__(self, context, parent, button_id, kind, description):
        self.context = context
        self.parent = parent
        self.id = button_id
        self.kind = kind
        self.button_dict = description
        self.enabled = True
        self.visible = True
        self._aspects = {}
        self.key = "original"
        self.object = None

        self.position = None
        self.toggle = False

        self.label = None
        self.icon = None

        self.bitmap = None
        self.bitmap_disabled = None

        self.min_size = 15
        self.max_size = 150

        self.available_bitmaps = {}
        self.available_bitmaps_disabled = {}

        self.tip = None
        self.help = None
        self.client_data = None
        self.state = 0
        self.dropdown = None
        self.overflow = False

        self.state_pressed = None
        self.state_unpressed = None
        self.group = None
        self.toggle_attr = None
        self.multi_autoexec = None
        self.identifier = None
        self.action = None
        self.action_right = None
        self.rule_enabled = None
        self.rule_visible = None
        self.min_width = 0
        self.min_height = 0
        self.default_width = int(self.max_size / 2)
        self.icon_size = self.default_width

        self.set_aspect(**description)
        self.apply_enable_rules()

    def set_aspect(
        self,
        label=None,
        icon=None,
        tip=None,
        help=None,
        group=None,
        toggle_attr=None,
        identifier=None,
        action=None,
        action_right=None,
        rule_enabled=None,
        rule_visible=None,
        object=None,
        multi_autoexec=None,
        **kwargs,
    ):
        """
        This sets all the different aspects that buttons generally have.

        @param label: button label
        @param icon: icon used for this button
        @param tip: tool tip for the button
        @param help: help information for aspect
        @param group: Group the button exists in for radio-toggles
        @param toggle_attr: The attribute that should be changed on toggle.
        @param identifier: Identifier in the group or toggle
        @param action: Action taken when button is pressed.
        @param action_right: Action taken when button is clicked with right mouse button.
        @param rule_enabled: Rule by which the button is enabled or disabled
        @param rule_visible: Rule by which the button will be hidden or shown
        @param object: object which the toggle_attr is an attr applied to
        @param kwargs:
        @return:
        """
        self.label = label
        resize_param = kwargs.get("size")
        if resize_param is None:
            self.default_width = int(self.max_size / 2)
        else:
            self.default_width = resize_param

        # We need to cast the icon explicitly to PyEmbeddedImage
        # as otherwise a strange type error is thrown:
        # TypeError: GetBitmap() got an unexpected keyword argument 'force_darkmode'
        # Well...
        from meerk40t.gui.icons import PyEmbeddedImage, VectorIcon

        if not isinstance(icon, VectorIcon):
            icon = PyEmbeddedImage(icon.data)
        self.icon = icon

        self.available_bitmaps.clear()
        self.available_bitmaps_disabled.clear()
        self.get_bitmaps(self.default_width)

        self.tip = tip
        self.help = help
        self.group = group
        self.toggle_attr = toggle_attr
        self.identifier = identifier
        self.action = action
        self.action_right = action_right
        self.rule_enabled = rule_enabled
        self.rule_visible = rule_visible
        self.multi_autoexec = multi_autoexec 
        if object is not None:
            self.object = object
        else:
            self.object = self.context
        if self.kind == "hybrid":
            self.dropdown = DropDown()
        self.modified()

    def get_bitmaps(self, point_size):
        top = self.parent.parent.parent
        darkm = bool(top.art.color_mode == COLOR_MODE_DARK)
        if point_size < self.min_size:
            point_size = self.min_size
        if point_size > self.max_size:
            point_size = self.max_size
        self.icon_size = int(point_size)
        edge = int(point_size / 25.0) + 1
        key = str(self.icon_size)
        if key not in self.available_bitmaps:
            self.available_bitmaps[key] = self.icon.GetBitmap(
                resize=self.icon_size,
                noadjustment=True,
                force_darkmode=darkm,
                buffer=edge,
            )
            self.available_bitmaps_disabled[key] = self.icon.GetBitmap(
                resize=self.icon_size,
                color=Color("grey"),
                noadjustment=True,
                buffer=edge,
            )
        self.bitmap = self.available_bitmaps[key]
        self.bitmap_disabled = self.available_bitmaps_disabled[key]

    def _restore_button_aspect(self, key):
        """
        Restores a saved button aspect for the given key. Given a key to the alternative aspect we restore the given
        aspect.

        @param key: aspect key to set.
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
        Stores visual aspects of the buttons within the "_aspects" dictionary.

        This stores the various icons, labels, help, and other properties found on the button.

        @param key: aspects to store.
        @param kwargs: Additional aspects to implement that are not necessarily currently set on the button.
        @return:
        """
        self._aspects[key] = {
            "action": self.action,
            "action_right": self.action_right,
            "label": self.label,
            "tip": self.tip,
            "help": self.help,
            "icon": self.icon,
            "client_data": self.client_data,
            "rule_enabled": self.rule_enabled,
            "rule_visible": self.rule_visible,
            "toggle_attr": self.toggle_attr,
            "object": self.object,
            "multi_autoexec": self.multi_autoexec,
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
        """
        Calls rule_enabled() and returns whether the given rule enables the button.

        @return:
        """
        if self.rule_enabled is not None:
            try:
                v = self.rule_enabled(0)
                if v != self.enabled:
                    self.enabled = v
                    self.modified()
            except (AttributeError, TypeError):
                pass
        if self.rule_visible is not None:
            v = self.rule_visible(0)
            if v != self.visible:
                self.visible = v
                if not self.visible:
                    self.position = None
                self.modified()
        else:
            if not self.visible:
                self.visible = True
                self.modified()

    def contains(self, pos):
        """
        Is this button hit by this position.

        @param pos:
        @return:
        """
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
            if self.state_pressed is None:
                # Regular button
                self.toggle = True
            else:
                # Real toggle button
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
            # Unless button has a pressed state we have finished.
            return

        # There is a pressed state which requires that we have a toggle.
        self.toggle = not self.toggle
        if self.toggle:
            # Call the toggle_attr restore the pressed state.
            if self.toggle_attr is not None:
                setattr(self.object, self.toggle_attr, True)
                self.context.signal(self.toggle_attr, True, self.object)
            self._restore_button_aspect(self.state_pressed)
        else:
            # Call the toggle_attr restore the unpressed state.
            if self.toggle_attr is not None:
                setattr(self.object, self.toggle_attr, False)
                self.context.signal(self.toggle_attr, False, self.object)
            self._restore_button_aspect(self.state_unpressed)

    def drop_click(self):
        """
        Drop down of a hybrid button was clicked.

        We make a menu popup and fill it with the data about the multi-button
        @return:
        """
        if self.toggle:
            return
        top = self.parent.parent.parent
        menu = wx.Menu()
        item = menu.Append(wx.ID_ANY, "...")
        item.Enable(False)
        for v in self.button_dict["multi"]:
            item = menu.Append(wx.ID_ANY, v.get("label"))
            tip = v.get("tip")
            if tip:
                item.SetHelp(tip)
            if v.get("identifier") == self.identifier:
                item.SetItemLabel(v.get("label") + "(*)")
            icon = v.get("icon")
            if icon:
                # There seems to be a bug to display icons in a submenu consistently
                # print (f"Had a bitmap for {v.get('label')}")
                item.SetBitmap(icon.GetBitmap(resize=STD_ICON_SIZE / 2, buffer=2))
            top.Bind(wx.EVT_MENU, self.drop_menu_click(v), id=item.GetId())
        top.PopupMenu(menu)

    def drop_menu_click(self, v):
        """
        Creates menu_item_click processors for the various menus created for a drop-click

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
            # And now execute it, provided it would be enabled...
            auto_execute = False if self.multi_autoexec is None else self.multi_autoexec
            auto_execute = auto_execute and self.context.setting(bool, "button_multi_menu_execute", True)
            if auto_execute:
                is_visible = True
                is_enabled = True
                if self.rule_visible:
                    try:
                        is_visible = self.rule_visible(0)
                    except (AttributeError, TypeError):
                        is_visible = False
                if self.rule_enabled:
                    try:
                        is_enabled = self.rule_enabled(0)
                    except (AttributeError, TypeError):
                        is_enabled = False
                if is_visible and is_enabled:
                    try:
                        self.action(None)
                    except AttributeError:
                        pass

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
        if "signal" in self.button_dict and "attr" in self.button_dict:
            self._create_generic_signal_for_multi(self.object, self.button_dict.get("attr"), self.button_dict.get("signal"))

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

        def multi_click(origin, *args):
            self._restore_button_aspect(key)

        self.context.listen(signal, multi_click)
        self.parent._registered_signals.append((signal, multi_click))

    def _create_generic_signal_for_multi(self, q_object, q_attr, signal):
        """
        Creates a signal to restore the state of a multi button.

        @param key:
        @param signal:
        @return:
        """

        def multi_click(origin, *args):
            try:
                key = getattr(q_object, q_attr)
            except AttributeError:
                return
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

        def toggle_click(origin, *args):
            # Whats the value to set?
            set_value = args[0] if args else not self.toggle
            # But if we have a toggle_attr then this has precedence
            set_value = getattr(self.object, self.toggle_attr) if self.toggle_attr else set_value
            self.set_button_toggle(set_value)

        self.context.listen(signal, toggle_click)
        self.parent._registered_signals.append((signal, toggle_click))

    def set_button_toggle(self, toggle_state):
        """
        Set the button's toggle state to the given toggle_state

        @param toggle_state:
        @return:
        """
        self.toggle = toggle_state
        if toggle_state:
            self._restore_button_aspect(self.state_pressed)
        else:
            self._restore_button_aspect(self.state_unpressed)

    def modified(self):
        """
        This button was modified and should be redrawn.
        @return:
        """
        self.parent.modified()


class RibbonPanel:
    """
    Ribbon Panel is a panel of buttons within the page.
    """

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
        self.available_position = None
        self._overflow = list()
        self._overflow_position = None

    def visible_buttons(self):
        for button in self.buttons:
            if button.visible:
                yield button

    @property
    def visible_button_count(self):
        pcount = 0
        for button in self.buttons:
            if button is not None and button.visible:
                pcount += 1
        return pcount

    def clear_buttons(self):
        self.buttons.clear()
        self.parent.modified()
        self._overflow = list()
        self._overflow_position = None

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
        * Toggle buttons have a toggle_identifier, this is used to set and retrieve the state of the toggle.


        @param new_values: dictionary of button values to use.
        @return:
        """
        # print (f"Setbuttons called for {self.label}")
        self.modified()
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
        """
        Does the given position hit the current panel.

        @param pos:
        @return:
        """
        if self.position is None:
            return False
        x, y = pos
        return (
            self.position[0] < x < self.position[2]
            and self.position[1] < y < self.position[3]
        )

    def modified(self):
        """
        Modified call parent page.
        @return:
        """
        self.parent.modified()

    def overflow_click(self):
        """
        Click of overflow. Overflow exists if some icons are not able to be shown.

        We make a menu popup and fill it with the overflow commands.

        @return:
        """
        # print (f"Overflow click called for {self.label}")
        menu = wx.Menu()
        top = self.parent.parent  # .parent
        for v in self._overflow:
            item = menu.Append(wx.ID_ANY, v.label)
            item.Enable(v.enabled)
            if callable(v.tip):
                item.SetHelp(v.tip())
            else:
                item.SetHelp(v.tip)
            if v.icon:
                item.SetBitmap(v.icon.GetBitmap(resize=STD_ICON_SIZE / 2, buffer=2))
            top.Bind(wx.EVT_MENU, v.click, id=item.Id)
        top.PopupMenu(menu)


class RibbonPage:
    """
    Ribbon Page is a page of buttons this is the series of ribbon panels as triggered by the different tags.
    """

    def __init__(self, context, parent, id, label, icon, reference):
        self.context = context
        self.parent = parent
        self.id = id
        self.label = label
        self.icon = icon
        self.panels = []
        self.position = None
        self.tab_position = None
        self.visible = True
        self.reference = reference

    def add_panel(self, panel, ref):
        """
        Adds a panel to this page.
        @param panel:
        @param ref:
        @return:
        """
        self.panels.append(panel)
        if ref is not None:
            # print(f"Setattr in add_panel: {ref} = {panel}")
            setattr(self, ref, panel)

    def contains(self, pos):
        """
        Does this position hit the tab position of this page.
        @param pos:
        @return:
        """
        if self.tab_position is None:
            return False
        x, y = pos
        return (
            self.tab_position[0] < x < self.tab_position[2]
            and self.tab_position[1] < y < self.tab_position[3]
        )

    def modified(self):
        """
        Call modified to parent RibbonBarPanel.

        @return:
        """
        self.parent.modified()


class RibbonBarPanel(wx.Control):
    def __init__(self, parent, id, context=None, pane=None, **kwds):
        super().__init__(parent, id, **kwds)
        self.context = context
        self.pages = []
        self.pane = pane
        jobname = f"realize_ribbon_bar_{self.GetId()}"
        #  print (f"Requesting job with name: '{jobname}'")
        self._redraw_job = Job(
            process=self._paint_main_on_buffer,
            job_name=jobname,
            interval=0.1,
            times=1,
            run_main=True,
        )
        # Layout properties.
        self.art = Art(self)

        # Define Ribbon.
        self._redraw_lock = threading.Lock()
        self._paint_dirty = True
        self._layout_dirty = True
        self._ribbon_buffer = None

        # self._overflow = list()
        # self._overflow_position = None

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_mouse_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)

        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        self.Bind(wx.EVT_RIGHT_UP, self.on_click_right)

        # Tooltip logic - as we do have a single control,
        # this will prevent wxPython from resetting the timer
        # when hovering to a different button
        self._tooltip = ""
        jobname = f"tooltip_ribbon_bar_{self.GetId()}"
        #  print (f"Requesting job with name: '{jobname}'")
        tooltip_delay = self.context.setting(int, "tooltip_delay", 100)
        interval = tooltip_delay / 1000.0
        self._tooltip_job = Job(
            process=self._exec_tooltip_job,
            job_name=jobname,
            interval=interval,
            times=1,
            run_main=True,
        )

    # Preparation for individual page visibility
    def visible_pages(self):
        count = 0
        for p in self.pages:
            if p.visible:
                count += 1
        return count

    def first_page(self):
        # returns the first visible page
        for p in self.pages:
            if p.visible:
                return p
        return None

    def modified(self):
        """
        if modified then we flag the layout and paint as dirty and call for a refresh of the ribbonbar.
        @return:
        """
        # (f"Modified called for RibbonBar with {self.visible_pages()} pages")
        self._paint_dirty = True
        self._layout_dirty = True
        self.context.schedule(self._redraw_job)

    def redrawn(self):
        """
        if refresh needed then we flag the paint as dirty and call for a refresh of the ribbonbar.
        @return:
        """
        self._paint_dirty = True
        self.context.schedule(self._redraw_job)

    def on_size(self, event: wx.SizeEvent):
        self._set_buffer()
        self.modified()

    def on_erase_background(self, event):
        pass

    def on_mouse_enter(self, event: wx.MouseEvent):
        pass

    def on_mouse_leave(self, event: wx.MouseEvent):
        self.art.hover_tab = None
        self.art.hover_button = None
        self.art.hover_dropdown = None
        self.redrawn()

    def stop_tooltip_job(self):
        self._tooltip_job.cancel()

    def start_tooltip_job(self):
        # print (f"Schedule a job with {self._tooltip_job.interval:.2f}sec")
        self.context.schedule(self._tooltip_job)

    def _exec_tooltip_job(self):
        # print (f"Executed with {self._tooltip}")
        try:
            super().SetToolTip(self._tooltip)
        except RuntimeError:
            # Could happen on a shutdown...
            return

    def SetToolTip(self, message):
        if callable(message):
            self._tooltip = message()
        else:
            self._tooltip = message
        if message == "":
            self.stop_tooltip_job()
            super().SetToolTip(message)
        else:
            # we restart the job and delete the tooltip in the meantime
            super().SetToolTip("")
            self.start_tooltip_job()

    def _check_hover_dropdown(self, drop, pos):
        if drop is not None and not drop.contains(pos):
            drop = None
        if drop is not self.art.hover_dropdown:
            self.art.hover_dropdown = drop
            self.redrawn()

    def _check_hover_button(self, pos):
        hover = self._overflow_at_position(pos)
        if hover is not None:
            self.SetToolTip(_("There is more to see - click to display"))
            self.SetHelpText("")
            return
        hover = self._button_at_position(pos)
        if hover is not None:
            self._check_hover_dropdown(hover.dropdown, pos)
        if hover is not None and hover is self.art.hover_button:
            return
        self.art.hover_button = hover
        if hover is None:
            hover = self._button_at_position(pos, use_all=True)
        if hover is not None:
            self.SetToolTip(hover.tip)
            hhelp = hover.help
            if hhelp is None:
                hhelp = ""
            self.SetHelpText(hhelp)
        else:
            self.SetToolTip("")
            self.SetHelpText("")

        self.redrawn()

    def _check_hover_tab(self, pos):
        hover = self._pagetab_at_position(pos)
        if hover is not self.art.hover_tab:
            self.art.hover_tab = hover
            self.redrawn()

    def on_mouse_move(self, event: wx.MouseEvent):
        pos = event.Position
        self._check_hover_button(pos)
        self._check_hover_tab(pos)

    def on_paint(self, event: wx.PaintEvent):
        """
        Ribbonbar paint event calls the paints the bitmap self._ribbon_buffer. If self._ribbon_buffer does not exist
        initially it is created in the self.scene.update_buffer_ui_thread() call.
        """
        if self._paint_dirty:
            self._paint_main_on_buffer()

        try:
            wx.BufferedPaintDC(self, self._ribbon_buffer)
        except (RuntimeError, AssertionError, TypeError):
            pass

    def _paint_main_on_buffer(self):
        """Performs redrawing of the data in the UI thread."""
        # print (f"Redraw job started for RibbonBar with {self.visible_pages()} pages")
        if self._redraw_lock.acquire(timeout=0.2):
            try:
                buf = self._set_buffer()
                dc = wx.MemoryDC()
                dc.SelectObject(buf)
                if self._layout_dirty:
                    self.art.layout(dc, self)
                    self._layout_dirty = False
                self.art.paint_main(dc, self)
                dc.SelectObject(wx.NullBitmap)
                del dc
                self._paint_dirty = False
            except (RuntimeError, AssertionError):
                pass
                # Shutdown error
            finally:
                self._redraw_lock.release()
        try:
            self.Refresh()  # Paint buffer on screen.
        except RuntimeError:
            # Shutdown error
            pass

    def prefer_horizontal(self):
        result = None
        if self.pane is not None:
            try:
                pane = self.pane.manager.GetPane(self.pane.name)
                if pane.IsDocked():
                    # if self.pane.name == "tools":
                    #     print (
                    #         f"Pane: {pane.name}: {pane.dock_direction}, State: {pane.IsOk()}/{pane.IsDocked()}/{pane.IsFloating()}"
                    #     )
                    if pane.dock_direction in (1, 3):
                        # Horizontal
                        result = True
                    elif pane.dock_direction in (2, 4):
                        # Vertical
                        result = False
                # else:
                #     if self.pane.name == "tools":
                #         print (
                #             f"Pane: {pane.name}: {pane.IsFloating()}"
                #         )
            except (AttributeError, RuntimeError):
                # Unknown error occurred
                pass

        if result is None:
            # Floating...
            width, height = self.ClientSize
            if width <= 0:
                width = 1
            if height <= 0:
                height = 1
            result = bool(width >= height)

        return result

    def _set_buffer(self):
        """
        Set the value for the self._Buffer bitmap equal to the panel's clientSize.
        """
        if (
            self._ribbon_buffer is None
            or self._ribbon_buffer.GetSize() != self.ClientSize
            or not self._ribbon_buffer.IsOk()
        ):
            width, height = self.ClientSize
            if width <= 0:
                width = 1
            if height <= 0:
                height = 1
            self._ribbon_buffer = wx.Bitmap(width, height)
        return self._ribbon_buffer

    def toggle_show_labels(self, v):
        self.art.show_labels = v
        self.modified()

    def _overflow_at_position(self, pos):
        for page in self.pages:
            if page is not self.art.current_page or not page.visible:
                continue
            for panel in page.panels:
                x, y = pos
                # print (f"Checking: {panel.label}: ({x},{y}) in ({panel._overflow_position})")
                if panel._overflow_position is None:
                    continue
                if (
                    panel._overflow_position[0] < x < panel._overflow_position[2]
                    and panel._overflow_position[1] < y < panel._overflow_position[3]
                ):
                    # print (f"Found a panel: {panel.label}")
                    return panel
        return None

    def _button_at_position(self, pos, use_all=False):
        """
        Find the button at the given position, so long as that button is enabled.

        @param pos:
        @return:
        """
        for page in self.pages:
            if page is not self.art.current_page or not page.visible:
                continue
            for panel in page.panels:
                for button in panel.visible_buttons():
                    if (
                        button.contains(pos)
                        and (button.enabled or use_all)
                        and not button.overflow
                    ):
                        return button
        return None

    def _pagetab_at_position(self, pos):
        """
        Find the page tab at the given position.

        @param pos:
        @return:
        """
        for page in self.pages:
            if page.visible and page.contains(pos):
                return page
        return None

    def on_click_right(self, event: wx.MouseEvent):
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
        else:
            # Click on background, off menu to edit and set colors
            def set_color(newmode):
                self.context.root.ribbon_color = newmode
                # Force refresh
                self.context.signal("ribbon_recreate", None)

            top = self  # .parent
            c_mode = self.context.root.setting(int, "ribbon_color", COLOR_MODE_DEFAULT)
            menu = wx.Menu()
            item = menu.Append(wx.ID_ANY, _("Colorscheme"))
            item.Enable(False)
            item = menu.Append(wx.ID_ANY, _("System Default"), "", wx.ITEM_CHECK)
            item.Check(bool(c_mode == COLOR_MODE_DEFAULT))
            top.Bind(
                wx.EVT_MENU, lambda v: set_color(COLOR_MODE_DEFAULT), id=item.GetId()
            )
            item = menu.Append(wx.ID_ANY, _("Colored"), "", wx.ITEM_CHECK)
            item.Check(bool(c_mode == COLOR_MODE_COLOR))
            top.Bind(
                wx.EVT_MENU, lambda v: set_color(COLOR_MODE_COLOR), id=item.GetId()
            )
            item = menu.Append(wx.ID_ANY, _("Black"), "", wx.ITEM_CHECK)
            item.Check(bool(c_mode == COLOR_MODE_DARK))
            top.Bind(wx.EVT_MENU, lambda v: set_color(COLOR_MODE_DARK), id=item.GetId())
            item = menu.AppendSeparator()
            haslabel = self.art.show_labels
            item = menu.Append(wx.ID_ANY, _("Show Labels"), "", wx.ITEM_CHECK)
            if not getattr(self, "allow_labels", True):
                item.Enable(False)
            item.Check(haslabel)
            top.Bind(
                wx.EVT_MENU,
                lambda v: self.toggle_show_labels(not haslabel),
                id=item.GetId(),
            )
            item = menu.AppendSeparator()
            item = menu.Append(wx.ID_ANY, _("Customize Toolbars"))

            def show_pref():
                self.context("window open Preferences\n")
                self.context.signal("preferences", "ribbon")

            top.Bind(
                wx.EVT_MENU,
                lambda v: show_pref(),
                id=item.GetId(),
            )
            top.PopupMenu(menu)

    def on_click(self, event: wx.MouseEvent):
        """
        The ribbon bar was clicked. We check the various parts of the ribbonbar that could have been clicked in the
        preferred click order. Overflow, pagetab, drop-down, button.
        @param event:
        @return:
        """
        pos = event.Position

        page = self._pagetab_at_position(pos)
        overflow = self._overflow_at_position(pos)
        if overflow is not None:
            overflow.overflow_click()
            self.modified()
            return

        button = self._button_at_position(pos)
        if page is not None and button is None:
            self.art.current_page = page
            self.apply_enable_rules()
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

    def _all_buttons(self):
        """
        Helper to cycle through all buttons in the panels that are currently visible.
        @return:
        """
        for page in self.pages:
            if page is not self.art.current_page or not page.visible:
                continue
            for panel in page.panels:
                for button in panel.buttons:
                    yield button

    def apply_enable_rules(self):
        """
        Applies all enable rules for all buttons that are currently seen.
        @return:
        """
        for button in self._all_buttons():
            button.apply_enable_rules()

    def add_page(self, ref, id, label, icon):
        """
        Add a page to the ribbonbar.
        @param ref:
        @param id:
        @param label:
        @param icon:
        @return:
        """
        page = RibbonPage(
            self.context,
            self,
            id,
            label,
            icon,
            ref,
        )
        if ref is not None:
            # print(f"Setattr in add_page: {ref} = {page}")
            setattr(self, ref, page)
        if self.art.current_page is None:
            self.art.current_page = page
        self.pages.append(page)
        self._layout_dirty = True
        return page

    def remove_page(self, pageid):
        """
        Remove a page from the ribbonbar.
        @param pageid:
        @return:
        """
        for pidx, page in enumerate(self.pages):
            if page.id == pageid:
                if self.art.current_page is page:
                    self.art.current_page = None
                for panel in page.panels:
                    panel.clear_buttons()
                    del panel
                self.pages.pop(pidx)
                break

        self._layout_dirty = True

    def validate_current_page(self):
        if self.art.current_page is None or not self.art.current_page.visible:
            self.art.current_page = self.first_page()

    def add_panel(self, ref, parent: RibbonPage, id, label, icon):
        """
        Add a panel to the ribbon bar. Parent must be a page.
        @param ref:
        @param parent:
        @param id:
        @param label:
        @param icon:
        @return:
        """
        panel = RibbonPanel(
            self.context,
            parent=parent,
            id=id,
            label=label,
            icon=icon,
        )
        parent.add_panel(panel, ref)
        self._layout_dirty = True
        return panel


class Art:
    def __init__(self, parent):
        self.RIBBON_ORIENTATION_AUTO = 0
        self.RIBBON_ORIENTATION_HORIZONTAL = 1
        self.RIBBON_ORIENTATION_VERTICAL = 2
        self.orientation = self.RIBBON_ORIENTATION_AUTO
        self.parent = parent
        self.between_button_buffer = 3
        self.panel_button_buffer = 3
        self.page_panel_buffer = 3
        self.between_panel_buffer = 5

        self.tab_width = 70
        self.tab_height = 20
        self.tab_tab_buffer = 10
        self.tab_initial_buffer = 30
        self.tab_text_buffer = 2
        self.edge_page_buffer = 4
        self.rounded_radius = 3
        self.font_sizes = {}

        self.bitmap_text_buffer = 5
        self.dropdown_height = 20
        self.overflow_width = 20
        self.text_dropdown_buffer = 7
        self.show_labels = True

        self.establish_colors()

        self.current_page = None
        self.hover_tab = None
        self.hover_button = None
        self.hover_dropdown = None

    def establish_colors(self):
        self.text_color = copy.copy(
            wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNTEXT)
        )
        self.text_color_inactive = copy.copy(self.text_color).ChangeLightness(50)
        self.text_color_disabled = wx.Colour("Dark Grey")
        self.black_color = copy.copy(
            wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNTEXT)
        )

        self.button_face_hover = copy.copy(
            wx.SystemSettings().GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        ).ChangeLightness(150)
        # self.button_face_hover = copy.copy(
        #     wx.SystemSettings().GetColour(wx.SYS_COLOUR_GRADIENTACTIVECAPTION)
        # )
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
            wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNHILIGHT)
        )
        self.ribbon_background = copy.copy(
            wx.SystemSettings().GetColour(wx.SYS_COLOUR_BTNHILIGHT)
        )
        self.highlight = copy.copy(
            wx.SystemSettings().GetColour(wx.SYS_COLOUR_HOTLIGHT)
        )

        # Do we have a setting for the color?
        c_mode = self.parent.context.root.setting(int, "ribbon_color", 0)
        # 0 system default
        # 1 colored background
        # 2 forced dark_mode
        if c_mode < COLOR_MODE_DEFAULT or c_mode > COLOR_MODE_DARK:
            c_mode = COLOR_MODE_DEFAULT
        if (
            c_mode == COLOR_MODE_DEFAULT
            and self.parent.context.themes.dark # wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        ):
            c_mode = COLOR_MODE_DARK  # dark mode
        self.color_mode = c_mode

        if self.color_mode == COLOR_MODE_DARK:
            # This is rather crude, as a dark mode could also
            # be based e.g. on a dark blue scheme
            self.button_face = wx.BLACK
            self.ribbon_background = wx.BLACK
            self.text_color = wx.WHITE
            self.text_color_inactive = copy.copy(self.text_color)
            self.text_color_disabled = wx.Colour("Light Grey")
            self.black_color = wx.WHITE
            self.inactive_background = wx.BLACK
            OS_NAME = platform.system()
            if OS_NAME == "Windows":
                self.button_face_hover = wx.BLUE
        if self.color_mode == COLOR_MODE_COLOR:
            self.ribbon_background = copy.copy(
                wx.SystemSettings().GetColour(wx.SYS_COLOUR_GRADIENTINACTIVECAPTION)
            )
            self.button_face = copy.copy(
                wx.SystemSettings().GetColour(wx.SYS_COLOUR_GRADIENTACTIVECAPTION)
            )
            self.button_face_hover = wx.Colour("gold").ChangeLightness(150)
            self.highlight = wx.Colour("gold")

        # Let's adjust the fontsize for the page headers
        screen_wd, screen_ht = wx.GetDisplaySize()
        ptdefault = 10
        if screen_wd <= 800 or screen_ht <= 600:
            ptdefault = 8
            self.tab_height = 16
        try:
            wxsize = wx.Size(ptdefault, ptdefault)
            dipsize = self.parent.FromDIP(wxsize)
            ptsize = int(wxsize[0] + 0.5 * (dipsize[0] - wxsize[0]))
            # print(ptdefault, wxsize[0], ptsize, dipsize[0])
        except AttributeError:
            ptsize = ptdefault
        self.default_font = wx.Font(
            ptsize, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )

    def paint_main(self, dc, ribbon):
        """
        Main paint routine. This should delegate, in paint order, to the things on screen that require painting.
        @return:
        """
        self._paint_background(dc)
        self.parent.validate_current_page()

        if ribbon.visible_pages() > 1:
            for page in ribbon.pages:
                if page.visible:
                    self._paint_tab(dc, page)
        else:
            self.current_page = ribbon.first_page()
        if self.current_page is not None:
            if self.current_page.position is None:
                # print("Was dirty...")
                self.layout(dc, self.parent)

        for page in ribbon.pages:
            if page is not self.current_page or not page.visible:
                continue

            dc.SetBrush(wx.Brush(self.ribbon_background))
            x, y, x1, y1 = page.position
            dc.DrawRoundedRectangle(
                int(x), int(y), int(x1 - x), int(y1 - y), self.rounded_radius
            )
            self.look_at_button_font_sizes(dc, page)
            for panel in page.panels:
                # We suppress empty panels
                if panel is None or panel.visible_button_count == 0:
                    continue
                self._paint_panel(dc, panel)
                for button in panel.visible_buttons():
                    self._paint_button(dc, button)

    def look_at_button_font_sizes(self, dc, page):
        self.font_sizes = {}
        for panel in page.panels:
            # We suppress empty panels
            if panel is None or panel.visible_button_count == 0:
                continue
            for button in panel.visible_buttons():
                x, y, x1, y1 = button.position
                start_y = y
                w = int(round(x1 - x, 2))
                h = int(round(y1 - y, 2))
                img_h = h
                # do we have text? if yes let's reduce the available space in y
                if self.show_labels:  # Regardless whether we have a label or not...
                    img_h -= self.bitmap_text_buffer
                    ptsize = min(18, int(round(min(w, img_h) / 5.0, 2)) * 2)
                    img_h -= int(ptsize * 1.35)

                button.get_bitmaps(min(w, img_h))
                if button.enabled:
                    bitmap = button.bitmap
                else:
                    bitmap = button.bitmap_disabled

                bitmap_width, bitmap_height = bitmap.Size
                # if button.label in  ("Circle", "Ellipse", "Wordlist", "Property Window"):
                #     print (f"N - {button.label}: {bitmap_width}x{bitmap_height} in {w}x{h}")
                bs = min(bitmap_width, bitmap_height)
                ptsize = self.get_font_size(bs)
                y += bitmap_height

                text_edge = self.bitmap_text_buffer
                if button.label and self.show_labels:
                    show_text = True
                    label_text = list(button.label.split(" "))
                    # We try to establish whether this would fit properly.
                    # We allow a small oversize of 25% to the button,
                    # before we try to reduce the fontsize
                    wouldfit = False
                    while not wouldfit:
                        total_text_height = 0
                        testfont = wx.Font(
                            ptsize,
                            wx.FONTFAMILY_SWISS,
                            wx.FONTSTYLE_NORMAL,
                            wx.FONTWEIGHT_NORMAL,
                        )
                        test_y = y + text_edge
                        dc.SetFont(testfont)
                        wouldfit = True
                        i = 0
                        while i < len(label_text):
                            # We know by definition that all single words
                            # are okay for drawing, now we check whether
                            # we can draw multiple in one line
                            word = label_text[i]
                            cont = True
                            while cont:
                                cont = False
                                if i < len(label_text) - 1:
                                    nextword = label_text[i + 1]
                                    test = word + " " + nextword
                                    tw, th = dc.GetTextExtent(test)
                                    if tw < w:
                                        word = test
                                        i += 1
                                        cont = True

                            text_width, text_height = dc.GetTextExtent(word)
                            if text_width > w:
                                wouldfit = False
                                break
                            test_y += text_height
                            total_text_height += text_height
                            if test_y > y1:
                                wouldfit = False
                                text_edge = 0
                                break
                            i += 1

                        if wouldfit:
                            # Let's see how much we have...
                            if ptsize in self.font_sizes:
                                self.font_sizes[ptsize] += 1
                            else:
                                self.font_sizes[ptsize] = 1
                            break

                        ptsize -= 2
                        if ptsize < 6:  # too small
                            break

    def _paint_tab(self, dc: wx.DC, page: RibbonPage):
        """
        Paint the individual page tab.

        @param dc:
        @param page:
        @return:
        """
        horizontal = self.parent.prefer_horizontal()
        highlight_via_color = False

        dc.SetPen(wx.Pen(self.black_color))
        show_rect = True
        if page is not self.current_page:
            dc.SetBrush(wx.Brush(self.button_face))
            dc.SetTextForeground(self.text_color_inactive)
            if not highlight_via_color:
                show_rect = False
        else:
            dc.SetBrush(wx.Brush(self.highlight))
            dc.SetBrush(wx.Brush(self.highlight))
            dc.SetTextForeground(self.text_color)
            if not highlight_via_color:
                dc.SetBrush(wx.Brush(self.button_face))
        if page is self.hover_tab and self.hover_button is None:
            dc.SetBrush(wx.Brush(self.button_face_hover))
            show_rect = True
        x, y, x1, y1 = page.tab_position
        if show_rect:
            dc.DrawRoundedRectangle(
                int(x), int(y), int(x1 - x), int(y1 - y), self.rounded_radius
            )
        dc.SetFont(self.default_font)
        text_width, text_height = dc.GetTextExtent(page.label)
        tpx = int(x + (x1 - x - text_width) / 2)
        tpy = int(y + self.tab_text_buffer)
        if horizontal:
            dc.DrawText(page.label, tpx, tpy)
        else:
            tpx = int(x + self.tab_text_buffer)
            tpy = int(y1 - (y1 - y - text_width) / 2)
            dc.DrawRotatedText(page.label, tpx, tpy, 90)

    def _paint_background(self, dc: wx.DC):
        """
        Paint the background of the ribbonbar.
        @param dc:
        @return:
        """
        w, h = dc.Size
        dc.SetBrush(wx.Brush(self.ribbon_background))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(0, 0, w, h)

    def _paint_panel(self, dc: wx.DC, panel: RibbonPanel):
        """
        Paint the ribbonpanel of the given panel.
        @param dc:
        @param panel:
        @return:
        """
        if not panel.position:
            # print(f"Panel position was not set for {panel.label}")
            return
        x, y, x1, y1 = panel.position
        # print(f"Painting panel {panel.label}: {panel.position}")
        dc.SetBrush(wx.Brush(self.ribbon_background))
        dc.SetPen(wx.Pen(self.black_color))
        dc.DrawRoundedRectangle(
            int(x), int(y), int(x1 - x), int(y1 - y), self.rounded_radius
        )
        """
        Paint the overflow of buttons that cannot be stored within the required width.

        @param dc:
        @return:
        """
        if not panel._overflow_position:
            return
        x, y, x1, y1 = panel._overflow_position
        dc.SetBrush(wx.Brush(self.highlight))
        dc.SetPen(wx.Pen(self.black_color))
        dc.DrawRoundedRectangle(
            int(x), int(y), int(x1 - x), int(y1 - y), self.rounded_radius
        )
        r = min((y1 - y) / 2, (x1 - x) / 2) - 2
        cx = (x + x1) / 2
        cy = -r / 2 + (y + y1) / 2
        # print (f"area: {x},{y}-{x1},{y1} - center={cx},{cy} r={r}")
        # points = [
        #     (
        #         int(cx + r * math.cos(math.radians(angle))),
        #         int(cy + r * math.sin(math.radians(angle))),
        #     )
        #     for angle in (0, 90, 180)
        # ]
        lx = x + (x1 - x) / 8
        rx = x1 - (x1 - x) / 8
        mx = x + (x1 - x) / 2
        ty = y + (y1 - y) * 2 / 8
        by = y1 - (y1 - y) * 2 / 8
        points = [
            (int(lx), int(ty)),
            (int(rx), int(ty)),
            (int(mx), int(by)),
            (int(lx), int(ty)),
        ]
        dc.SetPen(wx.Pen(self.black_color))
        dc.SetBrush(wx.Brush(self.inactive_background))
        dc.DrawPolygon(points)

    def _paint_dropdown(self, dc: wx.DC, dropdown: DropDown):
        """
        Paint the dropdown on the button containing a dropdown.

        @param dc:
        @param dropdown:
        @return:
        """
        x, y, x1, y1 = dropdown.position
        if dropdown is self.hover_dropdown:
            dc.SetBrush(wx.Brush(wx.Colour(self.highlight)))
        else:
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetPen(wx.TRANSPARENT_PEN)

        dc.DrawRoundedRectangle(
            int(x), int(y), int(x1 - x), int(y1 - y), self.rounded_radius
        )
        lx = x + (x1 - x) / 8
        rx = x1 - (x1 - x) / 8
        mx = x + (x1 - x) / 2
        ty = y + (y1 - y) * 2 / 8
        by = y1 - (y1 - y) * 2 / 8
        points = [
            (int(lx), int(ty)),
            (int(rx), int(ty)),
            (int(mx), int(by)),
            (int(lx), int(ty)),
        ]
        dc.SetPen(wx.Pen(self.black_color))
        dc.SetBrush(wx.Brush(self.inactive_background))
        dc.DrawPolygon(points)

    def _paint_button(self, dc: wx.DC, button: Button):
        """
        Paint the given button on the screen.

        @param dc:
        @param button:
        @return:
        """
        if button.overflow or not button.visible or button.position is None:
            return

        dc.SetBrush(wx.Brush(self.button_face))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetTextForeground(self.text_color)
        if not button.enabled:
            dc.SetBrush(wx.Brush(self.inactive_background))
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetTextForeground(self.text_color_disabled)
        if button.toggle:
            dc.SetBrush(wx.Brush(self.highlight))
            dc.SetPen(wx.Pen(self.black_color))
        if self.hover_button is button and self.hover_dropdown is None:
            dc.SetBrush(wx.Brush(self.button_face_hover))
            dc.SetPen(wx.Pen(self.black_color))

        x, y, x1, y1 = button.position
        start_y = y
        w = int(round(x1 - x, 2))
        h = int(round(y1 - y, 2))
        img_h = h
        # do we have text? if yes let's reduce the available space in y
        if self.show_labels:  # Regardless whether we have a label or not...
            img_h -= self.bitmap_text_buffer
            ptsize = min(18, int(round(min(w, img_h) / 5.0, 2)) * 2)
            img_h -= int(ptsize * 1.35)

        button.get_bitmaps(min(w, img_h))
        if button.enabled:
            bitmap = button.bitmap
        else:
            bitmap = button.bitmap_disabled

        # Let's clip the output
        dc.SetClippingRegion(int(x), int(y), int(w), int(h))

        dc.DrawRoundedRectangle(int(x), int(y), int(w), int(h), self.rounded_radius)
        bitmap_width, bitmap_height = bitmap.Size
        # if button.label in  ("Circle", "Ellipse", "Wordlist", "Property Window"):
        #     print (f"N - {button.label}: {bitmap_width}x{bitmap_height} in {w}x{h}")
        bs = min(bitmap_width, bitmap_height)
        ptsize = self.get_best_font_size(bs)
        font = wx.Font(
            ptsize, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )

        dc.DrawBitmap(bitmap, int(x + (w - bitmap_width) / 2), int(y))

        # # For debug purposes: draw rectangle around bitmap
        # dc.SetBrush(wx.TRANSPARENT_BRUSH)
        # dc.SetPen(wx.RED_PEN)
        # dc.DrawRectangle(int(x + (w - bitmap_width) / 2), int(y), bitmap_width, bitmap_height)

        y += bitmap_height

        text_edge = self.bitmap_text_buffer
        if button.label and self.show_labels:
            show_text = True
            label_text = list(button.label.split(" "))
            # We try to establish whether this would fit properly.
            # We allow a small oversize of 25% to the button,
            # before we try to reduce the fontsize
            wouldfit = False
            while not wouldfit:
                total_text_height = 0
                testfont = wx.Font(
                    ptsize,
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                )
                test_y = y + text_edge
                dc.SetFont(testfont)
                wouldfit = True
                i = 0
                while i < len(label_text):
                    # We know by definition that all single words
                    # are okay for drawing, now we check whether
                    # we can draw multiple in one line
                    word = label_text[i]
                    cont = True
                    while cont:
                        cont = False
                        if i < len(label_text) - 1:
                            nextword = label_text[i + 1]
                            test = word + " " + nextword
                            tw, th = dc.GetTextExtent(test)
                            if tw < w:
                                word = test
                                i += 1
                                cont = True

                    text_width, text_height = dc.GetTextExtent(word)
                    if text_width > w:
                        wouldfit = False
                        break
                    test_y += text_height
                    total_text_height += text_height
                    if test_y > y1:
                        wouldfit = False
                        text_edge = 0
                        break
                    i += 1

                if wouldfit:
                    font = testfont
                    break

                ptsize -= 2
                if ptsize < 6:  # too small
                    break
            if not wouldfit:
                show_text = False
                label_text = list()
        else:
            show_text = False
            label_text = list()
        if show_text:
            # if it wasn't a full fit, the new textsize might still be okay to be drawn at the intended position
            text_edge = min(
                max(0, start_y + h - y - total_text_height), self.bitmap_text_buffer
            )

            y += text_edge
            dc.SetFont(font)
            i = 0
            while i < len(label_text):
                # We know by definition that all single words
                # are okay for drawing, now we check whether
                # we can draw multiple in one line
                word = label_text[i]
                cont = True
                while cont:
                    cont = False
                    if i < len(label_text) - 1:
                        nextword = label_text[i + 1]
                        test = word + " " + nextword
                        tw, th = dc.GetTextExtent(test)
                        if tw < w:
                            word = test
                            i += 1
                            cont = True

                text_width, text_height = dc.GetTextExtent(word)
                dc.DrawText(
                    word,
                    int(x + (w / 2.0) - (text_width / 2)),
                    int(y),
                )
                y += text_height
                i += 1
        if button.dropdown is not None and button.dropdown.position is not None:
            self._paint_dropdown(dc, button.dropdown)
        dc.DestroyClippingRegion()

    def layout(self, dc: wx.DC, ribbon):
        """
        Performs the layout of the page. This is determined to be the size of the ribbon minus any edge buffering.

        @param dc:
        @param ribbon:
        @return:
        """
        ribbon_width, ribbon_height = dc.Size
        # print(f"ribbon: {dc.Size}")
        horizontal = self.parent.prefer_horizontal()
        xpos = 0
        ypos = 0
        has_page_header = ribbon.visible_pages() > 1
        dc.SetFont(self.default_font)
        for pn, page in enumerate(ribbon.pages):
            if not page.visible:
                continue
            # Set tab positioning.
            # Compute tabwidth according to be displayed label,
            # if bigger than default then extend width
            if has_page_header:
                line_width, line_height = dc.GetTextExtent(page.label)
                if line_height + 4 > self.tab_height:
                    self.tab_height = line_height + 4
                    for former in range(0, pn):
                        former_page = ribbon.pages[former]
                        t_x, t_y, t_x1, t_y1 = former_page.tab_position
                        if horizontal:
                            t_y1 = t_y + self.tab_height * 2
                        else:
                            t_x1 = t_x + self.tab_height * 2
                        former_page.tab_position = (t_x, t_y, t_x1, t_y1)

                tabwidth = max(line_width + 2 * self.tab_tab_buffer, self.tab_width)
                if horizontal:
                    t_x = pn * self.tab_tab_buffer + xpos + self.tab_initial_buffer
                    t_x1 = t_x + tabwidth
                    t_y = ypos
                    t_y1 = t_y + self.tab_height * 2
                else:
                    t_y = pn * self.tab_tab_buffer + ypos + self.tab_initial_buffer
                    t_y1 = t_y + tabwidth
                    t_x = xpos
                    t_x1 = t_x + self.tab_height * 2
                page.tab_position = (t_x, t_y, t_x1, t_y1)
                if horizontal:
                    xpos += tabwidth
                else:
                    ypos += tabwidth
            else:
                page.tab_position = (0, 0, 0, 0)
            if page is not self.current_page:
                continue

            page_width = ribbon_width - self.edge_page_buffer
            page_height = ribbon_height - self.edge_page_buffer
            if horizontal:
                page_width -= self.edge_page_buffer
                x = self.edge_page_buffer
                if has_page_header:
                    y = self.tab_height
                    page_height -= self.tab_height
                else:
                    x = self.edge_page_buffer
                    y = 0
            else:
                page_height -= self.edge_page_buffer
                y = self.edge_page_buffer
                if has_page_header:
                    x = self.tab_height
                    page_width -= self.tab_height
                else:
                    y = self.edge_page_buffer
                    x = 0

            # Page start position.
            if horizontal:
                if has_page_header:
                    y = self.tab_height
                    page_height += self.edge_page_buffer
                else:
                    x = self.edge_page_buffer
                    y = 0
            else:
                if has_page_header:
                    x = self.tab_height
                    page_width += self.edge_page_buffer
                else:
                    y = self.edge_page_buffer
                    x = 0
            # Set page position.
            page.position = (
                x,
                y,
                x + page_width,
                y + page_height,
            )

            # if self.parent.visible_pages() == 1:
            #     print(f"page: {page.position}")
            self.page_layout(dc, page)

    def preferred_button_size_for_page(self, dc, page):
        x, y, max_x, max_y = page.position
        page_width = max_x - x
        page_height = max_y - y
        horizontal = self.parent.prefer_horizontal()
        is_horizontal = (self.orientation == self.RIBBON_ORIENTATION_HORIZONTAL) or (
            horizontal and self.orientation == self.RIBBON_ORIENTATION_AUTO
        )
        # Count buttons and panels
        total_button_count = 0
        panel_count = 0
        for panel in page.panels:
            plen = panel.visible_button_count
            total_button_count += plen
            if plen > 0:
                panel_count += 1
            # else:
            #     print(f"No buttons for {panel.label} found during layout")
        # Calculate h/v counts for panels and buttons
        if is_horizontal:
            all_button_horizontal = max(total_button_count, 1)
            all_button_vertical = 1

            all_panel_horizontal = max(panel_count, 1)
            all_panel_vertical = 1
        else:
            all_button_horizontal = 1
            all_button_vertical = max(total_button_count, 1)

            all_panel_horizontal = 1
            all_panel_vertical = max(panel_count, 1)

        # Calculate optimal width/height for just buttons.
        button_width_across_panels = page_width
        button_width_across_panels -= (
            all_panel_horizontal - 1
        ) * self.between_panel_buffer
        button_width_across_panels -= 2 * self.page_panel_buffer

        button_height_across_panels = page_height
        button_height_across_panels -= (
            all_panel_vertical - 1
        ) * self.between_panel_buffer
        button_height_across_panels -= 2 * self.page_panel_buffer

        for p, panel in enumerate(page.panels):
            if p == 0:
                # Remove high-and-low perpendicular panel_button_buffer
                if is_horizontal:
                    button_height_across_panels -= 2 * self.panel_button_buffer
                else:
                    button_width_across_panels -= 2 * self.panel_button_buffer
            for b, button in enumerate(list(panel.visible_buttons())):
                if b == 0:
                    # First and last buffers.
                    if is_horizontal:
                        button_width_across_panels -= 2 * self.panel_button_buffer
                    else:
                        button_height_across_panels -= 2 * self.panel_button_buffer
                else:
                    # Each gap between buttons
                    if is_horizontal:
                        button_width_across_panels -= self.between_button_buffer
                    else:
                        button_height_across_panels -= self.between_button_buffer

        # Calculate width/height for each button.
        button_width = button_width_across_panels / all_button_horizontal
        button_height = button_height_across_panels / all_button_vertical

        return button_width, button_height

    def page_layout(self, dc, page):
        """
        Determine the layout of the page. This calls for each panel to be set relative to the number of buttons it
        contains.

        @param dc:
        @param page:
        @return:
        """
        x, y, max_x, max_y = page.position
        is_horizontal = (self.orientation == self.RIBBON_ORIENTATION_HORIZONTAL) or (
            self.parent.prefer_horizontal()
            and self.orientation == self.RIBBON_ORIENTATION_AUTO
        )
        button_width, button_height = self.preferred_button_size_for_page(dc, page)
        x += self.page_panel_buffer
        y += self.page_panel_buffer
        """
        THIS ALGORITHM NEEDS STILL TO BE IMPLEMENTED
        --------------------------------------------
        We discuss now the horizontal case, the same
        logic would apply for the vertical case.
        We iterate through the sizes and establish the space
        needed for every panel:
        1) We calculate the required button dimensions for all
        combinations of tiny/small/regular icons plus with/without labels
        2) We get the minimum amount of columns required to display
        the buttons (taking the vertical extent i.e. the amount
        of available rows into account).
        This will provide us with a solution that would need
        the least horizontal space.
        3) That may lead to a situation where you would still
        have horizontal space available for the panels.
        Hence we do a second pass where we assign additional space
        to all panels that need more than one row of icons.
        As we will do this for all possible size combinations,
        we will chose eventually that solution that has the
        fewest amount of buttons in overflow.
        """
        # 1 Calculate button sizes - this is not required
        # here, already done during button creation

        # 2 Loop over all sizes

        # Now that we have gathered all information we can assign
        # the space...
        available_space = 0
        p = -1
        for panel in page.panels:
            if panel.visible_button_count == 0:
                continue
            p += 1
            if p != 0:
                # Non-first move between panel gap.
                if is_horizontal:
                    x += self.between_panel_buffer
                else:
                    y += self.between_panel_buffer

            if is_horizontal:
                single_panel_horizontal = max(panel.visible_button_count, 1)
                single_panel_vertical = 1
            else:
                single_panel_horizontal = 1
                single_panel_vertical = max(panel.visible_button_count, 1)

            panel_width = (
                single_panel_horizontal * button_width
                + (single_panel_horizontal - 1) * self.between_button_buffer
                + 2 * self.panel_button_buffer
            )
            panel_height = (
                single_panel_vertical * button_height
                + (single_panel_vertical - 1) * self.between_button_buffer
                + 2 * self.panel_button_buffer
            )
            if is_horizontal:
                sx = available_space
                sy = 0
            else:
                sx = 0
                sy = available_space
            panel_width += sx
            panel_height += sy
            # print (f"{panel.label} was {panel.position} will be {x}, {y}, {x + panel_width}, {y + panel_height}")
            panel.position = x, y, x + panel_width, y + panel_height
            panel_max_x, panel_max_y = self.panel_layout(dc, panel)
            # print (f"Max values: {panel_max_x}, {panel_max_y}")
            # Do we have more space than needed?
            available_space = 0
            if panel._overflow_position is None:
                recalc = False
                # print (f"({x}, {y}) - ({x + panel_width},  {y+panel_height}), sx={sx}, sy={sy}")
                if is_horizontal:
                    available_space = max(
                        0, x + panel_width - panel_max_x - self.panel_button_buffer
                    )
                    # print (f"x={x + panel_width}, {panel_max_x} will become: {panel_max_x + self.panel_button_buffer}, available={available_space}")
                    if available_space != 0:
                        panel_width = panel_max_x + self.panel_button_buffer - x
                        recalc = True
                else:
                    available_space = max(
                        0, y + panel_height - panel_max_y - self.panel_button_buffer
                    )
                    # print (f"y={y + panel_height}, {panel_max_y} will become: {panel_max_y + self.panel_button_buffer}, available={available_space}")
                    if available_space != 0:
                        panel_height = panel_max_y + self.panel_button_buffer - y
                        recalc = True
                if recalc:
                    panel.position = x, y, x + panel_width, y + panel_height
                    self.panel_layout(dc, panel)

            if is_horizontal:
                x += panel_width
            else:
                y += panel_height

    def panel_layout(self, dc: wx.DC, panel):
        x, y, max_x, max_y = panel.position
        panel_width = max_x - x
        panel_height = max_y - y
        # print(f"Panel: {panel.label}: {panel.position}")
        horizontal = self.parent.prefer_horizontal()
        is_horizontal = (self.orientation == self.RIBBON_ORIENTATION_HORIZONTAL) or (
            horizontal and self.orientation == self.RIBBON_ORIENTATION_AUTO
        )
        plen = panel.visible_button_count
        # if plen == 0:
        #     print(f"layout for panel '{panel.label}' without buttons!")

        distribute_evenly = False
        if is_horizontal:
            button_horizontal = max(plen, 1)
            button_vertical = 1
        else:
            button_horizontal = 1
            button_vertical = max(plen, 1)

        all_button_width = (
            panel_width
            - (button_horizontal - 1) * self.between_button_buffer
            - 2 * self.panel_button_buffer
        )
        all_button_height = (
            panel_height
            - (button_vertical - 1) * self.between_button_buffer
            - 2 * self.panel_button_buffer
        )

        button_width = all_button_width / button_horizontal
        button_height = all_button_height / button_vertical
        # 'tiny'-size of a default 50x50 icon
        minim_size = 15
        button_width = max(minim_size, button_width)
        button_height = max(minim_size, button_height)

        x += self.panel_button_buffer
        y += self.panel_button_buffer
        panel._overflow.clear()
        panel._overflow_position = None
        for b, button in enumerate(list(panel.visible_buttons())):
            bitmapsize = button.max_size
            while bitmapsize > button.min_size:
                if bitmapsize <= button_height and bitmapsize <= button_width:
                    break
                bitmapsize -= 5
            button.get_bitmaps(bitmapsize)
            self.button_calc(dc, button)
            if b == 0:
                max_width = button.min_width
                max_height = button.min_height
            else:
                max_width = max(max_width, button.min_width)
                max_height = max(max_height, button.min_height)

        target_height = button_height
        target_width = button_width
        # print(f"Target: {panel.label} - {target_width}x{target_height}")
        for b, button in enumerate(list(panel.visible_buttons())):
            this_width = target_width
            this_height = target_height
            local_width = 1.25 * button.min_width
            local_height = 1.25 * button.min_height
            if not distribute_evenly:
                if button_horizontal > 1 or is_horizontal:
                    this_width = min(this_width, local_width)
                if button_vertical > 1 or not is_horizontal:
                    this_height = min(this_height, local_height)
            if b != 0:
                # Move across button gap if not first button.
                if is_horizontal:
                    x += self.between_button_buffer
                else:
                    y += self.between_button_buffer
            button.position = x, y, x + this_width, y + this_height
            if is_horizontal:
                is_overflow = False
                if x + this_width > panel.position[2]:
                    is_overflow = True
                    # Let's establish whether there is place for another row of icons underneath
                    # print(
                    #     f"Horizontal Overflow: y={y}, b-height={max_height}, new max={y + 2 * max_height + self.panel_button_buffer}, panel: {panel.position[3]}"
                    # )
                    if (
                        y + 2 + max_height + self.panel_button_buffer
                        < panel.position[3]
                    ):
                        is_overflow = False
                        target_height = max_height
                        # Reset height of all previous buttons:
                        for bb, bbutton in enumerate(list(panel.visible_buttons())):
                            if bb >= b:
                                break
                            bbutton.position = (
                                bbutton.position[0],
                                bbutton.position[1],
                                bbutton.position[2],
                                bbutton.position[1] + max_height,
                            )
                        x = panel.position[0] + self.panel_button_buffer
                        y += max_height + self.panel_button_buffer
                        button.position = x, y, x + this_width, y + max_height
                if is_overflow and panel._overflow_position is None:
                    ppx, ppy, ppx1, ppy1 = panel.position
                    panel._overflow_position = (ppx1 - 15, ppy, ppx1, ppy1)
            else:
                is_overflow = False
                if y + this_height > panel.position[3]:
                    is_overflow = True
                    # print(
                    #     f"Vertical Overflow: x={x}, b-width={max_width}, new max={x + 2 * max_width + self.panel_button_buffer}, panel: {panel.position[2]}"
                    # )
                    # Let's establish whether there is place for another column of icons to the right
                    if x + 2 * max_width + self.panel_button_buffer < panel.position[2]:
                        is_overflow = False
                        target_width = max_width
                        # Reset width of all previous buttons:
                        for bb, bbutton in enumerate(list(panel.visible_buttons())):
                            if bb >= b:
                                break
                            bbutton.position = (
                                bbutton.position[0],
                                bbutton.position[1],
                                bbutton.position[0] + max_width,
                                bbutton.position[3],
                            )
                        y = panel.position[1] + self.panel_button_buffer
                        x += max_width + self.panel_button_buffer
                        button.position = x, y, x + max_width, y + this_height
                if is_overflow and panel._overflow_position is None:
                    ppx, ppy, ppx1, ppy1 = panel.position
                    panel._overflow_position = (ppx, ppy1 - 15, ppx1, ppy1)

            # print(f"button: {button.position}")

            if is_horizontal:
                x += this_width
            else:
                y += this_height
        x = 0
        y = 0
        for button in panel.visible_buttons():
            button.overflow = False
            if button.position[2] > panel.position[2]:
                button.overflow = True
            elif button.position[3] > panel.position[3]:
                button.overflow = True
            elif (
                is_horizontal
                and panel._overflow_position is not None
                and button.position[2] > panel._overflow_position[0]
            ):
                button.overflow = True
            elif (
                not is_horizontal
                and panel._overflow_position is not None
                and button.position[3] > panel._overflow_position[1]
            ):
                button.overflow = True
            # if panel.label == "Create":
            #     print (f"{button.label}: {button.overflow}, {button.position}, {panel.position}, {panel._overflow_position}")
            if button.overflow:
                panel._overflow.append(button)
            else:
                x = max(x, button.position[2])
                y = max(y, button.position[3])
            self.button_layout(dc, button)
        if panel._overflow_position is not None:
            x = max(x, panel._overflow_position[2])
            y = max(y, panel._overflow_position[3])

        return min(x, panel.position[2]), min(y, panel.position[3])

    def button_calc(self, dc: wx.DC, button):
        bitmap = button.bitmap
        ptsize = self.get_font_size(button.icon_size)
        font = wx.Font(
            ptsize, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )

        dc.SetFont(font)
        bitmap_width, bitmap_height = bitmap.Size
        bitmap_height = max(bitmap_height, button.icon_size)
        bitmap_width = max(bitmap_width, button.icon_size)

        # Calculate text height/width
        text_width = 0
        text_height = 0
        if button.label and self.show_labels:
            label_text = list(button.label.split(" "))
            i = 0
            while i < len(label_text):
                # We know by definition that all single words
                # are okay for drawing, now we check whether
                # we can draw multiple in one line
                word = label_text[i]
                cont = True
                while cont:
                    cont = False
                    if i < len(label_text) - 1:
                        nextword = label_text[i + 1]
                        test = word + " " + nextword
                        tw, th = dc.GetTextExtent(test)
                        if tw < bitmap_width:
                            word = test
                            i += 1
                            cont = True
                line_width, line_height = dc.GetTextExtent(word)
                text_width = max(text_width, line_width)
                text_height += line_height
                i += 1

        # Calculate button_width/button_height
        button_width = max(bitmap_width, text_width)
        button_height = bitmap_height
        button_height += 2 * self.panel_button_buffer
        button_width += 2 * self.panel_button_buffer
        if button.label and self.show_labels:
            # button_height += + self.panel_button_buffer
            button_height += self.bitmap_text_buffer + text_height

        button.min_width = button_width
        button.min_height = button_height
        # print (f"layout for {button.label} ({button.bitmapsize}): {button.min_width}x{button.min_height}, icon={bitmap_width}x{bitmap_height}")

    def button_layout(self, dc: wx.DC, button):
        x, y, max_x, max_y = button.position
        bitmap = button.bitmap
        bitmap_width, bitmap_height = bitmap.Size
        if button.kind == "hybrid" and button.key != "toggle":
            # Calculate text height/width
            # Calculate dropdown
            # Same size regardless of bitmap-size
            sizx = 15
            sizy = 15
            if min(bitmap_width, bitmap_height) > 70:
                sizx = 20
                sizy = 20
            elif min(bitmap_width, bitmap_height) > 100:
                sizx = 25
                sizy = 25

            # Let's see whether we have enough room
            extx = (x + max_x) / 2 + bitmap_width / 2 + sizx - 1
            exty = y + bitmap_height + sizy - 1
            extx = max(x - sizx, min(extx, max_x - 1))
            exty = max(y + sizy, min(exty, max_y - 1))
            gap = 15
            if bitmap_height < 30:
                gap = 3

            # print (f"{bitmap_width}x{bitmap_height} - siz={sizx}, gap={gap}")
            button.dropdown.position = (
                extx - sizx,
                exty - sizy - gap,
                extx,
                exty - gap,
            )
            # button.dropdown.position = (
            #     x + bitmap_width / 2,
            #     y + bitmap_height / 2,
            #     x + bitmap_width,
            #     y + bitmap_height,
            # )
            # print (
            #     f"Required for {button.label}: button: {x},{y} to {max_x},{max_y}," +
            #     f"dropd: {extx-sizx},{exty-sizy} to {extx},{exty}"
            # )

    def get_font_size(self, imgsize):
        if imgsize <= 20:
            ptsize = 6
        elif imgsize <= 30:
            ptsize = 8
        elif imgsize <= 40:
            ptsize = 10
        elif imgsize <= 60:
            ptsize = 12
        elif imgsize <= 80:
            ptsize = 14
        else:
            ptsize = 16
        return ptsize

    def get_best_font_size(self, imgsize):
        sizes = [(pt, amount) for pt, amount in self.font_sizes.items()]
        sizes.sort(key=lambda e: e[1], reverse=True)
        best = 32768
        if len(sizes):
            # Take the one where we have most...
            best = sizes[0][0]
        ptsize = self.get_font_size(imgsize)
        if ptsize > best:
            ptsize = best
        return ptsize
