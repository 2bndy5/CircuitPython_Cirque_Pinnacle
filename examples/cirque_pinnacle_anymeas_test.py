""" a test example using SPI to read ADC measurements from the Pinnacle touch
controller in "AnyMeas" mode"""
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
trackpad.data_mode = DataModes.ANYMEAS

# setup toggle and polarity bits for measuring with PNP gate muxing
class MeasVector:
    """A blueprint matrix used to manipulate the measurements' vector"""
    def __init__(self, toggle, polarity):
        self.toggle = toggle
        self.polarity = polarity

vectors = []
# This toggles Y0 only and toggles it positively
vectors.append(MeasVector(0x00010000, 0x00010000))
# This toggles Y0 only and toggles it negatively
vectors.append(MeasVector(0x00010000, 0x00000000))
# This toggles X0 only and toggles it positively
vectors.append(MeasVector(0x00000001, 0x00000000))
# This toggles X16 only and toggles it positively
vectors.append(MeasVector(0x00008000, 0x00000000))
# This toggles Y0-Y7 negative and X0-X7 positive
vectors.append(MeasVector(0x00FF00FF, 0x000000FF))

# Calculate base compensation on startup
compensation = [0] * len(vectors)
for i, v in enumerate(vectors):
    for _ in range(5):  # take 5 measurements, then average them together
        compensation[i] += trackpad.measure_adc(v.toggle, v.polarity)
    compensation[i] /= 5

def take_measurements(timeout=10):
    """read ``len(vectors)`` number of measurements and print results for
    ``timeout`` number of seconds."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        for j, vect in enumerate(vectors):
            result = unpack('H', trackpad.measure_adc(vect.toggle, vect.polarity))
            print("measure {}: {}".format(i, result))
