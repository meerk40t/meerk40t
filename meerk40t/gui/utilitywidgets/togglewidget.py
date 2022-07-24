import wx

from meerk40t.gui.scene.sceneconst import (
    RESPONSE_ABORT, ORIENTATION_VERTICAL, HITCHAIN_DELEGATE_AND_HIT,
)
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.utilitywidgets.buttonwidget import ButtonWidget


class ToggleWidget(Widget):

    def __init__(self, scene, left, top, right, bottom, bitmap):
        Widget.__init__(self, scene, left, top, right, bottom)
        self.bitmap = bitmap
        self._opened = False
        self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_DELEGATE_AND_HIT

    def process_draw(self, gc: wx.GraphicsContext):
        gc.PushState()
        gc.DrawBitmap(self.bitmap, self.left, self.top, self.width, self.height)
        gc.PopState()

    def event(
        self, window_pos=None, space_pos=None, event_type=None, nearest_snap=None
    ):
        if event_type == "leftdown":
            if self._opened:
                self.minimize(window_pos=None, space_pos=None)
                self._opened = False
            else:
                self.maximize(window_pos=None, space_pos=None)
                self._opened = True
        return RESPONSE_ABORT

    def minimize(self, window_pos=None, space_pos=None):
        self.remove_all_widgets()
        self.scene.request_refresh()

    def maximize(self, window_pos=None, space_pos=None):
        new_values = self.scene.context.find("button/tool")
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
            button_size = 25
            resize_param = button.get("size")
            icon = button["icon"].GetBitmap(resize=button_size)
            self.add_widget(-1, ButtonWidget(self.scene, 0, 0, button_size, button_size, icon, clicked(button.get("action"))), ORIENTATION_VERTICAL)

            # group = button.get("group")
            # if "multi" in button:
            #     # Button is a multi-type button
            #     b = button_bar.AddHybridButton(
            #         button_id=new_id,
            #         label=button["label"],
            #         bitmap=button["icon"].GetBitmap(resize=resize_param),
            #         help_string=button["tip"] if show_tip else "",
            #     )
            #     button_bar.Bind(
            #         RB.EVT_RIBBONBUTTONBAR_DROPDOWN_CLICKED,
            #         self.drop_click,
            #         id=new_id,
            #     )
            # else:
            #     if "group" in button:
            #         bkind = RB.RIBBON_BUTTON_TOGGLE
            #     else:
            #         bkind = RB.RIBBON_BUTTON_NORMAL
            #     if "toggle" in button:
            #         bkind = RB.RIBBON_BUTTON_TOGGLE
            #     b = button_bar.AddButton(
            #         button_id=new_id,
            #         label=button["label"],
            #         bitmap=button["icon"].GetBitmap(resize=resize_param),
            #         bitmap_disabled=button["icon"].GetBitmap(
            #             resize=resize_param, color=Color("grey")
            #         ),
            #         help_string=button["tip"] if show_tip else "",
            #         kind=bkind,
            #     )
            #
            # # Store all relevant aspects for newly registered button.
            # b.button_dict = button
            # b.state_pressed = None
            # b.state_unpressed = None
            # b.toggle = False
            # b.parent = button_bar
            # b.group = group
            # b.identifier = button.get("identifier")
            # b.action = button.get("action")
            # b.action_right = button.get("right")
            # if "rule_enabled" in button:
            #     b.enable_rule = button.get("rule_enabled")
            # else:
            #     b.enable_rule = lambda cond: True
            #
            # if "multi" in button:
            #     # Store alternative aspects for multi-buttons, load stored previous state.
            #
            #     multi_action = button["multi"]
            #     multi_ident = button.get("identifier")
            #     b.save_id = multi_ident
            #     initial_id = self.context.setting(str, b.save_id, "default")
            #
            #     for i, v in enumerate(multi_action):
            #         key = v.get("identifier", i)
            #         self._store_button_aspect(b, key)
            #         self._update_button_aspect(b, key, **v)
            #         if "icon" in v:
            #             v_icon = button.get("icon")
            #             self._update_button_aspect(
            #                 b,
            #                 key,
            #                 bitmap_large=v_icon.GetBitmap(resize=resize_param),
            #                 bitmap_large_disabled=v_icon.GetBitmap(
            #                     resize=resize_param, color=Color("grey")
            #                 ),
            #             )
            #             if resize_param is None:
            #                 siz = v_icon.GetBitmap().GetSize()
            #                 small_resize = 0.5 * siz[0]
            #             else:
            #                 small_resize = 0.5 * resize_param
            #             self._update_button_aspect(
            #                 b,
            #                 key,
            #                 bitmap_small=v_icon.GetBitmap(resize=small_resize),
            #                 bitmap_small_disabled=v_icon.GetBitmap(
            #                     resize=small_resize, color=Color("grey")
            #                 ),
            #             )
            #         if key == initial_id:
            #             self._restore_button_aspect(b, key)
            # if "toggle" in button:
            #     # Store toggle and original aspects for toggle-buttons
            #
            #     b.state_pressed = "toggle"
            #     b.state_unpressed = "original"
            #
            #     self._store_button_aspect(b, "original")
            #
            #     toggle_action = button["toggle"]
            #     key = toggle_action.get("identifier", "toggle")
            #     self._store_button_aspect(
            #         b,
            #         key,
            #         **toggle_action
            #     )
            #     if "icon" in toggle_action:
            #         toggle_icon = toggle_action.get("icon")
            #         self._update_button_aspect(
            #             b,
            #             key,
            #             bitmap_large=toggle_icon.GetBitmap(resize=resize_param),
            #             bitmap_large_disabled=toggle_icon.GetBitmap(
            #                 resize=resize_param, color=Color("grey")
            #             ),
            #         )
            #         if resize_param is None:
            #             siz = v_icon.GetBitmap().GetSize()
            #             small_resize = 0.5 * siz[0]
            #         else:
            #             small_resize = 0.5 * resize_param
            #         self._update_button_aspect(
            #             b,
            #             key,
            #             bitmap_small=toggle_icon.GetBitmap(resize=small_resize),
            #             bitmap_small_disabled=toggle_icon.GetBitmap(
            #                 resize=small_resize, color=Color("grey")
            #             ),
            #         )
            # # Store newly created button in the various lookups
            # self.button_lookup[new_id] = b
            # if group is not None:
            #     c_group = self.group_lookup.get(group)
            #     if c_group is None:
            #         c_group = []
            #         self.group_lookup[group] = c_group
            #     c_group.append(b)
            #
            # button_bar.Bind(
            #     RB.EVT_RIBBONBUTTONBAR_CLICKED, self.button_click, id=new_id
            # )
            # button_bar.Bind(wx.EVT_RIGHT_UP, self.button_click_right)
        self.scene.request_refresh()
