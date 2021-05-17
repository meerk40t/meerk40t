# -*- coding: ISO-8859-1 -*-

import wx

from .icons import icons8_administrative_tools_50
from .mwindow import MWindow

_ = wx.GetTranslation


class Preferences(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(395, 424, *args, **kwds)

        self.bed_dim = self.context.get_context("/")
        self.bed_dim.setting(int, "bed_width", 310)
        self.bed_dim.setting(int, "bed_height", 210)

        self.combobox_board = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["M2", "B2", "M", "M1", "A", "B", "B1"],
            style=wx.CB_DROPDOWN,
        )
        self.checkbox_flip_x = wx.CheckBox(self, wx.ID_ANY, _("Flip X"))
        self.checkbox_home_right = wx.CheckBox(self, wx.ID_ANY, _("Homes Right"))
        self.checkbox_flip_y = wx.CheckBox(self, wx.ID_ANY, _("Flip Y"))
        self.checkbox_home_bottom = wx.CheckBox(self, wx.ID_ANY, _("Homes Bottom"))
        self.checkbox_swap_xy = wx.CheckBox(self, wx.ID_ANY, _("Swap X and Y"))
        self.checkbox_mock_usb = wx.CheckBox(
            self, wx.ID_ANY, _("Mock USB Connection Mode")
        )
        self.spin_device_index = wx.SpinCtrl(self, wx.ID_ANY, "-1", min=-1, max=5)
        self.spin_device_address = wx.SpinCtrl(self, wx.ID_ANY, "-1", min=-1, max=5)
        self.spin_device_bus = wx.SpinCtrl(self, wx.ID_ANY, "-1", min=-1, max=5)
        self.spin_device_version = wx.SpinCtrl(self, wx.ID_ANY, "-1", min=-1, max=255)
        self.spin_home_x = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "0.0", min=-50000.0, max=50000.0
        )
        self.spin_home_y = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "0.0", min=-50000.0, max=50000.0
        )
        self.button_home_by_current = wx.Button(self, wx.ID_ANY, _("Set Current"))
        self.spin_bedwidth = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "330.0", min=1.0, max=1000.0
        )
        self.spin_bedheight = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "230.0", min=1.0, max=1000.0
        )
        self.checkbox_autolock = wx.CheckBox(
            self, wx.ID_ANY, _("Automatically lock rail")
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_COMBOBOX, self.on_combobox_boardtype, self.combobox_board)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_swap_xy, self.checkbox_swap_xy)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_flip_x, self.checkbox_flip_x)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_home_right, self.checkbox_home_right)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_flip_y, self.checkbox_flip_y)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_home_bottom, self.checkbox_home_bottom)
        self.Bind(wx.EVT_CHECKBOX, self.on_checkbox_mock_usb, self.checkbox_mock_usb)
        self.Bind(wx.EVT_SPINCTRL, self.spin_on_device_index, self.spin_device_index)
        self.Bind(wx.EVT_TEXT, self.spin_on_device_index, self.spin_device_index)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_device_index, self.spin_device_index)
        self.Bind(
            wx.EVT_SPINCTRL, self.spin_on_device_address, self.spin_device_address
        )
        self.Bind(wx.EVT_TEXT, self.spin_on_device_address, self.spin_device_address)
        self.Bind(
            wx.EVT_TEXT_ENTER, self.spin_on_device_address, self.spin_device_address
        )
        self.Bind(wx.EVT_SPINCTRL, self.spin_on_device_bus, self.spin_device_bus)
        self.Bind(wx.EVT_TEXT, self.spin_on_device_bus, self.spin_device_bus)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_device_bus, self.spin_device_bus)
        self.Bind(
            wx.EVT_SPINCTRL, self.spin_on_device_version, self.spin_device_version
        )
        self.Bind(wx.EVT_TEXT, self.spin_on_device_version, self.spin_device_version)
        self.Bind(
            wx.EVT_TEXT_ENTER, self.spin_on_device_version, self.spin_device_version
        )
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.spin_on_home_x, self.spin_home_x)
        self.Bind(wx.EVT_TEXT, self.spin_on_home_x, self.spin_home_x)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_home_x, self.spin_home_x)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.spin_on_home_y, self.spin_home_y)
        self.Bind(wx.EVT_TEXT, self.spin_on_home_y, self.spin_home_y)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_home_y, self.spin_home_y)
        self.Bind(
            wx.EVT_BUTTON, self.on_button_set_home_current, self.button_home_by_current
        )
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.spin_on_bedwidth, self.spin_bedwidth)
        self.Bind(wx.EVT_TEXT, self.spin_on_bedwidth, self.spin_bedwidth)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_bedwidth, self.spin_bedwidth)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.spin_on_bedheight, self.spin_bedheight)
        self.Bind(wx.EVT_TEXT, self.spin_on_bedheight, self.spin_bedheight)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_bedheight, self.spin_bedheight)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_autolock, self.checkbox_autolock)
        # end wxGlade
        self.Bind(
            wx.EVT_KEY_DOWN,
            lambda e: self.context.console("webhelp help\n")
            if e.GetKeyCode() == wx.WXK_F1
            else None,
            self,
        )

    def window_open(self):
        self.context.setting(bool, "swap_xy", False)
        self.context.setting(bool, "flip_x", False)
        self.context.setting(bool, "flip_y", False)
        self.context.setting(bool, "home_right", False)
        self.context.setting(bool, "home_bottom", False)
        self.context.setting(int, "home_adjust_x", 0)
        self.context.setting(int, "home_adjust_y", 0)
        self.context.setting(int, "current_x", 0)
        self.context.setting(int, "current_y", 0)

        self.context.setting(bool, "mock", False)
        self.context.setting(bool, "autolock", True)
        self.context.setting(str, "board", "M2")
        self.context.setting(int, "units_index", 0)
        self.context.setting(int, "usb_index", -1)
        self.context.setting(int, "usb_bus", -1)
        self.context.setting(int, "usb_address", -1)
        self.context.setting(int, "usb_version", -1)

        self.checkbox_swap_xy.SetValue(self.context.swap_xy)
        self.checkbox_flip_x.SetValue(self.context.flip_x)
        self.checkbox_flip_y.SetValue(self.context.flip_y)
        self.checkbox_home_right.SetValue(self.context.home_right)
        self.checkbox_home_bottom.SetValue(self.context.home_bottom)
        self.checkbox_mock_usb.SetValue(self.context.mock)
        self.checkbox_autolock.SetValue(self.context.autolock)
        self.combobox_board.SetValue(self.context.board)
        self.spin_bedwidth.SetValue(self.bed_dim.bed_width)
        self.spin_bedheight.SetValue(self.bed_dim.bed_height)
        self.spin_device_index.SetValue(self.context.usb_index)
        self.spin_device_bus.SetValue(self.context.usb_bus)
        self.spin_device_address.SetValue(self.context.usb_address)
        self.spin_device_version.SetValue(self.context.usb_version)
        self.spin_home_x.SetValue(self.context.home_adjust_x)
        self.spin_home_y.SetValue(self.context.home_adjust_y)

    def window_close(self):
        pass

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Preferences.__set_properties
        self.SetTitle(_("Preferences"))
        self.combobox_board.SetToolTip(
            _("Select the board to use. This has affects the speedcodes used.")
        )
        self.combobox_board.SetSelection(0)
        self.checkbox_swap_xy.SetToolTip(
            _("Swaps the X and Y axis. This happens before the FlipX and FlipY.")
        )
        self.checkbox_flip_x.SetToolTip(
            _("Flip the Right and Left commands sent to the controller")
        )
        self.checkbox_home_right.SetToolTip(
            _("Indicates the device Home is on the right")
        )
        self.checkbox_flip_y.SetToolTip(
            _("Flip the Top and Bottom commands sent to the controller")
        )
        self.checkbox_home_bottom.SetToolTip(
            _("Indicates the device Home is on the bottom")
        )
        self.checkbox_mock_usb.SetToolTip(
            _(
                "DEBUG. Without a K40 connected continue to process things as if there was one."
            )
        )
        self.spin_device_index.SetToolTip(
            _("-1 match anything. 0-5 match exactly that value.")
        )
        self.spin_device_address.SetToolTip(
            _("-1 match anything. 0-5 match exactly that value.")
        )
        self.spin_device_bus.SetToolTip(
            _("-1 match anything. 0-5 match exactly that value.")
        )
        self.spin_device_version.SetToolTip(
            _("-1 match anything. 0-255 match exactly that value.")
        )
        self.spin_home_x.SetMinSize((80, 23))
        self.spin_home_x.SetToolTip(_("Translate Home X"))
        self.spin_home_y.SetMinSize((80, 23))
        self.spin_home_y.SetToolTip(_("Translate Home Y"))
        self.button_home_by_current.SetToolTip(
            _("Set Home Position based on the current position")
        )
        self.spin_bedwidth.SetMinSize((80, 23))
        self.spin_bedwidth.SetToolTip(_("Width of the laser bed."))
        self.spin_bedheight.SetMinSize((80, 23))
        self.spin_bedheight.SetToolTip(_("Height of the laser bed."))
        self.checkbox_autolock.SetToolTip(_("Lock rail after operations are finished."))
        self.checkbox_autolock.SetValue(1)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Preferences.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_general = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("General Options")), wx.VERTICAL
        )
        sizer_bed = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Bed Dimensions")), wx.HORIZONTAL
        )
        sizer_home = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Shift Home Position")), wx.HORIZONTAL
        )
        sizer_usb = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("USB Settings")), wx.VERTICAL
        )
        sizer_12 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_11 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_board = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Board Setup")), wx.HORIZONTAL
        )
        sizer_16 = wx.BoxSizer(wx.VERTICAL)
        sizer_17 = wx.BoxSizer(wx.VERTICAL)
        sizer_board.Add(self.combobox_board, 0, 0, 0)
        sizer_board.Add((20, 20), 0, 0, 0)
        sizer_17.Add(self.checkbox_flip_x, 0, 0, 0)
        sizer_17.Add(self.checkbox_home_right, 0, 0, 0)
        sizer_board.Add(sizer_17, 1, wx.EXPAND, 0)
        sizer_16.Add(self.checkbox_flip_y, 0, 0, 0)
        sizer_16.Add(self.checkbox_home_bottom, 0, 0, 0)
        sizer_board.Add(sizer_16, 1, wx.EXPAND, 0)
        sizer_board.Add(self.checkbox_swap_xy, 0, 0, 0)
        sizer_1.Add(sizer_board, 1, wx.EXPAND, 0)
        sizer_usb.Add(self.checkbox_mock_usb, 0, 0, 0)
        label_6 = wx.StaticText(self, wx.ID_ANY, _("Device Index:"))
        sizer_3.Add(label_6, 1, 0, 0)
        sizer_3.Add(self.spin_device_index, 1, 0, 0)
        sizer_usb.Add(sizer_3, 1, wx.EXPAND, 0)
        label_7 = wx.StaticText(self, wx.ID_ANY, _("Device Address:"))
        sizer_10.Add(label_7, 1, 0, 0)
        sizer_10.Add(self.spin_device_address, 1, 0, 0)
        sizer_usb.Add(sizer_10, 1, wx.EXPAND, 0)
        label_8 = wx.StaticText(self, wx.ID_ANY, _("Device Bus:"))
        sizer_11.Add(label_8, 1, 0, 0)
        sizer_11.Add(self.spin_device_bus, 1, 0, 0)
        sizer_usb.Add(sizer_11, 1, wx.EXPAND, 0)
        label_13 = wx.StaticText(self, wx.ID_ANY, _("Chip Version:"))
        sizer_12.Add(label_13, 1, 0, 0)
        sizer_12.Add(self.spin_device_version, 1, 0, 0)
        sizer_usb.Add(sizer_12, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_usb, 1, wx.EXPAND, 0)
        label_9 = wx.StaticText(self, wx.ID_ANY, _("X"))
        sizer_home.Add(label_9, 0, 0, 0)
        sizer_home.Add(self.spin_home_x, 0, 0, 0)
        label_12 = wx.StaticText(self, wx.ID_ANY, _("mil"))
        sizer_home.Add(label_12, 0, 0, 0)
        sizer_home.Add((20, 20), 0, 0, 0)
        label_10 = wx.StaticText(self, wx.ID_ANY, _("Y"))
        sizer_home.Add(label_10, 0, 0, 0)
        sizer_home.Add(self.spin_home_y, 0, 0, 0)
        label_11 = wx.StaticText(self, wx.ID_ANY, _("mil"))
        sizer_home.Add(label_11, 0, 0, 0)
        sizer_home.Add((20, 20), 0, 0, 0)
        sizer_home.Add(self.button_home_by_current, 0, 0, 0)
        sizer_1.Add(sizer_home, 1, wx.EXPAND, 0)
        label_2 = wx.StaticText(self, wx.ID_ANY, _("Width"))
        sizer_bed.Add(label_2, 0, 0, 0)
        sizer_bed.Add(self.spin_bedwidth, 0, 0, 0)
        label_17 = wx.StaticText(self, wx.ID_ANY, _("mm"))
        sizer_bed.Add(label_17, 0, 0, 0)
        sizer_bed.Add((20, 20), 0, 0, 0)
        label_3 = wx.StaticText(self, wx.ID_ANY, _("Height"))
        sizer_bed.Add(label_3, 0, 0, 0)
        sizer_bed.Add(self.spin_bedheight, 0, 0, 0)
        label_18 = wx.StaticText(self, wx.ID_ANY, _("mm"))
        sizer_bed.Add(label_18, 0, 0, 0)
        sizer_1.Add(sizer_bed, 1, wx.EXPAND, 0)
        sizer_general.Add(self.checkbox_autolock, 0, 0, 0)
        sizer_1.Add(sizer_general, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def calc_home_position(self):
        x = 0
        y = 0
        if self.context.home_right:
            x = int(self.bed_dim.bed_width * 39.3701)
        if self.context.home_bottom:
            y = int(self.bed_dim.bed_height * 39.3701)
        return x, y

    def on_combobox_boardtype(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.board = self.combobox_board.GetValue()

    def on_check_swap_xy(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.swap_xy = self.checkbox_swap_xy.GetValue()
        self.context("dev code_update\n")

    def on_check_flip_x(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.flip_x = self.checkbox_flip_x.GetValue()
        self.context("dev code_update\n")

    def on_check_home_right(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.home_right = self.checkbox_home_right.GetValue()

    def on_check_flip_y(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.flip_y = self.checkbox_flip_y.GetValue()
        self.context("dev code_update\n")

    def on_check_home_bottom(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.home_bottom = self.checkbox_home_bottom.GetValue()

    def spin_on_home_x(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.home_adjust_x = int(self.spin_home_x.GetValue())

    def spin_on_home_y(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.home_adjust_y = int(self.spin_home_y.GetValue())

    def on_button_set_home_current(self, event):  # wxGlade: Preferences.<event_handler>
        x, y = self.calc_home_position()
        current_x = self.context.current_x - x
        current_y = self.context.current_y - y
        self.context.home_adjust_x = int(current_x)
        self.context.home_adjust_y = int(current_y)
        self.spin_home_x.SetValue(self.context.home_adjust_x)
        self.spin_home_y.SetValue(self.context.home_adjust_y)

    def spin_on_bedwidth(self, event):  # wxGlade: Preferences.<event_handler>
        self.bed_dim.bed_width = int(self.spin_bedwidth.GetValue())
        self.bed_dim.bed_height = int(self.spin_bedheight.GetValue())
        self.context.signal(
            "bed_size", (self.bed_dim.bed_width, self.bed_dim.bed_height)
        )

    def spin_on_bedheight(self, event):  # wxGlade: Preferences.<event_handler>
        self.bed_dim.bed_width = int(self.spin_bedwidth.GetValue())
        self.bed_dim.bed_height = int(self.spin_bedheight.GetValue())
        self.context.signal(
            "bed_size", (self.bed_dim.bed_width, self.bed_dim.bed_height)
        )

    def on_check_autolock(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.autolock = self.checkbox_autolock.GetValue()

    def spin_on_device_index(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.usb_index = int(self.spin_device_index.GetValue())

    def spin_on_device_address(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.usb_address = int(self.spin_device_address.GetValue())

    def spin_on_device_bus(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.usb_bus = int(self.spin_device_bus.GetValue())

    def spin_on_device_version(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.usb_version = int(self.spin_device_version.GetValue())

    def on_checkbox_mock_usb(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.mock = self.checkbox_mock_usb.GetValue()
