def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .console_server import plugin as console_server
        from .tcp_server import plugin as tcp
        from .udp_server import plugin as udp
        from .web_server import plugin as web

        return [tcp, udp, web, console_server]
    if lifecycle == "invalidate":
        return True
