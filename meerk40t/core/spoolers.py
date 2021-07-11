from threading import Lock

from meerk40t.svgelements import Length

from ..device.lasercommandconstants import *
from ..kernel import Modifier
from .elements import MILS_IN_MM


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Spoolers", Spoolers)
        kernel_root = kernel.root
        kernel_root.activate("modifier/Spoolers")


class Spooler:
    """
    A spooler stores spoolable lasercode events as a synchronous queue.

    * peek()
    * pop()
    * job(job)
    * jobs(iterable<job>)
    * job_if_idle(job) -- Will enqueue the job if the device is currently idle.
    * clear_queue()
    * remove(job)
    """

    def __init__(self, context, spooler_name, *args, **kwargs):
        self.context = context
        self.name = spooler_name
        self.queue_lock = Lock()
        self._queue = []
        self.next = None

    def __repr__(self):
        return "Spooler(%s)" % str(self.name)

    def __del__(self):
        self.name = None
        self.queue_lock = None
        self._queue = None
        self.next = None

    def as_device(self):
        links = []
        obj = self
        while obj is not None:
            links.append(str(obj))
            obj = obj.next
        return " -> ".join(links)

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
            return None
        self.queue_lock.acquire(True)
        queue_head = self._queue[0]
        del self._queue[0]
        self.queue_lock.release()
        self.context.signal("spooler;queue", len(self._queue), self.name)
        return queue_head

    def job(self, *job):
        """
        Send a single job event with parameters as needed.

        The job can be a single command with (COMMAND_MOVE 20 20) or without parameters (COMMAND_HOME), or a generator
        which can yield many lasercode commands.

        :param job: job to send to the spooler.
        :return:
        """
        self.queue_lock.acquire(True)

        if len(job) == 1:
            self._queue.extend(job)
        else:
            self._queue.append(job)
        self.queue_lock.release()
        self.context.signal("spooler;queue", len(self._queue))

    def jobs(self, jobs):
        """
        Send several jobs generators to be appended to the end of the queue.

        The jobs parameter must be suitable to be .extended to the end of the queue list.
        :param jobs: jobs to extend
        :return:
        """
        self.queue_lock.acquire(True)
        if isinstance(jobs, (list, tuple)):
            self._queue.extend(jobs)
        else:
            self._queue.append(jobs)
        self.queue_lock.release()
        self.context.signal("spooler;queue", len(self._queue))

    def job_if_idle(self, element):
        if len(self._queue) == 0:
            self.job(element)
            return True
        else:
            return False

    def clear_queue(self):
        self.queue_lock.acquire(True)
        self._queue = []
        self.queue_lock.release()
        self.context.signal("spooler;queue", len(self._queue))

    def remove(self, element, index=None):
        self.queue_lock.acquire(True)
        if index is None:
            self._queue.remove(element)
        else:
            del self._queue[index]
        self.queue_lock.release()
        self.context.signal("spooler;queue", len(self._queue))


class Spoolers(Modifier):
    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)

    def get_or_make_spooler(self, device_name):
        dev = "device/%s" % device_name
        try:
            device = self.context.registered[dev]
        except KeyError:
            device = [None, None, None]
            self.context.registered[dev] = device
        if device[0] is None:
            device[0] = Spooler(self.context, device_name)
        return device[0]

    def default_spooler(self):
        return self.get_or_make_spooler(self.context.root.active)

    def attach(self, *a, **kwargs):
        context = self.context
        context.spoolers = self
        bed_dim = context.root
        self.context.root.setting(str, "active", "0")

        kernel = self.context._kernel
        _ = kernel.translation

        @context.console_option(
            "register",
            "r",
            type=bool,
            action="store_true",
            help=_("Register this device"),
        )
        @context.console_command(
            "spool",
            help=_("spool<?> <command>"),
            regex=True,
            input_type=(None, "plan", "device"),
            output_type="spooler",
        )
        def spool(
            command, channel, _, data=None, register=False, remainder=None, **kwgs
        ):
            root = self.context.root
            if len(command) > 5:
                device_name = command[5:]
            else:
                if register:
                    device_context = kernel.get_context("devices")
                    index = 0
                    while hasattr(device_context, "device_%d" % index):
                        index += 1
                    device_name = str(index)
                else:
                    device_name = root.active
            if register:
                device_context = kernel.get_context("devices")
                setattr(
                    device_context,
                    "device_%s" % device_name,
                    ("spool%s -r " % device_name) + remainder + "\n",
                )

            spooler = self.get_or_make_spooler(device_name)
            if data is not None:
                # If plan data is in data, then we copy that and move on to next step.
                spooler.jobs(data.plan)
                channel(_("Spooled Plan."))
                self.context.signal("plan", data.name, 6)

            if remainder is None:
                channel(_("----------"))
                channel(_("Spoolers:"))
                for d, d_name in enumerate(self.context.match("device", True)):
                    channel("%d: %s" % (d, d_name))
                channel(_("----------"))
                channel(_("Spooler %s:" % device_name))
                for s, op_name in enumerate(spooler.queue):
                    channel("%d: %s" % (s, op_name))
                channel(_("----------"))

            return "spooler", (spooler, device_name)

        @context.console_command(
            "list",
            help=_("spool<?> list"),
            input_type="spooler",
            output_type="spooler",
        )
        def spooler_list(command, channel, _, data_type=None, data=None, **kwgs):
            spooler, device_name = data
            channel(_("----------"))
            channel(_("Spoolers:"))
            for d, d_name in enumerate(self.context.match("device", True)):
                channel("%d: %s" % (d, d_name))
            channel(_("----------"))
            channel(_("Spooler %s:" % device_name))
            for s, op_name in enumerate(spooler.queue):
                channel("%d: %s" % (s, op_name))
            channel(_("----------"))
            return data_type, data

        @context.console_argument("op", type=str, help=_("unlock, origin, home, etc"))
        @context.console_command(
            "send",
            help=_("send a plan-command to the spooler"),
            input_type="spooler",
            output_type="spooler",
        )
        def spooler_send(
            command, channel, _, data_type=None, op=None, data=None, **kwgs
        ):
            spooler, device_name = data
            if op is None:
                raise SyntaxError
            try:
                for command_name in self.context.match("plan/%s" % op):
                    plan_command = self.context.registered[command_name]
                    spooler.job(plan_command)
                    return data_type, data
            except (KeyError, IndexError):
                pass
            channel(_("No plan command found."))
            return data_type, data

        @context.console_command(
            "clear",
            help=_("spooler<?> clear"),
            input_type="spooler",
            output_type="spooler",
        )
        def spooler_clear(command, channel, _, data_type=None, data=None, **kwgs):
            spooler, device_name = data
            spooler.clear_queue()
            return data_type, data

        def execute_absolute_position(position_x, position_y):
            x_pos = Length(position_x).value(
                ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
            )
            y_pos = Length(position_y).value(
                ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
            )

            def move():
                yield COMMAND_SET_ABSOLUTE
                yield COMMAND_MODE_RAPID
                yield COMMAND_MOVE, int(x_pos), int(y_pos)

            return move

        def execute_relative_position(position_x, position_y):
            x_pos = Length(position_x).value(
                ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
            )
            y_pos = Length(position_y).value(
                ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
            )

            def move():
                yield COMMAND_SET_INCREMENTAL
                yield COMMAND_MODE_RAPID
                yield COMMAND_MOVE, int(x_pos), int(y_pos)
                yield COMMAND_SET_ABSOLUTE

            return move

        @context.console_command(
            "+laser",
            hidden=True,
            input_type=("spooler", None),
            output_type="spooler",
            help=_("turn laser on in place"),
        )
        def plus_laser(data, **kwgs):
            if data is None:
                data = self.default_spooler(), self.context.root.active
            spooler, device_name = data
            spooler.job(COMMAND_LASER_ON)
            return "spooler", data

        @context.console_command(
            "-laser",
            hidden=True,
            input_type=("spooler", None),
            output_type="spooler",
            help=_("turn laser off in place"),
        )
        def minus_laser(data, **kwgs):
            if data is None:
                data = self.default_spooler(), self.context.root.active
            spooler, device_name = data
            spooler.job(COMMAND_LASER_OFF)
            return "spooler", data

        @context.console_argument(
            "amount", type=Length, help=_("amount to move in the set direction.")
        )
        @context.console_command(
            ("left", "right", "up", "down"),
            input_type=("spooler", None),
            output_type="spooler",
            help=_("cmd <amount>"),
        )
        def direction(command, channel, _, data=None, amount=None, **kwgs):
            if data is None:
                data = self.default_spooler(), self.context.root.active
            spooler, device_name = data
            if amount is None:
                amount = Length("1mm")
            max_bed_height = bed_dim.bed_height * MILS_IN_MM
            max_bed_width = bed_dim.bed_width * MILS_IN_MM
            if not hasattr(spooler, "_dx"):
                spooler._dx = 0
            if not hasattr(spooler, "_dy"):
                spooler._dy = 0
            if command.endswith("right"):
                spooler._dx += amount.value(ppi=1000.0, relative_length=max_bed_width)
            elif command.endswith("left"):
                spooler._dx -= amount.value(ppi=1000.0, relative_length=max_bed_width)
            elif command.endswith("up"):
                spooler._dy -= amount.value(ppi=1000.0, relative_length=max_bed_height)
            elif command.endswith("down"):
                spooler._dy += amount.value(ppi=1000.0, relative_length=max_bed_height)
            context(".timer 1 0 spool%s jog\n" % device_name)
            return "spooler", data

        @context.console_command(
            "jog",
            hidden=True,
            input_type="spooler",
            output_type="spooler",
            help=_("executes outstanding jog buffer"),
        )
        def jog(command, channel, _, data, **kwgs):
            if data is None:
                data = self.default_spooler(), self.context.root.active
            spooler, device_name = data
            try:
                idx = int(spooler._dx)
                idy = int(spooler._dy)
            except AttributeError:
                return
            if idx == 0 and idy == 0:
                return
            if spooler.job_if_idle(execute_relative_position(idx, idy)):
                channel(_("Position moved: %d %d") % (idx, idy))
                spooler._dx -= idx
                spooler._dy -= idy
            else:
                channel(_("Busy Error"))
            return "spooler", data

        @context.console_argument("x", type=Length, help=_("change in x"))
        @context.console_argument("y", type=Length, help=_("change in y"))
        @context.console_command(
            ("move", "move_absolute"),
            input_type=("spooler", None),
            output_type="spooler",
            help=_("move <x> <y>: move to position."),
        )
        def move(channel, _, x, y, data=None, **kwgs):
            if data is None:
                data = self.default_spooler(), self.context.root.active
            spooler, device_name = data
            if y is None:
                raise SyntaxError
            if not spooler.job_if_idle(execute_absolute_position(x, y)):
                channel(_("Busy Error"))
            return "spooler", data

        @context.console_argument("dx", type=Length, help=_("change in x"))
        @context.console_argument("dy", type=Length, help=_("change in y"))
        @context.console_command(
            "move_relative",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("move_relative <dx> <dy>"),
        )
        def move_relative(channel, _, dx, dy, data=None, **kwgs):
            if data is None:
                data = self.default_spooler(), self.context.root.active
            spooler, device_name = data
            if dy is None:
                raise SyntaxError
            if not spooler.job_if_idle(execute_relative_position(dx, dy)):
                channel(_("Busy Error"))
            return "spooler", data

        @context.console_argument("x", type=Length, help=_("x offset"))
        @context.console_argument("y", type=Length, help=_("y offset"))
        @context.console_command(
            "home",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("home the laser"),
        )
        def home(x=None, y=None, data=None, **kwgs):
            if data is None:
                data = self.default_spooler(), self.context.root.active
            spooler, device_name = data
            if x is not None and y is not None:
                x = x.value(ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM)
                y = y.value(ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM)
                spooler.job(COMMAND_HOME, int(x), int(y))
                return "spooler", data
            spooler.job(COMMAND_HOME)
            return "spooler", data

        @context.console_command(
            "unlock",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("unlock the rail"),
        )
        def unlock(data=None, **kwgs):
            if data is None:
                data = self.default_spooler(), self.context.root.active
            spooler, device_name = data
            spooler.job(COMMAND_UNLOCK)
            return "spooler", data

        @context.console_command(
            "lock",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("lock the rail"),
        )
        def lock(data, **kwgs):
            if data is None:
                data = self.default_spooler(), self.context.root.active
            spooler, device_name = data
            spooler.job(COMMAND_LOCK)
            return "spooler", data

        for i in range(5):
            self.get_or_make_spooler(str(i))
