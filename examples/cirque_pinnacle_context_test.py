"""This example shows the difference in register values between AnyMeas mode
and Absolute mode using the library's context manager."""
import board
from digitalio import DigitalInOut
from circuitpython_cirque_pinnacle import PinnacleTouchSPI, DataModes

spi = board.SPI()
ss_pin = DigitalInOut(board.D7)
dr_pin = DigitalInOut(board.D2)
dr_pin.switch_to_input()
csn_pin = DigitalInOut(board.D5)

tpad_abs = PinnacleTouchSPI(spi, ss_pin) # NOTE we did not pass the dr_pin
tpad_abs.data_mode = DataModes.ABSOLUTE

# NOTE The dr_pin is a required arg to use AnyMeas mode
tpad_any = PinnacleTouchSPI(spi, ss_pin, dr_pin=dr_pin)
# if dr_pin was not specified upon instantiation.
# this command will raise an AttributeError exception
tpad_any.data_mode = DataModes.ANYMEAS

# This example accesses the hidden bus protocol functions to read and
# print the data from the Pinnacle ASIC's configuration registers.
# pylint: disable=protected-access

print("register configured for Absolute data mode:")
with tpad_abs as tpad:
    for index, val in enumerate(tpad._rap_read_bytes(0x04, 11)):
        print("\taddress {} = {}".format(hex(index + 4), hex(val)))

print("\nregister configured for AnyMeas data mode:")
with tpad_any as tpad:
    for index, val in enumerate(tpad._rap_read_bytes(0x04, 11)):
        print("\taddress {} = {}".format(hex(index + 4), hex(val)))

# NOTE how different the register values are.
# Registers remain unaffected when exiting the `with` block, so technically
# tpad_abs (configured for Absolute mode) will not function properly outside
# a new `with` block after tpad_any (configured for AnyMeas mode) was the last
# object used in a `with` block.

# NOTE the Pinnacle ASIC is powered down when exiting a `with` block
print("Powered down?", tpad_any.shutdown)
# ok to read the shutdown attribute here because it does not write to the
# Pinnacle ASIC's register, but notice it is the last object used in a `with`
# block (otherwise the data may be innaccurate).
