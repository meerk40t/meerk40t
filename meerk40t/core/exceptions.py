class Meerk40tError(Exception):
    """
    This root Meerk40t exception is provided in case we ever want to provide common functionality
    across all Meerk40t exceptions.
    """


class BadFileError(Meerk40tError):
    """Abort loading a malformed file"""
