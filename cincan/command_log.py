import hashlib
import json
import pathlib
import string
import uuid
import os
import getpass
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
    md = hashlib.sha256()
    chunk = read_more(2048)
    while chunk:
        md.update(chunk)
        if write_to:
            write_to(chunk)
        chunk = read_more(2048)
    return md.hexdigest()


class FileLog:
    """Command log entry for a file"""
    def __init__(self, path: pathlib.Path, digest: str, timestamp: Optional[datetime] = None):
        self.path = path
        self.digest = digest
        self.timestamp = timestamp

    def to_json(self) -> Dict[str, Any]:
        js = {
            'path': self.path.as_posix()
        }
        if self.digest:
            js['sha256'] = self.digest
        if self.timestamp:
            js['timestamp'] = self.timestamp.strftime(JSON_TIME_FORMAT)
        return js

    @classmethod
    def from_json(cls, js: Dict[str, Any]) -> 'FileLog':
        log = FileLog(pathlib.Path(js['path']), js.get('sha256', ''))
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
            js['input'] = [f.to_json() for f in self.in_files]
        if len(self.out_files) > 0:
            js['output'] = [f.to_json() for f in self.out_files]
        return js

    @classmethod
    def from_json(cls, js: Dict[str, Any]) -> 'CommandLog':
        log = CommandLog(js['command'], datetime.strptime(js['timestamp'], JSON_TIME_FORMAT))
        if 'input' in js:
            log.in_files = [FileLog.from_json(fs) for fs in js['input']]
        if 'output' in js:
            log.out_files = [FileLog.from_json(fs) for fs in js['output']]
        return log

    def __repr__(self) -> str:
        return json.dumps(self.to_json(), indent=4)


class CommandLogBase:
    """Command log reader/writer base class"""
    def __init__(self, log_directory: Optional[pathlib.Path] = None):
        
        self.file_name_format = '%Y-%m-%d-%H-%M-%S-%f'

        #check if .cincan contains uuid.string, don't create new folder
        if(os.path.isfile(pathlib.Path.home() / '.cincan/uid.txt')):
            with open(pathlib.Path.home() / '.cincan/uid.txt', "r") as f:
                self.directoryname =  f.read()
        else:
            #create uuid.object and folder and such
            self.directoryname = str(uuid.uuid1())

            with open(pathlib.Path.home() / '.cincan/uid.txt', "w") as uid_file:
                uid_file.write(self.directoryname)

        self.log_directory = log_directory or pathlib.Path.home() / '.cincan' / 'shared' / self.directoryname /'logs'
        self.log_directory.mkdir(parents=True, exist_ok=True)


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
        log_root = self.log_directory.parent or self.log_directory  # read log from all users
        self.array = self.__read_log(log_root)

    def list_entries(self, reverse: bool = False) -> Iterable[CommandLog]:
        return sorted(self.array, key=lambda e: e.timestamp, reverse=reverse)

    def __read_log(self, directory: pathlib.Path) -> List[CommandLog]:
        log_l = []
        for file in self.log_directory.iterdir():
            if file.is_dir():
                # recursively go to sub d
                log_l.extend(self.__read_log(file))
            else:
                with file.open('r') as f:
                    js = json.load(f)
                    log_l.append(CommandLog.from_json(js))
        return log_l


class CommandRunner:
    def run(self, args: List[str]) -> CommandLog:
        raise NotImplementedError()
