.. _cincan_list:

===========
Cincan list
===========

Show `available tools <https://gitlab.com/CinCan/tools>`_ dockerized in CinCan project, their versions and possible updates with ``cincan list`` command like this:

.. code-block:: shell

   cincan list [OPTIONS]

You can see the list of available tools with:

.. code-block:: shell

   cincan list

Show your local tools with all tags:

.. code-block:: shell

   cincan list --local --all

**Note**: ``cincan list`` is using list command from module `cincan-registry <https://gitlab.com/CinCan/cincan-registry>`_. Consult the module's documentation for all available options.
