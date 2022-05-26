
AnyMeas mode API
================

.. automethod:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.anymeas_mode_config

   Be sure to set the `data_mode` attribute to
   :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS` before calling this function
   otherwise it will do nothing.

   :param int gain: Sets the sensitivity of the ADC matrix. Valid values are the constants
      defined in `AnyMeas mode Gain`_. Defaults to
      :attr:`~circuitpython_cirque_pinnacle.glidepoint.GAIN_200`.
   :param int frequency: Sets the frequency of measurements made by the ADC matrix. Valid
      values are the constants defined in
      `AnyMeas mode Frequencies`_.
      Defaults :attr:`~circuitpython_cirque_pinnacle.glidepoint.FREQ_0`.
   :param int sample_length: Sets the maximum bit length of the measurements made by the ADC
      matrix. Valid values are ``128``, ``256``, or ``512``. Defaults to ``512``.
   :param int mux_ctrl: The Pinnacle ASIC can employ different bipolar junctions
      and/or reference capacitors. Valid values are the constants defined in
      `AnyMeas mode Muxing`_. Additional combination of
      these constants is also allowed. Defaults to
      :attr:`~circuitpython_cirque_pinnacle.glidepoint.MUX_PNP`.
   :param int apperture_width: Sets the window of time (in nanoseconds) to allow for the ADC
      to take a measurement. Valid values are multiples of 125 in range [``250``, ``1875``].
      Erroneous values are clamped/truncated to this range.

      .. note:: The ``apperture_width`` parameter has a inverse relationship/affect on the
         ``frequency`` parameter. The approximated frequencies described in this
         documentation are based on an aperture width of 500 nanoseconds, and they will
         shrink as the apperture width grows or grow as the aperture width shrinks.

   :param int ctrl_pwr_cnt: Configure the Pinnacle to perform a number of measurements for
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

.. automethod:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.measure_adc

   Internally this function calls `start_measure_adc()` and `get_measure_adc()` in sequence.
   Be sure to set the `data_mode` attribute to
   :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS` before calling this function
   otherwise it will do nothing.

   :Parameters' Context:
      Each of the parameters are a 4-byte integer (see
      `format table below <#circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.measure_adc-byte-integer-format>`_)
      in which each bit corresponds to a capacitance sensing electrode in the sensor's matrix (12 electrodes for
      Y-axis, 16 electrodes for X-axis). They are used to compensate for varying capacitances in
      the electrodes during measurements. **It is highly recommended that the trackpad be
      installed in a finished/prototyped housing when determining what electrodes to
      manipulate.** See `AnyMeas mode example <examples.html#anymeas-mode-example>`_ to
      understand how to use these 4-byte integers.

   :param int bits_to_toggle: A bit
      of ``1`` flags that electrode's output for toggling, and a bit of ``0`` signifies that
      the electrode's output should remain unaffected.
   :param int toggle_polarity: This
      specifies which polarity the output of the electrode(s) (specified with corresponding
      bits in ``bits_to_toggle`` parameter) should be toggled (forced). A bit of ``1`` toggles
      that bit positive, and a bit of ``0`` toggles that bit negative.

   :Returns:
      A 2-byte `bytearray` that represents a signed short integer. If `data_mode` is not set
      to :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS`, then this function returns
      `None` and does nothing.

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

.. automethod:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.start_measure_adc

   See the parameters and table in `measure_adc()` as this is its helper function, and all
   parameters there are used the same way here.

.. automethod:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.get_measure_adc

   This function is only meant ot be used in conjunction with `start_measure_adc()` for
   non-blocking application.

   :returns:
      * `None` if `data_mode` is not set to `ANYMEAS` or if the "data ready" pin's signal is not
        active (while `data_mode` is set to `ANYMEAS`) meaning the Pinnacle ASIC is still computing
        the ADC measurements based on the 4-byte polynomials passed to `start_measure_adc()`.
      * a `bytearray` that represents a signed 16-bit integer upon completed ADC measurements based
        on the 4-byte polynomials passed to `start_measure_adc()`.

AnyMeas mode Gain
-----------------

Allowed ADC gain configurations of AnyMeas mode. The percentages defined here are approximate
values.

.. data:: circuitpython_cirque_pinnacle.glidepoint.GAIN_100

   around 100% gain

.. data:: circuitpython_cirque_pinnacle.glidepoint.GAIN_133

   around 133% gain

.. data:: circuitpython_cirque_pinnacle.glidepoint.GAIN_166

   around 166% gain

.. data:: circuitpython_cirque_pinnacle.glidepoint.GAIN_200

   around 200% gain

AnyMeas mode Frequencies
------------------------

Allowed frequency configurations of AnyMeas mode. The frequencies defined here are
approximated based on an aperture width of 500 nanoseconds. If the ``aperture_width``
parameter to `anymeas_mode_config()` specified is less than 500 nanoseconds, then the
frequency will be larger than what is described here (& vice versa).

.. data:: circuitpython_cirque_pinnacle.glidepoint.FREQ_0

   frequency around 500,000Hz

.. data:: circuitpython_cirque_pinnacle.glidepoint.FREQ_1

   frequency around 444,444Hz

.. data:: circuitpython_cirque_pinnacle.glidepoint.FREQ_2

   frequency around 400,000Hz

.. data:: circuitpython_cirque_pinnacle.glidepoint.FREQ_3

   frequency around 363,636Hz

.. data:: circuitpython_cirque_pinnacle.glidepoint.FREQ_4

   frequency around 333,333Hz

.. data:: circuitpython_cirque_pinnacle.glidepoint.FREQ_5

   frequency around 307,692Hz

.. data:: circuitpython_cirque_pinnacle.glidepoint.FREQ_6

   frequency around 267,000Hz

.. data:: circuitpython_cirque_pinnacle.glidepoint.FREQ_7

   frequency around 235,000Hz

AnyMeas mode Muxing
-------------------

Allowed muxing gate polarity and reference capacitor configurations of AnyMeas mode.
Combining these values (with ``+`` operator) is allowed.

.. note:: The sign of the measurements taken in AnyMeas mode is inverted depending on which
   muxing gate is specified (when specifying an individual gate polarity).

.. data:: circuitpython_cirque_pinnacle.glidepoint.MUX_REF1

   enables a builtin capacitor (~0.5pF).

.. data:: circuitpython_cirque_pinnacle.glidepoint.MUX_REF0

   enables a builtin capacitor (~0.25pF).

.. data:: circuitpython_cirque_pinnacle.glidepoint.MUX_PNP

   enable PNP sense line

.. data:: circuitpython_cirque_pinnacle.glidepoint.MUX_NPN

   enable NPN sense line

AnyMeas mode Control
--------------------

These constants control the number of measurements performed in `measure_adc()`.
The number of measurements can range [0, 63].

.. data:: circuitpython_cirque_pinnacle.glidepoint.CRTL_REPEAT

   required for more than 1 measurement

.. data:: circuitpython_cirque_pinnacle.glidepoint.CRTL_PWR_IDLE

   triggers low power mode (sleep) after completing measurements
