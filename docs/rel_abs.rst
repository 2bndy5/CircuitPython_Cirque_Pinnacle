Relative or Absolute mode API
=============================

.. autoattribute:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.feed_enable

   This function only applies to :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE`
   or :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE` mode, otherwise if `data_mode` is set to
   :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS`, then this function will do nothing.

.. autoattribute:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.hard_configured

   See note about product labeling in `Model Labeling Scheme <index.html#cc>`_. (read only)

   :Returns:
      `True` if a 470K ohm resistor is populated at the junction labeled "R4"

.. automethod:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.relative_mode_config

   (write only)

   This function only applies to :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE`
   mode, otherwise if `data_mode` is set to
   :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS` or
   :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE`, then this function does nothing.

   :param bool rotate90: Specifies if the axis data is altered for 90 degree rotation before
      reporting it (essentially swaps the axis data). Default is `False`.
   :param bool taps: Specifies if all taps should be reported (`True`) or not
      (`False`). Default is `True`. This affects ``secondary_tap`` option as well.
   :param bool secondary_tap: Specifies if tapping in the top-left corner (depending on
      orientation) triggers the secondary button data. Defaults to `True`. This feature is
      always disabled if `hard_configured` is `True`.
   :param bool glide_extend: A patented feature that allows the user to glide their finger off
      the edge of the sensor and continue gesture with the touch event. Default is `True`.
      This feature is always disabled if `hard_configured` is `True`.
   :param bool intellimouse: Specifies if the data reported includes a byte about scroll data.
      Default is `False`. Because this flag is specific to scroll data, this feature is always
      disabled if `hard_configured` is `True`.

.. automethod:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.absolute_mode_config

   (write only)

   This function only applies to :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE`
   mode, otherwise if `data_mode` is set to
   :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS` or
   :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE`, then this function does nothing.

   :param int z_idle_count: Specifies the number of empty packets (x-axis, y-axis, and z-axis
      are ``0``) reported (every 10 milliseconds) when there is no touch detected. Defaults
      to 30. This number is clamped to range [0, 255].
   :param bool invert_x: Specifies if the x-axis data is to be inverted before reporting it.
      Default is `False`.
   :param bool invert_y: Specifies if the y-axis data is to be inverted before reporting it.
      Default is `False`.

.. automethod:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.available

   If the ``dr_pin`` parameter is specified upon instantiation, then the specified
   input pin is used to detect if the data is new. Otherwise the SW_DR flag in the
   STATUS register is used to determine if the data is new.

   :Return: If there is fresh data to report (`True`) or not (`False`).

   .. versionadded:: 0.0.5

.. automethod:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.read

   This function only applies to :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE`
   or :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE` mode, otherwise if `data_mode` is set to
   :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS`, then this function returns `None` and does nothing.

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
         ``secondary_tap`` parameters are passed as `True` when calling `relative_mode_config()`,
         a single tap in the perspective top-left-most corner will be reflected here (secondary
         taps are constantly disabled if `hard_configured` returns `True`). Note that the
         top-left-most corner can be perspectively moved if ``rotate90`` parameter is passed as
         `True` when calling `relative_mode_config()`.
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

.. automethod:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.clear_status_flags

.. autoattribute:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.allow_sleep

   Set this attribute to `True` if you want the Pinnacle ASIC to enter sleep (low power)
   mode after about 5 seconds of inactivity (does not apply to AnyMeas mode). While the touch
   controller is in sleep mode, if a touch event or button press is detected, the Pinnacle
   ASIC will take about 300 milliseconds to wake up (does not include handling the touch event
   or button press data).

.. autoattribute:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.shutdown

   `True` means powered down (AKA standby mode), and `False` means not powered down
   (Active, Idle, or Sleep mode).

   .. note::
      The ASIC will take about 300 milliseconds to complete the transition
      from powered down mode to active mode. No touch events or button presses will be
      monitored while powered down.

.. autoattribute:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.sample_rate

   Valid values are ``100``, ``80``, ``60``, ``40``, ``20``, ``10``. Any other input values
   automatically set the sample rate to 100 sps (samples per second). Optionally, ``200`` and
   ``300`` sps can be specified, but using these values automatically disables palm (referred
   to as "NERD" in the specification sheet) and noise compensations. These higher values are
   meant for using a stylus with a 2mm diameter tip, while the values less than 200 are meant
   for a finger or stylus with a 5.25mm diameter tip.

   This function only applies to :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE`
   or :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE` mode, otherwise if `data_mode` is set to
   :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS`, then this function will do nothing.

.. automethod:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.detect_finger_stylus

   :param bool enable_finger: `True` enables the Pinnacle ASIC's measurements to
      detect if the touch event was caused by a finger or 5.25mm stylus. `False` disables
      this feature. Default is `True`.
   :param bool enable_stylus: `True` enables the Pinnacle ASIC's measurements to
      detect if the touch event was caused by a 2mm stylus. `False` disables this
      feature. Default is `True`.
   :param int sample_rate: See the `sample_rate` attribute as this parameter manipulates that
      attribute.

   .. tip::
      Consider adjusting the ADC matrix's gain to enhance performance/results using
      `set_adc_gain()`

.. automethod:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.calibrate

   This function only applies to :attr:`~circuitpython_cirque_pinnacle.glidepoint.RELATIVE`
   or :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE` mode, otherwise if `data_mode` is set to
   :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS`, then this function will do nothing.

   :param bool run: If `True`, this function forces a calibration of the sensor. If `False`,
      this function just writes the following parameters to the Pinnacle ASIC's "CalConfig1"
      register. This parameter is required while the rest are optional keyword parameters.
   :param bool tap: Enable dynamic tap compensation? Default is `True`.
   :param bool track_error: Enable dynamic track error compensation? Default is `True`.
   :param bool nerd: Enable dynamic NERD compensation? Default is `True`. This parameter has
      something to do with palm detection/compensation.
   :param bool background: Enable dynamic background compensation? Default is `True`.

   .. note::
      According to the datasheet, calibration of the sensor takes about 100
      milliseconds. This function will block until calibration is complete (if ``run`` is
      `True`). It is recommended for typical applications to leave all optional parameters
      in their default states.

.. autoattribute:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.calibration_matrix

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

.. automethod:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.set_adc_gain

   (does not apply to AnyMeas mode). (write-only)

   :param int sensitivity: This int specifies how sensitive the ADC (Analog to Digital
      Converter) component is. ``0`` means most sensitive, and ``3`` means least sensitive.
      A value outside this range will raise a `ValueError` exception.

   .. tip:: The official example code from Cirque for a curved overlay uses a value of ``1``.

.. automethod:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.tune_edge_sensitivity

   This function was ported from Cirque's example code and doesn't seem to have corresponding
   documentation. I'm having trouble finding a memory map of the Pinnacle ASIC as this
   function directly alters values in the Pinnacle ASIC's memory. USE AT YOUR OWN RISK!
