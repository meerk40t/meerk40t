import wx

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode
# end wxGlade


class BufferView(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: BufferView.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((697, 584))
        self.text_buffer_length = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_buffer_info = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_CHARWRAP | wx.TE_MULTILINE)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade
        self.project = None
        self.dirty = False
        self.append_text = ""

    def set_project(self, project):
        self.project = project
        buffer = self.project.controller.buffer + self.project.controller.add_queue
        try:
            bufferstr = buffer.decode()
        except ValueError:
            bufferstr = buffer.decode("ascii")
        self.text_buffer_length = self.text_buffer_length.SetValue(str(len(bufferstr)))
        self.text_buffer_info = self.text_buffer_info.SetValue(bufferstr)

    def __set_properties(self):
        # begin wxGlade: BufferView.__set_properties
        self.SetTitle("BufferView")
        self.text_buffer_length.SetMinSize((165, 23))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: BufferView.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        label_8 = wx.StaticText(self, wx.ID_ANY, "Buffer")
        sizer_5.Add(label_8, 0, 0, 0)
        sizer_5.Add(self.text_buffer_length, 10, 0, 0)
        sizer_1.Add(sizer_5, 0, wx.EXPAND, 0)
        sizer_1.Add(self.text_buffer_info, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

# end of class BufferView