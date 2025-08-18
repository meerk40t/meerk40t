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
        "ignored": As the name implies...
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

            # Validate and prepare choice using helper method
            c, attr, obj, is_valid = self._validate_and_prepare_choice(c)
            if not is_valid:
                continue

            this_subsection = c.get("subsection", "")
            this_section = c.get("section", "")
            this_page = c.get("page", "")
            ctrl_width = c.get("width", 0)
            # Do we have a parameter to add a trailing label after the control
            trailer = c.get("trailer")

            # Get additional signals using helper method
            additional_signal = self._get_additional_signals(c)

            # Do we have a parameter to affect the space consumption?
            weight = int(c.get("weight", 1))
            if weight < 0:
                weight = 0

            # Get data and data type using helper method
            data, data_type = self._get_choice_data_and_type(c, obj, attr)
            if data is None:
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

            # Try to create control using the dispatch table system
            dispatch_result = self._create_control_using_dispatch(
                label, data, data_type, data_style, c, attr, obj, additional_signal
            )

            if dispatch_result[0] is not None:
                # Successfully created using dispatch table
                control, control_sizer, wants_listener = dispatch_result
                if control_sizer is not None:
                    current_sizer.Add(
                        control_sizer, expansion_flag * weight, wx.EXPAND, 0
                    )
                elif control is not None:
                    current_sizer.Add(control, expansion_flag * weight, wx.EXPAND, 0)
            elif data_type == list and data_style == "chart":
                # Chart controls - complex case not yet unified
                chart = EditableListCtrl(
                    self,
                    wx.ID_ANY,
                    style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
                    context=self.context,
                    list_name=f"list_chart_{attr}",
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
                    self._make_chart_start_handler(l_columns, attr, chart, obj),
                )

                chart.Bind(
                    wx.EVT_LIST_END_LABEL_EDIT,
                    self._make_chart_stop_handler(l_columns, attr, chart, obj),
                )

                allow_deletion = c.get("allow_deletion", False)
                allow_duplication = c.get("allow_duplication", False)

                default = c.get("default", [])

                chart.Bind(
                    wx.EVT_RIGHT_DOWN,
                    self._make_chart_contextmenu_handler(
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
                control = chart
                wants_listener = True
            elif data_type == Color:
                # Color data_type objects are get a button with the background.
                control_sizer = self._create_labeled_sizer(label)
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
                self._apply_control_width(control, c.get("width", 0))
                control_sizer.Add(control, 0, wx.EXPAND, 0)

                control.Bind(
                    wx.EVT_BUTTON,
                    self._make_button_color_handler(
                        attr, control, obj, additional_signal
                    ),
                )
                current_sizer.Add(control_sizer, expansion_flag * weight, wx.EXPAND, 0)
                wants_listener = True
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
                # Use helper method for setting up update listener
                self._setup_update_listener(
                    c, control, attr, obj, data_type, data_style, choice_list
                )

            # Use helper method for setting up control properties
            self._setup_control_properties(c, control, attr, obj)
            last_page = this_page
            last_section = this_section
            last_subsection = this_subsection

        self.SetSizer(sizer_very_main)
        sizer_very_main.Fit(self)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        # Make sure stuff gets scrolled if necessary by default
        if scrolling:
            self.SetupScrolling()

    # Event Handler Methods
    def _dispatch_signals(self, param, value, obj, additional_signals):
        """Helper method to dispatch property change signals."""
        self.context.signal(param, value, obj)
        for _sig in additional_signals:
            self.context.signal(_sig)

    def _update_property_and_signal(self, obj, param, new_value, additional_signals):
        """Helper method to update property value and dispatch signals."""
        current_value = getattr(obj, param)
        if current_value != new_value:
            setattr(obj, param, new_value)
            self._dispatch_signals(param, new_value, obj, additional_signals)
            return True
        return False

    # UI Helper Methods
    def _create_text_control(self, label, data, data_type, config, handler_factory):
        """Unified TextCtrl creation for all text-based inputs."""
        # Handle special flat style
        if config.get("style") == "flat":
            control_sizer = wx.BoxSizer(wx.HORIZONTAL)
            if label != "":
                label_text = wxStaticText(self, id=wx.ID_ANY, label=label)
                control_sizer.Add(label_text, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        else:
            control_sizer = self._create_labeled_sizer(label)

        # Determine text control configuration
        text_config = self._get_text_control_config(data_type, config)

        # Create the control
        control = TextCtrl(
            self,
            wx.ID_ANY,
            style=text_config.get("style", wx.TE_PROCESS_ENTER),
            limited=text_config.get("limited", False),
            check=text_config.get("check", ""),
            nonzero=text_config.get("nonzero", False),
        )

        # Set display value
        display_value = self._format_text_display_value(data, data_type, config)
        control.SetValue(display_value)

        # Apply width and validation
        self._apply_control_width(control, config.get("width", 0))
        self._setup_text_validation(control, data_type, config)

        # Add to sizer
        control_sizer.Add(control, 1, wx.EXPAND, 0)

        # Add button for file inputs
        if text_config.get("has_button"):
            button = wxButton(self, wx.ID_ANY, text_config.get("button_text", "..."))
            control_sizer.Add(button, 0, wx.EXPAND, 0)
            # Store button reference for handler setup
            control._file_button = button
            control._wildcard = text_config.get("wildcard", "*")

        # Set up event handler
        if handler_factory:
            control.SetActionRoutine(handler_factory())

        return control, control_sizer

    def _create_combo_control(
        self, label, data, data_type, config, handler_factory=None
    ):
        """Unified wxComboBox creation for all combo-based inputs."""
        data_style = config.get("style")

        # Determine sizer type based on style
        if data_style == "combosmall":
            control_sizer = wx.BoxSizer(wx.HORIZONTAL)
        else:
            control_sizer = self._create_labeled_sizer(label)

        # Get combo configuration
        combo_config = self._get_combo_control_config(data_type, config)

        # Create choices list
        choice_list = list(map(str, config.get("choices", [config.get("default")])))

        # Create the control
        control = wxComboBox(
            self,
            wx.ID_ANY,
            choices=choice_list,
            style=combo_config["style"],
        )

        # Set display value
        self._set_combo_value(control, data, data_type, choice_list)

        # Apply width constraints
        if data_style == "combosmall":
            testsize = control.GetBestSize()
            control.SetMaxSize(dip_size(self, testsize[0] + 30, -1))
        else:
            self._apply_control_width(control, config.get("width", 0))

        # Add to sizer
        if data_style == "combosmall":
            if label != "":
                label_text = wxStaticText(self, id=wx.ID_ANY, label=label)
                control_sizer.Add(label_text, 0, wx.ALIGN_CENTER_VERTICAL, 0)
            control_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        else:
            control_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        # Set up event handler
        if handler_factory:
            control.Bind(wx.EVT_COMBOBOX, handler_factory())
            # For combosmall non-exclusive, also bind text events
            if data_style == "combosmall" and not config.get("exclusive", True):
                control.Bind(wx.EVT_TEXT, handler_factory())

        return control, control_sizer

    def _get_text_control_config(self, data_type, config):
        """Generate TextCtrl configuration based on data type."""
        text_config = {"style": wx.TE_PROCESS_ENTER}

        # Type-specific configurations
        if data_type in (int, float):
            text_config["limited"] = True
            text_config["check"] = "int" if data_type == int else "float"
        elif data_type == Length:
            text_config.update(
                {
                    "limited": True,
                    "check": "length",
                    "nonzero": config.get("nonzero", False),
                }
            )
        elif data_type == Angle:
            text_config.update({"check": "angle", "limited": True})
        elif config.get("style") == "multiline":
            text_config["style"] = wx.TE_MULTILINE
        elif config.get("style") == "file":
            text_config.update(
                {
                    "has_button": True,
                    "button_text": "...",
                    "wildcard": config.get("wildcard", "*"),
                }
            )

        return text_config

    def _get_combo_control_config(self, data_type, config):
        """Generate wxComboBox configuration based on data type and style."""
        combo_config = {}
        data_style = config.get("style")

        if data_style == "combosmall":
            exclusive = config.get("exclusive", True)
            combo_config["style"] = (
                wx.CB_DROPDOWN | wx.CB_READONLY if exclusive else wx.CB_DROPDOWN
            )
        else:  # regular combo
            combo_config["style"] = wx.CB_DROPDOWN | wx.CB_READONLY

        return combo_config

    def _set_combo_value(self, control, data, data_type, choice_list):
        """Set the value of a combo control based on data type."""
        if data is not None:
            if data_type == str:
                control.SetValue(str(data))
            else:
                # Find closest numeric match
                least = None
                for entry in choice_list:
                    if least is None:
                        least = entry
                    else:
                        if abs(data_type(entry) - data) < abs(data_type(least) - data):
                            least = entry
                if least is not None:
                    control.SetValue(least)

    def _create_radio_control(
        self, label, data, data_type, config, handler_factory=None
    ):
        """Unified radio control creation for radio and option styles."""
        data_style = config.get("style")

        # Create horizontal sizer for both types
        control_sizer = wx.BoxSizer(wx.HORIZONTAL)

        if data_style == "radio":
            # Traditional radio box
            choice_list = list(map(str, config.get("choices", [config.get("default")])))
            control = wxRadioBox(
                self,
                wx.ID_ANY,
                label,
                choices=choice_list,
                majorDimension=3,
                style=wx.RA_SPECIFY_COLS,
            )

            # Set selection based on data type
            self._set_radio_selection(control, data, data_type, choice_list)

            # Apply width and add to sizer
            self._apply_control_width(control, config.get("width", 0))
            control_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL, 0)

            # Set up event handler
            if handler_factory:
                control.Bind(wx.EVT_RADIOBOX, handler_factory())

        elif data_style == "option":
            # Option-style combo with display/choice separation
            display_list = list(map(str, config.get("display")))
            choice_list = list(map(str, config.get("choices", [config.get("default")])))

            # Handle value not in list
            try:
                index = choice_list.index(str(data))
            except ValueError:
                index = 0
                if data is None:
                    data = config.get("default")
                display_list.insert(0, str(data))
                choice_list.insert(0, str(data))

            # Create combo control
            control = wxComboBox(
                self,
                wx.ID_ANY,
                choices=display_list,
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            )
            control.SetSelection(index)

            # Constrain width
            testsize = control.GetBestSize()
            control.SetMaxSize(dip_size(self, testsize[0] + 30, -1))

            # Add label if provided
            if label != "":
                label_text = wxStaticText(self, id=wx.ID_ANY, label=label + " ")
                control_sizer.Add(label_text, 0, wx.ALIGN_CENTER_VERTICAL, 0)

            control_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL, 0)

            # Store choice list for handler
            control._choice_list = choice_list

            # Set up event handler
            if handler_factory:
                control.Bind(wx.EVT_COMBOBOX, handler_factory())

        return control, control_sizer

    def _set_radio_selection(self, control, data, data_type, choice_list):
        """Set radio box selection based on data and type."""
        if data is not None:
            if data_type == str:
                control.SetSelection(0)  # Default
                for idx, choice in enumerate(choice_list):
                    if choice == data:
                        control.SetSelection(idx)
                        break
            else:
                control.SetSelection(int(data))

    def _create_button_control(
        self, label, data, data_type, config, handler_factory=None
    ):
        """Unified button control creation for button, color, and checkbox styles."""
        data_style = config.get("style")
        wants_listener = True  # Most button types want listeners

        if data_style == "button":
            # Simple action button
            wants_listener = False  # Button style doesn't want listener
            control = wxButton(self, label=label)
            control_sizer = None  # Button goes directly into main sizer

            # Set up event handler
            if handler_factory:
                control.Bind(wx.EVT_BUTTON, handler_factory())

        elif data_style == "color":
            # Color picker button
            control_sizer = wx.BoxSizer(wx.HORIZONTAL)
            control = wxButton(self, -1)

            # Set up color display
            datastr = data
            data_color = Color(datastr)
            self._set_color_button(control, data_color)

            # Add color info label
            control_sizer.Add(control, 0, wx.EXPAND, 0)
            color_info = wxStaticText(self, wx.ID_ANY, label)
            control_sizer.Add(color_info, 1, wx.ALIGN_CENTER_VERTICAL)

            # Set up event handler
            if handler_factory:
                control.Bind(wx.EVT_BUTTON, handler_factory())

        else:
            # Regular checkbox for bool
            control = wxCheckBox(self, label=label)
            control.SetValue(data)
            control.SetMinSize(dip_size(self, -1, 23))
            control_sizer = None  # Checkbox goes directly into main sizer

            # Set up event handler
            if handler_factory:
                control.Bind(wx.EVT_CHECKBOX, handler_factory())

        # Apply width configuration
        self._apply_control_width(control, config.get("width", 0))

        return control, control_sizer, wants_listener

    def _set_color_button(self, control, color):
        """Set color button appearance based on color value."""
        control.SetLabel(str(color.hex))
        control.SetBackgroundColour(wx.Colour(swizzlecolor(color)))
        if Color.distance(color, Color("black")) > Color.distance(
            color, Color("white")
        ):
            control.SetForegroundColour(wx.BLACK)
        else:
            control.SetForegroundColour(wx.WHITE)
        control.color = color

    def _create_slider_control(
        self, label, data, data_type, config, handler_factory=None
    ):
        """Unified slider control creation for numeric slider inputs."""
        # Create labeled sizer
        control_sizer = self._create_labeled_sizer(label)

        # Get slider configuration
        minvalue = config.get("min", 0)
        maxvalue = config.get("max", 0)

        # Convert data to appropriate numeric type
        if data_type == float:
            value = float(data)
        elif data_type == int:
            value = int(data)
        else:
            value = int(data)

        # Handle callable min/max values
        if callable(minvalue):
            minvalue = minvalue()
        if callable(maxvalue):
            maxvalue = maxvalue()

        # Create slider control
        control = wx.Slider(
            self,
            wx.ID_ANY,
            value=value,
            minValue=minvalue,
            maxValue=maxvalue,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )

        # Apply width and add to sizer
        self._apply_control_width(control, config.get("width", 0))
        control_sizer.Add(control, 1, wx.EXPAND, 0)

        if handler_factory:
            control.Bind(wx.EVT_SLIDER, handler_factory())

        return control, control_sizer

    def _create_binary_control(
        self, label, data, data_type, config, attr, obj, additional_signal
    ):
        """Unified binary control creation for binary checkbox patterns."""
        mask = config.get("mask")

        # Get mask bits if specified
        mask_bits = 0
        if mask is not None and hasattr(obj, mask):
            mask_bits = getattr(obj, mask)

        # Create main sizer structure
        control_sizer = self._create_labeled_sizer(label)

        # Create header labels
        bit_sizer = wx.BoxSizer(wx.VERTICAL)

        # Empty header
        label_text = wxStaticText(self, wx.ID_ANY, "", style=wx.ALIGN_CENTRE_HORIZONTAL)
        bit_sizer.Add(label_text, 0, wx.EXPAND, 0)

        # Mask header if mask exists
        if mask is not None:
            label_text = wxStaticText(
                self,
                wx.ID_ANY,
                _("mask") + " ",
                style=wx.ALIGN_CENTRE_HORIZONTAL,
            )
            bit_sizer.Add(label_text, 0, wx.EXPAND, 0)

        # Value header
        label_text = wxStaticText(
            self, wx.ID_ANY, _("value") + " ", style=wx.ALIGN_CENTRE_HORIZONTAL
        )
        bit_sizer.Add(label_text, 0, wx.EXPAND, 0)
        control_sizer.Add(bit_sizer, 0, wx.EXPAND, 0)

        # Create bit columns
        bits = config.get("bits", 8)
        controls = []

        for b in range(bits):
            # Create bit column
            bit_sizer = wx.BoxSizer(wx.VERTICAL)

            # Bit number label
            label_text = wxStaticText(
                self, wx.ID_ANY, str(b), style=wx.ALIGN_CENTRE_HORIZONTAL
            )
            bit_sizer.Add(label_text, 0, wx.EXPAND, 0)

            # Value checkbox
            control = wxCheckBox(self)
            control.SetValue(bool((data >> b) & 1))
            if mask:
                control.Enable(bool((mask_bits >> b) & 1))

            # Set up value handler
            control.Bind(
                wx.EVT_CHECKBOX,
                self._make_checkbox_bitcheck_handler(
                    attr, control, obj, b, additional_signal
                ),
            )

            # Store for return
            controls.append(control)

            # Mask checkbox if mask exists
            if mask:
                mask_ctrl = wxCheckBox(self)
                mask_ctrl.SetValue(bool((mask_bits >> b) & 1))
                mask_ctrl.Bind(
                    wx.EVT_CHECKBOX,
                    self._make_checkbox_bitcheck_handler(
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

        return controls, control_sizer

    def _get_control_factory(self, data_type, data_style):
        """
        Dispatch table for control creation. Returns a tuple of (factory_function, handler_factory, needs_special_handling).
        If needs_special_handling is True, the factory handles its own sizer addition.
        """
        # Import types for dispatch table
        from meerk40t.core.units import Angle, Length
        from meerk40t.svgelements import Color

        # Define dispatch table as (data_type, data_style): (factory, handler_factory, needs_special_handling)
        # fmt:off
        dispatch_table = {
            # Text-based controls
            (str, None): (
                self._create_text_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_generic_text_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            (int, None): (
                self._create_text_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_generic_text_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            (float, None): (
                self._create_text_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_generic_text_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            (str, "multiline"): (
                self._create_text_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_generic_multi_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            (str, "file"): (
                self._create_text_control,
                lambda attr, control, obj, data_type, additional_signal, c, label: self._make_file_text_handler_with_button(attr, control, obj, data_type, additional_signal, c, label),
                False,
            ),
            (Length, None): (
                self._create_text_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_length_text_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            (Angle, None): (
                self._create_text_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_angle_text_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            # Button-based controls
            (bool, "button"): (
                self._create_button_control,
                lambda attr, obj, additional_signal: self._make_button_handler(attr, obj, additional_signal),
                False,
            ),
            (bool, None): (
                self._create_button_control,
                lambda attr, control, obj, additional_signal: self._make_checkbox_handler(attr, control, obj, additional_signal),
                False,
            ),
            (str, "color"): (
                self._create_button_control,
                lambda attr, control, obj, additional_signal: self._make_button_color_handler(attr, control, obj, additional_signal),
                False,
            ),
            # Combo-based controls
            (str, "combo"): (
                self._create_combo_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_combo_text_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            (int, "combo"): (
                self._create_combo_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_combo_text_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            (float, "combo"): (
                self._create_combo_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_combo_text_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            (str, "combosmall"): (
                self._create_combo_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_combosmall_text_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            (int, "combosmall"): (
                self._create_combo_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_combosmall_text_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            (float, "combosmall"): (
                self._create_combo_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_combosmall_text_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            # Radio-based controls
            (str, "radio"): (
                self._create_radio_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_radio_select_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            (int, "radio"): (
                self._create_radio_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_radio_select_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            (int, "option"): (
                self._create_radio_control,
                lambda attr, control, obj, data_type, additional_signal, choice_list: self._make_combosmall_option_handler(attr, control, obj, data_type, additional_signal, choice_list),
                False,
            ),
            (str, "option"): (
                self._create_radio_control,
                lambda attr, control, obj, data_type, additional_signal, choice_list: self._make_combosmall_option_handler(attr, control, obj, data_type, additional_signal, choice_list),
                False,
            ),
            # Slider controls
            (int, "slider"): (
                self._create_slider_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_slider_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            (float, "slider"): (
                self._create_slider_control,
                lambda attr, control, obj, data_type, additional_signal: self._make_slider_handler(attr, control, obj, data_type, additional_signal),
                False,
            ),
            # Binary controls
            (int, "binary"): (self._create_binary_control, None, False),
            # Special cases requiring custom handling
            (str, "info"): ("info", None, True),
            (list, "chart"): ("chart", None, True),
            (Color, None): ("color_type", None, True),
        }
        # fmt:on

        # Try exact match first
        key = (data_type, data_style)
        if key in dispatch_table:
            return dispatch_table[key]

        # Try with None style for basic types
        key = (data_type, None)
        if key in dispatch_table:
            return dispatch_table[key]

        return None, None, False

    def _create_control_using_dispatch(
        self, label, data, data_type, data_style, c, attr, obj, additional_signal
    ):
        """
        Create a control using the dispatch table system.
        Returns (control, control_sizer, wants_listener) or None if unable to create.
        """
        factory, handler_factory, needs_special_handling = self._get_control_factory(
            data_type, data_style
        )

        if factory is None:
            return None, None, None

        # Handle special cases
        if needs_special_handling:
            if factory == "info":
                return self._create_info_control(label), None, False
            elif factory == "chart":
                return (
                    self._create_chart_control(
                        label, data, data_type, c, attr, obj, additional_signal
                    ),
                    None,
                    True,
                )
            elif factory == "color_type":
                return (
                    self._create_color_type_control(
                        label, data, data_type, c, attr, obj, additional_signal
                    ),
                    None,
                    True,
                )
            return None, None, None

        # Handle regular controls
        if factory == self._create_binary_control:
            # Binary controls have a different signature
            controls, control_sizer = factory(
                label, data, data_type, c, attr, obj, additional_signal
            )
            return controls, control_sizer, False
        elif data_style == "file":
            # File controls need extra parameters - create without handler first
            control, control_sizer = factory(
                label,
                data,
                data_type,
                {**c, "style": data_style},
                lambda: None,  # Dummy handler for now
            )
            # Now bind the real handler after control is created
            if handler_factory is not None:
                real_handler = handler_factory(
                    attr, control, obj, data_type, additional_signal, c, label
                )
                if hasattr(control, "Bind"):
                    control.Bind(wx.EVT_TEXT, real_handler)
            return control, control_sizer, True
        elif data_style == "option":
            # Option controls need choice list - create without handler first
            control, control_sizer = factory(
                label,
                data,
                data_type,
                c,
                lambda: None,  # Dummy handler for now
            )
            # Now bind the real handler after control is created
            if handler_factory is not None:
                real_handler = handler_factory(
                    attr,
                    control,
                    obj,
                    data_type,
                    additional_signal,
                    control._choice_list,
                )
                if hasattr(control, "Bind"):
                    control.Bind(wx.EVT_COMBOBOX, real_handler)
            return control, control_sizer, True
        elif data_type == bool and data_style == "button":
            # Button-style bool controls have different handler signature
            control, control_sizer, wants_listener = factory(
                label,
                data,
                data_type,
                c,
                lambda: None,  # Dummy handler for now
            )
            # Now bind the real handler after control is created
            if handler_factory is not None:
                real_handler = handler_factory(attr, obj, additional_signal)
                if hasattr(control, "Bind"):
                    control.Bind(wx.EVT_BUTTON, real_handler)
            return control, control_sizer, wants_listener
        elif data_type == bool:
            # Regular bool controls
            control, control_sizer, wants_listener = factory(
                label,
                data,
                data_type,
                c,
                lambda: None,  # Dummy handler for now
            )
            # Now bind the real handler after control is created
            if handler_factory is not None:
                real_handler = handler_factory(attr, control, obj, additional_signal)
                if hasattr(control, "Bind"):
                    control.Bind(wx.EVT_CHECKBOX, real_handler)
            return control, control_sizer, wants_listener
        elif data_type == str and data_style == "color":
            # Color button controls
            control, control_sizer, wants_listener = factory(
                label,
                data,
                data_type,
                c,
                lambda: None,  # Dummy handler for now
            )
            # Now bind the real handler after control is created
            if handler_factory is not None:
                real_handler = handler_factory(attr, control, obj, additional_signal)
                if hasattr(control, "Bind"):
                    control.Bind(wx.EVT_BUTTON, real_handler)
            return control, control_sizer, wants_listener
        else:
            # Standard text, combo, radio, slider controls
            control, control_sizer = factory(
                label,
                data,
                data_type,
                {**c, "style": data_style}
                if factory == self._create_text_control
                else c,
                lambda: None,  # Dummy handler for now
            )
            # Now bind the real handler after control is created
            if handler_factory is not None:
                real_handler = handler_factory(
                    attr, control, obj, data_type, additional_signal
                )
                # Bind appropriate event based on control type
                if hasattr(control, "Bind"):
                    if data_style in ("combo", "combosmall"):
                        control.Bind(wx.EVT_COMBOBOX, real_handler)
                        if hasattr(control, "GetTextCtrl"):
                            text_ctrl = control.GetTextCtrl()
                            if text_ctrl:
                                text_ctrl.Bind(wx.EVT_TEXT, real_handler)
                    elif data_style == "radio":
                        control.Bind(wx.EVT_RADIOBOX, real_handler)
                    elif data_style == "slider":
                        control.Bind(wx.EVT_SLIDER, real_handler)
                    else:
                        # Default text controls
                        control.Bind(wx.EVT_TEXT, real_handler)
            return control, control_sizer, True

    def _create_info_control(self, label):
        """Create info/static text controls."""
        msgs = label.split("\n")
        for lbl in msgs:
            control = wxStaticText(self, label=lbl)
        return control

    def _create_chart_control(
        self, label, data, data_type, c, attr, obj, additional_signal
    ):
        """Create chart/list controls (placeholder - keep existing logic for now)."""
        # This would contain the existing chart creation logic
        # For now, return None to indicate we should fall back to original logic
        return None

    def _create_color_type_control(
        self, label, data, data_type, c, attr, obj, additional_signal
    ):
        """Create Color type controls (placeholder - keep existing logic for now)."""
        # This would contain the existing Color type creation logic
        # For now, return None to indicate we should fall back to original logic
        return None

    def _format_text_display_value(self, data, data_type, config):
        """Format data for display in text controls."""
        if data_type == Length and hasattr(data, "preferred_length"):
            if not data._preferred_units:
                data._preferred_units = "mm"
            if not data._digits:
                if data._preferred_units in ("mm", "cm", "in", "inch"):
                    data._digits = 4
            return data.preferred_length
        else:
            return str(data)

    def _setup_text_validation(self, control, data_type, config):
        """Set up validation limits for text controls."""
        if data_type in (int, float):
            lower_range = config.get("lower", None)
            upper_range = config.get("upper", None)

            if lower_range is not None:
                control.lower_limit = lower_range
                control.lower_limit_err = lower_range
            if upper_range is not None:
                control.upper_limit = upper_range
                control.upper_limit_err = upper_range

    def _apply_control_width(self, control, width):
        """Helper method to apply width constraints to a control."""
        if width > 0:
            control.SetMaxSize(dip_size(self, width, -1))

    def _create_labeled_sizer(self, label, orientation=wx.HORIZONTAL):
        """Helper method to create a sizer with optional label."""
        if label != "":
            return StaticBoxSizer(self, wx.ID_ANY, label, orientation)
        else:
            return wx.BoxSizer(orientation)

    def _setup_control_properties(self, control, config, data=None):
        """Helper method to setup common control properties."""
        ctrl_width = config.get("width", 0)
        self._apply_control_width(control, ctrl_width)

        if data is not None:
            control.SetValue(str(data))

        tooltip = config.get("tip")
        if tooltip:
            control.SetToolTip(tooltip)

        return control

    def _create_control_with_handler(
        self,
        control_type,
        parent_sizer,
        control,
        handler,
        event_type,
        weight=1,
        expansion_flag=0,
    ):
        """Helper method to bind event handlers and add controls to sizers."""
        if handler:
            control.Bind(event_type, handler)
        parent_sizer.Add(control, expansion_flag * weight, wx.EXPAND, 0)
        return control

    def _make_combo_text_handler(self, param, ctrl, obj, dtype, addsig):
        """Creates a handler for combo text controls."""

        def handle_combo_text_change(event):
            v = dtype(ctrl.GetValue())
            self._update_property_and_signal(obj, param, v, addsig)

        return handle_combo_text_change

    def _make_button_handler(self, param, obj, addsig):
        """Creates a handler for button controls."""

        def handle_button_click(event):
            # We just set it to True to kick it off
            self._update_property_and_signal(obj, param, True, addsig)

        return handle_button_click

    def _make_checkbox_handler(self, param, ctrl, obj, addsig):
        """Creates a handler for checkbox controls."""

        def handle_checkbox_change(event):
            v = bool(ctrl.GetValue())
            self._update_property_and_signal(obj, param, v, addsig)

        return handle_checkbox_change

    def _make_checkbox_bitcheck_handler(
        self, param, ctrl, obj, bit, addsig, enable_ctrl=None
    ):
        """Creates a handler for checkbox bit controls."""

        def handle_checkbox_bit_change(event):
            v = ctrl.GetValue()
            if enable_ctrl is not None:
                enable_ctrl.Enable(v)
            current = getattr(obj, param)
            if v:
                current |= 1 << bit
            else:
                current = ~((~current) | (1 << bit))
            self._update_property_and_signal(obj, param, current, addsig)

        return handle_checkbox_bit_change

    def _make_generic_multi_handler(self, param, ctrl, obj, dtype, addsig):
        """Creates a handler for generic multi controls."""

        def handle_multi_text_change(event):
            v = ctrl.GetValue()
            try:
                dtype_v = dtype(v)
                self._update_property_and_signal(obj, param, dtype_v, addsig)
            except ValueError:
                # cannot cast to data_type, pass
                pass

        return handle_multi_text_change

    def _make_button_filename_handler(self, param, ctrl, obj, wildcard, addsig, label):
        """Creates a handler for file button controls."""

        def handle_file_button_click(event):
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
                try:
                    self._update_property_and_signal(obj, param, pathname, addsig)
                except ValueError:
                    # cannot cast to data_type, pass
                    pass

        return handle_file_button_click

    def _make_file_text_handler(self, param, ctrl, obj, dtype, addsig):
        """Creates a handler for file text controls."""

        def handle_file_text_change(event):
            v = ctrl.GetValue()
            try:
                dtype_v = dtype(v)
                self._update_property_and_signal(obj, param, dtype_v, addsig)
            except ValueError:
                # cannot cast to data_type, pass
                pass

        return handle_file_text_change

    def _make_file_text_handler_with_button(
        self, param, ctrl, obj, dtype, addsig, config, label
    ):
        """Creates a handler for file text controls with button integration."""

        def handle_file_text_change(event):
            v = ctrl.GetValue()
            try:
                dtype_v = dtype(v)
                self._update_property_and_signal(obj, param, dtype_v, addsig)
            except ValueError:
                # cannot cast to data_type, pass
                pass

        # Set up button if it exists
        if hasattr(ctrl, "_file_button"):
            wildcard = getattr(ctrl, "_wildcard", "*")
            ctrl._file_button.Bind(
                wx.EVT_BUTTON,
                self._make_button_filename_handler(
                    param,
                    ctrl,
                    obj,
                    wildcard,
                    addsig,
                    label,
                ),
            )

        return handle_file_text_change

    def _make_slider_handler(self, param, ctrl, obj, dtype, addsig):
        """Creates a handler for slider controls."""

        def handle_slider_change(event):
            v = dtype(ctrl.GetValue())
            self._update_property_and_signal(obj, param, v, addsig)

        return handle_slider_change

    def _make_radio_select_handler(self, param, ctrl, obj, dtype, addsig):
        """Creates a handler for radio selection controls."""

        def handle_radio_selection_change(event):
            if dtype == int:
                v = dtype(ctrl.GetSelection())
            else:
                v = dtype(ctrl.GetLabel())
            self._update_property_and_signal(obj, param, v, addsig)

        return handle_radio_selection_change

    def _make_combosmall_option_handler(
        self, param, ctrl, obj, dtype, addsig, choice_list
    ):
        """Creates a handler for small combo option controls."""

        def handle_combo_option_selection(event):
            cl = choice_list[ctrl.GetSelection()]
            v = dtype(cl)
            self._update_property_and_signal(obj, param, v, addsig)

        return handle_combo_option_selection

    def _make_combosmall_text_handler(self, param, ctrl, obj, dtype, addsig):
        """Creates a handler for small combo text controls."""

        def handle_combo_text_entry(event):
            v = dtype(ctrl.GetValue())
            self._update_property_and_signal(obj, param, v, addsig)

        return handle_combo_text_entry

    def _make_button_color_handler(self, param, ctrl, obj, addsig):
        """Creates a handler for color button controls."""

        def handle_color_button_click(event):
            color_data = wx.ColourData()
            color_data.SetColour(wx.Colour(swizzlecolor(ctrl.color)))
            dlg = wx.ColourDialog(self, color_data)
            if dlg.ShowModal() == wx.ID_OK:
                color_data = dlg.GetColourData()
                data = Color(swizzlecolor(color_data.GetColour().GetRGB()), 1.0)
                set_color(ctrl, data)
                try:
                    data_v = data.hexa
                    self._update_property_and_signal(obj, param, data_v, addsig)
                except ValueError:
                    # cannot cast to data_type, pass
                    pass

        return handle_color_button_click

    def _make_angle_text_handler(self, param, ctrl, obj, dtype, addsig):
        """Creates a handler for angle text controls."""

        def handle_angle_text_change(event):
            try:
                v = Angle(ctrl.GetValue(), digits=5)
                data_v = str(v)
                self._update_property_and_signal(obj, param, data_v, addsig)
            except ValueError:
                # cannot cast to data_type, pass
                pass

        return handle_angle_text_change

    def _make_chart_start_handler(self, columns, param, ctrl, local_obj):
        """Creates a handler for chart start events."""

        def handle_chart_edit_start(event):
            for column in columns:
                if column.get("editable", False):
                    event.Allow()
                else:
                    event.Veto()

        return handle_chart_edit_start

    def _make_chart_stop_handler(self, columns, param, ctrl, local_obj):
        """Creates a handler for chart stop events."""

        def handle_chart_edit_stop(event):
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

        return handle_chart_edit_stop

    def _make_chart_contextmenu_handler(
        self, columns, param, ctrl, local_obj, allow_del, allow_dup, default
    ):
        """Creates a handler for chart context menu events."""

        def handle_chart_context_menu(event):
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

                def handle_delete_menu_item(event):
                    values = getattr(local_obj, param)
                    values.pop(row_id)
                    self.context.signal(param, values, 0, param)
                    fill_ctrl(ctrl, local_obj, param, columns)

                menuitem = menu.Append(wx.ID_ANY, _("Delete this entry"), "")
                self.Bind(wx.EVT_MENU, handle_delete_menu_item, id=menuitem.GetId())

            if l_allow_dup:

                def handle_duplicate_menu_item(event):
                    values = getattr(local_obj, param)
                    if isinstance(values[row_id], dict):
                        newentry = dict()
                        for key, content in values[row_id].items():
                            newentry[key] = content
                    else:
                        newentry = copy(values[row_id])
                    values.append(newentry)
                    self.context.signal(param, values, 0, param)
                    fill_ctrl(ctrl, local_obj, param, columns)

                menuitem = menu.Append(wx.ID_ANY, _("Duplicate this entry"), "")
                self.Bind(wx.EVT_MENU, handle_duplicate_menu_item, id=menuitem.GetId())

            def handle_default_menu_item(event):
                values = getattr(local_obj, param)
                values.clear()
                for e in default:
                    values.append(e)
                self.context.signal(param, values, 0, param)
                fill_ctrl(ctrl, local_obj, param, columns)

            menuitem = menu.Append(wx.ID_ANY, _("Restore defaults"), "")
            self.Bind(wx.EVT_MENU, handle_default_menu_item, id=menuitem.GetId())

            if menu.MenuItemCount != 0:
                self.PopupMenu(menu)
                menu.Destroy()

        return handle_chart_context_menu

    def _make_generic_text_handler(self, param, ctrl, obj, dtype, addsig):
        """Creates a handler for generic text controls."""

        def handle_generic_text_change(event):
            v = ctrl.GetValue()
            try:
                dtype_v = dtype(v)
                self._update_property_and_signal(obj, param, dtype_v, addsig)
            except ValueError:
                # cannot cast to data_type, pass
                pass

        return handle_generic_text_change

    def _make_length_text_handler(self, param, ctrl, obj, dtype, addsig):
        """Creates a handler for length text controls."""

        def handle_length_text_change(event):
            try:
                v = Length(ctrl.GetValue())
                data_v = v.preferred_length
                # Special comparison for length objects as strings
                current_value = getattr(obj, param)
                if str(current_value) != str(data_v):
                    setattr(obj, param, data_v)
                    self.context.signal(param, data_v, obj)
                    for _sig in addsig:
                        self.context.signal(_sig)
            except ValueError:
                # cannot cast to data_type, pass
                pass

        return handle_length_text_change

    def on_close(self, event):
        # We should not need this, but better safe than sorry
        event.Skip()
        self.pane_hide()

    def _validate_and_prepare_choice(self, c):
        """Validate and prepare a choice configuration."""
        if isinstance(c, tuple):
            # If c is tuple, convert to dict
            dict_c = {}
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
            return None, None, None, False

        # Check if hidden and not in developer mode
        hidden = c.get("hidden", False)
        hidden = bool(hidden) if hidden != "False" else False
        developer_mode = self.context.root.setting(bool, "developer_mode", False)
        if not developer_mode and hidden:
            return None, None, None, False

        # Check if ignored
        ignore = c.get("ignore", False)
        ignore = bool(ignore) if ignore != "False" else False
        if ignore:
            return None, None, None, False

        return c, attr, obj, True

    def _get_choice_data_and_type(self, c, obj, attr):
        """Get data and data type for a choice."""
        # get default value
        if hasattr(obj, attr):
            data = getattr(obj, attr)
        else:
            # if obj lacks attr, default must have been assigned.
            try:
                data = c["default"]
            except KeyError:
                # This choice is in error.
                return None, None

        data_type = type(data)
        data_type = c.get("type", data_type)
        return data, data_type

    def _get_additional_signals(self, c):
        """Extract additional signals from choice configuration."""
        additional_signal = []
        sig = c.get("signals")
        if isinstance(sig, str):
            additional_signal.append(sig)
        elif isinstance(sig, (tuple, list)):
            for _sig in sig:
                additional_signal.append(_sig)
        return additional_signal

    def _setup_control_properties(self, c, control, attr, obj):
        """Set up control properties like tooltips, help, and conditional enabling."""
        if control is None:
            return

        # Set tooltip
        tip = c.get("tip")
        if tip and not self.context.root.disable_tool_tips:
            control.SetToolTip(tip)

        # Set help text
        _help = c.get("help")
        if _help and hasattr(control, "SetHelpText"):
            control.SetHelpText(_help)

        # Handle enabled state and conditional enabling
        try:
            enabled = c["enabled"]
            control.Enable(enabled)
        except KeyError:
            # Listen to establish whether this control should be enabled based on another control's value.
            self._setup_conditional_enabling(c, control, attr, obj)

    def _setup_conditional_enabling(self, c, control, attr, obj):
        """Set up conditional enabling based on other control values."""
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
                            enable = bool(eqs[0] <= getattr(obj, param) <= eqs[1])
                        else:
                            enable = bool(getattr(obj, param) == eqs)
                        ctrl.Enable(enable)
                    except (IndexError, RuntimeError):
                        pass

                return listen

            listener = on_enable_listener(c_attr, control, c_obj, c_equals)
            self.listeners.append((c_attr, listener, c_obj))
            self.context.listen(c_attr, listener)
        except KeyError:
            pass

    def _setup_update_listener(
        self, c, control, attr, obj, data_type, data_style, choice_list
    ):
        """Set up update listener for control synchronization."""

        def on_update_listener(param, ctrl, dtype, dstyle, choicelist, sourceobj):
            def listen_to_myself(origin, value, target=None):
                if self.context.kernel.is_shutdown:
                    return

                if target is None or target is not sourceobj:
                    return

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
                    return

                # Check if control still exists
                try:
                    dummy = hasattr(ctrl, "GetValue")
                except RuntimeError:
                    return

                # Update control based on data type and style
                self._update_control_value(ctrl, data, dtype, dstyle, choicelist)

            return listen_to_myself

        update_listener = on_update_listener(
            attr, control, data_type, data_style, choice_list, obj
        )
        self.listeners.append((attr, update_listener, obj))
        self.context.listen(attr, update_listener)

    def _update_control_value(self, ctrl, data, dtype, dstyle, choicelist):
        """Update a control's value based on its type and style."""
        update_needed = False

        if dtype == bool:
            if ctrl.GetValue() != data:
                ctrl.SetValue(data)
        elif dtype == str and dstyle == "file":
            if ctrl.GetValue() != data:
                ctrl.SetValue(data)
        elif dtype in (int, float) and dstyle == "slider":
            if ctrl.GetValue() != data:
                ctrl.SetValue(data)
        elif dtype in (str, int, float) and dstyle in ("combo", "combosmall"):
            if dtype == str:
                ctrl.SetValue(str(data))
            else:
                least = None
                for entry in choicelist:
                    if least is None:
                        least = entry
                    else:
                        if abs(dtype(entry) - data) < abs(dtype(least) - data):
                            least = entry
                if least is not None:
                    ctrl.SetValue(least)
        elif (dtype == str and dstyle == "color") or dtype == Color:

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
                data = Color(data)
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
