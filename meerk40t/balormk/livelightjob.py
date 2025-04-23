"""
Live Full Light Job

This light job is full live because it syncs with the elements to run the current elements. The lighting can change
when the elements change. It will show the updated job.

This job works as a spoolerjob. Implementing all the regular calls for being a spooled job.
"""

import threading
import time
from math import isinf

import numpy as np

from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_PIXEL, Length
from meerk40t.kernel.jobs import Job
from meerk40t.svgelements import Matrix
from meerk40t.tools.geomstr import Geomstr


class LiveLightJob:
    def __init__(
        self,
        service,
        mode="full",
        geometry=None,
        travel_speed=None,
        jump_delay=None,
        quantization=100,
        listen=True,
        raw=False,
    ):
        self.service = service
        self.quantization = quantization
        self.mode = mode
        self.listen = listen
        self.raw = raw
        self._geometry = geometry
        self._travel_speed = travel_speed
        self._jump_delay = jump_delay

        # Kernel Job definition
        self.redlight_lock = threading.RLock()
        self.redlight_job = Job(
            self.jobevent,
            interval=0.1,
            job_name=f"redlight_{self.mode}_{time.perf_counter():3f}",
            run_main=False,
        )

        # Spooler-Job mirroring
        self.stopped = False
        self.started = False
        self.priority = -1
        self.time_submitted = time.time()
        self.time_started = time.time()
        self.runtime = 0

        # Update logic
        self._connection = None
        self.update_method = None
        self.changed = False
        self.points = None
        self.bounded = False

        methods = {
            "full": ("Full Light Job", self.update_full),
            "hull": ("Hull Light Job", self.update_hull),
            "bounds": ("Selection Light job", self.update_bounds),
            "crosshair": ("Simple Crosshairs", self.update_crosshair),
            "geometry": ("Element Light Job", self.update_geometry),
        }
        if self.mode not in methods:
            raise ValueError("Invalid mode.")
        self.label, self.update_method = methods[self.mode]
        if self.listen:
            self.label = f"Live {self.label}"

        # Caching of geometry to be drawn
        self.changed = True
        self._last_bounds = None
        self.source = "elements"

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

    def set_travel_speed(self, update_speed):
        self._travel_speed = update_speed

    def execute(self, driver):
        """
        Spooler job execute.

        @param driver: driver-like object
        @return:
        """
        if self.stopped:
            return True
        self.pre_job(driver)
        while not self.stopped:
            time.sleep(0.05)
        self.post_job(driver)
        return True

    def jobevent(self):
        def init_red(con):
            con.abort()
            first_x, first_y = con.get_last_xy()
            con.light_off()
            con.write_port()
            con.goto_xy(first_x, first_y, distance=0xFFFF)
            if self._travel_speed is not None:
                con._light_speed = self._travel_speed
                con._dark_speed = self._travel_speed
                con._goto_speed = self._travel_speed
            else:
                con._light_speed = self.service.redlight_speed
                con._dark_speed = self.service.redlight_speed
                con._goto_speed = self.service.redlight_speed
            con.light_mode()

        if self.stopped or self._connection is None:
            return
        con = self._connection
        if self.changed:
            # print ("Something changed")
            with self.redlight_lock:
                if self.update_method is not None:
                    self.update_method()
                # print (f"We are having now {len(self.points)} points")
                self.changed = False
            init_red(con)

        # Now draw the stuff
        self.trace_redlight(con)

    def trace_redlight(self, con):
        # Calls light based on the set mode.
        con.light_mode()
        delay_dark = self.service.delay_jump_long
        delay_between = self.service.delay_jump_short
        move = True
        for i, e in enumerate(self.points):
            if self.stopped or self.changed:
                # Abort due to stoppage or change, no sense to continue
                return
            if e is None:
                move = True
                continue
            x, y = e.real, e.imag
            if np.isnan(x) or np.isnan(y):
                move = True
                continue
            x = int(x)
            y = int(y)
            if x < 0 or x > 0xFFFF or y < 0 or y > 0xFFFF:
                # Our bounds are not in frame.
                if self.bounded:
                    # We required them in frame.
                    continue
                # Fix them.
                x &= 0xFFFF
                y &= 0xFFFF
            if move:
                con.dark(x, y, long=delay_dark, short=delay_dark)
                move = False
                continue
            con.light(x, y, long=delay_between, short=delay_between)
        con.light_off()
        con.write_port()

    def setup_listen(self, start):
        if not self.listen:
            return
        for method in ("emphasized", "modified_by_tool", "updating", "view;realized"):
            if start:
                self.service.listen(method, self.on_emphasis_changed)
            else:
                self.service.unlisten(method, self.on_emphasis_changed)

    def pre_job(self, driver):
        self.setup_listen(True)
        self.time_started = time.time()
        self.started = True
        self._connection = driver.connection
        self._connection.rapid_mode()
        self._connection.light_mode()
        self.update()
        self.service.kernel.schedule(self.redlight_job)

    def post_job(self, driver):
        self.stopped = True
        self.runtime += time.time() - self.time_started
        self.redlight_job.cancel()
        self.service.kernel.unschedule(self.redlight_job)
        self.setup_listen(False)
        if self._connection is not None:
            self._connection.abort()
            if self.service.redlight_preferred:
                self._connection.light_on()
            else:
                self._connection.light_off()
            self._connection.write_port()
            self._connection = None
            self.service.signal("light_simulate", False)

    def update(self):
        with self.redlight_lock:
            self.changed = True

    def on_emphasis_changed(self, *args):
        """
        During execute the emphasis signal will call this function.
        """
        self.update()

    def update_crosshair(self):
        margin = 5000
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
        self.prepare_redlight_point(geometry, False, "crosshair")

    def update_geometry(self):
        if self._geometry is None:
            self.update_crosshair()
            return
        geometry = Geomstr(self._geometry)
        self.prepare_redlight_point(geometry, not self.raw, "geometry")

    def update_bounds(self):
        elems = self._gather_source()
        if len(elems) == 0:
            self.update_crosshair()
            return
        bounds = Node.union_bounds(elems)
        if bounds is None or isinf(bounds[0]):
            self.update_crosshair()
            return
        xmin, ymin, xmax, ymax = bounds
        geometry = Geomstr.lines(
            (xmin, ymin),
            (xmax, ymin),
            (xmax, ymax),
            (xmin, ymax),
            (xmin, ymin),
        )
        self.prepare_redlight_point(geometry, True, "bounds")

    def update_hull(self):
        def create_hull(elemlist):
            geometry = Geomstr()
            for node in elemlist:
                try:
                    e = None
                    if hasattr(node, "convex_hull"):
                        e = node.convex_hull()
                    if e is None:
                        e = node.as_geometry()
                except AttributeError:
                    continue
                geometry.append(e)
            # Convert to hull.
            return Geomstr.hull(geometry, distance=500)

        elems = self._gather_source()
        if len(elems) == 0:
            self.update_crosshair()
            return
        geometry = create_hull(elems)
        self.prepare_redlight_point(geometry, True, "hull")

    def update_full(self):
        def create_full(elemlist):
            geometry = Geomstr()
            for node in elemlist:
                try:
                    e = None
                    if e is None and hasattr(node, "convex_hull"):
                        e = node.convex_hull()
                    if e is None and hasattr(node, "as_geometry"):
                        e = node.as_geometry()
                    if e is None and hasattr(node, "bounds"):
                        nx, ny, mx, my = node.bounds
                        e = Geomstr.rect(nx, ny, mx - nx, my - ny)
                except AttributeError:
                    continue
                geometry.append(e)
            return geometry

        elems = self._gather_source()
        if len(elems) == 0:
            self.update_crosshair()
            return
        geometry = create_full(elems)
        self.prepare_redlight_point(geometry, True, "full")

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

    def prepare_redlight_point(self, draw_geometry, adjust, source):
        # Create independent copy
        # draw_geometry.debug_me()
        geometry = Geomstr(draw_geometry)
        # print (f"Entered with {geometry.bbox()} ({geometry.index} segments [{source}])")
        if adjust:
            geometry.transform(self.service.view.matrix)
            # print (f"Adjusted to {geometry.bbox()}")
        rotate = self._redlight_adjust_matrix()
        geometry.transform(rotate)
        self.points = list(
            geometry.as_equal_interpolated_points(
                distance=self.quantization, expand_lines=True
            )
        )
        # print (f"Interpolation delivered: {len(self.points)} segments")

    # def process(self, con):
    #     """
    #     Called repeatedly by `execute()`
    #     @param con:
    #     @return:
    #     """
    #     if self.stopped:
    #         return False
    #     if self.changed:
    #         self.changed = False
    #         if self.update_method is not None:
    #             self.update_method()
    #         con.abort()
    #         first_x, first_y = con.get_last_xy()
    #         con.light_off()
    #         con.write_port()
    #         con.goto_xy(first_x, first_y, distance=0xFFFF)
    #         con.light_mode()

    #     self.trace_redlight(con)
    #     return True

    def _gather_source(self):
        self.source = "elements"
        elements = list(self.service.elements.elems(emphasized=True))
        if not elements:
            elements = list(self.service.elements.regmarks(emphasized=True))
            self.source = "regmarks"
        # if not elements:
        #     elements = list(self.service.elements.elems())
        #     self.source = "elements"
        return elements
