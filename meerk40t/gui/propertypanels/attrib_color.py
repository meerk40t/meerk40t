import wx
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.svgelements import Color

_ = wx.GetTranslation

class ColorPanel(wx.Panel):
    def __init__(self, *args, context=None, label=None, attribute=None, callback=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.callback = callback
        if attribute is None:
            attribute = "stroke"
        self.attribute = attribute

        main_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _(label)), wx.VERTICAL
        )
        color_sizer = wx.BoxSizer(wx.HORIZONTAL)
        label_sizer = wx.BoxSizer(wx.HORIZONTAL)
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
        if self.node is None or not self.accepts(node):
            self.Hide()
            return
        self.mark_color(None)
        self.Show()

    def mark_color(self, idx):
        if idx is None:    # Okay, we need to determine it ourselves
            idx = -1
            value = getattr(self.node, self.attribute, None)
            if value == "none":
                value = None
            if value is None:
                idx = 0
            else:
                nodecol = wx.Colour(swizzlecolor(value))
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

