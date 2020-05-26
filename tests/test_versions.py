import logging
import pytest
from unittest import mock
from cincan.frontend import ToolImage
from copy import deepcopy

VERSION_DATA = {"name": "cincan/test",
                "versions": {
                    "local": {
                        "version": "1.0",
                        "tags": ["cincan/test:latest-stable", ]
                    },
                    "remote": {
                        "version": "1.0",
                        "tags": ["latest-stable"]
                    },
                    "origin": {
                        "version": "1.0",
                        "details": {
                            "provider": "GitHub"
                        }
                    }
                },
                "other": [],
                "updates": {
                    "local": False,
                    "remote": False
                }
                }


def test_image_version_up_to_date(caplog):
    caplog.set_level(logging.INFO)
    version_data_copy = deepcopy(VERSION_DATA)
    version_data_copy["versions"]["remote"]["tags"] = ["latest", "latest-stable"]
    # Local tool is up to date
    with mock.patch("cincanregistry.ToolRegistry.get_version_by_image_id", return_value="1.0") as mock_ver_id:
        with mock.patch("cincanregistry.ToolRegistry.list_versions", return_value=version_data_copy) as mock_list:
            tool = ToolImage(image="cincan/test:latest", pull=True, rm=False)
            mock_ver_id.assert_called()
            mock_list.assert_called_with("cincan/test", only_updates=False)
    pull_msgs = [
        "pulling image with tag 'latest'...",
        "Your tool is up-to-date with remote. Current version: 1.0\n"
    ]
    logs = [l.message for l in caplog.records]
    assert logs == pull_msgs


def test_image_version_up_to_date_different_tag(caplog):
    caplog.set_level(logging.INFO)
    # Local tool is up to date
    with mock.patch("cincanregistry.ToolRegistry.get_version_by_image_id", return_value="1.0") as mock_ver_id:
        with mock.patch("cincanregistry.ToolRegistry.list_versions", return_value=VERSION_DATA) as mock_list:
            tool = ToolImage(image="cincan/test:latest", pull=True, rm=False)
            mock_ver_id.assert_called()
            mock_list.assert_called_with("cincan/test", only_updates=False)
    pull_msgs = [
        "pulling image with tag 'latest'...",
        "Latest local tool is up-to-date with remote. (1.0 vs. 1.0)"
        f" Unable to compare tags. Custom image?"
    ]
    logs = [l.message for l in caplog.records]
    assert logs == pull_msgs


def test_image_version_local_old_tag(caplog):
    caplog.set_level(logging.INFO)
    # Used image outdated
    with mock.patch("cincanregistry.ToolRegistry.get_version_by_image_id", return_value="0.9"):
        with mock.patch("cincanregistry.ToolRegistry.list_versions", return_value=VERSION_DATA) as mock_list:
            tool = ToolImage(image="cincan/test:latest", pull=True, rm=False)
    pull_msgs = [
        "pulling image with tag 'latest'...",
        "You are not using latest locally available version: (0.9 vs 1.0) Latest is "
        "available with tags 'cincan/test:latest-stable'",
        "Latest local tool is up-to-date with remote. (1.0 vs. 1.0) Unable to compare tags. Custom image?"
    ]
    logs = [l.message for l in caplog.records]
    assert logs == pull_msgs


def test_image_version_local_outdated(caplog):
    caplog.set_level(logging.INFO)
    # Remote image outdated
    version_data_copy = deepcopy(VERSION_DATA)
    version_data_copy["versions"]["remote"]["version"] = "1.1"
    version_data_copy["updates"]["local"] = True
    with mock.patch("cincanregistry.ToolRegistry.get_version_by_image_id", return_value="1.0"):
        with mock.patch("cincanregistry.ToolRegistry.list_versions", return_value=version_data_copy) as mock_list:
            tool = ToolImage(image="cincan/test:latest", pull=True, rm=False)
    pull_msgs = [
        "pulling image with tag 'latest'...",
        "Update available in remote: (1.0 vs. 1.1)"
        "\nUse 'docker pull cincan/test:latest-stable' to update."
    ]
    logs = [l.message for l in caplog.records]
    assert logs == pull_msgs


def test_image_version_remote_outdated(caplog):
    caplog.set_level(logging.INFO)
    # Remote image outdated
    version_data_copy = deepcopy(VERSION_DATA)
    version_data_copy["versions"]["remote"]["tags"] = ["latest", "latest-stable"]
    version_data_copy["versions"]["origin"]["version"] = "1.1"
    version_data_copy["updates"]["remote"] = True
    with mock.patch("cincanregistry.ToolRegistry.get_version_by_image_id", return_value="1.0"):
        with mock.patch("cincanregistry.ToolRegistry.list_versions", return_value=version_data_copy) as mock_list:
            tool = ToolImage(image="cincan/test:latest", pull=True, rm=False)
    pull_msgs = [
        "pulling image with tag 'latest'...",
        "Your tool is up-to-date with remote. Current version: 1.0\n",
        "Remote is not up-to-date with origin (1.0 vs. 1.1) in 'GitHub'"
    ]
    logs = [l.message for l in caplog.records]
    assert logs == pull_msgs


def test_image_version_new_dev_version(caplog):
    caplog.set_level(logging.INFO)
    # Remote image outdated
    version_data_copy = deepcopy(VERSION_DATA)
    version_data_copy["versions"]["remote"]["tags"] = ["dev"]
    version_data_copy["versions"]["remote"]["version"] = "1.1"
    version_data_copy["updates"]["local"] = True
    with mock.patch("cincanregistry.ToolRegistry.get_version_by_image_id", return_value="1.0"):
        with mock.patch("cincanregistry.ToolRegistry.list_versions", return_value=version_data_copy) as mock_list:
            tool = ToolImage(image="cincan/test:latest", pull=True, rm=False)
    pull_msgs = [
        "pulling image with tag 'latest'...",
        "Newer development version available in remote: 1.1 with tags 'dev'"
    ]
    logs = [l.message for l in caplog.records]
    assert logs == pull_msgs