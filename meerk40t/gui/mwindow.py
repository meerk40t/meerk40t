import wx

from meerk40t.kernel import Module

_ = wx.GetTranslation


class MWindow(wx.Frame, Module):
    """
    Meerk40t window class does some of the more fancy operations for the meerk40t windows. This includes saving and
    loading the windows sizes and positions, ensuring the module for the class is correctly opened and closed.
    Deduplicating a lot of the repeat code and future proofing for other changes.

    MeerK40t Windows have a hook module_close and module_open into window_open and window_close to register and
    unregister hooks from the kernel. We register the acceleration table of the main window and handle the window/module
    open and close events.
    """

    def __init__(self, width, height, context, path, parent, *args, style=-1, **kwds):
        if style == -1:
            if parent is None:
                style = wx.DEFAULT_FRAME_STYLE
            else:
                style = (
                    wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT | wx.TAB_TRAVERSAL
                )
        self._start_width = width
        self._start_height = height
        self.root_context = context.root
        self.window_context = context.get_context(path)
        self.root_context.setting(bool, "windows_save", True)
        self.window_save = self.root_context.windows_save

        wx.Frame.__init__(self, parent, style=style)
        Module.__init__(self, context, path)
        self.window_context.themes.set_window_colors(self)
        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_left_down, self)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu_request, self)
        self.Bind(wx.EVT_MOVE, self.on_change_window, self)
        self.Bind(wx.EVT_SIZE, self.on_change_window, self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.context.themes.set_window_colors(self)

    def restore_aspect(self, honor_initial_values=False):
        width = self._start_width
        height = self._start_height
        try:
            dipsize = self.FromDIP(wx.Size(width, height))
            d_width = dipsize[0]
            d_height = dipsize[1]
        except AttributeError:
            d_width = width
            d_height = height
        if honor_initial_values:
            width = d_width
            height = d_height
        else:
            # Forget about a default size, try to fit
            # the content as good as you can.
            self.sizer.Layout()
            self.sizer.Fit(self)
            width, height = self.GetSize()

        if self.window_save:
            self.window_context.setting(int, "width", width)
            self.window_context.setting(int, "height", height)
            if self.window_context.width < 100:
                self.window_context.width = 100
            if self.window_context.height < 100:
                self.window_context.height = 100
            display_idx = wx.Display.GetFromWindow(self)
            if display_idx != wx.NOT_FOUND:
                area = wx.Display(display_idx).GetClientArea()
                if self.window_context.width >= area[2]:
                    self.window_context.width = area[2]
                    self.window_context.setting(int, "x", 0)
                if self.window_context.height >= area[3]:
                    self.window_context.height = area[3]
                    self.window_context.setting(int, "y", 0)
            self.SetSize((self.window_context.width, self.window_context.height))
        self.Raise()

    def on_mouse_left_down(self, event):
        # Convert mac Control+left click into right click
        if event.RawControlDown() and not event.ControlDown():
            self.on_menu_request(event)
        else:
            event.Skip()

    def on_menu_request(self, event):
        menu = wx.Menu()
        self.create_menu(menu.AppendSubMenu)

        if menu.MenuItemCount != 0:
            self.PopupMenu(menu)
            menu.Destroy()

    def on_change_window(self, event):
        if self.IsShown():
            try:
                self.window_context.width, self.window_context.height = self.Size
                self.window_context.x, self.window_context.y = self.GetPosition()
            except RuntimeError:
                pass
        event.Skip()

    def create_menu(self, append):
        pass

    def on_close(self, event):
        if self.state == 5:
            event.Veto()
        else:
            if hasattr(self, "window_close_veto") and self.window_close_veto():
                event.Veto()
                return
            self.state = 5
            self.context.close(self.name)
            event.Skip()  # Call 'destroy' as regular.

    def window_open(self):
        self.window_context.themes.set_window_colors(self)

    def restore(self, *args, **kwargs):
        if self.IsIconized():
            self.Iconize(False)

    def window_close(self):
        pass

    def window_preserve(self):
        return True

    def window_menu(self):
        return True

    def module_open(self, *args, **kwargs):
        self.context.close(self.name)
        if self.window_save:
            x, y = self.GetPosition()
            self.window_context.setting(int, "x", x)
            self.window_context.setting(int, "y", y)
            self.SetPosition((self.window_context.x, self.window_context.y))
            display = wx.Display.GetFromWindow(self)
            if display == wx.NOT_FOUND:
                self.SetPosition((x, y))
        self.Show()
        self.Raise()
        self.window_open()

    def module_close(self, *args, shutdown=False, **kwargs):
        self.window_close()
        # We put this in the try bracket, as after nuke_settings
        # all the context setting stuff will no longer work
        try:
            if self.window_save:
                self.window_context.setting(bool, "open_on_start", False)
                self.window_context.open_on_start = shutdown and self.window_preserve()
            self.Close()
        except (AttributeError, RuntimeError):
            pass
