"""
Tree Operation decorators help define the Tree Operations found mostly in element_treeop class. We create dynamic menus
and thus need to classify the various different methods to access a node, without actually creating giant and
redundant code for each command on each code type.

These functions are overwhelmingly decorators. The `tree_operation` decorator sets the default values for the function
and all the other decorators set those values.

This data is expected to be called in a menu, but can be called via the console or through other methods.
"""

import functools


def tree_calc(value_name, calc_func):
    """
    Decorate a calc function.

    A calculator function will be called for each `value` in values or iterator, and will be permitted to calculate
    some dynamic value from that function.

    @param value_name:
    @param calc_func:
    @return:
    """
    def decor(func):
        func.calcs.append((value_name, calc_func))
        return func

    return decor


def tree_values(value_name, values):
    """
    Append explicit list of values and value_name to the function.
    @param value_name:
    @param values:
    @return:
    """
    def decor(func):
        func.value_name = value_name
        func.values = values
        return func

    return decor


def tree_iterate(value_name, start, stop, step=1):
    """
    Append range list of values to function.

    @param value_name:
    @param start: Start value
    @param stop: stop value
    @param step: step amount
    @return:
    """
    def decor(func):
        func.value_name = value_name
        func.values = range(start, stop, step)
        return func

    return decor


def tree_radio(radio_function):
    """
    Append radio value to the operation for menus.

    @param radio_function:
    @return:
    """
    def decor(func):
        func.radio = radio_function
        return func

    return decor


def tree_check(check_function):
    """
    Append checkbox function to the operation for menus.

    @param check_function:
    @return:
    """
    def decor(func):
        func.check = check_function
        return func

    return decor


def tree_submenu(submenu):
    """
    Decorate a submenu on to the operation for menus.

    @param submenu: submenu to use.
    @return:
    """
    def decor(func):
        func.submenu = submenu
        return func

    return decor


def tree_prompt(attr, prompt, data_type=str):
    """
    Decorate a tree_prompt for the operations for menu, this function will request this information from the user
    before calling the tree_operation function with the given attr.

    @param attr:
    @param prompt:
    @param data_type:
    @return:
    """
    def decor(func):
        func.user_prompt.append(
            {
                "attr": attr,
                "prompt": prompt,
                "type": data_type,
            }
        )
        return func

    return decor


def tree_conditional(conditional):
    """
    Decorate a conditional to the operation for menus.

    Each conditional decorated to a function must pass for this menu item to show to the user.

    @param conditional:
    @return:
    """
    def decor(func):
        func.conditionals.append(conditional)
        return func

    return decor


def tree_conditional_try(conditional):
    """
    Decorate a try conditional on this operation for menu.

    Try conditionals will not crash for the node, and can query states that may not exist.

    @param conditional:
    @return:
    """
    def decor(func):
        func.try_conditionals.append(conditional)
        return func

    return decor


def tree_reference(node):
    """
    Decorate a reference to on the tree.
    @param node:
    @return:
    """
    def decor(func):
        func.reference = node
        return func

    return decor


def tree_separator_after():
    """
    Decorator to flag this operation as having a separator after it.

    @return:
    """
    def decor(func):
        func.separate_after = True
        return func

    return decor


def tree_separator_before():
    """
    Decorator to flag this operation as having a separator before it.

    @return:
    """
    def decor(func):
        func.separate_before = True
        return func

    return decor


def tree_operation(
    registration, name, node_type=None, help=None, enable=True, **kwargs
):
    """
    Main tree registration decorator. Registers the tree operation with the given help and set the enabled state.

    @param registration: This is either a service or a kernel.
    @param name: Name of the tree operation being registered (required)
    @param node_type: types of node this operation applies to.
    @param help: Help data to be displayed in menu or other help information locations.
    @param enable: Should this be enabled.
    @param kwargs: Any remaining keywords.
    @return:
    """
    def decorator(func):
        @functools.wraps(func)
        def inner(node, **ik):
            """
            Wrapped inner function executes the operation.

            @param node:
            @param ik:
            @return:
            """
            returned = func(node, **ik, **kwargs)
            return returned

        if isinstance(node_type, tuple):
            ins = node_type
        else:
            ins = (node_type,)

        # inner.long_help = func.__doc__
        inner.help = help

        # Tuple of node types this applies to.
        inner.node_type = ins

        # Name of function.
        inner.name = name

        # attached radio commands.
        inner.radio = None

        # submenu of the operation
        inner.submenu = None

        # Optional information
        inner.reference = None

        # Should add a separator after this function.
        inner.separate_after = False

        # Should add a separator before this function.
        inner.separate_before = False

        # Conditionals required to be true to enable function.
        inner.conditionals = list()

        # Conditional attempted in a try-execute block (these may throw errors)
        inner.try_conditionals = list()

        # Prompt the user to discover this information.
        inner.user_prompt = list()

        # Calculations for the values.
        inner.calcs = list()

        # List of accepted values.
        inner.values = [0]

        # Function enabled/disabled
        inner.enabled = enable

        # Registered name is the same as the function name this is attached to.
        registered_name = inner.__name__

        for _in in ins:
            # Register tree/node/name for each node within the registration.
            p = f"tree/{_in}/{registered_name}"
            if p in registration._registered:
                # We used the name so we may not have duplicate tree operations with the same name.
                raise NameError(f"A function of this name was already registered: {p}")
            registration.register(p, inner)
        return inner

    # Return the entire decorator.
    return decorator


def get_tree_operation(registration):
    """
    Returns a tree op for all the function calls with the registration already set.

    @param registration:
    @return:
    """
    def treeop(name, node_type=None, help=None, enable=True, **kwargs):
        return tree_operation(
            registration, name, node_type=node_type, help=help, enable=enable, **kwargs
        )

    return treeop


def tree_operations_for_node(registration, node):
    """
    Generator to produce all tree operations for the given node.

    @param registration: kernel or service on which to find these operations
    @param node:
    @return:
    """
    if node.type is None:
        return
    for func, m, sname in registration.find("tree", node.type, ".*"):
        reject = False
        for cond in func.conditionals:
            # Do not provide this if the conditionals fail.
            if not cond(node):
                reject = True
                break
        if reject:
            continue
        for cond in func.try_conditionals:
            # Do not provide this if the try conditional fail. Crash is a pass.
            try:
                if not cond(node):
                    reject = True
                    break
            except Exception:
                continue
        if reject:
            continue
        node_name = (
            str(node.name)
            if (hasattr(node, "name") and node.name is not None)
            else str(node.label)
        )
        node_label = (
            str(node.name)
            if (hasattr(node, "name") and node.name is not None)
            else str(node.label)
        )

        def unescaped(filename):
            """
            Provide unescaped name/label.
            OS dependency is moot.

            @param filename:
            @return:
            """
            from platform import system

            OS_NAME = system()
            if OS_NAME == "Windows":
                newstring = filename.replace("&", "&&")
            else:
                newstring = filename.replace("&", "&&")
            return newstring

        # Create the operation calling dictionary.
        func_dict = {
            "name": unescaped(node_name),
            "label": unescaped(node_label),
        }

        # @tree_values / @tree_iterate values to be appended to function dictionary.
        iterator = func.values
        if iterator is None:
            iterator = [0]
        else:
            try:
                iterator = list(iterator())
            except TypeError:
                pass

        for i, value in enumerate(iterator):
            # Every value in the func.values gets an operation for the node.
            func_dict["iterator"] = i
            func_dict["value"] = value
            try:
                func_dict[func.value_name] = value
            except AttributeError:
                pass

            for calc in func.calcs:
                # Calculators are done called for the given value, result is set in the call dictionary.
                key, c = calc
                value = c(value)
                func_dict[key] = value
            if func.radio is not None:
                # Sets the radio state by the radio function.
                try:
                    func.radio_state = func.radio(node, **func_dict)
                except:
                    func.radio_state = False
            else:
                func.radio_state = None

            if hasattr(func, "check") and func.check is not None:
                # Sets the checkbox state by the checkbox function.
                try:
                    func.check_state = func.check(node, **func_dict)
                except:
                    func.check_state = False
            else:
                func.check_state = None

            # Function name is formatted such that any {} format brackets are filled with their values.
            name = func.name.format_map(func_dict)

            # Set the function and real name and provide it to the caller.
            func.func_dict = func_dict
            func.real_name = name
            yield func


def get_tree_operation_for_node(registration):
    """
    Provide treeops for the given registration without needing to provide the registration each time, only the node.
    @param registration:
    @return:
    """
    def treeop(node):
        return tree_operations_for_node(registration, node)

    return treeop
