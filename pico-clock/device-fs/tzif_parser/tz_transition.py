from datetime import timedelta


class TimeZoneTransition:
    def __init__(
        self,
        transition_time,
        time_type_infos,
        time_type_indices,
        transition_index,
        wall_standard_flags,
        is_utc_flags,
        timezone_abbrevs,
    ):
        self._transition_time = transition_time
        self._time_type_infos = time_type_infos
        self._time_type_indices = time_type_indices
        self._transition_index = transition_index
        self.time_type_info = time_type_infos[time_type_indices[transition_index]]
        self.wall_standard_flag = (
            wall_standard_flags[time_type_indices[transition_index]]
            if len(wall_standard_flags) > 0
            else None
        )
        self.is_utc = (
            bool(is_utc_flags[time_type_indices[transition_index]])
            if len(is_utc_flags) > 0
            else None
        )
        self.abbreviation = timezone_abbrevs[
            self.time_type_info.abbrev_index :
        ].partition("\x00")[0]

    @property
    def transition_time_local_standard(self):
        if self._transition_index == 0:
            # Prefer a non-DST ttinfo if present, else fall back to index 0
            first_std = None
            for tti in self._time_type_infos:
                if not tti.is_dst:
                    first_std = tti
                    break
            if first_std is None:
                first_std = self._time_type_infos[0]
            return _to_local(self.transition_time_utc, first_std.utc_offset_secs)
        ttinfo = self._time_type_infos[
            self._time_type_indices[self._transition_index - 1]
        ]
        return _to_local(self.transition_time_utc, ttinfo.utc_offset_secs)

    @property
    def transition_time_local_wall(self):
        return _to_local(self.transition_time_utc, self.utc_offset_secs)

    @property
    def transition_time_utc(self):
        return self._transition_time

    @property
    def dst_difference_secs(self):
        if not self.is_dst:
            return 0

        # Prefer the preceding standard ttinfo; fall back to next, then any non-DST entry.
        std_tt = None
        if self._transition_index > 0:
            prev_tt = self._time_type_infos[
                self._time_type_indices[self._transition_index - 1]
            ]
            if not prev_tt.is_dst:
                std_tt = prev_tt

        if std_tt is None and self._transition_index + 1 < len(self._time_type_indices):
            next_tt = self._time_type_infos[
                self._time_type_indices[self._transition_index + 1]
            ]
            if not next_tt.is_dst:
                std_tt = next_tt

        if std_tt is None:
            for tti in self._time_type_infos:
                if not tti.is_dst:
                    std_tt = tti
                    break

        if std_tt is None:
            return 0

        return self.utc_offset_secs - std_tt.utc_offset_secs

    @property
    def dst_difference_hours(self):
        return self.dst_difference_secs / 3600

    @property
    def utc_offset_secs(self):
        return self.time_type_info.utc_offset_secs

    @property
    def utc_offset_hours(self):
        return self.utc_offset_secs / 3600

    @property
    def is_dst(self):
        return self.time_type_info.is_dst


def _to_local(dt_utc, offset_secs):
    """Convert a naive UTC datetime to naive local time by adding offset seconds."""
    return dt_utc + timedelta(seconds=offset_secs)

