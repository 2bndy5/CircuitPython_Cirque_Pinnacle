"""
A simple example of using the Pinnacle ASIC in anymeas mode.
"""
import time
import board
from digitalio import DigitalInOut
from circuitpython_cirque_pinnacle import (
    PinnacleTouchSPI,
    PinnacleTouchI2C,  # noqa: imported-but-unused
    ANYMEAS,
)

dr_pin = DigitalInOut(board.D7)
# NOTE The dr_pin is a required keyword argument to the
# constructor when using AnyMeas mode

# if using a trackpad configured for SPI
spi = board.SPI()
ss_pin = DigitalInOut(board.D2)
trackpad = PinnacleTouchSPI(spi, ss_pin, dr_pin=dr_pin)
# if using a trackpad configured for I2C
# i2c = board.I2C()
# trackpad = PinnacleTouchI2C(i2c, dr_pin=dr_pin)

# if dr_pin was not specified upon instantiation.
# this command will raise an AttributeError exception
trackpad.data_mode = ANYMEAS

vectors = [
    # This toggles Y0 only and toggles it positively
    (0x00010000, 0x00010000),
    # This toggles Y0 only and toggles it negatively
    (0x00010000, 0x00000000),
    # This toggles X0 only and toggles it positively
    (0x00000001, 0x00000000),
    # This toggles X16 only and toggles it positively
    (0x00008000, 0x00000000),
    # This toggles Y0-Y7 negative and X0-X7 positive
    (0x00FF00FF, 0x000000FF),
]

idle_vectors = [0] * len(vectors)


def compensate(count=5):
    """take ``count`` measurements, then average them together"""
    for i, vector in enumerate(vectors):
        idle_vectors[i] = 0
        for _ in range(count):
            result = trackpad.measure_adc(
                bits_to_toggle=vector[0], toggle_polarity=vector[1]
            )
            idle_vectors[i] += result
        idle_vectors[i] = int(idle_vectors[i] / count)
        print("compensation {}: {}".format(i, idle_vectors[i]))


def take_measurements(timeout=6):
    """read ``len(vectors)`` number of measurements and print results for
    ``timeout`` number of seconds."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        for i, vector in enumerate(vectors):
            result = trackpad.measure_adc(
                bits_to_toggle=vector[0], toggle_polarity=vector[1]
            )
            print("meas{}: {}".format(i, result - idle_vectors[i]), end="\t")
        print()


def set_role():
    """Set the role using stdin stream. Timeout arg for slave() can be
    specified using a space delimiter (e.g. 'C 10' calls `compensate(10)`)
    """
    user_input = (
        input(
            "*** Enter 'C' to get compensations for measurements.\n"
            "*** Enter 'M' to read and print measurements.\n"
            "*** Enter 'Q' to quit example.\n"
        )
        or "?"
    )
    user_input = user_input.split()
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


print("    Cirque Pinnacle anymeas mode")

if __name__ == "__main__":
    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down trackpad...")
else:
    print(
        "    Run compensate() to set compensations for measurements.",
        "    Run take_measurements() to read and print measurements.",
        sep="\n",
    )
