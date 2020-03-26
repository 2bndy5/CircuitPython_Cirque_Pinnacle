""" a simple test example using SPI """
import time
from struct import unpack
import board
from digitalio import DigitalInOut
# this example also works with glideoint_lite.py
from circuitpython_cirque_pinnacle.glidepoint import  PinnacleTouchSPI, ABSOLUTE

spi = board.SPI()
ss_pin = DigitalInOut(board.D7)
dr_pin = DigitalInOut(board.D2)
dr_pin.switch_to_input()

tpad = PinnacleTouchSPI(spi, ss_pin) # NOTE we did not pass the dr_pin
tpad.data_mode = ABSOLUTE # ensure Absolute mode is enabled
tpad.absolute_mode_config(z_idle_count=1) # limit idle packet count to 1

def print_data(timeout=10):
    """Print available data reports from the Pinnacle touch controller
    for a period of ``timeout`` seconds."""
    print("using {} mode".format("Relative" if tpad.data_mode < 2 else "Absolute"))
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if dr_pin.value: # is there new data?
            data = tpad.report(only_new=False)
            # Because we did not specify the dr_pin when instantiating the tpad variable,
            # only_new=False skips the extra SPI transaction to check the SW_DR flag in
            # the STATUS register which is reflected on the dr_pin
            print(unpack('Bbbb', data) if tpad.data_mode < 2 else data)
