# aiobspwm

An asyncio bspwm client. This uses the json dump API and event notifications
to keep the state of the window manager constantly updated. It is implemented
using asyncio so the updating of the objects can occur in the background as
events occur.

This is a work-in-progress: issues and pull requests are welcomed!

This library is type-annotated.

## Dependencies

- Python 3.6+ (for f-strings and asyncio changes)

## Usage

For simple use cases, use call() (use await instead of aiorun if
you're not in a REPL):

```python
>>> aiorun(call(None, 'wm -g'.split()))
'WMLVDS1:oI:OII:fIII:oIV:LM:TT:G'
```

To use the abstraction of WM state:

```python
>>> wm = aiobspwm.WM()
>>> aiorun(wm.start())  # pull in initial state asynchronously
>>> wm.monitors.values()
dict_values([<Monitor 'LVDS1' (<Desktop 'I' (tiled)>, <Desktop 'II' (monocle)>,
             <Desktop 'III' (monocle)>, <Desktop 'IV' (monocle)>))])
```

To use the continuous updating of WM state:

```python
>>> asyncio.ensure_future(wm.run())  # this "blocks" forever,
                                     # so run it in the background
```

aiorun() source:

```python
def aiorun(coro):
    import asyncio
    return asyncio.get_event_loop().run_until_complete(coro)
```
