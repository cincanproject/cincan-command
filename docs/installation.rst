.. _installation:

============
Installation
============

.. toctree::
   :caption: Table of Contents
   :maxdepth: 3

As a prerequisite, you must have ``Docker`` **18.09+** installed for running the tools, and ``Python`` **3.6+** and ``pip`` Python package manager to install the ``cincan`` command.

**Note**: Docker below version 18.09 has not been tested, so there might be hope that it works.

--------------
Install Docker (>=18.09)
--------------

If you are running Ubuntu 18.04 or Debian 10, you can install Docker from the package repositories:

.. code-block:: shell

   sudo apt-get docker.io

One-liner for installing the Docker for almost any system, if you don't have Debian:

.. code-block:: shell

   curl -fsSL https://get.docker.com/ | sh

Add yourself to the `docker` group to communicate with the local installation of Docker:

.. code-block:: shell

   sudo usermod -aG docker $USER
   newgrp docker

Optionally, you can then test your installation running the Docker `hello-world` container:

.. code-block:: shell

    docker run hello-world

If you are encountering some problems, see the `official documentation for installing Docker <https://docs.docker.com/engine/install/>`_.

----------------------
Install Python (>=3.6)
----------------------

Newer distributions should have Python 3.6 or newer installed.
If you are running something older (like Ubuntu 16.04 Xenial),
we suggest using `pyenv <https://github.com/pyenv/pyenv>`_ to manage newer versions of Python.
Ubuntu 16.04 defaults to version 3.5 which is not enough.

In Debian, Python3 and pip can be installed in most cases as:

.. code-block:: shell

   sudo apt-get install python3 python3-pip

On other platforms, consult your system's documentation to install Python.

----------------------
Install cincan-command
----------------------

"""""""""""""""""""
Global installation
"""""""""""""""""""

The ``cincan`` command can be installed globally using pip for Python 3:

.. code-block:: shell

   sudo pip3 install cincan-command

If you invoke the pip installation with ``sudo`` and without ``--user`` flag (if you are OK with that),
the ``cincan`` command should be added to your path automatically and installed system-wide.

"""""""""""""""""
User installation
"""""""""""""""""

If you don't want to install packages globally, you can install the package for the current user:

.. code-block:: shell

   pip3 install --user cincan-command

This will install the package for the current user. However, it is possible that these packages are not in path.
You can add user-specific binaries into path for the current session with:

.. code-block:: shell

   export PATH=$PATH:$HOME/.local/bin

To add it permanently, append it into ``~/.bashrc`` file with your favorite text editor.
Note that this can depend on what kind of shell you are using.

""""""""""
virtualenv
""""""""""

You can alternatively use `virtualenv` not to touch your system Python environment:

.. code-block:: shell

    sudo apt-get install virtualenv
    virtualenv -p /usr/bin/python3 --system-site-packages cincan-env
    source cincan-env/bin/activate
    pip3 install cincan-command

On later Python versions, ``venv`` module should be automatically included and is easier to use:

.. code-block:: shell

    python3 -m venv cincan-env
    source cincan-env/bin/activate
    pip3 install cincan-command


.. Hide level 2 heading from table of contents
.. raw:: html

   <h2>Ready to Rock</h2>

Once we have successfully installed all the required packages, we can start the usage!

.. code-block:: shell

   cincan list

Should give a list for all stable `tools <https://gitlab.com/CinCan/tools>`_ dockerized in the **CinCan** project.

**Note**: Make sure ``Docker`` is running when you use the ``cincan`` command.

See more examples in the :ref:`commands` section.
