import copy
import platform
import threading

import wx
import wx.lib.agw.ribbon as RB
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

    def OnPaint(self, event):
        """
        Handles the ``wx.EVT_PAINT`` event for :class:`RibbonButtonBar`.

        :param `event`: a :class:`PaintEvent` event to be processed.
        """
        if self.screen_refresh_lock.acquire(timeout=0.2):

            dc = wx.AutoBufferedPaintDC(self)
            if dc is not None:

                self._art.DrawButtonBarBackground(
                    dc, self, wx.Rect(0, 0, *self.GetSize())
                )

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
                        button.position + self._layout_offset,
                        base.sizes[button.size].size,
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


class MyRibbonPanel(RB.RibbonPanel):
    def __init__(
        self,
        parent,
        id=wx.ID_ANY,
        label="",
        minimised_icon=wx.NullBitmap,
        pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        agwStyle=RB.RIBBON_PANEL_DEFAULT_STYLE,
        name="RibbonPanel",
        recurse=False,
    ):
        super().__init__(
            parent=parent,
            id=id,
            label=label,
            minimised_icon=minimised_icon,
            pos=pos,
            size=size,
            agwStyle=agwStyle,
            name=name,
        )
        self.recurse = recurse
        self._expanded_panel = None

    def GetBestSize(self):
        try:
            size = super().GetBestSize()
        except AttributeError:
            size = (0, 0)
        oldw = size[0]
        oldh = size[1]
        # Set default values
        wd = oldw
        ht = oldh
        if size[0] < 50:  # There's something wrong here
            # print ("Wrong best size for %s = %s" % (self.GetLabel(), size))
            for bar in self.GetChildren():
                if isinstance(bar, RB.RibbonButtonBar):
                    wd = 0
                    ht = 0
                    for layout in bar._layouts:
                        wd = max(wd, layout.overall_size.GetWidth())
                        ht = max(ht, layout.overall_size.GetHeight())
                    wd += 10
                    ht += 10
                    if self.GetLabel() != "":
                        ht += 23
                    else:
                        ht += 10
                    break
        else:
            wd = size[0]
            ht = size[1]
        if platform.system != "Windows":
            ht = max(ht, 120)
            maxw = 0
            ct = 0

            for bar in self.GetChildren():
                if isinstance(bar, RB.RibbonButtonBar):
                    # Look for the largest button
                    for button in bar._buttons:
                        w, h = button.bitmap_large.GetSize()
                        maxw = max(maxw, w + 10)
                        ct += 1
                    # Needs to have a minimum size of 25 though
                    maxw = max(maxw, 25 + 10)
            # print ("Ct=%d, widest=%d, wd=%.1f, wd2=%.1f, ht=%.1f, oldh=%.1f" % (ct, maxw, wd, 1.5*ct*maxw, ht, oldh))
            wd = max(wd, int(1.5 * ct * maxw))
        size = wx.Size(wd, ht)
        # print (size, size2)
        # size = size2
        return size

    def IsMinimised(self, at_size=None):
        # Very much simplified version..
        if self.recurse:
            res = False
        else:
            res = super().IsMinimised(at_size)
        return res

    def ShowExpanded(self):
        """
        Show the panel externally expanded.

        When a panel is minimised, it can be shown full-size in a pop-out window, which
        is referred to as being (externally) expanded.

        :returns: ``True`` if the panel was expanded, ``False`` if it was not (possibly
         due to it not being minimised, or already being expanded).

        :note: When a panel is expanded, there exist two panels - the original panel
         (which is referred to as the dummy panel) and the expanded panel. The original
         is termed a dummy as it sits in the ribbon bar doing nothing, while the expanded
         panel holds the panel children.

        :see: :meth:`~RibbonPanel.HideExpanded`, :meth:`~RibbonPanel.GetExpandedPanel`
        """

        if not self.IsMinimised():
            return False

        if self._expanded_dummy is not None or self._expanded_panel != None:
            return False

        size = self.GetBestSize()
        pos = self.GetExpandedPosition(
            wx.Rect(self.GetScreenPosition(), self.GetSize()),
            size,
            self._preferred_expand_direction,
        ).GetTopLeft()

        # Need a top-level frame to contain the expanded panel
        container = wx.Frame(
            None,
            wx.ID_ANY,
            self.GetLabel(),
            pos,
            size,
            wx.FRAME_NO_TASKBAR | wx.BORDER_NONE,
        )

        self._expanded_panel = MyRibbonPanel(
            parent=container,
            id=wx.ID_ANY,
            label=self.GetLabel(),
            minimised_icon=self._minimised_icon,
            pos=wx.Point(0, 0),
            size=size,
            agwStyle=self._flags,
            recurse=True,
        )
        self._expanded_panel.SetArtProvider(self._art)
        self._expanded_panel._expanded_dummy = self

        # Move all children to the new panel.
        # Conceptually it might be simpler to reparent self entire panel to the
        # container and create a new panel to sit in its place while expanded.
        # This approach has a problem though - when the panel is reinserted into
        # its original parent, it'll be at a different position in the child list
        # and thus assume a new position.
        # NB: Children iterators not used as behaviour is not well defined
        # when iterating over a container which is being emptied

        for child in self.GetChildren():
            child.Reparent(self._expanded_panel)
            child.Show()

        # Move sizer to new panel
        if self.GetSizer():
            sizer = self.GetSizer()
            self.SetSizer(None, False)
            self._expanded_panel.SetSizer(sizer)

        self._expanded_panel._minimised = False
        self._expanded_panel.SetSize(size)
        self._expanded_panel.Realize()
        self.Refresh()
        container.Show()
        self._expanded_panel.SetFocus()

        return True


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
    ribbon = RibbonPanel(window, wx.ID_ANY, context=context)
    pane.control = ribbon

    window.on_pane_create(pane)
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
        context.setting(bool, "ribbon_art", False)
        context.setting(bool, "ribbon_hide_labels", False)

        # Some helper variables for showing / hiding the toolbar
        self.panels_shown = True
        self.minmax = None
        self.context = context
        self.stored_labels = {}
        self.stored_height = 0
        self.art_provider_count = 0

        self.button_lookup = {}
        self.group_lookup = {}

        self.toggle_signals = list()

        # Define Ribbon.
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
        # self._ribbon
        self.pipe_state = None
        self._ribbon_dirty = False

    def button_click_right(self, event):
        """
        Handles the ``wx.EVT_RIGHT_DOWN`` event
        :param `event`: a :class:`MouseEvent` event to be processed.
        """
        evt_id = event.GetId()
        bar = None
        active_button = 0
        for item in self.ribbon_bars:
            item_id = item.GetId()
            if item_id == evt_id:
                bar = item
                # Now look for the corresponding buttons...
                if bar._hovered_button is not None:
                    # print ("Hovered button: %d" % bar._hovered_button.base.id)
                    active_button = bar._hovered_button.base.id
                break
        if bar is None or active_button == 0:
            # Nothing found
            return

        # We know the active button. Lookup and execute action_right
        button = self.button_lookup.get(active_button)
        if button is not None:
            action = button.action_right
            if action:
                action(event)

    def button_click(self, event):
        # Let's figure out what kind of action we need to perform
        evt_id = event.GetId()
        self._button_click_id(evt_id, event=event)

    def _button_click_id(self, evt_id, event=None):
        button = self.button_lookup.get(evt_id)
        if button is None:
            return

        if button.group:
            # Toggle radio buttons
            button.toggle = not button.toggle
            if button.toggle:  # got toggled
                button_group = self.group_lookup.get(button.group, [])

                for obutton in button_group:
                    # Untoggle all other buttons in this group.
                    if obutton.group == button.group and obutton.id != button.id:
                        obutton.parent.ToggleButton(obutton.id, False)
            else:  # got untoggled...
                # so let's activate the first button of the group (implicitly defined as default...)
                button_group = self.group_lookup.get(button.group)
                if button_group:
                    first_button = button_group[0]
                    first_button.parent.ToggleButton(first_button.id, True)

                    # Clone event and recurse.
                    if event:
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
            self._restore_button_aspect(button, button.state_pressed)
        else:
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
            setattr(self.context, button.save_id, key_id)
            button.state_unpressed = key_id
            self._restore_button_aspect(button, key_id)
            self.ensure_realize()

        return menu_item_click

    def _restore_button_aspect(self, base_button, key):
        if not hasattr(base_button, "alternatives"):
            return
        try:
            alt = base_button.alternatives[key]
        except KeyError:
            return
        base_button.action = alt.get("action", base_button.action)
        base_button.label = alt.get("label", base_button.label)
        base_button.help_string = alt.get("help_string", base_button.help_string)
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
        if not hasattr(base_button, "alternatives"):
            base_button.alternatives = {}
        base_button.alternatives[key] = {
            "action": base_button.action,
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
        if not hasattr(base_button, "alternatives"):
            base_button.alternatives = {}
        key_dict = base_button.alternatives[key]
        for k in kwargs:
            if kwargs[k] is not None:
                key_dict[k] = kwargs[k]

    def set_buttons(self, new_values, button_bar):
        """
        Set buttons is the primary button configuration routine. It is responsible for clearing and recreating buttons.

        @param new_values: dictionary of button values to use.
        @param button_bar: specific button bar these buttons are applied to.
        @return:
        """
        show_tip = not self.context.disable_tool_tips
        button_bar._current_layout = 0
        button_bar._hovered_button = None
        button_bar._active_button = None
        button_bar.ClearButtons()
        buttons = []
        for button, name, sname in new_values:
            buttons.append(button)

        def sort_priority(elem):
            return elem.get("priority", 0)

        buttons.sort(key=sort_priority)  # Sort buttons by priority

        for button in buttons:
            # Every registered button in the updated lookup gets created.
            group = button.get("group")
            resize_param = button.get("size")
            new_id = wx.NewIdRef()
            if "multi" in button:
                # Button is a multi-type button
                b = button_bar.AddHybridButton(
                    button_id=new_id,
                    label=button["label"],
                    bitmap=button["icon"].GetBitmap(resize=resize_param),
                    help_string=button["tip"] if show_tip else "",
                )
                button_bar.Bind(
                    RB.EVT_RIBBONBUTTONBAR_DROPDOWN_CLICKED,
                    self.drop_click,
                    id=new_id,
                )
            else:
                if "group" in button:
                    bkind = RB.RIBBON_BUTTON_TOGGLE
                else:
                    bkind = RB.RIBBON_BUTTON_NORMAL
                if "toggle" in button:
                    bkind = RB.RIBBON_BUTTON_TOGGLE
                b = button_bar.AddButton(
                    button_id=new_id,
                    label=button["label"],
                    bitmap=button["icon"].GetBitmap(resize=resize_param),
                    bitmap_disabled=button["icon"].GetBitmap(
                        resize=resize_param, color=Color("grey")
                    ),
                    help_string=button["tip"] if show_tip else "",
                    kind=bkind,
                )

            # Store all relevant aspects for newly registered button.
            b.button_dict = button
            b.state_pressed = None
            b.state_unpressed = None
            b.toggle = False
            b.parent = button_bar
            b.group = group
            b.identifier = button.get("identifier")
            b.action = button.get("action")
            b.action_right = button.get("right")
            if "rule_enabled" in button:
                b.enable_rule = button.get("rule_enabled")
            else:
                b.enable_rule = lambda cond: True

            if "multi" in button:
                # Store alternative aspects for multi-buttons, load stored previous state.

                multi_action = button["multi"]
                multi_ident = button.get("identifier")
                b.save_id = multi_ident
                initial_id = self.context.setting(str, b.save_id, "default")

                for i, v in enumerate(multi_action):
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
                    if key == initial_id:
                        self._restore_button_aspect(b, key)
            if "toggle" in button:
                # Store toggle and original aspects for toggle-buttons

                b.state_pressed = "toggle"
                b.state_unpressed = "original"

                self._store_button_aspect(b, "original")

                toggle_action = button["toggle"]
                key = toggle_action.get("identifier", "toggle")
                if "signal" in toggle_action:

                    def make_toggle_click(_tb):
                        def toggle_click(origin, set_value):
                            if set_value:
                                _tb.toggle = False
                                self._restore_button_aspect(_tb, _tb.state_unpressed)
                            else:
                                _tb.toggle = True
                                self._restore_button_aspect(_tb, _tb.state_pressed)
                            _tb.parent.ToggleButton(_tb.id, _tb.toggle)
                            _tb.parent.Refresh()

                        return toggle_click

                    signal_toggle_listener = make_toggle_click(b)
                    self.context.listen(toggle_action["signal"], signal_toggle_listener)
                    self.toggle_signals.append(
                        (toggle_action["signal"], signal_toggle_listener)
                    )

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
                        siz = v_icon.GetBitmap().GetSize()
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
            # Store newly created button in the various lookups
            self.button_lookup[new_id] = b
            if group is not None:
                c_group = self.group_lookup.get(group)
                if c_group is None:
                    c_group = []
                    self.group_lookup[group] = c_group
                c_group.append(b)

            button_bar.Bind(
                RB.EVT_RIBBONBUTTONBAR_CLICKED, self.button_click, id=new_id
            )
            button_bar.Bind(wx.EVT_RIGHT_UP, self.button_click_right)

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
        self.set_buttons(new_values, self.basicediting_button_bar)

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

    @lookup_listener("button/extended_tools")
    def set_tool_extended_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.extended_button_bar)

    @lookup_listener("button/geometry")
    def set_geometry_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.geometry_button_bar)

    @lookup_listener("button/preparation")
    def set_preparation_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.preparation_button_bar)

    @lookup_listener("button/jobstart")
    def set_jobstart_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.jobstart_button_bar)

    @lookup_listener("button/group")
    def set_group_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.group_button_bar)

    @lookup_listener("button/device")
    def set_device_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.device_button_bar)
        self.set_buttons(new_values, self.device_copy_button_bar)

    @lookup_listener("button/align")
    def set_align_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.align_button_bar)

    @lookup_listener("button/properties")
    def set_property_buttons(self, new_values, old_values):
        self.set_buttons(new_values, self.property_button_bar)

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
            # Reset toggle state
            if button.identifier == identifier:
                # Set toggle state
                button.parent.ToggleButton(button.id, True)
                button.toggle = True
            else:
                button.parent.ToggleButton(button.id, False)
                button.toggle = False
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
        self._ribbon.Realize()

    def __set_ribbonbar(self):
        self.ribbonbar_caption_visible = False

        if self.is_dark or self.context.ribbon_art:
            provider = self._ribbon.GetArtProvider()
            _update_ribbon_artprovider_for_dark_mode(
                provider, hide_labels=self.context.ribbon_hide_labels
            )
        self.ribbon_position_aspect_ratio = True
        self.ribbon_position_ignore_update = False

        home = RB.RibbonPage(
            self._ribbon,
            ID_PAGE_MAIN,
            _("Project"),
            icons8_opened_folder_50.GetBitmap(resize=16),
        )
        self.ribbon_pages.append((home, "home"))

        tool = RB.RibbonPage(
            self._ribbon,
            ID_PAGE_DESIGN,
            _("Design"),
            icons8_opened_folder_50.GetBitmap(resize=16),
        )
        self.ribbon_pages.append((tool, "design"))

        modify = RB.RibbonPage(
            self._ribbon,
            ID_PAGE_MODIFY,
            _("Modify"),
            icons8_opened_folder_50.GetBitmap(resize=16),
        )
        self.ribbon_pages.append((modify, "modify"))

        config = RB.RibbonPage(
            self._ribbon,
            ID_PAGE_CONFIG,
            _("Settings"),
            icons8_opened_folder_50.GetBitmap(resize=16),
        )
        self.ribbon_pages.append((config, "config"))

        # self.Bind(
        #    RB.EVT_RIBBONBAR_HELP_CLICK,
        #    lambda e: self.context("webhelp help\n"),
        # )

        panel_style = RB.RIBBON_PANEL_MINIMISE_BUTTON
        self.project_panel = MyRibbonPanel(
            parent=home,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Project"),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.project_panel)
        button_bar = RibbonButtonBar(self.project_panel)
        self.project_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.jobstart_panel = MyRibbonPanel(
            parent=home,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Execute"),
            minimised_icon=icons8_opened_folder_50.GetBitmap(),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.jobstart_panel)
        button_bar = RibbonButtonBar(self.jobstart_panel)
        self.jobstart_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.preparation_panel = MyRibbonPanel(
            parent=home,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Prepare"),
            minimised_icon=icons8_opened_folder_50.GetBitmap(),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.preparation_panel)
        button_bar = RibbonButtonBar(self.preparation_panel)
        self.preparation_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.control_panel = MyRibbonPanel(
            parent=home,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Control"),
            minimised_icon=icons8_opened_folder_50.GetBitmap(),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.control_panel)
        button_bar = RibbonButtonBar(self.control_panel)
        self.control_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.config_panel = MyRibbonPanel(
            parent=config,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Configuration"),
            minimised_icon=icons8_opened_folder_50.GetBitmap(),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.config_panel)
        button_bar = RibbonButtonBar(self.config_panel)
        self.config_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.device_panel = MyRibbonPanel(
            parent=home,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Devices"),
            minimised_icon=icons8_opened_folder_50.GetBitmap(),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.device_panel)
        button_bar = RibbonButtonBar(self.device_panel)
        self.device_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.device_panel_copy = MyRibbonPanel(
            parent=config,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Device"),
            minimised_icon=icons8_opened_folder_50.GetBitmap(),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.device_panel_copy)
        button_bar = RibbonButtonBar(self.device_panel_copy)
        self.device_copy_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.tool_panel = MyRibbonPanel(
            parent=tool,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Design"),
            minimised_icon=icons8_opened_folder_50.GetBitmap(),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.tool_panel)
        button_bar = RibbonButtonBar(self.tool_panel)
        self.tool_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        panel_style = RB.RIBBON_PANEL_MINIMISE_BUTTON
        self.basicediting_panel = MyRibbonPanel(
            parent=tool,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Edit"),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.basicediting_panel)
        button_bar = RibbonButtonBar(self.basicediting_panel)
        self.basicediting_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.group_panel = MyRibbonPanel(
            parent=tool,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Group"),
            minimised_icon=icons8_opened_folder_50.GetBitmap(),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.group_panel)
        button_bar = RibbonButtonBar(self.group_panel)
        self.group_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.extended_panel = MyRibbonPanel(
            parent=tool,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Extended Tools"),
            minimised_icon=icons8_opened_folder_50.GetBitmap(),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.extended_panel)
        button_bar = RibbonButtonBar(self.extended_panel)
        self.extended_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.property_panel = MyRibbonPanel(
            parent=tool,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Properties"),
            minimised_icon=icons8_opened_folder_50.GetBitmap(),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.property_panel)
        button_bar = RibbonButtonBar(self.property_panel)
        self.property_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.modify_panel = MyRibbonPanel(
            parent=modify,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Modification"),
            minimised_icon=icons8_opened_folder_50.GetBitmap(),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.modify_panel)
        button_bar = RibbonButtonBar(self.modify_panel)
        self.modify_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.geometry_panel = MyRibbonPanel(
            parent=modify,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Geometry"),
            minimised_icon=icons8_opened_folder_50.GetBitmap(),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.geometry_panel)
        button_bar = RibbonButtonBar(self.geometry_panel)
        self.geometry_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self.align_panel = MyRibbonPanel(
            parent=modify,
            id=wx.ID_ANY,
            label="" if self.is_dark else _("Alignment"),
            minimised_icon=icons8_opened_folder_50.GetBitmap(),
            agwStyle=panel_style,
        )
        self.ribbon_panels.append(self.align_panel)
        button_bar = RibbonButtonBar(self.align_panel)
        self.align_button_bar = button_bar
        self.ribbon_bars.append(button_bar)

        self._ribbon.Bind(RB.EVT_RIBBONBAR_PAGE_CHANGED, self.on_page_changed)

        self.ensure_realize()

    def pane_show(self):
        pass

    def pane_hide(self):
        for key, listener in self.toggle_signals:
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


def _update_ribbon_artprovider_for_dark_mode(provider, hide_labels=False):
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
    if hide_labels:
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
