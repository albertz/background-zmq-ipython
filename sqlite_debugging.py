
import threading
import better_exchook
import logging
import sys


class _WrapSqliteConnect:
    """
    Use this to debug where SQL connections are created.
    E.g. to trace errors like:

        attempt to write a readonly database
        SQLite objects created in a thread can only be used in that same thread

    """

    def __init__(self):
        self.lock = threading.Lock()
        import sqlite3
        self.orig_func = sqlite3.connect
        sqlite3.connect = self

    def __call__(self, *args, **kwargs):
        res = self.orig_func(*args, **kwargs)
        with self.lock:
            print("sqlite connect, thread %r, res %r" % (threading.current_thread(), res))
            # better_exchook.print_tb(None)
            return res


wrap_sqlite_connect = _WrapSqliteConnect()

# IPython HistoryManager uses this logger for Sqlite info.
logging.getLogger("traitlets").addHandler(logging.StreamHandler(sys.stdout))
