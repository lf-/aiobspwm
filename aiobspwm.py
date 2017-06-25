import asyncio
from typing import List, NamedTuple


class XDisplay(NamedTuple):
    host: str
    display: int
    screen: int


def parse_display(display: str) -> XDisplay:
    """
    Parse a DISPLAY string into its three component pieces

    Returns:
    A NamedTuple (XDisplay) of:
    host -- hostname or empty string
    display -- display number
    screen -- screen number or 0
    """
    host, rest = display.split(':')
    disp = rest.split('.')
    display = int(disp[0])
    if len(disp) == 1:
        # no screen part
        screen = 0
    elif len(disp) == 2:
        # screen part present
        screen = int(disp[1])
    else:
        raise ValueError('More than one dot in DISPLAY string')
    return XDisplay(host, display, screen)


class RWPair(NamedTuple):
    r: asyncio.StreamReader
    w: asyncio.StreamWriter


class BspwmConnection:
    """
    An async context manager for managing a connection to bspwm
    """
    def __init__(self, path):
        self._path = path

    async def __aenter__(self):
        pair = await asyncio.open_unix_connection(path=self._path)
        self._conn = RWPair(*pair)
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        self._conn.w.close()


async def call(sock_path: str, method: List[str]) -> str:
    """
    Call a remote operation like "wm -g" to get wm state in report form

    Parameters:
    sock_path -- path to bspwm socket
    method -- op to call in list form

    Example:
    >>> call('/tmp/bspwm_0_0-socket', 'wm -g'.split(' '))
    'WMLVDS1:oI:OII:fIII:oIV:LM:TT:G'
    """
    async with BspwmConnection(sock_path) as conn:
        conn.w.write(('\0'.join(method)).encode('utf-8') + b'\0')
        await conn.w.drain()
        return (await conn.r.read()).decode('utf-8').rstrip('\n')


class WM:
    """
    Represents the window/desktop state of a window manager at a given socket
    """
    def __init__(self, sock_path: str) -> None:
        """
        Parameters:
        sock_path -- socket path to connect to
        """
        self._sock_path = sock_path

