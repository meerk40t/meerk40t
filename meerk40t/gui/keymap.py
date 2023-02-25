import platform

import wx

from .icons import icons8_keyboard_50
from .mwindow import MWindow
from .wxutils import get_key_name

_ = wx.GetTranslation


class KeymapPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.parent = args[0]
        self.context = context
        self.list_index = []

        self.list_keymap = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES,
        )
        self.button_add = wx.Button(self, wx.ID_ANY, _("Add Hotkey"))
        self.text_key_name = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_command_name = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )

        self.key_menu = wx.MenuBar()
        self.create_menu(self.key_menu.Append)
        self.parent.SetMenuBar(self.key_menu)

        self.__set_properties()
        self.__do_layout()

        self.button_add.Bind(wx.EVT_BUTTON, self.on_button_add_hotkey)
        self.text_command_name.Bind(wx.EVT_TEXT_ENTER, self.on_button_add_hotkey)
        # end wxGlade
        self.list_keymap.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_rightclick)
        self.list_keymap.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_activated)
        self.text_key_name.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.text_key_name.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.key_pressed = False

    def pane_show(self):
        self.reload_keymap()
        self.Children[0].SetFocus()

    def pane_hide(self):
        pass

    def __set_properties(self):
        self.list_keymap.SetToolTip(_("What keys are bound to which actions?"))
        self.list_keymap.AppendColumn(_("Key"), format=wx.LIST_FORMAT_LEFT, width=140)
        self.list_keymap.AppendColumn(
            _("Command"), format=wx.LIST_FORMAT_LEFT, width=322
        )
        self.button_add.SetToolTip(_("Add a new hotkey"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Keymap.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(self.list_keymap, 1, wx.EXPAND, 0)
        sizer_2.Add(self.button_add, 0, 0, 0)
        sizer_2.Add(self.text_key_name, 1, 0, 0)
        sizer_2.Add(self.text_command_name, 2, 0, 0)
        sizer_1.Add(sizer_2, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def create_menu(self, append):
        tmp_menu = wx.Menu()
        item = tmp_menu.Append(wx.ID_ANY, _("Reset Keymap to defaults"), "")
        self.parent.Bind(wx.EVT_MENU, self.restore_keymap, id=item.GetId())
        append(tmp_menu, _("Standard"))

    def on_item_activated(self, event):
        element = event.Text
        self.text_key_name.SetValue(element)
        self.text_command_name.SetValue(
            self.context.bind.keymap[KeymapPanel.__translate_from_mac(element)]
        )

    def on_item_rightclick(self, event):
        element = event.Text

        menu = wx.Menu()
        self.Bind(
            wx.EVT_MENU,
            self.on_tree_popup_delete(element),
            menu.Append(
                wx.ID_ANY,
                _("Remove {name}").format(name=str(element)[:16]),
                "",
            ),
        )
        ct = self.list_keymap.GetSelectedItemCount()
        if ct > 1:
            self.Bind(
                wx.EVT_MENU,
                self.on_tree_popup_delete_all_selected,
                menu.Append(
                    wx.ID_ANY,
                    _("Remove {count} entries").format(count=ct),
                    "",
                ),
            )

        self.Bind(
            wx.EVT_MENU,
            self.on_tree_popup_clear(element),
            menu.Append(
                wx.ID_ANY,
                _("Reset Keymap to defaults"),
                "",
            ),
        )
        self.PopupMenu(menu)
        menu.Destroy()

    def on_tree_popup_clear(self, element):
        def delete(event=None):
            self.context.bind.default_keymap()
            self.reload_keymap()

        return delete

    def on_tree_popup_delete(self, element):
        def delete(event=None):
            try:
                del self.context.bind.keymap[element]
                self.list_keymap.DeleteAllItems()
                self.reload_keymap()
            except KeyError:
                pass

        return delete

    def on_tree_popup_delete_all_selected(self, event):
        item = self.list_keymap.GetFirstSelected()
        while item >= 0:
            key = self.list_keymap.GetItemText(item, col=0)
            # print ("Try to delete key %s" % key)
            try:
                del self.context.bind.keymap[key]
            except KeyError:
                pass
            item = self.list_keymap.GetNextSelected(item)
        self.reload_keymap()

    def restore_keymap(self, event):
        self.context.bind.default_keymap()
        self.reload_keymap()

    def reload_keymap(self):
        self.list_keymap.DeleteAllItems()
        self.list_index.clear()
        i = 0
        for key, value in self.context.bind.keymap.items():
            key = KeymapPanel.__translate_to_mac(key)
            m = self.list_keymap.InsertItem(0, str(key))
            if m != -1:
                self.list_keymap.SetItem(m, 1, str(value))
                self.list_keymap.SetItemData(m, i)
                self.list_index.append(KeymapPanel.__split_modifiers(key))
                i += 1
        self.list_keymap.SortItems(self.__list_sort_compare)

    def on_button_add_hotkey(self, event=None):  # wxGlade: Keymap.<event_handler>
        keystroke = self.text_key_name.GetValue()
        if len(keystroke) == 0:
            dlg = wx.MessageDialog(
                None,
                _("Missing Keystroke"),
                _("No Keystroke for binding."),
                wx.OK | wx.ICON_WARNING,
            )
            dlg.ShowModal()
            dlg.Destroy()
            self.text_key_name.SetFocus()
            return
        if len(self.text_command_name.GetValue()) == 0:
            dlg = wx.MessageDialog(
                None,
                _("Missing Command"),
                _("No Command for binding."),
                wx.OK | wx.ICON_WARNING,
            )
            dlg.ShowModal()
            dlg.Destroy()
            self.text_command_name.SetFocus()
            return
        origkey = self.text_key_name.GetValue()
        key = KeymapPanel.__translate_from_mac(origkey)
        self.context.bind.keymap[key] = self.text_command_name.GetValue()
        self.text_key_name.SetValue("")
        self.text_command_name.SetValue("")
        self.list_keymap.DeleteAllItems()
        self.reload_keymap()
        self.select_item_by_key(origkey)

    def on_key_down(self, event):
        keyvalue = get_key_name(event, return_modifier=True)
        # print("down", keyvalue)
        mod, key = KeymapPanel.__split_modifiers(keyvalue)
        if key:
            self.key_pressed = True
        self.process_key_event(keyvalue)

    def on_key_up(self, event):
        keyvalue = get_key_name(event, return_modifier=True)
        # print("up", keyvalue)
        if self.key_pressed:
            if keyvalue is None:
                self.key_pressed = False
            return
        mod, key = KeymapPanel.__split_modifiers(keyvalue)
        if key:
            self.key_pressed = True
        self.process_key_event(keyvalue)

    def process_key_event(self, keyvalue):
        keyvalue = KeymapPanel.__translate_to_mac(keyvalue)

        # Clear existing selection(s)
        i = self.list_keymap.GetFirstSelected()
        while i >= 0:
            self.list_keymap.Select(i, 0)
            i = self.list_keymap.GetFirstSelected()

        self.text_command_name.SetValue("")
        if keyvalue is None:
            self.text_key_name.SetValue("")
        else:
            self.text_key_name.SetValue(keyvalue)
            i = self.select_item_by_key(keyvalue)
            if i != wx.NOT_FOUND:
                self.text_command_name.SetValue(self.list_keymap.GetItemText(i, 1))

    def select_item_by_key(self, keyname):
        i = self.list_keymap.FindItem(-1, keyname)
        if i != wx.NOT_FOUND:
            self.list_keymap.Select(i, True)
            self.list_keymap.Focus(i)
            self.text_command_name.SetValue(self.list_keymap.GetItemText(i, 1))
        else:
            self.list_keymap.Select(i, False)
        return i

    @staticmethod
    def __split_modifiers(key):
        return key.rsplit("+", 1) if "+" in key else ("", key)

    @staticmethod
    def __join_modifiers(*args):
        if len(args) == 1:
            args = args[0]
        return "+".join(args) if args[0] else args[1]

    @staticmethod
    def __translate_to_mac(key):
        if platform.system() != "Darwin":
            return key
        if key is None:
            return key
        mods, key = KeymapPanel.__split_modifiers(key)
        mods = mods.replace("ctrl", "cmd")
        mods = mods.replace("macctl", "ctrl")
        return KeymapPanel.__join_modifiers(mods, key)

    @staticmethod
    def __translate_from_mac(key):
        if platform.system() != "Darwin":
            return key
        if key is None:
            return key
        mods, key = KeymapPanel.__split_modifiers(key)
        mods = mods.replace("ctrl", "macctl")
        mods = mods.replace("cmd", "ctrl")
        return KeymapPanel.__join_modifiers(mods, key)

    def __list_sort_compare(self, item1, item2):
        """
        Compare function to sort ListCtrl by modifier and then key

        Keys are listed in the following order:
        1. single character names
        2. double character names (i.e. f1 etc.)
        3. longer names

        and sorted alphabetically within these groups.
        """
        item1 = self.list_index[item1]
        item2 = self.list_index[item2]
        if item1[0] < item2[0]:
            return -1
        if item2[0] < item1[0]:
            return 1
        if len(item1[1]) <= 3 and len(item1[1]) < len(item2[1]):
            return -1
        if len(item2[1]) <= 3 and len(item2[1]) < len(item1[1]):
            return 1
        return -1 if item1 < item2 else 1 if item2 < item1 else 0


class Keymap(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(500, 530, *args, **kwds)

        self.panel = KeymapPanel(self, wx.ID_ANY, context=self.context)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_keyboard_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Keymap.__set_properties
        self.SetTitle(_("Keymap Settings"))

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/config/Keymap",
            {
                "label": _("Keymap"),
                "icon": icons8_keyboard_50,
                "tip": _("Opens Keymap Window"),
                "action": lambda v: kernel.console("window toggle Keymap\n"),
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def submenu():
        # suppress in tool-menu
        return ("", "Keymap", True)
