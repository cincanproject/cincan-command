
==============
Advanced Usage
==============

.. toctree::
   :maxdepth: 3
   :hidden:

-----------
Using tools
-----------


A tool can be invoked with cincan using 'run' sub-command like this:
 

.. code-block:: shell

   cincan run <tool> <parameters..

-----------------------
Version checks of tools
-----------------------

By default, every time tool is used, it's version status is showed. Is it up-to-date compared to Docker Hub, or maybe upstream has later version which is not ended up into our Docker Hub yet? This feature is available only for `cincan` tools, for those which are configured correctly.

If you want to disable it, modify/add file `~/.cincan/config.json` to contain attribute `show_updates` and set it as `false`.

----------------------
Input and output files
----------------------

As the tools are actually ran on docker container,
possible input and output files must be
transferred into and out from the container.
As default, this happens transparently as running the tools without docker.
For example, if you have file ``myfile.pcap``,
the following command should give you JSON-formatted output from 'tshark':


.. code-block:: shell

    cincan run cincan/tshark -r myfile.pcap
    cincan/tshark: <= myfile.pcap in

If you redirect output to a file, the file should be downloaded from the
container as you would expect, for example:

.. code-block:: shell

    cincan run cincan/tshark -r myfile.pcap -w result.pcap
    cincan/tshark: <= myfile.pcap in
    cincan/tshark: => result.pcap

Use argument `-q` to get rid of the log indicating which files are copied in or
out, e.g.


.. code-block:: shell

    cincan -q run cincan/tshark -r myfile.pcap -w result.pcap

Please note that `-q` is before the `run` sub command.

----------------------------
Limitations for input/output
----------------------------

Output files are only fetched to the current directory and to it's sub directories.
This is a safety feature to block dockerized tools for overwriting
arbitrary filesystem files.
E.g. the following does not produce any output files to ``/tmp``.

.. code-block:: shell

    cincan run cincan/tshark -r myfile.pcap -w /tmp/result.pcap


However, depending on the WORKDIR value of the container, you may get
unexpected files to current directory, such as `tmp/result.pcap`
in the sample above.

As default, the 'cincan' tool treat all existing files
listed in command line arguments as input files, so it may also upload
*output files* if those already exists when command is invoked. E.g.
when you run the following command several times you notice that the
file `result.pcap` gets uploaded to the container only to be
overwritten.

.. code-block:: shell

    cincan run cincan/tshark -r myfile.pcap -w result.pcap
    cincan/tshark: <= myfile.pcap in
    cincan/tshark: <= result.pcap in
    cincan/tshark: => result.pcap

This may become problem e.g. when you must give the command
and output directory which contains a lot of data already and
all that data gets (unnecessarily) copied to the container.