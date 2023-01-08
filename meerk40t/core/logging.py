from meerk40t.kernel import Service, Settings


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "register":
        kernel.add_service("logging", Logging(kernel))


class Logging(Service):
    """
    The logging service is located at .logging and stores and saves logged information. This should not store critical
    data and if the logging file is destroyed or deleted it should have no bearing on anything other than saved logs.
    """

    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "logging")
        self._setting_config = Settings(self.kernel.name, "meerk40t.log")
        self.logs = self._setting_config.literal_dict()

    def matching_events(self, prefix, **kwargs):
        for event_key in list(self.logs):
            if not str(event_key).startswith(prefix):
                continue
            event = self.logs[event_key]
            good = True
            for key in kwargs:
                if key in event and kwargs[key] != event[key]:
                    good = False
                    break
            if good:
                yield event_key, event

    def uid(self, prefix):
        if "uid" not in self.logs:
            self.logs["uid"] = dict()
        if prefix not in self.logs["uid"]:
            self.logs["uid"][prefix] = 0
        self.logs["uid"][prefix] += 1
        return f"{prefix}{self.logs['uid'][prefix]}"

    def event(self, event):
        if "uid" in event:
            uid = event["uid"]
            del event["uid"]
        else:
            uid = self.uid("event")
        self.logs[uid] = event

    def shutdown(self, *args, **kwargs):
        self._setting_config.set_dict(self.logs)
        self._setting_config.write_configuration()

    def service_detach(self, *args, **kwargs):
        pass

    def service_attach(self, *args, **kwargs):
        pass
