
def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .tcp_server import plugin as tcp
        from .udp_server import plugin as udp
        from .console_server import plugin as console_server
        return [tcp, udp, console_server]
    if lifecycle == "invalidate":
        return True
