from multiprocessing.pool import ThreadPool
import threading

class Nonblocking:
    '''
    This is a base class that allows the inheriting class to mark
    its methods as nonblocking, by decorating them with @Nonblocking.method.
    If a method marked as nonblocking is called, it is run in a separate
    thread, and the calling thread continues execution while the method runs.
    In order to get the return value of this method, the client can call the
    <instance>.<method_name>.await_return() class method. This will cause the
    client thread to block until the nonblocking method has finished, at which
    point the return value is read.

    The immedate return value of a nonblocking method is a reference to the
    nonblocking method itself.
    This can be used to make nonblocking methods block like a normal method:
    E.g. return_value = myNonblockingMethod(...).await_return()

    If a method marked as nonblocking calls another nonblocking method (from
    its worker thread), a new worker thread will not be spawned, and the
    function call will happen in the usual blocking manner in the worker
    thread. This is to prevent an unbounded number of thread from being
    created.

    Optionally multiple worker threads can be created, but the default
    number of worker threads is one per Nonblocking class.
    If the client calls a nonblocking method while all (usually only one) the
    worker threads are in use, then the nonblocking method call will be added
    to a queue, and called once a worker thread is free.
    '''
    def __init__(self, threads=1):
        '''
        Use @threads to specify number of worker threads. You probably
        want to leave this at the default of 1 to prevent concurrency issues.
        '''
        self._thread_pool = ThreadPool(processes=threads)
        self._thread_ident = threading.get_ident()
