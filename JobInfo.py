import wx

from ThreadConstants import *


class JobInfo(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: JobInfo.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((615, 627))
        self.panel_writer = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.gauge_writer = wx.Gauge(self.panel_writer, wx.ID_ANY, 100)
        self.text_job_progress = wx.TextCtrl(self.panel_writer, wx.ID_ANY, "")
        self.text_job_total = wx.TextCtrl(self.panel_writer, wx.ID_ANY, "")
        self.text_job_progress_copy = wx.TextCtrl(self.panel_writer, wx.ID_ANY, "")
        self.elements_listbox = wx.ListBox(self, wx.ID_ANY, choices=[], style=wx.LB_ALWAYS_SB | wx.LB_SINGLE)
        self.panel_controller = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.checkbox_queue_packets = wx.CheckBox(self.panel_controller, wx.ID_ANY, "Limit Packet Buffer")
        self.gauge_controller = wx.Gauge(self.panel_controller, wx.ID_ANY, 100)
        self.text_packet_buffer = wx.TextCtrl(self.panel_controller, wx.ID_ANY, "")
        self.spin_packet_buffer_max = wx.SpinCtrl(self.panel_controller, wx.ID_ANY, "50", min=1, max=10000)
        self.checkbox_1 = wx.CheckBox(self, wx.ID_ANY, "Automatically Start Controller")
        self.checkbox_2 = wx.CheckBox(self, wx.ID_ANY, "Home After")
        self.checkbox_3 = wx.CheckBox(self, wx.ID_ANY, "Beep After")
        self.button_writer_control = wx.ToggleButton(self, wx.ID_ANY, "Start Job")
        self.combo_box_1 = wx.ComboBox(self, wx.ID_ANY, choices=["Availible K40"], style=wx.CB_DROPDOWN)
        self.panel_usb = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.text_usb_status = wx.TextCtrl(self.panel_usb, wx.ID_ANY, "")
        self.text_buffer_length = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_controller_control = wx.ToggleButton(self, wx.ID_ANY, "Start Controller")
        self.button_stop = wx.BitmapButton(self, wx.ID_ANY,
                                           wx.Bitmap("icons/icons8-stop-sign-50.png", wx.BITMAP_TYPE_ANY))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_LISTBOX, self.on_listbox_click, self.elements_listbox)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_listbox_dclick, self.elements_listbox)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_limit_packet_buffer, self.checkbox_queue_packets)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_auto_start_controller, self.checkbox_1)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_home_after, self.checkbox_2)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_beep_after, self.checkbox_3)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_start_job, self.button_writer_control)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_select_writer, self.combo_box_1)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_start_controller, self.button_controller_control)
        self.Bind(wx.EVT_BUTTON, self.on_button_emergency_stop, self.button_stop)
        # end wxGlade
        self.project = None
        self.dirty = False
        self.queue_last = 0
        self.progress_total = 0
        self.progress_update = 0
        self.usb_status = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def set_project(self, project):
        self.project = project
        self.usb_status = project.controller.usb_status
        self.text_usb_status.SetValue(self.usb_status)
        self.project.thread.queue_listener = self.on_queue
        self.project.thread.progress_listener = self.on_progress
        self.project.controller.usbstatus_listener = self.on_usbstatus
        self.set_writer_button_by_state()
        self.set_controller_button_by_state()

        packet_buffer_text = str(self.project.controller.count_packet_buffer())
        self.text_packet_buffer.SetValue(packet_buffer_text)
        self.gauge_controller.SetValue(self.project.controller.count_packet_buffer())
        self.gauge_controller.SetRange(self.spin_packet_buffer_max.GetValue())

        self.text_job_progress.SetValue(str(self.progress_update))
        self.progress_total = len(self.project.thread.element_list)
        self.text_job_total.SetValue(str(self.progress_total))
        self.gauge_writer.SetValue(self.progress_update)
        self.gauge_writer.SetRange(self.progress_total)
        if len(self.project.thread.element_list) > 0:
            self.elements_listbox.InsertItems([str(e) for e in self.project.thread.element_list], 0)

    def on_close(self, event):
        if self.project.thread is not None:
            self.project.thread.progress_listener = None
            self.project.thread.queue_listener = None
            self.project.controller.usbstatus_listener = None
        self.project = None
        event.Skip()  # Call destroy as regular.

    def __set_properties(self):
        # begin wxGlade: JobInfo.__set_properties
        self.SetTitle("Job")
        self.panel_writer.SetBackgroundColour(wx.Colour(238, 238, 238))
        self.elements_listbox.Enable(False)
        self.checkbox_queue_packets.SetValue(1)
        self.panel_controller.SetBackgroundColour(wx.Colour(204, 204, 204))
        self.checkbox_1.SetValue(1)
        self.checkbox_3.SetValue(1)
        self.button_writer_control.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.button_writer_control.SetFont(
            wx.Font(15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))
        self.button_writer_control.SetBitmap(wx.Bitmap("icons/icons8-play-50.png", wx.BITMAP_TYPE_ANY))
        self.button_writer_control.SetBitmapPressed(wx.Bitmap("icons/icons8-pause-50.png", wx.BITMAP_TYPE_ANY))
        self.combo_box_1.SetSelection(0)
        self.panel_usb.SetBackgroundColour(wx.Colour(187, 187, 187))
        self.button_controller_control.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.button_controller_control.SetFont(
            wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))
        self.button_controller_control.SetBitmap(wx.Bitmap("icons/icons8-play-50.png", wx.BITMAP_TYPE_ANY))
        self.button_controller_control.SetBitmapPressed(wx.Bitmap("icons/icons8-pause-50.png", wx.BITMAP_TYPE_ANY))
        self.button_stop.SetBackgroundColour(wx.Colour(255, 0, 0))
        self.button_stop.SetSize(self.button_stop.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: JobInfo.__do_layout
        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_13 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_11 = wx.BoxSizer(wx.VERTICAL)
        sizer_12 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_9 = wx.BoxSizer(wx.VERTICAL)
        sizer_14 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_9.Add(self.gauge_writer, 0, wx.EXPAND, 0)
        label_1 = wx.StaticText(self.panel_writer, wx.ID_ANY, "Job Elements: ")
        sizer_10.Add(label_1, 4, 0, 0)
        sizer_10.Add(self.text_job_progress, 5, 0, 0)
        label_2 = wx.StaticText(self.panel_writer, wx.ID_ANY, "/")
        sizer_10.Add(label_2, 0, 0, 0)
        sizer_10.Add(self.text_job_total, 5, 0, 0)
        sizer_9.Add(sizer_10, 1, wx.EXPAND, 0)
        label_6 = wx.StaticText(self.panel_writer, wx.ID_ANY, "Command Index: ")
        sizer_14.Add(label_6, 4, 0, 0)
        sizer_14.Add(self.text_job_progress_copy, 10, 0, 0)
        sizer_9.Add(sizer_14, 1, wx.EXPAND, 0)
        self.panel_writer.SetSizer(sizer_9)
        sizer_2.Add(self.panel_writer, 0, wx.EXPAND, 0)
        sizer_2.Add(self.elements_listbox, 1, wx.EXPAND, 0)
        sizer_11.Add(self.checkbox_queue_packets, 1, 0, 0)
        sizer_11.Add(self.gauge_controller, 0, wx.EXPAND, 0)
        label_7 = wx.StaticText(self.panel_controller, wx.ID_ANY, "Packet Buffer")
        sizer_12.Add(label_7, 4, 0, 0)
        sizer_12.Add(self.text_packet_buffer, 5, 0, 0)
        label_4 = wx.StaticText(self.panel_controller, wx.ID_ANY, "/")
        sizer_12.Add(label_4, 0, 0, 0)
        sizer_12.Add(self.spin_packet_buffer_max, 0, 0, 0)
        sizer_11.Add(sizer_12, 1, wx.EXPAND, 0)
        self.panel_controller.SetSizer(sizer_11)
        sizer_2.Add(self.panel_controller, 0, wx.EXPAND, 0)
        sizer_4.Add(self.checkbox_1, 0, 0, 0)
        sizer_4.Add(self.checkbox_2, 0, 0, 0)
        sizer_4.Add(self.checkbox_3, 0, 0, 0)
        sizer_2.Add(sizer_4, 0, wx.EXPAND, 0)
        sizer_2.Add(self.button_writer_control, 0, wx.EXPAND, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        sizer_8.Add(self.combo_box_1, 0, wx.EXPAND, 0)
        label_5 = wx.StaticText(self.panel_usb, wx.ID_ANY, "Usb Status")
        sizer_13.Add(label_5, 1, 0, 0)
        sizer_13.Add(self.text_usb_status, 3, 0, 0)
        self.panel_usb.SetSizer(sizer_13)
        sizer_8.Add(self.panel_usb, 0, wx.EXPAND, 0)
        label_3 = wx.StaticText(self, wx.ID_ANY, "Buffer")
        sizer_5.Add(label_3, 1, 0, 0)
        sizer_5.Add(self.text_buffer_length, 3, 0, 0)
        sizer_8.Add(sizer_5, 1, wx.EXPAND, 0)
        sizer_8.Add(self.button_controller_control, 0, wx.EXPAND, 0)
        sizer_8.Add(self.button_stop, 0, wx.EXPAND, 0)
        sizer_1.Add(sizer_8, 0, 0, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def on_listbox_click(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_listbox_click' not implemented!")
        event.Skip()

    def on_listbox_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_listbox_dclick' not implemented!")
        event.Skip()

    def on_check_limit_packet_buffer(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_check_limit_packet_buffer' not implemented!")
        event.Skip()

    def on_spin_packet_buffer_max(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_spin_packet_buffer_max' not implemented!")
        event.Skip()

    def on_check_auto_start_controller(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_check_auto_start_controller' not implemented!")
        event.Skip()

    def on_check_home_after(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_check_home_after' not implemented!")
        event.Skip()

    def on_check_beep_after(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_check_beep_after' not implemented!")
        event.Skip()

    def on_button_start_job(self, event):  # wxGlade: JobInfo.<event_handler>
        if self.project is None:
            return
        if self.project.thread is None:
            return
        state = self.project.thread.state
        if state == THREAD_STATE_PROCEED:
            self.project.thread.state = THREAD_STATE_PAUSE
            self.set_writer_button_by_state()
        elif state == THREAD_STATE_PAUSE:
            self.project.thread.state = THREAD_STATE_PROCEED
            self.set_writer_button_by_state()
        elif state == THREAD_STATE_UNSTARTED:
            self.project.thread.state = THREAD_STATE_PROCEED
            self.project.thread.start()
            self.set_writer_button_by_state()
        elif state == THREAD_STATE_ABORT:
            self.Close()
        elif state == THREAD_STATE_FINISHED:
            self.Close()

    def set_writer_button_by_state(self):
        state = self.project.thread.state
        if state == THREAD_STATE_FINISHED:
            self.button_writer_control.SetBackgroundColour("#0000ff")
            self.button_writer_control.SetLabel("Close Job")
            self.button_writer_control.SetValue(False)
        elif state == THREAD_STATE_PAUSE:
            self.button_writer_control.SetBackgroundColour("#00ff00")
            self.button_writer_control.SetLabel("Resume Job")
            self.button_writer_control.SetValue(False)
        elif state == THREAD_STATE_UNSTARTED:
            self.button_writer_control.SetBackgroundColour("#00ff00")
            self.button_writer_control.SetLabel("Start Job")
            self.button_writer_control.SetValue(True)
        elif state == THREAD_STATE_PROCEED:
            self.button_writer_control.SetBackgroundColour("#ffff00")
            self.button_writer_control.SetLabel("Pause Job")
            self.button_writer_control.SetValue(True)
        elif state == THREAD_STATE_ABORT:
            self.button_writer_control.SetBackgroundColour("#ff0000")
            self.button_writer_control.SetLabel("Close Aborted Job")
            self.button_writer_control.SetValue(False)

    def on_combo_select_writer(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_combo_select_writer' not implemented!")
        event.Skip()

    def on_button_start_controller(self, event):  # wxGlade: JobInfo.<event_handler>
        if self.project is not None:
            state = self.project.controller.state
            if state == THREAD_STATE_PROCEED:
                self.project.controller.state = THREAD_STATE_PAUSE
            elif state == THREAD_STATE_PAUSE:
                self.project.controller.state = THREAD_STATE_PROCEED
            elif state == THREAD_STATE_FINISHED or state == THREAD_STATE_UNSTARTED:
                self.project.controller.state = THREAD_STATE_PROCEED
                self.project.controller.start_queue_consumer()
        self.set_controller_button_by_state()

    def set_controller_button_by_state(self):
        state = self.project.controller.state
        if state == THREAD_STATE_UNSTARTED:
            self.button_controller_control.SetBackgroundColour("#00ff00")
            self.button_controller_control.SetLabel("Start Controller")
            self.button_controller_control.SetValue(False)
        elif state == THREAD_STATE_PAUSE:
            self.button_controller_control.SetBackgroundColour("#00ff00")
            self.button_controller_control.SetLabel("Resume Controller")
            self.button_controller_control.SetValue(False)
        elif state == THREAD_STATE_PROCEED:
            self.button_controller_control.SetBackgroundColour("#ffff00")
            self.button_controller_control.SetLabel("Pause Controller")
            self.button_controller_control.SetValue(True)

    def on_button_emergency_stop(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_button_emergency_stop' not implemented!")
        event.Skip()

    def post_update(self):
        if not self.dirty:
            self.dirty = True
            wx.CallAfter(self.post_update_on_gui_thread)

    def post_update_on_gui_thread(self):
        if self.project is None:
            return  # left over update on closed window
        self.text_packet_buffer.SetValue(str(self.queue_last))
        self.gauge_controller.SetValue(self.queue_last)
        self.gauge_controller.SetRange(self.spin_packet_buffer_max.GetValue())

        self.text_job_progress.SetValue(str(self.progress_update))
        self.text_job_total.SetValue(str(self.progress_total))
        self.gauge_writer.SetValue(self.progress_update)
        self.gauge_writer.SetRange(self.progress_total)

        self.text_usb_status.SetValue(self.usb_status)
        self.set_writer_button_by_state()
        self.dirty = False

    def on_usbstatus(self, status):
        self.usb_status = status
        self.post_update()

    def on_queue(self, last):
        self.queue_last = last
        self.post_update()

    def on_progress(self, last, limit):
        self.progress_total = limit
        self.progress_update = last
        self.post_update()
