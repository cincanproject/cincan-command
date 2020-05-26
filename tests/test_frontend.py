import logging
import pathlib
import tarfile
import time
from typing import List
import io
import pytest
import subprocess
from cincan.file_tool import FileMatcher
from cincan.frontend import ToolImage
from .conftest import prepare_work_dir
from unittest import mock
import cincanregistry


def test_run_get_string(tool):
    out = tool.run_get_string(['echo', 'Hello'])
    assert out == 'Hello\n'

    out = tool.run_get_string(['echxo', 'Hello'])
    assert 'OCI runtime exec failed: exec failed:' in out


def test_magic_file_io(tool):
    work_dir = prepare_work_dir('_test', ['source-a.txt'])
    out = tool.run_get_string(['cat', '_test/source-a.txt'])
    assert out == 'Source A\n'
    assert tool.upload_files == ['_test/source-a.txt']
    assert tool.download_files == []

    work_dir = prepare_work_dir('_test', ['source-b.txt'])
    out = tool.run_get_string(['cat', '_test/source-b.txt'])
    assert out == 'Source B\n'
    assert tool.upload_files == ['_test/source-b.txt']
    assert tool.download_files == []

    work_dir = prepare_work_dir('_test', ['source-a.txt'])
    tool.run(["sh", "-c", '''cat _test/source-a.txt > _test/test_a.txt'''])
    assert tool.upload_files == ['_test/source-a.txt']
    assert tool.download_files == ['_test/test_a.txt']

    time.sleep(1.5)  # make sure file timestamp gets old
    tool.run(["sh", "-c", '''cat _test/source-a.txt > _test/test_a.txt'''])
    assert tool.upload_files == ['_test/source-a.txt', '_test/test_a.txt']
    assert tool.download_files == ['_test/test_a.txt']


def test_input_directory(tool):
    work_dir = prepare_work_dir('_test', ['source-b.txt', 'source-a.txt'])
    out = tool.run_get_string(['ls', '-1', '_test'])
    assert out == 'source-a.txt\nsource-b.txt\n'
    assert tool.upload_files == ['_test', '_test/source-a.txt', '_test/source-b.txt']
    assert tool.download_files == []


def test_output_mkdir(tool):
    work_dir = prepare_work_dir('_test', ['source-b.txt', 'source-a.txt'])
    tool.output_dirs = ['_test', '_test/a_test']
    out = tool.run_get_string(['ls', '-1', '_test'])
    assert out == 'a_test\n'
    assert tool.upload_files == ['_test', '_test/a_test']
    assert tool.download_files == ['_test/a_test']


def test_many_output_files(tool):
    work_dir = prepare_work_dir('_test', ['ab.zip'])
    tool.run_get_string(['unzip', '-d', '_test', '_test/ab.zip'])
    assert tool.upload_files == ['_test', '_test/ab.zip']
    assert tool.download_files == ['_test/source-a.txt', '_test/source-b.txt']


def test_log_stdout(tool):
    work_dir = prepare_work_dir('_test', ['ab.zip'])
    log = tool.run(['echo', 'abc'])
    assert tool.upload_files == []
    assert tool.download_files == []

    assert len(log.out_files) == 1
    assert log.out_files[0].path == pathlib.Path('/dev/stdout')
    assert log.out_files[0].digest == 'edeaaff3f1774ad2888673770c6d64097e391bc362d7d6fb34982ddf0efd18cb'


def test_log_entries(tool):
    work_dir = prepare_work_dir('_test', ['ab.zip'])
    log = tool.run(['unzip', '-d', '_test', '_test/ab.zip'])

    assert len(log.in_files) == 1
    assert log.in_files[0].path == pathlib.Path().cwd() / '_test/ab.zip'
    assert log.in_files[0].digest == 'b7514875bbb128f436a607a9a1b434d928cca9bb49b3608f58e25420e7ac827d'

    assert len(log.out_files) == 3
    assert log.out_files[0].path == pathlib.Path('/dev/stdout')
    assert log.out_files[0].digest == 'bf1844bc9dd9d1a3fca260f20f07b2560383e13a4537b65e7ea4304370d48d85'
    assert log.out_files[1].path == pathlib.Path().cwd() / '_test/source-a.txt'
    assert log.out_files[1].digest == '07a1a41dc6b0949c94b382890ce222005f8bf06a6bc9a2ad7d21fe577e17d2a3'
    assert log.out_files[2].path == pathlib.Path().cwd() / '_test/source-b.txt'
    assert log.out_files[2].digest == 'ad3b361a1df9bdcf159a68b122b3e21cfca69ccc13245a3df4acc996aa7414c5'


def test_output_to_tar(tool):
    work_dir = prepare_work_dir('_test', ['ab.zip'])
    tool.output_tar = (work_dir / 'output.tar').as_posix()
    log = tool.run(['unzip', '-d', '_test', '_test/ab.zip'])

    with tarfile.open(work_dir / 'output.tar') as tarball:
        tarball.extractall(path='_test')
    assert (work_dir / "_test/source-a.txt").open().read() == 'Source A\n'
    assert (work_dir / "_test/source-b.txt").open().read() == 'Source B\n'

    assert tool.upload_files == ['_test', '_test/ab.zip']
    assert tool.download_files == ['_test/source-a.txt', '_test/source-b.txt']


def test_tar_input_log(tool):
    work_dir = prepare_work_dir('_test', ['ab_zip.tar'])
    tool.input_tar = work_dir / 'ab_zip.tar'
    log = tool.run(['unzip', '-d', '_test', '_test/ab.zip'])

    assert len(log.in_files) == 1
    assert log.in_files[0].path == pathlib.Path().cwd() / '_test/ab.zip'
    assert log.in_files[0].digest == 'b7514875bbb128f436a607a9a1b434d928cca9bb49b3608f58e25420e7ac827d'

    assert len(log.out_files) == 3
    assert log.out_files[0].path == pathlib.Path('/dev/stdout')
    assert log.out_files[0].digest == 'bf1844bc9dd9d1a3fca260f20f07b2560383e13a4537b65e7ea4304370d48d85'
    assert log.out_files[1].path == pathlib.Path().cwd() / '_test/source-a.txt'
    assert log.out_files[1].digest == '07a1a41dc6b0949c94b382890ce222005f8bf06a6bc9a2ad7d21fe577e17d2a3'
    assert log.out_files[2].path == pathlib.Path().cwd() / '_test/source-b.txt'
    assert log.out_files[2].digest == 'ad3b361a1df9bdcf159a68b122b3e21cfca69ccc13245a3df4acc996aa7414c5'


def test_upload_file_from_dir(tool):
    # put in extra file, it should *not* get uploaded
    work_dir = prepare_work_dir('_test', ['source-a.txt', 'sub/source-c.txt'])
    tool.run_get_string(['echo', '_test/sub/source-c.txt'])
    assert tool.upload_files == ['_test/sub/source-c.txt']
    assert tool.download_files == []


def test_download_file_from_dir(tool):
    work_dir = prepare_work_dir('_test', ['sub/source-c.txt'])
    tool.run_get_string(['cp', '_test/sub/source-c.txt', '_test/sub.txt'])
    assert tool.upload_files == ['_test/sub/source-c.txt']
    assert tool.download_files == ['_test/sub.txt']


def test_download_prefix_files(tool):
    work_dir = prepare_work_dir('_test', [])
    tool.output_dirs = ['_test/fuzzed']
    r = tool.run(['sh', '-c', 'touch _test/fuzzed/a && touch _test/fuzzed/ab'])
    assert r.exit_code == 0
    assert tool.upload_files == ['_test/fuzzed']
    assert tool.download_files == ['_test/fuzzed/a', '_test/fuzzed/ab']


def test_colon_in_file_name(tool):
    work_dir = prepare_work_dir('_test', [])
    r = tool.run(['sh', '-c', 'echo Hello > "_test/file:0.txt"'])
    assert r.exit_code == 0
    assert tool.download_files == ['_test/file:0.txt']
    with open("_test/file:0.txt") as f:
        assert f.read() == 'Hello\n'


def test_interactive_mode():
    """
    Test interactive support with very simple commands by using subprocess
    It seems to impossible to test code by just by using functions, should split it more
    """
    process = subprocess.Popen(['python3', '-m', 'cincan', '-q', 'run', '-i', 'busybox', 'sh'], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    outs, errs = process.communicate(b'echo Hello, World!\n')
    assert outs == b"Hello, World!\n"
    assert errs == b""


def test_image_pull(caplog):
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
    caplog.clear()

    # Busybox is not 'cincan' image, pulling normally
    tool = ToolImage(image="busybox", pull=True, rm=False)
    pull_msgs = [
        "pulling image with tag 'latest'...",
    ]
    logs = [l.message for l in caplog.records]
    assert logs == pull_msgs
    caplog.clear()

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
    caplog.clear()

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

