
PinnacleTouch API
==================

Data Modes
----------

Allowed symbols for configuring the Pinnacle ASIC's data reporting/measurements.

.. data:: circuitpython_cirque_pinnacle.glidepoint.RELATIVE
   :annotation: = 0

   Alias symbol for specifying Relative mode (AKA Mouse mode).

.. data:: circuitpython_cirque_pinnacle.glidepoint.ANYMEAS
   :annotation: = 1

   Alias symbol for specifying "AnyMeas" mode (raw ADC measurement)

.. data:: circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE
   :annotation: = 2

   Alias symbol for specifying Absolute mode (axis positions)


PinnacleTouch class
-------------------

.. autoclass:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch
   :no-members:

   .. autoattribute:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.data_mode

SPI & I2C Interfaces
--------------------

.. autoclass:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouchSPI
   :members:
   :show-inheritance:

.. autoclass:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouchI2C
   :members:
   :show-inheritance:
