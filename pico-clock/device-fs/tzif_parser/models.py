from datetime import datetime


class TimeZoneResolution:
    """
    Resolution of a timezone at a specific instant.
    """

    def __init__(
        self,
        timezone_name: str,
        resolution_time: datetime,  # tz-aware UTC
        local_time: datetime,  # naive local wall time
        utc_offset_secs: int,
        is_dst: bool,
        abbreviation: str,
        dst_difference_secs: int,
        next_transition=None,
    ):
        self.timezone_name = timezone_name
        self.resolution_time = resolution_time
        self.local_time = local_time
        self.utc_offset_secs = utc_offset_secs
        self.is_dst = is_dst
        self.abbreviation = abbreviation
        self.dst_difference_secs = dst_difference_secs
        self.next_transition = next_transition

    def _replace(self, **kwargs):
        """Return a copy with specified fields replaced."""
        d = dict(
            timezone_name=self.timezone_name,
            resolution_time=self.resolution_time,
            local_time=self.local_time,
            utc_offset_secs=self.utc_offset_secs,
            is_dst=self.is_dst,
            abbreviation=self.abbreviation,
            dst_difference_secs=self.dst_difference_secs,
            next_transition=self.next_transition,
        )
        d.update(kwargs)
        return TimeZoneResolution(**d)


# WallStandardFlag constants (replaces Enum)
WALL = 0
STANDARD = 1


class LeapSecondTransition:
    """
    Represents a leap second entry in a TZif file.
    """

    def __init__(self, transition_time, correction, is_expiration=False):
        self.transition_time = transition_time
        self.correction = correction
        self.is_expiration = is_expiration


class TimeTypeInfo:
    """
    Represents a ttinfo structure in a TZif file.
    """

    def __init__(self, utc_offset_secs, is_dst, abbrev_index):
        self.utc_offset_secs = utc_offset_secs
        self.is_dst = is_dst
        self.abbrev_index = abbrev_index
