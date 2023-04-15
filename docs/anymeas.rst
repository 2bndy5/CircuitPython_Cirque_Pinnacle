
AnyMeas mode API
================

.. automethod:: circuitpython_cirque_pinnacle.PinnacleTouch.anymeas_mode_config

.. automethod:: circuitpython_cirque_pinnacle.PinnacleTouch.measure_adc

.. automethod:: circuitpython_cirque_pinnacle.PinnacleTouch.start_measure_adc

.. automethod:: circuitpython_cirque_pinnacle.PinnacleTouch.get_measure_adc

AnyMeas mode Gain
-----------------

Allowed ADC gain configurations of AnyMeas mode. The percentages defined here are approximate
values.

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_GAIN_100
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_GAIN_133
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_GAIN_166
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_GAIN_200
   :no-value:

AnyMeas mode Frequencies
------------------------

Allowed frequency configurations of AnyMeas mode. The frequencies defined here are
approximated based on an aperture width of 500 nanoseconds. If the ``aperture_width``
parameter to `anymeas_mode_config()` specified is less than 500 nanoseconds, then the
frequency will be larger than what is described here (& vice versa).

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_FREQ_0
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_FREQ_1
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_FREQ_2
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_FREQ_3
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_FREQ_4
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_FREQ_5
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_FREQ_6
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_FREQ_7
   :no-value:

AnyMeas mode Muxing
-------------------

Allowed muxing gate polarity and reference capacitor configurations of AnyMeas mode.
Combining these values (with ``+`` operator) is allowed.

.. note::
   The sign of the measurements taken in AnyMeas mode is inverted depending on which
   muxing gate is specified (when specifying an individual gate polarity).

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_MUX_REF1
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_MUX_REF0
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_MUX_PNP
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_MUX_NPN
   :no-value:

AnyMeas mode Control
--------------------

These constants control the number of measurements performed in `measure_adc()`.
The number of measurements can range [0, 63].

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_CRTL_REPEAT
   :no-value:

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_CRTL_PWR_IDLE
   :no-value:
