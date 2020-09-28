import wx

from Kernel import *
from icons import icons8_route_50

_ = wx.GetTranslation


class JobSpooler(wx.Frame, Module):
    def __init__(self, context, path, parent, *args, **kwds):
        # begin wxGlade: Spooler.__init__
        wx.Frame.__init__(self, parent, -1, "",
                          style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT | wx.TAB_TRAVERSAL)
        Module.__init__(self, context, path)
        self.SetSize((643, 633))
        self.spooler = context._kernel.active.spooler
        self.panel_simulation = wx.Panel(self, wx.ID_ANY)
        self.text_time_laser = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_time_travel = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_time_total = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_time_total_copy = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.list_job_spool = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_list_drag, self.list_job_spool)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_rightclick, self.list_job_spool)
        # end wxGlade
        self.dirty = False
        self.update_buffer_size = False
        self.update_spooler_state = False
        self.update_spooler = False

        self.elements_progress = 0
        self.elements_progress_total = 0
        self.command_index = 0
        self.listener_list = None
        self.list_lookup = {}
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_route_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Spooler.__set_properties
        self.SetTitle("Job Spooler")
        self.panel_simulation.SetToolTip("Job Simulation")
        self.text_time_laser.SetToolTip("Time Estimate: Lasering Time")
        self.text_time_travel.SetToolTip("Time Estimate: Traveling Time")
        self.text_time_total.SetToolTip("Time Estimate: Total Time")
        self.text_time_total_copy.SetToolTip("Time Estimate: Total Time")
        self.list_job_spool.SetToolTip("List and modify the queued operations")
        self.list_job_spool.AppendColumn("#", format=wx.LIST_FORMAT_LEFT, width=35)
        self.list_job_spool.AppendColumn("Name", format=wx.LIST_FORMAT_LEFT, width=143)
        self.list_job_spool.AppendColumn("Status", format=wx.LIST_FORMAT_LEFT, width=73)
        self.list_job_spool.AppendColumn("Type", format=wx.LIST_FORMAT_LEFT, width=53)
        self.list_job_spool.AppendColumn("Speed", format=wx.LIST_FORMAT_LEFT, width=77)
        self.list_job_spool.AppendColumn("Settings", format=wx.LIST_FORMAT_LEFT, width=223)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Spooler.__do_layout
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        sizer_time = wx.BoxSizer(wx.HORIZONTAL)
        sizer_total_remaining = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Time Remaining"), wx.VERTICAL)
        sizer_total_time = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Total Time"), wx.VERTICAL)
        sizer_travel_time = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Travel Time"), wx.VERTICAL)
        sizer_laser_time = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Laser Time"), wx.VERTICAL)
        sizer_frame.Add(self.panel_simulation, 7, wx.EXPAND, 0)
        sizer_laser_time.Add(self.text_time_laser, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_laser_time, 1, wx.EXPAND, 0)
        sizer_travel_time.Add(self.text_time_travel, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_travel_time, 1, wx.EXPAND, 0)
        sizer_total_time.Add(self.text_time_total, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_total_time, 1, wx.EXPAND, 0)
        sizer_total_remaining.Add(self.text_time_total_copy, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_total_remaining, 1, wx.EXPAND, 0)
        sizer_frame.Add(sizer_time, 0, wx.EXPAND, 0)
        sizer_frame.Add(self.list_job_spool, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_frame)
        self.Layout()
        # end wxGlade

    def on_close(self, event):
        if self.state == 5:
            event.Veto()
        else:
            self.state = 5
            self.context.close(self.name)
            event.Skip()  # Call destroy as regular.

    def initialize(self, channel=None):
        self.context.close(self.name)
        self.Show()

        self.context._kernel.active.listen('spooler;queue', self.on_spooler_update)
        self.refresh_spooler_list()

    def finalize(self, channel=None):
        self.context._kernel.active.unlisten('spooler;queue', self.on_spooler_update)
        try:
            self.Close()
        except RuntimeError:
            pass

    def shutdown(self, channel=None):
        try:
            self.Close()
        except RuntimeError:
            pass

    def on_list_drag(self, event):  # wxGlade: JobSpooler.<event_handler>
        event.Skip()

    def on_item_rightclick(self, event):  # wxGlade: JobSpooler.<event_handler>
        index = event.Index
        try:
            element = self.spooler._queue[index]
        except IndexError:
            return
        menu = wx.Menu()
        convert = menu.Append(wx.ID_ANY, _("Remove %s") % str(element)[:16], "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_delete(element), convert)
        convert = menu.Append(wx.ID_ANY, _("Clear All"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_clear(element), convert)
        self.PopupMenu(menu)
        menu.Destroy()

    def refresh_spooler_list(self):
        if not self.update_spooler:
            return

        def name_str(e):
            try:
                return e.__name__
            except AttributeError:
                return str(e)
        try:
            self.list_job_spool.DeleteAllItems()
        except RuntimeError:
            return

        if len(self.spooler._queue) > 0:
            # This should actually process and update the queue items.
            for i, e in enumerate(self.spooler._queue):
                m = self.list_job_spool.InsertItem(i, "#%d" % i)
                if m != -1:
                    self.list_job_spool.SetItem(m, 1, name_str(e))
                    try:
                        self.list_job_spool.SetItem(m, 2, e._status_value)
                    except AttributeError:
                        pass
                    try:
                        self.list_job_spool.SetItem(m, 3, e.operation)
                    except AttributeError:
                        pass
                    try:
                        self.list_job_spool.SetItem(m, 4, _("%.1fmm/s") % (e.speed))
                    except AttributeError:
                        pass
                    settings = list()
                    try:
                        settings.append(_("power=%g") % (e.power))
                    except AttributeError:
                        pass
                    try:
                        settings.append(_("step=%d") % (e.raster_step))
                    except AttributeError:
                        pass
                    try:
                        settings.append(_("overscan=%d") % (e.overscan))
                    except AttributeError:
                        pass
                    self.list_job_spool.SetItem(m, 5, " ".join(settings))

    def on_tree_popup_clear(self, element):
        def delete(event):
            self.spooler.clear_queue()
            self.refresh_spooler_list()

        return delete

    def on_tree_popup_delete(self, element):
        def delete(event):
            self.spooler.remove(element)
            self.refresh_spooler_list()

        return delete

    def on_spooler_update(self, value):
        self.update_spooler = True
        self.refresh_spooler_list()
