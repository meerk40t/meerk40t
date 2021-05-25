import wx

from .icons import icons8_play_50, icons8_route_50, icons8_laser_beam_hazard_50
from .laserrender import LaserRender
from .mwindow import MWindow
from .widget import GridWidget, GuideWidget, ReticleWidget, Widget, HITCHAIN_HIT, RESPONSE_CONSUME, \
    ScenePanel
from ..core.cutcode import CutCode
from ..svgelements import Matrix

_ = wx.GetTranslation

MILS_PER_MM = 39.3701


class Simulation(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(706, 755, *args, **kwds)
        if len(args) >= 4:
            plan_name = args[3]
        else:
            plan_name = 0
        self.plan_name = plan_name
        self.operations, original, commands, plan_name = self.context.root.default_plan()
        self.cutcode = CutCode()
        for c in self.operations:
            if isinstance(c, CutCode):
                self.cutcode.extend(c)
        self.cutcode = list(self.cutcode.flat())
        self.max = len(self.cutcode)

        self.bed_dim = self.context.root
        self.bed_dim.setting(int, "bed_width", 310)
        self.bed_dim.setting(int, "bed_height", 210)

        # Menu Bar
        self.Simulation_menubar = wx.MenuBar()
        wxglade_tmp_menu = wx.Menu()
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Travel Moves", "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_view_travel, id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Background", "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_view_background, id=item.GetId())
        self.Simulation_menubar.Append(wxglade_tmp_menu, "View")
        wxglade_tmp_menu = wx.Menu()
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Optimize Travel (Greedy)", "")
        self.Bind(wx.EVT_MENU, self.on_optimize_travel_greedy, id=item.GetId())
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Optimize Travel (Two-Opt)", "")
        self.Bind(wx.EVT_MENU, self.on_optimize_travel_twoop, id=item.GetId())
        self.Simulation_menubar.Append(wxglade_tmp_menu, "Optimize")
        self.SetMenuBar(self.Simulation_menubar)
        # Menu Bar end
        self.view_pane = ScenePanel(self.context, self, scene_name="SimScene", style=wx.EXPAND | wx.WANTS_CHARS)
        self.widget_scene = self.view_pane.scene

        m = max(self.max, 10)
        self.slider_progress = wx.Slider(self, wx.ID_ANY, m, 0, m)
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
        self.slider_playbackspeed = wx.Slider(self, wx.ID_ANY, 100, 1, 1000)
        self.text_playback_speed = wx.TextCtrl(
            self, wx.ID_ANY, "100%", style=wx.TE_READONLY
        )

        self.available_devices = [
            self.context.registered[i] for i in self.context.match("device")
        ]
        selected_spooler = self.context.root.active
        spools = [str(i) for i in self.context.match("device", suffix=True)]
        index = spools.index(selected_spooler)
        self.connected_name = spools[index]
        self.connected_spooler, self.connected_driver, self.connected_output = (
            None,
            None,
            None,
        )
        try:
            (
                self.connected_spooler,
                self.connected_driver,
                self.connected_output,
            ) = self.available_devices[index]
        except IndexError:
            for m in self.Children:
                if isinstance(m, wx.Window):
                    m.Disable()
        spools = [" -> ".join(map(repr, ad)) for ad in self.available_devices]

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
        # end wxGlade

        self.widget_scene.add_interfacewidget(SimulationInterfaceWidget(self.widget_scene))
        self.widget_scene.add_scenewidget(SimulationWidget(self.widget_scene, self))
        self.widget_scene.add_scenewidget(GridWidget(self.widget_scene))
        self.widget_scene.add_interfacewidget(GuideWidget(self.widget_scene))
        self.reticle = SimReticleWidget(self.widget_scene)
        self.widget_scene.add_interfacewidget(self.reticle)

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_laser_beam_hazard_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle("Simulation")
        self.text_distance_laser.SetToolTip("Time Estimate: Lasering Time")
        self.text_distance_travel.SetToolTip("Time Estimate: Traveling Time")
        self.text_distance_total.SetToolTip("Time Estimate: Total Time")
        self.text_time_laser.SetToolTip("Time Estimate: Lasering Time")
        self.text_time_travel.SetToolTip("Time Estimate: Traveling Time")
        self.text_time_total.SetToolTip("Time Estimate: Total Time")
        self.button_play.SetBitmap(icons8_play_50.GetBitmap())
        self.text_playback_speed.SetMinSize((55, 23))
        self.combo_device.SetToolTip("Select the device")
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
            wx.StaticBox(self, wx.ID_ANY, "Total Time"), wx.VERTICAL
        )
        sizer_travel_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Travel Time"), wx.VERTICAL
        )
        sizer_laser_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Laser Time"), wx.VERTICAL
        )
        sizer_distance = wx.BoxSizer(wx.HORIZONTAL)
        sizer_total_distance = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Total Distance"), wx.VERTICAL
        )
        sizer_travel_distance = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Travel Distance"), wx.VERTICAL
        )
        sizer_laser_distance = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Laser Distance"), wx.VERTICAL
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
        label_playback_speed = wx.StaticText(self, wx.ID_ANY, "Playback Speed")
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

    def window_open(self):
        self.context.setting(int, "language", 0)
        self.context.setting(str, "units_name", "mm")
        self.context.setting(int, "units_marks", 10)
        self.context.setting(int, "units_index", 0)
        self.context.listen("refresh_scene", self.on_refresh_scene)

        bbox = (0, 0, self.bed_dim.bed_width * MILS_PER_MM, self.bed_dim.bed_height * MILS_PER_MM)
        self.widget_scene.widget_root.focus_viewport_scene(
            bbox, self.view_pane.Size, 0.1
        )

    def window_close(self):
        self.context.unlisten("refresh_scene", self.on_refresh_scene)
        self.context("plan%s clear\n" % self.plan_name)
        self.context.close("SimScene")

    def on_refresh_scene(self, origin, *args):
        """
        Called by 'refresh_scene' change. To refresh tree.

        :param args:
        :return:
        """
        self.request_refresh()

    def request_refresh(self, *args):
        self.widget_scene.request_refresh(*args)

    def on_view_travel(self, event):  # wxGlade: Simulation.<event_handler>
        print("Event handler 'on_view_travel' not implemented!")
        event.Skip()

    def on_view_background(self, event):  # wxGlade: Simulation.<event_handler>
        print("Event handler 'on_view_background' not implemented!")
        event.Skip()

    def on_optimize_travel_greedy(self, event):  # wxGlade: Simulation.<event_handler>
        print("Event handler 'on_optimize_travel_greedy' not implemented!")
        event.Skip()

    def on_optimize_travel_twoop(self, event):  # wxGlade: Simulation.<event_handler>
        print("Event handler 'on_optimize_travel_twoop' not implemented!")
        event.Skip()

    def on_slider_progress(self, event):  # wxGlade: Simulation.<event_handler>
        self.max = self.slider_progress.GetValue()
        self.context.signal("refresh_scene")

    def on_button_play(self, event):  # wxGlade: Simulation.<event_handler>
        print("Event handler 'on_button_play' not implemented!")
        event.Skip()

    def on_slider_playback(self, event):  # wxGlade: Simulation.<event_handler>
        print("Event handler 'on_sldier_playback' not implemented!")
        event.Skip()

    def on_combo_device(self, event):  # wxGlade: Preview.<event_handler>
        self.available_devices = [
            self.context.registered[i] for i in self.context.match("device")
        ]
        index = self.combo_device.GetSelection()
        (
            self.connected_spooler,
            self.connected_driver,
            self.connected_output,
        ) = self.available_devices[index]
        self.connected_name = [
            str(i) for i in self.context.match("device", suffix=True)
        ][index]

    def on_button_spool(self, event):  # wxGlade: Simulation.<event_handler>
        self.context("plan%s spool%s\n" % (self.plan_name, self.connected_name))
        self.context("window close Simulation\n")


class SimulationWidget(Widget):
    def __init__(self, scene, sim):
        Widget.__init__(self, scene, all=False)
        self.renderer = LaserRender(self.scene.context)
        self.sim = sim

    def process_draw(self, gc):
        sim_cut = self.sim.cutcode[:self.sim.max]
        try:
            self.sim.reticle.set_pos(sim_cut[-1].end())
        except IndexError:
            self.sim.reticle.set_pos((0, 0))
        self.renderer.draw_cutcode(sim_cut, gc, 0, 0)


class SimulationInterfaceWidget(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, 40, 40, 200, 70)
        self.selected = False

    def process_draw(self, gc):
        font = wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD)
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        gc.SetFont(font, wx.BLACK)
        gc.DrawText(_("Simulating Burn..."), self.left, self.top)
        gc.SetPen(wx.BLACK_PEN)
        gc.DrawRectangle(self.left, self.top, self.width, self.height)

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "leftdown":
            self.selected = True
        if event_type == "move":
            self.translate_self(window_pos[4], window_pos[5])
            self.scene.context.signal("refresh_scene")
        if event_type == "leftup":
            self.selected = False
        return RESPONSE_CONSUME


class SimReticleWidget(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.x = 0
        self.y = 0

    def set_pos(self, pos):
        self.x = pos[0]
        self.y = pos[1]

    def process_draw(self, gc):
        context = self.scene.context
        try:
            # Draw Reticle
            gc.SetPen(wx.GREEN_PEN)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            x, y = self.scene.convert_scene_to_window([self.x, self.y])
            gc.DrawEllipse(x - 5, y - 5, 10, 10)
            gc.DrawEllipse(x - 10, y - 10, 20, 20)
            gc.DrawEllipse(x - 20, y - 20, 40, 40)
        except AttributeError:
            pass
