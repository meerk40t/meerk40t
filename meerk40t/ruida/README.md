# Ruida

Ruida classes deal with interactions between MeerK40t and Ruida-devices. Currently, this is limited to reading .rd files
and accepting mock Ruida connections from software that connects through UDP connections. Including RDWorks, Lightburn,
and a Ruida android application. As well as anything else that produces Ruida code. The parser is able to read every
Ruida command known.

Using `ruidacontrol` for example will make a socket connection to make the localhost appear as a ruida laser cutter. Any
commands sent to it will be spooled and the resulting laser code will be sent to the locally configured active laser
device. Likewise `ruidadesign` will transfer the ruida CutCode without executing it.
