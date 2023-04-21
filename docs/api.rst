
PinnacleTouch API
==================

Data Modes
----------

Allowed symbols for configuring the Pinnacle ASIC's data reporting/measurements.
These are used as valid values for `PinnacleTouch.data_mode`.

.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_RELATIVE
.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_ANYMEAS
.. autodata:: circuitpython_cirque_pinnacle.PINNACLE_ABSOLUTE

PinnacleTouch class
-------------------

.. autoclass:: circuitpython_cirque_pinnacle.PinnacleTouch
   :no-members:

   .. autoattribute:: circuitpython_cirque_pinnacle.PinnacleTouch.data_mode

SPI & I2C Interfaces
--------------------

.. autoclass:: circuitpython_cirque_pinnacle.PinnacleTouchSPI
   :members:
   :show-inheritance:

.. autoclass:: circuitpython_cirque_pinnacle.PinnacleTouchI2C
   :members:
   :show-inheritance:
