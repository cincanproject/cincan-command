.. CinCan Command documentation master file, created by
   sphinx-quickstart on Tue Jun  2 22:41:41 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

==========================================
Welcome to CinCan Command's documentation!
==========================================

.. toctree::
   :maxdepth: 2
   :hidden:
   :glob:

   *



CinCan Command
==============

The tool ``cincan`` command provided for a convenient
use of the native command-line tools provided as Docker images. CinCan Command is build to be particularly used for tools packed in the CinCan project. The list of the tools can be found from the CinCan's `tool repository. <https://gitlab.com/CinCan/tools>`_ 

*However*, it should be usable for most of the other CLI based Docker images.

Supported platforms  
-------------------

The ``cincan`` tool should run on all fairly modern Linux distributions.
Partial support for macOS is available - tested to work with macOS Catalina.

On Windows ``cincan`` **does not work**, unfortunately. `WSL 2 <https://docs.microsoft.com/en-us/windows/wsl/about>`_ has been tested to be enabler in this case.

Getting started
---------------

As prerequisite you must have installed ``Docker`` **18.09** for running the tools,
and ``Python`` **3.6+** and ``pip`` Python package management program for the command program.
Consult your system documentation how to install them.

Tool can be found from `Python Package Index (PyPi) <https://pypi.org/project/cincan-command/>`_ and can be installed in the most of the cases as:

.. code-block:: shell

   pip install cincan-command


See more detailed installation steps in :ref:`installation` section.

Quick Usage
-----------

.. Indices and tables
.. ==================

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
