"""
LaserJob is the basic Spooler Job. It stores a list of items that are merely called in order on the driver. Between
each call a cycle is returned with False until the processing is finished and True is returned.

The LaserJob itself permits looping. This will send the list of items that many times until the job is completed.
This could be an infinite number of times.
"""


import time
from math import isinf

from meerk40t.core.cutcode.cutcode import CutCode


class LaserJob:
    def __init__(self, label, items, driver=None, priority=0, loops=1, outline=None):
        self.items = items
        self.label = label
        self.priority = priority
        self.time_submitted = time.time()
        self.time_started = None
        self.runtime = 0
        self.time_pass_started = None
        self.steps_done = 0
        self.steps_total = 0
        self.avg_time_per_pass = None
        self.loops = loops
        self.loops_executed = 0
        self._driver = driver
        self.helper = False
        self.item_index = 0

        self._stopped = True

        self._estimate = 0

        for item in self.items:
            if isinstance(item, CutCode):
                time_travel = item.duration_travel()
                time_cuts = item.duration_cut()
                time_extra = item.extra_time()
                self._estimate += time_travel + time_cuts + time_extra
        self.outline = outline

    def __str__(self):
        return f"{self.__class__.__name__}({self.label}: {self.loops_executed}/{self.loops})"

    def bounds(self):
        if self.outline is None:
            return None
        max_x = float("-inf")
        max_y = float("-inf")
        min_x = float("inf")
        min_y = float("inf")
        for x, y in self.outline:
            if x > max_x:
                max_x = x
            if y > max_y:
                max_y = y
            if x < min_x:
                min_x = x
            if y < min_y:
                min_y = y
        return min_x, min_y, max_x, max_y

    @property
    def status(self):
        if self.is_running and self.time_started is not None:
            return "Running"
        elif not self.is_running:
            return "Disabled"
        else:
            return "Queued"

    def is_running(self):
        return not self._stopped

    def execute(self, driver=None):
        """
        Execute calls each item in the list of items in order. This is intended to be called by the spooler thread. And
        hold the spooler while these items are executing.
        @return:
        """
        self._stopped = False
        self.time_started = time.time()
        self.time_pass_started = time.time()
        self.steps_total = 0
        self.calc_steps()
        try:
            while self.loops_executed < self.loops:
                self.steps_done = 0
                if self._stopped:
                    return False
                while self.item_index < len(self.items):
                    if self._stopped:
                        return False
                    item = self.items[self.item_index]
                    self.execute_item(item)
                    if self._stopped:
                        return False
                    self.item_index += 1
                self.item_index = 0
                self.loops_executed += 1
                self.time_pass_started = time.time()
                self.avg_time_per_pass = self.elapsed_time() / self.loops_executed
        finally:
            self.runtime += time.time() - self.time_started
            self._stopped = True
        return True

    def calc_steps(self):
        def simple_step(item):
            if isinstance(item, tuple):
                attr = item[0]
                if hasattr(self._driver, attr):
                    self.steps_total += 1
            # STRING
            elif isinstance(item, str):
                attr = item
                if hasattr(self._driver, attr):
                    self.steps_total += 1
            # .generator is a Generator
            elif hasattr(item, "generate"):
                item = getattr(item, "generate")
                for p in item():
                    simple_step(p)

        self.steps_total = 0
        for pitem in self.items:
            simple_step(pitem)

    def execute_item(self, item):
        """
        This executes the different classes of spoolable object.

        * (str, attribute, ...) calls self.driver.str(*attributes)
        * str, calls self.driver.str()
        * has_attribute(generator), recursive call to list of lines produced by the
        generator, recursive call to list of lines produced by generator

        @param item:
        @return:
        """
        if isinstance(item, tuple):
            attr = item[0]
            if hasattr(self._driver, attr):
                function = getattr(self._driver, attr)
                function(*item[1:])
                self.steps_done += 1
            return

        # STRING
        if isinstance(item, str):
            attr = item

            if hasattr(self._driver, attr):
                function = getattr(self._driver, attr)
                function()
                self.steps_done += 1
            return

        # .generator is a Generator
        if hasattr(item, "generate"):
            item = getattr(item, "generate")

        # Generator item
        for p in item():
            if self._stopped:
                return
            self.execute_item(p)

    def stop(self):
        """
        Stop this current laser-job, cannot be called from the spooler thread.
        @return:
        """
        if not self._stopped:
            self.runtime += time.time() - self.time_started
        self._stopped = True

    def elapsed_time(self):
        """
        How long is this job already running...
        """
        result = 0
        if self.is_running():
            result = time.time() - self.time_started
        else:
            result = self.runtime
        return result

    def estimate_time(self):
        """
        Give laser job time estimate.
        @return:
        """
        # This is rather 'simple', we have no clue what exactly this job is doing,
        # but we have some ideas, if and only if the job is_running:
        # a) we know the elapsed time
        # b) we know current and total steps (if the driver has such a property)
        if isinf(self.loops):
            return float("inf")
        if not self.is_running or self.time_started is None:
            return self.loops * self._estimate

        # As we have mainly disabled the driver preview, we do something simpler:
        # We know the pass of passes and, we know the steps of total steps...
        if self.avg_time_per_pass is None:
            time_for_past_passes = 0
            time_for_future_passes = (
                max(self.loops - self.loops_executed - 1, 0) * self._estimate
            )
        else:
            time_for_past_passes = self.time_pass_started - self.time_started
            time_for_future_passes = self.avg_time_per_pass * max(
                self.loops - self.loops_executed - 1, 0
            )

        time_for_current_pass = 0
        if (
            self.time_pass_started is not None
            and isinf(self.loops)
            or self.loops_executed < self.loops
        ):
            # Still running.
            this_pass_seconds = time.time() - self.time_pass_started
            if this_pass_seconds >= 5:
                time_for_current_pass = max(
                    self._estimate,
                    this_pass_seconds / max(self.steps_done, 1) * self.steps_total,
                )
            else:
                time_for_current_pass = self._estimate
        result = time_for_current_pass + time_for_past_passes + time_for_future_passes
        if result:
            return result
        # 0 means no values, nothing useful came out, so we fall back on the initial value
        return self.loops * self._estimate
