from LaserNode import LaserNode

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

        self.signal_dispatcher = lambda listener, message: listener(message)
        self.translation = None

        if config is not None:
            self.set_config(config)

    def __str__(self):
        return "Project"

    def __call__(self, code, message):
        if code in self.listeners:
            listeners = self.listeners[code]
            for listener in listeners:
                self.signal_dispatcher(listener, message)
        self.last_message[code] = message

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
        self('shutdown', 0)

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
        return self.threads[thread_name].state()

    def start(self, thread_name):
        self.threads[thread_name].start()

    def resume(self, thread_name):
        self.threads[thread_name].resume()

    def pause(self, thread_name):
        self.threads[thread_name].pause()

    def abort(self, thread_name):
        self.threads[thread_name].abort()

    def reset(self, thread_name):
        self.threads[thread_name].reset()

    def stop(self, thread_name):
        self.threads[thread_name].stop()

    def set_selected(self, selected):
        self.selected = selected
        self("selection", self.selected)


    def bbox(self):
        boundary_points = []
        for e in self.elements.flat_elements(types=('image', 'path', 'text')):
            box = e.box
            if box is None:
                continue
            top_left = e.matrix.point_in_matrix_space([box[0], box[1]])
            top_right = e.matrix.point_in_matrix_space([box[2], box[1]])
            bottom_left = e.matrix.point_in_matrix_space([box[0], box[3]])
            bottom_right = e.matrix.point_in_matrix_space([box[2], box[3]])
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

    def notify_change(self):
        self("elements", 0)

    def move_selected(self, dx, dy):
        if self.selected is None:
            return
        self.selected.move(dx, dy)
        for e in self.selected:
            e.move(dx, dy)
