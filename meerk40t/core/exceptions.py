# Define meerk40t specific exceptions

# Base meerk40t exceptions
class Mk40tError(Exception):
    pass


class Mk40tImportAbort(ImportError, Mk40tError):
    """
    MkImportAbort should be used as follows in plugins that import an optional prerequisite Pypi package:

    try:
        import wx
    except ImportError as e:
        raise Mk40tImportAbort("wx") from e
    """

class CommandMatchRejected(Mk40tError):
    """
    Exception to be raised by a registered console command if the match to the command was erroneous
    """

class MalformedCommandRegistration(Mk40tError):
    """
    Exception raised by the Kernel if the registration of the console command is malformed.
    """
