.. _installation:

============
Installation
============

.. toctree::
   :caption: Table of Contents
   :maxdepth: 4

	
As prerequisite you must install ``Docker`` **18.09+** for running the tools,
and ``Python`` **3.6** and ``pip`` Python package management program for the command program.

--------------
Install Docker
--------------

If you are running Ubuntu 18.04 or Debian 10, you can install Docker from the package repositories:

.. code-block:: console

   sudo apt-get docker.io

One liner for installing the Docker for almost any system, if you don't have Debian:

.. code-block:: console

   curl -fsSL https://get.docker.com/ | sh


Add yourself to the `docker` group to communicate with the local installation of Docker:

.. code-block:: console

   sudo usermod -aG docker $USER
   newgrp docker

Optionally, you can then test your installation running the Docker `hello-world` container:

.. code-block:: console

    docker run hello-world


If you are encountering some problems, see the `official documentation for installing Docker. <https://docs.docker.com/engine/install/>`_

----------------------
Install Python (>=3.6)
----------------------

Newer distros should have python 3.6 or newer installed. If you are running something older (like Ubuntu 16.04),
we suggest using `pyenv <https://github.com/pyenv/pyenv>`_ to manage newer versions of Python.

"""""""""""""""""""
Global installation
"""""""""""""""""""

The ``cincan`` command program can be installed globally using pip for Python 3:

.. code-block:: console

   sudo pip3 install cincan-command

**If you invoke the pip installation with `sudo` and without `--user` flag (if you are OK with that) the command `cincan`
should be added to your path automatically and installed in system wide.**

"""""""""""""""""
User installation
"""""""""""""""""

If you don't want to install packages globally, you can install the package for the current user:

.. code-block:: console

   pip3 install cincan-command --user

This will install package for current user. However, it is possible that these packages are not in path.
You can add user-specific binaries into path for current session with:

.. code-block:: console

   export PATH=$PATH:$HOME/.local/bin

To add it permanently, append it into `~/.bashrc`  file with your favorite text editor. Note that this can depend on what kind of shell you are using.

""""""""""
virtualenv
""""""""""

You can also use `virtualenv` not to touch your system Python environment:

.. code-block:: console

    sudo apt-get install virtualenv
    virtualenv -p /usr/bin/python3 --system-site-packages cincan-env
    source cincan-env/bin/activate
    pip3 install cincan-command

On later Python versions, ``venv`` module should be automatically included and is easier to use:


.. code-block:: console

    python3 -m venv cincan-env
    source cincan-env/bin/activate
    pip3 install cincan-command
