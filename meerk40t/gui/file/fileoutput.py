
import wx

from meerk40t.gui.icons import icons8_file_50
from meerk40t.gui.mwindow import MWindow

_ = wx.GetTranslation


class FileOutput(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(312, 155, *args, **kwds)
        self.spooler, self.input_driver, self.output = self.context.registered["device/%s" % self.context.root.active]
        self.text_filename = wx.TextCtrl(self, wx.ID_ANY, "")
        self.radio_file = wx.RadioBox(self, wx.ID_ANY, "File", choices=["File Overwrite", "File Append", "File Increment"], majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.text_info = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TEXT, self.on_text_filename, self.text_filename)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_filename, self.text_filename)
        self.Bind(wx.EVT_RADIOBOX, self.on_radiobox_file, self.radio_file)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: Controller.__set_properties
        self.SetTitle("FileOutput")
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_file_50.GetBitmap())
        self.SetIcon(_icon)
        self.text_filename.SetToolTip("Output filename")
        self.radio_file.SetSelection(0)
        # end wxGlade
        self.radio_file.Enable(False)
        self.text_info.Enable(False)

    def __do_layout(self):
        # begin wxGlade: Controller.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        connection_controller = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_15 = wx.BoxSizer(wx.HORIZONTAL)
        label_8 = wx.StaticText(self, wx.ID_ANY, "Filename")
        sizer_15.Add(label_8, 1, 0, 0)
        sizer_15.Add(self.text_filename, 5, 0, 0)
        connection_controller.Add(sizer_15, 0, 0, 0)
        sizer_2.Add(self.radio_file, 0, 0, 0)
        sizer_2.Add(self.text_info, 1, wx.EXPAND, 0)
        connection_controller.Add(sizer_2, 1, wx.EXPAND, 0)
        sizer_1.Add(connection_controller, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def window_open(self):
        self.text_filename.SetValue(str(self.output.filename))
        self.context.listen("active", self.on_active_change)

    def window_close(self):
        self.context.unlisten("active", self.on_active_change)

    def on_active_change(self, origin, active):
        self.Close()

    def on_text_filename(self, event):  # wxGlade: Controller.<event_handler>
        self.output.filename = self.text_filename.GetValue()

    def on_radiobox_file(self, event):  # wxGlade: Controller.<event_handler>
        pass
