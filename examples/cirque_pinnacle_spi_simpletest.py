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

trackpad = PinnacleTouchSPI(spi, ss_pin) # NOTE we did not pass the dr_pin
trackpad.set_adc_gain(1) # for curved overlay type
trackpad.data_mode = DataModes.ABSOLUTE # ensure Absolute mode is enabled
trackpad.absolute_mode_config(z_idle_count=1) # limit idle packet count to 1

def print_data(timeout=10):
    """Print available data reports from the Pinnacle touch controller
    for a period of ``timeout`` seconds.
    """
    print("using {} mode".format("Relative" if not trackpad.data_mode else "Absolute"))
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if dr_pin.value: # is there new data?
            data = trackpad.report(only_new=False)
            # Because we did not specify the dr_pin when instantiating the trackpad variable,
            # only_new=False skips the extra SPI transaction to check the SW_DR flag in the
            # STATUS register which is reflected on the dr_pin (that we checked already)
            print(unpack('Bbbb', data) if not trackpad.data_mode else data)
