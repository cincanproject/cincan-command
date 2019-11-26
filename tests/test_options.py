from cincan.frontend import ToolImage


def test_option_user():
    tool = ToolImage(image='cincan/env', rm=False)
    out = tool.run_get_string(['id'])
    assert out == 'uid=1000(appuser) gid=1000(appuser)\n'

    tool = ToolImage(image='cincan/env', rm=False)
    tool.user = 'root'
    out = tool.run_get_string(['id'])
    assert out.startswith('uid=0(root) gid=0(root)')
