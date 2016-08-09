"""Dummy class for Logger interface. A real Logger should have four methods:
    debug(self, message)
    info(self, message)
    warning(self, message)
    error(self, message)
"""

# pylint: disable=no-self-use


class DummyLogger(object):
    """Implementation of Logger interface for testing."""
    def debug(self, message):
        """Debug message."""
        pass

    def info(self, message):
        """Info message."""
        print(message)

    def warning(self, message):
        """Warning message."""
        print(message)

    def warn(self, message):
        """Warning message."""
        print(message)

    def error(self, message):
        """Error message."""
        print(message)
