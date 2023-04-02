import re
from collections import deque
from datetime import datetime
from typing import Callable, Optional, Union

# https://en.wikipedia.org/wiki/ANSI_escape_code#3-bit_and_4-bit
BBCODE_LIST = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bg-black": "\033[40m",
    "bg-red": "\033[41m",
    "bg-green": "\033[42m",
    "bg-yellow": "\033[43m",
    "bg-blue": "\033[44m",
    "bg-magenta": "\033[45m",
    "bg-cyan": "\033[46m",
    "bg-white": "\033[47m",
    "bold": "\033[1m",
    "/bold": "\033[22m",
    "italic": "\033[3m",
    "/italic": "\033[3m",
    "underline": "\033[4m",
    "/underline": "\033[24m",
    "underscore": "\033[4m",
    "/underscore": "\033[24m",
    "negative": "\033[7m",
    "positive": "\033[27m",
    "normal": "\033[0m",
}

# re for bbcode->ansi
RE_ANSI = re.compile(
    r"((?:\[raw\])(.*?)(?:\[/raw\]|$)|"
    + r"|".join([r"\[%s\]" % x for x in BBCODE_LIST])
    + r")",
    re.IGNORECASE,
)


def bbcode_to_ansi(text):
    return "".join(
        [
            BBCODE_LIST["normal"],
            RE_ANSI.sub(bbcode_to_ansi_match, text),
            BBCODE_LIST["normal"],
        ]
    )


def bbcode_to_ansi_match(m):
    tag = re.sub(r"\].*", "", m[0])[1:].lower()
    return BBCODE_LIST[tag] if tag != "raw" else m[2]


def bbcode_to_plain(text):
    if isinstance(text, (bytes, bytearray)):
        return text
    return RE_ANSI.sub("", text)


class Channel:
    """
    Register and configure the Kernel channel that is used to send and view data within the kernel. Channels can send
    both string data and binary data. They provide debug information and data such as from a server module.
    """

    def __init__(
        self,
        name: str,
        buffer_size: int = 0,
        line_end: Optional[str] = None,
        timestamp: bool = False,
        pure: bool = False,
        ansi: bool = False,
    ):
        self.watchers = []
        self.greet = None
        self.name = name
        self.buffer_size = buffer_size
        self.line_end = line_end
        self._ = lambda e: e
        self.timestamp = timestamp
        self.pure = pure
        if buffer_size == 0:
            self.buffer = None
        else:
            self.buffer = deque()
        self.ansi = ansi

    def __repr__(self):
        return f"Channel({repr(self.name)}, buffer_size={str(self.buffer_size)}, line_end={repr(self.line_end)})"

    def _call_raw(
        self,
        message: Union[str, bytes, bytearray],
    ):
        for w in self.watchers:
            w(message)
        if self.buffer is not None:
            self.buffer.append(message)
            while len(self.buffer) > self.buffer_size:
                self.buffer.popleft()

    def __call__(
        self,
        message: Union[str, bytes, bytearray],
        *args,
        indent: Optional[bool] = True,
        ansi: Optional[bool] = False,
        **kwargs,
    ):
        if isinstance(message, (bytes, bytearray)) or self.pure:
            self._call_raw(message)
            return

        original_msg = message
        if self.line_end is not None:
            message = message + self.line_end
        if indent:
            message = "    " + message.replace("\n", "\n    ")
        if self.timestamp:
            ts = datetime.now().strftime("[%H:%M:%S] ")
            message = ts + message.replace("\n", f"\n{ts}")
        if ansi:
            if self.ansi:
                # Convert bbcode to ansi
                message = self.bbcode_to_ansi(message)
            else:
                # Convert bbcode to stripped
                message = self.bbcode_to_plain(message)

        console_open_print = False
        # Check if this channel is "open" i.e. being sent to console
        # and if so whether the console is being sent to print
        # because if so then we don't want to print ourselves
        for w in self.watchers:
            if isinstance(w, Channel) and w.name == "console" and print in w.watchers:
                console_open_print = True
                break
        for w in self.watchers:
            # Avoid double printing if this channel is "open" and printed
            # and console is also printed
            if w is print and console_open_print:
                continue
            # Avoid double timestamp and indent
            if isinstance(w, Channel):
                w(original_msg, indent=indent, ansi=ansi)
            else:
                w(message)
        if self.buffer is not None:
            self.buffer.append(message)
            while len(self.buffer) > self.buffer_size:
                self.buffer.popleft()

    def __len__(self):
        return self.buffer_size

    def __iadd__(self, other):
        self.watch(monitor_function=other)

    def __isub__(self, other):
        self.unwatch(monitor_function=other)

    def __bool__(self):
        """
        In the case that a channel requires preprocessing or object creation, the truthy value
        of the channel reflects whether that data will be actually sent anywhere before trying to
        send the data. With this you can have `channels` that do no work unless something in the kernel
        is listening for that data, or the data is being buffered.
        """
        return bool(self.watchers) or self.buffer_size != 0

    def bbcode_to_ansi(self, text):
        return "".join(
            [
                BBCODE_LIST["normal"],
                RE_ANSI.sub(self.bbcode_to_ansi_match, text),
                BBCODE_LIST["normal"],
            ]
        )

    def bbcode_to_ansi_match(self, m):
        tag = re.sub(r"\].*", "", m[0])[1:].lower()
        return BBCODE_LIST[tag] if tag != "raw" else m[2]

    def bbcode_to_plain(self, text):
        strip = lambda m: m[2]
        return RE_ANSI.sub(strip, text)

    def watch(self, monitor_function: Callable):
        for q in self.watchers:
            if q is monitor_function:
                return  # This is already being watched by that.
        self.watchers.append(monitor_function)
        if self.greet is not None:
            if isinstance(self.greet, str):
                monitor_function(self.greet)
            else:
                for g in self.greet():
                    monitor_function(g)
        if self.buffer is not None:
            for line in list(self.buffer):
                monitor_function(line)

    def unwatch(self, monitor_function: Callable):
        self.watchers.remove(monitor_function)
