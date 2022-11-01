import math
import platform
import re

import wx

from meerk40t.kernel import Job, signal_listener

from ..core.cutcode import (
    CubicCut,
    CutCode,
    DwellCut,
    GotoCut,
    HomeCut,
    # InfoCut,
    InputCut,
    LineCut,
    OutputCut,
    PlotCut,
    QuadCut,
    RasterCut,
    RawCut,
    WaitCut,
    SetOriginCut,
)
from ..core.node.util_console import ConsoleOperation
from ..core.node.util_goto import GotoOperation
from ..core.node.util_home import HomeOperation
from ..core.node.util_origin import SetOriginOperation
from ..core.node.util_wait import WaitOperation
from ..core.units import Length
from ..svgelements import Matrix
from .choicepropertypanel import ChoicePropertyPanel
from .icons import (
    STD_ICON_SIZE,
    icons8_image_50,
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
from .zmatrix import ZMatrix

_ = wx.GetTranslation


class OperationsPanel(wx.Panel):
    """
    OperationsPanel is a panel that display cutplan operations and allows to edit them
    """

    def __init__(self, *args, context=None, cutplan=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.parent = args[0]
        self.context = context
        self.cutplan = cutplan
        if self.cutplan is None:
            self.plan_name = ""
        else:
            self.plan_name = self.cutplan.name
        self.list_operations = wx.ListBox(self, wx.ID_ANY, choices=[])
        self.text_operation_param = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )
        self.text_operation_param.SetToolTip(
            _("Modify operation parameter, press Enter to apply")
        )

        self.list_operations.Bind(
            wx.EVT_RIGHT_DOWN, self.on_listbox_operation_rightclick
        )
        self.list_operations.Bind(
            wx.EVT_LISTBOX_DCLICK, self.on_listbox_operation_dclick
        )
        self.list_operations.Bind(wx.EVT_LISTBOX, self.on_listbox_operation_select)
        self.text_operation_param.Bind(wx.EVT_TEXT_ENTER, self.on_text_operation_param)

        ops_sizer = wx.BoxSizer(wx.VERTICAL)
        ops_sizer.Add(self.list_operations, 1, wx.EXPAND, 0)
        ops_sizer.Add(self.text_operation_param, 0, wx.EXPAND, 0)
        self.SetSizer(ops_sizer)
        self.Layout()
        self.SetCutPlan(self.cutplan)

    def SetCutPlan(self, cutplan):
        def name_str(e):
            try:
                return e.__name__
            except AttributeError:
                return str(e)
        oldidx = self.list_operations.GetSelection()
        self.cutplan = cutplan
        self.plan_name = self.cutplan.name
        self.list_operations.Clear()
        if self.cutplan.plan is not None and len(self.cutplan.plan) != 0:
            self.list_operations.InsertItems(
                [name_str(e) for e in self.cutplan.plan], 0
            )
        if 0 <= oldidx < len(self.cutplan.plan):
            self.list_operations.SetSelection(oldidx)
            self.on_listbox_operation_select(None)

    def on_listbox_operation_drag_drop(self, event):
        idx1 = 0
        idx2 = 0
        temp = self.cutplan.plan[idx1]
        self.cutplan.plan[idx1] = self.cutplan.plan[idx2]
        self.cutplan.plan[idx2] = temp

    def on_text_operation_param(self, event):
        content = self.text_operation_param.GetValue()
        idx = self.list_operations.GetSelection()
        flag = False
        if idx >= 0:
            op = self.cutplan.plan[idx]
            if isinstance(op, ConsoleOperation):
                op.command = content
                flag = True
            elif isinstance(op, GotoOperation):
                params = content.split(",")
                x = 0
                y = 0
                if len(params) > 0:
                    try:
                        x = float(Length(params[0]))
                    except ValueError:
                        return
                if len(params) > 1:
                    try:
                        y = float(Length(params[1]))
                    except ValueError:
                        return
                op.x = x
                op.y = y
                flag = True
            elif isinstance(op, WaitOperation):
                try:
                    duration = float(content)
                    op.wait = duration
                    flag = True
                except ValueError:
                    return
            elif isinstance(op, SetOriginOperation):
                if content != "":
                    params = content.split(",")
                    x = 0
                    y = 0
                    if len(params) > 0:
                        try:
                            x = float(Length(params[0]))
                        except ValueError:
                            return
                    if len(params) > 1:
                        try:
                            y = float(Length(params[1]))
                        except ValueError:
                            return
                    op.x = x
                    op.y = y
                    flag = True
                else:
                    op.x = None
                    op.y = None
                    flag = True
        if flag:
            self.context.signal("plan", self.plan_name, 1)

    def on_listbox_operation_select(self, event):
        flag = False
        content = ""
        idx = self.list_operations.GetSelection()
        cutcode = None
        if idx >= 0:
            op = self.cutplan.plan[idx]
            if isinstance(op, ConsoleOperation):
                content = op.command
                flag = True
            elif isinstance(op, GotoOperation):
                content = str(op.x) + "," + str(op.y)
                flag = True
            elif isinstance(op, WaitOperation):
                content = str(op.wait)
                flag = True
            elif isinstance(op, SetOriginOperation):
                if op.x is None or op.y is None:
                    content = ""
                else:
                    content = str(op.x) + "," + str(op.y)
                flag = True
            elif isinstance(op, CutCode):
                cutcode = op
        self.parent.set_cutcode_entry(cutcode)
        self.text_operation_param.SetValue(content)
        self.text_operation_param.Enable(flag)

    def on_listbox_operation_dclick(self, event):
        # No useful logic yet, the old logic fails as it is opening a wrong node
        # There are no property panels for CutObjects yet
        return
        # node_index = self.list_operations.GetSelection()
        # if node_index == -1:
        #     return
        # obj = self.cutplan.plan[node_index]
        # self.context.open("window/Properties", self)
        # self.context.kernel.activate_instance(obj)

    def on_listbox_operation_rightclick(self, event):
        def remove_operation(event):
            idx = self.list_operations.GetSelection()
            self.cutplan.plan.pop(idx)
            self.context.signal("plan", self.plan_name, 1)
            # self._refresh_simulated_plan()

        def append_operation(operation):
            def check(event):
                self.cutplan.plan.append(my_operation)
                self.context.signal("plan", self.plan_name, 1)

            my_operation = operation
            return check

        def insert_operation(operation):
            def check(event):
                self.cutplan.plan.insert(
                    self.list_operations.GetSelection(), my_operation
                )
                self.context.signal("plan", self.plan_name, 1)

            my_operation = operation
            return check

        if self.list_operations.GetSelection() < 0:
            return

        gui = self

        menu = wx.Menu()
        self.Bind(
            wx.EVT_MENU,
            remove_operation,
            menu.Append(
                wx.ID_ANY,
                _("Remove operation"),
                _("Removes the current operation from the active cutplan"),
            ),
        )
        standards = (
            ("Home", "util home", ""),
            ("Set Origin", "util origin", ""),
            ("Goto Origin", "util goto", "0,0"),
            ("Beep", "util console", "beep"),
            ("Interrupt", "util console", 'interrupt "Spooling was interrupted"'),
            ("Console", "util console", "echo 'Still burning'"),
            ("Wait", "util wait", "5"),
        )
        pre_items = []
        for elem in standards:
            desc = elem[0]
            optype = elem[1]
            opparam = elem[2]

            if optype is not None:
                addop = None
                if optype == "util console":
                    addop = ConsoleOperation(command=opparam)
                elif optype == "util home":
                    addop = HomeOperation()
                # elif optype == "util output":
                #     if opparam is not None:
                #         params = opparam.split(",")
                #         mask = 0
                #         setvalue = 0
                #         if len(params) > 0:
                #             try:
                #                 mask = int(params[0])
                #             except ValueError:
                #                 mask = 0
                #         if len(params) > 1:
                #             try:
                #                 setvalue = int(params[1])
                #             except ValueError:
                #                 setvalue = 0
                #         if mask != 0 or setvalue != 0:
                #             addop = OutputOperation(mask, setvalue)
                elif optype == "util goto":
                    if opparam is not None:
                        params = opparam.split(",")
                        x = 0
                        y = 0
                        if len(params) > 0:
                            try:
                                x = float(Length(params[0]))
                            except ValueError:
                                x = 0
                        if len(params) > 1:
                            try:
                                y = float(Length(params[1]))
                            except ValueError:
                                y = 0
                        addop = GotoOperation(x=x, y=y)
                elif optype == "util origin":
                    if opparam is not None and opparam != "":
                        params = opparam.split(",")
                        x = 0
                        y = 0
                        if len(params) > 0:
                            try:
                                x = float(Length(params[0]))
                            except ValueError:
                                x = 0
                        if len(params) > 1:
                            try:
                                y = float(Length(params[1]))
                            except ValueError:
                                y = 0
                        addop = SetOriginOperation(x=x, y=y)
                    else:
                        addop = SetOriginOperation(x=None, y=None)
                elif optype == "util wait":
                    if opparam is not None:
                        try:
                            opparam = float(opparam)
                        except ValueError:
                            opparam = None
                    if opparam is not None:
                        addop = WaitOperation(wait=opparam)
                if addop is not None:
                    pre_items.append([desc, addop])

        menu.AppendSeparator()
        for entry in pre_items:
            self.Bind(
                wx.EVT_MENU,
                insert_operation(entry[1]),
                menu.Append(
                    wx.ID_ANY,
                    _("Insert '{operation}' before").format(operation=entry[0]),
                    _(
                        "Inserts this special operation before the current cutplan entrys"
                    ),
                ),
            )
        menu.AppendSeparator()
        for entry in pre_items:
            self.Bind(
                wx.EVT_MENU,
                append_operation(entry[1]),
                menu.Append(
                    wx.ID_ANY,
                    _("Appends '{operation}' at end").format(operation=entry[0]),
                    _("Appends this special operation at the end of the cutplan"),
                ),
            )

        if menu.MenuItemCount != 0:
            gui.PopupMenu(menu)
            menu.Destroy()


class CutcodePanel(wx.Panel):
    """
    CutcodePanel is a panel that display cutplan Cutcode and allows to edit them
    """

    def __init__(self, *args, context=None, cutcode=None, plan_name=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        self.parent = args[0]
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.cutcode = cutcode
        self.plan_name = plan_name
        self.list_cutcode = wx.ListBox(self, wx.ID_ANY, choices=[], style=wx.LB_MULTIPLE)
        # self.text_operation_param = wx.TextCtrl(
        #     self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        # )
        # self.text_operation_param.SetToolTip(
        #     _("Modify operation parameter, press Enter to apply")
        # )

        self.list_cutcode.Bind(wx.EVT_RIGHT_DOWN, self.on_listbox_operation_rightclick)
        self.list_cutcode.Bind(wx.EVT_LISTBOX_DCLICK, self.on_listbox_operation_dclick)
        self.list_cutcode.Bind(wx.EVT_LISTBOX, self.on_listbox_operation_select)
        # self.text_operation_param.Bind(wx.EVT_TEXT_ENTER, self.on_text_operation_param)

        ops_sizer = wx.BoxSizer(wx.VERTICAL)
        ops_sizer.Add(self.list_cutcode, 1, wx.EXPAND, 0)
        # ops_sizer.Add(self.text_operation_param, 0, wx.EXPAND, 0)
        self.SetSizer(ops_sizer)
        self.Layout()
        self.set_cutcode_entry(self.cutcode, self.plan_name)

    def set_cutcode_entry(self, cutcode, plan_name):
        def name_str(e):
            res = ""
            if isinstance(e, RasterCut):
                res = f"Raster: {e.width} x {e.height}"
            elif isinstance(e, CubicCut):
                res = f"Cubic: ({e.start[0]:.0f}, {e.start[1]:.0f}) - ({e.end[0]:.0f}, {e.end[1]:.0f})"
                res += f" (c1=({e.c1()[0]:.0f}, {e.c1()[1]:.0f}), c2=({e.c2()[0]:.0f}, {e.c2()[1]:.0f}) )"
            elif isinstance(e, LineCut):
                res = f"Line: ({e.start[0]:.0f}, {e.start[1]:.0f}) - ({e.end[0]:.0f}, {e.end[1]:.0f})"
            elif isinstance(e, DwellCut):
                res = f"Dwell: {e.dwell_time}"
            elif isinstance(e, WaitCut):
                res = f"Wait: {e.dwell_time}"
            elif isinstance(e, HomeCut):
                res = f"Home"
            elif isinstance(e, GotoCut):
                coord = f"({e._start_x:.0f}, {e._start_y:.0f})"
                res = f"Goto: ({e.start[0]:.0f}, {e.start[1]:.0f}) {coord}"
            elif isinstance(e, InputCut):
                res = f"Input: {e.input_value:b} (mask: {e.input_mask:b})"
            elif isinstance(e, OutputCut):
                res = f"Output: {e.output_value:b} (mask: {e.output_mask:b})"
            elif isinstance(e, PlotCut):
                res = f"Plot: {len(e.plot)} points"
            elif isinstance(e, QuadCut):
                res = f"Quad: {e.start[0]:.0f}, {e.start[1]:.0f} - {e.end[0]:.0f}, {e.end[1]:.0f}"
                res += f" (c={e.c()[0]:.0f}, {e.c()[1]:.0f})"
            # elif isinstance(e, InfoCut):
            #     res = f"Info: {e.message}"
            elif isinstance(e, SetOriginCut):
                if e.set_current:
                    coord = "<current>"
                else:
                    coord = f"({e._start_x:.0f}, {e._start_y:.0f})"
                res = f"Set Origin: {coord}"
            elif isinstance(e, RawCut):
                res = f"Raw: {len(e.plot)} points"
            else:
                try:
                    res = e.__name__
                except AttributeError:
                    res = str(e)
            return res

        self.cutcode = cutcode
        self.plan_name = plan_name
        self.list_cutcode.Clear()
        self.list_cutcode.Enable(True)
        if self.cutcode is None:
            self.list_cutcode.InsertItems(
                [e for e in ("Please select a cutcode entry", "from the operations panel")], 0
            )
            self.list_cutcode.Enable(False)
        elif len(self.cutcode) != 0:
            self.list_cutcode.InsertItems([name_str(e) for e in self.cutcode], 0)

    def on_listbox_operation_drag_drop(self, event):
        idx1 = 0
        idx2 = 0
        temp = self.cutcode[idx1]
        self.cutcode[idx1] = self.cutcode[idx2]
        self.cutcode[idx2] = temp

    # def on_text_operation_param(self, event):
    #     content = self.text_operation_param.GetValue()
    #     idx = self.list_cutcode.GetSelection()
    #     flag = False
    #     if idx >= 0:
    #         op = self.cutcode[idx]
    #         if isinstance(op, ConsoleOperation):
    #             op.command = content
    #             flag = True
    #         elif isinstance(op, GotoOperation):
    #             params = content.split(",")
    #             x = 0
    #             y = 0
    #             if len(params) > 0:
    #                 try:
    #                     x = float(Length(params[0]))
    #                 except ValueError:
    #                     return
    #             if len(params) > 1:
    #                 try:
    #                     y = float(Length(params[1]))
    #                 except ValueError:
    #                     return
    #             op.x = x
    #             op.y = y
    #             flag = True
    #         elif isinstance(op, WaitOperation):
    #             try:
    #                 duration = float(content)
    #                 op.wait = duration
    #                 flag = True
    #             except ValueError:
    #                 return
    #         elif isinstance(op, SetOriginOperation):
    #             if content != "":
    #                 params = content.split(",")
    #                 x = 0
    #                 y = 0
    #                 if len(params) > 0:
    #                     try:
    #                         x = float(Length(params[0]))
    #                     except ValueError:
    #                         return
    #                 if len(params) > 1:
    #                     try:
    #                         y = float(Length(params[1]))
    #                     except ValueError:
    #                         return
    #                 op.x = x
    #                 op.y = y
    #                 flag = True
    #             else:
    #                 op.x = None
    #                 op.y = None
    #                 flag = True
    #     if flag:
    #         self.context.signal("plan", self.plan_name, 1)

    def on_listbox_operation_select(self, event):
        return
        # flag = False
        # content = ""
        # idx = self.list_cutcode.GetSelection()
        # if idx >= 0:
        #     op = self.cutcode[idx]
        #     if isinstance(op, ConsoleOperation):
        #         content = op.command
        #         flag = True
        #     elif isinstance(op, GotoOperation):
        #         content = str(op.x) + "," + str(op.y)
        #         flag = True
        #     elif isinstance(op, WaitOperation):
        #         content = str(op.wait)
        #         flag = True
        #     elif isinstance(op, SetOriginOperation):
        #         if op.x is None or op.y is None:
        #             content = ""
        #         else:
        #             content = str(op.x) + "," + str(op.y)
        #         flag = True

        # self.text_operation_param.SetValue(content)
        # self.text_operation_param.Enable(flag)

    def on_listbox_operation_dclick(self, event):
        # No useful logic yet, the old logic fails as it is opening a wrong node
        # There are no property panels for CutObjects yet
        return
        # node_index = self.list_cutcode.GetSelection()
        # if node_index == -1:
        #     return
        # obj = self.cutcode[node_index]
        # self.context.open("window/Properties", self)
        # self.context.kernel.activate_instance(obj)

    def on_listbox_operation_rightclick(self, event):
        def remove_operation(event):
            selected = self.list_cutcode.GetSelections()
            if selected is None or len(selected) == 0:
                return
            #
            idx = len(selected) - 1
            while idx>=0:
                entry = selected[idx]
                self.cutcode.pop(entry)
                idx -= 1
            self.context.signal("plan", self.plan_name, 1)

        def remove_before(event):
            selected = self.list_cutcode.GetSelections()
            if selected is None or len(selected) == 0:
                return
            #
            entry = selected[0]
            if entry > 0:
                del self.cutcode[:entry]
                self.context.signal("plan", self.plan_name, 1)

        def remove_after(event):
            selected = self.list_cutcode.GetSelections()
            if selected is None or len(selected) == 0:
                return
            #
            entry = selected[-1]
            if entry < len(self.cutcode) - 1:
                del self.cutcode[entry + 1:]
                self.context.signal("plan", self.plan_name, 1)

        def append_operation(cutcode):
            def check(event):
                self.cutcode.append(my_cutcode)
                self.context.signal("plan", self.plan_name, 1)

            my_cutcode = cutcode
            return check

        def insert_operation(cutcode):
            def check(event):
                selected = self.list_cutcode.GetSelections()
                if selected is None or len(selected) == 0:
                    return
                idx = selected[0]
                self.cutcode.insert(idx, my_cutcode)
                self.context.signal("plan", self.plan_name, 1)

            my_cutcode = cutcode
            return check

        selected = self.list_cutcode.GetSelections()
        if selected is None or len(selected) == 0:
            return
        sel_min = selected[0]
        sel_max = selected[-1]
        gui = self

        menu = wx.Menu()
        self.Bind(
            wx.EVT_MENU,
            remove_operation,
            menu.Append(
                wx.ID_ANY,
                _("Remove cutcode"),
                _("Removes the selected cutcode-entries from the active cutplan"),
            ),
        )
        if sel_min > 0:
            self.Bind(
                wx.EVT_MENU,
                remove_before,
                menu.Append(
                    wx.ID_ANY,
                    _("Delete cuts before"),
                    _("Delete all cuts before the first selected"),
                ),
            )
        if sel_max < len(self.cutcode) - 1:
            self.Bind(
                wx.EVT_MENU,
                remove_after,
                menu.Append(
                    wx.ID_ANY,
                    _("Delete cuts after"),
                    _("Delete all cuts after the last selected"),
                ),
            )
        standards = (
            ("Home", "home", ""),
            ("Set Origin", "origin", ""),
            ("Goto Origin", "goto", "0,0"),
            # ("Info", "info", "Still burning"),
            ("Wait", "wait", "5"),
        )
        pre_items = []
        for elem in standards:
            desc = elem[0]
            optype = elem[1]
            opparam = elem[2]

            if optype is not None:
                addop = None
                if optype == "console":
                    # addop = ConsoleOperation(command=opparam)
                    pass
                # elif optype == "info":
                #     addop = InfoCut(message=opparam)
                elif optype == "home":
                    addop = HomeCut()
                # elif optype == "util output":
                #     if opparam is not None:
                #         params = opparam.split(",")
                #         mask = 0
                #         setvalue = 0
                #         if len(params) > 0:
                #             try:
                #                 mask = int(params[0])
                #             except ValueError:
                #                 mask = 0
                #         if len(params) > 1:
                #             try:
                #                 setvalue = int(params[1])
                #             except ValueError:
                #                 setvalue = 0
                #         if mask != 0 or setvalue != 0:
                #             addop = OutputOperation(mask, setvalue)
                elif optype == "goto":
                    if opparam is not None:
                        params = opparam.split(",")
                        x = 0
                        y = 0
                        if len(params) > 0:
                            try:
                                x = float(Length(params[0]))
                            except ValueError:
                                x = 0
                        if len(params) > 1:
                            try:
                                y = float(Length(params[1]))
                            except ValueError:
                                y = 0
                        addop = GotoCut((x, y))
                elif optype == "origin":
                    if opparam is not None and opparam != "":
                        params = opparam.split(",")
                        x = 0
                        y = 0
                        if len(params) > 0:
                            try:
                                x = float(Length(params[0]))
                            except ValueError:
                                x = 0
                        if len(params) > 1:
                            try:
                                y = float(Length(params[1]))
                            except ValueError:
                                y = 0
                        addop = SetOriginCut((x, y))
                    else:
                        addop = SetOriginCut()
                elif optype == "wait":
                    if opparam is not None:
                        try:
                            opparam = float(opparam)
                        except ValueError:
                            opparam = None
                    if opparam is not None:
                        addop = WaitCut(wait=1000*opparam)
                if addop is not None:
                    pre_items.append([desc, addop])

        menu.AppendSeparator()
        for entry in pre_items:
            self.Bind(
                wx.EVT_MENU,
                insert_operation(entry[1]),
                menu.Append(
                    wx.ID_ANY,
                    _("Insert '{operation}' before").format(operation=entry[0]),
                    _(
                        "Inserts this special operation before the current cutplan entrys"
                    ),
                ),
            )
        menu.AppendSeparator()
        for entry in pre_items:
            self.Bind(
                wx.EVT_MENU,
                append_operation(entry[1]),
                menu.Append(
                    wx.ID_ANY,
                    _("Appends '{operation}' at end").format(operation=entry[0]),
                    _("Appends this special operation at the end of the cutplan"),
                ),
            )

        if menu.MenuItemCount != 0:
            gui.PopupMenu(menu)
            menu.Destroy()


class SimulationPanel(wx.Panel, Job):
    def __init__(self, *args, context=None, plan_name=None, auto_clear=True, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.parent = args[0]
        self.context = context
        self.plan_name = plan_name
        self.auto_clear = auto_clear

        Job.__init__(self)
        self._playback_cuts = True
        self._cut_end_time = []

        self.job_name = "simulate"
        self.run_main = True
        self.process = self.animate_sim
        self.interval = 0.1
        if plan_name:
            self.cutplan = self.context.planner.get_or_make_plan(plan_name)
        else:
            self.cutplan = self.context.planner.default_plan
        self.plan_name = self.cutplan.name
        self.operations = self.cutplan.plan
        # for e in self.operations:
        #     print(f"Init: {type(e).__name__} {e}")
        self.cutcode = CutCode()

        for c in self.operations:
            if isinstance(c, CutCode):
                self.cutcode.extend(c)
        self.cutcode = CutCode(self.cutcode.flat())
        self.statistics = self.cutcode.provide_statistics()

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
        self.btn_slide_options.SetToolTip(
            _("Show/Hide optimization options for this job.")
        )
        choices = self.context.lookup("choices/optimize")[:7]
        self.subpanel_optimize = wx.Panel(self, wx.ID_ANY)
        self.options_optimize = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=choices, scrolling=False
        )
        self.subpanel_operations = OperationsPanel(
            self, wx.ID_ANY, context=self.context, cutplan=self.cutplan
        )
        self.subpanel_cutcode = CutcodePanel(
            self, wx.ID_ANY, context=self.context, cutcode=None, plan_name=None
        )

        self.panel_optimize = wx.Notebook(self, wx.ID_ANY)
        self.subpanel_optimize.Reparent(self.panel_optimize)
        self.subpanel_operations.Reparent(self.panel_optimize)
        self.subpanel_cutcode.Reparent(self.panel_optimize)
        self.panel_optimize.AddPage(self.subpanel_optimize, _("Optimizations"))
        self.panel_optimize.AddPage(self.subpanel_operations, _("Operations"))
        self.panel_optimize.AddPage(self.subpanel_cutcode, _("Cutcode"))
        self.checkbox_optimize = wx.CheckBox(self, wx.ID_ANY, _("Optimize"))
        self.checkbox_optimize.SetToolTip(_("Enable/Disable Optimize"))
        self.checkbox_optimize.SetValue(1)
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
        self.text_time_extra = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
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
        self.text_time_extra_step = wx.TextCtrl(
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
        self.radio_cut = wx.RadioButton(self, wx.ID_ANY, _("Steps"))
        self.radio_time_seconds = wx.RadioButton(self, wx.ID_ANY, _("Time (sec.)"))
        self.radio_time_minutes = wx.RadioButton(self, wx.ID_ANY, _("Time (min)"))
        self.radio_cut.SetToolTip(
            _(
                "Cut operations Playback-Mode: play will jump from one completed operations to next"
            )
        )
        self.radio_time_seconds.SetToolTip(
            _("Timed Playback-Mode: play will jump from one second to next")
        )
        self.radio_time_minutes.SetToolTip(
            _("Timed Playback-Mode: play will jump from one minute to next")
        )

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
        # self.Bind(wx.EVT_COMBOBOX, self.on_combo_device, self.combo_device)
        self.Bind(wx.EVT_BUTTON, self.on_button_spool, self.button_spool)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_mouse_right_down)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_playback_mode, self.radio_cut)
        self.Bind(
            wx.EVT_RADIOBUTTON, self.on_radio_playback_mode, self.radio_time_seconds
        )
        self.Bind(
            wx.EVT_RADIOBUTTON, self.on_radio_playback_mode, self.radio_time_minutes
        )
        self.view_pane.scene_panel.Bind(wx.EVT_RIGHT_DOWN, self.on_mouse_right_down)
        self.Bind(wx.EVT_CHECKBOX, self.on_checkbox_optimize, self.checkbox_optimize)
        # end wxGlade

        ##############
        # BUILD SCENE
        ##############

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

        self.parent.add_module_delegate(self.options_optimize)
        self.context.setting(int, "simulation_mode", 0)
        default = self.context.simulation_mode
        if default == 0:
            self.radio_cut.SetValue(True)
        elif default == 1:
            self.radio_time_seconds.SetValue(True)
        elif default == 2:
            self.radio_time_minutes.SetValue(True)
        self.on_radio_playback_mode(None)

        self.running = False

    def __set_properties(self):
        self.text_distance_laser.SetToolTip(_("Distance Estimate: while Lasering"))
        self.text_distance_travel.SetToolTip(_("Distance Estimate: Traveling"))
        self.text_distance_total.SetToolTip(_("Distance Estimate: Total"))
        self.text_time_laser.SetToolTip(_("Time Estimate: Lasering Time"))
        self.text_time_travel.SetToolTip(_("Time Estimate: Traveling Time"))
        self.text_time_extra.SetToolTip(
            _("Time Estimate: Extra Time (ie to swing around)")
        )
        self.text_time_total.SetToolTip(_("Time Estimate: Total Time"))
        self.button_play.SetBitmap(icons8_play_50.GetBitmap())
        self.text_playback_speed.SetMinSize((55, 23))
        # self.combo_device.SetToolTip(_("Select the device"))
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
        self.text_time_extra.SetMinSize((35, -1))
        self.text_time_extra_step.SetMinSize((35, -1))
        v_sizer_main = wx.BoxSizer(wx.VERTICAL)
        h_sizer_scroll = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer_text_1 = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer_text_2 = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)

        sizer_execute = wx.BoxSizer(wx.VERTICAL)
        sizer_speed_options = wx.BoxSizer(wx.VERTICAL)
        sizer_pb_speed = wx.BoxSizer(wx.HORIZONTAL)
        sizer_total_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Total Time")), wx.HORIZONTAL
        )
        sizer_travel_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Travel Time")), wx.HORIZONTAL
        )
        sizer_laser_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Laser Time")), wx.HORIZONTAL
        )
        sizer_extra_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Extra Time")), wx.HORIZONTAL
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

        opt_sizer = wx.BoxSizer(wx.VERTICAL)
        self.options_optimize.Reparent(self.subpanel_optimize)
        self.checkbox_optimize.Reparent(self.subpanel_optimize)
        self.btn_redo_it.Reparent(self.subpanel_optimize)

        self.checkbox_optimize.SetMinSize(wx.Size(-1, 23))
        opt_sizer.Add(self.options_optimize, 1, wx.EXPAND, 0)
        opt_sizer.Add(self.checkbox_optimize, 0, wx.EXPAND, 0)
        opt_sizer.Add(self.btn_redo_it, 0, wx.EXPAND, 0)
        self.subpanel_optimize.SetSizer(opt_sizer)
        self.subpanel_optimize.Layout()

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

        sizer_extra_time.Add(self.text_time_extra_step, 1, wx.EXPAND, 0)
        sizer_extra_time.Add(self.text_time_extra, 1, wx.EXPAND, 0)
        h_sizer_text_2.Add(sizer_extra_time, 1, wx.EXPAND, 0)

        h_sizer_buttons.Add(self.button_play, 0, 0, 0)
        sizer_speed_options.Add(self.slider_playbackspeed, 0, wx.EXPAND, 0)

        label_playback_speed = wx.StaticText(self, wx.ID_ANY, _("Playback Speed") + " ")
        sizer_pb_speed.Add(label_playback_speed, 2, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_pb_speed.Add(self.text_playback_speed, 1, wx.EXPAND, 0)

        sizer_display = wx.BoxSizer(wx.HORIZONTAL)
        label_playback_mode = wx.StaticText(self, wx.ID_ANY, _("Mode") + " ")
        sizer_display.Add(label_playback_mode, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        # Make sure it has about textbox size, otherwise too narrow
        self.radio_cut.SetMinSize(wx.Size(-1, 23))
        sizer_display.Add(self.radio_cut, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_display.Add(self.radio_time_seconds, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_display.Add(self.radio_time_minutes, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_speed_options.Add(sizer_pb_speed, 0, wx.EXPAND, 0)
        sizer_speed_options.Add(sizer_display, 0, wx.EXPAND, 0)
        h_sizer_buttons.Add(sizer_speed_options, 1, wx.EXPAND, 0)
        # sizer_execute.Add(self.combo_device, 0, wx.EXPAND, 0)
        sizer_execute.Add(self.button_spool, 1, wx.EXPAND, 0)
        h_sizer_buttons.Add(sizer_execute, 1, wx.EXPAND, 0)

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

    def set_cutcode_entry(self, cutcode):
        self.subpanel_cutcode.set_cutcode_entry(cutcode, self.plan_name)

    def progress_to_idx(self, progress):
        residual = 0
        idx = progress
        if not self._playback_cuts:
            # progress is the time indicator
            idx = len(self.statistics) - 1
            prev_time = None
            while idx >= 0:
                item = self.statistics[idx]
                this_time = item["time_at_end_of_burn"]
                # print (f"{idx} {this_time} vs {progress} - {item}")
                if this_time <= progress:
                    if prev_time is not None:
                        # We compute a 0 to 1 ratio of the progress
                        residual = (progress - this_time) / (prev_time - this_time)
                    break
                prev_time = this_time
                idx -= 1
            idx += 1
            if idx == 0:
                item = self.statistics[idx]
                start_time = item["time_at_start"]
                this_time = item["time_at_end_of_burn"]
                residual = (progress - start_time) / (this_time - start_time)

        if idx >= len(self.statistics):
            idx = len(self.statistics) - 1
        if idx < 0:
            idx = 0
        # print(
        #     f"Cut-Mode={self._playback_cuts}, prog={progress}, idx={idx}, stats={len(self.statistics)}"
        # )
        return idx, residual

    def on_mouse_right_down(self, event=None):
        def cut_before(event):
            step, residual = self.progress_to_idx(self.progress)
            self.context(f"plan{self.plan_name} sublist {step} -1\n")

        def cut_after(event):
            step, residual = self.progress_to_idx(self.progress)
            self.context(f"plan{self.plan_name} sublist 0 {step}\n")

        gui = self
        menu = wx.Menu()
        if self.radio_cut.GetValue():
            self.Bind(
                wx.EVT_MENU,
                cut_before,
                menu.Append(
                    wx.ID_ANY,
                    _("Delete cuts before"),
                    _("Delete all cuts before the current position in Simulation"),
                ),
            )
            self.Bind(
                wx.EVT_MENU,
                cut_after,
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

    def _set_slider_dimensions(self):
        if self._playback_cuts:
            self.max = max(len(self.cutcode), 1)
        else:
            totalduration = 0
            maxidx = len(self.statistics)
            if maxidx > 0:
                totalduration = int(
                    self.statistics[-1]["total_time_extra"]
                    + self.statistics[-1]["total_time_travel"]
                    + self.statistics[-1]["total_time_cut"]
                )
            self.max = max(totalduration, 1)
        self.progress = self.max
        self.slider_progress.SetMin(0)
        self.slider_progress.SetMax(self.max)
        self.slider_progress.SetValue(self.max)
        value = self.slider_playbackspeed.GetValue()
        value = int((10.0 ** (value // 90)) * (1.0 + float(value % 90) / 10.0))
        if self.radio_cut.GetValue():
            factor = 0.1  # steps
        else:
            factor = 1  # seconds
        self.interval = factor * 100.0 / float(value)

    def _refresh_simulated_plan(self):

        # Stop animation
        if self.running:
            self._stop()
            return
        # Refresh cutcode
        if self.plan_name:
            self.cutplan = self.context.planner.get_or_make_plan(self.plan_name)
        else:
            self.cutplan = self.context.planner.default_plan
        self.plan_name = self.cutplan.name
        self.operations = self.cutplan.plan
        self.subpanel_cutcode.set_cutcode_entry(None, self.plan_name)
        self.subpanel_operations.SetCutPlan(self.cutplan)
        # for e in self.operations:
        #     print(f"Refresh: {type(e).__name__} {e}")
        #     try:
        #         idx = 0
        #         for n in e:
        #             print(f"Entry {idx}#: {name_str(n)}")
        #             idx += 1
        #     except:
        #         pass

        self.cutcode = CutCode()

        for c in self.operations:
            if isinstance(c, CutCode):
                self.cutcode.extend(c)
        self.cutcode = CutCode(self.cutcode.flat())
        self.statistics = self.cutcode.provide_statistics()
        # for idx, stat in enumerate(self.statistics):
        #     print(f"#{idx}: {stat}")
        self._set_slider_dimensions()
        self.sim_travel.initvars()
        self.update_fields()
        self.request_refresh()

    @signal_listener("plan")
    def on_plan_change(self, origin, plan_name, status):
        if plan_name == self.plan_name:
            self._refresh_simulated_plan()

    def on_radio_playback_mode(self, event):
        self._playback_cuts = self.radio_cut.GetValue()
        default = 0
        if self.radio_cut.GetValue():
            default = 0
        elif self.radio_time_seconds.GetValue():
            default = 1
        elif self.radio_time_minutes.GetValue():
            default = 2
        self.context.simulation_mode = default
        self._set_slider_dimensions()

    def on_checkbox_optimize(self, event):
        if self.checkbox_optimize.GetValue():
            self.options_optimize.Enable(True)
        else:
            self.options_optimize.Enable(False)

    def update_fields(self):
        step, residual = self.progress_to_idx(self.progress)
        item = self.statistics[step - 1]
        partials = {
            "total_distance_travel": 0,
            "total_distance_cut": 0,
            "total_time_travel": 0,
            "total_time_cut": 0,
            "total_time_extra": 0,
        }
        if residual != 0 and step < len(self.statistics):
            itemnext = self.statistics[step]
            for entry in partials:
                partials[entry] = residual * (itemnext[entry] - item[entry])

        ###################
        # UPDATE POSITIONAL
        ###################

        mm = self.cutcode.settings.get("native_mm", 39.3701)
        # item = (i, distance_travel, distance_cut, extra, duration_travel, duration_cut)
        travel_mm = (
            item["total_distance_travel"] + partials["total_distance_travel"]
        ) / mm
        cuts_mm = (item["total_distance_cut"] + partials["total_distance_cut"]) / mm
        # travel_mm = self.cutcode.length_travel(stop_at=step) / mm
        # cuts_mm = self.cutcode.length_cut(stop_at=step) / mm
        self.text_distance_travel_step.SetValue(f"{travel_mm:.0f}mm")
        self.text_distance_laser_step.SetValue(f"{cuts_mm:.0f}mm")
        self.text_distance_total_step.SetValue(f"{travel_mm + cuts_mm:.0f}mm")
        try:
            time_travel = item["total_time_travel"] + partials["total_time_travel"]
            t_hours = int(time_travel // 3600)
            t_mins = int((time_travel % 3600) // 60)
            t_seconds = int(time_travel % 60)
            self.text_time_travel_step.SetValue(
                f"{int(t_hours)}:{int(t_mins):02d}:{int(t_seconds):02d}"
            )
        except ZeroDivisionError:
            time_travel = 0
        try:
            time_cuts = item["total_time_cut"] + partials["total_time_cut"]
            t_hours = int(time_cuts // 3600)
            t_mins = int((time_cuts % 3600) // 60)
            t_seconds = int(time_cuts % 60)
            self.text_time_laser_step.SetValue(
                f"{int(t_hours)}:{int(t_mins):02d}:{int(t_seconds):02d}"
            )
        except ZeroDivisionError:
            time_cuts = 0
        try:
            extra = item["total_time_extra"] + partials["total_time_extra"]
            t_hours = int(extra // 3600)
            t_mins = int((extra % 3600) // 60)
            t_seconds = int(extra % 60)
            self.text_time_extra_step.SetValue(
                f"{int(t_hours)}:{int(t_mins):02d}:{int(t_seconds):02d}"
            )
            time_total = time_travel + time_cuts + extra
            if self._playback_cuts:
                time_total = time_travel + time_cuts + extra
            else:
                time_total = self.progress
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

        travel_mm = self.statistics[-1]["total_distance_travel"] / mm
        cuts_mm = self.statistics[-1]["total_distance_cut"] / mm
        self.text_distance_travel.SetValue(f"{travel_mm:.0f}mm")
        self.text_distance_laser.SetValue(f"{cuts_mm:.0f}mm")
        self.text_distance_total.SetValue(f"{travel_mm + cuts_mm:.0f}mm")

        try:
            time_travel = self.statistics[-1]["total_time_travel"]
            t_hours = int(time_travel // 3600)
            t_mins = int((time_travel % 3600) // 60)
            t_seconds = int(time_travel % 60)
            self.text_time_travel.SetValue(f"{t_hours}:{t_mins:02d}:{t_seconds:02d}")
        except ZeroDivisionError:
            time_travel = 0
        try:
            time_cuts = self.statistics[-1]["total_time_cut"]
            t_hours = int(time_cuts // 3600)
            t_mins = int((time_cuts % 3600) // 60)
            t_seconds = int(time_cuts % 60)
            self.text_time_laser.SetValue(f"{t_hours}:{t_mins:02d}:{t_seconds:02d}")
        except ZeroDivisionError:
            time_cuts = 0
        try:
            extra = self.statistics[-1]["total_time_extra"]
            t_hours = int(extra // 3600)
            t_mins = int((extra % 3600) // 60)
            t_seconds = int(extra % 60)
            self.text_time_extra.SetValue(f"{t_hours}:{t_mins:02d}:{t_seconds:02d}")
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
            plan = self.plan_name
            if self.checkbox_optimize.GetValue():
                opt = " optimize"
            else:
                opt = ""
            self.context(
                f"plan{plan} clear\nplan{plan} copy preprocess validate blob preopt{opt}\n"
            )
        self._refresh_simulated_plan()

    def pane_show(self):
        self.context.setting(str, "units_name", "mm")

        bbox = self.context.device.bbox()
        self.widget_scene.widget_root.focus_viewport_scene(
            bbox, self.view_pane.Size, 0.1
        )
        self.update_fields()
        # self.panel_optimize.pane_show()
        self.panel_optimize.Show()

    def pane_hide(self):
        if self.auto_clear:
            self.context(f"plan{self.plan_name} clear\n")
        self.context.close("SimScene")
        self.context.unschedule(self)
        self.running = False
        # self.panel_optimize.pane_hide()
        try:
            self.panel_optimize.Hide()
        except RuntimeError:
            pass

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
        if self.radio_time_minutes.GetValue():
            self.progress += 60
        else:
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
        if self.radio_cut.GetValue():
            factor = 0.1  # steps
        else:
            factor = 1  # seconds
        self.interval = factor * 100.0 / float(value)

        self.text_playback_speed.SetValue(f"{value}%")

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
        self.last_msg = None

    def process_draw(self, gc: wx.GraphicsContext):
        if self.sim.progress >= 0:
            residual = 0
            idx = 0
            if self.sim.progress < self.sim.max:
                idx, residual = self.sim.progress_to_idx(self.sim.progress)
                # print(f"SimWidget, idx={idx}, residual={residual:.3f}")
                sim_cut = self.sim.cutcode[:idx]
            else:
                sim_cut = self.sim.cutcode
            self.renderer.draw_cutcode(sim_cut, gc, 0, 0)
            if residual > 0:
                # We draw interpolated lines to acknowledge we are in the middle of a cut operation
                starts = []
                ends = []
                cutstart = wx.Point2D(self.sim.cutcode[idx].start)
                cutend = wx.Point2D(self.sim.cutcode[idx].end)
                if self.sim.statistics[idx]["type"] == "RasterCut":
                    # Rastercut object.
                    x = 0
                    y = 0
                    cut = self.sim.cutcode[idx]
                    image = cut.image
                    gc.PushState()
                    matrix = Matrix.scale(cut.step_x, cut.step_y)
                    matrix.post_translate(
                        cut.offset_x + x, cut.offset_y + y
                    )  # Adjust image xy
                    gc.ConcatTransform(
                        wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix))
                    )
                    try:
                        cache = cut.cache
                        cache_id = cut.cache_id
                    except AttributeError:
                        cache = None
                        cache_id = -1
                    if cache_id != id(image):
                        # Cached image is invalid.
                        cache = None
                    if cache is None:
                        # No valid cache. Generate.
                        cut._cache_width, cut._cache_height = image.size
                        try:
                            cut.cache = self.renderer.make_thumbnail(
                                image, maximum=5000
                            )
                        except (MemoryError, RuntimeError):
                            cut.cache = None
                        cut.cache_id = id(image)
                    # Set draw - constraint
                    clip_x = 0
                    clip_y = 0
                    clip_w = cut._cache_width
                    clip_h = cut._cache_height
                    mode = ""
                    if cut.horizontal:
                        if cut.start_on_top:
                            mode = "T2B"
                        else:
                            mode = "B2T"
                    else:
                        if cut.start_on_left:
                            mode = "L2R"
                        else:
                            mode = "R2L"

                    # msg = f"Mode: {mode}, Horiz: {cut.horizontal}, from left: {cut.start_on_left}, from top: {cut.start_on_top}"
                    # if msg != self.last_msg:
                    #     print (msg)
                    #     self.last_msg = msg
                    if mode == "T2B":
                        clip_w = cut._cache_width
                        clip_h = int(residual * cut._cache_height)
                        clip_x = 0
                        clip_y = 0
                    elif mode == "B2T":
                        clip_w = cut._cache_width
                        clip_h = int(residual * cut._cache_height)
                        clip_x = 0
                        clip_y = cut._cache_height - clip_h
                    elif mode == "L2R":
                        clip_w = int(residual * cut._cache_width)
                        clip_h = cut._cache_height
                        clip_x = 0
                        clip_y = 0
                    elif mode == "R2L":
                        clip_w = int(residual * cut._cache_width)
                        clip_h = cut._cache_height
                        clip_x = cut._cache_width - clip_w
                        clip_y = 0
                    gc.Clip(clip_x, clip_y, clip_w, clip_h)
                    if cut.cache is not None:
                        # Cache exists and is valid.
                        gc.DrawBitmap(
                            cut.cache, 0, 0, cut._cache_width, cut._cache_height
                        )
                        # gc.SetBrush(wx.RED_BRUSH)
                        # gc.DrawRectangle(0, 0, cut._cache_width, cut._cache_height)
                    else:
                        # Image was too large to cache, draw a red rectangle instead.
                        gc.SetBrush(wx.RED_BRUSH)
                        gc.DrawRectangle(0, 0, cut._cache_width, cut._cache_height)
                        gc.DrawBitmap(
                            icons8_image_50.GetBitmap(),
                            0,
                            0,
                            cut._cache_width,
                            cut._cache_height,
                        )
                    gc.ResetClip()
                    gc.PopState()

                    # # We draw a rectangle covering the raster area
                    # spath = str(self.sim.cutcode[idx].path)
                    # sparse = re.compile(" ([0-9,\.]*) ")
                    # min_x = None
                    # max_x = None
                    # path_width = 0
                    # for numpair in sparse.findall(spath):
                    #     comma_idx = numpair.find(",")
                    #     if comma_idx >= 0:
                    #         left_num = numpair[:comma_idx]
                    #         right_num = numpair[comma_idx + 1 :]
                    #         # print (f"'{numpair}' -> '{left_num}', '{right_num}'")
                    #         try:
                    #             c_x = float(left_num)
                    #             c_y = float(right_num)
                    #             if min_x is None:
                    #                 min_x = c_x
                    #                 max_x = c_x
                    #             else:
                    #                 if c_x < min_x:
                    #                     min_x = c_x
                    #                 if c_x > max_x:
                    #                     max_x = c_x
                    #                 path_width = max_x - min_x
                    #         except ValueError:
                    #             pass
                    # print(f"path={self.sim.cutcode[idx].path}")
                    # print(f"Raster: ({cutstart[0]}, {cutstart[1]}) - ({cutend[0]}, {cutend[1]})")
                    # print(f"w={abs(cutend[0] - cutstart[0])}, w-cutop = {2*self.sim.cutcode[idx].width}, w_path={path_width}")
                    # c_vars = vars(self.sim.cutcode[idx])
                    # for cv in c_vars:
                    #     print(f"{cv}={c_vars[cv]}")
                    # rect_y = cutstart[1]
                    # rect_x = self.sim.cutcode[idx].offset_x
                    # rect_w = max(2 * self.sim.cutcode[idx].width, path_width)
                    rect_h = residual * (cutend[1] - cutstart[1])
                    # interim_pen = wx.Pen(wx.GREEN, 1, wx.PENSTYLE_SOLID)
                    # gc.SetPen(interim_pen)
                    # gc.DrawRectangle(rect_x, rect_y, rect_w, rect_h)
                else:
                    end = wx.Point2D(
                        cutstart[0] + residual * (cutend[0] - cutstart[0]),
                        cutstart[1] + residual * (cutend[1] - cutstart[1]),
                    )
                    starts.append(cutstart)
                    ends.append(end)
                    interim_pen = wx.Pen(wx.GREEN, 1, wx.PENSTYLE_SOLID)
                    gc.SetPen(interim_pen)
                    gc.StrokeLineSegments(starts, ends)


class SimulationTravelWidget(Widget):
    """
    The simulation Travel Widget is responsible for the background of dotted lines and arrows
    within the simulation scene.
    """

    def __init__(self, scene, sim):
        Widget.__init__(self, scene, all=False)
        self.sim_matrix = scene.context.device.device_to_scene_matrix()
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
                    # This is a travel
                    start = wx.Point2D(*prev.end)
                    end = wx.Point2D(*curr.start)
                    self.starts.append(start)
                    self.ends.append(end)
                    # print (f"Travel found at idx {i}, {start}->{end}")
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
            else:
                end = wx.Point2D(*curr.start)
                self.starts = list()
                self.ends = list()
                self.starts.append(wx.Point2D(0, 0))
                self.ends.append(end)
            self.pos.append(len(self.starts))
            prev = curr

    def process_draw(self, gc: wx.GraphicsContext):
        if len(self.pos):
            residual = 0
            if self.sim.progress < self.sim.max:
                idx, residual = self.sim.progress_to_idx(self.sim.progress)
                pos = self.pos[idx]
                # print(f"TravelWidget, idx={idx}, residual={residual:.3f}, pos={pos}")
            else:
                pos = self.pos[-1]
            if pos >= 0:
                starts = self.starts[:pos]
                ends = self.ends[:pos]
                if residual > 0 and idx > 0:
                    p1 = self.sim.cutcode[idx - 1].end
                    p2 = self.sim.cutcode[idx - 1].start
                    # progress = time
                    t1 = self.sim.statistics[idx - 1]
                    t2 = self.sim.statistics[idx]
                    end_time = t1["time_at_end_of_travel"]
                    # Time after travel.
                    new_time = t2["time_at_end_of_travel"]
                    if (
                        t1["total_time_travel"] != t2["total_time_travel"]
                    ):  # Travel time
                        fact = (min(self.sim.progress, new_time) - end_time) / (
                            new_time - end_time
                        )
                        newstart = wx.Point2D(p1[0], p1[1])
                        newend = wx.Point2D(
                            p1[0] + fact * (p2[0] - p1[0]),
                            p1[1] + fact * (p2[1] - p1[1]),
                        )
                        mystarts = list()
                        myends = list()
                        mystarts.append(newstart)
                        myends.append(newend)
                        interim_pen = wx.Pen(wx.GREEN, 1, wx.PENSTYLE_DOT)
                        gc.SetPen(interim_pen)
                        gc.StrokeLineSegments(mystarts, myends)
                gc.SetPen(wx.BLACK_DASHED_PEN)
                gc.StrokeLineSegments(starts, ends)
                # for idx, pt_start in enumerate(starts):
                #     pt_end = ends[idx]
                #     print (f"#{idx}: ({pt_start[0]:.0f}, {pt_start[1]:.0f}) - ({pt_end[0]:.0f}, {pt_end[1]:.0f})")
                # starts = list()
                # ends = list()
                # starts.append(wx.Point2D(0, 0))
                # ends.append(wx.Point2D(10000, 10000))
                # starts.append(wx.Point2D(0, 10000))
                # ends.append(wx.Point2D(10000, 0))
                # gc.SetPen(wx.CYAN_PEN)
                # gc.StrokeLineSegments(starts, ends)


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
            # self.sim.progress > 0 and
            self.sim.cutcode is not None
            and len(self.sim.cutcode)
        ):
            idx, residual = self.sim.progress_to_idx(self.sim.progress)
            dx = 0
            dy = 0
            if self.sim.progress != self.sim.max:
                if idx > 0:
                    pos = self.sim.cutcode[idx - 1].end
                else:
                    pos = self.sim.cutcode[idx].start
                if residual > 0:
                    # We could still be traversing or already burning...
                    # We have two time stamps one after travel,
                    # one after burn
                    item = self.sim.statistics[idx]
                    # print(
                    #     f"Time stamp: {self.sim.progress}, "
                    #     + f"at start: {item['time_at_start']}, "
                    #     + f"after travel: {item['time_at_end_of_travel']}, "
                    #     + f"after burn: {item['time_at_end_of_burn']}"
                    # )
                    if self.sim.progress < item["time_at_end_of_travel"]:
                        # All travel done...
                        fraction = (self.sim.progress - item["time_at_start"]) / (
                            item["time_at_end_of_travel"] - item["time_at_start"]
                        )
                        pos = self.sim.cutcode[idx - 1].end
                        npos = self.sim.cutcode[idx].start
                    else:
                        # Still travelling, duration
                        fraction = (
                            self.sim.progress - item["time_at_end_of_travel"]
                        ) / (
                            item["time_at_end_of_burn"] - item["time_at_end_of_travel"]
                        )
                        pos = self.sim.cutcode[idx].start
                        npos = self.sim.cutcode[idx].end

                    dx = fraction * (npos[0] - pos[0])
                    dy = fraction * (npos[1] - pos[1])
            else:
                pos = self.sim.cutcode[idx].end
            x = pos[0] + dx
            y = pos[1] + dy
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
                    "planz copy preprocess validate blob preopt optimize\nwindow toggle Simulation z\n"
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
