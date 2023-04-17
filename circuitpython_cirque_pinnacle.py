"""
A driver module for the Cirque Pinnacle ASIC on the Cirque capacitive touch
based circular trackpads.
"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle.git"
import time
import struct

try:
    from typing import Optional, List, Union, Iterable
except ImportError:
    pass

from micropython import const
import digitalio
import busio
from adafruit_bus_device.spi_device import SPIDevice
from adafruit_bus_device.i2c_device import I2CDevice

#: A mode to measure changes in X & Y axis positions. See :doc:`rel_abs`.
PINNACLE_RELATIVE: int = const(0x00)
#: A mode for raw ADC measurements. See :doc:`anymeas`.
PINNACLE_ANYMEAS: int = const(0x01)
#: A mode to measure X, Y, & Z axis positions. See :doc:`rel_abs`.
PINNACLE_ABSOLUTE: int = const(0x02)
PINNACLE_GAIN_100: int = const(0xC0)  #: around 100% gain
PINNACLE_GAIN_133: int = const(0x80)  #: around 133% gain
PINNACLE_GAIN_166: int = const(0x40)  #: around 166% gain
PINNACLE_GAIN_200: int = const(0x00)  #: around 200% gain
PINNACLE_FREQ_0: int = const(0x02)  #: frequency around 500,000 Hz
PINNACLE_FREQ_1: int = const(0x03)  #: frequency around 444,444 Hz
PINNACLE_FREQ_2: int = const(0x04)  #: frequency around 400,000 Hz
PINNACLE_FREQ_3: int = const(0x05)  #: frequency around 363,636 Hz
PINNACLE_FREQ_4: int = const(0x06)  #: frequency around 333,333 Hz
PINNACLE_FREQ_5: int = const(0x07)  #: frequency around 307,692 Hz
PINNACLE_FREQ_6: int = const(0x09)  #: frequency around 267,000 Hz
PINNACLE_FREQ_7: int = const(0x0B)  #: frequency around 235,000 Hz
PINNACLE_MUX_REF1: int = const(0x10)  #: enables a builtin capacitor (~0.5 pF).
PINNACLE_MUX_REF0: int = const(0x08)  #: enables a builtin capacitor (~0.25 pF).
PINNACLE_MUX_PNP: int = const(0x04)  #: enable PNP sense line
PINNACLE_MUX_NPN: int = const(0x01)  #: enable NPN sense line
PINNACLE_CRTL_REPEAT: int = const(0x80)  #: required for more than 1 measurement
#: triggers low power mode (sleep) after completing measurements
PINNACLE_CRTL_PWR_IDLE: int = const(0x40)

#  Defined constants for Pinnacle registers
_FIRMWARE_ID: int = const(0x00)
_STATUS: int = const(0x02)
_SYS_CONFIG: int = const(0x03)
_FEED_CONFIG_1: int = const(0x04)
_FEED_CONFIG_2: int = const(0x05)
_FEED_CONFIG_3: int = const(0x06)
_CAL_CONFIG: int = const(0x07)
_SAMPLE_RATE: int = const(0x09)
_Z_IDLE: int = const(0x0A)
# _Z_SCALER: int = const(0x0B)
# _SLEEP_INTERVAL: int = const(0x0C)  # time of sleep until checking for finger
# _SLEEP_TIMER: int = const(0x0D)  # time after idle mode until sleep starts
_PACKET_BYTE_0: int = const(0x12)
_PACKET_BYTE_1: int = const(0x13)
_ERA_VALUE: int = const(0x1B)
_ERA_ADDR: int = const(0x1C)
_ERA_CONTROL: int = const(0x1E)
_HCO_ID: int = const(0x1F)


class AbsoluteReport:
    """A class to represent data reported by `PinnacleTouch.read()` when
    `PinnacleTouch.data_mode` is set to `PINNACLE_ABSOLUTE`.

    Each parameter is used as the initial value for the corresponding attribute.
    If not specified, then the attribute is set to ``0``.
    """

    def __init__(self, buttons: int = 0, x: int = 0, y: int = 0, z: int = 0):
        self.buttons: int = buttons
        """The button data is a byte in which each bit represents a button.
        The bit to button order is as follows:

        0. [LSBit] Button 1.
        1. Button 2.
        2. Button 3.
        """
        self.x: int = x
        """The position on the X axis ranging [0, 2047]. The datasheet recommends the
        X-axis value should be clamped to the range [128, 1920] for reliability."""
        self.y: int = y
        """The position on the Y axis ranging [0, 1535]. The datasheet recommends the
        Y-axis value should be clamped to the range [64, 1472] for reliability."""
        self.z: int = z
        """The magnitude of the Z axis (ranging [0, 255]) can be used as the proximity
        of the finger to the trackpad. ``0`` means no proximity. The maximum value
        reported may be influenced by `set_adc_gain()`."""

    def __repr__(self) -> str:
        return "<AbsoluteReport B1: {} B2: {} B3: {} X: {} Y: {} Z: {}>".format(
            self.buttons & 1,
            self.buttons & 2,
            self.buttons & 4,
            self.x,
            self.y,
            self.z,
        )


class RelativeReport:
    """A class to represent data reported by `PinnacleTouch.read()` when
    `PinnacleTouch.data_mode` is set to `PINNACLE_RELATIVE`.

    :param buf: A buffer object used to unpack initial values for the `buttons`, `x`,
        `y`, and `scroll` attributes. If not specified, then all attributes are set to
        ``0``.
    """

    def __init__(self, buf: Union[bytes, bytearray] = b"\0\0\0\0"):
        data = struct.unpack("Bbbb", buf[:4])
        self.buttons: int = data[0]
        """The button data is a byte in which each bit represents a button.
        The bit to button order is as follows:

        0. [LSBit] Button 1 (thought of as Left button on a mouse). If the ``taps``
           parameter is ``True`` when calling `relative_mode_config()`, a single tap
           will be reflected here.
        1. Button 2 (thought of as Right button on a mouse). If ``taps`` and
           ``secondary_tap`` parameters are ``True`` when calling
           `relative_mode_config()`, a single tap in the perspective top-left-most
           corner will be reflected here; secondary taps are constantly disabled if
           `hard_configured` returns ``True``. Note that the top-left-most corner can be
           perspectively moved if ``rotate90`` parameter is ``True`` when calling
           `relative_mode_config()`.
        2. Button 3 (thought of as Middle or scroll wheel button on a mouse)
        """
        self.x: int = data[1]  #: The change in X-axis ranging [-127, 127].
        self.y: int = data[2]  #: The change in Y-axis ranging [-127, 127].
        self.scroll: int = data[3]
        """The change in scroll counter ranging [-127, 127]. This data is only reported
        if the ``intellimouse`` parameter is ``True`` to `relative_mode_config()`.
        """

    @property
    def buffer(self) -> bytes:
        """A read-only property to return a `bytes` object that can be used as a Mouse
        HID report buffer."""
        return struct.pack("Bbbb", self.buttons, self.x, self.y, self.scroll)

    def __repr__(self) -> str:
        return (
            "<RelativeReport "
            "Left: {} Right: {} Middle: {} X: {} Y: {} Scroll: {}>".format(
                self.buttons & 1,
                self.buttons & 2,
                self.buttons & 4,
                self.x,
                self.y,
                self.scroll,
            )
        )


class PinnacleTouch:
    """The abstract base class for driving the Pinnacle ASIC.

    :param dr_pin: |dr_pin_parameter|

        .. important:: |dr_pin_note|

    .. |dr_pin_parameter| replace:: The input pin connected to the Pinnacle ASIC's "Data
        Ready" pin. If this parameter is not specified, then the SW_DR (software data
        ready) flag of the STATUS register is used to determine if the data being
        reported is new.

    .. |dr_pin_note| replace:: This parameter must be specified if your application is
        going to use the Pinnacle ASIC's `PINNACLE_ANYMEAS` mode (a rather experimental
        measuring of raw ADC values).
    """

    def __init__(self, dr_pin: Optional[digitalio.DigitalInOut] = None):
        self.dr_pin = dr_pin
        if self.dr_pin is not None:
            self.dr_pin.switch_to_input()
        firmware_id, firmware_ver = self._rap_read_bytes(_FIRMWARE_ID, 2)
        if firmware_id != 7 or firmware_ver != 0x3A:
            raise RuntimeError("Cirque Pinnacle ASIC not responding")
        self._intellimouse = False
        self._mode = PINNACLE_RELATIVE
        self.detect_finger_stylus()
        self._rap_write(_Z_IDLE, 30)  # z-idle packet count
        self._rap_write_bytes(_SYS_CONFIG, bytes(3))  # config data mode, power, etc
        self.set_adc_gain(0)
        while self.available():
            self.clear_status_flags()
        if not self.calibrate() and dr_pin is not None:
            raise AttributeError(
                "Calibration did not complete. Check wiring to `dr_pin`."
            )
        self.feed_enable = True

    @property
    def feed_enable(self) -> bool:
        """This `bool` attribute controls if the touch/button event data is
        reported (``True``) or not (``False``).

        This function only applies to `PINNACLE_RELATIVE` or `PINNACLE_ABSOLUTE` mode.
        Otherwise if `data_mode` is set to `PINNACLE_ANYMEAS`, then this attribute will
        have no effect.
        """
        return bool(self._rap_read(_FEED_CONFIG_1) & 1)

    @feed_enable.setter
    def feed_enable(self, is_on: bool):
        is_enabled = self._rap_read(_FEED_CONFIG_1)
        if bool(is_enabled & 1) != is_on:
            # save ourselves the unnecessary transaction
            is_enabled = (is_enabled & 0xFE) | bool(is_on)
            self._rap_write(_FEED_CONFIG_1, is_enabled)

    @property
    def data_mode(self) -> int:
        """This attribute controls the mode for which kind of data to report. The
        supported modes are `PINNACLE_RELATIVE`, `PINNACLE_ANYMEAS`,
        `PINNACLE_ABSOLUTE`. Default is `PINNACLE_RELATIVE`.

        .. important::
            When switching from `PINNACLE_ANYMEAS` to `PINNACLE_RELATIVE` or
            `PINNACLE_ABSOLUTE`, all configurations are reset, and must be re-configured
            by using `absolute_mode_config()` or `relative_mode_config()`.
        """
        return self._mode

    @data_mode.setter
    def data_mode(self, mode: int):
        if mode not in (PINNACLE_ANYMEAS, PINNACLE_RELATIVE, PINNACLE_ABSOLUTE):
            raise ValueError("Unrecognized input value for data_mode.")
        sys_config = self._rap_read(_SYS_CONFIG) & 0xE7  # clear AnyMeas mode flags
        if mode in (PINNACLE_RELATIVE, PINNACLE_ABSOLUTE):
            if self._mode == PINNACLE_ANYMEAS:  # if leaving AnyMeas mode
                self._rap_write(_CAL_CONFIG, 0x1E)  # enables all compensations
                self._rap_write(_Z_IDLE, 30)  # 30 z-idle packets
                self._mode = mode
                self.sample_rate = 100
                # set mode flag, enable feed, disable taps in Relative mode
                self._rap_write_bytes(_SYS_CONFIG, bytes([sys_config, 1 | mode, 2]))
            else:  # not leaving AnyMeas mode
                self._mode = mode
                self._rap_write(_FEED_CONFIG_1, 1 | mode)  # set mode flag, enable feed
            self._intellimouse = False
        else:  # for AnyMeas mode
            if self.dr_pin is None:  # AnyMeas requires the DR pin
                raise AttributeError(
                    "need the Data Ready (DR) pin specified for AnyMeas mode"
                )
            # disable tracking computations for AnyMeas mode
            self._rap_write(_SYS_CONFIG, sys_config | 0x08)
            time.sleep(0.01)  # wait for tracking computations to expire
            self._mode = mode
            self.anymeas_mode_config()  # configure registers for AnyMeas

    @property
    def hard_configured(self) -> bool:
        """This read-only `bool` attribute can be used to inform applications about
        factory customized hardware configuration. See note about product labeling in
        `Model Labeling Scheme <HCO>`.

        :Returns:
            ``True`` if a 470K ohm resistor is populated at the junction labeled "R4"
        """
        return bool(self._rap_read(_HCO_ID) & 0x80)

    def relative_mode_config(
        self,
        taps: bool = True,
        rotate90: bool = False,
        secondary_tap: bool = True,
        intellimouse: bool = False,
        glide_extend: bool = False,
    ):
        """Configure settings specific to Relative mode (AKA Mouse mode) data
        reporting.

        This function only applies to `PINNACLE_RELATIVE` mode, otherwise if `data_mode`
        is set to `PINNACLE_ANYMEAS` or `PINNACLE_ABSOLUTE`, then this function does
        nothing.

        :param taps: Specifies if all taps should be reported (``True``) or not
            (``False``). Default is ``True``. This affects the ``secondary_tap``
            parameter as well.
        :param rotate90: Specifies if the axis data is altered for 90 degree rotation
            before reporting it (essentially swaps the axis data). Default is ``False``.
        :param secondary_tap: Specifies if tapping in the top-left corner (depending on
            orientation) triggers the secondary button data. Defaults to ``True``. This
            feature is always disabled if `hard_configured` is ``True``.
        :param intellimouse: Specifies if the data reported includes a byte about scroll
            data. Default is ``False``. Because this flag is specific to scroll data,
            this feature is always disabled if `hard_configured` is ``True``.
        :param glide_extend: A patented feature that allows the user to glide their
            finger off the edge of the sensor and continue gesture with the touch event.
            Default is ``False``. This feature is always disabled if `hard_configured`
            is ``True``.
        """
        if self._mode == PINNACLE_RELATIVE:
            config2 = (rotate90 << 7) | ((not glide_extend) << 4)
            config2 |= ((not secondary_tap) << 2) | ((not taps) << 1)
            self._rap_write(_FEED_CONFIG_2, config2 | bool(intellimouse))
            if intellimouse:
                # send required cmd to enable intellimouse
                req_seq = bytes([0xF3, 0xC8, 0xF3, 0x64, 0xF3, 0x50])
                self._rap_write_cmd(req_seq)
                # verify w/ cmd to read the device ID
                response = self._rap_read_bytes(0xF2, 3)
                self._intellimouse = response.startswith(b"\xF3\x03")

    def absolute_mode_config(
        self, z_idle_count: int = 30, invert_x: bool = False, invert_y: bool = False
    ):
        """Configure settings specific to Absolute mode (reports axis
        positions).

        This function only applies to `PINNACLE_ABSOLUTE` mode, otherwise if `data_mode`
        is set to `PINNACLE_ANYMEAS` or `PINNACLE_RELATIVE`, then this function does
        nothing.

        :param z_idle_count: Specifies the number of empty packets (x-axis, y-axis, and
            z-axis are ``0``) reported (every 10 milliseconds) when there is no touch
            detected. Defaults to 30. This number is clamped to range [0, 255].
        :param invert_x: Specifies if the x-axis data is to be inverted before reporting
            it. Default is ``False``.
        :param invert_y: Specifies if the y-axis data is to be inverted before reporting
            it. Default is ``False``.
        """
        if self._mode == PINNACLE_ABSOLUTE:
            self._rap_write(_Z_IDLE, max(0, min(z_idle_count, 255)))
            config1 = self._rap_read(_FEED_CONFIG_1) & 0x3F | (invert_y << 7)
            self._rap_write(_FEED_CONFIG_1, config1 | (invert_x << 6))

    def available(self) -> bool:
        """Determine if there is fresh data to report.

        If the ``dr_pin`` parameter is specified upon instantiation, then the specified
        input pin is used to detect if the data is new. Otherwise the SW_DR flag in the
        STATUS register is used to determine if the data is new.

        :Returns: ``True`` if there is fresh data to report, otherwise ``False``.
        """
        if self.dr_pin is None:
            return bool(self._rap_read(_STATUS) & 0x0C)
        return self.dr_pin.value

    def read(
        self, report: Union[AbsoluteReport, RelativeReport], read_buttons: bool = True
    ) -> None:
        """This function will return touch (& button) event data from the Pinnacle ASIC.

        This function only applies to `PINNACLE_RELATIVE` or `PINNACLE_ABSOLUTE` mode.
        Otherwise if `data_mode` is set to `PINNACLE_ANYMEAS`, then this function
        does nothing.

        :param report: A `AbsoluteReport` or `RelativeReport` object (depending on the
            currently set `data_mode`) that is used to store the described touch and/or
            button event data.
        :param read_buttons: A flag that can be used to skip reading the button data
            from the Pinnacle. Default (``True``) will read the button data and store it
            in the ``report`` object's :attr:`~RelativeReport.buttons` attribute. This
            is really only useful to speed up read operations when not using the
            Pinnacle's button input pins.

            .. warning::
                If `PINNACLE_RELATIVE` mode's tap detection is enabled, then setting
                this parameter to ``False`` can be deceptively inaccurate when reporting
                tap gestures.
        """
        if self._mode == PINNACLE_ABSOLUTE:  # if absolute mode
            skip = (not read_buttons) * 2
            data = self._rap_read_bytes(_PACKET_BYTE_0 + skip, 6 - skip)
            self.clear_status_flags(False)
            assert isinstance(report, AbsoluteReport)
            if read_buttons:
                report.buttons &= 0xF8
                report.buttons = data[0] & 7
            report.x = data[2 - skip] | ((data[4 - skip] & 0x0F) << 8)
            report.y = data[3 - skip] | ((data[4 - skip] & 0xF0) << 4)
            report.z = data[5 - skip] & 0x3F
        elif self._mode == PINNACLE_RELATIVE:  # if in relative mode
            assert isinstance(report, RelativeReport)
            has_scroll = self._intellimouse
            read_buttons = bool(read_buttons)  # enforce bool data type
            data = self._rap_read_bytes(
                _PACKET_BYTE_0 + (not read_buttons), 2 + has_scroll + read_buttons
            )
            self.clear_status_flags(False)
            if read_buttons:
                report.buttons &= 0xF8
                report.buttons = data[0] & 7
            unpacked = struct.unpack("b" * (2 + has_scroll), data[read_buttons:])
            report.x, report.y = unpacked[0:2]
            if len(unpacked) > 2:
                report.scroll = unpacked[2]

    def clear_status_flags(self, post_delay=True):
        """This function clears the "Data Ready" flag which is reflected with
        the ``dr_pin``.

        :param post_delay: If ``True``, then this function waits the recommended 50
            milliseconds before exiting. Only set this to ``False`` if the following
            instructions do not require access to the Pinnacle ASIC."""
        self._rap_write(_STATUS, 0)
        if post_delay:
            time.sleep(0.00005)  # per official examples from Cirque

    @property
    def allow_sleep(self) -> bool:
        """This attribute specifies if the Pinnacle ASIC is allowed to sleep
        after about 5 seconds of idle (no input event).

        Set this attribute to ``True`` if you want the Pinnacle ASIC to enter sleep (low
        power) mode after about 5 seconds of inactivity (does not apply to
        `PINNACLE_ANYMEAS` mode). While the touch controller is in sleep mode, if a
        touch event or button press is detected, the Pinnacle ASIC will take about 300
        milliseconds to wake up (does not include handling the touch event or button
        press data).
        """
        return bool(self._rap_read(_SYS_CONFIG) & 4)

    @allow_sleep.setter
    def allow_sleep(self, is_enabled: bool):
        self._rap_write(
            _SYS_CONFIG, (self._rap_read(_SYS_CONFIG) & 0xFB) | (is_enabled << 2)
        )

    @property
    def shutdown(self) -> bool:
        """This attribute controls power of the Pinnacle ASIC. ``True`` means powered
        down (AKA standby mode), and ``False`` means not powered down (Active, Idle, or
        Sleep mode).

        .. note::
            The ASIC will take about 300 milliseconds to complete the transition
            from powered down mode to active mode. No touch events or button presses
            will be monitored while powered down.
        """
        return bool(self._rap_read(_SYS_CONFIG) & 2)

    @shutdown.setter
    def shutdown(self, is_off: bool):
        self._rap_write(
            _SYS_CONFIG, (self._rap_read(_SYS_CONFIG) & 0xFD) | (is_off << 1)
        )

    @property
    def sample_rate(self) -> int:
        """This attribute controls how many samples (of data) per second are reported.

        Valid values are ``100``, ``80``, ``60``, ``40``, ``20``, ``10``. Any other
        input values automatically set the sample rate to 100 sps (samples per second).
        Optionally, ``200`` and ``300`` sps can be specified, but using these values
        automatically disables palm (referred to as "NERD" in the specification sheet)
        and noise compensations. These higher values are meant for using a stylus with a
        2mm diameter tip, while the values less than 200 are meant for a finger or
        stylus with a 5.25mm diameter tip.

        This attribute only applies to `PINNACLE_RELATIVE` or `PINNACLE_ABSOLUTE` mode.
        Otherwise if `data_mode` is set to `PINNACLE_ANYMEAS`, then this attribute will
        have no effect.
        """
        return self._rap_read(_SAMPLE_RATE)

    @sample_rate.setter
    def sample_rate(self, val: int):
        if self._mode != PINNACLE_ANYMEAS:
            if val in (200, 300):
                # disable palm & noise compensations
                self._rap_write(_FEED_CONFIG_3, 10)
                reload_timer = 6 if val == 300 else 0x09
                self._era_write_bytes(0x019E, reload_timer, 2)
                val = 0
            else:
                # enable palm & noise compensations
                self._rap_write(_FEED_CONFIG_3, 0)
                self._era_write_bytes(0x019E, 0x13, 2)
                val = val if val in (100, 80, 60, 40, 20, 10) else 100
            self._rap_write(_SAMPLE_RATE, val)

    def detect_finger_stylus(
        self,
        enable_finger: bool = True,
        enable_stylus: bool = True,
        sample_rate: int = 100,
    ):
        """This function will configure the Pinnacle ASIC to detect either
        finger, stylus, or both.

        :param enable_finger: ``True`` enables the Pinnacle ASIC's measurements to
            detect if the touch event was caused by a finger or 5.25 mm stylus.
            ``False`` disables this feature. Default is ``True``.
        :param enable_stylus: ``True`` enables the Pinnacle ASIC's measurements to
            detect if the touch event was caused by a 2 mm stylus. ``False`` disables
            this feature. Default is ``True``.
        :param sample_rate: See the `sample_rate` attribute as this parameter
            manipulates that attribute.

        .. tip::
            Consider adjusting the ADC matrix's gain to enhance performance/results
            using `set_adc_gain()`
        """
        finger_stylus = self._era_read(0x00EB)
        finger_stylus |= (enable_stylus << 2) | enable_finger
        self._era_write(0x00EB, finger_stylus)
        self.sample_rate = sample_rate

    def calibrate(
        self,
        run: bool = True,
        tap: bool = True,
        track_error: bool = True,
        nerd: bool = True,
        background: bool = True,
    ) -> bool:
        """Set calibration parameters when the Pinnacle ASIC calibrates
        itself.

        This function only applies to `PINNACLE_RELATIVE` or `PINNACLE_ABSOLUTE` mode.
        Otherwise if `data_mode` is set to `PINNACLE_ANYMEAS`, then this function will
        have no effect.

        :param run: If ``True``, this function forces a calibration of the sensor. If
            ``False``, this function just writes the following parameters to the
            Pinnacle ASIC's "CalConfig1" register.
        :param tap: Enable dynamic tap compensation? Default is ``True``.
        :param track_error: Enable dynamic track error compensation? Default is
            ``True``.
        :param nerd: Enable dynamic NERD compensation? Default is ``True``. This
            parameter has something to do with palm detection/compensation.
        :param background: Enable dynamic background compensation? Default is ``True``.

        :Returns:
            ``False``
                - If `data_mode` is not set to `PINNACLE_RELATIVE` or
                  `PINNACLE_ABSOLUTE`.
                - If the calibration ``run`` timed out after 100 milliseconds.
            ``True``
                - If `data_mode` is set to `PINNACLE_RELATIVE` or `PINNACLE_ABSOLUTE`
                  and the calibration is **not** ``run``.
                - If the calibration ``run`` successfully finishes.
        """
        if self._mode not in (PINNACLE_RELATIVE, PINNACLE_ABSOLUTE):
            return False
        cal_config = (tap << 4) | (track_error << 3) | (nerd << 2)
        cal_config |= background << 1
        self._rap_write(_CAL_CONFIG, cal_config | run)
        timeout = time.monotonic_ns() + 100000000
        if run:
            done = False
            while not done and time.monotonic_ns() < timeout:
                done = self.available()  # calibration is running
            if done:
                self.clear_status_flags()  # now that calibration is done
            return done
        return True

    @property
    def calibration_matrix(self) -> List[int]:
        """This attribute returns a `list` of the 46 signed 16-bit (short)
        values stored in the Pinnacle ASIC's memory that is used for taking
        measurements.

        This matrix is not applicable in AnyMeas mode. Use this attribute to compare a
        prior compensation matrix with a new matrix that was either loaded manually by
        setting this attribute to a `list` of 46 signed 16-bit (short) integers or
        created internally by calling `calibrate()` with the ``run`` parameter as
        ``True``.

        .. note::
            A paraphrased note from Cirque's Application Note on Comparing compensation
            matrices:

            If any 16-bit values are above 20K (absolute), it generally indicates a
            problem with the sensor. If no values exceed 20K, proceed with the data
            comparison. Compare each 16-bit value in one matrix to the corresponding
            16-bit value in the other matrix. If the difference between the two values
            is greater than 500 (absolute), it indicates a change in the environment.
            Either an object was on the sensor during calibration, or the surrounding
            conditions (temperature, humidity, or noise level) have changed. One
            strategy is to force another calibration and compare again, if the values
            continue to differ by 500, determine whether to use the new data or a
            previous set of stored data. Another strategy is to average any two values
            that differ by more than 500 and write this new matrix, with the average
            values, back into Pinnacle ASIC.
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
        """Sets the ADC gain in range [0, 3] to enhance performance based on
        the overlay type (does not apply to AnyMeas mode).

        :param sensitivity: Specifies how sensitive the ADC (Analog to Digital
            Converter) component is. ``0`` means most sensitive, and ``3`` means least
            sensitive. A value outside this range will raise a `ValueError` exception.

            .. tip::
                The official example code from Cirque for a curved overlay uses a value
                of ``1``.
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
            corresponding documentation. This function directly alters values in the
            Pinnacle ASIC's memory. USE AT YOUR OWN RISK!
        """
        self._era_write(0x0149, x_axis_wide_z_min)
        self._era_write(0x0168, y_axis_wide_z_min)

    def anymeas_mode_config(
        self,
        gain: int = PINNACLE_GAIN_200,
        frequency: int = PINNACLE_FREQ_0,
        sample_length: int = 512,
        mux_ctrl: int = PINNACLE_MUX_PNP,
        apperture_width: int = 500,
        ctrl_pwr_cnt: int = 1,
    ):
        """This function configures the Pinnacle ASIC to output raw ADC
        measurements.

        Be sure to set the `data_mode` attribute to `PINNACLE_ANYMEAS` before calling
        this function, otherwise it will do nothing.

        :param gain: Sets the sensitivity of the ADC matrix. Valid values are the
            constants defined in `AnyMeas mode Gain`_. Defaults to `PINNACLE_GAIN_200`.
        :param frequency: Sets the frequency of measurements made by the ADC matrix.
            Valid values are the constants defined in `AnyMeas mode Frequencies`_.
            Defaults to `PINNACLE_FREQ_0`.
        :param sample_length: Sets the maximum bit length of the measurements made by
            the ADC matrix. Valid values are ``128``, ``256``, or ``512``. Defaults to
            ``512``.
        :param mux_ctrl: The Pinnacle ASIC can employ different bipolar junctions
            and/or reference capacitors. Valid values are the constants defined in
            `AnyMeas mode Muxing`_. Additional combination of these constants is also
            allowed. Defaults to `PINNACLE_MUX_PNP`.
        :param apperture_width: Sets the window of time (in nanoseconds) to allow for
            the ADC to take a measurement. Valid values are multiples of 125 in range
            [``250``, ``1875``]. Erroneous values are clamped/truncated to this range.

            .. note:: The ``apperture_width`` parameter has a inverse
                relationship/affect on the ``frequency`` parameter. The approximated
                frequencies described in this documentation are based on an aperture
                width of 500 nanoseconds, and they will shrink as the apperture width
                grows or grow as the aperture width shrinks.

        :param ctrl_pwr_cnt: Configure the Pinnacle to perform a number of measurements
            for each call to `measure_adc()`. Defaults to 1. Constants defined in
            `AnyMeas mode Control`_ can be used to specify if is sleep is allowed
            (`PINNACLE_CRTL_PWR_IDLE` -- this is not default) or if repetitive
            measurements is allowed (`PINNACLE_CRTL_REPEAT`) if number of measurements
            is more than 1.

            .. warning::
                There is no bounds checking on the number of measurements specified
                here. Specifying more than 63 will trigger sleep mode after performing
                measurements.

            .. tip::
                Be aware that allowing the Pinnacle to enter sleep mode after taking
                measurements will slow consecutive calls to `measure_adc()` as the
                Pinnacle requires about 300 milliseconds to wake up.
        """
        if self._mode == PINNACLE_ANYMEAS:
            buffer = bytearray(10)
            buffer[0] = gain | frequency
            buffer[1] = max(1, min(int(sample_length / 128), 3))
            buffer[2] = mux_ctrl
            buffer[4] = max(2, min(int(apperture_width / 125), 15))
            buffer[6] = _PACKET_BYTE_1
            buffer[9] = ctrl_pwr_cnt
            self._rap_write_bytes(_FEED_CONFIG_2, buffer)
            self._rap_write_bytes(_PACKET_BYTE_1, bytes(8))
            self.clear_status_flags()

    def measure_adc(self, bits_to_toggle: int, toggle_polarity: int) -> Optional[int]:
        """This blocking function instigates and returns the measurements (a
        signed short) from the Pinnacle ASIC's ADC (Analog to Digital Converter) matrix.

        Internally this function calls `start_measure_adc()` and `get_measure_adc()` in
        sequence. Be sure to set the `data_mode` attribute to `PINNACLE_ANYMEAS` before
        calling this function otherwise it will do nothing.

        Each of the parameters are a 4-byte integer (see
        :ref:`format table below <polynomial-fmt>`) in which each bit corresponds to
        a capacitance sensing electrode in the sensor's matrix (12 electrodes for
        Y-axis, 16 electrodes for X-axis). They are used to compensate for varying
        capacitances in the electrodes during measurements.

        :param bits_to_toggle: A bit of ``1`` flags that electrode's output for
            toggling, and a bit of ``0`` signifies that the electrode's output should
            remain unaffected.
        :param toggle_polarity: This specifies which polarity the output of the
            electrode(s) (specified with corresponding bits in ``bits_to_toggle``
            parameter) should be toggled (forced). A bit of ``1`` toggles that bit
            positive, and a bit of ``0`` toggles that bit negative.

        :Returns:
            A 2-byte `bytearray` that represents a signed short integer. If `data_mode`
            is not set to `PINNACLE_ANYMEAS`, then this function returns `None` and does
            nothing.

        .. _polynomial-fmt:

        :4-byte Integer Format:
            Bits 31 & 30 are not used and should remain ``0``. Bits 29 and 28 represent
            the optional implementation of reference capacitors built into the Pinnacle
            ASIC. To use these capacitors, the corresponding constants
            (`PINNACLE_MUX_REF0` and/or `PINNACLE_MUX_REF1`) must be passed to
            `anymeas_mode_config()` in the ``mux_ctrl`` parameter, and their
            representative bits must be flagged in both ``bits_to_toggle`` &
            ``toggle_polarity`` parameters.

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

            .. seealso::
                Review `AnyMeas mode example <examples.html#anymeas-mode-example>`_ to
                understand how to use these 4-byte integers.
        """
        if self._mode != PINNACLE_ANYMEAS:
            return None
        self.start_measure_adc(bits_to_toggle, toggle_polarity)
        while not self.available():
            pass  # wait till measurements are complete
        return self.get_measure_adc()

    def start_measure_adc(self, bits_to_toggle: int, toggle_polarity: int):
        """A non-blocking function that starts measuring ADC values in
        AnyMeas mode.

        See the parameters and table in `measure_adc()` as this is its helper function,
        and all parameters there are used the same way here.
        """
        if self._mode == PINNACLE_ANYMEAS:
            tog_pol = bytearray(8)  # assemble list of register buffers
            for i in range(3, -1, -1):
                tog_pol[3 - i] = (bits_to_toggle >> (i * 8)) & 0xFF
                tog_pol[3 - i + 4] = (toggle_polarity >> (i * 8)) & 0xFF
            # write toggle and polarity parameters to register 0x13 - 0x1A
            self._rap_write_bytes(_PACKET_BYTE_1, tog_pol)
            # clear_status_flags() and initiate measurements
            self._rap_write_bytes(_STATUS, b"\0\x18")

    def get_measure_adc(self) -> Optional[int]:
        """A non-blocking function that returns ADC measurement on
        completion.

        This function is only meant to be used in conjunction with `start_measure_adc()`
        for non-blocking application. Be sure that `available()` returns ``True`` before
        calling this function as it will `clear_status_flags()` that `available()` uses.

        :returns:
            * `None` if `data_mode` is not set to `PINNACLE_ANYMEAS` or if the "data
              ready" pin's signal is not active (while `data_mode` is set to
              `PINNACLE_ANYMEAS`) meaning the Pinnacle ASIC is still computing the ADC
              measurements based on the 4-byte polynomials passed to
              `start_measure_adc()`.
            * a `bytearray` that represents a signed 16-bit integer upon completed ADC
              measurements based on the 4-byte polynomials passed to
              `start_measure_adc()`.
        """
        if self._mode != PINNACLE_ANYMEAS:
            return None
        data = self._rap_read_bytes(0x11, 2)
        self.clear_status_flags()
        return struct.unpack("h", data)[0]

    def _rap_read(self, reg: int) -> int:
        raise NotImplementedError()

    def _rap_read_bytes(self, reg: int, numb_bytes: int) -> bytearray:
        raise NotImplementedError()

    def _rap_write(self, reg: int, value: int):
        raise NotImplementedError()

    def _rap_write_cmd(self, cmd: bytes):
        raise NotImplementedError()

    def _rap_write_bytes(self, reg: int, values: Iterable[int]):
        raise NotImplementedError()

    def _era_read(self, reg: int) -> int:
        prev_feed_state = self.feed_enable
        if prev_feed_state:
            self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write_bytes(_ERA_ADDR, bytes([reg >> 8, reg & 0xFF]))
        self._rap_write(_ERA_CONTROL, 1)  # indicate reading only 1 byte
        while self._rap_read(_ERA_CONTROL):  # read until reg == 0
            pass  # also sets Command Complete flag in Status register
        buf = self._rap_read(_ERA_VALUE)  # get value
        self.clear_status_flags()
        if prev_feed_state:
            self.feed_enable = prev_feed_state  # resume previous feed state
        return buf

    def _era_read_bytes(self, reg: int, numb_bytes: int) -> bytes:
        buf = b""
        prev_feed_state = self.feed_enable
        if prev_feed_state:
            self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write_bytes(_ERA_ADDR, bytes([reg >> 8, reg & 0xFF]))
        for _ in range(numb_bytes):
            self._rap_write(_ERA_CONTROL, 5)  # indicate reading sequential bytes
            while self._rap_read(_ERA_CONTROL):  # read until reg == 0
                pass  # also sets Command Complete flag in Status register
            buf += bytes([self._rap_read(_ERA_VALUE)])  # get value
            self.clear_status_flags()
        if prev_feed_state:
            self.feed_enable = prev_feed_state  # resume previous feed state
        return buf

    def _era_write(self, reg: int, value: int):
        prev_feed_state = self.feed_enable
        if prev_feed_state:
            self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write(_ERA_VALUE, value)  # write value
        self._rap_write_bytes(_ERA_ADDR, bytes([reg >> 8, reg & 0xFF]))
        self._rap_write(_ERA_CONTROL, 2)  # indicate writing only 1 byte
        while self._rap_read(_ERA_CONTROL):  # read until reg == 0
            pass  # also sets Command Complete flag in Status register
        self.clear_status_flags()
        if prev_feed_state:
            self.feed_enable = prev_feed_state  # resume previous feed state

    def _era_write_bytes(self, reg: int, value: int, numb_bytes: int):
        # rarely used as it only writes 1 value to multiple registers
        prev_feed_state = self.feed_enable
        if prev_feed_state:
            self.feed_enable = False  # accessing raw memory, so do this
        self._rap_write(_ERA_VALUE, value)  # write value
        self._rap_write_bytes(_ERA_ADDR, bytes([reg >> 8, reg & 0xFF]))
        self._rap_write(_ERA_CONTROL, 0x0A)  # indicate writing sequential bytes
        for _ in range(numb_bytes):
            while self._rap_read(_ERA_CONTROL):  # read until reg == 0
                pass  # also sets Command Complete flag in Status register
            self.clear_status_flags()
        if prev_feed_state:
            self.feed_enable = prev_feed_state  # resume previous feed state


# pylint: disable=no-member
class PinnacleTouchI2C(PinnacleTouch):
    """A derived class for interfacing with the Pinnacle ASIC via the I2C protocol.

    :param i2c: The object of the I2C bus to use. This object must be shared among other
        driver classes that use the same I2C bus (SDA & SCL pins).
    :param address: The slave I2C address of the Pinnacle ASIC. Defaults to ``0x2A``.
    :param dr_pin: |dr_pin_parameter|

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
        self._rap_write_bytes(reg, bytes([value]))

    def _rap_write_bytes(self, reg: int, values: Iterable[int]):
        buf = b""
        for index, byte in enumerate(values):
            # Pinnacle doesn't auto-increment register
            # addresses for I2C write operations
            buf += bytes([(reg + index) | 0x80, byte & 0xFF])
        self._rap_write_cmd(buf)

    def _rap_write_cmd(self, cmd: bytes):
        with self._i2c as i2c:
            i2c.write(cmd)


class PinnacleTouchSPI(PinnacleTouch):
    """A derived class for interfacing with the Pinnacle ASIC via the SPI protocol.

    :param spi: The object of the SPI bus to use. This object must be shared among other
        driver classes that use the same SPI bus (MOSI, MISO, & SCK pins).
    :param ss_pin: The "slave select" pin output to the Pinnacle ASIC.
    :param spi_frequency: The SPI bus speed in Hz. Default is the maximum 13 MHz.
    :param dr_pin: |dr_pin_parameter|

        .. important:: |dr_pin_note|
    """

    def __init__(
        self,
        spi: busio.SPI,
        ss_pin: digitalio.DigitalInOut,
        spi_frequency: int = 13000000,
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

    def _rap_write_cmd(self, cmd: bytes):
        with self._spi as spi:
            spi.write(cmd)

    def _rap_write(self, reg: int, value: int):
        self._rap_write_cmd(bytes([(reg | 0x80), value]))

    def _rap_write_bytes(self, reg: int, values: Iterable[int]):
        for i, val in enumerate(values):
            self._rap_write(reg + i, val)
