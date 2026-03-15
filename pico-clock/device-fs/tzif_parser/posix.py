import re
from datetime import datetime, timedelta


class PosixTzJulianDateTime:
    def __init__(self, day_of_year, hour, minute, second):
        self.day_of_year = day_of_year
        self.hour = hour
        self.minute = minute
        self.second = second

    def _is_leap_year(self, year):
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

    def to_datetime(self, year):
        # Jn excludes Feb 29. On leap years, days >= 60 are shifted by +1.
        base = datetime(year, 1, 1)
        day_index = self.day_of_year - 1
        if self._is_leap_year(year) and self.day_of_year >= 60:
            day_index += 1
        return base + timedelta(
            days=day_index, seconds=self.hour * 3600 + self.minute * 60 + self.second
        )


class PosixTzOrdinalDateTime:
    def __init__(self, day_index, hour, minute, second):
        self.day_index = day_index  # 0..365 (includes Feb 29)
        self.hour = hour
        self.minute = minute
        self.second = second

    def to_datetime(self, year):
        base = datetime(year, 1, 1)
        return base + timedelta(
            days=self.day_index,
            seconds=self.hour * 3600 + self.minute * 60 + self.second,
        )


class PosixTzDateTime:
    def __init__(self, month, week, weekday, hour, minute, second):
        self.month = month
        self.week = week  # 1..5 (5 = last)
        self.weekday = weekday  # POSIX: Sunday=0 ... Saturday=6
        self.hour = hour
        self.minute = minute
        self.second = second

    def to_datetime(self, year: int) -> datetime:
        # Convert POSIX weekday (Sun=0..Sat=6) to Python weekday (Mon=0..Sun=6)
        py_weekday = (self.weekday - 1) % 7  # Sun(0)->6, Mon(1)->0, ... Sat(6)->5

        # 1) Find first occurrence of py_weekday on/after the 1st of the month
        first_of_month = datetime(year, self.month, 1)
        first_wd = first_of_month.weekday()  # Mon=0..Sun=6
        delta = (py_weekday - first_wd) % 7
        first_occurrence = first_of_month + timedelta(days=delta)

        if self.week < 5:
            # 2) w-th occurrence (1-based): add 7*(w-1) days
            target = first_occurrence + timedelta(days=7 * (self.week - 1))
        else:
            # 3) Last occurrence: step to next month, back up to the last py_weekday
            if self.month == 12:
                next_month_first = datetime(year + 1, 1, 1)
            else:
                next_month_first = datetime(year, self.month + 1, 1)
            # last day of month
            last_of_month = next_month_first - timedelta(days=1)
            last_wd = last_of_month.weekday()
            back = (last_wd - py_weekday) % 7
            target = last_of_month - timedelta(days=back)

        target = target.replace(hour=0, minute=0, second=0)
        offset = timedelta(seconds=self.hour * 3600 + self.minute * 60 + self.second)
        return target + offset


def _split_posix_sections(posix_bytes: bytes) -> tuple[bytes, bytes, bytes]:
    sections: list[bytes] = []
    current = bytearray()
    depth = 0

    for b in posix_bytes:
        if b == ord("<"):
            depth += 1
        elif b == ord(">"):
            if depth == 0:
                raise ValueError("Unmatched '>' in POSIX TZ string")
            depth -= 1
        elif b == ord(",") and depth == 0:
            sections.append(bytes(current))
            current = bytearray()
            continue

        current.append(b)

    if depth != 0:
        raise ValueError("Unmatched '<' in POSIX TZ string")

    sections.append(bytes(current))

    if len(sections) == 1:
        return sections[0], b"", b""
    if len(sections) == 2:
        return sections[0], sections[1], b""
    if len(sections) == 3:
        return sections[0], sections[1], sections[2]

    raise ValueError("Too many comma-separated sections in POSIX TZ string")


class PosixTzInfo:
    def __init__(
        self,
        posix_string,
        standard_abbrev,
        utc_offset_secs,
        dst_abbrev,
        dst_offset_secs,
        dst_start,
        dst_end,
    ):
        self.posix_string = posix_string
        self.standard_abbrev = standard_abbrev
        self.utc_offset_secs = utc_offset_secs
        self.dst_abbrev = dst_abbrev
        self.dst_offset_secs = dst_offset_secs
        self.dst_start = dst_start
        self.dst_end = dst_end

    @property
    def utc_offset_hours(self):
        return self.utc_offset_secs / 3600

    @property
    def dst_offset_hours(self):
        if self.dst_offset_secs is None:
            return None
        return self.dst_offset_secs / 3600

    @property
    def dst_difference_secs(self):
        if self.dst_offset_secs is None:
            return None
        return self.dst_offset_secs - self.utc_offset_secs

    @property
    def dst_difference_hours(self):
        if self.dst_difference_secs is None:
            return None
        return self.dst_difference_secs / 3600

    @classmethod
    def read(cls, file):
        # Adapted from zoneinfo._zoneinfo._parse_tz_str
        _ = file.readline()
        posix_line = file.readline()
        if posix_line == b"":
            return None

        posix_string = posix_line.rstrip(b"\n\x00")
        if not posix_string:
            return None

        local_tz, dst_start, dst_end = _split_posix_sections(posix_string)
        local_tz_str = local_tz.decode("utf-8")
        print(f"local_tz_str=${local_tz_str}")
        local_tz_parser = re.compile(
            r"([^<0-9:.+-]+|<[^>]+>)"
            r"(?:"
            r"([+-]?\d{1,3}(?::\d{2}(?::\d{2})?)?)"
            r"(?:"
            r"([^0-9:.+-]+|<[^>]+>)"
            r"([+-]?\d{1,3}(?::\d{2}(?::\d{2})?)?)?"
            r")?"
            r")?"
        )
        local_tz_match = local_tz_parser.match(local_tz_str)
        if local_tz_match is None or local_tz_match.group(0) != local_tz_str:
            raise ValueError("{} is not a valid TZ string".format(local_tz))

        standard_abbrev = local_tz_match.group(1).strip("<>")
        utc_offset = local_tz_match.group(2)
        if utc_offset is None:
            raise ValueError("{} is missing required standard offset".format(repr(local_tz)))
        utc_offset_secs = cls._read_offset(utc_offset)
        dst_abbrev = local_tz_match.group(3)
        if dst_abbrev:
            dst_abbrev = dst_abbrev.strip("<>")
        dst_offset = local_tz_match.group(4)
        if dst_offset:
            dst_offset_secs = cls._read_offset(dst_offset)
        elif dst_abbrev:
            dst_offset_secs = utc_offset_secs + 3600
        else:
            dst_offset_secs = None
        posix_string = posix_string.decode("utf-8")
        dst_start = cls._read_dst_transition_datetime(dst_start.decode("utf-8"))
        dst_end = cls._read_dst_transition_datetime(dst_end.decode("utf-8"))

        return cls(
            posix_string,
            standard_abbrev,
            utc_offset_secs,
            dst_abbrev,
            dst_offset_secs,
            dst_start,
            dst_end,
        )

    @classmethod
    def _read_offset(cls, posix_offset):
        # Adapted from zoneinfo._zoneinfo._parse_tz_delta
        # Groups: 1=sign, 2=h, 3=:mm[:ss], 4=m, 5=:ss, 6=s
        offset_parser = re.compile(
            r"([+-])?(\d{1,3})(:(\d{2})(:(\d{2}))?)?",
        )
        offset_match = offset_parser.match(posix_offset)
        if offset_match is None or offset_match.group(0) != posix_offset:
            raise ValueError("{} is not a valid offset".format(posix_offset))

        h = int(offset_match.group(2) or 0)
        m = int(offset_match.group(4) or 0)
        s = int(offset_match.group(6) or 0)

        # POSIX constraints:
        # - hours 0..24 (not >24)
        # - minutes/seconds 0..59
        # - if hours == 24, then minutes == seconds == 0
        if h > 24:
            raise ValueError("Offset hours must be in [0, 24]: {}".format(posix_offset))
        if not (0 <= m < 60 and 0 <= s < 60):
            raise ValueError(
                "Offset minutes/seconds must be in [0, 59]: {}".format(posix_offset)
            )
        if h == 24 and (m != 0 or s != 0):
            raise ValueError("24-hour offsets must be 24:00[:00]: {}".format(posix_offset))

        total = h * 3600 + m * 60 + s
        # POSIX sign convention: positive means WEST of UTC => negative seconds
        if offset_match.group(1) != "-":
            total = -total

        return total

    @classmethod
    def _read_dst_transition_datetime(cls, posix_datetime):
        date, *time_parts = posix_datetime.split("/", 1)
        t = time_parts[0] if time_parts else None
        trans_time = cls._read_dst_transition_time(t) if t else (2, 0, 0)

        if not date:
            return None

        if date.startswith("M"):
            m = re.match(r"M(\d{1,2})\.(\d)\.(\d)$", date)
            if m is None:
                raise ValueError("Invalid dst start/end date: {}".format(posix_datetime))
            month = int(m.group(1))
            week = int(m.group(2))
            weekday = int(m.group(3))
            if not (1 <= month <= 12 and 1 <= week <= 5 and 0 <= weekday <= 6):
                raise ValueError("Invalid M<m>.<w>.<d>: {}".format(posix_datetime))
            return PosixTzDateTime(month, week, weekday, *trans_time)

        if date.startswith("J"):
            n = int(date[1:])
            if not (1 <= n <= 365):
                raise ValueError("J<n> must be 1..365: {}".format(posix_datetime))
            return PosixTzJulianDateTime(n, *trans_time)

        # Plain numeric day-of-year (0..365), includes Feb 29
        if date.isdigit():
            n = int(date)
            if not (0 <= n <= 365):
                raise ValueError("<n> must be 0..365: {}".format(posix_datetime))
            return PosixTzOrdinalDateTime(n, *trans_time)

        raise ValueError("Invalid dst start/end date: {}".format(posix_datetime))

    @classmethod
    def _read_dst_transition_time(cls, time_str):
        # Adapted from zoneinfo._zoneinfo._parse_transition_time
        # Groups: 1=sign, 2=h, 3=:mm[:ss], 4=m, 5=:ss, 6=s
        transition_time_parser = re.compile(
            r"([+-])?(\d{1,3})(:(\d{2})(:(\d{2}))?)?",
        )
        match = transition_time_parser.match(time_str)
        if match is None or match.group(0) != time_str:
            raise ValueError("Invalid time: {}".format(time_str))

        h = int(match.group(2) or 0)
        m = int(match.group(4) or 0)
        s = int(match.group(6) or 0)

        # bounds: hours 0..167, minutes/seconds 0..59
        if h > 167:
            raise ValueError("Hour must be in [0, 167]: {}".format(time_str))
        if not (0 <= m < 60 and 0 <= s < 60):
            raise ValueError("Minutes/seconds must be in [0, 59]: {}".format(time_str))

        if match.group(1) == "-":
            h, m, s = -h, -m, -s

        return h, m, s
