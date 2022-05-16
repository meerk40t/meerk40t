import time
from threading import Lock

from meerk40t.core.units import Length
from meerk40t.kernel import CommandSyntaxError


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation

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
                    spooler.job(plan_command)
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
                channel("%d: %s" % (d, d_name))
            channel(_("----------"))
            channel(_("Spooler on device %s:" % str(kernel.device.label)))
            for s, op_name in enumerate(spooler.queue):
                channel("%d: %s" % (s, op_name))
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
            spooler.job("laser_on")
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
            spooler.job("laser_off")
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
                spooler.job("move_rel", idx, idy)
                spooler._dx = Length(0)
                spooler._dy = Length(0)
            else:
                if spooler.job_if_idle("move_rel", float(idx), float(idy)):
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
                spooler.job("move_abs", x, y)
            else:
                if not spooler.job_if_idle("move_abs", x, y):
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
                spooler.job("move_rel", dx, dy)
            else:
                if not spooler.job_if_idle("move_rel", dx, dy):
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
                spooler.job("home", x, y)
                return "spooler", spooler
            spooler.job("home")
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
            spooler.job("unlock_rail")
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
            spooler.job("lock_rail")
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
                    yield "wait", 0.05
                    yield "laser_off"
                    yield "wait_finish"
                yield "home"
                yield "wait_finish"

            spooler.job(home_dot_test)
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

    * peek()
    * pop()
    * job(job)
    * jobs(iterable<job>)
    * job_if_idle(job) -- Will enqueue the job if the device is currently idle.
    * clear_queue()
    * remove(job)
    """

    def __init__(self, context, driver=None, **kwargs):
        self.context = context
        self.driver = driver
        self.foreground_only = True
        self._current = None

        self._realtime_lock = Lock()
        self._realtime_queue = []

        self._lock = Lock()
        self._queue = []

        self._idle = None

        self._shutdown = False
        self._thread = None

    def __repr__(self):
        return "Spooler(%s)" % str(self.context)

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
                thread_name="Spooler(%s)" % self.context.path,
            )
            self._thread.stop = clear_thread

    def _execute_program(self, program):
        """
        This executes the different classes of spoolable object.

        * (str, attribute, ...) calls self.driver.str(*attributes)
        * str, calls self.driver.str()
        * callable, callable()
        * has_attribute(generator), recursive call to list of lines produced by the
        generator, recursive call to list of lines produced by generator

        @param program: line to be executed.
        @return:
        """
        if self._shutdown:
            return
        # TUPLE[str, Any,...]
        if isinstance(program, tuple):
            attr = program[0]

            if hasattr(self.driver, attr):
                function = getattr(self.driver, attr)
                function(*program[1:])
            return

        # STRING
        if isinstance(program, str):
            attr = program

            if hasattr(self.driver, attr):
                function = getattr(self.driver, attr)
                function()
            return

        # .generator is a Generator
        if hasattr(program, "generate"):
            program = getattr(program, "generate")

        # GENERATOR
        for p in program():
            if self._shutdown:
                return
            self._execute_program(p)
        # print("Unspoolable object: {s}".format(s=str(program)))

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
        while True:
            # Forever Looping.
            if self._shutdown:
                # We have been told to stop.
                break
            if len(self._realtime_queue):
                # There is realtime work.
                with self._lock:
                    # threadsafe
                    program = self._realtime_queue.pop(0)
                self._current = program
                self.context.signal("spooler;realtime", len(self._realtime_queue))
                if program is not None:
                    # Process all data in the program.
                    self._execute_program(program)
            # Check if driver is holding work.
            if self.driver.hold_work():
                time.sleep(0.01)
                continue
            if len(self._queue):
                # There is active work to do.
                with self._lock:
                    # threadsafe
                    program = self._queue.pop(0)
                self._current = program
                self.context.signal("spooler;queue", len(self._queue))
                if program is not None:
                    # Process all data in the program.
                    self._execute_program(program)
            # Check if driver is holding idle.
            if self.driver.hold_idle():
                time.sleep(0.01)
                continue
            if self._current is not self._idle:
                self.context.signal("spooler;idle", True)
            self._current = self._idle
            if self._idle is not None:
                self._execute_program(self._idle)
                # Finished idle cycle.
                continue
            else:
                # There is nothing to send or do.
                time.sleep(0.1)

    @property
    def current(self):
        return self._current

    @property
    def idle(self):
        return self._idle

    @property
    def realtime_queue(self):
        return self._realtime_queue

    @property
    def queue(self):
        return self._queue

    def append(self, item):
        self.job(item)

    def peek(self):
        if len(self._queue) == 0:
            return None
        return self._queue[0]

    def pop(self):
        if len(self._queue) == 0:
            self.context.signal("spooler;queue", len(self._queue))
            return None
        with self._lock:
            queue_head = self._queue[0]
            del self._queue[0]
        self.context.signal("spooler;queue", len(self._queue))
        return queue_head

    def realtime(self, *job):
        """
        Enqueues a job into the realtime buffer. This preempts the regular work and is checked before hold_work.

        @param job:
        @return:
        """
        with self._realtime_lock:
            if len(job) == 1:
                self._realtime_queue.extend(job)
            else:
                self._realtime_queue.append(job)
        self.context.signal("spooler;realtime", len(self._realtime_queue))

    def job(self, *job):
        """
        Send a single job event with parameters as needed.

        The job can be a single command with ("move" 20 20) or without parameters ("home"), or a generator
        which can yield many lasercode commands.

        @param job: job to send to the spooler.
        @return:
        """
        with self._lock:
            if len(job) == 1:
                self._queue.extend(job)
            else:
                self._queue.append(job)
        self.context.signal("spooler;queue", len(self._queue))

    def jobs(self, jobs):
        """
        Send several jobs be appended to the end of the queue.

        The 'jobs' parameter must be suitable to be .extended to the end of the queue list.

        @param jobs: jobs to extend
        @return:
        """
        with self._lock:
            if isinstance(jobs, (list, tuple)):
                self._queue.extend(jobs)
            else:
                self._queue.append(jobs)
        self.context.signal("spooler;queue", len(self._queue))

    def set_idle(self, job):
        """
        Sets the idle job.

        @param job:
        @return:
        """
        if self._idle is not job:
            self.context.signal("spooler;idle", True)
        self._idle = job

    def job_if_idle(self, *element):
        """
        Deprecated.

        This should be fed into various forms of idle job.
        @param element:
        @return:
        """
        if len(self._queue) == 0:
            self.job(*element)
            return True
        else:
            return False

    def clear_queue(self):
        with self._lock:
            self._queue.clear()
        self.context.signal("spooler;queue", len(self._queue))

    def remove(self, element, index=None):
        with self._lock:
            if index is None:
                self._queue.remove(element)
            else:
                del self._queue[index]
        self.context.signal("spooler;queue", len(self._queue))
