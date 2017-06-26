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
    assert aiobspwm.find_socket() == '/tmp/bspwmtest_1_2-socket', \
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


# some heavily edited data out of a bspwm dump
testdata = {
    'focusedMonitorId': 6291457,
    'monitors': [
        {'borderWidth': 1,
            'desktops': [
                {
                    'borderWidth': 1,
                    'id': 6291459,
                    'layout': 'monocle',
                    'name': 'I',
                    'windowGap': 6
                },
                {
                    'borderWidth': 1,
                    'id': 6291460,
                    'layout': 'monocle',
                    'name': 'II',
                    'windowGap': 6
                }
            ],
            'focusedDesktopId': 6291460,
            'id': 6291457,
            'name': 'LVDS1',
            'padding': {'bottom': 0, 'left': 0, 'right': 0, 'top': 20},
            'randrId': 66,
            'rectangle': {'height': 768, 'width': 1366, 'x': 0, 'y': 0},
            'stickyCount': 0,
            'windowGap': 6,
            'wired': True
        },
        {'borderWidth': 1,
            'desktops': [
                {
                    'borderWidth': 1,
                    'id': 1234,
                    'layout': 'monocle',
                    'name': 'test1',
                    'windowGap': 6
                }
            ],
            'focusedDesktopId': 1234,
            'id': 12345678,
            'name': 'monitor2',
            'padding': {'bottom': 0, 'left': 0, 'right': 0, 'top': 20},
            'randrId': 67,
            'rectangle': {'height': 768, 'width': 1366, 'x': 0, 'y': 0},
            'stickyCount': 0,
            'windowGap': 6,
            'wired': True
        }
    ],
    'primaryMonitorId': 6291457,
    'stackingList': [37748745, 33554441, 23068673, 29360137, 39845897, 31457289]
}

def test_initial_load():
    """
    Test loading a state dump into the WM class
    """
    wm = aiobspwm.WM('/dev/null')
    wm._apply_initial_state(testdata)
    assert wm.focused_monitor in wm.monitors.values()
    for idx, monitor in wm.monitors.items():
        assert monitor.id == idx
        assert monitor.name in ('LVDS1', 'monitor2')
        assert monitor.focused_desktop in monitor.desktops.values()
        for desk_idx, desk in monitor.desktops.items():
            assert desk.id == desk_idx
            assert desk.layout in ('tiled', 'monocle')
            assert desk.name in ('I', 'II', 'test1')

def test_wm_event():
    """
    Test incoming window management events

    TODO: add coverage for unsupported event logging
          (how is that even possible to do anyway??)
    """
    wm = aiobspwm.WM('/dev/null')
    wm._apply_initial_state(testdata)
    wm._on_wm_event('desktop_focus 0x00600001 0x00600003')
    mon_id = 0x00600001
    desk_id = 0x00600003
    assert wm.monitors[mon_id].focused_desktop == \
           wm.monitors[mon_id].desktops[desk_id]
    wm._on_wm_event('desktop_layout 0x00600001 0x00600003 tiled')
    assert wm.monitors[mon_id].desktops[desk_id].layout == 'tiled'
