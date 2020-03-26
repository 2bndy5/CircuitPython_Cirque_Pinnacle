""" a test example using SPI to read ADC measurements from the Pinnacle touch
controller in "AnyMeas" mode"""
import time
from struct import unpack
import board
from digitalio import DigitalInOut
# this example does NOT work with glideoint_lite.py
from circuitpython_cirque_pinnacle.glidepoint import PinnacleTouchSPI, ANYMEAS

spi = board.SPI()
ss_pin = DigitalInOut(board.D7)
dr_pin = DigitalInOut(board.D2)

# NOTE The dr_pin is a required arg to use AnyMeas mode
tpad = PinnacleTouchSPI(spi, ss_pin, dr_pin=dr_pin)
# if dr_pin was not specified upon instantiation.
# this command will raise an AttributeError exception
tpad.data_mode = ANYMEAS

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

# tell pylint this example script is able to print results without compensation
# pylint: disable=redefined-outer-name
idle_vectors = [0] * len(vectors)
def compensate(count=5):
    """take ``count`` measurements, then average them together  """
    idle_vectors = [0] * len(vectors)
    for i, v in enumerate(vectors):
        for _ in range(count):  #
            idle_vectors[i] += unpack('h', tpad.measure_adc(v.toggle, v.polarity))[0]
        idle_vectors[i] /= count
        print("compensation {}: {}".format(i, idle_vectors[i]))

def take_measurements(timeout=10):
    """read ``len(vectors)`` number of measurements and print results for
    ``timeout`` number of seconds."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        for i, v in enumerate(vectors):
            result = unpack('h', tpad.measure_adc(v.toggle, v.polarity))[0]
            print("vector{}: {}".format(i, result - idle_vectors[i]), end='\t')
        print()
