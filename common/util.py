# -------------------------------------------------------------
# util_display.py - various utilities
# July 2018 - Andrei Diaconu, Hrutvik Kanabar
# -------------------------------------------------------------

"""Various utilities"""

import platform
import re

import common.exceptions as exceptions


def check_kernel_version(required_kernel):
    """
    Decorator function that checks if the target kernel supports the interface
    Raises a NotSupportedException if the kernel is not supported
    :param: required_kernel:
        The required kernel for the interface

    """
    def wrap(f):
        def wrapped_check(*args):
            target_kernel = platform.release()
            delimited_rk = re.split('\.|-', required_kernel)
            delimited_tk = re.split('\.|-', target_kernel)
            if delimited_tk[0:3] < delimited_rk[0:3]:
                raise exceptions.NotSupportedException("Kernel not supported",
                                                       required_kernel)
            return f(*args)
        return wrapped_check
    return wrap


def Override(superclass):
    def overrider(method):
        assert(method.__name__ in dir(superclass))
        return method
    return overrider


def log(logger):
    """
    A decorator wrapping a function for logging.

    Logs function entry and exit at level DEBUG, any exceptions that occur
    at level EXCEPTION, and arguments/optional arguments at level DEBUG.

    :param logger:
        The logging object to log to.

    """
    def decorator(fn):
        from functools import wraps

        @wraps(fn)
        def wrapper(*args, **kwargs):
            logger.debug('Entering function: {}'.format(fn.__name__))
            args_list = list(args)
            logger.debug("Args: {:<90.90s}...".format(str(args_list)))
            if kwargs != {}:
                logger.debug("Kwargs: {:<90.90s}...".format(str(kwargs)))
            try:
                # Apply the function
                out = fn(*args, **kwargs)
            except Exception:
                # Catch and log any exceptions
                logger.exception("Exception in {}".format(fn.__name__))
                # Re-raise the exception
                raise

            logger.debug("Leaving function: {}".format(fn.__name__))

            # Return the return value
            return out

        return wrapper
    return decorator
