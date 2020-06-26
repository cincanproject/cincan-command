[![pipeline status](https://gitlab.com/CinCan/cincan-command/badges/master/pipeline.svg)](https://gitlab.com/CinCan/cincan-command/commits/master)
[![coverage report](https://gitlab.com/CinCan/cincan-command/badges/master/coverage.svg)](https://gitlab.com/CinCan/cincan-command/commits/master)

# CinCan Command

CinCan is a command-line interface for running security analysis tools conveniently in Docker containers.

Complete documentation is available at [CinCan Documentation](https://cincan.gitlab.io/cincan-command/).

## Features
 - Install and update security analysis tools without dependency hell
 - Repeatable command-line experience
 - Community support

CinCan collects the best [security analysis tools](https://gitlab.com/CinCan/tools) around the web and provides them as containerized Docker images. You can use CinCan's tools as if they were installed locally because CinCan automates the process of installing and updating the tools and removes the need to manually maintain conflicting dependencies. Learn from [our blog](https://cincan.io/blog/) how CinCan improves the command-line experience by combining various tools for repeatable and high-quality security analysis. If you know a tool that is not available in CinCan, please [contribute](https://gitlab.com/CinCan/tools/-/blob/master/CONTRIBUTING.md) to the project!

## Supported platforms

The `cincan` command should run on all fairly modern Linux distributions. Partial support for macOS is available - tested to work with macOS Catalina. On Windows, `cincan` **does not work**, unfortunately.

## Installation

As a prerequisite, you must have `Docker` **18.09+** installed for running the tools, and `Python` **3.6+** and `pip` Python package manager to install the `cincan` command.

Install cincan via pip:

    % pip install --user cincan-command

You can verify that the installation works by running:

    % cincan list

If all goes well, you should get a list of the [latest stable tools](https://gitlab.com/CinCan/tools) dockerized in the CinCan project. The first time running this may take a while as it will fetch information about the tools and cache it locally.

Use the [installation instructions in the CinCan Documentation](https://cincan.gitlab.io/cincan-command/installation.html) for additional help.
