.. CinCan Command documentation master file, created by
   sphinx-quickstart on Tue Jun  2 22:41:41 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

==========================================
Welcome to CinCan Command's documentation!
==========================================

.. toctree::
   :hidden:

   Quick Start <self>

.. toctree::
   :maxdepth: 2
   :hidden:

   installation
   ./commands/index.rst
   configuration
   symlinks/CHANGELOG


Introduction
==============

The ``cincan`` command provides convenient use of native command-line tools in Docker images. The command is particularly used for security tools packed in the CinCan project. The list of available tools can be found from CinCan's `tool repository <https://gitlab.com/CinCan/tools>`_. *However*, it should be usable for most of the other CLI based Docker images.

But Why?
--------

Regular usage of Docker images introduces the problem of moving files safely from the host machine into the container. Usually, this is achieved by using *volume mounts*, but this breaks the concept of isolation, as the host machine is exposed to the container. The ``cincan`` command attempts to avoid usage of volumes while providing a similar command-line experience as using the tool natively.

Some additional features, such as tool version listing and tool command history are provided.

Supported platforms
-------------------

The ``cincan`` command should run on all fairly modern Linux distributions. Partial support for macOS is available - tested to work with macOS Catalina.

On Windows, ``cincan`` **does not work**, unfortunately. `WSL 2 <https://docs.microsoft.com/en-us/windows/wsl/about>`_ has been tested to be an enabler in this case.

Getting started
---------------

As a prerequisite, you must have ``Docker`` **18.09+** installed for running the tools, and ``Python`` **3.6+** and ``pip`` Python package manager to install the ``cincan`` command.

The ``cincan`` command is in `Python Package Index (PyPi) <https://pypi.org/project/cincan-command/>`_ and can typically be installed by running:

.. code-block:: shell

   pip install cincan-command

See more detailed installation steps in the :ref:`installation` section.

--------------
Invoking tools
--------------

You can see the list of `available tools <https://gitlab.com/CinCan/tools>`_ dockerized in CinCan project with:

.. code-block:: shell

   cincan list

A specific tool can be invoked with ``cincan run`` like this:

.. code-block:: shell

   cincan run [OPTIONS] TOOL[:TAG] [ARG...]

For example, invoke the tool `cincan/pywhois` with:

.. code-block:: shell

   cincan run cincan/pywhois 127.0.0.1

Many tools will show you help documentation if you invoke them without arguments, for example:

.. code-block:: shell

   cincan run cincan/tshark

More help is available with options like `-h` or `-–help`, depending on the tool.

**Note**: Make sure ``Docker`` is running when you use the ``cincan`` command.

See more examples in the :ref:`commands` section.

.. Indices and tables
.. ==================

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
