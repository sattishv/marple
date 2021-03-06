# -------------------------------------------------------------
# smem.py - interacts with the smem tool.
# June-July 2018 - Franz Nowak
# -------------------------------------------------------------

"""
Interacts with the smem tool.

Calls smem to collect memory data, format it, and has functions that create
data object generators.

"""

__all__ = (
    "MemoryGraph",
)


import asyncio
import datetime
import logging
import re
import time
from typing import NamedTuple

from marple.collect.interface import collecter
from marple.common import data_io, util, exceptions
from marple.common.consts import InterfaceTypes

logger = logging.getLogger(__name__)
logger.debug('Entered module: %s', __name__)


class MemoryGraph(collecter.Collecter):
    """
    Collects sorted memory usage for a specific number of processes.

    Collects multiple datasets based on the supplied frequency and groups them
    based on the collection time.

    """
    class Options(NamedTuple):
        """
        .. attribute:: mode:
            "name", "pid" or "command", to decide the labelling
        .. attribute:: frequency:
            refresh rate for the collection of datasets
        """
        mode: str
        frequency: float

    _DEFAULT_OPTIONS = Options(mode="name", frequency=0.5)
    modes = ["command", "name", "pid"]

    @util.check_kernel_version("2.6.27")
    def __init__(self, time_, options=_DEFAULT_OPTIONS):
        super().__init__(time_, options)

    @util.log(logger)
    @util.Override(collecter.Collecter)
    async def _get_raw_data(self):
        """ Collect raw data asynchronously from smem """
        # Dict for the datapoints to be collected
        datapoints = {}
        # Set the start time
        start_time = time.monotonic()
        current_time = 0.0
        self.start_time = datetime.datetime.now()
        while current_time < self.time:
            if self.options.mode not in self.modes:
                raise ValueError(
                    "mode {} not supported.".format(self.options.mode))

            smem = await asyncio.create_subprocess_shell(
                "smem -c \"{} pss\"".format(self.options.mode),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            out, err = await smem.communicate()
            if smem.returncode != 0:
                # Set an end_time
                raise exceptions.SubprocessedErorred(err.decode())

            datapoints[current_time] = {}

            # Get lines and get rid of the title line (Name       PSS) and the
            # empty line produced by the split
            lines = out.decode().split("\n")[1:-1]
            # TODO: Check why it's in reverse
            for idx in reversed(range(len(lines))):
                line = lines[idx]

                match = re.match(r"\s*(?P<label>\S+(\s\S+)*)\s*"
                                 r"(?P<memory>\d+)", line)
                if match is None:
                    raise IOError("Invalid output format from smem: {}".format(
                        line))

                label = match.group("label")
                memory = float(match.group("memory")) / 1024.0

                if label in datapoints[current_time]:
                    memory += float(datapoints[current_time][label])

                datapoints[current_time][label] = memory

            # Update the clock
            await asyncio.sleep(self.options.frequency)
            current_time = time.monotonic() - start_time

        self.end_time = datetime.datetime.now()
        return datapoints

    @util.log(logger)
    @util.Override(collecter.Collecter)
    def _get_generator(self, raw_data):
        """ Convert raw data to standard datatypes and yield them """
        for key in raw_data:
            for lab in raw_data[key]:
                mem = raw_data[key][lab]
                yield data_io.PointDatum(key, mem, lab)

    @util.log(logger)
    @util.Override(collecter.Collecter)
    async def collect(self):
        """ Collect data asynchronously using smem """
        try:
            raw_data = await self._get_raw_data()
        except exceptions.SubprocessedErorred as se:
            logger.error(str(se))
            return data_io.PointData(None, -1, -1,
                                     InterfaceTypes.MEMTIME, None)

        data = self._get_generator(raw_data)
        data_options = data_io.PointData.DataOptions(
            x_label='Time', y_label='Memory', x_units='s', y_units='MB')
        return data_io.PointData(data, self.start_time, self.end_time,
                                 InterfaceTypes.MEMTIME, data_options)
