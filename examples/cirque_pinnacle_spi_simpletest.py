""" a simple test example using SPI """
import time
from struct import unpack
import board
from digitalio import DigitalInOut
from circuitpython_cirque_pinnacle import PinnacleTouchSPI, DataModes

spi = board.SPI()
ss_pin = DigitalInOut(board.D7)
dr_pin = DigitalInOut(board.D2)
dr_pin.switch_to_input()

trackpad = PinnacleTouchSPI(spi, ss_pin)
trackpad.set_adc_gain(1) # for curved overlay type
trackpad.z_idle_count = 1  # set idle empty packet count to 1
trackpad.data_mode = DataModes.RELATIVE # ensure mouse mode is enabled

def print_data(timeout=10):
    """Print available data reports from the Pinnacle touch controller
    for a period of ``timeout`` seconds.
    """
    print("using {} mode".format("Relative" if not trackpad.data_mode else "Absolute"))
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        is_new = dr_pin.value
        data = trackpad.report()
        print("new:", is_new, unpack('Bbbb', data) if not trackpad.data_mode else data)
