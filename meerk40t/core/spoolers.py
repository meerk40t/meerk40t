import time
from math import isinf
from threading import Condition

from meerk40t.core.laserjob import LaserJob
from meerk40t.core.units import Length
from meerk40t.kernel import CommandSyntaxError


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
                spooler.laserjob(data.plan, loops=loops, label=label)
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
            self._current = program
            try:
                fully_executed = program.execute(self.driver)
            except ConnectionAbortedError:
                # Driver could no longer connect to where it was told to send the data.
                with self._lock:
                    self._lock.wait()
                continue
            except ConnectionRefusedError:
                # Driver connection failed but, we are not aborting the spooler thread
                continue
            if fully_executed:
                # all work finished
                self.remove(program)

    @property
    def is_idle(self):
        return len(self._queue) == 0 or self._queue[0].priority < 0

    @property
    def current(self):
        return self._current

    @property
    def queue(self):
        return self._queue

    def laserjob(self, job, priority=0, loops=1, label=None, helper=False):
        """
        send a wrapped laser job to the spooler.
        """
        if label is None:
            label = f"{self.__class__.__name__}:{len(job)} items"
        # label = str(job)
        ljob = LaserJob(
            label, list(job), driver=self.driver, priority=priority, loops=loops
        )
        ljob.helper = helper
        with self._lock:
            self._stop_lower_priority_running_jobs(priority)
            self._queue.append(ljob)
            self._queue.sort(key=lambda e: e.priority, reverse=True)
            self._lock.notify()
        self.context.signal("spooler;queue", len(self._queue))

    def command(self, *job, priority=0, helper=True):
        laserjob = LaserJob(str(job), [job], driver=self.driver, priority=priority)
        laserjob.helper = helper
        with self._lock:
            self._stop_lower_priority_running_jobs(priority)
            self._queue.append(laserjob)
            self._queue.sort(key=lambda e: e.priority, reverse=True)
            self._lock.notify()
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
            self._lock.notify()
        self.context.signal("spooler;queue", len(self._queue))

    def _stop_lower_priority_running_jobs(self, priority):
        for e in self._queue:
            if e.is_running() and e.priority < priority:
                e.stop()

    def clear_queue(self):
        with self._lock:
            for e in self._queue:
                try:
                    status = "completed"
                    needs_signal = e.is_running() and e.time_started is not None
                    loop = e.loops_executed
                    total = e.loops
                    if isinf(total):
                        status = "stopped"
                        total = "∞"
                    elif loop < total:
                        status = "stopped"
                    passinfo = f"{loop}/{total}"
                    e.stop()
                    if needs_signal:
                        info = (
                            e.label,
                            e.time_started,
                            e.runtime,
                            self.context.label,
                            passinfo,
                            status,
                            e.helper,
                            e.estimate_time(),
                            e.steps_done,
                            e.steps_total,
                            loop,
                        )
                        self.context.signal("spooler;completed", info)
                except AttributeError:
                    pass
            self._queue.clear()
            self._lock.notify()
        self.context.signal("spooler;queue", len(self._queue))

    def remove(self, element):
        with self._lock:
            status = "completed"
            if element.status == "running":
                element.stop()
                status = "stopped"
            try:
                loop = element.loops_executed
                total = element.loops
                if isinf(element.loops):
                    status = "stopped"
                    total = "∞"
                elif loop < total:
                    status = "stopped"
                info = (
                    element.label,
                    element.time_started,
                    element.runtime,
                    self.context.label,
                    f"{loop}/{total}",
                    status,
                    element.helper,
                    element.estimate_time(),
                    element.steps_done,
                    element.steps_total,
                    loop,
                )
                self.context.signal("spooler;completed", info)
            except AttributeError:
                pass
            element.stop()
            for i in range(len(self._queue) - 1, -1, -1):
                e = self._queue[i]
                if e is element:
                    del self._queue[i]
            self._lock.notify()
        self.context.signal("spooler;queue", len(self._queue))
