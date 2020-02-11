import pathlib

import pytest

from cincan.file_tool import FileResolver, FileMatcher

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

    # FIXME: Should be done by providing files in tar
    # resolver = FileResolver(['-fREADME.md'], pathlib.Path(),
    #                         input_filters=FileMatcher.parse(['README.md']))
    # assert resolver.command_args == ['-fREADME.md']
    # assert resolver.detect_upload_files() == [pathlib.Path('README.md')]

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


def test_create_target_directories():
    resolver = FileResolver(['--out', 'samples/output'], pathlib.Path())
    assert resolver.command_args == ['--out', 'samples/output']
    assert resolver.detect_upload_files() == [pathlib.Path('samples')]


def test_exclude_input():
    resolver = FileResolver(['--in', 'README.md', '--out', 'samples'], pathlib.Path(),
                            input_filters=[FileMatcher('samples/*', include=False)])
    assert resolver.command_args == ['--in', 'README.md', '--out', 'samples']
    assert resolver.detect_upload_files() == [pathlib.Path('README.md'), pathlib.Path('samples')]

    resolver = FileResolver(['--in', 'README.md', '--out', 'samples'], pathlib.Path(),
                            input_filters=[FileMatcher('samples/source-b.txt', include=True)])
    assert resolver.command_args == ['--in', 'README.md', '--out', 'samples']
    assert resolver.detect_upload_files() == [pathlib.Path('samples/source-b.txt')]


def test_with_existing_directory():
    assert pathlib.Path('tests/').is_dir()  # pre-requisite for testing

    # Issue #11 - Cincan-command eats uphill '/' from command
    resolver = FileResolver(['-o', 'tests/%n'], pathlib.Path())
    assert resolver.command_args == ['-o', 'tests/%n']
    assert len(resolver.detect_upload_files()) > 2

    resolver = FileResolver(['-o', 'no_tests/%n'], pathlib.Path())
    assert resolver.command_args == ['-o', 'no_tests/%n']
    assert len(resolver.detect_upload_files()) == 0

    resolver = FileResolver(['-o', 'tests&%&'], pathlib.Path())
    assert resolver.command_args == ['-o', 'tests&%&']
    assert len(resolver.detect_upload_files()) > 2

    resolver = FileResolver(['-o', 'tests///%n'], pathlib.Path())
    assert resolver.command_args == ['-o', 'tests///%n']
    assert len(resolver.detect_upload_files()) > 2

    resolver = FileResolver(['-o', '/'], pathlib.Path())
    assert resolver.command_args == ['-o', '/']
    assert len(resolver.detect_upload_files()) == 0

    resolver = FileResolver(['-o', '//'], pathlib.Path())
    assert resolver.command_args == ['-o', '//']
    assert len(resolver.detect_upload_files()) == 0

    # Issue #26 - space character doesn't work in file name
    resolver = FileResolver(["-i", "'tests/foo: story of foo-bar.pdf'"], pathlib.Path())
    assert resolver.host_files == [pathlib.Path("tests/foo: story of foo-bar.pdf")]
