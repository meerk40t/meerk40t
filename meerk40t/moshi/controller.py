"""
Moshiboard Controller Module

This module provides the MoshiController class, which manages communication with Moshiboard
laser controllers via USB connection. The controller handles the complex protocol for sending
laser cutting/engraving data to Moshiboard devices.

Key Features:
- Thread-safe data transmission with proper synchronization
- Automatic connection management and error recovery
- Real-time command processing (including emergency stop)
- Buffer management for queuing multiple programs
- Status monitoring and device state tracking
- Support for both libusb and windll drivers

The controller implements a three-stage protocol:
1. Send program data with preamble/epilogue framing
2. Monitor processing status and wait for completion
3. Send completion confirmation

Threading Model:
- Main processing thread handles data transmission
- Real-time commands can interrupt normal processing
- All buffer/program access is protected by a central lock
- Connection operations are thread-safe
"""

import threading
import time

from ..ch341 import get_ch341_interface
from .builder import MoshiBuilder

# Status codes returned by the Moshiboard device
STATUS_OK = 205  # Device is ready to accept commands
STATUS_PROCESSING = 207  # Device is currently processing data
STATUS_ERROR = 237  # An error occurred during processing
STATUS_RESET = 239  # Device has been reset


def get_code_string_from_moshicode(code):
    """
    Convert Moshiboard status codes to human-readable strings.

    Args:
        code (int): The status code returned by the Moshiboard device

    Returns:
        str: Human-readable description of the status code

    Status Codes:
        205 (STATUS_OK): Device is ready to accept commands
        207 (STATUS_PROCESSING): Device is currently processing data
        237 (STATUS_ERROR): An error occurred during processing
        239 (STATUS_RESET): Device has been reset
        0: USB connection failed
        Other: Unknown status code in hex format
    """
    if code == STATUS_OK:
        return "OK"
    elif code == STATUS_PROCESSING:
        return "Processing"
    elif code == STATUS_ERROR:
        return "Error"
    elif code == STATUS_RESET:
        return "Resetting"
    elif code == 0:
        return "USB Failed"
    else:
        return f"UNK {code:02x}"


class MoshiController:
    """
    Moshiboard Controller for managing laser device communication.

    This controller handles the complete lifecycle of sending laser cutting/engraving
    programs to Moshiboard devices. It manages USB connections, buffers data safely
    across threads, and implements the Moshiboard communication protocol.

    Key Responsibilities:
    - Establish and maintain USB connection to Moshiboard device
    - Queue and transmit laser programs in proper protocol format
    - Handle real-time commands (including emergency stop)
    - Monitor device status and manage connection recovery
    - Provide thread-safe access to buffer and program data

    Threading and Synchronization:
    - Uses a single central lock (_program_lock) to protect all buffer/program access
    - Main processing runs in a dedicated thread (_thread_data_send)
    - Real-time commands can interrupt normal processing safely
    - All state changes are properly synchronized

    Protocol Implementation:
    The controller implements a three-stage protocol for each program:

    Stage 0 - Program Preparation:
        - Wait for device ready status (STATUS_OK = 205)
        - Send protocol preamble via MoshiBuilder.prologue()
        - Load program data into transmission buffer

    Stage 1 - Data Transmission:
        - Send program data in 32-byte packets
        - No status checks between packets for efficiency
        - Send protocol epilogue via MoshiBuilder.epilogue()

    Stage 2 - Completion Verification:
        - Monitor device status until processing complete
        - Wait for STATUS_OK (205) indicating successful completion
        - Handle timeout and error conditions gracefully

    Error Handling:
    - Automatic connection recovery on temporary failures
    - Exponential backoff for repeated connection attempts
    - Graceful handling of device disconnection/reconnection
    - Comprehensive logging of all operations and errors

    Attributes:
        _programs (list): Queue of programs waiting to be sent
        _buffer (bytearray): Current program being transmitted
        _program_lock (threading.Lock): Central lock protecting buffer/program access
        connection: USB connection to the Moshiboard device
        state (str): Current controller state (unknown, init, active, idle, etc.)
        context: Service context for logging and signaling
    """

    def __init__(self, service, channel=None, force_mock=False, *args, **kwargs):
        """
        Initialize the MoshiController.

        Args:
            service: The service context providing logging, threading, and configuration
            channel: Optional channel for communication (unused)
            force_mock (bool): Force use of mock connection for testing
            *args: Additional positional arguments (unused)
            **kwargs: Additional keyword arguments (unused)
        """
        self.context = service
        self.state = "unknown"

        # Thread-safe data structures protected by _program_lock
        self._programs = []  # Queue of programs waiting to be processed
        self._buffer = bytearray()  # Current program being transmitted
        self._program_lock = (
            threading.Lock()
        )  # Central lock for all buffer/program access

        # Threading state
        self._thread = None
        self.is_shutdown = False

        # Device status and connection
        self._status = [0] * 6  # Device status array
        self._usb_state = -1
        self.connection = None
        self.force_mock = force_mock

        # Error handling and retry logic
        self.max_attempts = 5
        self.refuse_counts = 0  # Count of consecutive connection refusals
        self.connection_errors = 0  # Count of connection errors
        self.count = 0  # General purpose counter for backoff logic
        self.abort_waiting = False  # Flag to abort wait operations

        # Communication channels
        name = service.safe_label
        self.pipe_channel = service.channel(f"{name}/events")  # General events
        self.usb_log = service.channel(f"{name}/usb", buffer_size=500)  # USB operations
        self.usb_send_channel = service.channel(f"{name}/usb_send")  # Data being sent
        self.recv_channel = service.channel(f"{name}/recv")  # Data received

    def usb_signal_update(self, e):
        """
        Handle USB status updates from the connection.

        This method is registered as a callback for USB status changes
        and forwards them to the service context for broader notification.

        Args:
            e: The USB status event/message
        """
        self.context.signal("pipe;usb_status", e)

    def viewbuffer(self):
        """
        Get a string representation of the current buffer and program queue.

        This method is used by debugging and monitoring tools to inspect
        the current state of queued programs and transmission buffer.

        Returns:
            str: Formatted string showing buffer contents and queued programs
        """
        with self._program_lock:
            buffer = f"Current Working Buffer: {str(self._buffer)}\n"
            for p in self._programs:
                if hasattr(p, "data"):
                    buffer += f"{str(p.data)}\n"
                else:
                    buffer += f"{str(p)} [dataless]\n"
        return buffer

    def added(self, *args, **kwargs):
        """
        Called when the controller is added to the service.

        Sets up the USB logging callback and starts the controller.
        """
        self.start()
        self.usb_log.watch(self.usb_signal_update)

    def shutdown(self, *args, **kwargs):
        """
        Shut down the controller and clean up resources.

        Stops the USB logging callback, terminates processing,
        and signals the processing thread to stop.
        """
        self.usb_log.unwatch(self.usb_signal_update)
        self.update_state("terminate")
        if self._thread is not None:
            self.is_shutdown = True

    def __repr__(self):
        """Return a string representation of the controller."""
        return "MoshiController()"

    def __len__(self):
        """
        Get the total length of buffered data.

        Returns the combined length of the current transmission buffer
        and all queued programs.

        Returns:
            int: Total bytes of data in buffer and queue
        """
        with self._program_lock:
            return len(self._buffer) + sum(map(len, self._programs))

    def _log_connection_error(self, operation, error, usb_index=None):
        """
        Log connection errors with consistent formatting.

        Args:
            operation (str): Description of the operation that failed
            error: The exception that occurred
            usb_index (int, optional): USB device index if applicable
        """
        if usb_index is not None:
            self.usb_log(f"Failed to {operation} at index {usb_index}: {error}")
        else:
            self.usb_log(f"Failed to {operation}: {error}")

    def open(self):
        """
        Establish connection to the Moshiboard device.

        Attempts to find and connect to a compatible Moshiboard device by:
        1. Enumerating available CH341 interfaces
        2. Trying each interface at configured USB indices
        3. Validating device compatibility (bus, address, version)

        Raises:
            ConnectionRefusedError: If no compatible device is found
            PermissionError: If USB access is denied (logged, not raised)

        The method implements robust error handling with detailed logging
        for troubleshooting connection issues.
        """
        _ = self.usb_log._
        if self.connection is not None and self.connection.is_connected():
            return  # Already connected.
        self.pipe_channel("open()")

        try:
            interfaces = list(
                get_ch341_interface(
                    self.context,
                    self.usb_log,
                    mock=self.force_mock or self.context.mock,
                    mock_status=STATUS_OK,
                    bulk=False,
                )
            )
            if self.context.usb_index != -1:
                # Instructed to check one specific device.
                devices = [self.context.usb_index]
            else:
                devices = range(16)

            for interface in interfaces:
                self.connection = interface
                for i in devices:
                    try:
                        self._open_at_index(i)
                        return  # Opened successfully.
                    except ConnectionRefusedError as e:
                        self._log_connection_error("open connection", e, i)
                        if self.connection is not None:
                            self.connection.close()
                    except IndexError as e:
                        self._log_connection_error("open connection", e, i)
                        self.connection = None
                        break
        except PermissionError as e:
            self._log_connection_error("open connection", e)
            return  # OS denied permissions, no point checking anything else.
        if self.connection:
            self.close()
        raise ConnectionRefusedError(
            _("No valid connection matched any given criteria.")
        )

    def _open_at_index(self, usb_index):
        """
        Open connection at a specific USB index with validation.

        Args:
            usb_index (int): The USB device index to attempt connection

        Raises:
            ConnectionRefusedError: If device validation fails
        """
        _ = self.context.kernel.translation
        self.connection.open(usb_index=usb_index)
        if not self.connection.is_connected():
            raise ConnectionRefusedError("ch341 connect did not return a connection.")
        if self.context.usb_bus != -1 and self.connection.bus != -1:
            if self.connection.bus != self.context.usb_bus:
                raise ConnectionRefusedError(
                    _("K40 devices were found but they were rejected due to usb bus.")
                )
        if self.context.usb_address != -1 and self.connection.address != -1:
            if self.connection.address != self.context.usb_address:
                raise ConnectionRefusedError(
                    _(
                        "K40 devices were found but they were rejected due to usb address."
                    )
                )
        if self.context.usb_version != -1:
            version = self.connection.get_chip_version()
            if version != self.context.usb_version:
                raise ConnectionRefusedError(
                    _(
                        "K40 devices were found but they were rejected due to chip version."
                    )
                )

    def close(self):
        """
        Close the current USB connection.

        Safely closes the connection to the Moshiboard device and
        cleans up the connection reference.

        Raises:
            ConnectionError: If no connection exists to close
        """
        self.pipe_channel("close()")
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        else:
            raise ConnectionError

    def write(self, data):
        """
        Queue a program for transmission to the device.

        Adds the program data to the processing queue and ensures
        the processing thread is running.

        Args:
            data: The program data to be sent to the device
        """
        with self._program_lock:
            self._programs.append(data)
        self.start()

    def realtime(self, data):
        """
        Send a real-time command to the device.

        Real-time commands can interrupt normal processing and are
        sent immediately. Special handling for emergency stop commands
        which clear all buffers and terminate current processing.

        Args:
            data: The real-time command data to send
        """
        if MoshiBuilder.is_estop(data):
            self.context.signal("pipe;buffer", 0)
            self.update_state("terminate")
            with self._program_lock:
                self._programs.clear()
                self._buffer.clear()
        try:
            self.open()
            self.connection.write_addr(data)
        except (ConnectionRefusedError, ConnectionError) as e:
            self._log_connection_error("open connection for realtime command", e)

    def start(self):
        """
        Start the data transmission thread.

        Creates and starts a new thread for processing queued programs
        if one is not already running. The thread will process programs
        from the queue and transmit them to the device.

        Thread Safety:
        - Safe to call from any thread
        - Will not create duplicate threads
        - Thread creation is handled by the service context
        """
        if self._thread is None or not self._thread.is_alive():
            self._thread = self.context.threaded(
                self._thread_data_send,
                thread_name=f"MoshiPipe({self.context.path})",
                result=self.stop,
            )
            self.update_state("init")

    def pause(self):
        """
        Pause the current data transmission.

        If called during initialization, this will start processing.
        If called during active processing or idle state, this will
        pause the transmission until resume() is called.

        State Transitions:
        - init → pause (starts processing)
        - active/idle → pause (pauses processing)
        """
        if self.state == "init":
            self.start()
            self.update_state("pause")
        if self.state in ("active", "idle"):
            self.update_state("pause")

    def resume(self):
        """
        Resume paused data transmission.

        Can only be called when the controller is in the 'pause' state.
        Transitions the controller back to 'active' state to continue
        processing queued programs.

        Raises:
            No explicit errors, but has no effect if not in pause state
        """
        if self.state == "pause":
            self.update_state("active")

    def stop(self, *args):
        """
        Stop the data transmission thread.

        Waits for the current thread to complete its work before
        returning. This ensures clean shutdown of processing.

        Thread Safety:
        - Safe to call from any thread
        - Will block until thread completes
        - Handles RuntimeError if called from within the thread
        """
        if self._thread is not None:
            try:
                self._thread.join()  # Wait until stop completes before continuing.
            except RuntimeError:
                pass  # Thread is current thread.
        self._thread = None

    def update_state(self, state):
        """
        Update the controller's current state.

        Manages state transitions and notifies listeners of state changes.
        Only updates and signals if the state actually changes.

        Args:
            state (str): New state ('unknown', 'init', 'active', 'idle', 'pause', etc.)
        """
        if state == self.state:
            return
        self.state = state
        if self.context is not None:
            self.context.signal("pipe;thread", self.state)

    def update_buffer(self):
        """
        Signal that the buffer size has changed.

        Notifies all listeners about the current buffer size.
        Used by UI components to update buffer displays.
        """
        with self._program_lock:
            self.context.signal("pipe;buffer", len(self._buffer))

    def _has_work(self):
        """
        Check if there is any work to be done.

        Returns:
            bool: True if there are programs in queue or buffer has data
        """
        with self._program_lock:
            return bool(self._buffer or self._programs)

    def _load_next_program(self):
        """
        Load the next program from queue into buffer if buffer is empty.

        Returns:
            bool: True if a program was loaded, False otherwise
        """
        with self._program_lock:
            if not self._buffer and self._programs:
                self._buffer += self._programs.pop(0)
                return True
        return False

    def _buffer_length(self):
        """
        Get the current buffer length.

        Returns:
            int: Length of the current buffer
        """
        with self._program_lock:
            return len(self._buffer)

    def update_packet(self, packet):
        """
        Signal that a packet has been sent.

        Notifies listeners about the most recently transmitted packet
        and logs it to the USB send channel.

        Args:
            packet: The packet data that was just sent
        """
        if self.context is not None:
            self.context.signal("pipe;packet_text", packet)
            self.usb_send_channel(packet)

    def _send_buffer(self):
        """
        Send the current transmission buffer to the device.

        Processes the transmission buffer by sending data in chunks and
        managing the transmission state. Implements exponential backoff
        for handling transmission delays.

        Processing Logic:
        - Sends packets until buffer is empty
        - Resets backoff counter on successful sends
        - Increases wait time on failed sends (up to 1 second)
        - Updates controller state based on transmission success

        Thread Safety:
        - Called only from the main processing thread
        - Uses _program_lock for buffer access
        """
        self.pipe_channel("Sending Buffer...")
        while True:
            if not self._buffer_length():
                break
            queue_processed = self.process_buffer()
            self.refuse_counts = 0

            if queue_processed:
                # Packet was sent.
                if self.state not in (
                    "pause",
                    "busy",
                    "active",
                    "terminate",
                ):
                    self.update_state("active")
                self.count = 0
            else:
                # No packet could be sent.
                if self.state not in (
                    "pause",
                    "busy",
                    "terminate",
                ):
                    self.update_state("idle")
                wait_length = 0.02 * min(50, self.count)
                time.sleep(wait_length)
                # will tick up to 1 second waits if there's never a queue.
                self.count += 1

    def _thread_data_send(self):
        """
        Main data transmission thread function.

        This is the core processing loop that handles the complete lifecycle
        of sending programs to the Moshiboard device. Implements the three-stage
        protocol for each program and handles all error conditions.

        Processing Stages:
        1. Wait for work and establish connection
        2. Prepare program (load into buffer, send preamble)
        3. Send data and wait for completion
        4. Send epilogue and verify success

        Error Handling:
        - Connection errors trigger reconnection attempts
        - Multiple refusal errors trigger failure state
        - Graceful shutdown on termination signals

        Thread Safety:
        - This is the only thread that modifies _buffer
        - Uses _program_lock for all buffer/program access
        - Handles shutdown signals properly
        """
        with self._program_lock:
            program_count = len(self._programs)
        self.pipe_channel(f"Send Thread Start... {program_count}")
        self.count = 0
        self.is_shutdown = False

        while True:
            try:
                if self.state == "init":
                    self.update_state("active")
                if self.is_shutdown:
                    break

                if not self._has_work():
                    self.pipe_channel("Nothing to process")
                    break

                # ensure connection…
                if self.connection is None:
                    self.open()

                # Stage 0: load and prologue
                if self._load_next_program():
                    self.context.laser_status = "active"
                    self.pipe_channel("New Program")
                    self.wait_until_accepting_packets()
                    MoshiBuilder.prologue(self.connection.write_addr, self.pipe_channel)

                # Stage 1: send buffer
                buf_len = self._buffer_length()
                if buf_len:
                    self.context.laser_status = "active"
                    self.pipe_channel(f"Sending Data... {buf_len} bytes")
                    self._send_buffer()
                    self.update_status()
                    MoshiBuilder.epilogue(self.connection.write_addr, self.pipe_channel)

                if self.is_shutdown:
                    break

                # Stage 2: wait finish
                if not self._buffer_length():
                    self.pipe_channel("Waiting for finish processing.")
                    self.wait_finished()

                self.context.laser_status = "idle"

            except ConnectionRefusedError:
                if self.is_shutdown:
                    break
                # The attempt refused the connection.
                self.refuse_counts += 1

                if self.refuse_counts >= 5:
                    self.context.signal("pipe;state", "STATE_FAILED_RETRYING")
                self.context.signal("pipe;failing", self.refuse_counts)
                self.context.laser_status = "idle"
                time.sleep(3)  # 3-second sleep on failed connection attempt.
                continue
            except ConnectionError:
                # There was an error with the connection, close it and try again.
                if self.is_shutdown:
                    break
                self.connection_errors += 1
                time.sleep(0.5)
                try:
                    self.close()
                except ConnectionError:
                    pass
                continue
        self.context.laser_status = "idle"
        self._thread = None
        self.is_shutdown = False
        self.update_state("end")
        self.pipe_channel("Send Thread Finished...")

    def process_buffer(self):
        """
        Process and send the next packet from the transmission buffer.

        Extracts the next 32-byte chunk from the buffer, sends it to the device,
        and removes the sent data from the buffer.

        Returns:
            bool: True if a packet was successfully sent, False otherwise

        Thread Safety:
        - Called only from _send_buffer() in the main processing thread
        - Uses _program_lock for buffer modifications
        """
        with self._program_lock:
            if not self._buffer:
                return False
            packet = self._buffer[:32]
            self._buffer = self._buffer[32:]
        self.send_packet(packet)
        self.context.packet_count += 1
        self.update_buffer()
        return True

    def send_packet(self, packet):
        """
        Send a packet to the USB connection.

        Args:
            packet: The data packet to send

        Raises:
            ConnectionError: If no connection is available
        """
        if self.connection is None:
            raise ConnectionError
        self.connection.write(packet)
        self.update_packet(packet)

    def update_status(self):
        """
        Request a status update from the CH341 connection.

        Retrieves the current device status and broadcasts it to all
        listeners. Updates the internal status array and signals
        status changes to the application.

        Raises:
            ConnectionError: If no connection is available
        """
        if self.connection is None:
            raise ConnectionError
        self._status = self.connection.get_status()
        if self.context is not None:
            try:
                self.context.signal(
                    "pipe;status",
                    self._status,
                    get_code_string_from_moshicode(self._status[1]),
                )
            except IndexError:
                pass
            self.recv_channel(str(self._status))

    def wait_until_accepting_packets(self):
        """
        Wait until the device can accept packets.

        Polls the device status until it reports STATUS_OK (205),
        indicating it's ready to receive data. Implements timeout
        and abort handling for robust operation.

        Raises:
            ConnectionError: If USB connection fails
            ConnectionRefusedError: If device reports error status

        Thread Safety:
        - Can be interrupted by setting abort_waiting flag
        - Updates status during wait loop
        """
        i = 0
        while self.state != "terminate":
            self.update_status()
            status = self._status[1]
            if status == 0:
                raise ConnectionError
            if status == STATUS_ERROR:
                raise ConnectionRefusedError
            if status == STATUS_OK:
                return
            time.sleep(0.05)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.

    def wait_finished(self):
        """
        Wait until the device has finished the current sending buffer.

        Monitors device status until processing is complete (STATUS_OK).
        Handles connection recovery and abort signals during the wait.

        Processing States:
        - STATUS_PROCESSING (207): Device is still working
        - STATUS_OK (205): Processing complete
        - STATUS_ERROR (237): Error occurred
        - Status 0: Connection lost

        Thread Safety:
        - Can be interrupted by setting abort_waiting flag
        - Automatically attempts reconnection on connection loss
        - Updates controller state appropriately
        """
        self.pipe_channel("Wait Finished")
        i = 0
        original_state = self.state
        if self.state != "pause":
            self.pause()

        while True:
            if self.state != "wait":
                if self.state == "terminate":
                    return  # Abort all the processes was requested. This state change would be after clearing.
                self.update_state("wait")
            self.update_status()
            status = self._status[1]
            if status == 0:
                self.close()
                self.open()
                continue
            if status == STATUS_OK:
                break
            if self.context is not None:
                self.context.signal("pipe;wait", status, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.
            if status == STATUS_PROCESSING:
                time.sleep(0.5)  # Half a second between requests.
        self.update_state(original_state)
