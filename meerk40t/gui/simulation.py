import wx

from .icons import icons8_play_50, icons8_route_50, icons8_laser_beam_hazard_50
from .laserrender import DRAW_MODE_INVERT, DRAW_MODE_FLIPXY, LaserRender
from .mwindow import MWindow
from .zmatrix import ZMatrix
from ..core.cutcode import CutCode
from ..kernel import Job
from ..svgelements import Matrix

_ = wx.GetTranslation

MILS_PER_MM = 39.3701


class Simulation(MWindow, Job):
    def __init__(self, *args, **kwds):
        super().__init__(706, 755, *args, **kwds)
        Job.__init__(self, job_name="Simulation")
        if len(args) >= 4:
            plan_name = args[3]
        else:
            plan_name = 0
        self.plan_name = plan_name

        self.bed_dim = self.context.get_context("/")
        self.bed_dim.setting(int, "bed_width", 310)
        self.bed_dim.setting(int, "bed_height", 210)

        self.process = self.update_view
        self.interval = 1.0 / 20.0

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
        self.view_pane = wx.Panel(self, wx.ID_ANY)
        self.slider_progress = wx.Slider(self, wx.ID_ANY, 0, 0, 10)
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

        self.renderer = LaserRender(self.context)

        self.previous_window_position = None
        self.previous_scene_position = None
        self._Buffer = None

        self.Bind(wx.EVT_SLIDER, self.on_slider_progress, self.slider_progress)
        self.Bind(wx.EVT_BUTTON, self.on_button_play, self.button_play)
        self.Bind(wx.EVT_SLIDER, self.on_slider_playback, self.slider_playbackspeed)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_device, self.combo_device)
        self.Bind(wx.EVT_BUTTON, self.on_button_spool, self.button_spool)
        # end wxGlade

        self.view_pane.Bind(wx.EVT_PAINT, self.on_paint)
        self.view_pane.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase)
        self.view_pane.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.view_pane.Bind(wx.EVT_MOUSEWHEEL, self.on_mousewheel)
        self.view_pane.Bind(wx.EVT_MIDDLE_UP, self.on_mouse_middle_up)
        self.view_pane.Bind(wx.EVT_MIDDLE_DOWN, self.on_mouse_middle_down)

        self.view_pane.Bind(wx.EVT_RIGHT_DOWN, self.on_mouse_right_down)
        self.view_pane.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_left_down)
        self.view_pane.Bind(wx.EVT_LEFT_UP, self.on_mouse_left_up)
        self.view_pane.Bind(
            wx.EVT_ENTER_WINDOW, lambda event: self.view_pane.SetFocus()
        )  # Focus follows mouse.

        self.Bind(wx.EVT_SIZE, self.on_size, self)
        self.on_size()

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
        self.context.schedule(self)

        bbox = (0, 0, self.bed_dim.bed_width * MILS_PER_MM, self.bed_dim.bed_height * MILS_PER_MM)
        self.focus_viewport_scene(
            bbox, self.view_pane.Size, 0.1
        )

    def window_close(self):
        self.context.unschedule(self)

    def on_size(self, event=None):
        self.Layout()
        width, height = self.ClientSize
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        self._Buffer = wx.Bitmap(width, height)
        self.on_update_buffer()
        try:
            self.Refresh(True)
            self.Update()
        except RuntimeError:
            pass

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
        print("Event handler 'on_slider_progress' not implemented!")
        event.Skip()

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

    def update_view(self):
        if not wx.IsMainThread():
            wx.CallAfter(self._guithread_update_view)
        else:
            self._guithread_update_view()

    def _guithread_update_view(self):
        bed_width = self.bed_dim.bed_width
        bed_height = self.bed_dim.bed_height

        self.on_update_buffer()
        try:
            self.Refresh(True)
            self.Update()
        except RuntimeError:
            pass

    def on_erase(self, event):
        """
        Erase camera view.
        :param event:
        :return:
        """
        pass

    def on_paint(self, event):
        """
        Paint camera view.
        :param event:
        :return:
        """
        try:
            wx.BufferedPaintDC(self.view_pane, self._Buffer)
        except (RuntimeError, TypeError):
            pass

    def on_update_buffer(self, event=None):
        """
        Draw Camera view.

        :param event:
        :return:
        """
        dm = self.context.draw_mode
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        w, h = self._Buffer.GetSize()
        # dc.SetBackground(wx.WHITE_BRUSH)
        gc.SetBrush(wx.GREY_BRUSH)
        gc.DrawRectangle(0, 0, w, h)
        font = wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD)
        gc.SetFont(font, wx.BLACK)
        gc.DrawText(_("Simulating Burn..."), 0, 0)

        if dm & DRAW_MODE_FLIPXY != 0:
            dc.SetUserScale(-1, -1)
            dc.SetLogicalOrigin(w, h)

        gc.PushState()
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(self.matrix)))
        gc.SetBrush(wx.WHITE_BRUSH)
        gc.DrawRectangle(0, 0, self.bed_dim.bed_width * MILS_PER_MM, self.bed_dim.bed_height * MILS_PER_MM)

        context = self.context
        zoom_scale = 1 / self.matrix.value_scale_x()
        if zoom_scale < 1:
            zoom_scale = 1
        operations, original, commands, plan_name = self.context.default_plan()
        for op in reversed(operations):
            if isinstance(op, CutCode):
                self.renderer.draw_cutcode(op,gc,0,0)
        gc.PopState()
        if dm & DRAW_MODE_INVERT != 0:
            dc.Blit(0, 0, w, h, dc, 0, 0, wx.SRC_INVERT)
        gc.Destroy()
        del dc

    def convert_scene_to_window(self, position):
        """
        Scene Matrix convert scene to window.
        :param position:
        :return:
        """
        point = self.matrix.point_in_matrix_space(position)
        return point[0], point[1]

    def convert_window_to_scene(self, position):
        """
        Scene Matrix convert window to scene.
        :param position:
        :return:
        """
        point = self.matrix.point_in_inverse_space(position)
        return point[0], point[1]

    def on_mouse_move(self, event):
        """
        Handle mouse movement.

        :param event:
        :return:
        """
        if not event.Dragging():
            return
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        if self.previous_window_position is None:
            return
        pos = event.GetPosition()
        window_position = pos.x, pos.y
        scene_position = self.convert_window_to_scene(
            [window_position[0], window_position[1]]
        )
        sdx = scene_position[0] - self.previous_scene_position[0]
        sdy = scene_position[1] - self.previous_scene_position[1]
        wdx = window_position[0] - self.previous_window_position[0]
        wdy = window_position[1] - self.previous_window_position[1]
        self.scene_post_pan(wdx, wdy)
        self.previous_window_position = window_position
        self.previous_scene_position = scene_position

    def on_mouse_right_down(self, event):
        menu = wx.Menu()
        if menu.MenuItemCount != 0:
            self.PopupMenu(menu)
            menu.Destroy()

    def on_mousewheel(self, event):
        """
        Handle mouse wheel.

        Used for zooming.

        :param event:
        :return:
        """
        rotation = event.GetWheelRotation()
        mouse = event.GetPosition()
        if self.context.root.mouse_zoom_invert:
            rotation = -rotation
        if rotation > 1:
            self.scene_post_scale(1.1, 1.1, mouse[0], mouse[1])
        elif rotation < -1:
            self.scene_post_scale(0.9, 0.9, mouse[0], mouse[1])

    def on_mouse_left_down(self, event):
        """
        Handle mouse left down event.

        Used for adjusting perspective items.

        :param event:
        :return:
        """
        self.previous_window_position = event.GetPosition()
        self.previous_scene_position = self.convert_window_to_scene(
            self.previous_window_position
        )

    def on_mouse_left_up(self, event):
        """
        Handle Mouse Left Up.

        Drag Ends.

        :param event:
        :return:
        """
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        self.previous_window_position = None
        self.previous_scene_position = None

    def on_mouse_middle_down(self, event):
        """
        Handle mouse middle down

        Panning.

        :param event:
        :return:
        """
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.previous_window_position = event.GetPosition()
        self.previous_scene_position = self.convert_window_to_scene(
            self.previous_window_position
        )

    def on_mouse_middle_up(self, event):
        """
        Handle mouse middle up.

        Pan ends.

        :param event:
        :return:
        """
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        self.previous_window_position = None
        self.previous_scene_position = None

    def scene_post_pan(self, px, py):
        """
        Scene Pan.
        :param px:
        :param py:
        :return:
        """
        self.matrix.post_translate(px, py)
        self.on_update_buffer()

    def scene_post_scale(self, sx, sy=None, ax=0, ay=0):
        """
        Scene Zoom.
        :param sx:
        :param sy:
        :param ax:
        :param ay:
        :return:
        """
        self.matrix.post_scale(sx, sy, ax, ay)
        self.on_update_buffer()

    def focus_viewport_scene(
        self, new_scene_viewport, scene_size, buffer=0.0, lock=True
    ):
        """
        Focus on the given viewport in the scene.

        :param new_scene_viewport: Viewport to have after this process within the scene.
        :param scene_size: Size of the scene in which this viewport is active.
        :param buffer: Amount of buffer around the edge of the new viewport.
        :param lock: lock the scalex, scaley.
        :return:
        """
        window_width, window_height = scene_size
        left = new_scene_viewport[0]
        top = new_scene_viewport[1]
        right = new_scene_viewport[2]
        bottom = new_scene_viewport[3]
        viewport_width = right - left
        viewport_height = bottom - top

        left -= viewport_width * buffer
        right += viewport_width * buffer
        top -= viewport_height * buffer
        bottom += viewport_height * buffer

        if right == left:
            scale_x = 100
        else:
            scale_x = window_width / float(right - left)
        if bottom == top:
            scale_y = 100
        else:
            scale_y = window_height / float(bottom - top)

        cx = (right + left) / 2
        cy = (top + bottom) / 2
        self.matrix.reset()
        self.matrix.post_translate(-cx, -cy)
        if lock:
            scale = min(scale_x, scale_y)
            if scale != 0:
                self.matrix.post_scale(scale)
        else:
            if scale_x != 0 and scale_y != 0:
                self.matrix.post_scale(scale_x, scale_y)
        self.matrix.post_translate(window_width / 2.0, window_height / 2.0)
