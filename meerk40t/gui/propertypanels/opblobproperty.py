import wx

from meerk40t.gui.wxutils import ScrolledPanel

from ...core.units import Length
from ..icons import icons8_vector_50
from ..mwindow import MWindow
from .attributes import ColorPanel, IdPanel, PositionSizePanel, PreventChangePanel

_ = wx.GetTranslation


class BlobPropertyPanel(ScrolledPanel):
    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        self.panel_id = IdPanel(
            self, id=wx.ID_ANY, context=self.context, node=self.operation
        )
        self.text_blob = wx.TextCtrl(self, id=wx.ID_ANY, value="", style = wx.TE_MULTILINE | wx.TE_READONLY)

        self.__set_properties()
        self.__do_layout()

    @staticmethod
    def accepts(node):
        if node.type == "blob":
            return True
        else:
            return False

    def set_widgets(self, node):
        self.panel_id.set_widgets(node)

        if node is not None:
            self.operation = node
        self.fill_text()
        self.Refresh()

    def fill_text(self):
        self.text_blob.SetValue("")
        if self.operation is None:
            return
        content = ""
        data = self.operation.data
        debug = 0
        if data is not None:
            d = len(data)
            buffer = []
            for entry in data:
                # if debug <= 2:
                #     print (f"Data, {type(entry).__name__}: {entry}")
                if isinstance(entry, (list, tuple, str, bytes)):
                    for single in entry:
                        # if debug <= 2:
                        #     print (f"Single: {single}, {type(single).__name__}, {chr(single)}")
                        buffer.append(single)
                else:
                    buffer.append(entry)
                debug += 1
            # print (buffer)
            d = len(buffer)
        else:
            d = 0
        content += f"Data-Type: {self.operation.data_type}, Length={d}\n"
        content += "Offset | Hex                                             | Ascii          \n"
        content += "-------+-------------------------------------------------+----------------\n"
        offset = 0
        while offset < d:
            hexcodes = hex(offset)[2:]
            while len(hexcodes) < 6:
                hexcodes = "0" + hexcodes
            hexcodes += " |"
            cleartext = ""
            for bnum in range(16):
                idx = offset + bnum
                hexcodes += " "
                if idx < d:
                    code = int(buffer[idx])
                    hexa = hex(code)[2:]
                    while len(hexa) < 2:
                        hexa = "0" + hexa
                    hexcodes += hexa
                    if code >= 32:
                        cleartext += chr(code)
                    else:
                        cleartext += "."
                else:
                    hexcodes += "  "
                    cleartext += " "
            hexcodes += " | " + cleartext + "\n"
            content += hexcodes
            offset += 16
        self.text_blob.SetValue(content)

    def __set_properties(self):
        self.text_blob.SetFont(
            wx.Font(
                8,
                wx.FONTFAMILY_TELETYPE,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )

    def __do_layout(self):
        # begin wxGlade: PointProperty.__do_layout
        sizer_v_main = wx.BoxSizer(wx.VERTICAL)

        sizer_v_main.Add(self.panel_id, 0, wx.EXPAND, 0)
        sizer_v_main.Add(self.text_blob, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_v_main)
        self.Layout()
        self.Centre()
        # end wxGlade

    def update_label(self):
        return

class BlobProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(288, 303, *args, **kwds)

        self.panel = BlobPropertyPanel(
            self, wx.ID_ANY, context=self.context, node=node
        )
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_vector_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Blob Properties"))

    def restore(self, *args, node=None, **kwds):
        self.panel.set_widgets(node)

    def window_preserve(self):
        return False

    def window_menu(self):
        return False
