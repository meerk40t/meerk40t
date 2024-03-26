import math


class CylinderModifier:
    def __init__(self, wrapped_instance):
        self._wrapped_instance = wrapped_instance
        self.r = 0x4000
        self.l_x = 0x8000
        self.l_y = 0x8000

    def convert(self, x, y):
        y -= 0x8000
        y /= 0x8000
        y = math.asin(y) / (math.tau / 4)
        y *= self.r
        return x, y + 0x8000

    def mark(self, x, y, **kwargs):
        x, y = self.convert(x, y)
        self.l_x, self.l_y = x, y
        return getattr(self._wrapped_instance, "mark")(x, y, **kwargs)

    def goto(self, x, y, **kwargs):
        x, y = self.convert(x, y)
        self.l_x, self.l_y = x, y
        return getattr(self._wrapped_instance, "goto")(x, y, **kwargs)

    def light(self, x, y, **kwargs):
        x, y = self.convert(x, y)
        self.l_x, self.l_y = x, y
        return getattr(self._wrapped_instance, "light")(x, y, **kwargs)

    def dark(self, x, y, **kwargs):
        x, y = self.convert(x, y)
        self.l_x, self.l_y = x, y
        return getattr(self._wrapped_instance, "dark")(x, y, **kwargs)

    def set_xy(self, x, y, **kwargs):
        x, y = self.convert(x, y)
        self.l_x, self.l_y = x, y
        return getattr(self._wrapped_instance, "set_xy")(x, y, **kwargs)

    def get_last_xy(self, **kwargs):
        return self.l_x, self.l_y

    def __getattr__(self, attr):
        return getattr(self._wrapped_instance, attr)
