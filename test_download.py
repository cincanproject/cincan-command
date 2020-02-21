import docker
import io
import time
import os
import aiohttp
import asyncio
import urllib

from urllib.request import urlopen 

DOCKER_PATH = '/var/run/docker.sock'

async def main_aiohttp():
    start = time.time()

    conn = aiohttp.UnixConnector(path=DOCKER_PATH)

    params = {'path': '/out.raw'}
    f = io.BytesIO()
    # f = open("download.jpg", "wb", buffering=0)
    index = 0
    async with aiohttp.ClientSession(connector=conn) as session:
        async with session.get('http://v1.35/containers/157f9fdf80c737e39d2ab8d43a2e42a2c077f24a551b70821669a13d283721be/archive', params=params) as resp:
            # print(resp.status)
            # print(await resp.text())

            # async for data in resp.content.iter_chunked(1024 * 1024 * 1000):
            async for data in resp.content.iter_any():
                f.write(data)
                index += 1
    f.close()

    print(f"Time since start: {time.time() - start}. Number of chunks: {index}")


def docker_url(path, **kwargs):
    docker_socket = os.environ.get('DOCKER_SOCKET', '/var/run/docker.sock')
    return urllib.parse.urlunparse((
        'http+unix',
        urllib.parse.quote(docker_socket, safe=''),
        path,
        '',
        urllib.parse.urlencode(kwargs),
        ''))



def main_urllib():

    url = "/v1.35/containers/157f9fdf80c737e39d2ab8d43a2e42a2c077f24a551b70821669a13d283721be/archive"
    print(docker_url(url))
    url = docker_url(url)
    response = urlopen(url)
    CHUNK = 16 * 1024
    with open("second.jpg", 'wb') as f:

        for chunk in iter(lambda: f.read(CHUNK), ''):
            if not chunk:
                break
            f.write(chunk)


if __name__ == "__main__":
    main_urllib()
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())