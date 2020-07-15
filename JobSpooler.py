import wx

from Kernel import *
from icons import icons8_route_50

_ = wx.GetTranslation


class JobSpooler(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: JobSpooler.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT | wx.TAB_TRAVERSAL
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((661, 402))
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

    def on_close(self, event):
        try:
            v = self.device.instances['window'][self.name]
            self.device.close('window', self.name)
            event.Skip()  # Call destroy as regular.
        except KeyError:
            event.Veto()

    def initialize(self, channel=None):
        self.device.close('window', self.name)
        self.Show()

        self.device.listen('spooler;queue', self.on_spooler_update)
        self.refresh_spooler_list()

    def finalize(self, channel=None):
        self.device.unlisten('spooler;queue', self.on_spooler_update)
        try:
            self.Close()
        except RuntimeError:
            pass

    def shutdown(self, channel=None):
        try:
            self.Close()
        except RuntimeError:
            pass

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_route_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: JobSpooler.__set_properties
        self.SetTitle("Spooler")
        self.list_job_spool.SetToolTip("List and modify the queued operations")
        self.list_job_spool.AppendColumn("#", format=wx.LIST_FORMAT_LEFT, width=29)
        self.list_job_spool.AppendColumn("Name", format=wx.LIST_FORMAT_LEFT, width=90)
        self.list_job_spool.AppendColumn("Status", format=wx.LIST_FORMAT_LEFT, width=73)
        self.list_job_spool.AppendColumn("Device", format=wx.LIST_FORMAT_LEFT, width=53)
        self.list_job_spool.AppendColumn("Type", format=wx.LIST_FORMAT_LEFT, width=41)
        self.list_job_spool.AppendColumn("Speed", format=wx.LIST_FORMAT_LEFT, width=77)
        self.list_job_spool.AppendColumn("Settings", format=wx.LIST_FORMAT_LEFT, width=82+70)
        self.list_job_spool.AppendColumn("Time Estimate", format=wx.LIST_FORMAT_LEFT, width=123)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: JobSpooler.__do_layout
        spool_sizer = wx.BoxSizer(wx.VERTICAL)
        spool_sizer.Add(self.list_job_spool, 8, wx.EXPAND, 0)
        self.SetSizer(spool_sizer)
        self.Layout()
        # end wxGlade

    def on_list_drag(self, event):  # wxGlade: JobSpooler.<event_handler>
        event.Skip()

    def on_item_rightclick(self, event):  # wxGlade: JobSpooler.<event_handler>
        index = event.Index
        try:
            element = self.device.spooler._queue[index]
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
        if len(self.device.spooler._queue) > 0:
            # This should actually process and update the queue items.
            i = 0
            for e in self.device.spooler._queue:
                m = self.list_job_spool.InsertItem(i, "#%d" % i)
                if m != -1:
                    self.list_job_spool.SetItem(m, 1, name_str(e))
                    try:
                        self.list_job_spool.SetItem(m, 2, e._status_value)
                    except AttributeError:
                        pass
                    self.list_job_spool.SetItem(m, 3, self.device.device_name)
                    try:
                        self.list_job_spool.SetItem(m, 4, e.operation)
                    except AttributeError:
                        pass
                    try:
                        self.list_job_spool.SetItem(m, 5, _("%.1fmm/s") % (e.speed))
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
                    self.list_job_spool.SetItem(m, 6, " ".join(settings))
                    try:
                        self.list_job_spool.SetItem(m, 7, e.time_estimate())
                    except AttributeError:
                        pass

                i += 1

    def on_tree_popup_clear(self, element):
        def delete(event):
            self.device.spooler.clear_queue()
            self.refresh_spooler_list()

        return delete

    def on_tree_popup_delete(self, element):
        def delete(event):
            self.device.spooler.remove(element)
            self.refresh_spooler_list()

        return delete

    def on_spooler_update(self, value):
        self.update_spooler = True
        self.refresh_spooler_list()

