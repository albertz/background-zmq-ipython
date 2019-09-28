

import os

if __name__ == '__main__':
    # Make relative imports work here. https://stackoverflow.com/questions/54576879/
    __path__ = [os.path.dirname(os.path.abspath(__file__))]

from .kernel import init_ipython_kernel


def _endless_dummy_loop():
    import time
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print("KeyboardInterrupt in _endless_dummy_loop")
            return


def _sig_handler(num, frame):
    print("Got signal. Dump threads.")
    import better_exchook
    better_exchook.dump_all_thread_tracebacks()


def _main():
    import argparse
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--no_connection_fn_with_pid", action="store_true")
    arg_parser.add_argument("--debug_embed", action="store_true")
    args = arg_parser.parse_args()

    if args.debug_embed:
        from .kernel import _embed_kernel_simple
        _embed_kernel_simple()

    init_ipython_kernel(
        user_ns={"demo_var": 42},
        connection_fn_with_pid=not args.no_connection_fn_with_pid)

    # Do nothing. Keep main thread alive, as IPython kernel lives in a daemon thread.
    # This is just a demo. Normally you would have your main loop in the main thread.
    print("Running endless loop now... Press Ctrl+C to quit.")
    _endless_dummy_loop()


if __name__ == '__main__':
    import better_exchook
    better_exchook.install()
    better_exchook.replace_traceback_format_tb()
    import signal
    signal.signal(signal.SIGUSR1, _sig_handler)
    _main()
