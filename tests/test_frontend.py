from cincan.frontend import ToolImage


def test_run_get_string():
    tool = ToolImage(image='cincan/env', rm=False)
    out = tool.run_get_string(['echo', 'Hello'])
    assert out == 'Hello\n'

    out = tool.run_get_string(['echxo', 'Hello'])
    assert 'No such file or directory' in out


def test_magic_file_io():
    tool = ToolImage(image='cincan/env', rm=False)
    out = tool.run_get_string(['cat', 'samples/source-a.txt'])
    assert out == 'Source A\n'
    assert tool.upload_files == {'samples/source-a.txt': 'samples/source-a.txt'}

    out = tool.run_get_string(['cat', 'samples/source-b.txt'])
    assert out == 'Source B\n'
    assert tool.upload_files == {'samples/source-b.txt': 'samples/source-b.txt'}
