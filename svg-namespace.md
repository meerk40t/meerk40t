# Meerk40t SVG XML extensions
This web page briefly describes the Meerk40t-specific
extensions to the standard SVG [XML-namespace](http://www.w3.org/TR/REC-xml-names).

## Meerk40t namespace extensions
Meerk40t needs to store information in the SVG file that is specific to Meerk40t.

Prior to version 0.8.0, meerk40t utilised two xml tags that were not conformant with
xml-namespace syntax:

* operation
* note

For backwards compatibility reasons, these tags are still supported on loading an SVG file.

For version 0.8.0, an xml-namespace conformant extension to standard SVG is added to the SVG tag
as follows:

* xmlns:meerk40t="https://www.github.com/meerk40t/meerk40t/svg-namespace.md"

This namespace defines the following SVG xml extensions:

### SVG tag, meerk40t version: `<svg meerk40t:version>`
In Inkscape written SVG files, the SVG tag already contains details of the Inkscape version that
wrote the file.

We now add an equivalent attribute to define the Meerk40t version that wrote the file:
* meerk40t:version="0.8.0"

### Operations: `<meerk40t:op>`
Meerk40t Laser Operations are stored as follows:
* Tag: meerk40t:op
    * Attribute: acceleration="int"
    * Attribute: acceleration_custom="bool"
    * Attribute: advanced="bool"
    * Attribute: color="#xxxxxx"
    * Attribute: default="bool"
    * Attribute: dot_length="int"
    * Attribute: dot_length_custom="bool"
    * Attribute: dratio="float"
    * Attribute: dratio_custom="bool"
    * Attribute: jog_distance="int"
    * Attribute: jog_enable="bool"
    * Attribute: label="Image 350mm/s =B2T 1000ppi &#177;20"
    * Attribute: laser_enabled="bool"
    * Attribute: operation="str" (Image, Raster, Engrave, Cut, Dot)
    * Attribute: output="bool"
    * Attribute: overscan="int"
    * Attribute: passes="int"
    * Attribute: passes_custom="bool"
    * Attribute: power="float"
    * Attribute: ppi_enabled="bool"
    * Attribute: raster_direction="int"
    * Attribute: raster_preference_bottom="int"
    * Attribute: raster_preference_left="int"
    * Attribute: raster_preference_right="int"
    * Attribute: raster_preference_top="int"
    * Attribute: raster_step="int"
    * Attribute: raster_swing="bool"
    * Attribute: shift_enabled="bool"
    * Attribute: show="bool"
    * Attribute: speed="float"

TODO: Check that all these are actually used in the code.

Note: This is identical to the earlier `<operation>` tag except for
the omission of the following attributes previously stored
which are either ephemeral (relating to the GUI state rather than the project)
or redundant (e.g. `type="op"`):
    * Attribute: emphasized="bool"
    * Attribute: highlighted="bool"
    * Attribute: selected="bool"
    * Attribute: targeted="bool"
    * Attribute: type="str" (= "op" for all operations)

### Special Operations: `<meerk40t:cmdop>`
The `<meerk40t:cmdop>` tag is a new tag to store details of
special operations (such as Home, Beep, Interrupt etc.)
so that these can be saved and reloaded.

* Tag: meerk40t:cmdop
    * Attribute: label="str"
    * Attribute: name="str"
    * Attribute: command="int"
    * Attribute: args="str,..."
    * Attribute: output="bool"

### Note: `<meerk40t:note>`
This is identical to the earlier `<note>` tag:

* Tag: meerk40t:note
    * Attribute: text="str"

### Additional attributes on SVG elements
The following attributes will also be saved against SVGelement xml tags
(such as rect, circle, elipse, path, text etc.):

    * Attribute: inkscape:label="str" (if in the original file)
    * Attribute: meerk40t:ops="int,..." (associating with the op/cmdop operation listed above)

## DTD
A DTD is provided as a formal syntactic definition of these extensions attributes at:
https://github.com/meerk40t/meerk40t/blob/main/meerk40t.dtd
with a machine readable version accessible at
https://raw.githubusercontent.com/meerk40t/meerk40t/main/meerk40t.dtd

In theory a `<!DOCTYPE >` tag could be added to the SVG file to reference this,
however since this is non-standard Meerk40t does not do so in case it creates
interoperability issues.

## Existing SVG namespaces
The default namespace for SVG XML documents is `https://www.w3.org/2000/svg`.
This web URL gives a brief description of SVG and provides links to the SVG
documentation.
A [SVG DTD](https://www.w3.org/TR/2000/03/WD-SVG-20000303/svgdtd.html)
is described at https://www.w3.org/TR/2000/03/WD-SVG-20000303/svgdtd.html.

SVG files produced by Inkscape contain xml-namespace references to two
inkscape-specific extensions to standard SVG xml:
*  inkscape: http://www.inkscape.org/namespaces/inkscape
*  sodipodi: http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd
Sodipodi was an earlier name for Inkscape hence the separate namespaces.

Inkscape also adds the following namespaces to SVG files:
* xlink: http://www.w3.org/1999/xlink
* rdf: http://www.w3.org/1999/02/22-rdf-syntax-ns#
* cc: http://creativecommons.org/ns#
* dc: http://purl.org/dc/elements/1.1/
