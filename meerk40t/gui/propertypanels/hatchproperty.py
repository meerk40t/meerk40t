import wx

from meerk40t.gui.wxutils import ScrolledPanel, StaticBoxSizer

from ...core.units import Length
from ...svgelements import Angle
from ..wxutils import TextCtrl, set_ctrl_value
from .attributes import IdPanel, ColorPanel

_ = wx.GetTranslation


class HatchPropertyPanel(ScrolledPanel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # super().__init__(parent)
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.setting(
            bool, "_auto_classify", self.context.elements.classify_on_color
        )
        self.node = node

        self._Buffer = None

        main_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Hatch:"), wx.VERTICAL)

        # `Id` at top in all cases...
        panel_id = IdPanel(self, id=wx.ID_ANY, context=self.context, node=self.node)
        main_sizer.Add(panel_id, 1, wx.EXPAND, 0)

        panel_stroke = ColorPanel(
            self,
            id=wx.ID_ANY,
            context=self.context,
            label="Stroke:",
            attribute="stroke",
            callback=self.callback_color,
            node=self.node,
        )
        main_sizer.Add(panel_stroke, 1, wx.EXPAND, 0)

        panel_fill = ColorPanel(
            self,
            id=wx.ID_ANY,
            context=self.context,
            label="Fill:",
            attribute="fill",
            callback=self.callback_color,
            node=self.node,
        )
        main_sizer.Add(panel_fill, 1, wx.EXPAND, 0)

        sizer_distance = StaticBoxSizer(
            self, wx.ID_ANY, _("Hatch Distance:"), wx.HORIZONTAL
        )
        main_sizer.Add(sizer_distance, 0, wx.EXPAND, 0)

        self.text_distance = TextCtrl(
            self,
            wx.ID_ANY,
            str(node.hatch_distance),
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        sizer_distance.Add(self.text_distance, 1, wx.EXPAND, 0)

        sizer_angle = StaticBoxSizer(self, wx.ID_ANY, _("Angle"), wx.HORIZONTAL)

        self.text_angle = TextCtrl(
            self,
            wx.ID_ANY,
            str(node.hatch_angle),
            limited=True,
            check="angle",
            style=wx.TE_PROCESS_ENTER,
        )
        sizer_angle.Add(self.text_angle, 1, wx.EXPAND, 0)

        self.slider_angle = wx.Slider(self, wx.ID_ANY, 0, 0, 360)
        sizer_angle.Add(self.slider_angle, 3, wx.EXPAND, 0)
        main_sizer.Add(sizer_angle, 1, wx.EXPAND, 0)

        self.check_classify = wx.CheckBox(
            self, wx.ID_ANY, _("Immediately classify after colour change")
        )
        self.check_classify.SetValue(self.context._auto_classify)
        main_sizer.Add(self.check_classify, 1, wx.EXPAND, 0)

        self.SetSizer(main_sizer)

        self.text_distance.SetActionRoutine(self.on_text_distance)
        self.text_angle.SetActionRoutine(self.on_text_angle)

        self.Bind(wx.EVT_COMMAND_SCROLL, self.on_slider_angle, self.slider_angle)
        self.Layout()

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    @staticmethod
    def accepts(node):
        return node.type in ("effect hatch",)

    def set_widgets(self, node):
        self.node = node
        if self.node is None or not self.accepts(node):
            self.Hide()
            return
        set_ctrl_value(self.text_angle, str(self.node.hatch_angle))
        set_ctrl_value(self.text_distance, str(self.node.hatch_distance))
        try:
            h_angle = float(Angle.parse(self.node.hatch_angle).as_degrees)
            self.slider_angle.SetValue(int(h_angle))
        except ValueError:
            pass
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
            self.context.elements.signal("element_property_update", self.node)
            mynode.emphasized = wasemph
            self.set_widgets(mynode)

    def on_text_distance(self):
        try:
            self.node.distance = Length(
                self.text_distance.GetValue()
            ).length_mm
            self.node.modified()
        except ValueError:
            pass

    def on_text_angle(self):
        try:
            angle = f"{Angle.parse(self.text_angle.GetValue()).as_degrees}deg"
            if angle == self.node.hatch_angle:
                return
            self.node.angle = angle
            self.node.modified()
        except ValueError:
            return
        try:
            h_angle = float(Angle.parse(self.node.hatch_angle).as_degrees)
            while h_angle > self.slider_angle.GetMax():
                h_angle -= 360
            while h_angle < self.slider_angle.GetMin():
                h_angle += 360
            self.slider_angle.SetValue(int(h_angle))
        except ValueError:
            pass

    def on_slider_angle(self, event):
        value = self.slider_angle.GetValue()
        self.text_angle.SetValue(f"{value}deg")
        self.on_text_angle()
