
.. image:: https://readthedocs.org/projects/circuitpython-cirque-pinnacle/badge/?version=latest
    :target: https://circuitpython-cirque-pinnacle.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle/workflows/Build%20CI/badge.svg
    :target: https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle/actions/
    :alt: Build Status

.. image:: https://img.shields.io/pypi/v/circuitpython-cirque-pinnacle.svg
    :alt: latest version on PyPI
    :target: https://pypi.python.org/pypi/circuitpython-cirque-pinnacle

.. image:: https://pepy.tech/badge/circuitpython-cirque-pinnacle
    :alt: Total PyPI downloads
    :target: https://pepy.tech/project/circuitpython-cirque-pinnacle


Introduction
============

A CircuitPython driver library that implements the Adafruit_BusDevice library
for interfacing with the Cirque Pinnacle (1CA027) touch controller used in Cirque Circle Trackpads.

Supported Features
------------------

* Use SPI or I2C bus protocols to interface with the Pinnacle touch controller ASIC (Application
  Specific Integrated Circuit).
* Relative mode data reporting (AKA Mouse mode) with optional tap detection.
* Absolute mode data reporting (x, y, & z axis positions).
* AnyMeas mode data reporting. This mode exposes the ADC (Analog to Digital Converter) values and is
  not well documented in the numerous datasheets provided by the Cirque corporation about the
  Pinnacle (1CA027), thus this is a rather experimental mode.
* Hardware input buttons' states included in data reports. There are 3 button input lines on
  the Cirque circle trackpads -- see `Pinout`_ section.
* Configure measurements for finger or stylus (or automatically detirmine either) touch
  events. The Cirque circle trackpads are natively capable of measuring only 1 touch
  point per event.
* Download/upload the underlying compensation matrix for ADC measurements.
* Adjust the ADC matrix gain (sensitivity).

.. tip:: The SPI protocol is the preferred method for interfacing with more than 1 Cirque circle
    trackpad from the same MCU (microcontroller). The Cirque Pinnacle does not allow
    changing the I2C slave device address (via software); this means only 1 Cirque circle trackpad
    can be accessed over the I2C bus in the lifecycle of an application. That said, you could change
    the I2C address from ``0x2A`` to ``0x2C`` by soldering a 470K ohm resistor at the junction
    labeled "ADR" (see picture in `Pinout`_ section), although this is untested.

Unsupported Features
--------------------

* The legacy PS\\2 interface is pretty limited and not accessible by some CircuitPython MCUs.
  Therefore, it has been neglected in this library.
* Cirque's circle trackpads ship with the newer non-AG (Advanced Gestures) variant of the
  Pinnacle touch controller ASIC. Thus, this library focuses on the the non-AG variant's
  functionality via testing, and it does not provide access to the older AG variant's features
  (register addresses slightly differ which breaks compatibility).

Pinout
======

.. image:: https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle/raw/master/docs/_static/Cirque_GlidePoint-Circle-Trackpad.png
    :target: https://www.mouser.com/new/cirque/glidepoint-circle-trackpads/

The above picture is an example of the Cirque GlidePoint circle trackpad. This picture
is chosen as the test pads (larger copper circular pads) are clearly labeled. The test pads
are extended to the `12-pin FFC/FPC cable <https://www.mouser.com/Connectors/FFC-FPC/
FFC-FPC-Jumper-Cables/_/N-axro3?P=1yc8ojpZ1z0wxjx>`_ connector (the white block near the
bottom). The following table shows how the pins are connected in the `examples <examples.html>`_ (tested on an `ItsyBitys M4 <https://www.adafruit.com/product/3800>`_)

.. csv-table:: pinout (ordered the same as the FFC/FPC cable connector)
    :header: Label,"MCU pin",Description
    :widths: 5,5,13

    SCK,SCK,"SPI clock line"
    SO,MISO,"Master Input Slave Output"
    SS,D7,"Slave Select (AKA Chip Select)"
    DR,D2,"""data ready"" interrupt"
    SI,MOSI,"SPI Master Output Slave Input"
    B2,N/A,"Hardware input button #2"
    B3,N/A,"Hardware input button #3"
    B1,N/A,"Hardware input button #1"
    SCL,SCL,"I2C clock line"
    SDA,SDA,"I2C data line"
    GND,GND,"Ground"
    VDD,3V,"3V power supply"

.. tip:: Of course, you can capture button data manually (if your application utilizes more
    than 3 buttons), but if you connect the pins B1, B2, B3 to momentary push buttons that
    (when pressed) provide a path to ground, the Pinnacle touch controller will report all 3
    buttons' states for each touch (or even button only) events.

Model Labeling Scheme
---------------------

  TM\ [yyyxxx]_\ -202\ [i]_\ -\ [cc]_\ [o]_

  .. [yyyxxx] stands for the vertical & horizontal width of the trackpad, respectively.
  .. [i] stands for the hardwired interface protocol (3 = I2C, 4 = SPI). Notice, if there is a
    resistor populated at the R1 (470K ohm) junction (located just above the Pinnacle ASIC), it
    is configured for SPI, otherwise it is configured for I2C.
  .. [cc] stands for Custom Configuration which describes if a 470K ohm resistor is populated at
    junction R4. "30" (resistor at R4 exists) means that the hardware is configured to disable
    certain features despite what this library does. "00" (no resistor at R4) means that the
    hardware is configured to allow certain features to be manipulated by this library. These
    features include "secondary tap" (thought of as "right mouse button" in relative data mode),
    Intellimouse scrolling (Microsoft patented scroll wheel behavior -- a throw back to when
    scroll wheels were first introduced), and 180 degree orientation (your application can invert
    the axis data anyway).
  .. [o] stands for the overlay type (0 = none, 1 = adhesive, 2 = flat, 3 = curved)

Dependencies
=============
This driver depends on:

* `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_
* `Bus Device <https://github.com/adafruit/Adafruit_CircuitPython_BusDevice>`_

Please ensure all dependencies are available on the CircuitPython filesystem.
This is easily achieved by downloading `the Adafruit library and driver bundle
<https://github.com/adafruit/Adafruit_CircuitPython_Bundle>`_.

How to Install
=====================
This library is deployed to pypi.org, so you can easily install this library
using ``pip3 install circuitpython-cirque-pinnacle`` or use the following
commands:

.. code-block:: shell

    git clone https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle.git
    cd CircuitPython_Cirque_Pinnacle
    python3 setup.py install

To install globally, prefix the last command with ``sudo``.

Usage Example
=============

Ensure you've connected the TMyyyxxx correctly by running the `examples/` located in the `examples
folder of this library <https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle/tree/master/examples>`_.

Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle/blob/master/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.

Sphinx documentation
-----------------------

Sphinx is used to build the documentation based on rST files and comments in the code. First,
install dependencies (feel free to reuse the virtual environment from above):

.. code-block:: shell

    python3 -m venv .env
    source .env/bin/activate
    pip install Sphinx sphinx-rtd-theme

Now, once you have the virtual environment activated:

.. code-block:: shell

    cd docs
    sphinx-build -E -W -b html . _build/html

This will output the documentation to ``docs/_build/html``. Open the index.html in your browser to
view them. It will also (due to -W) error out on any warning like Travis will. This is a good way to
locally verify it will pass.
