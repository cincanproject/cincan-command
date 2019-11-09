import argparse
import datetime
import json
import logging
import pathlib
import sys
from typing import List, Set, Dict, Optional

import docker
import docker.errors

from cincan import registry
from cincan.commands import quote_args
from cincan.file_tool import FileResolver
from cincan.tar_tool import TarTool


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
        self.input_files: Optional[List[str]] = None  # Explicit tool input files
        self.upload_files = {}  # files to upload, key = name in host, value = name in image
        self.upload_stats: Dict[str, List] = {} # upload file stats
        self.output_files: Optional[List[str]] = None  # Explicit tool input files
        self.download_files = {}  # files to download, key = name in host, value = name in image

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

    def __create_container(self):
        """Create a container from the image here"""
        # override entry point to just keep the container running
        container = self.client.containers.create(self.image, auto_remove=True, entrypoint="sh",
                                                  stdin_open=True, tty=True)
        container.start()

        # upload files to container
        tar_tool = TarTool(self.logger, container, self.upload_stats)
        tar_tool.upload(self.upload_files)

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

    def __run(self, args: List[str]) -> (bytes, bytes, int):
        """Run native tool in container with given arguments"""

        # resolve files to upload
        resolver = FileResolver(args, pathlib.Path(), input_files=self.input_files)
        for up_file in resolver.detect_upload_files():
            arc_name = resolver.archive_name_for(up_file)
            self.upload_files[up_file.as_posix()] = arc_name
            self.logger.debug(f"{up_file.as_posix()} -> {arc_name}")
        cmd_args = resolver.command_args
        self.logger.debug("args: %s", ' '.join(quote_args(cmd_args)))

        container = self.__create_container()
        try:
            stdout, stderr, exit_code = self.__container_exec(container, cmd_args)
            if exit_code == 0:
                # download results
                tar_tool = TarTool(self.logger, container, self.upload_stats)
                tar_tool.download_files(self.output_files)
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
