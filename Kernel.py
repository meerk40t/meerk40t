import time
from threading import *

from LaserOperation import *
from svgelements import Path, SVGElement

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
        if isinstance(self.args, tuple):
            self.process(*self.args)
        else:
            self.process(self.args)
        self.last_run = time.time()
        self.next_run = self.last_run + self.interval


class Scheduler(Thread):
    def __init__(self, kernel):
        Thread.__init__(self, name='Meerk40t-Scheduler')
        self.daemon = True
        self.kernel = kernel
        self.state = THREAD_STATE_UNSTARTED
        self.jobs = []

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
        self.kernel.shutdown()

    def state(self):
        return self.state

    def resume(self):
        self.state = THREAD_STATE_STARTED

    def pause(self):
        self.state = THREAD_STATE_PAUSED

    def stop(self):
        self.state = THREAD_STATE_ABORT


class Module:
    def __init__(self):
        self.kernel = None
        self.name = None

    def initialize(self, kernel, name=None):
        self.kernel = kernel
        self.name = name

    def shutdown(self, kernel):
        self.kernel = None


class Backend:
    def __init__(self, kernel=None, uid=None):
        self.kernel = kernel
        self.uid = uid

    def create_device(self, uid):
        pass


class Device:
    def __init__(self, kernel=None, uid=None, spooler=None, interpreter=None, pipe=None):
        self.kernel = kernel
        self.uid = uid
        self.spooler = spooler
        self.interpreter = interpreter
        self.pipe = pipe
        self.device_log = ''
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
                kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
                start = f"Calling {obj}.{func.__name__}({signature})"
                debug_file.write(start + '\n')
                print(start)
                t = time.time()
                value = func(*args, **kwargs)
                t = time.time() - t
                finish = f"    {func.__name__!r} returned {value!r} after {t * 1000}ms"
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
        self.device_log += message
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

    def add_thread(self, name, thread):
        self.kernel.add_thread(self.uid + name, thread)

    def add_control(self, name, control):
        self.kernel.add_control(self.uid + name, control)


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
        command_index = 0
        self.set_state(THREAD_STATE_STARTED)
        try:
            self.spooler.device.hold()
            while True:
                element = self.spooler.peek()
                if element is None:
                    break  # Nothing left in spooler.
                self.spooler.device.hold()
                try:
                    gen = element.generate
                except AttributeError:
                    gen = element
                for e in gen():
                    if isinstance(e, (tuple, list)):
                        command = e[0]
                        if len(e) >= 2:
                            values = e[1:]
                        else:
                            values = [None]
                    else:
                        command = e
                        values = [None]
                    command_index += 1
                    if self.state == THREAD_STATE_ABORT:
                        break
                    self.spooler.device.hold()
                    self.spooler.execute(command, *values)
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
    Write location in the kernel. Provides general information about buffer size but is
    agnostic as to where the code ends up.

    Example pipes are mock, file, print, libusb-driver, and ch341-win. (these may or maynot exist).
    """

    def __init__(self, device=None):
        self.device = device

    def __len__(self):
        return 0

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def name(self):
        return NotImplementedError

    def open(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def write(self, bytes_to_write):
        raise NotImplementedError

    def read(self, size=-1):
        """Most pipes will be outstreams but some could provide data through this method."""
        raise NotImplementedError

    def realtime_write(self, bytes_to_write):
        """
        This method shall be permitted to not exist.
        To facilitate pipes being easily replaced with filelike objects, any calls
        to this method should assume pipe may not have this command.
        """
        self.write(bytes_to_write)


class Kernel:
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
        self.elements = []
        self.operations = []

        self.config = None

        self.modules = {}
        self.loaders = {}
        self.savers = {}
        self.threads = {}
        self.controls = {}
        self.windows = {}
        self.open_windows = {}

        self.backends = {}

        self.devices = {}
        self.device = None

        self.effects = []
        self.listeners = {}
        self.adding_listeners = []
        self.removing_listeners = []
        self.last_message = {}
        self.queue_lock = Lock()
        self.message_queue = {}
        self.is_queue_processing = False

        self.run_later = lambda listener, message: listener(message)
        self.shutdown_watcher = lambda i, e, o: True
        self.translation = lambda e: e  # Default for this code is do nothing.

        self.keymap = {}

        if config is not None:
            self.set_config(config)
        self.cron = None

    def __str__(self):
        return "Project"

    def __call__(self, code, *message):
        self.signal(code, message)

    def signal(self, code, *message):
        self.queue_lock.acquire(True)
        self.message_queue[code] = message
        self.queue_lock.release()

    def delegate_messages(self):
        if self.is_queue_processing:
            return
        self.run_later(self.process_queue, None)

    def process_queue(self, *args):
        if len(self.message_queue) == 0 and len(self.adding_listeners) == 0 and len(self.removing_listeners) == 0:
            return
        self.is_queue_processing = True
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
            # if 'spooler' in code:
            #     print("%s : %s" % (code,message))
            if code in self.listeners:
                listeners = self.listeners[code]
                for listener in listeners:
                    listener(*message)
            self.last_message[code] = message
        self.is_queue_processing = False

    def __setitem__(self, key, value):
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
        if isinstance(item, tuple):
            if len(item) == 2:
                t, key = item
                return self.read_config(t, key)
            else:
                t, key, default = item
                return self.read_config(t, key, default)
        return self.config.Read(item)

    def boot(self):
        if self.cron is None or not self.cron.is_alive():
            self.cron = Scheduler(self)
            self.cron.add_job(self.delegate_messages, args=(), interval=0.05)
            self.add_thread('Scheduler', self.cron)
            self.cron.start()

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
        for device_name in self.devices:
            device = self.devices[device_name]
            if kill(SHUTDOWN_FLUSH, device_name, device):
                device.flush()
        windows = list(self.open_windows)
        for i in range(0, len(windows)):
            window_name = windows[i]
            window = self.open_windows[window_name]
            if kill(SHUTDOWN_WINDOW, window_name, window):
                try:
                    window.Close()
                except AttributeError:
                    pass

        for window_name in list(self.open_windows):
            window = self.open_windows[window_name]
            kill(SHUTDOWN_WINDOW_ERROR, window_name, window)

        for module_name in list(self.modules):
            module = self.modules[module_name]
            if kill(SHUTDOWN_MODULE, module_name, module):
                try:
                    module.shutdown(self)
                except AttributeError:
                    pass
        for module_name in self.modules:
            module = self.modules[module_name]
            kill(SHUTDOWN_MODULE_ERROR, module_name, module)

        for thread_name in self.threads:
            thread = self.threads[thread_name]
            if not thread.is_alive:
                kill(SHUTDOWN_THREAD_ERROR, thread_name, thread)
                continue
            if kill(SHUTDOWN_THREAD, thread_name, thread):
                if thread is self.cron:
                    continue
                    # Do not sleep thread waiting for cron thread to die. This is the cron thread.
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

        If the setting exists, it's value remains unchanged.
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

    def add_window(self, window_name, window):
        self.windows[window_name] = window

    def mark_window_closed(self, name):
        if name in self.open_windows:
            del self.open_windows[name]

    def close_old_window(self, name):
        if name in self.open_windows:
            try:
                self.open_windows[name].Close()
            except RuntimeError:
                pass  # already closed.
        self.mark_window_closed(name)

    def open_window(self, window_name):
        self.close_old_window(window_name)
        w = self.windows[window_name]
        window = w(None, -1, "")
        window.Show()
        window.set_kernel(self)
        self.open_windows[window_name] = window
        return window

    def listen(self, signal, funct):
        self.queue_lock.acquire(True)
        self.adding_listeners.append((signal, funct))
        self.queue_lock.release()

    def unlisten(self, signal, funct):
        self.queue_lock.acquire(True)
        self.removing_listeners.append((signal, funct))
        self.queue_lock.release()

    def add_module(self, module_name, module):
        self.modules[module_name] = module
        module.initialize(self, name=module_name)

    def remove_module(self, module_name):
        del self.modules[module_name]

    def add_loader(self, loader_name, loader):
        self.loaders[loader_name] = loader

    def add_saver(self, saver_name, saver):
        self.savers[saver_name] = saver

    def add_backend(self, backend_name, backend):
        self.backends[backend_name] = backend

    def add_device(self, device_name, device):
        self.devices[device_name] = device

    def activate_device(self, device_name):
        if device_name is None:
            self.device = None
        else:
            self.device = self.devices[device_name]
        self.signal("device", self.device)

    def add_control(self, control_name, function):
        self.controls[control_name] = function

    def remove_control(self, control_name):
        del self.controls[control_name]

    def execute(self, control_name, *args):
        self.controls[control_name](*args)

    def add_thread(self, thread_name, object):
        self.threads[thread_name] = object

    def remove_thread(self, thread_name):
        del self.threads[thread_name]

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
            return self.threads[thread_name].state()
        except AttributeError:
            return THREAD_STATE_UNKNOWN

    def start(self, thread_name):
        try:
            self.modules[thread_name].start()
        except AttributeError:
            pass

    def resume(self, thread_name):
        try:
            self.modules[thread_name].resume()
        except AttributeError:
            pass

    def pause(self, thread_name):
        try:
            self.modules[thread_name].pause()
        except AttributeError:
            pass

    def abort(self, thread_name):
        try:
            self.modules[thread_name].abort()
        except AttributeError:
            pass

    def reset(self, thread_name):
        try:
            self.modules[thread_name].reset()
        except AttributeError:
            pass

    def stop(self, thread_name):
        try:
            self.modules[thread_name].stop()
        except AttributeError:
            pass

    def remove_element_from_operations(self, element):
        for q in self.operations:
            if element in q:
                q.remove(element)

    def remove_orphaned_operations(self):
        for q in list(self.operations):
            if len(q) == 0:
                self.operations.remove(q)

    def classify(self, elements):
        """
        Classify does the initial placement of elements as operations.
        RasterOperation is the default for images.
        If element strokes are red they get classed as cut operations
        If they are otherwise they get classed as engrave.
        """
        if elements is None:
            return
        ops = []
        for element in elements:
            if isinstance(element, SVGImage):
                ops.append(RasterOperation(element))
            elif isinstance(element, Path):
                if element.stroke == "red":
                    ops.append(CutOperation(element))
                else:
                    ops.append(EngraveOperation(element))
        self.operations.extend(ops)
        return ops

    def load(self, pathname):
        for loader_name, loader in self.loaders.items():
            for description, extensions, mimetype in loader.load_types():
                if pathname.lower().endswith(extensions):
                    results = loader.load(pathname)
                    if results is None:
                        continue
                    elements, pathname, basename = results
                    self.elements.extend(elements)
                    self('elements', elements)
                    return elements, pathname, basename
        return None

    def load_types(self, all=True):
        filetypes = []
        if all:
            filetypes.append('All valid types')
            exts = []
            for loader_name, loader in self.loaders.items():
                for description, extensions, mimetype in loader.load_types():
                    for ext in extensions:
                        exts.append('*.%s' % ext)
            filetypes.append(';'.join(exts))
        for loader_name, loader in self.loaders.items():
            for description, extensions, mimetype in loader.load_types():
                exts = []
                for ext in extensions:
                    exts.append('*.%s' % ext)
                filetypes.append("%s (%s)" % (description, extensions[0]))
                filetypes.append(';'.join(exts))
        return "|".join(filetypes)

    def save(self, pathname):
        for save_name, saver in self.savers.items():
            for description, extension, mimetype in saver.save_types():
                if pathname.lower().endswith(extension):
                    saver.save(pathname, 'default')
                    return True
        return False

    def save_types(self):
        filetypes = []
        for saver_name, saver in self.savers.items():
            for description, extension, mimetype in saver.save_types():
                filetypes.append("%s (%s)" % (description, extension))
                filetypes.append("*.%s" % (extension))
        return "|".join(filetypes)
