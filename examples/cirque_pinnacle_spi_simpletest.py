""" a simple test to debug the library's API """
import time
import board
from digitalio import DigitalInOut
import circuitpython_cirque_pinnacle as pinnacle

SPI = board.SPI()
ss_pin = DigitalInOut(board.D7)
dr_pin = DigitalInOut(board.D2)

trackpad = pinnacle.PinnacleTouchSPI(SPI, ss_pin, dr_pin, allow_sleep=1)
trackpad.set_adc_gain(1) # for curved overlay type

def print_data(timeout=10):
    """Print available data reports from the Pinnacle touch controller
    for a period of ``timeout`` seconds.
    """
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        data = trackpad.report()
        if data:
            print(data)
