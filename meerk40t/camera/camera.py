import threading
import time

try:
    import cv2
except ImportError as e:
    from ..core.exceptions import Mk40tImportAbort

    raise Mk40tImportAbort("OpenCV")

try:
    import numpy as np
except ImportError as e:
    from ..core.exceptions import Mk40tImportAbort

    raise Mk40tImportAbort("numpy")

from meerk40t.kernel import Service


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation

        kernel.register("modifier/Camera", True)

        @kernel.console_option(
            "width", "w", type=int, help="force the camera width"
        )
        @kernel.console_option(
            "height", "h", type=int, help="force the camera height"
        )
        @kernel.console_option("contrast", "c", help="Turn on AutoContrast", type=bool, action="store_true")
        @kernel.console_option("nocontrast", "C", help="Turn off AutoContrast", type=bool, action="store_true")
        @kernel.console_option("uri", "u", type=str)
        @kernel.console_command(
            "camera\d*",
            regex=True,
            help="camera commands and modifiers.",
            output_type="camera",
        )
        def camera(command, uri=None, width=None, height=None, contrast=None, nocontrast=None, **kwargs):
            if len(command) > 6:
                current_camera = command[6:]
                camera_path = "camera/%s" % current_camera
                if camera_path not in kernel.contexts:
                    kernel.add_service("camera", Camera(kernel, camera_path))
                kernel.activate_service_path("camera", camera_path)
            cam = kernel.camera
            if contrast:
                cam.autonormal = True
            if nocontrast:
                cam.autonormal = False
            if width:
                cam.width = width
            if height:
                cam.height = height
            if uri is not None:
                cam.set_uri(uri)
            return "camera", cam

        @kernel.console_option(
            "tries", "t", type=int, default=10, help="Attempts to recover connection"
        )
        @kernel.console_option(
            "frame_tries", "f", type=int, default=10, help="Attempts to fetch frame"
        )
        @kernel.console_command(
            "start", help="Start Camera.", input_type="camera", output_type="camera"
        )
        def start_camera(data=None, tries=None, frame_tries=None, **kwargs):
            if tries is not None:
                data.max_tries_connect = tries
            if frame_tries is not None:
                data.max_tries_frame = frame_tries
            data.open_camera()
            return "camera", data

        @kernel.console_command(
            "stop", help="Stop Camera", input_type="camera", output_type="camera"
        )
        def stop_camera(data=None, **kwargs):
            data.close_camera()
            return "camera", data

        @kernel.console_argument("subcommand", type=str, help="capture/reset")
        @kernel.console_command(
            "fisheye",
            help="fisheye subcommand",
            input_type="camera",
            output_type="camera",
        )
        def fisheye_camera(data=None, subcommand=None, **kwargs):
            if subcommand is None:
                raise SyntaxError
            if subcommand == "capture":
                data.fisheye_capture()
            elif subcommand == "reset":
                data.reset_fisheye()
            elif subcommand == "back":
                data.backtrack_fisheye()
            return "camera", data

        @kernel.console_argument("subcommand", type=str, help="reset/set")
        @kernel.console_argument("corner", type=int)
        @kernel.console_argument("x", type=float)
        @kernel.console_argument("y", type=float)
        @kernel.console_command(
            "perspective",
            help="perspective (set <#> <value>|reset)",
            input_type="camera",
            output_type="camera",
        )
        def perspective_camera(
            _, data=None, subcommand=None, corner=None, x=None, y=None, **kwargs
        ):
            if subcommand is None:
                raise SyntaxError
            if subcommand == "reset":
                data.reset_perspective()
                return "camera", data
            elif subcommand == "set":
                if y is None:
                    raise SyntaxError
                data.perspective[corner] = x, y
                return "camera", camera
            else:
                raise SyntaxError

        @kernel.console_command(
            "background",
            help="set background image",
            input_type="camera",
            output_type="image-array",
        )
        def background_camera(data=None, **kwargs):
            image_array = data.background()
            return "image-array", image_array

        @kernel.console_command(
            "export",
            help="export camera image",
            input_type="camera",
            output_type="image-array",
        )
        def export_camera(data=None, **kwargs):
            image_array = data.export()
            return "image-array", image_array

        @kernel.console_argument("setting", type=int)
        @kernel.console_argument("value", type=float)
        @kernel.console_command(
            "set", help="set a particular setting in the camera", input_type="camera"
        )
        def set_camera(command, _, channel, data=None, setting=None, value=None, **kwargs):
            if value is None:
                raise SyntaxError
            if data.capture is None:
                channel(_("Camera is not currently running..."))
                return
            prop = None
            for i in range(100):
                for name in dir(cv2):
                    if not name.startswith("CAP_PROP"):
                        continue
                    if getattr(cv2, name) == setting:
                        prop = name
                        break
            v0 = data.capture.get(setting)
            try:
                data.capture.set(setting, value)
            except cv2.error:
                channel(_("Attempt to change setting failed, raised cv2 error."))
                return
            v1 = data.capture.get(setting)
            channel(_("Attempt camera setting (%s) to %f. %f->%f") % (prop, value, v0, v1))

        @kernel.console_command(
            "list", help="list camera settings", input_type="camera"
        )
        def list_camera(command, _, channel, data=None, **kwargs):
            if data.capture is None:
                channel(_("Camera is not currently running..."))
                return
            for i in range(100):
                try:
                    v = data.capture.get(i)
                    prop = None
                    for name in dir(cv2):
                        if not name.startswith("CAP_PROP"):
                            continue
                        if getattr(cv2, name) == i:
                            prop = name
                            break
                    if prop is None:
                        continue
                    channel("%d: %s -- %s" % (i, str(prop), str(v)))
                except:
                    pass


CORNER_SIZE = 25


class Camera(Service):
    def __init__(self, kernel, camera_path, *args, **kwargs):
        Service.__init__(self, kernel, camera_path)
        self.uri = 0
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
        self.frame_index = 0
        self.quit_thread = False
        self.camera_thread = None
        self.max_tries_connect = 10
        self.max_tries_frame = 10
        self.setting(int, "width", 640)
        self.setting(int, "height", 480)
        self.setting(int, "fps", 1)
        self.setting(bool, "correction_fisheye", False)
        self.setting(bool, "correction_perspective", False)
        self.setting(str, "fisheye", "")
        self.setting(str, "perspective", "")
        self.setting(str, "uri", "0")
        self.setting(int, "index", 0)
        self.setting(bool, "autonormal", False)
        self.setting(bool, "aspect", False)
        self.setting(str, "preserve_aspect", "xMinYMin meet")

        # TODO: regex confirm fisheye and perspective.
        if self.fisheye is not None and len(self.fisheye) != 0:
            self.fisheye_k, self.fisheye_d = eval(self.fisheye)
        if self.perspective is not None and len(self.perspective) != 0:
            self.perspective = eval(self.perspective)
        self.uri = self.uri
        try:
            self.uri = int(self.uri)  # URI is an index.
        except ValueError:
            pass

    def __repr__(self):
        return "Camera()"

    def get_frame(self):
        return self.last_frame

    def get_raw(self):
        return self.last_raw

    def shutdown(self, *args, **kwargs):
        self.close_camera()

    def fisheye_capture(self):
        """
        Raw Camera frame was requested and should be processed.

        This attempts to perform checkerboard detection.

        :param frame:
        :return:
        """
        _ = self._
        frame = self.last_raw
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
            self.objpoints.append(objp)
            cv2.cornerSubPix(gray, corners, (3, 3), (-1, -1), subpix_criteria)
            self.imgpoints.append(corners)
        else:
            self.signal(
                "warning",
                _("Checkerboard 6x9 pattern not found."),
                _("Pattern not found."),
                4,
            )
            return
        N_OK = len(self.objpoints)
        K = np.zeros((3, 3))
        D = np.zeros((4, 1))
        rvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
        tvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
        try:
            rms, a, b, c, d = cv2.fisheye.calibrate(
                self.objpoints,
                self.imgpoints,
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
            _("Success. %d images so far.") % len(self.objpoints),
            _("Image Captured"),
            4 | 2048,
        )
        self.fisheye = repr([K.tolist(), D.tolist()])
        self.fisheye_k = K.tolist()
        self.fisheye_d = D.tolist()

    def open_camera(self):
        """
        Open Camera device.

        :param camera_index:
        :return:
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
                thread_name="CameraFetcher-%s-%s" % (self._path, self.uri),
            )

    def close_camera(self):
        """
        Disconnect from the current camera.

        :return:
        """
        self.quit_thread = True

    def process_frame(self):
        frame = self.current_raw
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
        if self.correction_perspective:
            # Perspective the drawing.
            dest_width = self.width
            dest_height = self.height
            width, height = frame.shape[:2][::-1]
            if self.perspective is None:
                rect = np.array(
                    [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
                    dtype="float32",
                )
            else:
                rect = np.array(self.perspective, dtype="float32")
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
        self.last_frame = self.current_frame
        self.current_frame = frame

    def _attempt_recovery(self):
        channel = self.channel("camera")
        if self.quit_thread:
            return False
        self.connection_attempts += 1
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        uri = self.uri
        self.signal("camera_reconnect")
        self.capture = cv2.VideoCapture(uri)
        channel("Capture: %s" % str(self.capture))
        if self.capture is None:
            return False
        return True

    def threaded_image_fetcher(self):
        channel = self.channel("camera")
        self.quit_thread = (
            True  # If another thread exists this will let it die gracefully.
        )
        with self.camera_lock:
            self.quit_thread = False
            self.connection_attempts = 0
            self.frame_attempts = 0
            uri = self.uri
            channel("URI: %s" % str(uri))
            if uri is None:
                return
            channel("Connecting %s" % str(uri))
            self.signal("camera_state", 1)
            self.capture = cv2.VideoCapture(uri)
            channel("Capture: %s" % str(self.capture))

            while not self.quit_thread:
                if self.connection_attempts > self.max_tries_connect:
                    return  # Too many connection attempts.
                if self.capture is None:
                    return  # No capture the thread dies.
                try:
                    channel("Grabbing Frame: %s" % str(uri))
                    ret = self.capture.grab()
                except AttributeError:
                    time.sleep(0.2)
                    channel("Grab Failed, trying Reconnect: %s" % str(uri))
                    if self._attempt_recovery():
                        continue
                    else:
                        return

                for i in range(self.max_tries_frame):
                    channel("Retrieving Frame: %s" % str(uri))
                    try:
                        ret, frame = self.capture.retrieve()
                    except cv2.error:
                        ret, frame = False, None
                    if not ret or frame is None:
                        channel("Failed Retry: %s" % str(uri))
                        time.sleep(0.1)
                    else:
                        break
                if not ret:  # Try auto-reconnect.
                    time.sleep(0.2)
                    channel("Frame Failed, trying Reconnect: %s" % str(uri))
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
        if self is not None:
            self.signal("camera_state", 0)
        channel("Camera Thread Exiting: %s" % str(uri))

    def reset_perspective(self):
        """
        Reset the perspective settings.

        :param event:
        :return:
        """
        self.perspective = None
        self.perspective = ""

    def backtrack_fisheye(self):
        if self.objpoints:
            del self.objpoints[-1]
            del self.imgpoints[-1]

    def reset_fisheye(self):
        """
        Reset the fisheye settings.

        :param event:
        :return:
        """
        self.fisheye_k = None
        self.fisheye_d = None
        self.objpoints = []
        self.imgpoints = []
        self.fisheye = ""

    def set_uri(self, uri):
        self.uri = uri
        self.uri = self.uri
        try:
            self.uri = int(self.uri)  # URI is an index.
        except ValueError:
            pass

    def background(self):
        """
        Sets image background to main scene.
        :param event:
        :return:
        """
        frame = self.last_frame
        if frame is not None:
            self.image_height, self.image_width = frame.shape[:2]
            self.signal("background", (self.image_width, self.image_height, frame))
            return (self.image_width, self.image_height, frame)
        return None

    def export(self):
        """
        Sends an image to the scene as an exported object.
        """
        frame = self.last_frame
        if frame is not None:
            self.image_height, self.image_width = frame.shape[:2]
            self.signal("export-image", (self.image_width, self.image_height, frame))
            return (self.image_width, self.image_height, frame)
        return None
