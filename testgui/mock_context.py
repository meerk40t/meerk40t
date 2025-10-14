class MockContext:
    def __init__(self):
        self._signals = {}
        self.kernel = self
        self.root = self
        self.is_shutdown = False
        self.disable_tool_tips = False
        self.themes = MockThemes()

    def listen(self, attr, listener):
        self._signals.setdefault(attr, []).append(listener)

    def unlisten(self, attr, listener):
        if attr in self._signals and listener in self._signals[attr]:
            self._signals[attr].remove(listener)

    def signal(self, attr, *args, **kwargs):
        for listener in self._signals.get(attr, []):
            listener(attr, *args, **kwargs)

    def setting(self, typ, name, default):
        # For developer_mode and similar
        return default

    def channel(self, name):
        def log(msg):
            pass

        return log


class MockThemes:
    def __init__(self):
        # Provide a minimal set of theme properties
        self._theme_properties = {
            "win_bg": None,
            "win_fg": None,
        }

    def set_window_colors(self, win):
        # No-op for tests, or set to a known color if needed
        if hasattr(win, "SetBackgroundColour"):
            win.SetBackgroundColour("#eeeeee")
        if hasattr(win, "SetForegroundColour"):
            win.SetForegroundColour("#111111")

    def get(self, key):
        return self._theme_properties.get(key, None)
