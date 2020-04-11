import time
from threading import *

from LaserOperation import *
from svgelements import Path, SVGText

THREAD_STATE_UNKNOWN = -1
THREAD_STATE_UNSTARTED = 0
THREAD_STATE_STARTED = 1
THREAD_STATE_PAUSED = 2
THREAD_STATE_FINISHED = 3
THREAD_STATE_ABORT = 10

SHUTDOWN_BEGIN = 0
SHUTDOWN_FLUSH = 1
SHUTDOWN_WINDOW = 2
SHUTDOWN_WINDOW_ERROR = -1
SHUTDOWN_MODULE = 3
SHUTDOWN_MODULE_ERROR = -2
SHUTDOWN_THREAD = 4
SHUTDOWN_THREAD_ERROR = -4
SHUTDOWN_THREAD_ALIVE = 5
SHUTDOWN_THREAD_FINISHED = 6
SHUTDOWN_LISTENER_ERROR = -10
SHUTDOWN_FINISH = 100


class KernelJob:
    def __init__(self, scheduler, process, args, interval=1.0, times=None):
        self.scheduler = scheduler
        self.interval = interval
        self.last_run = time.time()
        self.next_run = self.last_run + self.interval
        self.process = process
        self.args = args
        self.times = times
        self.paused = False
        self.executing = False

    @property
    def scheduled(self):
        return self.next_run is not None and time.time() >= self.next_run

    def cancel(self):
        self.times = -1
        self.scheduler.jobs.remove(self)

    def run(self):
        """
        Scheduler Job: updates the values for next_run and times. Removing if necessary.
        Executes the process requested in the SchedulerThread.

        :return:
        """
        if self.paused:
            return
        self.next_run = None

        if self.times is not None:
            self.times = self.times - 1
            if self.times <= 0:
                self.scheduler.jobs.remove(self)
            if self.times < 0:
                return
        if isinstance(self.args, tuple):
            self.process(*self.args)
        else:
            self.process(self.args)
        self.last_run = time.time()
        self.next_run = self.last_run + self.interval


class Module:
    """
    Modules are a generic lifecycle object. When registered they are passed the kernel they are registered to, and when
    the kernel is shutdown, the shutdown event is called. This permits the knowing registering and unregistering of
    other kernel objects. and the attachment of the module to a device.
    """

    def __init__(self):
        self.name = None
        self.kernel = None
        self.device = None

    def initialize(self, kernel, name=None):
        self.kernel = kernel
        self.name = name

    def register(self, device):
        self.device = device

    def deregister(self, device):
        self.device = None
        if self.name is not None:
            del device.module_instances[self.name]

    def shutdown(self, kernel):
        self.kernel = None
        try:
            if self.name is not None:
                del kernel.module_instances[self.name]
        except KeyError:
            pass


class Device:
    def __init__(self, kernel=None, uid=None, spooler=None, interpreter=None, pipe=None):
        self.kernel = kernel
        self.uid = uid
        self.spooler = spooler
        self.interpreter = interpreter
        self.pipe = pipe
        self._device_log = ''
        self.current_x = 0
        self.current_y = 0
        self.state = -1
        self.location = ''
        self.hold_condition = lambda e: False

    def _start_debugging(self):
        import functools
        import datetime
        import types
        filename = "MeerK40t-debug-{date:%Y-%m-%d_%H_%M_%S}.txt".format(date=datetime.datetime.now())
        debug_file = open(filename, "a")
        debug_file.write("\n\n\n")

        def debug(func, obj):
            @functools.wraps(func)
            def wrapper_debug(*args, **kwargs):
                args_repr = [repr(a) for a in args]

                kwargs_repr = ["%s=%s" % (k, v) for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
                start = "Calling %s.%s(%s)" % (str(obj), func.__name__, signature)
                debug_file.write(start + '\n')
                print(start)
                t = time.time()
                value = func(*args, **kwargs)
                t = time.time() - t
                finish = "    %s returned %s after %fms" % (func.__name__, value, t * 1000)
                print(finish)
                debug_file.write(finish + '\n')
                debug_file.flush()
                return value

            return wrapper_debug

        for obj in (self, self.spooler, self.pipe, self.interpreter):
            for attr in dir(obj):
                if attr.startswith('_'):
                    continue
                fn = getattr(obj, attr)
                if not isinstance(fn, types.FunctionType) and \
                        not isinstance(fn, types.MethodType):
                    continue
                setattr(obj, attr, debug(fn, obj))

    def hold(self):
        if self.spooler.thread.state == THREAD_STATE_ABORT:
            raise InterruptedError
        while self.hold_condition(0):
            if self.spooler.thread.state == THREAD_STATE_ABORT:
                raise InterruptedError
            time.sleep(0.1)

    def close(self):
        self.flush()

    def send_job(self, job):
        self.spooler.send_job(job)

    def execute(self, control_name, *args):
        self.kernel.controls[self.uid + control_name](*args)

    def signal(self, code, *message):
        self.kernel.signal(self.uid + ';' + code, *message)

    def log(self, message):
        self._device_log += message
        self.signal('pipe;device_log', message)

    def setting(self, setting_type, setting_name, default=None):
        """
        Registers a setting to be used on this device. The functionality is
        similar to that of Kernel.setting except that it registers at the device level.
        """
        setting_uid_name = self.uid + setting_name
        if hasattr(self, setting_name) and getattr(self, setting_name) is not None:
            return
        if not setting_name.startswith('_') and self.kernel.config is not None:
            load_value = self.kernel[setting_type, setting_uid_name, default]
        else:
            load_value = default
        setattr(self, setting_name, load_value)
        return load_value

    def flush(self):
        for attr in dir(self):
            if attr.startswith('_'):
                continue
            if attr == 'uid':
                continue
            value = getattr(self, attr)
            if value is None:
                continue
            uid_attr = self.uid + attr
            if isinstance(value, (int, bool, str, float)):
                self.kernel[uid_attr] = value

    def get(self, key):
        key = self.uid + key
        if hasattr(self.kernel, key):
            return getattr(self.kernel, key)

    def listen(self, signal, function):
        self.kernel.listen(self.uid + ';' + signal, function)

    def unlisten(self, signal, function):
        self.kernel.unlisten(self.uid + ';' + signal, function)

    def thread_instance_add(self, name, thread):
        self.kernel.thread_instance_add(self.uid + name, thread)

    def control_instance_add(self, name, control):
        self.kernel.control_instance_add(self.uid + name, control)


class SpoolerThread(Thread):
    """
    SpoolerThreads perform the spooler functions in an async manner.
    When the spooler is empty the thread ends.

    Expects spooler has commands:
    peek(), pop(), hold(), execute(), thread_state_update(int),

    """

    def __init__(self, spooler):
        Thread.__init__(self, name='MeerK40t-Spooler')
        self.spooler = spooler
        self.state = None
        self.set_state(THREAD_STATE_UNSTARTED)

    def set_state(self, state):
        if self.state != state:
            self.state = state
            self.spooler.thread_state_update()

    def start_element_producer(self):
        if self.state != THREAD_STATE_ABORT:
            self.set_state(THREAD_STATE_STARTED)
            self.start()

    def pause(self):
        self.set_state(THREAD_STATE_PAUSED)

    def resume(self):
        self.set_state(THREAD_STATE_STARTED)

    def abort(self, val):
        if val != 0:
            self.set_state(THREAD_STATE_ABORT)

    def stop(self):
        self.abort(1)

    def spool_line(self, e):
        if isinstance(e, (tuple, list)):
            command = e[0]
            if len(e) >= 2:
                values = e[1:]
            else:
                values = [None]
        elif isinstance(e, int):
            command = e
            values = [None]
        else:
            return
        self.spooler.device.hold()
        self.spooler.execute(command, *values)

    def run(self):
        """
        Main loop for the Spooler Thread.

        This runs the spooled laser commands sent do the device and turns those commands whatever the interpreter needs
        to send to the pipe. This code runs through all spooled objects which are either generators or code with a
        'generate' function that produces a generator. And the generators, in turn, yield a series of laser commands.

        The spooler automatically exits when there is no data left to spool.
        The spooler holds based on the device hold() commands, which should block the thread as needed.
        The call to hold() will either instantly return, decide to hold, or throw an InterruptError.
        The error will be caught and cause the thread to terminate.
        """
        self.set_state(THREAD_STATE_STARTED)
        try:
            self.spooler.device.hold()
            while True:
                element = self.spooler.peek()
                if element is None:
                    break  # Nothing left in spooler.
                self.spooler.device.hold()
                if self.state == THREAD_STATE_ABORT:
                    break
                if isinstance(element, (tuple, list)):
                    self.spool_line(element)
                else:
                    try:
                        gen = element.generate
                    except AttributeError:
                        gen = element
                    for e in gen():
                        if self.state == THREAD_STATE_ABORT:
                            break
                        self.spool_line(e)
                self.spooler.pop()
        except InterruptedError:
            pass
        if self.state == THREAD_STATE_ABORT:
            return
        self.set_state(THREAD_STATE_FINISHED)


class Spooler:
    """
    Given spoolable objects it uses an interpreter to convert these to code.

    The code is then written to a pipe.
    These operations occur in an async manner with a registered SpoolerThread.
    """

    def __init__(self, device):
        self.device = device

        self.queue_lock = Lock()
        self.queue = []
        self.thread = None
        self.reset_thread()

    def __repr__(self):
        return "Spooler()"

    def thread_state_update(self):
        if self.thread is None:
            self.device.signal('spooler;thread', THREAD_STATE_UNSTARTED)
        else:
            self.device.signal('spooler;thread', self.thread.state)

    def execute(self, command, *values):
        self.device.hold()
        self.device.interpreter.command(command, *values)

    def realtime(self, command, *values):
        """Realtimes are sent directly to the interpreter without spooling."""
        if command == COMMAND_PAUSE:
            self.thread.pause()
        elif command == COMMAND_RESUME:
            self.thread.resume()
        elif command == COMMAND_RESET:
            self.thread.stop()
            self.clear_queue()
        elif command == COMMAND_CLOSE:
            self.thread.stop()
        try:
            return self.device.interpreter.realtime_command(command, values)
        except NotImplementedError:
            pass

    def peek(self):
        if len(self.queue) == 0:
            return None
        return self.queue[0]

    def pop(self):
        if len(self.queue) == 0:
            return None
        self.queue_lock.acquire(True)
        queue_head = self.queue[0]
        del self.queue[0]
        self.queue_lock.release()
        self.device.signal("spooler;queue", len(self.queue))
        return queue_head

    def add_command(self, *element):
        self.queue_lock.acquire(True)
        self.queue.append(element)
        self.queue_lock.release()
        self.start_queue_consumer()
        self.device.signal("spooler;queue", len(self.queue))

    def send_job(self, element):
        self.queue_lock.acquire(True)
        if isinstance(element, (list, tuple)):
            self.queue += element
        else:
            self.queue.append(element)
        self.queue_lock.release()
        self.start_queue_consumer()
        self.device.signal("spooler;queue", len(self.queue))

    def clear_queue(self):
        self.queue_lock.acquire(True)
        self.queue = []
        self.queue_lock.release()
        self.device.signal("spooler;queue", len(self.queue))

    def reset_thread(self):
        self.thread = SpoolerThread(self)
        self.thread_state_update()

    def start_queue_consumer(self):
        if self.thread.state == THREAD_STATE_ABORT:
            # We cannot reset an aborted thread without specifically calling reset.
            return
        if self.thread.state == THREAD_STATE_FINISHED:
            self.reset_thread()
        if self.thread.state == THREAD_STATE_UNSTARTED:
            self.thread.state = THREAD_STATE_STARTED
            self.thread.start()


class Interpreter:
    """
    An Interpreter takes spoolable commands and turns those commands into states and code in a language
    agnostic fashion. This is intended to be overridden by a subclass or class with the required methods.
    """

    def __init__(self, device=None):
        self.device = device

    def __len__(self):
        if self.device.pipe is None:
            return 0
        else:
            return len(self.device.pipe)

    def command(self, command, values=None):
        """Commands are middle language LaserCommandConstants there values are given."""
        return NotImplementedError

    def realtime_command(self, command, values=None):
        """Asks for the execution of a realtime command. Unlike the spooled commands these
        return False if rejected and something else if able to be performed. These will not
        be queued. If rejected. They must be performed in realtime or cancelled.
        """
        return self.command(command, values)


class Pipe:
    """
    Write dataflow in the kernel. Provides general information about buffer size in through len() builtin.
    Pipes have a write and realtime_write functions.
    """

    def __len__(self):
        return 0

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def write(self, bytes_to_write):
        raise NotImplementedError

    def realtime_write(self, bytes_to_write):
        """
        This method shall be permitted to not exist.
        To facilitate pipes being easily replaced with filelike objects, any calls
        to this method should assume pipe may not have this command.
        """
        self.write(bytes_to_write)


class Channel:
    """
    Channels are a dataflow object to connect different modules together. These are often for logging of events or any
    other optional data output pipes.
    """

    def __init__(self):
        self.watcher = None
        self.greet = None

    def post(self, channel, text):
        if self.watcher is not None:
            for m in self.watcher:
                m(channel, text)

    def add_watcher(self, monitor_function):
        if self.watcher is None:
            self.watcher = [monitor_function]
        else:
            self.watcher.append(monitor_function)
        if self.greet is not None:
            monitor_function(None, self.greet)

    def remove_watcher(self, monitor_function):
        if self.watcher is not None:
            self.watcher.remove(monitor_function)


class Effect:
    """
    The select is a selections string for the exporting element selection.
    The save is the export file to use.
    The path refers to the external program.
    The command is the command to call the path with.
    The load is the file expected to exist when the execution finishes.
    """

    def __init__(self, select, save, path, command, load):
        self.select = select
        self.save = save
        self.path = path
        self.command = command
        self.load = load


class Modification:
    """
    Modifications are functions called on single SVGElement objects.
    Type Input is the input type kind of element this is intended to act upon.
    Type Output is the output type of the element this is intended to produce.
    """

    def __init__(self, input_type, output_type):
        self.input_type = input_type
        self.output_type = output_type


class Kernel(Thread):
    """
    The kernel is the software framework that is tasked with the API implementation.

    The class serves as:
    * a hub of communications between different processes.
    * implementation of event listeners
    * persistent saving and loading settings data
    * the threading of different events
    * interactions between different modules

    Since most parts of the system are intended to allow swapping between the different modules a level of API
    abstraction is required. The hackability of various systems depends on a robust code that is agnostic to the state
    of the rest of modules.

    LaserNode data is primarily of three types: path, image, and text.
    Readers convert some file or streams being read into LaserNode data.
    Saver, convert LaserNode data into some types of files or streams.
    Effects convert LaserNode data into different LaserNode data.
    Operations are functions that can be arbitrarily added to spoolers.
    Controls are functions that can simply be called, typically for very light threads.
    A spooler is a processing queue for LaserNode data and other command generators.
    Command generators use the LaserCommandConstant middle language to facilitate controller events.
    LaserNode are command generators.

    Most MeerK40t objects will have a direct reference to the Kernel. However, the Kernel should not directly reference
    any object.

    kernel.setting(type, name, default): Registers kernel.name as a persistent setting.
    kernel.flush(): push out persistent settings
    kernel.listen(signal, function): Registers function as a listener for the given signal.
    kernel.unlisten(signal, function): Unregister function as a listener for the signal.
    kernel.add_loader(loader): Registers a qualified loader function.
    kernel.add_saver(file): Registers a qualified saver function.
    kernel.add_effect(effect): registers a qualified effect.
    kernel.add_operation(op): registers a spooler operation
    kernel.add_thread(thread, object): Registers a thread.
    kernel.remove_thread(thread)

    kernel.load(file): Loads the given file and turns it into laser nodes.
    kernel.write(file): Saves the laser nodes to the given filename or stream.
    kernel.tick(seconds, function): tick each x seconds until function returns False.
    kernel.shutdown(): shuts down kernel.

    kernel(signal, value): Calls the signal with the given value.
    """

    def __init__(self, config=None):
        Thread.__init__(self, name='KernelThread')
        self.daemon = True
        self.state = THREAD_STATE_UNSTARTED
        self.jobs = []

        # Current Project.
        self.elements = []
        self.operations = []
        self.filenodes = {}

        # Instanceable Kernel Objects
        self.registered_devices = {}
        self.registered_modules = {}
        self.registered_pipes = {}
        self.registered_loaders = {}
        self.registered_savers = {}
        self.registered_modifications = {}
        self.registered_effects = {}

        # Active Kernel Object Instances
        self.device_instances = {}
        self.module_instances = {}
        self.pipe_instances = {}
        self.channel_instances = {}
        self.control_instances = {}
        self.thread_instances = {}

        # Signal processing.
        self.listeners = {}
        self.adding_listeners = []
        self.removing_listeners = []
        self.last_message = {}
        self.queue_lock = Lock()
        self.message_queue = {}
        self._is_queue_processing = False
        self.run_later = lambda listener, message: listener(message)

        # Persistent storage if it exists.
        self.config = None
        if config is not None:
            self.set_config(config)

        # Active Device
        self.device = None

        # Shutdown watcher if exists.
        self.shutdown_watcher = lambda i, e, o: True

        # Translation function if exists.
        self.translation = lambda e: e  # Default for this code is do nothing.

        # Keymap values
        self.keymap = {}

    def __str__(self):
        return "Project"

    def __call__(self, code, *message):
        self.signal(code, *message)

    def __setitem__(self, key, value):
        """
        Kernel value settings. If Config is registered this will be persistent.
        :param key: Key to set.
        :param value: Value to set
        :return: None
        """
        if isinstance(key, tuple):
            if value is None:
                key, value = key
                self.unlisten(key, value)
            else:
                key, value = key
                self.listen(key, value)
        elif isinstance(key, str):
            self.write_config(key, value)

    def __getitem__(self, item):
        """
        Kernel value get. If Config is set registered this will be persistent.

        As a shorthand any float, int, string, or bool set with this will also be found at kernel.item

        :param item:
        :return:
        """
        if isinstance(item, tuple):
            if len(item) == 2:
                t, key = item
                return self.read_config(t, key)
            else:
                t, key, default = item
                return self.read_config(t, key, default)
        return self.config.Read(item)

    def add_job(self, run, args=(), interval=1.0, times=None):
        """
        Adds a job to the scheduler.

        :param run: function to run
        :param args: arguments to give to that function.
        :param interval: in seconds, how often should the job be run.
        :param times: limit on number of executions.
        :return: Reference to the job added.
        """
        job = KernelJob(self, run, args, interval, times)
        self.jobs.append(job)
        return job

    def run(self):
        """
        Scheduler main loop.
        Check the Scheduler thread state, and whether it should abort or pause.
        Check each job, and if that job is scheduled to run. Executes that job.
        :return:
        """
        self.state = THREAD_STATE_STARTED
        while self.state != THREAD_STATE_FINISHED:
            time.sleep(0.005)  # 200 ticks a second.
            if self.state == THREAD_STATE_ABORT:
                break
            while self.state == THREAD_STATE_PAUSED:
                # The scheduler is paused.
                time.sleep(1.0)
            for job in self.jobs:
                # Checking if jobs should run.
                if job.scheduled:
                    job.run()
        self.state = THREAD_STATE_FINISHED
        # If we aborted the thread, we trigger Kernel Shutdown in this thread.
        self.shutdown()

    def state(self):
        return self.state

    def resume(self):
        self.state = THREAD_STATE_STARTED

    def pause(self):
        self.state = THREAD_STATE_PAUSED

    def stop(self):
        self.state = THREAD_STATE_ABORT

    def boot(self):
        """
        Kernel boot sequence. This should be called after all the registered devices are established.
        :return:
        """
        if not self.is_alive():
            self.add_job(self.delegate_messages, args=(), interval=0.05)
            self.start()

        self.setting(str, 'device_list', '')
        self.setting(str, 'device_primary', '')
        for device in self.device_list.split(';'):
            args = list(device.split(':'))
            if len(args) == 1:
                for r in self.registered_devices:
                    self.device_instance_open(r, args[0])
                    break
            else:
                self.device_instance_open(args[1], args[0])
            if device == self.device_primary:
                self.activate_device(device)

    def shutdown(self):
        """
        Begins kernel shutdown procedure.

        Checks if shutdown should be done.
        Save Kernel Persistent settings.
        Save Device Persistent settings.
        Closes all windows.
        Ask all modules to shutdown.
        Wait for threads to end.
        -- If threads do not end, threads must be aborted.
        Notifies of listener errors.
        """

        kill = self.shutdown_watcher

        if not kill(SHUTDOWN_BEGIN, 'shutdown', self):
            return
        self.flush()
        for device_name in self.device_instances:
            device = self.device_instances[device_name]
            if kill(SHUTDOWN_FLUSH, device_name, device):
                device.flush()
        if self.config is not None:
            self.config.Flush()

        for module_name in list(self.module_instances):
            module = self.module_instances[module_name]
            if kill(SHUTDOWN_MODULE, module_name, module):
                try:
                    module.shutdown(self)
                except AttributeError:
                    pass
        for module_name in self.module_instances:
            module = self.module_instances[module_name]
            kill(SHUTDOWN_MODULE_ERROR, module_name, module)

        for thread_name in self.thread_instances:
            thread = self.thread_instances[thread_name]
            if not thread.is_alive:
                kill(SHUTDOWN_THREAD_ERROR, thread_name, thread)
                continue
            if kill(SHUTDOWN_THREAD, thread_name, thread):
                if thread is self:
                    continue
                    # Do not sleep thread waiting for kernelthread to die. This is kernelthread.
                try:
                    thread.stop()
                except AttributeError:
                    pass
                if thread.is_alive:
                    kill(SHUTDOWN_THREAD_ALIVE, thread_name, thread)
                while thread.is_alive():
                    time.sleep(0.1)
                kill(SHUTDOWN_THREAD_FINISHED, thread_name, thread)
        for key, listener in self.listeners.items():
            if len(listener):
                kill(SHUTDOWN_LISTENER_ERROR, key, listener)
        kill(SHUTDOWN_FINISH, 'shutdown', self)
        self.last_message = {}
        self.listeners = {}
        self.device = None

    def read_config(self, t, key, default=None):
        if default is not None:
            if t == str:
                return self.config.Read(key, default)
            elif t == int:
                return self.config.ReadInt(key, default)
            elif t == float:
                return self.config.ReadFloat(key, default)
            elif t == bool:
                return self.config.ReadBool(key, default)
        if t == str:
            return self.config.Read(key)
        elif t == int:
            return self.config.ReadInt(key)
        elif t == float:
            return self.config.ReadFloat(key)
        elif t == bool:
            return self.config.ReadBool(key)

    def write_config(self, key, value):
        if isinstance(value, str):
            self.config.Write(key, value)
        elif isinstance(value, int):
            self.config.WriteInt(key, value)
        elif isinstance(value, float):
            self.config.WriteFloat(key, value)
        elif isinstance(value, bool):
            self.config.WriteBool(key, value)

    def set_config(self, config):
        self.config = config
        for attr in dir(self):
            if attr.startswith('_'):
                continue
            value = getattr(self, attr)
            if value is None:
                continue
            if isinstance(value, (int, bool, float, str)):
                self.write_config(attr, value)
        more, value, index = config.GetFirstEntry()
        while more:
            if not value.startswith('_'):
                if not hasattr(self, value):
                    setattr(self, value, None)
            more, value, index = config.GetNextEntry(index)

    def setting(self, setting_type, setting_name, default=None):
        """
        Registers a setting to be used between modules.

        If the setting exists, its value remains unchanged.
        If the setting exists in the persistent storage that value is used.
        If there is no settings value, the default will be used.

        :param setting_type: int, float, str, or bool value
        :param setting_name: name of the setting
        :param default: default value for the setting to have.
        :return: load_value
        """
        if hasattr(self, setting_name) and getattr(self, setting_name) is not None:
            return
        if not setting_name.startswith('_') and self.config is not None:
            load_value = self[setting_type, setting_name, default]
        else:
            load_value = default
        setattr(self, setting_name, load_value)
        return load_value

    def flush(self):
        for attr in dir(self):
            if attr.startswith('_'):
                continue
            value = getattr(self, attr)
            if value is None:
                continue
            if isinstance(value, (int, bool, str, float)):
                self[attr] = value

    def update(self, setting_name, value):
        if hasattr(self, setting_name):
            old_value = getattr(self, setting_name)
        else:
            old_value = None
        setattr(self, setting_name, value)
        self(setting_name, (value, old_value))

    # Signal processing.

    def signal(self, code, *message):
        """
        Signals add the latest message to the message queue.
        :param code: Signal code
        :param message: Message to send.
        """
        self.queue_lock.acquire(True)
        self.message_queue[code] = message
        self.queue_lock.release()

    def delegate_messages(self):
        """
        Delegate the process queue to the run_later thread.
        run_later should be a threading instance wherein all signals are delivered.
        """
        if self._is_queue_processing:
            return
        self.run_later(self.process_queue, None)

    def process_queue(self, *args):
        """
        Performed in the run_later thread. Signal groups. Threadsafe.

        Process the signals queued up. Inserting any attaching listeners, removing any removing listeners. And
        providing the newly attached listeners the last message known from that signal.
        :param args: None
        :return:
        """
        if len(self.message_queue) == 0 and len(self.adding_listeners) == 0 and len(self.removing_listeners) == 0:
            return
        self._is_queue_processing = True
        add = None
        remove = None
        self.queue_lock.acquire(True)
        queue = self.message_queue
        if len(self.adding_listeners) != 0:
            add = self.adding_listeners
            self.adding_listeners = []
        if len(self.removing_listeners):
            remove = self.removing_listeners
            self.removing_listeners = []
        self.message_queue = {}
        self.queue_lock.release()
        if add is not None:
            for signal, funct in add:
                if signal in self.listeners:
                    listeners = self.listeners[signal]
                    listeners.append(funct)
                else:
                    self.listeners[signal] = [funct]
                if signal in self.last_message:
                    last_message = self.last_message[signal]
                    funct(*last_message)
        if remove is not None:
            for signal, funct in remove:
                if signal in self.listeners:
                    listeners = self.listeners[signal]
                    try:
                        listeners.remove(funct)
                    except ValueError:
                        print("Value error removing: %s  %s" % (str(listeners), signal))

        for code, message in queue.items():
            if code in self.listeners:
                listeners = self.listeners[code]
                for listener in listeners:
                    listener(*message)
            self.last_message[code] = message
        self._is_queue_processing = False

    def last_signal(self, code):
        """
        Queries the last signal for a particular code.
        :param code: code to query.
        :return: Last signal sent through the kernel for that code.
        """
        try:
            return self.last_message[code]
        except KeyError:
            return None

    def listen(self, signal, funct):
        self.queue_lock.acquire(True)
        self.adding_listeners.append((signal, funct))
        self.queue_lock.release()

    def unlisten(self, signal, funct):
        self.queue_lock.acquire(True)
        self.removing_listeners.append((signal, funct))
        self.queue_lock.release()

    # Kernel object registration
    def register_window(self, name, obj):
        self.registered_windows[name] = obj

    def register_module(self, name, obj):
        self.registered_modules[name] = obj

    def register_device(self, name, obj):
        self.registered_devices[name] = obj

    def register_loader(self, name, obj):
        self.registered_loaders[name] = obj

    def register_saver(self, name, obj):
        self.registered_savers[name] = obj

    def register_pipe(self, name, obj):
        self.registered_pipes[name] = obj

    def register_modification(self, name, obj):
        self.registered_modifications[name] = obj

    def register_effect(self, name, obj):
        self.registered_effects[name] = obj

    # Device kernel object

    def device_instance_open(self, device_name, instance_name=None, **kwargs):
        if instance_name is None:
            instance_name = device_name
        device_object = self.registered_devices[device_name]
        device_instance = device_object(**kwargs)
        self.device_instances[instance_name] = device_instance
        device_instance.initialize(self, name=instance_name)
        return device_instance

    def device_instance_close(self, name):
        if name in self.device_instances:
            try:
                self.device_instances[name].close()
            except AttributeError:
                pass  # No close
        self.device_instance_remove(name)

    def device_instance_remove(self, name):
        if name in self.device_instances:
            del self.device_instances[name]

    def activate_device(self, device_name):
        original = self.device
        if device_name is None:
            self.device = None
        else:
            self.device = self.device_instances[device_name]
        if self.device is not original:
            for module_name in self.module_instances:
                module = self.module_instances[module_name]
                if original is not None:
                    module.deregister(original)
                module.register(self.device)
            self.signal("device", self.device)

    # Module kernel objects

    def module_instance_open(self, module_name, *args, instance_name=None, **kwargs):
        if instance_name is None:
            instance_name = module_name
        module_object = self.registered_modules[module_name]
        module_instance = module_object(*args, **kwargs)
        module_instance.initialize(self, name=instance_name)
        self.module_instances[instance_name] = module_instance
        module_instance.register(self.device)
        return module_instance

    def module_instance_close(self, name):
        if name in self.module_instances:
            # try:
            self.module_instances[name].shutdown(self)
            # except AttributeError:
            #     pass  # No shutdown.
        self.module_instance_remove(name)

    def module_instance_remove(self, name):
        if name in self.module_instances:
            del self.module_instances[name]

    # Pipe kernel object

    def pipe_instance_open(self, pipe_name, instance_name=None, **kwargs):
        if instance_name is None:
            instance_name = pipe_name
        pipe_object = self.registered_pipes[pipe_name]
        pipe_instance = pipe_object(**kwargs)
        self.pipe_instances[instance_name] = pipe_instance
        pipe_instance.initialize(self, name=instance_name)
        return pipe_instance

    # Channel kernel object.
    def channel_instance_add(self, name, channel):
        self.channel_instances[name] = channel

    def channel_instance_remove(self, name):
        del self.channel_instances[name]

    def watch(self, name, watcher):
        channel = self.channel_instances[name]
        channel.add_watcher(watcher)

    def unwatch(self, name, watcher):
        channel = self.channel_instances[name]
        channel.remove_watcher(watcher)

    # Control kernel object. Registered function calls.
    def control_instance_add(self, control_name, function):
        self.control_instances[control_name] = function

    def control_instance_remove(self, control_name):
        del self.control_instances[control_name]

    def execute(self, control_name, *args):
        self.control_instances[control_name](*args)

    # Thread kernel object. Registered Threads.
    def thread_instance_add(self, thread_name, obj):
        self.thread_instances[thread_name] = obj

    def thread_instance_remove(self, thread_name):
        del self.thread_instances[thread_name]

    def get_text_thread_state(self, state):
        _ = self.translation
        if state == THREAD_STATE_UNSTARTED:
            return _("Unstarted")
        elif state == THREAD_STATE_ABORT:
            return _("Aborted")
        elif state == THREAD_STATE_FINISHED:
            return _("Finished")
        elif state == THREAD_STATE_PAUSED:
            return _("Paused")
        elif state == THREAD_STATE_STARTED:
            return _("Started")
        elif state == THREAD_STATE_UNKNOWN:
            return _("Unknown")

    def get_state(self, thread_name):
        try:
            return self.thread_instances[thread_name].state()
        except AttributeError:
            return THREAD_STATE_UNKNOWN

    # TODO: check whether these have any actual function anymore.
    def module_start(self, thread_name):
        try:
            self.module_instances[thread_name].start()
        except AttributeError:
            pass

    def module_resume(self, thread_name):
        try:
            self.module_instances[thread_name].resume()
        except AttributeError:
            pass

    def module_pause(self, thread_name):
        try:
            self.module_instances[thread_name].pause()
        except AttributeError:
            pass

    def module_abort(self, thread_name):
        try:
            self.module_instances[thread_name].abort()
        except AttributeError:
            pass

    def module_reset(self, thread_name):
        try:
            self.module_instances[thread_name].reset()
        except AttributeError:
            pass

    def module_stop(self, thread_name):
        try:
            self.module_instances[thread_name].stop()
        except AttributeError:
            pass

    # Element processing and alterations.

    def classify(self, elements):
        """
        Classify does the initial placement of elements as operations.
        RasterOperation is the default for images.
        If element strokes are red they get classed as cut operations
        If they are otherwise they get classed as engrave.
        """
        if elements is None:
            return
        raster = None
        engrave = None
        cut = None
        rasters = []
        engraves = []
        cuts = []

        if not isinstance(elements, list):
            elements = [elements]
        for element in elements:
            if isinstance(element, Path):
                if element.stroke == "red":
                    if cut is None or not cut.has_same_properties(element):
                        cut = CutOperation()
                        cuts.append(cut)
                        cut.set_properties(element)
                    cut.append(element)
                elif element.stroke == "blue":
                    if engrave is None or not engrave.has_same_properties(element):
                        engrave = EngraveOperation()
                        engraves.append(engrave)
                        engrave.set_properties(element)
                    engrave.append(element)
                if (element.stroke != "red" and element.stroke != "blue") or element.fill is not None:
                    # not classed already, or was already classed but has a fill.
                    if raster is None or not raster.has_same_properties(element):
                        raster = RasterOperation()
                        rasters.append(raster)
                        raster.set_properties(element)
                    raster.append(element)
            elif isinstance(element, SVGImage):
                # TODO: Add SVGImages to overall Raster
                rasters.append(RasterOperation(element))
            elif isinstance(element, SVGText):
                pass  # I can't process actual text.
        rasters = [r for r in rasters if len(r) != 0]
        engraves = [r for r in engraves if len(r) != 0]
        cuts = [r for r in cuts if len(r) != 0]
        ops = []
        ops.extend(rasters)
        ops.extend(engraves)
        ops.extend(cuts)
        self.operations.extend(ops)
        return ops

    def load(self, pathname):
        for loader_name, loader in self.registered_loaders.items():
            for description, extensions, mimetype in loader.load_types():
                if pathname.lower().endswith(extensions):
                    results = loader.load(self, pathname)
                    if results is None:
                        continue
                    elements, pathname, basename = results
                    self.filenodes[pathname] = elements
                    self.elements.extend(elements)
                    self.signal('rebuild_tree', elements)
                    return elements, pathname, basename
        return None

    def load_types(self, all=True):
        filetypes = []
        if all:
            filetypes.append('All valid types')
            exts = []
            for loader_name, loader in self.registered_loaders.items():
                for description, extensions, mimetype in loader.load_types():
                    for ext in extensions:
                        exts.append('*.%s' % ext)
            filetypes.append(';'.join(exts))
        for loader_name, loader in self.registered_loaders.items():
            for description, extensions, mimetype in loader.load_types():
                exts = []
                for ext in extensions:
                    exts.append('*.%s' % ext)
                filetypes.append("%s (%s)" % (description, extensions[0]))
                filetypes.append(';'.join(exts))
        return "|".join(filetypes)

    def save(self, pathname):
        for save_name, saver in self.registered_savers.items():
            for description, extension, mimetype in saver.save_types():
                if pathname.lower().endswith(extension):
                    saver.save(self, pathname, 'default')
                    return True
        return False

    def save_types(self):
        filetypes = []
        for saver_name, saver in self.registered_savers.items():
            for description, extension, mimetype in saver.save_types():
                filetypes.append("%s (%s)" % (description, extension))
                filetypes.append("*.%s" % (extension))
        return "|".join(filetypes)
