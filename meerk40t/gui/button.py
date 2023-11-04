"""
Meerk40t Smart Buttons, interact with the meerk40t kernel to indicate when they are pressed with a signal, give alt
forms of the button, and draw colored buttons on all OSes.
"""

import copy
import platform
import threading

import wx

from meerk40t.gui.icons import STD_ICON_SIZE, PyEmbeddedImage
from meerk40t.kernel import Job
from meerk40t.svgelements import Color

_ = wx.GetTranslation

SMALL_RESIZE_FACTOR = 2 / 3
TINY_RESIZE_FACTOR = 0.5

COLOR_MODE_DEFAULT = 0
COLOR_MODE_COLOR = 1
COLOR_MODE_DARK = 2


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
        self.bitmapsize = "large"

        self.position = None
        self.toggle = False

        self.label = None
        self.bitmap = None
        self.bitmap_disabled = None
        self.bitmap_tiny_disabled = None
        self.bitmap_small_disabled = None
        self.bitmap_large_disabled = None
        self.bitmap_tiny = None
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
        self.rule_visible = None
        self.min_width = 0
        self.min_height = 0
        self.default_width = 50
        self.set_aspect(**description)
        self.apply_enable_rules()
        self.sizes = {
            "large_label": (0, 0),
            "small_label": (0, 0),
            "tiny_label": (0, 0),
            "large": (0, 0),
            "small": (0, 0),
            "tiny": (0, 0),
        }

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
        rule_visible=None,
        object=None,
        **kwargs,
    ):
        """
        This sets all the different aspects that buttons generally have.

        @param label: button label
        @param icon: icon used for this button
        @param tip: tool tip for the button
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
        self.icon = icon
        resize_param = kwargs.get("size")
        if resize_param is None:
            resize_param = STD_ICON_SIZE
        if resize_param is None:
            # We can get the real icon width, that means though
            # all buttons will have slightly different dimensions
            # so we set the minimum size
            siz = icon.GetBitmap().GetSize()
            wd = max(self.default_width, siz[0])
            small_resize = int(SMALL_RESIZE_FACTOR * wd)
            tiny_resize = int(TINY_RESIZE_FACTOR * wd)
            # print (f"No size parameter given for: {label}")

        else:
            self.default_width = resize_param
            small_resize = int(SMALL_RESIZE_FACTOR * resize_param)
            tiny_resize = int(TINY_RESIZE_FACTOR * resize_param)

        top = self.parent
        if top.art.color_mode == COLOR_MODE_DARK:
            targetcolor = Color("white")
            darkm = True
        else:
            targetcolor = None
            darkm = False
        # We need to cast the icon explicitly to PyEmbeddedImage
        # as otherwise a strange type error is thrown:
        # TypeError: GetBitmap() got an unexpected keyword argument 'force_darkmode'
        # Well...
        from meerk40t.gui.icons import PyEmbeddedImage, VectorIcon

        if not isinstance(icon, VectorIcon):
            icon = PyEmbeddedImage(icon.data)
        self.bitmap_large = icon.GetBitmap(
            resize=resize_param,
            noadjustment=True,
            force_darkmode=darkm,
            buffer=5,
        )
        self.bitmap_large_disabled = icon.GetBitmap(
            resize=resize_param,
            color=Color("grey"),
            noadjustment=True,
            force_darkmode=darkm,
            buffer=5,
        )
        self.bitmap_small = icon.GetBitmap(
            resize=small_resize,
            noadjustment=True,
            force_darkmode=darkm,
            buffer=2,
        )
        self.bitmap_small_disabled = icon.GetBitmap(
            resize=small_resize,
            color=Color("grey"),
            noadjustment=True,
            buffer=2,
        )
        self.bitmap_tiny = icon.GetBitmap(
            resize=tiny_resize,
            noadjustment=True,
            force_darkmode=darkm,
            buffer=1,
        )
        self.bitmap_tiny_disabled = icon.GetBitmap(
            resize=tiny_resize,
            color=Color("grey"),
            noadjustment=True,
            buffer=1,
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
        self.rule_visible = rule_visible
        if object is not None:
            self.object = object
        else:
            self.object = self.context
        # if self.kind == "hybrid":
        #     self.dropdown = DropDown()
        self.modified()

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

        @param event:
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


class MButton(wx.Control):
    def __init__(self, parent, id, kind, description, context=None, **kwds):
        super().__init__(parent, id, **kwds)
        self.context = context
        jobname = f"realize_ribbon_bar_{self.GetId()}"
        self._redraw_job = Job(
            process=self._paint_main_on_buffer,
            job_name=jobname,
            interval=0.1,
            times=1,
            run_main=True,
        )

        # Define Button
        self._redraw_lock = threading.Lock()
        self._paint_dirty = True
        self._layout_dirty = True
        self._button_buffer = None

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_mouse_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)

        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        self.Bind(wx.EVT_RIGHT_UP, self.on_click_right)

        self.art = Art(self)
        self.button = Button(context, self, id, kind, description)
        self.button.set_button_toggle(False)


    def modified(self):
        """
        if modified then we flag the layout and paint as dirty and call for a refresh of the button
        @return:
        """
        self._paint_dirty = True
        self._layout_dirty = True
        self.context.schedule(self._redraw_job)

    def redrawn(self):
        """
        if refresh needed then we flag the paint as dirty and call for a refresh of the button.
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
        self.redrawn()

    def _check_hover_button(self, pos):
        hover = self.button
        if hover is not None:
            self.SetToolTip(hover.tip)
        else:
            self.SetToolTip("")

        self.redrawn()

    def on_mouse_move(self, event: wx.MouseEvent):
        pos = event.Position
        self._check_hover_button(pos)

    def on_paint(self, event: wx.PaintEvent):
        """
        Button paint event calls the paints the bitmap self._button_buffer. If self._button_buffer does not exist
        initially it is created in the self.scene.update_buffer_ui_thread() call.
        """
        if self._paint_dirty:
            self._paint_main_on_buffer()

        try:
            wx.BufferedPaintDC(self, self._button_buffer)
        except (RuntimeError, AssertionError, TypeError):
            pass

    def _paint_main_on_buffer(self):
        """Performs redrawing of the data in the UI thread."""
        # print (f"Redraw job started for RibbonBar with {self.visible_pages()} pages")
        try:
            buf = self._set_buffer()
            dc = wx.MemoryDC()
        except RuntimeError:
            # Shutdown error
            return
        dc.SelectObject(buf)
        if self._redraw_lock.acquire(timeout=0.2):
            if self._layout_dirty:
                self.art.layout(dc, self)
                self._layout_dirty = False
            self.art.paint_main(dc, self)
            self._redraw_lock.release()
            self._paint_dirty = False
        dc.SelectObject(wx.NullBitmap)
        del dc

        self.Refresh()  # Paint buffer on screen.

    def _set_buffer(self):
        """
        Set the value for the self._Buffer bitmap equal to the panel's clientSize.
        """
        if (
            self._button_buffer is None
            or self._button_buffer.GetSize() != self.ClientSize
            or not self._button_buffer.IsOk()
        ):
            width, height = self.ClientSize
            if width <= 0:
                width = 1
            if height <= 0:
                height = 1
            self._button_buffer = wx.Bitmap(width, height)
        return self._button_buffer

    def on_click_right(self, event: wx.MouseEvent):
        """
        Handles the ``wx.EVT_RIGHT_DOWN`` event
        :param event: a :class:`MouseEvent` event to be processed.
        """
        button = self.button
        action = button.action_right
        if action:
            action(event)

    def on_click(self, event: wx.MouseEvent):
        """
        The ribbon bar was clicked. We check the various parts of the ribbonbar that could have been clicked in the
        preferred click order. Overflow, pagetab, drop-down, button.
        @param event:
        @return:
        """
        button = self.button
        button.click()
        self.modified()

    def apply_enable_rules(self):
        """
        Applies all enable rules for all buttons that are currently seen.
        @return:
        """
        self.button.apply_enable_rules()


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
            and wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        ):
            c_mode = COLOR_MODE_DARK  # dark mode
        self.color_mode = c_mode

        if self.color_mode == COLOR_MODE_DARK:
            # This is rather crude, as a dark mode could also
            # be based eg on a dark blue scheme
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

        self.default_font = wx.Font(
            10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )
        self.small_font = wx.Font(
            8, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )
        self.tiny_font = wx.Font(
            6, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )

    def paint_main(self, dc, button):
        """
        Main paint routine. This should delegate, in paint order, to the things on screen that require painting.
        @return:
        """
        self._paint_background(dc)
        self._paint_button(dc, button.button)

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

    def _paint_button(self, dc: wx.DC, button: Button):
        """
        Paint the given button on the screen.

        @param dc:
        @param button:
        @return:
        """
        # if button.overflow or not button.visible or button.position is None:
        #     return

        bitmap = button.bitmap_large
        bitmap_small = button.bitmap_small
        bitmap_tiny = button.bitmap_tiny

        button.bitmapsize = "large"
        if not button.enabled:
            bitmap = button.bitmap_large_disabled
            bitmap_small = button.bitmap_small_disabled
            bitmap_tiny = button.bitmap_tiny_disabled

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
        w = int(round(x1 - x, 2))
        h = int(round(y1 - y, 2))

        # Lets clip the output
        dc.SetClippingRegion(int(x), int(y), int(w), int(h))

        dc.DrawRoundedRectangle(int(x), int(y), int(w), int(h), self.rounded_radius)
        bitmap_width, bitmap_height = bitmap.Size
        font = self.default_font
        # if button.label in  ("Circle", "Ellipse", "Wordlist", "Property Window"):
        #     print (f"N - {button.label}: {bitmap_width}x{bitmap_height} in {w}x{h}")
        if bitmap_height > h or bitmap_width > w:
            button.bitmapsize = "small"
            bitmap = bitmap_small
            font = self.small_font
            bitmap_width, bitmap_height = bitmap.Size
            # if button.label in  ("Circle", "Ellipse", "Wordlist", "Property Window"):
            #     print (f"S - {button.label}: {bitmap_width}x{bitmap_height} in {w}x{h}")
            if bitmap_height > h or bitmap_width > w:
                button.bitmapsize = "tiny"
                bitmap = bitmap_tiny
                font = self.tiny_font
                bitmap_width, bitmap_height = bitmap.Size
                # if button.label in  ("Circle", "Ellipse", "Wordlist", "Property Window"):
                #     print (f"T - {button.label}: {bitmap_width}x{bitmap_height} in {w}x{h}")

        bitmap_width, bitmap_height = bitmap.Size
        dc.DrawBitmap(bitmap, int(x + (w - bitmap_width) / 2), int(y))
        y += bitmap_height

        if button.label and self.show_labels:
            show_text = True
            label_text = list(button.label.split(" "))
            # We try to establish whether this would fit properly.
            # We allow a small oversize of 25% to the button,
            # before we try to reduce the fontsize
            font_candidates = [
                self.default_font,
                self.small_font,
                self.tiny_font,
            ]
            if button.bitmapsize == "tiny":
                font_candidates = font_candidates[2:]
            elif button.bitmapsize == "small":
                font_candidates = font_candidates[1:]
            wouldfit = False
            for testfont in font_candidates:
                test_y = y + self.bitmap_text_buffer
                dc.SetFont(testfont)
                wouldfit = True
                for word in label_text:
                    text_width, text_height = dc.GetTextExtent(word)
                    if text_width > w:
                        wouldfit = False
                        break
                if wouldfit:
                    font = testfont
                    break
            if not wouldfit:
                show_text = False
                label_text = list()

            # Previous algorithm with abbreviated text
            # test_y = y + self.bitmap_text_buffer
            # dc.SetFont(font)
            # for idx, word in enumerate(label_text):
            #     test_word = word
            #     while True:
            #         text_width, text_height = dc.GetTextExtent(test_word)
            #         if text_width <= w:
            #             break
            #         if test_word.endswith("..."):
            #             test_word = test_word[:-4]
            #         else:
            #             test_word = word[:-2]
            #         if len(test_word) > 0:
            #             test_word += "..."
            #         else:
            #             show_text = False
            #             break
            #     if len(test_word) > 0:
            #         if test_word.endswith("..."):
            #             label_text[idx] = test_word
            #             label_text = label_text[: idx + 1]
            #             break
            #     else:
            #         if idx == 0:
            #             show_text = False
            #         else:
            #             label_text = label_text[:idx]

            #         break

            #     test_y += text_height

        else:
            show_text = False
            label_text = list()
        if show_text:
            y += self.bitmap_text_buffer
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
        dc.DestroyClippingRegion()

    def layout(self, dc: wx.DC, button):
        w, h = dc.GetSize()
        button.button.position = 0, 0, w, h
        self.button_layout(dc, self.parent.button)

    def button_layout(self, dc: wx.DC, button):
        x, y, max_x, max_y = button.position
        if button.bitmapsize == "small":
            bitmap = button.bitmap_small
        elif button.bitmapsize == "tiny":
            bitmap = button.bitmap_tiny
        else:
            bitmap = button.bitmap_large
        bitmap_width, bitmap_height = bitmap.Size
        if button.kind == "hybrid" and button.key != "toggle":
            # Calculate text height/width
            # Calculate dropdown
            # Same size regardless of bitmap-size
            sizx = 15
            sizy = 15
            # Let's see whether we have enough room
            extx = (x + max_x) / 2 + bitmap_width / 2 + sizx - 1
            exty = y + bitmap_height + sizy - 1
            extx = max(x - sizx, min(extx, max_x - 1))
            exty = max(y + sizy, min(exty, max_y - 1))
            gap = 5
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
