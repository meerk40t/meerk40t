# Welcome to MeerK40t!
MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed open-source laser cutting software.

The primary goals of this software is simple:


* Provide users with high quality laser control software.
* Provide developers with a highly extensible platform to help further their own ideas, and provide novel work to the laser community at large.

## Getting started
To get up and running, simply download Meerk40t from [here](https://github.com/meerk40t/meerk40t/releases) for your specific platform. (Windows, Mac OSX, Linux, and by extension, Raspberry Pi).

<details>
<summary>Release Versions (Just use the latest)</summary>


> * 0.9 - Active - New features and some underlying architectural changes. Try the latest released version: [0.9.9000](https://github.com/meerk40t/meerk40t/releases/tag/0.9.9000) (Jan 17, 2026) or try a prerelease even: [release list](https://github.com/meerk40t/meerk40t/releases)
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

Meerk40t provides a variety of drivers with an extensible framework to provide support for other new laser devices. The code was written with the myriad of possibilities for different software in mind. For example, it may be essential that GRBL be able to reset an alarm or notify the user of particular error codes. The configuration for GRBL is not the same for the configuration of other laser control drivers. With this in mind, MeerK40t can radically change how and when it works


### Supported devices
*   Lihuiyu M2/M3-Nano (aka K40 lasers)
*   Any GRBL device (Atomstack, Creality, Longer, Ortur etc...)
*   Ezcad2-compatible JCZ controllers galvo lasers
*   Moshiboard
*   NewlyDraw System 8.1 Lasers
*   Ruida-Emulation (Middleman between Lightburn and K40)