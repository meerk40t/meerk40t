# Scene

The scene provide for the interactions within visual space of dynamically drawn widgets. The widgets work independently of each other and independently control their hit boxes, deal with events, and draw themselves.

This is similar to other widget/scene UI visual libraries and includes affine transformations, hit chaining, event processing, and context specific interactions. It is intended to work correctly with wxPython drawing spaces and provides a ScenePanel to be drawn upon.

The scene contains two primary layers defined in the `SceneSpaceWidget` these are the scene widgets which are affected by the root matrix of the scene. And the interface widgets which are drawn at 1:1 within the interface space. The interface widgets are intended to be widgets occupying the window you are using to view the scene and the scene widgets are the matrix-modified space we are interacting with. 

The scene is organized into a tree with the root widget being a SceneSpaceWidget for the scene and all other widgets located somewhere in the tree. When events affecting the structure of the tree occur the widgets are notified through notify events. These are intended to perform actions when child widgets are changed by the code or when signals are broadcast to all widgets.


# Widget

The widgets provide their coordinates as to the space they officially occupy. They call set `all=True` which is to say they occupy all space.

If an event in the scene occurs it checks coordinates to find the list of widgets which could have been hit by that event. This is the list of `hittable_elements`  and is processed to see whether the widget was hit by this event. Namely, a check is made as to the space the event occurred contained the widget, and then a check is made on the widget's `hit()` function to return whether it was hit `HITCHAIN_HIT` or should delegate `HITCHAIN_DELEGATE` this hit. Widgets can also delegate and hit `HITCHAIN_DELEGATE_AND_HIT` or hit and delegate `HITCHAIN_HIT_AND_DELEGATE`.

If you only delegate then the widget does not appear in the hitchain. This widget can be drawn but will not be offered events. If it is hit, then this is the widget you wanted and the one that should get all event in the event chain. If we delegate and hit, this widget is placed below all of its children. For example the `SpaceSceneWidget` which creates the interface and scene levels of view is a `HITCHAIN_DELEGATE_AND_HIT` because anything within it should have first choice of accepting events but if no events are caught it will use them to manipulate the scene with zooms, pans and other scene level changes.

Events are processed for hit widgets. Events are often processed as a chain of events typically started with a mouse-down of some variety and end with a mouse-up and some events have happened between those points.

Event processing  requires a response, which is either consume, abort, chain, or drop. If an event is consumed by this widget nothing else in the hitchain is processed and this widget has dealt with the event and no further processing will be done. If we abort, then the entire sequence of events is discontinued, no future events will be processed from that event chain for any widgets. If we chain then we accepted this event but pass it down to the next widgets in the hitchain to also process it. This allows elements which are above other elements to still allow certain events to be processed anyway. This also means that some events could be consumed while others are chained giving a widget an incomplete view of the events in the event chain. The final event is drop, which means remove this widget from the hitchain. While it did respond that it was hit, it no longer wants any involvement with this chain of events. This is useful if the original check for hit didn't have sufficient information to know if this should be processed or not and to morph the initial hit widget into a delegate after the fact.

All widgets draw themselves. This drawing occurs within the local widget's current matrix. And is done in the process_draw() for the widget. Even if the widget doesn't interact with the scene it can still draw on the scene. For example a widget that provides a guide in the interface space or a grid within the scene.

