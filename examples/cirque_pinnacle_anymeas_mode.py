"""
A simple example of using the Pinnacle ASIC in anymeas mode.
"""
import sys
import time
import board
from digitalio import DigitalInOut
from circuitpython_cirque_pinnacle import (
    PinnacleTouchSPI,
    PinnacleTouchI2C,
    PINNACLE_ANYMEAS,
)

IS_ON_LINUX = sys.platform.lower() == "linux"

print("Cirque Pinnacle anymeas mode\n")

# Using HW Data Ready pin as required for Anymeas mode
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

trackpad.data_mode = PINNACLE_ANYMEAS

vectors = [
    #  toggle  ,   polarity
    (0x00010000, 0x00010000),  # This toggles Y0 only and toggles it positively
    (0x00010000, 0x00000000),  # This toggles Y0 only and toggles it negatively
    (0x00000001, 0x00000000),  # This toggles X0 only and toggles it positively
    (0x00008000, 0x00000000),  # This toggles X16 only and toggles it positively
    (0x00FF00FF, 0x000000FF),  # This toggles Y0-Y7 negative and X0-X7 positive
]

# a list of compensations to use with measured `vectors`
compensation = [0] * len(vectors)


def compensate(count=5):
    """Take ``count`` measurements, then average them together (for each vector)"""
    for i, (toggle, polarity) in enumerate(vectors):
        compensation[i] = 0
        for _ in range(count):
            result = trackpad.measure_adc(toggle, polarity)
            compensation[i] += result
        compensation[i] = int(compensation[i] / count)
        print("compensation {}: {}".format(i, compensation[i]))


def take_measurements(timeout=6):
    """Read ``len(vectors)`` number of measurements and print results for
    ``timeout`` number of seconds."""
    print("Taking measurements for", timeout, "seconds.")
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        for i, (toggle, polarity) in enumerate(vectors):
            result = trackpad.measure_adc(toggle, polarity)
            print("meas{}: {}".format(i, result - compensation[i]), end="\t")
        print()


def set_role():
    """Set the role using stdin stream. Arguments for functions can be
    specified using a space delimiter (e.g. 'C 10' calls `compensate(10)`)
    """
    user_input = (
        input(
            "\n*** Enter 'C' to get compensations for measurements."
            "\n*** Enter 'M' to read and print measurements."
            "\n*** Enter 'Q' to quit example.\n"
        )
        or "?"
    ).split()
    if user_input[0].upper().startswith("C"):
        compensate(*[int(x) for x in user_input[1:2]])
        return True
    if user_input[0].upper().startswith("M"):
        take_measurements(*[int(x) for x in user_input[1:2]])
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
        "\nRun compensate() to set compensations for measurements.",
        "Run take_measurements() to read and print measurements.",
        sep="\n",
    )
