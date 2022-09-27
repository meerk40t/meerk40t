import wx

from meerk40t.gui.wxutils import ScrolledPanel

from ...core.units import Length
from ..icons import icons8_vector_50
from ..mwindow import MWindow
from .attributes import ColorPanel, IdPanel, PositionSizePanel

_ = wx.GetTranslation

class PointPropertyPanel(ScrolledPanel):
    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.setting(
            bool, "_auto_classify", self.context.elements.classify_on_color
        )
        self.node = node

        self.panel_id = IdPanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.panel_stroke = ColorPanel(
            self,
            id=wx.ID_ANY,
            context=self.context,
            label="Stroke:",
            attribute="stroke",
            callback=self.callback_color,
            node=self.node,
        )
        self.panel_fill = ColorPanel(
            self,
            id=wx.ID_ANY,
            context=self.context,
            label="Fill:",
            attribute="fill",
            callback=self.callback_color,
            node=self.node,
        )
        self.panel_xy = PositionSizePanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )

        self.check_classify = wx.CheckBox(
            self, wx.ID_ANY, _("Immediately classify after colour change")
        )
        self.check_classify.SetValue(self.context._auto_classify)

        self.__set_properties()
        self.__do_layout()


    @staticmethod
    def accepts(node):
        if node.type == "elem point":
            return True
        else:
            return False

    def set_widgets(self, node):
        self.panel_id.set_widgets(node)
        self.panel_stroke.set_widgets(node)
        self.panel_fill.set_widgets(node)
        self.panel_xy.set_widgets(node)

        if node is not None:
            self.node = node
        self.Refresh()

    def __set_properties(self):
        return

    def __do_layout(self):
        # begin wxGlade: PointProperty.__do_layout
        sizer_v_main = wx.BoxSizer(wx.VERTICAL)

        sizer_v_main.Add(self.panel_id, 0, wx.EXPAND, 0)
        sizer_v_main.Add(self.panel_stroke, 0, wx.EXPAND, 0)
        sizer_v_main.Add(self.panel_fill, 0, wx.EXPAND, 0)
        sizer_v_main.Add(self.check_classify, 0, 0, 0)
        sizer_v_main.Add(self.panel_xy, 0, wx.EXPAND, 0)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_classify, self.check_classify)
        self.SetSizer(sizer_v_main)
        self.Layout()
        self.Centre()
        # end wxGlade

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

class PointProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(288, 303, *args, **kwds)

        self.panel = PointPropertyPanel(self, wx.ID_ANY, context=self.context, node=node)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_vector_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: PointProperty.__set_properties
        self.SetTitle(_("Point Properties"))

    def restore(self, *args, node=None, **kwds):
        self.panel.set_widgets(node)

    def window_preserve(self):
        return False

    def window_menu(self):
        return False
