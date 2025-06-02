"""
Mixin functions for wxMeerk40t
"""

import platform
from typing import List

import wx
import wx.lib.mixins.listctrl as listmix
from wx.lib.scrolledpanel import ScrolledPanel as SP

from meerk40t.core.units import ACCEPTED_ANGLE_UNITS, ACCEPTED_UNITS, Angle, Length
from meerk40t.svgelements import Matrix

_ = wx.GetTranslation


##############
# DYNAMIC CHOICE
# NODE MENU
##############


def get_matrix_scale(matrix):
    # We usually use the value_scale_x to establish a pixel size
    # by counteracting the scene matrix, linewidth = 1 / matrix.value_scale_x()
    # For a rotated scene this crashes, so we need to take
    # that into consideration, so let's look at the
    # distance from (1, 0) to (0, 0) and call this our scale
    from math import sqrt

    x0, y0 = matrix.point_in_matrix_space((0, 0))
    x1, y1 = matrix.point_in_matrix_space((1, 0))
    res = sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
    if res < 1e-8:
        res = 1
    return res


def get_matrix_full_scale(matrix):
    # We usually use the value_scale_x to establish a pixel size
    # by counteracting the scene matrix, linewidth = 1 / matrix.value_scale_x()
    # For a rotated scene this crashes, so we need to take
    # that into consideration, so let's look at the
    # distance from (1, 0) to (0, 0) and call this our scale
    from math import sqrt

    x0, y0 = matrix.point_in_matrix_space((0, 0))
    x1, y1 = matrix.point_in_matrix_space((1, 0))
    resx = sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
    if resx < 1e-8:
        resx = 1
    x1, y1 = matrix.point_in_matrix_space((0, 1))
    resy = sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
    if resy < 1e-8:
        resy = 1
    return resx, resy


def get_gc_scale(gc):
    gcmat = gc.GetTransform()
    mat_param = gcmat.Get()
    testmatrix = Matrix(
        mat_param[0],
        mat_param[1],
        mat_param[2],
        mat_param[3],
        mat_param[4],
        mat_param[5],
    )
    return get_matrix_scale(testmatrix)


def get_gc_full_scale(gc):
    gcmat = gc.GetTransform()
    mat_param = gcmat.Get()
    testmatrix = Matrix(
        mat_param[0],
        mat_param[1],
        mat_param[2],
        mat_param[3],
        mat_param[4],
        mat_param[5],
    )
    return get_matrix_full_scale(testmatrix)


def create_menu_for_choices(gui, choices: List[dict]) -> wx.Menu:
    """
    Creates a menu for a given choices table.

    Processes submenus, references, radio_state as needed.
    """
    menu = wx.Menu()
    submenus = {}
    choice = dict()

    def get(key, default=None):
        try:
            return choice[key]
        except KeyError:
            return default

    def execute(choice):
        func = choice["action"]
        func_kwargs = choice["kwargs"]
        func_args = choice["kwargs"]

        def specific(event=None):
            func(*func_args, **func_kwargs)

        return specific

    def set_bool(choice, value):
        obj = choice["object"]
        param = choice["attr"]

        def check(event=None):
            setattr(obj, param, value)

        return check

    for c in choices:
        choice = c
        submenu_name = get("submenu")
        submenu = None
        if submenu_name and submenu_name in submenus:
            submenu = submenus[submenu_name]
        else:
            if get("separate_before", default=False):
                menu.AppendSeparator()
                c["separate_before"] = False
            if submenu_name:
                submenu = wx.Menu()
                menu.AppendSubMenu(submenu, submenu_name)
                submenus[submenu_name] = submenu

        menu_context = submenu if submenu is not None else menu
        if get("separate_before", default=False):
            menu.AppendSeparator()
            c["separate_before"] = False
        t = get("type")
        if t == bool:
            item = menu_context.Append(
                wx.ID_ANY, get("label"), get("tip"), wx.ITEM_CHECK
            )
            obj = get("object")
            param = get("attr")
            check = bool(getattr(obj, param, False))
            item.Check(check)
            gui.Bind(
                wx.EVT_MENU,
                set_bool(choice, not check),
                item,
            )
        elif t == "action":
            item = menu_context.Append(
                wx.ID_ANY, get("label"), get("tip"), wx.ITEM_NORMAL
            )
            gui.Bind(
                wx.EVT_MENU,
                execute(choice),
                item,
            )
        if not submenu and get("separate_after", default=False):
            menu.AppendSeparator()
    return menu


def create_choices_for_node(node, elements) -> List[dict]:
    """
    Converts a node tree operation menu to a choices dictionary to display the menu items in a choice panel.

    @param node:
    @param elements:
    @return:
    """
    choices = []
    from meerk40t.core.treeop import get_tree_operation_for_node

    tree_operations_for_node = get_tree_operation_for_node(elements)
    for func in tree_operations_for_node(node):
        choice = {}
        choices.append(choice)
        choice["action"] = func
        choice["type"] = "action"
        choice["submenu"] = func.submenu
        choice["kwargs"] = dict()
        choice["args"] = tuple()
        choice["separate_before"] = func.separate_before
        choice["separate_after"] = func.separate_after
        choice["label"] = func.name
        choice["real_name"] = func.real_name
        choice["tip"] = func.help
        choice["radio"] = func.radio
        choice["reference"] = func.reference
        choice["user_prompt"] = func.user_prompt
        choice["calcs"] = func.calcs
        choice["values"] = func.values
    return choices


def create_menu_for_node_TEST(gui, node, elements) -> wx.Menu:
    """
    Test code towards unifying choices and tree nodes into choices that parse to menus.

    This is unused experimental code. Testing the potential interrelationships between choices for the choice panels
    and dynamic node menus.

    @param gui:
    @param node:
    @param elements:
    @return:
    """
    choices = create_choices_for_node(node, elements)
    return create_menu_for_choices(gui, choices)


##############
# DYNAMIC NODE MENU
##############


def create_menu_for_node(gui, node, elements, optional_2nd_node=None) -> wx.Menu:
    """
    Create menu for a particular node. Does not invoke the menu.

    Processes submenus, references, radio_state as needed.
    """
    menu = wx.Menu()
    submenus = {}
    radio_check_not_needed = []
    from meerk40t.core.treeop import get_tree_operation_for_node

    tree_operations_for_node = get_tree_operation_for_node(elements)

    def menu_functions(f, node):
        func_dict = dict(f.func_dict)

        def specific(event=None):
            prompts = f.user_prompt
            if len(prompts) > 0:
                with wx.Dialog(
                    None,
                    wx.ID_ANY,
                    _("Parameters"),
                    style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                ) as dlg:
                    gui.context.themes.set_window_colors(dlg)

                    sizer = wx.BoxSizer(wx.VERTICAL)
                    fields = []
                    for prompt in prompts:
                        label = wxStaticText(dlg, wx.ID_ANY, prompt["prompt"])
                        sizer.Add(label, 0, wx.EXPAND, 0)
                        dtype = prompt["type"]
                        if dtype == bool:
                            control = wxCheckBox(dlg, wx.ID_ANY)
                        else:
                            control = TextCtrl(dlg, wx.ID_ANY)
                            control.SetMaxSize(dip_size(dlg, 75, -1))
                        fields.append(control)
                        sizer.Add(control, 0, wx.EXPAND, 0)
                        sizer.AddSpacer(23)
                    b_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    button_OK = wxButton(dlg, wx.ID_OK, _("OK"))
                    button_CANCEL = wxButton(dlg, wx.ID_CANCEL, _("Cancel"))
                    # dlg.SetAffirmativeId(button_OK.GetId())
                    # dlg.SetEscapeId(button_CANCEL.GetId())
                    b_sizer.Add(button_OK, 0, wx.EXPAND, 0)
                    b_sizer.Add(button_CANCEL, 0, wx.EXPAND, 0)
                    sizer.Add(b_sizer, 0, wx.EXPAND, 0)
                    sizer.Fit(dlg)
                    dlg.SetSizer(sizer)
                    dlg.Layout()

                    response = dlg.ShowModal()
                    if response != wx.ID_OK:
                        return
                    for prompt, control in zip(prompts, fields):
                        dtype = prompt["type"]
                        try:
                            value = dtype(control.GetValue())
                        except ValueError:
                            return
                        func_dict[prompt["attr"]] = value
            # for prompt in prompts:
            #     response = elements.kernel.prompt(prompt["type"], prompt["prompt"])
            #     if response is None:
            #         return
            # func_dict[prompt["attr"]] = response
            f(node, **func_dict)

        return specific

    # Check specifically for the optional first (use case: reference nodes)
    if optional_2nd_node is not None:
        mc1 = menu.MenuItemCount
        last_was_separator = False

        for func in tree_operations_for_node(optional_2nd_node):
            submenu_name = func.submenu
            submenu = None
            if submenu_name and submenu_name in submenus:
                submenu = submenus[submenu_name]
            else:
                if submenu_name:
                    last_was_separator = False
                    subs = submenu_name.split("|")
                    common = ""
                    parent_menu = menu
                    for sname in subs:
                        if sname == "":
                            continue
                        if common:
                            common += "|"
                        common += sname
                        if common in submenus:
                            submenu = submenus[common]
                            parent_menu = submenu
                        else:
                            submenu = wx.Menu()
                            if func.separate_before:
                                last_was_separator = True
                                parent_menu.AppendSeparator()
                                func.separate_before = False

                            parent_menu.AppendSubMenu(submenu, sname, func.help)
                            submenus[common] = submenu
                            parent_menu = submenu

            menu_context = submenu if submenu is not None else menu
            if func.separate_before:
                menu_context.AppendSeparator()
            if func.reference is not None:
                menu_context.AppendSubMenu(
                    create_menu_for_node(
                        gui,
                        func.reference(optional_2nd_node),
                        elements,
                        optional_2nd_node,
                    ),
                    func.real_name,
                )
                continue
            if func.radio_state is not None:
                last_was_separator = False
                item = menu_context.Append(
                    wx.ID_ANY, func.real_name, func.help, wx.ITEM_RADIO
                )
                check = func.radio_state
                item.Check(check)
                if check and menu_context not in radio_check_not_needed:
                    radio_check_not_needed.append(menu_context)
                if func.enabled:
                    gui.Bind(
                        wx.EVT_MENU,
                        menu_functions(func, optional_2nd_node),
                        item,
                    )
                else:
                    item.Enable(False)
            else:
                last_was_separator = False
                if hasattr(func, "check_state") and func.check_state is not None:
                    check = func.check_state
                    kind = wx.ITEM_CHECK
                else:
                    kind = wx.ITEM_NORMAL
                    check = None
                item = menu_context.Append(wx.ID_ANY, func.real_name, func.help, kind)
                if check is not None:
                    item.Check(check)
                if func.enabled:
                    gui.Bind(
                        wx.EVT_MENU,
                        menu_functions(func, node),
                        item,
                    )
                else:
                    item.Enable(False)
                if menu_context not in radio_check_not_needed:
                    radio_check_not_needed.append(menu_context)
            if not submenu and func.separate_after:
                last_was_separator = True
                menu.AppendSeparator()
        mc2 = menu.MenuItemCount
        if not last_was_separator and mc2 - mc1 > 0:
            menu.AppendSeparator()

    for func in tree_operations_for_node(node):
        submenu_name = func.submenu
        submenu = None
        if submenu_name and submenu_name in submenus:
            submenu = submenus[submenu_name]
        else:
            if submenu_name:
                subs = submenu_name.split("|")
                common = ""
                parent_menu = menu
                for sname in subs:
                    if sname == "":
                        continue
                    if common:
                        common += "|"
                    common += sname
                    if common in submenus:
                        submenu = submenus[common]
                        parent_menu = submenu
                    else:
                        submenu = wx.Menu()
                        if func.separate_before:
                            parent_menu.AppendSeparator()
                            func.separate_before = False
                        parent_menu.AppendSubMenu(submenu, sname, func.help)
                        submenus[common] = submenu
                        parent_menu = submenu

        menu_context = submenu if submenu is not None else menu
        if func.separate_before:
            menu_context.AppendSeparator()
            func.separate_before = False
        if func.reference is not None:
            menu_context.AppendSubMenu(
                create_menu_for_node(gui, func.reference(node), elements),
                func.real_name,
            )
            continue
        if func.radio_state is not None:
            item = menu_context.Append(
                wx.ID_ANY, func.real_name, func.help, wx.ITEM_RADIO
            )
            check = func.radio_state
            item.Check(check)
            if check and menu_context not in radio_check_not_needed:
                radio_check_not_needed.append(menu_context)
            if func.enabled:
                gui.Bind(
                    wx.EVT_MENU,
                    menu_functions(func, node),
                    item,
                )
            else:
                item.Enable(False)
        else:
            if hasattr(func, "check_state") and func.check_state is not None:
                check = func.check_state
                kind = wx.ITEM_CHECK
            else:
                kind = wx.ITEM_NORMAL
                check = None
            item = menu_context.Append(wx.ID_ANY, func.real_name, func.help, kind)
            if check is not None:
                item.Check(check)
            if func.enabled:
                gui.Bind(
                    wx.EVT_MENU,
                    menu_functions(func, node),
                    item,
                )
            else:
                item.Enable(False)

            if menu_context not in radio_check_not_needed:
                radio_check_not_needed.append(menu_context)
        if not submenu and func.separate_after:
            menu.AppendSeparator()
    for submenu in submenus.values():
        plain = True
        for item in submenu.GetMenuItems():
            if not (item.IsSeparator() or item.IsSubMenu() or not item.IsEnabled()):
                plain = False
                break
        if plain and submenu not in radio_check_not_needed:
            radio_check_not_needed.append(submenu)

        if submenu not in radio_check_not_needed:
            item = submenu.Append(
                wx.ID_ANY,
                _("Other value..."),
                _("Value set using properties"),
                wx.ITEM_RADIO,
            )
            item.Check(True)
    return menu


def create_menu(gui, node, elements):
    """
    Create menu items. This is used for both the scene and the tree to create menu items.

    @param gui: Gui used to create menu items.
    @param node: The Node clicked on for the generated menu.
    @param elements: elements service for use with node creation
    @return:
    """
    if node is None:
        return
    # Is it a reference object?
    optional_node = None
    if hasattr(node, "node"):
        optional_node = node
        node = node.node

    menu = create_menu_for_node(gui, node, elements, optional_node)
    if menu.MenuItemCount != 0:
        gui.PopupMenu(menu)
        menu.Destroy()


##############
# GUI CONTROL OVERRIDES
##############
def set_color_according_to_theme(control, background, foreground):
    win = control
    while win is not None:
        if hasattr(win, "context") and hasattr(win.context, "themes"):
            if background:
                col = win.context.themes.get(background)
                if col:
                    control.SetBackgroundColour(col)
            if foreground:
                col = win.context.themes.get(foreground)
                if col:
                    control.SetForegroundColour(col)
            break
        win = win.GetParent()


class TextCtrl(wx.TextCtrl):
    """
    Just to add some of the more common things we need, i.e. smaller default size...

    Allow text boxes of specific types so that we can have consistent options for dealing with them.
    """

    def __init__(
        self,
        parent,
        id=wx.ID_ANY,
        value="",
        pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        style=0,
        validator=wx.DefaultValidator,
        name="",
        check="",
        limited=False,
        nonzero=False,
    ):
        if value is None:
            value = ""
        super().__init__(
            parent,
            id=id,
            value=value,
            pos=pos,
            size=size,
            style=style,
            validator=validator,
            name=name,
        )
        self.parent = parent
        self.extend_default_units_if_empty = True
        self._check = check
        self._style = style
        self._nonzero = nonzero
        if self._nonzero is None:
            self._nonzero = False
        # For the sake of readability we allow multiple occurrences of
        # the same character in the string even if it's unnecessary...
        floatstr = "+-.eE0123456789"
        unitstr = "".join(ACCEPTED_UNITS)
        anglestr = "".join(ACCEPTED_ANGLE_UNITS)
        self.charpattern = ""
        if self._check == "length":
            self.charpattern = floatstr + unitstr
        elif self._check == "percent":
            self.charpattern = floatstr + r"%"
        elif self._check == "float":
            self.charpattern = floatstr
        elif self._check == "angle":
            self.charpattern = floatstr + anglestr
        elif self._check == "int":
            self.charpattern = r"-+0123456789"
        self.lower_limit = None
        self.upper_limit = None
        self.lower_limit_err = None
        self.upper_limit_err = None
        self.lower_limit_warn = None
        self.upper_limit_warn = None
        self._default_color_background = self.GetBackgroundColour()
        self._error_color_background = wx.RED
        self._warn_color_background = wx.YELLOW
        self._modify_color_background = self._default_color_background

        self._default_color_foreground = self.GetForegroundColour()
        self._error_color_foreground = self._default_color_foreground
        self._warn_color_foreground = wx.BLACK
        self._modify_color_foreground = self._default_color_foreground
        self._warn_status = "modified"

        self._last_valid_value = None
        self._event_generated = None
        self._action_routine = None
        self._default_values = None

        # You can set this to False, if you don't want logic to interfere with text input
        self.execute_action_on_change = True

        if self._check is not None and self._check != "":
            self.Bind(wx.EVT_KEY_DOWN, self.on_char)
            self.Bind(wx.EVT_KEY_UP, self.on_check)
        self.Bind(wx.EVT_SET_FOCUS, self.on_enter_field)
        self.Bind(wx.EVT_KILL_FOCUS, self.on_leave_field)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_click)
        if self._style & wx.TE_PROCESS_ENTER != 0:
            self.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
        _MIN_WIDTH, _MAX_WIDTH = self.validate_widths()
        self.SetMinSize(dip_size(self, _MIN_WIDTH, -1))
        if limited:
            self.SetMaxSize(dip_size(self, _MAX_WIDTH, -1))
        set_color_according_to_theme(self, "text_bg", "text_fg")

    def validate_widths(self):
        minpattern = "0000"
        maxpattern = "999999999.99mm"
        if self._check == "length":
            minpattern = "0000"
            maxpattern = "999999999.99mm"
        elif self._check == "percent":
            minpattern = "0000"
            maxpattern = "99.99%"
        elif self._check == "float":
            minpattern = "0000"
            maxpattern = "99999.99"
        elif self._check == "angle":
            minpattern = "0000"
            maxpattern = "9999.99deg"
        elif self._check == "int":
            minpattern = "0000"
            maxpattern = "-999999"
        # Let's be a bit more specific: what is the minimum size of the textcontrol fonts
        # to hold these patterns
        tfont = self.GetFont()
        xsize = 15
        imgBit = wx.Bitmap(xsize, xsize)
        dc = wx.MemoryDC(imgBit)
        dc.SelectObject(imgBit)
        dc.SetFont(tfont)
        f_width, f_height, f_descent, f_external_leading = dc.GetFullTextExtent(
            minpattern
        )
        minw = f_width + 5
        f_width, f_height, f_descent, f_external_leading = dc.GetFullTextExtent(
            maxpattern
        )
        maxw = f_width + 10
        # Now release dc
        dc.SelectObject(wx.NullBitmap)
        return minw, maxw

    def SetActionRoutine(self, action_routine):
        """
        This routine will be called after a lost_focus / text_enter event,
        it's a simple way of dealing with all the
            ctrl.bind(wx.EVT_KILL_FOCUS / wx.EVT_TEXT_ENTER) things
        Yes, you can still have them, but you should call
            ctrl.prevalidate()
        then to ensure the logic to avoid invalid content is been called.
        If you need to programmatically distinguish between a lost focus
        and text_enter event, then consult
            ctrl.event_generated()
        this will give back wx.EVT_KILL_FOCUS or wx.EVT_TEXT_ENTER
        """
        self._action_routine = action_routine

    def event_generated(self):
        """
        This routine will give back wx.EVT_KILL_FOCUS or wx.EVT_TEXT_ENTER
        if called during an execution of the validator routine, see above,
        or None in any other case
        """
        return self._event_generated

    def set_default_values(self, def_values):
        self._default_values = def_values

    def get_warn_status(self, txt):
        status = ""
        try:
            value = None
            if self._check == "float":
                value = float(txt)
            elif self._check == "percent":
                if txt.endswith("%"):
                    value = float(txt[:-1]) / 100.0
                else:
                    value = float(txt)
            elif self._check == "int":
                value = int(txt)
            elif self._check == "empty":
                if len(txt) == 0:
                    status = "error"
            elif self._check == "length":
                value = Length(txt)
            elif self._check == "angle":
                value = Angle(txt)
            # we passed so far, thus the values are syntactically correct
            # Now check for content compliance
            if value is not None:
                if self.lower_limit is not None and value < self.lower_limit:
                    value = self.lower_limit
                    self.SetValue(str(value))
                    status = "default"
                if self.upper_limit is not None and value > self.upper_limit:
                    value = self.upper_limit
                    self.SetValue(str(value))
                    status = "default"
                if self.lower_limit_warn is not None and value < self.lower_limit_warn:
                    status = "warning"
                if self.upper_limit_warn is not None and value > self.upper_limit_warn:
                    status = "warning"
                if self.lower_limit_err is not None and value < self.lower_limit_err:
                    status = "error"
                if self.upper_limit_err is not None and value > self.upper_limit_err:
                    status = "error"
                if self._nonzero and value == 0:
                    status = "error"
        except ValueError:
            status = "error"
        return status

    def SetValue(self, newvalue):
        identical = False
        current = super().GetValue()
        if self._check == "float":
            try:
                v1 = float(current)
                v2 = float(newvalue)
                if v1 == v2:
                    identical = True
            except ValueError:
                pass
        if identical:
            # print (f"...ignored {current}={v1}, {newvalue}={v2}")
            return
        # print(f"SetValue called: {current} != {newvalue}")
        self._last_valid_value = newvalue
        status = self.get_warn_status(newvalue)
        self.warn_status = status
        cursor = self.GetInsertionPoint()
        super().SetValue(newvalue)
        cursor = min(len(newvalue), cursor)
        self.SetInsertionPoint(cursor)

    def set_error_level(self, err_min, err_max):
        self.lower_limit_err = err_min
        self.upper_limit_err = err_max

    def set_warn_level(self, warn_min, warn_max):
        self.lower_limit_warn = warn_min
        self.upper_limit_warn = warn_max

    def set_range(self, range_min, range_max):
        self.lower_limit = range_min
        self.upper_limit = range_max

    def prevalidate(self, origin=None):
        # Check whether the field is okay, if not then put it to the last value
        txt = super().GetValue()
        # print (f"prevalidate called from: {origin}, check={self._check}, content:{txt}")
        if self.warn_status == "error" and self._last_valid_value is not None:
            # ChangeValue is not creating any events...
            self.ChangeValue(self._last_valid_value)
            self.warn_status = ""
        elif (
            txt != "" and self._check == "length" and self.extend_default_units_if_empty
        ):
            # Do we have non-existing units provided? --> Change content
            purenumber = True
            unitstr = "".join(ACCEPTED_UNITS)
            for c in unitstr:
                if c in txt:
                    purenumber = False
                    break
            if purenumber and hasattr(self.parent, "context"):
                context = self.parent.context
                root = context.root
                root.setting(str, "units_name", "mm")
                units = root.units_name
                if units in ("inch", "inches"):
                    units = "in"
                txt = txt.strip() + units
                self.ChangeValue(txt)
        elif (
            txt != "" and self._check == "angle" and self.extend_default_units_if_empty
        ):
            # Do we have non-existing units provided? --> Change content
            purenumber = True
            unitstr = "".join(ACCEPTED_ANGLE_UNITS)
            for c in unitstr:
                if c in txt:
                    purenumber = False
                    break
            if purenumber and hasattr(self.parent, "context"):
                context = self.parent.context
                root = context.root
                root.setting(str, "angle_units", "deg")
                units = root.angle_units
                txt = txt.strip() + units
                self.ChangeValue(txt)

    def on_enter_field(self, event):
        self._last_valid_value = super().GetValue()
        event.Skip()

    def on_leave_field(self, event):
        # Needs to be passed on
        event.Skip()
        self.prevalidate("leave")
        if self._action_routine is not None:
            self._event_generated = wx.EVT_KILL_FOCUS
            try:
                self._action_routine()
            finally:
                self._event_generated = None
        self.SelectNone()
        # We assume it's been dealt with, so we recolor...
        self.SetModified(False)
        self.warn_status = self._warn_status

    def on_enter(self, event):
        # Let others deal with it after me
        event.Skip()
        self.prevalidate("enter")
        if self._action_routine is not None:
            self._event_generated = wx.EVT_TEXT_ENTER
            try:
                self._action_routine()
            finally:
                self._event_generated = None
        self.SelectNone()
        # We assume it's been dealt with, so we recolor...
        self.SetModified(False)
        self.warn_status = self._warn_status

    def on_right_click(self, event):
        def set_menu_value(to_be_set):
            def handler(event):
                self.SetValue(to_be_set)
                self.prevalidate("enter")
                if self._action_routine is not None:
                    self._event_generated = wx.EVT_TEXT_ENTER
                    try:
                        self._action_routine()
                    finally:
                        self._event_generated = None

            return handler

        if not self._default_values:
            event.Skip()
            return
        menu = wx.Menu()
        has_info = isinstance(self._default_values[0], (list, tuple))
        item: wx.MenuItem = menu.Append(wx.ID_ANY, _("Default values..."), "")
        item.Enable(False)
        for info in self._default_values:
            item = menu.Append(
                wx.ID_ANY, info[0] if has_info else info, info[1] if has_info else ""
            )
            self.Bind(
                wx.EVT_MENU,
                set_menu_value(info[0] if has_info else info),
                id=item.GetId(),
            )
        self.PopupMenu(menu)
        menu.Destroy()

    @property
    def warn_status(self):
        return self._warn_status

    @warn_status.setter
    def warn_status(self, value):
        self._warn_status = value
        background = self._default_color_background
        foreground = self._default_color_foreground
        if value == "modified":
            # Is it modified?
            if self.IsModified():
                background = self._modify_color_background
                foreground = self._modify_color_foreground
        elif value == "warning":
            background = self._warn_color_background
            foreground = self._warn_color_foreground
        elif value == "error":
            background = self._error_color_background
            foreground = self._error_color_foreground
        self.SetBackgroundColour(background)
        self.SetForegroundColour(foreground)
        self.Refresh()

    def on_char(self, event):
        proceed = True
        # The French azerty keyboard generates numbers by pressing Shift + some key
        # Under Linux this is not properly translated by GetUnicodeKey and
        # is hence leading to a 'wrong' character being recognised (the original key).
        # So we can't rely on a proper representation if the Shift-Key
        # is held down, sigh.
        if self.charpattern != "" and not event.ShiftDown():
            keyc = event.GetUnicodeKey()
            special = False
            if event.RawControlDown() or event.ControlDown() or event.AltDown():
                # GetUnicodeKey ignores all special keys, so we need to acknowledge that
                special = True
            if keyc == 127:  # delete
                special = True
            if keyc != wx.WXK_NONE and not special:
                # a 'real' character?
                if keyc >= ord(" "):
                    char = chr(keyc).lower()
                    if char not in self.charpattern:
                        proceed = False
                        # print(f"Ignored: {keyc} - {char}")
        if proceed:
            event.DoAllowNextEvent()
            event.Skip()

    def on_check(self, event):
        event.Skip()
        txt = super().GetValue()
        status = self.get_warn_status(txt)
        if status == "":
            status = "modified"
        self.warn_status = status
        # Is it a valid value?
        lenokay = True
        if len(txt) == 0 and self._check in (
            "float",
            "length",
            "angle",
            "int",
            "percent",
        ):
            lenokay = False
        if (
            self.execute_action_on_change
            and status == "modified"
            and hasattr(self.parent, "context")
            and lenokay
        ):
            if getattr(self.parent.context.root, "process_while_typing", False):
                if self._action_routine is not None:
                    self._event_generated = wx.EVT_TEXT
                    try:
                        self._action_routine()
                    finally:
                        self._event_generated = None

    @property
    def is_changed(self):
        return self.GetValue() != self._last_valid_value

    @property
    def Value(self):
        return self.GetValue()

    def GetValue(self):
        result = super().GetValue()
        if (
            result != ""
            and self._check == "length"
            and self.extend_default_units_if_empty
        ):
            purenumber = True
            unitstr = "".join(ACCEPTED_UNITS)
            for c in unitstr:
                if c in result:
                    purenumber = False
                    break
            if purenumber and hasattr(self.parent, "context"):
                context = self.parent.context
                root = context.root
                root.setting(str, "units_name", "mm")
                units = root.units_name
                if units in ("inch", "inches"):
                    units = "in"
                result = result.strip()
                if result.endswith("."):
                    result += "0"
                result += units
        return result


class wxCheckBox(wx.CheckBox):
    """
    This class wraps around  wx.CheckBox and creates a series of mouse over tool tips to permit Linux tooltips that
    otherwise do not show.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self._tool_tip = None
        super().__init__(*args, **kwargs)
        if platform.system() == "Linux":

            def on_mouse_over_check(ctrl):
                def mouse(event=None):
                    ctrl.SetToolTip(self._tool_tip)
                    event.Skip()

                return mouse

            self.Bind(wx.EVT_MOTION, on_mouse_over_check(super()))
        set_color_according_to_theme(self, "text_bg", "text_fg")

    def SetToolTip(self, tooltip):
        self._tool_tip = tooltip
        super().SetToolTip(self._tool_tip)


class wxComboBox(wx.ComboBox):
    """
    This class wraps around wx.ComboBox and creates a series of mouse over tool tips to permit Linux tooltips that
    otherwise do not show.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self._tool_tip = None
        super().__init__(*args, **kwargs)
        if platform.system() == "Linux":

            def on_mouse_over_check(ctrl):
                def mouse(event=None):
                    ctrl.SetToolTip(self._tool_tip)
                    event.Skip()

                return mouse

            self.Bind(wx.EVT_MOTION, on_mouse_over_check(super()))
        set_color_according_to_theme(self, "text_bg", "text_fg")

    def SetToolTip(self, tooltip):
        self._tool_tip = tooltip
        super().SetToolTip(self._tool_tip)


class wxTreeCtrl(wx.TreeCtrl):
    """
    This class wraps around wx.TreeCtrl and creates a series of mouse over tool tips to permit Linux tooltips that
    otherwise do not show.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self._tool_tip = None
        super().__init__(*args, **kwargs)
        if platform.system() == "Linux":

            def on_mouse_over_check(ctrl):
                def mouse(event=None):
                    ctrl.SetToolTip(self._tool_tip)
                    event.Skip()

                return mouse

            self.Bind(wx.EVT_MOTION, on_mouse_over_check(super()))
        set_color_according_to_theme(self, "list_bg", "list_fg")

    def SetToolTip(self, tooltip):
        self._tool_tip = tooltip
        super().SetToolTip(self._tool_tip)


class wxBitmapButton(wx.BitmapButton):
    """
    This class wraps around wx.Button and creates a series of mouse over tool tips to permit Linux tooltips that
    otherwise do not show.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self._tool_tip = None
        super().__init__(*args, **kwargs)
        if platform.system() == "Linux":

            def on_mouse_over_check(ctrl):
                def mouse(event=None):
                    ctrl.SetToolTip(self._tool_tip)
                    event.Skip()

                return mouse

            self.Bind(wx.EVT_MOTION, on_mouse_over_check(super()))
        set_color_according_to_theme(self, "button_bg", "button_fg")

    def SetToolTip(self, tooltip):
        self._tool_tip = tooltip
        super().SetToolTip(self._tool_tip)


class wxButton(wx.Button):
    """
    This class wraps around wx.Button and creates a series of mouse over tool tips to permit Linux tooltips that
    otherwise do not show.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self._tool_tip = None
        super().__init__(*args, **kwargs)
        if platform.system() == "Linux":

            def on_mouse_over_check(ctrl):
                def mouse(event=None):
                    ctrl.SetToolTip(self._tool_tip)
                    event.Skip()

                return mouse

            self.Bind(wx.EVT_MOTION, on_mouse_over_check(super()))
        set_color_according_to_theme(self, "button_bg", "button_fg")

    def SetToolTip(self, tooltip):
        self._tool_tip = tooltip
        super().SetToolTip(self._tool_tip)


class wxToggleButton(wx.ToggleButton):
    """
    This class wraps around wx.ToggleButton and creates a series of mouse over tool tips to permit Linux tooltips that
    otherwise do not show.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self._tool_tip = None
        super().__init__(*args, **kwargs)
        if platform.system() == "Linux":

            def on_mouse_over_check(ctrl):
                def mouse(event=None):
                    ctrl.SetToolTip(self._tool_tip)
                    event.Skip()

                return mouse

            self.Bind(wx.EVT_MOTION, on_mouse_over_check(super()))
        set_color_according_to_theme(self, "button_bg", "button_fg")
        self.bitmap_toggled = None
        self.bitmap_untoggled = None

    def update_button(self, value):
        # We just act as a man in the middle
        if value is None:
            value = self.GetValue()
        if value:
            if self.bitmap_toggled is not None:
                self.SetBitmap(self.bitmap_toggled)
        else:
            if self.bitmap_untoggled is not None:
                self.SetBitmap(self.bitmap_untoggled)

    def SetValue(self, value):
        super().SetValue(value)
        self.update_button(value)

    def SetToolTip(self, tooltip):
        self._tool_tip = tooltip
        super().SetToolTip(self._tool_tip)


class wxStaticBitmap(wx.StaticBitmap):
    """
    This class wraps around wx.StaticBitmap and creates a series of mouse over tool tips to permit Linux tooltips that
    otherwise do not show.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self._tool_tip = None
        super().__init__(*args, **kwargs)
        if platform.system() == "Linux":

            def on_mouse_over_check(ctrl):
                def mouse(event=None):
                    ctrl.SetToolTip(self._tool_tip)
                    event.Skip()

                return mouse

            self.Bind(wx.EVT_MOTION, on_mouse_over_check(super()))
        set_color_according_to_theme(self, "button_bg", "button_fg")

    def SetToolTip(self, tooltip):
        self._tool_tip = tooltip
        super().SetToolTip(self._tool_tip)


class StaticBoxSizer(wx.StaticBoxSizer):
    def __init__(
        self,
        parent,
        id=wx.ID_ANY,
        label="",
        orientation=wx.HORIZONTAL,
        *args,
        **kwargs,
    ):
        if label is None:
            label = ""
        self.sbox = wx.StaticBox(parent, id, label=label)
        self.sbox.SetMinSize(dip_size(self.sbox, 50, 50))
        super().__init__(self.sbox, orientation)
        self.parent = parent

    @property
    def Id(self):
        return self.sbox.Id

    def GetId(self):
        return self.Id

    def Show(self, show=True):
        self.sbox.Show(show)

    def SetLabel(self, label):
        self.sbox.SetLabel(label)

    def GetLabel(self):
        return self.sbox.GetLabel()

    def Refresh(self, *args):
        self.sbox.Refresh(*args)

    def Enable(self, enable: bool = True):
        """Enable or disable the StaticBoxSizer and its children.

        Enables or disables all children of the sizer recursively.
        """

        def enem(wind, flag):
            for c in wind.GetChildren():
                enem(c, flag)
            if hasattr(wind, "Enable"):
                wind.Enable(flag)

        enem(self.sbox, enable)


class ScrolledPanel(SP):
    """
    We sometimes delete things fast enough that they call _SetupAfter when dead and crash.
    """

    def _SetupAfter(self, scrollToTop):
        try:
            self.SetVirtualSize(self.GetBestVirtualSize())
            if scrollToTop:
                self.Scroll(0, 0)
        except RuntimeError:
            pass


class wxListCtrl(wx.ListCtrl):
    """
    wxListCtrl will extend a regular ListCtrl by saving / restoring column widths
    """

    def __init__(
        self,
        parent,
        ID=wx.ID_ANY,
        pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        style=0,
        context=None,
        list_name=None,
    ):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        self.context = context
        self.list_name = list_name
        # The resize event is never triggered, so tap into the parent...
        # parent.Bind(wx.EVT_SIZE, self.proxy_resize_event, self)
        parent.Bind(wx.EVT_SIZE, self.proxy_resize_event, parent)
        parent.Bind(wx.EVT_LIST_COL_END_DRAG, self.proxy_col_resized, self)
        set_color_according_to_theme(self, "list_bg", "list_fg")

    def save_column_widths(self):
        if self.context is None or self.list_name is None:
            return
        try:
            sizes = list()
            for col in range(self.GetColumnCount()):
                sizes.append(self.GetColumnWidth(col))
            self.context.setting(tuple, self.list_name, None)
            setattr(self.context, self.list_name, sizes)
        except RuntimeError:
            # Could happen if the control is already destroyed
            return

    def load_column_widths(self):
        if self.context is None or self.list_name is None:
            return
        sizes = self.context.setting(tuple, self.list_name, None)
        if sizes is None:
            return
        # print(f"Found for {self.list_name}: {sizes}")
        available = self.GetColumnCount()
        for idx, width in enumerate(sizes):
            if idx >= available:
                break
            self.SetColumnWidth(idx, width)

    def resize_columns(self):
        self.load_column_widths()
        # we could at least try to make use of the available space
        dummy = self.adjust_last_column()

    def proxy_col_resized(self, event):
        # We are not touching the event object to allow other routines to tap into it
        event.Skip()
        # print (f"col resized called from {self.GetId()} - {self.list_name}")
        dummy = self.adjust_last_column()
        self.save_column_widths()

    def adjust_last_column(self, size_to_use=None):
        # gap is the amount of pixels to be reserved to allow for a vertical scrollbar
        gap = 30
        size = size_to_use
        if size is None:
            size = self.GetSize()
        list_width = size[0]
        total = gap
        last = 0
        for col in range(self.GetColumnCount()):
            try:
                last = self.GetColumnWidth(col)
                total += last
            except Exception as e:
                # print(f"Strange, crashed for column {col} of {self.GetColumnCount()}: {e}")
                return False
        # print(f"{self.list_name}, cols={self.GetColumnCount()}, available={list_width}, used={total}")
        if total < list_width:
            col = self.GetColumnCount() - 1
            if col < 0:
                return False
            # print(f"Will adjust last column from {last} to {last + (list_width - total)}")
            try:
                self.SetColumnWidth(col, last + (list_width - total))
            except Exception as e:
                # print(f"Something strange happened while resizing the last columns for {self.list_name}: {e}")
                return False
            return True
        return False

    def proxy_resize_event(self, event):
        # We are not touching the event object to allow other routines to tap into it
        event.Skip()
        # print (f"Resize called from {self.GetId()} - {self.list_name}: {event.Size}")
        if self.adjust_last_column(event.Size):
            self.save_column_widths()


class EditableListCtrl(wxListCtrl, listmix.TextEditMixin):
    """TextEditMixin allows any column to be edited."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        parent,
        ID=wx.ID_ANY,
        pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        style=0,
        context=None,
        list_name=None,
    ):
        """Constructor"""
        wxListCtrl.__init__(
            self,
            parent=parent,
            ID=ID,
            pos=pos,
            size=size,
            style=style,
            context=context,
            list_name=list_name,
        )
        listmix.TextEditMixin.__init__(self)
        set_color_according_to_theme(self, "list_bg", "list_fg")


class HoverButton(wxButton):
    """
    Provide a button with Hover-Color changing ability.
    """

    def __init__(self, parent, ID, label):
        super().__init__(parent, ID, label)
        self._focus_color = None
        self._disable_color = None
        self._foreground_color = self.GetForegroundColour()
        self._background_color = self.GetBackgroundColour()
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        # self.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse)
        set_color_according_to_theme(self, "list_bg", "list_fg")

    def SetFocusColour(self, color):
        self._focus_color = wx.Colour(color)

    def SetDisabledBackgroundColour(self, color):
        self._disable_color = wx.Colour(color)

    def SetForegroundColour(self, color):
        self._foreground_color = wx.Colour(color)
        super().SetForegroundColour(color)

    def SetBackgroundColour(self, color):
        self._background_color = wx.Colour(color)
        super().SetBackgroundColour(color)

    def GetFocusColour(self, color):
        return self._focus_color

    def Enable(self, value):
        if value:
            super().SetBackgroundColour(self._background_color)
        else:
            if self._disable_color is None:
                r, g, b, a = self._background_color.Get()
                color = wx.Colour(
                    min(255, int(1.5 * r)),
                    min(255, int(1.5 * g)),
                    min(255, int(1.5 * b)),
                )
            else:
                color = self._disable_color
            super().SetBackgroundColour(color)
        super().Enable(value)
        self.Refresh()

    def on_enter(self, event):
        if self._focus_color is not None:
            super().SetForegroundColour(self._focus_color)
            self.Refresh()
        event.Skip()

    def on_leave(self, event):
        super().SetForegroundColour(self._foreground_color)
        self.Refresh()
        event.Skip()

    # def on_mouse(self, event):
    #     if event.Leaving():
    #         self.on_leave(event)
    #     event.Skip()


class wxRadioBox(StaticBoxSizer):
    """
    This class recreates the functionality of a wx.RadioBox, as this class does not recognize / honor parent color values, so a manual darkmode logic fails
    """

    def __init__(
        self,
        parent=None,
        id=None,
        label=None,
        choices=None,
        majorDimension=0,
        style=0,
        *args,
        **kwargs,
    ):
        self.parent = parent
        self.choices = choices
        self._children = []
        self._labels = []
        self._tool_tip = None
        self._help = None
        super().__init__(
            parent=parent, id=wx.ID_ANY, label=label, orientation=wx.VERTICAL
        )
        if majorDimension == 0 or style == wx.RA_SPECIFY_ROWS:
            majorDimension = 1000
        container = None
        for idx, c in enumerate(self.choices):
            if idx % majorDimension == 0:
                container = wx.BoxSizer(wx.HORIZONTAL)
                self.Add(container, 0, wx.EXPAND, 0)
            st = 0
            if idx == 0:
                st = wx.RB_GROUP

            radio_option = wx.RadioButton(parent, wx.ID_ANY, label=c, style=st)
            container.Add(radio_option, 1, wx.ALIGN_CENTER_VERTICAL, 0)
            self._children.append(radio_option)

        if platform.system() == "Linux":

            def on_mouse_over_check(ctrl):
                def mouse(event=None):
                    ctrl.SetToolTip(self._tool_tip)
                    event.Skip()

                return mouse

            for ctrl in self._children:
                ctrl.Bind(wx.EVT_MOTION, on_mouse_over_check(ctrl))

        for ctrl in self._children:
            ctrl.Bind(wx.EVT_RADIOBUTTON, self.on_radio)

        for ctrl in self._children + self._labels:
            set_color_according_to_theme(ctrl, "text_bg", "text_fg")

    @property
    def Children(self):
        return self._children

    def GetParent(self):
        return self.parent

    def SetToolTip(self, tooltip):
        self._tool_tip = tooltip
        for ctrl in self._children:
            ctrl.SetToolTip(self._tool_tip)

    def Select(self, n):
        self.SetSelection(n)

    def SetSelection(self, n):
        for idx, ctrl in enumerate(self._children):
            ctrl.SetValue(idx == n)

    def GetSelection(self):
        for idx, ctrl in enumerate(self._children):
            if ctrl.GetValue():
                return idx
        return -1

    def GetStringSelection(self):
        idx = self.GetSelection()
        return None if idx < 0 else self.choices[idx]

    def Disable(self):
        self.Enable(False)

    def EnableItem(self, n, flag):
        if 0 <= n < len(self._children):
            self._children[n].Enable(flag)

    def Enable(self, flag):
        for ctrl in self._children:
            ctrl.Enable(flag)

    def Hide(self):
        self.Show(False)

    def Show(self, flag):
        for ctrl in self._children + self._labels:
            ctrl.Show(flag)
        super().Show(flag)

    def Bind(self, event_type, routine):
        self.parent.Bind(event_type, routine, self)

    def on_radio(self, orgevent):
        #
        event = orgevent.Clone()
        event.SetEventType(wx.wxEVT_RADIOBOX)
        event.SetId(self.Id)
        event.SetEventObject(self)
        event.Int = self.GetSelection()
        wx.PostEvent(self.parent, event)

    def SetForegroundColour(self, wc):
        for ctrl in self._children + self._labels:
            ctrl.SetForegroundColour(wc)

    def SetBackgroundColour(self, wc):
        for ctrl in self._children + self._labels:
            ctrl.SetBackgroundColour(wc)

    def SetHelpText(self, help):
        self._help = help

    def GetHelpText(self):
        return self._help


class wxStaticText(wx.StaticText):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_color_according_to_theme(self, "label_bg", "label_fg")


class wxListBox(wx.ListBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_color_according_to_theme(self, "list_bg", "list_fg")


class wxCheckListBox(StaticBoxSizer):
    """
    This class recreates the functionality of a wx.CheckListBox, as this class has issues to properly refresh in nested sizers

    Known Limitations:
    - This custom implementation may not fully replicate all native wx.CheckListBox behaviors.
    - Keyboard navigation (e.g., arrow keys, space/enter to toggle) may not work as expected.
    - Accessibility features such as screen reader support may be limited or unavailable.
    - If your application requires full accessibility or native keyboard handling, consider using the native wx.CheckListBox where possible.
    """

    def __init__(
        self,
        parent=None,
        id=None,
        label=None,
        choices=None,
        majorDimension=0,
        style=0,
        *args,
        **kwargs,
    ):
        self.parent = parent
        self.choices = choices
        self._children = []
        self._tool_tip = None
        self._help = None
        super().__init__(
            parent=parent, id=wx.ID_ANY, label=label, orientation=wx.VERTICAL
        )
        self.majorDimension = majorDimension
        self.style = style
        self._build_controls()

    def _build_controls(self):
        """
        Build the controls for the CheckListBox.
        This method is called during initialization to create the checkboxes.
        """
        if self.choices is None:
            self.choices = []
        if self.majorDimension == 0 or self.style == wx.RA_SPECIFY_ROWS:
            self.majorDimension = 1000
        container = None
        for idx, c in enumerate(self.choices):
            if idx % self.majorDimension == 0:
                container = wx.BoxSizer(wx.HORIZONTAL)
                self.Add(container, 0, wx.EXPAND, 0)
            check_option = wx.CheckBox(self.parent, wx.ID_ANY, label=c)
            container.Add(check_option, 1, wx.ALIGN_CENTER_VERTICAL, 0)
            self._children.append(check_option)

        if platform.system() == "Linux":

            def on_mouse_over_check(ctrl):
                def mouse(event=None):
                    ctrl.SetToolTip(self._tool_tip)
                    event.Skip()

                return mouse

            for ctrl in self._children:
                ctrl.Bind(wx.EVT_MOTION, on_mouse_over_check(ctrl))

        for ctrl in self._children:
            ctrl.Bind(wx.EVT_CHECKBOX, self.on_check)
            ctrl.Bind(wx.EVT_RIGHT_DOWN, self.on_right_click)

        for ctrl in self._children:
            set_color_according_to_theme(ctrl, "text_bg", "text_fg")

    @property
    def Children(self):
        return self._children

    def GetParent(self):
        return self.parent

    def SetToolTip(self, tooltip):
        self._tool_tip = tooltip
        for ctrl in self._children:
            ctrl.SetToolTip(self._tool_tip)

    def Disable(self):
        self.Enable(False)

    def EnableItem(self, n, flag):
        if 0 <= n < len(self._children):
            self._children[n].Enable(flag)

    def Enable(self, flag):
        for ctrl in self._children:
            ctrl.Enable(flag)

    def Hide(self):
        self.Show(False)

    def Show(self, flag):
        for ctrl in self._children:
            ctrl.Show(flag)
        self.ShowItems(flag)

    # def Bind(self, event_type, routine):
    #     self.parent.Bind(event_type, routine, self)

    def on_check(self, orgevent):
        #
        event = orgevent.Clone()
        event.SetEventType(wx.wxEVT_CHECKLISTBOX)
        event.SetId(self.Id)
        event.SetEventObject(self)
        # event.Int = self.GetSelection()
        wx.PostEvent(self.parent, event)

    def on_right_click(self, event):
        menu = wx.Menu()
        parent = self.parent
        item = menu.Append(wx.ID_ANY, _("Check all"), "")
        parent.Bind(
            wx.EVT_MENU,
            lambda e: self.SetCheckedItems(range(len(self._children))),
            id=item.GetId(),
        )
        item = menu.Append(wx.ID_ANY, _("Uncheck all"), "")
        parent.Bind(wx.EVT_MENU, lambda e: self.SetCheckedItems([]), id=item.GetId())
        item = menu.Append(wx.ID_ANY, _("Invert selection"), "")
        parent.Bind(
            wx.EVT_MENU,
            lambda e: self.SetCheckedItems(
                [
                    i
                    for i in range(len(self._children))
                    if not self._children[i].GetValue()
                ]
            ),
            id=item.GetId(),
        )
        parent.PopupMenu(menu)
        menu.Destroy()

    def SetForegroundColour(self, wc):
        for ctrl in self._children:
            ctrl.SetForegroundColour(wc)

    def SetBackgroundColour(self, wc):
        for ctrl in self._children:
            ctrl.SetBackgroundColour(wc)

    def SetHelpText(self, help):
        self._help = help

    def GetHelpText(self):
        return self._help

    def Clear(self) -> None:
        with wx.BusyCursor():
            for child in self._children:
                child.Destroy()
        self._children.clear()
        self.choices.clear()

    def Check(self, item: int, check: bool = True) -> None:
        """
        Check or uncheck an item in the CheckListBox.
        :param item: The index of the item to check or uncheck.
        :param check: True to check, False to uncheck.
        """
        if 0 <= item < len(self._children):
            self._children[item].SetValue(check)

    def GetCheckItems(self) -> list:
        """
        Get a list of indices of checked items in the CheckListBox.
        :return: A list of indices of checked items.
        """
        return [idx for idx, ctrl in enumerate(self._children) if ctrl.GetValue()]

    def GetCheckedStrings(self) -> list:
        """
        Get a list of strings of checked items in the CheckListBox.
        :return: A list of strings of checked items.
        """
        return [self.choices[idx] for idx in self.GetCheckItems()]

    def GetSelections(self) -> list:
        """
        Get a list of indices of selected items in the CheckListBox.
        :return: A list of indices of selected items.
        """
        return self.GetCheckItems()

    def SetCheckedStrings(self, choices):
        """
        Set the checked items in the CheckListBox based on a list of strings.
        :param choices: A list of strings to check.
        """
        for idx, choice in enumerate(self.choices):
            if choice in choices:
                self.Check(idx, True)
            else:
                self.Check(idx, False)

    def SetCheckedItems(self, choices):
        """
        Set the checked items in the CheckListBox based on a list of indices.
        :param choices: A list of indices to check.
        """
        for idx in range(len(self._children)):
            self.Check(idx, idx in choices)

    def Set(self, choices):
        """
        Set the choices for the CheckListBox.
        :param choices: A list of strings to set as choices.
        """
        # print (f"Setting choices for {self.GetLabel()}: {choices}")
        self.Clear()
        self.choices = list(choices)
        self._build_controls()


##############
# GUI KEYSTROKE FUNCTIONS
##############

WX_METAKEYS = [
    wx.WXK_START,
    wx.WXK_WINDOWS_LEFT,
    wx.WXK_WINDOWS_RIGHT,
]

WX_MODIFIERS = {
    wx.WXK_CONTROL: "ctrl",
    wx.WXK_RAW_CONTROL: "macctl",
    wx.WXK_ALT: "alt",
    wx.WXK_SHIFT: "shift",
    wx.WXK_START: "start",
    wx.WXK_WINDOWS_LEFT: "win-left",
    wx.WXK_WINDOWS_RIGHT: "win-right",
}

WX_SPECIALKEYS = {
    wx.WXK_F1: "f1",
    wx.WXK_F2: "f2",
    wx.WXK_F3: "f3",
    wx.WXK_F4: "f4",
    wx.WXK_F5: "f5",
    wx.WXK_F6: "f6",
    wx.WXK_F7: "f7",
    wx.WXK_F8: "f8",
    wx.WXK_F9: "f9",
    wx.WXK_F10: "f10",
    wx.WXK_F11: "f11",
    wx.WXK_F12: "f12",
    wx.WXK_F13: "f13",
    wx.WXK_F14: "f14",
    wx.WXK_F15: "f15",
    wx.WXK_F16: "f16",
    wx.WXK_F17: "f17",
    wx.WXK_F18: "f18",
    wx.WXK_F19: "f19",
    wx.WXK_F20: "f20",
    wx.WXK_F21: "f21",
    wx.WXK_F22: "f22",
    wx.WXK_F23: "f23",
    wx.WXK_F24: "f24",
    wx.WXK_ADD: "+",
    wx.WXK_END: "end",
    wx.WXK_NUMPAD0: "numpad0",
    wx.WXK_NUMPAD1: "numpad1",
    wx.WXK_NUMPAD2: "numpad2",
    wx.WXK_NUMPAD3: "numpad3",
    wx.WXK_NUMPAD4: "numpad4",
    wx.WXK_NUMPAD5: "numpad5",
    wx.WXK_NUMPAD6: "numpad6",
    wx.WXK_NUMPAD7: "numpad7",
    wx.WXK_NUMPAD8: "numpad8",
    wx.WXK_NUMPAD9: "numpad9",
    wx.WXK_NUMPAD_ADD: "numpad_add",
    wx.WXK_NUMPAD_SUBTRACT: "numpad_subtract",
    wx.WXK_NUMPAD_MULTIPLY: "numpad_multiply",
    wx.WXK_NUMPAD_DIVIDE: "numpad_divide",
    wx.WXK_NUMPAD_DECIMAL: "numpad.",
    wx.WXK_NUMPAD_ENTER: "numpad_enter",
    wx.WXK_NUMPAD_RIGHT: "numpad_right",
    wx.WXK_NUMPAD_LEFT: "numpad_left",
    wx.WXK_NUMPAD_UP: "numpad_up",
    wx.WXK_NUMPAD_DOWN: "numpad_down",
    wx.WXK_NUMPAD_DELETE: "numpad_delete",
    wx.WXK_NUMPAD_INSERT: "numpad_insert",
    wx.WXK_NUMPAD_PAGEUP: "numpad_pgup",
    wx.WXK_NUMPAD_PAGEDOWN: "numpad_pgdn",
    wx.WXK_NUMPAD_HOME: "numpad_home",
    wx.WXK_NUMPAD_END: "numpad_end",
    wx.WXK_NUMLOCK: "num_lock",
    wx.WXK_SCROLL: "scroll_lock",
    wx.WXK_CAPITAL: "caps_lock",
    wx.WXK_HOME: "home",
    wx.WXK_DOWN: "down",
    wx.WXK_UP: "up",
    wx.WXK_RIGHT: "right",
    wx.WXK_LEFT: "left",
    wx.WXK_ESCAPE: "escape",
    wx.WXK_BACK: "back",
    wx.WXK_PAUSE: "pause",
    wx.WXK_PAGEDOWN: "pagedown",
    wx.WXK_PAGEUP: "pageup",
    wx.WXK_PRINT: "print",
    wx.WXK_RETURN: "return",
    wx.WXK_SPACE: "space",
    wx.WXK_TAB: "tab",
    wx.WXK_DELETE: "delete",
    wx.WXK_INSERT: "insert",
    wx.WXK_SPECIAL1: "special1",
    wx.WXK_SPECIAL2: "special2",
    wx.WXK_SPECIAL3: "special3",
    wx.WXK_SPECIAL4: "special4",
    wx.WXK_SPECIAL5: "special5",
    wx.WXK_SPECIAL6: "special6",
    wx.WXK_SPECIAL7: "special7",
    wx.WXK_SPECIAL8: "special8",
    wx.WXK_SPECIAL9: "special9",
    wx.WXK_SPECIAL10: "special10",
    wx.WXK_SPECIAL11: "special11",
    wx.WXK_SPECIAL12: "special12",
    wx.WXK_SPECIAL13: "special13",
    wx.WXK_SPECIAL14: "special14",
    wx.WXK_SPECIAL15: "special15",
    wx.WXK_SPECIAL16: "special16",
    wx.WXK_SPECIAL17: "special17",
    wx.WXK_SPECIAL18: "special18",
    wx.WXK_SPECIAL19: "special19",
    wx.WXK_SPECIAL20: "special20",
    wx.WXK_CLEAR: "clear",
    wx.WXK_WINDOWS_MENU: "menu",
}


def is_navigation_key(keyvalue):
    if keyvalue is None:
        return False
    if "right" in keyvalue:
        return True
    if "left" in keyvalue:
        return True
    if "up" in keyvalue and "pgup" not in keyvalue and "pageup" not in keyvalue:
        return True
    if "down" in keyvalue and "pagedown" not in keyvalue:
        return True
    if "tab" in keyvalue:
        return True
    if "return" in keyvalue:
        return True
    return False


def get_key_name(event, return_modifier=False):
    keyvalue = ""
    # https://wxpython.org/Phoenix/docs/html/wx.KeyEvent.html
    key = event.GetUnicodeKey()
    if key == wx.WXK_NONE:
        key = event.GetKeyCode()
    if event.RawControlDown() and not event.ControlDown():
        keyvalue += "macctl+"  # Deliberately not macctrl+
    elif event.ControlDown():
        keyvalue += "ctrl+"
    if event.AltDown() or key == wx.WXK_ALT:
        keyvalue += "alt+"
    if event.ShiftDown():
        keyvalue += "shift+"
    if event.MetaDown() or key in WX_METAKEYS:
        keyvalue += "meta+"
    # if return_modifier and keyvalue: print("key", key, keyvalue)
    if key in WX_MODIFIERS:
        return keyvalue if return_modifier else None
    if key in WX_SPECIALKEYS:
        keyvalue += WX_SPECIALKEYS[key]
    else:
        keyvalue += chr(key)
    # print("key", key, keyvalue)
    return keyvalue.lower()


def disable_window(window):
    for m in window.Children:
        if hasattr(m, "Disable"):
            m.Disable()
        if hasattr(m, "Children"):
            disable_window(m)


def set_ctrl_value(ctrl, value):
    # Let's try to save the caret position
    try:
        cursor = ctrl.GetInsertionPoint()
        if ctrl.GetValue() != value:
            ctrl.SetValue(str(value))
            ctrl.SetInsertionPoint(min(len(str(value)), cursor))
    except RuntimeError:
        # Control might already have been destroyed
        pass


def dip_size(frame, x, y):
    # wx.Window.FromDIP was introduced with wxPython 4.1, so not all distros may have this
    wxsize = wx.Size(x, y)
    try:
        dipsize = frame.FromDIP(wxsize)
        return dipsize
    except AttributeError:
        return wxsize
