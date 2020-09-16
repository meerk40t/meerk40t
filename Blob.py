from LaserCommandConstants import COMMAND_HOME


class Blob:
    def __init__(self, data, data_type):
        self.data = data
        self.type = data_type

    def __repr__(self):
        return "Blob(%s, '%s')" % (repr(self.data), str(self.type))


class BlobOperation:
    def __init__(self, blob=None):
        self.blob = blob
        self.output = True
        self.operation = "Blob"

    def __copy__(self):
        return BlobOperation(self)

    def __len__(self):
        return 1

    def generate(self):
        yield COMMAND_HOME
