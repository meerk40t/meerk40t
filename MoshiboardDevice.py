from Kernel import Device


class MoshiboardDevice(Device):
    """
    """
    def __init__(self, root, uid=''):
        Device.__init__(self, root, uid)
        self.uid = uid

        # Device specific stuff. Fold into proper kernel commands or delegate to subclass.
        self._device_log = ''
        self.current_x = 0
        self.current_y = 0

        self.hold_condition = lambda e: False
        self.pipe = None
        self.interpreter = None
        self.spooler = None

    def __repr__(self):
        return "MoshiboardDevice(uid='%s')" % str(self.uid)

    def initialize(self, device, name=''):
        """
        Device initialize.

        :param device:
        :param name:
        :return:
        """
        self.uid = name

    def shutdown(self, shutdown):
        self.spooler.clear_queue()
