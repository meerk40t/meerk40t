import datetime
import functools
import inspect
import os
import platform
import re
import threading
import time
from collections import deque
from threading import Lock, Thread
from typing import Any, Callable, Dict, Generator, Optional, Tuple, Union

from .svgelements import Color

STATE_UNKNOWN = -1
STATE_INITIALIZE = 0
STATE_IDLE = 1
STATE_ACTIVE = 2
STATE_BUSY = 3
STATE_PAUSE = 4
STATE_END = 5
STATE_SUSPEND = 6  # Controller is suspended.
STATE_WAIT = 7  # Controller is waiting for something. This could be aborted.
STATE_TERMINATE = 10


_cmd_parse = [
    ("OPT", r"-([a-zA-Z]+)"),
    ("LONG", r"--([^ ,\t\n\x09\x0A\x0C\x0D]+)"),
    ("QPARAM", r"\"(.*?)\""),
    ("PARAM", r"([^ ,\t\n\x09\x0A\x0C\x0D]+)"),
    ("SKIP", r"[ ,\t\n\x09\x0A\x0C\x0D]+"),
]
_CMD_RE = re.compile("|".join("(?P<%s>%s)" % pair for pair in _cmd_parse))

# https://en.wikipedia.org/wiki/ANSI_escape_code#3-bit_and_4-bit
BBCODE_LIST = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bg-black": "\033[40m",
    "bg-red": "\033[41m",
    "bg-green": "\033[42m",
    "bg-yellow": "\033[43m",
    "bg-blue": "\033[44m",
    "bg-magenta": "\033[45m",
    "bg-cyan": "\033[46m",
    "bg-white": "\033[47m",
    "bold": "\033[1m",
    "/bold": "\033[22m",
    "italic": "\033[3m",
    "/italic": "\033[3m",
    "underline": "\033[4m",
    "/underline": "\033[24m",
    "underscore": "\033[4m",
    "/underscore": "\033[24m",
    "negative": "\033[7m",
    "positive": "\033[27m",
    "normal": "\033[0m",
}

# re for bbcode->ansi
RE_ANSI = re.compile(
    r"((?:\[raw\])(.*?)(?:\[/raw\]|$)|"
    + r"|".join([r"\[%s\]" % x for x in BBCODE_LIST])
    + r")",
    re.IGNORECASE,
)


class Modifier:
    """
    A modifier alters a context with additional functionality set during attachment and detachment.

    These are also booted and shutdown with the kernel's lifecycle. The modifications to the kernel are not expected
    to be undone. Rather detach should kill any secondary processes the modifier may possess.

    A modifiers can only be called once at any particular context.
    """

    def __init__(self, context: "Context", name: str = None, channel: "Channel" = None):
        self.context = context
        self.name = name
        self.state = STATE_INITIALIZE

    def __repr__(self):
        # pylint: disable=no-member
        return '{class_name}({context}, name="{name}", channel={channel})'.format(
            class_name=self.__class__.__name__,
            context=repr(self.context),
            name=self.name,
            channel="Channel({name})".format(name=self.channel.name)
            if hasattr(self, "channel") and self.channel
            else "None",
        )

    def boot(self, *args, **kwargs):
        """
        Called when the context the modifier attached to is booted. This is typical for devices.
        """
        pass

    def attach(self, *args, **kwargs):
        """
        Called by activate to attach module to device.

        This should be overloaded when making a specific module type for reuse, where using init would require specific
        subclassing, or for modules that are intended to expand the functionality of a device rather than compliment
        that functionality.
        """
        pass

    def detach(self, *args, **kwargs):
        """
        Called by deactivate to detach the module from device.

        Devices are not expected to undo all changes they made. This would typically only happen on the closing of a
        particular context.
        """
        pass


class Module:
    """
    Modules are a generic lifecycle object. These are registered in the kernel as modules and when open() is called for
    a context. When close() is called on the context, it will close and delete references to the opened module and call
    finalize().

    If an opened module is tries to open() a second time in a context and it was never closed. The device restore()
    function is called for the device, with the same args and kwargs that would have been called on __init__().

    Multiple instances of a module can be opened but this requires a different initialization name. Modules are not
    expected to modify their contexts.
    """

    def __init__(self, context: "Context", name: str = None, *args, **kwargs):
        self.context = context
        self.name = name
        self.state = STATE_INITIALIZE

    def __repr__(self):
        return '{class_name}({context}, name="{name}")'.format(
            class_name=self.__class__.__name__,
            context=repr(self.context),
            name=self.name,
        )

    def initialize(self, *args, **kwargs):
        """Initialize() is called after open() to setup the module and allow it to register various hooks into the
        kernelspace."""
        pass

    def restore(self, *args, **kwargs):
        """Called with the same values of __init()__ on an attempted reopen of a module with the same name at the
        same context."""
        pass

    def finalize(self, *args, **kwargs):
        """Finalize is called after close() to unhook various kernelspace hooks. This will happen if kernel is being
        shutdown or if this individual module is being closed on its own."""
        pass


class Context:
    """
    Contexts serve as path-relevant snapshots of the kernel. These are are the primary interaction between the modules
    and the kernel. They permit getting other contexts of the kernel as well. This should serve as the primary interface
    code between the kernel and the modules. And the location where modifiers are applied and modules are opened.

    Context store the persistent settings and settings from these locations are saved and loaded.

    Contexts have settings located at .<setting> and so long as this setting does not begin with _ or 'implicit' it
    will be reloaded when .setting() is called for the given attribute. This should be called by any module that intends
    access to an attribute even if it was already called.

    Most modules and functions are applied at the root level '/'.
    """

    def __init__(self, kernel: "Kernel", path: str):
        self._kernel = kernel
        self._path = path
        self._state = STATE_UNKNOWN
        self.opened = {}
        self.attached = {}

    def __repr__(self):
        return "Context('%s')" % self._path

    def __call__(self, data: str, **kwargs):
        if len(data) and data[-1] != "\n":
            data += "\n"
        return self._kernel.console(data)

    def boot(self, channel: "Channel" = None):
        """
        Boot calls all attached modifiers with the boot command.

        :param channel:
        :return:
        """
        for attached_name in self.attached:
            attached = self.attached[attached_name]
            attached.boot(channel=channel)

    # ==========
    # PATH INFORMATION
    # ==========

    def abs_path(self, subpath: str) -> str:
        """
        The absolute path function determines the absolute path of the given subpath within the current path of the
        context.

        :param subpath: relative path to the path at this context
        :return:
        """
        subpath = str(subpath)
        if subpath.startswith("/"):
            return subpath[1:]
        if self._path is None or self._path == "/":
            return subpath
        return "%s/%s" % (self._path, subpath)

    def derive(self, path: str) -> "Context":
        """
        Derive a subpath context.

        :param path:
        :return:
        """
        return self._kernel.get_context(self.abs_path(path))

    @property
    def root(self) -> "Context":
        return self.get_context("/")

    @property
    def path(self) -> str:
        return self._path

    @property
    def kernel(self) -> "Kernel":
        return self._kernel

    @property
    def _(self):
        return self._kernel.translation

    def get_context(self, path) -> "Context":
        """
        Get a context at a given path location.

        :param path: path location to get a context.
        :return:
        """
        return self._kernel.get_context(path)

    def derivable(self) -> Generator[str, None, None]:
        """
        Generate all sub derived paths.

        :return:
        """
        for e in self._kernel.derivable(self._path):
            yield e

    def subpaths(self) -> Generator["Context", None, None]:
        """
        Generate all subpaths of the current context with their path name and the relevant context.
        """
        for e in list(self._kernel.contexts):
            if e.startswith(self._path):
                yield e, self._kernel.contexts[e]

    def close_subpaths(self) -> None:
        """
        Find all subpaths of the current context and set them to None.

        This is not a maintenance operation. It's needed for rare instances during shutdown. All contexts will be
        shutdown normally during the shutdown in the lifecycle.
        """
        for e in list(self._kernel.contexts):
            if e.startswith(self._path):
                del self._kernel.contexts[e]

    # ==========
    # PERSISTENT SETTINGS.
    # ==========

    def setting(self, setting_type, key, default=None) -> Any:
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
        if not key.startswith("_"):
            load_value = self._kernel.read_persistent(
                setting_type, self.abs_path(key), default
            )
        else:
            load_value = default
        setattr(self, key, load_value)
        return load_value

    def flush(self) -> None:
        """
        Commit any and all values currently stored as attr for this object to persistent storage.
        """
        from .svgelements import Color

        props = [k for k, v in vars(self.__class__).items() if isinstance(v, property)]
        for attr in dir(self):
            if attr.startswith("_"):
                continue
            if attr in props:
                continue
            value = getattr(self, attr)
            if value is None:
                continue
            if isinstance(value, (int, bool, str, float, Color)):
                self._kernel.write_persistent(self.abs_path(attr), value)

    def get_persistent_value(self, t: type, key: str) -> Any:
        """
        Gets a specific value of the persistent attributes.

        The attribute type of the value depends on the provided object value default values.

        :param t: type of value
        :param key: relative key for the value
        :return: the value associated with the key otherwise None
        """
        return self._kernel.read_persistent(
            t,
            self.abs_path(key),
        )

    def load_persistent_object(self, obj: Any) -> None:
        """
        Loads values of the persistent attributes, at this context and assigns them to the provided object.

        The attribute type of the value depends on the provided object value default values.

        :param obj:
        :return:
        """

        from .svgelements import Color

        for attr in dir(obj):
            if attr.startswith("_"):
                continue
            obj_value = getattr(obj, attr)

            if not isinstance(obj_value, (int, float, str, bool, Color)):
                continue

            load_value = self.get_persistent_value(
                type(obj_value),
                attr,
            )

            try:
                setattr(obj, attr, load_value)
                setattr(self, attr, load_value)
            except AttributeError:
                pass

    def clear_persistent(self) -> None:
        """
        Delegate to Kernel to clear the persistent settings located at this context.
        """
        self._kernel.clear_persistent(self._path)

    def write_persistent(
        self, key: str, value: Union[int, float, str, bool, Color]
    ) -> None:
        """
        Delegate to Kernel to write the given key at this context to persistent settings. This is typically done during
        shutdown but there are a variety of reasons to force this call early.

        If the persistence object is not yet established this function cannot succeed.
        """
        self._kernel.write_persistent(self.abs_path(key), value)

    def set_attrib_keys(self) -> None:
        """
        Iterate all the entries keys for the registered persistent settings, adds a None attribute for any key that
        exists.

        :return:
        """
        for k in self._kernel.keylist(self._path):
            if not hasattr(self, k):
                setattr(self, k, None)

    # ==========
    # CONTROL: Deprecated.
    # ==========

    def execute(self, control: str) -> None:
        """
        Execute the given control code relative to the path of this context.

        :param control: Function to execute relative to the current position.
        :return:
        """
        try:
            funct = self._kernel.registered[self.abs_path("control/%s" % control)]
        except KeyError:
            return
        funct()

    # ==========
    # DELEGATES
    # ==========

    def register(self, path: str, obj: Any) -> None:
        """
        Delegate to Kernel
        """
        self._kernel.register(path, obj)

    @staticmethod
    def console_argument(*args, **kwargs) -> Callable:
        """
        Delegate to Kernel
        """
        return Kernel.console_argument(*args, **kwargs)

    @staticmethod
    def console_option(*args, **kwargs) -> Callable:
        """
        Delegate to Kernel
        """
        return Kernel.console_option(*args, **kwargs)

    def console_command(self, *args, **kwargs) -> Callable:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_command being registered.
        """
        return Kernel.console_command(self._kernel, *args, **kwargs)

    @property
    def registered(self) -> Dict[str, Any]:
        """
        Delegate to Kernel
        """
        return self._kernel.registered

    @property
    def contexts(self) -> Dict[str, "Context"]:
        return self._kernel.contexts

    def has_feature(self, feature: str) -> bool:
        """
        Return whether or not this is a registered feature within the kernel.

        :param feature: feature to check if exists in kernel.
        :return:
        """
        return feature in self._kernel.registered

    def match(self, matchtext: str, suffix: bool = False) -> Generator[str, None, None]:
        """
        Delegate of Kernel match.

        :param matchtext:  regex matchtext to locate.
        :param suffix: provide the suffix of the match only.
        :yield: matched entries.
        """
        for m in self._kernel.match(matchtext, suffix):
            yield m

    def console(self, data: str) -> None:
        """
        Call the Kernel's Console with the given data.

        Note: '\n' is usually used to execute these functions and this is not added by default.
        """
        self._kernel.console(data)

    def schedule(self, job: Union["Job", Any]) -> None:
        """
        Call the Kernel's Scheduler with the given job.
        """
        self._kernel.schedule(job)

    def unschedule(self, job: Union["Job", Any]) -> None:
        """
        Unschedule a given job.

        This is often unneeded if the job completes on it's own, it will be removed from the scheduler.
        """
        self._kernel.unschedule(job)

    def threaded(
        self,
        func: Callable,
        *args,
        thread_name: str = None,
        result: Callable = None,
        daemon: bool = False,
    ):
        """
        Calls a thread to be registered in the kernel.

        Registered threads must complete before shutdown can be completed. These will told to stop and waited on until
        completion.

        The result function will be called with any returned result func.
        """
        return self._kernel.threaded(
            func,
            *args,
            thread_name=thread_name,
            result=result,
            daemon=daemon,
        )

    # ==========
    # MODULES
    # ==========

    def find(self, path: str) -> Union["Module", None]:
        """
        Finds a loaded instance. Or returns None if not such instance.

        Note: 'name' is not necessarily the type of instance. It could be the named value of the instance.

        :param path: The opened path to find the given instance.
        :return: The instance, if found, otherwise None.
        """
        try:
            return self.opened[path]
        except KeyError:
            return None

    def open(self, registered_path: str, *args, **kwargs) -> "Module":
        """
        Opens a registered module with the same instance path as the registered path.

        This is fairly standard but should not be used if the goal would be to open the same module several times.
        Unless those modules are being opened at different contexts.

        :param registered_path: registered path of the given module.
        :param args: args to open the module with.
        :param kwargs: kwargs to open the module with.
        :return:
        """
        return self.open_as(registered_path, registered_path, *args, **kwargs)

    def open_as(
        self, registered_path: str, instance_path: str, *args, **kwargs
    ) -> "Module":
        """
        Opens a registered module. If that module already exists it returns the already open module.

        Instance_name is the name under which this given module is opened.

        If the module already exists, the restore function is called on that object (if restore() exists), with the same
        args and kwargs that were intended for the init() routine.

        :param registered_path: path of object being opened.
        :param instance_path: path of object should be attached.
        :param args: Args to pass to newly opened module.
        :param kwargs: Kwargs to pass to newly opened module.
        :return: Opened module.
        """
        try:
            find = self.opened[instance_path]
            try:
                find.restore(*args, **kwargs)
            except AttributeError:
                pass
            return find
        except KeyError:
            pass

        try:
            open_object = self._kernel.registered[registered_path]
        except KeyError:
            raise ValueError

        instance = open_object(self, instance_path, *args, **kwargs)
        channel = self._kernel.channel("open", self._path)
        instance.initialize(channel=channel)

        self.opened[instance_path] = instance
        return instance

    def close(self, instance_path: str, *args, **kwargs) -> None:
        """
        Closes an opened module instance. Located at the instance_path location.

        This calls the close() function on the object (which may not exist). Then calls finalize() on the module,
        which should exist.

        :param instance_path: Instance path to close.
        :return:
        """
        try:
            instance = self.opened[instance_path]
        except KeyError:
            return  # Nothing to close.
        try:
            del self.opened[instance_path]
        except KeyError:
            pass

        try:
            instance.close()
        except AttributeError:
            pass
        instance.finalize(*args, **kwargs)

    # ==========
    # MODIFIERS
    # ==========

    def activate(self, registered_path: str, *args, **kwargs) -> "Modifier":
        """
        Activates a modifier at this context. activate() calls and attaches a modifier located at the given path
        to be attached to this context.

        The modifier is opened and attached at the current context. Unlike modules there is no instance_path and the
        registered_path should be a singleton. It is expected that attached modifiers will modify the context.

        :param registered_path: registered_path location of the modifier.
        :param args: arguments to call the modifier
        :param kwargs: kwargs to call the modifier
        :return: Modifier object.
        """
        try:
            find = self.attached[registered_path]
            try:
                find.restore(*args, **kwargs)
            except AttributeError:
                pass
            return find
        except KeyError:
            pass
        try:
            open_object = self._kernel.registered[registered_path]
        except KeyError:
            raise ValueError("Modifier not found.")

        instance = open_object(self, registered_path, *args, **kwargs)
        self.attached[registered_path] = instance
        instance.attach(self, *args, **kwargs)
        return instance

    def deactivate(self, instance_path: str, *args, **kwargs) -> None:
        """
        Deactivate a modifier attached to this context.
        The detach() is called on the modifier and modifier is deleted from the list of attached. This should be called
        during the shutdown of the Kernel. There is no expectation that modifiers actually remove their functions during
        this call.

        :param instance_path: Attached path location.
        :return:
        """
        instance = self.attached[instance_path]
        instance.detach(self, *args, **kwargs)
        del self.attached[instance_path]

    # ==========
    # DELEGATES via PATH.
    # ==========

    def signal(self, code: str, *message) -> None:
        """
        Send Signal to all registered listeners.

        :param code: Code to delegate at this given context location.
        :param message: Message to send.
        :return:
        """
        self._kernel.signal(code, self._path, *message)

    def last_signal(self, code: str) -> Tuple:
        """
        Returns the last signal at the given code.

        :param code: Code to delegate at this given context location.
        :return: message value of the last signal sent for that code.
        """
        return self._kernel.last_signal(code, self._path)

    def listen(self, signal: str, process: Callable) -> None:
        """
        Listen at a particular signal with a given process.

        :param signal: Signal code to listen for
        :param process: listener to be attached
        :return:
        """
        self._kernel.listen(signal, self._path, process)

    def unlisten(self, signal: str, process: Callable):
        """
        Unlisten to a particular signal with a given process.

        This should be called on the ending of the lifecycle of whatever process listened to the given signal.

        :param signal: Signal to unlisten for.
        :param process: listener that is to be detached.
        :return:
        """
        self._kernel.unlisten(signal, self._path, process)

    def channel(self, channel: str, *args, **kwargs) -> "Channel":
        """
        Return a channel from the kernel location

        :param channel: Channel to be opened.
        :return: Channel object that is opened.
        """
        return self._kernel.channel(channel, *args, **kwargs)

    def console_function(self, data: str) -> "ConsoleFunction":
        """
        Returns a function that calls a console command. This serves as a Job to be used in Scheduler or simply a
        function with the command as the str form.
        """
        return ConsoleFunction(self, data)


class Kernel:
    """
    The Kernel serves as the central hub of communication between different objects within the system. These are mapped
    to particular contexts that have locations within the kernel. The contexts can have modules opened and modifiers
    applied to them. The kernel serves to store the location of registered objects, as well as providing a scheduler,
    signals, channels, and a command console to be used by the modules, modifiers, devices, and other objects.

    The Kernel stores a persistence object, thread interactions, contexts, a translation routine, a run_later operation,
    jobs for the scheduler, listeners for signals, channel information, a list of devices, registered commands.

    Devices are contexts with a device. These are expected to have a Spooler attached, and the path should consist
    of numbers.

    """

    def __init__(
        self,
        name: str,
        version: str,
        profile: str,
        path: str = "/",
        config=None,
        ansi=False,
    ):
        """
        Initialize the Kernel. This sets core attributes of the ecosystem that are accessable to all modules.

        Name: The application name.
        Version: The version number of the application.
        Profile: The name to save our data under (this is often the same as name except if we want unused setting).
        Path: The subpath all data should be saved under. This is a prefix of data to silently add to all data.
        Config: This is the persistence object used to save. While official agnostic, it's actually strikingly identical
                    to a wx.Config object.
        """
        self.name = name
        self.profile = profile
        self.version = version
        self._path = path
        self.lifecycle = "init"

        # Store the plugins for the kernel. During lifecycle events all plugins will be called with the new lifecycle
        self._plugins = []

        # All established contexts.
        self.contexts = {}

        # All registered threads.
        self.threads = {}
        self.thread_lock = Lock()

        # All registered locations within the kernel.
        self.registered = {}

        # The translation object to be overridden by any valid translation functions
        self.translation = lambda e: e

        # The function used to process the signals. This is useful if signals should be kept to a single thread.
        self.run_later = lambda execute, op: execute(op)
        self.state = STATE_INITIALIZE

        # Scheduler
        self.jobs = {}
        self.scheduler_thread = None
        self.signal_job = None
        self.listeners = {}
        self.adding_listeners = []
        self.removing_listeners = []
        self.last_message = {}
        self.queue_lock = Lock()
        self.message_queue = {}
        self._is_queue_processing = False

        # Channels
        self.channels = {}

        # Registered Commands.
        self.commands = []
        self.console_job = Job(
            job_name="kernel.console.ticks",
            process=self._console_job_tick,
            interval=0.1,
        )
        self._current_directory = "."
        self._console_buffer = ""
        self.queue = []
        self._console_channel = self.channel("console", timestamp=True, ansi=ansi)
        self.console_channel_file = None

        if config is not None:
            self.set_config(config)
        else:
            self._config = None

    def __str__(self):
        return "Kernel()"

    def __setitem__(self, key: str, value: Union[str, int, bool, float, Color]):
        """
        Kernel value settings. If Config is registered this will be persistent.

        :param key: Key to set.
        :param value: Value to set
        :return: None
        """
        if isinstance(key, str):
            self.write_persistent(key, value)

    def __getitem__(
        self, item: Union[Tuple, str]
    ) -> Union[str, int, bool, float, Color]:
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

    def open_safe(self, *args):
        try:
            return open(*args)
        except PermissionError:
            from os import chdir

            original = os.getcwd()
            chdir(get_safe_path(self.name, True))
            print(
                "Changing working directory from %s to %s."
                % (str(original), str(os.getcwd()))
            )
            return open(*args)

    def _start_debugging(self) -> None:
        """
        Debug function hooks all functions within the device with a debug call that saves the data to the disk and
        prints that information.

        :return:
        """
        import types

        filename = "{name}-debug-{date:%Y-%m-%d_%H_%M_%S}.txt".format(
            name=self.name, date=datetime.datetime.now()
        )
        debug_file = self.open_safe(filename, "a")
        debug_file.write("\n\n\n")

        def debug(func: Callable, obj: Any) -> Callable:
            @functools.wraps(func)
            def wrapper_debug(*args, **kwargs):
                args_repr = [repr(a) for a in args]

                kwargs_repr = ["%s=%s" % (k, v) for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
                start = "Calling %s.%s(%s)" % (str(obj), func.__name__, signature)
                debug_file.write(start + "\n")
                print(start)
                t = time.time()
                value = func(*args, **kwargs)
                t = time.time() - t
                finish = "    %s returned %s after %fms" % (
                    func.__name__,
                    value,
                    t * 1000,
                )
                print(finish)
                debug_file.write(finish + "\n")
                debug_file.flush()
                return value

            return wrapper_debug

        context = self.root
        attach_list = [modules for modules, module_name in context.opened.items()]
        attach_list.append(self)
        for obj in attach_list:
            for attr in dir(obj):
                if attr.startswith("_"):
                    continue
                fn = getattr(obj, attr)
                if not isinstance(fn, types.FunctionType) and not isinstance(
                    fn, types.MethodType
                ):
                    continue
                setattr(obj, attr, debug(fn, obj))

    # ==========
    # PLUGIN API
    # ==========

    def add_plugin(self, plugin: Callable) -> None:
        """
        Accepts a plugin function. This should accept two arguments: kernel and lifecycle.

        The kernel is a copy of this kernel as an instanced object and the lifecycle is the stage of the kernel
        in the program lifecycle. Plugins should be added during startup.

        :param plugin:
        :return:
        """
        if plugin not in self._plugins:
            self._plugins.append(plugin)

    # ==========
    # LIFECYCLE PROCESSES
    # ==========

    def bootstrap(self, lifecycle: str) -> None:
        """
        Bootstraps all plugins at this particular lifecycle event.

        :param lifecycle:
        :return:

        Meerk40t bootstrap sequence:
        * console / gui
        * preregister
        * register
        * configure
        * boot
        * ready
        * finished
        """
        if self.lifecycle == "shutdown":
            return  # No backsies.
        self.lifecycle = lifecycle
        for plugin in self._plugins:
            plugin(self, lifecycle)
        self.signal("lifecycle;%s" % lifecycle, None, True)

    def boot(self) -> None:
        """
        Kernel boot sequence. This should be called after all the registered devices are established.

        :return:
        """

        self.command_boot()
        self.scheduler_thread = self.threaded(self.run, thread_name="Scheduler")
        self.signal_job = self.add_job(
            run=self.process_queue,
            name="kernel.signals",
            interval=0.005,
            run_main=True,
            conditional=lambda: not self._is_queue_processing,
        )
        self.bootstrap("boot")
        self.register("control/Debug Device", self._start_debugging)
        for context_name in list(self.contexts):
            context = self.contexts[context_name]
            context.boot()

    def shutdown(self):
        """
        Starts full shutdown procedure.

        Suspends all signals.
        Each initialized context is flushed and shutdown.
        Each opened module within the context is stopped and closed.
        Each attached modifier is shutdown and deactivated.

        All threads are stopped.

        Any residual attached listeners are made warnings.

        :param channel:
        :return:
        """
        channel = self.channel("shutdown")
        self.state = STATE_END  # Terminates the Scheduler.

        self.bootstrap("shutdown")
        _ = self.translation

        try:
            self.process_queue()  # Notify listeners of state.
        except RuntimeError:
            pass  # Runtime error for gui objects in the process of being killed.
        # Suspend Signals

        def signal(code, path, *message):
            if channel:
                channel(_("Suspended Signal: %s for %s" % (code, message)))

        # pylint: disable=method-hidden
        self.signal = signal  # redefine signal function, hidden by design

        def console(code):
            if channel:
                for c in code.split("\n"):
                    if c:
                        channel(_("Suspended Command: %s" % c))

        # pylint: disable=method-hidden
        self.console = console  # redefine console signal, hidden by design

        self.process_queue()  # Process last events.

        # Close Modules
        for context_name in list(self.contexts):
            context = self.contexts[context_name]
            if context is None:
                continue
            for opened_name in list(context.opened):
                obj = context.opened[opened_name]
                if channel:
                    channel(
                        _("%s: Finalizing Module %s: %s")
                        % (str(context), opened_name, str(obj))
                    )
                context.close(opened_name, channel=channel, shutdown=True)

        self.process_queue()  # Process last events.

        # Detach Modifiers
        for context_name in list(self.contexts):
            try:
                context = self.contexts[context_name]
            except KeyError:
                # Context was deleted by the deactivation of another context.
                continue
            for attached_name in list(context.attached):
                obj = context.attached[attached_name]
                if channel:
                    channel(
                        _("%s: Detaching %s: %s")
                        % (str(context), attached_name, str(obj))
                    )
                context.deactivate(attached_name, channel=channel)

        # Context Flush and Shutdown
        for context_name in list(self.contexts):
            context = self.contexts[context_name]
            if context is None:
                continue
            if channel:
                channel(_("Saving Context State: '%s'") % str(context))
            context.flush()
            del self.contexts[context_name]
            if channel:
                channel(_("Context Shutdown Finished: '%s'") % str(context))
        try:
            del self._config
            if channel:
                channel(_("Destroying persistence object"))
        except AttributeError:
            if channel:
                channel(_("Could not destroy persistence object"))
            pass
        if channel:
            channel(_("Shutting down."))

        # Stop/Wait for all threads
        thread_count = 0
        for thread_name in list(self.threads):
            thread_count += 1
            try:
                thread = self.threads[thread_name]
            except KeyError:
                if channel:
                    channel(_("Thread %s exited safely") % thread_name)
                continue

            if not thread.is_alive:
                if channel:
                    channel(
                        _("WARNING: Dead thread %s still registered to %s.")
                        % (thread_name, str(thread))
                    )
                continue
            if channel:
                channel(_("Finishing Thread %s for %s") % (thread_name, str(thread)))
            try:
                if thread is threading.currentThread():
                    if channel:
                        channel(_("%s is the current shutdown thread") % thread_name)
                    continue
                if channel:
                    channel(_("Asking thread to stop."))
                thread.stop()
            except AttributeError:
                pass
            if not thread.daemon:
                if channel:
                    channel(_("Waiting for thread %s: %s") % (thread_name, str(thread)))
                thread.join()
                if channel:
                    channel(
                        _("Thread %s has finished. %s") % (thread_name, str(thread))
                    )
            else:
                if channel:
                    channel(
                        _("Thread %s is daemon. It will die automatically: %s")
                        % (thread_name, str(thread))
                    )
        if thread_count == 0:
            if channel:
                channel(_("No threads required halting."))

        for key, listener in self.listeners.items():
            if len(listener):
                if channel:
                    channel(
                        _("WARNING: Listener '%s' still registered to %s.")
                        % (key, str(listener))
                    )
        self.last_message = {}
        self.listeners = {}
        if (
            self.scheduler_thread != threading.current_thread()
        ):  # Join if not this thread.
            self.scheduler_thread.join()
        if channel:
            channel(_("Shutdown."))
        self._state = STATE_TERMINATE

    # ==========
    # REGISTRATION
    # ==========

    def match(self, matchtext: str, suffix: bool = False) -> Generator[str, None, None]:
        """
        Lists all registered paths that regex match the given matchtext

        :param matchtext: match text to match.
        :param suffix: provide the suffix of the match only.
        :return:
        """
        match = re.compile(matchtext)
        for r in self.registered:
            if match.match(r):
                if suffix:
                    yield list(r.split("/"))[-1]
                else:
                    yield r

    def register(self, path: str, obj: Any) -> None:
        """
        Register an element at a given subpath.
        If this Kernel is not root, then it is registered relative to this location.

        :param path: a "/" separated hierarchical index to the object
        :param obj: object to be registered
        :return:
        """
        self.registered[path] = obj
        try:
            obj.sub_register(self)
        except AttributeError:
            pass

    @staticmethod
    def console_option(name: str, short: str = None, **kwargs) -> Callable:
        try:
            if short.startswith("-"):
                short = short[1:]
        except Exception:
            pass

        def decor(func):
            kwargs["name"] = name
            kwargs["short"] = short
            if "action" in kwargs:
                kwargs["type"] = bool
            elif "type" not in kwargs:
                kwargs["type"] = str
            func.options.insert(0, kwargs)
            return func

        return decor

    @staticmethod
    def console_argument(name: str, **kwargs) -> Callable:
        def decor(func):
            kwargs["name"] = name
            if "type" not in kwargs:
                kwargs["type"] = str
            func.arguments.insert(0, kwargs)
            return func

        return decor

    @staticmethod
    def _cmd_parser(text: str) -> Generator[Tuple[str, str, int, int], None, None]:
        pos = 0
        limit = len(text)
        while pos < limit:
            match = _CMD_RE.match(text, pos)
            if match is None:
                break  # No more matches.
            kind = match.lastgroup
            start = pos
            pos = match.end()
            if kind == "SKIP":
                continue
            elif kind == "PARAM":
                value = match.group()
                yield kind, value, start, pos
            elif kind == "QPARAM":
                value = match.group()
                yield "PARAM", value[1:-1], start, pos
            elif kind == "LONG":
                value = match.group()
                yield kind, value[2:], start, pos
            elif kind == "OPT":
                value = match.group()
                for letter in value[1:]:
                    yield kind, letter, start, pos
                    start += 1

    def console_command(
        self,
        path: Union[str, Tuple[str, ...]] = None,
        regex: bool = False,
        hidden: bool = False,
        help: str = None,
        input_type: Union[str, Tuple[str, ...]] = None,
        output_type: str = None,
    ):
        """
        Console Command registers is a decorator that registers a command to the kernel. Any commands that execute
        within the console are registered with this decorator. It various attributes that define how the decorator
        should be treated. Commands work with named contexts in a pipelined architecture. So "element" commands output
        must be followed by "element" command inputs. The input_type and output_type do not have to match and can be
        a tuple of different types. None refers to the base context.

        The long_help is the docstring of the actual function itself.

        @param path: command name of the command being registered
        @param regex: Should this command name match regex command values.
        @param hidden: Whether this command shows up in `help` or not.
        @param help: What should the help for this command be.
        @param input_type: What is the incoming context for the command
        @param output_type: What is the outgoing context for the command
        @return:
        """

        def decorator(func: Callable):
            @functools.wraps(func)
            def inner(command: str, remainder: str, channel: "Channel", **ik):
                options = inner.options
                arguments = inner.arguments
                stack = list()
                stack.extend(arguments)
                kwargs = dict()
                argument_index = 0
                opt_index = 0
                output_type = inner.output_type
                pos = 0
                for kind, value, start, pos in Kernel._cmd_parser(remainder):
                    if kind == "PARAM":
                        if argument_index == len(stack):
                            pos = start
                            break  # Nothing else is expected.
                        k = stack[argument_index]
                        argument_index += 1
                        if "type" in k and value is not None:
                            try:
                                value = k["type"](value)
                            except ValueError:
                                raise SyntaxError(
                                    "'%s' does not cast to %s"
                                    % (str(value), str(k["type"]))
                                )
                        key = k["name"]
                        current = kwargs.get(key, True)
                        if current is True:
                            kwargs[key] = [value]
                        else:
                            kwargs[key].append(value)
                        opt_index = argument_index
                    elif kind == "LONG":
                        for pk in options:
                            if value == pk["name"]:
                                if pk.get("action") != "store_true":
                                    count = pk.get("nargs", 1)
                                    for n in range(count):
                                        stack.insert(opt_index, pk)
                                        opt_index += 1
                                kwargs[value] = True
                                break
                        opt_index = argument_index
                    elif kind == "OPT":
                        for pk in options:
                            if value == pk["short"]:
                                if pk.get("action") != "store_true":
                                    count = pk.get("nargs", 1)
                                    for n in range(count):
                                        stack.insert(opt_index, pk)
                                        opt_index += 1
                                kwargs[pk["name"]] = True
                                break

                # Any unprocessed positional arguments get default values.
                for a in range(argument_index, len(stack)):
                    k = stack[a]
                    value = k.get("default")
                    if "type" in k and value is not None:
                        value = k["type"](value)
                    key = k["name"]
                    current = kwargs.get(key)
                    if current is None:
                        kwargs[key] = [value]
                    else:
                        try:
                            kwargs[key].append(value)
                        except AttributeError as e:
                            raise ValueError(f"{command} {remainder} syntax is malformed. Please report.")

                # Any singleton list arguments should become their only element.
                for a in range(len(stack)):
                    k = stack[a]
                    key = k["name"]
                    current = kwargs.get(key)
                    if isinstance(current, list):
                        if len(current) == 1:
                            kwargs[key] = current[0]

                remainder = remainder[pos:]
                if len(remainder) > 0:
                    kwargs["remainder"] = remainder
                    kwargs["args"] = remainder.split()
                if output_type is None:
                    remainder = ""  # not chaining
                returned = func(command=command, channel=channel, **ik, **kwargs)
                if returned is None:
                    value = None
                    out_type = None
                else:
                    if not isinstance(returned, tuple) or len(returned) != 2:
                        raise ValueError(
                            '"%s" from command "%s" returned improper values. "%s"'
                            % (str(returned), command, str(kwargs))
                        )
                    out_type, value = returned
                return value, remainder, out_type

            if hasattr(inner, "arguments"):
                raise MalformedCommandRegistration(
                    "Applying console_command() to console_command()"
                )

            # Main Decorator
            cmds = path if isinstance(path, tuple) else (path,)
            ins = input_type if isinstance(input_type, tuple) else (input_type,)
            inner.long_help = func.__doc__
            inner.help = help
            inner.regex = regex
            inner.hidden = hidden
            inner.input_type = input_type
            inner.output_type = output_type

            inner.arguments = list()
            inner.options = list()

            for cmd in cmds:
                for i in ins:
                    p = "command/%s/%s" % (i, cmd)
                    self.register(p, inner)
            return inner

        return decorator

    # ==========
    # PATH & CONTEXTS
    # ==========

    def abs_path(self, subpath: str) -> str:
        """
        The absolute path function determines the absolute path of the given subpath within the current path.

        :param subpath: relative path to the path at this context
        :return:
        """
        subpath = str(subpath)
        if subpath.startswith("/"):
            subpath = subpath[1:]
        return "/%s/%s" % (self._path, subpath)

    @property
    def root(self) -> "Context":
        return self.get_context("/")

    def get_context(self, path: str) -> Context:
        """
        Create a context derived from this kernel, at the given path.

        If this has been created previously, then return the previous object.

        :param path: path of context being gotten
        :return: Context object.
        """
        try:
            return self.contexts[path]
        except KeyError:
            pass
        derive = Context(self, path=path)
        self.contexts[path] = derive
        return derive

    def derivable(self, path: str) -> Generator[str, None, None]:
        """
        Finds all derivable paths within the config from the set path location.
        :param path:
        :return:
        """
        if self._config is None:
            return
        path = self.abs_path(path)
        self._config.SetPath(path)
        more, value, index = self._config.GetFirstGroup()
        while more:
            yield value
            more, value, index = self._config.GetNextGroup(index)
        self._config.SetPath("/")

    def read_item_persistent(self, key: str) -> Optional[str]:
        """Directly read from persistent storage the value of an item."""
        if self._config is None:
            return None
        return self._config.Read(self.abs_path(key))

    def read_persistent(
        self, t: type, key: str, default: Union[str, int, float, bool, Color] = None
    ) -> Any:
        """
        Directly read from persistent storage the value of an item.

        :param t: datatype.
        :param key: key used to reference item.
        :param default: default value if item does not exist.
        :return: value
        """
        if self._config is None:
            return default
        key = self.abs_path(key)
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
                return Color(argb=self._config.ReadInt(key, default))
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
                return Color(argb=self._config.ReadInt(key))
        return default

    def write_persistent(self, key: str, value: Union[str, int, float, bool, Color]):
        """
        Directly write the value to persistent storage.

        :param key: The item key being read.
        :param value: the value of the item.
        """
        if self._config is None:
            return
        key = self.abs_path(key)
        if isinstance(value, str):
            self._config.Write(key, value)
        elif isinstance(value, int):
            self._config.WriteInt(key, value)
        elif isinstance(value, float):
            self._config.WriteFloat(key, value)
        elif isinstance(value, bool):
            self._config.WriteBool(key, value)
        elif isinstance(value, Color):
            self._config.WriteInt(key, value.argb)

    def clear_persistent(self, path: str):
        if self._config is None:
            return
        path = self.abs_path(path)
        self._config.DeleteGroup(path)

    def delete_persistent(self, key: str):
        if self._config is None:
            return
        key = self.abs_path(key)
        self._config.DeleteEntry(key)

    def load_persistent_string_dict(
        self, path: str, dictionary: Optional[Dict] = None, suffix: bool = False
    ) -> Dict:
        if dictionary is None:
            dictionary = dict()
        for k in list(self.keylist(path)):
            item = self.read_item_persistent(k)
            if suffix:
                k = k.split("/")[-1]
            dictionary[k] = item
        return dictionary

    read_persistent_string_dict = load_persistent_string_dict

    def keylist(self, path: str) -> Generator[str, None, None]:
        """
        Get all keys located at the given path location. The keys are listed in absolute path locations.

        :param path:
        :return:
        """
        if self._config is None:
            return
        path = self.abs_path(path)
        self._config.SetPath(path)
        more, value, index = self._config.GetFirstEntry()
        while more:
            yield "%s/%s" % (path, value)
            more, value, index = self._config.GetNextEntry(index)
        self._config.SetPath("/")

    def set_config(self, config: Any) -> None:
        """
        Set the config object.

        :param config: Persistent storage object.
        :return:
        """
        if config is None:
            return
        self._config = config

    # ==========
    # THREADS PROCESSING
    # ==========

    def threaded(
        self,
        func: Callable,
        *args,
        thread_name: str = None,
        result: Callable = None,
        daemon: bool = False,
    ) -> Thread:
        """
        Register a thread, and run the provided function with the name if needed. When the function finishes this thread
        will exit, and deregister itself. During shutdown any active threads created will be told to stop and the kernel
        will wait until such time as it stops.

        result is a threadsafe execution. It will execute if the crashes or exits normally. If there was a return from
        the function call the result will be passed this value. If there is not one or it is None, None will be passed.
        result must take 1 argument. This permits final calls to the thread.

        :param func: The function to be executed.
        :param thread_name: The name under which the thread should be registered.
        :param result: Runs in the thread after func terminates but before the thread itself terminates.
        :param daemon: set this thread as daemon
        :return: The thread object created.
        """
        self.thread_lock.acquire(True)  # Prevent dup-threading.
        channel = self.channel("threads")
        _ = self.translation
        if thread_name is None:
            thread_name = func.__name__
        try:
            old_thread = self.threads[thread_name]
            channel(_("Thread: %s already exists. Waiting..." % thread_name))
            old_thread.join()
            # We must wait for the old thread to complete before running. Lock.
        except KeyError:
            # No current thread
            pass
        thread = Thread(name=thread_name)
        channel(_("Thread: %s, Initialized" % thread_name))

        def run():
            func_result = None
            channel(_("Thread: %s, Set" % thread_name))
            try:
                channel(_("Thread: %s, Start" % thread_name))
                func_result = func(*args)
                channel(_("Thread: %s, End " % thread_name))
            except Exception:
                channel(_("Thread: %s, Exception-End" % thread_name))
                import sys

                channel(str(sys.exc_info()))
                sys.excepthook(*sys.exc_info())
            channel(_("Thread: %s, Unset" % thread_name))
            del self.threads[thread_name]
            if result is not None:
                result(func_result)

        thread.run = run
        self.threads[thread_name] = thread
        thread.daemon = daemon
        thread.start()
        self.thread_lock.release()
        return thread

    def get_text_thread_state(self, state: int) -> str:
        _ = self.translation
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
        elif state == STATE_WAIT:
            return _("Waiting")
        elif state == STATE_ACTIVE:
            return _("Active")
        elif state == STATE_IDLE:
            return _("Idle")
        elif state == STATE_UNKNOWN:
            return _("Unknown")

    # ==========
    # SCHEDULER
    # ==========

    def run(self) -> None:
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
            for job_name in list(jobs):
                try:
                    job = jobs[job_name]
                except KeyError:
                    continue  # Job was removed during execution.

                # Checking if jobs should run.
                if job.scheduled:
                    job._next_run = 0  # Set to zero while running.
                    if job.times is not None:
                        job.times = job.times - 1
                        if job.times <= 0:
                            del jobs[job_name]
                        if job.times < 0:
                            continue
                    try:
                        if job.run_main and self.run_later is not None:
                            self.run_later(job.process, job.args)
                        else:
                            if job.args is None:
                                job.process()
                            else:
                                job.process(*job.args)
                    except Exception:
                        import sys

                        sys.excepthook(*sys.exc_info())
                    job._last_run = time.time()
                    job._next_run += job._last_run + job.interval
        self.state = STATE_END

    def schedule(self, job: "Job") -> "Job":
        self.jobs[job.job_name] = job
        return job

    def unschedule(self, job: "Job") -> "Job":
        try:
            del self.jobs[job.job_name]
        except KeyError:
            pass  # No such job.
        return job

    def add_job(
        self,
        run: Callable,
        name: Optional[str] = None,
        args: Tuple = (),
        interval: float = 1.0,
        times: int = None,
        run_main: bool = False,
        conditional: Callable = None,
    ) -> "Job":
        """
        Adds a job to the scheduler.

        :param run: function to run
        :param name: Specific job name to add
        :param args: arguments to give to that function.
        :param interval: in seconds, how often should the job be run.
        :param times: limit on number of executions.
        :param run_main: Should this run in the main thread (as registered by kernel.run_later)
        :param conditional: Should execute only if the given additional conditional is true. (checked outside run_main)
        :return: Reference to the job added.
        """
        job = Job(
            job_name=name,
            process=run,
            args=args,
            interval=interval,
            times=times,
            run_main=run_main,
            conditional=conditional,
        )
        return self.schedule(job)

    def remove_job(self, job: "Job") -> "Job":
        return self.unschedule(job)

    def set_timer(
        self,
        command: str,
        name: str = None,
        times: int = 1,
        interval: float = 1.0,
        run_main: bool = False,
    ):
        if name is None or len(name) == 0:
            i = 1
            while "timer%d" % i in self.jobs:
                i += 1
            name = "timer%d" % i
        if not name.startswith("timer"):
            name = "timer" + name
        if times == 0:
            times = None
        self.schedule(
            ConsoleFunction(
                self.root,
                command,
                interval=interval,
                times=times,
                job_name=name,
                run_main=run_main,
            )
        )

    # ==========
    # SIGNAL PROCESSING
    # ==========

    def signal(self, code: str, path: Optional[str], *message) -> None:
        """
        Signals add the latest message to the message queue.

        :param code: Signal code
        :param path: Path of signal
        :param message: Message to send.
        """
        self.queue_lock.acquire(True)
        self.message_queue[code] = path, message
        self.queue_lock.release()

    def process_queue(self, *args) -> None:
        """
        Performed in the run_later thread. Signal groups. Threadsafe.

        Process the signals queued up. Inserting any attaching listeners, removing any removing listeners. And
        providing the newly attached listeners the last message known from that signal.
        :param args: None
        :return:
        """
        if (
            len(self.message_queue) == 0
            and len(self.adding_listeners) == 0
            and len(self.removing_listeners) == 0
        ):
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
        # Process any adding listeners.
        if add is not None:
            for signal, path, funct in add:
                if signal in self.listeners:
                    listeners = self.listeners[signal]
                    listeners.append(funct)
                else:
                    self.listeners[signal] = [funct]
                if path + signal in self.last_message:
                    last_message = self.last_message[path + signal]
                    funct(path, *last_message)
        # Process any removing listeners.
        if remove is not None:
            for signal, path, funct in remove:
                if signal in self.listeners:
                    listeners = self.listeners[signal]
                    try:
                        listeners.remove(funct)
                    except ValueError:
                        print("Value error removing: %s  %s" % (str(listeners), signal))
        # Process signals.
        signal_channel = self.channel("signals")
        for signal, payload in queue.items():
            path, message = payload
            if signal in self.listeners:
                listeners = self.listeners[signal]
                for listener in listeners:
                    listener(path, *message)
                    if signal_channel:
                        signal_channel(
                            "Signal: %s %s: %s:%s%s"
                            % (
                                path,
                                signal,
                                listener.__module__,
                                listener.__name__,
                                str(message),
                            )
                        )
            if path is None:
                self.last_message[signal] = message
            else:
                self.last_message[path + signal] = message
        self._is_queue_processing = False

    def last_signal(self, signal: str, path: str) -> Optional[Tuple]:
        """
        Queries the last signal for a particular code.
        :param signal: signal to query.
        :param path: path for the given signal to query.
        :return: Last signal sent through the kernel for that signal and path
        """
        try:
            return self.last_message[path + signal]
        except KeyError:
            return None

    def listen(self, signal: str, path: str, funct: Callable) -> None:
        self.queue_lock.acquire(True)
        self.adding_listeners.append((signal, path, funct))
        self.queue_lock.release()

    def unlisten(self, signal: str, path: str, funct: Callable) -> None:
        self.queue_lock.acquire(True)
        self.removing_listeners.append((signal, path, funct))
        self.queue_lock.release()

    # ==========
    # CHANNEL PROCESSING
    # ==========

    def channel(self, channel: str, *args, **kwargs) -> "Channel":
        if channel not in self.channels:
            chan = Channel(channel, *args, **kwargs)
            chan._ = self.translation
            self.channels[channel] = chan
        elif "timestamp" in kwargs and isinstance(kwargs["timestamp"], bool):
            self.channels[channel].timestamp = kwargs["timestamp"]

        return self.channels[channel]

    # ==========
    # CONSOLE PROCESSING
    # ==========

    def console(self, data: str) -> None:
        """
        Console accepts console data information. When a '\n' is seen
        it will execute that in the console_parser. This works like a
        terminal, where each letter of data can be sent to the console and
        execution will occur at the carriage return.

        :param data:
        :return:
        """
        if isinstance(data, bytes):
            try:
                data = data.decode()
            except UnicodeDecodeError:
                return
        self._console_buffer += data
        while "\n" in self._console_buffer:
            pos = self._console_buffer.find("\n")
            command = self._console_buffer[0:pos].strip("\r")
            self._console_buffer = self._console_buffer[pos + 1 :]
            self._console_parse(command, channel=self._console_channel)

    def _console_job_tick(self) -> None:
        """
        Processes the console_job ticks. This executes any outstanding queued commands and any looped commands.

        :return:
        """
        for command in self.commands:
            self._console_parse(command, channel=self._console_channel)
        if len(self.queue):
            for command in self.queue:
                self._console_parse(command, channel=self._console_channel)
            self.queue.clear()
        if len(self.commands) == 0 and len(self.queue) == 0:
            self.unschedule(self.console_job)

    def _console_queue(self, command: str) -> None:
        self.queue = [
            c for c in self.queue if c != command
        ]  # Only allow 1 copy of any command.
        self.queue.append(command)
        if self.console_job not in self.jobs:
            self.add_job(self.console_job)

    def _tick_command(self, command: str) -> None:
        self.commands = [
            c for c in self.commands if c != command
        ]  # Only allow 1 copy of any command.
        self.commands.append(command)
        if self.console_job not in self.jobs:
            self.schedule(self.console_job)

    def _untick_command(self, command: str) -> None:
        self.commands = [c for c in self.commands if c != command]
        if len(self.commands) == 0:
            self.unschedule(self.console_job)

    def _console_interface(self, command: str):
        pass

    def _console_parse(self, text: str, channel: "Channel"):
        """
        Console parse takes single line console commands.
        """
        # Silence echo if started with '.'
        if text.startswith("."):
            text = text[1:]
        else:
            channel("[blue][bold][raw]%s[/raw]" % text, indent=False, ansi=True)

        data = None  # Initial data is null
        input_type = None  # Initial type is None

        while len(text) > 0:
            # Divide command from remainder.
            pos = text.find(" ")
            if pos != -1:
                remainder = text[pos + 1 :]
                command = text[0:pos]
            else:
                remainder = ""
                command = text

            _ = self.translation
            command = command.lower()
            command_executed = False
            # Process command matches.
            for command_name in self.match("command/%s/.*" % str(input_type)):
                command_funct = self.registered[command_name]
                cmd_re = command_name.split("/")[-1]

                if command_funct.regex:
                    match = re.compile(cmd_re)
                    if not match.match(command):
                        continue
                else:
                    if cmd_re != command:
                        continue
                try:
                    data, remainder, input_type = command_funct(
                        command,
                        remainder,
                        channel,
                        data=data,
                        data_type=input_type,
                        _=_,
                    )
                    command_executed = True
                    break
                except SyntaxError as e:
                    # If command function raises a syntax error, we abort the rest of the command.

                    # ToDo
                    # Don't use command help, which is or should be descriptive - use command syntax instead
                    # If SyntaxError has a msg then that needs to be provided AS WELL as the syntax.
                    message = command_funct.help
                    if e.msg:
                        message = e.msg
                    channel(
                        "[red][bold]" + _("Syntax Error (%s): %s") % (command, message),
                        ansi=True,
                    )
                    return None
                except CommandMatchRejected:
                    # If the command function raises a CommandMatchRejected more commands should be matched.
                    continue
            if command_executed:
                text = remainder.strip()
            else:
                if input_type is None:
                    ctx_name = "Base"
                else:
                    ctx_name = input_type
                channel(
                    "[red][bold]"
                    + _("%s is not a registered command in this context: %s")
                    % (command, ctx_name),
                    ansi=True,
                )
                return None
        return data

    def register_choices(self, sheet, choices):
        self.register("choices/%s" % sheet, choices)
        for c in choices:
            obj = c["object"]
            if isinstance(obj, Context):
                obj.setting(c["type"], c["attr"], c["default"])

    # ==========
    # KERNEL CONSOLE COMMANDS
    # ==========

    def command_boot(self) -> None:
        _ = self.translation

        @self.console_option("output", "o", help=_("Output type to match"), type=str)
        @self.console_option("input", "i", help=_("Input type to match"), type=str)
        @self.console_argument("extended_help", type=str)
        @self.console_command(("help", "?"), hidden=True, help=_("help <help>"))
        def help_command(channel, _, extended_help, output=None, input=None, **kwargs):
            """
            'help' will display the list of accepted commands. Help <command> will provided extended help for
            that topic. Help can be sub-specified by output or input type.
            """
            if extended_help is not None:
                found = False
                for command_name in self.match("command/.*/%s" % extended_help):
                    func = self.registered[command_name]
                    parts = command_name.split("/")
                    input_type = parts[1]
                    command_item = parts[2]
                    if command_item != extended_help and not func.regex:
                        continue
                    if input is not None and input != input_type:
                        continue
                    func = self.registered[command_name]
                    if output is not None and output != func.output_type:
                        continue
                    help_args = []
                    for a in func.arguments:
                        arg_name = a.get("name", "")
                        arg_type = a.get("type", type(None)).__name__
                        help_args.append("<%s:%s>" % (arg_name, arg_type))
                    if found:
                        channel("\n")
                    if func.long_help is not None:
                        channel(
                            "\t" + inspect.cleandoc(func.long_help).replace("\n", " ")
                        )
                        channel("\n")

                    channel("\t%s %s" % (command_item, " ".join(help_args)))
                    channel(
                        "\t(%s) -> %s -> (%s)"
                        % (input_type, command_item, func.output_type)
                    )
                    for a in func.arguments:
                        arg_name = a.get("name", "")
                        arg_type = a.get("type", type(None)).__name__
                        arg_help = a.get("help")
                        arg_help = (
                            ":\n\t\t%s" % arg_help if arg_help is not None else ""
                        )
                        channel(
                            _("\tArgument: %s '%s'%s") % (arg_type, arg_name, arg_help)
                        )
                    for b in func.options:
                        opt_name = b.get("name", "")
                        opt_short = b.get("short", "")
                        opt_type = b.get("type", type(None)).__name__
                        opt_nargs = int(b.get("nargs", 1))
                        opt_type = ",".join([opt_type] * opt_nargs)
                        opt_help = b.get("help")
                        opt_help = (
                            ":\n\t\t%s" % opt_help if opt_help is not None else ""
                        )
                        channel(
                            _("\tOption: %s ('--%s', '-%s')%s")
                            % (opt_type, opt_name, opt_short, opt_help)
                        )
                    found = True
                if found:
                    return
                channel(_("No extended help for: %s") % extended_help)
                return

            matches = list(self.match("command/.*/.*"))
            matches.sort()
            previous_input_type = None
            for command_name in matches:
                parts = command_name.split("/")
                input_type = parts[1]
                command_item = parts[2]
                if input is not None and input != input_type:
                    continue
                func = self.registered[command_name]
                if output is not None and output != func.output_type:
                    continue
                if previous_input_type != input_type:
                    command_class = input_type if input_type != "None" else _("Base")
                    channel(_("--- %s Commands ---") % command_class)
                    previous_input_type = input_type

                help_attribute = func.help
                if func.hidden:
                    continue
                if help_attribute is not None:
                    channel("%s %s" % (command_item.ljust(15), help_attribute))
                else:
                    channel(command_name.split("/")[-1])

        @self.console_command(
            "echo",
            help=_("Echo text to console"),
        )
        def echo_to_console(channel, remainder=None, **kwargs):
            if remainder:
                channel(remainder)

        @self.console_command("loop", help=_("loop <command>"))
        def loop(remainder=None, **kwargs):
            if remainder:
                self._tick_command(remainder)

        @self.console_command("end", help=_("end <commmand>"))
        def end(remainder=None, **kwargs):
            if remainder:
                self._untick_command(remainder)
            else:
                self.commands.clear()
                self.schedule(self.console_job)

        @self.console_option(
            "off", "o", action="store_true", help=_("Turn this timer off")
        )
        @self.console_option(
            "gui", "g", action="store_true", help=_("Run this timer in the gui-thread")
        )
        @self.console_argument(
            "times", help=_("Number of times this timer should execute.")
        )
        @self.console_argument(
            "duration",
            type=float,
            help=_("How long in seconds between/before should this be run."),
        )
        @self.console_command(
            "timer.*",
            regex=True,
            help=_(
                "run the command a given number of times with a given duration between."
            ),
        )
        def timer(
            command,
            channel,
            _,
            times=None,
            duration=None,
            off=False,
            gui=False,
            remainder=None,
            **kwargs,
        ):
            if times == "off":
                off = True
                times = None
            name = command[5:]
            if times is None and not off:
                channel(_("----------"))
                channel(_("Timers:"))
                i = 0
                for job_name in self.jobs:
                    if not job_name.startswith("timer"):
                        continue
                    i += 1
                    job = self.jobs[job_name]
                    parts = list()
                    parts.append("%d:" % i)
                    parts.append(job_name)
                    parts.append('"%s"' % str(job))
                    if job.times is None:
                        parts.append(_("forever,"))
                    else:
                        parts.append(_("%d times,") % job.times)
                    if job.interval is None:
                        parts.append(_("never"))
                    else:
                        parts.append(_("each %f seconds") % job.interval)
                    if job.run_main:
                        parts.append(_("- gui"))
                    channel(" ".join(parts))
                channel(_("----------"))
                return
            if off:
                if name == "*":
                    for job_name in [j for j in self.jobs if j.startswith("timer")]:
                        # removing jobs, must create current list
                        job = self.jobs[job_name]
                        job.cancel()
                        self.unschedule(job)
                    channel(_("All timers canceled."))
                    return
                try:
                    obj = self.jobs[command]
                    obj.cancel()
                    self.unschedule(obj)
                    channel(_("Timer '%s' canceled." % name))
                except KeyError:
                    channel(_("Timer '%s' does not exist." % name))
                return
            try:
                times = int(times)
            except (TypeError, ValueError):
                raise SyntaxError
            if duration is None:
                raise SyntaxError
            try:
                timer_command = remainder
                self.set_timer(
                    timer_command + "\n",
                    name=name,
                    times=times,
                    interval=duration,
                    run_main=gui,
                )
            except ValueError:
                channel(_("Syntax Error: timer<name> <times> <interval> <command>"))
            return

        @self.console_command("register", _("register"))
        def register(channel, _, args=tuple(), **kwargs):
            if len(args) == 0:
                channel(_("----------"))
                channel(_("Objects Registered:"))
                for i, name in enumerate(self.match(".*")):
                    obj = self.registered[name]
                    channel(_("%d: %s type of %s") % (i + 1, name, str(obj)))
                channel(_("----------"))
            if len(args) == 1:
                channel(_("----------"))
                channel("Objects Registered:")
                for i, name in enumerate(self.match("%s.*" % args[0])):
                    obj = self.registered[name]
                    channel("%d: %s type of %s" % (i + 1, name, str(obj)))
                channel(_("----------"))

        @self.console_command("context", _("context"))
        def context(channel, _, args=tuple(), **kwargs):
            if len(args) == 0:
                for context_name in self.contexts:
                    channel(context_name)
            return

        @self.console_command("plugin", _("list loaded plugins in kernel"))
        def plugin(channel, _, args=tuple(), **kwargs):
            if len(args) == 0:
                for name in self._plugins:
                    channel(name.__module__)
            return

        @self.console_option(
            "path", "p", type=str, default="/", help=_("Path of variables to set.")
        )
        @self.console_command("set", help=_("set [<key> <value>]"))
        def set_command(channel, _, path=None, args=tuple(), **kwargs):
            relevant_context = self.get_context(path) if path is not None else self.root
            if len(args) == 0:
                for attr in dir(relevant_context):
                    v = getattr(relevant_context, attr)
                    if attr.startswith("_") or not isinstance(
                        v, (int, float, str, bool)
                    ):
                        continue
                    channel('"%s" := %s' % (attr, str(v)))
                return
            if len(args) >= 2:
                attr = args[0]
                value = args[1]
                try:
                    if hasattr(relevant_context, attr):
                        v = getattr(relevant_context, attr)
                        if isinstance(v, bool):
                            if value == "False" or value == "false" or value == 0:
                                setattr(relevant_context, attr, False)
                            else:
                                setattr(relevant_context, attr, True)
                        elif isinstance(v, int):
                            setattr(relevant_context, attr, int(value))
                        elif isinstance(v, float):
                            setattr(relevant_context, attr, float(value))
                        elif isinstance(v, str):
                            setattr(relevant_context, attr, str(value))
                except RuntimeError:
                    channel(_("Attempt failed. Produced a runtime error."))
                except ValueError:
                    channel(_("Attempt failed. Produced a value error."))
                except AttributeError:
                    channel(_("Attempt failed. Produced an attribute error."))
            return

        @self.console_command("control", help=_("control [<executive>]"))
        def control(channel, _, remainder=None, **kwargs):
            if remainder is None:
                for control_name in self.root.match("[0-9]+/control", suffix=True):
                    channel(control_name)
                return

            control_name = remainder
            controls = list(self.match("control/.*", suffix=True))
            if control_name in controls:
                self.root.execute(control_name)
                channel(_("Executed '%s'") % control_name)
            else:
                channel(_("Control '%s' not found.") % control_name)

        @self.console_option(
            "path", "p", type=str, default="/", help=_("Path of variables to set.")
        )
        @self.console_command("module", help=_("module [(open|close) <module_name>]"))
        def module(channel, _, path=None, args=tuple(), **kwargs):
            if len(args) == 0:
                channel(_("----------"))
                channel(_("Modules Registered:"))
                for i, name in enumerate(self.match("module")):
                    channel("%d: %s" % (i + 1, name))
                channel(_("----------"))
                for i, name in enumerate(self.contexts):
                    context = self.contexts[name]
                    if len(context.opened) == 0:
                        continue
                    channel(_("Loaded Modules in Context %s:") % str(context.path))
                    for j, jname in enumerate(context.opened):
                        module = context.opened[jname]
                        channel(
                            _("%d: %s as type of %s") % (j + 1, jname, type(module))
                        )
                    channel(_("----------"))
                    return
            if path is None:
                path = "/"
            path_context = self.get_context(path)
            value = args[0]
            if value == "open":
                index = args[1]
                name = None
                if len(args) >= 3:
                    name = args[2]
                if index in self.registered:
                    if name is not None:
                        path_context.open_as(index, name)
                    else:
                        path_context.open(index)
                else:
                    channel(_("Module '%s' not found.") % index)
            elif value == "close":
                index = args[1]
                if index in path_context.opened:
                    path_context.close(index)
                else:
                    channel(_("Module '%s' not found.") % index)
            return

        @self.console_option(
            "path", "p", type=str, default="/", help=_("Path of variables to set.")
        )
        @self.console_command(
            "modifier", help=_("modifier [(open|close) <module_name>]")
        )
        def modifier(channel, _, path=None, args=tuple(), **kwargs):
            if path is None:
                path = "/"
            path_context = self.get_context(path)

            if len(args) == 0:
                channel(_("----------"))
                channel(_("Modifiers Registered:"))
                for i, name in enumerate(self.match("modifier")):
                    channel("%d: %s" % (i + 1, name))
                channel(_("----------"))

                channel(_("Loaded Modifiers in Context %s:") % str(path_context.path))
                for i, name in enumerate(path_context.attached):
                    modifier = path_context.attached[name]
                    channel(_("%d: %s as type of %s") % (i + 1, name, type(modifier)))
                channel(_("----------"))
                channel(_("Loaded Modifiers in Device %s:") % str(path_context.path))
                for i, name in enumerate(path_context.attached):
                    modifier = path_context.attached[name]
                    channel(_("%d: %s as type of %s") % (i + 1, name, type(modifier)))
                channel(_("----------"))
            else:
                value = args[0]
                if value == "open":
                    index = args[1]
                    if index in self.registered:
                        path_context.activate(index)
                    else:
                        channel(_("Modifier '%s' not found.") % index)
                elif value == "close":
                    index = args[1]
                    if index in path_context.attached:
                        path_context.deactivate(index)
                    else:
                        channel(_("Modifier '%s' not found.") % index)

        @self.console_command("schedule", help=_("show scheduled events"))
        def schedule(channel, _, **kwargs):
            channel(_("----------"))
            channel(_("Scheduled Processes:"))
            for i, job_name in enumerate(self.jobs):
                job = self.jobs[job_name]
                parts = list()
                parts.append("%d:" % (i + 1))
                parts.append(str(job))
                if job.times is None:
                    parts.append(_("forever,"))
                else:
                    parts.append(_("%d times,") % job.times)
                if job.interval is None:
                    parts.append(_("never"))
                else:
                    parts.append(_("each %f seconds") % job.interval)
                channel(" ".join(parts))
            channel(_("----------"))

        @self.console_command("thread", help=_("show threads"))
        def thread(channel, _, **kwargs):
            """
            Display the currently registered threads within the Kernel.
            """
            channel(_("----------"))
            channel(_("Registered Threads:"))
            for i, thread_name in enumerate(list(self.threads)):
                thread = self.threads[thread_name]
                parts = list()
                parts.append("%d:" % (i + 1))
                parts.append(str(thread))
                if thread.is_alive:
                    parts.append(_("is alive."))
                channel(" ".join(parts))
            channel(_("----------"))

        @self.console_command(
            "channel",
            help=_("channel (open|close|save|list|print) <channel_name>"),
            output_type="channel",
        )
        def channel(channel, _, remainder=None, **kwargs):
            if remainder is None:
                channel(_("----------"))
                channel(_("Channels Active:"))
                for i, name in enumerate(self.channels):
                    channel_name = self.channels[name]
                    if self._console_channel in channel_name.watchers:
                        is_watched = "* "
                    else:
                        is_watched = "  "
                    channel("%s%d: %s" % (is_watched, i + 1, name))
            return "channel", 0

        @self.console_command(
            "list",
            help=_("list the channels open in the kernel"),
            input_type="channel",
            output_type="channel",
        )
        def channel_list(channel, _, **kwargs):
            channel(_("----------"))
            channel(_("Channels Active:"))
            for i, name in enumerate(self.channels):
                channel_name = self.channels[name]
                if self._console_channel in channel_name.watchers:
                    is_watched = "* "
                else:
                    is_watched = "  "
                channel("%s%d: %s" % (is_watched, i + 1, name))
            return "channel", 0

        @self.console_argument("channel_name", help=_("name of the channel"))
        @self.console_command(
            "open",
            help=_("watch this channel in the console"),
            input_type="channel",
            output_type="channel",
        )
        def channel_open(channel, _, channel_name, **kwargs):
            if channel_name is None:
                raise SyntaxError(_("channel_name is not specified."))

            if channel_name == "console":
                channel(_("Infinite Loop Error."))
            else:
                self.channel(channel_name).watch(self._console_channel)
                channel(_("Watching Channel: %s") % channel_name)
            return "channel", channel_name

        @self.console_argument("channel_name", help=_("channel name"))
        @self.console_command(
            "close",
            help=_("stop watching this channel in the console"),
            input_type="channel",
            output_type="channel",
        )
        def channel_close(channel, _, channel_name, **kwargs):
            if channel_name is None:
                raise SyntaxError(_("channel_name is not specified."))

            try:
                self.channel(channel_name).unwatch(self._console_channel)
                channel(_("No Longer Watching Channel: %s") % channel_name)
            except (KeyError, ValueError):
                channel(_("Channel %s is not opened.") % channel_name)
            return "channel", channel_name

        @self.console_argument("channel_name", help=_("channel name"))
        @self.console_command(
            "print",
            help=_("print this channel to the standard out"),
            input_type="channel",
            output_type="channel",
        )
        def channel_print(channel, _, channel_name, **kwargs):
            if channel_name is None:
                raise SyntaxError(_("channel_name is not specified."))

            channel(_("Printing Channel: %s") % channel_name)
            self.channel(channel_name).watch(print)
            return "channel", channel_name

        @self.console_option(
            "filename", "f", help=_("Use this filename rather than default")
        )
        @self.console_argument(
            "channel_name", help=_("channel name (you may comma delimit)")
        )
        @self.console_command(
            "save",
            help=_("save this channel to disk"),
            input_type="channel",
            output_type="channel",
        )
        def channel_save(channel, _, channel_name, filename=None, **kwargs):
            """
            Save a particular channel to disk. Any data sent to that channel within Meerk40t will write out a log.
            """
            if channel_name is None:
                raise SyntaxError(_("channel_name is not specified."))

            from datetime import datetime

            if filename is None:
                filename = "MeerK40t-channel-{date:%Y-%m-%d_%H_%M_%S}.txt".format(
                    date=datetime.now()
                )
            channel(_("Opening file: %s") % filename)
            console_channel_file = self.open_safe(filename, "a")
            for cn in channel_name.split(","):
                channel(
                    _("Recording Channel: %s to file %s") % (channel_name, filename)
                )

                def _console_file_write(v):
                    console_channel_file.write("%s\r\n" % v)
                    console_channel_file.flush()

                self.channel(cn).watch(_console_file_write)
            return "channel", channel_name

        @self.console_option(
            "path",
            "p",
            type=str,
            default="/",
            help=_("Path that should be flushed to disk."),
        )
        @self.console_command("flush", help=_("flush current settings to disk"))
        def flush(channel, _, path=None, **kwargs):
            if path is not None:
                path_context = self.get_context(path)
            else:
                path_context = self.root

            if path_context is not None:
                path_context.flush()
                try:
                    self._config.Flush()
                except AttributeError:
                    pass
                channel(_("Persistent settings force saved."))
            else:
                channel(_("No relevant context found."))

        @self.console_command(
            ("quit", "shutdown"), help=_("shuts down all processes and exits")
        )
        def shutdown(**kwargs):
            if self.state not in (STATE_END, STATE_TERMINATE):
                self.shutdown()

        @self.console_command(("ls", "dir"), help=_("list directory"))
        def ls(channel, **kwargs):
            for f in os.listdir(self._current_directory):
                channel(str(f))

        @self.console_argument("directory")
        @self.console_command("cd", help=_("change directory"))
        def cd(channel, _, directory=None, **kwargs):
            import os

            if directory == "~":
                self._current_directory = "."
                channel(_("Working directory"))
                return
            if directory == "@":
                import sys

                if hasattr(sys, "_MEIPASS"):
                    # pylint: disable=no-member
                    self._current_directory = sys._MEIPASS
                    channel(_("Internal Directory"))
                    return
                else:
                    channel(_("No internal directory."))
                    return
            if directory is None:
                channel(os.path.abspath(self._current_directory))
                return
            new_dir = os.path.join(self._current_directory, directory)
            if not os.path.exists(new_dir):
                channel(_("No such directory."))
                return
            self._current_directory = new_dir
            channel(os.path.abspath(new_dir))

        @self.console_argument("filename")
        @self.console_command(
            "load",
            help=_("loads file from working directory"),
            input_type=None,
            output_type="file",
        )
        def load(channel, _, filename=None, **kwargs):
            import os

            if filename is None:
                channel(_("No file specified."))
                return
            new_file = os.path.join(self._current_directory, filename)
            if not os.path.exists(new_file):
                channel(_("No such file."))
                return
            root_context = self.root
            try:
                root_context.load(new_file)
            except AttributeError:
                raise SyntaxError(_("Loading files was not defined"))
            channel(_("loading..."))
            return "file", new_file


# ==========
# END KERNEL
# ==========


class CommandMatchRejected(BaseException):
    def __init__(self, *args):
        super().__init__(*args)


class MalformedCommandRegistration(BaseException):
    def __init__(self, *args):
        super().__init__(*args)


class Channel:
    def __init__(
        self,
        name: str,
        buffer_size: int = 0,
        line_end: Optional[str] = None,
        timestamp: bool = False,
        ansi: bool = False,
    ):
        self.watchers = []
        self.greet = None
        self.name = name
        self.buffer_size = buffer_size
        self.line_end = line_end
        self._ = lambda e: e
        self.timestamp = timestamp
        if buffer_size == 0:
            self.buffer = None
        else:
            self.buffer = deque()
        self.ansi = ansi

    def __repr__(self):
        return "Channel(%s, buffer_size=%s, line_end=%s)" % (
            repr(self.name),
            str(self.buffer_size),
            repr(self.line_end),
        )

    def _call_raw(
        self,
        message: Union[str, bytes, bytearray],
    ):
        for w in self.watchers:
            w(message)
        if self.buffer is not None:
            self.buffer.append(message)
            while len(self.buffer) > self.buffer_size:
                self.buffer.popleft()

    def __call__(
        self,
        message: Union[str, bytes, bytearray],
        *args,
        indent: Optional[bool] = True,
        ansi: Optional[bool] = False,
        **kwargs,
    ):
        if isinstance(message, (bytes, bytearray)):
            self._call_raw(message)
            return

        original_msg = message
        if self.line_end is not None:
            message = message + self.line_end
        if indent:
            message = "    " + message.replace("\n", "\n    ")
        if self.timestamp:
            ts = datetime.datetime.now().strftime("[%H:%M:%S] ")
            message = ts + message.replace("\n", "\n%s" % ts)
        if ansi:
            if self.ansi:
                # Convert bbcode to ansi
                message = self.bbcode_to_ansi(message)
            else:
                # Convert bbcode to stripped
                message = self.bbcode_to_plain(message)

        console_open_print = False
        # Check if this channel is "open" i.e. being sent to console
        # and if so whether the console is being sent to print
        # because if so then we don't want to print ourselves
        for w in self.watchers:
            if isinstance(w, Channel) and w.name == "console" and print in w.watchers:
                console_open_print = True
                break
        for w in self.watchers:
            # Avoid double printing if this channel is "open" and printed
            # and console is also printed
            if w is print and console_open_print:
                continue
            # Avoid double timestamp and indent
            if isinstance(w, Channel):
                w(original_msg, indent=indent)
            else:
                w(message)
        if self.buffer is not None:
            self.buffer.append(message)
            while len(self.buffer) > self.buffer_size:
                self.buffer.popleft()

    def __len__(self):
        return self.buffer_size

    def __iadd__(self, other):
        self.watch(monitor_function=other)

    def __isub__(self, other):
        self.unwatch(monitor_function=other)

    def __bool__(self):
        """
        In the case that a channel requires preprocessing or object creation, the truthy value
        of the channel reflects whether that data will be actually sent anywhere before trying to
        send the data. With this you can have channels that do no work unless something in the kernel
        is listening for that data, or the data is being buffered.
        """
        return bool(self.watchers) or self.buffer_size != 0

    def watch(self, monitor_function: Callable):
        for q in self.watchers:
            if q is monitor_function:
                return  # This is already being watched by that.
        self.watchers.append(monitor_function)
        if self.greet is not None:
            monitor_function(self.greet)
        if self.buffer is not None:
            for line in list(self.buffer):
                monitor_function(line)

    def unwatch(self, monitor_function: Callable):
        self.watchers.remove(monitor_function)

    def bbcode_to_ansi(self, text):
        return "".join(
            [
                BBCODE_LIST["normal"],
                RE_ANSI.sub(self.bbcode_to_ansi_match, text),
                BBCODE_LIST["normal"],
            ]
        )

    def bbcode_to_ansi_match(self, m):
        tag = re.sub(r"\].*", "", m[0])[1:].lower()
        return BBCODE_LIST[tag] if tag != "raw" else m[2]

    def bbcode_to_plain(self, text):
        strip = lambda m: m[2]
        return RE_ANSI.sub(strip, text)


class Job:
    """
    Generic job for the scheduler.

    Jobs that can be scheduled in the scheduler-kernel to run at a particular time and a given number of times.
    This is done calling schedule() and unschedule() and setting the parameters for process, args, interval,
    and times. This is usually extended directly by a module requiring that functionality.
    """

    def __init__(
        self,
        process: Optional[Callable] = None,
        args: Optional[Tuple] = (),
        interval: float = 1.0,
        times: Optional[int] = None,
        job_name: Optional[str] = None,
        run_main: bool = False,
        conditional: Callable = None,
    ):
        self.job_name = job_name
        self.state = STATE_INITIALIZE
        self.run_main = run_main
        self.conditional = conditional

        self.process = process
        self.args = args
        self.interval = interval
        self.times = times
        self._last_run = None
        self._next_run = time.time() + self.interval

    def __call__(self, *args, **kwargs):
        self.process(*args, **kwargs)

    def __str__(self):
        if self.job_name is not None:
            return self.job_name
        else:
            try:
                return self.process.__name__
            except AttributeError:
                return object.__str__(self)

    @property
    def scheduled(self) -> bool:
        return (
            self._next_run is not None
            and time.time() >= self._next_run
            and (self.conditional is None or self.conditional())
        )

    def cancel(self) -> None:
        self.times = -1


class ConsoleFunction(Job):
    def __init__(
        self,
        context: Context,
        data: str,
        interval: float = 1.0,
        times: Optional[int] = None,
        job_name: Optional[str] = None,
        run_main: bool = False,
        conditional: Callable = None,
    ):
        Job.__init__(
            self, self.__call__, None, interval, times, job_name, run_main, conditional
        )
        self.context = context
        self.data = data

    def __call__(self, *args, **kwargs):
        self.context.console(self.data)

    def __str__(self):
        return self.data.replace("\n", "")


def get_safe_path(
    name: str, create: Optional[bool] = False, system: Optional[str] = None
) -> str:
    if not system:
        system = platform.system()

    if system == "Darwin":
        directory = os.path.join(
            os.path.expanduser("~"),
            "Library",
            "Application Support",
            name,
        )
    elif system == "Windows":
        directory = os.path.join(os.path.expandvars("%LOCALAPPDATA%"), name)
    else:
        directory = os.path.join(os.path.expanduser("~"), ".config", name)
    if directory is not None and create:
        os.makedirs(directory, exist_ok=True)
    return directory
