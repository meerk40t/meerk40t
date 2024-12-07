# Welcome to MeerK40t!
MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed open-source laser cutting software.

The primary goals of this software is simple:


* Provide users with high quality laser control software.
* Provide developers with a highly extensible platform to help further their own ideas, and provide novel work to the laser community at large.

## Getting started
To get up and running, simply download Meerk40t from [here](https://github.com/meerk40t/meerk40t/releases) for your specific platform. (Windows, Mac OSX, Linux, and by extension, Raspberry Pi).

<details>
<summary>Release Versions (Just use the latest)</summary>


> * 0.9 - Active - New features and some underlying architectural changes. Try the latest released version: [0.9.5.1](https://github.com/meerk40t/meerk40t/releases#latest)
> * 0.8 - Maintenance - may receive critical bugfixes but no more new features, latest version: [0.8.12](https://github.com/meerk40t/meerk40t/releases/tag/0.8.12000) (Oct 17, 2023)
> * 0.7 - Discontinued - K40 support only (including ruidacontrol emulator for 3rd party lasersoftware integration), latest version [0.7.10](https://github.com/meerk40t/meerk40t/releases/tag/0.7.10000) (June 13, 2023)
> * 0.6 - Discontinued - K40 support only, latest version: [0.6.24](https://github.com/meerk40t/meerk40t/releases/tag/0.6.24) (Oct 11, 2021)


</details>

### Command Line Interface

Meerk40t has an advanced internal console system allowing access to most parts of the code with various commands. It also provides a command line interface which should allow you to automate any processes. To learn more, download a version of Meerk40t for your platform, and execute it in a terminal with the ``--help`` argument to get a list of options.

## Compiling from source

Alternatively you can run MeerK40t directly from Python. `pip install meerk40t[all]` with python installed will usually be sufficient. Then merely run `meerk40t` at the command line.

See [Install: Source wiki page](https://github.com/meerk40t/meerk40t/wiki/Install:-Source)

The wxMeerK40t is the GUI and is written in wxPython. We use AUI to allow to have a very highly configurable UI. We can easily add panes and tools and there are quite a few available already.

## Screenshots
![grafik](https://github.com/user-attachments/assets/e56135a2-7b1f-44be-9761-b92931e300f6)

## Drivers

Meerk40t provides a variety of drivers with an extensible framework to provide support for other new laser devices. The code was written with the myriad of possibilities for different software in mind. For example, it may be essential that GRBL be able to reset an alarm or notify the user of particular error codes. The configuration for GRBL is not the same for the configuration of other laser control drivers. With this in mind, Meerk40t can radically change how and when it works


### Supported devices
*   Lihuiyu M2/M3-Nano (aka K40 lasers)
*   Any GRBL device (Atomstack, Creality, Longer, Ortur etc...)
*   Ezcad2-compatible JCZ controllers galvo lasers
*   Moshiboard
*   NewlyDraw System 8.1 Lasers
*   Ruida-Emulation (Middleman between Lightburn and K40)

<details>
<summary>More device support info</summary>

### Lihuiyu M2-Nano/M3-Nano
For the Lihuiyu (stock driver), Meerk40t supports both the windows and libusb connection methods, making it compatible with Whisperer and with the original Chinese software. So MeerK40t can usually run alongside these other pieces of software interchangeably.

### GRBL

GRBL is itself open source and the various interfaces with the board should be quite well understood.

### EZCAD2-Compatible Galvo LMC

Meerk40t supports controlling galvo as well as gantry lasers with open source support.

### Moshiboard

The support for old moshiboards makes meerk40t the only known opensource software that controls moshiboards.

### System 8.1 Lasers (NewlyDraw)

HPGL-modified laser systems produced under many different company names

</details>

## Support
The primary source for help and documentation is the [MeerK40t Wiki - please click here](https://github.com/meerk40t/meerk40t/wiki).

If you have a bug, feature request, or other issue raise it here. These are likely to be resolved. Squeaky wheels get the grease.
https://github.com/meerk40t/meerk40t/issues

If you need additional support, please research/ask on:

*   [Facebook](https://www.facebook.com/groups/716000085655097/)
*   [Maker Forums](https://forum.makerforums.info/t/about-the-meerk40t-category/79660)
*   [YouTube - David Olsen's channel](https://www.youtube.com/channel/UCsAUV23O2FyKxC0HN7nkAQQ)
*   [YouTube - Some instruction videos](https://www.youtube.com/channel/UCMN9gGvpacxZINPZCSOecaQ)
*   [Discord](https://discord.gg/vkDD3HdQq6)

## Assisting the Project

Open source projects live and die with their support. There are a lots of ways to help the project. There are also a lot of ways the project should help you.
*   Code
*   Provide Translations in other languages.
*   Design ( Good design instincts, smooth out the rough edges)
*   Compile/Testers
*   Beta testers
*   Make helpful support content
*   Make guides ("How to set up cameras?", etc.)
*   Bounce ideas around
  
If you want to get into contact and help, then the [Discord Channel](https://discord.gg/vkDD3HdQq6) is the easiest and fastest way to reach out to us - we are looking forward to hear from you.


## Lightburn integration
Meerk40t allows to act as an intermediary between your K40 laser and software that supports Ruida-controlled laser equipment - [Lightburn](https://lightburnsoftware.com/) is a relevant example of such a software product. You just need to issue the command ``ruidacontrol`` in MeerK40ts console window, and you will then be able to add an emulated Ruida Laser inside Lightburn™. Laser jobs that are created inside Lightburn™ and sent to this laser will be picked up by MeerK40t and sent to your K40. See some more detailed instructions in this [video](https://www.youtube.com/watch?v=LUUfLf5Agu0). Please note `ruidacontrol` will require the DSP version of Lightburn™. (Present in all versions since 0.7)

With 0.9 another way of interacting with Lightburn was introduced, which will work as well with the standard version of LB: You just need to issue the command ``grblcontrol`` in MeerK40ts console window, and you will then be able to add an emulated remote GBRL-LPC laser inside Lightburn or any TCP GRBL control software.
