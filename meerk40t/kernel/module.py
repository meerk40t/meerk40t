class Module:
    """
    Modules are a generic lifecycle object. These are registered in the kernel as modules and when open() is called for
    a context. When close() is called on the context, it will close and delete references to the opened module and call
    module_close().

    If an opened module tries to open() a second time in a context with the same name, and was not closed, the
    restore() function is called for the module, with the same args and kwargs that would have been called on
    __init__().

    Multiple instances of a module can be opened but this requires a different initialization name.
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
        self.state = "init"

    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self.context)}, name="{self.name}")'

    def restore(self, *args, **kwargs):
        """Called with the same values of __init()__ on an attempt to reopen of a module with the same name at the
        same context."""
        pass

    def module_open(self, *args, **kwargs):
        """Initialize() is called after open() to set up the module and allow it to register various hooks into the
        kernelspace."""
        pass

    def module_close(self, *args, **kwargs):
        """Finalize is called after close() to unhook various kernelspace hooks. This will happen if kernel is being
        shutdown or if this individual module is being closed on its own."""
        pass

    def add_module_delegate(self, delegate):
        self.context.kernel.add_delegate(delegate, self)

    def remove_module_delegate(self, delegate):
        self.context.kernel.remove_delegate(delegate, self)
