from typing import Optional, List


class CommandLog:
    def __init__(self, command: List[str]):
        self.command = command
        self.exit_code = 0
        self.stdin: Optional[bytes] = None
        self.stdout: Optional[bytes] = None
        self.stderr: Optional[bytes] = None

