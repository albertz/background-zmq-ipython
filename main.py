
import os
import sys
import better_exchook


def init_ipython_kernel():
    """
    You can remotely connect to this IPython kernel. See the output on stdout.
    https://github.com/ipython/ipython/issues/8097
    https://stackoverflow.com/questions/29148319/provide-remote-shell-for-python-script
    """
    #
    try:
        import ipykernel.zmqshell
        from ipykernel.ipkernel import IPythonKernel
        from ipykernel.heartbeat import Heartbeat
        from ipykernel import write_connection_file
        from jupyter_client.session import Session
        import zmq
        from zmq.eventloop import ioloop
        from zmq.eventloop.zmqstream import ZMQStream
        # IPython.kernel.zmq.ipkernel.signal = lambda sig, f: None  # Overwrite.
    except ImportError as e:
        print("IPython import error, cannot start IPython kernel. %s" % e)
        return
    import atexit
    import socket
    import logging
    import threading

    import asyncio
    loop = asyncio.get_event_loop()

    # Do in mainthread to avoid history sqlite DB errors at exit.
    # https://github.com/ipython/ipython/issues/680
    assert isinstance(threading.currentThread(), threading._MainThread)
    try:
        connection_file = "kernel-%s.json" % os.getpid()
        def cleanup_connection_file():
            try:
                os.remove(connection_file)
            except (IOError, OSError):
                pass
        atexit.register(cleanup_connection_file)

        logger = logging.Logger("IPython", level=logging.INFO)
        #logger.addHandler(logging.NullHandler())
        logger.addHandler(logging.StreamHandler(sys.stdout))
        session = Session(username=u'kernel', key=b'')

        context = zmq.Context.instance()
        ip = socket.gethostbyname(socket.gethostname())
        transport = "tcp"
        addr = "%s://%s" % (transport, ip)
        shell_socket = context.socket(zmq.ROUTER)
        shell_port = shell_socket.bind_to_random_port(addr)
        iopub_socket = context.socket(zmq.PUB)
        iopub_port = iopub_socket.bind_to_random_port(addr)
        control_socket = context.socket(zmq.ROUTER)
        control_port = control_socket.bind_to_random_port(addr)

        hb_ctx = context #zmq.Context()
        heartbeat = Heartbeat(hb_ctx, (transport, ip, 0))
        hb_port = heartbeat.port
        heartbeat.start()

        shell_stream = ZMQStream(shell_socket)
        control_stream = ZMQStream(control_socket)

        kernel = IPythonKernel(
            session=session,
            shell_streams=[shell_stream, control_stream],
            iopub_socket=iopub_socket,
            log=logger)
        #kernel = IPythonKernel(session=session)

        write_connection_file(connection_file,
                              shell_port=shell_port, iopub_port=iopub_port, control_port=control_port, hb_port=hb_port,
                              ip=ip)

        print("To connect another client to this IPython kernel, use:",
              "jupyter console --existing %s" % connection_file)
    except Exception as e:
        print("Exception while initializing IPython ZMQ kernel. %s" % e)
        return

    def start_kernel():
        print("IPython: Start kernel now. pid: %i" % os.getpid())
        kernel.start()

    def ipython_thread():
        #ioloop.install()

        #loop.call_soon(start_kernel)
        try:
            #loop.run_forever()
            #kernel.start()
            pass

        except KeyboardInterrupt:
            pass

    # TODO run in separate thread ...
    loop.call_soon(start_kernel)
    loop.run_forever()

    thread = threading.Thread(target=ipython_thread, name="IPython kernel")
    #thread.daemon = True
    thread.start()


def main():
    init_ipython_kernel()


if __name__ == '__main__':
    better_exchook.install()
    main()
