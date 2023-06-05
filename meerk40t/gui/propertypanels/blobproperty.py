import wx

from meerk40t.gui.wxutils import ScrolledPanel

from ..icons import icons8_vector_50
from ..mwindow import MWindow
from .attributes import IdPanel

_ = wx.GetTranslation


class BlobPropertyPanel(ScrolledPanel):
    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node
        self.hex_content = ""
        self.ascii_content = ""
        self.panel_id = IdPanel(
            self, id=wx.ID_ANY, context=self.context, node=self.operation
        )
        optview = (_("Hexadecimal View"), _("Plain-Text"))
        self.option_view = wx.RadioBox(
            self, wx.ID_ANY, label="View", choices=optview, style=wx.RA_SPECIFY_COLS
        )
        self.option_view.SetSelection(0)
        self.text_blob = wx.TextCtrl(
            self, id=wx.ID_ANY, value="", style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.option_view.Bind(wx.EVT_RADIOBOX, self.on_option_view)
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
        self.on_option_view(None)
        self.Refresh()

    def fill_text(self):
        self.hex_content = ""
        self.ascii_content = ""
        if self.operation is None:
            return
        data = self.operation.data
        hexcodes = ""
        cleartext = ""
        data_len = 0
        if data is not None:
            offset = 0
            index = 0
            hexcodes = hex(offset)[2:]
            while len(hexcodes) < 6:
                hexcodes = "0" + hexcodes
            hexcodes += " |"
            cleartext = ""

            for entry in data:
                if isinstance(entry, bytes):
                    self.ascii_content += entry.decode("utf-8")
                    for single in entry:
                        data_len += 1
                        code = int(single)
                        hexa = hex(code)[2:]
                        while len(hexa) < 2:
                            hexa = "0" + hexa
                        hexcodes += " " + hexa
                        if code >= 32:
                            cleartext += chr(code)
                        else:
                            cleartext += "."
                        index += 1
                        offset += 1
                        if index >= 16:
                            hexcodes += " | " + cleartext + "\n"
                            self.hex_content += hexcodes
                            index = 0
                            hexcodes = hex(offset)[2:]
                            while len(hexcodes) < 6:
                                hexcodes = "0" + hexcodes
                            hexcodes += " |"
                            cleartext = ""

            # Still something to add?
            if index > 0:
                while index < 16:
                    hexcodes += "   "
                    cleartext += " "
                    index += 1
                hexcodes += " | " + cleartext + "\n"
                self.hex_content += hexcodes

        header1 = f"Data-Type: {self.operation.data_type}, Length={data_len}\n"
        header2 = "Offset | Hex                                             | Ascii          \n"
        header2 += "-------+-------------------------------------------------+----------------\n"
        self.hex_content = header1 + header2 + self.hex_content
        self.ascii_content = header1 + self.ascii_content

    def on_option_view(self, event):
        hex_view = bool(self.option_view.GetSelection() == 0)
        if hex_view:
            self.text_blob.SetValue(self.hex_content)
        else:
            self.text_blob.SetValue(self.ascii_content)

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
        sizer_v_main.Add(self.option_view, 0, wx.EXPAND, 0)
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

        self.panel = BlobPropertyPanel(self, wx.ID_ANY, context=self.context, node=node)
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
