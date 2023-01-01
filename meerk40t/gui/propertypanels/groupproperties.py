import os
import time

import wx

from meerk40t.gui.wxutils import ScrolledPanel

# from ...svgelements import SVG_ATTR_ID
from ..icons import icons8_group_objects_50
from ..mwindow import MWindow
from ..wxutils import StaticBoxSizer
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


class FilePropertiesPanel(ScrolledPanel):
    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        self.node = node
        self.text_filename = wx.TextCtrl(self, id=wx.ID_ANY, style=wx.TE_READONLY)
        self.text_path = wx.TextCtrl(self, id=wx.ID_ANY, style=wx.TE_READONLY)
        self.text_datetime = wx.TextCtrl(self, id=wx.ID_ANY, style=wx.TE_READONLY)
        self.text_size = wx.TextCtrl(self, id=wx.ID_ANY, style=wx.TE_READONLY)
        self.__set_properties()
        self.__do_layout()

        # end wxGlade

    def __set_properties(self):
        pass

    def __do_layout(self):
        # begin wxGlade: GroupProperty.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer1 = StaticBoxSizer(self, wx.ID_ANY, _("Filename:"), wx.HORIZONTAL)
        sizer1.Add(self.text_filename, 1, wx.EXPAND, 0)
        sizer2 = StaticBoxSizer(self, wx.ID_ANY, _("Path:"), wx.HORIZONTAL)
        sizer2.Add(self.text_path, 1, wx.EXPAND, 0)
        sizer3 = StaticBoxSizer(self, wx.ID_ANY, _("Size:"), wx.HORIZONTAL)
        sizer3.Add(self.text_size, 1, wx.EXPAND, 0)
        sizer4 = StaticBoxSizer(self, wx.ID_ANY, _("Date:"), wx.HORIZONTAL)
        sizer4.Add(self.text_datetime, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer1, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer2, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer3, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer4, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.Layout()
        self.Centre()
        # end wxGlade

    def set_widgets(self, node):
        self.node = node
        if self.node is None:
            text1 = ""
            text2 = ""
            text3 = ""
            text4 = ""
        else:
            fname = self.node.filepath
            if fname is not None:
                try:
                    text1 = os.path.basename(fname)
                    text2 = os.path.dirname(fname)
                except (PermissionError, OSError, FileNotFoundError):
                    text1 = fname
                    text2 = _("File not found")
                    fname = None
            if fname is not None:
                try:
                    fsize = os.path.getsize(fname)
                    ftime = os.path.getctime(fname)
                    mtime = os.path.getmtime(fname)
                    c_ti = time.ctime(ftime)
                    m_ti = time.ctime(mtime)
                    text3 = f"{fsize:,} bytes"
                    c1 = _("Created:")
                    c2 = _("Modified:")
                    text4 = f"{c1} {c_ti}, {c2} {m_ti}"
                except (PermissionError, OSError, FileNotFoundError):
                    pass
        self.text_filename.SetValue(text1)
        self.text_path.SetValue(text2)
        self.text_size.SetValue(text3)
        self.text_datetime.SetValue(text4)


class FileProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(372, 141, *args, **kwds)

        self.panel = FilePropertiesPanel(
            self, wx.ID_ANY, context=self.context, node=node
        )
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_group_objects_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("File Properties"))

    def restore(self, *args, node=None, **kwds):
        self.panel.set_widgets(node)

    def window_preserve(self):
        return False

    def window_menu(self):
        return False
