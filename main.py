
import os
import sys
import better_exchook
import threading


def _embed_kernel_simple():
    """
    Mostly just for reference, and easy code browsing.
    """
    from ipykernel.embed import embed_kernel
    embed_kernel()


class IPythonBackgroundKernelWrapper:
    """
    You can remotely connect to this IPython kernel. See the output on stdout.
    https://github.com/ipython/ipython/issues/8097
    https://stackoverflow.com/questions/29148319/provide-remote-shell-for-python-script
    """

    def __init__(self):
        assert threading.current_thread() is threading.main_thread()
        import asyncio
        self._lock = threading.Lock()
        self._condition = threading.Condition(lock=self._lock)
        self._main_thread = threading.current_thread()
        self._main_loop = asyncio.get_event_loop()
        self._thread = None  # type: threading.Thread
        self._shell_stream = None
        self._control_stream = None
        self._kernel = None
        self._create_logger()
        self._create_session()
        self._create_sockets()
        self._write_connection_file()

    def _create_logger(self):
        import logging
        logger = logging.Logger("IPython", level=logging.INFO)
        # or no logging? logger.addHandler(logging.NullHandler())
        logger.addHandler(logging.StreamHandler(sys.stdout))
        self._logger = logger

    def _create_session(self):
        assert threading.current_thread() is self._main_thread  # not sure...
        from jupyter_client.session import Session, new_id_bytes
        self._session = Session(username=u'kernel', key=new_id_bytes())

    def _create_sockets(self):
        import zmq
        import socket
        from ipykernel.heartbeat import Heartbeat

        context = zmq.Context()  # or existing? zmq.Context.instance()
        ip = socket.gethostbyname(socket.gethostname())
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

    def _write_connection_file(self):
        import atexit
        from ipykernel import write_connection_file

        #connection_file = "kernel-%s.json" % os.getpid()
        connection_file = "kernel.json"
        def cleanup_connection_file():
            try:
                os.remove(connection_file)
            except (IOError, OSError):
                pass
        atexit.register(cleanup_connection_file)

        write_connection_file(connection_file, key=self._session.key, **self._connection_info)

        print("To connect another client to this IPython kernel, use:",
              "jupyter console --existing %s" % connection_file)

    def _setup_streams(self):
        """
        Setup ZMQ streams.
        These need to be constructed within the right active event loop,
        i.e. this must run in the background thread.
        """
        assert threading.current_thread() is self._thread
        from zmq.eventloop.zmqstream import ZMQStream
        # ZMQStream wants a Tornado IOLoop, not a asyncio loop.
        with self._condition:
            self._shell_stream = ZMQStream(self._shell_socket)
            self._control_stream = ZMQStream(self._control_socket)
            self._condition.notify_all()

    def _wait_for_streams(self):
        assert threading.current_thread() is self._main_thread
        with self._condition:
            if not self._shell_stream:
                assert self._thread and self._thread.is_alive()
                self._condition.wait()

    def _create_kernel(self):
        """
        Creates the kernel.
        This must run in the main thread, to avoid history sqlite DB errors at exit.
        https://github.com/ipython/ipython/issues/680
        """
        assert threading.current_thread() is self._main_thread
        self._wait_for_streams()
        from ipykernel.ipkernel import IPythonKernel
        kernel = IPythonKernel(
            session=self._session,
            shell_streams=[self._shell_stream, self._control_stream],
            iopub_socket=self._iopub_socket,
            log=self._logger)
        with self._condition:
            self._kernel = kernel
            self._condition.notify_all()

    def _wait_for_kernel(self):
        # Wait until main thread creates the kernel.
        assert threading.current_thread() is self._thread
        with self._condition:
            if not self._kernel:
                self._condition.wait()

    def _start_kernel(self):
        """
        Starts the kernel itself.
        This must run in the background thread.
        """
        assert threading.current_thread() is self._thread
        self._setup_streams()
        self._wait_for_kernel()
        print("IPython: Start kernel now. pid: %i" % os.getpid())
        self._kernel.start()

    def _thread_loop(self):
        assert threading.current_thread() is self._thread
        import asyncio

        # Need own event loop for this thread.
        loop = asyncio.new_event_loop()
        loop.call_soon(self._start_kernel)
        try:
            loop.run_forever()

        except KeyboardInterrupt:
            pass

    def start(self):
        thread = threading.Thread(target=self._thread_loop, name="IPython kernel")
        thread.daemon = True
        self._thread = thread
        thread.start()
        self._create_kernel()


def init_ipython_kernel():
    kernel_wrapper = IPythonBackgroundKernelWrapper()
    kernel_wrapper.start()


def _endless_dummy_loop():
    import time
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print("KeyboardInterrupt in _endless_dummy_loop")
            return


def main():
    init_ipython_kernel()

    # Do nothing. Keep main thread alive, as IPython kernel lives in a daemon thread.
    # This is just a demo. Normally you would have your main loop in the main thread.
    _endless_dummy_loop()


if __name__ == '__main__':
    better_exchook.install()
    main()
