from copy import copy

import wx
from numpy import dtype

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
    A dynamic, configurable property panel that automatically generates GUI controls based on choice dictionaries.

    ChoicePropertyPanel provides a flexible system for creating property editing interfaces without requiring
    static UI definitions. It automatically generates appropriate controls (textboxes, checkboxes, sliders, etc.)
    based on data types and style configurations provided in choice dictionaries.

    Key Features:
        - Automatic control generation based on data types and styles
        - Support for complex layouts with pages, sections, and subsections
        - Real-time property synchronization with signal dispatching
        - Extensive customization through choice dictionary configuration
        - Support for conditional enabling/disabling of controls (unified architecture)
        - Optimized parameter architecture with minimal redundancy
        - Automatic listener management with proper cleanup on pane hide/show

    Choice Dictionary Configuration:
        Required Keys:
            "object": The object containing the property to be edited
            "attr": The attribute name on the object
            "type": Python data type (bool, str, int, float, Length, Angle, Color, list)

        Common Optional Keys:
            "default": Default value if attribute doesn't exist
            "label": Display label for the control (defaults to attr name)
            "style": Control style override (see Style Options below)
            "tip": Tooltip text for the control
            "enabled": Whether control is enabled (default: True)
            "signals": Additional signals to emit on value change
            "width": Control width constraint
            "help": Help text for the control

        Layout Keys:
            "page": Top-level grouping (creates labeled sections)
            "section": Mid-level grouping within pages
            "subsection": Controls grouped horizontally
            "priority": Sort order within same page/section
            "weight": Relative width allocation in subsections (default: 1)

        Advanced Keys:
            "dynamic": Function called to update choice before UI creation
            "conditional": Tuple (obj, attr[, value[, max]]) for conditional enabling
            "hidden": Show only in developer mode
            "ignore": Skip this choice entirely

    Conditional Enabling:
        The "conditional" key supports four patterns:
        1. Boolean check (2-tuple):     (obj, "attr")
           → Enables if getattr(obj, "attr") is truthy
        2. Value equality (3-tuple):    (obj, "attr", value)
           → Enables if getattr(obj, "attr") == value
        3. Multiple values (3-tuple):   (obj, "attr", [v1, v2, v3])
           → Enables if getattr(obj, "attr") matches any value in list
        4. Range check (4-tuple):       (obj, "attr", min, max)
           → Enables if min <= getattr(obj, "attr") <= max
        
        Note: Conditional listeners are automatically registered and deregistered with pane_hide/pane_show.

    Data Types and Default Controls:
        bool: Checkbox (style="button" creates action button)
        str: TextCtrl (various styles available)
        int/float: TextCtrl with validation (styles: slider, combo, power, speed)
        Length: TextCtrl with length validation and preferred units
        Angle: TextCtrl with angle validation
        Color: Color picker button
        list: Chart/table control for editing lists

    Style Options:
        Text Styles:
            "file": File selection dialog with browse button
            "multiline": Multi-line text input
            "combo": Dropdown with predefined choices
            "combosmall": Compact dropdown
            "option": Combo with separate display/value lists
            "power": Power value with percentage/absolute modes
            "speed": Speed value with per-minute/per-second modes
            "radio": Radio box selection
            "flat": Flat-style text control

        Numeric Styles:
            "slider": Slider control (requires "min"/"max" keys)
            "binary": Bit manipulation checkboxes (requires "bits"/"mask" keys)
            "info": Static text display (read-only)

        Boolean Styles:
            "button": Action button instead of checkbox
            "color": Color picker button (for str type)

        Special Styles:
            "chart": List/table control for editing complex data

    Special Configuration Flags:
        Power Controls:
            "percent": bool or callable - display as percentage (0-100%) vs absolute (0-1000)

        Speed Controls:
            "perminute": bool or callable - display per-minute vs per-second values

        File Controls:
            "wildcard": File dialog filter pattern

        Slider Controls:
            "min": Minimum value (can be callable)
            "max": Maximum value (can be callable)

        Binary Controls:
            "bits": Number of bits to display (default: 8)
            "mask": Attribute name for bit mask

        Combo Controls:
            "choices": List of available values
            "display": List of display strings (for "option" style)
            "exclusive": Whether combo allows custom values (default: True)

        Length Controls:
            "nonzero": Require non-zero values

        Validation:
            "lower": Minimum allowed value
            "upper": Maximum allowed value

    Layout System:
        - Choices are sorted by: priority → page → section → subsection
        - Pages create major visual groups with labels
        - Sections create sub-groups within pages
        - Subsections group controls horizontally with shared space
        - Weight determines relative width allocation within subsections
        - Leading "_sortkey_" in names is removed for display (allows custom sorting)
        - entries_per_column: Distribute controls across multiple columns

    Event System:
        - Automatic signal dispatching on property changes
        - Property name used as signal identifier
        - Additional signals can be specified in "signals" key
        - Real-time synchronization between multiple panels editing same properties
        - Conditional enabling automatically updates when conditions change
        - Listeners automatically reestablished when pane is shown (pane_show)
        - Listeners safely removed when pane is hidden (pane_hide)

    Constraints:
        The constraint parameter allows selective display:
        - None: Show all choices
        - (start, end): Show choices by index range
        - ["page1", "page2"]: Show only specified pages
        - ["-page1"]: Show all except specified pages

    Internal Architecture:
        - _create_control_using_dispatch(): Dispatch table for control creation
        - _setup_choice_control_properties(): Set up all control properties (tooltips, help, enabling)
        - _setup_control_enabling(): Unified method for all enabling logic (conditional + simple)
        - _register_conditional_listener(): Register listeners for dynamic condition checking
        - Listener management: All listeners stored for proper cleanup on pane_hide/pane_show

    Examples:
        Basic usage:
            choices = [
                {"object": obj, "attr": "name", "type": str, "label": "Name"},
                {"object": obj, "attr": "enabled", "type": bool, "label": "Enabled"}
            ]
            panel = ChoicePropertyPanel(parent, choices=choices, context=context)

        Conditional enabling (enable "power" only when "laser_active" is True):
            choices = [
                {"object": device, "attr": "laser_active", "type": bool, "label": "Laser Active"},
                {
                    "object": device, 
                    "attr": "power", 
                    "type": float,
                    "label": "Power",
                    "conditional": (device, "laser_active"),
                    "style": "power"
                }
            ]

        Conditional enabling with value check (enable "co2_settings" only for CO2 laser):
            choices = [
                {"object": device, "attr": "laser_type", "type": str, "style": "combo", 
                 "choices": ["co2", "fiber", "uv"]},
                {
                    "object": device,
                    "attr": "co2_settings",
                    "type": str,
                    "conditional": (device, "laser_type", "co2")
                }
            ]

        Advanced configuration:
            choice = {
                "object": laser,
                "attr": "power",
                "type": float,
                "style": "power",
                "label": "Laser Power",
                "percent": lambda: laser.power_mode == "percentage",
                "tip": "Laser power setting",
                "page": "Laser Settings",
                "section": "Power Control",
                "priority": "10_power"
            }
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
                for lookup_item in lookup_choice:
                    if "help" not in lookup_item:
                        lookup_item["help"] = choice
                new_choices.extend(lookup_choice)
            else:
                for choice_item in choice:
                    if "help" not in choice_item:
                        choice_item["help"] = standardhelp
                new_choices.extend(choice)
        choices = new_choices
        if injector is not None:
            # We have additional stuff to be added, so be it
            for injected_choice in injector:
                choices.append(injected_choice)
        if not choices:
            # No choices to process.
            return
        # Validate and look for dynamic
        for choice in choices:
            if not self._validate_choice_for_crucial_information(choice):
                if self.context:
                    channel = self.context.kernel.channels["console"]
                    channel(f"Invalid choice configuration: {choice}")
                # Delete choice
                choices.remove(choice)
                continue

            needs_dynamic_call = choice.get("dynamic")
            if needs_dynamic_call:
                # Calls dynamic function to update this dictionary before production
                needs_dynamic_call(choice)
                # print(f"Now we have: {choice}")
        # Set default values for required keys
        for choice in choices:
            choice.setdefault("subsection", "")
            choice.setdefault("section", "")
            choice.setdefault("page", "")
            choice.setdefault("priority", "ZZZZZZZZ")
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
                        for i, sorted_choice in enumerate(prechoices):
                            this_page = sorted_choice.get("page", "").lower()
                            if negative and positive:
                                # Negative takes precedence:
                                if this_page not in negative and this_page in positive:
                                    self.choices.append(sorted_choice)
                            elif len(negative) > 0:
                                # only negative....
                                if this_page not in negative:
                                    self.choices.append(sorted_choice)
                            elif len(positive) > 0:
                                # only positive....
                                if this_page in positive:
                                    self.choices.append(sorted_choice)
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
                        for i, sorted_choice in enumerate(prechoices):
                            if start_from <= i < end_at:
                                self.choices.append(sorted_choice)
        if not dealt_with:
            # no valid constraints
            self.choices = prechoices
        if len(self.choices) == 0:
            return
        root_horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        root_horizontal_sizer.Add(sizer_main, 1, wx.EXPAND, 0)
        last_page = ""
        last_section = ""
        last_subsection = ""
        current_container = None
        active_page_sizer = sizer_main
        active_section_sizer = sizer_main
        active_subsection_sizer = sizer_main
        # By default, 0 as we are stacking up stuff
        expansion_flag = 0
        current_col_entry = -1
        for i, choice in enumerate(self.choices):
            wants_listener = True
            current_col_entry += 1
            if (
                self.entries_per_column is not None
                and current_col_entry >= self.entries_per_column
            ):
                current_col_entry = -1
                prev_main = sizer_main
                sizer_main = wx.BoxSizer(wx.VERTICAL)
                if prev_main == active_page_sizer:
                    active_page_sizer = sizer_main
                if prev_main == active_section_sizer:
                    active_section_sizer = sizer_main
                if prev_main == active_subsection_sizer:
                    active_subsection_sizer = sizer_main

                root_horizontal_sizer.Add(sizer_main, 1, wx.EXPAND, 0)
                # I think we should reset all sections to make them
                # reappear in the next columns
                last_page = ""
                last_section = ""
                last_subsection = ""

            # Validate and prepare choice using helper method
            validated_choice, attr, obj, is_valid = self._validate_and_prepare_choice(
                choice
            )
            if not is_valid or validated_choice is None:
                continue

            # Use the validated choice from here on
            choice = validated_choice
            # Get data and data type using helper method
            data, data_type = self._get_choice_data_and_type(choice, obj)
            if data is None and data_type is None:
                continue
            data_style = choice.get("style", None)
            data_type = choice.get("type")

            this_subsection = choice.get("subsection", "")
            this_section = choice.get("section", "")
            this_page = choice.get("page", "")

            # Get additional signals using helper method
            additional_signal = self._get_additional_signals(choice)

            # Do we have a parameter to affect the space consumption?
            weight = int(choice.get("weight", 1))
            if weight < 0:
                weight = 0

            choice_list = None
            label = choice.get("label", attr)  # Undefined label is the attr

            # Do we have a parameter to add a trailing label after the control
            trailer = choice.get("trailer")
            # Handle dynamic trailer for power controls
            if data_type == float and data_style == "power":
                percent_flag = choice.get("percent", False)
                percent_mode = (
                    percent_flag() if callable(percent_flag) else percent_flag
                )
                trailer = "%" if percent_mode else "/1000"
            if data_type == float and data_style == "speed":
                minute_flag = choice.get("perminute", False)
                minute_mode = minute_flag() if callable(minute_flag) else minute_flag
                trailer = "mm/min" if minute_mode else "mm/s"
            if last_page != this_page:
                expansion_flag = 0
                last_section = ""
                last_subsection = ""
                # We could do a notebook, but let's choose a simple StaticBoxSizer instead...
                current_container = StaticBoxSizer(
                    self, wx.ID_ANY, _(self.unsorted_label(this_page)), wx.VERTICAL
                )
                sizer_main.Add(current_container, 0, wx.EXPAND, 0)
                active_page_sizer = current_container
                active_section_sizer = current_container
                active_subsection_sizer = current_container

            if last_section != this_section:
                expansion_flag = 0
                last_subsection = ""
                if this_section != "":
                    current_container = StaticBoxSizer(
                        self,
                        id=wx.ID_ANY,
                        label=_(self.unsorted_label(this_section)),
                        orientation=wx.VERTICAL,
                    )
                    active_page_sizer.Add(current_container, 0, wx.EXPAND, 0)
                else:
                    current_container = active_page_sizer
                active_subsection_sizer = current_container
                active_section_sizer = current_container

            if last_subsection != this_subsection:
                expansion_flag = 0
                if this_subsection != "":
                    expansion_flag = 1
                    lbl = _(self.unsorted_label(this_subsection))
                    if lbl != "":
                        current_container = StaticBoxSizer(
                            self,
                            id=wx.ID_ANY,
                            label=lbl,
                            orientation=wx.HORIZONTAL,
                        )
                    else:
                        current_container = wx.BoxSizer(wx.HORIZONTAL)
                    active_section_sizer.Add(current_container, 0, wx.EXPAND, 0)
                    img = choice.get("icon", None)
                    if img is not None:
                        icon = wxStaticBitmap(self, wx.ID_ANY, bitmap=img)
                        current_container.Add(icon, 0, wx.ALIGN_CENTER_VERTICAL, 0)
                        current_container.AddSpacer(5)
                else:
                    current_container = active_section_sizer
                active_subsection_sizer = current_container

            control = None
            control_sizer = None

            # Try to create control using the dispatch table system
            dispatch_result = self._create_control_using_dispatch(
                label, data, choice, obj
            )

            if dispatch_result[0] is not None:
                # Successfully created using dispatch table
                control, control_sizer, wants_listener = dispatch_result
                if control_sizer is not None:
                    active_subsection_sizer.Add(
                        control_sizer, expansion_flag * weight, wx.EXPAND, 0
                    )
                elif control is not None:
                    active_subsection_sizer.Add(
                        control, expansion_flag * weight, wx.EXPAND, 0
                    )
            elif data_type == list and data_style == "chart":
                # Chart controls - complex case not yet unified
                chart = EditableListCtrl(
                    self,
                    wx.ID_ANY,
                    style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
                    context=self.context,
                    list_name=f"list_chart_{attr}",
                )
                l_columns = choice.get("columns", [])

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

                allow_deletion = choice.get("allow_deletion", False)
                allow_duplication = choice.get("allow_duplication", False)

                default = choice.get("default", [])

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
                active_subsection_sizer.Add(
                    chart, expansion_flag * weight, wx.EXPAND, 0
                )
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
                self._apply_control_width(control, choice.get("width", 0))
                control_sizer.Add(control, 0, wx.EXPAND, 0)

                control.Bind(
                    wx.EVT_BUTTON,
                    self._make_button_color_handler(control, choice),
                )
                active_subsection_sizer.Add(
                    control_sizer, expansion_flag * weight, wx.EXPAND, 0
                )
                wants_listener = True
            else:
                # Requires a registered data_type
                continue

            if trailer and control_sizer:
                trailer_text = wxStaticText(self, id=wx.ID_ANY, label=f" {trailer}")
                control_sizer.Add(trailer_text, 0, wx.ALIGN_CENTER_VERTICAL, 0)

            if control is None:
                continue  # We're binary or some other style without a specific control.

            if wants_listener:
                # Use helper method for setting up update listener
                self._setup_update_listener(choice, control, obj, choice_list)

            # Use helper method for setting up control properties (including enabling state)
            self._setup_choice_control_properties(choice, control)
            last_page = this_page
            last_section = this_section
            last_subsection = this_subsection

        self.SetSizer(root_horizontal_sizer)
        # Do not call Fit(self) on a ScrolledPanel, as it can negate scrolling and cause layout issues.

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
        has_settings = hasattr(obj, "settings") and param in obj.settings
        current_value = obj.settings[param] if has_settings else getattr(obj, param)
        # print (f"Update property: {new_value} for attr: {param}, current: {current_value}")

        # Special handling for Angle comparison to avoid TypeError
        try:
            values_different = current_value != new_value
        except (TypeError, ValueError):
            # Fallback to string comparison for problematic types like Angle
            values_different = str(current_value) != str(new_value)

        if values_different:
            setattr(obj, param, new_value)
            if has_settings:
                obj.settings[param] = new_value
            self._dispatch_signals(param, new_value, obj, additional_signals)
            return True
        return False

    # UI Helper Methods
    def _create_text_control(self, label, data, choice, handler_factory):
        """
        Unified TextCtrl creation for all text-based inputs.

        This is the primary factory function for creating text-based controls across
        all data types (str, int, float, Length, Angle). It handles the complex
        configuration needed for different input types and styles.

        Recent optimizations:
        - Handler factories now receive control and choice only, extracting parameters internally
        - Consistent formatting using _format_text_display_value for display values
        - Proper support for power/speed controls with callable mode flags

        Args:
            label (str): Display label for the control
            data: Current value to display in the control
            choice (dict): Complete choice configuration
            handler_factory (callable): Factory function that creates the event handler

        Returns:
            tuple: (control, control_sizer) - the text control and its container sizer
        """
        # Extract type and style from choice
        data_type = choice.get("type")
        data_style = choice.get("style")

        # Handle special flat style
        if choice.get("style") == "flat":
            control_sizer = wx.BoxSizer(wx.HORIZONTAL)
            if label != "":
                label_text = wxStaticText(self, id=wx.ID_ANY, label=label)
                control_sizer.Add(label_text, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        else:
            control_sizer = self._create_labeled_sizer(label)

        # Determine text control configuration
        text_config = self._get_text_control_config(data_type, choice)

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
        display_value = self._format_text_display_value(data, choice)
        control.SetValue(display_value)

        # Apply width and validation
        self._apply_control_width(control, choice.get("width", 0))
        self._setup_text_validation(control, data_type, choice)

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

    def _create_combo_control(self, label, data, choice, handler_factory=None):
        """Unified wxComboBox creation for all combo-based inputs."""
        # Extract type and style from choice
        data_type = choice.get("type")
        data_style = choice.get("style")

        # Determine sizer type based on style
        if data_style == "combosmall":
            control_sizer = wx.BoxSizer(wx.HORIZONTAL)
        else:
            control_sizer = self._create_labeled_sizer(label)

        # Get combo configuration
        combo_config = self._get_combo_control_config(data_type, choice)

        # Check if display/choices separation is needed
        has_display = "display" in choice and choice["display"] != choice.get("choices")
        if has_display:
            # Use display/choices separation like "option" style
            display_list = list(map(str, choice.get("display")))
            choice_list = list(choice.get("choices", [choice.get("default")]))

            # Handle value not in list
            try:
                index = choice_list.index(data)
            except ValueError:
                index = 0
                if data is None:
                    data = choice.get("default")
                display_list.insert(0, str(data))
                choice_list.insert(0, data)

            # Create the control
            control = wxComboBox(
                self,
                wx.ID_ANY,
                choices=display_list,
                style=combo_config["style"],
            )
            control.SetSelection(index)

            # Store choice list for handler
            control._choice_list = choice_list
        else:
            # Standard combo without display/choices separation
            raw_choice_list = list(choice.get("choices", [choice.get("default")]))
            display_choice_list = list(map(str, raw_choice_list))

            # Create the control
            control = wxComboBox(
                self,
                wx.ID_ANY,
                choices=display_choice_list,
                style=combo_config["style"],
            )

            # Set display value
            self._set_combo_value(control, data, data_type, display_choice_list)
            
            # Store raw choices
            control._choice_list = raw_choice_list

        # Apply width constraints
        if data_style == "combosmall":
            testsize = control.GetBestSize()
            control.SetMaxSize(dip_size(self, testsize[0] + 30, -1))
        else:
            self._apply_control_width(control, choice.get("width", 0))

        # Add to sizer
        if data_style == "combosmall" and label != "":
            label_text = wxStaticText(self, id=wx.ID_ANY, label=label)
            control_sizer.Add(label_text, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        control_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        # Set up event handler
        if handler_factory:
            if has_display:
                # Use option handler for display/choices separation
                real_handler = self._make_combosmall_option_handler(control, choice)
                control.Bind(wx.EVT_COMBOBOX, real_handler)
            else:
                # Use the provided handler factory
                control.Bind(wx.EVT_COMBOBOX, handler_factory())
            # For combosmall non-exclusive, also bind text events
            if data_style == "combosmall" and not choice.get("exclusive", True):
                if has_display:
                    control.Bind(wx.EVT_TEXT, real_handler)
                else:
                    handler = self._make_combosmall_text_handler(control, choice)
                    control.Bind(wx.EVT_TEXT, handler)

        return control, control_sizer

    def _get_text_control_config(self, data_type, choice):
        """
        Generates TextCtrl configuration based on data type and style.

        This function creates the appropriate validation and display configuration
        for text controls based on the data type and special style requirements.
        It handles complex configurations for power and speed controls that can
        operate in different modes (percentage/absolute, per-minute/per-second).

        Enhanced Features:
        - Dynamic validation limits based on callable flags
        - Power control support with percentage/absolute mode detection
        - Speed control support with per-minute/per-second mode detection
        - Proper validation types for numeric controls
        - Length/Angle-specific validation and formatting

        Args:
            data_type (type): The Python type (int, float, str, Length, Angle)
            choice (dict): Choice configuration with style, validation limits, and flags

        Returns:
            dict: Configuration dictionary for TextCtrl creation containing:
                - style: wx text control style flags
                - limited: bool indicating validation is enabled
                - check: validation type ("int", "float", "length", "angle")
                - lower/upper: validation bounds
                - nonzero: whether zero values are allowed
        """
        text_config = {"style": wx.TE_PROCESS_ENTER}

        # Type-specific configurations
        if data_type in (int, float):
            text_config["limited"] = True
            text_config["check"] = "int" if data_type == int else "float"

            # Special handling for power controls - set appropriate validation limits
            if choice.get("style") == "power":
                # Determine if this is percentage or absolute mode
                percent_flag = choice.get("percent", False)
                percent_mode = (
                    percent_flag() if callable(percent_flag) else percent_flag
                )

                if percent_mode:
                    # Percentage mode: 0-100%
                    text_config.update({"lower": 0.0, "upper": 100.0})
                else:
                    # Absolute mode: 0-1000
                    text_config.update({"lower": 0.0, "upper": 1000.0})
            # Special handling for speed controls - set appropriate validation limits
            if choice.get("style") == "speed":
                # Determine if this is per minute or per second mode
                perminute_flag = choice.get("perminute", False)
                perminute_mode = (
                    perminute_flag() if callable(perminute_flag) else perminute_flag
                )

                # Set minimum to 0, but let maximum be flexible for speed values
                text_config.update({"lower": 0.0})

        elif data_type == Length:
            text_config.update(
                {
                    "limited": True,
                    "check": "length",
                    "nonzero": choice.get("nonzero", False),
                }
            )
        elif data_type == Angle:
            text_config.update({"check": "angle", "limited": True})
        elif choice.get("style") == "multiline":
            text_config["style"] = wx.TE_MULTILINE
        elif choice.get("style") == "file":
            text_config.update(
                {
                    "has_button": True,
                    "button_text": "...",
                    "wildcard": choice.get("wildcard", "*"),
                }
            )

        return text_config

    def _get_combo_control_config(self, data_type, choice):
        """Generate wxComboBox configuration based on data type and style."""
        combo_config = {}
        data_style = choice.get("style")

        if data_style == "combosmall":
            exclusive = choice.get("exclusive", True)
            combo_config["style"] = (
                wx.CB_DROPDOWN | wx.CB_READONLY if exclusive else wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER
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

    def _create_radio_control(self, label, data, choice, handler_factory=None):
        """Unified radio control creation for radio and option styles."""
        # Extract type and style from choice
        data_type = choice.get("type")
        data_style = choice.get("style")

        # Create horizontal sizer for both types
        control_sizer = wx.BoxSizer(wx.HORIZONTAL)

        if data_style == "radio":
            # Traditional radio box
            choice_list = list(map(str, choice.get("choices", [choice.get("default")])))
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
            self._apply_control_width(control, choice.get("width", 0))
            control_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL, 0)

            # Set up event handler
            if handler_factory:
                control.Bind(wx.EVT_RADIOBOX, handler_factory())

        elif data_style == "option":
            # Option-style combo with display/choice separation
            display_list = list(map(str, choice.get("display")))
            choice_list = list(map(str, choice.get("choices", [choice.get("default")])))

            # Handle value not in list
            try:
                index = choice_list.index(str(data))
            except ValueError:
                index = 0
                if data is None:
                    data = choice.get("default")
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
                label_text = wxStaticText(self, id=wx.ID_ANY, label=f"{label} ")
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

    def _create_button_control(self, label, data, choice, handler_factory=None):
        """Unified button control creation for button, color, and checkbox styles."""
        # Extract type and style from choice
        data_type = choice.get("type")
        data_style = choice.get("style")
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
        self._apply_control_width(control, choice.get("width", 0))

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

    def _create_slider_control(self, label, data, choice, handler_factory=None):
        """Unified slider control creation for numeric slider inputs."""
        # Extract type and style from choice
        data_type = choice.get("type")
        data_style = choice.get("style")
        # Create labeled sizer
        control_sizer = self._create_labeled_sizer(label)

        # Get slider configuration
        minvalue = choice.get("min", 0)
        maxvalue = choice.get("max", 0)

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
            value=int(value),
            minValue=int(minvalue),
            maxValue=int(maxvalue),
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )

        # Apply width and add to sizer
        self._apply_control_width(control, choice.get("width", 0))
        control_sizer.Add(control, 1, wx.EXPAND, 0)

        if handler_factory:
            control.Bind(wx.EVT_SLIDER, handler_factory())

        return control, control_sizer

    def _create_binary_control(self, label, data, choice, obj):
        """Unified binary control creation for binary checkbox patterns."""
        attr = choice["attr"]
        data_type = choice.get("type")
        mask = choice.get("mask")
        additional_signal = self._get_additional_signals(choice)

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
        bits = choice.get("bits", 8)
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
        Returns factory functions for creating controls and their event handlers.

        This function provides a dispatch table that maps (data_type, data_style) combinations
        to the appropriate control factory, handler factory, and special handling flag.

        The dispatch table has been optimized to minimize parameter passing:
        - Control factories receive choice dictionary and extract needed parameters internally
        - Handler factories receive control and choice, extracting obj/attr parameters internally
        - Lambda functions in the dispatch table use minimal parameter lists

        Args:
            data_type (type): Python type (bool, str, int, float, Length, Angle, Color, list)
            data_style (str): Style override for control type (None, "file", "slider", "combo", etc.)

        Returns:
            tuple: (factory_function, handler_factory, needs_special_handling)
                - factory_function: Creates the control widget
                - handler_factory: Creates event handler for the control
                - needs_special_handling: bool indicating if factory handles its own sizer addition

        Note:
            Lambda parameters in the dispatch table define the interface for when the lambdas
            are invoked by _create_control_using_dispatch, not references to variables in the
            current scope. All handler factories extract obj=choice["object"] and
            attr=choice["attr"] internally.
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
                lambda attr, control, obj, choice: self._make_generic_text_handler(control, choice),
                False,
            ),
            (int, None): (
                self._create_text_control,
                lambda attr, control, obj, choice: self._make_generic_text_handler(control, choice),
                False,
            ),
            (float, None): (
                self._create_text_control,
                lambda attr, control, obj, choice: self._make_generic_text_handler(control, choice),
                False,
            ),
            (float, "power"): (
                self._create_text_control,
                lambda attr, control, obj, choice: self._make_power_text_handler(control, choice),
                False,
            ),
            (float, "speed"): (
                self._create_text_control,
                lambda attr, control, obj, choice: self._make_speed_text_handler(control, choice),
                False,
            ),
            (str, "multiline"): (
                self._create_text_control,
                lambda attr, control, obj, choice: self._make_generic_multi_handler(control, choice),
                False,
            ),
            (str, "file"): (
                self._create_text_control,
                lambda attr, control, obj, choice: self._make_file_text_handler_with_button(control, choice),
                False,
            ),
            (Length, None): (
                self._create_text_control,
                lambda attr, control, obj, choice: self._make_length_text_handler(control, choice),
                False,
            ),
            (Angle, None): (
                self._create_text_control,
                lambda attr, control, obj, choice: self._make_angle_text_handler(control, choice),
                False,
            ),
            # Button-based controls
            (bool, "button"): (
                self._create_button_control,
                lambda attr, obj, choice: self._make_button_handler(choice),
                False,
            ),
            (bool, None): (
                self._create_button_control,
                lambda attr, control, obj, choice: self._make_checkbox_handler(control, choice),
                False,
            ),
            (str, "color"): (
                self._create_button_control,
                lambda attr, control, obj, choice: self._make_button_color_handler(control, choice),
                False,
            ),
            # Combo-based controls
            (str, "combo"): (
                self._create_combo_control,
                lambda attr, control, obj, choice: self._make_combo_text_handler(control, choice),
                False,
            ),
            (int, "combo"): (
                self._create_combo_control,
                lambda attr, control, obj, choice: self._make_combo_text_handler(control, choice),
                False,
            ),
            (float, "combo"): (
                self._create_combo_control,
                lambda attr, control, obj, choice: self._make_combo_text_handler(control, choice),
                False,
            ),
            (str, "combosmall"): (
                self._create_combo_control,
                lambda attr, control, obj, choice: self._make_combosmall_text_handler(control, choice),
                False,
            ),
            (int, "combosmall"): (
                self._create_combo_control,
                lambda attr, control, obj, choice: self._make_combosmall_text_handler(control, choice),
                False,
            ),
            (float, "combosmall"): (
                self._create_combo_control,
                lambda attr, control, obj, choice: self._make_combosmall_text_handler(control, choice),
                False,
            ),
            # Radio-based controls
            (str, "radio"): (
                self._create_radio_control,
                lambda attr, control, obj, choice: self._make_radio_select_handler(control, choice),
                False,
            ),
            (int, "radio"): (
                self._create_radio_control,
                lambda attr, control, obj, choice: self._make_radio_select_handler(control, choice),
                False,
            ),
            (int, "option"): (
                self._create_radio_control,
                lambda attr, control, obj, choice: self._make_combosmall_option_handler(control, choice),
                False,
            ),
            (str, "option"): (
                self._create_radio_control,
                lambda attr, control, obj, choice: self._make_combosmall_option_handler(control, choice),
                False,
            ),
            # Slider controls
            (int, "slider"): (
                self._create_slider_control,
                lambda attr, control, obj, choice: self._make_slider_handler(control, choice),
                False,
            ),
            (float, "slider"): (
                self._create_slider_control,
                lambda attr, control, obj, choice: self._make_slider_handler(control, choice),
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
        return dispatch_table.get(key, (None, None, False))

    def _create_control_using_dispatch(self, label, data, choice, obj):
        """
        Create a control using the dispatch table system.
        Returns (control, control_sizer, wants_listener) or None if unable to create.
        """
        attr = choice["attr"]
        data_style = choice.get("style")
        data_type = choice.get("type")
        additional_signal = self._get_additional_signals(choice)
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
                    self._create_chart_control(label, data, choice),
                    None,
                    True,
                )
            elif factory == "color_type":
                return (
                    self._create_color_type_control(label, data, choice),
                    None,
                    True,
                )
            return None, None, None

        # Handle regular controls
        if factory == self._create_binary_control:
            # Binary controls have a different signature
            controls, control_sizer = factory(label, data, choice, obj)
            return controls, control_sizer, False
        elif data_style == "file":
            # File controls need extra parameters - create without handler first
            control, control_sizer = factory(
                label,
                data,
                {**choice, "style": data_style},
                lambda: None,  # Dummy handler for now
            )
            # Now bind the real handler after control is created
            if handler_factory is not None:
                real_handler = handler_factory(attr, control, obj, choice)
                if hasattr(control, "Bind"):
                    control.Bind(wx.EVT_TEXT, real_handler)
            return control, control_sizer, True
        elif data_style == "option":
            # Option controls need choice list - create without handler first
            control, control_sizer = factory(
                label,
                data,
                choice,
                lambda: None,  # Dummy handler for now
            )
            # Now bind the real handler after control is created
            if handler_factory is not None:
                real_handler = handler_factory(
                    attr,
                    control,
                    obj,
                    choice,
                )
                if hasattr(control, "Bind"):
                    control.Bind(wx.EVT_COMBOBOX, real_handler)
            return control, control_sizer, True
        elif data_type == bool and data_style == "button":
            # Button-style bool controls have different handler signature
            control, control_sizer, wants_listener = factory(
                label,
                data,
                choice,
                lambda: None,  # Dummy handler for now
            )
            # Now bind the real handler after control is created
            if handler_factory is not None:
                real_handler = handler_factory(attr, obj, choice)
                if hasattr(control, "Bind"):
                    control.Bind(wx.EVT_BUTTON, real_handler)
            return control, control_sizer, wants_listener
        elif data_type == bool:
            # Regular bool controls
            control, control_sizer, wants_listener = factory(
                label,
                data,
                choice,
                lambda: None,  # Dummy handler for now
            )
            # Now bind the real handler after control is created
            if handler_factory is not None:
                real_handler = handler_factory(attr, control, obj, choice)
                if hasattr(control, "Bind"):
                    control.Bind(wx.EVT_CHECKBOX, real_handler)
            return control, control_sizer, wants_listener
        elif data_type == str and data_style == "color":
            # Color button controls
            control, control_sizer, wants_listener = factory(
                label,
                data,
                choice,
                lambda: None,  # Dummy handler for now
            )
            # Now bind the real handler after control is created
            if handler_factory is not None:
                real_handler = handler_factory(attr, control, obj, choice)
                if hasattr(control, "Bind"):
                    control.Bind(wx.EVT_BUTTON, real_handler)
            return control, control_sizer, wants_listener
        else:
            # Standard text, combo, radio, slider controls
            control, control_sizer = factory(
                label,
                data,
                {**choice, "style": data_style}
                if factory == self._create_text_control
                else choice,
                None,  # No handler for now
            )
            # Now bind the real handler after control is created
            if handler_factory is not None:
                real_handler = handler_factory(attr, control, obj, choice)
                # Bind appropriate event based on control type
                if hasattr(control, "Bind"):
                    if data_style in ("combo", "combosmall"):
                        has_display = "display" in choice and choice["display"] != choice.get("choices")
                        if has_display:
                            combo_handler = self._make_combosmall_option_handler(control, choice)
                        else:
                            combo_handler = real_handler
                        control.Bind(wx.EVT_COMBOBOX, combo_handler)
                        if not choice.get("exclusive", True):
                            control.Bind(wx.EVT_TEXT_ENTER, real_handler)
                            control.Bind(wx.EVT_KILL_FOCUS, real_handler)
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
        control = wxStaticText(self, label=label)
        return control

    def _create_chart_control(self, label, data, choice):
        """Create chart/list controls (placeholder - keep existing logic for now)."""
        # Extract obj from choice since obj = choice["object"]
        obj = choice["object"]
        # Extract additional_signal from choice
        additional_signal = self._get_additional_signals(choice)
        # This would contain the existing chart creation logic
        # For now, return None to indicate we should fall back to original logic
        return None

    def _create_color_type_control(self, label, data, choice):
        """Create Color type controls (placeholder - keep existing logic for now)."""
        # Extract obj from choice since obj = choice["object"]
        obj = choice["object"]
        # Extract additional_signal from choice
        additional_signal = self._get_additional_signals(choice)
        # This would contain the existing Color type creation logic
        # For now, return None to indicate we should fall back to original logic
        return None

    def _format_text_display_value(self, data, choice):
        """
        Formats data values for consistent display in text controls.

        This utility function handles the complex formatting requirements for different
        data types and control styles, ensuring consistent display across the interface.
        It is used by both control creation and control update functions.

        Key Features:
        - Length objects: Uses preferred units and appropriate decimal places
        - Power controls: Handles percentage/absolute mode conversions with callable flags
        - Speed controls: Handles per-minute/per-second mode conversions with callable flags
        - Angle objects: Proper formatting with appropriate precision
        - Basic types: String conversion with fallback handling

        Mode Support:
        - Power percentage mode: Converts 0-1000 absolute values to 0-100% display
        - Power absolute mode: Displays 0-1000 values directly
        - Speed per-minute mode: Converts per-second to per-minute for display
        - Speed per-second mode: Displays per-second values directly

        Args:
            data: The raw data value to format
            choice (dict): Choice configuration containing type, style, and mode flags

        Returns:
            str: Formatted string representation suitable for text control display
        """
        # Get type from choice, fallback to actual data type
        data_type = choice.get("type")

        if data_type == Length and hasattr(data, "preferred_length"):
            if not data._preferred_units:
                data._preferred_units = "mm"
            if not data._digits:
                if data._preferred_units in ("mm", "cm", "in", "inch"):
                    data._digits = 4
            return data.preferred_length
        elif data_type == Angle and hasattr(data, "angle"):
            # Format Angle objects with proper precision
            return str(data)
        elif choice.get("style") == "power":
            # Power controls: convert absolute value (0-1000) to display format
            percent_flag = choice.get("percent", False)
            percent_mode = percent_flag() if callable(percent_flag) else percent_flag
            if percent_mode:
                # Convert absolute value to percentage (0-1000 -> 0-100%)
                return str(float(data) / 10.0)
            else:
                # Display absolute value directly
                return str(data)
        elif choice.get("style") == "speed":
            # Speed controls: convert absolute value to display format
            per_minute_flag = choice.get("perminute", False)
            per_minute_mode = (
                per_minute_flag() if callable(per_minute_flag) else per_minute_flag
            )
            if per_minute_mode:
                # Convert absolute value to per minute (0-1000 -> 0-100%)
                return str(float(data) * 60.0)
            else:
                # Display absolute value directly
                return str(data)
        else:
            return str(data)

    def _setup_text_validation(self, control, data_type, choice):
        """Set up validation limits for text controls."""
        if data_type in (int, float):
            lower_range = choice.get("lower", None)
            upper_range = choice.get("upper", None)

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

    def _make_combo_text_handler(self, ctrl, choice):
        """Creates a handler for combo text controls."""
        param = choice["attr"]
        obj = choice["object"]
        dtype = choice.get("type", str)
        addsig = self._get_additional_signals(choice)

        def handle_combo_text_change(event):
            try:
                user_input = dtype(ctrl.GetValue())
                self._update_property_and_signal(obj, param, user_input, addsig)
            except (ValueError, TypeError):
                # Invalid input - could log this if needed, but don't crash the UI
                # For now, silently ignore invalid input to keep UI responsive
                pass

        return handle_combo_text_change

    def _make_button_handler(self, choice):
        """Creates a handler for button controls."""
        param = choice["attr"]
        obj = choice["object"]
        addsig = self._get_additional_signals(choice)

        def handle_button_click(event):
            # We just set it to True to kick it off
            self._update_property_and_signal(obj, param, True, addsig)

        return handle_button_click

    def _make_checkbox_handler(self, ctrl, choice):
        """
        Creates an event handler for checkbox controls.

        This handler automatically extracts the object and attribute from the choice
        dictionary and updates the property when the checkbox state changes.

        Args:
            ctrl (wx.CheckBox): The checkbox control
            choice (dict): Choice configuration containing 'object', 'attr', and optional 'signals'

        Returns:
            callable: Event handler function for wx.EVT_CHECKBOX events
        """
        param = choice["attr"]
        obj = choice["object"]
        addsig = self._get_additional_signals(choice)

        def handle_checkbox_change(event):
            is_checked = bool(ctrl.GetValue())
            self._update_property_and_signal(obj, param, is_checked, addsig)

        return handle_checkbox_change

    def _make_checkbox_bitcheck_handler(
        self, param, ctrl, obj, bit, addsig, enable_ctrl=None
    ):
        """Creates a handler for checkbox bit controls."""

        def handle_checkbox_bit_change(event):
            is_checked = ctrl.GetValue()
            if enable_ctrl is not None:
                enable_ctrl.Enable(is_checked)
            current = getattr(obj, param)
            if is_checked:
                current |= 1 << bit
            else:
                current &= ~(1 << bit)
            self._update_property_and_signal(obj, param, current, addsig)

        return handle_checkbox_bit_change

    def _make_generic_multi_handler(self, ctrl, choice):
        """Creates a handler for generic multi controls."""
        param = choice["attr"]
        obj = choice["object"]
        dtype = choice.get("type", str)
        addsig = self._get_additional_signals(choice)

        def handle_multi_text_change(event):
            v = ctrl.GetValue()
            try:
                dtype_v = dtype(v)
                self._update_property_and_signal(obj, param, dtype_v, addsig)
            except ValueError:
                # cannot cast to data_type, pass
                pass

        return handle_multi_text_change

    def _make_button_filename_handler(self, ctrl, wildcard, choice):
        """Creates a handler for file button controls."""
        param = choice["attr"]
        obj = choice["object"]
        label = choice.get("label", "Select File")
        addsig = self._get_additional_signals(choice)

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

    def _make_file_text_handler(self, ctrl, choice):
        """Creates a handler for file text controls."""
        param = choice["attr"]
        obj = choice["object"]
        dtype = choice.get("type", str)
        addsig = self._get_additional_signals(choice)

        def handle_file_text_change(event):
            v = ctrl.GetValue()
            try:
                dtype_v = dtype(v)
                self._update_property_and_signal(obj, param, dtype_v, addsig)
            except ValueError:
                # cannot cast to data_type, pass
                pass

        return handle_file_text_change

    def _make_file_text_handler_with_button(self, ctrl, choice):
        """Creates a handler for file text controls with button integration."""
        param = choice["attr"]
        obj = choice["object"]
        dtype = choice.get("type", str)
        addsig = self._get_additional_signals(choice)
        label = choice.get("label", "Select File")

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
                    ctrl,
                    wildcard,
                    choice,
                ),
            )

        return handle_file_text_change

    def _make_slider_handler(self, ctrl, choice):
        """Creates a handler for slider controls."""
        param = choice["attr"]
        obj = choice["object"]
        dtype = choice.get("type", int)
        addsig = self._get_additional_signals(choice)

        def handle_slider_change(event):
            v = dtype(ctrl.GetValue())
            self._update_property_and_signal(obj, param, v, addsig)

        return handle_slider_change

    def _make_radio_select_handler(self, ctrl, choice):
        """Creates a handler for radio selection controls."""
        param = choice["attr"]
        obj = choice["object"]
        dtype = choice.get("type", str)
        addsig = self._get_additional_signals(choice)

        def handle_radio_selection_change(event):
            if dtype == int:
                v = dtype(ctrl.GetSelection())
            else:
                # For non-int types, get the string value of the selected item
                selection = ctrl.GetSelection()
                if selection != wx.NOT_FOUND:
                    v = dtype(ctrl.GetString(selection))
                else:
                    v = dtype("")  # Fallback to empty string if no selection
            self._update_property_and_signal(obj, param, v, addsig)

        return handle_radio_selection_change

    def _make_combosmall_option_handler(self, ctrl, choice):
        """Creates a handler for small combo option controls."""
        param = choice["attr"]
        obj = choice["object"]
        dtype = choice.get("type", str)
        addsig = self._get_additional_signals(choice)

        def handle_combo_option_selection(event):
            try:
                selected_choice = ctrl._choice_list[ctrl.GetSelection()]
                converted_value = dtype(selected_choice)
                self._update_property_and_signal(obj, param, converted_value, addsig)
            except (ValueError, TypeError, IndexError):
                # Invalid selection or conversion - silently ignore to keep UI responsive
                pass

        return handle_combo_option_selection

    def _make_combosmall_text_handler(self, ctrl, choice):
        """Creates a handler for small combo text controls."""
        param = choice["attr"]
        obj = choice["object"]
        dtype = choice.get("type", str)
        addsig = self._get_additional_signals(choice)

        def handle_combo_text_entry(event):
            try:
                v = dtype(ctrl.GetValue())
                self._update_property_and_signal(obj, param, v, addsig)
            except (ValueError, TypeError):
                # Invalid input - silently ignore to keep UI responsive
                pass

        return handle_combo_text_entry

    def _make_button_color_handler(self, ctrl, choice):
        """Creates a handler for color button controls."""
        param = choice["attr"]
        obj = choice["object"]
        addsig = self._get_additional_signals(choice)

        def set_color(control, color: Color):
            control.SetLabel(str(color.hex))
            control.SetBackgroundColour(wx.Colour(swizzlecolor(color)))
            if Color.distance(color, Color("black")) > Color.distance(
                color, Color("white")
            ):
                control.SetForegroundColour(wx.BLACK)
            else:
                control.SetForegroundColour(wx.WHITE)
            control.color = color

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

    def _make_angle_text_handler(self, ctrl, choice):
        """Creates a handler for angle text controls."""
        param = choice["attr"]
        obj = choice["object"]
        addsig = self._get_additional_signals(choice)

        def handle_angle_text_change(event):
            try:
                v = Angle(ctrl.GetValue(), digits=5)
                data_v = v  # Store the Angle object, not string
                # Special comparison for angle objects using string representation to avoid TypeError
                current_value = getattr(obj, param)
                if str(current_value) != str(data_v):
                    setattr(obj, param, data_v)
                    self.context.signal(param, data_v, obj)
                    for _sig in addsig:
                        self.context.signal(_sig)
            except ValueError:
                # cannot cast to Angle, pass
                pass

        return handle_angle_text_change

    def _make_power_text_handler(self, ctrl, choice):
        """
        Creates a handler for power text controls that supports both absolute and percentage modes.

        Power controls can operate in two modes based on the 'percent' flag in the choice:
        - Percentage mode: User enters 0-100%, internally converts to 0-1000 absolute
        - Absolute mode: User enters 0-1000 directly

        The 'percent' flag can be a boolean or callable that returns a boolean.

        Args:
            ctrl (wx.TextCtrl): The text control
            choice (dict): Choice configuration containing 'object', 'attr', optional 'percent' flag, and 'signals'

        Returns:
            callable: Event handler function for text change events
        """
        param = choice["attr"]
        obj = choice["object"]
        addsig = self._get_additional_signals(choice)

        def handle_power_text_change(event):
            try:
                v = ctrl.GetValue()
                # Get the percent flag to determine conversion mode
                percent_flag = choice.get("percent", False)
                percent_mode = (
                    percent_flag() if callable(percent_flag) else percent_flag
                )

                if percent_mode:
                    # In percentage mode: user enters 0-100%, convert to 0-1000
                    percent_value = float(v)
                    if 0 <= percent_value <= 100:
                        absolute_value = (
                            percent_value * 10.0
                        )  # Convert % to absolute (0-1000)
                        self._update_property_and_signal(
                            obj, param, absolute_value, addsig
                        )
                else:
                    # In absolute mode: user enters 0-1000 directly
                    absolute_value = float(v)
                    if 0 <= absolute_value <= 1000:
                        self._update_property_and_signal(
                            obj, param, absolute_value, addsig
                        )
            except ValueError:
                # cannot cast to float, pass
                pass

        return handle_power_text_change

    def _make_speed_text_handler(self, ctrl, choice):
        """
        Creates a handler for speed text controls that supports both per-second and per-minute modes.

        Speed controls can operate in two modes based on the 'perminute' flag in the choice:
        - Per-minute mode: User enters per-minute values, internally converts to per-second
        - Per-second mode: User enters per-second values directly

        The 'perminute' flag can be a boolean or callable that returns a boolean.

        Args:
            ctrl (wx.TextCtrl): The text control
            choice (dict): Choice configuration containing 'object', 'attr', optional 'perminute' flag, and 'signals'

        Returns:
            callable: Event handler function for text change events
        """
        """Creates a handler for speed text controls that supports both absolute and per-minute modes."""
        param = choice["attr"]
        obj = choice["object"]
        addsig = self._get_additional_signals(choice)

        def handle_speed_text_change(event):
            try:
                v = ctrl.GetValue()
                # Get the perminute flag to determine conversion mode
                perminute_flag = choice.get("perminute", False)
                perminute_mode = (
                    perminute_flag() if callable(perminute_flag) else perminute_flag
                )

                absolute_value = float(v)
                if perminute_mode:
                    # In per-minute mode: user enters per-minute value, convert to per-second
                    if absolute_value >= 0:
                        absolute_value /= 60.0  # Convert per-minute to per-second
                else:
                    # In absolute mode: user enters per-second value directly
                    absolute_value = float(v)
                if absolute_value >= 0:
                    self._update_property_and_signal(obj, param, absolute_value, addsig)
            except ValueError:
                # cannot cast to float, pass
                pass

        return handle_speed_text_change

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
                        ctrl.SetItem(row_id, column_id, str(dataline.get(c_attr, "")))
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

    def _make_generic_text_handler(self, ctrl, choice):
        """Creates a handler for generic text controls."""
        param = choice["attr"]
        obj = choice["object"]
        dtype = choice.get("type", str)
        addsig = self._get_additional_signals(choice)

        def handle_generic_text_change(event):
            v = ctrl.GetValue()
            try:
                dtype_v = dtype(v)
                self._update_property_and_signal(obj, param, dtype_v, addsig)
            except ValueError:
                # cannot cast to data_type, pass
                pass

        return handle_generic_text_change

    def _make_length_text_handler(self, ctrl, choice):
        """Creates a handler for length text controls."""
        param = choice["attr"]
        obj = choice["object"]
        addsig = self._get_additional_signals(choice)

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

    def _validate_choice_for_crucial_information(self, choice):
        """Validate the choice configuration for crucial information."""
        if not choice.get("attr"):
            return False
        if not choice.get("object"):
            return False
        if not choice.get("type"):
            return False
        return True

    def _get_choice_data_and_type(self, c, obj):
        """Get data and data type for a choice."""
        attr = c["attr"]
        # get default value
        if hasattr(obj, attr):
            # Object has the attribute, use its value (can be None and that's fine)
            data = getattr(obj, attr)
        elif hasattr(obj, "settings") and attr in obj.settings:
            data = obj.settings[attr]
        elif "default" in c:
            # Use the provided default (can be None and that's fine)
            data = c.get("default")
        else:
            # No default provided for missing attribute - this is an error
            return None, None
        data_type = type(data)
        # Override with specified type if provided
        specified_type = c.get("type")
        if specified_type is not None:
            data_type = specified_type
        return data, data_type

    def _get_additional_signals(self, choice):
        """Extract additional signals from choice configuration."""
        additional_signal = []
        sig = choice.get("signals")
        if isinstance(sig, str):
            additional_signal.append(sig)
        elif isinstance(sig, (tuple, list)):
            for _sig in sig:
                additional_signal.append(_sig)
        return additional_signal

    def _setup_choice_control_properties(self, choice, control):
        """Set up control properties like tooltips, help, and conditional enabling."""
        if control is None:
            return

        # Extract obj from choice since obj = choice["object"]
        obj = choice["object"]

        # Handle binary controls (control is a list of checkboxes)
        if isinstance(control, list):
            for individual_control in control:
                self._setup_single_control_properties(choice, individual_control)
        else:
            self._setup_single_control_properties(choice, control)

    def _setup_single_control_properties(self, choice, control):
        """Set up properties for a single control (helper for _setup_control_properties)."""
        if control is None:
            return

        # Extract obj from choice since obj = choice["object"]
        obj = choice["object"]

        # Set tooltip
        tip = choice.get("tip")
        if tip and not self.context.root.setting(bool, "disable_tool_tips", False):
            control.SetToolTip(tip)

        # Set help text
        _help = choice.get("help")
        if _help and hasattr(control, "SetHelpText"):
            control.SetHelpText(_help)

        # Handle enabled state and conditional enabling using unified method
        enabled = choice.get("enabled", True)  # Default to True if not specified

        # If explicitly disabled, take precedence
        if enabled is False:
            if isinstance(control, list):
                for ctrl in control:
                    ctrl.Enable(False)
            else:
                control.Enable(False)
        else:
            # Use unified method for both conditional and regular enabling
            self._setup_control_enabling(choice, control, enabled)

    def _setup_update_listener(self, choice, control, obj, choice_list):
        """Set up update listener for control synchronization."""
        attr = choice["attr"]

        def on_update_listener(choice, ctrl, sourceobj):
            def listen_to_myself(origin, value, target=None, dict_key=None):
                if self.context.kernel.is_shutdown:
                    return

                if target is None or target is not sourceobj:
                    return

                data = None
                # data_style = choice.get("style")
                data_type = choice.get("type")

                if value is not None:
                    try:
                        data = data_type(value)
                    except ValueError:
                        pass
                    if data is None:
                        data = choice.get("default")
                if data is None:
                    return

                # Check if control still exists
                try:
                    dummy = hasattr(ctrl, "GetValue")
                except RuntimeError:
                    return

                # Update control based on data type and style
                self._update_control_value(ctrl, data, choice)

            return listen_to_myself

        update_listener = on_update_listener(choice, control, obj)
        self.listeners.append((attr, update_listener, obj))
        self.context.listen(attr, update_listener)

    def _update_control_value(self, ctrl, data, choice):
        """
        Updates a control's displayed value based on its type, style, and current data.

        This function handles the complex logic of converting internal data values to
        appropriate display formats for different control types. It supports:

        - Basic controls: checkboxes, text fields, sliders, combos
        - Special formatting: power controls (percentage/absolute), speed controls (per-minute/per-second)
        - Data type conversions: proper formatting for int, float, Length, Angle, Color types
        - Callable flags: supports dynamic percent/perminute flags that can change at runtime

        Recent improvements:
        - Uses _format_text_display_value for consistent text formatting
        - Properly handles callable percent and perminute flags
        - Improved Length object comparisons using length_mm attribute
        - Better error handling for type mismatches

        Args:
            ctrl: The UI control to update
            data: The internal data value to display
            choicelist: List of valid choices for combo controls
            choice (dict): Choice configuration containing type, style, and formatting flags
        """
        dtype = choice.get("type")
        dstyle = choice.get("style")
        choicelist = choice.get("choices", [])
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
            # print (f"Update combo control with data: {data} for attr: {choice.get('attr')}")
            if hasattr(ctrl, "_choice_list"):
                try:
                    idx = ctrl._choice_list.index(data)
                    if ctrl.GetSelection() != idx:
                        ctrl.SetSelection(idx)
                except ValueError:
                    # Value not found - extend lists
                    # Check if we are currently editing this control
                    has_focus = False
                    if ctrl.HasFocus():
                        has_focus = True
                    elif hasattr(ctrl, "GetTextCtrl") and ctrl.GetTextCtrl() and ctrl.GetTextCtrl().HasFocus():
                        has_focus = True
                    
                    # If user is typing and the value matches what they typed, don't update the list
                    if has_focus and ctrl.GetValue() == str(data):
                        return

                    new_val = str(data)
                    # Check if the string value is already in the control's list
                    found_idx = ctrl.FindString(new_val)
                    if found_idx != wx.NOT_FOUND:
                        # It's already in the list, just select it
                        ctrl.SetSelection(found_idx)
                    else:
                        # Not in list, insert it
                        ctrl.Insert(new_val, 0)
                        ctrl._choice_list.insert(0, data)
                        ctrl.SetSelection(0)
            elif dtype == str:
                ctrl.SetValue(str(data))
            else:
                least = None
                if choicelist is None:
                    choicelist = []
                for entry in choicelist:
                    if least is None:
                        least = entry
                    else:
                        if abs(dtype(entry) - data) < abs(dtype(least) - data):
                            least = entry
                if least is not None:
                    ctrl.SetValue(str(least))
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
                current_display_value = ctrl.GetValue()
                # Use the same formatting logic as _format_text_display_value
                new_display_value = self._format_text_display_value(data, choice)
                if current_display_value != new_display_value:
                    ctrl.SetValue(new_display_value)
        elif dtype == Length:
            try:
                current_length = Length(ctrl.GetValue())
                # Compare Length values using their internal representation
                if hasattr(data, "length_mm") and hasattr(current_length, "length_mm"):
                    if data.length_mm != current_length.length_mm:
                        update_needed = True
                else:
                    # Fallback comparison as string
                    if str(data) != str(current_length):
                        update_needed = True
            except (ValueError, TypeError):
                update_needed = True

            if update_needed:
                # Use consistent formatting for Length values
                display_value = self._format_text_display_value(data, choice)
                ctrl.SetValue(display_value)
        elif dtype == Angle:
            try:
                current_angle_str = ctrl.GetValue()
                # Compare string representations to avoid comparison issues
                if current_angle_str != str(data):
                    ctrl.SetValue(str(data))
            except (ValueError, TypeError):
                # Fallback to simple string update
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

    def _setup_control_enabling(self, choice, control, default_enabled=True):
        """
        Unified method to set up control enabling with optional conditional logic.

        Handles both simple enabled/disabled state and complex conditional enabling based on:
        - Boolean attribute check (2-tuple): Enable if attribute is truthy
        - Value equality check (3-tuple): Enable if attribute equals specified value
        - Multiple value check (3-tuple with list): Enable if attribute matches any value
        - Range check (4-tuple): Enable if attribute is between min and max values

        Args:
            choice (dict): Choice configuration containing "conditional" key if needed
            control: The control(s) to enable/disable (can be list for binary controls)
            default_enabled (bool): Default enabled state if no conditional logic
        """
        # Check if conditional enabling is needed
        if "conditional" not in choice:
            # No conditional logic, just use the default enabled value
            if isinstance(control, list):
                for ctrl in control:
                    ctrl.Enable(default_enabled)
            else:
                control.Enable(default_enabled)
            return

        conditional = choice.get("conditional")
        if conditional is None or len(conditional) < 2:
            # Invalid conditional tuple
            if isinstance(control, list):
                for ctrl in control:
                    ctrl.Enable(default_enabled)
            else:
                control.Enable(default_enabled)
            return

        cond_obj, cond_attr = conditional[0], conditional[1]
        equals_value = conditional[2] if len(conditional) > 2 else None
        range_max = conditional[3] if len(conditional) > 3 else None

        # Determine initial enabled state based on conditional logic
        try:
            current_value = getattr(cond_obj, cond_attr)
            if range_max is not None and equals_value is not None:
                # Range check: value should be between equals_value (min) and range_max
                conditional_enabled = equals_value <= current_value <= range_max
            elif equals_value is not None:
                # Value equality check (including list of values)
                if isinstance(equals_value, (list, tuple)) and not isinstance(equals_value, str):
                    conditional_enabled = any(current_value == v for v in equals_value)
                else:
                    conditional_enabled = current_value == equals_value
            else:
                # Boolean attribute check
                conditional_enabled = bool(current_value)
        except (AttributeError, TypeError):
            # If we can't get the value, default to disabled
            conditional_enabled = False

        # Apply initial state
        if isinstance(control, list):
            for ctrl in control:
                ctrl.Enable(conditional_enabled)
        else:
            control.Enable(conditional_enabled)

        # Set up listener for dynamic updates
        self._register_conditional_listener(choice, control, cond_obj, cond_attr, equals_value, range_max)

    def _register_conditional_listener(self, choice, control, cond_obj, cond_attr, equals_value, range_max):
        """
        Register a listener for conditional enabling that updates the control when the condition changes.

        Args:
            choice (dict): Choice configuration
            control: The control(s) to enable/disable
            cond_obj: The object containing the condition attribute
            cond_attr (str): The attribute name to listen to
            equals_value: The value(s) to compare for equality (None for boolean check)
            range_max: The maximum value for range check (None if not a range check)
        """
        def on_conditional_change(origin, value, target=None):
            def enable_control(enable):
                if isinstance(control, list):
                    for ctrl in control:
                        ctrl.Enable(enable)
                else:
                    control.Enable(enable)
                if self.context.kernel.is_shutdown:
                    return

            if target is None or target is not sourceobj:
                return

            if value is None:
                enable_control(False)
                return
            try:
                if range_max is not None and equals_value is not None:
                    # Range check
                    enable = equals_value <= value <= range_max
                elif equals_value is not None:
                    # Value equality check (including list of values)
                    if isinstance(equals_value, (list, tuple)) and not isinstance(equals_value, str):
                        enable = any(value == v for v in equals_value)
                    else:
                        enable = value == equals_value
                else:
                    # Boolean check
                    enable = bool(value)
                
                enable_control(enable)
            except (TypeError, ValueError, AttributeError):
                # If comparison fails, disable control
                enable_control(False)

        # Register the listener with the context system
        if self.context:
            sourceobj = cond_obj    
            self.context.listen(cond_attr, on_conditional_change)
            self.listeners.append((cond_attr, on_conditional_change, cond_obj))

    def _setup_conditional_enabling(self, choice, control):
        """
        Legacy wrapper for backward compatibility. Use _setup_control_enabling instead.
        
        Set up conditional enabling for a control based on another control's value.

        Args:
            choice: The choice control that drives the enabling condition
            control: The control to be enabled/disabled
        """
        self._setup_control_enabling(choice, control, default_enabled=True)

    def pane_hide(self):
        # print (f"hide called: {len(self.listeners)}")
        if len(self.listeners):
            for attr, listener, obj in self.listeners:
                self.context.unlisten(attr, listener)
                # Don't delete listener or clear list - keep them for restoration

    def pane_show(self):
        # print ("show called")
        # Reestablish all listeners that were stored
        if len(self.listeners) and self.context:
            for attr, listener, obj in self.listeners:
                self.context.listen(attr, listener)
