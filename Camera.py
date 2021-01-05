import threading
import time

import cv2
import numpy as np
import wx

from Kernel import Modifier, console_command

_ = wx.GetTranslation

CORNER_SIZE = 25


class CameraHub(Modifier):
    """
    CameraHub serves as a hub for camera interfacing. This provides support for the camera command in console as well
    as allowing for the indexing and launcing of cameras with various contexts.

    This is expected to be attached at /camera and the various camera objects are expected to be subdirectories.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self.current_camera = "0"

    def __repr__(self):
        return "CameraHub()"

    @staticmethod
    def sub_register(device):
        device.register('modifier/Camera', Camera)

    def attach(self, *a, **kwargs):
        kernel = self.context._kernel
        _ = kernel.translation

        @console_command(kernel, 'camera.*', regex=True, help="camera commands and modifiers.")
        def camera(command, *args, **kwargs):
            if len(command) > 6:
                self.current_camera = command[6:]
                self.context.signal('current_camera', self.current_camera)
            if len(args) == 0:
                yield _('Too few arguments')
                return
            camera_context = self.context.derive(self.current_camera)
            camera_context.activate('modifier/Camera')
            if args[0] == "start":
                camera_context.open_camera()
            elif args[0] == "stop":
                camera_context.close_camera()
            elif args[0] == "fisheye":
                if len(args) == 1:
                    yield _('Too few arguments')
                    return
                elif args[1] == "capture":
                    camera_context.fisheye_capture()
                elif args[1] == "reset":
                    camera_context.reset_fisheye()
            elif args[0] == "perspective":
                if len(args) <= 1:
                    yield _('Too few arguments')
                    return
                elif args[1] == "set":
                    if len(args) <= 3:
                        yield _('Too few arguments')
                        return
                    camera_context.perspective[int(args[2])] = float(args[3]), float(args[4])
                elif args[1] == "reset":
                    camera_context.reset_perspective()
            elif args[0] == "background":
                camera_context.background()
            elif args[0] == "export":
                camera_context.export()

    def detach(self, *args, **kwargs):
        pass


class Camera(Modifier):
    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self.fisheye_k = None
        self.fisheye_d = None
        self.perspective = None
        self.camera_job = None

        self.current_frame = None
        self.last_frame = None

        self.current_raw = None
        self.last_raw = None

        self.capture = None
        self.image_width = -1
        self.image_height = -1

        # Used during calibration.
        self.objpoints = []  # 3d point in real world space
        self.imgpoints = []  # 2d points in image plane.

        self.camera_lock = threading.Lock()

        self.connection_attempts = 0
        self.frame_attempts = 0
        self.last_frame_index = -1
        self.frame_index = 0
        self.quit_thread = False

    def __repr__(self):
        return "Camera()"

    def attach(self, *a, **kwargs):
        self.context.setting(int, "bed_width", 310)
        self.context.setting(int, "bed_height", 220)
        self.context.setting(int, 'fps', 1)
        self.context.setting(bool, 'correction_fisheye', False)
        self.context.setting(bool, 'correction_perspective', False)
        self.context.setting(str, 'fisheye', '')
        self.context.setting(str, 'perspective', '')
        self.context.setting(str, 'uri', '0')
        self.context.setting(int, 'index', 0)
        # TODO: regex confirm fisheye and perspective.
        if self.context.fisheye is not None and len(self.context.fisheye) != 0:
            self.fisheye_k, self.fisheye_d = eval(self.context.fisheye)
        if self.context.perspective is not None and len(self.context.perspective) != 0:
            self.perspective = eval(self.context.perspective)
        self.context.fisheye_capture = self.fisheye_capture
        self.context.open_camera = self.open_camera
        self.context.close_camera = self.close_camera
        self.context.reset_perspective = self.reset_perspective
        self.context.reset_fisheye = self.reset_fisheye
        self.context.background = self.background
        self.context.export = self.export

    def detach(self, *args, **kwargs):
        self.close_camera()

    def fisheye_capture(self):
        """
        Raw Camera frame was requested and should be processed.

        This attempts to perform checkboard detection.

        :param frame:
        :return:
        """
        frame = self.last_raw
        if frame is None:
            return
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
            self.context.get_context('/').signal("warning",
                                                 _("Checkerboard 6x9 pattern not found.",
                                                   _("Pattern not found."),
                                                   4))
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
            self.context.get_context('/').signal("warning",
                                                 _("Ill-conditioned Matrix. Keep trying."),
                                                 _("Matrix."),
                                                 4)
            return
        self.context.get_context('/').signal("warning",
                                             _("Success. %d images so far." % len(self.objpoints),
                                             _("Image Captured"),
                                             4 | 2048))
        self.context.fisheye = repr([K.tolist(), D.tolist()])
        self.fisheye_k = K.tolist()
        self.fisheye_d = D.tolist()

    def open_camera(self):
        """
        Open Camera device.

        :param camera_index:
        :return:
        """
        uri = self.context.uri
        if uri is not None:
            self.context.threaded(self.threaded_image_fetcher)

    def close_camera(self):
        """
        Disconnect from the current camera.

        :return:
        """
        self.quit_thread = True

    def process_frame(self):
        frame = self.current_raw
        if self.fisheye_k is not None and \
                self.fisheye_d is not None and \
                self.context.correction_fisheye:
            # Unfisheye the drawing
            K = np.array(self.fisheye_k)
            D = np.array(self.fisheye_d)
            DIM = frame.shape[:2][::-1]
            map1, map2 = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), K, DIM, cv2.CV_16SC2)
            frame = cv2.remap(frame, map1, map2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        if self.context.correction_perspective:
            # Perspective the drawing.
            bed_width = self.context.bed_width * 2
            bed_height = self.context.bed_height * 2
            width, height = frame.shape[:2][::-1]
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

    def _attempt_recovery(self):
        if self.quit_thread:
            return False
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        uri = self.context.uri
        self.context.signal("camera_reconnect")
        self.capture = cv2.VideoCapture(uri)
        if self.capture is None:
            return False
        self.connection_attempts += 1
        return True

    def threaded_image_fetcher(self):
        channel = self.context.channel('camera')
        self.quit_thread = True  # If another thread exists this will let it die gracefully.
        with self.camera_lock:
            self.quit_thread = False
            uri = self.context.uri
            try:
                uri = int(uri)  # URI is an index.
            except ValueError:
                pass
            channel("URI: %s" % str(uri))
            if uri is None:
                return
            channel("Connecting %s" % str(uri))
            self.context.signal("camera_state", 1)
            self.capture = cv2.VideoCapture(uri)
            channel("Capture: %s" % str(self.capture))
            while not self.quit_thread:
                if self.connection_attempts > 50:
                    return  # Too many connection attempts.
                if self.capture is None:
                    return  # No capture the thread dies.

                try:
                    channel("Grabbing Frame: %s" % str(uri))
                    ret = self.capture.grab()
                except AttributeError:
                    channel("Trying to reconnect: %s" % str(uri))
                    if self._attempt_recovery():
                        continue
                    else:
                        return

                for i in range(10):
                    channel("Retrieving Frame: %s" % str(uri))
                    ret, frame = self.capture.retrieve()
                    if not ret or frame is None:
                        channel("Failed Retry: %s" % str(uri))
                        time.sleep(0.05)
                    else:
                        break
                if not ret:  # Try auto-reconnect.
                    channel("Trying to reconnect2: %s" % str(uri))
                    if self._attempt_recovery():
                        continue
                    else:
                        return
                channel("Frame Success: %s" % str(uri))
                self.connection_attempts = 0

                self.last_raw = self.current_raw
                self.current_raw = frame
                self.frame_index += 1
                self.process_frame()
                channel("Processing Frame: %s" % str(uri))

            if self.capture is not None:
                channel("Releasing Capture: %s" % str(uri))
                self.capture.release()
                self.capture = None
                channel("Released: %s" % str(uri))
        if self.context is not None:
            self.context.signal("camera_state", 0)
        channel("Camera Thread Exiting: %s" % str(uri))

    def reset_perspective(self):
        """
        Reset the perspective settings.

        :param event:
        :return:
        """
        self.perspective = None
        self.context.perspective = ''

    def reset_fisheye(self):
        """
        Reset the fisheye settings.

        :param event:
        :return:
        """
        self.fisheye_k = None
        self.fisheye_d = None
        self.context.fisheye = ''

    def background(self):
        """
        Sets image background to main scene.
        :param event:
        :return:
        """
        frame = self.last_frame
        if frame is not None:
            root = self.context.get_context('/')
            self.image_height, self.image_width = frame.shape[:2]
            root.signal('background', (self.image_width, self.image_height, frame))

    def export(self):
        """
        Sends an image to the scene as an exported object.
        """
        frame = self.last_frame
        if frame is not None:
            root = self.context.get_context('/')
            frame = frame[0]
            root.signal('export-image', (self.image_width, self.image_height, frame))

