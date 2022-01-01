import datetime
import functools
import inspect
import os
import re
import threading
import time
from collections import deque
from threading import Lock, Thread
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

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

LIFECYCLE_SHUTDOWN = 1000
LIFECYCLE_INIT = 0
LIFECYCLE_KERNEL_PREREGISTER = 100
LIFECYCLE_KERNEL_REGISTER = 101
LIFECYCLE_KERNEL_CONFIGURE = 102
LIFECYCLE_KERNEL_PREBOOT = 200
LIFECYCLE_KERNEL_BOOT = 201
LIFECYCLE_KERNEL_POSTBOOT = 202
LIFECYCLE_KERNEL_PRESTART = 300
LIFECYCLE_KERNEL_START = 301
LIFECYCLE_KERNEL_POSTSTART = 302
LIFECYCLE_KERNEL_READY = 303
LIFECYCLE_KERNEL_FINISHED = 304
LIFECYCLE_KERNEL_PREMAIN = 400
LIFECYCLE_KERNEL_MAINLOOP = 401
LIFECYCLE_KERNEL_PRESHUTDOWN = 900

LIFECYCLE_SERVICE_ADDED = 50
LIFECYCLE_SERVICE_ATTACHED = 100
LIFECYCLE_SERVICE_ASSIGNED = 101
LIFECYCLE_SERVICE_DETACHED = 200

LIFECYCLE_MODULE_OPENED = 100
LIFECYCLE_MODULE_CLOSED = 200


def kernel_lifecycle_name(lifecycle):
    if lifecycle == LIFECYCLE_INIT:
        return "init"
    if lifecycle == LIFECYCLE_KERNEL_PREREGISTER:
        return "preregister"
    if lifecycle == LIFECYCLE_KERNEL_REGISTER:
        return "register"
    if lifecycle == LIFECYCLE_KERNEL_CONFIGURE:
        return "configure"
    if lifecycle == LIFECYCLE_KERNEL_PREBOOT:
        return "preboot"
    if lifecycle == LIFECYCLE_KERNEL_BOOT:
        return "boot"
    if lifecycle == LIFECYCLE_KERNEL_POSTBOOT:
        return "postboot"
    if lifecycle == LIFECYCLE_KERNEL_PRESTART:
        return "prestart"
    if lifecycle == LIFECYCLE_KERNEL_START:
        return "start"
    if lifecycle == LIFECYCLE_KERNEL_POSTSTART:
        return "poststart"
    if lifecycle == LIFECYCLE_KERNEL_READY:
        return "ready"
    if lifecycle == LIFECYCLE_KERNEL_FINISHED:
        return "finished"
    if lifecycle == LIFECYCLE_KERNEL_PREMAIN:
        return "premain"
    if lifecycle == LIFECYCLE_KERNEL_MAINLOOP:
        return "mainloop"
    if lifecycle == LIFECYCLE_KERNEL_PRESHUTDOWN:
        return "preshutdown"
    if lifecycle == LIFECYCLE_SHUTDOWN:
        return "shutdown"


def service_lifecycle_name(lifecycle):
    if lifecycle >= LIFECYCLE_SHUTDOWN:
        return "shutdown"
    if lifecycle >= LIFECYCLE_SERVICE_DETACHED:
        return "detached"
    if lifecycle >= LIFECYCLE_SERVICE_ASSIGNED:
        return "assigned"
    if lifecycle >= LIFECYCLE_SERVICE_ATTACHED:
        return "attached"
    if lifecycle >= LIFECYCLE_SERVICE_ADDED:
        return "added"
    if lifecycle >= LIFECYCLE_INIT:
        return "init"


_cmd_parse = [
    ("OPT", r"-([a-zA-Z]+)"),
    ("LONG", r"--([^ ,\t\n\x09\x0A\x0C\x0D]+)"),
    ("QPARAM", r"\"(.*?)\""),
    ("PARAM", r"([^ ,\t\n\x09\x0A\x0C\x0D]+)"),
    ("SKIP", r"[ ,\t\n\x09\x0A\x0C\x0D]+"),
]
_CMD_RE = re.compile("|".join("(?P<%s>%s)" % pair for pair in _cmd_parse))


class Module:
    """
    Modules are a generic lifecycle object. These are registered in the kernel as modules and when open() is called for
    a context. When close() is called on the context, it will close and delete references to the opened module and call
    module_close().

    If an opened module is tries to open() a second time in a context with the same name, and it was never closed.
    The device restore() function is called for the device, with the same args and kwargs that would have been called
    on __init__().

    Multiple instances of a module can be opened but this requires a different initialization name. Modules are not
    expected to modify their contexts.
    """

    def __init__(
        self,
        context: "Context",
        name: str = None,
        registered_path: str = None,
        *args,
        **kwargs,
    ):
        self.context = context
        self.name = name
        self.registered_path = registered_path
        self.state = STATE_INITIALIZE

    def __repr__(self):
        return '{class_name}({context}, name="{name}")'.format(
            class_name=self.__class__.__name__,
            context=repr(self.context),
            name=self.name,
        )

    def restore(self, *args, **kwargs):
        """Called with the same values of __init()__ on an attempted reopen of a module with the same name at the
        same context."""
        pass

    def module_open(self, *args, **kwargs):
        """Initialize() is called after open() to setup the module and allow it to register various hooks into the
        kernelspace."""
        pass

    def module_close(self, *args, **kwargs):
        """Finalize is called after close() to unhook various kernelspace hooks. This will happen if kernel is being
        shutdown or if this individual module is being closed on its own."""
        pass

    def add_module_delegate(self, delegate):
        self.context.kernel.add_delegate(delegate, self)


class Context:
    """
    Contexts serve as path-relevant snapshots of the kernel. These are are the primary interaction between the modules
    and the kernel. They permit getting other contexts of the kernel as well. This should serve as the primary interface
    code between the kernel and the modules.

    Contexts store the persistent settings and settings from at their path locations.

    Contexts have attribute settings located at .<setting> and so long as this setting does not begin with _ or
    'implicit' it will be reloaded when .setting() is called for the given attribute. This should be called by any
    module that intends access to an attribute even if it was already called.
    """

    def __init__(self, kernel: "Kernel", path: str):
        self._kernel = kernel
        self._path = path
        self._state = STATE_UNKNOWN
        self.opened = {}

        self.console_argument = console_argument
        self.console_option = console_option

    def __repr__(self):
        return "Context('%s')" % self._path

    def __call__(self, data: str, **kwargs):
        return self._kernel.console(data)

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
        Find all subpaths of the current context and delete them.

        This is not a maintenance operation. It's needed for rare instances during shutdown. All contexts will be
        shutdown, this prevents normal shutdown procedure.
        """
        for e in list(self._kernel.contexts):
            if e.startswith(self._path):
                del self._kernel.contexts[e]

    def destroy(self):
        self.clear_persistent()
        self.close_subpaths()

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
            load_value = self._kernel.read_persistent(
                type(obj_value), self.abs_path(attr)
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
            funct = self._kernel.lookup(self.abs_path("control/%s" % control))
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

    def unregister(self, path: str) -> None:
        """
        Delegate to Kernel
        """
        self._kernel.unregister(path)

    def console_command(self, *args, **kwargs) -> Callable:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_command being registered.
        """
        return console_command(self._kernel, *args, **kwargs)

    def console_command_remove(self, *args, **kwargs) -> Callable:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_command being removed.
        """
        return console_command_remove(self._kernel, *args, **kwargs)

    @property
    def contexts(self) -> Dict[str, "Context"]:
        return self._kernel.contexts

    def has_feature(self, feature: str) -> bool:
        """
        Return whether or not this is a registered feature within the kernel.

        :param feature: feature to check if exists in kernel.
        :return:
        """
        return self.lookup(feature) is not None

    def find(self, *args):
        """
        Delegate of Kernel match.

        :param matchtext:  regex matchtext to locate.
        :param suffix: provide the suffix of the match only.
        :yield: matched entries.
        """
        yield from self._kernel.find(*args)

    def match(self, matchtext: str, suffix: bool = False) -> Generator[str, None, None]:
        """
        Delegate of Kernel match.

        :param matchtext:  regex matchtext to locate.
        :param suffix: provide the suffix of the match only.
        :yield: matched entries.
        """
        yield from self._kernel.match(matchtext, suffix)

    def lookup(self, *args) -> Any:
        """
        Lookup a value in the kernel or services.

        @param args: arguments
        @return:
        """
        return self._kernel.lookup(*args)

    def lookup_all(self, *args) -> Any:
        """
        Lookup all matching values in the kernel or services.

        @param args: arguments
        @return:
        """
        yield from self._kernel.lookup_all(*args)

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

    def get_open(self, path: str) -> Union["Module", None]:
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
        :param instance_path: instance_path of object.
        :param args: Args to pass to newly opened module.
        :param kwargs: Kwargs to pass to newly opened module.
        :return: Opened module.
        """
        try:
            find = self.opened[instance_path]
            try:
                # Module found, attempt restore call.
                find.restore(*args, **kwargs)
            except AttributeError:
                pass
            return find
        except KeyError:
            # Module not found.
            pass

        open_object = self._kernel.lookup(registered_path)
        if open_object is None:
            raise ValueError

        instance = open_object(self, instance_path, *args, **kwargs)
        instance.registered_path = registered_path

        # Call module_open lifecycle event.
        self.kernel.set_module_lifecycle(instance, LIFECYCLE_MODULE_OPENED)

        return instance

    def close(self, instance_path: str, *args, **kwargs) -> None:
        """
        Closes an opened module instance. Located at the instance_path location.

        This calls the close() function on the object (which may not exist). Then calls module_close() on the module,
        which should exist.

        :param instance_path: Instance path to close.
        :return:
        """
        try:
            instance = self.opened[instance_path]
        except KeyError:
            return  # Nothing to close.
        # Call module_close lifecycle event.
        self.kernel.set_module_lifecycle(instance, LIFECYCLE_MODULE_CLOSED)

    # ==========
    # SIGNALS DELEGATES
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

    def listen(
        self,
        signal: str,
        process: Callable,
        lifecycle_object: Union["Service", Module, None] = None,
    ) -> None:
        """
        Listen at a particular signal with a given process.

        :param signal: Signal code to listen for
        :param process: listener to be attached
        :return:
        """
        self._kernel.listen(signal, self._path, process, lifecycle_object)

    def unlisten(self, signal: str, process: Callable):
        """
        Unlisten to a particular signal with a given process.

        This should be called on the ending of the lifecycle of whatever process listened to the given signal.

        :param signal: Signal to unlisten for.
        :param process: listener that is to be detached.
        :return:
        """
        self._kernel.unlisten(signal, self._path, process)

    # ==========
    # CHANNEL DELEGATES
    # ==========

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


class Service(Context):
    """
    A service is a context that with additional capabilities. These get registered by a domain in the kernel as a
    particular aspect. For example, .device or .gui could be a service and this service would be found at that attribute
    at for any context. A service does not exist pathwise at a particular domain. The path is the saving/loading
    location for persistent settings. This also allows several services to be registered for the same domain. These are
    swapped with the activate_service commands in the kernel.

    Each service has its own registered lookup of data. This extends the lookup of the kernel but only for those
    services which are currently active. This extends to various types of things that are registered in the kernel such
    as choices and console commands. The currently active service can modify these simply by being activated.

    Unlike contexts which can be derived or gotten at a particular path. Services can be directly instanced.
    """

    def __init__(self, kernel: "Kernel", path: str, registered_path: str = None):
        super().__init__(kernel, path)
        kernel.register_as_context(self)
        self.registered_path = registered_path
        self._registered = {}

    def __str__(self):
        if hasattr(self, "label"):
            return self.label
        return "Service('{path}', {rpath})".format(
            path=self._path, rpath=self.registered_path
        )

    def service_attach(self, *args, **kwargs):
        pass

    def service_detach(self, *args, **kwargs):
        pass

    def shutdown(self, *args, **kwargs):
        """
        Called by kernel during shutdown process for all services.
        @param args:
        @param kwargs:
        @return:
        """
        pass

    def register(self, path: str, obj: Any) -> None:
        """
        Registers an element within this service.

        :param path:
        :param obj:
        :return:
        """
        self._registered[path] = obj
        try:
            obj.sub_register(self)
        except AttributeError:
            pass
        self._kernel.lookup_change(path)

    def unregister(self, path: str) -> None:
        """
        Unregister an element within this service.

        @param path: Path to unregister
        @return:
        """
        del self._registered[path]
        self._kernel.lookup_change(path)

    def console_command(self, *args, **kwargs) -> Callable:
        """
        Service console command registration.

        Uses the current registration to register the given command.
        """
        return console_command(self, *args, **kwargs)

    def console_command_remove(self, *args, **kwargs) -> Callable:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_command being removed.
        """
        return console_command_remove(self, *args, **kwargs)

    def destroy(self):
        self.kernel.set_service_lifecycle(self, LIFECYCLE_SHUTDOWN)
        self.clear_persistent()
        self.close_subpaths()

    def register_choices(self, sheet, choices):
        """
        Service register choices command registration.

        Uses the current registration to register the choices.
        @param sheet: Name of choices being registered
        @param choices: list of choices
        @return:
        """
        Kernel.register_choices(self, sheet, choices)

    def add_service_delegate(self, delegate):
        self.kernel.add_delegate(delegate, self)


class Kernel:
    """
    The Kernel serves as the central hub of communication between different objects within the system, stores the
    main lookup of registered objects, as well as providing a scheduler, signals, channels, and a command console to be
    used within the system.

    The Kernel stores a persistence object, thread interactions, contexts, a translation routine, a run_later operation,
    jobs for the scheduler, listeners for signals, channel information, a list of devices, registered commands.
    """

    def __init__(
        self, name: str, version: str, profile: str, path: str = "/", config=None
    ):
        """
        Initialize the Kernel. This sets core attributes of the ecosystem that are accessible to all modules.

        Name: The application name.
        Version: The version number of the application.
        Profile: The name to save our data under (this is often the same as app name).
        Path: The path prefix to silently add to all data. This allows the same profile to be used without the same data
        Config: This is the persistence object used to save. While official agnostic, it's actually strikingly identical
                    to a wx.Config object.
        """
        self.name = name
        self.profile = profile
        self.version = version
        self._path = path

        # Boot State
        self._booted = False
        self._shutdown = False

        # Store the plugins for the kernel. During lifecycle events all plugins will be called with the new lifecycle
        self._kernel_plugins = []
        self._service_plugins = {}
        self._module_plugins = {}

        # All established contexts.
        self.contexts = {}

        # All registered threads.
        self.threads = {}
        self.thread_lock = Lock()

        # All established delegates
        self.delegates = []

        # All registered lookups within the kernel.
        self._clean_lookup = Job(
            process=self._registered_data_changed,
            job_name="kernel.lookup.clean",
            interval=0.3,
            times=1,
            run_main=True,
        )
        self._registered = {}
        self.lookups = {}
        self.lookup_previous = {}
        self._dirty_paths = []
        self._lookup_lock = Lock()

        # The translation object to be overridden by any valid translation functions
        self.translation = lambda e: e

        # The function used to process the signals. This is useful if signals should be kept to a single thread.
        self.run_later = lambda execute, op: execute(op)
        self.state = STATE_INITIALIZE

        # Scheduler
        self.jobs = {}
        self.scheduler_thread = None

        # Signal Listener
        self.signal_job = None
        self.listeners = {}
        self._adding_listeners = []
        self._removing_listeners = []
        self._last_message = {}
        self._signal_lock = Lock()
        self._message_queue = {}
        self._is_queue_processing = False

        # Channels
        self.channels = {}

        # Console Commands.
        self.commands = []
        self.console_job = Job(
            job_name="kernel.console.ticks",
            process=self._console_job_tick,
            interval=0.05,
        )
        self._console_buffer = ""
        self.queue = []
        self._console_channel = self.channel("console", timestamp=True)
        self._console_channel.timestamp = True
        self.console_channel_file = None

        self._current_directory = "."

        # Persistent Settings
        if config is not None:
            self.set_config(config)
        else:
            self._config = None

        # Arguments Objects
        self.args = None

        self.console_argument = console_argument
        self.console_option = console_option

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
        import datetime
        import functools
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
        Accepts a plugin function. Plugins should accept two arguments: kernel and lifecycle.

        The kernel is a copy of this kernel as an instanced object and the lifecycle is the stage of the kernel
        in the program lifecycle. Plugins should be added during startup.

        The "added" lifecycle occurs during plugin add, and is the only lifecycle to care about a return value which
        in this case serves as a path. If provided this should be the path of a service provider to bind that plugin
        to the provided service. Unlike other plugins the provided plugin will be bound to the service returned.

        :param plugin:
        :return:
        """
        service_path = plugin(self, "service")
        module_path = plugin(self, "module")
        if service_path is not None:
            if service_path not in self._service_plugins:
                self._service_plugins[service_path] = list()
            plugins = self._service_plugins[service_path]
        elif module_path is not None:
            if module_path not in self._module_plugins:
                self._module_plugins[module_path] = list()
            plugins = self._module_plugins[module_path]
        else:
            plugins = self._kernel_plugins
        if plugin not in plugins:
            plugins.append(plugin)

    # ==========
    # SERVICES API
    # ==========

    def services(self, domain: str, active: bool = False):
        """
        Fetch the active or available servers from the kernel.lookup
        @param domain: domain of service to lookup
        @param active: look up active or available
        @return:
        """
        if active:
            try:
                return self._registered["service/{domain}/active".format(domain=domain)]
            except KeyError:
                return None
        else:
            try:
                return self._registered[
                    "service/{domain}/available".format(domain=domain)
                ]
            except KeyError:
                return []

    def services_active(self):
        """
        Generate a series of active services.

        @return: domain, service
        """
        matchtext = "service/(.*)/active"
        match = re.compile(matchtext)
        for r in list(self._registered):
            result = match.match(r)
            if result:
                yield result.group(1), self._registered[r]

    def services_available(self):
        """
        Generate a series of available services.

        @return: domain, service
        """
        matchtext = "service/(.*)/available"
        match = re.compile(matchtext)
        for r in list(self._registered):
            result = match.match(r)
            if result:
                yield result.group(1), self._registered[r]

    def remove_service(self, service: Service):
        self.set_service_lifecycle(service, LIFECYCLE_SHUTDOWN)
        for path, services in self.services_available():
            for i in range(len(services) - 1, -1, -1):
                s = services[i]
                if s is service:
                    del services[i]
                self.register(path, services)

    def add_service(
        self,
        domain: str,
        service: Service,
        registered_path: str = None,
        activate: bool = False,
    ):
        """
        Adds a reference to a service.

        @param domain: service domain
        @param service: service to add
        @param registered_path: original provider path of service being added to notify plugins
        @return:
        """
        services = self.services(domain)
        if not services:
            services = []
            activate = True

        services.append(service)
        service.registered_path = registered_path
        self.register("service/{domain}/available".format(domain=domain), services)
        self.set_service_lifecycle(service, LIFECYCLE_SERVICE_ADDED)
        if activate:
            self.activate(domain, service)

    def activate_service_path(self, domain: str, path: str, assigned: bool = False):
        """
        Activate service at domain and path.

        @param domain:
        @param path:
        @return:
        """
        services = self.services(domain)
        if services is None:
            raise ValueError

        index = -1
        for i, serv in enumerate(services):
            if serv.path == path:
                index = i
                break
        if index == -1:
            raise ValueError
        self.activate_service_index(domain, index, assigned)

    def activate_service_index(self, domain: str, index: int, assigned: bool = False):
        """
        Activate the service at the given domain and index.

        If there is a currently active service it will be detached and shutdown.

        @param domain: service domain name
        @param index: index of the service to activate.
        @return:
        """
        services = self.services(domain)
        if services is None:
            raise ValueError

        service = services[index]
        active = self.services(domain, True)
        if active is not None:
            if service is active:
                # Do not set to self
                return
        self.activate(domain, service, assigned)

    def activate(self, domain, service, assigned: bool = False):
        """
        Activate the service specified on the domain specified.

        @param domain: Domain at which to activate service
        @param service: service to activate
        @return:
        """
        # Deactivate anything on this domain.
        self.deactivate(domain)

        # Set service and attach.
        self.register("service/{domain}/active".format(domain=domain), service)

        self.set_service_lifecycle(service, LIFECYCLE_SERVICE_ATTACHED)

        # Set context values for the domain.
        setattr(self, domain, service)
        for context_name in self.contexts:
            # For every registered context, set the given domain to this service
            context = self.contexts[context_name]
            setattr(context, domain, service)

        # Update any lookup changes.
        self.lookup_changes(list(service._registered))

        # Signal activation
        self.signal("activate;{domain}".format(domain=domain), "/", service)

        if assigned:
            self.set_service_lifecycle(service, LIFECYCLE_SERVICE_ASSIGNED)

    def deactivate(self, domain):
        """
        Deactivate the service currently active at the given domain.

        @param domain: domain at which to deactivate the service.
        @return:
        """
        setattr(self, domain, None)
        active = self.services(domain, True)
        if active is not None:
            previous_active = active
            if previous_active is not None:
                self.set_service_lifecycle(previous_active, LIFECYCLE_SERVICE_DETACHED)
                self.lookup_changes(list(previous_active._registered))

            for context_name in self.contexts:
                # For every registered context, set the given domain to None.
                context = self.contexts[context_name]
                setattr(context, domain, None)
            self.signal(
                "deactivate;{domain}".format(domain=domain), "/", previous_active
            )

    # ==========
    # DELEGATES API
    # ==========

    def add_delegate(
        self, delegate: Any, lifecycle_object: Union[Module, Service, "Kernel"]
    ):
        """
        Adds delegate to the kernel that should cause the delegate to mimic the lifecycle
        of the selected object.

        @param delegate:
        @param lifecycle_object:
        @return:
        """
        self.delegates.append((delegate, lifecycle_object))
        self.update_linked_lifecycles(lifecycle_object)

    # ==========
    # LIFECYCLE MANAGEMENT
    # ==========

    @staticmethod
    def service_lifecycle_position(obj):
        try:
            return obj._service_lifecycle
        except AttributeError:
            return 0

    @staticmethod
    def module_lifecycle_position(obj):
        try:
            return obj._module_lifecycle
        except AttributeError:
            return 0

    @staticmethod
    def kernel_lifecycle_position(obj):
        try:
            return obj._kernel_lifecycle
        except AttributeError:
            return 0

    def get_linked_objects(self, obj: Any, object_list: list = None):
        """
        adds
        @param obj: Object to check for delegate links.
        @param object_list: list of objects being added to
        @return: object_list of linked delegates
        """
        if object_list is None:
            object_list = list()
        object_list.append(obj)
        for delegate, cookie in self.delegates:
            if cookie is obj:
                self.get_linked_objects(delegate, object_list)
        return object_list

    def update_linked_lifecycles(self, model):
        """
        Matches the lifecycle of the obj on the model.

        @param model: lifecycled object being mimicked
        @return:
        """
        if isinstance(model, Module):
            self.set_module_lifecycle(model, Kernel.module_lifecycle_position(model))
        elif isinstance(model, Service):
            self.set_service_lifecycle(model, Kernel.service_lifecycle_position(model))
        elif isinstance(model, Kernel):
            self.set_kernel_lifecycle(model, Kernel.kernel_lifecycle_position(model))

    def set_kernel_lifecycle(self, kernel, position, *args, **kwargs):
        """
        Sets the kernel's lifecycle object

        @param position: lifecycle position to set
        @param kernel: optional kernel if not kernel object directly
        @param args:
        @param kwargs:
        @return:
        """
        channel = self.channel("kernel-lifecycle")
        objects = self.get_linked_objects(kernel)
        klp = Kernel.kernel_lifecycle_position
        start = klp(kernel)
        end = position

        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_PREREGISTER <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_PREREGISTER
                if channel:
                    channel("kernel-preregister: {object}".format(object=str(k)))
                if hasattr(k, "preregister"):
                    k.preregister()
        if start < LIFECYCLE_KERNEL_PREREGISTER <= end:
            if channel:
                channel("(plugin) kernel-preregister")
            for plugin in self._kernel_plugins:
                plugin(kernel, "preregister")

        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_REGISTER <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_REGISTER
                if channel:
                    channel("kernel-registration: {object}".format(object=str(k)))
                if hasattr(k, "registration"):
                    k.registration()
        if start < LIFECYCLE_KERNEL_REGISTER <= end:
            if channel:
                channel("(plugin) kernel-register")
            for plugin in self._kernel_plugins:
                plugin(kernel, "register")

        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_CONFIGURE <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_CONFIGURE
                if channel:
                    channel("kernel-configure: {object}".format(object=str(k)))
                if hasattr(k, "configure"):
                    k.configure()
        if start < LIFECYCLE_KERNEL_CONFIGURE <= end:
            if channel:
                channel("(plugin) kernel-configure")
            for plugin in self._kernel_plugins:
                plugin(kernel, "configure")

        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_PREBOOT <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_PREBOOT
                if channel:
                    channel("kernel-preboot: {object}".format(object=str(k)))
                if hasattr(k, "preboot"):
                    k.preboot()
        if start < LIFECYCLE_KERNEL_PREBOOT <= end:
            if channel:
                channel("(plugin) kernel-preboot")
            for plugin in self._kernel_plugins:
                plugin(kernel, "preboot")

        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_BOOT <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_BOOT
                if channel:
                    channel("kernel-boot: {object} boot".format(object=str(k)))
                if hasattr(k, "boot"):
                    k.boot()
                self._signal_attach(k)
                self._lookup_attach(k)
        if start < LIFECYCLE_KERNEL_BOOT <= end:
            if channel:
                channel("(plugin) kernel-boot")
            for plugin in self._kernel_plugins:
                plugin(kernel, "boot")

        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_POSTBOOT <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_POSTBOOT
                if channel:
                    channel("kernel-postboot: {object}".format(object=str(k)))
                if hasattr(k, "postboot"):
                    k.postboot()
        if start < LIFECYCLE_KERNEL_POSTBOOT <= end:
            if channel:
                channel("(plugin) kernel-postboot")
            for plugin in self._kernel_plugins:
                plugin(kernel, "postboot")

        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_PRESTART <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_PRESTART
                if channel:
                    channel("kernel-prestart: {object}".format(object=str(k)))
                if hasattr(k, "prestart"):
                    k.prestart()
        if start < LIFECYCLE_KERNEL_PRESTART <= end:
            if channel:
                channel("(plugin) kernel-prestart")
            for plugin in self._kernel_plugins:
                plugin(kernel, "prestart")

        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_START <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_START
                if channel:
                    channel("kernel-start: {object}".format(object=str(k)))
                if hasattr(k, "start"):
                    k.start()
        if start < LIFECYCLE_KERNEL_START <= end:
            if channel:
                channel("(plugin) kernel-start")
            for plugin in self._kernel_plugins:
                plugin(kernel, "start")

        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_POSTSTART <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_POSTSTART
                if channel:
                    channel("kernel-poststart: {object}".format(object=str(k)))
                if hasattr(k, "poststart"):
                    k.poststart()
        if start < LIFECYCLE_KERNEL_POSTSTART <= end:
            if channel:
                channel("(plugin) kernel-poststart")
            for plugin in self._kernel_plugins:
                plugin(kernel, "poststart")

        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_PREMAIN <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_PREMAIN
                if channel:
                    channel("kernel-premain: {object}".format(object=str(k)))
                if hasattr(k, "premain"):
                    k.premain()
        if start < LIFECYCLE_KERNEL_PREMAIN <= end:
            if channel:
                channel("(plugin) kernel-premain")
            for plugin in self._kernel_plugins:
                plugin(kernel, "premain")

        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_MAINLOOP <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_MAINLOOP
                if channel:
                    channel("kernel-mainloop: {object}".format(object=str(k)))
                if hasattr(k, "mainloop"):
                    k.mainloop()
        if start < LIFECYCLE_KERNEL_MAINLOOP <= end:
            if channel:
                channel("(plugin) kernel-mainloop")
            for plugin in self._kernel_plugins:
                plugin(kernel, "mainloop")

        if start < LIFECYCLE_KERNEL_PRESHUTDOWN <= end:
            if channel:
                channel("(plugin) kernel-preshutdown")
            for plugin in self._kernel_plugins:
                plugin(kernel, "preshutdown")
        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_PRESHUTDOWN <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_PRESHUTDOWN
                if channel:
                    channel("kernel-preshutdown: {object}".format(object=str(k)))
                self._signal_detach(k)
                self._lookup_detach(k)
                if hasattr(k, "preshutdown"):
                    k.preshutdown()

        if start < LIFECYCLE_SHUTDOWN <= end:
            if channel:
                channel("(plugin) kernel-shutdown")
            for plugin in self._kernel_plugins:
                plugin(kernel, "shutdown")
        for k in objects:
            if klp(k) < LIFECYCLE_SHUTDOWN <= end:
                k._kernel_lifecycle = LIFECYCLE_SHUTDOWN
                if channel:
                    channel("kernel-shutdown: {object}".format(object=str(k)))
                self._signal_detach(k)
                self._lookup_detach(k)
                if hasattr(k, "shutdown"):
                    k.shutdown()

        for k in objects:
            k._kernel_lifecycle = end

    def set_service_lifecycle(self, service, position, *args, **kwargs):
        """
        Advances the lifecycle of the service to the given position. Any linked elements are advanced to this same
        position even if those delegates were added later. This will not call the lifecycle events more than once
        per object unless the lifecycle repeats (attached/detached).

        @param position: position lifecycle should be advanced to.
        @param service: service to advanced, if not this service.
        @param args: additional args
        @param kwargs: additional kwargs
        @return:
        """
        channel = self.channel("service-lifecycle")
        objects = self.get_linked_objects(service)
        slp = Kernel.service_lifecycle_position

        start = slp(service)
        end = position

        # Update objects: added
        for s in objects:
            if slp(s) < LIFECYCLE_SERVICE_ADDED <= end:
                s._service_lifecycle = LIFECYCLE_SERVICE_ADDED
                if channel:
                    channel("service-added: {object}".format(object=str(s)))
                if hasattr(s, "added"):
                    s.added(*args, **kwargs)

        # Update plugin: added
        if start < LIFECYCLE_SERVICE_ADDED <= end:
            start = LIFECYCLE_SERVICE_ADDED
            if channel:
                channel("(plugin) service-added: {object}".format(object=str(service)))
            try:
                for plugin in self._service_plugins[service.registered_path]:
                    plugin(service, "added")
            except (KeyError, AttributeError):
                pass

        # Update objects: service_detach
        attached_positions = (
            LIFECYCLE_SERVICE_ATTACHED,
            LIFECYCLE_SERVICE_ASSIGNED,
        )
        for s in objects:
            if (
                slp(s) in attached_positions and end not in attached_positions
            ):  # starting attached
                s._service_lifecycle = LIFECYCLE_SERVICE_DETACHED
                if channel:
                    channel("service-service_detach: {object}".format(object=str(s)))
                if hasattr(s, "service_detach"):
                    s.service_detach(*args, **kwargs)
                self._signal_detach(s)
                self._lookup_detach(s)

        # Update plugin: service_detach
        if start in attached_positions and end not in attached_positions:
            if channel:
                channel(
                    "(plugin) service-service_detach: {object}".format(
                        object=str(service)
                    )
                )
            start = LIFECYCLE_SERVICE_DETACHED
            try:
                for plugin in self._service_plugins[service.registered_path]:
                    plugin(service, "service_detach")
            except (KeyError, AttributeError):
                pass

        # Update objects: service_attach
        for s in objects:
            if (
                slp(s) not in attached_positions and end in attached_positions
            ):  # ending attached
                s._service_lifecycle = LIFECYCLE_SERVICE_ATTACHED
                if channel:
                    channel("service-service_attach: {object}".format(object=str(s)))
                if hasattr(s, "service_attach"):
                    s.service_attach(*args, **kwargs)
                self._signal_attach(s)
                self._lookup_attach(s)

        # Update plugin: service_attach
        if start not in attached_positions and end in attached_positions:
            if channel:
                channel(
                    "(plugin) service-service_attach: {object}".format(
                        object=str(service)
                    )
                )
            start = LIFECYCLE_SERVICE_ATTACHED
            try:
                for plugin in self._service_plugins[service.registered_path]:
                    plugin(service, "service_attach")
            except (KeyError, AttributeError):
                pass

        # Update objects: assigned
        for s in objects:
            if (
                slp(s) == LIFECYCLE_SERVICE_ATTACHED
                and end == LIFECYCLE_SERVICE_ASSIGNED
            ):
                s._service_lifecycle = LIFECYCLE_SERVICE_ASSIGNED
                if channel:
                    channel("service-assigned: {object}".format(object=str(s)))
                if hasattr(s, "assigned"):
                    s.assigned(*args, **kwargs)

        # Update plugin: assigned
        if start == LIFECYCLE_SERVICE_ATTACHED and end == LIFECYCLE_SERVICE_ASSIGNED:
            start = LIFECYCLE_SERVICE_ASSIGNED
            if channel:
                channel(
                    "(plugin) service-assigned: {object}".format(object=str(service))
                )
            try:
                for plugin in self._service_plugins[service.registered_path]:
                    plugin(service, "assigned")
            except (KeyError, AttributeError):
                pass

        # Update objects: service_shutdown
        for s in objects:
            if slp(s) < LIFECYCLE_SHUTDOWN <= end:
                s._service_lifecycle = LIFECYCLE_SHUTDOWN
                if channel:
                    channel("service-shutdown: {object}".format(object=str(s)))
                if hasattr(s, "shutdown"):
                    s.shutdown(*args, **kwargs)

        # Update plugin: shutdown
        if start < LIFECYCLE_SHUTDOWN <= end:
            if channel:
                channel(
                    "(plugin) service-shutdown: {object}".format(object=str(service))
                )
            start = LIFECYCLE_SHUTDOWN
            self.remove_service(service)
            try:
                for plugin in self._service_plugins[service.registered_path]:
                    plugin(service, "shutdown")
            except (KeyError, AttributeError):
                pass

        # Update objects: position
        for s in objects:
            s._service_lifecycle = end

    def set_module_lifecycle(self, module, position, *args, **kwargs):
        """
        Advances module's lifecycle to the given position. Calling any lifecycle events
        that are required in the process.

        @param position:
        @param module: optional module reference if not self.
        @param args:
        @param kwargs:
        @return:
        """
        channel = self.channel("module-lifecycle")
        objects = self.get_linked_objects(module)
        mlp = Kernel.module_lifecycle_position

        start = mlp(module)
        end = position

        # Update objects: opened
        for m in objects:
            if mlp(m) < LIFECYCLE_MODULE_OPENED <= end:
                m._module_lifecycle = LIFECYCLE_MODULE_OPENED
                if channel:
                    channel("module-module_open: {object}".format(object=str(m)))
                if hasattr(m, "module_open"):
                    m.module_open(*args, **kwargs)
                self._signal_attach(m)
                self._lookup_attach(m)

        # Update plugin: opened
        if start < LIFECYCLE_MODULE_OPENED <= end:
            if channel:
                channel(
                    "(plugin) module-module_open: {object}".format(object=str(module))
                )
            module.context.opened[module.name] = module
            try:
                for plugin in self._module_plugins[module.registered_path]:
                    plugin(module, "module_open")
            except (KeyError, AttributeError):
                pass

        # Update objects: closed
        for m in objects:
            if mlp(m) < LIFECYCLE_MODULE_CLOSED <= end:
                m._module_lifecycle = LIFECYCLE_MODULE_CLOSED
                if channel:
                    channel("module-module_closed: {object}".format(object=str(m)))
                if hasattr(m, "module_close"):
                    m.module_close(*args, **kwargs)
                self._signal_detach(m)
                self._lookup_detach(m)

        # Update plugin: closed
        if start < LIFECYCLE_MODULE_CLOSED <= end:
            if channel:
                channel(
                    "(plugin) module-module_close: {object}".format(object=str(module))
                )
            try:
                # If this is a module, we remove it from opened.
                del module.context.opened[module.name]
            except (KeyError, AttributeError):
                pass  # Nothing to close.
            try:
                for plugin in self._module_plugins[module.registered_path]:
                    plugin(module, "module_close")
            except (KeyError, AttributeError):
                pass

        # Update objects: shutdown
        for m in objects:
            if mlp(m) < LIFECYCLE_SHUTDOWN <= end:
                m._module_lifecycle = LIFECYCLE_SHUTDOWN
                if channel:
                    channel("module-shutdown: {object}".format(object=str(m)))
                if hasattr(m, "shutdown"):
                    m.shutdown()

        # Update plugin: shutdown
        if start < LIFECYCLE_SHUTDOWN <= end:
            if channel:
                channel("(plugin) module-shutdown: {object}".format(object=str(module)))
            try:
                for plugin in self._module_plugins[module.registered_path]:
                    plugin(module, "shutdown")
            except (KeyError, AttributeError):
                pass

        for m in objects:
            m._module_lifecycle = end

    # ==========
    # LIFECYCLE PROCESSES
    # ==========

    def __call__(self):
        self.set_kernel_lifecycle(self, LIFECYCLE_KERNEL_MAINLOOP)

    def preboot(self):
        self.command_boot()
        self.choices_boot()

    def boot(self) -> None:
        """
        Kernel boot sequence. This should be called after all the registered devices are established.

        :return:
        """
        self.scheduler_thread = self.threaded(self.run, "Scheduler")
        self.signal_job = self.add_job(
            run=self.process_queue,
            name="kernel.signals",
            interval=0.005,
            run_main=True,
            conditional=lambda: not self._is_queue_processing,
        )
        self._booted = True

    def postboot(self):
        self.batch_boot()
        if hasattr(self.args, "verbose") and self.args.verbose:
            self._start_debugging()

    def start(self):
        if hasattr(self.args, "set") and self.args.set is not None:
            # Set the variables requested here.
            for v in self.args.set:
                try:
                    attr = v[0]
                    value = v[1]
                    self.console("set %s %s\n" % (attr, value))
                except IndexError:
                    break

    def poststart(self):
        if hasattr(self.args, "execute") and self.args.execute:
            # Any execute code segments gets executed here.
            self.channel("console").watch(print)
            for v in self.args.execute:
                if v is None:
                    continue
                self.console(v.strip() + "\n")
            self.channel("console").unwatch(print)

        if hasattr(self.args, "batch") and self.args.batch:
            # If a batch file is specified it gets processed here.
            self.channel("console").watch(print)
            with self.args.batch as batch:
                for line in batch:
                    self.console(line.strip() + "\n")
            self.channel("console").unwatch(print)

    def premain(self):
        if hasattr(self.args, "console") and self.args.console:
            self.channel("console").watch(print)
            import sys

            async def aio_readline(loop):
                while not self._shutdown:
                    print(">>", end="", flush=True)

                    line = await loop.run_in_executor(None, sys.stdin.readline)
                    self.console("." + line + "\n")
                    if line in ("quit", "shutdown"):
                        break

            import asyncio

            loop = asyncio.get_event_loop()
            loop.run_until_complete(aio_readline(loop))
            loop.close()
            self.channel("console").unwatch(print)

    def preshutdown(self):
        channel = self.channel("shutdown")
        _ = self.translation

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
                self.set_module_lifecycle(
                    obj,
                    LIFECYCLE_SHUTDOWN,
                    None,
                    opened_name,
                    channel=channel,
                    shutdown=True,
                )

        for domain, services in self.services_available():
            for service in list(services):
                self.set_service_lifecycle(service, LIFECYCLE_SHUTDOWN)

    def shutdown(self):
        """
        Starts shutdown procedure.

        Suspends all signals.
        Each initialized context is flushed and shutdown.
        Each opened module within the context is stopped and closed.

        All threads are stopped.

        Any residual attached listeners are made warnings.

        :param channel:
        :return:
        """
        channel = self.channel("shutdown")
        self._shutdown = True
        self.state = STATE_END  # Terminates the Scheduler.

        _ = self.translation

        try:
            self.process_queue()  # Notify listeners of state.
        except RuntimeError:
            pass  # Runtime error for gui objects in the process of being killed.
        # Suspend Signals

        def signal(code, path, *message):
            if channel:
                channel(_("Suspended Signal: %s for %s" % (code, message)))

        self.signal = signal  # redefine signal function.

        def console(code):
            if channel:
                for c in code.split("\n"):
                    if c:
                        channel(_("Suspended Command: %s" % c))

        self.console = console  # redefine console signal

        self.process_queue()  # Process last events.

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
        self._last_message = {}
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

    def find(self, *args):
        """
        Find registered path and objects that regex match the given matchtext

        :param args: parts of matchtext
        :return:
        """
        matchtext = "/".join(args)
        match = re.compile(matchtext)
        for domain, service in self.services_active():
            for r in service._registered:
                if match.match(r):
                    yield service._registered[r], r, list(r.split("/"))[-1]
        for r in self._registered:
            if match.match(r):
                yield self._registered[r], r, list(r.split("/"))[-1]

    def match(self, matchtext: str, suffix: bool = False) -> Generator[str, None, None]:
        """
        Lists all registered paths that regex match the given matchtext

        :param matchtext: match text to match.
        :param suffix: provide the suffix of the match only.
        :return:
        """
        match = re.compile(matchtext)
        for domain, service in self.services_active():
            for r in service._registered:
                if match.match(r):
                    if suffix:
                        yield list(r.split("/"))[-1]
                    else:
                        yield r
        for r in self._registered:
            if match.match(r):
                if suffix:
                    yield list(r.split("/"))[-1]
                else:
                    yield r

    def lookup(self, *args):
        """
        Lookup registered value from the registered dictionary checking the active devices first.

        @param args: parts of value
        @return:
        """
        value = "/".join(args)
        for domain, service in self.services_active():
            try:
                return service._registered[value]
            except KeyError:
                pass
        try:
            return self._registered[value]
        except KeyError:
            return None

    def lookup_all(self, *args):
        """
        Lookup registered values from the registered dictionary checking the active devices first.

        :param args: parts of matchtext
        :return:
        """
        for obj, name, sname in self.find(*args):
            yield obj

    def _remove_delegates(self, cookie: Any):
        """
        Remove any delegates bound to the given cookie.

        @param cookie:
        @return:
        """
        for i in range(len(self.delegates) - 1, -1, -1):
            delegate, ref = self.delegates[i]
            if cookie is ref:
                del self.delegates[i]

    def _lookup_detach(
        self,
        cookie: Any,
    ) -> None:
        """
        Detach all lookups associated with this cookie.

        @param cookie:
        @return:
        """
        for lookup in self.lookups:
            listens = self.lookups[lookup]
            for index, lul in enumerate(listens):
                listener, obj = lul
                if obj is cookie:
                    del listens[index]

    def _lookup_attach(
        self,
        scan_object: Union[Service, Module, None] = None,
        cookie: Any = None,
    ) -> None:
        """
        Attaches any lookups flagged as "@lookup_listener" to listen to that lookup.

        @param scan_object: Object to be scanned for looks to apply
        @param cookie: Cookie to attach these lookup listeners against
        @return:
        """
        if cookie is None:
            cookie = scan_object
        for attr in dir(scan_object):
            func = getattr(scan_object, attr)
            if hasattr(func, "lookup_decor"):
                for lul in func.lookup_decor:
                    self.add_lookup(lul, func, cookie)

    def add_lookup(self, matchtext: str, funct: Callable, cookie: Any):
        """
        Add matchtext equal lookup to call the given function bound to the given lifecycle object.

        @param matchtext:
        @param funct:
        @param cookie:
        @return:
        """
        if matchtext not in self.lookups:
            self.lookups[matchtext] = list()
        self.lookups[matchtext].append((funct, cookie))

    def lookup_changes(self, paths: List[str]) -> None:
        """
        Call for lookup changes, given a list of changed paths.

        @param paths:
        @return:
        """
        self.channel("lookup")(
            "Changed all: %s (%s)"
            % (str(paths), str(threading.currentThread().getName()))
        )
        with self._lookup_lock:
            if not self._dirty_paths:
                self.schedule(self._clean_lookup)
            self._dirty_paths.extend(paths)

    def lookup_change(self, path: str) -> None:
        """
        Manual call for lookup_change. Called during changing events register, unregister, activate_service, and the
        equal service events.

        @return:
        """
        self.channel("lookup")(
            "Changed %s (%s)" % (str(path), str(threading.currentThread().getName()))
        )
        with self._lookup_lock:
            if not self._dirty_paths:
                self.schedule(self._clean_lookup)
            self._dirty_paths.append(path)

    def _matchtext_is_dirty(self, matchtext: str) -> bool:
        match = re.compile(matchtext)
        for r in self._dirty_paths:
            if match.match(r):
                return True
        return False

    def _registered_data_changed(self, *args, **kwargs) -> None:
        """
        Triggered on events which can changed the registered data within the lookup.
        @return:
        """
        channel = self.channel("lookup")
        if channel:
            channel(
                "Lookup Change Processing (%s)"
                % (str(threading.currentThread().getName()))
            )
        with self._lookup_lock:
            for matchtext in self.lookups:
                if channel:
                    channel("Checking: %s" % matchtext)
                listeners = self.lookups[matchtext]
                try:
                    previous_matches = self.lookup_previous[matchtext]
                except KeyError:
                    previous_matches = None
                if previous_matches is not None and not self._matchtext_is_dirty(
                    matchtext
                ):
                    continue
                if channel:
                    channel("Differences for %s" % matchtext)
                new_matches = list(self.find(matchtext))
                if previous_matches != new_matches:
                    if channel:
                        channel("Values differ. %s" % matchtext)
                    self.lookup_previous[matchtext] = new_matches
                    for listener in listeners:
                        funct, lso = listener
                        funct(new_matches, previous_matches)
                else:
                    if channel:
                        channel("Values identical: %s" % matchtext)
            self._dirty_paths.clear()

    def register(self, path: str, obj: Any) -> None:
        """
        Register an element at a given subpath.
        If this Kernel is not root, then it is registered relative to this location.

        :param path: a "/" separated hierarchical index to the object
        :param obj: object to be registered
        :return:
        """
        self._registered[path] = obj
        try:
            obj.sub_register(self)
        except AttributeError:
            pass
        self.lookup_change(path)

    def unregister(self, path: str):
        del self._registered[path]
        self.lookup_change(path)

    # ==========
    # COMMAND REGISTRATION
    # ==========

    def console_command(self, *args, **kwargs) -> Callable:
        """
        Service console command registration.

        Uses the current registration to register the given command.
        """
        return console_command(self, *args, **kwargs)

    def console_command_remove(self, *args, **kwargs) -> Callable:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_command being removed.
        """
        return console_command_remove(self, *args, **kwargs)

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

    def register_as_context(self, context):
        # If context get after boot, apply all services.
        for domain, service in self.services_active():
            setattr(context, domain, service)
        self.contexts[context.path] = context

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
        self.register_as_context(derive)
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

    def keylist(self, path: str, suffix: bool = False) -> Generator[str, None, None]:
        """
        Get all keys located at the given path location. The keys are listed in absolute path locations.

        @param path: Path to check for keys.
        @param suffix:  Should only the suffix be yielded.
        @return:
        """
        if self._config is None:
            return
        path = self.abs_path(path)
        self._config.SetPath(path)
        more, value, index = self._config.GetFirstEntry()
        while more:
            if suffix:
                yield value
            else:
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

    def run(self, *args) -> None:
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
                    if job._remaining is not None:
                        job._remaining = job._remaining - 1
                        if job._remaining <= 0:
                            del jobs[job_name]
                        if job._remaining < 0:
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
        try:
            job.reset()
            # Could be recurring job. Reset on reschedule.
        except AttributeError:
            return
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
        self._signal_lock.acquire(True)
        self._message_queue[code] = path, message
        self._signal_lock.release()

    def process_queue(self, *args) -> None:
        """
        Performed in the run_later thread. Signal groups. Threadsafe.

        Process the signals queued up. Inserting any attaching listeners, removing any removing listeners. And
        providing the newly attached listeners the last message known from that signal.
        :param args: None
        :return:
        """
        if (
            len(self._message_queue) == 0
            and len(self._adding_listeners) == 0
            and len(self._removing_listeners) == 0
        ):
            return
        self._is_queue_processing = True
        self._signal_lock.acquire(True)

        add = None
        if len(self._adding_listeners) != 0:
            add = self._adding_listeners
            self._adding_listeners = []

        remove = None
        if len(self._removing_listeners):
            remove = self._removing_listeners
            self._removing_listeners = []

        queue = self._message_queue
        self._message_queue = {}

        self._signal_lock.release()

        # Process any adding listeners.
        if add is not None:
            for signal, path, funct, lso in add:
                if signal in self.listeners:
                    listeners = self.listeners[signal]
                    listeners.append((funct, lso))
                else:
                    self.listeners[signal] = [(funct, lso)]
                if path + signal in self._last_message:
                    last_message = self._last_message[path + signal]
                    funct(path, *last_message)

        # Process any removing listeners.
        if remove is not None:
            for signal, path, remove_funct, remove_lso in remove:
                if signal in self.listeners:
                    listeners = self.listeners[signal]
                    removed = False
                    for i, listen in enumerate(listeners):
                        listen_funct, listen_lso = listen
                        if (listen_funct == remove_funct or remove_funct is None) and (
                            listen_lso is remove_lso or remove_lso is None
                        ):
                            del listeners[i]
                            removed = True
                            break
                    if not removed:
                        print("Value error removing: %s  %s" % (str(listeners), signal))

        # Process signals.
        signal_channel = self.channel("signals")
        for signal, payload in queue.items():
            path, message = payload
            if signal in self.listeners:
                listeners = self.listeners[signal]
                for listener, listen_lso in listeners:
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
            if path is not None:
                signal = path + signal
            self._last_message[signal] = message
        self._is_queue_processing = False

    def last_signal(self, signal: str, path: str) -> Optional[Tuple]:
        """
        Queries the last signal for a particular signal/path

        :param signal: signal to query.
        :param path: path for the given signal to query.
        :return: Last signal sent through the kernel for that signal and path
        """
        try:
            return self._last_message[path + signal]
        except KeyError:
            return None

    def listen(
        self,
        signal: str,
        path: str,
        funct: Callable,
        lifecycle_object: Any = None,
    ) -> None:
        """
        Attaches callable to a particular signal. This will be attached next time the signals are processed.

        @param signal:
        @param path:
        @param funct:
        @param lifecycle_object:
        @return:
        """
        self._signal_lock.acquire(True)
        self._adding_listeners.append((signal, path, funct, lifecycle_object))
        self._signal_lock.release()

    def unlisten(
        self,
        signal: str,
        path: str,
        funct: Callable,
        lifecycle_object: Any = None,
    ) -> None:
        """
        Removes callable listener for a given signal. This will be detached next time the signals code runs.

        @param signal:
        @param path:
        @param funct:
        @param lifecycle_object:
        @return:
        """
        self._signal_lock.acquire(True)
        self._removing_listeners.append((signal, path, funct, lifecycle_object))
        self._signal_lock.release()

    def _signal_attach(
        self,
        scan_object: Union[Service, Module, None] = None,
        cookie: Any = None,
    ) -> None:
        """
        Attaches any signals flagged as "@signal_listener" to listen to that signal.

        @param scan_object:
        @return:
        """
        if cookie is None:
            cookie = scan_object
        for attr in dir(scan_object):
            func = getattr(scan_object, attr)
            if hasattr(func, "signal_listener"):
                for sl in func.signal_listener:
                    self.listen(sl, self._path, func, cookie)

    def _signal_detach(
        self,
        cookie: Any,
    ) -> None:
        """
        Detach all signals attached against the given cookie

        @param cookie: cookie used to bind this listener.
        @return:
        """
        self._signal_lock.acquire(True)

        for signal in self.listeners:
            listens = self.listeners[signal]
            for listener, lso in listens:
                if lso is cookie:
                    self._removing_listeners.append((signal, None, listener, cookie))

        self._signal_lock.release()

    # ==========
    # CHANNEL PROCESSING
    # ==========

    def channel(self, channel: str, *args, **kwargs) -> "Channel":
        if channel not in self.channels:
            chan = Channel(channel, *args, **kwargs)
            chan._ = self.translation
            self.channels[channel] = chan

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
            channel(text, indent=False)

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
            for command_funct, command_name, cmd_re in self.find(
                "command", str(input_type), ".*"
            ):
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
                    message = command_funct.help
                    if e.msg:
                        message = e.msg
                    channel(_("Syntax Error (%s): %s") % (command, message))
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
                    _("%s is not a registered command in this context: %s")
                    % (command, ctx_name)
                )
                return None
        return data

    def register_choices(self, sheet, choices):
        """
        Registers choices to a given sheet. If the sheet already exists then the new choices
        are appended to the given sheet.

        If these choices are registered to an object of Context type we then set the given
        default values.

        @param sheet: sheet being registered to
        @param choices: choices being registered
        @return:
        """
        key = "choices/%s" % sheet
        if key in self._registered:
            others = self._registered[key]
            others.extend(choices)
            self.register(key, others)  # Reregister to trigger lookup change
        else:
            self.register(key, choices)
        for c in choices:
            obj = c["object"]
            if isinstance(obj, Context):
                obj.setting(c["type"], c["attr"], c["default"])

    # ==========
    # KERNEL CONSOLE COMMANDS
    # ==========

    def choices_boot(self) -> None:
        _ = self.translation
        choices = [
            {
                "attr": "print_shutdown",
                "object": self.root,
                "default": False,
                "type": bool,
                "label": _("Print Shutdown"),
                "tip": _("Print shutdown log when closed."),
            },
        ]
        self.register_choices("preferences", choices)

    def command_boot(self) -> None:
        _ = self.translation

        # ==========
        # HELP COMMANDS
        # ==========

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
                for func, command_name, sname in self.find(
                    "command", ".*", extended_help
                ):
                    parts = command_name.split("/")
                    input_type = parts[1]
                    command_item = parts[2]
                    if command_item != extended_help and not func.regex:
                        continue
                    if input is not None and input != input_type:
                        continue
                    func = self.lookup(command_name)
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
                func = self.lookup(command_name)
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

        # ==========
        # THREADS SCHEDULER
        # ==========

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

        # ==========
        # CORE OBJECTS COMMANDS
        # ==========

        @self.console_command("register", _("register"))
        def register(channel, _, args=tuple(), **kwargs):
            channel(_("----------"))
            channel(_("Objects Registered:"))
            matchtext = ".*"
            if len(args) >= 1:
                matchtext = str(args[0]) + matchtext
            match = re.compile(matchtext)
            for domain, service in self.services_active():
                for i, r in enumerate(service._registered):
                    if match.match(r):
                        obj = service._registered[r]
                        channel(
                            _("%s, %d: %s type of %s") % (domain, i + 1, r, str(obj))
                        )
            for i, r in enumerate(self._registered):
                if match.match(r):
                    obj = self._registered[r]
                    channel(_("%s, %d: %s type of %s") % ("kernel", i + 1, r, str(obj)))
            channel(_("----------"))

        @self.console_command("context", _("context"))
        def context(channel, _, args=tuple(), **kwargs):
            if len(args) == 0:
                for context_name in self.contexts:
                    channel(context_name)
            return

        @self.console_command("plugin", _("list loaded plugins in kernel"))
        def plugins(channel, _, args=tuple(), **kwargs):
            if len(args) == 0:
                plugins = self._kernel_plugins
                channel(_("Kernel Plugins:"))
                for name in plugins:
                    channel(
                        "{path}: {value}".format(path="kernel", value=name.__module__)
                    )
                channel(_("Service Plugins:"))
                for path in self._service_plugins:
                    plugins = self._service_plugins[path]
                    for name in plugins:
                        channel(
                            "{path}: {value}".format(
                                path=str(path), value=name.__module__
                            )
                        )
                channel(_("Module Plugins:"))
                for path in self._module_plugins:
                    plugins = self._module_plugins[path]
                    for name in plugins:
                        channel(
                            "{path}: {value}".format(
                                path=str(path), value=name.__module__
                            )
                        )
            return

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
                if self.lookup(index) is not None:
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

        # ==========
        # SERVICE COMMANDS
        # ==========

        @console_argument("domain")
        @self.console_command(
            "service",
            output_type="service",
            help=_("Base command to manipulate services"),
        )
        def service_base(channel, _, domain=None, remainder=None, **kwargs):
            if not remainder or domain is None:
                channel(_("----------"))
                channel(_("Service Providers:"))
                for i, name in enumerate(self.match("provider")):
                    channel("%d: %s" % (i + 1, name))
                channel(_("----------"))
                channel(_("Services:"))
                for i, value in enumerate(self.services_available()):
                    _domain, available = value
                    if domain is not None and domain != _domain:
                        continue
                    active = self.services(_domain, True)
                    for index, s in enumerate(available):
                        channel(
                            _("{active}{domain},{index}: {path} of {service}").format(
                                domain=_domain,
                                path=(str(s.path)),
                                service=str(s),
                                active="*" if s is active else " ",
                                index=index,
                            )
                        )
                return
            try:
                available = self.services(domain)
                active = self.services(domain, True)
            except KeyError:
                return None
            return "service", (domain, available, active)

        @console_argument("index", type=int, help="Index of service to activate.")
        @self.console_command(
            "activate",
            input_type="service",
            help=_("Activate the service at the given index"),
        )
        def service_activate(channel, _, data=None, index=None, **kwargs):
            domain, available, active = data
            if index is None:
                raise SyntaxError
            self.activate_service_index(domain, index)

        @console_argument("name", help="Name of service to start")
        @console_option("path", "p", help="optional forced path initialize location")
        @console_option(
            "init",
            "i",
            type=bool,
            action="store_true",
            help="call extended initialize for this service",
        )
        @self.console_command(
            "start", input_type="service", help=_("Initialize a provider")
        )
        def service_init(
            channel, _, data=None, name=None, path=None, init=None, **kwargs
        ):
            domain, available, active = data
            if name is None:
                raise SyntaxError
            provider_path = "provider/{domain}/{name}".format(domain=domain, name=name)
            provider = self.lookup(provider_path)
            if provider is None:
                raise SyntaxError("Bad provider.")
            if path is None:
                path = name

            service_path = path
            i = 1
            while service_path in self.contexts:
                service_path = path + str(i)
                i += 1

            service = provider(self, service_path)
            self.add_service(domain, service, provider_path)
            if init is True:
                self.activate(domain, service, assigned=True)

        # ==========
        # BATCH COMMANDS
        # ==========
        @self.console_command(
            "batch",
            output_type="batch",
            help=_("Base command to manipulate batch commands."),
        )
        def batch_base(channel, _, remainder=None, **kwargs):
            root = self.root
            batch = [b for b in root.setting(str, "batch", "").split(";") if b]
            if not remainder:
                channel(_("----------"))
                channel(_("Batch Commands:"))
                for i, name in enumerate(batch):
                    find = name.find(" ")
                    origin = name[:find]
                    text = name[find + 1 :]
                    if text:
                        channel("%d - %s: %s" % (i + 1, origin, text))
                channel(_("----------"))
            return "batch", batch

        @console_option(
            "origin",
            "o",
            type=str,
            help="flag added batch command with a specific origin",
        )
        @console_option("index", "i", type=int, help="insert position for add")
        @self.console_command(
            "add", input_type="batch", help=_("add a batch command 'batch add <line>'")
        )
        def batch_add(
            channel, _, data=None, index=None, origin="cmd", remainder=None, **kwargs
        ):
            if remainder is None:
                raise SyntaxError
            self.batch_add(remainder, origin, index)

        @console_argument("index", type=int, help="line to delete")
        @self.console_command(
            "remove",
            input_type="batch",
            help=_("delete line located at specific index'"),
        )
        def batch_remove(channel, _, data=None, index=None, **kwargs):
            if index is None:
                raise SyntaxError
            try:
                self.batch_remove(index - 1)
            except IndexError:
                raise SyntaxError(
                    "Index out of bounds (1-{length})".format(length=len(data))
                )

        # ==========
        # CHANNEL COMMANDS
        # ==========

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

        # ==========
        # SETTINGS
        # ==========

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

        # ==========
        # LIFECYCLE
        # ==========

        @self.console_command(
            ("quit", "shutdown"), help=_("shuts down all processes and exits")
        )
        def shutdown(**kwargs):
            if self.state not in (STATE_END, STATE_TERMINATE):
                self.set_kernel_lifecycle(self, LIFECYCLE_SHUTDOWN)

        # ==========
        # FILE MANAGER
        # ==========

        @self.console_command(("ls", "dir"), help=_("list directory"))
        def ls(channel, **kwargs):
            import os

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
            elements = self.root.elements
            try:
                elements.load(new_file)
            except AttributeError:
                raise SyntaxError(_("Loading files was not defined"))
            channel(_("loading..."))
            return "file", new_file

        # ==========
        # DEPRECATED KERNEL COMMANDS
        # ==========

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

    def batch_add(self, command, origin="default", index=None):
        root = self.root
        batch = [b for b in root.setting(str, "batch", "").split(";") if b]
        batch_command = "{origin} {command}".format(origin=origin, command=command)
        if index is not None:
            batch.insert(index, batch_command)
        else:
            batch.append(batch_command)
        self.root.batch = ";".join(batch)

    def batch_remove(self, index):
        root = self.root
        batch = [b for b in root.setting(str, "batch", "").split(";") if b]
        del batch[index]
        self.root.batch = ";".join(batch)

    def batch_boot(self):
        root = self.root
        if root.setting(str, "batch", None) is None:
            return
        for b in root.batch.split(";"):
            if b:
                find = b.find(" ")
                text = b[find + 1 :]
                root("{batch}\n".format(batch=text))


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

    def __repr__(self):
        return "Channel(%s, buffer_size=%s, line_end=%s)" % (
            repr(self.name),
            str(self.buffer_size),
            repr(self.line_end),
        )

    def __call__(
        self, message: Union[str, bytes, bytearray], *args,
        indent: Optional[bool]=True, **kwargs
    ):
        original_msg = message
        if self.line_end is not None:
            message = message + self.line_end
        if indent and not isinstance(message, (bytes, bytearray)):
            message = "    " + message.replace("\n", "\n    ")
        if self.timestamp and not isinstance(message, (bytes, bytearray)):
            ts = datetime.datetime.now().strftime("[%H:%M:%S] ")
            message = ts + message.replace("\n", "\n%s" % ts)
        for w in self.watchers:
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
            for line in self.buffer:
                monitor_function(line)

    def unwatch(self, monitor_function: Callable):
        self.watchers.remove(monitor_function)


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
        self._remaining = self.times

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

    def reset(self) -> None:
        self._last_run = None
        self._next_run = time.time() + self.interval
        self._remaining = self.times

    def cancel(self) -> None:
        self._remaining = -1


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
    import platform

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


def console_argument(name: str, **kwargs) -> Callable:
    def decor(func):
        kwargs["name"] = name
        if "type" not in kwargs:
            kwargs["type"] = str
        func.arguments.insert(0, kwargs)
        return func

    return decor


def console_command(
    registration,
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

    @param registration: the kernel or service this is being registered to
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
            for kind, value, start, pos in _cmd_parser(remainder):
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
                    kwargs[key].append(value)

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
                registration.register(p, inner)
        return inner

    return decorator


def console_command_remove(
    registration,
    path: Union[str, Tuple[str, ...]] = None,
    input_type: Union[str, Tuple[str, ...]] = None,
):
    """
    Removes a console command with the given input_type at the given path.

    @param registration: the kernel or service this is being registered to
    @param path: path or tuple of paths to delete.
    @param input_type: type or tuple of types to delete
    @return:
    """
    cmds = path if isinstance(path, tuple) else (path,)
    ins = input_type if isinstance(input_type, tuple) else (input_type,)
    for cmd in cmds:
        for i in ins:
            p = "command/%s/%s" % (i, cmd)
            registration.unregister(p)


def _cmd_parser(text: str) -> Generator[Tuple[str, str, int, int], None, None]:
    """
    Parser for console command events.
    @param text:
    @return:
    """
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
                yield kind, letter, start, start + 1
                start += 1


def lookup_listener(param):
    """
    Flags a method as a lookup_listener. This method will be updated on the changes to find values dynamically.
    @param param:
    @return:
    """

    def decor(func):
        if not hasattr(func, "lookup_decor"):
            func.lookup_decor = [param]
        else:
            func.lookup_decor.append(param)
        return func

    return decor


def signal_listener(param):
    """
    Flags a method as a signal_listener. This will listened when the module is opened.
    @param param:
    @return:
    """

    def decor(func):
        if not hasattr(func, "signal_listener"):
            func.signal_listener = [param]
        else:
            func.signal_listener.append(param)
        return func

    return decor
