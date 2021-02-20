.. _cincan_shell:

############
Cincan shell
############

Usage of ``cincan shell`` subcommand is intended for launching interactive shell into any image, which has some shell installed.

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

*************
Inspect container after command execution
*************

``cincan run`` has option to create new image from produced container. It can be enabled with switch ``--create-image`` or ``-c``.
If something weird is happening in the container or you want to inspect produced environment more closely, you can for example launch shell into it afterwards. Image must have a shell for this to work.

For example, if you could run some command with specific input files, they would be found from the new image.

.. code-block:: shell

    cincan run --create-image <image> <command(s) with files>
    <lines of output>
    ...
    ...
    quay.io/cincan/<name>: Creating new image from the produced container.
    quay.io/cincan/<name>: Use it with following id. Shorter version can be used.
    quay.io/cincan/<name>: id: sha256:08f40d14ff205178d1681c829be93fd19cf464a1bf40c19ac2ea51f0a8a00f88
    quay.io/cincan/<name>: e.g. run 'cincan shell sha256:08f40d14ff' to open shell.


*********************
Further configuration
*********************

Shell paths can be configured additionally into configuration file. Values here `override` hardcoded default values.
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

