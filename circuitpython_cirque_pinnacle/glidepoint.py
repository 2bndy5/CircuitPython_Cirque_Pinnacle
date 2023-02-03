"""
A driver class for the Cirque Pinnacle ASIC on the Cirque capacitive touch
based circular trackpads.
"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle.git"
import time
import struct

try:
    from typing import Optional, List, Union
except ImportError:
    pass

from micropython import const
import digitalio
import busio
from adafruit_bus_device.spi_device import SPIDevice
from adafruit_bus_device.i2c_device import I2CDevice

RELATIVE: int = const(0x00)
ANYMEAS: int = const(0x01)
ABSOLUTE: int = const(0x02)
GAIN_100: int = const(0xC0)  #: around 100% gain
GAIN_133: int = const(0x80)  #: around 133% gain
GAIN_166: int = const(0x40)  #: around 166% gain
GAIN_200: int = const(0x00)  #: around 200% gain
FREQ_0: int = const(0x02)  #: frequency around 500,000Hz
FREQ_1: int = const(0x03)  #: frequency around 444,444Hz
FREQ_2: int = const(0x04)  #: frequency around 400,000Hz
FREQ_3: int = const(0x05)  #: frequency around 363,636Hz
FREQ_4: int = const(0x06)  #: frequency around 333,333Hz
FREQ_5: int = const(0x07)  #: frequency around 307,692Hz
FREQ_6: int = const(0x09)  #: frequency around 267,000Hz
FREQ_7: int = const(0x0B)  #: frequency around 235,000Hz
MUX_REF1: int = const(0x10)  #: enables a builtin capacitor (~0.5pF).
MUX_REF0: int = const(0x08)  #: enables a builtin capacitor (~0.25pF).
MUX_PNP: int = const(0x04)  #: enable PNP sense line
MUX_NPN: int = const(0x01)  #: enable NPN sense line
CRTL_REPEAT: int = const(0x80)  #: required for more than 1 measurement
CRTL_PWR_IDLE: int = const(
    0x40
)  #: triggers low power mode (sleep) after completing measurements


class PinnacleTouch:
    """The abstract base class for driving the Pinnacle ASIC.

    :param ~digitalio.DigitalInOut dr_pin: |dr_pin_parameter|

        .. important:: |dr_pin_note|

    .. |dr_pin_parameter| replace:: The input pin connected to the Pinnacle ASIC's "Data
        Ready" pin. If this parameter is not specified, then the SW_DR (software data ready) flag
        of the STATUS register is used to determine if the data being reported is new.

    .. |dr_pin_note| replace:: This parameter must be specified if your application is
        going to use the Pinnacle ASIC's
        :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS` mode (a rather
        experimental measuring of raw ADC values).
    """

    def __init__(self, dr_pin: Optional[digitalio.DigitalInOut] = None):
        self.dr_pin = dr_pin
        if self.dr_pin is not None:
            self.dr_pin.switch_to_input()
        firmware_id, firmware_ver = self._rap_read_bytes(0, 2)
        if firmware_id != 7 or firmware_ver != 0x3A:
            raise RuntimeError("Cirque Pinnacle ASIC not responding")
        # init internal attributes w/ factory defaults after power-on-reset
        self._mode = 0  # 0 means relative mode which is factory default
        self.detect_finger_stylus()
        self._rap_write(0x0A, 30)  # z-idle packet count
        self._rap_write_bytes(3, [0, 1, 2])  # configure relative mode
        self.set_adc_gain(0)
        self.calibrate(True)  # enables all compensations

    @property
    def feed_enable(self) -> bool:
        """This `bool` attribute controls if the touch/button event data is
        reported (`True`) or not (`False`).

        This function only applies to :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE`
        or :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE` mode. Otherwise if
        `data_mode` is set to :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS`,
        then this attribute will have no effect.
        """
        return bool(self._rap_read(4) & 1)

    @feed_enable.setter
    def feed_enable(self, is_on: bool):
        is_enabled = self._rap_read(4)
        if bool(is_enabled & 1) != is_on:
            # save ourselves the unnecessary transaction
            is_enabled = (is_enabled & 0xFE) | is_on
            self._rap_write(4, is_enabled)

    @property
    def data_mode(self) -> int:
        """This attribute controls which mode the data reports are configured
        for.

        Valid input values are :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE` for
        relative/mouse mode, :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE` for
        absolute positioning mode, or :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS`
        (referred to as "AnyMeas" in specification sheets) mode for reading ADC values.

        :Returns:

            - ``0`` for Relative mode (AKA mouse mode)
            - ``1`` for AnyMeas mode (raw ADC measurements)
            - ``2`` for Absolute mode (X & Y axis positions)

        .. important::
            When switching from :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS` to
            :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE` or
            :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE` all
            configurations are reset, and must be re-configured by using
            `absolute_mode_config()` or `relative_mode_config()`.
        """
        return self._mode

    @data_mode.setter
    def data_mode(self, mode: int):
        if mode not in (ANYMEAS, RELATIVE, ABSOLUTE):
            raise ValueError("Unrecognized input value for data_mode.")
        sys_config = self._rap_read(3) & 0xE7  # clear AnyMeas mode flags
        if mode in (RELATIVE, ABSOLUTE):
            if self.data_mode == ANYMEAS:  # if leaving AnyMeas mode
                # set mode flag, enable feed, disable taps in Relative mode
                self._rap_write_bytes(3, [sys_config, 1 | mode, 2])
                self.sample_rate = 100
                self._rap_write(7, 0x1E)  # enables all compensations
                self._rap_write(0x0A, 30)  # 30 z-idle packets
            else:  # not leaving AnyMeas mode
                self._rap_write(4, 1 | mode)  # set mode flag, enable feed
        else:  # for AnyMeas mode
            if self.dr_pin is None:  # AnyMeas requires the DR pin
                raise AttributeError(
                    "need the Data Ready (DR) pin specified for AnyMeas mode"
                )
            # disable tracking computations for AnyMeas mode
            self._rap_write(3, sys_config | 0x08)
            time.sleep(0.01)  # wait for tracking computations to expire
            self.anymeas_mode_config()  # configure registers for AnyMeas
        self._mode = mode

    @property
    def hard_configured(self) -> bool:
        """This read-only `bool` attribute can be used to inform applications about
        factory customized hardware configuration. See note about product labeling in
        `Model Labeling Scheme <index.html#cc>`_.

        :Returns:
            `True` if a 470K ohm resistor is populated at the junction labeled "R4"
        """
        return bool(self._rap_read(0x1F))

    def relative_mode_config(
        self,
        rotate90: bool = False,
        taps: bool = True,
        secondary_tap: bool = True,
        glide_extend: bool = True,
        intellimouse: bool = False,
    ):
        """Configure settings specific to Relative mode (AKA Mouse mode) data
        reporting.

        This function only applies to :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE`
        mode, otherwise if `data_mode` is set to
        :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS` or
        :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE`, then this function does nothing.

        :param rotate90: Specifies if the axis data is altered for 90 degree rotation before
            reporting it (essentially swaps the axis data). Default is `False`.
        :param taps: Specifies if all taps should be reported (`True`) or not
            (`False`). Default is `True`. This affects ``secondary_tap`` option as well.
        :param secondary_tap: Specifies if tapping in the top-left corner (depending on
            orientation) triggers the secondary button data. Defaults to `True`. This feature is
            always disabled if `hard_configured` is `True`.
        :param glide_extend: A patented feature that allows the user to glide their finger off
            the edge of the sensor and continue gesture with the touch event. Default is `True`.
            This feature is always disabled if `hard_configured` is `True`.
        :param intellimouse: Specifies if the data reported includes a byte about scroll data.
            Default is `False`. Because this flag is specific to scroll data, this feature is always
            disabled if `hard_configured` is `True`.
        """
        if self.data_mode == RELATIVE:
            config2 = (rotate90 << 7) | ((not glide_extend) << 4)
            config2 |= ((not secondary_tap) << 2) | ((not taps) << 1)
            self._rap_write(5, config2 | bool(intellimouse))

    def absolute_mode_config(
        self, z_idle_count: int = 30, invert_x: bool = False, invert_y: bool = False
    ):
        """Configure settings specific to Absolute mode (reports axis
        positions).

        This function only applies to :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE`
        mode, otherwise if `data_mode` is set to
        :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS` or
        :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE`, then this function does nothing.

        :param z_idle_count: Specifies the number of empty packets (x-axis, y-axis, and z-axis
            are ``0``) reported (every 10 milliseconds) when there is no touch detected. Defaults
            to 30. This number is clamped to range [0, 255].
        :param invert_x: Specifies if the x-axis data is to be inverted before reporting it.
            Default is `False`.
        :param invert_y: Specifies if the y-axis data is to be inverted before reporting it.
            Default is `False`.
        """
        if self.data_mode == ABSOLUTE:
            self._rap_write(0x0A, max(0, min(z_idle_count, 255)))
            config1 = self._rap_read(4) & 0x3F | (invert_y << 7)
            self._rap_write(4, config1 | (invert_x << 6))

    def available(self) -> bool:
        """Determine if there is fresh data to report.

        If the ``dr_pin`` parameter is specified upon instantiation, then the specified
        input pin is used to detect if the data is new. Otherwise the SW_DR flag in the
        STATUS register is used to determine if the data is new.

        :Return: If there is fresh data to report (`True`) or not (`False`).

        .. versionadded:: 0.0.5
        """
        if self.dr_pin is None:
            return bool(self._rap_read(2) & 4)
        return self.dr_pin.value

    def read(self) -> Optional[Union[List[int], bytearray]]:
        """This function will return touch event data from the Pinnacle ASIC
        (including empty packets on ending of a touch event).

        This function only applies to :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE`
        or :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE` mode. Otherwise if
        `data_mode` is set to :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS`, then this
        function returns `None` and does nothing.

        :Returns: A `list` or `bytearray` of parameters that describe the (touch or
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

                    0 |LessEq| X |LessEq| 2047 [4]_
                * - 2
                  - change in y-axis [2]_

                    -128 |LessEq| Y |LessEq| 127
                  - y-axis Position

                    0 |LessEq| Y |LessEq| 1535 [5]_
                * - 3
                  - change in scroll wheel [3]_

                    -128 |LessEq| SCROLL |LessEq| 127
                  - z-axis Magnitude

        .. [1] The returned button data is a byte in which each bit represents a button.
            The bit to button order is as follows:

            0. [LSB] Button 1 (thought of as Left button in Relative/Mouse mode). If ``taps``
               parameter is passed as `True` when calling `relative_mode_config()`, a single
               tap will be reflected here.
            1. Button 2 (thought of as Right button in Relative/Mouse mode). If ``taps`` and
               ``secondary_tap`` parameters are passed as `True` when calling
               `relative_mode_config()`, a single tap in the perspective top-left-most corner will
               be reflected here (secondary taps are constantly disabled if `hard_configured`
               returns `True`). Note that the top-left-most corner can be perspectively moved if
               ``rotate90`` parameter is passed as `True` when calling `relative_mode_config()`.
            2. Button 3 (thought of as Middle or scroll wheel button in Relative/Mouse mode)
        .. [2] The axis data reported in Relative/Mouse mode is in two's
            compliment form. Use Python's :py:func:`struct.unpack()` to convert the
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
        .. [4] The datasheet recommends the x-axis value (in Absolute mode) should be
            clamped to range 128 |LessEq| ``x`` |LessEq| 1920 for reliability.
        .. [5] The datasheet recommends the y-axis value (in Absolute mode) should be
            clamped to range 64 |LessEq| ``y`` |LessEq| 1472 for reliability.
        .. |LessEq| unicode:: U+2264

        .. versionchanged:: 0.0.5
            removed ``only_new`` parameter in favor of using `available()`.
        """
        if self._mode == ANYMEAS:
            return None
        return_vals: Optional[Union[List[int], bytearray]] = None
        if self.data_mode == ABSOLUTE:  # if absolute mode
            return_vals = list(self._rap_read_bytes(0x12, 6))
            return_vals[0] &= 0x3F  # buttons
            return_vals[2] |= (return_vals[4] & 0x0F) << 8  # x
            return_vals[3] |= (return_vals[4] & 0xF0) << 4  # y
            return_vals[5] &= 0x3F  # z
            del return_vals[4], return_vals[1]  # no longer need these
        elif self.data_mode == RELATIVE:  # if in relative mode
            return_vals = self._rap_read_bytes(0x12, 4)
            return_vals[0] &= 7
        self.clear_status_flags()
        return return_vals

    def clear_status_flags(self):
        """This function clears the "Data Ready" flag which is reflected with
        the ``dr_pin``."""
        self._rap_write(2, 0)
        time.sleep(0.00005)  # per official example from Cirque

    @property
    def allow_sleep(self) -> bool:
        """This attribute specifies if the Pinnacle ASIC is allowed to sleep
        after about 5 seconds of idle (no input event).

        Set this attribute to `True` if you want the Pinnacle ASIC to enter sleep (low power)
        mode after about 5 seconds of inactivity (does not apply to AnyMeas mode). While the touch
        controller is in sleep mode, if a touch event or button press is detected, the Pinnacle
        ASIC will take about 300 milliseconds to wake up (does not include handling the touch event
        or button press data).
        """
        return bool(self._rap_read(3) & 4)

    @allow_sleep.setter
    def allow_sleep(self, is_enabled: bool):
        self._rap_write(3, (self._rap_read(3) & 0xFB) | (is_enabled << 2))

    @property
    def shutdown(self) -> bool:
        """This attribute controls power of the Pinnacle ASIC. `True` means powered down
        (AKA standby mode), and `False` means not powered down (Active, Idle, or Sleep mode).

        .. note::
            The ASIC will take about 300 milliseconds to complete the transition
            from powered down mode to active mode. No touch events or button presses will be
            monitored while powered down.
        """
        return bool(self._rap_read(3) & 2)

    @shutdown.setter
    def shutdown(self, is_off: bool):
        self._rap_write(3, (self._rap_read(3) & 0xFD) | (is_off << 1))

    @property
    def sample_rate(self) -> int:
        """This attribute controls how many samples (of data) per second are reported.

        Valid values are ``100``, ``80``, ``60``, ``40``, ``20``, ``10``. Any other input values
        automatically set the sample rate to 100 sps (samples per second). Optionally, ``200`` and
        ``300`` sps can be specified, but using these values automatically disables palm (referred
        to as "NERD" in the specification sheet) and noise compensations. These higher values are
        meant for using a stylus with a 2mm diameter tip, while the values less than 200 are meant
        for a finger or stylus with a 5.25mm diameter tip.

        This attribute only applies to :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE`
        or :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE` mode. Otherwise if
        `data_mode` is set to :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS`, then
        this attribute will have no effect.
        """
        return self._rap_read(9)

    @sample_rate.setter
    def sample_rate(self, val: int):
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

    def detect_finger_stylus(
        self,
        enable_finger: bool = True,
        enable_stylus: bool = True,
        sample_rate: int = 100,
    ):
        """This function will configure the Pinnacle ASIC to detect either
        finger, stylus, or both.

        :param enable_finger: `True` enables the Pinnacle ASIC's measurements to
            detect if the touch event was caused by a finger or 5.25mm stylus. `False` disables
            this feature. Default is `True`.
        :param enable_stylus: `True` enables the Pinnacle ASIC's measurements to
            detect if the touch event was caused by a 2mm stylus. `False` disables this
            feature. Default is `True`.
        :param sample_rate: See the `sample_rate` attribute as this parameter manipulates that
            attribute.

        .. tip::
            Consider adjusting the ADC matrix's gain to enhance performance/results using
            `set_adc_gain()`
        """
        finger_stylus = self._era_read(0x00EB)
        finger_stylus |= (enable_stylus << 2) | enable_finger
        self._era_write(0x00EB, finger_stylus)
        self.sample_rate = sample_rate

    def calibrate(
        self,
        run: bool,
        tap: bool = True,
        track_error: bool = True,
        nerd: bool = True,
        background: bool = True,
    ):
        """Set calibration parameters when the Pinnacle ASIC calibrates
        itself.

        This function only applies to :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE`
        or :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE` mode. Otherwise if
        `data_mode` is set to :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS`, then this
        function will have no effect.

        :param run: If `True`, this function forces a calibration of the sensor. If `False`,
            this function just writes the following parameters to the Pinnacle ASIC's "CalConfig1"
            register. This parameter is required while the rest are optional keyword parameters.
        :param tap: Enable dynamic tap compensation? Default is `True`.
        :param track_error: Enable dynamic track error compensation? Default is `True`.
        :param nerd: Enable dynamic NERD compensation? Default is `True`. This parameter has
            something to do with palm detection/compensation.
        :param background: Enable dynamic background compensation? Default is `True`.

        .. note::
            According to the datasheet, calibration of the sensor takes about 100
            milliseconds. This function will block until calibration is complete (if ``run`` is
            `True`). It is recommended for typical applications to leave all optional parameters
            in their default states.
        """
        if self.data_mode != ANYMEAS:
            cal_config = (tap << 4) | (track_error << 3) | (nerd << 2)
            cal_config |= background << 1
            self._rap_write(7, cal_config | run)
            if run:
                while self._rap_read(7) & 1:
                    pass  # calibration is running
                self.clear_status_flags()  # now that calibration is done

    @property
    def calibration_matrix(self) -> List[int]:
        """This attribute returns a `list` of the 46 signed 16-bit (short)
        values stored in the Pinnacle ASIC's memory that is used for taking
        measurements.

        This matrix is not applicable in AnyMeas mode. Use this attribute to compare a prior
        compensation matrix with a new matrix that was either loaded manually by setting this
        attribute to a `list` of 46 signed 16-bit (short) integers or created internally by calling
        `calibrate()` with the ``run`` parameter as `True`.

        .. note::
            A paraphrased note from Cirque's Application Note on Comparing compensation matrices:

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
        # combine every 2 bytes from resulting buffer into list of signed
        # 16-bits integers
        return list(struct.unpack("46h", self._era_read_bytes(0x01DF, 92)))

    @calibration_matrix.setter
    def calibration_matrix(self, matrix: List[int]):
        matrix += [0] * (46 - len(matrix))  # pad short matrices w/ 0s
        for index in range(46):
            buf = struct.pack("h", matrix[index])
            self._era_write(0x01DF + index * 2, buf[0])
            self._era_write(0x01DF + index * 2 + 1, buf[1])

    def set_adc_gain(self, sensitivity: int):
        """Sets the ADC gain in range [0,3] to enhance performance based on
        the overlay type (does not apply to AnyMeas mode).

        :param int sensitivity: This int specifies how sensitive the ADC (Analog to Digital
            Converter) component is. ``0`` means most sensitive, and ``3`` means least sensitive.
            A value outside this range will raise a `ValueError` exception.

        .. tip:: The official example code from Cirque for a curved overlay uses a value of ``1``.
        """
        if not 0 <= sensitivity < 4:
            raise ValueError("sensitivity is out of bounds [0,3]")
        val = self._era_read(0x0187) & 0x3F | (sensitivity << 6)
        self._era_write(0x0187, val)

    def tune_edge_sensitivity(
        self, x_axis_wide_z_min: int = 0x04, y_axis_wide_z_min: int = 0x03
    ):
        """Changes thresholds to improve detection of fingers.

        .. warning::
            This function was ported from Cirque's example code and doesn't seem to have
            corresponding documentation. I'm having trouble finding a memory map of the Pinnacle
            ASIC as this function directly alters values in the Pinnacle ASIC's memory.
            USE AT YOUR OWN RISK!
        """
        self._era_write(0x0149, x_axis_wide_z_min)
        self._era_write(0x0168, y_axis_wide_z_min)

    def anymeas_mode_config(
        self,
        gain: int = GAIN_200,
        frequency: int = FREQ_0,
        sample_length: int = 512,
        mux_ctrl: int = MUX_PNP,
        apperture_width: int = 500,
        ctrl_pwr_cnt: int = 1,
    ):
        """This function configures the Pinnacle ASIC to output raw ADC
        measurements.

        Be sure to set the `data_mode` attribute to
        :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS` before calling this function
        otherwise it will do nothing.

        :param gain: Sets the sensitivity of the ADC matrix. Valid values are the constants
            defined in `AnyMeas mode Gain`_. Defaults to
            :attr:`~circuitpython_cirque_pinnacle.glidepoint.GAIN_200`.
        :param frequency: Sets the frequency of measurements made by the ADC matrix. Valid
            values are the constants defined in `AnyMeas mode Frequencies`_.
            Defaults :attr:`~circuitpython_cirque_pinnacle.glidepoint.FREQ_0`.
        :param sample_length: Sets the maximum bit length of the measurements made by the ADC
            matrix. Valid values are ``128``, ``256``, or ``512``. Defaults to ``512``.
        :param mux_ctrl: The Pinnacle ASIC can employ different bipolar junctions
            and/or reference capacitors. Valid values are the constants defined in
            `AnyMeas mode Muxing`_. Additional combination of
            these constants is also allowed. Defaults to
            :attr:`~circuitpython_cirque_pinnacle.glidepoint.MUX_PNP`.
        :param apperture_width: Sets the window of time (in nanoseconds) to allow for the ADC
            to take a measurement. Valid values are multiples of 125 in range [``250``, ``1875``].
            Erroneous values are clamped/truncated to this range.

            .. note:: The ``apperture_width`` parameter has a inverse relationship/affect on the
                ``frequency`` parameter. The approximated frequencies described in this
                documentation are based on an aperture width of 500 nanoseconds, and they will
                shrink as the apperture width grows or grow as the aperture width shrinks.

        :param ctrl_pwr_cnt: Configure the Pinnacle to perform a number of measurements for
            each call to `measure_adc()`. Defaults to 1. Constants defined in
            `AnyMeas mode Control`_ can be used to specify if is sleep
            is allowed (:attr:`~circuitpython_cirque_pinnacle.glidepoint.CRTL_PWR_IDLE` -- this
            is not default) or if repetitive measurements is allowed
            (:attr:`~circuitpython_cirque_pinnacle.glidepoint.CRTL_REPEAT`) if number of
            measurements is more than 1.

            .. warning::
                There is no bounds checking on the number of measurements specified
                here. Specifying more than 63 will trigger sleep mode after performing
                measurements.

            .. tip::
                Be aware that allowing the Pinnacle to enter sleep mode after taking
                measurements will slow consecutive calls to `measure_adc()` as the Pinnacle
                requires about 300 milliseconds to wake up.
        """
        if self.data_mode == ANYMEAS:
            anymeas_config = [2, 3, 4, 0, 4, 0, 19, 0, 0, 1]
            anymeas_config[0] = gain | frequency
            anymeas_config[1] = max(1, min(int(sample_length / 128), 3))
            anymeas_config[2] = mux_ctrl
            anymeas_config[4] = max(2, min(int(apperture_width / 125), 15))
            anymeas_config[9] = ctrl_pwr_cnt
            self._rap_write_bytes(5, anymeas_config)
            self._rap_write_bytes(0x13, [0] * 8)
            self.clear_status_flags()

    def measure_adc(self, bits_to_toggle: int, toggle_polarity: int) -> bytearray:
        """This blocking function instigates and returns the measurements (a
        signed short) from the Pinnacle ASIC's ADC (Analog to Digital Converter) matrix.

        Internally this function calls `start_measure_adc()` and `get_measure_adc()` in sequence.
        Be sure to set the `data_mode` attribute to
        :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS` before calling this function
        otherwise it will do nothing.

        :Parameters' Context:
            Each of the parameters are a 4-byte integer (see
            :ref:`format table below <polynomial-fmt>`) in which each bit corresponds to a
            capacitance sensing electrode in the sensor's matrix (12 electrodes for Y-axis, 16
            electrodes for X-axis). They are used to compensate for varying capacitances in
            the electrodes during measurements. **It is highly recommended that the trackpad be
            installed in a finished/prototyped housing when determining what electrodes to
            manipulate.** See `AnyMeas mode example <examples.html#anymeas-mode-example>`_ to
            understand how to use these 4-byte integers.

        :param bits_to_toggle: A bit of ``1`` flags that electrode's output for toggling, and a bit
            of ``0`` signifies that the electrode's output should remain unaffected.
        :param toggle_polarity: This specifies which polarity the output of the electrode(s)
            (specified with corresponding bits in ``bits_to_toggle`` parameter) should be toggled
            (forced). A bit of ``1`` toggles that bit positive, and a bit of ``0`` toggles that
            bit negative.

        :Returns:
            A 2-byte `bytearray` that represents a signed short integer. If `data_mode` is not set
            to :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS`, then this function returns
            `None` and does nothing.

        .. _polynomial-fmt:

        :4-byte Integer Format:
            Bits 31 & 30 are not used and should remain ``0``. Bits 29 and 28 represent the optional
            implementation of reference capacitors built into the Pinnacle ASIC. To use these
            capacitors, the corresponding constants
            (:attr:`~circuitpython_cirque_pinnacle.glidepoint.MUX_REF0` and/or
            :attr:`~circuitpython_cirque_pinnacle.glidepoint.MUX_REF1`) must be passed to
            `anymeas_mode_config()` in the ``mux_ctrl`` parameter, and their representative
            bits must be flagged in both ``bits_to_toggle`` & ``toggle_polarity`` parameters.

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
        """
        self.start_measure_adc(bits_to_toggle, toggle_polarity)
        result = self.get_measure_adc()
        while result is None:  # wait till measurements are complete
            result = self.get_measure_adc()  # Pinnacle is still computing
        return result

    def start_measure_adc(self, bits_to_toggle: int, toggle_polarity: int):
        """A non-blocking function that starts measuring ADC values in
        AnyMeas mode.

        See the parameters and table in `measure_adc()` as this is its helper function, and all
        parameters there are used the same way here.
        """
        if self._mode == ANYMEAS:
            tog_pol: List[int] = []  # assemble list of register buffers
            for i in range(3, -1, -1):
                tog_pol.append((bits_to_toggle >> (i * 8)) & 0xFF)
            for i in range(3, -1, -1):
                tog_pol.append((toggle_polarity >> (i * 8)) & 0xFF)
            # write toggle and polarity parameters to register 0x13 - 0x1A
            self._rap_write_bytes(0x13, tog_pol)
            # initiate measurements
            self._rap_write(3, self._rap_read(3) | 0x18)

    def get_measure_adc(self) -> Optional[bytearray]:
        """A non-blocking function that returns ADC measurement on
        completion.

        This function is only meant ot be used in conjunction with `start_measure_adc()` for
        non-blocking application.

        :returns:
            * `None` if `data_mode` is not set to `ANYMEAS` or if the "data ready" pin's signal is
              not active (while `data_mode` is set to `ANYMEAS`) meaning the Pinnacle ASIC is still
              computing the ADC measurements based on the 4-byte polynomials passed to
              `start_measure_adc()`.
            * a `bytearray` that represents a signed 16-bit integer upon completed ADC measurements
              based on the 4-byte polynomials passed to `start_measure_adc()`.
        """
        if self._mode != ANYMEAS:
            return None
        if self.dr_pin is not None and not self.dr_pin.value:
            return None
        result = self._rap_read_bytes(0x11, 2)
        self.clear_status_flags()
        return result

    def _rap_read(self, reg: int) -> int:
        raise NotImplementedError()

    def _rap_read_bytes(self, reg: int, numb_bytes: int) -> bytearray:
        raise NotImplementedError()

    def _rap_write(self, reg: int, value: int):
        raise NotImplementedError()

    def _rap_write_bytes(self, reg: int, values: List[int]):
        raise NotImplementedError()

    def _era_read(self, reg: int) -> int:
        prev_feed_state = self.feed_enable
        self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write_bytes(0x1C, [reg >> 8, reg & 0xFF])
        self._rap_write(0x1E, 1)  # indicate reading only 1 byte
        while self._rap_read(0x1E):  # read until reg == 0
            pass  # also sets Command Complete flag in Status register
        buf = self._rap_read(0x1B)  # get value
        self.clear_status_flags()
        self.feed_enable = prev_feed_state  # resume previous feed state
        return buf

    def _era_read_bytes(self, reg: int, numb_bytes: int) -> bytes:
        buf = b""
        prev_feed_state = self.feed_enable
        self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write_bytes(0x1C, [reg >> 8, reg & 0xFF])
        for _ in range(numb_bytes):
            self._rap_write(0x1E, 5)  # indicate reading sequential bytes
            while self._rap_read(0x1E):  # read until reg == 0
                pass  # also sets Command Complete flag in Status register
            buf += bytes([self._rap_read(0x1B)])  # get value
            self.clear_status_flags()
        self.feed_enable = prev_feed_state  # resume previous feed state
        return buf

    def _era_write(self, reg: int, value: int):
        prev_feed_state = self.feed_enable
        self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write(0x1B, value)  # write value
        self._rap_write_bytes(0x1C, [reg >> 8, reg & 0xFF])
        self._rap_write(0x1E, 2)  # indicate writing only 1 byte
        while self._rap_read(0x1E):  # read until reg == 0
            pass  # also sets Command Complete flag in Status register
        self.clear_status_flags()
        self.feed_enable = prev_feed_state  # resume previous feed state

    def _era_write_bytes(self, reg: int, value: int, numb_bytes: int):
        # rarely used as it only writes 1 value to multiple registers
        prev_feed_state = self.feed_enable
        self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write(0x1B, value)  # write value
        self._rap_write_bytes(0x1C, [reg >> 8, reg & 0xFF])
        self._rap_write(0x1E, 0x0A)  # indicate writing sequential bytes
        for _ in range(numb_bytes):
            while self._rap_read(0x1E):  # read until reg == 0
                pass  # also sets Command Complete flag in Status register
            self.clear_status_flags()
        self.feed_enable = prev_feed_state  # resume previous feed state


# pylint: disable=no-member
class PinnacleTouchI2C(PinnacleTouch):
    """Parent class for interfacing with the Pinnacle ASIC via the I2C
    protocol.

    :param ~busio.I2C i2c: The object of the I2C bus to use. This object must be shared among
        other driver classes that use the same I2C bus (SDA & SCL pins).
    :param int address: The slave I2C address of the Pinnacle ASIC. Defaults to ``0x2A``.
    :param ~digitalio.DigitalInOut dr_pin: |dr_pin_parameter|

        .. important:: |dr_pin_note|
    """

    def __init__(
        self,
        i2c: busio.I2C,
        address: int = 0x2A,
        dr_pin: Optional[digitalio.DigitalInOut] = None,
    ):
        self._i2c = I2CDevice(i2c, address)
        super().__init__(dr_pin=dr_pin)

    def _rap_read(self, reg: int) -> int:
        return self._rap_read_bytes(reg, 1)[0]

    def _rap_read_bytes(self, reg: int, numb_bytes: int) -> bytearray:
        buf = bytes([reg | 0xA0])  # per datasheet
        with self._i2c as i2c:
            i2c.write(buf)  # includes a STOP condition
            buf = bytearray(numb_bytes)  # for response(s)
            # auto-increments register for each byte read
            i2c.readinto(buf)
        return buf

    def _rap_write(self, reg: int, value: int):
        self._rap_write_bytes(reg, [value])

    def _rap_write_bytes(self, reg: int, values: List[int]):
        buf = b""
        for index, byte in enumerate(values):
            # Pinnacle doesn't auto-increment register
            # addresses for I2C write operations
            # Also truncate int elements of a list/tuple
            buf += bytes([(reg + index) | 0x80, byte & 0xFF])
        with self._i2c as i2c:
            i2c.write(buf)


class PinnacleTouchSPI(PinnacleTouch):
    """Parent class for interfacing with the Pinnacle ASIC via the SPI
    protocol.

    :param ~busio.SPI spi: The object of the SPI bus to use. This object must be shared among
        other driver classes that use the same SPI bus (MOSI, MISO, & SCK pins).
    :param ~digitalio.DigitalInOut ss_pin: The "slave select" pin output to the Pinnacle ASIC.
    :param int spi_frequency: The SPI bus speed in Hz. Default is 12 MHz.
    :param ~digitalio.DigitalInOut dr_pin: |dr_pin_parameter|

        .. important:: |dr_pin_note|
    """

    def __init__(
        self,
        spi: busio.SPI,
        ss_pin: digitalio.DigitalInOut,
        spi_frequency: int = 12000000,
        dr_pin: Optional[digitalio.DigitalInOut] = None,
    ):
        self._spi = SPIDevice(spi, chip_select=ss_pin, phase=1, baudrate=spi_frequency)
        super().__init__(dr_pin=dr_pin)

    def _rap_read(self, reg: int) -> int:
        buf_out = bytes([reg | 0xA0]) + b"\xFB" * 3
        buf_in = bytearray(len(buf_out))
        with self._spi as spi:
            spi.write_readinto(buf_out, buf_in)
        return buf_in[3]

    def _rap_read_bytes(self, reg: int, numb_bytes: int) -> bytearray:
        # using auto-increment method
        buf_out = bytes([reg | 0xA0]) + b"\xFC" * (1 + numb_bytes) + b"\xFB"
        buf_in = bytearray(len(buf_out))
        with self._spi as spi:
            spi.write_readinto(buf_out, buf_in)
        return buf_in[3:]

    def _rap_write(self, reg: int, value: int):
        buf = bytes([(reg | 0x80), value])
        with self._spi as spi:
            spi.write(buf)

    def _rap_write_bytes(self, reg: int, values: List[int]):
        for i, val in enumerate(values):
            self._rap_write(reg + i, val)
