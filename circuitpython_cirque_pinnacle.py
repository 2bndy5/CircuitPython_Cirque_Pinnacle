# The MIT License (MIT)
#
# Copyright (c) 2020 Brendan Doherty
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
PinnacleTouch API
=================

A driver class for the Cirque Pinnacle ASIC on the Cirque capacitve touch
based circular trackpads.
"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle.git"
import time
import struct
from adafruit_bus_device.spi_device import SPIDevice
from adafruit_bus_device.i2c_device import I2CDevice

# internal registers
# pylint: disable=bad-whitespace,too-few-public-methods
PINNACLE_STATUS           = 0x02  # Contains status flags about the state of Pinnacle
PINNACLE_SYS_CONFIG       = 0x03  # Contains system operation and configuration bits
PINNACLE_FEED_CONFIG1     = 0x04  # Contains feed operation and configuration bits
PINNACLE_FEED_CONFIG2     = 0x05  # Contains feed operation and configuration bits
PINNACLE_CALIBRATE_CONFIG = 0x07  # Contains calibration configuration bits
PINNACLE_SAMPLE_RATE      = 0x09  # Number of samples generated per second
PINNACLE_Z_IDLE           = 0x0A  # Number of Z=0 packets sent when Z goes from >0 to 0
PINNACLE_PACKET_BYTE_0    = 0x12  # trackpad Data
PINNACLE_ERA_VALUE        = 0x1B  # Value for extended register access
PINNACLE_ERA_ADDR_HIGH    = 0x1C  # High byte of 16 bit extended register address
PINNACLE_ERA_ADDR_LOW     = 0x1D  # Low byte of 16 bit extended register address
PINNACLE_ERA_CTRL         = 0x1E  # Control of extended register access

# constants used for bitwise configuration
class DataModes:
    """Allowed symbols for configuring the Pinanacle ASIC's data
    reporting/measurements."""
    RELATIVE = 0x00  #: Alias symbol for specifying Relative mode (AKA Mouse mode).
    ANYMEAS  = 0x01  #: Alias symbol for specifying "AnyMeas" mode (raw ADC measurement)
    ABSOLUTE = 0x02  #: Alias symbol for specifying Absolute mode (axis positions)

class AnyMeasGain:
    """Allowed ADC gain configurations of AnyMeas mode. The percentages defined here are
    approximate values."""
    GAIN_100 = 0xC0  #: around 100% gain
    GAIN_133 = 0x80  #: around 133% gain
    GAIN_166 = 0x40  #: around 166% gain
    GAIN_200 = 0x00  #: around 200% gain

class AnyMeasFreq:
    """Allowed frequency configurations of AnyMeas mode. The frequencies defined here are
    approximated based on an aperture width of 500 nanoseconds. If the ``aperture_width``
    parameter to `anymeas_mode_config()` specified is less than 500 nanoseconds, then the
    frequency will be larger than what is described here (& vice versa).
    """
    FREQ_0 = 0x02  #: frequency around 500,000Hz
    FREQ_1 = 0x03  #: frequency around 444,444Hz
    FREQ_2 = 0x04  #: frequency around 400,000Hz
    FREQ_3 = 0x05  #: frequency around 363,636Hz
    FREQ_4 = 0x06  #: frequency around 333,333Hz
    FREQ_5 = 0x07  #: frequency around 307,692Hz
    FREQ_6 = 0x09  #: frequency around 267,000Hz
    FREQ_7 = 0x0B  #: frequency around 235,000Hz

class AnyMeasMux:
    """Allowed muxing gate polarity and reference capacitor configurations of AnyMeas mode.
    Combining these values (with ``+`` operator) is allowed.

    .. note:: The sign of the measurements taken in AnyMeas mode is inverted depending on which
        muxing gate is specified (when specifying an individual gate polarity).
    """
    MUX_REF1 = 0x10  #: enables a builtin capacitor (~0.5pF). See note in `measure_adc()`
    MUX_REF0 = 0x08  #: enables a builtin capacitor (~0.25pF). See note in `measure_adc()`
    MUX_PNP  = 0x04  #: enable PNP sense line
    MUX_NPN  = 0x01  #: enable NPN sense line

class AnyMeasCrtl:
    """These constants control the number of measurements performed on a single call to
    `measure_adc()`. The number of measurements can range [0, 63]."""
    CRTL_REPEAT = 0x80  #: required for more than 1 measurement
    CRTL_PWR_IDLE = 0x40  #: triggers low power mode (sleep) after completing measurements
# pylint: enable=bad-whitespace,too-few-public-methods

class PinnacleTouch:
    """
    The abstract base class for driving the Pinnacle ASIC.

    :param ~microcontroller.Pin dr_pin: The input pin connected to the Pinnacle ASIC's "Data
        Ready" pin. If this parameter is not specified, then the SW_DR (software data ready) flag
        of the STATUS register is used to detirmine if the data being reported is new.

        .. important:: This parameter must be specified if your application is going to use the
            Pinnacle ASIC's :attr:`~circuitpython_cirque_pinnacle.DataModes.ANYMEAS`
            mode (a rather experimental measuring of raw ADC values).
    """

    def __init__(self, dr_pin=None):
        self.dr_pin = dr_pin
        if dr_pin is not None:
            self.dr_pin.switch_to_input()

        # perform hardware check
        firmware_id, firmware_ver = self._rap_read_bytes(0, 2)
        if firmware_id != 7 or firmware_ver != 0x3A:
            raise OSError("Cirque Pinnacle ASIC not responding")

        # init internal attributes w/ factory defaults after power-on-reset
        self._hco = bool(self._rap_read(0x1F))  # is hardware custom configured?
        self._sys_config = 0  # ignoring read-only reset flag (bit 0)
        self._feed_config1 = 1  # enables feed & sets to relative mode
        self._feed_config2 = 2  # disables taps in relative mode
        self._cal_config = 14  # enables all compensations
        self._sample_rate = 0  # just a place holder til detect_finger_stylus() call
        self._z_idle_count = 30
        self._finger_stylus = 0  # just a place holder til detect_finger_stylus() call
        self._sensitivity = 0  # most sensitive ADC gain fro relative/abs mode
        self._mode = 0  # 0 means relative mode which is factory default after power-on-reset
        # init internal buffer used for anymeas_mode_config() using defaults from official example
        self._anymeas_config = [2, 3, 4, 0, 4, 0, 19, 0, 0, 1]
        self.clear_flags()
        # write to all internal attributes to registers
        self.detect_finger_stylus() # also writes to FEED_CONFIG3 & SAMPLE_RATE registers
        self._rap_write(PINNACLE_CALIBRATE_CONFIG, self._cal_config)
        self._rap_write(PINNACLE_Z_IDLE, self._z_idle_count)
        self._rap_write_bytes(PINNACLE_SYS_CONFIG, [
            self._sys_config, self._feed_config1, self._feed_config2])
        self.set_adc_gain(self._sensitivity)

    def __enter__(self):
        self.clear_flags()
        if self.data_mode == DataModes.ANYMEAS:
            # disable tracking computations for AnyMeas mode & power up
            self._sys_config = (self._sys_config & 0xE5) | 0x08
            self._rap_write(PINNACLE_SYS_CONFIG, self._sys_config)
            time.sleep(0.01)  # wait 10 ms for tracking measurements to expire
            # dump self._anymeas_config to all 10 registers at once
            self._rap_write_bytes(PINNACLE_FEED_CONFIG2, self._anymeas_config)
            # clear 8 registers (used for toggle & polarity polynomials)
            self._rap_write_bytes(PINNACLE_PACKET_BYTE_0 + 1, [0] * 8)
        else:
            # power up & disable feed to save time/SPI transactions using ERA funcs
            self._feed_config1 &= 0xFE
            self._sys_config &= 0xE5
            # write to all internal attributes to registers
            self._rap_write_bytes(PINNACLE_SYS_CONFIG, [
                self._sys_config, self._feed_config1, self._feed_config2])
            self._era_write(0x0187, self._sensitivity)
            self.detect_finger_stylus(
                self._finger_stylus & 4, self._finger_stylus & 1, self._sample_rate)
            self._rap_write(PINNACLE_CALIBRATE_CONFIG, self._cal_config)
            self._rap_write(PINNACLE_Z_IDLE, self._z_idle_count)
            self.feed_enable = True
        self.clear_flags() # just to be sure
        return self

    def __exit__(self, *exc):
        self.shutdown = True
        return False

    @property
    def feed_enable(self):
        """This `bool` attribute controls if the touch data is reported (`True`) or not
        (`False`). This attribute does not apply to AnyMeas mode (only Relative & Absolute modes).
        """
        return bool(self._feed_config1 & 1)

    @feed_enable.setter
    def feed_enable(self, is_on):
        if self.feed_enable != is_on:  # save ourselves the unnecessary transaction
            self._feed_config1 = self._rap_read(PINNACLE_FEED_CONFIG1)
            self._feed_config1 = (self._feed_config1 & 0xFE) | is_on
            self._rap_write(PINNACLE_FEED_CONFIG1, self._feed_config1)

    @property
    def data_mode(self):
        """This attribute controls which mode the data report is configured for.

        Valid input values are :attr:`~circuitpython_cirque_pinnacle.DataModes.RELATIVE` for
        relative/mouse mode, :attr:`~circuitpython_cirque_pinnacle.DataModes.ABSOLUTE` for
        absolute positioning mode, or :attr:`~circuitpython_cirque_pinnacle.DataModes.ANYMEAS`
        (referred to as "AnyMeas" in specification sheets) mode for reading ADC values.

        :Returns:

            - ``0`` for Relative mode (AKA mouse mode)
            - ``1`` for AnyMeas mode (raw ADC measurements)
            - ``2`` for Absolute mode (X & Y axis positions)
        """
        return self._mode

    @data_mode.setter
    def data_mode(self, mode):
        if mode not in (DataModes.ANYMEAS, DataModes.RELATIVE, DataModes.ABSOLUTE):
            raise ValueError("unrecognised input value for data mode. Use 0 for Relative mode, "
                             "1 for AnyMeas mode, or 2 for Absolute mode.")
        if mode in (DataModes.RELATIVE, DataModes.ABSOLUTE):  # for relative/absolute mode
            if self.data_mode == DataModes.ANYMEAS:  # if leaving AnyMeas mode
                # reload user configuration
                self._mode = mode
                self._rap_write_bytes(PINNACLE_SYS_CONFIG, [
                    self._sys_config & 0xE7,  # clear flags specific to AnyMeas mode
                    (self._feed_config1 & 0xFD) | mode,  # set new mode's flag
                    self._feed_config2])  # Relative mode configs
                # next write to SAMPLE_RATE & FEED_CONFIG3 register
                self.sample_rate = self._sample_rate
                self._rap_write(PINNACLE_CALIBRATE_CONFIG, self._cal_config)
                self._rap_write(PINNACLE_Z_IDLE, self._z_idle_count)
            else:  # ok to write appropriate mode
                self._mode = mode
                self._feed_config1 = (self._feed_config1 & 0xFD) | mode
                self._rap_write(PINNACLE_FEED_CONFIG1, self._feed_config1)
        else:  # for AnyMeas mode
            if self.dr_pin is None:  # this mode requires the use of DR IRQ pin
                raise AttributeError("Data Ready digital input (interupt) pin is None, "
                                     "please specify the dr_pin attribute for AnyMeas mode")
            self._mode = mode  # allow for anymeas_mode_config() to do something
            # disable tracking computations for AnyMeas mode
            self._sys_config = (self._sys_config & 0xE7) | 0x08
            self._rap_write(PINNACLE_SYS_CONFIG, self._sys_config)
            time.sleep(0.01)  # wait 10 ms for tracking measurements to expire
            # now configure the AnyMeas mode to default values
            self.anymeas_mode_config()

    @property
    def hard_configured(self):
        """This `bool` attribute provides insight to applications about factory
        customized hardware configuration. see note about product labeling in
        `Model Labeling Scheme <index.html#cc>`_. (read only)

        :Returns:
            `True` if a 470K ohm resistor is populated at the junction labeled "R4"
        """
        return self._hco

    def relative_mode_config(self, rotate90=False, glide_extend=True,
                             secondary_tap=True, taps=False, intellimouse=False):
        """Set the configuration register for features specific to relative mode (AKA mouse mode)
        data reporting.

        :param bool rotate90: Specifies if the axis data is altered for 90 degree rotation before
            reporting it (essentially swaps the axis data). Default is `False`.
        :param bool glide_extend: A patended feature that allows the user to glide their finger off
            the edge of the sensor and continue gesture with the touch event. Default is `True`.
            This feature is only available if `hard_configured` is `False`.
        :param bool secondary_tap: Specifies if tapping in the top-left corner (depending on
            orientation) triggers the secondary button data. Defaults to `True`. This feature is
            only available if `hard_configured` is `False`.
        :param bool taps: Specifies if all taps should be reported (`True`) or not
            (`False`). Default is `True`. This affects ``secondary_tap`` option as well. The
            primary button (left mouse button) is emulated with a tap.
        :param bool intellimouse: Specifies if the data reported includes a byte about scroll data.
            Default is `False`. Because this flag is specific to scroll data, this feature is only
            available if `hard_configured` is `False`.
        """
        self._feed_config2 = rotate90 << 7 | (not glide_extend) << 4 | (
            not secondary_tap) << 2 | (not taps) << 1 | intellimouse
        self._rap_write(PINNACLE_FEED_CONFIG2, self._feed_config2)

    def absolute_mode_config(self, z_idle_count=30, invert_x=False, invert_y=False):
        """Set the configuration settings specific to Absolute mode (reports axis positions).
        (write only)

        This function only applies to Absolute mode, otherwise if `data_mode` is set to
        :attr:`~circuitpython_cirque_pinnacle.DataModes.ANYMEAS` or
        :attr:`~circuitpython_cirque_pinnacle.DataModes.RELATIVE`, then this function will take
        no affect until `data_mode` is set to
        :attr:`~circuitpython_cirque_pinnacle.DataModes.ABSOLUTE`.

        :param int z_idle_count: Specifies the number of empty packets (x-axis, y-axis, and z-axis
            are ``0``) reported (every 10 milliseconds) when there is no touch detected. Defaults
            to 30. This number is clamped to range [0, 255].
        :param bool invert_x: Specifies if the x-axis data is to be inverted before reporting it.
            Default is `False`.
        :param bool invert_y: Specifies if the y-axis data is to be inverted before reporting it.
            Default is `False`.
        """
        self._z_idle_count = max(0, min(z_idle_count, 255))
        self._rap_write(PINNACLE_Z_IDLE, self._z_idle_count)
        self._feed_config1 = (self._feed_config1 &
                              0x3F) | invert_y << 7 | invert_x << 6
        self._rap_write(PINNACLE_FEED_CONFIG1, self._feed_config1)

    def report(self, only_new=True):
        """This function will return touch event data from the Pinnacle ASIC (including empty
        packets on ending of a touch event). This function only applies to Relative or Absolute
        mode, otherwise if `data_mode` is set to
        :attr:`~circuitpython_cirque_pinnacle.DataModes.ANYMEAS`, then this function returns
        `None` and does nothing.

        :param bool only_new: This parameter can be used to ensure the data reported is only new
            data. Otherwise the data returned can be either old data or new data. If the ``dr_pin``
            parameter is specified upon instantiation, then the specified input pin is used to
            detect if the data is new. Otherwise the SW_DR flag in the STATUS register is used to
            detirmine if the data is new.

        :Returns: `None` if  the ``only_new`` parameter is set `True` and there is no new data to
            report. Otherwise, a `list` or `bytearray` of parameters that describe the (touch or
            button) event. The structure is as follows:

            .. list-table::
                :header-rows: 1
                :widths: 1, 5, 5

                * - Index
                  - Relative (Mouse) mode

                    as a `bytearray`
                  - Absolute Mode

                    as a `list`
                * - 0
                  - Button Data [1]_

                    one unsigned byte
                  - Button Data [1]_

                    one unsigned byte
                * - 1
                  - change in x-axis [2]_

                    -128 |LessEq| X |LessEq| 127
                  - x-axis Position

                    128 |LessEq| X |LessEq| 1920
                * - 2
                  - change in y-axis [2]_

                    -128 |LessEq| Y |LessEq| 127
                  - y-axis Position

                    64 |LessEq| Y |LessEq| 1472
                * - 3
                  - change in scroll wheel

                    -128 |LessEq| Y |LessEq| 127 [3]_
                  - z-axis Position

        .. [1] The returned button data is a byte in which each bit represents a button.
            The bit to button order is as follows:

            0. [LSB] Button 1 (thought of as Left button in Relative/Mouse mode). If taps
               are enabled using `relative_mode_config()`, a single tap will be reflected here.
            1. Button 2 (thought of as Right button in Relative/Mouse mode)
            2. Button 3 (thought of as Middle or scroll wheel button in Relative/Mouse mode)
        .. [2] The axis data reported in Relative/Mouse mode is in two's
            comliment form. Use Python's :py:func:`struct.unpack()` to convert the
            data into integer form (see `Simple Test example <examples.html#simple-test>`_
            for how to use this function).

            The axis data reported in Absolute mode is always positive as the
            xy-plane's origin is located to the top-left, unless ``invert_x`` or ``invert_y``
            parameters to `absolute_mode_config()` are manipulated to change the perspective
            location of the origin.
        .. [3] In Relative/Mouse mode the scroll wheel data is only reported if the
            ``intellimouse`` parameter is passed as `True` to `relative_mode_config()`.
            Otherwise this is an empty byte as the
            returned `bytearray` follows the buffer structure of a mouse HID report (see
            `USB Mouse example <examples.html#usb-mouse-example>`_).
        .. |LessEq| unicode:: U+2264
        """
        if self._mode == DataModes.ANYMEAS:
            return None
        return_vals = None
        data_ready = False
        if only_new:
            if self.dr_pin is None:
                data_ready = self._rap_read(PINNACLE_STATUS) & 4
            else:
                data_ready = self.dr_pin.value
        if (only_new and data_ready) or not only_new:
            if self.data_mode == DataModes.ABSOLUTE:  # if absolute mode
                temp = self._rap_read_bytes(PINNACLE_PACKET_BYTE_0, 6)
                return_vals = [temp[0] & 0x3F,  # buttons
                               ((temp[4] & 0x0F) << 8) | temp[2],  # x
                               ((temp[4] & 0xF0) << 4) | temp[3],  # y
                               temp[5] & 0x3F]  # z
                # datasheet recommends clipping for reliability
                return_vals[1] = min(128, max(1920, return_vals[1]))
                return_vals[2] = min(64, max(1472, return_vals[2]))
            elif self.data_mode == DataModes.RELATIVE:  # if in relative mode
                is_intellimouse = self._feed_config2 & 1
                # get relative data packets
                temp = self._rap_read_bytes(
                    PINNACLE_PACKET_BYTE_0, 3 + is_intellimouse)
                return_vals = bytearray([temp[0] & 7, temp[1], temp[2]])
                if is_intellimouse:  # scroll wheel data is captured
                    return_vals += bytes([temp[3]])
                else:  # append empty byte to suite mouse HID reports
                    return_vals += b'\x00'
            # clear flags despite if data is fresh or not (faster & reliable)
            self.clear_flags()
        return return_vals

    def clear_flags(self):
        """This function clears the "Data Ready" flag which is reflected with the ``dr_pin``."""
        self._rap_write(0x02, 0)  # 0x02 = Status1 register
        # delay 50 microseconds per official example from Cirque
        time.sleep(0.00005)

    @property
    def allow_sleep(self):
        """Set this attribute to `True` if you want the Pinnacle ASIC to enter sleep (low power)
        mode after about 5 seconds of inactivity (does not apply to AnyMeas mode). While the touch
        controller is in sleep mode, if a touch event or button press is detected, the Pinnacle
        ASIC will take about 300 milliseconds to wake up (does not include handling the touch event
        or button press data)."""
        return bool(self._sys_config & 4)

    @allow_sleep.setter
    def allow_sleep(self, is_enabled):
        self._sys_config = (self._sys_config & 0xFB) | is_enabled << 2
        self._rap_write(PINNACLE_SYS_CONFIG, self._sys_config)

    @property
    def shutdown(self):
        """This attribute controls power of the Pinnacle ASIC. `True` means powered down (AKA
        standby mode), and `False` means not powered down (Active, Idle, or Sleep mode).

        .. note:: The ASIC will take about 300 milliseconds to complete the transition
            from powered down mode to active mode. No touch events or button presses will be
            monitored while powered down.
        """
        return bool(self._sys_config & 2)

    @shutdown.setter
    def shutdown(self, is_off):
        self._sys_config = (self._sys_config & 0xFD) | is_off << 1
        self._rap_write(PINNACLE_SYS_CONFIG, self._sys_config)

    @property
    def sample_rate(self):
        """This attribute controls how many samples (of data) per second are reported. Valid values
        are ``100``, ``80``, ``60``, ``40``, ``20``, ``10``. Any other input values automatically
        set the sample rate to 100 sps (samples per second). Optionally, ``200`` and ``300`` sps
        can be specified, but using these values automatically disables palm (referred to as "NERD"
        in the specification sheet) and noise compensations. These higher values are meant for
        using a stylus with a 2mm diameter tip, while the values less than 200 are meant for a
        finger or stylus with a 5.25mm diameter tip.

        This function only applies to Relative or Absolute mode, otherwise if `data_mode` is set to
        :attr:`~circuitpython_cirque_pinnacle.DataModes.ANYMEAS`, then this function will take no
        affect until `data_mode` is set to
        :attr:`~circuitpython_cirque_pinnacle.DataModes.RELATIVE` or
        :attr:`~circuitpython_cirque_pinnacle.DataModes.ABSOLUTE`.
        """
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, val):
        if val in (200, 300):
            # disable palm & noise compensations
            self._rap_write(PINNACLE_FEED_CONFIG2 + 1, 10)
            reload_timer = 6 if val == 300 else 0x09
            self._era_write_bytes(0x019E, reload_timer, 2)
            self._sample_rate = val
            val = 0
        else:
            # enable palm & noise compensations
            self._rap_write(PINNACLE_FEED_CONFIG2 + 1, 0)
            self._era_write_bytes(0x019E, 0x13, 2)
            val = val if val in (100, 80, 60, 40, 20, 10) else 100
            self._sample_rate = val
        if self.data_mode != DataModes.ANYMEAS:
            self._rap_write(PINNACLE_SAMPLE_RATE, val)

    def detect_finger_stylus(self, enable_finger=True, enable_stylus=True, sample_rate=100):
        """This function will configure the Pinnacle ASIC to detect either finger,
        stylus, or both.

        :param bool enable_finger: `True` enables the Pinnacle ASIC's measurements to
            detect if the touch event was caused by a finger or 5.25mm stylus. `False` disables
            this feature. Default is `True`.
        :param bool enable_stylus: `True` enables the Pinnacle ASIC's measurements to
            detect if the touch event was caused by a 2mm stylus. `False` disables this
            feature. Default is `True`.
        :param int sample_rate: See the `sample_rate` attribute as this parameter manipulates that
            attribute.

        .. tip:: Consider adjusting the ADC matrix's gain to enhance performance/results using
            `set_adc_gain()`
        """
        self._finger_stylus = self._era_read(0x00EB)
        self._finger_stylus |= enable_stylus << 2 | enable_finger
        self._era_write(0x00EB, self._finger_stylus)
        self.sample_rate = sample_rate

    def calibrate(self, run, tap=True, track_error=True, nerd=True, background=True):
        """Set calibration parameters when the Pinnacle ASIC calibrates itself. This function only
        applies to Relative or Absolute mode, otherwise if `data_mode` is set to
        :attr:`~circuitpython_cirque_pinnacle.DataModes.ANYMEAS`, then this function will take no
        affect until `data_mode` is set to
        :attr:`~circuitpython_cirque_pinnacle.DataModes.RELATIVE` or
        :attr:`~circuitpython_cirque_pinnacle.DataModes.ABSOLUTE`.

        :param bool run: If `True`, this function forces a calibration of the sensor. If `False`,
            this function just writes the following parameters to the Pinnacle ASIC's "CalConfig1"
            register. This parameter is required while the rest are optional keyword parameters.
        :param bool tap: Enable dynamic tap compensation? Default is `True`.
        :param bool track_error: Enable dynamic track error compensation? Default is `True`.
        :param bool nerd: Enable dynamic NERD compensation? Default is `True`. This parameter has
            something to do with palm detection/compensation.
        :param bool background: Enable dynamic background compensation? Default is `True`.

        .. note:: According to the datasheet, calibration of the sensor takes about 100
            milliseconds. This function will block until calibration is complete (if ``run`` is
            `True`). It is recommended for typical applications to leave all optional parameters
            in their default states.
        """
        self._cal_config = tap << 4 | track_error << 3 | nerd << 2 | background << 1
        if self.data_mode != DataModes.ANYMEAS:
            self._rap_write(PINNACLE_CALIBRATE_CONFIG, self._cal_config | run)
            if run:
                while self._rap_read(PINNACLE_CALIBRATE_CONFIG) & 1:
                    pass  # calibration is running
                # now that calibration is done, clear "command complete" flag
                self.clear_flags()

    @property
    def calibration_matrix(self):
        """This attribute returns a `list` of the 46 signed 16-bit (short) values stored in the
        Pinnacle ASIC's memory that is used for taking measurements. This matrix is not applicable
        in AnyMeas mode. Use this attribute to compare a prior compensation matrix with a new
        matrix that was either loaded manually by setting this attribute to a `list` of 46 signed
        16-bit (short) integers or created internally by calling `calibrate()` with the ``run``
        parameter as `True`.

        .. note:: A paraphrased note from Cirque's Application Note on Comparing compensation
            matrices:

            If any 16-bit values are above 20K (absolute), it generally indicates a problem with
            the sensor. If no values exceed 20K, proceed with the data comparison. Compare each
            16-bit value in one matrix to the corresponding 16-bit value in the other matrix. If
            the difference between the two values is greater than 500 (absolute), it indicates a
            change in the environment. Either an object was on the sensor during calibration, or
            the surrounding conditions (temperature, humidity, or noise level) have changed. One
            strategy is to force another calibration and compare again, if the values continue to
            differ by 500, determine whether to use the new data or a previous set of stored data.
            Another strategy is to average any two values that differ by more than 500 and write
            this new matrix, with the average values, back into Pinnacle ASIC.
        """
        # combine every 2 bytes from resulting buffer to form a list of signed 16-bits integers
        return list(struct.unpack('46h', self._era_read_bytes(0x01DF, 46 * 2)))

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
            buf = struct.pack('h', matrix[index])
            self._era_write(0x01DF + index * 2, buf[0])
            self._era_write(0x01DF + index * 2 + 1, buf[1])
        self.feed_enable = prev_feed_state  # resume previous feed state

    def set_adc_gain(self, sensitivity):
        """Sets the ADC gain in range [0,3] to enhance performance based on the overlay type (does
        not apply to AnyMeas mode). (write-only)

        :param int sensitivity: This int specifies how sensitive the ADC (Analog to Digital
            Converter) component is. ``0`` means most sensitive, and ``3`` means least sensitive.
            A value outside this range will raise a `ValueError` exception.

        .. tip:: The official example code from Cirque for a curved overlay uses a value of ``1``.
        """
        if 0 <= sensitivity < 4:
            self._sensitivity = self._era_read(0x0187) & 0x3F
            self._sensitivity |= sensitivity << 6
            self._era_write(0x0187, self._sensitivity)
        else:
            raise ValueError("{} is out of bounds [0,3]".format(sensitivity))

    def tune_edge_sensitivity(self, x_axis_wide_z_min=0x04, y_axis_wide_z_min=0x03):
        """According to the official exmaple code from Cirque,
        this function "Changes thresholds to improve detection of fingers."

        This function was ported from Cirque's example code and doesn't seem to have corresponding
        documentation. I'm having trouble finding a memory map of the Pinnacle ASIC as this
        function directly alters values in the Pinnacle ASIC's memory. USE AT YOUR OWN RISK!
        """
        self._era_write(0x0149, x_axis_wide_z_min)
        self._era_write(0x0168, y_axis_wide_z_min)

    def anymeas_mode_config(self, gain=AnyMeasGain.GAIN_200, frequency=AnyMeasFreq.FREQ_0,
                            sample_length=512, mux_ctrl=AnyMeasMux.MUX_PNP, apperture_width=500,
                            ctrl_pwr_cnt=1):
        """This function configures the Pinnacle ASIC to output raw ADC measurements.
        Be sure to set the `data_mode` attribute to
        :attr:`~circuitpython_cirque_pinnacle.DataModes.ANYMEAS` before calling this function
        otherwise it will do nothing.

        :param int gain: Sets the sensitivity of the ADC matrix. Valid values are the constants
            defined in :class:`~circuitpython_cirque_pinnacle.AnyMeasGain`. Defaults to
            :attr:`~circuitpython_cirque_pinnacle.AnyMeasGain.GAIN_200`.
        :param int frequency: Sets the frequency of measurements made by the ADC matrix. Valid
            values are the constants defined in
            :class:`~circuitpython_cirque_pinnacle.AnyMeasFreq`.
            Defaults :attr:`~circuitpython_cirque_pinnacle.AnyMeasFreq.FREQ_0`.
        :param int sample_length: Sets the maximum bit length of the measurements made by the ADC
            matrix. Valid values are ``128``, ``256``, or ``512``. Defaults to ``512``.
        :param int mux_ctrl: The Pinnacle ASIC can employ different bipolar junctions
            and/or reference capacitors. Valid values are the constants defined in
            :class:`~circuitpython_cirque_pinnacle.AnyMeasMux`. Additional combination of
            these constants is also allowed. Defaults to
            :attr:`~circuitpython_cirque_pinnacle.AnyMeasMux.MUX_PNP`.
        :param int apperture_width: Sets the window of time (in nanoseconds) to allow for the ADC
            to take a measurement. Valid values are multiples of 125 in range [``250``, ``1875``].
            Erroneous values are clamped/truncated to this range.

            .. note:: The ``apperture_width`` parameter has a inverse relationship/affect on the
                ``frequency`` parameter. The approximated frequencies described in this
                documentation are based on an aperture width of 500 nanoseconds, and they will
                shrink as the apperture width grows or grow as the aperture width shrinks.

        :param int ctrl_pwr_cnt: Configure the Pinnacle to perform a number of measurements for
            each call to `measure_adc()`. Defaults to 1. Constants defined in
            :class:`~circuitpython_cirque_pinnacle.AnyMeasCrtl` can be used to specify if is sleep
            is allowed (:attr:`~circuitpython_cirque_pinnacle.AnyMeasCrtl.CRTL_PWR_IDLE` -- this
            is not default) or if repetive measurements is allowed (
            :attr:`~circuitpython_cirque_pinnacle.AnyMeasCrtl.CRTL_REPEAT`) if number of
            measurements is more than 1.

            .. warning:: There is no bounds checking on the number of measurements specified
                here. Specifying more than 63 will trigger sleep mode after performing
                measuements.

            .. tip:: Be aware that allowing the Pinnacle to enter sleep mode after taking
                measurements will slow consecutive calls to `measure_adc()` as the Pinnacle
                requires about 100 milliseconds to wake up.
        """
        if self.data_mode == DataModes.ANYMEAS:
            # assemble buffer for configuring ADC measurements
            # approximate frequency and gain config
            self._anymeas_config[0] = gain | frequency
            # sample length must be in range [1, 3]
            self._anymeas_config[1] = (max(1, min(int(sample_length / 128), 3)))
            # enable ADC gate polarity
            # (PNP can be combined w/ NPN or only NPN or only PNP)
            self._anymeas_config[2] = mux_ctrl
            # next is ADCconfig2 reg (mostly internal firmware flags)
            # self._anymeas_config[3] = 0
            # apperture widths 125 or less don't work; default to 250 if 125 or less is specified
            self._anymeas_config[4] = max(2, min(int(apperture_width / 125), 15))
            # self._anymeas_config.[5, 7, 8] = 0 these are "test-only" registers
            # specify the register to use as offset for measurement polynomials
            # self._anymeas_config[6] = PINNACLE_PACKET_BYTE_0 + 1  # use 0x13
            # next is the power and count control register
            self._anymeas_config[9] = ctrl_pwr_cnt
            # dump self._anymeas_config to all 10 registers at once
            self._rap_write_bytes(PINNACLE_FEED_CONFIG2, self._anymeas_config)
            # clear 8 registers (used for toggle & polarity polynomials)
            self._rap_write_bytes(PINNACLE_PACKET_BYTE_0 + 1, [0] * 8)
            self.clear_flags()

    def measure_adc(self, bits_to_toggle, toggle_polarity):
        """This function instigates and returns the measurements (a signed short) from the Pinnacle
        ASIC's ADC (Analog to Digital Converter) matrix (only applies to AnyMeas mode).

        :param int bits_to_toggle: This 4-byte integer specifies which bits the Pinnacle touch
            controller should toggle. A bit of ``1`` flags that bit for toggling, and a bit of
            ``0`` signifies that the bit should remain unaffected.
        :param int toggle_polarity: This 4-byte integer specifies which polarity the specified
            bits (from ``bits_to_toggle`` parameter) are toggled. A bit of ``1`` toggles that bit
            positve, and a bit of ``0`` toggles that bit negative.

        :Returns:
            A 2-byte `bytearray` that represents a signed short integer. If `data_mode` is not set
            to :attr:`~circuitpython_cirque_pinnacle.DataModes.ANYMEAS`, then this function returns
            `None` and does nothing.

        :4-byte Integer Format:
            .. csv-table:: byte 3 (MSByte)
                :stub-columns: 1
                :widths: 10, 5, 5, 5, 5, 5, 5, 5, 5

                "bit position",31,30,29,28,27,26,25,24
                "representation",N/A,N/A,Ref1,Ref0,Y11,Y10,Y9,Y8
            .. csv-table:: byte 2
                :stub-columns: 1
                :widths: 10, 5, 5, 5, 5, 5, 5, 5, 5

                "bit position",23,22,21,20,19,18,17,16
                "representation",Y7,Y6,Y5,Y4,Y3,Y2,Y1,Y0
            .. csv-table:: byte 1
                :stub-columns: 1
                :widths: 10, 5, 5, 5, 5, 5, 5, 5, 5

                "bit position",15,14,13,12,11,10,9,8
                "representation",X15,X14,X13,X12,X11,X10,X9,X8
            .. csv-table:: byte 0 (LSByte)
                :stub-columns: 1
                :widths: 10, 5, 5, 5, 5, 5, 5, 5, 5

                "bit position",7,6,5,4,3,2,1,0
                "representation",X7,X6,X5,X4,X3,X2,X1,X0

            See `AnyMeas mode example <examples.html#anymeas-mode-example>`_ to understand how to
            use these 4-byte integer polynomials.

            .. note:: Bits 29 and 28 represent the optional implementation of reference capacitors
                built into the Pinnacle ASIC. To use these capacitors, the
                corresponding constants
                (:attr:`~circuitpython_cirque_pinnacle.AnyMeasMux.MUX_REF0` and/or
                :attr:`~circuitpython_cirque_pinnacle.AnyMeasMux.MUX_REF1`) must be passed to
                `anymeas_mode_config()` in the ``mux_ctrl`` parameter, and their representative
                bits must be flagged in both ``bits_to_toggle`` & ``toggle_polarity`` parameters.
        """
        # assemble list of register buffers
        if self._mode != DataModes.ANYMEAS:
            return None
        tog_pol = []
        for i in range(3, -1, -1):
            tog_pol.append((bits_to_toggle >> (i * 8)) & 0xFF)
        for i in range(3, -1, -1):
            tog_pol.append((toggle_polarity >> (i * 8)) & 0xFF)
        # write toggle and polarity parameters to register 0x13 - 0x1A (PACKET_BYTE_1 + 8)
        self._rap_write_bytes(PINNACLE_PACKET_BYTE_0 + 1, tog_pol)

        # initiate measurements
        self._rap_write(PINNACLE_SYS_CONFIG, self._sys_config | 0x18)
        # wait till measurements are complete
        while not self.dr_pin.value:
            pass  # Pinnacle is still computing
        result = self._rap_read_bytes(PINNACLE_PACKET_BYTE_0 - 1, 2)
        self.clear_flags()
        return bytearray(result)

    def _rap_read(self, reg):
        """This function is overridden by the appropriate parent class based on interface type."""
        raise NotImplementedError()

    def _rap_read_bytes(self, reg, numb_bytes):
        """This function is overridden by the appropriate parent class based on interface type."""
        raise NotImplementedError()

    def _rap_write(self, reg, value):
        """This function is overridden by the appropriate parent class based on interface type."""
        raise NotImplementedError()

    def _rap_write_bytes(self, reg, values):
        """This function is overridden by the appropriate parent class based on interface type."""
        raise NotImplementedError()

    def _era_read(self, reg):
        prev_feed_state = self.feed_enable
        self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write_bytes(PINNACLE_ERA_ADDR_HIGH, [reg >> 8, reg & 0xff])
        self._rap_write(PINNACLE_ERA_CTRL, 1)  # indicate reading only 1 byte
        while self._rap_read(PINNACLE_ERA_CTRL):  # read until reg == 0
            pass  # also sets Command Complete flag in Status register
        buf = self._rap_read(PINNACLE_ERA_VALUE)  # get value
        self.clear_flags()
        self.feed_enable = prev_feed_state  # resume previous feed state
        return buf

    def _era_read_bytes(self, reg, numb_bytes):
        buf = b''
        prev_feed_state = self.feed_enable
        self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write_bytes(PINNACLE_ERA_ADDR_HIGH, [reg >> 8, reg & 0xff])
        for _ in range(numb_bytes):
            self._rap_write(PINNACLE_ERA_CTRL, 5)  # indicate reading sequential bytes
            while self._rap_read(PINNACLE_ERA_CTRL):  # read until reg == 0
                pass  # also sets Command Complete flag in Status register
            buf += bytes([self._rap_read(PINNACLE_ERA_VALUE)])  # get value
            self.clear_flags()
        self.feed_enable = prev_feed_state  # resume previous feed state
        return buf

    def _era_write(self, reg, value):
        prev_feed_state = self.feed_enable
        self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write(PINNACLE_ERA_VALUE, value)  # write value
        self._rap_write_bytes(PINNACLE_ERA_ADDR_HIGH, [reg >> 8, reg & 0xff])
        self._rap_write(PINNACLE_ERA_CTRL, 2)  # indicate writing only 1 byte
        while self._rap_read(PINNACLE_ERA_CTRL):  # read until reg == 0
            pass  # also sets Command Complete flag in Status register
        self.clear_flags()
        self.feed_enable = prev_feed_state  # resume previous feed state

    def _era_write_bytes(self, reg, value, numb_bytes):
        # NOTE this is rarely used as it only writes 1 value to multiple registers
        prev_feed_state = self.feed_enable
        self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write(PINNACLE_ERA_VALUE, value)  # write value
        self._rap_write_bytes(PINNACLE_ERA_ADDR_HIGH, [reg >> 8, reg & 0xff])
        self._rap_write(PINNACLE_ERA_CTRL, 0x0A)  # indicate writing sequential bytes
        for _ in range(numb_bytes):
            while self._rap_read(PINNACLE_ERA_CTRL):  # read until reg == 0
                pass  # also sets Command Complete flag in Status register
            self.clear_flags()
        self.feed_enable = prev_feed_state  # resume previous feed state

# due to use adafruit_bus_device, pylint can't find bus-specific functions
# pylint: disable=no-member
class PinnacleTouchI2C(PinnacleTouch):
    """
    Varaiant of the base class, `PinnacleTouch`, for interfacing with the Pinnacle ASIC via
    the I2C protocol.

    :param ~busio.I2C i2c: The object of the I2C bus to use. This object must be shared among
        other driver classes that use the same I2C bus (SDA & SCL pins).
    :param int address: The slave I2C address of the Pinnacle ASIC. Defaults to ``0x2A``.

    See the base class for other instantiating parameters.
    """

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
    """
    Varaiant of the base class, `PinnacleTouch`, for interfacing with the Pinnacle ASIC via
    the SPI protocol.

    :param ~busio.SPI spi: The object of the SPI bus to use. This object must be shared among
        other driver classes that use the same SPI bus (MOSI, MISO, & SCK pins).
    :param ~microcontroller.Pin ss_pin: The "slave select" pin output to the Pinnacle ASIC.

    See the base class for other instantiating parameters.
    """

    def __init__(self, spi, ss_pin, dr_pin=None):
        # MAX baudrate is up to 13MHz; use 10MHz to be safe
        self._spi = SPIDevice(spi, chip_select=ss_pin,
                              baudrate=12000000, phase=1)
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
