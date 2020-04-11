import wx

from icons import icons8_stop_sign_50, icon_meerk40t
from Kernel import *

_ = wx.GetTranslation


class Shutdown(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: Shutdown.__init__
        kwds["style"] = kwds.get("style", 0) | wx.CAPTION | wx.CLIP_CHILDREN | wx.FRAME_TOOL_WINDOW | wx.RESIZE_BORDER | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((413, 573))
        self.text_shutdown = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.button_stop = wx.BitmapButton(self, wx.ID_ANY, icons8_stop_sign_50.GetBitmap())
        self.button_reload = wx.BitmapButton(self, wx.ID_ANY, icon_meerk40t.GetBitmap())

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_stop, self.button_stop)
        self.Bind(wx.EVT_BUTTON, self.on_button_reload, self.button_reload)
        # end wxGlade

        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.kernel = None
        self.autoclose = True

    def on_close(self, event):
        self.kernel.module_instance_remove(self.name)
        event.Skip()  # Call destroy as regular.

    def initialize(self, kernel, name=None):
        kernel.module_instance_close(name)
        Module.initialize(kernel, name)
        self.kernel = kernel
        self.name = name
        self.Show()

        self.kernel.setting(bool, "autoclose_shutdown", True)
        self.autoclose = self.kernel.autoclose_shutdown
        self.kernel.shutdown_watcher = self.on_shutdown

    def shutdown(self, kernel):
        self.Close()
        Module.shutdown(self, kernel)
        self.kernel = None

    def on_shutdown(self, flag, name, obj):
        if obj == self:  # Trying to shut down this window. That's a 'no'.
            return False
        if self.text_shutdown is None:
            return
        if flag == SHUTDOWN_BEGIN:
            self.text_shutdown.AppendText(_("Shutting down.\n"))
        elif flag == SHUTDOWN_FLUSH:
            self.text_shutdown.AppendText(_("Saving data for device: %s\n") % str(obj))
        elif flag == SHUTDOWN_WINDOW:
            self.text_shutdown.AppendText(_("Closing %s Window: %s\n") % (name, str(obj)))
        elif flag == SHUTDOWN_WINDOW_ERROR:
            self.text_shutdown.AppendText(_("WARNING: Window %s was not closed.\n") % (name))
        elif flag == SHUTDOWN_MODULE:
            self.text_shutdown.AppendText(_("Shutting down %s module: %s\n") % (name, str(obj)))
        elif flag == SHUTDOWN_MODULE_ERROR:
            self.text_shutdown.AppendText(_("WARNING: Module %s was not closed.\n") % (name))
        elif flag == SHUTDOWN_THREAD:
            self.text_shutdown.AppendText(_("Finishing Thread %s for %s\n") % (name, str(obj)))
        elif flag == SHUTDOWN_THREAD_ERROR:
            self.text_shutdown.AppendText(_("WARNING: Dead thread %s still registered to %s.\n") % (name, str(obj)))
        elif flag == SHUTDOWN_THREAD_ALIVE:
            self.text_shutdown.AppendText(_("Waiting for thread %s: %s\n") % (name, str(obj)))
        elif flag == SHUTDOWN_THREAD_FINISHED:
            self.text_shutdown.AppendText(_("Thread %s finished. %s\n") % (name, str(obj)))
        elif flag == SHUTDOWN_LISTENER_ERROR:
            self.text_shutdown.AppendText(_("WARNING: Listener '%s' still registered to %s.\n") % (name, str(obj)))
        elif flag == SHUTDOWN_FINISH:
            self.text_shutdown.AppendText(_("Shutdown.\n"))
            if self.autoclose:
                self.text_shutdown = None
                if self.kernel.run_later is not None:
                    self.kernel.run_later(self.Close, False)
                else:
                    self.Close()
        return True

    def __set_properties(self):
        # begin wxGlade: Shutdown.__set_properties
        self.SetTitle(_("Shutdown"))
        self.button_stop.SetMinSize((108, 108))
        self.button_reload.SetSize(self.button_reload.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Shutdown.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(self.text_shutdown, 5, wx.EXPAND, 0)
        sizer_2.Add(self.button_stop, 0, 0, 0)
        sizer_2.Add(self.button_reload, 0, 0, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def on_button_stop(self, event):  # wxGlade: Shutdown.<event_handler>
        for name, device in self.kernel.device_instances.items():
            if device.spooler.thread is not None:
                if device.spooler.thread.is_alive() or device.pipe.thread.is_alive():
                    device.execute("Emergency Stop")
                    return
        wx.CallAfter(self.Close)

    def on_button_reload(self, event):  # wxGlade: Shutdown.<event_handler>
        # self.kernel.module_instance_open('MeerK40t', None, -1, "")
        self.Close()
