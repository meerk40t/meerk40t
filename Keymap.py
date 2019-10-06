import wx


class Keymap(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: Keymap.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((400, 300))
        self.check_invert_mouse_zoom = wx.CheckBox(self, wx.ID_ANY, "Invert Mouse Wheel Zoom")
        self.list_keymap = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.button_add = wx.Button(self, wx.ID_ANY, "Add Hotkey")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_mouse_zoom_invert, self.check_invert_mouse_zoom)
        self.Bind(wx.EVT_BUTTON, self.on_button_add_hotkey, self.button_add)
        # end wxGlade
        # end wxGlade
        self.project = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        try:
            del self.project.windows["preferences"]
        except KeyError:
            pass
        event.Skip()  # Call destroy.

    def set_project(self, project):
        self.project = project
        self.check_invert_mouse_zoom.SetValue(self.project.mouse_zoom_invert)
        self.reload_keymap()

    def __set_properties(self):
        # begin wxGlade: Keymap.__set_properties
        self.SetTitle("Keymap Settings")
        self.list_keymap.AppendColumn("Action", format=wx.LIST_FORMAT_LEFT, width=100)
        self.list_keymap.AppendColumn("Hotkey", format=wx.LIST_FORMAT_LEFT, width=279)
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
        for key in self.project.keymap:
            action = self.project.keymap[key]
            m = self.list_keymap.InsertItem(i, str(action))
            i += 1
            if m != -1:
                self.list_keymap.SetItem(m, 1, str(action.command))

    def on_check_mouse_zoom_invert(self, event):  # wxGlade: Keymap.<event_handler>
        self.project.mouse_zoom_invert = self.check_invert_mouse_zoom.GetValue()

    def on_button_add_hotkey(self, event):  # wxGlade: Keymap.<event_handler>
        print("Event handler 'on_button_add_hotkey' not implemented!")
        event.Skip()
