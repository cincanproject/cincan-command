import os
import pathlib
import shutil
import sys
import tarfile
import tempfile
import timeit
from datetime import datetime
from logging import Logger
from typing import Dict, Optional, List, Set, Tuple

import docker
from docker.errors import NotFound
from docker.models.containers import Container

from cincan.command_log import FileLog, read_with_hash
from cincan.file_tool import FileMatcher

IGNORE_FILENAME = ".cincanignore"
COMMENT_CHAR = "#"


class TarTool:
    def __init__(self, logger: Logger, container: Container, upload_stats: Dict[str, List],
                 explicit_file: Optional[str] = None):
        self.logger = logger
        self.container = container
        self.upload_stats = upload_stats
        self.explicit_file = explicit_file
        self.time_format_seconds = "%Y-%m-%dT%H:%M:%S"

        self.work_dir: str = container.image.attrs['Config'].get('WorkingDir', '.') or '/'
        if not self.work_dir.endswith('/'):
            self.work_dir += '/'

    def upload(self, upload_files: Dict[pathlib.Path, str], in_files: List[FileLog]):
        if not self.explicit_file and not upload_files:
            return  # nothing to upload

        if self.explicit_file == '-':
            # tar from stdin
            tar_file = tempfile.TemporaryFile()
            try:
                shutil.copyfileobj(sys.stdin.buffer, tar_file)
                tar_file.seek(0)
                self.__list_members(tar_file, in_files)
                tar_file.seek(0)
                self.__put_archive(tar_file)
            finally:
                tar_file.close()  # should be deleted by close
        elif self.explicit_file:
            # tar file provided, use it as-it-is
            explicit_path = pathlib.Path(self.explicit_file)
            with explicit_path.open("rb") as tar_file:
                self.__list_members(tar_file, in_files)
            with explicit_path.open("rb") as tar_file:
                self.__put_archive(tar_file)
        else:
            # collect a tar file, and upload it
            tar_file = self.__create_tar(upload_files, in_files)
            try:
                self.__put_archive(tar_file)
            finally:
                tar_file.close()

    def __put_archive(self, tar_content):
        put_arc_start = timeit.default_timer()
        self.container.put_archive(path=self.work_dir, data=tar_content)
        self.logger.debug("put_archive time %.4f s", timeit.default_timer() - put_arc_start)

    def __list_members(self, tar_content, in_files: List[FileLog]):
        with tarfile.open(fileobj=tar_content, mode="r") as tar:
            for m in tar.getmembers():
                self.logger.debug(f"checking in file {m.name}")
                # file size, modification time, upload time
                self.upload_stats[m.name] = [m.size, m.mtime, datetime.now().timestamp()]
                if not m.isfile():
                    continue
                m_fileobj = tar.extractfile(m)
                m_file = pathlib.Path(m.name)
                m_md = read_with_hash(m_fileobj.read)
                in_files.append(
                    FileLog(m_file.resolve(), m_md, datetime.fromtimestamp(m.mtime)))

    def __create_tar(self, upload_files: Dict[pathlib.Path, str], in_files: List[FileLog]):
        file_out = tempfile.TemporaryFile()
        tar = tarfile.open(mode="w", fileobj=file_out)

        # need to have all directories explicitly, otherwise seen them to be created with root
        # permissions without write possibility for the user
        dirs = set()

        for host_file, arc_name in upload_files.items():
            self.logger.info("<= %s", host_file.as_posix())

            # create all directories leading to the file, unless already added
            a_parent = pathlib.Path(arc_name).parent
            while a_parent and a_parent.as_posix() != '.':
                if a_parent not in dirs:
                    dirs.add(a_parent)
                    tar.addfile(self.__new_directory(a_parent.as_posix()))
                a_parent = a_parent.parent

            if not host_file.exists():
                # no host file, must be explicitly added directory for output
                tar.addfile(self.__new_directory(arc_name))
            else:
                tar_file = tar.gettarinfo(host_file, arcname=arc_name)
                tar_file.mode = 511  # 777 - allow all to access (uid may be different in container)
                # file size, modification time, upload time
                self.upload_stats[arc_name] = [tar_file.size, tar_file.mtime, datetime.now().timestamp()]
                if host_file.is_file():
                    # put file to tar
                    with host_file.open("rb") as f:
                        tar.addfile(tar_file, fileobj=f)
                    # create log entry
                    with host_file.open("rb") as f:
                        file_md = read_with_hash(f.read)
                    in_files.append(
                        FileLog(host_file.resolve(), file_md, datetime.fromtimestamp(host_file.stat().st_mtime)))
                elif host_file.is_dir():
                    # add directory to tar
                    tar.addfile(tar_file)
                else:
                    raise Exception(f"Cannot upload file of unknown type {arc_name}")
        file_out.seek(0)
        return file_out

    @classmethod
    def __new_directory(cls, name: str) -> tarfile.TarInfo:
        p_file = tarfile.TarInfo(name)
        p_file.type = tarfile.DIRTYPE
        p_file.uid = os.getuid()
        p_file.gid = os.getgid()
        p_file.mode = 511  # 777 - allow all to access (uid may be different in container)
        return p_file

    def __read_config_file(self, filepath: pathlib.Path, skip_comment: bool = False) -> List[str]:
        """Read configuration file.
        Returns a list of strings, where one index represents single line of the file.
        """

        file_lines = []
        try:
            chunks, stat = self.container.get_archive(str(filepath))
            tmp_tar = tempfile.TemporaryFile()
            # Write all chunks to construct tar
            for chunk in chunks:
                tmp_tar.write(chunk)
            tmp_tar.seek(0)
            open_tmp_tar = tarfile.open(fileobj=tmp_tar)
            # Extract ignorefile to fileobject
            f = open_tmp_tar.extractfile(filepath.name)
            if skip_comment:
                file_lines = list(filter(None, [line.decode("utf-8") for line in f.read().splitlines() if
                                                not line.decode("utf-8").lstrip().startswith(COMMENT_CHAR)]))
            else:
                file_lines = list(filter(None, [line.decode("utf-8") for line in f.read().splitlines()]))
            tmp_tar.close()
            f.close()
        except NotFound as e:
            self.logger.debug(
                f"Excepted {filepath.name} file not found from path '{filepath}'.")
            self.logger.debug(e)
        return file_lines

    def download_files(self, filters: List[FileMatcher] = None, no_defaults: bool = False,
                       file_paths: List[str] = None, implicit_output=True) -> List[FileLog]:
        """Download modified files, filtered as required"""
        # check all modified (includes the ones we uploaded)
        candidates = sorted(
            [d['Path'] for d in filter(lambda f: 'Path' in f, self.container.diff() or [])], reverse=True)
        # note: candidates start with / as path container absolute
        candidates = self.__filter_files(candidates, filters, no_defaults)

        # write to a tar?
        explicit_file = None
        try:
            if self.explicit_file == '-':
                # write tar to stdout
                explicit_file = tarfile.open(mode="w|", fileobj=sys.stdout.buffer)
            elif self.explicit_file:
                # write tar file
                explicit_file = tarfile.open(self.explicit_file, "w")

            files_to_do = set(candidates)
            out_files = []

            if implicit_output and self.work_dir != '/':
                # container has non-root working directory, get it at once!
                self.logger.debug("%d files to download, looking from %s...", len(files_to_do), self.work_dir)
                log = self.__download_file_set(self.work_dir, files_to_do, write_to=explicit_file)
                out_files.extend(log)

            # explicit result directories
            for fp in file_paths or []:
                if not files_to_do:
                    continue
                fp_in_cont = (pathlib.Path(self.work_dir) / fp).as_posix()
                self.logger.debug("%d files to download, looking from %s...", len(files_to_do), fp_in_cont)
                log = self.__download_file_set(fp_in_cont, files_to_do, write_to=explicit_file)
                out_files.extend(log)

            if implicit_output and files_to_do:
                # go for each missing file individually
                self.logger.debug("%d files to download, fetching each individually", len(files_to_do))
                files_to_load = sorted(files_to_do)
                for f in files_to_load:
                    # separately download and possibly copy remaining result files
                    log = self.__download_file_set(f, files_to_do, write_to=explicit_file)
                    out_files.extend(log)

            if files_to_do:
                self.logger.debug("%d files in diff not downloaded:", len(files_to_do))
                for f in sorted(files_to_do):
                    self.logger.debug("  %s", f)
            return out_files
        finally:
            explicit_file and explicit_file.close()

    def __filter_files(self, candidates: List[str], filters: List[FileMatcher] = None,
                       no_defaults: bool = False) -> List[str]:
        """Filter list of candidate files to download"""
        # Sort by excluding and including filters
        # Including filter has more power than excluding one!
        output_filters_to_exclude = filters.copy() if filters else []
        output_filters_to_include = [output_filters_to_exclude.pop(i) for i, f in
                                     enumerate(output_filters_to_exclude)
                                     if f.include] if filters else []

        # Check if container has .cincanignore file - these are not downloaded by default
        ignore_file = pathlib.Path(self.work_dir) / IGNORE_FILENAME
        ignore_paths = self.__read_config_file(ignore_file, skip_comment=True)
        # Ignore the ignorefile itself..
        ignore_paths.append(IGNORE_FILENAME)
        # remove files which are paths to files
        candidates = candidates.copy()
        skip_set = set()
        for i, c in enumerate(candidates):
            if c in skip_set:
                candidates[i] = None
                continue
            c_parent = pathlib.Path(c).parent
            while c_parent and c_parent.name:
                skip_set.add(c_parent.as_posix())
                c_parent = c_parent.parent
        candidates = list(filter(lambda s: s, candidates))
        # remove candidates which are not in working directory
        candidates = list(filter(lambda s: s.startswith(self.work_dir), candidates))
        # nicely sorted
        candidates.sort()
        # filters?
        ignore_filters = []
        if ignore_paths:
            for file in ignore_paths:
                if file.endswith("/"):
                    file = file + "*"
                    ignore_filters.append(FileMatcher(file, include=False))
                    continue
                if not file.endswith("*"):
                    ignore_filters.append(FileMatcher(file, include=False))
                    ignore_filters.append(FileMatcher(file + "/*", include=False))
                    continue
                ignore_filters.append(FileMatcher(file, include=False))

        # If user has not defined output_filters, use .cincanignore from container if not set to be ignored
        if not filters and ignore_paths and not no_defaults:
            self.logger.debug("No user provided output filters - using .cincanignore")
            for filth in ignore_filters or []:
                candidates = filth.filter_download_files(candidates, self.work_dir)

        elif filters and ignore_paths:

            # Check if user has defined to not use container specific output filters
            if no_defaults:
                for filth in filters or []:
                    candidates = filth.filter_download_files(candidates, self.work_dir)
            elif output_filters_to_include:
                # If we have some including filters, only those are applied
                for filth in output_filters_to_include:
                    candidates = filth.filter_download_files(candidates, self.work_dir)
            else:
                # Merge excluding/ignoring filters, no duplicates
                combined_excluding_filters = set(output_filters_to_exclude)
                if not output_filters_to_exclude:
                    combined_excluding_filters = ignore_filters
                else:
                    for i_f in ignore_filters:
                        for o_f in output_filters_to_exclude:
                            if i_f.match_string == o_f.match_string:
                                break
                            else:
                                combined_excluding_filters.add(i_f)
                for filth in combined_excluding_filters or []:
                    candidates = filth.filter_download_files(candidates, self.work_dir)

        else:
            for filth in filters or []:
                # remove non-matching files
                candidates = filth.filter_download_files(candidates, self.work_dir)
        return candidates

    def __download_file_set(self, file_path: str, files: Set[str],
                            write_to: Optional[tarfile.TarFile] = None) -> List[FileLog]:
        """Download files by a path, copy matching files into host"""
        base_path = pathlib.Path(file_path)

        # fetch the path from container in its own tar ball
        get_arc_start = timeit.default_timer()
        try:
            chunks, _ = self.container.get_archive(file_path)
        except docker.errors.NotFound:
            self.logger.debug("Not found in container: %s", file_path)
            return []

        # read the tarball into temp file
        tmp_tar = tempfile.TemporaryFile()
        for c in chunks:
            tmp_tar.write(c)
        self.logger.debug("get_archive %s time %.4f s", file_path, timeit.default_timer() - get_arc_start)

        tmp_tar.seek(0)
        down_tar = tarfile.open(fileobj=tmp_tar, mode="r|")
        out_files = []
        for tar_file in down_tar:
            file_in_cont = (base_path.parent or base_path) / tar_file.name
            cont_full_name = file_in_cont.as_posix()
            if cont_full_name not in files:
                continue  # not interested in this
            files.remove(cont_full_name)

            if cont_full_name.startswith(self.work_dir):
                file_in_host = pathlib.Path(cont_full_name[len(self.work_dir):])
            elif cont_full_name.startswith('/'):
                file_in_host = pathlib.Path(cont_full_name[1:])
            else:
                self.logger.warning("skipping file %s", cont_full_name)
                continue
            if file_in_host.is_absolute():
                self.logger.warning("skipping suspicious file %s", cont_full_name)
                continue
            modified, unmodified = self.__check_if_modified(file_in_host, tar_file)
            if unmodified:
                continue  # no need to download

            md = ''
            timestamp = datetime.now()
            if write_to:
                # write file to tar, calculate hash
                with tempfile.TemporaryFile() as temp_file:
                    tf_data = down_tar.extractfile(tar_file)
                    md = read_with_hash(tf_data.read, temp_file.write)

                    write_tf = tarfile.TarInfo(file_in_host.as_posix())
                    write_tf.mtime = tar_file.mtime
                    write_tf.mode = tar_file.mode
                    write_tf.size = temp_file.tell()
                    temp_file.seek(0)
                    write_to.addfile(write_tf, fileobj=temp_file)
            elif tar_file.isfile():
                # this is a file we were looking for
                if not file_in_host.exists():
                    # no local file or explicit output asked, this is too easy
                    self.logger.info(f"=> {file_in_host.as_posix()}")
                    tf_data = down_tar.extractfile(tar_file)
                    if file_in_host.parent:
                        file_in_host.parent.mkdir(parents=True, exist_ok=True)
                    with file_in_host.open("wb") as f:
                        md = read_with_hash(tf_data.read, f.write)
                else:
                    # compare by hash, if should override local file
                    tf_data = down_tar.extractfile(tar_file)
                    temp_file = pathlib.Path(file_in_host.as_posix() + '_TEMP')
                    self.logger.debug(f"creating temp file {temp_file.as_posix()}")

                    # calculate hash for file from tar, copy it to temp file
                    if file_in_host.parent:
                        file_in_host.parent.mkdir(parents=True, exist_ok=True)
                    with temp_file.open("wb") as f:
                        md = read_with_hash(tf_data.read, f.write)

                    self.logger.info(f"=> {file_in_host.as_posix()}")
                    if modified:
                        # modified by timestamp or size, overwrite
                        file_in_host.unlink()
                        temp_file.rename(file_in_host)
                    else:
                        # not sure if modified, calculate hash for existing file
                        with file_in_host.open("rb") as f:
                            host_digest = read_with_hash(f.read)

                        if md == host_digest:
                            self.logger.debug(f"identical file {file_in_host.as_posix()} digest {md}, no action")
                            # The file is identical as uploaded
                            # Assuming it was created identical, adding the log entry
                            temp_file.unlink()
                        else:
                            # digest changed, modified despite identical size and timestamps
                            self.logger.debug(
                                f"file {file_in_host.as_posix()} digest in container {md}, in host {host_digest}")
                            file_in_host.unlink()
                            temp_file.rename(file_in_host)
            else:
                if not file_in_host.exists():
                    # must be a directory we need
                    self.logger.info(f"=> {file_in_host.as_posix()}/")
                    file_in_host.mkdir(parents=True, exist_ok=True)
                    timestamp = datetime.fromtimestamp(file_in_host.stat().st_mtime)
                else:
                    pass  # no action required
            out_files.append(FileLog(file_in_host.resolve(), md, timestamp))
        tmp_tar.close()
        return out_files

    def __check_if_modified(self, host_file: pathlib.Path, file_info: tarfile.TarInfo) -> Tuple[bool, bool]:
        """Check if file has been modified, or not modified in the container"""
        up_stat = self.upload_stats.get(host_file.as_posix())
        if up_stat is None:
            return True, False  # not uploaded, must be downloaded

        # original size, upload time, original creation time
        orig_size, orig_time, up_time = up_stat

        # NOTE: for directories (?) size from container is 4096 -> mismatch for directories!!!
        down_size = file_info.size
        if orig_size != down_size:
            self.logger.debug(f"size {host_file.as_posix()} change {orig_size} -> {down_size}")
            return True, False

        # remove fractions for comparison
        down_time_s = int(file_info.mtime)
        orig_time_s = int(orig_time)
        up_time_s = int(up_time)
        if orig_time_s != down_time_s:
            self.logger.debug(f"{host_file.as_posix()} mtime updated at container")
            return True, False
        if orig_time_s != up_time_s:
            self.logger.debug(f"{host_file.as_posix()} old and not modified")
            return False, True
        self.logger.debug(f"{host_file.as_posix()} timestamp nor size tells if modified")
        return False, False
