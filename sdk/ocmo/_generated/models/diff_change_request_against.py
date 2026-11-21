from enum import Enum


class DiffChangeRequestAgainst(str, Enum):
    BASE = "base"
    LATEST = "latest"

    def __str__(self) -> str:
        return str(self.value)
