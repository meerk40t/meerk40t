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


class Module:
    """
    Modules are a generic lifecycle object. When attached they are initialized to that device. When that device
    is shutdown, the shutdown() event is called. This permits the knowing registering and unregistering of
    other kernel objects. and the attachment of the module to a device.

    Registered Modules are notified of the activation and deactivation of their device.

    Modules can also be scheduled in the kernel to run at a particular time and a given number of times.
    """

    def __init__(self, name=None, device=None, process=None, args=(), interval=1.0, times=None):
        self.name = name
        self.device = device

        self.interval = interval
        self.last_run = None
        self.next_run = time.time() + self.interval

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

    def schedule(self):
        if self not in self.device.jobs:
            self.device.jobs.append(self)

    def attach(self, device, name=None):
        self.device = device
        self.name = name
        self.initialize()

    def detach(self, device, channel=None):
        try:
            if self.name is not None and self.name in device.module_instances:
                del device.module_instances[self.name]
        except KeyError:
            pass
        self.shutdown(channel)
        self.device = None

    def initialize(self):
        pass

    def shutdown(self, channel):
        pass

    def activated(self, device):
        pass

    def deactivated(self, device):
        pass


class Spooler(Module):
    """
    The spooler stores spoolable lasercode events, as a synchronous queue.

    Spooler registers itself as the device.spooler and provides a standard location to send data to an unknown device.

    * Peek()
    * Pop()
    * Send_Job()
    * Clear_Queue()
    """

    def __init__(self):
        Module.__init__(self)
        self.queue_lock = Lock()
        self.queue = []

    def __repr__(self):
        return "Spooler()"

    def attach(self, device, name=None):
        Module.attach(self, device, name)
        self.device.spooler = self
        self.initialize()

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
        self.device.signal("spooler;queue", len(self.queue))

    def send_job(self, element):
        self.queue_lock.acquire(True)
        if isinstance(element, (list, tuple)):
            self.queue += element
        else:
            self.queue.append(element)
        self.queue_lock.release()
        self.device.signal("spooler;queue", len(self.queue))

    def clear_queue(self):
        self.queue_lock.acquire(True)
        self.queue = []
        self.queue_lock.release()
        self.device.signal("spooler;queue", len(self.queue))


class Interpreter(Module):
    """
    An Interpreter takes spoolable commands and turns those commands into states and code in a language
    agnostic fashion. This is intended to be overridden by a subclass or class with the required methods.
    """
    def __init__(self, pipe=None):
        Module.__init__(self)
        self.process_item = None
        self.spooled_item = None
        self.process = self.process_spool
        self.interval = 0.01
        self.pipe = pipe

    def attach(self, device, name=None):
        Module.attach(self, device, name)
        self.device.interpreter = self
        self.initialize()
        self.schedule()

    def hold(self):
        return False

    def command(self, command, *values):
        """Commands are middle language LaserCommandConstants there values are given."""
        return NotImplementedError

    def realtime_command(self, command, *values):
        """Asks for the execution of a realtime command. Unlike the spooled commands these
        return False if rejected and something else if able to be performed. These will not
        be queued. If rejected. They must be performed in realtime or cancelled.
        """
        if command == COMMAND_PAUSE:
            self.paused = True
        elif command == COMMAND_RESUME:
            self.paused = False
        elif command == COMMAND_RESET:
            self.device.spooler.clear_queue()
        elif command == COMMAND_CLOSE:
            self.times = -1
        return self.command(command, *values)

    def process_spool(self, *args):
        """
        Get next spooled element if needed.
        Calls execute.

        :param args:
        :return:
        """
        if self.spooled_item is None:
            self.fetch_next_item()
        if self.spooled_item is not None:
            self.execute()

    def execute(self):
        """
        Default process to run entire command as a single call.
        """
        if self.spooled_item is None:
            return
        if isinstance(self.spooled_item, tuple):
            self.command(self.spooled_item[0], *self.spooled_item[1:])
            self.spooled_item = None
            return
        try:
            e = next(self.spooled_item)
            if isinstance(e, int):
                self.command(e)
            else:
                self.command(e[0], *e[1:])
        except StopIteration:
            self.spooled_item = None

    def fetch_next_item(self):
        element = self.device.spooler.peek()
        if element is None:
            return  # Spooler is empty.

        self.device.spooler.pop()

        if isinstance(element, tuple):
            self.spooled_item = element
        else:
            try:
                self.spooled_item = element.generate()
            except AttributeError:
                self.spooled_item = element()


class Pipe:
    """
    Write dataflow in the kernel. Provides general information about buffer size in through len() builtin.
    Pipes have write and realtime_write functions.
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


class Signaler(Module):
    def __init__(self):
        Module.__init__(self)
        self.listeners = {}
        self.adding_listeners = []
        self.removing_listeners = []
        self.last_message = {}
        self.queue_lock = Lock()
        self.message_queue = {}
        self._is_queue_processing = False
        self.process = self.delegate_messages
        self.interval = 0.05
        self.args = ()

    def attach(self, device, name=None):
        Module.attach(self, device, name)
        self.device.signal = self.signal
        self.device.listen = self.listen
        self.device.unlisten = self.unlisten
        self.device.last_signal = self.last_signal
        self.schedule()

    def shutdown(self,  shutdown):
        for key, listener in self.listeners.items():
            if len(listener):
                shutdown(_("WARNING: Listener '%s' still registered to %s.\n") % (key, str(listener)))
        self.last_message = {}
        self.listeners = {}

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
        if self.device.run_later is not None:
            self.device.run_later(self.process_queue, None)
        else:
            self.process_queue(None)

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


class Device(Thread):
    """
    A Device is a specific module cluster that serves a unified purpose.

    * Provides job scheduler
    * Registers devices, modules, pipes, modifications, and effects.
    * Stores instanced devices, modules, pipes, channels, controls and threads.
    * Processes localized signals.
    """

    def __init__(self, root=None, uid=''):
        Thread.__init__(self, name=uid + 'KernelThread')
        self.daemon = True
        self.device_root = root
        self.uid = uid

        self.state = THREAD_STATE_UNKNOWN
        self.jobs = []

        # Instanceable Kernel Objects
        self.registered_devices = {}
        self.registered_modules = {}
        self.registered_pipes = {}
        self.registered_modifications = {}
        self.registered_effects = {}

        # Active Kernel Object Instances
        self.device_instances = {}
        self.module_instances = {}
        self.pipe_instances = {}

        self.control_instances = {}
        self.thread_instances = {}

        # Channel processing.
        self.channels = {}
        self.watchers = {}
        self.greet = {}

    def __str__(self):
        if self.uid is None:
            return "Project"
        else:
            return self.uid

    def __call__(self, code, *message):
        self.signal(code, *message)

    def __setitem__(self, key, value):
        """
        Kernel value settings. If Config is registered this will be persistent.

        :param key: Key to set.
        :param value: Value to set
        :return: None
        """
        if isinstance(key, str):
            self.write_persistent(key, value)

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
                return self.read_persistent(t, key)
            else:
                t, key, default = item
                return self.read_persistent(t, key, default)
        return self.read_item_persistent(item)

    def get(self, key):
        key = self.uid + key
        if hasattr(self.device_root, key):
            return getattr(self.device_root, key)

    def read_item_persistent(self, item):
        return self.device_root.read_item_persistent(item)

    def write_persistent(self, key, value):
        self.device_root.write_persistent(key, value)

    def read_persistent(self, t, key, default=None):
        return self.device_root.read_persistent(t, key, default)

    def boot(self):
        """
        Kernel boot sequence. This should be called after all the registered devices are established.
        :return:
        """
        if not self.is_alive():
            self.start()

    def shutdown(self, shutdown):
        """
        Begins device shutdown procedure.

        Checks if shutdown should be done.
        Save Kernel Persistent settings.
        Save Device Persistent settings.
        Closes all windows.
        Ask all modules to shutdown.
        Wait for threads to end.
        -- If threads do not end, threads must be aborted.
        Notifies of listener errors.
        """
        self.state = THREAD_STATE_ABORT
        _ = self.device_root.translation
        shutdown(_("Shutting down.\n"))
        self.flush()
        for device_name in self.device_instances:
            device = self.device_instances[device_name]
            shutdown(_("Device Shutdown Started: '%s'\n") % str(device))
            device.shutdown(shutdown)
            shutdown(_("Device Shutdown Finished: '%s'\n") % str(device))
            shutdown(_("Saving Device State: '%s'\n") % str(device))
            device.flush()
        self.flush()
        for module_name in list(self.module_instances):
            module = self.module_instances[module_name]
            shutdown(_("Shutting down %s module: %s\n") % (module_name, str(module)))
            try:
                module.detach(self, channel=shutdown)
            except AttributeError:
                pass
        for module_name in self.module_instances:
            module = self.module_instances[module_name]
            shutdown(_("WARNING: Module %s was not closed.\n") % (module_name))
        for thread_name in self.thread_instances:
            thread = self.thread_instances[thread_name]
            if not thread.is_alive:
                shutdown(_("WARNING: Dead thread %s still registered to %s.\n") % (thread_name, str(thread)))
                continue
            shutdown(_("Finishing Thread %s for %s\n") % (thread_name, str(thread)))
            if thread is self:
                continue
                # Do not sleep thread waiting for devicethread to die. This is devicethread.
            try:
                thread.stop()
            except AttributeError:
                pass
            if thread.is_alive:
                shutdown(_("Waiting for thread %s: %s\n") % (thread_name, str(thread)))
            while thread.is_alive():
                time.sleep(0.1)
            shutdown(_("Thread %s finished. %s\n") % (thread_name, str(thread)))
        shutdown(_("Shutdown.\n"))

    def add_job(self, run, args=(), interval=1.0, times=None):
        """
        Adds a job to the scheduler.

        :param run: function to run
        :param args: arguments to give to that function.
        :param interval: in seconds, how often should the job be run.
        :param times: limit on number of executions.
        :return: Reference to the job added.
        """
        job = Module(self, process=run, args=args, interval=interval, times=times)
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
            jobs = self.jobs
            jobs_update = False
            for job in jobs:
                # Checking if jobs should run.
                if job.scheduled:
                    job.next_run = 0  # Set to zero while running.
                    if job.times is not None:
                        job.times = job.times - 1
                        if job.times <= 0:
                            jobs_update = True
                        if job.times < 0:
                            continue
                    if isinstance(job.args, tuple):
                        job.process(*job.args)
                    else:
                        job.process(job.args)
                    job.last_run = time.time()
                    job.next_run += job.last_run + job.interval
            if jobs_update:
                self.jobs = [job for job in jobs if job.times is not None and job.times > 0]
        self.state = THREAD_STATE_FINISHED

        # If we aborted the thread, we trigger Kernel Shutdown in this thread.
        self.shutdown(self.channel_open('shutdown'))

    def _start_debugging(self):
        """
        Debug function hooks all functions within the device with a debug call that saves the data to the disk and
        prints that information.

        :return:
        """
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
        attach_list = [modules for modules, module_name in self.module_instances.items()]
        attach_list.append(self)
        for obj in attach_list:
            for attr in dir(obj):
                if attr.startswith('_'):
                    continue
                fn = getattr(obj, attr)
                if not isinstance(fn, types.FunctionType) and \
                        not isinstance(fn, types.MethodType):
                    continue
                setattr(obj, attr, debug(fn, obj))

    def close(self):
        self.flush()

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
        if self.uid is not None:
            setting_uid_name = self.uid + setting_name
        else:
            setting_uid_name = setting_name
        if hasattr(self, setting_name) and getattr(self, setting_name) is not None:
            return
        if not setting_name.startswith('_'):
            load_value = self.read_persistent(setting_type, setting_uid_name, default)
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
            if self.uid is not None:
                uid_attr = self.uid + attr
            else:
                uid_attr = attr
            if isinstance(value, (int, bool, str, float)):
                self.write_persistent(uid_attr, value)

    def update(self, setting_name, value):
        if hasattr(self, setting_name):
            old_value = getattr(self, setting_name)
        else:
            old_value = None
        setattr(self, setting_name, value)
        self(setting_name, (value, old_value))

    def execute(self, control_name, *args):
        if self.uid is not None:
            self.control_instances[self.uid + control_name](*args)
        else:
            self.control_instances[control_name](*args)

    def signal(self, code, *message):
        if self.uid is not None:
            code = self.uid + ';' + code
        if self.device_root is not None and self.device_root is not self:
            self.device_root.signal(code, *message)

    def listen(self, signal, funct):
        if self.uid is not None:
            signal = self.uid + ';' + signal
        if self.device_root is not None and self.device_root is not self:
            self.device_root.listen(signal, funct)

    def unlisten(self, signal, funct):
        if self.uid is not None:
            signal = self.uid + ';' + signal
        if self.device_root is not None and self.device_root is not self:
            self.device_root.unlisten(signal, funct)

    # Channel processing

    def add_greet(self, channel, greet):
        self.greet[channel] = greet
        if channel in self.channels:
            self.channels[channel](greet)

    def add_watcher(self, channel, monitor_function):
        if channel not in self.watchers:
            self.watchers[channel] = [monitor_function]
        else:
            self.watchers[channel].append(monitor_function)
        if channel in self.greet:
            monitor_function(self.greet[channel])

    def remove_watcher(self, channel, monitor_function):
        self.watchers[channel].remove(monitor_function)

    def channel_open(self, channel):
        if channel not in self.channels:
            def chan(message):
                if channel in self.watchers:
                    for w in self.watchers[channel]:
                        w(message)
            self.channels[channel] = chan
            if channel in self.greet:
                chan(self.greet[channel])
        return self.channels[channel]

    # Kernel object registration

    def register_module(self, name, obj):
        self.registered_modules[name] = obj

    def register_device(self, name, obj):
        self.registered_devices[name] = obj

    def register_pipe(self, name, obj):
        self.registered_pipes[name] = obj

    def register_modification(self, name, obj):
        self.registered_modifications[name] = obj

    def register_effect(self, name, obj):
        self.registered_effects[name] = obj

    # Device kernel object

    def is_root(self):
        return self.device_root is None or self.device_root is self

    def device_instance_open(self, device_name, instance_name=None, **kwargs):
        if instance_name is None:
            instance_name = device_name
        device_object = self.registered_devices[device_name]
        device_instance = device_object(self, **kwargs)
        self.device_instances[instance_name] = device_instance
        device_instance.initialize(self, name=instance_name)
        device_instance.boot()
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

    # Module kernel objects

    def module_instance_open(self, module_name, *args, instance_name=None, **kwargs):
        if instance_name is None:
            instance_name = module_name
        if self.device_root is None or self.device_root is self:
            module_object = self.registered_modules[module_name]
        else:
            module_object = self.device_root.registered_modules[module_name]
        module_instance = module_object(*args, **kwargs)
        module_instance.attach(self, name=instance_name)
        self.module_instances[instance_name] = module_instance
        return module_instance

    def module_instance_close(self, name):
        if name in self.module_instances:
            self.module_instances[name].detach(self)
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

    # Control kernel object. Registered function calls.

    def control_instance_add(self, control_name, function):
        self.control_instances[control_name] = function

    def control_instance_remove(self, control_name):
        del self.control_instances[control_name]

    # Thread kernel object. Registered Threads.

    def thread_instance_add(self, thread_name, obj):
        self.thread_instances[thread_name] = obj

    def thread_instance_remove(self, thread_name):
        del self.thread_instances[thread_name]

    def get_text_thread_state(self, state):
        _ = self.device_root.translation
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

    def classify(self, elements):
        return self.device_root.classify(elements)

    def load(self, pathname):
        return self.device_root.load(pathname)

    def load_types(self, all=True):
        return self.device_root.load_types(all)

    def save(self, pathname):
        return self.device_root.save(pathname)

    def save_types(self):
        return self.device_root.save_types()


class Kernel(Device):
    """
    The Kernel is the device root object. It stores device independent settings, values, and functions.

    * It is itself a type of device. It has no root, and should be the DeviceRoot.
    * Shared location of loaded elements data
    * Registered loaders and savers.
    * The persistent storage object
    * The translation function
    * The run later function
    * The keymap object

    """

    def __init__(self, config=None):
        Device.__init__(self, self, '')
        # Current Project.
        self.root = self
        self.uid = None

        # Active Device
        self.device = None

        # Elements
        self.elements = []
        self.operations = []
        self.filenodes = {}

        # Persistent storage if it exists.
        self.config = None
        if config is not None:
            self.set_config(config)

        # Translation function if exists.
        self.translation = lambda e: e  # Default for this code is do nothing.

        # Keymap values
        self.keymap = {}

        # Static Kernel Objects
        self.registered_loaders = {}
        self.registered_savers = {}

        self.run_later = lambda listener, message: listener(message)

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
        Device.boot(self)
        self.module_instance_open('Signaler')

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

    def shutdown(self, shutdown):
        """
        Begins kernel shutdown procedure.
        """
        Device.shutdown(self, shutdown)

        if self.config is not None:
            self.config.Flush()

    def read_item_persistent(self, item):
        return self.config.Read(item)

    def read_persistent(self, t, key, default=None):
        if self.config is None:
            return default
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

    def write_persistent(self, key, value):
        if self.config is None:
            return
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
                self.write_persistent(attr, value)
        more, value, index = config.GetFirstEntry()
        while more:
            if not value.startswith('_'):
                if not hasattr(self, value):
                    setattr(self, value, None)
            more, value, index = config.GetNextEntry(index)

    def activate_device(self, device_name):
        """
        Switch the activated device in the kernel.

        :param device_name:
        :return:
        """
        original = self.device
        if device_name is None:
            self.device = None
        else:
            self.device = self.device_instances[device_name]
        if self.device is not original:
            if original is not None:
                for module_name in original.module_instances:
                    module = original.module_instances[module_name]
                    module.deactivated(original)
            if self.device is not None:
                for module_name in self.device.module_instances:
                    module = self.device.module_instances[module_name]
                    module.activated(original)
            self.signal("device", self.device)

    # Element processing and alterations.

    def register_loader(self, name, obj):
        self.registered_loaders[name] = obj

    def register_saver(self, name, obj):
        self.registered_savers[name] = obj

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
