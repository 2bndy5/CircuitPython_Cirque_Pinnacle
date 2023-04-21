"""
A simple example of using the Pinnacle ASIC in relative mode.
"""
import sys
import time
import board
from digitalio import DigitalInOut
from circuitpython_cirque_pinnacle import (
    PinnacleTouchSPI,
    PinnacleTouchI2C,
    RelativeReport,
    PINNACLE_RELATIVE,
)

IS_ON_LINUX = sys.platform.lower() == "linux"

print("Cirque Pinnacle relative mode\n")

# a HW ``dr_pin`` is more efficient, but not required for Absolute or Relative modes
dr_pin = None
if not input("Use SW Data Ready? [y/N] ").lower().startswith("y"):
    print("-- Using HW Data Ready pin.")
    dr_pin = DigitalInOut(board.D7 if not IS_ON_LINUX else board.D25)

if not input("Is the trackpad configured for I2C? [y/N] ").lower().startswith("y"):
    print("-- Using SPI interface.")
    spi = board.SPI()
    ss_pin = DigitalInOut(board.D2 if not IS_ON_LINUX else board.CE0)
    trackpad = PinnacleTouchSPI(spi, ss_pin, dr_pin=dr_pin)
else:
    print("-- Using I2C interface.")
    i2c = board.I2C()
    trackpad = PinnacleTouchI2C(i2c, dr_pin=dr_pin)

trackpad.data_mode = PINNACLE_RELATIVE  # ensure mouse mode is enabled
trackpad.relative_mode_config(True)  # enable tap detection

# an object to hold the data reported by the Pinnacle
data = RelativeReport()


def print_data(timeout=6):
    """Print available data reports from the Pinnacle touch controller
    until there's no input for a period of ``timeout`` seconds."""
    print(
        "Touch the trackpad to see the data. Exits after",
        timeout,
        "seconds of inactivity.",
    )
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        while trackpad.available():  # is there new data?
            trackpad.read(data)
            print(data)
            start = time.monotonic()


def set_role():
    """Set the role using stdin stream. Arguments for functions can be
    specified using a space delimiter (e.g. 'M 10' calls `print_data(10)`)
    """
    user_input = (
        input(
            "\n*** Enter 'M' to measure and print data."
            "\n*** Enter 'Q' to quit example.\n"
        )
        or "?"
    ).split()
    if user_input[0].upper().startswith("M"):
        print_data(*[int(x) for x in user_input[1:2]])
        return True
    if user_input[0].upper().startswith("Q"):
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


if __name__ == "__main__":
    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected.")
else:
    print("\nRun print_data() to measure and print data.")
