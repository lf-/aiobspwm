import setuptools
import sys

import pip

pip_version = tuple([int(x) for x in pip.__version__.split('.')[:3]])
if pip_version < (9, 0, 1) :
    raise RuntimeError('Version of pip less than 9.0.1, breaking python ' \
                       'version requirement support')

with open('version.txt', 'rb') as h:
    version = h.read().decode('utf-8').rstrip('\n')


setuptools.setup(
    name = 'aiobspwm',
    version = version,
    py_modules = ['aiobspwm'],
    python_requires = '>=3.6',
    author = 'lf',
    author_email = 'github@lfcode.ca',
    description = 'asyncio-based bspwm library',
    license = 'MIT',
    keywords = 'asyncio bspwm'.split(' '),
    url = 'https://github.com/lf-/aiobspwm'
)
