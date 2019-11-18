import pathlib
import re
from datetime import datetime
from typing import List, Optional, Dict, Set, Tuple, Iterable

from cincan.command_log import FileLog, read_with_hash


class FileMatcher:
    def __init__(self, match_string: str, include: bool):
        self.match_string = match_string
        self.exact = '*' not in match_string
        self.include = include

    @classmethod
    def parse(cls, match_strings: List[str], include: bool) -> List['FileMatcher']:
        res = []
        for m in match_strings:
            if m.startswith('^'):
                res.append(FileMatcher(m[1:], include))
            else:
                res.append(FileMatcher(m, include))
        return res

    def list_upload_files(self) -> List[pathlib.Path]:
        return list(pathlib.Path().glob(self.match_string))

    def filter_download_files(self, files: List[pathlib.Path]) -> List[pathlib.Path]:
        return list(filter(lambda f: self.match(f.as_posix()), files))

    def filter_upload_files(self, files: List[str], work_dir: str) -> List[str]:
        if self.match_string.startswith('/'):
            # picking absolute files
            raise NotImplemented()  # FIXME
        else:
            res = []
            for file in files:
                try:
                    rel_file = pathlib.Path(file).relative_to(work_dir).as_posix()
                except ValueError:
                    continue
                if self.match(rel_file):
                    res.append(file)
            return res

    def match(self, value: str) -> bool:
        if self.exact:
            return self.match_string == value
        split = self.match_string.split("*")
        i = 0
        off = 0
        len_v = len(value)
        s = split[0]
        len_s = len(s)
        if len_s > 0:
            if len_v < i + len_s or value[i:i + len_s] != s:
                return False
            off += len_s
            i += 1
        while i < len(split):
            s = split[i]
            len_s = len(s)
            if len_s > 0:
                off = value.find(s, off)
                if off < 0:
                    return False
            i += 1
            off += len_s
        if split[-1] != '' and off != len_v:
            return False
        return True


class FileResolver:
    def __init__(self, args: List[str], directory: pathlib.Path, input_filters: List[FileMatcher] = None):
        self.original_args = args
        self.directory = directory

        # NOTE: Not good for Windows paths!
        self.arg_pattern = re.compile("([a-zA-Z_0-9-/.~]+)")

        self.host_files: List[pathlib.Path] = []
        self.command_args = args.copy()

        if input_filters:
            # input filter(s) specified
            if not input_filters[0].include:
                # start with filtering out the default files
                self.__analyze()
            for filth in input_filters:
                if filth.include:
                    # include files from file system
                    self.host_files.extend(filth.list_upload_files())
                else:
                    # exclude files by matcher
                    self.host_files = filth.filter_download_files(self.host_files)
        else:
            # autodetect input files
            self.__analyze()

    def __analyze(self):
        self.command_args = []
        for o_arg in self.original_args:
            split = list(filter(lambda s: s, self.arg_pattern.split(o_arg)))
            c_args = []
            for part in split:
                o_file = pathlib.Path(part)

                o_is_file = o_file.exists()
                if not o_is_file and not o_file.is_absolute() and '..' not in o_file.as_posix():
                    # the file does not exist, but it is relative path to a file/directory...
                    o_parent = o_file.parent
                    while not o_is_file and o_parent and o_parent.as_posix() != '.':
                        if o_parent.is_dir() and o_parent not in self.host_files:
                            o_is_file = True  # ...and there is existing parent directory, perhaps for output
                        o_parent = o_parent.parent

                if o_is_file:
                    h_file, a_name = self.__archive_name_for(o_file)
                    self.host_files.append(h_file)
                    c_args.append(a_name)
                else:
                    c_args.append(part)
            self.command_args.append(''.join(c_args))

    def resolve_upload_files(self, in_files: List[FileLog], upload_files: Dict[pathlib.Path, str]):
        for up_file in self.detect_upload_files():
            host_file, arc_name = self.__archive_name_for(up_file)
            if up_file.is_file():
                with up_file.open("rb") as f:
                    file_md5 = read_with_hash(f.read)
                in_files.append(FileLog(host_file.resolve(), file_md5, datetime.fromtimestamp(up_file.stat().st_mtime)))
            upload_files[host_file] = arc_name
        cmd_args = self.command_args
        return cmd_args

    def detect_upload_files(self, files: Optional[Iterable[pathlib.Path]] = None) -> List[pathlib.Path]:
        it_files = sorted(self.host_files) if files is None else files
        res = []
        for file in it_files:
            if file.exists():
                res.append(file)
            if file.is_dir():
                sub_res = self.detect_upload_files(file.iterdir())
                res.extend(sub_res)
        if files is None:
            # make sure also paths leading to output files are uploaded
            all_dirs = set()
            for file in res:
                all_dirs.add(file)
                for p in file.parents:
                    all_dirs.add(p)
            for file in filter(lambda f: not f.exists(), it_files):
                # file not exists, but marked for upload - must mean some sub directory for output
                p = file.parent
                while not p.exists():
                    p = p.parent
                if p not in all_dirs:
                    res.append(p)
        return res

    @classmethod
    def __archive_name_for(cls, file: pathlib.Path) -> Tuple[pathlib.Path, str]:
        if cls.__use_absolute_path(file):
            h_file = file.resolve()
            a_file = file.resolve().as_posix().replace(':', '_')  # 'C:/jee' -> 'C_/jee'
            a_file = a_file[1:] if a_file.startswith('/') else a_file
        else:
            h_file = file
            a_file = file.as_posix()
        return h_file, a_file

    @classmethod
    def __use_absolute_path(cls, file: pathlib.Path) -> bool:
        # - use absolute paths, if /../ used (ok, quite weak)
        return file.is_absolute() or (".." in file.as_posix())
