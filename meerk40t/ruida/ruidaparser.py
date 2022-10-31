from io import BytesIO


class RuidaParser:
    def __init__(self):
        pass

    def parse(self, data, elements):
        emulator = elements.open_as("emulator/ruida", "ruidaparser")
        emulator.spooler = elements.device.spooler
        emulator.device = elements.device
        emulator.elements = elements
        emulator.design = True
        emulator.write(BytesIO(emulator.unswizzle(data)))
        elements.close("ruidaparser")
