# CH341

The CH341 Universal USB Interface chip is used to interface a particular board to to a computer USB connection.
These are popular in both production and hobbyist functions, and the chips are cheap and ubiquitous.
Both the Lhystudios boards and the Moshiboards use this chip type.
It's also possible and likely to find these in some Arduino systems and for hobbyists to use them.

The purpose of this module is to provide connections to the CH341 interface objects.
This should allow multiple different connections to different CH341 connections.

The module works like a socket handler and provides different CH341 connections on demand if there are any to provide.
This can be requested in specific fashion based on criteria
or they can be accessed then rejected in turn after some minimum interactions.
For example if we get a CH341 connection that has a current status of 205
we can reject this connection in a Lhystudios driver because this code is never used there.
However, if we are accessing this data as a Moshiboard driver, we might reject any status *other* than a 205.

While it is not the goal of this sub-project to fully map out all CH341 commands,
it should serve as a usable starting place for a generic CH341 driver
and not be explicitly limited to uses here.
CH341 drivers common are used to read and write EEPROM data
and nothing in this project should be so specific as to prevent such interactions
even if those interactions are not our purposes here.

http://www.wch-ic.com/products/CH341.html