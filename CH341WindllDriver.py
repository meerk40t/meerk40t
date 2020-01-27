from ctypes import *


class CH341Driver:
    def __init__(self, driver_index):
        self.driver = windll.LoadLibrary("CH341DLL.dll")
        self.driver_index = driver_index
        self.driver_value = None

    def open(self):
        if self.driver_value is None:
            val = self.driver.CH341OpenDevice(self.driver_index)
            if val == -1:
                return -1
            self.driver_value = val
            self.driver.CH341InitParallel(self.driver_index, 1)  # 0x40, 177, 0x8800, 0, 0

    def close(self):
        self.driver.CH341CloseDevice(self.driver_index)
        self.driver_value = None

    def write(self, packet):
        length = len(packet)
        obuf = (c_byte * length)()
        for i in range(length):
            obuf[i] = packet[i]
        length = (c_byte * 1)()
        length[0] = 32
        self.driver.CH341EppWriteData(self.driver_index, obuf, length)

    def get_status(self):
        obuf = (c_byte * 6)()
        self.driver.CH341GetStatus(self.driver_index, obuf)
        return [int(q & 0xff) for q in obuf]

    def get_chip_version(self):
        return self.driver.CH341GetVerIC(0)  # 48, reads 0xc0, 95, 0, 0 (30,00? = 48)
