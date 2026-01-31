"""
The serial_exchange command is intended to facilitate some basic serial exchanges, triggering success or failure events.

The command is blocking so that it can be used as part of a `Console Operation` and block the spooler until the exchange
is finished.

For example, if you have a z-bed and that needs controlling with an auxiliary GRBL device, you could use the exchange
to communicate the needed command to the GRBL, without extremely complex uses of the full driver.
"""

import time


def plugin(kernel, lifecycle=None):
    if lifecycle == "invalidate":
        # Plugin requires pyserial.
        try:
            import serial
        except ImportError:
            return True
    if lifecycle == "register":
        import serial

        @kernel.console_option(
            "port", "c", type=str, default="COM4", help="com port to use"
        )
        @kernel.console_option(
            "baud_rate", "b", type=int, default=9600, help="baud rate"
        )
        @kernel.console_option(
            "timeout", "t", type=float, default=30.0, help="timeout in seconds"
        )
        @kernel.console_option(
            "delay",
            "d",
            type=float,
            default=0.0,
            help="Wait time before sending send_data.",
        )
        @kernel.console_option(
            "failure_message", "f", type=str, help="match data to declare failure"
        )
        @kernel.console_option(
            "failure_command", "F", type=str, help="command to execute on failure"
        )
        @kernel.console_option(
            "success_message", "s", type=str, help="match data to declare success"
        )
        @kernel.console_option(
            "success_command", "S", type=str, help="command to execute on success"
        )
        @kernel.console_argument("send_data", type=str, help="data to send to device")
        @kernel.console_command(
            "serial_exchange", help="Talk to a serial port in a blocking manner."
        )
        def serial_exchange_command(
            channel,
            _,
            send_data,
            delay=1.0,
            port="COM4",
            baud_rate=9600,
            timeout=30.0,
            success_message=None,
            success_command=None,
            failure_message=None,
            failure_command=None,
            **kwargs,
        ):
            serial_device = None
            try:
                # Open the serial port
                serial_device = serial.Serial(port, baud_rate, timeout=2)

                if delay:
                    # Add in wakeup delay.
                    time.sleep(delay)

                # Send data.
                serial_device.write(send_data.encode("utf-8"))

                end_time = time.time() + timeout
                while end_time > time.time():
                    # Execute until timeout.

                    response = (
                        serial_device.readline()
                        .decode("utf-8", errors="ignore")
                        .strip()
                    )
                    channel(response)
                    if success_message and success_message in response:
                        # Actively succeeded
                        if success_command:
                            kernel.root(success_command)
                        return
                    if failure_message and failure_message in response:
                        # Actively failed.
                        if failure_command:
                            kernel.root(failure_command)
                        return
                    if not failure_message and not success_message and not response:
                        # Not matching criteria, read buffer and exit.
                        return

                # We timed out.
                channel(_("Timeout reached."))
                if failure_command:
                    # Timeout is a failure condition.
                    kernel.root(failure_command)
            except serial.SerialException as e:
                channel(f"Error: {e}")
                # Error is a failure condition.
                kernel.root(failure_command)
            finally:
                # Close the serial port, if opened
                if serial_device is not None and serial_device.is_open:
                    serial_device.close()
