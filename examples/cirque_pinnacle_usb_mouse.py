"""
This example uses CircuitPython's built-in `usb_hid` API
to emulate a mouse with the Cirque circle trackpad.

NOTE: This example won't work on Linux (eg. using Raspberry Pi GPIO pins).
"""
import time
import board
from digitalio import DigitalInOut
import usb_hid
from circuitpython_cirque_pinnacle import (
    PinnacleTouchSPI,
    PinnacleTouchI2C,  # noqa: imported-but-unused
    RELATIVE,
    RelativeReport,
)

dr_pin = DigitalInOut(board.D7)
# NOTE Specifying the optional keyword argument ``dr_pin`` to the
# constructor expedites ``read()`` when using Absolute or Relative modes

# if using a trackpad configured for SPI
spi = board.SPI()
ss_pin = DigitalInOut(board.D2)
trackpad = PinnacleTouchSPI(spi, ss_pin, dr_pin=dr_pin)
# if using a trackpad configured for I2C
# i2c = board.I2C()
# trackpad = PinnacleTouchI2C(i2c, dr_pin=dr_pin)

trackpad.data_mode = RELATIVE  # ensure mouse mode is enabled

mouse = None
for dev in usb_hid.devices:
    # be sure we're grabbing the mouse singleton
    if dev.usage == 2 and dev.usage_page == 1:
        mouse = dev
# mouse.send_report() takes a 4 byte buffer in which
#   byte0 = buttons in which
#       bit5 = back, bit4 = forward, bit2 = middle, bit1 = right, bit0 = left
#   byte1 = delta x-axis
#   byte2 = delta y-axis
#   byte3 = delta scroll wheel
if mouse is None:
    raise OSError("mouse HID device not available.")


def move(timeout=10):
    """Send mouse X & Y reported data from the Pinnacle touch controller
    until there's no input for a period of ``timeout`` seconds."""
    print("acting as a USB mouse device")
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if trackpad.available():
            data: RelativeReport = trackpad.read()
            # swap and invert axes
            temp = data.x
            data.x = data.y * -1
            data.y = temp * -1
            mouse.send_report(data.buffer)
            start = time.monotonic()  # reset timeout

    mouse.send_report(b"\x00" * 4)  # release buttons (just in case)


def set_role():
    """Set the role using stdin stream. Timeout arg for slave() can be
    specified using a space delimiter (e.g. 'M 10' calls `move(10)`)
    """
    user_input = (
        input(
            "*** Enter 'M' to control the mouse with the trackpad.\n"
            "*** Enter 'Q' to quit example.\n"
        )
        or "?"
    )
    user_input = user_input.split()
    if user_input[0].upper().startswith("M"):
        move(*[int(x) for x in user_input[1:2]])
        return True
    if user_input[0].upper().startswith("Q"):
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


print("    Cirque Pinnacle absolute mode")

if __name__ == "__main__":
    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down trackpad...")
else:
    print("    Run move() to control the mouse with the trackpad.")
