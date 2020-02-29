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
from adafruit_bus_device.spi_device import SPIDevice
from adafruit_bus_device.i2c_device import I2CDevice

# internal registers
# pylint: disable=bad-whitespace
# PINNACLE_FIRMWARE_ID           = 0x00 # Firmware ASIC ID
# PINNACLE_FIRMWARE_VER          = 0x01 # Firmware revision number
PINNACLE_STATUS                = 0x02 # Contains status flags about the state of Pinnacle
PINNACLE_SYS_CONFIG            = 0x03 # Contains system operation and configuration bits
PINNACLE_FEED_CONFIG1          = 0x04 # Contains feed operation and configuration bits
PINNACLE_FEED_CONFIG2          = 0x05 # Contains feed operation and configuration bits
PINNACLE_FEED_CONFIG3          = 0x06 # Contains feed operation and configuration bits
PINNACLE_CALIBRATE_CONFIG      = 0x07 # Contains calibration configuration bits
# PINNACLE_PS_2_AUX_CTRL         = 0x08 # Contains Data register for PS/2 Aux Control
PINNACLE_SAMPLE_RATE           = 0x09 # Number of samples generated per second
PINNACLE_Z_IDLE                = 0x0A # Number of Z=0 packets sent when Z goes from >0 to 0
PINNACLE_Z_SCALAR              = 0x0B # Contains the pen Z_On threshold
# PINNACLE_SLEEP_INTERVAL        = 0x0C # No description
# PINNACLE_SLEEP_TIMER           = 0x0D # No description
# PINNACLE_EMI_THRESHOLD         = 0x0E # Threshold to adjust EMI settings
PINNACLE_PACKET_BYTE_0         = 0x12 # trackpad Data
PINNACLE_PACKET_BYTE_1         = 0x13 # trackpad Data
PINNACLE_PACKET_BYTE_2         = 0x14 # trackpad Data
PINNACLE_PACKET_BYTE_3         = 0x15 # trackpad Data
PINNACLE_PACKET_BYTE_4         = 0x16 # trackpad Data
PINNACLE_PACKET_BYTE_5         = 0x17 # trackpad Data
PINNACLE_PORTA_GPIO_CTRL       = 0x18 # Control of Port A GPIOs
PINNACLE_PORTA_GPIO_DATA       = 0x19 # Data of Port A GPIOs
PINNACLE_PORTB_GPIO_CTRL_DATA  = 0x1A # Control and Data of PortB GPIOs
PINNACLE_ERA_VALUE             = 0x1B # Value for extended register access
PINNACLE_ERA_ADDR_HIGH         = 0x1C # High byte of 16 bit extended register address
PINNACLE_ERA_ADDR_LOW          = 0x1D # Low byte of 16 bit extended register address
PINNACLE_ERA_CTRL              = 0x1E # Control of extended register access
# PINNACLE_PRODUCT_ID            = 0x1F # Product ID
# pylint: enable=bad-whitespace
# pylint: disable=too-many-arguments

def twos_comp(data, bits):
    """return integer representation of ``data`` in 2's compliment form using a
    specified number of ``bits`` """
    mask = 1 << (bits - 1)
    if data & mask:
        return -1 * mask + (data & ~mask)
    return data

class PinnacleTouch:
    """
    The abstract base class for driving the Pinnacle touch controller.

    :param ~microcontroller.Pin dr_pin: The input pin connected to the touch controller's "Data
        Ready" pin.
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
    def __init__(self, dr_pin, relative=True, invert_x=False, invert_y=False,
                 feed_enable=True, allow_sleep=False, z_idle_count=30):
        self.dr_pin = dr_pin
        self.dr_pin.switch_to_input()
        # init internal attribute and set user defined values
        self._feed_config1 = invert_y << 7 | invert_x << 6 | (not relative) << 1 | feed_enable
        self._feed_config2 = self._rap_read(PINNACLE_FEED_CONFIG2)
        self._sample_rate = self._rap_read(PINNACLE_SAMPLE_RATE)
        self._sys_config = allow_sleep << 2
        self._z_idle_count = z_idle_count
        with self:
            self.clear_flags() # clear any "Command Complete" and "Data Ready" flags

    def __enter__(self):
        self._rap_write_bytes(PINNACLE_FEED_CONFIG1, [self._feed_config1, self._feed_config2])
        self._rap_write_bytes(PINNACLE_SAMPLE_RATE, [self._sample_rate, self._z_idle_count])
        self._rap_write(PINNACLE_SYS_CONFIG, self._sys_config)

    def __exit__(self, *exc):
        return False

    def _read_reg_values(self):
        # this is called on init() and reset()
        self._feed_config1, self._feed_config2 = self._rap_read_bytes(PINNACLE_FEED_CONFIG1, 2)
        self._sample_rate, self._z_idle_count = self._rap_read_bytes(PINNACLE_SAMPLE_RATE, 2)
        self._sys_config = self._rap_read(PINNACLE_SYS_CONFIG)

    @property
    def mouse_mode(self):
        """A helper attribute to verify which mode the data report is configured for. (read-only)

        Use `set_data_mode()` to change this attribute.

        :Returns: `True` for Relative mode (AKA mouse mode) or `False` for Absolute mode.
        """
        return bool(not self._feed_config1 & 2)

    def set_data_mode(self, relative=True, invert_x=False, invert_y=False):
        """ Set the mode in which the data is reported. (write only)

        :param bool relative: Specifies if the data reported is relative (`True` -- change since
            last event) or absolute (`False` -- exact position on sensor). Default is `True`.

            .. note:: Relative mode is also referred to as "Mouse Mode" in the datasheet.
        :param bool invert_x: Specifies if the x-axis data is to be inverted before reporting it.
            Default is `False`.
        :param bool invert_y: Specifies if the y-axis data is to be inverted before reporting it.
            Default is `False`.
        """
        self._feed_config1 = (self._feed_config1 & 0x3D) | invert_y << 7 | invert_x << 6 | (
            not relative) << 1
        self._rap_write(PINNACLE_FEED_CONFIG1, self._feed_config1)

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

    @property
    def feed_enable(self):
        """This `bool` attribute controls if the touch data is reported (`True`) or not
        (`False`)."""
        return bool(self._feed_config1 & 1)

    @feed_enable.setter
    def feed_enable(self, is_on):
        if self.feed_enable != is_on: # save ourselves the unnecessary transaction
            self._feed_config1 = self._rap_read(PINNACLE_FEED_CONFIG1)
            self._feed_config1 = (self._feed_config1 & 0xFE) | is_on
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
            pass # calibration is running
        if run:
            self.clear_flags()

    def report(self):
        """This function will return touch event data from the touch controller (if there is any
        new data ready to report -- including empty packets on ending of a touch event).

        :Returns: `None` if there is no new data to report ("dr_pin" is low). Otherwise, a
            `list` or `bytearray` of parameters that describe the (touch or button) event.
            The structure is as follows:

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
            xy-plane's origin is located to the top-left, unless ``invert-x`` or ``invert-y``
            parameters to `set_data_mode()` are manipulated to change the perspective location
            of the origin.

        :Button Data:
            The returned button data is a byte in which each bit represents a button.
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
        temp = [] # placeholder for data reception
        return_vals = None
        if self.dr_pin.value:
            if self._feed_config1 & 2: # if absolute mode
                temp = self._rap_read_bytes(PINNACLE_PACKET_BYTE_0, 6)
                return_vals = [temp[0] & 0x3F, # buttons
                               ((temp[4] & 0x0F) << 8) | temp[2], # x
                               ((temp[4] & 0xF0) << 4) | temp[3], # y
                               temp[5] & 0x3F] # z
            else: # if in relative mode
                is_intellimouse = self._feed_config2 & 1
                # get relative data packets
                temp = self._rap_read_bytes(PINNACLE_PACKET_BYTE_0, 3 + is_intellimouse)
                return_vals = bytearray([temp[0] & 7, temp[1], temp[2]])
                if is_intellimouse: # scroll wheel data is captured
                    return_vals += bytes([temp[3]])
                else: # append empty byte to suite mouse HID reports
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
            self.feed_enable = False # accessing raw memory, so do this
            val = self._era_read(0x0187) & 0x3F
            val |= sensitivity << 6
            self._era_write(0x0187, val)
            self.feed_enable = prev_feed_state # resume normal operation
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
        self.feed_enable = False # accessing raw memory, so do this
        # write x_axis_wide_z_min value
        # self._era_read(0x0149) # this was used for printing unaltered value to serial monitor
        self._era_write(0x0149, x_axis_wide_z_min)
        # ERA_ReadBytes(0x0149) # this was used for printing verified value to serial monitor
        # write y_axis_wide_z_min value
        # self._era_read(0x0168) # this was used for printing unaltered value to serial monitor
        self._era_write(0x0168, y_axis_wide_z_min)
        # ERA_ReadBytes(0x0168) # this was used for printing verified value to serial monitor
        self.feed_enable = prev_feed_state # resume normal operation

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
        time.sleep(0.00005) # delay 50 microseconds per official example from Cirque

    def reset_device(self):
        """Resets the touch controller. (write only)

        .. warning:: Resetting the touch controller will change all register configurations to
            their default values which will be reflected in the `PinnacleTouch` object's
            attributes. Calibration is also automatically performed as it part of the touch
            controller's start-up sequence (unavoidable).
        """
        self._sys_config = self._rap_read(PINNACLE_SYS_CONFIG)
        self._sys_config = (self._sys_config & 0xFE) | 1
        self._rap_write(PINNACLE_SYS_CONFIG, self._sys_config)
        while not self.dr_pin.value:
            pass # wait for power-on & calibration to be performed
        self._read_reg_values()
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
        self._rap_write(PINNACLE_ERA_CTRL, 1) # indicate reading only 1 byte
        while self._rap_read(PINNACLE_ERA_CTRL): # read until reg == 0
            pass # also sets Command Complete flag in Status register
        buf = self._rap_read(PINNACLE_ERA_VALUE) # get value
        self.clear_flags()
        return buf

    def _era_read_bytes(self, reg, numb_bytes):
        buf = []
        self._rap_write_bytes(PINNACLE_ERA_ADDR_HIGH, [reg >> 8, reg & 0xff])
        self._rap_write(PINNACLE_ERA_CTRL, 5) # indicate reading sequential bytes
        for _ in range(numb_bytes):
            while self._rap_read(PINNACLE_ERA_CTRL): # read until reg == 0
                pass # also sets Command Complete flag in Status register
            buf.append(self._rap_read(PINNACLE_ERA_VALUE)) # get value
            self.clear_flags()
        return buf

    def _era_write(self, reg, value):
        self._rap_write(PINNACLE_ERA_VALUE, value) # write value
        self._rap_write_bytes(PINNACLE_ERA_ADDR_HIGH, [reg >> 8, reg & 0xff])
        self._rap_write(PINNACLE_ERA_CTRL, 2) # indicate writing only 1 byte
        while self._rap_read(PINNACLE_ERA_CTRL): # read until reg == 0
            pass # also sets Command Complete flag in Status register
        self.clear_flags()

    def _era_write_bytes(self, reg, value, numb_bytes):
        self._rap_write(PINNACLE_ERA_VALUE, value) # write value
        self._rap_write_bytes(PINNACLE_ERA_ADDR_HIGH, [reg >> 8, reg & 0xff])
        self._rap_write(PINNACLE_ERA_CTRL, 0x0A) # indicate writing sequential bytes
        for _ in range(numb_bytes):
            while self._rap_read(PINNACLE_ERA_CTRL): # read until reg == 0
                pass # also sets Command Complete flag in Status register
            self.clear_flags()

class PinnacleTouchI2C(PinnacleTouch):
    """
    Varaiant of the base class, `PinnacleTouch`, for interfacing with the touch controller via
    the I2C protocol.

    :param ~busio.I2C i2c: The object of the I2C bus to use. This object must be shared among
        other driver classes that use the same I2C bus (SDA & SCL pins).
    :param int address: The slave I2C address of the touch controller. Defaults to ``0x2A``.

    See the base class for other instantiating parameters.
    """

    def __init__(self, i2c, dr_pin, address=0x2A, relative=True, invert_x=False, invert_y=False,
                 feed_enable=True, allow_sleep=False, z_idle_count=30):
        self._i2c = I2CDevice(i2c, (address << 1))
        super(PinnacleTouchI2C, self).__init__(dr_pin, relative=relative, invert_x=invert_x,
                                               invert_y=invert_y, feed_enable=feed_enable,
                                               allow_sleep=allow_sleep, z_idle_count=z_idle_count)

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

    def __init__(self, spi, ss_pin, dr_pin, relative=True, invert_x=False, invert_y=False,
                 feed_enable=True, allow_sleep=False, z_idle_count=30):
        # MAX baudrate is up to 13MHz; use 10MHz to be safe
        self._spi = SPIDevice(spi, chip_select=ss_pin, baudrate=12000000, phase=1)
        super(PinnacleTouchSPI, self).__init__(dr_pin, relative=relative, invert_x=invert_x,
                                               invert_y=invert_y, feed_enable=feed_enable,
                                               allow_sleep=allow_sleep, z_idle_count=z_idle_count)

    def _rap_read(self, reg):
        buf_out = bytearray([reg | 0xA0]) + b'\xFB' * 3
        buf_in = bytearray(len(buf_out))
        with self._spi as spi:
            spi.write_readinto(buf_out, buf_in)
        return buf_in[3]

    def _rap_read_bytes(self, reg, numb_bytes):
        buf_out = bytearray([reg | 0xA0]) + b'\xFC' * (1 + numb_bytes) + b'\xFB'
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
