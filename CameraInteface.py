import threading

import wx

from Kernel import Module, Job
from LaserRender import DRAW_MODE_FLIPXY, DRAW_MODE_INVERT
from ZMatrix import ZMatrix
from icons import *
from svgelements import SVGImage, Matrix, Point

_ = wx.GetTranslation

CORNER_SIZE = 25


class CameraInterface(wx.Frame, Module, Job):
    def __init__(self, context, path, parent, *args, **kwds):
        wx.Frame.__init__(self, parent, -1, "",
                          style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT | wx.TAB_TRAVERSAL)
        Module.__init__(self, context, path)
        Job.__init__(self, job_name="Camera")
        if len(args) > 0 and args[0] >= 1:
            self.settings_value = args[0]
        else:
            self.settings_value = 0
        self.SetSize((600, 600))
        self.CameraInterface_menubar = wx.MenuBar()
        wxglade_tmp_menu = wx.Menu()
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Reset Perspective"), "")
        self.Bind(wx.EVT_MENU, self.reset_perspective, id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Reset Fisheye"), "")
        self.Bind(wx.EVT_MENU, self.reset_fisheye, id=item.GetId())
        wxglade_tmp_menu.AppendSeparator()

        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Set URI"), "")
        self.Bind(wx.EVT_MENU, lambda e: self.ip_menu_edit(), id=item.GetId())

        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Set IP Camera"), "", wx.ITEM_RADIO)
        self.ip_camera_menu = item
        self.Bind(wx.EVT_MENU, lambda e: self.swap_camera(-1), id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Set Camera 0"), "", wx.ITEM_RADIO)
        self.camera_0_menu = item
        self.Bind(wx.EVT_MENU, lambda e: self.swap_camera(0), id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Set Camera 1"), "", wx.ITEM_RADIO)
        self.camera_1_menu = item
        self.Bind(wx.EVT_MENU, lambda e: self.swap_camera(1), id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Set Camera 2"), "", wx.ITEM_RADIO)
        self.camera_2_menu = item
        self.Bind(wx.EVT_MENU, lambda e: self.swap_camera(2), id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Set Camera 3"), "", wx.ITEM_RADIO)
        self.camera_3_menu = item
        self.Bind(wx.EVT_MENU, lambda e: self.swap_camera(3), id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Set Camera 4"), "", wx.ITEM_RADIO)
        self.camera_4_menu = item
        self.Bind(wx.EVT_MENU, lambda e: self.swap_camera(4), id=item.GetId())

        self.CameraInterface_menubar.Append(wxglade_tmp_menu, _("Camera"))
        self.SetMenuBar(self.CameraInterface_menubar)
        # Menu Bar

        self.button_update = wx.BitmapButton(self, wx.ID_ANY, icons8_camera_50.GetBitmap())
        self.button_export = wx.BitmapButton(self, wx.ID_ANY, icons8_picture_in_picture_alternative_50.GetBitmap())
        self.button_reconnect = wx.BitmapButton(self, wx.ID_ANY, icons8_connected_50.GetBitmap())
        self.check_fisheye = wx.CheckBox(self, wx.ID_ANY, _("Correct Fisheye"))
        self.check_perspective = wx.CheckBox(self, wx.ID_ANY, _("Correct Perspective"))
        self.slider_fps = wx.Slider(self, wx.ID_ANY, 24, 0, 60, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.button_detect = wx.BitmapButton(self, wx.ID_ANY, icons8_detective_50.GetBitmap())
        self.display_camera = wx.Panel(self, wx.ID_ANY)
        self.__set_properties()
        self.__do_layout()

        self.camera_job = None
        self.fetch_job = None
        self.camera_setting = None
        self.setting = None

        self.current_frame = None
        self.last_frame = None

        self.current_raw = None
        self.last_raw = None

        self.capture = None
        self.image_width = -1
        self.image_height = -1
        self._Buffer = None

        self.frame_bitmap = None

        self.fisheye_k = None
        self.fisheye_d = None

        # Used during calibration.
        self.objpoints = []  # 3d point in real world space
        self.imgpoints = []  # 2d points in image plane.

        # Perspective Points
        self.perspective = None

        self.previous_window_position = None
        self.previous_scene_position = None

        self.corner_drag = None

        self.matrix = Matrix()

        self.Bind(wx.EVT_BUTTON, self.on_button_update, self.button_update)
        self.Bind(wx.EVT_BUTTON, self.on_button_export, self.button_export)
        self.Bind(wx.EVT_BUTTON, self.on_button_reconnect, self.button_reconnect)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_fisheye, self.check_fisheye)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_perspective, self.check_perspective)
        self.Bind(wx.EVT_SLIDER, self.on_slider_fps, self.slider_fps)
        self.Bind(wx.EVT_BUTTON, self.on_button_detect, self.button_detect)
        self.SetDoubleBuffered(True)
        # end wxGlade

        self.display_camera.Bind(wx.EVT_PAINT, self.on_paint)
        self.display_camera.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase)
        self.display_camera.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.display_camera.Bind(wx.EVT_MOUSEWHEEL, self.on_mousewheel)
        self.display_camera.Bind(wx.EVT_MIDDLE_UP, self.on_mouse_middle_up)
        self.display_camera.Bind(wx.EVT_MIDDLE_DOWN, self.on_mouse_middle_down)

        self.display_camera.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_left_down)
        self.display_camera.Bind(wx.EVT_LEFT_UP, self.on_mouse_left_up)
        self.display_camera.Bind(wx.EVT_ENTER_WINDOW,
                                 lambda event: self.display_camera.SetFocus())  # Focus follows mouse.
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

        self.on_size(None)
        self.Bind(wx.EVT_SIZE, self.on_size, self)
        self.camera_lock = threading.Lock()
        self.process = self.update_view
        self.connection_attempts = 0
        self.frame_attempts = 0
        self.last_frame_index = -1
        self.frame_index = 0
        self.quit_thread = False

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.button_update, 0, 0, 0)
        sizer_2.Add(self.button_export, 0, 0, 0)
        sizer_2.Add(self.button_reconnect, 0, 0, 0)
        sizer_3.Add(self.check_fisheye, 0, 0, 0)
        sizer_3.Add(self.check_perspective, 0, 0, 0)
        sizer_2.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_2.Add(self.slider_fps, 1, wx.EXPAND, 0)
        sizer_2.Add(self.button_detect, 0, 0, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        sizer_1.Add(self.display_camera, 10, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_camera_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: CameraInterface.__set_properties
        self.SetTitle("CameraInterface")
        self.button_update.SetToolTip(_("Update Image"))
        self.button_update.SetSize(self.button_update.GetBestSize())
        self.button_export.SetToolTip(_("Export Snapsnot"))
        self.button_export.SetSize(self.button_export.GetBestSize())
        self.button_reconnect.SetToolTip(_("Reconnect Camera"))
        self.button_reconnect.SetSize(self.button_reconnect.GetBestSize())
        self.button_detect.SetToolTip(_("Detect Distortions/Calibration"))
        self.button_detect.SetSize(self.button_detect.GetBestSize())
        # end wxGlade

    @staticmethod
    def sub_register(context):
        context.register('window/CameraURI', CameraURI)

    def on_close(self, event):
        if self.state == 5:
            event.Veto()
        else:
            self.state = 5
            self.context.close(self.name)
            event.Skip()  # Call destroy as regular.

    def initialize(self, *args, **kwargs):
        self.context.close(self.name)
        self.Show()
        self.context.setting(bool, 'mouse_zoom_invert', False)
        self.context.setting(int, 'draw_mode', 0)
        self.context.setting(int, "bed_width", 310)  # Default Value
        self.context.setting(int, "bed_height", 220)  # Default Value

        self.camera_setting = self.context.get_context('/camera')
        self.setting = self.camera_setting.derive(str(self.settings_value))

        self.setting.setting(int, 'index', 0)
        self.setting.setting(int, 'fps', 1)
        self.setting.setting(bool, 'correction_fisheye', False)
        self.setting.setting(bool, 'correction_perspective', False)
        self.setting.setting(str, 'fisheye', '')
        self.setting.setting(str, 'perspective', '')
        self.setting.setting(str, 'uri', '0')
        self.check_fisheye.SetValue(self.setting.correction_fisheye)
        self.check_perspective.SetValue(self.setting.correction_perspective)
        if self.setting.fisheye is not None and len(self.setting.fisheye) != 0:
            self.fisheye_k, self.fisheye_d = eval(self.setting.fisheye)
        if self.setting.perspective is not None and len(self.setting.perspective) != 0:
            self.perspective = eval(self.setting.perspective)
        self.slider_fps.SetValue(self.setting.fps)

        if self.camera_job is not None:
            self.camera_job.cancel()
        self.open_camera(self.setting.index)
        self.context.listen('camera_uri_changed', self.on_camera_uri_change)
        self.context.listen('camera_frame_raw', self.on_camera_frame_raw)
        self.set_camera_checks()

    def finalize(self, *args, **kwargs):
        self.setting.flush()
        self.camera_setting.flush()
        self.context.unlisten('camera_uri_changed', self.on_camera_uri_change)
        self.context.unlisten('camera_frame_raw', self.on_camera_frame_raw)
        self.quit_thread = True
        if self.camera_job is not None:
            self.camera_job.cancel()
        if self.fetch_job is not None:
            self.fetch_job.cancel()
        try:
            self.Close()
            self.quit_thread = True # was shutdown value
        except RuntimeError:
            pass

    def on_size(self, event):
        self.Layout()
        width, height = self.ClientSize
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        self._Buffer = wx.Bitmap(width, height)
        self.update_in_gui_thread()

    def on_camera_uri_change(self, *args):
        pass

    def ip_menu_edit(self):
        """
        Select a particular URI.
        :param uri:
        :return:
        """
        self.context.console('window open CameraURI %s %s\n' % (self.settings_value, self.setting.uri))

    def ip_menu_uri_change(self, uri):
        def function(event=None):
            self.ip_menu_uri(uri)

        return function

    def ip_menu_uri(self, uri):
        """
        Select a particular URI.
        :param uri:
        :return:
        """
        self.setting.uri = uri
        self.swap_camera(-1)

    def set_camera_checks(self):
        """
        Set the checkmarks based on the index value.

        :return:
        """

        if self.setting.index == 0:
            self.camera_0_menu.Check(True)
        elif self.setting.index == 1:
            self.camera_1_menu.Check(True)
        elif self.setting.index == 2:
            self.camera_2_menu.Check(True)
        elif self.setting.index == 3:
            self.camera_3_menu.Check(True)
        elif self.setting.index == 4:
            self.camera_4_menu.Check(True)
        else:
            self.ip_camera_menu.Check(True)

    def update_view(self):
        frame = self.last_frame
        if frame is None:
            return
        print("%d vs %d" % (self.last_frame_index, self.frame_index))
        if self.frame_index == self.last_frame_index:
            return
        else:
            self.last_frame_index = self.frame_index
        bed_width = self.context.bed_width * 2
        bed_height = self.context.bed_height * 2

        self.image_height, self.image_width = frame.shape[:2]
        self.frame_bitmap = wx.Bitmap.FromBuffer(self.image_width, self.image_height, frame)

        if self.setting.correction_perspective:
            if bed_width != self.image_width or bed_height != self.image_height:
                self.image_width = bed_width
                self.image_height = bed_height
                self.display_camera.SetSize((self.image_width, self.image_height))
        self.update_in_gui_thread()

    def on_camera_frame_raw(self, *args):
        """
        Raw Camera frame was requested and should be processed.

        This attempts to perform checkboard detection.

        :param frame:
        :return:
        """
        frame = self.last_raw
        if frame is None:
            return
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
            self.objpoints = self.objpoints[:-1]  # Deleting the last entry.
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
        self.setting.fisheye = repr([K.tolist(), D.tolist()])
        self.fisheye_k = K.tolist()
        self.fisheye_d = D.tolist()

    def swap_camera(self, camera_index=0):
        """
        Disconnect the current connected camera.
        Connect to the provided camera index.

        :param camera_index:
        :return:
        """
        with self.camera_lock:
            self.close_camera()
            self.open_camera(camera_index)
        self.set_camera_checks()

    def init_camera(self):
        """
        Connect to Camera.

        :return:
        """
        if self.context is None:
            return
        if self.capture is not None:
            self.capture = None
        try:
            import cv2
        except ImportError:
            wx.CallAfter(self.camera_error_requirement)
            return
        wx.CallAfter(lambda: self.set_control_enable(True))
        try:
            self.interval = 1.0 / self.setting.fps
        except ZeroDivisionError:
            self.interval = 5
        except AttributeError:
            return
        self.context._kernel.threaded(self.threaded_image_fetcher)
        self.context.schedule(self)

    def open_camera(self, camera_index=0):
        """
        Open Camera device. Prevents opening if already opening.

        :param camera_index:
        :return:
        """
        if self.camera_job is not None:
            self.camera_job.cancel()
        self.setting.index = camera_index
        uri = self.get_camera_uri()
        if uri is not None:
            self.camera_job = self.context._kernel.add_job(self.init_camera, times=1, interval=0.1)

    def close_camera(self):
        """
        Disconnect from the current camera.

        :return:
        """
        self.context.unschedule(self)
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def set_control_enable(self, enable=False):
        """
        Disable/Enable all the major controls within the GUI.
        :param enable:
        :return:
        """
        try:
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    if value is not self.button_reconnect:
                        value.Enable(enable)
        except RuntimeError:
            pass

    def camera_error_requirement(self):
        """
        Message Error that OpenCV is not installed and thus camera cannot run.

        Disable all Controls.

        :return:
        """
        try:
            self.set_control_enable(False)
            dlg = wx.MessageDialog(None, _(
                "If using a precompiled binary, this was requirement was not included.\nIf using pure Python, add it with: pip install opencv-python-headless"),
                                   _("Interface Requires OpenCV."), wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
        except RuntimeError:
            pass

    def camera_error_webcam(self):
        """
        Message error based on failure to connect to webcam.

        Disable all Controls.

        :return:
        """
        try:
            self.set_control_enable(False)
            dlg = wx.MessageDialog(None, _("No Webcam found."),
                                   _("Error"), wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
        except RuntimeError:
            pass

    def ip_menu_new(self):
        """
        Requests and adds new IP Connection URI.

        :return:
        """
        dlg = wx.TextEntryDialog(self, _(
            "Enter the HTTP or RTSP uri"),
                                 _("Webcam URI Update"), '')
        dlg.SetValue(str(self.get_camera_uri()))
        modal = dlg.ShowModal()
        if modal == wx.ID_OK:
            uri = str(dlg.GetValue())
            index = len(list(self.camera_setting.keylist()))
            setattr(self.camera_setting, 'uri' + str(index), uri)
            self.setting.uri = uri
            self.ip_menu_uri(uri)
            self.swap_camera(-1)
            self.set_camera_checks()

    def get_camera_uri(self):
        """
        Get the current camera URI.

        If the URI

        :return:
        """
        index = self.setting.index
        if index >= 0:
            return index
        uri = self.setting.uri
        if uri is None or len(uri) == 0:
            return None
        try:
            return int(uri)
        except ValueError:
            # URI is not a number.
            return uri

    def attempt_recovery(self):
        try:
            import cv2
        except ImportError:
            return False
        if self.quit_thread:
            return False
        if self.context is None:
            return False
        self.frame_attempts += 1
        if self.frame_attempts < 5:
            return True
        self.frame_attempts = 0

        if self.capture is not None:
            with self.camera_lock:
                self.capture.release()
                self.capture = None
        uri = self.get_camera_uri()
        if uri is None:
            return False

        self.context.signal("camera_initialize")
        with self.camera_lock:
            self.capture = cv2.VideoCapture(uri)

        if self.capture is None:
            return False
        self.connection_attempts += 1
        return True

    def threaded_image_fetcher(self):
        self.quit_thread = False
        try:
            import cv2
        except ImportError:
            return

        raw = False

        uri = self.get_camera_uri()
        if uri is None:
            return
        self.context.signal("camera_initialize")
        with self.camera_lock:
            self.capture = cv2.VideoCapture(uri)

        while not self.quit_thread:
            if self.connection_attempts > 50:
                wx.CallAfter(self.camera_error_webcam)
            with self.camera_lock:
                if self.capture is None:
                    # No capture the thread dies.
                    return
                try:
                    ret = self.capture.grab()
                except AttributeError:
                    continue

                if not ret:
                    if self.attempt_recovery():
                        continue
                    else:
                        return

                ret, frame = self.capture.retrieve()
                if not ret or frame is None:
                    if self.attempt_recovery():
                        continue
                    else:
                        return
            self.frame_attempts = 0
            self.connection_attempts = 0
            self.last_raw = self.current_raw
            self.current_raw = frame

            if not raw and \
                    self.fisheye_k is not None and \
                    self.fisheye_d is not None and \
                    self.context is not None and \
                    self.setting.correction_fisheye:
                # Unfisheye the drawing
                import numpy as np
                K = np.array(self.fisheye_k)
                D = np.array(self.fisheye_d)
                DIM = frame.shape[:2][::-1]
                map1, map2 = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), K, DIM, cv2.CV_16SC2)
                frame = cv2.remap(frame, map1, map2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            if not raw and self.context is not None and self.setting.correction_perspective:
                # Perspective the drawing.
                bed_width = self.context.bed_width * 2
                bed_height = self.context.bed_height * 2
                width, height = frame.shape[:2][::-1]
                import numpy as np
                if self.perspective is None:
                    rect = np.array([
                        [0, 0],
                        [width - 1, 0],
                        [width - 1, height - 1],
                        [0, height - 1]], dtype="float32")
                else:
                    rect = np.array(
                        self.perspective, dtype="float32")
                dst = np.array([
                    [0, 0],
                    [bed_width - 1, 0],
                    [bed_width - 1, bed_height - 1],
                    [0, bed_height - 1]], dtype="float32")
                M = cv2.getPerspectiveTransform(rect, dst)
                frame = cv2.warpPerspective(frame, M, (bed_width, bed_height))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            self.last_frame = self.current_frame
            self.current_frame = frame
            self.frame_index += 1
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        if self.context is not None:
            self.context.signal("camera_finalize")

    def reset_perspective(self, event):
        """
        Reset the perspective settings.

        :param event:
        :return:
        """
        self.perspective = None
        self.setting.perspective = ''

    def reset_fisheye(self, event):
        """
        Reset the fisheye settings.

        :param event:
        :return:
        """
        self.fisheye_k = None
        self.fisheye_d = None
        self.setting.fisheye = ''

    def on_erase(self, event):
        """
        Erase camera view.
        :param event:
        :return:
        """
        pass

    def on_paint(self, event):
        """
        Paint camera view.
        :param event:
        :return:
        """
        try:
            wx.BufferedPaintDC(self.display_camera, self._Buffer)
        except RuntimeError:
            pass

    def on_update_buffer(self, event=None):
        """
        Draw Camera view.

        :param event:
        :return:
        """
        if self.frame_bitmap is None:
            return  # Need the bitmap to refresh.
        dm = self.context.draw_mode
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        dc.Clear()
        w, h = dc.Size
        if dm & DRAW_MODE_FLIPXY != 0:
            dc.SetUserScale(-1, -1)
            dc.SetLogicalOrigin(w, h)
        dc.SetBackground(wx.WHITE_BRUSH)
        gc = wx.GraphicsContext.Create(dc)  # Can crash at bitmap okay
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(self.matrix)))
        gc.PushState()
        gc.DrawBitmap(self.frame_bitmap, 0, 0, self.image_width, self.image_height)
        if not self.setting.correction_perspective:
            if self.perspective is None:
                self.perspective = [0, 0], \
                                   [self.image_width, 0], \
                                   [self.image_width, self.image_height], \
                                   [0, self.image_height]
            gc.SetPen(wx.BLACK_DASHED_PEN)
            gc.StrokeLines(self.perspective)
            gc.StrokeLine(self.perspective[0][0], self.perspective[0][1],
                          self.perspective[3][0], self.perspective[3][1])
            gc.SetPen(wx.BLUE_PEN)
            for p in self.perspective:
                half = CORNER_SIZE / 2
                gc.StrokeLine(p[0] - half, p[1], p[0] + half, p[1])
                gc.StrokeLine(p[0], p[1] - half, p[0], p[1] + half)
                gc.DrawEllipse(p[0] - half, p[1] - half, CORNER_SIZE, CORNER_SIZE)
        gc.PopState()
        if dm & DRAW_MODE_INVERT != 0:
            dc.Blit(0, 0, w, h, dc, 0, 0, wx.SRC_INVERT)
        gc.Destroy()
        del dc

    def convert_scene_to_window(self, position):
        """
        Scene Matrix convert scene to window.
        :param position:
        :return:
        """
        point = self.matrix.point_in_matrix_space(position)
        return point[0], point[1]

    def convert_window_to_scene(self, position):
        """
        Scene Matrix convert window to scene.
        :param position:
        :return:
        """
        point = self.matrix.point_in_inverse_space(position)
        return point[0], point[1]

    def on_mouse_move(self, event):
        """
        Handle mouse movement.

        :param event:
        :return:
        """
        if not event.Dragging():
            return
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        if self.previous_window_position is None:
            return
        pos = event.GetPosition()
        window_position = pos.x, pos.y
        scene_position = self.convert_window_to_scene([window_position[0], window_position[1]])
        sdx = (scene_position[0] - self.previous_scene_position[0])
        sdy = (scene_position[1] - self.previous_scene_position[1])
        wdx = (window_position[0] - self.previous_window_position[0])
        wdy = (window_position[1] - self.previous_window_position[1])
        if self.corner_drag is None:
            self.scene_post_pan(wdx, wdy)
        else:
            self.perspective[self.corner_drag][0] += sdx
            self.perspective[self.corner_drag][1] += sdy
            self.setting.perspective = repr(self.perspective)
        self.previous_window_position = window_position
        self.previous_scene_position = scene_position

    def on_mousewheel(self, event):
        """
        Handle mouse wheel.

        Used for zooming.

        :param event:
        :return:
        """
        rotation = event.GetWheelRotation()
        mouse = event.GetPosition()
        if self.context.get_context('/').mouse_zoom_invert:
            rotation = -rotation
        if rotation > 1:
            self.scene_post_scale(1.1, 1.1, mouse[0], mouse[1])
        elif rotation < -1:
            self.scene_post_scale(0.9, 0.9, mouse[0], mouse[1])

    def on_mouse_left_down(self, event):
        """
        Handle mouse left down event.

        Used for adjusting perspective items.

        :param event:
        :return:
        """
        self.previous_window_position = event.GetPosition()
        self.previous_scene_position = self.convert_window_to_scene(self.previous_window_position)
        self.corner_drag = None
        if self.perspective is not None:
            for i, p in enumerate(self.perspective):
                half = CORNER_SIZE / 2
                if Point.distance(self.previous_scene_position, p) < half:
                    self.corner_drag = i
                    break

    def on_mouse_left_up(self, event):
        """
        Handle Mouse Left Up.

        Drag Ends.

        :param event:
        :return:
        """
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        self.previous_window_position = None
        self.previous_scene_position = None
        self.corner_drag = None

    def on_mouse_middle_down(self, event):
        """
        Handle mouse middle down

        Panning.

        :param event:
        :return:
        """
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.previous_window_position = event.GetPosition()
        self.previous_scene_position = self.convert_window_to_scene(self.previous_window_position)

    def on_mouse_middle_up(self, event):
        """
        Handle mouse middle up.

        Pan ends.

        :param event:
        :return:
        """
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        self.previous_window_position = None
        self.previous_scene_position = None

    def scene_post_pan(self, px, py):
        """
        Scene Pan.
        :param px:
        :param py:
        :return:
        """
        self.matrix.post_translate(px, py)
        self.on_update_buffer()

    def scene_post_scale(self, sx, sy=None, ax=0, ay=0):
        """
        Scene Zoom.
        :param sx:
        :param sy:
        :param ax:
        :param ay:
        :return:
        """
        self.matrix.post_scale(sx, sy, ax, ay)
        self.on_update_buffer()

    def update_in_gui_thread(self):
        """
        Redraw on the GUI thread.
        :return:
        """
        self.on_update_buffer()
        try:
            self.Refresh(True)
            self.Update()
        except RuntimeError:
            pass

    def on_check_perspective(self, event):
        """
        Perspective checked. Turns on/off
        :param event:
        :return:
        """
        self.setting.correction_perspective = self.check_perspective.GetValue()

    def on_check_fisheye(self, event):
        """
        Fisheye checked. Turns on/off.
        :param event:
        :return:
        """
        self.setting.correction_fisheye = self.check_fisheye.GetValue()

    def on_button_update(self, event):  # wxGlade: CameraInterface.<event_handler>
        """
        Button update.

        Sets image background to main scene.

        :param event:
        :return:
        """
        frame = self.context.last_signal('camera_frame')
        if frame is not None:
            frame = frame[0]
            buffer = wx.Bitmap.FromBuffer(self.image_width, self.image_height, frame)
            self.context.signal('background', buffer)

    def on_button_export(self, event):  # wxGlade: CameraInterface.<event_handler>
        """
        Button export.

        Sends an image to the scene as an exported object.
        :param event:
        :return:
        """
        frame = self.context.last_signal('camera_frame')
        if frame is not None:
            elements = self.context.elements
            frame = frame[0]
            from PIL import Image
            img = Image.fromarray(frame)
            obj = SVGImage()
            obj.image = img
            obj.image_width = self.image_width
            obj.image_height = self.image_height
            elements.add_elem(obj)

    def on_button_reconnect(self, event):  # wxGlade: CameraInterface.<event_handler>
        self.quit_thread = True

    def on_slider_fps(self, event):  # wxGlade: CameraInterface.<event_handler>
        """
        Adjusts the camera FPS.

        If set to 0, this will be a frame each 5 seconds.

        :param event:
        :return:
        """
        fps = self.slider_fps.GetValue()
        if fps == 0:
            tick = 5
        else:
            tick = 1.0 / fps
        self.setting.fps = fps
        self.interval = tick

    def on_button_detect(self, event):  # wxGlade: CameraInterface.<event_handler>
        """
        Attempts to locate 6x9 checkerboard pattern for OpenCV to correct the fisheye pattern.

        :param event:
        :return:
        """
        if self.fetch_job is not None:
            self.fetch_job.cancel()
        # TODO: This won't work anymore.
        self.context.signal('camera_frame_raw', None)

        self.fetch_job = self.context.add_job(self.on_camera_frame_raw, args=True, times=1, interval=0)


class CameraURI(wx.Frame, Module):
    def __init__(self, context, path, parent, *args, **kwds):
        # begin wxGlade: CameraURI.__init__
        wx.Frame.__init__(self, parent, -1, "",
                          style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT | wx.TAB_TRAVERSAL)
        if 'param' in kwds:
            self.set_name, self.set_uri = kwds['param']
        else:
            self.set_name = None
            self.set_uri = ''
        Module.__init__(self, context, path)
        self.SetSize((437, 530))
        self.list_uri = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.button_add = wx.Button(self, wx.ID_ANY, "Add URI")
        self.text_uri = wx.TextCtrl(self, wx.ID_ANY, self.set_uri)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_list_activated, self.list_uri)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_list_right_clicked, self.list_uri)
        self.Bind(wx.EVT_BUTTON, self.on_button_add_uri, self.button_add)
        self.Bind(wx.EVT_TEXT, self.on_text_uri, self.text_uri)
        # end wxGlade
        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.camera_setting = None
        self.camera_dict = dict()
        self.changed = False

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_camera_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: CameraURI.__set_properties
        self.SetTitle("Camera URI")
        self.list_uri.SetToolTip("Displays a list of registered camera URIs")
        self.list_uri.AppendColumn("Index", format=wx.LIST_FORMAT_LEFT, width=69)
        self.list_uri.AppendColumn("URI", format=wx.LIST_FORMAT_LEFT, width=348)
        self.button_add.SetToolTip("Add a new URL")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: CameraURI.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(self.list_uri, 1, wx.EXPAND, 0)
        sizer_2.Add(self.button_add, 0, 0, 0)
        sizer_2.Add(self.text_uri, 2, 0, 0)
        sizer_1.Add(sizer_2, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def on_close(self, event):
        if self.state == 5:
            event.Veto()
        else:
            self.state = 5
            self.context.close(self.name)
            event.Skip()  # Call destroy as regular.

    def initialize(self, *args, **kwargs):
        self.context.close(self.name)
        self.Show()
        self.camera_setting = self.context.get_context('/camera')
        self.camera_dict = self.camera_setting._kernel.load_persistent_string_dict(self.camera_setting._path)
        self.on_list_refresh()

    def finalize(self, *args, **kwargs):
        self.commit()
        try:
            self.Close()
        except RuntimeError:
            pass

    def commit(self):
        if not self.changed:
            return
        camera = self.camera_setting
        for c in list(camera.keylist()):
            try:
                print(self.camera_setting)
                setattr(self.camera_setting, c, None)
                self.camera_setting.delete_persistent(c)
            except (IndexError, AttributeError):
                break

        for key in self.camera_dict:
            value = self.camera_dict[key]
            if isinstance(value, str):
                setattr(self.camera_setting, key, value)
        self.camera_setting.flush()
        self.context.signal('camera_uri_changed', True)

    def on_list_refresh(self):
        self.list_uri.DeleteAllItems()
        for i, c in enumerate(self.camera_dict):
            camera_item = self.camera_dict[c]
            if camera_item == '':
                continue
            m = self.list_uri.InsertItem(i, c)
            if m != -1:
                if camera_item == self.set_uri:
                    self.list_uri.Select(i)
                self.list_uri.SetItem(m, 1, str(camera_item))

    def on_list_activated(self, event):  # wxGlade: CameraURI.<event_handler>
        index = event.GetIndex()
        element = event.Text
        new_url = self.camera_dict[element]
        interface = self.context.find('window', 'CameraInterface:%s' % self.set_name)
        if interface is not None:
            self.context.signal('camera_uri_set', self.set_uri, new_url)
            self.Close()

    def on_list_right_clicked(self, event):  # wxGlade: CameraURI.<event_handler>
        index = event.GetIndex()
        element = event.Text
        menu = wx.Menu()
        convert = menu.Append(wx.ID_ANY, _("Remove %s") % str(element)[:16], "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_delete(element), convert)
        convert = menu.Append(wx.ID_ANY, _("Clear All"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_clear(element), convert)
        self.PopupMenu(menu)
        menu.Destroy()

    def on_tree_popup_delete(self, element):
        def delete(event):
            try:
                del self.camera_dict[element]
            except KeyError:
                pass
            self.changed = True
            self.on_list_refresh()

        return delete

    def on_tree_popup_clear(self, element):
        def delete(event):
            self.camera_dict = dict()
            self.changed = True
            self.on_list_refresh()

        return delete

    def on_button_add_uri(self, event):  # wxGlade: CameraURI.<event_handler>
        uri = self.text_uri.GetValue()
        if uri is None or uri == '':
            return
        next_index = 1
        while ('uri%d' % next_index) in self.camera_dict:
            next_index += 1
        self.camera_dict['uri%d' % next_index] = uri
        self.text_uri.SetValue('')
        self.changed = True
        self.on_list_refresh()

    def on_text_uri(self, event):  # wxGlade: CameraURI.<event_handler>
        pass
