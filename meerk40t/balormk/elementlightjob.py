"""
Element Light Job

The element light job accepts elements (svg, etc.) and processes a light job based on those elements. This comes in two
forms. Simulate which does the light job at the speeds the laser job will run and light which will simply draw the given
elements.
"""
import time

from meerk40t.core.units import UNITS_PER_PIXEL
from meerk40t.svgelements import Matrix
from meerk40t.tools.geomstr import Geomstr


class ElementLightJob:
    def __init__(
        self,
        service,
        geometry,
        travel_speed=None,
        jump_delay=200.0,
        simulation_speed=None,
        quantization=500,
        simulate=True,
    ):
        self.service = service
        self.geometry = geometry
        self.started = False
        self.stopped = False
        self.travel_speed = travel_speed
        self.jump_delay = jump_delay
        self.simulation_speed = simulation_speed
        self.quantization = quantization
        self.simulate = simulate
        self.priority = -1
        self.label = "Element Light Job"
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
        return not self.stopped and self.started

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
        self.service.signal("light_simulate", False)

        if self.service.redlight_preferred:
            connection.light_on()
            connection.write_port()
        else:
            connection.light_off()
            connection.write_port()
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

    def process(self, con):
        if self.stopped:
            return False
        if not self.geometry:
            return False

        con._light_speed = self.service.redlight_speed
        con._dark_speed = self.service.redlight_speed
        con._goto_speed = self.service.redlight_speed
        con.light_mode()

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
        delay_dark = self.jump_delay

        delay_between = 8
        quantization = self.quantization
        rotate = Matrix()
        rotate.post_rotate(self.service.redlight_angle.radians, 0x8000, 0x8000)
        rotate.post_translate(x_offset, y_offset)

        geometry = Geomstr(self.geometry)

        # Move to device space.
        geometry.transform(self.service.scene_to_device_matrix())

        # Add redlight adjustments within device space.
        geometry.transform(rotate)

        points = list(self.geometry.as_interpolated_points(interpolate=quantization))
        move = True
        for i, e in enumerate(points):
            if self.stopped:
                return False
            if e is None:
                move = True
                continue
            x, y = e.real, e.imag
            x = int(x) & 0xFFFF
            y = int(y) & 0xFFFF
            if move:
                con.dark(x, y, long=delay_dark, short=delay_dark)
                move = False
                continue
            con.light(x, y, long=delay_between, short=delay_between)
        if con.light_off():
            con.list_write_port()
        return True
