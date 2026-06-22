import threading
import time

import cv2
import numpy as np

from meerk40t.kernel import Service

CORNER_SIZE = 25


class Camera(Service):
    def __init__(self, kernel, camera_path, *args, **kwargs):
        Service.__init__(self, kernel, camera_path)

        self._camera_job = None

        self._current_frame = None
        self._last_frame = None

        self._current_raw = None
        self._last_raw = None

        self.capture = None
        self.image_width = -1
        self.image_height = -1

        # Used during calibration.
        self._object_points = []  # 3d point in real world space
        self._image_points = []  # 2d points in image plane.

        self.camera_lock = threading.Lock()

        self.connection_attempts = 0
        self.frame_attempts = 0
        self.frame_index = 0
        self.quit_thread = False
        self.camera_thread = None
        self.max_tries_connect = 10
        self.max_tries_frame = 10
        self.setting(str, "desc", "")
        self.setting(int, "width", 640)
        self.setting(int, "height", 480)
        self.setting(bool, "correction_fisheye", False)
        self.setting(bool, "correction_perspective", False)
        self.setting(list, "fisheye", None)
        self.setting(list, "perspective", None)
        try:
            index = int(camera_path[7:])
        except ValueError:
            index = 0
        self.setting(str, "uri", str(index))
        self.setting(int, "index", index)
        self.setting(bool, "autonormal", False)
        self.setting(bool, "aspect", False)
        self.setting(str, "preserve_aspect", "xMinYMin meet")
        self.setting(bool, "flip_x", False)
        self.setting(bool, "flip_y", False)
        self.setting(float, "align_offset_x", 0.0)
        self.setting(float, "align_offset_y", 0.0)
        self.fisheye_k = None
        self.fisheye_d = None
        if self.fisheye is not None and len(self.fisheye) != 0:
            self.fisheye_k, self.fisheye_d = self.fisheye

        try:
            self.uri = int(self.uri)  # URI is an index.
        except ValueError:
            pass

    def __repr__(self):
        return "Camera()"

    @property
    def is_virtual(self):
        try:
            i = int(self.uri)
            return False
        except ValueError:
            return True

    @property
    def is_physical(self):
        try:
            i = int(self.uri)
            return True
        except ValueError:
            return False

    def get_frame(self):
        return self._last_frame

    def get_display_frame(self):
        """Latest RGB frame for UI; prefers the current frame over last."""
        if self._current_frame is not None:
            return self._current_frame
        return self._last_frame

    def get_raw(self):
        return self._last_raw

    def shutdown(self, *args, **kwargs):
        self.close_camera()

    def fisheye_capture(self):
        """
        Raw Camera frame was requested and should be processed.

        This attempts to perform checkerboard detection.

        @return:
        """
        _ = self._
        frame = self._last_raw
        if frame is None:
            return
        CHECKERBOARD = (6, 9)
        subpix_criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1)
        calibration_flags = (
            cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC
            + cv2.fisheye.CALIB_CHECK_COND
            + cv2.fisheye.CALIB_FIX_SKEW
        )
        objp = np.zeros((1, CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
        objp[0, :, :2] = np.mgrid[0 : CHECKERBOARD[0], 0 : CHECKERBOARD[1]].T.reshape(
            -1, 2
        )

        img = frame
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Find the chess board corners
        ret, corners = cv2.findChessboardCorners(
            gray,
            CHECKERBOARD,
            cv2.CALIB_CB_ADAPTIVE_THRESH
            + cv2.CALIB_CB_FAST_CHECK
            + cv2.CALIB_CB_NORMALIZE_IMAGE,
        )
        # If found, add object points, image points (after refining them)

        if ret:
            self._object_points.append(objp)
            cv2.cornerSubPix(gray, corners, (3, 3), (-1, -1), subpix_criteria)
            self._image_points.append(corners)
        else:
            self.signal(
                "warning",
                _("Checkerboard 6x9 pattern not found."),
                _("Pattern not found."),
                4,
            )
            return
        N_OK = len(self._object_points)
        K = np.zeros((3, 3))
        D = np.zeros((4, 1))
        rvecs = [np.zeros((1, 1, 3), dtype=np.float64) for _i in range(N_OK)]
        tvecs = [np.zeros((1, 1, 3), dtype=np.float64) for _i in range(N_OK)]
        try:
            rms, a, b, c, d = cv2.fisheye.calibrate(
                self._object_points,
                self._image_points,
                gray.shape[::-1],
                K,
                D,
                rvecs,
                tvecs,
                calibration_flags,
                (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-6),
            )
        except cv2.error:
            # Ill conditioned matrix for input values.
            self.backtrack_fisheye()
            self.signal(
                "warning", _("Ill-conditioned Matrix. Keep trying."), _("Matrix."), 4
            )
            return
        self.signal(
            "warning",
            _("Success. {count} images so far.").format(count=len(self._object_points)),
            _("Image Captured"),
            4 | 2048,
        )
        self.fisheye = [K.tolist(), D.tolist()]
        self.fisheye_k = K.tolist()
        self.fisheye_d = D.tolist()

    def set_resolution(self, width, height):
        self.width = width
        self.height = height

    def get_resolution(self):
        actual_width = self.width
        actual_height = self.height
        if self.capture:
            # We have a frame, so let's get the data from there
            try:
                actual_width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            except:
                pass
        return actual_width, actual_height

    def _get_capture(self, set_resolution=True):
        import platform

        # print (self.uri, type(self.uri).__name__)
        if platform.system() == "Windows":
            self.logger("Set DSHOW for Windows")
            cv2.CAP_DSHOW
            # sets the Windows cv2 backend to DSHOW (Direct Video Input Show)
            cap = cv2.VideoCapture(self.uri)
        elif platform.system() == "Linux":
            self.logger("Set GSTREAMER for Linux")
            cv2.CAP_GSTREAMER  # set the Linux cv2 backend to GTREAMER
            # cv2.CAP_V4L
            cap = cv2.VideoCapture(self.uri)
        else:
            self.logger("Try something for Darwin")
            cap = cv2.VideoCapture(self.uri)
            # For MAC please refer to link below for I/O
            cap.set(cv2.CAP_FFMPEG, cv2.CAP_AVFOUNDATION)  # not sure!
            # please refer to reference link at bottom of page for more I/O
        if set_resolution:
            self.logger(f"Try to start camera with {self.width}x{self.height}")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.logger(
                f"Capture: {str(self.capture)}\n"
                + f"Frame resolution set to: ({cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT)})"
            )

        return cap

    def open_camera(self):
        """
        Open Camera device.

        @return:
        """
        self.quit_thread = False
        if self.uri is not None:
            t = self.camera_thread
            if t is not None:
                self.quit_thread = True  # Inform previous thread it must die, if it doesn't already know.
                t.join()  # Join previous thread, before starting new thread.
                self.quit_thread = False
            self.camera_thread = self.threaded(
                self.threaded_image_fetcher,
                thread_name=f"CameraFetcher-{self._path}-{self.uri}",
            )

    def close_camera(self):
        """
        Disconnect from the current camera.

        @return:
        """
        self.quit_thread = True

    def logger(self, msg):
        # print (msg)
        camera_user_log(self.kernel, msg)

    def guess_supported_resolutions(self):
        # List of supported resolutions
        supported_resolutions = []
        # We need to stop the camera for that
        if self.capture:
            self.close_camera()
            waiting_time = 0
            while self.quit_thread and waiting_time < 3.0:
                waiting_time += 0.1
                time.sleep(0.1)
            if self.quit_thread:
                self.logger("Camera couldn't be stopped")
                return []
        # Open the camera
        cap = self._get_capture(set_resolution=False)
        if not cap.isOpened():
            self.logger("Camera couldn't be opened")
            return []

        # There is no defnitive list of resolutions that you could
        # inquire, so we try a couple of popular combinations
        if self.is_virtual:
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            supported_resolutions.append((actual_width, actual_height, "Webcam"))
            return supported_resolutions

        for combinations in (
            (640, 480, "0.3MP 4:3"),
            (800, 600, "0.5MP 4:3"),
            (960, 544, "0.5MP 30:17"),
            (1280, 720, "0.9MP 16:9"),
            (1440, 1080, "1.5MP 16:9"),
            (1920, 1080, "2.1MP 16:9"),
            (3840, 2160, "8MP 16:9"),
            (7680, 4320, "33MP 16:9"),
        ):
            width, height, description = combinations
            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                msg = "(OK)"
            except Exception as e:
                actual_height = 0
                actual_width = 0
                msg = f"(Fail: {e})"
            self.logger(
                f"Tried {width}x{height} ({description}) - received {actual_width}x{actual_height} {msg}"
            )
            if int(actual_width) == width and int(actual_height) == height:
                supported_resolutions.append((width, height, description))
        try:
            # Might crash if the camera is not opened
            cap.release()
        except cv2.error:
            pass
        return supported_resolutions

    def nudge_align(self, dx_mm=0.0, dy_mm=0.0):
        self.align_offset_x = float(self.align_offset_x or 0.0) + float(dx_mm)
        self.align_offset_y = float(self.align_offset_y or 0.0) + float(dy_mm)

    def align_offset_scene_units(self):
        from meerk40t.core.units import Length

        return (
            float(Length(f"{float(self.align_offset_x or 0.0)}mm")),
            float(Length(f"{float(self.align_offset_y or 0.0)}mm")),
        )

    def _orient_frame(self, frame):
        if frame is None:
            return frame
        if self.flip_x and self.flip_y:
            return cv2.flip(frame, -1)
        if self.flip_x:
            return cv2.flip(frame, 1)
        if self.flip_y:
            return cv2.flip(frame, 0)
        return frame

    def _perspective_frame_size(self):
        frame = self._orient_frame(self._current_raw)
        if frame is None:
            frame = self._orient_frame(self._last_raw)
        if frame is not None:
            height, width = frame.shape[:2]
            return width, height
        if self.image_width > 0 and self.image_height > 0:
            return self.image_width, self.image_height
        return self.width, self.height

    def ensure_perspective(self):
        if self.perspective is not None:
            return
        width, height = self._perspective_frame_size()
        self.perspective = [
            [0, 0],
            [width, 0],
            [width, height],
            [0, height],
        ]

    def set_image_flip(self, flip_x=None, flip_y=None, reset_corners=True):
        changed = False
        if flip_x is not None and bool(flip_x) != bool(self.flip_x):
            self.flip_x = bool(flip_x)
            changed = True
        if flip_y is not None and bool(flip_y) != bool(self.flip_y):
            self.flip_y = bool(flip_y)
            changed = True
        if changed and reset_corners:
            self.reset_perspective()
        return changed

    def process_frame(self):
        frame = self._orient_frame(self._current_raw)
        if (
            self.fisheye_k is not None
            and self.fisheye_d is not None
            and self.correction_fisheye
        ):
            # Unfisheye the drawing
            K = np.array(self.fisheye_k)
            D = np.array(self.fisheye_d)
            DIM = frame.shape[:2][::-1]
            map1, map2 = cv2.fisheye.initUndistortRectifyMap(
                K, D, np.eye(3), K, DIM, cv2.CV_16SC2
            )
            frame = cv2.remap(
                frame,
                map1,
                map2,
                interpolation=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
            )
        width, height = frame.shape[:2][::-1]
        if width > 0 and height > 0:
            self.width = width
            self.height = height
        if self.perspective is None:
            self.perspective = [
                [0, 0],
                [width, 0],
                [width, height],
                [0, height],
            ]
        if self.correction_perspective:
            dest_width = int(self.width)
            dest_height = int(self.height)
            max_edge = 1280
            edge = max(dest_width, dest_height)
            if edge > max_edge and edge > 0:
                scale = max_edge / float(edge)
                dest_width = max(1, int(dest_width * scale))
                dest_height = max(1, int(dest_height * scale))
            rect = np.array(
                self.perspective,
                dtype="float32",
            )
            dst = np.array(
                [
                    [0, 0],
                    [dest_width - 1, 0],
                    [dest_width - 1, dest_height - 1],
                    [0, dest_height - 1],
                ],
                dtype="float32",
            )
            M = cv2.getPerspectiveTransform(rect, dst)
            frame = cv2.warpPerspective(frame, M, (dest_width, dest_height))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if self.autonormal:
            cv2.normalize(frame, frame, 0, 255, cv2.NORM_MINMAX)
        self._last_frame = self._current_frame
        self._current_frame = frame

    def _attempt_recovery(self):
        channel = self.channel("camera")
        if self.quit_thread:
            return False
        self.connection_attempts += 1
        if self.capture is not None:
            try:
                self.capture.release()
            except cv2.error:
                pass
            self.capture = None
        self.signal("camera_reconnect")
        self.capture = self._get_capture()
        if self.capture is None:
            return False
        return True

    def _thread_looper(self, uri):
        channel = self.channel("camera")
        frame = None
        while True:
            if self.quit_thread:
                return  # Abort.
            if self.connection_attempts > self.max_tries_connect:
                return  # Too many connection attempts.
            if self.capture is None:
                return  # No capture the thread dies.
            try:
                # channel(f"Grabbing Frame: {str(uri)}")
                ret = self.capture.grab()
            except AttributeError:
                time.sleep(0.2)
                channel(f"Grab Failed, trying Reconnect: {str(uri)}")
                if self._attempt_recovery():
                    continue
                return

            for i in range(self.max_tries_frame):
                if self.quit_thread:
                    return  # Abort.
                # channel(f"Retrieving Frame: {str(uri)}")
                try:
                    ret, frame = self.capture.retrieve()
                except cv2.error:
                    ret, frame = False, None
                if not ret or frame is None:
                    channel(f"Failed Retry: {str(uri)}")
                    time.sleep(0.1)
                else:
                    break
            if not ret:  # Try auto-reconnect.
                time.sleep(0.2)
                channel(f"Frame Failed, trying Reconnect: {str(uri)}")
                if self._attempt_recovery():
                    continue  # Recovery was successful.
                return
            # channel(f"Frame Success: {str(uri)}")
            self.connection_attempts = 0

            self._last_raw = self._current_raw
            self._current_raw = frame
            self.frame_index += 1
            self.process_frame()
            # channel(f"Processing Frame: {str(uri)}")

    def threaded_image_fetcher(self):
        channel = self.channel("camera")
        uri = self.uri
        # channel(f"URI: {str(uri)}")
        if uri is None:
            channel("No camera uri.")
            return
        self.quit_thread = (
            True  # If another thread exists this will let it die gracefully.
        )

        with self.camera_lock:
            self.quit_thread = False
            self.connection_attempts = 0
            self.frame_attempts = 0
            uri = self.uri
            channel(f"Connecting {str(uri)}")
            self.signal("camera_state", 1)
            # Open the camera
            self.capture = self._get_capture()
            self._thread_looper(uri)

            if self.capture is not None:
                channel(f"Releasing Capture: {str(uri)}")
                try:
                    self.capture.release()
                except cv2.error:
                    pass
                self.capture = None
                channel(f"Released: {str(uri)}")
            if self is not None:
                self.signal("camera_state", 0)
            channel(f"Camera Thread Exiting: {str(uri)}")

    def reset_perspective(self):
        """
        Reset the perspective settings.

        @return:
        """
        self.perspective = None
        self.ensure_perspective()

    def backtrack_fisheye(self):
        if self._object_points:
            del self._object_points[-1]
            del self._image_points[-1]

    def reset_fisheye(self):
        """
        Reset the fisheye settings.

        @return:
        """
        self.fisheye_k = None
        self.fisheye_d = None
        self._object_points = []
        self._image_points = []
        self.fisheye = None

    def set_uri(self, uri):
        self.uri = uri
        try:
            self.uri = int(self.uri)  # URI is an index.
        except ValueError:
            pass

    def background(self):
        """
        Sets image background to main scene.
        @return:
        """
        frame = self.get_display_frame()
        if frame is None:
            if self.capture is None:
                camera_user_log(
                    self.kernel,
                    self._(
                        "No camera frame — camera is stopped. Click Reconnect or run: camera{index} start"
                    ).format(index=self.index),
                )
            else:
                camera_user_log(
                    self.kernel,
                    self._("No camera frame yet — wait for live video, then try again."),
                )
            return None
        frame = frame_for_wx_bitmap(frame)
        if frame is None:
            camera_user_log(
                self.kernel,
                self._("Camera frame could not be converted for the bed overlay."),
            )
            return None
        self.image_height, self.image_width = frame.shape[:2]
        bed_bitmap = make_bed_bitmap_from_frame(frame)
        if bed_bitmap is None:
            camera_user_log(
                self.kernel,
                self._("Camera frame could not be converted for the bed overlay."),
            )
            return None
        if not push_bed_background_bitmap(self.kernel, bed_bitmap):
            camera_user_log(
                self.kernel, self._("Bed overlay could not be sent to the main scene.")
            )
            return None
        return self.image_width, self.image_height, frame

    def export(self):
        """
        Sends an image to the scene as an exported object.
        """
        frame = self._last_frame
        if frame is not None:
            self.image_height, self.image_width = frame.shape[:2]
            self.signal("export-image", (self.image_width, self.image_height, frame))
            return self.image_width, self.image_height, frame
        return None


def camera_user_log(kernel, message):
    """Write camera/bed messages to the main Console (and camera log)."""
    for channel_name in ("console", "camera"):
        channel = kernel.channel(channel_name)
        if channel:
            channel(message)


def frame_for_wx_bitmap(frame):
    """Return uint8 contiguous RGB numpy array for wx.Bitmap.FromBuffer, or None."""
    if frame is None:
        return None
    arr = np.ascontiguousarray(frame)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    if arr.ndim != 3 or arr.shape[2] < 3:
        return None
    if arr.shape[2] > 3:
        arr = arr[:, :, :3]
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(arr)


def frame_to_wx_buffer(frame):
    """Return RGB byte buffer for wx.Bitmap.FromBuffer, or None."""
    arr = frame_for_wx_bitmap(frame)
    if arr is None:
        return None
    return arr.tobytes()


def make_bed_bitmap_from_frame(frame):
    """Owned wx.Bitmap for bed overlay (not tied to the camera refresh buffer)."""
    import wx

    arr = frame_for_wx_bitmap(frame)
    if arr is None:
        return None
    h, w = arr.shape[:2]
    data = arr.tobytes()
    try:
        img = wx.Image(w, h)
        img.SetData(data)
        if img.IsOk():
            bmp = wx.Bitmap(img)
            if bmp.IsOk():
                return bmp
    except (TypeError, ValueError, wx.wxAssertionError):
        pass
    try:
        bmp = wx.Bitmap(img, wx.BITMAP_SCREEN_DEPTH)
        if bmp.IsOk():
            return bmp
    except (TypeError, ValueError, wx.wxAssertionError):
        pass
    try:
        bmp = wx.Bitmap.FromBuffer(w, h, data)
        if bmp.IsOk():
            return bmp
    except (TypeError, ValueError, wx.wxAssertionError):
        pass
    return None


def _camera_service_for_index(kernel, idx):
    """Return the Camera service for camera/{idx}, or None if not instantiated."""
    path = f"camera/{idx}"
    try:
        services = kernel.services("camera") or []
    except (AttributeError, TypeError):
        services = []
    for service in services:
        if getattr(service, "path", None) == path:
            return service
    try:
        obj = kernel.get_context(path)
        if obj is not None and hasattr(obj, "align_offset_scene_units"):
            return obj
    except (AttributeError, KeyError):
        pass
    return None


def composite_bed_photo_on_device_dc(scene, dc):
    """
    Paint the bed camera photo with MemoryDC.DrawBitmap in device pixels.

    wx.GraphicsContext.DrawBitmap inside the scene layer cache is unreliable on
    Windows; this path runs after the background layer widgets are drawn.
    """
    import wx

    try:
        if not scene.has_background:
            return False
        bg = scene.active_background
        if bg is None or isinstance(bg, int):
            return False
        if not isinstance(bg, wx.Bitmap) or not bg.IsOk():
            return False
        root = scene.widget_root
        if root is None:
            return False
        matrix = root.scene_widget.matrix
        if matrix is None:
            from meerk40t.svgelements import Matrix

            matrix = Matrix()
    except AttributeError:
        return False

    context = scene.context
    try:
        vw = context.device.view
        unit_width = vw.unit_width
        unit_height = vw.unit_height
    except AttributeError:
        return False

    from meerk40t.gui.scenewidgets.bedwidget import _bed_rect

    try:
        offset_x, offset_y = camera_align_offsets_for_context(context)
    except (AttributeError, TypeError, ValueError):
        offset_x, offset_y = 0.0, 0.0
    x, y, w, h = _bed_rect(offset_x, offset_y, unit_width, unit_height)

    def to_device(px, py):
        return (
            matrix.a * px + matrix.c * py + matrix.e,
            matrix.b * px + matrix.d * py + matrix.f,
        )

    corners = (
        to_device(x, y),
        to_device(x + w, y),
        to_device(x + w, y + h),
        to_device(x, y + h),
    )
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    dev_x = min(xs)
    dev_y = min(ys)
    dev_w = max(xs) - dev_x
    dev_h = max(ys) - dev_y
    if dev_w < 1 or dev_h < 1:
        return False

    pw = max(1, int(round(dev_w)))
    ph = max(1, int(round(dev_h)))
    try:
        img = bg.ConvertToImage()
        if not img.IsOk():
            return False
        if img.GetWidth() != pw or img.GetHeight() != ph:
            scaled = img.Scale(pw, ph, wx.IMAGE_QUALITY_HIGH)
            if scaled.IsOk():
                img = scaled
        bmp = wx.Bitmap(img, wx.BITMAP_SCREEN_DEPTH)
        if not bmp.IsOk():
            bmp = wx.Bitmap(img)
        if not bmp.IsOk():
            return False
        dc.DrawBitmap(bmp, int(round(dev_x)), int(round(dev_y)), True)
        return True
    except (AttributeError, TypeError, ValueError, wx.wxAssertionError):
        return False


def _bed_bitmap_sample_rgb(bed_bitmap):
    """Return center-pixel RGB tuple for console diagnostics, or None."""
    import wx

    try:
        img = bed_bitmap.ConvertToImage()
        if not img.IsOk():
            return None
        cx = max(0, img.GetWidth() // 2)
        cy = max(0, img.GetHeight() // 2)
        return img.GetRed(cx, cy), img.GetGreen(cx, cy), img.GetBlue(cx, cy)
    except (AttributeError, TypeError, ValueError, wx.wxAssertionError):
        return None


def get_main_scene_panel(kernel):
    """Return the docked main MeerK40tScenePanel, if the GUI is up."""
    gui = getattr(kernel.root, "gui", None)
    if gui is None:
        return None
    try:
        pane_info = gui._mgr.GetPane("scene")
        window = getattr(pane_info, "window", None)
        if window is not None and hasattr(window, "widget_scene"):
            return window
    except (AttributeError, RuntimeError):
        pass
    try:
        for pane_info in gui._mgr.GetAllPanes():
            window = getattr(pane_info, "window", None)
            if window is not None and hasattr(window, "widget_scene"):
                return window
    except (AttributeError, RuntimeError):
        pass
    return None


def iter_bed_widgets(widget):
    """Yield every BedWidget under a scene widget root."""
    from meerk40t.gui.scenewidgets.bedwidget import BedWidget

    if isinstance(widget, BedWidget):
        yield widget
    try:
        children = list(widget)
    except TypeError:
        return
    for child in children:
        if child is not None:
            yield from iter_bed_widgets(child)


def _ensure_show_bed_background(context):
    from meerk40t.gui.laserrender import DRAW_MODE_BACKGROUND

    if context.draw_mode & DRAW_MODE_BACKGROUND:
        context.draw_mode &= ~DRAW_MODE_BACKGROUND
        context.signal("draw_mode", context.draw_mode)


def _apply_bed_background_to_scene(scene, bed_bitmap):
    """Set bed bitmap on scene bed widget(s) and scene background flags."""
    scene._signal_widget(scene.widget_root, "background", bed_bitmap)
    for bed in iter_bed_widgets(scene.widget_root):
        bed.background = bed_bitmap
    if bed_bitmap is None:
        scene.has_background = False
    elif isinstance(bed_bitmap, int):
        scene.has_background = False
    else:
        scene.has_background = True
        scene.active_background = bed_bitmap
    scene.invalidate_background()


def push_bed_background_bitmap(kernel, bed_bitmap):
    """
    Push an owned bed bitmap to the main scene bed widget.
    Also clears Hide Background draw mode and refreshes the scene.
    """
    from meerk40t.gui.laserrender import DRAW_MODE_BACKGROUND

    if bed_bitmap is None or not bed_bitmap.IsOk():
        return False

    ctx = kernel.root
    panel = get_main_scene_panel(kernel)
    if panel is None:
        _ = kernel.translation
        camera_user_log(kernel, _("Bed background: main scene panel not found."))
        return False

    scene = panel.widget_scene
    for show_ctx in (ctx, scene.context, panel.context):
        try:
            _ensure_show_bed_background(show_ctx)
        except AttributeError:
            pass

    _apply_bed_background_to_scene(scene, bed_bitmap)
    ctx.signal("background", bed_bitmap)

    def _refresh():
        try:
            scene.invalidate_background()
            panel.request_refresh()
            panel.scene_panel.Refresh()
            ctx.signal("refresh_scene", "Scene")
        except (AttributeError, RuntimeError):
            pass

    import wx

    wx.CallAfter(_refresh)
    _ = kernel.translation
    bed_count = sum(1 for _ in iter_bed_widgets(scene.widget_root))
    sample = _bed_bitmap_sample_rgb(bed_bitmap)
    if sample is not None:
        camera_user_log(
            kernel,
            _("Bed photo center pixel RGB: {r}, {g}, {b}.").format(
                r=sample[0], g=sample[1], b=sample[2]
            ),
        )
    camera_user_log(
        kernel,
        _("Bed background applied ({w} x {h} px, {n} bed widget(s)).").format(
            w=bed_bitmap.GetWidth(),
            h=bed_bitmap.GetHeight(),
            n=bed_count,
        ),
    )
    return True


def camera_align_offsets_for_context(context):
    """Return (offset_x, offset_y) in scene units from the active camera service."""
    try:
        kernel = context.kernel
    except AttributeError:
        return 0.0, 0.0
    fallback = (0.0, 0.0)
    for idx in range(8):
        cam = _camera_service_for_index(kernel, idx)
        if cam is None:
            continue
        try:
            units = cam.align_offset_scene_units()
        except AttributeError:
            continue
        if idx == 0:
            fallback = units
        ox = float(getattr(cam, "align_offset_x", 0.0) or 0.0)
        oy = float(getattr(cam, "align_offset_y", 0.0) or 0.0)
        if ox != 0.0 or oy != 0.0:
            return units
    return fallback
