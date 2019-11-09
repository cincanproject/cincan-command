import json
import pathlib
from datetime import datetime
from typing import Optional, List, Dict, Any

from cincan.commands import quote_args

JSON_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'


class FileLog:
    def __init__(self, path: pathlib.Path, md5: str, timestamp: Optional[datetime] = None):
        self.path = path
        self.md5 = md5
        self.timestamp = timestamp

    def to_json(self) -> Dict[str, Any]:
        js = {
            'path': self.path.as_posix(),
            'md5': self.md5
        }
        if self.timestamp:
            js['timestamp'] = self.timestamp.strftime(JSON_TIME_FORMAT)
        return js

    def __repr__(self) -> str:
        return json.dumps(self.to_json(), indent=4)


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

    def to_json(self) -> Dict[str, Any]:
        js = {
            'command': self.command,
            'timestamp': self.timestamp.strftime(JSON_TIME_FORMAT),
            'exit_code': self.exit_code,
        }
        if len(self.in_files) > 0:
            js['in_files'] = [f.to_json() for f in self.in_files]
        if len(self.out_files) > 0:
            js['out_files'] = [f.to_json() for f in self.out_files]
        return js

    def __repr__(self) -> str:
        return json.dumps(self.to_json(), indent=4)
