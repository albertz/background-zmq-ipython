
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

"""

from distutils.core import setup
import time


setup(
    name='background_zmq_ipython',
    version=time.strftime("1.%Y%m%d.%H%M%S", time.gmtime()),
    packages=['background_zmq_ipython'],
    package_dir={'background_zmq_ipython': ''},
    description='Background ZMQ IPython/Jupyter kernel',
    author='Albert Zeyer',
    author_email='albzey@gmail.com',
    url='https://github.com/albertz/background-zmq-ipython',
    license='2-clause BSD license',
    long_description=open('README.rst').read(),
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

