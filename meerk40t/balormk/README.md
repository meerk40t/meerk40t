# Balor

BalorMK is the meerk40t plugin-driver for Balor by Bryce Schroeder which controls the LMC ezcad2 galvo laser boards.

## Commands

### Spool

Send Balor or Plan to spooler

### Mark

Create a mark job out of selected elements.

### Light

Create a lighting job out of selected elements.

### Stop

Stop the looping idle job.

### estop 

### pause

### resume

### usb_connect

### usb_disconnect

### print, png, debug, save

### duplicates, loop

### goto

### red, red off

### status, lstatus, serial_number

### correction

## Licensing

Balor's original code was GPL licenced but was completely scrapped in pieces over time for this project. The new code still uses the name balor but was recoded from scratch based on various needs. For example the old balor code wasn't well suited to run uncompleted code and send packets while code in another thread is building that data. The replacement uses the name balor but is only based on some of the original research and none of the original code, outside of sections which were written specifically by me (Tatarize) originally anyway. 
