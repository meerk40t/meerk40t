import wx

from meerk40t.gui.wxutils import StaticBoxSizer, TextCtrl, wxButton
from meerk40t.gui.laserrender import DRAW_MODE_REGMARKS

_ = wx.GetTranslation


class RegBranchPanel(wx.Panel):
    name = "Regmarks"

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node
        self.text_elements = TextCtrl(self, id=wx.ID_ANY, style=wx.TE_READONLY)
        self.button_visible = wxButton(self, wx.ID_ANY, _("Toggle"))
        self.button_visible.SetToolTip(_("Toggle visibility of regmarks"))
        self.button_move_back = wxButton(self, wx.ID_ANY, _("Move all back"))
        self.button_move_back.SetToolTip(_("Move back to elements"))
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_id = StaticBoxSizer(self, wx.ID_ANY, _("Elements:"), wx.HORIZONTAL)
        sizer_id.Add(self.text_elements, 1, wx.EXPAND, 0)
        main_sizer.Add(sizer_id, 0, wx.EXPAND, 0)

        sizer_options = StaticBoxSizer(self, wx.ID_ANY, _("Options:"), wx.VERTICAL)
        line_sizer = wx.BoxSizer(wx.HORIZONTAL)
        line_sizer.Add(self.button_visible, 0, wx.EXPAND, 0)
        line_sizer.Add(self.button_move_back, 0, wx.EXPAND, 0)
        sizer_options.Add(line_sizer, 0, wx.EXPAND, 0)
        main_sizer.Add(sizer_options, 0, wx.EXPAND, 0)
        self.Bind(wx.EVT_BUTTON, self.on_visible, self.button_visible)
        self.Bind(wx.EVT_BUTTON, self.on_move_back, self.button_move_back)
        self.SetSizer(main_sizer)
        self.Layout()
        self.set_widgets(self.node)

    def on_visible(self, event):
        bits = DRAW_MODE_REGMARKS
        self.context.draw_mode ^= bits
        self.context.signal("draw_mode", self.context.draw_mode)
        self.context.signal("refresh_scene", "Scene")

    def on_move_back(self, event):
        elements = self.context.elements
        drop_node = elements.elem_branch
        data = list(elements.regmarks_nodes())
        if len(data):
            elements.drag_and_drop(data, drop_node)
        self.set_widgets(self.node)
        elements.set_selected([self.node])
        self.context.signal("selected")

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def set_widgets(self, node):
        def elem_count(enode):
            res = 0
            for e in enode.children:
                res += 1
                if e.type in ("file", "group"):
                    res += elem_count(e)
            return res

        self.node = node
        count = elem_count(self.node)
        self.text_elements.SetValue(_("{count} elements").format(count=count))
        self.button_move_back.Enable(count > 0)
