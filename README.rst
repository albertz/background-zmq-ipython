Run some IPython ZMQ kernel in the background, without an interactive shell.
You can connect to that kernel remotely via ZMQ.

Alternatives / related links:

* `pydbattach <https://github.com/albertz/pydbattach>`_
* `Twisted SSH <https://crochet.readthedocs.io/en/stable/introduction.html#ssh-into-your-server>`_
  (`example code <https://github.com/msabramo/pyramid_ssh_crochet/blob/master/pyramid_ssh_crochet.py>`_)
* ``IPython.embed_kernel`` in a background thread
  (`example code <https://github.com/msabramo/pyramid_ipython_kernel/blob/master/pyramid_ipython_kernel.py>`_).
  This has some issues
  (e.g. `here <https://github.com/ipython/ipython/issues/4032>`_;
  messing around with ``sys.stdout`` etc).
* This code was introduced in
  `this StackOverflow question <https://stackoverflow.com/questions/29148319/provide-remote-shell-for-python-script>`_,
  and also discussed in this `IPython GitHub issue #8097 <https://github.com/ipython/ipython/issues/8097>`_,
  but it has become outdated, so this project provides a rewrite / updated code,
  and the goal was also an easy to install pip package.
