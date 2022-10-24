import functools


def tree_calc(value_name, calc_func):
    def decor(func):
        func.calcs.append((value_name, calc_func))
        return func

    return decor


def tree_values(value_name, values):
    def decor(func):
        func.value_name = value_name
        func.values = values
        return func

    return decor


def tree_iterate(value_name, start, stop, step=1):
    def decor(func):
        func.value_name = value_name
        func.values = range(start, stop, step)
        return func

    return decor


def tree_radio(radio_function):
    def decor(func):
        func.radio = radio_function
        return func

    return decor


def tree_check(check_function):
    def decor(func):
        func.check = check_function
        return func

    return decor


def tree_submenu(submenu):
    def decor(func):
        func.submenu = submenu
        return func

    return decor


def tree_prompt(attr, prompt, data_type=str):
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
    def decor(func):
        func.conditionals.append(conditional)
        return func

    return decor


def tree_conditional_try(conditional):
    def decor(func):
        func.try_conditionals.append(conditional)
        return func

    return decor


def tree_reference(node):
    def decor(func):
        func.reference = node
        return func

    return decor


def tree_separator_after():
    def decor(func):
        func.separate_after = True
        return func

    return decor


def tree_separator_before():
    def decor(func):
        func.separate_before = True
        return func

    return decor


def tree_operation(
    registration, name, node_type=None, help=None, enable=True, **kwargs
):
    def decorator(func):
        @functools.wraps(func)
        def inner(node, **ik):
            returned = func(node, **ik, **kwargs)
            return returned

        if isinstance(node_type, tuple):
            ins = node_type
        else:
            ins = (node_type,)

        # inner.long_help = func.__doc__
        inner.help = help
        inner.node_type = ins
        inner.name = name
        inner.radio = None
        inner.submenu = None
        inner.reference = None
        inner.separate_after = False
        inner.separate_before = False
        inner.conditionals = list()
        inner.try_conditionals = list()
        inner.user_prompt = list()
        inner.calcs = list()
        inner.values = [0]
        inner.enabled = enable
        registered_name = inner.__name__

        for _in in ins:
            p = f"tree/{_in}/{registered_name}"
            if p in registration._registered:
                raise NameError(f"A function of this name was already registered: {p}")
            registration.register(p, inner)
        return inner

    return decorator


def get_tree_operation(registration):
    def treeop(name, node_type=None, help=None, enable=True, **kwargs):
        return tree_operation(
            registration, name, node_type=node_type, help=help, enable=enable, **kwargs
        )

    return treeop


def tree_operations_for_node(registration, node):
    for func, m, sname in registration.find("tree", node.type, ".*"):
        reject = False
        for cond in func.conditionals:
            if not cond(node):
                reject = True
                break
        if reject:
            continue
        for cond in func.try_conditionals:
            try:
                if not cond(node):
                    reject = True
                    break
            except Exception:
                continue
        if reject:
            continue
        func_dict = {
            "name": str(node.name)
            if (hasattr(node, "name") and node.name is not None)
            else str(node.label),
            "label": str(node.name)
            if (hasattr(node, "name") and node.name is not None)
            else str(node.label),
        }

        iterator = func.values
        if iterator is None:
            iterator = [0]
        else:
            try:
                iterator = list(iterator())
            except TypeError:
                pass
        for i, value in enumerate(iterator):
            func_dict["iterator"] = i
            func_dict["value"] = value
            try:
                func_dict[func.value_name] = value
            except AttributeError:
                pass

            for calc in func.calcs:
                key, c = calc
                value = c(value)
                func_dict[key] = value
            if func.radio is not None:
                try:
                    func.radio_state = func.radio(node, **func_dict)
                except:
                    func.radio_state = False
            else:
                func.radio_state = None
            if hasattr(func, "check") and func.check is not None:
                try:
                    func.check_state = func.check(node, **func_dict)
                except:
                    func.check_state = False
            else:
                func.check_state = None
            name = func.name.format_map(func_dict)
            func.func_dict = func_dict
            func.real_name = name
            yield func


def get_tree_operation_for_node(registration):
    def treeop(node):
        return tree_operations_for_node(registration, node)

    return treeop