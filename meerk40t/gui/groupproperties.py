import wx

from ..svgelements import SVG_ATTR_ID
from .icons import icons8_group_objects_50
from .mwindow import MWindow

_ = wx.GetTranslation


class GroupProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(372, 141, *args, **kwds)

        self.element = node.object
        self.element_node = node

        self.text_id = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_label = wx.TextCtrl(self, wx.ID_ANY, "")

        self.__set_properties()
        self.__do_layout()

        try:
            if node.object.id is not None:
                self.text_id.SetValue(str(node.object.id))
        except AttributeError:
            pass

        try:
            if node.label is not None:
                self.text_label.SetValue(str(node.label))
        except AttributeError:
            pass

        self.Bind(wx.EVT_TEXT, self.on_text_id_change, self.text_id)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_id_change, self.text_id)
        self.Bind(wx.EVT_TEXT, self.on_text_label_change, self.text_label)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_label_change, self.text_label)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: GroupProperty.__set_properties
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_group_objects_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Group Properties"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: GroupProperty.__do_layout
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Label")), wx.VERTICAL)
        sizer_1 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Id")), wx.VERTICAL)
        sizer_1.Add(self.text_id, 0, wx.EXPAND, 0)
        sizer_8.Add(sizer_1, 1, wx.EXPAND, 0)
        sizer_2.Add(self.text_label, 0, wx.EXPAND, 0)
        sizer_8.Add(sizer_2, 1, wx.EXPAND, 0)
        sizer_8.Add((0, 0), 0, 0, 0)
        self.SetSizer(sizer_8)
        self.Layout()
        self.Centre()
        # end wxGlade

    def on_text_id_change(
        self, event=None
    ):  # wxGlade: ElementProperty.<event_handler>
        try:
            self.element.id = self.text_id.GetValue()
            self.element.values[SVG_ATTR_ID] = self.element.id
            # self.context.signal("element_property_update", self.element)
        except AttributeError:
            pass

    def on_text_label_change(
            self, event=None
    ):  # wxGlade: ElementProperty.<event_handler>
        if len(self.text_label.GetValue()):
            self.element_node.label = self.text_label.GetValue()
            self.element.values["label"] = self.element_node.label
        else:
            self.element_node.label = None
            try:
                del self.element.values["label"]
            except KeyError:
                pass
        self.context.signal("element_property_update", self.element)

# end of class GroupProperty