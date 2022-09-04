import wx

from meerk40t.gui.wxutils import ScrolledPanel

# from ...svgelements import SVG_ATTR_ID
from ..icons import icons8_group_objects_50
from ..mwindow import MWindow
from .attributes import IdPanel

_ = wx.GetTranslation


class GroupPropertiesPanel(ScrolledPanel):
    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        self.node = node
        self.panel_id = IdPanel(self, id=wx.ID_ANY, context=self.context, node=node)

        self.__set_properties()
        self.__do_layout()

        # end wxGlade

    def __set_properties(self):
        pass

    def __do_layout(self):
        # begin wxGlade: GroupProperty.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.panel_id, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.Layout()
        self.Centre()
        # end wxGlade

    def set_widgets(self, node):
        self.panel_id.set_widgets(node)
        self.node = node


class GroupProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(372, 141, *args, **kwds)

        self.panel = GroupPropertiesPanel(
            self, wx.ID_ANY, context=self.context, node=node
        )
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_group_objects_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Group Properties"))

    def restore(self, *args, node=None, **kwds):
        self.panel.set_widgets(node)

    def window_preserve(self):
        return False

    def window_menu(self):
        return False
