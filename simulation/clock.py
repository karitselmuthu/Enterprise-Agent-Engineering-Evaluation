"""A deterministic clock measured in minutes from scenario start."""

from dataclasses import dataclass


@dataclass
class VirtualClock:
    minute: int = 0

    def __post_init__(self) -> None:
        self.seek(self.minute)

    def seek(self, minute: int) -> None:
        if not isinstance(minute, int) or isinstance(minute, bool) or minute < 0:
            raise ValueError("minute must be a nonnegative integer")
        self.minute = minute

    def advance(self, minutes: int) -> None:
        if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes < 0:
            raise ValueError("advance must be a nonnegative integer")
        self.minute += minutes
