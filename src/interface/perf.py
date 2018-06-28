from subprocess import call, check_output, Popen, PIPE


def collect(t, f=99, filename=None):
    """
    Collect system data using perf
    :param t:
        The ime in seconds for which to collect the data
    :param f:
        The frequency in Hz of taking samples
        The default value is 99 rather than 100 to avoid
        recording in lockstep with some periodic activity.
    :param filename:
        Optional parameter for the user to decide how the file should be stored

    """
    # create file for recording output. TODO: diff file names each time, also user option
    outfile = open("my_file.txt", "w")

    proc = Popen(["perf", "record", "-F", str(f), "-a", "-g" "--" "sleep", str(t)], stdout=outfile)
    # if blocking:
    #    proc.wait()


def collect_sched_all(t):
    """
    Collect all CPU scheduling data using perf sched.

    This will get all the events in the scheduler.
    :param t:
        time in seconds for which to collect the data

    """
    call(["perf", "sched", "record", "sleep", str(t)])


def collect_sched_enter_exit(t):
    """
    Collect relevant CPU scheduling data using perf sched.

    This will get the enter and exit events in the scheduler.
    :param t:
        time in seconds for which to collect the data

    """
    # At the moment same as sched_all
    call(["perf", "sched", "record", "sleep", str(t)])


def map_sched():
    """
    Display the collected scheduling data as a map.

    Each columns represents a CPU core, each entry is
    a process whose name can be found in the legend
    on the right.

    """
    call(["perf", "sched", "map"])


def get_sched_data():
    """
    Get the relevant scheduling data.

    This uses the previously by collect_sched collected data
    to output a list of relevant scheduler events in an ordered fashion.
    Note: this outputs all given events regardless of type.

    :return:
        string of sched event lines of the form pid:cpu:time

    """
    call(["perf", "sched", "script", "-F", "pid", "cpu", "time"])


if __name__ == "__main__":
    collect(1)
