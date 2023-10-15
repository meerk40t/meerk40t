
class TigerDriver:
    def __init__(self, service, channel=None, *args, **kwargs):
        super().__init__()
        self.service = service
        self.name = str(self.service)
        self.state = 0

        self.native_x = 0
        self.native_y = 0

    def __repr__(self):
        return f"TigerDriver({self.name})"

    def __call__(self, e, real=False):
        print(e)

    def hold_work(self, priority):
        """
        Required.

        Spooler check. to see if the work cycle should be held.

        @return: hold?
        """
        return False

    def job_start(self, job):
        pass

    def job_finish(self, job):
        pass

    def home(self):
        self("Home!")