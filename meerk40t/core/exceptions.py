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


class BadFileError(Mk40tError):
    """Abort loading a malformed file"""
