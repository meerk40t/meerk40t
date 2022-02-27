from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple, Union

from meerk40t.kernel.context import Context
from meerk40t.kernel.lifecycles import *

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
    registered in a deactivate service cannot be executed from the console, only the activated service's command is
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

    def console_command(self, *args, **kwargs) -> Callable:
        """
        Service console command registration.

        Uses the current registration to register the given command.
        """
        return self._kernel.console_command(*args, **kwargs)

    def console_command_remove(self, *args, **kwargs) -> None:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_command being removed.
        """
        self._kernel.console_command_remove(*args, **kwargs)

    def destroy(self):
        self.kernel.set_service_lifecycle(self, LIFECYCLE_SERVICE_SHUTDOWN)
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
        self.kernel.register_choices(sheet, choices)

    def add_service_delegate(self, delegate):
        self.kernel.add_delegate(delegate, self)
