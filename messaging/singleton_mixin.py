"""Provides a singleton of an object per thread."""
import threading


class SingletonMixin(object):  # pylint: disable=too-few-public-methods
    """Provides a singleton of an object per thread.

    Usage:
    class ObjectYouWantSingletoned(SingletonMixin):
        # implementation
    instance = ObjectYouWantSingletoned()
    """

    def __new__(cls, *args, **kwargs):
        lock = None

        # Create dictionary if needed
        if not hasattr(cls, '_singleton_instances'):
            lock = threading.Lock()
            with lock:
                if not hasattr(cls, '_singleton_instances'):
                    cls._singleton_instances = {}

        # Create new instance if needed
        key = str(hash(cls))
        if key not in cls._singleton_instances:
            if lock is None:
                lock = threading.Lock()
            with lock:
                if key not in cls._singleton_instances:
                    cls._singleton_instances[key] = super(SingletonMixin, cls) \
                            .__new__(cls, *args, **kwargs)

        return cls._singleton_instances[key]
