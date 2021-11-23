import math

import wx

from .wxutils import disable_window
from ..core.cutcode import CutCode, LineCut
from ..kernel import Job, signal_listener
from ..svgelements import Matrix
from .icons import (
    icons8_laser_beam_hazard2_50,
    icons8_pause_50,
    icons8_play_50,
    icons8_route_50,
)
from .laserrender import LaserRender
from .mwindow import MWindow
from .scene.scene import ScenePanel, Widget
from .scene.scenewidgets import GridWidget

_ = wx.GetTranslation

MILS_IN_MM = 39.3701


class SimulationPanel(wx.Panel, Job):
    def __init__(self, *args, context=None, plan_name=None, auto_clear=True, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.plan_name = plan_name
        self.auto_clear = auto_clear

        Job.__init__(self)
        self.job_name = "simulate"
        self.run_main = True
        self.process = self.animate_sim
        self.interval = 0.1
        if plan_name:
            cutplan = self.context.planner.get_or_make_plan(plan_name)
        else:
            cutplan = self.context.planner.default_plan
        self.plan_name = cutplan.name
        self.operations = cutplan.plan
        self.cutcode = CutCode()

        for c in self.operations:
            if isinstance(c, CutCode):
                self.cutcode.extend(c)
        self.cutcode = CutCode(self.cutcode.flat())
        self.max = max(len(self.cutcode), 0) + 1
        self.progress = self.max

        self.view_pane = ScenePanel(
            self.context,
            self,
            scene_name="SimScene",
            style=wx.EXPAND,
        )
        self.view_pane.SetCanFocus(False)
        self.widget_scene = self.view_pane.scene

        self.slider_progress = wx.Slider(self, wx.ID_ANY, self.max, 0, self.max)
        self.slider_progress.SetFocus()
        self.text_distance_laser = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.text_distance_travel = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.text_distance_total = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.text_time_laser = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_time_travel = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_time_total = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.button_play = wx.Button(self, wx.ID_ANY, "")
        self.slider_playbackspeed = wx.Slider(self, wx.ID_ANY, 180, 0, 310)
        self.text_playback_speed = wx.TextCtrl(
            self, wx.ID_ANY, "100%", style=wx.TE_READONLY
        )

        self.available_spoolers = list(self.context.lookup_all("spooler"))
        self.selected_spooler = self.context.device.spooler
        index = -1
        for i, s in enumerate(self.available_spoolers):
            if s is self.selected_spooler:
                index = i
                break
        self.connected_name = self.selected_spooler.name if self.selected_spooler is not None else "None"
        spools = [s.label for s in self.available_spoolers]

        self.combo_device = wx.ComboBox(
            self, wx.ID_ANY, choices=spools, style=wx.CB_DROPDOWN
        )
        self.combo_device.SetSelection(index)
        self.button_spool = wx.Button(self, wx.ID_ANY, "Send to Laser")

        self.__set_properties()
        self.__do_layout()

        self.matrix = Matrix()

        self.previous_window_position = None
        self.previous_scene_position = None
        self._Buffer = None

        self.Bind(wx.EVT_SLIDER, self.on_slider_progress, self.slider_progress)
        self.Bind(wx.EVT_BUTTON, self.on_button_play, self.button_play)
        self.Bind(wx.EVT_SLIDER, self.on_slider_playback, self.slider_playbackspeed)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_device, self.combo_device)
        self.Bind(wx.EVT_BUTTON, self.on_button_spool, self.button_spool)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_mouse_right_down)
        # end wxGlade

        self.widget_scene.add_scenewidget(SimulationWidget(self.widget_scene, self))
        self.widget_scene.add_scenewidget(
            SimulationTravelWidget(self.widget_scene, self)
        )
        self.widget_scene.add_scenewidget(GridWidget(self.widget_scene))
        self.reticle = SimReticleWidget(self.widget_scene, self)
        self.widget_scene.add_interfacewidget(self.reticle)
        self.running = False
        if index == -1:
            disable_window(self)

    def __set_properties(self):
        self.text_distance_laser.SetToolTip(_("Time Estimate: Lasering Time"))
        self.text_distance_travel.SetToolTip(_("Time Estimate: Traveling Time"))
        self.text_distance_total.SetToolTip(_("Time Estimate: Total Time"))
        self.text_time_laser.SetToolTip(_("Time Estimate: Lasering Time"))
        self.text_time_travel.SetToolTip(_("Time Estimate: Traveling Time"))
        self.text_time_total.SetToolTip(_("Time Estimate: Total Time"))
        self.button_play.SetBitmap(icons8_play_50.GetBitmap())
        self.text_playback_speed.SetMinSize((55, 23))
        self.combo_device.SetToolTip(_("Select the device"))
        self.button_spool.SetFont(
            wx.Font(
                18,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        self.button_spool.SetBitmap(icons8_route_50.GetBitmap())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Simulation.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6 = wx.BoxSizer(wx.VERTICAL)
        sizer_4 = wx.BoxSizer(wx.VERTICAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_time = wx.BoxSizer(wx.HORIZONTAL)
        sizer_total_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Total Time")), wx.VERTICAL
        )
        sizer_travel_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Travel Time")), wx.VERTICAL
        )
        sizer_laser_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Laser Time")), wx.VERTICAL
        )
        sizer_distance = wx.BoxSizer(wx.HORIZONTAL)
        sizer_total_distance = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Total Distance")), wx.VERTICAL
        )
        sizer_travel_distance = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Travel Distance")), wx.VERTICAL
        )
        sizer_laser_distance = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Laser Distance")), wx.VERTICAL
        )
        sizer_1.Add(self.view_pane, 3, wx.EXPAND, 0)
        sizer_2.Add(self.slider_progress, 0, wx.EXPAND, 0)
        sizer_laser_distance.Add(self.text_distance_laser, 0, wx.EXPAND, 0)
        sizer_distance.Add(sizer_laser_distance, 1, wx.EXPAND, 0)
        sizer_travel_distance.Add(self.text_distance_travel, 0, wx.EXPAND, 0)
        sizer_distance.Add(sizer_travel_distance, 1, wx.EXPAND, 0)
        sizer_total_distance.Add(self.text_distance_total, 0, wx.EXPAND, 0)
        sizer_distance.Add(sizer_total_distance, 1, wx.EXPAND, 0)
        sizer_2.Add(sizer_distance, 0, wx.EXPAND, 0)
        sizer_laser_time.Add(self.text_time_laser, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_laser_time, 1, wx.EXPAND, 0)
        sizer_travel_time.Add(self.text_time_travel, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_travel_time, 1, wx.EXPAND, 0)
        sizer_total_time.Add(self.text_time_total, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_total_time, 1, wx.EXPAND, 0)
        sizer_2.Add(sizer_time, 0, wx.EXPAND, 0)
        sizer_3.Add(self.button_play, 0, 0, 0)
        sizer_4.Add(self.slider_playbackspeed, 0, wx.EXPAND, 0)
        label_playback_speed = wx.StaticText(self, wx.ID_ANY, _("Playback Speed"))
        sizer_5.Add(label_playback_speed, 2, 0, 0)
        sizer_5.Add(self.text_playback_speed, 1, 0, 0)
        sizer_4.Add(sizer_5, 1, wx.EXPAND, 0)
        sizer_3.Add(sizer_4, 1, wx.EXPAND, 0)
        sizer_6.Add(self.combo_device, 0, wx.EXPAND, 0)
        sizer_6.Add(self.button_spool, 0, wx.EXPAND, 0)
        sizer_3.Add(sizer_6, 1, wx.EXPAND, 0)
        sizer_2.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def on_mouse_right_down(self, event=None):
        gui = self
        menu = wx.Menu()
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context(
                "plan%s sublist %d -1\n" % (self.plan_name, self.progress)
            ),
            menu.Append(
                wx.ID_ANY,
                _("Delete cuts before"),
                _("Delete all cuts before the current position in Simulation"),
            ),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context(
                "plan%s sublist 0 %d\n" % (self.plan_name, self.progress)
            ),
            menu.Append(
                wx.ID_ANY,
                _("Delete cuts after"),
                _("Delete all cuts after the current position in Simulation"),
            ),
        )
        if menu.MenuItemCount != 0:
            gui.PopupMenu(menu)
            menu.Destroy()

    @signal_listener("plan")
    def on_plan_change(self, origin, plan_name, status):
        if plan_name == self.plan_name:
            # Refresh cutcode
            self.cutcode = CutCode()

            for c in self.operations:
                if isinstance(c, CutCode):
                    self.cutcode.extend(c)
            self.cutcode = CutCode(self.cutcode.flat())
            self.max = max(len(self.cutcode), 0) + 1
            self.progress = self.max
            self.slider_progress.SetMin(0)
            self.slider_progress.SetMax(self.max)
            self.slider_progress.SetValue(self.max)
            self.request_refresh()

    def pane_show(self):
        self.context.setting(str, "units_name", "mm")
        self.context.setting(int, "units_marks", 10)
        self.context.setting(int, "units_index", 0)
        self.context.setting(float, "units_convert", MILS_IN_MM)

        bbox = (
            0,
            0,
            self.context.device.bedwidth,
            self.context.device.bedheight,
        )
        self.widget_scene.widget_root.focus_viewport_scene(
            bbox, self.view_pane.Size, 0.1
        )
        travel = self.cutcode.length_travel()
        cuts = self.cutcode.length_cut()
        travel /= MILS_IN_MM
        cuts /= MILS_IN_MM
        self.text_distance_travel.SetValue("%.2fmm" % travel)
        self.text_distance_laser.SetValue("%.2fmm" % cuts)
        self.text_distance_total.SetValue("%.2fmm" % (travel + cuts))

        extra = self.cutcode.extra_time()

        try:
            time_travel = travel / self.cutcode.travel_speed
            t_hours = time_travel // 3600
            t_mins = (time_travel % 3600) // 60
            t_seconds = time_travel % 60
            self.text_time_travel.SetValue(
                "%d:%02d:%02d" % (t_hours, t_mins, t_seconds)
            )
            time_cuts = self.cutcode.duration_cut()
            t_hours = time_cuts // 3600
            t_mins = (time_cuts % 3600) // 60
            t_seconds = time_cuts % 60
            self.text_time_laser.SetValue("%d:%02d:%02d" % (t_hours, t_mins, t_seconds))
            time_total = time_travel + time_cuts + extra
            t_hours = time_total // 3600
            t_mins = (time_total % 3600) // 60
            t_seconds = time_total % 60
            self.text_time_total.SetValue("%d:%02d:%02d" % (t_hours, t_mins, t_seconds))
        except ZeroDivisionError:
            pass

    def pane_hide(self):
        if self.auto_clear:
            self.context("plan%s clear\n" % self.plan_name)
        self.context.close("SimScene")
        self.context.unschedule(self)
        self.running = False

    @signal_listener("refresh_scene")
    def on_refresh_scene(self, origin, scene_name=None, *args):
        """
        Called by 'refresh_scene' change. To refresh tree.
        :param origin: the path of the originating signal
        :param args:
        :return:
        """
        if scene_name == "SimScene":
            self.request_refresh()

    def request_refresh(self, *args):
        self.widget_scene.request_refresh(*args)

    def on_slider_progress(self, event=None):  # wxGlade: Simulation.<event_handler>
        self.progress = min(self.slider_progress.GetValue(), self.max)
        self.context.signal("refresh_scene", self.widget_scene.name)

    def _start(self):
        self.button_play.SetBitmap(icons8_pause_50.GetBitmap())
        self.context.schedule(self)
        self.running = True

    def _stop(self):
        self.button_play.SetBitmap(icons8_play_50.GetBitmap())
        self.context.unschedule(self)
        self.running = False

    def on_button_play(self, event=None):  # wxGlade: Simulation.<event_handler>
        if self.running:
            self._stop()
            return
        if self.progress >= self.max:
            self.progress = 0
            self.slider_progress.SetValue(self.progress)
        self._start()

    def animate_sim(self, event=None):
        self.progress += 1
        if self.progress >= self.max:
            self.progress = self.max
            self._stop()
        else:
            self.context.signal("refresh_scene", self.widget_scene.name)
        self.slider_progress.SetValue(self.progress)

    def on_slider_playback(self, event=None):  # wxGlade: Simulation.<event_handler>
        # Slider is now pseudo logarithmic in scale varying from 1% to 5,000%.

        value = self.slider_playbackspeed.GetValue()
        value = int((10.0 ** (value // 90)) * (1.0 + float(value % 90) / 10.0))
        self.interval = 0.1 * 100.0 / float(value)

        self.text_playback_speed.SetValue("%d%%" % value)

    def on_combo_device(self, event=None):  # wxGlade: Preview.<event_handler>
        index = self.combo_device.GetSelection()
        self.selected_spooler = self.available_spoolers[index]

    def on_button_spool(self, event=None):  # wxGlade: Simulation.<event_handler>
        self.context("plan%s spool%s\n" % (self.plan_name, self.connected_name))
        self.context("window close Simulation\n")


class SimulationWidget(Widget):
    """
    The simulation widget is responsible for rendering the cutcode to the scene. This should be
    done such that both progress of 0 and 1 render nothing and items begin to draw at 2.
    """

    def __init__(self, scene, sim):
        Widget.__init__(self, scene, all=False)
        self.renderer = LaserRender(self.scene.context)
        self.sim = sim

    def process_draw(self, gc: wx.GraphicsContext):
        if self.sim.progress > 1:
            if self.sim.progress < self.sim.max:
                sim_cut = self.sim.cutcode[: self.sim.progress - 1]
            else:
                sim_cut = self.sim.cutcode
            self.renderer.draw_cutcode(sim_cut, gc, 0, 0)


class SimulationTravelWidget(Widget):
    """
    The simulation Travel Widget is responsible for the background of dotted lines and arrows
    within the simulation scene.
    """

    def __init__(self, scene, sim):
        Widget.__init__(self, scene, all=False)
        self.sim = sim
        self.starts = list()
        self.ends = list()
        self.pos = list()
        self.starts.append(wx.Point2D(0, 0))
        self.ends.append(wx.Point2D(0, 0))
        prev = None
        for i, curr in enumerate(list(self.sim.cutcode)):
            if prev is not None:
                if prev.end() != curr.start():
                    start = wx.Point2D(*prev.end())
                    end = wx.Point2D(*curr.start())
                    self.starts.append(start)
                    self.ends.append(end)
                    s = complex(start[0], start[1])
                    e = complex(end[0], end[1])
                    d = abs(s - e)
                    if d >= 127:
                        for p in [0.75]:
                            m = p * (e - s) + s
                            ang = math.atan2((s - e).imag, (s - e).real)
                            # arrow_size = d / 10.0
                            arrow_size = 50
                            m0 = m + complex(
                                math.cos(ang + math.tau / 10) * arrow_size,
                                math.sin(ang + math.tau / 10) * arrow_size,
                            )
                            m1 = m + complex(
                                math.cos(ang - math.tau / 10) * arrow_size,
                                math.sin(ang - math.tau / 10) * arrow_size,
                            )
                            m = wx.Point2D(m.real, m.imag)
                            self.starts.append(m)
                            self.ends.append(wx.Point2D(m0.real, m0.imag))
                            self.starts.append(m)
                            self.ends.append(wx.Point2D(m1.real, m1.imag))
            self.pos.append(len(self.starts))
            prev = curr

    def process_draw(self, gc: wx.GraphicsContext):
        if len(self.pos):
            if self.sim.progress < self.sim.max:
                pos = self.pos[self.sim.progress - 1]
            else:
                pos = self.pos[-1]
            if pos > 1:
                starts = self.starts[:pos]
                ends = self.ends[:pos]
                gc.SetPen(wx.BLACK_DASHED_PEN)
                gc.StrokeLineSegments(starts, ends)


class SimReticleWidget(Widget):
    """
    The simulation Reticle widget is responsible for rendering the three green circles.
    The position at 0 should be 0,0. At 1 the start position. And at all other positions
    the end of the current cut object.
    """

    def __init__(self, scene, sim):
        Widget.__init__(self, scene, all=False)
        self.sim = sim

    def process_draw(self, gc):
        x = 0
        y = 0
        if (
            self.sim.progress > 0
            and self.sim.cutcode is not None
            and len(self.sim.cutcode)
        ):
            if self.sim.progress != self.sim.max:
                pos = self.sim.cutcode[self.sim.progress - 1].start()
            else:
                pos = self.sim.cutcode[self.sim.progress - 2].end()
            x = pos[0]
            y = pos[1]

        try:
            # Draw Reticle
            gc.SetPen(wx.Pen(wx.Colour(0, 255, 0, alpha=127)))
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            x, y = self.scene.convert_scene_to_window([x, y])
            gc.DrawEllipse(x - 5, y - 5, 10, 10)
            gc.DrawEllipse(x - 10, y - 10, 20, 20)
            gc.DrawEllipse(x - 20, y - 20, 40, 40)
        except AttributeError:
            pass


class Simulation(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(706, 755, *args, **kwds)
        if len(args) > 3:
            plan_name = args[3]
        else:
            plan_name = None
        if len(args) > 4:
            auto_clear = bool(int(args[4]))
        else:
            auto_clear = True

        self.panel = SimulationPanel(
            self,
            wx.ID_ANY,
            context=self.context,
            plan_name=plan_name,
            auto_clear=auto_clear,
        )
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_laser_beam_hazard2_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Simulation"))

    @staticmethod
    def sub_register(kernel):

        def open_simulator(v=None):
            with wx.BusyInfo(_("Preparing simulation...")):
                kernel.console(
                    "plan0 copy preprocess validate blob preopt optimize\nwindow toggle Simulation 0\n"
                ),

        kernel.register(
            "button/project/Simulation",
            {
                "label": _("Simulate"),
                "icon": icons8_laser_beam_hazard2_50,
                "tip": _("Simulate the current laser job"),
                "action": open_simulator
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()
