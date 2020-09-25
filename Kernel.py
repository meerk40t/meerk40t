import os
import time
from threading import Thread, Lock

from LaserOperation import *

STATE_UNKNOWN = -1
STATE_INITIALIZE = 0
STATE_IDLE = 1
STATE_ACTIVE = 2
STATE_BUSY = 3
STATE_PAUSE = 4
STATE_END = 5
STATE_TERMINATE = 10

INTERPRETER_STATE_RAPID = 0
INTERPRETER_STATE_FINISH = 1
INTERPRETER_STATE_PROGRAM = 2


class Module:
    """
    Modules are a generic lifecycle object. When open() is called for a module registered with the device the device is
    attached. When attached the module is initialized to that device. When close() is called for a module initialized
    on the device. The device is detached. When detached the module is finalized. When that device controlling the
    initialized module is shutdown the shutdown() event is called. By default shutdown() calls the close for the
    device. During device shutdown, initialized modules will be notified by a shutdown() call that it is shutting down
    and after all modules are notified of the shutdown they will be close() by the device. This will detach and finalize
    them.

    If a device is attempted to be open() a second time while the device is still registered. The device restore()
    function is called for the device, with the same args and kwargs that would have been called on __init__().

    A module always has an understanding of its current state within the device, and is notified of any changes in this
    state.

    Modules are also qualified jobs that can be scheduled in the kernel to run at a particular time and a given number
    of times. This is done calling schedule() and unschedule() and setting the parameters for process, args, interval,
    and times.

    All life cycles events are provided channels. These can be used calling channel(string) to notify the channel of
    any relevant information. Attach and initialize are given the channel 'open', detach and finalize are given the
    channel 'close' and shutdown is given the channel 'shutdown'.
    """

    def __init__(self, name=None, device=None, process=None, args=(), interval=1.0, times=None):
        self.name = name
        self.device = device
        self.state = STATE_INITIALIZE

        self.process = process
        self.args = args
        self.interval = interval
        self.times = times
        self.last_run = None
        self.next_run = time.time() + self.interval

    @property
    def scheduled(self):
        return self.next_run is not None and time.time() >= self.next_run

    def cancel(self):
        self.times = -1

    def schedule(self):
        """Schedule this as a job."""
        if self.device is not None and self not in self.device.jobs:
            self.device.jobs.append(self)

    def unschedule(self):
        """Unschedule this module as a job"""
        if self in self.device.jobs:
            self.device.jobs.remove(self)

    def restore(self, *args, **kwargs):
        """Called if a second open attempt is made for this module."""
        pass

    def attach(self, device, name=None, channel=None):
        """
        Called by open to attach module to device.

        This should be overloaded when making a specific module type for reuse, where using init would require specific
        subclassing, or for modules that are intended to expand the functionality of a device rather than compliment
        that functionality.
        """
        self.device = device
        self.name = name
        self.initialize(channel=channel)

    def detach(self, device, channel=None):
        """
        Called by close to detach the module from device.

        :param device:
        :param channel:
        :return:
        """
        self.finalize(channel=channel)
        self.device = None
        self.state = STATE_END

    def initialize(self, channel=None):
        """Called when device is registered and module is named. On a freshly opened module."""
        pass

    def finalize(self, channel=None):
        """Called when the module is being closed."""
        pass

    def shutdown(self, channel=None):
        """Called during the shutdown process to notify the module that it should stop working."""
        pass


class Spooler(Module):
    """
    The spooler module stores spoolable lasercode events, as a synchronous queue.

    Spooler registers itself as the device.spooler object and provides a standard location to send data to an unknown
    device.

    * peek()
    * pop()
    * job(job)
    * jobs(iterable<job>)
    * job_if_idle(job) -- Will enqueue the job if the device is currently idle.
    * clear_queue()
    * remove(job)
    """

    def __init__(self):
        Module.__init__(self)
        self.queue_lock = Lock()
        self._queue = []

    def __repr__(self):
        return "Spooler()"

    def attach(self, device, name=None, channel=None):
        """Overloaded attach to demand .spooler attribute."""
        device.spooler = self
        Module.attach(self, device, name)

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
        self.device.signal('spooler;queue', len(self._queue))
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
        self.device.signal('spooler;queue', len(self._queue))

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
        self.device.signal('spooler;queue', len(self._queue))

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
        self.device.signal('spooler;queue', len(self._queue))

    def remove(self, element):
        self.queue_lock.acquire(True)
        self._queue.remove(element)
        self.queue_lock.release()
        self.device.signal('spooler;queue', len(self._queue))


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

    def attach(self, device, name=None, channel=None):
        device.interpreter = self
        Module.attach(self, device, name)
        self.device.setting(int, 'current_x', 0)
        self.device.setting(int, 'current_y', 0)
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
        else:
            if self.device.quit:
                self.device.interpreter.pipe.stop()
                self.device.stop()

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
        if isinstance(element, int):
            self.spooled_item = (element,)
        elif isinstance(element, tuple):
            self.spooled_item = element
        else:
            try:
                self.spooled_item = element.generate()
            except AttributeError:
                try:
                    self.spooled_item = element()
                except TypeError:
                    # This could be a text element, some unrecognized type.
                    return

    def command(self, command, *values):
        """Commands are middle language LaserCommandConstants there values are given."""
        try:
            if command == COMMAND_LASER_OFF:
                self.laser_off()
            elif command == COMMAND_LASER_ON:
                self.laser_on()
            elif command == COMMAND_LASER_DISABLE:
                self.laser_disable()
            elif command == COMMAND_LASER_ENABLE:
                self.laser_enable()
            elif command == COMMAND_CUT:
                x, y = values
                self.cut(x, y)
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
                if os.name == 'nt':
                    try:
                        import winsound
                        for x in range(5):
                            winsound.Beep(2000, 100)
                    except:
                        pass
                if os.name == 'posix':
                    # Mac or linux.
                    print('\a')  # Beep.
                    os.system('say "Ding"')
                else:
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

    def cut(self, x, y):
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
        if self.power > 1000.0:
            self.power = 1000.0
        if self.power <= 0:
            self.power = 0.0

    def set_ppi(self, power=1000.0):
        self.power = power
        if self.power > 1000.0:
            self.power = 1000.0
        if self.power <= 0:
            self.power = 0.0

    def set_pwm(self, power=1000.0):
        self.power = power
        if self.power > 1000.0:
            self.power = 1000.0
        if self.power <= 0:
            self.power = 0.0

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
        self.spooled_item = None
        self.device.spooler.clear_queue()
        self.spooled_item = None
        self.extra_hold = None

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

    def attach(self, device, name=None, channel=None):
        device.signal = self.signal
        device.listen = self.listen
        device.unlisten = self.unlisten
        device.last_signal = self.last_signal
        Module.attach(self, device, name)
        self.schedule()

    def detach(self, device, channel=None):
        self.unschedule()
        Module.detach(self, device, channel=channel)

    def shutdown(self, channel=None):
        _ = self.device.device_root.translation
        for key, listener in self.listeners.items():
            if len(listener):
                channel(_("WARNING: Listener '%s' still registered to %s.") % (key, str(listener)))
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


class Elemental(Module):
    """
    The elemental module is governs all the interactions with the various elements,
    operations, and filenodes. Handling structure change and selection, emphasis, and
    highlighting changes. The goal of this module is to make sure that the life cycle
    of the elements is strictly enforced. For example, every element that is removed
    must have had the .cache deleted. And anything selecting an element must propagate
    that information out to inform other interested modules.
    """

    def __init__(self):
        Module.__init__(self)
        self._operations = list()
        self._elements = list()
        self._filenodes = {}
        self.note = None
        self._bounds = None

    def attach(self, device, name=None, channel=None):
        device.elements = self
        device.classify = self.classify
        device.save = self.save
        device.save_types = self.save_types
        device.load = self.load
        device.load_types = self.load_types
        Module.attach(self, device, name)

    def register(self, obj):
        obj.wx_bitmap_image = None
        obj.icon = None
        obj.bounds = None
        obj.last_transform = None
        obj.selected = False
        obj.emphasized = False
        obj.highlighted = False

        def select():
            obj.selected = True
            self.device.signal('selected', obj)

        def unselect():
            obj.selected = False
            self.device.signal('selected', obj)

        def highlight():
            obj.highlighted = True
            self.device.signal('highlighted', obj)

        def unhighlight():
            obj.highlighted = False
            self.device.signal('highlighted', obj)

        def emphasize():
            obj.emphasized = True
            self.device.signal('emphasized', obj)
            self.validate_bounds()

        def unemphasize():
            obj.emphasized = False
            self.device.signal('emphasized', obj)
            self.validate_bounds()

        def modified():
            """
            The matrix transformation was changed.
            """
            obj.bounds = None
            self._bounds = None
            self.validate_bounds()
            self.device.signal('modified', obj)

        def altered():
            """
            The data structure was changed.
            """
            try:
                obj.wx_bitmap_image.UnGetNativePath(obj.wx_bitmap_image.NativePath)
            except AttributeError:
                pass
            del obj.wx_bitmap_image
            obj.wx_bitmap_image = None
            del obj.icon
            obj.icon = None
            obj.bounds = None
            self._bounds = None
            self.validate_bounds()
            self.device.signal('altered', obj)

        obj.select = select
        obj.unselect = unselect
        obj.highlight = highlight
        obj.unhighlight = unhighlight
        obj.emphasize = emphasize
        obj.unemphasize = unemphasize
        obj.modified = modified
        obj.altered = altered

    def unregister(self, e):
        try:
            e.wx_bitmap_image.UngetNativePath(e.wx_bitmap_image.NativePath)
        except AttributeError:
            pass
        try:
            del e.wx_bitmap_image
        except AttributeError:
            pass
        try:
            del e.icon
        except AttributeError:
            pass
        try:
            e.unselect()
            e.unemphasize()
            e.unhighlight()
            e.modified()
        except AttributeError:
            pass

    def load_default(self):
        self.clear_operations()
        self.add_op(LaserOperation(operation="Image", color="black",
                                   speed=140.0,
                                   power=1000.0,
                                   raster_step=3))
        self.add_op(LaserOperation(operation="Raster", color="black", speed=140.0))
        self.add_op(LaserOperation(operation="Engrave", color="blue", speed=35.0))
        self.add_op(LaserOperation(operation="Cut", color="red", speed=10.0))
        self.classify(self.elems())

    def load_default2(self):
        self.clear_operations()
        self.add_op(LaserOperation(operation="Image", color="black",
                                   speed=140.0,
                                   power=1000.0,
                                   raster_step=3))
        self.add_op(LaserOperation(operation="Raster", color="black", speed=140.0))
        self.add_op(LaserOperation(operation="Engrave", color="green", speed=35.0))
        self.add_op(LaserOperation(operation="Engrave", color="blue", speed=35.0))
        self.add_op(LaserOperation(operation="Engrave", color="magenta", speed=35.0))
        self.add_op(LaserOperation(operation="Engrave", color="cyan", speed=35.0))
        self.add_op(LaserOperation(operation="Engrave", color="yellow", speed=35.0))
        self.add_op(LaserOperation(operation="Cut", color="red", speed=10.0))
        self.classify(self.elems())

    def finalize(self, channel=None):
        kernel = self.device.device_root
        settings = kernel.derive('operations')
        settings.clear_persistent()
        for i, op in enumerate(self.ops()):
            op_set = settings.derive(str(i))
            for key in dir(op):
                if key.startswith('_'):
                    continue
                value = getattr(op, key)
                if value is None:
                    continue
                if isinstance(value, Color):
                    value = value.value
                op_set.write_persistent(key, value)

    def boot(self):
        kernel = self.device.device_root
        settings = kernel.derive('operations')
        subitems = list(settings.derivable())
        ops = [None] * len(subitems)
        for i, v in enumerate(subitems):
            op_set = settings.derive(v)
            op = LaserOperation()
            op_set.load_persistent_object(op)
            try:
                ops[i] = op
            except (ValueError, IndexError):
                ops.append(op)
        if not len(ops):
            self.load_default()
            return
        self.add_ops([o for o in ops if o is not None])
        self.device.signal('rebuild_tree')

    def items(self, **kwargs):
        def combined(*args):
            for listv in args:
                for itemv in listv:
                    yield itemv

        for j in combined(self.ops(**kwargs), self.elems(**kwargs)):
            yield j

    def _filtered_list(self, item_list, **kwargs):
        """
        Filters a list of items with selected, emphasized, and highlighted.
        False values means find where that parameter is false.
        True values means find where that parameter is true.
        If the filter does not exist then it isn't used to filter that data.

        Items which are set to None are skipped.

        :param item_list:
        :param kwargs:
        :return:
        """
        s = 'selected' in kwargs
        if s:
            s = kwargs['selected']
        else:
            s = None
        e = 'emphasized' in kwargs
        if e:
            e = kwargs['emphasized']
        else:
            e = None
        h = 'highlighted' in kwargs
        if h:
            h = kwargs['highlighted']
        else:
            h = None
        for obj in item_list:
            if obj is None:
                continue
            if s is not None and s != obj.selected:
                continue
            if e is not None and e != obj.emphasized:
                continue
            if h is not None and s != obj.highlighted:
                continue
            yield obj

    def ops(self, **kwargs):
        for item in self._filtered_list(self._operations, **kwargs):
            yield item

    def elems(self, **kwargs):
        for item in self._filtered_list(self._elements, **kwargs):
            yield item

    def first_element(self, **kwargs):
        for e in self.elems(**kwargs):
            return e
        return None

    def has_emphasis(self):
        return self.first_element(emphasized=True) is not None

    def count_elems(self, **kwargs):
        return len(list(self.elems(**kwargs)))

    def count_op(self, **kwargs):
        return len(list(self.ops(**kwargs)))

    def get_op(self, index, **kwargs):
        for i, op in enumerate(self.ops(**kwargs)):
            if i == index:
                return op
        raise IndexError

    def get_elem(self, index, **kwargs):
        for i, elem in enumerate(self.elems(**kwargs)):
            if i == index:
                return elem
        raise IndexError

    def add_op(self, op):
        self._operations.append(op)
        self.register(op)
        self.device.signal('operation_added', op)

    def add_ops(self, adding_ops):
        self._operations.extend(adding_ops)
        for op in adding_ops:
            self.register(op)
        self.device.signal('operation_added', adding_ops)

    def add_elem(self, element):
        self._elements.append(element)
        self.register(element)
        self.device.signal('element_added', element)

    def add_elems(self, adding_elements):
        self._elements.extend(adding_elements)
        for element in adding_elements:
            self.register(element)
        self.device.signal('element_added', adding_elements)

    def files(self):
        return self._filenodes

    def clear_operations(self):
        for op in self._operations:
            self.unregister(op)
            self.device.signal('operation_removed', op)
        self._operations.clear()

    def clear_elements(self):
        for e in self._elements:
            self.unregister(e)
            self.device.signal('element_removed', e)
        self._elements.clear()

    def clear_files(self):
        self._filenodes.clear()

    def clear_elements_and_operations(self):
        self.clear_elements()
        self.clear_operations()

    def clear_all(self):
        self.clear_elements()
        self.clear_operations()
        self.clear_files()
        self.clear_note()
        self.validate_bounds()

    def clear_note(self):
        self.note = None

    def remove_files(self, file_list):
        for f in file_list:
            del self._filenodes[f]

    def remove_elements(self, elements_list):
        for elem in elements_list:
            for i, e in enumerate(self._elements):
                if elem is e:
                    self.unregister(elem)
                    self.device.signal('element_removed', elem)
                    self._elements[i] = None
        self.remove_elements_from_operations(elements_list)
        self.validate_bounds()

    def remove_operations(self, operations_list):
        for op in operations_list:
            for i, o in enumerate(self._operations):
                if o is op:
                    self.unregister(op)
                    self.device.signal('operation_removed', op)
                    self._operations[i] = None
        self.purge_unset()

    def remove_elements_from_operations(self, elements_list):
        for i, op in enumerate(self._operations):
            if op is None:
                continue
            elems = [e for e in op if e not in elements_list]
            op.clear()
            op.extend(elems)
        self.purge_unset()

    def purge_unset(self):
        if None in self._operations:
            ops = [op for op in self._operations if op is not None]
            self._operations.clear()
            self._operations.extend(ops)
        if None in self._elements:
            elems = [elem for elem in self._elements if elem is not None]
            self._elements.clear()
            self._elements.extend(elems)

    def bounds(self):
        return self._bounds

    def validate_bounds(self):
        boundary_points = []
        for e in self._elements:
            if e.last_transform is None or e.last_transform != e.transform or e.bounds is None:
                e.bounds = e.bbox(False)
                e.last_transform = copy(e.transform)
            if e.bounds is None:
                continue
            if not e.emphasized:
                continue
            box = e.bounds
            top_left = e.transform.point_in_matrix_space([box[0], box[1]])
            top_right = e.transform.point_in_matrix_space([box[2], box[1]])
            bottom_left = e.transform.point_in_matrix_space([box[0], box[3]])
            bottom_right = e.transform.point_in_matrix_space([box[2], box[3]])
            boundary_points.append(top_left)
            boundary_points.append(top_right)
            boundary_points.append(bottom_left)
            boundary_points.append(bottom_right)

        if len(boundary_points) == 0:
            new_bounds = None
        else:
            xmin = min([e[0] for e in boundary_points])
            ymin = min([e[1] for e in boundary_points])
            xmax = max([e[0] for e in boundary_points])
            ymax = max([e[1] for e in boundary_points])
            new_bounds = [xmin, ymin, xmax, ymax]
        if self._bounds != new_bounds:
            self._bounds = new_bounds
            self.device.device_root.signal('selected_bounds', self._bounds)

    def is_in_set(self, v, selected, flat=True):
        for q in selected:
            if flat and isinstance(q, (list, tuple)) and self.is_in_set(v, q, flat):
                return True
            if q is v:
                return True
        return False

    def set_selected(self, selected):
        """
        Sets selected and other properties of a given element.

        All selected elements are also semi-selected.

        If elements itself is selected, all subelements are semiselected.

        If any operation is selected, all sub-operations are highlighted.

        """
        if selected is None:
            selected = []
        for s in self._elements:
            should_select = self.is_in_set(s, selected, False)
            should_emphasize = self.is_in_set(s, selected)
            if s.emphasized:
                if not should_emphasize:
                    s.unemphasize()
            else:
                if should_emphasize:
                    s.emphasize()
            if s.selected:
                if not should_select:
                    s.unselect()
            else:
                if should_select:
                    s.select()
        for s in self._operations:
            should_select = self.is_in_set(s, selected, False)
            should_emphasize = self.is_in_set(s, selected)
            if s.emphasized:
                if not should_emphasize:
                    s.unemphasize()
            else:
                if should_emphasize:
                    s.emphasize()
            if s.selected:
                if not should_select:
                    s.unselect()
            else:
                if should_select:
                    s.select()

    def center(self):
        bounds = self._bounds
        return (bounds[2] + bounds[0]) / 2.0, (bounds[3] + bounds[1]) / 2.0

    def ensure_positive_bounds(self):
        b = self._bounds
        self._bounds = [min(b[0], b[2]), min(b[1], b[3]), max(b[0], b[2]), max(b[1], b[3])]
        self.device.device_root.signal('selected_bounds', self._bounds)

    def update_bounds(self, b):
        self._bounds = [b[0], b[1], b[0], b[1]]
        self.device.device_root.signal('selected_bounds', self._bounds)

    @staticmethod
    def bounding_box(elements):
        if isinstance(elements, SVGElement):
            elements = [elements]
        elif isinstance(elements, list):
            try:
                elements = [e.object for e in elements if isinstance(e.object, SVGElement)]
            except AttributeError:
                pass
        boundary_points = []
        for e in elements:
            box = e.bbox(False)
            if box is None:
                continue
            top_left = e.transform.point_in_matrix_space([box[0], box[1]])
            top_right = e.transform.point_in_matrix_space([box[2], box[1]])
            bottom_left = e.transform.point_in_matrix_space([box[0], box[3]])
            bottom_right = e.transform.point_in_matrix_space([box[2], box[3]])
            boundary_points.append(top_left)
            boundary_points.append(top_right)
            boundary_points.append(bottom_left)
            boundary_points.append(bottom_right)
        if len(boundary_points) == 0:
            return None
        xmin = min([e[0] for e in boundary_points])
        ymin = min([e[1] for e in boundary_points])
        xmax = max([e[0] for e in boundary_points])
        ymax = max([e[1] for e in boundary_points])
        return xmin, ymin, xmax, ymax

    def move_selected(self, dx, dy):
        for obj in self.elems(emphasized=True):
            obj.transform.post_translate(dx, dy)
            obj.modified()

    def set_selected_by_position(self, position):
        def contains(box, x, y=None):
            if y is None:
                y = x[1]
                x = x[0]
            return box[0] <= x <= box[2] and box[1] <= y <= box[3]

        if self.has_emphasis():
            if self._bounds is not None and contains(self._bounds, position):
                return  # Select by position aborted since selection position within current select bounds.
        for e in reversed(list(self.elems())):
            bounds = e.bbox()
            if bounds is None:
                continue
            if contains(bounds, position):
                self.set_selected([e])
                return
        self.set_selected(None)

    def classify(self, elements):
        """
        Classify does the initial placement of elements as operations.
        "Image" is the default for images.
        If element strokes are red they get classed as cut operations
        If they are otherwise they get classed as engrave.
        """
        if elements is None:
            return
        for element in elements:
            found_color = False
            added_to_op = False
            for op in self.ops():
                if op.operation == "Raster" and op.color == element.stroke:
                    if not added_to_op:
                        op.append(element)
                    found_color = True
                    added_to_op = True
                elif op.operation in ("Engrave", "Cut") and op.color == element.stroke:
                    op.append(element)
                    found_color = True
                    added_to_op = True
                elif op.operation == 'Image' and isinstance(element, SVGImage):
                    op.append(element)
                    found_color = True
                    added_to_op = True
                elif op.operation == 'Raster' and \
                        not isinstance(element, SVGImage) and \
                        element.fill is not None and \
                        element.fill.value is not None:
                    op.append(element)
                    found_color = True
                    added_to_op = True
            if not found_color:
                if element.stroke is not None and element.stroke.value is not None:
                    op = LaserOperation(operation="Engrave", color=element.stroke, speed=35.0)
                    op.append(element)
                    self.add_op(op)

    def load(self, pathname, **kwargs):
        for loader_name, loader in self.device.registered['load'].items():
            for description, extensions, mimetype in loader.load_types():
                if pathname.lower().endswith(extensions):
                    results = loader.load(self.device, pathname, **kwargs)
                    if results is None:
                        continue
                    elements, ops, note, pathname, basename = results
                    self._filenodes[pathname] = elements
                    self.add_elems(elements)
                    if ops is not None:
                        self.clear_operations()
                        self.add_ops(ops)
                    if note is not None:
                        self.clear_note()
                        self.note = note
                    return elements, pathname, basename
        return None

    def load_types(self, all=True):
        filetypes = []
        if all:
            filetypes.append('All valid types')
            exts = []
            for loader_name, loader in self.device.registered['load'].items():
                for description, extensions, mimetype in loader.load_types():
                    for ext in extensions:
                        exts.append('*.%s' % ext)
            filetypes.append(';'.join(exts))
        for loader_name, loader in self.device.registered['load'].items():
            for description, extensions, mimetype in loader.load_types():
                exts = []
                for ext in extensions:
                    exts.append('*.%s' % ext)
                filetypes.append("%s (%s)" % (description, extensions[0]))
                filetypes.append(';'.join(exts))
        return "|".join(filetypes)

    def save(self, pathname):
        for save_name, saver in self.device.registered['save'].items():
            for description, extension, mimetype in saver.save_types():
                if pathname.lower().endswith(extension):
                    saver.save(self.device, pathname, 'default')
                    return True
        return False

    def save_types(self):
        filetypes = []
        for saver_name, saver in self.device.registered['save'].items():
            for description, extension, mimetype in saver.save_types():
                filetypes.append("%s (%s)" % (description, extension))
                filetypes.append("*.%s" % (extension))
        return "|".join(filetypes)


class Kern:
    """
    TODO: Transition.

    The Kernel defines a specific location for functional elements. These are registered and in turn those are
    subregistered. Every Kernel has a path. These can be derived from one another. Derived paths are stored as specific
    implemented objects. Kernels can have functionality added to them dynamically. For example calling on the Spooler
    object will set the .spooler when the spooler is attached. Every opened item has a source and an attached
    destination. This permits registration of multiple objects to different locations.
    """
    def __init__(self, parent=None, path=None):
        self._parent = parent
        self._path = path
        if parent is not None:
            self.registered = parent.registered
            self.instances = parent.instances
        else:
            self.registered = {}
            self.instances = {}

    def __str__(self):
        return "Kern('%s')" % self._path

    __repr__ = __str__

    def abs_path(self, subpath):
        subpath = str(subpath)
        current = self
        if subpath.startswith('../'):
            if self._parent is None:
                raise ValueError()
            current = self._parent
            subpath = subpath[3:]
        if subpath.startswith('/') or self._path is None:
            return subpath
        else:
            return "%s/%s" % (current._path, subpath)

    def derive(self, subpath):
        """
        Create a sub-object derived from this object.

        :param subpath: subpath underwhich to have the object.
        :return: Derived Object.
        """
        derive = Kern(parent=self, path=self.abs_path(subpath))
        return derive

    def register(self, path, obj):
        """
        Register an element at a given subpath. If this Kern is not root. Then
        it is registered relative to this location.

        :param path:
        :param obj:
        :return:
        """
        self.registered[path] = obj
        try:
            obj.sub_register(self)
        except AttributeError:
            pass

    def find(self, path):
        """
        Finds a loaded instance. Or returns None if not such instance.

        Note name is not necessarily the type of instance. It could be the named value of the instance.

        :param path: The type of instance to find.
        :return: The instance if found, otherwise none.
        """
        try:
            return self.instances[self.abs_path(path)]
        except KeyError:
            return None

    def open(self, registered_path, instance_path, *args, **kwargs):
        """
        Opens a registered module. If that module already exists it returns the already open module.

        Two special kwargs are passed to this. 'instance_name' and 'sub'. These control the name under which
        the module is registered. Instance_name replaces the default, which registers the instance under the object_name
        whereas sub provides a suffixed name 'object_name:sub'.

        If the module already exists, the restore function is called on that object, if it exists, with the same args
        and kwargs that were intended for the init() routine.

        :param registered_path: path of object being opened.
        :param instance_path: path of object should be attached.
        :param args: Args to pass to newly opened module.
        :param kwargs: Kwargs to pass to newly opened module.
        :return: Opened module.
        """
        instance_path = self.abs_path(instance_path)
        try:
            find = self.instances[instance_path]
            try:
                find.restore(*args, **kwargs)
            except AttributeError:
                pass
            return find
        except KeyError:
            pass

        try:
            open_object = self.registered[registered_path]
        except KeyError:
            raise ValueError

        instance = open_object(*args, **kwargs)
        try:
            channel = self.channel_open('open')
        except AttributeError:
            channel = None

        try:
            instance.attach(self, name=instance_path, channel=channel)
        except AttributeError:
            pass

        self.instances[instance_path] = instance
        return instance

    def close(self, instance_path):
        instance_path = self.abs_path(instance_path)
        try:
            instance = self.instances[instance_path]
        except KeyError:
            raise ValueError
        try:
            instance.close()
        except AttributeError:
            pass
        del self.instances[instance_path]
        try:
            channel = self.channel_open('close')
        except AttributeError:
            channel = None

        try:
            instance.detach(self, channel=channel)
        except AttributeError:
            pass


class Preferences:
    """
    This class is expected to run even if there is no persistent storage.

    Without an persistence object, attributes will be assigned by .settings() command, and the objects cannot flush().
    If the config is not set, it will check the root for a non-None config until setting. So only the root objects
    persistence object needs to be set.
    """
    def __init__(self, config=None, path=None, root=None):
        self._root = root
        if self._root is None:
            self._root = self
        self._path = path
        self._config = config
        self.set_config(config)

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

    def derive(self, subpath):
        """
        Create a sub-preferences object, at the given subpath.

        :param subpath: subpath underwhich to have the object.
        :return: Preferences object derived from this one.
        """
        if self._path is not None:
            subpath = "%s/%s" % (self._path, subpath)
        derive = Preferences(config=self._config, path=subpath, root=self._root)
        return derive

    def setting(self, setting_type, key, default=None):
        """
        Registers a setting to be used between modules.

        If the setting exists, its value remains unchanged.
        If the setting exists in the persistent storage that value is used.
        If there is no settings value, the default will be used.

        :param setting_type: int, float, str, or bool value
        :param key: name of the setting
        :param default: default value for the setting to have.
        :return: load_value
        """
        if hasattr(self, key) and getattr(self, key) is not None:
            return getattr(self, key)

        # Key is not located in the attr. Load the value.
        if not key.startswith('_'):
            load_value = self.read_persistent(setting_type, key, default)
        else:
            load_value = default
        setattr(self, key, load_value)
        return load_value

    def flush(self):
        """
        Commit any and all values currently stored as attr for this object to persistent storage.

        :return:
        """

        for attr in dir(self):
            if attr.startswith('_'):
                continue
            value = getattr(self, attr)
            if value is None:
                continue
            if isinstance(value, (int, bool, str, float, Color)):
                self.write_persistent(attr, value)

    def read_item_persistent(self, key):
        """Directly read from persistent storage the value of an item."""
        if self._config is None:
            self._config = self._root._config
        if self._config is None:
            return None
        if self._path is not None:
            key = '%s/%s' % (str(self._path), key)
        return self._config.Read(key)

    def read_persistent(self, t, key, default=None):
        """
        Directly read from persistent storage the value of an item.

        :param t: datatype.
        :param key: key used to reference item.
        :param default: default value if item does not exist.
        :return: value
        """
        if self._config is None:
            self._config = self._root._config
        if self._config is None:
            return default
        if self._path is not None:
            key = '%s/%s' % (str(self._path), key)
        if default is not None:
            if t == str:
                return self._config.Read(key, default)
            elif t == int:
                return self._config.ReadInt(key, default)
            elif t == float:
                return self._config.ReadFloat(key, default)
            elif t == bool:
                return self._config.ReadBool(key, default)
            elif t == Color:
                return self._config.ReadInt(key, default)
        else:
            if t == str:
                return self._config.Read(key)
            elif t == int:
                return self._config.ReadInt(key)
            elif t == float:
                return self._config.ReadFloat(key)
            elif t == bool:
                return self._config.ReadBool(key)
            elif t == Color:
                return self._config.ReadInt(key)
        return default

    def write_persistent(self, key, value):
        """
        Directly write the value to persistent storage.

        :param key: The item key being read.
        :param value: the value of the item.
        """
        if self._config is None:
            self._config = self._root._config
        if self._config is None:
            return
        if self._path is not None:
            key = '%s/%s' % (str(self._path), key)
        if isinstance(value, str):
            self._config.Write(key, value)
        elif isinstance(value, int):
            self._config.WriteInt(key, value)
        elif isinstance(value, float):
            self._config.WriteFloat(key, value)
        elif isinstance(value, bool):
            self._config.WriteBool(key, value)
        elif isinstance(value, Color):
            self._config.WriteInt(key, value)

    def clear_persistent(self):
        if self._config is None:
            self._config = self._root._config
        if self._config is None:
            return
        self._config.DeleteGroup(self._path)

    def delete_persistent(self, key):
        if self._config is None:
            self._config = self._root._config
        if self._config is None:
            return
        if self._path is not None:
            key = '%s/%s' % (str(self._path), key)
        self._config.DeleteEntry(key)

    def load_persistent_object(self, obj):
        """
        Loads values of the persistent attributes, and assigns them to the obj.
        The type of the value depends on the obj value default values.

        :param obj:
        :return:
        """
        for attr in dir(obj):
            if attr.startswith('_'):
                continue
            obj_value = getattr(obj, attr)

            if not isinstance(obj_value, (int, float, str, bool, Color)):
                continue
            load_value = self.read_persistent(type(obj_value), attr)
            setattr(obj, attr, load_value)
            setattr(self, attr, load_value)

    def load_persistent_string_dict(self, dictionary=None):
        if dictionary is None:
            dictionary = dict()
        for k in list(self.keylist()):
            dictionary[k] = self.read_item_persistent(k)
        return dictionary

    def keylist(self):
        if self._config is None:
            self._config = self._root._config
        if self._config is None:
            return
        if self._path is not None:
            self._config.SetPath(self._path)
        more, value, index = self._config.GetFirstEntry()
        while more:
            yield value
            more, value, index = self._config.GetNextEntry(index)
        self._config.SetPath('/')

    def derivable(self):
        if self._config is None:
            self._config = self._root._config
        if self._config is None:
            return
        if self._path is not None:
            self._config.SetPath(self._path)
        more, value, index = self._config.GetFirstGroup()
        while more:
            yield value
            more, value, index = self._config.GetNextGroup(index)
        self._config.SetPath('/')

    def set_attrib_keys(self):
        """
        Iterate all the entries for the registered config, adds a None attribute for keys.
        """

        for k in self.keylist():
            if not hasattr(self, k):
                setattr(self, k, None)

    def set_config(self, config):
        """
        Set the config object.

        :param config: Persistent storage object.
        :return:
        """
        if config is None:
            return
        self._config = config


class Device(Preferences):
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

    def __init__(self, root=None, uid=0, config=None):
        self.thread = None
        self.name = None
        self.device_root = root
        self.device_name = "Device"
        self.device_version = "0.0.0"
        self.device_location = "Kernel"
        self._uid = uid
        if uid != 0:
            Preferences.__init__(self, config=config, path=str(uid), root=root)
        else:
            Preferences.__init__(self, config=config, root=root)

        self.state = STATE_UNKNOWN
        self.jobs = []

        self.registered = {}
        self.instances = {}

        # Channel processing.
        self.channels = {}
        self.watchers = {}
        self.buffer = {}
        self.greet = {}
        self.element = None

    def __str__(self):
        if self._uid == 0:
            return "Project"
        else:
            return "%s:%d" % (self.device_name, self._uid)

    def __call__(self, code, *message):
        self.signal(code, *message)

    def attach(self, device, name=None, channel=None):
        self.device_root = device
        self.name = name
        self.setting(bool, 'quit', False)
        self.quit = False
        self.initialize(device, channel=channel)

    def detach(self, device, channel=None):
        def signal(code, *message):
            _ = self.device_root.translation
            channel(_("Suspended Signal: %s for %s" % (code, message)))
        self.signal = signal
        self.finalize(device, channel=channel)

    def initialize(self, device, channel=None):
        pass

    def finalize(self, device, channel=None):
        pass

    def threaded(self, func, thread_name=None):
        if thread_name is None:
            thread_name = func.__name__
        thread = Thread(name=thread_name)

        def run():
            self.thread_instance_add(thread_name, thread)
            try:
                func()
            except:
                import sys
                sys.excepthook(*sys.exc_info())
            self.thread_instance_remove(thread_name)

        thread.run = run
        thread.start()
        return thread

    def boot(self):
        """
        Device boot sequence. This should be called after all the registered devices are established.
        :return:
        """
        if self.thread is None or not self.thread.is_alive():
            self.thread = self.threaded(self.run, 'Device%d' % int(self._uid))
        self.control_instance_add("Debug Device", self._start_debugging)
        try:
            for m in self.instances['module']:
                m = self.instances['module'][m]
                try:
                    m.boot()
                except AttributeError:
                    pass
        except KeyError:
            pass

    def shutdown(self, channel=None):
        """
        Begins device shutdown procedure.
        """
        self.state = STATE_TERMINATE
        _ = self.device_root.translation
        channel(_("Shutting down."))
        self.detach(self, channel=channel)
        channel(_("Saving Device State: '%s'") % str(self))
        self.flush()

        # Stop all devices.
        if 'device' in self.instances:
            # Join and shutdown any child devices.
            devices = self.instances['device']
            del self.instances['device']
            for device_name in devices:
                device = devices[device_name]
                channel(_("Device Shutdown Started: '%s'") % str(device))
                device_thread = device.thread
                device.stop()
                if device_thread is not None:
                    device_thread.join()
                channel(_("Device Shutdown Finished: '%s'") % str(device))

        # Stop all instances.
        for type_name in list(self.instances):
            if type_name in ('control', 'thread'):
                continue
            for module_name in list(self.instances[type_name]):
                obj = self.instances[type_name][module_name]
                try:
                    obj.stop()
                    channel(_("Stopping %s %s: %s") % (module_name, type_name, str(obj)))
                except AttributeError:
                    pass
                channel(_("Closing %s %s: %s") % (module_name, type_name, str(obj)))
                self.close(type_name, module_name)

        # Stop/Wait for all threads.
        if 'thread' in self.instances:
            for thread_name in list(self.instances['thread']):
                thread = None
                try:
                    thread = self.instances['thread'][thread_name]
                except KeyError:
                    channel(_("Thread %s exited safely %s") % (thread_name, str(thread)))
                    continue
                if not thread.is_alive:
                    channel(_("WARNING: Dead thread %s still registered to %s.") % (thread_name, str(thread)))
                    continue
                channel(_("Finishing Thread %s for %s") % (thread_name, str(thread)))
                if thread is self.thread:
                    channel(_("%s is the current shutdown thread") % (thread_name))
                    continue
                    # Do not sleep thread waiting for that thread to die. This is that thread.
                try:
                    channel(_("Asking thread to stop."))
                    thread.stop()
                except AttributeError:
                    pass
                channel(_("Waiting for thread %s: %s") % (thread_name, str(thread)))
                thread.join()
                channel(_("Thread %s finished. %s") % (thread_name, str(thread)))
        else:
            channel(_("No threads required halting."))

        # Detach all instances.
        for type_name in list(self.instances):
            if type_name in ('control'):
                continue
            for module_name in list(self.instances[type_name]):
                obj = self.instances[type_name][module_name]
                try:
                    obj.detach(self, channel=channel)
                    channel(_("Shutting down %s %s: %s") % (module_name, type_name, str(obj)))
                except AttributeError:
                    pass

        # Check for failures.
        for type_name in list(self.instances):
            if type_name in ('control'):
                continue
            for module_name in self.instances[type_name]:
                obj = self.instances[type_name][module_name]
                if obj is self.thread:
                    continue  # Don't warn about failure to close current thread.
                channel(_("WARNING: %s %s was not closed.") % (type_name, module_name))

        channel(_("Shutdown."))

        shutdown_root = False
        if not self.is_root():
            if 'device' in self.device_root.instances:
                root_devices = self.device_root.instances['device']
                if root_devices is None:
                    shutdown_root = True
                else:
                    if str(self._uid) in root_devices:
                        del root_devices[str(self._uid)]
                    if len(root_devices) == 0:
                        shutdown_root = True
            else:
                shutdown_root = True
        if shutdown_root:
            channel(_("All Devices are shutdown. Stopping Kernel."))
            self.device_root.stop()
        else:
            self.device_root.resume()

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
        self.state = STATE_ACTIVE
        while self.state != STATE_END:
            time.sleep(0.005)  # 200 ticks a second.
            if self.state == STATE_TERMINATE:
                break
            while self.state == STATE_PAUSE:
                # The scheduler is paused.
                time.sleep(0.1)
            if self.state == STATE_TERMINATE:
                break
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
                    try:
                        if isinstance(jobs, int):
                            job.process(job.args[0])
                        elif isinstance(job.args, tuple):
                            job.process(*job.args)
                        else:
                            job.process(job.args)
                    except:
                        import sys
                        sys.excepthook(*sys.exc_info())
                    job.last_run = time.time()
                    job.next_run += job.last_run + job.interval
            if jobs_update:
                self.jobs = [job for job in jobs if job.times is None or job.times > 0]
        self.state = STATE_END

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

    def execute(self, control_name, *args):
        try:
            self.instances['control'][control_name](*args)
        except KeyError:
            pass

    def signal(self, code, *message):
        if self._uid != 0:
            code = '%d;%s' % (self._uid, code)
        if self.device_root is not None and self.device_root is not self:
            self.device_root.signal(code, *message)

    def last_signal(self, signal):
        if self._uid != 0:
            signal = '%d;%s' % (self._uid, signal)
        if self.device_root is not None and self.device_root is not self:
            try:
                return self.device_root.last_signal(signal)
            except AttributeError:
                pass
        return None

    def listen(self, signal, funct):
        if self._uid != 0:
            signal = '%d;%s' % (self._uid, signal)
        if self.device_root is not None and self.device_root is not self:
            self.device_root.listen(signal, funct)

    def unlisten(self, signal, funct):
        if self._uid != 0:
            signal = '%d;%s' % (self._uid, signal)
        if self.device_root is not None and self.device_root is not self:
            self.device_root.unlisten(signal, funct)

    def state(self):
        return self.state

    def resume(self):
        self.state = STATE_ACTIVE

    def pause(self):
        self.state = STATE_PAUSE

    def stop(self):
        self.state = STATE_TERMINATE

    # Channel processing

    def add_greet(self, channel, greet):
        self.greet[channel] = greet
        if channel in self.channels:
            self.channels[channel](greet)

    def add_watcher(self, channel, monitor_function):
        if channel not in self.watchers:
            self.watchers[channel] = [monitor_function]
        else:
            for q in self.watchers[channel]:
                if q is monitor_function:
                    return  # This is already being watched by that.
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

    def find(self, type_name, name):
        """
        Finds a loaded instance. Or returns None if not such instance.

        Note name is not necessarily the type of instance. It could be the named value of the instance.

        :param type_name: The type of instance to find.
        :param name: The name of this instance.
        :return: The instance if found, otherwise none.
        """
        if type_name in self.instances:
            if name in self.instances[type_name]:
                return self.instances[type_name][name]
        return None

    def using(self, type_name, object_name, *args, **kwargs):
        return self.open(type_name, object_name, *args, **kwargs)

    def open(self, type_name, object_name, *args, **kwargs):
        """
        Opens a registered module. If that module already exists it returns the already open module.

        Two special kwargs are passed to this. 'instance_name' and 'sub'. These control the name under which
        the module is registered. Instance_name replaces the default, which registers the instance under the object_name
        whereas sub provides a suffixed name 'object_name:sub'.

        If the module already exists, the restore function is called on that object, if it exists, with the same args
        and kwargs that were intended for the init() routine.

        :param type_name: Type of object being opened.
        :param object_name: Name of object being opened.
        :param args: Args to pass to newly opened module.
        :param kwargs: Kwargs to pass to newly opened module.
        :return: Opened module.
        """
        if 'instance_name' in kwargs:
            instance_name = kwargs['instance_name']
            del kwargs['instance_name']
        else:
            instance_name = object_name

        if 'sub' in kwargs:
            instance_name = "%s:%s" % (instance_name, kwargs['sub'])
            del kwargs['sub']

        find = self.find(type_name, instance_name)
        if find is not None:
            try:
                find.restore(*args, **kwargs)
            except AttributeError:
                pass
            return find

        if self.device_root is None or self.device_root is self:
            module_object = self.registered[type_name][object_name]
        else:
            module_object = self.device_root.registered[type_name][object_name]
        instance = module_object(*args, **kwargs)
        instance.attach(self, name=instance_name, channel=self.channel_open('open'))
        self.add(type_name, instance_name, instance)
        return instance

    def add(self, type_name, instance_name, instance):
        if type_name not in self.instances:
            self.instances[type_name] = {}
        self.instances[type_name][instance_name] = instance

    def close(self, type_name, instance_name):
        if type_name in self.instances and instance_name in self.instances[type_name]:
            instance = self.instances[type_name][instance_name]
            try:
                instance.close()
            except AttributeError:
                pass
            self.remove(type_name, instance_name)
            instance.detach(self, channel=self.channel_open('close'))

    def remove(self, type_name, instance_name):
        if instance_name in self.instances[type_name]:
            del self.instances[type_name][instance_name]

    def module_instance_open(self, module_name, *args, instance_name=None, **kwargs):
        return self.open('module', module_name, *args, instance_name=instance_name, **kwargs)

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
        if state == STATE_INITIALIZE:
            return _("Unstarted")
        elif state == STATE_TERMINATE:
            return _("Abort")
        elif state == STATE_END:
            return _("Finished")
        elif state == STATE_PAUSE:
            return _("Pause")
        elif state == STATE_BUSY:
            return _("Busy")
        elif state == STATE_ACTIVE:
            return _("Active")
        elif state == STATE_IDLE:
            return _("Idle")
        elif state == STATE_UNKNOWN:
            return _("Unknown")

    def get_state(self, thread_name):
        try:
            return self.instances['thread'][thread_name].state()
        except AttributeError:
            return STATE_UNKNOWN

    def classify(self, elements):
        if self.device_root is not None and self.device_root is not self:
            return self.device_root.classify(elements)

    def load(self, pathname, **kwargs):
        if self.device_root is not None and self.device_root is not self:
            return self.device_root.load(pathname, **kwargs)

    def load_types(self, all=True):
        if self.device_root is not None and self.device_root is not self:
            return self.device_root.load_types(all)

    def save(self, pathname):
        if self.device_root is not None and self.device_root is not self:
            return self.device_root.save(pathname)

    def save_types(self):
        if self.device_root is not None and self.device_root is not self:
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
        self.device_version = "0.6.6"
        self.device_root = self

        # Persistent storage if it exists.
        if config is not None:
            self.set_config(config)

        # Translation function if exists.
        self.translation = lambda e: e  # Default for this code is do nothing.

        # Keymap/alias values
        self.keymap = {}
        self.alias = {}

        self.run_later = lambda listener, message: listener(message)

        self.register_module('Signaler', Signaler)
        self.register_module('Elemental', Elemental)
        self.register_module('Spooler', Spooler)

    def boot(self):
        """
        Kernel boot sequence. This should be called after all the registered devices are established.
        :return:
        """
        Device.boot(self)
        self.boot_keymap()
        self.boot_alias()
        self.device_boot()

    def shutdown(self, channel=None):
        """
        Begins kernel shutdown procedure.
        """
        self.save_keymap_alias()
        Device.shutdown(self, channel)
        self.flush()

    def save_keymap_alias(self):
        keys = self.derive('keymap')
        alias = self.derive('alias')

        keys.clear_persistent()
        alias.clear_persistent()

        for key in self.keymap:
            if key is None or len(key) == 0:
                continue
            keys.write_persistent(key, self.keymap[key])

        for key in self.alias:
            if key is None or len(key) == 0:
                continue
            alias.write_persistent(key, self.alias[key])

    def boot_keymap(self):
        self.keymap = dict()
        prefs = self.derive('keymap')
        prefs.load_persistent_string_dict(self.keymap)
        if not len(self.keymap):
            self.default_keymap()

    def boot_alias(self):
        self.alias = dict()
        prefs = self.derive('alias')
        prefs.load_persistent_string_dict(self.alias)
        if not len(self.alias):
            self.default_alias()

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
        self.keymap['numpad_multiply'] = '+scale_up'
        self.keymap['numpad_divide'] = '+scale_down'
        self.keymap['numpad_add'] = '+rotate_cw'
        self.keymap['numpad_subtract'] = '+rotate_ccw'
        self.keymap['control+a'] = 'element *'
        self.keymap['control+i'] = 'element ~'
        self.keymap['control+f'] = 'control Fill'
        self.keymap['control+s'] = 'control Stroke'
        self.keymap['control+r'] = 'rect 0 0 1000 1000'
        self.keymap['control+e'] = 'circle 500 500 500'
        self.keymap['control+d'] = 'element copy'
        self.keymap['control+shift+h'] = 'scale -1 1'
        self.keymap['control+shift+v'] = 'scale 1 -1'
        self.keymap['control+1'] = "bind 1 move $x $y"
        self.keymap['control+2'] = "bind 2 move $x $y"
        self.keymap['control+3'] = "bind 3 move $x $y"
        self.keymap['control+4'] = "bind 4 move $x $y"
        self.keymap['control+5'] = "bind 5 move $x $y"
        self.keymap['alt+r'] = 'raster'
        self.keymap['alt+e'] = 'engrave'
        self.keymap['alt+c'] = 'cut'
        self.keymap['delete'] = 'element delete'
        self.keymap['f4'] = "window open CameraInterface"
        self.keymap['f5'] = "refresh"
        self.keymap['f6'] = "window open JobSpooler"
        self.keymap['f7'] = "window open Controller"
        self.keymap['f8'] = "control Path"
        self.keymap['f9'] = "control Transform"
        self.keymap['control+f9'] = "control Flip"
        self.keymap['f12'] = "window open Terminal"
        self.keymap['control+alt+g'] = "image wizard Gold"
        self.keymap['control+alt+x'] = "image wizard Xin"
        self.keymap['control+alt+s'] = "image wizard Stipo"
        self.keymap['alt+f12'] = "terminal_ruida"
        self.keymap['alt+f11'] = 'terminal_watch'
        self.keymap['pause'] = "control Realtime Pause_Resume"
        self.keymap['home'] = "home"
        self.keymap['control+z'] = "reset"
        self.keymap['control+alt+shift+escape'] = 'reset_bind_alias'

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
        self.alias['terminal_ruida'] = "window open Terminal;ruidaserver"
        self.alias['terminal_watch'] = "window open Terminal;channel save usb;channel save send;channel save recv"
        self.alias['reset_bind_alias'] = "bind default;alias default"

    def device_boot(self):
        """
        Boots any devices that are set to boot.

        :return:
        """
        for device in self.derivable():
            try:
                d = int(device)
            except ValueError:
                continue
            settings = self.derive(str(d))
            device_name = settings.read_persistent(str, 'device_name', 'Lhystudios')
            autoboot = settings.read_persistent(bool, 'autoboot', True)
            if autoboot:
                dev = self.device_instance_open(device_name, uid=d, instance_name=str(device), config=self._config)
                dev.boot()

    def device_add(self, device_type, device_uid):
        settings = self.derive(str(device_uid))
        settings.setting(str, 'device_name', device_type)
        settings.setting(bool, 'autoboot', True)
        settings.flush()

    def register_loader(self, name, obj):
        self.registered['load'][name] = obj

    def register_saver(self, name, obj):
        self.registered['save'][name] = obj
