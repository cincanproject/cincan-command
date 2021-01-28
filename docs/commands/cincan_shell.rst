.. _cincan_shell:

##########
Cincan shell
##########

Usage of ``cincan shell`` subcommand is intended for launching interactive shell into any image (not supported for running container yet), which has some shell installed.

It has similar optional arguments as ``cincan run`` command, excluding `--tty`, `--interactive` and `--entrypoint` parameters.

By default, it looks for ``/bin/bash`` and ``/bin/sh`` in that order, if nothing is specified.

Example use could look something like this:

.. code-block:: shell

    cincan shell busybox           
    busybox: Using shell from the path: /bin/sh
    / # 

Shell from the custom path could be defined as following, if it exist:

.. code-block:: shell

    cincan shell --shell=/bin/zsh cincan/test          


Additionally shell paths can be configured into configuration file. Values here `override` hardcoded default values.
Order defines which shell is selected if they are found.

.. code-block:: json
   :caption: ~/.cincan/config.json

   {
     "shells": [
        "/bin/zsh",
        "/bin/bash",
        "/bin/sh"
     ]
   }

