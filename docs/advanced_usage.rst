
.. _advanced_usage:

==============
Advanced Usage
==============

.. contents:: Table of Contents
   :local:
   :backlinks: none

-----------
Using tools
-----------

A tool can be invoked with ``cincan`` using 'run' sub-command like this:

A specific `tool <https://gitlab.com/CinCan/tools>`_ can be invoked with 'run' sub-command like this:

.. code-block:: shell

   cincan run <tool> <parameters..>

For example, invoke the tool *cincan/pywhois* with:

.. code-block:: shell

   $ cincan run cincan/pywhois 127.0.0.1

|

----------------------
Input and output files
----------------------

As the tools are run on Docker containers, possible input and output files must be transferred into and out from the container. Normally, this happens transparently as if running the tools without Docker.

For example, use the following command to read a file named ``myfile.pcap`` with *cincan/tshark* and you should receive a JSON-formatted output:

.. code-block:: shell

   $ cincan run cincan/tshark -r myfile.pcap
   cincan/tshark: <= myfile.pcap

If you redirect the output to a file, the file will be transferred out from the container:

.. code-block:: shell

   $ cincan run cincan/tshark -r myfile.pcap -w result.pcap
   cincan/tshark: <= myfile.pcap in
   cincan/tshark: => result.pcap

Use argument ``-q`` to suppress the log indicating which files are copied in or out, e.g.

.. code-block:: shell

   $ cincan -q run cincan/tshark -r myfile.pcap -w result.pcap

**Note**: The argument ``-q`` is before the 'run' sub-command

.. topic:: Further reading: Limitations to input/output
   :name: input_output_limitations

   a) Output files are only fetched to the current directory and to its subdirectories. This is a safety feature to block dockerized tools for overwriting arbitrary filesystem files. For example, the following does not produce any output files to ``/tmp``.

      .. code-block:: shell

         $ cincan run cincan/tshark -r myfile.pcap -w /tmp/result.pcap

      However, depending on the ``WORKDIR`` value of the container, you may get unexpected files to the current directory, such as *tmp/result.pcap* with the above sample.

   b) By default, the ``cincan`` command treats all existing files listed in command-line arguments as input files, so it may also upload output files if those already exists when a command is invoked. For example, when you run the following command several times, you will notice that the file ``result.pcap`` gets uploaded to the container only to be overwritten.

      .. code-block:: shell

         $ cincan run cincan/tshark -r myfile.pcap -w result.pcap
         cincan/tshark: <= myfile.pcap in
         cincan/tshark: <= result.pcap in
         cincan/tshark: => result.pcap

      This may become a problem, when you must give the command and output directory which contains a lot of data already and all that data gets (unnecessarily) copied to the container, for example.

|

.. _avoid_uploading_content_from_output_directories:

"""""""""""""""""""""""""""""""""""""""""""""""
Avoid uploading content from output directories
"""""""""""""""""""""""""""""""""""""""""""""""

In many cases, you may want to run a tool several times producing multiple files to the output directory. Since the ``cincan`` command does not know which files are output and which are input (see: `Limitations to input/output <input_output_limitations_>`_), it repeatedly copies also the output files from the previous runs to the container. This process may slow down your work and requires extra disk space. You can avoid this by using 'run' argument ``--mkdir`` (or ``-d``) to explicitly create output directory into the container without copying over any possible content.

For example, consider the tool *cincan/volatility*, which expects you to give an output dump directory when extracting process data. The following extracts the memory dump of process 123 to a ``dump/`` directory:

.. code-block:: shell

    $ cincan run cincan/volatility -f image.raw --dump-dir dump/ memdump -p 123
    cincan/volatility: <= image.raw
    cincan/volatility: <= dump
    cincan/volatility: => dump/123.dmp

If you run the same command again for a different process, you'll notice that the already extracted file gets copied into the container as a potential input file:

.. code-block:: shell

    $ cincan run cincan/volatility -f image.raw --dump-dir dump/ memdump -p 456
    cincan/volatility: <= image.raw
    cincan/volatility: <= dump
    cincan/volatility: <= dump/123.dmp
    cincan/volatility: => dump/456.dmp

You can address this by explicitly creating a ``dump/`` directory to the container (and also likely make your analysis faster):

.. code-block:: shell

    $ cincan run -d dump cincan/volatility -f image.raw --dump-dir dump/ memdump -p 789
    cincan/volatility: <= image.raw
    cincan/volatility: <= dump
    cincan/volatility: => dump/789.dmp

**Tip**: The argument ``--mkdir`` (or ``-d``) can be provided many times to create multiple directories.

|

"""""""""""""""""""""""""""""""
Input and output file filtering
"""""""""""""""""""""""""""""""

You can explicitly filter input files (copied to the container) and output files (copied from the container). The filtering is done by giving a glob-style pattern by run command arguments: ``--in-filter`` (or ``-I``) for input file filtering and ``--out-filter`` (or ``-O``) for output file filtering. When the arguments are prefixed with ``^``, they are negative filters for filtering-out files.

+-----------------------------+----------------------------------------------------+
| Argument                    | Description                                        |
+=============================+====================================================+
| ``--in-filter [PATTERN]``   | Match files to upload by the pattern               |
+-----------------------------+----------------------------------------------------+
| ``--in-filter ^[PATTERN]``  | Filter out files to upload which match the pattern |
+-----------------------------+----------------------------------------------------+
| ``--out-filter [PATTERN]``  | Match files to download by the pattern             |
+-----------------------------+----------------------------------------------------+
| ``--out-filter ^[PATTERN]`` | Filter out files to upload which match the pattern |
+-----------------------------+----------------------------------------------------+

For example, consider `the previous case <avoid_uploading_content_from_output_directories_>`_ with the tool *cincan/volatility*. An alternative approach would be to filter out copying of files under ``dump/`` like this:

.. code-block:: shell

    $ cincan run -I "^dump/*" cincan/volatility -f image.raw --dump-dir dump memdump -p 789
    cincan/volatility: <= image.raw
    cincan/volatility: <= dump
    cincan/volatility: => dump/789.dmp

|

-----------------------------------------------------------
Filtering by `.cincanignore` - file stored inside container
-----------------------------------------------------------

Downloadable files can be filtered by ``.cincanignore`` file as well, which should be stored inside tool container in build phase.
All files listed in that file are not downloaded from the container.
Paths are relative of the working directory of container.

Ignore file supports ``#`` char as comment character.

See example file from path ``samples/.cincanignore``:

.. literalinclude:: ../samples/.cincanignore
   :caption: samples/.cincanignore


This works with user supplied filters as well.

Argument ``--no-defaults`` can be passed for ``run`` command to not use this file.

|

--------------------------------
Providing tool input as tar file
--------------------------------

Instead of letting the tool to figure out the input files from command-line, you
can provide the input files directly as tar-file. When this is done,
the tool does not try to apply any logic to upload files, so you
have the full control. You cannot use input file filtering with this approach.

The input tar file is specified with option ``--in`` and
you can provide a file or use ``-`` to read from standard input. For example:

.. code-block:: shell

   $ tar c myfile.pcap | cincan run --in - cincan/tshark -r myfile.pcap

-------------------------------
Getting tool output as tar file
-------------------------------

You can also request the tool output files in a tar container.
This is done with argument ``--out``.
You can provide for the argument either a file name or ``-``for standard output.
You can also apply output file filtering to limit the number of files copied into the output tar archive.

For example, the following should write file ``output.tar``

.. code-block:: shell

    $ cincan run --out output.tar cincan/tshark -r myfile.pcap -w output.pcap

|

-------------------------------------
Running tool with interactive support
-------------------------------------

We are using `radare2 <https://gitlab.com/CinCan/tools/tree/master/radare2>`_ as example here. Tool with interactive mode requires `--interactive` (or `-i`) and --tty (or `-t`) switches. Start radare2 disassembler for local file `/bin/ls` by running command:

.. code-block:: shell

   $ cincan run -it cincan/radare2 r2 /bin/ls
   cincan/radare2: <= /usr/bin/ls
   -- We are surrounded by the enemy. - Excellent, we can attack in any direction!
   [0x00005b10]> aaa
   [x] Analyze all flags starting with sym. and entry0 (aa)
   [x] Analyze function calls (aac)
   [x] Analyze len bytes of instructions for references (aar)
   [x] Check for objc references
   [x] Check for vtables
   [x] Type matching analysis for all functions (aaft)
   [x] Propagate noreturn information
   [x] Use -AA or aaaa to perform additional experimental analysis.
   [0x00005b10]>

radare2 should open ``/bin/ls`` file, and this can be analysed by typing ``aaa`` and pressing enter.

|

---------------
All run options
---------------

The following table lists all command-line options available for the run -sub command:

+-------------------------+--------+---------------------------------------------------------------+
| Specific to ``cincan``  |        | Description                                                   |
+=========================+========+===============================================================+
| | --in tar-file         |        | Upload input to container in a tar                            |
+-------------------------+--------+---------------------------------------------------------------+
| | --out tar-file        |        | Download output files from container to a tar                 |
+-------------------------+--------+---------------------------------------------------------------+
| | --in-filter pattern   | | -I   | Filter input files, prefix ^ to negate the filter             |
+-------------------------+--------+---------------------------------------------------------------+
| | --out-filter pattern  | | -O   | Filter output files, prefix ^ to negate the filter            |
+-------------------------+--------+---------------------------------------------------------------+
| | --mkdir directory     | | -d   | Mark output directory, not uploaded as input                  |
+-------------------------+--------+---------------------------------------------------------------+
| | --no-defaults         |        | Ignore all container specific output filters. (.cincanignore) |
+-------------------------+--------+---------------------------------------------------------------+

|

""""""""""""""""""
``run`` subcommand
""""""""""""""""""

+---------------------------+------+---------------------------------------------------------------+
| Similar to ``docker run`` |      | Description                                                   |
+===========================+======+===============================================================+
| --tty                     | | -t | Allocate a pseudo-TTY                                         |
+---------------------------+------+---------------------------------------------------------------+
| --interactive             | | -i | Keep STDIN open even if not attached                          |
+---------------------------+------+---------------------------------------------------------------+
| --network value           |      | Network to connect                                            |
+---------------------------+------+---------------------------------------------------------------+
| --user name               |      | User to run with                                              |
+---------------------------+------+---------------------------------------------------------------+
| --cap-add CAP             |      | Add kernel capability                                         |
+---------------------------+------+---------------------------------------------------------------+
| --cap-drop CAP            |      | Drop kernel capability                                        |
+---------------------------+------+---------------------------------------------------------------+
| --runtime                 |      | Container runtime                                             |
+---------------------------+------+---------------------------------------------------------------+

Consult `Docker run documentation <(https://docs.docker.com/engine/reference/commandline/run/>`_ for more details.

|

--------------------------------------
Invoking tool without 'cincan' wrapper
--------------------------------------

Sometimes you cannot use the services provided by the 'cincan' frontend.
For example, as files are copied around you may ran out of disk space or
experience long delays when working with large files. An another reason
might be use of some 'docker' options which are not available in the
'cincan' tool.

Good luck with that! (seriously, no pun intended)
Please consult Docker documentation for details.

|

-------------
Configuration
-------------

"""""""""""""""""""""""
Version checks of tools
"""""""""""""""""""""""

By default, every time a tool is used, its version status is shown. Version check will compare the local version of a tool with the version in Docker Hub and with the version in the tool's upstream repository in case the newer version has not ended up into our Docker Hub yet. This feature is available only for those CinCan tools which are configured correctly.

If you want to disable it, modify/add file ``~/.cincan/config.json`` to contain attribute ``show_updates`` and set it as ``false``.

Example file could look like:

.. code-block:: json
   :caption: ~/.cincan/config.json

   {
     "show_updates": false
   }
