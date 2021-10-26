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
        func = choice['action']
        func_kwargs = choice['kwargs']
        func_args = choice['kwargs']

        def specific(event=None):
            func(*func_args, **func_kwargs)

        return specific

    def set_bool(choice, value):
        obj = choice['object']
        param = choice['attr']

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
            if get('separate_before', default=False):
                menu.AppendSeparator()
            if submenu_name is not None:
                submenu = wx.Menu()
                menu.AppendSubMenu(submenu, submenu_name)
                submenus[submenu_name] = submenu

        menu_context = submenu if submenu is not None else menu
        t = get('type')
        if t == bool:
            item = menu_context.Append(wx.ID_ANY, get("label"), get("tip"), wx.ITEM_CHECK)
            obj = get('object')
            param = get('attr')
            check = bool(getattr(obj, param, False))
            item.Check(check)
            gui.Bind(
                wx.EVT_MENU,
                set_bool(choice, not check),
                item,
            )
        elif t == "action":
            item = menu_context.Append(wx.ID_ANY, get("label"), get("tip"), wx.ITEM_NORMAL)
            gui.Bind(
                wx.EVT_MENU,
                execute(choice),
                item,
            )
        if not submenu and get("separate_after", default=False):
            menu.AppendSeparator()
    return menu
