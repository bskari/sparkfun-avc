"""Decorator for classes to provide mutex for class methods."""
import decorator

@decorator.decorator
def synchronized(wrapped, instance, args, kwargs):  # pylint: disable=unused-argument
    """Decorator that provides mutex."""
    lock = vars(wrapped).get('_lock', None)

    assert lock is not None

    with lock:
        return wrapped(*args, **kwargs)  # pylint: disable=star-args
