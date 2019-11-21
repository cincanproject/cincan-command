import pathlib
from typing import List

from cincan.command_log import CommandLog, CommandRunner


class ContainerCheck(CommandRunner):
    """Check container for suitability for use with this tool"""
    def __init__(self, tool: CommandRunner):
        self.tool = tool

    def run(self, args: List[str]) -> CommandLog:
        # test creation of file and directory in container
        in_file = pathlib.Path('cincan-in/cincan.txt')
        out_file = pathlib.Path('cincan-out/cincan.txt')

        self.tool.entrypoint = '/usr/bin/env'
        if not args:
            args = ['cp', in_file.as_posix(), out_file.as_posix()]  # the default test command

        test_string = 'This is a test'
        try:
            in_file.parent.mkdir(exist_ok=True)
            with in_file.open('w') as f:
                f.write(test_string)
            out_file.parent.mkdir(exist_ok=True)
            if out_file.exists():
                out_file.unlink()

            log = self.tool.run(args)

            test_out = None
            if out_file.is_file():
                with out_file.open() as f:
                    test_out = f.read()
        finally:
            if in_file.exists():
                in_file.unlink()
            if in_file.parent.exists():
                in_file.parent.rmdir()
            if out_file.exists():
                out_file.unlink()
            if out_file.parent.exists():
                out_file.parent.rmdir()

        error = None
        if log.exit_code != 0:
            error = f"Test failed, exit code {log.exit_code}\n"
        elif not test_out:
            error = "Test failed, test file not copied\n"
        else:
            if test_out != test_string:
                error = "Test failed, test data not copied properly\n"

        if error:
            log.stdout = log.stdout + b'\n' if log.stderr else b''
            log.stdout += error.encode('ascii')
        else:
            log.stdout = log.stdout + b'\n' if log.stdout else b''
            log.stdout += "Test pass\n".encode('ascii')
        return log
