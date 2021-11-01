from typing import List

import wx

"""
Mixin functions for wxMeerk40t
"""


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
                menu.AppendSubMenu(submenu, submenu_name)
                submenus[submenu_name] = submenu

        menu_context = submenu if submenu is not None else menu
        if func.reference is not None:
            menu_context.AppendSubMenu(
                create_menu_for_node(gui, func.reference(node), elements),
                func.real_name,
            )
            continue
        if func.radio_state is not None:
            item = menu_context.Append(wx.ID_ANY, func.real_name, "", wx.ITEM_RADIO)
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
                menu_context.Append(wx.ID_ANY, func.real_name, "", wx.ITEM_NORMAL),
            )
            if menu_context not in radio_check_not_needed:
                radio_check_not_needed.append(menu_context)
        if not submenu and func.separate_after:
            menu.AppendSeparator()

    for submenu in submenus.values():
        if submenu not in radio_check_not_needed:
            item = submenu.Append(wx.ID_ANY, "-----", "", wx.ITEM_RADIO)
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


def get_key_name(event):
    keyvalue = ""
    if event.ControlDown():
        keyvalue += "control+"
    if event.AltDown():
        keyvalue += "alt+"
    if event.ShiftDown():
        keyvalue += "shift+"
    if event.MetaDown():
        keyvalue += "meta+"
    key = event.GetKeyCode()
    if key == wx.WXK_CONTROL:
        return
    if key == wx.WXK_ALT:
        return
    if key == wx.WXK_SHIFT:
        return
    if key == wx.WXK_F1:
        keyvalue += "f1"
    elif key == wx.WXK_F2:
        keyvalue += "f2"
    elif key == wx.WXK_F3:
        keyvalue += "f3"
    elif key == wx.WXK_F4:
        keyvalue += "f4"
    elif key == wx.WXK_F5:
        keyvalue += "f5"
    elif key == wx.WXK_F6:
        keyvalue += "f6"
    elif key == wx.WXK_F7:
        keyvalue += "f7"
    elif key == wx.WXK_F8:
        keyvalue += "f8"
    elif key == wx.WXK_F9:
        keyvalue += "f9"
    elif key == wx.WXK_F10:
        keyvalue += "f10"
    elif key == wx.WXK_F11:
        keyvalue += "f11"
    elif key == wx.WXK_F12:
        keyvalue += "f12"
    elif key == wx.WXK_F13:
        keyvalue += "f13"
    elif key == wx.WXK_F14:
        keyvalue += "f14"
    elif key == wx.WXK_F15:
        keyvalue += "f15"
    elif key == wx.WXK_F16:
        keyvalue += "f16"
    elif key == wx.WXK_ADD:
        keyvalue += "+"
    elif key == wx.WXK_END:
        keyvalue += "end"
    elif key == wx.WXK_NUMPAD0:
        keyvalue += "numpad0"
    elif key == wx.WXK_NUMPAD1:
        keyvalue += "numpad1"
    elif key == wx.WXK_NUMPAD2:
        keyvalue += "numpad2"
    elif key == wx.WXK_NUMPAD3:
        keyvalue += "numpad3"
    elif key == wx.WXK_NUMPAD4:
        keyvalue += "numpad4"
    elif key == wx.WXK_NUMPAD5:
        keyvalue += "numpad5"
    elif key == wx.WXK_NUMPAD6:
        keyvalue += "numpad6"
    elif key == wx.WXK_NUMPAD7:
        keyvalue += "numpad7"
    elif key == wx.WXK_NUMPAD8:
        keyvalue += "numpad8"
    elif key == wx.WXK_NUMPAD9:
        keyvalue += "numpad9"
    elif key == wx.WXK_NUMPAD_ADD:
        keyvalue += "numpad_add"
    elif key == wx.WXK_NUMPAD_SUBTRACT:
        keyvalue += "numpad_subtract"
    elif key == wx.WXK_NUMPAD_MULTIPLY:
        keyvalue += "numpad_multiply"
    elif key == wx.WXK_NUMPAD_DIVIDE:
        keyvalue += "numpad_divide"
    elif key == wx.WXK_NUMPAD_DECIMAL:
        keyvalue += "numpad."
    elif key == wx.WXK_NUMPAD_ENTER:
        keyvalue += "numpad_enter"
    elif key == wx.WXK_NUMPAD_RIGHT:
        keyvalue += "numpad_right"
    elif key == wx.WXK_NUMPAD_LEFT:
        keyvalue += "numpad_left"
    elif key == wx.WXK_NUMPAD_UP:
        keyvalue += "numpad_up"
    elif key == wx.WXK_NUMPAD_DOWN:
        keyvalue += "numpad_down"
    elif key == wx.WXK_NUMPAD_DELETE:
        keyvalue += "numpad_delete"
    elif key == wx.WXK_NUMPAD_INSERT:
        keyvalue += "numpad_insert"
    elif key == wx.WXK_NUMPAD_PAGEUP:
        keyvalue += "numpad_pgup"
    elif key == wx.WXK_NUMPAD_PAGEDOWN:
        keyvalue += "numpad_pgdn"
    elif key == wx.WXK_NUMLOCK:
        keyvalue += "numlock"
    elif key == wx.WXK_SCROLL:
        keyvalue += "scroll"
    elif key == wx.WXK_HOME:
        keyvalue += "home"
    elif key == wx.WXK_DOWN:
        keyvalue += "down"
    elif key == wx.WXK_UP:
        keyvalue += "up"
    elif key == wx.WXK_RIGHT:
        keyvalue += "right"
    elif key == wx.WXK_LEFT:
        keyvalue += "left"
    elif key == wx.WXK_ESCAPE:
        keyvalue += "escape"
    elif key == wx.WXK_BACK:
        keyvalue += "back"
    elif key == wx.WXK_PAUSE:
        keyvalue += "pause"
    elif key == wx.WXK_PAGEDOWN:
        keyvalue += "pagedown"
    elif key == wx.WXK_PAGEUP:
        keyvalue += "pageup"
    elif key == wx.WXK_PRINT:
        keyvalue += "print"
    elif key == wx.WXK_RETURN:
        keyvalue += "return"
    elif key == wx.WXK_SPACE:
        keyvalue += "space"
    elif key == wx.WXK_TAB:
        keyvalue += "tab"
    elif key == wx.WXK_DELETE:
        keyvalue += "delete"
    elif key == wx.WXK_INSERT:
        keyvalue += "insert"
    else:
        keyvalue += chr(key)
    return keyvalue.lower()
