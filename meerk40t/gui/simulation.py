import math
import platform

import wx

from meerk40t.kernel import Job, signal_listener

from ..core.cutcode import CutCode
from ..svgelements import Matrix
from .choicepropertypanel import ChoicePropertyPanel
from .icons import (
    STD_ICON_SIZE,
    icons8_laser_beam_hazard2_50,
    icons8_pause_50,
    icons8_play_50,
    icons8_route_50,
)
from .laserrender import DRAW_MODE_BACKGROUND, LaserRender
from .mwindow import MWindow
from .scene.scenepanel import ScenePanel
from .scene.widget import Widget
from .scenewidgets.bedwidget import BedWidget
from .scenewidgets.gridwidget import GridWidget
from .wxutils import disable_window

_ = wx.GetTranslation


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

        # poor mans slide out
        self.btn_slide_options = wx.Button(self, wx.ID_ANY, "<")
        self.btn_slide_options.Bind(wx.EVT_BUTTON, self.slide_out)
        choices = self.context.lookup("choices/optimize")[:7]
        self.panel_optimize = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=choices, scrolling=False
        )
        self.btn_redo_it = wx.Button(self, wx.ID_ANY, _("Recalculate"))
        self.btn_redo_it.Bind(wx.EVT_BUTTON, self.on_redo_it)

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
        self.text_distance_laser_step = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.text_distance_travel_step = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.text_distance_total_step = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.text_time_laser_step = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.text_time_travel_step = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.text_time_total_step = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.button_play = wx.Button(self, wx.ID_ANY, "")
        self.slider_playbackspeed = wx.Slider(self, wx.ID_ANY, 180, 0, 310)
        self.text_playback_speed = wx.TextCtrl(
            self, wx.ID_ANY, "100%", style=wx.TE_READONLY
        )

        self.available_devices = list(self.context.kernel.services("device"))
        self.selected_device = self.context.device
        index = -1
        for i, s in enumerate(self.available_devices):
            if s is self.selected_device:
                index = i
                break
        spools = [s.label for s in self.available_devices]

        self.combo_device = wx.ComboBox(
            self, wx.ID_ANY, choices=spools, style=wx.CB_DROPDOWN
        )
        self.combo_device.SetSelection(index)
        self.button_spool = wx.Button(self, wx.ID_ANY, _("Send to Laser"))
        self._slided_in = None

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
        self.view_pane.scene_panel.Bind(wx.EVT_RIGHT_DOWN, self.on_mouse_right_down)
        # end wxGlade

        self.widget_scene.add_scenewidget(SimulationWidget(self.widget_scene, self))
        self.sim_travel = SimulationTravelWidget(self.widget_scene, self)
        self.widget_scene.add_scenewidget(self.sim_travel)
        # Don't let grid resize itself
        self.widget_scene.auto_tick = False
        if self.context.units_name == "mm":
            self.widget_scene.tick_distance = 10  # mm
        elif self.context.units_name == "cm":
            self.widget_scene.tick_distance = 1
        elif self.context.units_name == "inch":
            self.widget_scene.tick_distance = 0.5
        elif self.context.units_name == "mil":
            self.widget_scene.tick_distance = 500
        # print (f"{self.widget_scene.tick_distance} {self.context.units_name}")
        self.widget_scene.add_scenewidget(
            GridWidget(self.widget_scene, name="Simulation", suppress_labels=True)
        )
        self.widget_scene.add_scenewidget(
            BedWidget(self.widget_scene, name="Simulation")
        )
        self.widget_scene.add_interfacewidget(SimReticleWidget(self.widget_scene, self))
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
        self.text_distance_laser.SetMinSize((35, -1))
        self.text_distance_laser_step.SetMinSize((35, -1))
        self.text_distance_total.SetMinSize((35, -1))
        self.text_distance_total_step.SetMinSize((35, -1))
        self.text_distance_travel.SetMinSize((35, -1))
        self.text_distance_travel_step.SetMinSize((35, -1))
        self.text_time_laser.SetMinSize((35, -1))
        self.text_time_laser_step.SetMinSize((35, -1))
        self.text_time_total.SetMinSize((35, -1))
        self.text_time_total_step.SetMinSize((35, -1))
        self.text_time_travel.SetMinSize((35, -1))
        self.text_time_travel_step.SetMinSize((35, -1))
        v_sizer_main = wx.BoxSizer(wx.VERTICAL)
        h_sizer_scroll = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer_text_1 = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer_text_2 = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)

        sizer_6 = wx.BoxSizer(wx.VERTICAL)
        sizer_4 = wx.BoxSizer(wx.VERTICAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_total_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Total Time")), wx.HORIZONTAL
        )
        sizer_travel_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Travel Time")), wx.HORIZONTAL
        )
        sizer_laser_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Laser Time")), wx.HORIZONTAL
        )
        sizer_total_distance = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Total Distance")), wx.HORIZONTAL
        )
        sizer_travel_distance = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Travel Distance")), wx.HORIZONTAL
        )
        sizer_laser_distance = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Laser Distance")), wx.HORIZONTAL
        )
        # +--------+---+-------+
        # |   P    |   | Optim |
        # |   R    |   |       |
        # |   E    |   |Options|
        # |   V    | > |       |
        # |   I    |   |       |
        # |   E    |   +-------+
        # |   W    |   |Refresh|
        # +--------+---+-------+
        # Linux requires a minimum  height / width to display a text inside a button
        system = platform.system()
        if system == "Darwin":
            mysize = 40
        elif system == "Windows":
            mysize = 23
        elif system == "Linux":
            mysize = 40
        else:
            mysize = 20
        self.btn_slide_options.SetMinSize(wx.Size(mysize, -1))
        self.voption_sizer = wx.BoxSizer(wx.VERTICAL)
        self.voption_sizer.Add(self.panel_optimize, 1, wx.EXPAND, 0)
        self.voption_sizer.Add(self.btn_redo_it, 0, wx.EXPAND, 0)

        self.hscene_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.hscene_sizer.Add(self.view_pane, 2, wx.EXPAND, 0)
        self.hscene_sizer.Add(self.btn_slide_options, 0, wx.EXPAND, 0)
        self.hscene_sizer.Add(self.voption_sizer, 1, wx.EXPAND, 0)

        h_sizer_scroll.Add(self.slider_progress, 1, wx.EXPAND, 0)

        sizer_laser_distance.Add(self.text_distance_laser_step, 1, wx.EXPAND, 0)
        sizer_laser_distance.Add(self.text_distance_laser, 1, wx.EXPAND, 0)
        h_sizer_text_1.Add(sizer_laser_distance, 1, wx.EXPAND, 0)

        sizer_travel_distance.Add(self.text_distance_travel_step, 1, wx.EXPAND, 0)
        sizer_travel_distance.Add(self.text_distance_travel, 1, wx.EXPAND, 0)
        h_sizer_text_1.Add(sizer_travel_distance, 1, wx.EXPAND, 0)

        sizer_total_distance.Add(self.text_distance_total_step, 1, wx.EXPAND, 0)
        sizer_total_distance.Add(self.text_distance_total, 1, wx.EXPAND, 0)
        h_sizer_text_1.Add(sizer_total_distance, 1, wx.EXPAND, 0)

        sizer_laser_time.Add(self.text_time_laser_step, 1, wx.EXPAND, 0)
        sizer_laser_time.Add(self.text_time_laser, 1, wx.EXPAND, 0)
        h_sizer_text_2.Add(sizer_laser_time, 1, wx.EXPAND, 0)

        sizer_travel_time.Add(self.text_time_travel_step, 1, wx.EXPAND, 0)
        sizer_travel_time.Add(self.text_time_travel, 1, wx.EXPAND, 0)
        h_sizer_text_2.Add(sizer_travel_time, 1, wx.EXPAND, 0)

        sizer_total_time.Add(self.text_time_total_step, 1, wx.EXPAND, 0)
        sizer_total_time.Add(self.text_time_total, 1, wx.EXPAND, 0)
        h_sizer_text_2.Add(sizer_total_time, 1, wx.EXPAND, 0)

        h_sizer_buttons.Add(self.button_play, 0, 0, 0)
        sizer_4.Add(self.slider_playbackspeed, 0, wx.EXPAND, 0)
        label_playback_speed = wx.StaticText(self, wx.ID_ANY, _("Playback Speed"))
        sizer_5.Add(label_playback_speed, 2, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_5.Add(self.text_playback_speed, 1, wx.EXPAND, 0)
        sizer_4.Add(sizer_5, 0, wx.EXPAND, 0)
        h_sizer_buttons.Add(sizer_4, 1, wx.EXPAND, 0)
        sizer_6.Add(self.combo_device, 0, wx.EXPAND, 0)
        sizer_6.Add(self.button_spool, 0, wx.EXPAND, 0)
        h_sizer_buttons.Add(sizer_6, 1, wx.EXPAND, 0)

        v_sizer_main.Add(self.hscene_sizer, 1, wx.EXPAND, 0)
        v_sizer_main.Add(h_sizer_scroll, 0, wx.EXPAND, 0)
        v_sizer_main.Add(h_sizer_text_1, 0, wx.EXPAND, 0)
        v_sizer_main.Add(h_sizer_text_2, 0, wx.EXPAND, 0)
        v_sizer_main.Add(h_sizer_buttons, 0, wx.EXPAND, 0)
        self.SetSizer(v_sizer_main)
        self.slided_in = True  # Hide initially
        self.Layout()
        # end wxGlade

    # Manages the display, non-display of the optimisation-options
    @property
    def slided_in(self):
        return self._slided_in

    @slided_in.setter
    def slided_in(self, newvalue):
        self._slided_in = newvalue
        if newvalue:
            # Slided in ->
            self.hscene_sizer.Show(sizer=self.voption_sizer, show=False, recursive=True)
            self.voption_sizer.Layout()
            self.btn_slide_options.SetLabel("<")
            self.hscene_sizer.Layout()
            self.Layout()
        else:
            # Slided out ->
            self.hscene_sizer.Show(sizer=self.voption_sizer, show=True, recursive=True)
            self.voption_sizer.Layout()
            self.btn_slide_options.SetLabel(">")
            self.hscene_sizer.Layout()
            self.Layout()

    def toggle_background(self, event):
        """
        Toggle the draw mode for the background
        """
        self.widget_scene.context.draw_mode ^= DRAW_MODE_BACKGROUND
        self.widget_scene.request_refresh()

    def toggle_grid(self, gridtype):
        if gridtype == "primary":
            self.widget_scene.draw_grid_primary = (
                not self.widget_scene.draw_grid_primary
            )
        elif gridtype == "secondary":
            self.widget_scene.draw_grid_secondary = (
                not self.widget_scene.draw_grid_secondary
            )
        elif gridtype == "circular":
            self.widget_scene.draw_grid_circular = (
                not self.widget_scene.draw_grid_circular
            )
        self.widget_scene.request_refresh()

    def toggle_grid_p(self, event):
        self.toggle_grid("primary")

    def toggle_grid_s(self, event):
        self.toggle_grid("secondary")

    def toggle_grid_c(self, event):
        self.toggle_grid("circular")

    def remove_background(self, event):
        self.widget_scene._signal_widget(
            self.widget_scene.widget_root, "background", None
        )
        self.widget_scene.request_refresh()

    def fit_scene_to_panel(self):
        bbox = self.context.device.bbox()
        self.widget_scene.widget_root.focus_viewport_scene(
            bbox, self.view_pane.Size, 0.1
        )
        self.widget_scene.request_refresh()

    def on_mouse_right_down(self, event=None):
        gui = self
        menu = wx.Menu()
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context(
                f"plan{self.plan_name} sublist {self.progress} -1\n"
            ),
            menu.Append(
                wx.ID_ANY,
                _("Delete cuts before"),
                _("Delete all cuts before the current position in Simulation"),
            ),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.context(f"plan{self.plan_name} sublist 0 {self.progress}\n"),
            menu.Append(
                wx.ID_ANY,
                _("Delete cuts after"),
                _("Delete all cuts after the current position in Simulation"),
            ),
        )
        menu.AppendSeparator()
        id1 = menu.Append(
            wx.ID_ANY,
            _("Show Background"),
            _("Display the background picture in the Simulation pane"),
            wx.ITEM_CHECK,
        )
        self.Bind(wx.EVT_MENU, self.toggle_background, id=id1.GetId())
        menu.Check(
            id1.GetId(),
            (self.widget_scene.context.draw_mode & DRAW_MODE_BACKGROUND == 0),
        )
        id2 = menu.Append(
            wx.ID_ANY,
            _("Show Primary Grid"),
            _("Display the primary grid in the Simulation pane"),
            wx.ITEM_CHECK,
        )
        self.Bind(wx.EVT_MENU, self.toggle_grid_p, id=id2.GetId())
        menu.Check(id2.GetId(), self.widget_scene.draw_grid_primary)
        id3 = menu.Append(
            wx.ID_ANY,
            _("Show Secondary Grid"),
            _("Display the secondary grid in the Simulation pane"),
            wx.ITEM_CHECK,
        )
        self.Bind(wx.EVT_MENU, self.toggle_grid_s, id=id3.GetId())
        menu.Check(id3.GetId(), self.widget_scene.draw_grid_secondary)
        id4 = menu.Append(
            wx.ID_ANY,
            _("Show Circular Grid"),
            _("Display the circular grid in the Simulation pane"),
            wx.ITEM_CHECK,
        )
        self.Bind(wx.EVT_MENU, self.toggle_grid_c, id=id4.GetId())
        menu.Check(id4.GetId(), self.widget_scene.draw_grid_circular)
        if self.widget_scene.has_background:
            menu.AppendSeparator()
            id5 = menu.Append(wx.ID_ANY, _("Remove Background"), "")
            self.Bind(wx.EVT_MENU, self.remove_background, id=id5.GetId())
        menu.AppendSeparator()
        self.Bind(
            wx.EVT_MENU,
            lambda e: self.fit_scene_to_panel(),
            menu.Append(
                wx.ID_ANY,
                _("Zoom to Bed"),
                _("View the whole laser bed"),
            ),
        )

        if menu.MenuItemCount != 0:
            gui.PopupMenu(menu)
            menu.Destroy()

    def _refresh_simulated_plan(self):
        # Stop animation
        if self.running:
            self._stop()
            return
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
        self.sim_travel.initvars()
        self.update_fields()
        self.request_refresh()

    @signal_listener("activate;device")
    def on_activate_device(self, origin, device):
        self.available_devices = self.context.kernel.services("device")
        self.selected_device = self.context.device
        spools = []
        index = -1
        for i, s in enumerate(self.available_devices):
            if s is self.selected_device:
                index = i
                break
        spools = [s.label for s in self.available_devices]
        self.combo_device.Clear()
        self.combo_device.SetItems(spools)
        self.combo_device.SetSelection(index)
        self.on_combo_device(None)

    @signal_listener("plan")
    def on_plan_change(self, origin, plan_name, status):
        if plan_name == self.plan_name:
            self._refresh_simulated_plan()

    def update_fields(self):
        step = self.progress

        ###################
        # UPDATE POSITIONAL
        ###################

        mm = self.cutcode.settings.get("native_mm", 39.3701)
        travel_mm = self.cutcode.length_travel(stop_at=step) / mm
        cuts_mm = self.cutcode.length_cut(stop_at=step) / mm
        self.text_distance_travel_step.SetValue(f"{travel_mm:.2f}mm")
        self.text_distance_laser_step.SetValue(f"{cuts_mm:.2f}mm")
        self.text_distance_total_step.SetValue(f"{travel_mm + cuts_mm:.2f}mm")
        try:
            time_travel = self.cutcode.duration_travel(step)
            t_hours = int(time_travel // 3600)
            t_mins = int((time_travel % 3600) // 60)
            t_seconds = int(time_travel % 60)
            self.text_time_travel_step.SetValue(
                f"{int(t_hours)}:{int(t_mins):02d}:{int(t_seconds):02d}"
            )
        except ZeroDivisionError:
            time_travel = 0
        try:
            time_cuts = self.cutcode.duration_cut(stop_at=step)
            t_hours = int(time_cuts // 3600)
            t_mins = int((time_cuts % 3600) // 60)
            t_seconds = int(time_cuts % 60)
            self.text_time_laser_step.SetValue(
                f"{int(t_hours)}:{int(t_mins):02d}:{int(t_seconds):02d}"
            )
        except ZeroDivisionError:
            time_cuts = 0
        try:
            extra = self.cutcode.extra_time(stop_at=step)
            time_total = time_travel + time_cuts + extra
            t_hours = int(time_total // 3600)
            t_mins = int((time_total % 3600) // 60)
            t_seconds = int(time_total % 60)
            self.text_time_total_step.SetValue(
                f"{int(t_hours)}:{int(t_mins):02d}:{int(t_seconds):02d}"
            )
        except ZeroDivisionError:
            pass

        ###################
        # UPDATE TOTAL
        ###################

        travel_mm = self.cutcode.length_travel() / mm
        cuts_mm = self.cutcode.length_cut() / mm
        self.text_distance_travel.SetValue(f"{travel_mm:.2f}mm")
        self.text_distance_laser.SetValue(f"{cuts_mm:.2f}mm")
        self.text_distance_total.SetValue(f"{travel_mm + cuts_mm:.2f}mm")

        try:
            time_travel = self.cutcode.duration_travel()
            t_hours = int(time_travel // 3600)
            t_mins = int((time_travel % 3600) // 60)
            t_seconds = int(time_travel % 60)
            self.text_time_travel.SetValue(f"{t_hours}:{t_mins:02d}:{t_seconds:02d}")
        except ZeroDivisionError:
            time_travel = 0
        try:
            time_cuts = self.cutcode.duration_cut()
            t_hours = int(time_cuts // 3600)
            t_mins = int((time_cuts % 3600) // 60)
            t_seconds = int(time_cuts % 60)
            self.text_time_laser.SetValue(f"{t_hours}:{t_mins:02d}:{t_seconds:02d}")
        except ZeroDivisionError:
            time_cuts = 0
        try:
            extra = self.cutcode.extra_time()
            time_total = time_travel + time_cuts + extra
            t_hours = int(time_total // 3600)
            t_mins = int((time_total % 3600) // 60)
            t_seconds = int(time_total % 60)
            self.text_time_total.SetValue(f"{t_hours}:{t_mins:02d}:{t_seconds:02d}")
        except ZeroDivisionError:
            pass

    def slide_out(self, event):
        self.slided_in = not self.slided_in
        event.Skip()

    def on_redo_it(self, event):
        with wx.BusyInfo(_("Preparing simulation...")):
            self.context(
                "plan{plan} clear\nplan{plan} copy preprocess validate blob preopt optimize\n".format(
                    plan=self.plan_name
                )
            )
        self._refresh_simulated_plan()

    def pane_show(self):
        self.context.setting(str, "units_name", "mm")

        bbox = self.context.device.bbox()
        self.widget_scene.widget_root.focus_viewport_scene(
            bbox, self.view_pane.Size, 0.1
        )
        self.update_fields()
        self.panel_optimize.pane_show()

    def pane_hide(self):
        if self.auto_clear:
            self.context(f"plan{self.plan_name} clear\n")
        self.context.close("SimScene")
        self.context.unschedule(self)
        self.running = False
        self.panel_optimize.pane_hide()

    @signal_listener("refresh_scene")
    def on_refresh_scene(self, origin, scene_name=None, *args):
        """
        Called by 'refresh_scene' change. To refresh tree.
        @param origin: the path of the originating signal
        @param scene_name: Scene to refresh on if matching
        @param args:
        @return:
        """
        if scene_name == "SimScene":
            self.request_refresh()

    def request_refresh(self, *args):
        self.widget_scene.request_refresh(*args)

    def on_slider_progress(self, event=None):  # wxGlade: Simulation.<event_handler>
        self.progress = min(self.slider_progress.GetValue(), self.max)
        self.update_fields()
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
            self.update_fields()
        self._start()

    def animate_sim(self, event=None):
        self.progress += 1
        if self.progress >= self.max:
            self.progress = self.max
            self.slider_progress.SetValue(self.progress)
            self._stop()
        else:
            self.slider_progress.SetValue(self.progress)
        self.update_fields()
        self.context.signal("refresh_scene", self.widget_scene.name)

    def on_slider_playback(self, event=None):  # wxGlade: Simulation.<event_handler>
        # Slider is now pseudo logarithmic in scale varying from 1% to 5,000%.

        value = self.slider_playbackspeed.GetValue()
        value = int((10.0 ** (value // 90)) * (1.0 + float(value % 90) / 10.0))
        self.interval = 0.1 * 100.0 / float(value)

        self.text_playback_speed.SetValue(f"{value}%")

    def on_combo_device(self, event=None):  # wxGlade: Preview.<event_handler>
        index = self.combo_device.GetSelection()
        self.selected_device = self.available_devices[index]
        self.selected_device.kernel.activate_service_path(
            "device", self.selected_device.path
        )
        self.fit_scene_to_panel()

    def on_button_spool(self, event=None):  # wxGlade: Simulation.<event_handler>
        self.context(f"plan{self.plan_name} spool\n")
        self.context("window close Simulation\n")
        if self.context.auto_spooler:
            self.context("window open JobSpooler\n")


class SimulationWidget(Widget):
    """
    The simulation widget is responsible for rendering the cutcode to the scene. This should be
    done such that both progress of 0 and 1 render nothing and items begin to draw at 2.
    """

    def __init__(self, scene, sim):
        Widget.__init__(self, scene, all=False)
        self.renderer = LaserRender(self.scene.context)
        self.sim = sim
        self.matrix.post_cat(scene.context.device.device_to_scene_matrix())

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
        self.matrix.post_cat(scene.context.device.device_to_scene_matrix())
        self.initvars()

    def initvars(self):
        self.starts = list()
        self.ends = list()
        self.pos = list()
        self.starts.append(wx.Point2D(0, 0))
        self.ends.append(wx.Point2D(0, 0))
        prev = None
        for i, curr in enumerate(list(self.sim.cutcode)):
            if prev is not None:
                if prev.end != curr.start:
                    start = wx.Point2D(*prev.end)
                    end = wx.Point2D(*curr.start)
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
        self.sim_matrix = scene.context.device.device_to_scene_matrix()
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
                pos = self.sim.cutcode[self.sim.progress - 1].start
            else:
                pos = self.sim.cutcode[self.sim.progress - 2].end
            x = pos[0]
            y = pos[1]
            x, y = self.sim_matrix.point_in_matrix_space((x, y))

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
            "button/jobstart/Simulation",
            {
                "label": _("Simulate"),
                "icon": icons8_laser_beam_hazard2_50,
                "tip": _("Simulate the current laser job"),
                "action": open_simulator,
                "size": STD_ICON_SIZE,
                "priority": 1,
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    def delegates(self):
        yield self.panel

    @signal_listener("background")
    def on_background_signal(self, origin, background):
        if background is not None:
            background = wx.Bitmap.FromBuffer(*background)
        self.panel.widget_scene._signal_widget(
            self.panel.widget_scene.widget_root, "background", background
        )
        self.panel.widget_scene.request_refresh()

    @staticmethod
    def submenu():
        return ("Burning", "Simulation")
