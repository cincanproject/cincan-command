# CinCan command

The tool `cincan` command provide for a convenient
use of the native command-line tools provided as docker images.

:warning: Currently the tool is a proof-of-concept under construction.

## Installation

As prerequisite you must have installed `Docker` for running the tools,
and `Python 3` and `pip` Python package management program for the command program.
Consult your system documentation how to install them.

The command program is then installed using pip for Python 3:

    % FIXME

If you invoke the command with `sudo` the command `cincan` should be added to your path.
Otherwise, you may need to do that yourself.

NOTE: You may want to install the tool into `virtualenv` to avoid conflicts with
other Python applications you may have. Please consult appropriate documentation.

You can check that all works as follows:

    % cincan list

If all goes well you get a list of the tools dockerized in the 'Cincan' project.
However, you can use any dockerized tools as long as they meet the
requirements listed in the end of this document.
First time running this will take a while as it must fetch information of the tools
and cache it locally.

## Running tools with cincan

### Invoking tools

A tool can be invoked with cincan using 'run' sub-command like this:

    % cincan run <tool> <parameters..>

As you may remember you get the list of tools dockerized in 'Cincan' project
with `cincan list`.
For example the tool `cincan/pywhois`:

    % cincan run cincan/pywhois 127.0.0.1

Many tools give you help information, if you invoke them without arguments, for example:

    % cincan run cincan/tshark

More help is available with options like `-h` or `--help`, depending on the tool.

### Input and output files

As the tools are actually ran on docker container,
possible input and output files must be
transferred into and out from the container.
As default, this happens transparently as running the tools without docker.
For example, if you have file `myfile.pcap`,
the following command should give you JSON-formatted output from 'tshark':

    % cincan run cincan/tshark -r myfile.pcap
    cincan/tshark: <= myfile.pcap in
    ...

If you redirect output to a file, the file should be downloaded from the
container as you would expect, for example:

    % cincan run cincan/tshark -r myfile.pcap -w result.pcap
    cincan/tshark: <= myfile.pcap in
    cincan/tshark: => result.pcap

Use argument `-q` to get rid of the log indicating which files are copied in or
out, e.g.

    % cincan -q run cincan/tshark -r myfile.pcap -w result.pcap

### Limitations for input/output

Output files are only fetched to the current directory and to it's sub directories.
This is a safety feature to block dockerized tools for overwriting
arbitrary filesystem files.
E.g. the following does not produce any output files to `/tmp`.

    % cincan -q run cincan/tshark -r myfile.pcap -w /tmp/result.pcap

However, depending on the WORKDIR value of the container, you may get
unexpected files to current directory, such as `tmp/result.pcap`
in the sample above.


### Explicit input/output files

FIXME

## Invoking tool without frontend

Sometimes you cannot use the services provided by the 'cincan' frontend.
For example, you wish to provide the files through mounts for their size
rather using the copy approach.

Good luck with that! (seriously, no pun intended)

## Tool log

FIXME

## Requirements for the dockerized tools

FIXME

## Testing a tool image

FIXME

