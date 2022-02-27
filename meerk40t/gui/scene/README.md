# Scene

The scene provide for the interactions within visual space of dynamically drawn widgets. The widgets work independently of each other and can control their hit boxes, deal with events and draw themselves.

This is similar to other widget/scene UI visual libraries and includes affine transformations, hit chaining, and context specific interactions. It is intended to work correctly with wxPython drawing spaces and provides a ScenePanel to be drawn upon.

The scene contains two primary levels defined in the scene space widget these are the scene widgets which are affected by the core matrix of the drawing code. And the interface widgets which are drawn 1:1 within the interface space.
