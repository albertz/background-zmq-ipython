Run some IPython ZMQ kernel in the background, without an interactive shell.
You can connect to that kernel remotely via ZMQ.

Alternatives / related links:

* [pydbattach](https://github.com/albertz/pydbattach)
* [Twisted SSH](https://crochet.readthedocs.io/en/stable/introduction.html#ssh-into-your-server)
  ([example code](https://github.com/msabramo/pyramid_ssh_crochet/blob/master/pyramid_ssh_crochet.py))
* `IPython.embed_kernel` in a background thread
  ([example code](https://github.com/msabramo/pyramid_ipython_kernel/blob/master/pyramid_ipython_kernel.py)).
  This has some issues
  (e.g. [here](https://github.com/ipython/ipython/issues/4032);
  messing around with `sys.stdout` etc).
