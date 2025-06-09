import functools
import os
import os.path
import platform
import re
from math import isinf
from typing import Callable, Generator, List, Optional, Tuple, Union

from .exceptions import CommandSyntaxError, MalformedCommandRegistration

_cmd_parse = [
    ("OPT", r"-([a-zA-Z]+)"),
    ("LONG", r"--([^ ,\t\n\x09\x0A\x0C\x0D]+)"),
    ("QPARAM", r"\"(.*?)\""),
    ("PARAM", r"([^ ,\t\n\x09\x0A\x0C\x0D]+)"),
    ("SKIP", r"[ ,\t\n\x09\x0A\x0C\x0D]+"),
]
_CMD_RE = re.compile("|".join("(?P<%s>%s)" % pair for pair in _cmd_parse))


def get_safe_path(
    name: str, create: Optional[bool] = False, system: Optional[str] = None
) -> str:
    """
    Get a path which should have valid user permissions in an OS dependent method.

    @param name: directory name within the safe OS dependent userdirectory
    @param create: Should this directory be created if needed.
    @param system: Override the system value determination
    @return:
    """
    if not system:
        system = platform.system()

    if system == "Darwin":
        directory = os.path.join(
            os.path.expanduser("~"),
            "Library",
            "Application Support",
            name,
        )
    elif system == "Windows":
        directory = os.path.join(os.path.expandvars("%LOCALAPPDATA%"), name)
    else:
        directory = os.path.join(os.path.expanduser("~"), ".config", name)
    if directory is not None and create:
        os.makedirs(directory, exist_ok=True)
    return directory


def console_option(name: str, short: str = None, **kwargs) -> Callable:
    """
    Adds an option for a console_command.

    @param name: option name
    @param short: short flag of option name.
    @param kwargs:
    @return:
    """
    try:
        if short.startswith("-"):
            short = short[1:]
    except Exception:
        pass

    def decor(func):
        kwargs["name"] = name
        kwargs["short"] = short
        if "action" in kwargs:
            kwargs["type"] = bool
        elif "type" not in kwargs:
            kwargs["type"] = str
        func.options.insert(0, kwargs)
        return func

    return decor


def console_argument(name: str, **kwargs) -> Callable:
    """
    Adds an argument for the console_command. These are non-optional values and are expected to be provided when the
    command is called from console.

    @param name:
    @param kwargs:
    @return:
    """

    def decor(func):
        kwargs["name"] = name
        if "type" not in kwargs:
            kwargs["type"] = str
        func.arguments.insert(0, kwargs)
        return func

    return decor


def console_command(
    registration,
    path: Union[str, Tuple[str, ...]] = None,
    regex: bool = False,
    hidden: bool = False,
    help: str = None,
    input_type: Union[str, Tuple[str, ...]] = None,
    output_type: str = None,
    all_arguments_required: bool = False,
    force: str = None,
):
    """
    Console Command registers is a decorator that registers a command to the kernel. Any commands that execute
    within the console are registered with this decorator. It varies attributes that define how the decorator
    should be treated. Commands work with named contexts in a pipelined architecture. So "element" commands output
    must be followed by "element" command inputs. The input_type and output_type do not have to match and can be
    a tuple of different types. None refers to the base context.

    The long_help is the docstring of the actual function itself.

    @param registration: the kernel or service this is being registered to
    @param path: command name of the command being registered
    @param regex: Should this command name match regex command values.
    @param hidden: Whether this command shows up in `help` or not.
    @param help: What should the help for this command be.
    @param input_type: What is the incoming context for the command
    @param output_type: What is the outgoing context for the command
    @param all_arguments_required: Should raise a syntax error if any argument is unfilled
    @param force: force registration destination.
    @return:
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def inner(command: str, remainder: str, channel: "Channel", **ik):
            options = inner.options
            arguments = inner.arguments

            # Stack are the opts which require values.
            stack = list()
            stack.extend(arguments)

            # To be passed to the console_command
            kwargs = dict()

            argument_index = 0
            opt_index = 0
            pos = 0
            nargs = 0

            for kind, value, start, pos in _cmd_parser(remainder):
                if kind == "PARAM":
                    # is a parameter-option
                    if argument_index == len(stack):
                        pos = start
                        break  # Nothing else is expected.
                    # Set option qualities
                    k = stack[argument_index]

                    # Get key name.
                    key = k["name"]

                    if key not in kwargs:
                        # Set default key for unset key.
                        kwargs[key] = []

                    # Set nargs
                    nargs = k.get("nargs", 1)
                    if nargs == "*":
                        nargs = float("inf")

                    # Attempt cast to type.
                    if (
                        "type" in k
                        and value is not None
                        and not k.get("parallel_cast", False)
                    ):
                        try:
                            value = k["type"](value)
                        except ValueError:
                            # Failed cast, if nargs="*" this is end of list.
                            if isinf(nargs):
                                pos = start
                                break
                            raise CommandSyntaxError(
                                f"'{str(value)}' does not cast to {str(k['type'])}"
                            )

                    kwargs[key].append(value)

                    if nargs == len(kwargs[key]):
                        # We have satisfied the nargs, next values.
                        argument_index += nargs
                        opt_index = argument_index
                elif kind == "LONG" or kind == "OPT":
                    # is a --option or -o type option.
                    for pk in options:
                        # check all options for this one to match
                        name = pk["name"]
                        if (value == pk["name"] and kind == "LONG") or (
                            value == pk["short"] and kind == "OPT"
                        ):
                            nargs = pk.get("nargs", 1)
                            # matching option.
                            action = pk.get("action")
                            if action == "store_true":
                                kwargs[name] = True
                            elif action == "store_const":
                                kwargs[name] = pk.get("const")
                            else:
                                for n in range(nargs):
                                    stack.insert(opt_index, pk)
                                    opt_index += 1
                                nargs = 0
                            break
                    opt_index = argument_index
            if isinf(nargs):
                # If the final number_args was infinite.
                argument_index += 1
            if inner.all_arguments_required:
                if argument_index != len(stack):
                    raise CommandSyntaxError("Required arguments were not present.")

            # Any unprocessed positional arguments get default values (even None)
            for idx in range(argument_index, len(stack)):
                k = stack[idx]
                value = k.get("default")
                if "type" in k and value is not None:
                    try:
                        value = k["type"](value)
                    except (TypeError, ValueError):
                        pass
                key = k["name"]
                current = kwargs.get(key)
                if current is None:
                    kwargs[key] = [value]
                else:
                    kwargs[key].append(value)

            # Unset uncalled options with default values are added to kwargs.
            for pk in options:
                key = pk["name"]
                if "default" in pk and key not in kwargs:
                    value = pk.get("default")
                    if "type" in pk and value is not None:
                        try:
                            value = pk["type"](value)
                        except (TypeError, ValueError):
                            pass
                    kwargs[key] = value

            # Any parallel_cast opts should be cast in parallel
            for k in options + arguments:
                if not k.get("parallel_cast", False):
                    continue
                key = k["name"]
                current = kwargs.get(key)
                if "type" in k and isinstance(current, list):
                    try:
                        kwargs[key] = k["type"](*current)
                    except TypeError:
                        raise CommandSyntaxError(f"Not enough values given for {key}.")

            # Any singleton list arguments should become their only element, unless nargs is set.
            for k in stack:
                if k.get("nargs") is not None:
                    continue
                key = k["name"]
                current = kwargs.get(key)
                if isinstance(current, list):
                    if len(current) == 1:
                        kwargs[key] = current[0]

            # Process any remainder and args to include into kwargs
            remainder = remainder[pos:]
            if len(remainder) > 0:
                kwargs["remainder"] = remainder
                try:
                    kwargs["args"] = remainder.split()
                except AttributeError:
                    kwargs["args"] = remainder

            command_return_context = inner.output_type
            # If function does not chain, we should unset remainder
            if command_return_context is None:
                remainder = ""  # not chaining

            # Call the function.
            if inner.object:
                returned = func(
                    inner.object, command=command, channel=channel, **ik, **kwargs
                )
            else:
                returned = func(command=command, channel=channel, **ik, **kwargs)

            # Process return values.
            if returned is None:
                value = None
                command_return_context = None
            else:
                if not isinstance(returned, tuple) or len(returned) != 2:
                    raise ValueError(
                        f'"{str(returned)}" from command "{command}" returned improper values. "{str(kwargs)}"'
                    )
                command_return_context, value = returned
            return value, remainder, command_return_context

        if hasattr(inner, "arguments"):
            # Console_command() was called twice.
            raise MalformedCommandRegistration(
                "Applying console_command() to console_command()"
            )

        # Main Decorator
        cmds = path if isinstance(path, tuple) else (path,)
        ins = input_type if isinstance(input_type, tuple) else (input_type,)
        inner.long_help = func.__doc__
        inner.help = help
        inner.regex = regex
        inner.hidden = hidden
        inner.input_type = input_type
        inner.output_type = output_type
        inner.all_arguments_required = all_arguments_required

        inner.arguments = list()
        inner.options = list()
        inner.object = None

        # Process registration.
        def unregister(reg, obj=None):
            """
            Unregister into registration.
            """
            if force == "kernel" and hasattr(reg, "kernel"):
                reg = reg.kernel
            console_command_remove(reg, path, input_type)

        def register(reg, obj=None):
            """
            Register in the service or kernel.
            """
            if force == "service":
                if not hasattr(reg, "kernel"):
                    # Force service reg, but kernel registration given. Abort.
                    return
            if force == "kernel" and hasattr(reg, "kernel"):
                # force kernel reg, and given service. Use kernel.
                reg = reg.kernel
            for cmd in cmds:
                for i in ins:
                    p = f"command/{i}/{cmd}"
                    reg.register(p, inner)
            inner.object = obj
            inner.unreg = unregister

        inner.reg = register
        if registration:
            register(registration)

        return inner

    return decorator


def kernel_console_command(*args, **kwargs):
    return console_command(None, *args, **kwargs, force="kernel")


def service_console_command(*args, **kwargs):
    return console_command(None, *args, **kwargs, force="service")


def console_command_remove(
    registration,
    path: Union[str, Tuple[str, ...]] = None,
    input_type: Union[str, Tuple[str, ...]] = None,
):
    """
    Removes a console command with the given input_type at the given path.

    @param registration: the kernel or service this is being registered to
    @param path: path or tuple of paths to delete.
    @param input_type: type or tuple of types to delete
    @return:
    """
    cmds = path if isinstance(path, tuple) else (path,)
    ins = input_type if isinstance(input_type, tuple) else (input_type,)
    for cmd in cmds:
        for i in ins:
            p = f"command/{i}/{cmd}"
            registration.unregister(p)


def _cmd_cli_parser(
    argv: List[str],
) -> Generator[Tuple[str, str, int, int], None, None]:
    """
    Parser for console command events.

    @param argv:
    @return:
    """
    for text in argv:
        pos = 0
        limit = len(text)
        while pos < limit:
            match = _CMD_RE.match(text, pos)
            if match is None:
                break  # No more matches.
            kind = match.lastgroup
            start = pos
            pos = match.end()
            if kind == "SKIP":
                pass
            elif kind == "PARAM":
                value = match.group()
                yield kind, value, start, pos
            elif kind == "QPARAM":
                value = match.group()
                yield "PARAM", value[1:-1], start, pos
            elif kind == "LONG":
                value = match.group()
                yield kind, value[2:], start, pos
            elif kind == "OPT":
                value = match.group()
                for letter in value[1:]:
                    yield kind, letter, start, pos
                    start += 1


def _cmd_parser(text: str) -> Generator[Tuple[str, str, int, int], None, None]:
    """
    Parser for console command events.

    @param text:
    @return:
    """
    if isinstance(text, list):
        yield from _cmd_cli_parser(text)
        return
    pos = 0
    limit = len(text)
    while pos < limit:
        match = _CMD_RE.match(text, pos)
        if match is None:
            break  # No more matches.
        kind = match.lastgroup
        start = pos
        pos = match.end()
        if kind == "SKIP":
            continue
        elif kind == "PARAM":
            value = match.group()
            yield kind, value, start, pos
        elif kind == "QPARAM":
            value = match.group()
            yield "PARAM", value[1:-1], start, pos
        elif kind == "LONG":
            value = match.group()
            yield kind, value[2:], start, pos
        elif kind == "OPT":
            value = match.group()
            for letter in value[1:]:
                yield kind, letter, start, pos
                start += 1
