
About the lite version
======================

This library includes a "lite" version of the module ``glidepoint.py`` titled ``glidepoint_lite.py``.
The lite version is limited to only Relative and Absolute data modes. It has been developed to
save space on microcontrollers with limited amount of RAM and/or storage (like boards using the
ATSAMD21 M0). The following functionality has been removed from the lite version:

* `anymeas_mode_config()`
* `measure_adc()`
* `detect_finger_stylus()`
* `calibrate()`
* `calibration_matrix`
* `set_adc_gain()`
* `tune_edge_sensitivity()`
* ``_era_write_bytes()`` (private member for accessing the Pinnacle ASIC's memory)
* all comments and docstrings (meaning ``help()`` will provide no specific information)
