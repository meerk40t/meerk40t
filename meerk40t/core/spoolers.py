import time
from math import isinf
from threading import Condition

from meerk40t.core.laserjob import LaserJob
from meerk40t.core.units import Length
from meerk40t.kernel import CommandSyntaxError

"""
This module defines a set of commands that usually send a single easy command to the spooler. Basic jogging, home, 
unlock rail commands. And it provides the the spooler class which should be provided by each driver.

Spoolers process different jobs in order. A spooler job can be anything, but usually is a LaserJob which is a simple
list of commands.
"""


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
            # Do we have a filename to use as label?
            label = kernel.elements.basename

            if data is not None:
                # If plan data is in data, then we copy that and move on to next step.
                data.final()
                loops = 1
                elements = kernel.elements
                e = elements.op_branch

                if e.loop_continuous:
                    loops = float("inf")
                else:
                    if e.loop_enabled:
                        loops = e.loop_n
                spooler.laserjob(data.plan, loops=loops, label=label, outline=data.outline)
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
                    label = f"Send {op}"
                    spooler.laserjob(plan_command, label=label)
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
            "move_origin",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("move <x> <y>: move to position."),
        )
        def move_origin(channel, _, x, y, data=None, force=False, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data
            if y is None:
                raise CommandSyntaxError
            if force:
                spooler.command("move_ori", x, y)
            else:
                if spooler.is_idle:
                    spooler.command("move_ori", x, y)
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
        def move_absolute(channel, _, x, y, data=None, force=False, **kwgs):
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

        @kernel.console_argument("x", type=Length, help=_("change in x"))
        @kernel.console_argument("y", type=Length, help=_("change in y"))
        @kernel.console_command(
            "set_origin",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("set_origin <x> <y>: set origin to position"),
        )
        def set_origin(channel, _, x, y, data=None, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data
            if y is None:
                spooler.command("set_origin", None, None)
            else:
                x, y = kernel.device.physical_to_device_position(x, y)
                spooler.command("set_origin", x, y)
            return "spooler", spooler

        @kernel.console_command(
            "home",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("home the laser"),
        )
        def home(data=None, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data
            spooler.command("home")
            return "spooler", spooler

        @kernel.console_command(
            "physical_home",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("home the laser (goto endstops)"),
        )
        def physical_home(data=None, **kwgs):
            if data is None:
                data = kernel.device.spooler
            spooler = data
            spooler.command("physical_home")
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

            spooler.laserjob(
                list(home_dot_test()), label=f"Dot and Home Test", helper=True
            )
            return "spooler", spooler


class SpoolerJob:
    """
    Example of Spooler Job.

    The primary methodology of a spoolerjob is that it has an `execute` function that takes the driver as an argument
    it should then perform driver-like commands on the given driver to perform whatever actions the job should
    execute.

    The `priority` attribute is required.

    The job should be permitted to `stop()` and respond to `is_running()`, and other checks as to elapsed_time(),
    estimate_time(), and status.
    """
    def __init__(
        self,
        service,
    ):
        self.stopped = False
        self.service = service
        self.runtime = 0
        self.priority = 0

    @property
    def status(self):
        """
        Status is simply a status as to the job. This will be relayed by things that check the job status of jobs
        in the spooler.

        @return:
        """
        if self.is_running:
            return "Running"
        else:
            return "Queued"

    def execute(self, driver):
        """
        This is the primary method of the SpoolerJob. In this example we call the "home()" function.
        @param driver:
        @return:
        """
        try:
            driver.home()
        except AttributeError:
            pass

        return True

    def stop(self):
        self.stopped = True

    def is_running(self):
        return not self.stopped

    def elapsed_time(self):
        """
        How long is this job already running...
        """
        result = 0
        return result

    def estimate_time(self):
        return 0


class Spooler:
    """
    Spoolers are threaded job processors. A series of jobs is added to the spooler and these jobs are
    processed in order. The driver is checked for any holds it may have preventing new commands from being
    executed. If that isn't the case, the highest priority job is executed by calling the job's required
    `execute()` function passing the relevant driver as the one variable. The job itself is agnostic, and will
    execute whatever it wants calling the driver-like functions that may or may not exist on the driver.

    If execute() returns true then it is fully executed and will be removed. Otherwise it will be repeatedly
    called until whatever work it is doing is finished. This also means the driver itself is checked for holds
    (usually pausing or busy) each cycle.
    """

    def __init__(self, context, driver=None, **kwargs):
        self.context = context
        self.driver = driver
        self._current = None

        self._lock = Condition()
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

    def shutdown(self, *args, **kwargs):
        """
        device service is shutdown during the shutdown of the kernel or destruction of the service

        @param args:
        @param kwargs:
        @return:
        """
        self._shutdown = True
        with self._lock:
            self._lock.notify_all()

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
                try:
                    # If something is currently processing stop it.
                    self._current.stop()
                except AttributeError:
                    pass
                with self._lock:
                    self._lock.notify_all()

            self._thread = self.context.threaded(
                self.run,
                result=clear_thread,
                thread_name=f"Spooler({self.context.path})",
            )
            self._thread.stop = clear_thread

    def run(self):
        """
        Run thread for the spooler.

        The thread runs while the spooler is not shutdown. This executes in the spooler thread. It waits, while
        the queue is empty and is notified when items are added to the queue. Each job in the spooler is called
        with execute(). If the function returns True, the job is finished and removed. We then move on to the next
        spooler item. If execute() returns False the job is not finished and will be reattempted. Each spooler
        cycle checks the priority and whether there's a wait/hold for jobs at that priority level.

        @return:
        """
        while not self._shutdown:
            if self.context.kernel.is_shutdown:
                return  # Kernel shutdown spooler threads should die off.
            with self._lock:
                try:
                    program = self._queue[0]
                except IndexError:
                    # There is no work to do.
                    self._lock.wait()
                    continue
            priority = program.priority

            # Check if the driver holds work at this priority level.
            if self.driver.hold_work(priority):
                time.sleep(0.01)
                continue
            if program != self._current:
                # A different job is loaded. If it has a job_start, we call that.
                if hasattr(self.driver, "job_start"):
                    function = getattr(self.driver, "job_start")
                    function(program)
            self._current = program
            try:
                fully_executed = program.execute(self.driver)
            except ConnectionAbortedError:
                # Driver could no longer connect to where it was told to send the data.
                return
            except ConnectionRefusedError:
                # Driver connection failed but, we are not aborting the spooler thread
                if self._shutdown:
                    return
                with self._lock:
                    self._lock.wait()
                continue
            if fully_executed:
                # all work finished
                self.remove(program)

                # If we finished this work we call job_finished.
                if hasattr(self.driver, "job_finish"):
                    function = getattr(self.driver, "job_finish")
                    function(program)

    @property
    def is_idle(self):
        return len(self._queue) == 0 or self._queue[0].priority < 0

    @property
    def current(self):
        return self._current

    @property
    def queue(self):
        return self._queue

    def laserjob(self, job, priority=0, loops=1, label=None, helper=False, outline=None):
        """
        send a wrapped laser job to the spooler.
        """
        if label is None:
            label = f"{self.__class__.__name__}:{len(job)} items"
        # label = str(job)
        ljob = LaserJob(
            label, list(job), driver=self.driver, priority=priority, loops=loops, outline=outline
        )
        ljob.helper = helper
        ljob.uid = self.context.logging.uid("job")
        with self._lock:
            self._stop_lower_priority_running_jobs(priority)
            self._queue.append(ljob)
            self._queue.sort(key=lambda e: e.priority, reverse=True)
            self._lock.notify()
        self.context.signal("spooler;queue", len(self._queue))

    def command(self, *job, priority=0, helper=True, outline=None):
        ljob = LaserJob(str(job), [job], driver=self.driver, priority=priority, outline=outline)
        ljob.helper = helper
        ljob.uid = self.context.logging.uid("job")
        with self._lock:
            self._stop_lower_priority_running_jobs(priority)
            self._queue.append(ljob)
            self._queue.sort(key=lambda e: e.priority, reverse=True)
            self._lock.notify()
        self.context.signal("spooler;queue", len(self._queue))

    def send(self, job, prevent_duplicate=False):
        """
        Send a job to the spooler queue

        @param job: job to send to the spooler.
        @param prevent_duplicate: prevents the same job from being added again.
        @return:
        """
        job.uid = self.context.logging.uid("job")
        with self._lock:
            if prevent_duplicate:
                for q in self._queue:
                    if q is job:
                        return
            self._stop_lower_priority_running_jobs(job.priority)
            self._queue.append(job)
            self._queue.sort(key=lambda e: e.priority, reverse=True)
            self._lock.notify()
        self.context.signal("spooler;queue", len(self._queue))

    def _stop_lower_priority_running_jobs(self, priority):
        for e in self._queue:
            if e.is_running() and e.priority < priority:
                e.stop()

    def clear_queue(self):
        with self._lock:
            for element in self._queue:
                loop = getattr(element, "loops_executed", 0)
                total = getattr(element, "loops", 0)
                if isinf(total):
                    status = "stopped"
                elif loop < total:
                    status = "stopped"
                else:
                    status = "completed"
                self.context.logging.event(
                    {
                        "uid": getattr(element, "uid"),
                        "status": status,
                        "loop": getattr(element, "loops_executed", None),
                        "total": getattr(element, "loops", None),
                        "label": getattr(element, "label", None),
                        "start_time": getattr(element, "time_started", None),
                        "duration": getattr(element, "runtime", None),
                        "device": self.context.label,
                        "important": not getattr(element, "helper", False),
                        "estimate": element.estimate_time()
                        if hasattr(element, "estimate_time")
                        else None,
                        "steps_done": getattr(element, "steps_done", None),
                        "steps_total": getattr(element, "steps_total", None),
                    }
                )
                self.context.signal("spooler;completed")
                element.stop()
            self._queue.clear()
            self._lock.notify()
        self.context.signal("spooler;queue", len(self._queue))

    def remove(self, element):
        with self._lock:
            status = "completed"
            if element.status == "running":
                element.stop()
                status = "stopped"
            self.context.logging.event(
                {
                    "uid": getattr(element, "uid"),
                    "status": status,
                    "loop": getattr(element, "loops_executed", None),
                    "total": getattr(element, "loops", None),
                    "label": getattr(element, "label", None),
                    "start_time": getattr(element, "time_started", None),
                    "duration": getattr(element, "runtime", None),
                    "device": self.context.label,
                    "important": not getattr(element, "helper", False),
                    "estimate": element.estimate_time()
                    if hasattr(element, "estimate_time")
                    else None,
                    "steps_done": getattr(element, "steps_done", None),
                    "steps_total": getattr(element, "steps_total", None),
                }
            )
            self.context.signal("spooler;completed")
            element.stop()
            for i in range(len(self._queue) - 1, -1, -1):
                e = self._queue[i]
                if e is element:
                    del self._queue[i]
            self._lock.notify()
        self.context.signal("spooler;queue", len(self._queue))
