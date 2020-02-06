import pathlib
import tarfile
import time
import os
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
    out = tool.run_get_string(['sh', '-c', f'cat _test/.cincanignore > .cincanignore; touch .test'])
    assert not pathlib.Path(".test").is_file()
    # check that .cincanignore is ignored as well
    assert not pathlib.Path(".cincanignore").is_file()

    # No ignore file
    out = tool.run_get_string(['sh', '-c', f'touch .test'])
    assert pathlib.Path(".test").is_file()
    os.remove(".test")

    # File `.test` is not ignored by .cincanignore (path is different) # Using tmp directory here and from this
    out = tool.run_get_string(['sh', '-c', f'touch {relative_outdir}/.test'])
    assert pathlib.Path(d / ".test").is_file()
    os.remove(pathlib.Path(d / ".test"))

    # File `.test` is not ignored by .cincanignore - --no-defaults argument used
    tool.no_defaults = True
    out = tool.run_get_string(['sh', '-c', f'echo "{relative_outdir}/.test" >> .cincanignore; touch {relative_outdir}/.test'])
    assert pathlib.Path(d / ".test").is_file()
    # Ignore file is brought as well
    assert pathlib.Path(".cincanignore").is_file()
    os.remove(pathlib.Path(d / ".test"))
    os.remove(pathlib.Path(".cincanignore"))
    tool.no_defaults = False

    # File `.test` is not ignored by .cincanignore - --outfilter overrides
    tool.output_filters = FileMatcher.parse([f"{relative_outdir}/.test"])
    out = tool.run_get_string(['sh', '-c', f'echo "{relative_outdir}/.test" >> .cincanignore; touch {relative_outdir}/.test'])
    assert pathlib.Path(d / ".test").is_file()
    os.remove(pathlib.Path(d / ".test"))

    # File `.test` is ignored by .cincanignore - --outfilter used for wrong file
    tool.output_filters = FileMatcher.parse([f"{relative_outdir}/.testt"])
    out = tool.run_get_string(['sh', '-c', f'echo "{relative_outdir}/.test" >> .cincanignore; touch {relative_outdir}/.test'])
    assert not pathlib.Path(d / ".test").is_file()

    # File `.test` is not ignored by .cincanignore because --no-defaults option --outfilter ignores other file '.testagain'
    tool.no_defaults = True
    tool.output_filters = FileMatcher.parse([f"^{relative_outdir}/.testagain"])
    out = tool.run_get_string(['sh', '-c', f' echo "{relative_outdir}/.test" >> .cincanignore; touch {relative_outdir}/.test; touch {relative_outdir}/.testagain'])

    assert pathlib.Path(".cincanignore").is_file()
    assert pathlib.Path(d / ".test").is_file()
    assert not pathlib.Path(d / ".testagain").is_file()
    os.remove(pathlib.Path(".cincanignore"))