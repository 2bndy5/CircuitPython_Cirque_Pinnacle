
Examples
========

Relative Mode example
---------------------

A simple example of using the Pinnacle ASIC in relative mode.

.. literalinclude:: ../examples/cirque_pinnacle_relative_mode.py
    :caption: examples/cirque_pinnacle_relative_mode.py
    :linenos:
    :start-at: import time
    :end-before: def set_role()

Absolute Mode example
---------------------

A simple example of using the Pinnacle ASIC in absolute mode.

.. literalinclude:: ../examples/cirque_pinnacle_absolute_mode.py
    :caption: examples/cirque_pinnacle_absolute_mode.py
    :linenos:
    :start-at: import time
    :end-before: def set_role()

Anymeas mode example
--------------------

This example uses the Pinnacle touch controller's anymeas mode to fetch raw ADC values.

.. literalinclude:: ../examples/cirque_pinnacle_anymeas_mode.py
    :caption: examples/cirque_pinnacle_anymeas_mode.py
    :linenos:
    :start-at: import time
    :end-before: def set_role()
    :emphasize-lines: 30-35

USB Mouse example
-----------------

This example uses CircuitPython's built-in `usb_hid` API to emulate a mouse with the
Cirque circle trackpad.

.. literalinclude:: ../examples/cirque_pinnacle_usb_mouse.py
    :caption: examples/cirque_pinnacle_usb_mouse.py
    :linenos:
    :start-at: import time
    :end-before: def set_role()
