""" This example uses CircuitPython's built-in `usb_hid` API
to emulate a mouse with the Cirque circle trackpad. This example
also works with glidepoint_lite.py"""
import time
import board
from digitalio import DigitalInOut
import usb_hid
# if using a trackpad configured for SPI
from circuitpython_cirque_pinnacle.glidepoint import  PinnacleTouchSPI, ABSOLUTE, RELATIVE
# if using a trackpad configured for I2C
# from circuitpython_cirque_pinnacle.glidepoint import  PinnacleTouchI2C, ABSOLUTE, RELATIVE
# i2c = board.I2C()

# if using a trackpad configured for SPI
spi = board.SPI()
ss_pin = DigitalInOut(board.D7)

dr_pin = DigitalInOut(board.D2)

# if using a trackpad configured for SPI
tpad = PinnacleTouchSPI(spi, ss_pin) # NOTE we did not pass the dr_pin
# if using a trackpad configured for I2C
# tpad = PinnacleTouchI2C(i2c) # NOTE we did not pass the dr_pin

tpad.data_mode = RELATIVE  # ensure mouse mode is enabled

mouse = None
for dev in usb_hid.devices:
    # be sure we're grabbing the mouse singleton
    if dev.usage == 2 and dev.usage_page == 1:
        mouse = dev
# mouse.send_report() takes a 4 byte buffer in which
#   byte0 = buttons in which
#       bit5 = back, bit4 = forward, bit2 = middle, bit1 = right, bit0 = left
#   byte1 = delta x-axis
#   byte2 = delta y-axis
#   byte3 = delta scroll wheel

def move(timeout=10):
    """Send mouse X & Y reported data from the Pinnacle touch controller
    until there's no input for a period of ``timeout`` seconds."""
    if mouse is None:
        raise OSError("mouse HID device not available.")
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        data = tpad.report()  # only returns fresh data (if any)
        if data:  # is there fresh data?
            mouse.send_report(data)  # not using scroll wheel; nor back/forward butons
            start = time.monotonic()
    mouse.send_report(b'\x00' * 4)  # release buttons (just in case)
