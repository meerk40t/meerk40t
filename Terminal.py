
import wx

from Kernel import Module

_ = wx.GetTranslation


class Terminal(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: Terminal.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_NO_TASKBAR | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((581, 410))
        self.text_console = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_BESTWRAP | wx.TE_MULTILINE | wx.TE_READONLY)
        self.text_entry = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TEXT_ENTER, self.on_entry, self.text_entry)
        # end wxGlade
        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.kernel = None
        self.device = None
        self.uid = None
        self.pipe = None

    def initialize(self, kernel, name=None):
        kernel.module_instance_close(name)
        Module.initialize(kernel, name)
        self.kernel = kernel
        self.name = name
        self.Show()

        try:
            self.pipe = self.kernel.module_instances['Console']
        except KeyError:
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(False)
            dlg = wx.MessageDialog(None, _("Console module does not exist.."),
                                   _("No Console."), wx.OK | wx.ICON_WARNING)
            result = dlg.ShowModal()
            dlg.Destroy()
            return
        self.kernel.listen('console', self.update_console)

    def shutdown(self, kernel):
        self.Close()
        Module.shutdown(self, kernel)
        self.kernel = None

    def on_close(self, event):
        self.kernel.unlisten('console', self.update_console)
        self.kernel.module_instance_remove(self.name)
        event.Skip()

    def __set_properties(self):
        # begin wxGlade: Terminal.__set_properties
        self.SetTitle(_("Terminal"))
        self.text_entry.SetFocus()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Terminal.__do_layout
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.text_console, 20, wx.EXPAND, 0)
        sizer_2.Add(self.text_entry, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_2)
        self.Layout()
        # end wxGlade

    def update_console(self):
        if self.pipe is not None:
            r = self.pipe.read()
            if r is not None:
                self.text_console.AppendText(r)

    def on_entry(self, event):  # wxGlade: Terminal.<event_handler>
        if self.pipe is not None:
            self.pipe.write(self.text_entry.GetValue() + "\n")
            self.text_entry.SetValue('')
            self.update_console()
        event.Skip()
