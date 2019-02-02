
"""
Usage:

Create ~/.pypirc with info:

    [distutils]
    index-servers =
        pypi

    [pypi]
    repository: https://upload.pypi.org/legacy/
    username: ...
    password: ...

(Not needed anymore) Registering the project: python3 setup.py register
New release: python3 setup.py sdist upload

I had some trouble at some point, and this helped:
pip3 install --user twine
python3 setup.py sdist
twine upload dist/background_zmq_ipython-*

See also MANIFEST.in for included files.

For debugging this script:

python3 setup.py sdist
pip3 install --user dist/...*.tar.gz -v
(Without -v, all stdout/stderr from here will not be shown.)

"""

from distutils.core import setup
import time
from pprint import pprint
import os


def debug_print_file(fn):
    print("%s:" % fn)
    if not os.path.exists(fn):
        print("<does not exist>")
        return
    if os.path.isdir(fn):
        print("<dir:>")
        pprint(os.listdir(fn))
        return
    print(open(fn).read())


def parse_pkg_info(fn):
    """
    :param str fn:
    :rtype: dict[str,str]
    """
    res = {}
    for ln in open(fn).read().splitlines():
        if not ln or not ln[:1].strip():
            continue
        key, value = ln.split(": ", 1)
        res[key] = value
    return res


if os.path.exists("PKG-INFO"):
    print("Found existing PKG-INFO.")
    info = parse_pkg_info("PKG-INFO")
    version = info["Version"]
    print("Version via PKG-INFO:", version)
else:
    version = time.strftime("1.%Y%m%d.%H%M%S", time.gmtime())
    print("Version via current time:", version)


if os.environ.get("DEBUG", "") == "1":
    debug_print_file(".")
    debug_print_file("PKG-INFO")


setup(
    name='background_zmq_ipython',
    version=version,
    packages=['background_zmq_ipython'],
    package_dir={'background_zmq_ipython': ''},
    description='Background ZMQ IPython/Jupyter kernel',
    author='Albert Zeyer',
    author_email='albzey@gmail.com',
    url='https://github.com/albertz/background-zmq-ipython',
    license='2-clause BSD license',
    long_description=open('README.rst').read(),
    install_requires=open('requirements.txt').read().splitlines(),
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)

