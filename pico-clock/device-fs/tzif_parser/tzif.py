import os
from datetime import timedelta

from .models import TimeZoneResolution
from .posix import PosixTzInfo
from .tzif_body import TimeZoneInfoBody
from .tzif_header import TimeZoneInfoHeader


class TimeZoneResolutionCache:
    def __init__(self, cache_key, resolution):
        self.cache_key = cache_key
        self.resolution = resolution


class TimeZoneInfo:
    def __init__(
        self,
        timezone_name,
        filepath,
        header_data,
        body_data,
        v2_header_data=None,
        v2_body_data=None,
        posix_tz_info=None,
    ):
        self.timezone_name = timezone_name
        self.filepath = filepath
        self._posix_tz_info = posix_tz_info
        self._header_data = header_data
        self._body_data = body_data
        self._v2_header_data = v2_header_data
        self._v2_body_data = v2_body_data
        self._last_resolution = None

    @property
    def version(self):
        return self.header.version

    @property
    def header(self):
        if self._header_data is None:
            raise ValueError("No header data available")
        if self._header_data.version < 2:
            return self._header_data
        if self._v2_header_data is None:
            raise ValueError("No header data available")
        return self._v2_header_data

    @property
    def body(self):
        if self._body_data is None:
            raise ValueError("No body data available")
        if self.version < 2:
            return self._body_data
        if self._v2_body_data is None:
            raise ValueError("No body data available")
        return self._v2_body_data

    @property
    def footer(self):
        return self._posix_tz_info

    @staticmethod
    def _local_time(dt_utc, offset_secs):
        """Naive local wall clock for a naive UTC datetime plus offset seconds."""
        return dt_utc + timedelta(seconds=offset_secs)

    def _cache_resolution(
        self,
        dt_utc,
        dt_utc_key,
        offset_secs,
        is_dst,
        abbr,
        delta,
        next_transition,
    ):
        local = self._local_time(dt_utc, offset_secs)
        resolution = TimeZoneResolution(
            self.timezone_name,
            dt_utc,
            local,
            offset_secs,
            is_dst,
            abbr,
            delta,
            next_transition=next_transition,
        )
        self._last_resolution = TimeZoneResolutionCache(dt_utc_key, resolution)
        return resolution

    @staticmethod
    def _as_utc(dt):
        """Return the datetime as-is (all datetimes are treated as naive UTC in MicroPython)."""
        return dt

    @staticmethod
    def _cache_key(dt_utc):
        """Cache key (MicroPython datetime already has no sub-second precision)."""
        return dt_utc

    @staticmethod
    def _initial_tt_state(body):
        """
        Pick the standard ttinfo if present (otherwise the first ttinfo) and
        return its offset, dst delta, abbreviation, and dst flag.
        """
        std = None
        for x in body.time_type_infos:
            if not x.is_dst:
                std = x
                break
        tt = std if std is not None else body.time_type_infos[0]
        delta = (
            (tt.utc_offset_secs - std.utc_offset_secs) if (tt.is_dst and std) else 0
        )
        abbr = body.get_abbrev_by_index(tt.abbrev_index)
        return tt.utc_offset_secs, delta, abbr, tt.is_dst

    @staticmethod
    def _posix_offsets(posix_info):
        """
        Return (standard offset, dst offset, dst delta) in seconds
        derived from a PosixTzInfo footer.
        """
        std = posix_info.utc_offset_secs
        dst_offset = (
            posix_info.dst_offset_secs
            if posix_info.dst_offset_secs is not None
            else std + 3600
        )
        return std, dst_offset, dst_offset - std

    def _posix_footer_state(self, dt_utc):
        footer = self.footer
        if footer is None:
            return None

        std, dst_offset, dst_delta = self._posix_offsets(footer)

        # POSIX rules compare using naive local wall time in standard offset
        local_std = self._local_time(dt_utc, std)
        in_dst = False
        if footer.dst_start is not None and footer.dst_end is not None:
            start = footer.dst_start.to_datetime(local_std.year)
            end = footer.dst_end.to_datetime(local_std.year) - timedelta(
                seconds=dst_delta
            )
            if start < end:
                in_dst = start <= local_std < end
            else:
                # wrap over new year (southern hemisphere rule)
                in_dst = (local_std >= start) or (local_std < end)

        if in_dst:
            offset_secs = dst_offset
            delta = dst_delta
            abbr = footer.dst_abbrev or footer.standard_abbrev
        else:
            offset_secs = std
            delta = 0
            abbr = footer.standard_abbrev

        return offset_secs, delta, abbr, in_dst

    def _next_posix_transition_utc(self, dt_utc):
        """
        Compute the next transition instant in UTC using the POSIX footer rules,
        for a given UTC datetime strictly after the end of the TZif transition body.

        Returns a timezone-aware UTC datetime, or None if no DST rules exist.
        """
        footer = self.footer
        if footer is None:
            return None
        if footer.dst_start is None or footer.dst_end is None:
            return None

        std, dst_offset, dst_delta = self._posix_offsets(footer)
        dst_delta_td = timedelta(seconds=dst_delta)

        # Work in "standard-time local wall clock" coordinates, same as resolve()
        local_std = self._local_time(dt_utc, std)
        year = local_std.year

        candidates = []

        # Look for the next boundary in this year or next year
        for y in (year, year + 1):
            try:
                start_y = footer.dst_start.to_datetime(y)
                end_y_dst = footer.dst_end.to_datetime(y)
            except ValueError:
                # Out-of-range year for datetime, just skip
                continue

            if start_y > local_std:
                candidates.append((start_y, start_y, std))

            end_y_std = end_y_dst - dst_delta_td
            if end_y_std > local_std:
                candidates.append((end_y_std, end_y_dst, dst_offset))

        if not candidates:
            return None

        # Find minimum by first element of tuple
        best = candidates[0]
        for c in candidates[1:]:
            if c[0] < best[0]:
                best = c
        _, local_wall, boundary_offset = best
        boundary_delta = timedelta(seconds=boundary_offset)
        next_utc = local_wall - boundary_delta
        return next_utc

    @staticmethod
    def _next_meaningful_body_transition(
        body,
        start_index,
        current_offset,
        current_dst_diff,
        current_abbr,
    ):
        """
        Find the next transition that changes the effective ttinfo as defined by
        zoneinfo (_ttinfo equality is utcoff/dstoff/tzname).
        Some TZif files carry duplicate ttinfos; those are skipped.
        """
        for i in range(start_index, len(body.transitions)):
            tr = body.transitions[i]
            if (
                tr.utc_offset_secs != current_offset
                or tr.dst_difference_secs != current_dst_diff
                or tr.abbreviation != current_abbr
            ):
                return tr.transition_time_utc
        return None

    def resolve(self, dt):
        """
        Resolve this timezone at a given instant.
        Accepts naive (interpreted as UTC) or aware (converted to UTC).
        Returns a TimeZoneResolution with tz-aware UTC `resolution_time`,
        naive local wall `local_time`, and `next_transition` as the UTC datetime
        of the next transition if one is known.
        """
        dt_utc = self._as_utc(dt)
        dt_utc_key = self._cache_key(dt_utc)

        # Check cache
        if self._last_resolution is not None:
            cached_key = self._last_resolution.cache_key
            cached_resolution = self._last_resolution.resolution

            # Exact match: fast path
            if cached_key == dt_utc_key:
                off = cached_resolution.utc_offset_secs
                local = self._local_time(dt_utc, off)
                return cached_resolution._replace(
                    resolution_time=dt_utc,
                    local_time=local,
                )

            next_transition = cached_resolution.next_transition

            # Use range caching when we actually know the next transition
            # and the requested time is between the cached resolution_time
            # and the next_transition.
            if next_transition is not None and cached_key <= dt_utc_key < next_transition:
                off = cached_resolution.utc_offset_secs
                local = self._local_time(dt_utc, off)

                # Build a new resolution for this dt_utc, but reuse the same offset,
                # DST flag, abbr, delta, and next_transition.
                return cached_resolution._replace(
                    resolution_time=dt_utc,
                    local_time=local,
                )

        body = self.body

        # Case 0: No transitions at all => single ttinfo applies
        if not body.transitions:
            posix_state = self._posix_footer_state(dt_utc)
            offset_secs, delta, abbr, in_dst = posix_state or self._initial_tt_state(body)

            next_transition = self._next_posix_transition_utc(dt_utc)

            return self._cache_resolution(
                dt_utc,
                dt_utc_key,
                offset_secs,
                in_dst,
                abbr,
                delta,
                next_transition,
            )

        first = body.transitions[0]
        last = body.transitions[-1]

        # Case 1: Before first transition
        if dt_utc < first.transition_time_utc:
            offset_secs, delta, abbr, in_dst = self._initial_tt_state(body)

            next_transition = self._next_meaningful_body_transition(
                body, 0, offset_secs, delta, abbr
            )

            return self._cache_resolution(
                dt_utc,
                dt_utc_key,
                offset_secs,
                in_dst,
                abbr,
                delta,
                next_transition,
            )

        # Case 2: Between transitions (inclusive of the last transition instant)
        if dt_utc <= last.transition_time_utc:
            tr_index = body.find_transition_index(dt_utc)
            if tr_index is None:
                raise ValueError("No valid transition found for the given datetime")
            tr = body.transitions[tr_index]
            offset_secs = tr.utc_offset_secs
            delta = tr.dst_difference_secs if tr.is_dst else 0

            # Next body transition, if there is one.
            next_transition = self._next_meaningful_body_transition(
                body, tr_index + 1, offset_secs, delta, tr.abbreviation
            )

            if next_transition is None and self.footer is not None:
                # Fall back to POSIX rules after the body ends.
                next_transition = self._next_posix_transition_utc(dt_utc)

            return self._cache_resolution(
                dt_utc,
                dt_utc_key,
                offset_secs,
                tr.is_dst,
                tr.abbreviation,
                delta,
                next_transition,
            )

        # Case 3: After the last transition, use POSIX footer if present
        posix_state = self._posix_footer_state(dt_utc)
        if posix_state is not None:
            offset_secs, delta, abbr, in_dst = posix_state

            # Now that we're past the end of the TZif body, use the POSIX rules
            # to find the next transition.
            next_transition = self._next_posix_transition_utc(dt_utc)

            return self._cache_resolution(
                dt_utc,
                dt_utc_key,
                offset_secs,
                in_dst,
                abbr,
                delta,
                next_transition,
            )

        # Case 4: No footer; stick to the last known offset, no further transitions known
        offset_secs = last.utc_offset_secs
        delta = last.dst_difference_secs if last.is_dst else 0
        next_transition = None
        return self._cache_resolution(
            dt_utc,
            dt_utc_key,
            offset_secs,
            last.is_dst,
            last.abbreviation,
            delta,
            next_transition,
        )

    def local(self, dt):
        """Naive local wall time at `dt`."""
        return self.resolve(dt).local_time

    def is_dst(self, dt):
        return self.resolve(dt).is_dst

    def utc_offset_secs(self, dt):
        return self.resolve(dt).utc_offset_secs

    def dst_difference_secs(self, dt):
        return self.resolve(dt).dst_difference_secs

    def abbreviation(self, dt):
        return self.resolve(dt).abbreviation

    def next_transition(self, dt):
        return self.resolve(dt).next_transition

    @classmethod
    def _read_from_fileobj(cls, file, timezone_name, filepath):
        header_data = TimeZoneInfoHeader.read(file)
        body_data = TimeZoneInfoBody.read(file, header_data)
        if header_data.version < 2:
            return cls(timezone_name, filepath, header_data, body_data)

        v2_header_data = TimeZoneInfoHeader.read(file)
        v2_body_data = TimeZoneInfoBody.read(
            file, v2_header_data, v2_header_data.version
        )
        v2_posix_string = PosixTzInfo.read(file)

        return cls(
            timezone_name,
            filepath,
            header_data,
            body_data,
            v2_header_data,
            v2_body_data,
            v2_posix_string,
        )

    @classmethod
    def read(cls, timezone_name):
        """
        Load a timezone by name: check TZDIR, default tz paths, then bundled
        zoneinfo files. Rejects absolute paths.
        """
        if timezone_name.startswith("/"):
            raise ValueError(
                "Absolute paths are not allowed in TimeZoneInfo.read(); use from_path() instead."
            )

        normalized_name = cls._validate_timezone_key(timezone_name)

        search_paths = []
        tzdir_override = os.environ.get("TZDIR") if hasattr(os, "environ") else None
        if tzdir_override:
            search_paths.append(tzdir_override)
        search_paths.extend(cls._compute_default_tzpath())

        for tz_root in search_paths:
            candidate = tz_root + "/" + normalized_name
            try:
                st = os.stat(candidate)
                # Check it's a file (not a directory) - stat[0] bit 15..12 = type
                if st[0] & 0x8000:  # regular file
                    with open(candidate, "rb") as file:
                        return cls._read_from_fileobj(file, timezone_name, candidate)
            except OSError:
                pass

        raise FileNotFoundError("No time zone found with key {}".format(repr(timezone_name)))

    @classmethod
    def from_path(cls, path, timezone_name=None):
        """Read a TZif file directly from an absolute filesystem path."""
        with open(path, "rb") as file:
            return cls._read_from_fileobj(file, timezone_name or path, path)

    def __repr__(self):
        return (
            "TimeZoneInfo(timezone_name={}, "
            "filepath={}, "
            "header_data={}, "
            "body_data={}, "
            "v2_header_data={}, "
            "v2_body_data={}, "
            "posix_tz_info={})".format(
                repr(self.timezone_name),
                repr(self.filepath),
                repr(self._header_data),
                repr(self._body_data),
                repr(self._v2_header_data),
                repr(self._v2_body_data),
                repr(self._posix_tz_info),
            )
        )

    @staticmethod
    def _compute_default_tzpath():
        if hasattr(os, "environ"):
            env_var = os.environ.get("PYTHONTZPATH")
            if env_var:
                return tuple(path for path in env_var.split(":") if path)

        # Fallback paths - include common paths and the bundled zoneinfo
        return (
            "/usr/share/zoneinfo",
            "/usr/share/lib/zoneinfo",
            "/etc/zoneinfo",
        )

    @staticmethod
    def _validate_timezone_key(key):
        if key.startswith("/"):
            raise ValueError("Absolute paths are not allowed as timezone keys")

        # Reject path traversal attempts
        parts = key.split("/")
        for part in parts:
            if part in ("", ".", ".."):
                raise ValueError("Invalid timezone name: {}".format(repr(key)))

        return key
