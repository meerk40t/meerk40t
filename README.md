# Welcome to SefroCut!

**SefroCut** is a fork of [MeerK40t](https://github.com/meerk40t/meerk40t), a built-from-the-ground-up MIT licensed open-source laser cutting software.

## About This Fork

SefroCut is a custom fork based on MeerK40t, designed to provide enhanced features and specialized capabilities for laser cutting and engraving workflows.

**Original Project:** MeerK40t by [jpirnay](https://github.com/meerk40t/meerk40t)
**License:** MIT
**Fork Repository:** https://github.com/morroware/MyK40

## Primary Goals

* Provide users with high quality laser control software
* Provide developers with a highly extensible platform to help further their own ideas and provide novel work to the laser community at large

## Getting Started

To get up and running with SefroCut:

### Installation from Source

You can run SefroCut directly from Python:

```bash
pip install sefrocut[all]
```

Then run at the command line:

```bash
sefrocut
```

For more details on installation from source, see the [Install: Source wiki page](https://github.com/meerk40t/meerk40t/wiki/Install:-Source) from the original MeerK40t project.

### Command Line Interface

SefroCut has an advanced internal console system allowing access to most parts of the code with various commands. It also provides a command line interface which allows you to automate processes. To learn more, execute it in a terminal with the `--help` argument:

```bash
sefrocut --help
```

## Screenshots
![grafik](https://github.com/user-attachments/assets/e56135a2-7b1f-44be-9761-b92931e300f6)

## Architecture

The wxSefroCut GUI is written in wxPython using AUI to provide a highly configurable UI. The system allows easy addition of panes and tools, with many already available.

## Drivers

SefroCut provides a variety of drivers with an extensible framework to support different laser devices. The code was written with the myriad of possibilities for different software in mind.

### Supported Devices

* Lihuiyu M2/M3-Nano (aka K40 lasers)
* Any GRBL device (Atomstack, Creality, Longer, Ortur, etc.)
* Ezcad2-compatible JCZ controllers galvo lasers
* Moshiboard
* NewlyDraw System 8.1 Lasers
* Ruida-Emulation (Middleman between Lightburn and K40)

## Attribution & Credits

SefroCut is a fork of **MeerK40t** (pronounced MeerKat), created by **Jens Pirnay (jpirnay)**.

* Original MeerK40t Repository: https://github.com/meerk40t/meerk40t
* Original Author: jpirnay
* Original License: MIT

We are grateful to the MeerK40t project and its contributors for creating such a robust foundation for laser cutting software.

## License

SefroCut maintains the MIT license of the original MeerK40t project. See the LICENSE file for full details.
