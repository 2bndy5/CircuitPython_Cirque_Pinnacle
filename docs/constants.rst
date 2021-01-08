
Accepted Constants
------------------

Data Modes
***********


Allowed symbols for configuring the Pinanacle ASIC's data reporting/measurements.

.. data:: circuitpython_cirque_pinnacle.glidepoint.RELATIVE
   :annotation: =0


   Alias symbol for specifying Relative mode (AKA Mouse mode).

.. data:: circuitpython_cirque_pinnacle.glidepoint.ANYMEAS
   :annotation: =1

   Alias symbol for specifying "AnyMeas" mode (raw ADC measurement)

.. data:: circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE
   :annotation: =2

   Alias symbol for specifying Absolute mode (axis positions)

AnyMeas mode Gain
******************

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
************************

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
*******************

Allowed muxing gate polarity and reference capacitor configurations of AnyMeas mode.
Combining these values (with ``+`` operator) is allowed.

.. note:: The sign of the measurements taken in AnyMeas mode is inverted depending on which
   muxing gate is specified (when specifying an individual gate polarity).

.. data:: circuitpython_cirque_pinnacle.glidepoint.MUX_REF1

   enables a builtin capacitor (~0.5pF). See note in `measure_adc()`

.. data:: circuitpython_cirque_pinnacle.glidepoint.MUX_REF0

   enables a builtin capacitor (~0.25pF). See note in `measure_adc()`

.. data:: circuitpython_cirque_pinnacle.glidepoint.MUX_PNP

   enable PNP sense line

.. data:: circuitpython_cirque_pinnacle.glidepoint.MUX_NPN

   enable NPN sense line


AnyMeas mode Control
********************

These constants control the number of measurements performed in `measure_adc()`.
The number of measurements can range [0, 63].

.. data:: circuitpython_cirque_pinnacle.glidepoint.CRTL_REPEAT

   required for more than 1 measurement

.. data:: circuitpython_cirque_pinnacle.glidepoint.CRTL_PWR_IDLE

   triggers low power mode (sleep) after completing measurements
