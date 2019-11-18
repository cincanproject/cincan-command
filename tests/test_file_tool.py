import pathlib

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


def test_upload_many_nimes():
    resolver = FileResolver(['samples/source-a.txt', 'samples', 'samples/ab.zip'], pathlib.Path())
    assert resolver.detect_upload_files() == [pathlib.Path('samples/ab.zip'), pathlib.Path('samples/source-a.txt')]


def test_fix_arguments():
    resolver = FileResolver(['-f', 'tests/../README.md'], pathlib.Path())
    the_path = (pathlib.Path.cwd().resolve() / 'README.md').as_posix()
    assert resolver.command_args == ['-f', the_path[1:]]
    assert resolver.detect_upload_files() == [pathlib.Path(the_path)]
