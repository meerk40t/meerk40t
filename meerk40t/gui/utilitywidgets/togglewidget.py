import wx

from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_DELEGATE_AND_HIT,
    ORIENTATION_HORIZONTAL,
    ORIENTATION_VERTICAL,
    RESPONSE_ABORT,
)
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.utilitywidgets.buttonwidget import ButtonWidget

_ = wx.GetTranslation


class ToggleWidget(Widget):
    def __init__(self, scene, left, top, right, bottom, bitmap, buttons):
        Widget.__init__(self, scene, left, top, right, bottom)
        self.buttons = buttons
        self.bitmap = bitmap
        self._opened = False
        # If we use the tool-menu, how shall
        self.scene.context.setting(bool, "menu_autohide", True)
        self.scene.context.setting(bool, "menu_vertical", True)
        if self.scene.context.menu_vertical:
            self._orientation = ORIENTATION_VERTICAL
        else:
            self._orientation = ORIENTATION_HORIZONTAL
        self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_DELEGATE_AND_HIT

    def process_draw(self, gc: wx.GraphicsContext):
        gc.PushState()
        gc.DrawBitmap(self.bitmap, self.left, self.top, self.width, self.height)
        gc.PopState()

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        if event_type == "leftdown":
            if self._opened:
                self.minimize(window_pos=None, space_pos=None)
                self._opened = False
            else:
                self.maximize(window_pos=None, space_pos=None)
                self._opened = True
        elif event_type == "rightdown":
            self.show_options()
        return RESPONSE_ABORT

    def on_popup_close(self, event):
        self.hide()
        self.scene.request_refresh()

    def on_popup_horizontal(self, event):
        self.scene.context.menu_vertical = False
        self._orientation = ORIENTATION_HORIZONTAL
        if self._opened:
            self.minimize(window_pos=None, space_pos=None)
            self._opened = False
            self.maximize(window_pos=None, space_pos=None)
            self._opened = True

    def on_popup_vertical(self, event):
        self.scene.context.menu_vertical = True
        self._orientation = ORIENTATION_VERTICAL
        if self._opened:
            self.minimize(window_pos=None, space_pos=None)
            self._opened = False
            self.maximize(window_pos=None, space_pos=None)
            self._opened = True

    def on_popup_autohide(self, event):
        self.scene.context.menu_autohide = not self.scene.context.menu_autohide

    def show_options(self):
        menu = wx.Menu()
        gui = self.scene.context.gui
        item1 = menu.Append(wx.ID_ANY, _("Close"), "", wx.ITEM_NORMAL)
        menu.AppendSeparator()
        item2 = menu.Append(wx.ID_ANY, _("Horizontal"), "", wx.ITEM_CHECK)
        item3 = menu.Append(wx.ID_ANY, _("Vertical"), "", wx.ITEM_CHECK)
        menu.AppendSeparator()
        item4 = menu.Append(wx.ID_ANY, _("Autohide"), "", wx.ITEM_CHECK)
        item2.Check(not self.scene.context.menu_vertical)
        item3.Check(self.scene.context.menu_vertical)
        item4.Check(self.scene.context.menu_autohide)
        gui.Bind(wx.EVT_MENU, self.on_popup_close, item1)
        gui.Bind(wx.EVT_MENU, self.on_popup_horizontal, item2)
        gui.Bind(wx.EVT_MENU, self.on_popup_vertical, item3)
        gui.Bind(wx.EVT_MENU, self.on_popup_autohide, item4)
        gui.PopupMenu(menu)
        menu.Destroy()

    def signal(self, signal, *args, **kwargs):
        if signal == "tool_changed":
            if self.scene.context.menu_autohide:
                if self._opened:
                    self.minimize(window_pos=None, space_pos=None)
                    self._opened = False
        elif signal == "guide":
            # print ("guide")
            pass

    def minimize(self, window_pos=None, space_pos=None):
        self.remove_all_widgets()
        self.scene.request_refresh()

    def maximize(self, window_pos=None, space_pos=None):
        new_values = self.scene.context.find(self.buttons)
        buttons = []
        for button, name, sname in new_values:
            buttons.append(button)

        def sort_priority(elem):
            return elem.get("priority", 0)

        buttons.sort(key=sort_priority)  # Sort buttons by priority

        def clicked(action):
            def act(*args, **kwargs):
                action(None)

            return act

        for button in buttons:
            button_size = self.width
            resize_param = button.get("size")
            icon = button["icon"].GetBitmap(resize=button_size, use_theme=False)
            self.add_widget(
                -1,
                ButtonWidget(
                    self.scene,
                    0,
                    0,
                    button_size,
                    button_size,
                    icon,
                    clicked(button.get("action")),
                ),
                self._orientation,
            )
        self.scene.request_refresh()
