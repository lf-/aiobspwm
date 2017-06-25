import asyncio
import os
import os.path
import stat
from typing import List, NamedTuple


class XDisplay(NamedTuple):
    host: str
    display: int
    screen: int


def _parse_display(display: str) -> XDisplay:
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


def _make_socket_path(host: str, display: int, screen: int) -> str:
    """
    Attempt to create a path to a bspwm socket.

    No attempts are made to ensure its actual existence.

    The parameters are intentionally identical to the layout of an XDisplay,
    so you can just unpack one.

    Parameters:
    host -- hostname
    display -- display number
    screen -- screen number

    Example:
    >>> _make_socket_path(*_parse_display(':0'))
    '/tmp/bspwm_0_0-socket'
    """
    return f'/tmp/bspwm{host}_{display}_{screen}-socket'


def _is_socket(path: str) -> bool:
    """
    Find if a given path is a socket.

    Parameters:
    path -- path to check

    Raises:
    FileNotFoundError if the path doesn't actually exist
    """
    mode = os.stat(path).st_mode
    return stat.S_ISSOCK(mode)


def find_socket() -> str:
    """
    Try to find the bspwm socket using env variables
    """
    if 'BSPWM_SOCKET' in os.environ:
        # this is unlikely, but try it anyway
        return os.environ['BSPWM_SOCKET']

    try:
        # this intentionally uses the unsafe environment access so it blows
        # up if DISPLAY is unset
        path = _make_socket_path(*_parse_display(os.environ['DISPLAY']))
        if _is_socket(path):
            return path
        else:
            raise RuntimeError('Found non-socket file at bspwm socket '
                               'location')
    except (FileNotFoundError, KeyError) as e:
        raise RuntimeError('Failed to find bspwm socket') from e


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
    >>> await call('/tmp/bspwm_0_0-socket', 'wm -g'.split(' '))
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


