import wx

from ..kernel import Module

_ = wx.GetTranslation


class MWindow(wx.Frame, Module):
    """
    Meerk40t window class does some of the more fancy operations for the meerk40t windows. This includes saving and
    loading the windows sizes and positions, ensuring the module for the class is correctly opened and closed.
    Deduplicating a lot of the repeat code and future proofing for other changes.

    MeerK40t Windows have a hook finalize and initialize into window_open and window_close to register and unregister
    hooks from the kernel. We register the acceleration table of the main window and handle the window/module open and
    close events.
    """

    def __init__(self, width, height, context, path, parent, *args, **kwds):
        # begin wxGlade: Notes.__init__
        if parent is None:
            wx.Frame.__init__(self, parent, -1, "", style=wx.DEFAULT_FRAME_STYLE)
        else:
            wx.Frame.__init__(
                self,
                parent,
                -1,
                "",
                style=wx.DEFAULT_FRAME_STYLE
                | wx.FRAME_FLOAT_ON_PARENT
                | wx.TAB_TRAVERSAL,
            )
        Module.__init__(self, context, path)

        self.root_context = context.get_context("/")
        self.window_context = context.get_context(path)

        self.root_context.setting(bool, "windows_save", True)
        self.window_save = self.root_context.windows_save
        if self.window_save:
            self.window_context.setting(int, "width", width)
            self.window_context.setting(int, "height", height)
            if self.window_context.width < 100:
                self.window_context.width = 100
            if self.window_context.height < 100:
                self.window_context.height = 100
            self.SetSize((self.window_context.width, self.window_context.height))
        else:
            self.SetSize(width, height)
        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.accelerator_table(self)

    def accelerator_table(self, window):
        def close_window(e=None):
            try:
                window.Close(False)
            except RuntimeError:
                pass

        keyid = wx.NewId()
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord("W"), keyid)])
        window.Bind(wx.EVT_MENU, close_window, id=keyid)
        window.SetAcceleratorTable(accel_tbl)

    def on_close(self, event):
        if self.state == 5:
            event.Veto()
        else:
            self.window_context.width, self.window_context.height = self.Size
            self.window_context.x, self.window_context.y = self.GetPosition()
            self.state = 5
            self.context.close(self.name)
            event.Skip()  # Call destroy as regular.

    def window_open(self):
        pass

    def window_close(self):
        pass

    def initialize(self, *args, **kwargs):
        self.context.close(self.name)
        if self.window_save:
            x, y = self.GetPosition()
            self.window_context.setting(int, "x", x)
            self.window_context.setting(int, "y", y)
            self.SetPosition((self.window_context.x, self.window_context.y))
        self.window_open()
        self.Show()

    def finalize(self, *args, **kwargs):
        self.window_close()
        if self.window_save:
            self.window_context.width, self.window_context.height = self.Size
            self.window_context.x, self.window_context.y = self.GetPosition()
        try:
            self.Close()
        except RuntimeError:
            pass
