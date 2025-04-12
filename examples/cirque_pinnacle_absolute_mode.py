"""
A simple example of using the Pinnacle ASIC in absolute mode.
"""

import math
import sys
import time
import board
from digitalio import DigitalInOut
from circuitpython_cirque_pinnacle import (
    PinnacleTouchSPI,
    PinnacleTouchI2C,  # noqa: imported-but-unused
    PINNACLE_ABSOLUTE,
    AbsoluteReport,
)

IS_ON_LINUX = sys.platform.lower() == "linux"

print("Cirque Pinnacle absolute mode\n")

# the pin connected to the trackpad's DR pin.
dr_pin = DigitalInOut(board.D7 if not IS_ON_LINUX else board.D25)

if not input("Is the trackpad configured for I2C? [y/N] ").lower().startswith("y"):
    print("-- Using SPI interface.")
    spi = board.SPI()
    ss_pin = DigitalInOut(board.D2 if not IS_ON_LINUX else board.CE0)
    trackpad = PinnacleTouchSPI(spi, ss_pin, dr_pin)
else:
    print("-- Using I2C interface.")
    i2c = board.I2C()
    trackpad = PinnacleTouchI2C(i2c, dr_pin)

trackpad.data_mode = PINNACLE_ABSOLUTE  # ensure Absolute mode is enabled
trackpad.absolute_mode_config(z_idle_count=1)  # limit idle packet count to 1

# an object to hold the data reported by the Pinnacle
data = AbsoluteReport()


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
            # specification sheet recommends clamping absolute position data of
            # X & Y axis for reliability
            if data.z:  # only clamp values if Z axis is not idle.
                data.x = max(128, min(1920, data.x))  # X-axis
                data.y = max(64, min(1472, data.y))  # Y-axis
            print(data)
            start = time.monotonic()


def print_trig(timeout=6):
    """Print available data reports from the Pinnacle touch controller as trigonometric
    calculations until there's no input for a period of ``timeout`` seconds."""
    print(
        "Touch the trackpad to see the data. Exits after",
        timeout,
        "seconds of inactivity.",
    )
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        while trackpad.available():  # is there new data?
            trackpad.read(data)

            if not data.z:  # if not touching (or near) the sensor
                print("Idling")  # don't do calc when both axes are 0
            else:  # if touching (or near) the sensor
                # datasheet recommends clamping X & Y axis for reliability
                data.x = max(128, min(1920, data.x))  # 128 <= x <= 1920
                data.y = max(64, min(1472, data.y))  # 64 <= y <= 1472

                # coordinates assume axes have been clamped to recommended ranges
                coord_x = data.x - 960
                coord_y = data.y - 736  # NOTE: y-axis is inverted by default
                radius = math.sqrt(math.pow(coord_x, 2) + math.pow(coord_y, 2))
                # angle (in degrees) ranges [-180, 180];
                angle = math.atan2(coord_y, coord_x) * 180 / math.pi
                print("angle: %.02f\tradius: %.02f" % (angle, radius))
            start = time.monotonic()


def set_role():
    """Set the role using stdin stream. Arguments for functions can be
    specified using a space delimiter (e.g. 'M 10' calls `print_data(10)`)
    """
    user_input = (
        input(
            "\n*** Enter 'M' to measure and print raw data."
            "\n*** Enter 'T' to measure and print trigonometric calculations."
            "\n*** Enter 'Q' to quit example.\n"
        )
        or "?"
    ).split()
    if user_input[0].upper().startswith("M"):
        print_data(*[int(x) for x in user_input[1:2]])
        return True
    if user_input[0].upper().startswith("T"):
        print_trig(*[int(x) for x in user_input[1:2]])
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
    print(
        "\nRun print_data() to read and print raw data.",
        "Run print_trig() to measure and print trigonometric calculations.",
        sep="\n",
    )
