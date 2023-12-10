import time


def plugin(kernel, lifecycle=None):
    if lifecycle == "invalidate":
        try:
            import serial
        except ImportError:
            return True
    if lifecycle == "register":
        import serial

        @kernel.console_option("port", "c", type=str, default="COM4")
        @kernel.console_option(
            "baud_rate", "b", type=int, default=9600, help="baud rate"
        )
        @kernel.console_option(
            "timeout", "t", type=float, default=30.0, help="timeout in seconds"
        )
        @kernel.console_option(
            "delay", "d", type=float, default=0., help="Wait time before sending data info."
        )
        @kernel.console_argument("send_data", type=str, help="data to send to device")
        @kernel.console_argument("recv_data", type=str, help="match data from device")
        @kernel.console_command(
            "serial_exchange", help="Talk to a serial port in a blocking manner"
        )
        def serial_check(
            channel,
            _,
            send_data,
            recv_data,
            delay=1.0,
            port="COM4",
            baud_rate=9600,
            timeout=30.0,
            **kwargs,
        ):
            serial_device = None
            try:
                # Open the serial port
                serial_device = serial.Serial(port, baud_rate, timeout=2)

                if delay:
                    time.sleep(delay)
                # Send the "Start" command
                serial_device.write(send_data.encode("utf-8"))

                # Read and print the response until "End" is received
                found = False
                end_time = time.time() + timeout
                while end_time > time.time():
                    response = serial_device.readline().decode("utf-8").strip()
                    channel(response)
                    if recv_data in response:
                        found = True
                        break
                if not found:
                    channel(_("Timeout reached."))
            except serial.SerialException as e:
                channel(f"Error: {e}")
            finally:
                # Close the serial port, if opened
                if serial_device is not None and serial_device.is_open:
                    serial_device.close()
