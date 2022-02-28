
class CommandMatchRejected(Exception):
    """
    Exception to be raised by a registered console command if the match to the command was erroneous
    """


class MalformedCommandRegistration(Exception):
    """
    Exception raised by the Kernel if the registration of the console command is malformed.
    """
