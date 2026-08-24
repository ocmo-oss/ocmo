import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        from .notice import load_notice_text

        try:
            logger.info("OCMO product notice:\n%s", load_notice_text().rstrip())
        except FileNotFoundError as exc:
            logger.warning("%s", exc)
