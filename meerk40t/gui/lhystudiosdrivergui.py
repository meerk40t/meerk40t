# -*- coding: ISO-8859-1 -*-

import wx

from .icons import icons8_administrative_tools_50
from .mwindow import MWindow

_ = wx.GetTranslation


class LhystudiosDriverGui(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(393, 533, *args, **kwds)
        self.bed_dim = self.context.get_context("/")
        self.bed_dim.setting(int, "bed_width", 310)
        self.bed_dim.setting(int, "bed_height", 210)

        self.combobox_board = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["M2", "B2", "M", "M1", "A", "B", "B1"],
            style=wx.CB_DROPDOWN,
        )
        self.checkbox_fix_speeds = wx.CheckBox(
            self, wx.ID_ANY, "Fix rated to actual speed"
        )
        self.checkbox_flip_x = wx.CheckBox(self, wx.ID_ANY, "Flip X")
        self.checkbox_home_right = wx.CheckBox(self, wx.ID_ANY, "Home Right")
        self.checkbox_flip_y = wx.CheckBox(self, wx.ID_ANY, "Flip Y")
        self.checkbox_home_bottom = wx.CheckBox(self, wx.ID_ANY, "Home Bottom")
        self.checkbox_swap_xy = wx.CheckBox(self, wx.ID_ANY, "Swap X and Y")
        self.checkbox_strict = wx.CheckBox(self, wx.ID_ANY, "Strict")
        self.spin_home_x = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "0.0", min=-50000.0, max=50000.0
        )
        self.spin_home_y = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "0.0", min=-50000.0, max=50000.0
        )
        self.button_home_by_current = wx.Button(self, wx.ID_ANY, "Set Current")
        self.checkbox_plot_shift = wx.CheckBox(self, wx.ID_ANY, "Pulse Shifting")
        self.checkbox_random_ppi = wx.CheckBox(self, wx.ID_ANY, "Randomize PPI")
        self.checkbox_limit_buffer = wx.CheckBox(self, wx.ID_ANY, "Limit Write Buffer")
        self.text_buffer_length = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.spin_packet_buffer_max = wx.SpinCtrl(
            self, wx.ID_ANY, "1500", min=1, max=1000000
        )
        self.checkbox_autolock = wx.CheckBox(self, wx.ID_ANY, "Automatically lock rail")
        self.checkbox_vector_accel_enable = wx.CheckBox(self, wx.ID_ANY, "Enable")
        self.text_vector_accel_1 = wx.TextCtrl(self, wx.ID_ANY, "25.4")
        self.text_vector_accel_2 = wx.TextCtrl(self, wx.ID_ANY, "60")
        self.text_vector_accel_3 = wx.TextCtrl(self, wx.ID_ANY, "127")
        self.text_vector_accel_4 = wx.TextCtrl(self, wx.ID_ANY, "infinity")
        self.checkbox_raster_accel_enable = wx.CheckBox(self, wx.ID_ANY, "Enable")
        self.text_raster_accel_1 = wx.TextCtrl(self, wx.ID_ANY, "25.4")
        self.text_raster_accel_2 = wx.TextCtrl(self, wx.ID_ANY, "127")
        self.text_raster_accel_3 = wx.TextCtrl(self, wx.ID_ANY, "320")
        self.text_raster_accel_4 = wx.TextCtrl(self, wx.ID_ANY, "infinity")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_COMBOBOX, self.on_combobox_boardtype, self.combobox_board)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_fix_speeds, self.checkbox_fix_speeds)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_strict, self.checkbox_strict)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_swap_xy, self.checkbox_swap_xy)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_flip_x, self.checkbox_flip_x)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_home_right, self.checkbox_home_right)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_flip_y, self.checkbox_flip_y)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_home_bottom, self.checkbox_home_bottom)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.spin_on_home_x, self.spin_home_x)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_home_x, self.spin_home_x)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.spin_on_home_y, self.spin_home_y)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_home_y, self.spin_home_y)
        self.Bind(
            wx.EVT_BUTTON, self.on_button_set_home_current, self.button_home_by_current
        )
        self.Bind(wx.EVT_CHECKBOX, self.on_check_pulse_shift, self.checkbox_plot_shift)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_random_ppi, self.checkbox_random_ppi)
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
        self.Bind(wx.EVT_CHECKBOX, self.on_check_autolock, self.checkbox_autolock)
        self.Bind(
            wx.EVT_CHECKBOX,
            self.on_check_vector_accel_enable,
            self.checkbox_vector_accel_enable,
        )
        self.Bind(wx.EVT_TEXT, self.on_text_vector_accel, self.text_vector_accel_1)
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_text_vector_accel, self.text_vector_accel_1
        )
        self.Bind(wx.EVT_TEXT, self.on_text_vector_accel, self.text_vector_accel_2)
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_text_vector_accel, self.text_vector_accel_2
        )
        self.Bind(wx.EVT_TEXT, self.on_text_vector_accel, self.text_vector_accel_3)
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_text_vector_accel, self.text_vector_accel_3
        )
        self.Bind(wx.EVT_TEXT, self.on_text_vector_accel, self.text_vector_accel_4)
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_text_vector_accel, self.text_vector_accel_4
        )
        self.Bind(
            wx.EVT_CHECKBOX,
            self.on_check_raster_accel_enable,
            self.checkbox_raster_accel_enable,
        )
        self.Bind(wx.EVT_TEXT, self.on_text_raster_accel, self.text_raster_accel_1)
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_text_raster_accel, self.text_raster_accel_1
        )
        self.Bind(wx.EVT_TEXT, self.on_text_raster_accel, self.text_raster_accel_2)
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_text_raster_accel, self.text_raster_accel_2
        )
        self.Bind(wx.EVT_TEXT, self.on_text_raster_accel, self.text_raster_accel_3)
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_text_raster_accel, self.text_raster_accel_3
        )
        self.Bind(wx.EVT_TEXT, self.on_text_raster_accel, self.text_raster_accel_4)
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_text_raster_accel, self.text_raster_accel_4
        )
        # end wxGlade
        self.Bind(
            wx.EVT_KEY_DOWN,
            lambda e: self.context.console("webhelp help\n")
            if e.GetKeyCode() == wx.WXK_F1
            else None,
            self,
        )
        self.set_widgets()

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle("Lhystudios-Prefererences")
        self.combobox_board.SetToolTip(
            "Select the board to use. This has an effects the speedcodes used."
        )
        self.combobox_board.SetSelection(0)
        self.checkbox_fix_speeds.SetToolTip(
            "Correct for speed invalidity. Lhystudios speeds are 92% of the correctly rated speed."
        )
        self.checkbox_flip_x.SetToolTip(
            "Flip the Right and Left commands sent to the controller"
        )
        self.checkbox_home_right.SetToolTip("Indicates the device Home is on the right")
        self.checkbox_flip_y.SetToolTip(
            "Flip the Top and Bottom commands sent to the controller"
        )
        self.checkbox_home_bottom.SetToolTip(
            "Indicates the device Home is on the bottom"
        )
        self.checkbox_swap_xy.SetToolTip(
            "Swaps the X and Y axis. This happens before the FlipX and FlipY."
        )
        self.checkbox_strict.SetToolTip(
            "Forces the device to enter and exit programmed speed mode from the same direction.\nThis may prevent devices like the M2-V4 and earlier from having issues. Not typically needed."
        )
        self.spin_home_x.SetMinSize((80, 23))
        self.spin_home_x.SetToolTip("Translate Home X")
        self.spin_home_x.Enable(False)
        self.spin_home_y.SetMinSize((80, 23))
        self.spin_home_y.SetToolTip("Translate Home Y")
        self.spin_home_y.Enable(False)
        self.button_home_by_current.SetToolTip(
            "Set Home Position based on the current position"
        )
        self.button_home_by_current.Enable(False)
        self.checkbox_plot_shift.SetToolTip(
            "During the pulse planning process allow shifting pulses by one unit to increase command efficiency\nThis may prevent device stutter and reduce pulse accuracy by one up to one unit."
        )
        self.checkbox_random_ppi.SetToolTip(
            "Rather than orderly PPI, we perform PPI based on a randomized average"
        )
        self.checkbox_random_ppi.Enable(False)
        self.checkbox_limit_buffer.SetToolTip(
            "Limit the write buffer to a certain amount. Permits on-the-fly command production."
        )
        self.checkbox_limit_buffer.SetValue(1)
        self.text_buffer_length.SetToolTip(
            "Current number of bytes in the write buffer."
        )
        self.spin_packet_buffer_max.SetToolTip("Current maximum write buffer limit.")
        self.checkbox_autolock.SetToolTip("Lock rail after operations are finished.")
        self.checkbox_autolock.SetValue(1)
        self.checkbox_vector_accel_enable.SetToolTip(
            "Enable defined acceleration chart for vectors"
        )
        self.checkbox_vector_accel_enable.Enable(False)
        self.text_vector_accel_1.SetMinSize((55, 23))
        self.text_vector_accel_1.SetToolTip("Upper limit for accel level 1")
        self.text_vector_accel_1.Enable(False)
        self.text_vector_accel_2.SetMinSize((55, 23))
        self.text_vector_accel_2.SetToolTip("Upper limit for accel level 2")
        self.text_vector_accel_2.Enable(False)
        self.text_vector_accel_3.SetMinSize((55, 23))
        self.text_vector_accel_3.SetToolTip("Upper limit for accel level 3")
        self.text_vector_accel_3.Enable(False)
        self.text_vector_accel_4.SetMinSize((55, 23))
        self.text_vector_accel_4.SetToolTip("Upper limit for accel level 4")
        self.text_vector_accel_4.Enable(False)
        self.checkbox_raster_accel_enable.SetToolTip(
            "Enable defined acceleration chart for horizontal rasters"
        )
        self.checkbox_raster_accel_enable.Enable(False)
        self.text_raster_accel_1.SetMinSize((55, 23))
        self.text_raster_accel_1.SetToolTip("Upper limit for accel level 1")
        self.text_raster_accel_1.Enable(False)
        self.text_raster_accel_2.SetMinSize((55, 23))
        self.text_raster_accel_2.SetToolTip("Upper limit for accel level 2")
        self.text_raster_accel_2.Enable(False)
        self.text_raster_accel_3.SetMinSize((55, 23))
        self.text_raster_accel_3.SetToolTip("Upper limit for accel level 3")
        self.text_raster_accel_3.Enable(False)
        self.text_raster_accel_4.SetMinSize((55, 23))
        self.text_raster_accel_4.SetToolTip("Upper limit for accel level 4")
        self.text_raster_accel_4.Enable(False)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: LhystudiosDriver.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_accel = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Acceleration Chart"), wx.HORIZONTAL
        )
        sizer_13 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Raster"), wx.VERTICAL
        )
        sizer_19 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_18 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_15 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_14 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_8 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Vector"), wx.VERTICAL
        )
        sizer_12 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_11 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_9 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_general = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "General Options"), wx.HORIZONTAL
        )
        sizer_buffer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Write Buffer"), wx.HORIZONTAL
        )
        sizer_6 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Plot Planner"), wx.HORIZONTAL
        )
        sizer_home = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Shift Home Position"), wx.HORIZONTAL
        )
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_config = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Configuration"), wx.HORIZONTAL
        )
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_16 = wx.BoxSizer(wx.VERTICAL)
        sizer_17 = wx.BoxSizer(wx.VERTICAL)
        sizer_board = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Board Setup"), wx.HORIZONTAL
        )
        sizer_board.Add(self.combobox_board, 1, 0, 0)
        label_1 = wx.StaticText(self, wx.ID_ANY, "")
        sizer_board.Add(label_1, 1, 0, 0)
        sizer_board.Add(self.checkbox_fix_speeds, 0, 0, 0)
        sizer_main.Add(sizer_board, 1, wx.EXPAND, 0)
        sizer_17.Add(self.checkbox_flip_x, 0, 0, 0)
        sizer_17.Add(self.checkbox_home_right, 0, 0, 0)
        sizer_config.Add(sizer_17, 1, wx.EXPAND, 0)
        sizer_16.Add(self.checkbox_flip_y, 0, 0, 0)
        sizer_16.Add(self.checkbox_home_bottom, 0, 0, 0)
        sizer_config.Add(sizer_16, 1, wx.EXPAND, 0)
        sizer_3.Add(self.checkbox_swap_xy, 0, 0, 0)
        sizer_3.Add(self.checkbox_strict, 0, 0, 0)
        sizer_config.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_config, 1, wx.EXPAND, 0)
        label_9 = wx.StaticText(self, wx.ID_ANY, "X")
        sizer_4.Add(label_9, 0, 0, 0)
        sizer_4.Add(self.spin_home_x, 0, 0, 0)
        label_12 = wx.StaticText(self, wx.ID_ANY, "mil")
        sizer_4.Add(label_12, 0, 0, 0)
        sizer_home.Add(sizer_4, 2, wx.EXPAND, 0)
        label_10 = wx.StaticText(self, wx.ID_ANY, "Y")
        sizer_2.Add(label_10, 0, 0, 0)
        sizer_2.Add(self.spin_home_y, 0, 0, 0)
        label_11 = wx.StaticText(self, wx.ID_ANY, "mil")
        sizer_2.Add(label_11, 1, 0, 0)
        sizer_home.Add(sizer_2, 2, wx.EXPAND, 0)
        sizer_home.Add(self.button_home_by_current, 1, 0, 0)
        sizer_main.Add(sizer_home, 1, wx.EXPAND, 0)
        sizer_6.Add(self.checkbox_plot_shift, 1, 0, 0)
        sizer_6.Add(self.checkbox_random_ppi, 0, 0, 0)
        sizer_main.Add(sizer_6, 1, wx.EXPAND, 0)
        sizer_buffer.Add(self.checkbox_limit_buffer, 1, 0, 0)
        sizer_buffer.Add(self.text_buffer_length, 1, 0, 0)
        label_14 = wx.StaticText(self, wx.ID_ANY, "/")
        sizer_buffer.Add(label_14, 0, 0, 0)
        sizer_buffer.Add(self.spin_packet_buffer_max, 1, 0, 0)
        sizer_main.Add(sizer_buffer, 0, 0, 0)
        sizer_general.Add(self.checkbox_autolock, 0, 0, 0)
        sizer_main.Add(sizer_general, 0, wx.EXPAND, 0)
        sizer_8.Add(self.checkbox_vector_accel_enable, 0, 0, 0)
        label_2 = wx.StaticText(self, wx.ID_ANY, "1 <")
        sizer_9.Add(label_2, 1, 0, 0)
        sizer_9.Add(self.text_vector_accel_1, 1, 0, 0)
        label_3 = wx.StaticText(self, wx.ID_ANY, "mm/s")
        sizer_9.Add(label_3, 1, 0, 0)
        sizer_8.Add(sizer_9, 1, wx.EXPAND, 0)
        label_4 = wx.StaticText(self, wx.ID_ANY, "2 <")
        sizer_10.Add(label_4, 1, 0, 0)
        sizer_10.Add(self.text_vector_accel_2, 1, 0, 0)
        label_5 = wx.StaticText(self, wx.ID_ANY, "mm/s")
        sizer_10.Add(label_5, 1, 0, 0)
        sizer_8.Add(sizer_10, 1, wx.EXPAND, 0)
        label_6 = wx.StaticText(self, wx.ID_ANY, "3 <")
        sizer_11.Add(label_6, 1, 0, 0)
        sizer_11.Add(self.text_vector_accel_3, 1, 0, 0)
        label_7 = wx.StaticText(self, wx.ID_ANY, "mm/s")
        sizer_11.Add(label_7, 1, 0, 0)
        sizer_8.Add(sizer_11, 1, wx.EXPAND, 0)
        label_8 = wx.StaticText(self, wx.ID_ANY, "4 <")
        sizer_12.Add(label_8, 1, 0, 0)
        sizer_12.Add(self.text_vector_accel_4, 1, 0, 0)
        label_13 = wx.StaticText(self, wx.ID_ANY, "mm/s")
        sizer_12.Add(label_13, 1, 0, 0)
        sizer_8.Add(sizer_12, 1, wx.EXPAND, 0)
        sizer_accel.Add(sizer_8, 1, wx.EXPAND, 0)
        sizer_13.Add(self.checkbox_raster_accel_enable, 0, 0, 0)
        label_15 = wx.StaticText(self, wx.ID_ANY, "1 <")
        sizer_14.Add(label_15, 1, 0, 0)
        sizer_14.Add(self.text_raster_accel_1, 1, 0, 0)
        label_16 = wx.StaticText(self, wx.ID_ANY, "mm/s")
        sizer_14.Add(label_16, 1, 0, 0)
        sizer_13.Add(sizer_14, 1, wx.EXPAND, 0)
        label_17 = wx.StaticText(self, wx.ID_ANY, "2 <")
        sizer_15.Add(label_17, 1, 0, 0)
        sizer_15.Add(self.text_raster_accel_2, 1, 0, 0)
        label_18 = wx.StaticText(self, wx.ID_ANY, "mm/s")
        sizer_15.Add(label_18, 1, 0, 0)
        sizer_13.Add(sizer_15, 1, wx.EXPAND, 0)
        label_19 = wx.StaticText(self, wx.ID_ANY, "3 <")
        sizer_18.Add(label_19, 1, 0, 0)
        sizer_18.Add(self.text_raster_accel_3, 1, 0, 0)
        label_20 = wx.StaticText(self, wx.ID_ANY, "mm/s")
        sizer_18.Add(label_20, 1, 0, 0)
        sizer_13.Add(sizer_18, 1, wx.EXPAND, 0)
        label_21 = wx.StaticText(self, wx.ID_ANY, "4 <")
        sizer_19.Add(label_21, 1, 0, 0)
        sizer_19.Add(self.text_raster_accel_4, 1, 0, 0)
        label_22 = wx.StaticText(self, wx.ID_ANY, "mm/s")
        sizer_19.Add(label_22, 1, 0, 0)
        sizer_13.Add(sizer_19, 1, wx.EXPAND, 0)
        sizer_accel.Add(sizer_13, 4, wx.EXPAND, 0)
        sizer_main.Add(sizer_accel, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.Layout()
        # end wxGlade

    def window_open(self):
        pass

    def window_close(self):
        pass

    def set_widgets(self):
        context = self.context
        context.setting(bool, "fix_speeds", False)
        context.setting(bool, "swap_xy", False)
        context.setting(bool, "flip_x", False)
        context.setting(bool, "flip_y", False)
        context.setting(bool, "home_right", False)
        context.setting(bool, "home_bottom", False)
        context.setting(bool, "strict", False)

        context.setting(int, "home_adjust_x", 0)
        context.setting(int, "home_adjust_y", 0)
        context.setting(int, "current_x", 0)
        context.setting(int, "current_y", 0)
        context.setting(bool, "autolock", True)
        context.setting(str, "board", "M2")
        context.setting(bool, "buffer_limit", True)
        context.setting(int, "buffer_max", 1500)
        context.setting(bool, "random_ppi", False)
        context.setting(bool, "plot_shift", False)
        context.setting(bool, "raster_accel_table", False)
        context.setting(bool, "vector_accel_table", False)

        self.checkbox_fix_speeds.SetValue(context.fix_speeds)
        self.checkbox_swap_xy.SetValue(context.swap_xy)
        self.checkbox_flip_x.SetValue(context.flip_x)
        self.checkbox_flip_y.SetValue(context.flip_y)
        self.checkbox_home_right.SetValue(context.home_right)
        self.checkbox_home_bottom.SetValue(context.home_bottom)
        self.checkbox_strict.SetValue(context.strict)

        self.spin_home_x.SetValue(context.home_adjust_x)
        self.spin_home_y.SetValue(context.home_adjust_y)
        self.checkbox_autolock.SetValue(context.autolock)
        self.combobox_board.SetValue(context.board)
        self.checkbox_limit_buffer.SetValue(context.buffer_limit)
        self.spin_packet_buffer_max.SetValue(context.buffer_max)

        self.checkbox_random_ppi.SetValue(context.random_ppi)
        self.checkbox_plot_shift.SetValue(context.plot_shift)

        self.checkbox_raster_accel_enable.SetValue(context.raster_accel_table)
        self.checkbox_vector_accel_enable.SetValue(context.vector_accel_table)

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
        self.context.execute("Update Codes")

    def on_check_fix_speeds(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.fix_speeds = self.checkbox_fix_speeds.GetValue()

    def on_check_strict(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.strict = self.checkbox_strict.GetValue()

    def on_check_flip_x(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.flip_x = self.checkbox_flip_x.GetValue()
        self.context.execute("Update Codes")

    def on_check_home_right(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.home_right = self.checkbox_home_right.GetValue()

    def on_check_flip_y(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.flip_y = self.checkbox_flip_y.GetValue()
        self.context.execute("Update Codes")

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

    def on_check_autolock(self, event):  # wxGlade: Preferences.<event_handler>
        self.context.autolock = self.checkbox_autolock.GetValue()

    def on_check_limit_packet_buffer(self, event):  # wxGlade: JobInfo.<event_handler>
        self.context.buffer_limit = self.checkbox_limit_buffer.GetValue()

    def on_spin_packet_buffer_max(self, event):  # wxGlade: JobInfo.<event_handler>
        self.context.buffer_max = self.spin_packet_buffer_max.GetValue()

    def on_check_vector_accel_enable(
        self, event
    ):  # wxGlade: LhystudiosDriver.<event_handler>

        self.context.vector_accel_table = self.checkbox_vector_accel_enable.GetValue()

    def on_text_vector_accel(self, event):  # wxGlade: LhystudiosDriver.<event_handler>
        pass

    def on_check_raster_accel_enable(
        self, event
    ):  # wxGlade: LhystudiosDriver.<event_handler>
        self.context.raster_accel_table = self.checkbox_vector_accel_enable.GetValue()

    def on_text_raster_accel(self, event):  # wxGlade: LhystudiosDriver.<event_handler>
        pass

    def on_check_pulse_shift(self, event):  # wxGlade: LhystudiosDriver.<event_handler>
        self.context.plot_shift = self.checkbox_plot_shift.GetValue()

    def on_check_random_ppi(self, event):  # wxGlade: LhystudiosDriver.<event_handler>
        self.context.random_ppi = self.checkbox_random_ppi.GetValue()
