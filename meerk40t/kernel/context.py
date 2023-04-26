from typing import Any, Callable, Dict, Generator, Optional, Tuple, Union

from .jobs import ConsoleFunction
from .lifecycles import *


class Context:
    """
    Contexts serve as path-relevant snapshots of the kernel. These are the primary interaction between the modules
    and the kernel. They permit getting other contexts of the kernel. This should serve as the primary interface
    code between the kernel and the modules.

    Contexts store the persistent settings and settings from at their path locations.

    Contexts have attribute settings located at .<setting> and so long as this setting does not begin with _ it will be
    reloaded when .setting() is called for the given attribute. This should be called by code that intends access
    an attribute even if it was already called.
    """

    def __init__(self, kernel: "Kernel", path: str):
        self._kernel = kernel
        self._path = path
        self._state = "unknown"
        self.opened = {}

    def __repr__(self):
        return f"Context('{self._path}')"

    def __call__(self, data: str, **kwargs):
        if len(data) and data[-1] != "\n":
            data += "\n"
        return self._kernel.console(data)

    # ==========
    # PATH INFORMATION
    # ==========

    def abs_path(self, subpath: str) -> str:
        """
        The absolute path function determines the absolute path of the given subpath within the current path of the
        context.

        @param subpath: relative path to the path at this context
        @return:
        """
        subpath = str(subpath)
        if subpath.startswith("/"):
            return subpath[1:]
        if self._path is None or self._path == "/":
            return subpath
        return f"{self._path}/{subpath}"

    def derive(self, path: str) -> "Context":
        """
        Derive a subpath context.

        @param path:
        @return:
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

        @param path: path location to get a context.
        @return:
        """
        return self._kernel.get_context(path)

    def derivable(self) -> Generator[str, None, None]:
        """
        Generate all sub derived paths.

        @return:
        """
        yield from self._kernel.derivable(self._path)

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

        @param setting_type: int, float, str, bool, list or tuple value
        @param key: name of the setting
        @param default: default value for the setting to have.
        @return: load_value
        """
        if hasattr(self, key) and getattr(self, key) is not None:
            return getattr(self, key)

        # Key is not located in the attr. Load the value.
        if not key.startswith("_"):
            load_value = self._kernel.read_persistent(
                setting_type, self._path, key, default
            )
        else:
            load_value = default
        if load_value is not None and not isinstance(load_value, setting_type):
            load_value = setting_type(load_value)
        setattr(self, key, load_value)
        return load_value

    def flush(self) -> None:
        """
        Commit any and all values currently stored as attr for this object to persistent storage.
        """
        self._kernel.write_persistent_attributes(self._path, self)

    def write_persistent_attributes(self, obj: Any) -> None:
        """
        Writes values of the object's attributes at this context
        @param obj:
        @return:
        """
        self._kernel.write_persistent_attributes(self._path, obj)

    def read_persistent(self, t: type, key: str) -> Any:
        """
        Gets a specific value of the persistent attributes.

        The attribute type of the value depends on the provided object value default values.

        @param t: type of value
        @param key: relative key for the value
        @return: the value associated with the key otherwise None
        """
        return self._kernel.read_persistent(t, self._path, key)

    def read_persistent_attributes(self, obj: Any) -> None:
        """
        Loads values of the persistent attributes, at this context and assigns them to the provided object.

        The attribute type of the value depends on the provided object value default values.

        @param obj:
        @return:
        """
        self._kernel.read_persistent_attributes(self._path, obj)

    def read_persistent_string_dict(
        self, dictionary: Optional[Dict] = None, suffix: bool = False
    ) -> Dict:
        """
        Delegate to kernel to get a local string of dictionary values.

        @param dictionary: optional dictionary to be updated with values
        @param suffix:
        @return:
        """
        return self._kernel.read_persistent_string_dict(
            self._path, dictionary=dictionary, suffix=suffix
        )

    def clear_persistent(self) -> None:
        """
        Delegate to Kernel to clear the persistent settings located at this context.
        """
        self._kernel.clear_persistent(self._path)

    def write_persistent(
        self, key: str, value: Union[int, float, str, bool, list, tuple]
    ) -> None:
        """
        Delegate to Kernel to write the given key at this context to persistent settings. This is typically done during
        shutdown but there are a variety of reasons to force this call early.

        If the persistence object is not yet established this function cannot succeed.
        """
        self._kernel.write_persistent(self._path, key, value)

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

    def console_argument(self, *args, **kwargs) -> Callable:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_argument being registered.
        """
        return self._kernel.console_argument(*args, **kwargs)

    def console_option(self, *args, **kwargs) -> Callable:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_option being registered.
        """
        return self._kernel.console_option(*args, **kwargs)

    def console_command(self, *args, **kwargs) -> Callable:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_command being registered.
        """
        return self._kernel.console_command(*args, **kwargs)

    def console_command_remove(self, *args, **kwargs) -> Callable:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_command being removed.
        """
        return self._kernel.console_command_remove(*args, **kwargs)

    @property
    def contexts(self) -> Dict[str, "Context"]:
        return self._kernel.contexts

    def has_feature(self, feature: str) -> bool:
        """
        Return whether this is a registered feature within the kernel.

        @param feature: feature to check if exists in kernel.
        @return:
        """
        return self.lookup(feature) is not None

    def find(self, *args):
        """
        Delegate of Kernel match.

        @param args:  arguments to be delegated
        :yield: matched entries.
        """
        yield from self._kernel.find(*args)

    def match(self, matchtext: str, suffix: bool = False) -> Generator[str, None, None]:
        """
        Delegate of Kernel match.

        @param matchtext:  regex matchtext to locate.
        @param suffix: provide the suffix of the match only.
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

        This is often unneeded if the job completes on its own, it will be removed from the scheduler.
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

        Registered threads must complete before shutdown can be completed. These will be told to stop and waited on until
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

        @param path: The opened path to find the given instance.
        @return: The instance, if found, otherwise None.
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

        @param registered_path: registered path of the given module.
        @param args: args to open the module with.
        @param kwargs: kwargs to open the module with.
        @return:
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

        @param registered_path: path of object being opened.
        @param instance_path: instance_path of object.
        @param args: Args to pass to newly opened module.
        @param kwargs: Kwargs to pass to newly opened module.
        @return: Opened module.
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
        self._module_delegate(instance)

        # Call module_open lifecycle event.
        self.kernel.set_module_lifecycle(instance, LIFECYCLE_MODULE_OPENED)

        return instance

    def _module_delegate(self, module, model=None, add=True):
        """
        Recursively find any delegates for a module yielded under `.delegate()`
        @param module:
        @param model:
        @param add:
        @return:
        """
        kernel = self.kernel
        if model is None:
            model = module

        try:
            if model is not module:
                # We are the model we don't delegate to it.
                if add:
                    kernel.add_delegate(model, module)
                else:
                    kernel.remove_delegate(model, module)
            for delegate in model.delegates():
                self._module_delegate(module=module, model=delegate, add=add)
        except AttributeError:
            pass

    def close(self, instance_path: str, *args, **kwargs) -> None:
        """
        Closes an opened module instance. Located at the instance_path location.

        This calls the close() function on the object (which may not exist). Then calls module_close() on the module,
        which should exist.

        @param instance_path: Instance path to close.
        @return:
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

        @param code: Code to delegate at this given context location.
        @param message: Message to send.
        @return:
        """
        self._kernel.signal(code, self._path, *message)

    def last_signal(self, signal: str) -> Tuple:
        """
        Returns the last signal payload at the given code.

        @param signal: Code to delegate at this given context location.
        @return: message value of the last signal sent for that code.
        """
        return self._kernel.last_signal(signal)

    def listen(
        self,
        signal: str,
        process: Callable,
        lifecycle_object: Union["Service", "Module", None] = None,
    ) -> None:
        """
        Listen at a particular signal with a given process.

        @param signal: Signal code to listen for
        @param process: listener to be attached
        @param lifecycle_object: Object to use as a cookie to bind the listener.
        @return:
        """
        self._kernel.listen(signal, process, lifecycle_object)

    def unlisten(self, signal: str, process: Callable):
        """
        Unlisten to a particular signal with a given process.

        This should be called on the ending of the lifecycle of whatever process listened to the given signal.

        @param signal: Signal to unlisten for.
        @param process: listener that is to be detached.
        @return:
        """
        self._kernel.unlisten(signal, process)

    # ==========
    # CHANNEL DELEGATES
    # ==========

    def channel(self, channel: str, *args, **kwargs) -> "Channel":
        """
        Return a channel from the kernel location

        @param channel: Channel to be opened.
        @return: Channel object that is opened.
        """
        return self._kernel.channel(channel, *args, **kwargs)

    def console_function(self, data: str) -> "ConsoleFunction":
        """
        Returns a function that calls a console command. This serves as a Job to be used in Scheduler or simply a
        function with the command as the str form.
        """
        return ConsoleFunction(self, data)
