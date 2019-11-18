from datetime import datetime
import hashlib
import io
import pathlib
import tarfile
import tempfile
import timeit
from logging import Logger
from typing import Dict, Optional, List

from docker.models.containers import Container

from cincan.command_log import FileLog, read_with_hash
from cincan.file_tool import FileMatcher


class TarTool:
    def __init__(self, logger: Logger, container: Container, upload_stats: Dict[str, List]):
        self.logger = logger
        self.container = container
        self.upload_stats = upload_stats
        self.time_format_seconds = "%Y-%m-%dT%H:%M:%S"

        self.work_dir: str = container.image.attrs['Config'].get('WorkingDir', '.') or '/'
        if not self.work_dir.endswith('/'):
            self.work_dir += '/'

    def upload(self, upload_files: Dict[pathlib.Path, str]):
        if not upload_files:
            return
        file_out = io.BytesIO()
        tar = tarfile.open(mode="w", fileobj=file_out)

        # need to have all directories explicitly, otherwise seen them to be created with root
        # permissions without write possibility for the user
        dirs = set()

        for host_file, arc_name in upload_files.items():
            self.logger.info("<= %s", host_file.as_posix())
            tar_file = tar.gettarinfo(host_file, arcname=arc_name)

            h_parent = host_file.parent
            a_parent = pathlib.Path(arc_name).parent
            while a_parent and a_parent.as_posix() != '.':
                if a_parent not in dirs:
                    dirs.add(a_parent)
                    p_file = tar.gettarinfo(h_parent, arcname=a_parent.as_posix())  # copy permissions
                    tar.addfile(p_file)
                h_parent = h_parent.parent
                a_parent = a_parent.parent

            self.upload_stats[arc_name] = [tar_file.size, tar_file.mtime]  # [size, mtime]
            if host_file.is_file():
                with host_file.open("rb") as f:
                    tar.addfile(tar_file, fileobj=f)
            elif host_file.is_dir():
                tar_file.type = tarfile.DIRTYPE
                tar.addfile(tar_file)
            else:
                raise Exception(f"Cannot upload file of unknown type {arc_name}")
        tar.close()

        put_arc_start = timeit.default_timer()
        self.container.put_archive(path=self.work_dir, data=file_out.getvalue())
        self.logger.debug("put_archive time %.4f ms", timeit.default_timer() - put_arc_start)

    def download_files(self, output_filters: List[FileMatcher] = None) -> List[FileLog]:
        # check all modified (includes the ones we uploaded)
        candidates = sorted([d['Path'] for d in filter(lambda f: 'Path' in f, self.container.diff() or [])])
        # remove files which are paths to files
        for i, c in enumerate(candidates):
            if i < len(candidates) - 1 and candidates[i + 1].startswith(c):
                candidates[i] = None
        candidates = list(filter(lambda s: s, candidates))
        # remove candidates which are not in working directory
        candidates = list(filter(lambda s: s.startswith(self.work_dir), candidates))

        # filters?
        for filth in output_filters or []:
            # remove non-matching files
            candidates = filth.filter_upload_files(candidates, self.work_dir)

        out_files = []
        for f in candidates:
            log = self.__download_file_maybe(f, force_download=False)  # FIXME: We force sometimes?
            out_files.extend(log)
        return out_files

    def __download_file_maybe(self, file_name: str, force_download: bool) -> List[FileLog]:
        # self.logger.debug(f"container file changed {file_name}")
        down_file = pathlib.Path(file_name)
        host_file = pathlib.Path(
            (file_name[len(self.work_dir):] if file_name.startswith(self.work_dir) else file_name).replace(':', '_'))

        # get the tar ball for the files
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
        for tf in down_tar:
            cont_file = pathlib.Path(down_file).parent / tf.name
            if cont_file.as_posix() != file_name:
                # trim away leading directories
                continue
            md5 = ''
            timestamp = datetime.now()
            if tf.isfile() and (force_download or not host_file.exists()):
                # no local file or explicit output asked, this is too easy
                self.logger.info(f"=> {host_file.as_posix()}")
                tf_data = down_tar.extractfile(tf)
                if host_file.parent:
                    host_file.parent.mkdir(parents=True, exist_ok=True)
                with host_file.open("wb") as f:
                    md5 = read_with_hash(tf_data.read, f.write)
            elif tf.isfile() and host_file.is_dir():
                raise Exception(f"=> {host_file.as_posix()} failed, a directory with that name exists")
            elif tf.isfile() and host_file.exists():
                # compare by hash, if should override local file
                tf_data = down_tar.extractfile(tf)
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
                    self.logger.debug(f"file {host_file.as_posix()} md5 in container {md5}, in host {host_digest}")
                    host_file.unlink()
                    temp_file.rename(host_file)
            elif tf.isdir() and host_file.is_file():
                raise Exception(f"mkdir {host_file.as_posix()} failed, a file with that name exists")
            elif tf.isdir() and host_file.is_dir():
                pass  # no action required
            elif tf.isdir():
                self.logger.info(f"=> {host_file.as_posix()}/")
                host_file.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.fromtimestamp(host_file.stat().st_mtime)
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
