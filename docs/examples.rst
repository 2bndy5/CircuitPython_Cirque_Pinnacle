Simple Test
-----------

Ensure your device works with this simple test (using SPI protocol).

.. literalinclude:: ../examples/cirque_pinnacle_spi_simpletest.py
    :caption: examples/cirque_pinnacle_spi_simpletest.py
    :linenos:

USB Mouse example
-----------------

This example uses CircuitPython's built-in `usb_hid` API to emulate a mouse with the Cirque circle trackpad.


.. literalinclude:: ../examples/cirque_pinnacle_usb_mouse.py
    :caption: examples/cirque_pinnacle_usb_mouse.py
    :linenos:

AnyMeas mode example
--------------------

This example uses the Pinnacle touch controller's AnyMeas mode to fetch raw ADC values.


.. literalinclude:: ../examples/cirque_pinnacle_anymeas_test.py
    :caption: examples/cirque_pinnacle_anymeas_test.py
    :linenos:
