
Contributing Guidelines
=======================

Linting the source code
-----------------------

.. _pre-commit: https://pre-commit.com/

This library uses pre-commit_ for some linting tools like

- `black <https://black.readthedocs.io/en/stable/>`_
- `pylint <https://pylint.pycqa.org/en/stable/>`_
- `mypy <https://mypy.readthedocs.io/en/stable/>`_

To use pre-commit_, you must install it and create the cached environments that it needs.

.. code-block:: shell

    pip install pre-commit
    pre-commit install

Now, every time you commit something it will run pre-commit_ on the changed files. You can also
run pre-commit_ on staged files:

.. code-block:: shell

    pre-commit run

.. note::
    Use the ``--all-files`` argument to run pre-commit on all files in the repository.


Building the Documentation
--------------------------

To build library documentation, you need to install the documentation dependencies.

.. code-block:: shell

    pip install -r docs/requirements.txt

Finally, build the documentation with Sphinx:

.. code-block:: shell

    sphinx-build -E -W docs docs/_build/html

The rendered HTML files should now be located in the ``docs/_build/html`` folder. Point your
internet browser to this path and check the changes have been rendered properly.
