import pathlib
import tarfile
import time
from typing import List
import io
import pytest
import subprocess
from cincan.file_tool import FileMatcher
from cincan.frontend import ToolImage
from .utils import prepare_work_dir


def test_tar_input_log():
    tool = ToolImage(image='busybox', rm=False)
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


def test_output_to_tar():
    tool = ToolImage(image='busybox', rm=False)
    work_dir = prepare_work_dir('_test', ['ab.zip'])
    tool.output_tar = (work_dir / 'output.tar').as_posix()
    log = tool.run(['unzip', '-d', '_test', '_test/ab.zip'])

    with tarfile.open(work_dir / 'output.tar') as tarball:
        tarball.extractall(path='_test')
    assert (work_dir / "_test/source-a.txt").open().read() == 'Source A\n'
    assert (work_dir / "_test/source-b.txt").open().read() == 'Source B\n'

    assert tool.upload_files == ['_test', '_test/ab.zip']
    assert tool.download_files == ['_test/source-a.txt', '_test/source-b.txt']


def test_explicit_in_out_files():
    tool = ToolImage(image='busybox', rm=False)
    work_dir = prepare_work_dir('_test', ['ab.zip', 'empty.file'])
    tool.input_filters = FileMatcher.parse(['_test/ab.zip', '_test/empty.file'])  # NOTHING can pass this filter!
    tool.output_filters = FileMatcher.parse(['_test/source-b.txt'])

    tool.run_get_string(['unzip', '-d', '_test', '_test/ab.zip'])
    assert tool.upload_files == []
    assert tool.download_files == []


