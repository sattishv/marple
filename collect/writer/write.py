# -------------------------------------------------------------
# writer/write.py - Saves data objects into a file.
# June-July 2018 - Franz Nowak, Hrutvik Kanabar, Andrei Diaconu
# -------------------------------------------------------------

"""
Saves data objects into a file.

Gets the data that was collected by an interface module and converted into
formatted objects and writes them into a file that was provided by the user.

"""
__all__ = (
    'Writer',
    'create_cpu_event_data_cpel'
)

import logging
import struct
from datetime import datetime

from common import datatypes

logger = logging.getLogger("writer.write")
logger.setLevel(logging.DEBUG)


class Writer:
    def write(self, data, filename):
        with open(filename, "w") as out:
            for datum in data:
                out.write(str(datum) + "\n")


def create_cpu_event_data_cpel(sched_events, filename):
    """
    Saves the event data from the generator in a file in CPEL format.

    :param sched_events:
        An iterator of :class:`SchedEvent` objects.
    :param filename:
        The name of the file into which to store the output.


    """
    logger.info("Enter create_cpu_event_data_cpel.")

    cpel_writer = CpelWriter(sched_events)
    cpel_writer.write(filename)


class CpelWriter:
    """A class that takes event data and converts it to a CPEL file."""

    # ENDIAN_BIT: int value for endianness of the file (0 for big, 1 for little)
    ENDIAN_BIT = 0
    # FILE_VERSION: int value of 1 for showing this is a CPEL file
    FILE_VERSION = 1
    # FILE_STRING_TABLE_NAME: str, name of the (only) file string table (64b).
    FILE_STRING_TABLE_NAME = "FileStrtab" + 54 * "\x00"

    def __init__(self, event_objects):
        """
        Initialise the input data and read in the data

        :param event_objects:
            An iterator of event objects to be processed.

        """
        self.event_objects = event_objects

        # Information for writing the file header (no of sections etc.)
        self.info = dict()

        # Create list attribute for section lengths
        self.section_length = [None, 0, 0, 0, 0, 0]

        # Create attributes for string section data
        self.string_table = dict()
        self._string_resource = ""
        short_table_name = self.FILE_STRING_TABLE_NAME.rstrip("\x00")
        self.string_table[short_table_name] = 0
        self._string_resource += short_table_name
        self.section_length[1] = len(short_table_name)
        self.string_table["%s"] = self.section_length[1] + 1
        self._string_resource += ("\x00" + "%s")
        self.section_length[1] += (len("%s") + 1)

        # Dict for symbol table section
        self.symbol_table = dict()

        # Dicts for event definition section
        self.event_definitions_dict = dict()
        self.event_data_dict = dict()
        # Index for the two above
        self.event_def_index = 0

        # Dict for the track definitions
        self.track_definitions_dict = dict()
        self.track_def_index = 0

        # List of events for event section
        self.event_data = []

        # Int counting the number of sections in the file
        self.no_of_sections = 0

        # fill the above data structures with data from event input.
        self._collect()

        # Reserve attribute for file descriptor
        self.file_descriptor = None

    def _insert_string(self, string_key: str):
        """
        Puts a string into the string table, taking care of updating the index.
        :param string_key:
            A string to be put into the string table.

        """
        if string_key not in self.string_table:
            self.string_table[string_key] = self.section_length[1] + 1
            self.section_length[1] += (len(string_key) + 1)
            self._string_resource += ("\x00" + string_key)

    def _insert_object_strings(self, event_object):
        """
        Puts the string resources of the event object into the string table.

        :param event_object:
            A reference to the currently processed event object.

        """
        # insert datum, track, event_type (not time)
        self._insert_string(event_object.datum)
        self._insert_string(event_object.track)
        self._insert_string(event_object.type)

    def _insert_object_symbols(self, event_object):
        """
        Unused for now.
        :param event_object:
             A reference to the currently processed event object.

        """
        pass

    def _insert_object_event_def(self, event_object):
        """
        Puts the event into the event definition attribute.

        :param event_object:
            A reference to the currently processed event object.

        """
        # event_code event_offset datum_offset
        if event_object.type not in self.event_definitions_dict:
            self.event_definitions_dict[event_object.type] = \
                self.event_def_index
            self.event_def_index += 1

            self.section_length[3] += 12

    def _insert_object_track_def(self, event_object):
        """
        Puts the track into the track definition attribute.

        :param event_object:
            A reference to the currently processed event object.

        """
        # track_id track_format_offset

        if event_object.track not in self.track_definitions_dict:
            self.track_definitions_dict[event_object.track] = \
                self.track_def_index
            self.track_def_index += 1
            self.section_length[4] += 8

    def _insert_object_event_data(self, event_object):
        """
        Puts event data into the event attribute.

        :param event_object:
            A reference to the currently processed event object.
                time: string("d+.d+")

        """
        # time,time (from object) track_id (from track_def_dict) event_code (
        #   from event_def_dict) event_datum (from string table)

        self.event_data.append((event_object.time,
                                self.track_definitions_dict[
                                     event_object.track],
                                self.event_definitions_dict[event_object.type],
                                self.string_table[event_object.datum]))

        self.section_length[5] += 20

    def _collect(self):
        """
        Processes the data and puts it into data structures.

        """
        for event_object in self.event_objects:
            self._insert_object_strings(event_object)
            # self._insert_object_symbols(event_object)
            self._insert_object_event_def(event_object)
            self._insert_object_track_def(event_object)
            self._insert_object_event_data(event_object)

        self.no_of_sections += 4

    def _write_file_header(self):
        """Writes the file header into the Cpel file."""
        # Format:
        # 0x0 	    Endian bit (0x80), File Version, 7 bits (0x1...0x7F)
        # 0x1 	    Unused, 8 bits
        # 0x2-0x3 	Number of sections (16 bits) (NSECTIONS)
        # 0x4 	    File date (32-bits) (POSIX "epoch" format)

        # Calculate the file info byte
        first_byte = self.ENDIAN_BIT << 7 | self.FILE_VERSION
        # Insert number of sections
        number_of_sections = self.no_of_sections
        # Use POSIX "epoch" format for date
        file_date = int(datetime.now().timestamp())
        # Just date: file_date = int(datetime.combine(date.today(),
        #   time(0)).timestamp())

        header = struct.pack(">cxhi", bytes([first_byte]), number_of_sections,
                             file_date)

        self.file_descriptor.write(header)

    def _write_tld(self, section_type_nr: int, section_length: int):
        """
        Writes the type and the length of the following section into file.

        :param section_type_nr:
            The identifier of the section type.
        :param section_length:
            The length of the section.

        """
        tld = struct.pack(">ii", section_type_nr, section_length)
        self.file_descriptor.write(tld)

    def _write_strings(self):
        """Writes the string table into the file"""
        self.file_descriptor.write(bytearray(self._string_resource, "ascii"))

    def _write_symbols(self):
        """
        Not needed now.
        Writes the symbol table into the file.

        """
        # struct symbol_section_entry {
        #     unsigned long value;
        #     unsigned long name_offset_in_string_table;
        # };
        pass

    def _write_event_def(self):
        """Writes the event definition section into the file"""
        # struct event_definition_entry {
        #     unsigned long event_code;
        #     unsigned long event_format_offset_in_string_table;
        #     unsigned long datum_format_offset_in_string_table;
        # };

        # sort by index and write into file
        for event_def in sorted(
                self.event_definitions_dict.items(),
                key=(lambda x: x[1])):

            event_code = event_def[1]
            event_format = self.string_table[event_def[0]]
            event_data_format = self.string_table["%s"]
            self.file_descriptor.write(struct.pack(">LLL", event_code,
                                                   event_format,
                                                   event_data_format))

    def _write_track_def(self):
        """Writes the track definition section into the file"""
        # struct track_definition {
        #     unsigned long track_id;
        #     unsigned long track_format_offset_in_string_table;
        # };

        # Sort by id and write
        for track_def in sorted(
                self.track_definitions_dict.items(),
                key=(lambda x: x[0])):
            # import pdb; pdb.set_trace()

            track_id = track_def[1]
            track_format = self.string_table[track_def[0]]
            self.file_descriptor.write(struct.pack(">LL", track_id,
                                                   track_format))

    def _write_events(self):
        """Writes the event data to disk"""
        # struct event_entry {
        # 	unsigned long time[2];
        # 	unsigned long track;
        # 	unsigned long event_code;
        # 	unsigned long event_datum;
        # };

        # Just write
        for event in self.event_data:
            (time, track_id, event_code, event_datum) = event
            # import pdb; pdb.set_trace()
            time0, time1 = self._convert_time(time)
            data = struct.pack(">LLLLL", time0, time1, track_id, event_code,
                               event_datum)
            self.file_descriptor.write(data)

    def _write_section_header(self, no_of_entries, event_section=False):
        """
        Writes the table name before the start of a section

        :param no_of_entries:
            The number of entries the section has.
        :param event_section:
            Optional flag to indicate that the sectionn is an event section.

        """
        self.file_descriptor.write(bytearray(self.FILE_STRING_TABLE_NAME,
                                             "ascii"))
        self.file_descriptor.write(struct.pack(">L", no_of_entries))

        if event_section:
            # Write a number for ticks per microsecond:
            self.file_descriptor.write(struct.pack(">L", 1000000))

    @staticmethod
    def _convert_time(time):
        time0 = time >> 32
        time1 = time & 2 ** 32 - 1
        return time0, time1

    def _pad_strings(self):
        """Makes sure the string section is padded to the nearest four bytes"""
        padnum = 4 - (len(self._string_resource) % 4)
        for _ in range(padnum):
            self._string_resource += "\x00"
            self.section_length[1] += 1

    def write(self, filename):
        """
        Writes the data to disk in a CPEL file.

        :param filename:
            The name of the output file to which to write the data.

        """
        # Write linearly from data structures
        with open(filename, "wb") as file_:
            self.file_descriptor = file_

            # Header
            self._write_file_header()

            # String Table
            self._pad_strings()
            self._write_tld(1, self.section_length[1])
            self._write_strings()

            # Event Definition Section
            # Add 68 for the section header (table name and length)
            self._write_tld(3, self.section_length[3] + 68)
            self._write_section_header(len(self.event_definitions_dict))
            self._write_event_def()

            # Track Definition Section
            self._write_tld(4, self.section_length[4] + 68)
            self._write_section_header(len(self.track_definitions_dict))
            self._write_track_def()

            # Event Section
            # Add 72 for section header (table name, length and ticks per us)
            self._write_tld(5, self.section_length[5] + 72)
            self._write_section_header(len(self.event_data), event_section=True)
            self._write_events()


if __name__ == "__main__":
    create_cpu_event_data_cpel([datatypes.SchedEvent(datum="test_name (pid: "
                                                           "1234)",
                                                     track="cpu 2",
                                                     time=11112221,
                                                     type="event_type"
                                                     ),
                                datatypes.SchedEvent(datum="test_name2 (pid: "
                                                           "1234)",
                                                     track="cpu 1",
                                                     time=11112222,
                                                     type="event_type")],
                               "../test/converter/example_scheddata.cpel")
