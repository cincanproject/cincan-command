.. _cincan_run:

##########
Cincan run
##########

CinCan runs security analysis tools in Docker containers.

.. contents:: Table of Contents
   :local:
   :backlinks: none

***********
Using tools
***********

A specific `tool <https://gitlab.com/CinCan/tools>`_ can be invoked with ``cincan run`` command like this:

.. code-block:: shell

   cincan run [OPTIONS] TOOL[:TAG] [ARG...]

For example, invoke the tool *cincan/pywhois* with:

.. code-block:: shell

   $ cincan run cincan/pywhois 127.0.0.1

.. topic:: Further reading: Invoking tools without ``cincan run`` command
   :name: invoking_without_cincan

   Sometimes you may be unable to use the tools with the ``cincan run`` command. For example, as files are copied around you may run out of disk space or experience long delays when working with large files. Another reason might be the use of some ``docker`` options which are not available in the ``cincan run`` command.

   Good luck with that! (Seriously, no pun intended.) Please consult Docker documentation for details.

|

**********************
Input and output files
**********************

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

**Note**: The argument ``-q`` is before the 'run' subcommand

.. topic:: Further reading: Limitations to input/output
   :name: input_output_limitations

   a) Output files are only fetched to the current directory and its subdirectories. This is a safety feature to block dockerized tools for overwriting arbitrary filesystem files. For example, the following does not produce any output files to ``/tmp``.

      .. code-block:: shell

         $ cincan run cincan/tshark -r myfile.pcap -w /tmp/result.pcap

      However, depending on the ``WORKDIR`` value of the container, you may get unexpected files to the current directory, such as *tmp/result.pcap* with the above sample.

   b) By default, the ``cincan run`` command treats all existing files listed in command-line arguments as input files, so it may also upload output files if those already exists when a command is invoked. For example, when you run the following command several times, you will notice that the file ``result.pcap`` gets uploaded to the container only to be overwritten.

      .. code-block:: shell

         $ cincan run cincan/tshark -r myfile.pcap -w result.pcap
         cincan/tshark: <= myfile.pcap in
         cincan/tshark: <= result.pcap in
         cincan/tshark: => result.pcap

      This may become a problem, when you must give the command and output directory which contains a lot of data already and all that data gets (unnecessarily) copied to the container, for example.

|

.. _avoid_uploading_content_from_output_directories:

Avoid uploading content from output directories
===============================================

In many cases, you may want to run a tool several times producing multiple files to the output directory. Since the ``cincan run`` command does not know which files are output and which are input (see: `Limitations to input/output <input_output_limitations_>`_), it repeatedly copies also the output files from the previous runs to the container. This process may slow down your work and requires extra disk space. You can avoid this by using ``--mkdir`` (or ``-d``) option to explicitly create output directory into the container without copying over any possible content.

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

**Tip**: The ``--mkdir`` (or ``-d``) option can be provided many times to create multiple directories.

|

Input and output file filtering
===============================

You can explicitly filter input files (copied to the container) and output files (copied from the container). The filtering is done by giving a glob-style pattern by: ``--in-filter`` (or ``-I``) option for input file filtering and ``--out-filter`` (or ``-O``) option for output file filtering. When the options are prefixed with ``^``, they are negative filters for filtering-out files.

+-----------------------------+----------------------------------------------------+
| Option                      | Description                                        |
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

Providing tool input as a tar file
==================================

Instead of letting the ``cincan run`` command figure out the input files from the command-line (see: `Limitations to input/output <input_output_limitations_>`_), you can provide the input files directly as a tar file. When this is done, the ``cincan run`` command does not try to apply any logic to upload files, so you have full control.

The input tar file is specified with the ``--in`` option and you can provide a file or use ``-`` to read from standard input. For example:

.. code-block:: shell

   $ tar c myfile.pcap | cincan run --in - cincan/tshark -r myfile.pcap

**Note**: You cannot use input file filtering with this approach.

Getting tool output as a tar file
=================================

The ``cincan run`` command also supports creating a tar file from a tool's output files. This is done with ``--out`` option. You can provide for the option either a file name or ``-`` for standard output. You can also apply output file filtering to limit the number of files copied into the output tar file.

For example, the following should write file ``output.tar``

.. code-block:: shell

    $ cincan run --out output.tar cincan/tshark -r myfile.pcap -w output.pcap

|

Additional performance optimization
===================================

Sometimes the containerized tool may run slow because
a lot of files gets downloaded from the container.
This may happen even when you filter the unnecessary files out,
as the ``cincan`` command may still download them before they
are discarded.

If this is suspected, you can try a couple of things:

1. Use option ``--no-implicit-output`` with ``--mkdir``. This causes only the given output directories to be downloaded from the container.

2. Use option ``--explicit-output`` to explicilty list all files and/or directories which are downloaded from the container.


|

***************************************
Running a tool with interactive support
***************************************

Tools with interactive mode require ``--interactive`` (or ``-i``) and/or ``--tty`` (or ``-t``) options.

We are using *cincan/radare2* as an example of a tool with an interactive mode here. Start *cincan/radare2* disassembler for local file ``/bin/ls`` by running:

.. code-block:: shell

   $ cincan run -i cincan/radare2 r2 /bin/ls
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

You should see an interactive prompt like above where *cincan/radare2* has opened the ``/bin/ls`` file. Start the analysis by typing ``aaa`` and pressing enter. Type ``exit`` or press ``ctrl + d`` to quit the interactive prompt.

|

*****************************************
Filtering output files by `.cincanignore`
*****************************************

You can alter how output files are handled by adding specially named file
``.cincanignore`` into a container on built-time.
All files listed in the file are not downloaded from the container. Paths are relative to the working directory of the container.

See `example file <https://gitlab.com/CinCan/cincan-command/-/blob/master/samples/.cincanignore>`_ from path ``samples/.cincanignore``:

.. literalinclude:: ../../samples/.cincanignore
   :caption: samples/.cincanignore


This works for user-supplied filters as well. Ignore file supports ``#`` char as a comment character.

**Tip**: Option ``--no-defaults`` can be passed to not use this file.

|

.. _run_tool_tag:

**********
Tool[:tag]
**********

If you need to modify default tag when CinCan pulls a dockerized tool, you can do it by explicitly adding ``tool[:tag]`` to the command, for example:

.. code-block:: shell

   $ cincan run cincan/pywhois:latest-stable 127.0.0.1

**Tip**: To set the tag default, see :ref:`conf_tool_tag`.

|

*******************
All ``run`` options
*******************

The following table lists all command-line options available for the ``cincan run`` command:

+------------------------------------+---------------------------------------------------------------+
| Name, shorthand                    | Description                                                   |
+====================================+===============================================================+
|                                    | Specific to ``cincan run``                                    |
+------------------------------------+---------------------------------------------------------------+
| ``--in`` tar-file                  | Upload input to container in a tar                            |
+------------------------------------+---------------------------------------------------------------+
| ``--out`` tar-file                 | Download output files from container to a tar                 |
+------------------------------------+---------------------------------------------------------------+
| ``--in-filter, -I`` pattern        | Filter input files, prefix ^ to negate the filter             |
+------------------------------------+---------------------------------------------------------------+
| ``--out-filter, -O`` pattern       | Filter output files, prefix ^ to negate the filter            |
+------------------------------------+---------------------------------------------------------------+
| ``--mkdir, -d`` directory          | Mark output directory, not uploaded as input                  |
+------------------------------------+---------------------------------------------------------------+
| ``--no-defaults``                  | Ignore all container specific output filters. (.cincanignore) |
+------------------------------------+---------------------------------------------------------------+
| ``--no-implicit-output, -M``       | No implicit output, only download the marked output directories |
+------------------------------------+---------------------------------------------------------------+
| ``--explicit-output, -e`` file     | Give downloaded result file or directory explicitly           |
+------------------------------------+---------------------------------------------------------------+
|                                    | Similar to ``docker run``                                     |
+------------------------------------+---------------------------------------------------------------+
| ``--tty, -t``                      | Allocate a pseudo-TTY                                         |
+------------------------------------+---------------------------------------------------------------+
| ``--interactive, -i``              | Keep STDIN open even if not attached                          |
+------------------------------------+---------------------------------------------------------------+
| ``--network`` value                | Network to connect                                            |
+------------------------------------+---------------------------------------------------------------+
| ``--user`` name                    | User to run with                                              |
+------------------------------------+---------------------------------------------------------------+
| ``--cap-add`` CAP                  | Add kernel capability                                         |
+------------------------------------+---------------------------------------------------------------+
| ``--cap-drop`` CAP                 | Drop kernel capability                                        |
+------------------------------------+---------------------------------------------------------------+
| ``--runtime``                      | Container runtime                                             |
+------------------------------------+---------------------------------------------------------------+

Consult `Docker run documentation <https://docs.docker.com/engine/reference/commandline/run/>`_ for more details.
