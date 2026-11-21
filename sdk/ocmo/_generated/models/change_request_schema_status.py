from enum import Enum


class ChangeRequestSchemaStatus(str, Enum):
    APPLIED = "applied"
    OPEN = "open"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

    def __str__(self) -> str:
        return str(self.value)
