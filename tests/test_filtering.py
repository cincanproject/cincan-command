import pathlib
import tarfile
import time
from typing import List
import pytest
from cincan.file_tool import FileMatcher
from cincan.frontend import ToolImage
from .conftest import prepare_work_dir


def test_input_filtering(tool):
    work_dir = prepare_work_dir('_test', ['source-a.txt', 'ab.zip', 'source-b.txt'])
    out = tool.run_get_string(['ls', '-1', '_test'])
    assert out == 'ab.zip\nsource-a.txt\nsource-b.txt\n'
    assert tool.upload_files == ['_test', '_test/ab.zip', '_test/source-a.txt', '_test/source-b.txt']
    assert tool.download_files == []

    tool.input_filters = FileMatcher.parse(["_test*.zip"])
    work_dir = prepare_work_dir('_test', ['source-a.txt', 'ab.zip', 'source-b.txt'])
    out = tool.run_get_string(['ls', '-1', '_test'])
    assert out == 'ab.zip\n'
    assert tool.upload_files == ['_test/ab.zip']
    assert tool.download_files == []

    tool.input_filters = FileMatcher.parse(["_test*.txt"])
    work_dir = prepare_work_dir('_test', ['source-a.txt', 'ab.zip', 'source-b.txt'])
    out = tool.run_get_string(['ls', '-1', '_test'])
    assert out == 'source-a.txt\nsource-b.txt\n'
    assert tool.upload_files == ['_test/source-a.txt', '_test/source-b.txt']
    assert tool.download_files == []

    tool.input_filters = FileMatcher.parse(["^*.txt"])
    work_dir = prepare_work_dir('_test', ['source-a.txt', 'ab.zip', 'source-b.txt'])
    out = tool.run_get_string(['ls', '-1', '_test'])
    assert out == 'ab.zip\n'
    assert tool.upload_files == ['_test', '_test/ab.zip']
    assert tool.download_files == []

def test_explicit_in_out_files(tool):
    work_dir = prepare_work_dir('_test', ['ab.zip', 'empty.file'])
    tool.input_filters = FileMatcher.parse(['_test/ab.zip', '_test/empty.file'])  # NOTHING can pass this filter!
    tool.output_filters = FileMatcher.parse(['_test/source-b.txt'])

    tool.run_get_string(['unzip', '-d', '_test', '_test/ab.zip'])
    assert tool.upload_files == []
    assert tool.download_files == []

def test_container_specific_ignore(tmp_path, tool):
    """
    Method for testing wheather .cincanignore marks files not to be downloaded from the container
    """
    d = tmp_path / "tcs"
    d.mkdir()
    work_dir = prepare_work_dir('_test', ['.cincanignore'])
    relative_outdir = d.relative_to(pathlib.Path.cwd())
    # File `.test` is ignored by .cincanignore
    out = tool.run_get_string(['sh', '-c', f'cat samples/.cincanignore > .cincanignore; echo "{relative_outdir}/.test" >> .cincanignore;cat .cincanignore; touch {relative_outdir}/.test'])
    assert not pathlib.Path(d / ".test").is_file()

def test_container_specific_ignore_not_match(tmp_path, tool):
    """
    Test for not ignored file
    """
    d = tmp_path / "tcs"
    d.mkdir()
    work_dir = prepare_work_dir('_test', ['.cincanignore'])
    relative_outdir = d.relative_to(pathlib.Path.cwd())
    # File `.test` is ignored by .cincanignore
    out = tool.run_get_string(['sh', '-c', f'cat samples/.cincanignore > .cincanignore; cat .cincanignore; touch {relative_outdir}/.test'])
    assert pathlib.Path(d / ".test").is_file()