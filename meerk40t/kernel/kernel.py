import functools
import inspect
import os
import platform
import re
import threading
import time
from datetime import datetime
from threading import Thread
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple, Union

from .channel import Channel
from .context import Context
from .exceptions import CommandMatchRejected, CommandSyntaxError
from .functions import (
    console_argument,
    console_command,
    console_command_remove,
    console_option,
    get_safe_path,
)
from .jobs import ConsoleFunction, Job
from .lifecycles import *
from .module import Module
from .service import Service
from .settings import Settings
from .states import *

KERNEL_VERSION = "0.0.1"

RE_ACTIVE = re.compile("service/(.*)/active")
RE_AVAILABLE = re.compile("service/(.*)/available")


class Kernel(Settings):
    """
    The Kernel serves as the central hub of communication between different objects within the system, stores the
    main lookup of registered objects, as well as providing a scheduler, signals, channels, and a command console to be
    used within the system.

    The Kernel stores a persistence object, thread interactions, contexts, a translation routine, a run_later operation,
    jobs for the scheduler, listeners for signals, channel information, a list of devices, registered commands.
    """

    def __init__(self, name: str, version: str, profile: str):
        """
        Initialize the Kernel. This sets core attributes of the ecosystem that are accessible to all modules.

        Name: The application name.
        Version: The version number of the application.
        Profile: The name to save our data under (this is often the same as app name).
        """
        self.name = name
        self.profile = profile
        self.version = version

        # Persistent Settings
        Settings.__init__(
            self,
            self.name,
            "{profile}.cfg".format(name=name, profile=profile, version=version),
        )
        self.settings = self

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
        self.thread_lock = threading.Lock()

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
        self._lookup_lock = threading.Lock()

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
        self._signal_lock = threading.Lock()
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
        self.console_channel_file = None

        self.current_directory = "."

        # Arguments Objects
        self.args = None

    def __str__(self):
        return "Kernel()"

    def open_safe(self, *args):
        try:
            return open(*args)
        except PermissionError:
            original = os.getcwd()
            os.chdir(get_safe_path(self.name, True))
            print(
                "Changing working directory from %s to %s."
                % (str(original), str(os.getcwd()))
            )
            return open(*args)

    def _start_debugging(self) -> None:
        """
        Debug function hooks all functions within the device with a debug call that saves the data to the disk and
        prints that information.

        @return:
        """
        import types

        filename = "{name}-debug-{date:%Y-%m-%d_%H_%M_%S}.txt".format(
            name=self.name, date=datetime.now()
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

        @param plugin:
        @return:
        """
        additional_plugins = plugin(self, "plugins")
        if additional_plugins is not None:
            for p in additional_plugins:
                self.add_plugin(p)
        plugins = self._kernel_plugins
        service_path = plugin(self, "service")
        if service_path is not None:
            if service_path not in self._service_plugins:
                self._service_plugins[service_path] = list()
            plugins = self._service_plugins[service_path]
        else:
            module_path = plugin(self, "module")
            if module_path is not None:
                if module_path not in self._module_plugins:
                    self._module_plugins[module_path] = list()
                plugins = self._module_plugins[module_path]

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
        for r in list(self._registered):
            result = RE_ACTIVE.match(r)
            if result:
                yield result.group(1), self._registered[r]

    def services_available(self):
        """
        Generate a series of available services.

        @return: domain, service
        """
        for r in list(self._registered):
            result = RE_AVAILABLE.match(r)
            if result:
                yield result.group(1), self._registered[r]

    def remove_service(self, service: Service):
        self.set_service_lifecycle(service, LIFECYCLE_KERNEL_SHUTDOWN)
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
        @param activate: Should this service be activated upon addition
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

        @param domain: Domain to add service at
        @param path: Path to this service locally
        @param assigned: Should this service be assigned when activated
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
        @param assigned: Should this service be assigned when activated
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
        @param assigned: Should this service be assigned when activated
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
            if klp(k) < LIFECYCLE_KERNEL_PRECLI <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_PRECLI
                if channel:
                    channel("kernel-precli: {object}".format(object=str(k)))
                if hasattr(k, "precli"):
                    k.precli()
        if start < LIFECYCLE_KERNEL_PRECLI <= end:
            if channel:
                channel("(plugin) kernel-precli")
            for plugin in self._kernel_plugins:
                plugin(kernel, "precli")

        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_CLI <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_CLI
                if channel:
                    channel("kernel-cli: {object}".format(object=str(k)))
                if hasattr(k, "cli"):
                    k.cli()
        if start < LIFECYCLE_KERNEL_CLI <= end:
            if channel:
                channel("(plugin) kernel-cli")
            for plugin in self._kernel_plugins:
                plugin(kernel, "cli")

        objects = self.get_linked_objects(kernel)
        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_INVALIDATE <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_INVALIDATE
                if channel:
                    channel("kernel-invalidate: {object}".format(object=str(k)))
                if hasattr(k, "invalidate"):
                    k.invalidate()
        if start < LIFECYCLE_KERNEL_INVALIDATE <= end:
            if channel:
                channel("(plugin) kernel-invalidate")
            plugin_list = self._kernel_plugins
            for i in range(len(plugin_list) - 1, -1, -1):
                plugin = plugin_list[i]
                if plugin(kernel, "invalidate"):
                    del plugin_list[i]
            for domain in self._service_plugins:
                plugin_list = self._service_plugins[domain]
                for i in range(len(plugin_list) - 1, -1, -1):
                    plugin = plugin_list[i]
                    if plugin(kernel, "invalidate"):
                        del plugin_list[i]
            for module_path in self._module_plugins:
                plugin_list = self._module_plugins[module_path]
                for i in range(len(plugin_list) - 1, -1, -1):
                    plugin = plugin_list[i]
                    if plugin(kernel, "invalidate"):
                        del plugin_list[i]

        objects = self.get_linked_objects(kernel)
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
            if klp(k) < LIFECYCLE_KERNEL_READY <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_READY
                if channel:
                    channel("kernel-ready: {object}".format(object=str(k)))
                if hasattr(k, "ready"):
                    k.ready()
        if start < LIFECYCLE_KERNEL_READY <= end:
            if channel:
                channel("(plugin) kernel-ready")
            for plugin in self._kernel_plugins:
                plugin(kernel, "ready")

        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_FINISHED <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_FINISHED
                if channel:
                    channel("kernel-finished: {object}".format(object=str(k)))
                if hasattr(k, "finished"):
                    k.finished()
        if start < LIFECYCLE_KERNEL_FINISHED <= end:
            if channel:
                channel("(plugin) kernel-finished")
            for plugin in self._kernel_plugins:
                plugin(kernel, "finished")

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

        if start < LIFECYCLE_KERNEL_SHUTDOWN <= end:
            if channel:
                channel("(plugin) kernel-shutdown")
            for plugin in self._kernel_plugins:
                plugin(kernel, "shutdown")
        for k in objects:
            if klp(k) < LIFECYCLE_KERNEL_SHUTDOWN <= end:
                k._kernel_lifecycle = LIFECYCLE_KERNEL_SHUTDOWN
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
            if slp(s) < LIFECYCLE_KERNEL_SHUTDOWN <= end:
                s._service_lifecycle = LIFECYCLE_KERNEL_SHUTDOWN
                if channel:
                    channel("service-shutdown: {object}".format(object=str(s)))
                if hasattr(s, "shutdown"):
                    s.shutdown(*args, **kwargs)

        # Update plugin: shutdown
        if start < LIFECYCLE_KERNEL_SHUTDOWN <= end:
            if channel:
                channel(
                    "(plugin) service-shutdown: {object}".format(object=str(service))
                )
            start = LIFECYCLE_KERNEL_SHUTDOWN
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
            if mlp(m) < LIFECYCLE_KERNEL_SHUTDOWN <= end:
                m._module_lifecycle = LIFECYCLE_KERNEL_SHUTDOWN
                if channel:
                    channel("module-shutdown: {object}".format(object=str(m)))
                if hasattr(m, "shutdown"):
                    m.shutdown()

        # Update plugin: shutdown
        if start < LIFECYCLE_KERNEL_SHUTDOWN <= end:
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

    def __print_delegate(self, *args, **kwargs):
        if print not in self._console_channel.watchers:
            print(*args, **kwargs)

    def __call__(self):
        self.set_kernel_lifecycle(self, LIFECYCLE_KERNEL_MAINLOOP)

    def precli(self):
        pass

    def cli(self):
        pass

    def preboot(self):
        self.command_boot()
        self.choices_boot()

    def boot(self) -> None:
        """
        Kernel boot sequence. This should be called after all the registered devices are established.

        @return:
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
            self.channel("console").watch(self.__print_delegate)
            for v in self.args.execute:
                if v is None:
                    continue
                self.console(v.strip() + "\n")
            self.channel("console").unwatch(self.__print_delegate)

        if hasattr(self.args, "batch") and self.args.batch:
            # If a batch file is specified it gets processed here.
            self.channel("console").watch(self.__print_delegate)
            with self.args.batch as batch:
                for line in batch:
                    self.console(line.strip() + "\n")
            self.channel("console").unwatch(self.__print_delegate)

    def premain(self):
        if hasattr(self.args, "console") and self.args.console:
            self.channel("console").watch(self.__print_delegate)
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
            self.channel("console").unwatch(self.__print_delegate)

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
                    LIFECYCLE_KERNEL_SHUTDOWN,
                    None,
                    opened_name,
                    channel=channel,
                    shutdown=True,
                )

        for domain, services in self.services_available():
            for service in list(services):
                self.set_service_lifecycle(service, LIFECYCLE_KERNEL_SHUTDOWN)

    def shutdown(self):
        """
        Starts shutdown procedure.

        Suspends all signals.
        Each initialized context is flushed and shutdown.
        Each opened module within the context is stopped and closed.

        All threads are stopped.

        Any residual attached listeners are made warnings.

        @return:
        """
        channel = self.channel("shutdown")
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
        self.write_configuration()
        try:
            del self._config_dict
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

        @param args: parts of matchtext
        @return:
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

        @param matchtext: match text to match.
        @param suffix: provide the suffix of the match only.
        @return:
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

    def has_feature(self, *args):
        for a in args:
            try:
                v = self._registered["feature/{feature}".format(feature=a)]
            except KeyError:
                return False
            if not v:
                return False
        return True

    def set_feature(self, feature):
        self._registered["feature/{feature}".format(feature=feature)] = True

    def lookup_all(self, *args):
        """
        Lookup registered values from the registered dictionary checking the active devices first.

        @param args: parts of matchtext
        @return:
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
            # Handle is excluded. triggers a knock-on effect bug in wxPython GTK systems.
            if attr == "Handle":
                continue
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

        @param path: a "/" separated hierarchical index to the object
        @param obj: object to be registered
        @return:
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
    # PATH & CONTEXTS
    # ==========

    @property
    def root(self) -> "Context":
        return self.get_context("/")

    def register_as_context(self, context):
        # If context get after boot, apply all services.
        for domain, service in self.services_active():
            setattr(context, domain, service)
        self.contexts[context.path] = context

    def get_context(self, path: str) -> "Context":
        """
        Create a context derived from this kernel, at the given path.

        If this has been created previously, then return the previous object.

        @param path: path of context being gotten
        @return: Context object.
        """
        try:
            return self.contexts[path]
        except KeyError:
            pass
        derive = Context(self, path=path)
        self.register_as_context(derive)
        return derive

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

        @param func: The function to be executed.
        @param thread_name: The name under which the thread should be registered.
        @param result: Runs in the thread after func terminates but before the thread itself terminates.
        @param daemon: set this thread as daemon
        @return: The thread object created.
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
        @return:
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

        @param run: function to run
        @param name: Specific job name to add
        @param args: arguments to give to that function.
        @param interval: in seconds, how often should the job be run.
        @param times: limit on number of executions.
        @param run_main: Should this run in the main thread (as registered by kernel.run_later)
        @param conditional: Should execute only if the given additional conditional is true. (checked outside run_main)
        @return: Reference to the job added.
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

        @param code: Signal code
        @param path: Path of signal
        @param message: Message to send.
        """
        self._signal_lock.acquire(True)
        self._message_queue[code] = path, message
        self._signal_lock.release()

    def process_queue(self, *args) -> None:
        """
        Performed in the run_later thread. Signal groups. Threadsafe.

        Process the signals queued up. Inserting any attaching listeners, removing any removing listeners. And
        providing the newly attached listeners the last message known from that signal.
        @param args: None
        @return:
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
            for signal, funct, lso in add:
                if signal in self.listeners:
                    listeners = self.listeners[signal]
                    listeners.append((funct, lso))
                else:
                    self.listeners[signal] = [(funct, lso)]
                if signal in self._last_message:
                    origin, message = self._last_message[signal]
                    funct(origin, *message)

        # Process any removing listeners.
        if remove is not None:
            for signal, remove_funct, remove_lso in remove:
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
            origin, message = payload
            if signal in self.listeners:
                listeners = self.listeners[signal]
                for listener, listen_lso in listeners:
                    listener(origin, *message)
                    if signal_channel:
                        signal_channel(
                            "Signal: %s %s: %s:%s%s"
                            % (
                                origin,
                                signal,
                                listener.__module__,
                                listener.__name__,
                                str(message),
                            )
                        )
            self._last_message[signal] = payload
        self._is_queue_processing = False

    def last_signal(self, signal: str) -> Optional[Tuple]:
        """
        Queries the last signal for a particular signal/path

        @param signal: signal to query.
        @return: Last signal sent through the kernel for that signal and path
        """
        try:
            return self._last_message[signal]
        except KeyError:
            return None, None

    def listen(
        self,
        signal: str,
        funct: Callable,
        lifecycle_object: Any = None,
    ) -> None:
        """
        Attaches callable to a particular signal. This will be attached next time the signals are processed.

        @param signal:
        @param funct:
        @param lifecycle_object:
        @return:
        """
        self._signal_lock.acquire(True)
        self._adding_listeners.append((signal, funct, lifecycle_object))
        self._signal_lock.release()

    def unlisten(
        self,
        signal: str,
        funct: Callable,
        lifecycle_object: Any = None,
    ) -> None:
        """
        Removes callable listener for a given signal. This will be detached next time the signals code runs.

        @param signal:
        @param funct:
        @param lifecycle_object:
        @return:
        """
        self._signal_lock.acquire(True)
        self._removing_listeners.append((signal, funct, lifecycle_object))
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
            # Handle is excluded. triggers a knock-on effect bug in wxPython GTK systems.
            if attr == "Handle":
                continue
                # TODO: exclude properties.
            func = getattr(scan_object, attr)
            if hasattr(func, "signal_listener"):
                for sl in func.signal_listener:
                    self.listen(sl, func, cookie)

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
                    self._removing_listeners.append((signal, listener, cookie))

        self._signal_lock.release()

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

        @param data:
        @return:
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

        @return:
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
            channel("[blue][bold][raw]%s[/raw]" % text, indent=False)

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
                except CommandSyntaxError as e:
                    # If command function raises a syntax error, we abort the rest of the command.

                    # ToDo
                    # Don't use command help, which is or should be descriptive - use command syntax instead
                    # If CommandSyntaxError has a msg then that needs to be provided AS WELL as the syntax.
                    message = command_funct.help
                    if e.msg:
                        message = e.msg
                    channel(
                        "[red][bold]" + _("Syntax Error (%s): %s") % (command, message)
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
                    % (command, ctx_name)
                )
                return None
        return data

    # ==========
    # CHOICES REGISTRATION
    # ==========

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
                raise CommandSyntaxError
            if duration is None:
                raise CommandSyntaxError
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

        @self.console_command("version", _("System Information"))
        def version(channel, _, **kwargs):
            channel(_("MK Kernel {version}.").format(version=KERNEL_VERSION))
            channel(
                _("App: {name} {version}.").format(name=self.name, version=self.version)
            )

        def beep(channel, _, **kwargs):
            OS_NAME = platform.system()
            if OS_NAME == "Windows":
                try:
                    import winsound

                    for x in range(5):
                        winsound.Beep(2000, 100)
                except Exception:
                    pass
            elif OS_NAME == "Darwin":  # Mac

                os.system("afplay /System/Library/Sounds/Ping.aiff")
            else:  # Assuming other linux like system
                print("\a")  # Beep.

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
        def plugin(channel, _, args=tuple(), **kwargs):
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
            if len(args) == 0:
                return
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

        @self.console_argument("domain")
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

        @self.console_argument("index", type=int, help="Index of service to activate.")
        @self.console_command(
            "activate",
            input_type="service",
            help=_("Activate the service at the given index"),
        )
        def service_activate(channel, _, data=None, index=None, **kwargs):
            domain, available, active = data
            if index is None:
                raise CommandSyntaxError
            self.activate_service_index(domain, index)

        @self.console_argument("name", help="Name of service to start")
        @self.console_option(
            "path", "p", help="optional forced path initialize location"
        )
        @self.console_option(
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
                raise CommandSyntaxError
            provider_path = "provider/{domain}/{name}".format(domain=domain, name=name)
            provider = self.lookup(provider_path)
            if provider is None:
                raise CommandSyntaxError("Bad provider.")
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

        @self.console_option(
            "origin",
            "o",
            type=str,
            help="flag added batch command with a specific origin",
        )
        @self.console_option("index", "i", type=int, help="insert position for add")
        @self.console_command(
            "add", input_type="batch", help=_("add a batch command 'batch add <line>'")
        )
        def batch_add(
            channel, _, data=None, index=None, origin="cmd", remainder=None, **kwargs
        ):
            if remainder is None:
                raise CommandSyntaxError
            self.batch_add(remainder, origin, index)

        @self.console_argument("index", type=int, help="line to delete")
        @self.console_command(
            "remove",
            input_type="batch",
            help=_("delete line located at specific index'"),
        )
        def batch_remove(channel, _, data=None, index=None, **kwargs):
            if index is None:
                raise CommandSyntaxError
            try:
                self.batch_remove(index - 1)
            except IndexError:
                raise CommandSyntaxError(
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
                raise CommandSyntaxError(_("channel_name is not specified."))

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
                raise CommandSyntaxError(_("channel_name is not specified."))

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
                raise CommandSyntaxError(_("channel_name is not specified."))

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
                raise CommandSyntaxError(_("channel_name is not specified."))

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

        @self.console_command("flush", help=_("flush current settings to disk"))
        def flush(channel, _, **kwargs):
            for context_name in list(self.contexts):
                context = self.contexts[context_name]
                context.flush()
            self.write_configuration()
            channel(_("Persistent settings force saved."))

        # ==========
        # LIFECYCLE
        # ==========

        @self.console_command(
            ("quit", "shutdown"), help=_("shuts down all processes and exits")
        )
        def shutdown(**kwargs):
            if self._shutdown:
                return
            self._shutdown = True
            self.set_kernel_lifecycle(self, LIFECYCLE_KERNEL_SHUTDOWN)

        # ==========
        # FILE MANAGER
        # ==========

        @self.console_command(("ls", "dir"), help=_("list directory"))
        def ls(channel, **kwargs):
            for f in os.listdir(self.current_directory):
                channel(str(f))

        @self.console_argument("directory")
        @self.console_command("cd", help=_("change directory"))
        def cd(channel, _, directory=None, **kwargs):
            if directory == "~":
                self.current_directory = "."
                channel(_("Working directory"))
                return
            if directory == "&":
                self.current_directory = os.path.dirname(self._config_file)
                channel(
                    _("Configuration Directory: {dir}").format(
                        dir=str(self.current_directory)
                    )
                )
                return
            if directory == "@":
                import sys

                if hasattr(sys, "_MEIPASS"):
                    # pylint: disable=no-member
                    self.current_directory = sys._MEIPASS
                    channel(_("Internal Directory"))
                    return
                else:
                    channel(_("No internal directory."))
                    return
            if directory is None:
                channel(os.path.abspath(self.current_directory))
                return
            new_dir = os.path.join(self.current_directory, directory)
            if not os.path.exists(new_dir):
                channel(_("No such directory."))
                return
            self.current_directory = new_dir
            channel(os.path.abspath(new_dir))

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
    # KERNEL REPLACEABLE
    # ==========

    def _text_prompt(self, data_type, prompt):
        """
        Kernel Prompt should be replaced with higher level versions of this depending on the user interface.

        Default this is purely text based input() prompt.

        @param data_type: type of data being prompted for.
        @param prompt: question asked of the user.
        @return:
        """
        try:
            value = input(prompt + "\n?")
            return data_type(value)
        except ValueError:
            return None

    # Prompt should be replaced with higher level versions of this depending on the user interface.
    prompt = _text_prompt

    # ==========
    # CONSOLE DECORATORS
    # ==========

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
        Delegate to Kernel

        Uses current context to be passed to the console_command being registered.
        """
        return console_command(self, *args, **kwargs)

    def console_command_remove(self, *args, **kwargs) -> Callable:
        """
        Delegate to Kernel

        Uses current context to be passed to the console_command being removed.
        """
        return console_command_remove(self, *args, **kwargs)


def lookup_listener(param):
    """
    Flags a method as a @lookup_listener. This method will be updated on the changes to the lookup. The lookup changes
    when values are registered in the lookup or during service activation.

    @param param: function being attached to
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
    Flags a method as a @signal_listener. This will listened when the module is opened.

    @param param: function being attached to
    @return:
    """

    def decor(func):
        if not hasattr(func, "signal_listener"):
            func.signal_listener = [param]
        else:
            func.signal_listener.append(param)
        return func

    return decor
