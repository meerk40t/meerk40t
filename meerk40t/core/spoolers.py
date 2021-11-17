from threading import Lock


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation


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
        self.label = spooler_name
        self.activate = None

    def __repr__(self):
        return "Spooler(%s)" % str(self.name)

    def __del__(self):
        self.name = None
        self.queue_lock = None
        self._queue = None
        self.next = None

    def __len__(self):
        return len(self._queue)

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
            self.context.signal("spooler;queue", len(self._queue), self.name)
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
