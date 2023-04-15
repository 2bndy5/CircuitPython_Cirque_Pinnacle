"""
This example uses CircuitPython's built-in `usb_hid` API
to emulate a mouse with the Cirque circle trackpad.

NOTE: This example won't work on Linux (eg. using Raspberry Pi GPIO pins).
"""
import sys
import time
import board
from digitalio import DigitalInOut
import usb_hid
from circuitpython_cirque_pinnacle import (
    PinnacleTouchSPI,
    PinnacleTouchI2C,
    PINNACLE_RELATIVE,
    RelativeReport,
)

IS_ON_LINUX = sys.platform.lower() == "linux"

print("Cirque Pinnacle as a USB mouse\n")

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
# tell the Pinnacle ASIC to rotate the orientation of the axis data by +90 degrees
trackpad.relative_mode_config(rotate90=True)

# an object to hold the data reported by the Pinnacle
data = RelativeReport()

mouse = None
for dev in usb_hid.devices:
    # be sure we're grabbing the mouse singleton
    if dev.usage == 2 and dev.usage_page == 1:
        mouse = dev
        break
else:
    raise OSError("mouse HID device not available.")
# mouse.send_report() takes a 4 byte buffer in which
#   byte0 = buttons in which
#       bit5 = back, bit4 = forward, bit2 = middle, bit1 = right, bit0 = left
#   byte1 = delta x-axis
#   byte2 = delta y-axis
#   byte3 = delta scroll wheel


def move(timeout=10):
    """Send mouse X & Y reported data from the Pinnacle touch controller
    until there's no input for a period of ``timeout`` seconds."""
    print(
        "Trackpad acting as a USB mouse device until", timeout, "seconds of inactivity."
    )
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        while trackpad.available():
            trackpad.read(data)
            data.x *= -1  # invert x-axis
            mouse.send_report(data.buffer)
            start = time.monotonic()  # reset timeout

    mouse.send_report(b"\x00" * 4)  # release buttons (just in case)


def set_role():
    """Set the role using stdin stream. Arguments for functions can be
    specified using a space delimiter (e.g. 'M 10' calls `move(10)`)
    """
    user_input = (
        input(
            "\n*** Enter 'M' to control the mouse with the trackpad."
            "\n*** Enter 'Q' to quit example.\n"
        )
        or "?"
    ).split()
    if user_input[0].upper().startswith("M"):
        move(*[int(x) for x in user_input[1:2]])
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
    print("\nRun move() to control the mouse with the trackpad.")
