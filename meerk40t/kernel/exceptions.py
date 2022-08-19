class KernelError(Exception):
    """
    This root Kernel exception is provided in case we ever want to provide common functionality
    across all Kernel exceptions.
    """


class KernelImportAbort(ImportError, KernelError):
    """
    KernelImportAbort should be used as follows in plugins that import an optional prerequisite Pypi package:

    try:
        import wx
    except ImportError as e:
        raise KernelImportAbort("wx") from e
    """


class CommandSyntaxError(KernelError):
    """
    Exception to be raised by a registered console command if the parameters provided are erroneous.

    An explanatory message can be provided when this exception is raised.
    """

    @property
    def msg(self):
        """Backwards compatibility with SyntaxError undocumented property."""
        return str(self)


class CommandMatchRejected(KernelError):
    """
    Exception to be raised by a registered console command if the match to the command was erroneous
    """


class MalformedCommandRegistration(KernelError):
    """
    Exception raised by the Kernel if the registration of the console command is malformed.
    """
