from copy import copy

import wx

from meerk40t.core.units import Angle, Length
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.wxutils import (
    EditableListCtrl,
    ScrolledPanel,
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxButton,
    wxCheckBox,
    wxComboBox,
    wxRadioBox,
    wxStaticBitmap,
    wxStaticText,
)
from meerk40t.kernel import Context
from meerk40t.svgelements import Color

_ = wx.GetTranslation


class ChoicePropertyPanel(ScrolledPanel):
    """
    ChoicePropertyPanel is a generic panel that presents a list of properties to be viewed and edited.
    In most cases it can be initialized by passing a choices value which will read the registered choice values
    and display the given properties, automatically generating an appropriate changers for that property.

    In most cases the ChoicePropertyPanel should be used for properties of a dynamic nature. A lot of different
    relationships can be established and the class should be kept fairly easy to extend. With a set dictionary
    either registered in the Kernel as a choice or called directly on the ChoicePropertyPanel you can make dynamic
    controls to set various properties. This avoids needing to create a new static window when a panel is just
    providing options to change settings.
    The choices need to be provided either as list of dictionaries or indirectly via
    a string indicating a stored list registered in the given context under "choices"
    The dictionary recognizes the following entries:

        "object": The object to which the property defined in attr belongs to
        "attr": The name of the attribute
        "default": The default value if no value has been given before
        "label": The label will be used for labelling the to be created UI-elements
        "trailer": this text will be displayed immediately after the element
        "tip": The tooltip that will be used for this element
        "dynamic": a function called with the current dictionary choice. This is to update
            values that may have changed since the choice was first established.
        "type": This can be one of (no quotation marks, real python data types):
            bool: will always be represented by a checkbox
            str: normally be represented by a textbox (may be influenced by style)
            int: normally be represented by a textbox (may be influenced by style)
            float: normally be represented by a textbox (may be influenced by style)
            Length: represented by a textbox
            Angle: represented by a textbox
            Color: represented by a color picker
        "style": If given then the standard representation for a data-type (see above)
            will be replaced by more tailored UI-elements:
            "file": (only available for str) a file selection dialog is used,
                this recognizes a further property "wildcard"
            "slider:" Creates a slider (for int and float) that will use two additional
                entries, "min" and "max.
            "combo": see combosmall (but larger).
            "option": Creates a combo box but also takes "display" as a parameter
                that displays these strings rather than the underlying choices.
            "combosmall": Available for str, int, float will fill the combo
                with values defined in "choices" (additional parameter)
            "binary": uses two additional settings "mask" and "bit" to
                allow the bitwise manipulation of an int data type
            "multiline": (only available for str) the content allows multiline input
        "weight": only valid in subsections, default value 1, i.e. equal width
            allocation, can be changed to force a different sizing behaviour
    UI-Appearance
        "page":
        "section":
        "subsection":
        "priority":
            These entries will create visible separation/joining of elements.
            The dictionary list will be sorted first by priority, then page,
            then section, then subsection. While normally every item ends up
            on a new line, elements within a subsection remain in one horizontal
            container.
        Notabene:
            a) to influence ordering without compromising the intended Page,
            Section etc. names, the routine will remove a leading "_xxxx_" string
            b) The Page, Section etc. names will be translated, so please provide
            them in plain English

    There are some special hacks to influence appearance / internal logic
        "hidden": if set then this expert property will only appear if the
            developer-mode has been set
        "enabled": Is the control enabled (default yes, so does not need to be
            provided)
        "conditional": if given as tuple (cond_obj, cond_prop) then the (boolean)
            value of the property cond_obj.cond_prop will decide if the element
            will be enabled or not. (If a third value then the value must equal that value).
        "signals": This for advanced treatment, normally any change to a property
            will be announced to the wider mk-universe by sending a signal with the
            attributes name as signal-indicator (this is used to inform other UI-
            elements with the same content of such a change). If you want to invoke
            additional logic (or don't want to write a specific signal-listen routine
            to forward it to other routines) then you can add a single signal-name
            or a list of signal-names to be called
    """

    def __init__(
        self,
        *args,
        context: Context = None,
        choices=None,
        scrolling=True,
        constraint=None,
        entries_per_column=None,
        injector=None,
        **kwds,
    ):
        # constraints are either
        # - None (default) - all choices will be display
        # - a pair of integers (start, end), from where to where (index) to display
        #   use case: display the first 10 entries constraint=(0, 9)
        #   then the remaining: constraint=(10, -1)
        #   -1 defines the min / max boundaries
        # - a list of strings that describe
        #   the pages to show : constraint=("page1", "page2")
        #   the pages to omit : constraint=("-page1", "-page2")
        #   a leading hyphen establishes omission
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.listeners = list()
        self.entries_per_column = entries_per_column
        if choices is None:
            return
        if isinstance(choices, str):
            choices = [choices]

        new_choices = []
        # we need to create an independent copy of the lookup, otherwise
        # any amendments to choices like injector will affect the original
        standardhelp = ""
        
        def on_combo_text(param, ctrl, obj, dtype, addsig):
            def select(event=None):
                v = dtype(ctrl.GetValue())
                current_value = getattr(obj, param)
                if current_value != v:
                    setattr(obj, param, v)
                    self.context.signal(param, v, obj)
                    for _sig in addsig:
                        self.context.signal(_sig)

            return select

        def on_button(param, obj, addsig):
            def check(event=None):
                # We just set it to True to kick it off
                setattr(obj, param, True)
                # We don't signal ourselves...
                self.context.signal(param, True, obj)
                for _sig in addsig:
                    self.context.signal(_sig)

            return check

        def on_checkbox_check(param, ctrl, obj, addsig):
            def check(event=None):
                v = ctrl.GetValue()
                current_value = getattr(obj, param)
                if current_value != bool(v):
                    setattr(obj, param, bool(v))
                    self.context.signal(param, v, obj)
                    for _sig in addsig:
                        self.context.signal(_sig)

            return check

        def on_checkbox_bitcheck(param, ctrl, obj, bit, addsig, enable_ctrl=None):
            def check(event=None):
                v = ctrl.GetValue()
                if enable_ctrl is not None:
                    enable_ctrl.Enable(v)
                current = getattr(obj, param)
                if v:
                    current |= 1 << bit
                else:
                    current = ~((~current) | (1 << bit))
                current_value = getattr(obj, param)
                if current_value != current:
                    setattr(obj, param, current)
                    self.context.signal(param, v, obj)
                    for _sig in addsig:
                        self.context.signal(_sig)

            return check

        def on_generic_multi(param, ctrl, obj, dtype, addsig):
            def text():
                v = ctrl.GetValue()
                try:
                    dtype_v = dtype(v)
                    current_value = getattr(obj, param)
                    if current_value != dtype_v:
                        setattr(obj, param, dtype_v)
                        self.context.signal(param, dtype_v, obj)
                        for _sig in addsig:
                            self.context.signal(_sig)
                except ValueError:
                    # cannot cast to data_type, pass
                    pass

            return text

        def on_button_filename(param, ctrl, obj, wildcard, addsig):
            def click(event=None):
                with wx.FileDialog(
                    self,
                    label,
                    wildcard=wildcard if wildcard else "*",
                    style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW,
                ) as fileDialog:
                    if fileDialog.ShowModal() == wx.ID_CANCEL:
                        return  # the user changed their mind
                    pathname = str(fileDialog.GetPath())
                    ctrl.SetValue(pathname)
                    self.Layout()
                    current_value = getattr(obj, param)
                    if current_value != pathname:
                        try:
                            setattr(obj, param, pathname)
                            self.context.signal(param, pathname, obj)
                            for _sig in addsig:
                                self.context.signal(_sig)
                        except ValueError:
                            # cannot cast to data_type, pass
                            pass

            return click

        def on_file_text(param, ctrl, obj, dtype, addsig):
            def filetext():
                v = ctrl.GetValue()
                try:
                    dtype_v = dtype(v)
                    current_value = getattr(obj, param)
                    if current_value != dtype_v:
                        setattr(obj, param, dtype_v)
                        self.context.signal(param, dtype_v, obj)
                        for _sig in addsig:
                            self.context.signal(_sig)
                except ValueError:
                    # cannot cast to data_type, pass
                    pass

            return filetext

        def on_slider(param, ctrl, obj, dtype, addsig):
            def select(event=None):
                v = dtype(ctrl.GetValue())
                current_value = getattr(obj, param)
                if current_value != v:
                    setattr(obj, param, v)
                    self.context.signal(param, v, obj)
                    for _sig in addsig:
                        self.context.signal(_sig)

            return select

        def on_radio_select(param, ctrl, obj, dtype, addsig):
            def select(event=None):
                if dtype == int:
                    v = dtype(ctrl.GetSelection())
                else:
                    v = dtype(ctrl.GetLabel())
                current_value = getattr(obj, param)
                if current_value != v:
                    setattr(obj, param, v)
                    self.context.signal(param, v, obj)
                    for _sig in addsig:
                        self.context.signal(_sig)

            return select

        def on_combosmall_option(param, ctrl, obj, dtype, addsig, choice_list):
            def select(event=None):
                cl = choice_list[ctrl.GetSelection()]
                v = dtype(cl)
                current_value = getattr(obj, param)
                if current_value != v:
                    setattr(obj, param, v)
                    self.context.signal(param, v, obj)
                    for _sig in addsig:
                        self.context.signal(_sig)

            return select

        def on_combosmall_text(param, ctrl, obj, dtype, addsig):
            def select(event=None):
                v = dtype(ctrl.GetValue())
                current_value = getattr(obj, param)
                if current_value != v:
                    # print (f"Setting it to {v}")
                    setattr(obj, param, v)
                    self.context.signal(param, v, obj)
                    for _sig in addsig:
                        self.context.signal(_sig)

            return select

        def on_button_color(param, ctrl, obj, addsig):
            def click(event=None):
                color_data = wx.ColourData()
                color_data.SetColour(wx.Colour(swizzlecolor(ctrl.color)))
                dlg = wx.ColourDialog(self, color_data)
                if dlg.ShowModal() == wx.ID_OK:
                    color_data = dlg.GetColourData()
                    data = Color(
                        swizzlecolor(color_data.GetColour().GetRGB()), 1.0
                    )
                    set_color(ctrl, data)
                    try:
                        data_v = data.hexa
                        current_value = getattr(obj, param)
                        if current_value != data_v:
                            setattr(obj, param, data_v)
                            self.context.signal(param, data_v, obj)
                            for _sig in addsig:
                                self.context.signal(_sig)
                    except ValueError:
                        # cannot cast to data_type, pass
                        pass

            return click
        
        def on_angle_text(param, ctrl, obj, dtype, addsig):
            def text():
                try:
                    v = Angle(ctrl.GetValue(), digits=5)
                    data_v = str(v)
                    current_value = str(getattr(obj, param))
                    if current_value != data_v:
                        setattr(obj, param, data_v)
                        self.context.signal(param, data_v, obj)
                        for _sig in addsig:
                            self.context.signal(_sig)
                except ValueError:
                    # cannot cast to data_type, pass
                    pass

            return text

        def on_chart_start(columns, param, ctrl, local_obj):
            def chart_start(event=None):
                for column in columns:
                    if column.get("editable", False):
                        event.Allow()
                    else:
                        event.Veto()

            return chart_start

        def on_chart_stop(columns, param, ctrl, local_obj):
            def chart_stop(event=None):
                row_id = event.GetIndex()  # Get the current row
                col_id = event.GetColumn()  # Get the current column
                new_data = event.GetLabel()  # Get the changed data
                ctrl.SetItem(row_id, col_id, new_data)
                column = columns[col_id]
                c_attr = column.get("attr")
                c_type = column.get("type")
                values = getattr(local_obj, param)
                if isinstance(values[row_id], dict):
                    values[row_id][c_attr] = c_type(new_data)
                    self.context.signal(param, values, row_id, param)
                elif isinstance(values[row_id], str):
                    values[row_id] = c_type(new_data)
                    self.context.signal(param, values, row_id)
                else:
                    values[row_id][col_id] = c_type(new_data)
                    self.context.signal(param, values, row_id)

            return chart_stop

        def on_chart_contextmenu(
            columns, param, ctrl, local_obj, allow_del, allow_dup, default
        ):
            def chart_menu(event=None):
                # row_id = event.GetIndex()  # Get the current row

                x, y = event.GetPosition()
                row_id, flags = ctrl.HitTest((x, y))
                if row_id < 0:
                    l_allow_del = False
                    l_allow_dup = False
                else:
                    l_allow_del = allow_del
                    l_allow_dup = allow_dup
                menu = wx.Menu()
                if l_allow_del:

                    def on_delete(event):
                        values = getattr(local_obj, param)
                        # try:
                        values.pop(row_id)
                        self.context.signal(param, values, 0, param)
                        fill_ctrl(ctrl, local_obj, param, columns)
                        # except IndexError:
                        #    pass

                    menuitem = menu.Append(
                        wx.ID_ANY, _("Delete this entry"), ""
                    )
                    self.Bind(
                        wx.EVT_MENU,
                        on_delete,
                        id=menuitem.GetId(),
                    )
                if l_allow_dup:

                    def on_duplicate(event):
                        values = getattr(local_obj, param)
                        if isinstance(values[row_id], dict):
                            newentry = dict()
                            for key, content in values[row_id].items():
                                newentry[key] = content
                        else:
                            newentry = copy(values[row_id])
                        values.append(newentry)
                        self.context.signal(param, values, 0, param)
                        # except IndexError:
                        #    pass
                        fill_ctrl(ctrl, local_obj, param, columns)

                    menuitem = menu.Append(
                        wx.ID_ANY, _("Duplicate this entry"), ""
                    )
                    self.Bind(
                        wx.EVT_MENU,
                        on_duplicate,
                        id=menuitem.GetId(),
                    )

                def on_default(event):
                    values = getattr(local_obj, param)
                    values.clear()
                    for e in default:
                        values.append(e)

                    self.context.signal(param, values, 0, param)
                    fill_ctrl(ctrl, local_obj, param, columns)
                    # except IndexError:
                    #    pass

                menuitem = menu.Append(wx.ID_ANY, _("Restore defaults"), "")
                self.Bind(
                    wx.EVT_MENU,
                    on_default,
                    id=menuitem.GetId(),
                )

                if menu.MenuItemCount != 0:
                    self.PopupMenu(menu)
                    menu.Destroy()

            return chart_menu

        def on_generic_text(param, ctrl, obj, dtype, addsig):
            def text():
                v = ctrl.GetValue()
                try:
                    dtype_v = dtype(v)
                    current_value = getattr(obj, param)
                    if current_value != dtype_v:
                        setattr(obj, param, dtype_v)
                        self.context.signal(param, dtype_v, obj)
                        for _sig in addsig:
                            self.context.signal(_sig)
                except ValueError:
                    # cannot cast to data_type, pass
                    pass

            return text

        def on_length_text(param, ctrl, obj, dtype, addsig):
            def text():
                try:
                    v = Length(ctrl.GetValue())
                    data_v = v.preferred_length
                    current_value = getattr(obj, param)
                    if str(current_value) != str(data_v):
                        setattr(obj, param, data_v)
                        self.context.signal(param, data_v, obj)
                        for _sig in addsig:
                            self.context.signal(_sig)
                except ValueError:
                    # cannot cast to data_type, pass
                    pass

            return text


        for choice in choices:
            if isinstance(choice, dict):
                if "help" not in choice:
                    choice["help"] = standardhelp
                new_choices.append(choice)
            elif isinstance(choice, str):
                lookup_choice = self.context.lookup("choices", choice)
                if lookup_choice is None:
                    continue
                for c in lookup_choice:
                    if "help" not in c:
                        c["help"] = choice
                new_choices.extend(lookup_choice)
            else:
                for c in choice:
                    if "help" not in c:
                        c["help"] = standardhelp
                new_choices.extend(choice)
        choices = new_choices
        if injector is not None:
            # We have additional stuff to be added, so be it
            for c in injector:
                choices.append(c)
        if len(choices) == 0:
            # No choices to process.
            return
        for c in choices:
            needs_dynamic_call = c.get("dynamic")
            if needs_dynamic_call:
                # Calls dynamic function to update this dictionary before production
                needs_dynamic_call(c)
        # Let's see whether we have a section and a page property...
        for c in choices:
            try:
                dummy = c["subsection"]
            except KeyError:
                c["subsection"] = ""
            try:
                dummy = c["section"]
            except KeyError:
                c["section"] = ""
            try:
                dummy = c["page"]
            except KeyError:
                c["page"] = ""
            try:
                dummy = c["priority"]
            except KeyError:
                c["priority"] = "ZZZZZZZZ"
        # print ("Choices: " , choices)
        prechoices = sorted(
            sorted(
                sorted(
                    sorted(choices, key=lambda d: d["priority"]),
                    key=lambda d: d["subsection"],
                ),
                key=lambda d: d["section"],
            ),
            key=lambda d: d["page"],
        )
        self.choices = list()
        dealt_with = False
        if constraint is not None:
            if isinstance(constraint, (tuple, list, str)):
                if isinstance(constraint, str):
                    # make it a tuple
                    constraint = (constraint,)
                if len(constraint) > 0:
                    if isinstance(constraint[0], str):
                        dealt_with = True
                        # Section list
                        positive = list()
                        negative = list()
                        for item in constraint:
                            if item.startswith("-"):
                                item = item[1:]
                                negative.append(item.lower())
                            else:
                                positive.append(item.lower())
                        for i, c in enumerate(prechoices):
                            try:
                                this_page = c["page"].lower()
                            except KeyError:
                                this_page = ""
                            if len(negative) > 0 and len(positive) > 0:
                                # Negative takes precedence:
                                if not this_page in negative and this_page in positive:
                                    self.choices.append(c)
                            elif len(negative) > 0:
                                # only negative....
                                if not this_page in negative:
                                    self.choices.append(c)
                            elif len(positive) > 0:
                                # only positive....
                                if this_page in positive:
                                    self.choices.append(c)
                    else:
                        dealt_with = True
                        # Section list
                        start_from = 0
                        end_at = len(prechoices)
                        if constraint[0] >= 0:
                            start_from = constraint[0]
                        if len(constraint) > 1 and constraint[1] >= 0:
                            end_at = constraint[1]
                        if start_from < 0:
                            start_from = 0
                        if end_at > len(prechoices):
                            end_at = len(prechoices)
                        if end_at < start_from:
                            end_at = len(prechoices)
                        for i, c in enumerate(prechoices):
                            if start_from <= i < end_at:
                                self.choices.append(c)
        else:
            # Empty constraint
            pass
        if not dealt_with:
            # no valid constraints
            self.choices = prechoices
        if len(self.choices) == 0:
            return
        sizer_very_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_very_main.Add(sizer_main, 1, wx.EXPAND, 0)
        last_page = ""
        last_section = ""
        last_subsection = ""
        last_box = None
        current_main_sizer = sizer_main
        current_sec_sizer = sizer_main
        current_sizer = sizer_main
        # By default, 0 as we are stacking up stuff
        expansion_flag = 0
        current_col_entry = -1
        for i, c in enumerate(self.choices):
            wants_listener = True
            current_col_entry += 1
            if self.entries_per_column is not None:
                if current_col_entry >= self.entries_per_column:
                    current_col_entry = -1
                    prev_main = sizer_main
                    sizer_main = wx.BoxSizer(wx.VERTICAL)
                    if prev_main == current_main_sizer:
                        current_main_sizer = sizer_main
                    if prev_main == current_sec_sizer:
                        current_sec_sizer = sizer_main
                    if prev_main == current_sizer:
                        current_sizer = sizer_main

                    sizer_very_main.Add(sizer_main, 1, wx.EXPAND, 0)
                    # I think we should reset all sections to make them
                    # reappear in the next columns
                    last_page = ""
                    last_section = ""
                    last_subsection = ""

            if isinstance(c, tuple):
                # If c is tuple
                dict_c = dict()
                try:
                    dict_c["object"] = c[0]
                    dict_c["attr"] = c[1]
                    dict_c["default"] = c[2]
                    dict_c["label"] = c[3]
                    dict_c["tip"] = c[4]
                    dict_c["type"] = c[5]
                except IndexError:
                    pass
                c = dict_c
            try:
                attr = c["attr"]
                obj = c["object"]
            except KeyError:
                continue
            this_subsection = c.get("subsection", "")
            this_section = c.get("section", "")
            this_page = c.get("page", "")
            ctrl_width = c.get("width", 0)
            # Do we have a parameter to add a trailing label after the control
            trailer = c.get("trailer")
            # Is there another signal to send?
            additional_signal = []
            sig = c.get("signals")
            if isinstance(sig, str):
                additional_signal.append(sig)
            elif isinstance(sig, (tuple, list)):
                for _sig in sig:
                    additional_signal.append(_sig)

            # Do we have a parameter to hide the control unless in expert mode
            hidden = c.get("hidden", False)
            hidden = (
                bool(hidden) if hidden != "False" else False
            )  # bool("False") = True
            # Do we have a parameter to affect the space consumption?
            weight = int(c.get("weight", 1))
            if weight < 0:
                weight = 0
            developer_mode = self.context.root.setting(bool, "developer_mode", False)
            if not developer_mode and hidden:
                continue
            # get default value
            if hasattr(obj, attr):
                data = getattr(obj, attr)
            else:
                # if obj lacks attr, default must have been assigned.
                try:
                    data = c["default"]
                except KeyError:
                    # This choice is in error.
                    continue
            data_style = c.get("style", None)
            data_type = type(data)
            data_type = c.get("type", data_type)
            choice_list = None
            label = c.get("label", attr)  # Undefined label is the attr

            if last_page != this_page:
                expansion_flag = 0
                last_section = ""
                last_subsection = ""
                # We could do a notebook, but let's choose a simple StaticBoxSizer instead...
                last_box = StaticBoxSizer(
                    self, wx.ID_ANY, _(self.unsorted_label(this_page)), wx.VERTICAL
                )
                sizer_main.Add(last_box, 0, wx.EXPAND, 0)
                current_main_sizer = last_box
                current_sec_sizer = last_box
                current_sizer = last_box

            if last_section != this_section:
                expansion_flag = 0
                last_subsection = ""
                if this_section != "":
                    last_box = StaticBoxSizer(
                        self,
                        id=wx.ID_ANY,
                        label=_(self.unsorted_label(this_section)),
                        orientation=wx.VERTICAL,
                    )
                    current_main_sizer.Add(last_box, 0, wx.EXPAND, 0)
                else:
                    last_box = current_main_sizer
                current_sizer = last_box
                current_sec_sizer = last_box

            if last_subsection != this_subsection:
                expansion_flag = 0
                if this_subsection != "":
                    expansion_flag = 1
                    lbl = _(self.unsorted_label(this_subsection))
                    if lbl != "":
                        last_box = StaticBoxSizer(
                            self,
                            id=wx.ID_ANY,
                            label=lbl,
                            orientation=wx.HORIZONTAL,
                        )
                    else:
                        last_box = wx.BoxSizer(wx.HORIZONTAL)
                    current_sec_sizer.Add(last_box, 0, wx.EXPAND, 0)
                    img = c.get("icon", None)
                    if img is not None:
                        icon = wxStaticBitmap(self, wx.ID_ANY, bitmap=img)
                        last_box.Add(icon, 0, wx.ALIGN_CENTER_VERTICAL, 0)
                        last_box.AddSpacer(5)
                else:
                    last_box = current_sec_sizer
                current_sizer = last_box

            control = None
            control_sizer = None
            if data_type == str and data_style == "info":
                # This is just an info box.
                wants_listener = False
                msgs = label.split("\n")
                controls = []
                for lbl in msgs:
                    control = wxStaticText(self, label=lbl)
                    current_sizer.Add(control, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type == bool and data_style == "button":
                # This is just a signal to the outside world.
                wants_listener = False
                control = wxButton(self, label=label)


                control.Bind(
                    wx.EVT_BUTTON,
                    on_button(attr, obj, additional_signal),
                )
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                current_sizer.Add(control, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type == bool:
                # Bool type objects get a checkbox.
                control = wxCheckBox(self, label=label)
                control.SetValue(data)
                control.SetMinSize(dip_size(self, -1, 23))


                control.Bind(
                    wx.EVT_CHECKBOX,
                    on_checkbox_check(attr, control, obj, additional_signal),
                )

                current_sizer.Add(control, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type == str and data_style == "multiline":
                control_sizer = StaticBoxSizer(self, wx.ID_ANY, label, wx.HORIZONTAL)
                control = TextCtrl(
                    self,
                    wx.ID_ANY,
                    style=wx.TE_MULTILINE,
                )
                ctrl_width = c.get("width", 0)
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control.SetValue(str(data))
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control_sizer.Add(control, 1, wx.EXPAND, 0)
                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)


                control.SetActionRoutine(
                    on_generic_multi(attr, control, obj, data_type, additional_signal)
                )

            elif data_type == str and data_style == "file":
                control_sizer = StaticBoxSizer(self, wx.ID_ANY, label, wx.HORIZONTAL)
                control = TextCtrl(
                    self,
                    wx.ID_ANY,
                    style=wx.TE_PROCESS_ENTER,
                )
                control_btn = wxButton(self, wx.ID_ANY, "...")

                def set_file(filename: str):
                    # if not filename:
                    #     filename = _("No File")
                    control.SetValue(filename)


                control.SetActionRoutine(
                    on_file_text(attr, control, obj, data_type, additional_signal)
                )

                ctrl_width = c.get("width", 0)
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control.SetValue(str(data))
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control_sizer.Add(control, 1, wx.EXPAND, 0)
                control_sizer.Add(control_btn, 0, wx.EXPAND, 0)
                control_btn.Bind(
                    wx.EVT_BUTTON,
                    on_button_filename(
                        attr, control, obj, c.get("wildcard", "*"), additional_signal
                    ),
                )
                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type in (int, float) and data_style == "slider":
                if label != "":
                    control_sizer = StaticBoxSizer(
                        self, wx.ID_ANY, label, wx.HORIZONTAL
                    )
                else:
                    control_sizer = wx.BoxSizer(wx.HORIZONTAL)
                minvalue = c.get("min", 0)
                maxvalue = c.get("max", 0)
                if data_type == float:
                    value = float(data)
                elif data_type == int:
                    value = int(data)
                else:
                    value = int(data)
                control = wx.Slider(
                    self,
                    wx.ID_ANY,
                    value=value,
                    minValue=minvalue,
                    maxValue=maxvalue,
                    style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
                )


                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control_sizer.Add(control, 1, wx.EXPAND, 0)
                control.Bind(
                    wx.EVT_SLIDER,
                    on_slider(attr, control, obj, data_type, additional_signal),
                )
                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type in (str, int, float) and data_style == "combo":
                if label != "":
                    control_sizer = StaticBoxSizer(
                        self, wx.ID_ANY, label, wx.HORIZONTAL
                    )
                else:
                    control_sizer = wx.BoxSizer(wx.HORIZONTAL)
                choice_list = list(map(str, c.get("choices", [c.get("default")])))
                control = wxComboBox(
                    self,
                    wx.ID_ANY,
                    choices=choice_list,
                    style=wx.CB_DROPDOWN | wx.CB_READONLY,
                )
                if data is not None:
                    if data_type == str:
                        control.SetValue(str(data))
                    else:
                        least = None
                        for entry in choice_list:
                            if least is None:
                                least = entry
                            else:
                                if abs(data_type(entry) - data) < abs(
                                    data_type(least) - data
                                ):
                                    least = entry
                        if least is not None:
                            control.SetValue(least)


                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL, 0)
                control.Bind(
                    wx.EVT_COMBOBOX,
                    on_combo_text(attr, control, obj, data_type, additional_signal),
                )
                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type in (str, int) and data_style == "radio":
                control_sizer = wx.BoxSizer(wx.HORIZONTAL)
                choice_list = list(map(str, c.get("choices", [c.get("default")])))
                control = wxRadioBox(
                    self,
                    wx.ID_ANY,
                    label,
                    choices=choice_list,
                    majorDimension=3,
                    style=wx.RA_SPECIFY_COLS,  # wx.RA_SPECIFY_ROWS,
                )
                if data is not None:
                    if data_type == str:
                        control.SetSelection(0)
                        for idx, _c in enumerate(choice_list):
                            if _c == data:
                                control.SetSelection(idx)
                    else:
                        control.SetSelection(int(data))


                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL, 0)
                control.Bind(
                    wx.EVT_RADIOBOX,
                    on_radio_select(attr, control, obj, data_type, additional_signal),
                )
                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type in (int, str) and data_style == "option":
                control_sizer = wx.BoxSizer(wx.HORIZONTAL)
                display_list = list(map(str, c.get("display")))
                choice_list = list(map(str, c.get("choices", [c.get("default")])))
                try:
                    index = choice_list.index(str(data))
                except ValueError:
                    # Value was not in list.
                    index = 0
                    if data is None:
                        data = c.get("default")
                    display_list.insert(0, str(data))
                    choice_list.insert(0, str(data))
                cb_style = wx.CB_DROPDOWN | wx.CB_READONLY 
                control = wxComboBox(
                    self,
                    wx.ID_ANY,
                    choices=display_list,
                    style=cb_style,
                )
                control.SetSelection(index)

                # Constrain the width
                testsize = control.GetBestSize()
                control.SetMaxSize(dip_size(self, testsize[0] + 30, -1))
                # print ("Display: %s" % display_list)
                # print ("Choices: %s" % choice_list)
                # print ("To set: %s" % str(data))


                if label != "":
                    # Try to center it vertically to the controls extent
                    wd, ht = control.GetSize()
                    label_text = wxStaticText(self, id=wx.ID_ANY, label=label + " ")
                    # label_text.SetMinSize(dip_size(self, -1, ht))
                    control_sizer.Add(label_text, 0, wx.ALIGN_CENTER_VERTICAL, 0)
                control_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL, 0)
                control.Bind(
                    wx.EVT_COMBOBOX,
                    on_combosmall_option(
                        attr, control, obj, data_type, additional_signal, choice_list
                    ),
                )
                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type in (str, int, float) and data_style == "combosmall":
                control_sizer = wx.BoxSizer(wx.HORIZONTAL)
                exclusive = c.get("exclusive", True)
                cb_style = wx.CB_DROPDOWN | wx.CB_READONLY if exclusive else wx.CB_DROPDOWN 

                choice_list = list(map(str, c.get("choices", [c.get("default")])))
                control = wxComboBox(
                    self,
                    wx.ID_ANY,
                    choices=choice_list,
                    style = cb_style,
                )
                # Constrain the width
                testsize = control.GetBestSize()
                control.SetMaxSize(dip_size(self, testsize[0] + 30, -1))
                # print ("Choices: %s" % choice_list)
                # print ("To set: %s" % str(data))
                if data is not None:
                    if data_type == str:
                        control.SetValue(str(data))
                    else:
                        least = None
                        for entry in choice_list:
                            if least is None:
                                least = entry
                            else:
                                if abs(data_type(entry) - data) < abs(
                                    data_type(least) - data
                                ):
                                    least = entry
                        if least is not None:
                            control.SetValue(least)


                if label != "":
                    # Try to center it vertically to the controls extent
                    wd, ht = control.GetSize()
                    label_text = wxStaticText(self, id=wx.ID_ANY, label=label + " ")
                    # label_text.SetMinSize(dip_size(self, -1, ht))
                    control_sizer.Add(label_text, 0, wx.ALIGN_CENTER_VERTICAL, 0)
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL, 0)
                control.Bind(
                    wx.EVT_COMBOBOX,
                    on_combosmall_text(
                        attr, control, obj, data_type, additional_signal
                    ),
                )
                if not exclusive:
                    control.Bind(
                        wx.EVT_TEXT,
                        on_combosmall_text(
                            attr, control, obj, data_type, additional_signal
                        ),
                    )

                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type == int and data_style == "binary":
                mask = c.get("mask")

                # get default value
                mask_bits = 0
                if mask is not None and hasattr(obj, mask):
                    mask_bits = getattr(obj, mask)

                if label != "":
                    control_sizer = StaticBoxSizer(
                        self, wx.ID_ANY, label, wx.HORIZONTAL
                    )
                else:
                    control_sizer = wx.BoxSizer(wx.HORIZONTAL)


                bit_sizer = wx.BoxSizer(wx.VERTICAL)
                label_text = wxStaticText(
                    self, wx.ID_ANY, "", style=wx.ALIGN_CENTRE_HORIZONTAL
                )
                bit_sizer.Add(label_text, 0, wx.EXPAND, 0)
                if mask is not None:
                    label_text = wxStaticText(
                        self,
                        wx.ID_ANY,
                        _("mask") + " ",
                        style=wx.ALIGN_CENTRE_HORIZONTAL,
                    )
                    bit_sizer.Add(label_text, 0, wx.EXPAND, 0)
                label_text = wxStaticText(
                    self, wx.ID_ANY, _("value") + " ", style=wx.ALIGN_CENTRE_HORIZONTAL
                )
                bit_sizer.Add(label_text, 0, wx.EXPAND, 0)
                control_sizer.Add(bit_sizer, 0, wx.EXPAND, 0)

                bits = c.get("bits", 8)
                for b in range(bits):
                    # Label
                    bit_sizer = wx.BoxSizer(wx.VERTICAL)
                    label_text = wxStaticText(
                        self, wx.ID_ANY, str(b), style=wx.ALIGN_CENTRE_HORIZONTAL
                    )
                    bit_sizer.Add(label_text, 0, wx.EXPAND, 0)

                    # value bit
                    control = wxCheckBox(self)
                    control.SetValue(bool((data >> b) & 1))
                    if mask:
                        control.Enable(bool((mask_bits >> b) & 1))
                    control.Bind(wx.EVT_CHECKBOX, on_checkbox_bitcheck(attr, control, obj, b, additional_signal), )

                    # mask bit
                    if mask:
                        mask_ctrl = wxCheckBox(self)
                        mask_ctrl.SetValue(bool((mask_bits >> b) & 1))
                        mask_ctrl.Bind(
                            wx.EVT_CHECKBOX,
                            on_checkbox_bitcheck(
                                mask,
                                mask_ctrl,
                                obj,
                                b,
                                additional_signal,
                                enable_ctrl=control,
                            ),
                        )
                        bit_sizer.Add(mask_ctrl, 0, wx.EXPAND, 0)

                    bit_sizer.Add(control, 0, wx.EXPAND, 0)
                    control_sizer.Add(bit_sizer, 0, wx.EXPAND, 0)

                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type == str and data_style == "color":
                # str data_type with style "color" objects do get a button with the background.
                control_sizer = wx.BoxSizer(wx.HORIZONTAL)
                control = wxButton(self, -1)

                def set_color(ctrl, color: Color):
                    ctrl.SetLabel(str(color.hex))
                    ctrl.SetBackgroundColour(wx.Colour(swizzlecolor(color)))
                    if Color.distance(color, Color("black")) > Color.distance(
                        color, Color("white")
                    ):
                        ctrl.SetForegroundColour(wx.BLACK)
                    else:
                        ctrl.SetForegroundColour(wx.WHITE)
                    ctrl.color = color

                datastr = data
                data = Color(datastr)
                set_color(control, data)
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control_sizer.Add(control, 0, wx.EXPAND, 0)
                color_info = wxStaticText(self, wx.ID_ANY, label)
                control_sizer.Add(color_info, 1, wx.ALIGN_CENTER_VERTICAL)

                control.Bind(
                    wx.EVT_BUTTON,
                    on_button_color(attr, control, obj, additional_signal),
                )
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type == list and data_style == "chart":
                chart = EditableListCtrl(
                    self,
                    wx.ID_ANY,
                    style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
                    context=self.context, list_name=f"list_chart_{attr}",
                )
                l_columns = c.get("columns", [])

                def fill_ctrl(ctrl, local_obj, param, columns):
                    data = getattr(local_obj, param)
                    ctrl.ClearAll()
                    for column in columns:
                        wd = column.get("width", 150)
                        if wd < 0:
                            wd = ctrl.Size[0] - 10
                        ctrl.AppendColumn(
                            column.get("label", ""),
                            format=wx.LIST_FORMAT_LEFT,
                            width=wd,
                        )
                    ctrl.resize_columns()
                    for dataline in data:
                        if isinstance(dataline, dict):
                            for kk in dataline.keys():
                                key = kk
                                break
                            row_id = ctrl.InsertItem(
                                ctrl.GetItemCount(),
                                dataline.get(key, 0),
                            )
                            for column_id, column in enumerate(columns):
                                c_attr = column.get("attr")
                                ctrl.SetItem(
                                    row_id, column_id, str(dataline.get(c_attr, ""))
                                )
                        elif isinstance(dataline, str):
                            row_id = ctrl.InsertItem(
                                ctrl.GetItemCount(),
                                dataline,
                            )
                        elif isinstance(dataline, (list, tuple)):
                            row_id = ctrl.InsertItem(
                                ctrl.GetItemCount(),
                                dataline[0],
                            )
                            for column_id, column in enumerate(columns):
                                # c_attr = column.get("attr")
                                ctrl.SetItem(row_id, column_id, dataline[column_id])

                fill_ctrl(chart, obj, attr, l_columns)


                chart.Bind(
                    wx.EVT_LIST_BEGIN_LABEL_EDIT,
                    on_chart_start(l_columns, attr, chart, obj),
                )


                chart.Bind(
                    wx.EVT_LIST_END_LABEL_EDIT,
                    on_chart_stop(l_columns, attr, chart, obj),
                )

                allow_deletion = c.get("allow_deletion", False)
                allow_duplication = c.get("allow_duplication", False)

                default = c.get("default", [])
                # chart.Bind(
                #     wx.EVT_LIST_ITEM_RIGHT_CLICK,
                #     on_chart_contextmenu(
                #         l_columns,
                #         attr,
                #         chart,
                #         obj,
                #         allow_deletion,
                #         allow_duplication,
                #         default,
                #     ),
                # )
                # chart.Bind(
                #     wx.EVT_LIST_COL_RIGHT_CLICK,
                #     on_chart_contextmenu(
                #         l_columns,
                #         attr,
                #         chart,
                #         obj,
                #         allow_deletion,
                #         allow_duplication,
                #         default,
                #     ),
                # )
                chart.Bind(
                    wx.EVT_RIGHT_DOWN,
                    on_chart_contextmenu(
                        l_columns,
                        attr,
                        chart,
                        obj,
                        allow_deletion,
                        allow_duplication,
                        default,
                    ),
                )
                current_sizer.Add(chart, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type in (str, int, float):
                # str, int, and float type objects get a TextCtrl setter.
                if label != "" and data_style != "flat":
                    control_sizer = StaticBoxSizer(
                        self, wx.ID_ANY, label, wx.HORIZONTAL
                    )
                else:
                    control_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    if label != "":
                        label_text = wxStaticText(self, id=wx.ID_ANY, label=label)
                        control_sizer.Add(label_text, 0, wx.ALIGN_CENTER_VERTICAL, 0)

                if data_type == int:
                    check_flag = "int"
                    limit = True
                    lower_range = c.get("lower", None)
                    upper_range = c.get("upper", None)
                elif data_type == float:
                    check_flag = "float"
                    limit = True
                    lower_range = c.get("lower", None)
                    upper_range = c.get("upper", None)
                else:
                    check_flag = ""
                    limit = False
                    lower_range = None
                    upper_range = None

                control = TextCtrl(
                    self,
                    wx.ID_ANY,
                    style=wx.TE_PROCESS_ENTER,
                    limited=limit,
                    check=check_flag,
                )
                if lower_range is not None:
                    control.lower_limit = lower_range
                    control.lower_limit_err = lower_range
                if upper_range is not None:
                    control.upper_limit = upper_range
                    control.upper_limit_err = upper_range
                ctrl_width = c.get("width", 0)
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control.SetValue(str(data))
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control_sizer.Add(control, 1, wx.EXPAND, 0)


                control.SetActionRoutine(
                    on_generic_text(attr, control, obj, data_type, additional_signal)
                )
                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type == Length:
                # Length type is a TextCtrl with special checks
                if label != "":
                    control_sizer = StaticBoxSizer(
                        self, wx.ID_ANY, label, wx.HORIZONTAL
                    )
                else:
                    control_sizer = wx.BoxSizer(wx.HORIZONTAL)
                nonzero = c.get("nonzero", False)
                if nonzero is None or not isinstance(nonzero, bool):
                    nonzero = False
                control = TextCtrl(
                    self,
                    wx.ID_ANY,
                    style=wx.TE_PROCESS_ENTER,
                    limited=True,
                    check="length",
                    nonzero=nonzero,
                )
                if isinstance(data, Length):
                    if not data._preferred_units:
                        data._preferred_units = "mm"
                    if not data._digits:
                        if data._preferred_units in ("mm", "cm", "in", "inch"):
                            data._digits = 4
                    display_value = data.preferred_length
                else:
                    display_value = str(data)
                control.SetValue(display_value)
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control_sizer.Add(control, 1, wx.EXPAND, 0)

                control.SetActionRoutine(
                    on_length_text(attr, control, obj, data_type, additional_signal)
                )
                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type == Angle:
                # Angle type is a TextCtrl with special checks
                if label != "":
                    control_sizer = StaticBoxSizer(
                        self, wx.ID_ANY, label, wx.HORIZONTAL
                    )
                else:
                    control_sizer = wx.BoxSizer(wx.HORIZONTAL)
                control = TextCtrl(
                    self,
                    wx.ID_ANY,
                    style=wx.TE_PROCESS_ENTER,
                    check="angle",
                    limited=True,
                )
                control.SetValue(str(data))
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control_sizer.Add(control, 1, wx.EXPAND, 0)

                control.SetActionRoutine(
                    on_angle_text(attr, control, obj, data_type, additional_signal)
                )
                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type == Color:
                # Color data_type objects are get a button with the background.
                if label != "":
                    control_sizer = StaticBoxSizer(
                        self, wx.ID_ANY, label, wx.HORIZONTAL
                    )
                else:
                    control_sizer = wx.BoxSizer(wx.HORIZONTAL)
                control = wxButton(self, -1)

                def set_color(ctrl, color: Color):
                    ctrl.SetLabel(str(color.hex))
                    ctrl.SetBackgroundColour(wx.Colour(swizzlecolor(color)))
                    if Color.distance(color, Color("black")) > Color.distance(
                        color, Color("white")
                    ):
                        ctrl.SetForegroundColour(wx.BLACK)
                    else:
                        ctrl.SetForegroundColour(wx.WHITE)
                    ctrl.color = color

                set_color(control, data)
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                control_sizer.Add(control, 0, wx.EXPAND, 0)

                control.Bind(
                    wx.EVT_BUTTON,
                    on_button_color(attr, control, obj, additional_signal),
                )
                if ctrl_width > 0:
                    control.SetMaxSize(dip_size(self, ctrl_width, -1))
                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)
            else:
                # Requires a registered data_type
                continue

            if trailer and control_sizer:
                trailer_text = wxStaticText(self, id=wx.ID_ANY, label=f" {trailer}")
                control_sizer.Add(trailer_text, 0, wx.ALIGN_CENTER_VERTICAL, 0)

            if control is None:
                continue  # We're binary or some other style without a specific control.

            # Get enabled value
            try:
                enabled = c["enabled"]
                control.Enable(enabled)
            except KeyError:
                # Listen to establish whether this control should be enabled based on another control's value.
                try:
                    conditional = c["conditional"]
                    if len(conditional) == 2:
                        c_obj, c_attr = conditional
                        enabled = bool(getattr(c_obj, c_attr))
                        c_equals = True
                        control.Enable(enabled)
                    elif len(conditional) == 3:
                        c_obj, c_attr, c_equals = conditional
                        enabled = bool(getattr(c_obj, c_attr) == c_equals)
                        control.Enable(enabled)
                    elif len(conditional) == 4:
                        c_obj, c_attr, c_from, c_to = conditional
                        enabled = bool(c_from <= getattr(c_obj, c_attr) <= c_to)
                        c_equals = (c_from, c_to)
                        control.Enable(enabled)

                    def on_enable_listener(param, ctrl, obj, eqs):
                        def listen(origin, value, target=None):
                            try:
                                if isinstance(eqs, (list, tuple)):
                                    enable = bool(
                                        eqs[0] <= getattr(obj, param) <= eqs[1]
                                    )
                                else:
                                    enable = bool(getattr(obj, param) == eqs)
                                ctrl.Enable(enable)
                            except (IndexError, RuntimeError):
                                pass

                        return listen

                    listener = on_enable_listener(c_attr, control, c_obj, c_equals)
                    self.listeners.append((c_attr, listener, c_obj))
                    context.listen(c_attr, listener)
                except KeyError:
                    pass

            # Now we listen to 'ourselves' as well to learn about changes somewhere else...
            def on_update_listener(param, ctrl, dtype, dstyle, choicelist, sourceobj):
                def listen_to_myself(origin, value, target=None):
                    if self.context.kernel.is_shutdown:
                        return

                    if target is None or target is not sourceobj:
                        # print (f"Signal for {param}={value}, but no target given or different to source")
                        return
                    update_needed = False
                    # print (f"attr={param}, origin={origin}, value={value}, datatype={dtype}, datastyle={dstyle}")
                    data = None
                    if value is not None:
                        try:
                            data = dtype(value)
                        except ValueError:
                            pass
                        if data is None:
                            try:
                                data = c["default"]
                            except KeyError:
                                pass
                    if data is None:
                        # print (f"Invalid data based on {value}, exiting")
                        return
                    # Let's just access the ctrl to see whether it has been already
                    # destroyed (as we are in the midst of a shutdown)
                    try:
                        dummy = hasattr(ctrl, "GetValue")
                    except RuntimeError:
                        return
                    if dtype == bool:
                        # Bool type objects get a checkbox.
                        if ctrl.GetValue() != data:
                            ctrl.SetValue(data)
                    elif dtype == str and dstyle == "file":
                        if ctrl.GetValue() != data:
                            ctrl.SetValue(data)
                    elif dtype in (int, float) and dstyle == "slider":
                        if ctrl.GetValue() != data:
                            ctrl.SetValue(data)
                    elif dtype in (str, int, float) and dstyle == "combo":
                        if dtype == str:
                            ctrl.SetValue(str(data))
                        else:
                            least = None
                            for entry in choicelist:
                                if least is None:
                                    least = entry
                                else:
                                    if abs(dtype(entry) - data) < abs(
                                        dtype(least) - data
                                    ):
                                        least = entry
                            if least is not None:
                                ctrl.SetValue(least)
                    elif dtype in (str, int, float) and dstyle == "combosmall":
                        if dtype == str:
                            ctrl.SetValue(str(data))
                        else:
                            least = None
                            for entry in choicelist:
                                if least is None:
                                    least = entry
                                else:
                                    if abs(dtype(entry) - data) < abs(
                                        dtype(least) - data
                                    ):
                                        least = entry
                            if least is not None:
                                ctrl.SetValue(least)
                    elif dtype == int and dstyle == "binary":
                        pass  # not supported...
                    elif (dtype == str and dstyle == "color") or dtype == Color:
                        # Color dtype objects are a button with the background set to the color
                        def set_color(color: Color):
                            ctrl.SetLabel(str(color.hex))
                            ctrl.SetBackgroundColour(wx.Colour(swizzlecolor(color)))
                            if Color.distance(color, Color("black")) > Color.distance(
                                color, Color("white")
                            ):
                                ctrl.SetForegroundColour(wx.BLACK)
                            else:
                                ctrl.SetForegroundColour(wx.WHITE)
                            ctrl.color = color

                        if isinstance(data, str):
                            # print ("Needed to change type")
                            data = Color(data)
                        # print (f"Will set color to {data}")
                        set_color(data)
                    elif dtype in (str, int, float):
                        if hasattr(ctrl, "GetValue"):
                            try:
                                if dtype(ctrl.GetValue()) != data:
                                    update_needed = True
                            except ValueError:
                                update_needed = True
                            if update_needed:
                                ctrl.SetValue(str(data))
                    elif dtype == Length:
                        if float(data) != float(Length(ctrl.GetValue())):
                            update_needed = True
                        if update_needed:
                            if not isinstance(data, str):
                                data = Length(data).length_mm
                            ctrl.SetValue(str(data))
                    elif dtype == Angle:
                        if ctrl.GetValue() != str(data):
                            ctrl.SetValue(str(data))

                return listen_to_myself

            if wants_listener:
                update_listener = on_update_listener(
                    attr, control, data_type, data_style, choice_list, obj
                )
                self.listeners.append((attr, update_listener, obj))
                context.listen(attr, update_listener)
            tip = c.get("tip")
            if tip and not context.root.disable_tool_tips:
                # Set the tool tip if 'tip' is available
                control.SetToolTip(tip)
            _help = c.get("help")
            if _help and hasattr(control, "SetHelpText"):
                control.SetHelpText(_help)
            last_page = this_page
            last_section = this_section
            last_subsection = this_subsection

        self.SetSizer(sizer_very_main)
        sizer_very_main.Fit(self)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        # Make sure stuff gets scrolled if necessary by default
        if scrolling:
            self.SetupScrolling()

    def on_close(self, event):
        # We should not need this, but better safe than sorry
        event.Skip()
        self.pane_hide()

    @staticmethod
    def unsorted_label(original):
        # Special sort key just to sort stuff - we fix the preceeding "_sortcriteria_Correct label"
        result = original
        if result.startswith("_"):
            idx = result.find("_", 1)
            if idx >= 0:
                result = result[idx + 1 :]
        return result

    def reload(self):
        for attr, listener, obj in self.listeners:
            try:
                value = getattr(obj, attr)
            except AttributeError as e:
                # print(f"error: {e}")
                continue
            listener("internal", value, obj)

    def module_close(self, *args, **kwargs):
        self.pane_hide()

    def pane_hide(self):
        # print (f"hide called: {len(self.listeners)}")
        if len(self.listeners):
            for attr, listener, obj in self.listeners:
                self.context.unlisten(attr, listener)
                del listener
            self.listeners.clear()

    def pane_show(self):
        # print ("show called")
        # if len(self.listeners) == 0:
        #     print ("..but no one cares")
        pass
