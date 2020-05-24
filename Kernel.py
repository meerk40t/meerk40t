import time
from threading import Thread, Lock

from LaserOperation import *
from svgelements import Path, SVGText

THREAD_STATE_UNKNOWN = -1
THREAD_STATE_UNSTARTED = 0
THREAD_STATE_STARTED = 1
THREAD_STATE_PAUSED = 2
THREAD_STATE_FINISHED = 3
THREAD_STATE_ABORT = 10

INTERPRETER_STATE_RAPID = 0
INTERPRETER_STATE_FINISH = 1
INTERPRETER_STATE_PROGRAM = 2


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

    def unschedule(self):
        if self in self.device.jobs:
            self.device.jobs.remove(self)

    def attach(self, device, name=None):
        self.device = device
        self.name = name
        self.initialize()

    def detach(self, device, channel=None):
        try:
            if self.name is not None and self.name in device.instances['module']:
                del device.instances['module'][self.name]
        except KeyError:
            pass
        self.shutdown(channel)
        self.device = None

    def initialize(self):
        pass

    def shutdown(self, channel):
        pass


class Spooler(Module):
    """
    The spooler module stores spoolable lasercode events, as a synchronous queue.

    Spooler registers itself as the device.spooler object and provides a standard location to send data to an unknown device.

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
    An Interpreter Module takes spoolable commands and turns those commands into states and code in a language
    agnostic fashion. This is intended to be overridden by a subclass or class with the required methods.

    Interpreters register themselves as device.interpreter objects.
    Interpreters expect the device.spooler object exists to provide spooled commands as needed.

    These modules function to interpret hardware specific backend information from the reusable spoolers and server
    objects that may also be common within devices.
    """

    def __init__(self, pipe=None):
        Module.__init__(self)
        self.process_item = None
        self.spooled_item = None
        self.process = self.process_spool
        self.interval = 0.01
        self.pipe = pipe
        self.extra_hold = None

        self.state = INTERPRETER_STATE_RAPID
        self.pulse_total = 0.0
        self.pulse_modulation = True
        self.properties = 0
        self.is_relative = False
        self.laser = False
        self.laser_enabled = True
        self.raster_step = 0
        self.overscan = 20
        self.speed = 30
        self.power = 1000.0
        self.d_ratio = None  # None means to use speedcode default.
        self.acceleration = None  # None means to use speedcode default

    def attach(self, device, name=None):
        Module.attach(self, device, name)
        self.device.interpreter = self
        self.device.setting(int, 'current_x', 0)
        self.device.setting(int, 'current_y', 0)
        self.initialize()
        self.schedule()

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
        if self.hold():
            return
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

    def command(self, command, *values):
        """Commands are middle language LaserCommandConstants there values are given."""
        try:
            if command == COMMAND_LASER_OFF:
                self.laser_on()
            elif command == COMMAND_LASER_ON:
                self.laser_off()
            elif command == COMMAND_LASER_DISABLE:
                self.laser_disable()
            elif command == COMMAND_LASER_ENABLE:
                self.laser_enable()
            elif command == COMMAND_MOVE:
                x, y = values
                self.move(x, y)
            elif command == COMMAND_HOME:
                self.home()
            elif command == COMMAND_LOCK:
                self.lock_rail()
            elif command == COMMAND_UNLOCK:
                self.unlock_rail()
            elif command == COMMAND_PLOT:
                self.plot_path(values[0])
            elif command == COMMAND_RASTER:
                self.plot_raster(values[0])
            elif command == COMMAND_SET_SPEED:
                self.set_speed(values[0])
            elif command == COMMAND_SET_POWER:
                self.set_power(values[0])
            elif command == COMMAND_SET_PPI:
                self.set_ppi(values[0])
            elif command == COMMAND_SET_PWM:
                self.set_pwm(values[0])
            elif command == COMMAND_SET_STEP:
                self.set_step(values[0])
            elif command == COMMAND_SET_OVERSCAN:
                self.set_overscan(values[0])
            elif command == COMMAND_SET_ACCELERATION:
                self.set_acceleration(values[0])
            elif command == COMMAND_SET_D_RATIO:
                self.set_d_ratio(values[0])
            elif command == COMMAND_SET_DIRECTION:
                self.set_directions(values[0], values[1], values[2], values[3])
            elif command == COMMAND_SET_INCREMENTAL:
                self.set_incremental()
            elif command == COMMAND_SET_ABSOLUTE:
                self.set_absolute()
            elif command == COMMAND_SET_POSITION:
                self.set_position(values[0], values[1])
            elif command == COMMAND_MODE_RAPID:
                self.ensure_rapid_mode()
            elif command == COMMAND_MODE_PROGRAM:
                self.ensure_program_mode()
            elif command == COMMAND_MODE_FINISHED:
                self.ensure_finished_mode()
            elif command == COMMAND_WAIT:
                self.wait(values[0])
            elif command == COMMAND_WAIT_FINISH:
                self.wait_finish()
            elif command == COMMAND_BEEP:
                print('\a')  # Beep.
            elif command == COMMAND_FUNCTION:
                if len(values) >= 1:
                    t = values[0]
                    if callable(t):
                        t()
            elif command == COMMAND_SIGNAL:
                if isinstance(values, str):
                    self.device.signal(values, None)
                elif len(values) >= 2:
                    self.device.signal(values[0], *values[1:])
        except AttributeError:
            pass

    def realtime_command(self, command, *values):
        """Asks for the execution of a realtime command. Unlike the spooled commands these
        return False if rejected and something else if able to be performed. These will not
        be queued. If rejected. They must be performed in realtime or cancelled.
        """
        try:
            if command == REALTIME_PAUSE:
                self.pause()
            elif command == REALTIME_RESUME:
                self.resume()
            elif command == REALTIME_RESET:
                self.reset()
            elif command == REALTIME_STATUS:
                self.status()
            elif command == REALTIME_SAFETY_DOOR:
                self.safety_door()
            elif command == REALTIME_JOG_CANCEL:
                self.jog_cancel(*values)
            elif command == REALTIME_SPEED_PERCENT:
                self.realtime_speed_percent(*values)
            elif command == REALTIME_SPEED:
                self.realtime_speed(*values)
            elif command == REALTIME_RAPID_PERCENT:
                self.realtime_rapid_percent(*values)
            elif command == REALTIME_RAPID:
                self.realtime_rapid(*values)
            elif command == REALTIME_POWER_PERCENT:
                self.realtime_power_percent(*values)
            elif command == REALTIME_POWER:
                self.realtime_power(*values)
            elif command == REALTIME_OVERSCAN:
                self.realtime_overscan(*values)
            elif command == REALTIME_LASER_DISABLE:
                self.realtime_laser_disable(*values)
            elif command == REALTIME_LASER_ENABLE:
                self.realtime_laser_enable(*values)
            elif command == REALTIME_FLOOD_COOLANT:
                self.realtime_flood_coolant(*values)
            elif command == REALTIME_MIST_COOLANT:
                self.realtime_mist_coolant(*values)
        except AttributeError:
            pass  # Method doesn't exist.

    def hold(self):
        if self.extra_hold is not None:
            if self.extra_hold():
                return True
            else:
                self.extra_hold = None
        return False

    def laser_off(self, *values):
        self.laser = False

    def laser_on(self, *values):
        self.laser = True

    def laser_disable(self, *values):
        self.laser_enabled = False

    def laser_enable(self, *values):
        self.laser_enabled = True

    def move(self, x, y):
        self.device.current_x = x
        self.device.current_y = y

    def home(self, *values):
        self.device.current_x = 0
        self.device.current_y = 0

    def ensure_rapid_mode(self, *values):
        if self.state == INTERPRETER_STATE_RAPID:
            return
        self.state = INTERPRETER_STATE_RAPID
        self.device.signal('interpreter;mode', self.state)

    def ensure_finished_mode(self, *values):
        if self.state == INTERPRETER_STATE_FINISH:
            return
        self.state = INTERPRETER_STATE_FINISH
        self.device.signal('interpreter;mode', self.state)

    def ensure_program_mode(self, *values):
        if self.state == INTERPRETER_STATE_PROGRAM:
            return
        self.state = INTERPRETER_STATE_PROGRAM
        self.device.signal('interpreter;mode', self.state)

    def set_speed(self, speed=None):
        self.speed = speed

    def set_power(self, power=1000.0):
        self.power = power

    def set_ppi(self, power=1000.0):
        self.power = power

    def set_pwm(self, power=1000.0):
        self.power = power

    def set_d_ratio(self, d_ratio=None):
        self.d_ratio = d_ratio

    def set_acceleration(self, accel=None):
        self.acceleration = accel

    def set_step(self, step=None):
        self.raster_step = step

    def set_overscan(self, overscan=None):
        self.overscan = overscan

    def set_incremental(self, *values):
        self.is_relative = True

    def set_absolute(self, *values):
        self.is_relative = False

    def set_position(self, x, y):
        self.device.current_x = x
        self.device.current_y = y

    def wait(self, t):
        self.next_run = t

    def wait_finish(self, *values):
        """Adds an additional holding requirement if the pipe has any data."""
        self.extra_hold = lambda: len(self.pipe) != 0

    def reset(self):
        self.device.spooler.clear_queue()

    def status(self):
        parts = list()
        parts.append("x=%f" % self.device.current_x)
        parts.append("y=%f" % self.device.current_y)
        parts.append("speed=%f" % self.speed)
        parts.append("power=%d" % self.power)
        status = ";".join(parts)
        self.device.signal('interpreter;status', status)

    def set_prop(self, mask):
        self.properties |= mask

    def unset_prop(self, mask):
        self.properties &= ~mask

    def is_prop(self, mask):
        return bool(self.properties & mask)

    def toggle_prop(self, mask):
        if self.is_prop(mask):
            self.unset_prop(mask)
        else:
            self.set_prop(mask)


class Pipe:
    """
    Pipes are a generic file-like object with write commands and a realtime_write function.

    The realtime_write function should exist, but code using pipes should do so in a try block. Excepting
    the AttributeError if it doesn't exist. So that pipes are able to be exchanged for real file-like objects.

    Buffer size general information is provided through len() builtin.
    """

    def __len__(self):
        return 0

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        pass

    def close(self):
        pass

    def write(self, bytes_to_write):
        pass

    def realtime_write(self, bytes_to_write):
        """
        This method shall be permitted to not exist.
        To facilitate pipes being easily replaced with filelike objects, any calls
        to this method should assume pipe may not have this command.
        """
        self.write(bytes_to_write)


class Effect:
    """
    Effects are intended to be external program modifications of the data.
    None of these are implemented yet.

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
    Modifications are intended to be lazy implemented changes to SVGElement objects and groups. The intent is to
    provide a method for delayed modifications of data.

    Modifications are functions called on single SVGElement objects.
    Type Input is the input type kind of element this is intended to act upon.
    Type Output is the output type of the element this is intended to produce.
    """

    def __init__(self, input_type, output_type):
        self.input_type = input_type
        self.output_type = output_type


class Signaler(Module):
    """
    Signaler provides the signals functionality for a device. It replaces the functions for .signal(), .listen(),
    .unlisten(), .last_signal().
    """

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

    def shutdown(self, channel):
        _ = self.device.device_root.translation
        for key, listener in self.listeners.items():
            if len(listener):
                channel(_("WARNING: Listener '%s' still registered to %s.\n") % (key, str(listener)))
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

    The Kernel is a type of device which provides root functionality.

    * Provides job scheduler
    * Registers devices, modules, pipes, modifications, and effects.
    * Stores instanced devices, modules, pipes, channels, controls and threads.
    * Processes local channels.

    Channels are a device object with specific uids that sends messages to watcher functions. These can be watched
    even if the channels are not ever opened or used. The channels can opened and provided information without any
    consideration of what might be watching.
    """

    def __init__(self, root=None, uid=0):
        Thread.__init__(self, name='Device%d' % int(uid))
        self.device_root = root
        self.device_name = "Device"
        self.device_version = "0.0.0"
        self.location_name = "Kernel"
        self.uid = uid

        self.state = THREAD_STATE_UNKNOWN
        self.jobs = []

        self.registered = {}
        self.instances = {}

        # Channel processing.
        self.channels = {}
        self.watchers = {}
        self.buffer = {}
        self.greet = {}

    def __str__(self):
        if self.uid == 0:
            return "Project"
        else:
            return "%s:%d" % (self.device_name, self.uid)

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

    def attach(self, device, name=None):
        self.device_root = device
        self.name = name
        self.initialize(device)

    def detach(self, device, channel=None):
        if 'device' in self.device_root.instances:
            devices = self.device_root.instances['device']
            if self.uid in devices:
                del devices[self.uid]

    def initialize(self, device):
        pass

    def read_item_persistent(self, item):
        return self.device_root.read_item_persistent(item)

    def write_persistent(self, key, value, uid=0):
        self.device_root.write_persistent(key, value, uid=uid)

    def read_persistent(self, t, key, default=None, uid=0):
        return self.device_root.read_persistent(t, key, default, uid=uid)

    def boot(self):
        """
        Kernel boot sequence. This should be called after all the registered devices are established.
        :return:
        """
        if not self.is_alive():
            self.start()

    def shutdown(self, channel=None):
        """
        Begins device shutdown procedure.
        """
        self.state = THREAD_STATE_ABORT
        _ = self.device_root.translation
        channel(_("Shutting down.\n"))
        self.detach(self, channel=channel)
        if 'device' in self.instances:
            devices = self.instances['device']
            del self.instances['device']
            for device_name in devices:
                device = devices[device_name]
                channel(_("Device Shutdown Started: '%s'\n") % str(device))
                device.shutdown(channel=channel)
                channel(_("Device Shutdown Finished: '%s'\n") % str(device))
        channel(_("Saving Device State: '%s'\n") % str(self))
        self.flush()
        for type_name in list(self.instances):
            if type_name in ('control'):
                continue
            for module_name in list(self.instances[type_name]):
                module = self.instances[type_name][module_name]
                channel(_("Shutting down %s %s: %s\n") % (module_name, type_name, str(module)))
                try:
                    module.detach(self, channel=channel)
                except AttributeError:
                    pass
        for type_name in list(self.instances):
            if type_name in ('control'):
                continue
            for module_name in self.instances[type_name]:
                channel(_("WARNING: %s %s was not closed.\n") % (type_name, module_name))
        if 'thread' in self.instances:
            for thread_name in self.instances['thread']:
                thread = self.instances['thread'][thread_name]
                if not thread.is_alive:
                    channel(_("WARNING: Dead thread %s still registered to %s.\n") % (thread_name, str(thread)))
                    continue
                channel(_("Finishing Thread %s for %s\n") % (thread_name, str(thread)))
                if thread is self:
                    continue
                    # Do not sleep thread waiting for devicethread to die. This is devicethread.
                try:
                    thread.stop()
                except AttributeError:
                    pass
                if thread.is_alive:
                    channel(_("Waiting for thread %s: %s\n") % (thread_name, str(thread)))
                while thread.is_alive():
                    time.sleep(0.1)
                channel(_("Thread %s finished. %s\n") % (thread_name, str(thread)))
        else:
            channel(_("No threads required halting.\n"))
        channel(_("Shutdown.\n\n"))
        shutdown_root = False
        if not self.is_root():
            if 'device' in self.device_root.instances:
                root_devices = self.device_root.instances['device']
                if root_devices is None:
                    shutdown_root = True
                else:
                    if str(self.uid) in root_devices:
                        del root_devices[str(self.uid)]
                    if len(root_devices) == 0:
                        shutdown_root = True
            else:
                shutdown_root = True
        if shutdown_root:
            channel(_("All Devices are shutdown. Stopping Kernel.\n"))
            self.device_root.stop()

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
        self.shutdown(self.device_root.channel_open('shutdown'))

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
        attach_list = [modules for modules, module_name in self.instances['module'].items()]
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
        if self.uid != 0:
            setting_uid_name = '%s/%s' % (self.uid, setting_name)
        else:
            setting_uid_name = setting_name

        if hasattr(self, setting_name) and getattr(self, setting_name) is not None:
            return getattr(self, setting_name)
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
            if self.uid != 0:
                uid_attr = '%d/%s' % (self.uid, attr)
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
        self.instances['control'][control_name](*args)

    def signal(self, code, *message):
        if self.uid != 0:
            code = '%d;%s' % (self.uid, code)
        if self.device_root is not None and self.device_root is not self:
            self.device_root.signal(code, *message)

    def last_signal(self, signal):
        if self.uid != 0:
            signal = '%d;%s' % (self.uid, signal)
        if self.device_root is not None and self.device_root is not self:
            try:
                return self.device_root.last_signal(signal)
            except AttributeError:
                pass
        return None

    def listen(self, signal, funct):
        if self.uid != 0:
            signal = '%d;%s' % (self.uid, signal)
        if self.device_root is not None and self.device_root is not self:
            self.device_root.listen(signal, funct)

    def unlisten(self, signal, funct):
        if self.uid != 0:
            signal = '%d;%s' % (self.uid, signal)
        if self.device_root is not None and self.device_root is not self:
            self.device_root.unlisten(signal, funct)

    def state(self):
        return self.state

    def resume(self):
        self.state = THREAD_STATE_STARTED

    def pause(self):
        self.state = THREAD_STATE_PAUSED

    def stop(self):
        self.state = THREAD_STATE_ABORT

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
        if channel in self.buffer:
            for line in self.buffer[channel]:
                monitor_function(line)

    def remove_watcher(self, channel, monitor_function):
        self.watchers[channel].remove(monitor_function)

    def channel_open(self, channel, buffer=0):
        if channel not in self.channels:
            def chan(message):
                if channel in self.watchers:
                    for w in self.watchers[channel]:
                        w(message)
                if buffer <= 0:
                    return
                try:
                    buff = self.buffer[channel]
                except KeyError:
                    buff = list()
                    self.buffer[channel] = buff
                buff.append(message)
                if len(buff) + 10 > buffer:
                    self.buffer[channel] = buff[-buffer:]
            self.channels[channel] = chan
            if channel in self.greet:
                chan(self.greet[channel])
        return self.channels[channel]

    # Kernel object registration

    def register(self, object_type, name, obj):
        if object_type not in self.registered:
            self.registered[object_type] = {}
        self.registered[object_type][name] = obj
        try:
            obj.sub_register(self)
        except AttributeError:
            pass

    def register_module(self, name, obj):
        self.register('module', name, obj)

    def register_device(self, name, obj):
        self.register('device', name, obj)

    def register_pipe(self, name, obj):
        self.register('pipe', name, obj)

    def register_modification(self, name, obj):
        self.register('modification', name, obj)

    def register_effect(self, name, obj):
        self.register('effect', name, obj)

    # Device kernel object

    def is_root(self):
        return self.device_root is None or self.device_root is self

    def device_instance_open(self, device_name, instance_name=None, **kwargs):
        if instance_name is None:
            instance_name = device_name
        return self.open('device', device_name, self, instance_name=instance_name, **kwargs)

    def device_instance_close(self, name):
        self.close('device', name)

    def device_instance_remove(self, name):
        if name in self.instances['device']:
            del self.instances['device'][name]

    def using(self, type_name, object_name, *args, instance_name=None, **kwargs):
        if instance_name is None:
            instance_name = object_name
        if type_name in self.instances:
            if instance_name in self.instances[type_name]:
                return self.instances[type_name][instance_name]
        return self.open(type_name, object_name, *args, instance_name=instance_name, **kwargs)

    def open(self, type_name, object_name, *args, instance_name=None, **kwargs):
        if instance_name is None:
            instance_name = object_name
        if self.device_root is None or self.device_root is self:
            module_object = self.registered[type_name][object_name]
        else:
            module_object = self.device_root.registered[type_name][object_name]
        instance = module_object(*args, **kwargs)
        instance.attach(self, name=instance_name)
        self.add(type_name, instance_name, instance)
        return instance

    def close(self, type_name, name):
        if type_name in self.instances and name in self.instances[type_name]:
            obj = self.instances[type_name][name]
            try:
                obj.close()
            except AttributeError:
                pass
            obj.detach(self)
            if name in self.instances[type_name]:
                del self.instances[type_name][name]

    def add(self, type_name, name, instance):
        if type_name not in self.instances:
            self.instances[type_name] = {}
        self.instances[type_name][name] = instance

    def remove(self, type_name, name):
        if name in self.instances[type_name]:
            del self.instances[type_name][name]

    def module_instance_open(self, module_name, *args, instance_name=None, **kwargs):
        return self.open('module', module_name, *args, instance_name=instance_name, **kwargs )

    def module_instance_close(self, name):
        self.close('module', name)

    def module_instance_remove(self, name):
        self.remove('module', name)

    # Pipe kernel object

    def pipe_instance_open(self, pipe_name, instance_name=None, **kwargs):
        self.open('pipe', pipe_name, instance_name=instance_name, **kwargs)

    # Control kernel object. Registered function calls.

    def control_instance_add(self, control_name, function):
        self.add('control', control_name, function)

    def control_instance_remove(self, control_name):
        self.remove('control', control_name)

    # Thread kernel object. Registered Threads.

    def thread_instance_add(self, thread_name, obj):
        self.add('thread', thread_name, obj)

    def thread_instance_remove(self, thread_name):
        self.remove('thread', thread_name)

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
            return self.instances['thread'][thread_name].state()
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
        Device.__init__(self, self, 0)
        # Current Project.
        self.device_name = "MeerK40t"
        self.device_version = "0.6.0"
        self.device_root = self

        self.selected_elements = list()
        self.selected_operations = list()
        self.elements = []
        self.operations = []
        self.filenodes = {}

        # Persistent storage if it exists.
        self.config = None
        if config is not None:
            self.set_config(config)

        # Translation function if exists.
        self.translation = lambda e: e  # Default for this code is do nothing.

        # Keymap/alias values
        self.keymap = {}
        self.alias = {}

        self.run_later = lambda listener, message: listener(message)

        self.register_module('Signaler', Signaler)
        self.register_module('Spooler', Spooler)

    def boot(self):
        """
        Kernel boot sequence. This should be called after all the registered devices are established.
        :return:
        """
        Device.boot(self)
        self.default_keymap()
        self.default_alias()
        self.setting(str, 'list_devices', '')
        devices = self.list_devices
        for device in devices.split(';'):
            try:
                d = int(device)
            except ValueError:
                return
            device_name = self.read_persistent(str, 'device_name', 'Lhystudios', uid=d)
            autoboot = self.read_persistent(bool, 'autoboot', True, uid=d)
            if autoboot:
                dev = self.device_instance_open(device_name, uid=d, instance_name=str(device))
                dev.boot()

    def shutdown(self, channel=None):
        """
        Begins kernel shutdown procedure.
        """
        Device.shutdown(self, channel)

        if self.config is not None:
            self.config.Flush()

    def default_keymap(self):
        self.keymap["escape"] = "window open Adjustments"
        self.keymap["d"] = "+right"
        self.keymap["a"] = "+left"
        self.keymap["w"] = "+up"
        self.keymap["s"] = "+down"
        self.keymap['numpad_down'] = '+translate_down'
        self.keymap['numpad_up'] = '+translate_up'
        self.keymap['numpad_left'] = '+translate_left'
        self.keymap['numpad_right'] = '+translate_right'
        self.keymap['numpad*'] = '+scale_up'
        self.keymap['numpad/'] = '+scale_down'
        self.keymap['numpad+'] = '+rotate_cw'
        self.keymap['numpad-'] = '+rotate_ccw'
        self.keymap['control+shift+h'] = 'scale -1 1'
        self.keymap['control+shift+v'] = 'scale 1 -1'
        self.keymap['control+1'] = "bind 1 move $x $y"
        self.keymap['control+2'] = "bind 2 move $x $y"
        self.keymap['control+3'] = "bind 3 move $x $y"
        self.keymap['control+4'] = "bind 4 move $x $y"
        self.keymap['control+5'] = "bind 5 move $x $y"
        self.keymap['control+r'] = 'rect 0 0 1000 1000'
        self.keymap['control+e'] = 'circle 500 500 500'
        self.keymap['alt+r'] = 'raster'
        self.keymap['alt+e'] = 'engrave'
        self.keymap['alt+c'] = 'cut'
        self.keymap['control+f'] = 'control Fill'
        self.keymap['control+s'] = 'control Stroke'
        self.keymap['f4'] = "window open CameraInterface"
        self.keymap['f5'] = "refresh"
        self.keymap['f6'] = "window open JobSpooler"
        self.keymap['f7'] = "window open Controller"
        self.keymap['f8'] = "control Path"
        self.keymap['f9'] = "control Transform"
        self.keymap['f12'] = "window open Terminal"
        self.keymap['pause'] = "control Realtime Pause_Resume"

    def default_alias(self):
        self.alias['+scale_up'] = "loop scale 1.02"
        self.alias['+scale_down'] = "loop scale 0.98"
        self.alias['+rotate_cw'] = "loop rotate 2"
        self.alias['+rotate_ccw'] = "loop rotate -2"
        self.alias['+translate_right'] = "loop translate 1mm 0"
        self.alias['+translate_left'] = "loop translate -1mm 0"
        self.alias['+translate_down'] = "loop translate 0 1mm"
        self.alias['+translate_up'] = "loop translate 0 -1mm"
        self.alias['+right'] = "loop right 1mm"
        self.alias['+left'] = "loop left 1mm"
        self.alias['+up'] = "loop up 1mm"
        self.alias['+down'] = "loop down 1mm"
        self.alias['-scale_up'] = "end scale 1.02"
        self.alias['-scale_down'] = "end scale 0.98"
        self.alias['-rotate_cw'] = "end rotate 2"
        self.alias['-rotate_ccw'] = "end rotate -2"
        self.alias['-translate_right'] = "end translate 1mm 0"
        self.alias['-translate_left'] = "end translate -1mm 0"
        self.alias['-translate_down'] = "end translate 0 1mm"
        self.alias['-translate_up'] = "end translate 0 -1mm"
        self.alias['-right'] = "end right 1mm"
        self.alias['-left'] = "end left 1mm"
        self.alias['-up'] = "end up 1mm"
        self.alias['-down'] = "end down 1mm"

    def read_item_persistent(self, item):
        return self.config.Read(item)

    def read_persistent(self, t, key, default=None, uid=0):
        if self.config is None:
            return default
        if uid != 0:
            key = '%s/%s' % (str(uid), key)
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

    def write_persistent(self, key, value, uid=0):
        if self.config is None:
            return
        if uid != 0:
            key = '%d/%s' % (uid, key)
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

    def register_loader(self, name, obj):
        self.registered['load'][name] = obj

    def register_saver(self, name, obj):
        self.registered['save'][name] = obj

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
        self.setting(float, 'cut_dratio', None)
        self.setting(float, 'cut_speed', 10.0)
        self.setting(float, 'cut_power', 1000.0)
        self.setting(float, 'engrave_speed', 35.0)
        self.setting(float, 'engrave_power', 1000.0)
        self.setting(float, 'engrave_dratio', None)
        self.setting(float, 'raster_speed', 35.0)
        self.setting(float, 'raster_power', 1000.0)
        self.setting(int, 'raster_step', 2)
        self.setting(int, 'raster_direction', 0)
        self.setting(int, 'raster_overscan', 20)

        if not isinstance(elements, list):
            elements = [elements]
        for element in elements:
            if isinstance(element, Path):
                if element.stroke == "red":
                    if cut is None or not cut.has_same_properties(element.values):
                        cut = CutOperation(speed=self.cut_speed, power=self.cut_power, dratio=self.cut_dratio)
                        cuts.append(cut)
                        cut.set_properties(element.values)
                    cut.append(element)
                elif element.stroke == "blue":
                    if engrave is None or not engrave.has_same_properties(element.values):
                        engrave = EngraveOperation(speed=self.engrave_speed, power=self.engrave_power,
                                                   dratio=self.engrave_dratio)
                        engraves.append(engrave)
                        engrave.set_properties(element.values)
                    engrave.append(element)
                if (element.stroke != "red" and element.stroke != "blue") or element.fill is not None:
                    # not classed already, or was already classed but has a fill.
                    if raster is None or not raster.has_same_properties(element.values):
                        raster = RasterOperation(speed=self.raster_speed, power=self.raster_power,
                                                 raster_step=self.raster_step, raster_direction=self.raster_direction,
                                                 overscan=self.raster_overscan)
                        rasters.append(raster)
                        raster.set_properties(element.values)
                    raster.append(element)
            elif isinstance(element, SVGImage):
                # TODO: Add SVGImages to overall Raster, requires function to combine images.
                rasters.append(RasterOperation(element, speed=self.raster_speed, power=self.raster_power,
                                               raster_step=self.raster_step, raster_direction=self.raster_direction,
                                               overscan=self.raster_overscan))
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
        for loader_name, loader in self.registered['load'].items():
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
            for loader_name, loader in self.registered['load'].items():
                for description, extensions, mimetype in loader.load_types():
                    for ext in extensions:
                        exts.append('*.%s' % ext)
            filetypes.append(';'.join(exts))
        for loader_name, loader in self.registered['load'].items():
            for description, extensions, mimetype in loader.load_types():
                exts = []
                for ext in extensions:
                    exts.append('*.%s' % ext)
                filetypes.append("%s (%s)" % (description, extensions[0]))
                filetypes.append(';'.join(exts))
        return "|".join(filetypes)

    def save(self, pathname):
        for save_name, saver in self.registered['save'].items():
            for description, extension, mimetype in saver.save_types():
                if pathname.lower().endswith(extension):
                    saver.save(self, pathname, 'default')
                    return True
        return False

    def save_types(self):
        filetypes = []
        for saver_name, saver in self.registered['save'].items():
            for description, extension, mimetype in saver.save_types():
                filetypes.append("%s (%s)" % (description, extension))
                filetypes.append("*.%s" % (extension))
        return "|".join(filetypes)

