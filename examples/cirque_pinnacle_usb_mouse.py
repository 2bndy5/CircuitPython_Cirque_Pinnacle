""" a simple test to debug the library's API """
import time
import struct
import board
import usb_hid
from digitalio import DigitalInOut
import circuitpython_cirque_pinnacle as pinnacle

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

SPI = board.SPI()
ss_pin = DigitalInOut(board.D7)
dr_pin = DigitalInOut(board.D2)

trackpad = pinnacle.PinnacleTouchSPI(SPI, ss_pin, dr_pin)
trackpad.set_adc_gain(1) # for curved overlay type
trackpad.set_data_mode() # ensure mouse mode is enabled

def enable_mouse(timeout=10):
    """Send mouse X & Y reported data from the Pinnacle touch controller
    for a period of ``timeout`` seconds.
    """
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        data = trackpad.report()
        if data:
            rep = struct.pack('Bbb', data['buttons'], data['x'] >> 1, data['y'] >> 1)
            mouse.send_report(rep + b'\x00') # not using scroll wheel
    mouse.send_report(b'\x00' * 4) # release buttons (just in case)
