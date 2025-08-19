"""
IPython/Jupyter kernel
"""

import re
import os
import sys
import threading
import logging
from packaging import version
# Note: IPython uses zmq.eventloop.zmqstream.ZMQStream, see IPythonKernel.
# ZMQStream wants a Tornado IOLoop, not a asyncio loop.
from tornado import ioloop
import ipykernel
from ipykernel.ipkernel import IPythonKernel, ZMQInteractiveShell
from ipykernel.iostream import OutStream

try:
    import typing
except ImportError:
    typing = None
try:
    from better_exchook import better_exchook as except_hook
except ImportError:
    except_hook = sys.excepthook

# Use this to debug Sqlite problems:
# import .sqlite_debugging


def _embed_kernel_simple():
    """
    Mostly just for reference, and easy code browsing.
    """
    from ipykernel.embed import embed_kernel
    embed_kernel()


class OurZMQInteractiveShell(ZMQInteractiveShell):
    """
    Overwrite for the embedding case.
    Also see InteractiveShellEmbed for reference.
    py> `exit(keep_kernel=False)` or `exit(0)` to kill kernel thread
    """

    def init_sys_modules(self):
        pass

    def init_environment(self):
        pass

    def init_prompts(self):
        pass

    def exiter(self, keep_kernel=True):
        # See ZMQExitAutocall.
        self.keepkernel_on_exit = keep_kernel
        self.ask_exit()


class OurIPythonKernel(IPythonKernel):
    """
    Overwrite some functions, to make it work in a thread.
    E.g. we do not want to have any `signal.signal` calls.
    """

    shell_class = OurZMQInteractiveShell

    def pre_handler_hook(self):
        pass

    def post_handler_hook(self):
        pass


class OurOutStream():
    """
    Stream proxy:
    Call thread streams if in my thread
    Otherwise, call standard stream (process-wide)
    """
    def __init__(self, process_stream, session, socket, name):
        self._process_stream = process_stream
        self._thread_stream = OutStream(session, socket, name)
        self._thread_id = threading.currentThread().ident

    def __getattr__(self, name):
        ident = threading.currentThread().ident
        if ident == self._thread_id:
            return getattr(self._thread_stream, name)
        return getattr(self._process_stream, name)


class IPythonBackgroundKernelWrapper:
    """
    You can remotely connect to this IPython kernel. See the output on stdout.
    https://github.com/ipython/ipython/issues/8097
    https://stackoverflow.com/questions/29148319/provide-remote-shell-for-python-script
    """

    def __init__(self, connection_filename=None, connection_fn_with_pid=True, logger=None,
                 user_ns=None, redirect_stdio=False, banner="Hello from background-zmq-ipython.",
                 allow_remote_connections=False):
        """
        :param str connection_filename:
        :param bool connection_fn_with_pid: will add "-<pid>" to the filename (before the extension)
        :param logging.Logger logger:
        :param bool redirect_stdio: write stdio of this thread to the client requesting it
        :param bool allow_remote_connections: allow connections from other machines
        """
        self._lock = threading.Lock()
        self._condition = threading.Condition(lock=self._lock)

        self.connection_filename, self._should_reduce_filename = self._craft_connection_filename(
            connection_filename, connection_fn_with_pid)
        self.loop = None  # type: typing.Optional[ioloop.IOLoop]
        self.thread = None  # type: typing.Optional[threading.Thread]
        self._shell_stream = None
        self._control_stream = None
        self._kernel = None  # type: typing.Optional[OurIPythonKernel]
        self.user_ns = user_ns
        self._redirect_stdio = redirect_stdio
        self._banner = banner
        self._allowed_remote_connections = allow_remote_connections

        if not logger:
            logger = logging.Logger("IPython", level=logging.INFO)
            # or no logging? logger.addHandler(logging.NullHandler())
            logger.addHandler(logging.StreamHandler(sys.stdout))
        self._logger = logger

    def _init_io(self):
        """
        Redirect stdout to iopub socket
        call me after logging connection file
        """
        self._stdout_save, self._stderr_save = sys.stdout, sys.stderr
        sys.stdout = OurOutStream(sys.stdout, self._session, self._iopub_socket, 'stderr')
        sys.stderr = OurOutStream(sys.stderr, self._session, self._iopub_socket, 'stderr')

    def _reset_io(self):
        """
        Restore original io to please client
        call me on kernel close
        """
        sys.stdout = self._stdout_save
        sys.stderr = self._stderr_save

    def _craft_connection_filename(self, connection_filename, connection_fn_with_pid):
        """
        :param str connection_filename:
        :param bool connection_fn_with_pid:
        :return: full connection file path, should logger reduce filename
        :rtype: (str, bool)
        """
        should_reduce_filename = False
        if connection_filename is None:
            connection_filename = 'kernel.json'
            try:
                from jupyter_core.paths import jupyter_runtime_dir
                connection_filename = os.path.join(jupyter_runtime_dir(), connection_filename)
                if connection_fn_with_pid:
                    should_reduce_filename = True
            except ImportError:
                pass
        if connection_fn_with_pid:
            name, ext = os.path.splitext(connection_filename)
            connection_filename = "%s-%i%s" % (name, os.getpid(), ext)
        return connection_filename, should_reduce_filename

    def _create_session(self):
        from jupyter_client.session import Session
        try:
            from jupyter_client.session import new_id_bytes
        except ImportError:
            def new_id_bytes():
                import uuid
                return uuid.uuid4()
        self._session = Session(username=u'kernel', key=new_id_bytes())

    def _create_sockets(self):
        import zmq
        import socket
        from ipykernel.heartbeat import Heartbeat

        context = zmq.Context()  # or existing? zmq.Context.instance()
        if self._allowed_remote_connections:
            ip = socket.gethostbyname(socket.gethostname())
        else:
            ip = '127.0.0.1'
        transport = "tcp"
        addr = "%s://%s" % (transport, ip)
        shell_socket = context.socket(zmq.ROUTER)
        shell_port = shell_socket.bind_to_random_port(addr)
        iopub_socket = context.socket(zmq.PUB)
        iopub_port = iopub_socket.bind_to_random_port(addr)
        control_socket = context.socket(zmq.ROUTER)
        control_port = control_socket.bind_to_random_port(addr)

        # heartbeat doesn't share context, because it mustn't be blocked
        # by the GIL, which is accessed by libzmq when freeing zero-copy messages
        hb_ctx = zmq.Context()
        heartbeat = Heartbeat(hb_ctx, (transport, ip, 0))
        hb_port = heartbeat.port
        heartbeat.start()

        self._connection_info = dict(
            ip=ip,
            shell_port=shell_port, iopub_port=iopub_port, control_port=control_port, hb_port=hb_port)
        self._shell_socket = shell_socket
        self._control_socket = control_socket
        self._iopub_socket = iopub_socket

    def _cleanup_connection_file(self):
        try:
            os.remove(self.connection_filename)
        except (IOError, OSError):
            pass

    def _write_connection_file(self):
        import atexit
        from ipykernel import write_connection_file
        atexit.register(self._cleanup_connection_file)
        os.makedirs(os.path.dirname(self.connection_filename), exist_ok=True)
        write_connection_file(self.connection_filename, key=self._session.key, **self._connection_info)
        # The key should be secret, to only allow the same user to connect.
        # Make sure the permissions are set accordingly.
        os.chmod(self.connection_filename, os.stat(self.connection_filename).st_mode & 0o0700)

        # Log connection advice to stdout
        fname_log = self.connection_filename
        if self._should_reduce_filename:
            fname_log = re.sub(r'.*kernel-([^\-]*).*\.json', r'\1', fname_log)
        self._logger.info(
            "To connect another client to this IPython kernel, use: "
            "jupyter console --existing %s", fname_log)

    def _setup_streams(self):
        """
        Setup ZMQ streams.
        These need to be constructed within the right active event loop,
        i.e. this must run in the background thread.
        """
        assert threading.current_thread() is self.thread
        assert self.loop
        from zmq.eventloop.zmqstream import ZMQStream
        with self._condition:
            self._shell_stream = ZMQStream(self._shell_socket, io_loop=self.loop)
            self._control_stream = ZMQStream(self._control_socket, io_loop=self.loop)
            self._condition.notify_all()

    def _create_kernel(self):
        """
        Creates the kernel.
        This should be done in the background thread.
        """
        from traitlets.config.loader import Config
        assert threading.current_thread() is self.thread
        # Creating the kernel will also initialize the shell (ZMQInteractiveShell) on the first call.
        # The shell will have the history manager (HistoryManager).
        # HistoryManager/HistoryAccessor will init the Sqlite DB. It will be closed via atexit,
        # so we want to allow the access from a different thread at that point.
        # Also see here: https://github.com/ipython/ipython/issues/680
        config = Config()
        config.InteractiveShell.banner2 = self._banner
        config.HistoryAccessor.connection_options = dict(check_same_thread=False)
        kernel = OurIPythonKernel(
            session=self._session,
            **(dict(shell_stream=self._shell_stream, control_stream=self._control_stream)
               if version.parse(ipykernel.__version__) >= version.parse('6.0')
               else dict(shell_streams=[self._shell_stream, self._control_stream])),
            iopub_socket=self._iopub_socket,
            log=self._logger,
            user_ns=self.user_ns,
            config=config)
        with self._condition:
            self._kernel = kernel
            self._condition.notify_all()

    def _start_kernel(self):
        """
        Starts the kernel itself.
        This must run in the background thread.
        """
        assert threading.current_thread() is self.thread

        self._create_session()
        self._create_sockets()
        self._write_connection_file()

        self._setup_streams()
        self._create_kernel()

        self._logger.info(
            "IPython: Start kernel now. pid: %i, thread: %r",
            os.getpid(), threading.current_thread())
        if self._redirect_stdio:
            import atexit
            self._init_io()
            atexit.register(self._reset_io)
        self._kernel.start()

    def _tornado_handle_callback_exception(self, callback):
        self._logger.info("Tornado exception.")
        except_hook(*sys.exc_info())

    def _thread_loop(self):
        assert threading.current_thread() is self.thread

        # Need own event loop for this thread.
        loop = ioloop.IOLoop()
        loop.handle_callback_exception = self._tornado_handle_callback_exception
        self.loop = loop
        loop.make_current()
        loop.add_callback(self._start_kernel)
        try:
            loop.start()
        except KeyboardInterrupt:
            pass

    def start(self):
        thread = threading.Thread(target=self._thread_loop, name="IPython kernel")
        thread.daemon = True
        self.thread = thread
        thread.start()


def init_ipython_kernel(**kwargs):
    kernel_wrapper = IPythonBackgroundKernelWrapper(**kwargs)
    kernel_wrapper.start()
    return kernel_wrapper


init_ipython_kernel.__doc__ = IPythonBackgroundKernelWrapper.__init__.__doc__
