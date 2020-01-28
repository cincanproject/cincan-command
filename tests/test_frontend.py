import pathlib
import shutil
import tarfile
import time
from typing import List
import io
import pytest
import subprocess
from cincan.file_tool import FileMatcher
from cincan.frontend import ToolImage

@pytest.fixture(autouse=True)
def disable_tty_interactive(monkeypatch):
    """Mock stdin to make tty part of tests to complete"""
    monkeypatch.setattr('sys.stdin', io.StringIO(''))
    monkeypatch.setattr('sys.stdin.fileno', lambda : 0)


def prepare_work_dir(name: str, with_files: List['str']) -> pathlib.Path:
    src_root = pathlib.Path('samples')
    root = pathlib.Path(name)
    if root.is_dir():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    for f_name in with_files:
        src = src_root / f_name
        dst = root / f_name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        shutil.copystat(src, dst)
    return root


def test_run_get_string():
    tool = ToolImage(image='busybox', rm=False)
    out = tool.run_get_string(['echo', 'Hello'])
    assert out == 'Hello\n'

    out = tool.run_get_string(['echxo', 'Hello'])
    assert 'OCI runtime exec failed: exec failed:' in out


def test_magic_file_io():
    tool = ToolImage(image='busybox', rm=False)
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


def test_input_directory():
    tool = ToolImage(image='busybox', rm=False)
    work_dir = prepare_work_dir('_test', ['source-b.txt', 'source-a.txt'])
    out = tool.run_get_string(['ls', '-1', '_test'])
    assert out == 'source-a.txt\nsource-b.txt\n'
    assert tool.upload_files == ['_test', '_test/source-a.txt', '_test/source-b.txt']
    assert tool.download_files == []


def test_output_mkdir():
    tool = ToolImage(image='busybox', rm=False)
    work_dir = prepare_work_dir('_test', ['source-b.txt', 'source-a.txt'])
    tool.output_dirs = ['_test', '_test/a_test']
    out = tool.run_get_string(['ls', '-1', '_test'])
    assert out == 'a_test\n'
    assert tool.upload_files == ['_test', '_test/a_test']
    assert tool.download_files == ['_test/a_test']


def test_many_output_files():
    tool = ToolImage(image='busybox', rm=False)
    work_dir = prepare_work_dir('_test', ['ab.zip'])
    tool.run_get_string(['unzip', '-d', '_test', '_test/ab.zip'])
    assert tool.upload_files == ['_test', '_test/ab.zip']
    assert tool.download_files == ['_test/source-a.txt', '_test/source-b.txt']


def test_log_stdout():
    tool = ToolImage(image='busybox', rm=False)
    work_dir = prepare_work_dir('_test', ['ab.zip'])
    log = tool.run(['echo', 'abc'])
    assert tool.upload_files == []
    assert tool.download_files == []

    assert len(log.out_files) == 1
    assert log.out_files[0].path == pathlib.Path('/dev/stdout')
    assert log.out_files[0].md5 == '0bee89b07a248e27c83fc3d5951213c1'


def test_log_entries():
    tool = ToolImage(image='busybox', rm=False)
    work_dir = prepare_work_dir('_test', ['ab.zip'])
    log = tool.run(['unzip', '-d', '_test', '_test/ab.zip'])

    assert len(log.in_files) == 1
    assert log.in_files[0].path == pathlib.Path().cwd() / '_test/ab.zip'
    assert log.in_files[0].md5 == 'c0e2d802aadc37f6f3ef51aa98b6b885'

    assert len(log.out_files) == 3
    assert log.out_files[0].path == pathlib.Path('/dev/stdout')
    assert log.out_files[0].md5 == '211a5763cbd6622cca4d801ab22ea171'
    assert log.out_files[1].path == pathlib.Path().cwd() / '_test/source-a.txt'
    assert log.out_files[1].md5 == 'b7e3a4d97941c994007322fd47d5ec03'
    assert log.out_files[2].path == pathlib.Path().cwd() / '_test/source-b.txt'
    assert log.out_files[2].md5 == '10ef82451bb3e854b122e68897d3b0a2'


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


def test_tar_input_log():
    tool = ToolImage(image='busybox', rm=False)
    work_dir = prepare_work_dir('_test', ['ab_zip.tar'])
    tool.input_tar = work_dir / 'ab_zip.tar'
    log = tool.run(['unzip', '-d', '_test', '_test/ab.zip'])

    assert len(log.in_files) == 1
    assert log.in_files[0].path == pathlib.Path().cwd() / '_test/ab.zip'
    assert log.in_files[0].md5 == 'c0e2d802aadc37f6f3ef51aa98b6b885'

    assert len(log.out_files) == 3
    assert log.out_files[0].path == pathlib.Path('/dev/stdout')
    assert log.out_files[0].md5 == '211a5763cbd6622cca4d801ab22ea171'
    assert log.out_files[1].path == pathlib.Path().cwd() / '_test/source-a.txt'
    assert log.out_files[1].md5 == 'b7e3a4d97941c994007322fd47d5ec03'
    assert log.out_files[2].path == pathlib.Path().cwd() / '_test/source-b.txt'
    assert log.out_files[2].md5 == '10ef82451bb3e854b122e68897d3b0a2'


def test_explicit_in_out_files():
    tool = ToolImage(image='busybox', rm=False)
    work_dir = prepare_work_dir('_test', ['ab.zip', 'empty.file'])
    tool.input_filters = FileMatcher.parse(['_test/ab.zip', '_test/empty.file'])  # NOTHING can pass this filter!
    tool.output_filters = FileMatcher.parse(['_test/source-b.txt'])

    tool.run_get_string(['unzip', '-d', '_test', '_test/ab.zip'])
    assert tool.upload_files == []
    assert tool.download_files == []


def test_upload_file_from_dir():
    tool = ToolImage(image='busybox', rm=False)
    # put in extra file, it should *not* get uploaded
    work_dir = prepare_work_dir('_test', ['source-a.txt', 'sub/source-c.txt'])
    tool.run_get_string(['echo', '_test/sub/source-c.txt'])
    assert tool.upload_files == ['_test/sub/source-c.txt']
    assert tool.download_files == []


def test_download_file_from_dir():
    tool = ToolImage(image='busybox', rm=False)
    work_dir = prepare_work_dir('_test', ['sub/source-c.txt'])
    tool.run_get_string(['cp', '_test/sub/source-c.txt', '_test/sub.txt'])
    assert tool.upload_files == ['_test/sub/source-c.txt']
    assert tool.download_files == ['_test/sub.txt']


def test_input_filtering():
    tool = ToolImage(image='busybox', rm=False)
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


def test_download_prefix_files():
    tool = ToolImage(image='busybox', rm=False)
    work_dir = prepare_work_dir('_test', [])
    tool.output_dirs = ['_test/fuzzed']
    r = tool.run(['sh', '-c', 'touch _test/fuzzed/a && touch _test/fuzzed/ab'])
    assert r.exit_code == 0
    assert tool.upload_files == ['_test/fuzzed']
    assert tool.download_files == ['_test/fuzzed/a', '_test/fuzzed/ab']


def test_colon_in_file_name():
    tool = ToolImage(image='busybox', rm=False)
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
    process = subprocess.Popen(['python3', '-m', 'cincan', 'run', '-i', 'busybox', 'sh'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    outs, errs = process.communicate(b'echo Hello, World!\n')
    assert outs == b"Hello, World!\n"
    assert errs == b""