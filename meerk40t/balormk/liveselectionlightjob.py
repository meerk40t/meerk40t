import time

from meerk40t.core.units import UNITS_PER_PIXEL
from meerk40t.svgelements import Matrix


class LiveSelectionLightJob:
    """
    Live Bounds Job.
    """

    def __init__(
        self,
        service,
    ):
        self.service = service
        self.stopped = False
        self.started = False
        self._current_points = None
        self._last_bounds = None
        self.priority = -1
        self.label = "Live Selection Light Job"
        self.time_submitted = time.time()
        self.time_started = time.time()
        self.runtime = 0

    @property
    def status(self):
        if self.is_running and self.time_started is not None:
            return "Running"
        elif not self.is_running:
            return "Disabled"
        else:
            return "Queued"

    def is_running(self):
        return not self.stopped

    def execute(self, driver):
        if self.stopped:
            return True
        self.time_started = time.time()
        self.started = True
        connection = driver.connection
        connection.rapid_mode()
        connection.light_mode()
        while self.process(connection):
            if self.stopped:
                break
        connection.abort()
        self.stopped = True
        self.runtime += time.time() - self.time_started
        self.service.signal("stop_tracing", True)
        return True

    def update_points(self, bounds):
        if bounds == self._last_bounds and self._current_points is not None:
            return self._current_points, False

        # Calculate rotate matrix.
        rotate = Matrix()
        rotate.post_rotate(self.service.redlight_angle.radians, 0x8000, 0x8000)
        x_offset = self.service.length(
            self.service.redlight_offset_x,
            axis=0,
            as_float=True,
            unitless=UNITS_PER_PIXEL,
        )
        y_offset = self.service.length(
            self.service.redlight_offset_y,
            axis=1,
            as_float=True,
            unitless=UNITS_PER_PIXEL,
        )
        rotate.post_translate(x_offset, y_offset)

        # Function for using rotate
        def mx_rotate(pt):
            if pt is None:
                return None
            return (
                pt[0] * rotate.a + pt[1] * rotate.c + 1 * rotate.e,
                pt[0] * rotate.b + pt[1] * rotate.d + 1 * rotate.f,
            )

        def crosshairs():
            margin = 5000
            points = [
                (0x8000, 0x8000),
                (0x8000 - margin, 0x8000),
                (0x8000, 0x8000),
                (0x8000, 0x8000 - margin),
                (0x8000, 0x8000),
                (0x8000 + margin, 0x8000),
                (0x8000, 0x8000),
                (0x8000, 0x8000 + margin),
                (0x8000, 0x8000),
            ]
            for i in range(len(points)):
                pt = points[i]
                x, y = mx_rotate(pt)
                x = int(x)
                y = int(y)
                points[i] = x, y
            return points

        if bounds is None:
            # bounds is None, default crosshair
            points = crosshairs()
        else:
            # Bounds exist
            xmin, ymin, xmax, ymax = bounds
            points = [
                (xmin, ymin),
                (xmax, ymin),
                (xmax, ymax),
                (xmin, ymax),
                (xmin, ymin),
            ]
            for i in range(len(points)):
                pt = points[i]
                x, y = self.service.scene_to_device_position(*pt)
                x, y = mx_rotate((x, y))
                x = int(x)
                y = int(y)
                if 0 <= x <= 0xFFFF and 0 <= y <= 0xFFFF:
                    points[i] = x, y
                else:
                    # Our bounds are not in frame.
                    points = crosshairs()
                    break
        self._current_points = points
        self._last_bounds = bounds
        return self._current_points, True

    def stop(self):
        self.stopped = True

    def elapsed_time(self):
        """
        How long is this job already running...
        """
        result = 0
        if self.runtime != 0:
            result = self.runtime
        else:
            if self.is_running():
                result = time.time() - self.time_started
        return result

    def estimate_time(self):
        return 0

    def process(self, con):
        if self.stopped:
            return False
        con._light_speed = self.service.redlight_speed
        con._dark_speed = self.service.redlight_speed
        con._goto_speed = self.service.redlight_speed
        con.light_mode()

        jump_delay = self.service.delay_jump_long
        dark_delay = self.service.delay_jump_short

        bounds = self.service.elements.selected_area()
        first_run = self._current_points is None
        points, update = self.update_points(bounds)
        if update and not first_run:
            con.abort()
            first_x = 0x8000
            first_y = 0x8000
            if len(points):
                first_x, first_y = points[0]
            con.goto_xy(first_x, first_y, distance=0xFFFF)
            con.light_mode()

        if self.stopped:
            return False
        for pt in points:
            if self.stopped:
                return False
            con.light(*pt, long=dark_delay, short=dark_delay)
        return True
