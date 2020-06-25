import wx

from Kernel import Module

_ = wx.GetTranslation


class Keymap(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: Keymap.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.FRAME_FLOAT_ON_PARENT
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((500, 530))
        self.list_keymap = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.button_add = wx.Button(self, wx.ID_ANY, _("Add Hotkey"))
        self.text_key_name = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_command_name = wx.TextCtrl(self, wx.ID_ANY, "")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_add_hotkey, self.button_add)
        # end wxGlade
        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.text_key_name.Bind(wx.EVT_KEY_DOWN, self.on_key_press)
        self.SetFocus()

    def on_close(self, event):
        self.device.remove('window', self.name)
        event.Skip()  # Call destroy.

    def initialize(self):
        self.device.close('window', self.name)
        self.Show()
        self.reload_keymap()

    def shutdown(self, channel):
        try:
            self.Close()
        except RuntimeError:
            pass

    def __set_properties(self):
        # begin wxGlade: Keymap.__set_properties
        self.SetTitle(_("Keymap Settings"))
        self.list_keymap.SetToolTip(_("What keys are bound to which actions?"))
        self.list_keymap.AppendColumn(_("Key"), format=wx.LIST_FORMAT_LEFT, width=114)
        self.list_keymap.AppendColumn(_("Command"), format=wx.LIST_FORMAT_LEFT, width=348)
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

    def reload_keymap(self):
        i = 0
        for key in self.device.device_root.keymap:
            value = self.device.device_root.keymap[key]
            m = self.list_keymap.InsertItem(i, str(key))
            i += 1
            if m != -1:
                self.list_keymap.SetItem(m, 1, str(value))

    def on_button_add_hotkey(self, event):  # wxGlade: Keymap.<event_handler>
        keystroke = self.text_key_name.GetValue()
        if len(keystroke) == 0:
            dlg = wx.MessageDialog(None, _("Missing Keystroke"),
                               _("No Keystroke for binding."), wx.OK | wx.ICON_WARNING)
            result = dlg.ShowModal()
            dlg.Destroy()
            return
        if len(self.text_key_name.GetValue()) == 0:
            dlg = wx.MessageDialog(None, _("Missing Command"),
                               _("No Command for binding."), wx.OK | wx.ICON_WARNING)
            result = dlg.ShowModal()
            dlg.Destroy()
            return
        self.device.device_root.keymap[self.text_key_name.GetValue()] = self.text_command_name.GetValue()
        self.text_key_name.SetValue('')
        self.text_command_name.SetValue('')
        self.reload_keymap()

    def on_key_press(self, event):
        from wxMeerK40t import get_key_name
        keyvalue = get_key_name(event)
        self.text_command_name.SetValue('')
        if keyvalue is None:
            self.text_key_name.SetValue('')
        else:
            self.text_key_name.SetValue(keyvalue)
            for i, key in enumerate(self.device.device_root.keymap):
                if key == keyvalue:
                    self.list_keymap.Select(i, True)
                    self.list_keymap.Focus(i)
                    self.text_command_name.SetValue(self.device.device_root.keymap[key])
                else:
                    self.list_keymap.Select(i, False)