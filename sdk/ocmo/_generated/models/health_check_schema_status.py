from enum import Enum


class HealthCheckSchemaStatus(str, Enum):
    ERROR = "error"
    OK = "ok"

    def __str__(self) -> str:
        return str(self.value)
