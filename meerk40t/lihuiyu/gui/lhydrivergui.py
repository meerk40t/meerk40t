# -*- coding: ISO-8859-1 -*-
import wx

from meerk40t.core.units import Length
from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.gui.icons import icons8_administrative_tools_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import ScrolledPanel, TextCtrl
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation

FIX_SPEEDS_RATIO = 0.9195


class ConfigurationUsb(wx.Panel):
    def __init__(self, *args, context=None, **kwds):

        # begin wxGlade: ConfigurationUsb.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_usb_settings = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("USB Settings")), wx.VERTICAL
        )

        sizer_usb_restrict = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Restrict Multiple Lasers")), wx.VERTICAL
        )
        sizer_usb_settings.Add(sizer_usb_restrict, 0, wx.EXPAND, 0)

        sizer_criteria = wx.BoxSizer(wx.HORIZONTAL)
        sizer_usb_restrict.Add(sizer_criteria, 1, wx.EXPAND, 0)

        sizer_chip_version = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("CH341 Version")), wx.HORIZONTAL
        )
        sizer_criteria.Add(sizer_chip_version, 0, wx.EXPAND, 0)

        self.text_device_version = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        sizer_chip_version.Add(self.text_device_version, 1, wx.EXPAND, 0)

        self.spin_device_version = wx.SpinCtrl(self, wx.ID_ANY, "-1", min=-1, max=25)
        self.spin_device_version.SetMinSize((40, -1))
        self.spin_device_version.SetToolTip(
            _(
                "Optional: Distinguish between different lasers using the match criteria below.\n-1 match anything. 0+ match exactly that value."
            )
        )
        sizer_chip_version.Add(self.spin_device_version, 0, wx.EXPAND, 0)

        sizer_device_index = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Device Index:")), wx.HORIZONTAL
        )
        sizer_criteria.Add(sizer_device_index, 0, wx.EXPAND, 0)

        self.text_device_index = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        sizer_device_index.Add(self.text_device_index, 1, wx.EXPAND, 0)

        self.spin_device_index = wx.SpinCtrl(self, wx.ID_ANY, "-1", min=-1, max=5)
        self.spin_device_index.SetMinSize((40, -1))
        self.spin_device_index.SetToolTip(
            _(
                "Optional: Distinguish between different lasers using the match criteria below.\n-1 match anything. 0+ match exactly that value."
            )
        )
        sizer_device_index.Add(self.spin_device_index, 0, wx.EXPAND, 0)

        sizer_serial = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Serial Number")), wx.HORIZONTAL
        )
        sizer_usb_restrict.Add(sizer_serial, 0, wx.EXPAND, 0)

        self.check_serial_number = wx.CheckBox(self, wx.ID_ANY, _("Serial Number"))
        self.check_serial_number.SetToolTip(
            _("Require a serial number match for this board")
        )
        sizer_serial.Add(self.check_serial_number, 0, wx.EXPAND, 0)

        self.text_serial_number = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )
        self.text_serial_number.SetMinSize((50, -1))
        self.text_serial_number.SetToolTip(
            _(
                "Board Serial Number to be used to identify a specific laser. If the device fails to match the serial number it will be disconnected."
            )
        )
        sizer_serial.Add(self.text_serial_number, 1, wx.EXPAND, 0)

        sizer_buffer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Write Buffer")), wx.HORIZONTAL
        )
        sizer_usb_settings.Add(sizer_buffer, 0, wx.EXPAND, 0)

        self.checkbox_limit_buffer = wx.CheckBox(
            self, wx.ID_ANY, _("Limit Write Buffer")
        )
        self.checkbox_limit_buffer.SetToolTip(
            _(
                "Limit the write buffer to a certain amount. Permits on-the-fly command production."
            )
        )
        self.checkbox_limit_buffer.SetValue(1)
        sizer_buffer.Add(self.checkbox_limit_buffer, 0, 0, 0)

        self.text_buffer_length = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY, limited=True
        )
        self.text_buffer_length.SetToolTip(
            _("Current number of bytes in the write buffer.")
        )
        sizer_buffer.Add(self.text_buffer_length, 1, wx.EXPAND, 0)

        label_14 = wx.StaticText(self, wx.ID_ANY, "/")
        sizer_buffer.Add(label_14, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.spin_packet_buffer_max = wx.SpinCtrl(
            self, wx.ID_ANY, "1500", min=1, max=1000000
        )
        self.spin_packet_buffer_max.SetToolTip(_("Current maximum write buffer limit."))
        self.spin_packet_buffer_max.SetMaxSize((100, -1))
        sizer_buffer.Add(self.spin_packet_buffer_max, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_usb_settings)

        self.Layout()

        self.Bind(
            wx.EVT_SPINCTRL, self.spin_on_device_version, self.spin_device_version
        )
        self.Bind(
            wx.EVT_TEXT_ENTER, self.spin_on_device_version, self.spin_device_version
        )
        self.Bind(wx.EVT_SPINCTRL, self.spin_on_device_index, self.spin_device_index)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_device_index, self.spin_device_index)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_serial_number, self.check_serial_number
        )
        self.text_serial_number.SetActionRoutine(self.on_text_serial_number)
        self.Bind(
            wx.EVT_CHECKBOX,
            self.on_check_limit_packet_buffer,
            self.checkbox_limit_buffer,
        )
        self.Bind(
            wx.EVT_SPINCTRL, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max
        )
        self.Bind(
            wx.EVT_TEXT, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max
        )
        self.Bind(
            wx.EVT_TEXT_ENTER,
            self.on_spin_packet_buffer_max,
            self.spin_packet_buffer_max,
        )
        # end wxGlade
        self.spin_device_index.SetValue(self.context.usb_index)
        self.spin_device_version.SetValue(self.context.usb_version)
        if self.context.serial is not None:
            self.text_serial_number.SetValue(self.context.serial)
        self.check_serial_number.SetValue(self.context.serial_enable)
        self.checkbox_limit_buffer.SetValue(self.context.buffer_limit)
        self.spin_packet_buffer_max.SetValue(self.context.buffer_max)

        # Disables of features not yet supported.
        self.check_serial_number.Enable(False)
        self.text_serial_number.Enable(False)

    def pane_show(self):
        # self.context.listen("pipe;buffer", self.on_buffer_update)
        pass

    def pane_hide(self):
        # self.context.unlisten("pipe;buffer", self.on_buffer_update)
        pass

    @signal_listener("pipe;buffer")
    def on_buffer_update(self, origin, value, *args):
        self.text_buffer_length.SetValue(str(value))

    @signal_listener("pipe;index")
    def on_update_pipe_index(self, origin, value):
        if origin != self.context.path:
            return
        self.text_device_index.SetValue(str(value))

    @signal_listener("pipe;chipv")
    def on_update_pipe_chipv(self, origin, value):
        if origin != self.context.path:
            return
        self.text_device_version.SetValue(str(value))

    def on_check_limit_packet_buffer(
        self, event=None
    ):  # wxGlade: JobInfo.<event_handler>
        self.context.buffer_limit = self.checkbox_limit_buffer.GetValue()

    def on_spin_packet_buffer_max(self, event=None):  # wxGlade: JobInfo.<event_handler>
        self.context.buffer_max = self.spin_packet_buffer_max.GetValue()

    def spin_on_device_index(self, event=None):
        self.context.usb_index = int(self.spin_device_index.GetValue())

    def spin_on_device_version(self, event=None):
        self.context.usb_version = int(self.spin_device_version.GetValue())

    def on_check_serial_number(
        self, event
    ):  # wxGlade: ConfigurationUsb.<event_handler>
        self.context.serial_enable = self.check_serial_number.GetValue()

    def on_text_serial_number(self):
        self.context.serial = self.text_serial_number.GetValue()


class ConfigurationTcp(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationTcp.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_13 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("TCP Settings")), wx.HORIZONTAL
        )

        h_sizer_y1 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Address")), wx.VERTICAL
        )
        sizer_13.Add(h_sizer_y1, 3, wx.EXPAND, 0)

        self.text_address = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_address.SetMinSize((75, -1))
        self.text_address.SetToolTip(_("IP/Host if the server computer"))
        h_sizer_y1.Add(self.text_address, 1, wx.EXPAND, 0)

        sizer_port = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Port")), wx.VERTICAL
        )
        sizer_13.Add(sizer_port, 1, wx.EXPAND, 0)

        self.text_port = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="int",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_port.SetToolTip(_("Port for tcp connection on the server computer"))
        sizer_port.Add(self.text_port, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_13)

        self.Layout()

        self.text_address.SetActionRoutine(self.on_text_address)
        self.text_port.SetActionRoutine(self.on_text_port)
        # end wxGlade
        self.text_port.SetValue(str(self.context.port))
        self.text_address.SetValue(self.context.address)

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    def on_text_address(self):
        self.context.address = self.text_address.GetValue()

    def on_text_port(self):  # wxGlade: ConfigurationTcp.<event_handler>
        try:
            self.context.port = int(self.text_port.GetValue())
        except ValueError:
            pass


class ConfigurationLaserPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationLaserPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        v_sizer_main = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Laser Parameters")), wx.VERTICAL
        )

        sizer_bed = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Bed Dimensions")), wx.HORIZONTAL
        )
        v_sizer_main.Add(sizer_bed, 0, wx.EXPAND, 0)

        h_sizer_wd = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Width")), wx.HORIZONTAL
        )
        sizer_bed.Add(h_sizer_wd, 1, wx.EXPAND, 0)

        self.text_bedwidth = TextCtrl(
            self,
            wx.ID_ANY,
            "310mm",
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_bedwidth.SetToolTip(_("Width of the laser bed."))
        h_sizer_wd.Add(self.text_bedwidth, 1, wx.EXPAND, 0)

        h_sizer_ht = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Height")), wx.HORIZONTAL
        )
        sizer_bed.Add(h_sizer_ht, 1, wx.EXPAND, 0)

        label_3 = wx.StaticText(self, wx.ID_ANY, "")
        h_sizer_ht.Add(label_3, 0, wx.EXPAND, 0)

        self.text_bedheight = TextCtrl(
            self,
            wx.ID_ANY,
            "210mm",
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_bedheight.SetToolTip(_("Height of the laser bed."))
        h_sizer_ht.Add(self.text_bedheight, 1, wx.EXPAND, 0)

        sizer_scale_factors = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("User Scale Factor")), wx.HORIZONTAL
        )
        v_sizer_main.Add(sizer_scale_factors, 0, wx.EXPAND, 0)

        h_sizer_x_2 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("X:")), wx.HORIZONTAL
        )
        sizer_scale_factors.Add(h_sizer_x_2, 1, wx.EXPAND, 0)

        self.text_scale_x = TextCtrl(
            self,
            wx.ID_ANY,
            "1.000",
            limited=True,
            check="float",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_scale_x.SetToolTip(
            _("Scale factor for the X-axis. Board units to actual physical units.")
        )
        h_sizer_x_2.Add(self.text_scale_x, 1, wx.EXPAND, 0)

        h_sizer_y_2 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Y:")), wx.HORIZONTAL
        )
        sizer_scale_factors.Add(h_sizer_y_2, 1, wx.EXPAND, 0)

        self.text_scale_y = TextCtrl(
            self,
            wx.ID_ANY,
            "1.000",
            limited=True,
            check="float",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_scale_y.SetToolTip(
            _("Scale factor for the Y-axis. Board units to actual physical units.")
        )
        h_sizer_y_2.Add(self.text_scale_y, 1, wx.EXPAND, 0)

        self.SetSizer(v_sizer_main)

        self.text_bedwidth.SetValue(self.context.bedwidth)
        self.text_bedheight.SetValue(self.context.bedheight)
        self.text_scale_x.SetValue(f"{self.context.scale_x:.4f}")
        self.text_scale_y.SetValue(f"{self.context.scale_y:.4f}")

        self.Layout()

        self.text_bedwidth.SetActionRoutine(self.on_text_bedwidth)
        self.text_bedheight.SetActionRoutine(self.on_text_bedheight)
        self.text_scale_x.SetActionRoutine(self.on_text_x_scale)
        self.text_scale_y.SetActionRoutine(self.on_text_y_scale)

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    def on_text_bedwidth(self):
        ctrl = self.text_bedwidth
        try:
            bedwidth = Length(ctrl.GetValue())
        except ValueError:
            return

        self.context.device.width = bedwidth.preferred_length
        self.context.device.bedwidth = bedwidth.preferred_length
        self.context.signal(
            "bed_size", (self.context.device.bedwidth, self.context.device.bedheight)
        )
        self.context.device.realize()
        self.context("viewport_update\n")
        self.context.signal("bedsize", False)

    def on_text_bedheight(self):
        ctrl = self.text_bedheight
        try:
            bedheight = Length(ctrl.GetValue())
        except ValueError:
            return
        self.context.device.height = bedheight.preferred_length
        self.context.device.bedheight = bedheight.preferred_length
        self.context.signal(
            "bed_size", (self.context.device.bedwidth, self.context.device.bedheight)
        )
        self.context.device.realize()
        self.context("viewport_update\n")
        self.context.signal("bedsize", False)

    def on_text_x_scale(self):
        try:
            self.context.device.user_scale_x = float(self.text_scale_x.GetValue())
            self.context.device.user_scale_y = float(self.text_scale_y.GetValue())
            self.context.signal(
                "scale_step", (self.context.device.scale_x, self.context.device.scale_y)
            )
            self.context.device.realize()
            self.context("viewport_update\n")
            self.context.signal("bedsize", False)
        except ValueError:
            pass

    def on_text_y_scale(self):
        try:
            self.context.device.user_scale_x = float(self.text_scale_x.GetValue())
            self.context.device.user_scale_y = float(self.text_scale_y.GetValue())
            self.context.device.scale_x = self.context.device.user_scale_x
            self.context.device.scale_y = self.context.device.user_scale_y
            self.context.signal(
                "scale_step", (self.context.device.scale_x, self.context.device.scale_y)
            )
            self.context.device.realize()
            self.context("viewport_update\n")
            self.context.signal("bedsize", False)
        except ValueError:
            pass


class ConfigurationInterfacePanel(ScrolledPanel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationInterfacePanel.__init__
        kwds["style"] = kwds.get("style", 0)
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context

        sizer_page_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_name = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Device Name")), wx.HORIZONTAL
        )
        self.text_device_label = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )
        self.text_device_label.SetToolTip(
            _("The internal label to be used for this device")
        )
        sizer_name.Add(self.text_device_label, 1, wx.EXPAND, 0)
        sizer_page_1.Add(sizer_name, 0, wx.EXPAND, 0)

        sizer_config = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Configuration")), wx.HORIZONTAL
        )
        sizer_page_1.Add(sizer_config, 0, wx.EXPAND, 0)

        sizer_board = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Board Setup")), wx.HORIZONTAL
        )
        sizer_config.Add(sizer_board, 0, wx.EXPAND, 0)

        self.combobox_board = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["M2", "B2", "M", "M1", "A", "B", "B1"],
            style=wx.CB_DROPDOWN,
        )
        self.combobox_board.SetToolTip(
            _("Select the board to use. This has an effects the speedcodes used.")
        )
        self.combobox_board.SetSelection(0)
        sizer_board.Add(self.combobox_board, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_17 = wx.BoxSizer(wx.VERTICAL)
        sizer_config.Add(sizer_17, 1, wx.EXPAND, 0)

        self.checkbox_flip_x = wx.CheckBox(self, wx.ID_ANY, _("Flip X"))
        self.checkbox_flip_x.SetToolTip(
            _("Flip the Right and Left commands sent to the controller")
        )
        sizer_17.Add(self.checkbox_flip_x, 0, wx.EXPAND, 0)

        self.checkbox_home_right = wx.CheckBox(self, wx.ID_ANY, _("Home Right"))
        self.checkbox_home_right.SetToolTip(
            _("Indicates the device Home is on the right")
        )
        sizer_17.Add(self.checkbox_home_right, 0, wx.EXPAND, 0)

        label_1 = wx.StaticText(self, wx.ID_ANY, "")
        sizer_17.Add(label_1, 0, wx.EXPAND, 0)

        sizer_16 = wx.BoxSizer(wx.VERTICAL)
        sizer_config.Add(sizer_16, 1, wx.EXPAND, 0)

        self.checkbox_flip_y = wx.CheckBox(self, wx.ID_ANY, _("Flip Y"))
        self.checkbox_flip_y.SetToolTip(
            _("Flip the Top and Bottom commands sent to the controller")
        )
        sizer_16.Add(self.checkbox_flip_y, 0, wx.EXPAND, 0)

        self.checkbox_home_bottom = wx.CheckBox(self, wx.ID_ANY, _("Home Bottom"))
        self.checkbox_home_bottom.SetToolTip(
            _("Indicates the device Home is on the bottom")
        )
        sizer_16.Add(self.checkbox_home_bottom, 0, wx.EXPAND, 0)

        self.checkbox_swap_xy = wx.CheckBox(self, wx.ID_ANY, _("Swap X and Y"))
        self.checkbox_swap_xy.SetToolTip(
            _("Swaps the X and Y axis. This happens before the FlipX and FlipY.")
        )
        sizer_16.Add(self.checkbox_swap_xy, 0, wx.EXPAND, 0)

        sizer_interface = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Interface")), wx.VERTICAL
        )
        sizer_page_1.Add(sizer_interface, 0, wx.EXPAND, 0)

        sizer_interface_radio = wx.BoxSizer(wx.HORIZONTAL)
        sizer_interface.Add(sizer_interface_radio, 0, wx.EXPAND, 0)

        self.radio_usb = wx.RadioButton(self, wx.ID_ANY, _("USB"), style=wx.RB_GROUP)
        self.radio_usb.SetValue(1)
        self.radio_usb.SetToolTip(
            _(
                "Select this if you have an m2-nano controller physically connected to this computer using a USB cable."
            )
        )
        sizer_interface_radio.Add(self.radio_usb, 1, wx.EXPAND, 0)

        self.radio_tcp = wx.RadioButton(self, wx.ID_ANY, _("Networked"))
        self.radio_tcp.SetToolTip(
            _(
                "Select this to connect this instance of Meerk40t to another instance of Meerk40t running as a remote server."
            )
        )
        sizer_interface_radio.Add(self.radio_tcp, 1, wx.EXPAND, 0)

        self.radio_mock = wx.RadioButton(self, wx.ID_ANY, _("Mock"))
        self.radio_mock.SetToolTip(
            _(
                "Select this only for debugging without a physical laser available. Execute a burn as if there was an m2-nano controller physically connected by USB."
            )
        )
        sizer_interface_radio.Add(self.radio_mock, 1, wx.EXPAND, 0)

        self.panel_usb_settings = ConfigurationUsb(
            self, wx.ID_ANY, context=self.context
        )
        sizer_interface.Add(self.panel_usb_settings, 0, wx.EXPAND, 0)

        self.panel_tcp_config = ConfigurationTcp(self, wx.ID_ANY, context=self.context)
        sizer_interface.Add(self.panel_tcp_config, 0, wx.EXPAND, 0)

        self.ConfigurationLaserPanel = ConfigurationLaserPanel(
            self, wx.ID_ANY, context=self.context
        )
        sizer_page_1.Add(self.ConfigurationLaserPanel, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_page_1)

        self.Layout()

        self.text_device_label.SetActionRoutine(self.on_device_label)
        self.Bind(wx.EVT_COMBOBOX, self.on_combobox_boardtype, self.combobox_board)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_flip_x, self.checkbox_flip_x)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_home_right, self.checkbox_home_right)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_flip_y, self.checkbox_flip_y)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_home_bottom, self.checkbox_home_bottom)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_swapxy, self.checkbox_swap_xy)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_usb)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_tcp)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_mock)
        # end wxGlade
        self.text_device_label.SetValue(self.context.label)
        self.checkbox_swap_xy.SetValue(self.context.swap_xy)
        self.checkbox_flip_x.SetValue(self.context.flip_x)
        self.checkbox_flip_y.SetValue(self.context.flip_y)
        self.checkbox_home_right.SetValue(self.context.home_right)
        self.checkbox_home_bottom.SetValue(self.context.home_bottom)
        self.combobox_board.SetValue(self.context.board)
        if self.context.mock:
            self.panel_tcp_config.Hide()
            self.panel_usb_settings.Hide()
            self.radio_mock.SetValue(True)
        elif self.context.networked:
            self.panel_usb_settings.Hide()
            self.radio_tcp.SetValue(True)
        else:
            self.radio_usb.SetValue(True)
            self.panel_tcp_config.Hide()
        self.SetupScrolling()

    def pane_show(self):
        self.ConfigurationLaserPanel.pane_show()
        self.panel_usb_settings.pane_show()
        self.panel_tcp_config.pane_show()

    def pane_hide(self):
        self.ConfigurationLaserPanel.pane_hide()
        self.panel_usb_settings.pane_hide()
        self.panel_tcp_config.pane_hide()

    def on_combobox_boardtype(self, event=None):
        self.context.board = self.combobox_board.GetValue()

    def on_check_swapxy(self, event=None):
        self.context.swap_xy = self.checkbox_swap_xy.GetValue()
        self.context.show_swap_xy = False
        self.context("viewport_update\n")
        self.context.signal("bedsize", False)

    def on_check_flip_x(self, event=None):
        self.context.flip_x = self.checkbox_flip_x.GetValue()
        self.context("viewport_update\n")
        self.context.signal("bedsize", False)

    def on_check_home_right(self, event=None):
        direction = self.checkbox_home_right.GetValue()
        self.context.home_right = direction
        if direction:
            self.context.show_flip_x = True
            self.context.origin_x = 1.0
        else:
            self.context.show_flip_x = False
            self.context.origin_x = 0.0
        self.context.show_origin_x = self.context.origin_x
        self.context("viewport_update\n")
        self.context.signal("bedsize", False)

    def on_check_flip_y(self, event=None):
        self.context.flip_y = self.checkbox_flip_y.GetValue()
        self.context("viewport_update\n")
        self.context.signal("bedsize", False)

    def on_check_home_bottom(self, event=None):
        direction = self.checkbox_home_bottom.GetValue()
        self.context.home_bottom = direction
        if direction:
            self.context.show_flip_y = True
            self.context.origin_y = 1.0
        else:
            self.context.show_flip_y = False
            self.context.origin_y = 0.0
        self.context.show_origin_y = self.context.origin_y
        self.context("viewport_update\n")
        self.context.signal("bedsize", False)

    def on_device_label(self):
        self.context.label = self.text_device_label.GetValue()
        self.context.signal("device;renamed")

    def on_radio_interface(
        self, event
    ):  # wxGlade: ConfigurationInterfacePanel.<event_handler>
        if self.radio_usb.GetValue():
            self.panel_tcp_config.Hide()
            self.panel_usb_settings.Show()
            self.context.networked = False
            self.context.mock = False
            self.context(".network_update\n")
        if self.radio_tcp.GetValue():
            self.panel_tcp_config.Show()
            self.panel_usb_settings.Hide()
            self.context.networked = True
            self.context.mock = False
            self.context(".network_update\n")
        if self.radio_mock.GetValue():
            self.panel_tcp_config.Hide()
            self.panel_usb_settings.Hide()
            self.context.networked = False
            self.context.mock = True
            self.context(".network_update\n")
        self.Layout()


class ConfigurationSetupPanel(ScrolledPanel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationSetupPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_page_2 = wx.BoxSizer(wx.VERTICAL)

        sizer_general = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("General Options")), wx.VERTICAL
        )
        sizer_page_2.Add(sizer_general, 0, wx.EXPAND, 0)

        self.check_autolock = wx.CheckBox(self, wx.ID_ANY, _("Automatically lock rail"))
        self.check_autolock.SetToolTip(_("Lock rail after operations are finished."))
        self.check_autolock.SetValue(1)
        sizer_general.Add(self.check_autolock, 0, wx.EXPAND, 0)

        self.check_plot_shift = wx.CheckBox(self, wx.ID_ANY, _("Pulse Grouping"))
        self.check_plot_shift.SetToolTip(
            "\n".join(
                [
                    _(
                        "Pulse Grouping is an alternative means of reducing the incidence of stuttering, allowing you potentially to burn at higher speeds."
                    ),
                    "",
                    _(
                        "It works by swapping adjacent on or off bits to group on and off together and reduce the number of switches."
                    ),
                    "",
                    _(
                        'As an example, instead of X_X_ it will burn XX__ - because the laser beam is overlapping, and because a bit is only moved at most 1/1000", the difference should not be visible even under magnification.'
                    ),
                    _(
                        "Whilst the Pulse Grouping option in Operations are set for that operation before the job is spooled, and cannot be changed on the fly, this global Pulse Grouping option is checked as instructions are sent to the laser and can turned on and off during the burn process. Because the changes are believed to be small enough to be undetectable, you may wish to leave this permanently checked."
                    ),
                ]
            ),
        )
        sizer_general.Add(self.check_plot_shift, 0, wx.EXPAND, 0)

        self.check_strict = wx.CheckBox(self, wx.ID_ANY, _("Strict"))
        self.check_strict.SetToolTip(
            _(
                "Forces the device to enter and exit programmed speed mode from the same direction.\nThis may prevent devices like the M2-V4 and earlier from having issues. Not typically needed."
            )
        )
        sizer_general.Add(self.check_strict, 0, wx.EXPAND, 0)

        self.check_alternative_raster = wx.CheckBox(
            self, wx.ID_ANY, _("Alt Raster Style")
        )
        self.check_alternative_raster.SetToolTip(
            _(
                "This feature uses an alternative raster method performing a raster turn around using NSE rather than G00x encoding."
            )
        )

        sizer_general.Add(self.check_alternative_raster, 0, wx.EXPAND, 0)

        self.check_twitches = wx.CheckBox(self, wx.ID_ANY, _("Twitch Vectors"))
        self.check_twitches.SetToolTip(
            _(
                "Twitching is an unnecessary move in an unneeded direction at the start and end of travel moves between vector burns. "
                "It is most noticeable when you are doing a number of small burns (e.g. stitch holes in leather). "
                "A twitchless mode is now default in 0.7.6+ or later which results in a noticeable faster travel time. "
                "This option allows you to turn on the previous mode if you experience problems."
            )
        )
        sizer_general.Add(self.check_twitches, 0, wx.EXPAND, 0)

        sizer_jog = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Rapid Jog")), wx.VERTICAL
        )
        sizer_page_2.Add(sizer_jog, 0, wx.EXPAND, 0)

        h_sizer_y3 = wx.BoxSizer(wx.VERTICAL)
        sizer_jog.Add(h_sizer_y3, 0, wx.EXPAND, 0)

        self.check_rapid_moves_between = wx.CheckBox(
            self, wx.ID_ANY, _("Rapid Moves Between Objects")
        )
        self.check_rapid_moves_between.SetToolTip(
            _("Perform rapid moves between the objects")
        )
        self.check_rapid_moves_between.SetValue(1)
        h_sizer_y3.Add(self.check_rapid_moves_between, 0, wx.EXPAND, 0)

        h_sizer_y5 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Minimum Jog Distance")), wx.HORIZONTAL
        )
        h_sizer_y3.Add(h_sizer_y5, 0, wx.EXPAND, 0)

        self.text_minimum_jog_distance = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            style=wx.TE_PROCESS_ENTER,
        )
        h_sizer_y5.Add(self.text_minimum_jog_distance, 1, wx.EXPAND, 0)

        self.radio_box_jog_method = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Jog Method"),
            choices=[_("Default"), _("Reset"), _("Finish")],
            majorDimension=3,
            style=wx.RA_SPECIFY_COLS,  # wx.RA_SPECIFY_ROWS,
        )
        self.radio_box_jog_method.SetToolTip(
            _(
                "Changes the method of jogging. Default are NSE jogs. Reset are @NSE jogs. Finished are @FNSE jogs followed by a wait."
            )
        )
        self.radio_box_jog_method.SetSelection(0)
        sizer_jog.Add(self.radio_box_jog_method, 0, wx.EXPAND, 0)

        sizer_rapid_override = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Rapid Override")), wx.VERTICAL
        )
        sizer_page_2.Add(sizer_rapid_override, 0, wx.EXPAND, 0)

        self.check_override_rapid = wx.CheckBox(
            self, wx.ID_ANY, _("Override Rapid Movements")
        )
        sizer_rapid_override.Add(self.check_override_rapid, 0, wx.EXPAND, 0)
        self.check_override_rapid.SetMaxSize(wx.Size(300, -1))

        sizer_speed_xy = wx.BoxSizer(wx.HORIZONTAL)

        sizer_36 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("X Travel Speed:")), wx.HORIZONTAL
        )

        self.text_rapid_x = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="float",
            style=wx.TE_PROCESS_ENTER,
        )
        sizer_36.Add(self.text_rapid_x, 1, wx.EXPAND, 0)

        label_2 = wx.StaticText(self, wx.ID_ANY, _("mm/s"))
        sizer_36.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_35 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Y Travel Speed:")), wx.HORIZONTAL
        )

        sizer_speed_xy.Add(sizer_36, 1, wx.EXPAND, 0)
        sizer_speed_xy.Add(sizer_35, 1, wx.EXPAND, 0)

        sizer_rapid_override.Add(sizer_speed_xy, 0, wx.EXPAND, 0)

        self.text_rapid_y = TextCtrl(
            self, wx.ID_ANY, "", limited=True, check="float", style=wx.TE_PROCESS_ENTER
        )
        sizer_35.Add(self.text_rapid_y, 1, wx.EXPAND, 0)

        label_4 = wx.StaticText(self, wx.ID_ANY, _("mm/s"))
        sizer_35.Add(label_4, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_speed = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Speed:")), wx.VERTICAL
        )
        sizer_page_2.Add(sizer_speed, 0, wx.EXPAND, 0)

        sizer_32 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_speed.Add(sizer_32, 0, wx.EXPAND, 0)

        self.check_fix_speeds = wx.CheckBox(
            self, wx.ID_ANY, _("Fix rated to actual speed")
        )
        self.check_fix_speeds.SetToolTip(
            _(
                "Correct for speed invalidity. Lihuiyu Studios speeds are 92% of the correctly rated speed"
            )
        )
        self.check_fix_speeds.SetMaxSize(wx.Size(300, -1))

        sizer_32.Add(self.check_fix_speeds, 1, wx.EXPAND, 0)

        self.text_fix_rated_speed = TextCtrl(
            self, wx.ID_ANY, str(FIX_SPEEDS_RATIO), style=wx.TE_READONLY, limited=True
        )
        sizer_32.Add(self.text_fix_rated_speed, 1, wx.EXPAND, 0)

        h_sizer_y9 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_speed.Add(h_sizer_y9, 0, wx.EXPAND, 0)

        self.check_scale_speed = wx.CheckBox(self, wx.ID_ANY, _("Scale Speed"))
        self.check_scale_speed.SetToolTip(
            _(
                "Scale any given speeds to this device by this amount. If set to 1.1, all speeds are 10% faster than rated."
            )
        )
        self.check_scale_speed.SetMaxSize(wx.Size(300, -1))
        h_sizer_y9.Add(self.check_scale_speed, 1, wx.EXPAND, 0)

        self.text_speed_scale_amount = TextCtrl(
            self,
            wx.ID_ANY,
            "1.000",
            limited=True,
            check="float",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_speed_scale_amount.SetToolTip(
            _(
                "Scales the machine's speed ratio so that rated speeds speeds multiplied by this ratio."
            )
        )
        h_sizer_y9.Add(self.text_speed_scale_amount, 1, wx.EXPAND, 0)

        sizer_30 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_speed.Add(sizer_30, 0, wx.EXPAND, 0)

        self.check_max_speed_vector = wx.CheckBox(
            self, wx.ID_ANY, _("Max Speed (Vector)")
        )
        self.check_max_speed_vector.SetToolTip(
            _("Limit the maximum vector speed to this value")
        )
        self.check_max_speed_vector.SetMaxSize(wx.Size(300, -1))
        sizer_30.Add(self.check_max_speed_vector, 1, wx.EXPAND, 0)

        self.text_max_speed_vector = TextCtrl(
            self,
            wx.ID_ANY,
            "100",
            limited=True,
            check="float",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_max_speed_vector.SetToolTip(
            _("maximum speed at which all greater speeds are limited")
        )
        sizer_30.Add(self.text_max_speed_vector, 1, wx.EXPAND, 0)

        sizer_31 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_speed.Add(sizer_31, 0, wx.EXPAND, 0)

        self.check_max_speed_raster = wx.CheckBox(
            self, wx.ID_ANY, _("Max Speed (Raster)")
        )
        self.check_max_speed_raster.SetToolTip(
            _("Limit the maximum raster speed to this value")
        )
        self.check_max_speed_raster.SetMaxSize(wx.Size(300, -1))
        sizer_31.Add(self.check_max_speed_raster, 1, wx.EXPAND, 0)

        self.text_max_speed_raster = TextCtrl(
            self,
            wx.ID_ANY,
            "750",
            limited=True,
            check="float",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_max_speed_raster.SetToolTip(
            _("maximum speed at which all greater speeds are limited")
        )
        sizer_31.Add(self.text_max_speed_raster, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_page_2)

        self.Layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_autolock, self.check_autolock)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_pulse_shift, self.check_plot_shift)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_strict, self.check_strict)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_alt_raster, self.check_alternative_raster
        )
        self.Bind(wx.EVT_CHECKBOX, self.on_check_twitches, self.check_twitches)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_rapid_between, self.check_rapid_moves_between
        )
        self.text_minimum_jog_distance.SetActionRoutine(self.on_text_min_jog_distance)
        self.Bind(wx.EVT_RADIOBOX, self.on_jog_method_radio, self.radio_box_jog_method)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_override_rapid, self.check_override_rapid
        )
        self.text_rapid_x.SetActionRoutine(self.on_text_rapid_x)
        self.text_rapid_y.SetActionRoutine(self.on_text_rapid_y)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_fix_speeds, self.check_fix_speeds)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_scale_speed, self.check_scale_speed)
        self.text_speed_scale_amount.SetActionRoutine(self.on_text_speed_scale)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_max_speed_vector, self.check_max_speed_vector
        )
        self.text_max_speed_vector.SetActionRoutine(self.on_text_speed_max_vector)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_max_speed_raster, self.check_max_speed_raster
        )
        self.text_max_speed_raster.SetActionRoutine(self.on_text_speed_max_raster)
        # end wxGlade

        self.check_autolock.SetValue(self.context.autolock)
        self.check_plot_shift.SetValue(self.context.plot_shift)
        self.check_strict.SetValue(self.context.strict)
        self.check_alternative_raster.SetValue(self.context.nse_raster)
        self.check_twitches.SetValue(self.context.twitches)
        self.check_rapid_moves_between.SetValue(self.context.opt_rapid_between)
        self.text_minimum_jog_distance.SetValue(str(self.context.opt_jog_minimum))
        self.radio_box_jog_method.SetSelection(self.context.opt_jog_mode)
        self.check_override_rapid.SetValue(self.context.rapid_override)
        self.text_rapid_x.SetValue(str(self.context.rapid_override_speed_x))
        self.text_rapid_y.SetValue(str(self.context.rapid_override_speed_y))
        self.check_fix_speeds.SetValue(self.context.fix_speeds)
        self.check_scale_speed.SetValue(self.context.scale_speed_enabled)
        self.text_speed_scale_amount.SetValue(str(self.context.scale_speed))
        self.check_max_speed_vector.SetValue(self.context.max_speed_vector_enabled)
        self.text_max_speed_vector.SetValue(str(self.context.max_speed_vector))
        self.check_max_speed_raster.SetValue(self.context.max_speed_raster_enabled)
        self.text_max_speed_raster.SetValue(str(self.context.max_speed_raster))

        # Disables of features not yet supported.
        self.text_max_speed_raster.Enable(False)
        self.text_max_speed_vector.Enable(False)
        self.text_speed_scale_amount.Enable(False)
        self.check_max_speed_raster.Enable(False)
        self.check_max_speed_vector.Enable(False)
        self.check_scale_speed.Enable(False)
        self.SetupScrolling()

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    def on_check_fix_speeds(self, event=None):
        self.context.fix_speeds = self.check_fix_speeds.GetValue()
        self.text_fix_rated_speed.SetValue(
            "1.000" if self.context.fix_speeds else str(FIX_SPEEDS_RATIO)
        )

    def on_check_strict(self, event=None):
        self.context.strict = self.check_strict.GetValue()

    def on_check_autolock(self, event=None):
        self.context.autolock = self.check_autolock.GetValue()

    def on_check_pulse_shift(self, event=None):
        self.context.plot_shift = self.check_plot_shift.GetValue()
        try:
            self.context.plot_planner.force_shift = self.context.plot_shift
        except (AttributeError, TypeError):
            pass

    def on_check_alt_raster(self, event):
        self.context.nse_raster = self.check_alternative_raster.GetValue()

    def on_check_twitches(self, event):
        self.context.twitches = self.check_twitches.GetValue()

    def on_check_rapid_between(self, event):
        self.context.opt_rapid_between = self.check_rapid_moves_between.GetValue()

    def on_text_min_jog_distance(self):
        try:
            self.context.opt_jog_minimum = int(
                self.text_minimum_jog_distance.GetValue()
            )
        except ValueError:
            pass

    def on_jog_method_radio(self, event):
        self.context.opt_jog_mode = self.radio_box_jog_method.GetSelection()

    def on_check_override_rapid(self, event):
        self.context.rapid_override = self.check_override_rapid.GetValue()

    def on_text_rapid_x(self):
        try:
            self.context.rapid_override_speed_x = float(self.text_rapid_x.GetValue())
        except ValueError:
            pass

    def on_text_rapid_y(self):
        try:
            self.context.rapid_override_speed_y = float(self.text_rapid_y.GetValue())
        except ValueError:
            pass

    def on_check_scale_speed(
        self, event
    ):  # wxGlade: ConfigurationSetupPanel.<event_handler>
        self.context.scale_speed_enabled = self.check_scale_speed.GetValue()

    def on_text_speed_scale(self):
        try:
            self.context.scale_speed = float(self.text_speed_scale_amount.GetValue())
        except ValueError:
            pass

    def on_check_max_speed_vector(
        self, event
    ):  # wxGlade: ConfigurationSetupPanel.<event_handler>
        self.context.max_speed_vector_enabled = self.check_max_speed_vector.GetValue()

    def on_text_speed_max_vector(self):
        try:
            self.context.max_speed_vector = float(self.text_max_speed_vector.GetValue())
        except ValueError:
            pass

    def on_check_max_speed_raster(
        self, event
    ):  # wxGlade: ConfigurationSetupPanel.<event_handler>
        self.context.max_speed_raster_enabled = self.check_max_speed_raster.GetValue()

    def on_text_speed_max_raster(self):
        try:
            self.context.max_speed_raster = float(self.text_max_speed_raster.GetValue())
        except ValueError:
            pass


class LihuiyuDriverGui(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(330, 630, *args, **kwds)
        self.context = self.context.device
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Lihuiyu-Configuration"))

        # self.notebook_main = wx.Notebook(self, wx.ID_ANY)
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.panels = []

        panel_config = ConfigurationInterfacePanel(
            self.notebook_main, wx.ID_ANY, context=self.context
        )

        panel_setup = ConfigurationSetupPanel(
            self.notebook_main, wx.ID_ANY, context=self.context
        )

        panel_warn = WarningPanel(self, id=wx.ID_ANY, context=self.context)
        panel_actions = DefaultActionPanel(self, id=wx.ID_ANY, context=self.context)
        newpanel = FormatterPanel(self, id=wx.ID_ANY, context=self.context)

        self.panels.append(panel_config)
        self.panels.append(panel_setup)
        self.panels.append(panel_warn)
        self.panels.append(panel_actions)
        self.panels.append(newpanel)

        self.notebook_main.AddPage(panel_config, _("Configuration"))
        self.notebook_main.AddPage(panel_setup, _("Setup"))
        self.notebook_main.AddPage(panel_warn, _("Warning"))
        self.notebook_main.AddPage(panel_actions, _("Default Actions"))
        self.notebook_main.AddPage(newpanel, _("Display Options"))

        self.Layout()

        for panel in self.panels:
            self.add_module_delegate(panel)

    def window_open(self):
        for panel in self.panels:
            panel.pane_show()

    def window_close(self):
        for panel in self.panels:
            panel.pane_hide()

    def window_preserve(self):
        return False

    @staticmethod
    def submenu():
        return ("Device-Settings", "Configuration")
