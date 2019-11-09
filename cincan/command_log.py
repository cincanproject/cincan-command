import pathlib
from datetime import datetime
from typing import Optional, List


class FileLog:
    def __init__(self, path: pathlib.Path, md5: str, timestamp: Optional[datetime] = None):
        self.path = path
        self.md5 = md5
        self.timestamp = timestamp


class CommandLog:
    def __init__(self, command: List[str], timestamp: datetime = datetime.now()):
        self.command = command
        self.timestamp = timestamp
        self.exit_code = 0
        self.stdin: Optional[bytes] = None
        self.stdout: Optional[bytes] = None
        self.stderr: Optional[bytes] = None
        self.in_files: List[FileLog] = []
        self.out_files: List[FileLog] = []
