import time
from copy import copy
from math import isinf

import wx

from meerk40t.core.elements.element_types import elem_nodes
from meerk40t.core.laserjob import LaserJob
from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_INCH, Length
from meerk40t.gui.icons import icons8_up_50
from meerk40t.gui.statusbarwidgets.statusbarwidget import StatusBarWidget
from meerk40t.svgelements import Color

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
        self._percentage = -1

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
        self.progress_bar = wx.Gauge(
            self.parent, range=100, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH
        )
        infocolor = wx.Colour(128, 128, 128, 128)
        self.btn_next.SetBackgroundColour(infocolor)
        self.btn_next.Bind(wx.EVT_LEFT_DOWN, self.on_button_next)
        self.btn_next.Bind(wx.EVT_RIGHT_DOWN, self.on_button_prev)

        self.Add(self.info_text, 5, wx.EXPAND, 0)
        self.Add(self.progress_bar, 1, wx.EXPAND, 0)
        self.Add(self.btn_next, 0, wx.EXPAND, 0)
        self.SetActive(self.btn_next, False)
        self.SetActive(self.progress_bar, False)

    def SetPercentage(self, newpercentage):
        self._percentage = int(newpercentage)
        if newpercentage < 0:
            self.progress_bar.SetValue(0)
            self.SetActive(self.progress_bar, False)
        else:
            self.SetActive(self.progress_bar, True)
            self.progress_bar.SetValue(self._percentage)
        self._percentage = newpercentage

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
        self.info_text.SetToolTip(msg)

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

    def Show(self, showit=True):
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

    def covered_area(self, nodes):
        area_with_stroke = 0
        area_without_stroke = 0
        make_raster = self.context.root.lookup("render-op/make_raster")
        if nodes is None or len(nodes) == 0 or not make_raster:
            return 0, 0
        ratio = 0
        dpi = 300
        dots_per_units = dpi / UNITS_PER_INCH
        _mm = float(Length("1mm"))
        data = []
        for node in nodes:
            e = copy(node)
            if hasattr(e, "fill"):
                e.fill = Color("black")
            data.append(e)

        for with_stroke in (True, False):
            no_stroke = True
            for e in data:
                if hasattr(e, "stroke"):
                    no_stroke = False
                    e.stroke = Color("black")
                    if not with_stroke:
                        e.stroke_width = 1
                    e.altered()

            if with_stroke:
                bounds = Node.union_bounds(data, attr="paint_bounds")
            else:
                bounds = Node.union_bounds(data)
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
            new_width = int(width * dots_per_units)
            new_height = int(height * dots_per_units)
            # print(f"Width: {width:.0f} -> {new_width}")
            # print(f"Height: {height:.0f} -> {new_height}")
            keep_ratio = True
            ratio = 0

            all_pixel = new_height * new_width
            if all_pixel > 0:
                image = make_raster(
                    data,
                    bounds=bounds,
                    width=new_width,
                    height=new_height,
                    keep_ratio=keep_ratio,
                )
                white_pixel = sum(
                    image.point(lambda x: 255 if x else 0)
                    .convert("L")
                    .point(bool)
                    .getdata()
                )
                black_pixel = all_pixel - white_pixel
                # print(
                #     f"Mode: {with_stroke}, pixels: {all_pixel}, white={white_pixel}, black={black_pixel}"
                # )
                ratio = black_pixel / all_pixel
                area = (
                    ratio
                    * (bounds[2] - bounds[0])
                    * (bounds[3] - bounds[1])
                    / (_mm * _mm)
                )
                if with_stroke:
                    area_with_stroke = area
                else:
                    area_without_stroke = area
                if no_stroke:
                    # No sense of doing it again
                    if area_without_stroke == 0:
                        area_without_stroke = area_with_stroke
                    break

        # print(f"Area, with: {area_with_stroke:.0f}, without: {area_without_stroke:.0f}")
        return area_with_stroke, area_without_stroke

    def calculate_infos(self):
        msg = ""
        if self._info_active:
            elements = self.context.elements
            ct = 0
            total_area = 0
            total_length = 0
            _mm = float(Length("1mm"))
            mydata = list(elements.flat(types=elem_nodes, emphasized=True))
            total_area, second_area = self.covered_area(mydata)
            for e in mydata:
                ct += 1
                if hasattr(e, "as_path"):
                    path = e.as_path()
                    this_length = path.length()
                else:
                    this_length = 0
                total_length += this_length

            if ct > 0:
                total_length = total_length / _mm
                msg = f"# = {ct}, A = {total_area:.1f} mm², D = {total_length:.1f} mm"
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
        self.fontsize = 7
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
        self._job_remaining = 0
        # How often do I want to have an update?
        self._last_invokation = 0
        self._invokation_delta = 2  # Every 2 seconds max
        self._driver = None

    def Show(self, showit=True):
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
            if isinf(t):
                runtime = "∞"
            else:
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
        self._job_remaining = 0

        percentage = -1

        spooler = self.context.device.spooler
        if spooler is None:
            self.StartPopulation()
            self.SetPercentage(percentage)
            self.SetInformation(self._status_text)
            self.EndPopulation()
            return
        self._driver = spooler.driver

        self._queue_len = len(spooler.queue)
        # Let's establish the start time, as the queue grows and shrinks
        # we only reset the start_time if the queue became empty.
        if self._queue_len == 0:
            self._start_time = 0
        else:
            if self._start_time == 0:
                self._start_time = time.time()

        for idx, spool_obj in enumerate(spooler.queue):
            # Idx, Status, Type, Passes, Priority, Runtime, Estimate
            if self._job_active:
                # We already have one, so these are the jobs still in the queue
                # So we just add the time to the remaining...
                self._queue_remaining += spool_obj.estimate_time()
            elif spool_obj.is_running() and isinstance(spool_obj, LaserJob):
                self._queue_pos = idx + 1
                self._job_label = spool_obj.label
                self._job_active = True
                self._start_time = spool_obj.time_started
                self._job_loops = spool_obj.loops
                self._loops_executed = spool_obj.loops_executed
                self._job_len = len(spool_obj.items)
                self._job_pos = spool_obj.item_index
                self.inspect_job_details(spool_obj)
                self._job_elapsed = time.time() - spool_obj.time_started
                self._job_estimate = spool_obj.estimate_time()
                self._queue_elapsed += self._job_elapsed
                if self._job_estimate > self._job_elapsed:
                    self._job_remaining = self._job_estimate - self._job_elapsed
                else:
                    if self._job_pos != 0:
                        self._job_remaining = (
                            self._job_elapsed * self._job_len / self._job_pos
                        )
                self._queue_remaining += self._job_remaining
                if self._job_len > 0:
                    percentage = min(100, 100 * self._job_pos / self._job_len)
            else:
                # Already executed jobs
                self._queue_elapsed += spool_obj.runtime

        if self._queue_pos > 0:
            msg = _("Burn-Time: {elapsed}, Remaining: {total}, {remaining}").format(
                elapsed=timestr(time.time() - self._start_time),
                remaining=timestr(self._queue_remaining),
                step=str(self._queue_pos),
                total=str(self._queue_len),
                togo=str(max(0, self._queue_len - self._queue_pos)),
            )
            self._status_text.append(msg)
        if self._job_pos > 0:
            msg = _("Job: {steps}/{steptotal}, {elapsed} [{remaining}]").format(
                steps=str(self._job_pos),
                steptotal=str(self._job_len),
                elapsed=timestr(self._job_elapsed),
                estimate=timestr(self._job_estimate),
                remaining=timestr(self._job_remaining),
            )
            self._status_text.append(msg)

        if self._queue_misc is not None and len(self._queue_misc) > 0:
            self._status_text.append(self._queue_misc)

        self.StartPopulation()
        self.SetPercentage(percentage)
        self.SetInformation(self._status_text)
        self.EndPopulation()
        self._needs_generation = False

    def Signal(self, signal, *args):
        if signal == "spooler;queue":
            if len(args) > 0:
                if isinstance(args[0], (tuple, list)):
                    self._queue_len = args[0][0]
                else:
                    self._queue_len = args[0]
            else:
                self._queue_len = 0
                self._queue_pos = 0
            if self._queue_len == 0:
                self._last_invokation = 0  # Force display
            self.GenerateInfos()
        elif signal == "spooler;update":
            self.GenerateInfos()
        elif signal == "spooler;thread":
            if len(args) > 0:
                value = args[0]
                msg = self.context.get_text_thread_state(value)
                self._queue_misc = msg
            self.GenerateInfos()
        elif signal == "spooler;completed":
            self._last_invokation = 0  # Force display
            self.GenerateInfos()
