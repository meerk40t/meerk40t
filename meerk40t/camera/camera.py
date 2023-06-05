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

    def get_frame(self):
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
        rvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
        tvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
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

    def process_frame(self):
        frame = self._current_raw
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
        if self.perspective is None:
            self.perspective = [
                [0, 0],
                [width, 0],
                [width, height],
                [0, height],
            ]
        if self.correction_perspective:
            # Perspective the drawing.
            dest_width = self.width
            dest_height = self.height
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
        uri = self.uri
        self.signal("camera_reconnect")
        self.capture = cv2.VideoCapture(uri)
        channel(f"Capture: {str(self.capture)}")
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
                channel(f"Grabbing Frame: {str(uri)}")
                ret = self.capture.grab()
            except AttributeError:
                time.sleep(0.2)
                channel(f"Grab Failed, trying Reconnect: {str(uri)}")
                if self._attempt_recovery():
                    continue
                else:
                    return

            for i in range(self.max_tries_frame):
                if self.quit_thread:
                    return  # Abort.
                channel(f"Retrieving Frame: {str(uri)}")
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
                else:
                    return
            channel(f"Frame Success: {str(uri)}")
            self.connection_attempts = 0

            self._last_raw = self._current_raw
            self._current_raw = frame
            self.frame_index += 1
            self.process_frame()
            channel(f"Processing Frame: {str(uri)}")

    def threaded_image_fetcher(self):
        channel = self.channel("camera")
        uri = self.uri
        channel(f"URI: {str(uri)}")
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
            self.capture = cv2.VideoCapture(uri)
            channel(f"Capture: {str(self.capture)}")

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
        frame = self._last_frame
        if frame is not None:
            self.image_height, self.image_width = frame.shape[:2]
            self.signal("background", (self.image_width, self.image_height, frame))
            return self.image_width, self.image_height, frame
        return None

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
