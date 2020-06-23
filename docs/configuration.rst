.. _configuration:

=============
Configuration
=============

CinCan reads configuration from the ``~/.cincan/config.json`` file.

-----------------------
Version checks of tools
-----------------------

By default, every time a tool is used, its version status is shown. Version check will compare the local version of a tool with the version in Docker Hub and with the version in the tool's upstream repository in case the newer version has not ended up into our Docker Hub yet. This feature is available only for those CinCan tools which are configured correctly.

If you want to disable it, modify/add file ``~/.cincan/config.json`` to contain attribute ``show_updates`` and set it as ``false``.

Example file could look like:

.. code-block:: json
   :caption: ~/.cincan/config.json

   {
     "show_updates": false
   }
