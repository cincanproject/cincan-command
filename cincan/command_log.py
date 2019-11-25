import hashlib
import json
import pathlib
import string
from datetime import datetime
from typing import Optional, List, Dict, Any, Iterable

JSON_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'


def quote_args(args: Iterable[str]) -> List[str]:
    """Quote the arguments which contain whitespaces"""
    r = []
    for arg in args:
        if any(map(lambda c: c in string.whitespace, arg)):
            r.append(f'"{arg}"')
        else:
            r.append(arg)
    return r


def read_with_hash(read_more, write_to: Optional = None) -> str:
    """Read data from stream, calculate hash, optionally write the data to stream"""
    md5sum = hashlib.md5()
    chunk = read_more(2048)
    while chunk:
        md5sum.update(chunk)
        if write_to:
            write_to(chunk)
        chunk = read_more(2048)
    return md5sum.hexdigest()


class FileLog:
    """Command log entry for a file"""
    def __init__(self, path: pathlib.Path, md5: str, timestamp: Optional[datetime] = None):
        self.path = path
        self.md5 = md5
        self.timestamp = timestamp

    def to_json(self) -> Dict[str, Any]:
        js = {
            'path': self.path.as_posix()
        }
        if self.md5:
            js['md5'] = self.md5
        if self.timestamp:
            js['timestamp'] = self.timestamp.strftime(JSON_TIME_FORMAT)
        return js

    @classmethod
    def from_json(cls, js: Dict[str, Any]) -> 'FileLog':
        log = FileLog(pathlib.Path(js['path']), js.get('md5', ''))
        if 'timestamp' in js:
            log.timestamp = datetime.strptime(js['timestamp'], JSON_TIME_FORMAT)
        return log

    def __repr__(self) -> str:
        return json.dumps(self.to_json(), indent=4)


class CommandLog:
    """Command log entry"""
    def __init__(self, command: List[str], timestamp: datetime = datetime.now()):
        self.command = command
        self.timestamp = timestamp
        self.exit_code = 0
        self.stdin: Optional[bytes] = None
        self.stdout: Optional[bytes] = None
        self.stderr: Optional[bytes] = None
        self.in_files: List[FileLog] = []
        self.out_files: List[FileLog] = []

    def command_string(self) -> str:
        return " ".join(quote_args(self.command))

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
    """Command log reader/writer base class"""
    def __init__(self, log_directory: Optional[pathlib.Path] = None):
        self.log_directory = log_directory or pathlib.Path.home() / '.cincan' / 'logs'
        self.log_directory.mkdir(parents=True, exist_ok=True)
        self.file_name_format = '%Y-%m-%d-%H-%M-%S-%f'


class CommandLogWriter(CommandLogBase):
    """Command log writer"""
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
    """Command log index for reading command log"""
    def __init__(self, log_directory: Optional[pathlib.Path] = None):
        super().__init__(log_directory)
        self.array = self.__read_log()

    def list_entries(self, reverse: bool = False) -> Iterable[CommandLog]:
        return sorted(self.array, key=lambda e: e.timestamp, reverse=reverse)

    def __read_log(self) -> List[CommandLog]:
        log_l = []
        for file in self.log_directory.iterdir():
            with file.open('r') as f:
                js = json.load(f)
                log_l.append(CommandLog.from_json(js))
        return log_l


class CommandRunner:
    def run(self, args: List[str]) -> CommandLog:
        raise NotImplementedError()
