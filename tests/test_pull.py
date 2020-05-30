import logging
import pytest
from cincan.frontend import ToolImage


def test_image_pull_no_default_tag(caplog):
    caplog.set_level(logging.INFO)
    # cincan/test image has only 'latest' tag
    tool = ToolImage(image="cincan/test", pull=True, rm=False)
    logs = [l.message for l in caplog.records]
    pull_msgs = [
        "pulling image with tag 'latest-stable'...",
        "Tag 'latest-stable' not found. Trying 'latest' instead."
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


def test_pull_tag_not_found(caplog):
    caplog.set_level(logging.INFO)
    # Pulling non-existing tag
    with pytest.raises(SystemExit) as ex:
        tool = ToolImage(image="cincan/test:not_found", pull=True, rm=False)
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

# def test_pull_no_defaul_tags(caplog):
    # caplog.set_level(logging.INFO)
    # CI has probably different Docker version, not working similarly compared to local
    # Pulling 'cincan' image without 'latest-stable' or 'latest' tag
    # with pytest.raises(SystemExit) as ex:
    #     tool = ToolImage(image="cincan/test_not_found", pull=True, rm=False)
    # assert ex.type == SystemExit
    # assert ex.value.code == 1
    # pull_msgs = [
    #     "pulling image with tag 'latest-stable'...",
    #     "Tag 'latest-stable' not found. Trying 'latest' instead.",
    #     "'latest-stable' or 'latest' tag not found for image cincan/test_not_found locally or remotely."
    # ]
    # logs = [l.message for l in caplog.records]
    # assert logs == pull_msgs
