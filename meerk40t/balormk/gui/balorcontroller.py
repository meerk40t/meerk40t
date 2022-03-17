import wx

from meerk40t.gui.icons import icons8_connected_50, icons8_disconnected_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class BalorController(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(499, 170, *args, **kwds)
        self.button_device_connect = wx.Button(self, wx.ID_ANY, _("Connection"))
        self.service = self.context.device
        self.log_append = ""
        self.text_status = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_usb_log = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_BUTTON, self.on_button_start_connection, self.button_device_connect
        )
        # end wxGlade
        self.max = 0
        self.state = None

    def __set_properties(self):
        # begin wxGlade: Controller.__set_properties
        self.SetTitle(_("Balor-Controller"))
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_connected_50.GetBitmap())
        self.SetIcon(_icon)
        self.button_device_connect.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.button_device_connect.SetForegroundColour(wx.BLACK)
        self.button_device_connect.SetFont(
            wx.Font(
                12,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        self.button_device_connect.SetToolTip(
            _("Force connection/disconnection from the device.")
        )
        self.button_device_connect.SetBitmap(
            icons8_disconnected_50.GetBitmap(use_theme=False)
        )
        # end wxGlade

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        connection_controller = wx.BoxSizer(wx.VERTICAL)
        connection_controller.Add(self.button_device_connect, 0, wx.EXPAND, 0)
        sizer_1.Add(connection_controller, 0, wx.EXPAND, 0)
        static_line_2 = wx.StaticLine(self, wx.ID_ANY)
        static_line_2.SetMinSize((483, 5))
        sizer_1.Add(static_line_2, 0, wx.EXPAND, 0)
        sizer_1.Add(self.text_usb_log, 5, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()

    def window_open(self):
        self.context.channel("balor", buffer_size=500).watch(self.update_text)

    def window_close(self):
        self.context.channel("balor").unwatch(self.update_text)

    def update_text(self, text):
        self.log_append += text + "\n"
        self.context.signal("usb_log_update")

    @signal_listener("usb_log_update")
    def update_text_gui(self, origin):
        try:
            self.text_usb_log.AppendText(self.log_append)
            self.log_append = ""
        except RuntimeError:
            pass

    @signal_listener("pipe;usb_status")
    def on_usb_update(self, origin=None, status=None):
        if status == None:
            status = "Unknown"
        try:
            connected = self.context.device.driver.connected
        except AttributeError:
            return
        self.button_device_connect.SetLabel(status)
        if connected:
            self.button_device_connect.SetBackgroundColour("#00ff00")
            self.button_device_connect.SetBitmap(
                icons8_connected_50.GetBitmap(use_theme=False)
            )
            self.button_device_connect.Enable()
        else:
            self.button_device_connect.SetBackgroundColour("#dfdf00")
            self.button_device_connect.SetBitmap(
                icons8_disconnected_50.GetBitmap(use_theme=False)
            )
            self.button_device_connect.Enable()

    def on_button_start_connection(self, event):  # wxGlade: Controller.<event_handler>
        try:
            connected = self.context.device.driver.connected
        except AttributeError:
            return
        if connected:
            self.context("usb_disconnect\n")
        else:
            self.context("usb_connect\n")
