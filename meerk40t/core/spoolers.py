from threading import Lock

from ..kernel import Modifier


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Spoolers", Spoolers)
    elif lifecycle == "boot":
        kernel_root = kernel.get_context("/")
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
        self.spooler_name = spooler_name
        self.queue_lock = Lock()
        self._queue = []

    def __repr__(self):
        return "Spooler(%s, %s)" % (repr(self.context), str(self.spooler_name))

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
        self.context.signal("spooler;queue", len(self._queue),  self.spooler_name)
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

    def remove(self, element):
        self.queue_lock.acquire(True)
        self._queue.remove(element)
        self.queue_lock.release()
        self.context.signal("spooler;queue", len(self._queue))


class Spoolers(Modifier):
    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self._spoolers = dict()
        self._default_spooler = "0"

    def get_or_make_spooler(self, spooler_name):
        try:
            return self._spoolers[spooler_name]
        except KeyError:
            self._spoolers[spooler_name] = Spooler(self.context, spooler_name)
            return self._spoolers[spooler_name]

    def default_spooler(self):
        return self.get_or_make_spooler(self._default_spooler)

    def attach(self, *a, **kwargs):
        context = self.context
        context.spoolers = self
        context.spooler = self.default_spooler

        kernel = self.context._kernel
        _ = kernel.translation

        @self.context.console_command(
            "spool",
            help="spooler<?> <command>",
            regex=True,
            input_type=(None, "plan"),
            output_type="spooler",
        )
        def spooler(command, channel, _, data=None, remainder=None, **kwargs):
            if len(command) > 4:
                self._default_spooler = command[5:]
                self.context.signal("spooler", self._default_spooler, None)
            spooler = self.get_or_make_spooler(self._default_spooler)

            if data is not None:
                # If plan data is in data, then we copy that and move on to next step.
                plan, original, commands, plan_name = data
                spooler.jobs(plan)
                channel(_("Spooled Plan."))

                self.context.signal("plan", plan_name, 6)

            if remainder is None:
                channel(_("----------"))
                channel(_("Spoolers:"))
                for i, spooler_name in enumerate(self._spoolers):
                    channel("%d: %s" % (i, spooler_name))
                channel(_("----------"))
                channel(_("Spooler %s:" % self._default_spooler))
                for i, op_name in enumerate(spooler.queue):
                    channel("%d: %s" % (i, op_name))
                channel(_("----------"))

            return "spooler", spooler

        @self.context.console_command(
            "list",
            help="spool<?> list",
            input_type="spool",
            output_type="spool",
        )
        def spooler_list(command, channel, _, data_type=None, data=None, **kwargs):
            spooler = data
            channel(_("----------"))
            channel(_("Spoolers:"))
            for i, spooler_name in enumerate(self._spoolers):
                channel("%d: %s" % (i, spooler_name))
            channel(_("----------"))
            channel(_("Spooler %s:" % self._default_spooler))
            for i, op_name in enumerate(spooler):
                channel("%d: %s" % (i, op_name))
            channel(_("----------"))
            return data_type, data

        @self.context.console_argument("op", type=str, help="unlock, origin, home, etc")
        @self.context.console_command(
            "send",
            help="send a plan-command to the spooler",
            input_type="spooler",
            output_type="spooler",
        )
        def spooler_send(command, channel, _, data_type=None, op=None, data=None, **kwargs):
            spooler = data
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

        @self.context.console_command(
            "clear",
            help="spooler<?> clear",
            input_type="plan",
            output_type="plan",
        )
        def spooler_clear(command, channel, _, data_type=None, data=None, **kwargs):
            spooler = data
            spooler.clear_queue()
            return data_type, data
