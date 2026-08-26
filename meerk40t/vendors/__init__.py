"""
Vendor-specific hardware integrations.

Each subpackage implements support for a specific controller/firmware ecosystem
(GRBL, Lhystudios, Ruida, Moshiboard, Newly, Balor) or vendor hardware component
(CH341 USB chip). Packages are registered as device providers via the internal
plugin system and can be excluded from builds independently.
"""
