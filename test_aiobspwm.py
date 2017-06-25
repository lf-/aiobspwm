import asyncio
import os
import stat
import tempfile

import aiobspwm
import pytest


def test_parse_display() -> None:
    """
    Test various display strings
    """
    with pytest.raises(ValueError):
        aiobspwm._parse_display(':1.1.1')
    assert aiobspwm._parse_display(':1') == ('', 1, 0)
    assert aiobspwm._parse_display('abc:0') == ('abc', 0, 0)
    assert aiobspwm._parse_display(':1.1') == ('', 1, 1)


def test_make_bspwm_socket_path() -> None:
    """
    Make various configurations of socket paths
    """
    assert aiobspwm._make_socket_path('', 0, 0) == '/tmp/bspwm_0_0-socket'
    assert aiobspwm._make_socket_path('box', 1, 2) == '/tmp/bspwmbox_1_2-socket'


def test_find_socket_simple(monkeypatch) -> None:
    """
    Test the simple case of getting the bspwm socket in an env variable
    """
    fakeenviron = {
        'BSPWM_SOCKET': '/tmp/bspwm_0_0-socket'
    }
    monkeypatch.setattr('os.environ', fakeenviron)
    assert aiobspwm.find_socket() == '/tmp/bspwm_0_0-socket', 'simple case'


def test_find_socket(monkeypatch) -> None:
    oldstat = os.stat
    def fakestat(path):
        if path != '/tmp/bspwmtest_1_2-socket':
            return oldstat(path)
        return os.stat_result((0,) * 10)
    monkeypatch.setattr('os.stat', fakestat)
    fakeenviron = {
        'DISPLAY': 'test:1.2'
    }
    monkeypatch.setattr('os.environ', fakeenviron)
    with pytest.raises(RuntimeError):
        # test non-socket file
        aiobspwm.find_socket()

    def fakestat2(path):
        if path != '/tmp/bspwmtest_1_2-socket':
            return oldstat(path)
        res = [stat.S_IFSOCK]
        res += [0] * (10 - len(res))
        return os.stat_result(res)
    monkeypatch.setattr('os.stat', fakestat2)
    assert aiobspwm.find_socket() == '/tmp/bspwmtest_1_2-socket',
        'success case with DISPLAY'


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
