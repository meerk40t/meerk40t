from functools import partial
import wx

from .icons import icons8_keyboard_50
from .mwindow import MWindow

_ = wx.GetTranslation


class KeymapPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.list_index = []

        self.list_keymap = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES,
        )
        self.button_add = wx.Button(self, wx.ID_ANY, _("Add Hotkey"))
        self.text_key_name = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_command_name = wx.TextCtrl(self, wx.ID_ANY, "")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_add_hotkey, self.button_add)
        # end wxGlade
        self.Bind(
            wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_rightclick, self.list_keymap
        )
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_activated, self.list_keymap)
        self.text_key_name.Bind(wx.EVT_KEY_DOWN, partial(self.on_key_press, True))
        self.text_key_name.Bind(wx.EVT_KEY_UP, partial(self.on_key_press, False))

    def initialize(self):
        self.reload_keymap()
        self.Children[0].SetFocus()

    def finalize(self):
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

    def on_item_activated(self, event):
        element = event.Text
        self.text_key_name.SetValue(element)
        self.text_command_name.SetValue(self.context.keymap[element])

    def on_item_rightclick(self, event):
        element = event.Text
        menu = wx.Menu()
        convert = menu.Append(
            wx.ID_ANY, _("Remove %s") % str(element)[:16], "", wx.ITEM_NORMAL
        )
        self.Bind(wx.EVT_MENU, self.on_tree_popup_delete(element), convert)
        convert = menu.Append(
            wx.ID_ANY, _("Reset Keymap to defaults"), "", wx.ITEM_NORMAL
        )
        self.Bind(wx.EVT_MENU, self.on_tree_popup_clear(element), convert)
        self.PopupMenu(menu)
        menu.Destroy()

    def on_tree_popup_clear(self, element):
        def delete(event=None):
            self.context.default_keymap()
            self.reload_keymap()

        return delete

    def on_tree_popup_delete(self, element):
        def delete(event=None):
            try:
                del self.context.keymap[element]
                self.list_keymap.DeleteAllItems()
                self.reload_keymap()
            except KeyError:
                pass

        return delete

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
        self.context.keymap[
            self.text_key_name.GetValue()
        ] = self.text_command_name.GetValue()
        self.text_key_name.SetValue("")
        self.text_command_name.SetValue("")
        self.list_keymap.DeleteAllItems()
        self.reload_keymap()

    def on_key_press(self, keydown, event):
        from meerk40t.gui.wxutils import get_key_name

        keyvalue = get_key_name(event, return_modifier=keydown)

        # Do not clear keyvalue if key chosen and modifier is released
        # i.e. Alt down, Alt+a, Alt up
        if not keydown and keyvalue is None:
            oldkey = self.text_key_name.GetValue()
            oldkey = oldkey.rsplit("+", 1)[1] if "+" in oldkey else oldkey
            if oldkey != "":
                return

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
            i = self.list_keymap.FindItem(-1, keyvalue)
            if i != wx.NOT_FOUND:
                self.list_keymap.Select(i, True)
                self.list_keymap.Focus(i)
                self.text_command_name.SetValue(self.list_keymap.GetItemText(i,1))
            else:
                self.list_keymap.Select(i, False)

    def reload_keymap(self):
        self.list_keymap.DeleteAllItems()
        self.list_index.clear()
        i = 0
        for key, value in self.context.keymap.items():
            m = self.list_keymap.InsertItem(0, str(key))
            if m != -1:
                self.list_keymap.SetItem(m, 1, str(value))
                self.list_keymap.SetItemData(m, i)
                i += 1
                self.list_index.append(tuple(key.rsplit("+", 1)) if "+" in key else ("", key))
        self.list_keymap.SortItems(self.__list_sort_compare)

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
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_keyboard_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Keymap.__set_properties
        self.SetTitle(_("Keymap Settings"))

    def window_open(self):
        self.panel.initialize()

    def window_close(self):
        self.panel.finalize()
