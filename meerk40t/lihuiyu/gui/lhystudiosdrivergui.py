# -*- coding: ISO-8859-1 -*-

import wx

from meerk40t.gui.icons import icons8_administrative_tools_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class ConfigurationUsb(wx.Panel):
    def __init__(self, *args, context=None, **kwds):

        # begin wxGlade: ConfigurationUsb.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_usb_settings = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "USB Settings"), wx.VERTICAL
        )

        sizer_usb_restrict = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Restrict Multiple Lasers"), wx.VERTICAL
        )
        sizer_usb_settings.Add(sizer_usb_restrict, 0, 0, 0)

        sizer_criteria = wx.BoxSizer(wx.HORIZONTAL)
        sizer_usb_restrict.Add(sizer_criteria, 1, wx.EXPAND, 0)

        sizer_chip_version = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "CH341 Version"), wx.HORIZONTAL
        )
        sizer_criteria.Add(sizer_chip_version, 0, wx.EXPAND, 0)

        self.text_device_version = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.text_device_version.SetMinSize((55, 23))
        sizer_chip_version.Add(self.text_device_version, 0, 0, 0)

        self.spin_device_version = wx.SpinCtrl(self, wx.ID_ANY, "-1", min=-1, max=25)
        self.spin_device_version.SetMinSize((40, 23))
        self.spin_device_version.SetToolTip(
            "Optional: Distinguish between different lasers using the match criteria below.\n-1 match anything. 0+ match exactly that value."
        )
        sizer_chip_version.Add(self.spin_device_version, 0, 0, 0)

        sizer_device_index = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Device Index:"), wx.HORIZONTAL
        )
        sizer_criteria.Add(sizer_device_index, 0, wx.EXPAND, 0)

        self.text_device_index = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_device_index.SetMinSize((55, 23))
        sizer_device_index.Add(self.text_device_index, 0, 0, 0)

        self.spin_device_index = wx.SpinCtrl(self, wx.ID_ANY, "-1", min=-1, max=5)
        self.spin_device_index.SetMinSize((40, 23))
        self.spin_device_index.SetToolTip(
            "Optional: Distinguish between different lasers using the match criteria below.\n-1 match anything. 0+ match exactly that value."
        )
        sizer_device_index.Add(self.spin_device_index, 0, 0, 0)

        sizer_serial = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Serial Number"), wx.HORIZONTAL
        )
        sizer_usb_restrict.Add(sizer_serial, 0, wx.EXPAND, 0)

        self.check_serial_number = wx.CheckBox(self, wx.ID_ANY, "Serial Number")
        self.check_serial_number.SetToolTip(
            "Require a serial number match for this board"
        )
        sizer_serial.Add(self.check_serial_number, 0, 0, 0)

        self.text_serial_number = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_serial_number.SetMinSize((150, 23))
        self.text_serial_number.SetToolTip(
            "Board Serial Number to be used to identify a specific laser. If the device fails to match the serial number it will be disconnected."
        )
        sizer_serial.Add(self.text_serial_number, 0, wx.EXPAND, 0)

        sizer_buffer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Write Buffer"), wx.HORIZONTAL
        )
        sizer_usb_settings.Add(sizer_buffer, 0, wx.EXPAND, 0)

        self.checkbox_limit_buffer = wx.CheckBox(self, wx.ID_ANY, "Limit Write Buffer")
        self.checkbox_limit_buffer.SetToolTip(
            "Limit the write buffer to a certain amount. Permits on-the-fly command production."
        )
        self.checkbox_limit_buffer.SetValue(1)
        sizer_buffer.Add(self.checkbox_limit_buffer, 0, 0, 0)

        self.text_buffer_length = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_buffer_length.SetToolTip(
            "Current number of bytes in the write buffer."
        )
        sizer_buffer.Add(self.text_buffer_length, 0, 0, 0)

        label_14 = wx.StaticText(self, wx.ID_ANY, "/")
        sizer_buffer.Add(label_14, 0, 0, 0)

        self.spin_packet_buffer_max = wx.SpinCtrl(
            self, wx.ID_ANY, "1500", min=1, max=1000000
        )
        self.spin_packet_buffer_max.SetToolTip("Current maximum write buffer limit.")
        sizer_buffer.Add(self.spin_packet_buffer_max, 0, 0, 0)

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
        self.Bind(wx.EVT_TEXT, self.on_text_serial_number, self.text_serial_number)
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


    def on_check_limit_packet_buffer(
        self, event=None
    ):  # wxGlade: JobInfo.<event_handler>
        self.context.buffer_limit = self.checkbox_limit_buffer.GetValue()

    def on_spin_packet_buffer_max(self, event=None):  # wxGlade: JobInfo.<event_handler>
        self.context.buffer_max = self.spin_packet_buffer_max.GetValue()

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

    def spin_on_device_index(self, event=None):
        self.context.usb_index = int(self.spin_device_index.GetValue())

    def spin_on_device_version(self, event=None):
        self.context.usb_version = int(self.spin_device_version.GetValue())

    def on_check_serial_number(
        self, event
    ):  # wxGlade: ConfigurationUsb.<event_handler>
        self.context.serial_enable = self.check_serial_number.GetValue()

    def on_text_serial_number(self, event):  # wxGlade: ConfigurationUsb.<event_handler>
        self.context.serial = self.text_serial_number.GetValue()


class ConfigurationTcp(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationTcp.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_13 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "TCP Settings"), wx.HORIZONTAL
        )

        sizer_21 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Address"), wx.VERTICAL
        )
        sizer_13.Add(sizer_21, 0, 0, 0)

        self.text_address = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_address.SetMinSize((150, 23))
        self.text_address.SetToolTip("IP/Host if the server computer")
        sizer_21.Add(self.text_address, 0, 0, 0)

        sizer_port = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Port"), wx.VERTICAL
        )
        sizer_13.Add(sizer_port, 0, 0, 0)

        self.text_port = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_port.SetToolTip("Port for tcp connection on the server computer")
        sizer_port.Add(self.text_port, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_13)

        self.Layout()

        self.Bind(wx.EVT_TEXT, self.on_text_address, self.text_address)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_address, self.text_address)
        self.Bind(wx.EVT_TEXT, self.on_text_port, self.text_port)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_port, self.text_port)
        # end wxGlade
        self.text_port.SetValue(str(self.context.port))
        self.text_address.SetValue(self.context.address)

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    def on_text_address(self, event):  # wxGlade: ConfigurationTcp.<event_handler>
        self.context.address = self.text_address.GetValue()

    def on_text_port(self, event):  # wxGlade: ConfigurationTcp.<event_handler>
        self.context.port = self.text_port.GetValue()


class ConfigurationLaserPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationLaserPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_27 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Laser Parameters"), wx.VERTICAL
        )

        sizer_home = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Shift Home Position"), wx.HORIZONTAL
        )
        sizer_27.Add(sizer_home, 0, wx.EXPAND, 0)

        sizer_4 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "X:"), wx.HORIZONTAL)
        sizer_home.Add(sizer_4, 2, wx.EXPAND, 0)

        self.spin_home_x = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "0.0", min=-50000.0, max=50000.0
        )
        self.spin_home_x.SetMinSize((80, 23))
        self.spin_home_x.SetToolTip("Translate Home X")
        sizer_4.Add(self.spin_home_x, 0, 0, 0)

        label_12 = wx.StaticText(self, wx.ID_ANY, "steps")
        sizer_4.Add(label_12, 0, 0, 0)

        sizer_2 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Y:"), wx.HORIZONTAL)
        sizer_home.Add(sizer_2, 2, wx.EXPAND, 0)

        self.spin_home_y = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "0.0", min=-50000.0, max=50000.0
        )
        self.spin_home_y.SetMinSize((80, 23))
        self.spin_home_y.SetToolTip("Translate Home Y")
        sizer_2.Add(self.spin_home_y, 0, 0, 0)

        label_11 = wx.StaticText(self, wx.ID_ANY, "steps")
        sizer_2.Add(label_11, 0, 0, 0)

        self.button_home_by_current = wx.Button(self, wx.ID_ANY, "Set Current")
        self.button_home_by_current.SetToolTip(
            "Set Home Position based on the current position"
        )
        sizer_home.Add(self.button_home_by_current, 1, 0, 0)

        sizer_bed = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Bed Dimensions"), wx.HORIZONTAL
        )
        sizer_27.Add(sizer_bed, 0, wx.EXPAND, 0)

        sizer_14 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Width"), wx.HORIZONTAL
        )
        sizer_bed.Add(sizer_14, 1, 0, 0)

        self.spin_bedwidth = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "12205.0", min=1.0, max=100000.0
        )
        self.spin_bedwidth.SetMinSize((80, 23))
        self.spin_bedwidth.SetToolTip("Width of the laser bed.")
        self.spin_bedwidth.SetIncrement(40.0)
        sizer_14.Add(self.spin_bedwidth, 4, 0, 0)

        label_17 = wx.StaticText(self, wx.ID_ANY, "steps")
        sizer_14.Add(label_17, 1, 0, 0)

        sizer_15 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Height"), wx.HORIZONTAL
        )
        sizer_bed.Add(sizer_15, 1, 0, 0)

        label_3 = wx.StaticText(self, wx.ID_ANY, "")
        sizer_15.Add(label_3, 0, 0, 0)

        self.spin_bedheight = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "8268.0", min=1.0, max=100000.0
        )
        self.spin_bedheight.SetMinSize((80, 23))
        self.spin_bedheight.SetToolTip("Height of the laser bed.")
        self.spin_bedheight.SetIncrement(40.0)
        sizer_15.Add(self.spin_bedheight, 4, 0, 0)

        label_18 = wx.StaticText(self, wx.ID_ANY, "steps\n")
        sizer_15.Add(label_18, 1, 0, 0)

        sizer_scale_factors = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Mil/Step Scale Factor"), wx.HORIZONTAL
        )
        sizer_27.Add(sizer_scale_factors, 0, wx.EXPAND, 0)

        sizer_19 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "X:"), wx.HORIZONTAL)
        sizer_scale_factors.Add(sizer_19, 0, wx.EXPAND, 0)

        self.text_scale_x = wx.TextCtrl(self, wx.ID_ANY, "1.000")
        self.text_scale_x.SetToolTip(
            "Scale factor for the X-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
        )
        sizer_19.Add(self.text_scale_x, 0, 0, 0)

        sizer_20 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Y:"), wx.HORIZONTAL)
        sizer_scale_factors.Add(sizer_20, 0, wx.EXPAND, 0)

        self.text_scale_y = wx.TextCtrl(self, wx.ID_ANY, "1.000")
        self.text_scale_y.SetToolTip(
            "Scale factor for the Y-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
        )
        sizer_20.Add(self.text_scale_y, 0, 0, 0)

        self.SetSizer(sizer_27)

        self.Layout()

        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.spin_on_home_x, self.spin_home_x)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_home_x, self.spin_home_x)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.spin_on_home_y, self.spin_home_y)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_home_y, self.spin_home_y)
        self.Bind(
            wx.EVT_BUTTON, self.on_button_set_home_current, self.button_home_by_current
        )
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.spin_on_bedwidth, self.spin_bedwidth)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.spin_on_bedheight, self.spin_bedheight)
        self.Bind(wx.EVT_TEXT, self.on_text_x_scale, self.text_scale_x)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_x_scale, self.text_scale_x)
        self.Bind(wx.EVT_TEXT, self.on_text_y_scale, self.text_scale_y)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_y_scale, self.text_scale_y)
        # end wxGlade
        self.spin_home_x.SetValue(self.context.home_adjust_x)
        self.spin_home_y.SetValue(self.context.home_adjust_y)

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    def spin_on_home_x(self, event=None):
        self.context.home_adjust_x = int(self.spin_home_x.GetValue())

    def spin_on_home_y(self, event=None):
        self.context.home_adjust_y = int(self.spin_home_y.GetValue())

    def on_button_set_home_current(self, event=None):
        x, y = self.calc_home_position()
        current_x = self.context.device.current_x - x
        current_y = self.context.device.current_y - y
        self.context.home_adjust_x = int(current_x)
        self.context.home_adjust_y = int(current_y)
        self.spin_home_x.SetValue(self.context.home_adjust_x)
        self.spin_home_y.SetValue(self.context.home_adjust_y)

    def calc_home_position(self):
        x = 0
        y = 0
        if self.context.home_right:
            x = int(self.context.device.bedwidth)
        if self.context.home_bottom:
            y = int(self.context.device.bedheight)
        return x, y

    def spin_on_bedwidth(self, event=None):
        self.context.device.bedwidth = float(self.spin_bedwidth.GetValue())
        self.context.device.bedheight = float(self.spin_bedheight.GetValue())
        self.context.signal(
            "bed_size", (self.context.device.bedwidth, self.context.device.bedheight)
        )

    def spin_on_bedheight(self, event=None):
        self.context.device.bedwidth = float(self.spin_bedwidth.GetValue())
        self.context.device.bedheight = float(self.spin_bedheight.GetValue())
        self.context.signal(
            "bed_size", (self.context.device.bedwidth, self.context.device.bedheight)
        )

    def on_text_x_scale(self, event=None):
        try:
            self.context.device.scale_x = float(self.text_scale_x.GetValue())
            self.context.device.scale_y = float(self.text_scale_y.GetValue())
            self.context.signal(
                "scale_step", (self.context.device.scale_x, self.context.device.scale_y)
            )
        except ValueError:
            pass

    def on_text_y_scale(self, event=None):
        try:
            self.context.device.scale_x = float(self.text_scale_x.GetValue())
            self.context.device.scale_y = float(self.text_scale_y.GetValue())
            self.context.signal(
                "scale_step", (self.context.device.scale_x, self.context.device.scale_y)
            )
        except ValueError:
            pass


class ConfigurationInterfacePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationInterfacePanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_page_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_37 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Device Name"), wx.HORIZONTAL
        )
        sizer_page_1.Add(sizer_37, 0, wx.EXPAND, 0)

        self.text_device_label = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_device_label.SetToolTip(
            "The internal label to be used for this device"
        )
        sizer_37.Add(self.text_device_label, 1, 0, 0)

        sizer_config = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Configuration"), wx.HORIZONTAL
        )
        sizer_page_1.Add(sizer_config, 0, wx.EXPAND, 0)

        sizer_board = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Board Setup"), wx.HORIZONTAL
        )
        sizer_config.Add(sizer_board, 0, wx.EXPAND, 0)

        self.combobox_board = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["M2", "B2", "M", "M1", "A", "B", "B1"],
            style=wx.CB_DROPDOWN,
        )
        self.combobox_board.SetToolTip(
            "Select the board to use. This has an effects the speedcodes used."
        )
        self.combobox_board.SetSelection(0)
        sizer_board.Add(self.combobox_board, 1, 0, 0)

        sizer_17 = wx.BoxSizer(wx.VERTICAL)
        sizer_config.Add(sizer_17, 1, wx.EXPAND, 0)

        self.checkbox_flip_x = wx.CheckBox(self, wx.ID_ANY, "Flip X")
        self.checkbox_flip_x.SetToolTip(
            "Flip the Right and Left commands sent to the controller"
        )
        sizer_17.Add(self.checkbox_flip_x, 0, 0, 0)

        self.checkbox_home_right = wx.CheckBox(self, wx.ID_ANY, "Home Right")
        self.checkbox_home_right.SetToolTip("Indicates the device Home is on the right")
        sizer_17.Add(self.checkbox_home_right, 0, 0, 0)

        label_1 = wx.StaticText(self, wx.ID_ANY, "")
        sizer_17.Add(label_1, 0, 0, 0)

        sizer_16 = wx.BoxSizer(wx.VERTICAL)
        sizer_config.Add(sizer_16, 1, wx.EXPAND, 0)

        self.checkbox_flip_y = wx.CheckBox(self, wx.ID_ANY, "Flip Y")
        self.checkbox_flip_y.SetToolTip(
            "Flip the Top and Bottom commands sent to the controller"
        )
        sizer_16.Add(self.checkbox_flip_y, 0, 0, 0)

        self.checkbox_home_bottom = wx.CheckBox(self, wx.ID_ANY, "Home Bottom")
        self.checkbox_home_bottom.SetToolTip(
            "Indicates the device Home is on the bottom"
        )
        sizer_16.Add(self.checkbox_home_bottom, 0, 0, 0)

        self.checkbox_swap_xy = wx.CheckBox(self, wx.ID_ANY, "Swap X and Y")
        self.checkbox_swap_xy.SetToolTip(
            "Swaps the X and Y axis. This happens before the FlipX and FlipY."
        )
        sizer_16.Add(self.checkbox_swap_xy, 0, 0, 0)

        sizer_interface = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Interface"), wx.VERTICAL
        )
        sizer_page_1.Add(sizer_interface, 0, wx.EXPAND, 0)

        sizer_interface_radio = wx.BoxSizer(wx.HORIZONTAL)
        sizer_interface.Add(sizer_interface_radio, 0, wx.EXPAND, 0)

        self.radio_usb = wx.RadioButton(self, wx.ID_ANY, "USB", style=wx.RB_GROUP)
        self.radio_usb.SetValue(1)
        sizer_interface_radio.Add(self.radio_usb, 1, 0, 0)

        self.radio_tcp = wx.RadioButton(self, wx.ID_ANY, "Networked")
        sizer_interface_radio.Add(self.radio_tcp, 4, 0, 0)

        self.radio_mock = wx.RadioButton(self, wx.ID_ANY, "Mock")
        self.radio_mock.SetToolTip(
            "DEBUG. Without a K40 connected continue to process things as if there was one."
        )
        sizer_interface_radio.Add(self.radio_mock, 1, 0, 0)

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

        self.Bind(wx.EVT_TEXT, self.on_device_label, self.text_device_label)
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
        self.radio_usb.SetValue(True)
        if self.context.networked:
            self.radio_tcp.SetValue(True)
        if self.context.mock:
            self.radio_mock.SetValue(True)

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
        self.context("code_update\n")

    def on_check_flip_x(self, event=None):
        self.context.flip_x = self.checkbox_flip_x.GetValue()
        self.context("code_update\n")

    def on_check_home_right(self, event=None):
        self.context.home_right = self.checkbox_home_right.GetValue()

    def on_check_flip_y(self, event=None):
        self.context.flip_y = self.checkbox_flip_y.GetValue()
        self.context("code_update\n")

    def on_check_home_bottom(self, event=None):
        self.context.home_bottom = self.checkbox_home_bottom.GetValue()

    def on_device_label(
        self, event
    ):  # wxGlade: ConfigurationInterfacePanel.<event_handler>
        self.context.label = self.text_device_label.GetValue()

    def on_radio_interface(
        self, event
    ):  # wxGlade: ConfigurationInterfacePanel.<event_handler>
        if self.radio_usb.GetValue():
            self.context.networked = False
            self.context.mock = False
            self.context(".network_update\n")
        if self.radio_tcp.GetValue():
            self.context.networked = False
            self.context.mock = False
            self.context(".network_update\n")
        if self.radio_mock.GetValue():
            self.context.networked = False
            self.context.mock = True
            self.context(".network_update\n")


class ConfigurationSetupPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationSetupPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_page_2 = wx.BoxSizer(wx.VERTICAL)

        sizer_general = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "General Options"), wx.VERTICAL
        )
        sizer_page_2.Add(sizer_general, 0, wx.EXPAND, 0)

        self.checkbox_autolock = wx.CheckBox(self, wx.ID_ANY, "Automatically lock rail")
        self.checkbox_autolock.SetToolTip("Lock rail after operations are finished.")
        self.checkbox_autolock.SetValue(1)
        sizer_general.Add(self.checkbox_autolock, 0, 0, 0)

        self.checkbox_plot_shift = wx.CheckBox(self, wx.ID_ANY, "Pulse Shifting")
        self.checkbox_plot_shift.SetToolTip(
            'Pulse Grouping is an alternative means of reducing the incidence of stuttering, allowing you potentially to burn at higher speeds. \n\nIt works by swapping adjacent on or off bits to group on and off together and reduce the number of switches.\n\nAs an example, instead of X_X_ it will burn XX__ - because the laser beam is overlapping, and because a bit is only moved at most 1/1000", the difference should not be visible even under magnification.\nWhilst the Pulse Grouping option in Operations are set for that operation before the job is spooled, and cannot be changed on the fly, this global Pulse Grouping option is checked as instructions are sent to the laser and can turned on and off during the burn process. Because the changes are believed to be small enough to be undetectable, you may wish to leave this permanently checked.'
        )
        sizer_general.Add(self.checkbox_plot_shift, 0, 0, 0)

        self.checkbox_strict = wx.CheckBox(self, wx.ID_ANY, "Strict")
        self.checkbox_strict.SetToolTip(
            "Forces the device to enter and exit programmed speed mode from the same direction.\nThis may prevent devices like the M2-V4 and earlier from having issues. Not typically needed."
        )
        sizer_general.Add(self.checkbox_strict, 0, 0, 0)

        self.checkbox_alternative_raster = wx.CheckBox(
            self, wx.ID_ANY, "Alt Raster Style"
        )
        sizer_general.Add(self.checkbox_alternative_raster, 0, 0, 0)

        self.checkbox_twitchless = wx.CheckBox(self, wx.ID_ANY, "Twitchless Vectors")
        sizer_general.Add(self.checkbox_twitchless, 0, 0, 0)

        sizer_jog = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Rapid Jog"), wx.VERTICAL
        )
        sizer_page_2.Add(sizer_jog, 0, 0, 0)

        sizer_23 = wx.BoxSizer(wx.VERTICAL)
        sizer_jog.Add(sizer_23, 0, wx.EXPAND, 0)

        self.check_rapid_moves_between = wx.CheckBox(
            self, wx.ID_ANY, "Rapid Moves Between Objects"
        )
        self.check_rapid_moves_between.SetToolTip(
            "Perform rapid moves between the objects"
        )
        self.check_rapid_moves_between.SetValue(1)
        sizer_23.Add(self.check_rapid_moves_between, 0, 0, 0)

        sizer_25 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Minimum Jog Distance"), wx.HORIZONTAL
        )
        sizer_23.Add(sizer_25, 0, 0, 0)

        self.text_minimum_jog_distance = wx.TextCtrl(self, wx.ID_ANY, "")
        sizer_25.Add(self.text_minimum_jog_distance, 0, 0, 0)

        self.radio_box_1 = wx.RadioBox(
            self,
            wx.ID_ANY,
            "Jog Method",
            choices=["Default", "Reset", "Finish"],
            majorDimension=3,
            style=wx.RA_SPECIFY_ROWS,
        )
        self.radio_box_1.SetSelection(0)
        sizer_jog.Add(self.radio_box_1, 0, 0, 0)

        sizer_rapid_override = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Rapid Override"), wx.VERTICAL
        )
        sizer_page_2.Add(sizer_rapid_override, 0, wx.EXPAND, 0)

        self.checkbox_3 = wx.CheckBox(self, wx.ID_ANY, "Override Rapid Movements")
        sizer_rapid_override.Add(self.checkbox_3, 0, 0, 0)

        sizer_36 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "X Travel Speed:"), wx.HORIZONTAL
        )
        sizer_rapid_override.Add(sizer_36, 0, wx.EXPAND, 0)

        self.text_rapid_x = wx.TextCtrl(self, wx.ID_ANY, "")
        sizer_36.Add(self.text_rapid_x, 0, 0, 0)

        label_2 = wx.StaticText(self, wx.ID_ANY, "mm/s")
        sizer_36.Add(label_2, 0, 0, 0)

        sizer_35 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Y Travel Speed:"), wx.HORIZONTAL
        )
        sizer_rapid_override.Add(sizer_35, 0, wx.EXPAND, 0)

        self.text_rapid_y = wx.TextCtrl(self, wx.ID_ANY, "")
        sizer_35.Add(self.text_rapid_y, 0, 0, 0)

        label_4 = wx.StaticText(self, wx.ID_ANY, "mm/s")
        sizer_35.Add(label_4, 0, 0, 0)

        sizer_speed = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Speed:"), wx.VERTICAL
        )
        sizer_page_2.Add(sizer_speed, 0, wx.EXPAND, 0)

        sizer_32 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_speed.Add(sizer_32, 1, wx.EXPAND, 0)

        self.checkbox_fix_speeds = wx.CheckBox(
            self, wx.ID_ANY, "Fix rated to actual speed"
        )
        self.checkbox_fix_speeds.SetToolTip(
            "Correct for speed invalidity. Lihuiyu Studios speeds are 92% of the correctly rated speed"
        )
        sizer_32.Add(self.checkbox_fix_speeds, 1, 0, 0)

        self.text_fix_rated_speed = wx.TextCtrl(
            self, wx.ID_ANY, "0.9195", style=wx.TE_READONLY
        )
        sizer_32.Add(self.text_fix_rated_speed, 1, 0, 0)

        sizer_29 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_speed.Add(sizer_29, 1, wx.EXPAND, 0)

        self.check_scale_speed = wx.CheckBox(self, wx.ID_ANY, "Scale Speed")
        self.check_scale_speed.SetToolTip(
            "Scale any given speeds to this device by this amount. If set to 1.1, all speeds are 10% faster than rated."
        )
        sizer_29.Add(self.check_scale_speed, 1, 0, 0)

        self.text_speed_scale_amount = wx.TextCtrl(self, wx.ID_ANY, "1.000")
        self.text_speed_scale_amount.SetToolTip(
            "Scales the machine's speed ratio so that rated speeds speeds multiplied by this ratio."
        )
        sizer_29.Add(self.text_speed_scale_amount, 1, wx.EXPAND, 0)

        sizer_30 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_speed.Add(sizer_30, 1, wx.EXPAND, 0)

        self.check_max_speed_vector = wx.CheckBox(self, wx.ID_ANY, "Max Speed (Vector)")
        self.check_max_speed_vector.SetToolTip(
            "Limit the maximum vector speed to this value"
        )
        sizer_30.Add(self.check_max_speed_vector, 1, 0, 0)

        self.text_speed_max = wx.TextCtrl(self, wx.ID_ANY, "100")
        self.text_speed_max.SetToolTip(
            "maximum speed at which all greater speeds are limited"
        )
        sizer_30.Add(self.text_speed_max, 1, 0, 0)

        sizer_31 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_speed.Add(sizer_31, 1, wx.EXPAND, 0)

        self.check_max_speed_raster = wx.CheckBox(self, wx.ID_ANY, "Max Speed (Raster)")
        self.check_max_speed_raster.SetToolTip(
            "Limit the maximum raster speed to this value"
        )
        sizer_31.Add(self.check_max_speed_raster, 1, 0, 0)

        self.text_speed_max_copy = wx.TextCtrl(self, wx.ID_ANY, "750")
        self.text_speed_max_copy.SetToolTip(
            "maximum speed at which all greater speeds are limited"
        )
        sizer_31.Add(self.text_speed_max_copy, 1, 0, 0)

        self.SetSizer(sizer_page_2)

        self.Layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_autolock, self.checkbox_autolock)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_pulse_shift, self.checkbox_plot_shift)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_strict, self.checkbox_strict)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_alt_raster, self.checkbox_alternative_raster
        )
        self.Bind(wx.EVT_CHECKBOX, self.on_check_twitchless, self.checkbox_twitchless)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_rapid_between, self.check_rapid_moves_between
        )
        self.Bind(wx.EVT_CHECKBOX, self.on_check_fix_speeds, self.checkbox_fix_speeds)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_scale_speed, self.check_scale_speed)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_max_speed_vector, self.check_max_speed_vector
        )
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_max_speed_raster, self.check_max_speed_raster
        )
        # end wxGlade

        self.checkbox_fix_speeds.SetValue(self.context.fix_speeds)
        self.checkbox_strict.SetValue(self.context.strict)
        self.checkbox_autolock.SetValue(self.context.autolock)
        self.checkbox_plot_shift.SetValue(self.context.plot_shift)

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    def on_check_fix_speeds(self, event=None):
        self.context.fix_speeds = self.checkbox_fix_speeds.GetValue()

    def on_check_strict(self, event=None):
        self.context.strict = self.checkbox_strict.GetValue()

    def on_check_autolock(self, event=None):
        self.context.autolock = self.checkbox_autolock.GetValue()

    def on_check_pulse_shift(
        self, event=None
    ):  # wxGlade: LhystudiosDriver.<event_handler>
        self.context.plot_shift = self.checkbox_plot_shift.GetValue()
        try:
            _, driver, _ = self.context.root.device()
            driver.plot_planner.force_shift = self.context.plot_shift
        except (AttributeError, TypeError):
            pass

    def on_check_alt_raster(
        self, event
    ):  # wxGlade: ConfigurationSetupPanel.<event_handler>
        print("Event handler 'on_check_alt_raster' not implemented!")
        event.Skip()

    def on_check_twitchless(
        self, event
    ):  # wxGlade: ConfigurationSetupPanel.<event_handler>
        print("Event handler 'on_check_twitchless' not implemented!")
        event.Skip()

    def on_check_rapid_between(
        self, event
    ):  # wxGlade: ConfigurationSetupPanel.<event_handler>
        print("Event handler 'on_check_rapid_between' not implemented!")
        event.Skip()

    def on_check_scale_speed(
        self, event
    ):  # wxGlade: ConfigurationSetupPanel.<event_handler>
        print("Event handler 'on_check_scale_speed' not implemented!")
        event.Skip()

    def on_check_max_speed_vector(
        self, event
    ):  # wxGlade: ConfigurationSetupPanel.<event_handler>
        print("Event handler 'on_check_max_speed_vector' not implemented!")
        event.Skip()

    def on_check_max_speed_raster(
        self, event
    ):  # wxGlade: ConfigurationSetupPanel.<event_handler>
        print("Event handler 'on_check_max_speed_raster' not implemented!")
        event.Skip()


class LhystudiosDriverGui(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(374, 734, *args, **kwds)
        self.context = self.context.device
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Lhystudios-Configuration"))

        # self.notebook_main = wx.Notebook(self, wx.ID_ANY)
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )

        self.ConfigurationPanel = ConfigurationInterfacePanel(
            self.notebook_main, wx.ID_ANY, context=self.context
        )
        self.notebook_main.AddPage(self.ConfigurationPanel, "Configuration")

        self.SetupPanel = ConfigurationSetupPanel(
            self.notebook_main, wx.ID_ANY, context=self.context
        )
        self.notebook_main.AddPage(self.SetupPanel, "Setup")
        self.Layout()

        self.add_module_delegate(self.ConfigurationPanel)
        self.add_module_delegate(self.SetupPanel)

    def window_open(self):
        self.SetupPanel.pane_show()
        self.ConfigurationPanel.pane_show()

    def window_close(self):
        self.SetupPanel.pane_hide()
        self.ConfigurationPanel.pane_hide()

    def window_preserve(self):
        return False
