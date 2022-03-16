"""
Mixin functions for wxMeerk40t
"""

from typing import List

import wx

_ = wx.GetTranslation


def create_menu_for_choices(gui, choices: List[dict]) -> wx.Menu:
    """
    Creates a menu for a given choices table

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
        if submenu_name in submenus:
            submenu = submenus[submenu_name]
        else:
            if get("separate_before", default=False):
                menu.AppendSeparator()
            if submenu_name is not None:
                submenu = wx.Menu()
                menu.AppendSubMenu(submenu, submenu_name)
                submenus[submenu_name] = submenu

        menu_context = submenu if submenu is not None else menu
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


def create_menu_for_node(gui, node, elements) -> wx.Menu:
    """
    Create menu for a particular node. Does not invoke the menu.

    Processes submenus, references, radio_state as needed.
    """
    menu = wx.Menu()
    submenus = {}
    radio_check_not_needed = []

    def menu_functions(f, node):
        func_dict = dict(f.func_dict)

        def specific(event=None):
            f(node, **func_dict)

        return specific

    for func in elements.tree_operations_for_node(node):
        submenu_name = func.submenu
        submenu = None
        if submenu_name in submenus:
            submenu = submenus[submenu_name]
        else:
            if func.separate_before:
                menu.AppendSeparator()
            if submenu_name is not None:
                submenu = wx.Menu()
                menu.AppendSubMenu(submenu, submenu_name, func.help)
                submenus[submenu_name] = submenu

        menu_context = submenu if submenu is not None else menu
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
            gui.Bind(
                wx.EVT_MENU,
                menu_functions(func, node),
                item,
            )
            check = func.radio_state
            item.Check(check)
            if check and menu_context not in radio_check_not_needed:
                radio_check_not_needed.append(menu_context)
        else:
            gui.Bind(
                wx.EVT_MENU,
                menu_functions(func, node),
                menu_context.Append(
                    wx.ID_ANY, func.real_name, func.help, wx.ITEM_NORMAL
                ),
            )
            if menu_context not in radio_check_not_needed:
                radio_check_not_needed.append(menu_context)
        if not submenu and func.separate_after:
            menu.AppendSeparator()

    for submenu in submenus.values():
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

    :param gui: Gui used to create menu items.
    :param node: The Node clicked on for the generated menu.
    :return:
    """
    if node is None:
        return
    if hasattr(node, "node"):
        node = node.node
    menu = create_menu_for_node(gui, node, elements)
    if menu.MenuItemCount != 0:
        gui.PopupMenu(menu)
        menu.Destroy()


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
    wx.WXK_F16: "f17",
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
