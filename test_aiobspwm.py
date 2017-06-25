import asyncio
import tempfile

import aiobspwm
import pytest


def test_parse_display() -> None:
    """
    Test various display strings
    """
    with pytest.raises(ValueError):
        aiobspwm.parse_display(':1.1.1')
    assert aiobspwm.parse_display(':1') == ('', 1, 0)
    assert aiobspwm.parse_display('abc:0') == ('abc', 0, 0)
    assert aiobspwm.parse_display(':1.1') == ('', 1, 1)


@pytest.mark.asyncio
async def test_call(event_loop: asyncio.BaseEventLoop) -> None:
    """
    Test calling operations
    """
    requests = []
    async def connect_cb(r: asyncio.StreamReader,
                         w: asyncio.StreamWriter) -> None:
        nonlocal requests
        requests.append(await r.read(4096))
        w.write(b'abc\n')
        await w.drain()
        w.write_eof()

    path = tempfile.mktemp()
    svr = await asyncio.start_unix_server(connect_cb, path=path, loop=event_loop)
    assert await aiobspwm.call(path, ['abc', 'def']) == 'abc'
    svr.close()
    await svr.wait_closed()
    assert requests[0] == b'abc\0def\0'
