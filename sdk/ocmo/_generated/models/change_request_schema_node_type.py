from enum import Enum


class ChangeRequestSchemaNodeType(str, Enum):
    CONFIG = "config"
    SECRET = "secret"
    TEMPLATE = "template"

    def __str__(self) -> str:
        return str(self.value)
