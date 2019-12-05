# CinCan command

The tool `cincan` command provide for a convenient
use of the native command-line tools provided as docker images.

:warning: Currently the tool is a proof-of-concept under construction.

## Supported platforms

The `cincan` tool should run on fairly modern Linux distributions.
It is not tested on MacOS, but there should be no blocking issues in principle.
On Windows `cincan` **noes not work**, unfortunately.

## Installation

As prerequisite you must have installed `Docker` for running the tools,
and `Python 3` and `pip` Python package management program for the command program.
Consult your system documentation how to install them.

The command program is then installed using pip for Python 3:

    % sudo pip install cincan-command

If you invoke the pip installation with `sudo` the command `cincan` should be added to your path.
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

Please note that `-q` is before the `run` sub command.

### Limitations for input/output

Output files are only fetched to the current directory and to it's sub directories.
This is a safety feature to block dockerized tools for overwriting
arbitrary filesystem files.
E.g. the following does not produce any output files to `/tmp`.

    % cincan run cincan/tshark -r myfile.pcap -w /tmp/result.pcap

However, depending on the WORKDIR value of the container, you may get
unexpected files to current directory, such as `tmp/result.pcap`
in the sample above.

As default, the 'cincan' tool treat all existing files
listed in command line arguments as input files, so it may also upload
*output files* if those already exists when command is invoked. E.g.
when you run the following command several times you notice that the
file `result.pcap` gets uploaded to the container only to be
overwritten.

    % cincan run cincan/tshark -r myfile.pcap -w result.pcap
    cincan/tshark: <= myfile.pcap in
    cincan/tshark: <= result.pcap in
    cincan/tshark: => result.pcap

This may become problem e.g. when you must give the command
and output directory which contains a lot of data already and
all that data gets (unnecessarily) copied to the container.

### Avoid uploading content from output directories

On many cases a tool writes files into an output directory and you may
run the tool several times to produce many files to the output directory.
However, as 'cincan' does not know which files are output and which are input,
it repeatedly copies also the output files from the previous runs to container.
This may process may slow down your work and requires extra disk space.

This is avoided by using run argument `--mkdir` (or `-d`) to explicitly
create output directory into container without copying over any possible 
content.

For example, consider the tool 'volatility' which expects you to
give an output dump directory when extracting process data, e.g.
the following extracts the memory dump of process 123 to directory `dump/`

    % cincan run cincan/volatility -f image.raw --dump-dir dump/ memdump -p 123
    cincan/volatility: <= image.raw
    cincan/volatility: <= dump
    cincan/volatility: => dump/123.dmp

However, if you extract again you notice that the already extracted file
gets copied into the container as potential input file:

    % cincan run cincan/volatility -f image.raw --dump-dir dump/ memdump -p 456
    cincan/volatility: <= image.raw
    cincan/volatility: <= dump
    cincan/volatility: <= dump/123.dmp
    cincan/volatility: => dump/456.dmp

This can easily slow down your analysis a lot when many process
files are copied around unnecessarily. You can address this by
explicitly creating `dump/` directory to the container this way:

    % cincan run -d dump cincan/volatility -f image.raw --dump-dir dump/ memdump -p 789
    cincan/volatility: <= image.raw
    cincan/volatility: <= dump
    cincan/volatility: => dump/789.dmp

You can provide the argument many times to create multiple directories.

### Input and output file filtering

You can explicitly filter input files, which are copied to the container,
and output files, which are copied from the container. The filtering is done
by giving a glob-style pattern by run command arguments
`--in-filter` (or `-I`) for input file filtering
and  `--out-filter` (or `-O`) for output file filtering.
Negative filters for filtering-out files are prefixed with ^.

| Argument                 | Description |
|--------------------------|-------------|
| --in-filter pattern      | Match files to upload by the pattern |
| --in-filter ^pattern     | Filter out files to upload which match the pattern |
| --out-filter pattern     | Match files to download by the pattern |
| --out-filter ^pattern    | Filter out files to download which match the pattern |

For example, consider the previous case with
tool 'volatility'.
An alternative approach would be to filter out 
copying of files under `dump/` like this:

    % cincan run -I "^dump/*" cincan/volatility -f image.raw --dump-dir dump memdump -p 789
    cincan/volatility: <= image.raw
    cincan/volatility: <= dump
    cincan/volatility: => dump/789.dmp

### Providing tool input as tar file

Instead of letting the tool to figure out the input files from command-line, you
can provide the input files directly as tar-file. When this is done,
the tool does not try to apply any logic to upload files, so you
have the full control. You cannot use input file filtering with this approach.

The input tar file is specified with option `--in` (or `-i` ) and
you can provide a file or use `-` to read from standard input. For example:

    % tar c myfile.pcap | cincan run --in - cincan/tshark -r myfile.pcap

### Getting tool output as tar file

You can also request the tool output files in a tar container. This
is done with argument `--out` (or `-o`). You can provide for the argument
either a file name or `-`for standard output. You can also apply output
file filtering to limit the number of files copied into the output tar archive.

For example, the following should write file `output.tar`

    % cincan run --out output.tar cincan/tshark -r myfile.pcap -w output.pcap

### All run options

The following table lists all command-line options available for the run -sub command:

| Option                  |    | Description |
|-------------------------|----|-------------|
| --in tar-file           | -i | Upload input to container in a tar |
| --out tar-file          | -o | Download output files from container to a tar|
| --in-filter pattern     | -I | Filter input files, prefix ^ to negate the filter|
| --out-filter pattern    | -O | Filter output files, prefix ^ to negate the filter
| --mkdir directory       | -d | Mark output directory, not uploaded as input
| --network value         |    | Network to connect (see help of docker run --network)|
| --user name             |    | User to run with (see help of docker run --user)|
| --cap-add CAP           |    | Add kernel capability (see help of docker run --cap-add)|
| --cap-drop CAP          |    | Drop kernel capability (see help of docker run --cap-drop)|

## Invoking tool without 'cincan' wrapper

Sometimes you cannot use the services provided by the 'cincan' frontend. 
For example, as files are copied around you may ran out of disk space or
experience long delays when working with large files. An another reason
might be use of some 'docker' options which are not available in the
'cincan' tool.

Good luck with that! (seriously, no pun intended)
Please consult Docker documentation for details.
