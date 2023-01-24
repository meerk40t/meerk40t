
def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .tcp_server import plugin as tcp
        from .udp_server import plugin as udp
        return [tcp, udp]
    if lifecycle == "invalidate":
        return True
