import wx

_ = wx.GetTranslation


class CameraInterface(wx.Frame):
    def __init__(self, *args, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)

        try:
            import cv2
        except ImportError:
            dlg = wx.MessageDialog(None, _("This Interface Requires OpenCV: pip install opencv-python-headless"),
                                   _("Error"), wx.OK | wx.ICON_WARNING)
            result = dlg.ShowModal()
            dlg.Destroy()
            return

        self.imgSizer = (480, 360)
        self.pnl = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.image = wx.EmptyImage(self.imgSizer[0], self.imgSizer[1])
        self.imageBit = wx.BitmapFromImage(self.image)
        self.staticBit = wx.StaticBitmap(self.pnl, wx.ID_ANY, self.imageBit)

        self.vbox.Add(self.staticBit)

        self.capture = cv2.VideoCapture(0)
        ret, self.frame = self.capture.read()
        if ret:
            self.height, self.width = self.frame.shape[:2]
            self.bmp = wx.BitmapFromBuffer(self.width, self.height, self.frame)

            self.timex = wx.Timer(self)
            self.timex.Start(1000. / 1)
            self.Bind(wx.EVT_TIMER, self.fetch_image)
            self.SetSize(self.imgSizer)
        else:
            dlg = wx.MessageDialog(None, _("No Webcam found."),
                                   _("Error"), wx.OK | wx.ICON_WARNING)
            result = dlg.ShowModal()
            dlg.Destroy()
        self.pnl.SetSizer(self.vbox)
        self.vbox.Fit(self)
        self.Show()
        self.kernel = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        self.kernel.mark_window_closed("CameraInterface")
        event.Skip()  # Call destroy.

    def set_kernel(self, kernel):
        self.kernel = kernel
        self.device = kernel.device

    def fetch_image(self, e):
        import cv2
        ret, self.frame = self.capture.read()
        if ret:
            self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            self.bmp.CopyFromBuffer(self.frame)
            self.staticBit.SetBitmap(self.bmp)
            self.Refresh()