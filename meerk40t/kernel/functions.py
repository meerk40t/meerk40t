import functools
import os
import os.path
import platform
import re
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple, Union

from meerk40t.kernel.exceptions import MalformedCommandRegistration

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
    @return:
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def inner(command: str, remainder: str, channel: "Channel", **ik):
            options = inner.options
            arguments = inner.arguments
            stack = list()
            stack.extend(arguments)
            kwargs = dict()
            argument_index = 0
            opt_index = 0
            output_type = inner.output_type
            pos = 0
            for kind, value, start, pos in _cmd_parser(remainder):
                if kind == "PARAM":
                    if argument_index == len(stack):
                        pos = start
                        break  # Nothing else is expected.
                    k = stack[argument_index]
                    argument_index += 1
                    if "type" in k and value is not None:
                        try:
                            value = k["type"](value)
                        except ValueError:
                            raise SyntaxError(
                                "'%s' does not cast to %s"
                                % (str(value), str(k["type"]))
                            )
                    key = k["name"]
                    current = kwargs.get(key, True)
                    if current is True:
                        kwargs[key] = [value]
                    else:
                        kwargs[key].append(value)
                    opt_index = argument_index
                elif kind == "LONG":
                    for pk in options:
                        if value == pk["name"]:
                            if pk.get("action") != "store_true":
                                count = pk.get("nargs", 1)
                                for n in range(count):
                                    stack.insert(opt_index, pk)
                                    opt_index += 1
                            kwargs[value] = True
                            break
                    opt_index = argument_index
                elif kind == "OPT":
                    for pk in options:
                        if value == pk["short"]:
                            count = pk.get("nargs", 1)
                            for n in range(count):
                                if pk.get("action") != "store_true":
                                    stack.insert(opt_index, pk)
                                    opt_index += 1
                            kwargs[pk["name"]] = True
                            break

            # Any unprocessed positional arguments get default values.
            for a in range(argument_index, len(stack)):
                k = stack[a]
                value = k.get("default")
                if "type" in k and value is not None:
                    value = k["type"](value)
                key = k["name"]
                current = kwargs.get(key)
                if current is None:
                    kwargs[key] = [value]
                else:
                    kwargs[key].append(value)

            # TODO: Options with default values should be passed to the function with those values.

            # Any singleton list arguments should become their only element.
            for a in range(len(stack)):
                k = stack[a]
                key = k["name"]
                current = kwargs.get(key)
                if isinstance(current, list):
                    if len(current) == 1:
                        kwargs[key] = current[0]

            remainder = remainder[pos:]
            if len(remainder) > 0:
                kwargs["remainder"] = remainder
                try:
                    kwargs["args"] = remainder.split()
                except AttributeError:
                    kwargs["args"] = remainder
            if output_type is None:
                remainder = ""  # not chaining
            returned = func(command=command, channel=channel, **ik, **kwargs)
            if returned is None:
                value = None
                out_type = None
            else:
                if not isinstance(returned, tuple) or len(returned) != 2:
                    raise ValueError(
                        '"%s" from command "%s" returned improper values. "%s"'
                        % (str(returned), command, str(kwargs))
                    )
                out_type, value = returned
            return value, remainder, out_type

        if hasattr(inner, "arguments"):
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

        inner.arguments = list()
        inner.options = list()

        for cmd in cmds:
            for i in ins:
                p = "command/%s/%s" % (i, cmd)
                registration.register(p, inner)
        return inner

    return decorator


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
            p = "command/%s/%s" % (i, cmd)
            registration.unregister(p)


def _cmd_cli_parser(
    argv: List[str],
) -> Generator[Tuple[str, str, int, int], None, None]:
    """
    Parser for console command events.

    @param text:
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
