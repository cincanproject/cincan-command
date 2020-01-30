import pathlib
import re
from typing import List, Optional, Dict, Set, Tuple, Iterable


class FileMatcher:
    """Match files based on a pattern"""
    def __init__(self, match_string: str, include: bool):
        self.match_string = match_string
        self.exact = '*' not in match_string
        self.absolute_path = match_string.startswith('/')
        self.include = include

    @classmethod
    def parse(cls, match_strings: List[str]) -> List['FileMatcher']:
        """Parse pattens from a list"""
        res = []
        for m in match_strings:
            if m.startswith('^'):
                res.append(FileMatcher(m[1:], include=False))
            else:
                res.append(FileMatcher(m, include=True))
        return res

    def filter_upload_files(self, files: List[pathlib.Path]) -> List[pathlib.Path]:
        """Filter uploaded files by this pattern"""
        return list(filter(lambda f: self.__match(f.as_posix()) == self.include, files))

    def filter_download_files(self, files: List[str], work_dir: str) -> List[str]:
        """Filter downloaded files by this pattern"""
        if self.absolute_path:
            # matching absolute files
            res = []
            for file in files:
                if self.__match(file) == self.include:
                    res.append(file)
            return res
        else:
            # matching files relative to working directory
            res = []
            for file in files:
                try:
                    rel_file = pathlib.Path(file).relative_to(work_dir).as_posix()
                except ValueError:
                    if not self.include:
                        res.append(file)
                    continue
                if self.__match(rel_file) == self.include:
                    res.append(file)
            return res

    def __match(self, value: str) -> bool:
        """Match value with this pattern"""
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
    """Resolve files from command line arguments"""
    def __init__(self, args: List[str], directory: pathlib.Path, output_dirs: List[str] = None,
                 do_resolve: bool = True, input_filters: List[FileMatcher] = None):
        self.original_args = args
        self.directory = directory

        # NOTE: Not good for Windows paths!
        self.arg_pattern = re.compile("([a-zA-Z_0-9-/.~]+)")

        self.host_files: List[pathlib.Path] = []
        self.command_args = args.copy()

        # these are output directories, upload them without contents
        for dir in output_dirs or []:
            self.host_files.append(pathlib.Path(dir))
        self.output_dirs = set([pathlib.Path(d) for d in (output_dirs or [])])

        if do_resolve:
            # autodetect input files
            self.__analyze()

            # exclude files by filters, perhaps?
            for filth in input_filters or []:
                self.host_files = filth.filter_upload_files(self.host_files)

    def __analyze(self):
        """Analyze the command line"""
        self.command_args = []
        already_listed: Set[pathlib.Path] = self.output_dirs.copy()
        for o_arg in self.original_args:
            split = list(filter(lambda s: s, self.arg_pattern.split(o_arg)))
            c_args = []
            for part in split:
                o_file = pathlib.Path(part)

                # does file/dir exists? No attempt to copy '/', leave it as it is...
                file_exists = o_file.exists() and not all([c == '/' for c in part])

                if not file_exists and not o_file.is_absolute() and '..' not in o_file.as_posix():
                    # the file does not exist, but it is relative path to a file/directory...
                    o_parent = o_file.parent
                    while not file_exists and o_parent and o_parent.as_posix() != '.':
                        if o_parent.is_dir() and o_parent not in self.host_files:
                            file_exists = True  # ...and there is existing parent directory, perhaps for output
                        o_parent = o_parent.parent

                if file_exists:
                    h_file, a_name = self.__archive_name_for(o_file)
                    if h_file not in already_listed:
                        self.host_files.append(h_file)
                        already_listed.add(h_file)

                    # '/' in the end gets eaten away... fix
                    for p in range(len(part) - 1, 0, -1):
                        if part[p] != '/':
                            break
                        a_name += '/'

                    c_args.append(a_name)
                else:
                    c_args.append(part)

                if file_exists and o_file.is_dir() and o_file not in self.output_dirs:
                    # include files in sub directories
                    self.__include_sub_dirs(o_file.iterdir(), already_listed)

            self.command_args.append(''.join(c_args))

    def __include_sub_dirs(self, files: Iterable[pathlib.Path], file_set: Set[pathlib.Path]):
        """Include files from sub directories"""
        for f in files:
            if f not in file_set:
                self.host_files.append(f)
                file_set.add(f)
            if f.is_dir():
                self.__include_sub_dirs(f.iterdir(), file_set)

    def resolve_upload_files(self, upload_files: Dict[pathlib.Path, str]):
        """Resolve the files to upload"""
        for up_file in self.detect_upload_files():
            host_file, arc_name = self.__archive_name_for(up_file)
            upload_files[host_file] = arc_name
        cmd_args = self.command_args
        return cmd_args

    def detect_upload_files(self, files: Optional[Iterable[pathlib.Path]] = None) -> List[pathlib.Path]:
        """Detect files to upload"""
        it_files = sorted(self.host_files) if files is None else files
        res = []

        # filter out files which do not exist nor should exists
        for file in it_files:
            if file.exists() or file in self.output_dirs:
                res.append(file)

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
        """Resolve host file and archive name for uploaded file"""
        if cls.__use_absolute_path(file):
            h_file = file.resolve()
            a_file = file.resolve().as_posix()
            a_file = a_file[1:] if a_file.startswith('/') else a_file
        else:
            h_file = file
            a_file = file.as_posix()
        return h_file, a_file

    @classmethod
    def __use_absolute_path(cls, file: pathlib.Path) -> bool:
        """Should use absolute path to refer a file path?"""
        # - use absolute paths, if /../ used (ok, quite weak)
        return file.is_absolute() or (".." in file.as_posix())
