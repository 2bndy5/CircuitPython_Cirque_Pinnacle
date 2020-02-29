""" a simple test example using SPI """
import time
from struct import unpack
import board
from digitalio import DigitalInOut
import circuitpython_cirque_pinnacle as pinnacle

SPI = board.SPI()
ss_pin = DigitalInOut(board.D7)
dr_pin = DigitalInOut(board.D2)

trackpad = pinnacle.PinnacleTouchSPI(SPI, ss_pin, dr_pin, z_idle_count=1)
trackpad.set_adc_gain(1) # for curved overlay type
trackpad.set_data_mode() # ensure mouse mode is enabled

def print_data(timeout=10):
    """Print available data reports from the Pinnacle touch controller
    for a period of ``timeout`` seconds.
    """
    print("using {} mode".format("Relative" if trackpad.mouse_mode else "Absolute"))
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        data = trackpad.report()
        if data:
            print(unpack('Bbbb', data) if trackpad.mouse_mode else data)
