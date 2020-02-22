import wx

from icons import *

_ = wx.GetTranslation


class CameraInterface(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: CameraInterface.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((451, 489))

        self.button_update = wx.BitmapButton(self, wx.ID_ANY, icons8_camera_50.GetBitmap())
        self.button_export = wx.BitmapButton(self, wx.ID_ANY, icons8_picture_in_picture_alternative_50.GetBitmap())
        self.slider_fps = wx.Slider(self, wx.ID_ANY, 1, 0, 24, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.button_detect = wx.BitmapButton(self, wx.ID_ANY, icons8_detective_50.GetBitmap())
        self.display_camera = wx.Panel(self, wx.ID_ANY)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_update, self.button_update)
        self.Bind(wx.EVT_BUTTON, self.on_button_export, self.button_export)
        self.Bind(wx.EVT_SLIDER, self.on_slider_fps, self.slider_fps)
        self.Bind(wx.EVT_BUTTON, self.on_button_detect, self.button_detect)
        self.SetDoubleBuffered(True)
        # end wxGlade
        self.capture = None
        self.width = -1
        self.height = -1
        self.kernel = None
        self._Buffer = None
        try:
            import cv2
        except ImportError:
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(False)
            dlg = wx.MessageDialog(None, _("This Interface Requires OpenCV: 'pip install opencv-python-headless'"),
                                   _("Error"), wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            return
        try:
            self.capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        except TypeError:
            self.capture = cv2.VideoCapture(0)
        ret, self.frame = self.capture.read()
        if not ret:
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(False)
            dlg = wx.MessageDialog(None, _("No Webcam found."),
                                   _("Error"), wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            self.capture = None
            return
        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.height, self.width = self.frame.shape[:2]
        self._Buffer = wx.Bitmap.FromBuffer(self.width, self.height, self.frame)
        self.display_camera.SetSize((self.width, self.height))
        self.display_camera.Bind(wx.EVT_PAINT, self.on_paint)
        self.display_camera.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase)
        self.job = None

    def on_erase(self, event):
        pass

    def on_paint(self, event):
        try:
            wx.BufferedPaintDC(self.display_camera, self._Buffer)
        except RuntimeError:
            pass

    def on_close(self, event):
        if self.capture is not None:
            self.capture.release()
        self.kernel.mark_window_closed("CameraInterface")
        self.kernel = None
        event.Skip()  # Call destroy.
        self.job.cancel()

    def set_kernel(self, kernel):
        self.kernel = kernel
        self.job = self.kernel.cron.add_job(self.fetch_image)

    def fetch_image(self):
        if self.kernel is None or self.capture is None:
            return
        import cv2
        ret, self.frame = self.capture.read()
        if ret:
            self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            self._Buffer.CopyFromBuffer(self.frame)
            wx.CallAfter(self.update_in_gui_thread)

    def update_in_gui_thread(self):
        if self.kernel is None:
            return
        self.display_camera.Refresh(True)

    def __set_properties(self):
        # begin wxGlade: CameraInterface.__set_properties
        self.SetTitle(_("CameraInterface"))
        self.button_update.SetToolTip(_("Update Scene"))
        self.button_update.SetSize(self.button_update.GetBestSize())
        self.button_export.SetToolTip(_("Export Snapsnot"))
        self.button_export.SetSize(self.button_export.GetBestSize())
        self.button_detect.SetToolTip(_("Detect Distortions/Calibration"))
        self.button_detect.SetSize(self.button_detect.GetBestSize())
        self.display_camera.SetToolTip(_("Live Camera View"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: CameraInterface.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(self.button_update, 0, 0, 0)
        sizer_2.Add(self.button_export, 0, 0, 0)
        label_1 = wx.StaticText(self, wx.ID_ANY, "")
        sizer_2.Add(label_1, 1, 0, 0)
        sizer_2.Add(self.slider_fps, 0, wx.EXPAND, 0)
        sizer_2.Add(self.button_detect, 0, 0, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        sizer_1.Add(self.display_camera, 10, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def on_button_update(self, event):  # wxGlade: CameraInterface.<event_handler>
        import cv2
        ret, frame = self.capture.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            buffer = wx.Bitmap.FromBuffer(self.width, self.height, frame)
            self.kernel.signal("background", buffer)

    def on_button_export(self, event):  # wxGlade: CameraInterface.<event_handler>
        print("Event handler 'on_button_export' not implemented!")
        event.Skip()

    def on_slider_fps(self, event):  # wxGlade: CameraInterface.<event_handler>
        fps = self.slider_fps.GetValue()
        if fps == 0:
            tick = 5
        else:
            tick = 1.0 / fps
        self.job.interval = tick

    def on_button_detect(self, event):  # wxGlade: CameraInterface.<event_handler>
        dlg = wx.MessageDialog(None, _("This feature is not implemented."),
                               _("Not Implemented"), wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

# end of class CameraInterface
