import math
from functools import lru_cache


class CylinderModifier:
    def __init__(self, wrapped_instance, service):
        self._wrapped_instance = wrapped_instance
        self.service = service

        self.mirror_distance = service.cylinder_mirror_distance
        self.x_axis = service.cylinder_x_axis
        self.x_axis_length = service.cylinder_x_diameter
        self.x_concave = service.cylinder_x_concave

        self.y_axis = service.cylinder_y_axis
        self.y_axis_length = service.cylinder_y_diameter
        self.y_concave = service.cylinder_y_concave

        dx, dy = self.service.view.position(self.x_axis_length, 0, vector=True)
        self.r_x = abs(complex(dx, dy))
        dx, dy = self.service.view.position(0, self.y_axis_length, vector=True)
        self.r_y = abs(complex(dx, dy))
        self.l_x = 0x8000
        self.l_y = 0x8000

    @lru_cache(maxsize=1024)
    def convert(self, x, y):
        a = x - 0x8000
        r = self.r_x
        x_prime = a if r == 0 else r * math.sin(a / r)
        a = y - 0x8000
        r = self.r_y
        y_prime = a if r == 0 else r * math.sin(a / r)
        return x_prime + 0x8000, y_prime + 0x8000

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
