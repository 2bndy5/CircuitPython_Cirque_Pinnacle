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

A driver class for the Cirque Pinnacle touch controller ASIC on the Cirque capacitve touch
based circular trackpads.
"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle.git"
import time
import math
from struct import unpack, pack
from adafruit_bus_device.spi_device import SPIDevice
from adafruit_bus_device.i2c_device import I2CDevice

# internal registers
# pylint: disable=bad-whitespace
# PINNACLE_FIRMWARE_ID             = 0x00  # Firmware ASIC ID (always = 7)
# PINNACLE_FIRMWARE_VER            = 0x01  # Firmware revision number (always = 0x3A)
PINNACLE_STATUS                  = 0x02  # Contains status flags about the state of Pinnacle
PINNACLE_SYS_CONFIG              = 0x03  # Contains system operation and configuration bits
PINNACLE_FEED_CONFIG1            = 0x04  # Contains feed operation and configuration bits
PINNACLE_FEED_CONFIG2            = 0x05  # Contains feed operation and configuration bits
# PINNACLE_FEED_CONFIG3          = 0x06  # Contains feed operation and configuration bits
PINNACLE_CALIBRATE_CONFIG        = 0x07  # Contains calibration configuration bits
PINNACLE_SAMPLE_RATE             = 0x09  # Number of samples generated per second
PINNACLE_Z_IDLE                  = 0x0A  # Number of Z=0 packets sent when Z goes from >0 to 0
# PINNACLE_Z_SCALAR                = 0x0B  # Contains the pen Z_On threshold
# PINNACLE_SLEEP_INTERVAL          = 0x0C  # No description
# PINNACLE_SLEEP_TIMER             = 0x0D  # No description
# PINNACLE_EMI_THRESHOLD           = 0x0E  # Threshold to adjust EMI settings
PINNACLE_PACKET_BYTE_0           = 0x12  # trackpad Data
# PINNACLE_PACKET_BYTE_1           = 0x13  # trackpad Data
# PINNACLE_PACKET_BYTE_2           = 0x14  # trackpad Data
# PINNACLE_PACKET_BYTE_3           = 0x15  # trackpad Data
# PINNACLE_PACKET_BYTE_4           = 0x16  # trackpad Data
# PINNACLE_PACKET_BYTE_5           = 0x17  # trackpad Data
PINNACLE_ERA_VALUE               = 0x1B  # Value for extended register access
PINNACLE_ERA_ADDR_HIGH           = 0x1C  # High byte of 16 bit extended register address
PINNACLE_ERA_ADDR_LOW            = 0x1D  # Low byte of 16 bit extended register address
PINNACLE_ERA_CTRL                = 0x1E  # Control of extended register access

# constants used for bitwise configuration
REL_MODE                = 0x00 #: Alias symbol for specifying Relative/Mouse mode
ABS_MODE                = 0x02 #: Alias symbol for specifying Absolute mode
ANY_MODE                = 0x10 #: Alias symbol for specifying "AnyMeas" (raw ADC) mode
ADC_GAIN_100            = 0xC0 #: AnyMeas mode config around 100% gain
ADC_GAIN_133            = 0x80 #: AnyMeas mode config around 133% gain
ADC_GAIN_166            = 0x40 #: AnyMeas mode config around 166% gain
ADC_GAIN_200            = 0x00 #: AnyMeas mode config around 200% gain
ADC_FREQ_0              = 0x02 #: AnyMeas mode config frequency around 500,000Hz
ADC_FREQ_1              = 0x03 #: AnyMeas mode config frequency around 444,444Hz
ADC_FREQ_2              = 0x04 #: AnyMeas mode config frequency around 400,000Hz
ADC_FREQ_3              = 0x05 #: AnyMeas mode config frequency around 363,636Hz
ADC_FREQ_4              = 0x06 #: AnyMeas mode config frequency around 333,333Hz
ADC_FREQ_5              = 0x07 #: AnyMeas mode config frequency around 307,692Hz
ADC_FREQ_6              = 0x09 #: AnyMeas mode config frequency around 267,000Hz
ADC_FREQ_7              = 0x0B #: AnyMeas mode config frequency around 235,000Hz
ADC_MUX_PNP             = 0x04 #: AnyMeas mode config enable PNP sense line
ADC_MUX_NPN             = 0x01 #: AnyMeas mode config enable NPN sense line
# pylint: enable=bad-whitespace

class PinnacleTouch:
    """
    The abstract base class for driving the Pinnacle touch controller.

    :param ~microcontroller.Pin dr_pin: The input pin connected to the touch controller's "Data
        Ready" pin. If this parameter is not specified, then the SW_DR (software data ready) flag
        of the STATUS register is used to detirmine if the data being reported is new.
    :param int z_idle_count: The number of empty packets to report (every 10 milliseconds) when
        z-axis is idle (no touch detected). Default is 5.
    :param bool relative: Specifies if the data reported is relative (`True` -- change since
        last event) or absolute (`False` -- exact position on sensor) modes. Default is `True`.

        .. note:: Relative data mode is also referred to as "Mouse Mode" in the datasheet.
    :param bool invert_x: Specifies if the x-axis data is to be inverted before reporting it.
        Default is `False`.
    :param bool invert_y: Specifies if the y-axis data is to be inverted before reporting it.
        Default is `False`.
    :param bool feed_enable: Specifies if data reporting is enabled (`True`) or not (`False`).
        Default is `True`.
    """

    def __init__(self, dr_pin=None, feed_enable=True, allow_sleep=False):
        self.dr_pin = dr_pin
        if dr_pin is not None:
            self.dr_pin.switch_to_input()

        # perform hardware check
        firmware_id, firmware_ver = self._rap_read_bytes(0, 2)
        if firmware_id != 7 or firmware_ver != 0x3A:
            raise OSError("Cirque Pinnacle touch controller not responding")

        # init internal attributes
        self._feed_config1 = 0
        self._feed_config2 = 0
        self._sample_rate = 0
        self._sys_config = 0
        self._z_idle_count = 0

        # reset device on init in case Pinnacle is configured for AnyMeas mode
        self.reset_device()  # also reads reg values for internal attributes

        # set user defined values
        self._feed_config1 = feed_enable
        self._sys_config = allow_sleep << 2

        # write user config settings into Pinnacle registers
        self._rap_write_bytes(PINNACLE_SYS_CONFIG, [
            self._sys_config, self._feed_config1, self._feed_config2])
        self._rap_write(PINNACLE_SAMPLE_RATE, self._sample_rate)
        # clear any "Command Complete" and "Data Ready" flags (just to be sure)
        self.clear_flags()  # this is also done by reset_device()

    @property
    def feed_enable(self):
        """This `bool` attribute controls if the touch data is reported (`True`) or not
        (`False`)."""
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

        Valid input values are `REL_MODE` for relative/mouse mode, `ABS_MODE` for absolute
        positioning mode, or `ANY_MODE` (referred to as "AnyMeas" in specification sheets) mode
        for reading ADC values.

        :Returns:

            - ``0`` for Relative mode (AKA mouse mode)
            - ``2`` for Absolute mode (X & Y axis positions)
            - ``16`` for AnyMeas mode (raw ADC measurements)
        """
        if self._sys_config & ANY_MODE:
            return ANY_MODE
        return ABS_MODE if self._feed_config1 & ABS_MODE else REL_MODE

    @data_mode.setter
    def data_mode(self, mode):
        if mode not in (ANY_MODE, REL_MODE, ABS_MODE):
            raise ValueError("unrecognised parameter value for mode. Use 0 for Relative mode, "
                             "2 for Absolute mode, or 16 for AnyMeas mode.")
        if mode < ANY_MODE:  # for relative/mouse or absolute mode
            if self.data_mode == ANY_MODE:
                # best to reset device and then reload user configuration, but be sure to clear
                # flags specific to enabled AnyMeas mode
                prev_state1 = [self._sys_config & 0xE7, self._feed_config1, self._feed_config2]
                prev_state2 = [self._sample_rate, self._z_idle_count]
                self.reset_device()
                self._rap_write_bytes(PINNACLE_SYS_CONFIG, prev_state1)
                self._rap_write_bytes(PINNACLE_SAMPLE_RATE, prev_state2)
            # now write appropriate mode
            self._feed_config1 = (self._feed_config1 & 0xFD) | mode
            self._rap_write(PINNACLE_FEED_CONFIG1, self._feed_config1)
        else:  # for AnyMeas mode
            # disable tracking computations & enable AnyMeas mode
            self._sys_config = (self._sys_config & 0xE7) | 0x18
            self._rap_write(PINNACLE_SYS_CONFIG, self._sys_config)
            time.sleep(0.01) # wait 10 ms for tracking measurements to expire
            # now configure the AnyMeas mode to default values
            self.anymeas_mode_config()

    def anymeas_mode_config(self, gain=ADC_GAIN_200, frequency=ADC_FREQ_0, sample_length=512,
                            mux_ctrl=ADC_MUX_PNP, apperture_width=500):
        """This function configures the Pinnacle touch controller to output raw ADC measurements.
        Be sure to set the `data_mode` attribute to `ANY_MODE` before calling this function
        otherwise it will do nothing.

        :param int gain: Sets the sensitivity of the ADC matrix. Valid values are `ADC_GAIN_100`,
            `ADC_GAIN_133`, `ADC_GAIN_166`, or `ADC_GAIN_200`. Defaults to `ADC_GAIN_200`.
        :param int frequency: Sets the frequency of measurements made by the ADC matrix. Valid
            values are `ADC_FREQ_0`, `ADC_FREQ_1`, `ADC_FREQ_2`, `ADC_FREQ_3`, `ADC_FREQ_4`,
            `ADC_FREQ_5`, `ADC_FREQ_6`, `ADC_FREQ_7`. Defaults `ADC_FREQ_0`.
        :param int sample_length: Sets the maximum bit length of the measurements made by the ADC
            matrix. Valid values are ``128``, ``256``, or ``512``. Defaults to ``512``.
        :param int mux_ctrl: The Pinnacle touch controller can employ different bipolar junctions.
            Valid values are `ADC_MUX_PNP`, `ADC_MUX_NPN`, or a combination of the 2. Defaults to
            `ADC_MUX_PNP`.
        :param int apperture_width: Sets the window of time (in nanoseconds) to allow for the ADC
            to take a measurement. Valid values are multiples of 125 in range [``250``, ``1875``].
            Erroneous values are clamped/truncated to this range.

        .. note:: The ``apperture_width`` parameter has a inverse relationship/affect on the
            ``frequency`` parameter. The approximated frequencies described in this documentation
            are based on an aperture width of 500 nanoseconds, and they will shrink as the
            apperture width grows or grow as the aperture width shrinks.
        """
        if self.data_mode == ANY_MODE:
            # assemble buffer for configuring ADC measurements
            init_vals = [gain | frequency]  # approximate frequency and gain config
            # sample length must be in range [1, 3]
            init_vals.append(max(1, min(int(sample_length / 128), 3)))
            # enable ADC gate polarity
            init_vals.append(mux_ctrl)  # (PNP can be combined w/ NPN or only NPN or only PNP)
            # apperture widths 125 or less don't work; default to 250 if 125 or less is specified
            init_vals.append(max(2, min(int(apperture_width / 125), 15)))
            # clear some "test-only" registers w/ 0, specify the register to use as
            # offset for saving measurement results, and enforce single (fastest) measurement
            # multiple measurements can be averaged by the application without sacrificing
            # measurement speed
            init_vals += [0, PINNACLE_PACKET_BYTE_0 + 1, 0, 0, 1]
            self._rap_write_bytes(PINNACLE_FEED_CONFIG2, init_vals)
            # clear these other registers according to example code
            self._rap_write_bytes(PINNACLE_PACKET_BYTE_0 + 1, [0] * 8)
            self.clear_flags()

    def relative_mode_config(self, rotate90=False, glide_extend=True, scroll_disable=False,
                             secondary_tap=True, disable_taps=True, intellimouse=False):
        """Set the configuration register for features specific to relative mode (AKA mouse mode)
        data reporting.

        :param bool rotate90: Specifies if the axis data is altered for 90 degree rotation before
            reporting it. Default is `False`.
        :param bool glide_extend: A patended feature that allows the user to glide their finger off
            the edge of the sensor and continue gesture with the touch event. Default is `True`.
            This feature is only implemented on the AG variant of the Pinnacle touch controller
            ASIC.
        :param bool scroll_disable: Specifies if the scrolling data is enabled (`True`) or
            disabled (`False`). Default is `False`. This feature is only implemented on the AG
            variant of the Pinnacle touch controller ASIC.
        :param bool secondary_tap: Specifies if tapping in the top-left corner (depending on
            orientation) triggers the secondary button data. Defaults to `True`. This feature is
            only implemented on the AG variant of the Pinnacle touch controller ASIC.
        :param bool disable_taps: Specifies if all taps should be reported (`True`) or not
            (`False`). Default is `True`. This affects ``secondary_tap`` option as well. Only the
            primary button (left mouse button) is emulated with a tap on the non-AG variant of the
            Pinnacle touch controller ASIC.
        :param bool intellimouse: Specifies if the data reported includes a byte about scroll data.
            Default is `False`. Because this flag is specific to scroll data, this feature is only
            implemented on the AG variant of the Pinnacle touch controller ASIC.
        """
        self._feed_config2 = rotate90 << 7 | (not glide_extend) << 4 | scroll_disable << 3 | (
            not secondary_tap) << 2 | (not disable_taps) << 1 | intellimouse
        self._rap_write(PINNACLE_FEED_CONFIG2, self._feed_config2)

    def invert_axis(self, invert_x=False, invert_y=False):
        """ Set the mode in which the data is reported. (write only)

        :param bool invert_x: Specifies if the x-axis data is to be inverted before reporting it.
            Default is `False`.
        :param bool invert_y: Specifies if the y-axis data is to be inverted before reporting it.
            Default is `False`.
        """
        self._feed_config1 = (self._feed_config1 & 0x3D) | invert_y << 7 | invert_x << 6
        self._rap_write(PINNACLE_FEED_CONFIG1, self._feed_config1)

    @property
    def sample_rate(self):
        """This attribute controls how many samples (of data) per second are reported. Valid values
        are ``100``, ``80``, ``60``, ``40``, ``20``, ``10``. Any other input values automatically
        set the sample rate to 100 sps (samples per second).
        """
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, val):
        self._rap_write(PINNACLE_SAMPLE_RATE, val)
        self._sample_rate = self._rap_read(PINNACLE_SAMPLE_RATE)

    def calibrate(self, run, tap=True, track_error=True, nerd=True, background=True):
        """Set calibration parameters when the Pinnacle ASIC calibrates itself.

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
        self._rap_write(PINNACLE_CALIBRATE_CONFIG,
                        tap << 4 | track_error << 3 | nerd << 2 | background << 1 | run)
        while self._rap_read(PINNACLE_CALIBRATE_CONFIG) & 1:
            pass  # calibration is running
        if run:
            self.clear_flags()

    def report(self, only_new=True):
        """This function will return touch event data from the touch controller (including empty
        packets on ending of a touch event).

        :param bool only_new: This parameter can be used to ensure the data reported is only new
            data. Otherwise the data returned can be either old data or new data. If the ``dr_pin``
            parameter is specified upon instantiation, then the specified input pin is used to
            detect if the data is new. Otherwise the SW_DR flag in the STATUS register is used to
            detirmine if the data is new.

        :Returns: `None` if  the ``only_new`` parameter is set `True` and there is no new data to
            report. Otherwise, a `list` or `bytearray` of parameters that describe the (touch or
            button) event. The structure is as follows:

            +-------+------------------------+-----------------+
            | Index |  Relative (Mouse) mode |  Absolute Mode  |
            |       |  as a `bytearray`      |  as a `list`    |
            +=======+========================+=================+
            |   0   |      Button Data       |   Button Data   |
            +-------+------------------------+-----------------+
            |   1   |   change in x-axis     | x-axis Position |
            +-------+------------------------+-----------------+
            |   2   |   change in y-axis     | y-axis Position |
            +-------+------------------------+-----------------+
            |   3   | change in scroll wheel | z-axis Position |
            +-------+------------------------+-----------------+

            .. important:: The axis and scroll data reported in Relative/Mouse mode is in two's
                comliment form. Use Python's :py:func:`struct.unpack()` to convert the
                data into integer form (see `Simple Test example <examples.html#Simple-Test>`_
                for how to use this function).

                The axis data reported in Absolute mode is always positive as the
                xy-plane's origin is located to the top-left, unless ``invert_x`` or ``invert_y``
                parameters to `invert_axis()` are manipulated to change the perspective location
                of the origin.

        :Button Data: The returned button data is a byte in which each bit represents a button
            The bit to button order is as follows:

                0. [LSB] Button 1 (thought of as Left Button in Relative/Mouse mode).
                   If taps are enabled in Relative/Mouse mode, a single tap will be reflected here.
                1. Button 2 (thought of as Right Button in Relative/Mouse mode)
                2. Button 3 (thought of as Middle or scroll wheel Button in Relative/Mouse mode)

        .. note:: In Relative/Mouse mode the scroll wheel data is only reported if the
            ``intellimouse`` parameter is passed as `True` to `relative_mode_config()`.
            Otherwise this is an empty byte as the returned `bytearray` follows the
            buffer structure of a mouse HID report
            (see `USB Mouse example <examples.html#USB-Mouse-example>`_).
        """
        temp = []  # placeholder for data reception
        return_vals = None
        data_ready = False
        if only_new:
            if self.dr_pin is None:
                data_ready = (self._rap_read(PINNACLE_STATUS) & 4) >> 2
            else:
                data_ready = self.dr_pin.value
        if (only_new and data_ready) or not only_new:
            if self.data_mode == ABS_MODE:  # if absolute mode
                temp = self._rap_read_bytes(PINNACLE_PACKET_BYTE_0, 6)
                return_vals = [temp[0] & 0x3F,  # buttons
                               ((temp[4] & 0x0F) << 8) | temp[2],  # x
                               ((temp[4] & 0xF0) << 4) | temp[3],  # y
                               temp[5] & 0x3F]  # z
            elif self.data_mode == REL_MODE:  # if in relative mode
                is_intellimouse = self._feed_config2 & 1
                # get relative data packets
                temp = self._rap_read_bytes(
                    PINNACLE_PACKET_BYTE_0, 3 + is_intellimouse)
                return_vals = bytearray([temp[0] & 7, temp[1], temp[2]])
                if is_intellimouse:  # scroll wheel data is captured
                    return_vals += bytes([temp[3]])
                else:  # append empty byte to suite mouse HID reports
                    return_vals += b'\x00'
            self.clear_flags()
        return return_vals

    def set_adc_gain(self, sensitivity):
        """Sets the ADC gain in range [0,3] to enhance performance based on the overlay type.
        (write-only)

        :param int sensitivity: This int specifies how sensitive the ADC (Analog to Digital
            Converter) component is. ``0`` means most sensitive, and ``3`` means least sensitive.
            A value outside this range will raise a `ValueError` exception.

        .. tip:: The official example code from Cirque for a curved overlay uses a value of ``1``.
        """
        if 0 <= sensitivity < 4:
            prev_feed_state = self.feed_enable
            self.feed_enable = False  # accessing raw memory, so do this
            val = self._era_read(0x0187) & 0x3F
            val |= sensitivity << 6
            self._era_write(0x0187, val)
            self.feed_enable = prev_feed_state  # resume normal operation
        else:
            raise ValueError("{} is out of bounds [0,3]".format(sensitivity))

    def tune_edge_sensitivity(self, x_axis_wide_z_min=0x04, y_axis_wide_z_min=0x03):
        """According to the official exmaple code from Cirque,
        this function "Changes thresholds to improve detection of fingers."

        This function was ported from Cirque's example code and doesn't seem to have corresponding
        documentation. I'm having trouble finding a memory map of the Pinnacle ASIC as this
        function directly alters values in the Pinnacle ASIC's memory. USE AT YOUR OWN RISK!
        """
        prev_feed_state = self.feed_enable
        self.feed_enable = False  # accessing raw memory, so do this
        # write x_axis_wide_z_min value
        # self._era_read(0x0149) # this was used for printing unaltered value to serial monitor
        self._era_write(0x0149, x_axis_wide_z_min)
        # ERA_ReadBytes(0x0149) # this was used for printing verified value to serial monitor
        # write y_axis_wide_z_min value
        # self._era_read(0x0168) # this was used for printing unaltered value to serial monitor
        self._era_write(0x0168, y_axis_wide_z_min)
        # ERA_ReadBytes(0x0168) # this was used for printing verified value to serial monitor
        self.feed_enable = prev_feed_state  # resume normal operation

    @property
    def z_idle_count(self):
        """The number of empty packets (x-axis & y-axis both are ``0``) reported (every 10
        milliseconds) when there is no touch detected. Defaults to 30."""
        return self._z_idle_count

    @z_idle_count.setter
    def z_idle_count(self, val):
        self._z_idle_count = val
        self._rap_write(PINNACLE_Z_IDLE, self._z_idle_count)

    def clear_flags(self):
        """This function clears the "Data Ready" flag which is reflected with the ``dr_pin``."""
        self._rap_write(0x02, 0)  # 0x02 = Status1 register
        # delay 50 microseconds per official example from Cirque
        time.sleep(0.00005)

    def reset_device(self):
        """Resets the touch controller. (write only)

        .. warning:: Resetting the touch controller will change all register configurations to
            their default values which will be reflected in the `PinnacleTouch` object's
            attributes. Calibration is also automatically performed as it part of the touch
            controller's start-up sequence.
        """
        self._rap_write(PINNACLE_SYS_CONFIG, (self._rap_read(PINNACLE_SYS_CONFIG) & 0xFE) | 1)
        while not self.dr_pin.value:
            pass  # wait for power-on & calibration to be performed

        # read register values after reset operation completes
        self._sys_config, self._feed_config1, self._feed_config2 = self._rap_read_bytes(
            PINNACLE_SYS_CONFIG, 3)
        self._sample_rate, self._z_idle_count = self._rap_read_bytes(
            PINNACLE_SAMPLE_RATE, 2)
        self.clear_flags()

    @property
    def allow_sleep(self):
        """Set this attribute to `True` if you want the touch controller to enter sleep (low power)
        mode after about 5 seconds of inactivity. While the touch controller is in sleep mode, if a
        touch event or button press is detected, the Pinnacle ASIC will take about 300 milliseconds
        to wake up (does not include handling the touch event or button press data)."""
        return bool(self._sys_config & 4)

    @allow_sleep.setter
    def allow_sleep(self, is_enabled):
        self._sys_config = (self._sys_config & 0xFB) | is_enabled << 2
        self._rap_write(PINNACLE_SYS_CONFIG, self._sys_config)

    @property
    def shutdown(self):
        """This attribute controls power of the touch controller. `True` means powered down (AKA
        standby mode), and `False` means not powered down (Active, Idle, or Sleep mode).

        .. note:: The touch controller will take about 300 milliseconds to complete the transition
            from powered down mode to active mode. No touch events or button presses will be
            monitored while powered down.
        """
        return bool(self._sys_config & 2)

    @shutdown.setter
    def shutdown(self, is_off):
        self._sys_config = (self._sys_config & 0xFD) | is_off << 1
        self._rap_write(PINNACLE_SYS_CONFIG, self._sys_config)

    def _rap_read(self, reg):
        """This function is overridden by the appropriate parent class based on interface type."""
        raise NotImplementedError()

    def _rap_read_bytes(self, reg, numb_bytes):
        """This function is overridden by the appropriate parent class based on interface type."""
        raise NotImplementedError()

    def _rap_write(self, reg, value):
        """This function is overridden by the appropriate parent class based on interface type."""
        raise NotImplementedError()

    def _rap_write_bytes(self, reg, value):
        """This function is overridden by the appropriate parent class based on interface type."""
        raise NotImplementedError()

    def _era_read(self, reg):
        self._rap_write_bytes(PINNACLE_ERA_ADDR_HIGH, [reg >> 8, reg & 0xff])
        self._rap_write(PINNACLE_ERA_CTRL, 1)  # indicate reading only 1 byte
        while self._rap_read(PINNACLE_ERA_CTRL):  # read until reg == 0
            pass  # also sets Command Complete flag in Status register
        buf = self._rap_read(PINNACLE_ERA_VALUE)  # get value
        self.clear_flags()
        return buf

    def _era_read_bytes(self, reg, numb_bytes):
        buf = []
        self._rap_write_bytes(PINNACLE_ERA_ADDR_HIGH, [reg >> 8, reg & 0xff])
        # indicate reading sequential bytes
        self._rap_write(PINNACLE_ERA_CTRL, 5)
        for _ in range(numb_bytes):
            while self._rap_read(PINNACLE_ERA_CTRL):  # read until reg == 0
                pass  # also sets Command Complete flag in Status register
            buf.append(self._rap_read(PINNACLE_ERA_VALUE))  # get value
            self.clear_flags()
        return buf

    def _era_write(self, reg, value):
        self._rap_write(PINNACLE_ERA_VALUE, value)  # write value
        self._rap_write_bytes(PINNACLE_ERA_ADDR_HIGH, [reg >> 8, reg & 0xff])
        self._rap_write(PINNACLE_ERA_CTRL, 2)  # indicate writing only 1 byte
        while self._rap_read(PINNACLE_ERA_CTRL):  # read until reg == 0
            pass  # also sets Command Complete flag in Status register
        self.clear_flags()

    def _era_write_bytes(self, reg, value, numb_bytes):
        self._rap_write(PINNACLE_ERA_VALUE, value)  # write value
        self._rap_write_bytes(PINNACLE_ERA_ADDR_HIGH, [reg >> 8, reg & 0xff])
        # indicate writing sequential bytes
        self._rap_write(PINNACLE_ERA_CTRL, 0x0A)
        for _ in range(numb_bytes):
            while self._rap_read(PINNACLE_ERA_CTRL):  # read until reg == 0
                pass  # also sets Command Complete flag in Status register
            self.clear_flags()

# due to use adafruit_bus_device, pylint can't find bus-specific functions
# pylint: disable=no-member
class PinnacleTouchI2C(PinnacleTouch):
    """
    Varaiant of the base class, `PinnacleTouch`, for interfacing with the touch controller via
    the I2C protocol.

    :param ~busio.I2C i2c: The object of the I2C bus to use. This object must be shared among
        other driver classes that use the same I2C bus (SDA & SCL pins).
    :param int address: The slave I2C address of the touch controller. Defaults to ``0x2A``.

    See the base class for other instantiating parameters.
    """

    def __init__(self, i2c, dr_pin=None, address=0x2A, feed_enable=True, allow_sleep=False):
        self._i2c = I2CDevice(i2c, (address << 1))
        super(PinnacleTouchI2C, self).__init__(dr_pin=dr_pin, feed_enable=feed_enable,
                                               allow_sleep=allow_sleep)

    def _rap_read(self, reg):
        return self._rap_read_bytes(reg)

    def _rap_read_bytes(self, reg, numb_bytes=1):
        self._i2c.device_address &= 0  # set write flag
        buf = bytearray([reg | 0xA0])  # per datasheet
        with self._i2c as i2c:
            i2c.write(buf)  # includes a STOP condition
        self._i2c.device_address &= 1  # set read flag
        return_buf = b''  # for accumulating response(s)
        buf = bytearray(1)
        with self._i2c as i2c:
            # need to send the ((address << 1) & read flag) for each byte read
            for _ in range(numb_bytes):  # increments register for each read command
                i2c.readinto(buf)  # I assume this includes a STOP condition
                return_buf += buf  # save response
        return list(return_buf)

    def _rap_write(self, reg, value):
        self._i2c.device_address &= 0  # set write flag
        buf = bytearray([reg | 0x80, value & 0xFF])  # assumes value is an int
        with self._i2c as i2c:
            i2c.write(buf)  # includes STOP condition

    def _rap_write_bytes(self, reg, value):
        self._i2c.device_address &= 0  # set write flag
        buf = b''
        for byte in value:  # works for bytearrays/lists/tuples
            buf += bytearray([reg | 0x80, byte])
        with self._i2c as i2c:
            # need only 1 STOP condition for multiple write operations
            i2c.write(buf)

class PinnacleTouchSPI(PinnacleTouch):
    """
    Varaiant of the base class, `PinnacleTouch`, for interfacing with the touch controller via
    the SPI protocol.

    :param ~busio.SPI spi: The object of the SPI bus to use. This object must be shared among
        other driver classes that use the same SPI bus (MOSI, MISO, & SCK pins).
    :param ~microcontroller.Pin ss_pin: The "slave select" pin output to the touch controller.

    See the base class for other instantiating parameters.
    """

    def __init__(self, spi, ss_pin, dr_pin=None, feed_enable=True, allow_sleep=False):
        # MAX baudrate is up to 13MHz; use 10MHz to be safe
        self._spi = SPIDevice(spi, chip_select=ss_pin,
                              baudrate=12000000, phase=1)
        super(PinnacleTouchSPI, self).__init__(dr_pin=dr_pin, feed_enable=feed_enable,
                                               allow_sleep=allow_sleep)

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
        return list(buf_in[3:])

    def _rap_write(self, reg, value):
        buf = bytearray([(reg | 0x80), value])
        with self._spi as spi:
            spi.write(buf)

    def _rap_write_bytes(self, reg, value):
        for i, val in enumerate(value):
            self._rap_write(reg + i, val)
# pylint: enable=no-member

class TrackBall:
    """A helper class imtended to emulate trackball mouse movement using the Cirque Pinnacle touch
    controller.

    .. important:: The data report used to emulate trackball mouse behavior is expected to be in
        `REL_MODE`.
    """
    def __init__(self, friction=0.5):
        # init internal attributes
        self._delta_xy = []  # index 0 = x_axis, index 1 = y_axis
        self._theta = 0
        self._radius = 0
        self.friction = friction

    def move(self, reported):
        """This function reads any data reported by the Pinnacle touch controller and
        calculates the movement of the emulated trackball based on the data received."""
        if reported is not None and unpack('H', reported[1:3])[0] > 0:
            self._delta_xy.append(unpack('bb', reported[1:3]))
            late_index = len(self._delta_xy) - 1
            self._radius = 0
            for delta in self._delta_xy:
                radius = math.sqrt(delta[0] ** 2.0 + delta[1] ** 2)
                self._radius += radius
            self._radius = max(self._radius, 127)
            self._theta = math.atan2(self._delta_xy[late_index][1], self._delta_xy[late_index][0])
            return reported[1:3]
        # elif reported is None:
        self._delta_xy.clear() # dispose of delta samples; now ready for next touch event
        if self._radius:  # if self._radius != 0
            # reduce radius by a factor of friction until friction is larger than radius
            self._radius *= self.friction if self._radius > math.ceil(self.friction) else 0
            return pack('bb',
                        int(math.cos(self._theta) * self._radius) & 0xff,
                        int(math.sin(self._theta) * self._radius) & 0xff)
        # elif self._radius == 0:
        return b'\x00' * 2 # return null movement
