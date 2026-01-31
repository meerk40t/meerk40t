# Property Panels

Property panels are panels which are loaded for particular node types, sometimes several for the same node type. These
are registered in the `property/{class_name}/.*` for the given node. The panels themselves are rendered in the
PropertyWindow which is a standard MWindow type. These are typically for all the major node types and anything else that
needs additional properties. In addition to these property panels some can be registered by particular services. For
example the `operationpropertymain.py` contains all the main windows for different operation types, but in addition to
this certain driver can contain additional operations, such as M2Nano driver which will include things like `d_ratio`
which is specific to that type of controller card but also needs to be available as a per-operation attribute.
