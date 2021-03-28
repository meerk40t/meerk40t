import wx

from .icons import icons8_keyboard_50
from .mwindow import MWindow

_ = wx.GetTranslation


class Keymap(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(500, 530, *args, **kwds)

        self.list_keymap = wx.ListCtrl(
            self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES
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
        self.text_key_name.Bind(wx.EVT_KEY_DOWN, self.on_key_press)

    def window_open(self):
        self.reload_keymap()

    def window_close(self):
        pass

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_keyboard_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Keymap.__set_properties
        self.SetTitle(_("Keymap Settings"))
        self.list_keymap.SetToolTip(_("What keys are bound to which actions?"))
        self.list_keymap.AppendColumn(_("Key"), format=wx.LIST_FORMAT_LEFT, width=114)
        self.list_keymap.AppendColumn(
            _("Command"), format=wx.LIST_FORMAT_LEFT, width=348
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
        convert = menu.Append(wx.ID_ANY, _("Reset Default"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_clear(element), convert)
        self.PopupMenu(menu)
        menu.Destroy()

    def on_tree_popup_clear(self, element):
        def delete(event):
            self.context.default_keymap()
            self.list_keymap.DeleteAllItems()
            self.reload_keymap()

        return delete

    def on_tree_popup_delete(self, element):
        def delete(event):
            try:
                del self.context.keymap[element]
                self.list_keymap.DeleteAllItems()
                self.reload_keymap()
            except KeyError:
                pass

        return delete

    def reload_keymap(self):
        i = 0
        for key in self.context.keymap:
            value = self.context.keymap[key]
            m = self.list_keymap.InsertItem(i, str(key))
            i += 1
            if m != -1:
                self.list_keymap.SetItem(m, 1, str(value))

    def on_button_add_hotkey(self, event):  # wxGlade: Keymap.<event_handler>
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

    def on_key_press(self, event):
        from .wxmeerk40t import get_key_name

        keyvalue = get_key_name(event)
        self.text_command_name.SetValue("")
        if keyvalue is None:
            self.text_key_name.SetValue("")
        else:
            self.text_key_name.SetValue(keyvalue)
            for i, key in enumerate(self.context.keymap):
                if key == keyvalue:
                    self.list_keymap.Select(i, True)
                    self.list_keymap.Focus(i)
                    self.text_command_name.SetValue(self.context.keymap[key])
                else:
                    self.list_keymap.Select(i, False)
