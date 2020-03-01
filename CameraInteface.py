import wx

from icons import *
from svgelements import SVGImage

_ = wx.GetTranslation


class CameraInterface(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: CameraInterface.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((451, 489))

        self.button_update = wx.BitmapButton(self, wx.ID_ANY, icons8_camera_50.GetBitmap())
        self.button_export = wx.BitmapButton(self, wx.ID_ANY, icons8_picture_in_picture_alternative_50.GetBitmap())
        self.check_fisheye = wx.CheckBox(self, wx.ID_ANY, _("Correct Fisheye"))
        self.slider_fps = wx.Slider(self, wx.ID_ANY, 1, 0, 24, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.button_detect = wx.BitmapButton(self, wx.ID_ANY, icons8_detective_50.GetBitmap())
        self.display_camera = wx.Panel(self, wx.ID_ANY)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_update, self.button_update)
        self.Bind(wx.EVT_BUTTON, self.on_button_export, self.button_export)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_fisheye, self.check_fisheye)
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
            dlg = wx.MessageDialog(None, _("If using a precompiled binary, this was requirement was not included.\nIf using pure Python, add it with: pip install opencv-python-headless"),
                                   _("Interface Requires OpenCV."), wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            return
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
        self.fisheye_k = None
        self.fisheye_d = None

        # Used during calibration.
        self.objpoints = []  # 3d point in real world space
        self.imgpoints = []  # 2d points in image plane.

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
        self.kernel.setting(int, 'camera_fps', 1)
        self.kernel.setting(bool, 'camera_correction_fisheye', True)
        self.kernel.setting(str, 'fisheye', '')
        self.check_fisheye.SetValue(kernel.camera_correction_fisheye)
        self.job = self.kernel.cron.add_job(self.fetch_image)
        if kernel.fisheye is not None and len(kernel.fisheye) != 0:
            self.fisheye_k, self.fisheye_d = eval(kernel.fisheye)

        self.slider_fps.SetValue(kernel.camera_fps)
        self.on_slider_fps(None)

    def capture_frame(self, raw=False):
        import cv2
        ret, frame = self.capture.read()
        if not ret or frame is None:
            return None
        if not raw and\
                self.fisheye_k is not None and \
                self.fisheye_d is not None and \
                self.kernel is not None and \
                self.kernel.camera_correction_fisheye:
            # Unfisheye the drawing
            import numpy as np
            K = np.array(self.fisheye_k)
            D = np.array(self.fisheye_d)
            DIM = frame.shape[:2][::-1]
            map1, map2 = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), K, DIM, cv2.CV_16SC2)
            frame = cv2.remap(frame, map1, map2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame

    def fetch_image(self):
        if self.kernel is None or self.capture is None:
            return
        try:
            self.frame = self.capture_frame()
            if self.frame is not None:
                self._Buffer.CopyFromBuffer(self.frame)
                wx.CallAfter(self.update_in_gui_thread)
        except RuntimeError:
            pass  # Failed to gain access to raw bitmap data: skip frame.

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
        sizer_2.Add(self.check_fisheye, 0, 0, 0)
        sizer_2.Add(self.slider_fps, 0, wx.EXPAND, 0)
        sizer_2.Add(self.button_detect, 0, 0, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        sizer_1.Add(self.display_camera, 10, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def on_check_fisheye(self, event):
        self.kernel.camera_correction_fisheye = self.check_fisheye.GetValue()

    def on_button_update(self, event):  # wxGlade: CameraInterface.<event_handler>
        frame = self.capture_frame()
        if frame is not None:
            buffer = wx.Bitmap.FromBuffer(self.width, self.height, frame)
            self.kernel.signal("background", buffer)

    def on_button_export(self, event):  # wxGlade: CameraInterface.<event_handler>
        frame = self.capture_frame()
        if frame is not None:
            from PIL import Image
            img = Image.fromarray(frame)
            obj = SVGImage()
            obj.image = img
            obj.image_width = self.width
            obj.image_height = self.height
            self.kernel.elements.append(obj)
            self.kernel.signal('refresh_elements',0)
            self.kernel.signal('rebuild_tree',0)

    def on_slider_fps(self, event):  # wxGlade: CameraInterface.<event_handler>
        fps = self.slider_fps.GetValue()
        if fps == 0:
            tick = 5
        else:
            tick = 1.0 / fps
        self.kernel.camera_fps = fps
        self.job.interval = tick

    def on_button_detect(self, event):  # wxGlade: CameraInterface.<event_handler>
        try:
            import cv2
            import numpy as np
        except:
            dlg = wx.MessageDialog(None, _("Could not import Camera requirements"),
                                _("Imports Failed"), wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        CHECKERBOARD = (6, 9)
        subpix_criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1)
        calibration_flags = cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC + cv2.fisheye.CALIB_CHECK_COND + cv2.fisheye.CALIB_FIX_SKEW
        objp = np.zeros((1, CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
        objp[0, :, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)

        frame = self.capture_frame(raw=True)
        img = frame
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Find the chess board corners
        ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD,
                                                     cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK + cv2.CALIB_CB_NORMALIZE_IMAGE)
            # If found, add object points, image points (after refining them)

        if ret:
            self.objpoints.append(objp)
            cv2.cornerSubPix(gray, corners, (3, 3), (-1, -1), subpix_criteria)
            self.imgpoints.append(corners)
        else:
            dlg = wx.MessageDialog(None, _("Checkerboard 6x9 pattern not found."),
                                   _("Pattern not found."), wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        N_OK = len(self.objpoints)
        K = np.zeros((3, 3))
        D = np.zeros((4, 1))
        rvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
        tvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
        try:
            rms, a, b, c, d = \
                cv2.fisheye.calibrate(
                    self.objpoints,
                    self.imgpoints,
                    gray.shape[::-1],
                    K,
                    D,
                    rvecs,
                    tvecs,
                    calibration_flags,
                    (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-6)
                )
        except cv2.error:
            # Ill conditioned matrix for input values.
            self.objpoints = self.objpoints[:-1] # Deleting the last entry.
            self.imgpoints = self.imgpoints[:-1]
            dlg = wx.MessageDialog(None, _("Ill-conditioned Matrix. Keep trying."),
                                   _("Matrix."), wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        dlg = wx.MessageDialog(None, _("Success. %d images so far." % len(self.objpoints)),
                               _("Image Captured"), wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
        self.kernel.fisheye = repr([K.tolist(), D.tolist()])
        self.fisheye_k = K.tolist()
        self.fisheye_d = D.tolist()

# end of class CameraInterface
