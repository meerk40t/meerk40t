from threading import Lock, Thread
from LaserNode import LaserNode
import time

THREAD_STATE_UNKNOWN = -1
THREAD_STATE_UNSTARTED = 0
THREAD_STATE_STARTED = 1
THREAD_STATE_PAUSED = 2
THREAD_STATE_FINISHED = 3
THREAD_STATE_ABORT = 10


def get_state_string_from_state(state):
    if state == THREAD_STATE_UNSTARTED:
        return "Unstarted"
    elif state == THREAD_STATE_ABORT:
        return "Aborted"
    elif state == THREAD_STATE_FINISHED:
        return "Finished"
    elif state == THREAD_STATE_PAUSED:
        return "Paused"
    elif state == THREAD_STATE_STARTED:
        return "Started"
    elif state == THREAD_STATE_UNKNOWN:
        return "Unknown"


class KernelThread(Thread):
    def __init__(self, kernel):
        Thread.__init__(self)
        self.kernel = kernel
        self.state = THREAD_STATE_UNSTARTED

    def run(self):
        self.state = THREAD_STATE_STARTED
        while self.state != THREAD_STATE_ABORT:
            time.sleep(0.1)
            if self.state == THREAD_STATE_ABORT:
                return
            while self.state == THREAD_STATE_PAUSED:
                time.sleep(1.0)
            self.kernel.tick()
        self.state = THREAD_STATE_FINISHED

    def state(self):
        return self.state

    def resume(self):
        self.state = THREAD_STATE_STARTED

    def pause(self):
        self.state = THREAD_STATE_PAUSED

    def stop(self):
        self.state = THREAD_STATE_ABORT


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
    Writers convert LaserNode data into some types of files or streams.
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
    kernel.add_writer(file): Registers a qualified saver function.
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

    def __init__(self, spooler=None, config=None):
        self.spooler = spooler  # Class responsible for spooling commands
        self.elements = LaserNode(parent=self)

        self.config = None
        self.loaders = []
        self.writers = []
        self.effects = []
        self.operations = []
        self.threads = {}
        self.controls = {}

        self.listeners = {}
        self.last_message = {}

        self.selected = None
        self.windows = {}
        self.keymap = {}

        self.queue_lock = Lock()
        self.message_queue = {}

        self.run_later = lambda listener, message: listener(message)
        self.needs_queue_processed = False
        self.translation = None

        if config is not None:
            self.set_config(config)

        self.kernel_thread = KernelThread(self)
        self.add_thread('Ticks', self.kernel_thread)
        self.start('Ticks')

    def __str__(self):
        return "Project"

    def __call__(self, code, message):
        self.queue_lock.acquire(True)
        self.message_queue[code] = message
        self.queue_lock.release()
        self.needs_queue_processed = True

    def process_queue(self, *args):
        self.queue_lock.acquire(True)
        queue = self.message_queue
        self.message_queue = {}
        self.queue_lock.release()

        for code, message in queue.items():
            if code in self.listeners:
                listeners = self.listeners[code]
                for listener in listeners:
                    self.run_later(listener, message)
            self.last_message[code] = message
        self.needs_queue_processed = False

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
        :return:
        """
        if hasattr(self, setting_name) and getattr(self, setting_name) is not None:
            return
        if not setting_name.startswith('_') and self.config is not None:
            load_value = self[setting_type, setting_name, default]
        else:
            load_value = default
        setattr(self, setting_name, load_value)

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

    def close_old_window(self, name):
        if name in self.windows:
            old_window = self.windows[name]
            try:
                old_window.Close()
            except RuntimeError:
                pass  # already closed.

    def shutdown(self):
        """
        Invokes Kernel Shutdown.
        All threads are stopped.
        """
        for thread_name in self.threads:
            thread = self.threads[thread_name]
            try:
                thread.stop()
            except AttributeError:
                pass

    def listen(self, signal, function):
        if signal in self.listeners:
            listeners = self.listeners[signal]
            listeners.append(function)
        else:
            self.listeners[signal] = [function]
        if signal in self.last_message:
            last_message = self.last_message[signal]
            function(last_message)

    def unlisten(self, listener, code):
        if code in self.listeners:
            listeners = self.listeners[code]
            listeners.remove(listener)

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

    def get_state(self, thread_name):
        try:
            return self.threads[thread_name].state()
        except AttributeError:
            return THREAD_STATE_UNKNOWN

    def start(self, thread_name):
        try:
            self.threads[thread_name].start()
        except AttributeError:
            pass

    def resume(self, thread_name):
        try:
            self.threads[thread_name].resume()
        except AttributeError:
            pass

    def pause(self, thread_name):
        try:
            self.threads[thread_name].pause()
        except AttributeError:
            pass

    def abort(self, thread_name):
        try:
            self.threads[thread_name].abort()
        except AttributeError:
            pass

    def reset(self, thread_name):
        try:
            self.threads[thread_name].reset()
        except AttributeError:
            pass

    def stop(self, thread_name):
        try:
            self.threads[thread_name].stop()
        except AttributeError:
            pass

    def tick(self):
        """Called by KernelThread every 50ms to handle events."""
        if self.needs_queue_processed:
            self.run_later(self.process_queue, None)

    def set_selected(self, selected):
        self.selected = selected
        self("selection", self.selected)

    def notify_change(self):
        self("elements", 0)

    def move_selected(self, dx, dy):
        if self.selected is None:
            return
        self.selected.move(dx, dy)
        for e in self.selected:
            e.move(dx, dy)
