"""
Live Full Light Job

This light job is full live because it syncs with the elements to run the current elements. The lighting can change
when the elements change. It will show the updated job.

This job works as a spoolerjob. Implementing all the regular calls for being a spooled job.
"""

import time
from math import isinf
from typing import Iterable
import numpy as np

from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_PIXEL, Length
from meerk40t.svgelements import Matrix
from meerk40t.tools.geomstr import Geomstr
from meerk40t.kernel.jobs import Job


class LiveLightJob:
    def __init__(
        self,
        service,
        mode="full",
        geometry=None,
        travel_speed=None,
        jump_delay=None,
        quantization=50,
        listen=True,
        raw=False,
    ):
        self.service = service
        self.connection = None
        self.root = self.service.kernel
        self.stopped: bool = False
        self.started: bool = False
        self.changed: bool = False
        self._last_bounds = None
        self.priority: int = -1
        self.time_submitted: float = time.time()
        self.time_started: float = time.time()
        self.runtime: float = 0
        self.gap_required: float = float(Length("0.1mm"))

        self.quantization = quantization
        self.mode = mode
        self.points = None
        self.source = "elements"
        self.redlight_job = None
        if self.mode == "full":
            self.label = "Live Full Light Job"
            self._mode_light = self._full
        elif self.mode == "bounds":
            self.label = "Live Selection Light Job"
            self._mode_light = self._bounds
        elif self.mode == "crosshair":
            self.label = "Simple Crosshairs"
            self._mode_light = self._crosshairs
        # elif self.mode == "regmarks":
        #     self.label = "Live Regmark Light Job"
        #     self._mode_light = self._regmarks
        elif self.mode == "hull":
            self.label = "Live Hull Light Job"
            self._mode_light = self._hull
        elif self.mode == "geometry":
            self.label = "Element Light Job"
            self._mode_light = self._static
        else:
            raise ValueError("Invalid mode.")

        self.listen = listen
        self.raw = raw
        self._geometry = geometry
        self._travel_speed = travel_speed
        self._jump_delay = jump_delay

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

    def jobhandler(self):
        print(f"Jobhandler {self.mode} on {self.source}")
        con = self.connection
        if self.stopped or con is None:
            return

        self.changed = False
        con.abort()
        first_x, first_y = con.get_last_xy()
        con.light_off()
        con.write_port()
        con.goto_xy(first_x, first_y, distance=0xFFFF)
        con.light_mode()

        if self._travel_speed is not None:
            con._light_speed = self._travel_speed
            con._dark_speed = self._travel_speed
            con._goto_speed = self._travel_speed
        else:
            con._light_speed = self.service.redlight_speed
            con._dark_speed = self.service.redlight_speed
            con._goto_speed = self.service.redlight_speed
        con.light_mode()
        # Calls light based on the set mode.
        self._mode_light(con)

    def pre_job(self):
        if self.listen:
            self.service.listen("emphasized", self.on_emphasis_changed)
            self.service.listen("modified_by_tool", self.on_emphasis_changed)
            self.service.listen("updating", self.on_emphasis_changed)
            self.service.listen("view;realized", self.on_emphasis_changed)
        if self.redlight_job is not None:
            self.root.unschedule(self.redlight_job)
        self.redlight_job = Job(
            process=self.jobhandler,
            job_name=f"balor_{self.mode}_redlight",
            interval=0.01,
            times=1,
            run_main=True,
        )
        self.time_started = time.time()
        self.started = True
        self.connection.rapid_mode()
        self.connection.light_mode()

    def post_job(self):
        if self.redlight_job is not None:
            self.root.unschedule(self.redlight_job)
        self.redlight_job = None
        self.connection.abort()
        self.stopped = True
        self.runtime += time.time() - self.time_started
        if self.listen:
            self.service.unlisten("emphasized", self.on_emphasis_changed)
            self.service.unlisten("modified_by_tool", self.on_emphasis_changed)
            self.service.unlisten("updating", self.on_emphasis_changed)
            self.service.unlisten("view;realized", self.on_emphasis_changed)
        self.service.signal("light_simulate", False)
        if self.service.redlight_preferred:
            self.connection.light_on()
        else:
            self.connection.light_off()
        self.connection.write_port()

    def execute(self, driver):
        """
        Spooler job execute.

        @param driver: driver-like object
        @return:
        """
        if self.stopped:
            return True
        self.connection = driver.connection
        self.pre_job()
        self.update()
        while not self.stopped:
            time.sleep(0.05)
        self.post_job()
        return True

    def set_travel_speed(self, update_speed):
        self._travel_speed = update_speed

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
        elif self.is_running():
            result = time.time() - self.time_started
        return result

    def estimate_time(self):
        """
        Estimate how long this spooler job will require to complete.
        @return:
        """
        return 0

    def update(self):
        self.changed = True
        self.points = None
        bounds = self.service.elements.selected_area()
        if bounds is None or isinf(bounds[0]):
            bounds = Node.union_bounds(
                list(self.service.elements.regmarks(emphasized=True))
            )
        if bounds is None or isinf(bounds[0]):
            bounds = Node.union_bounds(list(self.service.elements.elems()))
        self._last_bounds = bounds
        self.root.schedule(self.redlight_job)
        print(f"Changed [{self.mode}]")

    def on_emphasis_changed(self, *args):
        """
        During execute the emphasis signal will call this function.

        @param args:
        @return:
        """
        self.update()

    def process(self):
        """
        Called repeatedly by `execute()`
        @param con:
        @return:
        """
        if self.stopped:
            return False
        # The emphasis selection has changed.
        print(f"Run {self.mode} [{self.changed}]")
        time.sleep(0.1)
        self.jobhandler()
        return True

    # def _regmarks(self, con):
    #     """
    #     Mode light regmarks gets the elements for regmarks. Sends to light elements.

    #     @param con: connection
    #     @return:
    #     """
    #     elements = list(self.service.elements.regmarks(emphasized=True))
    #     if len(elements) == 0:
    #         elements = list(self.service.elements.regmarks())
    #     return self._light_elements(con, elements)

    def _gather_source(self):
        self.source = "elements"
        elements = list(self.service.elements.elems(emphasized=True))
        if not elements:
            elements = list(self.service.elements.regmarks(emphasized=True))
            self.source = "regmarks"
        if not elements:
            elements = list(self.service.elements.elems())
        return elements

    def _full(self, con):
        """
        Mode light full gets the elements from the emphasized primary elements. Sends to light elements.
        @param con: connection
        @return:
        """
        # Full was requested.
        elements = self._gather_source()
        return self._light_elements(con, elements)

    def _hull(self, con):
        """
        Mode light hull gets the convex hull. Sends to light hull.

        @param con: connection
        @return:
        """
        elements = self._gather_source()
        return self._light_hull(con, elements)

    def adjust_redlight(self, geometry):
        rotate = self._redlight_adjust_matrix()
        geometry.transform(rotate)

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
        self.adjust_redlight(geometry)
        return self._light_geometry(con, geometry)

    def _static(self, con):
        geometry = Geomstr(self._geometry)
        if not self.raw:
            geometry.transform(self.service.view.matrix)
        self.adjust_redlight(geometry)
        return self._light_geometry(con, geometry)

    def _bounds(self, con):
        """
        Light the bound's geometry. Sends to light geometry.

        @param con:
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
        if not self.raw:
            geometry.transform(self.service.view.matrix)
        self.adjust_redlight(geometry)
        return self._light_geometry(con, geometry, bounded=True)

    def _redlight_adjust_matrix(self):
        """
        Calculate the redlight adjustment matrix which is the product of the redlight offset values and the
        redlight rotation value.

        @return:
        """

        x_offset = float(
            Length(
                self.service.redlight_offset_x,
                relative_length=self.service.view.width,
                unitless=UNITS_PER_PIXEL,
            )
        )
        y_offset = float(
            Length(
                self.service.redlight_offset_y,
                relative_length=self.service.view.height,
                unitless=UNITS_PER_PIXEL,
            )
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

        points = list(geometry.as_equal_interpolated_points(distance=self.quantization))
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
        if con.light_off():
            con.list_write_port()
        return True

    def _light_elements(self, con, elements):
        """
        Light the given elements. The elements should be a node list with `as_geometry()` objects
        @param con:
        @param elements:
        @return:
        """
        geometry = self.build_geometry(elements, True)
        if not geometry:
            # There are no elements, return a default crosshair.
            return self._crosshairs(con)

        if self.stopped:
            return False

        if self.changed:
            return True

        # Move to device space.
        if not self.raw:
            geometry.transform(self.service.view.matrix)

        # Add redlight adjustments within device space.
        self.adjust_redlight(geometry)

        self._light_geometry(con, geometry)
        if con.light_off():
            con.list_write_port()
        return True

    def build_geometry(self, elements: Iterable, deal_with_images: bool) -> Geomstr:
        geometry = Geomstr()
        for node in elements:
            try:
                e = None
                if hasattr(node, "convex_hull"):
                    e = node.convex_hull()
                if e is None:
                    e = node.as_geometry()
                if e is None and deal_with_images and hasattr(node, "as_image"):
                    nx, ny, mx, my = node.bounds
                    e = Geomstr.rect(nx, ny, mx - nx, my - ny)

            except AttributeError:
                continue
            geometry.append(e)
        return geometry

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
        if self.points is None:
            # Convert elements to geomstr
            geometry = self.build_geometry(elements, False)

            # Convert to hull.
            hull = Geomstr.hull(geometry, distance=500)
            if not self.raw:
                hull.transform(self.service.view.matrix)
            self.adjust_redlight(hull)
            self.points = hull

        # Light geometry.
        return self._light_geometry(con, self.points)
