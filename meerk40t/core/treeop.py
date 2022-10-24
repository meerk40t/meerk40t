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
