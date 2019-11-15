from cincan.frontend import ToolImage


def test_run_get_string():
    tool = ToolImage(image='cincan/test2tool')
    out = tool.run_get_string(['echo Hello'])
    assert out == 'Hello\n'

    out = tool.run_get_string(['echxo Hello'])
    assert 'echxo: not found' in out
