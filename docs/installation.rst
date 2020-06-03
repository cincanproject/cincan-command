.. _installation:

============
Installation
============

.. toctree::
   :caption: Table of Contents
   :maxdepth: 3

	
As prerequisite you must install ``Docker`` **18.09+** for running the tools,
and ``Python`` **3.6+** and ``pip`` Python package management program for the command program.

*Docker below version 18.09 has not been tested,* so there might be hope that it works.

--------------
Install Docker (>=18.09)
--------------

If you are running Ubuntu 18.04 or Debian 10, you can install Docker from the package repositories:

.. code-block:: shell

   sudo apt-get docker.io

One liner for installing the Docker for almost any system, if you don't have Debian:

.. code-block:: shell

   curl -fsSL https://get.docker.com/ | sh


Add yourself to the `docker` group to communicate with the local installation of Docker:

.. code-block:: shell

   sudo usermod -aG docker $USER
   newgrp docker

Optionally, you can then test your installation running the Docker `hello-world` container:

.. code-block:: shell

    docker run hello-world


If you are encountering some problems, see the `official documentation for installing Docker. <https://docs.docker.com/engine/install/>`_

----------------------
Install Python (>=3.6)
----------------------

Newer distributions should have Python 3.6 or newer installed. 
If you are running something older (like Ubuntu 16.04 Xenial),
we suggest using `pyenv <https://github.com/pyenv/pyenv>`_ to manage newer versions of Python. 
Ubuntu 16.04 defaults to version 3.5 which is not enough.

In Debian, Python3 and pip can be installed in the most cases as:

.. code-block:: shell

   sudo apt-get install python3 python3-pip

On other platforms, consult your systems documentation to install Python.

----------------------
Install cincan-command
----------------------

"""""""""""""""""""
Global installation
"""""""""""""""""""

The ``cincan`` command program can be installed globally using pip for Python 3:

.. code-block:: shell

   sudo pip3 install cincan-command

If you invoke the pip installation with ``sudo`` and without ``--user`` flag (if you are OK with that) the command ``cincan``
should be added to your path automatically and installed in system wide.

"""""""""""""""""
User installation
"""""""""""""""""

If you don't want to install packages globally, you can install the package for the current user:

.. code-block:: shell

   pip3 install cincan-command --user

This will install package for current user. However, it is possible that these packages are not in path.
You can add user-specific binaries into path for current session with:

.. code-block:: shell

   export PATH=$PATH:$HOME/.local/bin

To add it permanently, append it into ``~/.bashrc``  file with your favorite text editor. 
Note that this can depend on what kind of shell you are using.

""""""""""
virtualenv
""""""""""

You can also use `virtualenv` not to touch your system Python environment:

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

"""""""""""""
Ready to Rock
"""""""""""""

Once we have successfully installed the required packages, we can start the usage!

.. code-block:: shell

   cincan list

Should give a list for all stable **cincan** tools.