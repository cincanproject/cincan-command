import logging
import pytest
from unittest import mock
from cincan.frontend import ToolImage
from cincan.configuration import Configuration

DEFAULT_IMAGE = "quay.io/cincan/test"
DEFAULT_STABLE_TAG = Configuration().default_stable_tag
DEFAULT_DEV_TAG = Configuration().default_dev_tag


def test_image_pull_no_default_tag(caplog):
    caplog.set_level(logging.INFO)
    # cincan/test image has only 'dev' tag
    tool = ToolImage(image=DEFAULT_IMAGE, pull=True, rm=False)
    logs = [l.message for l in caplog.records]
    pull_msgs = [
        f"pulling image with tag '{DEFAULT_STABLE_TAG}'...",
        f"Tag 'latest' not found. Trying development tag '{DEFAULT_DEV_TAG}' instead."
    ]
    # Ignore version check messages, get two first
    assert logs[:len(pull_msgs)] == pull_msgs


def test_pull_not_cincan(caplog):
    caplog.set_level(logging.INFO)
    # Busybox is not 'cincan' image, pulling normally
    tool = ToolImage(image="busybox", pull=True, rm=False)
    pull_msgs = [
        "pulling image with tag 'latest'...",
    ]
    logs = [l.message for l in caplog.records]
    assert logs == pull_msgs


def test_pull_not_cincan_tag_not_found(caplog):
    caplog.set_level(logging.INFO)
    # Busybox is not 'cincan' image, pulling non existing tag
    with pytest.raises(SystemExit) as ex:
        tool = ToolImage(image="busybox:cincan", pull=True, rm=False)
    assert ex.type == SystemExit
    assert ex.value.code == 1
    pull_msgs = [
        "pulling image with tag 'cincan'...",
        "Tag 'cincan' not found. Is it typed correctly?"
    ]
    logs = [l.message for l in caplog.records]
    assert logs == pull_msgs


def test_pull_tag_not_found(caplog):
    caplog.set_level(logging.INFO)
    # Pulling non-existing tag from cincan tool
    with pytest.raises(SystemExit) as ex:
        tool = ToolImage(image=f"{DEFAULT_IMAGE}:not_found", pull=True, rm=False)
    assert ex.type == SystemExit
    assert ex.value.code == 1
    pull_msgs = [
        "pulling image with tag 'not_found'...",
        "Tag 'not_found' not found. Is it typed correctly?"
    ]
    logs = [l.message for l in caplog.records]
    assert logs[:len(pull_msgs)] == pull_msgs
    caplog.clear()


def test_pull_repository_not_found(caplog):
    caplog.set_level(logging.INFO)

    # Pulling from non-existing repository 'cincann'
    with pytest.raises(SystemExit) as ex:
        tool = ToolImage(image="cincann/test_not_found", pull=True, rm=False)
    assert ex.type == SystemExit
    assert ex.value.code == 1
    pull_msgs = [
        "pulling image with tag 'latest'...",
        "Repository not found or no access into it. Is it typed correctly?"
    ]
    logs = [l.message for l in caplog.records]
    assert logs == pull_msgs


def test_pull_no_default_tags_no_credentials(caplog):
    """
    Test for pulling non-existing 'cincan' image
    Method behaves differently whether credentials for 'cincan' is found
    (if Docker Hub credentials are found, it attempts to pull both tags)
    """
    # Mock contents of ~/.docker/config.json to have no credentials
    read_data = "{}"
    mock_open = mock.mock_open(read_data=read_data)
    caplog.set_level(logging.INFO)

    # Mock with no credentials/custom config
    with mock.patch("builtins.open", mock_open):
        # Pulling 'cincan' image without default development or stable tag
        with pytest.raises(SystemExit) as ex:
            tool = ToolImage(image="quay.io/cincan/test_not_found", pull=True, rm=False)
    assert ex.type == SystemExit
    assert ex.value.code == 1
    pull_msg = '500 Server Error: Internal Server Error ' \
               '("unauthorized: access to the requested resource is not authorized")'
    logs = [l.message for l in caplog.records]
    assert pull_msg in logs


def test_batch_option_pull(caplog):
    """Test --batch option to disable some properties (version check, pull-progress bar"""

    caplog.set_level(logging.INFO)
    tool = ToolImage(image=f"{DEFAULT_IMAGE}:{DEFAULT_DEV_TAG}", pull=True, rm=False, batch=True)
    pull_msgs = [
        f"pulling image with tag '{DEFAULT_DEV_TAG}'...",
    ]
    logs = [l.message for l in caplog.records]
    assert logs == pull_msgs
    tool = ToolImage(image=f"cincan/test:{DEFAULT_DEV_TAG}", pull=True, rm=False, batch=False)
    msg = f"No version information available for {DEFAULT_IMAGE}\n"
    logs = [l.message for l in caplog.records]
    assert msg in logs


def test_pull_cincan_tool_from_dockerhub(caplog):
    """Pull cincan image from Docker Hub -> Redirect into Quay expected"""

    caplog.set_level(logging.INFO)
    tool = ToolImage(image=f"cincan/test:{DEFAULT_DEV_TAG}", pull=True, rm=False, batch=True)
    assert f"{DEFAULT_IMAGE}:{DEFAULT_DEV_TAG}" in tool.image.tags
