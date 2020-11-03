from os.path import basename
import asyncio
import logging
from typing import List
from urllib.parse import urlparse
from docker.models.images import Image
from cincan.configuration import Configuration
from cincanregistry import ToolRegistry, Remotes


class VersionHandler:
    """Class for handling version information from 'cincan-registry' on image runtime"""

    def __init__(self, config: Configuration, registry: ToolRegistry, image: Image, tool_name: str,
                 logger: logging.Logger):
        self.config = config
        self.registry = registry
        self.image = image
        self.tool_name = tool_name
        self.logger = logger
        self.current_version = ""
        self.data_available: bool = False
        self.latest_local: str = ""
        self.local_tags: List = []
        self.local_updates: bool = False
        self.latest_remote: str = ""
        self.remote_tags: List = []
        self.remote_updates: bool = False
        self.latest_origin: str = ""
        self.origin_provider: str = ""

    def _get_version_information(self):
        """
        Get version status of image from remote and origin,
        including local current version
        """
        self.current_version = self.registry.local_registry.get_version_by_image_id(self.image.id)
        loop = asyncio.get_event_loop()
        try:
            version_info = loop.run_until_complete(self.registry.list_versions(self.tool_name, only_updates=False))
        except FileNotFoundError as e:
            # FileNotFoundError is raised if origin check is not implemented
            self.logger.debug(f"Version check failed for {self.tool_name}: {e}")
            return
        if version_info:
            version_data = version_info.get("versions", {})
            local_data = version_data.get("local", {})
            remote_data = version_data.get("remote", {})
            origin_data = version_data.get("origin", {})
            if local_data:
                self.latest_local = local_data.get("version", "")
                self.local_tags = local_data.get("tags", [])
            if remote_data:
                self.latest_remote = remote_data.get("version", "")
                self.remote_tags = remote_data.get("tags", [])
            if origin_data:
                self.latest_origin = origin_data.get("version", "")
                self.origin_provider = origin_data.get("details", {}).get("provider", "")
            available_updates = version_info.get("updates", {})
            self.local_updates = available_updates.get("local")
            self.remote_updates = available_updates.get("remote")
            if version_data and available_updates:
                self.data_available = True

    def compare_versions(self):
        """
        Compare version information, log details
        """

        # Warn about rate limits when using CinCan tools from Docker Hub (is optional registry)
        if self.registry.default_remote == Remotes.DOCKERHUB:
            # Default prefix for dockerhub: cincan
            if not self.tool_name.startswith(f"{self.registry.remote_registry.full_prefix}/"):
                self.logger.debug("Version checking enabled only for 'cincan' tools, or when used from the configured"
                                  f"default registry. Current: {str(self.registry.default_remote)}. Image names"
                                  f"which starts with 'cincan/' are pointing to Docker Hub.")
                return
            else:
                self.logger.warning(f"WARNING: Rate limits will be used, when using Docker Hub. Use with caution! ")
                self.logger.warning(
                    f"Usage will be increased with the amount of tags tool have. Change default registry "
                    f"into {str(list(Remotes)[0])} by modifying file '{self.registry.config.file}'")
        else:
            registry_name = urlparse(self.registry.remote_registry.registry_root).netloc
            if not self.tool_name.startswith(f'{registry_name}/{self.registry.remote_registry.cincan_namespace}/'):
                if self.tool_name.startswith('cincan/'):
                    tool_basename = basename(self.tool_name)
                    self.logger.warning("Version information is not fully supported when using tools "
                                        "from Docker Hub. We are migrating away due to rate limits.")
                    self.logger.warning(f"You can use images from current default registry {str(list(Remotes)[0])}"
                                        f" for example with command 'cincan run {registry_name}"
                                        f"/{self.registry.remote_registry.cincan_namespace}/{tool_basename}'\n")
                    return
                else:
                    self.logger.debug("Version information disabled for non-cincan tools.")
                    return

        self._get_version_information()
        if self.data_available:
            if self.current_version != self.latest_local:
                self.logger.info(
                    f"You are not using latest locally available version: "
                    f"({self.current_version} vs {self.latest_local}) "
                    f"Latest is available with tags '{','.join(self.local_tags)}'")
            if not self.local_updates:
                if self.current_version != self.latest_local:
                    self.logger.info(
                        f"Latest local tool is up-to-date with remote: version {self.latest_local}")
                else:
                    self.logger.info(f"Your tool is up-to-date with remote. Current version: {self.current_version}")
            else:
                if self.config.default_stable_tag in self.remote_tags:
                    self.logger.info(
                        f"Update available in remote: ('{self.latest_local}' vs. '{self.latest_remote}')"
                        f"\nUse 'docker pull {self.tool_name}:{self.config.default_stable_tag}' to update.")
                else:
                    self.logger.info(f"Newer development version available in remote: "
                                     f"'{self.latest_local}' vs. '{self.latest_remote}' with tags '{','.join(self.remote_tags)}'")
            if self.remote_updates:
                self.logger.info(
                    f"Remote is not up-to-date with origin ({self.origin_provider}): "
                    f"'{self.latest_remote}' vs. '{self.latest_origin}'")
        else:
            self.logger.info(f"No version information available for {self.tool_name}\n")
