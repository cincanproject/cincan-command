import argparse
import datetime
import hashlib
import io
import json
import logging
import pathlib
import sys
import tarfile
import tempfile
import timeit
from typing import List, Set, Dict, Optional

import docker
import docker.errors
from cincan import registry
from cincan.commands import quote_args
from cincan.file_tool import FileResolver


class ToolImage:
    """A tool wrapped to docker image"""

    def __init__(self, name: str, path: Optional[str] = None,
                 image: Optional[str] = None,
                 pull: bool = False,
                 tag: Optional[str] = None,
                 rm: bool = True):
        self.logger = logging.getLogger(name)
        self.client = docker.from_env()
        self.name = name
        if path is not None:
            if tag is not None:
                self.image, log = self.client.images.build(path=path, tag=tag, rm=rm)
            else:
                self.image, log = self.client.images.build(path=path, rm=rm)
            self.context = path
            self.__log_dict_values(log)
        elif image is not None:
            if pull:
                # pull first
                self.logger.info(f"pulling image...")
                self.__get_image(image, pull=True)
            else:
                # just get the image
                try:
                    self.__get_image(image, pull=False)
                except docker.errors.ImageNotFound:
                    # image not found, try to pull it
                    self.logger.info(f"pulling image...")
                    self.__get_image(image, pull=True)
            self.context = '.'  # not really correct, but will do
        else:
            raise Exception("No file nor image specified")
        self.upload_files = {}  # files to upload, key = name in host, value = name in image
        self.input_files: Optional[List[str]] = None  # Explicit tool input files
        self.upload_stats: Dict[str, List] = {}
        self.input_tar = None  # optional input tar name, directory name, or '-' for stdin
        self.output_files: Optional[List[str]] = None  # Explicit tool input files
        self.upload_tar = None  # tar file pathlib.Path to upload
        self.download_files = {}  # files to download, key = name in host, value = name in image
        self.time_format_seconds = "%Y-%m-%dT%H:%M:%S"
        self.dump_upload_tar = False

    def get_tags(self) -> List[str]:
        """List image tags"""
        return self.image.tags

    def get_id(self) -> str:
        return self.image.id

    def get_creation_time(self) -> datetime.datetime:
        """Get image creation time"""
        return registry.parse_json_time(self.image.attrs['Created'])

    def __get_image(self, image: str, pull: bool = False):
        """Get Docker image, possibly pulling it first"""
        if pull:
            self.client.images.pull(image)
        self.image = self.client.images.get(image)

    def __create_upload_tar(self) -> Optional[bytes]:
        """Copy uploaded files into tar archive"""
        if not self.upload_files:
            return None
        file_out = io.BytesIO()
        tar = tarfile.open(mode="w", fileobj=file_out)
        for name, arc_name in self.upload_files.items():
            self.logger.info("copy %s in", name)
            host_file = pathlib.Path(name)

            tar_file = tar.gettarinfo(name=name, arcname=arc_name)
            self.upload_stats[arc_name] = [tar_file.size, tar_file.mtime]  # [size, mtime]
            if host_file.is_file():
                with host_file.open("rb") as f:
                    tar.addfile(tar_file, fileobj=f)
            else:
                tar.addfile(tar_file)
        tar.close()
        return file_out.getvalue()

    def __create_container(self):
        """Create a container from the image here"""
        # override entry point to just keep the container running
        container = self.client.containers.create(self.image, auto_remove=True, entrypoint="sh",
                                                  stdin_open=True, tty=True)
        container.start()

        tarball = self.__create_upload_tar()
        if tarball:
            self.logger.debug("Tarball to upload, size %d", len(tarball))
            if self.dump_upload_tar:
                with open("upload_files.tar", "wb") as f:
                    f.write(tarball)
            put_arc_start = timeit.default_timer()
            container.put_archive(path='.', data=tarball)
            self.logger.debug("put_archive time %.4f ms", timeit.default_timer() - put_arc_start)
        return container

    def __container_exec(self, container, cmd_args: List[str]) -> (str, str, int):
        """Execute a command in the container"""
        # create the full command line and run with exec
        entry_point = self.image.attrs['Config'].get('Entrypoint')
        if not entry_point:
            entry_point = []
        cmd = self.image.attrs['Config'].get('Cmd')
        if not cmd:
            cmd = []  # 'None' value observed
        full_cmd = entry_point + (cmd_args if cmd_args else cmd)
        exit_code, cmd_output = container.exec_run(full_cmd, demux=True)
        stdout = cmd_output[0] if cmd_output[0] else b''
        stderr = cmd_output[1] if cmd_output[1] else b''
        return stdout, stderr, exit_code

    def _download_file_maybe(self, container, file_name: str):
        # self.logger.debug(f"container file changed {file_name}")
        down_file = pathlib.Path(file_name)
        # all files come with leading '/' whether they are in home or in root :O
        # ... just strip it and put all to work dir
        host_file = pathlib.Path((file_name[1:] if file_name.startswith('/') else file_name).replace(':', '_'))

        get_arc_start = timeit.default_timer()
        chunks, stat = container.get_archive(file_name)

        up_stat = self.upload_stats.get(host_file.as_posix())

        # NOTE: for directories (?) size from container is 4096 -> mismatch for directories!!!
        up_down_size_mismatch = False
        if up_stat and 'size' in stat:
            down_size = int(stat['size'])
            up_size = up_stat[0]
            up_down_size_mismatch = up_size != down_size
            if up_down_size_mismatch:
                self.logger.debug(f"size {host_file.as_posix()} change {up_size} -> {down_size}")

        if (not up_down_size_mismatch) and up_stat and 'mtime' in stat:
            down_time_s = stat['mtime']  # seconds + timezone
            up_time = datetime.datetime.fromtimestamp(int(up_stat[1]))
            up_time_s = up_time.strftime(self.time_format_seconds)  # seconds
            time_now_s = datetime.datetime.now().strftime(self.time_format_seconds)
            if down_time_s.startswith(up_time_s) and up_time_s != time_now_s:
                # down_time is seconds, up_time has more precision
                self.logger.debug(f"timestamp {host_file.as_posix()} not updated {down_time_s}")
                return
            self.logger.debug(f"timestamp {host_file.as_posix()} updated {up_time_s} -> {down_time_s}")

        tmp_tar = tempfile.TemporaryFile()
        for c in chunks:
            # self.logger.debug(f"chunk of {len(c)} bytes")
            tmp_tar.write(c)
        self.logger.debug("get_archive time %.4f ms", timeit.default_timer() - get_arc_start)

        tmp_tar.seek(0)
        down_tar = tarfile.open(fileobj=tmp_tar, mode="r|")
        for tf in down_tar:
            cont_file = pathlib.Path(down_file).parent / tf.name
            if cont_file.as_posix() != file_name:
                # trim away leading directories
                continue
            if tf.isfile() and (not host_file.exists() or self.output_files is not None):
                # no local file or explicit output asked, this is too easy
                self.logger.info(f"copy out {host_file.as_posix()}")
                tf_data = down_tar.extractfile(tf)
                if host_file.parent:
                    host_file.parent.mkdir(parents=True, exist_ok=True)
                with host_file.open("wb") as f:
                    f_chunk = tf_data.read(2048)
                    while f_chunk:
                        f.write(f_chunk)
                        f_chunk = tf_data.read(2048)
            elif tf.isfile() and host_file.is_dir():
                raise Exception(f"copy out {host_file.as_posix()} failed, a directory with that name exists")
            elif tf.isfile() and host_file.exists():
                # compare by hash, if should override local file
                tf_data = down_tar.extractfile(tf)
                candi_file = pathlib.Path(host_file.as_posix() + '_TEMP')
                self.logger.debug(f"creating temp file {candi_file.as_posix()}")
                if host_file.parent:
                    host_file.parent.mkdir(parents=True, exist_ok=True)
                candi_f = candi_file.open("wb")
                md5sum = hashlib.md5()
                f_chunk = tf_data.read(2048)
                while f_chunk:
                    candi_f.write(f_chunk)
                    md5sum.update(f_chunk)
                    f_chunk = tf_data.read(2048)
                candi_f.close()
                tf_digest = md5sum.hexdigest()

                # calculate hash for existing file
                with host_file.open("rb") as f:
                    md5sum = hashlib.md5()
                    f_chunk = f.read(2048)
                    while f_chunk:
                        md5sum.update(f_chunk)
                        f_chunk = f.read(2048)
                    candi_digest = md5sum.hexdigest()

                if tf_digest == candi_digest:
                    self.logger.debug(f"identical file {host_file.as_posix()} md5 {tf_digest}, no action")
                    candi_file.unlink()
                    continue

                self.logger.debug(f"file {host_file.as_posix()} md5 in container {tf_digest}, in host {candi_digest}")
                self.logger.info(f"copy out and replace {host_file.as_posix()}")
                host_file.unlink()
                candi_file.rename(host_file)
            elif tf.isdir() and host_file.is_file():
                raise Exception(f"mkdir {host_file.as_posix()} failed, a file with that name exists")
            elif tf.isdir() and host_file.is_dir():
                pass  # no action required
            elif tf.isdir():
                self.logger.info(f"mkdir {host_file.as_posix()}")
                host_file.mkdir(parents=True, exist_ok=True)
        tmp_tar.close()

    def _download_files(self, container):
        # resolve files to download
        if self.output_files is not None:
            candidates = self.output_files  # explicitly given
        else:
            # check all modified (includes the ones we uploaded)
            candidates = sorted([d['Path'] for d in filter(lambda f: 'Path' in f, container.diff() or [])])
            # remove files which are paths to files
            for i, c in enumerate(candidates):
                if i < len(candidates) -1 and candidates[i+1].startswith(c):
                    candidates[i] = None
            candidates = list(filter(lambda s: s, candidates))
        for f in candidates:
            self._download_file_maybe(container, f)

    def __run(self, args: List[str]) -> (bytes, bytes, int):
        """Run native tool in container with given arguments"""

        # resolve files to upload and fix command-line if required
        resolver = FileResolver(args, pathlib.Path(), input_files=self.input_files)
        for up_file in resolver.detect_upload_files():
            arc_name = resolver.archive_name_for(up_file)
            self.upload_files[arc_name] = up_file.as_posix()
            self.logger.debug(f"{up_file.as_posix()} -> {arc_name}")
        cmd_args = resolver.command_args
        self.logger.debug("args: %s", ' '.join(quote_args(cmd_args)))

        container = self.__create_container()
        try:
            stdout, stderr, exit_code = self.__container_exec(container, cmd_args)
            if exit_code == 0:
                self._download_files(container)
        finally:
            self.logger.debug("killing the container")
            container.kill()

        return stdout, stderr, exit_code

    def run(self, args: List[str]) -> (bytes, bytes, int):
        """Run native tool in container, return output"""
        return self.__run(args)

    def run_get_string(self, args: List[str], preserve_image: Optional[bool] = False) -> str:
        """Run native tool in container, return output as a string"""
        r = self.__run(args)
        if not preserve_image:
            try:
                self.remove_image()
            except docker.errors.APIError as e:
                self.logger.warning(e)
        return r[0].decode('utf8') + r[1].decode('utf8')

    def __log_dict_values(self, log: Set[Dict[str, str]]) -> None:
        """Log values from a dict as debug"""
        for i in log:
            v = i.values()
            self.logger.debug("{}".format(*v).strip())

    def file_to_copy_from_context(self, file: str) -> str:
        """Create path for sample file inside docker context (for unit testing) """
        return str(pathlib.Path(self.context) / file)

    def remove_image(self):
        """Remove this image"""
        self.client.images.remove(self.get_id())


def tool_with_file(file: str, use_tag: Optional[bool] = True) -> ToolImage:
    path = pathlib.Path(file).parent.name
    tag = None
    if use_tag:
        tag = 'test_{}'.format(path)
    return ToolImage(name=path, path=path, tag=tag)


def image_default_args(sub_parser):
    """Default arguments for sub commands which load docker image"""
    sub_parser.add_argument('tool', help="the tool and possible arguments", nargs=argparse.REMAINDER)
    sub_parser.add_argument('-p', '--path', help='path to Docker context')
    sub_parser.add_argument('-u', '--pull', action='store_true', help='Pull image from registry')
    sub_parser.add_argument('--unpack', action='store_true',
                            help="Unpack output file(s) from tar")
    sub_parser.add_argument('--dump-upload-files', action='store_true',
                            help="Dump the uploaded tar file into 'upload_files.tar'")


def main():
    m_parser = argparse.ArgumentParser()
    m_parser.add_argument("-l", "--log", dest="log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                          help="Set the logging level", default=None)
    m_parser.add_argument('-q', '--quiet', action='store_true', help='Be quite quiet')
    subparsers = m_parser.add_subparsers(dest='sub_command')

    run_parser = subparsers.add_parser('run')
    image_default_args(run_parser)
    run_parser.add_argument('-i', '--in', dest='input_files', default=None, help='Explicitly list tool input files')
    run_parser.add_argument('-o', '--out', dest='output_files', default=None, help='Explicitly list tool output files')

    list_parser = subparsers.add_parser('list')
    list_parser.add_argument('-i', '--in', dest='input', action='store_true', help='Show input formats')
    list_parser.add_argument('-o', '--out', action='store_true', help='Show output formats')
    list_parser.add_argument('-t', '--tags', action='store_true', help='Show tags')

    mani_parser = subparsers.add_parser('manifest')
    image_default_args(mani_parser)

    help_parser = subparsers.add_parser('help')

    if len(sys.argv) > 1:
        args = m_parser.parse_args(args=sys.argv[1:])
    else:
        args = m_parser.parse_args(args=['help'])

    log_level = args.log_level if args.log_level else ('WARNING' if args.quiet else 'INFO')
    logging.basicConfig(format='%(name)s: %(message)s', level=getattr(logging, log_level))
    if args.sub_command == 'help':
        m_parser.print_help()
        sys.exit(1)
    elif args.sub_command in {'run'}:
        if len(args.tool) == 0:
            raise Exception('Missing tool name argument')
        name = args.tool[0]
        if args.path is None:
            tool = ToolImage(name, image=name, pull=args.pull)
        elif args.path is not None:
            tool = ToolImage(name, path=args.path)
        else:
            tool = ToolImage(name)  # should raise exception
        tool.input_files = list(filter(
            lambda s: s, args.input_files.split(","))) if args.input_files is not None else None
        tool.output_files = list(filter(
            lambda s: s, args.output_files.split(","))) if args.output_files is not None else None
        tool.unpack_download_files = args.unpack
        tool.dump_upload_tar = args.dump_upload_files
        all_args = args.tool[1:]

        ret = tool.run(all_args)
        sys.stdout.buffer.write(ret[0])
        sys.stderr.buffer.write(ret[1])
        sys.exit(ret[2])  # exit code
    elif args.sub_command == 'manifest':
        # sub command 'manifest'
        if len(args.tool) == 0:
            raise Exception('Missing tool name argument')
        name = args.tool[0]
        reg = registry.ToolRegistry()
        info = reg.fetch_manifest(name)
        print(json.dumps(info, indent=2))
    else:
        format_str = "{0:<25}"
        if args.input:
            format_str += " {2:<30}"
        if args.out:
            format_str += " {3:<30}"
        if args.tags:
            format_str += " {4:<20}"
        format_str += " {1}"
        reg = registry.ToolRegistry()
        tool_list = reg.list_tools()
        for tool in sorted(tool_list):
            lst = tool_list[tool]
            print(format_str.format(lst.name, lst.description, ",".join(lst.input), ",".join(lst.output),
                                    ",".join(lst.tags)))
