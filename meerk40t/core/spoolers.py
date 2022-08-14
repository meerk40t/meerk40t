import time
from threading import Lock

from meerk40t.core.units import Length
from meerk40t.kernel import CommandSyntaxError
from meerk40t.core.cutcode import CutCode


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation

        @kernel.console_command(
            "spool",
            help=_("spool <command>"),
            regex=True,
            input_type=(None, "plan"),
            output_type="spooler",
        )
        def spool(command, channel, _, data=None, remainder=None, **kwgs):
            device = kernel.device

            spooler = device.spooler

            if data is not None:
                # If plan data is in data, then we copy that and move on to next step.
                loops = 1
                elements = kernel.elements
                e = elements.op_branch

                if e.loop_continuous:
                    loops = float("inf")
                else:
                    if e.loop_enabled:
                        loops = e.loop_n
                spooler.laserjob(data.plan, loops=loops)
                channel(_("Spooled Plan."))
                kernel.root.signal("plan", data.name, 6)

            if remainder is None:
                channel(_("----------"))
                channel(_("Spoolers:"))
                for d, d_name in enumerate(device.match("device", suffix=True)):
                    channel(f"{d}: {d_name}")
                channel(_("----------"))
                channel(_("Spooler on device {name}:").format(name=str(device.label)))
                for s, op_name in enumerate(spooler.queue):
                    channel(f"{s}: {op_name}")
                channel(_("----------"))
            return "spooler", spooler

        @kernel.console_argument("op", type=str, help=_("unlock, origin, home, etc"))
        @kernel.console_command(
            "send",
            help=_("send a plan-command to the spooler"),
            input_type="spooler",
            output_type="spooler",
        )
        def spooler_send(
            command, channel, _, data_type=None, op=None, data=None, **kwgs
        ):
            spooler = data
            if op is None:
                raise CommandSyntaxError
            try:
                for plan_command, command_name, suffix in kernel.find("plan", op):
                    spooler.laserjob(plan_command)
                    return data_type, spooler
            except (KeyError, IndexError):
                pass
            channel(_("No plan command found."))
            return data_type, spooler

        @kernel.console_command(
            "list",
            help=_("spool<?> list"),
            input_type="spooler",
            output_type="spooler",
        )
        def spooler_list(command, channel, _, data_type=None, data=None, **kwgs):
            spooler = data
            channel(_("----------"))
            channel(_("Spoolers:"))
            for d, d_name in enumerate(kernel.match("device", suffix=True)):
                channel(f"{d}: {d_name}")
            channel(_("----------"))
            channel(
                _("Spooler on device {name}:").format(name=str(kernel.device.label))
            )
            for s, op_name in enumerate(spooler.queue):
                channel(f"{s}: {op_name}")
            channel(_("----------"))
            return data_type, spooler

        @kernel.console_command(
            "clear",
            help=_("spooler<?> clear"),
            input_type="spooler",
            output_type="spooler",
        )
        def spooler_clear(command, channel, _, data_type=None, data=None, **kwgs):
            spooler = data
            spooler.clear_queue()
            return data_type, spooler

        @kernel.console_command(
            "+laser",
            hidden=True,
            input_type=("spooler", None),
            output_type="spooler",
            help=_("turn laser on in place"),
        )
        def plus_laser(data, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data
            spooler.command("laser_on")
            return "spooler", spooler

        @kernel.console_command(
            "-laser",
            hidden=True,
            input_type=("spooler", None),
            output_type="spooler",
            help=_("turn laser off in place"),
        )
        def minus_laser(data, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data
            spooler.command("laser_off")
            return "spooler", spooler

        @kernel.console_argument(
            "amount", type=Length, help=_("amount to move in the set direction.")
        )
        @kernel.console_command(
            ("left", "right", "up", "down"),
            input_type=("spooler", None),
            output_type="spooler",
            help=_("cmd <amount>"),
        )
        def direction(command, channel, _, data=None, amount=None, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data
            if amount is None:
                amount = Length("1mm")
            if not hasattr(spooler, "_dx"):
                spooler._dx = Length(0)
            if not hasattr(spooler, "_dy"):
                spooler._dy = Length(0)
            if command.endswith("right"):
                spooler._dx += amount
            elif command.endswith("left"):
                spooler._dx -= amount
            elif command.endswith("up"):
                spooler._dy -= amount
            elif command.endswith("down"):
                spooler._dy += amount
            kernel.console(".timer 1 0 spool jog\n")
            return "spooler", spooler

        @kernel.console_option("force", "f", type=bool, action="store_true")
        @kernel.console_command(
            "jog",
            hidden=True,
            input_type=("spooler", None),
            output_type="spooler",
            help=_("executes outstanding jog buffer"),
        )
        def jog(command, channel, _, data, force=False, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data
            try:
                idx = spooler._dx
                idy = spooler._dy
            except AttributeError:
                return
            if force:
                spooler.command("move_rel", idx, idy)
                spooler._dx = Length(0)
                spooler._dy = Length(0)
            else:
                if spooler.is_idle:
                    spooler.command("move_rel", float(idx), float(idy))
                    channel(_("Position moved: {x} {y}").format(x=idx, y=idy))
                    spooler._dx = Length(0)
                    spooler._dy = Length(0)
                else:
                    channel(_("Busy Error"))
            return "spooler", spooler

        @kernel.console_option("force", "f", type=bool, action="store_true")
        @kernel.console_argument("x", type=Length, help=_("change in x"))
        @kernel.console_argument("y", type=Length, help=_("change in y"))
        @kernel.console_command(
            ("move", "move_absolute"),
            input_type=("spooler", None),
            output_type="spooler",
            help=_("move <x> <y>: move to position."),
        )
        def move(channel, _, x, y, data=None, force=False, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data
            if y is None:
                raise CommandSyntaxError
            if force:
                spooler.command("move_abs", x, y)
            else:
                if spooler.is_idle:
                    spooler.command("move_abs", x, y)
                else:
                    channel(_("Busy Error"))
            return "spooler", spooler

        @kernel.console_option("force", "f", type=bool, action="store_true")
        @kernel.console_argument("dx", type=Length, help=_("change in x"))
        @kernel.console_argument("dy", type=Length, help=_("change in y"))
        @kernel.console_command(
            "move_relative",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("move_relative <dx> <dy>"),
        )
        def move_relative(channel, _, dx, dy, data=None, force=False, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data
            if dy is None:
                raise CommandSyntaxError
            if force:
                spooler.command("move_rel", dx, dy)
            else:
                if spooler.is_idle:
                    spooler.command("move_rel", dx, dy)
                else:
                    channel(_("Busy Error"))
            return "spooler", spooler

        @kernel.console_argument("x", type=Length, help=_("x offset"))
        @kernel.console_argument("y", type=Length, help=_("y offset"))
        @kernel.console_command(
            "home",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("home the laser"),
        )
        def home(x=None, y=None, data=None, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data
            if x is not None and y is not None:
                spooler.command("home", x, y)
                return "spooler", spooler
            spooler.command("home")
            return "spooler", spooler

        @kernel.console_command(
            "unlock",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("unlock the rail"),
        )
        def unlock(data=None, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data
            spooler.command("unlock_rail")
            return "spooler", spooler

        @kernel.console_command(
            "lock",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("lock the rail"),
        )
        def lock(data, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data
            spooler.command("lock_rail")
            return "spooler", spooler

        @kernel.console_command(
            "test_dot_and_home",
            input_type=("spooler", None),
            hidden=True,
        )
        def run_home_and_dot_test(data, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data

            def home_dot_test():
                for i in range(25):
                    yield "rapid_mode"
                    yield "home"
                    yield "laser_off"
                    yield "wait_finish"
                    yield "move_abs", "3in", "3in"
                    yield "wait_finish"
                    yield "laser_on"
                    yield "wait", 50
                    yield "laser_off"
                    yield "wait_finish"
                yield "home"
                yield "wait_finish"

            spooler.laserjob(list(home_dot_test()))
            return "spooler", spooler


class LaserJob:
    def __init__(self, label, items, driver=None, priority=0, loops=1):
        self.items = items
        self.label = label
        self.priority = priority
        self.time_submitted = time.time()
        self.time_started = None
        self.runtime = 0

        self.loops = loops
        self.loops_executed = 0

        self._driver = driver
        self.item_index = 0

        self._stopped = True

        self._estimate = 0
        MILS_IN_MM = 39.3701

        for item in self.items:
            time_cuts = 0
            time_travel = 0
            time_extra = 0
            if isinstance(item, CutCode):
                travel = item.length_travel()
                cuts = item.length_cut()
                travel /= MILS_IN_MM
                cuts /= MILS_IN_MM
                time_extra = item.extra_time()
                if item.travel_speed is not None and item.travel_speed != 0:
                    time_travel = travel / item.travel_speed
                time_cuts = item.duration_cut()
                time_total = time_travel + time_cuts + time_extra
                self._estimate += time_total

    def __str__(self):
        return f"{self.__class__.__name__}({self.label}: {self.loops_executed}/{self.loops})"

    def is_running(self):
        return not self._stopped

    def execute(self, driver):
        """
        Execute calls each item in the list of items in order. This is intended to be called by the spooler thread. And
        hold the spooler while these items are executing.
        @return:
        """
        self._stopped = False
        self.time_started = time.time()
        try:
            while self.loops_executed < self.loops:
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
        finally:
            self.runtime += time.time() - self.time_started
            self._stopped = True
        return True

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
            return

        # STRING
        if isinstance(item, str):
            attr = item

            if hasattr(self._driver, attr):
                function = getattr(self._driver, attr)
                function()
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
        self._stopped = True

    def elapsed_time(self):
        """
        How long is this job already running...
        """
        result = 0
        if self.runtime != 0:
            result = self.runtime
        else:
            if not self._stopped:
                result = time.time() - self.time_started
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
        result = 0
        if self.is_running and self.time_started is not None:
            # We fall back on elapsed and some info from the driver...
            elapsed = time.time() - self.time_started
            ratio = 1
            if hasattr(self._driver, "total_steps"):
                total = self._driver.total_steps
                current = self._driver.current_steps
                if current > 10 and total > 0:
                    # Arbitrary minimum steps (if too low, value is erratic)
                    ratio = total / current
            result = elapsed * ratio
        if result == 0:
            # Nothing useful came out, so we fall back on the initial value
            result = self._estimate

        return result


class Spooler:
    """
    Spoolers store spoolable events in a two synchronous queue, and a single idle job that
    will be executed in a loop, if the synchronous queues are empty. The two queues are the
    realtime and the regular queue.

    Spooler should be registered as a service_delegate of the device service running the driver
    to process data.

    Spoolers have threads that process and run each set of commands. Ultimately all commands are
    executed against the given driver. So if the command within the spooled element is "unicorn"
    then driver.unicorn() is called with the given arguments. This permits arbitrary execution of
    specifically spooled elements in the correct sequence.

    The two queues are the realtime and the regular queue. The realtime queue tries to execute
    particular events as soon as possible. And will execute even if there is a hold on the current
    work.

    When the queues are empty the idle job is repeatedly executed in a loop. If there is no idle job
    then the spooler is inactive.

    """

    def __init__(self, context, driver=None, **kwargs):
        self.context = context
        self.driver = driver
        self.foreground_only = True
        self._current = None

        self._lock = Lock()
        self._queue = []

        self._shutdown = False
        self._thread = None

    def __repr__(self):
        return f"Spooler({str(self.context)})"

    def __del__(self):
        self.name = None
        self._lock = None
        self._queue = None

    def __len__(self):
        return len(self._queue)

    def added(self, *args, **kwargs):
        """
        Device service is added to the kernel.

        @param args:
        @param kwargs:
        @return:
        """
        self.restart()

    def service_attach(self, *args, **kwargs):
        """
        device service is attached to the kernel.

        @param args:
        @param kwargs:
        @return:
        """
        if self.foreground_only:
            self.restart()

    def service_detach(self):
        """
        device service is detached from the kernel.

        @return:
        """
        if self.foreground_only:
            self.shutdown()

    def shutdown(self, *args, **kwargs):
        """
        device service is shutdown during the shutdown of the kernel or destruction of the service

        @param args:
        @param kwargs:
        @return:
        """
        self._shutdown = True

    def restart(self):
        """
        Start or restart the spooler thread.

        @return:
        """
        self._shutdown = False
        if self._thread is None:

            def clear_thread(*a):
                self._shutdown = True
                self._thread = None

            self._thread = self.context.threaded(
                self.run,
                result=clear_thread,
                thread_name=f"Spooler({self.context.path})",
            )
            self._thread.stop = clear_thread

    def run(self):
        """
        Run thread for the spooler.

        Process the real time queue.
        Hold work queue if driver requires a hold
        Process work queue.
        Hold idle if driver requires idle to be held.
        Process idle work

        @return:
        """
        while not self._shutdown:
            if not len(self._queue):
                # There is no work to do.
                time.sleep(0.1)
                continue

            with self._lock:
                # threadsafe
                program = self._queue[0]

            priority = program.priority

            # Check if the driver holds work at this priority level.
            if self.driver.hold_work(priority):
                time.sleep(0.01)
                continue
            self._current = program

            fully_executed = program.execute(self.driver)
            if fully_executed:
                # all work finished
                self.remove(program, 0)

    @property
    def is_idle(self):
        return len(self._queue) == 0 or self._queue[0].priority < 0

    @property
    def current(self):
        return self._current

    @property
    def queue(self):
        return self._queue

    def laserjob(self, job, priority=0, loops=1):
        """
        send a wrapped laser job to the spooler.
        """
        label = f"{self.__class__.__name__}:{len(job)} items"
        # label = str(job)
        laserjob = LaserJob(
            label, list(job), driver=self.driver, priority=priority, loops=loops
        )
        with self._lock:
            self._stop_lower_priority_running_jobs(priority)
            self._queue.append(laserjob)
            self._queue.sort(key=lambda e: e.priority, reverse=True)
        self.context.signal("spooler;queue", len(self._queue))

    def command(self, *job, priority=0):
        laserjob = LaserJob(str(job), [job], driver=self.driver, priority=priority)
        with self._lock:
            self._stop_lower_priority_running_jobs(priority)
            self._queue.append(laserjob)
            self._queue.sort(key=lambda e: e.priority, reverse=True)
        self.context.signal("spooler;queue", len(self._queue))

    def send(self, job):
        """
        Send a job to the spooler queue

        @param job: job to send to the spooler.
        @return:
        """
        with self._lock:
            self._stop_lower_priority_running_jobs(job.priority)
            self._queue.append(job)
            self._queue.sort(key=lambda e: e.priority, reverse=True)
        self.context.signal("spooler;queue", len(self._queue))

    def _stop_lower_priority_running_jobs(self, priority):
        for e in self._queue:
            if e.is_running() and e.priority < priority:
                e.stop()

    def clear_queue(self):
        with self._lock:
            for e in self._queue:
                e.stop()
            self._queue.clear()
            self.context.signal("spooler;queue", len(self._queue))

    def remove(self, element, index=None):
        info = None
        with self._lock:
            if index is None:
                try:
                    element.stop()
                    info = (
                        element.label,
                        element.time_started,
                        element.runtime,
                        self.context.label,
                    )
                except AttributeError:
                    pass
                self._queue.remove(element)
            else:
                element = self._queue[index]
                try:
                    element.stop()
                    info = (
                        element.label,
                        element.time_started,
                        element.runtime,
                        self.context.label,
                    )
                except AttributeError:
                    pass
                del self._queue[index]
        self.context.signal("spooler;completed", info)
        self.context.signal("spooler;queue", len(self._queue))
