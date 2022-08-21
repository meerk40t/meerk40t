import wx

from meerk40t.gui.wxutils import ScrolledPanel

# from ...svgelements import SVG_ATTR_ID
from ..icons import icons8_group_objects_50
from ..mwindow import MWindow

_ = wx.GetTranslation


class GroupPropertiesPanel(ScrolledPanel):
    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        self.node = node

        self.text_id = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_label = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)

        self.__set_properties()
        self.__do_layout()

        try:
            if node.id is not None:
                self.text_id.SetValue(str(node.id))
        except AttributeError:
            pass

        try:
            if node.label is not None:
                self.text_label.SetValue(str(node.label))
        except AttributeError:
            pass

        self.text_id.Bind(wx.EVT_KILL_FOCUS, self.on_text_id_change)
        self.text_id.Bind(wx.EVT_TEXT_ENTER, self.on_text_id_change)
        self.text_label.Bind(wx.EVT_KILL_FOCUS, self.on_text_label_change)
        self.text_label.Bind(wx.EVT_TEXT_ENTER, self.on_text_label_change)
        # end wxGlade

    def __set_properties(self):
        pass

    def __do_layout(self):
        # begin wxGlade: GroupProperty.__do_layout
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Label")), wx.VERTICAL
        )
        sizer_1 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Id")), wx.VERTICAL)
        sizer_1.Add(self.text_id, 0, wx.EXPAND, 0)
        sizer_8.Add(sizer_1, 0, wx.EXPAND, 0)
        sizer_2.Add(self.text_label, 0, wx.EXPAND, 0)
        sizer_8.Add(sizer_2, 0, wx.EXPAND, 0)
        sizer_8.Add((0, 0), 0, 0, 0)
        self.SetSizer(sizer_8)
        self.Layout()
        self.Centre()
        # end wxGlade

    def on_text_id_change(self, event=None):  # wxGlade: ElementProperty.<event_handler>
        try:
            self.node.id = self.text_id.GetValue()
            # self.node.values[SVG_ATTR_ID] = self.node.id
            self.context.signal("element_property_update", self.node)
        except AttributeError:
            pass

    def on_text_label_change(
        self, event=None
    ):  # wxGlade: ElementProperty.<event_handler>
        if len(self.text_label.GetValue()):
            try:
                self.node.label = self.text_label.GetValue()
            except AttributeError:
                # Can throw an error if non valid
                pass
        else:
            self.node.label = None
        self.context.elements.signal("element_property_update", self.node)


class GroupProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(372, 141, *args, **kwds)

        self.panel = GroupPropertiesPanel(
            self, wx.ID_ANY, context=self.context, node=node
        )
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_group_objects_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Group Properties"))

    def delegate(self):
        yield self.panel

    def window_preserve(self):
        return False

    def window_menu(self):
        return False
