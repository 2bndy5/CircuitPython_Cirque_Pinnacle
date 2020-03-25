# see license and copyright information in glidepoint.py of this directory
# pylint: disable=missing-class-docstring,missing-function-docstring,missing-module-docstring
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle.git"
import time
from adafruit_bus_device.spi_device import SPIDevice
from adafruit_bus_device.i2c_device import I2CDevice

RELATIVE = 0x00
ABSOLUTE = 0x02

class PinnacleTouch:
    def __init__(self, dr_pin=None):
        self.dr_pin = dr_pin
        if dr_pin is not None:
            self.dr_pin.switch_to_input()
        firmware_id, firmware_ver = self._rap_read_bytes(0, 2)
        if firmware_id != 7 or firmware_ver != 0x3A:
            raise OSError("Cirque Pinnacle ASIC not responding")
        self._mode = 0
        self.sample_rate = 100
        self._rap_write(0x0A, 30)
        self._rap_write_bytes(3, [0, 1, 2])
        self.clear_flags()

    @property
    def feed_enable(self):
        return bool(self._rap_read(4) & 1)

    @feed_enable.setter
    def feed_enable(self, is_on):
        is_enabled = self._rap_read(4)
        if is_enabled & 1 != is_on:
            is_enabled = (is_enabled & 0xFE) | is_on
            self._rap_write(4, is_enabled)

    @property
    def data_mode(self):
        return self._mode

    @data_mode.setter
    def data_mode(self, mode):
        if mode not in (RELATIVE, ABSOLUTE):
            raise ValueError("unrecognized input value for data mode. Use 0 for Relative mode, "
                             "or 2 for Absolute mode.")
        self._mode = mode
        self._rap_write(4, 1 | mode)

    @property
    def hard_configured(self):
        return bool(self._rap_read(0x1f))

    def relative_mode_config(self, rotate90=False, glide_extend=True,
                             secondary_tap=True, taps=False, intellimouse=False):
        config2 = rotate90 << 7 | (not glide_extend) << 4 | (
            not secondary_tap) << 2 | (not taps) << 1 | intellimouse
        self._rap_write(5, config2)

    def absolute_mode_config(self, z_idle_count=30, invert_x=False, invert_y=False):
        self._rap_write(0x0A, max(0, min(z_idle_count, 255)))
        config1 = (self._rap_read(4) & 0x3F) | (invert_y << 7) | (invert_x << 6)
        self._rap_write(4, config1)

    def report(self, only_new=True):
        return_vals = None
        data_ready = False
        if only_new:
            if self.dr_pin is None:
                data_ready = self._rap_read(2) & 4
            else:
                data_ready = self.dr_pin.value
        if (only_new and data_ready) or not only_new:
            if self.data_mode == ABSOLUTE:
                temp = self._rap_read_bytes(0x12, 6)
                return_vals = [temp[0] & 0x3F,
                               ((temp[4] & 0x0F) << 8) | temp[2],
                               ((temp[4] & 0xF0) << 4) | temp[3],
                               temp[5] & 0x3F]
                return_vals[1] = max(128, min(1920, return_vals[1]))
                return_vals[2] = max(64, min(1472, return_vals[2]))
            elif self.data_mode == RELATIVE:
                temp = self._rap_read_bytes(0x12, 4)
                return_vals = bytearray([temp[0] & 7, temp[1], temp[2]])
                return_vals += bytes([temp[3]])
            self.clear_flags()
        return return_vals

    def clear_flags(self):
        self._rap_write(2, 0)
        time.sleep(0.00005)

    @property
    def allow_sleep(self):
        return bool(self._rap_read(3) & 4)

    @allow_sleep.setter
    def allow_sleep(self, is_enabled):
        self._rap_write(3, (self._rap_read(3) & 0xFB) | (is_enabled << 2))

    @property
    def shutdown(self):
        return bool(self._rap_read(3) & 2)

    @shutdown.setter
    def shutdown(self, is_off):
        self._rap_write(3, (self._rap_read(3) & 0xFD) | (is_off << 1))

    @property
    def sample_rate(self):
        return self._rap_read(9)

    @sample_rate.setter
    def sample_rate(self, val):
        if val in (200, 300):
            self._rap_write(6, 10)
            reload_timer = 6 if val == 300 else 0x09
            self._era_write(0x019E, reload_timer)
            self._era_write(0x019F, reload_timer)
            val = 0
        else:
            self._rap_write(6, 0)
            self._era_write(0x019E, 0x13)
            self._era_write(0x019F, 0x13)
            val = val if val in (100, 80, 60, 40, 20, 10) else 100
        self._rap_write(9, val)

    def _rap_read(self, reg):
        raise NotImplementedError()

    def _rap_read_bytes(self, reg, numb_bytes):
        raise NotImplementedError()

    def _rap_write(self, reg, value):
        raise NotImplementedError()

    def _rap_write_bytes(self, reg, values):
        raise NotImplementedError()

    def _era_read(self, reg):
        prev_feed_state = self.feed_enable
        self.feed_enable = False
        self._rap_write_bytes(0x1C, [reg >> 8, reg & 0xff])
        self._rap_write(0x1E, 1)
        while self._rap_read(0x1E):
            pass
        buf = self._rap_read(0x1B)
        self.clear_flags()
        self.feed_enable = prev_feed_state
        return buf

    def _era_read_bytes(self, reg, numb_bytes):
        buf = b''
        prev_feed_state = self.feed_enable
        self.feed_enable = False
        self._rap_write_bytes(0x1C, [reg >> 8, reg & 0xff])
        for _ in range(numb_bytes):
            self._rap_write(0x1E, 5)
            while self._rap_read(0x1E):
                pass
            buf += bytes([self._rap_read(0x1B)])
            self.clear_flags()
        self.feed_enable = prev_feed_state
        return buf

    def _era_write(self, reg, value):
        prev_feed_state = self.feed_enable
        self.feed_enable = False
        self._rap_write(0x1B, value)
        self._rap_write_bytes(0x1C, [reg >> 8, reg & 0xff])
        self._rap_write(0x1E, 2)
        while self._rap_read(0x1E):
            pass
        self.clear_flags()
        self.feed_enable = prev_feed_state

# pylint: disable=no-member
class PinnacleTouchI2C(PinnacleTouch):
    def __init__(self, i2c, address=0x2A, dr_pin=None):
        self._i2c = I2CDevice(i2c, (address << 1))
        super(PinnacleTouchI2C, self).__init__(dr_pin=dr_pin)

    def _rap_read(self, reg):
        return self._rap_read_bytes(reg)

    def _rap_read_bytes(self, reg, numb_bytes=1):
        self._i2c.device_address &= 0xFE
        buf = bytearray([reg | 0xA0])
        with self._i2c as i2c:
            i2c.write(buf)
        self._i2c.device_address |= 1
        buf = bytearray(numb_bytes)
        with self._i2c as i2c:
            i2c.readinto(buf)
        return buf

    def _rap_write(self, reg, value):
        self._rap_write_bytes(reg, [value])

    def _rap_write_bytes(self, reg, values):
        self._i2c.device_address &= 0xFE
        buf = b''
        for index, byte in enumerate(values):
            buf += bytearray([(reg + index) | 0x80, byte & 0xFF])
        with self._i2c as i2c:
            i2c.write(buf)

class PinnacleTouchSPI(PinnacleTouch):
    def __init__(self, spi, ss_pin, dr_pin=None):
        self._spi = SPIDevice(spi, chip_select=ss_pin, baudrate=12000000, phase=1)
        super(PinnacleTouchSPI, self).__init__(dr_pin=dr_pin)

    def _rap_read(self, reg):
        buf_out = bytearray([reg | 0xA0]) + b'\xFB' * 3
        buf_in = bytearray(len(buf_out))
        with self._spi as spi:
            spi.write_readinto(buf_out, buf_in)
        return buf_in[3]

    def _rap_read_bytes(self, reg, numb_bytes):
        buf_out = bytearray([reg | 0xA0]) + b'\xFC' * \
            (1 + numb_bytes) + b'\xFB'
        buf_in = bytearray(len(buf_out))
        with self._spi as spi:
            spi.write_readinto(buf_out, buf_in)
        return buf_in[3:]

    def _rap_write(self, reg, value):
        buf = bytearray([(reg | 0x80), value])
        with self._spi as spi:
            spi.write(buf)

    def _rap_write_bytes(self, reg, values):
        for i, val in enumerate(values):
            self._rap_write(reg + i, val)
