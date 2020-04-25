import wx

from Kernel import Module

_ = wx.GetTranslation


class Keymap(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: Keymap.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((400, 300))
        self.check_invert_mouse_zoom = wx.CheckBox(self, wx.ID_ANY, _("Invert Mouse Wheel Zoom"))
        self.list_keymap = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.button_add = wx.Button(self, wx.ID_ANY, _("Add Hotkey"))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_mouse_zoom_invert, self.check_invert_mouse_zoom)
        self.Bind(wx.EVT_BUTTON, self.on_button_add_hotkey, self.button_add)
        # end wxGlade
        # end wxGlade
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        self.device.module_instance_remove(self.name)
        event.Skip()  # Call destroy.

    def initialize(self):
        self.device.module_instance_close(self.name)
        self.Show()
        self.device.setting(bool, "mouse_zoom_invert", False)
        self.check_invert_mouse_zoom.SetValue(self.device.mouse_zoom_invert)
        self.reload_keymap()

    def shutdown(self,  channel):
        self.Close()

    def __set_properties(self):
        # begin wxGlade: Keymap.__set_properties
        self.SetTitle(_("Keymap Settings"))
        self.check_invert_mouse_zoom.SetToolTip(_("Invert the zoom direction from the mouse wheel."))
        self.list_keymap.SetToolTip(_("What keys are bound to which actions?"))
        self.list_keymap.AppendColumn(_("Action"), format=wx.LIST_FORMAT_LEFT, width=100)
        self.list_keymap.AppendColumn(_("Hotkey"), format=wx.LIST_FORMAT_LEFT, width=279)
        self.button_add.SetToolTip(_("Add a new hotkey"))
        self.button_add.Enable(False)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Keymap.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.check_invert_mouse_zoom, 0, 0, 0)
        sizer_1.Add(self.list_keymap, 1, wx.EXPAND, 0)
        sizer_1.Add(self.button_add, 0, 0, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def reload_keymap(self):
        i = 0
        for key in self.device.device_root.keymap:
            action = self.device.device_root.keymap[key]
            m = self.list_keymap.InsertItem(i, str(action))
            i += 1
            if m != -1:
                self.list_keymap.SetItem(m, 1, str(action.command))

    def on_check_mouse_zoom_invert(self, event):  # wxGlade: Keymap.<event_handler>
        self.device.mouse_zoom_invert = self.check_invert_mouse_zoom.GetValue()

    def on_button_add_hotkey(self, event):  # wxGlade: Keymap.<event_handler>
        pass
