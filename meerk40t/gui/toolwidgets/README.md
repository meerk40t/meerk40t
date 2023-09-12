# Tool Widgets

The toolwidgets provide tool interactions within the main wxScene. These are registered in the `tool/<widget>` namespace
in the kernel and preempts other widgets to control take over the controls for the scene. These widgets are added as
children to the toolcontainer widget which delegates to its selected tool.