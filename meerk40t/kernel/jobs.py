import time
from typing import Callable, Optional, Tuple


class Job:
    """
    Generic job for the scheduler.

    Jobs that can be scheduled in the scheduler-kernel to run at a particular time and a given number of times.
    This is done calling schedule() and unschedule() and setting the parameters for process, args, interval,
    and times.
    """

    def __init__(
        self,
        process: Optional[Callable] = None,
        args: Optional[Tuple] = (),
        interval: float = 1.0,
        times: Optional[int] = None,
        job_name: Optional[str] = None,
        run_main: bool = False,
        conditional: Callable = None,
    ):
        self.job_name = job_name
        self.state = "init"
        self.run_main = run_main
        self.conditional = conditional

        self.process = process
        self.args = args
        self.interval = interval
        self.times = times

        self._last_run = None
        self._next_run = time.time() + self.interval
        self._remaining = self.times

    def __call__(self, *args, **kwargs):
        self.process(*args, **kwargs)

    def __str__(self):
        if self.job_name is not None:
            return self.job_name
        else:
            try:
                return self.process.__name__
            except AttributeError:
                return object.__str__(self)

    @property
    def remaining(self) -> int:
        return self._remaining

    @property
    def scheduled(self) -> bool:
        return (
            self._next_run is not None
            and time.time() >= self._next_run
            and (self.conditional is None or self.conditional())
        )

    def reset(self) -> None:
        self._last_run = None
        self._next_run = time.time() + self.interval
        self._remaining = self.times

    def cancel(self) -> None:
        self._remaining = -1


class ConsoleFunction(Job):
    """
    Special type of Job that runs the Console command provided when the job is executed.
    """

    def __init__(
        self,
        context: "Context",
        data: str,
        interval: float = 1.0,
        times: Optional[int] = None,
        job_name: Optional[str] = None,
        run_main: bool = False,
        conditional: Callable = None,
    ):
        Job.__init__(
            self, self.__call__, None, interval, times, job_name, run_main, conditional
        )
        self.context = context
        self.data = data
        self.index = 1

    def __call__(self, *args, **kwargs):
        self.context.console(
            self.data.format(index=self.index, remaining=self.remaining)
        )
        self.index += 1

    def __str__(self):
        return self.data.replace("\n", "")
