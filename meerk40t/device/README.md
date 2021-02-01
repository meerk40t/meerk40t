
# Device

Device modules are specific to laser cutting and the lower level interactions with laser cutter drivers. This includes the USB connections and connections to the CH341-chip through both the libUSB driver (`pyusb`) as well as any networked connections with laser-cutters.

This includes mock devices that are emulated for the purposes of compatibility or research.

# Lhystudios
These are the stock M2 Nano boards by Lhystudios and other closely related boards. This is the primary user of CH341 interfacing drivers. And the most complete driver availible. This includes parsing of Lhymicro-GL, production of Lhymicro-GL, channels of the data being sent over the USB. As well as emulation and parsing the commands.


# Moshi

Moshiboard classes are intended to deal with USB interactions to and from the CH341 chips on Moshiboards over USB. This is the result of `Project Moshi` (https://github.com/meerk40t/moshi) which seeks to reverse engineer the Moshiboard interactions and control them with MeerK40t. This provides functional Moshiboard drivers.



# Ruida
Ruida classes deal with interactions between MeerK40t and Ruida-devices. Currently this is limited to reading .rd files and accepting mock Ruida connections from software that connects through UDP connections. Including RDWorks, Lightburn, and a Ruida android application. As well as anything else that produces Ruida code. The parser is able to read every Ruida command known.

Using `ruidaserver --spool` for example will make a socket connection to make the localhost appear as a ruida laser cutter. Any commands sent to it will be spooled with regard to the `--spool` command and the resulting laser code will be sent to the locally configured laser device.


# GRBL

Grbl and more generic gcode devices and their interactions. Currently this project is a stub. However the `grblserver` previously has worked and allowed direct interactions with the GRBL Emulator and permitted the exporting of commands to the Lhystudios devices.
