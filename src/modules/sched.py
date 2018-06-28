from src.interface import perf


def collect_all(t, filename):
    """
    Uses perf module to collect scheduling data

    :param t:
        The time in seconds for which to collect the data.
    :param filename:
        The location where the file is stored.

    """
    perf.collect_sched_all(t)
    perf.get_sched_data(filename)
