import threading

import wx

from Kernel import Module
from ZMatrix import ZMatrix
from icons import *
from svgelements import SVGImage, Matrix, Point

_ = wx.GetTranslation

CORNER_SIZE = 25


class CameraInterface(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: CameraInterface.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((608, 549))
        self.CameraInterface_menubar = wx.MenuBar()
        wxglade_tmp_menu = wx.Menu()
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Reset Perspective"), "")
        self.Bind(wx.EVT_MENU, self.reset_perspective, id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, _("Reset Fisheye"), "")
        self.Bind(wx.EVT_MENU, self.reset_fisheye, id=item.GetId())
        wxglade_tmp_menu.AppendSeparator()

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
        self.check_fisheye = wx.CheckBox(self, wx.ID_ANY, _("Correct Fisheye"))
        self.check_perspective = wx.CheckBox(self, wx.ID_ANY, _("Correct Perspective"))
        self.slider_fps = wx.Slider(self, wx.ID_ANY, 1, 0, 24, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.button_detect = wx.BitmapButton(self, wx.ID_ANY, icons8_detective_50.GetBitmap())
        self.display_camera = wx.Panel(self, wx.ID_ANY)
        self.__set_properties()
        self.__do_layout()

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
        self.process = self.fetch_image

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.button_update, 0, 0, 0)
        sizer_2.Add(self.button_export, 0, 0, 0)
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
        # begin wxGlade: CameraInterface.__set_properties
        self.SetTitle("CameraInterface")
        self.button_update.SetToolTip(_("Update Image"))
        self.button_update.SetSize(self.button_update.GetBestSize())
        self.button_export.SetToolTip(_("Export Snapsnot"))
        self.button_export.SetSize(self.button_export.GetBestSize())
        self.button_detect.SetToolTip(_("Detect Distortions/Calibration"))
        self.button_detect.SetSize(self.button_detect.GetBestSize())
        # end wxGlade

    def initialize(self):
        self.device.close('window', self.name)
        self.Show()
        self.device.setting(int, "draw_mode", 0)
        self.device.setting(int, 'camera_index', 0)
        self.device.setting(int, 'camera_fps', 1)
        self.device.setting(bool, 'mouse_zoom_invert', False)
        self.device.setting(bool, 'camera_correction_fisheye', False)
        self.device.setting(bool, 'camera_correction_perspective', False)
        self.device.setting(str, 'fisheye', '')
        self.device.setting(str, 'perspective', '')
        self.check_fisheye.SetValue(self.device.camera_correction_fisheye)
        self.check_perspective.SetValue(self.device.camera_correction_perspective)
        if self.device.fisheye is not None and len(self.device.fisheye) != 0:
            self.fisheye_k, self.fisheye_d = eval(self.device.fisheye)
        if self.device.perspective is not None and len(self.device.perspective) != 0:
            self.perspective = eval(self.device.perspective)
            # print("Perspective value loaded: %s" % kernel.perspective)
        self.slider_fps.SetValue(self.device.camera_fps)

        if self.device.camera_index == 0:
            self.camera_0_menu.Check(True)
        elif self.device.camera_index == 1:
            self.camera_1_menu.Check(True)
        elif self.device.camera_index == 2:
            self.camera_2_menu.Check(True)
        elif self.device.camera_index == 3:
            self.camera_3_menu.Check(True)
        elif self.device.camera_index == 4:
            self.camera_4_menu.Check(True)
        self.device.add_job(self.init_camera, times=1, interval=0.1)
        self.device.listen("camera_frame", self.on_camera_frame)
        self.device.listen("camera_frame_raw", self.on_camera_frame_raw)
        self.device.add('control', 'camera_snapshot', self.snapshot_close)
        self.device.add('control', 'camera_update', self.update_close)

    def shutdown(self,  channel):
        self.Close()

    def on_close(self, event):
        self.camera_lock.acquire()
        self.device.unlisten("camera_frame_raw", self.on_camera_frame_raw)
        self.device.unlisten("camera_frame", self.on_camera_frame)
        self.device.signal("camera_frame_raw", None)
        self.close_camera()
        self.device.remove('window', self.name)
        event.Skip()  # Call destroy.
        self.camera_lock.release()

    def snapshot_close(self):
        self.fetch_image()
        self.on_button_export(None)
        self.Close()

    def update_close(self):
        self.fetch_image()
        self.on_button_update(None)
        self.Close()

    def on_size(self, event):
        self.Layout()
        width, height = self.ClientSize
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        self._Buffer = wx.Bitmap(width, height)
        self.update_in_gui_thread()

    def on_camera_frame(self, frame):
        if frame is None:
            return
        bed_width = self.device.bed_width * 2
        bed_height = self.device.bed_height * 2

        self.image_height, self.image_width = frame.shape[:2]
        self.frame_bitmap = wx.Bitmap.FromBuffer(self.image_width, self.image_height, frame)

        if self.check_perspective.GetValue():
            if bed_width != self.image_width or bed_height != self.image_height:
                self.image_width = bed_width
                self.image_height = bed_height
                self.display_camera.SetSize((self.image_width, self.image_height))
        self.update_in_gui_thread()

    def on_camera_frame_raw(self, frame):
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
        self.device.fisheye = repr([K.tolist(), D.tolist()])
        self.fisheye_k = K.tolist()
        self.fisheye_d = D.tolist()

    def swap_camera(self, camera_index=0):
        self.camera_lock.acquire()
        self.device.camera_index = camera_index
        self.close_camera()
        self.device.add_job(self.init_camera, times=1, interval=0.1)
        self.camera_lock.release()

    def close_camera(self):
        self.unschedule()
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def camera_error_requirement(self):
        try:
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(False)
            dlg = wx.MessageDialog(None, _(
                "If using a precompiled binary, this was requirement was not included.\nIf using pure Python, add it with: pip install opencv-python-headless"),
                                   _("Interface Requires OpenCV."), wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
        except RuntimeError:
            pass

    def camera_error_webcam(self):
        try:
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(False)
            dlg = wx.MessageDialog(None, _("No Webcam found."),
                                   _("Error"), wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
        except RuntimeError:
            pass

    def camera_success(self):
        try:
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(True)
        except RuntimeError:
            pass

    def init_camera(self):
        if self.capture is not None:
            self.capture = None
        try:
            import cv2
        except ImportError:
            wx.CallAfter(self.camera_error_requirement)
            return
        self.capture = cv2.VideoCapture(self.device.camera_index)
        wx.CallAfter(self.camera_success)
        try:
            self.interval = 1.0 / self.device.camera_fps
        except ZeroDivisionError:
            self.interval = 5
        except AttributeError:
            return
        self.schedule()

    def reset_perspective(self, event):
        self.perspective = None
        self.device.perspective = ''

    def reset_fisheye(self, event):
        self.fisheye_k = None
        self.fisheye_d = None
        self.device.fisheye = ''

    def on_erase(self, event):
        pass

    def on_paint(self, event):
        try:
            wx.BufferedPaintDC(self.display_camera, self._Buffer)
        except RuntimeError:
            pass

    def on_update_buffer(self, event=None):
        if self.frame_bitmap is None:
            return  # Need the bitmap to refresh.
        dm = self.device.draw_mode
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        dc.Clear()
        w, h = dc.Size
        if dm & 0x800000 != 0:
            dc.SetUserScale(-1, -1)
            dc.SetLogicalOrigin(w, h)
        dc.SetBackground(wx.WHITE_BRUSH)
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(self.matrix)))
        gc.PushState()
        gc.DrawBitmap(self.frame_bitmap, 0, 0, self.image_width, self.image_height)
        if not self.device.camera_correction_perspective:
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
        if dm & 0x400000 != 0:
            dc.Blit(0, 0, w, h, dc, 0, 0, wx.SRC_INVERT)
        gc.Destroy()
        del dc

    def convert_scene_to_window(self, position):
        point = self.matrix.point_in_matrix_space(position)
        return point[0], point[1]

    def convert_window_to_scene(self, position):
        point = self.matrix.point_in_inverse_space(position)
        return point[0], point[1]

    def on_mouse_move(self, event):
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
            self.device.perspective = repr(self.perspective)
        self.previous_window_position = window_position
        self.previous_scene_position = scene_position

    def on_mousewheel(self, event):
        rotation = event.GetWheelRotation()
        mouse = event.GetPosition()
        if self.device.device_root.mouse_zoom_invert:
            rotation = -rotation
        if rotation > 1:
            self.scene_post_scale(1.1, 1.1, mouse[0], mouse[1])
        elif rotation < -1:
            self.scene_post_scale(0.9, 0.9, mouse[0], mouse[1])

    def on_mouse_left_down(self, event):
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
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        self.previous_window_position = None
        self.previous_scene_position = None
        self.corner_drag = None

    def on_mouse_middle_down(self, event):
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.previous_window_position = event.GetPosition()
        self.previous_scene_position = self.convert_window_to_scene(self.previous_window_position)

    def on_mouse_middle_up(self, event):
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        self.previous_window_position = None
        self.previous_scene_position = None

    def scene_post_pan(self, px, py):
        self.matrix.post_translate(px, py)
        self.on_update_buffer()

    def scene_post_scale(self, sx, sy=None, ax=0, ay=0):
        self.matrix.post_scale(sx, sy, ax, ay)
        self.on_update_buffer()

    def fetch_image(self, raw=False):
        if self.device is None or self.capture is None:
            return
        try:
            import cv2
        except ImportError:
            return
        if self.capture is None:
            return
        self.camera_lock.acquire()
        if self.device is None:
            self.camera_lock.release()
            return
        ret, frame = self.capture.read()
        if not ret or frame is None:
            wx.CallAfter(self.camera_error_webcam)
            self.capture = None
            self.camera_lock.release()
            return
        if not raw and \
                self.fisheye_k is not None and \
                self.fisheye_d is not None and \
                self.device is not None and \
                self.device.camera_correction_fisheye:
            # Unfisheye the drawing
            import numpy as np
            K = np.array(self.fisheye_k)
            D = np.array(self.fisheye_d)
            DIM = frame.shape[:2][::-1]
            map1, map2 = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), K, DIM, cv2.CV_16SC2)
            frame = cv2.remap(frame, map1, map2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        if not raw and self.device is not None and self.device.camera_correction_perspective:
            bed_width = self.device.bed_width * 2
            bed_height = self.device.bed_height * 2
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
        if raw:
            self.device.signal("camera_frame_raw", frame)
        else:
            self.device.signal("camera_frame", frame)
        self.camera_lock.release()
        return frame

    def update_in_gui_thread(self):
        if self.device is None:
            return
        self.on_update_buffer()
        self.Refresh(True)
        self.Update()

    def on_check_perspective(self, event):
        self.device.camera_correction_perspective = self.check_perspective.GetValue()

    def on_check_fisheye(self, event):
        self.device.camera_correction_fisheye = self.check_fisheye.GetValue()

    def on_button_update(self, event):  # wxGlade: CameraInterface.<event_handler>
        frame = self.device.last_signal("camera_frame")
        if frame is not None:
            frame = frame[0]
            buffer = wx.Bitmap.FromBuffer(self.image_width, self.image_height, frame)
            self.device.signal("background", buffer)

    def on_button_export(self, event):  # wxGlade: CameraInterface.<event_handler>
        frame = self.device.last_signal("camera_frame")
        if frame is not None:
            frame = frame[0]
            from PIL import Image
            img = Image.fromarray(frame)
            obj = SVGImage()
            obj.image = img
            obj.image_width = self.image_width
            obj.image_height = self.image_height
            self.device.device_root.elements.append(obj)
            self.device.signal('refresh_elements', 0)
            self.device.signal('rebuild_tree', 0)

    def on_slider_fps(self, event):  # wxGlade: CameraInterface.<event_handler>
        fps = self.slider_fps.GetValue()
        if fps == 0:
            tick = 5
        else:
            tick = 1.0 / fps
        self.device.camera_fps = fps
        self.interval = tick

    def on_button_detect(self, event):  # wxGlade: CameraInterface.<event_handler>
        self.device.add_job(self.fetch_image, args=True, times=1, interval=0)
