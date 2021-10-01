import sys

SLEEP_DISABLED = [None, dict(), False]


def on_usb_running(origin, value):
    running = SLEEP_DISABLED[1]
    running[origin] = value
    any = False
    for v in running:
        q = running[v]
        if q:
            any = True
            break
    if any != SLEEP_DISABLED[2]:
        SLEEP_DISABLED[2] = any
        if any:
            SLEEP_DISABLED[0](".sleepmode_disable\n")
        else:
            SLEEP_DISABLED[0](".sleepmode_enable\n")


def plugin(kernel, lifecycle):
    if sys.platform != 'win32':
        # Plugin only matters for MSW platform
        return
    if lifecycle == "boot":
        context = kernel.root

        context.listen("pipe;running", on_usb_running)
    elif lifecycle == "register":
        context = kernel.root

        SLEEP_DISABLED[0] = context
        _ = kernel.translation

        @context.console_command("sleepmode_disable", help=_("disables sleepmode"), hidden=True)
        def sleepmode_disable(**kwargs):
            try:
                import ctypes
                # ES_CONTINUOUS, 0x80000000, # ES_SYSTEM_REQUIRED = 0x00000001
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
            except AttributeError:
                pass

        @context.console_command("sleepmode_enable", help=_("enables sleepmode"), hidden=True)
        def sleepmode_enable(**kwargs):
            try:
                import ctypes
                # ES_CONTINUOUS, 0x80000000
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            except AttributeError:
                pass
    elif lifecycle == "shutdown":
        context = kernel.root
        context.unlisten("pipe;running", on_usb_running)
