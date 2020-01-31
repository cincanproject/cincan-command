# Cincan command logging

Command `cincan` can produce experimental log with details of the
commands can and digests of the related data files. 
The log makes it possible to recall the commands which have been
invoked to a file.

Further, the log can be shared with collegues to see how they have
processed files using `cincan`.

Again, **this is highly experimental** feature!

## Enable logging

Logging is enabled by editing configuration file `~/.cincan/config.json`.
The file should be edited like this:

    {
      "command_log": true
    }

Now, to enable sharing, which is not required or can be enabled later, 
you clone the relevant git repository
into location `~/.cincan/shared`
(Note, you need to have credentials to access the repository).

    $ cd ~/.cincan
    $ git clone <repo-location> shared

FIXME: Our local experimental repository is
`git@gitlab.com:CinCan/log-sharing.git`.

Make sure that the repository is in correct directory 
e.g. by checking that the directory `~/.cincan/shared/.git`exists.

Note, you must explicitly use 'cincan' sub command `commit` to
commit and push your logs into the shared log repository. See below.

## Log files

For logging an unique 'uid' is created for each user.
The file is stored in file `~/.cincan/uid.txt`

Actual log files, one file per tool invocation are located into
`~/.cincan/shared/<uid>/logs/`

## Sharing log 

If you have cloned the log repository, you can share logs through
the log repository. Use the sub command `commit` to commit and push
your changes into the repository, e.g.

    $ cincan commit

If you have not shared your log repository, but you have already
used logging so that 'shared' directory is created,
then you can do the following to enable sharing:

    $ cd ~/.cincan/shared
    $ git init
    $ git remote add origin <repo-location>
    $ git pull origin master
    $ git branch --set-upstream-to=origin/master master"

## Using the log to see command history

There are two 'cincan' sub commands to use the log history.
Sub command `fanout` shows the commands which have used a file
as input and it is used like this:

    $ cincan fanout <file>

Another sub command `fanin` shows which commands have produced the file

    $ cincan fanin <file>

The matching is based on the digest of the file and not into the file name.
