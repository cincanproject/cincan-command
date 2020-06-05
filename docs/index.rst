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

   Home <self>
   installation
   advanced_usage
   symlinks/CHANGELOG


CinCan Command
==============

The tool ``cincan`` command provided for a convenient
use of the native command-line tools provided as Docker images. Build to be particularly used for security tools packed in the CinCan project. The list of the available tools can be found from the CinCan's `tool repository. <https://gitlab.com/CinCan/tools>`_ 

*However*, it should be usable for most of the other CLI based Docker images.

But Why?
--------

Regular usage of Docker images introduces the problem of moving files safely from host machine into container. Usually this is achieved by using *volume mounts*, but this breaks the concept of isolation, as host machine is exposed into container. CinCan command attempts avoid usage of volumes while providing similar command line experience, as tool is naturally used.

Some additional features such as tool version listing and tool command history are provided.

Supported platforms  
-------------------

The ``cincan`` tool should run on all fairly modern Linux distributions.
Partial support for macOS is available - tested to work with macOS Catalina.

On Windows ``cincan`` **does not work**, unfortunately. `WSL 2 <https://docs.microsoft.com/en-us/windows/wsl/about>`_ has been tested to be enabler in this case.

Getting started
---------------

As prerequisite you must have installed ``Docker`` **18.09+** for running the tools,
and ``Python`` **3.6+** and ``pip`` Python package management program for the command program.

Tool can be found from `Python Package Index (PyPi) <https://pypi.org/project/cincan-command/>`_ and can be installed in the most of the cases as:

.. code-block:: shell

   pip install cincan-command


See more detailed installation steps in :ref:`installation` section.

--------------
Invoking tools
--------------

The list of available **cincan** tools can be provided as:

.. code-block:: shell

   cincan list

A tool can be invoked with cincan using 'run' sub-command like this:
 

.. code-block:: shell

   cincan run <tool> <parameters..>

As previously showed, you get the list of tools dockerized in 'CinCan' project
with ``cincan list``.
For example the tool `cincan/pywhois`:

.. code-block:: shell

   cincan run cincan/pywhois 127.0.0.1

Many tools give you help information, if you invoke them without arguments, for example:

.. code-block:: shell

   cincan run cincan/tshark

More help is available with options like `-h` or `--help`, depending on the tool.


.. Indices and tables
.. ==================

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
