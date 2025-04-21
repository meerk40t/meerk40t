import wx

from meerk40t.gui.icons import icons8_finger
from meerk40t.gui.wxutils import (
    ScrolledPanel,
    StaticBoxSizer,
    wxCheckBox,
    wxStaticBitmap,
    wxStaticText,
)

from .attributes import AutoHidePanel, ColorPanel, IdPanel

_ = wx.GetTranslation


class WarpPropertyPanel(ScrolledPanel):
    """
    Minimal property page for warp-effects
    """
    def __init__(self, *args, context=None, node=None, **kwds):
        # super().__init__(parent)
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node
        self.context.setting(
            bool, "_auto_classify", self.context.elements.classify_on_color
        )

        self.SetHelpText("warp")

        main_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Wobble:"), wx.VERTICAL)
        self.panels = []
        # `Id` at top in all cases...
        panel_id = IdPanel(self, id=wx.ID_ANY, context=self.context, node=self.node)
        main_sizer.Add(panel_id, 0, wx.EXPAND, 0)
        self.panels.append(panel_id)

        panel_hide = AutoHidePanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        main_sizer.Add(panel_hide, 0, wx.EXPAND, 0)
        self.panels.append(panel_hide)

        panel_stroke = ColorPanel(
            self,
            id=wx.ID_ANY,
            context=self.context,
            label="Stroke:",
            attribute="stroke",
            callback=self.callback_color,
            node=self.node,
        )
        main_sizer.Add(panel_stroke, 0, wx.EXPAND, 0)
        self.panels.append(panel_stroke)

        self.check_classify = wxCheckBox(
            self, wx.ID_ANY, _("Immediately classify after colour change")
        )
        self.check_classify.SetValue(self.context._auto_classify)
        main_sizer.Add(self.check_classify, 0, wx.EXPAND, 0)

        sizer_instructions = StaticBoxSizer(
            self, wx.ID_ANY, _("Instructions:"), wx.HORIZONTAL
        )
        content = _("Use the finger tool to modify the containing shape of the warped children")
        label_instructions = wxStaticText(self, wx.ID_ANY, content)
        iconsize = 40
        finger_icon = wxStaticBitmap(self, wx.ID_ANY, size=wx.Size(iconsize, iconsize))
        finger_icon.SetBitmap(icons8_finger.GetBitmap(resize=iconsize * self.context.root.bitmap_correction_scale))
        sizer_instructions.Add(finger_icon, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_instructions.Add(label_instructions, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        main_sizer.Add(sizer_instructions, 0, wx.EXPAND, 0)
        self.SetSizer(main_sizer)

        self.Layout()
        self.check_classify.Bind(wx.EVT_CHECKBOX, self.on_check_classify)

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    @staticmethod
    def accepts(node):
        return node.type in ("effect warp",)

    def set_widgets(self, node):
        for panel in self.panels:
            panel.set_widgets(node)
        self.node = node
        if self.node is None or not self.accepts(node):
            self.Hide()
            return
        self.Show()

    def on_check_classify(self, event):
        self.context._auto_classify = self.check_classify.GetValue()

    def update_label(self):
        return

    def callback_color(self):
        self.node.altered()
        self.update_label()
        self.Refresh()
        if self.check_classify.GetValue():
            mynode = self.node
            wasemph = self.node.emphasized
            self.context("declassify\nclassify\n")
            self.context.elements.signal("tree_changed")
            self.context.elements.signal("element_property_reload", self.node)
            mynode.emphasized = wasemph
            self.set_widgets(mynode)

    def update(self):
        self.node.modified()
        self.context.elements.signal("element_property_reload", self.node)
