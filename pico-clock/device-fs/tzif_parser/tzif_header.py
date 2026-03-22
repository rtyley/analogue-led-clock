import struct


class TimeZoneInfoHeader:
    def __init__(
        self,
        version,
        is_utc_flag_count,
        wall_standard_flag_count,
        leap_second_transitions_count,
        transitions_count,
        local_time_type_count,
        timezone_abbrev_byte_count,
    ):
        self.version = version
        self.is_utc_flag_count = is_utc_flag_count
        self.wall_standard_flag_count = wall_standard_flag_count
        self.leap_second_transitions_count = leap_second_transitions_count
        self.transitions_count = transitions_count
        self.local_time_type_count = local_time_type_count
        self.timezone_abbrev_byte_count = timezone_abbrev_byte_count

    @classmethod
    def read(cls, file) -> "TimeZoneInfoHeader":
        format_ = ">4sb15x6I"
        header_size = struct.calcsize(format_)
        header_data = struct.unpack(format_, file.read(header_size))
        (
            magic,
            version_byte,
            is_utc_flag_count,
            wall_standard_flag_count,
            leap_second_count,
            transitions_count,
            local_time_type_count,
            timezone_abbrev_byte_count,
        ) = header_data

        if magic != b"TZif":
            raise ValueError("Invalid TZif file: Magic sequence not found.")

        version = 1 if version_byte == b"\x00" else version_byte - 48 # ord('0')

        return cls(
            version,
            is_utc_flag_count,
            wall_standard_flag_count,
            leap_second_count,
            transitions_count,
            local_time_type_count,
            timezone_abbrev_byte_count,
        )
