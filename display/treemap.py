# -------------------------------------------------------------
# treemap.py - Generates a treemap representation of the data
# July 2018 - Andrei Diaconu, Hrutvik Kanabar
# -------------------------------------------------------------
"""
Displays the collected data as a treemap

"""

__all__ = (
    'Treemap'
)

from util.d3plus import d3IpyPlus as d3
import subprocess
import os
import logging

from common import (
    file,
    util
)
from display.generic_display import GenericDisplay

logger = logging.getLogger(__name__)
logger.debug('Entered module: %s', __name__)


class Treemap(GenericDisplay):
    def __init__(self, depth, inp, out):
        """
        Constructor for the Treemap.

        :param depth:
            the depth of Treemap
        :param inp:
            Input [Stack] file as a string
        :param out;
            Output file as a file object

        """
        self.depth = depth
        self.input = inp
        out.set_options("treemap", "html")
        self.output = str(out)

    @staticmethod
    @util.log(logger)
    def _generate_csv(in_file, out_file):
        """
        Creates a semicolon separated file from a stack parser output.
        The output format will be:
            - first line: Represents the columns (header); first column will
                          represent the value of the stack line; the rest of the
                          columns will be numbers from 1 to the maximum stack
                          depth, representing the groups we use for creating the
                          hierarchies;
            - next lines: values of the above columns, separated by semicolons;
                          the values for the groups will be the function at that
                          depth;
                          example: value;1;2;3 -- first row
                                   5;firefox;[unknown];libxul.so -- second row

        :param in_file: a collapsed stack produced by the stack parser; expects
                        an absolute path
        :param out_file: a semicolon separated file generated from the in_file;
                         expects an absolute path
        """
        max_num_proc = 0
        with open(in_file, "r") as read_file:
            # Skip first line, header
            read_file.readline()

            for line in read_file:
                cnt = line.count(';')
                # If we don't have any ';' characters raise error
                if cnt == 0:
                    print(line)
                    raise ValueError("Invalid format of the file!")
                if max_num_proc < cnt:
                    max_num_proc = cnt
            # Number of fields in a line is 1 plus the number of ';' characters
            max_num_proc += 1

        with open(out_file, "w") as out_file:
            # Header of the csv
            out_file.write("value;" +
                           ";".join([str(i) for i in range(1, max_num_proc + 1)]) +
                           "\n")

            with open(in_file, "r") as read_file:
                # Skip first line, header
                read_file.readline()

                for line in read_file:
                    call_stack = line.replace("#", ";")
                    out_file.write(call_stack)

            return max_num_proc

    @util.Override(GenericDisplay)
    @util.log(logger)
    def show(self):
        """
        Displays the input stack as a treemap using the d3IpyPlus tool. Because
        of the big loading times for big depths, we will use at most DEPTH
        levels

        :param in_file: a stack file
        :param out_file: an html file containing the treemap representation

        """

        # Temp file for the csv file
        temp_file = str(file.TempFileName())
        max_num_proc = self._generate_csv(self.input, temp_file)

        # Generate the ids we use for the hierarchies and the columns of the
        # input file
        ids = []
        for i in range(1, max_num_proc + 1):
            ids.append(str(i))
        cols = ["value"] + ids

        data = d3.from_csv(temp_file, ';', columns=cols)
        tmap = d3.TreeMap(id=ids[0:self.depth], value="value", color="value",
                          legend=True, width=700)
        with open(str(self.output), "w") as out:
            out.write(tmap.dump_html(data))

        username = os.environ['SUDO_USER']
        subprocess.call(["su", "-", "-c", "firefox " +
                         str(self.output), username])