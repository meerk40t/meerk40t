import time

from meerk40t.core.units import UNITS_PER_PIXEL
from meerk40t.svgelements import Matrix, Polygon, Polyline


class LiveFullLightJob:
    def __init__(
        self,
        service,
    ):
        self.service = service
        self.stopped = False
        self.started = False
        self.changed = False
        self._last_bounds = None
        self.priority = -1
        self.label = "Live Full Light Job"
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
        self.service.listen("emphasized", self.on_emphasis_changed)
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
        self.service.unlisten("emphasized", self.on_emphasis_changed)
        self.service.signal("stop_tracing", True)
        return True

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

    def on_emphasis_changed(self, *args):
        self.changed = True

    def crosshairs(self, con):
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

        jump_delay = self.service.delay_jump_long
        dark_delay = self.service.delay_jump_short
        for pt in points:
            if self.stopped:
                return False
            con.light(*pt, long=jump_delay, short=dark_delay)
        return True

    def process(self, con):
        if self.stopped:
            return False
        bounds = self.service.elements.selected_area()
        if self._last_bounds is not None and bounds != self._last_bounds:
            # Emphasis did not change but the bounds did. We dragged something.
            self.changed = True
        self._last_bounds = bounds

        if self.changed:
            self.changed = False
            con.abort()
            first_x = 0x8000
            first_y = 0x8000
            con.goto_xy(first_x, first_y, distance=0xFFFF)
            con.light_mode()
        jump_delay = self.service.delay_jump_long
        dark_delay = self.service.delay_jump_short

        con._light_speed = self.service.redlight_speed
        con._dark_speed = self.service.redlight_speed
        con._goto_speed = self.service.redlight_speed
        con.light_mode()

        elements = list(self.service.elements.elems(emphasized=True))

        if not elements:
            return self.crosshairs(con)

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
        quantization = 50
        rotate = Matrix()
        rotate.post_rotate(self.service.redlight_angle.radians, 0x8000, 0x8000)
        rotate.post_translate(x_offset, y_offset)

        def mx_rotate(pt):
            if pt is None:
                return None
            return (
                pt[0] * rotate.a + pt[1] * rotate.c + 1 * rotate.e,
                pt[0] * rotate.b + pt[1] * rotate.d + 1 * rotate.f,
            )

        for node in elements:
            if self.stopped:
                return False
            if self.changed:
                return True
            try:
                e = node.as_path()
            except AttributeError:
                continue
            if not e:
                continue
            x, y = e.point(0)
            x, y = self.service.scene_to_device_position(x, y)
            x, y = mx_rotate((x, y))
            x = int(x) & 0xFFFF
            y = int(y) & 0xFFFF
            if isinstance(e, (Polygon, Polyline)):
                con.dark(x, y, long=jump_delay, short=jump_delay)
                for pt in e:
                    if self.stopped:
                        return False
                    if self.changed:
                        return True
                    x, y = self.service.scene_to_device_position(*pt)
                    x, y = mx_rotate((x, y))
                    x = int(x) & 0xFFFF
                    y = int(y) & 0xFFFF
                    con.light(x, y, long=dark_delay, short=dark_delay)
                continue

            con.dark(x, y, long=jump_delay, short=jump_delay)
            for i in range(1, quantization + 1):
                if self.stopped:
                    return False
                if self.changed:
                    return True
                x, y = e.point(i / float(quantization))
                x, y = self.service.scene_to_device_position(x, y)
                x, y = mx_rotate((x, y))
                x = int(x) & 0xFFFF
                y = int(y) & 0xFFFF
                con.light(x, y, long=dark_delay, short=dark_delay)
        if con.light_off():
            con.list_write_port()
        return True
