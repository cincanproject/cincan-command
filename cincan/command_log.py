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

    @classmethod
    def from_json(cls, js: Dict[str, Any]) -> 'FileLog':
        log = FileLog(pathlib.Path(js['path']), js['md5'])
        if 'timestamp' in js:
            log.timestamp = datetime.strptime(js['timestamp'], JSON_TIME_FORMAT)
        return log

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

    @classmethod
    def from_json(cls, js: Dict[str, Any]) -> 'CommandLog':
        log = CommandLog(js['command'], datetime.strptime(js['timestamp'], JSON_TIME_FORMAT))
        if 'in_files' in js:
            log.in_files = [FileLog.from_json(fs) for fs in js['in_files']]
        if 'out_files' in js:
            log.out_files = [FileLog.from_json(fs) for fs in js['out_files']]
        return log

    def __repr__(self) -> str:
        return json.dumps(self.to_json(), indent=4)


class CommandLogBase:
    def __init__(self, log_directory: Optional[pathlib.Path] = None):
        self.log_directory = log_directory or pathlib.Path.home() / '.cincan' / 'logs'
        self.log_directory.mkdir(parents=True, exist_ok=True)
        self.file_name_format = '%Y-%m-%d-%H-%M-%S-%f'


class CommandLogWriter(CommandLogBase):
    def __init__(self, log_directory: Optional[pathlib.Path] = None):
        super().__init__(log_directory)

    def write(self, log: CommandLog):
        log_file = self.__log_file()
        while log_file.exists():
            log_file = self.__log_file()
        with log_file.open("w") as f:
            json.dump(log.to_json(), f)

    def __log_file(self) -> pathlib.Path:
        return self.log_directory / datetime.now().strftime(self.file_name_format)


class CommandLogIndex(CommandLogBase):
    def __init__(self, log_directory: Optional[pathlib.Path] = None):
        super().__init__(log_directory)
        self.array = self.__read_log()

    def __read_log(self) -> List[CommandLog]:
        log_l = []
        for file in self.log_directory.iterdir():
            with file.open('r') as f:
                js = json.load(f)
                log_l.append(CommandLog.from_json(js))
        return log_l
