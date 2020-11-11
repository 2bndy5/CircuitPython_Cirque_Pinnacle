"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

from os import path
from setuptools import setup

# To use a consistent encoding
from codecs import open

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="circuitpython-cirque-pinnacle",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    description="A CircuitPython driver for Cirque Pinnacle (1CA027) touch "
    "controller used in Cirque Trackpads implementing the Adafruit_BusDevice library.",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    # The project's main homepage.
    url="https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle",
    # Author details
    author="Brendan Doherty",
    author_email="2bndy5@gmail.com",
    install_requires=["Adafruit-Blinka", "adafruit-circuitpython-busdevice"],
    # Choose your license
    license="MIT",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Hardware",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
    ],
    # What does your project relate to?
    keywords="adafruit blinka circuitpython Pinnacle "
    "touch sensor driver Cirque trackpad",
    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    # TODO: IF LIBRARY FILES ARE A PACKAGE FOLDER,
    #       CHANGE `py_modules=['...']` TO `packages=['...']`
    packages=["circuitpython_cirque_pinnacle"],
    # Extra links for the sidebar on pypi
    project_urls={
        "Documentation": "https://circuitpython-cirque-pinnacle.readthedocs.io",
    },
    download_url="https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle/releases",
)
