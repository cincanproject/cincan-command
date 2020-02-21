import docker
import io
import time

import aiohttp
import asyncio


async def main():
    start = time.time()

    conn = aiohttp.UnixConnector(path='/var/run/docker.sock')

    params = {'path': '/out.raw'}
    # tmp_data = io.BytesIO()
    f = open("download.jpg", "wb", buffering=0)
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


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())