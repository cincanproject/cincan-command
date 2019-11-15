from cincan.frontend import ToolImage


def test_run_get_string():
    tool = ToolImage(image='cincan/env', rm=False)
    out = tool.run_get_string(['echo', 'Hello'])
    assert out == 'Hello\n'

    out = tool.run_get_string(['echxo', 'Hello'])
    assert 'No such file or directory' in out
