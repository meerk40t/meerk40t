import wx

_ = wx.GetTranslation

#TODO: Issue #53 ( https://github.com/meerk40t/meerk40t/issues/53 ) Lacks mouseover hints.

class BufferView(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: BufferView.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((697, 584))
        self.text_buffer_length = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_buffer_info = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_CHARWRAP | wx.TE_MULTILINE)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade
        self.kernel = None
        self.device = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        self.kernel.mark_window_closed("BufferView")
        self.kernel = None
        event.Skip()  # Call destroy as regular.

    def set_kernel(self, kernel):
        self.kernel = kernel
        self.device = kernel.device
        if self.device is None:
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(False)
            dlg = wx.MessageDialog(None, _("You do not have a selected device."),
                                   _("No Device Selected."), wx.OK | wx.ICON_WARNING)
            result = dlg.ShowModal()
            dlg.Destroy()
        else:
            pipe = self.device.pipe
            buffer = None
            if pipe is not None:
                try:
                    buffer = pipe.buffer + pipe.queue
                except AttributeError:
                    buffer = None
            if buffer is None:
                buffer = _("Could not find buffer.\n")

            try:
                bufferstr = buffer.decode()
            except ValueError:
                bufferstr = buffer.decode("ascii")

            self.text_buffer_length = self.text_buffer_length.SetValue(str(len(bufferstr)))
            self.text_buffer_info = self.text_buffer_info.SetValue(bufferstr)

    def __set_properties(self):
        # begin wxGlade: BufferView.__set_properties
        self.SetTitle(_("BufferView"))
        self.text_buffer_length.SetMinSize((165, 23))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: BufferView.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        label_8 = wx.StaticText(self, wx.ID_ANY, _("Buffer"))
        sizer_5.Add(label_8, 0, 0, 0)
        sizer_5.Add(self.text_buffer_length, 10, 0, 0)
        sizer_1.Add(sizer_5, 0, wx.EXPAND, 0)
        sizer_1.Add(self.text_buffer_info, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

# end of class BufferView
