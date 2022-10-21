# MeerK40t
MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed open-source laser cutting software.

## Primary Goals
* Provide users with high quality laser control software.
* Provide developers with a highly extensible platform to help further their own ideas, and provide novel work to the laser community at large.

## Running
MeerK40t is written in Python and precompiled versions are [available for download](https://github.com/meerk40t/meerk40t/releases) for Windows, Mac OSX, Linux and Raspberry Pi. Due note this sometimes will give false postitives for various viruses (especially since Meerk40t isn't signed).

Alternatively you can run MeerK40t directly from Python. `pip install meerk40t[all]` with python installed will usually be sufficient. Then merely run `meerk40t` at the command line.

### GUI
![meerk40t8](https://user-images.githubusercontent.com/3302478/196283699-745d0616-5e74-49b3-ba95-f4902061584b.png)

The wxMeerK40t is the GUI and is written in wxPython. We use AUI to allow highly you to have a very highly configurable UI. We can easily add panes and tools and there are quite a few available already.

### Command Line Interface

Meerk40t has an advanced internal console system allowing access to most parts of the code with various commands. It also provides a command line interface which should allow you to automate any processes.

## Drivers

Meerk40t provides a variety of drivers with an extensible framework to provide support for other new laser devices. The code was written with the myriad of possibilities for different software in mind. For example, it may be essential that GRBL be able to reset an alarm or notify the user of particular error codes. The configuration for GRBL is not the same for the configuration of other laser control drivers. With this in mind, Meerk40t can radically change how and when it works


### Supported devices
*   M2-Nano
*   Moshiboard
*   GRBL
*   Fibre Lasers based on the JCZ controllers (still experimental)
*   Ruida-Emulation (Middleman between Lightburn and K40)

### Lihuiyu M2-Nano
For the Lihuiyu (stock driver), Meerk40t supports both the windows and libusb connection methods, making it compatible with Whisperer and with the original Chinese software. So MeerK40t can usually run alongside these other pieces of software interchangeably.

### Galvo LMC

Meerk40t supports controlling galvo as well as gantry lasers with open source support.

### Moshiboard

The support for old moshiboards makes meerk40t the only known software opensource software that controls moshiboards.

### GRBL

GRBL is itself open source and the various interfaces with the board should be quite well understood.

## Support
The primary source for help and documentation is the [MeerK40t Wiki - please click here](https://github.com/meerk40t/meerk40t/wiki).

If you have a bug, feature request, or other issue raise it here. These are likely to be resolved. Squeaky wheels get the grease.
https://github.com/meerk40t/meerk40t/issues

If you need additional support, please research/ask on:

*   [Facebook](https://www.facebook.com/groups/716000085655097/)
*   [Maker Forums](https://forum.makerforums.info/t/about-the-meerk40t-category/79660)
*   [Youtube - David Olsen's channel](https://www.youtube.com/channel/UCsAUV23O2FyKxC0HN7nkAQQ)
*   [Discord](https://discord.gg/vkDD3HdQq6)

## Assisting the Project

Open source projects live and die with their support. There are a lots of ways to help the project. There are also a lot of ways the project should help you. 
*   Code
*   Provide Translations in other languages.
*   Design ( Good design instincts, smooth out the rough edges)
*   Compile/Testers
*   Beta testers
*   Make helpful support content
*   Make guides ("How to setup cameras?", etc)
*   Bounce ideas around

