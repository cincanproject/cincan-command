import pathlib

import pytest

from cincan.file_tool import FileResolver


def test_upload_file_detection():
    resolver = FileResolver(['README.md'], pathlib.Path())
    assert resolver.command_args == ['README.md']
    assert resolver.detect_upload_files() == [pathlib.Path('README.md')]

    resolver = FileResolver(['README.md5'], pathlib.Path())
    assert resolver.command_args == ['README.md5']
    assert resolver.detect_upload_files() == []

    resolver = FileResolver(['-f', 'README.md'], pathlib.Path())
    assert resolver.command_args == ['-f', 'README.md']
    assert resolver.detect_upload_files() == [pathlib.Path('README.md')]

    resolver = FileResolver(['-fREADME.md'], pathlib.Path())
    assert resolver.command_args == ['-fREADME.md']
    assert resolver.detect_upload_files() == []

    resolver = FileResolver(['-fREADME.md'], pathlib.Path(), input_files=['README.md'])
    assert resolver.command_args == ['-fREADME.md']
    assert resolver.detect_upload_files() == [pathlib.Path('README.md')]

    resolver = FileResolver(['file=README.md'], pathlib.Path())
    assert resolver.command_args == ['file=README.md']
    assert resolver.detect_upload_files() == [pathlib.Path('README.md')]

    resolver = FileResolver(['file=README.md,die'], pathlib.Path())
    assert resolver.command_args == ['file=README.md,die']
    assert resolver.detect_upload_files() == [pathlib.Path('README.md')]


def test_upload_many_files():
    resolver = FileResolver(['ls', 'samples/sub'], pathlib.Path())
    assert resolver.command_args == ['ls', 'samples/sub']
    assert resolver.detect_upload_files() == [pathlib.Path('samples/sub'), pathlib.Path('samples/sub/source-c.txt')]


def test_fix_arguments():
    the_path = (pathlib.Path.cwd().resolve() / 'README.md').as_posix()

    resolver = FileResolver(['-f', the_path], pathlib.Path())
    assert resolver.command_args == ['-f', the_path[1:]]
    assert resolver.detect_upload_files() == [pathlib.Path(the_path)]

    resolver = FileResolver(['-f', 'tests/../README.md'], pathlib.Path())
    assert resolver.command_args == ['-f', the_path[1:]]
    assert resolver.detect_upload_files() == [pathlib.Path(the_path)]

    resolver = FileResolver(['-f', '../no-such-file.txt'], pathlib.Path())
    assert resolver.command_args == ['-f', '../no-such-file.txt']
    assert resolver.detect_upload_files() == []

    resolver = FileResolver(['-f', 'tests/../no-such-file.txt'], pathlib.Path())
    assert resolver.command_args == ['-f', 'tests/../no-such-file.txt']
    assert resolver.detect_upload_files() == []


def test_upload_target_directories():
    resolver = FileResolver(['--out', 'samples/sub'], pathlib.Path())
    assert resolver.command_args == ['--out', 'samples/sub']
    assert resolver.detect_upload_files() == [pathlib.Path('samples/sub'), pathlib.Path('samples/sub/source-c.txt')]

    resolver = FileResolver(['--out', 'samples/output'], pathlib.Path())
    assert resolver.command_args == ['--out', 'samples/output']
    assert resolver.detect_upload_files() == [pathlib.Path('samples')]
