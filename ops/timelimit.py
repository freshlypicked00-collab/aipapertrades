"""Time limits for the steps of a check-in (owner, Nov 19: "the race must never stop again").

A step that only draws or sends something (a picture, an album, a news feed) may not hold a check-in: limit(seconds) stops it, even when
it is stuck in a loop that never asks the network for anything (the animated-card recorder of Nov 18 was such a loop; no request timeout
could have ended it). StepTimeout is NOT an ordinary Exception, so the many "except Exception: try again" blocks cannot swallow it: it
travels up to the guard that set the limit. Limits can sit inside one another (the whole run has one too).

Used only around steps that do not change the race's records half-way; orders and settlements are never interrupted."""
import contextlib
import signal
import threading
import time


class StepTimeout(BaseException):
    pass


@contextlib.contextmanager
def limit(seconds, what='step'):
    usable = hasattr(signal, 'setitimer') and threading.current_thread() is threading.main_thread()
    if not usable or not seconds or seconds <= 0:
        yield
        return

    def stop(signum, frame):
        raise StepTimeout(f'{what}: stopped after {seconds:g} s')
    old = signal.signal(signal.SIGALRM, stop)
    outer = signal.setitimer(signal.ITIMER_REAL, seconds)[0]   # seconds that were left on a limit around this one (0 = none)
    t0 = time.monotonic()
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)
        if outer > 0:   # the limit around this one goes on with the time it has left
            signal.setitimer(signal.ITIMER_REAL, max(0.01, outer - (time.monotonic() - t0)))


def guarded(fn, seconds, what, default=None, log=print):
    """fn with a time limit: past it, the step is dropped, a line is printed and `default` is returned (a picture that is not made
    means the post goes out without it; nothing else changes)."""
    def w(*a, **k):
        try:
            with limit(seconds, what):
                return fn(*a, **k)
        except StepTimeout as e:
            log(f'::warning title=Step stopped::{e}')
            return default
    w._guarded = True
    w.__name__ = getattr(fn, '__name__', 'guarded')
    return w
