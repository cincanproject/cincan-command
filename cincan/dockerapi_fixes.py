# Temporal file hopefully...
# Contains some method overrides for docker-py
# Fixing some issues not in upstream

import docker
from docker import utils


class CustomContainerApiMixin(docker.api.container.ContainerApiMixin):

    def __init__(self, *args, **kwargs):
        super(CustomContainerApiMixin, self).__init__(*args, **kwargs)

    @utils.check_resource('container')
    def get_archive(self, container, path, chunk_size=docker.api.container.DEFAULT_DATA_CHUNK_SIZE):

        params = {
            'path': path
        }
        url = self._url('/containers/{0}/archive', container)
        # Requests is using gzip | deflate 'Accept-Encoding' header by default, this chunks file into
        # too tiny pieces by Docker engine - override to not use encoding/little chunks to increase performance
        # Saving bandwith by compressing tar does not make sense when querying local docker API in terms of CPU usage
        headers = {
            "Accept-Encoding": "identity"
        }
        res = self._get(url, params=params, stream=True, headers=headers)
        self._raise_for_status(res)
        encoded_stat = res.headers.get('x-docker-container-path-stat')
        return (
            self._stream_raw_result(res, chunk_size, False),
            utils.decode_json_header(encoded_stat) if encoded_stat else None
        )