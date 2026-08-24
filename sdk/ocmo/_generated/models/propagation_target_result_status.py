from enum import Enum


class PropagationTargetResultStatus(str, Enum):
    ERROR = "error"
    SKIPPED = "skipped"
    UNCHANGED = "unchanged"
    UPDATED = "updated"

    def __str__(self) -> str:
        return str(self.value)
