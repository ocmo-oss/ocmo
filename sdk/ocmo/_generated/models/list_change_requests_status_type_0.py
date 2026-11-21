from enum import Enum


class ListChangeRequestsStatusType0(str, Enum):
    APPLIED = "applied"
    OPEN = "open"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

    def __str__(self) -> str:
        return str(self.value)
