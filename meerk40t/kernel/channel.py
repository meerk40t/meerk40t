import re
import threading
import weakref
from collections import deque
from datetime import datetime
from queue import Empty, Queue
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
all_tags = list(BBCODE_LIST.keys())
# Add closing versions of color tags that don't have explicit closing entries
color_tags = [
    k
    for k in BBCODE_LIST
    if not k.startswith('/') and k not in ('normal', 'positive')
]
closing_tags = [f'/{k}' for k in color_tags]
all_tags.extend(closing_tags)

RE_ANSI = re.compile(
    r"((?:\[raw\])(.*?)(?:\[/raw\]|$)|"
    + r"|".join([r"\[%s\]" % x for x in all_tags])
    + r")",
    re.IGNORECASE,
)

class SimpleLogger:
    def __init__(self, name: str):
        self.name = name

    def log(self, message: str):
        print(f"[{self.name}-Info] {message}")

    def warning(self, message: str):
        print(f"[{self.name}-Warning] {message}")

    def error(self, message: str):  
        print(f"[{self.name}-Error] {message}")
        
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
    return text if isinstance(text, (bytes, bytearray)) else RE_ANSI.sub("", text)

# Logger for channel system
logger = SimpleLogger(__name__)

class Channel:
    """
    Observer pattern implementation for kernel messaging.
    
    Channels provide a publish-subscribe mechanism for distributing messages
    throughout the MeerK40t kernel. They support both synchronous and 
    asynchronous (threaded) message delivery, optional buffering, and 
    text formatting for console output.
    
    Key Features:
    - Observer pattern with watcher registration (supports weak references)
    - Optional message buffering with configurable size
    - Threaded message processing for performance
    - BBCode to ANSI text formatting for console output
    - Timestamp prefixes for logging
    - Greeting messages for new watchers
    - Error isolation (one broken watcher doesn't break others)
    
    Thread Safety:
    - Synchronous mode is thread-safe for single-writer scenarios
    - Threaded mode uses proper synchronization with Queue
    
    Memory Management:
    - Weak reference support prevents memory leaks
    - Automatic cleanup of dead weak references
    
    Usage:
        channel = Channel("debug", buffer_size=100, timestamp=True)
        channel.watch(print)  # Add watcher
        channel("Hello world!")  # Send message
        channel.resize_buffer(200)  # Resize buffer
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
        self.buffer = None if buffer_size == 0 else deque()
        self.ansi = ansi
        self.threaded = False

    def __repr__(self):
        return f"Channel({repr(self.name)}, buffer_size={str(self.buffer_size)}, line_end={repr(self.line_end)})"

    def _call_raw(
        self,
        message: Union[str, bytes, bytearray],
    ):
        # Create a copy of watchers to avoid modification during iteration
        for w in self.watchers[:]:
            self._call_watcher(w, message)
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
        execute_threaded=True,
        **kwargs,
    ):
        if self.threaded and execute_threaded:
            self._threaded_call(message, *args, indent=indent, ansi=ansi, **kwargs)
            return
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
        for w in self.watchers[:]:  # Copy list to avoid modification during iteration
            # Avoid double printing if this channel is "open" and printed
            # and console is also printed
            if w is print and console_open_print:
                continue
            self._call_watcher(w, message, indent=indent, ansi=ansi, original_msg=original_msg)
        if self.buffer is not None:
            self.buffer.append(message)
            while len(self.buffer) > self.buffer_size:
                self.buffer.popleft()

    def __len__(self):
        return self.buffer_size

    def __iadd__(self, other):
        self.watch(other)
        return self

    def __isub__(self, other):
        self.unwatch(other)
        return self

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
        return m[2] if tag == "raw" else BBCODE_LIST.get(tag, BBCODE_LIST["normal"])

    def bbcode_to_plain(self, text):
        def strip(m):
            tag = re.sub(r"\].*", "", m[0])[1:].lower()
            return m[2] if tag == "raw" else ""
        return RE_ANSI.sub(strip, text)

    def watch(self, monitor_function: Callable, weak: bool = False):
        """
        Add a watcher function to this channel.
        
        Args:
            monitor_function: The function to call when messages are sent
            weak: If True, use a weak reference to prevent memory leaks
        """
        for q in self.watchers:
            if q is monitor_function:
                return  # This is already being watched by that.
        
        if weak:
            # Use weak reference to prevent memory leaks
            ref = weakref.ref(monitor_function, self._watcher_died)
            self.watchers.append(ref)
        else:
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

    def _call_watcher(self, watcher, message, indent=None, ansi=None, original_msg=None):
        """
        Helper to call a watcher, handling weak references and exceptions.
        
        Args:
            watcher: The watcher to call (may be a weak reference)
            message: The processed message to send to function watchers
            indent: Whether to indent the message (for Channel watchers)
            ansi: Whether to apply ANSI formatting (for Channel watchers)
            original_msg: The original unprocessed message (for Channel watchers)
        """
        try:
            if isinstance(watcher, Channel):
                msg_to_send = original_msg if original_msg is not None else message
                watcher(msg_to_send, indent=indent, ansi=ansi)
            else:
                if isinstance(watcher, weakref.ref):
                    watcher_func = watcher()
                    if watcher_func is None:
                        # Dead weakref, remove it
                        try:
                            self.watchers.remove(watcher)
                        except ValueError:
                            pass
                        return
                else:
                    watcher_func = watcher
                # For function watchers, pass the processed message directly
                watcher_func(message)
        except Exception as e:
            # Log watcher errors but continue processing other watchers
            logger.warning(f"Watcher error in channel '{self.name}': {e}")

    def _watcher_died(self, ref):
        """Callback when a weak reference watcher is garbage collected."""
        try:
            self.watchers.remove(ref)
        except ValueError:
            pass  # Already removed

    def unwatch(self, monitor_function: Callable):
        """Remove a watcher function from this channel."""
        # First try direct removal (for non-weak references)
        try:
            self.watchers.remove(monitor_function)
            return
        except ValueError:
            pass
        
        # If direct removal failed, check for weak references
        for w in self.watchers[:]:
            if isinstance(w, weakref.ref) and w() is monitor_function:
                self.watchers.remove(w)
                return
        
        # If we get here, the function wasn't found
        raise ValueError(f"Watcher {monitor_function} not found in channel '{self.name}'")

    def resize_buffer(self, new_size: int):
        """
        Dynamically resize the message buffer.
        
        Args:
            new_size: New buffer size. 0 disables buffering.
        """
        if new_size == 0:
            if self.buffer is not None:
                self.buffer.clear()
            self.buffer = None
        elif self.buffer is None:
            self.buffer = deque(maxlen=new_size)
        else:
            # Create new deque with new maxlen and copy existing items
            self.buffer = deque(self.buffer, maxlen=new_size)
        self.buffer_size = new_size

    ###########################
    # Threaded Channel Mixins.
    ###########################

    def start(self, root):
        self.threaded = True
        lock = threading.Condition()
        queue = Queue()  # Thread-safe queue

        def threaded_call(
            message: Union[str, bytes, bytearray],
            *args,
            **kwargs,
        ):
            queue.put((message, args, kwargs))
            with lock:
                lock.notify()

        self._threaded_call = threaded_call

        def run():
            while self.threaded:
                try:
                    # Use timeout to allow checking self.threaded periodically
                    q, a, k = queue.get(timeout=0.1)
                    self(q, *a, **k, execute_threaded=False)
                except (Empty, Exception):
                    # Queue.get() timed out or other error, check if we should continue
                    continue

        def stop():
            self.threaded = False
            with lock:
                lock.notify()

        thread = root.threaded(
            run,
            thread_name=self.name,
            daemon=True,
        )
        thread.stop = stop
        return thread
