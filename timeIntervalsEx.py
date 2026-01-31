from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)


class TimeIntervalsEX:
    # MARK: - Nested type
    @dataclass(frozen=True)
    class Interval:
        start: datetime
        end: datetime

    # MARK: - Date formatters
    _INPUT_FORMAT = "%d-%m-%Y %H:%M"
    _OUTPUT_FORMAT = "%d.%m %H:%M"
    _KYIV_TZ = ZoneInfo("Europe/Kyiv")

    # MARK: - Init / Storage
    def __init__(self) -> None:
        self.intervals: List[TimeIntervalsEX.Interval] = []

    # MARK: - Append with merge
    def append(self, range_: Tuple[str, str]) -> None:
        try:
            start_date = datetime.strptime(range_[0], self._INPUT_FORMAT).replace(
                tzinfo=self._KYIV_TZ
            )
            end_date = datetime.strptime(range_[1], self._INPUT_FORMAT).replace(
                tzinfo=self._KYIV_TZ
            )
        except ValueError:
            return

        if start_date > end_date:
            return

        self.intervals.append(
            TimeIntervalsEX.Interval(start=start_date, end=end_date)
        )
        self._merge_intervals()

    # MARK: - Merge logic
    def _merge_intervals(self) -> None:
        if len(self.intervals) <= 1:
            return

        self.intervals.sort(key=lambda i: i.start)

        merged: List[TimeIntervalsEX.Interval] = []
        current = self.intervals[0]

        for next_interval in self.intervals[1:]:
            if next_interval.start <= current.end:
                current = TimeIntervalsEX.Interval(
                    start=min(current.start, next_interval.start),
                    end=max(current.end, next_interval.end),
                )
            else:
                merged.append(current)
                current = next_interval

        merged.append(current)
        self.intervals = merged

    # MARK: - Interval lookup
    def interval_containing(self, date: datetime) -> Optional[Interval]:
        for interval in self.intervals:
            if interval.start <= date <= interval.end:
                return interval
        return None

    def is_in(self, date: datetime) -> bool:
        return self.interval_containing(date) is not None

    # MARK: - Pretty print
    def pretty_print(self, multiline: bool = False) -> str:
        separator = "\n" if multiline else ""
        return separator.join(
            f"[{interval.start.strftime(self._OUTPUT_FORMAT)}-"
            f"{interval.end.strftime(self._OUTPUT_FORMAT)}]"
            for interval in self.intervals
        )

    def compare(self, compare_to: "TimeIntervalsEX") -> bool:
        logger.debug(f"compare: {compare_to.pretty_print()}")
        now = datetime.now(self._KYIV_TZ)
        soon = now + timedelta(minutes=10)

        logger.debug(f"compare now: {now}, soon: {soon}")

        saved_intervals = self.intervals
        new_intervals = compare_to.intervals

        # New interval(s) appeared
        # Always true
        if len(new_intervals) > len(saved_intervals):
            logger.debug(f"new_intervals > saved_intervals: {len(new_intervals)-len(saved_intervals)}")
            return True

        # Interval(s) missing
        # False if only one is missing, and missing one has already ended (or will end in the next 10 minutes)
        # Otherwise true
        if len(new_intervals) < len(saved_intervals):
            logger.debug(f"new_intervals < saved_intervals: {len(saved_intervals) - len(new_intervals)}")
            # find intervals that are missing in compare_to
            missing = [
                interval for interval in saved_intervals
                if interval not in new_intervals
            ]
            logger.debug(f"missing intervals: {missing}")

            if len(missing) > 1:
                return True
            # False if only missing interval ends before now or within next 10 minutes
            return any(interval.end >= soon for interval in missing)

        # Same number of intervals
        # False only if none changed
        diff_intervals = [
            interval for interval in new_intervals
            if interval not in saved_intervals
        ]

        logger.info(f"diff_intervals len: {len(diff_intervals)}; array:{diff_intervals}")

        if len(diff_intervals) > 0:
            return True

        if len(diff_intervals) == 1 and diff_intervals[0].start > now:
            return True

        return False
