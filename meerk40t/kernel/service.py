from typing import Any, Callable

from .context import Context
from .functions import (
    console_argument,
    console_command,
    console_command_remove,
    console_option,
)
from .lifecycles import *


class Service(Context):
    """
    A service is a context that with additional capabilities. These get registered by a domain in the kernel as a
    particular aspect. For example, .device or .gui could be a service and this service would be found at that attribute
    at for any context. As a type of context, services have a path for saving settings. The path is the saving/loading
    location for persistent settings. As a service, these contexts may exist at .<domain> relative to any context.
    This also allows several services to be registered for the same domain. These are swapped with the activate_service
    commands in the kernel.

    Each service has its own registered lookup of data. This extends the lookup of the kernel but only for those
    services which are currently active. This extends to various data types that are registered in the kernel such
    as choices and console commands. The currently active service can modify these simply by being activated. A command
    registered in a deactivated service cannot be executed from the console, only the activated service's command is
    executed in that case.

    Unlike contexts which should be derived or gotten at a particular path. Services can be directly instanced.
    """

    def __init__(self, kernel: "Kernel", path: str, registered_path: str = None):
        super().__init__(kernel, path)
        kernel.register_as_context(self)
        self.registered_path = registered_path
        self._registered = {}

    def __str__(self):
        if hasattr(self, "label"):
            return self.label
        return f"Service('{self._path}', {self.registered_path})"

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

        @param path:
        @param obj:
        @return:
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

    def console_argument(self, *args, **kwargs) -> Callable:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_argument being registered.
        """
        return console_argument(*args, **kwargs)

    def console_option(self, *args, **kwargs) -> Callable:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_option being registered.
        """
        return console_option(*args, **kwargs)

    def console_command(self, *args, **kwargs) -> Callable:
        """
        Service console command registration.

        Uses the current registration to register the given command.
        """
        return console_command(self, *args, **kwargs)

    def console_command_remove(self, *args, **kwargs) -> None:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_command being removed.
        """
        return console_command_remove(self, *args, **kwargs)

    def destroy(self):
        self.kernel.set_service_lifecycle(self, LIFECYCLE_SERVICE_SHUTDOWN)
        self.clear_persistent()
        self.close_subpaths()

    def register_choices(self, sheet, choices):
        """
        Registers choices to a given sheet. If the sheet already exists then the new choices
        are appended to the given sheet.

        If these choices are registered to an object of Context type we then set the given
        default values.

        Service register choices command registration.

        Uses the current registration to register the choices.
        @param sheet: Name of choices being registered
        @param choices: list of choices
        @return:
        """
        key = f"choices/{sheet}"
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

    def add_service_delegate(self, delegate):
        self.kernel.add_delegate(delegate, self)
