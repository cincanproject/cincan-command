import io
import os
import pathlib
import sys
import tarfile
import tempfile
import timeit
from datetime import datetime
from logging import Logger
from typing import Dict, Optional, List

from docker.models.containers import Container

from cincan.command_log import FileLog, read_with_hash
from cincan.file_tool import FileMatcher


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

        if self.explicit_file:
            # tar file provided, use it as-it-is
            if self.explicit_file == '-':
                tar_content = sys.stdin.buffer.read()
            else:
                explicit_file = pathlib.Path(self.explicit_file)
                with explicit_file.open("rb") as f:
                    tar_content = f.read()

            with tarfile.open(fileobj=io.BytesIO(tar_content), mode="r") as tar:
                for m in tar.getmembers():
                    self.logger.debug(f"checking in file {m.name}")
                    self.upload_stats[m.name] = [m.size, m.mtime]  # [size, mtime]
                    if not m.isfile():
                        continue
                    m_fileobj = tar.extractfile(m)
                    m_file = pathlib.Path(m.name)
                    m_md5 = read_with_hash(m_fileobj.read)
                    in_files.append(
                        FileLog(m_file.resolve(), m_md5, datetime.fromtimestamp(m.mtime)))
        else:
            tar_content = self.__create_tar(upload_files, in_files)
        put_arc_start = timeit.default_timer()
        self.container.put_archive(path=self.work_dir, data=tar_content)
        self.logger.debug("put_archive time %.4f ms", timeit.default_timer() - put_arc_start)

    def __create_tar(self, upload_files: Dict[pathlib.Path, str], in_files: List[FileLog]) -> bytes:
        file_out = io.BytesIO()
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
                self.upload_stats[arc_name] = [tar_file.size, tar_file.mtime]  # [size, mtime]
                if host_file.is_file():
                    # put file to tar
                    with host_file.open("rb") as f:
                        tar.addfile(tar_file, fileobj=f)
                    # create log entry
                    with host_file.open("rb") as f:
                        file_md5 = read_with_hash(f.read)
                    in_files.append(
                        FileLog(host_file.resolve(), file_md5, datetime.fromtimestamp(host_file.stat().st_mtime)))
                elif host_file.is_dir():
                    # add directory to tar
                    tar.addfile(tar_file)
                else:
                    raise Exception(f"Cannot upload file of unknown type {arc_name}")
        tar.close()
        return file_out.getvalue()

    @classmethod
    def __new_directory(cls, name: str) -> tarfile.TarInfo:
        p_file = tarfile.TarInfo(name)
        p_file.type = tarfile.DIRTYPE
        p_file.uid = os.getuid()
        p_file.gid = os.getgid()
        p_file.mode = 511  # 777 - allow all to access (uid may be different in container)
        return p_file

    def download_files(self, output_filters: List[FileMatcher] = None) -> List[FileLog]:
        # check all modified (includes the ones we uploaded)
        candidates = sorted([d['Path'] for d in filter(lambda f: 'Path' in f, self.container.diff() or [])],
                            reverse=True)
        # remove files which are paths to files
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
        for filth in output_filters or []:
            # remove non-matching files
            candidates = filth.filter_download_files(candidates, self.work_dir)

        # write to a tar?
        explicit_file = None
        try:
            if self.explicit_file == '-':
                explicit_file = tarfile.open(mode="w|", fileobj=sys.stdout.buffer)
            elif self.explicit_file:
                explicit_file = tarfile.open(self.explicit_file, "w")
            out_files = []
            for f in candidates:
                log = self.__download_file_maybe(f, write_to=explicit_file)
                out_files.extend(log)
            return out_files
        finally:
            explicit_file and explicit_file.close()

    def __download_file_maybe(self, file_name: str, write_to: Optional[tarfile.TarFile] = None) -> List[FileLog]:
        host_file = pathlib.Path(
            (file_name[len(self.work_dir):] if file_name.startswith(self.work_dir) else file_name))

        # fetch the file from container in its own tar ball
        get_arc_start = timeit.default_timer()
        chunks, stat = self.container.get_archive(file_name)
        file_modified = self.__check_for_download(host_file, stat)
        if not file_modified:
            return []  # do not attempt download

        # read the tarball into temp file
        tmp_tar = tempfile.TemporaryFile()
        for c in chunks:
            # self.logger.debug(f"chunk of {len(c)} bytes")
            tmp_tar.write(c)
        self.logger.debug("get_archive time %.4f ms", timeit.default_timer() - get_arc_start)

        tmp_tar.seek(0)
        down_tar = tarfile.open(fileobj=tmp_tar, mode="r|")
        out_files = []
        for tar_file in down_tar:
            # Note, we trust all intermediate directories to be provided in the tar files
            local_file = host_file.parent / tar_file.name
            md5 = ''
            timestamp = datetime.now()
            if write_to:
                # write file to tar, calculate hash
                with tempfile.TemporaryFile() as temp_file:
                    tf_data = down_tar.extractfile(tar_file)
                    md5 = read_with_hash(tf_data.read, temp_file.write)

                    write_tf = tarfile.TarInfo(local_file.as_posix())
                    write_tf.mtime = tar_file.mtime
                    write_tf.mode = tar_file.mode
                    write_tf.size = temp_file.tell()
                    temp_file.seek(0)
                    write_to.addfile(write_tf, fileobj=temp_file)
            elif local_file == host_file and tar_file.isfile():
                # this is the file we were looking for
                if not host_file.exists():
                    # no local file or explicit output asked, this is too easy
                    self.logger.info(f"=> {host_file.as_posix()}")
                    tf_data = down_tar.extractfile(tar_file)
                    if host_file.parent:
                        host_file.parent.mkdir(parents=True, exist_ok=True)
                    with host_file.open("wb") as f:
                        md5 = read_with_hash(tf_data.read, f.write)
                else:
                    # compare by hash, if should override local file
                    tf_data = down_tar.extractfile(tar_file)
                    temp_file = pathlib.Path(host_file.as_posix() + '_TEMP')
                    self.logger.debug(f"creating temp file {temp_file.as_posix()}")

                    # calculate hash for file from tar, copy it to temp file
                    if host_file.parent:
                        host_file.parent.mkdir(parents=True, exist_ok=True)
                    with temp_file.open("wb") as f:
                        md5 = read_with_hash(tf_data.read, f.write)

                    # calculate hash for existing file
                    with host_file.open("rb") as f:
                        host_digest = read_with_hash(f.read)

                    self.logger.info(f"=> {host_file.as_posix()}")
                    if md5 == host_digest:
                        self.logger.debug(f"identical file {host_file.as_posix()} md5 {md5}, no action")
                        # The file is identical as uploaded, but timestamps tell different story.
                        # Assuming it was created identical, adding the log entry
                        temp_file.unlink()
                    else:
                        self.logger.debug(
                            f"file {host_file.as_posix()} md5 in container {md5}, in host {host_digest}")
                        host_file.unlink()
                        temp_file.rename(host_file)
            else:
                if not host_file.exists():
                    # must be a directory we need
                    self.logger.info(f"=> {local_file.as_posix()}/")
                    local_file.mkdir(parents=True, exist_ok=True)
                    timestamp = datetime.fromtimestamp(local_file.stat().st_mtime)
                else:
                    pass  # no action required
            out_files.append(FileLog(host_file.resolve(), md5, timestamp))
        tmp_tar.close()
        return out_files

    def __check_for_download(self, host_file: pathlib.Path, stat: Dict) -> bool:
        up_stat = self.upload_stats.get(host_file.as_posix())

        # NOTE: for directories (?) size from container is 4096 -> mismatch for directories!!!
        if up_stat and 'size' in stat:
            down_size = int(stat['size'])
            up_size = up_stat[0]
            up_down_size_mismatch = up_size != down_size
            if up_down_size_mismatch:
                self.logger.debug(f"size {host_file.as_posix()} change {up_size} -> {down_size}")
                return True

        if up_stat and 'mtime' in stat:
            down_time_s = stat['mtime']  # seconds + timezone
            up_time = datetime.fromtimestamp(int(up_stat[1]))
            up_time_s = up_time.strftime(self.time_format_seconds)  # seconds
            time_now_s = datetime.now().strftime(self.time_format_seconds)
            if down_time_s.startswith(up_time_s):
                # looks like timestamp not updated, but down_time is seconds and up_time has more precision
                if up_time_s == time_now_s:
                    self.logger.debug(f"timestamps {host_file.as_posix()} now {down_time_s}, may or may not be updated")
                    return True # edited, but actually we do not know
                self.logger.debug(f"timestamp {host_file.as_posix()} not updated {down_time_s}")
                return False  # not edited, we are sure
            self.logger.debug(f"timestamp {host_file.as_posix()} updated {up_time_s} -> {down_time_s}")
            return True  # edited, we are sure

        return True  # tell edited, but we have no idea
