"""
A simple example of using the Pinnacle ASIC in relative mode.
"""
import time
import board
from digitalio import DigitalInOut
from circuitpython_cirque_pinnacle import (
    PinnacleTouchSPI,
    PinnacleTouchI2C,  # noqa: imported-but-unused
    RelativeReport,
)

dr_pin = DigitalInOut(board.D7)
# NOTE The dr_pin is an optional keyword argument to the
# constructor when using Absolute or Relative modes

# if using a trackpad configured for SPI
spi = board.SPI()
ss_pin = DigitalInOut(board.D2)
trackpad = PinnacleTouchSPI(spi, ss_pin, dr_pin=dr_pin)
# if using a trackpad configured for I2C
# i2c = board.I2C()
# trackpad = PinnacleTouchI2C(i2c, dr_pin=dr_pin)


def print_data(timeout=6):
    """Print available data reports from the Pinnacle touch controller
    until there's no input for a period of ``timeout`` seconds."""
    print("touch the sensor to see the data")
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if dr_pin.value:  # is there new data?
            data: RelativeReport = trackpad.read()
            print(data)
            start = time.monotonic()


def set_role():
    """Set the role using stdin stream. Timeout arg for slave() can be
    specified using a space delimiter (e.g. 'P 10' calls `print_data(10)`)
    """
    user_input = (
        input("*** Enter 'P' to read and print data.\n*** Enter 'Q' to quit example.\n")
        or "?"
    )
    user_input = user_input.split()
    if user_input[0].upper().startswith("P"):
        print_data(*[int(x) for x in user_input[1:2]])
        return True
    if user_input[0].upper().startswith("Q"):
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


print("    Cirque Pinnacle relative mode")

if __name__ == "__main__":
    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down trackpad...")
else:
    print("    Run print_data() to read and print data.")
