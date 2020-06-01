import logging
import pytest
from asyncio import coroutine
from unittest import mock
from cincan.frontend import ToolImage
from cincan.configuration import Configuration
from copy import deepcopy

TEST_IMAGE = "cincan/test:dev"
TEST_IMAGE_NAME = TEST_IMAGE.rsplit(":", 1)[0]
TEST_IMAGE_TAG = TEST_IMAGE.rsplit(":", 1)[1]
DEFAULT_STABLE_TAG = Configuration().default_stable_tag

VERSION_DATA = {"name": TEST_IMAGE_NAME,
                "versions": {
                    "local": {
                        "version": "1.0",
                        "tags": [f"{TEST_IMAGE_NAME}:{DEFAULT_STABLE_TAG}", ]
                    },
                    "remote": {
                        "version": "1.0",
                        "tags": [DEFAULT_STABLE_TAG]
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
    """Local tool is up to date"""
    caplog.set_level(logging.INFO)

    def coroutine_func():
        """Mock coroutine function to have custom result"""
        version_data_copy = deepcopy(VERSION_DATA)
        version_data_copy["versions"]["remote"]["tags"] = ["latest", TEST_IMAGE_TAG]
        coroutine_result = mock.Mock(name="CoroutineResult", return_value=version_data_copy)
        mocked_funk = mock.Mock(name="CoroutineFunction", side_effect=coroutine(coroutine_result))
        mocked_funk.coroutine_result = coroutine_result
        return mocked_funk

    with mock.patch("cincanregistry.ToolRegistry.get_version_by_image_id", return_value="1.0") as mock_ver_id:
        with mock.patch("cincanregistry.ToolRegistry.list_versions", side_effect=coroutine_func()) as mock_list:
            tool = ToolImage(image=TEST_IMAGE, pull=True, rm=False)
            mock_ver_id.assert_called()
            mock_list.assert_called_with(TEST_IMAGE_NAME, only_updates=False)
    pull_msgs = [
        "Your tool is up-to-date with remote. Current version: 1.0\n"
    ]
    logs = [l.message for l in caplog.records]
    assert logs[1:] == pull_msgs


def test_image_version_no_info(caplog):
    caplog.set_level(logging.INFO)

    def coroutine_func():
        """Mock coroutine function to have custom result"""
        coroutine_result = mock.Mock(name="CoroutineResult", return_value={})
        mocked_funk = mock.Mock(name="CoroutineFunction", side_effect=coroutine(coroutine_result))
        mocked_funk.coroutine_result = coroutine_result
        return mocked_funk

    with mock.patch("cincanregistry.ToolRegistry.get_version_by_image_id", return_value="1.0") as mock_ver_id:
        with mock.patch("cincanregistry.ToolRegistry.list_versions", side_effect=coroutine_func()) as mock_list:
            tool = ToolImage(image=TEST_IMAGE, pull=True, rm=False)
            mock_ver_id.assert_called()
            mock_list.assert_called_with(TEST_IMAGE_NAME, only_updates=False)
    pull_msgs = [
        f"No version information available for {TEST_IMAGE_NAME}\n"
    ]
    logs = [l.message for l in caplog.records]
    assert logs[1:] == pull_msgs


def test_image_version_local_old_tag(caplog):
    """Used image outdated"""
    caplog.set_level(logging.INFO)

    def coroutine_func():
        """Mock coroutine function to have custom result"""
        coroutine_result = mock.Mock(name="CoroutineResult", return_value=VERSION_DATA)
        mocked_funk = mock.Mock(name="CoroutineFunction", side_effect=coroutine(coroutine_result))
        mocked_funk.coroutine_result = coroutine_result
        return mocked_funk

    with mock.patch("cincanregistry.ToolRegistry.get_version_by_image_id", return_value="0.9"):
        with mock.patch("cincanregistry.ToolRegistry.list_versions", side_effect=coroutine_func()) as mock_list:
            tool = ToolImage(image=TEST_IMAGE, pull=True, rm=False)
    pull_msgs = [
        "You are not using latest locally available version: (0.9 vs 1.0) Latest is "
        f"available with tags '{TEST_IMAGE_NAME}:{DEFAULT_STABLE_TAG}'",
        "Latest local tool is up-to-date with remote. Latest local version: 1.0"
    ]
    logs = [l.message for l in caplog.records]
    assert logs[1:] == pull_msgs


def test_image_version_local_outdated(caplog):
    """Local image outdated"""
    caplog.set_level(logging.INFO)

    def coroutine_func():
        """Mock coroutine function to have custom result"""
        version_data_copy = deepcopy(VERSION_DATA)
        version_data_copy["versions"]["remote"]["version"] = "1.1"
        version_data_copy["updates"]["local"] = True
        coroutine_result = mock.Mock(name="CoroutineResult", return_value=version_data_copy)
        mocked_funk = mock.Mock(name="CoroutineFunction", side_effect=coroutine(coroutine_result))
        mocked_funk.coroutine_result = coroutine_result
        return mocked_funk

    with mock.patch("cincanregistry.ToolRegistry.get_version_by_image_id", return_value="1.0"):
        with mock.patch("cincanregistry.ToolRegistry.list_versions", side_effect=coroutine_func()) as mock_list:
            tool = ToolImage(image=TEST_IMAGE, pull=True, rm=False)
    pull_msgs = [
        "Update available in remote: (1.0 vs. 1.1)"
        f"\nUse 'docker pull {TEST_IMAGE_NAME}:{DEFAULT_STABLE_TAG}' to update."
    ]
    logs = [l.message for l in caplog.records]
    assert logs[1:] == pull_msgs


def test_image_version_remote_outdated(caplog):
    """Remote image outdated"""
    caplog.set_level(logging.INFO)

    def coroutine_func():
        """Mock coroutine function to have custom result"""
        version_data_copy = deepcopy(VERSION_DATA)
        version_data_copy["versions"]["origin"]["version"] = "1.1"
        version_data_copy["updates"]["remote"] = True
        coroutine_result = mock.Mock(name="CoroutineResult", return_value=version_data_copy)
        mocked_funk = mock.Mock(name="CoroutineFunction", side_effect=coroutine(coroutine_result))
        mocked_funk.coroutine_result = coroutine_result
        return mocked_funk

    with mock.patch("cincanregistry.ToolRegistry.get_version_by_image_id", return_value="1.0"):
        with mock.patch("cincanregistry.ToolRegistry.list_versions", side_effect=coroutine_func()) as mock_list:
            tool = ToolImage(image=TEST_IMAGE, pull=True, rm=False)
    pull_msgs = [
        "Your tool is up-to-date with remote. Current version: 1.0\n",
        "Remote is not up-to-date with origin (1.0 vs. 1.1) in 'GitHub'"
    ]
    logs = [l.message for l in caplog.records]
    assert logs[1:] == pull_msgs


def test_image_version_new_dev_version(caplog):
    """Remote image outdated - new dev version"""
    caplog.set_level(logging.INFO)

    def coroutine_func():
        """Mock coroutine function to have custom result"""
        version_data_copy = deepcopy(VERSION_DATA)
        version_data_copy["versions"]["remote"]["tags"] = ["dev"]
        version_data_copy["versions"]["remote"]["version"] = "1.1"
        version_data_copy["updates"]["local"] = True
        coroutine_result = mock.Mock(name="CoroutineResult", return_value=version_data_copy)
        mocked_funk = mock.Mock(name="CoroutineFunction", side_effect=coroutine(coroutine_result))
        mocked_funk.coroutine_result = coroutine_result
        return mocked_funk

    with mock.patch("cincanregistry.ToolRegistry.get_version_by_image_id", return_value="1.0"):
        with mock.patch("cincanregistry.ToolRegistry.list_versions", side_effect=coroutine_func()) as mock_list:
            tool = ToolImage(image=TEST_IMAGE, pull=True, rm=False)
    pull_msgs = [
        f"Newer development version available in remote: 1.1 with tags 'dev'"
    ]
    logs = [l.message for l in caplog.records]
    assert logs[1:] == pull_msgs
