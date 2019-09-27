Run some IPython ZMQ kernel in the background, without an interactive shell.
You can connect to that kernel remotely via ZMQ.

Installation (`package is on PyPI <https://pypi.org/project/background_zmq_ipython/>`_)::

    pip install background_zmq_ipython

Usage::

    import background_zmq_ipython
    background_zmq_ipython.init_ipython_kernel()

The kernel will then run in the background in its own thread.
The init will print some message similar to this on stdout::

    To connect another client to this IPython kernel, use:
    jupyter console --existing kernel-1111.json

Now, after you connected, how to access globals from the main module? E.g. let's say there is a variable ``a``.

* ``sys.modules["__main__"].a`` should work.
  Via ``sys.modules``, you can access all the imported modules. Or just do ``import mod`` again.
* Get the stack of all/other frames via ``sys._current_frames()``,
  and there you can access the globals from other threads as well.
* You can provide ``user_ns`` to ``init_ipython_kernel``, e.g::

    init_ipython_kernel(user_ns=globals())

  or::
  
    init_ipython_kernel(user_ns={"main_globals": globals()})

  or::
  
    init_ipython_kernel(user_ns={"a": a})


Alternatives / related links:

* `pydbattach <https://github.com/albertz/pydbattach>`_
* `Twisted SSH <https://crochet.readthedocs.io/en/stable/introduction.html#ssh-into-your-server>`_
  (`example code <https://github.com/msabramo/pyramid_ssh_crochet/blob/master/pyramid_ssh_crochet.py>`__)
* ``IPython.embed_kernel`` in a background thread
  (`example code <https://github.com/msabramo/pyramid_ipython_kernel/blob/master/pyramid_ipython_kernel.py>`__).
  This has some issues
  (e.g. `here <https://github.com/ipython/ipython/issues/4032>`_;
  messing around with ``sys.stdout`` etc).
* This code was introduced in
  `this StackOverflow question <https://stackoverflow.com/questions/29148319/provide-remote-shell-for-python-script>`_,
  and also discussed in this `IPython GitHub issue #8097 <https://github.com/ipython/ipython/issues/8097>`_,
  but it has become outdated, so this project provides a rewrite / updated code,
  and the goal was also an easy to install pip package.
