
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

.. |dr_pin_parameter| replace:: The input pin connected to the Pinnacle ASIC's "Data
      Ready" pin. If this parameter is not specified, then the SW_DR (software data ready) flag
      of the STATUS register is used to determine if the data being reported is new.

.. |dr_pin_note| replace:: This parameter must be specified if your application is going to use the
      Pinnacle ASIC's :attr:`~circuitpython_cirque_pinnacle.glidepoint.ANYMEAS`
      mode (a rather experimental measuring of raw ADC values).

.. autoclass:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch
   :no-members:

   :param ~digitalio.DigitalInOut dr_pin: |dr_pin_parameter|

      .. important:: |dr_pin_note|

.. autoattribute:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouch.data_mode

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
      :attr:`~circuitpython_cirque_pinnacle.glidepoint.ABSOLUTE` all configurations are reset, and
      must be re-configured by using  `absolute_mode_config()` or `relative_mode_config()`.


SPI & I2C Interfaces
--------------------

.. autoclass:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouchSPI
   :members:
   :show-inheritance:

   :param ~busio.SPI spi: The object of the SPI bus to use. This object must be shared among
      other driver classes that use the same SPI bus (MOSI, MISO, & SCK pins).
   :param ~digitalio.DigitalInOut ss_pin: The "slave select" pin output to the Pinnacle ASIC.
   :param int spi_frequency: The SPI bus speed in Hz. Default is 12 MHz.
   :param ~digitalio.DigitalInOut dr_pin: |dr_pin_parameter|

      .. important:: |dr_pin_note|

.. autoclass:: circuitpython_cirque_pinnacle.glidepoint.PinnacleTouchI2C
   :members:
   :show-inheritance:


   :param ~busio.I2C i2c: The object of the I2C bus to use. This object must be shared among
      other driver classes that use the same I2C bus (SDA & SCL pins).
   :param int address: The slave I2C address of the Pinnacle ASIC. Defaults to ``0x2A``.
   :param ~digitalio.DigitalInOut dr_pin: |dr_pin_parameter|

      .. important:: |dr_pin_note|
