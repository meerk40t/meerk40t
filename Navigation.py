# -*- coding: ISO-8859-1 -*-
#
# generated by wxGlade 0.9.3 on Thu Jun 27 21:45:40 2019
#

import wx

from Kernel import Module
from icons import *

_ = wx.GetTranslation

MILS_IN_MM = 39.3701


class Navigation(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: Navigation.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.FRAME_FLOAT_ON_PARENT
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((598, 429))
        self.spin_jog_mils = wx.SpinCtrlDouble(self, wx.ID_ANY, "394.0", min=0.0, max=10000.0)
        self.spin_jog_mm = wx.SpinCtrlDouble(self, wx.ID_ANY, "10.0", min=0.0, max=254.0)
        self.spin_jog_cm = wx.SpinCtrlDouble(self, wx.ID_ANY, "1.0", min=0.0, max=25.4)
        self.spin_jog_inch = wx.SpinCtrlDouble(self, wx.ID_ANY, "0.394", min=0.0, max=10.0)
        self.button_navigate_up_left = wx.BitmapButton(self, wx.ID_ANY, icons8_up_left_50.GetBitmap())
        self.button_navigate_up = wx.BitmapButton(self, wx.ID_ANY, icons8_up_50.GetBitmap())
        self.button_navigate_up_right = wx.BitmapButton(self, wx.ID_ANY, icons8_up_right_50.GetBitmap())
        self.button_navigate_left = wx.BitmapButton(self, wx.ID_ANY, icons8_left_50.GetBitmap())
        self.button_navigate_home = wx.BitmapButton(self, wx.ID_ANY, icons8_home_filled_50.GetBitmap())
        self.button_navigate_right = wx.BitmapButton(self, wx.ID_ANY, icons8_right_50.GetBitmap())
        self.button_navigate_down_left = wx.BitmapButton(self, wx.ID_ANY, icons8_down_left_50.GetBitmap())
        self.button_navigate_down = wx.BitmapButton(self, wx.ID_ANY, icons8_down_50.GetBitmap())
        self.button_navigate_down_right = wx.BitmapButton(self, wx.ID_ANY, icons8_down_right_50.GetBitmap())
        self.button_navigate_unlock = wx.BitmapButton(self, wx.ID_ANY, icons8_padlock_50.GetBitmap())
        self.button_navigate_lock = wx.BitmapButton(self, wx.ID_ANY, icons8_lock_50.GetBitmap())
        self.button_align_corner_top_left = wx.BitmapButton(self, wx.ID_ANY, icon_corner1.GetBitmap())
        self.button_align_drag_up = wx.BitmapButton(self, wx.ID_ANY, icons8up.GetBitmap())
        self.button_align_corner_top_right = wx.BitmapButton(self, wx.ID_ANY, icon_corner2.GetBitmap())
        self.button_align_drag_left = wx.BitmapButton(self, wx.ID_ANY, icons8_left.GetBitmap())
        self.button_align_center = wx.BitmapButton(self, wx.ID_ANY, icons8_square_border_50.GetBitmap())
        self.button_align_drag_right = wx.BitmapButton(self, wx.ID_ANY, icons8_right.GetBitmap())
        self.button_align_corner_bottom_left = wx.BitmapButton(self, wx.ID_ANY, icon_corner4.GetBitmap())
        self.button_align_drag_down = wx.BitmapButton(self, wx.ID_ANY, icons8_down.GetBitmap())
        self.button_align_corner_bottom_right = wx.BitmapButton(self, wx.ID_ANY, icon_corner3.GetBitmap())
        self.button_align_trace_hull = wx.BitmapButton(self, wx.ID_ANY, icons8_pentagon_50.GetBitmap())
        self.button_align_trace_quick = wx.BitmapButton(self, wx.ID_ANY, icons8_pentagon_square_50.GetBitmap())
        self.button_scale_down = wx.BitmapButton(self, wx.ID_ANY, icons8_compress_50.GetBitmap())
        self.button_translate_up = wx.BitmapButton(self, wx.ID_ANY, icons8_up_50.GetBitmap())
        self.button_scale_up = wx.BitmapButton(self, wx.ID_ANY, icons8_enlarge_50.GetBitmap())
        self.button_translate_left = wx.BitmapButton(self, wx.ID_ANY, icons8_left_50.GetBitmap())
        self.button_reset = wx.BitmapButton(self, wx.ID_ANY, icons8_delete_50.GetBitmap())
        self.button_translate_right = wx.BitmapButton(self, wx.ID_ANY, icons8_right_50.GetBitmap())
        self.button_rotate_ccw = wx.BitmapButton(self, wx.ID_ANY, icons8_rotate_left_50.GetBitmap())
        self.button_translate_down = wx.BitmapButton(self, wx.ID_ANY, icons8_down_50.GetBitmap())
        self.button_rotate_cw = wx.BitmapButton(self, wx.ID_ANY, icons8_rotate_right_50.GetBitmap())
        self.text_a = wx.TextCtrl(self, wx.ID_ANY, "1.000000")
        self.text_c = wx.TextCtrl(self, wx.ID_ANY, "0.000000")
        self.text_d = wx.TextCtrl(self, wx.ID_ANY, "1.000000")
        self.text_b = wx.TextCtrl(self, wx.ID_ANY, "0.000000")
        self.text_e = wx.TextCtrl(self, wx.ID_ANY, "0.000000")
        self.text_f = wx.TextCtrl(self, wx.ID_ANY, "0.000000")

        self.button_navigate_pulse = wx.BitmapButton(self, wx.ID_ANY, icons8_laser_beam_52.GetBitmap())
        self.spin_pulse_duration = wx.SpinCtrl(self, wx.ID_ANY, "50", min=1, max=1000)
        self.button_navigate_move_to = wx.BitmapButton(self, wx.ID_ANY, icons8_center_of_gravity_50.GetBitmap())
        self.text_position_x = wx.TextCtrl(self, wx.ID_ANY, "0")
        self.text_position_y = wx.TextCtrl(self, wx.ID_ANY, "0")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_jog_distance, self.spin_jog_mils)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_jog_distance, self.spin_jog_mils)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_jog_distance, self.spin_jog_mm)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_jog_distance, self.spin_jog_mm)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_jog_distance, self.spin_jog_cm)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_jog_distance, self.spin_jog_cm)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_jog_distance, self.spin_jog_inch)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_jog_distance, self.spin_jog_inch)
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_home, self.button_navigate_home)
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_ul, self.button_navigate_up_left)
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_u, self.button_navigate_up)
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_ur, self.button_navigate_up_right)
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_l, self.button_navigate_left)
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_r, self.button_navigate_right)
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_dl, self.button_navigate_down_left)
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_d, self.button_navigate_down)
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_dr, self.button_navigate_down_right)
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_unlock, self.button_navigate_unlock)
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_lock, self.button_navigate_lock)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_corner_tl, self.button_align_corner_top_left)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_drag_up, self.button_align_drag_up)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_corner_tr, self.button_align_corner_top_right)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_drag_left, self.button_align_drag_left)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_center, self.button_align_center)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_drag_right, self.button_align_drag_right)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_corner_bl, self.button_align_corner_bottom_left)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_drag_down, self.button_align_drag_down)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_corner_br, self.button_align_corner_bottom_right)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_trace_hull, self.button_align_trace_hull)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_trace_quick, self.button_align_trace_quick)
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_pulse, self.button_navigate_pulse)

        self.Bind(wx.EVT_BUTTON, self.on_scale_down, self.button_scale_down)
        self.Bind(wx.EVT_BUTTON, self.on_translate_up, self.button_translate_up)
        self.Bind(wx.EVT_BUTTON, self.on_scale_up, self.button_scale_up)
        self.Bind(wx.EVT_BUTTON, self.on_translate_left, self.button_translate_left)
        self.Bind(wx.EVT_BUTTON, self.on_reset, self.button_reset)
        self.Bind(wx.EVT_BUTTON, self.on_translate_right, self.button_translate_right)
        self.Bind(wx.EVT_BUTTON, self.on_rotate_ccw, self.button_rotate_ccw)
        self.Bind(wx.EVT_BUTTON, self.on_translate_down, self.button_translate_down)
        self.Bind(wx.EVT_BUTTON, self.on_rotate_cw, self.button_rotate_cw)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_a)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_c)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_e)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_b)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_d)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_f)

        self.Bind(wx.EVT_SPINCTRL, self.on_spin_pulse_duration, self.spin_pulse_duration)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_pulse_duration, self.spin_pulse_duration)
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_move_to, self.button_navigate_move_to)
        # end wxGlade
        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.elements = None
        self.console = None
        self.design_locked = False
        self.drag_ready(False)
        self.select_ready(False)

    def on_close(self, event):
        kernel = self.device.device_root
        self.device.remove('window', self.name)
        kernel.unlisten('emphasized', self.on_emphasized_elements_changed)
        self.device.unlisten('interpreter;position', self.on_position_update)

        event.Skip()  # Call destroy.

    def __set_properties(self):
        # begin wxGlade: Navigation.__set_properties
        self.SetTitle(_("Navigation"))
        self.spin_jog_mils.SetMinSize((80, 23))
        self.spin_jog_mils.SetToolTip(_("Set Jog Distance in mils (1/1000th of an inch)"))
        self.spin_jog_mm.SetMinSize((80, 23))
        self.spin_jog_mm.SetToolTip(_("Set Jog Distance in mm"))
        self.spin_jog_cm.SetMinSize((80, 23))
        self.spin_jog_cm.SetToolTip(_("Set Jog Distance in cm"))
        self.spin_jog_inch.SetMinSize((80, 23))
        self.spin_jog_inch.SetToolTip(_("Set Jog Distance in inch"))
        self.button_navigate_up_left.SetToolTip(_("Move laser diagonally in the up and left direction"))
        self.button_navigate_up_left.SetSize(self.button_navigate_up_left.GetBestSize())
        self.button_navigate_up.SetToolTip(_("Move laser in the up direction"))
        self.button_navigate_up.SetSize(self.button_navigate_up.GetBestSize())
        self.button_navigate_up_right.SetToolTip(_("Move laser diagonally in the up and right direction"))
        self.button_navigate_up_right.SetSize(self.button_navigate_up_right.GetBestSize())
        self.button_navigate_left.SetToolTip(_("Move laser in the left direction"))
        self.button_navigate_left.SetSize(self.button_navigate_left.GetBestSize())
        self.button_navigate_home.SetSize(self.button_navigate_home.GetBestSize())
        self.button_navigate_right.SetToolTip(_("Move laser in the right direction"))
        self.button_navigate_right.SetSize(self.button_navigate_right.GetBestSize())
        self.button_navigate_down_left.SetToolTip(_("Move laser diagonally in the down and left direction"))
        self.button_navigate_down_left.SetSize(self.button_navigate_down_left.GetBestSize())
        self.button_navigate_down.SetToolTip(_("Move laser in the down direction"))
        self.button_navigate_down.SetSize(self.button_navigate_down.GetBestSize())
        self.button_navigate_down_right.SetToolTip(_("Move laser diagonally in the down and right direction"))
        self.button_navigate_down_right.SetSize(self.button_navigate_down_right.GetBestSize())
        self.button_navigate_unlock.SetToolTip(_("Unlock the laser rail"))
        self.button_navigate_unlock.SetSize(self.button_navigate_unlock.GetBestSize())
        self.button_navigate_lock.SetToolTip(_("Lock the laser rail"))
        self.button_navigate_lock.SetSize(self.button_navigate_lock.GetBestSize())
        self.button_align_corner_top_left.SetToolTip(_("Align laser with the upper left corner of the selection"))
        self.button_align_corner_top_left.SetSize(self.button_align_corner_top_left.GetBestSize())
        self.button_align_drag_up.SetSize(self.button_align_drag_up.GetBestSize())
        self.button_align_corner_top_right.SetToolTip(_("Align laser with the upper right corner of the selection"))
        self.button_align_corner_top_right.SetSize(self.button_align_corner_top_right.GetBestSize())
        self.button_align_drag_left.SetSize(self.button_align_drag_left.GetBestSize())
        self.button_align_center.SetToolTip(_("Align laser with the center of the selection"))
        self.button_align_center.SetSize(self.button_align_center.GetBestSize())
        self.button_align_drag_right.SetSize(self.button_align_drag_right.GetBestSize())
        self.button_align_corner_bottom_left.SetToolTip(_("Align laser with the lower left corner of the selection"))
        self.button_align_corner_bottom_left.SetSize(self.button_align_corner_bottom_left.GetBestSize())
        self.button_align_drag_down.SetSize(self.button_align_drag_down.GetBestSize())
        self.button_align_corner_bottom_right.SetToolTip(_("Align laser with the lower right corner of the selection"))
        self.button_align_corner_bottom_right.SetSize(self.button_align_corner_bottom_right.GetBestSize())
        self.button_align_trace_hull.SetToolTip(_("Perform a convex hull trace of the selection"))
        self.button_align_trace_hull.SetSize(self.button_align_trace_hull.GetBestSize())
        self.button_align_trace_quick.SetToolTip(_("Perform a simple trace of the selection"))
        self.button_align_trace_quick.SetSize(self.button_align_trace_quick.GetBestSize())

        self.button_scale_down.SetSize(self.button_scale_down.GetBestSize())
        self.button_translate_up.SetSize(self.button_translate_up.GetBestSize())
        self.button_scale_up.SetSize(self.button_scale_up.GetBestSize())
        self.button_translate_left.SetSize(self.button_translate_left.GetBestSize())
        self.button_reset.SetSize(self.button_reset.GetBestSize())
        self.button_translate_right.SetSize(self.button_translate_right.GetBestSize())
        self.button_rotate_ccw.SetSize(self.button_rotate_ccw.GetBestSize())
        self.button_translate_down.SetSize(self.button_translate_down.GetBestSize())
        self.button_rotate_cw.SetSize(self.button_rotate_cw.GetBestSize())

        self.button_scale_down.SetToolTip(_("Scale Down"))
        self.button_translate_up.SetToolTip(_("Translate Top"))
        self.button_scale_up.SetToolTip(_("Scale Up"))
        self.button_translate_left.SetToolTip(_("Translate Left"))
        self.button_reset.SetToolTip(_("Reset Matrix"))
        self.button_translate_right.SetToolTip(_("Translate Right"))
        self.button_rotate_ccw.SetToolTip(_("Rotate Counterclockwise"))
        self.button_translate_down.SetToolTip(_("Translate Bottom"))
        self.button_rotate_cw.SetToolTip(_("Rotate Clockwise"))

        self.text_a.SetMinSize((70, 23))
        self.text_a.SetToolTip(_("Transform: Scale X"))
        self.text_c.SetMinSize((70, 23))
        self.text_c.SetToolTip(_("Transform: Skew Y"))
        self.text_e.SetMinSize((70, 23))
        self.text_e.SetToolTip(_("Transform: Translate X"))
        self.text_b.SetMinSize((70, 23))
        self.text_b.SetToolTip(_("Transform: Skew X"))
        self.text_d.SetMinSize((70, 23))
        self.text_d.SetToolTip(_("Transform: Scale Y"))
        self.text_f.SetMinSize((70, 23))
        self.text_f.SetToolTip(_("Transform: Translate Y"))

        self.button_navigate_pulse.SetToolTip(_("Fire a short laser pulse"))
        self.button_navigate_pulse.SetSize(self.button_navigate_pulse.GetBestSize())
        self.spin_pulse_duration.SetMinSize((80, 23))
        self.spin_pulse_duration.SetToolTip(_("Set the duration of the laser pulse"))
        self.button_navigate_move_to.SetToolTip(_("Move to the set position"))
        self.button_navigate_move_to.SetSize(self.button_navigate_move_to.GetBestSize())
        self.text_position_x.SetToolTip(_("Set X value for the Move To"))
        self.text_position_y.SetToolTip(_("Set Y value for the Move To"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Navigation.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_16 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_12 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Move To")), wx.HORIZONTAL)
        sizer_13 = wx.BoxSizer(wx.VERTICAL)
        sizer_15 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_14 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_5 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Short Pulse")), wx.HORIZONTAL)
        sizer_11 = wx.BoxSizer(wx.HORIZONTAL)
        matrix_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_17 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        grid_sizer_2 = wx.FlexGridSizer(3, 3, 0, 0)
        align_sizer = wx.FlexGridSizer(4, 3, 0, 0)
        navigation_sizer = wx.FlexGridSizer(4, 3, 0, 0)
        sizer_6 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Jog Distance")), wx.HORIZONTAL)
        sizer_10 = wx.BoxSizer(wx.VERTICAL)
        sizer_9 = wx.BoxSizer(wx.VERTICAL)
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_7 = wx.BoxSizer(wx.VERTICAL)
        sizer_7.Add(self.spin_jog_mils, 0, 0, 0)
        label_5 = wx.StaticText(self, wx.ID_ANY, _("mils"))
        sizer_7.Add(label_5, 0, 0, 0)
        sizer_6.Add(sizer_7, 0, wx.EXPAND, 0)
        sizer_8.Add(self.spin_jog_mm, 0, 0, 0)
        label_6 = wx.StaticText(self, wx.ID_ANY, _(" mm"))
        sizer_8.Add(label_6, 0, 0, 0)
        sizer_6.Add(sizer_8, 0, wx.EXPAND, 0)
        sizer_9.Add(self.spin_jog_cm, 0, 0, 0)
        label_7 = wx.StaticText(self, wx.ID_ANY, _("cm"))
        sizer_9.Add(label_7, 0, 0, 0)
        sizer_6.Add(sizer_9, 0, wx.EXPAND, 0)
        sizer_10.Add(self.spin_jog_inch, 0, 0, 0)
        label_8 = wx.StaticText(self, wx.ID_ANY, _("inch"))
        sizer_10.Add(label_8, 0, 0, 0)
        sizer_6.Add(sizer_10, 0, wx.EXPAND, 0)
        sizer_1.Add(sizer_6, 0, wx.EXPAND, 0)
        navigation_sizer.Add(self.button_navigate_up_left, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_up, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_up_right, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_left, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_home, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_right, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_down_left, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_down, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_down_right, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_unlock, 0, 0, 0)
        navigation_sizer.Add((0, 0), 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_lock, 0, 0, 0)
        sizer_11.Add(navigation_sizer, 1, wx.EXPAND, 0)
        align_sizer.Add(self.button_align_corner_top_left, 0, 0, 0)
        align_sizer.Add(self.button_align_drag_up, 0, 0, 0)
        align_sizer.Add(self.button_align_corner_top_right, 0, 0, 0)
        align_sizer.Add(self.button_align_drag_left, 0, 0, 0)
        align_sizer.Add(self.button_align_center, 0, 0, 0)
        align_sizer.Add(self.button_align_drag_right, 0, 0, 0)
        align_sizer.Add(self.button_align_corner_bottom_left, 0, 0, 0)
        align_sizer.Add(self.button_align_drag_down, 0, 0, 0)
        align_sizer.Add(self.button_align_corner_bottom_right, 0, 0, 0)
        align_sizer.Add((0, 0), 0, 0, 0)
        align_sizer.Add(self.button_align_trace_hull, 0, 0, 0)
        align_sizer.Add(self.button_align_trace_quick, 0, 0, 0)
        sizer_11.Add(align_sizer, 1, wx.EXPAND, 0)
        grid_sizer_2.Add(self.button_scale_down, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_up, 0, 0, 0)
        grid_sizer_2.Add(self.button_scale_up, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_left, 0, 0, 0)
        grid_sizer_2.Add(self.button_reset, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_right, 0, 0, 0)
        grid_sizer_2.Add(self.button_rotate_ccw, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_down, 0, 0, 0)
        grid_sizer_2.Add(self.button_rotate_cw, 0, 0, 0)
        matrix_sizer.Add(grid_sizer_2, 0, wx.EXPAND, 0)
        sizer_2.Add(self.text_a, 0, 0, 0)
        sizer_2.Add(self.text_c, 0, 0, 0)
        sizer_17.Add(sizer_2, 1, wx.EXPAND, 0)
        sizer_3.Add(self.text_b, 0, 0, 0)
        sizer_3.Add(self.text_d, 0, 0, 0)
        sizer_17.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_4.Add(self.text_e, 0, 0, 0)
        sizer_4.Add(self.text_f, 0, 0, 0)
        sizer_17.Add(sizer_4, 1, wx.EXPAND, 0)
        matrix_sizer.Add(sizer_17, 1, wx.EXPAND, 0)
        sizer_11.Add(matrix_sizer, 0, 0, 0)
        sizer_1.Add(sizer_11, 0, wx.EXPAND, 0)
        sizer_5.Add(self.button_navigate_pulse, 0, 0, 0)
        sizer_5.Add(self.spin_pulse_duration, 0, 0, 0)
        label_4 = wx.StaticText(self, wx.ID_ANY, _(" ms"))
        sizer_5.Add(label_4, 0, 0, 0)
        sizer_16.Add(sizer_5, 0, wx.EXPAND, 0)
        sizer_12.Add(self.button_navigate_move_to, 0, 0, 0)
        label_9 = wx.StaticText(self, wx.ID_ANY, _("X:"))
        sizer_14.Add(label_9, 0, 0, 0)
        sizer_14.Add(self.text_position_x, 0, 0, 0)
        sizer_13.Add(sizer_14, 0, wx.EXPAND, 0)
        label_10 = wx.StaticText(self, wx.ID_ANY, _("Y:"))
        sizer_15.Add(label_10, 0, 0, 0)
        sizer_15.Add(self.text_position_y, 0, 0, 0)
        sizer_13.Add(sizer_15, 0, wx.EXPAND, 0)
        sizer_12.Add(sizer_13, 0, wx.EXPAND, 0)
        sizer_16.Add(sizer_12, 0, wx.EXPAND, 0)
        sizer_1.Add(sizer_16, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def initialize(self):
        device = self.device
        kernel = self.device.device_root
        self.elements = kernel.elements
        device.close('window', self.name)
        self.Show()
        if device.is_root():
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(False)
            dlg = wx.MessageDialog(None, _("You do not have a selected device."),
                                   _("No Device Selected."), wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            dlg.Destroy()
            return

        device.setting(float, "navigate_jog", self.spin_jog_mils.GetValue())
        device.setting(float, "navigate_pulse", self.spin_pulse_duration.GetValue())
        self.spin_pulse_duration.SetValue(self.device.navigate_pulse)
        self.set_jog_distances(self.device.navigate_jog)

        kernel.listen('emphasized', self.on_emphasized_elements_changed)
        device.listen('interpreter;position', self.on_position_update)
        self.console = self.device.using('module', 'Console')
        self.update_matrix_text()

    def shutdown(self,  channel):
        try:
            self.Close()
        except RuntimeError:
            pass

    def on_emphasized_elements_changed(self, elements):
        self.select_ready(self.elements.has_emphasis())
        self.update_matrix_text()

    def update_matrix_text(self):
        v = self.elements.has_emphasis()
        self.text_a.Enable(v)
        self.text_b.Enable(v)
        self.text_c.Enable(v)
        self.text_d.Enable(v)
        self.text_e.Enable(v)
        self.text_f.Enable(v)
        if v:
            matrix = self.elements.first_element(emphasized=True).transform
            self.text_a.SetValue(str(matrix.a))
            self.text_b.SetValue(str(matrix.b))
            self.text_c.SetValue(str(matrix.c))
            self.text_d.SetValue(str(matrix.d))
            self.text_e.SetValue(str(matrix.e))
            self.text_f.SetValue(str(matrix.f))

    def on_position_update(self, *args):
        self.text_position_x.SetValue(str(self.device.current_x))
        self.text_position_y.SetValue(str(self.device.current_y))

    def drag_ready(self, v):
        self.design_locked = v
        self.button_align_drag_down.Enable(v)
        self.button_align_drag_up.Enable(v)
        self.button_align_drag_right.Enable(v)
        self.button_align_drag_left.Enable(v)

    def select_ready(self, v):
        """
        Enables the relevant buttons when there is a selection in the elements.
        :param v: whether selection is currently drag ready.
        :return:
        """
        if not v:
            self.button_align_drag_down.Enable(False)
            self.button_align_drag_up.Enable(False)
            self.button_align_drag_left.Enable(False)
            self.button_align_drag_right.Enable(False)
        self.button_align_center.Enable(v)
        self.button_align_corner_top_left.Enable(v)
        self.button_align_corner_top_right.Enable(v)
        self.button_align_corner_bottom_left.Enable(v)
        self.button_align_corner_bottom_right.Enable(v)
        self.button_align_trace_hull.Enable(v)
        self.button_align_trace_quick.Enable(v)
        self.button_scale_down.Enable(v)
        self.button_scale_up.Enable(v)
        self.button_rotate_ccw.Enable(v)
        self.button_rotate_cw.Enable(v)
        self.button_translate_down.Enable(v)
        self.button_translate_up.Enable(v)
        self.button_translate_left.Enable(v)
        self.button_translate_right.Enable(v)
        self.button_reset.Enable(v)

    def set_jog_distances(self, jog_mils):
        self.spin_jog_mils.SetValue(jog_mils)
        self.spin_jog_mm.SetValue(jog_mils / MILS_IN_MM)
        self.spin_jog_cm.SetValue(jog_mils / (MILS_IN_MM * 10.0))
        self.spin_jog_inch.SetValue(jog_mils / 1000.0)

    def on_spin_jog_distance(self, event):  # wxGlade: Navigation.<event_handler>
        if event.Id == self.spin_jog_mils.Id:
            self.device.navigate_jog = float(self.spin_jog_mils.GetValue())
        elif event.Id == self.spin_jog_mm.Id:
            self.device.navigate_jog = float(self.spin_jog_mm.GetValue() * MILS_IN_MM)
        elif event.Id == self.spin_jog_cm.Id:
            self.device.navigate_jog = float(self.spin_jog_cm.GetValue() * MILS_IN_MM * 10.0)
        else:
            self.device.navigate_jog = float(self.spin_jog_inch.GetValue() * 1000.0)
        self.set_jog_distances(int(self.device.navigate_jog))

    def on_button_navigate_home(self, event):  # wxGlade: Navigation.<event_handler>
        self.console.write('home\n')
        self.drag_ready(False)

    def on_button_navigate_ul(self, event):  # wxGlade: Navigation.<event_handler>
        dx = -self.device.navigate_jog
        dy = -self.device.navigate_jog
        self.console.write('move_relative %d %d\n' % (dx, dy))
        self.drag_ready(False)

    def on_button_navigate_u(self, event):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = -self.device.navigate_jog
        self.console.write('move_relative %d %d\n' % (dx, dy))
        self.drag_ready(False)

    def on_button_navigate_ur(self, event):  # wxGlade: Navigation.<event_handler>
        dx = self.device.navigate_jog
        dy = -self.device.navigate_jog
        self.console.write('move_relative %d %d\n' % (dx, dy))
        self.drag_ready(False)

    def on_button_navigate_l(self, event):  # wxGlade: Navigation.<event_handler>
        dx = -self.device.navigate_jog
        dy = 0
        self.console.write('move_relative %d %d\n' % (dx, dy))
        self.drag_ready(False)

    def on_button_navigate_r(self, event):  # wxGlade: Navigation.<event_handler>
        dx = self.device.navigate_jog
        dy = 0
        self.console.write('move_relative %d %d\n' % (dx, dy))
        self.drag_ready(False)

    def on_button_navigate_dl(self, event):  # wxGlade: Navigation.<event_handler>
        dx = -self.device.navigate_jog
        dy = self.device.navigate_jog
        self.console.write('move_relative %d %d\n' % (dx, dy))
        self.drag_ready(False)

    def on_button_navigate_d(self, event):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = self.device.navigate_jog
        self.console.write('move_relative %d %d\n' % (dx, dy))
        self.drag_ready(False)

    def on_button_navigate_dr(self, event):  # wxGlade: Navigation.<event_handler>
        dx = self.device.navigate_jog
        dy = self.device.navigate_jog
        self.console.write('move_relative %d %d\n' % (dx, dy))
        self.drag_ready(False)

    def on_button_navigate_unlock(self, event):  # wxGlade: Navigation.<event_handler>
        self.console.write('unlock\n')

    def on_button_navigate_lock(self, event):  # wxGlade: Navigation.<event_handler>
        self.console.write('lock\n')

    def on_button_align_center(self, event):  # wxGlade: Navigation.<event_handler>
        elements = self.elements
        bbox = elements.bounds()
        if bbox is None:
            return
        px = (bbox[0] + bbox[2]) / 2.0
        py = (bbox[3] + bbox[1]) / 2.0
        self.console.write('move_absolute %f %f\n' % (px,py))
        self.drag_ready(True)

    def on_button_align_corner_tl(self, event):  # wxGlade: Navigation.<event_handler>
        elements = self.elements
        bbox = elements.bounds()
        if bbox is None:
            return
        self.console.write('move_absolute %f %f\n' % (bbox[0], bbox[1]))
        self.drag_ready(True)

    def on_button_align_corner_tr(self, event):  # wxGlade: Navigation.<event_handler>
        elements = self.device.device_root.elements
        bbox = elements.bounds()
        if bbox is None:
            return
        self.console.write('move_absolute %f %f\n' % (bbox[2], bbox[1]))
        self.drag_ready(True)

    def on_button_align_corner_bl(self, event):  # wxGlade: Navigation.<event_handler>
        elements = self.device.device_root.elements
        bbox = elements.bounds()
        if bbox is None:
            return
        self.console.write('move_absolute %f %f\n' % (bbox[0], bbox[3]))
        self.drag_ready(True)

    def on_button_align_corner_br(self, event):  # wxGlade: Navigation.<event_handler>
        elements = self.device.device_root.elements
        bbox = elements.bounds()
        if bbox is None:
            return
        self.console.write('move_absolute %f %f\n' % (bbox[2], bbox[3]))
        self.drag_ready(True)

    def drag_relative(self, dx, dy):
        self.console.write('move_relative %d %d\ntranslate %d %d\n' % (dx, dy, dx, dy))

    def on_button_align_drag_down(self, event):  # wxGlade: Navigation.<event_handler>
        self.drag_relative(0, self.device.navigate_jog)
        self.update_matrix_text()

    def on_button_align_drag_right(self, event):  # wxGlade: Navigation.<event_handler>
        self.drag_relative(self.device.navigate_jog, 0)
        self.update_matrix_text()

    def on_button_align_drag_up(self, event):  # wxGlade: Navigation.<event_handler>
        self.drag_relative(0, -self.device.navigate_jog)
        self.update_matrix_text()

    def on_button_align_drag_left(self, event):  # wxGlade: Navigation.<event_handler>
        self.drag_relative(-self.device.navigate_jog, 0)
        self.update_matrix_text()

    def on_button_align_trace_hull(self, event):  # wxGlade: Navigation.<event_handler>
        self.console.write('trace_hull\n')

    def on_button_align_trace_quick(self, event):  # wxGlade: Navigation.<event_handler>
        self.console.write('trace_quick\n')
        self.drag_ready(True)

    def on_button_navigate_pulse(self, event):  # wxGlade: Navigation.<event_handler>
        value = self.spin_pulse_duration.GetValue()
        self.console.write('pulse %f\n' % value)

    def on_spin_pulse_duration(self, event):  # wxGlade: Navigation.<event_handler>
        self.device.navigate_pulse = float(self.spin_pulse_duration.GetValue())

    def on_button_navigate_move_to(self, event):  # wxGlade: Navigation.<event_handler>
        try:
            x = int(self.text_position_x.GetValue())
            y = int(self.text_position_y.GetValue())
            self.console.write('move %d %d\n' % (x, y))
        except ValueError:
            return

    def matrix_updated(self):
        self.device.signal('refresh_scene')
        self.update_matrix_text()
        self.drag_ready(False)

    def on_scale_down(self, event):  # wxGlade: Navigation.<event_handler>
        scale = 19.0 / 20.0
        self.console.write('scale %f %f %f %f\n' % (scale,
                                                                              scale,
                                                                              self.device.current_x,
                                                                              self.device.current_y))
        self.matrix_updated()

    def on_scale_up(self, event):  # wxGlade: Navigation.<event_handler>
        scale = 20.0 / 19.0
        self.console.write('scale %f %f %f %f\n' % (scale,
                                                                              scale,
                                                                              self.device.current_x,
                                                                              self.device.current_y))
        self.matrix_updated()

    def on_translate_up(self, event):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = -self.device.navigate_jog
        self.console.write('translate %f %f\n' % (dx, dy))
        self.matrix_updated()

    def on_translate_left(self, event):  # wxGlade: Navigation.<event_handler>
        dx = -self.device.navigate_jog
        dy = 0
        self.console.write('translate %f %f\n' % (dx, dy))
        self.matrix_updated()

    def on_translate_right(self, event):  # wxGlade: Navigation.<event_handler>
        dx = self.device.navigate_jog
        dy = 0
        self.console.write('translate %f %f\n' % (dx, dy))
        self.matrix_updated()

    def on_translate_down(self, event):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = self.device.navigate_jog
        self.console.write('translate %f %f\n' % (dx, dy))
        self.matrix_updated()

    def on_reset(self, event):  # wxGlade: Navigation.<event_handler>
        self.console.write('reset\n')
        self.matrix_updated()

    def on_rotate_ccw(self, event):  # wxGlade: Navigation.<event_handler>
        self.console.write('rotate %fdeg %f %f\n' % (-5,
                                                                               self.device.current_x,
                                                                               self.device.current_y))
        self.matrix_updated()

    def on_rotate_cw(self, event):  # wxGlade: Navigation.<event_handler>
        self.console.write('rotate %fdeg %f %f\n' % (5,
                                                                               self.device.current_x,
                                                                               self.device.current_y))
        self.matrix_updated()

    def on_text_matrix(self, event):  # wxGlade: Navigation.<event_handler>
        try:
            self.console.write("matrix %f %f %f %f %s %s" % (
                float(self.text_a.GetValue()),
                float(self.text_b.GetValue()),
                float(self.text_c.GetValue()),
                float(self.text_d.GetValue()),
                self.text_e.GetValue(),
                self.text_f.GetValue()
            ))
        except ValueError:
            self.update_matrix_text()
            self.drag_ready(False)
        self.device.signal('refresh_scene')
