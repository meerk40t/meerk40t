"""
Live Full Light Job

This light job is full live because it syncs with the elements to run the current elements. The lighting can change
when the elements change. It will show the updated job.

This job works as a spoolerjob. Implementing all the regular calls for being a spooled job.
"""

import time

import numpy as np

from meerk40t.core.units import UNITS_PER_PIXEL
from meerk40t.svgelements import Matrix
from meerk40t.tools.geomstr import Geomstr


class LiveLightJob:
    def __init__(
        self,
        service,
        mode="full",
    ):
        self.service = service
        self.stopped = False
        self.started = False
        self.changed = False
        self._last_bounds = None
        self.priority = -1
        self.time_submitted = time.time()
        self.time_started = time.time()
        self.runtime = 0
        self.quantization = 50
        self.mode = mode
        if self.mode == "full":
            self.label = "Live Full Light Job"
            self._mode_light = self._full
        elif self.mode == "bounds":
            self.label = "Live Selection Light Job"
            self._mode_light = self._bounds
        elif self.mode == "crosshair":
            self.label = "Simple Crosshairs"
            self._mode_light = self._crosshairs
        elif self.mode == "regmarks":
            self.label = "Live Regmark Light Job"
            self._mode_light = self._regmarks
        elif self.mode == "hull":
            self.label = "Live Hull Light Job"
            self._mode_light = self._hull
        else:
            raise ValueError("Invalid mode.")

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
        """
        Spooler job execute.

        @param driver: driver-like object
        @return:
        """
        if self.stopped:
            return True
        self.service.listen("emphasized", self.on_emphasis_changed)
        self.time_started = time.time()
        self.started = True
        connection = driver.connection
        connection.rapid_mode()
        connection.light_mode()
        while self.process(connection):
            # Calls process while execute() is running.
            if self.stopped:
                break
        connection.abort()
        self.stopped = True
        self.runtime += time.time() - self.time_started
        self.service.unlisten("emphasized", self.on_emphasis_changed)
        self.service.signal("light_simulate", False)
        if self.service.redlight_preferred:
            connection.light_on()
            connection.write_port()
        else:
            connection.light_off()
            connection.write_port()
        return True

    def stop(self):
        """
        Called in order to kill the spooler-job.
        @return:
        """
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
        """
        Estimate how long this spooler job will require to complete.
        @return:
        """
        return 0

    def on_emphasis_changed(self, *args):
        """
        During execute the emphasis signal will call this function.

        @param args:
        @return:
        """
        self.changed = True

    def process(self, con):
        """
        Called repeatedly by `execute()`
        @param con:
        @return:
        """
        if self.stopped:
            return False
        bounds = self.service.elements.selected_area()
        if self._last_bounds is not None and bounds != self._last_bounds:
            # Emphasis did not change but the bounds did. We dragged something.
            self.changed = True
        self._last_bounds = bounds

        if self.changed:
            # The emphasis selection has changed.
            self.changed = False
            con.abort()
            first_x = 0x8000
            first_y = 0x8000
            con.goto_xy(first_x, first_y, distance=0xFFFF)
            con.light_mode()
        con._light_speed = self.service.redlight_speed
        con._dark_speed = self.service.redlight_speed
        con._goto_speed = self.service.redlight_speed
        con.light_mode()
        # Calls light based on the set mode.
        return self._mode_light(con)

    def _regmarks(self, con):
        """
        Mode light regmarks gets the elements for regmarks. Sends to light elements.

        @param con: connection
        @return:
        """
        elements = list(self.service.elements.regmarks())
        return self._light_elements(con, elements)

    def _full(self, con):
        """
        Mode light full gets the elements from the emphasized primary elements. Sends to light elements.
        @param con: connection
        @return:
        """
        # Full was requested.
        elements = list(self.service.elements.elems(emphasized=True))
        return self._light_elements(con, elements)

    def _hull(self, con):
        """
        Mode light hull gets the convex hull. Sends to light hull.

        @param con: connection
        @return:
        """
        elements = list(self.service.elements.elems(emphasized=True))
        return self._light_hull(con, elements)

    def _crosshairs(self, con, margin=5000):
        """
        Mode light crosshairs draws crosshairs. Sends to light geometry.

        @param con: connection
        @return:
        """
        geometry = Geomstr.lines(
            (0x8000, 0x8000),
            (0x8000 - margin, 0x8000),
            (0x8000, 0x8000),
            (0x8000, 0x8000 - margin),
            (0x8000, 0x8000),
            (0x8000 + margin, 0x8000),
            (0x8000, 0x8000),
            (0x8000, 0x8000 + margin),
            (0x8000, 0x8000),
        )
        rotate = self._redlight_adjust_matrix()
        geometry.transform(rotate)

        return self._light_geometry(con, geometry)

    def _bounds(self, con):
        """
        Light the bounds geometry. Sends to light geometry.

        @param con:
        @param bounds:
        @return:
        """
        bounds = self._last_bounds
        if not bounds:
            # If no bounds give crosshairs.
            return self._crosshairs(con)
        xmin, ymin, xmax, ymax = bounds
        geometry = Geomstr.lines(
            (xmin, ymin),
            (xmax, ymin),
            (xmax, ymax),
            (xmin, ymax),
            (xmin, ymin),
        )
        rotate = self._redlight_adjust_matrix()
        geometry.transform(self.service.scene_to_device_matrix())
        geometry.transform(rotate)
        return self._light_geometry(con, geometry, bounded=True)

    def _redlight_adjust_matrix(self):
        """
        Calculate the redlight adjustment matrix which is the product of the redlight offset values and the
        redlight rotation value.

        @return:
        """
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
        redlight_adjust_matrix = Matrix()
        redlight_adjust_matrix.post_rotate(
            self.service.redlight_angle.radians, 0x8000, 0x8000
        )
        redlight_adjust_matrix.post_translate(x_offset, y_offset)
        return redlight_adjust_matrix

    def _light_geometry(self, con, geometry, bounded=False):
        """
        Light the current geometry.

        We abort quickly if self.stopped or self.changed is set.

        @param con: connection
        @param geometry: geometry to light
        @param bounded: Require the geometry to be properly bounded.
        @return: True if we should continue, False if we should not.
        """
        delay_dark = self.service.delay_jump_long
        delay_between = self.service.delay_jump_short

        points = list(geometry.as_interpolated_points(interpolate=self.quantization))
        move = True
        for i, e in enumerate(points):
            if self.stopped:
                # Abort due to stoppage.
                return False
            if self.changed:
                # Abort due to change.
                return True
            if e is None:
                move = True
                continue
            x, y = e.real, e.imag
            if np.isnan(x) or np.isnan(y):
                move = True
                continue
            x = int(x)
            y = int(y)
            if (0 > x or x > 0xFFFF) or (0 > y or y > 0xFFFF):
                # Our bounds are not in frame.
                if bounded:
                    # We required them in frame.
                    return self._crosshairs(con)
                else:
                    # Fix them.
                    x = x & 0xFFFF
                    y = y & 0xFFFF
            if move:
                con.dark(x, y, long=delay_dark, short=delay_dark)
                move = False
                continue
            con.light(x, y, long=delay_between, short=delay_between)
        return True

    def _light_elements(self, con, elements):
        """
        Light the given elements. The elements should be a node list with `as_geometry()` objects
        @param con:
        @param elements:
        @return:
        """
        if not elements:
            # There are no elements, return a default crosshair.
            return self._crosshairs(con)

        rotate = self._redlight_adjust_matrix()
        for node in elements:
            if self.stopped:
                return False
            if self.changed:
                return True
            geometry = Geomstr(node.as_geometry())

            # Move to device space.
            geometry.transform(self.service.scene_to_device_matrix())

            # Add redlight adjustments within device space.
            geometry.transform(rotate)

            self._light_geometry(con, geometry)
        if con.light_off():
            con.list_write_port()
        return True

    def _light_hull(self, con, elements):
        """
        Light the given elements convex hull.

        @param con:
        @param elements:
        @return:
        """
        if not elements:
            # There are no elements, return a default crosshair.
            return self._crosshairs(con)

        # Convert elements to geomstr
        geometry = Geomstr()
        for node in elements:
            try:
                e = node.as_geometry()
            except AttributeError:
                continue
            geometry.append(e)

        # Convert to hull.
        hull = Geomstr.hull(geometry)
        hull.transform(self.service.scene_to_device_matrix())
        hull.transform(self._redlight_adjust_matrix())

        # Light geometry.
        return self._light_geometry(con, hull)
