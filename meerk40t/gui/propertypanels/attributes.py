import wx
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.svgelements import Color

_ = wx.GetTranslation

class ColorPanel(wx.Panel):
    def __init__(self, *args, context=None, label=None, attribute=None, callback=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.callback = callback
        if attribute is None:
            attribute = "stroke"
        self.attribute = attribute
        self.label = label
        self.node = node

        self.header = wx.StaticBox(self, wx.ID_ANY, _(self.label))
        main_sizer = wx.StaticBoxSizer(
            self.header, wx.VERTICAL
        )
        color_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(color_sizer, 0, wx.EXPAND, 0)
        self.btn_color = []
        self.lbl_color = []
        bgcolors = (
            0xFFFFFF,
            0x000000,
            0xFF0000,
            0x00FF00,
            0x0000FF,
            0xFFFF00,
            0xFF00FF,
            0x00FFFF,
        )
        for i in range(8):
            self.lbl_color.append(wx.StaticText(self, wx.ID_ANY, ""))
            # self.lbl_color[i].SetMinSize((-1, 20))
            self.btn_color.append(wx.Button(self, wx.ID_ANY, ""))
            if i == 0:
                self.btn_color[i].SetForegroundColour(wx.RED)
                self.btn_color[i].SetLabel("X")
            self.btn_color[i].SetMinSize((10, 23))
            self.btn_color[i].SetBackgroundColour(wx.Colour(bgcolors[i]))
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(self.btn_color[i], 0, wx.EXPAND, 0)
            sizer.Add(self.lbl_color[i], 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
            color_sizer.Add(sizer, 1, wx.EXPAND, 0)
            self.btn_color[i].Bind(wx.EVT_BUTTON, self.on_button)
        self.SetSizer(main_sizer)
        self.Layout()
        self.set_widgets(self.node)

    def on_button(self, event):
        button = event.GetEventObject()
        for bidx, sbtn in enumerate(self.btn_color):
            if sbtn == button:
                value = None
                if bidx == 0:
                    value = None
                else:
                    if bidx<0 or bidx>=len(self.btn_color):
                        bidx = -1
                    else:
                        bcolor = button.GetBackgroundColour()
                        rgb = bcolor.GetRGB()
                        color = swizzlecolor(rgb)
                        value = Color(color, 1.0)
                setattr(self.node, self.attribute, value)
                self.context.elements.signal("element_property_update", self.node)
                if self.callback is not None:
                    self.callback()
                self.mark_color(bidx)

                break

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def accepts(self, node):
        return hasattr(node, self.attribute)

    def set_widgets(self, node):
        self.node = node
        # print(f"set_widget for {self.attribute} to {str(node)}")
        if self.node is None or not self.accepts(node):
            self.Hide()
            return
        self.mark_color(None)
        self.Show()

    def mark_color(self, idx):
        if self.node is None:
            idx = -1
        else:
            value = getattr(self.node, self.attribute, None)
            nodecol = None
            if value == "none":
                value = None
            colinfo = "None"
            if value is not None:
                nodecol = wx.Colour(swizzlecolor(value))
                s = ""
                try:
                    s = nodecol.GetAsString(wx.C2S_NAME)
                except AssertionError:
                    s = ""
                if s != "":
                    s = s + " = " + value.hexrgb
                else:
                    s = value.hexrgb
                colinfo = s
            self.header.SetLabel(_(self.label)+ " (" + colinfo + ")")
            self.header.Refresh()

            if idx is None:    # Okay, we need to determine it ourselves
                idx = -1
                if value is None:
                    idx = 0
                else:
                    for i, btn in enumerate(self.btn_color):
                        col = self.btn_color[i].GetBackgroundColour()
                        if nodecol == col:
                            idx = i
                            break

        for i, label in enumerate(self.lbl_color):
            if i == idx:
                label.SetLabel("x")
            else:
                label.SetLabel("")
        self.Layout()

class IdPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.node = node
        self.text_id = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_label = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_id_label = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_id = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Id")), wx.VERTICAL
        )
        self.sizer_id.Add(self.text_id, 1, wx.EXPAND, 0)
        self.sizer_label = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Label")), wx.VERTICAL
        )
        self.sizer_label.Add(self.text_label, 1, wx.EXPAND, 0)
        sizer_id_label.Add(self.sizer_id, 1, wx.EXPAND, 0)
        sizer_id_label.Add(self.sizer_label, 1, wx.EXPAND, 0)

        main_sizer.Add(sizer_id_label, 0, wx.EXPAND, 0)

        self.SetSizer(main_sizer)
        self.Layout()
        self.text_id.Bind(wx.EVT_KILL_FOCUS, self.on_text_id_change)
        self.text_id.Bind(wx.EVT_TEXT_ENTER, self.on_text_id_change)
        self.text_label.Bind(wx.EVT_KILL_FOCUS, self.on_text_label_change)
        self.text_label.Bind(wx.EVT_TEXT_ENTER, self.on_text_label_change)
        self.set_widgets(self.node)

    def on_text_id_change(self, event=None):
        try:
            self.node.id = self.text_id.GetValue()
            self.context.elements.signal("element_property_update", self.node)
        except AttributeError:
            pass

    def on_text_label_change(self, event=None):
        try:
            self.node.label = self.text_label.GetValue()
            self.context.elements.signal("element_property_update", self.node)
        except AttributeError:
            pass

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def set_widgets(self, node):
        def mklabel(value):
            res = ""
            if value is not None:
                res = str(value)
            return res

        self.node = node
        # print(f"set_widget for {self.attribute} to {str(node)}")
        vis1 = False
        vis2 = False
        if hasattr(self.node, "id"):
            vis1 = True
            self.text_id.SetValue(mklabel(node.id))
        self.text_id.Show(vis1)
        if hasattr(self.node, "label"):
            vis2 = True
            self.text_label.SetValue(mklabel(node.label))

        self.text_label.Show(vis2)
        if vis1 or vis2:
            self.Show()
        else:
            self.Hide()
