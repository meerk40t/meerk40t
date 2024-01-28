# GUI

![meerk40t](https://user-images.githubusercontent.com/3302478/132944749-c40ad085-76ed-4236-b7bb-e97abdc578bf.png)

The wxMeerK40t is the GUI and is written in wxPython, using AUI to perform advanced user interface commands.

The GUI modules all require wxPython and deal with the graphical interactions between the user and the software. The
general rule is that the GUI should not do work that cannot be done through console command operations. In many cases
the GUI interactions translate specific actions into console commands. These also rely heavily on the kernel and various
kernel interactions to view channels opened within the kernel, receive signals from various events, and visualize data
stored within the broader kernel ecosystem.

As a rule, the GUI should never be a requirement, and replacing the GUI should not be significantly harder than writing
another GUI.
