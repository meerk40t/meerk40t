import time
import wx

from ...core.element_types import elem_nodes
from ...core.units import Length
from ..icons import icons8_up_50
from .statusbarwidget import StatusBarWidget

_ = wx.GetTranslation


class SimpleInfoWidget(StatusBarWidget):
    """
    Placeholder to accept any kind of information,
    if none is given externally it falls back to basic infos
    about the emphasized elements
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # We can store multiple lines of information
        self._messages = []
        self._counter = 0
        self.fontsize = None
        self.priority_for_first_message = True

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)

        self.info_text = wx.StaticText(self.parent, wx.ID_ANY, label="")
        if self.fontsize is not None:
            self.info_text.SetFont(
                wx.Font(
                    self.fontsize,
                    wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                )
            )
        self.btn_next = wx.StaticBitmap(
            self.parent,
            id=wx.ID_ANY,
            bitmap=icons8_up_50.GetBitmap(resize=20),
            size=wx.Size(20, 20),
            style=wx.BORDER_RAISED,
        )
        infocolor = wx.Colour(128, 128, 128, 128)
        self.btn_next.SetBackgroundColour(infocolor)
        self.btn_next.Bind(wx.EVT_LEFT_DOWN, self.on_button_next)
        self.btn_next.Bind(wx.EVT_RIGHT_DOWN, self.on_button_prev)

        self.Add(self.info_text, 1, wx.EXPAND, 0)
        self.Add(self.btn_next, 0, wx.EXPAND, 0)
        self.SetActive(self.btn_next, False)

    def AppendInformation(self, msg):
        self._messages.append(msg)
        self._counter = -1
        self._display_current_line()

    def SetInformation(self, msg):
        lastlen = len(self._messages)
        self._messages = []
        if isinstance(msg, str):
            self._messages = [msg]
        elif isinstance(msg, (tuple, list)):
            self._messages = msg
        flag = len(self._messages) > 1
        self.SetActive(self.btn_next, enableit=flag)
        self.Layout()
        if lastlen != len(self._messages) or self.priority_for_first_message:
            self._counter = 0
        self._display_current_line()

    def _display_current_line(self):
        msg = ""
        if len(self._messages) > 0:
            if self._counter < 0:
                self._counter = len(self._messages) - 1
            if self._counter >= len(self._messages):
                self._counter = 0
            content = self._messages[self._counter]
            msg = "" if content is None else content
        self.info_text.SetLabel(msg)

    def on_button_prev(self, event):
        self._counter -= 1
        self._display_current_line()

    def on_button_next(self, event):
        self._counter += 1
        self._display_current_line()


class InformationWidget(SimpleInfoWidget):
    """
    This widget displays basic infos about the emphasized elements
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fontsize = 7
        self._needs_generation = False
        # We dont have a context yet...
        self._info_active = True

    def Show(self, showit):
        if self._needs_generation and showit:
            self.calculate_infos()
        super().Show(showit)

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)
        self.context.setting(bool, "statusbar_auto_statistic", True)
        self._info_active = self.context.statusbar_auto_statistic

        self.chk_active = wx.CheckBox(parent, wx.ID_ANY, "")
        self.chk_active.SetToolTip(
            _("Uncheck if you don't want automatic statistic generation")
        )
        self.chk_active.SetValue(self._info_active)
        self.chk_active.Bind(wx.EVT_CHECKBOX, self.on_checkbox)
        self.Add(self.chk_active, 0, 0, 0)

    def on_checkbox(self, event):
        self._info_active = self.chk_active.GetValue()
        self.context.statusbar_auto_statistic = self._info_active
        self.calculate_infos()
        event.Skip()

    def GenerateInfos(self):
        if self.visible:
            self.calculate_infos()
        else:
            self._needs_generation = True

    def calculate_infos(self):
        msg = ""
        if self._info_active:
            elements = self.context.elements
            ct = 0
            total_area = 0
            total_length = 0
            _mm = float(Length("1{unit}".format(unit="mm")))
            for e in elements.flat(types=elem_nodes, emphasized=True):
                ct += 1
                this_area, this_length = elements.get_information(e, density=50)
                total_area += this_area
                total_length += this_length

            if ct > 0:
                total_area = total_area / (_mm * _mm)
                total_length = total_length / _mm
                msg = "# = %d, A = %.1f mm², D = %.1f mm" % (
                    ct,
                    total_area,
                    total_length,
                )
        else:
            msg = "---"
        self.StartPopulation()
        self.SetInformation(msg)
        self.EndPopulation()
        self._needs_generation = False

    def Signal(self, signal, *args):
        if signal == "emphasized":
            self.GenerateInfos()


class StatusPanelWidget(SimpleInfoWidget):
    """
    This widget displays basic infos about the emphasized elements
    """

    def __init__(self, panelct, **kwargs):
        super().__init__(**kwargs)
        self.status_text = [""] * panelct
        # self.fontsize = 7

    def GenerateInfos(self):
        compacted_messages = []
        for idx, entry in enumerate(self.status_text):
            if entry != "":
                msg = entry
                if idx > 0:
                    msg = "#" + str(idx) + ": " + msg
                compacted_messages.append(msg)
        self.SetInformation(compacted_messages)

    def Signal(self, signal, *args):
        if signal == "statusmsg":
            msg = ""
            idx = 0
            if len(args) > 0:
                msg = args[0]
            if len(args) > 1:
                idx = args[1]
            self.status_text[idx] = msg
            self.GenerateInfos()


class BurnProgressPanel(SimpleInfoWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.priority_for_first_message = False
        self._status_text = []
        self._needs_generation = False
        self._queue_len = 0
        self._queue_pos = 0
        self._queue_elapsed = 0
        self._queue_remaining = 0
        self._job_label = ""
        self._job_len = 0
        self._job_pos = 0
        self._job_active = False
        self._start_time = 0
        self._remaining = 0.0
        self._queue_misc = ""
        self._job_loops = 0
        self._loops_executed = 0
        self._job_estimate = 0
        self._job_elapsed = 0
        # How often do i want to have an update?
        self._last_invokation = 0
        self._invokation_delta = 2 # Every 2 seconds max
        self._driver = None

    def Show(self, showit):
        if self._needs_generation and showit:
            self.calculate_infos()
        super().Show(showit)

    def GenerateInfos(self):
        if self.visible:
            self.calculate_infos()
        else:
            self._needs_generation = True

    def inspect_job_details(self, laserjob):
        return

    def calculate_infos(self):
        def timestr(t):
            hours, remainder = divmod(t, 3600)
            minutes, seconds = divmod(remainder, 60)
            runtime = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
            return runtime

        dtime = time.time()
        if dtime - self._last_invokation < self._invokation_delta:
            return
        self._last_invokation = dtime

        self._status_text = []
        self._queue_elapsed = 0
        self._queue_len = 0
        self._queue_pos = 0
        self._queue_remaining = 0
        self._job_label = ""
        self._job_len = 0
        self._job_pos = 0
        self._job_active = False
        self._job_loops = 0
        self._loops_executed = 0
        self._job_estimate = 0
        self._job_elapsed = 0

        spooler = self.context.device.spooler
        if spooler is None:
            return
        self._driver = spooler.driver

        self._queue_len = len(spooler.queue)
        for idx, spool_obj in enumerate(spooler.queue):
            # Idx, Status, Type, Passes, Priority, Runtime, Estimate
            if self._job_active:
                # We already have one...
                # So we just add the time to the remaining...
                self._queue_remaining += spool_obj.estimate_time()
            elif spool_obj.is_running():
                self._queue_pos = idx + 1
                self._job_label = spool_obj.label
                self._job_active = True
                self._job_loops = spool_obj.loops
                self._loops_executed = spool_obj.loops_executed
                self._job_len = len(spool_obj.items)
                self._job_pos = spool_obj.item_index
                self.inspect_job_details(spool_obj)
                self._job_elapsed = time.time() - spool_obj.time_started
                self._job_estimate = spool_obj.estimate_time()
                self._queue_elapsed += self._job_elapsed
                if self._job_estimate > self._job_elapsed:
                    self._queue_remaining = self._job_estimate - self._job_elapsed
                else:
                    if self._job_pos!=0:
                        self._queue_remaining = (
                            self._job_elapsed * self._job_len / self._job_pos
                        )
            else:
                self._queue_elapsed += spool_obj.runtime

        if self._queue_pos > 0:
            msg = _("Queue - Active: {step}, {elapsed}, To Go: {remaining}").format(
                elapsed=timestr(self._queue_elapsed),
                remaining=timestr(self._queue_remaining),
                step=str(self._queue_pos),
                total=str(self._queue_len),
                togo=str(max(0, self._queue_len - self._queue_pos)),
            )
            self._status_text.append(msg)
        if self._job_pos > 0:
            msg = _("Job - Pass {passes}/{passtotal}: {steps} of {steptotal}").format(
                passes=str(self._job_pos),
                passtotal=str(self._job_len),
                steps=str(self._queue_pos),
                steptotal=str(self._queue_len),
            )
            self._status_text.append(msg)

            msg = _("Job-Time: {elapsed} ({estimate})").format(
                elapsed=timestr(self._job_elapsed), estimate=timestr(self._job_estimate)
            )
            self._status_text.append(msg)

        if self._queue_misc is not None and len(self._queue_misc) > 0:
            self._status_text.append(self._queue_misc)

        self.StartPopulation()
        self.SetInformation(self._status_text)
        self.EndPopulation()
        self._needs_generation = False

    def Signal(self, signal, *args):
        if signal == "spooler;queue":
            if len(args) > 0:
                self._queue_len = args[0]
            else:
                self._queue_len = 0
                self._queue_pos = 0
            self._start_time = time.time()
        elif signal == "spooler;update":
            self.GenerateInfos()
        elif signal == "spooler;thread":
            if len(args) > 0:
                value = args[0]
                msg = self.context.get_text_thread_state(value)
                self._queue_misc = msg
            self.GenerateInfos()
