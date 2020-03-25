"""
A driver class for the Cirque Pinnacle ASIC on the Cirque capacitve touch
based circular trackpads.
"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle.git"
from time import sleep
from struct import pack, unpack
from adafruit_bus_device.spi_device import SPIDevice
from adafruit_bus_device.i2c_device import I2CDevice

RELATIVE = 0x00
ANYMEAS = 0x01
ABSOLUTE = 0x02
GAIN_100 = 0xC0
GAIN_133 = 0x80
GAIN_166 = 0x40
GAIN_200 = 0x00
FREQ_0 = 0x02
FREQ_1 = 0x03
FREQ_2 = 0x04
FREQ_3 = 0x05
FREQ_4 = 0x06
FREQ_5 = 0x07
FREQ_6 = 0x09
FREQ_7 = 0x0B
MUX_REF1 = 0x10
MUX_REF0 = 0x08
MUX_PNP = 0x04
MUX_NPN = 0x01
CRTL_REPEAT = 0x80
CRTL_PWR_IDLE = 0x40

class PinnacleTouch:
    """The abstract base class for driving the Pinnacle ASIC."""
    def __init__(self, dr_pin=None):
        self.dr_pin = dr_pin
        if dr_pin is not None:
            self.dr_pin.switch_to_input()
        firmware_id, firmware_ver = self._rap_read_bytes(0, 2)
        if firmware_id != 7 or firmware_ver != 0x3A:
            raise OSError("Cirque Pinnacle ASIC not responding")
        # init internal attributes w/ factory defaults after power-on-reset
        self._mode = 0  # 0 means relative mode which is factory default after power-on-reset
        self.detect_finger_stylus()
        self._rap_write(0x0A, 30)  # z-idle packet count
        self._rap_write_bytes(3, [0, 1, 2]) # configure relative (& absolute mode)
        self.set_adc_gain(0)
        self.calibrate(True)  # enables all compensations

    @property
    def feed_enable(self):
        """This `bool` attribute controls if the touch/button event data is
        reported (`True`) or not (`False`)."""
        return bool(self._rap_read(4) & 1)

    @feed_enable.setter
    def feed_enable(self, is_on):
        is_enabled = self._rap_read(4)
        if is_enabled & 1 != is_on:  # save ourselves the unnecessary transaction
            is_enabled = (is_enabled & 0xFE) | is_on
            self._rap_write(4, is_enabled)

    @property
    def data_mode(self):
        """This attribute controls which mode the data report is configured for."""
        return self._mode

    @data_mode.setter
    def data_mode(self, mode):
        if mode not in (ANYMEAS, RELATIVE, ABSOLUTE):
            raise ValueError("unrecognised input value for data mode. Use 0 for Relative mode, "
                             "1 for AnyMeas mode, or 2 for Absolute mode.")
        self._mode = mode
        sys_config = self._rap_read(3) & 0xE7  # clear flags specific to AnyMeas mode
        if mode in (RELATIVE, ABSOLUTE):  # for relative/absolute mode
            if self.data_mode == ANYMEAS:  # if leaving AnyMeas mode
                self._rap_write_bytes(3, [
                    sys_config,
                    1 | mode,  # set new mode's flag & enables feed
                    2])  # disables taps in Relative mode
                self.sample_rate = 100
                self._rap_write(7, 0x1E)  # enables all compensations
                self._rap_write(0x0A, 30)  # 30 z-idle packets
            else:  # ok to write appropriate mode
                self._rap_write(4, 1 | mode)
        else:  # for AnyMeas mode
            if self.dr_pin is None:  # this mode requires the use of DR IRQ pin
                raise AttributeError("Data Ready digital input (interupt) pin is None, "
                                     "please specify the dr_pin attribute for AnyMeas mode")
            # disable tracking computations for AnyMeas mode
            self._rap_write(3, sys_config | 0x08)
            sleep(0.01)  # wait 10 ms for tracking measurements to expire
            self.anymeas_mode_config()  # configure registers for the AnyMeas mode

    @property
    def hard_configured(self):
        """This `bool` attribute can be used to inform applications about factory
        customized hardware configuration."""
        return bool(self._rap_read(0x1f))

    def relative_mode_config(self, rotate90=False, glide_extend=True,
                             secondary_tap=True, taps=False, intellimouse=False):
        """Configure settings specific to Relative mode (AKA Mouse mode) data reporting."""
        if self.data_mode == RELATIVE:
            config2 = rotate90 << 7 | (not glide_extend) << 4 | (
                not secondary_tap) << 2 | (not taps) << 1 | intellimouse
            self._rap_write(5, config2)

    def absolute_mode_config(self, z_idle_count=30, invert_x=False, invert_y=False):
        """Configure settings specific to Absolute mode (reports axis positions)."""
        if self.data_mode == ABSOLUTE:
            self._rap_write(0x0A, max(0, min(z_idle_count, 255)))
            config1 = (self._rap_read(4) & 0x3F) | (invert_y << 7) | (invert_x << 6)
            self._rap_write(4, config1)

    def report(self, only_new=True):
        """This function will return touch event data from the Pinnacle ASIC (including empty
        packets on ending of a touch event)."""
        if self._mode == ANYMEAS:
            return None
        return_vals = None
        data_ready = False
        if only_new:
            if self.dr_pin is None:
                data_ready = self._rap_read(2) & 4
            else:
                data_ready = self.dr_pin.value
        if (only_new and data_ready) or not only_new:
            if self.data_mode == ABSOLUTE:  # if absolute mode
                temp = self._rap_read_bytes(0x12, 6)
                return_vals = [temp[0] & 0x3F,  # buttons
                               ((temp[4] & 0x0F) << 8) | temp[2],  # x
                               ((temp[4] & 0xF0) << 4) | temp[3],  # y
                               temp[5] & 0x3F]  # z
                return_vals[1] = max(128, min(1920, return_vals[1]))
                return_vals[2] = max(64, min(1472, return_vals[2]))
            elif self.data_mode == RELATIVE:  # if in relative mode
                temp = self._rap_read_bytes(0x12, 4)
                return_vals = bytearray([temp[0] & 7, temp[1], temp[2]])
                return_vals += bytes([temp[3]])
            self.clear_flags()
        return return_vals

    def clear_flags(self):
        """This function clears the "Data Ready" flag which is reflected with the ``dr_pin``."""
        self._rap_write(2, 0)
        # delay 50 microseconds per official example from Cirque
        sleep(0.00005)

    @property
    def allow_sleep(self):
        """This attribute specifies if the Pinnacle ASIC is allowed to sleep after about 5 seconds
        of idle (no input event)."""
        return bool(self._rap_read(3) & 4)

    @allow_sleep.setter
    def allow_sleep(self, is_enabled):
        self._rap_write(3, (self._rap_read(3) & 0xFB) | (is_enabled << 2))

    @property
    def shutdown(self):
        """This attribute controls power of the Pinnacle ASIC."""
        return bool(self._rap_read(3) & 2)

    @shutdown.setter
    def shutdown(self, is_off):
        self._rap_write(3, (self._rap_read(3) & 0xFD) | (is_off << 1))

    @property
    def sample_rate(self):
        """This attribute controls how many samples (of data) per second are reported."""
        return self._rap_read(9)

    @sample_rate.setter
    def sample_rate(self, val):
        if self.data_mode != ANYMEAS:
            if val in (200, 300):
                # disable palm & noise compensations
                self._rap_write(6, 10)
                reload_timer = 6 if val == 300 else 0x09
                self._era_write_bytes(0x019E, reload_timer, 2)
                val = 0
            else:
                # enable palm & noise compensations
                self._rap_write(6, 0)
                self._era_write_bytes(0x019E, 0x13, 2)
                val = val if val in (100, 80, 60, 40, 20, 10) else 100
            self._rap_write(9, val)

    def detect_finger_stylus(self, enable_finger=True, enable_stylus=True, sample_rate=100):
        """This function will configure the Pinnacle ASIC to detect either finger,
        stylus, or both."""
        finger_stylus = self._era_read(0x00EB)
        finger_stylus |= (enable_stylus << 2) | enable_finger
        self._era_write(0x00EB, finger_stylus)
        self.sample_rate = sample_rate

    def calibrate(self, run, tap=True, track_error=True, nerd=True, background=True):
        """Set calibration parameters when the Pinnacle ASIC calibrates itself."""
        if self.data_mode != ANYMEAS:
            cal_config = tap << 4 | track_error << 3 | nerd << 2 | background << 1
            self._rap_write(7, cal_config | run)
            if run:
                while self._rap_read(7) & 1:
                    pass  # calibration is running
                self.clear_flags() # now that calibration is done

    @property
    def calibration_matrix(self):
        """This attribute returns a `list` of the 46 signed 16-bit (short) values stored in the
        Pinnacle ASIC's memory that is used for taking measurements."""
        # combine every 2 bytes from resulting buffer to form a list of signed 16-bits integers
        return list(unpack('46h', self._era_read_bytes(0x01DF, 92)))

    @calibration_matrix.setter
    def calibration_matrix(self, matrix):
        if len(matrix) < 46:  # padd short matrices w/ 0s
            matrix += [0] * (46 - len(matrix))
        # save time on bus interactions by pausing feed now
        prev_feed_state = self.feed_enable
        self.feed_enable = False # required for ERA functions anyway
        # be sure to not write more than allowed
        for index in range(46):
            # write 2 bytes at a time
            buf = pack('h', matrix[index])
            self._era_write(0x01DF + index * 2, buf[0])
            self._era_write(0x01DF + index * 2 + 1, buf[1])
        self.feed_enable = prev_feed_state  # resume previous feed state

    def set_adc_gain(self, sensitivity):
        """Sets the ADC gain in range [0,3] to enhance performance based on the overlay type"""
        if 0 <= sensitivity < 4:
            val = self._era_read(0x0187) & 0x3F
            val |= sensitivity << 6
            self._era_write(0x0187, val)
        else:
            raise ValueError("{} is out of bounds [0,3]".format(sensitivity))

    def tune_edge_sensitivity(self, x_axis_wide_z_min=0x04, y_axis_wide_z_min=0x03):
        """Changes thresholds to improve detection of fingers."""
        self._era_write(0x0149, x_axis_wide_z_min)
        self._era_write(0x0168, y_axis_wide_z_min)

    def anymeas_mode_config(self, gain=GAIN_200, frequency=FREQ_0,
                            sample_length=512, mux_ctrl=MUX_PNP, apperture_width=500,
                            ctrl_pwr_cnt=1):
        """This function configures the Pinnacle ASIC to output raw ADC measurements."""
        if self.data_mode == ANYMEAS:
            anymeas_config = [2, 3, 4, 0, 4, 0, 19, 0, 0, 1]
            anymeas_config[0] = gain | frequency
            anymeas_config[1] = (max(1, min(int(sample_length / 128), 3)))
            anymeas_config[2] = mux_ctrl
            anymeas_config[4] = max(2, min(int(apperture_width / 125), 15))
            anymeas_config[9] = ctrl_pwr_cnt
            self._rap_write_bytes(5, anymeas_config)
            self._rap_write_bytes(0x13, [0] * 8)
            self.clear_flags()

    def measure_adc(self, bits_to_toggle, toggle_polarity):
        """This function instigates and returns the measurements (a signed short) from the Pinnacle
        ASIC's ADC (Analog to Digital Converter) matrix (only applies to AnyMeas mode)."""
        if self._mode != ANYMEAS:
            return None
        tog_pol = []  # assemble list of register buffers
        for i in range(3, -1, -1):
            tog_pol.append((bits_to_toggle >> (i * 8)) & 0xFF)
        for i in range(3, -1, -1):
            tog_pol.append((toggle_polarity >> (i * 8)) & 0xFF)
        # write toggle and polarity parameters to register 0x13 - 0x1A (PACKET_BYTE_1 + 8)
        self._rap_write_bytes(0x13, tog_pol)

        # initiate measurements
        self._rap_write(3, self._rap_read(3) | 0x18)
        while not self.dr_pin.value:  # wait till measurements are complete
            pass  # Pinnacle is still computing
        result = self._rap_read_bytes(0x11, 2)
        self.clear_flags()
        return bytearray(result)

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
        self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write_bytes(0x1C, [reg >> 8, reg & 0xff])
        self._rap_write(0x1E, 1)  # indicate reading only 1 byte
        while self._rap_read(0x1E):  # read until reg == 0
            pass  # also sets Command Complete flag in Status register
        buf = self._rap_read(0x1B)  # get value
        self.clear_flags()
        self.feed_enable = prev_feed_state  # resume previous feed state
        return buf

    def _era_read_bytes(self, reg, numb_bytes):
        buf = b''
        prev_feed_state = self.feed_enable
        self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write_bytes(0x1C, [reg >> 8, reg & 0xff])
        for _ in range(numb_bytes):
            self._rap_write(0x1E, 5)  # indicate reading sequential bytes
            while self._rap_read(0x1E):  # read until reg == 0
                pass  # also sets Command Complete flag in Status register
            buf += bytes([self._rap_read(0x1B)])  # get value
            self.clear_flags()
        self.feed_enable = prev_feed_state  # resume previous feed state
        return buf

    def _era_write(self, reg, value):
        prev_feed_state = self.feed_enable
        self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write(0x1B, value)  # write value
        self._rap_write_bytes(0x1C, [reg >> 8, reg & 0xff])
        self._rap_write(0x1E, 2)  # indicate writing only 1 byte
        while self._rap_read(0x1E):  # read until reg == 0
            pass  # also sets Command Complete flag in Status register
        self.clear_flags()
        self.feed_enable = prev_feed_state  # resume previous feed state

    def _era_write_bytes(self, reg, value, numb_bytes):
        # NOTE this is rarely used as it only writes 1 value to multiple registers
        prev_feed_state = self.feed_enable
        self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write(0x1B, value)  # write value
        self._rap_write_bytes(0x1C, [reg >> 8, reg & 0xff])
        self._rap_write(0x1E, 0x0A)  # indicate writing sequential bytes
        for _ in range(numb_bytes):
            while self._rap_read(0x1E):  # read until reg == 0
                pass  # also sets Command Complete flag in Status register
            self.clear_flags()
        self.feed_enable = prev_feed_state  # resume previous feed state

# pylint: disable=no-member,too-few-public-methods
class PinnacleTouchI2C(PinnacleTouch):
    """Parent class for interfacing with the Pinnacle ASIC via the I2C protocol."""
    def __init__(self, i2c, address=0x2A, dr_pin=None):
        self._i2c = I2CDevice(i2c, (address << 1))  # per datasheet
        super(PinnacleTouchI2C, self).__init__(dr_pin=dr_pin)

    def _rap_read(self, reg):
        return self._rap_read_bytes(reg)

    def _rap_read_bytes(self, reg, numb_bytes=1):
        self._i2c.device_address &= 0xFE  # set write flag
        buf = bytearray([reg | 0xA0])  # per datasheet
        with self._i2c as i2c:
            i2c.write(buf)  # includes a STOP condition
        self._i2c.device_address |= 1  # set read flag
        buf = bytearray(numb_bytes)  # for accumulating response(s)
        with self._i2c as i2c:
            # auto-increments register for each byte read
            i2c.readinto(buf)
        return buf

    def _rap_write(self, reg, value):
        self._rap_write_bytes(reg, [value])

    def _rap_write_bytes(self, reg, values):
        self._i2c.device_address &= 0xFE  # set write flag
        buf = b''
        for index, byte in enumerate(values):  # works for bytearrays/lists/tuples
            # Pinnacle doesn't auto-increment register addresses for I2C write operations
            # Also truncate int elements of a list/tuple
            buf += bytearray([(reg + index) | 0x80, byte & 0xFF])
        with self._i2c as i2c:
            i2c.write(buf)

class PinnacleTouchSPI(PinnacleTouch):
    """Parent class for interfacing with the Pinnacle ASIC via the SPI protocol."""
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
        # using auto-increment method
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
