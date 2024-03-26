class CylinderModifier:
    def __init__(self, wrapped_instance):
        self._wrapped_instance = wrapped_instance

    def mark(self, x, y):
        print("Wrapper: Marking coordinates at ({}, {})".format(x, y))
        return getattr(self._wrapped_instance, "mark")(x, y)

    def goto(self, x, y):
        print("Wrapper: Moving to coordinates ({}, {})".format(x, y))
        return getattr(self._wrapped_instance, "goto")(x, y)

    def get_last_xy(self):
        print("Wrapper: Getting last coordinates")
        return getattr(self._wrapped_instance, "get_last_xy")()

    def __getattr__(self, attr):
        return getattr(self._wrapped_instance, attr)
