.. _cincan_base:

``cincan`` is the base command for the CinCan CLI.

.. Hide level 2 heading from table of contents
.. raw:: html

 <h3>Options for base command</h3>

+----------------------------------+------------------------------------------------------------------+
| Option                           | Description                                                      |
+==================================+==================================================================+
| ``--help, -h``                   | Show help text.                                                  |
+----------------------------------+------------------------------------------------------------------+
| ``-l``                           | Set logging level. Choose from DEBUG,INFO,WARNING,ERROR,CRITICAL |
+----------------------------------+------------------------------------------------------------------+
| ``--batch``                      | Use with automation. Disables some properties meant for tty      |
|                                  | device(s). Such as animations and version prints.                |
+----------------------------------+------------------------------------------------------------------+
| ``--quiet, -q``                  | Be quite quiet. Reduces logging level and includes batch.        |
+----------------------------------+------------------------------------------------------------------+
| ``--version, -v``                | Show  version information of cincan-command.                     |
+----------------------------------+------------------------------------------------------------------+


.. raw:: html

 <h3>Child commands</h3>


+----------------------------------+--------------------------------------------------------------+
| Command                          | Description                                                  |
+==================================+==============================================================+
| :ref:`cincan run <cincan_run>`   | CinCan runs security analysis tools in Docker containers.    |
+----------------------------------+--------------------------------------------------------------+
| :ref:`cincan list <cincan_list>` | See the list of available tools dockerized in CinCan project |
+----------------------------------+--------------------------------------------------------------+
